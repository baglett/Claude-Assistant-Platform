"use client";

/**
 * Global error boundary component for the application.
 *
 * Catches and displays runtime errors during rendering,
 * providing a recovery mechanism for users.
 */

import { useEffect } from "react";

/**
 * Props for the error boundary component.
 */
interface ErrorProps {
  /** The error that was thrown */
  error: Error & { digest?: string };
  /** Function to attempt recovery by re-rendering the segment */
  reset: () => void;
}

/**
 * Error boundary component for handling runtime errors.
 *
 * This component is automatically rendered by Next.js App Router
 * when an error occurs during rendering. It provides a user-friendly
 * error message and a recovery mechanism.
 *
 * @param error - The error object containing details about what went wrong
 * @param reset - Function to reset the error boundary and retry rendering
 */
export default function Error({ error, reset }: ErrorProps): JSX.Element {
  /**
   * Log error to console for debugging.
   * In production, this could be sent to an error reporting service.
   */
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-100 p-4">
      <div className="card bg-base-200 shadow-xl max-w-md w-full">
        <div className="card-body items-center text-center">
          {/* Error icon */}
          <div className="w-16 h-16 rounded-full bg-error/20 flex items-center justify-center mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="w-8 h-8 text-error"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z"
                clipRule="evenodd"
              />
            </svg>
          </div>

          {/* Error title */}
          <h2 className="card-title text-xl">Something went wrong</h2>

          {/* Error description */}
          <p className="text-base-content/70 mb-4">
            An unexpected error occurred. Please try again or refresh the page.
          </p>

          {/* Error details (development only) */}
          {process.env.NODE_ENV === "development" && error.message && (
            <div className="w-full mb-4">
              <div className="collapse collapse-arrow bg-base-300">
                <input type="checkbox" />
                <div className="collapse-title text-sm font-medium">
                  Error Details
                </div>
                <div className="collapse-content">
                  <pre className="text-xs text-error overflow-x-auto whitespace-pre-wrap break-all">
                    {error.message}
                    {error.stack && (
                      <>
                        {"\n\n"}
                        {error.stack}
                      </>
                    )}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="card-actions justify-center gap-3">
            <button onClick={reset} className="btn btn-primary">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path
                  fillRule="evenodd"
                  d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm-1.561-5.848a5.5 5.5 0 00-9.201 2.466.75.75 0 001.449.39 4.001 4.001 0 016.887-1.79l.31.31H10.77a.75.75 0 000 1.5h4.243a.75.75 0 00.75-.75V3.46a.75.75 0 00-1.5 0v2.424l-.312-.31z"
                  clipRule="evenodd"
                />
              </svg>
              Try Again
            </button>
            <a href="/" className="btn btn-ghost">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path
                  fillRule="evenodd"
                  d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 11h-1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-3a1 1 0 00-1-1H9a1 1 0 00-1 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-6H3a1 1 0 01-.707-1.707l7-7z"
                  clipRule="evenodd"
                />
              </svg>
              Go Home
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
