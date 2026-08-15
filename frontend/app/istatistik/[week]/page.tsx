"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { getStatsWeek } from "@/lib/api";
import { SEMBOLLER, type Sembol, type WeekRow } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";
import { SEMBOL_ADI, SymbolLegend } from "@/components/ui/symbol";

const ZEMIN: Record<Sembol, string> = {
  "1": "bg-sym-1/12 text-sym-1 border-sym-1/25",
  "0": "bg-sym-0/12 text-sym-0 border-sym-0/25",
  "2": "bg-sym-2/12 text-sym-2 border-sym-2/25",
};

export default function HaftaPage({ params }: { params: { week: string } }) {
  const week = Number(params.week);
  const [veri, setVeri] = React.useState<WeekRow | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!Number.isFinite(week)) {
      setHata("Geçersiz hafta numarası");
      return;
    }
    const ac = new AbortController();
    getStatsWeek(week, ac.signal)
      .then(setVeri)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setHata(e instanceof Error ? e.message : String(e));
      });
    return () => ac.abort();
  }, [week]);

  const semboller = React.useMemo(
    () =>
      (veri?.results || "")
        .split("")
        .filter((c): c is Sembol => (SEMBOLLER as readonly string[]).includes(c)),
    [veri],
  );

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
              <h1 className="font-display text-[30px] italic leading-tight">
                {veri.week}. hafta
              </h1>
              <p className="tnum mt-1 text-[13px] text-muted-foreground">
                {veri.close_date} · {veri.season}
              </p>
            </div>
            <div className="flex gap-2">
              <Badge ton="primary">{veri.n1} ev</Badge>
              <Badge>{veri.n0} beraberlik</Badge>
              <Badge>{veri.n2} deplasman</Badge>
            </div>
          </header>

          <div className="grid gap-4 sm:grid-cols-3">
            {SEMBOLLER.map((s) => {
              const adet =
                s === "1" ? veri.n1 : s === "0" ? veri.n0 : veri.n2;
              return (
                <Stat
                  key={s}
                  etiket={`${s} · ${SEMBOL_ADI[s]}`}
                  deger={adet}
                  alt={`15 maçın %${((adet / 15) * 100).toFixed(0)}'i`}
                />
              );
            })}
          </div>

          <Card>
            <CardHeader
              title="Maç maç sonuçlar"
              hint="Semboller kupon düzeninde (1, 0, 2) gösterilir."
              action={<SymbolLegend />}
            />
            <CardBody>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                {semboller.map((s, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex items-center gap-2.5 rounded-xl border px-3 py-2.5",
                      ZEMIN[s],
                    )}
                  >
                    <span className="tnum text-[11px] font-medium text-muted-foreground">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="tnum font-mono text-[17px] font-bold">{s}</span>
                    <span className="truncate text-[11px] opacity-80">
                      {SEMBOL_ADI[s]}
                    </span>
                  </div>
                ))}
              </div>
              <code className="tnum mt-4 block break-all rounded-lg bg-muted px-3 py-2 font-mono text-[12.5px]">
                {veri.results}
              </code>
            </CardBody>
          </Card>
        </>
      ) : null}
    </div>
  );
}
