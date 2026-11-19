"use client";

import { useAuth } from "@/lib/auth";
import type { InternDashboard } from "@/lib/types";
import { useApi } from "@/lib/useApi";

/** The signed-in intern's own dashboard. */
export function useDashboard() {
  const { user } = useAuth();
  return useApi<InternDashboard>(user ? `/interns/${user.id}/dashboard` : null);
}
