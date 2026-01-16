# =============================================================================
# Resume Pydantic Models
# =============================================================================
"""
Pydantic models for Resume API requests and responses.

These models handle validation, serialization, and documentation
for all resume-related API operations. They are separate from the
SQLAlchemy ORM models in src/database/models.py.

Usage:
    from src.models.resume import (
        ProfileCreate, ProfileResponse,
        SkillCreate, SkillResponse,
        WorkExperienceCreate, WorkExperienceResponse,
    )

    # Create a new skill
    data = SkillCreate(name="Python", category=SkillCategory.PROGRAMMING_LANGUAGE)

    # Validate response
    response = SkillResponse.model_validate(skill_orm_instance)
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# =============================================================================
# Enums
# =============================================================================


class SkillProficiency(str, Enum):
    """
    Skill proficiency levels.

    Proficiency indicates mastery level:
    - beginner: Basic understanding, limited practical experience
    - intermediate: Solid working knowledge, can handle most tasks
    - advanced: Deep expertise, can handle complex scenarios
    - expert: Industry-leading expertise, can teach others
    """

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillCategory(str, Enum):
    """
    Skill categories for organization and filtering.

    Categories help organize skills for resume generation:
    - programming_language: Python, JavaScript, Go, etc.
    - framework: React, FastAPI, Django, etc.
    - database: PostgreSQL, MongoDB, Redis, etc.
    - cloud: AWS, GCP, Azure, etc.
    - devops: Docker, Kubernetes, CI/CD, etc.
    - soft_skill: Leadership, Communication, etc.
    - tool: Git, VSCode, Figma, etc.
    - methodology: Agile, Scrum, TDD, etc.
    - other: Anything else
    """

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    DEVOPS = "devops"
    SOFT_SKILL = "soft_skill"
    TOOL = "tool"
    METHODOLOGY = "methodology"
    OTHER = "other"


class EmploymentType(str, Enum):
    """
    Employment types for work experience entries.

    Types include:
    - full_time: Standard full-time employment
    - part_time: Part-time position
    - contract: Fixed-term contract
    - freelance: Independent contractor/freelancer
    - internship: Internship or co-op position
    """

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"


class DegreeType(str, Enum):
    """
    Education degree types.

    Degree types from basic to advanced:
    - high_school: High school diploma/GED
    - associate: Associate's degree (2-year)
    - bachelor: Bachelor's degree (4-year)
    - master: Master's degree
    - doctorate: PhD or professional doctorate
    - certificate: Professional certificate
    - bootcamp: Coding bootcamp or similar
    - other: Other educational achievement
    """

    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    CERTIFICATE = "certificate"
    BOOTCAMP = "bootcamp"
    OTHER = "other"


class ResumeFormat(str, Enum):
    """
    Resume output formats.

    Supported formats:
    - pdf: PDF document (best for viewing/printing)
    - docx: Word document (best for ATS compatibility)
    """

    PDF = "pdf"
    DOCX = "docx"


class ApplicationStatus(str, Enum):
    """
    Job application status tracking.

    Status progression:
    - not_applied: Haven't applied yet
    - applied: Application submitted
    - interviewing: In interview process
    - offered: Received offer
    - rejected: Application rejected
    - withdrawn: Withdrew application
    """

    NOT_APPLIED = "not_applied"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


# =============================================================================
# User Profile Models
# =============================================================================


class ProfileBase(BaseModel):
    """Base fields shared by profile create and update."""

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's first name",
        examples=["John"],
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's last name",
        examples=["Doe"],
    )
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Primary email address",
        examples=["john.doe@example.com"],
    )
    phone: Optional[str] = Field(
        None,
        max_length=50,
        description="Phone number",
        examples=["+1 (555) 123-4567"],
    )
    city: Optional[str] = Field(
        None,
        max_length=100,
        description="City of residence",
        examples=["San Francisco"],
    )
    state: Optional[str] = Field(
        None,
        max_length=100,
        description="State or province",
        examples=["California"],
    )
    country: str = Field(
        "United States",
        max_length=100,
        description="Country of residence",
        examples=["United States"],
    )
    linkedin_url: Optional[str] = Field(
        None,
        max_length=500,
        description="LinkedIn profile URL",
        examples=["https://linkedin.com/in/johndoe"],
    )
    github_url: Optional[str] = Field(
        None,
        max_length=500,
        description="GitHub profile URL",
        examples=["https://github.com/johndoe"],
    )
    portfolio_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Portfolio website URL",
        examples=["https://johndoe.dev"],
    )
    personal_website: Optional[str] = Field(
        None,
        max_length=500,
        description="Personal website URL",
        examples=["https://johndoe.com"],
    )
    professional_summary: Optional[str] = Field(
        None,
        description="Default professional summary for resumes",
        examples=[
            "Senior software engineer with 8+ years of experience building scalable web applications."
        ],
    )


class ProfileCreate(ProfileBase):
    """
    Schema for creating a new user profile.

    All personal and professional information for resume generation.

    Attributes:
        first_name: User's first name (required).
        last_name: User's last name (required).
        email: Primary email address (required).
        phone: Phone number (optional).
        city: City of residence (optional).
        state: State/province (optional).
        country: Country of residence (default: United States).
        linkedin_url: LinkedIn profile URL (optional).
        github_url: GitHub profile URL (optional).
        portfolio_url: Portfolio website URL (optional).
        personal_website: Personal website URL (optional).
        professional_summary: Default professional summary (optional).
        metadata: Additional flexible data (optional).

    Example:
        ProfileCreate(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            city="San Francisco",
            state="California",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
    """

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible JSON storage for additional profile data",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+1 (555) 123-4567",
                "city": "San Francisco",
                "state": "California",
                "country": "United States",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "github_url": "https://github.com/johndoe",
                "professional_summary": "Senior software engineer with 8+ years of experience.",
            }
        }
    )


class ProfileUpdate(BaseModel):
    """
    Schema for updating an existing user profile.

    All fields are optional - only provided fields will be updated.

    Example:
        ProfileUpdate(professional_summary="Updated summary text")
    """

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    personal_website: Optional[str] = Field(None, max_length=500)
    professional_summary: Optional[str] = Field(None)
    metadata: Optional[dict[str, Any]] = Field(None)


class ProfileResponse(ProfileBase):
    """
    Schema for profile responses.

    Includes all profile fields plus metadata and timestamps.

    Attributes:
        id: Unique identifier (UUID).
        ... (all ProfileBase fields)
        telegram_user_id: Linked Telegram user ID (if any).
        metadata: Additional data dictionary.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID = Field(..., description="Unique identifier")
    telegram_user_id: Optional[int] = Field(None, description="Linked Telegram user")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional data")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Skill Models
# =============================================================================


class SkillCreate(BaseModel):
    """
    Schema for creating a new skill.

    Attributes:
        name: Skill name (required, 1-200 chars).
        category: Skill category (default: other).
        proficiency: Proficiency level (default: intermediate).
        years_experience: Years of experience (optional, 0-50).
        keywords: Alternative names for job matching (optional).
        display_order: Order for resume display (default: 0).
        is_featured: Whether to prioritize in resumes (default: false).

    Example:
        SkillCreate(
            name="Python",
            category=SkillCategory.PROGRAMMING_LANGUAGE,
            proficiency=SkillProficiency.EXPERT,
            years_experience=8.0,
            keywords=["python3", "py"],
            is_featured=True
        )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Skill name",
        examples=["Python", "React", "AWS"],
    )
    category: SkillCategory = Field(
        SkillCategory.OTHER,
        description="Skill category",
    )
    proficiency: SkillProficiency = Field(
        SkillProficiency.INTERMEDIATE,
        description="Proficiency level",
    )
    years_experience: Optional[Decimal] = Field(
        None,
        ge=0,
        le=50,
        description="Years of experience with this skill",
        examples=[3.5, 8.0],
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Alternative names for job matching",
        examples=[["python3", "py"]],
    )
    display_order: int = Field(
        0,
        ge=0,
        description="Order for resume display",
    )
    is_featured: bool = Field(
        False,
        description="Whether to prioritize in resume generation",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Python",
                "category": "programming_language",
                "proficiency": "expert",
                "years_experience": 8.0,
                "keywords": ["python3", "py"],
                "is_featured": True,
            }
        }
    )


class SkillUpdate(BaseModel):
    """Schema for updating an existing skill."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[SkillCategory] = Field(None)
    proficiency: Optional[SkillProficiency] = Field(None)
    years_experience: Optional[Decimal] = Field(None, ge=0, le=50)
    keywords: Optional[list[str]] = Field(None)
    display_order: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = Field(None)


class SkillResponse(BaseModel):
    """
    Schema for skill responses.

    Includes all skill fields plus timestamps.

    Attributes:
        id: Unique identifier (UUID).
        profile_id: Owning profile ID.
        name: Skill name.
        category: Skill category.
        proficiency: Proficiency level.
        years_experience: Years of experience (may be None).
        keywords: Alternative names.
        display_order: Display order.
        is_featured: Whether featured.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID = Field(..., description="Unique identifier")
    profile_id: UUID = Field(..., description="Owning profile ID")
    name: str = Field(..., description="Skill name")
    category: SkillCategory = Field(..., description="Skill category")
    proficiency: SkillProficiency = Field(..., description="Proficiency level")
    years_experience: Optional[Decimal] = Field(None, description="Years of experience")
    keywords: list[str] = Field(default_factory=list, description="Alternative names")
    display_order: int = Field(..., description="Display order")
    is_featured: bool = Field(..., description="Whether featured")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


class SkillListResponse(BaseModel):
    """Schema for skill list responses with pagination."""

    items: list[SkillResponse] = Field(..., description="List of skills")
    total: int = Field(..., description="Total count")


# =============================================================================
# Work Experience Models
# =============================================================================


class WorkExperienceCreate(BaseModel):
    """
    Schema for creating a new work experience entry.

    Attributes:
        company_name: Employer name (required).
        job_title: Position title (required).
        start_date: Employment start date (required).
        end_date: Employment end date (None if current).
        is_current: Whether this is current position.
        employment_type: Type of employment.
        company_url: Company website URL (optional).
        company_location: Company location (optional).
        description: Job description (optional).
        achievements: Achievement bullet points (optional).
        skills_used: Skills used in this role (optional).
        display_order: Order for resume display.

    Example:
        WorkExperienceCreate(
            company_name="Tech Corp",
            job_title="Senior Software Engineer",
            start_date=date(2020, 1, 15),
            is_current=True,
            achievements=["Led team of 5 engineers", "Reduced latency by 40%"]
        )
    """

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Employer name",
        examples=["Tech Corp", "Google"],
    )
    job_title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Position title",
        examples=["Senior Software Engineer"],
    )
    start_date: date = Field(
        ...,
        description="Employment start date",
    )
    end_date: Optional[date] = Field(
        None,
        description="Employment end date (None if current)",
    )
    is_current: bool = Field(
        False,
        description="Whether this is the current position",
    )
    employment_type: EmploymentType = Field(
        EmploymentType.FULL_TIME,
        description="Type of employment",
    )
    company_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Company website URL",
    )
    company_location: Optional[str] = Field(
        None,
        max_length=200,
        description="Company location",
        examples=["San Francisco, CA"],
    )
    description: Optional[str] = Field(
        None,
        description="Job description",
    )
    achievements: list[str] = Field(
        default_factory=list,
        description="Achievement bullet points",
        examples=[["Led team of 5 engineers", "Reduced latency by 40%"]],
    )
    skills_used: list[str] = Field(
        default_factory=list,
        description="Skills used in this role",
        examples=[["Python", "AWS", "PostgreSQL"]],
    )
    display_order: int = Field(
        0,
        ge=0,
        description="Order for resume display",
    )

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[date], info) -> Optional[date]:
        """Ensure end_date is after start_date if provided."""
        if v is not None and "start_date" in info.data:
            start = info.data["start_date"]
            if v < start:
                raise ValueError("end_date must be after start_date")
        return v


class WorkExperienceUpdate(BaseModel):
    """Schema for updating an existing work experience entry."""

    company_name: Optional[str] = Field(None, min_length=1, max_length=300)
    job_title: Optional[str] = Field(None, min_length=1, max_length=300)
    start_date: Optional[date] = Field(None)
    end_date: Optional[date] = Field(None)
    is_current: Optional[bool] = Field(None)
    employment_type: Optional[EmploymentType] = Field(None)
    company_url: Optional[str] = Field(None, max_length=500)
    company_location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None)
    achievements: Optional[list[str]] = Field(None)
    skills_used: Optional[list[str]] = Field(None)
    display_order: Optional[int] = Field(None, ge=0)


class WorkExperienceResponse(BaseModel):
    """
    Schema for work experience responses.

    Includes all work experience fields plus timestamps.
    """

    id: UUID = Field(..., description="Unique identifier")
    profile_id: UUID = Field(..., description="Owning profile ID")
    company_name: str = Field(..., description="Employer name")
    job_title: str = Field(..., description="Position title")
    start_date: date = Field(..., description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    is_current: bool = Field(..., description="Whether current position")
    employment_type: EmploymentType = Field(..., description="Employment type")
    company_url: Optional[str] = Field(None, description="Company URL")
    company_location: Optional[str] = Field(None, description="Company location")
    description: Optional[str] = Field(None, description="Job description")
    achievements: list[str] = Field(default_factory=list, description="Achievements")
    skills_used: list[str] = Field(default_factory=list, description="Skills used")
    display_order: int = Field(..., description="Display order")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


class WorkExperienceListResponse(BaseModel):
    """Schema for work experience list responses."""

    items: list[WorkExperienceResponse] = Field(..., description="List of experiences")
    total: int = Field(..., description="Total count")


# =============================================================================
# Education Models
# =============================================================================


class EducationCreate(BaseModel):
    """
    Schema for creating a new education entry.

    Attributes:
        institution_name: Name of the institution (required).
        degree_type: Type of degree (required).
        field_of_study: Major or field of study (required).
        degree_name: Full degree name (optional).
        start_date: Start date (optional).
        end_date: Graduation or expected date (optional).
        is_in_progress: Whether currently enrolled.
        institution_location: Institution location (optional).
        institution_url: Institution website URL (optional).
        gpa: Grade point average (optional).
        gpa_scale: GPA scale (default: 4.0).
        honors: Academic honors (optional).
        relevant_coursework: Relevant courses (optional).
        activities: Extracurricular activities (optional).
        display_order: Order for resume display.

    Example:
        EducationCreate(
            institution_name="Stanford University",
            degree_type=DegreeType.BACHELOR,
            field_of_study="Computer Science",
            gpa=3.8
        )
    """

    institution_name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Name of the institution",
        examples=["Stanford University"],
    )
    degree_type: DegreeType = Field(
        ...,
        description="Type of degree",
    )
    field_of_study: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Major or field of study",
        examples=["Computer Science"],
    )
    degree_name: Optional[str] = Field(
        None,
        max_length=300,
        description="Full degree name (e.g., Bachelor of Science)",
        examples=["Bachelor of Science"],
    )
    start_date: Optional[date] = Field(
        None,
        description="Start date",
    )
    end_date: Optional[date] = Field(
        None,
        description="Graduation or expected date",
    )
    is_in_progress: bool = Field(
        False,
        description="Whether currently enrolled",
    )
    institution_location: Optional[str] = Field(
        None,
        max_length=200,
        description="Institution location",
        examples=["Stanford, CA"],
    )
    institution_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Institution website URL",
    )
    gpa: Optional[Decimal] = Field(
        None,
        ge=0,
        le=4.0,
        description="Grade point average",
        examples=[3.8],
    )
    gpa_scale: Decimal = Field(
        Decimal("4.0"),
        ge=1.0,
        le=10.0,
        description="GPA scale",
    )
    honors: list[str] = Field(
        default_factory=list,
        description="Academic honors",
        examples=[["Magna Cum Laude", "Dean's List"]],
    )
    relevant_coursework: list[str] = Field(
        default_factory=list,
        description="Relevant courses",
        examples=[["Data Structures", "Algorithms", "Machine Learning"]],
    )
    activities: list[str] = Field(
        default_factory=list,
        description="Extracurricular activities",
    )
    display_order: int = Field(
        0,
        ge=0,
        description="Order for resume display",
    )


class EducationUpdate(BaseModel):
    """Schema for updating an existing education entry."""

    institution_name: Optional[str] = Field(None, min_length=1, max_length=300)
    degree_type: Optional[DegreeType] = Field(None)
    field_of_study: Optional[str] = Field(None, min_length=1, max_length=300)
    degree_name: Optional[str] = Field(None, max_length=300)
    start_date: Optional[date] = Field(None)
    end_date: Optional[date] = Field(None)
    is_in_progress: Optional[bool] = Field(None)
    institution_location: Optional[str] = Field(None, max_length=200)
    institution_url: Optional[str] = Field(None, max_length=500)
    gpa: Optional[Decimal] = Field(None, ge=0, le=4.0)
    gpa_scale: Optional[Decimal] = Field(None, ge=1.0, le=10.0)
    honors: Optional[list[str]] = Field(None)
    relevant_coursework: Optional[list[str]] = Field(None)
    activities: Optional[list[str]] = Field(None)
    display_order: Optional[int] = Field(None, ge=0)


class EducationResponse(BaseModel):
    """Schema for education responses."""

    id: UUID = Field(..., description="Unique identifier")
    profile_id: UUID = Field(..., description="Owning profile ID")
    institution_name: str = Field(..., description="Institution name")
    degree_type: DegreeType = Field(..., description="Degree type")
    field_of_study: str = Field(..., description="Field of study")
    degree_name: Optional[str] = Field(None, description="Degree name")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    is_in_progress: bool = Field(..., description="Whether in progress")
    institution_location: Optional[str] = Field(None, description="Location")
    institution_url: Optional[str] = Field(None, description="URL")
    gpa: Optional[Decimal] = Field(None, description="GPA")
    gpa_scale: Decimal = Field(..., description="GPA scale")
    honors: list[str] = Field(default_factory=list, description="Honors")
    relevant_coursework: list[str] = Field(default_factory=list, description="Coursework")
    activities: list[str] = Field(default_factory=list, description="Activities")
    display_order: int = Field(..., description="Display order")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


class EducationListResponse(BaseModel):
    """Schema for education list responses."""

    items: list[EducationResponse] = Field(..., description="List of education entries")
    total: int = Field(..., description="Total count")


# =============================================================================
# Certification Models
# =============================================================================


class CertificationCreate(BaseModel):
    """
    Schema for creating a new certification entry.

    Attributes:
        name: Certification name (required).
        issuing_organization: Organization that issued it (required).
        issue_date: When the certification was issued (required).
        expiration_date: When it expires (optional, None if no expiration).
        credential_id: Credential ID or number (optional).
        credential_url: URL to verify the credential (optional).
        is_active: Whether currently active.
        related_skills: Skills this certification validates (optional).
        display_order: Order for resume display.

    Example:
        CertificationCreate(
            name="AWS Solutions Architect - Professional",
            issuing_organization="Amazon Web Services",
            issue_date=date(2023, 6, 15),
            expiration_date=date(2026, 6, 15),
            related_skills=["AWS", "Cloud Architecture"]
        )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Certification name",
        examples=["AWS Solutions Architect - Professional"],
    )
    issuing_organization: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Organization that issued the certification",
        examples=["Amazon Web Services"],
    )
    issue_date: date = Field(
        ...,
        description="When the certification was issued",
    )
    expiration_date: Optional[date] = Field(
        None,
        description="When the certification expires",
    )
    credential_id: Optional[str] = Field(
        None,
        max_length=200,
        description="Credential ID or number",
    )
    credential_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL to verify the credential",
    )
    is_active: bool = Field(
        True,
        description="Whether the certification is currently active",
    )
    related_skills: list[str] = Field(
        default_factory=list,
        description="Skills this certification validates",
        examples=[["AWS", "Cloud Architecture"]],
    )
    display_order: int = Field(
        0,
        ge=0,
        description="Order for resume display",
    )


