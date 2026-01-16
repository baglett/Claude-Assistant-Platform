# =============================================================================
# Google Drive MCP Server
# =============================================================================
"""
FastMCP server providing Google Drive API tools.

This server exposes MCP tools for:
- Uploading and downloading files
- Creating and managing folders
- Sharing files and creating shareable links
- Searching files
- Getting storage quota information

The server runs as a standalone HTTP service and can be called by the
orchestrator or other components to interact with Google Drive.
"""

import base64
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .auth import DriveAuthManager
from .client import DriveClient
from .models import (
    CreateFolderRequest,
    CreateShareableLinkRequest,
    UploadFileRequest,
)

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
        google_drive_client_id: OAuth client ID.
        google_drive_client_secret: OAuth client secret.
        google_drive_token_path: Path to store OAuth tokens.
        google_drive_oauth_port: Port for OAuth callback.
        host: Host address for the server.
        port: Port number for the server.
    """

    google_drive_client_id: str = Field(
        default="",
        description="Google OAuth client ID",
    )
    google_drive_client_secret: str = Field(
        default="",
        description="Google OAuth client secret",
    )
    google_drive_token_path: str = Field(
        default="./data/drive_token.json",
        description="Path to store OAuth tokens",
    )
    google_drive_oauth_port: int = Field(
        default=8088,
        description="Port for OAuth callback server",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host address for the server",
    )
    port: int = Field(
        default=8087,
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
auth_manager = DriveAuthManager(
    client_id=settings.google_drive_client_id,
    client_secret=settings.google_drive_client_secret,
    token_path=settings.google_drive_token_path,
    oauth_port=settings.google_drive_oauth_port,
)

drive_client = DriveClient(auth_manager=auth_manager)


# -----------------------------------------------------------------------------
# FastMCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("google-drive-mcp")


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
    is_auth = drive_client.is_authenticated()
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
# File Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def upload_file(
    name: str,
    content_base64: str,
    mime_type: str = "application/octet-stream",
    parent_folder_id: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Upload a file to Google Drive.

    Args:
        name: Name for the file in Drive.
        content_base64: Base64 encoded file content.
        mime_type: MIME type of the file (e.g., "application/pdf", "text/plain").
        parent_folder_id: ID of the parent folder (optional).
        description: Description for the file (optional).

    Returns:
        Dictionary with uploaded file info including ID and web link.
    """
    result = await drive_client.upload_file_base64(
        name=name,
        content_base64=content_base64,
        mime_type=mime_type,
        parent_folder_id=parent_folder_id,
        description=description,
    )
    return result.model_dump()


@mcp.tool()
async def list_files(
    folder_id: Optional[str] = None,
    page_size: int = 20,
    include_trashed: bool = False,
) -> dict:
    """
    List files in Google Drive.

    Args:
        folder_id: ID of the folder to list (None for root).
        page_size: Number of results per page (default: 20).
        include_trashed: Whether to include trashed files (default: False).

    Returns:
        Dictionary containing list of files with their IDs, names, and links.
    """
    result = await drive_client.list_files(
        folder_id=folder_id,
        page_size=page_size,
        include_trashed=include_trashed,
    )
    return result.model_dump()


@mcp.tool()
async def get_file(file_id: str) -> dict:
    """
    Get file metadata by ID.

    Args:
        file_id: The file ID to retrieve.

    Returns:
        Dictionary with file metadata including name, size, and links.
    """
    result = await drive_client.get_file(file_id)
    return result.model_dump()


@mcp.tool()
async def delete_file(file_id: str, permanent: bool = False) -> dict:
    """
    Delete a file (move to trash or permanently delete).

    Args:
        file_id: The file ID to delete.
        permanent: If True, permanently delete; otherwise move to trash.

    Returns:
        Dictionary indicating success or failure.
    """
    result = await drive_client.delete_file(file_id, permanent)
    return result.model_dump()


