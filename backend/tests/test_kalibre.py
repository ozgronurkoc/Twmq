"""Venn-Abers denetimi.

**Asıl bekçi `test_kalibrasyon_sezon_bazli_bolunuyor`.** Venn-Abers'ın
geçerlilik iddiası kalibrasyon kümesinin bağımsızlığına dayanır; zaman
sıralı veride rastgele bir dilim (AlphaPy Pro'nun `cal_size=0.2`si) aynı
sezonun maçlarını hem uydurmaya hem kalibrasyona koyar.

İkinci bekçi `test_aralik_p0_p1_sirali`: `p0 ≤ p1` bir **özdeşliktir**
(aynı noktayı 0 ve 1 etiketiyle eklemek monoton uyumu ancak yukarı iter).
Ters çıkarsa PAV ya da ızgara ara değerleme bozuktur.
"""
from __future__ import annotations

import numpy as np
import pytest

from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.kalibre import (
    EN_AZ_KALIBRASYON,
    VennAbersTahminci,
    _ivap_izgarasi,
)
from spor_toto.predict import PiyasaTahminci

PIYASA = {"1": 0.50, "0": 0.25, "2": 0.25}


def _girdi(week: int, results: str, sezon: str, probs=None) -> dict:
    return {"week": week, "close_date": "2026-01-01", "results": results,
            "probs": list(probs) if probs else [dict(PIYASA)] * MATCH_COUNT,
            "sezon": sezon, "missing": 0, "usable": True}


def _kesit(n_sezon: int = 2, hafta: int = 30) -> list[dict]:
    """Kalibrasyon esiğini geçecek kadar büyük bir kesit."""
    import random

    rnd = random.Random(3)
    return [_girdi(s * hafta + w,
                   "".join(rnd.choice(SYMBOLS) for _ in range(MATCH_COUNT)),
                   f"s{s}")
            for s in range(n_sezon) for w in range(hafta)]


# ─── IVAP ızgarası ────────────────────────────────────────────────────────

def test_aralik_p0_p1_sirali():
    """**Özdeşlik.** `p0 ≤ p1` her ızgara noktasında."""
    rnd = np.random.default_rng(0)
    skorlar = rnd.uniform(0, 1, 400)
    etiketler = (rnd.uniform(0, 1, 400) < skorlar).astype(float)
    izgara = np.linspace(0.05, 0.95, 20)
    p0, p1 = _ivap_izgarasi(skorlar, etiketler, izgara)
    assert (p0 <= p1 + 1e-12).all()
    assert (p0 >= 0).all() and (p1 <= 1).all()


def test_aralik_kalibre_veride_dar():
    """Skor gerçekten kalibre ise aralık dar ve skorun etrafında olmalı."""
    rnd = np.random.default_rng(1)
    skorlar = rnd.uniform(0.1, 0.9, 2000)
    etiketler = (rnd.uniform(0, 1, 2000) < skorlar).astype(float)
    izgara = np.array([0.3, 0.5, 0.7])
    p0, p1 = _ivap_izgarasi(skorlar, etiketler, izgara)
    for i, s in enumerate(izgara):
        assert p1[i] - p0[i] < 0.10
        assert abs((p0[i] + p1[i]) / 2 - s) < 0.15


def test_aralik_az_veride_genis():
    """Kalibrasyon kümesi küçükse aralık **genişlemeli** — bilgisizlik görünür."""
    rnd = np.random.default_rng(2)
    az = rnd.uniform(0, 1, 20)
    cok = rnd.uniform(0, 1, 2000)
    izgara = np.array([0.5])
    ga = _ivap_izgarasi(az, (rnd.uniform(0, 1, 20) < az).astype(float), izgara)
    gc = _ivap_izgarasi(cok, (rnd.uniform(0, 1, 2000) < cok).astype(float), izgara)
    assert (ga[1][0] - ga[0][0]) > (gc[1][0] - gc[0][0])


# ─── tahminci sözleşmesi ──────────────────────────────────────────────────

def test_sozlesme_sekil_ve_toplam():
    t = VennAbersTahminci(izgara=24)
    t.egit(_kesit())
    for p in t.tahmin(_girdi(999, "1" * MATCH_COUNT, "s9")):
        assert set(p) == set(SYMBOLS)
        assert sum(p.values()) == pytest.approx(1.0, abs=1e-9)
        assert all(0.0 <= v <= 1.0 for v in p.values())


