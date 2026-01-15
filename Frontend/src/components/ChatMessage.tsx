"use client";

/**
 * ChatMessage component for displaying individual messages in the chat.
 *
 * Renders user and assistant messages with appropriate styling, markdown
 * support, and action buttons (copy, retry).
 */

import { useCallback, useState } from "react";
import { ChatMessage as ChatMessageType, useChatStore } from "@/stores/chatStore";
import { MarkdownContent } from "./MarkdownContent";

/**
 * Props for the ChatMessage component.
 */
interface ChatMessageProps {
  /** The message to display */
  message: ChatMessageType;
}

/**
 * Typing indicator component shown while assistant is generating a response.
 */
function TypingIndicator(): JSX.Element {
  return (
    <div className="flex items-center gap-1">
      <span className="typing-dot w-2 h-2 bg-base-content/50 rounded-full" />
      <span className="typing-dot w-2 h-2 bg-base-content/50 rounded-full" />
      <span className="typing-dot w-2 h-2 bg-base-content/50 rounded-full" />
    </div>
  );
}

/**
 * Copy icon SVG component.
 */
function CopyIcon(): JSX.Element {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="w-4 h-4"
    >
      <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
      <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
    </svg>
  );
}

/**
 * Check icon SVG component.
 */
function CheckIcon(): JSX.Element {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="w-4 h-4 text-success"
    >
      <path
        fillRule="evenodd"
        d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/**
 * Retry icon SVG component.
 */
function RetryIcon(): JSX.Element {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="w-4 h-4"
    >
      <path
        fillRule="evenodd"
        d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm-1.561-5.848a5.5 5.5 0 00-9.201 2.466.75.75 0 001.449.39 4.001 4.001 0 016.887-1.79l.31.31H10.77a.75.75 0 000 1.5h4.243a.75.75 0 00.75-.75V3.46a.75.75 0 00-1.5 0v2.424l-.312-.31z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/**
 * Message action buttons (copy, retry).
 */
interface MessageActionsProps {
  /** Message content to copy */
  content: string;
  /** Whether this is a user message (shows retry button) */
  isUser: boolean;
  /** Callback to retry sending the message */
  onRetry?: () => void;
}

/**
 * Action buttons for messages (copy, retry).
 */
function MessageActions({
  content,
  isUser,
  onRetry,
}: MessageActionsProps): JSX.Element {
  const [copied, setCopied] = useState(false);

  /**
   * Handle copy to clipboard.
   */
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [content]);

  return (
    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      {/* Copy button */}
      <button
        onClick={handleCopy}
        className="btn btn-ghost btn-xs"
        title={copied ? "Copied!" : "Copy message"}
        aria-label={copied ? "Copied!" : "Copy message"}
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </button>

      {/* Retry button (only for user messages) */}
      {isUser && onRetry && (
        <button
          onClick={onRetry}
          className="btn btn-ghost btn-xs"
          title="Retry message"
          aria-label="Retry message"
        >
          <RetryIcon />
        </button>
      )}
    </div>
  );
}

/**
 * ChatMessage component displaying a single message in the conversation.
 *
 * Features:
 * - Markdown rendering with syntax highlighting
 * - Copy to clipboard button
 * - Retry button for user messages
 * - Typing indicator during streaming
 *
 * @example
 * <ChatMessage message={{ id: "1", role: "user", content: "Hello", timestamp: new Date() }} />
 */
export function ChatMessage({ message }: ChatMessageProps): JSX.Element {
  const isUser = message.role === "user";
  const isStreaming = message.isStreaming && !message.content;
  const sendMessage = useChatStore((state) => state.sendMessage);
  const isLoading = useChatStore((state) => state.isLoading);

  /**
   * Handle retry - resend the user's message.
   */
  const handleRetry = useCallback(() => {
    if (!isLoading && message.content) {
      sendMessage(message.content);
    }
  }, [isLoading, message.content, sendMessage]);

  return (
    <div
      className={`chat ${isUser ? "chat-end" : "chat-start"} animate-fade-in-up group`}
    >
      {/* Avatar */}
      <div className="chat-image avatar placeholder">
        <div
          className={`w-10 rounded-full ${
            isUser ? "bg-primary" : "bg-secondary"
          }`}
        >
          <span className="text-lg">{isUser ? "U" : "C"}</span>
        </div>
      </div>

      {/* Message header with actions */}
      <div className="chat-header opacity-70 text-xs mb-1 flex items-center gap-2">
        <span>
          {isUser ? "You" : "Claude"}
          <time className="ml-2">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </time>
        </span>
        {/* Action buttons appear on hover */}
        {!isStreaming && message.content && (
          <MessageActions
            content={message.content}
            isUser={isUser}
            onRetry={isUser ? handleRetry : undefined}
          />
        )}
      </div>

      {/* Message bubble */}
      <div
        className={`chat-bubble ${
          isUser ? "chat-bubble-primary" : "chat-bubble-secondary"
        } max-w-[85%]`}
      >
        {isStreaming ? (
          <TypingIndicator />
        ) : isUser ? (
          // User messages: plain text with line breaks
          <span className="whitespace-pre-wrap">{message.content}</span>
        ) : (
          // Assistant messages: full markdown rendering
          <MarkdownContent content={message.content} />
        )}
      </div>
    </div>
  );
}
