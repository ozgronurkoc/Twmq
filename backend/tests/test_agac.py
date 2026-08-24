"""Gradyan artırmalı ağaç tahmincisinin denetimi.

**En kritik test `test_egitilmemis_agac_piyasayi_aynen_tasir` ile
`test_init_score_gercekten_ekleniyor`.** İkisi de aynı sessiz hatayı
kovalıyor: `init_score` ile eğitilen bir LightGBM modelinin
`predict_proba`sı başlangıç skorunu **eklemez**. Unutulursa model piyasayı
hiç görmemiş gibi tahmin eder, ölçüm çalışır görünür ve bambaşka bir şeyi
ölçer — "ağaç piyasanın artığını öğrenemiyor" diye okunur, oysa ağaca
piyasa hiç verilmemiştir.

Testler `lightgbm` yoksa atlanır: paket `model` ekstrasındadır ve üretim
bağımlılığı değildir.
"""
from __future__ import annotations

import numpy as np
import pytest

from spor_toto.history import MATCH_COUNT, SYMBOLS

lgb = pytest.importorskip("lightgbm")

from spor_toto.agac import (
    ADAYLAR,
    OZELLIK_ALANLARI,
    SABIT,
    AgacTahminci,
    _tasarim,
    fabrikalar,
)

PIYASA = {"1": 0.50, "0": 0.25, "2": 0.25}


def _girdi(week: int, results: str, probs=None) -> dict:
    return {"week": week, "close_date": "2026-01-01", "results": results,
            "probs": list(probs) if probs else [dict(PIYASA)] * MATCH_COUNT,
            "missing": 0, "usable": True, "sezon": f"{20 + week % 4}xx"}


def _kesit(n_sezon: int = 3, hafta: int = 8) -> list[dict]:
    """Sezon etiketi taşıyan sözde-haftalar — iç halkanın çalışabilmesi için."""
    import random

    rnd = random.Random(5)
    out = []
    for s in range(n_sezon):
        for w in range(hafta):
            sonuc = "".join(rnd.choice(SYMBOLS) for _ in range(MATCH_COUNT))
            g = _girdi(s * hafta + w, sonuc)
            g["sezon"] = f"sezon{s}"
            out.append(g)
    return out


# ─── sözleşme ─────────────────────────────────────────────────────────────

def test_sozlesme_sekil_ve_toplam():
    t = AgacTahminci()
    t.egit(_kesit())
    tahminler = t.tahmin(_girdi(99, "1" * MATCH_COUNT))
    assert len(tahminler) == MATCH_COUNT
    for p in tahminler:
        assert set(p) == set(SYMBOLS)
        assert sum(p.values()) == pytest.approx(1.0, abs=1e-9)
        assert all(0.0 <= v <= 1.0 for v in p.values())


def test_egitilmemis_agac_piyasayi_aynen_tasir():
    """Bilgisizken uydurma düzeltme üretme — `predict` modülünün kuralı."""
    t = AgacTahminci()
    for p in t.tahmin(_girdi(1, "1" * MATCH_COUNT)):
        assert p == PIYASA


def test_bos_egitim_seti_cokmez():
    t = AgacTahminci()
    t.egit([])
    assert t.tahmin(_girdi(1, "1" * MATCH_COUNT))[0] == PIYASA


def test_iki_fabrika_farkli_ad_veriyor():
    adlar = [f().ad for f in fabrikalar()]
    assert adlar == ["agac", "agac_ham"]


def test_fabrikalar_taze_ornek_verir():
    for f in fabrikalar():
        assert f() is not f()


# ─── init_score — sessiz hatanın bekçisi ──────────────────────────────────

def test_init_score_gercekten_ekleniyor():
    """**Asıl bekçi.** Piyasa fiyatı değişince tahmin de değişmeli.

    `init_score` unutulursa (ya da `predict_proba` kullanılırsa) model
    piyasayı hiç görmemiş gibi davranır ve aynı özelliklerde aynı sayıyı
    verir. Burada özellikler sabit, yalnızca fiyat değişiyor.
    """
    haftalar = _kesit()
    t = AgacTahminci()
    t.egit(haftalar)

    favori_ev = [{"1": 0.75, "0": 0.15, "2": 0.10}] * MATCH_COUNT
    favori_dep = [{"1": 0.10, "0": 0.15, "2": 0.75}] * MATCH_COUNT
    a = t.tahmin(_girdi(99, "1" * MATCH_COUNT, favori_ev))
    b = t.tahmin(_girdi(99, "1" * MATCH_COUNT, favori_dep))

    assert a[0]["1"] > b[0]["1"], "fiyat degisti, tahmin degismedi — init_score kayip"
    # Ve piyasadan cok uzaklasmamali: agac ARTIGI ogreniyor, fiyati degil.
    assert abs(a[0]["1"] - 0.75) < 0.35


