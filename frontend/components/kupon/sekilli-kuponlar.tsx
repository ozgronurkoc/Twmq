"use client";

import * as React from "react";

import { CIZGI_ADI, type KuponSatiri } from "@/lib/kupon";
import { kuponBedeli } from "@/lib/kupon-kur";
import { HEDEF_KACAK, type SekilliKupon } from "@/lib/kupon-sekil";
import { MAC_SAYISI, SEMBOLLER, type Cizgi, type Sembol } from "@/lib/types";
import { cn, sayi, yuzde } from "@/lib/utils";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

/**
 * Sekilli kuponlar — acilis ve kapanis, her biri iki sekil.
 *
 * ─── Neden tek tablo, neden dort ayri kart ───────────────────────────────
 *
 * Dort kupon ayni 15 maci isaretliyor ve okunacak asil sey FARKLARI: hangi
 * mac acilista banko, kapanista uclu oldu; hangisi iki sekilde de banko
 * kaldi. Dort ayri kart bu karsilastirmayi imkansiz kilardi — `izgara`da
 * ayni gerekceyle tablo secilmisti.
 *
 * Her hucrede uc sembol de yaziyor, isaretlenenler vurgulu. Isaretlenmeyeni
 * silmek "neden bu isaret" sorusunu ekrandan kaldirirdi: bir bankoyu banko
 * yapan sey, otekilerin ne kadar geride kaldigidir.
 */

const SECILI: Record<Sembol, string> = {
  "1": "bg-sym-1 text-white border-sym-1",
  "0": "bg-sym-0 text-white border-sym-0",
  "2": "bg-sym-2 text-white border-sym-2",
};

const SEVIYE_ADI: Record<1 | 2 | 3, string> = {
  1: "banko",
  2: "çift",
  3: "üçlü",
};

