// Wording for the intern screens. Same tone rules as lib/microcopy.ts:
// specific, calm, human. No exclamation marks.

import type { TaskStatus } from "@/lib/types";

export function activeCoursesLabel(active: number, total: number): string {
  if (total === 0) return "No courses yet";
  if (active === 0) return total === 1 ? "Your course is complete" : "All your courses are complete";
  return active === 1 ? "1 active course" : `${active} active courses`;
}

/** One calm line under the focus task title. */
export const HERO_LINE: Record<TaskStatus, string> = {
  locked: "This task opens when the step before it is approved.",
  unlocked: "This task is ready when you are.",
  in_progress: "Pick up where you left off.",
  needs_another_pass: "Your last attempt needs another pass. Read the feedback, then hand in again.",
  review_pending: "A trainer is reviewing your work. You can reread the brief while you wait.",
  complete: "This task is approved.",
};

export const HERO_NOTHING = "Nothing is waiting for you";

export const NO_TRAINER = "No trainer is assigned to your courses yet.";

export const NO_MILESTONES = "The milestones for this course have not been published yet.";

export const COURSE_NOT_FOUND = "This course does not exist or is not one of yours.";
