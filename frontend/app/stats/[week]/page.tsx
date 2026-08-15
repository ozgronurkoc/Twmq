"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getStatsWeek, type Sym, type WeekDetail } from "@/lib/api";
import { Card, Legend, ResultStrip, StatTile } from "@/components/stats/primitives";
import { SYMS, SYM_COLOR, SYM_LABEL, fmt1 } from "@/components/stats/tokens";

export default function WeekDetailPage({ params }: { params: { week: string } }) {
  const week = Number(params.week);
  const [data, setData] = useState<WeekDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setData(null);
    setErr(null);
    getStatsWeek(week)
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setErr(e instanceof Error ? e.message : String(e)); });
    return () => { alive = false; };
  }, [week]);

  if (err) {
    return (
      <div className="max-w-xl space-y-3">
        <p className="text-[13px] text-red-600 bg-red-50 rounded-xl p-4">{err}</p>
        <Link href="/stats" className="btn-ghost">Tüm haftalar</Link>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="space-y-4" aria-busy>
        <div className="h-8 w-48 rounded-xl bg-black/5" />
        <div className="h-32 rounded-2xl bg-black/5" />
      </div>
    );
  }

  const pos = data.position_stats;
  // Sezonda en nadir görülen tercihler — bu haftanın sürprizleri.
  const surprises = data.cells
    .map((c) => ({ ...c, pct: pos[c.pos - 1]?.pct[c.symbol] ?? 0 }))
    .sort((a, b) => a.pct - b.pct)
    .slice(0, 3);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link href="/stats" className="text-[12px] text-[var(--brand)] hover:underline">
            ← Tarihsel 1/0/2
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight mt-1">{data.week}. hafta</h1>
          <p className="text-[13px] text-[var(--muted)] mt-1">
            {data.season} · {data.close_date} · en uzun seri {data.max_streak.length}× {data.max_streak.symbol}
          </p>
        </div>
        <nav className="flex items-center gap-2">
          {data.prev_week !== null ? (
            <Link href={`/stats/${data.prev_week}`} className="btn-ghost">← {data.prev_week}. hf</Link>
          ) : (
            <span className="btn-ghost opacity-40 pointer-events-none">← önceki</span>
          )}
          {data.next_week !== null ? (
            <Link href={`/stats/${data.next_week}`} className="btn-ghost">{data.next_week}. hf →</Link>
          ) : (
            <span className="btn-ghost opacity-40 pointer-events-none">sonraki →</span>
          )}
        </nav>
      </header>

      <Card title="Sonuç dizisi" hint="Kupon sırasına göre 15 maç." right={<Legend />}>
        <ResultStrip results={data.results} size="lg" marks={(i) => `%${(pos[i]?.pct[data.results[i] as Sym] ?? 0).toFixed(0)}`} />
        <p className="text-[12px] text-[var(--muted)] mt-3">
          Kutuların altındaki yüzde, o sıradaki maçta bu sembolün sezon boyunca çıkma oranıdır.
        </p>
        {!data.consistent && data.reported_counts && (
          <p className="text-[12px] mt-3 flex items-start gap-2">
            <span aria-hidden className="text-[var(--warn)]">⚠</span>
            <span className="text-[var(--muted)]">
              Veri uyarısı: dosyadaki hazır sayım{" "}
              {SYMS.map((s) => data.reported_counts![s]).join("/")}, dizinin kendisi{" "}
              {SYMS.map((s) => data.counts[s]).join("/")} diyor. Sayfadaki tüm sayılar diziden türetilmiştir.
            </span>
          </p>
        )}
      </Card>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {SYMS.map((s) => (
          <StatTile
            key={s}
            accent={s}
            label={SYM_LABEL[s]}
            value={String(data.counts[s])}
            sub={`sezon ort. ${fmt1(data.season_avg[s])} · sıra ${data.rank[s].rank}/${data.rank[s].of}`}
            delta={data.delta_vs_avg[s]}
            deltaNote="sezon ortalamasına göre"
          />
        ))}
      </section>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,320px)]">
        <Card
          title="Sıra sıra bağlam"
          hint="Her maç sırasında sezon boyunca oluşan pay; bu haftanın sonucu işaretli."
        >
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
                <th scope="col" className="text-left font-medium py-1.5 w-10">Sıra</th>
                <th scope="col" className="text-left font-medium py-1.5 w-12">Sonuç</th>
                <th scope="col" className="text-left font-medium py-1.5">Sezon payı (1 / 0 / 2)</th>
                <th scope="col" className="text-right font-medium py-1.5 w-16">Oran</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {data.cells.map((c) => {
                const p = pos[c.pos - 1];
                const own = p?.pct[c.symbol] ?? 0;
                return (
                  <tr key={c.pos} className="border-t border-[var(--line-soft)]">
                    <td className="py-1.5 text-[var(--muted)]">{c.pos}</td>
                    <td className="py-1.5">
                      <span
                        className="inline-flex h-6 w-6 items-center justify-center rounded-md text-white text-[12px] font-semibold"
                        style={{ background: SYM_COLOR[c.symbol] }}
                      >
                        {c.symbol}
                      </span>
                    </td>
                    <td className="py-1.5">
                      <div className="flex gap-[2px] h-4 rounded-md overflow-hidden">
                        {SYMS.map((s) => (
                          <div
                            key={s}
                            title={`${SYM_LABEL[s]}: %${(p?.pct[s] ?? 0).toFixed(0)}`}
                            style={{
                              background: SYM_COLOR[s],
                              flexGrow: Math.max(p?.pct[s] ?? 0, 0.001),
                              flexBasis: 0,
                              opacity: s === c.symbol ? 1 : 0.28,
                            }}
                          />
                        ))}
                      </div>
                    </td>
                    <td className="py-1.5 text-right">%{own.toFixed(0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>

        <div className="space-y-5">
          <Card title="Sürprizler" hint="Sezonda en nadir görülen tercihler.">
            <ul className="space-y-2 text-[13px] tabular-nums">
              {surprises.map((s) => (
                <li key={s.pos} className="flex items-center gap-2">
                  <span
                    className="inline-flex h-6 w-6 items-center justify-center rounded-md text-white text-[12px] font-semibold shrink-0"
                    style={{ background: SYM_COLOR[s.symbol] }}
                  >
                    {s.symbol}
                  </span>
                  <span className="text-[var(--muted)]">
                    {s.pos}. maç · sezonda %{s.pct.toFixed(0)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Seriler" hint="Ardışık aynı sembol blokları.">
            <ul className="space-y-1.5 text-[13px] tabular-nums">
              {data.runs
                .filter((r) => r.length > 1)
                .map((r) => (
                  <li key={r.start} className="text-[var(--muted)]">
                    <span className="text-[var(--ink)] font-medium">{r.length}× {r.symbol}</span> ·{" "}
                    {r.start}–{r.start + r.length - 1}. maçlar
                  </li>
                ))}
              {data.runs.every((r) => r.length < 2) && (
                <li className="text-[var(--muted)]">Bu haftada tekrar eden ardışık sembol yok.</li>
              )}
            </ul>
            <p className="text-[12px] text-[var(--muted)] mt-3">
              Hafta içi en uzun seri: {data.max_streak.length}× {data.max_streak.symbol}
              {data.max_streak.length > 1 && <> ({data.max_streak.start}. maçtan itibaren)</>} ·
              toplam {data.runs.length} blok.
            </p>
          </Card>

        </div>
      </div>
    </div>
  );
}
