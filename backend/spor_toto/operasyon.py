"""Operasyon — planı **yatırmanın** bedeli.

Bu depo şimdiye kadar iki şeyi ölçtü: planın ne kadar iyi olduğunu
(`coklu.py`) ve o iyiliğin hedefte ne ettiğini (`ufuk.py`). İkisi de
**kâğıt üstündeki** planın sayılarıdır. Arada ölçülmemiş bir adım duruyor:
81 kupon bir insan tarafından, bir terminalin başında, elle giriliyor.

§3.71'den beri açık duran soru şuydu: *"81–729 kupon bir haftada fiilen
yatırılabiliyor mu?"* §3.73 onun **yarısını** fiyatladı — 81'de takılmanın
bedeli hedefte 1,8 puandır. Fiyatlanmayan yarısı sorunun içindeki
"**güvenle**" kelimesiydi: yatırabiliyor olmak yetmez, *doğru* yatırmak
gerekir ve insan yanlış yatırır.

─── Niçin ayrı bir modül ─────────────────────────────────────────────────

Çünkü `coklu.p_onbes` **oynanan** kuponu puanlayamaz. Gövdesi kuponların
ayrık olduğunu varsayar ve olasılıkları toplar:

    P(15/15) = Σ_j p_j        (yalnızca kuponlar ayrıkken doğru)

Planın kuponları ayrıktır — ayrıklık eksen bileşimlerinin **birbirinden
farklı** olmasından gelir ve arama bunu kurar. Ama insanın girdiği kupon
kümesi plan değildir: bir kupon iki kez girilirse, ya da bir işaret yanlış
işaretlenirse, ayrıklık bozulur ve o toplam **fazla sayar**. Yani tam da
denetim istediğiniz durumda sayı yalan söyler, üstelik iyimser yönde.

`birlesim_p_onbes` bu yüzden var: kolonları tek tek sayar, ayrıklığı
varsaymaz. Yavaştır (haftada ~0,1 sn, 21.000 kolon) ve öyle olmalıdır —
haftada bir kez, girilen kuponu doğrulamak için koşar.

─── Yanlış girmenin beş yolu ─────────────────────────────────────────────

Elle giriş bozulduğunda bozulma keyfî değildir; bir kalem darbesi kadardır:

* **atlama** — kupon hiç girilmez. Para da harcanmaz.
* **kopya** — bir kupon iki kez girilir, başka biri girilmez. Para harcanır.
* **eksik** — bir maçta bir işaret unutulur. Kupon ucuzlar, kapsama daralır.
* **fazla** — bir maçta fazladan bir işaret konur. Kupon **pahalanır**.
* **takas** — yanlış kutu işaretlenir. Bedel aynı, kapsama başka yere gider.

`slipler` bu ailenin tamamını gezer ve her birinin `P(15/15)` kaybını
**kesin** hesaplar (kapalı form; bekçisi `birlesim_p_onbes`e karşı).

─── Okuma kuralı — ölçüm görülmeden yazıldı ──────────────────────────────

Kaybın işareti modlara göre **aynı olmak zorunda değil** ve bu bir kusur
değil:

1. **`fazla` muhtemelen `P`yi YÜKSELTİR.** Fazladan işaret kapsamayı
   genişletir; bedeli parada ödenir, olasılıkta değil. O modda okunacak
   sayı `P` kaybı değil **bütçe aşımıdır**, ve aşım gerçektir: plan
   bütçenin neredeyse tamamını kullanıyor, yani fazla işaret doğrudan
   cebe yazılır.
2. **`kopya` ile `atlama`nın `P` kaybı AYNI çıkmalıdır.** İkisinde de
   kaybedilen tam olarak girilmeyen kuponun kendisidir; kopyanın eklediği
   kutu zaten kümededir. Ayrışırlarsa gövdede hata vardır — bekçisi
   `test_kopya_kaybi_atlama_kaybiyla_AYNI`.
3. **Asıl sınav büyüklük değil, KARŞILAŞTIRMA.** Tek bir slipin kaç puan
   ettiği tek başına bir şey söylemez. Söyleyen şey şudur: **hangi hata
   oranında 729 kupon 81 kupondan kötü olur?** 729'un kazancı hedefte
   1,8 puandır ve 729 kupon dokuz kat daha çok giriş demektir, yani dokuz
   kat daha çok slip. O eşiğin altında operasyon bağlayıcı kısıt değildir;
   üstünde, kupon sayısını artırmak **zarar**dır.
"""
from __future__ import annotations

