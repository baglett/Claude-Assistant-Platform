# =============================================================================
# Work Experience Service
# =============================================================================
"""
Service layer for work experience management.

Provides business logic for creating, updating, querying, and managing
work experience entries for resume generation.

Usage:
    from src.services.resume.work_experience_service import WorkExperienceService

    async with get_session() as session:
        service = WorkExperienceService(session)
        exp = await service.create(profile_id, WorkExperienceCreate(...))
"""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import WorkExperience
from src.models.resume import (
    EmploymentType,
    WorkExperienceCreate,
    WorkExperienceListResponse,
    WorkExperienceResponse,
    WorkExperienceUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Work Experience Service Class
# -----------------------------------------------------------------------------
class WorkExperienceService:
    """
    Service class for work experience management operations.

    Provides methods for creating, updating, querying, and deleting
    work experience entries.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = WorkExperienceService(session)

            # Create work experience
            exp = await service.create(
                profile_id,
                WorkExperienceCreate(
                    company_name="Tech Corp",
                    job_title="Senior Engineer",
                    start_date=date(2020, 1, 1),
                    is_current=True
                )
            )
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the work experience service.

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
        data: WorkExperienceCreate,
    ) -> WorkExperience:
        """
        Create a new work experience entry.

        Args:
            profile_id: UUID of the profile to associate with.
            data: Work experience creation data.

        Returns:
            Created WorkExperience ORM instance.

        Example:
            exp = await service.create(
                profile_id,
                WorkExperienceCreate(
                    company_name="Tech Corp",
                    job_title="Senior Software Engineer",
                    start_date=date(2020, 1, 15),
                    is_current=True,
                    achievements=["Led team of 5", "Reduced latency by 40%"]
                )
            )
        """
        experience = WorkExperience(
            profile_id=profile_id,
            company_name=data.company_name,
            company_url=data.company_url,
            company_location=data.company_location,
            job_title=data.job_title,
            employment_type=data.employment_type.value,
            start_date=data.start_date,
            end_date=data.end_date,
            is_current=data.is_current,
            description=data.description,
            achievements=data.achievements,
            skills_used=data.skills_used,
            display_order=data.display_order,
        )

        self.session.add(experience)
        await self.session.flush()
        await self.session.refresh(experience)

        logger.info(
            f"Created work experience {experience.id}: "
            f"'{experience.job_title}' at '{experience.company_name}'"
        )

        return experience

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_by_id(self, experience_id: UUID) -> Optional[WorkExperience]:
        """
        Get a work experience by ID.

        Args:
            experience_id: Work experience UUID to retrieve.

        Returns:
            WorkExperience instance or None if not found.
        """
        query = select(WorkExperience).where(WorkExperience.id == experience_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_experiences(
        self,
        profile_id: UUID,
        employment_type: Optional[EmploymentType] = None,
        is_current: Optional[bool] = None,
    ) -> WorkExperienceListResponse:
        """
        List work experiences for a profile with optional filtering.

        Results are ordered by start_date descending (most recent first).

        Args:
            profile_id: Profile UUID to list experiences for.
            employment_type: Filter by employment type.
            is_current: Filter by current position status.

        Returns:
            WorkExperienceListResponse with all matching experiences.

        Example:
            # Get all current positions
            experiences = await service.list_experiences(
                profile_id,
                is_current=True
            )
        """
        conditions = [WorkExperience.profile_id == profile_id]

        if employment_type:
            conditions.append(WorkExperience.employment_type == employment_type.value)

        if is_current is not None:
            conditions.append(WorkExperience.is_current == is_current)

        # Count total
        count_query = select(func.count(WorkExperience.id)).where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch experiences
        query = (
            select(WorkExperience)
            .where(and_(*conditions))
            .order_by(WorkExperience.start_date.desc())
        )

        result = await self.session.execute(query)
        experiences = list(result.scalars().all())

        items = [self._to_response(exp) for exp in experiences]

        return WorkExperienceListResponse(items=items, total=total)

    async def get_current_position(
        self,
        profile_id: UUID,
    ) -> Optional[WorkExperience]:
        """
        Get the current position for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            Current WorkExperience instance or None if no current position.
        """
        query = (
            select(WorkExperience)
            .where(
                WorkExperience.profile_id == profile_id,
                WorkExperience.is_current == True,  # noqa: E712
            )
            .order_by(WorkExperience.start_date.desc())
            .limit(1)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update(
        self,
        experience_id: UUID,
        data: WorkExperienceUpdate,
    ) -> Optional[WorkExperience]:
        """
        Update an existing work experience.

        Only fields provided in the update data are modified.

        Args:
            experience_id: Work experience UUID to update.
            data: Fields to update (only non-None fields are applied).

        Returns:
            Updated WorkExperience instance or None if not found.

        Example:
            exp = await service.update(
                experience_id,
                WorkExperienceUpdate(is_current=False, end_date=date.today())
            )
        """
        experience = await self.get_by_id(experience_id)
        if not experience:
            return None

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Convert enums to their values for database storage
            if field == "employment_type" and value is not None:
                value = value.value

            setattr(experience, field, value)

        await self.session.flush()
        await self.session.refresh(experience)

        logger.info(f"Updated work experience {experience_id}: {list(update_data.keys())}")

        return experience

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    async def delete(self, experience_id: UUID) -> bool:
        """
        Delete a work experience.

        Args:
            experience_id: Work experience UUID to delete.

        Returns:
            True if deleted, False if not found.
        """
        experience = await self.get_by_id(experience_id)
        if not experience:
            return False

        await self.session.delete(experience)
        await self.session.flush()

        logger.info(f"Deleted work experience {experience_id}")

        return True

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, experience: WorkExperience) -> WorkExperienceResponse:
        """
        Convert a WorkExperience ORM instance to a WorkExperienceResponse.

        Args:
            experience: WorkExperience ORM instance to convert.

        Returns:
            WorkExperienceResponse Pydantic model.
        """
        return WorkExperienceResponse(
            id=experience.id,
            profile_id=experience.profile_id,
            company_name=experience.company_name,
            company_url=experience.company_url,
            company_location=experience.company_location,
            job_title=experience.job_title,
            employment_type=EmploymentType(experience.employment_type),
            start_date=experience.start_date,
            end_date=experience.end_date,
            is_current=experience.is_current,
            description=experience.description,
            achievements=experience.achievements,
            skills_used=experience.skills_used,
            display_order=experience.display_order,
            created_at=experience.created_at,
            updated_at=experience.updated_at,
        )
