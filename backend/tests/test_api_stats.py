"""/api/stats uçları — sözleşme testleri."""

import pytest

pytest.importorskip("flask")

from web_app import app  # noqa: E402
from spor_toto.history import MATCH_COUNT, SYMBOLS, history_weeks  # noqa: E402


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


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


def test_olmayan_hafta_404(client):
    r = client.get("/api/stats/99999")
    assert r.status_code == 404
    assert "error" in r.get_json()
