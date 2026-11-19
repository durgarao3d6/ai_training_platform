import { ROLE_NAMES } from "@/lib/microcopy";
import type { RoleProfileKey } from "@/lib/types";

import styles from "./admin.module.css";

/** Track name on its pastel colour. Text carries the meaning; colour is decoration. */
export function TrackChip({ track }: { track: RoleProfileKey }) {
  return (
    <span className={styles.trackChip} data-track={track}>
      {ROLE_NAMES[track]}
    </span>
  );
}

const dateOnly = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

/** Formats a "YYYY-MM-DD" date without a timezone shift. */
export function formatDay(value: string | null): string {
  if (!value) return "No start date";
  const [y, m, d] = value.split("-").map(Number);
  return dateOnly.format(new Date(y, m - 1, d));
}

export function formatStamp(value: string): string {
  return dateOnly.format(new Date(value));
}
