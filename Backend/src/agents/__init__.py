# =============================================================================
# Agents Package
# =============================================================================
"""
Agent definitions for the Claude Assistant Platform.

Contains the orchestrator agent, specialized sub-agents, and base classes
for building new agents.

Architecture:
    - BaseAgent: Abstract base class for all agents
    - AgentContext: Context passed to agents for execution
    - AgentResult: Result returned by agent execution
    - AgentRegistry: Registry for looking up agents by name
    - OrchestratorAgent: Main coordinator that delegates to sub-agents

Usage:
    from src.agents import BaseAgent, AgentContext, AgentResult

    class MyAgent(BaseAgent):
        @property
        def name(self) -> str:
            return "my_agent"

        @property
        def description(self) -> str:
            return "Does something useful"

        async def _execute_task(self, context, service, execution):
            # Implementation
            return AgentResult(success=True, message="Done!")
"""

from src.agents.base import (
    AgentContext,
    AgentProtocol,
    AgentRegistry,
    AgentResult,
    BaseAgent,
)
from src.agents.orchestrator import OrchestratorAgent
from src.agents.resume_agent import ResumeAgent
from src.agents.todo_agent import TodoAgent

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "AgentProtocol",
    "AgentRegistry",
    # Agents
    "OrchestratorAgent",
    "ResumeAgent",
    "TodoAgent",
]
