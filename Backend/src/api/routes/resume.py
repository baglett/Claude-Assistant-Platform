# =============================================================================
# Resume API Routes
# =============================================================================
"""
API routes for resume feature management.

Provides RESTful endpoints for:
- User profile management
- Skills CRUD
- Work experience CRUD
- Education CRUD
- Certifications CRUD
- Job listings management
- Generated resumes management

All endpoints are prefixed with /resume when registered.

Usage:
    from src.api.routes import resume
    app.include_router(resume.router, prefix="/api")
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session_dependency
from src.models.resume import (
    # Enums
    ApplicationStatus,
    DegreeType,
    EmploymentType,
    ResumeFormat,
    SkillCategory,
    SkillProficiency,
    # Profile
    ProfileCreate,
    ProfileResponse,
    ProfileStats,
    ProfileUpdate,
    # Skills
    SkillCreate,
    SkillListResponse,
    SkillResponse,
    SkillUpdate,
    # Work Experience
    WorkExperienceCreate,
    WorkExperienceListResponse,
    WorkExperienceResponse,
    WorkExperienceUpdate,
    # Education
    EducationCreate,
    EducationListResponse,
    EducationResponse,
    EducationUpdate,
    # Certifications
    CertificationCreate,
    CertificationListResponse,
    CertificationResponse,
    CertificationUpdate,
    # Job Listings
    JobListingCreate,
    JobListingListResponse,
    JobListingResponse,
    JobListingUpdate,
    JobScrapeRequest,
    # Generated Resumes
    GeneratedResumeListResponse,
    GeneratedResumeResponse,
)
from src.services.resume import (
    CertificationService,
    EducationService,
    GeneratedResumeService,
    JobListingService,
    ProfileService,
    SkillService,
    WorkExperienceService,
)


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Router Configuration
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/resume", tags=["resume"])


# -----------------------------------------------------------------------------
# Service Dependencies
# -----------------------------------------------------------------------------
async def get_profile_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> ProfileService:
    """Get ProfileService instance with database session."""
    return ProfileService(session)


async def get_skill_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> SkillService:
    """Get SkillService instance with database session."""
    return SkillService(session)


async def get_work_experience_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> WorkExperienceService:
    """Get WorkExperienceService instance with database session."""
    return WorkExperienceService(session)


async def get_education_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> EducationService:
    """Get EducationService instance with database session."""
    return EducationService(session)


async def get_certification_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> CertificationService:
    """Get CertificationService instance with database session."""
    return CertificationService(session)


async def get_job_listing_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> JobListingService:
    """Get JobListingService instance with database session."""
    return JobListingService(session)


async def get_generated_resume_service(
    session: AsyncSession = Depends(get_session_dependency),
) -> GeneratedResumeService:
    """Get GeneratedResumeService instance with database session."""
    return GeneratedResumeService(session)


# =============================================================================
# Profile Endpoints
# =============================================================================


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Get user profile",
    description="Get the user profile. Creates a placeholder if none exists.",
    responses={
        200: {"description": "Profile retrieved successfully"},
    },
)
async def get_profile(
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """
    Get the user profile.

    Returns the user's resume profile. Since this is a single-user system,
    returns the only profile or creates a placeholder if none exists.

    Args:
        service: ProfileService from dependency injection.

    Returns:
        The user profile.

    Example:
        GET /api/resume/profile
    """
    profile = await service.get_or_create_profile()
    return service._to_response(profile)


@router.put(
    "/profile",
    response_model=ProfileResponse,
    summary="Update user profile",
    description="Update the user profile. Creates if none exists.",
    responses={
        200: {"description": "Profile updated successfully"},
    },
)
async def update_profile(
    data: ProfileUpdate,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """
    Update the user profile.

    Updates profile fields. Only provided fields are modified.

    Args:
        data: Fields to update.
        service: ProfileService from dependency injection.

    Returns:
        The updated profile.

    Example:
        PUT /api/resume/profile
        {"professional_summary": "Updated summary text"}
    """
    # Ensure profile exists
    await service.get_or_create_profile()

    profile = await service.update_profile(data)
    return service._to_response(profile)


@router.get(
    "/profile/stats",
    response_model=ProfileStats,
    summary="Get profile statistics",
    description="Get aggregated statistics about the profile.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
    },
)
async def get_profile_stats(
    service: ProfileService = Depends(get_profile_service),
) -> ProfileStats:
    """
    Get profile statistics.

    Returns aggregate counts for skills, experience, education, etc.

    Args:
        service: ProfileService from dependency injection.

    Returns:
        Aggregated statistics.

    Example:
        GET /api/resume/profile/stats
    """
    return await service.get_profile_stats()


# =============================================================================
# Skills Endpoints
# =============================================================================


@router.get(
    "/skills",
    response_model=SkillListResponse,
    summary="List skills",
    description="List all skills with optional filtering.",
    responses={
        200: {"description": "List of skills"},
    },
)
async def list_skills(
    category: Optional[SkillCategory] = Query(None, description="Filter by category"),
    proficiency: Optional[SkillProficiency] = Query(None, description="Filter by proficiency"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    profile_service: ProfileService = Depends(get_profile_service),
    service: SkillService = Depends(get_skill_service),
) -> SkillListResponse:
    """
    List skills for the user profile.

    Args:
        category: Optional category filter.
        proficiency: Optional proficiency filter.
        is_featured: Optional featured status filter.
        profile_service: ProfileService for getting profile ID.
        service: SkillService from dependency injection.

    Returns:
        List of skills.

    Example:
        GET /api/resume/skills?category=programming_language&is_featured=true
    """
    profile = await profile_service.get_or_create_profile()
    return await service.list_skills(
        profile.id,
        category=category,
        proficiency=proficiency,
        is_featured=is_featured,
    )


@router.post(
    "/skills",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a skill",
    description="Add a new skill to the profile.",
    responses={
        201: {"description": "Skill created successfully"},
        400: {"description": "Skill already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_skill(
    data: SkillCreate,
    profile_service: ProfileService = Depends(get_profile_service),
    service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Create a new skill.

    Args:
        data: Skill creation data.
        profile_service: ProfileService for getting profile ID.
        service: SkillService from dependency injection.

    Returns:
        The created skill.

    Example:
        POST /api/resume/skills
        {"name": "Python", "category": "programming_language", "proficiency": "expert"}
    """
    profile = await profile_service.get_or_create_profile()

    try:
        skill = await service.create(profile.id, data)
        return service._to_response(skill)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/skills/{skill_id}",
    response_model=SkillResponse,
    summary="Get a skill",
    description="Get a specific skill by ID.",
    responses={
        200: {"description": "Skill found"},
        404: {"description": "Skill not found"},
    },
)
async def get_skill(
    skill_id: UUID,
    service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Get a skill by ID.

    Args:
        skill_id: UUID of the skill.
        service: SkillService from dependency injection.

    Returns:
        The skill if found.

    Raises:
        HTTPException: 404 if not found.
    """
    skill = await service.get_by_id(skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {skill_id} not found",
        )
    return service._to_response(skill)


@router.patch(
    "/skills/{skill_id}",
    response_model=SkillResponse,
    summary="Update a skill",
    description="Update skill fields.",
    responses={
        200: {"description": "Skill updated"},
        404: {"description": "Skill not found"},
    },
)
async def update_skill(
    skill_id: UUID,
    data: SkillUpdate,
    service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Update a skill.

    Args:
        skill_id: UUID of the skill.
        data: Fields to update.
        service: SkillService from dependency injection.

    Returns:
        The updated skill.
    """
    skill = await service.update(skill_id, data)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {skill_id} not found",
        )
    return service._to_response(skill)


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a skill",
    description="Remove a skill from the profile.",
    responses={
        204: {"description": "Skill deleted"},
        404: {"description": "Skill not found"},
    },
)
async def delete_skill(
    skill_id: UUID,
    service: SkillService = Depends(get_skill_service),
) -> None:
    """
    Delete a skill.

    Args:
        skill_id: UUID of the skill.
        service: SkillService from dependency injection.
    """
    deleted = await service.delete(skill_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {skill_id} not found",
        )


