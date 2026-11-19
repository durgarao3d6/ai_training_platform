"use client";

import Link from "next/link";

import { Button, Card, EmptyState, Notice, PageHeader, SkeletonRows } from "@/components/ui/primitives";
import type { components } from "@/lib/api-schema";
import { useApi } from "@/lib/useApi";

import styles from "./review.module.css";

type QueueItem = components["schemas"]["ReviewQueueItem"];
const date = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

export default function TrainerQueue() {
  const queue = useApi<QueueItem[]>("/trainer/review-queue");
  return (
    <>
      <PageHeader
        eyebrow="Trainer workspace"
        title="Review queue"
        description="Attempts waiting for your decision, oldest first."
        actions={<Button variant="secondary" onClick={queue.reload} disabled={queue.loading}>Refresh</Button>}
      />
      <Card>
        {queue.error ? (
          <Notice>The review queue could not be loaded. Try refreshing it.</Notice>
        ) : !queue.data ? (
          <SkeletonRows rows={3} height={56} label="Loading the review queue…" />
        ) : queue.data.length ? (
          <ul className={styles.list}>
            {queue.data.map((item) => (
              <li key={item.submission_id}>
                <Link href={`/trainer/review/${item.submission_id}`}>{item.task_title}</Link>
                <span>{item.intern_name} · {item.cohort_name} · Attempt {item.attempt_number}</span>
                <time dateTime={item.submitted_at}>{date.format(new Date(item.submitted_at))}</time>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon="inbox" title="Nothing to review yet">
            Submitted attempts with a published rubric appear here.
          </EmptyState>
        )}
      </Card>
    </>
  );
}
