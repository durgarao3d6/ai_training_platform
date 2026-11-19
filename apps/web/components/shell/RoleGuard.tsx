"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { EmptyState, PageLoader } from "@/components/ui/primitives";
import { useAuth } from "@/lib/auth";
import { homeFor, SHELL_ROLES, type Shell } from "@/lib/roles";

import { AppShell } from "./AppShell";

/**
 * Convenience guard only. The API enforces every permission (403); this just keeps
 * people out of screens that would show nothing but errors.
 */
export function RoleGuard({ shell, children }: { shell: Shell; children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return (
      <div className="page-status">
        <PageLoader label="Checking your sign-in…" />
      </div>
    );
  }

  if (!user.roles.some((r) => SHELL_ROLES[shell].includes(r))) {
    return (
      <main id="main" className="page-status">
        <EmptyState
          icon="alert"
          title="You do not have access to this area"
          action={
            <a className="text-link" href={homeFor(user.roles)}>
              Go to your home page
            </a>
          }
        >
          Your account does not include this part of AITMS. Ask an administrator if you think it should.
        </EmptyState>
      </main>
    );
  }

  return <AppShell shell={shell}>{children}</AppShell>;
}
