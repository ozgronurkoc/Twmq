"""Geri test — strateji, kaplama ve skorlamanın denetimi.

Buradaki testlerin çoğu **sentetik** haftalar kullanır: gerçek veri setinde
küme içi kalan hafta neredeyse hiç yok (bulgunun kendisi bu), o yüzden
skorlamanın doğruluğu ancak sonucu bilinen kurgu haftalarla kanıtlanabilir.
"""

import pytest

from spor_toto.backtest import (
    BANKO_IZGARA,
    UCLU_IZGARA,
    UZAY_SINIRI,
    _hafta_calistir,
    _wilson,
    backtest,
    esik_taramasi,
    hafta_girdileri,
    holdout,
    izgara_tablosu,
    secim_uret,
)
from spor_toto.history import MATCH_COUNT
from spor_toto.odds import load_odds

KUVVETLI = {"1": 0.90, "0": 0.05, "2": 0.05}
ORTA = {"1": 0.45, "0": 0.35, "2": 0.20}
BELIRSIZ = {"1": 0.35, "0": 0.34, "2": 0.31}


def _girdi(results: str, probs) -> dict:
    return {
        "week": 99, "close_date": "2026-01-01", "results": results,
        "probs": list(probs), "missing": 0, "usable": True,
    }


# ─── strateji ─────────────────────────────────────────────────────────────────

def test_secim_esige_gore_banko_cifte_uclu():
    assert secim_uret(KUVVETLI, 0.68, 0.38) == ["1"]
    assert secim_uret(ORTA, 0.68, 0.38) == ["1", "0"]
    assert secim_uret(BELIRSIZ, 0.68, 0.38) == ["1", "0", "2"]


def test_secim_kupon_duzeninde_siralanir():
    """Çifte '01' değil '10' yazılır — kupon düzeni alfabetik değildir."""
    assert secim_uret({"1": 0.45, "0": 0.40, "2": 0.15}, 0.68, 0.0) == ["1", "0"]
    assert secim_uret({"2": 0.45, "0": 0.40, "1": 0.15}, 0.68, 0.0) == ["0", "2"]


def test_anlamsiz_esik_ciftinde_bile_tanimli():
    """banko <= uclu verilse bile önce banko sorulur, çıktı tanımlı kalır."""
    assert secim_uret(KUVVETLI, 0.30, 0.80) == ["1"]
    assert secim_uret(ORTA, 0.99, 0.99) == ["1", "0", "2"]


# ─── skorlama ─────────────────────────────────────────────────────────────────

def test_kume_ici_hafta_15_tutturur():
    """13 doğru banko + sonucu içeren 2 çifte: 2 kolon, küme içi, 15 doğru."""
    h = _hafta_calistir(_girdi("1" * 13 + "10", [KUVVETLI] * 13 + [ORTA, ORTA]),
                        0.68, 0.38)
    assert h["banko"] == 13 and h["double"] == 2 and h["triple"] == 0
    assert h["columns"] == 2 and h["in_set"] is True
    assert h["misses"] == 0 and h["miss_at"] == []
    assert h["best"] == MATCH_COUNT
    assert h["guaranteed"] is True


def test_tek_kacak_14e_duser_ve_yeri_raporlanir():
    girdi = _girdi("1" * 12 + "2" + "10", [KUVVETLI] * 13 + [ORTA, ORTA])
    h = _hafta_calistir(girdi, 0.68, 0.38)
    assert h["in_set"] is False
    assert h["misses"] == 1 and h["miss_at"] == [13]
    assert h["best"] == MATCH_COUNT - 1


def test_iki_kacak_13e_duser():
    girdi = _girdi("1" * 11 + "22" + "10", [KUVVETLI] * 13 + [ORTA, ORTA])
    h = _hafta_calistir(girdi, 0.68, 0.38)
    assert h["misses"] == 2 and h["miss_at"] == [12, 13]
    assert h["best"] == MATCH_COUNT - 2


def test_kacak_numaralari_1_tabanli_ve_sirali():
    girdi = _girdi("2" + "1" * 12 + "10", [KUVVETLI] * 13 + [ORTA, ORTA])
    h = _hafta_calistir(girdi, 0.68, 0.38)
    assert h["miss_at"] == [1]


def test_uzay_siniri_asilirsa_hafta_atlanir():
    """15 üçlü = 14,3 M nokta. Doğrulanamayacak bedel raporlanmaz."""
    h = _hafta_calistir(_girdi("1" * 15, [BELIRSIZ] * 15), 0.99, 0.99)
    assert h["skipped"] is True
    assert str(UZAY_SINIRI) in h["reason"].replace(",", "")


