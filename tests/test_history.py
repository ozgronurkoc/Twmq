"""Tarihsel istatistik katmanı — türetilmiş sayıların iç tutarlılığı."""

import pytest

from spor_toto.history import (
    MATCH_COUNT, SYMBOLS,
    count_distribution, extreme_weeks, history_analytics, history_summary,
    history_week, history_week_detail, history_weeks, normalized_weeks,
    position_stats, recent_form, streak_stats, transition_stats,
    _max_run, _runs,
)

WEEKS = normalized_weeks()


def test_weeks_sirali_ve_tam():
    numbers = [w["week"] for w in WEEKS]
    assert numbers == sorted(numbers)
    assert numbers, "veri dosyasi bos"
    for w in WEEKS:
        assert set(w["results"]) <= set(SYMBOLS)
        assert len(w["results"]) == MATCH_COUNT
        assert w["n1"] + w["n0"] + w["n2"] == MATCH_COUNT


def test_sayimlar_results_dizisinden_turetilir():
    for w in WEEKS:
        assert w["counts"] == {s: w["results"].count(s) for s in SYMBOLS}
        assert (w["n1"], w["n0"], w["n2"]) == (w["counts"]["1"], w["counts"]["0"], w["counts"]["2"])


def test_totals_haftalarla_uyumlu():
    s = history_summary()
    weeks = history_weeks()
    for sym in SYMBOLS:
        assert s["totals"][sym] == sum(w["counts"][sym] for w in weeks)
    assert sum(s["totals"][sym] for sym in SYMBOLS) == s["meta"]["matches"]
    assert s["meta"]["weeks"] == len(weeks)
    assert round(sum(s["totals"][f"pct_{sym}"] for sym in SYMBOLS), 2) == 100.0


def test_weekly_avg_ve_bands():
    s = history_summary()
    weeks = history_weeks()
    for sym in SYMBOLS:
        vals = [w["counts"][sym] for w in weeks]
        b = s["bands"][sym]
        assert b["min"] == min(vals) and b["max"] == max(vals)
        assert b["avg"] == pytest.approx(sum(vals) / len(vals), abs=1e-4)
        assert s["weekly_avg"][sym] == pytest.approx(b["avg"], abs=1e-4)
        assert b["above_n"] + b["below_n"] == len(vals)
        assert b["above_gap"] >= 0 and b["below_gap"] >= 0


def test_last_dilimi_son_haftalari_verir():
    tam = history_weeks()
    dilim = history_weeks(5)
    assert len(dilim) == 5
    assert [w["week"] for w in dilim] == [w["week"] for w in tam[-5:]]
    s = history_summary(5)
    assert s["meta"]["weeks"] == 5
    assert s["meta"]["sliced"] is True
    assert s["meta"]["matches"] == 5 * MATCH_COUNT
    assert history_summary()["meta"]["sliced"] is False


def test_last_hafta_sayisindan_buyukse_tum_sezon():
    assert len(history_weeks(10_000)) == len(history_weeks())


def test_data_quality_catisan_haftalari_raporlar():
    dq = history_summary()["data_quality"]
    assert dq["source"] == "results"
    assert dq["weeks_total"] == len(WEEKS)
    assert dq["incomplete_weeks"] == []
    for c in dq["count_conflicts"]:
        assert c["reported"] != c["derived"]
        assert sum(c["derived"].values()) == MATCH_COUNT
    for d in dq["duplicate_results"]:
        assert len(d["weeks"]) > 1
    assert dq["ok"] == (not dq["count_conflicts"] and not dq["duplicate_results"])


def test_position_stats_her_maca_tum_haftalari_dagitir():
    pos = position_stats(WEEKS)
    assert [p["pos"] for p in pos] == list(range(1, MATCH_COUNT + 1))
    for p in pos:
        assert sum(p["counts"].values()) == len(WEEKS) == p["n"]
        assert sum(p["pct"].values()) == pytest.approx(100.0, abs=0.05)
        assert p["top"] in SYMBOLS
    # sütun toplamları sezon toplamına eşit
    for sym in SYMBOLS:
        assert sum(p["counts"][sym] for p in pos) == sum(w["counts"][sym] for w in WEEKS)


