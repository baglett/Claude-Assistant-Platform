# =============================================================================
# Gmail MCP Server
# =============================================================================
"""
FastMCP server providing Gmail API tools.

This server exposes MCP tools for:
- Listing and searching messages
- Reading full message content
- Sending emails and creating drafts
- Managing labels on messages
- Archiving and trashing messages

The server runs as a standalone HTTP service and can be called by the
orchestrator or other components to interact with Gmail.
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .auth import GmailAuthManager
from .client import GmailClient
from .models import SendEmailRequest

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
class Settings(BaseSettings):
    """
    Server settings loaded from environment variables.

    Attributes:
        gmail_client_id: OAuth client ID.
        gmail_client_secret: OAuth client secret.
        gmail_token_path: Path to store OAuth tokens.
        gmail_oauth_port: Port for OAuth callback.
        host: Host address for the server.
        port: Port number for the server.
    """

    gmail_client_id: str = Field(
        default="",
        description="Google OAuth client ID",
    )
    gmail_client_secret: str = Field(
        default="",
        description="Google OAuth client secret",
    )
    gmail_token_path: str = Field(
        default="./data/gmail_token.json",
        description="Path to store OAuth tokens",
    )
    gmail_oauth_port: int = Field(
        default=8086,
        description="Port for OAuth callback server",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host address for the server",
    )
    port: int = Field(
        default=8085,
        description="Port number for the server",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


# -----------------------------------------------------------------------------
# Initialize Auth Manager and Client
# -----------------------------------------------------------------------------
auth_manager = GmailAuthManager(
    client_id=settings.gmail_client_id,
    client_secret=settings.gmail_client_secret,
    token_path=settings.gmail_token_path,
    oauth_port=settings.gmail_oauth_port,
)

gmail_client = GmailClient(auth_manager=auth_manager)


# -----------------------------------------------------------------------------
# FastMCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("gmail-mcp")


# -----------------------------------------------------------------------------
# Authentication Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def check_auth_status() -> dict:
    """
    Check the current authentication status.

    Returns:
        Dictionary with authentication status and details.
    """
    is_auth = gmail_client.is_authenticated()
    needs_refresh = auth_manager.needs_refresh

    return {
        "authenticated": is_auth,
        "needs_refresh": needs_refresh,
        "message": (
            "Authenticated and ready"
            if is_auth
            else "Authentication required. Use authenticate tool or visit the auth URL."
        ),
    }


@mcp.tool()
async def get_auth_url() -> dict:
    """
    Get the OAuth authorization URL for manual authentication.

    Use this if automatic browser authentication is not available.

    Returns:
        Dictionary with the authorization URL.
    """
    url = auth_manager.get_auth_url()
    return {
        "auth_url": url,
        "instructions": (
            "Visit this URL in a browser to authenticate. "
            "After granting permission, you will be redirected to a local callback."
        ),
    }


# -----------------------------------------------------------------------------
# Label Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def list_labels() -> dict:
    """
    List all labels in the user's mailbox.

    Returns labels like INBOX, SENT, TRASH, SPAM, and any custom labels.

    Returns:
        Dictionary containing list of labels with id, name, and message counts.
    """
    result = await gmail_client.list_labels()
    return result.model_dump()


@mcp.tool()
async def create_label(name: str) -> dict:
    """
    Create a new label in the mailbox.

    Args:
        name: Name for the new label.

    Returns:
        Dictionary indicating success and the new label ID.
    """
    result = await gmail_client.create_label(name)
    return result.model_dump()


# -----------------------------------------------------------------------------
# Message Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def list_messages(
    query: Optional[str] = None,
    max_results: int = 10,
    label_ids: Optional[list[str]] = None,
    include_spam_trash: bool = False,
) -> dict:
    """
    List messages in the user's mailbox.

    Args:
        query: Gmail search query (e.g., "from:alice@example.com is:unread").
               See Gmail search operators for full syntax.
        max_results: Maximum number of messages to return (default: 10).
        label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"]).
        include_spam_trash: Include spam and trash in results (default: False).

    Returns:
        Dictionary containing list of message summaries with id, snippet, labels.
    """
    result = await gmail_client.list_messages(
        query=query,
        max_results=max_results,
        label_ids=label_ids,
        include_spam_trash=include_spam_trash,
    )
    return result.model_dump()


@mcp.tool()
async def get_message(
    message_id: str,
    format: str = "full",
) -> dict:
    """
    Get a specific message by ID with full content.

    Args:
        message_id: The message ID to retrieve.
        format: Response format - "full" (default), "metadata", "minimal", or "raw".

    Returns:
        Dictionary containing full message details including:
        - subject, from, to, cc addresses
        - date sent
        - plain text and HTML body content
        - attachment information
        - all headers
    """
    result = await gmail_client.get_message(
        message_id=message_id,
        format=format,
    )
    return result.model_dump()


@mcp.tool()
async def search_messages(
    query: str,
    max_results: int = 25,
) -> dict:
    """
    Search messages using Gmail query syntax.

    Supports operators like:
    - from:, to:, subject:, has:attachment
    - is:unread, is:starred, is:important
    - before:, after:, newer_than:, older_than:
    - label:, category:, filename:
    - larger:, smaller: (for size filtering)

    Examples:
    - "from:alice@example.com is:unread" - Unread from Alice
    - "subject:meeting has:attachment" - Meetings with attachments
    - "newer_than:7d label:work" - Work emails from last week

    Args:
        query: Gmail search query string.
        max_results: Maximum results to return (default: 25).

    Returns:
        Dictionary containing matching messages with snippets.
    """
    result = await gmail_client.search_messages(
        query=query,
        max_results=max_results,
    )
    return result.model_dump()


@mcp.tool()
async def send_email(
    to: list[str],
    subject: str,
    body: str,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> dict:
    """
    Send a new email.

    Args:
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Plain text body content.
        cc: CC recipients (optional).
        bcc: BCC recipients (optional).
        html_body: HTML body for rich formatting (optional).
        reply_to: Reply-to address (optional).
        thread_id: Thread ID if replying to existing conversation (optional).

    Returns:
        Dictionary with sent message ID and thread ID.
    """
    result = await gmail_client.send_email(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html_body=html_body,
        reply_to=reply_to,
        thread_id=thread_id,
    )
    return result.model_dump()


@mcp.tool()
async def trash_message(message_id: str) -> dict:
    """
    Move a message to trash.

    The message can be recovered from trash within 30 days.

    Args:
        message_id: The message ID to trash.

    Returns:
        Dictionary indicating success or failure.
    """
    result = await gmail_client.trash_message(message_id)
    return result.model_dump()


@mcp.tool()
async def mark_as_read(message_id: str) -> dict:
    """
    Mark a message as read.

    Removes the UNREAD label from the message.

    Args:
        message_id: The message ID to mark as read.

    Returns:
        Dictionary indicating success or failure.
    """
    result = await gmail_client.mark_as_read(message_id)
    return result.model_dump()


@mcp.tool()
async def mark_as_unread(message_id: str) -> dict:
    """
    Mark a message as unread.

    Adds the UNREAD label to the message.

    Args:
        message_id: The message ID to mark as unread.

    Returns:
        Dictionary indicating success or failure.
    """
    result = await gmail_client.mark_as_unread(message_id)
    return result.model_dump()


@mcp.tool()
async def archive_message(message_id: str) -> dict:
    """
    Archive a message.

    Removes the INBOX label, moving the message out of the inbox
    while keeping it accessible in All Mail.

    Args:
        message_id: The message ID to archive.

    Returns:
        Dictionary indicating success or failure.
    """
    result = await gmail_client.archive_message(message_id)
    return result.model_dump()


@mcp.tool()
async def add_label(message_id: str, label_id: str) -> dict:
    """
    Add a label to a message.

    Args:
        message_id: The message ID.
        label_id: The label ID to add (e.g., "STARRED", "IMPORTANT", or custom label ID).

    Returns:
        Dictionary indicating success or failure.
    """
    result = await gmail_client.modify_message_labels(
        message_id=message_id,
        add_label_ids=[label_id],
    )
    return result.model_dump()


@mcp.tool()
async def remove_label(message_id: str, label_id: str) -> dict:
    """
    Remove a label from a message.

    Args:
        message_id: The message ID.
        label_id: The label ID to remove.

    Returns:
        Dictionary indicating success or failure.
    """
    result = await gmail_client.modify_message_labels(
        message_id=message_id,
        remove_label_ids=[label_id],
    )
    return result.model_dump()


# -----------------------------------------------------------------------------
# Draft Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def create_draft(
    to: list[str],
    subject: str,
    body: str,
    cc: Optional[list[str]] = None,
    html_body: Optional[str] = None,
) -> dict:
    """
    Create a draft email without sending.

    The draft will be saved and can be edited in Gmail or sent later.

    Args:
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Plain text body content.
        cc: CC recipients (optional).
        html_body: HTML body for rich formatting (optional).

    Returns:
        Dictionary with draft ID and details.
    """
    result = await gmail_client.create_draft(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        html_body=html_body,
    )
    return result.model_dump()


@mcp.tool()
async def send_draft(draft_id: str) -> dict:
    """
    Send an existing draft.

    The draft will be sent and moved to the Sent folder.

    Args:
        draft_id: The draft ID to send.

    Returns:
        Dictionary with sent message ID and thread ID.
    """
    result = await gmail_client.send_draft(draft_id)
    return result.model_dump()


@mcp.tool()
async def list_drafts(max_results: int = 10) -> dict:
    """
    List drafts in the user's mailbox.

    Args:
        max_results: Maximum number of drafts to return (default: 10).

    Returns:
        Dictionary containing list of drafts with IDs and message info.
    """
    result = await gmail_client.list_drafts(max_results=max_results)
    return result.model_dump()


# -----------------------------------------------------------------------------
# FastAPI Application (for HTTP access)
# -----------------------------------------------------------------------------
fastapi_app = FastAPI(
    title="Gmail MCP Server",
    description="MCP server providing Gmail API tools",
    version="0.1.0",
)


@fastapi_app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Dictionary with service status.
    """
    is_auth = gmail_client.is_authenticated()
    return {
        "status": "healthy",
        "service": "gmail-mcp",
        "authenticated": is_auth,
    }


