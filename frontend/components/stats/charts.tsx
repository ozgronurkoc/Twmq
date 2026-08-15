"use client";

import { useMemo, useState } from "react";
import type { Analytics, Band, Sym, SymMap, WeekRow } from "@/lib/api";
import { VizTooltip, TooltipRow } from "./primitives";
import { SEQ, SYMS, SYM_COLOR, SYM_LABEL, fmt1, seqColor, seqInk } from "./tokens";

/* ── ortak yardımcılar ────────────────────────────────────────────────────── */

type Mouse = { px: number; py: number; frac: number; w: number } | null;

function useMouse() {
  const [m, setM] = useState<Mouse>(null);
  return {
    m,
    handlers: {
      onMouseMove: (e: React.MouseEvent<HTMLDivElement>) => {
        const r = e.currentTarget.getBoundingClientRect();
        const px = e.clientX - r.left;
        setM({ px, py: e.clientY - r.top, frac: r.width ? px / r.width : 0, w: r.width });
      },
      onMouseLeave: () => setM(null),
    },
  };
}

/** Tepesi 4px yuvarlak, tabanı kare sütun. */
function barPath(x: number, y: number, w: number, h: number, r = 4): string {
  const rr = Math.max(0, Math.min(r, h, w / 2));
  if (h <= 0) return "";
  return `M${x},${y + h} L${x},${y + rr} Q${x},${y} ${x + rr},${y} L${x + w - rr},${y} Q${x + w},${y} ${x + w},${y + rr} L${x + w},${y + h} Z`;
}

/* ── 1. Sezon payı — parça/bütün ──────────────────────────────────────────── */

export function ShareBar({
  totals, matches,
}: {
  totals: SymMap<number> & { pct_1: number; pct_0: number; pct_2: number };
  matches: number;
}) {
  const pct: SymMap<number> = {
    "1": totals.pct_1, "0": totals.pct_0, "2": totals.pct_2,
  };
  return (
    <div>
      <div className="flex gap-[2px] h-11" role="img"
        aria-label={SYMS.map((s) => `${SYM_LABEL[s]} %${fmt1(pct[s])}`).join(", ")}>
        {SYMS.map((s, i) => (
          <div
            key={s}
            className={`flex items-center justify-center text-white text-[13px] font-semibold overflow-hidden
              ${i === 0 ? "rounded-l-lg" : ""} ${i === SYMS.length - 1 ? "rounded-r-lg" : ""}`}
            style={{ background: SYM_COLOR[s], flexGrow: Math.max(pct[s], 0.001), flexBasis: 0 }}
          >
            {pct[s] >= 8 ? `${s} · %${fmt1(pct[s])}` : ""}
          </div>
        ))}
      </div>
      <div className="mt-2 text-[12px] text-[var(--muted)] tabular-nums">
        {matches} maç · {SYMS.map((s) => `${totals[s]} × ${s}`).join(" · ")}
      </div>
    </div>
  );
}

/* ── 2. Haftalık seyir — çok serili çizgi ─────────────────────────────────── */

