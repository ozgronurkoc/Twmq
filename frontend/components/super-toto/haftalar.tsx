"use client";

import * as React from "react";

import {
  HAFTALAR,
  haftaDoluMu,
  haftaSonuclandiMi,
  ikinciTahminVarMi,
  type SuperTotoHafta,
  type SuperTotoMac,
} from "@/lib/super-toto";
import { SEMBOLLER as SEM } from "@/lib/types";
import { yuzde as _yuzde } from "@/lib/utils";

/** Bu tabloda basamak yok — `yuzde(v, 0)`.
 *
 *  Girdi `number | undefined`: `Record<string, number>` erisimi eksik
 *  anahtarda `undefined` doner (`noUncheckedIndexedAccess`) ve `_yuzde`
 *  bu durumu zaten "—" ile karsiliyor. Takma adi daraltmak, cagri yerinde
 *  `!` koymayi gerektirirdi — yani olmayan bir garantiyi ilan etmeyi. */
const yuzde = (v: number | undefined) => _yuzde(v, 0);
import { Tabs, TabPanel, type TabItem } from "@/components/ui/tabs";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { BenzerKart } from "@/components/benzer/kart";
import { Tahmin2Paneli } from "@/components/super-toto/tahmin2";
import { FiyatKaynaklari, KuponGerekcesi } from "@/components/super-toto/fiyatlar";
import { adreseYaz, adrestenOku } from "@/lib/adres";

const HAFTA_PARAM = "hafta";

/**
 * Secili haftayi adresten okur (`?hafta=7`). Sunucuda ve ilk render'da
 * null doner: deger bir EFEKTTE uygulanir, cunku on-render edilen sayfada
 * render sirasinda `window`'a bakmak hidrasyon uyusmazligi yapar
 * (ayni gerekce icin bkz. `istatistik/parts.tsx`).
 */
