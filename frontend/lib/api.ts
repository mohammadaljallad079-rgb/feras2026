/**
 * Typed API client. All requests go through the Next.js rewrite to the FastAPI
 * backend. The access token is kept in memory + sessionStorage; the backend is
 * the only place authorization is enforced.
 */

export type ApiError = { status: number; detail: unknown };

const ACCESS_KEY = "safir.access";
const REFRESH_KEY = "safir.refresh";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  window.sessionStorage.setItem(ACCESS_KEY, access);
  window.sessionStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  window.sessionStorage.removeItem(ACCESS_KEY);
  window.sessionStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  const resp = await fetch("/api/backend/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) {
    clearTokens();
    return null;
  }
  const data = await resp.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const resp = await fetch(`/api/backend${path}`, { ...init, headers });
  if (resp.status === 401 && retry) {
    const next = await refreshAccessToken();
    if (next) return request<T>(path, init, false);
  }
  if (!resp.ok) {
    let detail: unknown = null;
    try {
      detail = (await resp.json()).detail;
    } catch {
      detail = resp.statusText;
    }
    const err: ApiError = { status: resp.status, detail };
    throw err;
  }
  if (resp.status === 204) return undefined as T;
  const text = await resp.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) }),
  upload: <T,>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
  download: async (path: string, filename: string) => {
    const token = getAccessToken();
    const resp = await fetch(`/api/backend${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw { status: resp.status, detail: "download_failed" } as ApiError;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};

// --- Types shared with the backend -----------------------------------------
export type Me = {
  id: number;
  email: string;
  full_name_ar: string;
  full_name_en: string;
  locale: string;
  roles: string[];
  permissions: string[];
};

export type Company = {
  id: number;
  code: string;
  name_ar: string;
  name_en: string;
  country: string;
  sector: string;
  contact_email: string | null;
  contact_phone: string | null;
  manager_user_id: number | null;
  ownership_percent: string;
  currency: string;
  status: string;
  logo_file_id: number | null;
  activated_at: string | null;
  closed_at: string | null;
  public_visible: boolean;
  created_at: string;
};

export type DashboardCard = {
  key: string;
  label_ar: string;
  label_en: string;
  value: string | number;
  hint_ar?: string | null;
  hint_en?: string | null;
};

export type Dashboard = {
  role: string;
  title_ar: string;
  title_en: string;
  cards: DashboardCard[];
  sections: Record<string, unknown>[];
};

export type MonthlyReport = {
  id: number;
  company_id: number;
  period_id: number;
  status: string;
  currency: string;
  commentary: string | null;
  bank_statement_file_id: number | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  returned_reason: string | null;
  forwarded_at: string | null;
  locked_at: string | null;
  created_at: string;
  values: { field_id: number; field_version: number; value_text: string | null; value_number: string | null }[];
};

export type ReportingPeriod = {
  id: number;
  label_ar: string;
  label_en: string;
  year: number;
  month: number;
  opens_on: string;
  due_on: string;
  status: string;
};

export type FormField = {
  id: number;
  code: string;
  name_ar: string;
  name_en: string;
  field_type: string;
  is_required: boolean;
  parent_id: number | null;
  sector_scope: string | null;
  company_id: number | null;
  is_active: boolean;
  version: number;
  display_order: number;
};

export type Role = {
  id: number;
  slug: string;
  name_ar: string;
  name_en: string;
  is_system: boolean;
  permission_codes: string[];
};

export type UserOut = {
  id: number;
  email: string;
  full_name_ar: string;
  full_name_en: string;
  locale: string;
  is_active: boolean;
  roles: string[];
  company_ids: number[];
  last_login_at: string | null;
};

export type AiAnswer = {
  answer: string;
  confidence: string;
  sources: { kind: string; ref: string; label: string; url: string | null }[];
  provider: string;
  model: string;
  configured: boolean;
  note: string | null;
};
