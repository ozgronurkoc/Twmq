"""`sistem_kiyasi.py` bekçileri — sökümün gerekçesi ölçülü kalsın.

**Bu dosya Aşama 2'de kaplama gövdesiyle birlikte silinecek** ve bu bilinerek
yazıldı: kaplama sökülünce kıyas koşamaz olur. O ana kadar bekçi, geçiş
kararının dayandığı iki sayıyı tutar — biri deponun bilinen bulgusunun yeniden
üretimi, öteki kararın kendisi. Sayılar `docs/DUZ_SISTEME_GECIS.md`e
dondurulduğu için silinmeleri kaydı yok etmez.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from scripts.butce_kademeleri import hafta_olasiliklari
from scripts.sistem_kiyasi import dogrula, en_iyi_sekil, odul_tablosu

DORT_SEKIZ_UC = ["10", "10", "1", "102", "102", "10", "02", "12", "1", "1",
                 "02", "12", "12", "102", "2"]


@pytest.fixture(scope="module")
def odul():
    return odul_tablosu("2026_27", 1)


@pytest.fixture(scope="module")
def probs3():
    return hafta_olasiliklari(3, "2026_27")


def test_AYNI_isaretler_iki_sistemde_kolon_basina_AYNI(probs3, odul):
    """§3.40'ın doğrusallığı — kıyasın ön şartı.

    Tutmazsa `en_iyi_sekil`in kaplama tarafında kullandığı 1/8 kısayolu
    geçersizdir ve bütün kıyas çöker. Kaplama tarafı burada kaba kuvvetle
    sayılır, yani kısayol bağımsız olarak sınanmış olur.
    """
    d = dogrula(probs3, DORT_SEKIZ_UC, odul)
    assert d["fix16_kolon"] == 864
    assert d["duz_kolon"] == 6912
    sapma = abs(d["fix16_birim"] - d["duz_birim"]) / d["duz_birim"]
    assert sapma < 0.01, f"kolon başına beklenti ayrıştı: %{100*sapma:.2f}"


def test_duz_her_butcede_kaplamayi_geciyor(probs3, odul):
    """Sökümün gerekçesi: aynı kolon bütçesinde düz önde — E[TL] ve P(≥12).

    Dar tutuldu: yön ve alt sınır sınanır, kesirli basamak değil.
    """
    for tavan in (16, 64, 256, 864, 3888, 10368, 59049):
        dz = en_iyi_sekil(probs3, tavan, "duz", odul)
        fx = en_iyi_sekil(probs3, tavan, "fix16", odul)
        assert dz and fx, f"tavan {tavan}: şekil bulunamadı"
        assert dz["tl"] > fx["tl"], f"tavan {tavan}: düz geride"
        assert dz["p12"] > fx["p12"], f"tavan {tavan}: düz P(≥12)'de geride"
        assert dz["kolon"] <= tavan and fx["kolon"] <= tavan


def test_kaplamanin_en_az_yedi_cifte_sarti_sekli_ZORLUYOR(probs3, odul):
    """Farkın sebebi: kaplama yayvan kalmak zorunda, düz yoğunlaşabiliyor.

    Bu bir açıklama değil **ölçüm**: 864 kolonda kaplamanın en iyisi 8 çifte
    taşırken düzünki 5'te kalıyor, tek sayısı 4'ten 7'ye çıkıyor.
    """
    dz = en_iyi_sekil(probs3, 864, "duz", odul)
    fx = en_iyi_sekil(probs3, 864, "fix16", odul)
    assert fx["sekil"][1] >= 7, "fix16 yedi çifteden az taşıyamaz"
    assert dz["sekil"][0] > fx["sekil"][0], "düz daha yoğun olmalı"
