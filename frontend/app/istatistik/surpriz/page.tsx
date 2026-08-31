"use client";

import * as React from "react";

import { getMeta, getSurpriz } from "@/lib/api";
import { useIstek } from "@/lib/istek";
import type { SurprizBandi, SurprizResponse, TauUyumu } from "@/lib/types";
import { ondalik } from "@/lib/utils";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  SectionTitle,
  Skeleton,
} from "@/components/ui/primitives";
import {
  DeltaStat,
  SeasonFilter,
  aralikUrldenOku,
  sezonEtiketi,
  sezonUrldenOku,
  sezonUrleYaz,
} from "@/components/istatistik/parts";
import { IstatistikSekmeleri } from "@/components/istatistik/sekmeler";

/**
 * TL biçimlendirici — kuruş **yok**, ve bu `super-toto/sonuc`taki
 * ikizinden bilerek farklı. Oradaki sayı tek bir haftanın gerçek
 * ikramiyesidir ve kuruşu vardır; buradaki sayı bir bandın **ortancasıdır**
 * ve milyonluk bir ortancada iki hane, olmayan bir kesinlik gösterirdi.
 */
const tl = (v: number | undefined) =>
  v == null ? "—" : `${Math.round(v).toLocaleString("tr-TR")} TL`;

/**
 * Adet biçimlendirici — **yuvarlamıyor.**
 *
 * Buradaki sayılar ortancadır ve çift sayıda haftada ortanca `.5` ile
 * biter. `Math.round` kullanılıyordu ve 18,5'i 19 gösteriyordu; aynı sayı
 * CLI'da 18 yazıyordu (Python `.0f` bankacı yuvarlaması). İki yüzey aynı
 * ölçüme iki farklı sayı diyordu. Kesir varsa gösterilir.
 */
const adet = (v: number | undefined) =>
  v == null
    ? "—"
    : v.toLocaleString("tr-TR", { maximumFractionDigits: 1 });

function bantEtiketi(b: SurprizBandi, ust: number) {
  return b.hi > ust ? `${b.lo}+` : `${b.lo}–${b.hi - 1}`;
}

function aralik(u: TauUyumu) {
  return `[${ondalik(u.ga_alt, 3)}, ${ondalik(u.ga_ust, 3)}]`;
}

/**
 * τ satırı — üç katın hepsi **aynı** bileşenden çıkar.
 *
 * Manşet ile sağlama satırlarının farklı görünmesi cazipti ve yanlış
 * olurdu: sağlama, manşetin küçük yazılmış dipnotu değil, onunla eşit
 * haklı bir ölçümdür. Ayıran tek şey `vurgulu` ile gelen kalınlıktır.
 */
function TauSatiri({
  ad,
  uyum,
  vurgulu = false,
}: {
  ad: string;
  uyum: TauUyumu;
  vurgulu?: boolean;
}) {
  return (
    <tr className="border-b border-border/30">
      <td className={`py-2 pr-3 ${vurgulu ? "font-medium" : ""}`}>{ad}</td>
      <td className="py-2 pr-3 text-right tabular-nums">{uyum.n}</td>
      <td
        className={`py-2 pr-3 text-right tabular-nums ${
          vurgulu ? "font-medium" : ""
        }`}
      >
        {ondalik(uyum.tau, 3)}
      </td>
      <td className="py-2 pr-3 text-right tabular-nums text-muted-foreground">
        {aralik(uyum)}
      </td>
      <td className="py-2 text-right">
        {uyum.birden_buyuk ? (
          <Badge ton="primary">1&apos;i geçiyor</Badge>
        ) : (
          <span className="text-[12px] text-muted-foreground">değmiyor</span>
        )}
      </td>
    </tr>
  );
}

/**
 * Sürpriz sayfası — *"sürpriz havuzda ne ediyor?"*
 *
 * Bu sayfa **bilerek** bir tahmin sayfası değildir ve olmadığı her blokta
 * yazar. "Hangi maç sürpriz olacak" ekseni depoda on beş kez ölçüldü
 * (`ISTATISTIK_YOL_HARITASI.md` §5.1) ve hiçbiri piyasayı geçmedi; o
 * boşluğu doldurmaya çalışan bir arayüz, ölçülmemiş bir sayıyı ürün diye
 * satardı.
 *
 * Sorduğu soru başkadır ve müşterek bahse özgüdür: aynı havuz, sürprizli
 * haftada kaç kişiye bölünüyor — ve kalabalık piyasadan sapıyor mu?
 * İkincisinin cevabı τ'dur ve **aralığıyla birlikte** gösterilir; nokta
 * tahminini tek başına göstermek, sezondan sezona 1,04–1,80 arası gezen
 * bir sayıyı kesin gibi okuturdu.
 *
 * ─── `?last` bu sayfada YOK ve bu bir eksiklik değil ─────────────────────
 *
 * Şerit `?last`i taşımaya devam ediyor (sekme geçişinde dilim korunsun),
 * ama bu sayfa onu **kullanmıyor**: kesiti belirleyen şey hafta dilimi
 * değil, resmî ikramiye tablosunun bulunduğu haftalar. Sessizce yok
 * saymak yerine sayfanın kendisi bunu yazıyor.
 */
