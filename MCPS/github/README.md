# GitHub MCP Server

MCP (Model Context Protocol) server providing GitHub API tools for the Claude Assistant Platform.

## Features

- **Issue Management**: Create, list, update, close, and comment on issues
- **Pull Request Management**: Create, list, update, merge, and review PRs
- **Branch Management**: Create, list, and delete branches
- **Repository Access**: Get repo info, list repos, read file contents
- **Rate Limit Monitoring**: Check API usage to avoid rate limits

## Tools Available

### Issue Tools

| Tool | Description |
|------|-------------|
| `github_list_issues` | List issues with filters (state, labels, assignee) |
| `github_get_issue` | Get a specific issue by number |
| `github_create_issue` | Create a new issue |
| `github_update_issue` | Update an existing issue |
| `github_add_issue_comment` | Add a comment to an issue |
| `github_list_issue_comments` | List comments on an issue |

### Pull Request Tools

| Tool | Description |
|------|-------------|
| `github_list_pull_requests` | List PRs with filters (state, head, base) |
| `github_get_pull_request` | Get a specific PR by number |
| `github_create_pull_request` | Create a new PR |
| `github_update_pull_request` | Update an existing PR |
| `github_merge_pull_request` | Merge a PR (merge, squash, rebase) |
| `github_list_pr_files` | List files changed in a PR |
| `github_add_pr_comment` | Add a comment to a PR |
| `github_create_pr_review` | Create a review (approve, request changes, comment) |

### Branch Tools

| Tool | Description |
|------|-------------|
| `github_list_branches` | List all branches in a repo |
| `github_get_branch` | Get branch details |
| `github_create_branch` | Create a new branch |
| `github_delete_branch` | Delete a branch |
| `github_get_default_branch` | Get the default branch name |

### Repository Tools

| Tool | Description |
|------|-------------|
| `github_get_repository` | Get repository information |
| `github_list_repositories` | List repos for a user/org |
| `github_get_file_content` | Get file content from a repo |
| `github_list_labels` | List labels in a repo |

### Utility Tools

| Tool | Description |
|------|-------------|
| `github_get_authenticated_user` | Get current auth user info |
| `github_check_rate_limit` | Check API rate limit status |

## Setup

### 1. Create a GitHub Fine-Grained Personal Access Token

GitHub fine-grained tokens provide precise control over permissions. Follow these steps:

#### Step 1: Navigate to Token Settings

1. Log in to [GitHub](https://github.com)
2. Click your profile picture (top-right) → **Settings**
3. Scroll down in the left sidebar → **Developer settings**
4. Click **Personal access tokens** → **Fine-grained tokens**
5. Or go directly to: https://github.com/settings/tokens?type=beta

#### Step 2: Generate New Token

1. Click **"Generate new token"**
2. Enter a **Token name**: `claude-assistant-github-mcp` (or your preferred name)
3. Set **Expiration**:
   - Recommended: 90 days
   - Maximum: 1 year (or no expiration if allowed by your org)
4. Add a **Description** (optional): "GitHub MCP for Claude Assistant Platform"

#### Step 3: Configure Repository Access

Choose one of:
- **Only select repositories**: Pick specific repos (more secure)
- **All repositories**: Access to all current and future repos

#### Step 4: Set Repository Permissions

Under **"Repository permissions"**, configure these required permissions:

| Permission | Access Level | Why It's Needed |
|------------|-------------|-----------------|
| **Contents** | Read and write | Create branches, read files, push commits |
| **Issues** | Read and write | Create, update, close, and comment on issues |
| **Pull requests** | Read and write | Create, update, merge PRs and add reviews |
| **Metadata** | Read-only | Basic repo info (auto-selected, required) |

> **Note**: Leave all other permissions at "No access" for security.

#### Step 5: Generate and Save

1. Click **"Generate token"** at the bottom
2. **IMPORTANT**: Copy the token immediately - you won't see it again!
3. Store it securely (password manager, secrets vault, etc.)

#### Token Format

Fine-grained tokens start with `github_pat_` followed by a long string:
```
github_pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
```

#### For Jenkins Deployment

Add the token to Jenkins credentials:
1. Go to: **Jenkins → Manage Jenkins → Credentials → System → Global credentials**
2. Click **"Add Credentials"**
3. Kind: **Secret text**
4. Secret: *paste your token*
5. ID: `github-token`
6. Click **"Create"**

### 2. Configure Environment (Local Development)

Create a `.env` file with your token:

```bash
# Copy the example file
cp .env.example .env
```

Then edit `.env` and set your token:

```env
# Required - your fine-grained PAT from Step 1
GITHUB_TOKEN=github_pat_11ABCDEFG0123456789_yourActualTokenHere

# Optional - defaults shown
# GITHUB_MCP_HOST=0.0.0.0
# GITHUB_MCP_PORT=8083
# LOG_LEVEL=INFO
```

> **Important**: The variable name is `GITHUB_TOKEN` (not `GITHUB_PAT` or `GH_TOKEN`)

### 3. Run Locally

```bash
# Install dependencies
uv sync

# Run the server
uv run python -m src.server
```

You should see:
```
INFO:     Starting GitHub MCP Server on 0.0.0.0:8083
INFO:     GitHub token configured
INFO:     Uvicorn running on http://0.0.0.0:8083
```

Verify it's working:
```bash
curl http://localhost:8083/health
```

### 4. Run with Docker

```bash
# Build the image
docker build -t github-mcp .

# Run the container
docker run -d \
  --name github-mcp \
  -p 8083:8083 \
  -e GITHUB_TOKEN=your-token-here \
  github-mcp
```

## API Endpoints

### Health Check

```bash
curl http://localhost:8083/health
```

### Rate Limit

```bash
curl http://localhost:8083/tools/github_check_rate_limit
```

### HTTP Tool Endpoints

All tools are also available via HTTP POST:

```bash
# List issues
curl -X POST http://localhost:8083/tools/github_list_issues \
  -H "Content-Type: application/json" \
  -d '{"owner": "octocat", "repo": "Hello-World", "state": "open"}'

# Create an issue
curl -X POST http://localhost:8083/tools/github_create_issue \
  -H "Content-Type: application/json" \
  -d '{"owner": "octocat", "repo": "Hello-World", "title": "New feature", "body": "Description here"}'
```

## Rate Limiting

GitHub API limits:
- **Authenticated**: 5,000 requests/hour
- **Search API**: 30 requests/minute

The client automatically:
- Waits and retries on rate limit errors
- Implements exponential backoff
- Logs remaining requests for monitoring

Use `github_check_rate_limit` to monitor usage.

## Error Handling

All tools return a consistent response format:

```json
{
  "success": true,
  "data": { ... }
}
```

Or on error:

```json
{
  "success": false,
  "error": "error_type",
  "message": "Human-readable description"
}
```

Error types:
- `authentication_error`: Invalid token
- `forbidden`: Access denied
- `not_found`: Resource not found
- `validation_error`: Invalid request
- `rate_limit_exceeded`: Rate limit hit
- `api_error`: General API error

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | — | Fine-grained PAT |
| `GITHUB_API_BASE_URL` | No | `https://api.github.com` | API base URL |
| `GITHUB_REQUEST_TIMEOUT` | No | `30` | Request timeout (seconds) |
| `GITHUB_MAX_RETRIES` | No | `3` | Max retries for rate limits |
| `GITHUB_MCP_HOST` | No | `0.0.0.0` | Server host |
| `GITHUB_MCP_PORT` | No | `8083` | Server port |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Format code
uv run ruff format .
```

## License

MIT
