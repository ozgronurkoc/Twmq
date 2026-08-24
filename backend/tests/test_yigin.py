"""Yığınlama denetimi — kat dışılığın bekçisi.

**Asıl test `test_ust_ogrenici_kat_disi_olasilik_goruyor`.** Yığının bütün
değeri buradan gelir: üst-öğrenici tabanları kendi eğitim setlerinde
görürse, en çok ezberleyene en büyük ağırlığı verir.
`DIS_INCELEME_ALPHAPY.md` §4 madde 4'te ölçülen hata tam buydu — klasik
AlphaPy'ın `predict_blend`i örneklem içi olasılıklardan kuruluyor.

İkinci bekçi `test_tek_sezonda_referansa_duser`: kat dışı geçiş
kurulamıyorsa yığın **uydurmaz**, bilinen bir görüşe düşer.
"""
from __future__ import annotations

import pytest

from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.predict import Tahminci
from spor_toto.yigin import YiginTahminci, taban_fabrikalari

PIYASA = {"1": 0.50, "0": 0.25, "2": 0.25}


def _girdi(week: int, results: str, sezon: str) -> dict:
    return {"week": week, "close_date": "2026-01-01", "results": results,
            "probs": [dict(PIYASA)] * MATCH_COUNT, "sezon": sezon,
            "missing": 0, "usable": True}


def _kesit(n_sezon: int = 3, hafta: int = 6) -> list[dict]:
    import random

    rnd = random.Random(9)
    return [_girdi(s * hafta + w,
                   "".join(rnd.choice(SYMBOLS) for _ in range(MATCH_COUNT)),
                   f"s{s}")
            for s in range(n_sezon) for w in range(hafta)]


class _Sabit(Tahminci):
    """Sabit olasılık veren taban — ağırlıkların okunmasını kolaylaştırır."""

    def __init__(self, ad: str, p: dict[str, float]) -> None:
        self.ad = ad
        self._p = p

    def tahmin(self, hafta):
        n = len(hafta["results"])
        return [dict(self._p) for _ in range(n)]


class _Ezberci(Tahminci):
    """Eğitim setini EZBERLER, dışarısında bilgisizdir.

    Kat dışı geçiş çalışıyorsa üst-öğrenici bu tabanı dışarıda görür ve
    ona ağırlık **vermez**. Örneklem içi görseydi kusursuz sanır ve bütün
    ağırlığı ona verirdi.
    """

    ad = "ezberci"

    def __init__(self) -> None:
        self._bellek: dict[int, str] = {}

    def egit(self, haftalar):
        self._bellek = {h["week"]: h["results"] for h in haftalar}

    def tahmin(self, hafta):
        n = len(hafta["results"])
        sonuc = self._bellek.get(hafta["week"])
        if sonuc is None:
            return [dict.fromkeys(SYMBOLS, 1 / 3) for _ in range(n)]
        return [{s: (0.98 if s == sonuc[i] else 0.01) for s in SYMBOLS}
                for i in range(n)]


# ─── sözleşme ─────────────────────────────────────────────────────────────

def test_sozlesme_sekil_ve_toplam():
    tabanlar = [("a", lambda: _Sabit("a", PIYASA)),
                ("b", lambda: _Sabit("b", dict.fromkeys(SYMBOLS, 1 / 3)))]
    t = YiginTahminci(tabanlar)
    t.egit(_kesit())
    for p in t.tahmin(_girdi(99, "1" * MATCH_COUNT, "s0")):
        assert set(p) == set(SYMBOLS)
        assert sum(p.values()) == pytest.approx(1.0, abs=1e-9)


def test_egitilmeden_duzgun_dagilim():
    t = YiginTahminci([("a", lambda: _Sabit("a", PIYASA))])
    for p in t.tahmin(_girdi(1, "1" * MATCH_COUNT, "s0")):
        assert all(v == pytest.approx(1 / 3) for v in p.values())


def test_varsayilan_tabanlar_piyasayla_basliyor():
    """Sıra kasıtlı: referans önce, bağımsız görüşler sonra."""
    adlar = [ad for ad, _ in taban_fabrikalari()]
    assert adlar[0] == "piyasa"
    assert "dixon_coles" in adlar
    assert len(set(adlar)) == len(adlar)


# ─── kat dışılık — asıl bekçi ─────────────────────────────────────────────

