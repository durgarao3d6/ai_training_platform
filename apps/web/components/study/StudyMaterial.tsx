"use client";

import { useId, useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { Loading, Notice } from "@/components/ui/primitives";
import { ApiError } from "@/lib/api";
import type { QuizQuestion, StudyItem, StudyMaterialView } from "@/lib/types";
import { useApi } from "@/lib/useApi";

import { SelfCheckQuiz } from "./SelfCheckQuiz";
import styles from "./study.module.css";

const KIND: Record<StudyItem["type"], string> = {
  reading_note: "Reading",
  resource: "Link",
  quiz: "Self-check",
  starter_file: "Starter file",
};

/** The approved study material for one milestone, read before doing its tasks. */
export function StudyMaterial({ moduleId }: { moduleId: string }) {
  const study = useApi<StudyMaterialView>(`/modules/${moduleId}/study`);

  if (study.loading && !study.data) return <Loading label="Loading study material…" />;
  if (study.error) {
    const locked = study.error instanceof ApiError && study.error.status === 403;
    return (
      <Notice tone={locked ? "info" : "error"}>
        {locked ? "Study material opens with this milestone." : "Study material could not be loaded. Try again."}
      </Notice>
    );
  }
  const items = study.data?.items ?? [];
  if (items.length === 0) {
    return <p className={styles.muted}>No study material yet. Your trainer is preparing it; you can start the task.</p>;
  }
  return (
    <ul className={styles.items}>
      {items.map((item) => (
        <li key={item.id} className={styles.item}>
          <div className={styles.itemHead}>
            <h4 className={styles.itemTitle}>{item.title}</h4>
            <span className={styles.kind}>{KIND[item.type]}</span>
          </div>
          <ItemBody item={item} />
        </li>
      ))}
    </ul>
  );
}

function ItemBody({ item }: { item: StudyItem }) {
  const p = item.payload;
  switch (item.type) {
    case "reading_note":
      return <p className={`prose ${styles.body}`}>{String(p.body ?? "")}</p>;
    case "resource":
      return (
        <>
          <p className={styles.body}>
            <a className={styles.link} href={String(p.url)} target="_blank" rel="noopener noreferrer">
              {String(p.url)}
              <span className="visually-hidden"> (opens in a new tab)</span>
            </a>
          </p>
          {Boolean(p.note) && <p className={styles.muted}>{String(p.note)}</p>}
        </>
      );
    case "quiz":
      return <SelfCheckQuiz questions={(p.questions ?? []) as QuizQuestion[]} />;
    case "starter_file":
      return (
        <p className={styles.body}>
          <code>{String(p.filename ?? "")}</code>
          {p.description ? `: ${String(p.description)}` : ""}
        </p>
      );
  }
}

/** "1. Study" step for a milestone card. Content loads only when opened. */
export function StudyStep({ moduleId, defaultOpen }: { moduleId: string; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <section className={styles.step} aria-label="Study material">
      <p className={styles.stepHead}>
        <span className={styles.stepNumber}>1</span>
        Study
      </p>
      <button
        type="button"
        className={styles.toggle}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name={open ? "up" : "down"} size={16} />
        {open ? "Hide study material" : "Show study material"}
      </button>
      <div id={panelId} hidden={!open}>
        {open && <StudyMaterial moduleId={moduleId} />}
      </div>
    </section>
  );
}

export function TaskStepHead() {
  return (
    <p className={`${styles.stepHead} ${styles.step}`}>
      <span className={styles.stepNumber}>2</span>
      Do the task
    </p>
  );
}