export function TrendChart({ weeks }: { weeks: WeekRow[] }) {
  const { m, handlers } = useMouse();
  const W = 840, H = 260;
  const padL = 30, padR = 44, padT = 14, padB = 30;
  const n = weeks.length;
  const yMax = Math.max(4, ...weeks.flatMap((w) => SYMS.map((s) => w.counts[s])));
  const yTop = Math.ceil(yMax / 2) * 2;
  const px = (i: number) => padL + (n <= 1 ? 0 : (i * (W - padL - padR)) / (n - 1));
  const py = (v: number) => H - padB - (v / yTop) * (H - padT - padB);

  const ticks = useMemo(() => {
    const step = yTop > 8 ? 3 : 2;
    const out: number[] = [];
    for (let v = 0; v <= yTop; v += step) out.push(v);
    return out;
  }, [yTop]);

  const xTicks = useMemo(() => {
    if (n === 0) return [];
    const want = Math.min(8, n);
    const step = Math.max(1, Math.round(n / want));
    const idx: number[] = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const hover = m && n > 0
    ? Math.min(n - 1, Math.max(0, Math.round(((m.frac * W - padL) / (W - padL - padR)) * (n - 1))))
    : null;

  // Uç etiketleri sadece çakışmıyorsa yazılır — üst üste binen etiket gürültüdür.
  const endLabels = useMemo(() => {
    if (!n) return [] as Array<{ sym: Sym; y: number }>;
    const items = SYMS.map((s) => ({ sym: s, y: py(weeks[n - 1].counts[s]) }))
      .sort((a, b) => a.y - b.y);
    const ok = items.every((it, i) => i === 0 || it.y - items[i - 1].y >= 14);
    return ok ? items : [];
  }, [weeks, n, yTop]);

  if (!n) return <p className="text-[13px] text-[var(--muted)]">Hafta yok.</p>;

  return (
    <div className="relative" {...handlers}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
        aria-label={`Hafta ${weeks[0].week}–${weeks[n - 1].week} arası haftalık 1/0/2 sayıları`}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={padL} x2={W - padR} y1={py(v)} y2={py(v)} stroke="var(--viz-grid)" strokeWidth={1} />
            <text x={padL - 8} y={py(v) + 4} textAnchor="end" fontSize={11} fill="var(--viz-mute)"
              style={{ fontVariantNumeric: "tabular-nums" }}>{v}</text>
          </g>
        ))}
        {xTicks.map((i) => (
          <text key={i} x={px(i)} y={H - padB + 18} textAnchor="middle" fontSize={11} fill="var(--viz-mute)"
            style={{ fontVariantNumeric: "tabular-nums" }}>{weeks[i].week}</text>
        ))}

        {hover !== null && (
          <line x1={px(hover)} x2={px(hover)} y1={padT} y2={H - padB}
            stroke="var(--viz-axis)" strokeWidth={1} />
        )}

        {SYMS.map((s) => (
          <path
            key={s}
            d={weeks.map((w, i) => `${i ? "L" : "M"}${px(i)},${py(w.counts[s])}`).join(" ")}
            fill="none" stroke={SYM_COLOR[s]} strokeWidth={2}
            strokeLinejoin="round" strokeLinecap="round"
          />
        ))}

        {SYMS.map((s) => (
          <circle key={s} cx={px(n - 1)} cy={py(weeks[n - 1].counts[s])} r={4}
            fill={SYM_COLOR[s]} stroke="var(--viz-surface)" strokeWidth={2} />
        ))}
        {endLabels.map((it) => (
          <text key={it.sym} x={px(n - 1) + 10} y={it.y + 4} fontSize={11} fill="var(--viz-ink)">
            {it.sym}
          </text>
        ))}

        {hover !== null && SYMS.map((s) => (
          <circle key={s} cx={px(hover)} cy={py(weeks[hover].counts[s])} r={4.5}
            fill={SYM_COLOR[s]} stroke="var(--viz-surface)" strokeWidth={2} />
        ))}
      </svg>

      {m && hover !== null && (
        <VizTooltip x={(px(hover) / W) * m.w} y={m.py} width={m.w}>
          <div className="font-semibold mb-1">{weeks[hover].week}. hafta</div>
          <div className="space-y-0.5 min-w-[128px]">
            {SYMS.map((s) => (
              <TooltipRow key={s} sym={s} label={s} value={String(weeks[hover].counts[s])} />
            ))}
          </div>
          <div className="text-white/60 mt-1">{weeks[hover].close_date}</div>
        </VizTooltip>
      )}
    </div>
  );
}

/* ── 3. Dağılım — gruplanmış sütun ────────────────────────────────────────── */

