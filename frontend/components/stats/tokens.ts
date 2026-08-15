import type { Sym } from "@/lib/api";

/** Sembol sırası her yerde sabittir — renk kimliği takip eder, sıralamayı değil. */
export const SYMS: Sym[] = ["1", "0", "2"];

export const SYM_COLOR: Record<Sym, string> = {
  "1": "var(--viz-1)",
  "0": "var(--viz-0)",
  "2": "var(--viz-2)",
};

export const SYM_LABEL: Record<Sym, string> = {
  "1": "Ev sahibi (1)",
  "0": "Beraberlik (0)",
  "2": "Deplasman (2)",
};

export const SYM_SHORT: Record<Sym, string> = { "1": "1", "0": "0", "2": "2" };

/** Tek hue, açıktan koyuya — büyüklük (magnitude) için sequential ramp. */
export const SEQ = [
  "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
  "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95",
];

/** t ∈ [0,1] → ramp adımı. */
export function seqColor(t: number): string {
  if (!Number.isFinite(t)) return SEQ[0];
  const i = Math.round(Math.min(1, Math.max(0, t)) * (SEQ.length - 1));
  return SEQ[i];
}

/** Dolgunun içindeki yazı: koyu adımlarda beyaz, açıkta mürekkep. */
export function seqInk(t: number): string {
  return t >= 0.55 ? "#ffffff" : "var(--viz-ink)";
}

/** Türkçe ondalık ayırıcı: 6,7 — 6.7 değil. */
function tr(n: number, digits: number): string {
  return n.toLocaleString("tr-TR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export const fmt0 = (n: number) => tr(n, 0);
export const fmt1 = (n: number) => tr(n, 1);
export const fmt2 = (n: number) => tr(n, 2);
export const signed = (n: number, digits = 1) =>
  `${n > 0 ? "+" : n < 0 ? "−" : "±"}${tr(Math.abs(n), digits)}`;
