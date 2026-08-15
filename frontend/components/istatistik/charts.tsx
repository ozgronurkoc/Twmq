"use client";

import * as React from "react";

import { SEMBOLLER, type Analytics, type Band, type Sembol, type WeekRow } from "@/lib/types";
import { cn, ondalik } from "@/lib/utils";
import { SEMBOL_ADI } from "@/components/ui/symbol";
import { SYM_BG, SYM_FILL, SYM_STROKE, barPath, seqFill, seqInk } from "./viz";

/* ── ortak ──────────────────────────────────────────────────────────────── */

type Fare = { px: number; py: number; oran: number; w: number } | null;

/**
 * SVG viewBox olceklendigi icin fare konumunu piksel olarak kabin
 * dikdortgeninden okuyoruz; boylece kart genisligi ne olursa olsun
 * ipucu dogru yerde durur.
 */
function useFare() {
  const [fare, setFare] = React.useState<Fare>(null);
  return {
    fare,
    olaylar: {
      onMouseMove: (e: React.MouseEvent<HTMLDivElement>) => {
        const r = e.currentTarget.getBoundingClientRect();
        const px = e.clientX - r.left;
        setFare({ px, py: e.clientY - r.top, oran: r.width ? px / r.width : 0, w: r.width });
      },
      onMouseLeave: () => setFare(null),
    },
  };
}

export function Tooltip({
  x,
  y,
  w,
  children,
}: {
  x: number;
  y: number;
  w: number;
  children: React.ReactNode;
}) {
  const kirpik = Math.min(Math.max(x, 76), Math.max(w - 76, 76));
  return (
    <div
      role="status"
      className={cn(
        "pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+10px)]",
        "whitespace-nowrap rounded-xl bg-foreground px-3 py-2 text-[12px] text-background shadow-card",
      )}
      style={{ left: kirpik, top: y }}
    >
      {children}
    </div>
  );
}

function TooltipSatir({ sym, etiket, deger }: { sym?: Sembol; etiket: string; deger: string }) {
  return (
    <div className="flex items-center gap-2">
      {sym ? <span className={cn("inline-block h-2 w-2 rounded-sm", SYM_BG[sym])} aria-hidden /> : null}
      <span className="opacity-70">{etiket}</span>
      <span className="tnum ml-auto font-medium">{deger}</span>
    </div>
  );
}

/* ── 1. Sezon payi — parca/butun ────────────────────────────────────────── */

export function ShareBar({
  pct,
  totals,
  matches,
}: {
  pct: Record<Sembol, number>;
  totals: Record<Sembol, number>;
  matches: number;
}) {
  return (
    <div>
      <div
        className="flex h-11 gap-[2px]"
        role="img"
        aria-label={SEMBOLLER.map((s) => `${SEMBOL_ADI[s]} %${ondalik(pct[s], 1)}`).join(", ")}
      >
        {SEMBOLLER.map((s, i) => (
          <div
            key={s}
            className={cn(
              "flex items-center justify-center overflow-hidden text-[13px] font-semibold text-white",
              SYM_BG[s],
              i === 0 && "rounded-l-lg",
              i === SEMBOLLER.length - 1 && "rounded-r-lg",
            )}
            style={{ flexGrow: Math.max(pct[s], 0.001), flexBasis: 0 }}
          >
            {pct[s] >= 8 ? `${s} · %${ondalik(pct[s], 1)}` : ""}
          </div>
        ))}
      </div>
      <div className="tnum mt-2 text-[11.5px] text-muted-foreground">
        {matches} maç · {SEMBOLLER.map((s) => `${totals[s]} × ${s}`).join(" · ")}
      </div>
    </div>
  );
}

/* ── 2. Haftalik seyir ──────────────────────────────────────────────────── */

