"use client";

import { CourseList } from "@/components/intern/CourseList";
import { useDashboard } from "@/components/intern/useDashboard";
import { Card, EmptyState, Notice, PageHeader, SkeletonCards } from "@/components/ui/primitives";
import { EMPTY } from "@/lib/microcopy";

/** All of the intern's courses, filterable by status. */
export default function MyCourses() {
  const { data, error, loading } = useDashboard();

  const header = (
    <PageHeader
      title="My courses"
      description="Every course you are enrolled in, with the ones that need you first."
    />
  );

  if (loading) {
    return (
      <>
        {header}
        <SkeletonCards count={3} lines={3} label="Loading your courses…" />
      </>
    );
  }
  if (error || !data) return <Notice>{EMPTY.loadFailed}</Notice>;

  return (
    <>
      {header}
      {data.enrollments.length ? (
        <CourseList enrollments={data.enrollments} />
      ) : (
        <Card>
          <EmptyState icon="book" title="No course yet">
            {EMPTY.notEnrolled}
          </EmptyState>
        </Card>
      )}
    </>
  );
}
