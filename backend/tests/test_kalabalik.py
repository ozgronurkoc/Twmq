"""Kalabalık modelinin denetimi.

Bu modülün manşeti tek bir sayıdır (τ) ve o sayının **yorumu** üç yerde
sessizce ters dönebilir. Üçü de burada kilitleniyor.

`test_tau_bir_ise_prim_tam_bir` — τ = 1, "kalabalık tam piyasayı oynuyor",
yani kenar **yok**. Prim formülü `(p_h/p_f)^(1−τ)` bunu tam olarak 1
vermek zorunda. İşaret ters yazılsaydı (`τ−1`) sayı hâlâ makul görünür,
tablo hâlâ dolar ve eksen **tam tersini** söylerdi: sürprizden kaçmayı
öneren bir araç.

`test_sentetik_tau_geri_kazaniliyor` — uydurucunun kendisi. Bilinen bir
τ ile üretilmiş veriden aynı τ geri çıkmıyorsa gerçek veriden çıkan sayı
da bir şey ölçmüyordur. Bu, ölçüm hattının tek uçtan ucu sağlamasıdır.

`test_asiri_yayilim_araligi_daraltMAZ` — φ aralığı **genişletmek** için
var. Bölme yanlış yöne yazılsaydı τ'nun aralığı ±0,01 çıkar ve sayı
olduğundan kat kat kesin görünürdü.
"""
from __future__ import annotations

import math

import pytest

from spor_toto.history import SYMBOLS
from spor_toto.kalabalik import (
    ASGARI_HAFTA,
    KADEME,
    TAU_ALT,
    TAU_UST,
    _kesit,
    _olabilirlik,
    kalabalik_agirliklari,
    prim,
    tau_olcumu,
    uydur,
)

# ─── kalabalık ağırlıkları ──────────────────────────────────────────────

def test_agirliklar_normalize():
    a = kalabalik_agirliklari({"1": 0.5, "0": 0.3, "2": 0.2}, 1.7)
    assert sum(a.values()) == pytest.approx(1.0)
    assert set(a) == set(SYMBOLS)


def test_tau_bir_ise_kalabalik_piyasanin_ta_KENDISI():
    """τ = 1'in tanımı budur ve kaymışsa her şey kayar."""
    p = {"1": 0.52, "0": 0.26, "2": 0.22}
    a = kalabalik_agirliklari(p, 1.0)
    for s in SYMBOLS:
        assert a[s] == pytest.approx(p[s], abs=1e-12)


def test_tau_buyudukce_favori_agirligi_artar():
    p = {"1": 0.52, "0": 0.26, "2": 0.22}
    onceki = 0.0
    for tau in (0.8, 1.0, 1.3, 1.8, 2.4):
        agirlik = kalabalik_agirliklari(p, tau)["1"]
        assert agirlik > onceki
        onceki = agirlik


def test_beraberlik_kaymasi_yalnizca_beraberligi_iter():
    p = {"1": 0.4, "0": 0.3, "2": 0.3}
    temel = kalabalik_agirliklari(p, 1.0)
    kaymis = kalabalik_agirliklari(p, 1.0, beraberlik=0.5)
    assert kaymis["0"] > temel["0"]
    assert kaymis["1"] < temel["1"] and kaymis["2"] < temel["2"]
    # "1" ile "2" arasindaki ORAN degismemeli: kayma yalnizca "0"a bindi.
    assert kaymis["1"] / kaymis["2"] == pytest.approx(temel["1"] / temel["2"])


# ─── prim: eksenin bütün yorumu bu formülde ─────────────────────────────

def test_tau_bir_ise_prim_tam_bir():
    """τ = 1 ⇒ kenar YOK. Bu satır kırılırsa eksenin işareti tersine döner."""
    for pf, ps in ((0.55, 0.25), (0.5, 0.28), (0.4, 0.32), (0.9, 0.05)):
        assert prim(ps, pf, 1.0) == pytest.approx(1.0)


def test_tau_birden_buyukse_surpriz_primli():
    assert prim(0.25, 0.55, 1.3) > 1.0


def test_tau_birden_kucukse_surpriz_cezali():
    """Ters yön de tutmalı — formül tek yönde doğru yazılmış olabilirdi."""
    assert prim(0.25, 0.55, 0.7) < 1.0


def test_prim_tau_ile_monoton_artar():
    onceki = 0.0
    for tau in (0.6, 0.9, 1.0, 1.2, 1.6, 2.2):
        p = prim(0.25, 0.55, tau)
        assert p > onceki
        onceki = p


def test_ayni_olasilikta_prim_bir():
    """Favoriyi favoriyle değiştirmek hiçbir şey kazandırmaz."""
    assert prim(0.4, 0.4, 1.8) == pytest.approx(1.0)


# ─── uydurucunun kendisi ────────────────────────────────────────────────

