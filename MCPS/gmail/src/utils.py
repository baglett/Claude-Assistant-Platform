# =============================================================================
# Gmail MCP Server - Utilities
# =============================================================================
"""
Utility functions for the Gmail MCP server.

Provides helpers for email parsing, MIME handling, and data conversion.
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from .models import (
    AttachmentInfo,
    DraftInfo,
    EmailHeader,
    LabelInfo,
    LabelListVisibility,
    LabelType,
    MessageDetail,
    MessageListVisibility,
    MessageSummary,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Email Creation Utilities
# -----------------------------------------------------------------------------
def create_email_message(
    to: list[str],
    subject: str,
    body: str,
    from_address: Optional[str] = None,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
    thread_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
) -> dict:
    """
    Create an email message for sending via Gmail API.

    Args:
        to: List of recipient email addresses.
        subject: Email subject.
        body: Plain text body.
        from_address: From address (optional, uses authenticated user).
        cc: CC recipients.
        bcc: BCC recipients.
        html_body: HTML body (optional).
        reply_to: Reply-to address.
        thread_id: Thread ID for replies.
        in_reply_to: In-Reply-To header for threading.
        references: References header for threading.

    Returns:
        Dictionary with 'raw' key containing base64-encoded message.
    """
    if html_body:
        # Multipart message with both plain text and HTML
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))
    else:
        # Plain text only
        message = MIMEText(body, "plain", "utf-8")

    message["To"] = ", ".join(to)
    message["Subject"] = subject

    if from_address:
        message["From"] = from_address
    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)
    if reply_to:
        message["Reply-To"] = reply_to
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references

    # Encode to base64
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    result = {"raw": raw}
    if thread_id:
        result["threadId"] = thread_id

    return result


# -----------------------------------------------------------------------------
# Message Parsing Utilities
# -----------------------------------------------------------------------------
def extract_header_value(headers: list[dict], name: str) -> Optional[str]:
    """
    Extract a header value from a list of headers.

    Args:
        headers: List of header dictionaries.
        name: Header name to find (case-insensitive).

    Returns:
        Header value or None if not found.
    """
    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value")
    return None


def extract_addresses(header_value: Optional[str]) -> list[str]:
    """
    Extract email addresses from a header value.

    Args:
        header_value: Header value containing addresses.

    Returns:
        List of email addresses.
    """
    if not header_value:
        return []

    # Split by comma and strip whitespace
    addresses = [addr.strip() for addr in header_value.split(",")]
    return [addr for addr in addresses if addr]


def decode_body_part(part: dict) -> Optional[str]:
    """
    Decode a message body part.

    Args:
        part: Message part dictionary from Gmail API.

    Returns:
        Decoded string or None.
    """
    body = part.get("body", {})
    data = body.get("data")

    if not data:
        return None

    try:
        return base64.urlsafe_b64decode(data).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decode body part: {e}")
        return None


def extract_body_content(payload: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Extract plain text and HTML body from message payload.

    Args:
        payload: Message payload from Gmail API.

    Returns:
        Tuple of (plain_text, html_text).
    """
    plain_body = None
    html_body = None

    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        plain_body = decode_body_part(payload)
    elif mime_type == "text/html":
        html_body = decode_body_part(payload)
    elif mime_type.startswith("multipart/"):
        parts = payload.get("parts", [])
        for part in parts:
            part_mime = part.get("mimeType", "")
            if part_mime == "text/plain" and plain_body is None:
                plain_body = decode_body_part(part)
            elif part_mime == "text/html" and html_body is None:
                html_body = decode_body_part(part)
            elif part_mime.startswith("multipart/"):
                # Recursive extraction for nested multipart
                nested_plain, nested_html = extract_body_content(part)
                if plain_body is None:
                    plain_body = nested_plain
                if html_body is None:
                    html_body = nested_html

    return plain_body, html_body


