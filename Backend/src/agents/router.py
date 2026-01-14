# =============================================================================
# Router Integration
# =============================================================================
"""
Router integration for the orchestrator agent.

Provides a high-level interface for routing user messages to specialized agents,
bypassing the orchestrator's LLM call when confident routing is possible.

This module bridges the RouterService with the OrchestratorAgent, providing:
- Automatic routing decision caching
- Seamless fallback to orchestrator when routing is uncertain
- Performance metrics and logging

Usage:
    from src.agents.router import AgentRouter

    router = AgentRouter(registry)
    await router.initialize()

    # Try to route directly
    result = await router.try_route(message, context)
    if result:
        return result  # Direct agent response
    else:
        # Fall back to orchestrator
        return await orchestrator.process_message(message, ...)
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import AgentContext, AgentRegistry, AgentResult
from src.services.router_service import RouterService, RoutingResult, get_router_service


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Router Statistics
# -----------------------------------------------------------------------------
@dataclass
class RouterStats:
    """
    Statistics about router performance.

    Attributes:
        total_requests: Total routing requests processed.
        tier1_hits: Number of Tier 1 (regex) successful routes.
        tier2_hits: Number of Tier 2 (hybrid) successful routes.
        tier3_hits: Number of Tier 3 (LLM) successful routes.
        cache_hits: Number of cache hits.
        orchestrator_fallbacks: Number of fallbacks to orchestrator.
        avg_latency_ms: Average routing latency in milliseconds.
    """

    total_requests: int = 0
    tier1_hits: int = 0
    tier2_hits: int = 0
    tier3_hits: int = 0
    cache_hits: int = 0
    orchestrator_fallbacks: int = 0
    total_latency_ms: int = 0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def bypass_rate(self) -> float:
        """Calculate orchestrator bypass rate."""
        if self.total_requests == 0:
            return 0.0
        bypassed = (
            self.tier1_hits
            + self.tier2_hits
            + self.tier3_hits
            + self.cache_hits
        )
        return bypassed / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "total_requests": self.total_requests,
            "tier1_hits": self.tier1_hits,
            "tier2_hits": self.tier2_hits,
            "tier3_hits": self.tier3_hits,
            "cache_hits": self.cache_hits,
            "orchestrator_fallbacks": self.orchestrator_fallbacks,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "bypass_rate": round(self.bypass_rate * 100, 1),
        }


# -----------------------------------------------------------------------------
# Agent Router Class
# -----------------------------------------------------------------------------
class AgentRouter:
    """
    High-level router for directing messages to specialized agents.

    Integrates the RouterService with the AgentRegistry to provide
    seamless routing with fallback to the orchestrator.

    Attributes:
        registry: Agent registry for looking up agents.
        router: RouterService for making routing decisions.
        stats: Performance statistics.
        enabled: Whether routing is enabled.

    Example:
        router = AgentRouter(registry)
        await router.initialize()

        # Try direct routing
        result = await router.try_route(message, context)
        if result:
            return result.message
        else:
            # Use orchestrator
            return await orchestrator.process_message(...)
    """

    def __init__(self, registry: AgentRegistry) -> None:
        """
        Initialize the agent router.

        Args:
            registry: Agent registry for looking up agents.
        """
        self.registry = registry
        self.router: Optional[RouterService] = None
        self.stats = RouterStats()
        self.enabled = True
        self._initialized = False

    async def initialize(self, session: Optional[AsyncSession] = None) -> None:
        """
        Initialize the router.

        Args:
            session: Optional database session.
        """
        if self._initialized:
            return

        try:
            self.router = await get_router_service()
            await self.router.initialize(session)
            self._initialized = True
            logger.info("Agent router initialized")
        except Exception as e:
            logger.error(f"Failed to initialize agent router: {e}")
            self.enabled = False

    async def try_route(
        self,
        message: str,
        context: AgentContext,
    ) -> Optional[AgentResult]:
        """
        Try to route a message directly to a specialized agent.

        If routing is confident, executes the agent and returns the result.
        If not confident, returns None to indicate fallback to orchestrator.

        Args:
            message: The user's message.
            context: Agent context for execution.

        Returns:
            AgentResult if routed successfully, None if should use orchestrator.

        Example:
            result = await router.try_route("create a github issue", context)
            if result:
                return result  # Direct response from agent
            else:
                return await orchestrator.execute(context)  # Fallback
        """
        if not self.enabled or not self._initialized:
            return None

        start_time = time.perf_counter()
        self.stats.total_requests += 1

        try:
            # Get routing decision
            routing_result = await self.router.route(
                message,
                chat_id=context.chat_id,
                session=context.session,
            )

            self.stats.total_latency_ms += routing_result.latency_ms

            # Update stats based on result
            if routing_result.from_cache:
                self.stats.cache_hits += 1
            elif routing_result.tier == 1:
                if routing_result.should_bypass_orchestrator:
                    self.stats.tier1_hits += 1
            elif routing_result.tier == 2:
                if routing_result.should_bypass_orchestrator:
                    self.stats.tier2_hits += 1
            elif routing_result.tier == 3:
                if routing_result.should_bypass_orchestrator:
                    self.stats.tier3_hits += 1

            # If not confident enough, fall back to orchestrator
            if not routing_result.should_bypass_orchestrator:
                self.stats.orchestrator_fallbacks += 1
                logger.debug(
                    f"Routing not confident (conf={routing_result.confidence:.2f}), "
                    f"falling back to orchestrator"
                )
                return None

            # Look up the agent
            agent = self.registry.get(routing_result.agent)
            if not agent:
                logger.warning(
                    f"Routed to unknown agent '{routing_result.agent}', "
                    f"falling back to orchestrator"
                )
                self.stats.orchestrator_fallbacks += 1
                return None

            # Execute the agent directly
            logger.info(
                f"Direct routing to '{routing_result.agent}' "
                f"(tier={routing_result.tier}, conf={routing_result.confidence:.2f}, "
                f"latency={routing_result.latency_ms}ms)"
            )

            # Create a sub-context with the task
            sub_context = AgentContext(
                chat_id=context.chat_id,
                task=message,
                session=context.session,
                created_by=context.created_by,
                recent_messages=context.recent_messages,
                parent_execution_id=context.parent_execution_id,
                metadata={
                    **context.metadata,
                    "routed_by": "hybrid_router",
                    "routing_tier": routing_result.tier,
                    "routing_confidence": routing_result.confidence,
                },
            )

            result = await agent.execute(sub_context)

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.debug(
                f"Direct agent execution completed in {elapsed_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Error during routing: {e}", exc_info=True)
            self.stats.orchestrator_fallbacks += 1
            return None

    def get_stats(self) -> dict[str, Any]:
        """
        Get router performance statistics.

        Returns:
            Dictionary with performance metrics.
        """
        return self.stats.to_dict()

    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self.stats = RouterStats()

    async def refresh(self, session: Optional[AsyncSession] = None) -> None:
        """
        Refresh router configuration.

        Call this when agent configuration changes.

        Args:
            session: Optional database session.
        """
        if self.router:
            await self.router.refresh_agents(session)
            logger.info("Agent router refreshed")


# -----------------------------------------------------------------------------
# Module-Level Router Instance
# -----------------------------------------------------------------------------
_agent_router: Optional[AgentRouter] = None


async def get_agent_router(registry: AgentRegistry) -> AgentRouter:
    """
    Get or create the global agent router instance.

    Args:
        registry: Agent registry (required on first call).

    Returns:
        The global AgentRouter instance.
    """
    global _agent_router

    if _agent_router is None:
        _agent_router = AgentRouter(registry)
        await _agent_router.initialize()

    return _agent_router


def set_agent_router(router: AgentRouter) -> None:
    """
    Set the global agent router instance.

    Useful for testing or custom configurations.

    Args:
        router: AgentRouter instance to use globally.
    """
    global _agent_router
    _agent_router = router
