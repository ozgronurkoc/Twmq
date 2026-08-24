"""1X2 dışı pazarların denetimi.

İki tanım bu dosyada kilitleniyor ve ikisi de sessizce ters yazılabilir:

`test_handikap_brier_uretmez` — Asya handikabının Brier'i **yok** ve bu bir
eksiklik değil bir tanım. Çizgilerin %53'ü çeyrek, sonuç ikili değil kesirli
bir getiri, ve kesirli bir sonuca karşı Brier düzgün bir puanlama kuralı
değildir. Biri "eksik" sanıp doldurursa sayı bir şeye benzer ama hiçbir şey
ölçmez.

`test_handikap_bantlari_cizgiye_gore` — handikap bantları olasılığa göre
dilimlenirse eğri hiçbir şey söylemez (539 maçın 531'i tek banda düşüyor,
ölçüldü). Pazarın tanımı gereği olasılık %50'ye çivilidir.
"""
from __future__ import annotations

import pytest

from spor_toto.pazar import (
    ALT_UST_CIZGI,
    BANTLAR,
    CIZGI_DILIMLERI,
    _ah_getiri,
    alt_ust,
    handikap,
    sezon_ozeti,
)


def _satir(**ek) -> dict:
    odds = {"Avg>2.5": 1.90, "Avg<2.5": 1.90,
            "AvgAHH": 1.95, "AvgAHA": 1.95, "AHh": -0.5}
    odds.update(ek.pop("odds", {}))
    return {"week": 1, "no": 1, "home": "A", "away": "B",
            "hg": 1, "ag": 1, "odds": odds, **ek}


# ─── AH getirisi — çeyrek çizgi ve iade ───────────────────────────────────

@pytest.mark.parametrize("fark,h,beklenen", [
    (1, -0.5, 1.0),      # 1 farkla kazandi, -0,5 kapandi
    (0, -0.5, 0.0),      # berabere, -0,5 kapanmadi
    (0, 0.0, 0.5),       # tam sayi cizgide beraberlik IADE
    (1, 0.0, 1.0),
    (-1, 0.0, 0.0),
    (0, -0.25, 0.25),    # ceyrek: yarisi iade, yarisi kayip
    (1, -0.25, 1.0),
    (0, 0.25, 0.75),     # ceyrek: yarisi iade, yarisi kazanc
    # Ceyrek cizgi -1,25 iki yarima bolunur: -1,0 ve -1,5.
    (1, -1.25, 0.25),    # -1,0'da IADE (0,5), -1,5'te kayip (0) -> 0,25
    (2, -1.25, 1.0),     # ikisi de kazanir
])
def test_ah_getirisi_bilinen_durumlar(fark, h, beklenen):
    assert _ah_getiri(fark, h) == pytest.approx(beklenen)


def test_ah_getirisi_araligi_disina_cikmaz():
    for fark in range(-4, 5):
        for h4 in range(-10, 11):
            g = _ah_getiri(fark, h4 / 4.0)
            assert 0.0 <= g <= 1.0


def test_ah_getirisi_cizgi_buyudukce_azalir():
    """Ev sahibine daha ağır handikap = daha az getiri."""
    onceki = 1.0
    for h in (0.5, 0.0, -0.5, -1.0, -1.5, -2.0):
        g = _ah_getiri(1, h)
        assert g <= onceki
        onceki = g


# ─── alt / üst ────────────────────────────────────────────────────────────

def test_alt_ust_olasilik_bire_toplar():
    k = alt_ust(_satir())
    assert set(k["probs"]) == {"ust", "alt"}
    assert sum(k["probs"].values()) == pytest.approx(1.0, abs=1e-9)


def test_alt_ust_sonucu_gollerden_okur():
    assert alt_ust(_satir(hg=2, ag=1))["sonuc"] == "ust"   # 3 > 2,5
    assert alt_ust(_satir(hg=1, ag=1))["sonuc"] == "alt"   # 2 < 2,5
    # 2,5 yarim cizgi: esitlik IMKANSIZ, iade yok.
    assert ALT_UST_CIZGI % 1 == 0.5


def test_alt_ust_kapanis_oranini_tercih_eder():
    k = alt_ust(_satir(odds={"AvgC>2.5": 1.50, "AvgC<2.5": 2.60}))
    ac = alt_ust(_satir())
    assert k["probs"]["ust"] > ac["probs"]["ust"]


