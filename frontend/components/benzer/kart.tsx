"use client";

import * as React from "react";

import { ARINDIRMA_YONTEMLERI, getBenzer, type ArindirmaYontemi } from "@/lib/api";
import { useIstek } from "@/lib/istek";
import { SEMBOLLER as SEM } from "@/lib/types";
import type {
  BenzerDilim,
  BenzerKarne,
  BenzerResponse,
} from "@/lib/types";
import { Badge } from "@/components/ui/primitives";
import { sayi, yuzde } from "@/lib/utils";


/**
 * "Gecmiste bu oranda ne oldu?" karti.
 *
 * ISTEK UZERINE yuklenir. Bir hafta 15 mac tasir ve hepsini birden cekmek
 * 15 sorgu demek olurdu; kullanici hangi maci merak ediyorsa onu acar.
 *
 * Kart bir TAHMIN gostermez. Gosterdigi sey su: piyasa bu fiyati verdiginde
 * gecmiste ne oldu, ve piyasanin dedigi o araligin ICINDE mi. Bu yuzden
 * hicbir yuzde `n` ve guven araligi olmadan yazilmaz — 44 macta %80 ile %55
 * arasindaki fark gurultudur ve cikplak bir yuzde onu gizler.
 */
export function BenzerKart({
  oranlar,
  lig,
}: {
  oranlar: Record<string, number> | null;
  lig?: string;
}) {
  const [acik, setAcik] = React.useState(false);

  // Arindirma yontemi kullanicinin secimidir. Backend bunu bastan beri
  // kabul ediyordu (`?arindirma=`) ama arayuz hic gondermiyordu — yani
  // motorun bir yetenegi kapali duruyordu. Yontem SORGUYU degistirir,
  // dolayisiyla anahtarin parcasidir.
  const [arindirma, setArindirma] = React.useState<ArindirmaYontemi>("shin");

  // Sorguyu belirleyen TEK sey bu anahtardir. `oranlar` her render'da yeni
  // kimlik alabilen bir nesnedir; onu bagimlilik yapmak sonsuz donguye
  // giden yoldu (asagidaki tarihce).
  const anahtar = oranlar
    ? `${SEM.map((s) => oranlar[s]).join(",")}|${lig ?? ""}|${arindirma}`
    : "";

  /*
    Bagimlilik listesi DAR tutulmustur ve bu kasitlidir. Ilk surumde
    `yukleniyor` da listedeydi ve sonsuz donguye giriyordu: efekt
    `setYukleniyor(true)` diyor, bagimlilik degistigi icin temizleyici
    kosuyor, `ac.abort()` UCUSTAKI istegi iptal ediyor, `finally`
    `yukleniyor`u false yapiyor, efekt yeniden kosuyor… Kart "araniyor…"
    yazisinda takili kaliyor ve sunucuya saniyede onlarca istek gidiyordu.
    Tip denetimi de derleme de bunu goremez — yalnizca uygulamayi
    calistirinca gorunur.

    `useIstek` bu dersi tasiyor: `getir` bir ref'te durur ve istegi ne
    zaman yenileyecegine YALNIZCA verilen bagimliliklar karar verir.
  */
  // MANDAL: kart bir kez acildiktan sonra kapali iken de "hazir" kalir.
  // Dogrudan `acik` verilseydi her kapat-ac istegi yeniden atardi; eski
  // surumdeki `if (sonuc?.anahtar === anahtar) return;` korumasi tam olarak
  // bunu engelliyordu ve tarayici testinde kapat-ac-kapat-ac uc istek
  // uretti. Sorgu yalnizca ANAHTAR degisince tekrarlanmali.
  const [hicAcildi, setHicAcildi] = React.useState(false);
  React.useEffect(() => {
    if (acik) setHicAcildi(true);
  }, [acik]);

  const { veri, hata, yukleniyor } = useIstek(
    (signal) =>
      getBenzer(
        oranlar as Record<string, number>,
        { arindirma, ...(lig ? { lig } : {}) },
        signal,
      ),
    [anahtar],
    {
      hazir: hicAcildi && !!anahtar && !!oranlar,
      varsayilanHata: "Sorgu başarısız",
      eskiyiKoru: false,
    },
  );

  // Orani olmayan mac icin sorulacak bir sey yok: 1/3-1/3-1/3 bir fiyat
  // degil, bilgi yoklugudur.
  if (!oranlar) return null;

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setAcik((v) => !v)}
        className="text-[11.5px] text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground"
      >
        {acik ? "gizle" : "geçmişte bu oranlarda…"}
      </button>

      {acik ? (
        <div className="mt-1.5 rounded-lg border border-line bg-muted/30 px-3 py-2 text-[11.5px]">
          {yukleniyor ? (
            <span className="text-muted-foreground">aranıyor…</span>
          ) : hata ? (
            <span className="text-danger">{hata}</span>
          ) : veri ? (
            <BenzerGovde
              veri={veri}
              arindirma={arindirma}
              onArindirma={setArindirma}
            />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function Satir({
  sembol,
  karne,
}: {
  sembol: string;
  karne: BenzerKarne;
}) {
  // Eksik anahtar `undefined` doner. Bu bir zamanlar ELLE yazilmis bir
  // cast'ti (`as BenzerSembol | undefined`) cunku `noUncheckedIndexedAccess`
  // kapaliydi ve tip `BenzerSembol` diye YALAN soyluyordu; backend bir
  // sembolu hic dondurmediginde `r.adet` render sirasinda cokuyordu —
  // bos hucre degil, BEYAZ SAYFA. Bayrak acik oldugu icin cast gereksiz:
  // daralmayi artik derleyici yapiyor.
  const r = karne.semboller[sembol];
  if (!r) {
    return (
      <tr>
        <td className="pr-2 font-mono">{sembol}</td>
        <td colSpan={5} className="py-1 text-muted-foreground">
          bu dilimde örnek yok
        </td>
      </tr>
    );
  }
  const oran = r.oran ?? 0;
  return (
    <tr>
      <td className="pr-2 font-mono">{sembol}</td>
      <td className="pr-2 text-right tabular-nums text-muted-foreground">
        {r.adet}
      </td>
      <td className="pr-2 text-right tabular-nums font-medium">
        %{(100 * oran).toFixed(1)}
      </td>
      <td className="pr-2 text-right tabular-nums text-muted-foreground">
        [%{(100 * r.ga_alt).toFixed(1)} – %{(100 * r.ga_ust).toFixed(1)}]
      </td>
      <td className="pr-2 text-right tabular-nums text-muted-foreground">
        %{(100 * r.piyasa).toFixed(1)}
      </td>
      <td className="text-right">
        {/*
          Asil okunacak sutun bu. Piyasanin dedigi aralik DISINDAYSA, o
          fiyatta piyasa sozunu tutmamis demektir. Icindeyse — ki cogu zaman
          oyledir — arac piyasayi DOGRULAMIS olur ve bu da bir cevaptir.
        */}
        {r.piyasa_ga_icinde === false ? (
          <span className="text-warning">aralık dışı</span>
        ) : (
          <span className="text-muted-foreground">uyumlu</span>
        )}
      </td>
    </tr>
  );
}

function BenzerGovde({
  veri,
  arindirma,
  onArindirma,
}: {
  veri: BenzerResponse;
  arindirma: ArindirmaYontemi;
  onArindirma: (y: ArindirmaYontemi) => void;
}) {
  const t = veri.toplam;
  if (!t.yeterli) {
    return (
      <div className="text-muted-foreground">
        Bu fiyata yakın yalnızca {t.n} maç var — yüzde okumak için yetersiz.
      </div>
    );
  }
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge>{t.n} benzer maç</Badge>
        <Badge>±{(100 * veri.tolerans).toFixed(1)} puan</Badge>
        {/* Bu ucu daha once yalnizca `toplam`, `tolerans`, `arindirma` ve
            `uyarilar` okunuyordu; gerisi hesaplanip ATILIYORDU. `evren`
            karsilastirmanin hangi havuzdan yapildigini, `marj` ise
            arindirmanin ne kadarini attigini soyler — ikisi de sayiyi
            okurken bilinmesi gereken sey. */}
        <Badge>{sayi(veri.evren)} maçlık korpus</Badge>
        <Badge>marj %{(100 * veri.marj).toFixed(1)}</Badge>
        {veri.tolerans_genisledi ? (
          <Badge ton="warning">yarıçap genişletildi</Badge>
        ) : null}
        {veri.tolerans_tavana_dayandi ? (
          <Badge ton="warning">yarıçap tavanda</Badge>
        ) : null}
      </div>

      <label className="flex items-center gap-2 text-[11px] text-muted-foreground">
        marj arındırma
        <select
          value={arindirma}
          onChange={(e) => onArindirma(e.target.value as ArindirmaYontemi)}
          className="rounded-md border border-line-strong bg-elevated px-1.5 py-0.5 text-[11px]"
        >
          {ARINDIRMA_YONTEMLERI.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </label>

      <table className="w-full">
        <thead className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="pr-2 text-left">sem</th>
            <th className="pr-2 text-right">adet</th>
            <th className="pr-2 text-right">gerçek</th>
            <th className="pr-2 text-right">%95 aralık</th>
            <th className="pr-2 text-right">piyasa</th>
            <th className="text-right">durum</th>
          </tr>
        </thead>
        <tbody>
          {SEM.map((s) => (
            <Satir key={s} sembol={s} karne={t} />
          ))}
        </tbody>
      </table>

      <LigDilimleri dilimler={veri.dilimler.lig} />

      {veri.uyarilar.length ? (
        <ul className="space-y-0.5 text-[11px] leading-relaxed text-muted-foreground">
          {veri.uyarilar.map((u, i) => (
            <li key={i}>• {u}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/**
 * Lig kirilimi — sunucu bunu hesaplayip gonderiyordu ve arayuz TAMAMEN
 * atiyordu.
 *
 * Neden degerli: "bu fiyata gecmiste ne oldu" sorusunun cevabi lige gore
 * degisebilir ve toplam yuzde o farki gizler. Neden dikkatli gosteriliyor:
 * dilim kucuklukce carpici yuzde cikma olasiligi artar, o yuzden yalnizca
 * `yeterli` olanlar listelenir ve n her zaman yaninda durur — bu aracin
 * tek gercek tehlikesi ince bir dilimdeki carpici oranin bulgu sanilmasidir.
 */
function LigDilimleri({ dilimler }: { dilimler: BenzerDilim[] }) {
  const [acik, setAcik] = React.useState(false);
  const yeterli = dilimler.filter((d) => d.karne.yeterli);
  if (!yeterli.length) return null;

  return (
    <div>
      <button
        type="button"
        onClick={() => setAcik((a) => !a)}
        aria-expanded={acik}
        className="text-[11px] text-primary hover:underline"
      >
        {acik ? "Lig kırılımını gizle" : `Lig kırılımı (${yeterli.length} lig)`}
      </button>
      {acik ? (
        <table className="mt-1 w-full">
          <thead className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="pr-2 text-left">lig</th>
              <th className="pr-2 text-right">n</th>
              {SEM.map((s) => (
                <th key={s} className="pr-2 text-right">
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {yeterli.map((d) => (
              <tr key={d.deger}>
                <td className="pr-2 font-mono">{d.deger}</td>
                <td className="tnum pr-2 text-right text-muted-foreground">
                  {d.karne.n}
                </td>
                {SEM.map((s) => {
                  const r = d.karne.semboller[s];
                  return (
                    <td key={s} className="tnum pr-2 text-right">
                      {r ? yuzde(r.oran ?? 0, 0) : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
