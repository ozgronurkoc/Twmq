"""Çoklu kuponun denetimi.

Bu modülün iddiası bir **sayı** değil bir **yapıdır**: aynı bütçe birden çok
kupona bölünürse `P(15/15)` artar. Testlerin çoğu o yapının bozulmadığını
kovalıyor — kuponlar ayrık mı, bütçe aşılıyor mu, iki ayrı hesap aynı hedefi
mi söylüyor.

`test_p_onbes_plandan_ve_kupondan_AYNI` süs değil: yazıldığında **gerçek bir
hatayı tuttu**. `coklu_plan` bileşim indeksini ham sembol düzeninde (`1/0/2`)
kuruyor ama çözerken sıralama düzenine çeviriyordu; plan `P = 0,0329` derken
kupondan yeniden ölçüm `0,0215` veriyordu. Aynı kupon iki yerde iki farklı
hedef gösteriyordu ve tek görünür belirti bu ayrışmaydı.
"""

import numpy as np
import pytest

from spor_toto.coklu import (
    MAC_SAYISI,
    VARSAYILAN_KUPON_TAVANI,
    coklu_plan,
    eksen_sec,
    kademe_dagilimi,
    kupon_sayisi_egrisi,
    p_onbes,
)
from spor_toto.core import SEMBOLLER
from spor_toto.secim import en_iyi_secim


def _probs(tohum: int = 0) -> list[dict[str, float]]:
    rng = np.random.default_rng(tohum)
    out = []
    for _ in range(MAC_SAYISI):
        v = rng.dirichlet([6.0, 3.0, 2.5])
        out.append({s: float(v[j]) for j, s in enumerate(SEMBOLLER)})
    return out


def test_p_onbes_plandan_ve_kupondan_AYNI():
    """Planın taşıdığı hedef ile kupondan yeniden ölçülen hedef ayrışmaz."""
    for tohum in range(8):
        probs = _probs(tohum)
        plan = coklu_plan(probs, 19_683, VARSAYILAN_KUPON_TAVANI)
        assert plan.p_onbes == pytest.approx(p_onbes(probs, plan.kuponlar),
                                             rel=1e-12)


def test_kuponlar_AYRIK():
    """İki kupon aynı kolonu içeremez — içerseydi toplama hakkımız olmazdı.

    `p_onbes` kupon olasılıklarını **topluyor**; bu ancak kuponlar ayrıksa
    doğrudur. Ayrıklık, her kupon çiftinin en az bir eksen maçında farklı
    tek sembol taşımasından gelir.
    """
    probs = _probs(3)
    plan = coklu_plan(probs, 19_683, kupon_tavani=27)
    for a in range(len(plan.kuponlar)):
        for b in range(a + 1, len(plan.kuponlar)):
            ka, kb = plan.kuponlar[a], plan.kuponlar[b]
            assert any(set(x).isdisjoint(y)
                       for x, y in zip(ka.secimler, kb.secimler)), (
                f"{a}. ve {b}. kupon kesisiyor")


def test_kupon_sayisi_buyudukce_P15_DUSMEZ():
    """Eğri monoton: daha çok kupon her zaman en az o kadar kapsama verir."""
    for tohum in range(5):
        probs = _probs(tohum)
        egri = kupon_sayisi_egrisi(probs, 19_683)
        ps = [p for _, _, p in egri]
        assert ps == sorted(ps), f"egri monoton degil: {ps}"


