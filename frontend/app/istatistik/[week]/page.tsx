"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";

import { getStatsWeek } from "@/lib/api";
import { SEMBOLLER, type Sembol, type WeekDetail } from "@/lib/types";
import { cn, ondalik } from "@/lib/utils";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
} from "@/components/ui/primitives";
import { SEMBOL_ADI, SymbolLegend } from "@/components/ui/symbol";
import { DeltaStat } from "@/components/istatistik/parts";
import { SYM_BG } from "@/components/istatistik/viz";

const ZEMIN: Record<Sembol, string> = {
  "1": "bg-sym-1/12 text-sym-1 border-sym-1/25",
  "0": "bg-sym-0/12 text-sym-0 border-sym-0/25",
  "2": "bg-sym-2/12 text-sym-2 border-sym-2/25",
};

export default function HaftaPage({ params }: { params: { week: string } }) {
  const week = Number(params.week);
  const [veri, setVeri] = React.useState<WeekDetail | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!Number.isFinite(week)) {
      setHata("Geçersiz hafta numarası");
      return;
    }
    const ac = new AbortController();
    setVeri(null);
    setHata(null);
    getStatsWeek(week, ac.signal)
      .then(setVeri)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setHata(e instanceof Error ? e.message : String(e));
      });
    return () => ac.abort();
  }, [week]);

  // Sezonda en nadir gorulen tercihler — bu haftanin surprizleri.
  const surprizler = React.useMemo(() => {
    if (!veri) return [];
    return veri.cells
      .map((c) => ({ ...c, pct: veri.position_stats[c.pos - 1]?.pct[c.symbol] ?? 0 }))
      .sort((a, b) => a.pct - b.pct)
      .slice(0, 3);
  }, [veri]);

  return (
    <div className="space-y-6">
      <Link
        href="/istatistik"
        className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft size={15} />
        Tüm haftalar
      </Link>

      {hata ? (
        <Callout ton="danger" baslik="Hafta bulunamadı">
          {hata}
        </Callout>
      ) : null}

      {!veri && !hata ? <Skeleton className="h-72 w-full" /> : null}

      {veri ? (
        <>
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-[30px] italic leading-tight">{veri.week}. hafta</h1>
              <p className="tnum mt-1 text-[13px] text-muted-foreground">
                {veri.close_date} · {veri.season} · en uzun seri {veri.max_streak.length}×{" "}
                {veri.max_streak.symbol}
              </p>
            </div>
            <nav className="flex items-center gap-2">
              {veri.prev_week !== null ? (
                <Link
                  href={`/istatistik/${veri.prev_week}`}
                  className="inline-flex h-9 items-center gap-1 rounded-xl border border-line-strong px-3 text-[12.5px] transition-colors hover:bg-muted"
                >
                  <ChevronLeft size={14} />
                  {veri.prev_week}. hf
                </Link>
              ) : null}
              {veri.next_week !== null ? (
                <Link
                  href={`/istatistik/${veri.next_week}`}
                  className="inline-flex h-9 items-center gap-1 rounded-xl border border-line-strong px-3 text-[12.5px] transition-colors hover:bg-muted"
                >
                  {veri.next_week}. hf
                  <ChevronRight size={14} />
                </Link>
              ) : null}
            </nav>
          </header>

          {!veri.consistent && veri.reported_counts ? (
            <Callout ton="warning" baslik="Veri uyarısı">
              Dosyadaki hazır sayım {SEMBOLLER.map((s) => veri.reported_counts![s]).join("/")},
              dizinin kendisi {SEMBOLLER.map((s) => veri.counts[s]).join("/")} diyor. Bu sayfadaki
              tüm sayılar 15 karakterlik diziden türetilmiştir.
            </Callout>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-3">
            {SEMBOLLER.map((s) => (
              <DeltaStat
                key={s}
                rozet={s}
                rozetSinif={SYM_BG[s]}
                etiket={SEMBOL_ADI[s]}
                deger={String(veri.counts[s])}
                alt={`sezon ort. ${ondalik(veri.season_avg[s], 1)} · sıra ${veri.rank[s].rank}/${veri.rank[s].of}`}
                delta={veri.delta_vs_avg[s]}
                deltaNot="sezon ortalamasına göre"
              />
            ))}
          </div>

          <Card>
            <CardHeader
              title="Maç maç sonuçlar"
              hint="Semboller kupon düzeninde (1, 0, 2) gösterilir. Yüzde, o sıradaki maçta bu sembolün sezon boyunca çıkma oranıdır."
              action={<SymbolLegend />}
            />
            <CardBody>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                {veri.cells.map((c) => (
                  <div
                    key={c.pos}
                    className={cn(
                      "flex items-center gap-2.5 rounded-xl border px-3 py-2.5",
                      ZEMIN[c.symbol],
                    )}
                  >
                    <span className="tnum text-[11px] font-medium text-muted-foreground">
                      {String(c.pos).padStart(2, "0")}
                    </span>
                    <span className="tnum font-mono text-[17px] font-bold">{c.symbol}</span>
                    <span className="tnum ml-auto text-[11px] opacity-80">
                      %{(veri.position_stats[c.pos - 1]?.pct[c.symbol] ?? 0).toFixed(0)}
                    </span>
                  </div>
                ))}
              </div>
              <code className="tnum mt-4 block break-all rounded-lg bg-muted px-3 py-2 font-mono text-[12.5px]">
                {veri.results}
              </code>
            </CardBody>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,320px)]">
            <Card>
              <CardHeader
                title="Sıra sıra bağlam"
                hint="Her maç sırasında sezon boyunca oluşan pay; bu haftanın sonucu tam renkte, diğerleri soluk."
              />
              <CardBody className="scroll-slim overflow-x-auto">
                <table className="w-full min-w-[420px] text-[12.5px]">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
                      <th scope="col" className="w-10 pb-2 font-medium">
                        Sıra
                      </th>
                      <th scope="col" className="w-12 pb-2 font-medium">
                        Sonuç
                      </th>
                      <th scope="col" className="pb-2 font-medium">
                        Sezon payı (1 / 0 / 2)
                      </th>
                      <th scope="col" className="w-16 pb-2 text-right font-medium">
                        Oran
                      </th>
                    </tr>
                  </thead>
                  <tbody className="tnum">
                    {veri.cells.map((c) => {
                      const p = veri.position_stats[c.pos - 1];
                      const kendi = p?.pct[c.symbol] ?? 0;
                      return (
                        <tr key={c.pos} className="border-t border-line">
                          <td className="py-1.5 text-muted-foreground">{c.pos}</td>
                          <td className="py-1.5">
                            <span
                              className={cn(
                                "grid h-6 w-6 place-items-center rounded-md font-mono text-[12px] font-bold text-white",
                                SYM_BG[c.symbol],
                              )}
                            >
                              {c.symbol}
                            </span>
                          </td>
                          <td className="py-1.5">
                            <div className="flex h-4 gap-[2px] overflow-hidden rounded-md">
                              {SEMBOLLER.map((s) => (
                                <div
                                  key={s}
                                  title={`${SEMBOL_ADI[s]}: %${(p?.pct[s] ?? 0).toFixed(0)}`}
                                  className={SYM_BG[s]}
                                  style={{
                                    flexGrow: Math.max(p?.pct[s] ?? 0, 0.001),
                                    flexBasis: 0,
                                    opacity: s === c.symbol ? 1 : 0.28,
                                  }}
                                />
                              ))}
                            </div>
                          </td>
                          <td className="py-1.5 text-right">%{kendi.toFixed(0)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </CardBody>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader title="Sürprizler" hint="Sezonda en nadir görülen tercihler." />
                <CardBody>
                  <ul className="tnum space-y-2 text-[12.5px]">
                    {surprizler.map((s) => (
                      <li key={s.pos} className="flex items-center gap-2">
                        <span
                          className={cn(
                            "grid h-6 w-6 shrink-0 place-items-center rounded-md font-mono text-[12px] font-bold text-white",
                            SYM_BG[s.symbol],
                          )}
                        >
                          {s.symbol}
                        </span>
                        <span className="text-muted-foreground">
                          {s.pos}. maç · sezonda %{s.pct.toFixed(0)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </CardBody>
              </Card>

              <Card>
                <CardHeader title="Seriler" hint="Ardışık aynı sembol blokları." />
                <CardBody>
                  <ul className="tnum space-y-1.5 text-[12.5px] text-muted-foreground">
                    {veri.runs
                      .filter((r) => r.length > 1)
                      .map((r) => (
                        <li key={r.start}>
                          <span className="font-medium text-foreground">
                            {r.length}× {r.symbol}
                          </span>{" "}
                          · {r.start}–{r.start + r.length - 1}. maçlar
                        </li>
                      ))}
                    {veri.runs.every((r) => r.length < 2) ? (
                      <li>Bu haftada ardışık tekrar eden sembol yok.</li>
                    ) : null}
                  </ul>
                  <p className="mt-3 text-[11.5px] text-muted-foreground">
                    Toplam {veri.runs.length} blok.
                  </p>
                </CardBody>
              </Card>

              <div className="flex flex-wrap gap-2">
                <Badge ton="primary">{veri.counts["1"]} ev</Badge>
                <Badge>{veri.counts["0"]} beraberlik</Badge>
                <Badge>{veri.counts["2"]} deplasman</Badge>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
