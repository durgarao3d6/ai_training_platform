"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { getMe, login as apiLogin, logout as apiLogout, refreshSession, type Me } from "./api";

interface AuthState {
  user: Me | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<Me>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (await refreshSession()) {
          const me = await getMe();
          if (!cancelled) setUser(me);
        }
      } catch {
        // Not signed in; the guard sends the person to /login.
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    await apiLogin(email, password);
    const me = await getMe();
    setUser(me);
    return me;
  }, []);

  const signOut = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, loading, signIn, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
