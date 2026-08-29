/**
 * Guncel sezonun iskeleti ve GERCEK verisi.
 *
 * Hafta verisi artik elle tutulmuyor: `super-toto-veri.json`,
 * `backend/scripts/super_toto_frontend.py` tarafindan
 * `backend/data/super_toto` altindan uretilir. Backend kaynaktir, bu dosya
 * onu okur. Besleme eskirse CI kirilir (`--kontrol`) — sessizce eskimis bir
 * arayuz, bos bir arayuzden daha kotudur cunku yanlis oldugu belli olmaz.
 *
 * Gecmis sezon (2025/2026) buraya GIRMEZ: o veri backend'in
 * `st_history_2025_26.json` dosyasinda yasar ve /istatistik altindan
 * okunur. Ikisi bilerek ayri tutulur — biri arsiv, biri isleyen sezon.
 */
import veri from "./super-toto-veri.json";
import { MAC_SAYISI } from "./types";

/** Uzerinde calisilan sezon. */
export const SUPER_TOTO_SEZON = veri.season;

/**
 * Sezonun planlanan hafta sayisi. Gecen sezon 41 tam hafta uretti;
 * takvim uzarsa TEK degistirilecek yer burasidir.
 */
export const HAFTA_SAYISI = 41;

/** Bir kuponun mac sayisi — motorun sabiti (backend `meta.MATCH_COUNT`). */

/** Beslemeyi ureten marj arindirma yontemi — sayfada yazar. */
export const ARINDIRMA = veri.arindirma;

export interface SuperTotoMac {
  no: number;
  date: string | null;
  kickoff: string | null;
  league: string;
  home: string;
  away: string;
  /** Orani ilan edilmemis mac icin null — bu bir tahmin yoklugudur. */
  odds: Record<string, number> | null;
  odds_missing: boolean;
  probs: Record<string, number>;
  fav: string | null;
  margin: number;
  play: Record<string, number>;
  /** Sonuc girilmemisse null. */
  result: string | null;
}

/**
 * DONDURULMUS kupon — sonuclar gorulmeden kaydedilmis isaretler.
 *
 * Bu bir KAYITTIR, yeniden hesaplanmaz. Kural degismese bile OLCEK
 * degisebilir (marj arindirma varsayilani 2026-08'de `orantili`dan
 * `shin`e cevrildi) ve ayni esik baska isaretler uretir. Yeniden
 * hesaplanan bir kuponu gostermek, "sonuclar gorulmeden dondu" diyen
 * kaydin ustune sonradan yazmak olurdu.
 */
export interface SuperTotoKupon {
  picks: string[];
  label: string | null;
  columns: number | null;
  rows: number | null;
  in_set_p: number | null;
  banko_esik: number | null;
  uclu_esik: number | null;
  /**
   * Hangi KURALLA donduruldugu. Ilk iki hafta `esik`ti ve kart kural adini
   * SABIT yaziyordu; 3. hafta `hedef + kalabalik ayari` ile dondurulunca
   * esikler bos kaldi ve kart "esik / " diye yanlis bir kural bildirdi.
   */
  kural: string | null;
  /** Hangi olcekte donduruldugu — bu alan olmadan isaretler yorumlanamaz. */
  arindirma: string | null;
  marj_ort_pct: number | null;
  frozen_at: string | null;
  results_known: boolean | null;
  /** Oynanacak 16 satir — kuponu dolduracak kisi bunlari gorur. */
  lines: string[] | null;
  /**
   * Kuralin verdigi alternatifler ve her birinin OLCULMUS bedeli. Kupon
   * "nicin bu" sorusunu ancak yaninda reddettikleriyle cevaplayabilir.
   */
  variants: SuperTotoVaryant[];
  /** Kalabalik ayarinin neyi neye degistigi — kaydin kendi gerekcesi. */
  kalabalik_gerekcesi: string | null;
  /** Kupon aninda KESINLIKLE elde olan fiyatla (acilis) kurulan surum. */
  duyarlilik: SuperTotoDuyarlilik | null;
}

/** Kuralin ayni haftada urettigi bir secenek ve olculmus bedeli. */
export interface SuperTotoVaryant {
  label: string | null;
  picks: string[];
  columns: number | null;
  /** P(en iyi kolon >= 12) — kuponun asil olcusu. */
  hedef: number | null;
  in_set_p: number | null;
  crowd_in_set_p: number | null;
  crowd_ratio: number | null;
}

/** Fiyat duyarliligi: kapanis elde degilse bedeli ne olurdu. */
export interface SuperTotoDuyarlilik {
  not: string | null;
  fark: string | null;
  picks: string[] | null;
  hedef: number | null;
}

