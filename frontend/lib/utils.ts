import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import { SEMBOLLER, type ProbRow, type Sembol } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Kupon duzeninde (1, 0, 2) sirala. Alfabetik siralama okuma hatasi yaptirir. */
export function siralaSemboller(syms: Iterable<string>): Sembol[] {
  const set = new Set(Array.from(syms));
  return SEMBOLLER.filter((s) => set.has(s));
}

export function yuzde(n: number, basamak = 2): string {
  if (!Number.isFinite(n)) return "—";
  return `%${n.toFixed(basamak)}`;
}

export function sayi(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "—";
  return n.toLocaleString("tr-TR");
}

export function ondalik(n: number | null | undefined, basamak = 4): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "—";
  return n.toFixed(basamak);
}

export function sure(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} sn`;
}

/** Bir maca isaretlenen sembol sayisindan kolon carpani. */
export function satirBedeli(row: string[]): number {
  return row.reduce((acc, cell) => acc * Math.max(1, cell.length), 1);
}

export function uniformProb(sel: Sembol[]): ProbRow {
  const pay = sel.length ? 1 / sel.length : 1 / 3;
  return {
    "1": sel.includes("1") ? pay : 0,
    "0": sel.includes("0") ? pay : 0,
    "2": sel.includes("2") ? pay : 0,
  };
}

/** Bir olasilik satirini 1'e normalize eder; toplam 0 ise uniform doner. */
export function normalize(row: ProbRow): ProbRow {
  const toplam = SEMBOLLER.reduce((a, s) => a + Math.max(0, row[s] || 0), 0);
  if (toplam <= 0) return { "1": 1 / 3, "0": 1 / 3, "2": 1 / 3 };
  return {
    "1": Math.max(0, row["1"] || 0) / toplam,
    "0": Math.max(0, row["0"] || 0) / toplam,
    "2": Math.max(0, row["2"] || 0) / toplam,
  };
}

export function panoyaKopyala(text: string): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.clipboard) {
    return navigator.clipboard.writeText(text);
  }
  return Promise.reject(new Error("Pano kullanılamıyor"));
}
