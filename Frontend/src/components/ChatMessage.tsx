"use client";

/**
 * ChatMessage component for displaying individual messages in the chat.
 *
 * Renders user and assistant messages with appropriate styling and animations.
 */

import { ChatMessage as ChatMessageType } from "@/stores/chatStore";

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
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1">
      <span className="typing-dot w-2 h-2 bg-base-content/50 rounded-full" />
      <span className="typing-dot w-2 h-2 bg-base-content/50 rounded-full" />
      <span className="typing-dot w-2 h-2 bg-base-content/50 rounded-full" />
    </div>
  );
}

/**
 * Format message content with basic markdown-like styling.
 *
 * @param content - Raw message content
 * @returns Formatted JSX content
 */
function formatContent(content: string): React.ReactNode {
  // Split by code blocks first
  const parts = content.split(/(```[\s\S]*?```)/g);

  return parts.map((part, index) => {
    // Handle code blocks
    if (part.startsWith("```") && part.endsWith("```")) {
      const codeContent = part.slice(3, -3);
      const firstNewline = codeContent.indexOf("\n");
      const language = firstNewline > 0 ? codeContent.slice(0, firstNewline).trim() : "";
      const code = firstNewline > 0 ? codeContent.slice(firstNewline + 1) : codeContent;

      return (
        <pre key={index} className="bg-base-300 p-4 rounded-lg overflow-x-auto my-2 text-sm">
          {language && (
            <div className="text-xs text-base-content/50 mb-2">{language}</div>
          )}
          <code>{code}</code>
        </pre>
      );
    }

    // Handle inline code
    const inlineParts = part.split(/(`[^`]+`)/g);
    return (
      <span key={index}>
        {inlineParts.map((inlinePart, i) => {
          if (inlinePart.startsWith("`") && inlinePart.endsWith("`")) {
            return (
              <code
                key={i}
                className="bg-base-300 px-1.5 py-0.5 rounded text-sm font-mono"
              >
                {inlinePart.slice(1, -1)}
              </code>
            );
          }
          // Handle line breaks
          return inlinePart.split("\n").map((line, j, arr) => (
            <span key={`${i}-${j}`}>
              {line}
              {j < arr.length - 1 && <br />}
            </span>
          ));
        })}
      </span>
    );
  });
}

/**
 * ChatMessage component displaying a single message in the conversation.
 *
 * @param props - Component props containing the message to display
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isStreaming = message.isStreaming && !message.content;

  return (
    <div
      className={`chat ${isUser ? "chat-end" : "chat-start"} animate-fade-in-up`}
    >
      {/* Avatar */}
      <div className="chat-image avatar placeholder">
        <div
          className={`w-10 rounded-full ${
            isUser ? "bg-primary" : "bg-secondary"
          }`}
        >
          <span className="text-lg">
            {isUser ? "U" : "C"}
          </span>
        </div>
      </div>

      {/* Message header */}
      <div className="chat-header opacity-70 text-xs mb-1">
        {isUser ? "You" : "Claude"}
        <time className="ml-2">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </time>
      </div>

      {/* Message bubble */}
      <div
        className={`chat-bubble ${
          isUser
            ? "chat-bubble-primary"
            : "chat-bubble-secondary"
        } max-w-[85%] prose-chat`}
      >
        {isStreaming ? <TypingIndicator /> : formatContent(message.content)}
      </div>
    </div>
  );
}
