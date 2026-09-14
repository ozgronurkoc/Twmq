import { ARINDIRMA_YONTEMLERI, type ArindirmaYontemi } from "./api";
import { oranSayilari, oranTam, type KuponSatiri } from "./kupon";
import { CIZGILER, SEMBOLLER, type BenzerResponse, type Cizgi, type Sembol } from "./types";

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

export interface AnalizAyari {
  /** Korpusun HANGI fiyat cizgisinde aranacagi. */
  cizgi: Cizgi;
  arindirma: ArindirmaYontemi;
  /** Uyarlanan yaricapin ulasmaya calistigi mac sayisi. */
  enAz: number;
  /** `YYYY-AA-GG`; bos = butun korpus. Verilirse yalnizca ONCESI aranir. */
  tarih: string;
}

export const VARSAYILAN_ANALIZ: AnalizAyari = {
  cizgi: "kapanis",
  arindirma: "shin",
  enAz: 200,
  tarih: "",
};

/** Tek satirin analizdeki hali. */
export type SatirDurumu = "bos" | "kosuyor" | "bitti" | "hata";

export interface SatirAnalizi {
  durum: SatirDurumu;
  veri: BenzerResponse | null;
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
  return [oranlar, ayar.cizgi, ayar.arindirma, ayar.enAz, ayar.tarih].join("§");
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
    (CIZGILER as readonly string[]).includes(ayar.cizgi) &&
    (ARINDIRMA_YONTEMLERI as readonly string[]).includes(ayar.arindirma) &&
    Number.isInteger(ayar.enAz) &&
    ayar.enAz > 0 &&
    tarihGecerli(ayar.tarih)
  );
}

/** Analiz kosulabilir mi: 15 satirin da orani tam VE ayar gecerli. */
export function analizeHazir(satirlar: KuponSatiri[], ayar: AnalizAyari): boolean {
  return satirlar.length > 0 && satirlar.every(oranTam) && ayarGecerli(ayar);
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
