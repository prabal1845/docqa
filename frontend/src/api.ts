// Typed client for the DocQA FastAPI backend. Dev requests go through Vite's /api proxy.
const BASE = import.meta.env.VITE_API_URL ?? "/api";
const TOKEN_KEY = "docqa_token";

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface DocumentInfo {
  id: number;
  filename: string;
  status: DocumentStatus;
  error: string | null;
  page_count: number | null;
  chunk_count: number;
  created_at: string;
}

export interface Citation {
  index: number;
  document_id: number;
  filename: string;
  page: number;
  snippet: string;
  score: number;
  cited: boolean;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

let token = readToken();
let onUnauthorized: () => void = () => {};

export function setToken(value: string | null) {
  token = value;
  try {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage unavailable (private mode); the token still lives in memory
  }
}

export function hasToken() {
  return token !== null;
}

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

// FastAPI returns {detail: "..."} for HTTPException and {detail: [{msg}]} for validation errors
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => {
        const field = d.loc?.[d.loc.length - 1];
        return field && field !== "body" ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(BASE + path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the backend running?");
  }

  if (res.status === 401 && token) onUnauthorized();
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, errorMessage(body, `Request failed (${res.status})`));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function json(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", json({ email, password })),

  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
    }),

  me: () => request<User>("/auth/me"),

  listDocuments: () => request<DocumentInfo[]>("/documents"),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentInfo>("/documents", { method: "POST", body: form });
  },

  deleteDocument: (id: number) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  query: (question: string, documentIds?: number[]) =>
    request<QueryResponse>(
      "/query",
      json({ question, document_ids: documentIds?.length ? documentIds : null }),
    ),
};
