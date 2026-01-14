# =============================================================================
# Embedding Service
# =============================================================================
"""
OpenAI embedding generation service for the routing system.

Provides embedding generation with caching support for efficient semantic
similarity comparisons in Tier 2 routing.

Usage:
    from src.services.embedding_service import EmbeddingService, get_embedding_service

    service = await get_embedding_service()
    embedding = await service.get_embedding("create a github issue")
"""

import logging
from typing import Optional

import numpy as np
from openai import AsyncOpenAI

from src.config.settings import get_settings
from src.services.cache_service import CacheService, get_cache_service


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
# Default embedding model dimensions
EMBEDDING_DIMENSIONS = 1536


# -----------------------------------------------------------------------------
# Embedding Service Class
# -----------------------------------------------------------------------------
class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI's API.

    Provides caching support via Redis to avoid redundant API calls
    for repeated queries.

    Attributes:
        client: OpenAI async client instance.
        model: Embedding model name.
        dimensions: Expected embedding dimensions.
        cache: Optional cache service for embedding storage.

    Example:
        service = EmbeddingService(api_key="sk-...")
        await service.initialize()

        embedding = await service.get_embedding("create a github issue")
        similarity = service.cosine_similarity(embedding, other_embedding)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        """
        Initialize the embedding service.

        Args:
            api_key: OpenAI API key.
            model: Embedding model name.
            dimensions: Expected embedding dimensions.
        """
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.client: Optional[AsyncOpenAI] = None
        self.cache: Optional[CacheService] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the embedding service.

        Creates the OpenAI client and connects to cache.
        """
        if self._initialized:
            return

        if not self.api_key:
            logger.warning(
                "OpenAI API key not configured. Embedding service disabled."
            )
            return

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.cache = await get_cache_service()
        self._initialized = True
        logger.info(f"Embedding service initialized with model: {self.model}")

    @property
    def is_available(self) -> bool:
        """
        Check if the embedding service is available.

        Returns:
            True if the service is initialized and has a valid client.
        """
        return self._initialized and self.client is not None

    async def get_embedding(
        self,
        text: str,
        use_cache: bool = True,
    ) -> Optional[list[float]]:
        """
        Generate an embedding for the given text.

        Checks cache first if enabled, then calls OpenAI API if needed.

        Args:
            text: The text to generate an embedding for.
            use_cache: Whether to use caching (default: True).

        Returns:
            List of floats representing the embedding, or None if unavailable.

        Example:
            embedding = await service.get_embedding("create a github issue")
        """
        if not self.is_available:
            logger.debug("Embedding service not available")
            return None

        # Check cache first
        if use_cache and self.cache and self.cache.connected:
            query_hash = CacheService.hash_query(text)
            cached = await self.cache.get_embedding(query_hash)
            if cached:
                logger.debug(f"Cache hit for embedding: {query_hash[:8]}...")
                return self._deserialize_embedding(cached)

        # Call OpenAI API
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
            )
            embedding = response.data[0].embedding

            # Cache the result
            if use_cache and self.cache and self.cache.connected:
                query_hash = CacheService.hash_query(text)
                serialized = self._serialize_embedding(embedding)
                await self.cache.set_embedding(query_hash, serialized)
                logger.debug(f"Cached embedding: {query_hash[:8]}...")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def get_embeddings_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
    ) -> list[Optional[list[float]]]:
        """
        Generate embeddings for multiple texts in a single API call.

        More efficient than calling get_embedding() multiple times.

        Args:
            texts: List of texts to generate embeddings for.
            use_cache: Whether to use caching (default: True).

        Returns:
            List of embeddings (or None for failed texts).

        Example:
            embeddings = await service.get_embeddings_batch([
                "create a github issue",
                "send an email",
            ])
        """
        if not self.is_available:
            return [None] * len(texts)

        # Check cache for all texts
        results: list[Optional[list[float]]] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        if use_cache and self.cache and self.cache.connected:
            for i, text in enumerate(texts):
                query_hash = CacheService.hash_query(text)
                cached = await self.cache.get_embedding(query_hash)
                if cached:
                    results[i] = self._deserialize_embedding(cached)
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # Call API for uncached texts
        if uncached_texts:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                    dimensions=self.dimensions,
                )

                # Map results back to original indices
                for j, embedding_data in enumerate(response.data):
                    original_idx = uncached_indices[j]
                    embedding = embedding_data.embedding
                    results[original_idx] = embedding

                    # Cache the result
                    if use_cache and self.cache and self.cache.connected:
                        query_hash = CacheService.hash_query(uncached_texts[j])
                        serialized = self._serialize_embedding(embedding)
                        await self.cache.set_embedding(query_hash, serialized)

                logger.debug(f"Generated {len(uncached_texts)} embeddings via API")

            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")

        return results

    @staticmethod
    def cosine_similarity(
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.

        Returns:
            Cosine similarity score (0.0 to 1.0).

        Example:
            similarity = EmbeddingService.cosine_similarity(emb1, emb2)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    @staticmethod
    def _serialize_embedding(embedding: list[float]) -> bytes:
        """
        Serialize an embedding to bytes for caching.

        Args:
            embedding: List of floats representing the embedding.

        Returns:
            Serialized bytes.
        """
        return np.array(embedding, dtype=np.float32).tobytes()

    @staticmethod
    def _deserialize_embedding(data: bytes) -> list[float]:
        """
        Deserialize an embedding from cached bytes.

        Args:
            data: Serialized embedding bytes.

        Returns:
            List of floats representing the embedding.
        """
        return np.frombuffer(data, dtype=np.float32).tolist()


# -----------------------------------------------------------------------------
# Module-Level Service Instance
# -----------------------------------------------------------------------------
_embedding_service: Optional[EmbeddingService] = None


async def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global embedding service instance.

    Creates a new instance on first call and initializes it.

    Returns:
        The global EmbeddingService instance.

    Example:
        service = await get_embedding_service()
        embedding = await service.get_embedding("create a github issue")
    """
    global _embedding_service

    if _embedding_service is None:
        settings = get_settings()
        _embedding_service = EmbeddingService(
            api_key=settings.openai_api_key,
            model=settings.router_embedding_model,
            dimensions=settings.router_embedding_dimensions,
        )
        await _embedding_service.initialize()

    return _embedding_service


