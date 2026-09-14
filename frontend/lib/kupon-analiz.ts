import { ARINDIRMA_YONTEMLERI, type ArindirmaYontemi } from "./api";
import { oranSayilari, oranTam, type KuponSatiri } from "./kupon";
import {
  CIZGILER,
  MAC_SAYISI,
  SEMBOLLER,
  type ArsivAnalizi,
  type ArsivKarnesi,
  type BenzerResponse,
  type BenzerSembol,
  type Cizgi,
  type Sembol,
} from "./types";

/**
 * Kupon kurucunun 2. asamasi: 15 satirin AYNI ayarla korpusta aranmasi.
 *
 * ─── Neden ayri bir modul ─────────────────────────────────────────────────
 *
 * Sorgunun kendisi `lib/api.getBenzer` ile yapiliyor ve o uc zaten var;
 * burada duran sey sorgunun ETRAFI: hangi ayarla kosuldugu, ayni ayarin
 * iki kez kosulmamasi, ve 15 cevabin tek bakista okunabilir bir ozete
 * indirgenmesi. Hepsi saf — React yok, istek yok — yani `scripts/check.mjs`
 * modulu dogrudan kosup dogrulayabiliyor.
 *
 * ─── Neden toplu bir uc YOK (olculdu) ────────────────────────────────────
 *
 * 15 satir, 15 ayri `/api/benzer` cagrisidir. "Tek istekte 15 satir" diyen
 * bir uc akla yatkin gorunuyor ve EKLENMEDI, cunku maliyeti olculdu:
 *
 *     15 sorgu, korpus sicakken : 0,81 sn  (satir basina 54 ms)
 *     ilk sorgu (korpus okumasi): 1,98 sn  (yalnizca bir kez, surec basina)
 *
 * Yani kazanc, ayrisabilecek ikinci bir sorgu yolunun bakim borcunu
 * odemiyor. Ustelik ayni ucu cagirmak, buradaki karnenin `/oran-analizi`de
 * acilanla tanim geregi AYNI cikmasini sagliyor.
 *
 * ─── Neden lig suzgeci YOK ────────────────────────────────────────────────
 *
 * Sahibinin istegi acikti: *"bakacagimiz yer genel tum liglerin icerildigi
 * sonuclar olacak."* `/api/benzer` lig suzgecini destekliyor ama buradan
 * ASLA gonderilmiyor; lig kirilimi `/oran-analizi`de duruyor ve her satirin
 * kendi baglantisi oraya gidiyor.
 */

/**
 * Aramanin EVRENI: butun korpus mu, macin kendi ligi mi.
 *
 * `tum`  — lig suzgeci hic gonderilmez. Varsayilan ve en genis evren.
 * `kendi`— her satir KENDI lig koduyla aranir (`lig=T1`).
 *
 * Ikisi ayni soruyu SORMAZ. "Bu fiyatta genel olarak ne olmus" ile "bu
 * fiyatta BU LIGDE ne olmus" farkli sorulardir ve ikincisinin bedeli
 * OLCULDU (5. haftanin 15 maci, kapanis, shin, hedef orneklem 200):
 *
 *     tum ligler   yaricap tavani  1/15   az ornek 0/15
 *     kendi ligi   yaricap tavani 10/15   az ornek 1/15
 *
 * Evren 23.085'ten bir ligin boyuna duser (T1: 1.415, D1: 1.224), yani
 * uyarlanan yaricap +-5 puana dayanir ve orneklem "benzer" maclardan degil
 * SINIRDAN toplanir. En uc ornek Levante–Barcelona: tum liglerde n=123,
 * kendi liginde n=2.
 *
 * Bu, secenegi kotu yapmaz — baska bir soru sordurur. Sayfa bedeli
 * gizlemiyor: her satirda n ve yaricap yaziyor, tavana dayanan satir
 * "tavan" diye isaretleniyor.
 */
export type LigKapsami = "tum" | "kendi";

export interface AnalizAyari {
  /** Korpusun HANGI fiyat cizgisinde aranacagi. */
  cizgi: Cizgi;
  arindirma: ArindirmaYontemi;
  /** Uyarlanan yaricapin ulasmaya calistigi mac sayisi. */
  enAz: number;
  /** `YYYY-AA-GG`; bos = butun korpus. Verilirse yalnizca ONCESI aranir. */
  tarih: string;
  /** Arama evreni — tum ligler mi, macin kendi ligi mi. */
  kapsam: LigKapsami;
}

export const KAPSAMLAR = ["tum", "kendi"] as const;

