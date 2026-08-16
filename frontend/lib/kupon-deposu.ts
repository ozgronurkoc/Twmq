import {
  MAC_SAYISI,
  type CouponRow,
  type ModeId,
  type Sembol,
  type SolveResult,
} from "./types";
import { siralaSemboller } from "./utils";

/**
 * Adlandirilmis kupon deposu (tarayici yereli).
 *
 * Neden `localStorage` ve neden `sessionStorage` degil: kayit sekme
 * kapaninca kaybolmamali — `lib/transfer.ts`'teki hafta devrinin tam tersi
 * bir ihtiyac. Devir tek seferlik bir tasima, bu ise kalici bir defter.
 *
 * Neden sunucuda degil: bu repoda kullanici hesabi yok ve kupon kimin
 * oynadigini soyleyen bir veri. Sunucuya yazmak, olmayan bir hesap
 * sistemini ima etmek olurdu. Kayit tarayicida kalir; baska cihazda
 * gorunmez ve bu KASITLIDIR.
 *
 * Neden okurken dogrulaniyor: depoya kullanici da (devtools) eski surumler
 * de yazabilir. Dogrulanmamis bir `Sembol[][]` arayuze girerse izgara bos
 * mac cizer, motor da ValueError verir. Bozuk kayit sessizce ATILIR —
 * tamir edilmeye calisilmaz, cunku neyin kastedildigi bilinemez.
 */
const ANAHTAR = "twmq.kayitli-kuponlar";

/** Depo bicimi surumu. Uyusmayan tum depo atilir. */
const SURUM = 1;

export const AD_UZUNLUK = 60;
export const KUPON_SINIRI = 50;

/**
 * Uretilen formulun kaydedilen ozeti. `rows` kota basincinda dusurulebilir
 * (bkz. `kuponKaydet`), o yuzden ayri ve nullable.
 */
export interface KuponOzeti {
  baslik: string;
  satir_sayisi: number;
  /** Odenecek tutar budur. `satir_sayisi` ile karistirilmamali. */
  kolon_bedeli: number;
  guaranteed: boolean;
  match_count: number;
  rows: CouponRow[] | null;
}

export interface KayitliKupon {
  ad: string;
  /** Kayit ani (epoch ms). Liste buna gore yeniden eskiye siralanir. */
  ts: number;
  matches: Sembol[][];
  mode: ModeId;
  variant: number;
  /** Formul uretilmeden kaydedildiyse null — yalnizca isaretler saklanir. */
  ozet: KuponOzeti | null;
}

interface Depo {
  v: number;
  kuponlar: KayitliKupon[];
}

export type KayitSonucu =
  | { ok: true; liste: KayitliKupon[]; satirDusuruldu: boolean }
  | { ok: false; hata: string };

// ─── Dogrulama ────────────────────────────────────────────────────────────

function secimleriDogrula(x: unknown): Sembol[][] | null {
  if (!Array.isArray(x) || x.length !== MAC_SAYISI) return null;
  const out: Sembol[][] = [];
  for (const satir of x) {
    if (!Array.isArray(satir)) return null;
    // siralaSemboller hem gecersiz girdileri eler hem kupon duzenine sokar.
    const semboller = siralaSemboller(satir.filter((s) => typeof s === "string"));
    if (!semboller.length) return null;
    out.push(semboller);
  }
  return out;
}

function satirlariDogrula(x: unknown): CouponRow[] | null {
  if (!Array.isArray(x) || !x.length) return null;
  const out: CouponRow[] = [];
  for (const ham of x) {
    if (!ham || typeof ham !== "object") return null;
    const { cells, cost } = ham as Partial<CouponRow>;
    if (!Array.isArray(cells) || !cells.every((c) => typeof c === "string")) {
      return null;
    }
    out.push({
      cells,
      cost: typeof cost === "number" && Number.isFinite(cost) && cost > 0 ? cost : 1,
    });
  }
  return out;
}

function ozetiDogrula(x: unknown): KuponOzeti | null {
  if (!x || typeof x !== "object") return null;
  const o = x as Partial<KuponOzeti>;
  if (typeof o.satir_sayisi !== "number" || typeof o.kolon_bedeli !== "number") {
    return null;
  }
  return {
    baslik: typeof o.baslik === "string" ? o.baslik : "—",
    satir_sayisi: o.satir_sayisi,
    kolon_bedeli: o.kolon_bedeli,
    guaranteed: o.guaranteed === true,
    match_count:
      typeof o.match_count === "number" ? o.match_count : MAC_SAYISI,
    rows: satirlariDogrula(o.rows),
  };
}

