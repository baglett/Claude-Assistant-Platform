# =============================================================================
# Job Scraper Service
# =============================================================================
"""
Service for scraping and parsing job listings from various job boards.

Provides a unified interface to scrape job URLs and extract structured data.
Supports multiple job boards with site-specific parsers and falls back to
Claude-assisted parsing for unknown or complex sites.

Usage:
    from src.services.scraper import JobScraperService

    scraper = JobScraperService()

    # Simple scrape
    job_data = await scraper.scrape_job("https://linkedin.com/jobs/view/123456")

    # With Claude fallback for low-confidence results
    job_data = await scraper.scrape_job(
        "https://unknown-site.com/job/xyz",
        claude_fallback=True
    )
"""

import logging
from typing import Optional
from urllib.parse import urlparse

import httpx

from src.services.scraper.parsers import (
    ParsedJobData,
    get_parsers,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MIN_CONFIDENCE_FOR_SUCCESS = 50  # Below this, consider using Claude fallback


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------
class ScraperError(Exception):
    """Base exception for scraper errors."""

    pass


class FetchError(ScraperError):
    """Error fetching URL content."""

    pass


class ParseError(ScraperError):
    """Error parsing HTML content."""

    pass


class UnsupportedURLError(ScraperError):
    """URL is not supported or invalid."""

    pass


# -----------------------------------------------------------------------------
# Job Scraper Service Class
# -----------------------------------------------------------------------------
class JobScraperService:
    """
    Service for scraping job listings from various job boards.

    Provides methods to fetch and parse job listings, with support for
    multiple job boards and Claude-assisted fallback parsing.

    Attributes:
        http_client: Async HTTP client for fetching pages.
        parsers: List of available parsers.

    Example:
        scraper = JobScraperService()

        # Scrape a LinkedIn job
        job = await scraper.scrape_job("https://linkedin.com/jobs/view/123456")
        print(f"Title: {job.job_title}")
        print(f"Company: {job.company_name}")
        print(f"Skills: {job.required_skills}")
    """

    def __init__(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize the job scraper service.

        Args:
            http_client: Optional pre-configured httpx client.
            user_agent: User agent string for requests.
            timeout: Request timeout in seconds.
        """
        self._owned_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            follow_redirects=True,
        )
        self.parsers = get_parsers()

    async def close(self) -> None:
        """
        Close the HTTP client if owned by this service.

        Should be called when the service is no longer needed.
        """
        if self._owned_client and self.http_client:
            await self.http_client.aclose()
            logger.debug("HTTP client closed")

    async def __aenter__(self) -> "JobScraperService":
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up on context exit."""
        await self.close()

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------
    async def scrape_job(
        self,
        url: str,
        claude_fallback: bool = False,
        anthropic_api_key: Optional[str] = None,
    ) -> ParsedJobData:
        """
        Scrape a job listing from the given URL.

        Fetches the page HTML and parses it using the appropriate parser.
        If parsing confidence is low and claude_fallback is enabled,
        uses Claude to extract job details.

        Args:
            url: Job listing URL to scrape.
            claude_fallback: Whether to use Claude for low-confidence results.
            anthropic_api_key: API key for Claude (required if claude_fallback=True).

        Returns:
            Parsed job data with extracted information.

        Raises:
            UnsupportedURLError: If URL is invalid or obviously not a job listing.
            FetchError: If unable to fetch the URL.
            ParseError: If unable to parse the page content.

        Example:
            job = await scraper.scrape_job(
                "https://linkedin.com/jobs/view/123456",
                claude_fallback=True,
                anthropic_api_key="sk-ant-..."
            )
        """
        # ---------------------------------------------------------------------
        # Validate URL
        # ---------------------------------------------------------------------
        validated_url = self._validate_url(url)
        logger.info(f"Scraping job listing: {validated_url}")

        # ---------------------------------------------------------------------
        # Fetch HTML
        # ---------------------------------------------------------------------
        html = await self._fetch_url(validated_url)
        logger.debug(f"Fetched {len(html)} bytes from {validated_url}")

        # ---------------------------------------------------------------------
        # Find appropriate parser
        # ---------------------------------------------------------------------
        parser = self._select_parser(validated_url, html)
        logger.info(f"Using parser: {parser.source_name}")

        # ---------------------------------------------------------------------
        # Parse HTML
        # ---------------------------------------------------------------------
        try:
            job_data = parser.parse(html, validated_url)
        except Exception as e:
            logger.error(f"Parser error: {e}", exc_info=True)
            raise ParseError(f"Failed to parse job listing: {e}") from e

        # ---------------------------------------------------------------------
        # Claude Fallback for Low Confidence
        # ---------------------------------------------------------------------
        if (
            claude_fallback
            and job_data.parse_confidence < MIN_CONFIDENCE_FOR_SUCCESS
            and anthropic_api_key
        ):
            logger.info(
                f"Low confidence ({job_data.parse_confidence}%), "
                "attempting Claude-assisted parsing"
            )
            enhanced_data = await self._claude_parse(
                html, validated_url, anthropic_api_key
            )
            if enhanced_data:
                # Merge Claude results with existing data
                job_data = self._merge_parsed_data(job_data, enhanced_data)
                job_data.parse_warnings.append(
                    "Enhanced with Claude-assisted parsing"
                )

        return job_data

    async def scrape_multiple(
        self,
        urls: list[str],
        claude_fallback: bool = False,
        anthropic_api_key: Optional[str] = None,
    ) -> list[ParsedJobData]:
        """
        Scrape multiple job listings.

        Args:
            urls: List of job listing URLs.
            claude_fallback: Whether to use Claude for low-confidence results.
            anthropic_api_key: API key for Claude.

        Returns:
            List of parsed job data, one per URL.

        Note:
            Failed URLs will have empty ParsedJobData with error in warnings.
        """
        import asyncio

        results = []

        # Scrape in batches to avoid rate limiting
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[
                    self._safe_scrape(url, claude_fallback, anthropic_api_key)
                    for url in batch
                ],
                return_exceptions=True,
            )

            for url, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    # Create error result
                    error_data = ParsedJobData()
                    error_data.parse_warnings.append(f"Scrape failed: {result}")
                    error_data.parse_confidence = 0
                    results.append(error_data)
                else:
                    results.append(result)

            # Brief delay between batches
            if i + batch_size < len(urls):
                await asyncio.sleep(1.0)

        return results

    def get_supported_sites(self) -> list[str]:
        """
        Get list of explicitly supported job sites.

        Returns:
            List of site names with dedicated parsers.
        """
        return [p.source_name for p in self.parsers if p.source_name != "generic"]

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------
    def _validate_url(self, url: str) -> str:
        """
        Validate and normalize the URL.

        Args:
            url: URL to validate.

        Returns:
            Normalized URL string.

        Raises:
            UnsupportedURLError: If URL is invalid.
        """
        if not url:
            raise UnsupportedURLError("URL cannot be empty")

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            parsed = urlparse(url)

            # Basic validation
            if not parsed.netloc:
                raise UnsupportedURLError(f"Invalid URL format: {url}")

            # Block obvious non-job URLs
            blocked_domains = ["google.com", "facebook.com", "twitter.com"]
            if any(d in parsed.netloc.lower() for d in blocked_domains):
                raise UnsupportedURLError(
                    f"URL does not appear to be a job listing: {url}"
                )

            return url

        except Exception as e:
            raise UnsupportedURLError(f"Invalid URL: {e}") from e

    async def _fetch_url(self, url: str) -> str:
        """
        Fetch HTML content from URL.

        Args:
            url: URL to fetch.

        Returns:
            HTML content as string.

        Raises:
            FetchError: If request fails.
        """
        try:
            response = await self.http_client.get(url)

            # Check for non-success status
            if response.status_code >= 400:
                raise FetchError(
                    f"HTTP {response.status_code}: {response.reason_phrase}"
                )

            return response.text

        except httpx.TimeoutException as e:
            raise FetchError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise FetchError(f"Request failed: {e}") from e

    def _select_parser(self, url: str, html: str):
        """
        Select the best parser for the given URL and HTML.

        Args:
            url: Job listing URL.
            html: Page HTML content.

        Returns:
            Parser instance to use.
        """
        for parser in self.parsers:
            if parser.can_parse(url, html):
                return parser

        # Should never reach here as generic parser always matches
        return self.parsers[-1]

    async def _safe_scrape(
        self,
        url: str,
        claude_fallback: bool,
        anthropic_api_key: Optional[str],
    ) -> ParsedJobData:
        """
        Scrape with exception handling.

        Args:
            url: URL to scrape.
            claude_fallback: Whether to use Claude fallback.
            anthropic_api_key: API key for Claude.

        Returns:
            Parsed job data or error result.
        """
        try:
            return await self.scrape_job(url, claude_fallback, anthropic_api_key)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            raise

    async def _claude_parse(
        self,
        html: str,
        url: str,
        api_key: str,
    ) -> Optional[ParsedJobData]:
        """
        Use Claude to extract job details from HTML.

        Falls back to Claude's understanding of HTML structure
        when site-specific parsers fail or have low confidence.

        Args:
            html: HTML content to parse.
            url: Original URL for context.
            api_key: Anthropic API key.

        Returns:
            Parsed job data or None if Claude parsing fails.
        """
        try:
            import anthropic
            from bs4 import BeautifulSoup

            # Clean HTML to reduce token usage
            soup = BeautifulSoup(html, "lxml")

            # Remove scripts, styles, and other non-content
            for tag in soup(["script", "style", "meta", "link", "noscript"]):
                tag.decompose()

            # Get cleaned text content
            cleaned_text = soup.get_text(separator="\n", strip=True)

            # Limit text length for token efficiency
            max_chars = 15000
            if len(cleaned_text) > max_chars:
                cleaned_text = cleaned_text[:max_chars] + "..."

            # Create Claude client
            client = anthropic.Anthropic(api_key=api_key)

            # Build prompt for extraction
            prompt = f"""Extract job listing information from this webpage content.

URL: {url}

Content:
{cleaned_text}

Extract the following in JSON format:
{{
    "job_title": "The job title/position",
    "company_name": "Company name",
    "location": "Job location (city, state, country)",
    "is_remote": true/false,
    "salary_min": number or null,
    "salary_max": number or null,
    "salary_currency": "USD/EUR/etc or null",
    "description": "Brief summary of the job (2-3 sentences)",
    "required_skills": ["skill1", "skill2", ...],
    "preferred_skills": ["skill1", "skill2", ...],
    "requirements": ["requirement1", "requirement2", ...]
}}

Return ONLY the JSON object, no other text."""

            # Call Claude
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            import json

            response_text = message.content[0].text.strip()

            # Try to extract JSON from response
            if response_text.startswith("{"):
                data = json.loads(response_text)
            else:
                # Try to find JSON in response
                import re

                json_match = re.search(r"\{[\s\S]*\}", response_text)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    logger.warning("Could not extract JSON from Claude response")
                    return None

            # Convert to ParsedJobData
            result = ParsedJobData(
                job_title=data.get("job_title"),
                company_name=data.get("company_name"),
                location=data.get("location"),
                is_remote=data.get("is_remote", False),
                salary_min=data.get("salary_min"),
                salary_max=data.get("salary_max"),
                salary_currency=data.get("salary_currency"),
                description=data.get("description"),
                required_skills=data.get("required_skills", []),
                preferred_skills=data.get("preferred_skills", []),
                requirements=data.get("requirements", []),
                source_site="claude",
                parse_confidence=75,  # Claude parsing is reasonably confident
            )

            logger.info(
                f"Claude parsed job: '{result.job_title}' at '{result.company_name}'"
            )

            return result

        except Exception as e:
            logger.error(f"Claude parsing failed: {e}", exc_info=True)
            return None

    def _merge_parsed_data(
        self,
        original: ParsedJobData,
        enhanced: ParsedJobData,
    ) -> ParsedJobData:
        """
        Merge Claude-enhanced data with original parser results.

        Prefers Claude data for empty fields, keeps original for populated fields.

        Args:
            original: Data from site-specific parser.
            enhanced: Data from Claude parsing.

        Returns:
            Merged ParsedJobData with best available information.
        """
        # Create merged result starting from original
        merged = ParsedJobData(
            job_title=original.job_title or enhanced.job_title,
            company_name=original.company_name or enhanced.company_name,
            company_url=original.company_url or enhanced.company_url,
            location=original.location or enhanced.location,
            is_remote=original.is_remote or enhanced.is_remote,
            salary_min=original.salary_min or enhanced.salary_min,
            salary_max=original.salary_max or enhanced.salary_max,
            salary_currency=original.salary_currency or enhanced.salary_currency,
            description=original.description or enhanced.description,
            required_skills=original.required_skills or enhanced.required_skills,
            preferred_skills=original.preferred_skills or enhanced.preferred_skills,
            requirements=original.requirements or enhanced.requirements,
            raw_html=original.raw_html,
            source_site=original.source_site,
            parse_confidence=max(original.parse_confidence, enhanced.parse_confidence),
            parse_warnings=original.parse_warnings + enhanced.parse_warnings,
        )

        return merged
