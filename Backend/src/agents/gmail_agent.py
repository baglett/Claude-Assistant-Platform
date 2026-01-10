# =============================================================================
# Gmail Agent
# =============================================================================
"""
Specialized agent for Gmail email management.

The GmailAgent handles all Gmail-related operations including listing messages,
reading emails, sending messages, managing drafts, and organizing with labels.
It communicates with the Gmail MCP server via HTTP.

Usage:
    from src.agents.gmail_agent import GmailAgent

    agent = GmailAgent(
        api_key=api_key,
        mcp_url="http://gmail-mcp:8085"
    )
    result = await agent.execute(context)
"""

import json
import logging
import time
from typing import Any

import anthropic
import httpx

from src.agents.base import AgentContext, AgentResult, BaseAgent
from src.database import AgentExecution
from src.services.agent_execution_service import AgentExecutionService


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Gmail Agent System Prompt
# -----------------------------------------------------------------------------
GMAIL_AGENT_SYSTEM_PROMPT = """You are the Gmail Agent for the Claude Assistant Platform.

Your responsibility is managing emails in Gmail - reading, sending, searching, and organizing.

## Available Tools:

### Authentication
- **gmail_check_auth_status**: Check if authenticated with Gmail
- **gmail_get_auth_url**: Get OAuth URL for authentication (if needed)

### Labels
- **gmail_list_labels**: List all labels (INBOX, SENT, custom labels, etc.)
- **gmail_create_label**: Create a new custom label

### Messages
- **gmail_list_messages**: List messages with optional filters
- **gmail_get_message**: Get full content of a specific message
- **gmail_search_messages**: Search using Gmail query syntax
- **gmail_send_email**: Send a new email
- **gmail_trash_message**: Move a message to trash
- **gmail_mark_as_read**: Mark a message as read
- **gmail_mark_as_unread**: Mark a message as unread
- **gmail_archive_message**: Archive a message (remove from inbox)
- **gmail_add_label**: Add a label to a message
- **gmail_remove_label**: Remove a label from a message

### Drafts
- **gmail_create_draft**: Create a draft email
- **gmail_send_draft**: Send an existing draft
- **gmail_list_drafts**: List all drafts

## Gmail Search Syntax:
Use these operators with gmail_search_messages:
- `from:alice@example.com` - From specific sender
- `to:bob@example.com` - To specific recipient
- `subject:meeting` - Subject contains word
- `is:unread` - Unread messages
- `is:starred` - Starred messages
- `has:attachment` - Has attachments
- `newer_than:7d` - Within last 7 days
- `older_than:1m` - Older than 1 month
- `label:work` - Has specific label
- `larger:5M` - Larger than 5MB

## Important Notes:
1. Always check auth status first if operations fail with 401
2. Use message IDs from list/search results for other operations
3. Gmail query syntax is powerful - use it for precise searches
4. Be concise and confirm actions taken

## Workflow Tips:
- To find unread emails: Use search with "is:unread"
- To reply to a thread: Use send_email with thread_id parameter
- To organize: Use add_label/remove_label or archive_message
- For important emails: Add STARRED or IMPORTANT labels"""