@fastapi_app.get("/auth/status")
async def http_auth_status() -> dict:
    """Get authentication status via HTTP."""
    return await check_auth_status()


@fastapi_app.get("/auth/url")
async def http_auth_url() -> dict:
    """Get OAuth authorization URL via HTTP."""
    return await get_auth_url()


@fastapi_app.post("/auth/authenticate")
async def http_authenticate() -> dict:
    """
    Trigger OAuth authentication flow.

    Note: This will open a browser window for authentication.
    """
    result = await gmail_client.authenticate()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/labels")
async def http_list_labels() -> dict:
    """List all labels via HTTP."""
    if not gmail_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await gmail_client.list_labels()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/messages")
async def http_list_messages(
    query: Optional[str] = None,
    max_results: int = 10,
    include_spam_trash: bool = False,
) -> dict:
    """List messages via HTTP."""
    if not gmail_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await gmail_client.list_messages(
        query=query,
        max_results=max_results,
        include_spam_trash=include_spam_trash,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/messages/{message_id}")
async def http_get_message(
    message_id: str,
    format: str = "full",
) -> dict:
    """Get a specific message via HTTP."""
    if not gmail_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await gmail_client.get_message(
        message_id=message_id,
        format=format,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.post("/messages/send")
async def http_send_email(request: SendEmailRequest) -> dict:
    """Send an email via HTTP."""
    if not gmail_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await gmail_client.send_email(
        to=request.to,
        subject=request.subject,
        body=request.body,
        cc=request.cc,
        bcc=request.bcc,
        html_body=request.html_body,
        reply_to=request.reply_to,
        thread_id=request.thread_id,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.delete("/messages/{message_id}")
async def http_trash_message(message_id: str) -> dict:
    """Trash a message via HTTP."""
    if not gmail_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await gmail_client.trash_message(message_id)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/drafts")
async def http_list_drafts(max_results: int = 10) -> dict:
    """List drafts via HTTP."""
    if not gmail_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await gmail_client.list_drafts(max_results=max_results)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Run the server."""
    import uvicorn

    logger.info(f"Starting Gmail MCP Server on {settings.host}:{settings.port}")

    if not settings.gmail_client_id:
        logger.warning("GMAIL_CLIENT_ID not set - authentication will not work")

    if gmail_client.is_authenticated():
        logger.info("Already authenticated with Gmail")
    else:
        logger.info("Not authenticated - run authentication flow to enable tools")

    uvicorn.run(
        fastapi_app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
