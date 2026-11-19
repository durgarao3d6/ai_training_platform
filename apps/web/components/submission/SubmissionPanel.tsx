"use client";

import { useRef, useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { Button, inputClass, Notice } from "@/components/ui/primitives";
import { ApiError } from "@/lib/api";
import { DELIVERABLE_KIND } from "@/lib/microcopy";
import { countWords, submit, uploadFile, type ArtifactPayload } from "@/lib/submissions";
import type { ArtifactProblem, Deliverable, DeliverableKind, SubmissionView, TaskStatus } from "@/lib/types";

import styles from "./submission.module.css";

const OPEN: TaskStatus[] = ["unlocked", "in_progress", "needs_another_pass"];
const CLOSED_REASON: Partial<Record<TaskStatus, string>> = {
  locked: "This task opens when the previous milestone is approved.",
  review_pending: "Your last attempt is waiting for trainer review.",
  complete: "This task is approved. Your attempts stay in the history below.",
};

interface UploadedFile {
  name: string;
  key: string | null; // null while uploading
  error: string | null;
}

interface DraftState {
  mode: DeliverableKind;
  files: UploadedFile[];
  url: string;
  text: string;
}

function initialDraft(d: Deliverable): DraftState {
  return { mode: d.kinds[0], files: [], url: "", text: "" };
}

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : String(Date.now());
}

function maxFiles(d: Deliverable): number {
  return d.max_count ?? (d.min_count && d.min_count > 1 ? d.min_count + 5 : 1);
}

