"""Bayes Dirichlet güncelleme testleri."""

import pytest

from spor_toto.bayes import (
    bayes_summary,
    bayes_update_matches,
    default_prior,
    dirichlet_posterior,
    interpret_kl,
    posteriors_only,
    prior_mean,
    recommend_strengths,
)
from spor_toto.core import SEMBOLLER, parse_picks


def test_default_prior_uniform_when_no_selection():
    p = default_prior(None, strength=2.0)
    assert all(p[s] == 2.0 for s in SEMBOLLER)


def test_default_prior_favors_selection():
    p = default_prior(["1", "0"], strength=3.0)
    assert p["1"] == 3.0 and p["0"] == 3.0
    assert p["2"] < 0.1


def test_prior_mean_sums_to_one():
    alpha = default_prior(["1"], strength=1.0)
    m = prior_mean(alpha)
    assert sum(m.values()) == pytest.approx(1.0)
    assert m["1"] > m["0"] and m["1"] > m["2"]


def test_posterior_equals_prior_when_strength_zero():
    alpha = default_prior(["1", "0", "2"], strength=1.0)
    ev = {"1": 0.9, "0": 0.05, "2": 0.05}
    post = dirichlet_posterior(alpha, ev, strength=0.0)
    prior = prior_mean(alpha)
    for s in SEMBOLLER:
        assert post[s] == pytest.approx(prior[s], rel=1e-9)


def test_posterior_moves_toward_evidence():
    alpha = default_prior(["1", "0", "2"], strength=1.0)
    ev = {"1": 1.0, "0": 0.0, "2": 0.0}
    weak = dirichlet_posterior(alpha, ev, strength=1.0)
    strong = dirichlet_posterior(alpha, ev, strength=100.0)
    assert strong["1"] > weak["1"] > prior_mean(alpha)["1"]
    assert strong["1"] > 0.95


def test_posterior_normalized():
    post = dirichlet_posterior(
        {"1": 1, "0": 1, "2": 1},
        {"1": 0.5, "0": 0.3, "2": 0.2},
        strength=10,
    )
    assert sum(post.values()) == pytest.approx(1.0)


def test_bayes_update_matches_length():
    sels = parse_picks("1,10,12")
    ev = [
        {"1": 0.8, "0": 0.1, "2": 0.1},
        {"1": 0.5, "0": 0.5, "2": 0.0},
        {"1": 0.4, "0": 0.0, "2": 0.6},
    ]
    rows = bayes_update_matches(sels, ev, prior_strength=1.0, evidence_strength=8.0)
    assert len(rows) == 3
    for r in rows:
        assert abs(sum(r["posterior"].values()) - 1.0) < 1e-9
        assert r["kl_prior_post"] >= 0.0


def test_posteriors_only_feeds_mc_shape():
    sels = parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10")
    ev = [{s: 1.0 / 3 for s in SEMBOLLER} for _ in range(15)]
    posts = posteriors_only(sels, ev, evidence_strength=5.0)
    assert len(posts) == 15
    assert all(abs(sum(p.values()) - 1.0) < 1e-9 for p in posts)


def test_bayes_summary_top_shifts():
    """Prior ile uyumlu evidence → küçük KL; prior dışı mass → büyük KL."""
    sels = parse_picks("1,10")
    ev = [
        {"1": 0.99, "0": 0.005, "2": 0.005},  # banko prior ile aynı yön → az kayma
        {"1": 0.34, "0": 0.33, "2": 0.33},    # çifte prior dışı '2' mass → daha çok kayma
    ]
    rows = bayes_update_matches(sels, ev, evidence_strength=20.0)
    summary = bayes_summary(rows)
    assert summary["n"] == 2
    assert len(summary["top_shifts"]) == 2
    # sıralama KL azalan
    kls = [t["kl"] for t in summary["top_shifts"]]
    assert kls == sorted(kls, reverse=True)
    # maç 2 (yayvan evidence) maç 1'den (uyumlu evidence) daha yüksek KL
    assert rows[1]["kl_prior_post"] > rows[0]["kl_prior_post"]
    assert summary["top_shifts"][0]["mac"] == 2


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        bayes_update_matches([["1"]], [{"1": 1}, {"0": 1}])


def test_interpret_kl_labels():
    assert interpret_kl(0.005) == "ihmal edilebilir"
    assert interpret_kl(0.05) == "hafif kayma"
    assert interpret_kl(0.2) == "orta kayma"
    assert interpret_kl(0.5) == "belirgin kayma"
    assert interpret_kl(1.0) == "güçlü kayma"


def test_recommend_strengths_presets():
    d = recommend_strengths("dengeli")
    assert d["prior_strength"] == 1.0 and d["evidence_strength"] == 10.0
    e = recommend_strengths("evidence_agir")
    assert e["evidence_strength"] >= 30.0
    # bilinmeyen → dengeli
    assert recommend_strengths("xyz")["prior_strength"] == 1.0


def test_bayes_summary_has_label_and_guide():
    sels = parse_picks("1,10")
    ev = [
        {"1": 0.9, "0": 0.05, "2": 0.05},
        {"1": 0.3, "0": 0.3, "2": 0.4},
    ]
    rows = bayes_update_matches(sels, ev, evidence_strength=15.0)
    summary = bayes_summary(rows)
    assert "mean_kl_label" in summary
    assert summary["mean_kl_label"] in {
        "ihmal edilebilir", "hafif kayma", "orta kayma",
        "belirgin kayma", "güçlü kayma",
    }
    assert "guide" in summary and "kl" in summary["guide"]
    assert "kl_label" in rows[0]
    assert "kl_label" in summary["top_shifts"][0]
