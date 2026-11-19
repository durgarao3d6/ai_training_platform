"use client";

import Link from "next/link";

import styles from "@/components/admin/admin.module.css";
import { TrackChip } from "@/components/admin/TrackChip";
import { StatusChip } from "@/components/status/StatusChip";
import { Icon, type IconName } from "@/components/ui/Icon";
import {
  ButtonLink,
  Card,
  EmptyState,
  Notice,
  PageHeader,
  SkeletonRows,
  SkeletonStats,
  SkeletonTable,
} from "@/components/ui/primitives";
import { useAuth } from "@/lib/auth";
import { EMPTY } from "@/lib/microcopy";
import type { CohortSummary, CourseSummary, UserView } from "@/lib/types";
import { useApi } from "@/lib/useApi";

function Stat({ icon, value, label, tint }: { icon: IconName; value: number | string; label: string; tint?: string }) {
  return (
    <div className={styles.stat}>
      <span className={`${styles.statIcon} ${tint ?? ""}`}>
        <Icon name={icon} size={22} />
      </span>
      <div>
        <p className={styles.statValue}>{value}</p>
        <p className={styles.statLabel}>{label}</p>
      </div>
    </div>
  );
}

export default function AdminOverview() {
  const { user } = useAuth();
  const isAdmin = user?.roles.includes("admin") ?? false;
  const courses = useApi<CourseSummary[]>("/admin/courses");
  const cohorts = useApi<CohortSummary[]>("/admin/cohorts");
  const interns = useApi<UserView[]>("/admin/users?role=intern");

  // Each section waits on its own request. The tiles wait only on the three lists they count,
  // and never on each other's cards.
  const coursesPending = courses.loading && !courses.data;
  const cohortsPending = cohorts.loading && !cohorts.data;
  const internsPending = interns.loading && !interns.data;
  const statsPending = coursesPending || cohortsPending || internsPending;
  const enrolled = cohorts.data?.reduce((sum, c) => sum + c.enrollment_count, 0) ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Management"
        title="Overview"
        description="Courses, cohorts and people in the programme. Everything here is created in the app."
        actions={
          <>
            {isAdmin && (
              <ButtonLink href="/admin/courses" variant="secondary">
                Manage courses
              </ButtonLink>
            )}
            <ButtonLink href="/admin/cohorts">Manage cohorts</ButtonLink>
          </>
        }
      />

      {statsPending ? (
        <SkeletonStats count={4} label="Loading figures…" />
      ) : (
        <div className={styles.stats}>
          <Stat icon="book" value={courses.data?.length ?? 0} label="Courses" />
          <Stat icon="users" value={cohorts.data?.length ?? 0} label="Cohorts" tint={styles.tintAttention} />
          <Stat icon="user" value={interns.data?.length ?? 0} label="Intern accounts" tint={styles.tintSuccess} />
          <Stat icon="layers" value={enrolled} label="Enrollments" tint={styles.tintReview} />
        </div>
      )}

      <div className={styles.twoCol}>
      <Card title="Courses" action={isAdmin ? <Link href="/admin/courses" className={styles.cardLink}>All courses</Link> : undefined} padded>
        {coursesPending ? (
          <SkeletonTable rows={4} columns={5} label="Loading courses…" />
        ) : courses.error ? (
          <Notice>{EMPTY.loadFailed}</Notice>
        ) : courses.data && courses.data.length ? (
          <div className={styles.tableWrap}>
            <table className={styles.table} data-density="default">
              <caption>Courses and their status</caption>
              <thead>
                <tr>
                  <th scope="col">Course</th>
                  <th scope="col">Track</th>
                  <th scope="col">Status</th>
                  <th scope="col" className={styles.num}>
                    Milestones
                  </th>
                  <th scope="col" className={styles.num}>
                    Enrolled
                  </th>
                </tr>
              </thead>
              <tbody>
                {courses.data.map((c) => (
                  <tr key={c.id}>
                    <td>
                      {isAdmin ? (
                        <Link href={`/admin/courses/${c.id}`} className={styles.rowTitle}>
                          {c.title}
                        </Link>
                      ) : (
                        <span className={styles.rowTitle}>{c.title}</span>
                      )}
                    </td>
                    <td>
                      <TrackChip track={c.role_profile} />
                    </td>
                    <td>
                      <StatusChip
                        label={c.review_status === "approved" ? "Approved" : "Draft"}
                        tone={c.review_status === "approved" ? "success" : "neutral"}
                      />
                    </td>
                    <td className={styles.num}>{c.milestone_count}</td>
                    <td className={styles.num}>{c.enrollment_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="book"
            title="No courses yet"
            action={isAdmin ? <ButtonLink href="/admin/courses">Create the first course</ButtonLink> : undefined}
          >
            {isAdmin ? "Create a course, then add its milestones and tasks." : "An administrator creates the courses."}
          </EmptyState>
        )}
      </Card>

      <Card title="Cohorts" action={<Link href="/admin/cohorts" className={styles.cardLink}>All cohorts</Link>}>
        {cohortsPending ? (
          <SkeletonRows rows={4} height={52} label="Loading cohorts…" />
        ) : cohorts.error ? (
          <Notice>{EMPTY.loadFailed}</Notice>
        ) : cohorts.data && cohorts.data.length ? (
          <ul className={styles.cohortList} aria-label="Cohorts">
            {cohorts.data.map((c) => (
              <li key={c.id}>
                <Link href={`/admin/cohorts/${c.id}`} className={styles.cohortRow}>
                  <span>
                    <span className={styles.personName}>{c.name}</span>
                    <span className={styles.personSub}> {c.trainer_name ?? "No trainer yet"}</span>
                  </span>
                  <span className={styles.muted}>{c.enrollment_count} enrolled</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon="users" title="No cohorts yet" action={<ButtonLink href="/admin/cohorts">Create a cohort</ButtonLink>}>
            Group interns into a cohort, then enroll them in courses.
          </EmptyState>
        )}
      </Card>
      </div>
    </>
  );
}
