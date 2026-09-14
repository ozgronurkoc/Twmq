"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { ARINDIRMA_YONTEMLERI, type ArindirmaYontemi } from "@/lib/api";
import { tarihGecerli, type AnalizAyari, type LigKapsami } from "@/lib/kupon-analiz";
import type { Cizgi, LigEnvanteriSatiri } from "@/lib/types";
import { sayi, yuzde } from "@/lib/utils";
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
  ligler,
  taninmayan,
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
  /** Korpusun lig envanteri; `null` = henuz okunmadi. */
  ligler: LigEnvanteriSatiri[] | null;
  /** Kapsam `kendi` iken ligi taninmayan satirlarin 0 tabanli sirasi. */
  taninmayan: number[];
}) {
  const tarihBozuk = !tarihGecerli(ayar.tarih);

  return (
    <div className="space-y-4">
      <Select<LigKapsami>
        label="Arama evreni"
        value={ayar.kapsam}
        onChange={(v) => onChange({ ...ayar, kapsam: v })}
        options={[
          { value: "tum", label: "Tüm ligler" },
          { value: "kendi", label: "Maçın kendi ligi" },
        ]}
        hint={
          ayar.kapsam === "tum" ? (
            <>
              Her satır <strong>bütün korpusta</strong> aranır
              {ligler ? ` (${sayi(ligler.reduce((t, l) => t + l.n, 0))} maç, ${ligler.length} lig)` : ""}
              . Geniş evren örneklemi ayakta tutar; karşılığında cevap
              &quot;bu ligde&quot; değil &quot;bu fiyatta genel olarak&quot;dır.
            </>
          ) : (
            <>
              Her satır <strong>kendi lig koduyla</strong> aranır. Evren bir
              ligin boyuna düşer, yani yarıçap büyür ve örneklem küçülür —
              her satırda n ve yarıçap yazıyor, &quot;tavan&quot; uyarısı
              sıklaşırsa cevap benzer maçlardan değil sınırdan toplanmış
              demektir.
            </>
          )
        }
      />

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

      {ayar.kapsam === "kendi" && ligler ? (
        <div className="rounded-xl border border-line px-4 py-3">
          <div className="text-[12px] font-medium text-muted-foreground">
            Korpusun tanıdığı lig kodları
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
            {ligler.map((l) => (
              <span key={l.lig} className="text-[11.5px] text-muted-foreground">
                <code className="font-mono text-foreground">{l.lig}</code>{" "}
                {l.etiket} <span className="tnum opacity-60">{sayi(l.n)}</span>
              </span>
            ))}
          </div>
          {taninmayan.length ? (
            <p className="mt-2 text-[11.5px] text-danger">
              {taninmayan.map((i) => i + 1).join(", ")}. satırın lig kodu
              korpusta yok. Bu kodla arama <strong>400 dönmez, boş döner</strong>{" "}
              — yani &quot;benzer maç yok&quot; ile &quot;kodu tanımıyorum&quot;
              ayırt edilemezdi. Tablodaki lig hücrelerini yukarıdaki kodlarla
              düzeltin.
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Button tip="primary" onClick={onAnaliz} disabled={!hazir || kosuyor}>
          <Search size={15} />
          {kosuyor ? "Aranıyor…" : "15 maçı analiz et"}
        </Button>
        {!hazir ? (
          <span className="text-[12px] text-muted-foreground">
            15 satırın da oranı tam olmalı
            {tarihBozuk ? ", tarih kesmesi okunabilmeli" : ""}
            {taninmayan.length ? ", her satırın lig kodu korpusta tanınmalı" : ""}.
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
