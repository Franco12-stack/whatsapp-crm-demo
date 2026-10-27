const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API = `${BASE_URL}/api/v1`;
const TOKEN_KEY = "demo_token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API}${path}`, { ...options, headers });

  if (response.status === 401) {
    setToken(null);
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }

  if (!response.ok) {
    let message = `Error ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* no JSON body */
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),

  async login(email: string, password: string) {
    const form = new URLSearchParams({ username: email, password });
    const response = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    if (!response.ok) {
      let message = response.status === 401 ? "Incorrect email or password" : `Error ${response.status}`;
      try {
        const body = await response.json();
        if (typeof body.detail === "string") message = body.detail;
      } catch {
        /* no JSON body */
      }
      throw new ApiError(response.status, message);
    }
    return response.json();
  },
};
