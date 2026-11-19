import Link from "next/link";

import { StatusChip } from "@/components/status/StatusChip";
import { Icon } from "@/components/ui/Icon";
import { ROLE_NAMES } from "@/lib/microcopy";
import type { EnrollmentDashboard } from "@/lib/types";

import { courseState } from "./courseStatus";
import styles from "./intern.module.css";
import { ProgressSegments } from "./Milestones";

/** One course as a floating card. The whole card is one link (stretched from the title). */
export function CourseCard({ enrollment, large = false }: { enrollment: EnrollmentDashboard; large?: boolean }) {
  const state = courseState(enrollment);
  return (
    <article className={`${styles.courseCard} ${large ? styles.courseCardLarge : ""}`} data-track={enrollment.role_profile}>
      <div className={styles.cardBand}>
        <span className={styles.trackPill}>{ROLE_NAMES[enrollment.role_profile]}</span>
      </div>
      <div className={styles.cardBody}>
        <h3 className={styles.courseTitle}>
          <Link href={`/intern/courses/${enrollment.enrollment_id}`} className={styles.courseLink}>
            {enrollment.course_title}
          </Link>
        </h3>
        <div>
          <StatusChip label={state.label} tone={state.tone} />
        </div>
        <ProgressSegments milestones={enrollment.milestones} />
        {enrollment.current && (
          <p className={styles.nextTask}>
            <span className={styles.nextTaskLabel}>Current task</span>
            {enrollment.current.title}
          </p>
        )}
        {large && (
          <p className={styles.cardMeta}>
            {enrollment.cohort_name}
            {enrollment.trainer_name ? ` · Trainer: ${enrollment.trainer_name}` : ""}
          </p>
        )}
        <span className={styles.cardArrow} aria-hidden="true">
          <Icon name="right" size={18} />
        </span>
      </div>
    </article>
  );
}
