"""Skor dağılımı türetmesi (A6, `spor_toto.skor`).

Bulgu **null**: türetilmiş 1X2 piyasayı geçmiyor. Ama testler bulguyu değil
**matematiği** korur — bir gün yeni veriyle tekrar denenirse, o denemenin
altındaki hesabın doğru olduğu bilinmeli. Bozuk bir türetmenin ürettiği
null, "bilgi yok" değil "kod yanlış" demektir ve ikisi ayırt edilemezse
bulgu da değersizdir.
"""

import math

import pytest

from spor_toto.skor import (
    MAKS_GOL,
    ah_kapama,
    beraberlik_duzelt,
    delta_coz,
    fark_dagilimi,
    mu_coz,
    oranlardan_1x2,
    poisson_pmf,
    turetilmis_1x2,
)

SEM = ("1", "0", "2")


# ─── Poisson ──────────────────────────────────────────────────────────────

def test_poisson_bire_toplar():
    for lam in (0.3, 1.0, 2.7, 5.0):
        assert sum(poisson_pmf(lam, k) for k in range(60)) == pytest.approx(1.0)


def test_poisson_bilinen_degerler():
    assert poisson_pmf(1.0, 0) == pytest.approx(math.exp(-1))
    assert poisson_pmf(2.0, 1) == pytest.approx(2 * math.exp(-2))
    assert poisson_pmf(0.0, 0) == 1.0
    assert poisson_pmf(0.0, 3) == 0.0


def test_mu_coz_kendini_tersler():
    """Çözülen μ, verilen üst olasılığını geri üretmeli."""
    for p_ust in (0.20, 0.35, 0.50, 0.65, 0.80):
        mu = mu_coz(p_ust)
        geri = 1.0 - sum(poisson_pmf(mu, k) for k in (0, 1, 2))
        assert geri == pytest.approx(p_ust, abs=1e-6)


def test_mu_ust_olasilikla_artar():
    assert mu_coz(0.30) < mu_coz(0.50) < mu_coz(0.70)


# ─── fark dağılımı ────────────────────────────────────────────────────────

def test_fark_dagilimi_bire_toplar():
    d = fark_dagilimi(1.4, 1.1)
    assert sum(d.values()) == pytest.approx(1.0, abs=1e-6)
    assert min(d) >= -MAKS_GOL
    assert max(d) <= MAKS_GOL


def test_esit_lambda_simetriktir():
    """λ'lar eşitse ev ve deplasman kazanma olasılıkları da eşit olmalı."""
    d = fark_dagilimi(1.3, 1.3)
    ev = sum(v for k, v in d.items() if k > 0)
    dep = sum(v for k, v in d.items() if k < 0)
    assert ev == pytest.approx(dep, abs=1e-9)


# ─── Asya handikabı ───────────────────────────────────────────────────────

def test_sifir_cizgide_beraberlik_iadedir():
    """`h = 0`: D=0 ne kazanç ne kayıp — iki toplama da girmemeli.

    Kıyas 1'e değil **dağılımın kendi kütlesine** yapılıyor: dağılım
    ±`MAKS_GOL`'de kesildiği için 1'e tam toplanmaz (kalan ~3e-9) ve 1'e
    kıyaslayan bir test o kesilmeyi hata sanardı.
    """
    d = fark_dagilimi(1.3, 1.3)
    kazanc, kayip = ah_kapama(d, 0.0)
    assert kazanc + kayip == pytest.approx(sum(d.values()) - d[0], abs=1e-12)
    assert kazanc == pytest.approx(kayip, abs=1e-9)


def test_yarim_cizgide_iade_yoktur():
    d = fark_dagilimi(1.3, 1.1)
    kazanc, kayip = ah_kapama(d, -0.5)
    assert kazanc + kayip == pytest.approx(1.0, abs=1e-6)


def test_ceyrek_cizgi_iki_yarim_bahsin_ortalamasidir():
    """Arşivdeki çizgilerin %53'ü çeyrek — bu dal ana yol, istisna değil."""
    d = fark_dagilimi(1.4, 1.2)
    ceyrek = ah_kapama(d, -0.25)
    sifir = ah_kapama(d, 0.0)
    yarim = ah_kapama(d, -0.5)
    for i in (0, 1):
        assert ceyrek[i] == pytest.approx(0.5 * sifir[i] + 0.5 * yarim[i])


def test_cizgi_agirlastikca_kapama_zorlasir():
    d = fark_dagilimi(1.5, 1.0)
    oranlar = []
    for h in (0.5, 0.0, -0.5, -1.0, -1.5):
        k, ky = ah_kapama(d, h)
        oranlar.append(k / (k + ky))
    assert oranlar == sorted(oranlar, reverse=True)


