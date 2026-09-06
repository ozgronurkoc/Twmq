""" `amac_kiyasi.py` bekçileri — "en az kaçak" okuması kuralı geçemez.

**Neden var.** Kural anlatılırken `P(k ≤ eşik)` neredeyse her seferinde
*"en az kaçağı seçiyor"* diye okunuyor. Kütükte artık iki sayı duruyor:
bu sezonun 4 haftasında iki amaç **aynı** kuponu veriyor, rastgele 400
haftanın **61'inde** ayrışıyor. İkisi de bir betiğin çıktısı ve bekçisiz
kalırsa `secim.py`de yapılacak bir değişiklik onları sessizce bayatlatır.

Asıl bekçi üçüncüsü ve bir **değişmez**dir: `en_iyi_secim` kesin çözdüğü
için rakip amacın planı `P(k ≤ eşik)`te onu hiçbir haftada geçemez. Bu
sayı değil kuraldır — geçerse betikte değil `secim.py`de hata var demektir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from scripts.amac_kiyasi import rastgele_kiyas, sezon_kiyasi


@pytest.fixture(scope="module")
def sezon():
    return sezon_kiyasi()


@pytest.fixture(scope="module")
def rastgele():
    return rastgele_kiyas(400, 7)


def test_sezonun_haftalari_kurulabiliyor(sezon):
    """Dondurulmuş her haftada iki amaç da bir plan üretmeli."""
    assert len(sezon) >= 4, "hafta dosyaları okunamadı"
    assert all(h["hedef_picks"] and h["enaz_picks"] for h in sezon)


def test_sezonda_iki_amac_AYNI_kuponu_veriyor(sezon):
    """Kütükteki *"4/4 hafta ayrışmıyor"* satırının bekçisi.

    Ayrışma çıkarsa sayı bayatlamıştır: kütük güncellenir, test değil.
    """
    ayrisan = {h["hafta"]: h["ayrisan"] for h in sezon if h["ayrisan"]}
    assert not ayrisan, f"ayrışan hafta çıktı: {ayrisan}"


def test_hedef_kuralinin_3_ve_4_hafta_kuponunu_BIREBIR_verdigi(sezon):
    """Aynı ölçekte (shin) kurulan iki hafta dondurulmuş kuponu vermeli.

    1. ve 2. hafta `orantili` ile dondurulduğu için kapsam dışı — betiğin
    başlığındaki ölçek uyarısının testteki karşılığı budur.
    """
    beklenen = {3: (864, 0.3809), 4: (3888, 0.4670)}
    for h in sezon:
        if h["hafta"] not in beklenen:
            continue
        bedel, p = beklenen[h["hafta"]]
        assert h["hedef_bedel"] == bedel, f'{h["hafta"]}. hafta bedeli'
        assert h["hedef_p"] == pytest.approx(p, abs=0.0001)


def test_rastgele_ayrisma_sikligi_kutukle_ayni(rastgele):
    """Kütükteki *"61/400"* satırının bekçisi — tohum sabit, sayı sabit."""
    assert rastgele["hafta"] == 400
    assert rastgele["ayrisan"] == 61


def test_EN_AZ_KACAK_okumasi_hedefi_HICBIR_haftada_gecemez(rastgele):
    """Asıl değişmez: `en_iyi_secim` kesin çözer, rakip amaç onu geçemez.

    Sayı değil kural sınanıyor; ihlali `secim.py`de hata demektir.
    """
    assert rastgele["kayip_min"] >= 0.0, (
        "rakip amaç hedefi geçti — `en_iyi_secim` kesin çözmüyor demektir")
    assert rastgele["kayip_ort"] == pytest.approx(0.00214, abs=0.00005)
    assert rastgele["kayip_max"] == pytest.approx(0.00862, abs=0.00005)
