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

α / n pratik seçim
-----------------
  α (Prior strength)
    0.5–1   → zayıf prior, evidence hemen baskın olur
    1–3     → dengeli (varsayılan 1)
    5–20    → güçlü prior, seçim kümesine güven yüksek

  n (Evidence strength)
    0       → posterior = prior (evidence yok sayılır)
    5–15    → orta güven (varsayılan 10)
    30–100  → yüksek güven, evidence neredeyse doğrudan alınır
    →∞      → posterior → evidence

KL(p‖q) yorumu (nats)
---------------------
  < 0.02   ihmal edilebilir kayma
  0.02–0.10  hafif
  0.10–0.30  orta
  0.30–0.70  belirgin
  > 0.70   güçlü kayma (prior ile evidence çatışıyor)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .core import SEMBOLLER

# UI ve CLI için hazır preset'ler
STRENGTH_PRESETS: Dict[str, Dict[str, float]] = {
    "zayif_prior": {"prior_strength": 0.5, "evidence_strength": 15.0},
    "dengeli": {"prior_strength": 1.0, "evidence_strength": 10.0},
    "guclu_prior": {"prior_strength": 5.0, "evidence_strength": 8.0},
    "evidence_agir": {"prior_strength": 1.0, "evidence_strength": 40.0},
    "sadece_prior": {"prior_strength": 3.0, "evidence_strength": 0.0},
}


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


def interpret_kl(kl: float) -> str:
    """KL(p‖q) nats → insan dilinde etiket."""
    kl = float(kl)
    if kl < 0.02:
        return "ihmal edilebilir"
    if kl < 0.10:
        return "hafif kayma"
    if kl < 0.30:
        return "orta kayma"
    if kl < 0.70:
        return "belirgin kayma"
    return "güçlü kayma"


def recommend_strengths(
    confidence: str = "dengeli",
) -> Dict[str, float]:
    """
    Kullanıcı güven seviyesine göre α / n öner.

    confidence: zayif_prior | dengeli | guclu_prior | evidence_agir | sadece_prior
    """
    key = confidence.strip().lower().replace(" ", "_")
    if key not in STRENGTH_PRESETS:
        key = "dengeli"
    return dict(STRENGTH_PRESETS[key])


def bayes_update_matches(
    selections: Sequence[Sequence[str]],
    evidence_probs: Sequence[Dict[str, float]],
    prior_strength: float = 1.0,
    evidence_strength: float = 10.0,
) -> List[Dict[str, object]]:
    """
    Tüm maçlar için prior → posterior.

    Dönen her eleman:
      prior_alpha, prior, evidence, posterior, kl_prior_post, kl_ev_post, kl_label
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
        kl_pp = _kl(post, prior)
        out.append({
            "prior_alpha": alpha,
            "prior": prior,
            "evidence": ev_n,
            "posterior": post,
            "kl_prior_post": kl_pp,
            "kl_ev_post": _kl(post, ev_n),
            "kl_label": interpret_kl(kl_pp),
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
    """Maç listesi özeti: ortalama KL, etiket, en çok kayan maçlar."""
    if not updates:
        return {
            "n": 0,
            "mean_kl_prior_post": 0.0,
            "mean_kl_label": interpret_kl(0.0),
            "top_shifts": [],
            "guide": _strength_guide(),
        }

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
        kl_val = float(u["kl_prior_post"])  # type: ignore[arg-type]
        top.append({
            "mac": mac,
            "kl": kl_val,
            "kl_label": interpret_kl(kl_val),
            "prior": {s: round(float(prior[s]), 4) for s in SEMBOLLER},  # type: ignore[index]
            "posterior": {s: round(float(post[s]), 4) for s in SEMBOLLER},  # type: ignore[index]
        })
    return {
        "n": len(updates),
        "mean_kl_prior_post": round(mean_kl, 6),
        "mean_kl_label": interpret_kl(mean_kl),
        "top_shifts": top,
        "guide": _strength_guide(),
    }


def _strength_guide() -> Dict[str, str]:
    """UI / rapor için kısa α–n kılavuzu."""
    return {
        "alpha": (
            "Prior α: 0.5–1 zayıf (evidence baskın), 1–3 dengeli, "
            "5–20 güçlü (seçim kümesine güven)."
        ),
        "n": (
            "Evidence n: 0 = sadece prior, 5–15 orta, 30–100 yüksek güven, "
            "büyük n → posterior ≈ evidence."
        ),
        "kl": (
            "KL: <0.02 ihmal, 0.02–0.10 hafif, 0.10–0.30 orta, "
            "0.30–0.70 belirgin, >0.70 güçlü kayma."
        ),
    }
