# =============================================================================
# Education Service
# =============================================================================
"""
Service layer for education management.

Provides business logic for creating, updating, querying, and managing
education entries for resume generation.

Usage:
    from src.services.resume.education_service import EducationService

    async with get_session() as session:
        service = EducationService(session)
        edu = await service.create(profile_id, EducationCreate(...))
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Education
from src.models.resume import (
    DegreeType,
    EducationCreate,
    EducationListResponse,
    EducationResponse,
    EducationUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Education Service Class
# -----------------------------------------------------------------------------
class EducationService:
    """
    Service class for education management operations.

    Provides methods for creating, updating, querying, and deleting
    education entries.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = EducationService(session)

            # Create education entry
            edu = await service.create(
                profile_id,
                EducationCreate(
                    institution_name="Stanford University",
                    degree_type=DegreeType.BACHELOR,
                    field_of_study="Computer Science"
                )
            )
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the education service.

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
        data: EducationCreate,
    ) -> Education:
        """
        Create a new education entry.

        Args:
            profile_id: UUID of the profile to associate with.
            data: Education creation data.

        Returns:
            Created Education ORM instance.

        Example:
            edu = await service.create(
                profile_id,
                EducationCreate(
                    institution_name="Stanford University",
                    degree_type=DegreeType.BACHELOR,
                    field_of_study="Computer Science",
                    gpa=3.8,
                    honors=["Magna Cum Laude"]
                )
            )
        """
        education = Education(
            profile_id=profile_id,
            institution_name=data.institution_name,
            institution_location=data.institution_location,
            institution_url=data.institution_url,
            degree_type=data.degree_type.value,
            degree_name=data.degree_name,
            field_of_study=data.field_of_study,
            start_date=data.start_date,
            end_date=data.end_date,
            is_in_progress=data.is_in_progress,
            gpa=data.gpa,
            gpa_scale=data.gpa_scale,
            honors=data.honors,
            relevant_coursework=data.relevant_coursework,
            activities=data.activities,
            display_order=data.display_order,
        )

        self.session.add(education)
        await self.session.flush()
        await self.session.refresh(education)

        logger.info(
            f"Created education {education.id}: "
            f"'{education.degree_type}' in '{education.field_of_study}' "
            f"at '{education.institution_name}'"
        )

        return education

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_by_id(self, education_id: UUID) -> Optional[Education]:
        """
        Get an education entry by ID.

        Args:
            education_id: Education UUID to retrieve.

        Returns:
            Education instance or None if not found.
        """
        query = select(Education).where(Education.id == education_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_education(
        self,
        profile_id: UUID,
        degree_type: Optional[DegreeType] = None,
        is_in_progress: Optional[bool] = None,
    ) -> EducationListResponse:
        """
        List education entries for a profile with optional filtering.

        Results are ordered by end_date descending (most recent first).

        Args:
            profile_id: Profile UUID to list education for.
            degree_type: Filter by degree type.
            is_in_progress: Filter by in-progress status.

        Returns:
            EducationListResponse with all matching entries.

        Example:
            # Get all completed bachelor's degrees
            education = await service.list_education(
                profile_id,
                degree_type=DegreeType.BACHELOR,
                is_in_progress=False
            )
        """
        conditions = [Education.profile_id == profile_id]

        if degree_type:
            conditions.append(Education.degree_type == degree_type.value)

        if is_in_progress is not None:
            conditions.append(Education.is_in_progress == is_in_progress)

        # Count total
        count_query = select(func.count(Education.id)).where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch education entries
        query = (
            select(Education)
            .where(and_(*conditions))
            .order_by(Education.end_date.desc().nullsfirst())
        )

        result = await self.session.execute(query)
        entries = list(result.scalars().all())

        items = [self._to_response(edu) for edu in entries]

        return EducationListResponse(items=items, total=total)

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update(
        self,
        education_id: UUID,
        data: EducationUpdate,
    ) -> Optional[Education]:
        """
        Update an existing education entry.

        Only fields provided in the update data are modified.

        Args:
            education_id: Education UUID to update.
            data: Fields to update (only non-None fields are applied).

        Returns:
            Updated Education instance or None if not found.

        Example:
            edu = await service.update(
                education_id,
                EducationUpdate(gpa=3.9)
            )
        """
        education = await self.get_by_id(education_id)
        if not education:
            return None

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Convert enums to their values for database storage
            if field == "degree_type" and value is not None:
                value = value.value

            setattr(education, field, value)

        await self.session.flush()
        await self.session.refresh(education)

        logger.info(f"Updated education {education_id}: {list(update_data.keys())}")

        return education

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    async def delete(self, education_id: UUID) -> bool:
        """
        Delete an education entry.

        Args:
            education_id: Education UUID to delete.

        Returns:
            True if deleted, False if not found.
        """
        education = await self.get_by_id(education_id)
        if not education:
            return False

        await self.session.delete(education)
        await self.session.flush()

        logger.info(f"Deleted education {education_id}")

        return True

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, education: Education) -> EducationResponse:
        """
        Convert an Education ORM instance to an EducationResponse.

        Args:
            education: Education ORM instance to convert.

        Returns:
            EducationResponse Pydantic model.
        """
        return EducationResponse(
            id=education.id,
            profile_id=education.profile_id,
            institution_name=education.institution_name,
            institution_location=education.institution_location,
            institution_url=education.institution_url,
            degree_type=DegreeType(education.degree_type),
            degree_name=education.degree_name,
            field_of_study=education.field_of_study,
            start_date=education.start_date,
            end_date=education.end_date,
            is_in_progress=education.is_in_progress,
            gpa=education.gpa,
            gpa_scale=education.gpa_scale,
            honors=education.honors,
            relevant_coursework=education.relevant_coursework,
            activities=education.activities,
            display_order=education.display_order,
            created_at=education.created_at,
            updated_at=education.updated_at,
        )
