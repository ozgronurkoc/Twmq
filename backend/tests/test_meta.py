"""`/api/meta` sözleşmesi ve mod çalıştırıcıları.

Buradaki testler iki şeyi bağlar: (1) ilan edilen envanterin kendi içinde
tutarlı olması, (2) ilan edilen her modun gerçekten koşabilmesi. İkisi
ayrıştığında arayüz seçilebilir ama bozuk bir mod gösterir.
"""

import pytest

from spor_toto import __version__
from spor_toto.bayes import STRENGTH_PRESETS
from spor_toto.core import HAS_SCIPY, Encoder, dogrula_kaplama, parse_picks
from spor_toto.engines import (
    engine_params,
    run_auto,
    run_block,
    run_butce,
    run_exact,
    run_fix16,
    run_heuristic,
    run_maxcov,
)
from spor_toto.history import MATCH_COUNT
from spor_toto.meta import ENGINE_DEFAULTS, LIMITS, MODE_IDS, MODES, meta_payload

# 7 çifte -> 128 nokta, alt sınır 16 kolon.
KUCUK = "1,1,1,1,1,1,1,10,10,10,10,10,10,10,1"
gerek_scipy = pytest.mark.skipif(not HAS_SCIPY, reason="scipy yok")


@pytest.fixture()
def enc():
    return Encoder(parse_picks(KUCUK))


@pytest.fixture()
def eng():
    return engine_params(trials=1, ls_iters=2_000, time_limit=10.0,
                         exact_limit=256, block_limit=256)


# ─── envanter ─────────────────────────────────────────────────────────────────

def test_meta_govdesi():
    m = meta_payload(__version__)
    assert set(m) >= {
        "version", "has_scipy", "match_count", "symbols", "modes",
        "bayes_presets", "engine_defaults", "backtest", "limits",
    }
    assert m["version"] == __version__
    assert m["match_count"] == MATCH_COUNT
    assert m["has_scipy"] is HAS_SCIPY


def test_mod_kimlikleri_tekil_ve_dolu():
    ids = [m["id"] for m in MODES]
    assert len(ids) == len(set(ids)) == len(MODE_IDS)
    for m in MODES:
        assert m["label"] and m["aciklama"]
        for bayrak in ("garanti", "needs_budget", "needs_scipy"):
            assert isinstance(m[bayrak], bool)


def test_sinirlarda_min_varsayilan_max_sirasi():
    for ad, lim in LIMITS.items():
        assert lim["min"] <= lim["max"], ad
        if "default" in lim:
            assert lim["min"] <= lim["default"] <= lim["max"], ad


def test_motor_varsayilanlari_sinirlarin_icinde():
    for ad, deger in ENGINE_DEFAULTS.items():
        lim = LIMITS.get(ad)
        if lim is not None:
            assert lim["min"] <= deger <= lim["max"], ad


def test_bayes_presetleri_motorla_ayni():
    m = meta_payload(__version__)
    presetler = {p["id"]: p for p in m["bayes_presets"]}
    assert set(presetler) == set(STRENGTH_PRESETS)
    for ad, p in presetler.items():
        assert p["prior_strength"] == STRENGTH_PRESETS[ad]["prior_strength"]
        assert p["evidence_strength"] == STRENGTH_PRESETS[ad]["evidence_strength"]


def test_geri_test_varsayilanlari_izgarada():
    bt = meta_payload(__version__)["backtest"]
    assert bt["banko_default"] in bt["banko_grid"]
    assert bt["uclu_default"] in bt["uclu_grid"]


# ─── mod çalıştırıcıları ──────────────────────────────────────────────────────

def _kaplama_gecerli(cols, sizes) -> bool:
    worst, acik = dogrula_kaplama(cols, sizes)
    return worst <= 1 and acik == 0


