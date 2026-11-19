"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import styles from "@/components/admin/admin.module.css";
import { DraftDialog } from "@/components/authoring/DraftDialog";
import { MilestoneTools } from "@/components/authoring/MilestoneTools";
import { StatusChip } from "@/components/status/StatusChip";
import { Icon } from "@/components/ui/Icon";
import { Button, EmptyState, Notice, PageHeader, SkeletonRows } from "@/components/ui/primitives";
import { EMPTY, ROLE_NAMES } from "@/lib/microcopy";
import type { AuthoringConfig, CourseAdmin } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function TrainerCourseWorkspace() {
  const { id } = useParams<{ id: string }>();
  const course = useApi<CourseAdmin>(`/authoring/courses/${id}`);
  const config = useApi<AuthoringConfig>("/authoring/config");
  const [draftOpen, setDraftOpen] = useState(false);
  const data = course.data;

  // The authoring config only decides whether the assistant buttons are live, so the course
  // never waits for it.
  if (course.loading && !data) {
    return (
      <>
        <Link href="/trainer/courses" className={styles.backLink}>
          <Icon name="right" size={16} />
          My courses
        </Link>
        <PageHeader eyebrow="My courses" title="Course" />
        <SkeletonRows rows={3} height={132} label="Loading the course…" />
      </>
    );
  }
  if (course.error || !data) {
    return (
      <>
        <PageHeader eyebrow="My courses" title="Course" />
        <Notice>{EMPTY.loadFailed}</Notice>
      </>
    );
  }
  const aiEnabled = config.data?.ai_enabled ?? false;

  return (
    <>
      <Link href="/trainer/courses" className={styles.backLink}>
        <Icon name="right" size={16} />
        My courses
      </Link>
      <PageHeader
        eyebrow={ROLE_NAMES[data.role_profile]}
        title={data.title}
        description={data.description || undefined}
        actions={
          <Button icon="plus" onClick={() => setDraftOpen(true)}>
            Draft milestones with the assistant
          </Button>
        }
      />
      {!aiEnabled && config.data && (
        <Notice tone="info">The assistant is switched off. You can still add material and components by hand.</Notice>
      )}
      {data.modules.length === 0 ? (
        <section className={styles.milestone}>
          <EmptyState icon="layers" title="No milestones yet">
            Ask the assistant to draft some, then choose which to keep.
          </EmptyState>
        </section>
      ) : (
        <ol className={styles.milestones} aria-label="Milestones">
          {data.modules.map((m, index) => (
            <li key={m.id} className={styles.milestone}>
              <div className={styles.milestoneHead}>
                <span className={styles.milestoneNumber} aria-hidden="true">
                  {index + 1}
                </span>
                <div className={styles.milestoneBody}>
                  <h2 className={styles.milestoneTitle}>{m.title}</h2>
                  <p className={styles.milestoneText}>{m.description}</p>
                  <p>
                    <StatusChip
                      label={m.review_status === "approved" ? "Published" : "Draft, waiting for approval"}
                      tone={m.review_status === "approved" ? "success" : "neutral"}
                    />
                  </p>
                </div>
              </div>
              {m.tasks.length > 0 && (
                <ul className={styles.tasks} aria-label={`Tasks in ${m.title}`}>
                  {m.tasks.map((t) => (
                    <li key={t.id} className={styles.task}>
                      <span className={styles.taskTitle}>{t.title}</span>
                    </li>
                  ))}
                </ul>
              )}
              <MilestoneTools
                moduleId={m.id}
                title={m.title}
                status={m.review_status}
                isAdmin={false}
                aiEnabled={aiEnabled}
                onCourseChanged={(c) => c && course.setData(c)}
              />
            </li>
          ))}
        </ol>
      )}
      <DraftDialog
        open={draftOpen}
        courseId={data.id}
        aiEnabled={aiEnabled}
        onClose={() => setDraftOpen(false)}
        onChanged={course.reload}
      />
    </>
  );
}
