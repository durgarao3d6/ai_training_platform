import Link from "next/link";

import { StatusChip } from "@/components/status/StatusChip";
import { StudyStep, TaskStepHead } from "@/components/study/StudyMaterial";
import { Icon } from "@/components/ui/Icon";
import { MILESTONE_STATUS, TASK_STATUS } from "@/lib/microcopy";
import type { MilestoneView } from "@/lib/types";

import styles from "./intern.module.css";

/** Segmented progress: one segment per milestone. The text label carries the meaning. */
export function ProgressSegments({ milestones }: { milestones: MilestoneView[] }) {
  const complete = milestones.filter((m) => m.status === "complete").length;
  return (
    <div className={styles.progress}>
      <div className={styles.segments} aria-hidden="true">
        {milestones.map((m) => (
          <span key={m.id} className={`${styles.segment} ${styles[`segment_${m.status}`]}`} />
        ))}
      </div>
      <p className={styles.progressLabel}>
        {milestones.length ? `${complete} of ${milestones.length} milestones complete` : "No milestones yet"}
      </p>
    </div>
  );
}

function Marker({ status, position }: { status: MilestoneView["status"]; position: number }) {
  return (
    <span className={`${styles.marker} ${styles[`marker_${status}`]}`} aria-hidden="true">
      {status === "complete" ? <Icon name="check" size={16} /> : position}
    </span>
  );
}

/** The next four steps of one course: done, current, then locked with the reason. */
export function UpNext({ milestones }: { milestones: MilestoneView[] }) {
  const firstOpen = milestones.findIndex((m) => m.status !== "complete");
  const anchor = firstOpen === -1 ? milestones.length : firstOpen;
  const start = Math.max(0, Math.min(anchor, milestones.length - 4));
  const steps = milestones.slice(start, start + 4);

  return (
    <ol className={styles.steps}>
      {steps.map((m) => (
        <li key={m.id} className={styles.step}>
          <Marker status={m.status} position={m.position} />
          <div>
            <p className={`${styles.stepTitle} ${m.status === "locked" ? styles.stepTitleMuted : ""}`}>{m.title}</p>
            <p className={styles.stepNote}>
              {m.status === "complete" && "Complete"}
              {m.status === "unlocked" && "You are here"}
              {m.status === "locked" && m.reason}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}

/** Full vertical timeline for the course map. Locked milestones say what unlocks them (FR-INT-02). */
export function MilestoneTimeline({ milestones }: { milestones: MilestoneView[] }) {
  return (
    <ol className={styles.timeline}>
      {milestones.map((m) => {
        const status = MILESTONE_STATUS[m.status];
        return (
          <li key={m.id} className={`${styles.timelineItem} ${styles[`item_${m.status}`]}`}>
            <Marker status={m.status} position={m.position} />
            <div className={styles.timelineCard}>
              <div className={styles.timelineHead}>
                <span className={styles.eyebrowSmall}>Milestone {m.position}</span>
                <StatusChip label={status.label} tone={status.tone} />
              </div>
              <h2 className={styles.timelineTitle}>{m.title}</h2>
              {m.status !== "unlocked" && m.reason && <p className={styles.reason}>{m.reason}</p>}
              {m.status !== "locked" && <StudyStep moduleId={m.id} defaultOpen={m.status === "unlocked"} />}
              {m.status !== "locked" && m.tasks.length > 0 && <TaskStepHead />}
              {m.status !== "locked" && m.tasks.length > 0 && (
                <ul className={styles.taskLinks}>
                  {m.tasks.map((t) => {
                    const ts = TASK_STATUS[t.status];
                    return (
                      <li key={t.task_instance_id}>
                        <Link href={`/intern/tasks/${t.task_instance_id}`} className={styles.taskLink}>
                          <span className={styles.taskLinkTitle}>{t.title}</span>
                          <StatusChip label={ts.label} tone={ts.tone} />
                          <Icon name="right" />
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
