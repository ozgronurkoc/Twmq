import * as React from "react";

import { SEMBOLLER, type Sembol } from "@/lib/types";
import { cn } from "@/lib/utils";

const RENK: Record<Sembol, string> = {
  "1": "text-sym-1",
  "0": "text-sym-0",
  "2": "text-sym-2",
};

const ZEMIN: Record<Sembol, string> = {
  "1": "bg-sym-1/12 text-sym-1 border-sym-1/25",
  "0": "bg-sym-0/12 text-sym-0 border-sym-0/25",
  "2": "bg-sym-2/12 text-sym-2 border-sym-2/25",
};

export const SEMBOL_ADI: Record<Sembol, string> = {
  "1": "ev sahibi",
  "0": "beraberlik",
  "2": "deplasman",
};

/**
 * Tek bir kupon hucresi. Icerik "1", "10" ya da "102" olabilir.
 *
 * Semboller HER ZAMAN kupon duzeninde (1, 0, 2) gosterilir. Alfabetik
 * siralama "01" uretir ve kuponu elle doldururken hata yaptirir — bu
 * kuralin kaynagi motorun kendi kodudur (core.py SEMBOLLER).
 */
export function CouponCell({
  value,
  className,
}: {
  value: string;
  className?: string;
}) {
  const semboller = SEMBOLLER.filter((s) => value.includes(s));
  const coklu = semboller.length > 1;

  return (
    <span
      className={cn(
        // Genislik bilerek dar: 15 sutunluk kupon tablosunun masaustunde
        // kirpilmadan sigmasi gerekiyor. Cok isaretli hucreler dogal olarak
        // buyur, tekli hucreler hizalamayi korur.
        "tnum inline-flex min-w-[2rem] items-center justify-center gap-0.5 rounded-md border px-1 py-1",
        "font-mono text-[12.5px] font-semibold leading-none",
        coklu ? "border-line-strong bg-muted" : ZEMIN[semboller[0] ?? "1"],
        className,
      )}
    >
      {semboller.map((s) => (
        <span key={s} className={cn(coklu && RENK[s])}>
          {s}
        </span>
      ))}
    </span>
  );
}

/** 15 sembollük bir dizi ("120021012210020") icin satir gorunumu. */
export function ResultStrip({ results }: { results: string }) {
  const hucreler = results.split("").filter((c): c is Sembol =>
    (SEMBOLLER as readonly string[]).includes(c),
  );
  return (
    <div className="flex flex-wrap gap-1">
      {hucreler.map((s, i) => (
        <span
          key={i}
          title={`${i + 1}. maç · ${SEMBOL_ADI[s]}`}
          className={cn(
            "tnum grid h-7 w-7 place-items-center rounded-md border font-mono text-[12px] font-semibold",
            ZEMIN[s],
          )}
        >
          {s}
        </span>
      ))}
    </div>
  );
}

/** Renk anahtari — sembollerin ne anlama geldigini bir kez soyler. */
export function SymbolLegend({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-3", className)}>
      {SEMBOLLER.map((s) => (
        <span key={s} className="flex items-center gap-1.5">
          <span
            className={cn(
              "grid h-5 w-5 place-items-center rounded border font-mono text-[11px] font-semibold",
              ZEMIN[s],
            )}
          >
            {s}
          </span>
          <span className="text-[11.5px] text-muted-foreground">{SEMBOL_ADI[s]}</span>
        </span>
      ))}
    </div>
  );
}