# =============================================================================
# Work Experience Endpoints
# =============================================================================


@router.get(
    "/experience",
    response_model=WorkExperienceListResponse,
    summary="List work experiences",
    description="List all work experience entries.",
    responses={
        200: {"description": "List of work experiences"},
    },
)
async def list_work_experiences(
    employment_type: Optional[EmploymentType] = Query(None, description="Filter by type"),
    is_current: Optional[bool] = Query(None, description="Filter by current status"),
    profile_service: ProfileService = Depends(get_profile_service),
    service: WorkExperienceService = Depends(get_work_experience_service),
) -> WorkExperienceListResponse:
    """
    List work experiences.

    Args:
        employment_type: Optional type filter.
        is_current: Optional current position filter.
        profile_service: ProfileService for getting profile ID.
        service: WorkExperienceService from dependency injection.

    Returns:
        List of work experiences.
    """
    profile = await profile_service.get_or_create_profile()
    return await service.list_experiences(
        profile.id,
        employment_type=employment_type,
        is_current=is_current,
    )


@router.post(
    "/experience",
    response_model=WorkExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create work experience",
    description="Add a new work experience entry.",
    responses={
        201: {"description": "Experience created"},
        422: {"description": "Validation error"},
    },
)
async def create_work_experience(
    data: WorkExperienceCreate,
    profile_service: ProfileService = Depends(get_profile_service),
    service: WorkExperienceService = Depends(get_work_experience_service),
) -> WorkExperienceResponse:
    """
    Create a work experience entry.

    Args:
        data: Work experience creation data.
        profile_service: ProfileService for getting profile ID.
        service: WorkExperienceService from dependency injection.

    Returns:
        The created work experience.
    """
    profile = await profile_service.get_or_create_profile()
    experience = await service.create(profile.id, data)
    return service._to_response(experience)


