"use client";

import * as React from "react";
import { Check, Link2, RotateCcw } from "lucide-react";

import { adresiYaz, paylasimAdresi, type Kurulum } from "@/lib/kurulum";
import { panoyaKopyala } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";

/**
 * Kurulumun tasima cubugu: baglanti uret / basa don.
 *
 * "Kaydedildi" yazisi surekli durur, bir bildirim olarak parlayip
 * kaybolmaz. Kalicilik sessiz calisir; kullanicinin bilmesi gereken sey
 * "az once kaydettim" degil, "burada birakirsam duruyor olacak"tir.
 */
export function KurulumBar({
  kurulum,
  onSifirla,
  disabled,
}: {
  kurulum: Kurulum;
  onSifirla: () => void;
  disabled?: boolean;
}) {
  const [durum, setDurum] = React.useState<"bos" | "kopyalandi" | "hata">("bos");
  const [onay, setOnay] = React.useState(false);

  React.useEffect(() => {
    if (durum === "bos") return;
    const id = window.setTimeout(() => setDurum("bos"), 2200);
    return () => window.clearTimeout(id);
  }, [durum]);

  // Onay penceresi kendiliginden kapanir; yanlislikla acilan bir "emin
  // misin" ekranda kalip sonraki tiklamayi yutmasin.
  React.useEffect(() => {
    if (!onay) return;
    const id = window.setTimeout(() => setOnay(false), 4000);
    return () => window.clearTimeout(id);
  }, [onay]);

  async function baglantiKopyala() {
    // Once adres cubugu: pano calismasa da kullaniciya gosterecek dogru bir
    // adres kalsin. Panodan once yazilir, cunku catch dalindaki tavsiye
    // ancak adres guncelse dogrudur.
    adresiYaz(kurulum);
    try {
      await panoyaKopyala(paylasimAdresi(kurulum));
      setDurum("kopyalandi");
    } catch {
      setDurum("hata");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button tip="outline" boyut="sm" onClick={baglantiKopyala} disabled={disabled}>
        {durum === "kopyalandi" ? <Check size={13} /> : <Link2 size={13} />}
        {durum === "kopyalandi" ? "Bağlantı kopyalandı" : "Bağlantıyı kopyala"}
      </Button>

      {onay ? (
        <>
          <Button
            tip="outline"
            boyut="sm"
            className="border-danger/50 text-danger"
            onClick={() => {
              setOnay(false);
              onSifirla();
            }}
          >
            Emin misin?
          </Button>
          <Button tip="ghost" boyut="sm" onClick={() => setOnay(false)}>
            Vazgeç
          </Button>
        </>
      ) : (
        <Button tip="ghost" boyut="sm" onClick={() => setOnay(true)} disabled={disabled}>
          <RotateCcw size={13} />
          Sıfırla
        </Button>
      )}

      <p className="min-w-0 flex-1 text-right text-[11px] leading-tight text-muted-foreground">
        {durum === "hata"
          ? "Pano kullanılamadı — adres çubuğundan kopyalayabilirsin."
          : "Kurulum bu tarayıcıya kaydediliyor."}
      </p>
    </div>
  );
}
