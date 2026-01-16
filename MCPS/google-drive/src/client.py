# =============================================================================
# Google Drive MCP Server - Drive API Client
# =============================================================================
"""
Google Drive API client wrapper.

Provides async methods for interacting with Google Drive,
including file operations, folder management, and sharing.
"""

import asyncio
import base64
import io
import logging
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from .auth import DriveAuthManager
from .models import (
    AboutResponse,
    DriveResponse,
    FileDeleteResponse,
    FileInfo,
    FileListResponse,
    FileUploadResponse,
    FolderCreateResponse,
    FolderInfo,
    SearchResponse,
    ShareableLinkResponse,
    StorageQuota,
    file_info_from_api,
    folder_info_from_api,
)

logger = logging.getLogger(__name__)

# Google Drive folder MIME type
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class DriveClient:
    """
    Async client for Google Drive API operations.

    Provides methods for file upload, download, listing, sharing,
    and folder management.

    Attributes:
        auth_manager: DriveAuthManager for handling authentication.
    """

    def __init__(self, auth_manager: DriveAuthManager) -> None:
        """
        Initialize the Drive client.

        Args:
            auth_manager: DriveAuthManager instance for authentication.
        """
        self.auth_manager = auth_manager
        self._service = None

    def _get_service(self):
        """
        Get or create the Drive API service.

        Returns:
            Google Drive API service instance.
        """
        creds = self.auth_manager.get_credentials()
        if creds is None:
            return None

        if self._service is None:
            self._service = build("drive", "v3", credentials=creds)

        return self._service

    def is_authenticated(self) -> bool:
        """Check if authenticated with Drive API."""
        return self.auth_manager.is_authenticated

    async def authenticate(self) -> DriveResponse:
        """
        Trigger OAuth authentication flow.

        Returns:
            DriveResponse indicating success or failure.
        """
        try:
            self.auth_manager.authenticate()
            self._service = None  # Reset service to use new credentials
            return DriveResponse(success=True)
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return DriveResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------
    async def upload_file(
        self,
        name: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
        parent_folder_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> FileUploadResponse:
        """
        Upload a file to Google Drive.

        Args:
            name: Name for the file in Drive.
            content: File content as bytes.
            mime_type: MIME type of the file.
            parent_folder_id: ID of parent folder (optional).
            description: File description (optional).

        Returns:
            FileUploadResponse with uploaded file info.
        """
        service = self._get_service()
        if service is None:
            return FileUploadResponse(
                success=False, error="Not authenticated with Google Drive"
            )

        try:
            # Prepare file metadata
            file_metadata = {"name": name}

            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]

            if description:
                file_metadata["description"] = description

            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(content),
                mimetype=mime_type,
                resumable=True,
            )

            # Upload file
            loop = asyncio.get_event_loop()
            file = await loop.run_in_executor(
                None,
                lambda: service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink,webContentLink",
                )
                .execute(),
            )

            logger.info(f"Uploaded file: {file.get('name')} ({file.get('id')})")

            return FileUploadResponse(
                success=True,
                file=file_info_from_api(file),
            )

        except HttpError as e:
            logger.error(f"Drive API error uploading file: {e}")
            return FileUploadResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return FileUploadResponse(success=False, error=str(e))

    async def upload_file_base64(
        self,
        name: str,
        content_base64: str,
        mime_type: str = "application/octet-stream",
        parent_folder_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> FileUploadResponse:
        """
        Upload a file to Google Drive from base64 encoded content.

        Args:
            name: Name for the file in Drive.
            content_base64: Base64 encoded file content.
            mime_type: MIME type of the file.
            parent_folder_id: ID of parent folder (optional).
            description: File description (optional).

        Returns:
            FileUploadResponse with uploaded file info.
        """
        try:
            content = base64.b64decode(content_base64)
        except Exception as e:
            return FileUploadResponse(
                success=False, error=f"Invalid base64 content: {e}"
            )

        return await self.upload_file(
            name=name,
            content=content,
            mime_type=mime_type,
            parent_folder_id=parent_folder_id,
            description=description,
        )

    async def list_files(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 20,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        include_trashed: bool = False,
    ) -> FileListResponse:
        """
        List files in Google Drive.

        Args:
            folder_id: ID of folder to list (None for root).
            page_size: Number of results per page.
            page_token: Token for pagination.
            query: Additional query string.
            include_trashed: Whether to include trashed files.

        Returns:
            FileListResponse with list of files.
        """
        service = self._get_service()
        if service is None:
            return FileListResponse(
                success=False, error="Not authenticated with Google Drive"
            )

        try:
            # Build query
            query_parts = []

            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")

            if not include_trashed:
                query_parts.append("trashed = false")

            if query:
                query_parts.append(query)

            q = " and ".join(query_parts) if query_parts else None

            # Execute query
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: service.files()
                .list(
                    q=q,
                    pageSize=page_size,
                    pageToken=page_token,
                    fields="nextPageToken,files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink,webContentLink,shared,starred,trashed)",
                )
                .execute(),
            )

            files = [file_info_from_api(f) for f in result.get("files", [])]

            return FileListResponse(
                success=True,
                files=files,
                next_page_token=result.get("nextPageToken"),
            )

        except HttpError as e:
            logger.error(f"Drive API error listing files: {e}")
            return FileListResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return FileListResponse(success=False, error=str(e))

    async def get_file(self, file_id: str) -> FileUploadResponse:
        """
        Get file metadata by ID.

        Args:
            file_id: ID of the file.

        Returns:
            FileUploadResponse with file info.
        """
        service = self._get_service()
        if service is None:
            return FileUploadResponse(
                success=False, error="Not authenticated with Google Drive"
            )

        try:
            loop = asyncio.get_event_loop()
            file = await loop.run_in_executor(
                None,
                lambda: service.files()
                .get(
                    fileId=file_id,
                    fields="id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink,webContentLink,shared,starred,trashed",
                )
                .execute(),
            )

            return FileUploadResponse(
                success=True,
                file=file_info_from_api(file),
            )

        except HttpError as e:
            logger.error(f"Drive API error getting file: {e}")
            return FileUploadResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error getting file: {e}")
            return FileUploadResponse(success=False, error=str(e))

    async def delete_file(self, file_id: str, permanent: bool = False) -> FileDeleteResponse:
        """
        Delete a file (move to trash or permanently delete).

        Args:
            file_id: ID of the file to delete.
            permanent: If True, permanently delete; otherwise move to trash.

        Returns:
            FileDeleteResponse indicating success or failure.
        """
        service = self._get_service()
        if service is None:
            return FileDeleteResponse(
                success=False, error="Not authenticated with Google Drive"
            )

        try:
            loop = asyncio.get_event_loop()

            if permanent:
                await loop.run_in_executor(
                    None,
                    lambda: service.files().delete(fileId=file_id).execute(),
                )
            else:
                # Move to trash
                await loop.run_in_executor(
                    None,
                    lambda: service.files()
                    .update(fileId=file_id, body={"trashed": True})
                    .execute(),
                )

            logger.info(f"Deleted file: {file_id} (permanent={permanent})")

            return FileDeleteResponse(success=True, file_id=file_id)

        except HttpError as e:
            logger.error(f"Drive API error deleting file: {e}")
            return FileDeleteResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return FileDeleteResponse(success=False, error=str(e))

    async def search_files(
        self,
        query: str,
        page_size: int = 20,
    ) -> SearchResponse:
        """
        Search for files in Google Drive.

        Args:
            query: Search query (supports Drive query syntax).
            page_size: Number of results to return.

        Returns:
            SearchResponse with matching files.
        """
        service = self._get_service()
        if service is None:
            return SearchResponse(
                success=False, error="Not authenticated with Google Drive", query=query
            )

        try:
            # Add trashed filter
            full_query = f"({query}) and trashed = false"

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: service.files()
                .list(
                    q=full_query,
                    pageSize=page_size,
                    fields="files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink,webContentLink,shared)",
                )
                .execute(),
            )

            files = [file_info_from_api(f) for f in result.get("files", [])]

            return SearchResponse(
                success=True,
                files=files,
                query=query,
                total_results=len(files),
            )

        except HttpError as e:
            logger.error(f"Drive API error searching files: {e}")
            return SearchResponse(success=False, error=str(e), query=query)
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return SearchResponse(success=False, error=str(e), query=query)

    # -------------------------------------------------------------------------
    # Folder Operations
    # -------------------------------------------------------------------------
    async def create_folder(
        self,
        name: str,
        parent_folder_id: Optional[str] = None,
    ) -> FolderCreateResponse:
        """
        Create a new folder in Google Drive.

        Args:
            name: Name for the folder.
            parent_folder_id: ID of parent folder (optional).

        Returns:
            FolderCreateResponse with created folder info.
        """
        service = self._get_service()
        if service is None:
            return FolderCreateResponse(
                success=False, error="Not authenticated with Google Drive"
            )

        try:
            file_metadata = {
                "name": name,
                "mimeType": FOLDER_MIME_TYPE,
            }

            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]

            loop = asyncio.get_event_loop()
            folder = await loop.run_in_executor(
                None,
                lambda: service.files()
                .create(
                    body=file_metadata,
                    fields="id,name,createdTime,parents,webViewLink",
                )
                .execute(),
            )

            logger.info(f"Created folder: {folder.get('name')} ({folder.get('id')})")

            return FolderCreateResponse(
                success=True,
                folder=folder_info_from_api(folder),
            )

        except HttpError as e:
            logger.error(f"Drive API error creating folder: {e}")
            return FolderCreateResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return FolderCreateResponse(success=False, error=str(e))

    async def get_or_create_folder(
        self,
        name: str,
        parent_folder_id: Optional[str] = None,
    ) -> FolderCreateResponse:
        """
        Get existing folder or create if it doesn't exist.

        Args:
            name: Name for the folder.
            parent_folder_id: ID of parent folder (optional).

        Returns:
            FolderCreateResponse with folder info.
        """
        service = self._get_service()
        if service is None:
            return FolderCreateResponse(
                success=False, error="Not authenticated with Google Drive"
            )

        try:
            # Search for existing folder
            query_parts = [
                f"name = '{name}'",
                f"mimeType = '{FOLDER_MIME_TYPE}'",
                "trashed = false",
            ]

            if parent_folder_id:
                query_parts.append(f"'{parent_folder_id}' in parents")

            q = " and ".join(query_parts)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: service.files()
                .list(q=q, pageSize=1, fields="files(id,name,createdTime,parents,webViewLink)")
                .execute(),
            )

            files = result.get("files", [])

            if files:
                # Folder exists
                return FolderCreateResponse(
                    success=True,
                    folder=folder_info_from_api(files[0]),
                )

            # Create new folder
            return await self.create_folder(name, parent_folder_id)

        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            return FolderCreateResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error: {e}")
            return FolderCreateResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # Sharing Operations
    # -------------------------------------------------------------------------
    async def create_shareable_link(
        self,
        file_id: str,
        role: str = "reader",
    ) -> ShareableLinkResponse:
        """
        Create a shareable link for a file.

        Args:
            file_id: ID of the file to share.
            role: Permission role (reader, writer, commenter).

        Returns:
            ShareableLinkResponse with shareable link.
        """
        service = self._get_service()
        if service is None:
            return ShareableLinkResponse(
                success=False,
                error="Not authenticated with Google Drive",
                file_id=file_id,
            )

        try:
            loop = asyncio.get_event_loop()

            # Create permission for anyone with link
            permission = {"type": "anyone", "role": role}

            perm_result = await loop.run_in_executor(
                None,
                lambda: service.permissions()
                .create(fileId=file_id, body=permission, fields="id,role")
                .execute(),
            )

            # Get updated file info with webViewLink
            file = await loop.run_in_executor(
                None,
                lambda: service.files()
                .get(fileId=file_id, fields="id,webViewLink")
                .execute(),
            )

            logger.info(f"Created shareable link for file: {file_id}")

            from .models import ShareableLink

            return ShareableLinkResponse(
                success=True,
                file_id=file_id,
                web_view_link=file.get("webViewLink"),
                permission=ShareableLink(
                    link=file.get("webViewLink", ""),
                    permission_id=perm_result.get("id", ""),
                    role=perm_result.get("role", role),
                ),
            )

        except HttpError as e:
            logger.error(f"Drive API error creating shareable link: {e}")
            return ShareableLinkResponse(success=False, error=str(e), file_id=file_id)
        except Exception as e:
            logger.error(f"Error creating shareable link: {e}")
            return ShareableLinkResponse(success=False, error=str(e), file_id=file_id)

    # -------------------------------------------------------------------------
    # About/Status Operations
    # -------------------------------------------------------------------------
    async def get_about(self) -> AboutResponse:
        """
        Get information about the Drive account.

        Returns:
            AboutResponse with account info.
        """
        service = self._get_service()
        if service is None:
            return AboutResponse(
                success=False, error="Not authenticated with Google Drive"
            )

        try:
            loop = asyncio.get_event_loop()
            about = await loop.run_in_executor(
                None,
                lambda: service.about()
                .get(fields="user,storageQuota")
                .execute(),
            )

            user = about.get("user", {})
            quota = about.get("storageQuota", {})

            return AboutResponse(
                success=True,
                user_email=user.get("emailAddress"),
                user_name=user.get("displayName"),
                storage_quota=StorageQuota(
                    limit=int(quota.get("limit", 0)) if quota.get("limit") else None,
                    usage=int(quota.get("usage", 0)) if quota.get("usage") else None,
                    usage_in_drive=int(quota.get("usageInDrive", 0))
                    if quota.get("usageInDrive")
                    else None,
                    usage_in_drive_trash=int(quota.get("usageInDriveTrash", 0))
                    if quota.get("usageInDriveTrash")
                    else None,
                ),
            )

        except HttpError as e:
            logger.error(f"Drive API error getting about: {e}")
            return AboutResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error getting about: {e}")
            return AboutResponse(success=False, error=str(e))
