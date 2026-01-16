# =============================================================================
# Job Scraper Service Package
# =============================================================================
"""
Job scraper service for extracting job listing data from various job boards.

Provides functionality to scrape and parse job listings from:
- LinkedIn Jobs
- Indeed
- Greenhouse (ATS)
- Lever (ATS)
- Generic websites (Claude-assisted parsing)

Usage:
    from src.services.scraper import JobScraperService

    scraper = JobScraperService()
    job_data = await scraper.scrape_job("https://linkedin.com/jobs/view/123456")
"""

from src.services.scraper.service import JobScraperService

__all__ = ["JobScraperService"]
