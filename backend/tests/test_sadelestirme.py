"""Sadeleştirmenin bekçileri — **aynı kolonlar** iddiası sınanıyor.

Bu modülün tek iddiası bir özdeşliktir: birleştirme kolon kümesini
değiştirmez. Buradaki bekçilerin çoğu tam olarak o iddiayı kovalıyor,
çünkü bozulduğunda **sessizce** bozulur: slip sayısı düşer, tablo güzel
görünür ve plan başka bir plan olmuştur.

`test_ayrik_olmayan_girdi_REDDEDILIYOR` süs değil: grup birleştirmenin
bütçeyi koruması girdinin ayrıklığına dayanır. Ayrık olmayan bir kümede
aynı gövde kolon sayısını **düşürür** (örtüşen kolon bir kez sayılır) ve
sonuç "daha ucuz plan" gibi görünür — oysa oynanan kupon değişmemiştir.
"""

import itertools

import numpy as np
import pytest

from spor_toto.coklu import MAC_SAYISI, Kupon, coklu_plan, p_onbes
from spor_toto.core import SEMBOLLER
from spor_toto.operasyon import ayrik_mi, birlesim_p_onbes
from spor_toto.sadelestirme import (
    ayni_kolonlar,
    ayrik_bolunti_mu,
    birlestir,
    en_az_slip,
    isaret_sayisi,
    kolonlar,
    sadelestir,
)

BUTCE = 19_683
TAVAN = 27


def _probs(tohum: int = 0) -> list[dict[str, float]]:
    rng = np.random.default_rng(tohum)
    out = []
    for _ in range(MAC_SAYISI):
        v = rng.dirichlet([6.0, 3.0, 2.5])
        out.append(dict(zip(SEMBOLLER, (float(x) for x in v))))
    return out


def _kupon(picks: list[str]) -> Kupon:
    kolon = 1
    for s in picks:
        kolon *= len(s)
    return Kupon(secimler=[list(s) for s in picks], kolon=kolon)


def _tek_konum(a: str, b: str) -> list[Kupon]:
    """Yalnız son konumda ayrışan iki kupon — en küçük birleşme."""
    ortak = ["1"] * (MAC_SAYISI - 1)
    return [_kupon([*ortak, a]), _kupon([*ortak, b])]


# ─── Özdeşlik: kolonlar değişmiyor ────────────────────────────────────────

def test_kolon_KUMESI_ayni():
    """Birleştirmenin **tek** iddiası: aynı kolonlar."""
    plan = coklu_plan(_probs(), BUTCE, TAVAN)
    yeni = birlestir(plan.kuponlar)
    assert ayni_kolonlar(plan.kuponlar, yeni)


def test_kolon_SAYISI_degismiyor():
    """Bütçe aynı kalıyor — bölüntü olmasının sebebi bu."""
    plan = coklu_plan(_probs(1), BUTCE, TAVAN)
    yeni = birlestir(plan.kuponlar)
    assert sum(k.kolon for k in yeni) == plan.kolon
    # `Kupon.kolon` alanı ile fiili çarpım da ayrışmamalı.
    for k in yeni:
        carpim = 1
        for s in k.secimler:
            carpim *= len(s)
        assert k.kolon == carpim


@pytest.mark.parametrize("tavan", [1, 3, 9, 27, 81])
def test_p_onbes_DEGISMIYOR(tavan):
    """`P(15/15)` kolon kümesinin fonksiyonu; küme aynıysa o da aynı."""
    probs = _probs(2)
    plan = coklu_plan(probs, BUTCE, tavan)
    yeni = birlestir(plan.kuponlar)
    assert p_onbes(probs, yeni) == pytest.approx(plan.p_onbes, rel=1e-12)
    # Ve ayrıklığı varsaymayan gövdeyle de aynı — birleşmiş küme örtüşüyor
    # olsaydı bu iki sayı ayrışırdı.
    assert birlesim_p_onbes(probs, yeni) == pytest.approx(plan.p_onbes,
                                                          rel=1e-12)