class CertificationUpdate(BaseModel):
    """Schema for updating an existing certification entry."""

    name: Optional[str] = Field(None, min_length=1, max_length=300)
    issuing_organization: Optional[str] = Field(None, min_length=1, max_length=300)
    issue_date: Optional[date] = Field(None)
    expiration_date: Optional[date] = Field(None)
    credential_id: Optional[str] = Field(None, max_length=200)
    credential_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = Field(None)
    related_skills: Optional[list[str]] = Field(None)
    display_order: Optional[int] = Field(None, ge=0)


class CertificationResponse(BaseModel):
    """Schema for certification responses."""

    id: UUID = Field(..., description="Unique identifier")
    profile_id: UUID = Field(..., description="Owning profile ID")
    name: str = Field(..., description="Certification name")
    issuing_organization: str = Field(..., description="Issuing organization")
    issue_date: date = Field(..., description="Issue date")
    expiration_date: Optional[date] = Field(None, description="Expiration date")
    credential_id: Optional[str] = Field(None, description="Credential ID")
    credential_url: Optional[str] = Field(None, description="Credential URL")
    is_active: bool = Field(..., description="Whether active")
    related_skills: list[str] = Field(default_factory=list, description="Related skills")
    display_order: int = Field(..., description="Display order")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


class CertificationListResponse(BaseModel):
    """Schema for certification list responses."""

    items: list[CertificationResponse] = Field(..., description="List of certifications")
    total: int = Field(..., description="Total count")


