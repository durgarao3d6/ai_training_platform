// Submission client calls (task 4.3). Replaced by the generated OpenAPI client in task 1.4.

import { apiFetch, ApiError } from "./api";
import type { SubmissionSummary, SubmissionView } from "./types";

export type ArtifactPayload =
  | { deliverable_id: string; kind: "file"; upload_key: string }
  | { deliverable_id: string; kind: "link"; url: string }
  | { deliverable_id: string; kind: "text"; text: string };

interface SignedUpload {
  upload_key: string;
  url: string;
  fields: Record<string, string>;
  expires_in: number;
  max_bytes: number;
}

/** Content type sent to storage. The server checks the extension against the task manifest. */
function contentTypeFor(file: File): string {
  return /^[\w.+-]+\/[\w.+-]+$/.test(file.type) ? file.type : "application/octet-stream";
}

/** Sign, then post the file straight to storage. Returns the key to cite in the submission. */
export async function uploadFile(taskInstanceId: string, deliverableId: string, file: File): Promise<string> {
  const contentType = contentTypeFor(file);
  const signed = await apiFetch<SignedUpload>("/uploads/sign", {
    method: "POST",
    body: JSON.stringify({
      task_instance_id: taskInstanceId,
      deliverable_id: deliverableId,
      filename: file.name,
      content_type: contentType,
      size_bytes: file.size,
    }),
  });

  const form = new FormData();
  for (const [name, value] of Object.entries(signed.fields)) form.append(name, value);
  form.append("Content-Type", contentType);
  form.append("file", file); // must be the last field in an S3 POST
  const response = await fetch(signed.url, { method: "POST", body: form });
  if (!response.ok) {
    throw new ApiError(response.status, "The upload did not finish. Check your connection and try again.");
  }
  return signed.upload_key;
}

export function submit(taskInstanceId: string, artifacts: ArtifactPayload[], idempotencyKey: string) {
  return apiFetch<SubmissionView>(`/task-instances/${taskInstanceId}/submissions`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ artifacts }),
  });
}

export const listSubmissions = (taskInstanceId: string) =>
  apiFetch<SubmissionSummary[]>(`/task-instances/${taskInstanceId}/submissions`);

export const getSubmission = (submissionId: string) => apiFetch<SubmissionView>(`/submissions/${submissionId}`);

/** Downloads need the bearer token, so fetch the file and hand the browser a local object URL. */
export async function downloadArtifact(downloadPath: string, filename: string): Promise<void> {
  const blob = await apiFetch<Blob>(downloadPath.replace(/^\/api\/v1/, ""), {}, true, "blob");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function countWords(text: string): number {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}