import itertools
from collections.abc import Iterator, Sequence
from typing import NamedTuple

from .coklu import _INDEKS, MAC_SAYISI, Kupon, _matris
from .core import SEMBOLLER

#: Slip türleri, elle girişte gerçekten olan şeyler. Sıra rapor sırasıdır.
SLIP_TURLERI = ("atlama", "kopya", "eksik", "fazla", "takas")


class Slip(NamedTuple):
    """Tek bir elle giriş hatası ve ölçülmüş bedeli.

    `p_kayip` **kayıptır**: pozitifse plan kötüleşmiştir, negatifse hata
    `P`yi yükseltmiştir (bkz. `fazla`). `kolon_fark` girilen kolon
    sayısının plandan farkıdır ve para budur — pozitifse bütçe aşılmıştır.

    Tek istisna `kopya`: orada fark hangi kuponun kopyalandığına bağlıdır ve
    alan **en kötü hâli** taşır (en pahalı kupon kopyalandı).
    """

    tur: str
    kupon: int
    konum: int | None
    eski: str
    yeni: str
    p_kayip: float
    kolon_fark: int


def _setler(kuponlar: Sequence[Kupon]) -> list[list[set[str]]]:
    """Kuponların seçimleri, konum başına küme olarak."""
    return [[set(s) for s in k.secimler] for k in kuponlar]


def _kutu_olculeri(P, setler: list[list[set[str]]]
                   ) -> tuple[list[float], list[int]]:
    """Her kuponun olasılığı ve kolon sayısı — ikisi de çarpımdır.

    İki gövde bunu istiyor (`slipler` ve `yogunlasma`); iki kopya olsaydı
    biri sessizce eskirdi.
    """
    plar: list[float] = []
    kolonlar: list[int] = []
    for S in setler:
        p, kolon = 1.0, 1
        for i, sec in enumerate(S):
            p *= sum(P[i][_INDEKS[s]] for s in sec)
            kolon *= len(sec)
        plar.append(p)
        kolonlar.append(kolon)
    return plar, kolonlar


def kupon_olasiliklari(probs_listesi: list[dict[str, float]],
                       kuponlar: Sequence[Kupon]) -> list[float]:
    """Her kuponun `P(15/15)`e katkısı — kupon sırasında.

    Kuponlar ayrıkken bunların toplamı `coklu.p_onbes`tir. Ayrık değilken
    toplam fazla sayar (`birlesim_p_onbes`in var olma sebebi), ama tek tek
    değerler yine de her kuponun **kendi** ağırlığıdır ve sıralama için
    doğru olan budur.
    """
    P = _matris(probs_listesi)
    return _kutu_olculeri(P, _setler(kuponlar))[0]


class Yogunlasma(NamedTuple):
    """Planın `P(15/15)`i kaç kupona yığılmış."""

    kupon: int
    en_buyuk_pay: float
    yarisini_tasiyan: int
    duz_pay: float


def yogunlasma(probs_listesi: list[dict[str, float]],
               kuponlar: Sequence[Kupon]) -> Yogunlasma:
    """Hedefin kaç kupona yığıldığı — **denetim sırasının** dayanağı.

    Bütün kuponlar eşit değerde olsaydı her biri `1/M` taşırdı ve hangi
    kuponu yanlış girdiğiniz fark etmezdi. Ölçülen şey bunun tersi: eksen
    bileşimlerinin olasılıkları yüzler kat ayrışıyor (`coklu.py` başlığı),
    yani **bir kuponu yanlış girmek ötekinden çok daha pahalı**.

    `yarisini_tasiyan`, planın `P(15/15)`inin yarısını taşıyan en küçük
    kupon sayısıdır. Elle giriş iki kez denetlenecekse denetlenecek küme
    budur; sıra, kuponları olasılığa göre azalan dizmektir.
    """
    plar = kupon_olasiliklari(probs_listesi, kuponlar)
    toplam = sum(plar)
    if not plar or toplam <= 0.0:
        return Yogunlasma(len(plar), 0.0, 0, 0.0)
    sirali = sorted(plar, reverse=True)
    birikim, yari = 0.0, 0
    for p in sirali:
        birikim += p
        yari += 1
        if birikim >= toplam / 2.0:
            break
    return Yogunlasma(len(plar), sirali[0] / toplam, yari, 1.0 / len(plar))


