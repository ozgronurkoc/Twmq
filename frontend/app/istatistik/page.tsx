"use client";

import * as React from "react";
import Link from "next/link";

import { getStats } from "@/lib/api";
import { useIstek } from "@/lib/istek";
import {
  SEMBOLLER,
  type Sembol,
  type StatsResponse,
} from "@/lib/types";
import { cn, ondalik, sayi } from "@/lib/utils";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  SectionTitle,
  Skeleton,
} from "@/components/ui/primitives";
import { SEMBOL_ADI, SymbolLegend } from "@/components/ui/symbol";
import {
  BandStrips,
  DistributionChart,
  PositionHeatmap,
  ShareBar,
  TransitionMatrix,
  TrendChart,
} from "@/components/istatistik/charts";
import {
  DataQualityPanel,
  DeltaStat,
  RangeFilter,
  SliceNote,
  aralikUrldenOku,
  aralikUrleYaz,
} from "@/components/istatistik/parts";
import { WeeksTable } from "@/components/istatistik/weeks-table";
import { IstatistikSekmeleri } from "@/components/istatistik/sekmeler";
import { SYM_BG } from "@/components/istatistik/viz";

const ARALIKLAR: Array<{ deger: number | null; etiket: string }> = [
  { deger: null, etiket: "Tüm sezon" },
  { deger: 24, etiket: "Son 24" },
  { deger: 12, etiket: "Son 12" },
  { deger: 6, etiket: "Son 6" },
];

