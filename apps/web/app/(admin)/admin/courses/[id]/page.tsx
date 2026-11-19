"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import styles from "@/components/admin/admin.module.css";
import { ConfirmDialog } from "@/components/admin/ConfirmDialog";
import { CourseDialog, ModuleDialog, RubricDialog, TaskDialog } from "@/components/admin/CourseDialogs";
import { ErrorList } from "@/components/admin/ErrorList";
import { DraftDialog } from "@/components/authoring/DraftDialog";
import { MilestoneTools } from "@/components/authoring/MilestoneTools";
import { useAction } from "@/components/admin/useAction";
import { StatusChip } from "@/components/status/StatusChip";
import { Icon } from "@/components/ui/Icon";
import {
  Button,
  EmptyState,
  Notice,
  PageHeader,
  Skeleton,
  SkeletonRegion,
  SkeletonRows,
  SkeletonText,
} from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { EMPTY, ROLE_NAMES } from "@/lib/microcopy";
import type { AuthoringConfig, CourseAdmin, ModuleAdmin, RoleProfileView, TaskAdmin } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type DeleteTarget =
  | { kind: "course" }
  | { kind: "module"; module: ModuleAdmin }
  | { kind: "task"; task: TaskAdmin };

type TaskDialogState = { moduleId: string; task: TaskAdmin | null };
type ModuleDialogState = { module: ModuleAdmin | null };

function RubricChip({ task }: { task: TaskAdmin }) {
  const { published_rubric: live, draft_rubric: draft } = task;
  if (!live && !draft) return <StatusChip label="No rubric" tone="locked" />;
  return (
    <>
      {live && <StatusChip label={`Published v${live.version}`} tone="success" />}
      {draft && <StatusChip label={`Draft v${draft.version}`} tone="attention" />}
    </>
  );
}

