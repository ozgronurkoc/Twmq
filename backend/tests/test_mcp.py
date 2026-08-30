"""MCP yüzeyi — sözleşme bölünmedi mi?

Bu süit **modülün kalmasını savunmuyor.** `mcp_server.py` kendi ölçütüne
göre yerini hak etmiyor (ölçüt 1: yeni yetenek yok) ve bunu kendi
başlığında yazıyor. Buradaki testlerin işi başka: modül depoda durduğu
sürece **sözleşmeyi ikiye bölmediğini** garanti etmek.

Asıl bekçi `test_arac_olmayan_uca_baglanmaz`: bir MCP aracı kayıtlı
olmayan bir ucu sarıyorsa, ajana var olmayan bir yetenek vaat edilmiş
demektir ve bu sessizce olur.
"""

import pytest

pytest.importorskip("flask")

import web_app
from spor_toto import mcp_server

# ─── uç envanteri (deneyin kalıcı yan ürünü) ─────────────────────────────────

def test_uc_envanteri_KAYIT_TABLOSUNDAN_turer():
    """Liste elle yazılmamalı — eskiyen bir envanter sessizce yanlıştır.

    Ölçüldü (§6H): `/api/pazar` ve `/api/takimlar` aylarca kayıtlı ve
    çalışırken servis kökünün listesinde YOKTU. Kusuru MCP deneyinin
    envanter denetimi buldu.
    """
    satirlar = web_app.uc_envanteri()
    yollar = {s.split()[1] for s in satirlar}
    kayitli = {str(k.rule) for k in web_app.app.url_map.iter_rules()
               if str(k.rule).startswith("/api") or str(k.rule) == "/health"}
    assert yollar == kayitli, yollar ^ kayitli


def test_uc_envanteri_yeni_uc_eklendiginde_KENDILIGINDEN_buyur():
    """Ayrı bir uygulamada sınanır — küresel `app`e uç eklemek sızıntıdır."""
    from flask import Flask

    yalitik = Flask("envanter_testi")

    @yalitik.route("/api/ornek", methods=["GET"])
    def _ornek():  # pragma: no cover - yalnizca kayit icin
        """Örnek uç."""
        return ""

    @yalitik.route("/api/pazar", methods=["GET"])
    def _pazar():  # pragma: no cover - yalnizca kayit icin
        """Açıklaması olan uç."""
        return ""

    satirlar = web_app.uc_envanteri(yalitik)
    assert [s.split()[1] for s in satirlar] == ["/api/ornek", "/api/pazar"]
    # Aciklamasi olan uc onu TASIR, olmayan sade kalir.
    assert satirlar[0] == "GET  /api/ornek"
    assert "(alt/ust 2,5 ve Asya handikabi)" in satirlar[1]
    # Kuresel uygulama etkilenmedi.
    assert "/api/ornek" not in " ".join(web_app.uc_envanteri())


def test_servis_koku_pazar_ve_takimlari_TASIR():
    """Kusurun kendisi için bir bekçi — geri gelmesin."""
    body = web_app.app.test_client().get("/").get_json()
    metin = " ".join(body["endpoints"])
    assert "/api/pazar" in metin
    assert "/api/takimlar" in metin


# ─── sözleşme bölünmesi ──────────────────────────────────────────────────────

def test_arac_olmayan_uca_baglanmaz():
    """Her MCP aracı GERÇEKTEN kayıtlı bir ucu sarmalı."""
    e = mcp_server.envanter()
    assert e["olmayan_uca_baglanan"] == [], e["olmayan_uca_baglanan"]
    assert e["saglam"] is True


def test_envanter_meta_okuyabiliyor():
    assert mcp_server.envanter()["meta_okundu"] is True


def test_araclar_tekil_uclara_baglanir():
    """İki araç aynı ucu sarmamalı — ajan hangisini seçeceğini bilemez."""
    yollar = list(mcp_server.ARACLAR.values())
    assert len(yollar) == len(set(yollar)), yollar


def test_sarilmamis_uclar_RAPORLANIR():
    """Kapsam bilgisi sessiz kalmamalı; kusur değil ama görünür olmalı."""
    e = mcp_server.envanter()
    assert "/api/takimlar" in e["sarilmamis_uclar"]


# ─── taşıma katmanı gerçekten aynı gövdeyi veriyor mu ────────────────────────

def test_mcp_govdesi_HTTP_govdesiyle_AYNI():
    """MCP yeni bir çevirici değil; gövde birebir aynı olmalı.

    Bu, modülün varlık sebebi olan tek-çevirici kuralının bekçisi.
    """
    dogrudan = web_app.app.test_client().get("/api/meta").get_json()
    mcp_yolu = mcp_server._al("/api/meta")
    assert mcp_yolu["durum"] == 200
    assert mcp_yolu["govde"] == dogrudan


def test_bos_parametreler_DUSURULUR():
    """`None` sorgu parametresi gönderilmemeli — ucun varsayılanı kazanmalı."""
    a = mcp_server._al("/api/stats", last=None, sezon=None)
    b = mcp_server._al("/api/stats")
    assert a["durum"] == b["durum"] == 200
    assert a["govde"] == b["govde"]


# ─── sunucu kurulumu (mcp kuruluysa) ─────────────────────────────────────────

def test_sunucu_kuruluyor_ve_araclari_tasiyor():
    pytest.importorskip("mcp")
    s = mcp_server.sunucu()
    assert s.name == "spor-toto"


def test_mcp_yoksa_suite_KIRILMAZ():
    """`agac.HAS_LIGHTGBM` deseni: eksik isteğe bağlı bağımlılık atlatır, kırmaz."""
    import importlib
    assert importlib.import_module("spor_toto.mcp_server") is mcp_server
