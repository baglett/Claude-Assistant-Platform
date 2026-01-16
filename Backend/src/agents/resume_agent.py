# =============================================================================
# Resume Agent
# =============================================================================
"""
Specialized agent for resume generation and profile management.

The ResumeAgent handles all resume-related operations including managing
profile data, skills, work experience, education, certifications, scraping
job listings, generating tailored resumes, and uploading to Google Drive.

Usage:
    from src.agents.resume_agent import ResumeAgent

    agent = ResumeAgent(
        api_key=api_key,
        mcp_url="http://google-drive-mcp:8087"
    )
    result = await agent.execute(context)
"""

import base64
import json
import logging
import os
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import anthropic
import httpx

from src.agents.base import AgentContext, AgentResult, BaseAgent
from src.database import AgentExecution
from src.models.resume import (
    CertificationCreate,
    EducationCreate,
    GeneratedResumeCreate,
    JobListingCreate,
    ProfileCreate,
    ProfileUpdate,
    ResumeFormat,
    SkillCategory,
    SkillCreate,
    SkillProficiency,
    WorkExperienceCreate,
)
from src.services.agent_execution_service import AgentExecutionService
from src.services.resume.certification_service import CertificationService
from src.services.resume.education_service import EducationService
from src.services.resume.generated_resume_service import GeneratedResumeService
from src.services.resume.job_listing_service import JobListingService
from src.services.resume.profile_service import ProfileService
from src.services.resume.skill_service import SkillService
from src.services.resume.work_experience_service import WorkExperienceService
from src.services.scraper import JobScraperService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Resume Agent System Prompt
# -----------------------------------------------------------------------------
RESUME_AGENT_SYSTEM_PROMPT = """You are the Resume Agent for the Claude Assistant Platform.

Your responsibility is managing resume data and generating tailored resumes for job applications.

## Core Capabilities:

### Profile Management
- **get_profile**: View the user's profile information
- **update_profile**: Update personal info, contact details, links, summary

### Skills Management
- **list_skills**: List all skills with optional filtering
- **add_skill**: Add a new skill with category, proficiency, years
- **update_skill**: Modify an existing skill
- **delete_skill**: Remove a skill

### Work Experience Management
- **list_work_experience**: List all work experience entries
- **add_work_experience**: Add a job/position with company, dates, achievements
- **update_work_experience**: Modify work experience
- **delete_work_experience**: Remove work experience

### Education Management
- **list_education**: List all education entries
- **add_education**: Add a degree, institution, dates
- **update_education**: Modify education entry
- **delete_education**: Remove education entry

### Certifications Management
- **list_certifications**: List all certifications
- **add_certification**: Add a certification with issuer, dates
- **update_certification**: Modify certification
- **delete_certification**: Remove certification

### Job Listings
- **scrape_job**: Scrape a job listing from a URL
- **list_job_listings**: List scraped job listings
- **get_job_listing**: Get details of a specific job

### Resume Generation
- **match_skills**: Calculate skill match score for a job
- **generate_resume**: Create a tailored resume for a job
- **list_generated_resumes**: View previously generated resumes
- **upload_to_drive**: Upload a resume to Google Drive

## Skill Categories:
- programming_language: Python, JavaScript, Java, etc.
- framework: React, Django, FastAPI, etc.
- database: PostgreSQL, MongoDB, Redis, etc.
- cloud: AWS, GCP, Azure services
- devops: Docker, Kubernetes, CI/CD tools
- soft_skill: Leadership, Communication, etc.
- tool: Git, VS Code, Jira, etc.
- domain: Finance, Healthcare, etc.
- certification: AWS Certified, PMP, etc.
- other: Everything else

## Proficiency Levels:
- beginner: Just started learning
- intermediate: Can use independently
- advanced: Deep knowledge
- expert: Can teach others

## When Generating Resumes:
1. First scrape the job listing if not already done
2. Load the user's profile and skills
3. Match skills to job requirements
4. Tailor the resume content (reorder skills, customize summary)
5. Generate the resume file
6. Optionally upload to Google Drive

Be helpful and confirm actions taken. Guide the user through adding their information if their profile is incomplete."""


