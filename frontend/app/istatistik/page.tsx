"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { getStats } from "@/lib/api";
import { SEMBOLLER, type Band, type Sembol, type StatsResponse } from "@/lib/types";
import { cn, ondalik, sayi } from "@/lib/utils";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
} from "@/components/ui/primitives";
import { ResultStrip, SEMBOL_ADI, SymbolLegend } from "@/components/ui/symbol";

const SEMBOL_ZEMIN: Record<Sembol, string> = {
  "1": "bg-sym-1",
  "0": "bg-sym-0",
  "2": "bg-sym-2",
};

export default function IstatistikPage() {
  const [veri, setVeri] = React.useState<StatsResponse | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);

  React.useEffect(() => {
    const ac = new AbortController();
    getStats(ac.signal)
      .then(setVeri)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setHata(e instanceof Error ? e.message : String(e));
      });
    return () => ac.abort();
  }, []);

  if (hata) {
    return (
      <Callout ton="danger" baslik="İstatistik alınamadı">
        {hata}
      </Callout>
    );
  }

  if (!veri) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  const meta = veri.meta || {};
  const totals = veri.totals || {};
  const toplamMac = SEMBOLLER.reduce((a, s) => a + (totals[s] ?? 0), 0);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[30px] italic leading-tight">
          Tarihsel 1 / 0 / 2
        </h1>
        <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
          Geçmiş sezon sonuçlarının dağılımı. Bu veri bir tahmin değildir ve
          formül üretimine girmez — yalnızca kendi olasılık tahminlerini
          kalibre etmen için referanstır.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {meta.season ? <Badge ton="primary">{meta.season}</Badge> : null}
          <Badge>{sayi(meta.weeks)} hafta</Badge>
          <Badge>{sayi(meta.matches)} maç</Badge>
          {meta.date_from ? (
            <Badge>
              {meta.date_from} → {meta.date_to}
            </Badge>
          ) : null}
        </div>
      </header>

      {veri.error ? (
        <Callout ton="warning" baslik="Veri uyarısı">
          {veri.error}
        </Callout>
      ) : null}

      {/* Toplam dagilim */}
      <Card>
        <CardHeader
          title="Sezon dağılımı"
          hint={meta.rule}
          action={<SymbolLegend />}
        />
        <CardBody className="space-y-4">
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
            {SEMBOLLER.map((s) => {
              const pay = toplamMac ? ((totals[s] ?? 0) / toplamMac) * 100 : 0;
              return (
                <span
                  key={s}
                  className={cn(SEMBOL_ZEMIN[s], "transition-all duration-500 ease-ios")}
                  style={{ width: `${pay}%` }}
                  title={`${s} · ${pay.toFixed(1)}%`}
                />
              );
            })}
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {SEMBOLLER.map((s) => {
              const adet = totals[s] ?? 0;
              const pct = totals[`pct_${s}` as "pct_1"] ?? 0;
              const ort = veri.weekly_avg?.[s];
              return (
                <div
                  key={s}
                  className="rounded-xl border border-line bg-elevated px-4 py-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                      {SEMBOL_ADI[s]}
                    </span>
                    <span
                      className={cn(
                        "tnum grid h-6 w-6 place-items-center rounded-md font-mono text-[12px] font-bold text-white",
                        SEMBOL_ZEMIN[s],
                      )}
                    >
                      {s}
                    </span>
                  </div>
                  <div className="tnum mt-1 text-[24px] font-semibold leading-tight">
                    %{Number(pct).toFixed(1)}
                  </div>
                  <div className="tnum mt-0.5 text-[11.5px] text-muted-foreground">
                    {sayi(adet)} maç
                    {ort !== undefined
                      ? ` · haftada ort. ${Number(ort).toFixed(2)}`
                      : ""}
                  </div>
                </div>
              );
            })}
          </div>
        </CardBody>
      </Card>

      {/* Bantlar */}
      <Card>
        <CardHeader
          title="Haftalık bantlar"
          hint="Her sembolün hafta başına adet dağılımı. Ortalamanın üstü/altı, o taraftaki haftaların sayısı ve ortalamadan uzaklığıdır."
        />
        <CardBody className="scroll-slim overflow-x-auto">
          <table className="w-full min-w-[720px] text-[12.5px]">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
                <th className="pb-2 pr-3 font-medium">Sembol</th>
                <th className="pb-2 pr-3 font-medium">Ortalama</th>
                <th className="pb-2 pr-3 font-medium">Medyan</th>
                <th className="pb-2 pr-3 font-medium">En az</th>
                <th className="pb-2 pr-3 font-medium">En çok</th>
                <th className="pb-2 pr-3 font-medium">Std sapma</th>
                <th className="pb-2 pr-3 font-medium">Üst bant</th>
                <th className="pb-2 font-medium">Alt bant</th>
              </tr>
            </thead>
            <tbody className="tnum">
              {SEMBOLLER.map((s) => {
                const b = veri.bands?.[s] as Band | undefined;
                if (!b) return null;
                return (
                  <tr key={s} className="border-t border-line">
                    <td className="py-2.5 pr-3">
                      <span className="flex items-center gap-2">
                        <span
                          className={cn(
                            "grid h-5 w-5 place-items-center rounded font-mono text-[11px] font-bold text-white",
                            SEMBOL_ZEMIN[s],
                          )}
                        >
                          {s}
                        </span>
                        <span className="text-muted-foreground">{SEMBOL_ADI[s]}</span>
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 font-semibold">{ondalik(b.avg, 2)}</td>
                    <td className="py-2.5 pr-3">{sayi(b.median)}</td>
                    <td className="py-2.5 pr-3">{sayi(b.min)}</td>
                    <td className="py-2.5 pr-3">{sayi(b.max)}</td>
                    <td className="py-2.5 pr-3">{ondalik(b.std, 3)}</td>
                    <td className="py-2.5 pr-3 text-muted-foreground">
                      {ondalik(b.above_mean, 2)}{" "}
                      <span className="text-[11px]">({b.above_n} hafta)</span>
                    </td>
                    <td className="py-2.5 text-muted-foreground">
                      {ondalik(b.below_mean, 2)}{" "}
                      <span className="text-[11px]">({b.below_n} hafta)</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardBody>
      </Card>

      {/* Haftalar */}
      <Card>
        <CardHeader
          title={`Haftalar (${veri.weeks?.length ?? 0})`}
          hint={meta.source}
        />
        <CardBody className="space-y-1.5">
          {(veri.weeks || []).map((w) => (
            <Link
              key={w.week}
              href={`/istatistik/${w.week}`}
              className={cn(
                "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-line bg-elevated px-3 py-2.5",
                "transition-colors duration-200 ease-smooth hover:border-primary/40 hover:bg-accent",
              )}
            >
              <span className="tnum w-12 shrink-0 text-[13px] font-semibold">
                {w.week}.
              </span>
              <span className="tnum w-24 shrink-0 text-[11.5px] text-muted-foreground">
                {w.close_date}
              </span>
              <span className="tnum flex w-28 shrink-0 gap-2 text-[12px]">
                <span className="text-sym-1">{w.n1}</span>
                <span className="text-sym-0">{w.n0}</span>
                <span className="text-sym-2">{w.n2}</span>
              </span>
              <span className="min-w-0 flex-1">
                <ResultStrip results={w.results} />
              </span>
              <ChevronRight size={15} className="shrink-0 text-muted-foreground" />
            </Link>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
