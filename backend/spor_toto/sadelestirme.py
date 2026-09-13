"""Sadeleştirme — aynı kolonlar, daha az slip.

§3.74 operasyon sorusunun istatistiksel yarısını kapattı ve lojistik
yarısını *"bu depodan ölçülemez"* diye bıraktı: **bir insan 81 kuponu
kupon kapanmadan girebiliyor mu?** O cümle bir şeyi sormadan doğru kabul
ediyordu — **81 kupon 81 slip demek**.

Demek değil. Planın kuponları birer **kutudur** (her maçta bir sembol
kümesi, kolon sayısı kümelerin çarpımı) ve iki kutu *bir tek* konumda
ayrışıyorsa o konumdaki kümeler birleştirilerek **tek kutu** yazılabilir:

    kupon A:  1 2 102 102 2 ... 2 ...
    kupon B:  1 2 102 102 2 ... 1 ...
    ───────────────────────────────────
    tek slip: 1 2 102 102 2 ... 12 ...

Bu bir yaklaşıklık değil bir **özdeşliktir**. Birleşmiş kutunun kolon
kümesi ikisinin birleşimidir, kolon sayısı toplamlarıdır (kutular ayrık),
ve `P(15/15)` kolon kümesinin bir fonksiyonu olduğu için **birebir aynı
kalır**. Değişen tek şey kaç kez elle kutu doldurulacağı.

─── Neden ÖRTÜŞEN kapama değil, AYRIK bölüntü ────────────────────────────

Aynı kolon kümesini daha az kutuyla yazmanın iki yolu var ve biri
tuzaktır. Kutuların **örtüşmesine** izin verilirse arama serbestleşir ve
ilk bakışta daha az slip vaat eder — ama örtüşen kolon **iki kez
oynanır**, yani iki kez ödenir. Ölçüldü (5. haftanın donmuş kaydı, açgözlü
kapama): slip sayısı **25**, yani ayrık bölüntüyle **aynı**, ama kolon
19.683 yerine **33.048** — bütçenin 1,68 katı. Serbestlik burada hiçbir
şey almıyor, yalnızca para harcıyor.

Bu yüzden buradaki gövde bir **bölüntü** arar: kutular ikişer ikişer
ayrık kalır, toplam kolon sayısı **değişmez**, bütçe aynıdır. Bedava olan
şey slip sayısıdır, başka hiçbir şey değil.

─── Okuma kuralı — ölçüm görülmeden yazıldı ──────────────────────────────

1. **Slip sayısı DÜŞECEK.** Bu bir keşif değil, kurulum: eksen
   bileşimlerinin en olası `M` tanesi rütbe sırasında bir **aşağı
   kümedir**, yani tek koordinatta komşu olan bileşimler kümeye birlikte
   girer ve birleşmeye hazır dururlar. Ölçülecek olan düşüşün *oranıdır*.
2. **İşaret sayısı da DÜŞECEK ve bu ayrı bir kazançtır.** Bir birleşme
   `Σ_{i≠k} |A_i|` işareti siler (iki kutunun ortak konumları bir kez
   yazılır). Elle giriş yükü slip sayısıyla değil karalanan kutucuk
   sayısıyla orantılıysa kazanç oradadır.
3. **TAHSİS BİRLEŞMEYİ ENGELLER.** §3.71 her kupona **ayrı** alt sistem
   bütçesi veriyor, yani kuponların alt sistemleri artık birbirinin aynı
   değil. İki kutu ancak bir tek konumda ayrışıyorsa birleşir; alt
   sistemleri ayrışan iki kupon **hiç** birleşmez. Yani §3.71'in `P`
   kazancının ölçülmemiş bir operasyon bedeli var ve bu modül onu ölçüyor.
   Beklenti: tekdüze bütçeli (tahsissiz) planda birleşme oranı belirgin
   biçimde daha yüksek çıkacak.
4. **BEKLENEN KAYIP AYNI KALABİLİR, ve bu bir kusur değil.** §3.74'ün
   kaybı `M · r · δ̄` idi: slip sayısı çarpı slip başına hata oranı çarpı
   ortalama bedel. Birleşme `M`yi küçültürken `δ̄`yı **büyütür** — atlanan
   kutu artık daha büyüktür. Hata oranı slip başınaysa iki etki birbirini
   götürebilir; kutucuk başınaysa götürmez. Bu modül iki sayıyı da ayrı
   ayrı veriyor ve hangi modelin doğru olduğunu **söylemiyor** — o bir
   insan olgusudur, §3.74'ün kapanmayan yarısı.
5. **Bulunan sayı bir ÜST SINIRDIR.** Ayrık kutu bölüntüsünün enküçüğünü
   bulmak genel hâlde zordur. `birlestir` açgözlü bir fixpoint verir;
   `en_az_slip` küçük örneklerde kesin cevabı arar ve bekçi ikisini
   karşılaştırır — yani "ne kadar iyi" sorusu ölçülüdür, iddia edilmez.
   Üst sınır olması iddiayı **zayıflatan** yöndedir: gerçek yük ölçülenden
   ancak daha az olabilir.

─── Gövde: konum konum grup birleştirme ──────────────────────────────────

Her turda bir konum `k` seçilir ve kutular *`k` dışındaki bütün
konumlara* göre gruplanır. Aynı gruptaki kutular yalnızca `k`da ayrışır;
ayrık oldukları için `k`daki sembol kümeleri de ayrıktır, dolayısıyla
grubun tamamı `k`da birleşen **tek** kutuya iner. Tur, en çok kazandıran
konumu seçer; hiçbir konum kazandırmıyorsa fixpoint'tir.

İkişer birleştirmeye göre üstünlüğü grubu **bir kerede** kapatmasıdır;
ikişer gövde sıraya duyarlıydı (5. haftada 60 rastgele sırada en iyisi 30,
bu gövde 25). Işın araması (genişlik 8 ve 40) hiçbir haftada bu sayıyı
iyileştirmedi, yani açgözlü seçim bu ailede darboğaz değil.
"""
from __future__ import annotations

