"use client";

import * as React from "react";
import { Save, Trash2, Upload } from "lucide-react";

import {
  AD_UZUNLUK,
  KUPON_SINIRI,
  kuponKaydet,
  kuponSil,
  kuponlariOku,
  ozetCikar,
  type KayitliKupon,
} from "@/lib/kupon-deposu";
import type { ModeId, Sembol, SolveResult } from "@/lib/types";
import { cn, sayi, secimMetni } from "@/lib/utils";
import { Badge, Button, Callout } from "@/components/ui/primitives";
import { TextField } from "@/components/ui/controls";

/**
 * Adlandirilmis kupon kaydi.
 *
 * Neden isaretler + mod + varyant saklaniyor da olasiliklar saklanmiyor:
 * kaydin isi "hangi maclara ne oynadim"i hatirlamak. Olasilik girdisi
 * tahmindir, kupona yazilmaz ve haftadan haftaya degisir; onu da geri
 * yuklemek kullanicinin guncel tahminini sessizce ezerdi.
 *
 * Uretilmis formulun satir tablosu da saklanir — yalnizca kayit anindaki
 * hali. Ayni isaretlerle formulu yeniden uretmek deterministiktir (seed
 * sabit), ama motor ayarlari degismisse sonuc farkli cikabilir; bu yuzden
 * tablo "o gun ne oynandi"nin kaydi olarak durur, yeniden hesaplanmaz.
 */
export function KuponDeposu({
  matches,
  mode,
  variant,
  sonuc,
  onYukle,
  disabled,
}: {
  matches: Sembol[][];
  mode: ModeId;
  variant: number;
  sonuc: SolveResult | null;
  onYukle: (k: KayitliKupon) => void;
  disabled?: boolean;
}) {
  // Depo yalnizca baglandiktan sonra okunur: sunucuda localStorage yok ve
  // ilk cizimde okumak hydration uyusmazligi uretir.
  const [liste, setListe] = React.useState<KayitliKupon[]>([]);
  const [ad, setAd] = React.useState("");
  const [not, setNot] = React.useState<{ ton: "success" | "danger"; metin: string } | null>(null);
  const [silinecek, setSilinecek] = React.useState<string | null>(null);

  React.useEffect(() => {
    setListe(kuponlariOku());
  }, []);

  const temizAd = ad.trim();
  const cakisan = liste.find((k) => k.ad === temizAd) ?? null;

  function kaydet() {
    if (!temizAd) {
      setNot({ ton: "danger", metin: "Önce bir kupon adı gir." });
      return;
    }
    const sonucIslemi = kuponKaydet({
      ad: temizAd,
      matches,
      mode,
      variant,
      ozet: sonuc ? ozetCikar(sonuc) : null,
    });

    if (!sonucIslemi.ok) {
      setNot({ ton: "danger", metin: sonucIslemi.hata });
      return;
    }

    setListe(sonucIslemi.liste);
    setAd("");
    setNot({
      ton: "success",
      metin: sonucIslemi.satirDusuruldu
        ? `«${temizAd}» kaydedildi ama depolama dolduğu için satır tablosu saklanamadı — işaretler duruyor.`
        : `«${temizAd}» kaydedildi.`,
    });
  }

  function sil(k: KayitliKupon) {
    setListe(kuponSil(k.ad));
    setSilinecek(null);
    setNot({ ton: "success", metin: `«${k.ad}» silindi.` });
  }

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-2">
        <div className="min-w-0 flex-1">
          <TextField
            label="Kupon adı"
            value={ad}
            onChange={(v) => {
              setAd(v);
              setNot(null);
            }}
            onEnter={kaydet}
            placeholder="ör. 51. hafta — bankolu"
            maxLength={AD_UZUNLUK}
            disabled={disabled}
          />
        </div>
        <Button
          tip="outline"
          onClick={kaydet}
          disabled={disabled || !temizAd}
          title={cakisan ? "Aynı adlı kaydın üzerine yazılır" : "Bu işaretleri kaydet"}
        >
          <Save size={15} />
          {cakisan ? "Üzerine yaz" : "Kaydet"}
        </Button>
      </div>

      <p className="text-[11.5px] leading-relaxed text-muted-foreground">
        {sonuc ? (
          <>
            İşaretler, mod ve üretilen{" "}
            <strong>{sayi(sonuc.satir_sayisi)} satırlık</strong> tablo birlikte
            saklanır.
          </>
        ) : (
          <>
            Henüz formül üretilmedi — yalnızca işaretler ve mod saklanır. Formülü
            de kaydetmek için önce <strong>Formülü üret</strong>&apos;e bas.
          </>
        )}{" "}
        Kayıt bu tarayıcıda kalır, başka cihaza geçmez.
      </p>

      {cakisan ? (
        <Callout ton="warning" baslik={`«${cakisan.ad}» zaten var`}>
          Kaydedersen üzerine yazılır.
        </Callout>
      ) : null}

      {not ? (
        <Callout ton={not.ton === "success" ? "success" : "danger"}>{not.metin}</Callout>
      ) : null}

      {liste.length ? (
        <ul className="space-y-2">
          {liste.map((k) => (
            <li
              key={k.ad}
              className="rounded-xl border border-line bg-elevated px-3 py-2.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-[13px] font-medium">{k.ad}</div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground">
                    {new Date(k.ts).toLocaleString("tr-TR", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </div>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  <Button
                    tip="ghost"
                    boyut="sm"
                    onClick={() => onYukle(k)}
                    disabled={disabled}
                    title="İşaretleri, modu ve varyantı forma yükle"
                  >
                    <Upload size={13} />
                    Yükle
                  </Button>
                  <Button
                    tip="ghost"
                    boyut="sm"
                    onClick={() => (silinecek === k.ad ? sil(k) : setSilinecek(k.ad))}
                    onBlur={() => setSilinecek((s) => (s === k.ad ? null : s))}
                    className={cn(silinecek === k.ad && "text-danger")}
                    title={silinecek === k.ad ? "Tekrar bas, silinsin" : "Sil"}
                  >
                    <Trash2 size={13} />
                    {silinecek === k.ad ? "Emin misin?" : "Sil"}
                  </Button>
                </div>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <Badge>{k.mode}</Badge>
                {k.variant ? <Badge>varyant {k.variant}</Badge> : null}
                {k.ozet ? (
                  <>
                    <Badge ton={k.ozet.guaranteed ? "success" : "warning"}>
                      {k.ozet.guaranteed ? "14-garanti" : "garanti yok"}
                    </Badge>
                    <Badge>
                      {sayi(k.ozet.satir_sayisi)} satır ·{" "}
                      {sayi(k.ozet.kolon_bedeli)} kolon
                    </Badge>
                    {k.ozet.rows ? null : (
                      <Badge ton="warning" title="Depolama dolduğu için tablo saklanamadı">
                        tablo yok
                      </Badge>
                    )}
                  </>
                ) : (
                  <Badge ton="neutral">formül üretilmedi</Badge>
                )}
              </div>

              {/* CLI'ye oldugu gibi yapistirilabilen `--picks` dizesi. */}
              <div className="tnum mt-2 break-all font-mono text-[11px] text-muted-foreground">
                {secimMetni(k.matches)}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-xl border border-dashed border-line px-3 py-4 text-center text-[12px] text-muted-foreground">
          Kayıtlı kupon yok. En fazla {KUPON_SINIRI} kupon saklanabilir.
        </p>
      )}
    </div>
  );
}
