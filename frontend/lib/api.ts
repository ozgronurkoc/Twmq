const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getStats() {
  return api<any>("/api/stats");
}

export function getHealth() {
  return api<Record<string, unknown>>("/api/health");
}

export function solve(body: {
  picks?: string;
  matches?: string[][];
  mode?: string;
  variant?: number;
  use_bayes?: boolean;
}) {
  return api<any>("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
