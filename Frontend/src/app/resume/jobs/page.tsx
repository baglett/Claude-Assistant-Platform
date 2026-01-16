/**
 * Job listings management page.
 *
 * View, scrape, and manage saved job listings.
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  useResumeStore,
  getApplicationStatusLabel,
  getApplicationStatusColor,
} from "@/stores/resumeStore";
import { JobListingCard } from "@/components/resume";
import type { ApplicationStatus } from "@/lib/api/resume";

/**
 * Application status options.
 */
const STATUS_OPTIONS: { value: ApplicationStatus | ""; label: string }[] = [
  { value: "", label: "All Statuses" },
  { value: "not_applied", label: "Not Applied" },
  { value: "applied", label: "Applied" },
  { value: "interviewing", label: "Interviewing" },
  { value: "offered", label: "Offered" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

/**
 * Jobs page component.
 */
export default function JobsPage() {
  const {
    jobListings,
    jobFilters,
    jobTotal,
    jobHasNext,
    jobsLoading,
    jobsError,
    scraping,
    selectedJob,
    fetchJobListings,
    setJobFilters,
    scrapeJob,
    removeJobListing,
    selectJob,
  } = useResumeStore();

  const [scrapeUrl, setScrapeUrl] = useState("");
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Load jobs on mount
  useEffect(() => {
    fetchJobListings();
  }, [fetchJobListings]);

  const handleScrape = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scrapeUrl.trim()) return;

    const result = await scrapeJob(scrapeUrl);
    if (result) {
      setScrapeUrl("");
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirmId) return;
    const success = await removeJobListing(deleteConfirmId);
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
            <li>Job Listings</li>
          </ul>
        </div>

        {/* Page Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold lg:text-3xl">Job Listings</h1>
            <p className="text-base-content/60">
              Scrape and save job postings for resume tailoring
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

        {/* Scrape Form */}
        <div className="card mb-6 bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg">Scrape New Job</h3>
            <form onSubmit={handleScrape} className="flex gap-3">
              <input
                type="url"
                value={scrapeUrl}
                onChange={(e) => setScrapeUrl(e.target.value)}
                className="input input-bordered flex-1"
                placeholder="Paste job listing URL (LinkedIn, Indeed, etc.)"
                required
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={scraping}
              >
                {scraping ? (
                  <>
                    <span className="loading loading-spinner loading-sm" />
                    Scraping...
                  </>
                ) : (
                  <>
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
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Scrape
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Error Alert */}
        {jobsError && (
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
            <span>{jobsError}</span>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={jobFilters.search || ""}
            onChange={(e) => setJobFilters({ search: e.target.value || undefined })}
            className="input input-bordered input-sm w-64"
            placeholder="Search jobs..."
          />

          <select
            value={jobFilters.application_status || ""}
            onChange={(e) =>
              setJobFilters({
                application_status:
                  (e.target.value as ApplicationStatus) || undefined,
              })
            }
            className="select select-bordered select-sm"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className="label cursor-pointer gap-2">
            <input
              type="checkbox"
              checked={jobFilters.is_favorite || false}
              onChange={(e) =>
                setJobFilters({ is_favorite: e.target.checked || undefined })
              }
              className="checkbox checkbox-sm checkbox-primary"
            />
            <span className="label-text">Favorites only</span>
          </label>

          <span className="ml-auto text-sm text-base-content/60">
            {jobTotal} job{jobTotal !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Loading State */}
        {jobsLoading && (
          <div className="flex justify-center py-8">
            <span className="loading loading-spinner loading-lg" />
          </div>
        )}

        {/* Empty State */}
        {!jobsLoading && jobListings.length === 0 && (
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
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold">No job listings yet</h3>
            <p className="mb-4 text-base-content/60">
              Paste a job URL above to scrape your first listing
            </p>
          </div>
        )}

        {/* Job Grid */}
        {!jobsLoading && jobListings.length > 0 && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {jobListings.map((job) => (
              <JobListingCard
                key={job.id}
                job={job}
                expanded={selectedJob?.id === job.id}
                onClick={() =>
                  selectJob(selectedJob?.id === job.id ? null : job)
                }
                onDelete={() => setDeleteConfirmId(job.id)}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {!jobsLoading && jobHasNext && (
          <div className="mt-6 flex justify-center">
            <button
              onClick={() =>
                setJobFilters({ page: (jobFilters.page || 1) + 1 })
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
              <h3 className="text-lg font-bold">Delete Job Listing</h3>
              <p className="py-4">
                Are you sure you want to delete this job listing? This action
                cannot be undone.
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