@router.get(
    "/experience/{experience_id}",
    response_model=WorkExperienceResponse,
    summary="Get work experience",
    description="Get a specific work experience by ID.",
    responses={
        200: {"description": "Experience found"},
        404: {"description": "Experience not found"},
    },
)
async def get_work_experience(
    experience_id: UUID,
    service: WorkExperienceService = Depends(get_work_experience_service),
) -> WorkExperienceResponse:
    """
    Get a work experience by ID.

    Args:
        experience_id: UUID of the experience.
        service: WorkExperienceService from dependency injection.

    Returns:
        The experience if found.
    """
    experience = await service.get_by_id(experience_id)
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work experience {experience_id} not found",
        )
    return service._to_response(experience)


@router.patch(
    "/experience/{experience_id}",
    response_model=WorkExperienceResponse,
    summary="Update work experience",
    description="Update work experience fields.",
    responses={
        200: {"description": "Experience updated"},
        404: {"description": "Experience not found"},
    },
)
async def update_work_experience(
    experience_id: UUID,
    data: WorkExperienceUpdate,
    service: WorkExperienceService = Depends(get_work_experience_service),
) -> WorkExperienceResponse:
    """
    Update a work experience.

    Args:
        experience_id: UUID of the experience.
        data: Fields to update.
        service: WorkExperienceService from dependency injection.

    Returns:
        The updated experience.
    """
    experience = await service.update(experience_id, data)
    if not experience:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work experience {experience_id} not found",
        )
    return service._to_response(experience)


@router.delete(
    "/experience/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete work experience",
    description="Remove a work experience entry.",
    responses={
        204: {"description": "Experience deleted"},
        404: {"description": "Experience not found"},
    },
)
async def delete_work_experience(
    experience_id: UUID,
    service: WorkExperienceService = Depends(get_work_experience_service),
) -> None:
    """
    Delete a work experience.

    Args:
        experience_id: UUID of the experience.
        service: WorkExperienceService from dependency injection.
    """
    deleted = await service.delete(experience_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work experience {experience_id} not found",
        )


# =============================================================================
# Education Endpoints
# =============================================================================


