"use client";

import * as React from "react";
import { Eraser } from "lucide-react";

import {
  bosKupon,
  kuponOzeti,
  kuponuYereldenOku,
  kuponuYereleYaz,
  yereliTemizle,
  type KuponSatiri,
} from "@/lib/kupon";
import { MAC_SAYISI, type Sembol } from "@/lib/types";
import { yuzde } from "@/lib/utils";
import { Badge, Button, Callout, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { KuponIzgarasi } from "@/components/kupon/izgara";

/**
 * Kupon kurucu — **1. aşama: giriş**.
 *
 * Bu sayfanin tamamlanmis hali su zinciri kuracak:
 *
 *   elle 15 satir  →  satir basina `/api/benzer` sorgusu (tum ligler)
 *                  →  olasilik  →  isaret secimi  →  kupon
 *
 * Su an yalnizca ILK halka var ve bu bilerek boyle: girdinin sekli
 * (hangi alanlar, hangi dogrulama, neyin kalici oldugu) sonraki halkalarin
 * hepsini belirliyor. Once o sekil elle denenir, sonra uzerine sorgu
 * baglanir.
 *
 * ─── Neden `/oran-analizi`nin bir kopyasi degil ───────────────────────────
 *
 * `/oran-analizi` TEK macin sorgu aracidir ve oyle kalmali: orada soru
 * "bu fiyatta ne oldu", cevabin yaninda lig kirilimi ve maclarin kendisi
 * durur. Burada soru "bu 15 macla hangi kupon" — yani girdi bir tablo,
 * cikti bir plan. Ayni motoru cagiracaklar ama ayni ekran degiller.
 *
 * ─── Neden hicbir sey otomatik doldurulmuyor ──────────────────────────────
 *
 * Depo 5. haftanin maclarini ve Pinnacle oranlarini zaten tasiyor
 * (`backend/data/super_toto/2026_27/hafta_05.json`). Yine de bu tablo bos
 * aciliyor: girilecek oranlar iddaa bulteninden gelecek ve o fiyat
 * Pinnacle'inkiyle ayni degil. Hazir doldurulmus bir tablo, kullanicinin
 * kendi bulteni yerine baska bir bultenle calistigini gizlerdi.
 */
export default function KuponSayfasi() {
  const [satirlar, setSatirlar] = React.useState<KuponSatiri[]>(bosKupon);
  // Yerel kayit ANCAK okunduktan sonra yazilir: ilk render'daki bos tablo
  // depodaki dolu tabloyu ezmesin.
  const [okundu, setOkundu] = React.useState(false);

  React.useEffect(() => {
    const kayit = kuponuYereldenOku();
    if (kayit) setSatirlar(kayit);
    setOkundu(true);
  }, []);

  React.useEffect(() => {
    if (!okundu) return;
    kuponuYereleYaz(satirlar);
  }, [satirlar, okundu]);

  function yaz(mac: number, alan: string, deger: string) {
    setSatirlar((onceki) =>
      onceki.map((satir, i) => {
        if (i !== mac) return satir;
        if (alan === "lig" || alan === "ev" || alan === "dep") {
          return { ...satir, [alan]: deger };
        }
        return { ...satir, oran: { ...satir.oran, [alan as Sembol]: deger } };
      }),
    );
  }

  function temizle() {
    setSatirlar(bosKupon());
    yereliTemizle();
  }

  const ozet = kuponOzeti(satirlar);
  const doluMu = satirlar.some(
    (s) => s.lig || s.ev || s.dep || s.oran["1"] || s.oran["0"] || s.oran["2"],
  );

  return (
    <div className="mx-auto w-full max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Kupon Kurucu</h1>
        <p className="mt-1 max-w-[68ch] text-[13px] leading-relaxed text-muted-foreground">
          Haftanın 15 maçını ve elinizdeki bültenin 1 / 0 / 2 oranlarını buraya
          yazın. Bu tablo zincirin <strong>ilk halkası</strong>: sonraki
          aşamada her satır kendi oranıyla tüm liglerin korpusunda aranacak,
          çıkan karneden olasılık üretilecek ve işaretler seçilecek.
        </p>
      </div>

      <Card>
        <CardHeader
          title="Maçlar ve oranlar"
          hint="Tab satır boyunca, ok tuşları ve Enter sütun boyunca ilerler — bülten sütun sütun okunur."
          action={
            <Button tip="ghost" boyut="sm" onClick={temizle} disabled={!doluMu}>
              <Eraser size={14} />
              Tabloyu temizle
            </Button>
          }
        />
        <CardBody className="space-y-4">
          <KuponIzgarasi satirlar={satirlar} onChange={yaz} />

          <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
            <Badge ton={ozet.adliMac === MAC_SAYISI ? "success" : "neutral"}>
              {ozet.adliMac}/{MAC_SAYISI} maç adı
            </Badge>
            <Badge ton={ozet.sorguyaHazir ? "success" : "neutral"}>
              {ozet.oranliMac}/{MAC_SAYISI} oran tam
            </Badge>
            {ozet.ortalamaMarj != null ? (
              <Badge ton={ozet.ortalamaMarj > 0.12 ? "warning" : "neutral"}>
                ortalama marj {yuzde(ozet.ortalamaMarj)}
              </Badge>
            ) : null}
            {doluMu ? (
              <span className="text-[11.5px] text-muted-foreground">
                Tablo tarayıcıya kaydedildi — yenileme kaybettirmez.
              </span>
            ) : null}
          </div>
        </CardBody>
      </Card>

      {ozet.bozukSatirlar.length ? (
        <Callout ton="danger" baslik="Okunamayan oran">
          {ozet.bozukSatirlar.map((i) => i + 1).join(", ")}. satırda 1,00&apos;den
          büyük bir sayı olmayan hücre var. Oran her zaman ondalık yazılır;
          virgül otomatik noktaya çevrilir.
        </Callout>
      ) : null}

      {ozet.eksikOranlar.length ? (
        <Callout ton="warning" baslik="Oranı yarım kalan satır">
          {ozet.eksikOranlar.map((i) => i + 1).join(", ")}. satırda veri var ama
          üç oranın hepsi girilmemiş. Arama <strong>olasılık uzayında</strong>
          {" "}yapılır; bunun için üç oran birden gerekir — ikisi marjı
          belirlemeye yetmez.
        </Callout>
      ) : null}

      <Callout ton={ozet.sorguyaHazir ? "success" : "neutral"} baslik="Sıradaki aşama">
        {ozet.sorguyaHazir ? (
          <>
            15 satırın da oranı tam. Sonraki adımda bu tablo{" "}
            <strong>tüm liglerin korpusunda</strong> satır satır aranacak;
            açılış/kapanış çizgisi ve marj arındırma yöntemi (shin · güç ·
            orantılı) üstte tek çubuktan seçilecek.
          </>
        ) : (
          <>
            Tabloyu doldurun. Sorgu, <strong>15 satırın da</strong> oranı tam
            olduğunda kurulabilir — eksik satır kuponun o maçını körleştirir.
          </>
        )}
      </Callout>
    </div>
  );
}