# =============================================================================
# Job Listing Models
# =============================================================================


class JobListingCreate(BaseModel):
    """
    Schema for creating a job listing (typically from scraping).

    Attributes:
        url: Source URL of the job listing (required).
        job_title: Position title (required).
        description: Full job description (required).
        source_site: Website source (optional).
        company_name: Company name (optional).
        company_url: Company website URL (optional).
        location: Job location (optional).
        is_remote: Whether the position is remote (optional).
        salary_min: Minimum salary (optional).
        salary_max: Maximum salary (optional).
        salary_currency: Salary currency (default: USD).
        required_skills: Skills explicitly required (optional).
        preferred_skills: Skills listed as preferred (optional).
        requirements: Other requirements (optional).
        raw_html: Original HTML for re-parsing (optional).
        notes: User notes (optional).

    Example:
        JobListingCreate(
            url="https://linkedin.com/jobs/view/123456",
            job_title="Senior Software Engineer",
            company_name="Tech Corp",
            description="We are looking for...",
            required_skills=["Python", "AWS"]
        )
    """

    url: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Source URL of the job listing",
    )
    job_title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Position title",
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Full job description",
    )
    source_site: Optional[str] = Field(
        None,
        max_length=100,
        description="Website source (e.g., linkedin, indeed)",
    )
    company_name: Optional[str] = Field(
        None,
        max_length=300,
        description="Company name",
    )
    company_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Company website URL",
    )
    location: Optional[str] = Field(
        None,
        max_length=300,
        description="Job location",
    )
    is_remote: Optional[bool] = Field(
        None,
        description="Whether the position is remote",
    )
    salary_min: Optional[int] = Field(
        None,
        ge=0,
        description="Minimum salary",
    )
    salary_max: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum salary",
    )
    salary_currency: str = Field(
        "USD",
        max_length=10,
        description="Salary currency",
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="Skills explicitly required",
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description="Skills listed as preferred",
    )
    requirements: list[str] = Field(
        default_factory=list,
        description="Other requirements",
    )
    raw_html: Optional[str] = Field(
        None,
        description="Original HTML for re-parsing",
    )
    notes: Optional[str] = Field(
        None,
        description="User notes",
    )


