import { MAC_SAYISI, SEMBOLLER, type Sembol } from "./types";

/**
 * Kupon kurucunun GIRDISI — 15 satirlik elle doldurulan mac tablosu.
 *
 * Bu modul saf: React yok, istek yok, `window` erisimi yalnizca depo
 * fonksiyonlarinda ve orada da korumali (`check.mjs` modulu dogrudan
 * kosabilsin diye — `lib/kurulum.ts` ile ayni doktrin).
 *
 * ─── Oran neden METIN tutuluyor ───────────────────────────────────────────
 *
 * `1.` yazmakta olan biri sayiya cevrilen bir alanda her tus vuruşunda
 * alanin altindan kayan bir deger gorur (`components/oran-analizi/parts.tsx`
 * `OranKutusu` ayni karari ayni gerekceyle veriyor). Cevirme yalnizca sorgu
 * kurulurken, tek yerde yapilir: `oranSayilari`.
 *
 * ─── Lig neden serbest metin ──────────────────────────────────────────────
 *
 * Korpusun lig sozlugu SUNUCUDA (`odds.LIG_ADLARI`) ve `lib/types.ts`
 * bilerek onun kopyasini tutmuyor: *"ceviri SUNUCUDA yapilir, harita orada
 * zaten var, buraya kopyalansaydi ayrisabilen ikinci bir sozluk olurdu."*
 * Ayni kural burada da gecerli. Ustelik bu alan sorgunun parcasi DEGIL —
 * arama tum ligler uzerinde yapilacak — yani lig, kullanicinin kendi
 * duzeni icin duran bir etikettir.
 */
export interface KuponSatiri {
  /** Serbest metin: `T1`, `Süper Lig`, `TR` — ne yazildiysa o. */
  lig: string;
  ev: string;
  dep: string;
  /** Ham metin hâliyle 1 / 0 / 2 orani. Bos olabilir. */
  oran: Record<Sembol, string>;
}

/** Metin alanlarinin en fazla uzunlugu — uzun bir yapistirma depoyu sismesin. */
export const METIN_SINIR = 40;

/** Oran metninin en fazla uzunlugu; `14.06` uzun ucta bile 5 karakter. */
export const ORAN_SINIR = 8;

export function bosSatir(): KuponSatiri {
  return { lig: "", ev: "", dep: "", oran: { "1": "", "0": "", "2": "" } };
}

export function bosKupon(): KuponSatiri[] {
  return Array.from({ length: MAC_SAYISI }, bosSatir);
}

/** Tek bir oran hucresi okunabilir mi — bos hucre "bozuk" DEGILDIR. */
export function oranHucresiBozuk(ham: string): boolean {
  if (ham.trim() === "") return false;
  const v = Number(ham);
  return !(Number.isFinite(v) && v > 1);
}

/** Satirin uc orani da okunabiliyor mu. */
export function oranTam(satir: KuponSatiri): boolean {
  return SEMBOLLER.every((s) => {
    const v = Number(satir.oran[s]);
    return satir.oran[s].trim() !== "" && Number.isFinite(v) && v > 1;
  });
}

/** Satirda hic veri yok mu — "bos" ile "yarim" ayri seylerdir. */
export function satirBos(satir: KuponSatiri): boolean {
  return (
    !satir.lig.trim() &&
    !satir.ev.trim() &&
    !satir.dep.trim() &&
    SEMBOLLER.every((s) => !satir.oran[s].trim())
  );
}

/** Maçin adi tam mi — iki takim da yazilmis mi. */
export function macTam(satir: KuponSatiri): boolean {
  return Boolean(satir.ev.trim() && satir.dep.trim());
}

export function oranSayilari(satir: KuponSatiri): Record<Sembol, number> {
  return {
    "1": Number(satir.oran["1"]),
    "0": Number(satir.oran["0"]),
    "2": Number(satir.oran["2"]),
  };
}

/**
 * Satirin marji — `Σ 1/oran − 1`. Oranlar tam degilse `null`.
 *
 * Neden ekranda duruyor: iddaa bulteni ~%18–28 marjli, korpus ~%7. Marj
 * arindirma yontemi bu farkta sonucu gorunur bicimde degistirir, yani marj
 * girdinin bir parcasidir ve kullanici onu ikinci asamayi beklemeden
 * gormeli (`components/oran-analizi/parts.tsx` `marjHesapla` ile ayni
 * gerekce; orasi tek mac, burasi 15 satir).
 */
export function satirMarji(satir: KuponSatiri): number | null {
  if (!oranTam(satir)) return null;
  const n = oranSayilari(satir);
  return SEMBOLLER.reduce((t, s) => t + 1 / n[s], 0) - 1;
}

