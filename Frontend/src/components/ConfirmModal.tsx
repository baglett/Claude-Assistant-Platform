"use client";

/**
 * ConfirmModal component for confirmation dialogs.
 *
 * Replaces native browser confirm() with a styled DaisyUI modal
 * for consistent UX across the application.
 */

import { useCallback, useEffect, useRef } from "react";

/**
 * Props for the ConfirmModal component.
 */
interface ConfirmModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Modal title */
  title: string;
  /** Confirmation message/description */
  message: string;
  /** Text for the confirm button */
  confirmText?: string;
  /** Text for the cancel button */
  cancelText?: string;
  /** Visual variant for the confirm button */
  variant?: "primary" | "error" | "warning";
  /** Whether the confirm action is in progress */
  isLoading?: boolean;
  /** Callback when confirm is clicked */
  onConfirm: () => void;
  /** Callback when cancel is clicked or modal is closed */
  onCancel: () => void;
}

/**
 * Confirmation modal component using DaisyUI styling.
 *
 * Provides a consistent, accessible confirmation dialog that replaces
 * the native browser confirm() function.
 *
 * @example
 * <ConfirmModal
 *   isOpen={showConfirm}
 *   title="Delete Todo"
 *   message="Are you sure you want to delete this todo? This action cannot be undone."
 *   variant="error"
 *   confirmText="Delete"
 *   onConfirm={handleDelete}
 *   onCancel={() => setShowConfirm(false)}
 * />
 */
export function ConfirmModal({
  isOpen,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "primary",
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps): JSX.Element | null {
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  /**
   * Focus the confirm button when modal opens for accessibility.
   */
  useEffect(() => {
    if (isOpen && confirmButtonRef.current) {
      confirmButtonRef.current.focus();
    }
  }, [isOpen]);

  /**
   * Handle keyboard escape to close modal.
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape" && !isLoading) {
        onCancel();
      }
    },
    [isLoading, onCancel]
  );

  /**
   * Get button class based on variant.
   */
  const getButtonClass = (): string => {
    switch (variant) {
      case "error":
        return "btn btn-error";
      case "warning":
        return "btn btn-warning";
      default:
        return "btn btn-primary";
    }
  };

  if (!isOpen) return null;

  return (
    <dialog
      className="modal modal-open"
      onKeyDown={handleKeyDown}
      aria-labelledby="confirm-modal-title"
      aria-describedby="confirm-modal-description"
    >
      <div className="modal-box">
        {/* Warning icon for destructive actions */}
        {variant === "error" && (
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-full bg-error/20 flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-6 h-6 text-error"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>
        )}

        {/* Title */}
        <h3
          id="confirm-modal-title"
          className="font-bold text-lg text-center"
        >
          {title}
        </h3>

        {/* Message */}
        <p
          id="confirm-modal-description"
          className="py-4 text-base-content/70 text-center"
        >
          {message}
        </p>

        {/* Action buttons */}
        <div className="modal-action justify-center gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="btn btn-ghost"
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            onClick={onConfirm}
            className={getButtonClass()}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="loading loading-spinner loading-sm" />
                Processing...
              </>
            ) : (
              confirmText
            )}
          </button>
        </div>
      </div>

      {/* Click outside to close (only if not loading) */}
      <form method="dialog" className="modal-backdrop">
        <button
          onClick={onCancel}
          disabled={isLoading}
          aria-label="Close modal"
        >
          close
        </button>
      </form>
    </dialog>
  );
}
