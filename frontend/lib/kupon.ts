import { CIZGILER, MAC_SAYISI, SEMBOLLER, type Cizgi, type Sembol } from "./types";

/**
 * Kupon kurucunun GIRDISI — 15 satirlik elle doldurulan mac tablosu.
 *
 * Bu modul saf: React yok, istek yok, `window` erisimi yalnizca depo
 * fonksiyonlarinda ve orada da korumali (`check.mjs` modulu dogrudan
 * kosabilsin diye — `lib/kurulum.ts` ile ayni doktrin).
 *
 * ─── Oran neden IKI blok: acilis ve kapanis ───────────────────────────────
 *
 * Sahibinin istegi: *"acilis ve kapanis oranlarini verdigimde ... acilis
 * kendi icinde 2 kupon, kapanis kendi icinde 2 kupon olacak."* Yani bir
 * satir artik TEK bir fiyat tasimiyor; iki fiyat tasiyor ve her biri kendi
 * korpus cizgisinde araniyor (`benzer` `cizgi=acilis` / `cizgi=kapanis`).
 *
 * Onceden tabloda tek blok vardi ve hangi cizgiye ait oldugunu AYAR
 * soyluyordu. O hal iki fiyati ayni anda tutamiyordu: acilisla kapanisi
 * kiyaslamak icin tabloyu bir kez acilis, bir kez kapanis diye iki kez
 * doldurmak gerekiyordu ve iki dolduruşun ayni maclara ait oldugunu
 * hicbir sey garanti etmiyordu.
 *
 * Blok EKSIK BIRAKILABILIR: yalnizca kapanisi olan biri kapanis tarafini
 * doldurup o cizginin kuponlarini kurar. Analiz, orani TAM olan cizgiler
 * icin kosar (`kupon-analiz.hazirCizgiler`).
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
 * Ayni kural burada da gecerli.
 */

/** Bir cizginin ham 1/0/2 hucreleri. */
export type OranBlogu = Record<Sembol, string>;

export interface KuponSatiri {
  /** Serbest metin: `T1`, `Süper Lig`, `TR` — ne yazildiysa o. */
  lig: string;
  ev: string;
  dep: string;
  /** Her cizginin KENDI 1/0/2 orani, ham metin hâliyle. Bos olabilir. */
  oran: Record<Cizgi, OranBlogu>;
}

/**
 * Izgarada ve cikti tablolarinda cizgilerin okunma sirasi.
 *
 * `types.CIZGILER` sirasi `["kapanis", "acilis"]` ve o sira sunucunun
 * VARSAYILANINI onde tutmak icin boyle (`benzer` kapanisla calisir).
 * Insan ise bulteni zaman sirasiyla okur: once acilis, sonra kapanis.
 * Iki sirayi da birbirine cevirmek yerine ekran sirasi burada, tek yerde.
 */
export const CIZGI_SIRASI: readonly Cizgi[] = ["acilis", "kapanis"] as const;

export const CIZGI_ADI: Record<Cizgi, string> = {
  acilis: "Açılış",
  kapanis: "Kapanış",
};

/** Metin alanlarinin en fazla uzunlugu — uzun bir yapistirma depoyu sismesin. */
export const METIN_SINIR = 40;

/** Oran metninin en fazla uzunlugu; `14.06` uzun ucta bile 5 karakter. */
export const ORAN_SINIR = 8;

export function bosOranBlogu(): OranBlogu {
  return { "1": "", "0": "", "2": "" };
}

