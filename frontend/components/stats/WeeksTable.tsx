"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Sym, SymMap, WeekRow } from "@/lib/api";
import { ResultStrip } from "./primitives";
import { SYMS } from "./tokens";

type SortKey = "week" | Sym | "streak";

const HEADERS: Array<{ key: SortKey; label: string; title: string }> = [
  { key: "week", label: "Hf", title: "Hafta" },
  { key: "1", label: "1", title: "Ev sahibi" },
  { key: "0", label: "0", title: "Beraberlik" },
  { key: "2", label: "2", title: "Deplasman" },
  { key: "streak", label: "Seri", title: "Hafta içindeki en uzun aynı-sembol serisi" },
];

export function WeeksTable({ weeks, avg }: { weeks: WeekRow[]; avg: SymMap<number> }) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<SortKey>("week");
  const [desc, setDesc] = useState(false);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const filtered = needle
      ? weeks.filter(
          (w) =>
            String(w.week).includes(needle) ||
            w.close_date.toLowerCase().includes(needle) ||
            w.results.includes(needle),
        )
      : weeks;
    const val = (w: WeekRow) =>
      sort === "week" ? w.week : sort === "streak" ? w.max_streak.length : w.counts[sort];
    return [...filtered].sort((a, b) => (desc ? val(b) - val(a) : val(a) - val(b)) || a.week - b.week);
  }, [weeks, q, sort, desc]);

  function toggle(key: SortKey) {
    if (key === sort) setDesc((d) => !d);
    else {
      setSort(key);
      setDesc(key !== "week");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-3 mb-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Hafta, tarih veya dizi ara…"
          aria-label="Haftalarda ara"
          className="h-9 px-3 rounded-xl border border-[var(--line)] bg-white text-[13px] w-56
            focus:outline-none focus:ring-2 focus:ring-[var(--brand)]/25"
        />
        <span className="text-[12px] text-[var(--muted)] tabular-nums">{rows.length} hafta</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px] min-w-[560px]">
          <thead>
            <tr className="text-[var(--muted)] text-[11px] uppercase tracking-wide">
              {HEADERS.map((h) => (
                <th key={h.key} scope="col" className="py-2 text-left font-medium">
                  <button
                    type="button"
                    onClick={() => toggle(h.key)}
                    title={`${h.title} — sırala`}
                    aria-sort={sort === h.key ? (desc ? "descending" : "ascending") : "none"}
                    className="inline-flex items-center gap-1 hover:text-[var(--ink)] transition"
                  >
                    {h.label}
                    <span aria-hidden className={sort === h.key ? "opacity-100" : "opacity-0"}>
                      {desc ? "▾" : "▴"}
                    </span>
                  </button>
                </th>
              ))}
              <th scope="col" className="py-2 text-left font-medium">Tarih</th>
              <th scope="col" className="py-2 text-left font-medium">Sonuç dizisi</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {rows.map((w) => (
              <tr key={w.week} className="border-t border-[var(--line-soft)] hover:bg-[var(--bg)]">
                <td className="py-2">
                  <Link href={`/stats/${w.week}`} className="text-[var(--brand)] font-medium hover:underline">
                    {w.week}
                  </Link>
                </td>
                {SYMS.map((s) => (
                  <td key={s} className="py-2">
                    <span className={w.counts[s] >= Math.ceil(avg[s] + 2) ? "font-semibold" : ""}>
                      {w.counts[s]}
                    </span>
                  </td>
                ))}
                <td className="py-2 text-[var(--muted)]">
                  {w.max_streak.length}× {w.max_streak.symbol}
                </td>
                <td className="py-2 text-[var(--muted)] whitespace-nowrap">{w.close_date}</td>
                <td className="py-2">
                  <Link href={`/stats/${w.week}`} className="inline-block align-middle" aria-label={`${w.week}. hafta detayı`}>
                    <ResultStrip results={w.results} />
                  </Link>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="py-6 text-center text-[var(--muted)]">Eşleşen hafta yok.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-[var(--muted)] mt-3">
        Kalın yazılan sayılar sezon ortalamasının 2 üstündeki haftaları işaretler.
      </p>
    </div>
  );
}
