import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Spor Toto Lab",
  description: "14-garanti kaplama · Next.js + Python API",
};

const nav = [
  { href: "/", label: "Formül Üret", hint: "Fix-16 motor" },
  { href: "/stats", label: "İstatistik", hint: "Tarihsel 1/0/2" },
  { href: "/health", label: "Sağlık", hint: "Sistem testleri" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <div className="min-h-screen flex bg-[var(--bg)]">
          <aside className="hidden sm:flex w-[240px] shrink-0 flex-col bg-[#0f0f10] text-white">
            <div className="px-5 pt-6 pb-5">
              <div className="flex items-center gap-3">
                <span className="h-8 w-8 rounded-xl bg-gradient-to-br from-[#0071e3] via-[#5ac8fa] to-[#a78bfa] shadow-lg shadow-blue-500/20" />
                <div>
                  <div className="text-[15px] font-semibold tracking-tight">Spor Toto Lab</div>
                  <div className="text-[11px] text-zinc-500">14-garanti motor</div>
                </div>
              </div>
            </div>
            <div className="px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-600 mb-2">Çalışma</div>
            <nav className="flex flex-col gap-1 px-3">
              {nav.map((item) => (
                <Link key={item.href} href={item.href} className="group rounded-xl px-3 py-2.5 transition hover:bg-white/5">
                  <div className="text-[13px] font-medium text-zinc-200 group-hover:text-white">{item.label}</div>
                  <div className="text-[11px] text-zinc-600 group-hover:text-zinc-500">{item.hint}</div>
                </Link>
              ))}
            </nav>
            <div className="mt-auto px-5 py-4 border-t border-white/5">
              <div className="text-[11px] text-zinc-600 leading-relaxed">
                Next.js UI · Python API<br />
                <span className="text-zinc-500">spor_toto · Fix-16</span>
              </div>
            </div>
          </aside>
          <div className="sm:hidden fixed top-0 inset-x-0 z-40 bg-white/80 backdrop-blur-xl border-b border-[var(--line-soft)]">
            <div className="flex items-center gap-2 px-4 h-12 overflow-x-auto">
              <span className="font-semibold text-sm shrink-0">Lab</span>
              {nav.map((item) => (
                <Link key={item.href} href={item.href} className="shrink-0 text-xs font-medium px-3 py-1.5 rounded-full bg-[var(--bg)] text-[var(--muted)]">{item.label}</Link>
              ))}
            </div>
          </div>
          <main className="flex-1 min-w-0 pt-14 sm:pt-0">
            <div className="max-w-6xl mx-auto px-4 sm:px-8 py-6 sm:py-10">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
