import type { ComponentKind } from "@/lib/types";

export const KIND_LABEL: Record<ComponentKind, string> = {
  resource: "Link",
  reading_note: "Reading note",
  quiz: "Self-check quiz",
  starter_file: "Starter file",
};

/** One short line describing a component's content, for lists and proposals. */
export function componentSummary(kind: ComponentKind, payload: Record<string, unknown>): string {
  switch (kind) {
    case "resource":
      return `${String(payload.url ?? "")}${payload.note ? `, ${String(payload.note)}` : ""}`;
    case "reading_note":
      return String(payload.body ?? "").slice(0, 240);
    case "quiz": {
      const count = Array.isArray(payload.questions) ? payload.questions.length : 0;
      return `${count} question${count === 1 ? "" : "s"}`;
    }
    case "starter_file":
      return `${String(payload.filename ?? "")}${payload.description ? `, ${String(payload.description)}` : ""}`;
  }
}
