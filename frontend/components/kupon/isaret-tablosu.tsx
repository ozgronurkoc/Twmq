"use client";

import * as React from "react";

import type { KuponSatiri } from "@/lib/kupon";
import { MAC_SAYISI, SEMBOLLER, type Sembol } from "@/lib/types";
import { cn } from "@/lib/utils";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

/**
 * 15 maç x N kupon işaret tablosu — **iki kaynağın ortak çizicisi**.
 *
 * Sayfada iki kupon ailesi var ve ikisi de aynı tabloyu istiyor: karne
 * kuponları (`kupon-sekil.ts`) ve motor kuponları (`/api/kupon/motor`).
 * İkinci bir kopya yazmak, iki tablonun sessizce ayrışacağı yer olurdu —
 * aynı maç iki kartta farklı hizalanır, biri sembol düzenini değiştirir ve
 * kimse fark etmez. Çizim burada tek, besleyen veri iki.
 *
 * ─── Niçin üç sembol de yazılıyor ────────────────────────────────────────
 *
 * İşaretlenmeyeni silmek "neden bu işaret" sorusunu ekrandan kaldırırdı:
 * bir bankoyu banko yapan şey, ötekilerin ne kadar geride kaldığıdır.
 * Seçilenler dolu, seçilmeyenler soluk.
 */

const SECILI: Record<Sembol, string> = {
  "1": "bg-sym-1 text-white border-sym-1",
  "0": "bg-sym-0 text-white border-sym-0",
  "2": "bg-sym-2 text-white border-sym-2",
};

/** Bir maçın bir kupondaki hâli. */
export interface SutunHucresi {
  /** Seçilen semboller; boş dizi "işaret yok" demektir. */
  semboller: Sembol[];
  /** `BANKO` / `ÇİFT` / `ÜÇLÜ` — hücrenin yanında duran kısa etiket. */
  etiket: string;
  /** Etiketin ipucu (derece, kaçak olasılığı…). */
  ipucu?: string;
  /** Satırın yanında duran kısa uyarılar ("piyasa", "az örnek"). */
  uyarilar?: { metin: string; ipucu: string }[];
  /** İşaret üretilememişse ekranda duracak metin. */
  bosMetni?: string;
}

/** Tablodaki bir kupon sütunu. */
export interface KuponSutunu {
  /** React anahtarı — sütunlar arasında benzersiz. */
  anahtar: string;
  /** Üst satır: `AÇILIŞ` / `KAPANIŞ`. */
  baslik: string;
  /** Alt satır: şeklin adı. */
  altBaslik: string;
  /** 15 hücre. */
  hucreler: SutunHucresi[];
}

export function IsaretTablosu({
  satirlar,
  sutunlar,
}: {
  satirlar: KuponSatiri[];
  sutunlar: KuponSutunu[];
}) {
  return (
    <div className={TABLO_SARMAL}>
      {/*
        En az genişlik SÜTUN SAYISINA bağlı: `table-fixed` hücreyi içeriğe
        göre büyütmez, taşan şey kırpılır. Bir kupon sütunu üç sembol
        kutusu + seviye etiketi taşıyor (~142 piksel).
      */}
      <table
        className="w-full table-fixed border-separate border-spacing-0"
        style={{ minWidth: `${300 + 142 * Math.max(1, sutunlar.length)}px` }}
      >
        <colgroup>
          <col className="w-[4%]" />
          <col className="w-[25%]" />
          {sutunlar.map((s) => (
            <col key={s.anahtar} style={{ width: `${71 / sutunlar.length}%` }} />
          ))}
        </colgroup>
        <thead>
          <tr className={cn(TABLO_BASLIK_SATIRI, "[&>th]:whitespace-nowrap")}>
            <th className="pb-2 pr-2 text-right font-medium">#</th>
            <th className="pb-2 pl-2 text-left font-medium">Maç</th>
            {sutunlar.map((s) => (
              <th
                key={s.anahtar}
                // Şekil adı KENDİ satırında ve sarabilir; tek satırda son
                // sütunda kırpılıyordu (başlık satırı `nowrap`).
                className="whitespace-normal border-l border-line/50 pb-2 pl-2 text-left align-bottom font-medium"
              >
                <div className="text-foreground/80">{s.baslik}</div>
                <div className="font-normal normal-case leading-[1.25] tracking-normal opacity-70">
                  {s.altBaslik}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {satirlar.map((satir, i) => {
            const alt = i === MAC_SAYISI - 1 ? "" : "border-b border-line/50";
            const ad = [satir.ev, satir.dep].filter(Boolean).join(" – ");
            return (
              <tr key={i}>
                <td className={cn("py-2 pr-2 text-right align-middle", alt)}>
                  <span className="tnum text-[12px] text-muted-foreground">{i + 1}</span>
                </td>
                <td className={cn("py-2 pl-2 align-middle", alt)}>
                  <div className="truncate text-[13px]">
                    {ad || <span className="text-muted-foreground/50">adsız</span>}
                  </div>
                  {satir.lig ? (
                    <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                      {satir.lig}
                    </div>
                  ) : null}
                </td>
                {sutunlar.map((s) => (
                  <td
                    key={s.anahtar}
                    className={cn("border-l border-line/50 py-2 pl-2 align-middle", alt)}
                  >
                    <Hucre hucre={s.hucreler[i]} />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Hucre({ hucre }: { hucre: SutunHucresi | undefined }) {
  if (!hucre) return null;
  if (!hucre.semboller.length) {
    return (
      <span className="text-[11.5px] text-danger">
        {hucre.bosMetni ?? "işaret yok"}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1">
      {SEMBOLLER.map((sem) => {
        const secili = hucre.semboller.includes(sem);
        return (
          <span
            key={sem}
            className={cn(
              "inline-flex h-6 w-6 items-center justify-center rounded-md border",
              "font-mono text-[12px] font-semibold",
              secili ? SECILI[sem] : "border-line/60 text-muted-foreground/40",
            )}
          >
            {sem}
          </span>
        );
      })}
      <span
        className="ml-1 whitespace-nowrap text-[10px] uppercase tracking-[0.04em] text-muted-foreground"
        title={hucre.ipucu}
      >
        {hucre.etiket}
      </span>
      {(hucre.uyarilar ?? []).map((u) => (
        <span key={u.metin} className="text-[10.5px] text-warning" title={u.ipucu}>
          {u.metin}
        </span>
      ))}
    </span>
  );
}

/** Seviyeden okunur etiket — iki kaynak da aynı kelimeyi kullansın diye. */
export const SEVIYE_ADI: Record<number, string> = {
  1: "banko",
  2: "çift",
  3: "üçlü",
};
