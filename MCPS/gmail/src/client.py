# =============================================================================
# Gmail MCP Server - Gmail API Client
# =============================================================================
"""
Gmail API client wrapper.

Provides a high-level interface for Gmail operations with proper
error handling and data conversion.
"""

import logging
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth import GmailAuthManager
from .models import (
    DraftInfo,
    DraftListResponse,
    DraftResponse,
    LabelInfo,
    LabelListResponse,
    MessageDetail,
    MessageListResponse,
    MessageResponse,
    OperationResponse,
    SendEmailResponse,
)
from .utils import (
    convert_draft_from_api,
    convert_label_from_api,
    convert_message_detail_from_api,
    convert_message_summary_from_api,
    create_email_message,
)

logger = logging.getLogger(__name__)


class GmailClient:
    """
    High-level client for Gmail API operations.

    Handles authentication, API calls, and data conversion.

    Attributes:
        auth_manager: OAuth authentication manager.
    """

    def __init__(self, auth_manager: GmailAuthManager) -> None:
        """
        Initialize the Gmail client.

        Args:
            auth_manager: Configured GmailAuthManager instance.
        """
        self.auth_manager = auth_manager
        self._service = None

    def _get_service(self):
        """
        Get or create the Gmail API service.

        Returns:
            Gmail API service object.

        Raises:
            RuntimeError: If not authenticated.
        """
        if self._service is not None:
            return self._service

        creds = self.auth_manager.get_credentials()
        if creds is None:
            raise RuntimeError(
                "Not authenticated. Please run authentication flow first."
            )

        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self.auth_manager.is_authenticated

    async def authenticate(self) -> OperationResponse:
        """
        Run the OAuth authentication flow.

        Returns:
            OperationResponse indicating success or failure.
        """
        try:
            self.auth_manager.authenticate()
            self._service = None  # Reset service to use new credentials
            return OperationResponse(
                success=True,
                message="Authentication successful",
            )
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return OperationResponse(
                success=False,
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Label Operations
    # -------------------------------------------------------------------------
    async def list_labels(self) -> LabelListResponse:
        """
        List all labels in the user's mailbox.

        Returns:
            LabelListResponse with list of labels.
        """
        try:
            service = self._get_service()
            result = service.users().labels().list(userId="me").execute()

            labels = [
                convert_label_from_api(label) for label in result.get("labels", [])
            ]

            return LabelListResponse(
                success=True,
                labels=labels,
            )

        except HttpError as e:
            logger.error(f"HTTP error listing labels: {e}")
            return LabelListResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error listing labels: {e}")
            return LabelListResponse(
                success=False,
                error=str(e),
            )

    async def create_label(self, name: str) -> OperationResponse:
        """
        Create a new label.

        Args:
            name: Name for the new label.

        Returns:
            OperationResponse with result.
        """
        try:
            service = self._get_service()
            label_body = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }

            result = (
                service.users().labels().create(userId="me", body=label_body).execute()
            )

            return OperationResponse(
                success=True,
                message=f"Label '{name}' created with ID: {result['id']}",
            )

        except HttpError as e:
            logger.error(f"HTTP error creating label: {e}")
            return OperationResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error creating label: {e}")
            return OperationResponse(
                success=False,
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Message Operations
    # -------------------------------------------------------------------------
    async def list_messages(
        self,
        query: Optional[str] = None,
        max_results: int = 10,
        label_ids: Optional[list[str]] = None,
        include_spam_trash: bool = False,
        page_token: Optional[str] = None,
    ) -> MessageListResponse:
        """
        List messages in the user's mailbox.

        Args:
            query: Gmail search query.
            max_results: Maximum number of messages to return.
            label_ids: Filter by label IDs.
            include_spam_trash: Include spam and trash.
            page_token: Token for pagination.

        Returns:
            MessageListResponse with list of messages.
        """
        try:
            service = self._get_service()

            params = {
                "userId": "me",
                "maxResults": max_results,
                "includeSpamTrash": include_spam_trash,
            }

            if query:
                params["q"] = query
            if label_ids:
                params["labelIds"] = label_ids
            if page_token:
                params["pageToken"] = page_token

            result = service.users().messages().list(**params).execute()

            messages = []
            for msg in result.get("messages", []):
                # Get basic info for each message
                msg_detail = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="metadata")
                    .execute()
                )
                messages.append(convert_message_summary_from_api(msg_detail))

            return MessageListResponse(
                success=True,
                messages=messages,
                next_page_token=result.get("nextPageToken"),
                result_size_estimate=result.get("resultSizeEstimate"),
            )

        except HttpError as e:
            logger.error(f"HTTP error listing messages: {e}")
            return MessageListResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error listing messages: {e}")
            return MessageListResponse(
                success=False,
                error=str(e),
            )

    async def get_message(
        self,
        message_id: str,
        format: str = "full",
    ) -> MessageResponse:
        """
        Get a specific message by ID.

        Args:
            message_id: The message ID.
            format: Response format (full, metadata, minimal, raw).

        Returns:
            MessageResponse with message details.
        """
        try:
            service = self._get_service()

            result = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format=format)
                .execute()
            )

            message = convert_message_detail_from_api(result)

            return MessageResponse(
                success=True,
                message=message,
            )

        except HttpError as e:
            logger.error(f"HTTP error getting message: {e}")
            return MessageResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return MessageResponse(
                success=False,
                error=str(e),
            )

    async def search_messages(
        self,
        query: str,
        max_results: int = 25,
    ) -> MessageListResponse:
        """
        Search messages using Gmail query syntax.

        Args:
            query: Gmail search query string.
            max_results: Maximum results to return.

        Returns:
            MessageListResponse with matching messages.
        """
        return await self.list_messages(query=query, max_results=max_results)

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        html_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> SendEmailResponse:
        """
        Send a new email.

        Args:
            to: List of recipient email addresses.
            subject: Email subject.
            body: Plain text body.
            cc: CC recipients.
            bcc: BCC recipients.
            html_body: HTML body (optional).
            reply_to: Reply-to address.
            thread_id: Thread ID for replies.

        Returns:
            SendEmailResponse with sent message details.
        """
        try:
            service = self._get_service()

            message = create_email_message(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                html_body=html_body,
                reply_to=reply_to,
                thread_id=thread_id,
            )

            result = (
                service.users().messages().send(userId="me", body=message).execute()
            )

            return SendEmailResponse(
                success=True,
                message_id=result.get("id"),
                thread_id=result.get("threadId"),
                label_ids=result.get("labelIds", []),
            )

        except HttpError as e:
            logger.error(f"HTTP error sending email: {e}")
            return SendEmailResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return SendEmailResponse(
                success=False,
                error=str(e),
            )

    async def trash_message(self, message_id: str) -> OperationResponse:
        """
        Move a message to trash.

        Args:
            message_id: The message ID to trash.

        Returns:
            OperationResponse with result.
        """
        try:
            service = self._get_service()

            service.users().messages().trash(userId="me", id=message_id).execute()

            return OperationResponse(
                success=True,
                message=f"Message {message_id} moved to trash",
            )

        except HttpError as e:
            logger.error(f"HTTP error trashing message: {e}")
            return OperationResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error trashing message: {e}")
            return OperationResponse(
                success=False,
                error=str(e),
            )

    async def untrash_message(self, message_id: str) -> OperationResponse:
        """
        Remove a message from trash.

        Args:
            message_id: The message ID to untrash.

        Returns:
            OperationResponse with result.
        """
        try:
            service = self._get_service()

            service.users().messages().untrash(userId="me", id=message_id).execute()

            return OperationResponse(
                success=True,
                message=f"Message {message_id} removed from trash",
            )

        except HttpError as e:
            logger.error(f"HTTP error untrashing message: {e}")
            return OperationResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error untrashing message: {e}")
            return OperationResponse(
                success=False,
                error=str(e),
            )

    async def modify_message_labels(
        self,
        message_id: str,
        add_label_ids: Optional[list[str]] = None,
        remove_label_ids: Optional[list[str]] = None,
    ) -> OperationResponse:
        """
        Modify labels on a message.

        Args:
            message_id: The message ID.
            add_label_ids: Labels to add.
            remove_label_ids: Labels to remove.

        Returns:
            OperationResponse with result.
        """
        try:
            service = self._get_service()

            body = {}
            if add_label_ids:
                body["addLabelIds"] = add_label_ids
            if remove_label_ids:
                body["removeLabelIds"] = remove_label_ids

            service.users().messages().modify(
                userId="me", id=message_id, body=body
            ).execute()

            return OperationResponse(
                success=True,
                message=f"Labels modified on message {message_id}",
            )

        except HttpError as e:
            logger.error(f"HTTP error modifying labels: {e}")
            return OperationResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error modifying labels: {e}")
            return OperationResponse(
                success=False,
                error=str(e),
            )

    async def mark_as_read(self, message_id: str) -> OperationResponse:
        """
        Mark a message as read.

        Args:
            message_id: The message ID.

        Returns:
            OperationResponse with result.
        """
        return await self.modify_message_labels(
            message_id=message_id,
            remove_label_ids=["UNREAD"],
        )

    async def mark_as_unread(self, message_id: str) -> OperationResponse:
        """
        Mark a message as unread.

        Args:
            message_id: The message ID.

        Returns:
            OperationResponse with result.
        """
        return await self.modify_message_labels(
            message_id=message_id,
            add_label_ids=["UNREAD"],
        )

    async def archive_message(self, message_id: str) -> OperationResponse:
        """
        Archive a message (remove from INBOX).

        Args:
            message_id: The message ID.

        Returns:
            OperationResponse with result.
        """
        return await self.modify_message_labels(
            message_id=message_id,
            remove_label_ids=["INBOX"],
        )

    # -------------------------------------------------------------------------
    # Draft Operations
    # -------------------------------------------------------------------------
    async def create_draft(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
        html_body: Optional[str] = None,
    ) -> DraftResponse:
        """
        Create a draft email.

        Args:
            to: List of recipient email addresses.
            subject: Email subject.
            body: Plain text body.
            cc: CC recipients.
            html_body: HTML body (optional).

        Returns:
            DraftResponse with draft details.
        """
        try:
            service = self._get_service()

            message = create_email_message(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                html_body=html_body,
            )

            draft_body = {"message": message}

            result = (
                service.users().drafts().create(userId="me", body=draft_body).execute()
            )

            draft = convert_draft_from_api(result)

            return DraftResponse(
                success=True,
                draft=draft,
            )

        except HttpError as e:
            logger.error(f"HTTP error creating draft: {e}")
            return DraftResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            return DraftResponse(
                success=False,
                error=str(e),
            )

    async def send_draft(self, draft_id: str) -> SendEmailResponse:
        """
        Send an existing draft.

        Args:
            draft_id: The draft ID to send.

        Returns:
            SendEmailResponse with sent message details.
        """
        try:
            service = self._get_service()

            result = (
                service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )

            return SendEmailResponse(
                success=True,
                message_id=result.get("id"),
                thread_id=result.get("threadId"),
                label_ids=result.get("labelIds", []),
            )

        except HttpError as e:
            logger.error(f"HTTP error sending draft: {e}")
            return SendEmailResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error sending draft: {e}")
            return SendEmailResponse(
                success=False,
                error=str(e),
            )

    async def list_drafts(
        self,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> DraftListResponse:
        """
        List drafts in the user's mailbox.

        Args:
            max_results: Maximum number of drafts to return.
            page_token: Token for pagination.

        Returns:
            DraftListResponse with list of drafts.
        """
        try:
            service = self._get_service()

            params = {
                "userId": "me",
                "maxResults": max_results,
            }
            if page_token:
                params["pageToken"] = page_token

            result = service.users().drafts().list(**params).execute()

            drafts = [
                convert_draft_from_api(draft) for draft in result.get("drafts", [])
            ]

            return DraftListResponse(
                success=True,
                drafts=drafts,
                next_page_token=result.get("nextPageToken"),
            )

        except HttpError as e:
            logger.error(f"HTTP error listing drafts: {e}")
            return DraftListResponse(
                success=False,
                error=f"Gmail API error: {e.reason}",
            )
        except Exception as e:
            logger.error(f"Error listing drafts: {e}")
            return DraftListResponse(
                success=False,
                error=str(e),
            )