def test_garanti_ilan_eden_modlar_gercekten_kapliyor(enc, eng):
    kosucular = {
        "fix16": lambda: run_fix16(enc),
        "auto": lambda: run_auto(enc, eng),
        "block": lambda: run_block(enc, eng),
        "heuristic": lambda: run_heuristic(enc, eng),
        "butce": lambda: run_butce(enc, 24),
    }
    for m in MODES:
        if not m["garanti"] or m["id"] not in kosucular:
            continue
        r = kosucular[m["id"]]()
        e = r.get("enc", enc)
        assert _kaplama_gecerli(r["cols"], e.alphabet_sizes), m["id"]


@gerek_scipy
def test_exact_modu_kapliyor(enc, eng):
    r = run_exact(enc, eng)
    assert _kaplama_gecerli(r["cols"], enc.alphabet_sizes)


def test_maxcov_garanti_vermez(enc):
    """Alt sınırın (16) altındaki bir bütçeyle tam kaplama İMKÂNSIZDIR.

    maxcov meta'da `garanti: False` ilan eder; bu test o ilanın gerçek
    olduğunu bağlar — bayrak ile davranış ayrışırsa kullanıcı garanti
    sandığı bir kupon oynar.
    """
    r = run_maxcov(enc, 8)
    _worst, acik = dogrula_kaplama(r["cols"], enc.alphabet_sizes)
    assert acik > 0
    assert len(r["cols"]) <= 8
    assert r["kapsanan"] + acik == enc.space_size()


def test_butce_plani_butceyi_asmaz(enc):
    r = run_butce(enc, 24)
    planlar = r["planlar"]
    assert planlar
    assert planlar[r["secili_index"]].bedel <= 24
    assert len(r["cols"]) <= 24
    assert r["enc"] is not enc  # plan kuponu daralttı


def test_butce_sigmayan_butcede_hata_verir(enc):
    with pytest.raises(ValueError, match="bütçeye sığan plan yok"):
        run_butce(enc, 1)


def test_engine_params_varsayilanlari_tamamlar():
    p = engine_params(trials=3)
    assert p["trials"] == 3
    assert p["seed"] == ENGINE_DEFAULTS["seed"]
    assert engine_params()["ls_iters"] == ENGINE_DEFAULTS["ls_iters"]


# ─── uç: /api/meta ve ilan edilen modların çalışabilirliği ────────────────────

# `client` fixture'i `tests/conftest.py`den geliyor — ayni govde bes
# dosyada, ucu BIREBIR yaziliydi. (Ezmesi gereken ikisi eziyor:
# `test_api_health` onbellek temizliyor, `test_tahmin` modul kapsamli.)


def test_meta_ucu_ayni_govdeyi_verir(client):
    body = client.get("/api/meta").get_json()
    assert body == meta_payload(__version__)


def test_ilan_edilen_her_mod_solve_edilebilir(client):
    """Meta'da ilan edilen bir mod, `/api/solve` tarafından tanınmak
    ZORUNDADIR: arayüz mod listesini meta'dan üretir, seçilebilir ama
    çalışmayan bir mod doğrudan kullanıcıya çarpar."""
    for m in MODES:
        if m["needs_scipy"] and not HAS_SCIPY:
            continue
        govde = {"picks": KUCUK, "mode": m["id"],
                 "trials": 1, "ls_iters": 2000, "exact_limit": 256,
                 "time_limit": 10.0, "fire_max": 0, "mc_samples": 1000}
        if m["needs_budget"]:
            govde["budget"] = 24 if m["id"] == "butce" else 8
        r = client.post("/api/solve", json=govde)
        body = r.get_json()
        assert r.status_code == 200, f"{m['id']}: {body.get('error')}"
        assert body["ok"] is True, f"{m['id']}: {body.get('error')}"
        assert body["result"]["mode"] == m["id"]
        # `garanti` bayrağı sonuçla ayrışmamalı.
        assert body["result"]["guaranteed"] is m["garanti"], m["id"]