# ─── supremacy ────────────────────────────────────────────────────────────

def test_delta_coz_kendini_tersler():
    for h, hedef in ((-0.5, 0.55), (0.0, 0.45), (-0.25, 0.52), (-1.0, 0.60)):
        mu = 2.6
        delta = delta_coz(mu, hedef, h)
        lam_ev, lam_dep = (mu + delta) / 2, (mu - delta) / 2
        k, ky = ah_kapama(fark_dagilimi(lam_ev, lam_dep), h)
        assert k / (k + ky) == pytest.approx(hedef, abs=1e-3)


def test_esit_ah_fiyati_sifir_cizgide_esit_lambda_verir():
    delta = delta_coz(2.6, 0.5, 0.0)
    assert delta == pytest.approx(0.0, abs=1e-3)


# ─── türetilmiş 1X2 ───────────────────────────────────────────────────────

def test_turetilmis_bire_toplar():
    p = turetilmis_1x2(0.52, 0.55, -0.25)
    assert p is not None
    assert sum(p.values()) == pytest.approx(1.0)
    assert all(0.0 < v < 1.0 for v in p.values())


def test_denk_macta_lig_taban_oranlarina_yakin():
    """Denk bir maçta türetme, ligin uzun dönem dağılımına yakın olmalı.

    Korpusta gerçekleşen: ev %43,4 · beraberlik %26,1 · deplasman %30,5.
    Bu bir kalibrasyon iddiası değil, **akıl sağlığı** kontrolü: türetme
    çok uzak bir yere düşüyorsa matematikte hata var demektir.
    """
    p = oranlardan_1x2(ust=1.95, alt=1.85, ah_ev=1.90, ah_dep=1.90, h=-0.25)
    assert p is not None
    assert 0.38 < p["1"] < 0.50
    assert 0.22 < p["0"] < 0.30
    assert 0.25 < p["2"] < 0.36


def test_ev_lehine_handikap_ev_olasiligini_buyutur():
    az = oranlardan_1x2(ust=1.95, alt=1.85, ah_ev=1.90, ah_dep=1.90, h=0.0)
    cok = oranlardan_1x2(ust=1.95, alt=1.85, ah_ev=1.90, ah_dep=1.90, h=-1.0)
    assert az is not None and cok is not None
    assert cok["1"] > az["1"]


def test_bozuk_oran_none_doner():
    assert oranlardan_1x2(ust=1.0, alt=1.85, ah_ev=1.9, ah_dep=1.9, h=0.0) is None
    assert oranlardan_1x2(ust=1.95, alt=1.85, ah_ev=0.5, ah_dep=1.9, h=0.0) is None


def test_daha_cok_gol_daha_az_beraberlik():
    az_gol = oranlardan_1x2(ust=1.40, alt=3.00, ah_ev=1.9, ah_dep=1.9, h=0.0)
    cok_gol = oranlardan_1x2(ust=3.00, alt=1.40, ah_ev=1.9, ah_dep=1.9, h=0.0)
    assert az_gol is not None and cok_gol is not None
    # `az_gol` yuksek ust olasiligi = COK gol beklentisi; beraberlik duser.
    assert az_gol["0"] < cok_gol["0"]


# ─── beraberlik düzeltmesi ────────────────────────────────────────────────

def test_duzeltme_bire_toplar():
    p = {"1": 0.44, "0": 0.24, "2": 0.32}
    for rho, beta in ((0.0, 1.0), (0.17, 1.15), (-0.05, 0.9)):
        q = beraberlik_duzelt(p, rho, beta)
        assert sum(q.values()) == pytest.approx(1.0)


def test_rho_beraberligi_buyutur():
    p = {"1": 0.44, "0": 0.24, "2": 0.32}
    assert beraberlik_duzelt(p, 0.20, 1.0)["0"] > p["0"]
    assert beraberlik_duzelt(p, -0.20, 1.0)["0"] < p["0"]


def test_notr_parametreler_dagilimi_degistirmez():
    p = {"1": 0.44, "0": 0.24, "2": 0.32}
    q = beraberlik_duzelt(p, 0.0, 1.0)
    for s in SEM:
        assert q[s] == pytest.approx(p[s])


def test_beta_keskinlestirir():
    """β > 1 en olasıyı büyütür, β < 1 dağılımı düzleştirir."""
    p = {"1": 0.50, "0": 0.25, "2": 0.25}
    assert beraberlik_duzelt(p, 0.0, 1.4)["1"] > p["1"]
    assert beraberlik_duzelt(p, 0.0, 0.6)["1"] < p["1"]
