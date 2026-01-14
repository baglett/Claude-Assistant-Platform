# =============================================================================
# Cache Service
# =============================================================================
"""
Redis caching service for the routing system.

Provides a unified interface for caching routing-related data including:
- Query embeddings (expensive to compute, cache for 1 hour)
- Routing decisions (cache repeated queries for 5 minutes)
- Agent data (cache configuration for 1 hour)

The service gracefully degrades if Redis is unavailable, allowing the system
to continue operating without caching.

Usage:
    from src.services.cache_service import CacheService, get_cache_service

    cache = await get_cache_service()

    # Cache an embedding
    await cache.set_embedding("query_hash", embedding_bytes, ttl=3600)
    embedding = await cache.get_embedding("query_hash")

    # Cache a routing decision
    await cache.set_routing_decision("query_hash", "github", confidence=0.95)
    result = await cache.get_routing_decision("query_hash")
"""

import hashlib
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from src.config.settings import get_settings


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Cache Key Prefixes
# -----------------------------------------------------------------------------
# Using prefixes to namespace different types of cached data
PREFIX_EMBEDDING = "router:emb:"
PREFIX_DECISION = "router:decision:"
PREFIX_AGENTS = "router:agents"
PREFIX_AGENT = "router:agent:"


# -----------------------------------------------------------------------------
# Default TTL Values (seconds)
# -----------------------------------------------------------------------------
TTL_EMBEDDING = 3600  # 1 hour - embeddings are expensive to compute
TTL_DECISION = 300    # 5 minutes - routing decisions for identical queries
TTL_AGENTS = 3600     # 1 hour - agent configuration doesn't change often


