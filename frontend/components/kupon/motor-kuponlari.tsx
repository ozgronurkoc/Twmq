"use client";

import * as React from "react";

import { CIZGI_ADI, CIZGI_SIRASI } from "@/lib/kupon";
import type { Cizgi, MotorCevabi, MotorPlani } from "@/lib/types";
import { cn, sayi, yuzde } from "@/lib/utils";
import type { KuponSatiri } from "@/lib/kupon";
import {
  IsaretTablosu,
  SEVIYE_ADI,
  type KuponSutunu,
} from "@/components/kupon/isaret-tablosu";
import { KuponOzetKutusu, KuponToplami } from "@/components/kupon/kupon-ozet";

/**
 * MOTOR kuponları — haftanın kuponunu fiilen kuran zincir.
 *
 * Karne kuponlarının (`sekilli-kuponlar.tsx`) ikizi ve aynı tabloyu çizer
 * (`isaret-tablosu.tsx`), ama başka bir soruya cevap verir:
 *
 *     karne  "bu fiyatta geçmişte ne olmuş"     (`/api/benzer`)
 *     motor  "marjı atılmış fiyat ne diyor"     (`/api/kupon/motor`)
 *
 * Motor, 5. haftada OYNANAN kuponu birebir yeniden üretiyor
 * (`backend/tests/test_kupon_motor.py`), yani bu kart "hafta 5'te ne
 * yaptıysak" sorusunun cevabıdır.
 *
 * ─── İki plan, iki ayrı karar ────────────────────────────────────────────
 *
 * `hak`   şekli BÜTÇE seçer — beklenen parayı enbüyükleyen plan.
 * `sabit` şekli KULLANICI seçer (5 banko · 5 çift · 5 üçlü) ve motor o
 *         şeklin kanıtlanmış en iyisini verir.
 */

/** Plan ekranda hangi sırayla dursun — önce bütçenin şekli. */
function planSirasi(planlar: MotorPlani[]): MotorPlani[] {
  return [...planlar].sort((a, b) => (a.anahtar === "hak" ? -1 : 0) - (b.anahtar === "hak" ? -1 : 0));
}

interface MotorSutunu {
  cizgi: Cizgi;
  plan: MotorPlani;
}

function sutunlariKur(cevap: MotorCevabi): MotorSutunu[] {
  return CIZGI_SIRASI.flatMap((c) => {
    const cizgi = cevap.cizgiler[c];
    if (!cizgi) return [];
    return planSirasi(cizgi.planlar).map((plan) => ({ cizgi: c, plan }));
  });
}

export function MotorKuponlari({
  satirlar,
  cevap,
  haftalikTavanTl,
}: {
  satirlar: KuponSatiri[];
  cevap: MotorCevabi;
  haftalikTavanTl: number | null;
}) {
  const girdiler = sutunlariKur(cevap);
  const toplamKolon = girdiler.reduce((t, g) => t + g.plan.kolon, 0);
  const toplamBedel = girdiler.reduce((t, g) => t + g.plan.bedel_tl, 0);

  const sutunlar: KuponSutunu[] = girdiler.map(({ cizgi, plan }) => ({
    anahtar: `${cizgi}-${plan.anahtar}`,
    baslik: CIZGI_ADI[cizgi],
    altBaslik: plan.sekil,
    hucreler: plan.isaretler.map((semboller) => ({
      semboller,
      etiket: SEVIYE_ADI[semboller.length] ?? "",
      ipucu:
        semboller.length === 3
          ? "üçlü hiç kaçmaz"
          : `bu seviyede işaretli — planın hedefi P(kaçak ≤ ${cevap.kacak_esigi}) = ${yuzde(plan.p_hedef)}`,
    })),
  }));

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "grid gap-3",
          girdiler.length >= 4 ? "sm:grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-2",
        )}
      >
        {girdiler.map(({ cizgi, plan }) => (
          <KuponOzetKutusu
            key={`${cizgi}-${plan.anahtar}`}
            ustBaslik={CIZGI_ADI[cizgi]}
            altBaslik={`${plan.ad} — ${plan.sekil}`}
            kolon={plan.kolon}
            bedelTl={plan.bedel_tl}
            satirlar={[
              { etiket: "15/15", deger: yuzde(plan.p_kacaksiz) },
              {
                etiket: `≥12 (kaçak ≤ ${cevap.kacak_esigi})`,
                deger: yuzde(plan.p_hedef),
              },
            ]}
            uyari={
              plan.tavana_dayandi && plan.serbest_kolon
                ? `Tavana dayandı — kural serbestken ${sayi(plan.serbest_kolon)} kolon isterdi`
                : null
            }
          />
        ))}
      </div>

      <KuponToplami
        etiket={`${girdiler.length} kupon toplamı`}
        kolon={toplamKolon}
        bedelTl={toplamBedel}
        haftalikTavanTl={haftalikTavanTl}
      />

      <IsaretTablosu satirlar={satirlar} sutunlar={sutunlar} />
    </div>
  );
}

/** Motorun kuralı ve varsayımları — ekranda durur. */
export function MotorAciklamasi({ cevap }: { cevap: MotorCevabi }) {
  const vektor = Object.entries(cevap.odul_vektoru).sort(
    (a, b) => Number(a[0]) - Number(b[0]),
  );
  return (
    <p className="text-[11.5px] leading-relaxed text-muted-foreground">
      Olasılık <strong>tahminden değil orandan</strong> geliyor: marj{" "}
      <strong>{cevap.arindirma}</strong> ile atılıyor, takım kimliği ya da
      form modeli girmiyor. İki plan iki ayrı karar:{" "}
      <strong>şekli bütçe seçtiğinde</strong> kural beklenen parayı
      enbüyükler (kademeler kendi ağırlığıyla — 15, 12&apos;den kat kat çok
      öder), <strong>şekil sabitlendiğinde</strong> motor o şeklin kanıtlanmış
      en iyisini verir. Bütçe{" "}
      <strong>₺{sayi(cevap.butce_tl)} = {sayi(cevap.butce_kolon)} kolon</strong>.{" "}
      Kademe ödülleri <strong>bir önceki sezonun</strong> tablosundan (
      {vektor.map(([k, v]) => `${k}: ₺${sayi(Math.round(v))}`).join(" · ")}) —
      bu sezonun ölçeği kupon kurulurken henüz bilinmiyor, o yüzden nedensel.{" "}
      <strong>15/15</strong> ödeyen olaydır, <strong>≥12</strong> ise kapsama
      ölçüsü; ikisi aynı sayı değildir.
    </p>
  );
}
