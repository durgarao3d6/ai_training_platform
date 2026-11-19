"use client";

import Link from "next/link";

import { activeCoursesLabel, NO_TRAINER } from "@/components/intern/copy";
import { CourseCard } from "@/components/intern/CourseCard";
import {
  completedMilestones,
  courseState,
  pickFocusCourse,
  sortByAttention,
  tasksNeedingAnotherPass,
} from "@/components/intern/courseStatus";
import { FocusHero } from "@/components/intern/FocusHero";
import styles from "@/components/intern/intern.module.css";
import { UpNext } from "@/components/intern/Milestones";
import { useDashboard } from "@/components/intern/useDashboard";
import { Icon, type IconName } from "@/components/ui/Icon";
import { Avatar, Card, EmptyState, Notice, PageHeader, SkeletonHero } from "@/components/ui/primitives";
import { EMPTY } from "@/lib/microcopy";
import type { EnrollmentDashboard } from "@/lib/types";

function Tile({
  icon,
  tone,
  value,
  label,
}: {
  icon: IconName;
  tone: "success" | "attention" | "accent";
  value: number;
  label: string;
}) {
  return (
    <li className={styles.tile}>
      <span className={`${styles.tileIcon} ${styles[`tileIcon_${tone}`]}`} aria-hidden="true">
        <Icon name={icon} />
      </span>
      <span className={styles.tileValue}>{value}</span>
      <span className={styles.tileLabel}>{label}</span>
    </li>
  );
}

/** Distinct trainers across all courses, with the courses each one reviews. */
function trainersOf(enrollments: EnrollmentDashboard[]): { name: string; courses: string[] }[] {
  const byName = new Map<string, string[]>();
  for (const e of enrollments) {
    if (!e.trainer_name) continue;
    byName.set(e.trainer_name, [...(byName.get(e.trainer_name) ?? []), e.course_title]);
  }
  return Array.from(byName, ([name, courses]) => ({ name, courses }));
}

/** Intern home: where you are now, one primary action, then every course (FR-INT-01, UI brief 6.1). */
export default function InternHome() {
  const { data, error, loading } = useDashboard();

  // The heading is already known, so only the data area waits. The layout does not jump.
  if (loading) {
    return (
      <>
        <PageHeader title="Where you are now" />
        <SkeletonHero label="Loading your courses…" />
      </>
    );
  }
  if (error || !data) return <Notice>{EMPTY.loadFailed}</Notice>;

  const enrollments = data.enrollments;
  const focus = pickFocusCourse(enrollments);
  if (!focus) {
    return (
      <>
        <PageHeader title="Where you are now" />
        <Card>
          <EmptyState icon="book" title="No course yet">
            {EMPTY.notEnrolled}
          </EmptyState>
        </Card>
      </>
    );
  }

  const states = enrollments.map(courseState);
  const active = states.filter((s) => s.key !== "complete").length;
  const inProgress = states.filter((s) => s.key === "in_progress").length;
  const approved = enrollments.reduce((sum, e) => sum + completedMilestones(e), 0);
  const needAnotherPass = enrollments.reduce((sum, e) => sum + tasksNeedingAnotherPass(e), 0);
  const trainers = trainersOf(enrollments);

  return (
    <>
      <PageHeader eyebrow={activeCoursesLabel(active, enrollments.length)} title="Where you are now" />

      <div className={styles.homeGrid}>
        <div className={styles.mainCol}>
          <FocusHero enrollment={focus} />

          <ul className={styles.tiles} aria-label="Your progress at a glance">
            <Tile icon="check" tone="success" value={approved} label="milestones approved" />
            <Tile icon="history" tone="attention" value={needAnotherPass} label="tasks needing another pass" />
            <Tile icon="layers" tone="accent" value={inProgress} label="courses in progress" />
          </ul>

          <section aria-labelledby="your-courses">
            <div className={styles.sectionHead}>
              <h2 id="your-courses" className={styles.sectionTitle}>
                Your courses
              </h2>
              <Link href="/intern/courses">See all courses</Link>
            </div>
            <div className={styles.courseGrid}>
              {sortByAttention(enrollments).map((e) => (
                <CourseCard key={e.enrollment_id} enrollment={e} />
              ))}
            </div>
          </section>
        </div>

        <div className={styles.sideCol}>
          <Card title="Your trainers">
            {trainers.length ? (
              <ul className={styles.people}>
                {trainers.map((t) => (
                  <li key={t.name} className={styles.person}>
                    <Avatar name={t.name} size={44} />
                    <div>
                      <p className={styles.personName}>{t.name}</p>
                      <p className={styles.personMeta}>Reviews {t.courses.join(", ")}</p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.personMeta}>{NO_TRAINER}</p>
            )}
          </Card>

          {focus.milestones.length > 0 && (
            <Card
              title="Up next"
              action={<Link href={`/intern/courses/${focus.enrollment_id}`}>Course map</Link>}
            >
              <p className={styles.personMeta}>{focus.course_title}</p>
              <UpNext milestones={focus.milestones} />
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
