# GitHub MCP Server - Implementation Plan

## Overview

This document outlines the implementation plan for a GitHub MCP (Model Context Protocol) server that provides read/write access to GitHub Issues, Pull Requests, and Branches for the Claude Assistant Platform orchestrator agent.

---

## Table of Contents

1. [Authentication Analysis](#authentication-analysis)
2. [Architecture Design](#architecture-design)
3. [Tool Specifications](#tool-specifications)
4. [Implementation Steps](#implementation-steps)
5. [Deployment Configuration](#deployment-configuration)
6. [Testing Strategy](#testing-strategy)

---

## Authentication Analysis

### Options Evaluated

| Method | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Fine-grained PAT** | Simple setup, granular permissions, personal use optimized | Tied to user, expires | ✅ **RECOMMENDED** |
| Classic PAT | Simple, widely supported | Broad permissions, less secure | Not recommended |
| GitHub App | Org-level, not tied to user, survives user departure | Complex setup, overkill for personal use | Future consideration |
| OAuth App | User-delegated access | Requires auth flow, complex | Not suitable |

### Decision: Fine-grained Personal Access Token (PAT)

**Rationale:**
- This is a personal assistant platform, not a multi-tenant service
- Fine-grained PATs offer precise permission control
- Simple to configure (just an environment variable)
- Follows the same pattern as Motion MCP (API key auth)
- No complex OAuth flows required for a self-hosted solution

### Required PAT Permissions

The fine-grained PAT needs these permissions for full functionality:

| Permission | Access Level | Purpose |
|------------|-------------|---------|
| **Issues** | Read & Write | Create, update, close, comment on issues |
| **Pull requests** | Read & Write | Create, update, merge, comment on PRs |
| **Contents** | Read & Write | Read files, create branches, push commits |
| **Metadata** | Read-only | Repository info (automatically included) |

### Token Generation Steps

1. Go to: **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Click "Generate new token"
3. Set token name: `claude-assistant-github-mcp`
4. Set expiration: 90 days (or custom)
5. Select repository access: "Only select repositories" or "All repositories"
6. Under "Repository permissions":
   - Contents: Read and write
   - Issues: Read and write
   - Pull requests: Read and write
   - Metadata: Read-only (auto-selected)
7. Click "Generate token"
8. Copy and store securely

---

## Architecture Design

### Component Structure

```
MCPS/github/
├── src/
│   ├── __init__.py           # Package marker
│   ├── server.py             # FastMCP + FastAPI server (main entry)
│   ├── client.py             # GitHub API client wrapper
│   ├── models/
│   │   ├── __init__.py       # Model exports
│   │   ├── issues.py         # Issue-related models
│   │   ├── pull_requests.py  # PR-related models
│   │   ├── branches.py       # Branch/ref models
│   │   └── common.py         # Shared models (User, Label, etc.)
│   └── utils.py              # Helper functions
├── tests/
│   ├── __init__.py
│   ├── test_client.py        # Client unit tests
│   └── test_server.py        # Server integration tests
├── Dockerfile                # Multi-stage Docker build
├── Makefile                  # Dev convenience commands
├── pyproject.toml            # uv project config
├── uv.lock                   # Lock file
├── README.md                 # MCP documentation
├── .env.example              # Example environment config
└── GITHUB-MCP-PLAN.md        # This file
```

### Integration Pattern

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  Orchestrator Agent │────▶│    GitHub MCP       │────▶│    GitHub API       │
│  (Backend)          │     │    (Port 8083)      │     │    api.github.com   │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
        │                            │
        │ HTTP POST                  │ REST API calls
        │ /tools/*                   │ w/ Bearer token
        ▼                            ▼
```

### Port Allocation

| Service | Container Port | Host Port (Prod) |
|---------|---------------|------------------|
| GitHub MCP | 8083 | 8083 |

This follows the port allocation strategy: 8080-8089 for MCP servers.

---

## Tool Specifications

### Issue Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `github_list_issues` | List issues with filters | `owner`, `repo`, `state?`, `labels?`, `assignee?`, `per_page?` |
| `github_get_issue` | Get single issue details | `owner`, `repo`, `issue_number` |
| `github_create_issue` | Create new issue | `owner`, `repo`, `title`, `body?`, `labels?`, `assignees?` |
| `github_update_issue` | Update existing issue | `owner`, `repo`, `issue_number`, `title?`, `body?`, `state?`, `labels?`, `assignees?` |
| `github_add_issue_comment` | Add comment to issue | `owner`, `repo`, `issue_number`, `body` |
| `github_list_issue_comments` | List comments on issue | `owner`, `repo`, `issue_number`, `per_page?` |

### Pull Request Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `github_list_pull_requests` | List PRs with filters | `owner`, `repo`, `state?`, `head?`, `base?`, `per_page?` |
| `github_get_pull_request` | Get single PR details | `owner`, `repo`, `pr_number` |
| `github_create_pull_request` | Create new PR | `owner`, `repo`, `title`, `body?`, `head`, `base`, `draft?` |
| `github_update_pull_request` | Update existing PR | `owner`, `repo`, `pr_number`, `title?`, `body?`, `state?`, `base?` |
| `github_merge_pull_request` | Merge a PR | `owner`, `repo`, `pr_number`, `merge_method?`, `commit_title?`, `commit_message?` |
| `github_list_pr_files` | List files changed in PR | `owner`, `repo`, `pr_number` |
| `github_add_pr_comment` | Add comment to PR | `owner`, `repo`, `pr_number`, `body` |
| `github_create_pr_review` | Create PR review | `owner`, `repo`, `pr_number`, `body?`, `event`, `comments?` |

### Branch Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `github_list_branches` | List repository branches | `owner`, `repo`, `per_page?` |
| `github_get_branch` | Get branch details | `owner`, `repo`, `branch` |
| `github_create_branch` | Create new branch from ref | `owner`, `repo`, `branch_name`, `source_branch?` |
| `github_delete_branch` | Delete a branch | `owner`, `repo`, `branch` |
| `github_get_default_branch` | Get repo's default branch | `owner`, `repo` |

### Repository Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `github_get_repository` | Get repository info | `owner`, `repo` |
| `github_list_repositories` | List user/org repos | `owner?`, `type?`, `per_page?` |
| `github_get_file_content` | Get file content from repo | `owner`, `repo`, `path`, `ref?` |

### Utility Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `github_get_authenticated_user` | Get current auth user info | — |
| `github_check_rate_limit` | Check API rate limit status | — |

---

## Implementation Steps

### Phase 1: Project Setup

1. **Create directory structure**
   ```powershell
   New-Item -ItemType Directory -Path "MCPS/github/src/models" -Force
   New-Item -ItemType Directory -Path "MCPS/github/tests" -Force
   ```

2. **Create pyproject.toml**
   - Dependencies: `mcp>=1.9.0`, `httpx>=0.28.0`, `fastapi>=0.115.0`, `uvicorn>=0.32.0`, `pydantic>=2.10.0`, `pydantic-settings>=2.6.0`
   - Python requirement: `>=3.12`
   - Entry point: `github-mcp = "src.server:main"`

3. **Create .env.example**
   ```env
   # GitHub MCP Configuration
   GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
   GITHUB_MCP_HOST=0.0.0.0
   GITHUB_MCP_PORT=8083
   ```

### Phase 2: Core Implementation

4. **Implement models** (`src/models/`)
   - `common.py`: User, Label, Milestone, Repository models
   - `issues.py`: Issue, IssueCreate, IssueUpdate, IssueComment models
   - `pull_requests.py`: PullRequest, PRCreate, PRUpdate, PRReview models
   - `branches.py`: Branch, Ref, Commit models

5. **Implement client** (`src/client.py`)
   - `GitHubClient` class with httpx async client
   - Rate limit handling with exponential backoff
   - Error handling with custom exceptions
   - Methods for each API operation

6. **Implement server** (`src/server.py`)
   - FastMCP server with all tools
   - FastAPI app with HTTP endpoints
   - Health check endpoint
   - Settings from environment

### Phase 3: Docker & Deployment

7. **Create Dockerfile**
   - Multi-stage build (builder + runtime)
   - Based on `python:3.12-slim`
   - uv for dependency management
   - Non-root user for security
   - Health check configuration

8. **Update Jenkinsfile**
   - Add `github-token` credential
   - Add build stage for GitHub MCP
   - Add push stage for GitHub MCP
   - Add container start stage with env vars
   - Add to cleanup stage
   - Add to verify stage

9. **Update Backend configuration**
   - Add GitHub MCP host/port settings
   - Add GitHub MCP URL property
   - Wire up to orchestrator agent

### Phase 4: Testing & Documentation

10. **Create tests**
    - Unit tests for client methods
    - Integration tests for MCP tools
    - Mock GitHub API responses

11. **Update documentation**
    - DEPLOYMENT.md: Add GitHub MCP section
    - CLAUDE.md: Add changelog entry
    - README.md: Add GitHub integration section
    - .env.example: Add GitHub MCP variables

---

## Deployment Configuration

### Jenkins Credential

| Credential ID | Type | Description |
|---------------|------|-------------|
| `github-token` | Secret text | Fine-grained PAT |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | — | Fine-grained PAT |
| `GITHUB_MCP_HOST` | No | `0.0.0.0` | Server bind address |
| `GITHUB_MCP_PORT` | No | `8083` | Server port |
| `GITHUB_API_BASE_URL` | No | `https://api.github.com` | API base URL |
| `GITHUB_REQUEST_TIMEOUT` | No | `30` | Request timeout (seconds) |

### Container Configuration

| Property | Value |
|----------|-------|
| Container Name | `claude-assistant-github-mcp` |
| Image Name | `claude-assistant-github-mcp` |
| Internal Port | 8083 |
| External Port | 8083 |
| Network | `claude-assistant-network` |
| Restart Policy | `unless-stopped` |

### Jenkinsfile Changes Required

```groovy
// Add to environment block
GITHUB_TOKEN = credentials('github-token')
GITHUB_MCP_IMAGE_NAME = 'claude-assistant-github-mcp'
GITHUB_MCP_CONTAINER = 'claude-assistant-github-mcp'
GITHUB_MCP_PORT = '8083'

// Add to image preparation
env.GITHUB_MCP_IMAGE = "${DOCKER_REGISTRY}/${GITHUB_MCP_IMAGE_NAME}:${env.IMAGE_VERSION}"

// Add build stage (parallel)
stage('Build GitHub MCP') {
    steps {
        script {
            sh """
            docker build --platform linux/arm64/v8 \
                -t ${env.GITHUB_MCP_IMAGE} \
                -f ./MCPS/github/Dockerfile \
                ./MCPS/github
            """
        }
    }
}

// Add push stage (parallel)
stage('Push GitHub MCP') {
    steps {
        script {
            sh "docker push ${env.GITHUB_MCP_IMAGE}"
        }
    }
}

// Add stop/remove to cleanup
docker ps -f name=${GITHUB_MCP_CONTAINER} -q | xargs --no-run-if-empty docker container stop
docker container ls -a -f name=${GITHUB_MCP_CONTAINER} -q | xargs -r docker container rm

// Add start stage
stage('Start GitHub MCP') {
    steps {
        script {
            sh """
            docker run -d \
                --name ${GITHUB_MCP_CONTAINER} \
                --network ${DOCKER_NETWORK} \
                --restart unless-stopped \
                -p ${GITHUB_MCP_PORT}:8083 \
                -e GITHUB_TOKEN=\${GITHUB_TOKEN} \
                -e GITHUB_MCP_HOST=0.0.0.0 \
                -e GITHUB_MCP_PORT=8083 \
                ${env.GITHUB_MCP_IMAGE}
            """

            sh """
            echo "Waiting for GitHub MCP to be healthy..."
            sleep 10
            curl -f http://localhost:${GITHUB_MCP_PORT}/health || echo "Health check pending..."
            """
        }
    }
}

// Add backend env vars
-e GITHUB_MCP_HOST=${GITHUB_MCP_CONTAINER} \
-e GITHUB_MCP_PORT=8083 \
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_client.py
@pytest.mark.asyncio
async def test_list_issues():
    """Test listing issues returns expected format."""
    ...

@pytest.mark.asyncio
async def test_create_issue():
    """Test creating an issue."""
    ...

@pytest.mark.asyncio
async def test_rate_limit_handling():
    """Test rate limit backoff behavior."""
    ...
```

### Integration Tests

```python
# tests/test_server.py
@pytest.mark.asyncio
async def test_github_list_issues_tool():
    """Test MCP tool for listing issues."""
    ...

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check returns expected status."""
    ...
```

### Manual Testing Checklist

- [ ] Health endpoint returns status
- [ ] List issues from a test repo
- [ ] Create issue and verify on GitHub
- [ ] Update issue title/body
- [ ] Add comment to issue
- [ ] Close issue
- [ ] List pull requests
- [ ] Create PR from branch
- [ ] List PR files
- [ ] Merge PR
- [ ] Create new branch
- [ ] Delete branch
- [ ] Rate limit handling works

---

## Security Considerations

1. **Token Storage**: Never commit tokens to git; use Jenkins credentials store
2. **Token Scope**: Use minimum required permissions
3. **Token Rotation**: Set 90-day expiration, rotate proactively
4. **Rate Limiting**: Implement backoff to avoid hitting limits
5. **Input Validation**: Validate owner/repo format to prevent injection
6. **Error Handling**: Don't expose token in error messages

---

## Rate Limit Management

GitHub API rate limits:
- **Authenticated requests**: 5,000 per hour
- **Search API**: 30 per minute

Strategy:
- Check rate limit before expensive operations
- Implement exponential backoff on 403/429
- Log remaining requests for monitoring
- Provide `github_check_rate_limit` tool for visibility

---

## Timeline Estimate

| Phase | Tasks |
|-------|-------|
| Phase 1 | Project setup, pyproject.toml, directory structure |
| Phase 2 | Models, client, server implementation |
| Phase 3 | Dockerfile, Jenkinsfile updates, backend integration |
| Phase 4 | Tests, documentation updates |

---

## References

- [GitHub REST API Docs](https://docs.github.com/en/rest)
- [GitHub Fine-grained PATs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens)
- [GitHub Authentication: PATs vs GitHub Apps](https://michaelkasingye.medium.com/github-authentication-personal-access-tokens-vs-github-apps-0f8fba446fbd)
- [Existing Motion MCP Implementation](../motion/src/server.py) - Reference pattern
- [Existing Gmail MCP Implementation](../gmail/src/server.py) - Reference pattern

---

## Approval

- [ ] Authentication approach approved
- [ ] Tool list approved
- [ ] Port allocation approved
- [ ] Ready to implement

---

*Document created: 2025-01-10*
*Last updated: 2025-01-10*
