"""/api/stats uçları — sözleşme testleri."""

import pytest

pytest.importorskip("flask")

from spor_toto.history import MATCH_COUNT, SYMBOLS, history_weeks

# `client` fixture'i `tests/conftest.py`den geliyor — ayni govde bes
# dosyada, ucu BIREBIR yaziliydi. (Ezmesi gereken ikisi eziyor:
# `test_api_health` onbellek temizliyor, `test_tahmin` modul kapsamli.)


def test_stats_govdesi(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.get_json()
    assert set(body) >= {
        "meta", "totals", "weekly_avg", "bands", "data_quality", "analytics", "weeks", "last"
    }
    assert body["last"] is None
    assert body["error"] is None
    assert len(body["weeks"]) == body["meta"]["weeks"] == len(history_weeks())
    assert len(body["analytics"]["positions"]) == MATCH_COUNT
    for sym in SYMBOLS:
        assert body["totals"][sym] == sum(w["counts"][sym] for w in body["weeks"])


@pytest.mark.parametrize("raw,beklenen", [("5", 5), ("all", None), ("", None), ("abc", None), ("0", None), ("-3", None)])
def test_last_parametresi(client, raw, beklenen):
    body = client.get(f"/api/stats?last={raw}").get_json()
    assert body["last"] == beklenen
    assert len(body["weeks"]) == (beklenen or len(history_weeks()))


def test_hafta_detayi(client):
    hafta = history_weeks()[1]["week"]
    r = client.get(f"/api/stats/{hafta}")
    assert r.status_code == 200
    body = r.get_json()
    assert body["week"] == hafta
    assert len(body["cells"]) == MATCH_COUNT
    assert body["prev_week"] == history_weeks()[0]["week"]
    assert set(body) >= {"runs", "season_avg", "delta_vs_avg", "rank", "position_stats", "matches"}
    assert len(body["matches"]) == MATCH_COUNT
    for hucre, mac in zip(body["cells"], body["matches"]):
        assert hucre["symbol"] == mac["code"]
        assert mac["home"] and mac["away"]


def test_stats_mac_sonucu_orani_tasiyor(client):
    """Arayuze YALNIZCA 1X2 gider; alt/ust ve Asya handikap arsivde kalir."""
    body = client.get("/api/stats").get_json()
    o = body["odds"]
    if o is None:  # oran arsivi yoksa uc sessizce None doner
        return
    assert 0 < o["with_odds"] <= o["matches"]
    assert 0 <= o["favourite_hit_pct"] <= 100
    assert o["favourite_split"]["0"] == 0, "beraberlik favori olamaz"
    assert o["favourite_hit"] + o["favourite_miss"] == o["with_odds"]
    # Favori tuttugunda beraberlik cikamaz: beraberlik hicbir zaman favori degil.
    assert o["outcome_when_hit"]["0"] == 0
    for sym in SYMBOLS:
        assert (o["outcome_when_hit"][sym] + o["outcome_when_miss"][sym]
                == o["outcome_totals"][sym])
        assert o["cross"][sym][sym] == o["outcome_when_hit"][sym]
    assert sum(o["outcome_totals"].values()) == o["with_odds"]
    assert sum(o["outcome_when_hit"].values()) == o["favourite_hit"]
    assert sum(o["outcome_when_miss"].values()) == o["favourite_miss"]
    # Surpriz = favorinin karsi tarafi kazandi; beraberlikler bunun disinda.
    assert o["underdog_wins"] == o["favourite_miss"] - o["outcome_when_miss"]["0"]
    # Banko bantlari: tuttu+tutmadi = n, beraberlik+karsi = tutmadi
    assert o["favourite_bands"], "favori bantlari bos"
    assert sum(b["n"] for b in o["favourite_bands"]) == o["with_odds"]
    for b in o["favourite_bands"]:
        assert b["hit"] + b["miss"] == b["n"]
        assert b["draw"] + b["upset"] == b["miss"]
        assert b["lo"] > 1.0 or b["lo"] == 1.0
        assert b["hi"] is None or b["hi"] > b["lo"]
    assert sum(b["draw"] for b in o["favourite_bands"]) == o["outcome_when_miss"]["0"]
    assert sum(b["upset"] for b in o["favourite_bands"]) == o["underdog_wins"]
    assert sum(b["hit"] for b in o["favourite_bands"]) == o["favourite_hit"]
    assert o["avg_margin_pct"] > 0
    for kova in o["calibration"]:
        assert kova["lo"] < kova["hi"] and kova["n"] >= 10


def test_karar_destek_bloklari(client):
    """Çift kapsama, beraberlik profili ve lig kırılımı — F3 blokları."""
    o = client.get("/api/stats").get_json()["odds"]
    if o is None:
        return
    assert o["low_sample_at"] > 0

    # Cift kapsama: banko her zaman ciftenin altinda kalir (alt kume).
    kapsama = o["set_coverage"]
    assert kapsama
    assert sum(b["n"] for b in kapsama) == o["with_odds"]
    for b in kapsama:
        assert b["in_one"] <= b["in_two"] <= b["n"]
        assert b["in_two_pct"] >= b["in_one_pct"]
        assert 0 <= b["model_pct"] <= 100
        assert b["low_sample"] == (b["n"] < o["low_sample_at"])
    # Ilk iki olasilik toplami buyudukce kapsama artar (bant sirasi monoton).
    buyuk = [b for b in kapsama if not b["low_sample"]]
    assert buyuk == sorted(buyuk, key=lambda b: b["in_two_pct"])

    # Beraberlik profili: banttaki maclarin toplami tum maclari verir.
    profil = o["draw_profile"]
    assert profil
    assert sum(b["n"] for b in profil) == o["with_odds"]
    assert sum(b["draw"] for b in profil) == o["outcome_totals"]["0"]
    for b in profil:
        assert b["draw"] <= b["n"]
        assert 0 <= b["model_draw_pct"] <= 100

    # Lig kirilimi: paylar toplami maclarin tamami.
    ligler = o["leagues"]
    assert ligler
    assert sum(lig["n"] for lig in ligler) == o["with_odds"]
    assert sum(lig["draw"] for lig in ligler) == o["outcome_totals"]["0"]
    assert sum(lig["favourite_hit"] for lig in ligler) == o["favourite_hit"]
    assert ligler == sorted(ligler, key=lambda lig: (-lig["n"], lig["league"]))
    for lig in ligler:
        assert lig["label"], "lig etiketi bos olamaz"
        assert 0 <= lig["draw_pct"] <= 100


def test_haftalik_brier(client):
    """Piyasa hangi hafta yanıldı — favori isabetinden daha dürüst ölçü."""
    o = client.get("/api/stats").get_json()["odds"]
    if o is None:
        return
    haftalar = o["weekly_brier"]
    assert haftalar
    assert haftalar == sorted(haftalar, key=lambda w: w["week"])
    assert sum(w["n"] for w in haftalar) == o["with_odds"]
    for w in haftalar:
        # Brier [0, 2] araligindadir; 0 kusursuz, 2 tam ters.
        assert 0.0 <= w["brier"] <= 2.0
        assert w["favourite_hit"] <= w["n"]
        assert w["partial"] == (w["n"] < 15)
    # Esit olasilik referansi: piyasa bunun altinda kalmali, yoksa bilgi
    # tasimiyor demektir.
    assert o["brier_uniform"] == pytest.approx(2 / 3, abs=1e-3)
    assert 0.0 < o["brier_avg"] < o["brier_uniform"]
    # Sezon ortalamasi hafta ortalamalarinin mac agirlikli ortalamasidir.
    agirlikli = sum(w["brier"] * w["n"] for w in haftalar) / o["with_odds"]
    assert o["brier_avg"] == pytest.approx(agirlikli, abs=1e-3)


def test_karar_destek_dilime_uyar(client):
    """?last=N üç bloğu da kapsar — iki görsel farklı veriyi anlatmaz."""
    tam = client.get("/api/stats").get_json()["odds"]
    dilim = client.get("/api/stats?last=6").get_json()["odds"]
    if tam is None or dilim is None:
        return
    for anahtar in ("set_coverage", "draw_profile", "leagues", "weekly_brier"):
        assert sum(b["n"] for b in dilim[anahtar]) == dilim["with_odds"]
        assert sum(b["n"] for b in dilim[anahtar]) < sum(b["n"] for b in tam[anahtar])


def test_stats_odds_dilime_uyar(client):
    tam = client.get("/api/stats").get_json()["odds"]
    dilim = client.get("/api/stats?last=6").get_json()["odds"]
    if tam is None or dilim is None:
        return
    assert dilim["matches"] < tam["matches"]


def test_hafta_detayinda_1x2_var_diger_pazarlar_yok(client):
    hafta = history_weeks()[-1]["week"]
    body = client.get(f"/api/stats/{hafta}").get_json()
    assert "odds" in body and "odds_hit" in body
    for _no, blok in body["odds"].items():
        assert set(blok["odds"]) == set(SYMBOLS)
        assert set(blok["probs"]) == set(SYMBOLS)
        assert abs(sum(blok["probs"].values()) - 1.0) < 1e-3
        assert blok["favourite"] in SYMBOLS
        assert blok["margin"] > 0
        # Alt/ust ve handikap arayuze sizmamali.
        assert not any(k in blok for k in ("over", "under", "ah", "2.5"))
    assert body["odds_hit"] <= len(body["odds"])


def test_olmayan_hafta_404(client):
    r = client.get("/api/stats/99999")
    assert r.status_code == 404
    assert "error" in r.get_json()


# ─── ?sezon= ──────────────────────────────────────────────────────────────────

def test_stats_varsayilan_sezon_secimi_None(client):
    b = client.get("/api/stats").get_json()
    assert b["sezon"] is None
    assert b["meta"]["weeks"] == 41


def test_stats_sezon_secilince_o_sezon_gelir(client):
    from spor_toto.history import history_summary, sezonlar

    s = sezonlar()[0]
    b = client.get(f"/api/stats?sezon={s}").get_json()
    assert b["sezon"] == s
    assert b["meta"]["weeks"] == history_summary(sezon=s)["meta"]["weeks"]


def test_stats_oran_karti_AYNI_sezondan_gelir(client):
    """En sinsi hata buydu: `weeks` yalnızca hafta NUMARASI taşır.

    Sezon geçirilmezse başka bir sezonun arşivinde aynı numaralar bulunur
    ve oran kartı sessizce başka bir sezonu anlatırdı.
    """
    from spor_toto.odds import season_1x2_summary

    s = "2023_24"
    b = client.get(f"/api/stats?sezon={s}").get_json()
    beklenen = season_1x2_summary(
        [w["week"] for w in b["weeks"]], s)
    assert b["odds"]["with_odds"] == beklenen["with_odds"]
    assert b["odds"]["brier_avg"] == beklenen["brier_avg"]
    # Varsayılanla aynı olsaydı sezon geçmemiş demektir.
    varsayilan = client.get("/api/stats").get_json()
    assert b["odds"]["with_odds"] != varsayilan["odds"]["with_odds"]


def test_bilinmeyen_sezon_400_ve_listeyi_yazar(client):
    r = client.get("/api/stats?sezon=yok_boyle")
    assert r.status_code == 400
    assert r.get_json()["sezonlar"]


def test_hafta_detayi_sezonla_calisir(client):
    from spor_toto.history import history_weeks

    s = "2023_24"
    hafta = history_weeks(sezon=s)[0]["week"]
    b = client.get(f"/api/stats/{hafta}?sezon={s}").get_json()
    assert b["week"] == hafta
    assert len(b["odds"]) == 15, "seçilen sezonun oranları gelmedi"


def test_meta_sezon_listesini_yayinlar(client):
    b = client.get("/api/meta").get_json()
    assert b["seasons"]["default"] is None
    assert b["seasons"]["available"]
