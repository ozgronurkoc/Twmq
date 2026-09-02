"use client";

import * as React from "react";
import { RefreshCw } from "lucide-react";

import { ARINDIRMA_YONTEMLERI, getPazar, type ArindirmaYontemi } from "@/lib/api";
import { useIstek } from "@/lib/istek";
// `yuzde` BURADA YENIDEN YAZILMISTI ve kanonik govdeden zayifti:
// yalnizca `v == null` eliyordu, `NaN`/`Infinity` elemiyordu — yani
// kapsanmayan bir banttaki bolme ekrana "%NaN" basardi. `/api/pazar`
// tam da null tasiyan uc (`handikap.brier` tanim geregi null).
// `lib/utils.ts:12` bu tekillestirmenin yapildigini yaziyordu; bir
// kopya hayatta kalmisti.
import { yuzde } from "@/lib/utils";
import type { PazarOzeti } from "@/lib/types";
import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  SectionTitle,
  Skeleton,
  Stat,
} from "@/components/ui/primitives";



/**
 * Bir bandın etiketi **eksene göre** okunur. Alt/üstte olasılık,
 * handikapta çizgi büyüklüğü — aynı alan adı, farklı anlam. Sunucu bunu
 * `bant_ekseni` ile söylüyor ve arayüz tahmin etmiyor.
 */
function bantEtiketi(ozet: PazarOzeti, lo: number, hi: number) {
  if (ozet.bant_ekseni === "olasilik") {
    return `${yuzde(lo, 0)}–${yuzde(Math.min(hi, 1), 0)}`;
  }
  return hi > 9 ? `|h| ≥ ${lo.toFixed(2)}` : `|h| ${lo.toFixed(2)}–${hi.toFixed(2)}`;
}

