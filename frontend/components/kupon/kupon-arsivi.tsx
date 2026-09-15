"use client";

import * as React from "react";
import { Check, FilePlus2, FolderOpen, Save, Trash2 } from "lucide-react";

import { CIZGI_ADI, CIZGI_SIRASI } from "@/lib/kupon";
import { MAC_SAYISI, type ArsivOzeti } from "@/lib/types";
import { cn, sayi } from "@/lib/utils";
import { NumberField, TextField } from "@/components/ui/controls";
import { Badge, Button, Callout } from "@/components/ui/primitives";

/**
 * Kupon arsivi: adiyla kaydet · ac · sil.
 *
 * ─── Neden birim HAFTA degil KUPON ────────────────────────────────────────
 *
 * Bir haftanin birden cok kuponu olur: biri acilis oranlariyla, oteki
 * kapanisla; biri shin, oteki orantili arindirmayla. Bunlar birbirinin
 * surumu degil AYRI denemelerdir ve yan yana durmalari gerekir. Hafta bu
 * yuzden kimlik degil ETIKET; kimlik, sunucunun verdigi numaradir.
 *
 * ─── Neden iki ayri kaydetme dugmesi ──────────────────────────────────────
 *
 * "Kaydet" ile "yeni kupon olarak kaydet" ayni ekranda iki AYRI niyettir ve
 * bir dugmenin hangisi oldugunu tahmin etmesi gerekmiyor. Acik bir kaydin
 * ustune yazmak ile ondan yeni bir deneme turetmek — ikisi de sik ve ikisi
 * de geri alinamaz.
 *
 * ─── Neden otomatik degil ─────────────────────────────────────────────────
 *
 * Tablo zaten her tus vurusunda tarayiciya yaziliyor (yenileme
 * kaybettirmiyor). Arsiv baska bir sey: bir kuponu KAYDA gecirmek bilincli
 * bir karardir.
 */
