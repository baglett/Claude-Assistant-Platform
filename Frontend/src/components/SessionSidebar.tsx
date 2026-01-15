"use client";

/**
 * SessionSidebar component for displaying conversation history.
 *
 * Shows a list of past sessions with the ability to create new chats,
 * switch between sessions, and delete old conversations.
 */

import { useCallback, useEffect } from "react";

import { useChatStore } from "@/stores/chatStore";
import { SessionItem } from "./SessionItem";

/**
 * Props for the SessionSidebar component.
 */
interface SessionSidebarProps {
  /** Whether the sidebar is collapsed (for mobile) */
  isCollapsed?: boolean;
  /** Callback when sidebar should close (mobile) */
  onClose?: () => void;
}

/**
 * Sidebar component for session history navigation.
 *
 * Features:
 * - New Chat button at top
 * - List of past sessions with title + timestamp
 * - Active session highlighting
 * - Delete session functionality
 *
 * @example
 * <SessionSidebar />
 */
export function SessionSidebar({
  isCollapsed = false,
  onClose,
}: SessionSidebarProps): JSX.Element {
  // Store state
  const sessions = useChatStore((state) => state.sessions);
  const sessionsLoading = useChatStore((state) => state.sessionsLoading);
  const conversationId = useChatStore((state) => state.conversationId);

  // Store actions
  const fetchSessions = useChatStore((state) => state.fetchSessions);
  const loadSession = useChatStore((state) => state.loadSession);
  const deleteSession = useChatStore((state) => state.deleteSession);
  const startNewChat = useChatStore((state) => state.startNewChat);

  /**
   * Fetch sessions on mount.
   */
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  /**
   * Handle new chat button click.
   */
  const handleNewChat = useCallback(() => {
    startNewChat();
    onClose?.();
  }, [startNewChat, onClose]);

  /**
   * Handle session click.
   */
  const handleSessionClick = useCallback(
    (sessionId: string) => {
      loadSession(sessionId);
      onClose?.();
    },
    [loadSession, onClose]
  );

  /**
   * Handle session delete.
   */
  const handleSessionDelete = useCallback(
    (sessionId: string) => {
      deleteSession(sessionId);
    },
    [deleteSession]
  );

  if (isCollapsed) {
    return <></>;
  }

  return (
    <div className="w-64 bg-base-200 flex flex-col h-full border-r border-base-300">
      {/* Header */}
      <div className="p-4 border-b border-base-300">
        <button
          onClick={handleNewChat}
          className="btn btn-primary w-full"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-5 h-5"
          >
            <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto">
        {sessionsLoading && sessions.length === 0 ? (
          // Loading skeleton
          <div className="p-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-base-300 rounded w-3/4 mb-2" />
                <div className="h-3 bg-base-300 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : sessions.length === 0 ? (
          // Empty state with icon, headline, description per UI/UX guidelines
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-base-300 flex items-center justify-center mb-3">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-6 h-6 text-base-content/40"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M3.43 2.524A41.29 41.29 0 0 1 10 2c2.236 0 4.43.18 6.57.524 1.437.231 2.43 1.49 2.43 2.902v5.148c0 1.413-.993 2.67-2.43 2.902a41.202 41.202 0 0 1-5.183.501.78.78 0 0 0-.528.224l-3.579 3.58A.75.75 0 0 1 6 17.25v-3.443a.75.75 0 0 0-.663-.746 41.268 41.268 0 0 1-1.907-.299c-1.437-.232-2.43-1.49-2.43-2.902V5.426c0-1.413.993-2.67 2.43-2.902Z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-base-content mb-1">No conversations yet</h3>
            <p className="text-xs text-base-content/60">
              Click "New Chat" above to begin
            </p>
          </div>
        ) : (
          // Sessions list
          <div className="divide-y divide-base-300">
            {sessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={conversationId === session.id}
                onClick={() => handleSessionClick(session.id)}
                onDelete={() => handleSessionDelete(session.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer with session count */}
      {sessions.length > 0 && (
        <div className="p-3 border-t border-base-300 text-xs text-base-content/60 text-center">
          {sessions.length} conversation{sessions.length !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}
