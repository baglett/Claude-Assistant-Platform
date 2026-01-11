# Claude Assistant Platform

A self-hosted AI assistant platform using the Claude API with an orchestrator pattern.

## Quick Reference

| Requirement | Value |
|-------------|-------|
| Python | 3.14+ |
| Package Manager | uv (not pip) |
| HTTP Framework | FastAPI |
| Orchestration | Docker Compose |
| Frontend | Next.js + TypeScript |

## Documentation

- `DOCUMENTATION/ARCHITECTURE.md` - System architecture and data flows
- `DOCUMENTATION/REQUIREMENTS.md` - Functional and non-functional requirements
- `DOCUMENTATION/DEPLOYMENT.md` - Deployment configuration and ports
- `DOCUMENTATION/TODO_Implementation.md` - Todo system implementation details
- `DOCUMENTATION/apple-watch-shortcut.md` - Apple Watch Siri shortcut setup guide
- `CHANGELOG.md` - Detailed change history

## Modular Rules

This project uses `.claude/rules/` for context-specific instructions.
See `.claude/rules/README.md` for maintenance and update guidelines.

| Rule File | Scope |
|-----------|-------|
| `project-overview.md` | Always loaded - architecture, key patterns |
| `security.md` | Always loaded - secrets, OWASP |
| `documentation.md` | Always loaded - when and how to update docs |
| `backend/python.md` | `Backend/**/*.py` |
| `backend/fastapi.md` | `Backend/src/api/**/*.py` |
| `backend/agents.md` | `Backend/src/agents/**/*.py` |
| `backend/database.md` | `Backend/src/database/**/*.py`, `Backend/database/**/*.sql` |
| `backend/pydantic-models.md` | `Backend/src/models/**/*.py` |
| `frontend/nextjs.md` | `Frontend/**/*.{ts,tsx}` |
| `frontend/react-components.md` | `Frontend/src/components/**/*.tsx` |
| `mcp-servers/fastmcp.md` | `MCPS/**/*.py` |
| `infrastructure/docker.md` | `**/Dockerfile`, `**/docker-compose*.yml` |
| `infrastructure/jenkins.md` | `Jenkinsfile` |

## Critical Reminders

- **ALWAYS** consider `DOCUMENTATION/REQUIREMENTS.md` for project requirements
- **ALWAYS** remove dead or unused code
- **ALWAYS** update documentation if changes affect architecture or usage
- **NEVER** commit credentials to git
- **NEVER** hardcode secrets - use environment variables

## Running Locally

```powershell
# Sync dependencies
uv sync

# Start development server
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or via Docker
docker-compose up --build
```

## Testing

```powershell
uv run pytest
uv run pytest --cov=src
```

## Known Issues

None currently tracked.

## Future Considerations

- Voice message support via Telegram
- Web dashboard for task visualization
- Additional MCP integrations (Slack, Discord)
- Multi-user support with authentication
