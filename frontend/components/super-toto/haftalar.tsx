"use client";

import * as React from "react";

import { HAFTALAR, haftaDoluMu, type SuperTotoHafta } from "@/lib/super-toto";
import { Tabs, type TabItem } from "@/components/ui/tabs";

const HAFTA_PARAM = "hafta";

/**
 * Secili haftayi adresten okur (`?hafta=7`). Sunucuda ve ilk render'da
 * null doner: deger bir EFEKTTE uygulanir, cunku on-render edilen sayfada
 * render sirasinda `window`'a bakmak hidrasyon uyusmazligi yapar
 * (ayni gerekce icin bkz. `istatistik/parts.tsx`).
 */
export function haftaUrldenOku(): number | null {
  if (typeof window === "undefined") return null;
  const ham = new URL(window.location.href).searchParams.get(HAFTA_PARAM);
  if (!ham) return null;
  const n = Number(ham);
  if (!Number.isFinite(n)) return null;
  return HAFTALAR.some((h) => h.week === Math.floor(n)) ? Math.floor(n) : null;
}

/**
 * Secili haftayi adres cubuguna yazar — `/super-toto?hafta=7` paylasilabilir
 * olsun diye. `router.replace` DEGIL dogrudan `history.replaceState`:
 * ayni rotaya yapilan router replace sayfa bilesenini yeniden baglar ve
 * her sekme tikinda panel bastan kurulurdu.
 */
export function haftaUrleYaz(week: number): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  url.searchParams.set(HAFTA_PARAM, String(week));
  const yeni = url.pathname + (url.search || "") + url.hash;
  if (yeni === window.location.pathname + window.location.search + window.location.hash) return;
  window.history.replaceState(window.history.state, "", yeni);
}

/**
 * Hafta seridi. 41 sekme yatay olarak sigmaz; bu yuzden secili sekme
 * her degisimde goruse KAYDIRILIR — aksi halde `?hafta=33` ile acilan
 * bir baglantida serit basta durur ve secili sekme gorunmez.
 *
 * `block: "nearest"` sayfayi dikeyde oynatmaz, yalnizca seridin kendi
 * yatay kaydirmasi degisir. Kaydirma BILEREK animasyonsuz: `scroll-smooth`
 * denendi ve derin baglantiyla acilan sayfada serit, secili sekmeye
 * varana kadar bir sure alakasiz haftalari gosteriyordu.
 */
export function HaftaSekmeleri({
  secili,
  onSec,
}: {
  secili: number;
  onSec: (week: number) => void;
}) {
  React.useEffect(() => {
    const el = document.getElementById(`tab-${secili}`);
    el?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [secili]);

  // Rozet YALNIZCA verisi girilmis haftada cikar. Tersi denendi ("—" ile
  // bos haftalar isaretlendi) ve sezon basinda 41 sekmenin 41'i birden
  // isaretli goruntu verdi; isaretin bilgi tasimasi icin azinlikta olmasi
  // gerekiyor.
  const items: TabItem[] = HAFTALAR.map((h) => ({
    id: String(h.week),
    label: `${h.week}. Hafta`,
    badge: haftaDoluMu(h) ? "●" : undefined,
  }));

  return (
    <Tabs
      items={items}
      value={String(secili)}
      onChange={(id) => onSec(Number(id))}
    />
  );
}

/**
 * Verisi girilmemis bir haftanin paneli. Bilerek BOS: uydurma bir tablo
 * ya da ornek veri gostermek, ilerde gercek veri girildiginde ikisinin
 * ayirt edilmesini zorlastirir.
 */
export function BosHafta({ hafta }: { hafta: SuperTotoHafta }) {
  return (
    <div className="grid place-items-center rounded-xl border border-dashed border-line-strong px-6 py-14 text-center">
      <div className="max-w-md">
        <div className="text-[15px] font-semibold">
          {hafta.week}. haftanın verisi henüz girilmedi
        </div>
        <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
          Bu hafta için 15 maçın kadrosu, oranları ve sonuçları henüz yok. Veri
          girildiğinde bu panel maç listesi ve dağılımla dolacak.
        </p>
      </div>
    </div>
  );
}