function PazarKarti({
  baslik,
  aciklama,
  ozet,
  gercekBaslik,
}: {
  baslik: string;
  aciklama: string;
  ozet: PazarOzeti;
  gercekBaslik: string;
}) {
  return (
    <Card>
      <CardHeader title={baslik} hint={aciklama} />
      <CardBody className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat etiket="Maç" deger={String(ozet.n)} />
          <Stat etiket="Kapsama" deger={yuzde(ozet.kapsama)} />
          <Stat etiket="Marj" deger={yuzde(ozet.marj, 2)} />
          <Stat
            etiket="Brier"
            deger={ozet.brier == null ? "yok" : ozet.brier.toFixed(4)}
          />
        </div>

        {ozet.brier == null && ozet.brier_yok_sebep ? (
          <Callout ton="primary" baslik="Brier neden yok">
            {ozet.brier_yok_sebep}. Yerine <strong>beklenen getiri
            kalibrasyonu</strong> ölçülüyor: modelin dediği ortalama kapama
            olasılığı ile gerçekleşen ortalama getiri.
          </Callout>
        ) : null}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-[13px]">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border/60 text-left">
                <th className="py-2 pr-3 font-medium">
                  {ozet.bant_ekseni === "olasilik" ? "Olasılık bandı" : "Çizgi"}
                </th>
                <th className="py-2 pr-3 text-right font-medium">n</th>
                <th className="py-2 pr-3 text-right font-medium">Piyasa</th>
                <th className="py-2 pr-3 text-right font-medium">{gercekBaslik}</th>
                <th className="py-2 pr-3 text-right font-medium">Fark</th>
                <th className="py-2 text-right font-medium">%95 aralık</th>
              </tr>
            </thead>
            <tbody>
              {ozet.bantlar.map((b) => (
                <tr key={`${b.lo}-${b.hi}`} className="border-b border-border/30">
                  <td className="py-2 pr-3 tabular-nums">
                    {bantEtiketi(ozet, b.lo, b.hi)}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">{b.n}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {yuzde(b.piyasa)}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {yuzde(b.gercek)}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {b.fark >= 0 ? "+" : ""}
                    {(100 * b.fark).toFixed(1)}
                  </td>
                  <td className="py-2 text-right tabular-nums text-muted-foreground">
                    [{yuzde(b.ga_alt)}, {yuzde(b.ga_ust)}]
                    {b.piyasa_ga_icinde ? "" : " ⚠"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-[12px] leading-relaxed text-muted-foreground">
          <strong>{ozet.sapan_bant}</strong> / {ozet.bantlar.length} bantta
          piyasanın söylediği sayı %95 aralığının dışında. Aralığın içinde
          kalmak, piyasanın o bantta <em>sözünü tuttuğu</em> anlamına gelir.
        </p>
      </CardBody>
    </Card>
  );
}

/**
 * 1X2 dışı pazarlar.
 *
 * Bu sayfa uzun süre **yoktu** ve sebebi bir ürün kararıydı: *"diğer
 * pazarlar analiz içindir, arşivde kalır."* O kısıt kalktı. Kalkmayan
 * kural sayfanın kuruluşunu belirliyor: her pazarın **ölçümü** tablosunun
 * üstünde durur ve kesitin sınırı katlanmaz.
 */
export default function PazarlarSayfasi() {
  const [arindirma, setArindirma] = React.useState<ArindirmaYontemi>("shin");
  const { veri, hata, yukleniyor, yenile } = useIstek(
    (signal) => getPazar(arindirma, signal),
    [arindirma],
    { varsayilanHata: "Pazar verisi alınamadı" },
  );

  return (
    <div className="mx-auto w-full max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Pazarlar</h1>
          <p className="mt-1 max-w-[62ch] text-[13px] leading-relaxed text-muted-foreground">
            1X2 dışındaki iki fiyat: <strong>alt/üst 2,5</strong> ve{" "}
            <strong>Asya handikabı</strong>. İkisi de marj arındırılmış piyasa
            fiyatıdır — bir model değil. Yanlarında her zaman bu fiyatların{" "}
            <strong>ölçülmüş</strong> kalibrasyonu durur.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Marj arındırma yöntemi"
            className="h-9 rounded-md border border-border bg-background px-2 text-[13px]"
            value={arindirma}
            onChange={(e) => setArindirma(e.target.value as ArindirmaYontemi)}
          >
            {ARINDIRMA_YONTEMLERI.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <Button tip="ghost" onClick={yenile} aria-label="Yenile">
            <RefreshCw size={15} />
          </Button>
        </div>
      </div>

      {hata ? <Callout ton="danger" baslik="Hata">{hata}</Callout> : null}

      {veri ? (
        <Callout ton="warning" baslik="Kesitin sınırı">
          {veri.sinir}
        </Callout>
      ) : null}

      {yukleniyor && !veri ? (
        <div className="space-y-4">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : null}

      {veri ? (
        <>
          <SectionTitle>Alt / üst {veri.alt_ust.n ? "2,5" : ""}</SectionTitle>
          <PazarKarti
            baslik="Alt / üst 2,5"
            aciklama={
              `Temiz ikili olay: 2,5 yarım çizgidir, iade yoktur. ` +
              `Üst gelen maç oranı ${yuzde(veri.alt_ust.ust_orani)}.`
            }
            ozet={veri.alt_ust}
            gercekBaslik="Gerçek üst"
          />

          <SectionTitle>Asya handikabı</SectionTitle>
          <PazarKarti
            baslik="Asya handikabı"
            aciklama={
              `Çizgiler: ` +
              Object.entries(veri.handikap.cizgi_tipleri ?? {})
                .map(([k, v]) => `${k} ${v}`)
                .join(" · ") +
              `. Ortalama getiri ${yuzde(veri.handikap.ortalama_getiri)}.`
            }
            ozet={veri.handikap}
            gercekBaslik="Gerçek getiri"
          />

          <p className="text-[12px] leading-relaxed text-muted-foreground">
            Handikap bantları <strong>çizgiye</strong> göre dilimlenir,
            olasılığa göre değil. Sebep pazarın tanımıdır: Asya handikabının
            amacı iki tarafı eşitlemektir, yani olasılık kasten %50&apos;ye
            çivilenir — olasılığa göre dilimlendiğinde 539 maçın 531&apos;i tek
            banda düşüyor ve eğri hiçbir şey söylemiyor.
          </p>
        </>
      ) : null}
    </div>
  );
}
