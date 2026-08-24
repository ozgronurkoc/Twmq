"use client";

import * as React from "react";

import { getStats } from "@/lib/api";
import { useIstek } from "@/lib/istek";
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
  CalibrationChart,
  DrawProfile,
  FavouriteBands,
  FavouriteBreakdown,
  LeagueSplit,
  SetCoverage,
} from "@/components/istatistik/charts";
import {
  DeltaStat,
  RangeFilter,
  SliceNote,
  aralikUrldenOku,
  aralikUrleYaz,
} from "@/components/istatistik/parts";
import { IstatistikSekmeleri } from "@/components/istatistik/sekmeler";

const ARALIKLAR: Array<{ deger: number | null; etiket: string }> = [
  { deger: null, etiket: "Tüm sezon" },
  { deger: 24, etiket: "Son 24" },
  { deger: 12, etiket: "Son 12" },
  { deger: 6, etiket: "Son 6" },
];

/**
 * Piyasa sayfası — *"oranlar ne diyordu?"*
 *
 * `/istatistik` uzun süre tek akıştı ve §6.8 G1 ölçtü: 7.210 px. Bir
 * sayfanın uzunluğu tek başına bir kusur değil; kusur, **üç ayrı sorunun**
 * tek akışta üst üste durmasıydı — sezon nasıl geçti, piyasa ne dedi,
 * strateji ne yapardı. Bu sayfa ikincisidir.
 *
 * Bölme veri kaybettirmez: bütün bloklar aynen taşındı ve hepsi hâlâ
 * **aynı `?last` dilimi** üzerinden hesaplanıyor (sekme şeridi dilimi
 * href'te taşır).
 */