def test_tek_kupon_TEK_SISTEMIN_kendisi():
    """Tavan 1 iken plan, `en_iyi_secim`in kurduğu tek sistemin aynısıdır.

    Bu modül mevcut davranışı **içerir**: genelleme onu bir aday olarak gezer
    ve tavan onu tek adaya indirdiğinde birebir aynısını üretmelidir. İlk
    sürüm bunu geçemiyordu — eksen dışını üçlüye zorladığı için `en_iyi_secim`
    daha iyisini buluyordu (`P = 0,1240` ↔ `0,1142`, 17.496 ↔ 19.683 kolon).
    """
    for tohum in range(5):
        probs = _probs(tohum)
        plan = coklu_plan(probs, 19_683, kupon_tavani=1)
        assert plan.kupon_sayisi == 1
        tek = en_iyi_secim(probs, 19_683, esik=0)
        a = [sorted(s) for s in plan.kuponlar[0].secimler]
        b = [sorted(s) for s in tek.secimler]
        assert a == b
        assert plan.p_onbes == pytest.approx(
            p_onbes(probs, plan.kuponlar), rel=1e-12)


def test_coklu_TEK_SISTEMI_gecer():
    """Asıl iddia: aynı bütçede çoklu kupon tek sistemden kötü olamaz.

    Arama tek sistemi zaten bir aday olarak geziyor, o yüzden bu bir
    **eşitsizliktir**, bir umut değil. Eşitlik nadir haftalarda olabilir;
    testin tuttuğu şey gerilemedir.
    """
    for tohum in range(8):
        probs = _probs(tohum)
        tek = coklu_plan(probs, 19_683, kupon_tavani=1)
        cok = coklu_plan(probs, 19_683, kupon_tavani=81)
        assert cok.p_onbes >= tek.p_onbes - 1e-12


def test_butce_asilmaz():
    for butce in (243, 729, 5_000, 19_683, 21_000):
        probs = _probs(1)
        plan = coklu_plan(probs, butce, VARSAYILAN_KUPON_TAVANI)
        assert plan.kolon <= butce
        assert plan.kolon == sum(k.kolon for k in plan.kuponlar)


def test_butce_pozitif_olmali():
    """Sessizce kırpmaz: eksik plan yanlış hedefi görünmez kılardı."""
    with pytest.raises(ValueError, match="pozitif"):
        coklu_plan(_probs(0), 0)


def test_eksen_FAVORI_olasiligina_gore_secilir():
    """Eksen, ev sahibi olasılığına göre değil favoriye göre seçilir.

    İlk sürüm `P[:, 0]`'a bakıyordu; `_matris` ham düzende (`1/0/2`) döndüğü
    için o sütun **ev sahibi**dir, favori değil. Deplasman favorili maçlar
    yanlış tarafa düşüyordu.
    """
    probs = [{"1": 0.10, "0": 0.20, "2": 0.70}] + \
            [{"1": 0.40, "0": 0.30, "2": 0.30}] * (MAC_SAYISI - 1)
    assert 0 in eksen_sec(probs, 1)


def test_butce_MERDIVEN_degil():
    """Daha büyük bütçe daha kötü plan veremez.

    Tek sistemde bedel `2^a·3^b` olduğu için bütçe basamaklıydı: 19.683 ile
    21.000 kolon **aynı** kuponu alıyordu. Çoklu kuponda bedel `M · kupon`
    ve `M` serbest tamsayı, yani aradaki para da bir şey satın alabilir.
    """
    probs = _probs(2)
    a = coklu_plan(probs, 19_683, kupon_tavani=243)
    b = coklu_plan(probs, 21_000, kupon_tavani=243)
    assert b.p_onbes >= a.p_onbes - 1e-12
    assert b.kolon >= a.kolon


def test_kademe_dagilimi_kupon_kupon_TOPLANIR():
    """Kademe sayımı her kupondan toplanır; tek sistemin sayımı değil."""
    probs = _probs(4)
    plan = coklu_plan(probs, 19_683, kupon_tavani=81)
    gercek = [max(p, key=p.get) for p in probs]      # her maçta favori
    dag = kademe_dagilimi(probs, plan.kuponlar, gercek)
    assert dag[15] == 1, "favori sonucunda tam olarak bir kolon 15 yapar"
    assert sum(dag.values()) <= plan.kolon
