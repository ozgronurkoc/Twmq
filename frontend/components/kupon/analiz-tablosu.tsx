"use client";

import * as React from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";

import { oranAnaliziAdresi, type AnalizAyari, type SatirAnalizi } from "@/lib/kupon-analiz";
import type { KuponSatiri } from "@/lib/kupon";
import {
  MAC_SAYISI,
  SEMBOLLER,
  type BenzerSembol,
  type Cizgi,
  type Sembol,
} from "@/lib/types";
import { cn, sayi, yuzde } from "@/lib/utils";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

/**
 * 15 satirin karnesi — *"bu fiyatta gecmiste ne olmus"* tablo halinde.
 *
 * ─── Her hucrede IKI sayi var ve ikisi de gerekli ─────────────────────────
 *
 * Ustteki KARNE (benzer maclarin ampirik orani), alttaki PIYASA (ayni
 * fiyatin marj arindirilmis olasiligi). Tek basina hicbiri okunmaz:
 * "bu oranda %58 ev sahibi" carpici gorunur ama piyasa zaten %56 diyorsa
 * ortada bulgu yoktur. Fiyatin tasidigi bilgi ikisinin FARKIDIR.
 *
 * ─── Fark ne zaman isaretleniyor ──────────────────────────────────────────
 *
 * Yalnizca piyasa, ampirik %95 araligin DISINDA kaldiginda. Yuzde farki
 * buyuk gorunup aralik iceride kalabilir — o zaman fark orneklemin
 * gurultusudur ve isaretlenmesi yanlis olur. Bu, `benzer`in kendi
 * `piyasa_ga_icinde` bayragidir; arayuz kendi esigini UYDURMAZ.
 *
 * ─── Az orneklem gizlenmez, SOYLENIR ──────────────────────────────────────
 *
 * `yeterli=false` (n < 30) olan satirin yuzdeleri soluk basilir ve n
 * uyarilir. Satir tablodan DUSURULMEZ: "bu fiyatta yeterli gecmis yok"
 * kuponu kuran icin bir bilgidir, eksiklik degil.
 */
