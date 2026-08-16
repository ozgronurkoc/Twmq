"use client";

import * as React from "react";

import { ETIKET_SINIR, temizEtiketler } from "@/lib/kurulum";
import { MAC_SAYISI } from "@/lib/types";
import { Collapsible } from "@/components/ui/controls";
import { Button } from "@/components/ui/primitives";

/**
 * Mac adlarinin toplu girisi: satir basina bir ad.
 *
 * NEDEN TEK TEK 15 KUTU DEGIL: adlar neredeyse her zaman bir yerden
 * KOPYALANIR (bulten, hafta detayi, gazete listesi). Yapistirma tek
 * hamlede biter; 15 ayri kutu ayni isi 15 hamleye bolerdi ve zaten dar
 * olan girdi kolonuna 15 kutu daha eklerdi. Tek bir adi duzeltmek de
 * burada mumkun — ilgili satiri degistirmek yeter.
 *
 * Adlar cozume HIC girmez; motor yalnizca isaretleri gorur. Buradaki tek
 * is, 16 satirlik bir kuponu elle doldururken hangi macin hangisi
 * oldugunu bilmek.
 */
export function AdGirisi({
  labels,
  onChange,
  disabled,
}: {
  labels: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
}) {
  // Yazarken metin ALANIN kendisinde durur; her tusa basista 15'e
  // bolup birlestirmek imleci satir sonuna atardi.
  const [taslak, setTaslak] = React.useState<string | null>(null);
  const metin = taslak ?? labels.join("\n");
  const satirlar = metin.split("\n").filter((s) => s.trim()).length;
  const doluAd = labels.filter(Boolean).length;

  function yaz(ham: string) {
    setTaslak(ham);
    onChange(temizEtiketler(ham.split("\n")));
  }

  return (
    <Collapsible
      baslik="Maç adları"
      hint={
        doluAd
          ? `${doluAd} maçın adı var — ızgarada görünüyor`
          : "Satır başına bir ad; ızgarada işaretlerin üstünde görünür"
      }
    >
      <div className="space-y-2">
        <textarea
          value={metin}
          disabled={disabled}
          onChange={(e) => yaz(e.target.value)}
          onBlur={() => setTaslak(null)}
          rows={MAC_SAYISI}
          spellCheck={false}
          aria-label="Maç adları, satır başına bir ad"
          placeholder={"Galatasaray – Fenerbahçe\nBeşiktaş – Trabzonspor\n…"}
          className="scroll-slim w-full resize-y rounded-xl border border-line bg-background px-3 py-2 text-[12.5px] leading-relaxed transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button
            tip="ghost"
            boyut="sm"
            disabled={disabled || !doluAd}
            onClick={() => {
              setTaslak(null);
              onChange(Array(MAC_SAYISI).fill(""));
            }}
          >
            Adları temizle
          </Button>
          <p className="min-w-0 flex-1 text-[11px] leading-relaxed text-muted-foreground">
            {satirlar > MAC_SAYISI ? (
              <span className="text-warning">
                {satirlar} satır var; yalnızca ilk {MAC_SAYISI} tanesi kullanılır.
              </span>
            ) : (
              <>
                {satirlar}/{MAC_SAYISI} satır. Adlar bu tarayıcıda saklanır,{" "}
                <strong>paylaşılan bağlantıya girmez</strong> ve sonucu
                etkilemez. Satır {ETIKET_SINIR} karakterde kırpılır.
              </>
            )}
          </p>
        </div>
      </div>
    </Collapsible>
  );
}
