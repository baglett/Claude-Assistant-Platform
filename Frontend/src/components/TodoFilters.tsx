"use client";

/**
 * TodoFilters component for filtering the todo list.
 *
 * Provides dropdowns for filtering by status, agent, and priority.
 */

import { useTodoStore } from "@/stores/todoStore";
import type { TodoStatus, AgentType, TodoPriority } from "@/lib/api/todos";

/**
 * TodoFilters component for filtering todos.
 *
 * @example
 * <TodoFilters />
 */
export function TodoFilters(): JSX.Element {
  const filters = useTodoStore((state) => state.filters);
  const setFilters = useTodoStore((state) => state.setFilters);
  const resetFilters = useTodoStore((state) => state.resetFilters);

  /**
   * Check if any filters are active.
   */
  const hasActiveFilters =
    filters.status || filters.assigned_agent || filters.priority;

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Status filter */}
      <div className="form-control">
        <select
          value={filters.status || ""}
          onChange={(e) =>
            setFilters({
              status: (e.target.value as TodoStatus) || undefined,
              page: 1,
            })
          }
          className="select select-bordered select-sm"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Agent filter */}
      <div className="form-control">
        <select
          value={filters.assigned_agent || ""}
          onChange={(e) =>
            setFilters({
              assigned_agent: (e.target.value as AgentType) || undefined,
              page: 1,
            })
          }
          className="select select-bordered select-sm"
        >
          <option value="">All Agents</option>
          <option value="github">GitHub</option>
          <option value="email">Email</option>
          <option value="calendar">Calendar</option>
          <option value="obsidian">Obsidian</option>
          <option value="orchestrator">Orchestrator</option>
        </select>
      </div>

      {/* Priority filter */}
      <div className="form-control">
        <select
          value={filters.priority || ""}
          onChange={(e) =>
            setFilters({
              priority: e.target.value
                ? (Number(e.target.value) as TodoPriority)
                : undefined,
              page: 1,
            })
          }
          className="select select-bordered select-sm"
        >
          <option value="">All Priorities</option>
          <option value="1">Critical</option>
          <option value="2">High</option>
          <option value="3">Medium</option>
          <option value="4">Low</option>
          <option value="5">Lowest</option>
        </select>
      </div>

      {/* Reset button */}
      {hasActiveFilters && (
        <button
          onClick={resetFilters}
          className="btn btn-ghost btn-sm"
          title="Clear all filters"
        >
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
          Clear
        </button>
      )}
    </div>
  );
}