export function SubmissionPanel({
  taskInstanceId,
  status,
  deliverables,
  onSubmitted,
}: {
  taskInstanceId: string;
  status: TaskStatus;
  deliverables: Deliverable[];
  onSubmitted: (submission: SubmissionView) => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, DraftState>>(() =>
    Object.fromEntries(deliverables.map((d) => [d.id, initialDraft(d)])),
  );
  const [problems, setProblems] = useState<Record<string, string[]>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const idempotencyKey = useRef(newKey());

  if (!OPEN.includes(status)) {
    return <Notice tone="info">{CLOSED_REASON[status] ?? "Submissions are closed for this task."}</Notice>;
  }

  function update(id: string, change: Partial<DraftState>) {
    setDrafts((all) => ({ ...all, [id]: { ...all[id], ...change } }));
    setProblems((all) => ({ ...all, [id]: [] }));
    setSuccess(null);
  }

  async function addFiles(d: Deliverable, list: FileList | null) {
    if (!list?.length) return;
    const room = maxFiles(d) - drafts[d.id].files.length;
    const picked = Array.from(list).slice(0, Math.max(room, 0));
    const placeholders: UploadedFile[] = picked.map((f) => ({ name: f.name, key: null, error: null }));
    update(d.id, { files: [...drafts[d.id].files, ...placeholders] });

    for (const file of picked) {
      let result: Partial<UploadedFile>;
      try {
        result = { key: await uploadFile(taskInstanceId, d.id, file) };
      } catch (err) {
        result = { error: err instanceof ApiError ? err.messages.join(" ") : "The upload did not finish." };
      }
      setDrafts((all) => ({
        ...all,
        [d.id]: {
          ...all[d.id],
          files: all[d.id].files.map((f) => (f.name === file.name && f.key === null && !f.error ? { ...f, ...result } : f)),
        },
      }));
    }
  }

  function removeFile(d: Deliverable, index: number) {
    update(d.id, { files: drafts[d.id].files.filter((_, i) => i !== index) });
  }

  function collect(): { artifacts: ArtifactPayload[]; missing: string[]; pending: boolean } {
    const artifacts: ArtifactPayload[] = [];
    const missing: string[] = [];
    let pending = false;
    for (const d of deliverables) {
      const draft = drafts[d.id];
      const before = artifacts.length;
      if (draft.mode === "file") {
        for (const f of draft.files) {
          if (f.key === null && !f.error) pending = true;
          if (f.key) artifacts.push({ deliverable_id: d.id, kind: "file", upload_key: f.key });
        }
      } else if (draft.mode === "link" && draft.url.trim()) {
        artifacts.push({ deliverable_id: d.id, kind: "link", url: draft.url.trim() });
      } else if (draft.mode === "text" && draft.text.trim()) {
        artifacts.push({ deliverable_id: d.id, kind: "text", text: draft.text });
      }
      if (d.required && artifacts.length === before) missing.push(d.title);
    }
    return { artifacts, missing, pending };
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    setSuccess(null);
    const { artifacts, missing, pending } = collect();
    if (pending) {
      setFormError("Wait for your uploads to finish, then hand in.");
      return;
    }
    if (missing.length) {
      setFormError(`Still needed: ${missing.join(", ")}.`);
      return;
    }
    setBusy(true);
    try {
      const submission = await submit(taskInstanceId, artifacts, idempotencyKey.current);
      idempotencyKey.current = newKey();
      setDrafts(Object.fromEntries(deliverables.map((d) => [d.id, initialDraft(d)])));
      setSuccess(`Attempt ${submission.attempt_number} is in. It will be checked next, and the result will be waiting here.`);
      onSubmitted(submission);
    } catch (err) {
      if (err instanceof ApiError) {
        const byDeliverable: Record<string, string[]> = {};
        for (const p of err.errors as ArtifactProblem[]) {
          if (p && typeof p === "object" && "deliverable_id" in p) {
            (byDeliverable[p.deliverable_id] ??= []).push(p.message);
          }
        }
        setProblems(byDeliverable);
        setFormError(err.detail ?? err.message);
      } else {
        setFormError("We could not send your work. Nothing was lost; try again in a moment.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className={styles.form} noValidate>
      {deliverables.map((d) => {
        const draft = drafts[d.id];
        const errors = problems[d.id] ?? [];
        const words = countWords(draft.text);
        return (
          <fieldset key={d.id} className={styles.deliverable} aria-invalid={errors.length ? true : undefined}>
            <legend className={styles.legend}>
              {d.title}
              {!d.required && <span className={styles.optional}> (optional)</span>}
            </legend>
            {d.description && <p className={styles.description}>{d.description}</p>}

            {d.kinds.length > 1 && (
              <div className={styles.modes} role="radiogroup" aria-label={`How to hand in ${d.title}`}>
                {d.kinds.map((kind) => (
                  <label key={kind} className={`${styles.mode} ${draft.mode === kind ? styles.modeOn : ""}`}>
                    <input
                      type="radio"
                      name={`mode-${d.id}`}
                      value={kind}
                      checked={draft.mode === kind}
                      onChange={() => update(d.id, { mode: kind })}
                      className="visually-hidden"
                    />
                    <Icon name={kind === "file" ? "upload" : kind === "link" ? "link" : "text"} size={16} />
                    {DELIVERABLE_KIND[kind].replace(/^a /, "").replace(/^\w/, (c) => c.toUpperCase())}
                  </label>
                ))}
              </div>
            )}

            {draft.mode === "file" && (
              <>
                {draft.files.length < maxFiles(d) && (
                  <label className={styles.drop}>
                    <Icon name="upload" size={22} />
                    <span>
                      <strong>Choose {maxFiles(d) > 1 ? "files" : "a file"}</strong>
                      <span className={styles.dropHint}>
                        {d.accept.length ? d.accept.join(", ") : "Any document type"}
                        {d.min_count ? ` · at least ${d.min_count}` : ""}
                      </span>
                    </span>
                    <input
                      type="file"
                      className="visually-hidden"
                      accept={d.accept.join(",") || undefined}
                      multiple={maxFiles(d) > 1}
                      onChange={(e) => {
                        void addFiles(d, e.target.files);
                        e.target.value = "";
                      }}
                    />
                  </label>
                )}
                {draft.files.length > 0 && (
                  <ul className={styles.files}>
                    {draft.files.map((f, i) => (
                      <li key={`${f.name}-${i}`} className={styles.file}>
                        <Icon name="file" />
                        <span className={styles.fileName}>{f.name}</span>
                        <span className={f.error ? styles.fileError : styles.fileState}>
                          {f.error ? f.error : f.key ? "Uploaded" : "Uploading…"}
                        </span>
                        <button type="button" className={styles.remove} onClick={() => removeFile(d, i)}>
                          <Icon name="close" size={16} label={`Remove ${f.name}`} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}

            {draft.mode === "link" && (
              <input
                type="url"
                inputMode="url"
                placeholder="https://"
                aria-label={`Link for ${d.title}`}
                className={inputClass}
                value={draft.url}
                onChange={(e) => update(d.id, { url: e.target.value })}
              />
            )}

            {draft.mode === "text" && (
              <>
                <textarea
                  aria-label={`Text for ${d.title}`}
                  className={inputClass}
                  rows={6}
                  value={draft.text}
                  onChange={(e) => update(d.id, { text: e.target.value })}
                />
                {(d.min_words || d.max_words) && (
                  <p className={styles.wordCount} aria-live="polite">
                    {words} words
                    {d.min_words && d.max_words
                      ? ` · aim for ${d.min_words} to ${d.max_words}`
                      : d.min_words
                        ? ` · at least ${d.min_words}`
                        : ` · at most ${d.max_words}`}
                  </p>
                )}
              </>
            )}

            {d.sections.length > 0 && (
              <p className={styles.description}>Use these headings: {d.sections.join(", ")}.</p>
            )}

            {errors.map((message) => (
              <p key={message} className={styles.problem}>
                <Icon name="alert" size={16} />
                {message}
              </p>
            ))}
          </fieldset>
        );
      })}

      {formError && <Notice>{formError}</Notice>}
      {success && <Notice tone="info">{success}</Notice>}

      <Button type="submit" busy={busy} icon="upload" className={styles.submit}>
        {busy ? "Handing in…" : "Hand in this attempt"}
      </Button>
      <p className={styles.footnote}>Every attempt is kept. Handing in again never changes an earlier attempt.</p>
    </form>
  );
}
