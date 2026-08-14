"""Analiz katmani: Monte Carlo ve mac bazli hata frekansi."""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

from .core import SEMBOLLER, Encoder, Point, ball, hamming


def monte_carlo_report(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[Dict[str, float]],
    n_samples: int = 100_000,
    seed: int = 42,
) -> dict:
    """
    Independent multinomial draws per match → outcome in {1,0,2}^15.

    Reports empirical rates for: selection-set membership, best-column
    hits at 15/14/13/12, with normal-approx 95% CI half-widths.

    n_samples < 1 → ValueError (sessiz sifir rapor yok).
    1 ≤ n_samples < 100 → calisir ama 'warning' alani eklenir.
    100 ≤ n_samples < 1000 → yumusak warning.
    """
    try:
        n_samples = int(n_samples)
    except (TypeError, ValueError) as e:
        raise ValueError(f"n_samples sayi olmali, alindi: {n_samples!r}") from e
    if n_samples < 1:
        raise ValueError(
            f"Monte Carlo icin n_samples >= 1 gerekli (alindi: {n_samples}). "
            f"CLI'de --mc-samples 0 MC'yi kapatir; acmak icin pozitif deger ver."
        )
    warning: Optional[str] = None
    if n_samples < 100:
        warning = (
            f"n_samples={n_samples} cok dusuk; %95 CI guvenilmez. "
            f"En az 1000 (tercihen 10000+) onerilir."
        )
    elif n_samples < 1000:
        warning = (
            f"n_samples={n_samples} dusuk; CI genis kalabilir. "
            f"Karar icin en az 1000, rapor icin 10000+ onerilir."
        )

    rng = random.Random(seed)

    cum: List[List[Tuple[float, str]]] = []
    for i in range(enc.total_len):
        p = probs[i]
        weights = [max(0.0, float(p.get(sym, 0.0))) for sym in SEMBOLLER]
        total = sum(weights)
        if total <= 0:
            weights = [1.0 / 3.0] * 3
        else:
            weights = [w / total for w in weights]
        running = 0.0
        entries: List[Tuple[float, str]] = []
        for w, sym in zip(weights, SEMBOLLER):
            running += w
            entries.append((running, sym))
        if entries:
            entries[-1] = (1.0, entries[-1][1])
        cum.append(entries)

    sel_sets = [set(s) for s in enc.selections]

    n_ici = n_15 = n_14 = n_13 = n_12 = 0

    for _ in range(n_samples):
        outcome: List[str] = []
        for i in range(enc.total_len):
            r = rng.random()
            chosen = cum[i][-1][1]
            for threshold, sym in cum[i]:
                if r <= threshold:
                    chosen = sym
                    break
            outcome.append(chosen)

        if any(outcome[i] not in sel_sets[i] for i in range(enc.total_len)):
            continue
        n_ici += 1

        # Best column distance in variable space only (banko fixed match)
        if not enc.variable_pos:
            best = 0
        else:
            # Map outcome symbols on variable positions to alphabet indices
            var_idx: List[int] = []
            ok = True
            for j, pos in enumerate(enc.variable_pos):
                sym = outcome[pos]
                try:
                    var_idx.append(enc.variable_syms[j].index(sym))
                except ValueError:
                    ok = False
                    break
            if not ok:
                continue
            pt = tuple(var_idx)
            best = min(hamming(pt, c) for c in cols) if cols else 99

        if best == 0:
            n_15 += 1
        elif best == 1:
            n_14 += 1
        elif best == 2:
            n_13 += 1
        elif best == 3:
            n_12 += 1

    def _rate(k: int) -> dict:
        p = k / n_samples if n_samples else 0.0
        se = math.sqrt(p * (1.0 - p) / n_samples) if n_samples else 0.0
        return {
            "count": k,
            "pct": 100.0 * p,
            "se": se,
            "ci95": 1.96 * 100.0 * se,
        }

    out = {
        "n_samples": n_samples,
        "seed": seed,
        "kume_ici": _rate(n_ici),
        "p15": _rate(n_15),
        "p14": _rate(n_14),
        "p13": _rate(n_13),
        "p12": _rate(n_12),
    }
    if warning:
        out["warning"] = warning
    return out


def match_error_frequency(
    enc: Encoder,
    cols: Sequence[Point],
    max_distance: int = 2,
) -> dict:
    """
    For each variable match, how often it is among the disagreeing coordinates
    when the nearest column is at distance d (d=1 or d=2).
    """
    sizes = enc.alphabet_sizes
    if not sizes or not cols:
        return {"d1": {}, "d2": {}, "n1": 0, "n2": 0}

    from itertools import product

    space = list(product(*[range(k) for k in sizes]))
    d1_counts = [0] * len(sizes)
    d2_counts = [0] * len(sizes)
    n1 = n2 = 0

    for pt in space:
        best_d = 99
        best_cols = []
        for c in cols:
            d = hamming(pt, c)
            if d < best_d:
                best_d = d
                best_cols = [c]
            elif d == best_d:
                best_cols.append(c)
        if best_d == 1:
            n1 += 1
            for c in best_cols:
                for i, (a, b) in enumerate(zip(pt, c)):
                    if a != b:
                        d1_counts[i] += 1
        elif best_d == 2:
            n2 += 1
            for c in best_cols:
                for i, (a, b) in enumerate(zip(pt, c)):
                    if a != b:
                        d2_counts[i] += 1

    def _pack(counts, n):
        out = {}
        for i, cnt in enumerate(counts):
            mac = enc.variable_pos[i] + 1
            out[mac] = {"count": cnt, "share": (cnt / n) if n else 0.0}
        return out

    return {
        "d1": _pack(d1_counts, n1),
        "d2": _pack(d2_counts, n2),
        "n1": n1,
        "n2": n2,
    }
