---
paths:
  - "Backend/src/agents/**/*.py"
---

# Agent Development Patterns

## Base Agent Extension

All agents MUST extend `BaseAgent` from `Backend/src/agents/base.py`:

```python
from src.agents.base import BaseAgent, AgentContext, AgentResult

class MyAgent(BaseAgent):
    """
    Description of what this agent does.

    Available tools:
        - tool_name: Brief description
    """

    name = "my_agent"
    description = "Handles specific domain tasks"

    async def _execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's main logic."""
        # Implementation here
        return AgentResult(
            success=True,
            response="Task completed",
            data={"key": "value"},
        )
```

## AgentContext

Use `AgentContext` for passing execution context:

```python
@dataclass
class AgentContext:
    chat_id: UUID | None           # Originating chat
    task: str                       # User's request
    session: AsyncSession           # Database session
    parent_execution_id: UUID | None  # For nested agent calls
    metadata: dict[str, Any]        # Additional context
```

## AgentResult

Return `AgentResult` from all agent executions:

```python
@dataclass
class AgentResult:
    success: bool                   # Whether execution succeeded
    response: str                   # Human-readable response
    data: dict[str, Any] | None     # Structured data
    delegated_to: str | None        # If delegating to another agent
    error: str | None               # Error message if failed
```

## Tool Definitions

Define tools as a list of dictionaries for Claude's tool_use:

```python
TOOLS = [
    {
        "name": "create_item",
        "description": "Create a new item in the system",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The item title",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority 1-5 (1=highest)",
                    "minimum": 1,
                    "maximum": 5,
                },
            },
            "required": ["title"],
        },
    },
]
```

## Tool Calling Loop

Implement the tool calling loop pattern:

```python
async def _execute(self, context: AgentContext) -> AgentResult:
    messages = [{"role": "user", "content": context.task}]

    while True:
        response = await self.client.messages.create(
            model=self.model,
            system=self.system_prompt,
            tools=self.TOOLS,
            messages=messages,
        )

        # Check for tool use
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            # No more tools, extract final response
            break

        # Execute tools and add results
        for tool_use in tool_uses:
            result = await self._handle_tool(tool_use.name, tool_use.input)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": result}],
            })

    return AgentResult(success=True, response=extract_text(response))
```

## Orchestrator Delegation

The orchestrator uses `AgentRegistry` to delegate:

```python
# Register agents on startup
registry = AgentRegistry()
registry.register(TodoAgent())
registry.register(GitHubAgent())

# Delegate via tool
async def delegate_to_agent(agent_name: str, task: str) -> str:
    agent = registry.get(agent_name)
    result = await agent.execute(context)
    return result.response
```

## Execution Logging

BaseAgent automatically logs executions. For manual logging:

```python
from src.services.agent_execution_service import AgentExecutionService

# Log thinking
await execution_service.log_thinking(execution_id, "Analyzing request...")

# Log tool call
await execution_service.log_tool_call(
    execution_id,
    tool_name="create_todo",
    tool_input={"title": "..."},
    tool_output={"id": "..."},
)
```

## Key Rules

1. **Never execute domain tasks in orchestrator** - always delegate
2. **Use tool calling loop** - let Claude decide when to stop
3. **Log all executions** - for debugging and analytics
4. **Handle errors gracefully** - return AgentResult with error field
5. **Keep agents focused** - one domain per agent
