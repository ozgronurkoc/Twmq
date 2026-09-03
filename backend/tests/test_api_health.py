"""/api/health uçları — sözleşme testleri."""

import pytest

pytest.importorskip("flask")

import web_app
from spor_toto import __version__
from spor_toto import health_history as hh
from spor_toto.health import CHECKS, ORNEK
from web_app import app


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

def test_ikinci_cagri_onbellekten_gelir(client, monkeypatch):
    """İkinci çağrı önbellekten gelmeli — TTL testte SABİTLENİR.

    Test uzun süre `HEALTH_TTL_S`in üretim değerine (5 sn) yaslanıyordu ve
    bu **gizli bir duvar saati kırılganlığıydı**: 27 değişmezin ölçümü tek
    başına 2,1 sn sürüyor ve süit `-n auto` koştuğu için yük altında bu
    rahatça 5 sn'yi aşıyor. Aşınca ikinci çağrı taze ölçüm yapıyor ve test
    "önbellek çalışmıyor" diye düşüyordu — oysa çalışıyordu, TTL dolmuştu.

    `pytest-randomly` bunu ilk koşumda yakaladı (§6I); kusur sıralamada
    değil **varsayımdaydı**. Ölçülen şey önbellek POLİTİKASI olmalı,
    ölçümün hızı değil; TTL bu yüzden sabitleniyor.
    """
    monkeypatch.setattr(web_app, "HEALTH_TTL_S", 3600.0)
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
    """Uç, geçmiş ile özeti TUTARLI biçimde birlikte veriyor mu.

    Sayma mantığının kendisi burada değil, `test_health_history.py::
    test_ozet_ne_zamandan_beri_bu_durumda`'da — orada kayıtlar elle
    beslendiği için deterministiktir. Buradaki iş, uçtan çıkan özetin
    yine uçtan çıkan kayıtlarla uyuşması.

    `bu_durumda_kosu == 2` diye sabitlenmişti ve bu, **iki koşumun aynı
    durumda kalacağını** varsayıyordu. Varsayım yüklü makinede tutmuyor:
    ölçüm süreye bakan denetimler içerdiği için ilk koşum DEGRADED, ikincisi
    HEALTHY olabiliyor ve sayı haklı olarak 1'e düşüyor. Testler paralel
    koşmaya başlayınca (`-n auto`) bu CI'da düzenli olarak patladı.
    Beklenen değer artık kayıtlardan **türetiliyor**; böylece test iki
    senaryoda da ayakta kalıyor ve sayacın yanlış sayması hâlâ yakalanıyor.
    """
    client.get("/api/health?fresh=1")
    client.get("/api/health?fresh=1")
    body = client.get("/api/health/history").get_json()
    kayitlar = body["kayitlar"]          # en yeni başta
    ozet = body["ozet"]
    assert len(kayitlar) == 2
    # Yavas bir makinede durum DEGRADED olur ve bu bir basarisizlik degil
    # (gerekce: tests/test_health.py::test_health_report_dict_shape).
    assert ozet["durum"] in ("HEALTHY", "DEGRADED")
    assert ozet["durum"] == kayitlar[0]["durum"]

    # Son durumla aynı kalan ardışık koşum sayısı — kayıtlardan sayılır.
    beklenen = 0
    for k in kayitlar:
        if k["durum"] != kayitlar[0]["durum"]:
            break
        beklenen += 1
    assert 1 <= beklenen <= 2
    assert ozet["bu_durumda_kosu"] == beklenen

    # `degisim_zamani` o durumun BAŞLADIĞI koşumun zamanı: seride en yeniden
    # geriye giderken durumun bozulmadığı SON kayıt. Eskiden yalnızca "boş
    # değil" diye bakılıyordu; bu satır onu gerçek kayda bağlıyor.
    assert ozet["degisim_zamani"] == kayitlar[beklenen - 1]["timestamp"]
    assert body["ornek"]["pid"]
    # En yeni kayıt başta.
    assert kayitlar[0]["timestamp"] >= kayitlar[1]["timestamp"]


