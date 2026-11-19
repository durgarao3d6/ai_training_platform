"use client";

import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { StatusChip } from "@/components/status/StatusChip";
import { Button, SkeletonRows } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { ComponentView } from "@/lib/types";
import { useApi } from "@/lib/useApi";

import { AiLabel } from "./AiLabel";
import styles from "./authoring.module.css";
import { componentSummary, KIND_LABEL } from "./componentText";

const STATUS = {
  draft: { label: "Draft", tone: "neutral" },
  in_review: { label: "Waiting for approval", tone: "review" },
  approved: { label: "Approved", tone: "success" },
} as const;

/** Components attached to a milestone, with the actions each person is allowed to take. */
export function ComponentList({
  moduleId,
  isAdmin,
  refreshKey,
}: {
  moduleId: string;
  isAdmin: boolean;
  refreshKey: number;
}) {
  const list = useApi<ComponentView[]>(`/authoring/components?module_id=${moduleId}&r=${refreshKey}`);
  const action = useAction();

  async function call(id: string, verb: "submit" | "verify-link" | "approve") {
    const done = await action.run(() => api.post<ComponentView>(`/authoring/components/${id}/${verb}`, {}));
    if (done) list.reload();
  }

  async function remove(id: string) {
    const done = await action.run(async () => {
      await api.del<void>(`/authoring/components/${id}`);
      return true;
    });
    if (done) list.reload();
  }

  // Only the first load shows placeholders; a refresh keeps the rows already on screen.
  if (list.loading && !list.data) {
    return <SkeletonRows rows={2} height={44} label="Loading attached components…" />;
  }
  if (!list.data) return null;
  if (list.data.length === 0) {
    return (
      <p className={styles.meta}>
        No study material yet. Add material and use it as study material, or attach components with the assistant.
      </p>
    );
  }

  return (
    <>
      <ErrorList errors={action.errors} />
      <ul className={styles.components} aria-label="Attached components">
        {list.data.map((c) => {
          const unverified = c.type === "resource" && !c.payload.link_verified;
          const status = STATUS[c.review_status];
          return (
            <li key={c.id} className={styles.component}>
              <span className={styles.componentTitle}>
                {c.title}
                <span className={styles.meta}>
                  {KIND_LABEL[c.type]}: {componentSummary(c.type, c.payload)}
                </span>
              </span>
              {c.ai_generated && <AiLabel text="Written by AI" />}
              {unverified && <StatusChip label="Link not checked" tone="attention" />}
              <StatusChip label={status.label} tone={status.tone} />
              {unverified && c.review_status !== "approved" && (
                <Button size="sm" variant="secondary" onClick={() => void call(c.id, "verify-link")} busy={action.busy}>
                  I checked this link
                </Button>
              )}
              {c.review_status === "draft" && (
                <Button size="sm" variant="secondary" onClick={() => void call(c.id, "submit")} busy={action.busy}>
                  Send for approval
                </Button>
              )}
              {isAdmin && c.review_status !== "approved" && (
                <Button size="sm" icon="check" onClick={() => void call(c.id, "approve")} busy={action.busy}>
                  Approve
                </Button>
              )}
              {c.review_status !== "approved" && (
                <Button
                  size="sm"
                  variant="ghost"
                  icon="trash"
                  aria-label={`Remove ${c.title}`}
                  onClick={() => void remove(c.id)}
                  busy={action.busy}
                >
                  Remove
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}
