"""Sistem health — tek vücut entegrasyon doğrulaması."""

from spor_toto.health import run_health, print_report


def test_run_health_all_pass():
    report = run_health()
    failed = [c for c in report.checks if not c.ok]
    assert report.ok, f"Health FAIL: {[(c.name, c.detail) for c in failed]}"
    passed = sum(1 for c in report.checks if c.ok)
    assert passed == len(report.checks)
    assert len(report.checks) >= 10


def test_health_report_dict_shape():
    d = run_health().to_dict()
    assert "version" in d
    assert "timestamp" in d
    assert d["ok"] is True
    assert d["passed"] == d["total"]
    assert isinstance(d["checks"], list)
    for c in d["checks"]:
        assert set(c.keys()) >= {"name", "ok", "detail", "duration_ms"}
        assert c["ok"] is True


def test_health_includes_core_and_analysis():
    names = {c.name for c in run_health().checks}
    for required in (
        "encoder",
        "fix16_garanti",
        "distance_layers",
        "olasilik_exact",
        "monte_carlo",
        "error_freq",
        "pipeline_result_shape",
    ):
        assert required in names


def test_print_report_no_crash(capsys):
    print_report(run_health())
    out = capsys.readouterr().out
    assert "SYSTEM HEALTH" in out
    assert "HEALTHY" in out
