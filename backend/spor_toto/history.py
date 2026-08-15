"""Spor Toto tarihsel 1/0/2 istatistikleri.

Tek doğruluk kaynağı haftaların ``results`` dizisidir (15 karakter). Dosyadaki
``n1/n0/n2`` alanları bilgi amaçlı taşınır; dizi ile çeliştiklerinde fark
``data_quality`` bloğunda raporlanır — sessizce yutulmaz.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "st_history_2025_26.json"

SYMBOLS: Tuple[str, str, str] = ("1", "0", "2")
MATCH_COUNT = 15
RECENT_WINDOW = 6


@lru_cache(maxsize=1)
def load_history() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        return {
            "meta": {"weeks": 0, "matches": 0},
            "totals": {},
            "weekly_avg": {},
            "bands": {},
            "weeks": [],
            "error": f"Veri dosyasi yok: {DATA_FILE}",
        }
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


# ─── temel yardımcılar ────────────────────────────────────────────────────────

def _clean_results(raw: Any) -> str:
    """Sadece 1/0/2 karakterlerini bırakır."""
    return "".join(ch for ch in str(raw or "") if ch in SYMBOLS)


def _zero_counts() -> Dict[str, int]:
    return {s: 0 for s in SYMBOLS}


def _counts_of(results: str) -> Dict[str, int]:
    return {s: results.count(s) for s in SYMBOLS}


def _runs(results: str) -> List[Dict[str, Any]]:
    """Ardışık aynı sembol serilerini döndürür: [{symbol, start, length}]."""
    out: List[Dict[str, Any]] = []
    for i, ch in enumerate(results):
        if out and out[-1]["symbol"] == ch:
            out[-1]["length"] += 1
        else:
            out.append({"symbol": ch, "start": i + 1, "length": 1})
    return out


def _max_run(results: str) -> Dict[str, Any]:
    runs = _runs(results)
    if not runs:
        return {"symbol": "", "start": 0, "length": 0}
    return max(runs, key=lambda r: (r["length"], -r["start"]))


def _pct(part: float, total: float, digits: int = 4) -> float:
    return round(100.0 * part / total, digits) if total else 0.0


# ─── hafta normalizasyonu ─────────────────────────────────────────────────────

def normalized_weeks(last: Optional[int] = None) -> List[Dict[str, Any]]:
    """Hafta numarasına göre sıralı, türetilmiş alanlarla zenginleştirilmiş liste.

    ``last`` verilirse sadece son N hafta döner (istatistik dilimleme için).
    """
    rows: List[Dict[str, Any]] = []
    for w in load_history().get("weeks", []) or []:
        results = _clean_results(w.get("results"))
        derived = _counts_of(results)
        reported = {
            "1": int(w.get("n1") or 0),
            "0": int(w.get("n0") or 0),
            "2": int(w.get("n2") or 0),
        }
        mx = _max_run(results)
        rows.append({
            "week": int(w.get("week") or 0),
            "close_date": w.get("close_date") or "",
            "season": w.get("season") or "",
            "results": results,
            "n1": derived["1"],
            "n0": derived["0"],
            "n2": derived["2"],
            "counts": derived,
            "top": max(SYMBOLS, key=lambda s: (derived[s], -SYMBOLS.index(s))),
            "max_streak": mx,
            "complete": len(results) == MATCH_COUNT,
            "consistent": derived == reported,
            "reported_counts": None if derived == reported else reported,
        })
    rows.sort(key=lambda r: r["week"])
    if last is not None and last > 0:
        rows = rows[-last:]
    return rows


def _band(values: Sequence[int]) -> Dict[str, Any]:
    if not values:
        return {
            "avg": 0.0, "min": 0, "max": 0, "median": 0.0, "std": 0.0,
            "above_n": 0, "below_n": 0, "above_mean": 0.0, "below_mean": 0.0,
            "above_gap": 0.0, "below_gap": 0.0,
        }
    avg = statistics.fmean(values)
    above = [v for v in values if v > avg]
    below = [v for v in values if v <= avg]
    above_mean = statistics.fmean(above) if above else avg
    below_mean = statistics.fmean(below) if below else avg
    return {
        "avg": round(avg, 4),
        "min": min(values),
        "max": max(values),
        "median": round(statistics.median(values), 4),
        "std": round(statistics.pstdev(values), 4),
        "above_n": len(above),
        "below_n": len(below),
        "above_mean": round(above_mean, 4),
        "below_mean": round(below_mean, 4),
        "above_gap": round(above_mean - avg, 4),
        "below_gap": round(avg - below_mean, 4),
    }


def _data_quality(weeks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    weeks = list(weeks)
    conflicts = [
        {
            "week": w["week"],
            "close_date": w["close_date"],
            "reported": w["reported_counts"],
            "derived": w["counts"],
        }
        for w in weeks if not w["consistent"]
    ]
    incomplete = [w["week"] for w in weeks if not w["complete"]]
    by_results: Dict[str, List[int]] = defaultdict(list)
    for w in weeks:
        if w["results"]:
            by_results[w["results"]].append(w["week"])
    duplicates = [
        {"results": r, "weeks": sorted(ws)}
        for r, ws in by_results.items() if len(ws) > 1
    ]
    duplicates.sort(key=lambda d: d["weeks"][0])
    return {
        "source": "results",
        "weeks_total": len(weeks),
        "count_conflicts": conflicts,
        "incomplete_weeks": incomplete,
        "duplicate_results": duplicates,
        "ok": not conflicts and not incomplete and not duplicates,
    }


# ─── özet ─────────────────────────────────────────────────────────────────────

def history_summary(last: Optional[int] = None) -> Dict[str, Any]:
    data = load_history()
    weeks = normalized_weeks(last)
    n_weeks = len(weeks)
    matches = sum(len(w["results"]) for w in weeks)

    totals: Dict[str, Any] = {s: sum(w["counts"][s] for w in weeks) for s in SYMBOLS}
    for s in SYMBOLS:
        totals[f"pct_{s}"] = _pct(totals[s], matches)

    weekly_avg = {
        s: round(totals[s] / n_weeks, 4) if n_weeks else 0.0
        for s in SYMBOLS
    }
    bands = {s: _band([w["counts"][s] for w in weeks]) for s in SYMBOLS}

    meta = dict(data.get("meta", {}) or {})
    meta.update({
        "weeks": n_weeks,
        "matches": matches,
        "week_from": weeks[0]["week"] if weeks else None,
        "week_to": weeks[-1]["week"] if weeks else None,
        "sliced": bool(last and last > 0 and last < len(normalized_weeks())),
    })
    if weeks:
        meta["date_from"] = weeks[0]["close_date"] or meta.get("date_from")
        meta["date_to"] = weeks[-1]["close_date"] or meta.get("date_to")

    return {
        "meta": meta,
        "totals": totals,
        "weekly_avg": weekly_avg,
        "bands": bands,
        "week_count": n_weeks,
        "data_quality": _data_quality(weeks),
        "error": data.get("error"),
    }


def history_weeks(last: Optional[int] = None) -> List[Dict[str, Any]]:
    return normalized_weeks(last)


# ─── analitik bloklar ─────────────────────────────────────────────────────────

def position_stats(weeks: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Maç sırasına (1..15) göre 1/0/2 dağılımı."""
    out: List[Dict[str, Any]] = []
    for pos in range(MATCH_COUNT):
        counts = _zero_counts()
        for w in weeks:
            if pos < len(w["results"]):
                counts[w["results"][pos]] += 1
        n = sum(counts.values())
        out.append({
            "pos": pos + 1,
            "counts": counts,
            "pct": {s: _pct(counts[s], n, 2) for s in SYMBOLS},
            "n": n,
            "top": max(SYMBOLS, key=lambda s: (counts[s], -SYMBOLS.index(s))) if n else "",
        })
    return out


