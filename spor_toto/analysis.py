"""Monte Carlo olasılık simülasyonu ve maç bazlı hata frekansı."""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

from .core import Encoder, Point, SEMBOLLER


def monte_carlo_report(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[Dict[str, float]],
    n_samples: int = 100_000,
    seed: int = 42,
) -> dict:
    """
    Kullanıcı olasılıkları altında Monte Carlo simülasyonu.

    Dönen alanlar (her biri p, pct, se, ci95, count içerir):
      kume_ici, p15, p14, p13, p12

    n_samples < 1 → ValueError (sessiz sıfır rapor yok).
    1 ≤ n_samples < 100 → çalışır ama 'warning' alanı eklenir.
    """
    if len(probs) != enc.total_len:
        raise ValueError(
            f"{len(probs)} maç için olasılık verildi, {enc.total_len} bekleniyordu."
        )
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

    rng = random.Random(seed)

    # Her maç için normalize kümülatif dağılım (toplam = 1)
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
        # son eşiği tam 1.0 yap (float kayması)
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

        if not all(outcome[i] in sel_sets[i] for i in range(enc.total_len)):
            continue
        n_ici += 1

        try:
            var = tuple(
                enc.variable_syms[j].index(outcome[pos])
                for j, pos in enumerate(enc.variable_pos)
            )
        except ValueError:
            continue

        if not cols:
            d = 99
        elif not enc.variable_pos:
            d = 0
        else:
            d = min(sum(a != b for a, b in zip(var, c)) for c in cols)

        dogru = 15 - d
        if dogru >= 15:
            n_15 += 1
        elif dogru == 14:
            n_14 += 1
        elif dogru == 13:
            n_13 += 1
        elif dogru == 12:
            n_12 += 1

    def rate(k: int) -> dict:
        p = k / n_samples if n_samples else 0.0
        se = math.sqrt(p * (1.0 - p) / n_samples) if n_samples else 0.0
        return {
            "p": p,
            "pct": round(100.0 * p, 3),
            "se": se,
            "ci95": round(1.96 * se * 100.0, 3),
            "count": k,
        }

    out = {
        "n_samples": n_samples,
        "kume_ici": rate(n_ici),
        "p15": rate(n_15),
        "p14": rate(n_14),
        "p13": rate(n_13),
        "p12": rate(n_12),
    }
    if warning:
        out["warning"] = warning
    return out


def match_error_frequency(
    enc: Encoder,
    cols: Sequence[Point],
    max_d: int = 2,
) -> dict:
    """
    Seçim kümesi içinde, her mesafe katmanı (d=1, d=2, ...) için
    hangi maçların hata ürettiğinin frekansı.

    Dönen yapı:
      n1, n2, d1: [{mac, count, pct}, ...], d2: [...]
    """
    from .core import distance_layers, dogrula_kaplama

    # Brute force only for modest spaces
    space = list(enc.variable_space()) if hasattr(enc, "variable_space") else []
    if not space:
        # reconstruct from alphabet
        from itertools import product
        space = list(product(*[range(k) for k in enc.alphabet_sizes]))

    if len(space) > 20000:
        return {"n1": 0, "n2": 0, "d1": [], "d2": [], "skipped": True}

    err1: Counter = Counter()
    err2: Counter = Counter()
    n1 = n2 = 0

    for pt in space:
        if not cols:
            continue
        dists = [sum(a != b for a, b in zip(pt, c)) for c in cols]
        d = min(dists) if dists else 99
        if d == 0:
            continue
        # which variable positions differ from nearest col
        nearest = cols[dists.index(d)]
        bad_pos = [j for j, (a, b) in enumerate(zip(pt, nearest)) if a != b]
        # map variable index → match number (1-based full index)
        for j in bad_pos:
            mac = enc.variable_pos[j] + 1
            if d == 1:
                err1[mac] += 1
            elif d == 2:
                err2[mac] += 1
        if d == 1:
            n1 += 1
        elif d == 2:
            n2 += 1

    def pack(counter: Counter, n: int):
        if n <= 0:
            return []
        rows = []
        for mac, cnt in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
            rows.append({
                "mac": mac,
                "count": cnt,
                "pct": round(100.0 * cnt / n, 2),
            })
        return rows

    return {
        "n1": n1,
        "n2": n2,
        "d1": pack(err1, n1),
        "d2": pack(err2, n2),
    }