export function KuponArsivi({
  ad,
  onAdChange,
  hafta,
  onHaftaChange,
  not,
  onNotChange,
  kayitlar,
  acikNo,
  kosuyor,
  hata,
  onKaydet,
  onYeniOlarakKaydet,
  onAc,
  onSil,
  kaydedildi,
  analizVar,
  kuponVar,
}: {
  ad: string;
  onAdChange: (v: string) => void;
  /** Hafta ETİKETİ; 0 = boş bırakıldı. */
  hafta: number;
  onHaftaChange: (v: number) => void;
  not: string;
  onNotChange: (v: string) => void;
  kayitlar: ArsivOzeti[];
  /** Ekrandaki kayıt hangi numaradan açıldı — `null` = henüz kaydedilmedi. */
  acikNo: number | null;
  kosuyor: boolean;
  hata: string | null;
  onKaydet: () => void;
  onYeniOlarakKaydet: () => void;
  onAc: (no: number) => void;
  onSil: (no: number) => void;
  kaydedildi: string | null;
  /** Zincirin durumu — kaydedilecek olan bu. */
  analizVar: boolean;
  kuponVar: boolean;
}) {
  const acik = kayitlar.find((k) => k.no === acikNo) ?? null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_110px]">
        <TextField
          label="Kupon adı"
          value={ad}
          placeholder="1 numaralı kupon"
          onChange={onAdChange}
          hint="Serbest. Ad kimlik değil — kaydın kimliği numarasıdır, iki kupon aynı adı taşıyabilir."
        />
        <NumberField
          label="Hafta"
          value={hafta}
          min={0}
          max={60}
          onChange={onHaftaChange}
          hint="0 = boş"
        />
      </div>

      <TextField
        label="Not"
        value={not}
        placeholder="iddaa bülteni · açılış · 14 Eylül"
        onChange={onNotChange}
        hint="Oranların hangi bültenden ve hangi gün alındığı. Kayıtta açılış mı kapanış mı olduğu ancak böyle okunur."
      />

      {/* Kaydedilecek zincir, KAYDETMEDEN ONCE gorunur durur. */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11.5px] text-muted-foreground">Kayda girecek:</span>
        <Badge ton="success">girdi</Badge>
        <Badge ton={analizVar ? "success" : "neutral"}>
          analiz{analizVar ? "" : " yok"}
        </Badge>
        <Badge ton={kuponVar ? "success" : "neutral"}>
          kupon{kuponVar ? "" : " yok"}
        </Badge>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button tip="primary" onClick={onKaydet} disabled={kosuyor}>
          {kaydedildi ? <Check size={15} /> : <Save size={15} />}
          {kosuyor
            ? "Kaydediliyor…"
            : acik
              ? `Kaydet (#${acik.no} üstüne)`
              : "Arşive kaydet"}
        </Button>
        {acik ? (
          <Button tip="outline" onClick={onYeniOlarakKaydet} disabled={kosuyor}>
            <FilePlus2 size={15} />
            Yeni kupon olarak kaydet
          </Button>
        ) : null}
        {kaydedildi ? (
          <span className="text-[12px] text-success">Kaydedildi — {kaydedildi}</span>
        ) : null}
      </div>

      {hata ? (
        <Callout ton="danger" baslik="Arşiv işlemi başarısız">
          {hata}
        </Callout>
      ) : null}

      <div className="border-t border-line pt-4">
        <div className="mb-2 flex items-center gap-2 text-[12px] font-medium text-muted-foreground">
          <FolderOpen size={13} />
          Kayıtlı kuponlar
          {kayitlar.length ? <Badge>{kayitlar.length}</Badge> : null}
        </div>
        {kayitlar.length ? (
          <ul className="space-y-1.5">
            {kayitlar.map((k) => (
              <li
                key={k.no}
                className={cn(
                  "flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border px-3 py-2",
                  k.no === acikNo ? "border-primary/40 bg-accent" : "border-line",
                )}
              >
                <span className="tnum shrink-0 text-[12px] text-muted-foreground">
                  #{k.no}
                </span>
                <span className="min-w-0 max-w-[220px] shrink-0 truncate text-[13px] font-medium">
                  {k.ad}
                </span>
                <Zincir kayit={k} />
                <span className="tnum text-[11.5px] text-muted-foreground">
                  {k.hafta ? `h${k.hafta} · ` : ""}
                  {k.ayar ? `${k.ayar.cizgi}/${k.ayar.arindirma}` : "—"}
                  {k.kupon_var && k.kolon ? ` · ${sayi(k.kolon)} kolon` : ""}
                </span>
                {k.not ? (
                  <span className="min-w-0 flex-1 truncate text-[11.5px] text-muted-foreground/80">
                    {k.not}
                  </span>
                ) : (
                  <span className="flex-1" />
                )}
                <span className="tnum shrink-0 text-[11px] text-muted-foreground/70">
                  {k.guncellendi.slice(0, 10)}
                </span>
                <span className="flex shrink-0 items-center gap-1">
                  <Button tip="ghost" boyut="sm" onClick={() => onAc(k.no)} disabled={kosuyor}>
                    Aç
                  </Button>
                  <Button
                    tip="ghost"
                    boyut="sm"
                    onClick={() => onSil(k.no)}
                    disabled={kosuyor}
                    title={`#${k.no} — ${k.ad} kaydını sil`}
                    aria-label={`${k.no} numaralı kuponu sil`}
                  >
                    <Trash2 size={13} />
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[12px] text-muted-foreground">
            Henüz kayıt yok. Tabloyu doldurup analiz ettikten sonra{" "}
            <strong>Arşive kaydet</strong> deyin; kayıt sunucuda{" "}
            <code className="font-mono text-[11px]">
              data/kupon_arsivi/&lt;sezon&gt;/kupon_NNN.json
            </code>{" "}
            olarak durur ve git&apos;e girebilir.
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Kaydın zinciri tek bakışta: girdi · analiz · kupon · sonuç.
 *
 * Yarım kalmış bir kupon, kaydı AÇMADAN görünmeli — listedeki asıl bilgi bu.
 *
 * Girdi halkası artık İKİ çizgiyi birden sayıyor ve "tam" demek için
 * **en az bir** çizginin 15/15 olması yetiyor: elinde tek bülten olan biri
 * de kupon kurabiliyor ve o kayıt yarım sayılmamalı. Kaç çizginin hazır
 * olduğu ipucunda yazıyor.
 */
function Zincir({ kayit }: { kayit: ArsivOzeti }) {
  const oranli = kayit.oranli_mac ?? ({} as Record<string, number>);
  const sayimlar = CIZGI_SIRASI.map((c) => [c, oranli[c] ?? 0] as const);
  const halkalar: [string, boolean, string][] = [
    [
      "G",
      sayimlar.some(([, n]) => n === MAC_SAYISI),
      `girdi: ${sayimlar.map(([c, n]) => `${CIZGI_ADI[c]} ${n}/${MAC_SAYISI}`).join(" · ")}`,
    ],
    [
      "A",
      kayit.analiz_var,
      kayit.analiz_olculdu
        ? `analiz: ${kayit.analiz_olculdu.slice(0, 10)} ölçüldü`
          + (kayit.analiz_cizgileri?.length
            ? ` (${kayit.analiz_cizgileri.map((c) => CIZGI_ADI[c]).join(", ")})`
            : "")
        : "analiz koşulmadı",
    ],
    [
      "K",
      kayit.kupon_var || kayit.sekilli_sayisi > 0,
      [
        kayit.kupon_var ? "ikili kupon kuruldu" : "ikili kupon kurulmadı",
        kayit.sekilli_sayisi
          ? `${kayit.sekilli_sayisi} şekilli kupon`
          : "şekilli kupon yok",
      ].join(" · "),
    ],
    ["S", kayit.sonuc_var, kayit.sonuc_var ? "sonuçlar girildi" : "sonuç girilmedi"],
  ];
  return (
    <span className="flex shrink-0 items-center gap-0.5" aria-label="kaydın zinciri">
      {halkalar.map(([harf, var_, baslik]) => (
        <span
          key={harf}
          title={baslik}
          className={cn(
            "inline-flex h-[18px] w-[18px] items-center justify-center rounded",
            "font-mono text-[10px] font-semibold",
            var_
              ? "bg-success-soft text-success"
              : "bg-muted text-muted-foreground/50",
          )}
        >
          {harf}
        </span>
      ))}
    </span>
  );
}
