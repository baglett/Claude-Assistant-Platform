/**
 * Profile form component for editing user profile information.
 *
 * Displays and allows editing of personal information, contact details,
 * and professional links. Auto-saves on form submission.
 */

"use client";

import { useState, useEffect } from "react";
import { useProfileStore } from "@/stores/profileStore";
import type { ProfileCreateUpdate } from "@/lib/api/resume";

/**
 * ProfileForm component props.
 */
interface ProfileFormProps {
  /** Callback after successful save */
  onSaved?: () => void;
}

/**
 * Profile form component.
 *
 * @param props - Component props
 * @returns Profile form JSX
 */
export function ProfileForm({ onSaved }: ProfileFormProps) {
  const { profile, profileLoading, profileError, fetchProfile, saveProfile } =
    useProfileStore();

  // Form state
  const [formData, setFormData] = useState<ProfileCreateUpdate>({
    first_name: "",
    last_name: "",
    email: "",
    phone: null,
    city: null,
    state: null,
    country: "United States",
    linkedin_url: null,
    github_url: null,
    portfolio_url: null,
    personal_website: null,
    professional_summary: null,
  });

  // Load profile data on mount
  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  // Populate form when profile loads
  useEffect(() => {
    if (profile) {
      setFormData({
        first_name: profile.first_name,
        last_name: profile.last_name,
        email: profile.email,
        phone: profile.phone,
        city: profile.city,
        state: profile.state,
        country: profile.country,
        linkedin_url: profile.linkedin_url,
        github_url: profile.github_url,
        portfolio_url: profile.portfolio_url,
        personal_website: profile.personal_website,
        professional_summary: profile.professional_summary,
      });
    }
  }, [profile]);

  /**
   * Handle form field changes.
   */
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value || null,
    }));
  };

  /**
   * Handle form submission.
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await saveProfile(formData);
    if (result && onSaved) {
      onSaved();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Error Alert */}
      {profileError && (
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
          <span>{profileError}</span>
        </div>
      )}

      {/* Personal Information */}
      <div className="card bg-base-100 shadow-sm">
        <div className="card-body">
          <h3 className="card-title text-lg">Personal Information</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* First Name */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">First Name *</span>
              </label>
              <input
                type="text"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="John"
                required
              />
            </div>

            {/* Last Name */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Last Name *</span>
              </label>
              <input
                type="text"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="Doe"
                required
              />
            </div>

            {/* Email */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Email *</span>
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="john.doe@example.com"
                required
              />
            </div>

            {/* Phone */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Phone</span>
              </label>
              <input
                type="tel"
                name="phone"
                value={formData.phone || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="+1 (555) 123-4567"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Location */}
      <div className="card bg-base-100 shadow-sm">
        <div className="card-body">
          <h3 className="card-title text-lg">Location</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {/* City */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">City</span>
              </label>
              <input
                type="text"
                name="city"
                value={formData.city || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="San Francisco"
              />
            </div>

            {/* State */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">State</span>
              </label>
              <input
                type="text"
                name="state"
                value={formData.state || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="California"
              />
            </div>

            {/* Country */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Country</span>
              </label>
              <input
                type="text"
                name="country"
                value={formData.country || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="United States"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Professional Links */}
      <div className="card bg-base-100 shadow-sm">
        <div className="card-body">
          <h3 className="card-title text-lg">Professional Links</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* LinkedIn */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">LinkedIn URL</span>
              </label>
              <input
                type="url"
                name="linkedin_url"
                value={formData.linkedin_url || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="https://linkedin.com/in/johndoe"
              />
            </div>

            {/* GitHub */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">GitHub URL</span>
              </label>
              <input
                type="url"
                name="github_url"
                value={formData.github_url || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="https://github.com/johndoe"
              />
            </div>

            {/* Portfolio */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Portfolio URL</span>
              </label>
              <input
                type="url"
                name="portfolio_url"
                value={formData.portfolio_url || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="https://johndoe.dev"
              />
            </div>

            {/* Personal Website */}
            <div className="form-control">
              <label className="label">
                <span className="label-text">Personal Website</span>
              </label>
              <input
                type="url"
                name="personal_website"
                value={formData.personal_website || ""}
                onChange={handleChange}
                className="input input-bordered w-full"
                placeholder="https://johndoe.com"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Professional Summary */}
      <div className="card bg-base-100 shadow-sm">
        <div className="card-body">
          <h3 className="card-title text-lg">Professional Summary</h3>
          <div className="form-control">
            <label className="label">
              <span className="label-text">
                Default summary for your resumes
              </span>
            </label>
            <textarea
              name="professional_summary"
              value={formData.professional_summary || ""}
              onChange={handleChange}
              className="textarea textarea-bordered h-32 w-full"
              placeholder="Senior software engineer with 8+ years of experience building scalable web applications..."
            />
            <label className="label">
              <span className="label-text-alt text-base-content/60">
                This summary will be used as a starting point when generating
                resumes. It can be customized per job.
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex justify-end gap-2">
        <button
          type="submit"
          className="btn btn-primary"
          disabled={profileLoading}
        >
          {profileLoading ? (
            <>
              <span className="loading loading-spinner loading-sm" />
              Saving...
            </>
          ) : (
            "Save Profile"
          )}
        </button>
      </div>
    </form>
  );
}

export default ProfileForm;
