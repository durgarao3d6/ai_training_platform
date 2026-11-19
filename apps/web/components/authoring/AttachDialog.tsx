"use client";

import { useState } from "react";

import adminStyles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { Button, Dialog, Field, FormActions, inputClass, Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { AiJob, ComponentProposal } from "@/lib/types";

import styles from "./authoring.module.css";
import { componentSummary, KIND_LABEL } from "./componentText";
import { ProposalFrame } from "./ProposalFrame";

/** Feature 3: the trainer says what to attach; the assistant prepares it; the trainer chooses. */
export function AttachDialog({
  open,
  moduleId,
  moduleTitle,
  aiEnabled,
  onClose,
  onChanged,
}: {
  open: boolean;
  moduleId: string;
  moduleTitle: string;
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
      api.post<AiJob>("/authoring/attach", { module_id: moduleId, instruction: String(f.get("instruction")) }),
    );
    if (created) setJob(created);
  }

  const items = (job?.result?.components ?? []) as ComponentProposal[];
  const dropped = Number(job?.result?.dropped_invalid ?? 0);

  return (
    <Dialog
      open={open}
      wide
      title={`Attach to “${moduleTitle}”`}
      description="Say what to add, for example “a 5 question self-check and two reading notes”."
      onClose={close}
    >
      {!aiEnabled ? (
        <Notice tone="info">The assistant is switched off for this workspace. Ask an administrator to turn it on.</Notice>
      ) : job?.status === "failed" ? (
        <>
          <Notice>{job.error ?? "The assistant could not prepare components."}</Notice>
          <FormActions>
            <Button variant="secondary" onClick={() => setJob(null)}>
              Try again
            </Button>
          </FormActions>
        </>
      ) : job?.status === "ready" ? (
        <ProposalFrame
          job={job}
          count={items.length}
          noun="component"
          notes={[
            ...(dropped ? [`${dropped} item(s) did not fit a supported type and were left out.`] : []),
            "Links are not checked. Open each one and confirm it before sending for approval.",
          ]}
          renderItem={(i) => (
            <>
              <p className={styles.proposalTitle}>{items[i].title}</p>
              <p className={styles.meta}>{KIND_LABEL[items[i].type]}</p>
              <p className={styles.proposalText}>{componentSummary(items[i].type, items[i].payload)}</p>
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
          <Field label="What should the assistant attach?">
            {(p) => <textarea {...p} name="instruction" className={inputClass} rows={4} required maxLength={1000} />}
          </Field>
          <FormActions>
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button type="submit" busy={action.busy}>
              {action.busy ? "Preparing…" : "Prepare components"}
            </Button>
          </FormActions>
        </form>
      )}
    </Dialog>
  );
}
