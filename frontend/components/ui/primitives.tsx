import * as React from "react";

import { cn } from "@/lib/utils";

// ─── Card ─────────────────────────────────────────────────────────────────

export function Card({
  className,
  glow = false,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { glow?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-line bg-card text-card-foreground shadow-card",
        glow && "shadow-primary",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({
  title,
  hint,
  action,
  className,
}: {
  title: React.ReactNode;
  hint?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 border-b border-line px-5 py-4",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
        {hint ? (
          <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
            {hint}
          </p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function CardBody({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...props} />;
}

// ─── Badge ────────────────────────────────────────────────────────────────

type Ton = "neutral" | "primary" | "success" | "warning" | "danger";

const TONLAR: Record<Ton, string> = {
  neutral: "bg-muted text-muted-foreground border-line",
  primary: "bg-accent text-accent-foreground border-primary/20",
  success: "bg-success-soft text-success border-success/25",
  warning: "bg-warning-soft text-warning border-warning/25",
  danger: "bg-danger-soft text-danger border-danger/25",
};

export function Badge({
  ton = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { ton?: Ton }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5",
        "text-[11.5px] font-medium leading-5",
        TONLAR[ton],
        className,
      )}
      {...props}
    />
  );
}

// ─── Button ───────────────────────────────────────────────────────────────

type ButonTipi = "primary" | "ghost" | "outline" | "subtle";

const BUTONLAR: Record<ButonTipi, string> = {
  primary:
    "bg-primary text-primary-foreground shadow-primary hover:brightness-110 active:brightness-95",
  outline: "border border-line-strong bg-transparent hover:bg-muted",
  ghost: "bg-transparent hover:bg-muted",
  subtle: "bg-muted text-foreground hover:bg-line",
};

export const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    tip?: ButonTipi;
    boyut?: "sm" | "md" | "lg";
  }
>(function Button({ tip = "primary", boyut = "md", className, ...props }, ref) {
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex select-none items-center justify-center gap-2 rounded-xl font-medium",
        "transition-all duration-200 ease-smooth",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        boyut === "sm" && "h-8 px-3 text-[12.5px]",
        boyut === "md" && "h-10 px-4 text-[13.5px]",
        boyut === "lg" && "h-12 px-6 text-[15px]",
        BUTONLAR[tip],
        className,
      )}
      {...props}
    />
  );
});

// ─── Callout ──────────────────────────────────────────────────────────────

export function Callout({
  ton = "neutral",
  baslik,
  children,
  className,
}: {
  ton?: Ton;
  baslik?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  const kenar: Record<Ton, string> = {
    neutral: "border-line bg-muted/60",
    primary: "border-primary/25 bg-accent",
    success: "border-success/25 bg-success-soft",
    warning: "border-warning/30 bg-warning-soft",
    danger: "border-danger/30 bg-danger-soft",
  };
  const yazi: Record<Ton, string> = {
    neutral: "text-muted-foreground",
    primary: "text-accent-foreground",
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
  };
  return (
    <div className={cn("rounded-xl border px-4 py-3", kenar[ton], className)}>
      {baslik ? (
        <div className={cn("text-[13px] font-semibold", yazi[ton])}>{baslik}</div>
      ) : null}
      {children ? (
        <div
          className={cn(
            "text-[12.5px] leading-relaxed",
            baslik && "mt-1",
            ton === "neutral" ? "text-muted-foreground" : yazi[ton],
          )}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}

// ─── Stat ─────────────────────────────────────────────────────────────────

/**
 * Etiket + buyuk sayi + aciklama kutusu.
 *
 * `boyut` iki cagri yerini de karsilar: `istatistik/backtest` bu kutunun
 * kendi kopyasini (`Kutu`) tasiyordu ve tek farki daha buyuk punto ile
 * `alt` satirindaki tabular rakamlardi — manşet sayilari icin bilincli bir
 * secim. Kopya yerine varyant.
 */
export function Stat({
  etiket,
  deger,
  alt,
  ton = "neutral",
  boyut = "md",
  className,
}: {
  etiket: React.ReactNode;
  deger: React.ReactNode;
  alt?: React.ReactNode;
  ton?: Ton;
  boyut?: "md" | "lg";
  className?: string;
}) {
  const renk: Record<Ton, string> = {
    neutral: "text-foreground",
    primary: "text-primary",
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
  };
  return (
    <div
      className={cn(
        "rounded-xl border border-line bg-elevated px-4 py-3",
        className,
      )}
    >
      <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
        {etiket}
      </div>
      <div
        className={cn(
          "tnum mt-1 font-semibold leading-tight",
          boyut === "lg" ? "text-[24px]" : "text-[22px]",
          renk[ton],
        )}
      >
        {deger}
      </div>
      {alt ? (
        <div
          className={cn(
            "mt-0.5 text-[11.5px] leading-relaxed text-muted-foreground",
            boyut === "lg" && "tnum",
          )}
        >
          {alt}
        </div>
      ) : null}
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-shimmer rounded-lg bg-muted",
        "bg-[linear-gradient(90deg,hsl(var(--muted))_0%,hsl(var(--elevated))_50%,hsl(var(--muted))_100%)]",
        "bg-[length:200%_100%]",
        className,
      )}
    />
  );
}

// ─── Bolum basligi ────────────────────────────────────────────────────────

export function SectionTitle({
  children,
  hint,
}: {
  children: React.ReactNode;
  hint?: React.ReactNode;
}) {
  return (
    <div className="mb-3">
      <h3 className="text-[13px] font-semibold uppercase tracking-[0.09em] text-muted-foreground">
        {children}
      </h3>
      {hint ? (
        <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
