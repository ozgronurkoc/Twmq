"use client";

import * as React from "react";

import { getBenzerMaclar, type ArindirmaYontemi } from "@/lib/api";
import { useIstek } from "@/lib/istek";
import { SEMBOLLER } from "@/lib/types";
import type {
  BenzerDilim,
  BenzerKarne,
  BenzerResponse,
  Cizgi,
} from "@/lib/types";
import { sayi } from "@/lib/utils";
import { Badge, Callout, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { TABLO_BASLIK_SATIRI, TABLO_SARMAL } from "@/components/ui/tablo";

/** Sorguyu belirleyen her şey — adres çubuğunda taşınan durum da budur. */
export interface Sorgu {
  oran: Record<string, string>;
  cizgi: Cizgi;
  arindirma: ArindirmaYontemi;
  /** `null` = yarıçap uyarlanır (sunucu varsayılanı). */
  tolerans: number | null;
  enAz: number;
  sezon: string;
  tarih: string;
}

export function oranSayilari(oran: Record<string, string>): Record<string, number> {
  return Object.fromEntries(SEMBOLLER.map((s) => [s, Number(oran[s])]));
}

export function oranGecerli(oran: Record<string, string>): boolean {
  return SEMBOLLER.every((s) => {
    const v = Number(oran[s]);
    return Number.isFinite(v) && v > 1;
  });
}

/**
 * Girilen oranın marjı — **canlı** gösterilir.
 *
 * Sebep sunucunun uyarısıyla aynı: iddaa bülteni ~%18–28 marjlı, korpus
 * ~%7. Arındırma yöntemi bu farkta sonucu görünür biçimde değiştirir, yani
 * marj sorgunun bir parçasıdır ve kullanıcı onu cevabı beklemeden görmeli.
 */
export function marjHesapla(oran: Record<string, string>): number | null {
  if (!oranGecerli(oran)) return null;
  return SEMBOLLER.reduce((t, s) => t + 1 / Number(oran[s]), 0) - 1;
}

// ─── oran girişi ──────────────────────────────────────────────────────────

/**
 * Ondalıklı oran girişi **metin** tutar, sayı değil.
 *
 * `ui/controls.NumberField` sayı tutar ve okunamayan değeri `min`e düşürür;
 * "1." yazmakta olan biri her tuş vuruşunda alanının altından kayan bir
 * değer görürdü. Burada dönüştürme yalnızca sorgu kurulurken yapılır.
 */
function OranKutusu({
  etiket,
  sembol,
  deger,
  onChange,
}: {
  etiket: string;
  sembol: string;
  deger: string;
  onChange: (v: string) => void;
}) {
  const id = React.useId();
  const v = Number(deger);
  const bozuk = deger !== "" && !(Number.isFinite(v) && v > 1);
  return (
    <div>
      <label htmlFor={id} className="block text-[12px] font-medium text-muted-foreground">
        {etiket} <span className="font-mono text-[11px]">({sembol})</span>
      </label>
      <input
        id={id}
        type="text"
        inputMode="decimal"
        value={deger}
        placeholder="1.82"
        aria-invalid={bozuk}
        onChange={(e) => onChange(e.target.value.replace(",", "."))}
        className={[
          "tnum mt-1.5 h-10 w-full rounded-xl border bg-background px-3 text-[13.5px]",
          "transition-shadow duration-200 ease-smooth",
          "focus:outline-none focus:ring-2 focus:ring-primary/50",
          bozuk ? "border-danger" : "border-line",
        ].join(" ")}
      />
      {bozuk ? (
        <p className="mt-1 text-[11.5px] text-danger">1.00&apos;den büyük olmalı</p>
      ) : null}
    </div>
  );
}

export function OranGirisi({
  oran,
  onChange,
}: {
  oran: Record<string, string>;
  onChange: (s: string, v: string) => void;
}) {
  const etiketler: Record<string, string> = {
    "1": "Ev sahibi",
    "0": "Beraberlik",
    "2": "Deplasman",
  };
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {/* Sira KUPON duzeni (1, 0, 2) — alfabetik degil. */}
      {SEMBOLLER.map((s) => (
        <OranKutusu
          key={s}
          sembol={s}
          etiket={etiketler[s] ?? s}
          deger={oran[s] ?? ""}
          onChange={(v) => onChange(s, v)}
        />
      ))}
    </div>
  );
}