def test_kaplama_her_zaman_14_garantili():
    """Küme içi kalan bir haftada motor en fazla 1 hataya izin verir."""
    h = _hafta_calistir(_girdi("1" * 5 + "0" * 5 + "1" * 5,
                               [ORTA] * 15), 0.68, 0.0)
    assert h["double"] == 15 and h["guaranteed"] is True
    assert h["in_set"] is True
    assert h["best"] >= MATCH_COUNT - 1


# ─── Wilson ───────────────────────────────────────────────────────────────────

def test_wilson_sinirlari_araligi_asmaz():
    for basari, n in ((0, 36), (36, 36), (3, 36), (1, 2)):
        lo, hi = _wilson(basari, n)
        assert 0.0 <= lo <= hi <= 1.0
    assert _wilson(0, 0) == (0.0, 0.0)


def test_wilson_kenarda_bile_daralir():
    """40/41'de normal yaklaşım 1'i aşardı; Wilson aşmaz."""
    lo, hi = _wilson(40, 41)
    assert hi <= 1.0 and lo > 0.8


# ─── sezon (gerçek veri) ──────────────────────────────────────────────────────

pytestmark_veri = pytest.mark.skipif(
    not load_odds(), reason="oran arşivi yok (scripts/build_odds.py)"
)


@pytestmark_veri
def test_girdiler_oransiz_haftayi_eler():
    girdiler = hafta_girdileri()
    assert girdiler
    for g in girdiler:
        assert len(g["probs"]) == MATCH_COUNT
        # Doktrin 2: eksik oranlı hafta tamamlanmaz, elenir.
        assert g["usable"] == (g["missing"] == 0 and len(g["results"]) == MATCH_COUNT)
    assert any(not g["usable"] for g in girdiler), "milli maç haftaları elenmeliydi"


@pytestmark_veri
def test_sezon_ozeti_tutarli():
    r = backtest(sweep=False)
    s = r["season"]
    assert s["weeks"] == r["meta"]["weeks_used"] - s["skipped"]
    assert s["hit15"] <= s["hit14"] <= s["hit13"] <= s["weeks"]
    assert s["in_set"] <= s["hit14"], "küme içi hafta en az 14 tutturmalı"
    assert s["columns_total"] == sum(h["columns"] for h in r["weeks"] if not h["skipped"])
    lo, hi = s["hit14_ci"]
    assert lo <= s["hit14_pct"] <= hi
    assert r["warning"]


@pytestmark_veri
def test_dilim_daha_az_hafta_calistirir():
    tam = backtest(sweep=False)["meta"]["weeks_available"]
    dilim = backtest(last=6, sweep=False)["meta"]["weeks_available"]
    assert dilim == 6 < tam


@pytestmark_veri
def test_tarama_izgarayi_kapsar_ve_tablo_paylasilir():
    girdiler = hafta_girdileri()
    tablo = izgara_tablosu(girdiler)
    tarama = esik_taramasi(girdiler, tablo=tablo)
    assert len(tarama) == len(BANKO_IZGARA) * len(UCLU_IZGARA)
    for satir in tarama:
        assert satir["banko"] in BANKO_IZGARA and satir["uclu"] in UCLU_IZGARA
        assert satir["hit14"] <= satir["weeks"]
        assert satir["weeks"] + satir["skipped"] == len(tablo[(satir["banko"], satir["uclu"])])


@pytestmark_veri
def test_holdout_taramadan_iyi_olamaz():
    """Aşırı uyumun ölçüsü: hold-out, taramanın en iyisini geçemez."""
    girdiler = hafta_girdileri()
    tablo = izgara_tablosu(girdiler)
    tarama = esik_taramasi(girdiler, tablo=tablo)
    ho = holdout(girdiler, tablo=tablo)
    en_iyi = max(s["hit14"] for s in tarama)
    assert ho["hit14"] <= en_iyi
    assert ho["chosen"], "hangi eşiğin seçildiği raporlanmalı"


@pytestmark_veri
def test_hicbir_hafta_garantisiz_kalmaz():
    r = backtest(sweep=False)
    for h in r["weeks"]:
        if h["skipped"]:
            continue
        assert h["guaranteed"], f"{h['week']}. hafta kaplaması açık nokta bıraktı"
        assert h["banko"] + h["double"] + h["triple"] == MATCH_COUNT
        assert len(h["picks"]) == MATCH_COUNT