# -----------------------------------------------------------------------------
# Gmail Agent Tool Definitions
# -----------------------------------------------------------------------------
GMAIL_TOOLS = [
    # Authentication Tools
    {
        "name": "gmail_check_auth_status",
        "description": "Check if authenticated with Gmail. Use this first if operations fail.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "gmail_get_auth_url",
        "description": "Get the OAuth authorization URL if authentication is needed.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # Label Tools
    {
        "name": "gmail_list_labels",
        "description": "List all labels in the mailbox (INBOX, SENT, custom labels, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "gmail_create_label",
        "description": "Create a new custom label.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the new label.",
                },
            },
            "required": ["name"],
        },
    },
    # Message Tools
    {
        "name": "gmail_list_messages",
        "description": "List messages in the mailbox with optional filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query (e.g., 'from:alice@example.com is:unread').",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum messages to return. Default: 10.",
                },
                "label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by label IDs (e.g., ['INBOX', 'UNREAD']).",
                },
                "include_spam_trash": {
                    "type": "boolean",
                    "description": "Include spam and trash. Default: false.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "gmail_get_message",
        "description": "Get full content of a specific message by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The message ID to retrieve.",
                },
                "format": {
                    "type": "string",
                    "enum": ["full", "metadata", "minimal", "raw"],
                    "description": "Response format. Default: 'full'.",
                },
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_search_messages",
        "description": "Search messages using Gmail query syntax.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query (e.g., 'from:alice is:unread newer_than:7d').",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results. Default: 25.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "gmail_send_email",
        "description": "Send a new email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses.",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line.",
                },
                "body": {
                    "type": "string",
                    "description": "Plain text body content.",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CC recipients.",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "BCC recipients.",
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML body for rich formatting.",
                },
                "reply_to": {
                    "type": "string",
                    "description": "Reply-to address.",
                },
                "thread_id": {
                    "type": "string",
                    "description": "Thread ID if replying to existing conversation.",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "gmail_trash_message",
        "description": "Move a message to trash. Can be recovered within 30 days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The message ID to trash.",
                },
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_mark_as_read",
        "description": "Mark a message as read (removes UNREAD label).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The message ID to mark as read.",
                },
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_mark_as_unread",
        "description": "Mark a message as unread (adds UNREAD label).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The message ID to mark as unread.",
                },
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_archive_message",
        "description": "Archive a message (remove from inbox, keep in All Mail).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The message ID to archive.",
                },
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_add_label",
        "description": "Add a label to a message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The message ID.",
                },
                "label_id": {
                    "type": "string",
                    "description": "Label ID to add (e.g., 'STARRED', 'IMPORTANT', or custom label ID).",
                },
            },
            "required": ["message_id", "label_id"],
        },
    },
    {
        "name": "gmail_remove_label",
        "description": "Remove a label from a message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The message ID.",
                },
                "label_id": {
                    "type": "string",
                    "description": "Label ID to remove.",
                },
            },
            "required": ["message_id", "label_id"],
        },
    },
    # Draft Tools
    {
        "name": "gmail_create_draft",
        "description": "Create a draft email without sending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses.",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line.",
                },
                "body": {
                    "type": "string",
                    "description": "Plain text body content.",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CC recipients.",
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML body for rich formatting.",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "gmail_send_draft",
        "description": "Send an existing draft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "draft_id": {
                    "type": "string",
                    "description": "The draft ID to send.",
                },
            },
            "required": ["draft_id"],
        },
    },
    {
        "name": "gmail_list_drafts",
        "description": "List all drafts in the mailbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum drafts to return. Default: 10.",
                },
            },
            "required": [],
        },
    },
]


