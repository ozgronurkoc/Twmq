"use client";

import * as React from "react";

import {
  CIZGI_ADI,
  CIZGI_SIRASI,
  favori,
  oranHucresiBozuk,
  satirMarji,
  type KuponSatiri,
  METIN_SINIR,
  ORAN_SINIR,
} from "@/lib/kupon";
import { MAC_SAYISI, SEMBOLLER, type Cizgi, type Sembol } from "@/lib/types";
import { cn, yuzde } from "@/lib/utils";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

/**
 * 15 satirlik elle giris izgarasi: lig · ev · deplasman · ACILIS 1/0/2 ·
 * KAPANIS 1/0/2.
 *
 * ─── Neden tablo, neden 15 ayri kart degil ────────────────────────────────
 *
 * Doldurulan sey bir LISTE degil bir TABLO: kullanici oranlari alt alta
 * karsilastirarak girer ("bu maca 1.26 yazdim, digeri 1.25'ti"). Kartlara
 * bolunmus bir duzen o karsilastirmayi imkansiz kilar.
 *
 * ─── Neden iki fiyat blogu ────────────────────────────────────────────────
 *
 * Sahibinin istegi: *"acilis ve kapanis oranlarini verdigimde ... acilis
 * kendi icinde 2 kupon, kapanis kendi icinde 2 kupon olacak."* Onceden tek
 * blok vardi ve hangi cizgiye ait oldugunu AYAR soyluyordu; o hal iki
 * fiyati ayni anda tutamiyordu. Iki blok YAN YANA duruyor, cunku okunacak
 * asil sey ikisinin FARKI — fiyatin nereye kaydigi.
 *
 * Bir blok bos birakilabilir: elinde yalnizca kapanis bulteni olan biri o
 * tarafi doldurur ve yalnizca kapanisin kuponlari kurulur.
 *
 * ─── Klavye ───────────────────────────────────────────────────────────────
 *
 * 135 hucre (15 x 9) yalnizca fareyle doldurulmaz. `Tab` satir boyunca
 * ilerler — tarayicinin kendi davranisi, dokunulmadi. Ok tuslari ve `Enter`
 * ise SUTUN boyunca ilerler: bulten cogu zaman sutun sutun okunur (once 15
 * ev sahibi, sonra 15 oran). `components/formul/match-grid.tsx` ayni kalibi
 * kullaniyor.
 *
 * Sol/sag oklar BILINCLI olarak bagli degil: metin kutusunda imleci
 * hareket ettirirler ve onlari kacirmak yazmayi bozar.
 */

/** Kimlik sutunlari — oranlar disindaki serbest metin alanlari. */
export type KimlikAlani = "lig" | "ev" | "dep";

const KIMLIK: readonly KimlikAlani[] = ["lig", "ev", "dep"] as const;

/**
 * Klavye gezinmesinin sutun duzeni: uc kimlik alani, sonra her cizginin uc
 * orani. `refs` bu sirayla doldurulur; sira degisirse gezinme de degisir.
 */
const SUTUN_SAYISI = KIMLIK.length + CIZGI_SIRASI.length * SEMBOLLER.length;

/** Bir oran hucresinin gezinme sutunu. */
function oranSutunu(cizgi: Cizgi, sembol: Sembol): number {
  return (
    KIMLIK.length +
    CIZGI_SIRASI.indexOf(cizgi) * SEMBOLLER.length +
    SEMBOLLER.indexOf(sembol)
  );
}

const SEMBOL_ETIKETI: Record<Sembol, string> = {
  "1": "Ev",
  "0": "Beraberlik",
  "2": "Deplasman",
};

/** Favori sembolun hucresi vurgulanir — hangi tarafin ucuz oldugu okunsun. */
const FAVORI_RENGI: Record<Sembol, string> = {
  "1": "text-sym-1",
  "0": "text-sym-0",
  "2": "text-sym-2",
};

