# =============================================================================
# Resume Services Package
# =============================================================================
"""
Services for resume feature management.

This package contains services for:
- User profile management
- Skills, work experience, education, certifications CRUD
- Job listings (scraped jobs)
- Generated resumes

Usage:
    from src.services.resume import ProfileService, SkillService

    async with get_session() as session:
        profile_service = ProfileService(session)
        profile = await profile_service.get_or_create_profile()
"""

from src.services.resume.profile_service import ProfileService
from src.services.resume.skill_service import SkillService
from src.services.resume.work_experience_service import WorkExperienceService
from src.services.resume.education_service import EducationService
from src.services.resume.certification_service import CertificationService
from src.services.resume.job_listing_service import JobListingService
from src.services.resume.generated_resume_service import GeneratedResumeService


__all__ = [
    "ProfileService",
    "SkillService",
    "WorkExperienceService",
    "EducationService",
    "CertificationService",
    "JobListingService",
    "GeneratedResumeService",
]
