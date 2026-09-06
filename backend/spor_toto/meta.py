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

from typing import Any

from .bayes import STRENGTH_PRESETS
from .core import HAS_SCIPY, MAC_SAYISI, SEMBOLLER

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

# **Yedi mod bire indi.** Kaplama katmanı söküldü
# (`docs/DUZ_SISTEME_GECIS.md`) ve onunla birlikte `fix16`, `auto`, `exact`,
# `block`, `heuristic`, `butce`, `maxcov` da gitti. Hepsi aynı soruyu
# soruyordu — *seçim kümesini en az kaç kolonla örtebilirim?* Düzde o soru
# yok: kümenin tamamı oynanıyor, yani arama değil üretim var.
#
# Liste yine de **liste** olarak duruyor: `/api/meta` sözleşmesi ve arayüz
# bir dizi bekliyor, ve tek elemanlı bir dizi "mod kavramı kalktı" demenin
# uyumlu yoludur.
DUZ_MOD = "duz"
MODES: list[dict[str, Any]] = [
    {"id": DUZ_MOD, "label": "Düz (tam sistem)", "garanti": True,
     "needs_budget": False, "needs_scipy": False,
     "aciklama": "Seçim kümesinin tamamı oynanır; indirgeme yok. Sonuç "
                 "kümenin içindeyse bir kolon 15 tutturur, küme dışında "
                 "kalan her maç en iyi kolonu bir kademe düşürür."},
]
MODE_IDS: set[str] = {m["id"] for m in MODES}

# **Motor varsayilanlari BOSALDI ve alan bilerek duruyor.**
#
# Burada yedi ayar vardi (`trials`, `ls_iters`, `seed`, `time_limit`,
# `block_limit`, `exact_limit`, `auto_ilp_limit`) ve hepsi kaplama
# ARAMASININ ayarlariydi: kac deneme, kac yerel arama adimi, ILP'ye kac
# saniye. Kaplama sokuldu (`docs/DUZ_SISTEME_GECIS.md`); duzde arama yok,
# kolonlar carpimdan uretiliyor, ayarlanacak bir sey kalmadi.
#
# Alan `/api/meta` sozlesmesinde BOS SOZLUK olarak duruyor: arayuz onu
# okuyor ve `health._check_meta_sozlesmesi` her girdisinin `limits` icinde
# olmasini sart kosuyor. Bos birakmak "ayar yok" demenin uyumlu yoludur;
# alani silmek arayuzu kirardi ve "ayar var ama ilan edilmiyor" ile
# ayirt edilemezdi.
ENGINE_DEFAULTS: dict[str, Any] = {}

# Her sinir icin min <= default <= max tutmak ZORUNDADIR; arayuz kaydiraclari
# dogrudan bu sayilardan uretiliyor.
LIMITS: dict[str, dict[str, Any]] = {
    "mc_samples": {"min": MC_MIN, "max": MC_MAX, "default": MC_WEB_SAMPLES},
    "fire_max": {"min": 0, "max": 2, "default": FIRE_MAX_VARSAYILAN},
    "fire_maliyet": {"min": 0, "max": FIRE_MAX_MALIYET},
    # **`budget`, `plan_count` ve `plan_apply` dustu.** Ucu de kaplama
    # butce danismaninin (`core.butce_danismani`) ayarlariydi: "elimde N
    # kolon var, hangi isareti kismaliyim, kac plan uret, hangisini
    # uygula". Duzde bedel isaretlerin kendisi; kismak icin isareti
    # degistirirsin, motora butce vermezsin. `/api/solve` bu alanlari
    # ARTIK KABUL ETMIYOR.
}


def bayes_preset_listesi() -> list[dict[str, Any]]:
    return [
        {"id": k,
         "prior_strength": v["prior_strength"],
         "evidence_strength": v["evidence_strength"]}
        for k, v in STRENGTH_PRESETS.items()
    ]


def meta_payload(version: str) -> dict[str, Any]:
    """`/api/meta` govdesi. Uc yalnizca bunu jsonify eder."""
    # Geri test izgarasi da sabit kodlanmaz; motorla tek kaynaktan senkron
    # kalsin diye backtest modulunden okunur. Import burada: backtest, veri
    # katmanini acar ve meta modulunun import maliyeti olmamalidir.
    from .backtest import (
        BANKO_IZGARA,
        UCLU_IZGARA,
        VARSAYILAN_BANKO,
        VARSAYILAN_UCLU,
    )
    from .history import sezonlar as _sezonlar

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
        # Arayuzun `?sezon=` icin kullanabilecegi liste. VARSAYILAN bu
        # listede YOKTUR ve olmamali: o bir sezon secimi degil, "hicbir sey
        # secilmedi" hali (§6G.5 — 2025/26'nin iki ayri okumasi var).
        "seasons": {
            "default": None,
            "available": _sezonlar(),
            "note": ("varsayilan secim yok; secilirse `?sezon=` ile "
                     "gonderilir. `2025_26` varsayilanin AYNI sezonu ikinci "
                     "kez okumasidir (29 hafta / 41 hafta)"),
        },
        "limits": LIMITS,
    }
