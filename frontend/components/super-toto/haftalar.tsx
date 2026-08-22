"use client";

import * as React from "react";

import {
  HAFTALAR,
  haftaDoluMu,
  haftaSonuclandiMi,
  type SuperTotoHafta,
  type SuperTotoMac,
} from "@/lib/super-toto";
import { Tabs, type TabItem } from "@/components/ui/tabs";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";

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
    // Iki farkli dolu hali var ve ayirt edilmeleri gerekiyor: verisi
    // girilmis ama oynanmamis hafta (○) ile sonuclanmis hafta (●).
    badge: haftaSonuclandiMi(h) ? "●" : haftaDoluMu(h) ? "○" : undefined,
  }));

  return (
    <Tabs
      items={items}
      value={String(secili)}
      onChange={(id) => onSec(Number(id))}
    />
  );
}

const SEM = ["1", "0", "2"] as const;

function yuzde(v: number): string {
  return `%${(100 * v).toFixed(0)}`;
}

/** Bir macin satiri: oran, olasilik, oynanma, isaret ve (varsa) sonuc. */
function MacSatiri({
  mac,
  isaret,
}: {
  mac: SuperTotoMac;
  isaret: string | null;
}) {
  const tuttu = mac.result && isaret ? isaret.includes(mac.result) : null;
  return (
    <tr className="border-t border-line">
      <td className="py-1.5 pr-2 text-right tabular-nums text-muted-foreground">
        {mac.no}
      </td>
      <td className="py-1.5 pr-3">
        <div className="truncate">
          {mac.home} – {mac.away}
        </div>
        <div className="text-[11px] text-muted-foreground">{mac.league}</div>
      </td>
      <td className="py-1.5 pr-3 tabular-nums">
        {mac.odds_missing ? (
          <span className="text-muted-foreground">oran yok</span>
        ) : (
          SEM.map((s) => mac.odds?.[s].toFixed(2)).join(" / ")
        )}
      </td>
      <td className="py-1.5 pr-3 tabular-nums">
        {SEM.map((s) => yuzde(mac.probs[s]).slice(1)).join(" / ")}
      </td>
      <td className="py-1.5 pr-3 tabular-nums text-muted-foreground">
        {SEM.map((s) => yuzde(mac.play[s]).slice(1)).join(" / ")}
      </td>
      <td className="py-1.5 pr-3 font-mono">{isaret ?? "—"}</td>
      <td className="py-1.5 tabular-nums">
        {mac.result ? (
          <span className={tuttu === false ? "text-danger" : undefined}>
            {mac.result}
            {tuttu === false ? " ✗" : tuttu ? " ✓" : ""}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
    </tr>
  );
}

/**
 * Verisi girilmis bir haftanin paneli.
 *
 * Sayfa hicbir sayiyi KENDI hesaplamaz: olasiliklar, isaretler ve kolon
 * sayisi backend boru hattindan (`super_toto_frontend.py`) gelir. Arayuzde
 * yeniden hesaplanan bir sayi, iki yerde iki farkli cevap demektir.
 */
export function DoluHafta({ hafta }: { hafta: SuperTotoHafta }) {
  const k = hafta.coupon;
  const uyarilar = [
    ...hafta.warnings_manual.map((m) => ({ kaynak: "elle" as const, m })),
    ...hafta.warnings_generated.map((m) => ({ kaynak: "kod" as const, m })),
  ];
  const dogru =
    hafta.results && k
      ? hafta.matches.filter(
          (mac) => mac.result && k.picks[mac.no - 1].includes(mac.result),
        ).length
      : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-[12.5px]">
        {hafta.program ? <Badge>{hafta.program}</Badge> : null}
        {hafta.odds_kind ? <Badge>{hafta.odds_kind}</Badge> : null}
        {haftaSonuclandiMi(hafta) ? (
          <Badge ton="primary">sonuçlandı</Badge>
        ) : (
          <Badge>sonuç bekleniyor</Badge>
        )}
      </div>

      {k ? (
        <Card>
          <CardHeader
            title="Kuralın işaretleri"
            hint={`eşik ${k.banko_esik} / ${k.uclu_esik}`}
          />
          <CardBody className="space-y-1.5 text-[12.5px]">
            <div className="font-mono text-[13px]">{k.picks.join(" ")}</div>
            <div className="text-muted-foreground">
              {k.banko.length} banko · {k.cift.length} çift · {k.uclu.length} üçlü
              {k.columns ? ` · ${k.columns.toLocaleString("tr-TR")} kolon` : ""}
              {k.rows ? ` · ${k.rows} satır` : ""} · küme-içi{" "}
              {(100 * k.in_set_p).toFixed(2)}%
              {dogru !== null ? ` · ${dogru}/15 küme içinde` : ""}
            </div>
          </CardBody>
        </Card>
      ) : null}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-[12.5px]">
          <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="pb-1.5 pr-2 text-right">#</th>
              <th className="pb-1.5 pr-3">Maç</th>
              <th className="pb-1.5 pr-3">Oran 1/0/2</th>
              <th className="pb-1.5 pr-3">Olasılık</th>
              <th className="pb-1.5 pr-3">Oynanma</th>
              <th className="pb-1.5 pr-3">İşaret</th>
              <th className="pb-1.5">Sonuç</th>
            </tr>
          </thead>
          <tbody>
            {hafta.matches.map((mac) => (
              <MacSatiri
                key={mac.no}
                mac={mac}
                isaret={k ? k.picks[mac.no - 1] : null}
              />
            ))}
          </tbody>
        </table>
      </div>

      {uyarilar.length ? (
        <Card>
          <CardHeader title="Veri uyarıları" hint={`${uyarilar.length} not`} />
          <CardBody>
            <ul className="space-y-1 text-[12.5px] leading-relaxed">
              {uyarilar.map((u, i) => (
                <li key={i} className="flex gap-2">
                  <span className="shrink-0 text-muted-foreground">
                    [{u.kaynak}]
                  </span>
                  <span>{u.m}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      ) : null}

      <p className="text-[11.5px] leading-relaxed text-muted-foreground">
        Oran kaynağı: {hafta.odds_source ?? "—"}. Oynanma yüzdeleri{" "}
        {hafta.play_source ?? "—"} ve <strong>Spor Toto havuzunun tamamı
        değildir</strong>. İşaretler yalnızca 2025/26 geri testinin eşiğinden
        gelir; oynanma verisi seçime girmez.
      </p>
    </div>
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
