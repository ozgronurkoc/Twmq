"use client";

import * as React from "react";

import { cn, sayi } from "@/lib/utils";

/**
 * Kupon özet kutusu ve toplam şeridi — iki kupon ailesinin ortak muhasebesi.
 *
 * Karne kuponları ile motor kuponları aynı üç sayıyı gösteriyor (kolon,
 * bedel, olasılıklar) ve ikinci bir kopya, birinin TL biçimini değiştirip
 * ötekinin değiştirmemesi demek olurdu.
 */

export function KuponOzetKutusu({
  ustBaslik,
  altBaslik,
  kolon,
  bedelTl,
  satirlar,
  uyari,
}: {
  ustBaslik: string;
  altBaslik: string;
  kolon: number;
  bedelTl: number | null;
  satirlar: { etiket: string; deger: string }[];
  uyari?: string | null;
}) {
  return (
    <div className="rounded-xl border border-line px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
        {ustBaslik}
      </div>
      {/* Şekil satırı sabit yükseklikte: sarınca kutular eşit kalsın. */}
      <div className="mt-0.5 min-h-[2.4em] text-[11.5px] leading-[1.2] text-muted-foreground">
        {altBaslik}
      </div>
      <div className="tnum mt-1 text-[16px] font-semibold">{sayi(kolon)} kolon</div>
      <div className="tnum mt-0.5 text-[11.5px] text-muted-foreground">
        {bedelTl == null ? "bedel —" : `₺${sayi(bedelTl)}`}
      </div>
      <div className="mt-2 space-y-0.5 border-t border-line/60 pt-2 text-[11.5px]">
        {satirlar.map((s) => (
          <div key={s.etiket} className="flex items-baseline justify-between gap-2">
            <span className="text-muted-foreground">{s.etiket}</span>
            <span className="tnum font-medium">{s.deger}</span>
          </div>
        ))}
      </div>
      {uyari ? <div className="mt-2 text-[11px] text-danger">{uyari}</div> : null}
    </div>
  );
}

export function KuponToplami({
  etiket,
  kolon,
  bedelTl,
  haftalikTavanTl,
}: {
  etiket: string;
  kolon: number;
  bedelTl: number | null;
  haftalikTavanTl: number | null;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-line px-3 py-2.5 text-[12px]">
      <span className="text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
        {etiket}
      </span>
      <span className="tnum font-semibold">{sayi(kolon)} kolon</span>
      <span className="tnum font-semibold">
        {bedelTl == null ? "—" : `₺${sayi(bedelTl)}`}
      </span>
      {bedelTl != null && haftalikTavanTl ? (
        <span
          className={cn(
            "tnum",
            bedelTl > haftalikTavanTl ? "text-danger" : "text-success",
          )}
        >
          haftalık tavanın {(bedelTl / haftalikTavanTl).toFixed(2)}×&apos;i (₺
          {sayi(haftalikTavanTl)})
        </span>
      ) : null}
    </div>
  );
}
