/**
 * Job listing card component.
 *
 * Displays a scraped job listing with details, skills, and actions.
 */

"use client";

import {
  useResumeStore,
  getApplicationStatusLabel,
  getApplicationStatusColor,
  formatSalaryRange,
} from "@/stores/resumeStore";
import type { JobListing, ApplicationStatus } from "@/lib/api/resume";

/**
 * Job listing card props.
 */
interface JobListingCardProps {
  /** Job listing data */
  job: JobListing;
  /** Whether to show full details */
  expanded?: boolean;
  /** Callback when card is clicked */
  onClick?: () => void;
  /** Callback when edit is requested */
  onEdit?: () => void;
  /** Callback when delete is requested */
  onDelete?: () => void;
}

/**
 * Format relative time.
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

/**
 * Job listing card component.
 */
export function JobListingCard({
  job,
  expanded = false,
  onClick,
  onEdit,
  onDelete,
}: JobListingCardProps) {
  const { toggleJobFavorite } = useResumeStore();

  const handleFavoriteClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await toggleJobFavorite(job.id);
  };

  const handleEditClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.();
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.();
  };

  return (
    <div
      className={`card bg-base-100 shadow-sm transition-all ${
        onClick ? "cursor-pointer hover:shadow-md" : ""
      }`}
      onClick={onClick}
    >
      <div className="card-body p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold truncate">{job.job_title}</h3>
              {job.is_remote && (
                <span className="badge badge-info badge-sm">Remote</span>
              )}
            </div>
            <p className="text-base-content/70 truncate">
              {job.company_name || "Unknown Company"}
              {job.location && ` · ${job.location}`}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            <button
              onClick={handleFavoriteClick}
              className={`btn btn-ghost btn-sm btn-square ${
                job.is_favorite ? "text-warning" : ""
              }`}
              aria-label={job.is_favorite ? "Remove from favorites" : "Add to favorites"}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill={job.is_favorite ? "currentColor" : "none"}
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                />
              </svg>
            </button>
            {onEdit && (
              <button
                onClick={handleEditClick}
                className="btn btn-ghost btn-sm btn-square"
                aria-label="Edit job listing"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
              </button>
            )}
            {onDelete && (
              <button
                onClick={handleDeleteClick}
                className="btn btn-ghost btn-sm btn-square text-error"
                aria-label="Delete job listing"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Meta Info */}
        <div className="flex flex-wrap items-center gap-2 text-sm text-base-content/60">
          <span
            className={`badge badge-sm ${getApplicationStatusColor(job.application_status as ApplicationStatus)}`}
          >
            {getApplicationStatusLabel(job.application_status as ApplicationStatus)}
          </span>
          {job.salary_min || job.salary_max ? (
            <span>
              {formatSalaryRange(job.salary_min, job.salary_max, job.salary_currency)}
            </span>
          ) : null}
          <span>Scraped {formatRelativeTime(job.scraped_at)}</span>
        </div>

        {/* Skills */}
        {(job.required_skills.length > 0 || job.preferred_skills.length > 0) && (
          <div className="mt-2 space-y-2">
            {job.required_skills.length > 0 && (
              <div>
                <span className="text-xs text-base-content/60">Required: </span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {job.required_skills.slice(0, expanded ? undefined : 5).map((skill, idx) => (
                    <span
                      key={idx}
                      className="badge badge-outline badge-sm"
                    >
                      {skill}
                    </span>
                  ))}
                  {!expanded && job.required_skills.length > 5 && (
                    <span className="badge badge-ghost badge-sm">
                      +{job.required_skills.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            )}
            {expanded && job.preferred_skills.length > 0 && (
              <div>
                <span className="text-xs text-base-content/60">Preferred: </span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {job.preferred_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="badge badge-ghost badge-sm"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Expanded Content */}
        {expanded && (
          <>
            {/* Description */}
            {job.description && (
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-1">Description</h4>
                <p className="text-sm text-base-content/70 whitespace-pre-wrap line-clamp-6">
                  {job.description}
                </p>
              </div>
            )}

            {/* Requirements */}
            {job.requirements.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-1">Requirements</h4>
                <ul className="text-sm text-base-content/70 list-disc list-inside space-y-1">
                  {job.requirements.map((req, idx) => (
                    <li key={idx}>{req}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Notes */}
            {job.notes && (
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-1">Notes</h4>
                <p className="text-sm text-base-content/70">{job.notes}</p>
              </div>
            )}

            {/* Source Link */}
            <div className="mt-4">
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="link link-primary text-sm"
                onClick={(e) => e.stopPropagation()}
              >
                View Original Posting
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="inline h-4 w-4 ml-1"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default JobListingCard;
