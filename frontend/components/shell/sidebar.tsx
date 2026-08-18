"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Grid3x3,
  History,
  PanelLeftClose,
  PanelLeftOpen,
  Trophy,
  Zap,
} from "lucide-react";

import { SUPER_TOTO_SEZON } from "@/lib/super-toto";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./theme";

interface NavItem {
  href: string;
  label: string;
  hint: string;
  icon: React.ReactNode;
}

interface NavGroup {
  baslik: string;
  items: NavItem[];
}

const GRUPLAR: NavGroup[] = [
  {
    baslik: "Çalışma",
    items: [
      {
        href: "/",
        label: "Formül",
        hint: "Kaplama kodu üret",
        icon: <Grid3x3 size={17} />,
      },
    ],
  },
  {
    baslik: "Veri",
    items: [
      {
        href: "/super-toto",
        label: "Süper Toto",
        hint: `${SUPER_TOTO_SEZON} · işlenen sezon`,
        icon: <Trophy size={17} />,
      },
      {
        href: "/istatistik",
        label: "İstatistik",
        hint: "Tarihsel 1 / 0 / 2",
        icon: <BarChart3 size={17} />,
      },
      {
        href: "/istatistik/geri-test",
        label: "Geri test",
        hint: "Strateji geçen sezon ne yapardı",
        icon: <History size={17} />,
      },
    ],
  },
  {
    baslik: "Sistem",
    items: [
      {
        href: "/saglik",
        label: "Sağlık",
        hint: "Motor değişmezleri",
        icon: <Activity size={17} />,
      },
    ],
  },
];

function eslesirMi(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(href + "/");
}

/**
 * Eslesen href'lerin EN UZUNU aktiftir. `/istatistik` ile
 * `/istatistik/geri-test` ikisi de eslestigi icin bu gerekli: aksi halde
 * geri test sayfasinda iki baglanti birden vurgulanirdi.
 */
function aktifHref(pathname: string): string | null {
  const eslesenler = GRUPLAR.flatMap((g) => g.items)
    .map((i) => i.href)
    .filter((h) => eslesirMi(pathname, h));
  if (!eslesenler.length) return null;
  return eslesenler.reduce((a, b) => (b.length > a.length ? b : a));
}

export function SidebarIcerik({
  dar,
  onDarDegis,
  onGezinme,
}: {
  dar: boolean;
  onDarDegis?: () => void;
  onGezinme?: () => void;
}) {
  const pathname = usePathname() || "/";
  const aktif_href = aktifHref(pathname);

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      {/* Marka */}
      <div
        className={cn(
          "flex items-center gap-3 px-4 pb-4 pt-5",
          dar && "justify-center px-2",
        )}
      >
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-hero shadow-glow">
          <Zap size={18} className="text-white" />
        </span>
        {!dar ? (
          <div className="min-w-0 flex-1">
            <div className="truncate font-display text-[16px] italic leading-tight">
              Spor Toto Lab
            </div>
            <div className="truncate text-[11px] text-sidebar-muted">
              14-garanti kaplama motoru
            </div>
          </div>
        ) : null}
        {onDarDegis && !dar ? (
          <button
            type="button"
            onClick={onDarDegis}
            aria-label="Kenar çubuğunu daralt"
            className="rounded-lg p-1.5 text-sidebar-muted transition-colors hover:bg-white/5 hover:text-sidebar-foreground"
          >
            <PanelLeftClose size={16} />
          </button>
        ) : null}
      </div>

      {onDarDegis && dar ? (
        <button
          type="button"
          onClick={onDarDegis}
          aria-label="Kenar çubuğunu genişlet"
          className="mx-auto mb-2 rounded-lg p-1.5 text-sidebar-muted transition-colors hover:bg-white/5 hover:text-sidebar-foreground"
        >
          <PanelLeftOpen size={16} />
        </button>
      ) : null}

      {/* Gezinme */}
      <nav className="flex-1 overflow-y-auto scroll-slim px-2 pb-4">
        {GRUPLAR.map((grup) => (
          <div key={grup.baslik} className="mb-4">
            {!dar ? (
              <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-sidebar-muted">
                {grup.baslik}
              </div>
            ) : (
              <div className="mx-3 mb-2 border-t border-sidebar-border" />
            )}
            <div className="flex flex-col gap-0.5">
              {grup.items.map((item) => {
                const aktif = item.href === aktif_href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onGezinme}
                    aria-current={aktif ? "page" : undefined}
                    title={dar ? item.label : undefined}
                    className={cn(
                      "group relative flex items-center gap-3 rounded-xl px-3 py-2.5",
                      "transition-colors duration-200 ease-smooth",
                      dar && "justify-center px-0",
                      aktif
                        ? "bg-sidebar-active text-white"
                        : "text-sidebar-foreground/80 hover:bg-white/5 hover:text-sidebar-foreground",
                    )}
                  >
                    {aktif ? (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary-glow"
                      />
                    ) : null}
                    <span className="shrink-0">{item.icon}</span>
                    {!dar ? (
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13.5px] font-medium leading-tight">
                          {item.label}
                        </span>
                        <span className="block truncate text-[11px] text-sidebar-muted">
                          {item.hint}
                        </span>
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Alt blok */}
      <div className="border-t border-sidebar-border p-3">
        {!dar ? (
          <>
            <ThemeToggle />
            <p className="mt-3 text-[10.5px] leading-relaxed text-sidebar-muted">
              Next.js arayüz · Python motoru
              <br />
              Bu araç maç sonucu tahmin etmez.
            </p>
          </>
        ) : (
          <div className="flex justify-center">
            <ThemeToggle kompakt />
          </div>
        )}
      </div>
    </div>
  );
}
