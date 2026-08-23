import { SEMBOLLER, type ProbRow, type Sembol } from "./types";
import { normalize } from "./utils";

/**
 * Secim kumesinin dogru sonucu icerme olasiligi ve onu buyutmenin bedeli.
 *
 * NEDEN BU SAYFADA EN ONEMLI SAYI: 14-garanti KOSULLUDUR — ancak gercek
 * sonuc secim kumesinin icindeyse devreye girer. Sayfanin en gorunur
 * ogesi buyuk yesil "14-garanti VAR" kalkani, ama kosulun kendisi
 * olculmeden birakiliyordu. README'nin kendi ornek kuponu, check.sh'in
 * kendi ornek olasiliklariyla olculdu: kosul %0,0149 (~1/6.700).
 *
 * NEDEN ISTEMCIDE: hesap `∏ᵢ Σ_{s∈secᵢ} pᵢ(s)` — 15 carpma. Sunucuya
 * gitmesi icin hicbir sebep yok, ve gitmemesi sayesinde kullanici
 * isaretleri degistirirken sayiyi ANINDA gorur. Motoru calistirip 13 sn
 * beklemek gerekmez.
 *
 * BU BIR KAZANMA OLASILIGI DEGILDIR. Ikramiye, kolon bedeli ve kac kisinin
 * tutturdugu hesaba girmez; bu yalnizca garantinin gecerli olma kosuludur.
 */

export interface Oneri {
  /** 0 tabanli maç sırası. */
  mac: number;
  sembol: Sembol;
  /** Küme-içi olasılık bu kadar katlanır. Küme-içi 0 ise Infinity. */
  kumeCarpani: number;
  /** Değişken uzay (ve bedel) bu kadar katlanır: (k+1)/k. */
  bedelCarpani: number;
  /** kumeCarpani / bedelCarpani — ödenen her kolon başına kazanç. */
  verim: number;
}

export interface KumeIci {
  /** 0..1. Herhangi bir maçın kütlesi 0 ise 0. */
  p: number;
  /**
   * Seçim dışına HİÇ kütle verilmemiş — yani kullanıcı daha tahmin
   * girmemiş. Bu durumda `p` tanım gereği 1 çıkar ve hiçbir şey anlatmaz;
   * arayüz sayı yerine bunu söyler. Kapama (üç işaretli) maçlar sayılmaz,
   * onların kütlesi zaten her tahminde 1'dir.
   */
  bilgiYok: boolean;
  /** Maç başına küme-içi kütle: seçili sembollerin olasılık toplamı. */
  kutleler: number[];
  /** Kütlesi 0 olan maçların 0 tabanlı sırası — küme bu tahminlerle imkânsız. */
  imkansizlar: number[];
  /** En düşük kütleli üç maç (0 tabanlı), küçükten büyüğe. */
  zayiflar: number[];
  /** Verime göre sıralı, en fazla 3 ekleme önerisi. */
  oneriler: Oneri[];
}

