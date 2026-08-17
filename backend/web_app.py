"""Spor Toto API-only backend (JSON). Frontend = Next.js only."""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from flask import Flask, jsonify, request

from spor_toto.core import (
    Encoder, Fix16Hatasi, HAS_SCIPY, dogrula_kaplama,
    merge_rows, parse_picks, row_cost, distance_layers, olasilik_raporu,
    SEMBOLLER,
)
from spor_toto.engines import (
    run_auto, run_block, run_butce, run_exact, run_fix16, run_heuristic,
    run_maxcov,
)
from spor_toto.meta import (
    ENGINE_DEFAULTS, FIRE_MAX_MALIYET, FIRE_MAX_VARSAYILAN, LIMITS,
    MATCH_COUNT, MC_MAX, MC_MIN, MC_WEB_SAMPLES, MODE_IDS, MODES,
    meta_payload,
)
from spor_toto.report import basliklar
from spor_toto.analysis import monte_carlo_report, match_error_frequency
from spor_toto.fire_scenarios import fire_maliyeti, fire_scenario_report
from spor_toto.bayes import (
    STRENGTH_PRESETS, bayes_summary, bayes_update_matches, recommend_strengths,
)
from spor_toto.markov import markov_report
from spor_toto.health import check_envanteri, run_health
from spor_toto.history import (
    history_analytics, history_summary, history_week_detail, history_weeks,
)
from spor_toto.odds import season_1x2_summary, week_1x2
from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU, backtest
from spor_toto import __version__

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "spor-toto-api")

# Sabitler ve mod envanteri artik spor_toto.meta icinde: saglik katmani da
# ayni kaynaktan okuyor (bkz. health._check_meta_sozlesmesi).


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
    """CLI'de acik olan motor ayarlari; API'de sabit kodlanmislardi.

    Sinirlar `meta.LIMITS`'ten okunur: arayuzun gordugu bant ile burada
    uygulanan bant ayrisirsa kullanici sessizce kirpilan bir deger gonderir.
    """
    def _bant(ad: str, tip):
        lim = LIMITS[ad]
        return _sayi(data, ad, ENGINE_DEFAULTS[ad], tip, lim["min"], lim["max"])

    return {
        "trials": _bant("trials", int),
        "ls_iters": _bant("ls_iters", int),
        "seed": _sayi(data, "seed", ENGINE_DEFAULTS["seed"], int, 0, 2**31 - 1),
        "time_limit": _bant("time_limit", float),
        "block_limit": _bant("block_limit", int),
        "exact_limit": _bant("exact_limit", int),
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


# Kisa omurlu rapor onbellegi. Amaci iki tuketiciyi de korumak: sayfayi acik
# birakan kullanici (oto yenileme) ve arka arkaya vuran izleme. TTL bilerek
# kisadir — daha uzunu, sayfanin "az once olctum" iddiasini yalanlar.
HEALTH_TTL_S = float(os.environ.get("HEALTH_TTL_S", "5"))
_BASLANGIC = time.monotonic()
_health_onbellek: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_health_kilit = threading.Lock()


def _health_govde(only: Optional[str], fresh: bool) -> Dict[str, Any]:
    """Raporu üretir; TTL içinde tekrar istenirse önbellekten döner.

    Önbellekten dönen gövde bunu SAKLAMAZ: `summary.onbellek` alanı yaşını
    yazar. Bir sağlık raporunun ne zaman ölçüldüğünü gizlemesi, raporun
    kendisini değersizleştirir.
    """
    anahtar = only or ""
    simdi = time.monotonic()

    if not fresh and HEALTH_TTL_S > 0:
        with _health_kilit:
            kayit = _health_onbellek.get(anahtar)
        if kayit and (simdi - kayit[0]) <= HEALTH_TTL_S:
            govde = dict(kayit[1])
            govde["summary"] = {
                **govde.get("summary", {}),
                "onbellek": {
                    "cached": True,
                    "yas_ms": round((simdi - kayit[0]) * 1000, 1),
                    "ttl_s": HEALTH_TTL_S,
                },
            }
            return govde

    govde = run_health(only).to_dict()
    govde["summary"] = {
        **govde.get("summary", {}),
        "onbellek": {"cached": False, "yas_ms": 0.0, "ttl_s": HEALTH_TTL_S},
    }
    with _health_kilit:
        _health_onbellek[anahtar] = (simdi, govde)
    return govde


# ─── API only ─────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "spor-toto-api",
        "version": __version__,
        "frontend": "Next.js only — bu process HTML servis etmez",
        "endpoints": [
            "GET  /api/meta",
            "GET  /api/health         (readiness: tam değişmez raporu)",
            "GET  /api/health/checks",
            "GET  /api/stats",
            "GET  /api/stats/<week>",
            "GET  /api/backtest",
            "POST /api/solve",
            "GET  /health             (liveness: süreç ayakta mı)",
        ],
    })


@app.route("/health", methods=["GET"])
def health_liveness():
    """
    LIVENESS — "bu süreç ayakta mı?" Başka hiçbir şey.

    Eskiden bu yol `/api/health` ile AYNI handler'a bağliydi ve 21
    değişmezin tamamını koşuyordu (~500 ms, soğuk başlangıçta ~2,3 sn).
    Dağıtım hedefi autoscale: platform probe'u her vurdugunda bu bedel
    ödeniyordu ve probe zaman aşımına düşerse platform SAGLIKLI bir
    konteyneri öldürür — yani sağlık kontrolünün kendisi kesinti üretebilir.

    Bu uç hiçbir değişmez koşmaz; sürecin istek karşılayabildiğini söyler.
    Değişmezler "trafiğe hazır mıyım" sorusudur ve `/api/health`'in işidir.
    """
    return jsonify({
        "status": "ok",
        "service": "spor-toto-api",
        "version": __version__,
        "uptime_s": round(time.monotonic() - _BASLANGIC, 1),
        "readiness": "/api/health",
    })


