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

export default function TrainerCourses() {
  const router = useRouter();
  const courses = useApi<CourseSummary[]>("/authoring/courses");
  const [open, setOpen] = useState(false);
  const action = useAction();

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const created = await action.run(() =>
      api.post<CourseAdmin>("/authoring/courses", {
        title: String(f.get("title")),
        role_profile: String(f.get("role_profile")) as RoleProfileKey,
        description: String(f.get("description") ?? ""),
      }),
    );
    if (created) router.push(`/trainer/courses/${created.id}`);
  }

  return (
    <>
      <PageHeader
        eyebrow="Trainer workspace"
        title="My courses"
        description="Draft new milestones, attach material and let the assistant help. Everything you add stays a draft until an administrator approves it."
        actions={
          <Button icon="plus" onClick={() => setOpen(true)}>
            New course
          </Button>
        }
      />
      {courses.loading && !courses.data ? (
        <SkeletonCards count={4} lines={2} label="Loading your courses…" />
      ) : courses.error ? (
        <Notice>{EMPTY.loadFailed}</Notice>
      ) : courses.data && courses.data.length ? (
        <ul className={styles.courseGrid} aria-label="Courses">
          {courses.data.map((c) => (
            <li key={c.id}>
              <Link href={`/trainer/courses/${c.id}`} className={styles.courseCard} data-track={c.role_profile}>
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
                </ul>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <section className={styles.milestone}>
          <EmptyState icon="book" title="No courses yet">
            Create a course, then draft its milestones with the assistant.
          </EmptyState>
        </section>
      )}
      <Dialog
        open={open}
        title="New course"
        description="It starts as a draft. An administrator approves it before interns can use it."
        onClose={() => {
          setOpen(false);
          action.reset();
        }}
      >
        <form onSubmit={create} className={styles.form}>
          <ErrorList errors={action.errors} />
          <Field label="Title">{(p) => <input {...p} name="title" className={inputClass} required maxLength={200} />}</Field>
          <Field label="Track">
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