export default function OranlarPage() {
  const [last, setLast] = React.useState<number | null>(null);
  const [urlOkundu, setUrlOkundu] = React.useState(false);

  React.useEffect(() => {
    setLast(aralikUrldenOku());
    setUrlOkundu(true);
  }, []);

  function aralikSec(v: number | null) {
    setLast(v);
    aralikUrleYaz(v);
  }

  const {
    veri,
    hata,
    yukleniyor: mesgul,
  } = useIstek((signal) => getStats(last, signal), [last], {
    hazir: urlOkundu,
    varsayilanHata: "Oran özeti alınamadı",
  });

  const odds = veri?.odds;

  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <div>
          <h1 className="font-display text-[30px] italic leading-tight">Oranlar</h1>
          <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted-foreground">
            Maç sonucu (1/0/2) kapanış oranlarının <strong>ölçülmüş</strong>{" "}
            karnesi: favori ne sıklıkta tuttu, banko nerede güvenli, ikinci
            işaret neyi kurtarıyor, piyasa kalibre mi. Bu bir tahmin değil —
            piyasanın kendi sözünün tutulup tutulmadığıdır.
          </p>
        </div>
        <IstatistikSekmeleri last={last} />
        {odds ? (
          <div className="flex flex-wrap items-center gap-2">
            <Badge>
              {odds.with_odds}/{odds.matches} maç · %
              {ondalik(odds.coverage_pct, 1)}
            </Badge>
            <Badge ton="primary">marj %{ondalik(odds.avg_margin_pct, 2)}</Badge>
            {veri?.meta.sliced ? <Badge ton="warning">dilim</Badge> : null}
          </div>
        ) : null}
        <div>
          <RangeFilter
            deger={last}
            onChange={aralikSec}
            secenekler={ARALIKLAR}
            mesgul={mesgul}
          />
          {veri ? (
            <SliceNote
              weeks={veri.weeks.map((w) => w.week)}
              matches={veri.meta.matches ?? 0}
              sliced={Boolean(veri.meta.sliced)}
            />
          ) : null}
        </div>
      </header>

      {hata ? (
        <Callout ton="danger" baslik="Oran özeti alınamadı">
          {hata}
        </Callout>
      ) : null}

      {!veri && !hata ? <Skeleton className="h-96 w-full" /> : null}

      {veri && !odds ? (
        <Callout ton="warning" baslik="Oran verisi yok">
          Bu dilimde oran arşivi boş. Milli maç haftalarında oran
          yayınlanmaz; daha geniş bir dilim seçmeyi deneyin.
        </Callout>
      ) : null}

      {odds ? (
        <Card>
          <CardHeader
            title="Oranlar ne diyordu?"
            hint={`Maç sonucu (1/0/2) kapanış oranları — ${odds.note}.`}
          />
          <CardBody className="space-y-5">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <DeltaStat
                etiket="Favori tuttu"
                deger={`%${ondalik(odds.favourite_hit_pct, 1)}`}
                alt={`${odds.favourite_hit} / ${odds.with_odds} maç`}
              />
              <DeltaStat
                etiket="Favori 1 idi"
                deger={String(odds.favourite_split["1"])}
                alt="maçta ev sahibi favoriydi"
              />
              <DeltaStat
                etiket="Favori 2 idi"
                deger={String(odds.favourite_split["2"])}
                alt="maçta deplasman favoriydi"
              />
              <DeltaStat
                etiket="Favori 0 idi"
                deger={String(odds.favourite_split["0"])}
                alt="beraberlik hiçbir maçta favori olmaz"
              />
            </div>

            <div>
              <SectionTitle hint="Favori tuttuğunda ve tutmadığında hangi sonuç kaç maçta gerçekleşti.">
                Favori tuttu mu, tutmayınca ne oldu?
              </SectionTitle>
              <FavouriteBreakdown
                hit={odds.outcome_when_hit}
                miss={odds.outcome_when_miss}
                cross={odds.cross}
                hitTotal={odds.favourite_hit}
                missTotal={odds.favourite_miss}
                underdog={odds.underdog_wins}
              />
            </div>

            <div>
              <SectionTitle hint="Favorinin oranı düştükçe isabet artar. Banko yapmadan önce bakılacak tablo budur; “tutmadı”nın ne kadarının beraberlikten geldiği ayrı gösterilir.">
                Banko güvenilirliği — favori oranına göre
              </SectionTitle>
              <FavouriteBands bands={odds.favourite_bands} />
              <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
                Az maç içeren bantlarda yüzdeler oynaktır; “Maç” sütununa
                bakmadan karar vermeyin. Aralık filtresi bu tabloyu da kapsar.
              </p>
            </div>

            <div>
              <SectionTitle hint="Bir maça ikinci işareti koymak neyi satın alıyor? “Oran diyor” sütunu ilk iki olasılığın toplamıdır — yani piyasanın kendi kapsama tahmini; yanındaki sütun gerçekleşeni gösterir.">
                Çifte kapsaması — ikinci işaret neyi kurtarıyor
              </SectionTitle>
              <SetCoverage rows={odds.set_coverage} esik={odds.low_sample_at} />
            </div>

            <div>
              <SectionTitle hint="Favori ile ikinci sembol birbirine yakınsa beraberlik ihtimali artar. Eğilim var ama zayıf: bu bir gösterge, tahminci değil.">
                Beraberlik profili
              </SectionTitle>
              <DrawProfile rows={odds.draw_profile} esik={odds.low_sample_at} />
            </div>

            <div>
              <SectionTitle hint="Kuponun yarısı Süper Lig’den geliyor ve ligler beraberlik oranında birbirinden ayrışıyor — bu fark “0” bütçesinin nereye harcanacağını değiştirir. Lig etiketi oran arşivinden gelir.">
                Lig kırılımı
              </SectionTitle>
              <LeagueSplit rows={odds.leagues} esik={odds.low_sample_at} />
            </div>

            <div>
              <SectionTitle hint="Oranın verdiği olasılık, gerçekte o sıklıkta oldu mu? İki nokta ne kadar üst üsteyse oran o kadar kalibre.">
                Kalibrasyon
              </SectionTitle>
              <CalibrationChart rows={odds.calibration} />
            </div>

            <p className="text-[11.5px] leading-relaxed text-muted-foreground">
              Ortalama bahisçi payı (marj) %{ondalik(odds.avg_margin_pct, 2)};
              yukarıdaki olasılıklar bu pay arındırılarak hesaplandı. Kaynak:{" "}
              {odds.books.join(", ")} kapanış. Milli maç haftalarında oran yok,
              kapsama bu yüzden %100 değildir.
            </p>
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
}
