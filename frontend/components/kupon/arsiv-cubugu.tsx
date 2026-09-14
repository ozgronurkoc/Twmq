"use client";

import * as React from "react";
import { Check, FolderOpen, Save, Trash2 } from "lucide-react";

import type { ArsivOzeti } from "@/lib/types";
import { cn } from "@/lib/utils";
import { NumberField, TextField } from "@/components/ui/controls";
import { Badge, Button, Callout } from "@/components/ui/primitives";

/**
 * Hafta arsivi: kaydet · ac · sil.
 *
 * ─── Neden hafta NUMARASI, neden serbest bir ad degil ─────────────────────
 *
 * Kayit dosya sisteminde `hafta_NN.json` olarak duruyor ve depodaki oteki
 * hafta ailesiyle (`data/super_toto/<sezon>/hafta_NN.json`) ayni adi
 * tasiyor. Serbest ad ("bu haftaki", "yeni deneme") iki hafta sonra hangi
 * haftaya ait oldugunu soyleyemezdi; numara ise sezonun kendi sirasidir.
 * Serbest metin yine de var ama YANINDA: `not` alani.
 *
 * ─── Neden "kaydet" otomatik degil ────────────────────────────────────────
 *
 * Tablo zaten her tus vurusunda tarayiciya yaziliyor (yenileme
 * kaybettirmiyor). Arsiv baska bir sey: bir haftayi KAYDA gecirmek bilincli
 * bir karardir ve yanlislikla 5. haftanin uzerine 6. haftanin yarim
 * tablosunu yazmak, geri alinamayacak tek islem olurdu.
 */
export function ArsivCubugu({
  hafta,
  onHaftaChange,
  not,
  onNotChange,
  kayitlar,
  yuklenen,
  kosuyor,
  hata,
  onKaydet,
  onAc,
  onSil,
  kaydedildi,
}: {
  hafta: number;
  onHaftaChange: (v: number) => void;
  not: string;
  onNotChange: (v: string) => void;
  kayitlar: ArsivOzeti[];
  /** Ekrandaki tablo hangi haftadan yuklendi — `null` = arsivden gelmedi. */
  yuklenen: number | null;
  kosuyor: boolean;
  hata: string | null;
  onKaydet: () => void;
  onAc: (hafta: number) => void;
  onSil: (hafta: number) => void;
  /** Son kaydetmenin zamani; kisa sure "kaydedildi" gostermek icin. */
  kaydedildi: string | null;
}) {
  const mevcut = kayitlar.find((k) => k.hafta === hafta) ?? null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[140px_1fr]">
        <NumberField
          label="Hafta"
          value={hafta}
          min={1}
          max={60}
          onChange={onHaftaChange}
          hint={mevcut ? "bu hafta kayıtlı" : "yeni kayıt"}
        />
        <TextField
          label="Not"
          value={not}
          placeholder="iddaa bülteni · kapanış · 14 Eylül"
          onChange={onNotChange}
          hint="Oranların hangi bültenden ve hangi gün alındığı. Kayıtta açılış mı kapanış mı olduğu ancak böyle okunur."
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button tip="primary" onClick={onKaydet} disabled={kosuyor}>
          {kaydedildi ? <Check size={15} /> : <Save size={15} />}
          {kosuyor ? "Kaydediliyor…" : mevcut ? `${hafta}. haftanın üstüne yaz` : "Arşive kaydet"}
        </Button>
        {kaydedildi ? (
          <span className="text-[12px] text-success">
            Kaydedildi — {kaydedildi}
          </span>
        ) : mevcut ? (
          <span className="text-[12px] text-warning">
            {hafta}. hafta zaten kayıtlı ({mevcut.oranli_mac}/15 oran,{" "}
            {mevcut.guncellendi.slice(0, 10)}) — kaydetmek üstüne yazar.
          </span>
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
          Kayıtlı haftalar
          {kayitlar.length ? <Badge>{kayitlar.length}</Badge> : null}
        </div>
        {kayitlar.length ? (
          <ul className="space-y-1.5">
            {kayitlar.map((k) => (
              <li
                key={k.hafta}
                className={cn(
                  "flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border px-3 py-2",
                  k.hafta === yuklenen ? "border-primary/40 bg-accent" : "border-line",
                )}
              >
                <span className="tnum w-[74px] shrink-0 text-[13px] font-medium">
                  {k.hafta}. hafta
                </span>
                <span className="tnum text-[11.5px] text-muted-foreground">
                  {k.oranli_mac}/15 oran · {k.adli_mac}/15 ad
                  {k.ayar ? ` · ${k.ayar.cizgi}/${k.ayar.arindirma}` : ""}
                  {k.sonuc_var ? " · sonuçlu" : ""}
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
                  <Button
                    tip="ghost"
                    boyut="sm"
                    onClick={() => onAc(k.hafta)}
                    disabled={kosuyor}
                  >
                    Aç
                  </Button>
                  <Button
                    tip="ghost"
                    boyut="sm"
                    onClick={() => onSil(k.hafta)}
                    disabled={kosuyor}
                    title={`${k.hafta}. haftanın kaydını sil`}
                    aria-label={`${k.hafta}. haftanın kaydını sil`}
                  >
                    <Trash2 size={13} />
                  </Button>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[12px] text-muted-foreground">
            Henüz kayıt yok. Tabloyu doldurup <strong>Arşive kaydet</strong>{" "}
            deyin; kayıt sunucuda{" "}
            <code className="font-mono text-[11px]">
              data/kupon_arsivi/&lt;sezon&gt;/hafta_NN.json
            </code>{" "}
            olarak durur ve git&apos;e girebilir.
          </p>
        )}
      </div>
    </div>
  );
}