# -----------------------------------------------------------------------------
# Resume Agent Tool Definitions
# -----------------------------------------------------------------------------
RESUME_TOOLS = [
    # Profile Tools
    {
        "name": "get_profile",
        "description": "Get the user's profile information including skills, experience, education.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_stats": {
                    "type": "boolean",
                    "description": "Include profile statistics (counts, totals).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "update_profile",
        "description": "Update the user's profile information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string", "description": "First name."},
                "last_name": {"type": "string", "description": "Last name."},
                "email": {"type": "string", "description": "Email address."},
                "phone": {"type": "string", "description": "Phone number."},
                "city": {"type": "string", "description": "City."},
                "state": {"type": "string", "description": "State/Province."},
                "country": {"type": "string", "description": "Country."},
                "linkedin_url": {"type": "string", "description": "LinkedIn profile URL."},
                "github_url": {"type": "string", "description": "GitHub profile URL."},
                "portfolio_url": {"type": "string", "description": "Portfolio website URL."},
                "personal_website": {"type": "string", "description": "Personal website URL."},
                "professional_summary": {
                    "type": "string",
                    "description": "Professional summary for resume header.",
                },
            },
            "required": [],
        },
    },
    # Skills Tools
    {
        "name": "list_skills",
        "description": "List all skills with optional filtering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "programming_language",
                        "framework",
                        "database",
                        "cloud",
                        "devops",
                        "soft_skill",
                        "tool",
                        "domain",
                        "certification",
                        "other",
                    ],
                    "description": "Filter by skill category.",
                },
                "is_featured": {
                    "type": "boolean",
                    "description": "Filter to only featured skills.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_skill",
        "description": "Add a new skill to the profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill name (e.g., 'Python')."},
                "category": {
                    "type": "string",
                    "enum": [
                        "programming_language",
                        "framework",
                        "database",
                        "cloud",
                        "devops",
                        "soft_skill",
                        "tool",
                        "domain",
                        "certification",
                        "other",
                    ],
                    "description": "Skill category.",
                },
                "proficiency": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced", "expert"],
                    "description": "Proficiency level.",
                },
                "years_experience": {
                    "type": "number",
                    "description": "Years of experience with this skill.",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Related keywords for matching.",
                },
                "is_featured": {
                    "type": "boolean",
                    "description": "Whether to feature this skill prominently.",
                },
            },
            "required": ["name", "category"],
        },
    },
    {
        "name": "update_skill",
        "description": "Update an existing skill.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "Skill UUID to update."},
                "name": {"type": "string", "description": "New skill name."},
                "category": {
                    "type": "string",
                    "enum": [
                        "programming_language",
                        "framework",
                        "database",
                        "cloud",
                        "devops",
                        "soft_skill",
                        "tool",
                        "domain",
                        "certification",
                        "other",
                    ],
                },
                "proficiency": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced", "expert"],
                },
                "years_experience": {"type": "number"},
                "is_featured": {"type": "boolean"},
            },
            "required": ["skill_id"],
        },
    },
    {
        "name": "delete_skill",
        "description": "Delete a skill from the profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "Skill UUID to delete."},
            },
            "required": ["skill_id"],
        },
    },
    # Work Experience Tools
    {
        "name": "list_work_experience",
        "description": "List all work experience entries.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "add_work_experience",
        "description": "Add a new work experience entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Company name."},
                "job_title": {"type": "string", "description": "Job title/position."},
                "location": {"type": "string", "description": "Work location."},
                "is_remote": {"type": "boolean", "description": "Whether remote work."},
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD).",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD), omit if current.",
                },
                "is_current": {"type": "boolean", "description": "Whether current job."},
                "description": {"type": "string", "description": "Job description."},
                "achievements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key achievements.",
                },
                "technologies_used": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Technologies/tools used.",
                },
            },
            "required": ["company_name", "job_title", "start_date"],
        },
    },
    {
        "name": "update_work_experience",
        "description": "Update an existing work experience entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "experience_id": {"type": "string", "description": "Experience UUID."},
                "company_name": {"type": "string"},
                "job_title": {"type": "string"},
                "location": {"type": "string"},
                "is_remote": {"type": "boolean"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "is_current": {"type": "boolean"},
                "description": {"type": "string"},
                "achievements": {"type": "array", "items": {"type": "string"}},
                "technologies_used": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["experience_id"],
        },
    },
    {
        "name": "delete_work_experience",
        "description": "Delete a work experience entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "experience_id": {"type": "string", "description": "Experience UUID."},
            },
            "required": ["experience_id"],
        },
    },
    # Education Tools
    {
        "name": "list_education",
        "description": "List all education entries.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "add_education",
        "description": "Add a new education entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "institution_name": {"type": "string", "description": "School/University."},
                "degree": {"type": "string", "description": "Degree type (e.g., Bachelor's)."},
                "field_of_study": {"type": "string", "description": "Major/Field of study."},
                "location": {"type": "string", "description": "Location."},
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)."},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)."},
                "is_current": {"type": "boolean", "description": "Currently enrolled."},
                "gpa": {"type": "number", "description": "GPA if applicable."},
                "honors": {"type": "string", "description": "Honors/Awards."},
                "relevant_coursework": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relevant courses.",
                },
                "activities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Activities/Organizations.",
                },
            },
            "required": ["institution_name", "degree", "field_of_study"],
        },
    },
    {
        "name": "update_education",
        "description": "Update an existing education entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "education_id": {"type": "string", "description": "Education UUID."},
                "institution_name": {"type": "string"},
                "degree": {"type": "string"},
                "field_of_study": {"type": "string"},
                "location": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "is_current": {"type": "boolean"},
                "gpa": {"type": "number"},
                "honors": {"type": "string"},
            },
            "required": ["education_id"],
        },
    },
    {
        "name": "delete_education",
        "description": "Delete an education entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "education_id": {"type": "string", "description": "Education UUID."},
            },
            "required": ["education_id"],
        },
    },
    # Certification Tools
    {
        "name": "list_certifications",
        "description": "List all certifications.",
        "input_schema": {
            "type": "object",
            "properties": {
                "is_active": {"type": "boolean", "description": "Filter by active status."},
            },
            "required": [],
        },
    },
    {
        "name": "add_certification",
        "description": "Add a new certification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Certification name."},
                "issuing_organization": {"type": "string", "description": "Issuer."},
                "issue_date": {"type": "string", "description": "Issue date (YYYY-MM-DD)."},
                "expiration_date": {"type": "string", "description": "Expiration date."},
                "credential_id": {"type": "string", "description": "Credential ID."},
                "credential_url": {"type": "string", "description": "Verification URL."},
            },
            "required": ["name", "issuing_organization"],
        },
    },
    {
        "name": "update_certification",
        "description": "Update an existing certification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "certification_id": {"type": "string", "description": "Certification UUID."},
                "name": {"type": "string"},
                "issuing_organization": {"type": "string"},
                "issue_date": {"type": "string"},
                "expiration_date": {"type": "string"},
                "credential_id": {"type": "string"},
                "credential_url": {"type": "string"},
            },
            "required": ["certification_id"],
        },
    },
    {
        "name": "delete_certification",
        "description": "Delete a certification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "certification_id": {"type": "string", "description": "Certification UUID."},
            },
            "required": ["certification_id"],
        },
    },
    # Job Listing Tools
    {
        "name": "scrape_job",
        "description": "Scrape a job listing from a URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Job listing URL."},
                "use_claude_fallback": {
                    "type": "boolean",
                    "description": "Use Claude to parse unrecognized sites.",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "list_job_listings",
        "description": "List scraped job listings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_query": {"type": "string", "description": "Search in title/company."},
                "is_favorite": {"type": "boolean", "description": "Filter favorites."},
                "limit": {"type": "integer", "description": "Max results (default 10)."},
            },
            "required": [],
        },
    },
    {
        "name": "get_job_listing",
        "description": "Get details of a specific job listing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job listing UUID."},
            },
            "required": ["job_id"],
        },
    },
    # Resume Generation Tools
    {
        "name": "match_skills",
        "description": "Calculate skill match score between profile and job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job listing UUID to match."},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "generate_resume",
        "description": "Generate a tailored resume for a job listing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job listing UUID."},
                "format": {
                    "type": "string",
                    "enum": ["pdf", "docx"],
                    "description": "Output format (default: pdf).",
                },
                "template": {
                    "type": "string",
                    "description": "Template name to use.",
                },
                "upload_to_drive": {
                    "type": "boolean",
                    "description": "Auto-upload to Google Drive.",
                },
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "list_generated_resumes",
        "description": "List previously generated resumes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Filter by job listing."},
                "limit": {"type": "integer", "description": "Max results (default 10)."},
            },
            "required": [],
        },
    },
    {
        "name": "upload_to_drive",
        "description": "Upload a generated resume to Google Drive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resume_id": {"type": "string", "description": "Generated resume UUID."},
                "folder_name": {
                    "type": "string",
                    "description": "Drive folder name (default: 'Resumes').",
                },
            },
            "required": ["resume_id"],
        },
    },
]


