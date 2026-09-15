import type { SatirAnalizi } from "./kupon-analiz";
import { MAC_SAYISI, SEMBOLLER, type Sembol } from "./types";

/**
 * Kuponun kurulmasi — **karnenin en yuksek IKI sembolu**.
 *
 * Sahibinin kurali, kendi cumlesiyle: *"mevcut olan oran analizden en
 * yuksek ikiliyi alip sececeksin."* Besiktas–Erzurumspor ornegi:
 * 1 %80,9 · 0 %12,4 · 2 %6,7 -> isaret `1-0`.
 *
 * Kural KARNEDEN okur, piyasadan degil. Sayfanin varlik sebebi bu: piyasa
 * zaten oranin kendisi, karne ise "bu fiyatta gecmiste ne olmus".
 *
 * ─── Her mac CIFTE demek ve bunun bir bedeli var ──────────────────────────
 *
 * 15 macin hepsi iki sembol tasirsa kolon sayisi `2^15 = 32.768`tir. Bu
 * sabit bir sayidir, girdiye bagli degil — kural her satira ayni sayida
 * sembol veriyor. Arayuz bedeli yaninda yaziyor; karar sahibinin.
 *
 * ─── Esitlik neyle bozulur ────────────────────────────────────────────────
 *
 * Iki sembolun karnesi BIREBIR ayni cikabilir (ornek: 100 macta 40/40/20).
 * O zaman sira PIYASAYA bakilir, o da esitse sembol duzenine (1, 0, 2).
 * Rastgele ya da "ilk gelen" bir secim, ayni girdiyle iki farkli kupon
 * uretirdi ve kayit yeniden uretilemez olurdu.
 *
 * ─── Karnesi olmayan satir ────────────────────────────────────────────────
 *
 * Sorgusu hata almis ya da hic ornek bulunamamis bir satirda karne YOKTUR.
 * O satir sessizce atlanmaz ve uydurulmaz: piyasadan secilir ve satir
 * `kaynak: "piyasa"` diye ISARETLENIR. Arayuz bunu gosterir — kural
 * degismedi, o satirda uygulanacak veri yoktu.
 */

/** Bir satirin isareti nereden cikti. */
export type IsaretKaynagi = "karne" | "piyasa" | "yok";

export interface SatirIsareti {
  /** Secilen semboller — daima KUPON duzeninde (1, 0, 2). */
  semboller: Sembol[];
  kaynak: IsaretKaynagi;
  /** Karne yuzdeleri buyukten kucuge — arayuz sirayi gostersin diye. */
  sirali: { sembol: Sembol; deger: number | null; piyasa: number }[];
  /** Ornegi `AZ_ORNEK` altinda mi — yuzdeler okunmaz sayilir. */
  azOrnek: boolean;
  /** Esitlik bozuldu mu (iki sembolun karnesi birebir ayniydi). */
  esitlikBozuldu: boolean;
}

export interface KurulanKupon {
  satirlar: SatirIsareti[];
  /** Isaretlerin carpimi — `2^cifte · 3^uclu`. */
  kolon: number;
  /** Karne yerine piyasadan secilen satirlarin 0 tabanli sirasi. */
  piyasadanSecilen: number[];
  /** Ornegi yetersiz satirlarin 0 tabanli sirasi. */
  azOrnekli: number[];
  /** Esitligin piyasa/duzen ile bozuldugu satirlar. */
  esitlikli: number[];
  /** Hic isaret uretilememis satir var mi — kupon EKSIK demektir. */
  eksik: number[];
}

/** Kac sembol isaretlenecek. Sahibinin kurali: en yuksek IKI. */
export const IKILI = 2;

/** Bir satirin SIRALANMIS okumasi — isaret secimi bunun uzerine kurulur. */
export interface SatirOkumasi {
  kaynak: IsaretKaynagi;
  /** Buyukten kucuge sirali semboller. `kaynak` "yok" ise sira ham duzen. */
  sirali: { sembol: Sembol; deger: number | null; piyasa: number }[];
  azOrnek: boolean;
  /** Siralamanin okundugu deger: karne varsa karne, yoksa piyasa. */
  agirlik: (x: { deger: number | null; piyasa: number }) => number;
}

/**
 * Tek satirin karnesini SIRALAR — isaret saymadan.
 *
 * Siralama uc anahtarli ve sirasi onemli: karne -> piyasa -> sembol duzeni.
 * Ilk ikisi veriden gelir, ucuncusu yalnizca belirlilik icindir.
 *
 * Ayri bir fonksiyon, cunku iki musterisi var: her maca sabit sayida sembol
 * veren `satiriKur`, ve maclara FARKLI derinlik dagitan `kupon-sekil`.
 * Ikisinin ayni siradan okumasi sart — ayrisirlarsa ayni karne iki farkli
 * isaret uretirdi.
 */
