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



# ─── birleşik kesitte oran özeti ─────────────────────────────────────────────

def test_birlesik_suzgec_HAFTA_NUMARASIYLA_calismaz():
    """Birleşik kesitte süzgeç `(sezon, hafta)` çiftidir — ve olmak zorunda.

    Hafta numarası dört kaydın dördünde de var. Süzgeç numara listesi
    kabul etseydi "2023/24'ün 12. haftası" isteği dört sezonun 12.
    haftasını birden geçirirdi: özet dolu görünür, maç sayısı dörde
    katlanır ve hiçbir yerde yazmazdı.
    """
    from spor_toto.history import TUM_SEZONLAR
    from spor_toto.odds import _kesit_satirlari

    tek = _kesit_satirlari([(("2023_24"), 12)], TUM_SEZONLAR)
    assert tek, "cift suzgeci hicbir satir gecirmedi"
    assert {r["sezon"] for r in tek} == {"2023_24"}
    assert {r["week"] for r in tek} == {12}
    assert {r["anahtar"] for r in tek} == {"2023_24-12"}

    # Aynı numara başka kayıtlarda da var — kanıt:
    hepsi = _kesit_satirlari(None, TUM_SEZONLAR)
    on_ikiler = {r["sezon"] for r in hepsi if r["week"] == 12}
    assert len(on_ikiler) > 1, "testin dayandigi cakisma yok"


def test_birlesik_ozet_haftalik_brier_ANAHTARLA_gruplar():
    """Aynı numaralı haftalar tek satırda toplanmamalı."""
    from spor_toto.history import TUM_SEZONLAR, normalized_weeks
    from spor_toto.odds import season_1x2_summary

    kesit = [(w["sezon"], w["week"]) for w in normalized_weeks(sezon=TUM_SEZONLAR)]
    ozet = season_1x2_summary(kesit, TUM_SEZONLAR)
    assert ozet is not None
    satirlar = ozet["weekly_brier"]
    anahtarlar = [h["anahtar"] for h in satirlar]
    assert len(set(anahtarlar)) == len(anahtarlar)
    # Numaraya göre gruplansaydı satır sayısı benzersiz numara kadar olurdu.
    assert len(satirlar) > len({h["week"] for h in satirlar})
    # Her satırın maç sayısı bir kuponu aşmamalı — çakışmanın ikinci kanıtı.
    for h in satirlar:
        assert h["n"] <= 15, f"{h['anahtar']}: {h['n']} mac — haftalar birlesmis"


def test_birlesik_ozet_tek_sezonlardan_BUYUK():
    """Birleşim gerçekten birleştiriyor mu — toplamın alt sınırı."""
    from spor_toto.history import TUM_SEZONLAR, birlesik_kesit, normalized_weeks
    from spor_toto.odds import season_1x2_summary

    kesit = [(w["sezon"], w["week"]) for w in normalized_weeks(sezon=TUM_SEZONLAR)]
    birlesik = season_1x2_summary(kesit, TUM_SEZONLAR)
    assert birlesik is not None
    toplam = 0
    for s in birlesik_kesit():
        tek = season_1x2_summary([w["week"] for w in normalized_weeks(sezon=s)], s)
        if tek:
            toplam += tek["matches"]
    assert birlesik["matches"] == toplam, "birlesim parcalarin toplami degil"
