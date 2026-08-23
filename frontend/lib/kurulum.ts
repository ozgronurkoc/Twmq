import {
  MAC_SAYISI,
  SEMBOLLER,
  type EngineDefaults,
  type ModeId,
  type ProbRow,
  type Sembol,
} from "./types";
// `esitPay` burada `uniformProb` ile BIREBIR ayni bir govdeydi.
import { normalize, uniformProb as esitPay } from "./utils";

/**
 * Monte Carlo ornek sayisinin sinirlari — sunucunun `/api/meta`'da ilan
 * ettigi degerlerle AYNI olmak zorunda (`meta.MC_MIN` / `MC_MAX`).
 *
 * Bu modul saf: React yok, istek yok (check.mjs onu dogrudan kosar), yani
 * calisma aninda `/api/meta`yi okuyamaz. Bu yuzden deger burada duruyor ve
 * Faz 5'in urettigi sozlesme dosyasi ikisinin ayrismadigini denetleyecek.
 */
export const MC_MIN = 1000;
export const MC_MAX = 200_000;
export const VARSAYILAN_MC = 80_000;

/**
 * Formul sayfasinin KURULUMU: 15 macin isaretleri, olasilik satirlari ve
 * motorun tum ayarlari. Sonuc buraya girmez — sonuc turetilmis veridir,
 * kurulum ise kullanicinin elle urettigi tek sey.
 *
 * Iki tasiyicisi var ve ikisi ayri ise yarar:
 *
 *   yerel depo  — sessizdir, otomatiktir, YALNIZCA bu tarayicida durur.
 *                 Yenileme/sekme kapama kaybettirmesin diye.
 *   URL         — yalnizca kullanici "Baglantiyi kopyala" dediginde uretilir.
 *                 Adres cubugu kendiliginden GUNCELLENMEZ; her tusa basista
 *                 URL yazmak hem gecmisi kirletir hem de devir isaretiyle
 *                 (`?hafta=51`) carpisirdi.
 *
 * Onceligin sirasi sayfada soyle: URL > yerel depo, sonra devir paketi
 * yalnizca olasiliklarin uzerine yazar (bkz. lib/transfer.ts).
 *
 * `transfer.ts` "olasiliklar URL'e sigmaz ve paylasilabilir olmasi da
 * ISTENMEZ" der; bu onunla celismez. Orada anlatilan bir TASIMA'dir —
 * kullanici istemeden olusur ve takim adlari da tasir. Buradaki baglanti
 * ise kullanicinin acikca bastigi bir dugmeden cikar, takim adi tasimaz ve
 * 15 mac icin 90 karaktere sikistirilmistir.
 */
export interface Kurulum {
  matches: Sembol[][];
  /**
   * "Galatasaray – Fenerbahçe" biçiminde 15 etiket; boş olabilir.
   *
   * YEREL depoda durur, BAGLANTIYA girmez. Sebep `transfer.ts`'te verilen
   * kararla ayni: 15 takim adi URL'i uc katina cikarir. Ayrica etiket
   * cozume hic girmez — motor yalnizca isaretleri gorur — bu yuzden
   * sonucun parmak izine de dahil DEGILDIR: maca ad vermek ekrandaki
   * sonucu bayatlatmaz.
   */
  labels: string[];
  probsAcik: boolean;
  probs: ProbRow[];
  mode: ModeId;
  variant: number;
  budget: number;
  planCount: number;
  planApply: number;
  kati: boolean;
  fireMax: number;
  useBayes: boolean;
  preset: string;
  elleAyar: boolean;
  prior: number;
  evidence: number;
  mcSamples: number;
  eng: EngineDefaults;
}

/** README'deki örnek kupon: "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10" */
export const VARSAYILAN_MACLAR: Sembol[][] = [
  ["1"], ["1", "0"], ["1"], ["1", "2"], ["0"],
  ["1", "0"], ["2"], ["1", "0"], ["1"], ["1", "2"],
  ["0", "2"], ["1"], ["1", "0"], ["2"], ["1", "0"],
];

