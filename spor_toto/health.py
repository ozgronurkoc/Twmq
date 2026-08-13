"""Sistem sağlık kontrolü — tüm katmanları tek vücut olarak doğrular.

Kullanım:
  python -m spor_toto.health
  python -m spor_toto.health --interval 60   # her 60 sn tekrar
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import traceback
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

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


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
    probs = [{s: 1.0 / 3 for s in ("1", "0", "2")} for _ in range(15)]
    rap = olasilik_raporu(enc, cols, probs)
    assert 0 <= rap.p_15 <= 1
    assert 0 <= rap.p_kume_ici <= 1
    assert rap.p_15 + rap.p_14 == pytest_approx(rap.p_kume_ici)
    return f"p_ici={rap.p_kume_ici:.4f} p15={rap.p_15:.4f} p14={rap.p_14:.4f}"


def pytest_approx(a: float, b: float = None, rel: float = 1e-9):
    """Mini approx without importing pytest in production health path."""
    if b is None:
        # used as assert x == pytest_approx(y) style via helper
        return _Approx(a, rel)
    return abs(a - b) <= rel * max(1.0, abs(b))


class _Approx:
    def __init__(self, expected: float, rel: float = 1e-9):
        self.expected = expected
        self.rel = rel

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (int, float)):
            return False
        return abs(float(other) - self.expected) <= self.rel * max(1.0, abs(self.expected))


def _check_monte_carlo() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = [{s: 1.0 / 3 for s in ("1", "0", "2")} for _ in range(15)]
    mc = monte_carlo_report(enc, cols, probs, n_samples=5_000, seed=42)
    assert mc["n_samples"] == 5_000
    for key in ("kume_ici", "p15", "p14", "p13", "p12"):
        assert 0.0 <= mc[key]["p"] <= 1.0
        assert mc[key]["ci95"] >= 0.0
    # uniform: küme içi ~1 (tüm semboller seçili değişkenlerde)
    # örnek kupon banko+cifte; p_kume_ici bankolara bağlı
    assert mc["kume_ici"]["p"] > 0.01
    return (
        f"n=5000 kume_ici={mc['kume_ici']['pct']}% "
        f"p15={mc['p15']['pct']}%±{mc['p15']['ci95']}"
    )


def _check_error_freq() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    ef = match_error_frequency(enc, cols, max_d=2)
    assert ef["n1"] + ef["n2"] + len(set(cols)) <= enc.space_size()
    # d=0 points = codewords; remaining at d<=1 for valid cover
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert acik == 0
    return f"n1={ef['n1']} n2={ef['n2']} d1_macs={len(ef['d1'])}"


def _check_pipeline_web_shape() -> str:
    """web_app._build_result ile aynı şekli üret."""
    from web_app import _build_result, _run_fix16

    enc = Encoder(parse_picks(ORNEK))
    r = _run_fix16(enc, variant=0)
    probs = [{s: 1.0 / 3 for s in ("1", "0", "2")} for _ in range(15)]
    result = _build_result(enc, r["cols"], r["baslik"], r["notlar"], user_probs=probs)
    assert result["guaranteed"] is True
    assert result["satir_sayisi"] == 16
    assert result["probs"]["15"]["count"] >= 1
    assert result["advanced"] is not None
    assert "monte_carlo" in result["advanced"]
    assert result["error_freq"] is not None
    return (
        f"satir={result['satir_sayisi']} bedel={result['kolon_bedeli']} "
        f"adv={result['advanced']['exact']['p_kume_ici']}%"
    )


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
        ("error_freq", _check_error_freq),
        ("pipeline_web_shape", _check_pipeline_web_shape),
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
