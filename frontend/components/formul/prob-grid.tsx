"use client";

import * as React from "react";
import { Wand2 } from "lucide-react";

import { SEMBOLLER, type ProbRow, type Sembol } from "@/lib/types";
import { cn, normalize, uniformProb } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { SEMBOL_ADI } from "@/components/ui/symbol";

const CIZGI: Record<Sembol, string> = {
  "1": "bg-sym-1",
  "0": "bg-sym-0",
  "2": "bg-sym-2",
};

/**
 * Mac basina 1/0/2 olasilik girisi.
 *
 * Bu, onceki arayuzde HIC olmayan parcadir. `probs` gonderilmedigi icin
 * sunucuda exact olasilik, Monte Carlo, Bayes ve Markov bloklarinin hicbiri
 * doldurulmuyordu — motorun yarisi erisilemezdi.
 *
 * Degerler sunucuya gonderilmeden once normalize edilir; kullanici ham
 * agirlik da girebilir (orn. 5 / 3 / 2), toplamin 1 olmasi sart degildir.
 */
export function ProbGrid({
  probs,
  selections,
  onChange,
  disabled,
}: {
  probs: ProbRow[];
  selections: Sembol[][];
  onChange: (next: ProbRow[]) => void;
  disabled?: boolean;
}) {
  function yaz(mac: number, sym: Sembol, deger: number) {
    const next = probs.map((r) => ({ ...r }));
    // `mac` izgaradan gelir ve gecerlidir, ama satir yoksa sessizce
    // hicbir sey yazmamak, `undefined`e alan atayip cokmekten iyidir.
    const satir = next[mac];
    if (!satir) return;
    satir[sym] = Number.isFinite(deger) ? Math.max(0, deger) : 0;
    onChange(next);
  }

  function secimdenDoldur() {
    onChange(selections.map((sel) => uniformProb(sel)));
  }

  function esitDoldur() {
    onChange(probs.map(() => ({ "1": 1 / 3, "0": 1 / 3, "2": 1 / 3 })));
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        <Button tip="outline" boyut="sm" onClick={secimdenDoldur} disabled={disabled}>
          <Wand2 size={13} />
          Seçimlerden doldur
        </Button>
        <Button tip="ghost" boyut="sm" onClick={esitDoldur} disabled={disabled}>
          Hepsi eşit (1/3)
        </Button>
      </div>

      <div className="scroll-slim -mx-1 overflow-x-auto px-1">
        <div className="min-w-[420px]">
          <div className="mb-1.5 grid grid-cols-[2rem_repeat(3,minmax(0,1fr))_4.5rem] gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              Maç
            </span>
            {SEMBOLLER.map((s) => (
              <span
                key={s}
                className="text-center text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground"
              >
                {s} · {SEMBOL_ADI[s].slice(0, 3)}
              </span>
            ))}
            <span className="text-center text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              Normalize
            </span>
          </div>

          <div className="flex flex-col gap-1.5">
            {probs.map((row, i) => {
              const norm = normalize(row);
              const secim = selections[i] || [];
              return (
                <div
                  key={i}
                  className="grid grid-cols-[2rem_repeat(3,minmax(0,1fr))_4.5rem] items-center gap-1.5"
                >
                  <span className="tnum text-right text-[11.5px] text-muted-foreground">
                    {i + 1}
                  </span>
                  {SEMBOLLER.map((s) => {
                    const secimDisi = !secim.includes(s);
                    return (
                      <input
                        key={s}
                        type="number"
                        min={0}
                        step={0.05}
                        disabled={disabled}
                        value={Number.isFinite(row[s]) ? Number(row[s].toFixed(4)) : 0}
                        onChange={(e) => yaz(i, s, Number(e.target.value))}
                        aria-label={`${i + 1}. maç ${s} olasılığı`}
                        title={
                          secimDisi
                            ? `${s} bu maçta seçili değil — küme dışı kalma olasılığına katkı verir`
                            : undefined
                        }
                        className={cn(
                          "tnum h-9 w-full rounded-lg border bg-background px-2 text-center font-mono text-[12.5px]",
                          "transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50",
                          secimDisi
                            ? "border-dashed border-line text-muted-foreground"
                            : "border-line",
                        )}
                      />
                    );
                  })}
                  <div
                    className="flex h-9 items-center gap-px overflow-hidden rounded-lg border border-line"
                    title={SEMBOLLER.map(
                      (s) => `${s}: ${(norm[s] * 100).toFixed(1)}%`,
                    ).join(" · ")}
                  >
                    {SEMBOLLER.map((s) => (
                      <span
                        key={s}
                        className={cn(CIZGI[s], "h-full transition-all duration-300 ease-ios")}
                        style={{ width: `${norm[s] * 100}%` }}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
        Ham ağırlık girebilirsin (örn. <code className="font-mono">5 / 3 / 2</code>);
        her satır sunucuya gönderilmeden 1&apos;e normalize edilir. Kesikli
        çerçeveli hücreler o maçta <strong>seçili olmayan</strong> sembollerdir —
        oraya verdiğin olasılık, sonucun seçim kümenin dışına çıkma riskini
        artırır.
      </p>
    </div>
  );
}
