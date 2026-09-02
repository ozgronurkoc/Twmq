"""/api/backtest — uç sözleşmesi.

Geri test sayfada tek başına bir sayı olarak görünmemeli: sezon özeti, eşik
taraması ve hold-out birlikte anlam taşır. Bu testler üçünün de uçtan
çıktığını ve birbiriyle tutarlı kaldığını denetler.
"""

import pytest

pytest.importorskip("flask")

from spor_toto.odds import load_odds

pytestmark = pytest.mark.skipif(
    not load_odds(), reason="oran arşivi yok (scripts/build_odds.py)"
)


# `client` fixture'i `tests/conftest.py`den geliyor — ayni govde bes
# dosyada, ucu BIREBIR yaziliydi. (Ezmesi gereken ikisi eziyor:
# `test_api_health` onbellek temizliyor, `test_tahmin` modul kapsamli.)


def test_govde_ve_ozet(client):
    r = client.get("/api/backtest?sweep=0")
    assert r.status_code == 200
    body = r.get_json()
    assert set(body) >= {
        "meta", "strategy", "season", "weeks", "sweep", "holdout", "warning"
    }
    s = body["season"]
    assert s["weeks"] > 0
    assert s["hit15"] <= s["hit14"] <= s["hit13"] <= s["weeks"]
    assert s["columns_total"] > 0
    # Uyari metni kaldirilmamali: 41 hafta kucuk ornekem.
    assert "garanti" in body["warning"].lower()


def test_esikler_secime_uyar(client):
    """Yüksek banko eşiği daha az banko üretir — strateji gerçekten uygulanıyor."""
    dusuk = client.get("/api/backtest?banko=0.55&uclu=0&sweep=0").get_json()
    yuksek = client.get("/api/backtest?banko=0.80&uclu=0&sweep=0").get_json()
    assert dusuk["strategy"]["banko"] == 0.55
    assert yuksek["strategy"]["banko"] == 0.80
    assert dusuk["season"]["banko_avg"] > yuksek["season"]["banko_avg"]
    # Daha az banko = daha genis kupon = daha pahali. Olculen: 5,3 banko /
    # 243 kolon (esik 0,55) -> 0,2 banko / 3.755 kolon (esik 0,80).
    assert dusuk["season"]["columns_avg"] < yuksek["season"]["columns_avg"]


@pytest.mark.parametrize("raw,beklenen", [
    ("0.6", 0.6), ("2", 1.0), ("-1", 0.0), ("abc", 0.68), ("", 0.68),
])
def test_esik_ayristirma(client, raw, beklenen):
    body = client.get(f"/api/backtest?banko={raw}&sweep=0").get_json()
    assert body["strategy"]["banko"] == beklenen


def test_dilim_uygulanir(client):
    body = client.get("/api/backtest?last=6&sweep=0").get_json()
    assert body["meta"]["weeks_available"] == 6


def test_hafta_satirlari_kendini_anlatir(client):
    body = client.get("/api/backtest?sweep=0").get_json()
    for h in body["weeks"]:
        if h["skipped"]:
            assert h["reason"]
            continue
        assert len(h["picks"]) == 15
        assert h["banko"] + h["double"] + h["triple"] == 15
        assert h["misses"] == len(h["miss_at"])
        assert h["in_set"] == (h["misses"] == 0)
        assert 0 <= h["best"] <= 15
        assert h["guaranteed"] is True
        # Kolon bedeli satir sayisiyla karistirilmamali.
        assert h["columns"] >= h["rows"]


def test_tarama_ve_holdout_birlikte_gelir(client):
    body = client.get("/api/backtest").get_json()
    assert body["sweep"], "eşik taraması boş"
    assert body["sweep_best"] in body["sweep"]
    ho = body["holdout"]
    assert ho["weeks"] > 0
    # Hold-out taramanin en iyisini gecemez; fark asiri uyumun buyuklugudur.
    assert ho["hit14"] <= body["sweep_best"]["hit14"]
    assert ho["chosen"]


def test_diger_pazarlar_geri_teste_de_sizmaz(client):
    """Arayüze yalnızca maç sonucu (1X2) çıkar — geri test de istisna değil."""
    ham = client.get("/api/backtest?sweep=0").get_data(as_text=True).lower()
    for anahtar in ("asya", "handikap", '"ah"', "2.5", "over", "under"):
        assert anahtar not in ham


# ─── ?sezon= ──────────────────────────────────────────────────────────────────
#
# Geri test uzun süre yalnızca varsayılan sezonu görüyordu. Sezon seçimi
# `/api/stats`e eklendiğinde bu uç geride kaldı ve sonuç SESSİZ bir
# tutarsızlıktı: kullanıcı 2023/24 seçip *Geri test* sekmesine geçince
# 2025/26'nın tablosunu görüyordu ve bunu anlamasının bir yolu yoktu.

def test_backtest_varsayilan_sezon_None(client):
    b = client.get("/api/backtest?sweep=0").get_json()
    assert b["meta"]["sezon"] is None
    assert b["meta"]["weeks_available"] == 41


def test_backtest_sezon_secilince_o_sezonu_kosar(client):
    b = client.get("/api/backtest?sweep=0&sezon=2023_24").get_json()
    assert b["meta"]["sezon"] == "2023_24"
    assert b["meta"]["weeks_available"] == 31
    # Yeni sezonlarda oran kapsaması %100 — elenen hafta olmamalı.
    assert b["meta"]["weeks_used"] == 31


def test_backtest_bilinmeyen_sezon_400(client):
    r = client.get("/api/backtest?sweep=0&sezon=yok_boyle")
    assert r.status_code == 400
    assert r.get_json()["sezonlar"]


def test_backtest_sezon_onbellegi_karistirmaz(client):
    """`_backtest_cached` sezona anahtarlı olmalı."""
    a = client.get("/api/backtest?sweep=0").get_json()
    client.get("/api/backtest?sweep=0&sezon=2023_24")
    b = client.get("/api/backtest?sweep=0").get_json()
    assert a["meta"]["weeks_available"] == b["meta"]["weeks_available"] == 41