/** Satirin favorisi — en dusuk oranli sembol. Oran tam degilse `null`. */
export function favori(satir: KuponSatiri): Sembol | null {
  if (!oranTam(satir)) return null;
  const n = oranSayilari(satir);
  return SEMBOLLER.reduce((en, s) => (n[s] < n[en] ? s : en), "1" as Sembol);
}

export interface KuponOzeti {
  /** Adi tam girilmis mac sayisi. */
  adliMac: number;
  /** Uc orani da okunabilen satir sayisi. */
  oranliMac: number;
  /** Icinde en az bir bozuk oran hucresi olan satirlarin 0 tabanli sirasi. */
  bozukSatirlar: number[];
  /** Adi var ama orani eksik olan satirlarin 0 tabanli sirasi. */
  eksikOranlar: number[];
  /** Oranli satirlarin ortalama marji; hic yoksa `null`. */
  ortalamaMarj: number | null;
  /** Ikinci asamaya (sorgu) gecmeye yeter mi: 15 satirin da orani tam. */
  sorguyaHazir: boolean;
}

export function kuponOzeti(satirlar: KuponSatiri[]): KuponOzeti {
  const bozukSatirlar: number[] = [];
  const eksikOranlar: number[] = [];
  const marjlar: number[] = [];
  let adliMac = 0;
  let oranliMac = 0;

  satirlar.forEach((satir, i) => {
    if (macTam(satir)) adliMac++;
    if (SEMBOLLER.some((s) => oranHucresiBozuk(satir.oran[s]))) bozukSatirlar.push(i);
    if (oranTam(satir)) {
      oranliMac++;
      const m = satirMarji(satir);
      if (m != null) marjlar.push(m);
    } else if (!satirBos(satir)) {
      eksikOranlar.push(i);
    }
  });

  return {
    adliMac,
    oranliMac,
    bozukSatirlar,
    eksikOranlar,
    ortalamaMarj: marjlar.length
      ? marjlar.reduce((a, b) => a + b, 0) / marjlar.length
      : null,
    sorguyaHazir: oranliMac === MAC_SAYISI,
  };
}

// ─── Yerel depo ───────────────────────────────────────────────────────────
//
// Elle 15 satir doldurmak dakikalar suren bir is; yenileme ya da sekme
// kapanmasi onu kaybettirmemeli. `lib/kurulum.ts` ile ayni kalip: yazma
// sessizce basarisiz olabilir (ozel sekme, kota), okuma ise depodaki
// JSON'a GUVENMEZ — elle kurcalanmis ya da eski surumden kalmis olabilir.

const YEREL_ANAHTAR = "twmq.kupon-girdi";

/** Herhangi bir girdiyi tek satirlik, kirpilmis metne cevirir. */
function temizMetin(ham: unknown, sinir: number): string {
  if (typeof ham !== "string") return "";
  return ham.replace(/\s+/g, " ").trim().slice(0, sinir);
}

/**
 * Herhangi bir girdiyi 15 satirlik gecerli bir kupona cevirir.
 *
 * Kayip TOLERE EDILIR, reddedilmez: yarim doldurulmus bir tablo da
 * kaydedilir ve geri okunur. `kurulumuCoz`un katiligi orada motorun
 * girdisini korudugu icin dogruydu; burada motor yok, insan var.
 */
export function kuponuTemizle(ham: unknown): KuponSatiri[] {
  const dizi = Array.isArray(ham) ? ham : [];
  return Array.from({ length: MAC_SAYISI }, (_, i) => {
    const aday = dizi[i];
    if (!aday || typeof aday !== "object") return bosSatir();
    const satir = aday as Record<string, unknown>;
    const oranHam = (satir.oran ?? {}) as Record<string, unknown>;
    return {
      lig: temizMetin(satir.lig, METIN_SINIR),
      ev: temizMetin(satir.ev, METIN_SINIR),
      dep: temizMetin(satir.dep, METIN_SINIR),
      oran: {
        "1": temizMetin(oranHam["1"], ORAN_SINIR),
        "0": temizMetin(oranHam["0"], ORAN_SINIR),
        "2": temizMetin(oranHam["2"], ORAN_SINIR),
      },
    };
  });
}

export function kuponuYereleYaz(satirlar: KuponSatiri[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(YEREL_ANAHTAR, JSON.stringify(satirlar));
  } catch {
    // Ozel sekme / kota dolu: kalicilik bir kolayliktir, sart degil.
  }
}

export function kuponuYereldenOku(): KuponSatiri[] | null {
  if (typeof window === "undefined") return null;
  try {
    const ham = window.localStorage.getItem(YEREL_ANAHTAR);
    if (!ham) return null;
    return kuponuTemizle(JSON.parse(ham));
  } catch {
    return null;
  }
}

export function yereliTemizle(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(YEREL_ANAHTAR);
  } catch {
    /* zaten yazilamamisti */
  }
}