def transition_stats(weeks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Hafta içinde ardışık maçlarda sembol geçiş matrisi (3x3)."""
    counts: Dict[str, Dict[str, int]] = {s: _zero_counts() for s in SYMBOLS}
    for w in weeks:
        r = w["results"]
        for a, b in zip(r, r[1:]):
            counts[a][b] += 1
    total = sum(sum(row.values()) for row in counts.values())
    pct = {
        a: {b: _pct(counts[a][b], sum(counts[a].values()), 2) for b in SYMBOLS}
        for a in SYMBOLS
    }
    repeat = sum(counts[s][s] for s in SYMBOLS)
    return {
        "counts": counts,
        "pct": pct,
        "row_totals": {a: sum(counts[a].values()) for a in SYMBOLS},
        "n": total,
        "repeat_pct": _pct(repeat, total, 2),
    }


def count_distribution(weeks: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Her sembol için 'kaç haftada k adet çıktı' histogramı."""
    n = len(weeks)
    out: Dict[str, List[Dict[str, Any]]] = {}
    hi = 0
    per: Dict[str, Counter] = {}
    for s in SYMBOLS:
        c = Counter(w["counts"][s] for w in weeks)
        per[s] = c
        hi = max([hi] + list(c))
    for s in SYMBOLS:
        out[s] = [
            {"count": k, "weeks": per[s].get(k, 0), "pct": _pct(per[s].get(k, 0), n, 2)}
            for k in range(0, hi + 1)
        ]
    return out


def streak_stats(weeks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Hafta içi en uzun aynı-sembol serileri."""
    best: Dict[str, Dict[str, Any]] = {s: {"length": 0, "week": None, "start": 0} for s in SYMBOLS}
    all_runs: List[Dict[str, Any]] = []
    for w in weeks:
        for run in _runs(w["results"]):
            item = {
                "week": w["week"], "symbol": run["symbol"],
                "start": run["start"], "length": run["length"],
            }
            all_runs.append(item)
            s = run["symbol"]
            if run["length"] > best[s]["length"]:
                best[s] = {"length": run["length"], "week": w["week"], "start": run["start"]}
    all_runs.sort(key=lambda r: (-r["length"], r["week"], r["start"]))
    avg_max = (
        round(statistics.fmean([w["max_streak"]["length"] for w in weeks]), 2)
        if weeks else 0.0
    )
    return {"by_symbol": best, "top": all_runs[:8], "avg_week_max": avg_max}


def extreme_weeks(weeks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Her sembol için en yüksek/en düşük haftalar."""
    out: Dict[str, Any] = {}
    for s in SYMBOLS:
        if not weeks:
            out[s] = {"max": None, "min": None}
            continue
        hi = max(weeks, key=lambda w: (w["counts"][s], w["week"]))
        lo = min(weeks, key=lambda w: (w["counts"][s], w["week"]))
        out[s] = {
            "max": {"week": hi["week"], "value": hi["counts"][s], "results": hi["results"]},
            "min": {"week": lo["week"], "value": lo["counts"][s], "results": lo["results"]},
        }
    return out


def recent_form(weeks: Sequence[Dict[str, Any]], window: int = RECENT_WINDOW) -> Dict[str, Any]:
    """Son N haftanın ortalaması ve sezon ortalamasına göre sapması."""
    if not weeks:
        return {"window": 0, "weeks": [], "avg": _zero_counts(), "delta": _zero_counts()}
    tail = list(weeks[-window:])
    season_avg = {s: statistics.fmean([w["counts"][s] for w in weeks]) for s in SYMBOLS}
    tail_avg = {s: statistics.fmean([w["counts"][s] for w in tail]) for s in SYMBOLS}
    return {
        "window": len(tail),
        "weeks": [w["week"] for w in tail],
        "avg": {s: round(tail_avg[s], 2) for s in SYMBOLS},
        "delta": {s: round(tail_avg[s] - season_avg[s], 2) for s in SYMBOLS},
    }


def history_analytics(last: Optional[int] = None) -> Dict[str, Any]:
    weeks = normalized_weeks(last)
    return {
        "positions": position_stats(weeks),
        "transitions": transition_stats(weeks),
        "distribution": count_distribution(weeks),
        "streaks": streak_stats(weeks),
        "extremes": extreme_weeks(weeks),
        "recent": recent_form(weeks),
    }


# ─── tek hafta ────────────────────────────────────────────────────────────────

def history_week(week: int) -> Optional[Dict[str, Any]]:
    for w in normalized_weeks():
        if w["week"] == week:
            return w
    return None


def history_week_detail(week: int) -> Optional[Dict[str, Any]]:
    """Tek hafta + komşular + sezon ortalamasına göre konum."""
    weeks = normalized_weeks()
    idx = next((i for i, w in enumerate(weeks) if w["week"] == week), None)
    if idx is None:
        return None
    w = dict(weeks[idx])
    n = len(weeks)
    season_avg = {
        s: round(statistics.fmean([x["counts"][s] for x in weeks]), 4) for s in SYMBOLS
    } if n else _zero_counts()

    ranks: Dict[str, Any] = {}
    for s in SYMBOLS:
        ordered = sorted(weeks, key=lambda x: (-x["counts"][s], x["week"]))
        ranks[s] = {
            "rank": next(i for i, x in enumerate(ordered) if x["week"] == week) + 1,
            "of": n,
        }

    w.update({
        "prev_week": weeks[idx - 1]["week"] if idx > 0 else None,
        "next_week": weeks[idx + 1]["week"] if idx < n - 1 else None,
        "cells": [
            {"pos": i + 1, "symbol": ch} for i, ch in enumerate(w["results"])
        ],
        "runs": _runs(w["results"]),
        "season_avg": season_avg,
        "delta_vs_avg": {
            s: round(w["counts"][s] - season_avg[s], 2) for s in SYMBOLS
        },
        "rank": ranks,
        "position_stats": position_stats(weeks),
    })
    return w
