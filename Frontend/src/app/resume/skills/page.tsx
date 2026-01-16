/**
 * Skills management page.
 *
 * Full CRUD interface for managing professional skills.
 */

"use client";

import Link from "next/link";
import { SkillList } from "@/components/resume";

/**
 * Skills page component.
 */
export default function SkillsPage() {
  return (
    <div className="min-h-screen bg-base-200">
      <div className="container mx-auto p-4 lg:p-8">
        {/* Breadcrumbs */}
        <div className="breadcrumbs mb-4 text-sm">
          <ul>
            <li>
              <Link href="/resume">Resume</Link>
            </li>
            <li>Skills</li>
          </ul>
        </div>

        {/* Page Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold lg:text-3xl">Skills</h1>
            <p className="text-base-content/60">
              Manage your professional skills and expertise
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

        {/* Skills List */}
        <SkillList />
      </div>
    </div>
  );
}
