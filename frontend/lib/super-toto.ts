/**
 * Guncel sezonun ISKELETI. Burada henuz VERI YOKTUR ve olmasi da
 * beklenmez: bu dosya yalnizca "hangi sezondayiz, kac hafta var, bir
 * haftanin dolu sayilmasi ne demek" sorularini tek yerden cevaplar.
 *
 * Hafta verisi (kapanis tarihi, maclar, 15 karakterlik sonuc dizisi)
 * sonradan `HAFTALAR` icine yazilacak; arayuzun geri kalani o gun
 * degismeyecek cunku sekmeler de, dolu/bos ayrimi da bu listeden turer.
 *
 * Gecmis sezon (2025/2026) buraya GIRMEZ: o veri backend'in
 * `st_history_2025_26.json` dosyasinda yasar ve /istatistik altindan
 * okunur. Ikisi bilerek ayri tutulur — biri arsiv, biri isleyen sezon.
 */

/** Uzerinde calisilan sezon. */
export const SUPER_TOTO_SEZON = "2026/2027";

/**
 * Sezonun planlanan hafta sayisi. Gecen sezon 41 tam hafta uretti;
 * takvim uzarsa TEK degistirilecek yer burasidir.
 */
export const HAFTA_SAYISI = 41;

/** Bir kuponun mac sayisi — motorun sabiti (backend `meta.MATCH_COUNT`). */
export const MAC_SAYISI = 15;

export interface SuperTotoHafta {
  /** 1'den baslayan hafta numarasi. */
  week: number;
  /** Kupon kapanis tarihi (YYYY-MM-DD). Veri girilene kadar null. */
  close_date: string | null;
  /** 15 karakterlik sonuc dizisi ("1"/"0"/"2"). Veri girilene kadar null. */
  results: string | null;
}

/**
 * Sezonun tum haftalari. Su an hepsi bos: veri girisi bu listeyi
 * doldurarak yapilacak.
 */
export const HAFTALAR: SuperTotoHafta[] = Array.from(
  { length: HAFTA_SAYISI },
  (_, i): SuperTotoHafta => ({ week: i + 1, close_date: null, results: null }),
);

/**
 * Bir hafta ancak 15 sonucun TAMAMI varsa doludur. Eksik hafta yarim
 * gosterilmez: yarim veri, yanlis veriden daha tehlikelidir cunku
 * ortalamalara sessizce karisir.
 */
export function haftaDoluMu(h: SuperTotoHafta): boolean {
  return typeof h.results === "string" && h.results.length === MAC_SAYISI;
}

export function haftaBul(week: number): SuperTotoHafta | null {
  return HAFTALAR.find((h) => h.week === week) ?? null;
}

/** Veri girilmis hafta sayisi — basliktaki rozetin kaynagi. */
export function doluHaftaSayisi(): number {
  return HAFTALAR.filter(haftaDoluMu).length;
}
