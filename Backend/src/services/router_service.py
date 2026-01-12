# =============================================================================
# Router Service
# =============================================================================
"""
Three-tier hybrid router service for fast agent selection.

Implements a cascading routing system that minimizes latency:
- Tier 1: Regex/keyword matching (<1ms) - handles 60-70% of queries
- Tier 2: BM25 + Embedding hybrid (10-50ms) - handles 20-25% of queries
- Tier 3: LLM classification (200-500ms) - handles 5-10% of ambiguous queries

The router attempts each tier in order, stopping when a confident decision
is made. This minimizes Claude API calls for clear-intent queries.

Usage:
    from src.services.router_service import RouterService, get_router_service

    router = await get_router_service()
    result = await router.route("create a github issue")
    if result.agent:
        # Route directly to agent
        agent = registry.get(result.agent)
        response = await agent.execute(context)
    else:
        # Fall back to orchestrator
        response = await orchestrator.execute(context)
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.database import RoutingAgent, RoutingDecision, get_session
from src.services.cache_service import CacheService, get_cache_service


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Routing Result Dataclass
# -----------------------------------------------------------------------------
@dataclass
class RoutingResult:
    """
    Result of a routing decision.

    Attributes:
        agent: Selected agent name (None if should use orchestrator).
        confidence: Confidence score (0.0-1.0).
        tier: Which tier made the decision (1, 2, 3, or 0 for cache hit).
        scores: Detailed scores per agent for debugging.
        latency_ms: Time taken to make the decision.
        from_cache: Whether the result was retrieved from cache.

    Example:
        result = RoutingResult(
            agent="github",
            confidence=1.0,
            tier=1,
            scores={"github": 3, "todo": 0, "email": 0},
            latency_ms=1,
        )
    """

    agent: Optional[str] = None
    confidence: float = 0.0
    tier: int = 0
    scores: dict[str, float] = field(default_factory=dict)
    latency_ms: int = 0
    from_cache: bool = False

    @property
    def should_bypass_orchestrator(self) -> bool:
        """
        Whether the routing is confident enough to bypass the orchestrator.

        Returns:
            True if an agent was selected with sufficient confidence.
        """
        return self.agent is not None and self.confidence >= 0.75


# -----------------------------------------------------------------------------
# Tier 1: Regex Patterns
# -----------------------------------------------------------------------------
# These patterns are used for fast, deterministic routing.
# Each pattern is compiled once at startup for performance.

AGENT_PATTERNS: dict[str, list[str]] = {
    "github": [
        r"\b(github|gh)\b",
        r"\b(issue|issues)\b",
        r"\b(pull\s*request|pr|prs)\b",
        r"\b(repository|repo|repos)\b",
        r"\b(branch|branches|merge|commit|commits)\b",
        r"\b(review|reviewing)\s+(pr|pull|code)\b",
    ],
    "todo": [
        r"\b(todo|todos)\b",
        r"\b(task|tasks)\b",
        r"\b(remind|reminder|reminders)\b",
        r"\b(add|create|make).{0,20}(task|todo|reminder)\b",
        r"\b(complete|done|finish).{0,20}(task|todo)\b",
        r"\b(list|show|what).{0,20}(tasks?|todos?)\b",
    ],
    "email": [
        r"\b(email|emails|e-mail)\b",
        r"\b(mail|inbox|mailbox)\b",
        r"\b(gmail)\b",
        r"\b(send|compose|write|draft).{0,20}(email|message|mail)\b",
        r"\b(reply|forward|respond).{0,20}(email|message)\b",
        r"\b(check|read).{0,20}(inbox|email|mail)\b",
    ],
    "calendar": [
        r"\b(calendar|calendars)\b",
        r"\b(schedule|scheduling)\b",
        r"\b(meeting|meetings)\b",
        r"\b(event|events)\b",
        r"\b(appointment|appointments)\b",
        r"\b(free|busy|available|availability)\b",
        r"\b(book|booking).{0,20}(time|slot|meeting)\b",
    ],
    "motion": [
        r"\bmotion\b",
        r"\bmotion.{0,20}(task|project|workspace)\b",
    ],
}


# -----------------------------------------------------------------------------
# Router Service Class
# -----------------------------------------------------------------------------
class RouterService:
    """
    Three-tier hybrid router for fast agent selection.

    Implements cascading routing:
    1. Tier 1: Regex matching (<1ms)
    2. Tier 2: BM25 + Embedding hybrid (10-50ms) [Phase 2]
    3. Tier 3: LLM classification (200-500ms) [Phase 3]

    Attributes:
        cache: Redis cache service.
        agents: Cached list of enabled agents.
        compiled_patterns: Pre-compiled regex patterns per agent.
        settings: Application settings.

    Example:
        router = RouterService()
        await router.initialize()

        result = await router.route("create a github issue")
        print(result.agent)  # "github"
        print(result.tier)   # 1
    """

    def __init__(self) -> None:
        """Initialize the router service."""
        self.cache: Optional[CacheService] = None
        self.agents: list[dict[str, Any]] = []
        self.agent_names: list[str] = []
        self.compiled_patterns: dict[str, list[re.Pattern]] = {}
        self.settings = get_settings()
        self._initialized = False

    async def initialize(self, session: Optional[AsyncSession] = None) -> None:
        """
        Initialize the router service.

        Loads agents from database, compiles regex patterns, and connects to cache.

        Args:
            session: Optional database session.
        """
        if self._initialized:
            return

        # Connect to cache
        self.cache = await get_cache_service()

        # Load agents from database
        await self._load_agents(session)

        # Compile regex patterns
        self._compile_patterns()

        self._initialized = True
        logger.info(
            f"Router service initialized with {len(self.agents)} agents"
        )

    async def _load_agents(self, session: Optional[AsyncSession] = None) -> None:
        """
        Load enabled agents from database.

        Args:
            session: Optional database session.
        """
        # Try cache first
        if self.cache and self.cache.connected:
            cached_agents = await self.cache.get_agents()
            if cached_agents:
                self.agents = cached_agents
                self.agent_names = [a["name"] for a in self.agents]
                logger.debug(f"Loaded {len(self.agents)} agents from cache")
                return

        # Load from database
        if session:
            await self._load_agents_from_db(session)
        else:
            async with get_session() as session:
                await self._load_agents_from_db(session)

        # Cache the agents
        if self.cache and self.cache.connected and self.agents:
            await self.cache.set_agents(self.agents)

    async def _load_agents_from_db(self, session: AsyncSession) -> None:
        """
        Load agents from database.

        Args:
            session: Database session.
        """
        query = (
            select(RoutingAgent)
            .where(RoutingAgent.enabled == True)
            .order_by(RoutingAgent.priority)
        )
        result = await session.execute(query)
        agents = result.scalars().all()

        self.agents = [agent.to_dict() for agent in agents]
        self.agent_names = [a["name"] for a in self.agents]
        logger.debug(f"Loaded {len(self.agents)} agents from database")

    def _compile_patterns(self) -> None:
        """Compile regex patterns for Tier 1 matching."""
        # First, use patterns from database if available
        for agent in self.agents:
            name = agent["name"]
            patterns = agent.get("regex_patterns") or []
            if patterns:
                self.compiled_patterns[name] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]

        # Fall back to hardcoded patterns for any missing agents
        for name, patterns in AGENT_PATTERNS.items():
            if name not in self.compiled_patterns:
                self.compiled_patterns[name] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]

        logger.debug(
            f"Compiled patterns for {len(self.compiled_patterns)} agents"
        )

    async def route(
        self,
        message: str,
        chat_id: Optional[UUID] = None,
        session: Optional[AsyncSession] = None,
    ) -> RoutingResult:
        """
        Route a user message to the appropriate agent.

        Attempts each tier in order, stopping when a confident decision is made.

        Args:
            message: The user's message to route.
            chat_id: Optional chat ID for logging.
            session: Optional database session.

        Returns:
            RoutingResult with the selected agent and confidence.

        Example:
            result = await router.route("create a github issue")
            if result.should_bypass_orchestrator:
                agent = registry.get(result.agent)
                response = await agent.execute(context)
        """
        if not self._initialized:
            await self.initialize(session)

        start_time = time.perf_counter()

        # Check cache first
        if self.cache and self.cache.connected:
            query_hash = CacheService.hash_query(message)
            cached = await self.cache.get_routing_decision(query_hash)
            if cached:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                return RoutingResult(
                    agent=cached["agent"],
                    confidence=cached["confidence"],
                    tier=cached["tier"],
                    latency_ms=latency_ms,
                    from_cache=True,
                )

        # Tier 1: Regex matching
        result = self._tier1_regex(message)
        if result.should_bypass_orchestrator:
            result.latency_ms = int((time.perf_counter() - start_time) * 1000)
            await self._log_decision(result, message, chat_id, session)
            return result

        # Tier 2: BM25 + Embedding (Phase 2 - placeholder)
        if not self.settings.router_tier1_only:
            result = await self._tier2_hybrid(message)
            if result.should_bypass_orchestrator:
                result.latency_ms = int((time.perf_counter() - start_time) * 1000)
                await self._log_decision(result, message, chat_id, session)
                return result

            # Tier 3: LLM Classification (Phase 3 - placeholder)
            result = await self._tier3_llm(message)
            result.latency_ms = int((time.perf_counter() - start_time) * 1000)
            await self._log_decision(result, message, chat_id, session)
            return result

        # If tier1_only and no match, return no agent (use orchestrator)
        result.latency_ms = int((time.perf_counter() - start_time) * 1000)
        await self._log_decision(result, message, chat_id, session)
        return result

    def _tier1_regex(self, message: str) -> RoutingResult:
        """
        Tier 1: Regex-based agent matching.

        Counts pattern matches per agent. If exactly one agent matches,
        routes directly with high confidence.

        Args:
            message: The user's message.

        Returns:
            RoutingResult with scores and potential agent selection.
        """
        message_lower = message.lower()
        scores: dict[str, int] = {}

        for agent_name, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(message_lower):
                    score += 1
            scores[agent_name] = score

        # Find agents with matches
        matched_agents = [name for name, score in scores.items() if score > 0]

        # If exactly one agent matched, route with high confidence
        if len(matched_agents) == 1:
            agent = matched_agents[0]
            confidence = min(1.0, scores[agent] / 3)  # Cap at 1.0, scale by matches
            return RoutingResult(
                agent=agent,
                confidence=max(0.85, confidence),  # At least 0.85 for regex match
                tier=1,
                scores={k: float(v) for k, v in scores.items()},
            )

        # If multiple agents matched, check if one is clearly dominant
        if len(matched_agents) > 1:
            sorted_agents = sorted(
                matched_agents, key=lambda x: scores[x], reverse=True
            )
            top_score = scores[sorted_agents[0]]
            second_score = scores[sorted_agents[1]]

            # If top agent has 2+ more matches than second, route to it
            if top_score >= second_score + 2:
                agent = sorted_agents[0]
                confidence = 0.75 + (0.1 * (top_score - second_score - 1))
                return RoutingResult(
                    agent=agent,
                    confidence=min(0.95, confidence),
                    tier=1,
                    scores={k: float(v) for k, v in scores.items()},
                )

        # No clear match, return scores for potential Tier 2
        return RoutingResult(
            agent=None,
            confidence=0.0,
            tier=1,
            scores={k: float(v) for k, v in scores.items()},
        )

    async def _tier2_hybrid(self, message: str) -> RoutingResult:
        """
        Tier 2: BM25 + Embedding hybrid scoring.

        Combines keyword matching (BM25) with semantic similarity (embeddings)
        for more nuanced routing decisions.

        Args:
            message: The user's message.

        Returns:
            RoutingResult with hybrid scores.

        Note:
            This is a placeholder for Phase 2 implementation.
        """
        # TODO: Phase 2 - Implement BM25 + embedding scoring
        # 1. Compute BM25 scores using agent keywords
        # 2. Generate query embedding via OpenAI
        # 3. Compute cosine similarity with agent embeddings
        # 4. Combine: 0.3 * BM25 + 0.7 * embedding
        # 5. Return if confidence > threshold

        logger.debug("Tier 2 hybrid scoring not yet implemented (Phase 2)")
        return RoutingResult(
            agent=None,
            confidence=0.0,
            tier=2,
            scores={},
        )

    async def _tier3_llm(self, message: str) -> RoutingResult:
        """
        Tier 3: LLM-based classification.

        Uses Claude Haiku to classify ambiguous queries when Tier 1 and 2
        don't produce confident results.

        Args:
            message: The user's message.

        Returns:
            RoutingResult with LLM classification.

        Note:
            This is a placeholder for Phase 3 implementation.
        """
        # TODO: Phase 3 - Implement Haiku classification
        # 1. Send message to Claude Haiku with classification prompt
        # 2. Parse response to get agent name
        # 3. Return with appropriate confidence

        logger.debug("Tier 3 LLM classification not yet implemented (Phase 3)")
        return RoutingResult(
            agent=None,
            confidence=0.0,
            tier=3,
            scores={},
        )

    async def _log_decision(
        self,
        result: RoutingResult,
        message: str,
        chat_id: Optional[UUID],
        session: Optional[AsyncSession],
    ) -> None:
        """
        Log a routing decision to the database.

        Args:
            result: The routing result to log.
            message: The user's message.
            chat_id: Optional chat ID.
            session: Optional database session.
        """
        # Skip logging for cache hits
        if result.from_cache:
            return

        # Cache the decision if we have a confident result
        if self.cache and self.cache.connected and result.agent:
            query_hash = CacheService.hash_query(message)
            await self.cache.set_routing_decision(
                query_hash,
                result.agent,
                result.confidence,
                result.tier,
            )

        # Log to database
        try:
            decision = RoutingDecision(
                chat_id=chat_id,
                user_message=message[:1000],  # Truncate long messages
                tier_used=result.tier,
                selected_agent=result.agent,
                confidence=result.confidence,
                bm25_scores=result.scores if result.tier >= 2 else None,
                embedding_scores=None,  # Phase 2
                latency_ms=result.latency_ms,
            )

            if session:
                session.add(decision)
                await session.flush()
            else:
                async with get_session() as new_session:
                    new_session.add(decision)
                    await new_session.commit()

            logger.debug(
                f"Logged routing decision: tier={result.tier}, "
                f"agent={result.agent}, confidence={result.confidence:.2f}"
            )
        except Exception as e:
            logger.warning(f"Failed to log routing decision: {e}")

    async def refresh_agents(self, session: Optional[AsyncSession] = None) -> None:
        """
        Refresh agent data from database.

        Call this when agent configuration changes.

        Args:
            session: Optional database session.
        """
        if self.cache and self.cache.connected:
            await self.cache.invalidate_agents()

        await self._load_agents(session)
        self._compile_patterns()
        logger.info(f"Refreshed router with {len(self.agents)} agents")


# -----------------------------------------------------------------------------
# Module-Level Router Instance
# -----------------------------------------------------------------------------
_router_service: Optional[RouterService] = None


async def get_router_service() -> RouterService:
    """
    Get or create the global router service instance.

    Creates a new instance on first call and initializes it.

    Returns:
        The global RouterService instance.

    Example:
        router = await get_router_service()
        result = await router.route("create a github issue")
    """
    global _router_service

    if _router_service is None:
        _router_service = RouterService()
        await _router_service.initialize()

    return _router_service


async def close_router_service() -> None:
    """
    Close the global router service instance.

    Should be called during application shutdown.
    """
    global _router_service
    _router_service = None
