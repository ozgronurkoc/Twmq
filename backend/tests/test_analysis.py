"""analysis.py: Monte Carlo ve hata frekansi testleri."""

from __future__ import annotations

import math

import pytest

from spor_toto.analysis import match_error_frequency, monte_carlo_report
from spor_toto.core import Encoder, SEMBOLLER, parse_picks, solve_fix16

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


def _enc_cols():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    return enc, cols


def _uniform_probs(n: int = 15):
    return [{s: 1.0 / 3.0 for s in SEMBOLLER} for _ in range(n)]


def test_monte_carlo_shape_and_bounds():
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=3_000, seed=1)
    assert mc["n_samples"] == 3_000
    for key in ("kume_ici", "p15", "p14", "p13", "p12"):
        block = mc[key]
        assert 0.0 <= block["p"] <= 1.0
        assert "pct" in block and "se" in block and "ci95" in block
        assert "count" in block


def test_monte_carlo_mac_sayisi_uyusmazligi():
    enc, cols = _enc_cols()
    with pytest.raises(ValueError):
        monte_carlo_report(enc, cols, _uniform_probs(3), n_samples=100)


def test_monte_carlo_deterministik():
    enc, cols = _enc_cols()
    a = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2_000, seed=99)
    b = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2_000, seed=99)
    assert a["p15"]["count"] == b["p15"]["count"]
    assert a["kume_ici"]["count"] == b["kume_ici"]["count"]


def test_monte_carlo_exact_ile_yaklasik():
    """Yuksek n ile exact p_kume_ici'ye yaklasmali (uniform secim ici)."""
    enc, cols = _enc_cols()
    # Secim kumesi uzerinde uniform: her mac icin seceneklere esit agirlik
    probs = []
    for sec in enc.selections:
        p = {s: 0.0 for s in SEMBOLLER}
        for s in sec:
            p[s] = 1.0 / len(sec)
        probs.append(p)
    mc = monte_carlo_report(enc, cols, probs, n_samples=20_000, seed=42)
    # Secim ici normalize oldugu icin kume_ici ~ 1
    assert mc["kume_ici"]["p"] > 0.95


def test_monte_carlo_dusuk_n_calisir():
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=500, seed=0)
    assert mc["n_samples"] == 500


def test_error_freq_gecerli_kaplamada_n2_sifir():
    enc, cols = _enc_cols()
    ef = match_error_frequency(enc, cols)
    assert ef["n2"] == 0
    assert isinstance(ef["d1"], list)
    assert isinstance(ef["d2"], list)


def test_error_freq_bos_kolon():
    enc = Encoder(parse_picks(ORNEK))
    ef = match_error_frequency(enc, [])
    assert ef == {"d1": [], "d2": [], "n1": 0, "n2": 0}


def test_error_freq_se_ci_formulu():
    """rate blogundaki se formulu tutarli."""
    enc, cols = _enc_cols()
    n = 5_000
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=n, seed=7)
    p = mc["p15"]["p"]
    se = math.sqrt(p * (1.0 - p) / n)
    assert abs(mc["p15"]["se"] - se) < 1e-12


def test_mc_warning_cok_dusuk():
    """n < 100 → sert uyarı."""
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=50, seed=1)
    assert "warning" in mc
    assert "cok dusuk" in mc["warning"]


def test_mc_warning_dusuk():
    """100 ≤ n < 1000 → yumuşak uyarı."""
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=500, seed=1)
    assert "warning" in mc
    assert "dusuk" in mc["warning"]
    assert "cok dusuk" not in mc["warning"]


def test_mc_warning_yok_yeterli_n():
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2000, seed=1)
    assert "warning" not in mc
