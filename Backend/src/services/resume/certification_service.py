# =============================================================================
# Certification Service
# =============================================================================
"""
Service layer for certification management.

Provides business logic for creating, updating, querying, and managing
professional certifications for resume generation.

Usage:
    from src.services.resume.certification_service import CertificationService

    async with get_session() as session:
        service = CertificationService(session)
        cert = await service.create(profile_id, CertificationCreate(...))
"""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Certification
from src.models.resume import (
    CertificationCreate,
    CertificationListResponse,
    CertificationResponse,
    CertificationUpdate,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Certification Service Class
# -----------------------------------------------------------------------------
class CertificationService:
    """
    Service class for certification management operations.

    Provides methods for creating, updating, querying, and deleting
    professional certifications.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Example:
        async with get_session() as session:
            service = CertificationService(session)

            # Create certification
            cert = await service.create(
                profile_id,
                CertificationCreate(
                    name="AWS Solutions Architect",
                    issuing_organization="Amazon Web Services",
                    issue_date=date(2023, 6, 15)
                )
            )
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the certification service.

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
        data: CertificationCreate,
    ) -> Certification:
        """
        Create a new certification entry.

        Args:
            profile_id: UUID of the profile to associate with.
            data: Certification creation data.

        Returns:
            Created Certification ORM instance.

        Example:
            cert = await service.create(
                profile_id,
                CertificationCreate(
                    name="AWS Solutions Architect - Professional",
                    issuing_organization="Amazon Web Services",
                    issue_date=date(2023, 6, 15),
                    expiration_date=date(2026, 6, 15),
                    related_skills=["AWS", "Cloud Architecture"]
                )
            )
        """
        certification = Certification(
            profile_id=profile_id,
            name=data.name,
            issuing_organization=data.issuing_organization,
            credential_id=data.credential_id,
            credential_url=data.credential_url,
            issue_date=data.issue_date,
            expiration_date=data.expiration_date,
            is_active=data.is_active,
            related_skills=data.related_skills,
            display_order=data.display_order,
        )

        self.session.add(certification)
        await self.session.flush()
        await self.session.refresh(certification)

        logger.info(
            f"Created certification {certification.id}: "
            f"'{certification.name}' from '{certification.issuing_organization}'"
        )

        return certification

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------
    async def get_by_id(self, certification_id: UUID) -> Optional[Certification]:
        """
        Get a certification by ID.

        Args:
            certification_id: Certification UUID to retrieve.

        Returns:
            Certification instance or None if not found.
        """
        query = select(Certification).where(Certification.id == certification_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_certifications(
        self,
        profile_id: UUID,
        is_active: Optional[bool] = None,
    ) -> CertificationListResponse:
        """
        List certifications for a profile with optional filtering.

        Results are ordered by issue_date descending (most recent first).

        Args:
            profile_id: Profile UUID to list certifications for.
            is_active: Filter by active status.

        Returns:
            CertificationListResponse with all matching certifications.

        Example:
            # Get all active certifications
            certs = await service.list_certifications(
                profile_id,
                is_active=True
            )
        """
        conditions = [Certification.profile_id == profile_id]

        if is_active is not None:
            conditions.append(Certification.is_active == is_active)

        # Count total
        count_query = select(func.count(Certification.id)).where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch certifications
        query = (
            select(Certification)
            .where(and_(*conditions))
            .order_by(Certification.issue_date.desc())
        )

        result = await self.session.execute(query)
        certifications = list(result.scalars().all())

        items = [self._to_response(cert) for cert in certifications]

        return CertificationListResponse(items=items, total=total)

    async def get_active_certifications(
        self,
        profile_id: UUID,
    ) -> list[Certification]:
        """
        Get all active certifications for a profile.

        Also checks expiration dates and marks expired certs as inactive.

        Args:
            profile_id: Profile UUID.

        Returns:
            List of active Certification instances.
        """
        today = date.today()

        # First, update any expired certifications
        query = (
            select(Certification)
            .where(
                Certification.profile_id == profile_id,
                Certification.is_active == True,  # noqa: E712
                Certification.expiration_date.isnot(None),
                Certification.expiration_date < today,
            )
        )

        result = await self.session.execute(query)
        expired_certs = list(result.scalars().all())

        for cert in expired_certs:
            cert.is_active = False
            logger.info(f"Marked certification {cert.id} as inactive (expired)")

        await self.session.flush()

        # Now fetch active certifications
        query = (
            select(Certification)
            .where(
                Certification.profile_id == profile_id,
                Certification.is_active == True,  # noqa: E712
            )
            .order_by(Certification.issue_date.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------
    async def update(
        self,
        certification_id: UUID,
        data: CertificationUpdate,
    ) -> Optional[Certification]:
        """
        Update an existing certification.

        Only fields provided in the update data are modified.

        Args:
            certification_id: Certification UUID to update.
            data: Fields to update (only non-None fields are applied).

        Returns:
            Updated Certification instance or None if not found.

        Example:
            cert = await service.update(
                certification_id,
                CertificationUpdate(is_active=False)
            )
        """
        certification = await self.get_by_id(certification_id)
        if not certification:
            return None

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(certification, field, value)

        await self.session.flush()
        await self.session.refresh(certification)

        logger.info(f"Updated certification {certification_id}: {list(update_data.keys())}")

        return certification

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    async def delete(self, certification_id: UUID) -> bool:
        """
        Delete a certification.

        Args:
            certification_id: Certification UUID to delete.

        Returns:
            True if deleted, False if not found.
        """
        certification = await self.get_by_id(certification_id)
        if not certification:
            return False

        await self.session.delete(certification)
        await self.session.flush()

        logger.info(f"Deleted certification {certification_id}")

        return True

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _to_response(self, certification: Certification) -> CertificationResponse:
        """
        Convert a Certification ORM instance to a CertificationResponse.

        Args:
            certification: Certification ORM instance to convert.

        Returns:
            CertificationResponse Pydantic model.
        """
        return CertificationResponse(
            id=certification.id,
            profile_id=certification.profile_id,
            name=certification.name,
            issuing_organization=certification.issuing_organization,
            credential_id=certification.credential_id,
            credential_url=certification.credential_url,
            issue_date=certification.issue_date,
            expiration_date=certification.expiration_date,
            is_active=certification.is_active,
            related_skills=certification.related_skills,
            display_order=certification.display_order,
            created_at=certification.created_at,
            updated_at=certification.updated_at,
        )