# -----------------------------------------------------------------------------
# Resume Agent Class
# -----------------------------------------------------------------------------
class ResumeAgent(BaseAgent):
    """
    Specialized agent for resume generation and profile management.

    Handles all resume-related operations via Claude's tool calling.
    Communicates with Google Drive MCP for file storage.

    Attributes:
        client: Anthropic API client.
        model: Claude model to use.
        mcp_url: URL of the Google Drive MCP server.
        http_client: Async HTTP client for MCP calls.

    Example:
        agent = ResumeAgent(
            api_key="sk-...",
            mcp_url="http://google-drive-mcp:8087"
        )
        context = AgentContext(
            chat_id=chat_uuid,
            task="Generate a resume for this job: https://linkedin.com/jobs/...",
            session=session,
        )
        result = await agent.execute(context)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        mcp_url: str | None = None,
    ):
        """
        Initialize the Resume Agent.

        Args:
            api_key: Anthropic API key.
            model: Claude model to use.
            mcp_url: URL of the Google Drive MCP server (optional).
        """
        super().__init__(api_key=api_key, model=model)
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

        # Get MCP URL from environment or parameter
        drive_host = os.environ.get("GOOGLE_DRIVE_MCP_HOST", "google-drive-mcp")
        drive_port = os.environ.get("GOOGLE_DRIVE_MCP_PORT", "8087")
        self.mcp_url = mcp_url or f"http://{drive_host}:{drive_port}"
        self.mcp_url = self.mcp_url.rstrip("/")

        self._http_client: httpx.AsyncClient | None = None

        # Token tracking for execution logging
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

    @property
    def name(self) -> str:
        """Agent identifier."""
        return "resume"

    @property
    def description(self) -> str:
        """Agent description."""
        return "Manages resume data and generates tailored resumes for job applications"

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create the async HTTP client for MCP calls.

        Returns:
            The httpx.AsyncClient instance.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def _execute_task(
        self,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> AgentResult:
        """
        Execute the resume management task.

        Uses Claude's tool calling to determine and execute the appropriate
        resume operations based on the task description.

        Args:
            context: Execution context with task and chat info.
            execution_service: Service for logging execution details.
            execution: Current execution record.

        Returns:
            AgentResult with the outcome.
        """
        if not self.client:
            return AgentResult(
                success=False,
                message="API client not initialized",
                error="No API key provided",
            )

        # Reset token counters
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

        # Build messages for Claude
        messages = self._build_messages(context)

        # Log initial thinking
        await self.log_thinking(
            execution_service,
            execution,
            f"Processing resume task: {context.task}\n"
            f"Google Drive MCP URL: {self.mcp_url}",
        )

        # Process with tool calling loop
        try:
            result_text = await self._process_with_tools(
                messages=messages,
                context=context,
                execution_service=execution_service,
                execution=execution,
            )

            return AgentResult(
                success=True,
                message=result_text,
            )

        except Exception as e:
            logger.error(f"ResumeAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                message=f"Failed to process resume request: {str(e)}",
                error=str(e),
            )

    def _build_messages(self, context: AgentContext) -> list[dict[str, Any]]:
        """
        Build the message list for Claude.

        Args:
            context: The agent context.

        Returns:
            List of messages in Claude format.
        """
        messages = []

        # Add recent conversation context (limit to avoid token overflow)
        for msg in context.recent_messages[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add the current task as the final user message
        messages.append({
            "role": "user",
            "content": context.task,
        })

        return messages

    async def _process_with_tools(
        self,
        messages: list[dict[str, Any]],
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
        max_iterations: int = 15,
    ) -> str:
        """
        Process the task with tool calling loop.

        Args:
            messages: Conversation messages.
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.
            max_iterations: Max tool call iterations.

        Returns:
            Final response text.
        """
        working_messages = list(messages)

        for iteration in range(max_iterations):
            logger.debug(f"ResumeAgent tool loop iteration {iteration + 1}")

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=RESUME_AGENT_SYSTEM_PROMPT,
                tools=RESUME_TOOLS,
                messages=working_messages,
            )

            # Track tokens
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._llm_calls += 1

            # Check stop reason
            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            elif response.stop_reason == "tool_use":
                # Process tool calls
                await self.log_thinking(
                    execution_service,
                    execution,
                    f"Iteration {iteration + 1}: Processing resume tool calls",
                )

                # Add assistant response to messages
                working_messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Execute tools and get results
                tool_results = await self._execute_tools(
                    response.content,
                    context,
                    execution_service,
                    execution,
                )

                # Add tool results to messages
                working_messages.append({
                    "role": "user",
                    "content": tool_results,
                })

            else:
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                return self._extract_text(response)

        return "Max iterations reached. Please try a simpler request."

    async def _execute_tools(
        self,
        content_blocks: list,
        context: AgentContext,
        execution_service: AgentExecutionService,
        execution: AgentExecution,
    ) -> list[dict[str, Any]]:
        """
        Execute tool calls from Claude's response.

        Args:
            content_blocks: Response content blocks.
            context: Agent context.
            execution_service: For logging.
            execution: Current execution.

        Returns:
            List of tool result blocks.
        """
        tool_results = []

        # Initialize services
        profile_service = ProfileService(context.session)
        skill_service = SkillService(context.session)
        work_exp_service = WorkExperienceService(context.session)
        education_service = EducationService(context.session)
        certification_service = CertificationService(context.session)
        job_listing_service = JobListingService(context.session)
        resume_service = GeneratedResumeService(context.session)

        services = {
            "profile": profile_service,
            "skill": skill_service,
            "work_exp": work_exp_service,
            "education": education_service,
            "certification": certification_service,
            "job_listing": job_listing_service,
            "resume": resume_service,
        }

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"ResumeAgent executing tool: {tool_name}")
            start_time = time.time()

            try:
                # Execute the tool
                result = await self._execute_single_tool(
                    tool_name,
                    tool_input,
                    services,
                    context,
                )

                duration_ms = int((time.time() - start_time) * 1000)

                # Log the tool call
                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    output_data=result,
                    duration_ms=duration_ms,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)

                duration_ms = int((time.time() - start_time) * 1000)

                await self.log_tool_call(
                    execution_service,
                    execution,
                    tool_name=tool_name,
                    input_data=tool_input,
                    error=str(e),
                    duration_ms=duration_ms,
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"success": False, "error": str(e)}),
                    "is_error": True,
                })

        return tool_results

    async def _execute_single_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        services: dict[str, Any],
        context: AgentContext,
    ) -> dict[str, Any]:
        """
        Execute a single tool and return the result.

        Args:
            tool_name: Name of the tool.
            tool_input: Input parameters.
            services: Dictionary of service instances.
            context: Agent context.

        Returns:
            Tool execution result.
        """
        # Profile tools
        if tool_name == "get_profile":
            return await self._tool_get_profile(tool_input, services)
        elif tool_name == "update_profile":
            return await self._tool_update_profile(tool_input, services)

        # Skill tools
        elif tool_name == "list_skills":
            return await self._tool_list_skills(tool_input, services)
        elif tool_name == "add_skill":
            return await self._tool_add_skill(tool_input, services)
        elif tool_name == "update_skill":
            return await self._tool_update_skill(tool_input, services)
        elif tool_name == "delete_skill":
            return await self._tool_delete_skill(tool_input, services)

        # Work experience tools
        elif tool_name == "list_work_experience":
            return await self._tool_list_work_experience(services)
        elif tool_name == "add_work_experience":
            return await self._tool_add_work_experience(tool_input, services)
        elif tool_name == "update_work_experience":
            return await self._tool_update_work_experience(tool_input, services)
        elif tool_name == "delete_work_experience":
            return await self._tool_delete_work_experience(tool_input, services)

        # Education tools
        elif tool_name == "list_education":
            return await self._tool_list_education(services)
        elif tool_name == "add_education":
            return await self._tool_add_education(tool_input, services)
        elif tool_name == "update_education":
            return await self._tool_update_education(tool_input, services)
        elif tool_name == "delete_education":
            return await self._tool_delete_education(tool_input, services)

        # Certification tools
        elif tool_name == "list_certifications":
            return await self._tool_list_certifications(tool_input, services)
        elif tool_name == "add_certification":
            return await self._tool_add_certification(tool_input, services)
        elif tool_name == "update_certification":
            return await self._tool_update_certification(tool_input, services)
        elif tool_name == "delete_certification":
            return await self._tool_delete_certification(tool_input, services)

        # Job listing tools
        elif tool_name == "scrape_job":
            return await self._tool_scrape_job(tool_input, services, context)
        elif tool_name == "list_job_listings":
            return await self._tool_list_job_listings(tool_input, services)
        elif tool_name == "get_job_listing":
            return await self._tool_get_job_listing(tool_input, services)

        # Resume generation tools
        elif tool_name == "match_skills":
            return await self._tool_match_skills(tool_input, services)
        elif tool_name == "generate_resume":
            return await self._tool_generate_resume(tool_input, services, context)
        elif tool_name == "list_generated_resumes":
            return await self._tool_list_generated_resumes(tool_input, services)
        elif tool_name == "upload_to_drive":
            return await self._tool_upload_to_drive(tool_input, services)

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    # -------------------------------------------------------------------------
    # Profile Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_get_profile(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Get the user's profile."""
        profile_service: ProfileService = services["profile"]

        profile = await profile_service.get_or_create_profile()

        result = {
            "success": True,
            "profile": {
                "id": str(profile.id),
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "full_name": profile.full_name,
                "email": profile.email,
                "phone": profile.phone,
                "city": profile.city,
                "state": profile.state,
                "country": profile.country,
                "linkedin_url": profile.linkedin_url,
                "github_url": profile.github_url,
                "portfolio_url": profile.portfolio_url,
                "personal_website": profile.personal_website,
                "professional_summary": profile.professional_summary,
            },
        }

        # Include stats if requested
        if input_data.get("include_stats"):
            stats = await profile_service.get_profile_stats(profile.id)
            result["stats"] = {
                "total_skills": stats.total_skills,
                "skills_by_category": stats.skills_by_category,
                "total_work_experience_years": float(stats.total_work_experience_years),
                "total_positions": stats.total_positions,
                "total_education": stats.total_education,
                "total_certifications": stats.total_certifications,
                "active_certifications": stats.active_certifications,
                "total_generated_resumes": stats.total_generated_resumes,
                "total_job_listings": stats.total_job_listings,
            }

        return result

    async def _tool_update_profile(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Update the user's profile."""
        profile_service: ProfileService = services["profile"]

        # Ensure profile exists
        profile = await profile_service.get_or_create_profile()

        # Build update data
        update_data = ProfileUpdate(**{k: v for k, v in input_data.items() if v is not None})

        updated = await profile_service.update_profile(update_data, profile.id)

        return {
            "success": True,
            "profile_id": str(updated.id),
            "full_name": updated.full_name,
            "message": "Profile updated successfully",
        }

    # -------------------------------------------------------------------------
    # Skill Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_list_skills(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """List skills with optional filtering."""
        profile_service: ProfileService = services["profile"]
        skill_service: SkillService = services["skill"]

        profile = await profile_service.get_or_create_profile()

        category = None
        if input_data.get("category"):
            category = SkillCategory(input_data["category"])

        is_featured = input_data.get("is_featured")

        result = await skill_service.list_skills(
            profile_id=profile.id,
            category=category,
            is_featured=is_featured,
        )

        skills = []
        for item in result.items:
            skills.append({
                "id": str(item.id),
                "name": item.name,
                "category": item.category.value,
                "proficiency": item.proficiency.value,
                "years_experience": float(item.years_experience) if item.years_experience else None,
                "is_featured": item.is_featured,
            })

        return {
            "success": True,
            "total": result.total,
            "skills": skills,
        }

    async def _tool_add_skill(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a new skill."""
        profile_service: ProfileService = services["profile"]
        skill_service: SkillService = services["skill"]

        profile = await profile_service.get_or_create_profile()

        skill_data = SkillCreate(
            name=input_data["name"],
            category=SkillCategory(input_data["category"]),
            proficiency=SkillProficiency(input_data.get("proficiency", "intermediate")),
            years_experience=Decimal(str(input_data.get("years_experience", 0))) if input_data.get("years_experience") else None,
            keywords=input_data.get("keywords", []),
            is_featured=input_data.get("is_featured", False),
        )

        skill = await skill_service.create(profile.id, skill_data)

        return {
            "success": True,
            "skill_id": str(skill.id),
            "name": skill.name,
            "category": skill.category,
            "message": f"Added skill: {skill.name}",
        }

    async def _tool_update_skill(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing skill."""
        from src.models.resume import SkillUpdate

        skill_service: SkillService = services["skill"]

        skill_id = UUID(input_data["skill_id"])

        # Build update data
        update_fields = {}
        if "name" in input_data:
            update_fields["name"] = input_data["name"]
        if "category" in input_data:
            update_fields["category"] = SkillCategory(input_data["category"])
        if "proficiency" in input_data:
            update_fields["proficiency"] = SkillProficiency(input_data["proficiency"])
        if "years_experience" in input_data:
            update_fields["years_experience"] = Decimal(str(input_data["years_experience"]))
        if "is_featured" in input_data:
            update_fields["is_featured"] = input_data["is_featured"]

        update_data = SkillUpdate(**update_fields)
        skill = await skill_service.update(skill_id, update_data)

        if not skill:
            return {"success": False, "error": f"Skill {skill_id} not found"}

        return {
            "success": True,
            "skill_id": str(skill.id),
            "name": skill.name,
            "message": f"Updated skill: {skill.name}",
        }

    async def _tool_delete_skill(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Delete a skill."""
        skill_service: SkillService = services["skill"]

        skill_id = UUID(input_data["skill_id"])
        deleted = await skill_service.delete(skill_id)

        return {
            "success": deleted,
            "skill_id": str(skill_id),
            "message": "Skill deleted" if deleted else "Skill not found",
        }

    # -------------------------------------------------------------------------
    # Work Experience Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_list_work_experience(
        self,
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """List all work experience entries."""
        profile_service: ProfileService = services["profile"]
        work_exp_service: WorkExperienceService = services["work_exp"]

        profile = await profile_service.get_or_create_profile()
        result = await work_exp_service.list_experiences(profile.id)

        experiences = []
        for item in result.items:
            experiences.append({
                "id": str(item.id),
                "company_name": item.company_name,
                "job_title": item.job_title,
                "location": item.location,
                "is_remote": item.is_remote,
                "start_date": item.start_date.isoformat() if item.start_date else None,
                "end_date": item.end_date.isoformat() if item.end_date else None,
                "is_current": item.is_current,
                "achievements": item.achievements,
            })

        return {
            "success": True,
            "total": result.total,
            "experiences": experiences,
        }

    async def _tool_add_work_experience(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a new work experience entry."""
        profile_service: ProfileService = services["profile"]
        work_exp_service: WorkExperienceService = services["work_exp"]

        profile = await profile_service.get_or_create_profile()

        exp_data = WorkExperienceCreate(
            company_name=input_data["company_name"],
            job_title=input_data["job_title"],
            location=input_data.get("location"),
            is_remote=input_data.get("is_remote", False),
            start_date=date.fromisoformat(input_data["start_date"]),
            end_date=date.fromisoformat(input_data["end_date"]) if input_data.get("end_date") else None,
            is_current=input_data.get("is_current", False),
            description=input_data.get("description"),
            achievements=input_data.get("achievements", []),
            technologies_used=input_data.get("technologies_used", []),
        )

        exp = await work_exp_service.create(profile.id, exp_data)

        return {
            "success": True,
            "experience_id": str(exp.id),
            "company_name": exp.company_name,
            "job_title": exp.job_title,
            "message": f"Added work experience: {exp.job_title} at {exp.company_name}",
        }

    async def _tool_update_work_experience(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing work experience entry."""
        from src.models.resume import WorkExperienceUpdate

        work_exp_service: WorkExperienceService = services["work_exp"]

        exp_id = UUID(input_data["experience_id"])

        # Build update data
        update_fields = {}
        for field in ["company_name", "job_title", "location", "is_remote", "is_current", "description", "achievements", "technologies_used"]:
            if field in input_data:
                update_fields[field] = input_data[field]

        if "start_date" in input_data:
            update_fields["start_date"] = date.fromisoformat(input_data["start_date"])
        if "end_date" in input_data:
            update_fields["end_date"] = date.fromisoformat(input_data["end_date"]) if input_data["end_date"] else None

        update_data = WorkExperienceUpdate(**update_fields)
        exp = await work_exp_service.update(exp_id, update_data)

        if not exp:
            return {"success": False, "error": f"Work experience {exp_id} not found"}

        return {
            "success": True,
            "experience_id": str(exp.id),
            "message": f"Updated work experience: {exp.job_title} at {exp.company_name}",
        }

    async def _tool_delete_work_experience(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Delete a work experience entry."""
        work_exp_service: WorkExperienceService = services["work_exp"]

        exp_id = UUID(input_data["experience_id"])
        deleted = await work_exp_service.delete(exp_id)

        return {
            "success": deleted,
            "experience_id": str(exp_id),
            "message": "Work experience deleted" if deleted else "Work experience not found",
        }

    # -------------------------------------------------------------------------
    # Education Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_list_education(
        self,
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """List all education entries."""
        profile_service: ProfileService = services["profile"]
        education_service: EducationService = services["education"]

        profile = await profile_service.get_or_create_profile()
        result = await education_service.list_education(profile.id)

        education = []
        for item in result.items:
            education.append({
                "id": str(item.id),
                "institution_name": item.institution_name,
                "degree": item.degree,
                "field_of_study": item.field_of_study,
                "start_date": item.start_date.isoformat() if item.start_date else None,
                "end_date": item.end_date.isoformat() if item.end_date else None,
                "is_current": item.is_current,
                "gpa": float(item.gpa) if item.gpa else None,
            })

        return {
            "success": True,
            "total": result.total,
            "education": education,
        }

    async def _tool_add_education(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a new education entry."""
        profile_service: ProfileService = services["profile"]
        education_service: EducationService = services["education"]

        profile = await profile_service.get_or_create_profile()

        edu_data = EducationCreate(
            institution_name=input_data["institution_name"],
            degree=input_data["degree"],
            field_of_study=input_data["field_of_study"],
            location=input_data.get("location"),
            start_date=date.fromisoformat(input_data["start_date"]) if input_data.get("start_date") else None,
            end_date=date.fromisoformat(input_data["end_date"]) if input_data.get("end_date") else None,
            is_current=input_data.get("is_current", False),
            gpa=Decimal(str(input_data["gpa"])) if input_data.get("gpa") else None,
            honors=input_data.get("honors"),
            relevant_coursework=input_data.get("relevant_coursework", []),
            activities=input_data.get("activities", []),
        )

        edu = await education_service.create(profile.id, edu_data)

        return {
            "success": True,
            "education_id": str(edu.id),
            "institution_name": edu.institution_name,
            "degree": edu.degree,
            "message": f"Added education: {edu.degree} from {edu.institution_name}",
        }

    async def _tool_update_education(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing education entry."""
        from src.models.resume import EducationUpdate

        education_service: EducationService = services["education"]

        edu_id = UUID(input_data["education_id"])

        # Build update data
        update_fields = {}
        for field in ["institution_name", "degree", "field_of_study", "location", "is_current", "honors"]:
            if field in input_data:
                update_fields[field] = input_data[field]

        if "start_date" in input_data:
            update_fields["start_date"] = date.fromisoformat(input_data["start_date"]) if input_data["start_date"] else None
        if "end_date" in input_data:
            update_fields["end_date"] = date.fromisoformat(input_data["end_date"]) if input_data["end_date"] else None
        if "gpa" in input_data:
            update_fields["gpa"] = Decimal(str(input_data["gpa"])) if input_data["gpa"] else None

        update_data = EducationUpdate(**update_fields)
        edu = await education_service.update(edu_id, update_data)

        if not edu:
            return {"success": False, "error": f"Education {edu_id} not found"}

        return {
            "success": True,
            "education_id": str(edu.id),
            "message": f"Updated education: {edu.degree} from {edu.institution_name}",
        }

    async def _tool_delete_education(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Delete an education entry."""
        education_service: EducationService = services["education"]

        edu_id = UUID(input_data["education_id"])
        deleted = await education_service.delete(edu_id)

        return {
            "success": deleted,
            "education_id": str(edu_id),
            "message": "Education deleted" if deleted else "Education not found",
        }

    # -------------------------------------------------------------------------
    # Certification Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_list_certifications(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """List all certifications."""
        profile_service: ProfileService = services["profile"]
        certification_service: CertificationService = services["certification"]

        profile = await profile_service.get_or_create_profile()
        is_active = input_data.get("is_active")

        result = await certification_service.list_certifications(
            profile_id=profile.id,
            is_active=is_active,
        )

        certs = []
        for item in result.items:
            certs.append({
                "id": str(item.id),
                "name": item.name,
                "issuing_organization": item.issuing_organization,
                "issue_date": item.issue_date.isoformat() if item.issue_date else None,
                "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
                "is_active": item.is_active,
                "credential_id": item.credential_id,
            })

        return {
            "success": True,
            "total": result.total,
            "certifications": certs,
        }

    async def _tool_add_certification(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a new certification."""
        profile_service: ProfileService = services["profile"]
        certification_service: CertificationService = services["certification"]

        profile = await profile_service.get_or_create_profile()

        cert_data = CertificationCreate(
            name=input_data["name"],
            issuing_organization=input_data["issuing_organization"],
            issue_date=date.fromisoformat(input_data["issue_date"]) if input_data.get("issue_date") else None,
            expiration_date=date.fromisoformat(input_data["expiration_date"]) if input_data.get("expiration_date") else None,
            credential_id=input_data.get("credential_id"),
            credential_url=input_data.get("credential_url"),
        )

        cert = await certification_service.create(profile.id, cert_data)

        return {
            "success": True,
            "certification_id": str(cert.id),
            "name": cert.name,
            "message": f"Added certification: {cert.name}",
        }

    async def _tool_update_certification(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing certification."""
        from src.models.resume import CertificationUpdate

        certification_service: CertificationService = services["certification"]

        cert_id = UUID(input_data["certification_id"])

        # Build update data
        update_fields = {}
        for field in ["name", "issuing_organization", "credential_id", "credential_url"]:
            if field in input_data:
                update_fields[field] = input_data[field]

        if "issue_date" in input_data:
            update_fields["issue_date"] = date.fromisoformat(input_data["issue_date"]) if input_data["issue_date"] else None
        if "expiration_date" in input_data:
            update_fields["expiration_date"] = date.fromisoformat(input_data["expiration_date"]) if input_data["expiration_date"] else None

        update_data = CertificationUpdate(**update_fields)
        cert = await certification_service.update(cert_id, update_data)

        if not cert:
            return {"success": False, "error": f"Certification {cert_id} not found"}

        return {
            "success": True,
            "certification_id": str(cert.id),
            "message": f"Updated certification: {cert.name}",
        }

    async def _tool_delete_certification(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Delete a certification."""
        certification_service: CertificationService = services["certification"]

        cert_id = UUID(input_data["certification_id"])
        deleted = await certification_service.delete(cert_id)

        return {
            "success": deleted,
            "certification_id": str(cert_id),
            "message": "Certification deleted" if deleted else "Certification not found",
        }

    # -------------------------------------------------------------------------
    # Job Listing Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_scrape_job(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
        context: AgentContext,
    ) -> dict[str, Any]:
        """Scrape a job listing from URL."""
        job_listing_service: JobListingService = services["job_listing"]

        url = input_data["url"]
        use_claude = input_data.get("use_claude_fallback", True)

        # Get API key from environment for Claude fallback
        api_key = os.environ.get("ANTHROPIC_API_KEY")

        # Scrape the job
        async with JobScraperService() as scraper:
            job_data = await scraper.scrape_job(
                url=url,
                claude_fallback=use_claude,
                anthropic_api_key=api_key,
            )

        # Create job listing in database
        listing_data = JobListingCreate(
            url=url,
            source_site=job_data.source_site,
            job_title=job_data.job_title or "Unknown Position",
            company_name=job_data.company_name or "Unknown Company",
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
            raw_html=job_data.raw_html,
        )

        listing, created = await job_listing_service.create_or_update(listing_data)

        return {
            "success": True,
            "job_id": str(listing.id),
            "job_title": listing.job_title,
            "company_name": listing.company_name,
            "location": listing.location,
            "is_remote": listing.is_remote,
            "required_skills": listing.required_skills,
            "preferred_skills": listing.preferred_skills,
            "created": created,
            "parse_confidence": job_data.parse_confidence,
            "message": f"{'Scraped' if created else 'Updated'} job listing: {listing.job_title} at {listing.company_name}",
        }

    async def _tool_list_job_listings(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """List scraped job listings."""
        job_listing_service: JobListingService = services["job_listing"]

        result = await job_listing_service.list_listings(
            search_query=input_data.get("search_query"),
            is_favorite=input_data.get("is_favorite"),
            page_size=input_data.get("limit", 10),
        )

        listings = []
        for item in result.items:
            listings.append({
                "id": str(item.id),
                "job_title": item.job_title,
                "company_name": item.company_name,
                "location": item.location,
                "is_remote": item.is_remote,
                "is_favorite": item.is_favorite,
                "application_status": item.application_status,
                "scraped_at": item.scraped_at.isoformat() if item.scraped_at else None,
            })

        return {
            "success": True,
            "total": result.total,
            "listings": listings,
        }

    async def _tool_get_job_listing(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Get details of a specific job listing."""
        job_listing_service: JobListingService = services["job_listing"]

        job_id = UUID(input_data["job_id"])
        listing = await job_listing_service.get_by_id(job_id)

        if not listing:
            return {"success": False, "error": f"Job listing {job_id} not found"}

        return {
            "success": True,
            "job": {
                "id": str(listing.id),
                "url": listing.url,
                "job_title": listing.job_title,
                "company_name": listing.company_name,
                "company_url": listing.company_url,
                "location": listing.location,
                "is_remote": listing.is_remote,
                "salary_min": float(listing.salary_min) if listing.salary_min else None,
                "salary_max": float(listing.salary_max) if listing.salary_max else None,
                "salary_currency": listing.salary_currency,
                "description": listing.description,
                "required_skills": listing.required_skills,
                "preferred_skills": listing.preferred_skills,
                "requirements": listing.requirements,
                "is_favorite": listing.is_favorite,
                "application_status": listing.application_status,
            },
        }

    # -------------------------------------------------------------------------
    # Resume Generation Tool Implementations
    # -------------------------------------------------------------------------
    async def _tool_match_skills(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate skill match score between profile and job."""
        profile_service: ProfileService = services["profile"]
        skill_service: SkillService = services["skill"]
        job_listing_service: JobListingService = services["job_listing"]

        profile = await profile_service.get_or_create_profile()
        job_id = UUID(input_data["job_id"])

        job = await job_listing_service.get_by_id(job_id)
        if not job:
            return {"success": False, "error": f"Job listing {job_id} not found"}

        # Get user's skills
        skills_result = await skill_service.list_skills(profile.id)
        user_skills = {s.name.lower() for s in skills_result.items}

        # Match required skills
        required_skills = job.required_skills or []
        matched_required = []
        missing_required = []
        for skill in required_skills:
            if skill.lower() in user_skills:
                matched_required.append(skill)
            else:
                missing_required.append(skill)

        # Match preferred skills
        preferred_skills = job.preferred_skills or []
        matched_preferred = []
        missing_preferred = []
        for skill in preferred_skills:
            if skill.lower() in user_skills:
                matched_preferred.append(skill)
            else:
                missing_preferred.append(skill)

        # Calculate scores
        required_score = (
            (len(matched_required) / len(required_skills) * 100)
            if required_skills else 100
        )
        preferred_score = (
            (len(matched_preferred) / len(preferred_skills) * 100)
            if preferred_skills else 100
        )

        # Overall score: 70% required, 30% preferred
        overall_score = (required_score * 0.7) + (preferred_score * 0.3)

        return {
            "success": True,
            "job_id": str(job_id),
            "job_title": job.job_title,
            "company_name": job.company_name,
            "overall_match_score": round(overall_score, 1),
            "required_skills_score": round(required_score, 1),
            "preferred_skills_score": round(preferred_score, 1),
            "matched_required": matched_required,
            "missing_required": missing_required,
            "matched_preferred": matched_preferred,
            "missing_preferred": missing_preferred,
        }

    async def _tool_generate_resume(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
        context: AgentContext,
    ) -> dict[str, Any]:
        """Generate a tailored resume for a job listing."""
        profile_service: ProfileService = services["profile"]
        skill_service: SkillService = services["skill"]
        work_exp_service: WorkExperienceService = services["work_exp"]
        education_service: EducationService = services["education"]
        certification_service: CertificationService = services["certification"]
        job_listing_service: JobListingService = services["job_listing"]
        resume_service: GeneratedResumeService = services["resume"]

        job_id = UUID(input_data["job_id"])
        output_format = ResumeFormat(input_data.get("format", "pdf"))
        upload_to_drive = input_data.get("upload_to_drive", False)

        # Get job listing
        job = await job_listing_service.get_by_id(job_id)
        if not job:
            return {"success": False, "error": f"Job listing {job_id} not found"}

        # Get profile data
        profile = await profile_service.get_or_create_profile()
        skills_result = await skill_service.list_skills(profile.id)
        exp_result = await work_exp_service.list_experiences(profile.id)
        edu_result = await education_service.list_education(profile.id)
        cert_result = await certification_service.list_certifications(profile.id)

        # Calculate skill match
        user_skills = {s.name.lower(): s for s in skills_result.items}
        required_skills = job.required_skills or []
        matched_skills = [s for s in required_skills if s.lower() in user_skills]
        match_score = (len(matched_skills) / len(required_skills) * 100) if required_skills else 100

        # Build resume content (simple text version for now)
        resume_content = self._build_resume_content(
            profile=profile,
            skills=[s for s in skills_result.items],
            experiences=[e for e in exp_result.items],
            education=[e for e in edu_result.items],
            certifications=[c for c in cert_result.items],
            job=job,
            matched_skills=matched_skills,
        )

        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d")
        company_slug = job.company_name.replace(" ", "_")[:20]
        filename = f"Resume_{company_slug}_{timestamp}.{output_format.value}"

        # Create resume record
        resume_data = GeneratedResumeCreate(
            name=filename,
            format=output_format,
            job_listing_id=job_id,
            content_snapshot={"text_content": resume_content},
            included_skills=matched_skills,
            skill_match_score=Decimal(str(match_score)),
            overall_match_score=Decimal(str(match_score)),
            match_analysis={
                "matched_skills": matched_skills,
                "required_skills": required_skills,
            },
        )

        resume = await resume_service.create(profile.id, resume_data)

        result = {
            "success": True,
            "resume_id": str(resume.id),
            "filename": filename,
            "format": output_format.value,
            "skill_match_score": round(match_score, 1),
            "job_title": job.job_title,
            "company_name": job.company_name,
            "message": f"Generated resume for {job.job_title} at {job.company_name}",
        }

        # Upload to Drive if requested
        if upload_to_drive:
            upload_result = await self._upload_resume_to_drive(
                resume_id=resume.id,
                filename=filename,
                content=resume_content.encode("utf-8"),
                mime_type="text/plain",  # TODO: Change when PDF generation is added
                services=services,
            )
            if upload_result.get("success"):
                result["drive_url"] = upload_result.get("url")
                result["drive_file_id"] = upload_result.get("file_id")

        return result

    def _build_resume_content(
        self,
        profile,
        skills: list,
        experiences: list,
        education: list,
        certifications: list,
        job,
        matched_skills: list,
    ) -> str:
        """
        Build resume content as structured text.

        This is a simple text representation. PDF generation will be added later.
        """
        lines = []

        # Header
        lines.append(f"{'=' * 60}")
        lines.append(f"{profile.full_name}")
        lines.append(f"{'=' * 60}")

        if profile.email:
            lines.append(f"Email: {profile.email}")
        if profile.phone:
            lines.append(f"Phone: {profile.phone}")
        if profile.linkedin_url:
            lines.append(f"LinkedIn: {profile.linkedin_url}")
        if profile.github_url:
            lines.append(f"GitHub: {profile.github_url}")

        # Professional Summary
        if profile.professional_summary:
            lines.append("")
            lines.append("PROFESSIONAL SUMMARY")
            lines.append("-" * 40)
            lines.append(profile.professional_summary)

        # Skills (prioritizing matched skills)
        if skills:
            lines.append("")
            lines.append("SKILLS")
            lines.append("-" * 40)

            # Show matched skills first
            matched_lower = {s.lower() for s in matched_skills}
            featured = [s for s in skills if s.name.lower() in matched_lower]
            other = [s for s in skills if s.name.lower() not in matched_lower]

            skill_names = [s.name for s in featured] + [s.name for s in other]
            lines.append(", ".join(skill_names[:20]))

        # Work Experience
        if experiences:
            lines.append("")
            lines.append("WORK EXPERIENCE")
            lines.append("-" * 40)

            for exp in sorted(experiences, key=lambda x: x.start_date or date.min, reverse=True):
                end_str = "Present" if exp.is_current else (exp.end_date.strftime("%b %Y") if exp.end_date else "")
                start_str = exp.start_date.strftime("%b %Y") if exp.start_date else ""
                lines.append(f"\n{exp.job_title}")
                lines.append(f"{exp.company_name} | {start_str} - {end_str}")
                if exp.achievements:
                    for achievement in exp.achievements[:5]:
                        lines.append(f"  • {achievement}")

        # Education
        if education:
            lines.append("")
            lines.append("EDUCATION")
            lines.append("-" * 40)

            for edu in education:
                lines.append(f"\n{edu.degree} in {edu.field_of_study}")
                lines.append(f"{edu.institution_name}")
                if edu.gpa:
                    lines.append(f"GPA: {edu.gpa}")

        # Certifications
        if certifications:
            lines.append("")
            lines.append("CERTIFICATIONS")
            lines.append("-" * 40)

            for cert in certifications:
                lines.append(f"  • {cert.name} - {cert.issuing_organization}")

        return "\n".join(lines)

    async def _tool_list_generated_resumes(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """List previously generated resumes."""
        profile_service: ProfileService = services["profile"]
        resume_service: GeneratedResumeService = services["resume"]

        profile = await profile_service.get_or_create_profile()

        job_listing_id = None
        if input_data.get("job_id"):
            job_listing_id = UUID(input_data["job_id"])

        result = await resume_service.list_resumes(
            profile_id=profile.id,
            job_listing_id=job_listing_id,
            page_size=input_data.get("limit", 10),
        )

        resumes = []
        for item in result.items:
            resumes.append({
                "id": str(item.id),
                "name": item.name,
                "format": item.format.value,
                "skill_match_score": float(item.skill_match_score) if item.skill_match_score else None,
                "drive_file_url": item.drive_file_url,
                "generated_at": item.generated_at.isoformat() if item.generated_at else None,
            })

        return {
            "success": True,
            "total": result.total,
            "resumes": resumes,
        }

    async def _tool_upload_to_drive(
        self,
        input_data: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Upload a generated resume to Google Drive."""
        resume_service: GeneratedResumeService = services["resume"]

        resume_id = UUID(input_data["resume_id"])
        folder_name = input_data.get("folder_name", "Resumes")

        resume = await resume_service.get_by_id(resume_id)
        if not resume:
            return {"success": False, "error": f"Resume {resume_id} not found"}

        # Get resume content
        content_snapshot = resume.content_snapshot or {}
        text_content = content_snapshot.get("text_content", "")

        if not text_content:
            return {"success": False, "error": "Resume has no content to upload"}

        # Upload to Drive
        upload_result = await self._upload_resume_to_drive(
            resume_id=resume.id,
            filename=resume.name,
            content=text_content.encode("utf-8"),
            mime_type="text/plain",
            services=services,
        )

        if upload_result.get("success"):
            # Update resume record with Drive info
            await resume_service.update_drive_info(
                resume_id=resume.id,
                drive_file_id=upload_result.get("file_id"),
                drive_file_url=upload_result.get("url"),
            )

        return upload_result

    async def _upload_resume_to_drive(
        self,
        resume_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Upload a resume file to Google Drive via MCP.

        Args:
            resume_id: Resume UUID for tracking.
            filename: Name for the file in Drive.
            content: File content bytes.
            mime_type: MIME type of the content.
            services: Service dictionary (unused here, for consistency).

        Returns:
            Upload result with file_id and url.
        """
        client = await self._get_http_client()

        try:
            # First, ensure the Resumes folder exists
            folder_response = await client.post(
                f"{self.mcp_url}/folders",
                json={"name": "Resumes"},
            )

            folder_id = None
            if folder_response.status_code == 200:
                folder_data = folder_response.json()
                folder_id = folder_data.get("folder", {}).get("id")

            # Upload the file
            content_base64 = base64.b64encode(content).decode("utf-8")

            upload_response = await client.post(
                f"{self.mcp_url}/files",
                json={
                    "name": filename,
                    "content_base64": content_base64,
                    "mime_type": mime_type,
                    "parent_folder_id": folder_id,
                },
            )

            upload_response.raise_for_status()
            upload_data = upload_response.json()

            file_info = upload_data.get("file", {})
            file_id = file_info.get("id")

            # Create shareable link
            share_response = await client.post(
                f"{self.mcp_url}/files/{file_id}/share",
                json={"role": "reader"},
            )

            share_url = None
            if share_response.status_code == 200:
                share_data = share_response.json()
                share_url = share_data.get("shareable_link")

            return {
                "success": True,
                "file_id": file_id,
                "url": share_url or file_info.get("web_view_link"),
                "message": f"Uploaded {filename} to Google Drive",
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Drive MCP HTTP error: {e.response.status_code}")
            return {
                "success": False,
                "error": f"Failed to upload to Drive: {e.response.status_code}",
            }

        except httpx.RequestError as e:
            logger.error(f"Drive MCP request error: {e}")
            return {
                "success": False,
                "error": f"Failed to connect to Drive MCP: {e}",
            }

    def _extract_text(self, response) -> str:
        """Extract text from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts)
