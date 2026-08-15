"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getStats, type StatsResponse } from "@/lib/api";
import {
  BandStrips, DistributionChart, PositionHeatmap, ShareBar, TransitionMatrix, TrendChart,
} from "@/components/stats/charts";
import {
  Card, DataQualityPanel, Legend, RangeFilter, StatTile,
} from "@/components/stats/primitives";
import { WeeksTable } from "@/components/stats/WeeksTable";
import { SYMS, SYM_LABEL, fmt1 } from "@/components/stats/tokens";

const RANGES = [
  { value: null as number | null, label: "Tüm sezon" },
  { value: 24, label: "Son 24" },
  { value: 12, label: "Son 12" },
  { value: 6, label: "Son 6" },
];

export default function StatsPage() {
  const [last, setLast] = useState<number | null>(null);
  const [data, setData] = useState<StatsResponse | null>(null);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setBusy(true);
    getStats(last)
      .then((d) => { if (alive) { setData(d); setErr(null); } })
      .catch((e) => { if (alive) setErr(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [last]);

  if (err) {
    return (
      <div className="max-w-2xl space-y-3">
        <h1 className="text-2xl font-semibold tracking-tight">Tarihsel 1 / 0 / 2</h1>
        <p className="text-[13px] text-red-600 bg-red-50 rounded-xl p-4">{err}</p>
        <button type="button" className="btn-ghost" onClick={() => setLast((v) => (v === null ? null : v))}>
          Tekrar dene
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-4" aria-busy>
        <div className="h-8 w-64 rounded-xl bg-black/5" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => <div key={i} className="h-28 rounded-2xl bg-black/5" />)}
        </div>
        <div className="h-72 rounded-2xl bg-black/5" />
      </div>
    );
  }

  const { meta, totals, weekly_avg, bands, analytics, weeks, data_quality } = data;
  const pct = { "1": totals.pct_1, "0": totals.pct_0, "2": totals.pct_2 } as const;
  const lider = SYMS.reduce((a, b) => (totals[a] >= totals[b] ? a : b));
  const rec = analytics.recent;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tarihsel 1 / 0 / 2</h1>
          <p className="text-[13px] text-[var(--muted)] mt-1">
            {meta.season} · {meta.weeks} hafta ({meta.week_from}–{meta.week_to}) · {meta.matches} maç
            {meta.date_from && <> · {meta.date_from} → {meta.date_to}</>}
          </p>
        </div>
        <RangeFilter value={last} onChange={setLast} options={RANGES} busy={busy} />
      </header>

      <div className={`space-y-5 transition-opacity ${busy ? "opacity-60" : "opacity-100"}`}>
        <Card>
          <div className="grid gap-6 lg:grid-cols-[minmax(0,260px)_minmax(0,1fr)] lg:items-center">
            <div>
              <div className="text-[12px] text-[var(--muted)]">En sık sonuç</div>
              <div className="text-[56px] leading-none font-semibold tracking-tight mt-1">
                {lider}
              </div>
              <div className="text-[13px] text-[var(--muted)] mt-2">
                {SYM_LABEL[lider]} · maçların %{fmt1(pct[lider])}’i ·
                haftada ort. {fmt1(weekly_avg[lider])} maç
              </div>
            </div>
            <div>
              <ShareBar totals={totals} matches={meta.matches} />
            </div>
          </div>
        </Card>

        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {SYMS.map((s) => (
            <StatTile
              key={s}
              accent={s}
              label={SYM_LABEL[s]}
              value={String(totals[s])}
              sub={`%${fmt1(pct[s])} · haftada ort. ${fmt1(weekly_avg[s])}`}
              delta={rec.delta[s]}
              deltaNote={`son ${rec.window} haftada (ort. ${fmt1(rec.avg[s])})`}
            />
          ))}
          <StatTile
            label="Hafta içi en uzun seri"
            value={`${fmt1(analytics.streaks.avg_week_max)}`}
            sub="ortalama; aynı sembolün arka arkaya tekrarı"
          />
        </section>

        <Card
          title="Haftalık seyir"
          hint="Dikey eksen o haftaki maç sayısı, yatay eksen hafta numarası. Eksik veri nedeniyle dışarıda kalan haftalar eksende yer almaz. Fare ile bir haftanın üzerine gelin."
          right={<Legend />}
        >
          <TrendChart weeks={weeks} />
        </Card>

        <div className="grid gap-5 lg:grid-cols-2">
          <Card
            title="Bantlar"
            hint="Yatay eksen bir haftadaki adet (0–15). Açık şerit en az–en çok aralığı, koyu şerit ±1 standart sapma, beyaz çizgi ortanca, nokta ortalama."
          >
            <BandStrips bands={bands} />
            <ul className="mt-3 space-y-1 text-[12px] text-[var(--muted)] tabular-nums">
              {SYMS.map((s) => (
                <li key={s}>
                  <span className="text-[var(--ink)] font-medium">{s}</span> · ortalama üstü{" "}
                  {bands[s].above_n} hafta (ort. {fmt1(bands[s].above_mean)}), altı {bands[s].below_n} hafta
                  (ort. {fmt1(bands[s].below_mean)}) · σ = {fmt1(bands[s].std)}
                </li>
              ))}
            </ul>
          </Card>

          <Card
            title="Haftalık adet dağılımı"
            hint="Yatay eksen bir haftada çıkan adet, dikey eksen o adedin görüldüğü hafta sayısı."
            right={<Legend compact />}
          >
            <DistributionChart distribution={analytics.distribution} weekCount={meta.weeks} />
          </Card>
        </div>

        <Card
          title="Maç sırasına göre dağılım"
          hint="Kuponun 1.–15. sırasındaki maçlarda sembollerin çıkma yüzdesi. Koyu hücre = daha sık."
        >
          <PositionHeatmap positions={analytics.positions} />
        </Card>

        <div className="grid gap-5 lg:grid-cols-2">
          <Card
            title="Geçiş matrisi"
            hint={`Bir maçın sonucundan sonra bir sonraki maçta ne çıktı (${analytics.transitions.n} ardışık çift). Aynı sembolün tekrarı: %${analytics.transitions.repeat_pct.toFixed(0)}.`}
          >
            <TransitionMatrix transitions={analytics.transitions} />
          </Card>

          <Card title="Uçlar ve seriler" hint="Sezonun sınır haftaları ve en uzun aynı-sembol serileri.">
            <div className="grid sm:grid-cols-2 gap-5 text-[13px]">
              <div>
                <div className="text-[12px] text-[var(--muted)] mb-2">En yüksek / en düşük hafta</div>
                <ul className="space-y-1.5 tabular-nums">
                  {SYMS.map((s) => {
                    const e = analytics.extremes[s];
                    return (
                      <li key={s} className="flex items-center gap-2">
                        <span className="font-medium w-3">{s}</span>
                        <span className="text-[var(--muted)]">
                          en çok {e.max?.value} →{" "}
                          <Link className="text-[var(--brand)] hover:underline" href={`/stats/${e.max?.week}`}>
                            {e.max?.week}. hf
                          </Link>{" "}
                          · en az {e.min?.value} →{" "}
                          <Link className="text-[var(--brand)] hover:underline" href={`/stats/${e.min?.week}`}>
                            {e.min?.week}. hf
                          </Link>
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
              <div>
                <div className="text-[12px] text-[var(--muted)] mb-2">En uzun seriler</div>
                <ul className="space-y-1.5 tabular-nums">
                  {analytics.streaks.top.slice(0, 5).map((r, i) => (
                    <li key={`${r.week}-${r.start}-${i}`} className="text-[var(--muted)]">
                      <span className="text-[var(--ink)] font-medium">{r.length}× {r.symbol}</span>{" "}
                      ·{" "}
                      <Link className="text-[var(--brand)] hover:underline" href={`/stats/${r.week}`}>
                        {r.week}. hf
                      </Link>{" "}
                      · {r.start}. maçtan itibaren
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>
        </div>

        <Card
          title="Haftalar"
          hint="Başlıklara tıklayarak sıralayın; hafta numarasından detay sayfasına gidin."
          right={<Legend compact />}
        >
          <WeeksTable weeks={weeks} avg={weekly_avg} />
        </Card>

        <Card title="Veri kalitesi" hint={meta.source}>
          <DataQualityPanel dq={data_quality} />
        </Card>
      </div>
    </div>
  );
}