# -----------------------------------------------------------------------------
# Cache Service Class
# -----------------------------------------------------------------------------
class CacheService:
    """
    Redis caching service for the routing system.

    Provides methods for caching embeddings, routing decisions, and agent data.
    Gracefully handles Redis connection failures by returning None/False.

    Attributes:
        redis: Redis async client instance.
        connected: Whether the Redis connection is active.

    Example:
        cache = CacheService(redis_url="redis://localhost:6379/0")
        await cache.connect()

        # Cache embedding
        await cache.set_embedding("hash123", embedding_bytes)
        embedding = await cache.get_embedding("hash123")

        await cache.close()
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
    ) -> None:
        """
        Initialize the cache service.

        Args:
            redis_host: Redis server hostname.
            redis_port: Redis server port.
            redis_db: Redis database number.
            redis_password: Optional Redis password.
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self.redis: Optional[redis.Redis] = None
        self.connected = False

    async def connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.redis = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=False,  # We handle encoding ourselves
            )
            # Test connection with ping
            await self.redis.ping()
            self.connected = True
            logger.info(
                f"Connected to Redis at {self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
            return True
        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self.connected = False
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.connected = False
            logger.info("Closed Redis connection")

    async def health_check(self) -> bool:
        """
        Check if Redis is healthy and responsive.

        Returns:
            True if Redis responds to ping, False otherwise.
        """
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Embedding Cache Methods
    # -------------------------------------------------------------------------
    @staticmethod
    def hash_query(query: str) -> str:
        """
        Generate a hash for a query string.

        Args:
            query: The query string to hash.

        Returns:
            SHA256 hash of the query (first 16 chars).
        """
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]

    async def get_embedding(self, query_hash: str) -> Optional[bytes]:
        """
        Get cached embedding for a query hash.

        Args:
            query_hash: Hash of the query string.

        Returns:
            Embedding bytes if cached, None otherwise.
        """
        if not self.connected or not self.redis:
            return None
        try:
            key = f"{PREFIX_EMBEDDING}{query_hash}"
            return await self.redis.get(key)
        except Exception as e:
            logger.warning(f"Error getting embedding from cache: {e}")
            return None

    async def set_embedding(
        self,
        query_hash: str,
        embedding: bytes,
        ttl: int = TTL_EMBEDDING,
    ) -> bool:
        """
        Cache an embedding for a query hash.

        Args:
            query_hash: Hash of the query string.
            embedding: Embedding bytes (serialized numpy array).
            ttl: Time-to-live in seconds.

        Returns:
            True if cached successfully, False otherwise.
        """
        if not self.connected or not self.redis:
            return False
        try:
            key = f"{PREFIX_EMBEDDING}{query_hash}"
            await self.redis.setex(key, ttl, embedding)
            return True
        except Exception as e:
            logger.warning(f"Error setting embedding in cache: {e}")
            return False

    # -------------------------------------------------------------------------
    # Routing Decision Cache Methods
    # -------------------------------------------------------------------------
    async def get_routing_decision(
        self, query_hash: str
    ) -> Optional[dict[str, Any]]:
        """
        Get cached routing decision for a query hash.

        Args:
            query_hash: Hash of the query string.

        Returns:
            Dictionary with 'agent' and 'confidence' if cached, None otherwise.
        """
        if not self.connected or not self.redis:
            return None
        try:
            key = f"{PREFIX_DECISION}{query_hash}"
            data = await self.redis.get(key)
            if data:
                return json.loads(data.decode("utf-8"))
            return None
        except Exception as e:
            logger.warning(f"Error getting routing decision from cache: {e}")
            return None

    async def set_routing_decision(
        self,
        query_hash: str,
        agent: Optional[str],
        confidence: float,
        tier: int,
        ttl: int = TTL_DECISION,
    ) -> bool:
        """
        Cache a routing decision for a query hash.

        Args:
            query_hash: Hash of the query string.
            agent: Selected agent name (or None for orchestrator).
            confidence: Confidence score (0.0-1.0).
            tier: Which tier made the decision (1, 2, or 3).
            ttl: Time-to-live in seconds.

        Returns:
            True if cached successfully, False otherwise.
        """
        if not self.connected or not self.redis:
            return False
        try:
            key = f"{PREFIX_DECISION}{query_hash}"
            data = json.dumps({
                "agent": agent,
                "confidence": confidence,
                "tier": tier,
            })
            await self.redis.setex(key, ttl, data.encode("utf-8"))
            return True
        except Exception as e:
            logger.warning(f"Error setting routing decision in cache: {e}")
            return False

    # -------------------------------------------------------------------------
    # Agent Data Cache Methods
    # -------------------------------------------------------------------------
    async def get_agents(self) -> Optional[list[dict[str, Any]]]:
        """
        Get cached agent data.

        Returns:
            List of agent dictionaries if cached, None otherwise.
        """
        if not self.connected or not self.redis:
            return None
        try:
            data = await self.redis.get(PREFIX_AGENTS)
            if data:
                return json.loads(data.decode("utf-8"))
            return None
        except Exception as e:
            logger.warning(f"Error getting agents from cache: {e}")
            return None

    async def set_agents(
        self,
        agents: list[dict[str, Any]],
        ttl: int = TTL_AGENTS,
    ) -> bool:
        """
        Cache agent data.

        Args:
            agents: List of agent dictionaries.
            ttl: Time-to-live in seconds.

        Returns:
            True if cached successfully, False otherwise.
        """
        if not self.connected or not self.redis:
            return False
        try:
            data = json.dumps(agents)
            await self.redis.setex(PREFIX_AGENTS, ttl, data.encode("utf-8"))
            return True
        except Exception as e:
            logger.warning(f"Error setting agents in cache: {e}")
            return False

    async def invalidate_agents(self) -> bool:
        """
        Invalidate cached agent data.

        Call this when agent configuration changes.

        Returns:
            True if invalidated successfully, False otherwise.
        """
        if not self.connected or not self.redis:
            return False
        try:
            await self.redis.delete(PREFIX_AGENTS)
            logger.info("Invalidated agents cache")
            return True
        except Exception as e:
            logger.warning(f"Error invalidating agents cache: {e}")
            return False

    # -------------------------------------------------------------------------
    # Generic Cache Methods
    # -------------------------------------------------------------------------
    async def get(self, key: str) -> Optional[bytes]:
        """
        Get a value from cache by key.

        Args:
            key: Cache key.

        Returns:
            Cached value if exists, None otherwise.
        """
        if not self.connected or not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning(f"Error getting key {key} from cache: {e}")
            return None

    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Optional time-to-live in seconds.

        Returns:
            True if cached successfully, False otherwise.
        """
        if not self.connected or not self.redis:
            return False
        try:
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)
            return True
        except Exception as e:
            logger.warning(f"Error setting key {key} in cache: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self.connected or not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Error deleting key {key} from cache: {e}")
            return False


# -----------------------------------------------------------------------------
# Module-Level Cache Instance
# -----------------------------------------------------------------------------
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """
    Get or create the global cache service instance.

    Creates a new instance on first call and reuses it thereafter.
    Automatically connects to Redis using settings.

    Returns:
        The global CacheService instance.

    Example:
        cache = await get_cache_service()
        await cache.set_embedding("hash", embedding)
    """
    global _cache_service

    if _cache_service is None:
        settings = get_settings()
        _cache_service = CacheService(
            redis_host=settings.redis_host,
            redis_port=settings.redis_port,
            redis_db=settings.redis_db,
            redis_password=getattr(settings, "redis_password", None),
        )
        await _cache_service.connect()

    return _cache_service


async def close_cache_service() -> None:
    """
    Close the global cache service instance.

    Should be called during application shutdown.
    """
    global _cache_service

    if _cache_service is not None:
        await _cache_service.close()
        _cache_service = None
