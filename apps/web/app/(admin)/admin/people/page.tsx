"use client";

import { useState } from "react";

import styles from "@/components/admin/admin.module.css";
import { ErrorList } from "@/components/admin/ErrorList";
import { formatStamp } from "@/components/admin/TrackChip";
import { useAction } from "@/components/admin/useAction";
import { StatusChip } from "@/components/status/StatusChip";
import {
  Avatar,
  Button,
  Card,
  Dialog,
  EmptyState,
  Field,
  FormActions,
  inputClass,
  Notice,
  PageHeader,
  SkeletonTable,
} from "@/components/ui/primitives";
import { api, type Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EMPTY } from "@/lib/microcopy";
import type { UserView } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Filter = "all" | Role;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "intern", label: "Interns" },
  { value: "trainer", label: "Trainers" },
  { value: "hr", label: "HR" },
  { value: "admin", label: "Admins" },
];

const ROLE_LABEL: Record<Role, string> = { intern: "Intern", trainer: "Trainer", hr: "HR", admin: "Admin" };

function isRole(value: string): value is Role {
  return value in ROLE_LABEL;
}

export default function PeoplePage() {
  const { user } = useAuth();
  const isAdmin = user?.roles.includes("admin") ?? false;
  const [filter, setFilter] = useState<Filter>("all");
  const people = useApi<UserView[]>(filter === "all" ? "/admin/users" : `/admin/users?role=${filter}`);
  const [open, setOpen] = useState(false);
  const action = useAction();

  function close() {
    setOpen(false);
    action.reset();
  }

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const chosen = String(form.get("role") ?? "intern");
    const created = await action.run(() =>
      api.post<UserView>("/admin/users", {
        full_name: String(form.get("full_name") ?? "").trim(),
        email: String(form.get("email") ?? "").trim(),
        role: isAdmin && isRole(chosen) ? chosen : "intern",
        password: String(form.get("password") ?? ""),
      }),
    );
    if (created) {
      close();
      people.reload();
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="People"
        title="People"
        description={
          isAdmin
            ? "Everyone with an account. New accounts get a temporary password to share securely."
            : "Intern accounts. New accounts get a temporary password to share securely."
        }
        actions={
          <Button icon="plus" onClick={() => setOpen(true)}>
            New account
          </Button>
        }
      />

      <div className={styles.filterBar}>
        <fieldset className={styles.segmented}>
          <legend>Filter by role</legend>
          {FILTERS.map((f) => (
            <label key={f.value} className={styles.segment}>
              <input
                type="radio"
                name="role-filter"
                value={f.value}
                checked={filter === f.value}
                onChange={() => setFilter(f.value)}
              />
              <span>{f.label}</span>
            </label>
          ))}
        </fieldset>
        {people.data && (
          <p className={styles.hint} role="status">
            {people.data.length} {people.data.length === 1 ? "person" : "people"}
          </p>
        )}
      </div>

      <Card>
        {people.loading && !people.data ? (
          <SkeletonTable rows={6} columns={4} label="Loading people…" />
        ) : people.error ? (
          <Notice>{EMPTY.loadFailed}</Notice>
        ) : people.data && people.data.length ? (
          <div className={styles.tableWrap}>
            <table className={styles.table} data-density="default">
              <caption>People with an account</caption>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Email</th>
                  <th scope="col">Role</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {people.data.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <span className={styles.person}>
                        <Avatar name={p.full_name} size={32} />
                        <span className={styles.personName}>{p.full_name}</span>
                      </span>
                    </td>
                    <td className={styles.muted}>{p.email}</td>
                    <td>
                      <div className={styles.chips}>
                        {p.roles.map((r) => (
                          <StatusChip key={r} label={isRole(r) ? ROLE_LABEL[r] : r} tone={r === "admin" ? "review" : "neutral"} />
                        ))}
                      </div>
                    </td>
                    <td className={styles.muted}>{formatStamp(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon="user"
            title={filter === "all" ? "No accounts yet" : "No one with this role yet"}
            action={
              <Button icon="plus" onClick={() => setOpen(true)}>
                New account
              </Button>
            }
          >
            {isAdmin ? "Create an account and share the temporary password securely." : "Create an intern account and share the temporary password securely."}
          </EmptyState>
        )}
      </Card>

      <Dialog
        open={open}
        title="New account"
        description={isAdmin ? "The person signs in with this email and the temporary password." : "HR creates intern accounts. The intern signs in with this email and the temporary password."}
        onClose={close}
      >
        <form onSubmit={create} className={styles.form}>
          <ErrorList errors={action.errors} />
          <Field label="Full name">
            {(p) => <input {...p} name="full_name" className={inputClass} required maxLength={200} autoComplete="off" />}
          </Field>
          <Field label="Email">
            {(p) => <input {...p} name="email" type="email" className={inputClass} required autoComplete="off" />}
          </Field>
          {isAdmin && (
            <Field label="Role">
              {(p) => (
                <select {...p} name="role" className={inputClass} defaultValue="intern">
                  <option value="intern">Intern</option>
                  <option value="trainer">Trainer</option>
                  <option value="hr">HR</option>
                  <option value="admin">Admin</option>
                </select>
              )}
            </Field>
          )}
          <Field label="Temporary password" hint="At least 12 characters. Share it securely, not by chat or email in plain text.">
            {(p) => <input {...p} name="password" type="password" className={inputClass} required minLength={12} maxLength={1024} autoComplete="new-password" />}
          </Field>
          <FormActions>
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button type="submit" busy={action.busy}>
              Create account
            </Button>
          </FormActions>
        </form>
      </Dialog>
    </>
  );
}
