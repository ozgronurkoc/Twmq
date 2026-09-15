import type { SatirAnalizi } from "./kupon-analiz";
import {
  okumadanIsaret,
  satirOkumasi,
  type SatirIsareti,
  type SatirOkumasi,
} from "./kupon-kur";
import { MAC_SAYISI } from "./types";

/**
 * **Sekilli kupon** — 5. haftada oynanan tek sistemin mantigi.
 *
 * `kupon-kur` her maca AYNI sayida sembol veriyor (en yuksek ikili) ve
 * bunun bir bedeli var: `2^15 = 32.768` kolon, girdiden bagimsiz. Burada
 * kural degisiyor — derinlik maca gore dagitiliyor:
 *
 *     banko (1 sembol)   en emin maclar
 *     cifte (2 sembol)   ortadakiler
 *     uclu  (3 sembol)   en belirsiz maclar
 *
 * Sahibinin istegi, kendi cumlesiyle: *"5. haftada yaptigimiz tekli kuponun
 * mantigindan kuponlar olusturmak ... 6 banko 9 uclu ve 5 banko 5 cift 5
 * uclu seklinde 2 ayri kupon"*, ve *"her kuponda en fazla tekten en cok
 * cifte ve en cok ciftten en cok ucluye dogru ... derecelendirilecek."*
 *
 * ─── 6 banko + 9 uclu neden tanidik bir sayi ──────────────────────────────
 *
 * `3^9 = 19.683` kolon. 5. haftada OYNANAN tek sistemin kolon sayisi tam
 * buydu (`.claude/devam_notu.md`, §3.82): 19.683 kolon, 12/15, ₺4.436,90.
 * Yani bu sekil yeni bir fikir degil, oynanmis kuponun seklidir.
 *
 *     6 banko + 9 uclu        3^9            = 19.683 kolon
 *     5 banko + 5 cift + 5 uclu  2^5 · 3^5   =  7.776 kolon
 *
 * ─── Derecelendirme neden IKI anahtarli ───────────────────────────────────
 *
 * Bir maci iyi BANKO yapan sey ile iyi CIFTE yapan sey ayni sayi degil.
 * Kacak aritmetigi (`spor_toto/secim.py`) bunu tam soyluyor:
 *
 *     banko isaretlenirse kacar mi   q = 1 − p₁
 *     cifte isaretlenirse kacar mi   q = p₃
 *     uclu isaretlenirse kacar mi    q = 0        ← uclu ASLA kacmaz
 *
 * Yani banko sirasi `p₁`e (buyukten kucuge), cifte sirasi `p₃`e (kucukten
 * buyuge) bakar. Tek bir anahtarla siralamak akla yatkin gorunur ve
 * yanlistir: `p₁ = 0,45 · p₃ = 0,05` olan bir mac kotu bankodur ama
 * MUKEMMEL ciftedir, tek anahtarli sirada ise ikisinde de ortada kalirdi.
 *
 * Sira bu yuzden iki asamali kuruluyor ve sahibinin cumlesi de zaten oyle
 * okunuyor: once "en fazla tek"ler ayrilir, KALANLAR icinde "en cok
 * cifte"den "en cok uclu"ye dogru siralanir.
 *
 * ─── Ciftede hangi iki sembol ─────────────────────────────────────────────
 *
 * *"Ciftlilerde en mantikli secenekler secilecek."* Kural `kupon-kur`daki
 * kuralin AYNISI ve ayni koddan geliyor (`satirOkumasi` + `okumadanIsaret`):
 * karnenin en yuksek iki sembolu, esitlikte piyasa, o da esitse sembol
 * duzeni. Iki modul ayni siradan okuyor; ayrisirlarsa ayni karne iki farkli
 * isaret uretirdi.
 *
 * ─── Karnesi olmayan satir ────────────────────────────────────────────────
 *
 * Derecelendirilemez, cunku hangi seviyenin ona uygun oldugunu soyleyecek
 * sayi yok. Sirada EN SONA konur, yani once uclu yapilir — ve bu bir kacamak
 * degil, dogru cevap: uclu hicbir bilgi gerektirmez (uc sembol de isaretli,
 * kacak sifir). Uclu kontenjani dolmussa o satir `eksik` sayilir ve kupon
 * kurulamaz; uydurulmus bir banko yazilmaz.
 */

/** Bir kuponun sekli: kac banko, kac cifte, kac uclu. */
export interface Sekil {
  /** Kalici anahtar — arsiv kaydina bu yazilir, ad degil. */
  anahtar: string;
  ad: string;
  banko: number;
  cift: number;
  uclu: number;
}

/**
 * Sahibinin istedigi iki sekil. Liste SABIT: sayilar sahibinin karari ve
 * arayuzden degistirilmiyor.
 */
