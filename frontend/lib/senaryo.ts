import type { Kurulum } from "./kurulum";
import type { ModeId, SolveResult } from "./types";

/**
 * Calistirilan formullerin karsilastirma listesi.
 *
 * NEDEN VAR: mod secimi bu sayfadaki en pahali karardir (fix16 mi, butce
 * mi, maxcov mu) ama bugune kadar gozle yapilamiyordu — bir modu
 * calistirip digerine gecince oncekinin sayilari ekrandan siliniyordu.
 * Kullanici 16 satir / 32 kolonu, 29 kolonluk bir alternatifle ancak
 * akildan kiyaslayabiliyordu.
 *
 * NEDEN KALICI DEGIL: senaryolar TURETILMIS veridir, tipki `sonuc` gibi.
 * Kurulum kalicidir cunku kullanicinin elle urettigi tek sey odur;
 * bunlar motorun ciktisidir ve her an yeniden uretilebilir.
 *
 * NEDEN SECIM PARMAK IZI TASIYOR: iki calismanin bedelleri ancak AYNI
 * isaretler uzerinde kosulduysa kiyaslanabilir. Kullanici arada bir maci
 * cifte yaptiysa "32 kolon yerine 64 kolon" karsilastirmasi modlarla
 * degil, secimle ilgilidir. Liste bunu gizlemez, isaretler.
 */
export interface Senaryo {
  /** Kurulumun tam parmak izi — ayni kurulum tekrar kosulursa satir yenilenir. */
  id: string;
  /** Yalnizca işaretlerin parmak izi. */
  secimParmak: string;
  mode: ModeId;
  baslik: string;
  satir: number;
  bedel: number;
  /** 14-garanti geçerli mi (açık nokta yok ve en kötü durum ≤ 1). */
  garanti: boolean;
  acik: number;
  altSinir: number;
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
    mode: r.mode ?? kurulum.mode,
    baslik: r.baslik,
    satir: r.satir_sayisi,
    bedel: r.kolon_bedeli,
    garanti: r.acik === 0 && r.worst <= 1,
    acik: r.acik,
    altSinir: r.alt_sinir,
    pKumeIci: r.advanced ? r.advanced.exact.p_kume_ici / 100 : null,
    kurulum,
  };
}

/**
 * Listeye ekler. Ayni kurulum tekrar kosulursa YERINDE yenilenir —
 * varyant denerken listenin ayni satirin kopyalariyla dolmasi, asil
 * karsilastirmayi ekrandan iterdi.
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
 * Karsilastirmada one cikacak satir: AYNI secim uzerinde kosulmus,
 * 14-garantiyi veren ve en ucuz olan. Garanti vermeyen bir senaryo daha
 * ucuz olabilir ama onunla kiyas yanlis olurdu — farkli sey satin
 * aliniyor. Boyle bir satir yoksa null.
 */
export function enUcuzGarantili(
  liste: Senaryo[],
  secimParmak: string,
): Senaryo | null {
  const adaylar = liste.filter((s) => s.secimParmak === secimParmak && s.garanti);
  if (!adaylar.length) return null;
  return adaylar.reduce((a, b) => (b.bedel < a.bedel ? b : a));
}
