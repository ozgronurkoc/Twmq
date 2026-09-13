"""Duyarlılık senaryosunun denetimi.

Bu modülün riski bir hesap hatası değil, bir **sızıntı**: ölçülen sapma bir
senaryo olarak kuruldu ve §3.64'ün durma kuralı gereği üretime konmadı.
Sızarsa depo, ölçülebilen son sezonda etkisi olmayan bir şeyi geçmişe
uydurmuş olur — `esik_taramasi`nın bir kez yaptığı hata. Bekçisi
`test_senaryo_URETIME_sizmiyor`.

İkinci risk kalibrasyon sınavının yönü: `plan_kalibrasyonu` küçük bir
`iki_yanli` verdiğinde bu "model iyi" değil "model iddiası gerçekleşenle
bağdaşmıyor" demektir. Yön bir kez ters yazılırsa bütün okuma tersine döner,
o yüzden iki uçtan da sınanıyor.
"""

import numpy as np
import pytest

from spor_toto.coklu import MAC_SAYISI, eksen_sec
from spor_toto.core import SEMBOLLER
from spor_toto.duyarlilik import BANKO_SAPMASI, TARANAN_SAYI, plan_kalibrasyonu, sapma_uygula


def _probs(tohum: int = 0) -> list[dict[str, float]]:
    rng = np.random.default_rng(tohum)
    out = []
    for _ in range(MAC_SAYISI):
        v = rng.dirichlet([6.0, 3.0, 2.5])
        out.append({s: float(v[j]) for j, s in enumerate(SEMBOLLER)})
    return out


# ============================================================
# SENARYO — sapmanın uygulanması
# ============================================================

def test_senaryo_URETIME_sizmiyor():
    """`karne.BANKO_Q_DUZELTMESI` sıfır kalmalı — durma kuralı karşılanmadı.

    Bu test bir hesabı değil bir **kararı** koruyor: sapma ölçüldü ama
    gözlenebilen son sezonda yoktu (§3.64, `n = 150 < 300`). Düzeltmeyi
    üretime koymak isteyen önce bu testi değiştirmek, yani kararı görünür
    kılmak zorunda.
    """
    from spor_toto.karne import BANKO_Q_DUZELTMESI, T1_DUZELTME_ESIGI

    assert BANKO_Q_DUZELTMESI == 0.0
    assert T1_DUZELTME_ESIGI == 300
    # Senaryo girdisi sıfır DEĞİL — yoksa duyarlılık ölçümü boş koşardı.
    assert BANKO_SAPMASI > 0.0


def test_sapma_girdiyi_DEGISTIRMIYOR():
    p = _probs(1)
    kopya = [dict(d) for d in p]
    sapma_uygula(p, 0.05, 6)
    assert p == kopya


def test_sapma_toplam_BIRI_koruyor():
    for sayi in (0, 1, 6, 15):
        yeni = sapma_uygula(_probs(2), BANKO_SAPMASI, sayi)
        for d in yeni:
            assert sum(d.values()) == pytest.approx(1.0)
            assert all(v >= 0.0 for v in d.values())


def test_sapma_YALNIZCA_en_emin_maclara_dokunuyor():
    """Dokunulan küme `eksen_sec`in kümesi olmalı — ikinci bir tanım yok."""
    p = _probs(3)
    sayi = 6
    yeni = sapma_uygula(p, BANKO_SAPMASI, sayi)
    hedef = set(eksen_sec(p, sayi))
    assert len(hedef) == sayi
    for i, (eski, taze) in enumerate(zip(p, yeni)):
        toplam = sum(eski.values())
        normal = {s: v / toplam for s, v in eski.items()}
        degisti = any(abs(taze[s] - normal[s]) > 1e-12 for s in SEMBOLLER)
        assert degisti is (i in hedef), f"mac {i}"


def test_sapma_favoriyi_TAM_sapma_kadar_kaldiriyor():
    p = _probs(4)
    yeni = sapma_uygula(p, 0.058, 15)
    for eski, taze in zip(p, yeni):
        toplam = sum(eski.values())
        fav = max(eski, key=lambda s: eski[s])
        assert taze[fav] == pytest.approx(eski[fav] / toplam + 0.058)


def test_sapma_SIFIR_taban_ile_ayni():
    """`sayi = 0` ve `sapma = 0` aynı şeyi vermeli: taban ayrı yol değil."""
    p = _probs(5)
    normal = [{s: v / sum(d.values()) for s, v in d.items()} for d in p]
    for yol in (sapma_uygula(p, BANKO_SAPMASI, 0), sapma_uygula(p, 0.0, 6)):
        for taze, bekle in zip(yol, normal):
            assert taze == pytest.approx(bekle)


def test_sapma_BIRI_asmiyor():
    """`p₁ + sapma > 1` kırpılmalı ve kalan semboller negatife düşmemeli."""
    p = [{"1": 0.98, "0": 0.01, "2": 0.01} for _ in range(MAC_SAYISI)]
    yeni = sapma_uygula(p, 0.5, MAC_SAYISI)
    for d in yeni:
        assert d["1"] == pytest.approx(1.0)
        assert d["0"] == pytest.approx(0.0)
        assert d["2"] == pytest.approx(0.0)


def test_sapma_araligi_ZORUNLU():
    with pytest.raises(ValueError):
        sapma_uygula(_probs(6), 1.0, 6)


def test_taranan_sayi_TABANI_iceriyor():
    """Taban (0) taranmazsa hiçbir senaryo okunamaz."""
    assert 0 in TARANAN_SAYI
    assert max(TARANAN_SAYI) == MAC_SAYISI


# ============================================================
# PLAN DÜZEYİ KALİBRASYON
# ============================================================

def test_kalibrasyon_UYUMDA_buyuk_p_veriyor():
    """Model doğruysa `iki_yanli` küçük olmamalı."""
    p = [0.1] * 100
    k = plan_kalibrasyonu(p, [1] * 10 + [0] * 90)
    assert k["beklenen"] == pytest.approx(10.0)
    assert k["gozlenen"] == 10
    assert k["oran"] == pytest.approx(1.0)
    assert k["iki_yanli"] > 0.5


def test_kalibrasyon_AYRISMAYI_yakaliyor():
    """Gerçekleşen beklenenin iki katıysa sınav bunu söylemeli."""
    p = [0.1] * 100
    k = plan_kalibrasyonu(p, [1] * 20 + [0] * 80)
    assert k["oran"] == pytest.approx(2.0)
    assert k["kuyruk"] < 0.01
    assert k["iki_yanli"] < 0.02


def test_kalibrasyon_iki_yonlu():
    """Az gerçekleşen de ayrışmadır — sınav tek yönlü olmamalı."""
    p = [0.5] * 100
    az = plan_kalibrasyonu(p, [1] * 20 + [0] * 80)
    assert az["iki_yanli"] < 0.01
    assert az["kuyruk"] > 0.99          # üst kuyruk büyük, ayrışma aşağıda


def test_kalibrasyon_kuyruk_GOZLENENI_iceriyor():
    """`kuyruk = P(X >= gözlenen)`; gözlenen 0 ise 1 olmalı."""
    k = plan_kalibrasyonu([0.3] * 10, [0] * 10)
    assert k["kuyruk"] == pytest.approx(1.0)


def test_kalibrasyon_ayrisik_hafta_sayisi_HATA():
    with pytest.raises(ValueError):
        plan_kalibrasyonu([0.1, 0.2], [1])
    with pytest.raises(ValueError):
        plan_kalibrasyonu([], [])
