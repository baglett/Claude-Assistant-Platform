# =============================================================================
# Models Package
# =============================================================================
"""
Pydantic models and API schemas for the Claude Assistant Platform.

This package contains Pydantic models used for:
- API request/response validation
- Data serialization
- OpenAPI documentation generation

Note: SQLAlchemy ORM models are in src/database/models.py

Usage:
    from src.models import TodoCreate, TodoResponse, TodoStatus
    from src.models.chat import ChatRequest, ChatResponse
    from src.models.resume import ProfileCreate, SkillCreate, SkillResponse
"""

# Todo models
from src.models.todo import (
    AgentType,
    TodoCreate,
    TodoExecuteRequest,
    TodoExecuteResponse,
    TodoListResponse,
    TodoPriority,
    TodoResponse,
    TodoStats,
    TodoStatus,
    TodoUpdate,
)

# Resume models
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
    GeneratedResumeCreate,
    GeneratedResumeListResponse,
    GeneratedResumeResponse,
    ResumeGenerateRequest,
    # Analysis
    ResumeMatchAnalysis,
    SkillMatchResult,
)


__all__ = [
    # Todo models
    "TodoStatus",
    "AgentType",
    "TodoPriority",
    "TodoCreate",
    "TodoUpdate",
    "TodoExecuteRequest",
    "TodoResponse",
    "TodoListResponse",
    "TodoExecuteResponse",
    "TodoStats",
    # Resume enums
    "SkillProficiency",
    "SkillCategory",
    "EmploymentType",
    "DegreeType",
    "ResumeFormat",
    "ApplicationStatus",
    # Profile models
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    "ProfileStats",
    # Skill models
    "SkillCreate",
    "SkillUpdate",
    "SkillResponse",
    "SkillListResponse",
    # Work Experience models
    "WorkExperienceCreate",
    "WorkExperienceUpdate",
    "WorkExperienceResponse",
    "WorkExperienceListResponse",
    # Education models
    "EducationCreate",
    "EducationUpdate",
    "EducationResponse",
    "EducationListResponse",
    # Certification models
    "CertificationCreate",
    "CertificationUpdate",
    "CertificationResponse",
    "CertificationListResponse",
    # Job Listing models
    "JobListingCreate",
    "JobListingUpdate",
    "JobListingResponse",
    "JobListingListResponse",
    "JobScrapeRequest",
    # Generated Resume models
    "GeneratedResumeCreate",
    "GeneratedResumeResponse",
    "GeneratedResumeListResponse",
    "ResumeGenerateRequest",
    # Analysis models
    "SkillMatchResult",
    "ResumeMatchAnalysis",
]
