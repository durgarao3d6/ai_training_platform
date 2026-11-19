"use client";

import { useState } from "react";

import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { Button, FormActions, Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { AiJob } from "@/lib/types";

import { AiLabel } from "./AiLabel";
import styles from "./authoring.module.css";

/**
 * Shows an AI proposal for review. Nothing is selected by default: a person picks what to keep.
 * Accepting writes drafts only; an admin still approves before interns see anything.
 */
export function ProposalFrame({
  job,
  count,
  noun,
  renderItem,
  notes,
  onAccepted,
  onDismissed,
}: {
  job: AiJob;
  count: number;
  noun: string;
  renderItem: (index: number) => React.ReactNode;
  notes?: string[];
  onAccepted: () => void;
  onDismissed: () => void;
}) {
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const action = useAction();

  function toggle(index: number) {
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function accept() {
    const done = await action.run(() =>
      api.post<AiJob>(`/authoring/jobs/${job.id}/accept`, { items: [...picked].sort((a, b) => a - b) }),
    );
    if (done) onAccepted();
  }

  async function dismiss() {
    const done = await action.run(() => api.post<AiJob>(`/authoring/jobs/${job.id}/dismiss`, {}));
    if (done) onDismissed();
  }

  if (count === 0) {
    return (
      <>
        <Notice tone="info">The assistant found nothing to {noun === "edit" ? "change" : "add"}.</Notice>
        {notes?.map((n) => (
          <p key={n} className={styles.meta}>
            {n}
          </p>
        ))}
        <FormActions>
          <Button variant="secondary" onClick={() => void dismiss()} busy={action.busy}>
            Close
          </Button>
        </FormActions>
      </>
    );
  }

  return (
    <>
      <p>
        <AiLabel />
      </p>
      <p className={styles.meta}>
        Choose the {noun}s you want to keep. They are saved as drafts. An administrator approves them before interns see
        anything.
      </p>
      <ErrorList errors={action.errors} />
      <ul className={styles.proposal} aria-label={`Proposed ${noun}s`}>
        {Array.from({ length: count }, (_, index) => (
          <li key={index} className={styles.proposalItem}>
            <input
              type="checkbox"
              checked={picked.has(index)}
              onChange={() => toggle(index)}
              aria-label={`Keep ${noun} ${index + 1}`}
            />
            <div>{renderItem(index)}</div>
          </li>
        ))}
      </ul>
      {notes?.map((n) => (
        <p key={n} className={styles.meta}>
          {n}
        </p>
      ))}
      <FormActions>
        <Button variant="secondary" onClick={() => setPicked(new Set(Array.from({ length: count }, (_, i) => i)))}>
          Select all
        </Button>
        <Button variant="secondary" onClick={() => void dismiss()} disabled={action.busy}>
          Dismiss all
        </Button>
        <Button icon="check" onClick={() => void accept()} busy={action.busy} disabled={picked.size === 0}>
          Keep {picked.size} as draft{picked.size === 1 ? "" : "s"}
        </Button>
      </FormActions>
    </>
  );
}
