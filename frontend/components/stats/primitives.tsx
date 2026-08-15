"use client";

import type { ReactNode } from "react";
import type { DataQuality, Sym } from "@/lib/api";
import { SYMS, SYM_COLOR, SYM_LABEL, signed } from "./tokens";

export function Card({
  title, hint, children, className = "", right,
}: {
  title?: string; hint?: string; children: ReactNode; className?: string; right?: ReactNode;
}) {
  return (
    <section className={`card p-5 ${className}`}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 mb-4">
          <div>
            {title && <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>}
            {hint && <p className="text-[12px] text-[var(--muted)] mt-0.5 max-w-prose">{hint}</p>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

/** İki ve daha fazla seri için efsane her zaman vardır — kimlik asla renge tek başına bırakılmaz. */
export function Legend({ compact = false }: { compact?: boolean }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {SYMS.map((s) => (
        <li key={s} className="flex items-center gap-1.5 text-[12px] text-[var(--muted)]">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm shrink-0"
            style={{ background: SYM_COLOR[s] }}
            aria-hidden
          />
          {compact ? s : SYM_LABEL[s]}
        </li>
      ))}
    </ul>
  );
}

export function StatTile({
  label, value, sub, delta, deltaNote, accent,
}: {
  label: string; value: string; sub?: string;
  delta?: number; deltaNote?: string; accent?: Sym;
}) {
  return (
    <div className="rounded-2xl bg-[var(--bg)] px-4 py-4">
      <div className="flex items-center gap-1.5">
        {accent && (
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: SYM_COLOR[accent] }}
            aria-hidden
          />
        )}
        <span className="text-[12px] text-[var(--muted)]">{label}</span>
      </div>
      <div className="text-[28px] leading-tight font-semibold mt-1">{value}</div>
      {sub && <div className="text-[12px] text-[var(--muted)] mt-0.5">{sub}</div>}
      {delta !== undefined && (
        <div className="text-[12px] mt-1.5 text-[var(--muted)]">
          <span className="font-medium text-[var(--ink)]">{signed(delta)}</span>
          {deltaNote ? ` ${deltaNote}` : ""}
        </div>
      )}
    </div>
  );
}

/** 15 maçlık sonuç dizisi — kareler arasında 2px yüzey boşluğu ayırıcıdır. */
export function ResultStrip({
  results, size = "sm", marks,
}: {
  results: string; size?: "sm" | "lg"; marks?: (i: number) => string | undefined;
}) {
  const cells = results.split("");
  const lg = size === "lg";
  return (
    <div className={`flex ${lg ? "gap-1.5 flex-wrap" : "gap-[2px]"}`}>
      {cells.map((ch, i) => {
        const sym = ch as Sym;
        const note = marks?.(i);
        return (
          <div key={i} className={lg ? "text-center" : ""}>
            {lg && <div className="text-[10px] text-[var(--muted)] mb-1">{i + 1}</div>}
            <div
              title={`${i + 1}. maç · ${SYM_LABEL[sym] ?? ch}`}
              className={
                lg
                  ? "h-9 w-9 rounded-lg text-white text-[13px] font-semibold flex items-center justify-center"
                  : "h-4 w-[9px] rounded-[2px]"
              }
              style={{ background: SYM_COLOR[sym] ?? "var(--line)" }}
            >
              {lg ? ch : ""}
            </div>
            {lg && note && <div className="text-[10px] text-[var(--muted)] mt-1">{note}</div>}
          </div>
        );
      })}
    </div>
  );
}

/** Tüm görselleri kapsayan tek filtre satırı — kartların içine filtre koymuyoruz. */
export function RangeFilter({
  value, onChange, options, busy,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
  options: Array<{ value: number | null; label: string }>;
  busy?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap" role="group" aria-label="Hafta aralığı">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={String(o.value)}
            type="button"
            onClick={() => onChange(o.value)}
            aria-pressed={active}
            className={`h-9 px-3.5 rounded-xl text-[13px] font-medium border transition ${
              active
                ? "bg-[var(--ink)] text-white border-transparent"
                : "bg-white text-[var(--ink)] border-[var(--line)] hover:bg-[var(--bg)]"
            }`}
          >
            {o.label}
          </button>
        );
      })}
      <span
        className={`text-[12px] text-[var(--muted)] transition-opacity ${busy ? "opacity-100" : "opacity-0"}`}
        aria-live="polite"
      >
        güncelleniyor…
      </span>
    </div>
  );
}

export function DataQualityPanel({ dq }: { dq: DataQuality }) {
  const conflicts = dq.count_conflicts ?? [];
  const dups = dq.duplicate_results ?? [];
  const incomplete = dq.incomplete_weeks ?? [];
  if (dq.ok) {
    return (
      <p className="text-[13px] text-[var(--muted)] flex items-center gap-2">
        <span aria-hidden>✓</span> {dq.weeks_total} haftanın tamamı tutarlı: sayımlar sonuç dizisiyle birebir.
      </p>
    );
  }
  return (
    <div className="space-y-3 text-[13px]">
      <p className="flex items-start gap-2 text-[var(--ink)]">
        <span aria-hidden className="text-[var(--warn)]">⚠</span>
        <span>
          <strong className="font-semibold">Veri uyarısı.</strong> Tüm sayımlar 15 karakterlik{" "}
          <code className="text-[12px]">results</code> dizisinden türetilir; dosyadaki hazır{" "}
          <code className="text-[12px]">n1/n0/n2</code> alanları çeliştiğinde aşağıda listelenir.
        </span>
      </p>
      {conflicts.length > 0 && (
        <div>
          <div className="text-[var(--muted)] mb-1.5">
            Sayım çelişkisi: {conflicts.length} hafta
          </div>
          <ul className="space-y-1">
            {conflicts.map((c) => (
              <li key={c.week} className="tabular-nums">
                <span className="font-medium">{c.week}. hafta</span>{" "}
                <span className="text-[var(--muted)]">
                  dosya {SYMS.map((s) => c.reported?.[s] ?? 0).join("/")} · dizi{" "}
                  {SYMS.map((s) => c.derived[s]).join("/")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {dups.length > 0 && (
        <div>
          <div className="text-[var(--muted)] mb-1.5">Aynı sonuç dizisi tekrar eden haftalar</div>
          <ul className="space-y-1">
            {dups.map((d) => (
              <li key={d.results} className="flex items-center gap-2">
                <span className="tabular-nums">{d.weeks.join(" · ")}. hafta</span>
                <ResultStrip results={d.results} />
              </li>
            ))}
          </ul>
        </div>
      )}
      {incomplete.length > 0 && (
        <div className="text-[var(--muted)]">
          Eksik hafta (15 maçtan az): {incomplete.join(", ")}
        </div>
      )}
    </div>
  );
}

export function VizTooltip({
  x, y, width, children,
}: {
  x: number; y: number; width: number; children: ReactNode;
}) {
  const clamped = Math.min(Math.max(x, 72), Math.max(width - 72, 72));
  return (
    <div
      className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+10px)]
        rounded-xl bg-[#1d1d1f] text-white text-[12px] px-3 py-2 shadow-lg whitespace-nowrap"
      style={{ left: clamped, top: y }}
      role="status"
    >
      {children}
    </div>
  );
}

export function TooltipRow({ sym, label, value }: { sym?: Sym; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      {sym && (
        <span className="inline-block h-2 w-2 rounded-sm" style={{ background: SYM_COLOR[sym] }} aria-hidden />
      )}
      <span className="text-white/70">{label}</span>
      <span className="ml-auto tabular-nums font-medium">{value}</span>
    </div>
  );
}
