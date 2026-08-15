"use client";

import * as React from "react";
import Link from "next/link";

import { SEMBOLLER, type Sembol, type WeekRow } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ResultStrip } from "@/components/ui/symbol";

type SiraAnahtari = "week" | Sembol | "streak";

const BASLIKLAR: Array<{ key: SiraAnahtari; etiket: string; baslik: string }> = [
  { key: "week", etiket: "Hf", baslik: "Hafta" },
  { key: "1", etiket: "1", baslik: "Ev sahibi" },
  { key: "0", etiket: "0", baslik: "Beraberlik" },
  { key: "2", etiket: "2", baslik: "Deplasman" },
  { key: "streak", etiket: "Seri", baslik: "Hafta içindeki en uzun aynı-sembol serisi" },
];

/**
 * Gorsellerin tablo karsiligi. Her grafikte okunabilen her deger burada da
 * durur — hicbir sayi yalnizca renge ya da ipucuna birakilmaz.
 */
export function WeeksTable({
  weeks,
  avg,
}: {
  weeks: WeekRow[];
  avg: Partial<Record<Sembol, number>>;
}) {
  const [arama, setArama] = React.useState("");
  const [sira, setSira] = React.useState<SiraAnahtari>("week");
  const [azalan, setAzalan] = React.useState(false);

  const satirlar = React.useMemo(() => {
    const q = arama.trim().toLowerCase();
    const suzulmus = q
      ? weeks.filter(
          (w) =>
            String(w.week).includes(q) ||
            w.close_date.toLowerCase().includes(q) ||
            w.results.includes(q),
        )
      : weeks;
    const deger = (w: WeekRow) =>
      sira === "week" ? w.week : sira === "streak" ? w.max_streak.length : w.counts[sira];
    return [...suzulmus].sort(
      (a, b) => (azalan ? deger(b) - deger(a) : deger(a) - deger(b)) || a.week - b.week,
    );
  }, [weeks, arama, sira, azalan]);

  function degistir(key: SiraAnahtari) {
    if (key === sira) {
      setAzalan((d) => !d);
    } else {
      setSira(key);
      setAzalan(key !== "week");
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <input
          value={arama}
          onChange={(e) => setArama(e.target.value)}
          placeholder="Hafta, tarih veya dizi ara…"
          aria-label="Haftalarda ara"
          className={cn(
            "h-9 w-56 rounded-xl border border-line bg-background px-3 text-[13px]",
            "placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
          )}
        />
        <span className="tnum text-[11.5px] text-muted-foreground">{satirlar.length} hafta</span>
      </div>

      <div className="scroll-slim overflow-x-auto">
        <table className="w-full min-w-[720px] text-[12.5px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
              {BASLIKLAR.map((h) => (
                <th key={h.key} scope="col" className="pb-2 pr-3 font-medium">
                  <button
                    type="button"
                    onClick={() => degistir(h.key)}
                    title={`${h.baslik} — sırala`}
                    aria-sort={sira === h.key ? (azalan ? "descending" : "ascending") : "none"}
                    className="inline-flex items-center gap-1 transition-colors hover:text-foreground"
                  >
                    {h.etiket}
                    <span aria-hidden className={sira === h.key ? "opacity-100" : "opacity-0"}>
                      {azalan ? "▾" : "▴"}
                    </span>
                  </button>
                </th>
              ))}
              <th scope="col" className="pb-2 pr-3 font-medium">
                Tarih
              </th>
              <th scope="col" className="pb-2 font-medium">
                Sonuç dizisi
              </th>
            </tr>
          </thead>
          <tbody className="tnum">
            {satirlar.map((w) => (
              <tr key={w.week} className="border-t border-line transition-colors hover:bg-muted">
                <td className="py-2 pr-3">
                  <Link
                    href={`/istatistik/${w.week}`}
                    className="font-semibold text-primary hover:underline"
                  >
                    {w.week}
                  </Link>
                </td>
                {SEMBOLLER.map((s) => (
                  <td key={s} className="py-2 pr-3">
                    <span
                      className={cn(
                        w.counts[s] >= Math.ceil((avg[s] ?? 0) + 2) && "font-semibold",
                      )}
                    >
                      {w.counts[s]}
                    </span>
                  </td>
                ))}
                <td className="py-2 pr-3 text-muted-foreground">
                  {w.max_streak.length}× {w.max_streak.symbol}
                </td>
                <td className="whitespace-nowrap py-2 pr-3 text-muted-foreground">{w.close_date}</td>
                <td className="py-2">
                  <Link href={`/istatistik/${w.week}`} aria-label={`${w.week}. hafta detayı`}>
                    <ResultStrip results={w.results} />
                  </Link>
                </td>
              </tr>
            ))}
            {satirlar.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-6 text-center text-muted-foreground">
                  Eşleşen hafta yok.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] text-muted-foreground">
        Kalın yazılan sayılar, sezon ortalamasının 2 üstünde kapatan haftaları işaretler.
      </p>
    </div>
  );
}
