/**
 * Work experience list component with CRUD operations.
 *
 * Displays work history in chronological order with add/edit/delete capabilities.
 */

"use client";

import { useState, useEffect } from "react";
import { useProfileStore } from "@/stores/profileStore";
import type {
  WorkExperience,
  WorkExperienceCreate,
  WorkExperienceUpdate,
  EmploymentType,
} from "@/lib/api/resume";

/**
 * Employment type options.
 */
const EMPLOYMENT_TYPES: { value: EmploymentType; label: string }[] = [
  { value: "full_time", label: "Full-time" },
  { value: "part_time", label: "Part-time" },
  { value: "contract", label: "Contract" },
  { value: "freelance", label: "Freelance" },
  { value: "internship", label: "Internship" },
];

/**
 * Format date for display.
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

/**
 * Format date for input fields.
 */
function formatDateForInput(dateStr: string | null): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toISOString().split("T")[0];
}

/**
 * Experience form component.
 */
interface ExperienceFormProps {
  experience?: WorkExperience | null;
  onSave: (data: WorkExperienceCreate | WorkExperienceUpdate) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
}

function ExperienceForm({
  experience,
  onSave,
  onCancel,
  isLoading,
}: ExperienceFormProps) {
  const [formData, setFormData] = useState<WorkExperienceCreate>({
    company_name: experience?.company_name || "",
    job_title: experience?.job_title || "",
    start_date: formatDateForInput(experience?.start_date || null),
    end_date: formatDateForInput(experience?.end_date || null),
    is_current: experience?.is_current || false,
    employment_type: experience?.employment_type || "full_time",
    company_location: experience?.company_location || null,
    company_url: experience?.company_url || null,
    description: experience?.description || null,
    achievements: experience?.achievements || [],
    skills_used: experience?.skills_used || [],
  });

  const [achievementsInput, setAchievementsInput] = useState(
    experience?.achievements?.join("\n") || ""
  );
  const [skillsInput, setSkillsInput] = useState(
    experience?.skills_used?.join(", ") || ""
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave({
      ...formData,
      end_date: formData.is_current ? null : formData.end_date || null,
      achievements: achievementsInput
        .split("\n")
        .map((a) => a.trim())
        .filter(Boolean),
      skills_used: skillsInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Company Name */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Company Name *</span>
          </label>
          <input
            type="text"
            value={formData.company_name}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, company_name: e.target.value }))
            }
            className="input input-bordered w-full"
            placeholder="Acme Corp"
            required
          />
        </div>

        {/* Job Title */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Job Title *</span>
          </label>
          <input
            type="text"
            value={formData.job_title}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, job_title: e.target.value }))
            }
            className="input input-bordered w-full"
            placeholder="Senior Software Engineer"
            required
          />
        </div>

        {/* Employment Type */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Employment Type</span>
          </label>
          <select
            value={formData.employment_type}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                employment_type: e.target.value as EmploymentType,
              }))
            }
            className="select select-bordered w-full"
          >
            {EMPLOYMENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* Company Location */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Location</span>
          </label>
          <input
            type="text"
            value={formData.company_location || ""}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                company_location: e.target.value || null,
              }))
            }
            className="input input-bordered w-full"
            placeholder="San Francisco, CA"
          />
        </div>

        {/* Start Date */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Start Date *</span>
          </label>
          <input
            type="date"
            value={formData.start_date}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, start_date: e.target.value }))
            }
            className="input input-bordered w-full"
            required
          />
        </div>

        {/* End Date */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">End Date</span>
          </label>
          <input
            type="date"
            value={formData.end_date || ""}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                end_date: e.target.value || null,
              }))
            }
            className="input input-bordered w-full"
            disabled={formData.is_current}
          />
        </div>
      </div>

      {/* Current Position */}
      <div className="form-control">
        <label className="label cursor-pointer justify-start gap-3">
          <input
            type="checkbox"
            checked={formData.is_current}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                is_current: e.target.checked,
                end_date: e.target.checked ? null : prev.end_date,
              }))
            }
            className="checkbox checkbox-primary"
          />
          <span className="label-text">I currently work here</span>
        </label>
      </div>

      {/* Company URL */}
      <div className="form-control">
        <label className="label">
          <span className="label-text">Company Website</span>
        </label>
        <input
          type="url"
          value={formData.company_url || ""}
          onChange={(e) =>
            setFormData((prev) => ({
              ...prev,
              company_url: e.target.value || null,
            }))
          }
          className="input input-bordered w-full"
          placeholder="https://acme.com"
        />
      </div>

      {/* Description */}
      <div className="form-control">
        <label className="label">
          <span className="label-text">Description</span>
        </label>
        <textarea
          value={formData.description || ""}
          onChange={(e) =>
            setFormData((prev) => ({
              ...prev,
              description: e.target.value || null,
            }))
          }
          className="textarea textarea-bordered h-24 w-full"
          placeholder="Brief description of your role and responsibilities..."
        />
      </div>

      {/* Achievements */}
      <div className="form-control">
        <label className="label">
          <span className="label-text">Key Achievements (one per line)</span>
        </label>
        <textarea
          value={achievementsInput}
          onChange={(e) => setAchievementsInput(e.target.value)}
          className="textarea textarea-bordered h-32 w-full"
          placeholder="Led a team of 5 engineers&#10;Reduced API latency by 40%&#10;Shipped new authentication system"
        />
        <label className="label">
          <span className="label-text-alt text-base-content/60">
            Use action verbs and quantify results when possible
          </span>
        </label>
      </div>

      {/* Skills Used */}
      <div className="form-control">
        <label className="label">
          <span className="label-text">Skills Used (comma-separated)</span>
        </label>
        <input
          type="text"
          value={skillsInput}
          onChange={(e) => setSkillsInput(e.target.value)}
          className="input input-bordered w-full"
          placeholder="Python, AWS, PostgreSQL, React"
        />
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="btn btn-ghost">
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={isLoading}>
          {isLoading ? (
            <>
              <span className="loading loading-spinner loading-sm" />
              Saving...
            </>
          ) : experience ? (
            "Update Experience"
          ) : (
            "Add Experience"
          )}
        </button>
      </div>
    </form>
  );
}

