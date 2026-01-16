-- Migration: 006_create_resume_tables.sql
-- Description: Create resume schema with tables for user profiles, skills, work experience,
--              education, certifications, job listings, and generated resumes.
-- Author: Claude Assistant
-- Date: 2025-01-15

-- ============================================================================
-- SCHEMA CREATION
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS resume;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

-- Skill proficiency levels
CREATE TYPE resume.skill_proficiency AS ENUM (
    'beginner',
    'intermediate',
    'advanced',
    'expert'
);

-- Skill categories for organization
CREATE TYPE resume.skill_category AS ENUM (
    'programming_language',
    'framework',
    'database',
    'cloud',
    'devops',
    'soft_skill',
    'tool',
    'methodology',
    'other'
);

-- Employment types
CREATE TYPE resume.employment_type AS ENUM (
    'full_time',
    'part_time',
    'contract',
    'freelance',
    'internship'
);

-- Education degree types
CREATE TYPE resume.degree_type AS ENUM (
    'high_school',
    'associate',
    'bachelor',
    'master',
    'doctorate',
    'certificate',
    'bootcamp',
    'other'
);

-- Resume output formats
CREATE TYPE resume.resume_format AS ENUM (
    'pdf',
    'docx'
);

-- ============================================================================
-- USER PROFILES TABLE
-- ============================================================================
-- Single-user profile containing personal info, contact details, and summary.
-- This is the central table that all other resume data relates to.

CREATE TABLE IF NOT EXISTS resume.user_profiles (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Personal information
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),

    -- Location
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'United States',

    -- Professional links
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    portfolio_url VARCHAR(500),
    personal_website VARCHAR(500),

    -- Professional summary (tailored per resume, but this is the default)
    professional_summary TEXT,

    -- Optional: Link to Telegram user for future multi-user support
    telegram_user_id BIGINT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for documentation
COMMENT ON TABLE resume.user_profiles IS 'User profile information for resume generation';
COMMENT ON COLUMN resume.user_profiles.professional_summary IS 'Default professional summary, can be customized per generated resume';
COMMENT ON COLUMN resume.user_profiles.telegram_user_id IS 'Links profile to Telegram identity for future multi-user support';
COMMENT ON COLUMN resume.user_profiles.metadata IS 'Flexible JSON storage for additional profile data';

-- ============================================================================
-- SKILLS TABLE
-- ============================================================================
-- Skills with category, proficiency level, and years of experience.
-- Used for matching against job requirements.

CREATE TABLE IF NOT EXISTS resume.skills (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to user profile
    profile_id UUID NOT NULL REFERENCES resume.user_profiles(id) ON DELETE CASCADE,

    -- Skill details
    name VARCHAR(200) NOT NULL,
    category resume.skill_category NOT NULL DEFAULT 'other',
    proficiency resume.skill_proficiency NOT NULL DEFAULT 'intermediate',
    years_experience NUMERIC(4,1) CHECK (years_experience >= 0 AND years_experience <= 50),

    -- Optional: Keywords for better job matching
    keywords TEXT[] DEFAULT '{}',

    -- Display order for resume
    display_order INTEGER DEFAULT 0,

    -- Whether to include by default in resumes
    is_featured BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure unique skill names per profile
    CONSTRAINT unique_skill_per_profile UNIQUE (profile_id, name)
);

-- Comments for documentation
COMMENT ON TABLE resume.skills IS 'User skills for resume generation and job matching';
COMMENT ON COLUMN resume.skills.keywords IS 'Alternative names/keywords for better job requirement matching';
COMMENT ON COLUMN resume.skills.is_featured IS 'Skills marked as featured are prioritized in resume generation';

