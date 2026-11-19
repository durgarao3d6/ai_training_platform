"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Button, Field, inputClass, Notice } from "@/components/ui/primitives";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { homeFor } from "@/lib/roles";

import styles from "./login.module.css";

function LoginForm() {
  const { signIn } = useAuth();
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const me = await signIn(String(form.get("email")), String(form.get("password")));
      // Only follow same-site relative paths to avoid open redirects.
      const target = next && next.startsWith("/") && !next.startsWith("//") ? next : homeFor(me.roles);
      router.replace(target);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "We could not reach the server. Try again in a moment.");
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      <div>
        <h1 className={styles.title}>Sign in</h1>
        <p className={styles.subtitle}>Use the account your trainer or HR team gave you.</p>
      </div>

      {error && <Notice>{error}</Notice>}

      <Field label="Email">
        {(props) => (
          <input {...props} className={inputClass} name="email" type="email" autoComplete="username" required />
        )}
      </Field>
      <Field label="Password">
        {(props) => (
          <input
            {...props}
            className={inputClass}
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
        )}
      </Field>

      <Button type="submit" busy={busy} className={styles.submit}>
        {busy ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main id="main" className={styles.page}>
      <section className={styles.brandPanel} aria-label="About AITMS">
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true" />
          AITMS
        </div>
        <div className={styles.pitch}>
          <p className={styles.headline}>Practical training, judged by what good looks like in each profession.</p>
          <p className={styles.lede}>
            Real assignments, feedback you can act on, and a trainer who sees your work.
          </p>
          <ul className={styles.tracks}>
            <li>Software Developer</li>
            <li>Business Analyst</li>
            <li>QA Engineer</li>
            <li>UI/UX Designer</li>
          </ul>
        </div>
        <p className={styles.footnote}>Smart Knowledge Portal programme</p>
      </section>

      <section className={styles.formPanel}>
        <Suspense>
          <LoginForm />
        </Suspense>
      </section>
    </main>
  );
}
