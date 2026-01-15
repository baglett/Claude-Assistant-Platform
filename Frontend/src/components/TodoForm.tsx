"use client";

/**
 * TodoForm component for creating and editing todos.
 *
 * Provides a modal form with fields for title, description,
 * priority, agent assignment, and scheduled time.
 */

import { useCallback, useEffect, useState } from "react";
import { useTodoStore } from "@/stores/todoStore";
import type {
  Todo,
  CreateTodoRequest,
  AgentType,
  TodoPriority,
} from "@/lib/api/todos";

/**
 * Props for the TodoForm component.
 */
interface TodoFormProps {
  /** Todo to edit (null for create mode) */
  todo?: Todo | null;
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
}

/**
 * Available agent options for the dropdown.
 */
const agentOptions: { value: AgentType | ""; label: string }[] = [
  { value: "", label: "Unassigned" },
  { value: "github", label: "GitHub" },
  { value: "email", label: "Email" },
  { value: "calendar", label: "Calendar" },
  { value: "obsidian", label: "Obsidian" },
  { value: "orchestrator", label: "Orchestrator" },
];

/**
 * Available priority options for the dropdown.
 */
const priorityOptions: { value: TodoPriority; label: string }[] = [
  { value: 1, label: "Critical" },
  { value: 2, label: "High" },
  { value: 3, label: "Medium" },
  { value: 4, label: "Low" },
  { value: 5, label: "Lowest" },
];

/**
 * TodoForm component for creating/editing todos.
 *
 * @example
 * <TodoForm isOpen={showForm} onClose={() => setShowForm(false)} todo={editingTodo} />
 */
export function TodoForm({
  todo,
  isOpen,
  onClose,
}: TodoFormProps): JSX.Element | null {
  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TodoPriority>(3);
  const [assignedAgent, setAssignedAgent] = useState<AgentType | "">("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Store actions
  const addTodo = useTodoStore((state) => state.addTodo);
  const editTodo = useTodoStore((state) => state.editTodo);
  const error = useTodoStore((state) => state.error);

  /**
   * Populate form when editing.
   */
  useEffect(() => {
    if (todo) {
      setTitle(todo.title);
      setDescription(todo.description || "");
      setPriority(todo.priority);
      setAssignedAgent(todo.assigned_agent || "");
      setScheduledAt(
        todo.scheduled_at
          ? new Date(todo.scheduled_at).toISOString().slice(0, 16)
          : ""
      );
    } else {
      // Reset form for create mode
      setTitle("");
      setDescription("");
      setPriority(3);
      setAssignedAgent("");
      setScheduledAt("");
    }
  }, [todo, isOpen]);

  /**
   * Handle form submission.
   */
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!title.trim()) return;

      setIsSubmitting(true);

      const data: CreateTodoRequest = {
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        assigned_agent: assignedAgent || undefined,
        scheduled_at: scheduledAt
          ? new Date(scheduledAt).toISOString()
          : undefined,
      };

      let success = false;

      if (todo) {
        // Edit mode
        const result = await editTodo(todo.id, data);
        success = result !== null;
      } else {
        // Create mode
        const result = await addTodo(data);
        success = result !== null;
      }

      setIsSubmitting(false);

      if (success) {
        onClose();
      }
    },
    [
      title,
      description,
      priority,
      assignedAgent,
      scheduledAt,
      todo,
      addTodo,
      editTodo,
      onClose,
    ]
  );

  if (!isOpen) return null;

  return (
    <dialog className="modal modal-open">
      <div className="modal-box">
        <h3 className="font-bold text-lg mb-4">
          {todo ? "Edit Todo" : "Create Todo"}
        </h3>

        {/* Error display */}
        {error && (
          <div className="alert alert-error mb-4">
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Title field */}
          <div className="form-control mb-4">
            <label className="label">
              <span className="label-text">Title *</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What needs to be done?"
              className="input input-bordered w-full"
              required
              maxLength={500}
              autoFocus
            />
          </div>

          {/* Description field */}
          <div className="form-control mb-4">
            <label className="label">
              <span className="label-text">Description</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Additional details..."
              className="textarea textarea-bordered w-full"
              rows={3}
            />
          </div>

          {/* Priority and Agent row */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            {/* Priority dropdown */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Priority</span>
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value) as TodoPriority)}
                className="select select-bordered w-full"
              >
                {priorityOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Agent dropdown */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Assigned Agent</span>
              </label>
              <select
                value={assignedAgent}
                onChange={(e) => setAssignedAgent(e.target.value as AgentType | "")}
                className="select select-bordered w-full"
              >
                {agentOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Scheduled time field */}
          <div className="form-control mb-6">
            <label className="label">
              <span className="label-text">Scheduled Time (optional)</span>
            </label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="input input-bordered w-full"
            />
            <label className="label">
              <span className="label-text-alt text-base-content/60">
                Leave empty for manual execution
              </span>
            </label>
          </div>

          {/* Action buttons */}
          <div className="modal-action">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-ghost"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting || !title.trim()}
            >
              {isSubmitting ? (
                <>
                  <span className="loading loading-spinner loading-sm" />
                  Saving...
                </>
              ) : todo ? (
                "Update"
              ) : (
                "Create"
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Click outside to close */}
      <form method="dialog" className="modal-backdrop">
        <button onClick={onClose}>close</button>
      </form>
    </dialog>
  );
}
