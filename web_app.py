"""Flask web interface for Spor Toto 14-garanti covering code generator."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request

from spor_toto.core import (
    Encoder, Fix16Hatasi, HAS_SCIPY, butce_danismani, dogrula_kaplama,
    exact_cover, exact_max_coverage, greedy_full, ball,
    merge_rows, parse_picks, row_cost, solve_fix16,
    solve_by_blocks, solve_heuristic, distance_layers, olasilik_raporu,
    SEMBOLLER,
)
from spor_toto.report import basliklar
from spor_toto.analysis import monte_carlo_report, match_error_frequency
from spor_toto.health import run_health
from spor_toto import __version__

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "spor-toto-web-default")

MATCH_COUNT = 15
SYMBOLS = [("1", "Ev (1)"), ("0", "Beraberlik (0)"), ("2", "Deplasman (2)")]
MODES = [
    ("fix16", "Fix-16 (16 satır, Hamming garantili)"),
    ("auto",  "Otomatik (en ucuz çözüm)"),
    ("butce", "Bütçe danışmanı"),
    ("maxcov","Maksimum kapsama"),
    ("heuristic", "Sezgisel"),
]

DEFAULT_PICKS = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


def _parse_form_picks(form) -> str:
    parts = []
    for i in range(1, MATCH_COUNT + 1):
        selected = form.getlist(f"match_{i}")
        if not selected:
            selected = ["1", "0", "2"]
        order = {"1": 0, "0": 1, "2": 2}
        selected.sort(key=lambda s: order.get(s, 9))
        parts.append("".join(selected))
    return ",".join(parts)


def _parse_prob_value(raw: str) -> float:
    v = float(raw.replace(",", "."))
    if v < 0:
        return 0.0
    if v > 1.0:
        v = v / 100.0
    return min(v, 1.0)


def _parse_form_probs(form, selections: List[List[str]]) -> Optional[List[Dict[str, float]]]:
    any_filled = False
    raw: List[Dict[str, float]] = []
    for i in range(1, MATCH_COUNT + 1):
        p: Dict[str, float] = {s: 0.0 for s in SEMBOLLER}
        for sym in SEMBOLLER:
            val = form.get(f"prob_{i}_{sym}", "").strip()
            if val != "":
                any_filled = True
                try:
                    p[sym] = _parse_prob_value(val)
                except ValueError:
                    p[sym] = 0.0
        raw.append(p)

    if not any_filled:
        return None

    out: List[Dict[str, float]] = []
    for i, p in enumerate(raw):
        total = sum(p.values())
        if total <= 0:
            sel = selections[i] if i < len(selections) else list(SEMBOLLER)
            u = 1.0 / len(sel) if sel else 1.0 / 3
            out.append({s: (u if s in sel else 0.0) for s in SEMBOLLER})
        else:
            out.append({s: v / total for s, v in p.items()})
    return out


def _run_fix16(enc: Encoder, variant: int = 0) -> Dict[str, Any]:
    cols, aciklama = solve_fix16(enc, variant=variant)
    return {"cols": cols, "baslik": f"Sabit 16 satır ({aciklama})", "notlar": [aciklama]}


def _run_auto(enc: Encoder, time_limit: float = 30.0) -> Dict[str, Any]:
    aday = []
    if HAS_SCIPY:
        r = solve_by_blocks(enc, max_block_space=256, time_limit=min(time_limit, 30.0))
        if r:
            aday.append((r[0], f"Blok ayrıştırma ({r[1]})", False))
        if enc.space_size() <= 512:
            cols, kanit = exact_cover(enc.alphabet_sizes, time_limit=time_limit)
            if cols:
                aday.append((cols, "Kesin çözücü (ILP)", kanit))
    cols_h = solve_heuristic(enc, trials=5, ls_iters=10000, seed=42)
    aday.append((cols_h, "Sezgisel (açgözlü + local search)", False))

    if not aday:
        raise RuntimeError("Hiçbir motor sonuç üretemedi.")
    en_az = min(len(a[0]) for a in aday)
    esitler = [a for a in aday if len(a[0]) == en_az]
    kanit = any(a[2] for a in esitler)
    cols, baslik, _ = min(esitler, key=lambda a: len(merge_rows(a[0])))
    notlar = []
    if cols and len(cols) == enc.lower_bound():
        notlar.append("Alt sınıra eşit → KANITLANMIŞ OPTİMAL")
    elif kanit:
        notlar.append("ILP optimalliği kanıtladı → KANITLANMIŞ OPTİMAL")
    if len(aday) > 1:
        notlar.append("Denenen motorlar: " +
                      ", ".join(f"{a[1].split(' (')[0]}={len(a[0])}" for a in aday))
    return {"cols": cols, "baslik": baslik, "notlar": notlar}


def _run_heuristic(enc: Encoder) -> Dict[str, Any]:
    cols = solve_heuristic(enc, trials=5, ls_iters=30000, seed=42)
    return {"cols": cols, "baslik": "Sezgisel (açgözlü + local search)", "notlar": []}


def _run_maxcov(enc: Encoder, budget: int) -> Dict[str, Any]:
    cols, kapsanan, kanit = exact_max_coverage(enc.alphabet_sizes, budget)
    if cols is None:
        import random
        g = greedy_full(list(enc.variable_space()), enc.alphabet_sizes, random.Random(42))
        cols = g[:budget]
        kapsanan = len({q for c in cols for q in ball(c, enc.alphabet_sizes)})
        kanit = False
    notlar = [
        f"Kapsanan nokta: {kapsanan}/{enc.space_size()} "
        f"(%{100 * kapsanan / enc.space_size():.2f})",
        f"Optimallik: {'KANITLANDI' if kanit else 'kanıtlanmadı (zaman sınırı)'}",
        "DİKKAT: bu bir GARANTİ DEĞİL, olasılıktır.",
    ]
    return {"cols": cols, "baslik": f"Maksimum kapsama – {budget} kolon", "notlar": notlar}


def _build_result(
    enc: Encoder,
    cols,
    baslik: str,
    notlar: List[str],
    user_probs: Optional[List[Dict[str, float]]] = None,
) -> Dict[str, Any]:
    rows = merge_rows(cols)
    total_cost = sum(row_cost(r) for r in rows)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    dist = distance_layers(cols, enc.alphabet_sizes)
    total_space = enc.space_size()

    decoded_rows = []
    for r in rows:
        cells = list(enc.decode_row(r))
        cost = row_cost(r)
        decoded_rows.append({"cells": cells, "cost": cost})

    dist_items = []
    for d in sorted(dist):
        dogru = 15 - d
        pct = 100 * dist[d] / total_space if total_space else 0
        dist_items.append({
            "d": d, "dogru": dogru, "label": f"{dogru} doğru",
            "count": dist[d], "pct": f"{pct:.2f}"
        })

    def _get(d):
        count = dist.get(d, 0)
        pct = 100 * count / total_space if total_space else 0
        return {"count": count, "pct": f"{pct:.2f}"}

    probs_uniform = {
        "15": _get(0), "14": _get(1), "13": _get(2), "12": _get(3),
    }

    advanced = None
    if user_probs is not None:
        rap = olasilik_raporu(enc, cols, user_probs)
        mc = monte_carlo_report(enc, cols, user_probs, n_samples=80_000, seed=42)
        advanced = {
            "exact": {
                "p_kume_ici": round(100 * rap.p_kume_ici, 3),
                "p_15": round(100 * rap.p_15, 3),
                "p_14": round(100 * rap.p_14, 3),
                "p_tek": round(100 * rap.p_tek_kolon_15, 3),
            },
            "monte_carlo": mc,
        }

    error_freq = None
    try:
        if enc.space_size() <= 20000:
            error_freq = match_error_frequency(enc, cols, max_d=2)
    except Exception:
        logger.exception(
            "match_error_frequency failed (space=%s, cols=%s)",
            enc.space_size(), len(cols) if cols is not None else 0,
        )
        error_freq = None

    guaranteed = worst <= 1
    return {
        "baslik": baslik,
        "notlar": notlar,
        "satir_sayisi": len(rows),
        "kolon_bedeli": total_cost,
        "alt_sinir": enc.lower_bound(),
        "guaranteed": guaranteed,
        "worst": worst,
        "acik": acik,
        "rows": decoded_rows,
        "dist": dist_items,
        "probs": probs_uniform,
        "advanced": advanced,
        "error_freq": error_freq,
        "stat_lines": basliklar(enc),
        "match_count": enc.total_len,
        "total_space": total_space,
    }


@app.route("/health", methods=["GET"])
def health():
    report = run_health()
    code = 200 if report.ok else 503
    return jsonify(report.to_dict()), code


@app.route("/", methods=["GET"])
def index():
    default_selections = []
    try:
        sels = parse_picks(DEFAULT_PICKS)
        for s in sels:
            default_selections.append(s)
    except Exception:
        default_selections = [["1", "0", "2"]] * MATCH_COUNT
    while len(default_selections) < MATCH_COUNT:
        default_selections.append(["1", "0", "2"])

    return render_template(
        "index.html",
        version=__version__,
        match_count=MATCH_COUNT,
        symbols=SYMBOLS,
        modes=MODES,
        default_selections=default_selections,
        result=None,
        error=None,
        form_data=None,
        has_scipy=HAS_SCIPY,
    )


@app.route("/solve", methods=["POST"])
def solve():
    error = None
    result = None

    picks_str = _parse_form_picks(request.form)
    mode = request.form.get("mode", "fix16")
    budget_raw = request.form.get("budget", "").strip()
    variant_raw = request.form.get("variant", "0").strip()

    form_selections = []
    for i in range(1, MATCH_COUNT + 1):
        form_selections.append(request.form.getlist(f"match_{i}"))

    try:
        selections = parse_picks(picks_str)
        enc = Encoder(selections)
        user_probs = _parse_form_probs(request.form, selections)

        variant = int(variant_raw) if variant_raw.isdigit() else 0

        if mode == "fix16":
            r = _run_fix16(enc, variant=variant)
        elif mode == "auto":
            r = _run_auto(enc)
        elif mode == "heuristic":
            r = _run_heuristic(enc)
        elif mode == "butce":
            if not budget_raw or not budget_raw.isdigit():
                raise ValueError("Bütçe modu için bir kolon bütçesi giriniz.")
            budget = int(budget_raw)
            planlar = butce_danismani(enc, budget, user_probs, en_fazla=5)
            if not planlar:
                raise ValueError(
                    f"{budget} kolonluk bütçeye sığan plan bulunamadı. "
                    "Daha fazla maçı bankoya çevirmeniz ya da bütçeyi artırmanız gerekiyor."
                )
            secili = planlar[0]
            from spor_toto.core import Encoder as Enc2
            yeni_enc = Enc2(secili.selections)
            cols2, aciklama2 = solve_fix16(yeni_enc, variant=0)
            notlar = [f"Uygulanan değişiklikler: {'; '.join(secili.degisiklikler) or 'yok'}",
                      f"Plan bedeli: {secili.bedel} kolon, {secili.satir} satır"]
            result = _build_result(
                yeni_enc, cols2,
                f"Bütçe planı ({secili.bedel} kolon) – {aciklama2}",
                notlar, user_probs=None,
            )
        elif mode == "maxcov":
            if not budget_raw or not budget_raw.isdigit():
                raise ValueError("Maksimum kapsama modu için bir kolon bütçesi giriniz.")
            budget = int(budget_raw)
            r = _run_maxcov(enc, budget)
        else:
            r = _run_fix16(enc)

        if mode != "butce":
            result = _build_result(enc, r["cols"], r["baslik"], r["notlar"], user_probs)

        if result is not None and enc.uyarilar:
            result["uyarilar"] = enc.uyarilar

    except (ValueError, RuntimeError, Fix16Hatasi) as e:
        error = str(e)

    return render_template(
        "index.html",
        version=__version__,
        match_count=MATCH_COUNT,
        symbols=SYMBOLS,
        modes=MODES,
        default_selections=form_selections,
        result=result,
        error=error,
        form_data=request.form,
        has_scipy=HAS_SCIPY,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
