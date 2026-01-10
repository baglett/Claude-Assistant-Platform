"use client";

/**
 * ChatContainer component that holds the message list and input.
 *
 * Manages scrolling behavior and displays the conversation history.
 */

import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";

/**
 * Empty state component shown when no messages exist.
 */
function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
      <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center mb-6">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="w-10 h-10 text-primary"
        >
          <path
            fillRule="evenodd"
            d="M4.848 2.771A49.144 49.144 0 0 1 12 2.25c2.43 0 4.817.178 7.152.52 1.978.292 3.348 2.024 3.348 3.97v6.02c0 1.946-1.37 3.678-3.348 3.97a48.901 48.901 0 0 1-3.476.383.39.39 0 0 0-.297.17l-2.755 4.133a.75.75 0 0 1-1.248 0l-2.755-4.133a.39.39 0 0 0-.297-.17 48.9 48.9 0 0 1-3.476-.384c-1.978-.29-3.348-2.024-3.348-3.97V6.741c0-1.946 1.37-3.68 3.348-3.97ZM6.75 8.25a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 0 1.5h-9a.75.75 0 0 1-.75-.75Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H7.5Z"
            clipRule="evenodd"
          />
        </svg>
      </div>
      <h2 className="text-2xl font-bold mb-2">Claude Assistant</h2>
      <p className="text-base-content/70 max-w-md mb-6">
        Start a conversation with your personal AI assistant. I can help you
        manage tasks, answer questions, and more.
      </p>
      <div className="flex flex-wrap gap-2 justify-center">
        <SuggestionChip text="What can you help me with?" />
        <SuggestionChip text="Create a todo list for my project" />
        <SuggestionChip text="Help me organize my tasks" />
      </div>
    </div>
  );
}

/**
 * Suggestion chip component for quick-start prompts.
 */
function SuggestionChip({ text }: { text: string }) {
  const { sendMessage, isLoading } = useChatStore();

  return (
    <button
      onClick={() => sendMessage(text)}
      disabled={isLoading}
      className="btn btn-outline btn-sm"
    >
      {text}
    </button>
  );
}

/**
 * Error alert component.
 */
function ErrorAlert({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="alert alert-error mx-4 mb-4">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="stroke-current shrink-0 h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span>{message}</span>
      <button onClick={onDismiss} className="btn btn-sm btn-ghost">
        Dismiss
      </button>
    </div>
  );
}

/**
 * Main chat container component.
 *
 * Displays the message history with auto-scroll and the input component.
 */
export function ChatContainer() {
  const { messages, error, setError, clearMessages } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /**
   * Auto-scroll to bottom when new messages arrive.
   */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="navbar bg-base-200 border-b border-base-300 px-4">
        <div className="flex-1">
          <span className="text-xl font-bold">Claude Assistant</span>
        </div>
        <div className="flex-none gap-2">
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="btn btn-ghost btn-sm"
              title="Clear conversation"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path
                  fillRule="evenodd"
                  d="M16.5 4.478v.227a48.816 48.816 0 0 1 3.878.512.75.75 0 1 1-.256 1.478l-.209-.035-1.005 13.07a3 3 0 0 1-2.991 2.77H8.084a3 3 0 0 1-2.991-2.77L4.087 6.66l-.209.035a.75.75 0 0 1-.256-1.478A48.567 48.567 0 0 1 7.5 4.705v-.227c0-1.564 1.213-2.9 2.816-2.951a52.662 52.662 0 0 1 3.369 0c1.603.051 2.815 1.387 2.815 2.951Zm-6.136-1.452a51.196 51.196 0 0 1 3.273 0C14.39 3.05 15 3.684 15 4.478v.113a49.488 49.488 0 0 0-6 0v-.113c0-.794.609-1.428 1.364-1.452Zm-.355 5.945a.75.75 0 1 0-1.5.058l.347 9a.75.75 0 1 0 1.499-.058l-.346-9Zm5.48.058a.75.75 0 1 0-1.498-.058l-.347 9a.75.75 0 0 0 1.5.058l.345-9Z"
                  clipRule="evenodd"
                />
              </svg>
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Error display */}
      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <ChatInput />
    </div>
  );
}