export const VARSAYILAN_ANALIZ: AnalizAyari = {
  cizgi: "kapanis",
  arindirma: "shin",
  enAz: 200,
  tarih: "",
  // Varsayilan TUM LIGLER: sahibinin ilk istegi buydu ve genis evren
  // orneklemi ayakta tutuyor. "Kendi ligi" bilincli olarak secilir.
  kapsam: "tum",
};

/** Tek satirin analizdeki hali. */
export type SatirDurumu = "bos" | "kosuyor" | "bitti" | "hata";

/**
 * Tablonun cizmek icin ihtiyac duydugu EN KUCUK karne.
 *
 * `BenzerResponse` bunu yapisal olarak zaten karsiliyor; arsivden gelen
 * damgali kayit (`ArsivKarnesi`) da. Tek bir tablo bileseni ikisini de
 * cizebilsin diye tip burada daraltildi: canli sorgu ile acilan kayit ayni
 * ekrani vermeli, yoksa "kaydettigimle gordugum ayni mi" sorusu dogar.
 */
export interface KarneGorunumu {
  tolerans: number;
  tolerans_genisledi: boolean;
  tolerans_tavana_dayandi: boolean;
  toplam: {
    n: number;
    yeterli: boolean;
    semboller: Record<Sembol, BenzerSembol>;
  };
}

export interface SatirAnalizi {
  durum: SatirDurumu;
  veri: KarneGorunumu | null;
  hata: string | null;
}

export function bosAnaliz(uzunluk: number): SatirAnalizi[] {
  return Array.from({ length: uzunluk }, () => ({
    durum: "bos" as SatirDurumu,
    veri: null,
    hata: null,
  }));
}

/**
 * Sorgunun PARMAK IZI — girdi ya da ayar degisince sonuc bayatlar.
 *
 * Ekranda duran karne, hangi orandan ve hangi ayardan ciktigini
 * unutturmamali: kullanici 7. macin oranini duzeltip tabloya bakmaya devam
 * ederse eski cevabi gorurdu. Sayfa bu izi karsilastirip "sonuc bayat"
 * diyor, sessizce eski veriyi gostermiyor.
 */
export function sorguIzi(satirlar: KuponSatiri[], ayar: AnalizAyari): string {
  const oranlar = satirlar
    .map((s) => SEMBOLLER.map((sem) => s.oran[sem].trim()).join(","))
    .join("|");
  // Kapsam `kendi` iken LIG KODLARI da ize girer: bir satirin ligi
  // degisirse o satirin sorgusu degisir ve ekrandaki karne bayatlar.
  // Kapsam `tum` iken lig sorgunun parcasi degildir ve ize girmez —
  // girseydi etiket duzeltmek butun tabloyu bayatlatirdi.
  const ligler = ayar.kapsam === "kendi"
    ? satirlar.map((s) => s.lig.trim().toUpperCase()).join(",")
    : "";
  return [oranlar, ayar.cizgi, ayar.arindirma, ayar.enAz, ayar.tarih,
          ayar.kapsam, ligler].join("§");
}

/**
 * Satirin `/oran-analizi` adresi — AYNI sorgu, ayrintili haliyle.
 *
 * Bu sayfanin varlik sebebi 15 maci tek tek oraya girmemek; ama bir satir
 * dikkat cektiginde (lig kirilimi, maclarin kendisi) oraya tek tiklamayla
 * gidilebilmeli. Adres `/oran-analizi`nin okudugu adlarla kurulur.
 */
export function oranAnaliziAdresi(satir: KuponSatiri, ayar: AnalizAyari): string {
  const n = oranSayilari(satir);
  const q = new URLSearchParams({
    o1: String(n["1"]),
    o0: String(n["0"]),
    o2: String(n["2"]),
  });
  // Varsayilanlar adrese YAZILMAZ — `/oran-analizi` kendi kuralinda da
  // boyle yapiyor: paylasilan baglanti yalnizca degiseni tasisin.
  if (ayar.cizgi !== VARSAYILAN_ANALIZ.cizgi) q.set("cizgi", ayar.cizgi);
  if (ayar.arindirma !== VARSAYILAN_ANALIZ.arindirma) q.set("arindirma", ayar.arindirma);
  if (ayar.enAz !== VARSAYILAN_ANALIZ.enAz) q.set("en_az", String(ayar.enAz));
  if (ayar.tarih) q.set("tarih", ayar.tarih);
  // Kapsam `kendi` ise baglanti AYNI suzgecle acilmali; yoksa "ac" dendiginde
  // baska bir sorgunun cevabi gorunurdu.
  if (ayar.kapsam === "kendi" && satir.lig.trim()) {
    q.set("lig", satir.lig.trim().toUpperCase());
  }
  return `/oran-analizi?${q}`;
}

