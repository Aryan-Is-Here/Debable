/**
 * Thin fetch wrapper around the Debable API.
 *
 * Its one job beyond `fetch` is turning the backend's error envelope
 * (`{"error": {"code", "message", "details?"}}`) into a typed exception, so callers get a
 * usable message instead of "Failed to fetch".
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }

  /** True when the caller needs to sign in (or sign in again). */
  get isUnauthenticated(): boolean {
    return this.status === 401;
  }
}

/** Query parameter values; undefined, null and empty entries are dropped when building the URL. */
export type QueryParams = Readonly<Record<string, string | number | undefined | null>>;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  params?: QueryParams;
  body?: unknown;
  /** Clerk session token, for endpoints that require a signed-in user. */
  token?: string | null;
  signal?: AbortSignal;
  /** Next.js fetch cache hints, used by server components. */
  next?: RequestInit["next"];
  cache?: RequestInit["cache"];
}

function buildUrl(path: string, params?: RequestOptions["params"]): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    url.searchParams.set(key, String(value));
  }
  return url.toString();
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody = {
    code: "unknown_error",
    message: `Request failed with status ${response.status}.`,
  };
  try {
    const parsed = await response.json();
    if (parsed?.error?.message) body = parsed.error as ApiErrorBody;
  } catch {
    // Non-JSON error body (a proxy timeout, say) — keep the generic message.
  }
  return new ApiError(response.status, body);
}

export async function apiRequest<T>(
  path: string,
  { method = "GET", params, body, token, signal, next, cache }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(buildUrl(path, params), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
    next,
    cache,
  });

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;

  return (await response.json()) as T;
}
