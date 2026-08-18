"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ChevronLeft, ChevronRight, Wand2 } from "lucide-react";

import { getStatsWeek } from "@/lib/api";
import { DEVIR_PARAM, haftaDevret } from "@/lib/transfer";
import { SEMBOLLER, type ProbRow, type WeekDetail } from "@/lib/types";
import { cn, ondalik } from "@/lib/utils";
import {
  Badge,
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
} from "@/components/ui/primitives";
import { SEMBOL_ADI, SymbolLegend } from "@/components/ui/symbol";
import { DeltaStat } from "@/components/istatistik/parts";
import { SYM_BG } from "@/components/istatistik/viz";

/** Oranı olmayan maç 1/3'e düşer — uydurulmaz, eşit dağıtılır ve söylenir. */
const ESIT: ProbRow = { "1": 1 / 3, "0": 1 / 3, "2": 1 / 3 };

export default function HaftaPage({ params }: { params: { week: string } }) {
  const week = Number(params.week);
  const router = useRouter();
  const [veri, setVeri] = React.useState<WeekDetail | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);
  const [devirHatasi, setDevirHatasi] = React.useState<string | null>(null);

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

  const oranliMac = veri ? Object.keys(veri.odds || {}).length : 0;

  /**
   * Bu haftanin 15 macini formul sayfasina tasir. Tasinan sey YALNIZCA
   * olasiliktir; isaretleri (banko/cifte/uclu) kullanici kendisi secer —
   * kaplama motoru tahmin etmez, tahmini garantiye alir (olasilik icin
   * /tahmin sayfasi var).
   */
  function formuleGonder() {
    if (!veri) return;
    const probs: ProbRow[] = [];
    const labels: string[] = [];
    const missing: number[] = [];
    for (let i = 1; i <= veri.cells.length; i++) {
      const oran = veri.odds?.[String(i)];
      const mac = veri.matches?.[i - 1];
      probs.push(oran ? { ...oran.probs } : { ...ESIT });
      labels.push(mac ? `${mac.home} – ${mac.away}` : "");
      if (!oran) missing.push(i);
    }
    const ok = haftaDevret({
      week: veri.week,
      probs,
      labels,
      missing,
      note: `${veri.week}. haftanın kapanış oranlarından (marj arındırılmış)`,
    });
    if (!ok) {
      setDevirHatasi(
        "Tarayıcı oturum deposu kullanılamıyor (özel sekme olabilir); hafta formüle taşınamadı.",
      );
      return;
    }
    router.push(`/?${DEVIR_PARAM}=${veri.week}`);
  }

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
              {oranliMac > 0 ? (
                <Button
                  tip="outline"
                  boyut="sm"
                  className="h-9"
                  onClick={formuleGonder}
                  title="15 maçın kapanış oranından türeyen olasılıkları formül sayfasına taşır"
                >
                  <Wand2 size={14} />
                  Bu haftayı formüle gönder
                </Button>
              ) : null}
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

          {devirHatasi ? (
            <Callout ton="warning" baslik="Formüle gönderilemedi">
              {devirHatasi}
            </Callout>
          ) : null}

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

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,320px)]">
            <Card>
              <CardHeader
                title="Maç maç sonuçlar"
                hint="Sezon payı çubuğunda bu haftanın sonucu tam renkte, diğer iki ihtimal soluktur; oran, o sıradaki maçta bu sembolün sezon boyunca çıkma yüzdesidir."
                action={<SymbolLegend />}
              />
              <CardBody className="scroll-slim overflow-x-auto">
                <table className="w-full min-w-[640px] text-[12.5px]">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
                      <th scope="col" className="w-8 pb-2 font-medium">
                        #
                      </th>
                      <th scope="col" className="pb-2 pr-3 font-medium">
                        Maç
                      </th>
                      <th scope="col" className="w-14 pb-2 font-medium">
                        Skor
                      </th>
                      <th scope="col" className="w-12 pb-2 font-medium">
                        Sonuç
                      </th>
                      <th scope="col" className="w-36 pb-2 font-medium">
                        Sezon payı (1 / 0 / 2)
                      </th>
                      <th scope="col" className="w-14 pb-2 text-right font-medium">
                        Sıra payı
                      </th>
                      <th scope="col" className="w-32 pb-2 pl-3 font-medium">
                        Kapanış oranı
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {veri.cells.map((c) => {
                      const p = veri.position_stats[c.pos - 1];
                      const kendi = p?.pct[c.symbol] ?? 0;
                      const mac = veri.matches?.[c.pos - 1];
                      const oran = veri.odds?.[String(c.pos)];
                      return (
                        <tr key={c.pos} className="border-t border-line align-middle">
                          <td className="tnum py-2 text-muted-foreground">{c.pos}</td>
                          <td className="py-2 pr-3">
                            {mac ? (
                              <>
                                <span className={c.symbol === "1" ? "font-medium" : ""}>
                                  {mac.home}
                                </span>
                                <span className="text-muted-foreground"> – </span>
                                <span className={c.symbol === "2" ? "font-medium" : ""}>
                                  {mac.away}
                                </span>
                                {mac.kickoff ? (
                                  <span className="tnum block text-[11px] text-muted-foreground">
                                    {mac.kickoff}
                                  </span>
                                ) : null}
                              </>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="tnum py-2 font-mono">
                            {mac && mac.hg !== null ? `${mac.hg}-${mac.ag}` : "—"}
                          </td>
                          <td className="py-2">
                            <span
                              className={cn(
                                "grid h-6 w-6 place-items-center rounded-md font-mono text-[12px] font-bold text-white",
                                SYM_BG[c.symbol],
                              )}
                            >
                              {c.symbol}
                            </span>
                          </td>
                          <td className="py-2 pr-3">
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
                          <td className="tnum py-2 text-right">%{kendi.toFixed(0)}</td>
                          <td className="py-2 pl-3">
                            {oran ? (
                              <span className="tnum flex items-center gap-1.5 font-mono text-[12px]">
                                {SEMBOLLER.map((s) => (
                                  <span
                                    key={s}
                                    title={`${SEMBOL_ADI[s]} · %${(oran.probs[s] * 100).toFixed(0)}${
                                      s === oran.favourite ? " · favori" : ""
                                    }`}
                                    className={cn(
                                      "rounded px-1 py-0.5",
                                      s === oran.favourite
                                        ? "bg-primary/12 font-semibold text-foreground"
                                        : "text-muted-foreground",
                                    )}
                                  >
                                    {oran.odds[s].toFixed(2)}
                                  </span>
                                ))}
                              </span>
                            ) : (
                              <span className="text-[11.5px] text-muted-foreground">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {oranliMac > 0 ? (
                  <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
                    Kapanış favorisi (vurgulu oran) bu haftanın {oranliMac} maçından{" "}
                    <span className="tnum font-medium text-foreground">{veri.odds_hit}</span>{" "}
                    tanesinde tuttu. Piyasa kapanış oranı — iddaa oranı değildir.
                  </p>
                ) : null}
                <code className="tnum mt-4 block break-all rounded-lg bg-muted px-3 py-2 font-mono text-[12.5px]">
                  {veri.results}
                </code>
              </CardBody>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader title="Sürprizler" hint="Sezonda en nadir görülen tercihler." />
                <CardBody>
                  <ul className="space-y-2.5 text-[12.5px]">
                    {surprizler.map((s) => {
                      const mac = veri.matches?.[s.pos - 1];
                      return (
                        <li key={s.pos} className="flex items-start gap-2">
                          <span
                            className={cn(
                              "grid h-6 w-6 shrink-0 place-items-center rounded-md font-mono text-[12px] font-bold text-white",
                              SYM_BG[s.symbol],
                            )}
                          >
                            {s.symbol}
                          </span>
                          <span className="min-w-0">
                            {mac ? (
                              <span className="block truncate">
                                {mac.home} – {mac.away}
                              </span>
                            ) : null}
                            <span className="tnum block text-[11.5px] text-muted-foreground">
                              {s.pos}. maç · sezonda %{s.pct.toFixed(0)}
                            </span>
                          </span>
                        </li>
                      );
                    })}
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
