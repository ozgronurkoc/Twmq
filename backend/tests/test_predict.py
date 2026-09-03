"""Tahminci sözleşmesinin denetimi.

Buradaki asıl mesele üç referansın "doğru sayı" üretmesi değil, **sözleşmeye
uyması**: her tahminci 15 maç döndürür, olasılıkları 1'e toplanır ve eğitimle
durum tutan tahminci fabrikadan taze çıktığında önceki eğitimi taşımaz. Sonuncusu
sızıntıya karşı tek savunmadır (bkz. `test_evaluate.test_sezon_sabiti_sizdirmaz`).
"""

import pytest

from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.predict import (
    REFERANS_AD,
    DuzgunTahminci,
    PiyasaTahminci,
    SezonSabitiTahminci,
    Tahminci,
    referans_fabrikalar,
)

TEK_TIP = {"1": 0.5, "0": 0.3, "2": 0.2}


def _girdi(results: str, probs=None) -> dict:
    return {
        "week": 99, "close_date": "2026-01-01", "results": results,
        "probs": list(probs) if probs else [None] * MATCH_COUNT,
        "missing": 0, "usable": True,
    }


# ─── sözleşme ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fabrika", referans_fabrikalar())
def test_sozlesme_15_mac_ve_toplam_bir(fabrika):
    """Her referans 15 maç döndürür ve her maçın olasılıkları 1'e toplanır."""
    t = fabrika()
    t.egit([_girdi("1" * MATCH_COUNT)])
    tahminler = t.tahmin(_girdi("1" * MATCH_COUNT))

    assert len(tahminler) == MATCH_COUNT
    for p in tahminler:
        assert set(p) == set(SYMBOLS)
        assert pytest.approx(sum(p.values()), abs=1e-9) == 1.0
        assert all(v >= 0 for v in p.values())


@pytest.mark.parametrize("fabrika", referans_fabrikalar())
def test_fabrika_taze_ornek_verir(fabrika):
    """İki çağrı ayrı nesne verir — eğitim durumu paylaşılmaz."""
    assert fabrika() is not fabrika()


def test_taban_sinif_tahmin_yazilmadan_calismaz():
    with pytest.raises(NotImplementedError):
        Tahminci().tahmin(_girdi("1" * MATCH_COUNT))


def test_referans_ad_piyasadir():
    """Karşılaştırmanın çizgisi piyasadır; değişirse koşumun anlamı değişir."""
    assert REFERANS_AD == "piyasa"
    assert REFERANS_AD in {f.ad for f in referans_fabrikalar()}


# ─── duzgun ───────────────────────────────────────────────────────────────────

def test_duzgun_her_sembole_ucte_bir():
    tahminler = DuzgunTahminci().tahmin(_girdi("1" * MATCH_COUNT))
    for p in tahminler:
        for s in SYMBOLS:
            assert pytest.approx(p[s], abs=1e-12) == 1 / 3


def test_duzgun_egitimden_etkilenmez():
    """Zemin sabittir: ne görürse görsün 1/3 der."""
    t = DuzgunTahminci()
    once = t.tahmin(_girdi("1" * MATCH_COUNT))
    t.egit([_girdi("1" * MATCH_COUNT)] * 10)
    assert t.tahmin(_girdi("1" * MATCH_COUNT)) == once


# ─── sezon_sabiti ─────────────────────────────────────────────────────────────

def test_sezon_sabiti_egitimsizken_duzgune_duser():
    """Bilgisizliğini itiraf eder; uydurma bir dağılım üretmez."""
    for p in SezonSabitiTahminci().tahmin(_girdi("1" * MATCH_COUNT)):
        assert pytest.approx(p["1"], abs=1e-12) == 1 / 3


def test_sezon_sabiti_egitim_dagilimini_ogrenir():
    """3 hafta: 30 adet '1', 15 adet '0' → 2/3 ve 1/3."""
    t = SezonSabitiTahminci()
    t.egit([_girdi("1" * MATCH_COUNT), _girdi("1" * MATCH_COUNT),
            _girdi("0" * MATCH_COUNT)])
    p = t.tahmin(_girdi("1" * MATCH_COUNT))[0]
    assert pytest.approx(p["1"], abs=1e-9) == 2 / 3
    assert pytest.approx(p["0"], abs=1e-9) == 1 / 3
    assert pytest.approx(p["2"], abs=1e-9) == 0.0


def test_sezon_sabiti_her_maca_ayni_dagilimi_verir():
    """Maçlar arasında ayrım yapmaz — naif taban olmasının sebebi bu."""
    t = SezonSabitiTahminci()
    t.egit([_girdi("102" * 5)])
    tahminler = t.tahmin(_girdi("102" * 5))
    assert all(p == tahminler[0] for p in tahminler)


# ─── piyasa ───────────────────────────────────────────────────────────────────

def test_piyasa_oranlari_oldugu_gibi_gecirir():
    girdi = _girdi("1" * MATCH_COUNT, [dict(TEK_TIP)] * MATCH_COUNT)
    for p in PiyasaTahminci().tahmin(girdi):
        assert p == TEK_TIP


def test_piyasa_orani_olmayan_maca_duzgun_verir():
    """`usable=False` haftada oran eksik olabilir; sessizce sıfır verilmez."""
    probs = [dict(TEK_TIP)] * MATCH_COUNT
    probs[3] = None
    tahminler = PiyasaTahminci().tahmin(_girdi("1" * MATCH_COUNT, probs))
    assert pytest.approx(tahminler[3]["1"], abs=1e-12) == 1 / 3
    assert tahminler[0] == TEK_TIP


def test_piyasa_donen_sozlugu_kopyalar():
    """Çağıran çıktıyı değiştirirse oran arşivi bozulmamalı."""
    kaynak = dict(TEK_TIP)
    girdi = _girdi("1" * MATCH_COUNT, [kaynak] * MATCH_COUNT)
    tahminler = PiyasaTahminci().tahmin(girdi)
    tahminler[0]["1"] = 0.99
    assert kaynak["1"] == TEK_TIP["1"]
