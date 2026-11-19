"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import styles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { formatDay } from "@/components/admin/TrackChip";
import { useAction } from "@/components/admin/useAction";
import { Icon } from "@/components/ui/Icon";
import {
  Avatar,
  Button,
  Dialog,
  EmptyState,
  Field,
  FormActions,
  inputClass,
  Loading,
  Notice,
  PageHeader,
  SkeletonCards,
} from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { EMPTY } from "@/lib/microcopy";
import type { CohortDetail, CohortSummary, UserView } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function CohortsPage() {
  const router = useRouter();
  const cohorts = useApi<CohortSummary[]>("/admin/cohorts");
  const trainers = useApi<UserView[]>("/admin/users?role=trainer");
  const [open, setOpen] = useState(false);
  const action = useAction();

  // Trainers only fill the dialog's dropdown, so the list never waits on them.
  const trainersPending = trainers.loading && !trainers.data;

  function close() {
    setOpen(false);
    action.reset();
  }

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const startsOn = String(form.get("starts_on") ?? "");
    const trainerId = String(form.get("trainer_id") ?? "");
    const created = await action.run(() =>
      api.post<CohortDetail>("/admin/cohorts", {
        name: String(form.get("name") ?? "").trim(),
        starts_on: startsOn || null,
        trainer_id: trainerId || null,
      }),
    );
    if (created) router.push(`/admin/cohorts/${created.id}`);
  }

  return (
    <>
      <PageHeader
        eyebrow="People"
        title="Cohorts"
        description="A cohort is a group of interns who start together under one trainer. Enroll interns from the cohort page."
        actions={
          <Button icon="plus" onClick={() => setOpen(true)}>
            New cohort
          </Button>
        }
      />

      {cohorts.loading && !cohorts.data ? (
        <SkeletonCards count={4} lines={2} label="Loading cohorts…" />
      ) : cohorts.error ? (
        <Notice>{EMPTY.loadFailed}</Notice>
      ) : cohorts.data && cohorts.data.length ? (
        <ul className={styles.cohortGrid} aria-label="Cohorts">
          {cohorts.data.map((c) => (
            <li key={c.id}>
              <Link href={`/admin/cohorts/${c.id}`} className={styles.cohortCard}>
                <h2 className={styles.cohortName}>{c.name}</h2>
                <p className={styles.muted}>
                  <Icon name="calendar" size={16} /> {formatDay(c.starts_on)}
                </p>
                <div className={styles.cohortFoot}>
                  {c.trainer_name ? (
                    <span className={styles.person}>
                      <Avatar name={c.trainer_name} size={32} />
                      <span>
                        <span className={styles.personName}>{c.trainer_name}</span>
                        <span className={styles.personSub}> Trainer</span>
                      </span>
                    </span>
                  ) : (
                    <span>No trainer yet</span>
                  )}
                  <span>
                    {c.enrollment_count} enrolled
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <section className={styles.milestone}>
          <EmptyState
            icon="users"
            title="No cohorts yet"
            action={
              <Button icon="plus" onClick={() => setOpen(true)}>
                New cohort
              </Button>
            }
          >
            Create a cohort, then enroll interns in it.
          </EmptyState>
        </section>
      )}

      <Dialog open={open} title="New cohort" description="You can enroll interns once the cohort exists." onClose={close}>
        <form onSubmit={create} className={styles.form}>
          <ErrorList errors={action.errors} />
          <Field label="Name">
            {(p) => <input {...p} name="name" className={inputClass} required maxLength={200} />}
          </Field>
          <Field label="Start date" hint="Optional.">
            {(p) => <input {...p} name="starts_on" type="date" className={inputClass} />}
          </Field>
          {trainersPending ? (
            <Loading label="Loading trainers…" delayMs={0} />
          ) : (
            <Field label="Trainer" hint="Optional. You can set or change it later.">
              {(p) => (
                <select {...p} name="trainer_id" className={inputClass} defaultValue="">
                  <option value="">No trainer yet</option>
                  {trainers.data?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name}
                    </option>
                  ))}
                </select>
              )}
            </Field>
          )}
          <FormActions>
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button type="submit" busy={action.busy} disabled={trainersPending}>
              Create cohort
            </Button>
          </FormActions>
        </form>
      </Dialog>
    </>
  );
}
