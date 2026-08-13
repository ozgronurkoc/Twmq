"""Monte Carlo ve maç bazlı hata frekansı testleri."""

import math

import pytest

from spor_toto.analysis import match_error_frequency, monte_carlo_report
from spor_toto.core import Encoder, olasilik_raporu, parse_picks, solve_fix16

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


def _uniform_probs(n: int = 15):
    return [{s: 1.0 / 3 for s in ("1", "0", "2")} for _ in range(n)]


def test_monte_carlo_shape_and_bounds():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=3_000, seed=1)
    assert mc["n_samples"] == 3_000
    for key in ("kume_ici", "p15", "p14", "p13", "p12"):
        assert 0.0 <= mc[key]["p"] <= 1.0
        assert mc[key]["count"] >= 0
        assert mc[key]["ci95"] >= 0.0
        assert mc[key]["pct"] == pytest.approx(100.0 * mc[key]["p"], rel=1e-6)


def test_monte_carlo_mac_sayisi_uyusmazligi():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    with pytest.raises(ValueError, match="bekleniyordu"):
        monte_carlo_report(enc, cols, _uniform_probs(3), n_samples=100)


def test_monte_carlo_deterministik():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    a = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2_000, seed=99)
    b = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2_000, seed=99)
    assert a["p15"]["count"] == b["p15"]["count"]
    assert a["kume_ici"]["p"] == b["kume_ici"]["p"]


def test_monte_carlo_exact_ile_yaklasik():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _uniform_probs()
    rap = olasilik_raporu(enc, cols, probs)
    mc = monte_carlo_report(enc, cols, probs, n_samples=20_000, seed=42)
    assert abs(mc["kume_ici"]["p"] - rap.p_kume_ici) < 0.03
    assert abs(mc["p15"]["p"] - rap.p_15) < 0.03


def test_monte_carlo_sifir_agirlik_normalize():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    # tüm sıfır → uniform fallback, çökmemeli
    probs = [{s: 0.0 for s in ("1", "0", "2")} for _ in range(15)]
    mc = monte_carlo_report(enc, cols, probs, n_samples=500, seed=0)
    assert mc["n_samples"] == 500


def test_error_freq_gecerli_kaplamada_n2_sifir():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    ef = match_error_frequency(enc, cols)
    assert ef["n2"] == 0
    assert ef["n1"] >= 0
    assert isinstance(ef["d1"], list)
    for item in ef["d1"]:
        assert "mac" in item and "count" in item and "pct" in item


def test_error_freq_bos_kolon():
    enc = Encoder(parse_picks(ORNEK))
    ef = match_error_frequency(enc, [])
    assert ef == {"d1": [], "d2": [], "n1": 0, "n2": 0}


def test_error_freq_se_ci_formulu():
    """CI formülü: 1.96 * sqrt(p(1-p)/n) * 100."""
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    n = 5_000
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=n, seed=7)
    p = mc["p15"]["p"]
    expected_ci = round(1.96 * math.sqrt(p * (1.0 - p) / n) * 100.0, 3)
    assert mc["p15"]["ci95"] == expected_ci