/**
 * Work experience list component.
 */
export function ExperienceList() {
  const {
    workExperiences,
    experiencesLoading,
    experiencesError,
    fetchWorkExperiences,
    addWorkExperience,
    editWorkExperience,
    removeWorkExperience,
  } = useProfileStore();

  const [showForm, setShowForm] = useState(false);
  const [editingExperience, setEditingExperience] =
    useState<WorkExperience | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Load experiences on mount
  useEffect(() => {
    fetchWorkExperiences();
  }, [fetchWorkExperiences]);

  const handleAddExperience = async (data: WorkExperienceCreate) => {
    const result = await addWorkExperience(data);
    if (result) {
      setShowForm(false);
    }
  };

  const handleEditExperience = async (data: WorkExperienceUpdate) => {
    if (!editingExperience) return;
    const result = await editWorkExperience(editingExperience.id, data);
    if (result) {
      setEditingExperience(null);
    }
  };

  const handleDeleteExperience = async (id: string) => {
    const success = await removeWorkExperience(id);
    if (success) {
      setDeleteConfirmId(null);
    }
  };

  // Sort experiences by start date (most recent first)
  const sortedExperiences = [...workExperiences].sort(
    (a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime()
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Work Experience</h2>
          <p className="text-base-content/60">
            Your professional work history
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn btn-primary"
          disabled={showForm || editingExperience !== null}
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
              d="M12 4v16m8-8H4"
            />
          </svg>
          Add Experience
        </button>
      </div>

      {/* Error Alert */}
      {experiencesError && (
        <div className="alert alert-error">
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
          <span>{experiencesError}</span>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg">Add Work Experience</h3>
            <ExperienceForm
              onSave={handleAddExperience}
              onCancel={() => setShowForm(false)}
              isLoading={experiencesLoading}
            />
          </div>
        </div>
      )}

      {/* Edit Form */}
      {editingExperience && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg">Edit Experience</h3>
            <ExperienceForm
              experience={editingExperience}
              onSave={handleEditExperience}
              onCancel={() => setEditingExperience(null)}
              isLoading={experiencesLoading}
            />
          </div>
        </div>
      )}

      {/* Loading State */}
      {experiencesLoading && !showForm && !editingExperience && (
        <div className="flex justify-center py-8">
          <span className="loading loading-spinner loading-lg" />
        </div>
      )}

      {/* Empty State */}
      {!experiencesLoading && workExperiences.length === 0 && (
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
                d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="mb-2 text-lg font-semibold">No work experience yet</h3>
          <p className="mb-4 text-base-content/60">
            Add your work history to build your resume
          </p>
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            Add Your First Position
          </button>
        </div>
      )}

      {/* Experience Timeline */}
      {!experiencesLoading && sortedExperiences.length > 0 && (
        <div className="space-y-4">
          {sortedExperiences.map((exp) => (
            <div
              key={exp.id}
              className="card bg-base-100 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="card-body">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold">{exp.job_title}</h3>
                      {exp.is_current && (
                        <span className="badge badge-success badge-sm">
                          Current
                        </span>
                      )}
                    </div>
                    <p className="text-base-content/70">
                      {exp.company_name}
                      {exp.company_location && ` · ${exp.company_location}`}
                    </p>
                    <p className="text-sm text-base-content/60">
                      {formatDate(exp.start_date)} -{" "}
                      {exp.is_current
                        ? "Present"
                        : exp.end_date
                          ? formatDate(exp.end_date)
                          : "Present"}
                      {" · "}
                      {EMPLOYMENT_TYPES.find((t) => t.value === exp.employment_type)?.label}
                    </p>

                    {exp.description && (
                      <p className="mt-3 text-base-content/80">
                        {exp.description}
                      </p>
                    )}

                    {exp.achievements.length > 0 && (
                      <ul className="mt-3 list-inside list-disc space-y-1 text-sm">
                        {exp.achievements.map((achievement, idx) => (
                          <li key={idx} className="text-base-content/80">
                            {achievement}
                          </li>
                        ))}
                      </ul>
                    )}

                    {exp.skills_used.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {exp.skills_used.map((skill, idx) => (
                          <span
                            key={idx}
                            className="badge badge-outline badge-sm"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-1">
                    <button
                      onClick={() => setEditingExperience(exp)}
                      className="btn btn-ghost btn-sm btn-square"
                      aria-label="Edit experience"
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
                    <button
                      onClick={() => setDeleteConfirmId(exp.id)}
                      className="btn btn-ghost btn-sm btn-square text-error"
                      aria-label="Delete experience"
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
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="modal modal-open">
          <div className="modal-box">
            <h3 className="text-lg font-bold">Delete Experience</h3>
            <p className="py-4">
              Are you sure you want to delete this work experience? This action
              cannot be undone.
            </p>
            <div className="modal-action">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="btn btn-ghost"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteExperience(deleteConfirmId)}
                className="btn btn-error"
              >
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
  );
}

export default ExperienceList;
