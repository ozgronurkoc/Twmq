"""Faz 1 — kenar durum ve girdi dogrulama testleri."""

from __future__ import annotations

import math

import pytest

from spor_toto.analysis import monte_carlo_report
from spor_toto.bayes import (
    bayes_update_matches,
    default_prior,
    dirichlet_posterior,
    prior_mean,
)
from spor_toto.cli import main
from spor_toto.core import (
    SEMBOLLER,
    Encoder,
    parse_picks,
    parse_probs,
)
from spor_toto.duz import kolonlar as duz_kolonlar

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


from tests.conftest import esit_olasiliklar as _uniform_probs  # tek kaynak


def test_picks_bos():
    with pytest.raises(ValueError, match="bos"):
        parse_picks("")
    with pytest.raises(ValueError, match="bos"):
        parse_picks("   ")


def test_picks_bos_slot_ortada():
    """Bos slot sessizce atlanmamali."""
    with pytest.raises(ValueError, match="bos mac slotu"):
        parse_picks("1,,10")
    with pytest.raises(ValueError, match="bos mac slotu"):
        parse_picks("1, ,10")


def test_picks_gecersiz_sembol():
    with pytest.raises(ValueError, match="gecersiz sembol"):
        parse_picks("1,5,1")


def test_picks_bas_son_fazla_ayirici_ok():
    assert parse_picks(",1,10,") == [["1"], ["1", "0"]]


def test_picks_bosluklu_cifte_ok():
    assert parse_picks("1, 10, 1") == [["1"], ["1", "0"], ["1"]]


def test_picks_sadece_bosluk_ayirici():
    assert parse_picks("1 10 1") == [["1"], ["1", "0"], ["1"]]


def test_cli_bayes_probs_zorunlu(capsys):
    assert main(["--picks", ORNEK, "--bayes-preset", "dengeli", "--kisa"]) == 1
    assert "probs" in capsys.readouterr().err.lower()


def test_cli_mc_samples_negatif(capsys):
    assert main(["--picks", ORNEK, "--mc-samples", "-5", "--kisa"]) == 1
    assert "negatif" in capsys.readouterr().err.lower()


def test_bayes_n0_equals_prior():
    alpha = default_prior(["1", "0"], strength=2.0)
    prior = prior_mean(alpha)
    post = dirichlet_posterior(alpha, {"1": 0.9, "0": 0.05, "2": 0.05}, strength=0.0)
    for s in SEMBOLLER:
        assert post[s] == pytest.approx(prior[s], rel=1e-9)
    assert sum(post.values()) == pytest.approx(1.0)


def test_bayes_huge_alpha_stable():
    alpha = default_prior(["1", "0", "2"], strength=1e6)
    post = dirichlet_posterior(alpha, {"1": 1.0, "0": 0.0, "2": 0.0}, strength=1.0)
    assert abs(sum(post.values()) - 1.0) < 1e-9
    assert all(math.isfinite(v) for v in post.values())


def test_bayes_single_symbol_100():
    alpha = default_prior(["1", "0", "2"], strength=1.0)
    post = dirichlet_posterior(alpha, {"1": 1.0, "0": 0.0, "2": 0.0}, strength=100.0)
    assert post["1"] > 0.95
    assert abs(sum(post.values()) - 1.0) < 1e-9


def test_probs_all_zero_raises():
    sel = parse_picks("1,10")
    with pytest.raises(ValueError, match="sifir"):
        parse_probs("1:0,0:0,2:0;1:0,0:0,2:0", sel)


def test_bayes_update_no_nan():
    sel = parse_picks("1,10,12")
    ev = [
        {"1": 1.0, "0": 0.0, "2": 0.0},
        {"1": 0.0, "0": 1.0, "2": 0.0},
        {"1": 0.0, "0": 0.0, "2": 1.0},
    ]
    rows = bayes_update_matches(sel, ev, prior_strength=1.0, evidence_strength=10.0)
    for r in rows:
        for s in SEMBOLLER:
            assert math.isfinite(r["posterior"][s])
        assert abs(sum(r["posterior"].values()) - 1.0) < 1e-9


# **Uc "fix16" kenar durumu dustu ve yerine bir tanesi geldi.** Eskiden
# sinanan seyler kaplamaya ozguydu: 6 ciftenin reddedilmesi (`7 CIFTE`
# hatasi), 7 ciftede tam 16 kolon, 8 ciftede 32. Duzde "en az 7 cifte" diye
# bir sart yok ve bedel her zaman `2^cifte * 3^uclu`; asagidaki tek test
# ucunun de yerini tutar cunku KURALI sinar, uc ornegi degil.


@pytest.mark.parametrize("cifte,uclu", [(0, 0), (1, 0), (6, 0), (7, 0),
                                        (8, 0), (5, 2), (0, 4)])
def test_duz_bedel_her_sekilde_carpimin_kendisi(cifte, uclu):
    isaret = ["10"] * cifte + ["102"] * uclu
    isaret += ["1"] * (15 - len(isaret))
    enc = Encoder(parse_picks(",".join(isaret)))
    assert len(duz_kolonlar(enc)) == 2 ** cifte * 3 ** uclu


def test_mc_n_samples_sifir_raises():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,1,1,1,1,1,1,1,1"))
    cols = duz_kolonlar(enc)
    with pytest.raises(ValueError, match="n_samples"):
        monte_carlo_report(enc, cols, _uniform_probs(15), n_samples=0)


