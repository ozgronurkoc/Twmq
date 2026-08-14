"""Flask web interface for Spor Toto 14-garanti covering code generator."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
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
from spor_toto.bayes import bayes_summary, bayes_update_matches
from spor_toto.markov import markov_report
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
MC_WEB_SAMPLES = 80_000


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
    notlar = [aciklama]
    if variant:
        notlar.append(f"Varyant {variant}")
    return {"cols": cols, "baslik": f"Sabit 16 satır – {aciklama}", "notlar": notlar}


def _run_auto(enc: Encoder) -> Dict[str, Any]:
    aday = []
    r = solve_by_blocks(enc, max_block_space=256, time_limit=30.0)
    if r:
        aday.append((r[0], f"Blok ayrıştırma ({r[1]})", False))
    if enc.space_size() <= 512 and HAS_SCIPY:
        cols, kanit = exact_cover(enc.alphabet_sizes, time_limit=30.0)
        if cols:
            aday.append((cols, "Kesin çözücü (ILP)", kanit))
    if not any(a[2] for a in aday):
        cols_h = solve_heuristic(enc, trials=5, ls_iters=10000, seed=42)
        aday.append((cols_h, "Heuristik (açgözlü + local search)", False))
    if not aday:
        raise RuntimeError("Hiçbir motor sonuç üretemedi.")
    en_az = min(len(a[0]) for a in aday)
    esitler = [a for a in aday if len(a[0]) == en_az]
    cols, baslik, _ = min(esitler, key=lambda a: len(merge_rows(a[0])))
    return {"cols": cols, "baslik": baslik, "notlar": []}


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


def _new_run_log() -> Dict[str, Any]:
    return {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": [],
        "warnings": [],
        "error": None,
    }


def _log_step(log: Dict[str, Any], name: str, detail: str = "", ms: float = 0.0) -> None:
    log["steps"].append({
        "name": name,
        "detail": detail,
        "ms": round(ms, 2),
    })


def _format_run_log(log: Dict[str, Any]) -> str:
    lines = [
        "=== SPOR TOTO ÇALIŞMA LOGU ===",
        f"başlangıç (UTC): {log.get('started_at', '')}",
        f"bitiş (UTC)    : {log.get('finished_at', '')}",
        f"süre toplam    : {log.get('total_ms', 0):.1f} ms",
        f"mod            : {log.get('mode', '')}",
        f"picks          : {log.get('picks', '')}",
        f"variant        : {log.get('variant', 0)}",
        f"budget         : {log.get('budget', '')}",
        f"probs dolu     : {log.get('probs_filled', False)}",
        f"bayes          : {log.get('use_bayes', False)}",
        f"prior α / n    : {log.get('prior_strength', '')} / {log.get('evidence_strength', '')}",
        f"MC örnek       : {log.get('mc_samples', 0)}  (0 = çalışmadı)",
        "--- adımlar ---",
    ]
    for s in log.get("steps") or []:
        lines.append(f"  [{s.get('ms', 0):8.1f} ms] {s.get('name', '')}: {s.get('detail', '')}")
    if log.get("warnings"):
        lines.append("--- uyarılar ---")
        for w in log["warnings"]:
            lines.append(f"  ! {w}")
    if log.get("error"):
        lines.append("--- hata ---")
        lines.append(f"  {log['error']}")
    if log.get("result_summary"):
        lines.append("--- sonuç özeti ---")
        for k, v in log["result_summary"].items():
            lines.append(f"  {k}: {v}")
    lines.append("=== LOG SONU ===")
    return "\n".join(lines)


def _build_result(
    enc: Encoder,
    cols,
    baslik: str,
    notlar: List[str],
    user_probs: Optional[List[Dict[str, float]]] = None,
    use_bayes: bool = False,
    prior_strength: float = 1.0,
    evidence_strength: float = 10.0,
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
    bayes_block = None
    markov_block = None
    if user_probs is not None:
        work_probs = user_probs
        if use_bayes:
            updates = bayes_update_matches(
                enc.selections, user_probs,
                prior_strength=prior_strength,
                evidence_strength=evidence_strength,
            )
            work_probs = [u["posterior"] for u in updates]
            bayes_block = {
                "prior_strength": prior_strength,
                "evidence_strength": evidence_strength,
                "summary": bayes_summary(updates),
                "matches": [
                    {
                        "mac": i + 1,
                        "prior": {s: round(float(u["prior"][s]), 4) for s in SEMBOLLER},
                        "evidence": {s: round(float(u["evidence"][s]), 4) for s in SEMBOLLER},
                        "posterior": {s: round(float(u["posterior"][s]), 4) for s in SEMBOLLER},
                        "kl": float(u["kl_prior_post"]),
                        "kl_label": u.get("kl_label", ""),
                    }
                    for i, u in enumerate(updates)
                ],
            }

        rap = olasilik_raporu(enc, cols, work_probs)
        mc = monte_carlo_report(enc, cols, work_probs, n_samples=MC_WEB_SAMPLES, seed=42)
        advanced = {
            "exact": {
                "p_kume_ici": round(100 * rap.p_kume_ici, 3),
                "p_15": round(100 * rap.p_15, 3),
                "p_14": round(100 * rap.p_14, 3),
                "p_tek": round(100 * rap.p_tek_kolon_15, 3),
            },
            "monte_carlo": mc,
            "source": "bayes_posterior" if use_bayes else "user_probs",
        }
        try:
            markov_block = markov_report(enc, cols, work_probs)
        except Exception:
            logger.exception("markov_report failed")
            markov_block = None

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
        "bayes": bayes_block,
        "markov": markov_block,
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
        run_log_text=None,
    )


@app.route("/solve", methods=["POST"])
def solve():
    error = None
    result = None
    t0 = time.perf_counter()
    run_log = _new_run_log()

    picks_str = _parse_form_picks(request.form)
    mode = request.form.get("mode", "fix16")
    budget_raw = request.form.get("budget", "").strip()
    variant_raw = request.form.get("variant", "0").strip()
    use_bayes = request.form.get("use_bayes") == "1"
    try:
        prior_strength = float(request.form.get("prior_strength", "1") or "1")
    except ValueError:
        prior_strength = 1.0
    try:
        evidence_strength = float(request.form.get("evidence_strength", "10") or "10")
    except ValueError:
        evidence_strength = 10.0

    form_selections = []
    for i in range(1, MATCH_COUNT + 1):
        form_selections.append(request.form.getlist(f"match_{i}"))

    run_log["mode"] = mode
    run_log["picks"] = picks_str
    run_log["variant"] = variant_raw
    run_log["budget"] = budget_raw
    run_log["use_bayes"] = use_bayes
    run_log["prior_strength"] = prior_strength
    run_log["evidence_strength"] = evidence_strength
    run_log["mc_samples"] = 0
    run_log["probs_filled"] = False

    try:
        t1 = time.perf_counter()
        selections = parse_picks(picks_str)
        enc = Encoder(selections)
        _log_step(
            run_log, "parse+encoder",
            f"banko={len(enc.banko_pos)} cifte={sum(1 for k in enc.alphabet_sizes if k==2)} "
            f"uclu={sum(1 for k in enc.alphabet_sizes if k==3)} uzay={enc.space_size()}",
            (time.perf_counter() - t1) * 1000,
        )

        t1 = time.perf_counter()
        user_probs = _parse_form_probs(request.form, selections)
        run_log["probs_filled"] = user_probs is not None
        _log_step(
            run_log, "parse_probs",
            "dolu" if user_probs is not None else "bos (MC/Bayes atlanacak)",
            (time.perf_counter() - t1) * 1000,
        )

        variant = int(variant_raw) if variant_raw.isdigit() else 0
        run_log["variant"] = variant

        t1 = time.perf_counter()
        r = None
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
            notlar = [
                f"Uygulanan değişiklikler: {'; '.join(secili.degisiklikler) or 'yok'}",
                f"Plan bedeli: {secili.bedel} kolon, {secili.satir} satır",
            ]
            _log_step(
                run_log, "motor_butce",
                f"plan bedel={secili.bedel} satir={secili.satir}",
                (time.perf_counter() - t1) * 1000,
            )
            t1 = time.perf_counter()
            result = _build_result(
                yeni_enc, cols2,
                f"Bütçe planı ({secili.bedel} kolon) – {aciklama2}",
                notlar, user_probs=None,
            )
            _log_step(run_log, "build_result", "butce (probs yok)",
                      (time.perf_counter() - t1) * 1000)
        elif mode == "maxcov":
            if not budget_raw or not budget_raw.isdigit():
                raise ValueError("Maksimum kapsama modu için bir kolon bütçesi giriniz.")
            budget = int(budget_raw)
            r = _run_maxcov(enc, budget)
        else:
            r = _run_fix16(enc)

        if mode != "butce" and r is not None:
            _log_step(
                run_log, f"motor_{mode}",
                f"kolon={len(r['cols'])} | {r.get('baslik', '')}",
                (time.perf_counter() - t1) * 1000,
            )
            t1 = time.perf_counter()
            if user_probs is not None:
                run_log["mc_samples"] = MC_WEB_SAMPLES
            result = _build_result(
                enc, r["cols"], r["baslik"], r["notlar"], user_probs,
                use_bayes=use_bayes and user_probs is not None,
                prior_strength=prior_strength,
                evidence_strength=evidence_strength,
            )
            detail = "exact+MC+bayes" if user_probs is not None else "sadece kaplama (MC yok)"
            _log_step(run_log, "build_result", detail,
                      (time.perf_counter() - t1) * 1000)

        if result is not None and enc.uyarilar:
            result["uyarilar"] = enc.uyarilar
            run_log["warnings"].extend(list(enc.uyarilar))

        if result is not None:
            run_log["result_summary"] = {
                "satir": result.get("satir_sayisi"),
                "bedel": result.get("kolon_bedeli"),
                "garanti": result.get("guaranteed"),
                "worst": result.get("worst"),
                "advanced": bool(result.get("advanced")),
                "bayes": bool(result.get("bayes")),
            }

    except (ValueError, RuntimeError, Fix16Hatasi) as e:
        error = str(e)
        run_log["error"] = error
        _log_step(run_log, "HATA", error, 0.0)
        logger.warning("solve failed: %s", error)

    run_log["finished_at"] = datetime.now(timezone.utc).isoformat()
    run_log["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    run_log_text = _format_run_log(run_log)
    if result is not None:
        result["run_log"] = run_log
        result["run_log_text"] = run_log_text

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
        run_log_text=run_log_text,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
