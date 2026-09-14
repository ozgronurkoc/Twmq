"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { ARINDIRMA_YONTEMLERI, type ArindirmaYontemi } from "@/lib/api";
import { tarihGecerli, type AnalizAyari } from "@/lib/kupon-analiz";
import type { Cizgi } from "@/lib/types";
import { yuzde } from "@/lib/utils";
import { Collapsible, NumberField, Select, TextField } from "@/components/ui/controls";
import { Button } from "@/components/ui/primitives";

/**
 * 15 satirin TAMAMI icin gecerli sorgu ayarlari.
 *
 * ─── Neden tek cubuk, neden satir basina degil ────────────────────────────
 *
 * Satir basina cizgi/arindirma secilebilseydi tablonun 15 satiri birbiriyle
 * kiyaslanamaz olurdu: biri acilis evreninde, oteki kapanista aranmis iki
 * karne ayni sutunda yan yana duramaz. Ayar kuponun tamaminin ozelligidir.
 *
 * ─── Neden dugmeye bagli ──────────────────────────────────────────────────
 *
 * `/oran-analizi` ayni karari veriyor ve gerekcesi burada daha da agir: bir
 * ayar degisikligi TEK sorgu degil 15 sorgu demek. Canli kosan bir form,
 * "Hedef orneklem" kutusunda 2-0-0 yazarken uc kez 15 sorgu atardi.
 */
export function AnalizAyarlari({
  ayar,
  onChange,
  onAnaliz,
  hazir,
  kosuyor,
  ortalamaMarj,
  bayat,
}: {
  ayar: AnalizAyari;
  onChange: (next: AnalizAyari) => void;
  onAnaliz: () => void;
  /** 15 satirin orani tam ve ayar gecerli mi. */
  hazir: boolean;
  kosuyor: boolean;
  /** Tablodaki satirlarin ortalama marji — arindirma secimi bunu okur. */
  ortalamaMarj: number | null;
  /** Ekrandaki sonuc, su anki girdi/ayarla ayrismis mi. */
  bayat: boolean;
}) {
  const tarihBozuk = !tarihGecerli(ayar.tarih);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Select<Cizgi>
          label="Fiyat çizgisi"
          value={ayar.cizgi}
          onChange={(v) => onChange({ ...ayar, cizgi: v })}
          options={[
            { value: "kapanis", label: "Kapanış" },
            { value: "acilis", label: "Açılış" },
          ]}
          hint="Tabloya yazdığınız oran açılış oranıysa açılışı seçin: aynı maçın iki fiyatı arasındaki fark ölçülmüş bir şeydir ve kapanış evreninde arama yapmak elmayı armutla karşılaştırmak olur."
        />
        <Select<ArindirmaYontemi>
          label="Marj arındırma"
          value={ayar.arindirma}
          onChange={(v) => onChange({ ...ayar, arindirma: v })}
          options={ARINDIRMA_YONTEMLERI.map((y) => ({ value: y, label: y }))}
          hint={
            ortalamaMarj == null ? (
              "Eşleme oran uzayında değil, marj arındırıldıktan sonra olasılık uzayında yapılır."
            ) : (
              <>
                Tablonun ortalama marjı{" "}
                <strong>{yuzde(ortalamaMarj)}</strong>
                {ortalamaMarj > 0.12
                  ? " — korpus ~%7 marjlı; bu farkta yöntem sonucu görünür biçimde değiştirir."
                  : "."}
              </>
            )
          }
        />
      </div>

      <Collapsible baslik="Gelişmiş" hint="örneklem · kronolojik kesme">
        <div className="grid grid-cols-1 gap-3 pt-1 sm:grid-cols-2">
          <NumberField
            label="Hedef örneklem"
            value={ayar.enAz}
            min={1}
            max={5000}
            onChange={(v) => onChange({ ...ayar, enAz: v })}
            hint="Uyarlanan aramanın ulaşmaya çalıştığı maç sayısı. Yarıçap buna ulaşana kadar büyür, ±5 puanda durur; fiilen kullanılan yarıçap her satırda yazar."
          />
          <TextField
            label="Tarih kesmesi"
            value={ayar.tarih}
            placeholder="2026-09-01"
            bozuk={tarihBozuk}
            onChange={(v) => onChange({ ...ayar, tarih: v })}
            hint={
              tarihBozuk
                ? "YYYY-AA-GG olmalı ve takvimde var olan bir gün olmalı."
                : "YYYY-AA-GG. Verilirse yalnızca bu günden ÖNCEKİ maçlar aranır — geçmiş bir haftayı sınarken sızıntısız sorgu ancak böyle kurulur."
            }
          />
        </div>
      </Collapsible>

      <div className="flex flex-wrap items-center gap-3">
        <Button tip="primary" onClick={onAnaliz} disabled={!hazir || kosuyor}>
          <Search size={15} />
          {kosuyor ? "Aranıyor…" : "15 maçı analiz et"}
        </Button>
        {!hazir ? (
          <span className="text-[12px] text-muted-foreground">
            15 satırın da oranı tam olmalı{tarihBozuk ? " ve tarih kesmesi okunabilmeli" : ""}.
          </span>
        ) : bayat ? (
          <span className="text-[12px] text-warning">
            Aşağıdaki sonuç, tablodaki güncel oran/ayarla üretilmedi — yeniden
            analiz edin.
          </span>
        ) : null}
      </div>
    </div>
  );
}