export default function CourseEditorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const course = useApi<CourseAdmin>(`/admin/courses/${id}`);
  const profiles = useApi<RoleProfileView[]>("/admin/role-profiles");
  const config = useApi<AuthoringConfig>("/authoring/config");
  const [draftOpen, setDraftOpen] = useState(false);

  const [editCourse, setEditCourse] = useState(false);
  const [moduleDialog, setModuleDialog] = useState<ModuleDialogState | null>(null);
  const [taskDialog, setTaskDialog] = useState<TaskDialogState | null>(null);
  const [rubricTask, setRubricTask] = useState<TaskAdmin | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);

  const pageAction = useAction();
  const deleteAction = useAction();

  const data = course.data;

  // The role profiles and the authoring config only feed the rubric dialog's checker list and the
  // assistant buttons, so nothing on the page waits for them.
  if (course.loading && !data) {
    return (
      <>
        <Link href="/admin/courses" className={styles.backLink}>
          <Icon name="right" size={16} />
          All courses
        </Link>
        <PageHeader eyebrow="Course editor" title="Course" />
        <section className={styles.hero} aria-label="Course details">
          <div className={styles.heroBody}>
            <SkeletonRegion label="Loading the course…">
              <Skeleton width="38%" height={24} />
              <SkeletonText lines={2} />
            </SkeletonRegion>
          </div>
        </section>
        <SkeletonRows rows={3} height={132} label="Loading milestones…" />
      </>
    );
  }
  if (course.error || !data) {
    return (
      <>
        <PageHeader eyebrow="Catalog" title="Course" />
        <Notice>{EMPTY.loadFailed}</Notice>
      </>
    );
  }

  const checkers = profiles.data?.find((p) => p.key === data.role_profile)?.checkers ?? [];
  const approved = data.review_status === "approved";
  const courseId = data.id;
  const courseTitle = data.title;
  const moduleList = data.modules;
  const taskCount = data.modules.reduce((sum, m) => sum + m.tasks.length, 0);

  async function toggleApproval() {
    const next = approved ? "draft" : "approved";
    const saved = await pageAction.run(() => api.patch<CourseAdmin>(`/admin/courses/${courseId}`, { review_status: next }));
    if (saved) course.setData(saved);
  }

  async function move(index: number, direction: -1 | 1) {
    const ids = moduleList.map((m) => m.id);
    const target = index + direction;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    const saved = await pageAction.run(() => api.put<CourseAdmin>(`/admin/courses/${courseId}/module-order`, { module_ids: ids }));
    if (saved) course.setData(saved);
  }

  async function confirmDelete() {
    const target = deleteTarget;
    if (!target) return;
    if (target.kind === "course") {
      const done = await deleteAction.run(async () => {
        await api.del<void>(`/admin/courses/${courseId}`);
        return true;
      });
      if (done) router.push("/admin/courses");
      return;
    }
    const path = target.kind === "module" ? `/admin/modules/${target.module.id}` : `/admin/tasks/${target.task.id}`;
    const saved = await deleteAction.run(() => api.del<CourseAdmin>(path));
    if (saved) {
      course.setData(saved);
      closeDelete();
    }
  }

  function closeDelete() {
    setDeleteTarget(null);
    deleteAction.reset();
  }

  const deleteCopy = deleteTarget
    ? deleteTarget.kind === "course"
      ? {
          title: "Delete this course?",
          description: `"${courseTitle}" and all of its milestones, tasks and marking guides will be removed. This cannot be undone.`,
          label: "Delete course",
        }
      : deleteTarget.kind === "module"
        ? {
            title: "Delete this milestone?",
            description: `"${deleteTarget.module.title}" and its ${deleteTarget.module.tasks.length} task${
              deleteTarget.module.tasks.length === 1 ? "" : "s"
            } will be removed. If interns have already handed in work here, it cannot be deleted.`,
            label: "Delete milestone",
          }
        : {
            title: "Delete this task?",
            description: `"${deleteTarget.task.title}" and its marking guide will be removed. If interns have already handed in work for it, it cannot be deleted.`,
            label: "Delete task",
          }
    : null;

  return (
    <>
      <Link href="/admin/courses" className={styles.backLink}>
        <Icon name="right" size={16} />
        All courses
      </Link>
      <PageHeader eyebrow="Course editor" title={data.title} />

      <section className={styles.hero} aria-label="Course details">
        <div className={styles.heroBand} data-track={data.role_profile}>
          <span className={styles.heroPill}>{ROLE_NAMES[data.role_profile]}</span>
          <p className={styles.heroTitle}>{data.final_deliverable || "No final deliverable yet"}</p>
        </div>
        <div className={styles.heroBody}>
          <div className={styles.courseMeta}>
            <StatusChip label={approved ? "Approved" : "Draft"} tone={approved ? "success" : "neutral"} />
            <span>
              {data.modules.length} milestone{data.modules.length === 1 ? "" : "s"}
            </span>
            <span>
              {taskCount} task{taskCount === 1 ? "" : "s"}
            </span>
            <span>
              {data.enrollment_count} intern{data.enrollment_count === 1 ? "" : "s"} enrolled
            </span>
          </div>
          {data.description && <p className={styles.heroText}>{data.description}</p>}
          <ErrorList errors={pageAction.errors} />
          <div className={styles.heroActions}>
            <Button variant="secondary" icon="plus" onClick={() => setDraftOpen(true)}>
              Draft milestones with the assistant
            </Button>
            <Button variant="secondary" icon="edit" onClick={() => setEditCourse(true)}>
              Edit course
            </Button>
            <Button icon={approved ? "edit" : "check"} busy={pageAction.busy} onClick={() => void toggleApproval()}>
              {approved ? "Move back to draft" : "Approve course"}
            </Button>
            <Button
              variant="danger"
              icon="trash"
              disabled={data.enrollment_count > 0}
              aria-describedby={data.enrollment_count > 0 ? "delete-course-note" : undefined}
              onClick={() => setDeleteTarget({ kind: "course" })}
            >
              Delete course
            </Button>
          </div>
          {data.enrollment_count > 0 && (
            <p id="delete-course-note" className={styles.hint}>
              This course cannot be deleted while interns are enrolled. Move it back to draft to stop new work, or remove the enrollments first.
            </p>
          )}
        </div>
      </section>

      {data.modules.length === 0 ? (
        <section className={styles.milestone}>
          <EmptyState
            icon="layers"
            title="No milestones yet"
            action={
              <Button icon="plus" onClick={() => setModuleDialog({ module: null })}>
                Add milestone
              </Button>
            }
          >
            A milestone groups tasks. Interns work through them in order.
          </EmptyState>
        </section>
      ) : (
        <>
          <ol className={styles.milestones} aria-label="Milestones">
            {data.modules.map((m, index) => (
              <li key={m.id} className={styles.milestone}>
                <div className={styles.milestoneHead}>
                  <span className={styles.milestoneNumber} aria-hidden="true">
                    {index + 1}
                  </span>
                  <div className={styles.milestoneBody}>
                    <h2 className={styles.milestoneTitle}>{m.title}</h2>
                    {m.review_status === "draft" && <StatusChip label="Draft, not visible to interns" tone="attention" />}
                    {m.description && <p className={styles.milestoneText}>{m.description}</p>}
                    <p className={styles.milestoneText}>
                      {m.learning_objective ? (
                        <>
                          <strong>Objective:</strong> {m.learning_objective}
                        </>
                      ) : (
                        "This milestone needs a learning objective. Add one with Edit."
                      )}
                    </p>
                  </div>
                  <div className={styles.toolbar}>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon="up"
                      disabled={index === 0 || pageAction.busy}
                      aria-label={`Move ${m.title} up`}
                      onClick={() => void move(index, -1)}
                    >
                      Move up
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon="down"
                      disabled={index === data.modules.length - 1 || pageAction.busy}
                      aria-label={`Move ${m.title} down`}
                      onClick={() => void move(index, 1)}
                    >
                      Move down
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon="edit"
                      aria-label={`Edit milestone ${m.title}`}
                      onClick={() => setModuleDialog({ module: m })}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon="trash"
                      aria-label={`Delete milestone ${m.title}`}
                      onClick={() => setDeleteTarget({ kind: "module", module: m })}
                    >
                      Delete
                    </Button>
                  </div>
                </div>

                {m.tasks.length > 0 && (
                  <ul className={styles.tasks} aria-label={`Tasks in ${m.title}`}>
                    {m.tasks.map((t) => (
                      <li key={t.id} className={styles.task}>
                        <span className={styles.taskTitle}>{t.title}</span>
                        <StatusChip label={t.depth === "demo" ? "Demo" : "Content"} tone="neutral" />
                        <RubricChip task={t} />
                        {t.requires_review && <StatusChip label="Trainer reviews" tone="review" />}
                        <div className={styles.toolbar}>
                          <Button
                            size="sm"
                            variant="secondary"
                            icon="edit"
                            aria-label={`Edit task ${t.title}`}
                            onClick={() => setTaskDialog({ moduleId: m.id, task: t })}
                          >
                            Edit task
                          </Button>
                          <Button size="sm" variant="secondary" icon="target" aria-label={`Rubric for ${t.title}`} onClick={() => setRubricTask(t)}>
                            Rubric
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            icon="trash"
                            aria-label={`Delete task ${t.title}`}
                            onClick={() => setDeleteTarget({ kind: "task", task: t })}
                          >
                            Delete
                          </Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
                <div className={styles.addTask}>
                  <Button size="sm" variant="secondary" icon="plus" onClick={() => setTaskDialog({ moduleId: m.id, task: null })}>
                    Add task
                  </Button>
                </div>
                <MilestoneTools
                  moduleId={m.id}
                  title={m.title}
                  status={m.review_status}
                  isAdmin
                  aiEnabled={config.data?.ai_enabled ?? false}
                  onCourseChanged={(c) => c && course.setData(c)}
                />
              </li>
            ))}
          </ol>
          <Button icon="plus" onClick={() => setModuleDialog({ module: null })}>
            Add milestone
          </Button>
        </>
      )}

      <DraftDialog
        open={draftOpen}
        courseId={data.id}
        aiEnabled={config.data?.ai_enabled ?? false}
        onClose={() => setDraftOpen(false)}
        onChanged={course.reload}
      />
      <CourseDialog open={editCourse} course={data} onClose={() => setEditCourse(false)} onSaved={course.setData} />
      <ModuleDialog
        open={moduleDialog !== null}
        courseId={data.id}
        milestone={moduleDialog?.module ?? null}
        onClose={() => setModuleDialog(null)}
        onSaved={course.setData}
      />
      <TaskDialog
        open={taskDialog !== null}
        moduleId={taskDialog?.moduleId ?? ""}
        task={taskDialog?.task ?? null}
        onClose={() => setTaskDialog(null)}
        onSaved={course.setData}
      />
      {rubricTask && (
        <RubricDialog open task={rubricTask} checkers={checkers} onClose={() => setRubricTask(null)} onSaved={course.setData} />
      )}
      <ConfirmDialog
        open={deleteTarget !== null}
        title={deleteCopy?.title ?? ""}
        description={deleteCopy?.description ?? ""}
        confirmLabel={deleteCopy?.label ?? "Delete"}
        busy={deleteAction.busy}
        errors={deleteAction.errors}
        onConfirm={() => void confirmDelete()}
        onClose={closeDelete}
      />
    </>
  );
}