import itertools
from collections.abc import Iterable, Sequence
from typing import NamedTuple

from .coklu import MAC_SAYISI, Kupon
from .core import SEMBOLLER, sirala_semboller

#: Kutu: her maç için bir sembol kümesi. `Kupon.secimler`in çekirdek hâli.
Kutu = tuple[frozenset[str], ...]


class Sadelestirme(NamedTuple):
    """Bir planın elle giriş yükü — birleştirmeden önce ve sonra.

    `kolon` birleştirmeyle **değişmez** (bekçisi `test_kolon_DEGISMIYOR`);
    alan bu yüzden tekildir. Değişenler `slip` ve `isaret`tir.
    """

    kuponlar: list[Kupon]
    slip_once: int
    slip_sonra: int
    isaret_once: int
    isaret_sonra: int
    kolon: int
    en_buyuk_slip_kolon: int

    @property
    def slip_orani(self) -> float:
        """Kaç kat az slip. 1,0 hiç birleşme olmadı demektir."""
        return self.slip_once / self.slip_sonra if self.slip_sonra else 1.0

    @property
    def isaret_orani(self) -> float:
        """Kaç kat az karalanan kutucuk."""
        return (self.isaret_once / self.isaret_sonra
                if self.isaret_sonra else 1.0)


# ─── Kutu cebri ───────────────────────────────────────────────────────────

def _kutu(kupon: Kupon) -> Kutu:
    return tuple(frozenset(s) for s in kupon.secimler)


def _kolon(kutu: Kutu) -> int:
    n = 1
    for s in kutu:
        n *= len(s)
    return n


def isaret_sayisi(kuponlar: Sequence[Kupon]) -> int:
    """Planın tamamında karalanan kutucuk sayısı.

    Slip sayısı elle girişin **kaç kez** yapıldığını sayar; bu, her birinde
    **ne kadar** iş olduğunu. İkisi birlikte okunmalı: birleşme slip
    sayısını düşürürken her slipi büyütür, ama kutucuk sayısı yine de
    düşer — birleşen kutuların ortak konumları bir kez yazılır.

    >>> isaret_sayisi([Kupon(secimler=[["1"]] * 15, kolon=1)])
    15
    """
    return sum(len(s) for k in kuponlar for s in k.secimler)


def kolonlar(kuponlar: Iterable[Kupon]) -> set[tuple[str, ...]]:
    """Planın oynadığı kolonların kümesi — birleştirmenin **ölçüsü**.

    Birleştirme ancak bu küme birebir aynı kalıyorsa doğrudur. Pahalıdır
    (21.000 kolon) ama denetim haftada bir koşar; `operasyon.
    birlesim_p_onbes` aynı sebeple pahalı ve aynı sebeple doğru.
    """
    out: set[tuple[str, ...]] = set()
    for k in kuponlar:
        out.update(itertools.product(*k.secimler))
    return out


