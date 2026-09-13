"""Çoklu kupon — tek sistemin çarpım kısıtını kaldırır.

`secim.py` bir hafta için **tek** bir tam sistem kurar: her maça 1/2/3
sembol, kupon bunların Kartezyen çarpımı, bedel `2^a·3^b`. Bu modül aynı
bütçeyi **birden çok kupona** böler ve ölçülen kazanç büyüktür.

─── Neden çarpım bir kısıt ───────────────────────────────────────────────

`N` kolonluk en iyi küme, tanım gereği olasılığa göre en büyük `N` kolondur.
O küme genel olarak bir **kutu değildir**. Çarpım kümesi, kutunun köşelerini
(tüm belirsiz maçların aynı anda ters gitmesi) satın almak zorunda kalırken
kutunun dışında kalan daha olası kolonları (tek bir bankonun dönmesi)
alamaz. Ölçülen bedel, 114 tam haftada, `3⁹ = 19.683` kolonda:

    tek sistem (çarpım)        P(15/15) = %7,489    gerçekleşen 15/114
    serbest (en büyük N kolon) P(15/15) = %10,865   gerçekleşen 22/114

Aynı para, aynı olasılık modeli, **×1,45**. Fark yalnızca kümenin şekli.

─── Neden bu modül, serbest liste değil ──────────────────────────────────

Serbest kümeyi birebir oynamak ~4.300 ayrı kupon ister (ölçüldü: 20 haftada
medyan 4.290 kutu, birleştirme sonrası). Bedel aynıdır ama operasyon ağır.
Bu modül araya giren aileyi kurar ve kazancın çoğu birkaç düzine kuponda
zaten alınır:

    kupon    model P(15/15)    gerçekleşen    13 hafta
        1          %7,489         15/114        %63,6   ← tek sistem
       27          %9,353         20/114        %72,1
       81          %9,862         21/114        %74,1
      729         %10,461         22/114        %76,2
   19.683         %10,865         22/114        %77,6   ← serbest

Yapı: `d` maç **eksen** seçilir — en emin olduklarımız — ve kuponlar arasında
tek tek sabitlenir; eksen üzerindeki `3^d` bileşimden en olası `M` tanesi
oynanır. Kalan `15−d` maç her kuponda **aynı alt sistemdir** ve onu
`secim.en_iyi_secim` kendi bütçesiyle (`bütçe // M`) çözer.

`M = 1` tam olarak bugünkü tek sistemdir. Yani bu modül mevcut davranışı
**içerir** ve arama onu bir aday olarak gezer; `M`i büyütmek genelleştirir.

─── Yan fayda: bütçe merdiveni kalkıyor ──────────────────────────────────

Tek sistemde bedel `2^a·3^b` olduğu için bütçe **basamaklıdır**: 19.683 ile
21.000 kolon *aynı* kuponu alır, aradaki 13.170 TL hiçbir şey satın almaz.
Çoklu kuponda bedel `M · 3^(15−d)`'dir ve `M` serbest tamsayıdır, yani her
bütçe kullanılabilir.

─── Sınır ────────────────────────────────────────────────────────────────

Buradaki olasılıklar maçlar arası **bağımsızlık** varsayar; `kuyruk.py`
hafta içi bağımlılığı ölçtü ve korpus üst sınırında kuyruk %5 şişiyor. Bu
her iki şekli de aynı yönde etkiler, oran görece dayanıklıdır — ama
`P(15/15)`'in mutlak değeri bu varsayıma bağlıdır ve öyle okunmalıdır.

Bu modül **yalnızca 15/15'i** enbüyükler. Alt kademeler (12–13) paranın
çoğunu taşır ve çoklu kupon onları tek sistem kadar tutturmaz; ölçümü
`kademe_dagilimi` ile alınır. Ürün kararı bilerek 15'tir.
"""
from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np

from .core import SEMBOLLER, sirala_semboller

#: Kupondaki maç sayısı.
MAC_SAYISI = 15

#: Varsayılan kupon tavanı. Ölçülen eğride kazancın büyük kısmı ilk birkaç
#: düzine kuponda alınıyor; tavan bir **operasyon** kararıdır, matematiksel
#: bir sınır değil. `None` verilirse arama `ARANAN_KUPON`un tamamını gezer.
VARSAYILAN_KUPON_TAVANI = 81


class Kupon(NamedTuple):
    """Tek bir oynanabilir kupon: her maç için işaretlenen semboller."""

    secimler: list[list[str]]
    kolon: int

    @property
    def picks(self) -> list[str]:
        return ["".join(sirala_semboller(s)) for s in self.secimler]


class CokluPlan(NamedTuple):
    """Bir haftanın çoklu kupon planı ve ölçülmüş hedefi."""

    kuponlar: list[Kupon]
    eksen: list[int]
    kolon: int
    p_onbes: float

    @property
    def kupon_sayisi(self) -> int:
        return len(self.kuponlar)