export function AnalizTablosu({
  satirlar,
  sonuclar,
  ayar,
  cizgi,
}: {
  satirlar: KuponSatiri[];
  sonuclar: SatirAnalizi[];
  ayar: AnalizAyari;
  /** Tablonun okudugu fiyat cizgisi — satirdaki oran bloku de buradan. */
  cizgi: Cizgi;
}) {
  return (
    <div className={TABLO_SARMAL}>
      <table className="w-full min-w-[900px] table-fixed border-separate border-spacing-0">
        <colgroup>
          <col className="w-[4%]" />
          <col className="w-[30%]" />
          <col className="w-[13%]" />
          <col className="w-[15%]" />
          <col className="w-[15%]" />
          <col className="w-[15%]" />
          <col className="w-[8%]" />
        </colgroup>
        <thead>
          <tr className={cn(TABLO_BASLIK_SATIRI, "[&>th]:whitespace-nowrap")}>
            <th className="pb-2 pr-2 text-right font-medium">#</th>
            <th className="pb-2 pl-2 font-medium">Maç</th>
            <th className="pb-2 pr-2 text-right font-medium">Örneklem</th>
            {SEMBOLLER.map((s, k) => (
              <th
                key={s}
                className={cn(
                  "pb-2 pr-2 text-right font-medium",
                  k === 0 && "border-l border-line/50",
                )}
              >
                {s}
              </th>
            ))}
            <th className="pb-2 pr-1 text-right font-medium">Ayrıntı</th>
          </tr>
        </thead>
        <tbody>
          {satirlar.map((satir, i) => {
            const sonuc = sonuclar[i] ?? { durum: "bos", veri: null, hata: null };
            const alt = i === MAC_SAYISI - 1 ? "" : "border-b border-line/50";
            const veri = sonuc.veri;
            const yeterli = veri?.toplam.yeterli ?? false;
            const ad = [satir.ev, satir.dep].filter(Boolean).join(" – ");

            return (
              <tr key={i}>
                <td className={cn("py-2 pr-2 text-right align-top", alt)}>
                  <span className="tnum text-[12px] text-muted-foreground">{i + 1}</span>
                </td>

                <td className={cn("py-2 pl-2 align-top", alt)}>
                  <div className="truncate text-[13px]">{ad || <Bos />}</div>
                  <div className="tnum mt-0.5 text-[11px] text-muted-foreground">
                    {satir.lig ? <span className="font-mono">{satir.lig}</span> : null}
                    {satir.lig ? " · " : ""}
                    {SEMBOLLER.map((s) => satir.oran[cizgi][s]).join(" / ")}
                  </div>
                </td>

                <td className={cn("py-2 pr-2 text-right align-top", alt)}>
                  <Orneklem sonuc={sonuc} />
                </td>

                {SEMBOLLER.map((s, k) => (
                  <td
                    key={s}
                    className={cn(
                      "py-2 pr-2 text-right align-top",
                      alt,
                      k === 0 && "border-l border-line/50",
                    )}
                  >
                    <SembolHucresi
                      durum={sonuc.durum}
                      sembol={veri?.toplam.semboller[s] ?? null}
                      yeterli={yeterli}
                    />
                  </td>
                ))}

                <td className={cn("py-2 pr-1 text-right align-top", alt)}>
                  <Link
                    href={oranAnaliziAdresi(satir, ayar, cizgi)}
                    title="Bu satırı /oran-analizi'nde aç — lig kırılımı ve maçların kendisi"
                    className="inline-flex items-center gap-1 text-[11.5px] text-muted-foreground transition-colors hover:text-primary"
                  >
                    aç
                    <ExternalLink size={11} />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Bos() {
  return <span className="text-muted-foreground/50">adsız</span>;
}

/** Bulunan mac sayisi + fiilen kullanilan yaricap. */
function Orneklem({ sonuc }: { sonuc: SatirAnalizi }) {
  if (sonuc.durum === "kosuyor") {
    return <span className="text-[11.5px] text-muted-foreground">aranıyor…</span>;
  }
  if (sonuc.durum === "hata") {
    return (
      <span className="text-[11.5px] text-danger" title={sonuc.hata ?? undefined}>
        hata
      </span>
    );
  }
  const v = sonuc.veri;
  if (!v) return <span className="text-[12px] text-muted-foreground/50">—</span>;

  const yaricap = `±${(100 * v.tolerans).toFixed(1)} puan`;
  return (
    <div>
      <div
        className={cn(
          "tnum text-[13px]",
          v.toplam.yeterli ? "font-medium" : "text-warning",
        )}
      >
        {sayi(v.toplam.n)}
        {v.toplam.yeterli ? "" : " ⚠"}
      </div>
      <div
        className={cn(
          "tnum mt-0.5 text-[11px]",
          v.tolerans_tavana_dayandi ? "text-warning" : "text-muted-foreground",
        )}
        title={
          v.tolerans_tavana_dayandi
            ? "Yarıçap tavana dayandı: örneklem 'benzer' maçlardan değil SINIRDAN toplandı"
            : v.tolerans_genisledi
              ? "Hedef örnekleme ulaşmak için yarıçap genişletildi"
              : "Fiilen kullanılan yarıçap"
        }
      >
        {yaricap}
        {/*
          Once burada `⌁` duruyordu ve ekranda tireden ayirt edilemiyordu —
          yani en onemli uyari, "bu ornek benzer maclardan degil SINIRDAN
          toplandi", sessizce okunmuyordu. Isaret yerine kelime.
        */}
        {v.tolerans_tavana_dayandi ? " tavan" : ""}
      </div>
    </div>
  );
}

/**
 * Tek sembolun hucresi: ustte karne, altta piyasa.
 *
 * Sapma isareti (nokta) `piyasa_ga_icinde === false` ile basilir; `null`
 * (ornek yok) sapma SAYILMAZ.
 */
function SembolHucresi({
  durum,
  sembol,
  yeterli,
}: {
  durum: SatirAnalizi["durum"];
  sembol: BenzerSembol | null;
  yeterli: boolean;
}) {
  if (durum !== "bitti" || !sembol) {
    return <span className="text-[12px] text-muted-foreground/40">—</span>;
  }
  const sapiyor = sembol.piyasa_ga_icinde === false;
  const aralik =
    sembol.oran == null
      ? "örnek yok"
      : `%95 aralık: ${yuzde(sembol.ga_alt)} – ${yuzde(sembol.ga_ust)}`;

  return (
    <div
      title={
        `Karne: ${sayi(sembol.adet)} maç bu sembolle bitti (${aralik})\n` +
        `Piyasa: ${yuzde(sembol.piyasa)} — girilen oranın marj arındırılmış hâli`
      }
    >
      <div className="flex items-baseline justify-end gap-1.5">
        <span
          className={cn(
            "tnum text-[13px]",
            !yeterli && "text-muted-foreground",
            sapiyor && yeterli && "font-semibold text-primary",
          )}
        >
          {sapiyor ? <span aria-hidden>• </span> : null}
          {sembol.oran == null ? "—" : yuzde(sembol.oran)}
        </span>
        {/*
          Yuzdenin KAC MACA denk geldigi. Yuzde tek basina okunamaz: aynı
          %40, 4 macta da 400 macta da %40'tir ve ikisi ayni sey degildir.
          Sayi satirin `n`iyle birlikte okunur (Orneklem sutunu); ucunun
          toplami n'i verir.
        */}
        <span className="tnum text-[11px] text-muted-foreground/70">
          {sayi(sembol.adet)}
        </span>
      </div>
      {/*
        Once burada yalnizca `p` yaziyordu ve ne oldugu ancak tablonun
        altindaki aciklamadan anlasiliyordu — yani okunmuyordu. Kisaltma
        yerine kelime.
      */}
      <div className="tnum mt-0.5 text-[11px] text-muted-foreground">
        piyasa {yuzde(sembol.piyasa)}
      </div>
    </div>
  );
}

/** Tablonun altinda duran okuma kilavuzu — sayilar kendini anlatmaz. */
export function TabloAciklamasi({ sapanVar }: { sapanVar: boolean }) {
  return (
    <p className="text-[11.5px] leading-relaxed text-muted-foreground">
      Her hücrede üstteki sayı <strong>karne</strong> — aynı fiyattaki geçmiş
      maçların yüzde kaçı o sembolle bitmiş; yanındaki küçük sayı bunun{" "}
      <strong>kaç maça</strong> denk geldiği (üçünün toplamı satırın
      örneklemini verir). Alttaki <strong>piyasa</strong>, girdiğiniz oranın
      marj arındırılmış hâli — yani bültenin o sembole verdiği olasılık.
      Fiyatın taşıdığı bilgi ikisinin farkıdır.{" "}
      {sapanVar ? (
        <>
          <span className="text-primary">•</span> işareti, piyasanın ampirik %95
          aralığın <strong>dışında</strong> kaldığı sembolü gösterir — yalnızca
          orada fark örneklem gürültüsüyle açıklanamıyor.
        </>
      ) : (
        <>
          Hiçbir sembolde piyasa, ampirik %95 aralığın dışında kalmadı — yani bu
          tabloda karne ile piyasa <strong>ayrışmıyor</strong>.
        </>
      )}{" "}
      <span className="text-warning">⚠</span> az örneklem (n &lt; 30, yüzde
      okunmaz); yarıçapın yanındaki <span className="text-warning">tavan</span>{" "}
      yazısı, örneklemin &quot;benzer&quot; maçlardan değil{" "}
      <strong>sınırdan</strong> toplandığını söyler.
    </p>
  );
}
