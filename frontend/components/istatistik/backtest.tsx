"use client";

import * as React from "react";
import Link from "next/link";

import type {
  BacktestHoldout,
  BacktestSeason,
  BacktestWeek,
  ButceRow,
  SweepRow,
} from "@/lib/types";
import { cn, ondalik, sayi } from "@/lib/utils";
import { Button, Callout, Stat } from "@/components/ui/primitives";
import { CouponCell } from "@/components/ui/symbol";
import { seqFill, seqInk } from "./viz";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

/* ── strateji secici ────────────────────────────────────────────────────── */

/**
 * Esikler VERI araligi degil STRATEJI parametresidir; bu yuzden "tek filtre
 * satiri" kuralini bozmadan kartin icinde durabilir. Aralik filtresi (?last)
 * yine sayfanin tepesinde ve butun bloklari birlikte kapsiyor.
 */
export function StrategyPicker({
  banko,
  uclu,
  grid,
  onChange,
  mesgul,
}: {
  banko: number;
  uclu: number;
  grid: { banko: number[]; uclu: number[] };
  onChange: (banko: number, uclu: number) => void;
  mesgul?: boolean;
}) {
  return (
    <div className="space-y-3">
      <div>
        <div className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          Banko eşiği — favori olasılığı bunun üstündeyse tek işaret
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Banko eşiği">
          {grid.banko.map((v) => (
            <Button
              key={v}
              type="button"
              tip={v === banko ? "primary" : "outline"}
              boyut="sm"
              aria-pressed={v === banko}
              disabled={mesgul}
              onClick={() => onChange(v, uclu)}
            >
              %{(v * 100).toFixed(0)}
            </Button>
          ))}
        </div>
      </div>
      <div>
        <div className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          Üçlü eşiği — favori olasılığı bunun altındaysa maç kapatılır
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Üçlü eşiği">
          {grid.uclu.map((v) => (
            <Button
              key={v}
              type="button"
              tip={v === uclu ? "primary" : "outline"}
              boyut="sm"
              aria-pressed={v === uclu}
              disabled={mesgul}
              onClick={() => onChange(banko, v)}
            >
              {v === 0 ? "üçlü yok" : `%${(v * 100).toFixed(0)}`}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── sezon ozeti ────────────────────────────────────────────────────────── */

/**
 * Kesit ozeti. MANSET 12'dir: ikramiye orada baslar, yani urunun olctugu
 * sayi odur. Uzun sure manset 14'tu ve bu, ortalamasi 11 civarinda olan bir
 * dagilimin ust kuyrugunu basari olcutu sanmak demekti — 14 o yuzden artik
 * kendi kutucugunda "kuyruk" olarak duruyor.
 */
export function BacktestStats({ season, kademe }: { season: BacktestSeason; kademe: number }) {
  if (!season.weeks) {
    return <p className="text-[13px] text-muted-foreground">Çalıştırılabilir hafta yok.</p>;
  }
  const [lo, hi] = season.hit12_ci;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat
        boyut="lg"
        etiket={`${kademe}+ tutan hafta`}
        deger={`${season.hit12} / ${season.weeks}`}
        alt={`%${ondalik(season.hit12_pct, 1)} · %95 aralık %${ondalik(lo, 1)}–%${ondalik(hi, 1)} — ikramiye ${kademe}'de başlar`}
        ton={season.hit12 === 0 ? "warning" : "neutral"}
      />
      <Stat
        boyut="lg"
        etiket="Ortalama en iyi kolon"
        deger={ondalik(season.best_avg, 2)}
        alt={`düzde 15 − kaçak · kırılım aşağıda`}
      />
      <Stat
        boyut="lg"
        etiket="Haftalık bedel"
        deger={`₺${sayi(Math.round(season.tl_avg))}`}
        alt={`ort. ${sayi(Math.round(season.columns_avg))} kolon · toplam ₺${sayi(Math.round(season.tl_total))}`}
      />
      <Stat
        boyut="lg"
        etiket={`${kademe} başına maliyet`}
        deger={season.columns_per_hit12 === null ? "—" : sayi(Math.round(season.columns_per_hit12))}
        alt={
          season.columns_per_hit12 === null
            ? `hiçbir hafta ${kademe}'ye ulaşmadı`
            : `bir ${kademe} için ödenen toplam kolon`
        }
        ton={season.columns_per_hit12 === null ? "warning" : "neutral"}
      />
    </div>
  );
}

/**
 * TAM kademe kirilimi. `hit12` "12 ve ustu" demek ve icinde 15'ler de var;
 * ikramiye tablosunda 15 ile 12 arasinda binlerce kat fark oluyor. Manset
 * 12+ KALIR ama yanina bu kirilim konmadan okunmamali.
 */
export function KademeDagilimi({ season }: { season: BacktestSeason }) {
  const d = season.kademe_dagilimi;
  // Ad BILEREK `yuzde` degil: o, `lib/utils.ts`in bicimleyici adlarindan
  // biri ve `scripts/check.mjs` yerel bir `const yuzde`yi "kanonigi
  // getirmeden yeniden yazilmis bicimleyici" sayiyor. Burasi bir
  // bicimleyici degil, sunucudan gelen veri.
  const paylar = season.kademe_dagilimi_pct;
  const satirlar = [
    { anahtar: "15", etiket: "15 — tam bilme", vurgu: true },
    { anahtar: "14", etiket: "14" },
    { anahtar: "13", etiket: "13" },
    { anahtar: "12", etiket: "12 — ikramiyenin başladığı kademe" },
    { anahtar: "alt", etiket: "12'nin altı — ikramiye yok", vurgu: false },
  ];
  const enCok = Math.max(...Object.values(d));
  return (
    <div className={TABLO_SARMAL}>
      <table className="w-full min-w-[420px] text-[12.5px]">
        <thead>
          <tr className={TABLO_BASLIK_SATIRI}>
            <th scope="col" className="pb-2 pr-3 font-medium">En iyi kolon</th>
            <th scope="col" className="w-20 pb-2 pr-3 text-right font-medium">Hafta</th>
            <th scope="col" className="w-20 pb-2 pr-3 text-right font-medium">Pay</th>
            <th scope="col" className="pb-2 font-medium">Dağılım</th>
          </tr>
        </thead>
        <tbody className="tnum">
          {satirlar.map((r) => {
            const n = d[r.anahtar] ?? 0;
            const p = paylar[r.anahtar] ?? 0;
            return (
              <tr key={r.anahtar} className="border-t border-line">
                <td className={cn("py-2 pr-3", r.vurgu && "font-semibold")}>{r.etiket}</td>
                <td className="py-2 pr-3 text-right">{n}</td>
                <td className="py-2 pr-3 text-right text-muted-foreground">%{ondalik(p, 1)}</td>
                <td className="py-2">
                  <div
                    className="h-2 rounded"
                    style={{
                      width: `${enCok ? (100 * n) / enCok : 0}%`,
                      minWidth: n ? "3px" : 0,
                      background: seqFill(enCok ? n / enCok : 0),
                    }}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ── esik taramasi ──────────────────────────────────────────────────────── */

/**
 * Tarama tablosu. En iyi satir vurgulanir ama "bul ve oyna" diye SUNULMAZ:
 * 41 hafta uzerinde en iyi gorunen esik tanimi geregi bu sezona uyar. Karar
 * icin okunacak sayi hold-out satiridir.
 */
/** Eşik taramasında varsayılan satır sayısı — §6.8 G1 sayfa bütçesi. */
const SWEEP_VARSAYILAN = 12;

export function SweepTable({
  rows,
  best,
  secili,
  onSec,
}: {
  rows: SweepRow[];
  best: SweepRow | null;
  secili: { banko: number; uclu: number };
  onSec: (banko: number, uclu: number) => void;
}) {
  const [hepsi, setHepsi] = React.useState(false);

  if (!rows.length) {
    return <p className="text-[13px] text-muted-foreground">Tarama sonucu yok.</p>;
  }
  const enCok = Math.max(...rows.map((r) => r.hit12));
  // Sayfa butcesi (§6.8 G1: < 3.500 px). 28 satirlik tam tarama tek basina
  // 1.190 px — sayfanin ucte biri. `BacktestWeeks` ile ayni desen: veri
  // kaybolmuyor, bir tik uzaga gidiyor. SECILI ve EN IYI satirlar her zaman
  // gorunur kalir; kisaltma bir karari gizlemez.
  const kisaltiliyor = !hepsi && rows.length > SWEEP_VARSAYILAN;
  const gorunen = kisaltiliyor
    ? rows.filter(
        (r, i) =>
          i < SWEEP_VARSAYILAN ||
          (r.banko === secili.banko && r.uclu === secili.uclu) ||
          (best !== null && r.banko === best.banko && r.uclu === best.uclu),
      )
    : rows;

  return (
    <div className="space-y-3">
      <div className={TABLO_SARMAL}>
        <table className="w-full min-w-[760px] text-[12.5px]">
          <thead>
            <tr className={TABLO_BASLIK_SATIRI}>
              <th scope="col" className="pb-2 pr-3 font-medium">Banko</th>
              <th scope="col" className="pb-2 pr-3 font-medium">Üçlü</th>
              <th scope="col" className="w-16 pb-2 pr-3 text-right font-medium">Hafta</th>
              <th scope="col" className="w-20 pb-2 pr-3 text-right font-medium">12+</th>
              <th scope="col" className="w-24 pb-2 pr-3 text-right font-medium">14+</th>
              <th scope="col" className="w-28 pb-2 pr-3 text-right font-medium">Ort. kolon</th>
              <th scope="col" className="w-32 pb-2 pr-3 text-right font-medium">12 başına</th>
              <th scope="col" className="w-28 pb-2 font-medium">Kupon şekli</th>
            </tr>
          </thead>
          <tbody className="tnum">
            {gorunen.map((r) => {
              const aktif = r.banko === secili.banko && r.uclu === secili.uclu;
              const enIyi = best !== null && r.banko === best.banko && r.uclu === best.uclu;
              return (
                <tr
                  key={`${r.banko}-${r.uclu}`}
                  className={cn(
                    "cursor-pointer border-t border-line transition-colors hover:bg-muted/60",
                    aktif && "bg-accent",
                  )}
                  onClick={() => onSec(r.banko, r.uclu)}
                >
                  <td className="py-2 pr-3 font-medium">%{(r.banko * 100).toFixed(0)}</td>
                  <td className="py-2 pr-3 text-muted-foreground">
                    {r.uclu === 0 ? "yok" : `%${(r.uclu * 100).toFixed(0)}`}
                  </td>
                  <td className="py-2 pr-3 text-right text-muted-foreground">
                    {r.weeks}
                    {r.skipped ? (
                      <span
                        className="ml-1 text-[11px] text-warning"
                        title={`${r.skipped} hafta seçim uzayı sınırını aştığı için çözülmedi`}
                      >
                        −{r.skipped}
                      </span>
                    ) : null}
                  </td>
                  <td className="py-2 pr-3 text-right">
                    <span
                      className="rounded px-1.5 py-0.5 font-semibold"
                      style={{
                        background: seqFill(enCok ? r.hit12 / enCok : 0),
                        color: seqInk(enCok ? r.hit12 / enCok : 0),
                      }}
                    >
                      {r.hit12}
                    </span>
                    {enIyi ? (
                      <span className="ml-1.5 text-[10px] uppercase tracking-wide text-primary">
                        en iyi
                      </span>
                    ) : null}
                  </td>
                  <td className="py-2 pr-3 text-right text-muted-foreground">
                    {r.hit14}
                    <span className="ml-1 text-[11px]">
                      %{((100 * r.hit14) / Math.max(r.weeks, 1)).toFixed(0)}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-right">{sayi(Math.round(r.columns_avg))}</td>
                  <td className="py-2 pr-3 text-right text-muted-foreground">
                    {r.columns_per_hit12 === null ? "—" : sayi(Math.round(r.columns_per_hit12))}
                  </td>
                  <td className="py-2 text-[11.5px] text-muted-foreground">
                    {ondalik(r.banko_avg, 1)}B · {ondalik(r.double_avg, 1)}Ç ·{" "}
                    {ondalik(r.triple_avg, 1)}Ü
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {kisaltiliyor ? (
        <div>
          <Button tip="outline" boyut="sm" onClick={() => setHepsi(true)}>
            {rows.length} stratejinin tamamı
          </Button>
          <span className="ml-2 text-[11px] text-muted-foreground">
            İlk {SWEEP_VARSAYILAN} satır gösteriliyor; seçili ve en iyi satır
            her zaman listede.
          </span>
        </div>
      ) : rows.length > SWEEP_VARSAYILAN ? (
        <div>
          <Button tip="ghost" boyut="sm" onClick={() => setHepsi(false)}>
            İlk {SWEEP_VARSAYILAN} satıra dön
          </Button>
        </div>
      ) : null}
      <p className="text-[11.5px] leading-relaxed text-muted-foreground">
        Satıra tıklayınca o eşik çifti yukarıdaki sezon özetine uygulanır. “Hafta” sütunundaki
        turuncu eksi, seçim uzayı sınırını aştığı için çözülmeyen hafta sayısıdır — o satır
        diğerlerinden az hafta üzerinden hesaplanmıştır, doğrudan karşılaştırılamaz.
        <span className="ml-1">B = banko, Ç = çifte, Ü = üçlü (hafta başına ortalama).</span>
      </p>
    </div>
  );
}

/* ── hold-out ───────────────────────────────────────────────────────────── */

/**
 * Hedef kuralinin butce taramasi.
 *
 * Esik taramasiyla KARISTIRILMAMALI ve o yuzden ayri bir bilesen: orada
 * taranan sey sonuclara bakip secilen bir PARAMETREYDI (asiri uyum riski,
 * hold-out gerektirir), burada taranan sey bir HARCAMA KARARI. Pahali
 * basamak her zaman daha cok tutturur; okunacak sey "en iyi satir" degil,
 * bir basamak yukari cikmanin kac lira ve kac hafta ettigidir.
 */
export function ButceTable({ rows, kademe }: { rows: ButceRow[]; kademe: number }) {
  if (!rows.length) {
    return <p className="text-[13px] text-muted-foreground">Bütçe taraması yok.</p>;
  }
  const enCok = Math.max(...rows.map((r) => r.hit12));
  return (
    <div className={TABLO_SARMAL}>
      <table className="w-full min-w-[680px] text-[12.5px]">
        <thead>
          <tr className={TABLO_BASLIK_SATIRI}>
            <th scope="col" className="pb-2 pr-3 font-medium">Bütçe</th>
            <th scope="col" className="w-24 pb-2 pr-3 text-right font-medium">Tavan</th>
            <th scope="col" className="w-20 pb-2 pr-3 text-right font-medium">{kademe}+</th>
            <th scope="col" className="w-24 pb-2 pr-3 text-right font-medium">Ort. kolon</th>
            <th scope="col" className="w-28 pb-2 pr-3 text-right font-medium">Gerçek bedel</th>
            <th scope="col" className="w-28 pb-2 text-right font-medium">Ort. en iyi</th>
          </tr>
        </thead>
        <tbody className="tnum">
          {rows.map((r) => (
            <tr key={r.butce_tl} className="border-t border-line">
              <td className="py-2 pr-3 font-medium">₺{sayi(r.butce_tl)}</td>
              <td className="py-2 pr-3 text-right text-muted-foreground">
                {sayi(r.butce_kolon)} kolon
              </td>
              <td className="py-2 pr-3 text-right">
                <span
                  className="rounded px-1.5 py-0.5 font-semibold"
                  style={{
                    background: seqFill(enCok ? r.hit12 / enCok : 0),
                    color: seqInk(enCok ? r.hit12 / enCok : 0),
                  }}
                >
                  {r.hit12}
                </span>
                <span className="ml-1.5 text-[11px] text-muted-foreground">
                  %{ondalik(r.hit12_pct, 1)}
                </span>
              </td>
              <td className="py-2 pr-3 text-right">{sayi(Math.round(r.columns_avg))}</td>
              <td className="py-2 pr-3 text-right text-muted-foreground">
                ₺{sayi(Math.round(r.tl_avg))}
              </td>
              <td className="py-2 text-right text-muted-foreground">
                {ondalik(r.best_avg, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Asiri uyumun olcusu. Ayni izgara, ayni motor — tek fark esigin o haftayi
 * GORMEDEN secilmis olmasi. Iki sayi arasindaki bosluk, tarama tablosunun
 * ne kadarinin gecmise uydurma oldugunu soyler.
 */
export function HoldoutPanel({
  holdout,
  best,
}: {
  holdout: BacktestHoldout;
  best: SweepRow | null;
}) {
  if (!holdout.weeks || holdout.hit12 === undefined) {
    return <p className="text-[13px] text-muted-foreground">Hold-out için yeterli hafta yok.</p>;
  }
  const fark = (best?.hit12 ?? 0) - holdout.hit12;
  const [lo, hi] = holdout.hit12_ci ?? [0, 0];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat
        boyut="lg"
          etiket="Taramanın en iyisi"
          deger={best ? `${best.hit12} / ${best.weeks}` : "—"}
          alt={best ? `eşik %${(best.banko * 100).toFixed(0)} / ${best.uclu === 0 ? "üçlü yok" : `%${(best.uclu * 100).toFixed(0)}`}` : undefined}
        />
        <Stat
        boyut="lg"
          etiket="Hold-out (haftayı görmeden)"
          deger={`${holdout.hit12} / ${holdout.weeks}`}
          alt={
            `%${ondalik(holdout.hit12_pct ?? 0, 1)} · %95 aralık %${ondalik(lo, 1)}–%${ondalik(hi, 1)}` +
            // Olculemeyen kat SESSIZCE dusmez: paydada duruyor (iska
            // sayiliyor) ve bunu soylemek zorundayiz, yoksa oran
            // olculmemis haftalari yok saymis gibi okunur.
            (holdout.atlanan
              ? ` · ${holdout.atlanan} hafta ölçülemedi (arama uzayı) ve ıska sayıldı`
              : "")
          }
          ton={holdout.hit12 === 0 ? "warning" : "neutral"}
        />
        <Stat
        boyut="lg"
          etiket="Aşırı uyum farkı"
          deger={fark > 0 ? `−${fark} hafta` : "±0"}
          alt="taramanın kazandığı, hold-out'un kaybettiği"
          ton={fark > 0 ? "warning" : "neutral"}
        />
      </div>

      {holdout.chosen?.length ? (
        <div>
          <div className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            Hold-out hangi eşiği seçti
          </div>
          <ul className="tnum flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-muted-foreground">
            {holdout.chosen.map((c) => (
              <li key={c.threshold}>
                <span className="font-medium text-foreground">{c.threshold}</span> · {c.weeks} hafta
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/* ── hafta hafta ────────────────────────────────────────────────────────── */

export function BacktestWeeks({ weeks }: { weeks: BacktestWeek[] }) {
  const [hepsi, setHepsi] = React.useState(false);
  const gosterilen = hepsi ? weeks : weeks.slice(-12);

  return (
    <div className="space-y-3">
      <div className={TABLO_SARMAL}>
        <table className="w-full min-w-[720px] text-[12.5px]">
          <thead>
            <tr className={TABLO_BASLIK_SATIRI}>
              <th scope="col" className="w-16 pb-2 pr-3 font-medium">Hafta</th>
              <th scope="col" className="w-24 pb-2 pr-3 font-medium">Kupon</th>
              <th scope="col" className="w-24 pb-2 pr-3 text-right font-medium">Kolon</th>
              <th scope="col" className="w-16 pb-2 pr-3 text-right font-medium">Satır</th>
              <th scope="col" className="w-20 pb-2 pr-3 text-right font-medium">En iyi</th>
              <th scope="col" className="pb-2 font-medium">Küme dışı kalan maçlar</th>
            </tr>
          </thead>
          <tbody className="tnum">
            {gosterilen.map((h) => (
              <tr key={h.week} className="border-t border-line">
                <td className="py-2.5 pr-3">
                  <Link className="text-primary hover:underline" href={`/istatistik/${h.week}`}>
                    {h.week}. hf
                  </Link>
                </td>
                {h.skipped ? (
                  <td colSpan={5} className="py-2.5 text-[11.5px] text-warning">
                    çözülmedi — {h.reason}
                  </td>
                ) : (
                  <>
                    <td className="py-2.5 pr-3 text-[11.5px] text-muted-foreground">
                      {h.banko}B · {h.double}Ç · {h.triple}Ü
                    </td>
                    <td className="py-2.5 pr-3 text-right font-semibold">{sayi(h.columns)}</td>
                    <td className="py-2.5 pr-3 text-right text-muted-foreground">{h.rows}</td>
                    <td className="py-2.5 pr-3 text-right">
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 font-semibold",
                          h.best >= 14
                            ? "bg-success-soft text-success"
                            : h.best >= 13
                              ? "bg-warning-soft text-warning"
                              : "text-muted-foreground",
                        )}
                      >
                        {h.best}
                      </span>
                    </td>
                    <td className="py-2.5 text-[11.5px] text-muted-foreground">
                      {h.in_set ? (
                        <span className="text-success">tamamı küme içinde</span>
                      ) : (
                        <>
                          {h.miss_at.join(", ")}. maç
                          <span className="ml-1.5 opacity-70">({h.misses} kaçak)</span>
                        </>
                      )}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {weeks.length > 12 ? (
        <Button tip="ghost" boyut="sm" onClick={() => setHepsi((v) => !v)}>
          {hepsi ? "Son 12 haftayı göster" : `Tüm ${weeks.length} haftayı göster`}
        </Button>
      ) : null}
    </div>
  );
}

/* ── tek hafta kuponu ───────────────────────────────────────────────────── */

/** Seçili stratejinin bir haftada ürettiği kupon — sayının somut karşılığı. */
export function WeekCoupon({ hafta }: { hafta: BacktestWeek }) {
  if (hafta.skipped) return null;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1">
        {hafta.picks.map((p, i) => (
          <span key={i} className="relative">
            <CouponCell
              value={p}
              className={cn(hafta.miss_at.includes(i + 1) && "ring-2 ring-danger")}
            />
          </span>
        ))}
      </div>
      <p className="tnum text-[11.5px] text-muted-foreground">
        {hafta.week}. hafta · {sayi(hafta.columns)} kolon · {hafta.rows} satır ·{" "}
        {hafta.engine} · en iyi kolon {hafta.best} doğru
        {hafta.misses ? ` · kırmızı çerçeve: sonucun kaçtığı ${hafta.misses} maç` : ""}
      </p>
    </div>
  );
}

/* ── uyari ──────────────────────────────────────────────────────────────── */

export function OverfitWarning({ metin }: { metin: string }) {
  return (
    <Callout ton="warning" baslik="Bu tablo geleceğin garantisi değildir">
      {metin}
    </Callout>
  );
}