@mcp.tool()
async def search_files(query: str, page_size: int = 20) -> dict:
    """
    Search for files in Google Drive.

    Supports Drive query syntax:
    - name contains 'resume' - Files with 'resume' in name
    - mimeType='application/pdf' - PDF files only
    - modifiedTime > '2024-01-01' - Modified after date
    - 'folder_id' in parents - Files in specific folder

    Examples:
    - "name contains 'resume' and mimeType='application/pdf'"
    - "modifiedTime > '2024-01-01'"

    Args:
        query: Search query using Drive query syntax.
        page_size: Number of results to return (default: 20).

    Returns:
        Dictionary containing matching files.
    """
    result = await drive_client.search_files(query, page_size)
    return result.model_dump()


# -----------------------------------------------------------------------------
# Folder Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def create_folder(
    name: str,
    parent_folder_id: Optional[str] = None,
) -> dict:
    """
    Create a new folder in Google Drive.

    Args:
        name: Name for the folder.
        parent_folder_id: ID of parent folder (optional, creates in root if not specified).

    Returns:
        Dictionary with created folder info including ID and web link.
    """
    result = await drive_client.create_folder(name, parent_folder_id)
    return result.model_dump()


@mcp.tool()
async def get_or_create_folder(
    name: str,
    parent_folder_id: Optional[str] = None,
) -> dict:
    """
    Get existing folder or create if it doesn't exist.

    Useful for ensuring a folder exists before uploading files.

    Args:
        name: Name for the folder.
        parent_folder_id: ID of parent folder (optional).

    Returns:
        Dictionary with folder info including ID and web link.
    """
    result = await drive_client.get_or_create_folder(name, parent_folder_id)
    return result.model_dump()


# -----------------------------------------------------------------------------
# Sharing Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def create_shareable_link(
    file_id: str,
    role: str = "reader",
) -> dict:
    """
    Create a shareable link for a file.

    Makes the file accessible to anyone with the link.

    Args:
        file_id: ID of the file to share.
        role: Permission role - "reader" (view only), "writer" (can edit),
              or "commenter" (can comment). Default: "reader".

    Returns:
        Dictionary with shareable link and permission details.
    """
    result = await drive_client.create_shareable_link(file_id, role)
    return result.model_dump()


# -----------------------------------------------------------------------------
# Account Tools
# -----------------------------------------------------------------------------
@mcp.tool()
async def get_drive_about() -> dict:
    """
    Get information about the Google Drive account.

    Returns:
        Dictionary with user info and storage quota details.
    """
    result = await drive_client.get_about()
    return result.model_dump()


# -----------------------------------------------------------------------------
# FastAPI Application (for HTTP access)
# -----------------------------------------------------------------------------
fastapi_app = FastAPI(
    title="Google Drive MCP Server",
    description="MCP server providing Google Drive API tools",
    version="0.1.0",
)


