---
paths:
  - "Backend/src/agents/orchestrator.py"
---

# Orchestrator Rules

The orchestrator is the central coordinator that parses user intent and delegates to specialized sub-agents. It should NEVER execute domain tasks directly.

## Core Principle

The orchestrator's only job is to:
1. Understand user intent
2. Delegate to the appropriate sub-agent
3. Return the sub-agent's response

## When Modifying the Orchestrator

### Adding a New Agent

1. Import the agent class at the top of the file
2. Register in the lifespan function:
   ```python
   registry.register(NewAgent(
       db_session_factory=db_session_factory,
       anthropic_api_key=anthropic_api_key,
       mcp_base_url=f"http://{os.getenv('NEW_MCP_HOST')}:{os.getenv('NEW_MCP_PORT')}"
   ))
   ```
3. Update `get_available_agents` tool to include the new agent description

### Updating Agent Descriptions

The orchestrator's system prompt contains descriptions of all available agents. Claude uses these to decide delegation. When updating:
- Be specific about what each agent handles
- Include keywords users might say
- Clarify boundaries between similar agents

## Tool Definitions

The orchestrator has exactly two tools:

| Tool | Purpose |
|------|---------|
| `delegate_to_agent` | Delegate a task to a specific sub-agent |
| `get_available_agents` | List available agents and their capabilities |

Do NOT add domain-specific tools to the orchestrator.

## Delegation Flow

```
User Message
    │
    ▼
Orchestrator receives message
    │
    ▼
Claude analyzes intent
    │
    ▼
delegate_to_agent(agent_name, task)
    │
    ▼
Sub-agent executes task
    │
    ▼
Result returned to orchestrator
    │
    ▼
Orchestrator formats response
```

## Error Handling

- If delegation fails, return a helpful error message
- Never expose internal errors to users
- Log failures for debugging

## Anti-Patterns

- **DON'T** add domain-specific tool handlers (delegate to sub-agents instead)
- **DON'T** execute MCP calls directly from orchestrator
- **DON'T** hardcode routing logic (let Claude decide based on intent)
- **DON'T** bypass the tool calling loop
- **DON'T** return raw sub-agent responses without formatting
- **DON'T** add business logic to the orchestrator

## Reference

For general agent patterns, see `.claude/rules/backend/agents.md`.
