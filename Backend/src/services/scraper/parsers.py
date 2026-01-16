# =============================================================================
# Job Listing Parsers
# =============================================================================
"""
Site-specific parsers for extracting job listing data from HTML.

Each parser is optimized for a specific job board's HTML structure.
Falls back to generic parsing when structure doesn't match expected patterns.

Note: Job board HTML structures change frequently. Parsers should be
designed to degrade gracefully when selectors fail to match.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Parsed Job Data Structure
# -----------------------------------------------------------------------------
@dataclass
class ParsedJobData:
    """
    Structured data extracted from a job listing.

    Attributes:
        job_title: Position title.
        company_name: Hiring company name.
        company_url: Company website or profile URL.
        location: Job location (city, state, country).
        is_remote: Whether the job is remote/hybrid.
        salary_min: Minimum salary if provided.
        salary_max: Maximum salary if provided.
        salary_currency: Currency code for salary (USD, EUR, etc.).
        description: Full job description text.
        required_skills: List of required skills extracted.
        preferred_skills: List of preferred/nice-to-have skills.
        requirements: List of job requirements/qualifications.
        raw_html: Original HTML for reference.
        source_site: Name of the job board.
        parse_confidence: Confidence score (0-100) for parsed data accuracy.
        parse_warnings: Any warnings or issues during parsing.
    """

    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    description: Optional[str] = None
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    raw_html: Optional[str] = None
    source_site: Optional[str] = None
    parse_confidence: int = 0
    parse_warnings: list[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Base Parser Abstract Class
# -----------------------------------------------------------------------------
class BaseJobParser(ABC):
    """
    Abstract base class for job listing parsers.

    Subclasses implement site-specific parsing logic while inheriting
    common utility methods for text extraction and cleaning.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the job board this parser handles."""
        pass

    @abstractmethod
    def can_parse(self, url: str, html: str) -> bool:
        """
        Check if this parser can handle the given URL/HTML.

        Args:
            url: The job listing URL.
            html: The HTML content.

        Returns:
            True if this parser should be used.
        """
        pass

    @abstractmethod
    def parse(self, html: str, url: str) -> ParsedJobData:
        """
        Parse the HTML and extract job data.

        Args:
            html: The HTML content to parse.
            url: The original URL for context.

        Returns:
            Parsed job data structure.
        """
        pass

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """
        Clean extracted text by removing extra whitespace.

        Args:
            text: Raw text to clean.

        Returns:
            Cleaned text or None if input was None/empty.
        """
        if not text:
            return None

        # Remove extra whitespace and normalize
        cleaned = re.sub(r"\s+", " ", text.strip())
        return cleaned if cleaned else None

    def _extract_text(
        self,
        soup: BeautifulSoup,
        selectors: list[str],
        attr: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extract text using multiple CSS selectors with fallback.

        Args:
            soup: BeautifulSoup object to search.
            selectors: List of CSS selectors to try in order.
            attr: Optional attribute to extract instead of text content.

        Returns:
            First successful text extraction or None.
        """
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if attr:
                    value = element.get(attr)
                    if isinstance(value, list):
                        value = " ".join(value)
                    return self._clean_text(value)
                return self._clean_text(element.get_text())
        return None

    def _extract_salary(self, text: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
        """
        Extract salary range from text.

        Handles formats like:
        - "$100,000 - $150,000"
        - "$100K-$150K"
        - "100,000 to 150,000 USD"

        Args:
            text: Text containing salary information.

        Returns:
            Tuple of (min_salary, max_salary, currency).
        """
        # Common currency patterns
        currency_map = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "USD": "USD",
            "EUR": "EUR",
            "GBP": "GBP",
        }

        currency = None
        for symbol, code in currency_map.items():
            if symbol in text:
                currency = code
                break

        # Extract numbers
        # Pattern handles: 100,000 or 100000 or 100K
        numbers = re.findall(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?K?)", text, re.IGNORECASE)

        if not numbers:
            return None, None, None

        def parse_number(s: str) -> int:
            """Convert salary string to integer."""
            s = s.replace(",", "")
            if s.upper().endswith("K"):
                return int(float(s[:-1]) * 1000)
            return int(float(s))

        try:
            if len(numbers) >= 2:
                return parse_number(numbers[0]), parse_number(numbers[1]), currency
            elif len(numbers) == 1:
                return parse_number(numbers[0]), None, currency
        except (ValueError, IndexError):
            pass

        return None, None, currency

    def _detect_remote(self, text: str) -> bool:
        """
        Detect if job is remote based on text.

        Args:
            text: Text to analyze.

        Returns:
            True if remote indicators found.
        """
        remote_patterns = [
            r"\bremote\b",
            r"\bwork from home\b",
            r"\bwfh\b",
            r"\bhybrid\b",
            r"\btelecommute\b",
            r"\bdistributed\b",
        ]

        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in remote_patterns)

    def _extract_skills_from_text(self, text: str) -> list[str]:
        """
        Extract skills from text using common skill keywords.

        Args:
            text: Text to search for skills.

        Returns:
            List of detected skills.
        """
        # Common technical skills to look for
        skill_patterns = [
            # Programming Languages
            r"\bPython\b", r"\bJavaScript\b", r"\bTypeScript\b", r"\bJava\b",
            r"\bC\+\+\b", r"\bC#\b", r"\bGo\b", r"\bRust\b", r"\bRuby\b",
            r"\bSwift\b", r"\bKotlin\b", r"\bScala\b", r"\bPHP\b", r"\bPerl\b",
            # Frameworks
            r"\bReact\b", r"\bAngular\b", r"\bVue\.?js?\b", r"\bNode\.?js\b",
            r"\bDjango\b", r"\bFlask\b", r"\bFastAPI\b", r"\bSpring\b",
            r"\bRails\b", r"\b\.NET\b", r"\bExpress\b", r"\bNext\.?js\b",
            # Databases
            r"\bPostgreSQL\b", r"\bMySQL\b", r"\bMongoDB\b", r"\bRedis\b",
            r"\bElasticsearch\b", r"\bSQL Server\b", r"\bOracle\b",
            r"\bCassandra\b", r"\bDynamoDB\b",
            # Cloud/DevOps
            r"\bAWS\b", r"\bAzure\b", r"\bGCP\b", r"\bGoogle Cloud\b",
            r"\bDocker\b", r"\bKubernetes\b", r"\bTerraform\b", r"\bAnsible\b",
            r"\bJenkins\b", r"\bCI/CD\b", r"\bGitHub Actions\b",
            # AI/ML
            r"\bMachine Learning\b", r"\bDeep Learning\b", r"\bTensorFlow\b",
            r"\bPyTorch\b", r"\bNLP\b", r"\bComputer Vision\b",
            r"\bLLM\b", r"\bGPT\b", r"\bClaude\b",
            # Other
            r"\bGraphQL\b", r"\bREST\b", r"\bAPI\b", r"\bAgile\b",
            r"\bScrum\b", r"\bGit\b", r"\bLinux\b", r"\bUnix\b",
        ]

        found_skills = []
        for pattern in skill_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Extract the actual matched text
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    skill = match.group().strip()
                    if skill and skill not in found_skills:
                        found_skills.append(skill)

        return found_skills


