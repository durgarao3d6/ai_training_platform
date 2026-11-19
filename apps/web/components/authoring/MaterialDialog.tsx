"use client";

import { useState } from "react";

import adminStyles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { useAction } from "@/components/admin/useAction";
import { Button, Dialog, Field, FormActions, inputClass, Notice, SkeletonRows } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { AiJob, ComponentView, MaterialView, Suggestion } from "@/lib/types";
import { useApi } from "@/lib/useApi";

import styles from "./authoring.module.css";
import { ProposalFrame } from "./ProposalFrame";

const CATEGORY: Record<Suggestion["category"], string> = {
  correction: "Correction",
  clarity: "Clarity",
  structure: "Structure",
  example: "Example",
  objective_alignment: "Fits the objective",
};

const MAX_BYTES = 200_000;

/**
 * Feature 2: upload or paste material, then ask the assistant to correct or enhance it.
 * The original is never overwritten. Accepted edits become a new version.
 */
export function MaterialDialog({
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
  const materials = useApi<MaterialView[]>(open ? `/authoring/materials?module_id=${moduleId}` : null);
  const publish = useAction();
  const [published, setPublished] = useState<string | null>(null);

  async function publishAsStudy(m: MaterialView) {
    const done = await publish.run(() =>
      api.post<ComponentView>(`/authoring/materials/${m.id}/publish`, {}),
    );
    if (done) {
      setPublished(m.filename);
      onChanged();
    }
  }
  const [job, setJob] = useState<AiJob | null>(null);
  const [selected, setSelected] = useState<MaterialView | null>(null);
  const [pasted, setPasted] = useState("");
  const [fileName, setFileName] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const save = useAction();
  const improve = useAction();

  function close() {
    setJob(null);
    setSelected(null);
    setPublished(null);
    save.reset();
    improve.reset();
    publish.reset();
    onClose();
  }

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    setFileError(null);
    const file = event.target.files?.[0];
    if (!file) return;
    if (!/\.(md|txt)$/i.test(file.name)) {
      setFileError("Upload a .md or .txt file, or paste the text. Word and PDF are not supported yet.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setFileError("That file is too large. Split it into smaller parts.");
      return;
    }
    setFileName(file.name);
    setPasted(await file.text());
  }

  async function add(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = fileName || String(new FormData(event.currentTarget).get("filename") ?? "");
    const created = await save.run(() =>
      api.post<MaterialView>("/authoring/materials", { module_id: moduleId, filename: name, text: pasted }),
    );
    if (created) {
      setPasted("");
      setFileName("");
      materials.reload();
    }
  }

  async function run(mode: "correct" | "enhance") {
    if (!selected) return;
    const created = await improve.run(() =>
      api.post<AiJob>(`/authoring/materials/${selected.id}/improve`, { mode, instruction: "" }),
    );
    if (created) setJob(created);
  }

  const suggestions = (job?.result?.suggestions ?? []) as Suggestion[];
  const dropped = Number(job?.result?.dropped_unanchored ?? 0);
  // Show only the newest version of each file.
  const latest = new Map<string, MaterialView>();
  for (const m of materials.data ?? []) {
    const have = latest.get(m.filename);
    if (!have || m.version > have.version) latest.set(m.filename, m);
  }

  return (
    <Dialog
      open={open}
      wide
      title={`Material for “${moduleTitle}”`}
      description="Add your own notes, then ask the assistant to correct or improve them. Your original is always kept."
      onClose={close}
    >
      {job?.status === "failed" ? (
        <>
          <Notice>{job.error ?? "The assistant could not review this material."}</Notice>
          <FormActions>
            <Button variant="secondary" onClick={() => setJob(null)}>
              Back
            </Button>
          </FormActions>
        </>
      ) : job?.status === "ready" ? (
        <ProposalFrame
          job={job}
          count={suggestions.length}
          noun="edit"
          notes={dropped ? [`${dropped} suggestion(s) could not be matched to your text and were left out.`] : undefined}
          renderItem={(i) => (
            <>
              <p className={styles.meta}>{CATEGORY[suggestions[i].category]}</p>
              <div className={styles.diff}>
                <p className={styles.diffOld}>{suggestions[i].original}</p>
                <p className={styles.diffNew}>{suggestions[i].proposed}</p>
              </div>
              {suggestions[i].reason && <p className={styles.proposalText}>{suggestions[i].reason}</p>}
            </>
          )}
          onAccepted={() => {
            materials.reload();
            setJob(null);
            setSelected(null);
          }}
          onDismissed={() => setJob(null)}
        />
      ) : (
        <>
          <h3 className={styles.sectionTitle}>Your material</h3>
          {materials.loading && !materials.data ? (
            <SkeletonRows rows={3} height={48} label="Loading your material…" />
          ) : latest.size === 0 ? (
            <p className={styles.meta}>Nothing added to this milestone yet.</p>
          ) : (
            <ul className={styles.components} aria-label="Material">
              {[...latest.values()].map((m) => (
                <li key={m.id} className={styles.component}>
                  <span className={styles.componentTitle}>
                    {m.filename} <span className={styles.meta}>version {m.version}</span>
                  </span>
                  <Button
                    size="sm"
                    variant={selected?.id === m.id ? "primary" : "secondary"}
                    aria-pressed={selected?.id === m.id}
                    onClick={() => setSelected(m)}
                  >
                    {selected?.id === m.id ? "Selected" : "Select"}
                  </Button>
                  <Button size="sm" variant="secondary" icon="book" busy={publish.busy} onClick={() => void publishAsStudy(m)}>
                    Use as study material
                  </Button>
                </li>
              ))}
            </ul>
          )}
          <ErrorList errors={publish.errors} />
          {published && (
            <Notice tone="info">
              “{published}” was added as a draft reading note. Send it for approval from the milestone; interns see it once an
              administrator approves it.
            </Notice>
          )}
          {selected && (
            <div className={styles.toolbarRow}>
              <ErrorList errors={improve.errors} />
              {!aiEnabled ? (
                <Notice tone="info">The assistant is switched off for this workspace.</Notice>
              ) : (
                <>
                  <Button icon="check" busy={improve.busy} onClick={() => void run("correct")}>
                    Correct mistakes
                  </Button>
                  <Button variant="secondary" icon="edit" busy={improve.busy} onClick={() => void run("enhance")}>
                    Correct and improve
                  </Button>
                </>
              )}
            </div>
          )}

          <h3 className={styles.sectionTitle}>Add material</h3>
          <form onSubmit={add} className={adminStyles.form}>
            <ErrorList errors={save.errors} />
            {fileError && <Notice>{fileError}</Notice>}
            <Field label="Upload a file" hint=".md or .txt, up to 200 KB.">
              {(p) => <input {...p} type="file" accept=".md,.txt,text/markdown,text/plain" onChange={(e) => void onFile(e)} />}
            </Field>
            {!fileName && (
              <Field label="Or name it and paste the text" hint="Give it a name ending in .md or .txt.">
                {(p) => <input {...p} name="filename" className={inputClass} placeholder="week-1-notes.md" />}
              </Field>
            )}
            <Field label="Text">
              {(p) => (
                <textarea
                  {...p}
                  className={`${inputClass} ${styles.textarea}`}
                  value={pasted}
                  onChange={(e) => setPasted(e.target.value)}
                  required
                />
              )}
            </Field>
            <FormActions>
              <Button variant="secondary" onClick={close}>
                Close
              </Button>
              <Button type="submit" busy={save.busy}>
                Save material
              </Button>
            </FormActions>
          </form>
        </>
      )}
    </Dialog>
  );
}
