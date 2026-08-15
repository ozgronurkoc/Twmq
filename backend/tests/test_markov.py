"""Markov zinciri testleri."""

import pytest

from spor_toto.core import parse_picks, solve_fix16, Encoder, olasilik_raporu
from spor_toto.markov import (
    error_budget_chain,
    markov_report,
    selection_survival_chain,
)

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


def _probs_on_sel(enc):
    out = []
    for sel in enc.selections:
        p = {"1": 0.0, "0": 0.0, "2": 0.0}
        u = 1.0 / len(sel)
        for s in sel:
            p[s] = u
        out.append(p)
    return out


def test_survival_equals_kume_ici():
    enc = Encoder(parse_picks(ORNEK))
    probs = _probs_on_sel(enc)
    surv = selection_survival_chain(enc, probs)
    assert surv["p_survive"] == pytest.approx(1.0, abs=1e-9)
    assert len(surv["p_in_after"]) == 16
    assert surv["p_in_after"][0] == 1.0


def test_survival_matches_olasilik_raporu():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_sel(enc)
    # evidence biraz çarpık
    probs[0] = {"1": 0.7, "0": 0.2, "2": 0.1}
    surv = selection_survival_chain(enc, probs)
    rap = olasilik_raporu(enc, cols, probs)
    assert surv["p_survive"] == pytest.approx(rap.p_kume_ici, rel=1e-9)


def test_error_budget_garanti_when_on_selection():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_sel(enc)
    eb = error_budget_chain(enc, cols, probs)
    assert eb["p_garanti"] == pytest.approx(1.0, abs=1e-6)
    assert eb["p_final"]["2+"] == pytest.approx(0.0, abs=1e-6)
    assert eb["p_final"]["0"] + eb["p_final"]["1"] == pytest.approx(1.0, abs=1e-6)


def test_markov_report_shape():
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_sel(enc)
    rep = markov_report(enc, cols, probs)
    assert "survival" in rep and "error_budget" in rep and "summary" in rep
    assert rep["summary"]["p_kume_ici"] == pytest.approx(1.0, abs=1e-9)


def test_length_mismatch():
    enc = Encoder(parse_picks(ORNEK))
    with pytest.raises(ValueError):
        selection_survival_chain(enc, [{"1": 1}] * 3)
