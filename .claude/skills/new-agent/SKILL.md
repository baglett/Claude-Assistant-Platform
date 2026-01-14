---
name: new-agent
description: Create a new backend agent for the Claude Assistant Platform. Use when adding a new specialized agent, scaffolding an agent, or when the user says "create agent", "add agent", "new agent", or "scaffold agent".
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Create New Agent

This skill scaffolds a new specialized agent following the established patterns.

## Prerequisites

Before creating an agent, gather:
1. **Agent name** (snake_case, e.g., `slack_agent`)
2. **Agent purpose** (what domain it handles)
3. **MCP server** (if connecting to external service)

## Steps

### 1. Create Agent File

Create `Backend/src/agents/{name}_agent.py` using the template in [TEMPLATE.md](TEMPLATE.md).

### 2. Register Agent

Add to `Backend/src/api/main.py` in the lifespan function:

```python
from src.agents.{name}_agent import {Name}Agent

# In lifespan(), after other agent registrations:
registry.register({Name}Agent(
    db_session_factory=db_session_factory,
    anthropic_api_key=anthropic_api_key,
    mcp_base_url=f"http://{os.getenv('{NAME}_MCP_HOST')}:{os.getenv('{NAME}_MCP_PORT')}"
))
```

### 3. Update Orchestrator

Edit `Backend/src/agents/orchestrator.py`:

1. Add agent to the system prompt's available agents list
2. Update `get_available_agents` tool response

### 4. Add Environment Variables

If the agent uses an MCP server, add to `.env.example`:

```env
# {Name} Integration
{NAME}_MCP_HOST=claude-assistant-{name}-mcp
{NAME}_MCP_PORT=808X
```

## Checklist

After creation, verify:

- [ ] Agent extends `BaseAgent`
- [ ] `name` and `description` properties defined
- [ ] System prompt describes available tools
- [ ] Tool definitions use JSON schema format
- [ ] Tool handlers implemented for each tool
- [ ] MCP base URL passed via constructor (if applicable)
- [ ] Agent registered in `main.py` lifespan
- [ ] Orchestrator knows about the agent
- [ ] Environment variables added to `.env.example`

## File Locations

| File | Purpose |
|------|---------|
| `Backend/src/agents/{name}_agent.py` | Agent implementation |
| `Backend/src/api/main.py` | Agent registration |
| `Backend/src/agents/orchestrator.py` | Delegation config |
| `.env.example` | Environment variables |

## Reference

- [TEMPLATE.md](TEMPLATE.md) - Agent code template
- `.claude/rules/backend/agents.md` - Agent patterns and anti-patterns
