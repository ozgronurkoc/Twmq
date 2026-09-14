"""`butce_egrisi.py` — haftalık bütçe cephesinin bekçileri.

Korunan iddia: **bütçe büyüdükçe bekleme kısalır ama beklenen harcama
büyür.** O ödünleşme cephenin kendisidir; ters dönerse (harcama da küçülürse)
"daha çok oyna" bedava öğle yemeği olurdu ve tablo yanlış okunurdu.

Sayımın kendisi de tutuluyor: `3¹⁵` basamağında olasılık **tam 1** olmalı —
bütün kolonları almak kesin kazançtır (Mandel, §3.77) ve bu, tavan
hesabının bağımsız sağlamasıdır.
"""
from __future__ import annotations

import pytest

from scripts.butce_egrisi import DUZEYLER, _hafta_egrisi, kos
from spor_toto.coklu import MAC_SAYISI

TUM_KOLON = 3 ** MAC_SAYISI


def _hafta(p_favori: float = 0.5) -> list[dict[str, float]]:
    kalan = (1.0 - p_favori) / 2
    return [{"1": p_favori, "0": kalan, "2": kalan}
            for _ in range(MAC_SAYISI)]


@pytest.fixture(scope="module")
def egri() -> list[float]:
    """Tek koşum, birden çok bekçi — `3¹⁵` dizi kurulumu pahalı."""
    return _hafta_egrisi(_hafta(), [1, 100, 1_000, 21_000, TUM_KOLON])


def test_TUM_kolonlarda_olasilik_TAM_BIR(egri):
    """Kesin kazancın sağlaması: hepsini alırsan tutturursun."""
    assert egri[-1] == pytest.approx(1.0, abs=1e-9)


def test_butce_buyudukce_olasilik_DUSMEZ(egri):
    assert all(a <= b + 1e-15 for a, b in zip(egri, egri[1:]))


def test_tek_kolon_EN_OLASI_kolonun_olasiligi(egri):
    """`N = 1` tam olarak en olası kolondur — burada `p_favori^15`."""
    assert egri[0] == pytest.approx(0.5 ** MAC_SAYISI, rel=1e-9)


def test_olasilik_butceyle_ORANTILI_DEGIL_altinda_buyur(egri):
    """Cephenin ödünleşmesinin kaynağı: `p` içbükey.

    100 kolon, 1 kolonun 100 katı olasılık vermez; 1.000 kolon da 100'ün
    10 katını. Bu doğruysa beklenen harcama (`maliyet / p`) bütçeyle
    **büyür** ve tablo öyle okunur.
    """
    bir, yuz, bin = egri[0], egri[1], egri[2]
    assert yuz < 100 * bir
    assert bin < 10 * yuz


def test_cephe_bekleme_kisalir_harcama_buyur():
    """Tablonun iki yönlü okunuşu — gerçek kesitte, küçük merdivenle."""
    c = kos([1_000, 21_000])
    a, b = c["satirlar"]
    assert b["p"] > a["p"]
    assert b["bekleme_hafta"] < a["bekleme_hafta"]
    assert b["beklenen_harcama"] > a["beklenen_harcama"]


def test_duzey_haftalari_MONOTON_ve_tutarli():
    """%50 < %90 < %99 ve her biri `1 − (1 − p)^H` ile tutarlı."""
    c = kos([21_000])
    r = c["satirlar"][0]
    h = [r["hafta"][f"{d:.0%}"] for d in DUZEYLER]
    assert h == sorted(h)
    for d, hh in zip(DUZEYLER, h):
        assert 1 - (1 - r["p"]) ** hh == pytest.approx(d, abs=1e-9)