def ayni_kolonlar(a: Sequence[Kupon], b: Sequence[Kupon]) -> bool:
    """İki kupon kümesi **tam olarak** aynı kolonları mı oynuyor."""
    return kolonlar(a) == kolonlar(b)


def ayrik_bolunti_mu(kuponlar: Sequence[Kupon]) -> bool:
    """Kutular ikişer ikişer ayrık mı — yani kolon iki kez ödenmiyor mu.

    `operasyon.ayrik_mi` ile aynı soru; burada ayrıca `birlestir`in ön
    koşuludur, çünkü grup birleştirmenin bütçeyi koruması tam olarak
    girdinin ayrıklığına dayanır.
    """
    kutular = [_kutu(k) for k in kuponlar]
    for a, b in itertools.combinations(kutular, 2):
        if all(a[i] & b[i] for i in range(MAC_SAYISI)):
            return False
    return True


# ─── Grup birleştirme ─────────────────────────────────────────────────────

def _tur(kutular: list[Kutu], k: int) -> list[Kutu]:
    """`k` konumunda birleşebilen bütün grupları bir kerede kapatır."""
    gruplar: dict[Kutu, list[frozenset[str]]] = {}
    for c in kutular:
        gruplar.setdefault(c[:k] + c[k + 1:], []).append(c[k])
    return [(*kalan[:k], frozenset().union(*semboller), *kalan[k:])
            for kalan, semboller in gruplar.items()]


def _grup_birlestir(kutular: list[Kutu]) -> list[Kutu]:
    """Hiçbir konum kazandırmayana kadar birleştir — fixpoint.

    Durma koşulu **bütün** konumların kazanamamasıdır, tek konumun değil:
    bir konumda birleşme başka bir konumu açabilir.
    """
    simdi = list(kutular)
    while True:
        en_iyi: list[Kutu] | None = None
        for k in range(MAC_SAYISI):
            aday = _tur(simdi, k)
            if en_iyi is None or len(aday) < len(en_iyi):
                en_iyi = aday
        assert en_iyi is not None
        if len(en_iyi) >= len(simdi):
            return simdi
        simdi = en_iyi


def birlestir(kuponlar: Sequence[Kupon]) -> list[Kupon]:
    """Aynı kolonları daha az kuponla yazar. Kolon kümesi **birebir** aynı.

    Çıktı kolon sayısına göre azalan, eşitlikte sembollere göre **belirli**
    sıradadır. Bu bir denetim sırası değil bir *kararlılık* sözleşmesidir:
    aynı girdi aynı dosyayı versin. §3.74'ün denetim sırası olasılığa
    göredir ve olasılık bu modülde yok; onu kayıt kuran taraf
    (`scripts/coklu_kupon.py`, `operasyon.kupon_olasiliklari`) veriyor —
    `coklu_plan`ın da kendi çıktısını sıralamamasıyla aynı iş bölümü.

    Girdi ayrık değilse `ValueError`: birleştirme ayrıklığı **varsayar** ve
    varsayım bozuksa çıktının kolon sayısı girdininkinden sapar — yani
    sessizce bütçe değiştirir.
    """
    if not kuponlar:
        return []
    # Boy denetimi SESLİ: eksik konumlu bir kupon aşağıda `IndexError`
    # veriyordu ve yığın izi sebebi göstermiyordu.
    for k in kuponlar:
        if len(k.secimler) != MAC_SAYISI:
            raise ValueError(
                f"Kupon {MAC_SAYISI} mac tasimali, {len(k.secimler)} tasiyor.")
    if not ayrik_bolunti_mu(kuponlar):
        raise ValueError("Kuponlar ayrik degil; birlestirme bolunti olmaz.")
    yeni = _grup_birlestir([_kutu(k) for k in kuponlar])
    yeni.sort(key=lambda kutu: (-_kolon(kutu),
                                [sorted(s) for s in kutu]))
    return [Kupon(secimler=[sirala_semboller(s) for s in kutu],
                  kolon=_kolon(kutu))
            for kutu in yeni]


