# =============================================================================
# Routing ORM Models
# =============================================================================
"""
SQLAlchemy ORM models for the routing schema.

These models support the 3-tier hybrid router system for agent selection:
- RoutingAgent: Agent definitions with embeddings and routing metadata
- RoutingTool: Tool definitions for future tool-level routing
- RoutingDecision: Decision logs for analytics and improvement

Usage:
    from src.database.routing_models import RoutingAgent, RoutingDecision

    # Query agents
    agents = await session.execute(select(RoutingAgent).where(RoutingAgent.enabled == True))

    # Log a routing decision
    decision = RoutingDecision(
        chat_id=chat_id,
        user_message="create a github issue",
        tier_used=1,
        selected_agent="github",
        confidence=1.0,
        latency_ms=2,
    )
    session.add(decision)
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models import Base


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
# Embedding dimensions for OpenAI text-embedding-3-small
EMBEDDING_DIMENSIONS = 1536


# -----------------------------------------------------------------------------
# Routing Agent Model
# -----------------------------------------------------------------------------
class RoutingAgent(Base):
    """
    ORM model for routing.agents table.

    Stores agent definitions with routing metadata including keywords for BM25,
    regex patterns for fast matching, and embeddings for semantic similarity.

    Attributes:
        id: Unique identifier (UUID).
        name: Internal agent name (e.g., "github", "todo").
        display_name: Human-readable name (e.g., "GitHub Agent").
        description: Full description used for embedding generation.
        keywords: Array of keywords for BM25 text matching.
        regex_patterns: Array of regex patterns for Tier 1 fast matching.
        embedding: Vector embedding (1536 dims) for semantic similarity.
        enabled: Whether agent is enabled for routing.
        priority: Routing priority (lower = higher priority).
        created_at: Timestamp when the agent was created.
        updated_at: Timestamp when the agent was last updated.

    Example:
        agent = RoutingAgent(
            name="github",
            display_name="GitHub Agent",
            description="Manages GitHub repositories...",
            keywords=["github", "issue", "pr"],
            regex_patterns=[r"\\b(github|gh)\\b"],
            enabled=True,
            priority=10,
        )
    """

    __tablename__ = "agents"
    __table_args__ = {"schema": "routing"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Agent identification
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        doc="Internal agent name (e.g., 'github', 'todo')",
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable display name",
    )

    # Routing data
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full description for embedding generation",
    )
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        doc="Keywords for BM25 text matching",
    )
    regex_patterns: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Regex patterns for Tier 1 fast matching",
    )

    # Embedding for semantic similarity
    # Using pgvector's Vector type for 1536-dimensional embeddings
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=True,
        doc="OpenAI text-embedding-3-small vector (1536 dims)",
    )

    # Configuration
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable/disable agent for routing",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        doc="Routing priority (lower = higher priority)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tools: Mapped[list["RoutingTool"]] = relationship(
        "RoutingTool",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of the routing agent."""
        return f"<RoutingAgent(name={self.name}, enabled={self.enabled}, priority={self.priority})>"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert agent to dictionary for caching and serialization.

        Returns:
            Dictionary representation of the agent.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "keywords": self.keywords,
            "regex_patterns": self.regex_patterns,
            "enabled": self.enabled,
            "priority": self.priority,
        }


# -----------------------------------------------------------------------------
# Routing Tool Model
# -----------------------------------------------------------------------------
class RoutingTool(Base):
    """
    ORM model for routing.tools table.

    Stores tool definitions for future tool-level routing (Phase 2+).
    Currently unused but schema is prepared for expansion.

    Attributes:
        id: Unique identifier (UUID).
        agent_name: Foreign key to parent agent.
        tool_name: Name of the tool.
        description: Full description for embedding generation.
        keywords: Array of keywords for BM25 matching.
        embedding: Vector embedding for semantic similarity.
        input_schema: JSON schema for tool inputs.
        enabled: Whether tool is enabled.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    __tablename__ = "tools"
    __table_args__ = {"schema": "routing"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Tool identification
    agent_name: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("routing.agents.name", ondelete="CASCADE"),
        nullable=False,
        doc="Parent agent name",
    )
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Tool name (e.g., 'github_create_issue')",
    )

    # Routing data
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full description for embedding generation",
    )
    keywords: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Keywords for BM25 text matching",
    )

    # Embedding for semantic similarity
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=True,
        doc="OpenAI text-embedding-3-small vector (1536 dims)",
    )

    # Tool schema
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="JSON schema for tool inputs",
    )

    # Configuration
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable/disable tool for routing",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    agent: Mapped["RoutingAgent"] = relationship(
        "RoutingAgent",
        back_populates="tools",
    )

    def __repr__(self) -> str:
        """String representation of the routing tool."""
        return f"<RoutingTool(agent={self.agent_name}, tool={self.tool_name})>"


# -----------------------------------------------------------------------------
# Routing Decision Model
# -----------------------------------------------------------------------------
class RoutingDecision(Base):
    """
    ORM model for routing.decisions table.

    Logs all routing decisions for analytics, debugging, and improvement.
    Records which tier made the decision, confidence scores, and latency.

    Attributes:
        id: Unique identifier (UUID).
        chat_id: Foreign key to the chat (optional).
        user_message: The user's message that was routed.
        tier_used: Which routing tier made the decision (1=regex, 2=hybrid, 3=llm).
        selected_agent: The agent selected (NULL if routed to orchestrator).
        confidence: Confidence score (0.0-1.0).
        bm25_scores: BM25 scores per agent (JSONB).
        embedding_scores: Embedding similarity scores per agent (JSONB).
        latency_ms: Total routing time in milliseconds.
        correct: User feedback on correctness (NULL until feedback).
        created_at: Timestamp when the decision was made.

    Example:
        decision = RoutingDecision(
            chat_id=uuid,
            user_message="create a github issue for the login bug",
            tier_used=1,
            selected_agent="github",
            confidence=1.0,
            latency_ms=2,
        )
    """

    __tablename__ = "decisions"
    __table_args__ = {"schema": "routing"}

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Context
    chat_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messaging.chats.id", ondelete="SET NULL"),
        nullable=True,
        doc="Chat ID for context",
    )
    user_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="The user's message that was routed",
    )

    # Routing result
    tier_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Routing tier: 1=regex, 2=hybrid, 3=llm",
    )
    selected_agent: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Selected agent name (NULL if orchestrator)",
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score (0.0-1.0)",
    )

    # Detailed scores for debugging
    bm25_scores: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="BM25 scores per agent",
    )
    embedding_scores: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Embedding similarity scores per agent",
    )

    # Performance metrics
    latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Total routing time in milliseconds",
    )

    # Feedback
    correct: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        doc="User feedback on correctness (NULL until feedback)",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """String representation of the routing decision."""
        return (
            f"<RoutingDecision(tier={self.tier_used}, "
            f"agent={self.selected_agent}, confidence={self.confidence})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert decision to dictionary for logging and serialization.

        Returns:
            Dictionary representation of the decision.
        """
        return {
            "id": str(self.id),
            "chat_id": str(self.chat_id) if self.chat_id else None,
            "user_message": self.user_message,
            "tier_used": self.tier_used,
            "selected_agent": self.selected_agent,
            "confidence": self.confidence,
            "bm25_scores": self.bm25_scores,
            "embedding_scores": self.embedding_scores,
            "latency_ms": self.latency_ms,
            "correct": self.correct,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
