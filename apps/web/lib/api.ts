// Minimal API client. Replaced by the generated OpenAPI client in task 1.4.
// The access token lives in memory only; the refresh token is an httpOnly cookie.

const BASE = "/api/v1";
const CSRF_COOKIE = "aitms_csrf";

export type Role = "intern" | "trainer" | "hr" | "admin";

export interface Me {
  id: string;
  email: string;
  full_name: string;
  roles: Role[];
}

interface TokenResponse {
  access_token: string;
  expires_in: number;
  roles: Role[];
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly detail: string | null = null,
    /** problem+json "errors" member, when the API sends one */
    public readonly errors: unknown[] = [],
  ) {
    super(message);
  }

  /** Every message the API sent, for showing in a form. */
  get messages(): string[] {
    const fromErrors = this.errors
      .map((e) => (typeof e === "object" && e && "message" in e ? String((e as { message: unknown }).message) : null))
      .filter((m): m is string => Boolean(m));
    return fromErrors.length ? fromErrors : [this.detail ?? this.message];
  }
}

let accessToken: string | null = null;

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

async function toError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { title?: string; detail?: string; errors?: unknown[] };
    return new ApiError(
      response.status,
      body.title ?? body.detail ?? response.statusText,
      body.detail ?? null,
      Array.isArray(body.errors) ? body.errors : [],
    );
  } catch {
    return new ApiError(response.status, response.statusText);
  }
}

async function cookieCall(path: string): Promise<Response> {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRF-Token": readCookie(CSRF_COOKIE) ?? "" },
  });
}

/** Try to get a new access token from the refresh cookie. Returns false if not signed in. */
export async function refreshSession(): Promise<boolean> {
  if (!readCookie(CSRF_COOKIE)) return false;
  const response = await cookieCall("/auth/refresh");
  if (!response.ok) {
    accessToken = null;
    return false;
  }
  accessToken = ((await response.json()) as TokenResponse).access_token;
  return true;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
  as: "json" | "blob" = "json",
): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const response = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "same-origin" });
  if (response.status === 401 && retry && (await refreshSession())) {
    return apiFetch<T>(path, init, false, as);
  }
  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (as === "blob" ? await response.blob() : await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};

export async function login(email: string, password: string): Promise<void> {
  const response = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw await toError(response);
  accessToken = ((await response.json()) as TokenResponse).access_token;
}

export async function logout(): Promise<void> {
  try {
    await cookieCall("/auth/logout");
  } finally {
    accessToken = null;
  }
}

export const getMe = () => apiFetch<Me>("/me");