export const VARSAYILAN_ENG: EngineDefaults = {
  trials: 5,
  ls_iters: 30000,
  seed: 42,
  time_limit: 60,
  block_limit: 256,
  exact_limit: 512,
};

const MODLAR: readonly ModeId[] = [
  "fix16", "auto", "exact", "block", "heuristic", "butce", "maxcov",
] as const;

/** Yerel depo anahtari. Surum numarasi anahtarin ICINDE: kurulumun sekli
 *  degisirse yeni anahtara gecilir, eski kayit okunmaya calisilmaz. */
const YEREL_ANAHTAR = "twmq.formul.kurulum.v1";

export function varsayilanKurulum(): Kurulum {
  return {
    matches: VARSAYILAN_MACLAR.map((r) => [...r]),
    labels: Array(MAC_SAYISI).fill(""),
    probsAcik: false,
    probs: VARSAYILAN_MACLAR.map((sel) => esitPay(sel)),
    mode: "fix16",
    variant: 0,
    budget: 32,
    planCount: 5,
    planApply: 1,
    kati: false,
    fireMax: 2,
    useBayes: false,
    preset: "dengeli",
    elleAyar: false,
    prior: 1,
    evidence: 10,
    mcSamples: VARSAYILAN_MC,
    eng: { ...VARSAYILAN_ENG },
  };
}

// ─── Dogrulama yardimcilari ───────────────────────────────────────────────
//
// Her alan tek tek kisitlanir. Bozuk bir baglantinin sayfayi kirmasi degil,
// o alani sessizce varsayilana dusurup HANGISININ dustugunu soylemesi
// gerekir — asagidaki `atlanan` listesi bunun icin.

// Uc ayristirici da ayni sozlesmeyi tasir: **deger yoksa ya da bozuksa
// yedek**. `undefined` de tam olarak "yok" demektir — `URLSearchParams.get`
// `null`, dizi erisimi ise `undefined` dondurur (`noUncheckedIndexedAccess`).
// Imzayi daraltip cagri yerinde `!` koymak, "burasi asla bos degil" diye bir
// sey iddia ederdi; oysa iddia edilmesi gereken sey bos OLABILECEGI.
type HamDeger = string | null | undefined;

function tamsayi(ham: HamDeger, alt: number, ust: number, yedek: number): number {
  if (ham === null || ham === undefined) return yedek;
  const n = Number(ham);
  if (!Number.isFinite(n)) return yedek;
  return Math.min(ust, Math.max(alt, Math.round(n)));
}

function ondalikDeger(ham: HamDeger, alt: number, ust: number, yedek: number): number {
  if (ham === null || ham === undefined) return yedek;
  const n = Number(ham);
  if (!Number.isFinite(n)) return yedek;
  return Math.min(ust, Math.max(alt, n));
}

function bayrak(ham: HamDeger, yedek: boolean): boolean {
  if (ham === null || ham === undefined) return yedek;
  return ham === "1" || ham === "true";
}

// ─── Isaretler: 15 karakter, her biri 1-7 arasi bit maskesi ───────────────
//
// bit0 = "1", bit1 = "0", bit2 = "2". Sifir gecersizdir: bos mac motorda
// ValueError uretir, o yuzden cozerken 7'ye (kapama) degil, o maci
// varsayilanda BIRAKMAYA karar verilir — bkz. `maclariCoz`.

/** Yalnizca isaretlerin parmak izi. Senaryo karsilastirmasi bunu kullanir:
 *  iki calisma ancak AYNI secim uzerinde kosulduysa bedelleri kiyaslanabilir. */
export function maclariKodla(matches: Sembol[][]): string {
  return matches
    .map((satir) => {
      let maske = 0;
      if (satir.includes("1")) maske |= 1;
      if (satir.includes("0")) maske |= 2;
      if (satir.includes("2")) maske |= 4;
      return String(maske || 1);
    })
    .join("");
}

