"""/api/health uçları — sözleşme testleri."""

import pytest

pytest.importorskip("flask")

from web_app import app  # noqa: E402
from spor_toto.health import CHECKS  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
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


def test_kisa_yol_health_ayni_govdeyi_verir(client):
    a = client.get("/health").get_json()
    b = client.get("/api/health").get_json()
    assert a["total"] == b["total"]
    assert [c["name"] for c in a["checks"]] == [c["name"] for c in b["checks"]]