-- Indexes for efficient querying
CREATE INDEX idx_skills_profile_id ON resume.skills(profile_id);
CREATE INDEX idx_skills_category ON resume.skills(category);
CREATE INDEX idx_skills_proficiency ON resume.skills(proficiency);
CREATE INDEX idx_skills_featured ON resume.skills(profile_id) WHERE is_featured = TRUE;
CREATE INDEX idx_skills_keywords ON resume.skills USING GIN (keywords);

-- ============================================================================
-- WORK EXPERIENCES TABLE
-- ============================================================================
-- Job history with company, role, dates, and achievements.

CREATE TABLE IF NOT EXISTS resume.work_experiences (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to user profile
    profile_id UUID NOT NULL REFERENCES resume.user_profiles(id) ON DELETE CASCADE,

    -- Company information
    company_name VARCHAR(300) NOT NULL,
    company_url VARCHAR(500),
    company_location VARCHAR(200),

    -- Role information
    job_title VARCHAR(300) NOT NULL,
    employment_type resume.employment_type DEFAULT 'full_time',

    -- Dates
    start_date DATE NOT NULL,
    end_date DATE, -- NULL means current position
    is_current BOOLEAN DEFAULT FALSE,

    -- Description and achievements
    description TEXT,
    achievements TEXT[] DEFAULT '{}', -- Bullet points

    -- Skills used in this role (for matching)
    skills_used TEXT[] DEFAULT '{}',

    -- Display order for resume
    display_order INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure end_date is after start_date if provided
    CONSTRAINT valid_date_range CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Comments for documentation
COMMENT ON TABLE resume.work_experiences IS 'Work history for resume generation';
COMMENT ON COLUMN resume.work_experiences.achievements IS 'Array of achievement bullet points';
COMMENT ON COLUMN resume.work_experiences.skills_used IS 'Skills used in this role for job matching';
COMMENT ON COLUMN resume.work_experiences.is_current IS 'Indicates this is the current position';

-- Indexes for efficient querying
CREATE INDEX idx_work_experiences_profile_id ON resume.work_experiences(profile_id);
CREATE INDEX idx_work_experiences_dates ON resume.work_experiences(start_date DESC, end_date DESC NULLS FIRST);
CREATE INDEX idx_work_experiences_skills ON resume.work_experiences USING GIN (skills_used);

-- ============================================================================
-- EDUCATION TABLE
-- ============================================================================
-- Educational background including degrees, institutions, and coursework.

CREATE TABLE IF NOT EXISTS resume.education (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to user profile
    profile_id UUID NOT NULL REFERENCES resume.user_profiles(id) ON DELETE CASCADE,

    -- Institution information
    institution_name VARCHAR(300) NOT NULL,
    institution_location VARCHAR(200),
    institution_url VARCHAR(500),

    -- Degree information
    degree_type resume.degree_type NOT NULL,
    degree_name VARCHAR(300), -- e.g., "Bachelor of Science"
    field_of_study VARCHAR(300) NOT NULL, -- e.g., "Computer Science"

    -- Dates
    start_date DATE,
    end_date DATE, -- Graduation date or expected
    is_in_progress BOOLEAN DEFAULT FALSE,

    -- Academic details
    gpa NUMERIC(3,2) CHECK (gpa >= 0 AND gpa <= 4.0),
    gpa_scale NUMERIC(3,1) DEFAULT 4.0, -- Some use 5.0 or 10.0 scale

    -- Additional details
    honors TEXT[] DEFAULT '{}', -- Dean's list, Magna Cum Laude, etc.
    relevant_coursework TEXT[] DEFAULT '{}',
    activities TEXT[] DEFAULT '{}',

    -- Display order for resume
    display_order INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for documentation
COMMENT ON TABLE resume.education IS 'Educational background for resume generation';
COMMENT ON COLUMN resume.education.honors IS 'Academic honors and distinctions';
COMMENT ON COLUMN resume.education.relevant_coursework IS 'Relevant courses for job applications';

-- Indexes for efficient querying
CREATE INDEX idx_education_profile_id ON resume.education(profile_id);
CREATE INDEX idx_education_dates ON resume.education(end_date DESC NULLS FIRST);

-- ============================================================================
-- CERTIFICATIONS TABLE
-- ============================================================================
-- Professional certifications and credentials.

CREATE TABLE IF NOT EXISTS resume.certifications (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to user profile
    profile_id UUID NOT NULL REFERENCES resume.user_profiles(id) ON DELETE CASCADE,

    -- Certification details
    name VARCHAR(300) NOT NULL,
    issuing_organization VARCHAR(300) NOT NULL,
    credential_id VARCHAR(200),
    credential_url VARCHAR(500),

    -- Dates
    issue_date DATE NOT NULL,
    expiration_date DATE, -- NULL means no expiration

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Skills associated with this certification
    related_skills TEXT[] DEFAULT '{}',

    -- Display order for resume
    display_order INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for documentation
COMMENT ON TABLE resume.certifications IS 'Professional certifications for resume generation';
COMMENT ON COLUMN resume.certifications.is_active IS 'Whether the certification is currently active';
COMMENT ON COLUMN resume.certifications.related_skills IS 'Skills this certification validates';

-- Indexes for efficient querying
CREATE INDEX idx_certifications_profile_id ON resume.certifications(profile_id);
CREATE INDEX idx_certifications_active ON resume.certifications(profile_id) WHERE is_active = TRUE;
CREATE INDEX idx_certifications_skills ON resume.certifications USING GIN (related_skills);

-- ============================================================================
-- JOB LISTINGS TABLE
-- ============================================================================
-- Scraped job descriptions for resume tailoring.

CREATE TABLE IF NOT EXISTS resume.job_listings (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source information
    url VARCHAR(2000) NOT NULL,
    source_site VARCHAR(100), -- 'linkedin', 'indeed', 'greenhouse', etc.

    -- Job details
    job_title VARCHAR(500) NOT NULL,
    company_name VARCHAR(300),
    company_url VARCHAR(500),
    location VARCHAR(300),
    is_remote BOOLEAN,

    -- Salary information (if available)
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'USD',

    -- Job description
    description TEXT NOT NULL,

    -- Extracted requirements (parsed from description)
    required_skills TEXT[] DEFAULT '{}',
    preferred_skills TEXT[] DEFAULT '{}',
    requirements TEXT[] DEFAULT '{}', -- Other requirements (education, experience, etc.)

    -- Raw HTML for reference
    raw_html TEXT,

    -- Scraping metadata
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- User notes
    notes TEXT,
    is_favorite BOOLEAN DEFAULT FALSE,

    -- Application status
    application_status VARCHAR(50) DEFAULT 'not_applied',
    applied_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure unique URLs
    CONSTRAINT unique_job_url UNIQUE (url)
);

-- Comments for documentation
COMMENT ON TABLE resume.job_listings IS 'Scraped job listings for resume tailoring';
COMMENT ON COLUMN resume.job_listings.required_skills IS 'Skills explicitly required in the job description';
COMMENT ON COLUMN resume.job_listings.preferred_skills IS 'Skills listed as preferred or nice-to-have';
COMMENT ON COLUMN resume.job_listings.raw_html IS 'Original HTML for re-parsing if needed';

-- Indexes for efficient querying
CREATE INDEX idx_job_listings_source ON resume.job_listings(source_site);
CREATE INDEX idx_job_listings_company ON resume.job_listings(company_name);
CREATE INDEX idx_job_listings_scraped ON resume.job_listings(scraped_at DESC);
CREATE INDEX idx_job_listings_favorite ON resume.job_listings(id) WHERE is_favorite = TRUE;
CREATE INDEX idx_job_listings_required_skills ON resume.job_listings USING GIN (required_skills);
CREATE INDEX idx_job_listings_preferred_skills ON resume.job_listings USING GIN (preferred_skills);

-- ============================================================================
-- GENERATED RESUMES TABLE
-- ============================================================================
-- Records of generated resumes with Google Drive file references.

CREATE TABLE IF NOT EXISTS resume.generated_resumes (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys
    profile_id UUID NOT NULL REFERENCES resume.user_profiles(id) ON DELETE CASCADE,
    job_listing_id UUID REFERENCES resume.job_listings(id) ON DELETE SET NULL,

    -- Resume metadata
    name VARCHAR(300) NOT NULL, -- e.g., "Software_Engineer_Google_2025-01-15"
    format resume.resume_format NOT NULL,

    -- Google Drive storage
    drive_file_id VARCHAR(200),
    drive_file_url VARCHAR(500),
    drive_folder_id VARCHAR(200),

    -- Content snapshot (for versioning)
    content_snapshot JSONB DEFAULT '{}', -- Stores the exact data used to generate

    -- Skills included in this resume
    included_skills UUID[] DEFAULT '{}', -- References to skills table

    -- Match analysis
    skill_match_score NUMERIC(5,2), -- Percentage of required skills matched
    overall_match_score NUMERIC(5,2), -- Overall suitability score
    match_analysis JSONB DEFAULT '{}', -- Detailed matching breakdown

    -- Generation metadata
    template_used VARCHAR(100) DEFAULT 'default',
    generation_params JSONB DEFAULT '{}',

    -- Timestamps
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for documentation
COMMENT ON TABLE resume.generated_resumes IS 'Generated resume records with Google Drive references';
COMMENT ON COLUMN resume.generated_resumes.content_snapshot IS 'JSON snapshot of profile/skills/experience used for this resume';
COMMENT ON COLUMN resume.generated_resumes.included_skills IS 'Array of skill UUIDs included in this resume';
COMMENT ON COLUMN resume.generated_resumes.match_analysis IS 'Detailed skill and requirement matching breakdown';

-- Indexes for efficient querying
CREATE INDEX idx_generated_resumes_profile_id ON resume.generated_resumes(profile_id);
CREATE INDEX idx_generated_resumes_job_listing_id ON resume.generated_resumes(job_listing_id);
CREATE INDEX idx_generated_resumes_generated_at ON resume.generated_resumes(generated_at DESC);
CREATE INDEX idx_generated_resumes_match_score ON resume.generated_resumes(skill_match_score DESC);

-- ============================================================================
-- TRIGGER FUNCTION FOR AUTO-UPDATING TIMESTAMPS
-- ============================================================================

CREATE OR REPLACE FUNCTION resume.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON resume.user_profiles
    FOR EACH ROW EXECUTE FUNCTION resume.update_updated_at_column();

CREATE TRIGGER update_skills_updated_at
    BEFORE UPDATE ON resume.skills
    FOR EACH ROW EXECUTE FUNCTION resume.update_updated_at_column();

CREATE TRIGGER update_work_experiences_updated_at
    BEFORE UPDATE ON resume.work_experiences
    FOR EACH ROW EXECUTE FUNCTION resume.update_updated_at_column();

CREATE TRIGGER update_education_updated_at
    BEFORE UPDATE ON resume.education
    FOR EACH ROW EXECUTE FUNCTION resume.update_updated_at_column();

CREATE TRIGGER update_certifications_updated_at
    BEFORE UPDATE ON resume.certifications
    FOR EACH ROW EXECUTE FUNCTION resume.update_updated_at_column();

CREATE TRIGGER update_job_listings_updated_at
    BEFORE UPDATE ON resume.job_listings
    FOR EACH ROW EXECUTE FUNCTION resume.update_updated_at_column();

CREATE TRIGGER update_generated_resumes_updated_at
    BEFORE UPDATE ON resume.generated_resumes
    FOR EACH ROW EXECUTE FUNCTION resume.update_updated_at_column();

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
-- Run this after migration to verify all tables were created:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'resume';