@router.get(
    "/education",
    response_model=EducationListResponse,
    summary="List education entries",
    description="List all education entries.",
    responses={
        200: {"description": "List of education entries"},
    },
)
async def list_education(
    degree_type: Optional[DegreeType] = Query(None, description="Filter by degree type"),
    is_in_progress: Optional[bool] = Query(None, description="Filter by in-progress status"),
    profile_service: ProfileService = Depends(get_profile_service),
    service: EducationService = Depends(get_education_service),
) -> EducationListResponse:
    """
    List education entries.

    Args:
        degree_type: Optional degree type filter.
        is_in_progress: Optional in-progress filter.
        profile_service: ProfileService for getting profile ID.
        service: EducationService from dependency injection.

    Returns:
        List of education entries.
    """
    profile = await profile_service.get_or_create_profile()
    return await service.list_education(
        profile.id,
        degree_type=degree_type,
        is_in_progress=is_in_progress,
    )


@router.post(
    "/education",
    response_model=EducationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create education entry",
    description="Add a new education entry.",
    responses={
        201: {"description": "Education entry created"},
        422: {"description": "Validation error"},
    },
)
async def create_education(
    data: EducationCreate,
    profile_service: ProfileService = Depends(get_profile_service),
    service: EducationService = Depends(get_education_service),
) -> EducationResponse:
    """
    Create an education entry.

    Args:
        data: Education creation data.
        profile_service: ProfileService for getting profile ID.
        service: EducationService from dependency injection.

    Returns:
        The created education entry.
    """
    profile = await profile_service.get_or_create_profile()
    education = await service.create(profile.id, data)
    return service._to_response(education)


@router.get(
    "/education/{education_id}",
    response_model=EducationResponse,
    summary="Get education entry",
    description="Get a specific education entry by ID.",
    responses={
        200: {"description": "Education entry found"},
        404: {"description": "Education entry not found"},
    },
)
async def get_education(
    education_id: UUID,
    service: EducationService = Depends(get_education_service),
) -> EducationResponse:
    """
    Get an education entry by ID.

    Args:
        education_id: UUID of the education entry.
        service: EducationService from dependency injection.

    Returns:
        The education entry if found.
    """
    education = await service.get_by_id(education_id)
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Education entry {education_id} not found",
        )
    return service._to_response(education)


@router.patch(
    "/education/{education_id}",
    response_model=EducationResponse,
    summary="Update education entry",
    description="Update education entry fields.",
    responses={
        200: {"description": "Education entry updated"},
        404: {"description": "Education entry not found"},
    },
)
async def update_education(
    education_id: UUID,
    data: EducationUpdate,
    service: EducationService = Depends(get_education_service),
) -> EducationResponse:
    """
    Update an education entry.

    Args:
        education_id: UUID of the education entry.
        data: Fields to update.
        service: EducationService from dependency injection.

    Returns:
        The updated education entry.
    """
    education = await service.update(education_id, data)
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Education entry {education_id} not found",
        )
    return service._to_response(education)


@router.delete(
    "/education/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete education entry",
    description="Remove an education entry.",
    responses={
        204: {"description": "Education entry deleted"},
        404: {"description": "Education entry not found"},
    },
)
async def delete_education(
    education_id: UUID,
    service: EducationService = Depends(get_education_service),
) -> None:
    """
    Delete an education entry.

    Args:
        education_id: UUID of the education entry.
        service: EducationService from dependency injection.
    """
    deleted = await service.delete(education_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Education entry {education_id} not found",
        )


# =============================================================================
# Certifications Endpoints
# =============================================================================


@router.get(
    "/certifications",
    response_model=CertificationListResponse,
    summary="List certifications",
    description="List all certifications.",
    responses={
        200: {"description": "List of certifications"},
    },
)
async def list_certifications(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    profile_service: ProfileService = Depends(get_profile_service),
    service: CertificationService = Depends(get_certification_service),
) -> CertificationListResponse:
    """
    List certifications.

    Args:
        is_active: Optional active status filter.
        profile_service: ProfileService for getting profile ID.
        service: CertificationService from dependency injection.

    Returns:
        List of certifications.
    """
    profile = await profile_service.get_or_create_profile()
    return await service.list_certifications(profile.id, is_active=is_active)


