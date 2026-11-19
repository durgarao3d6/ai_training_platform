// All wording lives here so the tone rules are testable (UI Design Brief section 8):
// specific, calm, human. "Needs another pass", never "Failed". No exclamation marks.

import type { MilestoneStatus, RoleProfileKey, SubmissionStatus, TaskStatus } from "./types";

export type Tone = "success" | "attention" | "review" | "locked" | "open" | "neutral";

export const TASK_STATUS: Record<TaskStatus, { label: string; tone: Tone }> = {
  locked: { label: "Locked", tone: "locked" },
  unlocked: { label: "Ready to start", tone: "open" },
  in_progress: { label: "In progress", tone: "open" },
  needs_another_pass: { label: "Needs another pass", tone: "attention" },
  review_pending: { label: "Trainer review pending", tone: "review" },
  complete: { label: "Approved", tone: "success" },
};

export const MILESTONE_STATUS: Record<MilestoneStatus, { label: string; tone: Tone }> = {
  locked: { label: "Locked", tone: "locked" },
  unlocked: { label: "Open", tone: "open" },
  complete: { label: "Complete", tone: "success" },
};

export const SUBMISSION_STATUS: Record<SubmissionStatus, { label: string; tone: Tone }> = {
  received: { label: "Received", tone: "neutral" },
  evaluating: { label: "Being checked", tone: "review" },
  evaluated: { label: "Checked", tone: "success" },
  rejected: { label: "Not accepted", tone: "attention" },
};

export const ROLE_NAMES: Record<RoleProfileKey, string> = {
  developer: "Software Developer",
  ba: "Business Analyst",
  qa: "QA Engineer",
  uiux: "UI/UX Designer",
};

export const DELIVERABLE_KIND: Record<string, string> = {
  file: "a file",
  link: "a link",
  text: "written text",
};

export const TRAINER_REVIEW_NOTE =
  "A trainer reviews every result for this task before it is approved, so expect a short wait after the automatic checks.";

export const EMPTY = {
  notEnrolled: "You are not enrolled in a course yet. Your trainer will add you, and your course will appear here.",
  nothingWaiting: "Nothing is waiting for you right now. Open your course map to see what comes next.",
  rubricPending:
    "The marking guide for this task is still being written. Your trainer will publish it before it counts.",
  loadFailed: "We could not load this page. Your work is saved. Try again in a moment.",
  noAttempts: "No attempts yet. When you hand in your work, every attempt is kept here.",
};
