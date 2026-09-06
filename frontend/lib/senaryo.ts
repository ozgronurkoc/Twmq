import type { Kurulum } from "./kurulum";
import type { SolveResult } from "./types";

/**
 * Calistirilan kuponlarin karsilastirma listesi.
 *
 * ─── KIYAS EKSENI DEGISTI: mod degil, ISARETLER ───────────────────────
 *
 * Bu liste mod secimi icin yazilmisti: *"mod secimi bu sayfadaki en pahali
 * karardir (fix16 mi, butce mi, maxcov mu) ama gozle yapilamiyordu — bir
 * modu calistirip digerine gecince oncekinin sayilari ekrandan
 * siliniyordu."* Kaplama sokuldu (`docs/DUZ_SISTEME_GECIS.md`) ve modlar
 * dustu; duzde ayni isaretler HER ZAMAN ayni kolonlari verir, yani mod
 * ekseninde kiyaslanacak bir sey kalmadi.
 *
 * Geriye kalan eksen daha onemli olan: **isaretlerin kendisi.** Bir maci
 * daha cifte yapmak kume-ici olasiligi buyutur ve bedeli katlar; bu
 * takas artik sayfanin TEK pahali kararidir ve akildan yapiliyordu.
 * Liste onu goze goruntuye cevirir.
 *
 * NEDEN KALICI DEGIL: senaryolar TURETILMIS veridir, tipki `sonuc` gibi.
 * Kurulum kalicidir cunku kullanicinin elle urettigi tek sey odur;
 * bunlar motorun ciktisidir ve her an yeniden uretilebilir.
 */
export interface Senaryo {
  /** Kurulumun tam parmak izi — ayni kurulum tekrar kosulursa satir yenilenir. */
  id: string;
  /** Yalnizca işaretlerin parmak izi. */
  secimParmak: string;
  baslik: string;
  /** Duzde her zaman 1: kupon isaretlerin kendisidir. */
  satir: number;
  bedel: number;
  /** Seçim kümesinin doğru sonucu içerme olasılığı (0–1); yoksa null. */
  pKumeIci: number | null;
  /** Bu satıra dönebilmek için kurulumun kendisi. */
  kurulum: Kurulum;
}

const SENARYO_SINIRI = 6;

/**
 * Sonuctan senaryo satiri uretir.
 *
 * `advanced.exact.p_kume_ici` sunucuda YUZDE olarak doner (bkz.
 * types.ts); burada 0-1'e cevrilir ki liste tek birimde kalsin.
 */
export function senaryoYap(
  r: SolveResult,
  kurulum: Kurulum,
  id: string,
  secimParmak: string,
): Senaryo {
  return {
    id,
    secimParmak,
    baslik: r.baslik,
    satir: r.satir_sayisi,
    bedel: r.kolon_bedeli,
    pKumeIci: r.advanced ? r.advanced.exact.p_kume_ici / 100 : null,
    kurulum,
  };
}

/**
 * Listeye ekler. Ayni kurulum tekrar kosulursa YERINDE yenilenir.
 */
export function senaryoEkle(
  liste: Senaryo[],
  yeni: Senaryo,
  sinir: number = SENARYO_SINIRI,
): Senaryo[] {
  const yer = liste.findIndex((s) => s.id === yeni.id);
  if (yer >= 0) {
    const kopya = [...liste];
    kopya[yer] = yeni;
    return kopya;
  }
  return [yeni, ...liste].slice(0, sinir);
}

/**
 * Kolon basina en cok kume-ici olasilik veren satir — duzdeki asil takas.
 *
 * Burada eskiden `enUcuzGarantili` vardi: *"AYNI secim uzerinde kosulmus,
 * 14-garantiyi veren ve en ucuz olan"*. Duzde o soru dejenere — ayni
 * secim her zaman ayni bedeli verir ve garanti diye bir secenek yok.
 * Anlamli soru bunun yerine su: **odedigim her kolon bana ne kadar
 * kume-ici olasilik aliyor?**
 *
 * BU BIR ONERI DEGILDIR. Verim yalnizca bir orandir; kume-ici olasilik
 * kazanma olasiligi degil, kacak aritmetiginin gecerli olma kosuludur
 * (bkz. `kume-ici.ts`). Ikramiye, kolon bedeli ve kac kisinin tutturdugu
 * hesaba girmez.
 *
 * `pKumeIci` bilinmeyen (olasilik girilmemis) satirlar elenir; bedeli
 * sifir olan satir olamaz ama savunmaci davraniliyor.
 */
export function enIyiVerim(liste: Senaryo[]): Senaryo | null {
  const adaylar = liste.filter((s) => s.pKumeIci !== null && s.bedel > 0);
  if (adaylar.length < 2) return null;
  return adaylar.reduce((a, b) =>
    (b.pKumeIci as number) / b.bedel > (a.pKumeIci as number) / a.bedel ? b : a,
  );
}