def _matris(probs_listesi: list[dict[str, float]]) -> np.ndarray:
    """Olasılıkları satır başına büyükten küçüğe sıralı matrise çevirir."""
    p = np.array([[d.get(s, 0.0) for s in SEMBOLLER] for d in probs_listesi],
                 dtype=float)
    toplam = p.sum(axis=1, keepdims=True)
    if np.any(toplam <= 0):
        raise ValueError("Bir macin olasilik toplami sifir.")
    return p / toplam


def eksen_sec(probs_listesi: list[dict[str, float]], d: int) -> list[int]:
    """Eksen maçları: en emin `d` maç (favori olasılığı en büyük).

    Eksen **kısıtlanan** taraftır — o maçlarda bütün bileşimleri değil
    yalnızca en olası `M` tanesini oynarız. Kısıtlamayı en emin olduğumuz
    yerde yapmak doğrudur: emin olmadığımız maç üçlü kalır ve hiç kaçmaz.
    """
    if not 0 <= d <= MAC_SAYISI:
        raise ValueError(f"Eksen sayisi 0..{MAC_SAYISI} araliginda olmali.")
    P = _matris(probs_listesi)
    # Favorinin olasılığı — `P[:, 0]` DEĞİL. `_matris` ham sembol düzeninde
    # (`1/0/2`) döner, yani ilk sütun ev sahibidir, favori değil.
    return sorted(np.argsort(-P.max(axis=1))[:d].tolist())


#: Aranan kupon sayıları. Her `M` için kupon başına bütçe `bütçe // M`
#: olur ve alt sistem o bütçeyle **ayrıca** çözülür. Izgara üçün kuvvetleri
#: etrafındadır çünkü eksen bileşim sayısı `3^d`'dir; aradaki değerler
#: kupon başına bütçeyi kırpmaktan başka bir şey yapmaz.
ARANAN_KUPON = (1, 3, 9, 27, 81, 243, 729, 2187)


def _eksen_bilesimleri(P: np.ndarray, eksen: list[int], M: int):
    """Eksen üzerindeki en olası `M` bileşim: (indeksler, toplam olasılık)."""
    v = np.array([1.0])
    for i in eksen:
        v = np.multiply.outer(v, P[i]).ravel()
    if M >= v.size:
        sec = np.arange(v.size)
    else:
        sec = np.argpartition(v, -M)[-M:]
    sec = sec[np.argsort(-v[sec])]          # en olasıdan başlayarak
    return sec, float(v[sec].sum())


def coklu_plan(probs_listesi: list[dict[str, float]],
               butce: int,
               kupon_tavani: int | None = None) -> CokluPlan:
    """Bütçe içinde `P(15/15)`'i enbüyükleyen çoklu kupon planı.

    `butce` kolon cinsindendir ve zorunludur — `secim.en_iyi_secim` ile aynı
    sebeple: tavansız aramanın cevabı dejenere (`3¹⁵` kolon, `P = 1`).

    Plan iki parçadır:

    * **eksen** — `d` maç, kuponlar arasında tek tek sabitlenir. Eksen
      üzerindeki `3^d` bileşimden en olası `M` tanesi oynanır, her biri bir
      kupon.
    * **alt sistem** — kalan `15−d` maç, her kuponda **aynı**, ve bütçesi
      `bütçe // M` olan bir tam sistem. Onu `secim.en_iyi_secim` çözer.

    Maçlar bağımsız sayıldığı için ikisi çarpılır:

        P(15/15) = P(eksen bileşimi oynananlar içinde) · P(alt sistem kaçmaz)

    ─── Alt sistemi neden `en_iyi_secim` çözüyor ────────────────────────

    İlk sürüm eksen dışını **üçlüye zorluyordu** ve bu ölçülebilir değer
    bırakıyordu: `test_tek_kupon_TEK_SISTEMIN_kendisi` tek kupon hâlinde iki
    planı karşılaştırdı ve `en_iyi_secim` daha iyisini buldu — `P = 0,1240`'a
    karşı `0,1142`, üstelik 17.496 kolona karşı 19.683. Sebebi: üçüncü
    sembolü çok küçük olan bir maçta **çifte**, üçlünün kapsamasının
    neredeyse tamamını üçte iki değil yarı bedele alır. Zorlama kalktı.
    """
    if butce is None or butce <= 0:
        raise ValueError("Butce pozitif bir kolon sayisi olmali.")
    if len(probs_listesi) != MAC_SAYISI:
        raise ValueError(f"{MAC_SAYISI} macin olasiligi gerekir.")

    from .secim import en_iyi_secim

    P = _matris(probs_listesi)
    emin_sira = np.argsort(-P.max(axis=1)).tolist()   # en eminden başlayarak

    en: tuple[float, list[Kupon], list[int]] | None = None
    for M in ARANAN_KUPON:
        if kupon_tavani is not None and M > kupon_tavani:
            break
        kupon_butce = butce // M
        if kupon_butce < 1:
            break
        for d in range(MAC_SAYISI + 1):
            if 3 ** d < M:
                continue                     # o kadar bileşim yok
            eksen = sorted(emin_sira[:d])
            kalanlar = [i for i in range(MAC_SAYISI) if i not in set(eksen)]
            alt = en_iyi_secim([probs_listesi[i] for i in kalanlar],
                               kupon_butce, esik=0) if kalanlar else None
            if kalanlar and alt is None:
                continue
            p_alt = 1.0 if alt is None else float(np.prod(
                [sum(probs_listesi[i][s] for s in sec)
                 for i, sec in zip(kalanlar, alt.secimler)]))
            kolon_kupon = 1 if alt is None else alt.bedel
            sec, p_eksen = _eksen_bilesimleri(P, eksen, M)
            gercek_M = len(sec)
            if gercek_M * kolon_kupon > butce:
                continue
            p = p_eksen * p_alt
            if en is not None and p <= en[0]:
                continue
            kuponlar = _kuponlari_kur(sec, eksen, kalanlar, alt, kolon_kupon)
            en = (p, kuponlar, eksen)

    if en is None:                            # bütçe 1 kolona bile yetmiyor
        raise ValueError(f"Butce hicbir plani karsilamiyor: {butce}")
    p, kuponlar, eksen = en
    return CokluPlan(
        kuponlar=kuponlar,
        eksen=eksen,
        kolon=sum(k.kolon for k in kuponlar),
        p_onbes=p,
    )


