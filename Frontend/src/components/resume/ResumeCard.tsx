/**
 * Generated resume card component.
 *
 * Displays a generated resume with match scores and links.
 */

"use client";

import {
  getResumeFormatLabel,
  formatMatchScore,
} from "@/stores/resumeStore";
import type { GeneratedResume } from "@/lib/api/resume";

/**
 * Resume card props.
 */
interface ResumeCardProps {
  /** Generated resume data */
  resume: GeneratedResume;
  /** Job title associated with this resume */
  jobTitle?: string;
  /** Company name associated with this resume */
  companyName?: string;
  /** Callback when card is clicked */
  onClick?: () => void;
  /** Callback when delete is requested */
  onDelete?: () => void;
}

/**
 * Format date for display.
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Generated resume card component.
 */
export function ResumeCard({
  resume,
  jobTitle,
  companyName,
  onClick,
  onDelete,
}: ResumeCardProps) {
  const skillMatch = formatMatchScore(resume.skill_match_score);
  const overallMatch = formatMatchScore(resume.overall_match_score);

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.();
  };

  const handleDriveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
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
            <h3 className="font-semibold truncate">{resume.name}</h3>
            {(jobTitle || companyName) && (
              <p className="text-base-content/70 text-sm truncate">
                {jobTitle && companyName
                  ? `${jobTitle} at ${companyName}`
                  : jobTitle || companyName}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            {resume.drive_file_url && (
              <a
                href={resume.drive_file_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost btn-sm btn-square"
                aria-label="Open in Google Drive"
                onClick={handleDriveClick}
              >
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
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            )}
            {onDelete && (
              <button
                onClick={handleDeleteClick}
                className="btn btn-ghost btn-sm btn-square text-error"
                aria-label="Delete resume"
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
          <span className="badge badge-sm badge-outline">
            {getResumeFormatLabel(resume.format)}
          </span>
          <span>Generated {formatDate(resume.generated_at)}</span>
        </div>

        {/* Match Scores */}
        {(resume.skill_match_score !== null ||
          resume.overall_match_score !== null) && (
          <div className="mt-3 grid grid-cols-2 gap-3">
            {resume.skill_match_score !== null && (
              <div className="bg-base-200 rounded-lg p-3 text-center">
                <p className="text-xs text-base-content/60 mb-1">Skill Match</p>
                <p className={`text-xl font-bold ${skillMatch.color}`}>
                  {skillMatch.text}
                </p>
              </div>
            )}
            {resume.overall_match_score !== null && (
              <div className="bg-base-200 rounded-lg p-3 text-center">
                <p className="text-xs text-base-content/60 mb-1">
                  Overall Match
                </p>
                <p className={`text-xl font-bold ${overallMatch.color}`}>
                  {overallMatch.text}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Template Used */}
        <div className="mt-3 text-xs text-base-content/50">
          Template: {resume.template_used}
        </div>
      </div>
    </div>
  );
}

export default ResumeCard;
