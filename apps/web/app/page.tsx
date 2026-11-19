"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { PageLoader } from "@/components/ui/primitives";
import { useAuth } from "@/lib/auth";
import { homeFor } from "@/lib/roles";

/** Sends each person to the home of their role, or to sign-in. */
export default function RootRedirect() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) router.replace(user ? homeFor(user.roles) : "/login");
  }, [loading, user, router]);

  return (
    <main id="main" className="page-status">
      <PageLoader />
    </main>
  );
}