function maclariCoz(ham: string | null): { matches: Sembol[][]; gecerli: boolean } {
  const yedek = VARSAYILAN_MACLAR.map((r) => [...r]);
  if (!ham || ham.length !== MAC_SAYISI) return { matches: yedek, gecerli: false };

  const cikti: Sembol[][] = [];
  for (const ch of ham) {
    const maske = Number(ch);
    if (!Number.isInteger(maske) || maske < 1 || maske > 7) {
      return { matches: yedek, gecerli: false };
    }
    // Kupon duzeninde (1, 0, 2) uret — alfabetik sira okuma hatasi yaptirir.
    const satir: Sembol[] = [];
    if (maske & 1) satir.push("1");
    if (maske & 2) satir.push("0");
    if (maske & 4) satir.push("2");
    cikti.push(satir);
  }
  return { matches: cikti, gecerli: true };
}

// ─── Olasiliklar: mac basina 4 karakter (binde birlik p1 + p0) ────────────
//
// p2 turetilir (1000 - p1 - p0), yani 15 mac = 60 karakter.
//
// Her deger 36 tabaninda IKI karakterdir. Ondalik yazim denendi ve kirikti:
// binde birlik bir olasilik 0..1000 arasi deger alir, yani 1000 DORT
// basamaktir. Banko bir macta (p=1.0) `padStart(3)` hicbir sey kirpmaz,
// alan 4 karaktere tasar ve sabit genislikli cozme o mactan sonraki tum
// maclari kaydirir. 36 tabaninda 1000 = "rs", iki karaktere sigar ve tasma
// imkansiz hale gelir (36^2 = 1296 > 1000).
//
// Kodlama KAYIPLIDIR: 0.4234 -> 0.423. Kayip Monte Carlo gurultusunun
// altinda kalir (80 bin ornekte standart hata ~0.002) ama tam degeri
// korumasi beklenmemeli. Ayrica satirlar NORMALIZE edilmis tasinir: ham
// agirlik giren (5/3/2) kullanicinin baglantisini acan kisi 0.5/0.3/0.2
// gorur. Yerel depo JSON tuttugu icin orada iki kayip da yoktur — ikisi de
// yalnizca PAYLASILAN baglantidadir.

const BINDE = 1000;

function binde(n: number, tavan: number): number {
  return Math.min(tavan, Math.max(0, Math.round(n * BINDE)));
}

function probsKodla(probs: ProbRow[]): string {
  return probs
    .map((row) => {
      const n = normalize(row);
      const p1 = binde(n["1"], BINDE);
      const p0 = binde(n["0"], BINDE - p1);
      return p1.toString(36).padStart(2, "0") + p0.toString(36).padStart(2, "0");
    })
    .join("");
}

function probsCoz(
  ham: string | null,
  matches: Sembol[][],
): { probs: ProbRow[]; gecerli: boolean } {
  const yedek = matches.map((sel) => esitPay(sel));
  if (!ham || ham.length !== MAC_SAYISI * 4 || !/^[0-9a-z]+$/.test(ham)) {
    return { probs: yedek, gecerli: false };
  }
  const cikti: ProbRow[] = [];
  for (let i = 0; i < MAC_SAYISI; i++) {
    const p1 = parseInt(ham.slice(i * 4, i * 4 + 2), 36);
    const p0 = parseInt(ham.slice(i * 4 + 2, i * 4 + 4), 36);
    if (!Number.isInteger(p1) || !Number.isInteger(p0)) return { probs: yedek, gecerli: false };
    if (p1 < 0 || p0 < 0 || p1 + p0 > BINDE) return { probs: yedek, gecerli: false };
    cikti.push({
      "1": p1 / BINDE,
      "0": p0 / BINDE,
      "2": (BINDE - p1 - p0) / BINDE,
    });
  }
  return { probs: cikti, gecerli: true };
}

// ─── URL ──────────────────────────────────────────────────────────────────