@router.post(
    "/certifications",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create certification",
    description="Add a new certification.",
    responses={
        201: {"description": "Certification created"},
        422: {"description": "Validation error"},
    },
)
async def create_certification(
    data: CertificationCreate,
    profile_service: ProfileService = Depends(get_profile_service),
    service: CertificationService = Depends(get_certification_service),
) -> CertificationResponse:
    """
    Create a certification.

    Args:
        data: Certification creation data.
        profile_service: ProfileService for getting profile ID.
        service: CertificationService from dependency injection.

    Returns:
        The created certification.
    """
    profile = await profile_service.get_or_create_profile()
    certification = await service.create(profile.id, data)
    return service._to_response(certification)


@router.get(
    "/certifications/{certification_id}",
    response_model=CertificationResponse,
    summary="Get certification",
    description="Get a specific certification by ID.",
    responses={
        200: {"description": "Certification found"},
        404: {"description": "Certification not found"},
    },
)
async def get_certification(
    certification_id: UUID,
    service: CertificationService = Depends(get_certification_service),
) -> CertificationResponse:
    """
    Get a certification by ID.

    Args:
        certification_id: UUID of the certification.
        service: CertificationService from dependency injection.

    Returns:
        The certification if found.
    """
    certification = await service.get_by_id(certification_id)
    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {certification_id} not found",
        )
    return service._to_response(certification)


@router.patch(
    "/certifications/{certification_id}",
    response_model=CertificationResponse,
    summary="Update certification",
    description="Update certification fields.",
    responses={
        200: {"description": "Certification updated"},
        404: {"description": "Certification not found"},
    },
)
async def update_certification(
    certification_id: UUID,
    data: CertificationUpdate,
    service: CertificationService = Depends(get_certification_service),
) -> CertificationResponse:
    """
    Update a certification.

    Args:
        certification_id: UUID of the certification.
        data: Fields to update.
        service: CertificationService from dependency injection.

    Returns:
        The updated certification.
    """
    certification = await service.update(certification_id, data)
    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {certification_id} not found",
        )
    return service._to_response(certification)


@router.delete(
    "/certifications/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete certification",
    description="Remove a certification.",
    responses={
        204: {"description": "Certification deleted"},
        404: {"description": "Certification not found"},
    },
)
async def delete_certification(
    certification_id: UUID,
    service: CertificationService = Depends(get_certification_service),
) -> None:
    """
    Delete a certification.

    Args:
        certification_id: UUID of the certification.
        service: CertificationService from dependency injection.
    """
    deleted = await service.delete(certification_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification {certification_id} not found",
        )


# =============================================================================
# Job Listings Endpoints
# =============================================================================


