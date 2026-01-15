"use client";

/**
 * TodoList component for displaying the list of todos.
 *
 * Renders todos with pagination and empty state handling.
 */

import { useTodoStore } from "@/stores/todoStore";
import { TodoItem } from "./TodoItem";
import type { Todo } from "@/lib/api/todos";

/**
 * Props for the TodoList component.
 */
interface TodoListProps {
  /** Callback when edit is requested */
  onEdit?: (todo: Todo) => void;
}

/**
 * Empty state component when no todos exist.
 */
function EmptyState(): JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center mb-4">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="w-8 h-8 text-primary"
        >
          <path
            fillRule="evenodd"
            d="M7.502 6h7.128A3.375 3.375 0 0118 9.375v9.375a3 3 0 003-3V6.108c0-1.505-1.125-2.811-2.664-2.94a48.972 48.972 0 00-.673-.05A3 3 0 0015 1.5h-1.5a3 3 0 00-2.663 1.618c-.225.015-.45.032-.673.05C8.662 3.295 7.554 4.542 7.502 6zM13.5 3A1.5 1.5 0 0012 4.5h4.5A1.5 1.5 0 0015 3h-1.5z"
            clipRule="evenodd"
          />
          <path
            fillRule="evenodd"
            d="M3 9.375C3 8.339 3.84 7.5 4.875 7.5h9.75c1.036 0 1.875.84 1.875 1.875v11.25c0 1.035-.84 1.875-1.875 1.875h-9.75A1.875 1.875 0 013 20.625V9.375zm9.586 4.594a.75.75 0 00-1.172-.938l-2.476 3.096-.908-.907a.75.75 0 00-1.06 1.06l1.5 1.5a.75.75 0 001.116-.062l3-3.75z"
            clipRule="evenodd"
          />
        </svg>
      </div>
      <h3 className="text-lg font-semibold mb-2">No Todos Yet</h3>
      <p className="text-base-content/70 max-w-sm">
        Create your first todo to start tracking tasks. You can assign them to
        agents for automatic execution.
      </p>
    </div>
  );
}

/**
 * Loading skeleton component.
 */
function LoadingSkeleton(): JSX.Element {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="card bg-base-100 shadow-sm animate-pulse">
          <div className="card-body p-4">
            <div className="h-5 bg-base-300 rounded w-3/4 mb-2" />
            <div className="h-4 bg-base-300 rounded w-1/2" />
            <div className="flex gap-2 mt-2">
              <div className="h-4 bg-base-300 rounded w-16" />
              <div className="h-4 bg-base-300 rounded w-20" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * TodoList component displaying all todos with pagination.
 *
 * @example
 * <TodoList onEdit={handleEdit} />
 */
export function TodoList({ onEdit }: TodoListProps): JSX.Element {
  const todos = useTodoStore((state) => state.todos);
  const isLoading = useTodoStore((state) => state.isLoading);
  const error = useTodoStore((state) => state.error);
  const total = useTodoStore((state) => state.total);
  const hasNext = useTodoStore((state) => state.hasNext);
  const filters = useTodoStore((state) => state.filters);
  const setFilters = useTodoStore((state) => state.setFilters);

  /**
   * Handle page navigation.
   */
  const handlePageChange = (newPage: number) => {
    setFilters({ page: newPage });
  };

  // Show loading skeleton on initial load
  if (isLoading && todos.length === 0) {
    return <LoadingSkeleton />;
  }

  // Show error state
  if (error && todos.length === 0) {
    return (
      <div className="alert alert-error">
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
        <span>{error}</span>
      </div>
    );
  }

  // Show empty state
  if (todos.length === 0) {
    return <EmptyState />;
  }

  const currentPage = filters.page || 1;
  const pageSize = filters.page_size || 20;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      {/* Todo list */}
      <div className="space-y-3">
        {todos.map((todo) => (
          <TodoItem key={todo.id} todo={todo} onEdit={onEdit} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-base-300">
          <span className="text-sm text-base-content/60">
            Showing {(currentPage - 1) * pageSize + 1} -{" "}
            {Math.min(currentPage * pageSize, total)} of {total}
          </span>

          <div className="join">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="join-item btn btn-sm"
            >
              Previous
            </button>
            <button className="join-item btn btn-sm">
              Page {currentPage} of {totalPages}
            </button>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={!hasNext}
              className="join-item btn btn-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