/**
 * Kurulumu sorgu dizesine cevirir. Varsayilanindan farkli olmayan alan
 * yazilmaz; boylece sade bir kurulumun baglantisi kisa kalir.
 */
export function kurulumuKodla(k: Kurulum): string {
  const v = varsayilanKurulum();
  const p = new URLSearchParams();

  p.set("s", maclariKodla(k.matches));
  if (k.mode !== v.mode) p.set("m", k.mode);
  if (k.variant !== v.variant) p.set("v", String(k.variant));
  if (k.fireMax !== v.fireMax) p.set("f", String(k.fireMax));
  if (k.kati !== v.kati) p.set("kt", k.kati ? "1" : "0");

  // Butce alanlari yalnizca butceli modlarda anlamli.
  if (k.mode === "butce" || k.mode === "maxcov") p.set("b", String(k.budget));
  if (k.mode === "butce") {
    p.set("pc", String(k.planCount));
    p.set("pa", String(k.planApply));
  }

  if (k.probsAcik) {
    p.set("p", probsKodla(k.probs));
    if (k.mcSamples !== v.mcSamples) p.set("mc", String(k.mcSamples));
    if (k.useBayes) {
      p.set("by", "1");
      if (k.elleAyar) {
        p.set("be", "1");
        p.set("pr", String(k.prior));
        p.set("ev", String(k.evidence));
      } else if (k.preset !== v.preset) {
        p.set("bp", k.preset);
      }
    }
  }

  const e = k.eng;
  const ev = v.eng;
  if (
    e.trials !== ev.trials || e.ls_iters !== ev.ls_iters || e.seed !== ev.seed ||
    e.time_limit !== ev.time_limit || e.block_limit !== ev.block_limit ||
    e.exact_limit !== ev.exact_limit
  ) {
    p.set(
      "e",
      [e.trials, e.ls_iters, e.seed, e.time_limit, e.block_limit, e.exact_limit].join(","),
    );
  }

  return p.toString();
}

export interface UrlCozum {
  kurulum: Kurulum;
  /** Bozuk oldugu icin varsayilana dusen alanlarin okunabilir adlari. */
  atlanan: string[];
}

/**
 * Sorgu dizesinden kurulum okur. `s` yoksa kurulum yok demektir (null doner);
 * boylece `?hafta=51` gibi ilgisiz parametreli adresler kurulum sanilmaz.
 */
