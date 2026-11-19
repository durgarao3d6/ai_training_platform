import type { IconName } from "@/components/ui/Icon";

import type { Role } from "./api";

export type Shell = "intern" | "trainer" | "admin";

export interface NavItem {
  label: string;
  href: string;
  icon: IconName;
  /** Roles that see this item. Omit for every role allowed in the shell. */
  roles?: Role[];
}

export const SHELL_ROLES: Record<Shell, Role[]> = {
  intern: ["intern"],
  trainer: ["trainer"],
  admin: ["hr", "admin"],
};

export const SHELL_TITLES: Record<Shell, string> = {
  intern: "My training",
  trainer: "Trainer workspace",
  admin: "Management",
};

// Only pages that exist are listed; later phases add their own items.
export const NAV: Record<Shell, NavItem[]> = {
  intern: [
    { label: "Home", href: "/intern", icon: "home" },
    { label: "My courses", href: "/intern/courses", icon: "map" },
  ],
  trainer: [
    { label: "Review queue", href: "/trainer", icon: "inbox" },
    { label: "My courses", href: "/trainer/courses", icon: "book" },
  ],
  admin: [
    { label: "Overview", href: "/admin", icon: "grid" },
    { label: "Courses", href: "/admin/courses", icon: "book", roles: ["admin"] },
    { label: "Approvals", href: "/admin/approvals", icon: "check", roles: ["admin"] },
    { label: "Cohorts", href: "/admin/cohorts", icon: "users" },
    { label: "People", href: "/admin/people", icon: "user" },
  ],
};

/** Where a signed-in person lands. Highest-privilege shell wins. */
export function homeFor(roles: Role[]): string {
  if (roles.includes("admin") || roles.includes("hr")) return "/admin";
  if (roles.includes("trainer")) return "/trainer";
  if (roles.includes("intern")) return "/intern";
  return "/login";
}

export const ROLE_LABEL: Record<Role, string> = {
  intern: "Intern",
  trainer: "Trainer",
  hr: "HR",
  admin: "Administrator",
};
