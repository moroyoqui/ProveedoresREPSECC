/**
 * Fetch wrapper for the REPSE API.
 *
 * - Sends cookies (the session is HttpOnly).
 * - Adds `If-Match` automatically when `etag` is provided (used by mutating
 *   endpoints in the catalog; see spec 003 plan + research §4).
 * - Normalizes the error envelope `{ error: { code, message, details } }`.
 */

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.error.code;
    this.details = body.error.details;
  }
}

export type ApiRequestInit = Omit<RequestInit, "body"> & {
  json?: unknown;
  body?: BodyInit;
  etag?: string | null;
};

const BASE_URL = "/api/v1";

export async function apiFetch<T = unknown>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  let body: BodyInit | undefined = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  if (init.etag) {
    headers.set("If-Match", `"${init.etag}"`);
  }

  const url = path.startsWith("http") ? path : `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...init,
    headers,
    body,
    credentials: "include",
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!res.ok) {
    const envelope = (data && typeof data === "object" && "error" in data
      ? (data as ApiErrorBody)
      : { error: { code: "http_error", message: res.statusText } });
    throw new ApiError(res.status, envelope);
  }

  return data as T;
}
