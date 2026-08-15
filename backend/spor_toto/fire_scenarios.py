"""Seçim dışı fire senaryoları (1-fire / 2-fire, banko-çifte)."""
from __future__ import annotations

from collections import Counter
from itertools import combinations, product
from typing import Dict, Sequence

from .core import Encoder, Point, SEMBOLLER


def fire_scenario_report(
    enc: Encoder,
    cols: Sequence[Point],
    max_fires: int = 2,
) -> dict:
    """
    Seçim dışı fire analizi (küme dışı).

    Tam k maç seçim dışında, diğerleri seçim içinde iken en iyi kolon
    skor dağılımı. Banko / çifte ayrımı ve maç bazlı özet.

    Not: Uniform '1 hata / 2 hata' küme *içi* mesafedir (d=1, d=2).
    Bu rapor seçim *dışı* fire içindir; ikisi farklıdır.
    """
    code_full = [enc.decode_full(c) for c in cols]
    n = enc.total_len
    ALL = tuple(SEMBOLLER)
    sel_sets = [set(s) for s in enc.selections]
    in_opts = [list(sel_sets[i]) for i in range(n)]
    out_opts = [[s for s in ALL if s not in sel_sets[i]] for i in range(n)]
    failable = [i for i in range(n) if out_opts[i]]

    def min_dist(x) -> int:
        best = n
        for c in code_full:
            d = sum(1 for i in range(n) if x[i] != c[i])
            if d < best:
                best = d
                if best == 0:
                    break
        return best

    def ftype(i: int) -> str:
        k = len(sel_sets[i])
        if k == 1:
            return "banko"
        if k == 2:
            return "double"
        return "triple"

    def pack(score_counts: Counter, n_total: int, by_type: dict, by_match: dict) -> dict:
        scores = {}
        pct = {}
        for s in range(n, n - 6, -1):
            cnt = int(score_counts.get(s, 0))
            scores[str(s)] = cnt
            pct[str(s)] = round(100.0 * cnt / n_total, 4) if n_total else 0.0
        for s, cnt in score_counts.items():
            if str(s) not in scores:
                scores[str(s)] = int(cnt)
                pct[str(s)] = round(100.0 * cnt / n_total, 4) if n_total else 0.0

        type_out = {}
        for tname, c in by_type.items():
            tot = sum(c.values())
            if tot == 0:
                continue
            type_out[tname] = {
                "n": tot,
                "scores": {str(k): int(v) for k, v in sorted(c.items(), reverse=True)},
                "pct": {
                    str(k): round(100.0 * v / tot, 4)
                    for k, v in sorted(c.items(), reverse=True)
                },
            }

        match_out = []
        for i in range(n):
            c = by_match.get(i, Counter())
            tot = sum(c.values())
            if tot == 0:
                match_out.append({
                    "mac": i + 1,
                    "type": ftype(i),
                    "n": 0,
                    "can_fail": bool(out_opts[i]),
                    "scores": {},
                    "pct": {},
                })
                continue
            match_out.append({
                "mac": i + 1,
                "type": ftype(i),
                "n": tot,
                "can_fail": True,
                "scores": {str(k): int(v) for k, v in sorted(c.items(), reverse=True)},
                "pct": {
                    str(k): round(100.0 * v / tot, 4)
                    for k, v in sorted(c.items(), reverse=True)
                },
            })

        return {
            "n": n_total,
            "scores": scores,
            "pct": pct,
            "by_type": type_out,
            "by_match": match_out,
            "min_best": min(score_counts.keys()) if score_counts else None,
            "max_best": max(score_counts.keys()) if score_counts else None,
            "p_ge_14": round(100.0 * sum(v for k, v in score_counts.items() if k >= 14) / n_total, 4) if n_total else 0.0,
            "p_ge_13": round(100.0 * sum(v for k, v in score_counts.items() if k >= 13) / n_total, 4) if n_total else 0.0,
            "p_ge_12": round(100.0 * sum(v for k, v in score_counts.items() if k >= 12) / n_total, 4) if n_total else 0.0,
        }

    out = {
        "note": "Secim disi fire: mac isaret disi. Uniform 1hata/2hata kume ici mesafedir."
    }

    if max_fires >= 1:
        sc: Counter = Counter()
        by_type: Dict[str, Counter] = {
            "banko": Counter(), "double": Counter(), "triple": Counter()
        }
        by_match: Dict[int, Counter] = {i: Counter() for i in range(n)}
        n_total = 0
        for fail_i in failable:
            ranges = [
                out_opts[k] if k == fail_i else in_opts[k] for k in range(n)
            ]
            ft = ftype(fail_i)
            for combo in product(*ranges):
                d = min_dist(combo)
                correct = n - d
                sc[correct] += 1
                by_type[ft][correct] += 1
                by_match[fail_i][correct] += 1
                n_total += 1
        out["fire1"] = pack(sc, n_total, by_type, by_match)

    if max_fires >= 2:
        sc = Counter()
        by_type = {
            "banko+banko": Counter(),
            "banko+double": Counter(),
            "double+double": Counter(),
        }
        by_match = {i: Counter() for i in range(n)}
        n_total = 0
        for i, j in combinations(failable, 2):
            ranges = []
            for k in range(n):
                if k == i or k == j:
                    ranges.append(out_opts[k])
                else:
                    ranges.append(in_opts[k])
            tkey = "+".join(sorted([ftype(i), ftype(j)]))
            if tkey not in by_type:
                by_type[tkey] = Counter()
            for combo in product(*ranges):
                d = min_dist(combo)
                correct = n - d
                sc[correct] += 1
                by_type[tkey][correct] += 1
                by_match[i][correct] += 1
                by_match[j][correct] += 1
                n_total += 1
        out["fire2"] = pack(sc, n_total, by_type, by_match)

    return out
