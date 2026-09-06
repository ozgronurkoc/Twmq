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


def test_sezonda_iki_amac_HER_HAFTA_ayrisiyor(sezon):
    """Düzde iki amaç dört haftanın dördünde de farklı kupon veriyor.

    **Bu bekçi ters çevrildi ve sebebi ölçüm.** Kaplama ölçeğinde iki amaç
    dört haftanın dördünde de *aynı* kuponu veriyordu (kütükte "0/4 ayrışma"
    diye duruyor ve o kayıt silinmedi, "kaplama ölçeği" diye etiketlendi).
    Düze geçince tablo tersine döndü: dördünde de ayrışıyorlar.

    Sebebi yapısal. Kaplamada bedel `2^a·3^b/8` idi ve yedi çifte şartı
    şekli zaten daraltıyordu; iki amacın manevra alanı dardı. Düzde alan
    açıldı ve `E[k]` enküçükleme ile kuyruk enbüyükleme birbirinden
    görünür biçimde ayrıldı.
    """
    ayrisan = {h["hafta"]: h["ayrisan"] for h in sezon if h["ayrisan"]}
    assert len(ayrisan) == len(sezon), (
        f"ayrışmayan hafta çıktı: {[h['hafta'] for h in sezon if not h['ayrisan']]}")


def test_duz_motorun_olculmus_planlari(sezon):
    """Motor, düz ölçeğinde ölçülmüş planları yeniden üretmeli.

    **Bu test eskiden dondurulmuş kuponları sınıyordu** (3. hafta 864 kolon
    / P=0,3809 · 4. hafta 3.888 / P=0,4670). O kuponlar kaplama motoruyla
    kurulmuştu ve motor düze geçince aynı bütçede aynı planı vermesi için
    hiçbir sebep kalmadı — testin dayanağı katmanla birlikte gitti. Kayıt
    silinmedi: kuponlar `hafta_0*_kupon.json`da duruyor ve kütükte "kaplama
    ölçeği" diye etiketli.

    Yerine geçen şey aynı işi görüyor: düz motorun ölçülmüş çıktısı.
    """
    beklenen = {3: (972, 0.5171), 4: (5832, 0.6055)}
    for h in sezon:
        if h["hafta"] not in beklenen:
            continue
        bedel, p = beklenen[h["hafta"]]
        assert h["hedef_bedel"] == bedel, f'{h["hafta"]}. hafta bedeli'
        assert h["hedef_p"] == pytest.approx(p, abs=0.0001)


def test_rastgele_ayrisma_sikligi_kutukle_ayni(rastgele):
    """Kütükteki *"306/400"* satırının bekçisi — tohum sabit, sayı sabit.

    Kaplama ölçeğinde bu sayı **61/400**'dü. Aradaki fark ölçümün kendisi:
    düzde iki amaç beş kat daha sık ayrışıyor.
    """
    assert rastgele["hafta"] == 400
    assert rastgele["ayrisan"] == 306


def test_EN_AZ_KACAK_okumasi_hedefi_HICBIR_haftada_gecemez(rastgele):
    """Asıl değişmez: `en_iyi_secim` kesin çözer, rakip amaç onu geçemez.

    Sayı değil kural sınanıyor; ihlali `secim.py`de hata demektir.
    """
    assert rastgele["kayip_min"] >= 0.0, (
        "rakip amaç hedefi geçti — `en_iyi_secim` kesin çözmüyor demektir")
    assert rastgele["kayip_ort"] == pytest.approx(0.02259, abs=0.00005)
    assert rastgele["kayip_max"] == pytest.approx(0.09844, abs=0.00005)
