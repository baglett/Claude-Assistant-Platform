/**
 * Generated resumes history page.
 *
 * View and manage previously generated resumes.
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  useResumeStore,
  getResumeFormatLabel,
} from "@/stores/resumeStore";
import { ResumeCard } from "@/components/resume";
import type { ResumeFormat } from "@/lib/api/resume";

/**
 * Format options.
 */
const FORMAT_OPTIONS: { value: ResumeFormat | ""; label: string }[] = [
  { value: "", label: "All Formats" },
  { value: "pdf", label: "PDF" },
  { value: "docx", label: "Word (DOCX)" },
];

/**
 * History page component.
 */
export default function HistoryPage() {
  const {
    generatedResumes,
    resumeFilters,
    resumeTotal,
    resumeHasNext,
    resumesLoading,
    resumesError,
    selectedResume,
    fetchGeneratedResumes,
    setResumeFilters,
    removeGeneratedResume,
    selectResume,
  } = useResumeStore();

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Load resumes on mount
  useEffect(() => {
    fetchGeneratedResumes();
  }, [fetchGeneratedResumes]);

  const handleDelete = async () => {
    if (!deleteConfirmId) return;
    const success = await removeGeneratedResume(deleteConfirmId);
    if (success) {
      setDeleteConfirmId(null);
    }
  };

  return (
    <div className="min-h-screen bg-base-200">
      <div className="container mx-auto p-4 lg:p-8">
        {/* Breadcrumbs */}
        <div className="breadcrumbs mb-4 text-sm">
          <ul>
            <li>
              <Link href="/resume">Resume</Link>
            </li>
            <li>History</li>
          </ul>
        </div>

        {/* Page Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold lg:text-3xl">Generated Resumes</h1>
            <p className="text-base-content/60">
              View your previously generated resumes
            </p>
          </div>
          <Link href="/resume" className="btn btn-ghost">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Back to Dashboard
          </Link>
        </div>

        {/* Info Alert */}
        <div className="alert mb-6">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <h3 className="font-bold">Generate resumes via chat</h3>
            <p className="text-sm">
              To generate a new resume, chat with the assistant and share a job
              listing URL. The assistant will scrape the job, match your skills,
              and generate a tailored resume.
            </p>
          </div>
        </div>

        {/* Error Alert */}
        {resumesError && (
          <div className="alert alert-error mb-6">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span>{resumesError}</span>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <select
            value={resumeFilters.format || ""}
            onChange={(e) =>
              setResumeFilters({
                format: (e.target.value as ResumeFormat) || undefined,
              })
            }
            className="select select-bordered select-sm"
          >
            {FORMAT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <span className="ml-auto text-sm text-base-content/60">
            {resumeTotal} resume{resumeTotal !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Loading State */}
        {resumesLoading && (
          <div className="flex justify-center py-8">
            <span className="loading loading-spinner loading-lg" />
          </div>
        )}

        {/* Empty State */}
        {!resumesLoading && generatedResumes.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-base-200">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-8 w-8 text-base-content/40"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold">No resumes generated yet</h3>
            <p className="mb-4 text-base-content/60">
              Chat with the assistant to generate your first tailored resume
            </p>
            <Link href="/" className="btn btn-primary">
              Go to Chat
            </Link>
          </div>
        )}

        {/* Resume Grid */}
        {!resumesLoading && generatedResumes.length > 0 && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {generatedResumes.map((resume) => (
              <ResumeCard
                key={resume.id}
                resume={resume}
                onClick={() =>
                  selectResume(selectedResume?.id === resume.id ? null : resume)
                }
                onDelete={() => setDeleteConfirmId(resume.id)}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {!resumesLoading && resumeHasNext && (
          <div className="mt-6 flex justify-center">
            <button
              onClick={() =>
                setResumeFilters({ page: (resumeFilters.page || 1) + 1 })
              }
              className="btn btn-outline"
            >
              Load More
            </button>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirmId && (
          <div className="modal modal-open">
            <div className="modal-box">
              <h3 className="text-lg font-bold">Delete Resume</h3>
              <p className="py-4">
                Are you sure you want to delete this resume? This will remove it
                from the system but not from Google Drive.
              </p>
              <div className="modal-action">
                <button
                  onClick={() => setDeleteConfirmId(null)}
                  className="btn btn-ghost"
                >
                  Cancel
                </button>
                <button onClick={handleDelete} className="btn btn-error">
                  Delete
                </button>
              </div>
            </div>
            <div
              className="modal-backdrop"
              onClick={() => setDeleteConfirmId(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