// ─── karne ────────────────────────────────────────────────────────────────

const SEMBOL_ADI: Record<string, string> = {
  "1": "Ev sahibi kazandı",
  "0": "Berabere bitti",
  "2": "Deplasman kazandı",
};

function KarneSatiri({ sembol, karne }: { sembol: string; karne: BenzerKarne }) {
  // Eksik anahtar `undefined` doner (`noUncheckedIndexedAccess`); daraltmayi
  // derleyici yapar. Bir zamanlar elle cast edilip render sirasinda BEYAZ
  // SAYFA veriyordu (`components/benzer/kart.tsx` tarihcesi).
  const r = karne.semboller[sembol];
  if (!r) {
    return (
      <tr>
        <td className="py-2 pr-3 font-mono font-semibold">{sembol}</td>
        <td colSpan={5} className="py-2 text-muted-foreground">
          bu dilimde örnek yok
        </td>
      </tr>
    );
  }
  return (
    <tr className="border-t border-line">
      <td className="py-2 pr-3">
        <span className="font-mono text-[15px] font-semibold">{sembol}</span>
        <span className="ml-2 text-[12px] text-muted-foreground">
          {SEMBOL_ADI[sembol]}
        </span>
      </td>
      <td className="py-2 pr-3 text-right tabular-nums">{r.adet}</td>
      <td className="py-2 pr-3 text-right text-[15px] font-semibold tabular-nums">
        %{(100 * (r.oran ?? 0)).toFixed(1)}
      </td>
      <td className="py-2 pr-3 text-right tabular-nums text-muted-foreground">
        %{(100 * r.ga_alt).toFixed(1)} – %{(100 * r.ga_ust).toFixed(1)}
      </td>
      <td className="py-2 pr-3 text-right tabular-nums text-muted-foreground">
        %{(100 * r.piyasa).toFixed(1)}
      </td>
      <td className="py-2 text-right">
        {/*
          Asil okunacak sutun bu. Piyasanin dedigi aralik DISINDAYSA, o
          fiyatta piyasa sozunu tutmamis demektir. Icindeyse — ki cogu zaman
          oyledir — arac piyasayi DOGRULAMIS olur ve o da bir cevaptir.
        */}
        {r.piyasa_ga_icinde === false ? (
          <Badge ton="warning">aralık dışı</Badge>
        ) : (
          <span className="text-[12px] text-muted-foreground">uyumlu</span>
        )}
      </td>
    </tr>
  );
}