def test_cikti_AYRIK():
    """Çıktı bölüntü; örtüşen kapama olsaydı kolon iki kez ödenirdi."""
    plan = coklu_plan(_probs(3), BUTCE, 81)
    yeni = birlestir(plan.kuponlar)
    assert ayrik_bolunti_mu(yeni)
    assert ayrik_mi(yeni)        # `operasyon`un bağımsız gövdesi de tutsun


# ─── Birleşme gerçekten oluyor mu ─────────────────────────────────────────

def test_TEK_KONUMDA_ayrisan_iki_kupon_BIRLESIYOR():
    yeni = birlestir(_tek_konum("1", "2"))
    assert len(yeni) == 1
    assert set(yeni[0].secimler[-1]) == {"1", "2"}
    assert yeni[0].kolon == 2


def test_IKI_konumda_ayrisanlar_BIRLESMIYOR():
    """İki konumda ayrışan kutuların birleşimi kutu değildir."""
    a = _kupon(["1"] * MAC_SAYISI)
    b = _kupon(["2", *["1"] * (MAC_SAYISI - 2), "2"])
    assert len(birlestir([a, b])) == 2


def test_gercek_planda_slip_KUPONDAN_AZ():
    """Modülün var olma sebebi: 81 kupon 81 slip değil."""
    s = sadelestir(coklu_plan(_probs(4), BUTCE, 81).kuponlar)
    assert s.slip_sonra < s.slip_once
    assert s.isaret_sonra < s.isaret_once
    assert s.slip_orani > 1.0


def test_TEKDUZE_plan_TAHSISLIDEN_cok_birlesiyor():
    """§3.75'in asıl bulgusu: tahsis birleşmeyi öldürüyor.

    Tekdüze bütçede bütün kuponlar aynı alt sistemi oynar ve yalnız
    eksende ayrışır; tahsisli planda alt sistemler de ayrışır. Burada
    tekdüze plan elle kuruluyor (aynı alt sistem, ayrı eksen bileşimleri)
    ki kıyas mekanizmayı yalıtsın.
    """
    ortak = ["102", "102", "10"]
    ayrisan = ["102", "10", "10"]
    dolgu = ["1"] * (MAC_SAYISI - 3 - len(ortak))
    bilesimler = list(itertools.product("102", repeat=3))
    tekduze = [_kupon([*b, *ortak, *dolgu]) for b in bilesimler]
    tahsisli = [_kupon([*b, *(ortak if i % 2 else ayrisan), *dolgu])
                for i, b in enumerate(bilesimler)]
    a = sadelestir(tekduze)
    b = sadelestir(tahsisli)
    assert a.slip_orani > b.slip_orani


# ─── Sıra ve sözleşme ─────────────────────────────────────────────────────

def test_cikti_BELIRLI_sirada():
    """Kararlılık sözleşmesi: aynı girdi aynı dosyayı versin.

    Sıra kolon sayısına göre azalan; denetim sırası (olasılığa göre)
    kaydı kuran tarafın işi ve orada ayrıca sınanıyor.
    """
    kuponlar = coklu_plan(_probs(5), BUTCE, 81).kuponlar
    yeni = birlestir(kuponlar)
    kolonlar_ = [k.kolon for k in yeni]
    assert kolonlar_ == sorted(kolonlar_, reverse=True)
    assert [k.picks for k in birlestir(list(reversed(kuponlar)))] == \
        [k.picks for k in yeni]


def test_semboller_SIRALI():
    """`picks` `1/0/2` düzeninde kalsın — kayıt ve arayüz onu bekliyor."""
    yeni = birlestir(coklu_plan(_probs(6), BUTCE, 27).kuponlar)
    for k in yeni:
        for s in k.secimler:
            assert s == [x for x in SEMBOLLER if x in s]


def test_ayrik_olmayan_girdi_REDDEDILIYOR():
    """Ayrıklık varsayım değil ÖN KOŞUL; bozuksa gövde sessizce yalan söyler."""
    a = _kupon(["102", *["1"] * (MAC_SAYISI - 1)])
    b = _kupon(["1", *["1"] * (MAC_SAYISI - 1)])
    assert not ayrik_bolunti_mu([a, b])
    with pytest.raises(ValueError):
        birlestir([a, b])


def test_bos_girdi():
    assert birlestir([]) == []
    assert sadelestir([]).slip_sonra == 0


