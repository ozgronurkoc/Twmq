"""İzotonik kalibrasyon (A5) — eğri, PAV ve tahmincinin sözleşmesi.

Buradaki testler *bulguyu* değil **mekanizmayı** korur: PAV gerçekten monoton
bir dizi üretiyor mu, tahminci eğitilmeden zarar veriyor mu, olasılıklar 1'e
toplanıyor mu. Bulgunun kendisi (geçti/geçmedi) ölçümün işidir ve buraya
sabitlenmez — sabitlenirse test, ölçümün cevabını önceden bilmiş olurdu.
"""

import pytest

from spor_toto.egitim import korpus_haftalari, korpus_yukle
from spor_toto.history import SYMBOLS
from spor_toto.kalibrasyon import BANTLAR, EN_AZ_BANT, kalibrasyon_egrisi
from spor_toto.recalibrate import EN_AZ_KOVA, IzotonikTahminci, _pav

KORPUS = korpus_yukle()
pytestmark = pytest.mark.skipif(
    not KORPUS, reason="egitim korpusu yok (scripts/build_egitim.py)")


@pytest.fixture(scope="module")
def haftalar():
    h = korpus_haftalari()
    if not h:
        pytest.skip("korpus haftalari uretilemedi")
    return h


@pytest.fixture(scope="module")
def egitilmis(haftalar):
    t = IzotonikTahminci()
    t.egit(haftalar)
    return t


# ─── PAV ──────────────────────────────────────────────────────────────────────

def test_pav_monoton_dizi_uretir():
    y = [0.5, 0.1, 0.2, 0.9, 0.3]
    out = _pav([1, 2, 3, 4, 5], y, [1] * 5)
    assert out == sorted(out), "PAV cikrisi monoton artan olmali"
    assert len(out) == len(y)


def test_pav_zaten_monotonu_bozmaz():
    y = [0.1, 0.2, 0.3]
    assert _pav([1, 2, 3], y, [1, 1, 1]) == pytest.approx(y)


def test_pav_agirligi_dikkate_alir():
    """Ağır blok birleşmede ortalamayı kendine çeker."""
    hafif = _pav([1, 2], [0.9, 0.1], [1, 1])
    agir = _pav([1, 2], [0.9, 0.1], [1, 9])
    assert hafif[0] == pytest.approx(0.5)
    assert agir[0] == pytest.approx(0.18)
    assert agir[0] < hafif[0]


def test_pav_toplam_agirlikli_ortalamayi_korur():
    y, w = [0.5, 0.1, 0.2, 0.9], [5.0, 3.0, 2.0, 1.0]
    out = _pav([1, 2, 3, 4], y, w)
    assert (sum(a * b for a, b in zip(out, w))
            == pytest.approx(sum(a * b for a, b in zip(y, w))))


# ─── tahminci sözleşmesi ──────────────────────────────────────────────────────

def test_egitilmeden_piyasayi_oldugu_gibi_gecirir(haftalar):
    """Uydurma bir düzeltme üretmemeli — bilinmiyorsa dokunulmaz."""
    ham = IzotonikTahminci()
    hafta = haftalar[0]
    assert ham.tahmin(hafta) == [dict(b) if b else b for b in hafta["probs"]]


def test_az_veriyle_egri_kurulmaz(haftalar):
    t = IzotonikTahminci()
    t.egit(haftalar[:1])
    assert t.egri == []


def test_egri_monoton_ve_kovalari_yeterli(egitilmis):
    x = [a for a, _ in egitilmis.egri]
    y = [b for _, b in egitilmis.egri]
    assert len(y) >= 10
    assert x == sorted(x)
    assert y == sorted(y)
    assert all(0.0 <= v <= 1.0 for v in y)


def test_tahminler_bire_toplanir(egitilmis, haftalar):
    for hafta in haftalar[:20]:
        for blok in egitilmis.tahmin(hafta):
            assert sum(blok.values()) == pytest.approx(1.0, abs=1e-9)
            assert set(blok) == set(SYMBOLS)


def test_duzeltme_yonu_olculen_yanliligi_izler(egitilmis):
    """Ölçülen sapmanın yönü: favori küçümseniyor, sürpriz abartılıyor.

    Eğri bu yönü taşımalı — yüksek olasılık yukarı, düşük olasılık aşağı
    düzeltilmeli. Ters çevrilirse bu test kırılır.
    """
    assert egitilmis._duzelt(0.75) > 0.75
    assert egitilmis._duzelt(0.10) < 0.10


def test_egri_veri_disinda_duzlesir(egitilmis):
    x = [a for a, _ in egitilmis.egri]
    assert egitilmis._duzelt(0.0) == pytest.approx(egitilmis._duzelt(x[0] / 2))
    assert egitilmis._duzelt(1.0) == pytest.approx(egitilmis._duzelt(
        (x[-1] + 1.0) / 2))


# ─── eğri tablosu ─────────────────────────────────────────────────────────────

def test_egri_belgedeki_sayilari_uretir():
    """`docs §3.18` tablosu buradan üretilir; elle yazılmış sayı yok."""
    e = kalibrasyon_egrisi()
    assert e["n_mac"] == len(KORPUS)
    assert e["n_nokta"] == 3 * len(KORPUS)
    assert e["sapan_bant"] == 10
    assert e["toplam_bant"] == 15
    yuksek = next(r for r in e["bantlar"] if (r["lo"], r["hi"]) == (0.70, 0.80))
    assert yuksek["n"] == 1702
    assert round(100 * yuksek["gercek"], 1) == 78.9
    assert yuksek["piyasa_ga_icinde"] is False


def test_shin_daha_az_bant_saptirir():
    """A5'in asil iddiasi: duzeltme sapan bant sayisini dusuruyor."""
    assert kalibrasyon_egrisi("shin")["sapan_bant"] < \
        kalibrasyon_egrisi("orantili")["sapan_bant"]


def test_ince_bantlar_yazilmaz():
    e = kalibrasyon_egrisi()
    assert all(r["n"] >= EN_AZ_BANT for r in e["bantlar"])
    assert e["toplam_bant"] <= len(BANTLAR)


def test_her_bant_guven_araligiyla_gelir():
    for r in kalibrasyon_egrisi()["bantlar"]:
        assert r["ga_alt"] <= r["gercek"] <= r["ga_ust"]
        assert r["piyasa_ga_icinde"] == (r["ga_alt"] <= r["piyasa"] <= r["ga_ust"])
