# =============================================================================
# Motion MCP Server - Rate Limiter Tests
# =============================================================================
"""
Unit tests for the rate limiter module.

These tests verify that the rate limiter correctly:
- Tracks requests within a sliding window
- Enforces rate limits
- Persists state to SQLite
- Calculates wait times correctly
"""

import asyncio
import os
import tempfile

import pytest

from src.rate_limiter import (
    AccountType,
    RateLimiter,
    RateLimitExceededError,
    create_rate_limiter,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def temp_db() -> str:
    """
    Create a temporary database file for testing.

    Yields:
        Path to temporary database file.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def rate_limiter(temp_db: str) -> RateLimiter:
    """
    Create a rate limiter with small limits for testing.

    Args:
        temp_db: Path to temporary database.

    Returns:
        Configured RateLimiter instance.
    """
    return RateLimiter(
        max_requests=3,
        window_seconds=2,
        db_path=temp_db,
    )


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------
class TestRateLimiter:
    """Tests for the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_initial_state(self, rate_limiter: RateLimiter) -> None:
        """Test that initial state allows requests."""
        status = await rate_limiter.check_rate_limit()

        assert status.can_proceed is True
        assert status.remaining_requests == 3
        assert status.wait_seconds == 0.0

    @pytest.mark.asyncio
    async def test_acquire_decrements_remaining(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test that acquiring slots decrements remaining count."""
        # First request
        status = await rate_limiter.acquire()
        assert status.remaining_requests == 2

        # Second request
        status = await rate_limiter.acquire()
        assert status.remaining_requests == 1

        # Third request
        status = await rate_limiter.acquire()
        assert status.remaining_requests == 0

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter: RateLimiter) -> None:
        """Test that exceeding rate limit raises error."""
        # Exhaust all requests
        for _ in range(3):
            await rate_limiter.acquire()

        # Fourth request should fail
        with pytest.raises(RateLimitExceededError) as exc_info:
            await rate_limiter.acquire(wait=False)

        assert exc_info.value.wait_seconds > 0
        assert "Rate limit exceeded" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_rate_limit_resets(self, rate_limiter: RateLimiter) -> None:
        """Test that rate limit resets after window expires."""
        # Exhaust all requests
        for _ in range(3):
            await rate_limiter.acquire()

        # Wait for window to expire
        await asyncio.sleep(2.5)

        # Should be able to make requests again
        status = await rate_limiter.acquire()
        assert status.can_proceed is True

    @pytest.mark.asyncio
    async def test_check_does_not_consume(self, rate_limiter: RateLimiter) -> None:
        """Test that check_rate_limit doesn't consume a request slot."""
        # Check multiple times
        for _ in range(10):
            status = await rate_limiter.check_rate_limit()
            assert status.remaining_requests == 3

    @pytest.mark.asyncio
    async def test_get_stats(self, rate_limiter: RateLimiter) -> None:
        """Test getting rate limiter statistics."""
        await rate_limiter.acquire()

        stats = await rate_limiter.get_stats()

        assert stats["max_requests"] == 3
        assert stats["window_seconds"] == 2
        assert stats["remaining_requests"] == 2
        assert stats["can_proceed"] is True

    @pytest.mark.asyncio
    async def test_reset(self, rate_limiter: RateLimiter) -> None:
        """Test resetting the rate limiter."""
        # Exhaust requests
        for _ in range(3):
            await rate_limiter.acquire()

        # Reset
        await rate_limiter.reset()

        # Should have full capacity again
        status = await rate_limiter.check_rate_limit()
        assert status.remaining_requests == 3


class TestRateLimiterFactory:
    """Tests for the create_rate_limiter factory function."""

    def test_individual_account(self, temp_db: str) -> None:
        """Test creating limiter for individual account."""
        limiter = create_rate_limiter(
            account_type=AccountType.INDIVIDUAL,
            db_path=temp_db,
        )
        assert limiter.max_requests == 12

    def test_team_account(self, temp_db: str) -> None:
        """Test creating limiter for team account."""
        limiter = create_rate_limiter(
            account_type=AccountType.TEAM,
            db_path=temp_db,
        )
        assert limiter.max_requests == 120

    def test_override_limit(self, temp_db: str) -> None:
        """Test overriding the rate limit."""
        limiter = create_rate_limiter(
            account_type=AccountType.INDIVIDUAL,
            override_limit=50,
            db_path=temp_db,
        )
        assert limiter.max_requests == 50

    def test_custom_window(self, temp_db: str) -> None:
        """Test custom window duration."""
        limiter = create_rate_limiter(
            account_type=AccountType.INDIVIDUAL,
            window_seconds=120,
            db_path=temp_db,
        )
        assert limiter.window_seconds == 120
