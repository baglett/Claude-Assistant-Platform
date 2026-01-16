/**
 * Skill list component with CRUD operations.
 *
 * Displays all user skills in a filterable, editable list.
 * Supports adding, editing, and deleting skills.
 */

"use client";

import { useState, useEffect } from "react";
import {
  useProfileStore,
  getCategoryLabel,
  getProficiencyLabel,
  getProficiencyColor,
} from "@/stores/profileStore";
import type {
  Skill,
  SkillCreate,
  SkillUpdate,
  SkillCategory,
  SkillProficiency,
} from "@/lib/api/resume";

/**
 * Available skill categories.
 */
const SKILL_CATEGORIES: SkillCategory[] = [
  "programming_language",
  "framework",
  "database",
  "cloud",
  "devops",
  "soft_skill",
  "tool",
  "methodology",
  "other",
];

/**
 * Available proficiency levels.
 */
const PROFICIENCY_LEVELS: SkillProficiency[] = [
  "beginner",
  "intermediate",
  "advanced",
  "expert",
];

/**
 * Skill form component for adding/editing skills.
 */
interface SkillFormProps {
  skill?: Skill | null;
  onSave: (data: SkillCreate | SkillUpdate) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
}

function SkillForm({ skill, onSave, onCancel, isLoading }: SkillFormProps) {
  const [formData, setFormData] = useState<SkillCreate>({
    name: skill?.name || "",
    category: skill?.category || "other",
    proficiency: skill?.proficiency || "intermediate",
    years_experience: skill?.years_experience || null,
    keywords: skill?.keywords || [],
    is_featured: skill?.is_featured || false,
  });

  const [keywordsInput, setKeywordsInput] = useState(
    skill?.keywords?.join(", ") || ""
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave({
      ...formData,
      keywords: keywordsInput
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Name */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Skill Name *</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, name: e.target.value }))
            }
            className="input input-bordered w-full"
            placeholder="Python"
            required
          />
        </div>

        {/* Category */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Category</span>
          </label>
          <select
            value={formData.category}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                category: e.target.value as SkillCategory,
              }))
            }
            className="select select-bordered w-full"
          >
            {SKILL_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {getCategoryLabel(cat)}
              </option>
            ))}
          </select>
        </div>

        {/* Proficiency */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Proficiency</span>
          </label>
          <select
            value={formData.proficiency}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                proficiency: e.target.value as SkillProficiency,
              }))
            }
            className="select select-bordered w-full"
          >
            {PROFICIENCY_LEVELS.map((level) => (
              <option key={level} value={level}>
                {getProficiencyLabel(level)}
              </option>
            ))}
          </select>
        </div>

        {/* Years Experience */}
        <div className="form-control">
          <label className="label">
            <span className="label-text">Years of Experience</span>
          </label>
          <input
            type="number"
            step="0.5"
            min="0"
            max="50"
            value={formData.years_experience || ""}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                years_experience: e.target.value
                  ? parseFloat(e.target.value)
                  : null,
              }))
            }
            className="input input-bordered w-full"
            placeholder="5"
          />
        </div>
      </div>

      {/* Keywords */}
      <div className="form-control">
        <label className="label">
          <span className="label-text">Keywords (comma-separated)</span>
        </label>
        <input
          type="text"
          value={keywordsInput}
          onChange={(e) => setKeywordsInput(e.target.value)}
          className="input input-bordered w-full"
          placeholder="python3, py, python programming"
        />
        <label className="label">
          <span className="label-text-alt text-base-content/60">
            Alternative names for job matching
          </span>
        </label>
      </div>

      {/* Featured */}
      <div className="form-control">
        <label className="label cursor-pointer justify-start gap-3">
          <input
            type="checkbox"
            checked={formData.is_featured}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                is_featured: e.target.checked,
              }))
            }
            className="checkbox checkbox-primary"
          />
          <span className="label-text">Featured skill</span>
        </label>
        <label className="label">
          <span className="label-text-alt text-base-content/60">
            Featured skills are prioritized in resume generation
          </span>
        </label>
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
          ) : skill ? (
            "Update Skill"
          ) : (
            "Add Skill"
          )}
        </button>
      </div>
    </form>
  );
}

/**
 * Skill list component.
 */
