# -*- coding: utf-8 -*-
"""web_app.py icine /api/health /api/stats /api/solve + CORS ekler."""
from pathlib import Path

p = Path("web_app.py")
t = p.read_text(encoding="utf-8")

if "from spor_toto.history import" not in t:
    t = t.replace(
        "from spor_toto.health import run_health",
        "from spor_toto.health import run_health\nfrom spor_toto.history import history_summary, history_weeks, history_week",
    )

if "def api_solve" not in t:
    block = r'''

@app.route("/api/health", methods=["GET"])
def api_health():
    report = run_health()
    code = 200 if report.ok else 503
    return jsonify(report.to_dict()), code


@app.route("/api/stats", methods=["GET"])
def api_stats():
    summary = history_summary()
    return jsonify({
        "meta": summary.get("meta", {}),
        "totals": summary.get("totals", {}),
        "weekly_avg": summary.get("weekly_avg", {}),
        "bands": summary.get("bands", {}),
        "weeks": history_weeks(),
        "error": summary.get("error"),
    })


@app.route("/api/stats/<int:week>", methods=["GET"])
def api_stats_week(week: int):
    w = history_week(week)
    if not w:
        return jsonify({"error": f"{week}. hafta yok"}), 404
    return jsonify(w)


@app.route("/api/solve", methods=["POST"])
def api_solve():
    t0 = time.perf_counter()
    run_log = _new_run_log()
    error = None
    result = None
    data = request.get_json(silent=True) or {}
    if request.is_json and data:
        picks_str = data.get("picks") or ""
        if not picks_str and "matches" in data:
            parts = []
            for m in data["matches"][:MATCH_COUNT]:
                if isinstance(m, list):
                    order = {"1": 0, "0": 1, "2": 2}
                    sel = sorted([str(x) for x in m], key=lambda s: order.get(s, 9))
                    parts.append("".join(sel) or "102")
                else:
                    parts.append(str(m) or "102")
            while len(parts) < MATCH_COUNT:
                parts.append("102")
            picks_str = ",".join(parts)
        mode = data.get("mode", "fix16")
        variant_raw = str(data.get("variant", "0") or "0")
        use_bayes = bool(data.get("use_bayes", False))
    else:
        picks_str = _parse_form_picks(request.form)
        mode = request.form.get("mode", "fix16")
        variant_raw = request.form.get("variant", "0")
        use_bayes = request.form.get("use_bayes") == "1"
    try:
        selections = parse_picks(picks_str)
        enc = Encoder(selections)
        variant = int(variant_raw) if str(variant_raw).isdigit() else 0
        r = _run_fix16(enc, variant=variant) if mode == "fix16" else _run_auto(enc)
        result = _build_result(enc, r["cols"], r["baslik"], r["notlar"], None)
    except Exception as e:
        error = str(e)
        run_log["error"] = error
    run_log["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    run_log["finished_at"] = datetime.now(timezone.utc).isoformat()
    body = {
        "ok": error is None and result is not None,
        "error": error,
        "result": result,
        "run_log_text": _format_run_log(run_log),
        "version": __version__,
    }
    return jsonify(body), (200 if body["ok"] else 400)


@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin", "")
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp
'''
    if 'if __name__ == "__main__":' in t:
        t = t.replace('if __name__ == "__main__":', block + '\nif __name__ == "__main__":', 1)
    else:
        t += block
    print("api routes eklendi")
else:
    print("api routes zaten var")

p.write_text(t, encoding="utf-8")
print("DONE")