export function GenelKarne({ veri }: { veri: BenzerResponse }) {
  const t = veri.toplam;
  return (
    <Card>
      <CardHeader
        title="Geçmişte bu oranlarda ne oldu"
        hint="Yüzdenin yanında n ve Wilson %95 aralığı her zaman durur — 44 maçta %80 ile %55 arasındaki fark gürültüdür."
      />
      <CardBody className="space-y-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge ton="primary">{sayi(t.n)} benzer maç</Badge>
          <Badge>±{(100 * veri.tolerans).toFixed(1)} puan yarıçap</Badge>
          <Badge>{veri.cizgi === "acilis" ? "açılış" : "kapanış"} çizgisi</Badge>
          <Badge>{sayi(veri.evren)} maçlık evren</Badge>
          <Badge>marj %{(100 * veri.marj).toFixed(1)}</Badge>
          {veri.tolerans_genisledi ? (
            <Badge ton="warning">yarıçap genişletildi</Badge>
          ) : null}
          {veri.tolerans_tavana_dayandi ? (
            <Badge ton="warning">yarıçap tavanda</Badge>
          ) : null}
          {veri.as_of ? (
            <Badge>{veri.as_of} öncesi ({sayi(veri.evren_kesilen)} kesildi)</Badge>
          ) : null}
        </div>

        {!t.yeterli ? (
          <Callout ton="warning" baslik="Yüzde okunmuyor">
            Bu fiyata yakın yalnızca <strong>{t.n}</strong> maç var. Yüzde{" "}
            <strong>30</strong> maçın altında okunmaz; aşağıdaki lig
            kırılımından maçların kendisine bakabilirsiniz.
          </Callout>
        ) : (
          <div className={TABLO_SARMAL}>
            <table className="w-full min-w-[620px] text-[13px]">
              <thead className={TABLO_BASLIK_SATIRI}>
                <tr>
                  <th className="py-2 pr-3 text-left">Sonuç</th>
                  <th className="py-2 pr-3 text-right">Adet</th>
                  <th className="py-2 pr-3 text-right">Gerçekleşen</th>
                  <th className="py-2 pr-3 text-right">%95 aralık</th>
                  <th className="py-2 pr-3 text-right">Piyasa dedi</th>
                  <th className="py-2 text-right">Durum</th>
                </tr>
              </thead>
              <tbody>
                {SEMBOLLER.map((s) => (
                  <KarneSatiri key={s} sembol={s} karne={t} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {t.yeterli ? <TabanSatiri veri={veri} /> : null}

        {veri.mesafe ? (
          <p className="text-[11.5px] leading-relaxed text-muted-foreground">
            Bulunanların hedefe uzaklığı: en yakın %
            {(100 * veri.mesafe.en_yakin).toFixed(2)} · ortanca %
            {(100 * veri.mesafe.ortanca).toFixed(2)} · en uzak %
            {(100 * veri.mesafe.en_uzak).toFixed(2)} puan. Ortanca tavana
            dayanmışsa örneklem <strong>benzer maçlardan değil sınırdan</strong>{" "}
            toplanmış demektir.
          </p>
        ) : null}

        {veri.uyarilar.length ? (
          <ul className="space-y-1 text-[11.5px] leading-relaxed text-muted-foreground">
            {veri.uyarilar.map((u, i) => (
              <li key={i}>• {u}</li>
            ))}
          </ul>
        ) : null}
      </CardBody>
    </Card>
  );
}

/**
 * Kıyas çizgisi — aynı evrenin tamamındaki 1/0/2.
 *
 * Tek başına bir yüzde okunamaz: "bu oranda %58 ev sahibi" çarpıcı görünür
 * ama korpusun genelinde ev sahibi zaten ~%43,5 kazanıyor. Fiyatın taşıdığı
 * bilgi ikisinin **farkıdır**. Sayı burada elle yazılmaz; sunucu bu
 * sorgunun kendi evreninden sayar.
 */
function TabanSatiri({ veri }: { veri: BenzerResponse }) {
  const toplam = SEMBOLLER.reduce((a, s) => a + (veri.taban[s] ?? 0), 0);
  if (!toplam) return null;
  return (
    <div className="rounded-xl border border-line bg-muted/40 px-3 py-2.5">
      <p className="text-[11.5px] font-medium text-muted-foreground">
        Kıyas: aynı {sayi(veri.evren)} maçlık evrenin tamamında
      </p>
      <div className="mt-1.5 flex flex-wrap gap-x-5 gap-y-1 text-[12.5px]">
        {SEMBOLLER.map((s) => {
          const tabanPay = (veri.taban[s] ?? 0) / toplam;
          const bulunan = veri.toplam.semboller[s]?.oran ?? 0;
          const fark = 100 * (bulunan - tabanPay);
          return (
            <span key={s} className="tabular-nums">
              <span className="font-mono font-semibold">{s}</span>{" "}
              <span className="text-muted-foreground">
                %{(100 * tabanPay).toFixed(1)}
              </span>{" "}
              <span
                className={
                  Math.abs(fark) < 1
                    ? "text-muted-foreground"
                    : fark > 0
                      ? "text-success"
                      : "text-danger"
                }
              >
                ({fark >= 0 ? "+" : "−"}
                {Math.abs(fark).toFixed(1)} puan)
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

// ─── lig kırılımı + maç listesi ───────────────────────────────────────────

function ligYuzdesi(karne: BenzerKarne, sembol: string): string {
  const r = karne.semboller[sembol];
  return r?.oran == null ? "—" : `%${(100 * r.oran).toFixed(0)}`;
}

export function LigKirilimi({
  veri,
  sorgu,
}: {
  veri: BenzerResponse;
  sorgu: Sorgu;
}) {
  const [acik, setAcik] = React.useState<string | null>(null);
  const dilimler = veri.dilimler.lig;

  // Sorgu degistiginde acik satir kapanir: eski ligin maclari yeni cevabin
  // altinda asili kalirsa kullanici iki farkli sorgunun cikitisini yan yana
  // okur ve bunu hicbir yerde goremez.
  const anahtar = `${veri.tolerans}|${veri.cizgi}|${veri.arindirma}`;
  React.useEffect(() => {
    setAcik(null);
  }, [anahtar]);

  if (!dilimler.length) return null;

  return (
    <Card>
      <CardHeader
        title="Lig kırılımı"
        hint="Bir lige tıklayın: o oranlardaki maçların kendisi açılır. 30 maçın altındaki dilimde yüzde okunmaz — ama maçlar görülebilir."
      />
      <CardBody className="space-y-3">
        <div className={TABLO_SARMAL}>
          <table className="w-full min-w-[560px] text-[13px]">
            <thead className={TABLO_BASLIK_SATIRI}>
              <tr>
                <th className="py-2 pr-3 text-left">Lig</th>
                <th className="py-2 pr-3 text-right">Maç</th>
                <th className="py-2 pr-3 text-right">1</th>
                <th className="py-2 pr-3 text-right">0</th>
                <th className="py-2 pr-3 text-right">2</th>
                <th className="py-2 text-right" />
              </tr>
            </thead>
            <tbody>
              {dilimler.map((d) => (
                <LigSatiri
                  key={d.deger}
                  dilim={d}
                  acik={acik === d.deger}
                  onToggle={() =>
                    setAcik((a) => (a === d.deger ? null : d.deger))
                  }
                  veri={veri}
                  sorgu={sorgu}
                />
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}

function LigSatiri({
  dilim,
  acik,
  onToggle,
  veri,
  sorgu,
}: {
  dilim: BenzerDilim;
  acik: boolean;
  onToggle: () => void;
  veri: BenzerResponse;
  sorgu: Sorgu;
}) {
  const k = dilim.karne;
  return (
    <>
      <tr className="border-t border-line">
        <td className="py-0 pr-3">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={acik}
            className="w-full py-2 text-left font-medium hover:text-primary"
          >
            {acik ? "▾" : "▸"} {dilim.etiket}
          </button>
        </td>
        <td className="py-2 pr-3 text-right tabular-nums">{k.n}</td>
        {k.yeterli ? (
          SEMBOLLER.map((s) => (
            <td key={s} className="py-2 pr-3 text-right tabular-nums">
              {ligYuzdesi(k, s)}
            </td>
          ))
        ) : (
          <td colSpan={3} className="py-2 pr-3 text-right text-[11.5px] text-muted-foreground">
            yetersiz örnek (n&lt;30)
          </td>
        )}
        <td className="py-2 text-right text-[11.5px] text-muted-foreground">
          {acik ? "gizle" : "maçlar"}
        </td>
      </tr>
      {acik ? (
        <tr>
          <td colSpan={6} className="bg-muted/30 px-2 py-3">
            <MacListesi lig={dilim.deger} veri={veri} sorgu={sorgu} />
          </td>
        </tr>
      ) : null}
    </>
  );
}

const SAYFA = 50;

/**
 * Bir ligin maçları.
 *
 * **Yarıçap sorgudan değil CEVAPTAN alınır** (`veri.tolerans`). Uyarlanan
 * yarıçap evrene bağlıdır: `lig` süzgeçli bir arama daha küçük evrende
 * durduğu için daha GENİŞ bir yarıçapta dinlenir. Liste kendi yarıçapını
 * uyarlasaydı, satırda "n=41" okuyup tıklayan kullanıcı başka sayıda maç
 * görürdü. Sunucu bu yüzden `tolerans`ı zorunlu tutuyor.
 */
function MacListesi({
  lig,
  veri,
  sorgu,
}: {
  lig: string;
  veri: BenzerResponse;
  sorgu: Sorgu;
}) {
  const [limit, setLimit] = React.useState(SAYFA);
  const oran = oranSayilari(sorgu.oran);
  const anahtar = `${SEMBOLLER.map((s) => oran[s]).join(",")}|${lig}|${veri.tolerans}|${veri.cizgi}|${veri.arindirma}|${sorgu.sezon}|${sorgu.tarih}|${limit}`;

  const { veri: liste, hata, yukleniyor } = useIstek(
    (signal) =>
      getBenzerMaclar(
        oran,
        {
          tolerans: veri.tolerans,
          cizgi: veri.cizgi,
          lig,
          limit,
          ...(sorgu.sezon ? { sezon: sorgu.sezon } : {}),
          ...(sorgu.tarih ? { tarih: sorgu.tarih } : {}),
          arindirma: veri.arindirma as ArindirmaYontemi,
        },
        signal,
      ),
    [anahtar],
    { varsayilanHata: "Maçlar alınamadı" },
  );

  if (hata) return <Callout ton="danger">{hata}</Callout>;
  if (!liste) {
    return <p className="px-2 text-[12px] text-muted-foreground">aranıyor…</p>;
  }

  return (
    <div className="space-y-2">
      <p className="px-1 text-[11.5px] text-muted-foreground">
        {liste.n} maçın {liste.maclar.length} tanesi · hedefe en yakından
        uzağa
      </p>
      <div className={TABLO_SARMAL}>
        <table className="w-full min-w-[680px] text-[12.5px]">
          <thead className={TABLO_BASLIK_SATIRI}>
            <tr>
              <th className="py-1.5 pr-3 text-left">Tarih</th>
              <th className="py-1.5 pr-3 text-left">Maç</th>
              <th className="py-1.5 pr-3 text-right">Skor</th>
              <th className="py-1.5 pr-3 text-center">Sonuç</th>
              <th className="py-1.5 pr-3 text-right">Oran (1 / 0 / 2)</th>
              <th className="py-1.5 text-right">Uzaklık</th>
            </tr>
          </thead>
          <tbody>
            {liste.maclar.map((m, i) => (
              <tr key={`${m.tarih}-${m.ev}-${i}`} className="border-t border-line">
                <td className="py-1.5 pr-3 tabular-nums text-muted-foreground">
                  {m.tarih}
                </td>
                <td className="py-1.5 pr-3">
                  {m.ev} <span className="text-muted-foreground">—</span> {m.dep}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums">
                  {m.ev_gol == null || m.dep_gol == null
                    ? "—"
                    : `${m.ev_gol}-${m.dep_gol}`}
                </td>
                <td className="py-1.5 pr-3 text-center font-mono font-semibold">
                  {m.kod}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-muted-foreground">
                  {SEMBOLLER.map((s) => (m.oranlar[s] ?? 0).toFixed(2)).join(" / ")}
                </td>
                <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                  %{(100 * m.mesafe).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {liste.maclar.length < liste.n ? (
        <button
          type="button"
          disabled={yukleniyor}
          onClick={() => setLimit((v) => Math.min(v + SAYFA, 500))}
          className="text-[12px] text-primary underline decoration-dotted underline-offset-2 disabled:opacity-50"
        >
          {yukleniyor ? "yükleniyor…" : `daha fazla (${liste.n - liste.maclar.length} kaldı)`}
        </button>
      ) : null}
    </div>
  );
}
