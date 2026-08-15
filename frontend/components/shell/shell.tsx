"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Menu, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { SidebarIcerik } from "./sidebar";

/**
 * Kalici kenar cubugu + icerik penceresi.
 *
 * Sayfa gecisi burada yasar: rota degistiginde YALNIZCA icerik alani
 * animasyonla degisir, kenar cubugu yerinde kalir. Egri Apple'in kendi
 * gecis egrisi (0.32, 0.72, 0, 1).
 */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const azHareket = useReducedMotion();
  const [dar, setDar] = React.useState(false);
  const [mobilAcik, setMobilAcik] = React.useState(false);

  // Rota degisince mobil cekmece kapansin.
  React.useEffect(() => {
    setMobilAcik(false);
  }, [pathname]);

  // Cekmece acikken arka plan kaymasin.
  React.useEffect(() => {
    if (!mobilAcik) return;
    const eski = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = eski;
    };
  }, [mobilAcik]);

  return (
    <div className="flex min-h-screen bg-background">
      {/* Masaustu kenar cubugu */}
      <aside
        className={cn(
          "sticky top-0 hidden h-screen shrink-0 lg:block",
          "transition-[width] duration-300 ease-ios",
          dar ? "w-[76px]" : "w-[264px]",
        )}
      >
        <SidebarIcerik dar={dar} onDarDegis={() => setDar((v) => !v)} />
      </aside>

      {/* Mobil ust cubuk */}
      <div className="fixed inset-x-0 top-0 z-40 flex h-14 items-center gap-3 border-b border-line bg-background/80 px-4 backdrop-blur-xl lg:hidden">
        <button
          type="button"
          onClick={() => setMobilAcik(true)}
          aria-label="Menüyü aç"
          className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <Menu size={18} />
        </button>
        <span className="font-display text-[15px] italic">Spor Toto Lab</span>
      </div>

      {/* Mobil cekmece */}
      <AnimatePresence>
        {mobilAcik ? (
          <>
            <motion.button
              type="button"
              aria-label="Menüyü kapat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setMobilAcik(false)}
              className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm lg:hidden"
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={
                azHareket
                  ? { duration: 0 }
                  : { duration: 0.34, ease: [0.32, 0.72, 0, 1] }
              }
              className="fixed inset-y-0 left-0 z-50 w-[280px] lg:hidden"
            >
              <SidebarIcerik dar={false} onGezinme={() => setMobilAcik(false)} />
              <button
                type="button"
                onClick={() => setMobilAcik(false)}
                aria-label="Menüyü kapat"
                className="absolute right-3 top-5 rounded-lg p-1.5 text-sidebar-muted hover:bg-white/5"
              >
                <X size={16} />
              </button>
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>

      {/* Icerik penceresi */}
      <main className="relative min-w-0 flex-1 pt-14 lg:pt-0">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-[420px] bg-glow"
        />
        <div className="relative mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-8 sm:py-10">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={pathname}
              initial={azHareket ? { opacity: 0 } : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={azHareket ? { opacity: 0 } : { opacity: 0, y: -6 }}
              transition={
                azHareket
                  ? { duration: 0.12 }
                  : { duration: 0.32, ease: [0.32, 0.72, 0, 1] }
              }
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
