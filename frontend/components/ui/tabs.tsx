"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
  /** false ise sekme gorunur ama tiklanamaz (veri yok). */
  enabled?: boolean;
  badge?: React.ReactNode;
}

/**
 * Elle yazilmis, erisilebilir sekme seridi.
 * role=tablist/tab/tabpanel + ok tuslariyla gezinme (WAI-ARIA deseni).
 */
export function Tabs({
  items,
  value,
  onChange,
  className,
}: {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  const refs = React.useRef<Record<string, HTMLButtonElement | null>>({});
  const acik = items.filter((i) => i.enabled !== false);

  function tusla(e: React.KeyboardEvent) {
    const idx = acik.findIndex((i) => i.id === value);
    if (idx < 0) return;
    let hedef: number | null = null;
    if (e.key === "ArrowRight") hedef = (idx + 1) % acik.length;
    else if (e.key === "ArrowLeft") hedef = (idx - 1 + acik.length) % acik.length;
    else if (e.key === "Home") hedef = 0;
    else if (e.key === "End") hedef = acik.length - 1;
    if (hedef === null) return;
    // `hedef` modulo ile hesaplandi, yani `acik` bosken 0 ya da NaN olur.
    // Sekme yokken ok tusuna basmak sayfayi cokertmemeli.
    const sekme = acik[hedef];
    if (!sekme) return;
    e.preventDefault();
    const id = sekme.id;
    onChange(id);
    refs.current[id]?.focus();
  }

  return (
    <div
      role="tablist"
      aria-label="Sonuç panelleri"
      onKeyDown={tusla}
      className={cn(
        "scroll-slim flex gap-1 overflow-x-auto rounded-xl bg-muted p-1",
        className,
      )}
    >
      {items.map((item) => {
        const secili = item.id === value;
        const kapali = item.enabled === false;
        return (
          <button
            key={item.id}
            ref={(el) => {
              refs.current[item.id] = el;
            }}
            role="tab"
            id={`tab-${item.id}`}
            aria-selected={secili}
            aria-controls={`panel-${item.id}`}
            tabIndex={secili ? 0 : -1}
            disabled={kapali}
            onClick={() => onChange(item.id)}
            className={cn(
              "relative shrink-0 whitespace-nowrap rounded-lg px-3 py-1.5 text-[12.5px] font-medium",
              "transition-all duration-200 ease-smooth",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60",
              secili
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
              kapali && "cursor-not-allowed opacity-40 hover:text-muted-foreground",
            )}
          >
            {item.label}
            {item.badge ? (
              <span className="ml-1.5 text-[10.5px] text-muted-foreground">
                {item.badge}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({
  id,
  active,
  children,
}: {
  id: string;
  active: boolean;
  children: React.ReactNode;
}) {
  if (!active) return null;
  return (
    <div
      role="tabpanel"
      id={`panel-${id}`}
      aria-labelledby={`tab-${id}`}
      tabIndex={0}
      className="animate-fade-up focus:outline-none"
    >
      {children}
    </div>
  );
}