def test_egitilmeden_tabani_aynen_tasir():
    """Bilgisizken uydurma düzeltme üretme."""
    t = VennAbersTahminci(izgara=24)
    assert t.tahmin(_girdi(1, "1" * MATCH_COUNT, "s0"))[0] == PIYASA


def test_az_kalibrasyonda_taban_tasinir():
    """`EN_AZ_KALIBRASYON` altında düzeltme yapılmaz."""
    t = VennAbersTahminci(izgara=16)
    t.egit([_girdi(w, "1" * MATCH_COUNT, "s0") for w in range(3)])
    assert 3 * MATCH_COUNT < EN_AZ_KALIBRASYON
    assert t.tahmin(_girdi(9, "1" * MATCH_COUNT, "s0"))[0] == PIYASA


def test_kalibrasyon_sezon_bazli_bolunuyor():
    """**Asıl bekçi.** Kalibrasyon SON sezondan, rastgele dilimden değil.

    Kurgu: iki sezon, taban `piyasa` (öğrenmiyor). Kalibrasyon kümesi
    yalnızca son sezonun maçlarını görmeli — bunu, son sezonun sonuçlarını
    tamamen değiştirdiğimizde modelin değişmesi, ilk sezonunkini
    değiştirdiğimizde DEĞİŞMEMESİ ile sınıyoruz.
    """
    taban = _kesit(n_sezon=2, hafta=40)

    def kur(haftalar):
        t = VennAbersTahminci(izgara=16)
        t.egit(haftalar)
        return t.tahmin(_girdi(999, "1" * MATCH_COUNT, "s9"))[0]

    ilk = kur(taban)

    # Ilk sezonu boz — kalibrasyon SON sezondan geldigi icin degismemeli.
    ilk_bozuk = [dict(h) for h in taban]
    for h in ilk_bozuk:
        if h["sezon"] == "s0":
            h["results"] = "2" * MATCH_COUNT
    assert kur(ilk_bozuk) == pytest.approx(ilk)

    # Son sezonu boz — degismeli.
    son_bozuk = [dict(h) for h in taban]
    for h in son_bozuk:
        if h["sezon"] == "s1":
            h["results"] = "2" * MATCH_COUNT
    assert kur(son_bozuk) != pytest.approx(ilk)


def test_aralik_sembol_basina_doner():
    t = VennAbersTahminci(izgara=16)
    t.egit(_kesit())
    bloklar = t.aralik(_girdi(999, "1" * MATCH_COUNT, "s9"))
    assert len(bloklar) == MATCH_COUNT
    for blok in bloklar:
        assert set(blok) == set(SYMBOLS)
        for p0, p1 in blok.values():
            assert 0.0 <= p0 <= p1 <= 1.0


def test_izgara_sikligi_sonucu_oynatmiyor():
    """Izgara bir **yaklaşıklık**; sıklaştıkça sonuç sabitlenmeli.

    Sabitlenmiyorsa ızgara çok kaba demektir ve `IZGARA` sabiti yeniden
    seçilmelidir — bu test o kararın bekçisi.
    """
    haftalar = _kesit(n_sezon=2, hafta=40)
    hafta = _girdi(999, "1" * MATCH_COUNT, "s9")

    def kur(n):
        t = VennAbersTahminci(izgara=n)
        t.egit(haftalar)
        return t.tahmin(hafta)[0]

    kaba, ince = kur(24), kur(64)
    for s in SYMBOLS:
        assert abs(kaba[s] - ince[s]) < 0.02


def test_deterministik():
    haftalar = _kesit()
    a, b = VennAbersTahminci(izgara=16), VennAbersTahminci(izgara=16)
    a.egit(haftalar)
    b.egit(haftalar)
    hafta = _girdi(999, "1" * MATCH_COUNT, "s9")
    assert a.tahmin(hafta) == b.tahmin(hafta)


def test_taban_degistirilebiliyor():
    """Taban tahminci enjekte edilebilmeli — soru "hangi tabanın üstüne"."""
    t = VennAbersTahminci(taban=PiyasaTahminci, izgara=16)
    t.egit(_kesit())
    assert t.tahmin(_girdi(999, "1" * MATCH_COUNT, "s9"))
