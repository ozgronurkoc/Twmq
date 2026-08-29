"use client";

import * as React from "react";

import type { SuperTotoHafta, SuperTotoTahmin2 } from "@/lib/super-toto";
import { SEMBOLLER as SEM } from "@/lib/types";
import { sayi, yuzde } from "@/lib/utils";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { Collapsible } from "@/components/ui/controls";
import { TABLO_SARMAL } from "@/components/ui/tablo";

/**
 * **2. Tahmin paneli** — ayni hafta, bugunku aletlerin tamamiyla.
 *
 * Panelin sirasi bir karar tasiyor ve karar bilinclidir: once **nicin
 * ikinci bir tahmin var** yazar, sonra iki kuponun ayni olcekteki kiyasi
 * gelir, isaretler ondan sonra. Ters sirada olsaydi okur yeni isaretleri
 * gorup eskisinin nesi eksikti sorusunu hic sormazdi.
 *
 * Sayfa hicbir sayiyi KENDI hesaplamaz — hepsi
 * `backend/data/super_toto/<sezon>/hafta_NN_tahmin2.json` kaydindan gelir
 * ve o kayit sonuclar gorulmeden donduruldu.
 *
 * Panelde para birimli hicbir sayi YOK ve bu bir eksiklik degil kural:
 * musterek beklenen deger olculmemis varsayimlarin fonksiyonudur ve
 * arayuze cikmaz (`spor_toto.getiri`, docs §6.3b). Havuz ekseninden
 * gorunen tek sey, olculmus oynanma paylarindan hesaplanan **kalabalik
 * orani**dir.
 */
export function Tahmin2Paneli({ hafta }: { hafta: SuperTotoHafta }) {
  const t = hafta.tahmin2;
  if (!t) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-[12.5px]">
        <Badge ton="primary">{t.ad}</Badge>
        <Badge>{t.frozen_at} · sonuçlar görülmeden</Badge>
        <Badge>arındırma: {t.arindirma}</Badge>
        <Badge>kural: {t.kural}</Badge>
        {/* Burada "sonuclandi · N/15 kume icinde" yaziyordu: dondurulmus
            bir kaydin uzerine sonradan bilinen bir sey. Tahmin paneli
            sonucu GORMEZ; karne kendi sekmesinde. */}
        {hafta.results ? (
          <Badge>sonuç: “Sonuç” sekmesinde</Badge>
        ) : (
          <Badge ton="warning">sonuç bekleniyor</Badge>
        )}
      </div>

      <NicinIkinci tahmin={t} />
      <Kiyas tahmin={t} />
      <KuponKarti tahmin={t} />
      <KalabalikAyari tahmin={t} sonuc={null} />
      <BagimsizGorus tahmin={t} />
      <MacTablosu hafta={hafta} tahmin={t} />
      <Duyarlilik tahmin={t} />

      <Collapsible
        baslik="Oynanacak satırlar"
        hint={`${t.rows ?? 0} satır · ${sayi(t.columns)} kolon · ${t.engine ?? "—"}`}
      >
        <div className={TABLO_SARMAL}>
          <ol className="min-w-[560px] space-y-0.5 font-mono text-[12px]">
            {t.lines.map((satir, i) => (
              <li key={i} className="flex gap-3">
                <span className="w-6 shrink-0 text-right text-muted-foreground">
                  {i + 1}
                </span>
                <span className="whitespace-pre">{satir}</span>
              </li>
            ))}
          </ol>
        </div>
      </Collapsible>

      <p className="text-[11.5px] leading-relaxed text-muted-foreground">
        Bu panel <strong>1. Tahmin&apos;in kaydını değiştirmez</strong>. O kayıt
        2026-08-18&apos;de donduruldu ve yerinde duruyor; buradaki ikinci kayıt
        onun yanına eklendi. Müşterek beklenen değer hesabı kayıtta var ama{" "}
        <strong>bu sayfada yok</strong>: ölçülmemiş varsayımlara dayanıyor
        (havuz büyüklüğü, komisyon, rakip kolon sayısı) ve ölçülmemiş bir sayı
        arayüze çıkmaz.
      </p>
    </div>
  );
}

