# =============================================================================
# Google Drive MCP Server - Pydantic Models
# =============================================================================
"""
Pydantic models for Google Drive API requests and responses.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Base Response Model
# -----------------------------------------------------------------------------
class DriveResponse(BaseModel):
    """Base response model with success indicator."""

    success: bool = Field(default=True, description="Whether the operation succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# -----------------------------------------------------------------------------
# File Models
# -----------------------------------------------------------------------------
class FileInfo(BaseModel):
    """Information about a Google Drive file."""

    id: str = Field(..., description="Unique file ID")
    name: str = Field(..., description="File name")
    mime_type: str = Field(..., description="MIME type of the file")
    size: Optional[int] = Field(default=None, description="File size in bytes")
    created_time: Optional[datetime] = Field(
        default=None, description="When the file was created"
    )
    modified_time: Optional[datetime] = Field(
        default=None, description="When the file was last modified"
    )
    parents: list[str] = Field(default_factory=list, description="Parent folder IDs")
    web_view_link: Optional[str] = Field(
        default=None, description="Link to view the file in browser"
    )
    web_content_link: Optional[str] = Field(
        default=None, description="Link to download the file"
    )
    thumbnail_link: Optional[str] = Field(
        default=None, description="Link to thumbnail image"
    )
    shared: bool = Field(default=False, description="Whether file is shared")
    starred: bool = Field(default=False, description="Whether file is starred")
    trashed: bool = Field(default=False, description="Whether file is in trash")


class FileListResponse(DriveResponse):
    """Response containing a list of files."""

    files: list[FileInfo] = Field(default_factory=list, description="List of files")
    next_page_token: Optional[str] = Field(
        default=None, description="Token for next page of results"
    )


class FileUploadResponse(DriveResponse):
    """Response after uploading a file."""

    file: Optional[FileInfo] = Field(default=None, description="Uploaded file info")


class FileDeleteResponse(DriveResponse):
    """Response after deleting a file."""

    file_id: Optional[str] = Field(default=None, description="Deleted file ID")


# -----------------------------------------------------------------------------
# Folder Models
# -----------------------------------------------------------------------------
class FolderInfo(BaseModel):
    """Information about a Google Drive folder."""

    id: str = Field(..., description="Unique folder ID")
    name: str = Field(..., description="Folder name")
    created_time: Optional[datetime] = Field(
        default=None, description="When the folder was created"
    )
    parents: list[str] = Field(default_factory=list, description="Parent folder IDs")
    web_view_link: Optional[str] = Field(
        default=None, description="Link to view the folder"
    )


class FolderCreateResponse(DriveResponse):
    """Response after creating a folder."""

    folder: Optional[FolderInfo] = Field(
        default=None, description="Created folder info"
    )


# -----------------------------------------------------------------------------
# Sharing Models
# -----------------------------------------------------------------------------
class ShareableLink(BaseModel):
    """Shareable link information."""

    link: str = Field(..., description="Shareable URL")
    permission_id: str = Field(..., description="Permission ID")
    role: str = Field(..., description="Permission role (reader, writer, etc.)")


class ShareableLinkResponse(DriveResponse):
    """Response after creating a shareable link."""

    file_id: str = Field(..., description="File ID")
    web_view_link: Optional[str] = Field(
        default=None, description="Web view link for file"
    )
    permission: Optional[ShareableLink] = Field(
        default=None, description="Permission details"
    )


# -----------------------------------------------------------------------------
# Search Models
# -----------------------------------------------------------------------------
class SearchResponse(DriveResponse):
    """Response from file search."""

    files: list[FileInfo] = Field(default_factory=list, description="Matching files")
    query: str = Field(..., description="Search query used")
    total_results: int = Field(default=0, description="Number of results found")


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------
class UploadFileRequest(BaseModel):
    """Request to upload a file."""

    name: str = Field(..., description="Name for the file in Drive")
    content: str = Field(
        ..., description="File content (base64 encoded for binary files)"
    )
    mime_type: str = Field(
        default="application/octet-stream", description="MIME type of the file"
    )
    parent_folder_id: Optional[str] = Field(
        default=None, description="Parent folder ID"
    )
    description: Optional[str] = Field(default=None, description="File description")


class CreateFolderRequest(BaseModel):
    """Request to create a folder."""

    name: str = Field(..., description="Folder name")
    parent_folder_id: Optional[str] = Field(
        default=None, description="Parent folder ID"
    )


class CreateShareableLinkRequest(BaseModel):
    """Request to create a shareable link."""

    file_id: str = Field(..., description="File ID to share")
    role: str = Field(
        default="reader", description="Permission role (reader, writer, commenter)"
    )


# -----------------------------------------------------------------------------
# About/Status Models
# -----------------------------------------------------------------------------
class StorageQuota(BaseModel):
    """Storage quota information."""

    limit: Optional[int] = Field(default=None, description="Total storage limit (bytes)")
    usage: Optional[int] = Field(default=None, description="Current usage (bytes)")
    usage_in_drive: Optional[int] = Field(
        default=None, description="Usage in Drive (bytes)"
    )
    usage_in_drive_trash: Optional[int] = Field(
        default=None, description="Usage in trash (bytes)"
    )


class AboutResponse(DriveResponse):
    """Response with Drive account information."""

    user_email: Optional[str] = Field(default=None, description="User's email")
    user_name: Optional[str] = Field(default=None, description="User's display name")
    storage_quota: Optional[StorageQuota] = Field(
        default=None, description="Storage quota info"
    )


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def file_info_from_api(file_data: dict[str, Any]) -> FileInfo:
    """
    Convert Google Drive API file response to FileInfo model.

    Args:
        file_data: Raw file data from Drive API.

    Returns:
        FileInfo model instance.
    """
    return FileInfo(
        id=file_data.get("id", ""),
        name=file_data.get("name", ""),
        mime_type=file_data.get("mimeType", ""),
        size=int(file_data.get("size", 0)) if file_data.get("size") else None,
        created_time=file_data.get("createdTime"),
        modified_time=file_data.get("modifiedTime"),
        parents=file_data.get("parents", []),
        web_view_link=file_data.get("webViewLink"),
        web_content_link=file_data.get("webContentLink"),
        thumbnail_link=file_data.get("thumbnailLink"),
        shared=file_data.get("shared", False),
        starred=file_data.get("starred", False),
        trashed=file_data.get("trashed", False),
    )


def folder_info_from_api(folder_data: dict[str, Any]) -> FolderInfo:
    """
    Convert Google Drive API folder response to FolderInfo model.

    Args:
        folder_data: Raw folder data from Drive API.

    Returns:
        FolderInfo model instance.
    """
    return FolderInfo(
        id=folder_data.get("id", ""),
        name=folder_data.get("name", ""),
        created_time=folder_data.get("createdTime"),
        parents=folder_data.get("parents", []),
        web_view_link=folder_data.get("webViewLink"),
    )
