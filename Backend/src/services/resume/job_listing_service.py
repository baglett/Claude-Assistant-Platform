# =============================================================================
# Job Listing Service
# =============================================================================
"""
Service layer for job listing management.

Provides business logic for creating, updating, querying, and managing
scraped job listings for resume tailoring.

Usage:
    from src.services.resume.job_listing_service import JobListingService

    async with get_session() as session:
        service = JobListingService(session)
        listing = await service.create(JobListingCreate(...))
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import JobListing
from src.models.resume import (
    ApplicationStatus,
    JobListingCreate,
    JobListingListResponse,
    JobListingResponse,
    JobListingUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Job Listing Service Class
# -----------------------------------------------------------------------------
class JobListingService:
    """
    Service class for job listing management operations.

    Provides methods for creating, updating, querying, and deleting
    job listings.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = JobListingService(session)

            # Create job listing
            listing = await service.create(
                JobListingCreate(
                    url="https://linkedin.com/jobs/view/123456",
                    job_title="Senior Software Engineer",
                    company_name="Tech Corp",
                    description="..."
                )
            )
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the job listing service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    # -------------------------------------------------------------------------
    # Create Operations
    # -------------------------------------------------------------------------
    async def create(
        self,
        data: JobListingCreate,
    ) -> JobListing:
        """
        Create a new job listing.

        Args:
            data: Job listing creation data.

        Returns:
            Created JobListing ORM instance.

        Raises:
            ValueError: If a listing with the same URL already exists.

        Example:
            listing = await service.create(
                JobListingCreate(
                    url="https://linkedin.com/jobs/view/123456",
                    job_title="Senior Software Engineer",
                    company_name="Tech Corp",
                    description="We are looking for...",
                    required_skills=["Python", "AWS"]
                )
            )
        """
        # Check for duplicate URL
        existing = await self.get_by_url(data.url)
        if existing:
            raise ValueError(f"Job listing with URL already exists: {data.url}")

        listing = JobListing(
            url=data.url,
            source_site=data.source_site,
            job_title=data.job_title,
            company_name=data.company_name,
            company_url=data.company_url,
            location=data.location,
            is_remote=data.is_remote,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_currency=data.salary_currency,
            description=data.description,
            required_skills=data.required_skills,
            preferred_skills=data.preferred_skills,
            requirements=data.requirements,
            raw_html=data.raw_html,
            notes=data.notes,
            scraped_at=datetime.now(timezone.utc),
        )

        self.session.add(listing)
        await self.session.flush()
        await self.session.refresh(listing)

        logger.info(
            f"Created job listing {listing.id}: "
            f"'{listing.job_title}' at '{listing.company_name}'"
        )

        return listing

    async def create_or_update(
        self,
        data: JobListingCreate,
    ) -> tuple[JobListing, bool]:
        """
        Create a new job listing or update existing one by URL.

        Args:
            data: Job listing data.

        Returns:
            Tuple of (JobListing, created) where created is True if new.

        Example:
            listing, created = await service.create_or_update(
                JobListingCreate(url="...", ...)
            )
            if created:
                print("New listing created")
            else:
                print("Existing listing updated")
        """
        existing = await self.get_by_url(data.url)

        if existing:
            # Update existing listing
            existing.job_title = data.job_title
            existing.company_name = data.company_name
            existing.company_url = data.company_url
            existing.location = data.location
            existing.is_remote = data.is_remote
            existing.salary_min = data.salary_min
            existing.salary_max = data.salary_max
            existing.salary_currency = data.salary_currency
            existing.description = data.description
            existing.required_skills = data.required_skills
            existing.preferred_skills = data.preferred_skills
            existing.requirements = data.requirements
            existing.raw_html = data.raw_html
            existing.scraped_at = datetime.now(timezone.utc)

            await self.session.flush()
            await self.session.refresh(existing)

            logger.info(f"Updated job listing {existing.id}")

            return existing, False

        # Create new listing
        listing = await self.create(data)
        return listing, True

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_by_id(self, listing_id: UUID) -> Optional[JobListing]:
        """
        Get a job listing by ID.

        Args:
            listing_id: Job listing UUID to retrieve.

        Returns:
            JobListing instance or None if not found.
        """
        query = select(JobListing).where(JobListing.id == listing_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_url(self, url: str) -> Optional[JobListing]:
        """
        Get a job listing by URL.

        Args:
            url: Job listing URL.

        Returns:
            JobListing instance or None if not found.
        """
        query = select(JobListing).where(JobListing.url == url)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_listings(
        self,
        company_name: Optional[str] = None,
        source_site: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        application_status: Optional[ApplicationStatus] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> JobListingListResponse:
        """
        List job listings with filtering and pagination.

        Results are ordered by scraped_at descending (most recent first).

        Args:
            company_name: Filter by company name (case-insensitive partial match).
            source_site: Filter by source site.
            is_favorite: Filter by favorite status.
            application_status: Filter by application status.
            search_query: Search in title, company, and description.
            page: Page number (1-indexed).
            page_size: Number of items per page (max 100).

        Returns:
            JobListingListResponse with paginated results.

        Example:
            # Get all favorite listings
            listings = await service.list_listings(is_favorite=True)

            # Search for Python jobs
            listings = await service.list_listings(search_query="Python")
        """
        conditions = []

        if company_name:
            conditions.append(
                func.lower(JobListing.company_name).like(f"%{company_name.lower()}%")
            )

        if source_site:
            conditions.append(JobListing.source_site == source_site)

        if is_favorite is not None:
            conditions.append(JobListing.is_favorite == is_favorite)

        if application_status:
            conditions.append(JobListing.application_status == application_status.value)

        if search_query:
            search_term = f"%{search_query.lower()}%"
            conditions.append(
                or_(
                    func.lower(JobListing.job_title).like(search_term),
                    func.lower(JobListing.company_name).like(search_term),
                    func.lower(JobListing.description).like(search_term),
                )
            )

        # Count total
        count_query = select(func.count(JobListing.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch listings
        query = select(JobListing).order_by(JobListing.scraped_at.desc())

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        listings = list(result.scalars().all())

        items = [self._to_response(listing) for listing in listings]

        return JobListingListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def get_recent_listings(
        self,
        limit: int = 10,
    ) -> list[JobListing]:
        """
        Get the most recently scraped job listings.

        Args:
            limit: Maximum number of listings to return.

        Returns:
            List of JobListing instances.
        """
        query = (
            select(JobListing)
            .order_by(JobListing.scraped_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update(
        self,
        listing_id: UUID,
        data: JobListingUpdate,
    ) -> Optional[JobListing]:
        """
        Update an existing job listing.

        Only fields provided in the update data are modified.

        Args:
            listing_id: Job listing UUID to update.
            data: Fields to update (only non-None fields are applied).

        Returns:
            Updated JobListing instance or None if not found.

        Example:
            listing = await service.update(
                listing_id,
                JobListingUpdate(is_favorite=True, notes="Great opportunity")
            )
        """
        listing = await self.get_by_id(listing_id)
        if not listing:
            return None

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Convert enums to their values for database storage
            if field == "application_status" and value is not None:
                value = value.value

            setattr(listing, field, value)

        await self.session.flush()
        await self.session.refresh(listing)

        logger.info(f"Updated job listing {listing_id}: {list(update_data.keys())}")

        return listing

    async def mark_applied(
        self,
        listing_id: UUID,
        applied_at: Optional[datetime] = None,
    ) -> Optional[JobListing]:
        """
        Mark a job listing as applied.

        Args:
            listing_id: Job listing UUID.
            applied_at: When the application was submitted (defaults to now).

        Returns:
            Updated JobListing instance or None if not found.
        """
        listing = await self.get_by_id(listing_id)
        if not listing:
            return None

        listing.application_status = "applied"
        listing.applied_at = applied_at or datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(listing)

        logger.info(f"Marked job listing {listing_id} as applied")

        return listing

    async def toggle_favorite(
        self,
        listing_id: UUID,
    ) -> Optional[JobListing]:
        """
        Toggle the favorite status of a job listing.

        Args:
            listing_id: Job listing UUID.

        Returns:
            Updated JobListing instance or None if not found.
        """
        listing = await self.get_by_id(listing_id)
        if not listing:
            return None

        listing.is_favorite = not listing.is_favorite

        await self.session.flush()
        await self.session.refresh(listing)

        logger.info(
            f"Toggled favorite for job listing {listing_id}: "
            f"now {'favorited' if listing.is_favorite else 'unfavorited'}"
        )

        return listing

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    async def delete(self, listing_id: UUID) -> bool:
        """
        Delete a job listing.

        Args:
            listing_id: Job listing UUID to delete.

        Returns:
            True if deleted, False if not found.
        """
        listing = await self.get_by_id(listing_id)
        if not listing:
            return False

        await self.session.delete(listing)
        await self.session.flush()

        logger.info(f"Deleted job listing {listing_id}")

        return True

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, listing: JobListing) -> JobListingResponse:
        """
        Convert a JobListing ORM instance to a JobListingResponse.

        Args:
            listing: JobListing ORM instance to convert.

        Returns:
            JobListingResponse Pydantic model.
        """
        return JobListingResponse(
            id=listing.id,
            url=listing.url,
            source_site=listing.source_site,
            job_title=listing.job_title,
            company_name=listing.company_name,
            company_url=listing.company_url,
            location=listing.location,
            is_remote=listing.is_remote,
            salary_min=listing.salary_min,
            salary_max=listing.salary_max,
            salary_currency=listing.salary_currency,
            description=listing.description,
            required_skills=listing.required_skills,
            preferred_skills=listing.preferred_skills,
            requirements=listing.requirements,
            scraped_at=listing.scraped_at,
            notes=listing.notes,
            is_favorite=listing.is_favorite,
            application_status=listing.application_status,
            applied_at=listing.applied_at,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )
