import type {
  BacktestResponse,
  HealthChecksResponse,
  HealthHistoryResponse,
  HealthReport,
  KuponDenetimSonuc,
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
 *
 * `only` verilirse yalnizca o kontrol/kategori calisir (virgulle coklu).
 * Bilinmeyen bir ad 400 doner ve bu gercek bir hatadir — firlatilir.
 *
 * `fresh` sunucudaki kisa TTL onbellegini atlar: kullanici "yeniden
 * calistir" dedigi anda ONBELLEK degil OLCUM bekler.
 */
export async function getHealth(
  only?: string | null,
  signal?: AbortSignal,
  fresh = false,
): Promise<HealthReport> {
  const p = new URLSearchParams();
  if (only) p.set("only", only);
  if (fresh) p.set("fresh", "1");
  const q = p.toString() ? `?${p.toString()}` : "";
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/health${q}`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError("API'ye ulaşılamadı. Backend çalışıyor mu?", 0);
  }
  const govde = await res.json().catch(() => null);
  if (res.status !== 200 && res.status !== 503) {
    const mesaj =
      (govde && typeof govde === "object" && "error" in govde
        ? String((govde as { error: unknown }).error ?? "")
        : "") || `HTTP ${res.status}`;
    throw new ApiError(mesaj, res.status);
  }
  if (!govde) throw new ApiError("Sağlık raporu okunamadı", res.status);
  return govde as HealthReport;
}

/** Kontrol envanteri — kontrolleri CALISTIRMADAN listeler. */
export function getHealthChecks(signal?: AbortSignal) {
  return istek<HealthChecksResponse>("/api/health/checks", { signal });
}

/**
 * Sunucudaki son kosular. Sayfadaki gecmis seridi OTURUM icidir ve sekme
 * kapaninca gider; bu uc "ne zamandan beri kirmizi?" sorusunu cevaplar.
 */
export function getHealthHistory(limit = 50, signal?: AbortSignal) {
  return istek<HealthHistoryResponse>(`/api/health/history?limit=${limit}`, {
    signal,
  });
}

/**
 * KULLANICININ kendi kuponunu ayni degismezlerden gecirir.
 *
 * Kayitli rapor sabit ornek kuponlarla kosar: HEALTHY, kullanicinin az once
 * urettigi kuponun dogrulandigi anlamina GELMEZ. Bu cagri o bosluga bakar
 * ve sonucu kayitli raporla ayni tabloda gosterilmemelidir.
 */
export function denetleKupon(
  body: { picks: string; mode?: string; variant?: number; budget?: number },
  signal?: AbortSignal,
) {
  return istek<KuponDenetimSonuc>("/api/health/kupon", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
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
 * Geri test. `sweep` kapaliyken tek strateji hesaplanir (~1 sn); acikken
 * 28 esikli tarama + hold-out gelir ve sunucu bunu ilk cagrida uretip
 * onbellege alir, sonraki cagrilar milisaniyedir.
 */
export function getBacktest(
  opt: { last?: number | null; banko?: number; uclu?: number; sweep?: boolean } = {},
  signal?: AbortSignal,
) {
  const q = new URLSearchParams();
  if (opt.last && opt.last > 0) q.set("last", String(opt.last));
  if (opt.banko !== undefined) q.set("banko", String(opt.banko));
  if (opt.uclu !== undefined) q.set("uclu", String(opt.uclu));
  if (opt.sweep === false) q.set("sweep", "0");
  const qs = q.toString();
  return istek<BacktestResponse>(`/api/backtest${qs ? `?${qs}` : ""}`, { signal });
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
