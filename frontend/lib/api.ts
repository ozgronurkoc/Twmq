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

export type Sym = "1" | "0" | "2";
export type SymMap<T> = Record<Sym, T>;

export type WeekRow = {
  week: number;
  close_date: string;
  season: string;
  results: string;
  n1: number;
  n0: number;
  n2: number;
  counts: SymMap<number>;
  top: Sym;
  max_streak: { symbol: string; start: number; length: number };
  complete: boolean;
  consistent: boolean;
  reported_counts: SymMap<number> | null;
};

export type Band = {
  avg: number; min: number; max: number; median: number; std: number;
  above_n: number; below_n: number; above_mean: number; below_mean: number;
  above_gap: number; below_gap: number;
};

export type PositionStat = {
  pos: number;
  counts: SymMap<number>;
  pct: SymMap<number>;
  n: number;
  top: Sym | "";
};

export type Analytics = {
  positions: PositionStat[];
  transitions: {
    counts: SymMap<SymMap<number>>;
    pct: SymMap<SymMap<number>>;
    row_totals: SymMap<number>;
    n: number;
    repeat_pct: number;
  };
  distribution: SymMap<Array<{ count: number; weeks: number; pct: number }>>;
  streaks: {
    by_symbol: SymMap<{ length: number; week: number | null; start: number }>;
    top: Array<{ week: number; symbol: Sym; start: number; length: number }>;
    avg_week_max: number;
  };
  extremes: SymMap<{
    max: { week: number; value: number; results: string } | null;
    min: { week: number; value: number; results: string } | null;
  }>;
  recent: { window: number; weeks: number[]; avg: SymMap<number>; delta: SymMap<number> };
};

export type DataQuality = {
  source: string;
  weeks_total: number;
  count_conflicts: Array<{
    week: number; close_date: string;
    reported: SymMap<number> | null; derived: SymMap<number>;
  }>;
  incomplete_weeks: number[];
  duplicate_results: Array<{ results: string; weeks: number[] }>;
  ok: boolean;
};

export type StatsResponse = {
  meta: {
    season?: string; weeks: number; matches: number;
    week_from: number | null; week_to: number | null; sliced: boolean;
    date_from?: string; date_to?: string; source?: string; rule?: string;
  };
  totals: SymMap<number> & { pct_1: number; pct_0: number; pct_2: number };
  weekly_avg: SymMap<number>;
  bands: SymMap<Band>;
  data_quality: DataQuality;
  analytics: Analytics;
  weeks: WeekRow[];
  last: number | null;
  error: string | null;
};

export type WeekDetail = WeekRow & {
  prev_week: number | null;
  next_week: number | null;
  cells: Array<{ pos: number; symbol: Sym }>;
  runs: Array<{ symbol: Sym; start: number; length: number }>;
  season_avg: SymMap<number>;
  delta_vs_avg: SymMap<number>;
  rank: SymMap<{ rank: number; of: number }>;
  position_stats: PositionStat[];
};

export function getStats(last?: number | null) {
  const q = last && last > 0 ? `?last=${last}` : "";
  return api<StatsResponse>(`/api/stats${q}`);
}

export function getStatsWeek(week: number) {
  return api<WeekDetail>(`/api/stats/${week}`);
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
