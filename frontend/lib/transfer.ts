import type { ProbRow } from "./types";

/**
 * Hafta detayindan formul sayfasina veri devri.
 *
 * Neden `sessionStorage` ve neden URL degil: 15 macin olasiligi + takim
 * adlari URL'e sigmayacak kadar uzun ve paylasilabilir olmasi da ISTENMEZ —
 * bu bir baglanti degil, bir tasima. Sekme kapaninca kendiliginden silinir.
 *
 * Neden paket okundugunda SILINMIYOR: App Router istemci tarafi gecisinde
 * hedef sayfa iki kez baglaniyor (olculdu: getItem sirasiyla "dolu", "null"
 * donuyor). "Oku ve sil" yaklasiminda ilk baglanma paketi tuketiyor, ayakta
 * kalan ikinci baglanma bos buluyordu ve devir sessizce kayboluyordu.
 *
 * Isareti URL'den dusurmek de ise yaramadi: hem `router.replace` hem —
 * Next router'i History API'yi yamaladigi icin — `history.replaceState`
 * yeniden baglanmayi TETIKLIYOR ve az once yazilan state gidiyordu.
 *
 * Cozum: isaret URL'de durur (`?hafta=51`) ve paket depoda kalir. Kac kez
 * yeniden baglanirsa baglansin ayni paket okunur, AYNI degerler yazilir
 * (idempotent). Isaretsiz bir adreste — kenar cubugundan formule
 * donuldugunde — paket hic okunmaz. Kullanici notu kapatinca paket silinir.
 */
const ANAHTAR = "twmq.hafta-devri";

/** Devrin yapildigini soyleyen URL parametresi. */
export const DEVIR_PARAM = "hafta";

export interface HaftaDevri {
  week: number;
  /** 15 maçın marj arındırılmış 1/0/2 olasılığı. */
  probs: ProbRow[];
  /** "Galatasaray – Fenerbahçe" biçiminde 15 etiket; boş olabilir. */
  labels: string[];
  /** Oranı bulunamadığı için 1/3'e düşen maçların 1 tabanlı numaraları. */
  missing: number[];
  /** Hangi kaynaktan geldiği — arayüz bunu olduğu gibi yazar. */
  note: string;
}

export function haftaDevret(paket: HaftaDevri): boolean {
  if (typeof window === "undefined") return false;
  try {
    window.sessionStorage.setItem(ANAHTAR, JSON.stringify(paket));
    return true;
  } catch {
    // Ozel sekme / kota dolu: devir sessizce basarisiz olur, cagiran
    // tarafta kullaniciya soylenir.
    return false;
  }
}

/** Paketi okur; SILMEZ — bkz. dosya başındaki idempotentlik notu. */
export function haftaDevriOku(): HaftaDevri | null {
  if (typeof window === "undefined") return null;
  try {
    const ham = window.sessionStorage.getItem(ANAHTAR);
    if (!ham) return null;
    const p = JSON.parse(ham) as HaftaDevri;
    if (!Array.isArray(p?.probs) || !p.probs.length) return null;
    return p;
  } catch {
    return null;
  }
}

/** URL'de devir isareti var mi — paket yalnizca varken uygulanir. */
export function devirIsaretliMi(): boolean {
  if (typeof window === "undefined") return false;
  return new URL(window.location.href).searchParams.has(DEVIR_PARAM);
}

/** Paketi siler. Kullanici notu kapattiginda cagrilir; sonraki yeniden
 *  baglanmalarda not geri gelmesin diye. */
export function haftaDevriTemizle(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(ANAHTAR);
  } catch {
    /* ozel sekme: zaten yazilamamisti */
  }
}