export default function IstatistikPage() {
  const [last, setLast] = React.useState<number | null>(null);
  // Adresteki `?last=` okunana kadar istek atmiyoruz; aksi halde
  // paylasilan bir baglanti once tum sezonu cekip sonra dilime donerdi.
  const [urlOkundu, setUrlOkundu] = React.useState(false);

  React.useEffect(() => {
    setLast(aralikUrldenOku());
    setUrlOkundu(true);
  }, []);

  /** Filtre secimi hem state'e hem adres cubuguna yazilir. */
  function aralikSec(v: number | null) {
    setLast(v);
    aralikUrleYaz(v);
  }

  const {
    veri,
    hata,
    yukleniyor: mesgul,
  } = useIstek((signal) => getStats(last, signal), [last], {
    hazir: urlOkundu,
    varsayilanHata: "İstatistik alınamadı",
  });

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

  const { meta, analytics, data_quality: dq } = veri;
  const totals = veri.totals as Record<string, number>;
  const bands = veri.bands as Record<Sembol, NonNullable<StatsResponse["bands"]["1"]>>;
  const weeklyAvg = veri.weekly_avg;
  const pct: Record<Sembol, number> = {
    "1": totals.pct_1 ?? 0,
    "0": totals.pct_0 ?? 0,
    "2": totals.pct_2 ?? 0,
  };
  const adet: Record<Sembol, number> = {
    "1": totals["1"] ?? 0,
    "0": totals["0"] ?? 0,
    "2": totals["2"] ?? 0,
  };
  const lider = SEMBOLLER.reduce((a, b) => (adet[a] >= adet[b] ? a : b));
  const son = analytics.recent;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-[30px] italic leading-tight">Tarihsel 1 / 0 / 2</h1>
        <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
          Geçmiş sezon sonuçlarının dağılımı. Bu veri bir tahmin değildir ve formül üretimine
          girmez — yalnızca kendi olasılık tahminlerini kalibre etmen için referanstır.
          Piyasanın karnesi <strong>Oranlar</strong>, stratejinin karnesi{" "}
          <strong>Geri test</strong> sekmesinde.
        </p>
        <div className="mt-4">
          <IstatistikSekmeleri last={last} />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {meta.season ? <Badge ton="primary">{meta.season}</Badge> : null}
          <Badge>
            {sayi(meta.weeks)} hafta
            {meta.week_from ? ` (${meta.week_from}–${meta.week_to})` : ""}
          </Badge>
          <Badge>{sayi(meta.matches)} maç</Badge>
          {meta.date_from ? (
            <Badge>
              {meta.date_from} → {meta.date_to}
            </Badge>
          ) : null}
          {meta.sliced ? <Badge ton="warning">dilim</Badge> : null}
        </div>
        <div className="mt-4">
          <RangeFilter deger={last} onChange={aralikSec} secenekler={ARALIKLAR} mesgul={mesgul} />
          <SliceNote
            weeks={veri.weeks.map((w) => w.week)}
            matches={meta.matches ?? 0}
            sliced={Boolean(meta.sliced)}
          />
        </div>
      </header>

      {veri.error ? (
        <Callout ton="warning" baslik="Veri uyarısı">
          {veri.error}
        </Callout>
      ) : null}

      <div className={cn("space-y-6 transition-opacity duration-200", mesgul && "opacity-60")}>
        {/* Sezon payi */}
        <Card>
          <CardHeader title="Sezon dağılımı" hint={meta.rule} action={<SymbolLegend />} />
          <CardBody>
            <div className="grid gap-6 lg:grid-cols-[minmax(0,240px)_minmax(0,1fr)] lg:items-center">
              <div>
                <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                  En sık sonuç
                </div>
                <div className="mt-1 flex items-baseline gap-3">
                  <span
                    className={cn(
                      "tnum grid h-12 w-12 place-items-center rounded-xl font-mono text-[24px] font-bold text-white",
                      SYM_BG[lider],
                    )}
                  >
                    {lider}
                  </span>
                  <span className="tnum text-[40px] font-semibold leading-none">
                    %{ondalik(pct[lider], 1)}
                  </span>
                </div>
                <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">
                  {SEMBOL_ADI[lider]} · haftada ortalama {ondalik(weeklyAvg[lider] ?? 0, 1)} maç
                </p>
              </div>
              <ShareBar pct={pct} totals={adet} matches={meta.matches ?? 0} />
            </div>
          </CardBody>
        </Card>

        {/* Sayilar */}
        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {SEMBOLLER.map((s) => (
            <DeltaStat
              key={s}
              rozet={s}
              rozetSinif={SYM_BG[s]}
              etiket={SEMBOL_ADI[s]}
              deger={sayi(adet[s])}
              alt={`%${ondalik(pct[s], 1)} · haftada ort. ${ondalik(weeklyAvg[s] ?? 0, 1)}`}
              delta={son.delta[s]}
              deltaNot={`son ${son.window} haftada (ort. ${ondalik(son.avg[s], 1)})`}
            />
          ))}
          <DeltaStat
            etiket="Hafta içi en uzun seri"
            deger={ondalik(analytics.streaks.avg_week_max, 1)}
            alt="ortalama; aynı sembolün arka arkaya tekrarı"
          />
        </section>

        {/* Haftalik seyir */}
        <Card>
          <CardHeader
            title="Haftalık seyir"
            hint="Dikey eksen o haftaki maç sayısı, yatay eksen hafta numarası. Eksik veri nedeniyle dışarıda kalan haftalar eksende yer almaz."
            action={<SymbolLegend />}
          />
          <CardBody>
            <TrendChart weeks={veri.weeks} />
          </CardBody>
        </Card>

        <div className="grid gap-6 xl:grid-cols-2">
          {/* Bantlar */}
          <Card>
            <CardHeader
              title="Haftalık bantlar"
              hint="Yatay eksen bir haftadaki adet (0–15). Açık şerit en az–en çok aralığı, koyu şerit ±1 standart sapma, ince çizgi ortanca, nokta ortalama."
            />
            <CardBody>
              <BandStrips bands={bands} />
              <ul className="tnum mt-3 space-y-1 text-[11.5px] text-muted-foreground">
                {SEMBOLLER.map((s) => {
                  const b = bands[s];
                  if (!b) return null;
                  return (
                    <li key={s}>
                      <span className="font-medium text-foreground">{s}</span> · ortalama üstü{" "}
                      {b.above_n} hafta (ort. {ondalik(b.above_mean, 1)}), altı {b.below_n} hafta
                      (ort. {ondalik(b.below_mean, 1)}) · σ = {ondalik(b.std, 2)}
                    </li>
                  );
                })}
              </ul>
            </CardBody>
          </Card>

          {/* Dagilim */}
          <Card>
            <CardHeader
              title="Haftalık adet dağılımı"
              hint="Yatay eksen bir haftada çıkan adet, dikey eksen o adedin görüldüğü hafta sayısı."
              action={<SymbolLegend />}
            />
            <CardBody>
              <DistributionChart
                distribution={analytics.distribution}
                weekCount={meta.weeks ?? 0}
              />
            </CardBody>
          </Card>
        </div>

        {/* Mac sirasi */}
        <Card>
          <CardHeader
            title="Maç sırasına göre dağılım"
            hint="Kuponun 1.–15. sırasındaki maçlarda sembollerin çıkma yüzdesi. Koyu hücre = daha sık."
          />
          <CardBody>
            <PositionHeatmap positions={analytics.positions} />
          </CardBody>
        </Card>

        <div className="grid gap-6 xl:grid-cols-2">
          {/* Gecis matrisi */}
          <Card>
            <CardHeader
              title="Geçiş matrisi"
              hint={`Bir maçın sonucundan sonra bir sonraki maçta ne çıktı (${analytics.transitions.n} ardışık çift). Aynı sembolün tekrarı: %${analytics.transitions.repeat_pct.toFixed(0)}.`}
            />
            <CardBody>
              <TransitionMatrix transitions={analytics.transitions} />
            </CardBody>
          </Card>

          {/* Uclar ve seriler */}
          <Card>
            <CardHeader
              title="Uçlar ve seriler"
              hint="Sezonun sınır haftaları ve en uzun aynı-sembol serileri."
            />
            <CardBody className="grid gap-5 sm:grid-cols-2">
              <div>
                <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                  En yüksek / en düşük hafta
                </div>
                <ul className="tnum space-y-1.5 text-[12.5px]">
                  {SEMBOLLER.map((s) => {
                    const e = analytics.extremes[s];
                    // `max`/`min` null olabilir (bkz. types.ts:Analytics).
                    // Once yalnizca degere `?.` konmustu: uc null oldugunda
                    // metin "undefined. hf" yaziyor ve baglanti
                    // /istatistik/undefined adresine gidiyordu.
                    const uc = (u: typeof e.max, etiket: string) =>
                      u ? (
                        <>
                          {etiket} {u.value} →{" "}
                          <Link
                            className="text-primary hover:underline"
                            href={`/istatistik/${u.week}`}
                          >
                            {u.week}. hf
                          </Link>
                        </>
                      ) : (
                        <>{etiket} —</>
                      );
                    return (
                      <li key={s} className="flex items-center gap-2">
                        <span className="w-3 font-medium">{s}</span>
                        <span className="text-muted-foreground">
                          {uc(e.max, "en çok")} · {uc(e.min, "en az")}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
              <div>
                <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                  En uzun seriler
                </div>
                <ul className="tnum space-y-1.5 text-[12.5px] text-muted-foreground">
                  {analytics.streaks.top.slice(0, 5).map((r, i) => (
                    <li key={`${r.week}-${r.start}-${i}`}>
                      <span className="font-medium text-foreground">
                        {r.length}× {r.symbol}
                      </span>{" "}
                      ·{" "}
                      <Link className="text-primary hover:underline" href={`/istatistik/${r.week}`}>
                        {r.week}. hf
                      </Link>{" "}
                      · {r.start}. maçtan itibaren
                    </li>
                  ))}
                </ul>
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Haftalar */}
        <Card>
          <CardHeader
            title={`Haftalar (${veri.weeks.length})`}
            hint="Başlıklara tıklayarak sıralayın; hafta numarasından detay sayfasına gidin."
            action={<SymbolLegend />}
          />
          <CardBody>
            <WeeksTable
              weeks={veri.weeks}
              avg={weeklyAvg}
              brier={veri.odds?.weekly_brier}
              brierAvg={veri.odds?.brier_avg}
            />
          </CardBody>
        </Card>

        {/* Veri kalitesi */}
        <Card>
          <CardHeader title="Veri kalitesi" hint={meta.source} />
          <CardBody>
            <DataQualityPanel dq={dq} />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