# -----------------------------------------------------------------------------
# LinkedIn Parser
# -----------------------------------------------------------------------------
class LinkedInParser(BaseJobParser):
    """
    Parser for LinkedIn job listings.

    Handles job URLs like:
    - https://www.linkedin.com/jobs/view/123456
    - https://linkedin.com/jobs/view/123456
    """

    @property
    def source_name(self) -> str:
        return "linkedin"

    def can_parse(self, url: str, html: str) -> bool:
        """Check if URL is a LinkedIn job posting."""
        return "linkedin.com/jobs" in url.lower()

    def parse(self, html: str, url: str) -> ParsedJobData:
        """
        Parse LinkedIn job listing HTML.

        LinkedIn frequently changes their HTML structure. This parser
        attempts multiple selectors for each field.
        """
        soup = BeautifulSoup(html, "lxml")
        data = ParsedJobData(source_site=self.source_name, raw_html=html)
        confidence_score = 0

        # ---------------------------------------------------------------------
        # Job Title
        # ---------------------------------------------------------------------
        title_selectors = [
            "h1.top-card-layout__title",
            "h1.topcard__title",
            "h1[class*='job-title']",
            "h1",
        ]
        data.job_title = self._extract_text(soup, title_selectors)
        if data.job_title:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Company Name
        # ---------------------------------------------------------------------
        company_selectors = [
            "a.topcard__org-name-link",
            "span.topcard__flavor a",
            "a[data-tracking-control-name='public_jobs_topcard-org-name']",
            ".topcard__org-name-link",
        ]
        data.company_name = self._extract_text(soup, company_selectors)
        if data.company_name:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Company URL
        # ---------------------------------------------------------------------
        company_link = soup.select_one("a.topcard__org-name-link")
        if company_link:
            data.company_url = company_link.get("href")

        # ---------------------------------------------------------------------
        # Location
        # ---------------------------------------------------------------------
        location_selectors = [
            "span.topcard__flavor--bullet",
            ".job-details-jobs-unified-top-card__primary-description-container",
            "[class*='location']",
        ]
        data.location = self._extract_text(soup, location_selectors)
        if data.location:
            confidence_score += 10

        # ---------------------------------------------------------------------
        # Job Description
        # ---------------------------------------------------------------------
        description_selectors = [
            "div.show-more-less-html__markup",
            "div.description__text",
            "section.description",
            "div[class*='description']",
        ]
        data.description = self._extract_text(soup, description_selectors)
        if data.description:
            confidence_score += 30
            # Check for remote
            data.is_remote = self._detect_remote(data.description)
            # Extract skills from description
            data.required_skills = self._extract_skills_from_text(data.description)

        # ---------------------------------------------------------------------
        # Salary (if visible)
        # ---------------------------------------------------------------------
        salary_selectors = [
            "div.salary-compensation-type__salary",
            "[class*='salary']",
        ]
        salary_text = self._extract_text(soup, salary_selectors)
        if salary_text:
            data.salary_min, data.salary_max, data.salary_currency = self._extract_salary(
                salary_text
            )
            if data.salary_min:
                confidence_score += 10

        data.parse_confidence = min(confidence_score, 100)

        if not data.job_title:
            data.parse_warnings.append("Could not extract job title")
        if not data.company_name:
            data.parse_warnings.append("Could not extract company name")
        if not data.description:
            data.parse_warnings.append("Could not extract job description")

        logger.info(
            f"Parsed LinkedIn job: '{data.job_title}' at '{data.company_name}' "
            f"(confidence: {data.parse_confidence}%)"
        )

        return data