export function kurulumuCoz(arama: string): UrlCozum | null {
  const p = new URLSearchParams(arama);
  if (!p.has("s")) return null;

  const v = varsayilanKurulum();
  const atlanan: string[] = [];

  const mac = maclariCoz(p.get("s"));
  if (!mac.gecerli) atlanan.push("maç seçimleri");

  const modHam = p.get("m");
  let mode = v.mode;
  if (modHam !== null) {
    if ((MODLAR as readonly string[]).includes(modHam)) mode = modHam as ModeId;
    else atlanan.push("mod");
  }

  // Olasilik alani bozuksa giris KAPALI acilir. Acik birakip secimlerden
  // tekduze deger uretmek, kullanicinin girmedigi bir tahmini Bayes'e ve
  // Monte Carlo'ya beslemek olurdu — bu arac tahmin uydurmaz.
  const probHam = p.get("p");
  const pr = probsCoz(probHam, mac.matches);
  const probsAcik = probHam !== null && pr.gecerli;
  if (probHam !== null && !pr.gecerli) atlanan.push("olasılıklar");

  const planCount = tamsayi(p.get("pc"), 1, 50, v.planCount);

  let eng = { ...v.eng };
  const engHam = p.get("e");
  if (engHam !== null) {
    const parca = engHam.split(",");
    if (parca.length === 6 && parca.every((x) => Number.isFinite(Number(x)))) {
      eng = {
        trials: tamsayi(parca[0], 1, 50, v.eng.trials),
        ls_iters: tamsayi(parca[1], 100, 500000, v.eng.ls_iters),
        seed: tamsayi(parca[2], 0, Number.MAX_SAFE_INTEGER, v.eng.seed),
        time_limit: tamsayi(parca[3], 1, 300, v.eng.time_limit),
        block_limit: tamsayi(parca[4], 2, 6561, v.eng.block_limit),
        exact_limit: tamsayi(parca[5], 2, 4096, v.eng.exact_limit),
      };
    } else {
      atlanan.push("motor ayarları");
    }
  }

  return {
    atlanan,
    kurulum: {
      matches: mac.matches,
      // Etiketler baglantida tasinmaz; cagiran taraf gerekiyorsa yerel
      // kayittan tamamlar.
      labels: Array(MAC_SAYISI).fill(""),
      probsAcik,
      probs: probsAcik ? pr.probs : mac.matches.map((s) => esitPay(s)),
      mode,
      variant: tamsayi(p.get("v"), 0, 9999, v.variant),
      budget: tamsayi(p.get("b"), 1, 10_000_000, v.budget),
      planCount,
      planApply: tamsayi(p.get("pa"), 1, planCount, v.planApply),
      kati: bayrak(p.get("kt"), v.kati),
      fireMax: tamsayi(p.get("f"), 0, 2, v.fireMax),
      useBayes: bayrak(p.get("by"), v.useBayes),
      preset: p.get("bp") || v.preset,
      elleAyar: bayrak(p.get("be"), v.elleAyar),
      prior: ondalikDeger(p.get("pr"), 0, 1000, v.prior),
      evidence: ondalikDeger(p.get("ev"), 0, 1000, v.evidence),
      // Ust sinir SUNUCUNUN ilan ettigi sinirdir (`/api/meta` limits.
      // mc_samples.max = 200_000). Burada 1_000_000 yaziyordu ve iki taraf
      // ayrisiyordu: `?mc=500000` tasiyan bir paylasim baglantisi cozuluyor
      // ama ne kaydiricida gosterilebiliyor ne de sunucuda kabul ediliyordu.
      // Faz 5'te uretilen sozlesme dosyasina baglanacak.
      mcSamples: tamsayi(p.get("mc"), MC_MIN, MC_MAX, v.mcSamples),
      eng,
    },
  };
}

/** Paylasilacak tam adres. Devir isareti (`?hafta`) tasinmaz — o baska
 *  tarayicida karsiligi olmayan bir oturum paketine isaret eder. */
export function paylasimAdresi(k: Kurulum): string {
  if (typeof window === "undefined") return "";
  const { origin, pathname } = window.location;
  return `${origin}${pathname}?${kurulumuKodla(k)}`;
}

/**
 * Adres cubugunu kurulumun adresine cevirir.
 *
 * Yalnizca kullanicinin bastigi dugmeden cagrilir, her degisiklikte DEGIL:
 * surekli yazmak gecmisi kirletir ve pano calismadiginda "adres cubugundan
 * kopyala" diyebilmek icin adresin dogru olmasi zaten sadece o an gerekir.
 * `replaceState` secildi — paylasma bir gezinme degildir, geri tusunun
 * kurulumlar arasinda gezinmesi beklenmez.
 */
export function adresiYaz(k: Kurulum): void {
  if (typeof window === "undefined") return;
  window.history.replaceState(null, "", paylasimAdresi(k));
}

/** Adres cubugundaki kurulumu (ve devir isaretini) dusurur. Sifirlamada
 *  cagrilir; aksi halde yenileme silinen kurulumu geri getirirdi. */
export function adresiTemizle(): void {
  if (typeof window === "undefined") return;
  window.history.replaceState(null, "", window.location.pathname);
}

// ─── Yerel depo ───────────────────────────────────────────────────────────

export function yereleYaz(k: Kurulum): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(YEREL_ANAHTAR, JSON.stringify(k));
  } catch {
    // Ozel sekme / kota dolu. Kalicilik bir kolaylik, sart degil — sayfa
    // kaydedemeden de calisir.
  }
}

