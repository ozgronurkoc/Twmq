import type {
  HealthReport,
  MetaResponse,
  SolveRequest,
  SolveResponse,
  StatsResponse,
  WeekDetail,
} from "./types";

/**
 * Bos birakilmasi KASITLIDIR: ayni origin kullanilir ve istek
 * next.config.mjs'deki rewrite ile Flask :8080'e proxy'lenir. Replit
 * onizlemesinde tarayici 127.0.0.1'e ulasamadigi icin bu sart.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function istek<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(
      "API'ye ulaşılamadı. Backend çalışıyor mu? (python backend/web_app.py)",
      0,
    );
  }

  const govde = await res.json().catch(() => null);

  if (!res.ok) {
    // Backend hatalari {ok:false, error:"..."} bicimindedir.
    const mesaj =
      (govde && typeof govde === "object" && "error" in govde
        ? String((govde as { error: unknown }).error ?? "")
        : "") || `HTTP ${res.status}`;
    throw new ApiError(mesaj, res.status);
  }
  return govde as T;
}

export function getMeta(signal?: AbortSignal) {
  return istek<MetaResponse>("/api/meta", { signal });
}

/**
 * /api/health SAGLIKSIZ durumda 503 doner. Bu bir hata degil, raporun
 * kendisidir — govde yine tam HealthReport'tur. Bu yuzden genel `istek`
 * yolundan gecmez; 503 basarisiz sayilsaydi kullanici invariantlarin
 * hangisinin kirildigini goremezdi.
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthReport> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/health`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError("API'ye ulaşılamadı. Backend çalışıyor mu?", 0);
  }
  if (res.status !== 200 && res.status !== 503) {
    throw new ApiError(`HTTP ${res.status}`, res.status);
  }
  const govde = await res.json().catch(() => null);
  if (!govde) throw new ApiError("Sağlık raporu okunamadı", res.status);
  return govde as HealthReport;
}

/**
 * `last` verilirse ozet, bantlar ve analiz bloklarinin TAMAMI son N hafta
 * uzerinden hesaplanir — filtre tek noktadan butun gorselleri kapsar.
 */
export function getStats(last?: number | null, signal?: AbortSignal) {
  const q = last && last > 0 ? `?last=${last}` : "";
  return istek<StatsResponse>(`/api/stats${q}`, { signal });
}

export function getStatsWeek(week: number, signal?: AbortSignal) {
  return istek<WeekDetail>(`/api/stats/${week}`, { signal });
}

/**
 * Cozucu. Buyuk kuponlarda saniyeler surebilir, bu yuzden `signal` ile
 * iptal edilebilir olmasi onemli — kullanici parametre degistirdiginde
 * onceki istek terk edilir.
 */
export function solve(body: SolveRequest, signal?: AbortSignal) {
  return istek<SolveResponse>("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}