export function TrendChart({ weeks }: { weeks: WeekRow[] }) {
  const { fare, olaylar } = useFare();
  const W = 840;
  const H = 260;
  const solB = 30;
  const sagB = 44;
  const ustB = 14;
  const altB = 30;
  const n = weeks.length;

  const yMax = Math.max(4, ...weeks.flatMap((w) => SEMBOLLER.map((s) => w.counts[s])));
  const yTepe = Math.ceil(yMax / 2) * 2;
  const px = (i: number) => solB + (n <= 1 ? 0 : (i * (W - solB - sagB)) / (n - 1));
  const py = (v: number) => H - altB - (v / yTepe) * (H - ustB - altB);

  const yEksen = React.useMemo(() => {
    const adim = yTepe > 8 ? 3 : 2;
    const out: number[] = [];
    for (let v = 0; v <= yTepe; v += adim) out.push(v);
    return out;
  }, [yTepe]);

  const xEksen = React.useMemo(() => {
    if (!n) return [];
    const adim = Math.max(1, Math.round(n / Math.min(8, n)));
    const idx: number[] = [];
    for (let i = 0; i < n; i += adim) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const vurgu =
    fare && n
      ? Math.min(n - 1, Math.max(0, Math.round(((fare.oran * W - solB) / (W - solB - sagB)) * (n - 1))))
      : null;

  // Uc etiketleri yalnizca cakismiyorsa yazilir; ust uste binen etiket
  // cizgisinden kopar ve gurultu olur — o durumda efsane + ipucu tasir.
  const ucEtiket = React.useMemo(() => {
    if (!n) return [] as Array<{ sym: Sembol; y: number }>;
    const items = SEMBOLLER.map((s) => ({ sym: s, y: py(weeks[n - 1].counts[s]) })).sort(
      (a, b) => a.y - b.y,
    );
    return items.every((it, i) => i === 0 || it.y - items[i - 1].y >= 14) ? items : [];
  }, [weeks, n, yTepe]);

  if (!n) return <p className="text-[13px] text-muted-foreground">Hafta yok.</p>;

  return (
    <div className="relative" {...olaylar}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label={`${weeks[0].week}–${weeks[n - 1].week}. haftalar arasi haftalik 1/0/2 sayilari`}
      >
        {yEksen.map((v) => (
          <g key={v}>
            <line x1={solB} x2={W - sagB} y1={py(v)} y2={py(v)} className="stroke-line" strokeWidth={1} />
            <text
              x={solB - 8}
              y={py(v) + 4}
              textAnchor="end"
              fontSize={11}
              className="tnum fill-muted-foreground"
            >
              {v}
            </text>
          </g>
        ))}
        {xEksen.map((i) => (
          <text
            key={i}
            x={px(i)}
            y={H - altB + 18}
            textAnchor="middle"
            fontSize={11}
            className="tnum fill-muted-foreground"
          >
            {weeks[i].week}
          </text>
        ))}

        {vurgu !== null ? (
          <line
            x1={px(vurgu)}
            x2={px(vurgu)}
            y1={ustB}
            y2={H - altB}
            className="stroke-line-strong"
            strokeWidth={1}
          />
        ) : null}

        {SEMBOLLER.map((s) => (
          <path
            key={s}
            d={weeks.map((w, i) => `${i ? "L" : "M"}${px(i)},${py(w.counts[s])}`).join(" ")}
            fill="none"
            className={SYM_STROKE[s]}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {SEMBOLLER.map((s) => (
          <circle
            key={s}
            cx={px(n - 1)}
            cy={py(weeks[n - 1].counts[s])}
            r={4}
            className={cn(SYM_FILL[s], "stroke-card")}
            strokeWidth={2}
          />
        ))}
        {ucEtiket.map((it) => (
          <text key={it.sym} x={px(n - 1) + 10} y={it.y + 4} fontSize={11} className="fill-foreground">
            {it.sym}
          </text>
        ))}

        {vurgu !== null
          ? SEMBOLLER.map((s) => (
              <circle
                key={s}
                cx={px(vurgu)}
                cy={py(weeks[vurgu].counts[s])}
                r={4.5}
                className={cn(SYM_FILL[s], "stroke-card")}
                strokeWidth={2}
              />
            ))
          : null}
      </svg>

      {fare && vurgu !== null ? (
        <Tooltip x={(px(vurgu) / W) * fare.w} y={fare.py} w={fare.w}>
          <div className="mb-1 font-semibold">{weeks[vurgu].week}. hafta</div>
          <div className="min-w-[128px] space-y-0.5">
            {SEMBOLLER.map((s) => (
              <TooltipSatir key={s} sym={s} etiket={s} deger={String(weeks[vurgu].counts[s])} />
            ))}
          </div>
          <div className="mt-1 opacity-60">{weeks[vurgu].close_date}</div>
        </Tooltip>
      ) : null}
    </div>
  );
}

/* ── 3. Haftalik adet dagilimi ──────────────────────────────────────────── */

export function DistributionChart({
  distribution,
  weekCount,
}: {
  distribution: Analytics["distribution"];
  weekCount: number;
}) {
  const { fare, olaylar } = useFare();
  const kovalar = distribution["1"].map((b) => b.count);
  const W = 840;
  const H = 240;
  const solB = 30;
  const sagB = 12;
  const ustB = 14;
  const altB = 34;
  const yMax = Math.max(1, ...SEMBOLLER.flatMap((s) => distribution[s].map((b) => b.weeks)));
  const yTepe = Math.ceil(yMax / 2) * 2;
  const bant = (W - solB - sagB) / Math.max(1, kovalar.length);
  const kalinlik = Math.min(20, (bant - 8) / 3 - 2);
  const py = (v: number) => H - altB - (v / yTepe) * (H - ustB - altB);
  const grupX = (i: number) => solB + i * bant;

  const vurgu = fare
    ? Math.min(kovalar.length - 1, Math.max(0, Math.floor((fare.oran * W - solB) / bant)))
    : null;
  const yEksen = Array.from(new Set([0, Math.round(yTepe / 2), yTepe]));

  return (
    <div className="relative" {...olaylar}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label="Bir haftada cikan sembol adedine gore hafta sayisi dagilimi"
      >
        {yEksen.map((v) => (
          <g key={v}>
            <line x1={solB} x2={W - sagB} y1={py(v)} y2={py(v)} className="stroke-line" strokeWidth={1} />
            <text
              x={solB - 8}
              y={py(v) + 4}
              textAnchor="end"
              fontSize={11}
              className="tnum fill-muted-foreground"
            >
              {v}
            </text>
          </g>
        ))}
        {kovalar.map((k, i) => (
          <g key={k}>
            {vurgu === i ? (
              <rect
                x={grupX(i)}
                y={ustB}
                width={bant}
                height={H - ustB - altB}
                className="fill-muted"
              />
            ) : null}
            {SEMBOLLER.map((s, j) => {
              const v = distribution[s][i].weeks;
              const x = grupX(i) + (bant - (kalinlik * 3 + 4)) / 2 + j * (kalinlik + 2);
              const h = (v / yTepe) * (H - ustB - altB);
              return <path key={s} d={barPath(x, py(v), kalinlik, h)} className={SYM_FILL[s]} />;
            })}
            <text
              x={grupX(i) + bant / 2}
              y={H - altB + 18}
              textAnchor="middle"
              fontSize={11}
              className="tnum fill-muted-foreground"
            >
              {k}
            </text>
          </g>
        ))}
        <line x1={solB} x2={W - sagB} y1={py(0)} y2={py(0)} className="stroke-line-strong" strokeWidth={1} />
      </svg>
      {fare && vurgu !== null ? (
        <Tooltip x={((grupX(vurgu) + bant / 2) / W) * fare.w} y={fare.py} w={fare.w}>
          <div className="mb-1 font-semibold">Haftada {kovalar[vurgu]} adet</div>
          <div className="min-w-[150px] space-y-0.5">
            {SEMBOLLER.map((s) => (
              <TooltipSatir
                key={s}
                sym={s}
                etiket={s}
                deger={`${distribution[s][vurgu].weeks} hafta · %${distribution[s][vurgu].pct.toFixed(0)}`}
              />
            ))}
          </div>
          <div className="mt-1 opacity-60">{weekCount} hafta içinden</div>
        </Tooltip>
      ) : null}
    </div>
  );
}

/* ── 4. Bant seridi ─────────────────────────────────────────────────────── */

export function BandStrips({ bands }: { bands: Record<Sembol, Band> }) {
  const W = 840;
  const satirY = 62;
  const solB = 52;
  const sagB = 44;
  const H = satirY * SEMBOLLER.length + 26;
  const xmax = 15;
  const x = (v: number) => solB + (v / xmax) * (W - solB - sagB);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-auto w-full"
      role="img"
      aria-label="Her sembol icin haftalik adet araligi: en az, ±1 standart sapma, ortanca, ortalama, en cok"
    >
      {[0, 3, 6, 9, 12, 15].map((v) => (
        <g key={v}>
          <line
            x1={x(v)}
            x2={x(v)}
            y1={10}
            y2={satirY * SEMBOLLER.length}
            className="stroke-line"
            strokeWidth={1}
          />
          <text
            x={x(v)}
            y={H - 6}
            textAnchor="middle"
            fontSize={11}
            className="tnum fill-muted-foreground"
          >
            {v}
          </text>
        </g>
      ))}
      {SEMBOLLER.map((s, i) => {
        const b = bands[s];
        if (!b) return null;
        const cy = 24 + i * satirY;
        const alt = Math.max(0, b.avg - b.std);
        const ust = Math.min(xmax, b.avg + b.std);
        return (
          <g key={s}>
            <line
              x1={x(b.min)}
              x2={x(b.max)}
              y1={cy}
              y2={cy}
              className={SYM_STROKE[s]}
              strokeOpacity={0.28}
              strokeWidth={4}
              strokeLinecap="round"
            />
            <line
              x1={x(alt)}
              x2={x(ust)}
              y1={cy}
              y2={cy}
              className={SYM_STROKE[s]}
              strokeOpacity={0.58}
              strokeWidth={12}
              strokeLinecap="round"
            />
            <line
              x1={x(b.median)}
              x2={x(b.median)}
              y1={cy - 9}
              y2={cy + 9}
              className="stroke-card"
              strokeWidth={2}
            />
            <circle cx={x(b.avg)} cy={cy} r={5} className={cn(SYM_FILL[s], "stroke-card")} strokeWidth={2} />
            <text
              x={x(b.min) - 10}
              y={cy + 4}
              textAnchor="end"
              fontSize={11}
              className="tnum fill-muted-foreground"
            >
              {b.min}
            </text>
            <text
              x={x(b.max) + 10}
              y={cy + 4}
              textAnchor="start"
              fontSize={11}
              className="tnum fill-muted-foreground"
            >
              {b.max}
            </text>
            <text x={x(b.avg)} y={cy + 26} textAnchor="middle" fontSize={11} className="tnum fill-foreground">
              ort. {ondalik(b.avg, 1)}
            </text>
            <text x={4} y={cy + 4} fontSize={13} fontWeight={600} className="fill-foreground">
              {s}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ── 5. Mac sirasi isi haritasi ─────────────────────────────────────────── */

export function PositionHeatmap({ positions }: { positions: Analytics["positions"] }) {
  const [hucre, setHucre] = React.useState<
    { pos: number; sym: Sembol; x: number; y: number; w: number } | null
  >(null);
  const enBuyuk = Math.max(1, ...positions.flatMap((p) => SEMBOLLER.map((s) => p.pct[s])));

  return (
    <div className="scroll-slim relative overflow-x-auto" onMouseLeave={() => setHucre(null)}>
      <table className="w-full min-w-[640px] border-separate" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="w-8" />
            {positions.map((p) => (
              <th key={p.pos} className="tnum pb-1 text-[11px] font-medium text-muted-foreground">
                {p.pos}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SEMBOLLER.map((s) => (
            <tr key={s}>
              <th scope="row" className="pr-1 text-left align-middle">
                <span className="flex items-center gap-1.5 text-[12px] font-medium">
                  <span className={cn("inline-block h-2.5 w-2.5 rounded-sm", SYM_BG[s])} aria-hidden />
                  {s}
                </span>
              </th>
              {positions.map((p) => {
                const t = p.pct[s] / enBuyuk;
                return (
                  <td
                    key={p.pos}
                    className="tnum h-9 cursor-default rounded-md text-center text-[11px]"
                    style={{ background: seqFill(t), color: seqInk(t) }}
                    onMouseMove={(e) => {
                      const kap = e.currentTarget.closest("div");
                      const r = kap?.getBoundingClientRect();
                      const c = e.currentTarget.getBoundingClientRect();
                      if (!r) return;
                      setHucre({
                        pos: p.pos,
                        sym: s,
                        x: c.left - r.left + c.width / 2,
                        y: c.top - r.top,
                        w: r.width,
                      });
                    }}
                  >
                    {Math.round(p.pct[s])}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-2 text-[11px] text-muted-foreground">
        <span>düşük</span>
        <span className="flex gap-[2px]" aria-hidden>
          {[0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1].map((t) => (
            <span key={t} className="h-2.5 w-5 rounded-[2px]" style={{ background: seqFill(t) }} />
          ))}
        </span>
        <span>yüksek · hücreler yüzde (%)</span>
      </div>
      {hucre ? (
        <Tooltip x={hucre.x} y={hucre.y} w={hucre.w}>
          <div className="mb-1 font-semibold">{hucre.pos}. maç</div>
          <TooltipSatir
            sym={hucre.sym}
            etiket={SEMBOL_ADI[hucre.sym]}
            deger={`%${positions[hucre.pos - 1].pct[hucre.sym].toFixed(0)} · ${
              positions[hucre.pos - 1].counts[hucre.sym]
            }/${positions[hucre.pos - 1].n}`}
          />
        </Tooltip>
      ) : null}
    </div>
  );
}

/* ── 6. Gecis matrisi ───────────────────────────────────────────────────── */

export function TransitionMatrix({ transitions }: { transitions: Analytics["transitions"] }) {
  const enBuyuk = Math.max(1, ...SEMBOLLER.flatMap((a) => SEMBOLLER.map((b) => transitions.pct[a][b])));
  return (
    <div className="scroll-slim overflow-x-auto">
      <table className="border-separate text-center" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="w-24" />
            {SEMBOLLER.map((b) => (
              <th key={b} className="w-20 pb-1 text-[11.5px] font-medium text-muted-foreground">
                sonraki {b}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SEMBOLLER.map((a) => (
            <tr key={a}>
              <th scope="row" className="whitespace-nowrap pr-2 text-right text-[12px] font-medium">
                <span className="inline-flex items-center gap-1.5">
                  <span className={cn("inline-block h-2.5 w-2.5 rounded-sm", SYM_BG[a])} aria-hidden />
                  {a} sonrası
                </span>
              </th>
              {SEMBOLLER.map((b) => {
                const t = transitions.pct[a][b] / enBuyuk;
                return (
                  <td
                    key={b}
                    className="h-14 w-20 rounded-lg align-middle"
                    style={{ background: seqFill(t), color: seqInk(t) }}
                    title={`${a} → ${b}: ${transitions.counts[a][b]} kez`}
                  >
                    <div className="tnum text-[15px] font-semibold">
                      %{transitions.pct[a][b].toFixed(0)}
                    </div>
                    <div className="tnum text-[10px] opacity-80">{transitions.counts[a][b]}</div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