def birlesim_p_onbes(probs_listesi: list[dict[str, float]],
                     kuponlar: Sequence[Kupon]) -> float:
    """`P(15/15)` — kuponlar **ayrık olmasa da** doğru.

    `coklu.p_onbes` olasılıkları toplar ve bu yalnızca kuponlar ayrıkken
    doğrudur. Bu gövde kolonları tek tek sayar, yani aynı kolon iki kuponda
    geçse de bir kez sayılır. Oynanan kuponu denetlemenin tek doğru yolu
    budur: insanın girdiği kümenin ayrık olduğu **bilinmez**.

    Bedeli kolon sayısıyla doğrusaldır (21.000 kolonda ~0,1 sn); haftada
    bir kez koşacak bir gövde için bu ucuzdur ve kesinlik pahalı olanı
    yazmaya değer.
    """
    P = _matris(probs_listesi)
    gorulen: dict[tuple[str, ...], float] = {}
    for k in kuponlar:
        for kolon in itertools.product(*k.secimler):
            if kolon in gorulen:
                continue
            p = 1.0
            for i, s in enumerate(kolon):
                p *= P[i][_INDEKS[s]]
            gorulen[kolon] = p
    return float(sum(gorulen.values()))


def ayrik_mi(kuponlar: Sequence[Kupon]) -> bool:
    """Kuponlar ikişer ikişer ayrık mı — yani `coklu.p_onbes` güvenilir mi?

    İki kutu, **bir tek** konumda sembol kümeleri kesişmiyorsa ayrıktır.
    Plan bunu eksen bileşimlerinin farklılığından alır; oynanan kupon
    kümesinde ise sınanması gerekir.
    """
    setler = _setler(kuponlar)
    for a, b in itertools.combinations(setler, 2):
        if all(a[i] & b[i] for i in range(MAC_SAYISI)):
            return False
    return True


def _kesisim(P, a: Sequence[set[str]], b: Sequence[set[str]]) -> float:
    """İki kutunun kesişiminin olasılığı; kesişmiyorlarsa 0."""
    p = 1.0
    for i in range(MAC_SAYISI):
        ortak = a[i] & b[i]
        if not ortak:
            return 0.0
        p *= sum(P[i][_INDEKS[s]] for s in ortak)
    return p


def _tekil_tanik(setler: list[list[set[str]]]) -> list[dict[int, list[int]]]:
    """`j` kuponunun, ayrıklığı **yalnızca** `i` konumuna dayanan komşuları.

    Niçin gerekli: bir slip tek bir konumu değiştirir. `j` ile `m` iki ayrı
    konumda da ayrıksa, `i`deki değişiklik ayrıklığı bozamaz. Yani örtüşme
    ancak `j`–`m` çiftinin **tek tanığı** `i` iken doğabilir. Bu tabloyu
    hafta başına bir kez kurmak, slip başına 80 kutu kesişimi hesaplamaya
    göre iki mertebe ucuzdur.

    Tarama **ikinci tanığı görünce durur**: iki tanıklı bir çift zaten
    hiçbir tek slipte örtüşemez, kaçıncı konumlarda ayrıldığı ilgisizdir.
    729 kuponda çift sayısı yarım milyonu geçiyor ve erken çıkış bu gövdeyi
    ölçümün darboğazı olmaktan çıkarıyor.
    """
    M = len(setler)
    out: list[dict[int, list[int]]] = [{} for _ in range(M)]
    for j in range(M):
        Sj = setler[j]
        for m in range(M):
            if m == j:
                continue
            tanik = -1
            for i in range(MAC_SAYISI):
                if not Sj[i] & setler[m][i]:
                    if tanik >= 0:
                        tanik = -1
                        break
                    tanik = i
            if tanik >= 0:
                out[j].setdefault(tanik, []).append(m)
    return out