export const SEKILLER: readonly Sekil[] = [
  { anahtar: "b6u9", ad: "6 banko · 9 üçlü", banko: 6, cift: 0, uclu: 9 },
  { anahtar: "b5c5u5", ad: "5 banko · 5 çift · 5 üçlü", banko: 5, cift: 5, uclu: 5 },
] as const;

/**
 * Kac kacaga kadar hedefe ulasilmis sayilir.
 *
 * `spor_toto.secim.VARSAYILAN_KACAK_ESIGI` ile AYNI sayi ve ayni gerekce:
 * duz sistemde `en iyi kolon = 15 − k`, yani `k ≤ 3` demek "en az 12" demek.
 * Urunun hedef kademesi 12'dir; 15 bir yan urundur.
 */
export const HEDEF_KACAK = 3;

/** Bir satirin sekilli kupondaki hali. */
export interface SekilliSatir extends SatirIsareti {
  /** Kac sembol isaretlendi: 1 banko, 2 cifte, 3 uclu. */
  seviye: 1 | 2 | 3;
  /** Derecelendirmedeki sirasi — 1 "en fazla tek", 15 "en cok uclu". */
  derece: number;
  /** Bu seviyede macin kacma olasiligi. Karne okunamiyorsa `null`. */
  kacak: number | null;
}

export interface SekilliKupon {
  sekil: Sekil;
  satirlar: SekilliSatir[];
  /** Isaretlerin carpimi — `2^cift · 3^uclu`. Sekil sabit, kolon da sabit. */
  kolon: number;
  piyasadanSecilen: number[];
  azOrnekli: number[];
  esitlikli: number[];
  /** Isaret uretilemeyen satirlar — kupon EKSIK demektir. */
  eksik: number[];
  /**
   * `dagilim[k]` = tam `k` macin kactigi olasilik. Hepsi karneden okunur.
   * Karnesi okunamayan satir varsa `null`: olasilik UYDURULMAZ.
   */
  dagilim: number[] | null;
  /** `P(kacak = 0)` — kuponun 15/15 tutturma olasiligi. `null` olabilir. */
  p15: number | null;
  /** `P(kacak ≤ 3)` = `P(en iyi kolon ≥ 12)`. `null` olabilir. */
  pHedef: number | null;
}

/** Bir satirin normallesmis `p₁ ≥ p₂ ≥ p₃`si. Veri yoksa `null`. */
function olasiliklar(okuma: SatirOkumasi): [number, number, number] | null {
  if (okuma.kaynak === "yok") return null;
  const ham = okuma.sirali.map((x) => Math.max(0, okuma.agirlik(x)));
  if (ham.length < 3) return null;
  const toplam = ham.reduce((a, b) => a + b, 0);
  // Karne yuzdeleri 1'e toplanir (her mac 1/0/2 ile biter); piyasa
  // olasiliklari MARJ tasir ve toplamlari 1'i asar. Normallestirme ikisini
  // ayni olceye getirir — kacak aritmetigi olasilik bekliyor, oran degil.
  if (!(toplam > 0)) return null;
  return [ham[0]! / toplam, ham[1]! / toplam, ham[2]! / toplam];
}

/**
 * Bagimsiz kacaklarin dagilimi — Poisson-binom evrisimi.
 *
 * `spor_toto.ortak.kacak_dagilimi` ile ayni hesap. Bagimsizlik bir
 * VARSAYIMDIR ve depoda olculmus bir kusuru var (hafta ici bagimlilik,
 * §3.46); burada sayinin yaninda "karneye gore" yaziyor, kesin bir vaat
 * olarak degil bir SIRALAMA olcutu olarak okunuyor.
 */
export function kacakDagilimi(qlar: number[]): number[] {
  let dagilim = [1];
  for (const q of qlar) {
    const yeni = new Array<number>(dagilim.length + 1).fill(0);
    dagilim.forEach((p, k) => {
      yeni[k] = (yeni[k] ?? 0) + p * (1 - q);
      yeni[k + 1] = (yeni[k + 1] ?? 0) + p * q;
    });
    dagilim = yeni;
  }
  return dagilim;
}

/** Satirin seviyesine gore kacak olasiligi. */
function kacakOlasiligi(p: [number, number, number] | null, seviye: 1 | 2 | 3): number | null {
  if (!p) return null;
  if (seviye === 3) return 0;
  if (seviye === 2) return Math.max(0, p[2]);
  return Math.max(0, 1 - p[0]);
}

/**
 * 15 satiri sekle gore derecelendirip isaretler.
 *
 * Girdi, ekrandaki analizin KENDISI — `kupon-kur` ile ayni girdi, ayni
 * okuma. Degisen tek sey derinligin nasil dagitildigi.
 */
