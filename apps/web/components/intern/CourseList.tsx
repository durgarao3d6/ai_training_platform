"use client";

import { useState } from "react";

import { EmptyState } from "@/components/ui/primitives";
import type { EnrollmentDashboard } from "@/lib/types";

import { CourseCard } from "./CourseCard";
import { COURSE_STATUS, courseState, sortByAttention, type CourseStatusKey } from "./courseStatus";
import styles from "./intern.module.css";

type Filter = "all" | CourseStatusKey;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "in_progress", label: COURSE_STATUS.in_progress.label },
  { key: "not_started", label: COURSE_STATUS.not_started.label },
  { key: "waiting", label: "Waiting" },
  { key: "complete", label: COURSE_STATUS.complete.label },
];

/** All courses with a segmented status filter (buttons that report their pressed state). */
export function CourseList({ enrollments }: { enrollments: EnrollmentDashboard[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const sorted = sortByAttention(enrollments);
  const count = (key: Filter) => (key === "all" ? sorted.length : sorted.filter((e) => courseState(e).key === key).length);
  const shown = filter === "all" ? sorted : sorted.filter((e) => courseState(e).key === filter);

  return (
    <>
      <div className={styles.filter} role="group" aria-label="Filter courses by status">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`${styles.filterButton} ${filter === f.key ? styles.filterOn : ""}`}
            aria-pressed={filter === f.key}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
            <span className={styles.filterCount}>{count(f.key)}</span>
          </button>
        ))}
      </div>
      <p className="visually-hidden" role="status">
        Showing {shown.length} {shown.length === 1 ? "course" : "courses"}
      </p>

      {shown.length ? (
        <div className={`${styles.courseGrid} ${styles.courseGridLarge}`}>
          {shown.map((e) => (
            <CourseCard key={e.enrollment_id} enrollment={e} large />
          ))}
        </div>
      ) : (
        <EmptyState icon="book" title="No courses here">
          None of your courses match this filter right now.
        </EmptyState>
      )}
    </>
  );
}
