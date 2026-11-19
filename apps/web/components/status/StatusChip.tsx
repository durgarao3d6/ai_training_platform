import type { Tone } from "@/lib/microcopy";

import styles from "./StatusChip.module.css";

// Each tone has its own icon SHAPE so meaning never depends on colour alone (FR-EVU-08).
function Icon({ tone }: { tone: Tone }) {
  const common = { width: 12, height: 12, viewBox: "0 0 12 12", "aria-hidden": true, focusable: false } as const;
  switch (tone) {
    case "success": // check mark
      return (
        <svg {...common}>
          <path d="M2 6.5 5 9.5 10 3" fill="none" stroke="currentColor" strokeWidth="1.8" />
        </svg>
      );
    case "attention": // circular arrow: go round again
      return (
        <svg {...common}>
          <path d="M9.5 6A3.5 3.5 0 1 1 6 2.5h2" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M7 0.8 9 2.5 7 4.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      );
    case "review": // eye: someone will look
      return (
        <svg {...common}>
          <path d="M1 6s2-3.5 5-3.5S11 6 11 6 9 9.5 6 9.5 1 6 1 6Z" fill="none" stroke="currentColor" strokeWidth="1.3" />
          <circle cx="6" cy="6" r="1.5" fill="currentColor" />
        </svg>
      );
    case "locked": // padlock
      return (
        <svg {...common}>
          <rect x="2.5" y="5.5" width="7" height="5.5" rx="1" fill="currentColor" />
          <path d="M4 5.5V4a2 2 0 0 1 4 0v1.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
        </svg>
      );
    default: // open: hollow circle
      return (
        <svg {...common}>
          <circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      );
  }
}

export function StatusChip({ label, tone }: { label: string; tone: Tone }) {
  return (
    <span className={`${styles.chip} ${styles[tone]}`}>
      <Icon tone={tone} />
      {label}
    </span>
  );
}