def test_alt_ust_eksik_fiyatta_none():
    assert alt_ust(_satir(odds={"Avg>2.5": None})) is None
    assert alt_ust({"odds": {}}) is None


def test_alt_ust_golsuz_macta_sonuc_none_ama_olasilik_var():
    k = alt_ust(_satir(hg=None, ag=None))
    assert k["sonuc"] is None
    assert k["probs"]


def test_alt_ust_marj_pozitif():
    assert alt_ust(_satir())["marj"] > 0


# ─── handikap ─────────────────────────────────────────────────────────────

def test_handikap_cizgi_tipini_dogru_etiketler():
    for h, tip in ((-0.25, "ceyrek"), (0.75, "ceyrek"),
                   (-0.5, "yarim"), (1.5, "yarim"),
                   (0.0, "tam"), (-2.0, "tam")):
        k = handikap(_satir(odds={"AHh": h}))
        assert k["cizgi_tipi"] == tip, (h, k["cizgi_tipi"])


def test_handikap_getiri_alani_sonuc_degil():
    """Alan adı `getiri` — çeyrek çizgide sonuç ikili DEĞİL."""
    k = handikap(_satir(hg=2, ag=1, odds={"AHh": -0.25}))
    assert "sonuc" not in k
    assert 0.0 <= k["getiri"] <= 1.0


def test_handikap_kapanis_cizgisini_tercih_eder():
    k = handikap(_satir(odds={"AHh": -0.5, "AHCh": -1.5}))
    assert k["cizgi"] == -1.5


def test_handikap_eksik_cizgide_none():
    s = _satir()
    del s["odds"]["AHh"]
    assert handikap(s) is None


# ─── sezon özeti ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ozet():
    return sezon_ozeti()


def test_iki_pazar_da_kapsamli(ozet):
    for ad in ("alt_ust", "handikap"):
        assert ozet[ad]["n"] > 300
        assert 0.5 < ozet[ad]["kapsama"] <= 1.0


def test_alt_ust_brier_makul(ozet):
    """İkili Brier ölçeği [0, 2]; bilgisiz tahmin 0,5 verir."""
    b = ozet["alt_ust"]["brier"]
    assert 0.30 < b < 0.50


def test_handikap_brier_uretmez(ozet):
    """**Tanımın bekçisi.** AH'nin Brier'i yok ve sebebi gövdede yazılı."""
    assert ozet["handikap"]["brier"] is None
    assert "ceyrek" in ozet["handikap"]["brier_yok_sebep"]


def test_handikap_bantlari_cizgiye_gore(ozet):
    """**Tanımın bekçisi.** Olasılığa göre dilimlense eğri boş kalırdı."""
    assert ozet["handikap"]["bant_ekseni"] == "cizgi"
    assert ozet["alt_ust"]["bant_ekseni"] == "olasilik"
    kenarlar = {(b["lo"], b["hi"]) for b in ozet["handikap"]["bantlar"]}
    assert kenarlar <= set(CIZGI_DILIMLERI)
    au = {(b["lo"], b["hi"]) for b in ozet["alt_ust"]["bantlar"]}
    assert au <= set(BANTLAR)


def test_handikap_olasiligi_yariya_civili(ozet):
    """Pazarın tanımı: handikap iki tarafı eşitler.

    Bu, bant ekseninin niçin değiştiğinin ölçülmüş gerekçesi.
    """
    for b in ozet["handikap"]["bantlar"]:
        assert 0.45 < b["piyasa"] < 0.55


def test_her_bant_ornegini_tasiyor(ozet):
    from spor_toto.pazar import EN_AZ_BANT

    for ad in ("alt_ust", "handikap"):
        for b in ozet[ad]["bantlar"]:
            assert b["n"] >= EN_AZ_BANT
            assert b["ga_alt"] <= b["gercek"] <= b["ga_ust"]


def test_sinir_govdede_yazili(ozet):
    """Kesitin sınırı katlanmaz — arayüz onu basmak zorunda."""
    assert "SEZON" in ozet["sinir"].upper()


def test_arindirma_yontemi_sonucu_degistirir():
    a = sezon_ozeti("shin")["alt_ust"]["brier"]
    b = sezon_ozeti("orantili")["alt_ust"]["brier"]
    assert a != b


def test_gecersiz_arindirma_reddedilir():
    with pytest.raises(ValueError):
        sezon_ozeti("yok")
