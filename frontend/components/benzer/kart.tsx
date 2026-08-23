"use client";

import * as React from "react";

import { ApiError, getBenzer } from "@/lib/api";
import type { BenzerKarne, BenzerResponse } from "@/lib/types";
import { Badge } from "@/components/ui/primitives";

const SEM = ["1", "0", "2"] as const;

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
  // Veri, HANGI sorguya ait oldugu bilgisiyle birlikte tutulur; boylece
  // oran degisirse eski cevap gosterilmez ve ayni oran icin ikinci kez
  // istek atilmaz.
  const [sonuc, setSonuc] = React.useState<{
    anahtar: string;
    veri: BenzerResponse;
  } | null>(null);
  const [hata, setHata] = React.useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = React.useState(false);

  const anahtar = oranlar
    ? `${SEM.map((s) => oranlar[s]).join(",")}|${lig ?? ""}`
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
  */
  React.useEffect(() => {
    if (!acik || !anahtar || !oranlar) return;
    if (sonuc?.anahtar === anahtar) return;
    let iptal = false;
    const ac = new AbortController();
    setYukleniyor(true);
    getBenzer(oranlar, lig ? { lig } : undefined, ac.signal)
      .then((d) => {
        if (iptal) return;
        setSonuc({ anahtar, veri: d });
        setHata(null);
      })
      .catch((e) => {
        if (iptal) return;
        if (e instanceof DOMException && e.name === "AbortError") return;
        setHata(e instanceof ApiError ? e.message : "Sorgu başarısız");
      })
      .finally(() => {
        if (!iptal) setYukleniyor(false);
      });
    return () => {
      iptal = true;
      ac.abort();
    };
    // `sonuc` ve `oranlar` bilerek listede DEGIL: ikisi de her render'da
    // yeni kimlik alabilir ve dongunun kaynagi tam olarak budur. Sorguyu
    // belirleyen tek sey `anahtar`dir.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [acik, anahtar]);

  const veri = sonuc?.anahtar === anahtar ? sonuc.veri : null;

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
            <BenzerGovde veri={veri} />
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
  const r = karne.semboller[sembol];
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

function BenzerGovde({ veri }: { veri: BenzerResponse }) {
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
        <Badge>{veri.arindirma}</Badge>
      </div>

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
