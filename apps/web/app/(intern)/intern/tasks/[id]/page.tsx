"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { useDashboard } from "@/components/intern/useDashboard";
import { StatusChip } from "@/components/status/StatusChip";
import { StudyMaterial } from "@/components/study/StudyMaterial";
import { AttemptHistory, ReviewFeedback } from "@/components/submission/AttemptHistory";
import { SubmissionPanel } from "@/components/submission/SubmissionPanel";
import { Icon } from "@/components/ui/Icon";
import {
  Button,
  Card,
  EmptyState,
  Notice,
  PageHeader,
  SkeletonRegion,
  SkeletonRows,
  SkeletonText,
} from "@/components/ui/primitives";
import { ApiError } from "@/lib/api";
import { EMPTY, TASK_STATUS, TRAINER_REVIEW_NOTE } from "@/lib/microcopy";
import type { SubmissionSummary, SubmissionView, TaskInstanceView } from "@/lib/types";
import { useApi } from "@/lib/useApi";

import page from "./task.module.css";

const LEVELS = ["4", "3", "2", "1", "0"];

const ATTEMPTS_FAILED = "We could not load your attempts. Your work is saved. Try again in a moment.";

/**
 * The way back, rendered before anything has loaded. The course comes from the task and the
 * course title from the dashboard, so both are added as they arrive; neither holds up the page.
 */
function BackLink({ enrollmentId, courseTitle }: { enrollmentId?: string; courseTitle?: string }) {
  return (
    <Link href={enrollmentId ? `/intern/courses/${enrollmentId}` : "/intern/courses"} className={page.back}>
      <Icon name="right" size={16} />
      Back to course
      {courseTitle && <span className={page.backContext}>{courseTitle}</span>}
    </Link>
  );
}

/**
 * Task page: brief, objective, deliverables, rubric in plain language, and hand-in (FR-INT-03, UI brief 6.2).
 * The task, its attempts and the dashboard load independently: each card fills in on its own.
 */