class JobListingUpdate(BaseModel):
    """Schema for updating an existing job listing."""

    job_title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=10)
    company_name: Optional[str] = Field(None, max_length=300)
    company_url: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=300)
    is_remote: Optional[bool] = Field(None)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=10)
    required_skills: Optional[list[str]] = Field(None)
    preferred_skills: Optional[list[str]] = Field(None)
    requirements: Optional[list[str]] = Field(None)
    notes: Optional[str] = Field(None)
    is_favorite: Optional[bool] = Field(None)
    application_status: Optional[ApplicationStatus] = Field(None)
    applied_at: Optional[datetime] = Field(None)


class JobListingResponse(BaseModel):
    """Schema for job listing responses."""

    id: UUID = Field(..., description="Unique identifier")
    url: str = Field(..., description="Source URL")
    source_site: Optional[str] = Field(None, description="Website source")
    job_title: str = Field(..., description="Position title")
    company_name: Optional[str] = Field(None, description="Company name")
    company_url: Optional[str] = Field(None, description="Company URL")
    location: Optional[str] = Field(None, description="Job location")
    is_remote: Optional[bool] = Field(None, description="Whether remote")
    salary_min: Optional[int] = Field(None, description="Min salary")
    salary_max: Optional[int] = Field(None, description="Max salary")
    salary_currency: str = Field(..., description="Salary currency")
    description: str = Field(..., description="Job description")
    required_skills: list[str] = Field(default_factory=list, description="Required skills")
    preferred_skills: list[str] = Field(default_factory=list, description="Preferred skills")
    requirements: list[str] = Field(default_factory=list, description="Requirements")
    scraped_at: datetime = Field(..., description="When scraped")
    notes: Optional[str] = Field(None, description="User notes")
    is_favorite: bool = Field(..., description="Whether favorite")
    application_status: str = Field(..., description="Application status")
    applied_at: Optional[datetime] = Field(None, description="When applied")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


