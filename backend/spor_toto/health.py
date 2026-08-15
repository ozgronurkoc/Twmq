"""Sistem sağlık kontrolü — tüm katmanları tek vücut olarak doğrular.

Kullanım:
  python -m spor_toto.health
  python -m spor_toto.health --interval 60
  python -m spor_toto.health --json
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from . import __version__
from .core import (
    HAS_SCIPY,
    Encoder,
    Fix16Hatasi,
    dogrula_kaplama,
    distance_layers,
    merge_rows,
    olasilik_raporu,
    parse_picks,
    row_cost,
    rows_to_points,
    solve_fix16,
    solve_by_blocks,
    solve_heuristic,
)
from .analysis import match_error_frequency, monte_carlo_report
from .bayes import posteriors_only
from .markov import markov_report
from .report import basliklar

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
SEMBOLLER = ("1", "0", "2")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class HealthReport:
    version: str
    timestamp: str
    ok: bool
    checks: List[CheckResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "ok": self.ok,
            "passed": sum(1 for c in self.checks if c.ok),
            "failed": sum(1 for c in self.checks if not c.ok),
            "total": len(self.checks),
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "detail": c.detail,
                    "duration_ms": round(c.duration_ms, 1),
                }
                for c in self.checks
            ],
            "summary": self.summary,
        }


def _run(name: str, fn: Callable[[], str]) -> CheckResult:
    t0 = time.perf_counter()
    try:
        detail = fn() or "ok"
        return CheckResult(name, True, detail, (time.perf_counter() - t0) * 1000)
    except Exception as e:
        return CheckResult(
            name, False, f"{type(e).__name__}: {e}", (time.perf_counter() - t0) * 1000
        )


def _approx(a: float, b: float, rel: float = 1e-9) -> bool:
    return abs(a - b) <= rel * max(1.0, abs(b))


def _probs_on_selections(enc: Encoder) -> List[Dict[str, float]]:
    out: List[Dict[str, float]] = []
    for sel in enc.selections:
        p = {s: 0.0 for s in SEMBOLLER}
        u = 1.0 / len(sel) if sel else 1.0 / 3
        for s in sel:
            p[s] = u
        out.append(p)
    return out


def _check_encoder() -> str:
    enc = Encoder(parse_picks(ORNEK))
    assert enc.total_len == 15
    assert enc.n == 8
    assert enc.space_size() == 256
    assert enc.lower_bound() == math.ceil(256 / 9)
    return f"n={enc.n} space={enc.space_size()} lb={enc.lower_bound()}"


def _check_fix16_garanti() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    rows = merge_rows(cols)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert len(rows) == 16
    assert worst <= 1 and acik == 0
    assert set(rows_to_points(rows)) == set(cols)
    assert sum(row_cost(r) for r in rows) == len(cols)
    return f"rows=16 bedel={len(cols)} worst={worst}"


def _check_fix16_yetersiz_cifte() -> str:
    enc = Encoder(parse_picks("10,10,10,10,10,10,1,1,1,1,1,1,1,1,1"))
    try:
        solve_fix16(enc)
        raise AssertionError("Fix16Hatasi bekleniyordu")
    except Fix16Hatasi:
        return "6 cifte reddedildi"


def _check_distance_layers() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    dist = distance_layers(cols, enc.alphabet_sizes)
    assert sum(dist.values()) == enc.space_size()
    assert dist.get(0, 0) == len(set(cols))
    assert max(dist) <= 1
    return f"layers={dict(dist)}"


def _check_blok_motor() -> str:
    enc = Encoder(parse_picks(ORNEK))
    r = solve_by_blocks(enc)
    assert r is not None
    cols, _ = r
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert worst <= 1 and acik == 0
    f16, _ = solve_fix16(enc)
    assert len(cols) <= len(f16)
    return f"blok_bedel={len(cols)} <= fix16={len(f16)}"


def _check_heuristic() -> str:
    picks = "10,10,10,10,10,10,1,1,1,1,1,1,1,1,1"
    enc = Encoder(parse_picks(picks))
    cols = solve_heuristic(enc, trials=2, ls_iters=3000, seed=42)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert worst <= 1 and acik == 0
    return f"heuristic_bedel={len(cols)}"


def _check_olasilik_exact() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_selections(enc)
    rap = olasilik_raporu(enc, cols, probs)
    assert 0 <= rap.p_15 <= 1
    assert 0 <= rap.p_kume_ici <= 1
    assert _approx(rap.p_15 + rap.p_14, rap.p_kume_ici)
    assert rap.p_kume_ici > 0.99
    return f"p_ici={rap.p_kume_ici:.4f} p15={rap.p_15:.4f} p14={rap.p_14:.4f}"


def _check_monte_carlo() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_selections(enc)
    mc = monte_carlo_report(enc, cols, probs, n_samples=5_000, seed=42)
    assert mc["n_samples"] == 5_000
    for key in ("kume_ici", "p15", "p14", "p13", "p12"):
        assert 0.0 <= mc[key]["p"] <= 1.0
        assert mc[key]["ci95"] >= 0.0
    assert mc["kume_ici"]["p"] > 0.9
    rap = olasilik_raporu(enc, cols, probs)
    assert abs(mc["kume_ici"]["p"] - rap.p_kume_ici) < 0.05
    return (
        f"n=5000 kume_ici={mc['kume_ici']['pct']}% "
        f"p15={mc['p15']['pct']}%±{mc['p15']['ci95']}"
    )


def _check_bayes() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    evidence = _probs_on_selections(enc)
    posts = posteriors_only(
        enc.selections, evidence, prior_strength=1.0, evidence_strength=10.0)
    assert len(posts) == 15
    assert all(abs(sum(p.values()) - 1.0) < 1e-9 for p in posts)
    rap = olasilik_raporu(enc, cols, posts)
    assert rap.p_kume_ici > 0.99
    return f"posteriors=15 p_ici={rap.p_kume_ici:.4f}"


def _check_markov() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_selections(enc)
    rep = markov_report(enc, cols, probs)
    assert rep["summary"]["p_kume_ici"] > 0.99
    assert rep["summary"]["p_garanti_path"] > 0.99
    assert rep["error_budget"]["p_final"]["2+"] < 0.01
    return (
        f"p_ici={rep['summary']['p_kume_ici']:.4f} "
        f"p0={rep['summary']['p0']:.4f} p1={rep['summary']['p1']:.4f}"
    )


def _check_error_freq() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    ef = match_error_frequency(enc, cols, max_d=2)
    assert ef["n1"] >= 0 and ef["n2"] >= 0
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert acik == 0 and worst <= 1
    assert ef["n2"] == 0
    return f"n1={ef['n1']} n2={ef['n2']} d1_macs={len(ef['d1'])}"


def _check_fire_scenarios() -> str:
    """
    Secim DISI fire invariantlari.

    Bir mac isaret disindaysa hicbir kolon 15 tutturamaz; iki mac
    disindaysa 14 de imkansizdir. Bunlar kombinatoryal zorunluluktur,
    kupona bagli degildir - kirilirsa mesafe hesabi bozulmus demektir.
    """
    from .fire_scenarios import fire_maliyeti, fire_scenario_report
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    r = fire_scenario_report(enc, cols, max_fires=2)
    assert r["fire1"]["scores"]["15"] == 0, "1 fire varken 15 mumkun gorunuyor"
    assert r["fire2"]["scores"]["15"] == 0
    assert r["fire2"]["scores"]["14"] == 0, "2 fire varken 14 mumkun gorunuyor"
    # Bankoda yanilmak ciftede yanilmaktan pahali olmali
    bt = r["fire1"]["by_type"]
    assert bt["double"]["pct"]["14"] > bt["banko"]["pct"]["14"]
    return (f"fire1>=14=%{r['fire1']['p_ge_14']} "
            f"fire2>=13=%{r['fire2']['p_ge_13']} "
            f"maliyet={fire_maliyeti(enc, cols)}")


def _check_pipeline_result_shape() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, baslik = solve_fix16(enc)
    rows = merge_rows(cols)
    total_cost = sum(row_cost(r) for r in rows)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    dist = distance_layers(cols, enc.alphabet_sizes)
    probs = _probs_on_selections(enc)
    rap = olasilik_raporu(enc, cols, probs)
    mc = monte_carlo_report(enc, cols, probs, n_samples=3_000, seed=1)
    ef = match_error_frequency(enc, cols)

    result = {
        "baslik": baslik,
        "satir_sayisi": len(rows),
        "kolon_bedeli": total_cost,
        "guaranteed": worst <= 1,
        "probs": {"15": dist.get(0, 0), "14": dist.get(1, 0)},
        "advanced": {
            "exact": {"p_kume_ici": rap.p_kume_ici, "p_15": rap.p_15},
            "monte_carlo": mc,
        },
        "error_freq": ef,
        "stat_lines": basliklar(enc),
        "match_count": enc.total_len,
    }
    assert result["guaranteed"] is True
    assert result["satir_sayisi"] == 16
    assert result["match_count"] == 15
    assert result["advanced"]["monte_carlo"]["n_samples"] == 3_000
    assert result["error_freq"]["n2"] == 0
    assert len(result["stat_lines"]) >= 4
    assert rap.p_kume_ici > 0.99
    return f"satir=16 bedel={total_cost} p_ici={rap.p_kume_ici:.4f}"


def _check_scipy_flag() -> str:
    return f"HAS_SCIPY={HAS_SCIPY}"


def run_health() -> HealthReport:
    checks_spec = [
        ("encoder", _check_encoder),
        ("fix16_garanti", _check_fix16_garanti),
        ("fix16_yetersiz_cifte", _check_fix16_yetersiz_cifte),
        ("distance_layers", _check_distance_layers),
        ("blok_motor", _check_blok_motor),
        ("heuristic", _check_heuristic),
        ("olasilik_exact", _check_olasilik_exact),
        ("monte_carlo", _check_monte_carlo),
        ("bayes_dirichlet", _check_bayes),
        ("markov_chain", _check_markov),
        ("error_freq", _check_error_freq),
        ("fire_scenarios", _check_fire_scenarios),
        ("pipeline_result_shape", _check_pipeline_result_shape),
        ("scipy_flag", _check_scipy_flag),
    ]
    results = [_run(name, fn) for name, fn in checks_spec]
    ok = all(c.ok for c in results)
    return HealthReport(
        version=__version__,
        timestamp=datetime.now(timezone.utc).isoformat(),
        ok=ok,
        checks=results,
        summary={
            "ornek_kupon": ORNEK,
            "has_scipy": HAS_SCIPY,
        },
    )


def print_report(report: HealthReport) -> None:
    status = "HEALTHY" if report.ok else "UNHEALTHY"
    print(f"\n=== SYSTEM HEALTH [{status}] v{report.version} ===")
    print(f"time: {report.timestamp}")
    passed = sum(1 for c in report.checks if c.ok)
    print(f"checks: {passed}/{len(report.checks)} passed\n")
    for c in report.checks:
        mark = "OK " if c.ok else "FAIL"
        print(f"  [{mark}] {c.name:24s} {c.duration_ms:7.1f} ms  {c.detail}")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Spor Toto system health checks")
    p.add_argument("--interval", type=float, default=0,
                   help="Saniye cinsinden tekrar aralığı (0 = bir kez)")
    p.add_argument("--json", action="store_true", help="JSON çıktı")
    args = p.parse_args(argv)

    while True:
        report = run_health()
        if args.json:
            import json
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            print_report(report)
        if args.interval <= 0:
            return 0 if report.ok else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
