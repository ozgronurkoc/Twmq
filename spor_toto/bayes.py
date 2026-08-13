"""Bayes güncelleme: maç bazlı Dirichlet prior → posterior.

Spor Toto bağlamı
-----------------
Her maç 3 kategorili (1 / 0 / 2). Dirichlet, çokterimli dağılımın
eşlenik prior'ıdır; posterior ortalama kapalı formda gelir:

    α_post = α_prior + n · evidence
    p_post = α_post / sum(α_post)

- α_prior: zayıf veya seçim kümesine dayalı prior (pseudo-count)
- evidence: kullanıcının girdiği 1/0/2 olasılıkları (normalize)
- n (strength): evidence'a verilen güven (pseudo-gözlem sayısı)

Posterior, mevcut exact + Monte Carlo motorlarına doğrudan verilir.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .core import SEMBOLLER


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(weights.get(s, 0.0))) for s in SEMBOLLER)
    if total <= 0:
        return {s: 1.0 / 3.0 for s in SEMBOLLER}
    return {s: max(0.0, float(weights.get(s, 0.0))) / total for s in SEMBOLLER}


def default_prior(
    selection: Optional[Sequence[str]] = None,
    strength: float = 1.0,
) -> Dict[str, float]:
    """
    Seçim kümesine dayalı zayıf prior.

    strength: her seçilen sembole verilen α (pseudo-count).
    Seçilmeyen semboller α = ε (çok küçük, sayısal stabilite).
    """
    strength = max(1e-6, float(strength))
    eps = 1e-3
    if not selection:
        return {s: strength for s in SEMBOLLER}
    sel = set(selection)
    return {s: (strength if s in sel else eps) for s in SEMBOLLER}


def dirichlet_posterior(
    prior_alpha: Dict[str, float],
    evidence: Dict[str, float],
    strength: float = 10.0,
) -> Dict[str, float]:
    """
    Dirichlet güncelleme.

    α_post[s] = α_prior[s] + strength * evidence[s]
    p[s]      = α_post[s] / Σ α_post

    strength=0 → posterior = prior mean
    strength→∞ → posterior → evidence
    """
    strength = max(0.0, float(strength))
    ev = _normalize(evidence)
    alpha_post: Dict[str, float] = {}
    for s in SEMBOLLER:
        a0 = max(1e-9, float(prior_alpha.get(s, 1e-9)))
        alpha_post[s] = a0 + strength * ev[s]
    total = sum(alpha_post.values())
    return {s: alpha_post[s] / total for s in SEMBOLLER}


def prior_mean(prior_alpha: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(1e-9, float(prior_alpha.get(s, 0.0))) for s in SEMBOLLER)
    return {s: max(1e-9, float(prior_alpha.get(s, 0.0))) / total for s in SEMBOLLER}


def bayes_update_matches(
    selections: Sequence[Sequence[str]],
    evidence_probs: Sequence[Dict[str, float]],
    prior_strength: float = 1.0,
    evidence_strength: float = 10.0,
) -> List[Dict[str, object]]:
    """
    Tüm maçlar için prior → posterior.

    Dönen her eleman:
      prior_alpha, prior, evidence, posterior, kl_divergence
    """
    if len(evidence_probs) != len(selections):
        raise ValueError(
            f"evidence {len(evidence_probs)} maç, selections {len(selections)} maç"
        )

    out: List[Dict[str, object]] = []
    for sel, ev in zip(selections, evidence_probs):
        alpha = default_prior(sel, strength=prior_strength)
        prior = prior_mean(alpha)
        ev_n = _normalize(ev)
        post = dirichlet_posterior(alpha, ev_n, strength=evidence_strength)
        out.append({
            "prior_alpha": alpha,
            "prior": prior,
            "evidence": ev_n,
            "posterior": post,
            "kl_prior_post": _kl(post, prior),
            "kl_ev_post": _kl(post, ev_n),
        })
    return out


def posteriors_only(
    selections: Sequence[Sequence[str]],
    evidence_probs: Sequence[Dict[str, float]],
    prior_strength: float = 1.0,
    evidence_strength: float = 10.0,
) -> List[Dict[str, float]]:
    """Sadece posterior olasılık listesi (exact/MC motoruna verilir)."""
    rows = bayes_update_matches(
        selections, evidence_probs, prior_strength, evidence_strength)
    return [r["posterior"] for r in rows]  # type: ignore[misc]


def _kl(p: Dict[str, float], q: Dict[str, float]) -> float:
    """KL(p || q) nats."""
    import math
    s = 0.0
    for k in SEMBOLLER:
        pk = max(1e-12, float(p.get(k, 0.0)))
        qk = max(1e-12, float(q.get(k, 0.0)))
        s += pk * math.log(pk / qk)
    return round(s, 6)


def bayes_summary(
    updates: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    """Maç listesi özeti: ortalama KL, en çok kayan maçlar."""
    if not updates:
        return {"n": 0, "mean_kl_prior_post": 0.0, "top_shifts": []}

    kls = [float(u["kl_prior_post"]) for u in updates]  # type: ignore[arg-type]
    mean_kl = sum(kls) / len(kls)
    ranked = sorted(
        enumerate(updates, 1),
        key=lambda t: float(t[1]["kl_prior_post"]),  # type: ignore[arg-type]
        reverse=True,
    )
    top = []
    for mac, u in ranked[:5]:
        post = u["posterior"]  # type: ignore[assignment]
        prior = u["prior"]  # type: ignore[assignment]
        top.append({
            "mac": mac,
            "kl": float(u["kl_prior_post"]),  # type: ignore[arg-type]
            "prior": {s: round(float(prior[s]), 4) for s in SEMBOLLER},  # type: ignore[index]
            "posterior": {s: round(float(post[s]), 4) for s in SEMBOLLER},  # type: ignore[index]
        })
    return {
        "n": len(updates),
        "mean_kl_prior_post": round(mean_kl, 6),
        "top_shifts": top,
    }