/** Ekranda bir kupon: hangi cizgiden cikti ve ne. */
export interface KuponGirdisi {
  cizgi: Cizgi;
  kupon: SekilliKupon;
  /** Analiz o cizgide kac satirda karne bulabildi (damga icin). */
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
  const toplamBedel = kuponBedeli(toplamKolon, kolonBedeliTl);

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "grid gap-3",
          kuponlar.length >= 4 ? "sm:grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-2",
        )}
      >
        {kuponlar.map((g) => (
          <OzetKutusu key={`${g.cizgi}-${g.kupon.sekil.anahtar}`} girdi={g} kolonBedeliTl={kolonBedeliTl} />
        ))}
      </div>

      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-line px-3 py-2.5 text-[12px]">
        <span className="text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
          {kuponlar.length} kupon toplamı
        </span>
        <span className="tnum font-semibold">{sayi(toplamKolon)} kolon</span>
        <span className="tnum font-semibold">
          {toplamBedel == null ? "—" : `₺${sayi(toplamBedel)}`}
        </span>
        {toplamBedel != null && haftalikTavanTl ? (
          <span
            className={cn(
              "tnum",
              toplamBedel > haftalikTavanTl ? "text-danger" : "text-success",
            )}
          >
            haftalık tavanın {(toplamBedel / haftalikTavanTl).toFixed(2)}×&apos;i
            {" "}(₺{sayi(haftalikTavanTl)})
          </span>
        ) : null}
      </div>

      <div className={TABLO_SARMAL}>
        {/*
          En az genislik KUPON SAYISINA bagli: `table-fixed` hucreyi icerige
          gore buyutmez, tasan sey kirpilir. Bir kupon sutunu uc sembol
          kutusu + seviye etiketi tasiyor (~142 piksel); dort kuponda sabit
          bir 980 piksel son sutunu kesiyordu.
        */}
        <table
          className="w-full table-fixed border-separate border-spacing-0"
          style={{ minWidth: `${300 + 142 * kuponlar.length}px` }}
        >
          <colgroup>
            <col className="w-[4%]" />
            <col className="w-[25%]" />
            {kuponlar.map((g) => (
              <col key={`${g.cizgi}-${g.kupon.sekil.anahtar}`} style={{ width: `${71 / kuponlar.length}%` }} />
            ))}
          </colgroup>
          <thead>
            <tr className={cn(TABLO_BASLIK_SATIRI, "[&>th]:whitespace-nowrap")}>
              <th className="pb-2 pr-2 text-right font-medium">#</th>
              <th className="pb-2 pl-2 text-left font-medium">Maç</th>
              {kuponlar.map((g) => (
                <th
                  key={`${g.cizgi}-${g.kupon.sekil.anahtar}`}
                  // Sekil adi KENDI satirinda ve sarabilir: tek satirda
                  // "Kapanış 5 banko · 5 çift · 5 üçlü" son sutunda
                  // kirpiliyordu (baslik satiri `nowrap`).
                  className="whitespace-normal border-l border-line/50 pb-2 pl-2 text-left font-medium align-bottom"
                >
                  <div className="text-foreground/80">{CIZGI_ADI[g.cizgi]}</div>
                  <div className="font-normal normal-case leading-[1.25] tracking-normal opacity-70">
                    {g.kupon.sekil.ad}
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
                  {kuponlar.map((g) => {
                    const s = g.kupon.satirlar[i];
                    return (
                      <td
                        key={`${g.cizgi}-${g.kupon.sekil.anahtar}`}
                        className={cn("border-l border-line/50 py-2 pl-2 align-middle", alt)}
                      >
                        {s ? <Isaretler satir={s} /> : null}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Isaretler({ satir }: { satir: SekilliKupon["satirlar"][number] }) {
  if (satir.kaynak === "yok") {
    return <span className="text-[11.5px] text-danger">karne yok</span>;
  }
  return (
    <span className="flex items-center gap-1">
      {SEMBOLLER.map((sem) => {
        const secili = satir.semboller.includes(sem);
        return (
          <span
            key={sem}
            className={cn(
              "inline-flex h-6 w-6 items-center justify-center rounded-md border",
              "font-mono text-[12px] font-semibold",
              secili
                ? SECILI[sem]
                : "border-line/60 text-muted-foreground/40",
            )}
          >
            {sem}
          </span>
        );
      })}
      <span
        className="ml-1 whitespace-nowrap text-[10px] uppercase tracking-[0.04em] text-muted-foreground"
        title={
          satir.kacak == null
            ? `${satir.derece}. derece`
            : `${satir.derece}. derece — bu seviyede kaçma olasılığı ${yuzde(satir.kacak)}`
        }
      >
        {SEVIYE_ADI[satir.seviye]}
      </span>
      {satir.kaynak === "piyasa" ? (
        <span
          className="text-[10.5px] text-warning"
          title="Bu satırda karne yok; işaret PİYASADAN seçildi"
        >
          piyasa
        </span>
      ) : null}
      {satir.azOrnek ? (
        <span className="text-[10.5px] text-warning" title="Örneklem 30'un altında">
          az
        </span>
      ) : null}
    </span>
  );
}

function OzetKutusu({
  girdi,
  kolonBedeliTl,
}: {
  girdi: KuponGirdisi;
  kolonBedeliTl: number | null;
}) {
  const { cizgi, kupon } = girdi;
  const bedel = kuponBedeli(kupon.kolon, kolonBedeliTl);
  return (
    <div className="rounded-xl border border-line px-3 py-2.5">
      {/*
        Cizgi ve sekil AYRI satirda: tek satirda "Kapanış · 5 banko · 5 çift
        · 5 üçlü" dort kutunun ucunde sariyordu ve kutular farkli
        yuksekliklerde duruyordu. Sekil satiri sabit yukseklikte.
      */}
      <div className="text-[11px] uppercase tracking-[0.06em] text-muted-foreground">
        {CIZGI_ADI[cizgi]}
      </div>
      <div className="mt-0.5 min-h-[2.4em] text-[11.5px] leading-[1.2] text-muted-foreground">
        {kupon.sekil.ad}
      </div>
      <div className="tnum mt-1 text-[16px] font-semibold">
        {sayi(kupon.kolon)} kolon
      </div>
      <div className="tnum mt-0.5 text-[11.5px] text-muted-foreground">
        {bedel == null ? "bedel —" : `₺${sayi(bedel)}`}
      </div>
      <div className="mt-2 space-y-0.5 border-t border-line/60 pt-2 text-[11.5px]">
        <Satir
          etiket="15/15"
          deger={kupon.p15 == null ? "—" : yuzde(kupon.p15)}
        />
        <Satir
          etiket={`≥12 (kaçak ≤ ${HEDEF_KACAK})`}
          deger={kupon.pHedef == null ? "—" : yuzde(kupon.pHedef)}
        />
      </div>
      {kupon.eksik.length ? (
        <div className="mt-2 text-[11px] text-danger">
          {kupon.eksik.map((i) => i + 1).join(", ")}. maçta işaret yok
        </div>
      ) : null}
    </div>
  );
}

function Satir({ etiket, deger }: { etiket: string; deger: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-muted-foreground">{etiket}</span>
      <span className="tnum font-medium">{deger}</span>
    </div>
  );
}

/** Kuralin kendisi — ekranda durur, katlanmaz. */
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
      kaçarsa <span className="font-mono">p₃</span>). Üçlü hiç kaçmaz. Çift
      işaretlenen maçta seçilen iki sembol, tek kuponda olduğu gibi
      karnenin en yüksek ikilisidir. Yüzdeler <strong>karnenin kendisinden</strong>{" "}
      okunur ve maçların bağımsız olduğu varsayılır — ölçülen hafta içi
      bağımlılık bu sayıyı bir vaat değil bir <strong>sıralama ölçütü</strong>{" "}
      yapar.{" "}
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
