"use client";

import { useCallback, useState } from "react";

import { ApiError } from "@/lib/api";

/** Runs a mutation and keeps its busy state and error messages for a form. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setErrors([]);
    try {
      return await fn();
    } catch (err) {
      setErrors(err instanceof ApiError ? err.messages : ["Something went wrong. Nothing was saved; try again."]);
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);

  const reset = useCallback(() => setErrors([]), []);
  return { busy, errors, run, reset };
}