/**
 * Tarih kesmesi gecerli mi. Bos GECERLIDIR (kesme yok).
 *
 * Sunucu bicimi kendi dogruluyor ve bozuk degere 400 doner; burada yapilan
 * sey o 400'u 15 kez almamak. `2026-13-45` gibi takvimde olmayan bir gun de
 * elenir: `Date` onu sessizce baska bir gune tasir, yani bicim denetimi tek
 * basina yetmez.
 */
export function tarihGecerli(ham: string): boolean {
  const metin = ham.trim();
  if (!metin) return true;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(metin)) return false;
  const d = new Date(`${metin}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === metin;
}

/** Ayarin tamami sunucuya gonderilebilir mi. */
export function ayarGecerli(ayar: AnalizAyari): boolean {
  return (
    (KAPSAMLAR as readonly string[]).includes(ayar.kapsam) &&
    (CIZGILER as readonly string[]).includes(ayar.cizgi) &&
    (ARINDIRMA_YONTEMLERI as readonly string[]).includes(ayar.arindirma) &&
    Number.isInteger(ayar.enAz) &&
    ayar.enAz > 0 &&
    tarihGecerli(ayar.tarih)
  );
}

/**
 * Kapsam `kendi` iken korpusun TANIMADIGI lig kodu tasiyan satirlar.
 *
 * Bu sessiz bir kusurdur ve bekci gerektirir: `lig=Süper Lig` diye bir
 * arama 400 DONMEZ, bos doner — kullanici "bu fiyatta hic benzer mac yok"
 * ile "yazdigin kodu tanimiyorum"u ayirt edemez. Envanter yuklenmediyse
 * (`null`) dogrulama YAPILMAZ: olmayan bir listeye gore satir suclanamaz.
 */
export function taninmayanLigler(
  satirlar: KuponSatiri[],
  ayar: AnalizAyari,
  bilinenKodlar: Set<string> | null,
): number[] {
  if (ayar.kapsam !== "kendi" || !bilinenKodlar) return [];
  const eksik: number[] = [];
  satirlar.forEach((s, i) => {
    const kod = s.lig.trim().toUpperCase();
    if (!kod || !bilinenKodlar.has(kod)) eksik.push(i);
  });
  return eksik;
}

/**
 * Analiz kosulabilir mi: 15 satirin da orani tam, ayar gecerli VE kapsam
 * `kendi` ise her satirin ligi korpusta taniniyor.
 */
export function analizeHazir(
  satirlar: KuponSatiri[],
  ayar: AnalizAyari,
  bilinenKodlar: Set<string> | null = null,
): boolean {
  return (
    satirlar.length > 0 &&
    satirlar.every(oranTam) &&
    ayarGecerli(ayar) &&
    taninmayanLigler(satirlar, ayar, bilinenKodlar).length === 0
  );
}

// ─── Ozet ─────────────────────────────────────────────────────────────────

export interface AnalizOzeti {
  biten: number;
  hatali: number;
  kosan: number;
  /** Ornegi `AZ_ORNEK` esiginin altinda kalan satirlar (0 tabanli). */
  azOrnek: number[];
  /** Yaricapi tavana dayanan satirlar — ornek "benzer"den degil SINIRDAN. */
  tavanaDayanan: number[];
  /**
   * Piyasanin en az bir sembolde ampirik %95 araligin DISINDA kaldigi
   * satirlar. Okunacak asil liste budur: fiyatin tasidigi bilgi, karne ile
   * piyasanin FARKI — ve bu fark ancak aralik disinda anlamli.
   */
  sapan: number[];
  /** Hepsi bitti mi (hata da bir bitis sayilmaz). */
  tamam: boolean;
}

/** `benzer.AZ_ORNEK` — altinda yuzde okunmaz. Sunucu `yeterli` ile soyler. */
export function analizOzeti(sonuclar: SatirAnalizi[]): AnalizOzeti {
  const azOrnek: number[] = [];
  const tavanaDayanan: number[] = [];
  const sapan: number[] = [];
  let biten = 0;
  let hatali = 0;
  let kosan = 0;

  sonuclar.forEach((s, i) => {
    if (s.durum === "kosuyor") kosan++;
    if (s.durum === "hata") hatali++;
    if (s.durum !== "bitti" || !s.veri) return;
    biten++;
    if (!s.veri.toplam.yeterli) azOrnek.push(i);
    if (s.veri.tolerans_tavana_dayandi) tavanaDayanan.push(i);
    // `piyasa_ga_icinde` null olabilir (adet 0); null "sapma" DEGILDIR.
    const disarida = SEMBOLLER.some(
      (sem) => s.veri?.toplam.semboller[sem]?.piyasa_ga_icinde === false,
    );
    if (disarida) sapan.push(i);
  });

  return {
    biten,
    hatali,
    kosan,
    azOrnek,
    tavanaDayanan,
    sapan,
    tamam: sonuclar.length > 0 && biten + hatali === sonuclar.length,
  };
}

/**
 * Bir satirin bir sembolde piyasadan sapip sapmadigi — ekrandaki tek isaret.
 *
 * `true` = ampirik %95 aralik piyasanin dedigini ICERMIYOR. `null` = karar
 * verilemez (ornek yok). Kirpilmamis bir bayrak: az orneklemde aralik zaten
 * genis oldugu icin bu nadiren `true` olur, ve olmasi gerekir.
 */
export function sembolSapiyorMu(
  veri: BenzerResponse | null,
  sembol: Sembol,
): boolean | null {
  const s = veri?.toplam.semboller[sembol];
  if (!s || s.piyasa_ga_icinde == null) return null;
  return !s.piyasa_ga_icinde;
}

// ─── Arsiv cevrimi ────────────────────────────────────────────────────────
//
// Kupon, analizden CIKIYOR. Kayit analizi tasimasaydi "neden bu isaretler"
// sorusu bir daha cevaplanamazdi (`spor_toto/kupon_arsivi.py` kunyesi).
// Buradaki iki fonksiyon o halkayi ceviriyor; ikisi de saf.

/**
 * Kosulmus analizi arsiv blogua cevirir. Hic satir bitmemisse `null`.
 *
 * `evren` ilk BITEN satirdan okunur: damganin ikinci yarisi odur ve
 * uydurulamaz — hangi buyuklukteki korpusta olculdugunu ancak cevabin
 * kendisi soyler. Sunucu damgasiz analizi reddediyor.
 */
export function analizdenKayit(
  sonuclar: SatirAnalizi[],
  evren: number | null,
): ArsivAnalizi | null {
  const biten = sonuclar.some((s) => s.durum === "bitti" && s.veri);
  if (!biten || !evren || evren <= 0) return null;
  return {
    olculdu: new Date().toISOString(),
    evren,
    satirlar: Array.from({ length: MAC_SAYISI }, (_, i) => {
      const s = sonuclar[i];
      // Sorgusu hata almis ya da hic kosmamis satir `null` durur: bu bir
      // kayip degil, kaydin kendisidir.
      if (!s || s.durum !== "bitti" || !s.veri) return null;
      const k: ArsivKarnesi = {
        n: s.veri.toplam.n,
        yeterli: s.veri.toplam.yeterli,
        tolerans: s.veri.tolerans,
        tolerans_genisledi: s.veri.tolerans_genisledi,
        tolerans_tavana_dayandi: s.veri.tolerans_tavana_dayandi,
        semboller: s.veri.toplam.semboller,
      };
      return k;
    }),
  };
}

/** Arsivden gelen analizi tabloya cevirir — canli sorguyla AYNI sekil. */
export function kayittanAnaliz(analiz: ArsivAnalizi | null): SatirAnalizi[] {
  if (!analiz) return bosAnaliz(MAC_SAYISI);
  return Array.from({ length: MAC_SAYISI }, (_, i) => {
    const k = analiz.satirlar?.[i];
    if (!k) return { durum: "bos" as SatirDurumu, veri: null, hata: null };
    return {
      durum: "bitti" as SatirDurumu,
      veri: {
        tolerans: k.tolerans,
        tolerans_genisledi: k.tolerans_genisledi,
        tolerans_tavana_dayandi: k.tolerans_tavana_dayandi,
        toplam: { n: k.n, yeterli: k.yeterli, semboller: k.semboller },
      },
      hata: null,
    };
  });
}

/** Kosulmus sorgularin evreni — hepsinde ayni olmali, ilk bulunani yeter. */
export function evreniOku(sonuclar: (BenzerResponse | null)[]): number | null {
  for (const v of sonuclar) {
    if (v && Number.isFinite(v.evren) && v.evren > 0) return v.evren;
  }
  return null;
}
