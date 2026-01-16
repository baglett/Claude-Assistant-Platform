/**
 * Resume dashboard page.
 *
 * Overview of profile, skills, job listings, and generated resumes.
 * Provides navigation to detailed management pages.
 */

"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useProfileStore } from "@/stores/profileStore";
import { useResumeStore, formatMatchScore } from "@/stores/resumeStore";

/**
 * Resume dashboard page component.
 */
export default function ResumeDashboard() {
  const {
    profile,
    profileLoading,
    skills,
    skillsLoading,
    workExperiences,
    experiencesLoading,
    educations,
    educationsLoading,
    certifications,
    certificationsLoading,
    fetchProfile,
    fetchSkills,
    fetchWorkExperiences,
    fetchEducations,
    fetchCertifications,
  } = useProfileStore();

  const {
    jobListings,
    jobsLoading,
    generatedResumes,
    resumesLoading,
    fetchJobListings,
    fetchGeneratedResumes,
  } = useResumeStore();

  // Load all data on mount
  useEffect(() => {
    fetchProfile();
    fetchSkills();
    fetchWorkExperiences();
    fetchEducations();
    fetchCertifications();
    fetchJobListings();
    fetchGeneratedResumes();
  }, [
    fetchProfile,
    fetchSkills,
    fetchWorkExperiences,
    fetchEducations,
    fetchCertifications,
    fetchJobListings,
    fetchGeneratedResumes,
  ]);

  const isLoading =
    profileLoading ||
    skillsLoading ||
    experiencesLoading ||
    educationsLoading ||
    certificationsLoading ||
    jobsLoading ||
    resumesLoading;

  // Calculate stats
  const featuredSkills = skills.filter((s) => s.is_featured).length;
  const currentPosition = workExperiences.find((e) => e.is_current);
  const favoriteJobs = jobListings.filter((j) => j.is_favorite).length;
  const avgMatchScore =
    generatedResumes.length > 0
      ? generatedResumes.reduce(
          (acc, r) => acc + (r.overall_match_score || 0),
          0
        ) / generatedResumes.length
      : null;

  return (
    <div className="min-h-screen bg-base-200">
      <div className="container mx-auto p-4 lg:p-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold lg:text-3xl">Resume Dashboard</h1>
          <p className="text-base-content/60">
            Manage your profile, skills, and generate tailored resumes
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <span className="loading loading-spinner loading-lg" />
          </div>
        )}

        {/* Main Content */}
        {!isLoading && (
          <div className="space-y-6">
            {/* Profile Status */}
            {!profile ? (
              <div className="alert alert-warning">
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
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <div>
                  <h3 className="font-bold">Profile Not Set Up</h3>
                  <p className="text-sm">
                    Create your profile to start generating resumes
                  </p>
                </div>
                <Link href="/resume/profile" className="btn btn-sm btn-primary">
                  Set Up Profile
                </Link>
              </div>
            ) : (
              /* Profile Card */
              <div className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h2 className="text-xl font-semibold">
                        {profile.first_name} {profile.last_name}
                      </h2>
                      <p className="text-base-content/70">{profile.email}</p>
                      {currentPosition && (
                        <p className="text-sm text-base-content/60">
                          {currentPosition.job_title} at{" "}
                          {currentPosition.company_name}
                        </p>
                      )}
                    </div>
                    <Link href="/resume/profile" className="btn btn-outline">
                      Edit Profile
                    </Link>
                  </div>
                </div>
              </div>
            )}

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {/* Skills Stat */}
              <Link
                href="/resume/skills"
                className="card bg-base-100 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="card-body p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-5 w-5 text-primary"
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
                    <div>
                      <p className="text-2xl font-bold">{skills.length}</p>
                      <p className="text-sm text-base-content/60">
                        Skills ({featuredSkills} featured)
                      </p>
                    </div>
                  </div>
                </div>
              </Link>

              {/* Experience Stat */}
              <Link
                href="/resume/experience"
                className="card bg-base-100 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="card-body p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary/10">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-5 w-5 text-secondary"
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
                    <div>
                      <p className="text-2xl font-bold">
                        {workExperiences.length}
                      </p>
                      <p className="text-sm text-base-content/60">
                        Work Positions
                      </p>
                    </div>
                  </div>
                </div>
              </Link>

              {/* Jobs Stat */}
              <Link
                href="/resume/jobs"
                className="card bg-base-100 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="card-body p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-5 w-5 text-accent"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                        />
                      </svg>
                    </div>
                    <div>
                      <p className="text-2xl font-bold">{jobListings.length}</p>
                      <p className="text-sm text-base-content/60">
                        Saved Jobs ({favoriteJobs} favorited)
                      </p>
                    </div>
                  </div>
                </div>
              </Link>

              {/* Resumes Stat */}
              <Link
                href="/resume/history"
                className="card bg-base-100 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="card-body p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/10">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-5 w-5 text-success"
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
                    <div>
                      <p className="text-2xl font-bold">
                        {generatedResumes.length}
                      </p>
                      <p className="text-sm text-base-content/60">
                        Generated Resumes
                      </p>
                    </div>
                  </div>
                </div>
              </Link>
            </div>

            {/* Quick Actions */}
            <div className="card bg-base-100 shadow-sm">
              <div className="card-body">
                <h3 className="card-title text-lg">Quick Actions</h3>
                <div className="flex flex-wrap gap-3">
                  <Link href="/resume/profile" className="btn btn-outline">
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
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                      />
                    </svg>
                    Edit Profile
                  </Link>
                  <Link href="/resume/skills" className="btn btn-outline">
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
                    Add Skills
                  </Link>
                  <Link href="/resume/jobs" className="btn btn-outline">
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
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                      />
                    </svg>
                    Scrape Job
                  </Link>
                </div>
              </div>
            </div>

            {/* Additional Stats Row */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Education & Certs */}
              <div className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <h3 className="card-title text-lg">Education & Certifications</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <p className="text-3xl font-bold">{educations.length}</p>
                      <p className="text-sm text-base-content/60">
                        Education Entries
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold">
                        {certifications.length}
                      </p>
                      <p className="text-sm text-base-content/60">
                        Certifications
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Match Score */}
              {avgMatchScore !== null && (
                <div className="card bg-base-100 shadow-sm">
                  <div className="card-body">
                    <h3 className="card-title text-lg">Average Match Score</h3>
                    <div className="flex items-center justify-center">
                      <div
                        className={`radial-progress ${formatMatchScore(avgMatchScore).color}`}
                        style={
                          {
                            "--value": avgMatchScore,
                            "--size": "8rem",
                            "--thickness": "8px",
                          } as React.CSSProperties
                        }
                        role="progressbar"
                      >
                        <span className="text-2xl font-bold">
                          {avgMatchScore.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
