"""/api/health uçları — sözleşme testleri."""

import pytest

pytest.importorskip("flask")

import web_app  # noqa: E402
from web_app import app  # noqa: E402
from spor_toto import __version__  # noqa: E402
from spor_toto.health import CHECKS  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    # Onbellek testler arasinda sizmasin: her test kendi olcumunu yapar.
    web_app._health_onbellek.clear()
    with app.test_client() as c:
        yield c


def test_health_govdesi(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert set(body) >= {
        "version", "timestamp", "ok", "degraded", "passed", "failed",
        "total", "duration_ms", "categories", "checks", "summary",
    }
    assert body["ok"] is True
    assert body["total"] == len(CHECKS)
    assert body["passed"] + body["failed"] == body["total"]


def test_health_kategorileri_kontrolleri_kapsar(client):
    body = client.get("/api/health").get_json()
    kat_ids = {k["id"] for k in body["categories"]}
    assert kat_ids == {c["category"] for c in body["checks"]}
    assert sum(k["total"] for k in body["categories"]) == body["total"]
    for k in body["categories"]:
        assert k["label"] and k["aciklama"]


def test_health_only_kategori(client):
    r = client.get("/api/health?only=cekirdek")
    assert r.status_code == 200
    body = r.get_json()
    assert body["summary"]["kismi"] is True
    assert body["summary"]["only"] == "cekirdek"
    assert {c["category"] for c in body["checks"]} == {"cekirdek"}
    assert body["summary"]["kayitli_kontrol"] == len(CHECKS)


def test_health_only_bilinmeyen_400(client):
    r = client.get("/api/health?only=yok_boyle_bir_kontrol")
    assert r.status_code == 400
    body = r.get_json()
    assert body["ok"] is False
    assert "Bilinmeyen" in body["error"]


def test_health_only_bos_hepsini_calistirir(client):
    body = client.get("/api/health?only=").get_json()
    assert body["total"] == len(CHECKS)
    assert body["summary"]["kismi"] is False


def test_health_envanteri(client):
    r = client.get("/api/health/checks")
    assert r.status_code == 200
    body = r.get_json()
    assert len(body["checks"]) == len(CHECKS)
    for c in body["checks"]:
        assert set(c) >= {"name", "category", "category_label", "aciklama", "critical"}


# ─── liveness / readiness ayrımı ─────────────────────────────────────────────

def test_health_liveness_degismez_kosmaz(client):
    """`/health` LIVENESS'tir: süreç ayakta mı, başka hiçbir şey.

    Eskiden `/api/health` ile aynı handler'a bağlıydı ve bütün değişmezleri
    koşuyordu. Autoscale probe'u her vurduğunda o bedeli ödüyordu; probe
    zaman aşımına düşerse platform sağlıklı bir konteyneri öldürür.
    """
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["readiness"] == "/api/health"
    assert body["uptime_s"] >= 0
    # Kanıt: rapor gövdesinin hiçbir parçası burada YOK.
    assert "checks" not in body
    assert "categories" not in body


def test_readiness_tam_raporu_verir(client):
    body = client.get("/api/health").get_json()
    assert len(body["checks"]) == len(CHECKS)


# ─── önbellek ────────────────────────────────────────────────────────────────

def test_ikinci_cagri_onbellekten_gelir(client):
    ilk = client.get("/api/health").get_json()
    assert ilk["summary"]["onbellek"]["cached"] is False

    ikinci = client.get("/api/health").get_json()
    onbellek = ikinci["summary"]["onbellek"]
    assert onbellek["cached"] is True
    assert onbellek["yas_ms"] >= 0
    # Aynı ölçüm: zaman damgası da aynı kalmalı, yoksa "az önce ölçüldü"
    # diyen bir rapor aslında eski ölçümü gösteriyor demektir.
    assert ikinci["timestamp"] == ilk["timestamp"]
    assert [c["name"] for c in ikinci["checks"]] == [c["name"] for c in ilk["checks"]]


def test_fresh_onbellegi_atlar(client):
    ilk = client.get("/api/health").get_json()
    taze = client.get("/api/health?fresh=1").get_json()
    assert taze["summary"]["onbellek"]["cached"] is False
    assert taze["timestamp"] != ilk["timestamp"]


def test_kismi_kosu_ayri_onbelleklenir(client):
    """`?only=` ile tam rapor aynı kovaya düşerse, kısmi bir koşu tam
    raporun yerine geçer — mümkün olan en yanıltıcı yeşil."""
    kismi = client.get("/api/health?only=cekirdek").get_json()
    tam = client.get("/api/health").get_json()
    assert kismi["summary"]["kismi"] is True
    assert tam["summary"]["kismi"] is False
    assert tam["total"] == len(CHECKS)
    assert client.get("/api/health?only=cekirdek").get_json()["total"] == kismi["total"]