export function KuponIzgarasi({
  satirlar,
  onKimlik,
  onOran,
}: {
  satirlar: KuponSatiri[];
  onKimlik: (mac: number, alan: KimlikAlani, deger: string) => void;
  onOran: (mac: number, cizgi: Cizgi, sembol: Sembol, deger: string) => void;
}) {
  const refs = React.useRef<(HTMLInputElement | null)[][]>([]);

  function odakla(mac: number, sut: number) {
    const m = Math.max(0, Math.min(MAC_SAYISI - 1, mac));
    const s = Math.max(0, Math.min(SUTUN_SAYISI - 1, sut));
    const hedef = refs.current[m]?.[s];
    hedef?.focus();
    hedef?.select();
  }

  function tusla(e: React.KeyboardEvent, mac: number, sut: number) {
    if (e.key === "ArrowDown" || e.key === "Enter") {
      e.preventDefault();
      odakla(mac + 1, sut);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      odakla(mac - 1, sut);
    }
  }

  return (
    <div className={TABLO_SARMAL}>
      <table className="w-full min-w-[1180px] table-fixed border-separate border-spacing-0">
        {/*
          Genislikler `colgroup`ta ve YUZDE: `table-fixed` ile birlikte bu,
          iki takim sutununu birbirine ESIT tutar. Once genislik yoktu ve
          tarayici sutunu ICERIGE gore buyutuyordu — "Manchester United"
          yazan sutun, karsisindaki "Hull City" sutunundan genis oluyor ve
          baslik satiri govdeyle ayni yerde durmuyordu.
        */}
        <colgroup>
          <col className="w-[3%]" />
          <col className="w-[7%]" />
          <col className="w-[17%]" />
          <col className="w-[17%]" />
          {CIZGI_SIRASI.map((c) => (
            <React.Fragment key={c}>
              <col className="w-[7%]" />
              <col className="w-[7%]" />
              <col className="w-[7%]" />
              <col className="w-[7%]" />
            </React.Fragment>
          ))}
        </colgroup>
        <thead>
          {/*
            Iki satirlik baslik: ust satir fiyat BLOGUNU adlandirir (acilis /
            kapanis), alt satir blogun icindeki sutunlari. Tek satirlik bir
            baslikta alti oran yan yana dururdu ve hangi ucunun acilis
            oldugu ancak sayarak anlasilirdi.
          */}
          <tr className={cn(TABLO_BASLIK_SATIRI, "[&>th]:whitespace-nowrap")}>
            <th className="pb-1 pr-2" rowSpan={2} />
            <th className="pb-1" rowSpan={2} />
            <th className="pb-1 pl-4 text-left font-medium align-bottom" rowSpan={2}>
              Ev sahibi
            </th>
            <th className="pb-1 pl-4 text-left font-medium align-bottom" rowSpan={2}>
              Deplasman
            </th>
            {CIZGI_SIRASI.map((c) => (
              <th
                key={c}
                colSpan={4}
                className="border-l border-line/50 pb-1 pl-2 text-left font-semibold text-foreground/80"
              >
                {CIZGI_ADI[c]}
              </th>
            ))}
          </tr>
          <tr className={cn(TABLO_BASLIK_SATIRI, "[&>th]:whitespace-nowrap")}>
            {CIZGI_SIRASI.map((c) =>
              [
                ...SEMBOLLER.map((s, k) => (
                  <th
                    key={`${c}-${s}`}
                    className={cn(
                      "pb-2 pr-2 text-right font-medium",
                      k === 0 && "border-l border-line/50",
                    )}
                  >
                    <span className="font-mono">{s}</span>{" "}
                    <span className="font-normal normal-case tracking-normal opacity-70">
                      {SEMBOL_ETIKETI[s]}
                    </span>
                  </th>
                )),
                <th key={`${c}-marj`} className="pb-2 pr-1 text-right font-medium">
                  Marj
                </th>,
              ],
            )}
          </tr>
        </thead>
        <tbody>
          {satirlar.map((satir, i) => {
            // 15 satirda goz kayar: her satirin altinda ince bir ayrac var,
            // sonuncusunda yok (tablonun kendi alt kenari onun yerine gecer).
            const alt = i === MAC_SAYISI - 1 ? "" : "border-b border-line/50";
            return (
              <tr key={i} className="group">
                <td className={cn("py-[3px] pl-1 pr-2 text-right align-middle", alt)}>
                  <span className="tnum text-[12px] text-muted-foreground">{i + 1}</span>
                </td>

                <Hucre
                  kutu={alt}
                  ref={(el) => kaydet(refs, i, 0, el)}
                  deger={satir.lig}
                  yerTutucu={i === 0 ? "T1" : ""}
                  sinir={METIN_SINIR}
                  hizala="orta"
                  onChange={(v) => onKimlik(i, "lig", v)}
                  onKeyDown={(e) => tusla(e, i, 0)}
                  etiket={`${i + 1}. maçın ligi`}
                />
                <Hucre
                  kutu={alt}
                  ref={(el) => kaydet(refs, i, 1, el)}
                  deger={satir.ev}
                  yerTutucu={i === 0 ? "Beşiktaş" : ""}
                  sinir={METIN_SINIR}
                  onChange={(v) => onKimlik(i, "ev", v)}
                  onKeyDown={(e) => tusla(e, i, 1)}
                  etiket={`${i + 1}. maçın ev sahibi`}
                />
                <Hucre
                  kutu={alt}
                  ref={(el) => kaydet(refs, i, 2, el)}
                  deger={satir.dep}
                  yerTutucu={i === 0 ? "Erzurumspor" : ""}
                  sinir={METIN_SINIR}
                  onChange={(v) => onKimlik(i, "dep", v)}
                  onKeyDown={(e) => tusla(e, i, 2)}
                  etiket={`${i + 1}. maçın deplasmanı`}
                />

                {CIZGI_SIRASI.map((c) => {
                  const marj = satirMarji(satir, c);
                  const fav = favori(satir, c);
                  return (
                    <React.Fragment key={c}>
                      {SEMBOLLER.map((s, k) => (
                        <Hucre
                          key={s}
                          // Fiyat blogu kimlik blogundan (ve oteki fiyat
                          // blogundan) ince bir cizgiyle ayrilir: "Deplasman"
                          // sutunu genis ve bitisigindeki 1 orani ona ait
                          // sanilabiliyordu.
                          kutu={cn(alt, k === 0 && "border-l border-line/50")}
                          ref={(el) => kaydet(refs, i, oranSutunu(c, s), el)}
                          deger={satir.oran[c][s]}
                          yerTutucu={i === 0 ? ORNEK_ORAN[c][s] : ""}
                          sinir={ORAN_SINIR}
                          sayisal
                          bozuk={oranHucresiBozuk(satir.oran[c][s])}
                          vurgu={fav === s ? FAVORI_RENGI[s] : undefined}
                          onChange={(v) => onOran(i, c, s, v)}
                          onKeyDown={(e) => tusla(e, i, oranSutunu(c, s))}
                          etiket={`${i + 1}. maçın ${CIZGI_ADI[c].toLocaleLowerCase("tr")} ${s} oranı`}
                        />
                      ))}
                      <td className={cn("py-[3px] pl-2 pr-1 text-right align-middle", alt)}>
                        <span
                          className={cn(
                            "tnum text-[12px]",
                            marj == null
                              ? "text-muted-foreground/50"
                              : marj > 0.12
                                ? "text-warning"
                                : "text-muted-foreground",
                          )}
                          title={
                            marj == null
                              ? "Üç oran da girilince marj burada görünür"
                              : marj > 0.12
                                ? "Korpus ~%7 marjlı; bu farkta arındırma yöntemi sonucu görünür biçimde değiştirir"
                                : undefined
                          }
                        >
                          {marj == null ? "—" : yuzde(marj)}
                        </span>
                      </td>
                    </React.Fragment>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Ilk satirda gosterilen ornek oran — 5. haftanin 1. maci (Pinnacle).
 *
 * Iki cizgi ayri ayri yaziyor ve sayilar BIREBIR o haftanin kaydindan
 * (`data/super_toto/2026_27/hafta_05.json`): yer tutucu bile uydurulmus bir
 * fiyat gostermemeli.
 */
const ORNEK_ORAN: Record<Cizgi, Record<Sembol, string>> = {
  acilis: { "1": "1.28", "0": "5.53", "2": "10.16" },
  kapanis: { "1": "1.26", "0": "6.48", "2": "13.54" },
};

function kaydet(
  refs: React.MutableRefObject<(HTMLInputElement | null)[][]>,
  mac: number,
  sut: number,
  el: HTMLInputElement | null,
) {
  const satir = refs.current[mac] ?? [];
  satir[sut] = el;
  refs.current[mac] = satir;
}

/**
 * Tek hucre. Kenarlik hucrenin KENDISINDE degil, odaklandiginda beliren bir
 * halkada: 135 kutuluk bir izgarada 135 cerceve cizmek tabloyu okunmaz yapar.
 */
const Hucre = React.forwardRef<
  HTMLInputElement,
  {
    deger: string;
    onChange: (v: string) => void;
    onKeyDown: (e: React.KeyboardEvent) => void;
    etiket: string;
    yerTutucu?: string;
    sinir: number;
    sayisal?: boolean;
    bozuk?: boolean;
    vurgu?: string;
    hizala?: "orta";
    /** Hucrenin kendi `td` sinifi — satir/sutun ayraclari buradan gelir. */
    kutu?: string;
  }
>(function Hucre(
  { deger, onChange, onKeyDown, etiket, yerTutucu, sinir, sayisal, bozuk, vurgu, hizala, kutu },
  ref,
) {
  return (
    <td className={cn("py-[3px] pl-2 align-middle", kutu)}>
      <input
        ref={ref}
        type="text"
        value={deger}
        aria-label={etiket}
        aria-invalid={bozuk}
        placeholder={yerTutucu}
        maxLength={sinir}
        spellCheck={false}
        inputMode={sayisal ? "decimal" : undefined}
        // Ondalik ayirici olarak virgul yazmak Turkce klavyede refleks;
        // sunucu ve `Number()` nokta bekler. Cevirme GIRISTE yapilir ki
        // kullanici yazdiginin kabul edildigini aninda gorsun.
        onChange={(e) => onChange(sayisal ? e.target.value.replace(",", ".") : e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={(e) => e.currentTarget.select()}
        className={cn(
          "h-9 w-full rounded-lg border bg-transparent px-2 text-[13px]",
          "transition-shadow duration-150 ease-smooth",
          "placeholder:text-muted-foreground/40",
          "focus:border-primary/40 focus:bg-background focus:outline-none focus:ring-2 focus:ring-primary/40",
          sayisal && "tnum text-right",
          hizala === "orta" && "text-center font-mono text-[12.5px]",
          bozuk ? "border-danger" : "border-transparent hover:border-line",
          vurgu && !bozuk && "font-semibold",
          vurgu,
        )}
      />
    </td>
  );
});
