"use client";

/**
 * ChatInput component for composing and sending messages.
 *
 * Provides a textarea input with send button and keyboard shortcuts.
 */

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { useChatStore } from "@/stores/chatStore";

/**
 * ChatInput component for message composition.
 *
 * Features:
 * - Auto-resizing textarea
 * - Enter to send (Shift+Enter for new line)
 * - Disabled state while loading
 */
export function ChatInput() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage, isLoading } = useChatStore();

  /**
   * Auto-resize textarea based on content.
   */
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  /**
   * Handle form submission.
   */
  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const message = input.trim();
    setInput("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    await sendMessage(message);
  };

  /**
   * Handle keyboard events for send shortcut.
   */
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-base-300 bg-base-200 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex gap-3 items-end">
          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
              className="textarea textarea-bordered w-full resize-none min-h-[52px] max-h-[200px] pr-4 bg-base-100"
              disabled={isLoading}
              rows={1}
            />
          </div>

          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className="btn btn-primary btn-square"
            aria-label="Send message"
          >
            {isLoading ? (
              <span className="loading loading-spinner loading-sm" />
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
              </svg>
            )}
          </button>
        </div>

        {/* Helper text */}
        <div className="text-xs text-base-content/50 mt-2 text-center">
          Press <kbd className="kbd kbd-xs">Enter</kbd> to send,{" "}
          <kbd className="kbd kbd-xs">Shift</kbd> +{" "}
          <kbd className="kbd kbd-xs">Enter</kbd> for new line
        </div>
      </div>
    </div>
  );
}