export function sekilliKuponKur(sonuclar: SatirAnalizi[], sekil: Sekil): SekilliKupon {
  const okumalar = Array.from({ length: MAC_SAYISI }, (_, i) => satirOkumasi(sonuclar[i]));
  const plar: ([number, number, number] | null)[] = okumalar.map(olasiliklar);
  const pAl = (i: number) => plar[i] ?? null;

  // ── 1. asama: "en fazla tek" — banko sirasi `p₁`e gore ────────────────
  //
  // Veri yoksa `-1`: butun gercek olasiliklarin altinda kalir, yani karnesi
  // olmayan satir asla banko secilmez (baska secenek kalmadikca).
  const bankoAnahtari = (i: number) => pAl(i)?.[0] ?? -1;
  // ── 2. asama: "en cok cifteden en cok ucluye" — `p₃`e gore ────────────
  //
  // Veri yoksa `2`: butun gercek olasiliklarin ustunde, yani sirada en sona
  // duser ve uclu kontenjanina gider.
  const cifteAnahtari = (i: number) => pAl(i)?.[2] ?? 2;

  const hepsi = Array.from({ length: MAC_SAYISI }, (_, i) => i);
  const bankoSirasi = [...hepsi].sort(
    (a, b) =>
      bankoAnahtari(b) - bankoAnahtari(a) ||
      // Esit `p₁`de daha iyi cifte olan one gecer; o da esitse mac sirasi.
      // Rastgelelik YOK: ayni karne hep ayni kuponu vermeli.
      cifteAnahtari(a) - cifteAnahtari(b) ||
      a - b,
  );
  const bankolar = bankoSirasi.slice(0, sekil.banko);
  const kalan = bankoSirasi.slice(sekil.banko).sort(
    (a, b) =>
      cifteAnahtari(a) - cifteAnahtari(b) ||
      bankoAnahtari(b) - bankoAnahtari(a) ||
      a - b,
  );
  const cifteler = kalan.slice(0, sekil.cift);

  const seviyeler = new Map<number, 1 | 2 | 3>();
  bankolar.forEach((i) => seviyeler.set(i, 1));
  cifteler.forEach((i) => seviyeler.set(i, 2));

  // Derece = ekranda gosterilen sira: once bankolar (kendi sirasiyla),
  // sonra cifteler, sonra ucluler. "1" en fazla tek, "15" en cok uclu.
  const derecesi = new Map<number, number>();
  [...bankolar, ...kalan].forEach((i, sira) => derecesi.set(i, sira + 1));

  const satirlar: SekilliSatir[] = okumalar.map((okuma, i) => {
    const seviye = seviyeler.get(i) ?? 3;
    const isaret = okumadanIsaret(okuma, seviye);
    return {
      ...isaret,
      seviye,
      derece: derecesi.get(i) ?? i + 1,
      kacak: kacakOlasiligi(pAl(i), seviye),
    };
  });

  const piyasadanSecilen: number[] = [];
  const azOrnekli: number[] = [];
  const esitlikli: number[] = [];
  const eksik: number[] = [];
  let kolon = 1;

  satirlar.forEach((s, i) => {
    if (s.kaynak === "piyasa") piyasadanSecilen.push(i);
    if (s.kaynak === "yok") eksik.push(i);
    if (s.azOrnek) azOrnekli.push(i);
    // Esitlik yalnizca SINIRDA anlamli; uclude sinir yok (hepsi isaretli).
    if (s.esitlikBozuldu && s.seviye < 3) esitlikli.push(i);
    kolon *= Math.max(1, s.semboller.length);
  });

  // Olasilik ancak HER satirin kacagi okunabiliyorsa hesaplanir. Bir satir
  // karnesizse "0 kacak" varsaymak kuponu oldugundan iyi gosterirdi.
  const qlar = satirlar.map((s) => s.kacak);
  const tam = qlar.every((q) => q != null);
  const dagilim = tam ? kacakDagilimi(qlar as number[]) : null;

  return {
    sekil,
    satirlar,
    kolon,
    piyasadanSecilen,
    azOrnekli,
    esitlikli,
    eksik,
    dagilim,
    p15: dagilim ? (dagilim[0] ?? 0) : null,
    pHedef: dagilim
      ? dagilim.slice(0, HEDEF_KACAK + 1).reduce((a, b) => a + b, 0)
      : null,
  };
}

/** Seklin kolon sayisi — isaret kurulmadan da bilinir (`2^cift · 3^uclu`). */
export function sekilKolonu(sekil: Sekil): number {
  return 2 ** sekil.cift * 3 ** sekil.uclu;
}
