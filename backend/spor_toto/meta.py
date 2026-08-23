"""Motorun yetenek envanteri — /api/meta'nin TEK kaynagi.

Arayuz mod listesini, Bayes preset'lerini, motor varsayilanlarini ve
sinirlari sabit kodlamaz; hepsini `/api/meta`'dan okur. Bu envanter daha
once `web_app.py` icinde duruyordu ve saglik katmani ona erisemiyordu:
web_app health'i import ettigi icin ters yon dairesel olurdu.

Buraya tasinmasinin sebebi tek: **ilan edilen sey ile calisan sey ayni
kaynaktan okunsun.** Meta bozulursa ana sayfanin tamami coker ama sagligin
haberi olmaz — `health._check_meta_sozlesmesi` artik bu bosluga bakar.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from .bayes import STRENGTH_PRESETS
from .core import MAC_SAYISI, SEMBOLLER, HAS_SCIPY

#: Kupon uzunlugu TEK kaynaktan (`core`) — ad korunuyor, deger degil.
MATCH_COUNT = MAC_SAYISI

MC_WEB_SAMPLES = 80_000
MC_MIN, MC_MAX = 1_000, 200_000

# Fire analizi senkron istek yolunda calisiyor. Olculen hiz ~24 M
# maliyet-birimi/sn (maliyet = ayrik senaryo x kolon): 7,4 M -> 311 ms.
# 20 M esigi ~0,85 sn'ye denk gelir. Uclu iceren gercekci bir kupon
# 440 M cikar ve bilerek atlanir.
FIRE_MAX_MALIYET = 20_000_000
FIRE_MAX_VARSAYILAN = 2

# Motorun tum modlari. `garanti` bir REKLAM degil sozlesmedir: saglik
# katmani her modu kosturup uretilen kaplamayi bu bayrakla karsilastirir
# (bkz. health._check_mod_envanteri).
MODES: List[Dict[str, Any]] = [
    {"id": "fix16", "label": "Sabit 16 satır", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "Her zaman 16 kupon satırı. En az 7 çifte zorunlu. "
                 "Hamming(7,4) tabanlı, kanıtlanmış optimal."},
    {"id": "auto", "label": "Otomatik", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "En ucuz çözümü arar; satır sayısı değişkendir."},
    {"id": "exact", "label": "Kesin çözücü (ILP)", "garanti": True,
     "needs_budget": False, "needs_scipy": True,
     "aciklama": "ILP ile kanıtlanmış optimal. Yalnızca küçük uzaylarda."},
    {"id": "block", "label": "Blok ayrıştırma", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "r=1 bloğu + tam sistem ayrıştırması; cebirsel bloklar."},
    {"id": "heuristic", "label": "Sezgisel", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "Açgözlü + local search. Büyük uzaylar için."},
    {"id": "butce", "label": "Bütçe danışmanı", "garanti": True,
     "needs_budget": True, "needs_scipy": False,
     "aciklama": "Elimde N kolon var, hangi maçı kısmalıyım?"},
    {"id": "maxcov", "label": "Maksimum kapsama", "garanti": False,
     "needs_budget": True, "needs_scipy": False,
     "aciklama": "Sabit bütçeyle maksimum kapsama. GARANTİ VERMEZ."},
]
MODE_IDS: Set[str] = {m["id"] for m in MODES}

# CLI ile birebir ayni motor varsayilanlari (bkz. spor_toto/cli.py).
#
# `auto_ilp_limit` ayri durur ve ayri bir sorunu cozer: `auto` modu
# `exact_limit` (512) altindaki her uzayda ILP'yi devreye sokuyordu ve 256
# noktalik gercekci bir kuponda **~11 saniye** suruyordu. Olculdu: ayni
# kupon 3 saniyelik sinirla da 32 kolon veriyor, yalnizca "optimallik
# kanitlandi" bayragini kaybediyor. `auto`nun sozu "en ucuzu ara"dir,
# "optimalligi kanitla" degil — kanit isteyen `--mode exact` kullanir.
ENGINE_DEFAULTS: Dict[str, Any] = {
    "trials": 5,
    "ls_iters": 30_000,
    "seed": 42,
    "time_limit": 60.0,
    "block_limit": 256,
    "exact_limit": 512,
    "auto_ilp_limit": 3.0,
}

# Her sinir icin min <= default <= max tutmak ZORUNDADIR; arayuz kaydiraclari
# dogrudan bu sayilardan uretiliyor.
LIMITS: Dict[str, Dict[str, Any]] = {
    "mc_samples": {"min": MC_MIN, "max": MC_MAX, "default": MC_WEB_SAMPLES},
    "fire_max": {"min": 0, "max": 2, "default": FIRE_MAX_VARSAYILAN},
    "fire_maliyet": {"min": 0, "max": FIRE_MAX_MALIYET},
    "plan_count": {"min": 1, "max": 50, "default": 5},
    "plan_apply": {"min": 1, "max": 50, "default": 1},
    "trials": {"min": 1, "max": 50, "default": ENGINE_DEFAULTS["trials"]},
    "ls_iters": {"min": 100, "max": 500_000, "default": ENGINE_DEFAULTS["ls_iters"]},
    "time_limit": {"min": 1.0, "max": 300.0, "default": ENGINE_DEFAULTS["time_limit"]},
    "block_limit": {"min": 2, "max": 6561, "default": ENGINE_DEFAULTS["block_limit"]},
    "exact_limit": {"min": 2, "max": 4096, "default": ENGINE_DEFAULTS["exact_limit"]},
    "auto_ilp_limit": {"min": 0.5, "max": 300.0,
                       "default": ENGINE_DEFAULTS["auto_ilp_limit"]},
}


def bayes_preset_listesi() -> List[Dict[str, Any]]:
    return [
        {"id": k,
         "prior_strength": v["prior_strength"],
         "evidence_strength": v["evidence_strength"]}
        for k, v in STRENGTH_PRESETS.items()
    ]


def meta_payload(version: str) -> Dict[str, Any]:
    """`/api/meta` govdesi. Uc yalnizca bunu jsonify eder."""
    # Geri test izgarasi da sabit kodlanmaz; motorla tek kaynaktan senkron
    # kalsin diye backtest modulunden okunur. Import burada: backtest, veri
    # katmanini acar ve meta modulunun import maliyeti olmamalidir.
    from .backtest import (
        BANKO_IZGARA, UCLU_IZGARA, VARSAYILAN_BANKO, VARSAYILAN_UCLU,
    )

    return {
        "version": version,
        "has_scipy": HAS_SCIPY,
        "match_count": MATCH_COUNT,
        "symbols": list(SEMBOLLER),
        "modes": MODES,
        "bayes_presets": bayes_preset_listesi(),
        "engine_defaults": ENGINE_DEFAULTS,
        "backtest": {
            "banko_default": VARSAYILAN_BANKO,
            "uclu_default": VARSAYILAN_UCLU,
            "banko_grid": list(BANKO_IZGARA),
            "uclu_grid": list(UCLU_IZGARA),
        },
        "limits": LIMITS,
    }