def test_ham_agac_init_score_kullanmaz():
    """`agac_ham` başlangıç skoru almaz; iki tahminci ayrışmalı."""
    haftalar = _kesit()
    a, b = AgacTahminci(), AgacTahminci(piyasadan_basla=False)
    a.egit(haftalar)
    b.egit(haftalar)
    hafta = _girdi(99, "1" * MATCH_COUNT,
                   [{"1": 0.75, "0": 0.15, "2": 0.10}] * MATCH_COUNT)
    assert a.tahmin(hafta)[0] != b.tahmin(hafta)[0]


# ─── iç halka ─────────────────────────────────────────────────────────────

def test_ic_halka_kosuyor_ve_sezon_sayisini_bildiriyor():
    t = AgacTahminci()
    t.egit(_kesit(n_sezon=3))
    assert t.arama is not None
    assert t.arama["arandi"] is True
    assert t.arama["n_kat"] == 3
    assert t.arama["parametreler"] in ADAYLAR


def test_tek_sezonda_arama_yapilmaz_varsayilan_kullanilir():
    """İç halka kurulamıyorsa ayar YAPILMAZ ve sebep yazılır."""
    haftalar = _kesit(n_sezon=1, hafta=12)
    t = AgacTahminci()
    t.egit(haftalar)
    assert t.arama["arandi"] is False
    assert t.arama["parametreler"] == ADAYLAR[0]
    assert t.arama["sebep"]


def test_egitim_deterministik():
    """Aynı veri aynı tahmini vermeli — 'ölçtük' demenin ön koşulu."""
    haftalar = _kesit()
    hafta = _girdi(99, "1" * MATCH_COUNT)
    a, b = AgacTahminci(), AgacTahminci()
    a.egit(haftalar)
    b.egit(haftalar)
    assert a.tahmin(hafta) == b.tahmin(hafta)


def test_sabit_ayarlar_tekrarlanabilirligi_kuruyor():
    assert SABIT["random_state"] is not None
    assert SABIT["deterministic"] is True
    assert SABIT["num_class"] == len(SYMBOLS)


def test_adaylar_basitten_karmasiga_sirali():
    """Sıra kasıtlı: eşitlikte `izgara_ara` ilkini seçer, yani az kapasiteyi."""
    yapraklar = [a["num_leaves"] for a in ADAYLAR]
    assert yapraklar == sorted(yapraklar)
    assert len(set(yapraklar)) == len(yapraklar)


# ─── tasarım matrisi ──────────────────────────────────────────────────────

def test_tasarim_sekli_ve_ham_skoru():
    ozellikler = [{"probs": {"1": 0.5, "0": 0.3, "2": 0.2},
                   **dict.fromkeys(OZELLIK_ALANLARI, 1.0)}]
    X, ham = _tasarim(ozellikler)
    assert X.shape == (1, len(OZELLIK_ALANLARI) + len(SYMBOLS))
    assert ham.shape == (1, len(SYMBOLS))
    assert ham[0, 0] == pytest.approx(np.log(0.5))
    # Fiyat X'te de duruyor: agacin NEREDE sapmasi gerektigini bilmesi icin.
    assert X[0, len(OZELLIK_ALANLARI)] == pytest.approx(0.5)


def test_tasarim_eksik_alani_notr_okur():
    X, ham = _tasarim([{"probs": None}])
    assert not np.isnan(X).any()
    assert ham[0, 0] == pytest.approx(np.log(1 / 3))


def test_tasarim_sifir_olasiligi_tabana_kirpar():
    _, ham = _tasarim([{"probs": {"1": 0.0, "0": 0.5, "2": 0.5}}])
    assert np.isfinite(ham).all()


def test_ozellik_kumesi_kademeyle_ayni():
    """Ağaç ile kademe **aynı** özellikleri görmeli.

    Aksi halde "ağaç mı kademe mi daha iyi" sorusu model sınıfını değil
    özellik farkını ölçerdi.
    """
    from spor_toto.recalibrate import YON_ALANLARI

    yon = {alan for alan, _ in YON_ALANLARI}
    assert yon <= set(OZELLIK_ALANLARI), yon - set(OZELLIK_ALANLARI)