# -----------------------------------------------------------------------------
# Gmail Agent Class
# -----------------------------------------------------------------------------
class GmailAgent(BaseAgent):
    """
    Specialized agent for Gmail email management.

    Communicates with the Gmail MCP server via HTTP to manage emails,
    drafts, labels, and search.

    Attributes:
        client: Anthropic API client.
        model: Claude model to use.
        mcp_url: URL of the Gmail MCP server.
        http_client: Async HTTP client for MCP calls.

    Example:
        agent = GmailAgent(
            api_key="sk-...",
            mcp_url="http://gmail-mcp:8085"
        )
        context = AgentContext(
            chat_id=chat_uuid,
            task="Find unread emails from today",
            session=session,
        )
        result = await agent.execute(context)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        mcp_url: str = "http://gmail-mcp:8085",
    ):
        """
        Initialize the Gmail Agent.

        Args:
            api_key: Anthropic API key.
            model: Claude model to use.
            mcp_url: URL of the Gmail MCP server.
        """
        super().__init__(api_key=api_key, model=model)
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.mcp_url = mcp_url.rstrip("/")
        self._http_client: httpx.AsyncClient | None = None

        # Token tracking for execution logging
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._llm_calls = 0

    @property
    def name(self) -> str:
        """Agent identifier."""
        return "email"

    @property
    def description(self) -> str:
        """Agent description."""
        return "Manages Gmail - reading, sending, searching, and organizing emails"

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create the async HTTP client for MCP calls.

        Returns:
            The httpx.AsyncClient instance.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
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
        Execute the Gmail management task.

        Uses Claude's tool calling to determine and execute the appropriate
        Gmail operations based on the task description.

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
            f"Processing Gmail task: {context.task}\n"
            f"MCP URL: {self.mcp_url}",
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
            logger.error(f"GmailAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                message=f"Failed to process Gmail request: {str(e)}",
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
        max_iterations: int = 10,
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
            logger.debug(f"GmailAgent tool loop iteration {iteration + 1}")

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=GMAIL_AGENT_SYSTEM_PROMPT,
                tools=GMAIL_TOOLS,
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
                    f"Iteration {iteration + 1}: Processing Gmail tool calls",
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

        for block in content_blocks:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            logger.info(f"GmailAgent executing tool: {tool_name}")
            start_time = time.time()

            try:
                # Execute the tool via Gmail MCP
                result = await self._call_gmail_mcp(tool_name, tool_input)

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
                    "content": json.dumps(result),
                })

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")

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

    async def _call_gmail_mcp(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a Gmail MCP tool via HTTP.

        Maps agent tool names to MCP HTTP endpoints.

        Args:
            tool_name: Name of the Gmail tool to call.
            tool_input: Tool input parameters.

        Returns:
            Tool execution result from MCP server.
        """
        client = await self._get_http_client()

        try:
            # Map tool to HTTP method and endpoint
            if tool_name == "gmail_check_auth_status":
                response = await client.get(f"{self.mcp_url}/auth/status")

            elif tool_name == "gmail_get_auth_url":
                response = await client.get(f"{self.mcp_url}/auth/url")

            elif tool_name == "gmail_list_labels":
                response = await client.get(f"{self.mcp_url}/labels")

            elif tool_name == "gmail_create_label":
                # MCP may expose this via POST /labels
                response = await client.post(
                    f"{self.mcp_url}/labels",
                    json=tool_input,
                )

            elif tool_name == "gmail_list_messages":
                params = {k: v for k, v in tool_input.items() if v is not None}
                response = await client.get(f"{self.mcp_url}/messages", params=params)

            elif tool_name == "gmail_get_message":
                message_id = tool_input.get("message_id")
                format_type = tool_input.get("format", "full")
                response = await client.get(
                    f"{self.mcp_url}/messages/{message_id}",
                    params={"format": format_type},
                )

            elif tool_name == "gmail_search_messages":
                params = {k: v for k, v in tool_input.items() if v is not None}
                response = await client.get(f"{self.mcp_url}/messages", params=params)

            elif tool_name == "gmail_send_email":
                response = await client.post(
                    f"{self.mcp_url}/messages/send",
                    json=tool_input,
                )

            elif tool_name == "gmail_trash_message":
                message_id = tool_input.get("message_id")
                response = await client.delete(f"{self.mcp_url}/messages/{message_id}")

            elif tool_name == "gmail_mark_as_read":
                message_id = tool_input.get("message_id")
                response = await client.post(
                    f"{self.mcp_url}/messages/{message_id}/read",
                )

            elif tool_name == "gmail_mark_as_unread":
                message_id = tool_input.get("message_id")
                response = await client.post(
                    f"{self.mcp_url}/messages/{message_id}/unread",
                )

            elif tool_name == "gmail_archive_message":
                message_id = tool_input.get("message_id")
                response = await client.post(
                    f"{self.mcp_url}/messages/{message_id}/archive",
                )

            elif tool_name == "gmail_add_label":
                message_id = tool_input.get("message_id")
                label_id = tool_input.get("label_id")
                response = await client.post(
                    f"{self.mcp_url}/messages/{message_id}/labels/{label_id}",
                )

            elif tool_name == "gmail_remove_label":
                message_id = tool_input.get("message_id")
                label_id = tool_input.get("label_id")
                response = await client.delete(
                    f"{self.mcp_url}/messages/{message_id}/labels/{label_id}",
                )

            elif tool_name == "gmail_create_draft":
                response = await client.post(
                    f"{self.mcp_url}/drafts",
                    json=tool_input,
                )

            elif tool_name == "gmail_send_draft":
                draft_id = tool_input.get("draft_id")
                response = await client.post(
                    f"{self.mcp_url}/drafts/{draft_id}/send",
                )

            elif tool_name == "gmail_list_drafts":
                params = {k: v for k, v in tool_input.items() if v is not None}
                response = await client.get(f"{self.mcp_url}/drafts", params=params)

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Gmail MCP HTTP error: {e.response.status_code}")
            error_detail = ""
            try:
                error_detail = e.response.text
            except Exception:
                pass
            return {
                "success": False,
                "error": f"Gmail MCP error: {e.response.status_code}",
                "detail": error_detail,
            }

        except httpx.RequestError as e:
            logger.error(f"Gmail MCP request error: {e}")
            return {
                "success": False,
                "error": f"Failed to connect to Gmail MCP: {e}",
            }

    def _extract_text(self, response) -> str:
        """Extract text from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts)
