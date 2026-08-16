"use client";

import * as React from "react";
import Link from "next/link";
import { Download } from "lucide-react";

import { SEMBOLLER, type OddsSummary, type Sembol, type WeekRow } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { ResultStrip } from "@/components/ui/symbol";

type SiraAnahtari = "week" | Sembol | "streak" | "brier";

const BASLIKLAR: Array<{ key: SiraAnahtari; etiket: string; baslik: string }> = [
  { key: "week", etiket: "Hf", baslik: "Hafta" },
  { key: "1", etiket: "1", baslik: "Ev sahibi" },
  { key: "0", etiket: "0", baslik: "Beraberlik" },
  { key: "2", etiket: "2", baslik: "Deplasman" },
  { key: "streak", etiket: "Seri", baslik: "Hafta içindeki en uzun aynı-sembol serisi" },
];

type BrierSatiri = OddsSummary["weekly_brier"][number];

/** CSV alanı: ayırıcı, tırnak ve satır sonu içeren değerler tırnaklanır. */
function csvAlan(v: string | number): string {
  const s = String(v);
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * Sayfadaki tabloyu oldugu gibi CSV'ye cevirir.
 *
 * Ayirici NOKTALI VIRGUL ve ondalik VIRGUL: Turkce yerelde Excel bunu
 * bekliyor, virgullu CSV tek sutuna yapisiyor. BOM da bu yuzden var —
 * onsuz Excel dosyayi latin-1 okuyup Turkce karakterleri bozuyor.
 */
function csvUret(rows: WeekRow[], brier: Map<number, BrierSatiri>): string {
  const basliklar = [
    "hafta", "tarih", "sezon", "1", "0", "2", "en_uzun_seri", "seri_sembolu",
    "sonuc_dizisi", "oranli_mac", "favori_isabet", "brier", "kismi_oran",
  ];
  const satirlar = rows.map((w) => {
    const b = brier.get(w.week);
    return [
      w.week,
      w.close_date,
      w.season,
      w.counts["1"],
      w.counts["0"],
      w.counts["2"],
      w.max_streak.length,
      w.max_streak.symbol,
      w.results,
      b ? b.n : "",
      b ? b.favourite_hit : "",
      b ? String(b.brier).replace(".", ",") : "",
      b ? (b.partial ? "evet" : "hayır") : "",
    ].map(csvAlan).join(";");
  });
  return "﻿" + [basliklar.join(";"), ...satirlar].join("\r\n") + "\r\n";
}

function csvIndir(metin: string, ad: string) {
  const blob = new Blob([metin], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = ad;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Serbest birakmayi bir sonraki tick'e birakiyoruz; hemen revoke edilirse
  // bazi tarayicilar indirmeyi baslatmadan baglantiyi kaybediyor.
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * Gorsellerin tablo karsiligi. Her grafikte okunabilen her deger burada da
 * durur — hicbir sayi yalnizca renge ya da ipucuna birakilmaz.
 */
export function WeeksTable({
  weeks,
  avg,
  brier,
  brierAvg,
}: {
  weeks: WeekRow[];
  avg: Partial<Record<Sembol, number>>;
  /** Hafta numarasına göre piyasa Brier skoru; oran arşivi yoksa boş. */
  brier?: OddsSummary["weekly_brier"];
  brierAvg?: number;
}) {
  const [arama, setArama] = React.useState("");
  const [sira, setSira] = React.useState<SiraAnahtari>("week");
  const [azalan, setAzalan] = React.useState(false);

  const brierHarita = React.useMemo(
    () => new Map((brier ?? []).map((b) => [b.week, b])),
    [brier],
  );
  const brierVar = brierHarita.size > 0;

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
      sira === "week"
        ? w.week
        : sira === "streak"
          ? w.max_streak.length
          : sira === "brier"
            ? // Oransiz haftalar siralamada en sona dussun.
              (brierHarita.get(w.week)?.brier ?? -1)
            : w.counts[sira];
    return [...suzulmus].sort(
      (a, b) => (azalan ? deger(b) - deger(a) : deger(a) - deger(b)) || a.week - b.week,
    );
  }, [weeks, arama, sira, azalan, brierHarita]);

  function degistir(key: SiraAnahtari) {
    if (key === sira) {
      setAzalan((d) => !d);
    } else {
      setSira(key);
      setAzalan(key !== "week");
    }
  }

  const basliklar = brierVar
    ? [...BASLIKLAR, { key: "brier" as SiraAnahtari, etiket: "Brier", baslik: "Piyasanın o haftaki yanılma ölçüsü — yüksek = sürprizli hafta" }]
    : BASLIKLAR;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
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
        <div className="flex items-center gap-3">
          <span className="tnum text-[11.5px] text-muted-foreground">{satirlar.length} hafta</span>
          <Button
            tip="outline"
            boyut="sm"
            onClick={() =>
              csvIndir(
                csvUret(satirlar, brierHarita),
                `spor-toto-haftalar-${satirlar.length}.csv`,
              )
            }
            title="Görünen satırları CSV olarak indir (noktalı virgül ayraçlı, Excel uyumlu)"
          >
            <Download size={13} />
            CSV
          </Button>
        </div>
      </div>

      <div className="scroll-slim overflow-x-auto">
        <table className="w-full min-w-[720px] text-[12.5px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
              {basliklar.map((h) => (
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
            {satirlar.map((w) => {
              const b = brierHarita.get(w.week);
              return (
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
                  {brierVar ? (
                    <td className="py-2 pr-3">
                      {b ? (
                        <span
                          className={cn(
                            brierAvg !== undefined && b.brier > brierAvg
                              ? "font-semibold text-warning"
                              : "text-muted-foreground",
                          )}
                          title={
                            `${b.n} maç · favori ${b.favourite_hit} kez tuttu` +
                            (b.partial ? " · bu haftanın bazı maçlarında oran yok" : "")
                          }
                        >
                          {b.brier.toFixed(3)}
                          {b.partial ? <span className="ml-1 text-[10px]">kısmi</span> : null}
                        </span>
                      ) : (
                        <span className="text-muted-foreground" title="Bu haftada oran yok">
                          —
                        </span>
                      )}
                    </td>
                  ) : null}
                  <td className="whitespace-nowrap py-2 pr-3 text-muted-foreground">
                    {w.close_date}
                  </td>
                  <td className="py-2">
                    <Link href={`/istatistik/${w.week}`} aria-label={`${w.week}. hafta detayı`}>
                      <ResultStrip results={w.results} />
                    </Link>
                  </td>
                </tr>
              );
            })}
            {satirlar.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-6 text-center text-muted-foreground">
                  Eşleşen hafta yok.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Kalın yazılan sayılar, sezon ortalamasının 2 üstünde kapatan haftaları işaretler.
        {brierVar ? (
          <>
            {" "}
            <strong className="text-foreground">Brier</strong>, piyasanın o haftaki yanılma
            ölçüsüdür: Σ(olasılık − gerçekleşme)². Sıfır kusursuz, 0,667 üç sembole eşit olasılık
            vermeye denk. Sezon ortalamasının
            {brierAvg !== undefined ? ` (${brierAvg.toFixed(3)})` : ""} üstünde kalan haftalar
            turuncu — piyasanın en çok yanıldığı, yani sürprizli haftalar. “Kısmi”, o haftanın
            bütün maçlarında oran bulunmadığını söyler; karşılaştırmaya girmemeli.
          </>
        ) : null}{" "}
        CSV düğmesi <strong className="text-foreground">görünen</strong> satırları indirir: arama
        ve sıralama neyi bırakıyorsa o.
      </p>
    </div>
  );
}