def test_transition_stats_toplamlari():
    t = transition_stats(WEEKS)
    assert t["n"] == len(WEEKS) * (MATCH_COUNT - 1)
    assert sum(sum(row.values()) for row in t["counts"].values()) == t["n"]
    for a in SYMBOLS:
        if t["row_totals"][a]:
            assert sum(t["pct"][a].values()) == pytest.approx(100.0, abs=0.05)
    assert 0 <= t["repeat_pct"] <= 100


def test_count_distribution_hafta_sayisini_korur():
    dist = count_distribution(WEEKS)
    for sym in SYMBOLS:
        assert sum(b["weeks"] for b in dist[sym]) == len(WEEKS)
        # k * hafta toplamı = sezon toplamı
        assert sum(b["count"] * b["weeks"] for b in dist[sym]) == sum(
            w["counts"][sym] for w in WEEKS
        )
        assert [b["count"] for b in dist[sym]] == list(range(len(dist[sym])))


def test_runs_ve_streak():
    assert _runs("110") == [
        {"symbol": "1", "start": 1, "length": 2},
        {"symbol": "0", "start": 3, "length": 1},
    ]
    assert _runs("") == []
    assert _max_run("100011")["length"] == 3
    assert _max_run("")["length"] == 0

    st = streak_stats(WEEKS)
    for sym in SYMBOLS:
        best = st["by_symbol"][sym]
        if best["length"]:
            hafta = next(w for w in WEEKS if w["week"] == best["week"])
            assert sym * best["length"] in hafta["results"]
    assert st["top"] == sorted(st["top"], key=lambda r: (-r["length"], r["week"], r["start"]))
    assert st["avg_week_max"] >= 1


def test_extremes_ve_recent():
    ex = extreme_weeks(WEEKS)
    for sym in SYMBOLS:
        vals = [w["counts"][sym] for w in WEEKS]
        assert ex[sym]["max"]["value"] == max(vals)
        assert ex[sym]["min"]["value"] == min(vals)

    rec = recent_form(WEEKS, window=6)
    assert rec["window"] == 6
    assert rec["weeks"] == [w["week"] for w in WEEKS[-6:]]
    for sym in SYMBOLS:
        assert rec["avg"][sym] == pytest.approx(
            sum(w["counts"][sym] for w in WEEKS[-6:]) / 6, abs=1e-2
        )


def test_bos_veride_cokmez():
    assert position_stats([])[0]["n"] == 0
    assert transition_stats([])["n"] == 0
    assert count_distribution([]) == {s: [{"count": 0, "weeks": 0, "pct": 0.0}] for s in SYMBOLS}
    assert streak_stats([])["by_symbol"]["1"]["length"] == 0
    assert extreme_weeks([])["1"]["max"] is None
    assert recent_form([])["window"] == 0


def test_analytics_bloklari():
    a = history_analytics()
    assert set(a) == {"positions", "transitions", "distribution", "streaks", "extremes", "recent"}
    assert len(a["positions"]) == MATCH_COUNT
    a5 = history_analytics(5)
    assert a5["transitions"]["n"] == 5 * (MATCH_COUNT - 1)


def test_week_detail():
    hafta = WEEKS[1]["week"]
    d = history_week_detail(hafta)
    assert d is not None
    assert d["week"] == hafta
    assert d["prev_week"] == WEEKS[0]["week"]
    assert d["next_week"] == WEEKS[2]["week"]
    assert [c["symbol"] for c in d["cells"]] == list(d["results"])
    assert [c["pos"] for c in d["cells"]] == list(range(1, MATCH_COUNT + 1))
    assert "".join(r["symbol"] * r["length"] for r in d["runs"]) == d["results"]
    for sym in SYMBOLS:
        assert d["delta_vs_avg"][sym] == pytest.approx(
            d["counts"][sym] - d["season_avg"][sym], abs=1e-2
        )
        assert 1 <= d["rank"][sym]["rank"] <= d["rank"][sym]["of"] == len(WEEKS)
    assert len(d["position_stats"]) == MATCH_COUNT

    assert history_week_detail(WEEKS[0]["week"])["prev_week"] is None
    assert history_week_detail(WEEKS[-1]["week"])["next_week"] is None
    assert history_week_detail(99_999) is None
    assert history_week(99_999) is None
    assert history_week(hafta)["results"] == d["results"]


def test_rank_en_yuksek_haftayi_birinci_yapar():
    for sym in SYMBOLS:
        hi = max(WEEKS, key=lambda w: (w["counts"][sym], -w["week"]))
        assert history_week_detail(hi["week"])["rank"][sym]["rank"] == 1