def test_mc_n_samples_negatif_raises():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,1,1,1,1,1,1,1,1"))
    cols = duz_kolonlar(enc)
    with pytest.raises(ValueError, match="n_samples"):
        monte_carlo_report(enc, cols, _uniform_probs(15), n_samples=-3)


def test_mc_kucuk_n_warning():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,1,1,1,1,1,1,1,1"))
    cols = duz_kolonlar(enc)
    mc = monte_carlo_report(enc, cols, _uniform_probs(15), n_samples=5, seed=1)
    assert mc["n_samples"] == 5
    assert "warning" in mc


# ── Olasilik ayristirmada CLI/API ayrimi ────────────────────────────────
#
# Iki ayristirici ayni girdiye BILEREK farkli cevap verir (gerekce:
# `web_app._parse_prob_value` docstring'i). Ayrim belgelenmisti ama hicbir
# test onu tutmuyordu; yani biri digerine dogru kayarsa kimse fark etmezdi.
# Asagidaki uc cift o ayrimin kendisini kilitler.

def _api_probs(satirlar, sel):
    flask = pytest.importorskip("flask")  # noqa: F841
    from web_app import _parse_json_probs
    return _parse_json_probs({"probs": satirlar}, sel)


def test_ayrim_negatif_olasilik():
    """CLI reddeder, API sifira kirpar."""
    sel = [["1", "0", "2"]] * 15
    with pytest.raises(ValueError, match=r"[Nn]egatif"):
        parse_probs(";".join(["1:-0.5,0:0.3,2:0.2"] * 15), sel)

    out = _api_probs([{"1": -0.5, "0": 0.3, "2": 0.2}] * 15, sel)
    assert out[0]["1"] == 0.0
    assert out[0]["0"] == pytest.approx(0.6)


def test_ayrim_satirin_tamami_sifir():
    """CLI reddeder, API secim kumesine esit dagitir."""
    sel = [["1", "0"]] * 15
    with pytest.raises(ValueError, match="sifir"):
        parse_probs(";".join(["1:0,0:0,2:0"] * 15), sel)

    out = _api_probs([{"1": 0, "0": 0, "2": 0}] * 15, sel)
    assert out[0] == {"1": 0.5, "0": 0.5, "2": 0.0}, \
        "isaretlenmemis sembole kutle verilmemeli"


def test_ayrim_yuzde_sezgisi():
    """API `>1` degeri yuzde sayar; CLI saymaz. Ikisi de 1'e normalize eder."""
    sel = [["1", "0", "2"]] * 15
    cli = parse_probs(";".join(["1:50,0:30,2:20"] * 15), sel)
    api = _api_probs([{"1": 50, "0": 30, "2": 20}] * 15, sel)
    # Olcek degismezligi: tek basina bu satir ikisini ayirmaz.
    assert cli[0]["1"] == pytest.approx(0.5)
    assert api[0]["1"] == pytest.approx(0.5)

    # Ayrim KARISIK olcekte gorunur: API once hepsini yuzde sanip boler.
    karisik = _api_probs([{"1": 50, "0": 0.3, "2": 0.2}] * 15, sel)
    assert karisik[0]["1"] == pytest.approx(0.5)
    cli_karisik = parse_probs(";".join(["1:50,0:0.3,2:0.2"] * 15), sel)
    assert cli_karisik[0]["1"] == pytest.approx(50 / 50.5)
    assert karisik[0]["1"] != pytest.approx(cli_karisik[0]["1"])


# ── "N dogru" etiketleri kupon uzunlugundan okunur ──────────────────────

def test_etiketler_15_sabitine_bagli_degil():
    """`Encoder(kati=False)` 15'ten kisa kupona izin verir.

    Etiketler once `15 - d` ile uretiliyordu; 14 macli bir kuponda butun
    "N dogru" etiketleri bir kayiyordu — cokme degil, YANLIS SAYI, yani
    fark edilmesi en zor tur. Monte Carlo kovalari, API'nin `dist` blogu ve
    konsol raporu ayni sabiti tasiyordu.
    """
    from spor_toto.duz import kolonlar as duz_kolonlar
    from spor_toto.report import dagilim_satirlari

    sel = [["1", "0"]] * 7 + [["1"]] * 7          # 14 mac, 7 cifte
    enc = Encoder(sel, kati=False)
    assert enc.total_len == 14
    cols = duz_kolonlar(enc)

    # **Bu iddia degisti ve sebebi olcum degil YAPI.** Kaplamada rapor bir
    # MESAFE dagilimiydi ("N dogru" etiketleri d=0,1,2... katmanlarindan
    # geliyordu) ve 15 sabitine baglanmis olmasi gercek bir hataydi. Duzde
    # mesafe yok; rapor kumenin tamaminin oynandigini gosteriyor ve tam
    # isabeti mac sayisindan okuyor. Testin korudugu sey ayni kaliyor:
    # **15 sabiti kodda gomulu olmamali.**
    satirlar = dagilim_satirlari(enc, cols)
    assert any(f"bir kolon {enc.total_len} tutturur" in s for s in satirlar), \
        f"tam isabet {enc.total_len} olmali, gelen: {satirlar}"
    assert not any("15 tutturur" in s for s in satirlar), \
        "14 macli kuponda 15 etiketi olamaz"

    # Monte Carlo kovalari da uzunluktan bagimsiz olmali. `distance_layers`
    # kaplamayla dustu; duzde tam isabet kolonlarin icinde ZATEN var.
    mc = monte_carlo_report(enc, cols, _uniform_probs(14), n_samples=2000, seed=1)
    assert len(cols) == enc.space_size()
    assert set(mc) >= {"p15", "p14", "p13", "p12", "kume_ici"}
