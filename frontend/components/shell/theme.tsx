"use client";

import * as React from "react";
import { Monitor, Moon, Sun } from "lucide-react";

import { cn } from "@/lib/utils";

type Tema = "system" | "light" | "dark";
const ANAHTAR = "spor-toto-tema";

const Ctx = React.createContext<{
  tema: Tema;
  setTema: (t: Tema) => void;
}>({ tema: "system", setTema: () => {} });

/**
 * Varsayilan "system"dir ve o durumda hicbir sey isaretlenmez —
 * globals.css'teki prefers-color-scheme devreye girer, yani JS calismadan
 * once de dogru tema uygulanir (flash yok). data-theme yalnizca kullanici
 * acikca sectiginde yazilir.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [tema, setTemaState] = React.useState<Tema>("system");

  React.useEffect(() => {
    try {
      const kayitli = window.localStorage.getItem(ANAHTAR) as Tema | null;
      if (kayitli === "light" || kayitli === "dark") setTemaState(kayitli);
    } catch {
      /* localStorage kapali olabilir */
    }
  }, []);

  React.useEffect(() => {
    const kok = document.documentElement;
    if (tema === "system") kok.removeAttribute("data-theme");
    else kok.setAttribute("data-theme", tema);
    try {
      if (tema === "system") window.localStorage.removeItem(ANAHTAR);
      else window.localStorage.setItem(ANAHTAR, tema);
    } catch {
      /* yok say */
    }
  }, [tema]);

  const deger = React.useMemo(() => ({ tema, setTema: setTemaState }), [tema]);
  return <Ctx.Provider value={deger}>{children}</Ctx.Provider>;
}

export function ThemeToggle({ kompakt = false }: { kompakt?: boolean }) {
  const { tema, setTema } = React.useContext(Ctx);
  const secenekler: { id: Tema; icon: React.ReactNode; label: string }[] = [
    { id: "light", icon: <Sun size={14} />, label: "Açık" },
    { id: "system", icon: <Monitor size={14} />, label: "Sistem" },
    { id: "dark", icon: <Moon size={14} />, label: "Koyu" },
  ];

  if (kompakt) {
    const sonraki: Tema =
      tema === "light" ? "dark" : tema === "dark" ? "system" : "light";
    const aktif = secenekler.find((s) => s.id === tema);
    return (
      <button
        type="button"
        onClick={() => setTema(sonraki)}
        aria-label={`Tema: ${aktif?.label}. Değiştir.`}
        className="rounded-lg p-2 text-sidebar-muted transition-colors hover:bg-white/5 hover:text-sidebar-foreground"
      >
        {aktif?.icon}
      </button>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-label="Tema"
      className="flex gap-0.5 rounded-lg bg-white/5 p-0.5"
    >
      {secenekler.map((s) => (
        <button
          key={s.id}
          type="button"
          role="radio"
          aria-checked={tema === s.id}
          aria-label={s.label}
          title={s.label}
          onClick={() => setTema(s.id)}
          className={cn(
            "flex-1 rounded-md px-2 py-1.5 transition-colors duration-200",
            "flex items-center justify-center",
            tema === s.id
              ? "bg-white/10 text-sidebar-foreground"
              : "text-sidebar-muted hover:text-sidebar-foreground",
          )}
        >
          {s.icon}
        </button>
      ))}
    </div>
  );
}
