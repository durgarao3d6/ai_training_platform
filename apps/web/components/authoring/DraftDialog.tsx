"use client";

import { useState } from "react";

import adminStyles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { Button, Dialog, Field, FormActions, inputClass, Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { AiJob, DraftMilestone } from "@/lib/types";

import styles from "./authoring.module.css";
import { ProposalFrame } from "./ProposalFrame";

/** Feature 1: the assistant drafts new milestones for a course. Existing milestones are kept. */
export function DraftDialog({
  open,
  courseId,
  aiEnabled,
  onClose,
  onChanged,
}: {
  open: boolean;
  courseId: string;
  aiEnabled: boolean;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [job, setJob] = useState<AiJob | null>(null);
  const action = useAction();

  function close() {
    setJob(null);
    action.reset();
    onClose();
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const created = await action.run(() =>
      api.post<AiJob>("/authoring/drafts", {
        course_id: courseId,
        topic: String(f.get("topic")),
        audience: String(f.get("audience") ?? ""),
        level: String(f.get("level")),
        duration_weeks: Number(f.get("duration_weeks")),
        notes: String(f.get("notes") ?? ""),
      }),
    );
    if (created) setJob(created);
  }

  const milestones = (job?.result?.milestones ?? []) as DraftMilestone[];
  const dropped = Number(job?.result?.dropped_duplicates ?? 0);

  return (
    <Dialog
      open={open}
      wide
      title="Draft milestones with the assistant"
      description="Describe what the course should teach. The assistant proposes milestones and tasks; you choose what to keep."
      onClose={close}
    >
      {!aiEnabled ? (
        <Notice tone="info">The assistant is switched off for this workspace. Ask an administrator to turn it on.</Notice>
      ) : job?.status === "failed" ? (
        <>
          <Notice>{job.error ?? "The assistant could not produce a draft."}</Notice>
          <FormActions>
            <Button variant="secondary" onClick={() => setJob(null)}>
              Try again
            </Button>
          </FormActions>
        </>
      ) : job?.status === "ready" ? (
        <ProposalFrame
          job={job}
          count={milestones.length}
          noun="milestone"
          notes={dropped ? [`${dropped} proposed milestone(s) matched existing titles and were left out.`] : undefined}
          renderItem={(i) => (
            <>
              <p className={styles.proposalTitle}>{milestones[i].title}</p>
              <p className={styles.proposalText}>{milestones[i].description}</p>
              <p className={styles.meta}>Objective: {milestones[i].learning_objective}</p>
              <ul className={styles.subList}>
                {milestones[i].tasks.map((t) => (
                  <li key={t.title}>{t.title}</li>
                ))}
              </ul>
            </>
          )}
          onAccepted={() => {
            onChanged();
            close();
          }}
          onDismissed={close}
        />
      ) : (
        <form onSubmit={submit} className={adminStyles.form}>
          <ErrorList errors={action.errors} />
          <Field label="Topic" hint="What should interns be able to do by the end?">
            {(p) => <input {...p} name="topic" className={inputClass} required maxLength={300} />}
          </Field>
          <Field label="Audience">
            {(p) => <input {...p} name="audience" className={inputClass} maxLength={200} />}
          </Field>
          <Field label="Level">
            {(p) => (
              <select {...p} name="level" className={inputClass} defaultValue="beginner">
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            )}
          </Field>
          <Field label="Duration in weeks">
            {(p) => (
              <input {...p} name="duration_weeks" type="number" min={1} max={52} defaultValue={4} className={inputClass} />
            )}
          </Field>
          <Field label="Notes for the assistant" hint="Optional. Topics to include or avoid.">
            {(p) => <textarea {...p} name="notes" className={inputClass} rows={3} maxLength={2000} />}
          </Field>
          <FormActions>
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button type="submit" busy={action.busy}>
              {action.busy ? "Drafting…" : "Draft milestones"}
            </Button>
          </FormActions>
        </form>
      )}
    </Dialog>
  );
}