export function DistributionChart({
  distribution, weekCount,
}: {
  distribution: Analytics["distribution"]; weekCount: number;
}) {
  const { m, handlers } = useMouse();
  const bins = distribution["1"].map((b) => b.count);
  const W = 840, H = 240;
  const padL = 30, padR = 12, padT = 14, padB = 34;
  const yMax = Math.max(1, ...SYMS.flatMap((s) => distribution[s].map((b) => b.weeks)));
  const yTop = Math.ceil(yMax / 2) * 2;
  const band = (W - padL - padR) / Math.max(1, bins.length);
  const barW = Math.min(20, (band - 8) / 3 - 2);
  const py = (v: number) => H - padB - (v / yTop) * (H - padT - padB);
  const groupX = (i: number) => padL + i * band;

  const hover = m
    ? Math.min(bins.length - 1, Math.max(0, Math.floor((m.frac * W - padL) / band)))
    : null;
  const ticks = [0, Math.round(yTop / 2), yTop].filter((v, i, a) => a.indexOf(v) === i);

  return (
    <div className="relative" {...handlers}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
        aria-label="Bir haftada çıkan sembol adedine göre hafta sayısı dağılımı">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={padL} x2={W - padR} y1={py(v)} y2={py(v)} stroke="var(--viz-grid)" strokeWidth={1} />
            <text x={padL - 8} y={py(v) + 4} textAnchor="end" fontSize={11} fill="var(--viz-mute)"
              style={{ fontVariantNumeric: "tabular-nums" }}>{v}</text>
          </g>
        ))}
        {bins.map((k, i) => (
          <g key={k}>
            {hover === i && (
              <rect x={groupX(i)} y={padT} width={band} height={H - padT - padB} fill="var(--bg)" />
            )}
            {SYMS.map((s, j) => {
              const v = distribution[s][i].weeks;
              const x = groupX(i) + (band - (barW * 3 + 4)) / 2 + j * (barW + 2);
              const h = (v / yTop) * (H - padT - padB);
              return <path key={s} d={barPath(x, py(v), barW, h)} fill={SYM_COLOR[s]} />;
            })}
            <text x={groupX(i) + band / 2} y={H - padB + 18} textAnchor="middle" fontSize={11}
              fill="var(--viz-mute)" style={{ fontVariantNumeric: "tabular-nums" }}>{k}</text>
          </g>
        ))}
        <line x1={padL} x2={W - padR} y1={py(0)} y2={py(0)} stroke="var(--viz-axis)" strokeWidth={1} />
      </svg>
      {m && hover !== null && (
        <VizTooltip x={((groupX(hover) + band / 2) / W) * m.w} y={m.py} width={m.w}>
          <div className="font-semibold mb-1">Haftada {bins[hover]} adet</div>
          <div className="space-y-0.5 min-w-[150px]">
            {SYMS.map((s) => (
              <TooltipRow key={s} sym={s} label={s}
                value={`${distribution[s][hover].weeks} hafta · %${distribution[s][hover].pct.toFixed(0)}`} />
            ))}
          </div>
          <div className="text-white/60 mt-1">{weekCount} hafta içinden</div>
        </VizTooltip>
      )}
    </div>
  );
}

/* ── 4. Maç sırası ısı haritası ───────────────────────────────────────────── */

