"use client";

import { useEffect, useState } from "react";

import styles from "./loader.module.css";

/**
 * Loading states for AITMS.
 *
 * Which one to use:
 * - Skeletons for a page or panel whose shape is known. They keep the layout steady,
 *   so nothing jumps when the data lands. Prefer these.
 * - PageLoader for a whole-page wait where the shape is not known yet (sign-in check, redirect).
 * - Loading for a small inline wait inside a card or dialog.
 * - Spinner inside a button or beside a label you have written yourself.
 *
 * Accessibility: each visible waiting state is one polite live region that announces what is
 * being loaded. The moving parts are decorative and hidden from screen readers. Every animation
 * stops under prefers-reduced-motion.
 */

/** Waits before returning true, so a fast response never shows a flash of spinner. */
function useDelayedShow(delayMs: number): boolean {
  const [show, setShow] = useState(delayMs === 0);
  useEffect(() => {
    if (delayMs === 0) return;
    const timer = setTimeout(() => setShow(true), delayMs);
    return () => clearTimeout(timer);
  }, [delayMs]);
  return show;
}

// ---------- Spinner ----------

/** Rounded arc in the current text colour. Decorative: give the surrounding element the label. */
export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <svg
      className={styles.spinner}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <circle className={styles.track} cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.4" />
      <circle
        className={styles.arc}
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeDasharray="14 43"
      />
    </svg>
  );
}

// ---------- Inline ----------

/** Small inline wait: spinner and label on one line. */
export function Loading({ label = "Loading…", delayMs = 200 }: { label?: string; delayMs?: number }) {
  const show = useDelayedShow(delayMs);
  if (!show) return null;
  return (
    <p role="status" className={styles.inline}>
      <Spinner />
      {label}
    </p>
  );
}

// ---------- Full page ----------

/**
 * Whole-page wait. The four pulsing tiles are the four tracks (Developer, Business Analyst,
 * QA, UI/UX), so the wait carries the product's identity instead of a generic spinner.
 */
export function PageLoader({
  label = "Loading your workspace…",
  delayMs = 200,
}: {
  label?: string;
  delayMs?: number;
}) {
  const show = useDelayedShow(delayMs);
  if (!show) return null;
  return (
    <div role="status" className={styles.page}>
      <span className={styles.marks} aria-hidden="true">
        <span className={styles.mark} />
        <span className={styles.mark} />
        <span className={styles.mark} />
        <span className={styles.mark} />
      </span>
      <p className={styles.pageLabel}>{label}</p>
    </div>
  );
}

// ---------- Skeletons ----------

/** One placeholder block. Width and height accept any CSS length. */
export function Skeleton({
  width = "100%",
  height = 16,
  radius,
  circle = false,
  className,
}: {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  circle?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`${styles.block} ${circle ? styles.circle : ""} ${className ?? ""}`}
      style={{ width, height, borderRadius: circle ? undefined : radius }}
      aria-hidden="true"
    />
  );
}

/** Several lines of placeholder text. The last line is shorter, as real text tends to be. */
export function SkeletonText({ lines = 3, width = "100%" }: { lines?: number; width?: number | string }) {
  return (
    <span className={styles.lines} style={{ width }} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} height={12} width={i === lines - 1 && lines > 1 ? "62%" : "100%"} />
      ))}
    </span>
  );
}

/** Wraps skeletons in the one live region that announces the wait. */
export function SkeletonRegion({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div role="status" aria-label={label} aria-busy="true" className={styles.region}>
      {children}
    </div>
  );
}

/** Card-shaped placeholder: a title line and a few body lines. */
export function SkeletonCard({ lines = 3, height }: { lines?: number; height?: number | string }) {
  return (
    <div className={styles.card} style={{ minHeight: height }} aria-hidden="true">
      <Skeleton width="46%" height={18} />
      <SkeletonText lines={lines} />
    </div>
  );
}

/** A grid of card placeholders, for the course grids and cohort lists. */
export function SkeletonCards({
  count = 3,
  lines = 2,
  label = "Loading…",
}: {
  count?: number;
  lines?: number;
  label?: string;
}) {
  return (
    <SkeletonRegion label={label}>
      <div className={styles.grid}>
        {Array.from({ length: count }, (_, i) => (
          <SkeletonCard key={i} lines={lines} />
        ))}
      </div>
    </SkeletonRegion>
  );
}

/** The stat tiles row on the intern home and the management overview. */
export function SkeletonStats({ count = 3, label = "Loading figures…" }: { count?: number; label?: string }) {
  return (
    <SkeletonRegion label={label}>
      <div className={styles.stats}>
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className={styles.tile} aria-hidden="true">
            <Skeleton width={44} height={44} radius="var(--radius-sm)" />
            <span className={styles.tileText}>
              <Skeleton width="48%" height={22} />
              <Skeleton width="72%" height={11} />
            </span>
          </div>
        ))}
      </div>
    </SkeletonRegion>
  );
}

/** Table placeholder with a header band, for the admin tables. */
export function SkeletonTable({
  rows = 5,
  columns = 4,
  label = "Loading table…",
}: {
  rows?: number;
  columns?: number;
  label?: string;
}) {
  return (
    <SkeletonRegion label={label}>
      <div className={styles.table} aria-hidden="true">
        <div className={`${styles.row} ${styles.head}`}>
          {Array.from({ length: columns }, (_, c) => (
            <Skeleton key={c} height={10} width={c === 0 ? "60%" : "40%"} />
          ))}
        </div>
        {Array.from({ length: rows }, (_, r) => (
          <div key={r} className={styles.row}>
            {Array.from({ length: columns }, (_, c) => (
              <Skeleton key={c} height={12} width={c === 0 ? "78%" : "52%"} />
            ))}
          </div>
        ))}
      </div>
    </SkeletonRegion>
  );
}

/** Rows inside a card: attempt history, enrollment lists, milestone lists. */
export function SkeletonRows({
  rows = 3,
  height = 56,
  label = "Loading…",
}: {
  rows?: number;
  height?: number;
  label?: string;
}) {
  return (
    <SkeletonRegion label={label}>
      <span className={styles.lines} aria-hidden="true">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} height={height} radius="var(--radius-sm)" />
        ))}
      </span>
    </SkeletonRegion>
  );
}

/** The hero card and side column on the intern home. */
export function SkeletonHero({ label = "Loading your courses…" }: { label?: string }) {
  return (
    <SkeletonRegion label={label}>
      <div className={styles.heroLayout}>
        <div className={styles.hero} aria-hidden="true">
          <Skeleton width={160} height={28} radius="var(--radius-full)" />
          <Skeleton width="72%" height={34} />
          <Skeleton width="40%" height={14} />
          <span className={styles.heroFoot}>
            <Skeleton width="55%" height={10} />
            <Skeleton width={150} height={44} radius="var(--radius-sm)" />
          </span>
        </div>
        <div className={styles.heroSide}>
          <SkeletonCard lines={2} />
          <SkeletonCard lines={3} />
        </div>
      </div>
    </SkeletonRegion>
  );
}
