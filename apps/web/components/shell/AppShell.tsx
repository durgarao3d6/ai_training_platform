"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/primitives";
import { useAuth } from "@/lib/auth";
import { NAV, ROLE_LABEL, SHELL_TITLES, type Shell } from "@/lib/roles";

import styles from "./AppShell.module.css";

function isCurrent(pathname: string, href: string, shellRoot: string): boolean {
  return href === shellRoot ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ shell, children }: { shell: Shell; children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const items = NAV[shell].filter((item) => !item.roles || item.roles.some((r) => user?.roles.includes(r)));
  const root = NAV[shell][0]?.href ?? "/";

  async function handleSignOut() {
    await signOut();
    router.replace("/login");
  }

  return (
    <div className={styles.shell}>
      <a href="#main" className={styles.skipLink}>
        Skip to main content
      </a>

      <aside className={styles.rail}>
        <Link href={root} className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true" />
          <span>
            <span className={styles.brandName}>AITMS</span>
            <span className={styles.brandArea}>{SHELL_TITLES[shell]}</span>
          </span>
        </Link>

        <nav aria-label={`${SHELL_TITLES[shell]} navigation`} className={styles.nav}>
          <ul>
            {items.map((item) => {
              const current = isCurrent(pathname, item.href, root);
              return (
                <li key={item.href}>
                  <Link href={item.href} aria-current={current ? "page" : undefined} className={styles.navLink}>
                    <Icon name={item.icon} />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {user && (
          <div className={styles.account}>
            <Avatar name={user.full_name} solid />
            <div className={styles.accountText}>
              <span className={styles.accountName}>{user.full_name}</span>
              <span className={styles.accountRole}>{user.roles.map((r) => ROLE_LABEL[r]).join(", ")}</span>
            </div>
            <button type="button" className={styles.signOut} onClick={handleSignOut}>
              <Icon name="logout" label="Sign out" />
            </button>
          </div>
        )}
      </aside>

      <main id="main" tabIndex={-1} className={styles.main}>
        <div className={styles.content}>{children}</div>
      </main>
    </div>
  );
}
