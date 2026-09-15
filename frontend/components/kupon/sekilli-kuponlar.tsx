"use client";

import * as React from "react";

import { CIZGI_ADI, type KuponSatiri } from "@/lib/kupon";
import { kuponBedeli } from "@/lib/kupon-kur";
import { HEDEF_KACAK, type SekilliKupon } from "@/lib/kupon-sekil";
import type { Cizgi } from "@/lib/types";
import { cn, yuzde } from "@/lib/utils";
import {
  IsaretTablosu,
  SEVIYE_ADI,
  type KuponSutunu,
} from "@/components/kupon/isaret-tablosu";
import { KuponOzetKutusu, KuponToplami } from "@/components/kupon/kupon-ozet";

/**
 * KARNE kuponları — "bu fiyatta geçmişte ne olmuş"tan kurulanlar.
 *
 * Motor kuponlarının (`motor-kuponlari.tsx`) ikizi: aynı tabloyu çizerler
 * (`isaret-tablosu.tsx`), farklı veriden beslenirler. İkisi ayrıştığında
 * okunacak şey o ayrışmadır.
 */

/** Ekranda bir kupon: hangi çizgiden çıktı ve ne. */
export interface KuponGirdisi {
  cizgi: Cizgi;
  kupon: SekilliKupon;
  /** Analizin damgası (arşivden açılan kayıtta dolu). */
  damga: string | null;
}

export function SekilliKuponlar({
  satirlar,
  kuponlar,
  kolonBedeliTl,
  haftalikTavanTl,
}: {
  satirlar: KuponSatiri[];
  kuponlar: KuponGirdisi[];
  kolonBedeliTl: number | null;
  haftalikTavanTl: number | null;
}) {
  const toplamKolon = kuponlar.reduce((t, g) => t + g.kupon.kolon, 0);
  const sutunlar: KuponSutunu[] = kuponlar.map((g) => ({
    anahtar: `${g.cizgi}-${g.kupon.sekil.anahtar}`,
    baslik: CIZGI_ADI[g.cizgi],
    altBaslik: g.kupon.sekil.ad,
    hucreler: g.kupon.satirlar.map((s) => ({
      semboller: s.semboller,
      etiket: SEVIYE_ADI[s.seviye] ?? "",
      ipucu:
        s.kacak == null
          ? `${s.derece}. derece`
          : `${s.derece}. derece — bu seviyede kaçma olasılığı ${yuzde(s.kacak)}`,
      uyarilar: [
        ...(s.kaynak === "piyasa"
          ? [{ metin: "piyasa", ipucu: "Bu satırda karne yok; işaret PİYASADAN seçildi" }]
          : []),
        ...(s.azOrnek
          ? [{ metin: "az", ipucu: "Örneklem 30'un altında — yüzdeler okunmaz sayılır" }]
          : []),
      ],
      bosMetni: "karne yok",
    })),
  }));

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "grid gap-3",
          kuponlar.length >= 4 ? "sm:grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-2",
        )}
      >
        {kuponlar.map((g) => (
          <KuponOzetKutusu
            key={`${g.cizgi}-${g.kupon.sekil.anahtar}`}
            ustBaslik={CIZGI_ADI[g.cizgi]}
            altBaslik={g.kupon.sekil.ad}
            kolon={g.kupon.kolon}
            bedelTl={kuponBedeli(g.kupon.kolon, kolonBedeliTl)}
            satirlar={[
              { etiket: "15/15", deger: g.kupon.p15 == null ? "—" : yuzde(g.kupon.p15) },
              {
                etiket: `≥12 (kaçak ≤ ${HEDEF_KACAK})`,
                deger: g.kupon.pHedef == null ? "—" : yuzde(g.kupon.pHedef),
              },
            ]}
            uyari={
              g.kupon.eksik.length
                ? `${g.kupon.eksik.map((i) => i + 1).join(", ")}. maçta işaret yok`
                : null
            }
          />
        ))}
      </div>

      <KuponToplami
        etiket={`${kuponlar.length} kupon toplamı`}
        kolon={toplamKolon}
        bedelTl={kuponBedeli(toplamKolon, kolonBedeliTl)}
        haftalikTavanTl={haftalikTavanTl}
      />

      <IsaretTablosu satirlar={satirlar} sutunlar={sutunlar} />
    </div>
  );
}

/** Kuralın kendisi — ekranda durur, katlanmaz. */
export function SekilAciklamasi({ kuponlar }: { kuponlar: KuponGirdisi[] }) {
  const piyasali = new Set<number>();
  const azli = new Set<number>();
  kuponlar.forEach((g) => {
    g.kupon.piyasadanSecilen.forEach((i) => piyasali.add(i));
    g.kupon.azOrnekli.forEach((i) => azli.add(i));
  });
  const liste = (k: Set<number>) =>
    [...k].sort((a, b) => a - b).map((i) => i + 1).join(", ");

  return (
    <p className="text-[11.5px] leading-relaxed text-muted-foreground">
      Kural: 15 maç <strong>karneye göre derecelendirilir</strong> — en fazla
      tekten (banko) en çok üçlüye doğru. Banko sırası{" "}
      <strong>en yüksek sembolün oranına</strong> bakar (banko kaçarsa{" "}
      <span className="font-mono">1 − p₁</span>), kalanlar arasındaki
      çift/üçlü sırası <strong>en düşük sembolün oranına</strong> bakar (çift
      kaçarsa <span className="font-mono">p₃</span>). Üçlü hiç kaçmaz.
      Yüzdeler <strong>karnenin kendisinden</strong> okunur ve maçların
      bağımsız olduğu varsayılır — ölçülen hafta içi bağımlılık bu sayıyı bir
      vaat değil bir <strong>sıralama ölçütü</strong> yapar. Aynı 15 maçın{" "}
      <strong>motor kuponları</strong> ayrı bir karttadır ve ayrı bir soruya
      cevap verir; ikisinin ayrışması okunacak şeydir.{" "}
      {piyasali.size ? (
        <>
          {liste(piyasali)}. maçta karne yok; işaret <strong>piyasadan</strong>{" "}
          seçildi.{" "}
        </>
      ) : null}
      {azli.size ? (
        <>
          {liste(azli)}. maçta örneklem 30&apos;un altında — o satırın
          yüzdeleri okunmaz sayılır, derece yine de bu sıradan çıktı.
        </>
      ) : null}
    </p>
  );
}
