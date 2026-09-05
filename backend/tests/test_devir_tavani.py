"""`devir_tavani.py` bekçileri — belgedeki sayı ölçümle örtüşmeli.

**Neden var.** `docs/DIS_TARAMA_PIYASAYI_YENME.md` §4 bir eksen kapatıyor
("devir yetmiyor") ve o kapanış **tek bir sayıya** dayanıyor: altı sezonun
azami devir çarpanı 1,645. Arşive bir sezon eklendiğinde o sayı değişir ve
belgenin sonucu sessizce yanlışlanabilir hâle gelir. Bu depoda aynı kusurun
bekçisiz kalan kopyaları daha önce üç kez bulundu (`test_belgeler.py`).

Kasıtlı olarak dar: yönü tutar, kesirli basamağı değil.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
DEPO = KOK.parent
BELGE = DEPO / "docs" / "DIS_TARAMA_PIYASAYI_YENME.md"

sys.path.insert(0, str(KOK))
from scripts.devir_tavani import OLCULEN_ORT_GETIRI, devir_tavani, ev_kurali


@pytest.fixture(scope="module")
def devir():
    return devir_tavani()


@pytest.fixture(scope="module")
def evk():
    return ev_kurali()


def test_devir_carpani_belgedeki_azamiyle_ayni(devir):
    """§4.2'nin **azami 1,645** satırı ölçümle örtüşmeli."""
    assert devir["n"] >= 200, "arşiv beklenenden küçük"
    assert devir["azami_carpan"] == pytest.approx(1.645, abs=0.005)


def test_devir_ekseninin_KAPANISI_hala_gecerli(devir):
    """Asıl bekçi: azami çarpan, gereken çarpanın **altında** kalmalı.

    Belgenin bütün sonucu bu eşitsizliktir. Arşiv büyüyüp azami devir
    yükselirse burası kırılır ve §4.3 yeniden yazılmak zorunda kalır —
    tam olarak istenen davranış.
    """
    for k in devir["kosul"]:
        assert not k["ulasildi"], (
            f"devir ekseni AÇILDI: ödeme %{100 * k['ima_edilen_odeme_orani']:.1f} "
            f"iken gereken {k['gereken_carpan']:.2f}, azami "
            f"{devir['azami_carpan']:.3f} — belge §4.3 yeniden yazılmalı")


def test_odeme_orani_bandi_tek_sayiya_indirilmedi():
    """Doktrin 2: ölçülmeyen `odeme_orani` uydurulmaz, band bırakılır."""
    assert len(OLCULEN_ORT_GETIRI) == 2
    assert OLCULEN_ORT_GETIRI[0] < OLCULEN_ORT_GETIRI[1]


def test_ev_kurali_piyasa_favorisinden_ZAYIF(evk):
    """§5: "hep ev" kuralı korpusta piyasa favorisini geçemez."""
    if not evk.get("n"):
        pytest.skip("eğitim korpusu bu kurulumda yok")
    assert evk["ev_orani"] < evk["favori_isabeti"]
    # Makalenin dayandığı %50,4 bu kesitin %95 aralığının DIŞINDA.
    assert evk["ev_ga"][1] < evk["makalenin_orani"]


def test_belgedeki_ev_orani_olculenle_ayni(evk):
    """§5 tablosundaki **%43,37** satırı ölçümle örtüşmeli."""
    if not evk.get("n"):
        pytest.skip("eğitim korpusu bu kurulumda yok")
    metin = BELGE.read_text(encoding="utf-8")
    yazili = {x.replace(",", ".") for x in re.findall(r"\*\*%(4\d,\d\d)\*\*", metin)}
    assert f"{100 * evk['ev_orani']:.2f}" in yazili, (
        f"belge {sorted(yazili)} diyor, ölçüm %{100 * evk['ev_orani']:.2f}")
