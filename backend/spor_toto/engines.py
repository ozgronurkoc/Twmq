"""Mod calistiricilar — `/api/solve`'un ve saglik katmaninin ORTAK yolu.

Bu fonksiyonlar `web_app.py` icinde `_run_*` olarak duruyordu; oradan
cikarilmalarinin tek sebebi var: saglik raporu ilan edilen modlari
gercekten kosturabilsin, ama bunu **API ile ayni kodla** yapsin. Ikinci bir
kopya, biri guncellenip digeri unutuldugu gun ikisini de degersizlestirirdi.

Her calistirici ayni sozlesmeyi dondurur:

    {"cols": [...], "baslik": str, "notlar": [str, ...]}

`butce` bir istisnadir: uygulanan planin yani sira plan LISTESINI de
dondurur, cunku arayuz planlar arasindan secim yaptirir.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from .core import (
    Encoder, HAS_SCIPY, ball, butce_danismani, exact_cover,
    exact_max_coverage, greedy_full, merge_rows, solve_by_blocks,
    solve_fix16, solve_heuristic,
)
from .meta import ENGINE_DEFAULTS


def engine_params(**kwargs: Any) -> Dict[str, Any]:
    """Eksik parametreleri motor varsayilanlariyla tamamlar."""
    p = dict(ENGINE_DEFAULTS)
    p.update({k: v for k, v in kwargs.items() if v is not None})
    return p


def run_fix16(enc: Encoder, variant: int = 0) -> Dict[str, Any]:
    cols, aciklama = solve_fix16(enc, variant=variant)
    notlar = [aciklama]
    if variant:
        notlar.append(f"Varyant {variant}")
    return {"cols": cols, "baslik": f"Sabit 16 satır – {aciklama}", "notlar": notlar}


def run_auto(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    aday = []
    r = solve_by_blocks(enc, max_block_space=eng["block_limit"],
                        time_limit=min(30.0, eng["time_limit"]))
    if r:
        aday.append((r[0], f"Blok ayrıştırma ({r[1]})", False))
    if enc.space_size() <= eng["exact_limit"] and HAS_SCIPY:
        cols, kanit = exact_cover(enc.alphabet_sizes,
                                  time_limit=min(30.0, eng["time_limit"]))
        if cols:
            aday.append((cols, "Kesin çözücü (ILP)", kanit))
    if not any(a[2] for a in aday):
        cols_h = solve_heuristic(enc, trials=eng["trials"],
                                 ls_iters=min(10_000, eng["ls_iters"]),
                                 seed=eng["seed"])
        aday.append((cols_h, "Heuristik (açgözlü + local search)", False))
    if not aday:
        raise RuntimeError("Hiçbir motor sonuç üretemedi.")
    en_az = min(len(a[0]) for a in aday)
    esitler = [a for a in aday if len(a[0]) == en_az]
    cols, baslik, _ = min(esitler, key=lambda a: len(merge_rows(a[0])))
    return {"cols": cols, "baslik": baslik, "notlar": []}


def run_heuristic(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    cols = solve_heuristic(enc, trials=eng["trials"], ls_iters=eng["ls_iters"],
                           seed=eng["seed"])
    return {"cols": cols, "baslik": "Sezgisel (açgözlü + local search)",
            "notlar": [f"trials={eng['trials']} · ls_iters={eng['ls_iters']} "
                       f"· seed={eng['seed']}"]}


def run_exact(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    """Kesin cozucu (ILP). CLI'de vardi, API'de hic acilmamisti."""
    if not HAS_SCIPY:
        raise ValueError(
            "Kesin çözücü (ILP) scipy gerektirir; bu kurulumda scipy yok. "
            "Bunun yerine 'block' veya 'heuristic' modunu kullanın.")
    cols, kanit = exact_cover(enc.alphabet_sizes, time_limit=eng["time_limit"])
    if cols is None:
        raise ValueError(
            f"ILP çözüm üretemedi (uzay {enc.space_size()}, zaman sınırı "
            f"{eng['time_limit']:.0f} sn). Uzayı küçültün ya da 'auto' deneyin.")
    return {
        "cols": cols,
        "baslik": "Kesin çözücü (ILP)",
        "notlar": [f"Optimallik: {'KANITLANDI' if kanit else 'kanıtlanmadı (zaman sınırı)'}"],
    }


def run_block(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    """Blok ayristirma motoru. CLI'de vardi, API'de hic acilmamisti."""
    r = solve_by_blocks(enc, max_block_space=eng["block_limit"],
                        time_limit=eng["time_limit"])
    if not r:
        raise ValueError(
            "Blok ayrıştırma sonuç üretemedi. block_limit değerini artırmayı "
            "ya da 'auto' modunu deneyin.")
    cols, aciklama = r
    return {"cols": cols, "baslik": f"Blok ayrıştırma – {aciklama}",
            "notlar": [aciklama]}


def run_maxcov(enc: Encoder, budget: int) -> Dict[str, Any]:
    """Sabit butceyle en genis kapsama. GARANTI VERMEZ — meta'da da oyle ilan
    edilir; saglik katmani bu iki ifadenin ayrismadigini denetler."""
    cols, kapsanan, kanit = exact_max_coverage(enc.alphabet_sizes, budget)
    if cols is None:
        g = greedy_full(list(enc.variable_space()), enc.alphabet_sizes,
                        random.Random(42))
        cols = g[:budget]
        kapsanan = len({q for c in cols for q in ball(c, enc.alphabet_sizes)})
        kanit = False
    notlar = [
        f"Kapsanan nokta: {kapsanan}/{enc.space_size()} "
        f"(%{100 * kapsanan / enc.space_size():.2f})",
        f"Optimallik: {'KANITLANDI' if kanit else 'kanıtlanmadı (zaman sınırı)'}",
        "DİKKAT: bu bir GARANTİ DEĞİL, olasılıktır.",
    ]
    return {"cols": cols, "baslik": f"Maksimum kapsama – {budget} kolon",
            "notlar": notlar, "kapsanan": kapsanan, "kanit": kanit}


def run_butce(
    enc: Encoder,
    budget: int,
    user_probs: Optional[List[Dict[str, float]]] = None,
    plan_count: int = 5,
    plan_apply: int = 1,
    variant: int = 0,
) -> Dict[str, Any]:
    """Butce danismani: butceye sigan planlari uretir ve secileni cozer.

    Donen sozlukte `enc` YENIDIR — uygulanan plan kuponu daralttigi icin
    sonraki butun hesaplar (olasilik, fire, satirlar) o daraltilmis kupon
    uzerinde yapilmalidir.
    """
    planlar = butce_danismani(enc, budget, user_probs, en_fazla=plan_count)
    if not planlar:
        raise ValueError(
            f"{budget} kolonluk bütçeye sığan plan yok. "
            f"Daha fazla banko veya bütçe artırın."
        )
    idx = min(plan_apply, len(planlar)) - 1
    secili = planlar[idx]
    yeni_enc = Encoder(secili.selections)
    cols, aciklama = solve_fix16(yeni_enc, variant=variant)
    return {
        "cols": cols,
        "enc": yeni_enc,
        "baslik": f"Bütçe planı ({secili.bedel} kolon) – {aciklama}",
        "notlar": [
            f"Uygulanan plan {idx + 1}/{len(planlar)}: "
            f"{'; '.join(secili.degisiklikler) or 'değişiklik yok'}",
            f"Plan bedeli: {secili.bedel} kolon, {secili.satir} satır",
        ],
        "planlar": planlar,
        "secili_index": idx,
    }
