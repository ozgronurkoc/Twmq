"use client";

import * as React from "react";
import Link from "next/link";
import { Download } from "lucide-react";

import { SEMBOLLER, type OddsSummary, type Sembol, type WeekRow } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { ResultStrip } from "@/components/ui/symbol";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

type SiraAnahtari = "week" | Sembol | "streak" | "brier" | "tarih";

const BASLIKLAR: Array<{ key: SiraAnahtari; etiket: string; baslik: string }> = [
  { key: "week", etiket: "Hf", baslik: "Hafta" },
  { key: "1", etiket: "1", baslik: "Ev sahibi" },
  { key: "0", etiket: "0", baslik: "Beraberlik" },
  { key: "2", etiket: "2", baslik: "Deplasman" },
  { key: "streak", etiket: "Seri", baslik: "Hafta içindeki en uzun aynı-sembol serisi" },
];

type BrierSatiri = OddsSummary["weekly_brier"][number];

/**
 * Varsayılan olarak gösterilen satır sayısı (§6.8 G1).
 *
 * Sayfa bölünürken kabul kriteri *"her sayfa < 3.500 px"*di ve 41 satırlık
 * tam tablo tek başına o bütçenin yarısını yiyordu. Kural 2 ("her görselin
 * tablo karşılığı vardır") **bozulmuyor**: veri kaybolmuyor, bir tık uzağa
 * gidiyor — ve CSV zaten görünen değil **süzülen tüm** satırları veriyor.
 */
const VARSAYILAN_SATIR = 12;

/** `"2023_24"` -> `"2023/24"`; varsayılan kayıt kendi adıyla anılır. */
function kayitEtiketi(sezon: string | null): string {
  if (!sezon) return "varsayılan";
  const [bas, son] = sezon.split("_");
  return son ? `${bas}/${son}` : sezon;
}

