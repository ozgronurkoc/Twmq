import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Spor Toto Lab",
  description: "14-garanti kaplama · Next.js + Python API",
};

const nav = [
  { href: "/", label: "Formül Üret" },
  { href: "/stats", label: "İstatistik" },
  { href: "/health", label: "Sağlık" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <div className="min-h-screen flex">
          <aside className="w-56 shrink-0 bg-ink text-white flex flex-col px-3 py-5">
            <div className="flex items-center gap-2 px-3 pb-6">
              <span className="h-5 w-5 rounded-md bg-gradient-to-br from-brand to-sky-300" />
              <span className="font-semibold tracking-tight">Spor Toto Lab</span>
            </div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-500 px-3 mb-2">Çalışma</div>
            <nav className="flex flex-col gap-1">
              {nav.map((item) => (
                <Link key={item.href} href={item.href} className="rounded-xl px-3 py-2.5 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white transition">
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="mt-auto px-3 pt-4 text-[11px] text-zinc-500 border-t border-zinc-800">Next.js · Python API</div>
          </aside>
          <main className="flex-1 min-w-0 p-6 md:p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