def _sentetik(tau_gercek: float, hafta: int = 40,
              n_kolon: float = 3_000_000.0) -> list[dict]:
    """Bilinen bir τ ile üretilmiş kesit.

    Gözlenen kazanan adedi, modelin **tam olarak** öngördüğü ortalamaya
    eşit alınıyor (Poisson gürültüsü yok). Poisson MLE'nin bu veride
    ulaştığı tepe, üreten τ'nun kendisidir — yani test uydurucunun
    yanlılığını ölçer, örneklem şansını değil.

    Olasılıklar haftadan haftaya kasıtlı olarak değiştiriliyor: hepsi aynı
    olsaydı olabilirlik τ'da düz olur ve test her τ'yu kabul ederdi.
    """
    kayitlar = []
    for h in range(hafta):
        maclar = []
        for m in range(15):
            taban = 0.35 + 0.03 * ((h + m) % 8)
            kalan = 1.0 - taban
            probs = {"1": taban, "0": kalan * 0.45, "2": kalan * 0.55}
            kod = SYMBOLS[(h * 7 + m * 3) % 3]
            maclar.append({"probs": probs, "code": kod, "favourite": "1"})
        beklenen = n_kolon * math.exp(sum(
            math.log(kalabalik_agirliklari(m["probs"], tau_gercek)[m["code"]])
            for m in maclar))
        kayitlar.append({
            "sezon": "sentetik", "hafta": h, "maclar": maclar,
            "surpriz": 0, "ger_surpriz": 0, "logp": 0.0, "ort_logp": 0.0,
            "kazanan": {KADEME: beklenen, 14: 0, 13: 0, 12: 1000.0},
            "odul": {15: 1.0, 14: 1.0, 13: 1.0, 12: 1.0},
            # Ofset kapali kullaniliyor: hacim sabit olsaydi bile sezon
            # sabiti onu soguracakti, ama testin olctugu sey tau.
            "hacim": 0.0,
        })
    return kayitlar


@pytest.mark.parametrize("tau_gercek", [0.8, 1.0, 1.3, 1.9])
def test_sentetik_tau_geri_kazaniliyor(tau_gercek):
    u = uydur(_sentetik(tau_gercek), ofset=False)
    assert u is not None
    assert u["tau"] == pytest.approx(tau_gercek, abs=0.01)


def test_sentetik_veride_yayilim_tabanda_ve_aralik_gercegi_kapsiyor():
    """Gürültüsüz veride φ tabana (1) oturur; aralık üreten τ'yu içerir."""
    u = uydur(_sentetik(1.3), ofset=False)
    assert u is not None
    assert u["phi"] == pytest.approx(1.0, abs=0.01)
    assert u["ga_alt"] <= 1.3 <= u["ga_ust"]


def test_aralik_genisligini_belirleyen_sey_kazanan_ADEDI():
    """Aynı τ, daha çok kazanan kolon → daha dar aralık.

    Bu, aralığın gerçekten **bilgiden** geldiğinin sağlamasıdır. Genişlik
    sabit bir sayıdan (ör. yanlışlıkla sabitlenmiş bir eşik) gelseydi
    kolon sayısını yüz kat büyütmek hiçbir şeyi değiştirmezdi.
    """
    dar = uydur(_sentetik(1.3, n_kolon=1e9), ofset=False)
    genis = uydur(_sentetik(1.3, n_kolon=3e6), ofset=False)
    assert dar is not None and genis is not None
    assert (dar["ga_ust"] - dar["ga_alt"]) < (genis["ga_ust"] - genis["ga_alt"])


def test_kucuk_kesit_uydurulmaz():
    assert uydur(_sentetik(1.3, hafta=ASGARI_HAFTA - 1)) is None


def test_olabilirlik_sezon_icinde_toplami_korur():
    """α_s'nin kapalı formu: sezon içinde Σ gözlenen = Σ beklenen."""
    kayitlar = _sentetik(1.4)
    kesit = _kesit(kayitlar, ofset=False)
    _, mu = _olabilirlik(kesit, 1.1)
    assert sum(mu) == pytest.approx(
        sum(k["kazanan"][KADEME] for k in kayitlar), rel=1e-9)


def test_asiri_yayilim_araligi_daraltMAZ():
    """φ ≥ 1 kırpması: eksik yayılım aralığı daraltamaz."""
    u = uydur(_sentetik(1.3), ofset=False)
    assert u is not None
    assert u["phi"] >= 1.0


# ─── gerçek veri: manşet ve sağlaması ───────────────────────────────────

def test_gercek_kesitte_tau_kenarda_degil():
    """Arama penceresine dayanan bir τ, ölçüm değil kırpmadır."""
    t = tau_olcumu()["tam"]
    assert TAU_ALT < t["tau"] < TAU_UST
    assert t["kenarda"] is False


def test_gercek_kesitte_asiri_yayilim_gizlenmiyor():
    """φ ≈ 390 — Poisson bu veride tutmuyor ve gövde bunu söylüyor."""
    t = tau_olcumu()["tam"]
    assert t["phi"] > 10, "φ ≈ 1 çıkıyorsa ölçek yanlış hesaplanıyor"


def test_saglama_katlari_birlikte_donuyor():
    """Manşet tek başına okunamasın: üç kat aynı gövdede."""
    o = tau_olcumu()
    assert o["tam"]["n"] > o["kesit"] - 1
    assert len(o["sezon_disarida"]) >= 2
    assert len(o["tek_sezon"]) >= 2
    s = o["saglama"]
    assert s["uyum"] == 1 + len(o["sezon_disarida"]) + len(o["tek_sezon"])
    assert s["tau_alt"] <= o["tam"]["tau"] <= s["tau_ust"]


def test_govde_mutlak_getiri_iddia_etmiyor():
    """RTP ölçülmedi; 'kâr' cümlesi gövdeye asla girmemeli."""
    sinir = tau_olcumu()["sinir"]
    assert "kâr demek değil" in sinir
    assert "RTP" in sinir


def test_genisletilmis_uyum_mansete_girmiyor():
    """İki fazladan parametre ayrı blokta durur, `tam` onları görmez."""
    o = tau_olcumu()
    assert "beraberlik" not in o["tam"]
    assert "beraberlik" in o["genisletilmis"]
