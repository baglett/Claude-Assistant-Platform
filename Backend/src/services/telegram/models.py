# =============================================================================
# Telegram Pydantic Models
# =============================================================================
"""
Pydantic models for Telegram Bot API data structures.

These models provide type-safe parsing and validation of incoming Telegram
updates and messages, as well as outgoing message structures.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# User and Chat Models
# -----------------------------------------------------------------------------
class TelegramUser(BaseModel):
    """
    Represents a Telegram user.

    Contains information about a user that can send messages to the bot.

    Attributes:
        id: Unique identifier for this user.
        is_bot: True if this user is a bot.
        first_name: User's first name.
        last_name: User's last name (optional).
        username: User's Telegram username (optional).
        language_code: IETF language tag of the user's language (optional).
    """

    id: int = Field(..., description="Unique identifier for this user")
    is_bot: bool = Field(default=False, description="True if this user is a bot")
    first_name: str = Field(..., description="User's first name")
    last_name: Optional[str] = Field(
        default=None, description="User's last name (optional)"
    )
    username: Optional[str] = Field(
        default=None, description="User's Telegram username (optional)"
    )
    language_code: Optional[str] = Field(
        default=None, description="IETF language tag of the user's language"
    )

    @property
    def full_name(self) -> str:
        """
        Get the user's full name.

        Returns:
            Full name combining first and last name.
        """
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def display_name(self) -> str:
        """
        Get a display-friendly name for the user.

        Returns:
            Username if available, otherwise full name.
        """
        if self.username:
            return f"@{self.username}"
        return self.full_name


class TelegramChat(BaseModel):
    """
    Represents a Telegram chat.

    Can be a private chat, group, supergroup, or channel.

    Attributes:
        id: Unique identifier for this chat.
        type: Type of chat (private, group, supergroup, channel).
        title: Title for groups, supergroups, and channels (optional).
        username: Username for private chats, supergroups, and channels (optional).
        first_name: First name of the other party in a private chat (optional).
        last_name: Last name of the other party in a private chat (optional).
    """

    id: int = Field(..., description="Unique identifier for this chat")
    type: str = Field(
        ..., description="Type of chat: private, group, supergroup, or channel"
    )
    title: Optional[str] = Field(
        default=None, description="Title for groups, supergroups, and channels"
    )
    username: Optional[str] = Field(
        default=None, description="Username for private chats and channels"
    )
    first_name: Optional[str] = Field(
        default=None, description="First name in private chat"
    )
    last_name: Optional[str] = Field(
        default=None, description="Last name in private chat"
    )

    @property
    def display_name(self) -> str:
        """
        Get a display-friendly name for the chat.

        Returns:
            Title for groups, or user info for private chats.
        """
        if self.title:
            return self.title
        if self.username:
            return f"@{self.username}"
        if self.first_name:
            if self.last_name:
                return f"{self.first_name} {self.last_name}"
            return self.first_name
        return str(self.id)


# -----------------------------------------------------------------------------
# Message Models
# -----------------------------------------------------------------------------
class TelegramMessage(BaseModel):
    """
    Represents a Telegram message.

    Contains the message content and metadata.

    Attributes:
        message_id: Unique message identifier within this chat.
        date: Unix timestamp when the message was sent.
        chat: Chat the message belongs to.
        from_user: Sender of the message (optional for channels).
        text: Text content of the message (optional).
        reply_to_message: Original message if this is a reply (optional).
    """

    message_id: int = Field(..., description="Unique message identifier in the chat")
    date: int = Field(..., description="Unix timestamp when the message was sent")
    chat: TelegramChat = Field(..., description="Chat the message belongs to")
    from_user: Optional[TelegramUser] = Field(
        default=None, alias="from", description="Sender of the message"
    )
    text: Optional[str] = Field(default=None, description="Text content of the message")
    reply_to_message: Optional["TelegramMessage"] = Field(
        default=None, description="Original message if this is a reply"
    )

    model_config = {"populate_by_name": True}

    @property
    def datetime(self) -> datetime:
        """
        Get the message timestamp as a datetime object.

        Returns:
            Datetime object representing when the message was sent.
        """
        return datetime.fromtimestamp(self.date)

    @property
    def has_text(self) -> bool:
        """
        Check if the message has text content.

        Returns:
            True if the message contains text.
        """
        return bool(self.text)

    @property
    def sender_id(self) -> Optional[int]:
        """
        Get the sender's user ID.

        Returns:
            User ID of the sender, or None for channel posts.
        """
        return self.from_user.id if self.from_user else None


# -----------------------------------------------------------------------------
# Update Models
# -----------------------------------------------------------------------------
class TelegramUpdate(BaseModel):
    """
    Represents an incoming update from Telegram.

    An update can contain a message, edited message, callback query, etc.
    For now, we focus on message updates.

    Attributes:
        update_id: Unique update identifier.
        message: New incoming message (optional).
        edited_message: Edited message (optional).
    """

    update_id: int = Field(..., description="Unique update identifier")
    message: Optional[TelegramMessage] = Field(
        default=None, description="New incoming message"
    )
    edited_message: Optional[TelegramMessage] = Field(
        default=None, description="Edited version of a message"
    )

    @property
    def effective_message(self) -> Optional[TelegramMessage]:
        """
        Get the effective message from this update.

        Returns the message or edited_message, whichever is present.

        Returns:
            The message object, or None if no message in this update.
        """
        return self.message or self.edited_message

    @property
    def has_message(self) -> bool:
        """
        Check if this update contains a message.

        Returns:
            True if the update has a message or edited_message.
        """
        return self.message is not None or self.edited_message is not None


class TelegramGetUpdatesResponse(BaseModel):
    """
    Response from the Telegram getUpdates API call.

    Attributes:
        ok: True if the request was successful.
        result: List of updates received.
        description: Error description if ok is False.
    """

    ok: bool = Field(..., description="True if the request was successful")
    result: list[TelegramUpdate] = Field(
        default_factory=list, description="List of updates received"
    )
    description: Optional[str] = Field(
        default=None, description="Error description if ok is False"
    )


# -----------------------------------------------------------------------------
# Outgoing Message Models
# -----------------------------------------------------------------------------
class SendMessageRequest(BaseModel):
    """
    Request payload for sending a message via Telegram API.

    Attributes:
        chat_id: Target chat ID to send the message to.
        text: Text of the message to be sent.
        parse_mode: Parse mode for formatting (HTML, Markdown, MarkdownV2).
        reply_to_message_id: ID of the message to reply to (optional).
        disable_notification: Send message silently (optional).
    """

    chat_id: int = Field(..., description="Target chat ID")
    text: str = Field(..., description="Text of the message to be sent")
    parse_mode: Optional[str] = Field(
        default=None, description="Parse mode: HTML, Markdown, or MarkdownV2"
    )
    reply_to_message_id: Optional[int] = Field(
        default=None, description="ID of the message to reply to"
    )
    disable_notification: bool = Field(
        default=False, description="Send message silently"
    )


class SendMessageResponse(BaseModel):
    """
    Response from the Telegram sendMessage API call.

    Attributes:
        ok: True if the message was sent successfully.
        result: The sent message object.
        description: Error description if ok is False.
    """

    ok: bool = Field(..., description="True if the request was successful")
    result: Optional[TelegramMessage] = Field(
        default=None, description="The sent message"
    )
    description: Optional[str] = Field(
        default=None, description="Error description if ok is False"
    )


# -----------------------------------------------------------------------------
# Internal Models for Message Handling
# -----------------------------------------------------------------------------
class IncomingTelegramMessage(BaseModel):
    """
    Internal representation of an incoming Telegram message for processing.

    Simplifies the Telegram data structure for internal use.

    Attributes:
        update_id: The Telegram update ID.
        message_id: The message ID within the chat.
        chat_id: The chat ID where the message was sent.
        user_id: The sender's user ID.
        username: The sender's username (optional).
        user_display_name: Display name for the user.
        text: The message text content.
        timestamp: Unix timestamp of the message.
        is_reply: Whether this message is a reply to another message.
        reply_to_message_id: ID of the message being replied to (optional).
    """

    update_id: int = Field(..., description="Telegram update ID")
    message_id: int = Field(..., description="Message ID within the chat")
    chat_id: int = Field(..., description="Chat ID where the message was sent")
    user_id: int = Field(..., description="Sender's user ID")
    username: Optional[str] = Field(default=None, description="Sender's username")
    user_display_name: str = Field(..., description="Display name for the user")
    text: str = Field(..., description="Message text content")
    timestamp: int = Field(..., description="Unix timestamp of the message")
    is_reply: bool = Field(default=False, description="Whether this is a reply")
    reply_to_message_id: Optional[int] = Field(
        default=None, description="ID of message being replied to"
    )

    @classmethod
    def from_telegram_update(
        cls, update: TelegramUpdate
    ) -> Optional["IncomingTelegramMessage"]:
        """
        Create an IncomingTelegramMessage from a TelegramUpdate.

        Args:
            update: The Telegram update to convert.

        Returns:
            IncomingTelegramMessage if the update contains a valid text message,
            None otherwise.
        """
        message = update.effective_message

        # Skip updates without messages or text
        if not message or not message.text:
            return None

        # Skip messages without a sender
        if not message.from_user:
            return None

        return cls(
            update_id=update.update_id,
            message_id=message.message_id,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            username=message.from_user.username,
            user_display_name=message.from_user.display_name,
            text=message.text,
            timestamp=message.date,
            is_reply=message.reply_to_message is not None,
            reply_to_message_id=(
                message.reply_to_message.message_id
                if message.reply_to_message
                else None
            ),
        )

    @property
    def conversation_id(self) -> str:
        """
        Generate a conversation ID for the orchestrator.

        Uses the chat_id to maintain conversation context per chat.

        Returns:
            Conversation ID string in format 'telegram_{chat_id}'.
        """
        return f"telegram_{self.chat_id}"
