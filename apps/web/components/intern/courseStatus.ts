// Per-enrollment status for interns who follow several courses at once.
// Derived on the client from the dashboard data; the API does not send it.

import type { Tone } from "@/lib/microcopy";
import type { DashboardTask, EnrollmentDashboard, TaskStatus } from "@/lib/types";

export type CourseStatusKey = "not_started" | "in_progress" | "waiting" | "complete";

export const COURSE_STATUS: Record<CourseStatusKey, { label: string; tone: Tone }> = {
  not_started: { label: "Not started", tone: "neutral" },
  in_progress: { label: "In progress", tone: "open" },
  waiting: { label: "Waiting for review", tone: "review" },
  complete: { label: "Complete", tone: "success" },
};

export interface CourseState {
  key: CourseStatusKey;
  label: string;
  tone: Tone;
  /** Lower is more urgent. Used to pick the focus course. */
  rank: number;
}

function tasksOf(enrollment: EnrollmentDashboard): DashboardTask[] {
  return enrollment.milestones.flatMap((m) => m.tasks);
}

export function completedMilestones(enrollment: EnrollmentDashboard): number {
  return enrollment.milestones.filter((m) => m.status === "complete").length;
}

export function tasksNeedingAnotherPass(enrollment: EnrollmentDashboard): number {
  return tasksOf(enrollment).filter((t) => t.status === "needs_another_pass").length;
}

function statusKey(enrollment: EnrollmentDashboard): CourseStatusKey {
  const tasks = tasksOf(enrollment);
  const has = (...statuses: TaskStatus[]) => tasks.some((t) => statuses.includes(t.status));
  const done = completedMilestones(enrollment);

  if (enrollment.milestones.length > 0 && done === enrollment.milestones.length) return "complete";
  if (!has("unlocked", "in_progress", "needs_another_pass") && has("review_pending")) return "waiting";
  if (done > 0 || has("in_progress", "needs_another_pass", "review_pending")) return "in_progress";
  return "not_started";
}

/**
 * Attention rank: a task needing another pass first, then work in progress, then a task that is
 * ready to start, then waiting for review, then not started, then complete.
 */
function attentionRank(enrollment: EnrollmentDashboard, key: CourseStatusKey): number {
  const tasks = tasksOf(enrollment);
  if (tasks.some((t) => t.status === "needs_another_pass")) return 0;
  if (key === "in_progress" && tasks.some((t) => t.status === "in_progress")) return 1;
  if (tasks.some((t) => t.status === "unlocked")) return key === "in_progress" ? 1 : 2;
  if (key === "in_progress") return 1;
  if (key === "waiting") return 3;
  if (key === "not_started") return 4;
  return 5;
}

export function courseState(enrollment: EnrollmentDashboard): CourseState {
  const key = statusKey(enrollment);
  return { key, ...COURSE_STATUS[key], rank: attentionRank(enrollment, key) };
}

/** The course that most needs the intern now. Ties keep the original order. */
export function pickFocusCourse(enrollments: EnrollmentDashboard[]): EnrollmentDashboard | null {
  let best: EnrollmentDashboard | null = null;
  let bestRank = Number.POSITIVE_INFINITY;
  for (const enrollment of enrollments) {
    const { rank } = courseState(enrollment);
    if (rank < bestRank) {
      best = enrollment;
      bestRank = rank;
    }
  }
  return best;
}

/** Courses sorted by attention rank (stable). */
export function sortByAttention(enrollments: EnrollmentDashboard[]): EnrollmentDashboard[] {
  return enrollments
    .map((enrollment, index) => ({ enrollment, index, rank: courseState(enrollment).rank }))
    .sort((a, b) => a.rank - b.rank || a.index - b.index)
    .map((entry) => entry.enrollment);
}