function kuponuDogrula(x: unknown): KayitliKupon | null {
  if (!x || typeof x !== "object") return null;
  const k = x as Partial<KayitliKupon>;
  if (typeof k.ad !== "string" || !k.ad.trim()) return null;
  const matches = secimleriDogrula(k.matches);
  if (!matches) return null;
  return {
    ad: k.ad.trim().slice(0, AD_UZUNLUK),
    ts: typeof k.ts === "number" && Number.isFinite(k.ts) ? k.ts : Date.now(),
    matches,
    mode: (typeof k.mode === "string" ? k.mode : "fix16") as ModeId,
    variant:
      typeof k.variant === "number" && Number.isFinite(k.variant) && k.variant >= 0
        ? Math.floor(k.variant)
        : 0,
    ozet: ozetiDogrula(k.ozet),
  };
}

// ─── Depo erisimi ─────────────────────────────────────────────────────────

/** Kayitlari yeniden eskiye dondurur. Depo yok/bozuk/eski surumse bos dizi. */
export function kuponlariOku(): KayitliKupon[] {
  if (typeof window === "undefined") return [];
  let ham: string | null;
  try {
    ham = window.localStorage.getItem(ANAHTAR);
  } catch {
    // Ozel sekme ya da depolama engelli: kayit ozelligi yok sayilir.
    return [];
  }
  if (!ham) return [];
  try {
    const depo = JSON.parse(ham) as Partial<Depo>;
    if (depo?.v !== SURUM || !Array.isArray(depo.kuponlar)) return [];
    return depo.kuponlar
      .map(kuponuDogrula)
      .filter((k): k is KayitliKupon => k !== null)
      .sort((a, b) => b.ts - a.ts);
  } catch {
    return [];
  }
}

function yaz(kuponlar: KayitliKupon[]): boolean {
  try {
    const depo: Depo = { v: SURUM, kuponlar };
    window.localStorage.setItem(ANAHTAR, JSON.stringify(depo));
    return true;
  } catch {
    return false;
  }
}

/** `SolveResult`ten kaydedilecek ozeti cikarir. */
export function ozetCikar(r: SolveResult): KuponOzeti {
  return {
    baslik: r.baslik,
    satir_sayisi: r.satir_sayisi,
    kolon_bedeli: r.kolon_bedeli,
    guaranteed: r.guaranteed,
    match_count: r.match_count,
    rows: r.rows,
  };
}

/**
 * Kaydeder ve guncel listeyi doner. Ayni ad varsa USTUNE YAZAR — cagiran
 * taraf onay almakla yukumludur.
 *
 * Kota dolduysa once satir tablosu dusurulup (`rows: null`) tekrar denenir:
 * bir kaydin tamamini kaybetmektense tabloyu kaybetmek yeglenir, cunku
 * isaretler + mod ile formul yeniden uretilebilir. Bu durumda
 * `satirDusuruldu` true doner ve arayuz kullaniciya soyler.
 */
export function kuponKaydet(yeni: Omit<KayitliKupon, "ts">): KayitSonucu {
  if (typeof window === "undefined") return { ok: false, hata: "Tarayıcı yok." };

  const ad = yeni.ad.trim().slice(0, AD_UZUNLUK);
  if (!ad) return { ok: false, hata: "Kupon adı boş olamaz." };

  const mevcut = kuponlariOku();
  const kalanlar = mevcut.filter((k) => k.ad !== ad);
  if (kalanlar.length >= KUPON_SINIRI) {
    return {
      ok: false,
      hata: `En fazla ${KUPON_SINIRI} kupon saklanır. Kaydetmek için önce birini sil.`,
    };
  }

  const kayit: KayitliKupon = { ...yeni, ad, ts: Date.now() };
  const liste = [kayit, ...kalanlar];

  if (yaz(liste)) return { ok: true, liste, satirDusuruldu: false };

  if (kayit.ozet?.rows) {
    const kirpik: KayitliKupon = {
      ...kayit,
      ozet: { ...kayit.ozet, rows: null },
    };
    const azaltilmis = [kirpik, ...kalanlar];
    if (yaz(azaltilmis)) {
      return { ok: true, liste: azaltilmis, satirDusuruldu: true };
    }
  }

  return {
    ok: false,
    hata: "Tarayıcı depolaması dolu veya engelli. Birkaç kaydı silip tekrar dene.",
  };
}

/** Siler ve guncel listeyi doner. */
export function kuponSil(ad: string): KayitliKupon[] {
  if (typeof window === "undefined") return [];
  const liste = kuponlariOku().filter((k) => k.ad !== ad);
  yaz(liste);
  return liste;
}
