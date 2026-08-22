/**
 * Guncel sezonun iskeleti ve GERCEK verisi.
 *
 * Hafta verisi artik elle tutulmuyor: `super-toto-veri.json`,
 * `backend/scripts/super_toto_frontend.py` tarafindan
 * `backend/data/super_toto` altindan uretilir. Backend kaynaktir, bu dosya
 * onu okur. Besleme eskirse CI kirilir (`--kontrol`) — sessizce eskimis bir
 * arayuz, bos bir arayuzden daha kotudur cunku yanlis oldugu belli olmaz.
 *
 * Gecmis sezon (2025/2026) buraya GIRMEZ: o veri backend'in
 * `st_history_2025_26.json` dosyasinda yasar ve /istatistik altindan
 * okunur. Ikisi bilerek ayri tutulur — biri arsiv, biri isleyen sezon.
 */
import veri from "./super-toto-veri.json";

/** Uzerinde calisilan sezon. */
export const SUPER_TOTO_SEZON = veri.season;

/**
 * Sezonun planlanan hafta sayisi. Gecen sezon 41 tam hafta uretti;
 * takvim uzarsa TEK degistirilecek yer burasidir.
 */
export const HAFTA_SAYISI = 41;

/** Bir kuponun mac sayisi — motorun sabiti (backend `meta.MATCH_COUNT`). */
export const MAC_SAYISI = 15;

/** Beslemeyi ureten marj arindirma yontemi — sayfada yazar. */
export const ARINDIRMA = veri.arindirma;

export interface SuperTotoMac {
  no: number;
  date: string | null;
  kickoff: string | null;
  league: string;
  home: string;
  away: string;
  /** Orani ilan edilmemis mac icin null — bu bir tahmin yoklugudur. */
  odds: Record<string, number> | null;
  odds_missing: boolean;
  probs: Record<string, number>;
  fav: string | null;
  margin: number;
  play: Record<string, number>;
  /** Sonuc girilmemisse null. */
  result: string | null;
}

/**
 * DONDURULMUS kupon — sonuclar gorulmeden kaydedilmis isaretler.
 *
 * Bu bir KAYITTIR, yeniden hesaplanmaz. Kural degismese bile OLCEK
 * degisebilir (marj arindirma varsayilani 2026-08'de `orantili`dan
 * `shin`e cevrildi) ve ayni esik baska isaretler uretir. Yeniden
 * hesaplanan bir kuponu gostermek, "sonuclar gorulmeden dondu" diyen
 * kaydin ustune sonradan yazmak olurdu.
 */
export interface SuperTotoKupon {
  picks: string[];
  label: string | null;
  columns: number | null;
  rows: number | null;
  in_set_p: number | null;
  banko_esik: number | null;
  uclu_esik: number | null;
  /** Hangi olcekte donduruldugu — bu alan olmadan isaretler yorumlanamaz. */
  arindirma: string | null;
  marj_ort_pct: number | null;
  frozen_at: string | null;
  results_known: boolean | null;
}

/** Bugunku kuralin AYNI hafta icin uretecegi kupon — kiyas icin, kayit degil. */
export interface SuperTotoBugunkuKupon {
  picks: string[];
  banko: number[];
  cift: number[];
  uclu: number[];
  columns: number | null;
  rows: number | null;
  in_set_p: number;
  banko_esik: number;
  uclu_esik: number;
  arindirma: string;
}

export interface SuperTotoHafta {
  /** 1'den baslayan hafta numarasi. */
  week: number;
  program: string | null;
  /** Kupon kapanis tarihi (YYYY-MM-DD). Veri girilene kadar null. */
  close_date: string | null;
  /** 15 karakterlik sonuc dizisi ("1"/"0"/"2"). Sonuc gelene kadar null. */
  results: string | null;
  odds_source: string | null;
  odds_kind: string | null;
  play_source: string | null;
  /** Insanin dustugu notlar. */
  warnings_manual: string[];
  /** Kalite kapisinin urettigi uyarilar. Ikisi AYRI tutulur. */
  warnings_generated: string[];
  matches: SuperTotoMac[];
  /** Dondurulmus kayit. */
  coupon: SuperTotoKupon | null;
  /** Bugunku kuralin uretecegi kupon — kiyas. */
  coupon_today: SuperTotoBugunkuKupon | null;
  /** Ikisinin ayristigi mac numaralari. Bos ise olcek degisimi isaret degistirmemis. */
  coupon_drift: number[] | null;
}

/** Verisi girilmis haftalar — beslemeden gelir. */
export const GIRILEN_HAFTALAR = veri.weeks as unknown as SuperTotoHafta[];

const GIRILEN = new Map(GIRILEN_HAFTALAR.map((h) => [h.week, h]));

/**
 * Sezonun tum haftalari. Verisi girilmis olanlar beslemeden, digerleri
 * bos iskelet olarak gelir — serit her zaman 41 sekme gosterir.
 */
export const HAFTALAR: SuperTotoHafta[] = Array.from(
  { length: HAFTA_SAYISI },
  (_, i): SuperTotoHafta =>
    GIRILEN.get(i + 1) ?? {
      week: i + 1,
      program: null,
      close_date: null,
      results: null,
      odds_source: null,
      odds_kind: null,
      play_source: null,
      warnings_manual: [],
      warnings_generated: [],
      matches: [],
      coupon: null,
      coupon_today: null,
      coupon_drift: null,
    },
);

/**
 * Bir haftanin verisi VAR mi — 15 macin kadrosu girilmis mi.
 *
 * Dikkat: bu "sonuclari geldi mi" DEGILDIR. Kupon dondurulmus ama maclar
 * daha oynanmamis bir hafta da doludur ve panelinde gosterilecek seyi
 * vardir (oranlar, olasiliklar, isaretler). Sonuc ayri sorulur.
 */
export function haftaDoluMu(h: SuperTotoHafta): boolean {
  return h.matches.length === MAC_SAYISI;
}

/** Sonuclari gelmis hafta — yarim veri ortalamalara karismasin diye ayri. */
export function haftaSonuclandiMi(h: SuperTotoHafta): boolean {
  return typeof h.results === "string" && h.results.length === MAC_SAYISI;
}

export function haftaBul(week: number): SuperTotoHafta | null {
  return HAFTALAR.find((h) => h.week === week) ?? null;
}

/** Veri girilmis hafta sayisi — basliktaki rozetin kaynagi. */
export function doluHaftaSayisi(): number {
  return HAFTALAR.filter(haftaDoluMu).length;
}

/** Sonuclanmis hafta sayisi. */
export function sonuclananHaftaSayisi(): number {
  return HAFTALAR.filter(haftaSonuclandiMi).length;
}