def extract_attachments(payload: dict) -> list[AttachmentInfo]:
    """
    Extract attachment information from message payload.

    Args:
        payload: Message payload from Gmail API.

    Returns:
        List of AttachmentInfo objects.
    """
    attachments = []

    def process_parts(parts: list[dict]) -> None:
        for part in parts:
            filename = part.get("filename")
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")

            if filename and attachment_id:
                attachments.append(
                    AttachmentInfo(
                        attachment_id=attachment_id,
                        filename=filename,
                        mime_type=part.get("mimeType", "application/octet-stream"),
                        size=body.get("size", 0),
                    )
                )

            # Check nested parts
            nested_parts = part.get("parts", [])
            if nested_parts:
                process_parts(nested_parts)

    parts = payload.get("parts", [])
    process_parts(parts)

    # Also check top-level body for single-attachment messages
    body = payload.get("body", {})
    if body.get("attachmentId") and payload.get("filename"):
        attachments.append(
            AttachmentInfo(
                attachment_id=body["attachmentId"],
                filename=payload["filename"],
                mime_type=payload.get("mimeType", "application/octet-stream"),
                size=body.get("size", 0),
            )
        )

    return attachments


# -----------------------------------------------------------------------------
# Data Conversion Utilities
# -----------------------------------------------------------------------------
def convert_label_from_api(api_label: dict[str, Any]) -> LabelInfo:
    """
    Convert Gmail API label data to LabelInfo model.

    Args:
        api_label: Label data from Gmail API.

    Returns:
        LabelInfo model instance.
    """
    label_type = LabelType.SYSTEM if api_label.get("type") == "system" else LabelType.USER

    msg_visibility = None
    if api_label.get("messageListVisibility"):
        try:
            msg_visibility = MessageListVisibility(api_label["messageListVisibility"])
        except ValueError:
            pass

    label_visibility = None
    if api_label.get("labelListVisibility"):
        try:
            label_visibility = LabelListVisibility(api_label["labelListVisibility"])
        except ValueError:
            pass

    return LabelInfo(
        id=api_label["id"],
        name=api_label.get("name", api_label["id"]),
        label_type=label_type,
        message_list_visibility=msg_visibility,
        label_list_visibility=label_visibility,
        messages_total=api_label.get("messagesTotal"),
        messages_unread=api_label.get("messagesUnread"),
        threads_total=api_label.get("threadsTotal"),
        threads_unread=api_label.get("threadsUnread"),
    )


def convert_message_summary_from_api(api_message: dict[str, Any]) -> MessageSummary:
    """
    Convert Gmail API message data to MessageSummary model.

    Args:
        api_message: Message data from Gmail API.

    Returns:
        MessageSummary model instance.
    """
    return MessageSummary(
        id=api_message["id"],
        thread_id=api_message.get("threadId", ""),
        label_ids=api_message.get("labelIds", []),
        snippet=api_message.get("snippet"),
        history_id=api_message.get("historyId"),
        internal_date=api_message.get("internalDate"),
        size_estimate=api_message.get("sizeEstimate"),
    )


def convert_message_detail_from_api(api_message: dict[str, Any]) -> MessageDetail:
    """
    Convert Gmail API message data to MessageDetail model.

    Args:
        api_message: Full message data from Gmail API.

    Returns:
        MessageDetail model instance.
    """
    payload = api_message.get("payload", {})
    headers = payload.get("headers", [])

    # Extract header values
    subject = extract_header_value(headers, "Subject")
    from_address = extract_header_value(headers, "From")
    to_header = extract_header_value(headers, "To")
    cc_header = extract_header_value(headers, "Cc")
    date = extract_header_value(headers, "Date")

    # Extract body content
    plain_body, html_body = extract_body_content(payload)

    # Extract attachments
    attachments = extract_attachments(payload)

    # Convert all headers
    email_headers = [
        EmailHeader(name=h["name"], value=h["value"])
        for h in headers
        if "name" in h and "value" in h
    ]

    return MessageDetail(
        id=api_message["id"],
        thread_id=api_message.get("threadId", ""),
        label_ids=api_message.get("labelIds", []),
        snippet=api_message.get("snippet"),
        subject=subject,
        from_address=from_address,
        to_addresses=extract_addresses(to_header),
        cc_addresses=extract_addresses(cc_header),
        date=date,
        body_plain=plain_body,
        body_html=html_body,
        attachments=attachments,
        headers=email_headers,
    )


def convert_draft_from_api(api_draft: dict[str, Any]) -> DraftInfo:
    """
    Convert Gmail API draft data to DraftInfo model.

    Args:
        api_draft: Draft data from Gmail API.

    Returns:
        DraftInfo model instance.
    """
    message = None
    if api_draft.get("message"):
        message = convert_message_summary_from_api(api_draft["message"])

    return DraftInfo(
        id=api_draft["id"],
        message=message,
    )
