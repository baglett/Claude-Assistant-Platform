# =============================================================================
# Obsidian MCP Server
# =============================================================================
"""
FastMCP server providing Obsidian vault interaction tools.

This server exposes MCP tools for:
- Reading and writing notes in an Obsidian vault
- Searching notes by content or advanced queries
- Managing periodic notes (daily, weekly, monthly, etc.)
- Listing files and directories in the vault
- Executing Obsidian commands

The server communicates with Obsidian through the Local REST API plugin.

Requirements:
    - Obsidian with Local REST API plugin installed and enabled
    - API key from the plugin settings

Note:
    The Local REST API plugin defaults to:
    - HTTPS on port 27124 (with self-signed certificate)
    - HTTP on port 27123 (if enabled in plugin settings)
"""

import logging
import ssl
import urllib.parse
from enum import Enum
from typing import Any, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        obsidian_api_key: API key from Obsidian Local REST API plugin.
        obsidian_host: Hostname where Obsidian is running.
        obsidian_port: Port for the Local REST API.
        obsidian_protocol: HTTP or HTTPS (HTTPS uses self-signed cert).
        obsidian_verify_ssl: Whether to verify SSL certificates.
        host: Host address for this MCP server.
        port: Port number for this MCP server.
    """

    obsidian_api_key: str = Field(
        default="",
        description="API key from Obsidian Local REST API plugin",
    )
    obsidian_host: str = Field(
        default="127.0.0.1",
        description="Hostname where Obsidian is running",
    )
    obsidian_port: int = Field(
        default=27124,
        description="Port for Obsidian Local REST API (27124 for HTTPS, 27123 for HTTP)",
    )
    obsidian_protocol: str = Field(
        default="https",
        description="Protocol to use (http or https)",
    )
    obsidian_verify_ssl: bool = Field(
        default=False,
        description="Whether to verify SSL certificates (set False for self-signed)",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host address for this MCP server",
    )
    port: int = Field(
        default=8080,
        description="Port number for this MCP server",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def obsidian_base_url(self) -> str:
        """Get the base URL for Obsidian Local REST API."""
        return f"{self.obsidian_protocol}://{self.obsidian_host}:{self.obsidian_port}"


settings = Settings()


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------
class PatchOperation(str, Enum):
    """Operation type for PATCH requests."""

    APPEND = "append"
    PREPEND = "prepend"
    REPLACE = "replace"


class TargetType(str, Enum):
    """Target type for PATCH requests."""

    HEADING = "heading"
    BLOCK = "block"
    FRONTMATTER = "frontmatter"


class PeriodType(str, Enum):
    """Periodic note period types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# -----------------------------------------------------------------------------
# Pydantic Models for API
# -----------------------------------------------------------------------------
class NoteContent(BaseModel):
    """Model representing note content from Obsidian."""

    content: str = Field(..., description="The markdown content of the note")
    path: Optional[str] = Field(default=None, description="Path to the note")
    tags: Optional[list[str]] = Field(default=None, description="Tags in the note")
    frontmatter: Optional[dict[str, Any]] = Field(
        default=None, description="YAML frontmatter parsed as dict"
    )
    stat: Optional[dict[str, Any]] = Field(
        default=None, description="File statistics (ctime, mtime, size)"
    )


class FileInfo(BaseModel):
    """Model representing a file or directory in the vault."""

    path: str = Field(..., description="Path relative to vault root")
    name: str = Field(..., description="File or directory name")
    is_directory: bool = Field(..., description="Whether this is a directory")


class SearchResult(BaseModel):
    """Model representing a search result."""

    filename: str = Field(..., description="Path to the matching file")
    score: Optional[float] = Field(default=None, description="Relevance score")
    matches: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Matching text contexts"
    )


class Command(BaseModel):
    """Model representing an Obsidian command."""

    id: str = Field(..., description="Command ID")
    name: str = Field(..., description="Human-readable command name")


