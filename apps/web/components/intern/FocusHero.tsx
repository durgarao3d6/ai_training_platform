import { ButtonLink } from "@/components/ui/primitives";
import { EMPTY, ROLE_NAMES, TASK_STATUS } from "@/lib/microcopy";
import type { EnrollmentDashboard } from "@/lib/types";

import { HERO_LINE, HERO_NOTHING } from "./copy";
import { courseState } from "./courseStatus";
import styles from "./intern.module.css";

/** The one thing to do next, taken from the course that needs attention most. */
export function FocusHero({ enrollment }: { enrollment: EnrollmentDashboard }) {
  const current = enrollment.current;
  const course = `${ROLE_NAMES[enrollment.role_profile]} · ${enrollment.course_title}`;

  if (!current) {
    return (
      <section className={styles.hero} data-track={enrollment.role_profile} aria-labelledby="focus-title">
        <span className={styles.pill}>{courseState(enrollment).label}</span>
        <h2 id="focus-title" className={styles.heroTitle}>
          {HERO_NOTHING}
        </h2>
        <p className={styles.heroCourse}>{course}</p>
        <p className={styles.heroText}>{EMPTY.nothingWaiting}</p>
        <div className={styles.heroActions}>
          <ButtonLink href={`/intern/courses/${enrollment.enrollment_id}`} icon="right">
            Open this course
          </ButtonLink>
        </div>
      </section>
    );
  }

  const milestone = enrollment.milestones.find((m) =>
    m.tasks.some((t) => t.task_instance_id === current.task_instance_id),
  );
  const where = milestone
    ? `Milestone ${milestone.position} of ${enrollment.milestones.length}`
    : current.milestone_title;

  return (
    <section className={styles.hero} data-track={enrollment.role_profile} aria-labelledby="focus-title">
      <span className={styles.pill}>
        {where} · {TASK_STATUS[current.status].label}
      </span>
      <h2 id="focus-title" className={styles.heroTitle}>
        {current.title}
      </h2>
      <p className={styles.heroCourse}>{course}</p>
      <p className={styles.heroText}>{HERO_LINE[current.status]}</p>
      <div className={styles.heroActions}>
        <ButtonLink href={`/intern/tasks/${current.task_instance_id}`} icon="right">
          Continue the task
        </ButtonLink>
      </div>
    </section>
  );
}
