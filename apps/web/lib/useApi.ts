"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch, ApiError } from "./api";

export interface ApiState<T> {
  data: T | null;
  error: ApiError | Error | null;
  loading: boolean;
  /** Fetch again (after a change elsewhere). */
  reload: () => void;
  /** Replace the data with a fresh copy returned by a mutation, without refetching. */
  setData: (data: T) => void;
}

/** Small GET hook. TanStack Query replaces it when the generated client lands. */
export function useApi<T>(path: string | null): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch<T>(path)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, loading, reload, setData };
}
