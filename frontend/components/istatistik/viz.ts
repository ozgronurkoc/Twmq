import type { Sembol } from "@/lib/types";

/*
  Grafiklerin renk sozlesmesi.

  Renk KIMLIGI takip eder, siralamayi degil: 1 hep --sym-1, 0 hep --sym-0,
  2 hep --sym-2. Filtre hafta sayisini degistirince hicbir seri renk
  degistirmez. Token'lar globals.css'te HSL bilesenleri olarak durur, bu
  yuzden koyu tema otomatik gelir — burada sabit hex YOKTUR.
*/

export const SYM_FILL: Record<Sembol, string> = {
  "1": "fill-sym-1",
  "0": "fill-sym-0",
  "2": "fill-sym-2",
};

export const SYM_STROKE: Record<Sembol, string> = {
  "1": "stroke-sym-1",
  "0": "stroke-sym-0",
  "2": "stroke-sym-2",
};

export const SYM_BG: Record<Sembol, string> = {
  "1": "bg-sym-1",
  "0": "bg-sym-0",
  "2": "bg-sym-2",
};

export const SYM_TEXT: Record<Sembol, string> = {
  "1": "text-sym-1",
  "0": "text-sym-0",
  "2": "text-sym-2",
};

/**
 * Buyukluk (magnitude) icin tek hue: birincil renk, acikatan koyuya.
 * Opaklik adimi kullaniyoruz ki ayni ramp iki temada da yuzeyle dogru
 * iliskiyi kursun (acik temada beyaza, koyu temada zemine dogru soner).
 */
export function seqFill(t: number): string {
  const k = Number.isFinite(t) ? Math.min(1, Math.max(0, t)) : 0;
  // 0.06 taban: sifir bile yuzeyden ayirt edilsin, izgara gibi kaybolmasin.
  return `hsl(var(--primary) / ${(0.06 + 0.82 * k).toFixed(3)})`;
}

/** Dolgunun icindeki yazi: koyu adimlarda beyaz, acikta normal murekkep. */
export function seqInk(t: number): string {
  return t >= 0.5 ? "hsl(var(--primary-foreground))" : "hsl(var(--foreground))";
}

/**
 * Isaretli sayi: +1.3 / −0.7 / ±0.0
 * Ondalik ayirici projenin geri kalaniyla ayni (lib/utils `ondalik`).
 */
export function isaretli(n: number, basamak = 1): string {
  if (!Number.isFinite(n)) return "—";
  return `${n > 0 ? "+" : n < 0 ? "−" : "±"}${Math.abs(n).toFixed(basamak)}`;
}

/** Tepesi 4px yuvarlak, tabani kare sutun yolu. */
export function barPath(x: number, y: number, w: number, h: number, r = 4): string {
  const rr = Math.max(0, Math.min(r, h, w / 2));
  if (h <= 0) return "";
  return (
    `M${x},${y + h} L${x},${y + rr} Q${x},${y} ${x + rr},${y} ` +
    `L${x + w - rr},${y} Q${x + w},${y} ${x + w},${y + rr} L${x + w},${y + h} Z`
  );
}
