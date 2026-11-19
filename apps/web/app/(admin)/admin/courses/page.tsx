"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import styles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { StatusChip } from "@/components/status/StatusChip";
import {
  Button,
  Dialog,
  EmptyState,
  Field,
  FormActions,
  inputClass,
  Notice,
  PageHeader,
  SkeletonCards,
} from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { EMPTY, ROLE_NAMES } from "@/lib/microcopy";
import type { CourseAdmin, CourseSummary, RoleProfileKey } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export default function CoursesPage() {
  const router = useRouter();
  const courses = useApi<CourseSummary[]>("/admin/courses");
  const [open, setOpen] = useState(false);
  const action = useAction();

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const created = await action.run(() =>
      api.post<CourseAdmin>("/admin/courses", {
        title: String(form.get("title")),
        role_profile: String(form.get("role_profile")) as RoleProfileKey,
        description: String(form.get("description") ?? ""),
        final_deliverable: String(form.get("final_deliverable") ?? ""),
      }),
    );
    if (created) router.push(`/admin/courses/${created.id}`);
  }

  return (
    <>
      <PageHeader
        eyebrow="Catalog"
        title="Courses"
        description="One course per track. Add milestones and tasks inside each course; enrolled interns pick up changes straight away."
        actions={
          <Button icon="plus" onClick={() => setOpen(true)}>
            New course
          </Button>
        }
      />

      {courses.loading && !courses.data ? (
        <SkeletonCards count={6} lines={3} label="Loading courses…" />
      ) : courses.error ? (
        <Notice>{EMPTY.loadFailed}</Notice>
      ) : courses.data && courses.data.length ? (
        <ul className={styles.courseGrid} aria-label="Courses">
          {courses.data.map((c) => (
            <li key={c.id}>
              <Link href={`/admin/courses/${c.id}`} className={styles.courseCard} data-track={c.role_profile}>
                <span className={styles.courseCardBand}>{ROLE_NAMES[c.role_profile]}</span>
                <h2 className={styles.courseCardTitle}>{c.title}</h2>
                <div>
                  <StatusChip
                    label={c.review_status === "approved" ? "Approved" : "Draft"}
                    tone={c.review_status === "approved" ? "success" : "neutral"}
                  />
                </div>
                <ul className={styles.courseCardFacts}>
                  <li>{c.milestone_count} milestones</li>
                  <li>{c.task_count} tasks</li>
                  <li>{c.enrollment_count} enrolled</li>
                </ul>
                <span className={styles.mutedSmall}>Last change {dateFormat.format(new Date(c.updated_at))}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <section className={styles.milestone}>
          <EmptyState
            icon="book"
            title="No courses yet"
            action={
              <Button icon="plus" onClick={() => setOpen(true)}>
                New course
              </Button>
            }
          >
            Start with one course per track: Developer, Business Analyst, QA or UI/UX.
          </EmptyState>
        </section>
      )}
      <Dialog
        open={open}
        title="New course"
        description="You can add milestones and tasks once the course exists."
        onClose={() => {
          setOpen(false);
          action.reset();
        }}
      >
        <form onSubmit={create} className={styles.form}>
          <ErrorList errors={action.errors} />
          <Field label="Title">
            {(p) => <input {...p} name="title" className={inputClass} required maxLength={200} />}
          </Field>
          <Field label="Track" hint="Decides which automatic checks are available for its tasks.">
            {(p) => (
              <select {...p} name="role_profile" className={inputClass} defaultValue="developer">
                {(Object.keys(ROLE_NAMES) as RoleProfileKey[]).map((key) => (
                  <option key={key} value={key}>
                    {ROLE_NAMES[key]}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <Field label="Description">
            {(p) => <textarea {...p} name="description" className={inputClass} rows={3} maxLength={5000} />}
          </Field>
          <Field label="Final deliverable" hint="What an intern has produced by the end of the course.">
            {(p) => <input {...p} name="final_deliverable" className={inputClass} maxLength={2000} />}
          </Field>
          <FormActions>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" busy={action.busy}>
              Create course
            </Button>
          </FormActions>
        </form>
      </Dialog>
    </>
  );
}
