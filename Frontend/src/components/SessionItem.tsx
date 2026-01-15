"use client";

/**
 * SessionItem component for displaying a single conversation session.
 *
 * Shows the session title, timestamp, and delete action.
 */

import { useCallback, useState } from "react";

import type { ConversationSummary } from "@/lib/api/chat";
import { formatRelativeTime } from "@/lib/utils/date";

/**
 * Props for the SessionItem component.
 */
interface SessionItemProps {
  /** The session data to display */
  session: ConversationSummary;
  /** Whether this session is currently active */
  isActive: boolean;
  /** Callback when the session is clicked */
  onClick: () => void;
  /** Callback when delete is requested */
  onDelete: () => void;
}

/**
 * Individual session item in the sidebar.
 *
 * Displays session title, relative timestamp, and delete button on hover.
 *
 * @example
 * <SessionItem
 *   session={session}
 *   isActive={currentId === session.id}
 *   onClick={() => loadSession(session.id)}
 *   onDelete={() => deleteSession(session.id)}
 * />
 */
export function SessionItem({
  session,
  isActive,
  onClick,
  onDelete,
}: SessionItemProps): JSX.Element {
  const [showConfirm, setShowConfirm] = useState(false);

  /**
   * Handle delete button click.
   */
  const handleDeleteClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setShowConfirm(true);
    },
    []
  );

  /**
   * Handle confirm delete.
   */
  const handleConfirmDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onDelete();
      setShowConfirm(false);
    },
    [onDelete]
  );

  /**
   * Handle cancel delete.
   */
  const handleCancelDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setShowConfirm(false);
    },
    []
  );

  return (
    <div
      onClick={onClick}
      className={`
        group relative px-3 py-3 cursor-pointer transition-colors
        hover:bg-base-300
        ${isActive ? "bg-base-300 border-l-4 border-primary" : ""}
      `}
    >
      {/* Title */}
      <p
        className={`
          text-sm font-medium line-clamp-2
          ${isActive ? "text-primary" : "text-base-content"}
        `}
      >
        {session.title}
      </p>

      {/* Timestamp and message count */}
      <p className="text-xs text-base-content/60 mt-1">
        {formatRelativeTime(session.modified_on)}
        <span className="mx-1">·</span>
        {session.message_count} messages
      </p>

      {/* Delete button (shown on hover) */}
      {!showConfirm && (
        <button
          onClick={handleDeleteClick}
          className="
            absolute right-2 top-1/2 -translate-y-1/2
            btn btn-ghost btn-xs opacity-0 group-hover:opacity-100
            transition-opacity
          "
          aria-label="Delete conversation"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4"
          >
            <path
              fillRule="evenodd"
              d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.519.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}

      {/* Confirm delete buttons */}
      {showConfirm && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
          <button
            onClick={handleConfirmDelete}
            className="btn btn-error btn-xs"
            title="Confirm delete"
          >
            Delete
          </button>
          <button
            onClick={handleCancelDelete}
            className="btn btn-ghost btn-xs"
            title="Cancel"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
