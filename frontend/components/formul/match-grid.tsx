"use client";

import * as React from "react";

import { MAC_SAYISI, SEMBOLLER, type Sembol } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SEMBOL_ADI } from "@/components/ui/symbol";

const SECILI: Record<Sembol, string> = {
  "1": "bg-sym-1 text-white border-sym-1 shadow-sm",
  "0": "bg-sym-0 text-white border-sym-0 shadow-sm",
  "2": "bg-sym-2 text-white border-sym-2 shadow-sm",
};

/**
 * 15 mac x 3 sembol secim izgarasi.
 *
 * Semboller daima kupon duzeninde (1, 0, 2). Bir macin son sembolu
 * kaldirilamaz — bos mac motorda ValueError uretir, o yuzden UI en az bir
 * secimi garanti eder.
 *
 * Klavye: ok tuslariyla gezinme, 1/0/2 tuslariyla dogrudan degistirme.
 * 45 hedefi yalnizca fareyle doldurmak eziyet.
 */
export function MatchGrid({
  matches,
  labels,
  onChange,
  disabled,
}: {
  matches: Sembol[][];
  /** 15 takım adı; boş olanlar yalnızca numarayla gösterilir. */
  labels: string[];
  onChange: (next: Sembol[][]) => void;
  disabled?: boolean;
}) {
  const refs = React.useRef<(HTMLButtonElement | null)[][]>([]);
  const adVar = labels.some(Boolean);

  function degistir(mac: number, sym: Sembol) {
    const next = matches.map((r) => [...r]);
    const satir = next[mac];
    // `noUncheckedIndexedAccess`: dizi erisimi `undefined` de dondurebilir.
    // Burada `mac` izgaradan gelir ve gecerlidir, ama guard hem tipi
    // daraltir hem de cagrian taraf bir gun kayarsa sessiz cokme yerine
    // sessiz NO-OP verir.
    if (!satir) return;
    if (satir.includes(sym)) {
      // Son sembol kaldirilamaz.
      if (satir.length === 1) return;
      next[mac] = satir.filter((s) => s !== sym);
    } else {
      next[mac] = SEMBOLLER.filter((s) => satir.includes(s) || s === sym);
    }
    onChange(next);
  }

  function odakla(mac: number, sut: number) {
    const m = Math.max(0, Math.min(MAC_SAYISI - 1, mac));
    const s = Math.max(0, Math.min(SEMBOLLER.length - 1, sut));
    refs.current[m]?.[s]?.focus();
  }

  function tusla(e: React.KeyboardEvent, mac: number, sut: number) {
    const tus = e.key;
    if (tus === "ArrowDown") {
      e.preventDefault();
      odakla(mac + 1, sut);
    } else if (tus === "ArrowUp") {
      e.preventDefault();
      odakla(mac - 1, sut);
    } else if (tus === "ArrowRight") {
      e.preventDefault();
      odakla(mac, sut + 1);
    } else if (tus === "ArrowLeft") {
      e.preventDefault();
      odakla(mac, sut - 1);
    } else if ((SEMBOLLER as readonly string[]).includes(tus)) {
      e.preventDefault();
      degistir(mac, tus as Sembol);
    }
  }

  return (
    <div>
      <div className="mb-2 grid grid-cols-[2rem_repeat(3,minmax(0,1fr))] gap-1.5 px-0.5">
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
      </div>

      <div className={cn("flex flex-col", adVar ? "gap-2.5" : "gap-1.5")}>
        {matches.map((satir, i) => {
          const tekli = satir.length === 1;
          const ad = labels[i] || "";
          return (
            <div key={i}>
              {/*
                Ad, dugme satirinin USTUNDE tam genislikte durur. Sola
                sutun olarak konsaydi 420 px'lik girdi kolonunda ya adi ya
                dugmeleri okunmaz hale getirirdi.
              */}
              {/*
                Numara BURADA tekrarlanmaz: hemen altindaki dugme satirinda
                zaten var ve orada ayrica banko/cifte renk kodunu tasiyor.
                Ad, o numara sutunuyla ayni hizada baslar.
              */}
              {adVar ? (
                <div
                  className="mb-0.5 truncate pl-0.5 text-[11.5px] leading-tight"
                  title={ad || undefined}
                >
                  <span className={ad ? "text-foreground" : "italic text-muted-foreground"}>
                    {ad || "adsız"}
                  </span>
                </div>
              ) : null}

              <div className="grid grid-cols-[2rem_repeat(3,minmax(0,1fr))] items-center gap-1.5">
              <span
                className={cn(
                  "tnum text-right text-[11.5px] font-medium tabular-nums",
                  tekli ? "text-muted-foreground" : "text-primary",
                )}
              >
                {i + 1}
              </span>
              {SEMBOLLER.map((sym, j) => {
                const secili = satir.includes(sym);
                const sonSembol = secili && satir.length === 1;
                return (
                  <button
                    key={sym}
                    ref={(el) => {
                      if (!refs.current[i]) refs.current[i] = [];
                      refs.current[i][j] = el;
                    }}
                    type="button"
                    disabled={disabled}
                    aria-pressed={secili}
                    aria-label={`${i + 1}. maç ${sym} (${SEMBOL_ADI[sym]})`}
                    title={sonSembol ? "Son sembol kaldırılamaz" : undefined}
                    onClick={() => degistir(i, sym)}
                    onKeyDown={(e) => tusla(e, i, j)}
                    className={cn(
                      "h-9 rounded-lg border font-mono text-[13.5px] font-semibold",
                      "transition-all duration-150 ease-smooth",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60",
                      "disabled:pointer-events-none disabled:opacity-50",
                      secili
                        ? SECILI[sym]
                        : "border-line bg-background text-muted-foreground hover:border-line-strong hover:bg-muted",
                      sonSembol && "cursor-default",
                    )}
                  >
                    {sym}
                  </button>
                );
              })}
            </div>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
        Ok tuşlarıyla gezin, <kbd className="rounded border border-line px-1">1</kbd>{" "}
        <kbd className="rounded border border-line px-1">0</kbd>{" "}
        <kbd className="rounded border border-line px-1">2</kbd> ile değiştir.
        Tek işaretli maç <strong>banko</strong>, iki işaretli <strong>çifte</strong>,
        üç işaretli <strong>kapama</strong>dır.
      </p>
    </div>
  );
}