class JobListingListResponse(BaseModel):
    """Schema for job listing list responses with pagination."""

    items: list[JobListingResponse] = Field(..., description="List of job listings")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether more pages exist")


class JobScrapeRequest(BaseModel):
    """
    Schema for requesting job scraping.

    Attributes:
        url: URL of the job listing to scrape.

    Example:
        JobScrapeRequest(url="https://linkedin.com/jobs/view/123456")
    """

    url: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="URL of the job listing to scrape",
    )


# =============================================================================
# Generated Resume Models
# =============================================================================


class GeneratedResumeCreate(BaseModel):
    """
    Schema for creating a generated resume record.

    Attributes:
        name: Resume name/identifier (required).
        format: Output format (required).
        job_listing_id: Associated job listing ID (optional).
        drive_file_id: Google Drive file ID (optional).
        drive_file_url: Google Drive file URL (optional).
        drive_folder_id: Google Drive folder ID (optional).
        content_snapshot: JSON snapshot of data used (optional).
        included_skills: UUIDs of skills included (optional).
        skill_match_score: Required skills match percentage (optional).
        overall_match_score: Overall suitability score (optional).
        match_analysis: Detailed matching breakdown (optional).
        template_used: Template name used (default: default).
        generation_params: Generation parameters (optional).

    Example:
        GeneratedResumeCreate(
            name="Software_Engineer_Google_2025-01-15",
            format=ResumeFormat.PDF,
            skill_match_score=85.5
        )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Resume name/identifier",
    )
    format: ResumeFormat = Field(
        ...,
        description="Output format",
    )
    job_listing_id: Optional[UUID] = Field(
        None,
        description="Associated job listing ID",
    )
    drive_file_id: Optional[str] = Field(
        None,
        max_length=200,
        description="Google Drive file ID",
    )
    drive_file_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Google Drive file URL",
    )
    drive_folder_id: Optional[str] = Field(
        None,
        max_length=200,
        description="Google Drive folder ID",
    )
    content_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON snapshot of data used",
    )
    included_skills: list[UUID] = Field(
        default_factory=list,
        description="UUIDs of skills included",
    )
    skill_match_score: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        description="Required skills match percentage",
    )
    overall_match_score: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        description="Overall suitability score",
    )
    match_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed matching breakdown",
    )
    template_used: str = Field(
        "default",
        max_length=100,
        description="Template name used",
    )
    generation_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Generation parameters",
    )


class GeneratedResumeResponse(BaseModel):
    """Schema for generated resume responses."""

    id: UUID = Field(..., description="Unique identifier")
    profile_id: UUID = Field(..., description="Owning profile ID")
    job_listing_id: Optional[UUID] = Field(None, description="Job listing ID")
    name: str = Field(..., description="Resume name")
    format: ResumeFormat = Field(..., description="Output format")
    drive_file_id: Optional[str] = Field(None, description="Drive file ID")
    drive_file_url: Optional[str] = Field(None, description="Drive file URL")
    drive_folder_id: Optional[str] = Field(None, description="Drive folder ID")
    content_snapshot: dict[str, Any] = Field(default_factory=dict, description="Content snapshot")
    included_skills: list[UUID] = Field(default_factory=list, description="Included skill IDs")
    skill_match_score: Optional[Decimal] = Field(None, description="Skill match score")
    overall_match_score: Optional[Decimal] = Field(None, description="Overall match score")
    match_analysis: dict[str, Any] = Field(default_factory=dict, description="Match analysis")
    template_used: str = Field(..., description="Template used")
    generation_params: dict[str, Any] = Field(default_factory=dict, description="Gen params")
    generated_at: datetime = Field(..., description="When generated")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


class GeneratedResumeListResponse(BaseModel):
    """Schema for generated resume list responses with pagination."""

    items: list[GeneratedResumeResponse] = Field(..., description="List of resumes")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether more pages exist")


class ResumeGenerateRequest(BaseModel):
    """
    Schema for requesting resume generation.

    Attributes:
        job_listing_id: ID of the job listing to tailor for (optional).
        job_url: URL of job listing to scrape and tailor for (optional).
        format: Output format (default: pdf).
        template: Template to use (default: default).
        include_all_skills: Whether to include all skills or just matched ones.
        custom_summary: Custom professional summary override (optional).

    Note: Either job_listing_id or job_url should be provided, not both.

    Example:
        ResumeGenerateRequest(
            job_url="https://linkedin.com/jobs/view/123456",
            format=ResumeFormat.PDF
        )
    """

    job_listing_id: Optional[UUID] = Field(
        None,
        description="ID of existing job listing to tailor for",
    )
    job_url: Optional[str] = Field(
        None,
        max_length=2000,
        description="URL of job listing to scrape and tailor for",
    )
    format: ResumeFormat = Field(
        ResumeFormat.PDF,
        description="Output format",
    )
    template: str = Field(
        "default",
        max_length=100,
        description="Template to use",
    )
    include_all_skills: bool = Field(
        False,
        description="Include all skills or just matched ones",
    )
    custom_summary: Optional[str] = Field(
        None,
        description="Custom professional summary override",
    )

    @field_validator("job_url")
    @classmethod
    def validate_job_source(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure at least one job source is provided, but not both."""
        job_listing_id = info.data.get("job_listing_id")
        if v is None and job_listing_id is None:
            raise ValueError("Either job_listing_id or job_url must be provided")
        if v is not None and job_listing_id is not None:
            raise ValueError("Provide either job_listing_id or job_url, not both")
        return v


