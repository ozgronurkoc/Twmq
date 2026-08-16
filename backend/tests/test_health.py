"""Sistem health — tek vücut entegrasyon doğrulaması."""

import pytest

from spor_toto.health import (
    CHECKS,
    KATEGORILER,
    check_envanteri,
    print_report,
    run_health,
    secili_checkler,
)


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
    assert d["degraded"] is False
    assert d["passed"] == d["total"]
    assert d["duration_ms"] > 0
    assert isinstance(d["checks"], list)
    for c in d["checks"]:
        assert set(c.keys()) >= {
            "name", "ok", "detail", "duration_ms",
            "category", "category_label", "aciklama", "critical",
        }
        assert c["ok"] is True
        assert c["aciklama"], f"{c['name']} icin aciklama yok"


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
        "veri_seti",
        "oran_arsivi",
    ):
        assert required in names


def test_print_report_no_crash(capsys):
    print_report(run_health())
    out = capsys.readouterr().out
    assert "SYSTEM HEALTH" in out
    assert "HEALTHY" in out
    # Kategori başlıkları çıktıda görünmeli.
    assert "Çekirdek" in out


# ─── kategori / envanter ──────────────────────────────────────────────────────

def test_her_check_bilinen_kategoride():
    gecerli = {k for k, _, _ in KATEGORILER}
    for c in CHECKS:
        assert c.category in gecerli, f"{c.name}: bilinmeyen kategori {c.category}"


def test_check_adlari_tekil():
    adlar = [c.name for c in CHECKS]
    assert len(adlar) == len(set(adlar))


def test_kategori_ozeti_toplami_tutar():
    report = run_health()
    kats = report.kategoriler()
    assert sum(k["total"] for k in kats) == len(report.checks)
    assert sum(k["passed"] for k in kats) == sum(1 for c in report.checks if c.ok)


def test_envanter_calistirmadan_listeler():
    env = check_envanteri()
    assert len(env) == len(CHECKS)
    assert {e["name"] for e in env} == {c.name for c in CHECKS}
    assert all(e["aciklama"] for e in env)


# ─── kısmi çalıştırma (--only / ?only=) ───────────────────────────────────────

def test_only_tek_kontrol():
    report = run_health("encoder")
    assert [c.name for c in report.checks] == ["encoder"]
    assert report.summary["kismi"] is True
    assert report.summary["only"] == "encoder"
    assert report.ok


def test_only_kategori():
    report = run_health("olasilik")
    assert {c.category for c in report.checks} == {"olasilik"}
    assert len(report.checks) >= 4


def test_only_coklu_ve_sira_korunur():
    report = run_health("markov_chain,encoder")
    # Tanım sırası korunur; istek sırası değil.
    assert [c.name for c in report.checks] == ["encoder", "markov_chain"]


def test_only_tekrarli_ad_iki_kez_calismaz():
    report = run_health("encoder,encoder,cekirdek")
    adlar = [c.name for c in report.checks]
    assert len(adlar) == len(set(adlar))


def test_only_bilinmeyen_ad_hata_verir():
    with pytest.raises(ValueError, match="Bilinmeyen kontrol/kategori"):
        secili_checkler("boyle_bir_sey_yok")


def test_only_bos_hepsini_calistirir():
    assert len(secili_checkler(None)) == len(CHECKS)
    assert len(secili_checkler("  ")) == len(CHECKS)
    assert run_health().summary["kismi"] is False


# ─── ortam bilgisi ────────────────────────────────────────────────────────────

def test_env_bilgisi_raporda():
    env = run_health("encoder").summary["env"]
    assert env["python"]
    assert env["platform"]
    assert "numpy" in env and "scipy" in env


def test_slowest_en_uzun_kontrolu_gosterir():
    d = run_health().to_dict()
    slowest = d["summary"]["slowest"]
    assert slowest["duration_ms"] == max(c["duration_ms"] for c in d["checks"])