def _tek_darbe(mevcut: set[str]) -> Iterator[tuple[str, set[str]]]:
    """Bir kalem darbesiyle ulaşılabilen seçim kümeleri ve slip türü.

    "Bir darbe" tanımı: bir sembol eklemek (`fazla`), bir sembol silmek
    (`eksik`) ya da bir sembolü bir başkasıyla değiştirmek (`takas`).
    İkiden çok sembolü aynı anda oynatan bozulmalar bu ailede **yoktur**;
    olsalardı "tek hata" sayımı anlamını yitirirdi.
    """
    for s in SEMBOLLER:
        if s not in mevcut:
            yield "fazla", mevcut | {s}
    if len(mevcut) > 1:
        for s in mevcut:
            yield "eksik", mevcut - {s}
    for eski in mevcut:
        for yeni in SEMBOLLER:
            if yeni not in mevcut:
                yield "takas", (mevcut - {eski}) | {yeni}


def slipler(probs_listesi: list[dict[str, float]],
            kuponlar: Sequence[Kupon]) -> list[Slip]:
    """Tek hatalı girişlerin **tamamı** ve her birinin ölçülmüş bedeli.

    Kayıplar kapalı formdur ve **kesindir** — örtüşme dâhil. Gerekçe: kutu
    olasılığı çarpımdır, yani tek bir konumu değiştirmek `p_j`yi bir orana
    çarpar; kalan kuponlar kendi aralarında ayrık olduğu için birleşimin
    olasılığı `Σ_{k≠j} p_k + p_j' − Σ_{k≠j} P(j' ∩ k)` olur ve içerme–
    dışarma bu terimde **durur**. Bekçisi `birlesim_p_onbes`e karşı
    koşuyor: iki gövde ayrışırsa kapalı form yanlıştır.

    `kopya` ailesi `j`den bağımsızdır — kopyanın eklediği kutu kümede zaten
    vardır, kaybedilen yalnızca girilmeyen kupondur. O yüzden tür başına
    `M` kayıt tutulur, `M²` değil.
    """
    P = _matris(probs_listesi)
    setler = _setler(kuponlar)
    M = len(kuponlar)
    plar, kolonlar = _kutu_olculeri(P, setler)
    en_pahali = max(kolonlar, default=0)
    tanik = _tekil_tanik(setler)

    out: list[Slip] = []
    for j in range(M):
        # Kupon hiç girilmedi: kaybedilen kendisi, harcanmayan da bedeli.
        out.append(Slip("atlama", j, None, "", "", plar[j], -kolonlar[j]))
        # `j` girilmedi, yerine başka bir kuponun kopyası girildi. `P` kaybı
        # `atlama`yla AYNIdır (kopyanın eklediği kutu kümede zaten var) ama
        # para HARCANDI — `atlama`dan ayıran şey budur.
        #
        # Kolon farkı `kolon[kopyalanan] − kolon[j]`dir, yani hangi kuponun
        # kopyalandığına bağlı ve ailede `M²` kayıt gerektirirdi. Burada
        # **en kötü hâli** yazılıyor (en pahalı kupon kopyalandı), çünkü bu
        # bir risk ölçüsüdür ve kuponlar eşit bedelli DEĞİL: §3.71'den beri
        # her kupon kendi alt sistem bütçesini alıyor ve ölçülen 52 planın
        # 52'sinde kupon bedelleri ayrışıyor.
        out.append(Slip("kopya", j, None, "", "",
                        plar[j], en_pahali - kolonlar[j]))
        w = [sum(P[i][_INDEKS[s]] for s in setler[j][i]) for i in range(MAC_SAYISI)]
        for i in range(MAC_SAYISI):
            mevcut = setler[j][i]
            for tur, yeni in _tek_darbe(mevcut):
                p_yeni = plar[j] / w[i] * sum(P[i][_INDEKS[s]] for s in yeni)
                ust = 0.0
                if yeni - mevcut:  # kutu BÜYÜYOR; ancak o zaman örtüşebilir
                    bozuk = list(setler[j])
                    bozuk[i] = yeni
                    for m in tanik[j].get(i, ()):
                        ust += _kesisim(P, bozuk, setler[m])
                kolon_fark = kolonlar[j] // len(mevcut) * len(yeni) - kolonlar[j]
                out.append(Slip(tur, j, i, "".join(sorted(mevcut)),
                                "".join(sorted(yeni)),
                                plar[j] - p_yeni + ust, kolon_fark))
    return out


