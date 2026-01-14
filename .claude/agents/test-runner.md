---
description: Run pytest tests, analyze failures, generate coverage reports, and suggest fixes for the Backend
capabilities:
  - Run pytest with various options
  - Analyze test failures and suggest fixes
  - Generate test coverage reports
  - Create test skeletons for new agents
  - Run specific test files or patterns
  - Debug failing tests
---

# Test Runner Agent

Specialized agent for running and analyzing tests in the Claude Assistant Platform.

## When to Use This Agent

Invoke this agent when:
- Running tests after implementing new features
- Investigating test failures
- Generating code coverage reports
- Creating test files for new components
- Debugging flaky or failing tests
- Verifying fixes before committing

## Test Commands

### Run All Tests

```bash
cd Backend
uv run pytest
```

### Run with Coverage

```bash
uv run pytest --cov=src --cov-report=term-missing
```

### Run Specific File

```bash
uv run pytest tests/test_agents.py
```

### Run Specific Test

```bash
uv run pytest tests/test_agents.py::test_todo_agent_creates_todo -v
```

### Run with Verbose Output

```bash
uv run pytest -v --tb=long
```

### Run Only Failed Tests

```bash
uv run pytest --lf
```

## Test Patterns

### Agent Tests

Agent tests should:
- Mock MCP HTTP calls with `httpx.MockTransport` or `respx`
- Mock Claude API responses with predefined tool_use
- Use `AsyncMock` for database sessions
- Test the tool calling loop behavior

```python
@pytest.mark.asyncio
async def test_agent_handles_task():
    # Arrange
    mock_session = AsyncMock()
    context = AgentContext(
        chat_id=uuid4(),
        task="Create a todo",
        session=mock_session,
    )

    # Act
    result = await agent.execute(context)

    # Assert
    assert result.success
    assert "created" in result.message.lower()
```

### MCP Server Tests

```python
@pytest.mark.asyncio
async def test_mcp_tool():
    # Test the tool function directly
    result = await example_tool(param1="test")
    assert result["success"]
```

### API Route Tests

```python
@pytest.mark.asyncio
async def test_endpoint(client: AsyncClient):
    response = await client.get("/api/todos")
    assert response.status_code == 200
```

## Analyzing Failures

When tests fail, check:

1. **Assertion Error**: Expected vs actual values
2. **Import Error**: Missing dependency or circular import
3. **Connection Error**: Database or external service unavailable
4. **Timeout**: Async operation hung or too slow
5. **Mock Not Called**: Mock setup incorrect

## Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| Agents | 80% |
| API Routes | 90% |
| Services | 85% |
| Models | 70% |

## Creating Test Skeletons

For a new agent at `Backend/src/agents/new_agent.py`:

```python
# Backend/tests/test_new_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.agents.new_agent import NewAgent
from src.agents.base import AgentContext


@pytest.fixture
def agent():
    return NewAgent(
        db_session_factory=AsyncMock(),
        anthropic_api_key="test-key",
        mcp_base_url="http://localhost:8080",
    )


@pytest.fixture
def context():
    return AgentContext(
        chat_id=uuid4(),
        task="Test task",
        session=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_agent_name(agent):
    assert agent.name == "new_agent"


@pytest.mark.asyncio
async def test_agent_executes_task(agent, context):
    with patch.object(agent, 'client') as mock_client:
        # Setup mock response
        mock_client.messages.create.return_value = MockResponse(...)

        result = await agent.execute(context)

        assert result.success
```

## vs Other Agents

- Use **Test Runner** for pytest execution and analysis
- Use **MCP Debugger** for service connectivity issues
- Use **PR Manager** for preparing code for review