export function bosSatir(): KuponSatiri {
  return {
    lig: "",
    ev: "",
    dep: "",
    oran: { acilis: bosOranBlogu(), kapanis: bosOranBlogu() },
  };
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

/** Bir cizginin uc orani da okunabiliyor mu. */
export function oranTam(satir: KuponSatiri, cizgi: Cizgi): boolean {
  const blok = satir.oran[cizgi];
  return SEMBOLLER.every((s) => {
    const v = Number(blok[s]);
    return blok[s].trim() !== "" && Number.isFinite(v) && v > 1;
  });
}

/** Bir cizginin blogunda hic veri yok mu. */
export function blokBos(satir: KuponSatiri, cizgi: Cizgi): boolean {
  return SEMBOLLER.every((s) => !satir.oran[cizgi][s].trim());
}

/** Satirda hic veri yok mu — "bos" ile "yarim" ayri seylerdir. */
export function satirBos(satir: KuponSatiri): boolean {
  return (
    !satir.lig.trim() &&
    !satir.ev.trim() &&
    !satir.dep.trim() &&
    CIZGILER.every((c) => blokBos(satir, c))
  );
}

/** Maçin adi tam mi — iki takim da yazilmis mi. */
export function macTam(satir: KuponSatiri): boolean {
  return Boolean(satir.ev.trim() && satir.dep.trim());
}

export function oranSayilari(satir: KuponSatiri, cizgi: Cizgi): Record<Sembol, number> {
  const blok = satir.oran[cizgi];
  return {
    "1": Number(blok["1"]),
    "0": Number(blok["0"]),
    "2": Number(blok["2"]),
  };
}

/**
 * Satirin bir cizgideki marji — `Σ 1/oran − 1`. Oranlar tam degilse `null`.
 *
 * Neden ekranda duruyor: iddaa bulteni ~%18–28 marjli, korpus ~%7. Marj
 * arindirma yontemi bu farkta sonucu gorunur bicimde degistirir, yani marj
 * girdinin bir parcasidir ve kullanici onu ikinci asamayi beklemeden
 * gormeli (`components/oran-analizi/parts.tsx` `marjHesapla` ile ayni
 * gerekce; orasi tek mac, burasi 15 satir).
 */
export function satirMarji(satir: KuponSatiri, cizgi: Cizgi): number | null {
  if (!oranTam(satir, cizgi)) return null;
  const n = oranSayilari(satir, cizgi);
  return SEMBOLLER.reduce((t, s) => t + 1 / n[s], 0) - 1;
}

/** Satirin favorisi — en dusuk oranli sembol. Oran tam degilse `null`. */
export function favori(satir: KuponSatiri, cizgi: Cizgi): Sembol | null {
  if (!oranTam(satir, cizgi)) return null;
  const n = oranSayilari(satir, cizgi);
  return SEMBOLLER.reduce((en, s) => (n[s] < n[en] ? s : en), "1" as Sembol);
}

export interface KuponOzeti {
  /** Adi tam girilmis mac sayisi. */
  adliMac: number;
  /** Uc orani da okunabilen satir sayisi (bu cizgide). */
  oranliMac: number;
  /** Icinde en az bir bozuk oran hucresi olan satirlarin 0 tabanli sirasi. */
  bozukSatirlar: number[];
  /** Adi ya da oteki cizgisi var ama BU cizgisi eksik olan satirlar. */
  eksikOranlar: number[];
  /** Oranli satirlarin ortalama marji; hic yoksa `null`. */
  ortalamaMarj: number | null;
  /** Bu cizgide sorguya gecmeye yeter mi: 15 satirin da orani tam. */
  sorguyaHazir: boolean;
}

/** Tek bir cizginin girdi ozeti. Iki cizgi ayri ayri ozetlenir. */
export function kuponOzeti(satirlar: KuponSatiri[], cizgi: Cizgi): KuponOzeti {
  const bozukSatirlar: number[] = [];
  const eksikOranlar: number[] = [];
  const marjlar: number[] = [];
  let adliMac = 0;
  let oranliMac = 0;

  satirlar.forEach((satir, i) => {
    if (macTam(satir)) adliMac++;
    if (SEMBOLLER.some((s) => oranHucresiBozuk(satir.oran[cizgi][s]))) {
      bozukSatirlar.push(i);
    }
    if (oranTam(satir, cizgi)) {
      oranliMac++;
      const m = satirMarji(satir, cizgi);
      if (m != null) marjlar.push(m);
    } else if (!satirBos(satir)) {
      // Satirda bir sey var (ad, ya da oteki cizginin orani) ama BU cizgi
      // yarim: bu bir eksiklik, "bos satir" degil.
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

function blokTemizle(ham: unknown): OranBlogu {
  const h = (ham ?? {}) as Record<string, unknown>;
  return {
    "1": temizMetin(h["1"], ORAN_SINIR),
    "0": temizMetin(h["0"], ORAN_SINIR),
    "2": temizMetin(h["2"], ORAN_SINIR),
  };
}

function blokDolu(blok: OranBlogu): boolean {
  return SEMBOLLER.some((s) => blok[s] !== "");
}

/**
 * Bir satirin ham `oran` alanini iki bloga cevirir — ESKI BICIMI de okur.
 *
 * Eski bicim duz bir `{1,0,2}` sozlugudur ve hangi cizgiye ait oldugunu
 * kendisi soylemez; onu AYAR soyluyordu. Bu yuzden cevrimde cizgi disaridan
 * verilir (`varsayilanCizgi`) ve duz blok oraya oturur. Oteki cizgi BOS
 * kalir: iki cizgiye birden kopyalamak, girilmemis bir fiyati girilmis
 * gibi gostermek olurdu.
 */
export function oranlariTemizle(ham: unknown, varsayilanCizgi: Cizgi): Record<Cizgi, OranBlogu> {
  const h = (ham ?? {}) as Record<string, unknown>;
  const yeni = {
    acilis: blokTemizle(h.acilis),
    kapanis: blokTemizle(h.kapanis),
  };
  if (blokDolu(yeni.acilis) || blokDolu(yeni.kapanis)) return yeni;
  // Yeni bicimde hicbir sey yok: duz (eski) bicim olabilir.
  const duz = blokTemizle(h);
  if (!blokDolu(duz)) return yeni;
  return varsayilanCizgi === "acilis"
    ? { acilis: duz, kapanis: bosOranBlogu() }
    : { acilis: bosOranBlogu(), kapanis: duz };
}

/**
 * Herhangi bir girdiyi 15 satirlik gecerli bir kupona cevirir.
 *
 * Kayip TOLERE EDILIR, reddedilmez: yarim doldurulmus bir tablo da
 * kaydedilir ve geri okunur. `kurulumuCoz`un katiligi orada motorun
 * girdisini korudugu icin dogruydu; burada motor yok, insan var.
 */
export function kuponuTemizle(ham: unknown, varsayilanCizgi: Cizgi = "kapanis"): KuponSatiri[] {
  const dizi = Array.isArray(ham) ? ham : [];
  return Array.from({ length: MAC_SAYISI }, (_, i) => {
    const aday = dizi[i];
    if (!aday || typeof aday !== "object") return bosSatir();
    const satir = aday as Record<string, unknown>;
    return {
      lig: temizMetin(satir.lig, METIN_SINIR),
      ev: temizMetin(satir.ev, METIN_SINIR),
      dep: temizMetin(satir.dep, METIN_SINIR),
      oran: oranlariTemizle(satir.oran, varsayilanCizgi),
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

/**
 * Arsiv kaydini GIRIS tablosuna cevirir.
 *
 * Kayitta oran SAYIDIR (bir kayit tipinde gevsek olmamali), tabloda ise
 * METIN — `1.` yazmakta olan biri sayiya cevrilen bir alanda her tus
 * vurusunda alaninin altindan kayan bir deger gorurdu (modul basindaki
 * gerekce). Cevrim bu yuzden tek yerde ve burada.
 *
 * `String(1.26)` -> `"1.26"`. Kayipsiz DEGILDIR ve olmasi da gerekmiyor:
 * kullanicinin yazdigi `1.260` kayitta `1.26` olur ve geri okundugunda
 * `1.26` gorunur. Ayni SAYI, farkli yazim.
 *
 * `varsayilanCizgi` YALNIZCA eski (duz oranli) kayitlar icin kullanilir:
 * o kayitlarda fiyatin hangi cizgiye ait oldugunu `ayar.cizgi` soyluyordu.
 */
export function kayittanSatirlar(
  kayitSatirlari: {
    lig?: string;
    ev?: string;
    dep?: string;
    oran?: Record<string, unknown>;
  }[],
  varsayilanCizgi: Cizgi = "kapanis",
): KuponSatiri[] {
  const sayiyaMetin = (blok: Record<string, unknown>): OranBlogu => {
    const metin = (s: Sembol) => {
      const v = blok?.[s];
      return typeof v === "number" && Number.isFinite(v) ? String(v) : "";
    };
    return { "1": metin("1"), "0": metin("0"), "2": metin("2") };
  };

  return Array.from({ length: MAC_SAYISI }, (_, i) => {
    const k = kayitSatirlari?.[i];
    if (!k) return bosSatir();
    const oranHam = (k.oran ?? {}) as Record<string, unknown>;
    const ic = (anahtar: Cizgi) =>
      oranHam[anahtar] && typeof oranHam[anahtar] === "object"
        ? sayiyaMetin(oranHam[anahtar] as Record<string, unknown>)
        : bosOranBlogu();
    let oran: Record<Cizgi, OranBlogu> = { acilis: ic("acilis"), kapanis: ic("kapanis") };
    if (!blokDolu(oran.acilis) && !blokDolu(oran.kapanis)) {
      // Eski kayit: duz `{1,0,2}` sayilari. Ayarin cizgisine oturur.
      const duz = sayiyaMetin(oranHam);
      if (blokDolu(duz)) {
        oran =
          varsayilanCizgi === "acilis"
            ? { acilis: duz, kapanis: bosOranBlogu() }
            : { acilis: bosOranBlogu(), kapanis: duz };
      }
    }
    return {
      lig: temizMetin(k.lig, METIN_SINIR),
      ev: temizMetin(k.ev, METIN_SINIR),
      dep: temizMetin(k.dep, METIN_SINIR),
      oran,
    };
  });
}
