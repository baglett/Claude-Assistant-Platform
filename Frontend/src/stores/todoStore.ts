/**
 * Todo state management using Zustand.
 *
 * Manages todo list state, filtering, and API interactions
 * for the todo dashboard.
 */

import { create } from "zustand";
import {
  getTodos,
  createTodo,
  updateTodo,
  deleteTodo,
  cancelTodo,
  getTodoStats,
  type Todo,
  type TodoStats,
  type TodoStatus,
  type AgentType,
  type TodoPriority,
  type CreateTodoRequest,
  type UpdateTodoRequest,
  type TodoFilters,
} from "@/lib/api/todos";

/**
 * Todo store state interface.
 */
interface TodoState {
  /** Array of todos in the current view */
  todos: Todo[];
  /** Todo statistics */
  stats: TodoStats | null;
  /** Current filter settings */
  filters: TodoFilters;
  /** Whether todos are being loaded */
  isLoading: boolean;
  /** Current error message, if any */
  error: string | null;
  /** Total count of todos matching filters */
  total: number;
  /** Whether there are more pages */
  hasNext: boolean;

  /** Fetch todos with current filters */
  fetchTodos: () => Promise<void>;
  /** Fetch todo statistics */
  fetchStats: () => Promise<void>;
  /** Create a new todo */
  addTodo: (data: CreateTodoRequest) => Promise<Todo | null>;
  /** Update an existing todo */
  editTodo: (id: string, data: UpdateTodoRequest) => Promise<Todo | null>;
  /** Delete a todo */
  removeTodo: (id: string) => Promise<boolean>;
  /** Cancel a todo */
  cancelTodoItem: (id: string) => Promise<Todo | null>;
  /** Update filter settings */
  setFilters: (filters: Partial<TodoFilters>) => void;
  /** Reset filters to default */
  resetFilters: () => void;
  /** Set loading state */
  setLoading: (loading: boolean) => void;
  /** Set error message */
  setError: (error: string | null) => void;
  /** Clear all state */
  reset: () => void;
}

/**
 * Default filter values.
 */
const defaultFilters: TodoFilters = {
  page: 1,
  page_size: 20,
};

/**
 * Initial state values.
 */
const initialState = {
  todos: [],
  stats: null,
  filters: defaultFilters,
  isLoading: false,
  error: null,
  total: 0,
  hasNext: false,
};

/**
 * Zustand store for todo state management.
 */