export function satirOkumasi(sonuc: SatirAnalizi | undefined): SatirOkumasi {
  const veri = sonuc?.durum === "bitti" ? sonuc.veri : null;
  const semboller = veri?.toplam.semboller;

  const sirali = SEMBOLLER.map((sembol) => ({
    sembol,
    deger: semboller?.[sembol]?.oran ?? null,
    piyasa: semboller?.[sembol]?.piyasa ?? 0,
  }));

  // Karne okunabiliyor mu: en az bir sembolde ampirik oran var mi.
  const karneVar = sirali.some((x) => x.deger != null);
  const kaynak: IsaretKaynagi = karneVar
    ? "karne"
    : sirali.some((x) => x.piyasa > 0)
      ? "piyasa"
      : "yok";

  const agirlik = (x: { deger: number | null; piyasa: number }) =>
    kaynak === "karne" ? (x.deger ?? -1) : x.piyasa;

  if (kaynak === "yok") {
    return { kaynak, sirali, azOrnek: false, agirlik };
  }

  const duzen = (s: Sembol) => SEMBOLLER.indexOf(s);
  const siraliKopya = [...sirali].sort(
    (a, b) =>
      agirlik(b) - agirlik(a) ||
      // Karne esitse PIYASA bozar; o da esitse sembol duzeni (1, 0, 2).
      b.piyasa - a.piyasa ||
      duzen(a.sembol) - duzen(b.sembol),
  );

  return {
    kaynak,
    sirali: siraliKopya,
    azOrnek: veri ? !veri.toplam.yeterli : false,
    agirlik,
  };
}

/** Sirali okumadan `kacSembol` tanesini isaretler. */
export function okumadanIsaret(okuma: SatirOkumasi, kacSembol: number): SatirIsareti {
  const { kaynak, sirali, azOrnek, agirlik } = okuma;
  if (kaynak === "yok") {
    return { semboller: [], kaynak, sirali, azOrnek: false, esitlikBozuldu: false };
  }

  const secilen = sirali.slice(0, kacSembol).map((x) => x.sembol);
  // Esitlik yalnizca SINIRDA onemli: secilenin sonuncusu ile disarida
  // kalanin ilki ayni degerdeyse secim veriyle degil kuralla yapildi.
  const sinirIci = sirali[kacSembol - 1];
  const sinirDisi = sirali[kacSembol];
  const esitlikBozuldu =
    !!sinirIci && !!sinirDisi && agirlik(sinirIci) === agirlik(sinirDisi);

  return {
    // Sira KUPON duzeni (1, 0, 2) — buyuklukten bagimsiz.
    semboller: SEMBOLLER.filter((s) => secilen.includes(s)),
    kaynak,
    sirali,
    azOrnek,
    esitlikBozuldu,
  };
}

function satiriKur(sonuc: SatirAnalizi | undefined, kacSembol: number): SatirIsareti {
  return okumadanIsaret(satirOkumasi(sonuc), kacSembol);
}

/**
 * 15 satirin tamamindan kuponu kurar.
 *
 * Girdi, ekrandaki analizin KENDISI. Ayri bir sorgu atilmiyor: kupon, o
 * analizden cikiyor ve ikisinin ayrisabilmesi icin bir sebep yok.
 */
export function kuponKur(
  sonuclar: SatirAnalizi[],
  kacSembol: number = IKILI,
): KurulanKupon {
  const satirlar = Array.from({ length: MAC_SAYISI }, (_, i) =>
    satiriKur(sonuclar[i], kacSembol),
  );

  const piyasadanSecilen: number[] = [];
  const azOrnekli: number[] = [];
  const esitlikli: number[] = [];
  const eksik: number[] = [];
  let kolon = 1;

  satirlar.forEach((s, i) => {
    if (s.kaynak === "piyasa") piyasadanSecilen.push(i);
    if (s.kaynak === "yok") eksik.push(i);
    if (s.azOrnek) azOrnekli.push(i);
    if (s.esitlikBozuldu) esitlikli.push(i);
    // Isaretsiz satir kuponu KURULAMAZ yapar; carpima 0 sokmak yerine
    // satir `eksik` sayilir ve arayuz kuponu kaydettirmez.
    kolon *= Math.max(1, s.semboller.length);
  });

  return { satirlar, kolon, piyasadanSecilen, azOrnekli, esitlikli, eksik };
}

/** Kuponun TL bedeli. Kolon bedeli SUNUCUDAN gelir, burada sabit yok. */
export function kuponBedeli(kolon: number, kolonBedeliTl: number | null): number | null {
  if (!kolonBedeliTl || !Number.isFinite(kolonBedeliTl)) return null;
  return kolon * kolonBedeliTl;
}