/** Dort degisiklik, dordu de olculmus — panelin ilk blogu. */
function NicinIkinci({ tahmin }: { tahmin: SuperTotoTahmin2 }) {
  return (
    <Card>
      <CardHeader
        title="Niçin ikinci bir tahmin"
        hint="1. Tahmin donduruldu, sonra projede dört şey değişti — dördü de bu haftada başka bir cevap üretiyor."
      />
      <CardBody>
        <ul className="space-y-1.5 text-[12.5px] leading-relaxed">
          {tahmin.yenilikler.map((y, i) => (
            <li key={i} className="flex gap-2">
              <span className="shrink-0 text-muted-foreground">{i + 1}.</span>
              <span>{y}</span>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

/**
 * Iki kupon, AYNI olcekte. Eski isaretler bugunku olasiliklarla yeniden
 * OLCULUR; kayit yeniden hesaplanmaz. Bu ayrim olmadan iki `p_hedef` yan
 * yana konamaz — biri orantili, oteki shin olceginde hesaplanmisti.
 */
function Kiyas({ tahmin }: { tahmin: SuperTotoTahmin2 }) {
  const k = tahmin.kiyas;
  if (!k) return null;
  const daha_iyi = tahmin.p_hedef > k.eski_p_hedef;
  const daha_ucuz =
    k.eski_columns !== null &&
    tahmin.columns !== null &&
    tahmin.columns < k.eski_columns;

  return (
    <Card>
      <CardHeader
        title="1. Tahmin ↔ 2. Tahmin"
        hint="Eski işaretler bugünkü ölçekte yeniden ölçüldü — iki sayı ancak böyle yan yana konabilir."
        action={
          <Badge ton={daha_iyi ? "success" : "neutral"}>
            {k.degisen_maclar.length} / {tahmin.picks.length} maçta işaret farklı
          </Badge>
        }
      />
      <CardBody className="space-y-3">
        <div className={TABLO_SARMAL}>
          <table className="w-full min-w-[560px] text-[12.5px]">
            <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="pb-1.5 pr-3">Ölçü</th>
                <th className="pb-1.5 pr-3">
                  1. Tahmin
                  <span className="ml-1 font-normal normal-case">
                    ({k.eski_kural} · {k.eski_arindirma})
                  </span>
                </th>
                <th className="pb-1.5">
                  2. Tahmin
                  <span className="ml-1 font-normal normal-case">
                    ({tahmin.kural} · {tahmin.arindirma})
                  </span>
                </th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              <tr className="border-t border-line">
                <td className="py-1.5 pr-3">P(en iyi kolon ≥ 12)</td>
                <td className="py-1.5 pr-3">{yuzde(k.eski_p_hedef, 2)}</td>
                <td className={`py-1.5 ${daha_iyi ? "text-success" : ""}`}>
                  {yuzde(tahmin.p_hedef, 2)}
                </td>
              </tr>
              <tr className="border-t border-line">
                <td className="py-1.5 pr-3">Kolon</td>
                <td className="py-1.5 pr-3">{sayi(k.eski_columns)}</td>
                <td className={`py-1.5 ${daha_ucuz ? "text-success" : ""}`}>
                  {sayi(tahmin.columns)}
                </td>
              </tr>
              <tr className="border-t border-line">
                <td className="py-1.5 pr-3">
                  Kalabalık oranı
                  <span className="ml-1 text-[11px] text-muted-foreground">
                    (1&apos;in üstü: olasılığına göre az oynanmış)
                  </span>
                </td>
                <td className="py-1.5 pr-3">{k.eski_crowd_ratio.toFixed(2)}</td>
                <td className="py-1.5">{tahmin.crowd_ratio.toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="space-y-1 font-mono text-[12.5px]">
          <div>
            <span className="mr-2 font-sans text-muted-foreground">1.</span>
            {k.eski_picks.join(" ")}
          </div>
          <div>
            <span className="mr-2 font-sans text-muted-foreground">2.</span>
            {tahmin.picks.join(" ")}
          </div>
        </div>
        <p className="text-[11.5px] leading-relaxed text-muted-foreground">
          {k.not}
        </p>
      </CardBody>
    </Card>
  );
}

/** Kuponun kendisi: uc plan, ucu de gorunur. */
function KuponKarti({ tahmin }: { tahmin: SuperTotoTahmin2 }) {
  return (
    <Card>
      <CardHeader
        title={"2. Tahmin'in kuponu"}
        hint={`Bütçe ${sayi(tahmin.butce)} kolon — ${tahmin.butce_kaynagi}`}
        action={
          tahmin.guaranteed_14 ? (
            <Badge ton="success">14-garanti</Badge>
          ) : (
            <Badge ton="warning">garanti yok</Badge>
          )
        }
      />
      <CardBody className="space-y-3 text-[12.5px]">
        <div className="font-mono text-[13px]">{tahmin.picks.join(" ")}</div>
        <div className="text-muted-foreground">
          {sayi(tahmin.columns)} kolon · {tahmin.rows} satır ·{" "}
          {tahmin.engine ?? "—"} · banko {tahmin.banko.length} · çift{" "}
          {tahmin.cift.length} · üçlü {tahmin.uclu.length}
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <Olcu
            baslik="P(en iyi kolon ≥ 12)"
            deger={yuzde(tahmin.p_hedef, 2)}
            alt="kuponun asıl ölçüsü"
          />
          <Olcu
            baslik="Küme-içi"
            deger={yuzde(tahmin.in_set_p, 3)}
            alt="15 maçın da seçim kümesinde kalması"
          />
          <Olcu
            baslik="Kalabalık oranı"
            deger={tahmin.crowd_ratio.toFixed(2)}
            alt="küme-içi ÷ kalabalık-içi"
          />
        </div>
        <div className="rounded-lg border border-line bg-muted/40 px-3 py-2 text-[11.5px] leading-relaxed text-muted-foreground">
          Aynı hafta, <strong>eski kuralla ama yeni ölçekte</strong>:{" "}
          <span className="font-mono">{tahmin.esik_picks.join(" ")}</span>. Kural
          değişiminin tek başına ne yaptığı bu satırda görünür.
        </div>
      </CardBody>
    </Card>
  );
}

function Olcu({
  baslik,
  deger,
  alt,
}: {
  baslik: string;
  deger: string;
  alt: string;
}) {
  return (
    <div className="rounded-xl border border-line px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {baslik}
      </div>
      <div className="mt-0.5 text-[17px] font-semibold tabular-nums">{deger}</div>
      <div className="text-[11px] text-muted-foreground">{alt}</div>
    </div>
  );
}

/**
 * Havuz ekseni. Kuponun kendisi degil, **hangi sembol** sorusu yeniden
 * soruldu: isaret sayilari sabit kaldigi icin bedel, satir ve motor aynidir.
 */
/**
 * Sembolu degisen macin sonucu: ayar o macta kazandi mi, kaybetti mi.
 *
 * Uc hal de ayri yazilir. Tek bir "basari" sayisina indirilseydi ayarin
 * gercek olcusu (bolusme) gorunmez, isabet farki onun yerine gecerdi —
 * oysa ayar isabetten bilerek vazgeciyor.
 */
function AyarSonucu({
  sonuc,
  degisim,
}: {
  sonuc: string | null;
  degisim: { no: number; taban: string; yeni: string };
}) {
  if (!sonuc) return null;
  const g = sonuc[degisim.no - 1];
  if (!g) return null;
  const taban = degisim.taban.includes(g);
  const yeni = degisim.yeni.includes(g);
  if (taban === yeni) {
    return <span className="text-muted-foreground">değişmedi</span>;
  }
  return yeni ? (
    <span className="text-success">kazandı</span>
  ) : (
    <span className="text-danger">kaybetti</span>
  );
}

function KalabalikAyari({
  tahmin,
  sonuc,
}: {
  tahmin: SuperTotoTahmin2;
  sonuc: string | null;
}) {
  const a = tahmin.ayar;
  return (
    <Card>
      <CardHeader
        title="Kalabalık ayarı"
        hint="Müşterek bahiste kazanç, piyasa olasılığı ile oynanma payının farkından doğar — kupon kuralı kalabalığı hiç görmüyordu."
        action={
          <Badge ton={a.degisimler.length ? "primary" : "neutral"}>
            {a.degisimler.length} maçta sembol değişti
          </Badge>
        }
      />
      <CardBody className="space-y-3 text-[12.5px]">
        <div className="text-muted-foreground">
          P(en iyi kolon ≥ 12) {yuzde(a.p_hedef_taban, 2)} →{" "}
          <strong className="text-foreground">
            {yuzde(a.p_hedef_ayarli, 2)}
          </strong>{" "}
          · kalabalık oranı {a.oran_taban.toFixed(2)} →{" "}
          <strong className="text-foreground">{a.oran_ayarli.toFixed(2)}</strong>{" "}
          · kazanınca rakip yoğunluğu ×{a.kat_taban.toFixed(1)} → ×
          {a.kat_ayarli.toFixed(1)}
        </div>
        <p className="text-[11.5px] leading-relaxed text-muted-foreground">
          <strong>Kazanınca rakip yoğunluğu</strong>: bu kupon tuttuğunda,
          rastgele bir rakip kolonun <em>aynı sonucu</em> tutturma
          olasılığının normalden kaç kat fazla olduğu. Küçülmesi, ikramiyenin
          daha az bölünmesi demektir. Sayı yalnızca <strong>aynı şekildeki</strong>
          iki plan arasında okunur — üçlü işaretlenen maçın katkısı tam 1,
          banko işaretlenenin katkısı büyüktür.
        </p>

        {a.degisimler.length ? (
          <div className={TABLO_SARMAL}>
            <table className="w-full min-w-[520px] text-[12.5px]">
              <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="pb-1.5 pr-2 text-right">#</th>
                  <th className="pb-1.5 pr-3">İşaret</th>
                  <th className="pb-1.5 pr-3">Olasılık</th>
                  <th className="pb-1.5 pr-3">Oynanma</th>
                  <th className="pb-1.5">{sonuc ? "Sonuç" : ""}</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {a.degisimler.map((d) => (
                  <tr key={d.no} className="border-t border-line">
                    <td className="py-1.5 pr-2 text-right text-muted-foreground">
                      {d.no}
                    </td>
                    <td className="py-1.5 pr-3 font-mono">
                      {d.taban} → <strong>{d.yeni}</strong>
                    </td>
                    <td className="py-1.5 pr-3">
                      {yuzde(d.prob_taban, 0)} → {yuzde(d.prob_yeni, 0)}
                    </td>
                    <td className="py-1.5 pr-3 text-success">
                      {yuzde(d.oynanma_taban, 0)} → {yuzde(d.oynanma_yeni, 0)}
                    </td>
                    <td className="py-1.5">
                      <AyarSonucu sonuc={sonuc} degisim={d} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted-foreground">
            Bu haftada hiçbir sembol değişmedi — kalabalıktan sapmanın{" "}
            {yuzde(tahmin.kayip_orani, 0)} bütçe içinde karşılığı yok.
          </p>
        )}

        <p className="text-[11.5px] leading-relaxed text-muted-foreground">
          {a.not} Ayar, P(en iyi kolon ≥ 12)&apos;den en çok{" "}
          <strong>{yuzde(tahmin.kayip_orani, 0)}</strong> harcayabilir; bu bir
          ölçüm değil <strong>harcama kararıdır</strong>. Oynanma yüzdeleri tek
          bir platformun kendi kullanıcılarınındır,{" "}
          <strong>Spor Toto havuzunun tamamı değildir</strong>.
        </p>
      </CardBody>
    </Card>
  );
}

/** Orana hic bakmayan ikinci gorus — ve isaret degistirmedigi. */
function BagimsizGorus({ tahmin }: { tahmin: SuperTotoTahmin2 }) {
  const g = tahmin.gorus;
  const ayrisan = tahmin.ayrisma.filter((r) => r.sembol_farkli);
  return (
    <Card>
      <CardHeader
        title="Bağımsız görüş — orana bakmadan"
        hint={`Dixon-Coles + Elo · ${sayi(g.tarihce_mac)} maçlık tarihçe (son ${g.tarihce_son ?? "—"})`}
        action={
          <Badge ton={g.kullanilabilir ? "success" : "warning"}>
            {g.dc_olan} / {g.n} maçta görüş var
          </Badge>
        }
      />
      <CardBody className="space-y-3 text-[12.5px]">
        {g.eslesmeyen.length ? (
          <p className="text-muted-foreground">
            Korpusta karşılığı olmayan takım: {g.eslesmeyen.join(", ")}. Bu
            maçlarda görüş <strong>yok</strong> ve uydurulmuyor.
          </p>
        ) : null}

        <div className={TABLO_SARMAL}>
          <table className="w-full min-w-[600px] text-[12.5px]">
            <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="pb-1.5 pr-2 text-right">#</th>
                <th className="pb-1.5 pr-3">Maç</th>
                <th className="pb-1.5 pr-3">Piyasa 1/0/2</th>
                <th className="pb-1.5 pr-3">Dixon-Coles 1/0/2</th>
                <th className="pb-1.5">Sapma</th>
              </tr>
            </thead>
            <tbody>
              {tahmin.ayrisma.map((r) => (
                <tr key={r.no} className="border-t border-line">
                  <td className="py-1.5 pr-2 text-right tabular-nums text-muted-foreground">
                    {r.no}
                  </td>
                  <td className="py-1.5 pr-3">
                    <span className="truncate">{r.mac}</span>
                    {r.sembol_farkli ? (
                      <span className="ml-1.5 text-[11px] text-warning">
                        favori ayrışıyor
                      </span>
                    ) : null}
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {SEM.map((s) => yuzde(r.piyasa[s], 0).slice(1)).join(" / ")}
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {SEM.map((s) => yuzde(r.dc[s], 0).slice(1)).join(" / ")}
                  </td>
                  <td className="py-1.5 tabular-nums">
                    {(100 * r.toplam_sapma).toFixed(0)} puan
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {ayrisan.length ? (
          <p className="text-muted-foreground">
            Favorinin ayrıştığı maç: {ayrisan.map((r) => r.no).join(", ")}. Bu,
            görüşün haklı olduğu anlamına <strong>gelmez</strong>; kuponun o
            maçta kırılgan olduğu anlamına gelir.
          </p>
        ) : null}

        <p className="text-[11.5px] leading-relaxed text-muted-foreground">
          {g.uyari}
        </p>
      </CardBody>
    </Card>
  );
}

/** Mac mac: iki olcek, bagimsiz gorus ve isaret bir arada. */
function MacTablosu({
  hafta,
  tahmin,
}: {
  hafta: SuperTotoHafta;
  tahmin: SuperTotoTahmin2;
}) {
  const adlar = new Map(
    hafta.matches.map((m) => [m.no, `${m.home} – ${m.away}`]),
  );
  // "Gercek" sutunu buradan KALDIRILDI. Sonuc gelince tahmin tablosuna
  // bir sutun eklemek, dondurulmus kaydin uzerine sonradan bilinen bir
  // sey yazmakti; kayit artik "o an ne biliniyordu" sorusunu temiz
  // cevaplayamiyordu. Sonuc kendi sekmesinde, iki kaydi da AYNI olcuyle
  // karneliyor (`components/super-toto/sonuc.tsx`).
  const sonuc: string | null = null;
  return (
    <Card>
      <CardHeader
        title="Maç maç"
        hint={`Aynı oran, iki ölçek: ${tahmin.arindirma} (bugün) ve ${tahmin.onceki_arindirma} (1. Tahmin donduğunda).`}
      />
      <CardBody>
        <div className={TABLO_SARMAL}>
          <table className="w-full min-w-[720px] text-[12.5px]">
            <thead className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="pb-1.5 pr-2 text-right">#</th>
                <th className="pb-1.5 pr-3">Maç</th>
                <th className="pb-1.5 pr-3">{tahmin.arindirma}</th>
                <th className="pb-1.5 pr-3">{tahmin.onceki_arindirma}</th>
                <th className="pb-1.5 pr-3">Dixon-Coles</th>
                <th className="pb-1.5 pr-3">Elo farkı</th>
                <th className="pb-1.5 pr-3">İşaret</th>
                {sonuc ? <th className="pb-1.5">Gerçek</th> : null}
              </tr>
            </thead>
            <tbody>
              {tahmin.matches.map((r) => (
                <tr key={r.no} className="border-t border-line">
                  <td className="py-1.5 pr-2 text-right tabular-nums text-muted-foreground">
                    {r.no}
                  </td>
                  <td className="py-1.5 pr-3 truncate">
                    {adlar.get(r.no) ?? "—"}
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {SEM.map((s) => yuzde(r.probs[s], 0).slice(1)).join(" / ")}
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums text-muted-foreground">
                    {SEM.map((s) =>
                      yuzde(r.probs_onceki[s], 0).slice(1),
                    ).join(" / ")}
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {r.dc
                      ? SEM.map((s) => yuzde(r.dc?.[s], 0).slice(1)).join(" / ")
                      : "—"}
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums text-muted-foreground">
                    {r.elo_farki === null
                      ? "—"
                      : `${r.elo_farki > 0 ? "+" : ""}${r.elo_farki.toFixed(0)}`}
                  </td>
                  <td className="py-1.5 pr-3 font-mono">
                    {r.isaret}
                    {r.taban !== r.isaret ? (
                      <span className="ml-1.5 text-[11px] text-muted-foreground line-through">
                        {r.taban}
                      </span>
                    ) : null}
                  </td>
                  {sonuc ? (
                    <td className="py-1.5 font-mono">
                      {sonuc[r.no - 1] ?? "—"}
                      <span
                        className={
                          r.isaret.includes(sonuc[r.no - 1] ?? "")
                            ? "ml-1.5 text-success"
                            : "ml-1.5 text-danger"
                        }
                      >
                        {r.isaret.includes(sonuc[r.no - 1] ?? "") ? "✓" : "✗"}
                      </span>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[11.5px] leading-relaxed text-muted-foreground">
          <strong>Elo farkı</strong> ev sahibi lehine puan farkıdır ve bir 1/0/2
          olasılığı <strong>değildir</strong> — beklenen skor verir, beraberliği
          yarım sayar. Üstü çizili işaret, kalabalık ayarından önceki plandır.
        </p>
      </CardBody>
    </Card>
  );
}

/** Kuskulu marjli satir duzeltilseydi ne olurdu — veri DUZELTILMEDI. */
function Duyarlilik({ tahmin }: { tahmin: SuperTotoTahmin2 }) {
  const d = tahmin.duyarlilik;
  if (!d) return null;
  return (
    <Card>
      <CardHeader
        title="Duyarlılık — kuşkulu marj düzeltilseydi"
        hint="Veri düzeltilmedi; yalnızca sonucun o satıra duyarlı olup olmadığı ölçüldü."
        action={
          <Badge ton={d.degisti ? "warning" : "success"}>
            {d.degisti ? "işaretler değişiyor" : "işaretler değişmiyor"}
          </Badge>
        }
      />
      <CardBody className="space-y-2 text-[12.5px]">
        <ul className="space-y-1">
          {d.duzeltilen.map((x) => (
            <li key={x.no}>
              <span className="text-muted-foreground">{x.no}. maç</span> {x.mac}:
              marj {yuzde(x.marj, 1)} → {yuzde(d.ortanca_marj, 1)} (bültenin
              ortancası)
            </li>
          ))}
        </ul>
        {d.degisti ? (
          <div className="font-mono text-[12.5px]">{d.picks.join(" ")}</div>
        ) : null}
        <div className="text-muted-foreground">
          Düzeltilmiş ölçekte P(en iyi kolon ≥ 12) {yuzde(d.p_hedef, 2)}.
        </div>
        <p className="text-[11.5px] leading-relaxed text-muted-foreground">
          {d.not}
        </p>
      </CardBody>
    </Card>
  );
}
