"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { AttemptArtifacts, ReviewFeedback } from "@/components/submission/AttemptHistory";
import { Button, Card, Field, FormActions, Notice, PageHeader, SkeletonRows } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import type { components } from "@/lib/api-schema";
import { useApi } from "@/lib/useApi";

import styles from "../../review.module.css";

type Schemas = components["schemas"];

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function RubricCriteria({ content }: { content: Schemas["ReviewRubric"]["content"] }) {
  const raw = record(content)?.criteria;
  const criteria = Array.isArray(raw) ? raw.map(record) : [];
  return (
    <ul className={styles.list}>
      {criteria.map((criterion, index) => {
        if (!criterion || typeof criterion.id !== "string") return null;
        const levels = record(criterion.levels);
        return (
          <li key={criterion.id}>
            <details open={index === 0}>
              <summary>{typeof criterion.title === "string" ? criterion.title : criterion.id}</summary>
              {typeof criterion.weight === "number" && <p>Weight {criterion.weight}%</p>}
              {typeof criterion.mandatory_min_level === "number" && (
                <p>Required level {criterion.mandatory_min_level}</p>
              )}
              {levels && (
                <dl>
                  {Object.entries(levels).map(([level, description]) => typeof description === "string" && (
                    <div key={level}><dt>Level {level}</dt><dd>{description}</dd></div>
                  ))}
                </dl>
              )}
            </details>
          </li>
        );
      })}
    </ul>
  );
}

function ReviewAttempt({ id }: { id: string }) {
  const submission = useApi<Schemas["SubmissionOut"]>(`/submissions/${id}`);
  const rubric = useApi<Schemas["ReviewRubric"]>(`/trainer/submissions/${id}/rubric`);
  const action = useAction();
  const [decision, setDecision] = useState<Schemas["ReviewInput"]["decision"]>("request_revision");
  const [result, setResult] = useState<Schemas["ReviewResult"] | null>(null);
  const [reason, setReason] = useState("");

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!rubric.data || action.busy) return;
    const input: Schemas["ReviewInput"] = { decision, reason, rubric_version_id: rubric.data.id };
    const saved = await action.run(() => apiFetch<Schemas["ReviewResult"]>(
      `/trainer/submissions/${id}/decision`, { method: "POST", body: JSON.stringify(input) },
    ));
    if (saved) setResult(saved);
  }

  const review = result ?? submission.data?.review;
  return (
    <>
      <Link href="/trainer">Back to review queue</Link>
      <PageHeader title={submission.data ? `Review attempt ${submission.data.attempt_number}` : "Review attempt"} />
      {(submission.error || rubric.error) && <Notice>This attempt or its rubric could not be loaded.</Notice>}
      <div className={styles.reviewLayout}>
        <Card title="Submitted work">
          {submission.data ? (
            <AttemptArtifacts artifacts={submission.data.artifacts} />
          ) : !submission.error && <SkeletonRows rows={3} height={42} label="Loading submitted work…" />}
        </Card>
        <Card title={rubric.data ? `Rubric version ${rubric.data.version}` : "Rubric"}>
          {rubric.data ? (
            <RubricCriteria content={rubric.data.content} />
          ) : !rubric.error && <SkeletonRows rows={3} height={42} label="Loading the rubric…" />}
        </Card>
      </div>
      {review ? (
        <Card title="Recorded decision"><ReviewFeedback review={review} /></Card>
      ) : submission.data?.status === "received" && rubric.data && (
        <Card title="Record your decision">
          <form className={styles.form} onSubmit={save}>
            <ErrorList errors={action.errors} />
            <Field label="Decision">
              {(props) => (
                <select {...props} value={decision} onChange={(event) => setDecision(
                  event.target.value === "approve" ? "approve" : "request_revision",
                )}>
                  <option value="request_revision">Request revision</option>
                  <option value="approve">Approve</option>
                </select>
              )}
            </Field>
            <Field label={decision === "request_revision" ? "What should the intern revise?" : "Feedback (optional)"}>
              {(props) => <textarea {...props} rows={5} maxLength={5000} value={reason}
                onChange={(event) => setReason(event.target.value)} required={decision === "request_revision"} />}
            </Field>
            <FormActions><Button type="submit" busy={action.busy}>Save decision</Button></FormActions>
          </form>
        </Card>
      )}
    </>
  );
}

export default function TrainerReviewPage() {
  const { id } = useParams<{ id: string }>();
  return <ReviewAttempt key={id} id={id} />;
}
