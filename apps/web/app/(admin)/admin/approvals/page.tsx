"use client";

import Link from "next/link";

import styles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { AiLabel } from "@/components/authoring/AiLabel";
import authoring from "@/components/authoring/authoring.module.css";
import { componentSummary, KIND_LABEL } from "@/components/authoring/componentText";
import { StatusChip } from "@/components/status/StatusChip";
import { Button, Card, EmptyState, Notice, PageHeader, SkeletonRows } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { EMPTY } from "@/lib/microcopy";
import type { ComponentView, CourseAdmin, PendingApprovals } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function ApprovalsPage() {
  const pending = useApi<PendingApprovals>("/authoring/pending");
  const action = useAction();

  async function approveModule(id: string) {
    const done = await action.run(() => api.post<CourseAdmin>(`/authoring/modules/${id}/approve`, {}));
    if (done) pending.reload();
  }

  async function approveComponent(id: string) {
    const done = await action.run(() => api.post<ComponentView>(`/authoring/components/${id}/approve`, {}));
    if (done) pending.reload();
  }

  const data = pending.data;
  const empty = data && data.modules.length === 0 && data.components.length === 0;

  return (
    <>
      <PageHeader
        eyebrow="Catalog"
        title="Approvals"
        description="Milestones and components that trainers or the assistant have drafted. Interns see nothing until you approve it."
      />
      <ErrorList errors={action.errors} />
      {pending.loading && !data ? (
        <>
          <Card title="Draft milestones">
            <SkeletonRows rows={3} height={52} label="Loading draft milestones…" />
          </Card>
          <Card title="Components waiting">
            <SkeletonRows rows={3} height={52} label="Loading components waiting for approval…" />
          </Card>
        </>
      ) : pending.error ? (
        <Notice>{EMPTY.loadFailed}</Notice>
      ) : empty ? (
        <Card>
          <EmptyState icon="check" title="Nothing is waiting">
            New drafts from trainers appear here.
          </EmptyState>
        </Card>
      ) : (
        data && (
          <>
            <Card title={`Draft milestones (${data.modules.length})`}>
              {data.modules.length === 0 ? (
                <p className={authoring.meta}>None.</p>
              ) : (
                <ul className={authoring.components} aria-label="Draft milestones">
                  {data.modules.map((m) => (
                    <li key={m.module_id} className={authoring.component}>
                      <span className={authoring.componentTitle}>
                        {m.title}
                        <span className={authoring.meta}>{m.course_title}</span>
                      </span>
                      <Link href={`/admin/courses/${m.course_id}`} className={styles.backLink}>
                        Review in course
                      </Link>
                      <Button size="sm" icon="check" busy={action.busy} onClick={() => void approveModule(m.module_id)}>
                        Approve and publish
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title={`Components waiting (${data.components.length})`}>
              {data.components.length === 0 ? (
                <p className={authoring.meta}>None.</p>
              ) : (
                <ul className={authoring.components} aria-label="Components waiting for approval">
                  {data.components.map(({ component: c, context }) => {
                    const unverified = c.type === "resource" && !c.payload.link_verified;
                    return (
                      <li key={c.id} className={authoring.component}>
                        <span className={authoring.componentTitle}>
                          {c.title}
                          <span className={authoring.meta}>
                            {KIND_LABEL[c.type]}
                            {context ? ` on ${context}` : ""}: {componentSummary(c.type, c.payload)}
                          </span>
                        </span>
                        {c.ai_generated && <AiLabel text="Written by AI" />}
                        {unverified && <StatusChip label="Link not checked" tone="attention" />}
                        <Button
                          size="sm"
                          icon="check"
                          busy={action.busy}
                          disabled={unverified}
                          onClick={() => void approveComponent(c.id)}
                        >
                          Approve
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </>
        )
      )}
    </>
  );
}