# =============================================================================
# Statistics and Analysis Models
# =============================================================================


class SkillMatchResult(BaseModel):
    """
    Schema for skill matching results.

    Attributes:
        skill_id: Skill UUID.
        skill_name: Skill name.
        match_type: Type of match (exact, keyword, fuzzy).
        confidence: Match confidence (0-1).
        matched_requirement: The job requirement it matched.
    """

    skill_id: UUID = Field(..., description="Skill UUID")
    skill_name: str = Field(..., description="Skill name")
    match_type: str = Field(..., description="Type of match")
    confidence: float = Field(..., ge=0, le=1, description="Match confidence")
    matched_requirement: str = Field(..., description="Matched requirement")


class ResumeMatchAnalysis(BaseModel):
    """
    Schema for resume-job match analysis.

    Attributes:
        job_listing_id: Job listing UUID.
        skill_match_score: Percentage of required skills matched.
        overall_match_score: Overall suitability score.
        matched_skills: Skills that matched job requirements.
        missing_skills: Required skills not in profile.
        bonus_skills: Profile skills that are preferred but not required.
        recommendations: Suggestions for improving match.
    """

    job_listing_id: UUID = Field(..., description="Job listing ID")
    skill_match_score: Decimal = Field(..., description="Skills match percentage")
    overall_match_score: Decimal = Field(..., description="Overall match score")
    matched_skills: list[SkillMatchResult] = Field(..., description="Matched skills")
    missing_skills: list[str] = Field(..., description="Missing required skills")
    bonus_skills: list[str] = Field(..., description="Preferred skills you have")
    recommendations: list[str] = Field(..., description="Improvement recommendations")


class ProfileStats(BaseModel):
    """
    Schema for profile statistics.

    Attributes:
        total_skills: Total number of skills.
        skills_by_category: Skills count by category.
        total_work_experience_years: Total years of work experience.
        total_positions: Number of work experience entries.
        total_education: Number of education entries.
        total_certifications: Number of certifications.
        active_certifications: Number of active certifications.
        total_generated_resumes: Number of resumes generated.
        total_job_listings: Number of saved job listings.
    """

    total_skills: int = Field(..., description="Total skills count")
    skills_by_category: dict[str, int] = Field(..., description="Skills by category")
    total_work_experience_years: Decimal = Field(..., description="Total work experience years")
    total_positions: int = Field(..., description="Number of positions")
    total_education: int = Field(..., description="Education entries count")
    total_certifications: int = Field(..., description="Certifications count")
    active_certifications: int = Field(..., description="Active certifications")
    total_generated_resumes: int = Field(..., description="Generated resumes count")
    total_job_listings: int = Field(..., description="Saved job listings count")