export function kumeIciHesapla(matches: Sembol[][], probs: ProbRow[]): KumeIci {
  const kutleler: number[] = [];
  const imkansizlar: number[] = [];
  const oneriler: Oneri[] = [];

  for (let i = 0; i < matches.length; i++) {
    const sec = matches[i] ?? [];
    const n = normalize(probs[i] ?? { "1": 1 / 3, "0": 1 / 3, "2": 1 / 3 });
    const kutle = sec.reduce((a, s) => a + (n[s] || 0), 0);
    kutleler.push(kutle);
    if (kutle <= 0) imkansizlar.push(i);

    const k = sec.length || 1;
    for (const s of SEMBOLLER) {
      if (sec.includes(s)) continue;
      const pay = n[s] || 0;
      // Olasiligi sifir olan sembolu eklemek kume-ici olasiligi
      // BUYUTMEZ, yalnizca bedeli iki katina cikarir. Oneri degildir.
      if (pay <= 0) continue;
      // Kutle 0 iken carpan tanimsiz; ekleme olasiligi sifirdan
      // cikardigi icin sonsuz kazanc sayilir ve basa gelir.
      const kumeCarpani = kutle > 0 ? (kutle + pay) / kutle : Infinity;
      const bedelCarpani = (k + 1) / k;
      oneriler.push({
        mac: i,
        sembol: s,
        kumeCarpani,
        bedelCarpani,
        verim: kumeCarpani / bedelCarpani,
      });
    }
  }

  const p = imkansizlar.length ? 0 : kutleler.reduce((a, b) => a * b, 1);

  // `kutleler` `matches` ile ayni uzunlukta uretilir; yine de hizasi
  // bozulursa o satiri "bilgi tasiyor" saymak yanlis olurdu — bilgi
  // yoklugu iddiasi ancak butun kutleler OKUNABILDIGINDE kurulabilir.
  const kisitli = matches
    .map((sec, i) => ({ sec, kutle: kutleler[i] }))
    .filter((x) => (x.sec?.length ?? 0) < SEMBOLLER.length);
  const bilgiYok =
    kisitli.length > 0 &&
    kisitli.every((x) => x.kutle !== undefined && x.kutle >= 1 - 1e-9);

  // Tum kutleler esitse "en zayif uc" diye bir sey YOKTUR; siralamanin
  // ilk ucunu isaretlemek onlari keyfi olarak sucluyor. Varsayilan
  // satirlarda (hepsi 1.0) tam bu oluyordu.
  const enAz = Math.min(...kutleler);
  const enCok = Math.max(...kutleler);
  const zayiflar =
    kutleler.length && enCok - enAz > 1e-9
      ? kutleler
          .map((kutle, i) => ({ kutle, i }))
          .sort((a, b) => a.kutle - b.kutle)
          .slice(0, 3)
          .map((x) => x.i)
      : [];

  oneriler.sort((a, b) => b.verim - a.verim || a.mac - b.mac);

  return {
    p,
    bilgiYok,
    kutleler,
    imkansizlar,
    zayiflar,
    oneriler: oneriler.slice(0, 3),
  };
}

/**
 * Kure-kaplama alt siniri: yaricapi 1 olan bir top `1 + Σ(kᵢ-1)` nokta
 * kapsar, dolayisiyla hicbir formul `ceil(uzay / top)` kolonun altina
 * inemez. Sunucu da ayni sayiyi doner (`alt_sinir`); burada tekrar
 * hesaplanmasinin sebebi kullanicinin motoru CALISTIRMADAN once bedelin
 * alt sinirini gorebilmesi.
 */
export function kaplamaAltSiniri(matches: Sembol[][]): {
  uzay: number;
  topBoyutu: number;
  altSinir: number;
} {
  let uzay = 1;
  let topBoyutu = 1;
  for (const satir of matches) {
    const k = satir.length || 1;
    uzay *= k;
    topBoyutu += k - 1;
  }
  return { uzay, topBoyutu, altSinir: Math.ceil(uzay / topBoyutu) };
}

/**
 * Kucuk olasiliklari okunur yazar.
 *
 * Kucuk degerlerde SABIT ondalik ise yaramaz ve esik koymak da yetmez: bu
 * sayfada tipik deger %0,0149 civari, yani hangi esigi koyarsan koy onun
 * hemen bir yaninda kaliyor ve `toFixed(3)` iki farkli kuponu ayni
 * "%0.015" yapip aradaki farki yutuyor. Bu yuzden %1'in altinda ondalik
 * degil ANLAMLI BASAMAK sayilir.
 *
 * Ayirac nokta: bitisikteki exact/Monte Carlo panelleri de `toFixed` ile
 * nokta basiyor, sayfa icinde iki ayri ayirac olmasin.
 */
export function olasilikYaz(p: number): string {
  if (!Number.isFinite(p) || p <= 0) return "%0";
  const pct = p * 100;
  if (pct >= 10) return `%${pct.toFixed(1)}`;
  if (pct >= 1) return `%${pct.toFixed(2)}`;
  // toPrecision sondaki sifirlari birakir (0.002 -> "0.00200"); Number'a
  // cevirip geri almak onlari duser.
  return `%${Number(pct.toPrecision(3))}`;
}

/** "~1/6.700" — yuzde tek basina kucuk sayilarda his vermiyor. */
export function birdeKac(p: number): string | null {
  if (!Number.isFinite(p) || p <= 0 || p >= 1) return null;
  return `1/${Math.round(1 / p).toLocaleString("tr-TR")}`;
}