export function haftaUrldenOku(): number | null {
  const ham = adrestenOku(HAFTA_PARAM);
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
  adreseYaz(HAFTA_PARAM, String(week));
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
        <BenzerKart oranlar={mac.odds} />
      </td>
      <td className="py-1.5 pr-3 tabular-nums">
        {mac.odds_missing ? (
          <span className="text-muted-foreground">oran yok</span>
        ) : (
          // `?.` yalnizca `odds`'un null olmasini koruyordu; ANAHTAR
          // eksikse `.toFixed` cokuyordu (index imzasi `number` der).
          SEM.map((s) => mac.odds?.[s]?.toFixed(2) ?? "—").join(" / ")
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
  // Ikinci tahmin AYRI bir sekmede durur, ilkinin ustune yazmaz. Sekme
  // yalnizca kaydi olan haftada cikar: bos bir panel, olmayan bir
  // dugmeden kotudur.
  // Hafta degisince secim kendiliginden 1'e doner: her hafta kendi
  // `TabPanel`i icinde yasiyor ve secili olmayan panel HIC render
  // edilmiyor (bkz. `ui/tabs.tsx`), yani bilesen sokuluyor. Burada bir
  // sifirlama efekti YOK — olsaydi hicbir sey yapmayan bir efekt olurdu.
  const ikinci = ikinciTahminVarMi(hafta);
  const [tahmin, setTahmin] = React.useState("1");
  const secili = ikinci ? tahmin : "1";

  const k = hafta.coupon;
  const bugun = hafta.coupon_today;
  const kayan = hafta.coupon_drift;
  const eski = hafta.coupon_superseded;
  const uyarilar = [
    ...hafta.warnings_manual.map((m) => ({ kaynak: "elle" as const, m })),
    ...hafta.warnings_generated.map((m) => ({ kaynak: "kod" as const, m })),
  ];
  const dogru =
    hafta.results && k
      ? hafta.matches.filter((mac) => {
          // `picks` hafta verisinden gelir; mac numarasi ile hizasi
          // bozulursa satir EKSIK olur. Once `.includes` dogrudan
          // cagriliyordu ve o durumda sayfa cokerdi.
          const isaret = k.picks[mac.no - 1];
          return !!mac.result && !!isaret && isaret.includes(mac.result);
        }).length
      : null;

  // 1. Tahmin'in paneli. Bir degiskene alinmasinin sebebi asagidaki
  // dallanma: ikinci kayit yoksa panel SEKMESIZ basilir. Sekme seridi
  // olmadan `TabPanel` basmak, hicbir sekmeye baglanmayan bir
  // `aria-labelledby` uretirdi.
  const birinciPanel = (
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
            title="Dondurulmuş kupon"
            hint={
              k.frozen_at
                ? `${k.frozen_at} · sonuçlar görülmeden`
                : "sonuçlar görülmeden"
            }
            action={
              k.arindirma ? <Badge>arındırma: {k.arindirma}</Badge> : null
            }
          />
          <CardBody className="space-y-1.5 text-[12.5px]">
            <div className="font-mono text-[13px]">{k.picks.join(" ")}</div>
            <div className="text-muted-foreground">
              {/*
                Kuralin ADI kayittan gelir. Burada "esik <banko>/<uclu>"
                SABIT yaziliydi; esik disi bir kuralla dondurulan hafta
                (3. hafta: hedef + kalabalik ayari) kartta "esik / " diye
                gorunuyordu — yani kart kuralin kendisini yanlis
                bildiriyordu. Esikler yalnizca ESIK kuralinda anlamlidir.
              */}
              {k.banko_esik !== null && k.uclu_esik !== null
                ? `eşik ${k.banko_esik} / ${k.uclu_esik}`
                : (k.kural ?? "kural yazılmamış")}
              {k.columns ? ` · ${k.columns.toLocaleString("tr-TR")} kolon` : ""}
              {k.rows ? ` · ${k.rows} satır` : ""}
              {k.in_set_p !== null
                ? ` · küme-içi ${_yuzde(k.in_set_p, 2)}`
                : ""}
              {dogru !== null ? ` · ${dogru}/15 küme içinde` : ""}
            </div>
            {/*
              Olcek degistiyse bunu SOYLEMEK zorundayiz. Kural ayni ama
              marj arindirma varsayilani degisti ve ayni esik baska
              isaretler uretiyor. Dondurulmus kayit yeniden hesaplanmaz;
              bugunku kuralin ne yapacagi AYRI bir satirda durur.
            */}
            {eski ? (
              <div className="rounded-lg border border-line bg-muted/40 px-3 py-2">
                <div className="text-[12px] font-medium">
                  Bu kupon yenilendi
                  {eski.revised_at ? ` · ${eski.revised_at}` : ""}
                </div>
                <div className="mt-1 font-mono text-[12.5px] text-muted-foreground">
                  {eski.picks.join(" ")}
                </div>
                {eski.reason ? (
                  <div className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">
                    {eski.reason}
                  </div>
                ) : null}
              </div>
            ) : null}
            {/*
              Iki sey birden degisti: OLCEK (marj arindirma orantili -> shin)
              ve KURAL (esik -> hedef). Ikisini de yazmak gerekiyor, cunku
              isaret farkinin hangisinden geldigi aksi halde anlasilmaz.
            */}
            {bugun &&
            (bugun.arindirma !== k.arindirma || bugun.kural !== "esik") ? (
              <div className="rounded-lg border border-line bg-muted/40 px-3 py-2">
                <div className="text-[12px] font-medium">
                  Bugünkü kural ne işaretlerdi
                  <span className="ml-1.5 font-normal text-muted-foreground">
                    ({bugun.kural} · {bugun.arindirma})
                  </span>
                </div>
                <div className="mt-1 font-mono text-[12.5px]">
                  {bugun.picks.join(" ")}
                </div>
                <div className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">
                  {bugun.columns
                    ? `${bugun.columns.toLocaleString("tr-TR")} kolon · `
                    : ""}
                  P(en iyi kolon ≥ 12) {(100 * bugun.p_hedef).toFixed(1)}%
                  {bugun.p_hedef_esik
                    ? ` — eşik kuralıyla ${(100 * bugun.p_hedef_esik).toFixed(1)}%`
                    : ""}
                  .{" "}
                  {kayan && kayan.length
                    ? `${kayan.join(", ")}. maçta işaret değişiyor. `
                    : "Bu haftada hiçbir işaret değişmiyor. "}
                  Yukarıdaki kayıt <strong>yeniden hesaplanmaz</strong> —
                  sonuçlar görülmeden donduruldu.
                </div>
              </div>
            ) : null}
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
                isaret={k?.picks[mac.no - 1] ?? null}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/*
        Kuponun gerekcesi ve fiyat kaynaklari. Ikisi de rapor sayfasinda
        vardi, arayuzde yoktu; veri tasimayan haftalarda hic cizilmez.
      */}
      {k ? <KuponGerekcesi kupon={k} /> : null}
      {hafta.prices ? (
        <FiyatKaynaklari fiyatlar={hafta.prices} oddsKind={hafta.odds_kind} />
      ) : null}

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
        değildir</strong>.{" "}
        {/*
          Bu cumle "isaretler yalnizca 2025/26 geri testinin ESIGINDEN
          gelir" diye SABIT yaziliydi. Ilk iki hafta icin dogruydu; 3.
          hafta `hedef` kuraliyla dondurulunca esik hic kullanilmadi ve
          cumle kaydin tersini soylemeye basladi. Kural artik kayittan
          okunuyor ve uc durumun her biri kendi cumlesini alir.
        */}
        {k?.kural?.includes("kalabalık") ? (
          <>
            İşaret <strong>sayıları</strong> yalnızca fiyattan gelir; oynanma
            yüzdeleri yalnızca <strong>hangi sembol</strong> sorusuna girer
            (kalabalık ayarı), bedeli değiştirmez.
          </>
        ) : k?.kural === "hedef" ? (
          <>
            İşaretler verilen bütçede doğrudan{" "}
            <strong>P(en iyi kolon ≥ 12)</strong>&apos;yi enbüyükler; eşiğe
            bakmaz ve <strong>oynanma verisi seçime girmez</strong>.
          </>
        ) : (
          <>
            İşaretler yalnızca 2025/26 geri testinin eşiğinden gelir; oynanma
            verisi seçime girmez.
          </>
        )}
      </p>
    </div>
  );

  if (!ikinci) return birinciPanel;

  // Sekme kimlikleri `tahmin-` onekli: sayfadaki HAFTA seridi de `Tabs`
  // kullaniyor ve onun kimlikleri "1".."41". Onek olmasa `tab-1` DOM'da
  // iki kez gecerdi — hem gecersiz HTML, hem de `HaftaSekmeleri`in
  // `getElementById` ile buldugu seridin yanlis dugmesi.
  return (
    <div className="space-y-4">
      <Tabs
        items={[
          { id: "tahmin-1", label: "1. Tahmin" },
          { id: "tahmin-2", label: "2. Tahmin", badge: "yeni" },
        ]}
        value={`tahmin-${secili}`}
        onChange={(id) => setTahmin(id === "tahmin-2" ? "2" : "1")}
        className="max-w-[300px]"
      />
      <TabPanel id="tahmin-1" active={secili === "1"}>
        {birinciPanel}
      </TabPanel>
      <TabPanel id="tahmin-2" active={secili === "2"}>
        <Tahmin2Paneli hafta={hafta} />
      </TabPanel>
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