export default function TaskPage() {
  const { id } = useParams<{ id: string }>();
  const task = useApi<TaskInstanceView>(`/task-instances/${id}`);
  const attempts = useApi<SubmissionSummary[]>(`/task-instances/${id}/submissions`);
  const dashboard = useDashboard();
  const latest = attempts.data?.[0];
  const feedback = useApi<SubmissionView>(
    latest?.status === "evaluated" ? `/submissions/${latest.id}` : null,
  );

  function refreshProgress() {
    task.reload();
    attempts.reload();
    dashboard.reload();
  }

  const view = task.data;
  const t = view?.task;
  const enrollment = dashboard.data?.enrollments.find((e) => e.enrollment_id === view?.enrollment_id);
  const milestone = enrollment?.milestones.find((m) => m.tasks.some((x) => x.task_instance_id === id));

  const nextMilestone = milestone?.status === "complete"
    ? enrollment?.milestones.find((item) => item.position > milestone.position && item.status === "unlocked")
    : null;

  if (task.error instanceof ApiError && task.error.status === 404) {
    return (
      <Card>
        <EmptyState icon="alert" title="Task not found" action={<Link href="/intern">Back to home</Link>}>
          This task does not exist or is not assigned to you.
        </EmptyState>
      </Card>
    );
  }
  if (task.error && !view) {
    return (
      <>
        <BackLink />
        <Notice>{EMPTY.loadFailed}</Notice>
      </>
    );
  }

  const chip = view ? TASK_STATUS[view.status] : null;

  return (
    <>
      <BackLink enrollmentId={view?.enrollment_id} courseTitle={enrollment?.course_title} />
      <PageHeader
        eyebrow={t ? (t.task_type === "assessment" ? "Assessment" : "Practical task") : "Task"}
        title={t ? t.title : "Loading the task…"}
        actions={chip ? <StatusChip label={chip.label} tone={chip.tone} /> : undefined}
      />

      <div className={page.layout}>
        <div className={page.main}>
          {milestone && (
            <Card title={`Study first: ${milestone.title}`}>
              <StudyMaterial moduleId={milestone.id} />
            </Card>
          )}
          <Card title="The brief">
            {t ? (
              <>
                <p className="prose">{t.description}</p>
                {t.learning_objective && (
                  <div className={page.objective} data-track={enrollment?.role_profile}>
                    <Icon name="target" />
                    <div>
                      <p className={page.objectiveLabel}>What you will learn</p>
                      <p className="prose">{t.learning_objective}</p>
                    </div>
                  </div>
                )}
                {t.requires_review && <p className={page.reviewNote}>{TRAINER_REVIEW_NOTE}</p>}
              </>
            ) : (
              <SkeletonRegion label="Loading the brief…">
                <SkeletonText lines={4} />
              </SkeletonRegion>
            )}
          </Card>

          {t && t.starter_files.length > 0 && (
            <Card title="Files to start from">
              <ul className={page.starters}>
                {t.starter_files.map((name) => (
                  <li key={name}>
                    <Icon name="file" />
                    <code>{name}</code>
                  </li>
                ))}
              </ul>
              <p className={page.muted}>Your trainer shares these files with you.</p>
            </Card>
          )}

          <Card title="How your work is judged">
            {!t ? (
              <SkeletonRows rows={3} height={56} label="Loading the marking guide…" />
            ) : t.rubric ? (
              <>
                <p className={page.muted}>
                  Each part is rated from 0 to 4. You need {t.rubric.pass_threshold} of 100 points, and every part
                  marked required must reach its minimum level.
                </p>
                <div className={page.criteria}>
                  {t.rubric.criteria.map((c) => (
                    <details key={c.id} className={page.criterion}>
                      <summary className={page.criterionHead}>
                        <span className={page.criterionTitle}>{c.title}</span>
                        {c.mandatory && <span className={page.required}>Required: level {c.mandatory_min_level}+</span>}
                        <span className={page.weight}>{c.weight} pts</span>
                        <Icon name="down" />
                      </summary>
                      <dl className={page.levels}>
                        {LEVELS.filter((l) => c.levels[l]).map((l) => (
                          <div key={l} className={page.level}>
                            <dt>Level {l}</dt>
                            <dd>{c.levels[l]}</dd>
                          </div>
                        ))}
                      </dl>
                    </details>
                  ))}
                </div>
              </>
            ) : (
              <>
                {t.evaluated_on && <p className="prose">Your work is judged on {t.evaluated_on.toLowerCase()}.</p>}
                <p className={page.muted}>{EMPTY.rubricPending}</p>
              </>
            )}
          </Card>
        </div>

        <aside className={page.aside} aria-label="Hand in your work">
          <Card title="Hand in your work">
            {view && t ? (
              <>
                {t.submits && <p className={page.muted}>{t.submits}</p>}
                <SubmissionPanel
                  taskInstanceId={view.id}
                  status={view.status}
                  deliverables={t.deliverables}
                  onSubmitted={refreshProgress}
                />
              </>
            ) : (
              <SkeletonRows rows={2} height={104} label="Loading the hand-in form…" />
            )}
          </Card>
          <Card title="Your attempts">
            <Button variant="secondary" onClick={refreshProgress} disabled={attempts.loading}>
              Refresh progress
            </Button>
            {feedback.data?.id === latest?.id && feedback.data?.review && (
              <ReviewFeedback review={feedback.data.review} />
            )}
            {nextMilestone && enrollment && (
              <p><Link href={`/intern/courses/${enrollment.enrollment_id}`}>Next milestone · {nextMilestone.title}</Link></p>
            )}
            {attempts.error && !attempts.data ? (
              <Notice>{ATTEMPTS_FAILED}</Notice>
            ) : (
              <AttemptHistory attempts={attempts.data} deliverables={t?.deliverables ?? []} />
            )}
          </Card>
        </aside>
      </div>
    </>
  );
}