/**
 * FIYAT KAYNAKLARI — uc bahisci x acilis/kapanis.
 *
 * Her sayi marj ARINDIRILMIS olasiliktir, ham oran degil: ham oranin
 * hareketi, piyasanin fikir degistirmesiyle bahiscinin marjini
 * degistirmesini karistirirdi.
 *
 * Ilk iki hafta tek bir bultenin tek anini tasiyor; orada `null`dur.
 */
export interface SuperTotoFiyatlar {
  /** Ayni ani gosteren bahisciler; ilki ANA fiyattir. */
  books: string[];
  main_book: string;
  /** Bahisci x an -> ortalama marj (yuzde puan). */
  margins: Record<string, number>;
  /**
   * Kapanisi acilisiyla BIREBIR ayni olan satirlar. Bunlar fiyat degil,
   * tazelenmemis kayittir: ayrismada buyuk gorunur ve gorus farki
   * sanilir.
   */
  stale_closing: Record<string, number[]>;
  rows: SuperTotoFiyatSatiri[];
}

/** Haftanin SONUC karnesi. Uretici: `super_toto_frontend._sonuc_blok`. */
export interface SuperTotoSonuc {
  /** 15 karakterlik gercek sonuc dizisi. */
  results: string;
  results_source: string | null;
  results_entered_at: string | null;
  /** Her dondurulmus kaydin AYNI olcuyle karnesi. */
  kayitlar: SuperTotoKayitKarnesi[];
  kalabalik: {
    halk_kuponu: string;
    halk_dogru: number;
    piyasa_kuponu: string;
    piyasa_dogru: number;
    beklenen_halk_dogru: number;
    beklenen_piyasa_dogru: number;
  };
  payout: Array<{
    correct: number;
    winners: number;
    prize: number | null;
  }> | null;
  payout_source: string | null;
  note: string;
}

export interface SuperTotoKayitKarnesi {
  /** "1. Tahmin" / "2. Tahmin" */
  ad: string;
  picks: string[];
  /** Kaplamanin en iyi kolonunun kac dogrusu var. */
  best: number;
  /** Secim kumesinin disinda kalan mac numaralari. */
  misses: number[];
  miss_count: number;
  /** Kuponun KENDI olasiliklarindan gelen beklenti — hafta iyi mi gecti. */
  expected_misses: number;
  p_in_set: number;
  p_at_least_actual: number;
  per_match: Array<{
    no: number;
    pick: string;
    gercek: string;
    tuttu: boolean;
  }>;
}

export interface SuperTotoFiyatSatiri {
  no: number;
  books: Record<string, Record<string, number> | null>;
  /** Acilistan kapanisa en cok oynayan sembol ve kaydigi miktar. */
  movement_symbol: string | null;
  movement: number | null;
  /** Ayni ani gosteren bahisciler arasindaki en buyuk fark. */
  disagreement: number;
}

/** Yerine yenisi kurulmus onceki surum. Revizyon gorunur kalmali. */
export interface SuperTotoEskiKupon {
  reason: string | null;
  revised_at: string | null;
  arindirma: string | null;
  picks: string[];
}

/** Bugunku kuralin AYNI hafta icin uretecegi kupon — kiyas icin, kayit degil. */
export interface SuperTotoBugunkuKupon {
  picks: string[];
  banko: number[];
  cift: number[];
  uclu: number[];
  columns: number | null;
  rows: number | null;
  in_set_p: number;
  banko_esik: number;
  uclu_esik: number;
  arindirma: string;
  /**
   * Kuponu kuran kural. Dondurulmus kuponlar `esik` ile kuruldu;
   * varsayilan `hedef`e cevrildi (docs §3.19). `hedef`, verilen butcede
   * P(en iyi kolon >= 12)'yi dogrudan enbuyukler.
   */
  kural: string;
  /** Butce (kolon) — esik kuralinin ayni haftada uretecegi maliyet. */
  butce: number | null;
  /** P(en iyi kolon >= 12) — kuponun asil sayisi. */
  p_hedef: number;
  /** Ayni haftada esik kurali kullanilsaydi cikacak deger. */
  p_hedef_esik: number;
}

/**
 * IKINCI tahmin — ayni hafta, bugunku aletlerin tamamiyla yeniden okunmus.
 *
 * 1. Tahmin'in KAYDINI degistirmez ve onun yerine GECMEZ; yaninda ayri bir
 * kayit olarak durur (uretici `scripts/super_toto_tahmin2.py`). Sayfa
 * ikisi arasinda gecis yapar, birini otekiyle karistirmaz.
 *
 * Alan `null` ise o hafta icin ikinci bir kayit yok ve "2. Tahmin" dugmesi
 * hic gosterilmez — bos bir panel, olmayan bir dugmeden kotudur.
 */
