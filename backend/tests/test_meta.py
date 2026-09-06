"""`/api/meta` sözleşmesi ve mod çalıştırıcıları.

Buradaki testler iki şeyi bağlar: (1) ilan edilen envanterin kendi içinde
tutarlı olması, (2) ilan edilen her modun gerçekten koşabilmesi. İkisi
ayrıştığında arayüz seçilebilir ama bozuk bir mod gösterir.
"""

import pytest

from spor_toto import __version__
from spor_toto.bayes import STRENGTH_PRESETS
from spor_toto.core import HAS_SCIPY, Encoder, parse_picks
from spor_toto.duz import kolonlar as duz_kolonlar
from spor_toto.history import MATCH_COUNT
from spor_toto.meta import DUZ_MOD, ENGINE_DEFAULTS, LIMITS, MODE_IDS, MODES, meta_payload

# 7 çifte -> 128 nokta, alt sınır 16 kolon.
KUCUK = "1,1,1,1,1,1,1,10,10,10,10,10,10,10,1"
gerek_scipy = pytest.mark.skipif(not HAS_SCIPY, reason="scipy yok")


@pytest.fixture()
def enc():
    return Encoder(parse_picks(KUCUK))


# `eng` fixture'i (motor parametreleri) burada durdu ve `engine_params`i
# cagiriyordu; o fonksiyon `engines.py` ile birlikte soküldu. Fixture'i
# kullanan test kalmamisti — yani ruff'in `F821 Undefined name` uyarisi
# calisma zamaninda hicbir zaman patlamayacak olu koddu.


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

def test_ilan_edilen_TEK_mod_kosuyor(enc):
    """Meta'da ilan edilen mod gerçekten koşuyor ve kümenin tamamını veriyor.

    **Burada beş mod koşturuluyordu** (`fix16`, `auto`, `block`,
    `heuristic`, `butce`) ve her birinin ürettiği kaplamanın geçerli olup
    olmadığı `dogrula_kaplama` ile sınanıyordu. Kaplama söküldü
    (`docs/DUZ_SISTEME_GECIS.md`): geriye tek mod kaldı ve onun sözü
    "örtüyorum" değil **"kümenin tamamını oynuyorum"**.
    """
    assert [m["id"] for m in MODES] == [DUZ_MOD]
    mod = MODES[0]
    assert mod["garanti"] is True
    cols = duz_kolonlar(enc)
    assert len(cols) == enc.space_size()
    assert len(set(cols)) == len(cols)


def test_garanti_VERMEYEN_mod_kalmadi():
    """`maxcov` gitti: düzde garantisiz bir oynama biçimi yok.

    Eski test şunu bağlıyordu: *"maxcov meta'da `garanti: False` ilan eder;
    bayrak ile davranış ayrışırsa kullanıcı garanti sandığı bir kupon
    oynar."* Düzde her kupon kümenin tamamını oynar, yani `garanti: False`
    ilan edecek bir mod yok. Değişmez ayakta: **ilan edilen bayrak gerçeği
    söylemeli.**
    """
    assert [m for m in MODES if not m["garanti"]] == []

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
