"""/api/health uçları — sözleşme testleri."""

import pytest

pytest.importorskip("flask")

import web_app  # noqa: E402
from web_app import app  # noqa: E402
from spor_toto import __version__  # noqa: E402
from spor_toto import health_history as hh  # noqa: E402
from spor_toto.health import CHECKS, ORNEK  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    # Onbellek ve zaman serisi testler arasinda sizmasin: her test kendi
    # olcumunu yapar.
    web_app._health_onbellek.clear()
    hh.temizle()
    with app.test_client() as c:
        yield c
    hh.temizle()


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


# ─── zaman serisi (§7.2) ─────────────────────────────────────────────────────

def test_history_ucu_kosulari_biriktirir(client):
    client.get("/api/health?fresh=1")
    client.get("/api/health?fresh=1")
    body = client.get("/api/health/history").get_json()
    assert len(body["kayitlar"]) == 2
    assert body["ozet"]["durum"] == "HEALTHY"
    assert body["ozet"]["bu_durumda_kosu"] == 2
    assert body["ozet"]["degisim_zamani"]
    assert body["ornek"]["pid"]
    # En yeni kayıt başta.
    assert body["kayitlar"][0]["timestamp"] >= body["kayitlar"][1]["timestamp"]


def test_onbellekten_donen_cevap_seriye_ikinci_kez_girmez(client):
    """Aynı ölçüm iki kez sayılırsa zaman serisi olmadığı kadar koşu gösterir."""
    client.get("/api/health?fresh=1")
    client.get("/api/health")          # önbellekten
    body = client.get("/api/health/history").get_json()
    assert len(body["kayitlar"]) == 1


def test_kismi_kosu_seriye_girmez(client):
    client.get("/api/health?only=cekirdek&fresh=1")
    body = client.get("/api/health/history").get_json()
    assert body["kayitlar"] == []
    assert body["ozet"]["kayit"] == 0


def test_history_limit_kirpar(client):
    for _ in range(3):
        client.get("/api/health?fresh=1")
    assert len(client.get("/api/health/history?limit=2").get_json()["kayitlar"]) == 2


# ─── kullanıcı kuponu (§7.4) ─────────────────────────────────────────────────

def test_kupon_ucu_kullanici_kuponunu_dogrular(client):
    r = client.post("/api/health/kupon", json={"picks": ORNEK})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["satir"] == 16 and body["bedel"] == 32
    assert body["uyari"], "kayıtlı rapordan ayrı olduğu yazmalı"
    assert len(body["checks"]) >= 5


def test_kupon_ucu_matches_kabul_eder(client):
    matches = [["1"], ["1", "0"], ["1"], ["1", "2"], ["0"], ["1", "0"], ["2"],
               ["1", "0"], ["1"], ["1", "2"], ["0", "2"], ["1"], ["1", "0"],
               ["2"], ["1", "0"]]
    body = client.post("/api/health/kupon", json={"matches": matches}).get_json()
    assert body["ok"] is True


def test_kupon_ucu_bos_govdede_400(client):
    r = client.post("/api/health/kupon", json={})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False


def test_kupon_ucu_bilinmeyen_mod_400(client):
    r = client.post("/api/health/kupon", json={"picks": ORNEK, "mode": "yok"})
    assert r.status_code == 400
    assert "Bilinmeyen mod" in r.get_json()["error"]


def test_kupon_dusen_degismez_503_uretmez(client):
    """Bir KUPONUN değişmezi düşmesi servisin sağlık durumu değildir; 503
    dönmek izlemeyi yanlış yere baktırırdı."""
    r = client.post("/api/health/kupon", json={"picks": ORNEK, "mode": "maxcov",
                                               "budget": 8})
    assert r.status_code == 200
    body = r.get_json()
    assert body["guaranteed"] is False
    assert body["ok"] is True   # maxcov zaten garanti vermediğini ilan eder


def test_kupon_kosusu_zaman_serisine_girmez(client):
    """Kupon denetimi kayıtlı rapor değildir; seriye girerse "21/21" ile
    "5/5" aynı grafikte yan yana durur."""
    client.post("/api/health/kupon", json={"picks": ORNEK})
    assert client.get("/api/health/history").get_json()["kayitlar"] == []