export function PositionHeatmap({ positions }: { positions: Analytics["positions"] }) {
  const [cell, setCell] = useState<{ pos: number; sym: Sym; x: number; y: number; w: number } | null>(null);
  const max = Math.max(1, ...positions.flatMap((p) => SYMS.map((s) => p.pct[s])));

  return (
    <div className="relative overflow-x-auto" onMouseLeave={() => setCell(null)}>
      <table className="w-full min-w-[640px] border-separate" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="w-8" />
            {positions.map((p) => (
              <th key={p.pos} className="text-[11px] font-medium text-[var(--viz-mute)] tabular-nums pb-1">
                {p.pos}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SYMS.map((s) => (
            <tr key={s}>
              <th scope="row" className="text-left align-middle pr-1">
                <span className="inline-flex items-center gap-1.5 text-[12px] font-medium">
                  <span className="h-2.5 w-2.5 rounded-sm inline-block" style={{ background: SYM_COLOR[s] }} aria-hidden />
                  {s}
                </span>
              </th>
              {positions.map((p) => {
                const t = p.pct[s] / max;
                return (
                  <td
                    key={p.pos}
                    className="h-9 rounded-md text-center text-[11px] tabular-nums cursor-default"
                    style={{ background: seqColor(t), color: seqInk(t) }}
                    onMouseMove={(e) => {
                      const host = e.currentTarget.closest("div");
                      const r = host?.getBoundingClientRect();
                      const c = e.currentTarget.getBoundingClientRect();
                      if (!r) return;
                      setCell({
                        pos: p.pos, sym: s,
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
      <div className="flex items-center gap-2 mt-3 text-[11px] text-[var(--viz-mute)]">
        <span>düşük</span>
        <span className="flex gap-[2px]" aria-hidden>
          {SEQ.map((c) => (
            <span key={c} className="h-2.5 w-5 rounded-[2px]" style={{ background: c }} />
          ))}
        </span>
        <span>yüksek · hücreler yüzde (%)</span>
      </div>
      {cell && (
        <VizTooltip x={cell.x} y={cell.y} width={cell.w}>
          <div className="font-semibold mb-1">{cell.pos}. maç</div>
          <TooltipRow
            sym={cell.sym}
            label={SYM_LABEL[cell.sym]}
            value={`%${positions[cell.pos - 1].pct[cell.sym].toFixed(0)} · ${positions[cell.pos - 1].counts[cell.sym]}/${positions[cell.pos - 1].n}`}
          />
        </VizTooltip>
      )}
    </div>
  );
}

/* ── 5. Geçiş matrisi ─────────────────────────────────────────────────────── */

export function TransitionMatrix({ transitions }: { transitions: Analytics["transitions"] }) {
  const max = Math.max(1, ...SYMS.flatMap((a) => SYMS.map((b) => transitions.pct[a][b])));
  return (
    <div className="overflow-x-auto">
      <table className="border-separate text-center" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="w-24" />
            {SYMS.map((b) => (
              <th key={b} className="w-20 text-[12px] font-medium text-[var(--muted)] pb-1">
                sonraki {b}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SYMS.map((a) => (
            <tr key={a}>
              <th scope="row" className="text-right pr-2 text-[12px] font-medium whitespace-nowrap">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm inline-block" style={{ background: SYM_COLOR[a] }} aria-hidden />
                  {a} sonrası
                </span>
              </th>
              {SYMS.map((b) => {
                const t = transitions.pct[a][b] / max;
                return (
                  <td key={b} className="h-14 w-20 rounded-lg align-middle"
                    style={{ background: seqColor(t), color: seqInk(t) }}
                    title={`${a} → ${b}: ${transitions.counts[a][b]} kez`}>
                    <div className="text-[15px] font-semibold tabular-nums">
                      %{transitions.pct[a][b].toFixed(0)}
                    </div>
                    <div className="text-[10px] opacity-80 tabular-nums">{transitions.counts[a][b]}</div>
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

/* ── 6. Bant şeridi — min · ±σ · ortalama · maks ──────────────────────────── */

export function BandStrips({ bands }: { bands: SymMap<Band> }) {
  const W = 840, rowH = 62, padL = 52, padR = 44;
  const H = rowH * SYMS.length + 26;
  const xmax = 15;
  const x = (v: number) => padL + (v / xmax) * (W - padL - padR);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
      aria-label="Her sembol için haftalık adet aralığı: en az, ±1 standart sapma, ortanca, ortalama, en çok">
      {[0, 3, 6, 9, 12, 15].map((v) => (
        <g key={v}>
          <line x1={x(v)} x2={x(v)} y1={10} y2={rowH * SYMS.length} stroke="var(--viz-grid)" strokeWidth={1} />
          <text x={x(v)} y={H - 6} textAnchor="middle" fontSize={11} fill="var(--viz-mute)"
            style={{ fontVariantNumeric: "tabular-nums" }}>{v}</text>
        </g>
      ))}
      {SYMS.map((s, i) => {
        const b = bands[s];
        const cy = 24 + i * rowH;
        const lo = Math.max(0, b.avg - b.std);
        const hi = Math.min(xmax, b.avg + b.std);
        return (
          <g key={s}>
            <line x1={x(b.min)} x2={x(b.max)} y1={cy} y2={cy}
              stroke={SYM_COLOR[s]} strokeOpacity={0.25} strokeWidth={4} strokeLinecap="round" />
            <line x1={x(lo)} x2={x(hi)} y1={cy} y2={cy}
              stroke={SYM_COLOR[s]} strokeOpacity={0.55} strokeWidth={12} strokeLinecap="round" />
            <line x1={x(b.median)} x2={x(b.median)} y1={cy - 9} y2={cy + 9}
              stroke="var(--viz-surface)" strokeWidth={2} />
            <circle cx={x(b.avg)} cy={cy} r={5} fill={SYM_COLOR[s]}
              stroke="var(--viz-surface)" strokeWidth={2} />
            <text x={x(b.min) - 10} y={cy + 4} fontSize={11} fill="var(--viz-mute)" textAnchor="end"
              style={{ fontVariantNumeric: "tabular-nums" }}>{b.min}</text>
            <text x={x(b.max) + 10} y={cy + 4} fontSize={11} fill="var(--viz-mute)" textAnchor="start"
              style={{ fontVariantNumeric: "tabular-nums" }}>{b.max}</text>
            <text x={x(b.avg)} y={cy + 26} fontSize={11} fill="var(--viz-ink)" textAnchor="middle"
              style={{ fontVariantNumeric: "tabular-nums" }}>ort. {fmt1(b.avg)}</text>
            <text x={4} y={cy + 4} fontSize={13} fill="var(--viz-ink)" fontWeight={600}>{s}</text>
          </g>
        );
      })}
    </svg>
  );
}
