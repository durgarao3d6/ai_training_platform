"use client";

import { useEffect, useRef, useState } from "react";

import { StatusChip } from "@/components/status/StatusChip";
import { Icon } from "@/components/ui/Icon";
import { Button, EmptyState, Loading, Notice, SkeletonRows } from "@/components/ui/primitives";
import type { components } from "@/lib/api-schema";
import { EMPTY, SUBMISSION_STATUS } from "@/lib/microcopy";
import { downloadArtifact, getSubmission } from "@/lib/submissions";
import type { Deliverable, SubmissionSummary, SubmissionView } from "@/lib/types";

import styles from "./submission.module.css";

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

function formatSize(bytes: number | null): string {
  if (!bytes) return "";
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AttemptDetails({ id, deliverables }: { id: string; deliverables: Deliverable[] }) {
  const [state, setState] = useState<{ data: SubmissionView | null; error: boolean }>({ data: null, error: false });

  useEffect(() => {
    let cancelled = false;
    getSubmission(id)
      .then((data) => !cancelled && setState({ data, error: false }))
      .catch(() => !cancelled && setState({ data: null, error: true }));
    return () => {
      cancelled = true;
    };
  }, [id]);
  if (state.error) return <Notice>{EMPTY.loadFailed}</Notice>;
  // A short wait inside an already open row: an inline spinner, lined up with the items below.
  if (!state.data)
    return (
      <div className={styles.attemptWait}>
        <Loading label="Loading this attempt…" />
      </div>
    );

  return (
    <>
      {state.data.review && <ReviewFeedback review={state.data.review} />}
      <AttemptArtifacts artifacts={state.data.artifacts} deliverables={deliverables} />
    </>
  );
}

export function ReviewFeedback({ review }: { review: components["schemas"]["ReviewResult"] }) {
  return (
    <div className={styles.reviewFeedback}>
      <strong>{review.decision === "approve" ? "Approved" : "Revision requested"}</strong>
      {review.reason && <p className={styles.textPreview}>{review.reason}</p>}
    </div>
  );
}

export function AttemptArtifacts({
  artifacts,
  deliverables = [],
}: {
  artifacts: components["schemas"]["ArtifactOut"][];
  deliverables?: Deliverable[];
}) {
  const titles = Object.fromEntries(deliverables.map((d) => [d.id, d.title]));
  const [downloadFailed, setDownloadFailed] = useState(false);

  async function download(path: string, filename: string) {
    setDownloadFailed(false);
    try {
      await downloadArtifact(path, filename);
    } catch {
      setDownloadFailed(true);
    }
  }

  return (
    <>
      {downloadFailed && <Notice>The file could not be downloaded. Try again.</Notice>}
      <ul className={styles.artifacts}>
        {artifacts.map((a) => (
          <li key={a.id} className={styles.artifact}>
            <span className={styles.artifactFor}>{titles[a.deliverable_id] ?? a.deliverable_id}</span>
            {a.kind === "file" && a.download_path && (
              <Button
                variant="ghost"
                size="sm"
                icon="download"
                onClick={() => void download(a.download_path!, a.filename ?? "file")}
              >
                {a.filename} <span className={styles.size}>{formatSize(a.size_bytes)}</span>
              </Button>
            )}
            {a.kind === "link" && a.url && (
              <a href={a.url} target="_blank" rel="noopener noreferrer" className={styles.artifactLink}>
                <Icon name="link" size={16} />
                {a.url}
              </a>
            )}
            {a.kind === "text" && <p className={styles.textPreview}>{a.text}</p>}
          </li>
        ))}
      </ul>
    </>
  );
}

/** Fetches an attempt's items only once its row has been opened. */
function LazyDetails({ id, deliverables }: { id: string; deliverables: Deliverable[] }) {
  const [opened, setOpened] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const details = ref.current?.closest("details");
    if (!details) return;
    const onToggle = () => details.open && setOpened(true);
    details.addEventListener("toggle", onToggle);
    return () => details.removeEventListener("toggle", onToggle);
  }, []);
  return <div ref={ref}>{opened && <AttemptDetails id={id} deliverables={deliverables} />}</div>;
}

export function AttemptHistory({
  attempts,
  deliverables,
}: {
  attempts: SubmissionSummary[] | null;
  deliverables: Deliverable[];
}) {
  // Rows the height of a closed attempt, so the card keeps its size when the list lands.
  if (!attempts) return <SkeletonRows rows={3} height={56} label="Loading your attempts…" />;
  if (!attempts.length) {
    return (
      <EmptyState icon="history" title="No attempts yet">
        {EMPTY.noAttempts}
      </EmptyState>
    );
  }
  return (
    <ol className={styles.attempts}>
      {attempts.map((a) => {
        const status = SUBMISSION_STATUS[a.status];
        return (
          <li key={a.id}>
            <details className={styles.attempt}>
              <summary className={styles.attemptSummary}>
                <span className={styles.attemptNumber}>Attempt {a.attempt_number}</span>
                <StatusChip label={status.label} tone={status.tone} />
                <span className={styles.attemptMeta}>
                  {dateFormat.format(new Date(a.created_at))} · {a.artifact_count}{" "}
                  {a.artifact_count === 1 ? "item" : "items"}
                </span>
                <Icon name="down" />
              </summary>
              <LazyDetails id={a.id} deliverables={deliverables} />
            </details>
          </li>
        );
      })}
    </ol>
  );
}