/** CSV alanı: ayırıcı, tırnak ve satır sonu içeren değerler tırnaklanır. */
function csvAlan(v: string | number): string {
  const s = String(v);
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * Sayfadaki tabloyu oldugu gibi CSV'ye cevirir.
 *
 * Ayirici NOKTALI VIRGUL ve ondalik VIRGUL: Turkce yerelde Excel bunu
 * bekliyor, virgullu CSV tek sutuna yapisiyor. BOM da bu yuzden var —
 * onsuz Excel dosyayi latin-1 okuyup Turkce karakterleri bozuyor.
 */
function csvUret(rows: WeekRow[], brier: Map<string, BrierSatiri>): string {
  const basliklar = [
    "hafta", "kayit", "tarih", "sezon", "1", "0", "2", "en_uzun_seri", "seri_sembolu",
    "sonuc_dizisi", "oranli_mac", "favori_isabet", "brier", "kismi_oran",
  ];
  const satirlar = rows.map((w) => {
    const b = brier.get(w.anahtar);
    return [
      w.week,
      // Hangi KAYITTAN geldigi: birlesik kesitte dort kaydin haftalari
      // yan yana duruyor ve yalnizca numara ile ayirt edilemezler.
      w.sezon ?? "varsayilan",
      w.close_date,
      w.season,
      w.counts["1"],
      w.counts["0"],
      w.counts["2"],
      w.max_streak.length,
      w.max_streak.symbol,
      w.results,
      b ? b.n : "",
      b ? b.favourite_hit : "",
      b ? String(b.brier).replace(".", ",") : "",
      b ? (b.partial ? "evet" : "hayır") : "",
    ].map(csvAlan).join(";");
  });
  return "﻿" + [basliklar.join(";"), ...satirlar].join("\r\n") + "\r\n";
}

function csvIndir(metin: string, ad: string) {
  const blob = new Blob([metin], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = ad;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Serbest birakmayi bir sonraki tick'e birakiyoruz; hemen revoke edilirse
  // bazi tarayicilar indirmeyi baslatmadan baglantiyi kaybediyor.
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * Gorsellerin tablo karsiligi. Her grafikte okunabilen her deger burada da
 * durur — hicbir sayi yalnizca renge ya da ipucuna birakilmaz.
 */
export function WeeksTable({
  weeks,
  avg,
  brier,
  brierAvg,
  birlesik = false,
  haftaAdresi,
}: {
  weeks: WeekRow[];
  avg: Partial<Record<Sembol, number>>;
  /** Hafta ANAHTARINA göre piyasa Brier skoru; oran arşivi yoksa boş. */
  brier?: OddsSummary["weekly_brier"];
  brierAvg?: number;
  /**
   * Birleşik kesitte satır hangi kayıttan geldiğini de yazar.
   *
   * Numara tek başına yetmez: dört kaydın dördünde de 12. hafta var ve
   * tablo onları yan yana gösteriyor.
   */
  birlesik?: boolean;
  /**
   * Hafta detayının adresi — kuralı SAYFA verir, tablo kendi kurmaz.
   *
   * Bu bağlantı uzun süre sezonu hiç taşımıyordu: 2023/24 seçip bir haftaya
   * tıklayan kullanıcı **varsayılan kaydın** o numaralı haftasını görüyordu
   * ve bunu anlamasının bir yolu yoktu. (Sayfanın uçlar/seriler bağlantıları
   * sezonu taşıyordu, tablo taşımıyordu — aynı sayfada iki farklı davranış.)
   * Birleşik kesitte aynı kusur dört katına çıkardı. Kural artık tek yerde.
   */
  haftaAdresi: (week: number, sezon: string | null) => string;
}) {
  const [arama, setArama] = React.useState("");
  // Birlesik kesitte varsayilan sira TARIHTIR, hafta numarasi degil.
  // Tek kayitta ikisi ayni siradir (numara tarihle birlikte artar); dort
  // kayit yan yanayken numaraya gore siralamak "41. haftalar" diye bir
  // kume uretir ve "son 12 hafta" kisaltmasi en YENI degil en YUKSEK
  // numarali haftalari gosterirdi.
  const [sira, setSira] = React.useState<SiraAnahtari>(birlesik ? "tarih" : "week");
  const [azalan, setAzalan] = React.useState(false);
  const [tumu, setTumu] = React.useState(false);

  // Eslesme ANAHTAR uzerinden. Numaraya gore eslestirmek birlesik kesitte
  // dort sezonun 12. haftasini tek satira baglardi — ve sessizce: tablo
  // dolu gorunur, sayilar yanlis olurdu.
  const brierHarita = React.useMemo(
    () => new Map((brier ?? []).map((b) => [b.anahtar, b])),
    [brier],
  );
  const brierVar = brierHarita.size > 0;

  const satirlar = React.useMemo(() => {
    const q = arama.trim().toLowerCase();
    const suzulmus = q
      ? weeks.filter(
          (w) =>
            String(w.week).includes(q) ||
            w.close_date.toLowerCase().includes(q) ||
            w.results.includes(q) ||
            // Birlesik kesitte "2023" yazip o kaydin haftalarini suzmek
            // dogal bir beklenti; anahtar zaten sezonu tasiyor.
            w.anahtar.toLowerCase().includes(q),
        )
      : weeks;
    const deger = (w: WeekRow) =>
      sira === "tarih"
        ? 0 // siralama asagidaki kronolojik esitlik bozucuya birakilir
        : sira === "week"
        ? w.week
        : sira === "streak"
          ? w.max_streak.length
          : sira === "brier"
            ? // Oransiz haftalar siralamada en sona dussun.
              (brierHarita.get(w.anahtar)?.brier ?? -1)
            : w.counts[sira];
    // Esitlik bozucu KRONOLOJIK: birlesik kesitte hafta numarasi tekrar
    // eder ve yalnizca numaraya gore ikincil siralama dort kaydi ic ice
    // gecirirdi.
    return [...suzulmus].sort(
      (a, b) =>
        (azalan ? deger(b) - deger(a) : deger(a) - deger(b)) ||
        a.close_date.localeCompare(b.close_date) ||
        a.week - b.week,
    );
  }, [weeks, arama, sira, azalan, brierHarita]);

  function degistir(key: SiraAnahtari) {
    if (key === sira) {
      setAzalan((d) => !d);
    } else {
      setSira(key);
      // Kronolojik sutunlar ARTAN baslar (eskiden yeniye), sayisal olanlar
      // azalan (once en buyuk deger).
      setAzalan(key !== "week" && key !== "tarih");
    }
  }

  // Arama yapiliyorsa KISALTMA YOK: kullanici zaten daralmis bir kumeye
  // bakiyor ve "12 satir gosteriliyor" uyarisi orada yanlis okunurdu.
  const kisaltiliyor = !tumu && !arama.trim() && satirlar.length > VARSAYILAN_SATIR;
  // Son N hafta: siralama hafta numarasina gore ARTAN oldugunda son
  // satirlar, azalan oldugunda ilk satirlar en yenidir. Bu yuzden dilim
  // her zaman "listenin sonu" degil, "siralamanin bası"ndan alinir —
  // kullanicinin sectigi sira korunur.
  const gorunen = kisaltiliyor
    ? (sira === "week" || sira === "tarih") && !azalan
      ? satirlar.slice(-VARSAYILAN_SATIR)
      : satirlar.slice(0, VARSAYILAN_SATIR)
    : satirlar;

  const basliklar = [
    ...BASLIKLAR,
    ...(brierVar
      ? [{
          key: "brier" as SiraAnahtari,
          etiket: "Brier",
          baslik: "Piyasanın o haftaki yanılma ölçüsü — yüksek = sürprizli hafta",
        }]
      : []),
    // Tarih sutunu artik SIRALANABILIR. Birlesik kesitte varsayilan sira
    // budur ve kullanicinin ona geri donebilmesi gerekir.
    { key: "tarih" as SiraAnahtari, etiket: "Tarih", baslik: "Haftanın kapanış tarihi" },
  ];

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <input
          value={arama}
          onChange={(e) => setArama(e.target.value)}
          placeholder="Hafta, tarih veya dizi ara…"
          aria-label="Haftalarda ara"
          className={cn(
            "h-9 w-56 rounded-xl border border-line bg-background px-3 text-[13px]",
            "placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
          )}
        />
        <div className="flex items-center gap-3">
          <span className="tnum text-[11.5px] text-muted-foreground">
            {kisaltiliyor ? `${gorunen.length} / ${satirlar.length}` : satirlar.length} hafta
          </span>
          <Button
            tip="outline"
            boyut="sm"
            onClick={() =>
              csvIndir(
                csvUret(satirlar, brierHarita),
                `spor-toto-haftalar-${satirlar.length}.csv`,
              )
            }
            title="Görünen satırları CSV olarak indir (noktalı virgül ayraçlı, Excel uyumlu)"
          >
            <Download size={13} />
            CSV
          </Button>
        </div>
      </div>

      <div className={TABLO_SARMAL}>
        <table className="w-full min-w-[720px] text-[12.5px]">
          <thead>
            <tr className={TABLO_BASLIK_SATIRI}>
              {/* `aria-sort` <th>'e ait: <button> rolu bu ozniteligi
                  DESTEKLEMEZ ve ekran okuyucu siralama durumunu hic
                  duymuyordu. Oznitelik dogru elemana tasindi. */}
              {basliklar.map((h) => (
                <th
                  key={h.key}
                  scope="col"
                  className="pb-2 pr-3 font-medium"
                  aria-sort={
                    sira === h.key ? (azalan ? "descending" : "ascending") : "none"
                  }
                >
                  <button
                    type="button"
                    onClick={() => degistir(h.key)}
                    title={`${h.baslik} — sırala`}
                    className="inline-flex items-center gap-1 transition-colors hover:text-foreground"
                  >
                    {h.etiket}
                    <span aria-hidden className={sira === h.key ? "opacity-100" : "opacity-0"}>
                      {azalan ? "▾" : "▴"}
                    </span>
                  </button>
                </th>
              ))}
              <th scope="col" className="pb-2 font-medium">
                Sonuç dizisi
              </th>
            </tr>
          </thead>
          <tbody className="tnum">
            {gorunen.map((w) => {
              const b = brierHarita.get(w.anahtar);
              return (
                <tr
                  key={w.anahtar}
                  className="border-t border-line transition-colors hover:bg-muted"
                >
                  <td className="py-2 pr-3">
                    <Link
                      href={haftaAdresi(w.week, w.sezon)}
                      className="font-semibold text-primary hover:underline"
                    >
                      {w.week}
                    </Link>
                    {birlesik ? (
                      <span className="ml-1.5 text-[11px] text-muted-foreground">
                        {kayitEtiketi(w.sezon)}
                      </span>
                    ) : null}
                  </td>
                  {SEMBOLLER.map((s) => (
                    <td key={s} className="py-2 pr-3">
                      <span
                        className={cn(
                          w.counts[s] >= Math.ceil((avg[s] ?? 0) + 2) && "font-semibold",
                        )}
                      >
                        {w.counts[s]}
                      </span>
                    </td>
                  ))}
                  <td className="py-2 pr-3 text-muted-foreground">
                    {w.max_streak.length}× {w.max_streak.symbol}
                  </td>
                  {brierVar ? (
                    <td className="py-2 pr-3">
                      {b ? (
                        <span
                          className={cn(
                            brierAvg !== undefined && b.brier > brierAvg
                              ? "font-semibold text-warning"
                              : "text-muted-foreground",
                          )}
                          title={
                            `${b.n} maç · favori ${b.favourite_hit} kez tuttu` +
                            (b.partial ? " · bu haftanın bazı maçlarında oran yok" : "")
                          }
                        >
                          {b.brier.toFixed(3)}
                          {b.partial ? <span className="ml-1 text-[10px]">kısmi</span> : null}
                        </span>
                      ) : (
                        <span className="text-muted-foreground" title="Bu haftada oran yok">
                          —
                        </span>
                      )}
                    </td>
                  ) : null}
                  <td className="whitespace-nowrap py-2 pr-3 text-muted-foreground">
                    {w.close_date}
                  </td>
                  <td className="py-2">
                    <Link
                      href={haftaAdresi(w.week, w.sezon)}
                      aria-label={`${kayitEtiketi(w.sezon)} ${w.week}. hafta detayı`}
                    >
                      <ResultStrip results={w.results} />
                    </Link>
                  </td>
                </tr>
              );
            })}
            {satirlar.length === 0 ? (
              <tr>
                {/* Sutun sayisi basliklardan okunur: `basliklar` Brier
                    varken 6, yokken 5; ustune iki sabit sutun biner.
                    Sabit 9 hicbir durumda dogru degildi. */}
                <td
                  colSpan={basliklar.length + 2}
                  className="py-6 text-center text-muted-foreground"
                >
                  Eşleşen hafta yok.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {kisaltiliyor ? (
        <div className="mt-3">
          <Button tip="outline" boyut="sm" onClick={() => setTumu(true)}>
            {satirlar.length} haftanın tamamı
          </Button>
          <span className="ml-2 text-[11px] text-muted-foreground">
            Son {VARSAYILAN_SATIR} hafta gösteriliyor; CSV her zaman tamamını
            verir.
          </span>
        </div>
      ) : null}
      {!kisaltiliyor && tumu && satirlar.length > VARSAYILAN_SATIR ? (
        <div className="mt-3">
          <Button tip="ghost" boyut="sm" onClick={() => setTumu(false)}>
            Son {VARSAYILAN_SATIR} haftaya dön
          </Button>
        </div>
      ) : null}

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Kalın yazılan sayılar, sezon ortalamasının 2 üstünde kapatan haftaları işaretler.
        {brierVar ? (
          <>
            {" "}
            <strong className="text-foreground">Brier</strong>, piyasanın o haftaki yanılma
            ölçüsüdür: Σ(olasılık − gerçekleşme)². Sıfır kusursuz, 0,667 üç sembole eşit olasılık
            vermeye denk. Sezon ortalamasının
            {brierAvg !== undefined ? ` (${brierAvg.toFixed(3)})` : ""} üstünde kalan haftalar
            turuncu — piyasanın en çok yanıldığı, yani sürprizli haftalar. “Kısmi”, o haftanın
            bütün maçlarında oran bulunmadığını söyler; karşılaştırmaya girmemeli.
          </>
        ) : null}{" "}
        CSV düğmesi <strong className="text-foreground">görünen</strong> satırları indirir: arama
        ve sıralama neyi bırakıyorsa o.
      </p>
    </div>
  );
}