async def close_embedding_service() -> None:
    """
    Close the global embedding service instance.

    Should be called during application shutdown.
    """
    global _embedding_service
    _embedding_service = None


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------
async def generate_agent_embeddings() -> dict[str, bool]:
    """
    Generate and store embeddings for all agents in the database.

    This function should be called once during initial setup or when
    agent descriptions change.

    Returns:
        Dictionary mapping agent names to success status.

    Example:
        results = await generate_agent_embeddings()
        # {'github': True, 'todo': True, 'email': True, ...}
    """
    from sqlalchemy import select, update

    from src.database import RoutingAgent, get_session

    service = await get_embedding_service()
    if not service.is_available:
        logger.error("Embedding service not available. Cannot generate embeddings.")
        return {}

    results: dict[str, bool] = {}

    async with get_session() as session:
        # Get all agents
        query = select(RoutingAgent).where(RoutingAgent.enabled == True)
        result = await session.execute(query)
        agents = result.scalars().all()

        # Generate embeddings for each agent
        for agent in agents:
            try:
                # Create embedding text from description and keywords
                embedding_text = f"{agent.description} Keywords: {', '.join(agent.keywords)}"
                embedding = await service.get_embedding(embedding_text, use_cache=False)

                if embedding:
                    # Update the agent with the embedding
                    stmt = (
                        update(RoutingAgent)
                        .where(RoutingAgent.id == agent.id)
                        .values(embedding=embedding)
                    )
                    await session.execute(stmt)
                    results[agent.name] = True
                    logger.info(f"Generated embedding for agent: {agent.name}")
                else:
                    results[agent.name] = False
                    logger.warning(f"Failed to generate embedding for agent: {agent.name}")

            except Exception as e:
                results[agent.name] = False
                logger.error(f"Error generating embedding for {agent.name}: {e}")

        await session.commit()

    return results


async def ensure_agent_embeddings() -> dict[str, str]:
    """
    Check for missing agent embeddings and generate them if needed.

    This function is designed to be called during application startup.
    It only generates embeddings for agents that don't have them yet,
    making it safe to call on every startup.

    Returns:
        Dictionary mapping agent names to status ('exists', 'generated', 'failed', 'skipped').

    Example:
        results = await ensure_agent_embeddings()
        # {'github': 'exists', 'todo': 'generated', 'email': 'exists', ...}
    """
    from sqlalchemy import select, update

    from src.database import RoutingAgent, get_session

    service = await get_embedding_service()
    results: dict[str, str] = {}

    async with get_session() as session:
        # Get all enabled agents
        query = select(RoutingAgent).where(RoutingAgent.enabled == True)
        result = await session.execute(query)
        agents = result.scalars().all()

        if not agents:
            logger.info("No agents found in routing.agents table")
            return results

        # Check each agent for missing embeddings
        missing_agents: list[RoutingAgent] = []
        for agent in agents:
            if agent.embedding is not None:
                results[agent.name] = "exists"
                logger.debug(f"Agent '{agent.name}' already has embedding")
            else:
                missing_agents.append(agent)

        if not missing_agents:
            logger.info(
                f"All {len(agents)} agents have embeddings - no generation needed"
            )
            return results

        # Check if embedding service is available
        if not service.is_available:
            logger.warning(
                f"Embedding service not available. "
                f"Skipping {len(missing_agents)} agents without embeddings. "
                f"Set OPENAI_API_KEY to enable embedding generation."
            )
            for agent in missing_agents:
                results[agent.name] = "skipped"
            return results

        # Generate embeddings for agents that don't have them
        logger.info(
            f"Generating embeddings for {len(missing_agents)} agents..."
        )

        for agent in missing_agents:
            try:
                # Create embedding text from description and keywords
                embedding_text = f"{agent.description} Keywords: {', '.join(agent.keywords)}"
                embedding = await service.get_embedding(embedding_text, use_cache=False)

                if embedding:
                    # Update the agent with the embedding
                    stmt = (
                        update(RoutingAgent)
                        .where(RoutingAgent.id == agent.id)
                        .values(embedding=embedding)
                    )
                    await session.execute(stmt)
                    results[agent.name] = "generated"
                    logger.info(f"Generated embedding for agent: {agent.name}")
                else:
                    results[agent.name] = "failed"
                    logger.warning(
                        f"Failed to generate embedding for agent: {agent.name}"
                    )

            except Exception as e:
                results[agent.name] = "failed"
                logger.error(f"Error generating embedding for {agent.name}: {e}")

        await session.commit()

        # Log summary
        generated = sum(1 for v in results.values() if v == "generated")
        failed = sum(1 for v in results.values() if v == "failed")
        if generated > 0:
            logger.info(f"Generated {generated} new agent embeddings")
        if failed > 0:
            logger.warning(f"Failed to generate {failed} agent embeddings")

    return results