export const useTodoStore = create<TodoState>()((set, get) => ({
  ...initialState,

  /**
   * Fetch todos from the API with current filters.
   */
  fetchTodos: async () => {
    const { filters, setLoading, setError } = get();
    setLoading(true);
    setError(null);

    try {
      const response = await getTodos(filters);
      set({
        todos: response.items,
        total: response.total,
        hasNext: response.has_next,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch todos";
      setError(message);
      console.error("Todo fetch error:", error);
    } finally {
      setLoading(false);
    }
  },

  /**
   * Fetch todo statistics from the API.
   */
  fetchStats: async () => {
    const { setError } = get();

    try {
      const stats = await getTodoStats();
      set({ stats });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch stats";
      setError(message);
      console.error("Stats fetch error:", error);
    }
  },

  /**
   * Create a new todo.
   *
   * @param data - Todo creation data
   * @returns Created todo or null on error
   */
  addTodo: async (data: CreateTodoRequest) => {
    const { setLoading, setError, fetchTodos, fetchStats } = get();
    setLoading(true);
    setError(null);

    try {
      const todo = await createTodo(data);
      // Refresh the list and stats
      await Promise.all([fetchTodos(), fetchStats()]);
      return todo;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create todo";
      setError(message);
      console.error("Todo create error:", error);
      return null;
    } finally {
      setLoading(false);
    }
  },

  /**
   * Update an existing todo.
   *
   * @param id - Todo UUID
   * @param data - Fields to update
   * @returns Updated todo or null on error
   */
  editTodo: async (id: string, data: UpdateTodoRequest) => {
    const { setError, todos, fetchStats } = get();
    setError(null);

    try {
      const updatedTodo = await updateTodo(id, data);
      // Update local state optimistically
      set({
        todos: todos.map((t) => (t.id === id ? updatedTodo : t)),
      });
      // Refresh stats in case priority changed
      await fetchStats();
      return updatedTodo;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to update todo";
      setError(message);
      console.error("Todo update error:", error);
      return null;
    }
  },

  /**
   * Delete a todo.
   *
   * @param id - Todo UUID
   * @returns True if deleted successfully
   */
  removeTodo: async (id: string) => {
    const { setError, todos, fetchStats } = get();
    setError(null);

    try {
      await deleteTodo(id);
      // Remove from local state
      set({
        todos: todos.filter((t) => t.id !== id),
        total: get().total - 1,
      });
      // Refresh stats
      await fetchStats();
      return true;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to delete todo";
      setError(message);
      console.error("Todo delete error:", error);
      return false;
    }
  },

  /**
   * Cancel a todo.
   *
   * @param id - Todo UUID
   * @returns Cancelled todo or null on error
   */
  cancelTodoItem: async (id: string) => {
    const { setError, todos, fetchStats } = get();
    setError(null);

    try {
      const cancelledTodo = await cancelTodo(id);
      // Update local state
      set({
        todos: todos.map((t) => (t.id === id ? cancelledTodo : t)),
      });
      // Refresh stats
      await fetchStats();
      return cancelledTodo;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to cancel todo";
      setError(message);
      console.error("Todo cancel error:", error);
      return null;
    }
  },

  /**
   * Update filter settings and refetch todos.
   *
   * @param filters - Partial filter updates
   */
  setFilters: (filters: Partial<TodoFilters>) => {
    set((state) => ({
      filters: { ...state.filters, ...filters },
    }));
    // Fetch with new filters
    get().fetchTodos();
  },

  /**
   * Reset filters to default values.
   */
  resetFilters: () => {
    set({ filters: defaultFilters });
    get().fetchTodos();
  },

  setLoading: (isLoading: boolean) => set({ isLoading }),

  setError: (error: string | null) => set({ error }),

  /**
   * Reset all state to initial values.
   */
  reset: () => set(initialState),
}));

/**
 * Helper to get status display text.
 */
export function getStatusLabel(status: TodoStatus): string {
  const labels: Record<TodoStatus, string> = {
    pending: "Pending",
    in_progress: "In Progress",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
  };
  return labels[status];
}

/**
 * Helper to get status color class.
 */
export function getStatusColor(status: TodoStatus): string {
  const colors: Record<TodoStatus, string> = {
    pending: "badge-warning",
    in_progress: "badge-info",
    completed: "badge-success",
    failed: "badge-error",
    cancelled: "badge-ghost",
  };
  return colors[status];
}

/**
 * Helper to get priority label.
 */
export function getPriorityLabel(priority: TodoPriority): string {
  const labels: Record<TodoPriority, string> = {
    1: "Critical",
    2: "High",
    3: "Medium",
    4: "Low",
    5: "Lowest",
  };
  return labels[priority];
}

/**
 * Helper to get priority color class.
 */
export function getPriorityColor(priority: TodoPriority): string {
  const colors: Record<TodoPriority, string> = {
    1: "text-error",
    2: "text-warning",
    3: "text-base-content",
    4: "text-base-content/70",
    5: "text-base-content/50",
  };
  return colors[priority];
}

/**
 * Helper to get agent display label.
 */
export function getAgentLabel(agent: AgentType | null): string {
  if (!agent) return "Unassigned";
  const labels: Record<AgentType, string> = {
    github: "GitHub",
    email: "Email",
    calendar: "Calendar",
    obsidian: "Obsidian",
    orchestrator: "Orchestrator",
  };
  return labels[agent];
}