@router.get(
    "/jobs",
    response_model=JobListingListResponse,
    summary="List job listings",
    description="List scraped job listings with filtering and pagination.",
    responses={
        200: {"description": "List of job listings"},
    },
)
async def list_job_listings(
    company_name: Optional[str] = Query(None, description="Filter by company"),
    source_site: Optional[str] = Query(None, description="Filter by source site"),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite status"),
    application_status: Optional[ApplicationStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title/company/description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: JobListingService = Depends(get_job_listing_service),
) -> JobListingListResponse:
    """
    List job listings.

    Args:
        company_name: Optional company filter.
        source_site: Optional source site filter.
        is_favorite: Optional favorite filter.
        application_status: Optional application status filter.
        search: Optional search query.
        page: Page number.
        page_size: Items per page.
        service: JobListingService from dependency injection.

    Returns:
        Paginated list of job listings.
    """
    return await service.list_listings(
        company_name=company_name,
        source_site=source_site,
        is_favorite=is_favorite,
        application_status=application_status,
        search_query=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/jobs",
    response_model=JobListingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create job listing",
    description="Add a new job listing (manually or from scraping).",
    responses={
        201: {"description": "Job listing created"},
        400: {"description": "Duplicate URL"},
        422: {"description": "Validation error"},
    },
)
async def create_job_listing(
    data: JobListingCreate,
    service: JobListingService = Depends(get_job_listing_service),
) -> JobListingResponse:
    """
    Create a job listing.

    Args:
        data: Job listing creation data.
        service: JobListingService from dependency injection.

    Returns:
        The created job listing.
    """
    try:
        listing = await service.create(data)
        return service._to_response(listing)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/jobs/scrape",
    response_model=JobListingResponse,
    summary="Scrape job listing",
    description="Scrape a job listing from a URL and save to database.",
    responses={
        200: {"description": "Job listing scraped"},
        400: {"description": "Failed to scrape"},
    },
)
async def scrape_job_listing(
    request: JobScrapeRequest,
    service: JobListingService = Depends(get_job_listing_service),
) -> JobListingResponse:
    """
    Scrape a job listing from URL.

    Fetches the job page, extracts relevant information using site-specific
    parsers, and saves the job listing to the database.

    Supports:
    - LinkedIn Jobs
    - Indeed
    - Greenhouse ATS
    - Lever ATS
    - Generic websites (with reduced accuracy)

    Args:
        request: Scrape request containing the URL to scrape.
        service: JobListingService from dependency injection.

    Returns:
        The scraped and saved job listing.

    Raises:
        HTTPException: If scraping fails or URL is invalid.
    """
    from src.services.scraper import JobScraperService
    from src.services.scraper.service import FetchError, ParseError, UnsupportedURLError

    # Check if job already exists
    existing = await service.get_by_url(request.url)
    if existing:
        logger.info(f"Job listing already exists for URL: {request.url}")
        return service._to_response(existing)

    # Scrape the job listing
    try:
        async with JobScraperService() as scraper:
            job_data = await scraper.scrape_job(request.url)
    except UnsupportedURLError as e:
        logger.warning(f"Unsupported URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported or invalid URL: {e}",
        )
    except FetchError as e:
        logger.error(f"Failed to fetch URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch job listing: {e}",
        )
    except ParseError as e:
        logger.error(f"Failed to parse job listing: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse job listing: {e}",
        )

    # Check if we got enough data
    if not job_data.job_title:
        logger.warning(f"Could not extract job title from {request.url}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract job title from page. The page structure may not be supported.",
        )

    # Create the job listing in database
    create_data = JobListingCreate(
        url=request.url,
        source_site=job_data.source_site,
        job_title=job_data.job_title,
        company_name=job_data.company_name,
        company_url=job_data.company_url,
        location=job_data.location,
        is_remote=job_data.is_remote,
        salary_min=job_data.salary_min,
        salary_max=job_data.salary_max,
        salary_currency=job_data.salary_currency,
        description=job_data.description,
        required_skills=job_data.required_skills,
        preferred_skills=job_data.preferred_skills,
        requirements=job_data.requirements,
        raw_html=job_data.raw_html if len(job_data.raw_html or "") < 500000 else None,
    )

    try:
        listing = await service.create(create_data)
    except ValueError as e:
        # Job listing already exists (race condition)
        existing = await service.get_by_url(request.url)
        if existing:
            return service._to_response(existing)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    logger.info(
        f"Scraped job listing: '{listing.job_title}' at '{listing.company_name}' "
        f"(confidence: {job_data.parse_confidence}%)"
    )

    return service._to_response(listing)


@router.get(
    "/jobs/{listing_id}",
    response_model=JobListingResponse,
    summary="Get job listing",
    description="Get a specific job listing by ID.",
    responses={
        200: {"description": "Job listing found"},
        404: {"description": "Job listing not found"},
    },
)
async def get_job_listing(
    listing_id: UUID,
    service: JobListingService = Depends(get_job_listing_service),
) -> JobListingResponse:
    """
    Get a job listing by ID.

    Args:
        listing_id: UUID of the job listing.
        service: JobListingService from dependency injection.

    Returns:
        The job listing if found.
    """
    listing = await service.get_by_id(listing_id)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing {listing_id} not found",
        )
    return service._to_response(listing)


@router.patch(
    "/jobs/{listing_id}",
    response_model=JobListingResponse,
    summary="Update job listing",
    description="Update job listing fields.",
    responses={
        200: {"description": "Job listing updated"},
        404: {"description": "Job listing not found"},
    },
)
async def update_job_listing(
    listing_id: UUID,
    data: JobListingUpdate,
    service: JobListingService = Depends(get_job_listing_service),
) -> JobListingResponse:
    """
    Update a job listing.

    Args:
        listing_id: UUID of the job listing.
        data: Fields to update.
        service: JobListingService from dependency injection.

    Returns:
        The updated job listing.
    """
    listing = await service.update(listing_id, data)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing {listing_id} not found",
        )
    return service._to_response(listing)