def sadelestir(kuponlar: Sequence[Kupon]) -> Sadelestirme:
    """`birlestir` + ölçülen yük farkı, tek çağrıda."""
    yeni = birlestir(kuponlar)
    return Sadelestirme(
        kuponlar=yeni,
        slip_once=len(kuponlar),
        slip_sonra=len(yeni),
        isaret_once=isaret_sayisi(kuponlar),
        isaret_sonra=isaret_sayisi(yeni),
        kolon=sum(k.kolon for k in yeni),
        en_buyuk_slip_kolon=max((k.kolon for k in yeni), default=0),
    )


# ─── Kesin enküçük — yalnız bekçi için ────────────────────────────────────

def en_az_slip(kuponlar: Sequence[Kupon],
               dugum_siniri: int = 200_000,
               kutu_siniri: int = 50_000) -> int | None:
    """Ayrık kutu bölüntüsünün **kesin** enküçüğü; bütçe aşılırsa `None`.

    `birlestir` bir üst sınır verir ve ne kadar iyi olduğu ölçülmeden
    bilinmez. Bu gövde küçük örneklerde kesin cevabı arar: `S` içinde kalan
    bütün kutular kurulur, sonra dal-sınır her adımda kalan noktaların **en
    küçüğünü** kapsayan ve kalana sığan kutuları dener.

    Üretimde koşmaz — iki yerde de üsteldir. **İki** bütçe var ve ikisi
    ayrı yeri tutuyor: `kutu_siniri` kutu sayımını, `dugum_siniri` aramayı.
    İlki eksikti ve gövde gerçek bir planda (27 kupon, 15 değişen konum)
    dakikalarca dönüyordu — sayım hiç bitmediği için arama bütçesine hiç
    gelinmiyordu. Aşılınca `None` döner; bekçi `None` gelince kıyası
    **atlar**, çünkü "ölçemedim" ile "eşit" ayrı şeylerdir.
    """
    if not kuponlar:
        return 0
    kutular = [_kutu(k) for k in kuponlar]
    degisen = [i for i in range(MAC_SAYISI)
               if len({kt[i] for kt in kutular}) > 1]
    if not degisen:
        return 1
    S: set[tuple[str, ...]] = set()
    for kt in kutular:
        S.update(itertools.product(*[sorted(kt[i]) for i in degisen]))
    n = len(degisen)

    # `S` içinde kalan bütün kutular: tek noktadan başlayıp genişlet.
    tumu: set[Kutu] = {tuple(frozenset([p[i]]) for i in range(n)) for p in S}
    if len(tumu) > kutu_siniri:
        return None
    sinir = set(tumu)
    while sinir:
        yeni_kutular: set[Kutu] = set()
        for c in sinir:
            for i in range(n):
                if len(c[i]) == len(SEMBOLLER):
                    continue
                for s in SEMBOLLER:
                    if s in c[i]:
                        continue
                    c2 = tuple(c[j] if j != i else frozenset(c[i] | {s})
                               for j in range(n))
                    if c2 in tumu or not set(itertools.product(*c2)) <= S:
                        continue
                    tumu.add(c2)
                    yeni_kutular.add(c2)
        if len(tumu) > kutu_siniri:
            return None
        sinir = yeni_kutular

    kapsam = {c: frozenset(itertools.product(*c)) for c in tumu}
    nokta_kutulari: dict[tuple[str, ...], list[Kutu]] = {}
    for c, noktalar in kapsam.items():
        for p in noktalar:
            nokta_kutulari.setdefault(p, []).append(c)
    for p in nokta_kutulari:
        nokta_kutulari[p].sort(key=lambda c: -len(kapsam[c]))

    en_iyi = [len(S) + 1]
    dugum = [0]
    asildi = [False]

    def dal(kalan: frozenset[tuple[str, ...]], sayi: int) -> None:
        if asildi[0]:
            return
        dugum[0] += 1
        if dugum[0] > dugum_siniri:
            asildi[0] = True
            return
        if not kalan:
            en_iyi[0] = min(en_iyi[0], sayi)
            return
        enb = max(len(kapsam[c] & kalan)
                  for p in kalan for c in nokta_kutulari[p])
        if sayi + -(-len(kalan) // enb) >= en_iyi[0]:
            return
        p = min(kalan)
        for c in nokta_kutulari[p]:
            if kapsam[c] <= kalan:
                dal(kalan - kapsam[c], sayi + 1)

    dal(frozenset(S), 0)
    return None if asildi[0] else en_iyi[0]