# -----------------------------------------------------------------------------
# Indeed Parser
# -----------------------------------------------------------------------------
class IndeedParser(BaseJobParser):
    """
    Parser for Indeed job listings.

    Handles job URLs like:
    - https://www.indeed.com/viewjob?jk=abc123
    - https://indeed.com/jobs?q=...&vjk=abc123
    """

    @property
    def source_name(self) -> str:
        return "indeed"

    def can_parse(self, url: str, html: str) -> bool:
        """Check if URL is an Indeed job posting."""
        return "indeed.com" in url.lower()

    def parse(self, html: str, url: str) -> ParsedJobData:
        """Parse Indeed job listing HTML."""
        soup = BeautifulSoup(html, "lxml")
        data = ParsedJobData(source_site=self.source_name, raw_html=html)
        confidence_score = 0

        # ---------------------------------------------------------------------
        # Job Title
        # ---------------------------------------------------------------------
        title_selectors = [
            "h1.jobsearch-JobInfoHeader-title",
            "h1[data-testid='jobTitle']",
            ".jobsearch-JobInfoHeader-title-container h1",
            "h1",
        ]
        data.job_title = self._extract_text(soup, title_selectors)
        if data.job_title:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Company Name
        # ---------------------------------------------------------------------
        company_selectors = [
            "[data-testid='inlineHeader-companyName'] a",
            "[data-testid='companyName']",
            ".jobsearch-CompanyInfoContainer a",
            "[class*='companyName']",
        ]
        data.company_name = self._extract_text(soup, company_selectors)
        if data.company_name:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Location
        # ---------------------------------------------------------------------
        location_selectors = [
            "[data-testid='inlineHeader-companyLocation']",
            "[data-testid='job-location']",
            ".jobsearch-JobInfoHeader-subtitle > div:nth-child(2)",
        ]
        data.location = self._extract_text(soup, location_selectors)
        if data.location:
            confidence_score += 10
            data.is_remote = self._detect_remote(data.location)

        # ---------------------------------------------------------------------
        # Salary
        # ---------------------------------------------------------------------
        salary_selectors = [
            "[data-testid='attribute_snippet_compensation']",
            "#salaryInfoAndJobType span",
            "[class*='salary']",
        ]
        salary_text = self._extract_text(soup, salary_selectors)
        if salary_text:
            data.salary_min, data.salary_max, data.salary_currency = self._extract_salary(
                salary_text
            )
            if data.salary_min:
                confidence_score += 10

        # ---------------------------------------------------------------------
        # Job Description
        # ---------------------------------------------------------------------
        description_selectors = [
            "#jobDescriptionText",
            "[data-testid='jobDescriptionText']",
            ".jobsearch-jobDescriptionText",
        ]
        data.description = self._extract_text(soup, description_selectors)
        if data.description:
            confidence_score += 30
            if not data.is_remote:
                data.is_remote = self._detect_remote(data.description)
            data.required_skills = self._extract_skills_from_text(data.description)

        data.parse_confidence = min(confidence_score, 100)

        if not data.job_title:
            data.parse_warnings.append("Could not extract job title")
        if not data.company_name:
            data.parse_warnings.append("Could not extract company name")

        logger.info(
            f"Parsed Indeed job: '{data.job_title}' at '{data.company_name}' "
            f"(confidence: {data.parse_confidence}%)"
        )

        return data