export function SkillList() {
  const {
    skills,
    skillFilters,
    skillsLoading,
    skillsError,
    fetchSkills,
    setSkillFilters,
    addSkill,
    editSkill,
    removeSkill,
  } = useProfileStore();

  const [showForm, setShowForm] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Load skills on mount
  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const handleAddSkill = async (data: SkillCreate) => {
    const result = await addSkill(data);
    if (result) {
      setShowForm(false);
    }
  };

  const handleEditSkill = async (data: SkillUpdate) => {
    if (!editingSkill) return;
    const result = await editSkill(editingSkill.id, data);
    if (result) {
      setEditingSkill(null);
    }
  };

  const handleDeleteSkill = async (id: string) => {
    const success = await removeSkill(id);
    if (success) {
      setDeleteConfirmId(null);
    }
  };

  // Group skills by category
  const groupedSkills = skills.reduce(
    (acc, skill) => {
      if (!acc[skill.category]) {
        acc[skill.category] = [];
      }
      acc[skill.category].push(skill);
      return acc;
    },
    {} as Record<SkillCategory, Skill[]>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Skills</h2>
          <p className="text-base-content/60">
            Manage your professional skills
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn btn-primary"
          disabled={showForm || editingSkill !== null}
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
          Add Skill
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <select
          value={skillFilters.category || ""}
          onChange={(e) =>
            setSkillFilters({
              category: (e.target.value as SkillCategory) || undefined,
            })
          }
          className="select select-bordered select-sm"
        >
          <option value="">All Categories</option>
          {SKILL_CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {getCategoryLabel(cat)}
            </option>
          ))}
        </select>

        <select
          value={skillFilters.proficiency || ""}
          onChange={(e) =>
            setSkillFilters({
              proficiency: (e.target.value as SkillProficiency) || undefined,
            })
          }
          className="select select-bordered select-sm"
        >
          <option value="">All Levels</option>
          {PROFICIENCY_LEVELS.map((level) => (
            <option key={level} value={level}>
              {getProficiencyLabel(level)}
            </option>
          ))}
        </select>

        <label className="label cursor-pointer gap-2">
          <input
            type="checkbox"
            checked={skillFilters.is_featured || false}
            onChange={(e) =>
              setSkillFilters({
                is_featured: e.target.checked || undefined,
              })
            }
            className="checkbox checkbox-sm checkbox-primary"
          />
          <span className="label-text">Featured only</span>
        </label>
      </div>

      {/* Error Alert */}
      {skillsError && (
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
          <span>{skillsError}</span>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg">Add New Skill</h3>
            <SkillForm
              onSave={handleAddSkill}
              onCancel={() => setShowForm(false)}
              isLoading={skillsLoading}
            />
          </div>
        </div>
      )}

      {/* Edit Form */}
      {editingSkill && (
        <div className="card bg-base-100 shadow-sm">
          <div className="card-body">
            <h3 className="card-title text-lg">Edit Skill</h3>
            <SkillForm
              skill={editingSkill}
              onSave={handleEditSkill}
              onCancel={() => setEditingSkill(null)}
              isLoading={skillsLoading}
            />
          </div>
        </div>
      )}

      {/* Loading State */}
      {skillsLoading && !showForm && !editingSkill && (
        <div className="flex justify-center py-8">
          <span className="loading loading-spinner loading-lg" />
        </div>
      )}

      {/* Empty State */}
      {!skillsLoading && skills.length === 0 && (
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
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <h3 className="mb-2 text-lg font-semibold">No skills yet</h3>
          <p className="mb-4 text-base-content/60">
            Add your professional skills to get started
          </p>
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            Add Your First Skill
          </button>
        </div>
      )}

      {/* Skills Grid by Category */}
      {!skillsLoading &&
        skills.length > 0 &&
        Object.entries(groupedSkills).map(([category, categorySkills]) => (
          <div key={category} className="space-y-3">
            <h3 className="text-sm font-medium text-base-content/60">
              {getCategoryLabel(category as SkillCategory)} (
              {categorySkills.length})
            </h3>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
              {categorySkills.map((skill) => (
                <div
                  key={skill.id}
                  className="card bg-base-100 shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="card-body p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium">{skill.name}</h4>
                          {skill.is_featured && (
                            <span className="badge badge-accent badge-sm">
                              Featured
                            </span>
                          )}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          <span
                            className={`badge badge-sm ${getProficiencyColor(skill.proficiency)}`}
                          >
                            {getProficiencyLabel(skill.proficiency)}
                          </span>
                          {skill.years_experience && (
                            <span className="text-sm text-base-content/60">
                              {skill.years_experience} years
                            </span>
                          )}
                        </div>
                        {skill.keywords.length > 0 && (
                          <p className="mt-2 text-xs text-base-content/50">
                            Keywords: {skill.keywords.join(", ")}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => setEditingSkill(skill)}
                          className="btn btn-ghost btn-sm btn-square"
                          aria-label="Edit skill"
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
                          onClick={() => setDeleteConfirmId(skill.id)}
                          className="btn btn-ghost btn-sm btn-square text-error"
                          aria-label="Delete skill"
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
          </div>
        ))}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="modal modal-open">
          <div className="modal-box">
            <h3 className="text-lg font-bold">Delete Skill</h3>
            <p className="py-4">
              Are you sure you want to delete this skill? This action cannot be
              undone.
            </p>
            <div className="modal-action">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="btn btn-ghost"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteSkill(deleteConfirmId)}
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

export default SkillList;