@fastapi_app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Dictionary with service status.
    """
    is_auth = drive_client.is_authenticated()
    return {
        "status": "healthy",
        "service": "google-drive-mcp",
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
    result = await drive_client.authenticate()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/files")
async def http_list_files(
    folder_id: Optional[str] = None,
    page_size: int = 20,
    include_trashed: bool = False,
) -> dict:
    """List files via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.list_files(
        folder_id=folder_id,
        page_size=page_size,
        include_trashed=include_trashed,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.post("/files")
async def http_upload_file(request: UploadFileRequest) -> dict:
    """Upload a file via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.upload_file_base64(
        name=request.name,
        content_base64=request.content,
        mime_type=request.mime_type,
        parent_folder_id=request.parent_folder_id,
        description=request.description,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/files/{file_id}")
async def http_get_file(file_id: str) -> dict:
    """Get file metadata via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.get_file(file_id)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.delete("/files/{file_id}")
async def http_delete_file(file_id: str, permanent: bool = False) -> dict:
    """Delete a file via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.delete_file(file_id, permanent)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/search")
async def http_search_files(query: str, page_size: int = 20) -> dict:
    """Search files via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.search_files(query, page_size)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.post("/folders")
async def http_create_folder(request: CreateFolderRequest) -> dict:
    """Create a folder via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.create_folder(
        name=request.name,
        parent_folder_id=request.parent_folder_id,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.post("/share/{file_id}")
async def http_create_shareable_link(
    file_id: str,
    role: str = "reader",
) -> dict:
    """Create shareable link via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.create_shareable_link(file_id, role)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


@fastapi_app.get("/about")
async def http_get_about() -> dict:
    """Get Drive account info via HTTP."""
    if not drive_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await drive_client.get_about()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.model_dump()


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def is_interactive_environment() -> bool:
    """
    Check if we're running in an interactive environment where OAuth browser flow works.

    Returns False if running in Docker, headless server, or no display available.
    """
    import os
    import sys

    # Check for Docker
    if os.path.exists("/.dockerenv"):
        return False

    # Check for common container indicators
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return False

    # Check for display (Linux)
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return False

    # Check for SSH session without X forwarding
    if os.environ.get("SSH_CLIENT") and not os.environ.get("DISPLAY"):
        return False

    return True


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Run the server."""
    import os
    import uvicorn

    logger.info(f"Starting Google Drive MCP Server on {settings.host}:{settings.port}")

    if not settings.google_drive_client_id:
        logger.warning("GOOGLE_DRIVE_CLIENT_ID not set - authentication will not work")

    if drive_client.is_authenticated():
        logger.info("Already authenticated with Google Drive")
    else:
        # Check if we have credentials configured
        if settings.google_drive_client_id and settings.google_drive_client_secret:
            # Check if refresh token is available via env var
            refresh_token = os.environ.get("GOOGLE_DRIVE_REFRESH_TOKEN")

            if refresh_token:
                # Token should have been loaded by auth_manager already
                # If we got here, it means the refresh failed
                logger.error("GOOGLE_DRIVE_REFRESH_TOKEN is set but authentication failed")
                logger.error("The refresh token may be invalid or revoked")
                logger.info("Please generate a new refresh token")
            elif is_interactive_environment():
                # Interactive environment - can run browser OAuth flow
                logger.info("=" * 60)
                logger.info("Google Drive authentication required - starting OAuth flow...")
                logger.info("=" * 60)
                logger.info("")
                logger.info("A browser window will open for you to sign in to Google.")
                logger.info("After signing in, grant the requested permissions.")
                logger.info("")
                logger.info(
                    f"OAuth callback will be received on port {settings.google_drive_oauth_port}"
                )
                logger.info("")

                try:
                    auth_manager.authenticate()
                    logger.info("Authentication successful!")
                    logger.info("")
                    logger.info("To use this in production, set GOOGLE_DRIVE_REFRESH_TOKEN to:")
                    # Read the saved token to show the refresh token
                    import json

                    with open(settings.google_drive_token_path, "r") as f:
                        token_data = json.load(f)
                    logger.info(f"  {token_data.get('refresh_token')}")
                    logger.info("")
                except Exception as e:
                    logger.error(f"Authentication failed: {e}")
            else:
                # Headless/container environment - need refresh token
                logger.warning("=" * 60)
                logger.warning(
                    "Google Drive authentication required but running in headless mode"
                )
                logger.warning("=" * 60)
                logger.warning("")
                logger.warning(
                    "To authenticate, set the GOOGLE_DRIVE_REFRESH_TOKEN environment variable."
                )
                logger.warning("")
                logger.warning("To get a refresh token:")
                logger.warning("  1. Run this MCP server locally (not in Docker)")
                logger.warning("  2. Complete the OAuth flow in your browser")
                logger.warning("  3. Copy the refresh_token from data/drive_token.json")
                logger.warning("  4. Set GOOGLE_DRIVE_REFRESH_TOKEN=<token> in your environment")
                logger.warning("")
        else:
            logger.info(
                "Not authenticated - set GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET"
            )

    uvicorn.run(
        fastapi_app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
