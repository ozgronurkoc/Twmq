"""Oran arşivi — arşivin geçmiş veri setiyle hizada kaldığını denetler.

Bu testler arayüzü değil, ileride yapılacak analizin girdisini korur.
"""

import pytest

from spor_toto.history import normalized_weeks
from spor_toto.odds import (
    coverage,
    implied_probs,
    load_odds,
    market_odds,
)

ROWS = load_odds()
WEEKS = normalized_weeks()

pytestmark = pytest.mark.skipif(not ROWS, reason="oran arşivi yok (scripts/build_odds.py)")


def test_arsiv_gecmis_veriyle_birebir_hizali():
    """Her kupon maçının arşivde tam bir karşılığı olmalı — sırasıyla."""
    beklenen = [(w["week"], m["no"]) for w in WEEKS for m in w["matches"]]
    gercek = [(r["week"], r["no"]) for r in ROWS]
    assert gercek == beklenen


def test_takim_ve_skorlar_kaymamis():
    kupon = {(w["week"], m["no"]): m for w in WEEKS for m in w["matches"]}
    for r in ROWS:
        m = kupon[(r["week"], r["no"])]
        assert (r["home"], r["away"]) == (m["home"], m["away"])
        assert (r["hg"], r["ag"], r["code"]) == (m["hg"], m["ag"], m["code"])


def test_eslesen_satirda_1x2_kapanis_orani_var():
    for r in ROWS:
        if not r["matched"]:
            continue
        o = market_odds(r, "1X2", "Avg")
        if not o:  # ek ülke dosyalarında Avg yoksa B365 var
            o = market_odds(r, "1X2", "B365")
        assert set(o) == {"1", "0", "2"}, f"{r['week']}/{r['no']} 1X2 eksik"
        assert all(v > 1.0 for v in o.values())


def test_kapsama_makul():
    k = coverage()
    assert k["matches"] == sum(len(w["matches"]) for w in WEEKS)
    # Milli maç haftaları bu kaynakta yok; %85 altına düşerse eşleştirme bozulmuştur.
    assert k["pct"] >= 85.0
    assert k["odds_values"] > 10_000


def test_marj_arindirma():
    r = next(x for x in ROWS if x["matched"])
    o = market_odds(r, "1X2", "Avg") or market_odds(r, "1X2", "B365")
    p = implied_probs(o)
    assert set(p) == set(o)
    assert sum(p.values()) == pytest.approx(1.0, abs=1e-9)
    # Marj: ham olasılık toplamı 1'in üstünde olmalı (bahisçi payı).
    assert sum(1 / v for v in o.values()) > 1.0


def test_favori_isabeti_gerceklikle_uyumlu():
    """Kapanış favorisi ~%50–60 tutmalı; bu, eşleştirmenin sağlamasıdır."""
    tut = top = 0
    for r in ROWS:
        if not r["matched"]:
            continue
        o = market_odds(r, "1X2", "Avg") or market_odds(r, "1X2", "B365")
        if len(o) != 3:
            continue
        favori = min(o, key=lambda s: o[s])
        top += 1
        tut += favori == r["code"]
    assert top > 400
    assert 0.45 <= tut / top <= 0.70, f"favori isabeti %{100 * tut / top:.1f} — eşleştirme şüpheli"

