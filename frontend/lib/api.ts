export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function messageFrom(data: unknown) {
  if (!data || typeof data !== "object") return "Request failed";
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => (item as { msg?: string }).msg || "Invalid value").join(" ");
  return "Request failed";
}

async function refresh(): Promise<boolean> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return false;
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;
  const data = await response.json();
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return true;
}

export async function request(path: string, options: RequestInit = {}, retry = true): Promise<any> {
  const headers = new Headers(options.headers);
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (response.status === 401 && retry && !path.startsWith("/auth/login")) {
    const ok = await refresh();
    if (ok) return request(path, options, false);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    if (!window.location.pathname.startsWith("/login")) window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }
  if (response.status === 204) return null;
  const isPdf = (response.headers.get("content-type") || "").includes("pdf");
  if (isPdf) {
    if (!response.ok) throw new ApiError(response.status, "The report could not be generated");
    return response.blob();
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) throw new ApiError(response.status, messageFrom(data));
  return data;
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, body?: unknown) => request(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  put: (path: string, body?: unknown) => request(path, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: (path: string) => request(path, { method: "DELETE" }),
  upload: (path: string, form: FormData) => request(path, { method: "POST", body: form }),
};

export async function downloadPdf(assessmentId: string, filename: string) {
  const blob = await request(`/reports/assessment/${assessmentId}/pdf`);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
