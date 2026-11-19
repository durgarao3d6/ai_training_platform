"use client";

import { Button, Field, inputClass } from "@/components/ui/primitives";
import type { Deliverable, DeliverableKind } from "@/lib/types";

import styles from "./admin.module.css";

/** Editable form of one deliverable. Numbers are kept as strings while typing. */
export interface DeliverableDraft {
  id: string;
  title: string;
  description: string;
  kinds: DeliverableKind[];
  required: boolean;
  accept: string;
  min_words: string;
  max_words: string;
  min_count: string;
  max_count: string;
  min_items: string;
  sections: string;
}

const KINDS: { kind: DeliverableKind; label: string }[] = [
  { kind: "file", label: "File" },
  { kind: "link", label: "Link" },
  { kind: "text", label: "Text" },
];

const toList = (value: string) =>
  value
    .split(/[\n,]/)
    .map((v) => v.trim())
    .filter(Boolean);

const toNumber = (value: string) => (value.trim() === "" ? null : Number(value));

const slug = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 40) || "item";

/** The API returns `kinds`; it accepts `kind`. Everything else round-trips unchanged. */
export function draftsFromDeliverables(items: Deliverable[]): DeliverableDraft[] {
  // The generic one-item manifest ("work") is what the API uses when none is set: show it as empty.
  if (items.length === 1 && items[0].id === "work") return [];
  return items.map((d) => ({
    id: d.id,
    title: d.title,
    description: d.description,
    kinds: d.kinds,
    required: d.required,
    accept: d.accept.join(", "),
    min_words: d.min_words?.toString() ?? "",
    max_words: d.max_words?.toString() ?? "",
    min_count: d.min_count?.toString() ?? "",
    max_count: d.max_count?.toString() ?? "",
    min_items: d.min_items?.toString() ?? "",
    sections: d.sections.join("\n"),
  }));
}

export function deliverablesPayload(drafts: DeliverableDraft[]) {
  return drafts.map((d) => ({
    id: d.id || slug(d.title),
    title: d.title.trim(),
    description: d.description.trim(),
    kind: d.kinds,
    required: d.required,
    accept: d.kinds.includes("file")
      ? toList(d.accept).map((a) => (a.startsWith(".") ? a.toLowerCase() : `.${a.toLowerCase()}`))
      : [],
    min_words: toNumber(d.min_words),
    max_words: toNumber(d.max_words),
    min_count: toNumber(d.min_count),
    max_count: toNumber(d.max_count),
    min_items: toNumber(d.min_items),
    sections: toList(d.sections),
  }));
}

const empty = (): DeliverableDraft => ({
  id: "",
  title: "",
  description: "",
  kinds: ["file"],
  required: true,
  accept: "",
  min_words: "",
  max_words: "",
  min_count: "",
  max_count: "",
  min_items: "",
  sections: "",
});

export function DeliverablesEditor({
  value,
  onChange,
}: {
  value: DeliverableDraft[];
  onChange: (next: DeliverableDraft[]) => void;
}) {
  const change = (index: number, patch: Partial<DeliverableDraft>) =>
    onChange(value.map((item, i) => (i === index ? { ...item, ...patch } : item)));

  const toggleKind = (index: number, kind: DeliverableKind) => {
    const current = value[index].kinds;
    const next = current.includes(kind) ? current.filter((k) => k !== kind) : [...current, kind];
    if (next.length) change(index, { kinds: next }); // at least one kind stays selected
  };

  return (
    <section aria-label="Deliverables" className={styles.form}>
      <div className={styles.subhead}>
        <h3>What to hand in</h3>
        <Button variant="ghost" size="sm" icon="plus" onClick={() => onChange([...value, empty()])}>
          Add deliverable
        </Button>
      </div>
      {!value.length && (
        <p className={styles.mutedSmall}>
          Nothing listed: interns hand in one piece of work as a file, a link or text.
        </p>
      )}
      {value.map((item, index) => (
        <div key={index} className={styles.itemBox}>
          <div className={styles.itemHead}>
            <strong>Deliverable {index + 1}</strong>
            <Button
              variant="ghost"
              size="sm"
              icon="trash"
              onClick={() => onChange(value.filter((_, i) => i !== index))}
            >
              Remove
            </Button>
          </div>
          <div className={styles.grid2}>
            <Field label="Title">
              {(p) => (
                <input
                  {...p}
                  className={inputClass}
                  value={item.title}
                  required
                  maxLength={200}
                  onChange={(e) => change(index, { title: e.target.value })}
                />
              )}
            </Field>
            <Field label="Description">
              {(p) => (
                <input
                  {...p}
                  className={inputClass}
                  value={item.description}
                  maxLength={2000}
                  onChange={(e) => change(index, { description: e.target.value })}
                />
              )}
            </Field>
          </div>
          <fieldset className={styles.checks}>
            <legend>Accepted as</legend>
            {KINDS.map(({ kind, label }) => (
              <label key={kind} className={styles.check}>
                <input type="checkbox" checked={item.kinds.includes(kind)} onChange={() => toggleKind(index, kind)} />
                {label}
              </label>
            ))}
            <label className={styles.check}>
              <input
                type="checkbox"
                checked={item.required}
                onChange={(e) => change(index, { required: e.target.checked })}
              />
              Required
            </label>
          </fieldset>
          {item.kinds.includes("file") && (
            <Field label="File types" hint="Comma-separated, for example .py, .md">
              {(p) => (
                <input
                  {...p}
                  className={inputClass}
                  value={item.accept}
                  onChange={(e) => change(index, { accept: e.target.value })}
                />
              )}
            </Field>
          )}
          <div className={styles.grid3}>
            {item.kinds.includes("text") && (
              <>
                <Field label="Min words">
                  {(p) => (
                    <input {...p} type="number" min={1} className={inputClass} value={item.min_words}
                      onChange={(e) => change(index, { min_words: e.target.value })} />
                  )}
                </Field>
                <Field label="Max words">
                  {(p) => (
                    <input {...p} type="number" min={1} className={inputClass} value={item.max_words}
                      onChange={(e) => change(index, { max_words: e.target.value })} />
                  )}
                </Field>
              </>
            )}
            <Field label="Min files or links">
              {(p) => (
                <input {...p} type="number" min={1} className={inputClass} value={item.min_count}
                  onChange={(e) => change(index, { min_count: e.target.value })} />
              )}
            </Field>
            <Field label="Max files or links">
              {(p) => (
                <input {...p} type="number" min={1} className={inputClass} value={item.max_count}
                  onChange={(e) => change(index, { max_count: e.target.value })} />
              )}
            </Field>
            <Field label="Min parsed items" hint="For example test cases.">
              {(p) => (
                <input {...p} type="number" min={1} className={inputClass} value={item.min_items}
                  onChange={(e) => change(index, { min_items: e.target.value })} />
              )}
            </Field>
          </div>
          <Field label="Required headings" hint="One per line. Leave empty if the document has no fixed structure.">
            {(p) => (
              <textarea {...p} className={inputClass} rows={2} value={item.sections}
                onChange={(e) => change(index, { sections: e.target.value })} />
            )}
          </Field>
        </div>
      ))}
    </section>
  );
}
