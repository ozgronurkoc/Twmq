# -*- coding: utf-8 -*-
"""web_app.py: history import + /stats + /health-ui routes."""
from pathlib import Path

p = Path("web_app.py")
t = p.read_text(encoding="utf-8")

if "from spor_toto.history import" not in t:
    t = t.replace(
        "from spor_toto.health import run_health",
        "from spor_toto.health import run_health\n"
        "from spor_toto.history import history_summary, history_weeks, history_week",
    )
    print("import ok")

if "def page_stats" not in t:
    block = '''

@app.route("/stats", methods=["GET"])
def page_stats():
    summary = history_summary()
    return render_template(
        "stats.html",
        active_page="stats",
        version=__version__,
        meta=summary.get("meta", {}),
        totals=summary.get("totals", {}),
        weekly_avg=summary.get("weekly_avg", {}),
        bands=summary.get("bands", {}),
        weeks=history_weeks(),
        error=summary.get("error"),
    )


@app.route("/stats/<int:week>", methods=["GET"])
def page_stats_week(week: int):
    ww = history_week(week)
    if not ww:
        return render_template(
            "stats.html",
            active_page="stats",
            version=__version__,
            meta={}, totals={}, weekly_avg={}, bands={}, weeks=[],
            error=f"{week}. hafta veri setinde yok.",
        ), 404
    return render_template(
        "stats_week.html",
        active_page="stats",
        version=__version__,
        week=ww,
    )


@app.route("/health-ui", methods=["GET"])
def page_health():
    import json as _json
    report = run_health()
    return render_template(
        "health.html",
        active_page="health",
        version=__version__,
        report_json=_json.dumps(report, ensure_ascii=False, indent=2),
    )

'''
    if '@app.route("/health"' in t:
        t = t.replace('@app.route("/health"', block + '\n@app.route("/health"', 1)
    else:
        t += block
    print("routes ok")
else:
    print("routes exist")

p.write_text(t, encoding="utf-8")
print("DONE")