# -----------------------------------------------------------------------------
# Greenhouse ATS Parser
# -----------------------------------------------------------------------------
class GreenhouseParser(BaseJobParser):
    """
    Parser for Greenhouse ATS job listings.

    Handles job URLs like:
    - https://boards.greenhouse.io/company/jobs/123456
    - https://company.greenhouse.io/jobs/123456
    """

    @property
    def source_name(self) -> str:
        return "greenhouse"

    def can_parse(self, url: str, html: str) -> bool:
        """Check if URL is a Greenhouse job posting."""
        return "greenhouse.io" in url.lower()

    def parse(self, html: str, url: str) -> ParsedJobData:
        """Parse Greenhouse ATS job listing HTML."""
        soup = BeautifulSoup(html, "lxml")
        data = ParsedJobData(source_site=self.source_name, raw_html=html)
        confidence_score = 0

        # ---------------------------------------------------------------------
        # Job Title
        # ---------------------------------------------------------------------
        title_selectors = [
            "h1.app-title",
            "h1[class*='posting-headline']",
            ".posting-headline h2",
            "h1",
        ]
        data.job_title = self._extract_text(soup, title_selectors)
        if data.job_title:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Company Name
        # ---------------------------------------------------------------------
        # Greenhouse often has company name in URL or header
        company_selectors = [
            "span.company-name",
            "[class*='company']",
            "a.company-link",
        ]
        data.company_name = self._extract_text(soup, company_selectors)

        # Try extracting from URL if not found
        if not data.company_name:
            parsed_url = urlparse(url)
            if "boards.greenhouse.io" in parsed_url.netloc:
                # Format: boards.greenhouse.io/company/jobs/123
                parts = parsed_url.path.strip("/").split("/")
                if parts:
                    data.company_name = parts[0].replace("-", " ").title()
            elif ".greenhouse.io" in parsed_url.netloc:
                # Format: company.greenhouse.io
                subdomain = parsed_url.netloc.split(".")[0]
                data.company_name = subdomain.replace("-", " ").title()

        if data.company_name:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Location
        # ---------------------------------------------------------------------
        location_selectors = [
            ".location",
            "[class*='location']",
            "div.location-name",
        ]
        data.location = self._extract_text(soup, location_selectors)
        if data.location:
            confidence_score += 10
            data.is_remote = self._detect_remote(data.location)

        # ---------------------------------------------------------------------
        # Job Description
        # ---------------------------------------------------------------------
        description_selectors = [
            "#content",
            ".content",
            "[class*='job-description']",
            "div[class*='description']",
        ]
        data.description = self._extract_text(soup, description_selectors)
        if data.description:
            confidence_score += 30
            if not data.is_remote:
                data.is_remote = self._detect_remote(data.description)
            data.required_skills = self._extract_skills_from_text(data.description)

        data.parse_confidence = min(confidence_score, 100)

        logger.info(
            f"Parsed Greenhouse job: '{data.job_title}' at '{data.company_name}' "
            f"(confidence: {data.parse_confidence}%)"
        )

        return data