def test_history_durum_degisirse_sayac_sifirdan_baslar(client, monkeypatch):
    """CI'da patlayan senaryonun **deterministik** hâli.

    İki koşum farklı durumda biterse `bu_durumda_kosu` 1 olmalı ve
    `degisim_zamani` en yeni kaydı göstermeli. Yukarıdaki test bunu
    tesadüfen yakalayabilir; bu test her zaman yakalar.
    """
    import spor_toto.health_history as gecmis_modulu

    gercek = gecmis_modulu.kaydet
    durumlar = iter([True, False])       # once saglikli, sonra degil

    def sahte_kaydet(rapor):
        rapor = dict(rapor)
        saglikli = next(durumlar, True)
        rapor["ok"] = saglikli
        rapor["degraded"] = False
        return gercek(rapor)

    monkeypatch.setattr(web_app.saglik_gecmisi, "kaydet", sahte_kaydet)
    client.get("/api/health?fresh=1")
    client.get("/api/health?fresh=1")

    body = client.get("/api/health/history").get_json()
    kayitlar = body["kayitlar"]
    assert [k["durum"] for k in kayitlar] == ["UNHEALTHY", "HEALTHY"]
    assert body["ozet"]["durum"] == "UNHEALTHY"
    assert body["ozet"]["bu_durumda_kosu"] == 1
    assert body["ozet"]["degisim_zamani"] == kayitlar[0]["timestamp"]


def test_onbellekten_donen_cevap_seriye_ikinci_kez_girmez(client):
    """Aynı ölçüm iki kez sayılırsa zaman serisi olmadığı kadar koşu gösterir."""
    client.get("/api/health?fresh=1")
    client.get("/api/health")          # önbellekten
    body = client.get("/api/health/history").get_json()
    assert len(body["kayitlar"]) == 1


def test_onbellek_damgasi_OLCUM_BITINCE_alinir(client, monkeypatch):
    """Yavaş bir ölçümden sonra bile önbellek YAŞAR — deterministik hâli.

    Üstteki test bunu ancak ölçüm TTL'yi aşarsa yakalar, yani makinenin
    yüküne bağlıdır: kapı ilk kez koşulduğunda tam olarak öyle düştü
    (ölçüm 7,7 sn sürdü, `HEALTH_TTL_S` 5 sn). Bu test ölçümü BİLEREK
    TTL'den uzun tutar, dolayısıyla hatayı her makinede, her sırada
    yakalar.

    Bekçilik ettiği hata: önbellek damgası isteğin BAŞINDA alınırsa kaydın
    ömrü `TTL - ölçüm_süresi` olur ve yavaş bir ölçümde kayıt **doğduğu
    anda ölü** doğar. Sonucu iki katmanlıdır: (1) önbellek tam da
    koruması gereken durumda — yük altında — devre dışı kalır, (2) her
    yeniden ölçüm `saglik_gecmisi.kaydet` çağırdığı için tek bir ölçüm
    penceresi zaman serisine birden fazla kayıt bırakır.
    """
    gercek = web_app.run_health

    def yavas_olcum(only=None):
        # TTL'den UZUN suren bir olcum: damga baslangictan alinirsa kayit
        # daha yazilmadan bayatlar.
        zaman.ilerlet(web_app.HEALTH_TTL_S + 1.0)
        return gercek(only)

    class _SahteSaat:
        """`time.monotonic`i testin denetimine alır — gerçek uyku yok."""

        def __init__(self):
            self.t = 1000.0

        def ilerlet(self, sn):
            self.t += sn

        def __call__(self):
            return self.t

    zaman = _SahteSaat()
    monkeypatch.setattr(web_app.time, "monotonic", zaman)
    monkeypatch.setattr(web_app, "run_health", yavas_olcum)

    client.get("/api/health?fresh=1")
    govde = client.get("/api/health").get_json()

    assert govde["summary"]["onbellek"]["cached"] is True, (
        "yavas olcumden sonra onbellek dusmus: damga olcum BASINDA aliniyor")
    # Yas, olcumun BITISINDEN itibaren sayilir; olcum suresi ona eklenmez.
    assert govde["summary"]["onbellek"]["yas_ms"] == 0.0
    assert len(client.get("/api/health/history").get_json()["kayitlar"]) == 1


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
