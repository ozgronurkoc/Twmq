const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      if (j?.error) msg = j.error;
      else if (typeof j === "string") msg = j;
    } catch {
      try {
        msg = (await res.text()) || msg;
      } catch {
        /* ignore */
      }
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export function getStats() {
  return api<any>("/api/stats");
}

export function getHealth() {
  return api<Record<string, unknown>>("/api/health");
}

export type SolveBody = {
  picks?: string;
  matches?: string[][];
  mode?: "fix16" | "auto" | "heuristic" | "butce" | "maxcov" | string;
  variant?: number;
  budget?: number;
  use_bayes?: boolean;
  prior_strength?: number;
  evidence_strength?: number;
  mc_samples?: number;
  probs?: Array<Record<string, number>>;
};

export type SolveResponse = {
  ok: boolean;
  error?: string | null;
  result?: Record<string, unknown> | null;
  run_log_text?: string;
  version?: string;
};

export function solve(body: SolveBody) {
  return api<SolveResponse>("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