class SlipOzeti(NamedTuple):
    """Bir slip türünün bir haftadaki bedeli."""

    tur: str
    sayi: int
    ortalama: float
    en_kotu: float
    en_kotu_kolon: int


def slip_ozeti(probs_listesi: list[dict[str, float]],
               kuponlar: Sequence[Kupon]) -> dict[str, SlipOzeti]:
    """Slip türü başına `(adet, ortalama kayıp, en kötü kayıp)`.

    Ortalama, o türün **bütün** tek hatalı girişleri üzerinden düz
    ortalamadır: yani "hata olduysa hangi hata olduğu belli değil"
    okuması. Bu bir varsayımdır ve açıkça yapılmıştır — gerçek insan
    hatası düz dağılmaz, ama yönünü bilmediğimiz bir ağırlığı uydurmak
    ölçümü kötüleştirirdi.
    """
    gruplar: dict[str, list[Slip]] = {t: [] for t in SLIP_TURLERI}
    for s in slipler(probs_listesi, kuponlar):
        gruplar[s.tur].append(s)
    out: dict[str, SlipOzeti] = {}
    for tur, grup in gruplar.items():
        if not grup:
            continue
        en = max(grup, key=lambda s: s.p_kayip)
        out[tur] = SlipOzeti(tur, len(grup),
                             sum(s.p_kayip for s in grup) / len(grup),
                             en.p_kayip,
                             max(s.kolon_fark for s in grup))
    return out


def hedef_duyarliligi(p_haftalik: Sequence[float]) -> float:
    """Haftalık `P`de 1 birimlik kaybın **hedefte** kaç birim ettiği.

    Hedef `1 − Π_w (1 − p_w)` olduğu için tek bir haftanın türevi
    `Π_{k≠w} (1 − p_k)`dır ve haftalar farklı `p`lere sahip olduğu için
    bu türev de haftadan haftaya değişir. Aşağıdaki sayı pencere boyunca
    **ortalamasıdır** ve küçük kayıplar için geçerli olan doğrusal
    yaklaşıklıktır — slip bedelleri haftalık `P`nin yüzdeleri
    mertebesinde olduğu sürece bu yaklaşıklık gürültünün altındadır.

    >>> round(hedef_duyarliligi([0.1] * 2), 6)
    0.9
    """
    if not p_haftalik:
        return 0.0
    kalan = 1.0
    for p in p_haftalik:
        kalan *= 1.0 - p
    return sum(kalan / (1.0 - p) for p in p_haftalik) / len(p_haftalik)


def kritik_hata_orani(fark_puan: float, duyarlilik: float, hafta: int,
                      kupon_farki: int, slip_bedeli: float) -> float:
    """Kupon sayısını artırmanın **zarara** döndüğü hata oranı.

    Daha çok kupon hedefte `fark_puan` kazandırır ama `kupon_farki` kadar
    fazla giriş demektir, yani o kadar fazla slip. Kupon başına hata
    oranı `r` iken beklenen ek kayıp haftada `kupon_farki · r ·
    slip_bedeli`dir; `hafta` hafta boyunca hedefte `hafta · duyarlilik`
    ile çarpılır. İkisi eşitlendiğinde:

        r* = fark_puan / (hafta · duyarlilik · kupon_farki · slip_bedeli)

    `r*`ın üstünde fazladan kupon **zarardır**. Payda sıfırsa eşik yoktur
    (`inf`): ya fazladan giriş yoktur ya da slipin bedeli sıfırdır.

    >>> round(kritik_hata_orani(0.018, 0.237, 13, 648, 0.00085), 4)
    0.0106
    """
    payda = hafta * duyarlilik * kupon_farki * slip_bedeli
    if payda <= 0.0:
        return float("inf")
    return fark_puan / payda