export interface SuperTotoTahmin2 {
  ad: string;
  frozen_at: string;
  results_known: boolean;
  /** Bugunku marj arindirma (`shin`). */
  arindirma: string;
  /** 1. Tahmin'in dondurulduğu olcek (`orantili`). */
  onceki_arindirma: string;
  /** Kuponu kuran kural (`hedef`). */
  kural: string;
  /** Kalabalik icin P(en iyi kolon >= 12)'den vazgecilen en cok oran. */
  kayip_orani: number;
  note: string;
  yenilikler: string[];
  /** 2. Tahmin'in isaretleri — kalabalik ayari uygulanmis plan. */
  picks: string[];
  /** Kalabalik gorulmeden kurulan plan (hedef kurali). */
  taban_picks: string[];
  /** Eski kural, yeni olcek — kiyas icin. */
  esik_picks: string[];
  columns: number | null;
  rows: number | null;
  engine: string | null;
  guaranteed_14: boolean | null;
  banko: number[];
  cift: number[];
  uclu: number[];
  p_hedef: number;
  in_set_p: number;
  crowd_in_set_p: number;
  /** Kume-ici / kalabalik-ici. 1'in USTU: olasiligina gore az oynanmis. */
  crowd_ratio: number;
  butce: number | null;
  butce_kaynagi: string;
  /** Oynanacak 16 satir. */
  lines: string[];
  ayar: {
    not: string;
    p_hedef_taban: number;
    p_hedef_ayarli: number;
    oran_taban: number;
    oran_ayarli: number;
    /** Kazaninca rakip yogunlugu — YALNIZCA taban ile ayarli arasinda okunur. */
    kat_taban: number;
    kat_ayarli: number;
    degisimler: {
      no: number;
      taban: string;
      yeni: string;
      prob_taban: number;
      prob_yeni: number;
      oynanma_taban: number;
      oynanma_yeni: number;
    }[];
  };
  /** 1. Tahmin ile kiyas — eski isaretler BUGUNKU olcekte olculmus. */
  kiyas: {
    eski_picks: string[];
    eski_arindirma: string;
    eski_kural: string;
    eski_p_hedef: number;
    eski_columns: number | null;
    eski_crowd_ratio: number;
    degisen_maclar: number[];
    not: string;
  } | null;
  /** Piyasadan bagimsiz gorusun kapsamasi. */
  gorus: {
    kapsama: number;
    dc_olan: number;
    n: number;
    kullanilabilir: boolean;
    tarihce_mac: number;
    tarihce_son: string | null;
    /** Korpusta karsiligi olmayan takimlar — o macta gorus YOKTUR. */
    eslesmeyen: string[];
    uyari: string;
  };
  /** Bagimsiz gorusun piyasadan koptugu maclar, sapmaya gore sirali. */
  ayrisma: {
    no: number;
    mac: string;
    piyasa: Record<string, number>;
    dc: Record<string, number>;
    piyasa_fav: string;
    dc_fav: string;
    sembol_farkli: boolean;
    toplam_sapma: number;
  }[];
  /** Kuskulu marjli satir duzeltilseydi ne olurdu — veri DUZELTILMEDI. */
  duyarlilik: {
    ortanca_marj: number;
    duzeltilen: { no: number; mac: string; marj: number }[];
    picks: string[];
    p_hedef: number;
    degisti: boolean;
    not: string;
  } | null;
  matches: {
    no: number;
    probs: Record<string, number>;
    probs_onceki: Record<string, number>;
    /** Dixon-Coles gorusu; `dc_var` kapaliysa null. */
    dc: Record<string, number> | null;
    dc_var: boolean;
    /** Elo puan farki (ev lehine pozitif). 1X2 DEGILDIR. */
    elo_farki: number | null;
    /** Elo'nun beklenen SKORU (0..1) — beraberlik yarim sayilir. */
    elo_beklenen: number | null;
    taban: string;
    isaret: string;
  }[];
}

