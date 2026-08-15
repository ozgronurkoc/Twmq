"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

// ─── Switch ───────────────────────────────────────────────────────────────

export function Switch({
  checked,
  onChange,
  label,
  hint,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: React.ReactNode;
  hint?: React.ReactNode;
  disabled?: boolean;
}) {
  // <label> sarmalamak role="switch" olan bir <button>'a ad KAZANDIRMAZ
  // (label yalnizca form kontrollerini etiketler). Bu yuzden ad acikca
  // aria-labelledby ile baglanir; aksi halde ekran okuyucu "isimsiz
  // anahtar" der.
  const labelId = React.useId();
  return (
    <div
      className={cn(
        "flex items-start gap-3",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
      )}
      onClick={() => !disabled && onChange(!checked)}
    >
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        disabled={disabled}
        onClick={(e) => {
          e.stopPropagation();
          onChange(!checked);
        }}
        className={cn(
          "relative mt-0.5 h-[22px] w-[38px] shrink-0 rounded-full transition-colors duration-200 ease-smooth",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          checked ? "bg-primary" : "bg-line-strong",
        )}
      >
        <span
          className={cn(
            "absolute top-[3px] h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ease-pop",
            checked ? "translate-x-[19px]" : "translate-x-[3px]",
          )}
        />
      </button>
      <span className="min-w-0 select-none">
        <span id={labelId} className="block text-[13.5px] font-medium leading-tight">
          {label}
        </span>
        {hint ? (
          <span className="mt-0.5 block text-[12px] leading-relaxed text-muted-foreground">
            {hint}
          </span>
        ) : null}
      </span>
    </div>
  );
}

// ─── Sayi alani ───────────────────────────────────────────────────────────

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  hint,
  suffix,
  disabled,
}: {
  label: React.ReactNode;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  hint?: React.ReactNode;
  suffix?: string;
  disabled?: boolean;
}) {
  const id = React.useId();
  return (
    <div className={cn(disabled && "opacity-50")}>
      <label
        htmlFor={id}
        className="block text-[12px] font-medium text-muted-foreground"
      >
        {label}
      </label>
      <div className="relative mt-1.5">
        <input
          id={id}
          type="number"
          inputMode="numeric"
          value={Number.isFinite(value) ? value : ""}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          onChange={(e) => {
            const n = Number(e.target.value);
            onChange(Number.isFinite(n) ? n : (min ?? 0));
          }}
          className={cn(
            "tnum h-10 w-full rounded-xl border border-line bg-background px-3 text-[13.5px]",
            "transition-shadow duration-200 ease-smooth",
            "focus:outline-none focus:ring-2 focus:ring-primary/50",
            suffix && "pr-12",
          )}
        />
        {suffix ? (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[12px] text-muted-foreground">
            {suffix}
          </span>
        ) : null}
      </div>
      {hint ? (
        <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

// ─── Kaydiraci ────────────────────────────────────────────────────────────

export function SliderField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  format,
  hint,
}: {
  label: React.ReactNode;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  format?: (v: number) => string;
  hint?: React.ReactNode;
}) {
  const id = React.useId();
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="text-[12px] font-medium text-muted-foreground">
          {label}
        </label>
        <span className="tnum text-[12.5px] font-semibold">
          {format ? format(value) : value}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-line accent-primary"
      />
      {hint ? (
        <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

// ─── Secim ────────────────────────────────────────────────────────────────

export function Select<T extends string>({
  label,
  value,
  onChange,
  options,
  hint,
  disabled,
}: {
  label: React.ReactNode;
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
  hint?: React.ReactNode;
  disabled?: boolean;
}) {
  const id = React.useId();
  return (
    <div className={cn(disabled && "opacity-50")}>
      <label htmlFor={id} className="block text-[12px] font-medium text-muted-foreground">
        {label}
      </label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as T)}
        className={cn(
          "mt-1.5 h-10 w-full rounded-xl border border-line bg-background px-3 text-[13.5px]",
          "transition-shadow duration-200 ease-smooth",
          "focus:outline-none focus:ring-2 focus:ring-primary/50",
        )}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {hint ? (
        <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

// ─── Katlanir bolum ───────────────────────────────────────────────────────

export function Collapsible({
  baslik,
  hint,
  children,
  defaultOpen = false,
}: {
  baslik: React.ReactNode;
  hint?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div className="rounded-xl border border-line">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <span className="min-w-0">
          <span className="block text-[13px] font-semibold">{baslik}</span>
          {hint ? (
            <span className="mt-0.5 block text-[11.5px] text-muted-foreground">{hint}</span>
          ) : null}
        </span>
        <span
          aria-hidden
          className={cn(
            "shrink-0 text-muted-foreground transition-transform duration-200 ease-smooth",
            open && "rotate-180",
          )}
        >
          ▾
        </span>
      </button>
      {open ? <div className="border-t border-line px-4 py-4">{children}</div> : null}
    </div>
  );
}
