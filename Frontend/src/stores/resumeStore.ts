/**
 * Resume state management using Zustand.
 *
 * Manages:
 * - Job listings (scraped job postings)
 * - Generated resumes
 */

import { create } from "zustand";
import {
  getJobListings,
  getJobListing,
  scrapeJobListing,
  updateJobListing,
  deleteJobListing,
  getGeneratedResumes,
  getGeneratedResume,
  deleteGeneratedResume,
  type JobListing,
  type JobListingUpdate,
  type JobListingFilters,
  type ApplicationStatus,
  type GeneratedResume,
  type GeneratedResumeFilters,
  type ResumeFormat,
} from "@/lib/api/resume";

/**
 * Resume store state interface.
 */
interface ResumeState {
  // Job Listings
  /** List of job listings */
  jobListings: JobListing[];
  /** Current job listing filters */
  jobFilters: JobListingFilters;
  /** Total count of job listings */
  jobTotal: number;
  /** Whether there are more pages */
  jobHasNext: boolean;
  /** Whether job listings are loading */
  jobsLoading: boolean;
  /** Jobs error message */
  jobsError: string | null;
  /** Currently selected job listing */
  selectedJob: JobListing | null;
  /** Whether scraping is in progress */
  scraping: boolean;

  // Generated Resumes
  /** List of generated resumes */
  generatedResumes: GeneratedResume[];
  /** Current resume filters */
  resumeFilters: GeneratedResumeFilters;
  /** Total count of generated resumes */
  resumeTotal: number;
  /** Whether there are more pages */
  resumeHasNext: boolean;
  /** Whether resumes are loading */
  resumesLoading: boolean;
  /** Resumes error message */
  resumesError: string | null;
  /** Currently selected resume */
  selectedResume: GeneratedResume | null;

  // Job Listing actions
  /** Fetch job listings with filters */
  fetchJobListings: () => Promise<void>;
  /** Set job listing filters */
  setJobFilters: (filters: Partial<JobListingFilters>) => void;
  /** Scrape a job listing from URL */
  scrapeJob: (url: string) => Promise<JobListing | null>;
  /** Update a job listing */
  editJobListing: (id: string, data: JobListingUpdate) => Promise<JobListing | null>;
  /** Delete a job listing */
  removeJobListing: (id: string) => Promise<boolean>;
  /** Toggle job favorite status */
  toggleJobFavorite: (id: string) => Promise<boolean>;
  /** Select a job listing */
  selectJob: (job: JobListing | null) => void;
  /** Fetch a single job by ID */
  fetchJob: (id: string) => Promise<JobListing | null>;

  // Generated Resume actions
  /** Fetch generated resumes with filters */
  fetchGeneratedResumes: () => Promise<void>;
  /** Set resume filters */
  setResumeFilters: (filters: Partial<GeneratedResumeFilters>) => void;
  /** Delete a generated resume */
  removeGeneratedResume: (id: string) => Promise<boolean>;
  /** Select a generated resume */
  selectResume: (resume: GeneratedResume | null) => void;
  /** Fetch a single resume by ID */
  fetchResume: (id: string) => Promise<GeneratedResume | null>;

  /** Reset all state */
  reset: () => void;
}

/**
 * Default filter values.
 */
const defaultJobFilters: JobListingFilters = {
  page: 1,
  page_size: 10,
};

const defaultResumeFilters: GeneratedResumeFilters = {
  page: 1,
  page_size: 10,
};

/**
 * Initial state values.
 */
const initialState = {
  // Job Listings
  jobListings: [],
  jobFilters: defaultJobFilters,
  jobTotal: 0,
  jobHasNext: false,
  jobsLoading: false,
  jobsError: null,
  selectedJob: null,
  scraping: false,

  // Generated Resumes
  generatedResumes: [],
  resumeFilters: defaultResumeFilters,
  resumeTotal: 0,
  resumeHasNext: false,
  resumesLoading: false,
  resumesError: null,
  selectedResume: null,
};

/**
 * Zustand store for job listings and generated resumes.
 */