export default function SurprizPage() {
  const [last, setLast] = React.useState<number | null>(null);
  const [sezon, setSezon] = React.useState<string | null>(null);
  const [sezonlar, setSezonlar] = React.useState<string[]>([]);
  const [urlOkundu, setUrlOkundu] = React.useState(false);

  React.useEffect(() => {
    setLast(aralikUrldenOku());
    setSezon(sezonUrldenOku());
    setUrlOkundu(true);
  }, []);

  React.useEffect(() => {
    getMeta()
      .then((m) => setSezonlar(m.seasons?.available ?? []))
      .catch(() => setSezonlar([]));
  }, []);

  function sezonSec(v: string | null) {
    setSezon(v);
    sezonUrleYaz(v);
  }

  const { veri, hata } = useIstek<SurprizResponse>(
    (signal) => getSurpriz(sezon, signal),
    [sezon],
    { hazir: urlOkundu, varsayilanHata: "Sürpriz ölçümü alınamadı" },
  );

  const olcum = veri?.olcum;
  const kalabalik = veri?.kalabalik;
  const tam = kalabalik?.tam;
  const enCokDagilim = Math.max(1, ...(olcum?.dagilim ?? []).map((d) => d.hafta));

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="font-display text-[30px] italic leading-tight">
            Sürpriz
          </h1>
          <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
            Bu sayfa <strong>hangi maçın sürpriz olacağını söylemez</strong> —
            o eksen depoda on beş kez ölçüldü ve hiçbiri kapanış fiyatını
            geçmedi. Söylediği şey başka ve müşterek bahse özgü: aynı havuz,
            sürprizli haftada <em>kaç kişiye</em> bölünüyor, ve kalabalık
            piyasadan sapıyor mu.
          </p>
        </div>
        <IstatistikSekmeleri last={last} sezon={sezon} />
        {olcum && tam ? (
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{olcum.kesit} hafta</Badge>
            <Badge>
              hafta başı {ondalik(olcum.hafta_basi.surpriz, 2)} sürpriz
            </Badge>
            <Badge ton={tam.birden_buyuk ? "primary" : "warning"}>
              τ = {ondalik(tam.tau, 2)} {aralik(tam)}
            </Badge>
            {olcum.denetim.elenen > 0 ? (
              <Badge ton="warning">{olcum.denetim.elenen} hafta elendi</Badge>
            ) : null}
          </div>
        ) : null}
        <SeasonFilter
          deger={sezon}
          secenekler={sezonlar}
          onChange={sezonSec}
        />
        <p className="text-[12px] leading-relaxed text-muted-foreground">
          Bu sayfa <strong>hafta dilimini (<code>?last</code>) kullanmaz</strong>:
          kesiti belirleyen şey son N hafta değil, resmî ikramiye tablosunun
          bulunduğu haftalardır. Şerit dilimi yine de taşır, diğer sekmelere
          geçişte kaybolmasın diye.
        </p>
      </header>

      {hata ? (
        <Callout ton="danger" baslik="Sürpriz ölçümü alınamadı">
          {hata}
        </Callout>
      ) : null}

      {!veri && !hata ? <Skeleton className="h-96 w-full" /> : null}

      {olcum?.error ? (
        <Callout ton="warning" baslik="Kesit boş">
          Bu seçimde üç arşivin (oran · kupon dizisi · resmî ikramiye
          tablosu) kesişimi boş. Daha geniş bir sezon seçmeyi deneyin.
        </Callout>
      ) : null}

      {/* ── 1. Havuz: aynı para, kaç kişiye bölünüyor ───────────────── */}
      {olcum && !olcum.error ? (
        <Card>
          <CardHeader
            title="Aynı havuz, kaç kişiye bölünüyor?"
            hint="Haftanın sürpriz sayısına göre resmî ikramiye tablosu. Sayılar ortancadır — ortalama değil: tek bir favorili hafta ortalamayı tek başına belirlerdi."
          />
          <CardBody className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-[13px]">
                <thead className="text-muted-foreground">
                  <tr className="border-b border-border/60 text-left">
                    <th className="py-2 pr-3 font-medium">Sürpriz</th>
                    <th className="py-2 pr-3 text-right font-medium">hafta</th>
                    <th className="py-2 pr-3 text-right font-medium">
                      15 bilen
                    </th>
                    <th className="py-2 pr-3 text-right font-medium">
                      12 bilen
                    </th>
                    <th className="py-2 pr-3 text-right font-medium">
                      15 kişi başı
                    </th>
                    <th className="py-2 text-right font-medium">
                      15 kazanansız
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {olcum.bantlar.map((b) => (
                    <tr key={`${b.lo}-${b.hi}`} className="border-b border-border/30">
                      <td className="py-2 pr-3 tabular-nums">
                        {bantEtiketi(b, 15)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {b.n}
                      </td>
                      {b.yeterli ? (
                        <>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {adet(b.kazanan_15)}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {adet(b.kazanan_12)}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {tl(b.odul_15)}
                          </td>
                          <td className="py-2 text-right tabular-nums">
                            {b.kazanansiz_15} / {b.n}
                          </td>
                        </>
                      ) : (
                        <td
                          colSpan={4}
                          className="py-2 text-right text-[12px] text-muted-foreground"
                        >
                          az veri — ortanca kendi gürültüsünü ölçer
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Callout ton="primary" baslik="Tabloyu ne değiştiriyor, ne değiştirmiyor">
              Değişen şey <strong>havuz değil</strong>, kaça bölündüğü: 15
              kademesinin havuzu (kazanan × kişi başı) bantlar arasında aynı
              büyüklükte kalıyor. Kişi başı ikramiye <strong>nominal TL</strong>
              &apos;dir ve sezonlar arası enflasyon taşır — bantları
              karşılaştırırken tek bir sezon seçmek daha dürüst okunur.
            </Callout>
          </CardBody>
        </Card>
      ) : null}

      {/* ── 2. Dağılım: sürpriz bir olay değil, bir sabit ────────────── */}
      {olcum && !olcum.error ? (
        <Card>
          <CardHeader
            title="Haftada kaç sürpriz çıkıyor?"
            hint="Favori kazanmadı (beraberlik dahil). Sürprizsiz hafta yok — yani bu bir sinyal sorunu değil, bir bütçe sorunu."
          />
          <CardBody className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <DeltaStat
                etiket="Hafta başı sürpriz"
                deger={ondalik(olcum.hafta_basi.surpriz, 2)}
                alt="favori kazanmadı, 15 maçta"
              />
              <DeltaStat
                etiket="Gerçek sürpriz"
                deger={ondalik(olcum.hafta_basi.ger_surpriz, 2)}
                alt="favorinin karşı tarafı kazandı"
              />
              <DeltaStat
                etiket="En temiz hafta"
                deger={String(olcum.en_az_surprizli_hafta)}
                alt={`${olcum.kesit} haftanın en azı`}
              />
            </div>
            <div className="space-y-1">
              {olcum.dagilim.map((d) => (
                <div key={d.adet} className="flex items-center gap-2 text-[12.5px]">
                  <span className="w-8 shrink-0 text-right tabular-nums text-muted-foreground">
                    {d.adet}
                  </span>
                  <div className="h-3.5 flex-1 rounded-sm bg-muted/40">
                    <div
                      className="h-full rounded-sm bg-primary/70"
                      style={{ width: `${(100 * d.hafta) / enCokDagilim}%` }}
                    />
                  </div>
                  <span className="w-16 shrink-0 tabular-nums text-muted-foreground">
                    {d.hafta} hafta
                  </span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      ) : null}

      {/* ── 3. Kalabalık modeli: τ ──────────────────────────────────── */}
      {kalabalik && tam && !kalabalik.error ? (
        <Card>
          <CardHeader
            title="Kalabalık piyasadan sapıyor mu? (τ)"
            hint="c ∝ p^τ — kalabalığın sembol dağılımı, piyasa olasılığının τ. kuvveti. τ = 1 ise kalabalık tam piyasayı oynuyor ve sürprizde kenar yok."
          />
          <CardBody className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <DeltaStat
                etiket="τ (tam kesit)"
                deger={ondalik(tam.tau, 3)}
                alt={`%95 ${aralik(tam)}`}
              />
              <DeltaStat
                etiket="Kesit"
                deger={`${tam.n} hafta`}
                alt={`${adet(tam.kazanan_kolon)} adet 15 bilen kolon`}
              />
              <DeltaStat
                etiket="Aşırı yayılım φ"
                deger={ondalik(tam.phi, 1)}
                alt="Poisson tutsaydı 1 olurdu"
              />
              <DeltaStat
                etiket="τ > 1 çıkan uyum"
                deger={`${kalabalik.saglama.tau_birden_buyuk} / ${kalabalik.saglama.uyum}`}
                alt={`aralığı 1'i geçen ${kalabalik.saglama.aralik_biri_geciyor}`}
              />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-[13px]">
                <thead className="text-muted-foreground">
                  <tr className="border-b border-border/60 text-left">
                    <th className="py-2 pr-3 font-medium">Kesit</th>
                    <th className="py-2 pr-3 text-right font-medium">n</th>
                    <th className="py-2 pr-3 text-right font-medium">τ</th>
                    <th className="py-2 pr-3 text-right font-medium">
                      %95 aralık
                    </th>
                    <th className="py-2 text-right font-medium">1&apos;i geçiyor mu</th>
                  </tr>
                </thead>
                <tbody>
                  <TauSatiri ad="Tam kesit" uyum={tam} vurgulu />
                  {Object.entries(kalabalik.sezon_disarida).map(([s, u]) => (
                    <TauSatiri
                      key={`d-${s}`}
                      ad={`${sezonEtiketi(s)} hariç`}
                      uyum={u}
                    />
                  ))}
                  {Object.entries(kalabalik.tek_sezon).map(([s, u]) => (
                    <TauSatiri
                      key={`t-${s}`}
                      ad={`yalnız ${sezonEtiketi(s)}`}
                      uyum={u}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <Callout ton="warning" baslik="Okunacak cümle τ = 1,28 değil">
              {kalabalik.saglama.uyum} uyumun{" "}
              {kalabalik.saglama.tau_birden_buyuk}&apos;inde τ birden büyük,
              ama nokta tahmini{" "}
              <strong>
                {ondalik(kalabalik.saglama.tau_alt, 2)}–
                {ondalik(kalabalik.saglama.tau_ust, 2)}
              </strong>{" "}
              arasında geziyor ve aralığı 1&apos;i geçen yalnızca{" "}
              {kalabalik.saglama.aralik_biri_geciyor} tanesi.{" "}
              <strong>Yön sağlam, miktar belirsiz.</strong> φ ={" "}
              {ondalik(tam.phi, 1)} olması da bunun bir parçası: bir oyuncu tek
              başına on binlerce kolon oynayabildiği için &quot;kolon&quot;
              bağımsız bir deneme değil, ve aralıklar bu yüzden φ ile
              genişletilmiş hâlleriyle gösteriliyor.
            </Callout>
          </CardBody>
        </Card>
      ) : null}

      {/* ── 4. Prim: bunun para karşılığı ───────────────────────────── */}
      {kalabalik && tam && !kalabalik.error ? (
        <Card>
          <CardHeader
            title="Bir sürprizi işaretlemenin ödeme primi"
            hint="Favoriyi bırakıp sürprizi işaretlemenin beklenen getiri oranı: (p_sürpriz / p_favori)^(1−τ). İsabet kaybı bu orana zaten dahildir."
          />
          <CardBody className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-[13px]">
                <thead className="text-muted-foreground">
                  <tr className="border-b border-border/60 text-left">
                    <th className="py-2 pr-3 font-medium">Favori p</th>
                    <th className="py-2 pr-3 font-medium">Sürpriz p</th>
                    <th className="py-2 pr-3 text-right font-medium">Prim</th>
                    <th className="py-2 pr-3 text-right font-medium">
                      τ aralığında
                    </th>
                    <th className="py-2 text-right font-medium">Üç maçta</th>
                  </tr>
                </thead>
                <tbody>
                  {kalabalik.prim.map((p) => (
                    <tr
                      key={`${p.p_favori}-${p.p_surpriz}`}
                      className="border-b border-border/30"
                    >
                      <td className="py-2 pr-3 tabular-nums">
                        {ondalik(p.p_favori, 2)}
                      </td>
                      <td className="py-2 pr-3 tabular-nums">
                        {ondalik(p.p_surpriz, 2)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums font-medium">
                        ×{ondalik(p.prim, 3)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-muted-foreground">
                        [{ondalik(p.prim_alt, 3)}, {ondalik(p.prim_ust, 3)}]
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        ×{ondalik(p.prim_3, 3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Callout ton="danger" baslik="Bu bir kâr sayısı DEĞİL">
              {kalabalik.sinir}
            </Callout>
          </CardBody>
        </Card>
      ) : null}

      {/* ── 5. Korelasyon + genişletilmiş uyum ──────────────────────── */}
      {olcum && kalabalik && !olcum.error ? (
        <Card>
          <CardHeader
            title="Kalabalık gerçekten piyasayı mı oynuyor?"
            hint="Sıra korelasyonu (Spearman): haftanın sürprizliği ile kazanan kolon adedi arasındaki ilişki."
          />
          <CardBody className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-[13px]">
                <thead className="text-muted-foreground">
                  <tr className="border-b border-border/60 text-left">
                    <th className="py-2 pr-3 font-medium">Ölçü</th>
                    {[15, 14, 13, 12].map((k) => (
                      <th key={k} className="py-2 pr-3 text-right font-medium">
                        {k} bilen
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(olcum.korelasyon).map(([alan, satir]) => (
                    <tr key={alan} className="border-b border-border/30">
                      <td className="py-2 pr-3">{olcum.tanim[alan] ?? alan}</td>
                      {[15, 14, 13, 12].map((k) => {
                        const v = satir[`kazanan_${k}`];
                        return (
                          <td
                            key={k}
                            className="py-2 pr-3 text-right tabular-nums"
                          >
                            {v == null
                              ? "—"
                              : `${v >= 0 ? "+" : ""}${ondalik(v, 3)}`}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div>
              <SectionTitle hint="Tek bir üs kalabalığı tam açıklıyor mu, yoksa sembole özgü bir kayma da var mı?">
                Genişletilmiş uyum
              </SectionTitle>
              <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">
                τ = {ondalik(kalabalik.genisletilmis.tau, 3)}, beraberlik
                kayması {kalabalik.genisletilmis.beraberlik >= 0 ? "+" : ""}
                {ondalik(kalabalik.genisletilmis.beraberlik, 3)}, deplasman
                kayması {kalabalik.genisletilmis.deplasman >= 0 ? "+" : ""}
                {ondalik(kalabalik.genisletilmis.deplasman, 3)}. Olabilirlik
                oranı {ondalik(kalabalik.genisletilmis.olabilirlik_orani, 2)} —
                eşik {kalabalik.genisletilmis.esik_khi2_2} —{" "}
                <strong>
                  {kalabalik.genisletilmis.gecti ? "geçti" : "geçmedi"}
                </strong>
                . {kalabalik.genisletilmis.not}
              </p>
            </div>
          </CardBody>
        </Card>
      ) : null}

      {/* ── 6. Denetim ──────────────────────────────────────────────── */}
      {olcum ? (
        <Card>
          <CardHeader
            title="Veri birleştirmesinin denetimi"
            hint="İki arşivin hafta numaraları ayrı kökenden gelir. Kayarlarsa hiçbir sayı hata vermez — sadece hepsi yanlış olur."
          />
          <CardBody className="space-y-3">
            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
              {olcum.denetim.not} Tolerans{" "}
              {olcum.denetim.tarih_toleransi_gun} gün.
            </p>
            {olcum.denetim.elenen === 0 ? (
              <Callout ton="primary" baslik="Temiz">
                Hiçbir hafta elenmedi.
              </Callout>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[420px] text-[13px]">
                  <thead className="text-muted-foreground">
                    <tr className="border-b border-border/60 text-left">
                      <th className="py-2 pr-3 font-medium">Sezon</th>
                      <th className="py-2 pr-3 font-medium">Hafta</th>
                      <th className="py-2 pr-3 font-medium">Sebep</th>
                      <th className="py-2 font-medium">Ayrıntı</th>
                    </tr>
                  </thead>
                  <tbody>
                    {olcum.denetim.elenenler.map((e) => (
                      <tr
                        key={`${e.sezon}-${e.hafta}`}
                        className="border-b border-border/30"
                      >
                        <td className="py-2 pr-3">{sezonEtiketi(e.sezon)}</td>
                        <td className="py-2 pr-3 tabular-nums">{e.hafta}</td>
                        <td className="py-2 pr-3">{e.sebep}</td>
                        <td className="py-2 text-muted-foreground">
                          {e.ayrinti || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <Callout ton="warning" baslik="Bu ölçümün sınırı">
              {olcum.sinir}
            </Callout>
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}
