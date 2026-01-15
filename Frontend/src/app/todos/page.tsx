"use client";

/**
 * Todo dashboard page for managing tasks.
 *
 * Displays todo statistics, filters, and list with CRUD operations.
 */

import { useEffect, useState, useCallback } from "react";
import { useTodoStore } from "@/stores/todoStore";
import { TodoStats } from "@/components/TodoStats";
import { TodoFilters } from "@/components/TodoFilters";
import { TodoList } from "@/components/TodoList";
import { TodoForm } from "@/components/TodoForm";
import type { Todo } from "@/lib/api/todos";

/**
 * Todo page component.
 *
 * Provides a complete todo management dashboard with:
 * - Statistics overview
 * - Filtering capabilities
 * - Todo list with CRUD
 * - Create/edit modal
 */
export default function TodosPage(): JSX.Element {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null);

  const fetchTodos = useTodoStore((state) => state.fetchTodos);
  const fetchStats = useTodoStore((state) => state.fetchStats);
  const error = useTodoStore((state) => state.error);
  const setError = useTodoStore((state) => state.setError);

  /**
   * Load todos and stats on mount.
   */
  useEffect(() => {
    fetchTodos();
    fetchStats();
  }, [fetchTodos, fetchStats]);

  /**
   * Handle opening the create form.
   */
  const handleCreate = useCallback(() => {
    setEditingTodo(null);
    setIsFormOpen(true);
  }, []);

  /**
   * Handle opening the edit form.
   */
  const handleEdit = useCallback((todo: Todo) => {
    setEditingTodo(todo);
    setIsFormOpen(true);
  }, []);

  /**
   * Handle closing the form.
   */
  const handleCloseForm = useCallback(() => {
    setIsFormOpen(false);
    setEditingTodo(null);
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="navbar bg-base-200 border-b border-base-300 px-4">
        <div className="flex-1">
          <span className="text-xl font-bold">Todo Dashboard</span>
        </div>
        <div className="flex-none">
          <a href="/" className="btn btn-ghost btn-sm">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-5 h-5"
            >
              <path
                fillRule="evenodd"
                d="M4.848 2.771A49.144 49.144 0 0 1 12 2.25c2.43 0 4.817.178 7.152.52 1.978.292 3.348 2.024 3.348 3.97v6.02c0 1.946-1.37 3.678-3.348 3.97a48.901 48.901 0 0 1-3.476.383.39.39 0 0 0-.297.17l-2.755 4.133a.75.75 0 0 1-1.248 0l-2.755-4.133a.39.39 0 0 0-.297-.17 48.9 48.9 0 0 1-3.476-.384c-1.978-.29-3.348-2.024-3.348-3.97V6.741c0-1.946 1.37-3.68 3.348-3.97Z"
                clipRule="evenodd"
              />
            </svg>
            Chat
          </a>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="alert alert-error mx-4 mt-4">
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
          <button onClick={() => setError(null)} className="btn btn-sm btn-ghost">
            Dismiss
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Stats */}
          <TodoStats />

          {/* Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <TodoFilters />

            <button onClick={handleCreate} className="btn btn-primary btn-sm">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
              </svg>
              New Todo
            </button>
          </div>

          {/* Todo list */}
          <TodoList onEdit={handleEdit} />
        </div>
      </div>

      {/* Create/Edit form modal */}
      <TodoForm
        todo={editingTodo}
        isOpen={isFormOpen}
        onClose={handleCloseForm}
      />
    </div>
  );
}
