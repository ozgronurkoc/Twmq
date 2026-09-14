"""Önceden yazılmış durma kurallarının **koşulabilirliği** — bekçiler.

`scripts/durma_kurallari.py` karar vermez, eşiğin neresinde olduğumuzu
yazar. Buradaki testler iki şeyi tutar: hesap doğru mu (sentetik), ve
bugünkü cevap ne (canlı kayıt). İkincisi kırıldığında yapılacak şey testi
düzeltmek değil, **kuralın karşılanıp karşılanmadığına bakmaktır**.
"""

import importlib
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data" / "super_toto" / "2026_27"

pytestmark = pytest.mark.skipif(
    not (VERI / "hafta_05.json").exists(),
    reason="canli sezon verisi yok")


@pytest.fixture(scope="module")
def mod():
    return importlib.import_module("scripts.durma_kurallari")


@pytest.fixture(scope="module")
def o(mod):
    return mod.rapor()


def test_canli_kesit_SONUCU_OLAN_haftalardan_kuruluyor(mod, o):
    """Sonucu girilmemiş hafta kesite girmez — yoksa `tuttu` uydurulurdu."""
    assert o["canli_mac"] == 15 * o["canli_hafta"]
    assert o["canli_hafta"] >= 5


def test_iki_kural_da_BUGUN_gecmiyor(o):
    """5. hafta sonrası durum — ve niçin kuralın *yazılmış* olması önemli.

    4. hafta üç kaçağını orta favori bandında verdi, 5. hafta üçünü
    bankoda (ikisi yine o bantta). İki hafta üst üste aynı yere düşen bir
    kayıp, düzeltme koymak için en güçlü sezgiyi üretir — ve bu test tam
    o anda "hayır" diyen şeydir.
    """
    for k in o["kurallar"]:
        assert k["gecti"] is False, k


def test_banko_kurali_ESIGIN_ALTINDA_ve_isaret_TERS(o):
    """§3.64: `n` yetmiyor, ve canlı sezon tarihsel sapmayı DOĞRULAMIYOR.

    Tarihsel etki dört sezon boyunca **artı** yöndeydi (+%5 ile +%10):
    piyasa favoriyi ucuza satıyordu. Canlı sezonun T1 banko rejimi
    **eksi** veriyor (−9,2 puan, n = 25). Yani 2022–2024 üzerinde
    kalibre edilmiş bir düzeltme bu sezon işleri KÖTÜLEŞTİRİRDİ; kuralın
    beklettiği şey bir titizlik değil, ölçülmüş bir zarar.
    """
    k = next(x for x in o["kurallar"] if x["kural"].startswith("§3.64"))
    assert k["n_yeterli"] is False
    assert k["havuzlanmis"]["n"] < k["esik_n"]
    assert k["2025_26"]["acik"] > 0        # tarihsel yon: arti
    assert k["2026_27"]["acik"] < 0        # canli yon: eksi


def test_orta_favori_kurali_ARSIVDE_TERS_yonde(o):
    """§3.65: bant canlı sezonda çöküyor, arşivde ÇÖKMÜYOR.

    Canlı: n = 38, açık −17,6 puan. 2025/26 kupon kesiti: n = 266, açık
    **+4,7 puan** — ters yön ve yedi kat örneklem. Bu, "iki haftadır aynı
    yerde kaybediyoruz" sezgisinin niçin bir düzeltmeye dönüşemeyeceğinin
    tek cümlelik cevabıdır.
    """
    k = next(x for x in o["kurallar"] if x["kural"].startswith("§3.65"))
    assert k["n_yeterli"] is False
    assert k["arsivde_de_var"] is False
    assert k["2026_27"]["acik"] < 0
    assert k["2025_26_arsiv"]["acik"] > 0
    assert k["2025_26_arsiv"]["n"] > k["2026_27"]["n"]


def test_rejim_siniri_CANLI_SEZONDAN_kesilmiyor(mod, o):
    """Eşik kupon kesitinden gelir; canlı ortancadan kesilseydi kayardı.

    Canlı sezonun kendi ortancası her hafta yer değiştirir ve havuzlama
    iki farklı rejimi toplamış olurdu. Sınır bu yüzden sabit bir sayıdır
    ve kaydın içinde durur.
    """
    k = next(x for x in o["kurallar"] if x["kural"].startswith("§3.64"))
    canli = mod.canli_satirlar()
    t1 = sorted(x["p"] for x in canli if x["lig"] == "T1")
    canli_ortanca = t1[len(t1) // 2]
    assert k["rejim_esigi_p"] != pytest.approx(canli_ortanca, abs=1e-9)
    assert 0.3 < k["rejim_esigi_p"] < 0.7
