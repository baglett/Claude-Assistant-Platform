/**
 * Profile state management using Zustand.
 *
 * Manages user profile state including:
 * - Personal information
 * - Skills
 * - Work experience
 * - Education
 * - Certifications
 */

import { create } from "zustand";
import {
  getProfile,
  saveProfile,
  getSkills,
  createSkill,
  updateSkill,
  deleteSkill,
  getWorkExperiences,
  createWorkExperience,
  updateWorkExperience,
  deleteWorkExperience,
  getEducations,
  createEducation,
  updateEducation,
  deleteEducation,
  getCertifications,
  createCertification,
  updateCertification,
  deleteCertification,
  type Profile,
  type ProfileCreateUpdate,
  type Skill,
  type SkillCreate,
  type SkillUpdate,
  type SkillFilters,
  type SkillCategory,
  type SkillProficiency,
  type WorkExperience,
  type WorkExperienceCreate,
  type WorkExperienceUpdate,
  type Education,
  type EducationCreate,
  type EducationUpdate,
  type Certification,
  type CertificationCreate,
  type CertificationUpdate,
} from "@/lib/api/resume";

/**
 * Profile store state interface.
 */
interface ProfileState {
  // Profile
  /** User profile data */
  profile: Profile | null;
  /** Whether profile is loading */
  profileLoading: boolean;
  /** Profile error message */
  profileError: string | null;

  // Skills
  /** List of skills */
  skills: Skill[];
  /** Current skill filters */
  skillFilters: SkillFilters;
  /** Whether skills are loading */
  skillsLoading: boolean;
  /** Skills error message */
  skillsError: string | null;

  // Work Experience
  /** List of work experiences */
  workExperiences: WorkExperience[];
  /** Whether work experiences are loading */
  experiencesLoading: boolean;
  /** Experiences error message */
  experiencesError: string | null;

  // Education
  /** List of education entries */
  educations: Education[];
  /** Whether educations are loading */
  educationsLoading: boolean;
  /** Educations error message */
  educationsError: string | null;

  // Certifications
  /** List of certifications */
  certifications: Certification[];
  /** Whether certifications are loading */
  certificationsLoading: boolean;
  /** Certifications error message */
  certificationsError: string | null;

  // Profile actions
  /** Fetch user profile */
  fetchProfile: () => Promise<void>;
  /** Save user profile */
  saveProfile: (data: ProfileCreateUpdate) => Promise<Profile | null>;

  // Skill actions
  /** Fetch skills with filters */
  fetchSkills: () => Promise<void>;
  /** Set skill filters */
  setSkillFilters: (filters: Partial<SkillFilters>) => void;
  /** Create a new skill */
  addSkill: (data: SkillCreate) => Promise<Skill | null>;
  /** Update an existing skill */
  editSkill: (id: string, data: SkillUpdate) => Promise<Skill | null>;
  /** Delete a skill */
  removeSkill: (id: string) => Promise<boolean>;

  // Work Experience actions
  /** Fetch all work experiences */
  fetchWorkExperiences: () => Promise<void>;
  /** Create a new work experience */
  addWorkExperience: (data: WorkExperienceCreate) => Promise<WorkExperience | null>;
  /** Update an existing work experience */
  editWorkExperience: (
    id: string,
    data: WorkExperienceUpdate
  ) => Promise<WorkExperience | null>;
  /** Delete a work experience */
  removeWorkExperience: (id: string) => Promise<boolean>;

  // Education actions
  /** Fetch all education entries */
  fetchEducations: () => Promise<void>;
  /** Create a new education entry */
  addEducation: (data: EducationCreate) => Promise<Education | null>;
  /** Update an existing education entry */
  editEducation: (id: string, data: EducationUpdate) => Promise<Education | null>;
  /** Delete an education entry */
  removeEducation: (id: string) => Promise<boolean>;

  // Certification actions
  /** Fetch all certifications */
  fetchCertifications: () => Promise<void>;
  /** Create a new certification */
  addCertification: (data: CertificationCreate) => Promise<Certification | null>;
  /** Update an existing certification */
  editCertification: (
    id: string,
    data: CertificationUpdate
  ) => Promise<Certification | null>;
  /** Delete a certification */
  removeCertification: (id: string) => Promise<boolean>;

  /** Reset all state */
  reset: () => void;
}

/**
 * Initial state values.
 */
const initialState = {
  // Profile
  profile: null,
  profileLoading: false,
  profileError: null,

  // Skills
  skills: [],
  skillFilters: {},
  skillsLoading: false,
  skillsError: null,

  // Work Experience
  workExperiences: [],
  experiencesLoading: false,
  experiencesError: null,

  // Education
  educations: [],
  educationsLoading: false,
  educationsError: null,

  // Certifications
  certifications: [],
  certificationsLoading: false,
  certificationsError: null,
};

/**
 * Zustand store for profile and related data.
 */
