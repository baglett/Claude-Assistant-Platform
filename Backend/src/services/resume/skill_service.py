# =============================================================================
# Skill Service
# =============================================================================
"""
Service layer for skill management.

Provides business logic for creating, updating, querying, and managing
skills for resume generation and job matching.

Usage:
    from src.services.resume.skill_service import SkillService

    async with get_session() as session:
        service = SkillService(session)
        skill = await service.create(profile_id, SkillCreate(name="Python"))
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Skill
from src.models.resume import (
    SkillCategory,
    SkillCreate,
    SkillListResponse,
    SkillProficiency,
    SkillResponse,
    SkillUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Skill Service Class
# -----------------------------------------------------------------------------
class SkillService:
    """
    Service class for skill management operations.

    Provides methods for creating, updating, querying, and deleting skills.
    Skills are associated with a user profile and used for resume generation.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = SkillService(session)

            # Create a skill
            skill = await service.create(
                profile_id,
                SkillCreate(name="Python", category=SkillCategory.PROGRAMMING_LANGUAGE)
            )

            # List all skills for a profile
            skills = await service.list_skills(profile_id)
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the skill service.

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
        data: SkillCreate,
    ) -> Skill:
        """
        Create a new skill.

        Args:
            profile_id: UUID of the profile to associate the skill with.
            data: Skill creation data from API request.

        Returns:
            Created Skill ORM instance.

        Raises:
            ValueError: If a skill with the same name already exists for the profile.

        Example:
            skill = await service.create(
                profile_id,
                SkillCreate(
                    name="Python",
                    category=SkillCategory.PROGRAMMING_LANGUAGE,
                    proficiency=SkillProficiency.EXPERT,
                    years_experience=8.0,
                    is_featured=True
                )
            )
        """
        # Check for duplicate skill name
        existing = await self._get_by_name(profile_id, data.name)
        if existing:
            raise ValueError(f"Skill '{data.name}' already exists for this profile")

        skill = Skill(
            profile_id=profile_id,
            name=data.name,
            category=data.category.value,
            proficiency=data.proficiency.value,
            years_experience=data.years_experience,
            keywords=data.keywords,
            display_order=data.display_order,
            is_featured=data.is_featured,
        )

        self.session.add(skill)
        await self.session.flush()
        await self.session.refresh(skill)

        logger.info(
            f"Created skill {skill.id}: '{skill.name}' "
            f"(category={skill.category}, proficiency={skill.proficiency})"
        )

        return skill

    async def create_many(
        self,
        profile_id: UUID,
        skills_data: list[SkillCreate],
    ) -> list[Skill]:
        """
        Create multiple skills at once.

        Skips skills that already exist (by name).

        Args:
            profile_id: UUID of the profile to associate skills with.
            skills_data: List of skill creation data.

        Returns:
            List of created Skill ORM instances.

        Example:
            skills = await service.create_many(
                profile_id,
                [
                    SkillCreate(name="Python", category=SkillCategory.PROGRAMMING_LANGUAGE),
                    SkillCreate(name="JavaScript", category=SkillCategory.PROGRAMMING_LANGUAGE),
                ]
            )
        """
        created_skills = []

        for data in skills_data:
            try:
                skill = await self.create(profile_id, data)
                created_skills.append(skill)
            except ValueError as e:
                logger.warning(f"Skipping skill creation: {e}")
                continue

        return created_skills

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_by_id(self, skill_id: UUID) -> Optional[Skill]:
        """
        Get a skill by ID.

        Args:
            skill_id: Skill UUID to retrieve.

        Returns:
            Skill instance or None if not found.
        """
        query = select(Skill).where(Skill.id == skill_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_by_name(
        self,
        profile_id: UUID,
        name: str,
    ) -> Optional[Skill]:
        """
        Get a skill by name for a specific profile.

        Args:
            profile_id: Profile UUID.
            name: Skill name (case-insensitive).

        Returns:
            Skill instance or None if not found.
        """
        query = select(Skill).where(
            Skill.profile_id == profile_id,
            func.lower(Skill.name) == name.lower(),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_skills(
        self,
        profile_id: UUID,
        category: Optional[SkillCategory] = None,
        proficiency: Optional[SkillProficiency] = None,
        is_featured: Optional[bool] = None,
    ) -> SkillListResponse:
        """
        List skills for a profile with optional filtering.

        Args:
            profile_id: Profile UUID to list skills for.
            category: Filter by skill category.
            proficiency: Filter by proficiency level.
            is_featured: Filter by featured status.

        Returns:
            SkillListResponse with all matching skills.

        Example:
            # Get all featured programming languages
            skills = await service.list_skills(
                profile_id,
                category=SkillCategory.PROGRAMMING_LANGUAGE,
                is_featured=True
            )
        """
        conditions = [Skill.profile_id == profile_id]

        if category:
            conditions.append(Skill.category == category.value)

        if proficiency:
            conditions.append(Skill.proficiency == proficiency.value)

        if is_featured is not None:
            conditions.append(Skill.is_featured == is_featured)

        # Count total
        count_query = select(func.count(Skill.id)).where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch skills
        query = (
            select(Skill)
            .where(and_(*conditions))
            .order_by(Skill.display_order.asc(), Skill.name.asc())
        )

        result = await self.session.execute(query)
        skills = list(result.scalars().all())

        items = [self._to_response(skill) for skill in skills]

        return SkillListResponse(items=items, total=total)

    async def get_featured_skills(
        self,
        profile_id: UUID,
    ) -> list[Skill]:
        """
        Get all featured skills for a profile.

        Args:
            profile_id: Profile UUID.

        Returns:
            List of featured Skill instances.
        """
        query = (
            select(Skill)
            .where(
                Skill.profile_id == profile_id,
                Skill.is_featured == True,  # noqa: E712
            )
            .order_by(Skill.display_order.asc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_skills(
        self,
        profile_id: UUID,
        query_text: str,
    ) -> list[Skill]:
        """
        Search skills by name or keywords.

        Args:
            profile_id: Profile UUID.
            query_text: Search query.

        Returns:
            List of matching Skill instances.
        """
        search_term = f"%{query_text.lower()}%"

        query = (
            select(Skill)
            .where(
                Skill.profile_id == profile_id,
                func.lower(Skill.name).like(search_term),
            )
            .order_by(Skill.name.asc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update(
        self,
        skill_id: UUID,
        data: SkillUpdate,
    ) -> Optional[Skill]:
        """
        Update an existing skill.

        Only fields provided in the update data are modified.

        Args:
            skill_id: Skill UUID to update.
            data: Fields to update (only non-None fields are applied).

        Returns:
            Updated Skill instance or None if not found.

        Example:
            skill = await service.update(
                skill_id,
                SkillUpdate(proficiency=SkillProficiency.EXPERT)
            )
        """
        skill = await self.get_by_id(skill_id)
        if not skill:
            return None

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Convert enums to their values for database storage
            if field == "category" and value is not None:
                value = value.value
            elif field == "proficiency" and value is not None:
                value = value.value

            setattr(skill, field, value)

        await self.session.flush()
        await self.session.refresh(skill)

        logger.info(f"Updated skill {skill_id}: {list(update_data.keys())}")

        return skill

    async def update_display_order(
        self,
        skill_ids: list[UUID],
    ) -> bool:
        """
        Update display order for multiple skills.

        Sets display_order to the index position in the provided list.

        Args:
            skill_ids: List of skill UUIDs in desired display order.

        Returns:
            True if successful.

        Example:
            await service.update_display_order([skill1_id, skill2_id, skill3_id])
        """
        for index, skill_id in enumerate(skill_ids):
            skill = await self.get_by_id(skill_id)
            if skill:
                skill.display_order = index

        await self.session.flush()

        logger.info(f"Updated display order for {len(skill_ids)} skills")

        return True

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    async def delete(self, skill_id: UUID) -> bool:
        """
        Delete a skill.

        Args:
            skill_id: Skill UUID to delete.

        Returns:
            True if deleted, False if not found.

        Example:
            deleted = await service.delete(skill_id)
            if deleted:
                print("Skill deleted successfully")
        """
        skill = await self.get_by_id(skill_id)
        if not skill:
            return False

        await self.session.delete(skill)
        await self.session.flush()

        logger.info(f"Deleted skill {skill_id}")

        return True

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, skill: Skill) -> SkillResponse:
        """
        Convert a Skill ORM instance to a SkillResponse.

        Args:
            skill: Skill ORM instance to convert.

        Returns:
            SkillResponse Pydantic model.
        """
        return SkillResponse(
            id=skill.id,
            profile_id=skill.profile_id,
            name=skill.name,
            category=SkillCategory(skill.category),
            proficiency=SkillProficiency(skill.proficiency),
            years_experience=skill.years_experience,
            keywords=skill.keywords,
            display_order=skill.display_order,
            is_featured=skill.is_featured,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
        )
