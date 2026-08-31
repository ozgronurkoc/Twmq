import type {
  BacktestResponse,
  BenzerResponse,
  HealthChecksResponse,
  HealthHistoryResponse,
  HealthReport,
  KuponDenetimSonuc,
  MetaResponse,
  SolveRequest,
  SolveResponse,
  PazarResponse,
  StatsResponse,
  SurprizResponse,
  TahminResponse,
  TakimlarResponse,
  WeekDetail,
} from "./types";
import { SEMBOLLER } from "./types";

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
export function getStats(
  last?: number | null,
  signal?: AbortSignal,
  sezon?: string | null,
) {
  const q = new URLSearchParams();
  if (last && last > 0) q.set("last", String(last));
  if (sezon) q.set("sezon", sezon);
  const qs = q.toString();
  return istek<StatsResponse>(`/api/stats${qs ? `?${qs}` : ""}`, { signal });
}

/**
 * `sezon` VERILMEZSE varsayilan kayit okunur (2025/26, 41 hafta). Sezon
 * verilirse hafta detayi ve oranlari AYNI sezondan gelir; oran arsivinin
 * anahtari `(hafta, no)` ve sezon bileseni yok, yani ayri gonderilmezse
 * baska bir sezonun oranlari bu haftaya yapisirdi.
 */
export function getStatsWeek(week: number, signal?: AbortSignal, sezon?: string | null) {
  const q = sezon ? `?sezon=${encodeURIComponent(sezon)}` : "";
  return istek<WeekDetail>(`/api/stats/${week}${q}`, { signal });
}

/**
 * Geri test. `sweep` kapaliyken tek strateji hesaplanir (~1 sn); acikken
 * 28 esikli tarama + hold-out gelir ve sunucu bunu ilk cagrida uretip
 * onbellege alir, sonraki cagrilar milisaniyedir.
 */
export function getBacktest(
  opt: {
    last?: number | null;
    banko?: number;
    uclu?: number;
    sweep?: boolean;
    sezon?: string | null;
  } = {},
  signal?: AbortSignal,
) {
  const q = new URLSearchParams();
  if (opt.last && opt.last > 0) q.set("last", String(opt.last));
  if (opt.banko !== undefined) q.set("banko", String(opt.banko));
  if (opt.uclu !== undefined) q.set("uclu", String(opt.uclu));
  if (opt.sweep === false) q.set("sweep", "0");
  if (opt.sezon) q.set("sezon", opt.sezon);
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

/**
 * Yaklasan maclarin tahmini.
 *
 * Sunucu ONBELLEKLEMEZ (bkz. `web_app._tahmin_cached` docstring'i): cevap
 * zamanla degisir, mac baslar ve bulten yenilenir. Bu yuzden burada da
 * agresif bir istemci onbellegi yok.
 *
 * `limit` yalnizca listeyi kirpar; olculmus isabet ve uyarilar hep tam gelir.
 */
/**
 * 1X2 disi pazarlar: alt/ust 2,5 ve Asya handikabi.
 *
 * Cevap bir TAHMIN degil, bir OLCUMdur: her pazarin kapsamasi, marji,
 * kalibrasyon bantlari ve sapan bant sayisi govdeyle birlikte gelir.
 * `handikap.brier` **null** doner ve bu bir eksiklik degil bir tanimdir —
 * sebep `brier_yok_sebep` alaninda yazili.
 */
export function getPazar(
  arindirma?: ArindirmaYontemi,
  signal?: AbortSignal,
) {
  const qs = arindirma ? `?arindirma=${arindirma}` : "";
  return istek<PazarResponse>(`/api/pazar${qs}`, { signal });
}

/**
 * Surpriz ekseni: haftanin surprizi ve onun MUSTEREK havuzdaki karsiligi.
 *
 * Cevap "hangi mac surpriz olacak" DEMEZ — o eksen depoda on bes kez
 * olculdu ve hicbiri gecmedi. Soyledigi sey surprizin havuzda ne ettigi
 * (`olcum`) ve kalabaligin piyasadan ne kadar saptigidir (`kalabalik.tam`).
 */
export function getSurpriz(sezon?: string | null, signal?: AbortSignal) {
  const qs = sezon ? `?sezon=${encodeURIComponent(sezon)}` : "";
  return istek<SurprizResponse>(`/api/surpriz${qs}`, { signal });
}

export function getTakimlar(
  lig?: string,
  sezon?: string,
  signal?: AbortSignal,
) {
  const q = new URLSearchParams();
  if (lig) q.set("lig", lig);
  if (sezon) q.set("sezon", sezon);
  const qs = q.toString();
  return istek<TakimlarResponse>(
    `/api/takimlar${qs ? `?${qs}` : ""}`,
    { signal },
  );
}

export function getTahmin(
  opt: { limit?: number } = {},
  signal?: AbortSignal,
) {
  const q = new URLSearchParams();
  if (opt.limit && opt.limit > 0) q.set("limit", String(opt.limit));
  const qs = q.toString();
  return istek<TahminResponse>(`/api/tahmin${qs ? `?${qs}` : ""}`, { signal });
}

/**
 * "Bu oranda gecmiste ne olmus?" — 31 bin maclik korpusta ayni fiyata sahip
 * maclarin nasil bittigi.
 *
 * `oranlar` 1/0/2 sirasiyla gonderilir. Cevap bir TAHMIN degildir: her yuzde
 * yaninda n ve Wilson %95 araligi gelir ve `piyasa_ga_icinde` alani asil
 * soruyu cevaplar — *piyasa sozunu tutmus mu*.
 */
export const ARINDIRMA_YONTEMLERI = ["shin", "guc", "orantili"] as const;
export type ArindirmaYontemi = (typeof ARINDIRMA_YONTEMLERI)[number];

export function getBenzer(
  oranlar: Record<string, number>,
  secenek?: {
    lig?: string;
    tolerans?: number;
    /** Marj arindirma yontemi. Sunucu varsayilani `shin`. */
    arindirma?: ArindirmaYontemi;
    /** Hedeflenen en az ornek — tolerans buna ulasana kadar genisler. */
    en_az?: number;
    sezon?: string;
    /**
     * `YYYY-MM-DD` — yalnizca bu gunun ONCESINDEKI maclar aranir. Kronolojik
     * sorgu; verilmezse butun korpus aranir.
     */
    tarih?: string;
  },
  signal?: AbortSignal,
) {
  // Sembol sirasi KUPON duzenidir (1, 0, 2), alfabetik degil.
  const eksik = SEMBOLLER.filter((s) => !Number.isFinite(oranlar[s]));
  if (eksik.length) {
    throw new ApiError(`oran eksik: ${eksik.join(", ")}`, 0);
  }
  const q = new URLSearchParams({ oran: SEMBOLLER.map((s) => oranlar[s]).join(",") });
  if (secenek?.lig) q.set("lig", secenek.lig);
  if (secenek?.sezon) q.set("sezon", secenek.sezon);
  if (secenek?.tolerans !== undefined) q.set("tolerans", String(secenek.tolerans));
  if (secenek?.arindirma) q.set("arindirma", secenek.arindirma);
  if (secenek?.en_az !== undefined) q.set("en_az", String(secenek.en_az));
  if (secenek?.tarih) q.set("tarih", secenek.tarih);
  return istek<BenzerResponse>(`/api/benzer?${q}`, { signal });
}