export const useResumeStore = create<ResumeState>()((set, get) => ({
  ...initialState,

  // ==========================================================================
  // Job Listing Actions
  // ==========================================================================

  /**
   * Fetch job listings with current filters.
   */
  fetchJobListings: async () => {
    const { jobFilters } = get();
    set({ jobsLoading: true, jobsError: null });

    try {
      const response = await getJobListings(jobFilters);
      set({
        jobListings: response.items,
        jobTotal: response.total,
        jobHasNext: response.has_next,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch job listings";
      set({ jobsError: message });
      console.error("Job listings fetch error:", error);
    } finally {
      set({ jobsLoading: false });
    }
  },

  /**
   * Set job listing filters and refetch.
   *
   * @param filters - Partial filter updates
   */
  setJobFilters: (filters: Partial<JobListingFilters>) => {
    set((state) => ({
      jobFilters: { ...state.jobFilters, ...filters },
    }));
    get().fetchJobListings();
  },

  /**
   * Scrape a job listing from URL.
   *
   * @param url - Job listing URL
   * @returns Scraped job listing or null on error
   */
  scrapeJob: async (url: string) => {
    set({ scraping: true, jobsError: null });

    try {
      const job = await scrapeJobListing(url);
      // Refresh the list
      await get().fetchJobListings();
      return job;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to scrape job listing";
      set({ jobsError: message });
      console.error("Job scrape error:", error);
      return null;
    } finally {
      set({ scraping: false });
    }
  },

  /**
   * Update a job listing.
   *
   * @param id - Job listing UUID
   * @param data - Fields to update
   * @returns Updated job listing or null on error
   */
  editJobListing: async (id: string, data: JobListingUpdate) => {
    set({ jobsError: null });

    try {
      const updated = await updateJobListing(id, data);
      // Update local state optimistically
      set((state) => ({
        jobListings: state.jobListings.map((j) => (j.id === id ? updated : j)),
        selectedJob:
          state.selectedJob?.id === id ? updated : state.selectedJob,
      }));
      return updated;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to update job listing";
      set({ jobsError: message });
      console.error("Job listing update error:", error);
      return null;
    }
  },

  /**
   * Delete a job listing.
   *
   * @param id - Job listing UUID
   * @returns True if deleted successfully
   */
  removeJobListing: async (id: string) => {
    set({ jobsError: null });

    try {
      await deleteJobListing(id);
      // Remove from local state
      set((state) => ({
        jobListings: state.jobListings.filter((j) => j.id !== id),
        jobTotal: state.jobTotal - 1,
        selectedJob: state.selectedJob?.id === id ? null : state.selectedJob,
      }));
      return true;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to delete job listing";
      set({ jobsError: message });
      console.error("Job listing delete error:", error);
      return false;
    }
  },

  /**
   * Toggle job favorite status.
   *
   * @param id - Job listing UUID
   * @returns True if toggled successfully
   */
  toggleJobFavorite: async (id: string) => {
    const { jobListings } = get();
    const job = jobListings.find((j) => j.id === id);
    if (!job) return false;

    const result = await get().editJobListing(id, {
      is_favorite: !job.is_favorite,
    });
    return result !== null;
  },

  /**
   * Select a job listing.
   *
   * @param job - Job listing to select, or null to deselect
   */
  selectJob: (job: JobListing | null) => {
    set({ selectedJob: job });
  },

  /**
   * Fetch a single job listing by ID.
   *
   * @param id - Job listing UUID
   * @returns Job listing or null on error
   */
  fetchJob: async (id: string) => {
    try {
      const job = await getJobListing(id);
      set({ selectedJob: job });
      return job;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch job listing";
      set({ jobsError: message });
      console.error("Job listing fetch error:", error);
      return null;
    }
  },

  // ==========================================================================
  // Generated Resume Actions
  // ==========================================================================

  /**
   * Fetch generated resumes with current filters.
   */
  fetchGeneratedResumes: async () => {
    const { resumeFilters } = get();
    set({ resumesLoading: true, resumesError: null });

    try {
      const response = await getGeneratedResumes(resumeFilters);
      set({
        generatedResumes: response.items,
        resumeTotal: response.total,
        resumeHasNext: response.has_next,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to fetch generated resumes";
      set({ resumesError: message });
      console.error("Generated resumes fetch error:", error);
    } finally {
      set({ resumesLoading: false });
    }
  },

  /**
   * Set resume filters and refetch.
   *
   * @param filters - Partial filter updates
   */
  setResumeFilters: (filters: Partial<GeneratedResumeFilters>) => {
    set((state) => ({
      resumeFilters: { ...state.resumeFilters, ...filters },
    }));
    get().fetchGeneratedResumes();
  },

  /**
   * Delete a generated resume.
   *
   * @param id - Generated resume UUID
   * @returns True if deleted successfully
   */
  removeGeneratedResume: async (id: string) => {
    set({ resumesError: null });

    try {
      await deleteGeneratedResume(id);
      // Remove from local state
      set((state) => ({
        generatedResumes: state.generatedResumes.filter((r) => r.id !== id),
        resumeTotal: state.resumeTotal - 1,
        selectedResume:
          state.selectedResume?.id === id ? null : state.selectedResume,
      }));
      return true;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to delete generated resume";
      set({ resumesError: message });
      console.error("Generated resume delete error:", error);
      return false;
    }
  },

  /**
   * Select a generated resume.
   *
   * @param resume - Resume to select, or null to deselect
   */
  selectResume: (resume: GeneratedResume | null) => {
    set({ selectedResume: resume });
  },

  /**
   * Fetch a single generated resume by ID.
   *
   * @param id - Generated resume UUID
   * @returns Generated resume or null on error
   */
  fetchResume: async (id: string) => {
    try {
      const resume = await getGeneratedResume(id);
      set({ selectedResume: resume });
      return resume;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to fetch generated resume";
      set({ resumesError: message });
      console.error("Generated resume fetch error:", error);
      return null;
    }
  },

  /**
   * Reset all state to initial values.
   */
  reset: () => set(initialState),
}));

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get display label for application status.
 */
export function getApplicationStatusLabel(status: ApplicationStatus): string {
  const labels: Record<ApplicationStatus, string> = {
    not_applied: "Not Applied",
    applied: "Applied",
    interviewing: "Interviewing",
    offered: "Offered",
    rejected: "Rejected",
    withdrawn: "Withdrawn",
  };
  return labels[status];
}

/**
 * Get color class for application status.
 */
export function getApplicationStatusColor(status: ApplicationStatus): string {
  const colors: Record<ApplicationStatus, string> = {
    not_applied: "badge-ghost",
    applied: "badge-info",
    interviewing: "badge-warning",
    offered: "badge-success",
    rejected: "badge-error",
    withdrawn: "badge-ghost",
  };
  return colors[status];
}

/**
 * Get display label for resume format.
 */
export function getResumeFormatLabel(format: ResumeFormat): string {
  const labels: Record<ResumeFormat, string> = {
    pdf: "PDF",
    docx: "Word (DOCX)",
  };
  return labels[format];
}

/**
 * Format a salary range for display.
 *
 * @param min - Minimum salary
 * @param max - Maximum salary
 * @param currency - Currency code
 * @returns Formatted salary string
 */
export function formatSalaryRange(
  min: number | null,
  max: number | null,
  currency: string = "USD"
): string {
  if (!min && !max) return "Not specified";

  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  });

  if (min && max) {
    return `${formatter.format(min)} - ${formatter.format(max)}`;
  } else if (min) {
    return `${formatter.format(min)}+`;
  } else if (max) {
    return `Up to ${formatter.format(max)}`;
  }

  return "Not specified";
}

/**
 * Format a match score for display.
 *
 * @param score - Match score (0-100)
 * @returns Formatted score string with color class
 */
export function formatMatchScore(score: number | null): {
  text: string;
  color: string;
} {
  if (score === null) {
    return { text: "N/A", color: "text-base-content/50" };
  }

  if (score >= 80) {
    return { text: `${score.toFixed(0)}%`, color: "text-success" };
  } else if (score >= 60) {
    return { text: `${score.toFixed(0)}%`, color: "text-warning" };
  } else {
    return { text: `${score.toFixed(0)}%`, color: "text-error" };
  }
}
