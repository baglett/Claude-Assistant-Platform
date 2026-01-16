# =============================================================================
# Generated Resume Service
# =============================================================================
"""
Service layer for generated resume management.

Provides business logic for creating, querying, and managing
generated resume records and their Google Drive references.

Usage:
    from src.services.resume.generated_resume_service import GeneratedResumeService

    async with get_session() as session:
        service = GeneratedResumeService(session)
        resume = await service.create(profile_id, GeneratedResumeCreate(...))
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import GeneratedResume, JobListing
from src.models.resume import (
    GeneratedResumeCreate,
    GeneratedResumeListResponse,
    GeneratedResumeResponse,
    ResumeFormat,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Generated Resume Service Class
# -----------------------------------------------------------------------------
class GeneratedResumeService:
    """
    Service class for generated resume management operations.

    Provides methods for creating, querying, and deleting
    generated resume records.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = GeneratedResumeService(session)

            # Create generated resume record
            resume = await service.create(
                profile_id,
                GeneratedResumeCreate(
                    name="Software_Engineer_Google_2025-01-15",
                    format=ResumeFormat.PDF,
                    skill_match_score=85.5
                )
            )
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the generated resume service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    # -------------------------------------------------------------------------
    # Create Operations
    # -------------------------------------------------------------------------
    async def create(
        self,
        profile_id: UUID,
        data: GeneratedResumeCreate,
    ) -> GeneratedResume:
        """
        Create a new generated resume record.

        Args:
            profile_id: UUID of the profile that owns this resume.
            data: Generated resume creation data.

        Returns:
            Created GeneratedResume ORM instance.

        Example:
            resume = await service.create(
                profile_id,
                GeneratedResumeCreate(
                    name="Software_Engineer_Google_2025-01-15",
                    format=ResumeFormat.PDF,
                    job_listing_id=job_uuid,
                    skill_match_score=85.5,
                    drive_file_id="abc123",
                    drive_file_url="https://drive.google.com/..."
                )
            )
        """
        resume = GeneratedResume(
            profile_id=profile_id,
            job_listing_id=data.job_listing_id,
            name=data.name,
            format=data.format.value,
            drive_file_id=data.drive_file_id,
            drive_file_url=data.drive_file_url,
            drive_folder_id=data.drive_folder_id,
            content_snapshot=data.content_snapshot,
            included_skills=data.included_skills,
            skill_match_score=data.skill_match_score,
            overall_match_score=data.overall_match_score,
            match_analysis=data.match_analysis,
            template_used=data.template_used,
            generation_params=data.generation_params,
            generated_at=datetime.now(timezone.utc),
        )

        self.session.add(resume)
        await self.session.flush()
        await self.session.refresh(resume)

        logger.info(
            f"Created generated resume {resume.id}: "
            f"'{resume.name}' ({resume.format})"
        )

        return resume

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_by_id(
        self,
        resume_id: UUID,
        include_job_listing: bool = False,
    ) -> Optional[GeneratedResume]:
        """
        Get a generated resume by ID.

        Args:
            resume_id: Generated resume UUID to retrieve.
            include_job_listing: Whether to eager-load job listing.

        Returns:
            GeneratedResume instance or None if not found.
        """
        query = select(GeneratedResume).where(GeneratedResume.id == resume_id)

        if include_job_listing:
            query = query.options(selectinload(GeneratedResume.job_listing))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_resumes(
        self,
        profile_id: UUID,
        job_listing_id: Optional[UUID] = None,
        format_filter: Optional[ResumeFormat] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> GeneratedResumeListResponse:
        """
        List generated resumes for a profile with pagination.

        Results are ordered by generated_at descending (most recent first).

        Args:
            profile_id: Profile UUID to list resumes for.
            job_listing_id: Filter by associated job listing.
            format_filter: Filter by output format.
            page: Page number (1-indexed).
            page_size: Number of items per page (max 100).

        Returns:
            GeneratedResumeListResponse with paginated results.

        Example:
            # Get all PDF resumes
            resumes = await service.list_resumes(
                profile_id,
                format_filter=ResumeFormat.PDF
            )
        """
        conditions = [GeneratedResume.profile_id == profile_id]

        if job_listing_id:
            conditions.append(GeneratedResume.job_listing_id == job_listing_id)

        if format_filter:
            conditions.append(GeneratedResume.format == format_filter.value)

        # Count total
        count_query = select(func.count(GeneratedResume.id)).where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch resumes
        query = (
            select(GeneratedResume)
            .where(and_(*conditions))
            .options(selectinload(GeneratedResume.job_listing))
            .order_by(GeneratedResume.generated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        resumes = list(result.scalars().all())

        items = [self._to_response(resume) for resume in resumes]

        return GeneratedResumeListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def get_latest_for_job(
        self,
        profile_id: UUID,
        job_listing_id: UUID,
    ) -> Optional[GeneratedResume]:
        """
        Get the most recent resume generated for a specific job.

        Args:
            profile_id: Profile UUID.
            job_listing_id: Job listing UUID.

        Returns:
            Most recent GeneratedResume for the job or None.
        """
        query = (
            select(GeneratedResume)
            .where(
                GeneratedResume.profile_id == profile_id,
                GeneratedResume.job_listing_id == job_listing_id,
            )
            .order_by(GeneratedResume.generated_at.desc())
            .limit(1)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_resumes_by_match_score(
        self,
        profile_id: UUID,
        min_score: float = 70.0,
        limit: int = 10,
    ) -> list[GeneratedResume]:
        """
        Get resumes with match scores above a threshold.

        Args:
            profile_id: Profile UUID.
            min_score: Minimum skill match score (0-100).
            limit: Maximum number of resumes to return.

        Returns:
            List of GeneratedResume instances ordered by score descending.
        """
        query = (
            select(GeneratedResume)
            .where(
                GeneratedResume.profile_id == profile_id,
                GeneratedResume.skill_match_score >= min_score,
            )
            .order_by(GeneratedResume.skill_match_score.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update_drive_info(
        self,
        resume_id: UUID,
        drive_file_id: str,
        drive_file_url: str,
        drive_folder_id: Optional[str] = None,
    ) -> Optional[GeneratedResume]:
        """
        Update Google Drive information for a resume.

        Args:
            resume_id: Generated resume UUID.
            drive_file_id: Google Drive file ID.
            drive_file_url: Google Drive file URL.
            drive_folder_id: Optional folder ID.

        Returns:
            Updated GeneratedResume instance or None if not found.
        """
        resume = await self.get_by_id(resume_id)
        if not resume:
            return None

        resume.drive_file_id = drive_file_id
        resume.drive_file_url = drive_file_url
        if drive_folder_id:
            resume.drive_folder_id = drive_folder_id

        await self.session.flush()
        await self.session.refresh(resume)

        logger.info(f"Updated Drive info for resume {resume_id}")

        return resume

    async def update_match_analysis(
        self,
        resume_id: UUID,
        skill_match_score: float,
        overall_match_score: float,
        match_analysis: dict[str, Any],
    ) -> Optional[GeneratedResume]:
        """
        Update match analysis for a resume.

        Args:
            resume_id: Generated resume UUID.
            skill_match_score: Skill match percentage.
            overall_match_score: Overall match percentage.
            match_analysis: Detailed analysis data.

        Returns:
            Updated GeneratedResume instance or None if not found.
        """
        resume = await self.get_by_id(resume_id)
        if not resume:
            return None

        resume.skill_match_score = skill_match_score
        resume.overall_match_score = overall_match_score
        resume.match_analysis = match_analysis

        await self.session.flush()
        await self.session.refresh(resume)

        logger.info(f"Updated match analysis for resume {resume_id}")

        return resume

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    async def delete(self, resume_id: UUID) -> bool:
        """
        Delete a generated resume record.

        Note: This only deletes the database record. The actual file
        in Google Drive should be deleted separately via the Drive MCP.

        Args:
            resume_id: Generated resume UUID to delete.

        Returns:
            True if deleted, False if not found.
        """
        resume = await self.get_by_id(resume_id)
        if not resume:
            return False

        drive_file_id = resume.drive_file_id  # Save for logging

        await self.session.delete(resume)
        await self.session.flush()

        logger.info(
            f"Deleted generated resume {resume_id} "
            f"(Drive file ID: {drive_file_id})"
        )

        return True

    # -------------------------------------------------------------------------
    # Statistics Operations
    # -------------------------------------------------------------------------
    async def get_generation_count(
        self,
        profile_id: UUID,
    ) -> int:
        """
        Get total count of generated resumes for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            Total count of generated resumes.
        """
        query = select(func.count(GeneratedResume.id)).where(
            GeneratedResume.profile_id == profile_id
        )

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_format_breakdown(
        self,
        profile_id: UUID,
    ) -> dict[str, int]:
        """
        Get count of resumes by format.

        Args:
            profile_id: Profile UUID.

        Returns:
            Dictionary mapping format to count.
        """
        query = (
            select(GeneratedResume.format, func.count(GeneratedResume.id))
            .where(GeneratedResume.profile_id == profile_id)
            .group_by(GeneratedResume.format)
        )

        result = await self.session.execute(query)
        return dict(result.all())

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, resume: GeneratedResume) -> GeneratedResumeResponse:
        """
        Convert a GeneratedResume ORM instance to a GeneratedResumeResponse.

        Args:
            resume: GeneratedResume ORM instance to convert.

        Returns:
            GeneratedResumeResponse Pydantic model.
        """
        return GeneratedResumeResponse(
            id=resume.id,
            profile_id=resume.profile_id,
            job_listing_id=resume.job_listing_id,
            name=resume.name,
            format=ResumeFormat(resume.format),
            drive_file_id=resume.drive_file_id,
            drive_file_url=resume.drive_file_url,
            drive_folder_id=resume.drive_folder_id,
            content_snapshot=resume.content_snapshot,
            included_skills=resume.included_skills,
            skill_match_score=resume.skill_match_score,
            overall_match_score=resume.overall_match_score,
            match_analysis=resume.match_analysis,
            template_used=resume.template_used,
            generation_params=resume.generation_params,
            generated_at=resume.generated_at,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )
