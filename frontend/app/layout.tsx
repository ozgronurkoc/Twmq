import type { Metadata, Viewport } from "next";
import { Bodoni_Moda } from "next/font/google";

import { Shell } from "@/components/shell/shell";
import { ThemeProvider } from "@/components/shell/theme";
import "./globals.css";

/**
 * Bodoni Moda — nonplo.com'un display serif'i. next/font onu derleme
 * aninda indirip kendi sunucumuzdan servis eder; calisma aninda disariya
 * istek gitmez.
 */
const display = Bodoni_Moda({
  subsets: ["latin"],
  style: ["italic", "normal"],
  weight: ["400", "500", "600"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Spor Toto Lab · 14-garanti kaplama",
  description:
    "Spor Toto kuponu için kaplama kodu üretir: tahminin doğruysa onu en az " +
    "kuponla garantiye alır. Ayrıca yaklaşan maçlara ölçülmüş isabetiyle " +
    "birlikte 1/0/2 olasılığı verir.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0f0d17" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Not: <html> ve <body> Next.js App Router'in kok bileseninde ZORUNLUDUR;
  // bu cercevenin API'sidir, elle yazilmis HTML dosyasi degildir. Projede
  // baska hicbir yerde ham HTML yoktur.
  return (
    <html lang="tr" className={display.variable} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <ThemeProvider>
          <Shell>{children}</Shell>
        </ThemeProvider>
      </body>
    </html>
  );
}