export interface SuperTotoHafta {
  /** 1'den baslayan hafta numarasi. */
  week: number;
  program: string | null;
  /** Kupon kapanis tarihi (YYYY-MM-DD). Veri girilene kadar null. */
  close_date: string | null;
  /** 15 karakterlik sonuc dizisi ("1"/"0"/"2"). Sonuc gelene kadar null. */
  results: string | null;
  odds_source: string | null;
  odds_kind: string | null;
  play_source: string | null;
  /** Insanin dustugu notlar. */
  warnings_manual: string[];
  /** Kalite kapisinin urettigi uyarilar. Ikisi AYRI tutulur. */
  warnings_generated: string[];
  matches: SuperTotoMac[];
  /** Dondurulmus kayit. */
  coupon: SuperTotoKupon | null;
  /** Girdi degistigi icin yenilenmisse, onceki surum. */
  coupon_superseded: SuperTotoEskiKupon | null;
  /** Bugunku kuralin uretecegi kupon — kiyas. */
  coupon_today: SuperTotoBugunkuKupon | null;
  /** Ikisinin ayristigi mac numaralari. Bos ise olcek degisimi isaret degistirmemis. */
  coupon_drift: number[] | null;
  /** Ikinci kayit. Yoksa null — "2. Tahmin" dugmesi cikmaz. */
  tahmin2: SuperTotoTahmin2 | null;
  /**
   * Fiyat kaynaklari — uc bahisci x acilis/kapanis. Hafta dosyasi tek bir
   * bulten tasiyorsa null'dur ve bolum hic cizilmez.
   */
  prices: SuperTotoFiyatlar | null;
  /**
   * SONUC karnesi — tahmin kayitlarindan AYRI.
   *
   * Sonuc gelince tahmin panelleri sonucla doluyordu (mac tablosuna bir
   * "Sonuc" sutunu, kupon kartina "N/15 kume icinde"). Dondurulmus bir
   * kaydin uzerine sonradan bilinen bir sey yazmak, kaydin "o an ne
   * biliniyordu" sorusunu temiz cevaplamasini bozuyordu. Sonuc artik
   * kendi sekmesinde ve her iki kaydi da AYNI olcuyle karneliyor.
   *
   * Sonuc girilmemisse null'dur ve sekme hic gosterilmez.
   */
  sonuc: SuperTotoSonuc | null;
}

/** Verisi girilmis haftalar — beslemeden gelir. */
export const GIRILEN_HAFTALAR = veri.weeks as unknown as SuperTotoHafta[];

const GIRILEN = new Map(GIRILEN_HAFTALAR.map((h) => [h.week, h]));

/**
 * Sezonun tum haftalari. Verisi girilmis olanlar beslemeden, digerleri
 * bos iskelet olarak gelir — serit her zaman 41 sekme gosterir.
 */
export const HAFTALAR: SuperTotoHafta[] = Array.from(
  { length: HAFTA_SAYISI },
  (_, i): SuperTotoHafta =>
    GIRILEN.get(i + 1) ?? {
      week: i + 1,
      program: null,
      close_date: null,
      results: null,
      odds_source: null,
      odds_kind: null,
      play_source: null,
      warnings_manual: [],
      warnings_generated: [],
      matches: [],
      coupon: null,
      coupon_superseded: null,
      coupon_today: null,
      coupon_drift: null,
      tahmin2: null,
      prices: null,
      sonuc: null,
    },
);

/**
 * Bir haftanin verisi VAR mi — 15 macin kadrosu girilmis mi.
 *
 * Dikkat: bu "sonuclari geldi mi" DEGILDIR. Kupon dondurulmus ama maclar
 * daha oynanmamis bir hafta da doludur ve panelinde gosterilecek seyi
 * vardir (oranlar, olasiliklar, isaretler). Sonuc ayri sorulur.
 */
export function haftaDoluMu(h: SuperTotoHafta): boolean {
  return h.matches.length === MAC_SAYISI;
}

/** Haftanin IKINCI tahmini var mi — "2. Tahmin" dugmesinin tek kosulu. */
export function ikinciTahminVarMi(h: SuperTotoHafta): boolean {
  return h.tahmin2 !== null && h.tahmin2.picks.length === MAC_SAYISI;
}

/** Sonuclari gelmis hafta — yarim veri ortalamalara karismasin diye ayri. */
/**
 * Sonuc karnesi VAR mi — ucuncu sekme bunun uzerine cikar.
 *
 * `haftaSonuclandiMi`den ayri: o, hafta dosyasindaki `results` dizisine
 * bakar; bu ise karnenin gercekten uretilip uretilmedigine. Ikisi normalde
 * ayni cevabi verir ama besleme eskiyse ayrisir ve o durumda BOS bir
 * sekme gostermek, olmayan bir sekmeden kotudur.
 */
export function sonucVarMi(h: SuperTotoHafta): boolean {
  return h.sonuc !== null && h.sonuc.kayitlar.length > 0;
}

export function haftaSonuclandiMi(h: SuperTotoHafta): boolean {
  return typeof h.results === "string" && h.results.length === MAC_SAYISI;
}

/** Veri girilmis hafta sayisi — basliktaki rozetin kaynagi. */
export function doluHaftaSayisi(): number {
  return HAFTALAR.filter(haftaDoluMu).length;
}

/** Sonuclanmis hafta sayisi. */
export function sonuclananHaftaSayisi(): number {
  return HAFTALAR.filter(haftaSonuclandiMi).length;
}
