# =============================================================================
# Motion MCP Server - Rate Limiter
# =============================================================================
"""
Token bucket rate limiter with SQLite persistence.

This module implements a robust rate limiting system to prevent exceeding
Motion's API rate limits (12 req/min for individual, 120 req/min for team).

The rate limiter uses SQLite for persistence, ensuring that rate limit state
survives server restarts and prevents accidental API abuse.

CRITICAL: Exceeding Motion's rate limits can result in account suspension.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import aiosqlite

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Constants and Enums
# -----------------------------------------------------------------------------
class AccountType(str, Enum):
    """
    Motion account types with their respective rate limits.

    Attributes:
        INDIVIDUAL: Personal accounts with 12 requests per minute.
        TEAM: Team/business accounts with 120 requests per minute.
        ENTERPRISE: Enterprise accounts with custom limits.
    """

    INDIVIDUAL = "individual"
    TEAM = "team"
    ENTERPRISE = "enterprise"


# Default rate limits per account type (requests per minute)
DEFAULT_RATE_LIMITS: dict[AccountType, int] = {
    AccountType.INDIVIDUAL: 12,
    AccountType.TEAM: 120,
    AccountType.ENTERPRISE: 500,  # Placeholder; should be configured
}


# -----------------------------------------------------------------------------
# Data Classes
# -----------------------------------------------------------------------------
@dataclass
class RateLimitStatus:
    """
    Current rate limit status.

    Attributes:
        can_proceed: Whether the request can proceed.
        remaining_requests: Number of requests remaining in current window.
        reset_time: Unix timestamp when the rate limit resets.
        wait_seconds: Seconds to wait if rate limited (0 if can proceed).
    """

    can_proceed: bool
    remaining_requests: int
    reset_time: float
    wait_seconds: float


# -----------------------------------------------------------------------------
# Rate Limiter Exception
# -----------------------------------------------------------------------------
class RateLimitExceededError(Exception):
    """
    Exception raised when rate limit is exceeded.

    Attributes:
        wait_seconds: Number of seconds to wait before retrying.
        message: Human-readable error message.
    """

    def __init__(self, wait_seconds: float, message: str):
        """
        Initialize the exception.

        Args:
            wait_seconds: Number of seconds to wait before retrying.
            message: Human-readable error message.
        """
        self.wait_seconds = wait_seconds
        self.message = message
        super().__init__(message)


# -----------------------------------------------------------------------------
# Rate Limiter Implementation
# -----------------------------------------------------------------------------
class RateLimiter:
    """
    Token bucket rate limiter with SQLite persistence.

    This implementation uses a sliding window approach to track API requests
    and ensure we never exceed Motion's rate limits. The state is persisted
    to SQLite so rate limits survive server restarts.

    Attributes:
        max_requests: Maximum requests allowed in the window.
        window_seconds: Duration of the rate limit window in seconds.
        db_path: Path to the SQLite database file.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int = 60,
        db_path: str = "motion_rate_limit.db",
    ) -> None:
        """
        Initialize the rate limiter.

        Args:
            max_requests: Maximum requests allowed in the window.
            window_seconds: Duration of the rate limit window in seconds.
            db_path: Path to the SQLite database file for persistence.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()
        self._initialized = False

        logger.info(
            f"Rate limiter configured: {max_requests} requests "
            f"per {window_seconds} seconds"
        )

    async def _ensure_initialized(self) -> None:
        """
        Ensure the database is initialized.

        Creates the database and table if they don't exist.
        """
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Create the requests table if it doesn't exist
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL
                )
                """
            )
            # Create an index for faster timestamp queries
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_requests_timestamp
                ON requests(timestamp)
                """
            )
            await db.commit()

        self._initialized = True
        logger.debug("Rate limiter database initialized")

    async def _cleanup_old_requests(self, db: aiosqlite.Connection) -> None:
        """
        Remove requests older than the rate limit window.

        Args:
            db: The database connection.
        """
        cutoff_time = time.time() - self.window_seconds
        await db.execute("DELETE FROM requests WHERE timestamp < ?", (cutoff_time,))
        await db.commit()

    async def _count_recent_requests(self, db: aiosqlite.Connection) -> int:
        """
        Count requests within the current window.

        Args:
            db: The database connection.

        Returns:
            Number of requests in the current window.
        """
        cutoff_time = time.time() - self.window_seconds
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE timestamp >= ?", (cutoff_time,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def _get_oldest_request_time(
        self, db: aiosqlite.Connection
    ) -> Optional[float]:
        """
        Get the timestamp of the oldest request in the current window.

        Args:
            db: The database connection.

        Returns:
            Timestamp of the oldest request, or None if no requests.
        """
        cutoff_time = time.time() - self.window_seconds
        async with db.execute(
            "SELECT MIN(timestamp) FROM requests WHERE timestamp >= ?", (cutoff_time,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def _record_request(self, db: aiosqlite.Connection) -> None:
        """
        Record a new request.

        Args:
            db: The database connection.
        """
        await db.execute("INSERT INTO requests (timestamp) VALUES (?)", (time.time(),))
        await db.commit()

    async def check_rate_limit(self) -> RateLimitStatus:
        """
        Check current rate limit status without consuming a request.

        Returns:
            RateLimitStatus with current state information.
        """
        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await self._cleanup_old_requests(db)
                current_count = await self._count_recent_requests(db)
                oldest_time = await self._get_oldest_request_time(db)

                remaining = self.max_requests - current_count
                can_proceed = remaining > 0

                # Calculate reset time
                if oldest_time:
                    reset_time = oldest_time + self.window_seconds
                else:
                    reset_time = time.time() + self.window_seconds

                # Calculate wait time if rate limited
                wait_seconds = 0.0
                if not can_proceed and oldest_time:
                    expires_at = oldest_time + self.window_seconds
                    wait_seconds = max(0.0, expires_at - time.time())

                return RateLimitStatus(
                    can_proceed=can_proceed,
                    remaining_requests=max(0, remaining),
                    reset_time=reset_time,
                    wait_seconds=wait_seconds,
                )

    async def acquire(self, wait: bool = False) -> RateLimitStatus:
        """
        Attempt to acquire a rate limit slot.

        If successful, records the request and returns the updated status.
        If rate limited and wait=True, waits until a slot is available.
        If rate limited and wait=False, raises RateLimitExceededError.

        Args:
            wait: If True, wait for a slot to become available.

        Returns:
            RateLimitStatus after acquiring the slot.

        Raises:
            RateLimitExceededError: If rate limit exceeded and wait=False.
        """
        await self._ensure_initialized()

        while True:
            async with self._lock:
                async with aiosqlite.connect(self.db_path) as db:
                    await self._cleanup_old_requests(db)
                    current_count = await self._count_recent_requests(db)

                    if current_count < self.max_requests:
                        # We can proceed - record the request
                        await self._record_request(db)
                        remaining = self.max_requests - current_count - 1

                        logger.debug(
                            f"Rate limit slot acquired. "
                            f"Remaining: {remaining}/{self.max_requests}"
                        )

                        return RateLimitStatus(
                            can_proceed=True,
                            remaining_requests=remaining,
                            reset_time=time.time() + self.window_seconds,
                            wait_seconds=0.0,
                        )

                    # Rate limit exceeded
                    oldest_time = await self._get_oldest_request_time(db)
                    wait_seconds = 0.0
                    if oldest_time:
                        wait_seconds = max(
                            0.0, (oldest_time + self.window_seconds) - time.time()
                        )

                    if not wait:
                        msg = (
                            f"Rate limit exceeded. "
                            f"Please wait {wait_seconds:.1f} seconds before retrying."
                        )
                        raise RateLimitExceededError(
                            wait_seconds=wait_seconds,
                            message=msg,
                        )

            # Wait for the oldest request to expire
            if wait_seconds > 0:
                logger.info(f"Rate limited. Waiting {wait_seconds:.1f} seconds...")
                await asyncio.sleep(wait_seconds + 0.1)  # Small buffer

    async def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with rate limiter statistics.
        """
        status = await self.check_rate_limit()

        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining_requests": status.remaining_requests,
            "can_proceed": status.can_proceed,
            "reset_time": status.reset_time,
            "wait_seconds": status.wait_seconds,
        }

    async def reset(self) -> None:
        """
        Reset the rate limiter (clear all recorded requests).

        WARNING: Use with caution - this removes all rate limit tracking.
        """
        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM requests")
                await db.commit()

        logger.warning("Rate limiter reset - all request history cleared")


# -----------------------------------------------------------------------------
# Factory Function
# -----------------------------------------------------------------------------
def create_rate_limiter(
    account_type: AccountType = AccountType.INDIVIDUAL,
    override_limit: int = 0,
    window_seconds: int = 60,
    db_path: str = "motion_rate_limit.db",
) -> RateLimiter:
    """
    Create a rate limiter with appropriate limits for the account type.

    Args:
        account_type: The Motion account type.
        override_limit: Override the default limit (0 = use default).
        window_seconds: Duration of the rate limit window.
        db_path: Path to the SQLite database file.

    Returns:
        Configured RateLimiter instance.
    """
    if override_limit > 0:
        max_requests = override_limit
        logger.warning(
            f"Using override rate limit: {override_limit} requests "
            f"per {window_seconds} seconds"
        )
    else:
        max_requests = DEFAULT_RATE_LIMITS.get(
            account_type, DEFAULT_RATE_LIMITS[AccountType.INDIVIDUAL]
        )

    return RateLimiter(
        max_requests=max_requests,
        window_seconds=window_seconds,
        db_path=db_path,
    )