@router.post(
    "/jobs/{listing_id}/favorite",
    response_model=JobListingResponse,
    summary="Toggle favorite",
    description="Toggle the favorite status of a job listing.",
    responses={
        200: {"description": "Favorite toggled"},
        404: {"description": "Job listing not found"},
    },
)
async def toggle_job_favorite(
    listing_id: UUID,
    service: JobListingService = Depends(get_job_listing_service),
) -> JobListingResponse:
    """
    Toggle favorite status.

    Args:
        listing_id: UUID of the job listing.
        service: JobListingService from dependency injection.

    Returns:
        The updated job listing.
    """
    listing = await service.toggle_favorite(listing_id)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing {listing_id} not found",
        )
    return service._to_response(listing)


@router.delete(
    "/jobs/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job listing",
    description="Remove a job listing.",
    responses={
        204: {"description": "Job listing deleted"},
        404: {"description": "Job listing not found"},
    },
)
async def delete_job_listing(
    listing_id: UUID,
    service: JobListingService = Depends(get_job_listing_service),
) -> None:
    """
    Delete a job listing.

    Args:
        listing_id: UUID of the job listing.
        service: JobListingService from dependency injection.
    """
    deleted = await service.delete(listing_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing {listing_id} not found",
        )


# =============================================================================
# Generated Resumes Endpoints
# =============================================================================


@router.get(
    "/generated",
    response_model=GeneratedResumeListResponse,
    summary="List generated resumes",
    description="List all generated resumes with pagination.",
    responses={
        200: {"description": "List of generated resumes"},
    },
)
async def list_generated_resumes(
    job_listing_id: Optional[UUID] = Query(None, description="Filter by job listing"),
    format_filter: Optional[ResumeFormat] = Query(None, description="Filter by format"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    profile_service: ProfileService = Depends(get_profile_service),
    service: GeneratedResumeService = Depends(get_generated_resume_service),
) -> GeneratedResumeListResponse:
    """
    List generated resumes.

    Args:
        job_listing_id: Optional job listing filter.
        format_filter: Optional format filter.
        page: Page number.
        page_size: Items per page.
        profile_service: ProfileService for getting profile ID.
        service: GeneratedResumeService from dependency injection.

    Returns:
        Paginated list of generated resumes.
    """
    profile = await profile_service.get_or_create_profile()
    return await service.list_resumes(
        profile.id,
        job_listing_id=job_listing_id,
        format_filter=format_filter,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/generated/{resume_id}",
    response_model=GeneratedResumeResponse,
    summary="Get generated resume",
    description="Get a specific generated resume by ID.",
    responses={
        200: {"description": "Generated resume found"},
        404: {"description": "Generated resume not found"},
    },
)
async def get_generated_resume(
    resume_id: UUID,
    service: GeneratedResumeService = Depends(get_generated_resume_service),
) -> GeneratedResumeResponse:
    """
    Get a generated resume by ID.

    Args:
        resume_id: UUID of the generated resume.
        service: GeneratedResumeService from dependency injection.

    Returns:
        The generated resume if found.
    """
    resume = await service.get_by_id(resume_id, include_job_listing=True)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generated resume {resume_id} not found",
        )
    return service._to_response(resume)


@router.delete(
    "/generated/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete generated resume",
    description="Remove a generated resume record.",
    responses={
        204: {"description": "Generated resume deleted"},
        404: {"description": "Generated resume not found"},
    },
)
async def delete_generated_resume(
    resume_id: UUID,
    service: GeneratedResumeService = Depends(get_generated_resume_service),
) -> None:
    """
    Delete a generated resume.

    Note: This only deletes the database record.
    The actual file in Google Drive should be deleted separately.

    Args:
        resume_id: UUID of the generated resume.
        service: GeneratedResumeService from dependency injection.
    """
    deleted = await service.delete(resume_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generated resume {resume_id} not found",
        )
