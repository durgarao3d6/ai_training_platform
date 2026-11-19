"use client";

import Link from "next/link";
import { forwardRef, useEffect, useId, useRef } from "react";

import { Icon, type IconName } from "./Icon";
import { Spinner } from "./Loader";
import styles from "./ui.module.css";

// Loading states live in ./Loader; re-exported so one import covers the whole UI kit.
export {
  Loading,
  PageLoader,
  Skeleton,
  SkeletonCard,
  SkeletonCards,
  SkeletonHero,
  SkeletonRegion,
  SkeletonRows,
  SkeletonStats,
  SkeletonTable,
  SkeletonText,
  Spinner,
} from "./Loader";

// ---------- Button ----------

type Variant = "primary" | "secondary" | "ghost" | "danger" | "onColor";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "md" | "sm";
  icon?: IconName;
  busy?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", icon, busy, children, className, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={`${styles.button} ${styles[variant]} ${size === "sm" ? styles.small : ""} ${className ?? ""}`}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <Spinner size={size === "sm" ? 16 : 18} /> : icon && <Icon name={icon} size={size === "sm" ? 16 : 18} />}
      {children}
    </button>
  );
});

export function ButtonLink({
  href,
  variant = "primary",
  icon,
  children,
}: {
  href: string;
  variant?: Variant;
  icon?: IconName;
  children: React.ReactNode;
}) {
  return (
    <Link href={href} className={`${styles.button} ${styles[variant]}`}>
      {children}
      {icon && <Icon name={icon} />}
    </Link>
  );
}

// ---------- Layout ----------

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <header className={styles.pageHeader}>
      <div>
        {eyebrow && <p className={styles.eyebrow}>{eyebrow}</p>}
        <h1 className={styles.pageTitle}>{title}</h1>
        {description && <p className={styles.pageDescription}>{description}</p>}
      </div>
      {actions && <div className={styles.pageActions}>{actions}</div>}
    </header>
  );
}

export function Card({
  title,
  action,
  children,
  className,
  padded = true,
}: {
  title?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section className={`${styles.card} ${padded ? styles.padded : ""} ${className ?? ""}`}>
      {(title || action) && (
        <div className={styles.cardHead}>
          {title && <h2 className={styles.cardTitle}>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function EmptyState({
  icon = "inbox",
  title,
  children,
  action,
}: {
  icon?: IconName;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className={styles.empty}>
      <span className={styles.emptyIcon}>
        <Icon name={icon} size={22} />
      </span>
      <p className={styles.emptyTitle}>{title}</p>
      {children && <p className={styles.emptyText}>{children}</p>}
      {action}
    </div>
  );
}

export function Notice({ tone = "error", children }: { tone?: "error" | "info"; children: React.ReactNode }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`${styles.notice} ${styles[`notice_${tone}`]}`}>
      <Icon name={tone === "error" ? "alert" : "check"} />
      <div>{children}</div>
    </div>
  );
}

export function Avatar({ name, size = 36, solid = false }: { name: string; size?: number; solid?: boolean }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return (
    <span
      className={`${styles.avatar} ${solid ? styles.avatarSolid : ""}`}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
      aria-hidden="true"
    >
      {initials || "?"}
    </span>
  );
}

// ---------- Forms ----------

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: React.ReactNode;
  error?: string | null;
  children: (props: { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean }) => React.ReactNode;
}) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {hint && (
        <p id={hintId} className={styles.hint}>
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className={styles.fieldError}>
          {error}
        </p>
      )}
    </div>
  );
}

export const inputClass = styles.input;

// ---------- Dialog ----------

/** Native modal dialog: focus moves inside, Escape closes, the page behind is inert. */
export function Dialog({
  open,
  title,
  description,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  // Hold the page still while the dialog is open, so scrolling only moves the dialog.
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`${styles.dialog} ${wide ? styles.dialogWide : ""}`}
      aria-labelledby={titleId}
      onClose={onClose}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className={styles.dialogHead}>
        <div>
          <h2 id={titleId} className={styles.dialogTitle}>
            {title}
          </h2>
          {description && <p className={styles.dialogDescription}>{description}</p>}
        </div>
        <button type="button" className={styles.iconButton} onClick={onClose}>
          <Icon name="close" label="Close" />
        </button>
      </div>
      {open && <div className={styles.dialogBody}>{children}</div>}
    </dialog>
  );
}

export function FormActions({ children }: { children: React.ReactNode }) {
  return <div className={styles.formActions}>{children}</div>;
}