/**
 * Yerel kaydi okur. Depodaki JSON'a GUVENILMEZ: elle kurcalanmis ya da eski
 * surumden kalmis olabilir, o yuzden URL'den gelen kadar siki dogrulanir.
 * Bunu kodu tekrar etmeden yapmanin yolu kaydi kodlayip cozmek.
 *
 * Olasiliklar bu turun DISINDA tutulur: kodlama binde birlik ve kayipli,
 * yerel depo ise JSON tasir. Tur icine alinsaydi kullanicinin yazdigi 0.4234
 * yalnizca sayfayi yeniledigi icin kutuda 0.423 olarak belirirdi.
 */
export function yereldenOku(): Kurulum | null {
  if (typeof window === "undefined") return null;
  try {
    const ham = window.localStorage.getItem(YEREL_ANAHTAR);
    if (!ham) return null;
    const aday = JSON.parse(ham) as Partial<Kurulum>;
    if (!Array.isArray(aday?.matches) || aday.matches.length !== MAC_SAYISI) return null;

    // Sekli varsayilanla tamamla, sonra kodla-coz turundan gecir.
    const tam: Kurulum = { ...varsayilanKurulum(), ...aday } as Kurulum;
    tam.matches = aday.matches.map((satir) =>
      SEMBOLLER.filter((s) => Array.isArray(satir) && satir.includes(s)),
    );
    if (tam.matches.some((s) => s.length === 0)) return null;

    const tur = kurulumuCoz(kurulumuKodla(tam));
    if (!tur) return null;

    const olasilik = tamOlasilik(aday.probs);
    return {
      ...tur.kurulum,
      // Etiketler de kodlama turunun DISINDA: baglanti onlari tasimaz,
      // tur icine alinsalardi yerel kayittan da silinirlerdi.
      labels: temizEtiketler(aday.labels),
      probsAcik: Boolean(aday.probsAcik) && olasilik !== null,
      probs: olasilik ?? tur.kurulum.probs,
    };
  } catch {
    return null;
  }
}

/** Etiket satirinin en fazla uzunlugu. Uzun bir yapistirma yerel depoyu
 *  sisirmesin; 80 karakter en uzun takim adi ciftini rahat aliyor. */
export const ETIKET_SINIR = 80;

/**
 * Herhangi bir girdiyi 15 elemanli, tek satirlik, kirpilmis etiket
 * dizisine cevirir. Kaynak ne olursa olsun (depo, devir paketi, kullanici
 * yapistirmasi) tek kapidan gecer.
 */
export function temizEtiketler(ham: unknown): string[] {
  const cikti: string[] = [];
  const dizi = Array.isArray(ham) ? ham : [];
  for (let i = 0; i < MAC_SAYISI; i++) {
    const deger = dizi[i];
    if (typeof deger !== "string") {
      cikti.push("");
      continue;
    }
    // Satir sonu izgara duzenini bozar; bosluklar sadelestirilir.
    cikti.push(deger.replace(/\s+/g, " ").trim().slice(0, ETIKET_SINIR));
  }
  return cikti;
}

/** Depodaki ham olasilik dizisini kayipsiz dogrular; bozuksa null doner. */
function tamOlasilik(ham: unknown): ProbRow[] | null {
  if (!Array.isArray(ham) || ham.length !== MAC_SAYISI) return null;
  const cikti: ProbRow[] = [];
  for (const satir of ham) {
    if (!satir || typeof satir !== "object") return null;
    const row = satir as Record<string, unknown>;
    const deger = (s: Sembol) => {
      const n = Number(row[s]);
      return Number.isFinite(n) && n >= 0 ? n : 0;
    };
    const aday: ProbRow = { "1": deger("1"), "0": deger("0"), "2": deger("2") };
    // Toplami sifir olan satir normalize edilemez; kayit bozuk sayilir.
    if (aday["1"] + aday["0"] + aday["2"] <= 0) return null;
    cikti.push(aday);
  }
  return cikti;
}

export function yereliTemizle(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(YEREL_ANAHTAR);
  } catch {
    /* zaten yazilamamisti */
  }
}
