# =============================================================================
# Gmail MCP Server - Pydantic Models
# =============================================================================
"""
Pydantic models for Gmail API data structures.

Provides type-safe models for messages, labels, drafts, and API responses.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------
class LabelType(str, Enum):
    """Label type values."""

    SYSTEM = "system"
    USER = "user"


class MessageListVisibility(str, Enum):
    """Label visibility in message list."""

    SHOW = "show"
    HIDE = "hide"


class LabelListVisibility(str, Enum):
    """Label visibility in label list."""

    LABEL_SHOW = "labelShow"
    LABEL_SHOW_IF_UNREAD = "labelShowIfUnread"
    LABEL_HIDE = "labelHide"


# -----------------------------------------------------------------------------
# Header Models
# -----------------------------------------------------------------------------
class EmailHeader(BaseModel):
    """
    Email header information.

    Attributes:
        name: Header name (e.g., "From", "To", "Subject").
        value: Header value.
    """

    name: str = Field(..., description="Header name")
    value: str = Field(..., description="Header value")


# -----------------------------------------------------------------------------
# Attachment Models
# -----------------------------------------------------------------------------
class AttachmentInfo(BaseModel):
    """
    Information about an email attachment.

    Attributes:
        attachment_id: The attachment ID.
        filename: The attachment filename.
        mime_type: MIME type of the attachment.
        size: Size in bytes.
    """

    attachment_id: str = Field(..., description="Attachment identifier")
    filename: str = Field(..., description="Filename")
    mime_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="Size in bytes")


# -----------------------------------------------------------------------------
# Label Models
# -----------------------------------------------------------------------------
class LabelInfo(BaseModel):
    """
    Information about a Gmail label.

    Attributes:
        id: Label identifier.
        name: Label name.
        label_type: Whether system or user label.
        message_list_visibility: Visibility in message list.
        label_list_visibility: Visibility in label list.
        messages_total: Total messages with this label.
        messages_unread: Unread messages with this label.
        threads_total: Total threads with this label.
        threads_unread: Unread threads with this label.
    """

    id: str = Field(..., description="Label identifier")
    name: str = Field(..., description="Label name")
    label_type: LabelType = Field(LabelType.USER, description="Label type")
    message_list_visibility: Optional[MessageListVisibility] = Field(
        None, description="Visibility in message list"
    )
    label_list_visibility: Optional[LabelListVisibility] = Field(
        None, description="Visibility in label list"
    )
    messages_total: Optional[int] = Field(None, description="Total messages")
    messages_unread: Optional[int] = Field(None, description="Unread messages")
    threads_total: Optional[int] = Field(None, description="Total threads")
    threads_unread: Optional[int] = Field(None, description="Unread threads")


class LabelListResponse(BaseModel):
    """Response for list labels operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    labels: list[LabelInfo] = Field(default_factory=list, description="List of labels")
    error: Optional[str] = Field(None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Message Models
# -----------------------------------------------------------------------------
class MessageSummary(BaseModel):
    """
    Summary information about a message.

    Attributes:
        id: Message identifier.
        thread_id: Thread identifier.
        label_ids: List of label IDs.
        snippet: Short snippet of the message.
        history_id: History ID for sync.
        internal_date: Internal timestamp (epoch ms).
        size_estimate: Estimated size in bytes.
    """

    id: str = Field(..., description="Message identifier")
    thread_id: str = Field(..., description="Thread identifier")
    label_ids: list[str] = Field(default_factory=list, description="Label IDs")
    snippet: Optional[str] = Field(None, description="Message snippet")
    history_id: Optional[str] = Field(None, description="History ID")
    internal_date: Optional[str] = Field(None, description="Internal date (epoch ms)")
    size_estimate: Optional[int] = Field(None, description="Estimated size")


class MessageDetail(BaseModel):
    """
    Detailed information about a message.

    Attributes:
        id: Message identifier.
        thread_id: Thread identifier.
        label_ids: List of label IDs.
        snippet: Short snippet of the message.
        subject: Email subject.
        from_address: Sender email address.
        to_addresses: Recipient email addresses.
        cc_addresses: CC email addresses.
        date: Email date.
        body_plain: Plain text body.
        body_html: HTML body.
        attachments: List of attachments.
        headers: All message headers.
    """

    id: str = Field(..., description="Message identifier")
    thread_id: str = Field(..., description="Thread identifier")
    label_ids: list[str] = Field(default_factory=list, description="Label IDs")
    snippet: Optional[str] = Field(None, description="Message snippet")
    subject: Optional[str] = Field(None, description="Email subject")
    from_address: Optional[str] = Field(None, description="Sender address")
    to_addresses: list[str] = Field(default_factory=list, description="To addresses")
    cc_addresses: list[str] = Field(default_factory=list, description="CC addresses")
    date: Optional[str] = Field(None, description="Email date")
    body_plain: Optional[str] = Field(None, description="Plain text body")
    body_html: Optional[str] = Field(None, description="HTML body")
    attachments: list[AttachmentInfo] = Field(
        default_factory=list, description="Attachments"
    )
    headers: list[EmailHeader] = Field(default_factory=list, description="All headers")


class MessageListResponse(BaseModel):
    """Response for list messages operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    messages: list[MessageSummary] = Field(
        default_factory=list, description="List of messages"
    )
    next_page_token: Optional[str] = Field(None, description="Token for next page")
    result_size_estimate: Optional[int] = Field(None, description="Estimated results")
    error: Optional[str] = Field(None, description="Error message if failed")


class MessageResponse(BaseModel):
    """Response for single message operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: Optional[MessageDetail] = Field(None, description="Message details")
    error: Optional[str] = Field(None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Draft Models
# -----------------------------------------------------------------------------
class DraftInfo(BaseModel):
    """
    Information about a draft.

    Attributes:
        id: Draft identifier.
        message: The draft message.
    """

    id: str = Field(..., description="Draft identifier")
    message: Optional[MessageSummary] = Field(None, description="Draft message")


class DraftResponse(BaseModel):
    """Response for draft operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    draft: Optional[DraftInfo] = Field(None, description="Draft details")
    error: Optional[str] = Field(None, description="Error message if failed")


class DraftListResponse(BaseModel):
    """Response for list drafts operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    drafts: list[DraftInfo] = Field(default_factory=list, description="List of drafts")
    next_page_token: Optional[str] = Field(None, description="Token for next page")
    error: Optional[str] = Field(None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Send Email Models
# -----------------------------------------------------------------------------
class SendEmailRequest(BaseModel):
    """Request model for sending an email."""

    to: list[str] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Plain text body")
    cc: Optional[list[str]] = Field(None, description="CC recipients")
    bcc: Optional[list[str]] = Field(None, description="BCC recipients")
    html_body: Optional[str] = Field(None, description="HTML body")
    reply_to: Optional[str] = Field(None, description="Reply-to address")
    thread_id: Optional[str] = Field(None, description="Thread ID for replies")


class SendEmailResponse(BaseModel):
    """Response for send email operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message_id: Optional[str] = Field(None, description="Sent message ID")
    thread_id: Optional[str] = Field(None, description="Thread ID")
    label_ids: list[str] = Field(default_factory=list, description="Label IDs")
    error: Optional[str] = Field(None, description="Error message if failed")


# -----------------------------------------------------------------------------
# Generic Response Models
# -----------------------------------------------------------------------------
class OperationResponse(BaseModel):
    """Generic response for operations without specific return data."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: Optional[str] = Field(None, description="Success or status message")
    error: Optional[str] = Field(None, description="Error message if failed")