# -----------------------------------------------------------------------------
# Lever ATS Parser
# -----------------------------------------------------------------------------
class LeverParser(BaseJobParser):
    """
    Parser for Lever ATS job listings.

    Handles job URLs like:
    - https://jobs.lever.co/company/abc123
    """

    @property
    def source_name(self) -> str:
        return "lever"

    def can_parse(self, url: str, html: str) -> bool:
        """Check if URL is a Lever job posting."""
        return "lever.co" in url.lower()

    def parse(self, html: str, url: str) -> ParsedJobData:
        """Parse Lever ATS job listing HTML."""
        soup = BeautifulSoup(html, "lxml")
        data = ParsedJobData(source_site=self.source_name, raw_html=html)
        confidence_score = 0

        # ---------------------------------------------------------------------
        # Job Title
        # ---------------------------------------------------------------------
        title_selectors = [
            "h2.posting-headline",
            ".posting-headline h2",
            "h2[data-qa='posting-name']",
            "h2",
        ]
        data.job_title = self._extract_text(soup, title_selectors)
        if data.job_title:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Company Name (from URL or page)
        # ---------------------------------------------------------------------
        company_selectors = [
            ".main-header-logo img",
            "[class*='company-name']",
        ]
        # Try getting alt text from logo
        logo = soup.select_one(".main-header-logo img")
        if logo:
            data.company_name = logo.get("alt")

        # Fallback to URL
        if not data.company_name:
            parsed_url = urlparse(url)
            # Format: jobs.lever.co/company/abc123
            parts = parsed_url.path.strip("/").split("/")
            if parts:
                data.company_name = parts[0].replace("-", " ").title()

        if data.company_name:
            confidence_score += 20

        # ---------------------------------------------------------------------
        # Location
        # ---------------------------------------------------------------------
        location_selectors = [
            ".location",
            "[class*='location']",
            ".posting-categories .sort-by-commit",
        ]
        data.location = self._extract_text(soup, location_selectors)
        if data.location:
            confidence_score += 10
            data.is_remote = self._detect_remote(data.location)

        # ---------------------------------------------------------------------
        # Job Description
        # ---------------------------------------------------------------------
        # Lever has sections for description, lists, etc.
        description_parts = []

        sections = soup.select(".section")
        for section in sections:
            section_text = section.get_text(separator="\n", strip=True)
            if section_text:
                description_parts.append(section_text)

        if description_parts:
            data.description = "\n\n".join(description_parts)
            confidence_score += 30
            if not data.is_remote:
                data.is_remote = self._detect_remote(data.description)
            data.required_skills = self._extract_skills_from_text(data.description)

        data.parse_confidence = min(confidence_score, 100)

        logger.info(
            f"Parsed Lever job: '{data.job_title}' at '{data.company_name}' "
            f"(confidence: {data.parse_confidence}%)"
        )

        return data


