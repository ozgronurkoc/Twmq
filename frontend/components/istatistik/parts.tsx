"use client";

import * as React from "react";

import { SEMBOLLER, type DataQuality } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { ResultStrip } from "@/components/ui/symbol";
import { isaretli } from "./viz";

/**
 * Tum gorselleri kapsayan TEK filtre satiri. Kart icine filtre koymuyoruz:
 * secim degisince butun bloklar ayni dilim uzerinden yeniden hesaplanir,
 * boylece iki gorsel asla farkli veriyi anlatmaz.
 */
export function RangeFilter({
  deger,
  onChange,
  secenekler,
  mesgul,
}: {
  deger: number | null;
  onChange: (v: number | null) => void;
  secenekler: Array<{ deger: number | null; etiket: string }>;
  mesgul?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Hafta aralığı">
      {secenekler.map((o) => {
        const secili = o.deger === deger;
        return (
          <Button
            key={String(o.deger)}
            type="button"
            tip={secili ? "primary" : "outline"}
            boyut="sm"
            aria-pressed={secili}
            onClick={() => onChange(o.deger)}
          >
            {o.etiket}
          </Button>
        );
      })}
      <span
        aria-live="polite"
        className={cn(
          "text-[11.5px] text-muted-foreground transition-opacity duration-200",
          mesgul ? "opacity-100" : "opacity-0",
        )}
      >
        güncelleniyor…
      </span>
    </div>
  );
}

/** Sayi kutusu — Stat'in sembol rozetli ve farkli surumu. */
export function DeltaStat({
  etiket,
  deger,
  alt,
  delta,
  deltaNot,
  rozet,
  rozetSinif,
}: {
  etiket: string;
  deger: string;
  alt?: string;
  delta?: number;
  deltaNot?: string;
  rozet?: string;
  rozetSinif?: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-elevated px-4 py-3">
      <div className="flex items-center gap-1.5">
        {rozet ? (
          <span
            className={cn(
              "tnum grid h-5 w-5 place-items-center rounded font-mono text-[11px] font-bold text-white",
              rozetSinif,
            )}
          >
            {rozet}
          </span>
        ) : null}
        <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          {etiket}
        </span>
      </div>
      <div className="tnum mt-1 text-[24px] font-semibold leading-tight">{deger}</div>
      {alt ? <div className="tnum mt-0.5 text-[11.5px] text-muted-foreground">{alt}</div> : null}
      {delta !== undefined ? (
        <div className="mt-1.5 text-[11.5px] text-muted-foreground">
          <span className="tnum font-medium text-foreground">{isaretli(delta)}</span>
          {deltaNot ? ` ${deltaNot}` : ""}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Veri kalitesi. Dosyadaki hazir sayim ile 15 karakterlik dizi
 * catistiginda fark burada acikca listelenir — sessizce yutulmaz.
 */
export function DataQualityPanel({ dq }: { dq: DataQuality }) {
  const catisma = dq.count_conflicts ?? [];
  const kopya = dq.duplicate_results ?? [];
  const eksik = dq.incomplete_weeks ?? [];

  if (dq.ok) {
    return (
      <p className="flex items-center gap-2 text-[13px] text-muted-foreground">
        <span aria-hidden className="text-success">
          ✓
        </span>
        {dq.weeks_total} haftanın tamamı tutarlı: sayımlar sonuç dizisiyle birebir örtüşüyor.
      </p>
    );
  }

  return (
    <div className="space-y-3 text-[13px]">
      <p className="flex items-start gap-2">
        <span aria-hidden className="text-warning">
          ⚠
        </span>
        <span>
          <strong className="font-semibold">Veri uyarısı.</strong> Sayımlar 15 karakterlik{" "}
          <code className="text-[12px]">results</code> dizisinden türetilir; dosyadaki hazır{" "}
          <code className="text-[12px]">n1/n0/n2</code> alanları çeliştiğinde aşağıda listelenir.
        </span>
      </p>

      {catisma.length > 0 ? (
        <div>
          <div className="mb-1.5 text-muted-foreground">Sayım çelişkisi: {catisma.length} hafta</div>
          <ul className="tnum space-y-1">
            {catisma.map((c) => (
              <li key={c.week}>
                <span className="font-medium">{c.week}. hafta</span>{" "}
                <span className="text-muted-foreground">
                  dosya {SEMBOLLER.map((s) => c.reported?.[s] ?? 0).join("/")} · dizi{" "}
                  {SEMBOLLER.map((s) => c.derived[s]).join("/")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {kopya.length > 0 ? (
        <div>
          <div className="mb-1.5 text-muted-foreground">Aynı sonuç dizisi tekrar eden haftalar</div>
          <ul className="space-y-2">
            {kopya.map((d) => (
              <li key={d.results} className="flex flex-wrap items-center gap-2">
                <span className="tnum">{d.weeks.join(" · ")}. hafta</span>
                <ResultStrip results={d.results} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {eksik.length > 0 ? (
        <div className="text-muted-foreground">
          Eksik hafta (15 maçtan az): {eksik.join(", ")}
        </div>
      ) : null}
    </div>
  );
}