export const useProfileStore = create<ProfileState>()((set, get) => ({
  ...initialState,

  // ==========================================================================
  // Profile Actions
  // ==========================================================================

  /**
   * Fetch the user profile from the API.
   */
  fetchProfile: async () => {
    set({ profileLoading: true, profileError: null });

    try {
      const profile = await getProfile();
      set({ profile });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch profile";
      set({ profileError: message });
      console.error("Profile fetch error:", error);
    } finally {
      set({ profileLoading: false });
    }
  },

  /**
   * Save the user profile.
   *
   * @param data - Profile data to save
   * @returns Saved profile or null on error
   */
  saveProfile: async (data: ProfileCreateUpdate) => {
    set({ profileLoading: true, profileError: null });

    try {
      const profile = await saveProfile(data);
      set({ profile });
      return profile;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to save profile";
      set({ profileError: message });
      console.error("Profile save error:", error);
      return null;
    } finally {
      set({ profileLoading: false });
    }
  },

  // ==========================================================================
  // Skill Actions
  // ==========================================================================

  /**
   * Fetch skills with current filters.
   */
  fetchSkills: async () => {
    const { skillFilters } = get();
    set({ skillsLoading: true, skillsError: null });

    try {
      const response = await getSkills(skillFilters);
      set({ skills: response.items });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch skills";
      set({ skillsError: message });
      console.error("Skills fetch error:", error);
    } finally {
      set({ skillsLoading: false });
    }
  },

  /**
   * Set skill filters and refetch.
   *
   * @param filters - Partial filter updates
   */
  setSkillFilters: (filters: Partial<SkillFilters>) => {
    set((state) => ({
      skillFilters: { ...state.skillFilters, ...filters },
    }));
    get().fetchSkills();
  },

  /**
   * Create a new skill.
   *
   * @param data - Skill creation data
   * @returns Created skill or null on error
   */
  addSkill: async (data: SkillCreate) => {
    set({ skillsLoading: true, skillsError: null });

    try {
      const skill = await createSkill(data);
      // Refresh the list
      await get().fetchSkills();
      return skill;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create skill";
      set({ skillsError: message });
      console.error("Skill create error:", error);
      return null;
    } finally {
      set({ skillsLoading: false });
    }
  },

  /**
   * Update an existing skill.
   *
   * @param id - Skill UUID
   * @param data - Fields to update
   * @returns Updated skill or null on error
   */
  editSkill: async (id: string, data: SkillUpdate) => {
    set({ skillsError: null });

    try {
      const updatedSkill = await updateSkill(id, data);
      // Update local state optimistically
      set((state) => ({
        skills: state.skills.map((s) => (s.id === id ? updatedSkill : s)),
      }));
      return updatedSkill;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to update skill";
      set({ skillsError: message });
      console.error("Skill update error:", error);
      return null;
    }
  },

  /**
   * Delete a skill.
   *
   * @param id - Skill UUID
   * @returns True if deleted successfully
   */
  removeSkill: async (id: string) => {
    set({ skillsError: null });

    try {
      await deleteSkill(id);
      // Remove from local state
      set((state) => ({
        skills: state.skills.filter((s) => s.id !== id),
      }));
      return true;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to delete skill";
      set({ skillsError: message });
      console.error("Skill delete error:", error);
      return false;
    }
  },

  // ==========================================================================
  // Work Experience Actions
  // ==========================================================================

  /**
   * Fetch all work experiences.
   */
  fetchWorkExperiences: async () => {
    set({ experiencesLoading: true, experiencesError: null });

    try {
      const response = await getWorkExperiences();
      set({ workExperiences: response.items });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch experiences";
      set({ experiencesError: message });
      console.error("Experiences fetch error:", error);
    } finally {
      set({ experiencesLoading: false });
    }
  },

  /**
   * Create a new work experience.
   *
   * @param data - Work experience creation data
   * @returns Created work experience or null on error
   */
  addWorkExperience: async (data: WorkExperienceCreate) => {
    set({ experiencesLoading: true, experiencesError: null });

    try {
      const experience = await createWorkExperience(data);
      // Refresh the list
      await get().fetchWorkExperiences();
      return experience;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create experience";
      set({ experiencesError: message });
      console.error("Experience create error:", error);
      return null;
    } finally {
      set({ experiencesLoading: false });
    }
  },

  /**
   * Update an existing work experience.
   *
   * @param id - Work experience UUID
   * @param data - Fields to update
   * @returns Updated work experience or null on error
   */
  editWorkExperience: async (id: string, data: WorkExperienceUpdate) => {
    set({ experiencesError: null });

    try {
      const updated = await updateWorkExperience(id, data);
      // Update local state optimistically
      set((state) => ({
        workExperiences: state.workExperiences.map((e) =>
          e.id === id ? updated : e
        ),
      }));
      return updated;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to update experience";
      set({ experiencesError: message });
      console.error("Experience update error:", error);
      return null;
    }
  },

  /**
   * Delete a work experience.
   *
   * @param id - Work experience UUID
   * @returns True if deleted successfully
   */
  removeWorkExperience: async (id: string) => {
    set({ experiencesError: null });

    try {
      await deleteWorkExperience(id);
      // Remove from local state
      set((state) => ({
        workExperiences: state.workExperiences.filter((e) => e.id !== id),
      }));
      return true;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to delete experience";
      set({ experiencesError: message });
      console.error("Experience delete error:", error);
      return false;
    }
  },

  // ==========================================================================
  // Education Actions
  // ==========================================================================

  /**
   * Fetch all education entries.
   */
  fetchEducations: async () => {
    set({ educationsLoading: true, educationsError: null });

    try {
      const response = await getEducations();
      set({ educations: response.items });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch education";
      set({ educationsError: message });
      console.error("Education fetch error:", error);
    } finally {
      set({ educationsLoading: false });
    }
  },

  /**
   * Create a new education entry.
   *
   * @param data - Education creation data
   * @returns Created education or null on error
   */
  addEducation: async (data: EducationCreate) => {
    set({ educationsLoading: true, educationsError: null });

    try {
      const education = await createEducation(data);
      // Refresh the list
      await get().fetchEducations();
      return education;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create education";
      set({ educationsError: message });
      console.error("Education create error:", error);
      return null;
    } finally {
      set({ educationsLoading: false });
    }
  },

  /**
   * Update an existing education entry.
   *
   * @param id - Education UUID
   * @param data - Fields to update
   * @returns Updated education or null on error
   */
  editEducation: async (id: string, data: EducationUpdate) => {
    set({ educationsError: null });

    try {
      const updated = await updateEducation(id, data);
      // Update local state optimistically
      set((state) => ({
        educations: state.educations.map((e) => (e.id === id ? updated : e)),
      }));
      return updated;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to update education";
      set({ educationsError: message });
      console.error("Education update error:", error);
      return null;
    }
  },

  /**
   * Delete an education entry.
   *
   * @param id - Education UUID
   * @returns True if deleted successfully
   */
  removeEducation: async (id: string) => {
    set({ educationsError: null });

    try {
      await deleteEducation(id);
      // Remove from local state
      set((state) => ({
        educations: state.educations.filter((e) => e.id !== id),
      }));
      return true;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to delete education";
      set({ educationsError: message });
      console.error("Education delete error:", error);
      return false;
    }
  },

  // ==========================================================================
  // Certification Actions
  // ==========================================================================

  /**
   * Fetch all certifications.
   */
  fetchCertifications: async () => {
    set({ certificationsLoading: true, certificationsError: null });

    try {
      const response = await getCertifications();
      set({ certifications: response.items });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to fetch certifications";
      set({ certificationsError: message });
      console.error("Certifications fetch error:", error);
    } finally {
      set({ certificationsLoading: false });
    }
  },

  /**
   * Create a new certification.
   *
   * @param data - Certification creation data
   * @returns Created certification or null on error
   */
  addCertification: async (data: CertificationCreate) => {
    set({ certificationsLoading: true, certificationsError: null });

    try {
      const certification = await createCertification(data);
      // Refresh the list
      await get().fetchCertifications();
      return certification;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to create certification";
      set({ certificationsError: message });
      console.error("Certification create error:", error);
      return null;
    } finally {
      set({ certificationsLoading: false });
    }
  },

  /**
   * Update an existing certification.
   *
   * @param id - Certification UUID
   * @param data - Fields to update
   * @returns Updated certification or null on error
   */
  editCertification: async (id: string, data: CertificationUpdate) => {
    set({ certificationsError: null });

    try {
      const updated = await updateCertification(id, data);
      // Update local state optimistically
      set((state) => ({
        certifications: state.certifications.map((c) =>
          c.id === id ? updated : c
        ),
      }));
      return updated;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to update certification";
      set({ certificationsError: message });
      console.error("Certification update error:", error);
      return null;
    }
  },

  /**
   * Delete a certification.
   *
   * @param id - Certification UUID
   * @returns True if deleted successfully
   */
  removeCertification: async (id: string) => {
    set({ certificationsError: null });

    try {
      await deleteCertification(id);
      // Remove from local state
      set((state) => ({
        certifications: state.certifications.filter((c) => c.id !== id),
      }));
      return true;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to delete certification";
      set({ certificationsError: message });
      console.error("Certification delete error:", error);
      return false;
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
 * Get display label for skill category.
 */
export function getCategoryLabel(category: SkillCategory): string {
  const labels: Record<SkillCategory, string> = {
    programming_language: "Programming Language",
    framework: "Framework",
    database: "Database",
    cloud: "Cloud",
    devops: "DevOps",
    soft_skill: "Soft Skill",
    tool: "Tool",
    methodology: "Methodology",
    other: "Other",
  };
  return labels[category];
}

/**
 * Get display label for skill proficiency.
 */
export function getProficiencyLabel(proficiency: SkillProficiency): string {
  const labels: Record<SkillProficiency, string> = {
    beginner: "Beginner",
    intermediate: "Intermediate",
    advanced: "Advanced",
    expert: "Expert",
  };
  return labels[proficiency];
}

/**
 * Get color class for skill proficiency.
 */
export function getProficiencyColor(proficiency: SkillProficiency): string {
  const colors: Record<SkillProficiency, string> = {
    beginner: "badge-ghost",
    intermediate: "badge-info",
    advanced: "badge-primary",
    expert: "badge-success",
  };
  return colors[proficiency];
}