def _kuponlari_kur(sec, eksen: list[int], kalanlar: list[int], alt,
                   kolon_kupon: int) -> list[Kupon]:
    """Eksen bileşimleri + ortak alt sistem → oynanabilir kuponlar.

    Bileşim indeksi `_eksen_bilesimleri`de **ham** sembol düzeninde
    (`SEMBOLLER`) kuruldu; her basamak doğrudan bir `SEMBOLLER` indeksidir.
    Sıralama düzenine çevirmek bir hataydı ve `p_onbes` bekçisi tuttu.
    """
    eksen_kumesi = set(eksen)
    alt_secim = {} if alt is None else dict(zip(kalanlar, alt.secimler))
    kuponlar = []
    for ix in sec:
        kalan = int(ix)
        basamak = [0] * MAC_SAYISI
        for i in reversed(eksen):
            basamak[i] = kalan % 3
            kalan //= 3
        secimler = [[SEMBOLLER[basamak[i]]] if i in eksen_kumesi
                    else list(alt_secim[i])
                    for i in range(MAC_SAYISI)]
        kuponlar.append(Kupon(secimler=secimler, kolon=kolon_kupon))
    return kuponlar


def p_onbes(probs_listesi: list[dict[str, float]],
            kuponlar: list[Kupon]) -> float:
    """Verilen kuponlar için `P(15/15)` — plandan bağımsız, yeniden ölçüm.

    `coklu_plan` bu sayıyı eksen vektöründen taşır; bu gövde onu **kuponun
    kendisinden** yeniden hesaplar. İkisi ayrışırsa aynı kupon iki yerde iki
    farklı hedef gösterir, ve bekçisi bunu tutar.

    Kuponlar ayrık olduğu için toplam, kupon olasılıklarının toplamıdır.
    """
    P = _matris(probs_listesi)
    indeks = {s: j for j, s in enumerate(SEMBOLLER)}
    toplam = 0.0
    for k in kuponlar:
        p = 1.0
        for i, sec in enumerate(k.secimler):
            p *= sum(P[i][indeks[s]] for s in sec)
        toplam += p
    return toplam


def kademe_dagilimi(probs_listesi: list[dict[str, float]],
                    kuponlar: list[Kupon],
                    gercek: list[str]) -> dict[int, int]:
    """Gerçek sonuç verildiğinde her kademeyi tutturan **kolon sayısı**.

    `duz.kademe_sayimlari` tek sistem içindir; çoklu kuponda her kupon kendi
    sayımını üretir ve kuponlar ayrık olduğu için sayımlar toplanır.
    """
    from .duz import kademe_sayimlari

    top: dict[int, int] = {}
    for k in kuponlar:
        kacak = [i for i, sec in enumerate(k.secimler) if gercek[i] not in sec]
        s = [len(sec) for sec in k.secimler]
        for kademe, adet in kademe_sayimlari(s, kacak).items():
            top[kademe] = top.get(kademe, 0) + adet
    return top


def kupon_sayisi_egrisi(probs_listesi: list[dict[str, float]],
                        butce: int,
                        tavanlar: tuple[int, ...] = ARANAN_KUPON
                        ) -> list[tuple[int, int, float]]:
    """`(kupon sayısı, kolon/kupon, P(15/15))` — tavana göre eğri.

    Bir haftada operasyon yükü ile hedef arasındaki ödünleşmeyi görmek için.
    Eğri **monotondur**: tavanı büyütmek aramanın uzayını genişletir, yani
    bulunan plan kötüleşemez.
    """
    out = []
    for tavan in tavanlar:
        try:
            plan = coklu_plan(probs_listesi, butce, kupon_tavani=tavan)
        except ValueError:
            continue
        kolon_kupon = plan.kuponlar[0].kolon if plan.kuponlar else 0
        out.append((plan.kupon_sayisi, kolon_kupon, plan.p_onbes))
    return out
