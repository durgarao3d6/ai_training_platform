"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { COURSE_NOT_FOUND, NO_MILESTONES } from "@/components/intern/copy";
import { courseState } from "@/components/intern/courseStatus";
import styles from "@/components/intern/intern.module.css";
import { MilestoneTimeline, ProgressSegments } from "@/components/intern/Milestones";
import { useDashboard } from "@/components/intern/useDashboard";
import { StatusChip } from "@/components/status/StatusChip";
import { Icon } from "@/components/ui/Icon";
import {
  ButtonLink,
  Card,
  EmptyState,
  Notice,
  PageHeader,
  Skeleton,
  SkeletonRegion,
  SkeletonRows,
} from "@/components/ui/primitives";
import { EMPTY, ROLE_NAMES } from "@/lib/microcopy";

/** Said the same way whether the course title is known yet or not, so the header does not move. */
const MAP_INTRO = "Milestones open one at a time. The next one opens when your trainer approves the current one.";

function BackToCourses() {
  return (
    <Link href="/intern/courses" className={styles.back}>
      <Icon name="right" size={16} />
      All courses
    </Link>
  );
}

/** Stand-in for the track-coloured summary card: status pill, progress panel, action, facts. */
function SummarySkeleton() {
  return (
    <SkeletonRegion label="Loading the course summary…">
      <div className={styles.summarySkeleton}>
        <div className={styles.summarySkeletonMain}>
          <Skeleton width={128} height={28} radius="var(--radius-full)" />
          <Skeleton width="100%" height={76} radius="var(--radius-md)" />
          <Skeleton width={176} height={44} radius="var(--radius-full)" />
        </div>
        <div className={styles.summarySkeletonFacts}>
          <Skeleton height={14} />
          <Skeleton height={14} />
          <Skeleton height={14} />
        </div>
      </div>
    </SkeletonRegion>
  );
}

/** Course map for one enrollment: complete, open and locked milestones; locked ones say what unlocks them (FR-INT-02). */
export default function CourseMap() {
  const { enrollmentId } = useParams<{ enrollmentId: string }>();
  const { data, error, loading } = useDashboard();

  // The heading and the way back are known before any data lands, so only the
  // summary card and the timeline wait, each on its own.
  if (loading && !data) {
    return (
      <>
        <BackToCourses />
        <PageHeader title="Your course map" description={MAP_INTRO} />
        <SummarySkeleton />
        <SkeletonRows rows={4} height={132} label="Loading the milestones…" />
      </>
    );
  }
  if (error || !data) return <Notice>{EMPTY.loadFailed}</Notice>;

  const enrollment = data.enrollments.find((e) => e.enrollment_id === enrollmentId);
  if (!enrollment) {
    return (
      <>
        <PageHeader title="Course not found" />
        <Card>
          <EmptyState icon="map" title="We could not find that course" action={<Link href="/intern/courses">Back to my courses</Link>}>
            {COURSE_NOT_FOUND}
          </EmptyState>
        </Card>
      </>
    );
  }

  const state = courseState(enrollment);

  return (
    <>
      <BackToCourses />
      <PageHeader
        eyebrow={`${ROLE_NAMES[enrollment.role_profile]} track`}
        title={enrollment.course_title}
        description={MAP_INTRO}
      />

      <section className={styles.summary} data-track={enrollment.role_profile} aria-label="Course summary">
        <div className={styles.summaryMain}>
          <div>
            <StatusChip label={state.label} tone={state.tone} />
          </div>
          <div className={styles.summaryProgress}>
            <ProgressSegments milestones={enrollment.milestones} />
          </div>
          {enrollment.current && (
            <div>
              <ButtonLink href={`/intern/tasks/${enrollment.current.task_instance_id}`} icon="right">
                Continue the task
              </ButtonLink>
            </div>
          )}
        </div>
        <dl className={styles.facts}>
          <div>
            <dt>Track</dt>
            <dd>{ROLE_NAMES[enrollment.role_profile]}</dd>
          </div>
          <div>
            <dt>Cohort</dt>
            <dd>{enrollment.cohort_name}</dd>
          </div>
          <div>
            <dt>Trainer</dt>
            <dd>{enrollment.trainer_name ?? "Not assigned yet"}</dd>
          </div>
        </dl>
      </section>

      {enrollment.milestones.length ? (
        <MilestoneTimeline milestones={enrollment.milestones} />
      ) : (
        <Card>
          <EmptyState icon="map" title="No milestones yet">
            {NO_MILESTONES}
          </EmptyState>
        </Card>
      )}
    </>
  );
}