@app.route("/api/health", methods=["GET"])
def api_health():
    """
    READINESS — degismezleri calistirip raporlar.

    `?only=` ile tek bir kontrol veya kategori calistirilabilir; arayuz
    dusen bir grubu butun takimi 500 ms bekletmeden yeniden deneyebilsin
    diye. `?fresh=1` onbellegi atlar. `degraded` (kritik olmayan kontrol
    dustu) 503 URETMEZ — servis calisiyordur, yalnizca bir yetenek eksiktir.
    """
    only = (request.args.get("only") or "").strip() or None
    fresh = (request.args.get("fresh") or "").strip().lower() in ("1", "true", "evet")
    try:
        govde = _health_govde(only, fresh)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify(govde), (200 if govde["ok"] else 503)


@app.route("/api/health/checks", methods=["GET"])
def api_health_checks():
    """Kontrol envanteri — calistirmadan, filtre menusunu beslemek icin."""
    return jsonify({
        "version": __version__,
        "checks": check_envanteri(),
    })


@app.route("/api/meta", methods=["GET"])
def api_meta():
    """
    Motorun yetenek envanteri. Frontend mod listesini, preset'leri ve
    sinirlari SABIT KODLAMAZ; hepsini buradan okur, boylece motorla
    tek kaynaktan senkron kalir.

    Govde `spor_toto.meta.meta_payload()` icinde uretilir: ayni envanteri
    saglik katmani da okuyup tutarliligini denetleyebilsin diye.
    """
    return jsonify(meta_payload(__version__))


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


def _parse_esik(raw: Any, varsayilan: float) -> float:
    """Eşik [0, 1] araligina kirpilir; gecersiz deger varsayilana duser."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return varsayilan
    return min(1.0, max(0.0, v))


@lru_cache(maxsize=32)
def _backtest_cached(last: Optional[int], banko: float, uclu: float,
                     sweep: bool) -> Dict[str, Any]:
    """Geri test sonucu istek basina yeniden hesaplanmaz.

    Veri seti surumlenmis bir dosyadir; ayni parametreler ayni cevabi verir.
    Tek strateji ~1,2 sn, 28 esikli tarama ilk cagrida ~15 sn surer (kaplama
    imzalari onbelleklenene kadar) ve sonrasinda milisaniyeye iner.
    """
    return backtest(last=last, banko_esik=banko, uclu_esik=uclu, sweep=sweep)


@app.route("/api/backtest", methods=["GET"])
def api_backtest():
    """
    "Bu strateji gecen sezon ne yapardi?"

    `?banko=` ve `?uclu=` esikleri, `?last=N` dilimi, `?sweep=0` ile tarama
    kapali. Cevap UC blok tasir ve ucu birlikte okunmalidir: secili
    stratejinin sezonu, esik taramasi ve **hold-out** — sonuncusu esigin o
    haftayi gormeden secildigi halde olculen sonuctur.
    """
    last = _parse_last(request.args.get("last"))
    banko = _parse_esik(request.args.get("banko"), VARSAYILAN_BANKO)
    uclu = _parse_esik(request.args.get("uclu"), VARSAYILAN_UCLU)
    sweep = str(request.args.get("sweep", "1")).strip().lower() not in {"0", "false", "no"}
    return jsonify(_backtest_cached(last, banko, uclu, sweep))


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
            r = run_fix16(enc, variant=variant)
        elif mode == "auto":
            r = run_auto(enc, eng)
        elif mode == "heuristic":
            r = run_heuristic(enc, eng)
        elif mode == "exact":
            r = run_exact(enc, eng)
        elif mode == "block":
            r = run_block(enc, eng)
        elif mode == "butce":
            if budget_raw is None or str(budget_raw).strip() == "":
                raise ValueError("Bütçe modu için budget gerekli")
            budget = int(budget_raw)
            # CLI'deki --plan-uygula karsiligi (1 tabanli). Once sadece
            # planlar[0] uygulanabiliyordu; artik kullanici UI'dan secebilir.
            b = run_butce(enc, budget, user_probs,
                          plan_count=plan_count, plan_apply=plan_apply,
                          variant=variant)
            idx, planlar = b["secili_index"], b["planlar"]
            butce_planlari = [_plan_to_dict(p, i + 1, i == idx)
                              for i, p in enumerate(planlar)]
            _log_step(run_log, "motor_butce",
                      f"plan={idx + 1}/{len(planlar)} bedel={planlar[idx].bedel}",
                      (time.perf_counter() - t1) * 1000)
            t1 = time.perf_counter()
            if user_probs is not None:
                run_log["mc_samples"] = mc_samples
            # Bu mod eskiden user_probs=None ile cagriliyordu; bu yuzden
            # butce modunda olasilik/Bayes/Markov analizi hic calismiyordu.
            result = _build_result(
                b["enc"], b["cols"], b["baslik"], b["notlar"],
                user_probs=user_probs,
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
            r = run_maxcov(enc, budget)

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