class OperationResponse(BaseModel):
    """Generic response model for operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: Optional[str] = Field(default=None, description="Status message")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    data: Optional[Any] = Field(default=None, description="Additional response data")


# -----------------------------------------------------------------------------
# Obsidian API Client
# -----------------------------------------------------------------------------
class ObsidianClient:
    """
    HTTP client for Obsidian Local REST API.

    Provides methods for interacting with an Obsidian vault through
    the Local REST API plugin.

    Attributes:
        api_key: API key for authentication.
        base_url: Base URL for API requests.
        verify_ssl: Whether to verify SSL certificates.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        verify_ssl: bool = False,
    ) -> None:
        """
        Initialize the Obsidian client.

        Args:
            api_key: API key from Local REST API plugin settings.
            base_url: Base URL for the Obsidian API.
            verify_ssl: Whether to verify SSL certificates.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            # Create SSL context that doesn't verify for self-signed certs
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context = True

            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0),
                verify=ssl_context if not self.verify_ssl else True,
            )
        return self._client

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": content_type,
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # -------------------------------------------------------------------------
    # Server Status
    # -------------------------------------------------------------------------
    async def get_status(self) -> OperationResponse:
        """Get server status and authentication status."""
        client = await self._get_client()
        try:
            response = await client.get(
                f"{self.base_url}/",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return OperationResponse(
                success=True,
                message="Connected to Obsidian",
                data=data,
            )
        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            return OperationResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # Vault File Operations
    # -------------------------------------------------------------------------
    async def list_files(
        self, directory: str = "", include_content: bool = False
    ) -> OperationResponse:
        """
        List files and directories in the vault.

        Args:
            directory: Directory path relative to vault root (empty for root).
            include_content: Whether to include file metadata.

        Returns:
            OperationResponse with list of files.
        """
        client = await self._get_client()
        path = f"/vault/{directory}" if directory else "/vault/"
        # Ensure trailing slash for directory listing
        if not path.endswith("/"):
            path += "/"

        try:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            # Parse file list
            files = []
            for item in data.get("files", []):
                files.append(
                    FileInfo(
                        path=item,
                        name=item.split("/")[-1] if "/" in item else item,
                        is_directory=item.endswith("/"),
                    )
                )

            return OperationResponse(
                success=True,
                data={"files": [f.model_dump() for f in files]},
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing files: {e.response.status_code}")
            return OperationResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return OperationResponse(success=False, error=str(e))

    async def read_note(
        self, path: str, format_type: str = "markdown"
    ) -> OperationResponse:
        """
        Read a note from the vault.

        Args:
            path: Path to the note relative to vault root.
            format_type: Response format ('markdown' or 'json').

        Returns:
            OperationResponse with note content.
        """
        client = await self._get_client()
        encoded_path = urllib.parse.quote(path, safe="/")

        # Set Accept header based on format
        headers = self._get_headers()
        if format_type == "json":
            headers["Accept"] = "application/vnd.olrapi.note+json"
        else:
            headers["Accept"] = "text/markdown"

        try:
            response = await client.get(
                f"{self.base_url}/vault/{encoded_path}",
                headers=headers,
            )
            response.raise_for_status()

            if format_type == "json":
                data = response.json()
                return OperationResponse(
                    success=True,
                    data=NoteContent(
                        content=data.get("content", ""),
                        path=path,
                        tags=data.get("tags"),
                        frontmatter=data.get("frontmatter"),
                        stat=data.get("stat"),
                    ).model_dump(),
                )
            else:
                return OperationResponse(
                    success=True,
                    data=NoteContent(content=response.text, path=path).model_dump(),
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return OperationResponse(
                    success=False, error=f"Note not found: {path}"
                )
            logger.error(f"HTTP error reading note: {e.response.status_code}")
            return OperationResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Error reading note: {e}")
            return OperationResponse(success=False, error=str(e))

    async def create_note(
        self, path: str, content: str, overwrite: bool = False
    ) -> OperationResponse:
        """
        Create a new note in the vault.

        Args:
            path: Path for the new note.
            content: Markdown content for the note.
            overwrite: If True, overwrite existing note (PUT). Otherwise append (POST).

        Returns:
            OperationResponse indicating success/failure.
        """
        client = await self._get_client()
        encoded_path = urllib.parse.quote(path, safe="/")

        headers = self._get_headers("text/markdown")

        try:
            if overwrite:
                response = await client.put(
                    f"{self.base_url}/vault/{encoded_path}",
                    headers=headers,
                    content=content,
                )
            else:
                response = await client.post(
                    f"{self.base_url}/vault/{encoded_path}",
                    headers=headers,
                    content=content,
                )
            response.raise_for_status()

            return OperationResponse(
                success=True,
                message=f"Note {'created/overwritten' if overwrite else 'created/appended'}: {path}",
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating note: {e.response.status_code}")
            return OperationResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return OperationResponse(success=False, error=str(e))

    async def update_note(
        self,
        path: str,
        content: str,
        operation: PatchOperation = PatchOperation.APPEND,
        target_type: Optional[TargetType] = None,
        target: Optional[str] = None,
    ) -> OperationResponse:
        """
        Update an existing note using PATCH operation.

        Args:
            path: Path to the note.
            content: Content to insert.
            operation: Type of operation (append, prepend, replace).
            target_type: Target location type (heading, block, frontmatter).
            target: Specific target identifier (heading text, block ref, etc.).

        Returns:
            OperationResponse indicating success/failure.
        """
        client = await self._get_client()
        encoded_path = urllib.parse.quote(path, safe="/")

        headers = self._get_headers("text/markdown")
        headers["Operation"] = operation.value

        if target_type and target:
            headers["Target-Type"] = target_type.value
            headers["Target"] = urllib.parse.quote(target)

        try:
            response = await client.patch(
                f"{self.base_url}/vault/{encoded_path}",
                headers=headers,
                content=content,
            )
            response.raise_for_status()

            return OperationResponse(
                success=True,
                message=f"Note updated ({operation.value}): {path}",
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating note: {e.response.status_code}")
            return OperationResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Error updating note: {e}")
            return OperationResponse(success=False, error=str(e))

    async def delete_note(self, path: str) -> OperationResponse:
        """
        Delete a note from the vault.

        Args:
            path: Path to the note to delete.

        Returns:
            OperationResponse indicating success/failure.
        """
        client = await self._get_client()
        encoded_path = urllib.parse.quote(path, safe="/")

        try:
            response = await client.delete(
                f"{self.base_url}/vault/{encoded_path}",
                headers=self._get_headers(),
            )
            response.raise_for_status()

            return OperationResponse(
                success=True,
                message=f"Note deleted: {path}",
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return OperationResponse(
                    success=False, error=f"Note not found: {path}"
                )
            logger.error(f"HTTP error deleting note: {e.response.status_code}")
            return OperationResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"Error deleting note: {e}")
            return OperationResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # Search Operations
    # -------------------------------------------------------------------------
    async def search_simple(
        self, query: str, context_length: int = 100
    ) -> OperationResponse:
        """
        Simple text search across the vault.

        Args:
            query: Search query string.
            context_length: Number of characters of context to return.

        Returns:
            OperationResponse with search results.
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.base_url}/search/simple/",
                headers=self._get_headers("application/json"),
                json={"query": query, "contextLength": context_length},
            )
            response.raise_for_status()
            data = response.json()

            results = [
                SearchResult(
                    filename=item.get("filename", ""),
                    score=item.get("score"),
                    matches=item.get("matches"),
                ).model_dump()
                for item in data
            ]

            return OperationResponse(
                success=True,
                data={"results": results, "count": len(results)},
            )

        except Exception as e:
            logger.error(f"Error searching vault: {e}")
            return OperationResponse(success=False, error=str(e))

    async def search_advanced(
        self, query: str, query_type: str = "dataview"
    ) -> OperationResponse:
        """
        Advanced search using Dataview DQL or JsonLogic.

        Args:
            query: The query string (Dataview DQL or JsonLogic JSON).
            query_type: Type of query ('dataview' or 'jsonlogic').

        Returns:
            OperationResponse with search results.
        """
        client = await self._get_client()

        headers = self._get_headers()
        if query_type == "dataview":
            headers["Content-Type"] = "application/vnd.olrapi.dataview.dql+txt"
        else:
            headers["Content-Type"] = "application/vnd.olrapi.jsonlogic+json"

        try:
            response = await client.post(
                f"{self.base_url}/search/",
                headers=headers,
                content=query,
            )
            response.raise_for_status()
            data = response.json()

            return OperationResponse(
                success=True,
                data=data,
            )

        except Exception as e:
            logger.error(f"Error in advanced search: {e}")
            return OperationResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # Periodic Notes
    # -------------------------------------------------------------------------
    async def get_periodic_note(
        self,
        period: PeriodType,
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
        format_type: str = "markdown",
    ) -> OperationResponse:
        """
        Get a periodic note (daily, weekly, monthly, etc.).

        Args:
            period: Type of periodic note.
            year: Specific year (optional, defaults to current).
            month: Specific month (optional).
            day: Specific day (optional).
            format_type: Response format ('markdown' or 'json').

        Returns:
            OperationResponse with note content.
        """
        client = await self._get_client()

        # Build path based on parameters
        if year and month and day:
            path = f"/periodic/{period.value}/{year}/{month}/{day}/"
        else:
            path = f"/periodic/{period.value}/"

        headers = self._get_headers()
        if format_type == "json":
            headers["Accept"] = "application/vnd.olrapi.note+json"
        else:
            headers["Accept"] = "text/markdown"

        try:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=headers,
            )
            response.raise_for_status()

            if format_type == "json":
                data = response.json()
                return OperationResponse(
                    success=True,
                    data=NoteContent(
                        content=data.get("content", ""),
                        path=data.get("path"),
                        tags=data.get("tags"),
                        frontmatter=data.get("frontmatter"),
                        stat=data.get("stat"),
                    ).model_dump(),
                )
            else:
                return OperationResponse(
                    success=True,
                    data=NoteContent(content=response.text).model_dump(),
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return OperationResponse(
                    success=False, error=f"Periodic note not found for {period.value}"
                )
            return OperationResponse(
                success=False, error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Error getting periodic note: {e}")
            return OperationResponse(success=False, error=str(e))

    async def create_periodic_note(
        self,
        period: PeriodType,
        content: str,
        overwrite: bool = False,
    ) -> OperationResponse:
        """
        Create or update a periodic note.

        Args:
            period: Type of periodic note.
            content: Content for the note.
            overwrite: If True, replace content. Otherwise append.

        Returns:
            OperationResponse indicating success/failure.
        """
        client = await self._get_client()
        path = f"/periodic/{period.value}/"

        headers = self._get_headers("text/markdown")

        try:
            if overwrite:
                response = await client.put(
                    f"{self.base_url}{path}",
                    headers=headers,
                    content=content,
                )
            else:
                response = await client.post(
                    f"{self.base_url}{path}",
                    headers=headers,
                    content=content,
                )
            response.raise_for_status()

            return OperationResponse(
                success=True,
                message=f"Periodic note ({period.value}) {'updated' if overwrite else 'appended'}",
            )

        except Exception as e:
            logger.error(f"Error creating periodic note: {e}")
            return OperationResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------
    async def list_commands(self) -> OperationResponse:
        """
        List available Obsidian commands.

        Returns:
            OperationResponse with list of commands.
        """
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.base_url}/commands/",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            commands = [
                Command(id=cmd.get("id", ""), name=cmd.get("name", "")).model_dump()
                for cmd in data.get("commands", [])
            ]

            return OperationResponse(
                success=True,
                data={"commands": commands, "count": len(commands)},
            )

        except Exception as e:
            logger.error(f"Error listing commands: {e}")
            return OperationResponse(success=False, error=str(e))

    async def execute_command(self, command_id: str) -> OperationResponse:
        """
        Execute an Obsidian command.

        Args:
            command_id: ID of the command to execute.

        Returns:
            OperationResponse indicating success/failure.
        """
        client = await self._get_client()
        encoded_id = urllib.parse.quote(command_id, safe="")

        try:
            response = await client.post(
                f"{self.base_url}/commands/{encoded_id}/",
                headers=self._get_headers(),
            )
            response.raise_for_status()

            return OperationResponse(
                success=True,
                message=f"Command executed: {command_id}",
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return OperationResponse(
                    success=False, error=f"Command not found: {command_id}"
                )
            return OperationResponse(
                success=False, error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return OperationResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # Active File Operations
    # -------------------------------------------------------------------------
    async def get_active_file(self, format_type: str = "markdown") -> OperationResponse:
        """
        Get the currently active (open) file in Obsidian.

        Args:
            format_type: Response format ('markdown' or 'json').

        Returns:
            OperationResponse with file content.
        """
        client = await self._get_client()

        headers = self._get_headers()
        if format_type == "json":
            headers["Accept"] = "application/vnd.olrapi.note+json"
        else:
            headers["Accept"] = "text/markdown"

        try:
            response = await client.get(
                f"{self.base_url}/active/",
                headers=headers,
            )
            response.raise_for_status()

            if format_type == "json":
                data = response.json()
                return OperationResponse(
                    success=True,
                    data=NoteContent(
                        content=data.get("content", ""),
                        path=data.get("path"),
                        tags=data.get("tags"),
                        frontmatter=data.get("frontmatter"),
                        stat=data.get("stat"),
                    ).model_dump(),
                )
            else:
                return OperationResponse(
                    success=True,
                    data=NoteContent(content=response.text).model_dump(),
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return OperationResponse(
                    success=False, error="No active file in Obsidian"
                )
            return OperationResponse(
                success=False, error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Error getting active file: {e}")
            return OperationResponse(success=False, error=str(e))

    async def open_file(self, path: str, new_leaf: bool = False) -> OperationResponse:
        """
        Open a file in Obsidian.

        Args:
            path: Path to the file to open.
            new_leaf: If True, open in a new tab/pane.

        Returns:
            OperationResponse indicating success/failure.
        """
        client = await self._get_client()
        encoded_path = urllib.parse.quote(path, safe="/")

        try:
            response = await client.post(
                f"{self.base_url}/open/{encoded_path}",
                headers=self._get_headers(),
                json={"newLeaf": new_leaf} if new_leaf else None,
            )
            response.raise_for_status()

            return OperationResponse(
                success=True,
                message=f"Opened file: {path}",
            )

        except Exception as e:
            logger.error(f"Error opening file: {e}")
            return OperationResponse(success=False, error=str(e))


# -----------------------------------------------------------------------------
# Initialize Obsidian Client
# -----------------------------------------------------------------------------
obsidian_client = ObsidianClient(
    api_key=settings.obsidian_api_key,
    base_url=settings.obsidian_base_url,
    verify_ssl=settings.obsidian_verify_ssl,
)


# -----------------------------------------------------------------------------
# FastMCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("obsidian-mcp")


@mcp.tool()
async def list_vault_files(directory: str = "") -> dict:
    """
    List files and directories in the Obsidian vault.

    Args:
        directory: Directory path relative to vault root. Empty string for root.

    Returns:
        Dictionary with list of files and directories.
    """
    result = await obsidian_client.list_files(directory)
    return result.model_dump()


@mcp.tool()
async def read_note(path: str, include_metadata: bool = False) -> dict:
    """
    Read a note from the Obsidian vault.

    Args:
        path: Path to the note relative to vault root (e.g., 'folder/note.md').
        include_metadata: If True, include frontmatter, tags, and file stats.

    Returns:
        Dictionary with note content and optionally metadata.
    """
    format_type = "json" if include_metadata else "markdown"
    result = await obsidian_client.read_note(path, format_type)
    return result.model_dump()


@mcp.tool()
async def create_note(path: str, content: str, overwrite: bool = False) -> dict:
    """
    Create a new note in the Obsidian vault.

    Args:
        path: Path for the new note (e.g., 'folder/new-note.md').
        content: Markdown content for the note.
        overwrite: If True, overwrite existing note. If False, append to existing.

    Returns:
        Dictionary with operation result.
    """
    result = await obsidian_client.create_note(path, content, overwrite)
    return result.model_dump()


@mcp.tool()
async def update_note(
    path: str,
    content: str,
    operation: Literal["append", "prepend", "replace"] = "append",
    target_type: Optional[Literal["heading", "block", "frontmatter"]] = None,
    target: Optional[str] = None,
) -> dict:
    """
    Update an existing note in the Obsidian vault.

    Args:
        path: Path to the note to update.
        content: Content to insert.
        operation: How to insert content ('append', 'prepend', 'replace').
        target_type: Target location type ('heading', 'block', 'frontmatter').
        target: Specific target (heading text, block reference, frontmatter key).

    Returns:
        Dictionary with operation result.
    """
    op = PatchOperation(operation)
    tt = TargetType(target_type) if target_type else None
    result = await obsidian_client.update_note(path, content, op, tt, target)
    return result.model_dump()


@mcp.tool()
async def delete_note(path: str) -> dict:
    """
    Delete a note from the Obsidian vault.

    Args:
        path: Path to the note to delete.

    Returns:
        Dictionary with operation result.
    """
    result = await obsidian_client.delete_note(path)
    return result.model_dump()


@mcp.tool()
async def search_vault(query: str, context_length: int = 100) -> dict:
    """
    Search for notes in the vault by text content.

    Args:
        query: Search query string.
        context_length: Number of characters of context to return around matches.

    Returns:
        Dictionary with search results including matching files and contexts.
    """
    result = await obsidian_client.search_simple(query, context_length)
    return result.model_dump()


@mcp.tool()
async def search_dataview(query: str) -> dict:
    """
    Execute a Dataview DQL query on the vault.

    Requires the Dataview plugin to be installed in Obsidian.

    Args:
        query: Dataview DQL query (TABLE, LIST, TASK, or CALENDAR type).
               Example: 'TABLE file.name, file.mtime FROM "Projects" SORT file.mtime DESC'

    Returns:
        Dictionary with query results.
    """
    result = await obsidian_client.search_advanced(query, "dataview")
    return result.model_dump()


@mcp.tool()
async def get_daily_note(
    year: Optional[int] = None,
    month: Optional[int] = None,
    day: Optional[int] = None,
    include_metadata: bool = False,
) -> dict:
    """
    Get a daily note from the vault.

    Args:
        year: Specific year (optional, defaults to today).
        month: Specific month (optional).
        day: Specific day (optional).
        include_metadata: If True, include frontmatter and tags.

    Returns:
        Dictionary with daily note content.
    """
    format_type = "json" if include_metadata else "markdown"
    result = await obsidian_client.get_periodic_note(
        PeriodType.DAILY, year, month, day, format_type
    )
    return result.model_dump()


@mcp.tool()
async def get_weekly_note(include_metadata: bool = False) -> dict:
    """
    Get the current weekly note from the vault.

    Args:
        include_metadata: If True, include frontmatter and tags.

    Returns:
        Dictionary with weekly note content.
    """
    format_type = "json" if include_metadata else "markdown"
    result = await obsidian_client.get_periodic_note(
        PeriodType.WEEKLY, format_type=format_type
    )
    return result.model_dump()


@mcp.tool()
async def append_to_daily_note(content: str) -> dict:
    """
    Append content to today's daily note.

    Args:
        content: Markdown content to append.

    Returns:
        Dictionary with operation result.
    """
    result = await obsidian_client.create_periodic_note(
        PeriodType.DAILY, content, overwrite=False
    )
    return result.model_dump()


@mcp.tool()
async def list_commands() -> dict:
    """
    List available Obsidian commands.

    Returns:
        Dictionary with list of command IDs and names.
    """
    result = await obsidian_client.list_commands()
    return result.model_dump()


@mcp.tool()
async def execute_command(command_id: str) -> dict:
    """
    Execute an Obsidian command by ID.

    Args:
        command_id: The command ID (from list_commands).

    Returns:
        Dictionary with operation result.
    """
    result = await obsidian_client.execute_command(command_id)
    return result.model_dump()


@mcp.tool()
async def get_active_file(include_metadata: bool = False) -> dict:
    """
    Get the currently active (open) file in Obsidian.

    Args:
        include_metadata: If True, include frontmatter and tags.

    Returns:
        Dictionary with active file content.
    """
    format_type = "json" if include_metadata else "markdown"
    result = await obsidian_client.get_active_file(format_type)
    return result.model_dump()


@mcp.tool()
async def open_file(path: str, new_tab: bool = False) -> dict:
    """
    Open a file in Obsidian.

    Args:
        path: Path to the file to open.
        new_tab: If True, open in a new tab.

    Returns:
        Dictionary with operation result.
    """
    result = await obsidian_client.open_file(path, new_tab)
    return result.model_dump()


@mcp.tool()
async def check_connection() -> dict:
    """
    Check the connection to Obsidian Local REST API.

    Returns:
        Dictionary with connection status and server info.
    """
    result = await obsidian_client.get_status()
    return result.model_dump()


# -----------------------------------------------------------------------------
# FastAPI Application (for HTTP access)
# -----------------------------------------------------------------------------
fastapi_app = FastAPI(
    title="Obsidian MCP Server",
    description="MCP server providing Obsidian vault interaction tools",
    version="0.1.0",
)


@fastapi_app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "obsidian-mcp"}


@fastapi_app.get("/status")
async def get_status() -> dict:
    """Get Obsidian connection status."""
    result = await obsidian_client.get_status()
    return result.model_dump()


@fastapi_app.get("/tools/list_files")
async def http_list_files(directory: str = "") -> dict:
    """HTTP endpoint for listing vault files."""
    if not settings.obsidian_api_key:
        raise HTTPException(status_code=500, detail="Obsidian API key not configured")
    result = await obsidian_client.list_files(directory)
    return result.model_dump()


@fastapi_app.get("/tools/read_note")
async def http_read_note(path: str, include_metadata: bool = False) -> dict:
    """HTTP endpoint for reading a note."""
    if not settings.obsidian_api_key:
        raise HTTPException(status_code=500, detail="Obsidian API key not configured")
    format_type = "json" if include_metadata else "markdown"
    result = await obsidian_client.read_note(path, format_type)
    return result.model_dump()


@fastapi_app.post("/tools/search")
async def http_search(query: str, context_length: int = 100) -> dict:
    """HTTP endpoint for searching the vault."""
    if not settings.obsidian_api_key:
        raise HTTPException(status_code=500, detail="Obsidian API key not configured")
    result = await obsidian_client.search_simple(query, context_length)
    return result.model_dump()


@fastapi_app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    await obsidian_client.close()
    logger.info("Obsidian client closed")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Run the server."""
    import uvicorn

    logger.info(f"Starting Obsidian MCP Server on {settings.host}:{settings.port}")
    logger.info(f"Obsidian API: {settings.obsidian_base_url}")

    if not settings.obsidian_api_key:
        logger.warning(
            "OBSIDIAN_API_KEY not set - server will not function properly. "
            "Get the API key from Obsidian > Settings > Local REST API"
        )

    uvicorn.run(
        fastapi_app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
