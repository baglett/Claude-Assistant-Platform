# =============================================================================
# Profile Service
# =============================================================================
"""
Service layer for user profile management.

Provides business logic for creating, updating, and retrieving user profiles
for resume generation. Single-user system - assumes one profile per instance.

Usage:
    from src.services.resume.profile_service import ProfileService

    async with get_session() as session:
        service = ProfileService(session)
        profile = await service.get_or_create_profile()
"""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import (
    Certification,
    Education,
    GeneratedResume,
    JobListing,
    Skill,
    UserProfile,
    WorkExperience,
)
from src.models.resume import (
    ProfileCreate,
    ProfileResponse,
    ProfileStats,
    ProfileUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Profile Service Class
# -----------------------------------------------------------------------------
class ProfileService:
    """
    Service class for user profile management.

    Handles profile CRUD operations and statistics calculation.
    Single-user system - most operations work with "the" profile.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = ProfileService(session)
            profile = await service.get_or_create_profile()
            stats = await service.get_profile_stats(profile.id)
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the profile service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_profile(self) -> Optional[UserProfile]:
        """
        Get the user profile.

        Since this is a single-user system, returns the first profile found.
        Use get_or_create_profile() if you need to ensure a profile exists.

        Returns:
            UserProfile instance or None if no profile exists.

        Example:
            profile = await service.get_profile()
            if profile:
                print(f"Profile: {profile.full_name}")
        """
        query = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.work_experiences),
                selectinload(UserProfile.education_entries),
                selectinload(UserProfile.certifications),
            )
            .limit(1)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_profile_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        """
        Get a profile by its ID.

        Args:
            profile_id: Profile UUID to retrieve.

        Returns:
            UserProfile instance or None if not found.
        """
        query = (
            select(UserProfile)
            .where(UserProfile.id == profile_id)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.work_experiences),
                selectinload(UserProfile.education_entries),
                selectinload(UserProfile.certifications),
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create_profile(
        self,
        default_data: Optional[ProfileCreate] = None,
    ) -> UserProfile:
        """
        Get the existing profile or create a new one.

        If no profile exists and no default_data is provided, creates a
        placeholder profile that should be updated with real information.

        Args:
            default_data: Optional profile data for creation.

        Returns:
            Existing or newly created UserProfile instance.

        Example:
            profile = await service.get_or_create_profile(
                ProfileCreate(
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com"
                )
            )
        """
        profile = await self.get_profile()

        if profile:
            return profile

        # Create new profile with provided data or placeholder
        if default_data:
            profile = UserProfile(
                first_name=default_data.first_name,
                last_name=default_data.last_name,
                email=default_data.email,
                phone=default_data.phone,
                city=default_data.city,
                state=default_data.state,
                country=default_data.country,
                linkedin_url=default_data.linkedin_url,
                github_url=default_data.github_url,
                portfolio_url=default_data.portfolio_url,
                personal_website=default_data.personal_website,
                professional_summary=default_data.professional_summary,
                profile_metadata=default_data.metadata,
            )
        else:
            # Create placeholder profile
            profile = UserProfile(
                first_name="User",
                last_name="Profile",
                email="user@example.com",
                country="United States",
                profile_metadata={"placeholder": True},
            )

        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)

        logger.info(f"Created profile {profile.id}: {profile.full_name}")

        return profile

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update_profile(
        self,
        data: ProfileUpdate,
        profile_id: Optional[UUID] = None,
    ) -> Optional[UserProfile]:
        """
        Update the user profile.

        Only fields provided in the update data are modified.

        Args:
            data: Fields to update (only non-None fields are applied).
            profile_id: Optional specific profile ID to update.

        Returns:
            Updated UserProfile instance or None if not found.

        Example:
            profile = await service.update_profile(
                ProfileUpdate(professional_summary="Updated summary")
            )
        """
        if profile_id:
            profile = await self.get_profile_by_id(profile_id)
        else:
            profile = await self.get_profile()

        if not profile:
            return None

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Map metadata field name
            if field == "metadata":
                field = "profile_metadata"
            setattr(profile, field, value)

        await self.session.flush()
        await self.session.refresh(profile)

        logger.info(f"Updated profile {profile.id}: {list(update_data.keys())}")

        return profile

    # -------------------------------------------------------------------------
    # Statistics Operations
    # -------------------------------------------------------------------------
    async def get_profile_stats(
        self,
        profile_id: Optional[UUID] = None,
    ) -> ProfileStats:
        """
        Get aggregated profile statistics.

        Calculates counts and totals for dashboard display.

        Args:
            profile_id: Optional profile ID (uses first profile if not specified).

        Returns:
            ProfileStats with aggregate counts.

        Example:
            stats = await service.get_profile_stats()
            print(f"Total skills: {stats.total_skills}")
            print(f"Total experience: {stats.total_work_experience_years} years")
        """
        if profile_id:
            profile = await self.get_profile_by_id(profile_id)
        else:
            profile = await self.get_profile()

        if not profile:
            # Return empty stats if no profile
            return ProfileStats(
                total_skills=0,
                skills_by_category={},
                total_work_experience_years=Decimal("0"),
                total_positions=0,
                total_education=0,
                total_certifications=0,
                active_certifications=0,
                total_generated_resumes=0,
                total_job_listings=0,
            )

        pid = profile.id

        # Count skills by category
        skills_query = (
            select(Skill.category, func.count(Skill.id))
            .where(Skill.profile_id == pid)
            .group_by(Skill.category)
        )
        skills_result = await self.session.execute(skills_query)
        skills_by_category = dict(skills_result.all())
        total_skills = sum(skills_by_category.values())

        # Count work experience positions and calculate total years
        work_query = select(WorkExperience).where(WorkExperience.profile_id == pid)
        work_result = await self.session.execute(work_query)
        work_experiences = list(work_result.scalars().all())
        total_positions = len(work_experiences)

        # Calculate total years of experience
        total_years = Decimal("0")
        for exp in work_experiences:
            if exp.start_date:
                end = exp.end_date or exp.start_date  # Use start if no end (current job)
                from datetime import date

                if exp.is_current:
                    end = date.today()
                years = Decimal((end - exp.start_date).days) / Decimal("365.25")
                total_years += max(years, Decimal("0"))

        # Count education entries
        edu_query = select(func.count(Education.id)).where(Education.profile_id == pid)
        edu_result = await self.session.execute(edu_query)
        total_education = edu_result.scalar_one()

        # Count certifications (total and active)
        cert_query = select(func.count(Certification.id)).where(
            Certification.profile_id == pid
        )
        cert_result = await self.session.execute(cert_query)
        total_certifications = cert_result.scalar_one()

        active_cert_query = select(func.count(Certification.id)).where(
            Certification.profile_id == pid,
            Certification.is_active == True,  # noqa: E712
        )
        active_cert_result = await self.session.execute(active_cert_query)
        active_certifications = active_cert_result.scalar_one()

        # Count generated resumes
        resume_query = select(func.count(GeneratedResume.id)).where(
            GeneratedResume.profile_id == pid
        )
        resume_result = await self.session.execute(resume_query)
        total_generated_resumes = resume_result.scalar_one()

        # Count job listings (all, not profile-specific)
        job_query = select(func.count(JobListing.id))
        job_result = await self.session.execute(job_query)
        total_job_listings = job_result.scalar_one()

        return ProfileStats(
            total_skills=total_skills,
            skills_by_category=skills_by_category,
            total_work_experience_years=round(total_years, 1),
            total_positions=total_positions,
            total_education=total_education,
            total_certifications=total_certifications,
            active_certifications=active_certifications,
            total_generated_resumes=total_generated_resumes,
            total_job_listings=total_job_listings,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, profile: UserProfile) -> ProfileResponse:
        """
        Convert a UserProfile ORM instance to a ProfileResponse.

        Args:
            profile: UserProfile ORM instance to convert.

        Returns:
            ProfileResponse Pydantic model.
        """
        return ProfileResponse(
            id=profile.id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            email=profile.email,
            phone=profile.phone,
            city=profile.city,
            state=profile.state,
            country=profile.country,
            linkedin_url=profile.linkedin_url,
            github_url=profile.github_url,
            portfolio_url=profile.portfolio_url,
            personal_website=profile.personal_website,
            professional_summary=profile.professional_summary,
            telegram_user_id=profile.telegram_user_id,
            metadata=profile.profile_metadata,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
