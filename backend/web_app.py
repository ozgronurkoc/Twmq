"""Spor Toto API-only backend (JSON). Frontend = Next.js only."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from flask import Flask, jsonify, request

from spor_toto.core import (
    Encoder, Fix16Hatasi, HAS_SCIPY, butce_danismani, dogrula_kaplama,
    exact_cover, exact_max_coverage, greedy_full, ball,
    merge_rows, parse_picks, row_cost, solve_fix16,
    solve_by_blocks, solve_heuristic, distance_layers, olasilik_raporu,
    SEMBOLLER,
)
from spor_toto.report import basliklar
from spor_toto.analysis import monte_carlo_report, match_error_frequency
from spor_toto.fire_scenarios import fire_maliyeti, fire_scenario_report
from spor_toto.bayes import (
    STRENGTH_PRESETS, bayes_summary, bayes_update_matches, recommend_strengths,
)
from spor_toto.markov import markov_report
from spor_toto.health import run_health
from spor_toto.history import (
    history_analytics, history_summary, history_week_detail, history_weeks,
)
from spor_toto.odds import season_1x2_summary, week_1x2
from spor_toto import __version__

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "spor-toto-api")

MATCH_COUNT = 15
MC_WEB_SAMPLES = 80_000
MC_MIN, MC_MAX = 1_000, 200_000

# Fire analizi senkron istek yolunda calisiyor. Olculen hiz ~24 M
# maliyet-birimi/sn (maliyet = ayrik senaryo x kolon): 7,4 M -> 311 ms.
# 20 M esigi ~0,85 sn'ye denk gelir. Uclu iceren gercekci bir kupon
# 440 M cikar ve bilerek atlanir.
FIRE_MAX_MALIYET = 20_000_000
FIRE_MAX_VARSAYILAN = 2

# Motorun tum modlari. Bu liste /api/meta ile disari verilir; frontend
# mod listesini sabit kodlamaz, tek kaynak burasidir.
MODES: List[Dict[str, Any]] = [
    {"id": "fix16", "label": "Sabit 16 satır", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "Her zaman 16 kupon satırı. En az 7 çifte zorunlu. "
                 "Hamming(7,4) tabanlı, kanıtlanmış optimal."},
    {"id": "auto", "label": "Otomatik", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "En ucuz çözümü arar; satır sayısı değişkendir."},
    {"id": "exact", "label": "Kesin çözücü (ILP)", "garanti": True,
     "needs_budget": False, "needs_scipy": True,
     "aciklama": "ILP ile kanıtlanmış optimal. Yalnızca küçük uzaylarda."},
    {"id": "block", "label": "Blok ayrıştırma", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "r=1 bloğu + tam sistem ayrıştırması; cebirsel bloklar."},
    {"id": "heuristic", "label": "Sezgisel", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "Açgözlü + local search. Büyük uzaylar için."},
    {"id": "butce", "label": "Bütçe danışmanı", "garanti": True,
     "needs_budget": True, "needs_scipy": False,
     "aciklama": "Elimde N kolon var, hangi maçı kısmalıyım?"},
    {"id": "maxcov", "label": "Maksimum kapsama", "garanti": False,
     "needs_budget": True, "needs_scipy": False,
     "aciklama": "Sabit bütçeyle maksimum kapsama. GARANTİ VERMEZ."},
]
MODE_IDS = {m["id"] for m in MODES}

# CLI ile birebir ayni motor varsayilanlari (bkz. spor_toto/cli.py).
ENGINE_DEFAULTS: Dict[str, Any] = {
    "trials": 5,
    "ls_iters": 30_000,
    "seed": 42,
    "time_limit": 60.0,
    "block_limit": 256,
    "exact_limit": 512,
}


def _parse_prob_value(raw: Any) -> float:
    v = float(str(raw).replace(",", "."))
    if v < 0:
        return 0.0
    if v > 1.0:
        v = v / 100.0
    return min(v, 1.0)


def _matches_to_picks(matches: list) -> str:
    parts: List[str] = []
    for m in matches[:MATCH_COUNT]:
        if isinstance(m, list):
            order = {"1": 0, "0": 1, "2": 2}
            sel = sorted([str(x) for x in m], key=lambda s: order.get(s, 9))
            parts.append("".join(sel) or "102")
        else:
            parts.append(str(m) or "102")
    while len(parts) < MATCH_COUNT:
        parts.append("102")
    return ",".join(parts)


def _parse_json_probs(data: dict, selections: List[List[str]]) -> Optional[List[Dict[str, float]]]:
    """probs: [{1:0.5,0:0.3,2:0.2}, ...] veya {\"1\":[...],...} — yoksa None."""
    raw_probs = data.get("probs")
    if not raw_probs:
        return None
    out: List[Dict[str, float]] = []
    if isinstance(raw_probs, list):
        for i in range(MATCH_COUNT):
            p = {s: 0.0 for s in SEMBOLLER}
            if i < len(raw_probs) and isinstance(raw_probs[i], dict):
                for sym in SEMBOLLER:
                    if sym in raw_probs[i] and raw_probs[i][sym] not in (None, ""):
                        try:
                            p[sym] = _parse_prob_value(raw_probs[i][sym])
                        except (TypeError, ValueError):
                            p[sym] = 0.0
            total = sum(p.values())
            if total <= 0:
                sel = selections[i] if i < len(selections) else list(SEMBOLLER)
                u = 1.0 / len(sel) if sel else 1.0 / 3
                out.append({s: (u if s in sel else 0.0) for s in SEMBOLLER})
            else:
                out.append({s: v / total for s, v in p.items()})
        return out
    return None


def _sayi(data: dict, key: str, default: Any, cast: Callable = float,
          lo: Optional[float] = None, hi: Optional[float] = None) -> Any:
    """Govdeden sayi okur; bos/bozuk deger varsayilana duser, sinirlara kirpar."""
    raw = data.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raw = default
    try:
        val = cast(raw)
    except (TypeError, ValueError):
        val = cast(default)
    if lo is not None:
        val = max(lo, val)
    if hi is not None:
        val = min(hi, val)
    return val


def _engine_params(data: dict) -> Dict[str, Any]:
    """CLI'de acik olan motor ayarlari; API'de sabit kodlanmislardi."""
    return {
        "trials": _sayi(data, "trials", ENGINE_DEFAULTS["trials"], int, 1, 50),
        "ls_iters": _sayi(data, "ls_iters", ENGINE_DEFAULTS["ls_iters"], int, 100, 500_000),
        "seed": _sayi(data, "seed", ENGINE_DEFAULTS["seed"], int, 0, 2**31 - 1),
        "time_limit": _sayi(data, "time_limit", ENGINE_DEFAULTS["time_limit"], float, 1.0, 300.0),
        "block_limit": _sayi(data, "block_limit", ENGINE_DEFAULTS["block_limit"], int, 2, 6561),
        "exact_limit": _sayi(data, "exact_limit", ENGINE_DEFAULTS["exact_limit"], int, 2, 4096),
    }


def _resolve_bayes(data: dict) -> Tuple[float, float, Optional[str]]:
    """
    Bayes alpha / n cozumleme. `bayes_preset` verilmisse CLI ile BIREBIR ayni
    degerler kullanilir (tek kaynak: bayes.STRENGTH_PRESETS); yoksa ham
    prior_strength / evidence_strength okunur.
    """
    ham = data.get("bayes_preset")
    if ham not in (None, ""):
        key = str(ham).strip().lower().replace(" ", "_")
        if key not in STRENGTH_PRESETS:
            raise ValueError(
                f"Bilinmeyen bayes_preset {ham!r}. "
                f"Geçerli olanlar: {', '.join(STRENGTH_PRESETS)}")
        v = recommend_strengths(key)
        return float(v["prior_strength"]), float(v["evidence_strength"]), key
    return (
        _sayi(data, "prior_strength", 1.0, float, 0.0, 1000.0),
        _sayi(data, "evidence_strength", 10.0, float, 0.0, 10_000.0),
        None,
    )


def _plan_to_dict(plan, index: int, secili: bool) -> Dict[str, Any]:
    """ButcePlani -> JSON. Kullanici planlar arasindan UI'dan secebilsin diye."""
    return {
        "index": index,
        "bedel": plan.bedel,
        "satir": plan.satir,
        "selections": ["".join(s) for s in plan.selections],
        "degisiklikler": list(plan.degisiklikler),
        "p_kume_ici": (round(100 * plan.p_kume_ici, 3)
                       if plan.p_kume_ici is not None else None),
        "secili": secili,
    }


def _run_fix16(enc: Encoder, variant: int = 0) -> Dict[str, Any]:
    cols, aciklama = solve_fix16(enc, variant=variant)
    notlar = [aciklama]
    if variant:
        notlar.append(f"Varyant {variant}")
    return {"cols": cols, "baslik": f"Sabit 16 satır – {aciklama}", "notlar": notlar}


def _run_auto(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    aday = []
    r = solve_by_blocks(enc, max_block_space=eng["block_limit"],
                        time_limit=min(30.0, eng["time_limit"]))
    if r:
        aday.append((r[0], f"Blok ayrıştırma ({r[1]})", False))
    if enc.space_size() <= eng["exact_limit"] and HAS_SCIPY:
        cols, kanit = exact_cover(enc.alphabet_sizes,
                                  time_limit=min(30.0, eng["time_limit"]))
        if cols:
            aday.append((cols, "Kesin çözücü (ILP)", kanit))
    if not any(a[2] for a in aday):
        cols_h = solve_heuristic(enc, trials=eng["trials"],
                                 ls_iters=min(10_000, eng["ls_iters"]),
                                 seed=eng["seed"])
        aday.append((cols_h, "Heuristik (açgözlü + local search)", False))
    if not aday:
        raise RuntimeError("Hiçbir motor sonuç üretemedi.")
    en_az = min(len(a[0]) for a in aday)
    esitler = [a for a in aday if len(a[0]) == en_az]
    cols, baslik, _ = min(esitler, key=lambda a: len(merge_rows(a[0])))
    return {"cols": cols, "baslik": baslik, "notlar": []}


def _run_heuristic(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    cols = solve_heuristic(enc, trials=eng["trials"], ls_iters=eng["ls_iters"],
                           seed=eng["seed"])
    return {"cols": cols, "baslik": "Sezgisel (açgözlü + local search)",
            "notlar": [f"trials={eng['trials']} · ls_iters={eng['ls_iters']} "
                       f"· seed={eng['seed']}"]}


def _run_exact(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    """Kesin cozucu (ILP). CLI'de vardi, API'de hic acilmamisti."""
    if not HAS_SCIPY:
        raise ValueError(
            "Kesin çözücü (ILP) scipy gerektirir; bu kurulumda scipy yok. "
            "Bunun yerine 'block' veya 'heuristic' modunu kullanın.")
    cols, kanit = exact_cover(enc.alphabet_sizes, time_limit=eng["time_limit"])
    if cols is None:
        raise ValueError(
            f"ILP çözüm üretemedi (uzay {enc.space_size()}, zaman sınırı "
            f"{eng['time_limit']:.0f} sn). Uzayı küçültün ya da 'auto' deneyin.")
    return {
        "cols": cols,
        "baslik": "Kesin çözücü (ILP)",
        "notlar": [f"Optimallik: {'KANITLANDI' if kanit else 'kanıtlanmadı (zaman sınırı)'}"],
    }


def _run_block(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    """Blok ayristirma motoru. CLI'de vardi, API'de hic acilmamisti."""
    r = solve_by_blocks(enc, max_block_space=eng["block_limit"],
                        time_limit=eng["time_limit"])
    if not r:
        raise ValueError(
            "Blok ayrıştırma sonuç üretemedi. block_limit değerini artırmayı "
            "ya da 'auto' modunu deneyin.")
    cols, aciklama = r
    return {"cols": cols, "baslik": f"Blok ayrıştırma – {aciklama}",
            "notlar": [aciklama]}


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
    log["steps"].append({"name": name, "detail": detail, "ms": round(ms, 2)})


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
    mc_samples: int = MC_WEB_SAMPLES,
    fire_max: int = FIRE_MAX_VARSAYILAN,
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
            "count": dist[d], "pct": f"{pct:.2f}",
        })

    def _get(d):
        count = dist.get(d, 0)
        pct = 100 * count / total_space if total_space else 0
        return {"count": count, "pct": f"{pct:.2f}"}

    probs_uniform = {"15": _get(0), "14": _get(1), "13": _get(2), "12": _get(3)}

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
        mc = monte_carlo_report(enc, cols, work_probs, n_samples=mc_samples, seed=42)
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
        logger.exception("match_error_frequency failed")
        error_freq = None

    # Secim DISI fire analizi. Diger paneller kume ICI mesafeyi olcer;
    # bu, 14-garantinin gecerli OLMADIGI bolgeyi olcer.
    fire = None
    try:
        if fire_max > 0:
            maliyet = fire_maliyeti(enc, cols, max_fires=fire_max)
            if maliyet <= FIRE_MAX_MALIYET:
                fire = fire_scenario_report(enc, cols, max_fires=fire_max)
                fire["skipped"] = False
                fire["maliyet"] = maliyet
                fire["fire_max"] = fire_max
            else:
                # Sessizce None birakma: arayuz NEDEN yok oldugunu
                # soyleyebilmeli, yoksa "bozuk" gibi gorunur.
                fire = {
                    "skipped": True,
                    "maliyet": maliyet,
                    "esik": FIRE_MAX_MALIYET,
                    "fire_max": fire_max,
                    "reason": (
                        f"Bu kupon için fire analizi çok pahalı "
                        f"({maliyet:,} işlem birimi, sınır {FIRE_MAX_MALIYET:,}). "
                        f"fire_max değerini düşürerek yalnızca 1-fire "
                        f"hesaplatabilirsiniz."
                    ),
                }
    except Exception:
        logger.exception("fire_scenario_report failed")
        fire = None

    return {
        "baslik": baslik,
        "notlar": notlar,
        "satir_sayisi": len(rows),
        "kolon_bedeli": total_cost,
        "alt_sinir": enc.lower_bound(),
        "guaranteed": worst <= 1,
        "worst": worst,
        "acik": acik,
        "rows": decoded_rows,
        "dist": dist_items,
        "probs": probs_uniform,
        "advanced": advanced,
        "bayes": bayes_block,
        "markov": markov_block,
        "error_freq": error_freq,
        "fire": fire,
        "stat_lines": basliklar(enc),
        "match_count": enc.total_len,
        "total_space": total_space,
        "has_scipy": HAS_SCIPY,
    }


# ─── API only ─────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "spor-toto-api",
        "version": __version__,
        "frontend": "Next.js only — bu process HTML servis etmez",
        "endpoints": [
            "GET  /api/meta",
            "GET  /api/health",
            "GET  /api/stats",
            "GET  /api/stats/<week>",
            "POST /api/solve",
            "GET  /health",
        ],
    })


@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def api_health():
    report = run_health()
    code = 200 if report.ok else 503
    return jsonify(report.to_dict()), code


@app.route("/api/meta", methods=["GET"])
def api_meta():
    """
    Motorun yetenek envanteri. Frontend mod listesini, preset'leri ve
    sinirlari SABIT KODLAMAZ; hepsini buradan okur, boylece motorla
    tek kaynaktan senkron kalir.
    """
    return jsonify({
        "version": __version__,
        "has_scipy": HAS_SCIPY,
        "match_count": MATCH_COUNT,
        "symbols": list(SEMBOLLER),
        "modes": MODES,
        "bayes_presets": [
            {"id": k,
             "prior_strength": v["prior_strength"],
             "evidence_strength": v["evidence_strength"]}
            for k, v in STRENGTH_PRESETS.items()
        ],
        "engine_defaults": ENGINE_DEFAULTS,
        "limits": {
            "mc_samples": {"min": MC_MIN, "max": MC_MAX, "default": MC_WEB_SAMPLES},
            "fire_max": {"min": 0, "max": 2, "default": FIRE_MAX_VARSAYILAN},
            "fire_maliyet": {"min": 0, "max": FIRE_MAX_MALIYET},
            "plan_count": {"min": 1, "max": 50, "default": 5},
            "trials": {"min": 1, "max": 50},
            "ls_iters": {"min": 100, "max": 500_000},
            "time_limit": {"min": 1.0, "max": 300.0},
            "block_limit": {"min": 2, "max": 6561},
            "exact_limit": {"min": 2, "max": 4096},
        },
    })


def _parse_last(raw: Any) -> Optional[int]:
    """?last=N — son N hafta dilimi. Gecersiz/bos deger = tum sezon."""
    if raw is None or str(raw).strip() == "" or str(raw).strip().lower() == "all":
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """
    Tarihsel 1/0/2. `?last=N` verilirse ozet, bantlar VE analiz bloklarinin
    tamami ayni dilim uzerinden hesaplanir — arayuzdeki tek filtre satiri
    boylece butun gorselleri ayni veriye baglar.
    """
    last = _parse_last(request.args.get("last"))
    summary = history_summary(last)
    weeks = history_weeks(last)
    return jsonify({
        "meta": summary.get("meta", {}),
        "totals": summary.get("totals", {}),
        "weekly_avg": summary.get("weekly_avg", {}),
        "bands": summary.get("bands", {}),
        "data_quality": summary.get("data_quality", {}),
        "analytics": history_analytics(last),
        # Yalnizca MAC SONUCU (1X2). Arsivdeki diger pazarlar (alt/ust, Asya
        # handikap) analiz icindir, API'den cikmaz. Arsiv yoksa None doner.
        "odds": season_1x2_summary([w["week"] for w in weeks]),
        "weeks": weeks,
        "last": last,
        "error": summary.get("error"),
    })


@app.route("/api/stats/<int:week>", methods=["GET"])
def api_stats_week(week: int):
    w = history_week_detail(week)
    if not w:
        return jsonify({"error": f"{week}. hafta yok"}), 404
    oranlar = week_1x2(week)
    w["odds"] = {str(no): blok for no, blok in oranlar.items()}
    w["odds_hit"] = sum(1 for b in oranlar.values() if b["hit"])
    return jsonify(w)


@app.route("/api/solve", methods=["POST", "OPTIONS"])
def api_solve():
    if request.method == "OPTIONS":
        return "", 204

    t0 = time.perf_counter()
    run_log = _new_run_log()
    error = None
    result = None
    data = request.get_json(silent=True) or {}

    picks_str = (data.get("picks") or "").strip()
    if not picks_str and data.get("matches"):
        picks_str = _matches_to_picks(data["matches"])

    mode = str(data.get("mode") or "fix16")
    variant_raw = str(data.get("variant", "0") or "0")
    budget_raw = data.get("budget")
    use_bayes = bool(data.get("use_bayes", False))
    kati = bool(data.get("kati", False))
    mc_samples = _sayi(data, "mc_samples", MC_WEB_SAMPLES, int, MC_MIN, MC_MAX)
    fire_max = _sayi(data, "fire_max", FIRE_MAX_VARSAYILAN, int, 0, 2)
    plan_count = _sayi(data, "plan_count", 5, int, 1, 50)
    plan_apply = _sayi(data, "plan_apply", 1, int, 1, 50)
    eng = _engine_params(data)
    # Bayes preset'i gecersizse burada patlamali (asagidaki try onu 400'e cevirir).
    bayes_preset: Optional[str] = None
    prior_strength, evidence_strength = 1.0, 10.0

    run_log["mode"] = mode
    run_log["picks"] = picks_str
    run_log["variant"] = variant_raw
    run_log["budget"] = budget_raw
    run_log["use_bayes"] = use_bayes
    run_log["mc_samples"] = 0
    run_log["probs_filled"] = False

    try:
        prior_strength, evidence_strength, bayes_preset = _resolve_bayes(data)
        run_log["prior_strength"] = prior_strength
        run_log["evidence_strength"] = evidence_strength
        run_log["bayes_preset"] = bayes_preset

        if mode not in MODE_IDS:
            raise ValueError(
                f"Bilinmeyen mod {mode!r}. Geçerli olanlar: "
                f"{', '.join(m['id'] for m in MODES)}")
        if not picks_str:
            raise ValueError("picks veya matches zorunlu")

        t1 = time.perf_counter()
        selections = parse_picks(picks_str)
        enc = Encoder(selections, kati=kati)
        _log_step(
            run_log, "parse+encoder",
            f"banko={len(enc.banko_pos)} cifte={sum(1 for k in enc.alphabet_sizes if k == 2)} "
            f"uclu={sum(1 for k in enc.alphabet_sizes if k == 3)} uzay={enc.space_size()}",
            (time.perf_counter() - t1) * 1000,
        )

        t1 = time.perf_counter()
        user_probs = _parse_json_probs(data, selections)
        run_log["probs_filled"] = user_probs is not None
        _log_step(
            run_log, "parse_probs",
            "dolu" if user_probs is not None else "bos",
            (time.perf_counter() - t1) * 1000,
        )

        variant = int(variant_raw) if str(variant_raw).isdigit() else 0
        run_log["variant"] = variant

        t1 = time.perf_counter()
        r = None

        butce_planlari = None

        if mode == "fix16":
            r = _run_fix16(enc, variant=variant)
        elif mode == "auto":
            r = _run_auto(enc, eng)
        elif mode == "heuristic":
            r = _run_heuristic(enc, eng)
        elif mode == "exact":
            r = _run_exact(enc, eng)
        elif mode == "block":
            r = _run_block(enc, eng)
        elif mode == "butce":
            if budget_raw is None or str(budget_raw).strip() == "":
                raise ValueError("Bütçe modu için budget gerekli")
            budget = int(budget_raw)
            planlar = butce_danismani(enc, budget, user_probs, en_fazla=plan_count)
            if not planlar:
                raise ValueError(
                    f"{budget} kolonluk bütçeye sığan plan yok. Daha fazla banko veya bütçe artırın."
                )
            # CLI'deki --plan-uygula karsiligi (1 tabanli). Once sadece
            # planlar[0] uygulanabiliyordu; artik kullanici UI'dan secebilir.
            idx = min(plan_apply, len(planlar)) - 1
            secili = planlar[idx]
            butce_planlari = [_plan_to_dict(p, i + 1, i == idx)
                              for i, p in enumerate(planlar)]
            yeni_enc = Encoder(secili.selections)
            cols2, aciklama2 = solve_fix16(yeni_enc, variant=variant)
            notlar = [
                f"Uygulanan plan {idx + 1}/{len(planlar)}: "
                f"{'; '.join(secili.degisiklikler) or 'değişiklik yok'}",
                f"Plan bedeli: {secili.bedel} kolon, {secili.satir} satır",
            ]
            _log_step(run_log, "motor_butce",
                      f"plan={idx + 1}/{len(planlar)} bedel={secili.bedel}",
                      (time.perf_counter() - t1) * 1000)
            t1 = time.perf_counter()
            if user_probs is not None:
                run_log["mc_samples"] = mc_samples
            # Bu mod eskiden user_probs=None ile cagriliyordu; bu yuzden
            # butce modunda olasilik/Bayes/Markov analizi hic calismiyordu.
            result = _build_result(
                yeni_enc, cols2,
                f"Bütçe planı ({secili.bedel} kolon) – {aciklama2}",
                notlar, user_probs=user_probs,
                use_bayes=use_bayes and user_probs is not None,
                prior_strength=prior_strength,
                evidence_strength=evidence_strength,
                mc_samples=mc_samples,
                fire_max=fire_max,
            )
            _log_step(run_log, "build_result", "butce", (time.perf_counter() - t1) * 1000)
        elif mode == "maxcov":
            if budget_raw is None or str(budget_raw).strip() == "":
                raise ValueError("maxcov için budget gerekli")
            budget = int(budget_raw)
            r = _run_maxcov(enc, budget)

        if r is not None:
            _log_step(
                run_log, f"motor_{mode}",
                f"kolon={len(r['cols'])} | {r.get('baslik', '')}",
                (time.perf_counter() - t1) * 1000,
            )
            t1 = time.perf_counter()
            if user_probs is not None:
                run_log["mc_samples"] = mc_samples
            result = _build_result(
                enc, r["cols"], r["baslik"], r["notlar"], user_probs,
                use_bayes=use_bayes and user_probs is not None,
                prior_strength=prior_strength,
                evidence_strength=evidence_strength,
                mc_samples=mc_samples,
                fire_max=fire_max,
            )
            detail = "exact+MC+bayes" if user_probs is not None else "kaplama"
            _log_step(run_log, "build_result", detail, (time.perf_counter() - t1) * 1000)

        if result is not None:
            result["mode"] = mode
            result["bayes_preset"] = bayes_preset
            if butce_planlari is not None:
                result["butce_planlari"] = butce_planlari

        if result is not None and getattr(enc, "uyarilar", None):
            result["uyarilar"] = list(enc.uyarilar)
            run_log["warnings"].extend(list(enc.uyarilar))

        if result is not None:
            run_log["result_summary"] = {
                "satir": result.get("satir_sayisi"),
                "bedel": result.get("kolon_bedeli"),
                "garanti": result.get("guaranteed"),
                "worst": result.get("worst"),
                "advanced": bool(result.get("advanced")),
                "bayes": bool(result.get("bayes")),
                "markov": bool(result.get("markov")),
            }

    except (ValueError, RuntimeError, Fix16Hatasi) as e:
        error = str(e)
        run_log["error"] = error
        _log_step(run_log, "HATA", error, 0.0)
        logger.warning("api_solve: %s", error)
    except Exception as e:
        error = str(e)
        run_log["error"] = error
        logger.exception("api_solve unexpected")

    run_log["finished_at"] = datetime.now(timezone.utc).isoformat()
    run_log["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    if result is not None:
        result["run_log_text"] = _format_run_log(run_log)

    body = {
        "ok": error is None and result is not None,
        "error": error,
        "result": result,
        "run_log_text": _format_run_log(run_log),
        "version": __version__,
    }
    return jsonify(body), (200 if body["ok"] else 400)


_IZINLI_ALANLAR = ("replit.dev", "repl.co")


def _origin_izinli(origin: str) -> bool:
    """
    Origin allowlist'i HOSTNAME uzerinden kontrol eder.

    Onceki surum substring bakiyordu ('.replit.dev' in origin); bu yuzden
    https://x.replit.dev.attacker.com gibi bir origin de geciyordu.
    """
    if not origin:
        return False
    try:
        host = (urlparse(origin).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    return any(host == d or host.endswith("." + d) for d in _IZINLI_ALANLAR)


@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin", "")
    allowed = _origin_izinli(origin)
    if allowed and origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Vary"] = "Origin"
    return resp


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
