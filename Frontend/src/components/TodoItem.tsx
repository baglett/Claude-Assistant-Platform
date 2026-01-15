"use client";

/**
 * TodoItem component for displaying a single todo in the list.
 *
 * Displays todo details with status badge, priority indicator,
 * and action buttons for edit, delete, and cancel operations.
 */

import { useCallback, useState } from "react";
import {
  useTodoStore,
  getStatusLabel,
  getStatusColor,
  getPriorityLabel,
  getPriorityColor,
  getAgentLabel,
} from "@/stores/todoStore";
import { ConfirmModal } from "./ConfirmModal";
import type { Todo } from "@/lib/api/todos";

/**
 * Props for the TodoItem component.
 */
interface TodoItemProps {
  /** The todo to display */
  todo: Todo;
  /** Callback when edit is requested */
  onEdit?: (todo: Todo) => void;
}

/**
 * Format a date string for display.
 */
function formatDate(dateString: string | null): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * TodoItem component displaying a single todo with actions.
 *
 * @example
 * <TodoItem todo={todo} onEdit={handleEdit} />
 */
export function TodoItem({ todo, onEdit }: TodoItemProps): JSX.Element {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const removeTodo = useTodoStore((state) => state.removeTodo);
  const cancelTodoItem = useTodoStore((state) => state.cancelTodoItem);

  /**
   * Handle delete confirmation.
   */
  const handleConfirmDelete = useCallback(async () => {
    setIsDeleting(true);
    await removeTodo(todo.id);
    setIsDeleting(false);
    setShowDeleteConfirm(false);
  }, [todo.id, removeTodo]);

  /**
   * Handle cancel confirmation.
   */
  const handleConfirmCancel = useCallback(async () => {
    setIsCancelling(true);
    await cancelTodoItem(todo.id);
    setIsCancelling(false);
    setShowCancelConfirm(false);
  }, [todo.id, cancelTodoItem]);

  /**
   * Check if todo can be cancelled.
   */
  const canCancel =
    todo.status === "pending" || todo.status === "in_progress";

  /**
   * Check if todo is in a final state.
   */
  const isFinal =
    todo.status === "completed" ||
    todo.status === "failed" ||
    todo.status === "cancelled";

  return (
    <div className="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow">
      <div className="card-body p-4">
        {/* Header row with title and status */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3
              className={`card-title text-base ${isFinal ? "line-through opacity-60" : ""}`}
            >
              {todo.title}
            </h3>
            {todo.description && (
              <p className="text-sm text-base-content/70 mt-1 line-clamp-2">
                {todo.description}
              </p>
            )}
          </div>
          <span className={`badge ${getStatusColor(todo.status)} badge-sm`}>
            {getStatusLabel(todo.status)}
          </span>
        </div>

        {/* Metadata row */}
        <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-base-content/60">
          {/* Priority */}
          <span className={`font-medium ${getPriorityColor(todo.priority)}`}>
            {getPriorityLabel(todo.priority)}
          </span>

          {/* Agent */}
          {todo.assigned_agent && (
            <span className="badge badge-outline badge-xs">
              {getAgentLabel(todo.assigned_agent)}
            </span>
          )}

          {/* Created date */}
          <span>Created {formatDate(todo.created_at)}</span>

          {/* Scheduled date */}
          {todo.scheduled_at && (
            <span className="text-info">
              Scheduled: {formatDate(todo.scheduled_at)}
            </span>
          )}

          {/* Completed date */}
          {todo.completed_at && (
            <span className="text-success">
              Completed: {formatDate(todo.completed_at)}
            </span>
          )}
        </div>

        {/* Result or error display */}
        {todo.result && (
          <div className="mt-2 p-2 bg-success/10 rounded text-sm text-success">
            {todo.result}
          </div>
        )}
        {todo.error_message && (
          <div className="mt-2 p-2 bg-error/10 rounded text-sm text-error">
            {todo.error_message}
          </div>
        )}

        {/* Actions */}
        <div className="card-actions justify-end mt-2">
          {/* Edit button */}
          {!isFinal && onEdit && (
            <button
              onClick={() => onEdit(todo)}
              className="btn btn-ghost btn-xs"
              title="Edit todo"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
              </svg>
              Edit
            </button>
          )}

          {/* Cancel button */}
          {canCancel && (
            <button
              onClick={() => setShowCancelConfirm(true)}
              disabled={isCancelling}
              className="btn btn-ghost btn-xs text-warning"
              title="Cancel todo"
            >
              {isCancelling ? (
                <span className="loading loading-spinner loading-xs" />
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="w-4 h-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              Cancel
            </button>
          )}

          {/* Delete button */}
          <button
            onClick={() => setShowDeleteConfirm(true)}
            disabled={isDeleting}
            className="btn btn-ghost btn-xs text-error"
            title="Delete todo"
          >
            {isDeleting ? (
              <span className="loading loading-spinner loading-xs" />
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path
                  fillRule="evenodd"
                  d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            Delete
          </button>
        </div>
      </div>

      {/* Delete confirmation modal */}
      <ConfirmModal
        isOpen={showDeleteConfirm}
        title="Delete Todo"
        message="Are you sure you want to delete this todo? This action cannot be undone."
        confirmText="Delete"
        variant="error"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />

      {/* Cancel confirmation modal */}
      <ConfirmModal
        isOpen={showCancelConfirm}
        title="Cancel Todo"
        message="Are you sure you want to cancel this todo? It will be marked as cancelled and won't be executed."
        confirmText="Cancel Todo"
        variant="warning"
        isLoading={isCancelling}
        onConfirm={handleConfirmCancel}
        onCancel={() => setShowCancelConfirm(false)}
      />
    </div>
  );
}