def test_tek_kupon_DEGISMIYOR():
    k = _kupon(["102", *["1"] * (MAC_SAYISI - 1)])
    yeni = birlestir([k])
    assert len(yeni) == 1
    assert kolonlar(yeni) == kolonlar([k])


def test_isaret_sayisi_karalanan_kutucuk():
    assert isaret_sayisi([_kupon(["102", *["1"] * (MAC_SAYISI - 1)])]) == 17


# ─── Ne kadar iyi — kesin enküçüğe karşı ──────────────────────────────────

def _tekduze(bilesimler, alt=("102", "10")) -> list[Kupon]:
    """Eksen bileşimleri + **ortak** alt sistem — tekdüze bütçeli plan.

    Birleşmenin ölçüldüğü aile budur; tahsisli plan alt sistemleri de
    ayrıştırdığı için küçük ve kesin ölçülebilir bir örnek vermiyor.
    """
    dolgu = ["1"] * (MAC_SAYISI - len(bilesimler[0]) - len(alt))
    return [_kupon([*b, *alt, *dolgu]) for b in bilesimler]


@pytest.mark.parametrize("bilesimler", [
    # Tam küp: tek kutuya inmeli.
    list(itertools.product("102", repeat=3)),
    # Merdiven (aşağı küme): eksen bileşimlerinin gerçek şekli.
    [("1", "1"), ("1", "0"), ("1", "2"), ("0", "1"), ("0", "0"), ("2", "1")],
    # Tek nokta eksik: birleşme kırılıyor, kaç kutuya bölündüğü ölçülüyor.
    [b for b in itertools.product("102", repeat=3) if b != ("2", "2", "2")],
    # L şekli: açgözlü sıranın tuzağa düştüğü klasik örnek.
    [("1", "1"), ("1", "0"), ("1", "2"), ("0", "1"), ("2", "1")],
])
def test_KESIN_enkucukle_ayni(bilesimler):
    """Açgözlü fixpoint üst sınırdır; küçük örnekte kesin cevap ölçülüyor.

    Bu ailede ikisi **eşit** çıkıyor, yani açgözlü seçim burada darboğaz
    değil. Bu bir kanıt değil bir ölçüm: gerçek planlarda `en_az_slip`
    bütçeyi aşıyor ve kıyas yapılamıyor (bir sonraki bekçi).
    """
    kuponlar = _tekduze(bilesimler)
    kesin = en_az_slip(kuponlar)
    assert kesin is not None
    assert len(birlestir(kuponlar)) == kesin


def test_en_az_slip_BUTCE_asilinca_None():
    """Sınır aşıldığında sayı uydurulmuyor.

    İki bütçe ayrı ayrı sınanıyor: kutu sayımı ve arama. İlki eksikken
    gövde gerçek bir planda dakikalarca dönüyordu.
    """
    kuponlar = _tekduze(list(itertools.product("102", repeat=3)))
    assert en_az_slip(kuponlar, kutu_siniri=5) is None
    assert en_az_slip(_tekduze(
        [b for b in itertools.product("102", repeat=3) if b != ("2", "2", "2")],
    ), dugum_siniri=1) is None


# ─── Örtüşen kapama neden reddedildi ──────────────────────────────────────

def test_ORTUSEN_kapama_kolonu_COGALTIR():
    """Modül başlığındaki iddia: örtüşmeye izin vermek parayı harcar.

    İki kutu bir konumda **kesişiyorsa** birleşimleri hâlâ tek kutuya
    iner, ama o kutu ikisinin toplamından çok kolon taşır. Gövde bu
    birleşmeyi yapmıyor; bekçi yapılsaydı ne olacağını ölçüyor.
    """
    a = _kupon(["10", *["1"] * (MAC_SAYISI - 1)])
    b = _kupon(["02", *["1"] * (MAC_SAYISI - 1)])
    birlesim = _kupon(["102", *["1"] * (MAC_SAYISI - 1)])
    gercek = len(set(itertools.product(*[set(s) for s in a.secimler]))
                 | set(itertools.product(*[set(s) for s in b.secimler])))
    assert gercek == 3
    assert birlesim.kolon == 3           # kolon kümesi aynı...
    assert a.kolon + b.kolon == 4        # ...ama ödenen 4
