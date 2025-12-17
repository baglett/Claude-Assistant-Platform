# Claude Assistant Platform - Backend

FastAPI backend service providing the orchestrator agent and API endpoints.

## Quick Start

### Local Development (without Docker)

```powershell
# Navigate to backend directory
cd Backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment file
Copy-Item ..\.env.example ..\.env
# Edit .env with your ANTHROPIC_API_KEY

# Run the development server
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### With Docker

```powershell
# From project root
docker-compose up backend db
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Basic health check |
| `/health/detailed` | GET | Detailed health with components |
| `/api/chat` | POST | Send message to orchestrator |
| `/docs` | GET | Swagger UI (dev only) |

## Project Structure

```
Backend/
├── src/
│   ├── api/
│   │   ├── main.py           # FastAPI application
│   │   └── routes/
│   │       ├── health.py     # Health check endpoints
│   │       └── chat.py       # Chat endpoints
│   ├── agents/
│   │   └── orchestrator.py   # Main orchestrator agent
│   ├── models/
│   │   └── chat.py           # Pydantic models
│   ├── services/             # Business logic (future)
│   └── config/
│       └── settings.py       # Configuration management
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Model to use |
| `API_HOST` | No | `0.0.0.0` | API bind address |
| `API_PORT` | No | `8000` | API port |
| `DEBUG` | No | `true` | Enable debug mode |
| `POSTGRES_*` | Yes | - | Database connection |

## Testing the API

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Send a chat message
$body = @{
    message = "Hello! Can you help me create a todo list?"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/chat" -Method Post -Body $body -ContentType "application/json"
```

## Development

```powershell
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Lint code
ruff check src/

# Format code
ruff format src/
```
