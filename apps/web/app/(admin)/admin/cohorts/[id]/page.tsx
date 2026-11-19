"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import styles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { formatDay, TrackChip } from "@/components/admin/TrackChip";
import { useAction } from "@/components/admin/useAction";
import { Icon } from "@/components/ui/Icon";
import {
  Avatar,
  Button,
  Card,
  Dialog,
  EmptyState,
  Field,
  FormActions,
  inputClass,
  Loading,
  Notice,
  PageHeader,
  Skeleton,
  SkeletonRegion,
  SkeletonTable,
  SkeletonText,
} from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { EMPTY } from "@/lib/microcopy";
import type { CohortDetail, CourseSummary, EnrollmentAdmin, RoleProfileKey, UserView } from "@/lib/types";
import { useApi } from "@/lib/useApi";

function Progress({ done, total }: { done: number; total: number }) {
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div className={styles.progress}>
      <span>
        {done} of {total} milestones
      </span>
      <span className={styles.progressTrack} aria-hidden="true">
        <span className={styles.progressFill} style={{ width: `${percent}%` }} />
      </span>
    </div>
  );
}

export default function CohortDetailPage() {
  const { id } = useParams<{ id: string }>();
  const cohort = useApi<CohortDetail>(`/admin/cohorts/${id}`);
  const courses = useApi<CourseSummary[]>("/admin/courses");
  const interns = useApi<UserView[]>("/admin/users?role=intern");
  const trainers = useApi<UserView[]>("/admin/users?role=trainer");

  const [editOpen, setEditOpen] = useState(false);
  const [enrollOpen, setEnrollOpen] = useState(false);
  const editAction = useAction();
  const enrollAction = useAction();

  // Courses, interns and trainers only fill the dialog dropdowns (and the track chip in the
  // table), so the page never waits for them.
  const optionsPending = (courses.loading && !courses.data) || (interns.loading && !interns.data);
  const publishedCourses =
    courses.data?.filter((course) => course.review_status === "approved") ?? [];
  const trainersPending = trainers.loading && !trainers.data;

  const data = cohort.data;
  if (cohort.loading && !data) {
    return (
      <>
        <Link href="/admin/cohorts" className={styles.backLink}>
          <Icon name="right" size={16} />
          All cohorts
        </Link>
        <PageHeader eyebrow="Cohort" title="Cohort" />
        <section className={styles.hero} aria-label="Cohort details">
          <div className={styles.heroBody}>
            <SkeletonRegion label="Loading the cohort…">
              <Skeleton width="32%" height={22} />
              <SkeletonText lines={2} />
            </SkeletonRegion>
          </div>
        </section>
        <Card title="Enrollments">
          <SkeletonTable rows={5} columns={4} label="Loading enrollments…" />
        </Card>
      </>
    );
  }
  if (cohort.error || !data) {
    return (
      <>
        <PageHeader eyebrow="People" title="Cohort" />
        <Notice>{EMPTY.loadFailed}</Notice>
      </>
    );
  }

  const cohortId = data.id;
  const trackByCourse = new Map<string, RoleProfileKey>(
    (courses.data ?? []).map((c): [string, RoleProfileKey] => [c.id, c.role_profile]),
  );

  function closeEdit() {
    setEditOpen(false);
    editAction.reset();
  }

  function closeEnroll() {
    setEnrollOpen(false);
    enrollAction.reset();
  }

  async function saveCohort(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const startsOn = String(form.get("starts_on") ?? "");
    const trainerId = String(form.get("trainer_id") ?? "");
    const saved = await editAction.run(() =>
      api.patch<CohortDetail>(`/admin/cohorts/${cohortId}`, {
        name: String(form.get("name") ?? "").trim(),
        starts_on: startsOn || null,
        trainer_id: trainerId || null,
      }),
    );
    if (saved) {
      cohort.setData(saved);
      closeEdit();
    }
  }

  async function enroll(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const saved = await enrollAction.run(() =>
      api.post<CohortDetail>(`/admin/cohorts/${cohortId}/enrollments`, {
        user_id: String(form.get("user_id") ?? ""),
        course_id: String(form.get("course_id") ?? ""),
      }),
    );
    if (saved) {
      cohort.setData(saved);
      closeEnroll();
    }
  }

  return (
    <>
      <Link href="/admin/cohorts" className={styles.backLink}>
        <Icon name="right" size={16} />
        All cohorts
      </Link>
      <PageHeader
        eyebrow="Cohort"
        title={data.name}
        description={`Starts ${formatDay(data.starts_on).toLowerCase()}.`}
        actions={
          <>
            <Button variant="secondary" icon="edit" onClick={() => setEditOpen(true)}>
              Edit cohort
            </Button>
            <Button icon="plus" onClick={() => setEnrollOpen(true)}>
              Enroll an intern
            </Button>
          </>
        }
      />

      <section className={styles.hero} aria-label="Cohort details">
        <div className={styles.heroBody}>
          <div className={styles.courseMeta}>
            <span className={styles.person}>
              {data.trainer_name ? (
                <>
                  <Avatar name={data.trainer_name} size={36} solid />
                  <span>
                    <span className={styles.personName}>{data.trainer_name}</span>
                    <span className={styles.personSub}> Trainer</span>
                  </span>
                </>
              ) : (
                <span>No trainer yet. Edit the cohort to choose one.</span>
              )}
            </span>
            <span>
              {data.enrollment_count} enrollment{data.enrollment_count === 1 ? "" : "s"}
            </span>
          </div>
        </div>
      </section>

      <Card title="Enrollments">
        {data.enrollments.length ? (
          <div className={styles.tableWrap}>
            <table className={styles.table} data-density="default">
              <caption>Interns enrolled in {data.name}</caption>
              <thead>
                <tr>
                  <th scope="col">Intern</th>
                  <th scope="col">Email</th>
                  <th scope="col">Course</th>
                  <th scope="col">Progress</th>
                </tr>
              </thead>
              <tbody>
                {data.enrollments.map((e: EnrollmentAdmin) => {
                  const track = trackByCourse.get(e.course_id);
                  return (
                    <tr key={e.id}>
                      <td>
                        <span className={styles.person}>
                          <Avatar name={e.intern_name} size={32} />
                          <span className={styles.personName}>{e.intern_name}</span>
                        </span>
                      </td>
                      <td className={styles.muted}>{e.intern_email}</td>
                      <td>
                        <div className={styles.chips}>
                          <span className={styles.rowTitle}>{e.course_title}</span>
                          {track && <TrackChip track={track} />}
                        </div>
                      </td>
                      <td>
                        <Progress done={e.milestones_complete} total={e.milestones_total} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="users"
            title="No one is enrolled yet"
            action={
              <Button icon="plus" onClick={() => setEnrollOpen(true)}>
                Enroll an intern
              </Button>
            }
          >
            Enrolled interns see their course on their home page straight away.
          </EmptyState>
        )}
      </Card>

      <Dialog open={editOpen} title="Edit cohort" onClose={closeEdit}>
        <form onSubmit={saveCohort} className={styles.form}>
          <ErrorList errors={editAction.errors} />
          <Field label="Name">
            {(p) => <input {...p} name="name" className={inputClass} defaultValue={data.name} required maxLength={200} />}
          </Field>
          <Field label="Start date">
            {(p) => <input {...p} name="starts_on" type="date" className={inputClass} defaultValue={data.starts_on ?? ""} />}
          </Field>
          {trainersPending ? (
            <Loading label="Loading trainers…" delayMs={0} />
          ) : (
            <Field label="Trainer">
              {(p) => (
                <select {...p} name="trainer_id" className={inputClass} defaultValue={data.trainer_id ?? ""}>
                  <option value="">No trainer yet</option>
                  {trainers.data?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name}
                    </option>
                  ))}
                </select>
              )}
            </Field>
          )}
          <FormActions>
            <Button variant="secondary" onClick={closeEdit}>
              Cancel
            </Button>
            <Button type="submit" busy={editAction.busy} disabled={trainersPending}>
              Save cohort
            </Button>
          </FormActions>
        </form>
      </Dialog>

      <Dialog
        open={enrollOpen}
        title="Enroll an intern"
        description="An intern can be enrolled in several courses. Enrolling in one more adds it next to the others."
        onClose={closeEnroll}
      >
        <form onSubmit={enroll} className={styles.form}>
          <ErrorList errors={enrollAction.errors} />
          {optionsPending ? (
            <Loading label="Loading interns and courses…" delayMs={0} />
          ) : (
            <>
              <Field label="Intern">
                {(p) => (
                  <select {...p} name="user_id" className={inputClass} required defaultValue="">
                    <option value="" disabled>
                      Choose an intern
                    </option>
                    {interns.data?.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.email})
                      </option>
                    ))}
                  </select>
                )}
              </Field>
              <Field label="Course">
                {(p) => (
                  <select {...p} name="course_id" className={inputClass} required defaultValue="">
                    <option value="" disabled>
                      {publishedCourses.length ? "Choose a course" : "No published courses available"}
                    </option>
                    {publishedCourses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.title}
                      </option>
                    ))}
                  </select>
                )}
              </Field>
            </>
          )}
          <FormActions>
            <Button variant="secondary" onClick={closeEnroll}>
              Cancel
            </Button>
            <Button
              type="submit"
              busy={enrollAction.busy}
              disabled={optionsPending || publishedCourses.length === 0}
            >
              Enroll
            </Button>
          </FormActions>
        </form>
      </Dialog>
    </>
  );
}
