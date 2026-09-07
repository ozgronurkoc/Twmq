"""/api/backtest — uç sözleşmesi.

Geri test sayfada tek başına bir sayı olarak görünmemeli: kesit özeti,
tarama ve (eşik ailesinde) hold-out birlikte anlam taşır. Bu testler
üçünün de uçtan çıktığını ve birbiriyle tutarlı kaldığını denetler.

**Varsayılan strateji `hedef`tir** — ürünün kendi kuralı. Eşik ailesini
sınayan testler onu `?strateji=esik` ile AÇIKÇA ister; uzun süre uç yalnız
eşik kuralını koşuyordu ve arayüz ürünün kullanmadığı bir kuralın
sayılarını gösteriyordu.
"""

import itertools

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
        "meta", "strategy", "season", "weeks", "sweep", "butce_sweep",
        "holdout", "warning"
    }
    s = body["season"]
    assert s["weeks"] > 0
    assert s["hit15"] <= s["hit14"] <= s["hit13"] <= s["hit12"] <= s["weeks"]
    assert s["columns_total"] > 0
    # Olcek kunyesi govdede DURMALI: kaplama sokulduktan sonra ayni alan
    # adlari bambaska bir aritmetigi anlatiyor (alt sinir -> esitlik).
    assert body["meta"]["olcek"] == "duz"
    assert body["meta"]["kademe"] == 12
    # Uyari metni kaldirilmamali.
    assert body["warning"]


def test_varsayilan_strateji_urunun_kurali(client):
    """Uç, ürünün kullanmadığı bir kuralı varsayılan yapmamalı."""
    body = client.get("/api/backtest?sweep=0").get_json()
    st = body["strategy"]
    assert st["ad"] == "hedef"
    assert st["kademe"] == 12 and st["kacak_esigi"] == 3
    assert st["butce_kolon"] >= 1
    # Bedel tavani bir HARCAMA KARARIDIR; govde onu TL olarak da tasimali.
    assert body["season"]["tl_avg"] <= st["butce_tl"]


def test_bilinmeyen_strateji_400(client):
    """Tanınmayan ad sessizce varsayılana düşmez."""
    r = client.get("/api/backtest?strateji=yok&sweep=0")
    assert r.status_code == 400
    assert "esik" in r.get_json()["stratejiler"]


def test_esikler_secime_uyar(client):
    """Yüksek banko eşiği daha az banko üretir — strateji gerçekten uygulanıyor."""
    dusuk = client.get(
        "/api/backtest?strateji=esik&banko=0.55&uclu=0&sweep=0").get_json()
    yuksek = client.get(
        "/api/backtest?strateji=esik&banko=0.80&uclu=0&sweep=0").get_json()
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
    body = client.get(
        f"/api/backtest?strateji=esik&banko={raw}&sweep=0").get_json()
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
    """Eşik ailesinde üçü birlikte gelir — ayarlanan bir parametre var."""
    body = client.get("/api/backtest?strateji=esik").get_json()
    assert body["sweep"], "eşik taraması boş"
    assert body["sweep_best"] in body["sweep"]
    ho = body["holdout"]
    assert ho["weeks"] > 0
    # Hold-out taramanin en iyisini gecemez; fark asiri uyumun buyuklugudur.
    assert ho["hit12"] <= body["sweep_best"]["hit12"]
    assert ho["chosen"]


def test_hedefte_holdout_YOK_butce_taramasi_VAR(client):
    """`hedef`te ayarlanan parametre yok; hold-out da o yüzden yok.

    Yerine bütçe taraması gelir — ve o bir parametre araması değil, bir
    **harcama kararının** karşılığıdır: pahalı basamak her zaman daha çok
    tutturur, sorulacak soru bedele değip değmediğidir.
    """
    body = client.get("/api/backtest").get_json()
    assert body["holdout"]["weeks"] == 0, "hedef kuralında hold-out anlamsız"
    assert not body["sweep"], "hedef kuralında eşik taraması anlamsız"
    tarama = body["butce_sweep"]
    assert len(tarama) >= 2
    # Butce arttikca isabet DUSEMEZ: daha genis kume, ayni sonuc uzayi.
    for onceki, sonraki in itertools.pairwise(tarama):
        assert sonraki["butce_tl"] > onceki["butce_tl"]
        assert sonraki["hit12"] >= onceki["hit12"]


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
