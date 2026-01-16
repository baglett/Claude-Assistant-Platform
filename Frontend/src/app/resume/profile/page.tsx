/**
 * Profile management page.
 *
 * Full-page editor for user profile information.
 */

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ProfileForm } from "@/components/resume";

/**
 * Profile page component.
 */
export default function ProfilePage() {
  const router = useRouter();

  const handleSaved = () => {
    // Show a brief toast or navigate back
    router.push("/resume");
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
            <li>Profile</li>
          </ul>
        </div>

        {/* Page Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold lg:text-3xl">Edit Profile</h1>
            <p className="text-base-content/60">
              Update your personal and professional information
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

        {/* Profile Form */}
        <ProfileForm onSaved={handleSaved} />
      </div>
    </div>
  );
}