# -----------------------------------------------------------------------------
# Generic Parser (Fallback)
# -----------------------------------------------------------------------------
class GenericParser(BaseJobParser):
    """
    Generic fallback parser for unknown job boards.

    Uses heuristics and common patterns to extract job data.
    Lower confidence than site-specific parsers.
    """

    @property
    def source_name(self) -> str:
        return "generic"

    def can_parse(self, url: str, html: str) -> bool:
        """Generic parser always returns True as fallback."""
        return True

    def parse(self, html: str, url: str) -> ParsedJobData:
        """
        Parse job listing using generic heuristics.

        Looks for common patterns in job postings:
        - h1 tags for titles
        - Common class names like 'job-title', 'company', 'location'
        - Structured data (JSON-LD) if present
        """
        soup = BeautifulSoup(html, "lxml")
        data = ParsedJobData(source_site=self._detect_source(url), raw_html=html)
        confidence_score = 0

        # ---------------------------------------------------------------------
        # Try JSON-LD structured data first (most reliable)
        # ---------------------------------------------------------------------
        json_ld = self._extract_json_ld(soup)
        if json_ld:
            if json_ld.get("title"):
                data.job_title = json_ld["title"]
                confidence_score += 20
            if json_ld.get("hiringOrganization"):
                data.company_name = json_ld["hiringOrganization"]
                confidence_score += 20
            if json_ld.get("jobLocation"):
                data.location = json_ld["jobLocation"]
                confidence_score += 10
            if json_ld.get("description"):
                data.description = json_ld["description"]
                confidence_score += 30
            if json_ld.get("baseSalary"):
                salary = json_ld["baseSalary"]
                if isinstance(salary, dict):
                    data.salary_min = salary.get("minValue")
                    data.salary_max = salary.get("maxValue")
                    data.salary_currency = salary.get("currency")

        # ---------------------------------------------------------------------
        # Fallback to heuristic parsing
        # ---------------------------------------------------------------------
        if not data.job_title:
            title_selectors = [
                "h1[class*='title']",
                "h1[class*='job']",
                "h1[class*='position']",
                ".job-title h1",
                "h1",
            ]
            data.job_title = self._extract_text(soup, title_selectors)
            if data.job_title:
                confidence_score += 15

        if not data.company_name:
            company_selectors = [
                "[class*='company-name']",
                "[class*='employer']",
                "[class*='organization']",
                "a[class*='company']",
            ]
            data.company_name = self._extract_text(soup, company_selectors)
            if data.company_name:
                confidence_score += 15

        if not data.location:
            location_selectors = [
                "[class*='location']",
                "[class*='address']",
                "[itemprop='jobLocation']",
            ]
            data.location = self._extract_text(soup, location_selectors)
            if data.location:
                confidence_score += 5
                data.is_remote = self._detect_remote(data.location)

        if not data.description:
            description_selectors = [
                "[class*='description']",
                "[class*='job-content']",
                "[itemprop='description']",
                "article",
                ".content",
            ]
            data.description = self._extract_text(soup, description_selectors)
            if data.description:
                confidence_score += 20
                if not data.is_remote:
                    data.is_remote = self._detect_remote(data.description)
                data.required_skills = self._extract_skills_from_text(data.description)

        # Generic parser has lower confidence
        data.parse_confidence = min(confidence_score, 70)
        data.parse_warnings.append("Used generic parser - results may be less accurate")

        logger.info(
            f"Parsed generic job: '{data.job_title}' at '{data.company_name}' "
            f"(confidence: {data.parse_confidence}%)"
        )

        return data

    def _detect_source(self, url: str) -> str:
        """Detect source site from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove common prefixes
        domain = domain.replace("www.", "").replace("jobs.", "")

        # Return cleaned domain
        return domain.split(".")[0] if "." in domain else domain

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[dict[str, Any]]:
        """
        Extract JobPosting structured data from JSON-LD.

        Args:
            soup: BeautifulSoup object.

        Returns:
            Dictionary with extracted job data or None.
        """
        import json

        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle array of items
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "JobPosting":
                            return self._normalize_json_ld(item)
                elif data.get("@type") == "JobPosting":
                    return self._normalize_json_ld(data)

            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        return None

    def _normalize_json_ld(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize JSON-LD JobPosting data to consistent format.

        Args:
            data: Raw JSON-LD data.

        Returns:
            Normalized dictionary.
        """
        result: dict[str, Any] = {}

        result["title"] = data.get("title")

        # Handle hiring organization
        org = data.get("hiringOrganization")
        if isinstance(org, dict):
            result["hiringOrganization"] = org.get("name")
        elif isinstance(org, str):
            result["hiringOrganization"] = org

        # Handle location
        location = data.get("jobLocation")
        if isinstance(location, dict):
            address = location.get("address", {})
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("addressCountry"),
                ]
                result["jobLocation"] = ", ".join(p for p in parts if p)
        elif isinstance(location, list) and location:
            result["jobLocation"] = str(location[0])

        result["description"] = data.get("description")

        # Handle salary
        salary = data.get("baseSalary", {})
        if isinstance(salary, dict):
            value = salary.get("value", {})
            if isinstance(value, dict):
                result["baseSalary"] = {
                    "minValue": value.get("minValue"),
                    "maxValue": value.get("maxValue"),
                    "currency": salary.get("currency"),
                }

        return result


# -----------------------------------------------------------------------------
# Parser Registry
# -----------------------------------------------------------------------------
def get_parsers() -> list[BaseJobParser]:
    """
    Get list of available parsers in priority order.

    Returns:
        List of parser instances, site-specific first, generic last.
    """
    return [
        LinkedInParser(),
        IndeedParser(),
        GreenhouseParser(),
        LeverParser(),
        GenericParser(),  # Always last as fallback
    ]