def test_ust_ogrenici_kat_disi_olasilik_goruyor():
    """**Asıl bekçi.** Ezberci tabana ağırlık verilmemeli.

    `_Ezberci` eğitim setinde kusursuz, dışarısında bilgisizdir. Kat dışı
    geçiş çalışıyorsa üst-öğrenici onu **dışarıda** görür ve ağırlığı
    sıfıra yakın kalır. Örneklem içi görseydi ağırlık patlardı.
    """
    tabanlar = [("piyasa", lambda: _Sabit("piyasa", PIYASA)),
                ("ezberci", _Ezberci)]
    t = YiginTahminci(tabanlar)
    t.egit(_kesit(n_sezon=3, hafta=8))

    w = t.agirliklar
    assert w is not None
    assert w["ezberci"] < w["piyasa"], (
        f"ezberci tabana fazla agirlik verildi: {w}")
    assert abs(w["ezberci"]) < 0.35


def test_kat_disi_mac_sayisi_kesitin_tamami():
    t = YiginTahminci([("a", lambda: _Sabit("a", PIYASA))])
    haftalar = _kesit(n_sezon=3, hafta=6)
    t.egit(haftalar)
    assert t.kat_disi_mac == len(haftalar) * MATCH_COUNT


def test_tek_sezonda_referansa_duser():
    """Kat dışı geçiş kurulamıyorsa yığın **uydurmaz**."""
    tabanlar = [("piyasa", lambda: _Sabit("piyasa", PIYASA)),
                ("baska", lambda: _Sabit("baska", {"1": 0.2, "0": 0.2, "2": 0.6}))]
    t = YiginTahminci(tabanlar)
    t.egit(_kesit(n_sezon=1, hafta=10))
    assert t.agirliklar is None
    assert t.kat_disi_mac == 0
    # Ilk tabana (referans) dusmeli.
    assert t.tahmin(_girdi(99, "1" * MATCH_COUNT, "s0"))[0] == PIYASA


# ─── ağırlıklar gerçekten öğreniliyor mu ──────────────────────────────────

def test_bilgili_tabana_daha_cok_agirlik():
    """Sonuçları gerçekten bilen bir taban ağırlığı toplamalı.

    Kurgu: sonuçların çoğu "1" ve bir taban "1"e yüksek olasılık veriyor.
    Uydurucu çalışıyorsa o tabanın ağırlığı ötekini geçmeli.
    """
    haftalar = [_girdi(s * 6 + w, "1" * MATCH_COUNT, f"s{s}")
                for s in range(3) for w in range(6)]
    tabanlar = [("kotu", lambda: _Sabit("kotu", {"1": 0.1, "0": 0.1, "2": 0.8})),
                ("iyi", lambda: _Sabit("iyi", {"1": 0.8, "0": 0.1, "2": 0.1}))]
    t = YiginTahminci(tabanlar)
    t.egit(haftalar)
    w = t.agirliklar
    assert w["iyi"] > w["kotu"]


def test_deterministik():
    haftalar = _kesit()
    tabanlar = [("a", lambda: _Sabit("a", PIYASA)),
                ("b", lambda: _Sabit("b", {"1": 0.3, "0": 0.4, "2": 0.3}))]
    a, b = YiginTahminci(tabanlar), YiginTahminci(tabanlar)
    a.egit(haftalar)
    b.egit(haftalar)
    assert a.agirliklar == pytest.approx(b.agirliklar)
    hafta = _girdi(99, "1" * MATCH_COUNT, "s0")
    assert a.tahmin(hafta) == b.tahmin(hafta)


def test_tek_taban_o_tabani_tasir():
    """Tek tabanla yığın o tabandan **ayrışmamalı** (ölçek dışında).

    Tek sütunlu bir softmax, katsayı 1 iken girdiyi aynen taşır. Katsayı
    1'den uzaklaşırsa sıcaklık değişir ama SIRALAMA korunur.
    """
    haftalar = [_girdi(s * 6 + w, "1" * MATCH_COUNT, f"s{s}")
                for s in range(3) for w in range(6)]
    t = YiginTahminci([("a", lambda: _Sabit("a", {"1": 0.6, "0": 0.25, "2": 0.15}))])
    t.egit(haftalar)
    p = t.tahmin(_girdi(99, "1" * MATCH_COUNT, "s0"))[0]
    assert p["1"] > p["0"] > p["2"]


def test_bos_egitim_cokmez():
    t = YiginTahminci([("a", lambda: _Sabit("a", PIYASA))])
    t.egit([])
    assert t.agirliklar is None
    assert len(t.tahmin(_girdi(1, "1" * MATCH_COUNT, "s0"))) == MATCH_COUNT
