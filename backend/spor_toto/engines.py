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
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

from .core import (
    Encoder, HAS_SCIPY, Point, ball, butce_danismani, exact_cover,
    exact_max_coverage, greedy_full, merge_rows, solve_by_blocks,
    solve_fix16, solve_heuristic,
)
from .meta import ENGINE_DEFAULTS


def engine_params(**kwargs: Any) -> Dict[str, Any]:
    """Eksik parametreleri motor varsayilanlariyla tamamlar."""
    p = dict(ENGINE_DEFAULTS)
    p.update({k: v for k, v in kwargs.items() if v is not None})
    return p


@dataclass
class Aday:
    """Bir motorun urettigi aday kaplama.

    `kanit`, ILP'nin optimalligi KANITLADIGINI soyler; zaman sinirina
    takilmis bir ILP cozumu de gecerlidir ama kanitli degildir.
    """

    cols: List[Point]
    baslik: str
    kanit: bool = False


def adaylar(
    enc: Encoder,
    eng: Dict[str, Any],
    motorlar: Sequence[str] = ("block", "exact", "heuristic"),
    log: Optional[Callable[[str], None]] = None,
    ilp_zorunlu: bool = False,
    heuristic_ls_cap: Optional[int] = None,
) -> List[Aday]:
    """Istenen motorlari kosturup aday kaplamalari toplar.

    `/api/solve`'un `auto` modu, CLI'nin `--mode auto/block/exact/heuristic`
    dagitimi ve saglik kontrolu **bu tek fonksiyonu** kullanir. Uc ayri
    kopya vardi; biri guncellenip digeri unutuldugu gun ucu de degersizdi.

    `ilp_zorunlu` (CLI'de `--mode exact`) uzay `exact_limit`ten buyuk olsa
    da ILP'yi kosturur. Aksi halde ILP yalnizca sinirin altindaki uzaylarda
    ve `auto_ilp_limit` saniyelik kisa bir butceyle calisir.
    """
    def _yaz(mesaj: str) -> None:
        if log:
            log(mesaj)

    out: List[Aday] = []

    if "block" in motorlar:
        r = solve_by_blocks(enc, max_block_space=eng["block_limit"],
                            time_limit=min(30.0, eng["time_limit"]))
        if r:
            _yaz(f"Blok: {r[1]} -> {len(r[0])} kolon")
            out.append(Aday(r[0], f"Blok ayrıştırma ({r[1]})"))

    if "exact" in motorlar and HAS_SCIPY:
        uygun = ilp_zorunlu or enc.space_size() <= eng["exact_limit"]
        if uygun:
            # Kanit istenmedigi surece ILP kisa butceyle kosar: aksi halde
            # 256 noktalik gercekci bir kupon `auto` modunu 11 saniyeye
            # cikariyordu (bkz. meta.ENGINE_DEFAULTS).
            sinir = (eng["time_limit"] if ilp_zorunlu
                     else min(eng["auto_ilp_limit"], eng["time_limit"]))
            cols, kanit = exact_cover(enc.alphabet_sizes, time_limit=sinir)
            if cols:
                _yaz(f"ILP: {len(cols)} kolon "
                     f"({'optimallik kanıtlandı' if kanit else 'zaman sınırı'})")
                out.append(Aday(cols, "Kesin çözücü (ILP)", kanit))
        else:
            _yaz(f"ILP atlandı (uzay {enc.space_size()} > {eng['exact_limit']}).")

    if "heuristic" in motorlar:
        # `auto`da sezgisel yalnizca KANITLI bir aday yoksa kosar: kanitli
        # optimalin yanina daha kotu bir aday koymak bedelsiz degil, sure.
        tek_motor = tuple(motorlar) == ("heuristic",)
        if tek_motor or not any(a.kanit for a in out):
            iters = (eng["ls_iters"] if heuristic_ls_cap is None
                     else min(heuristic_ls_cap, eng["ls_iters"]))
            cols = solve_heuristic(enc, trials=eng["trials"], ls_iters=iters,
                                   seed=eng["seed"], log=log)
            _yaz(f"Heuristik: {len(cols)} kolon")
            out.append(Aday(cols, "Heuristik (açgözlü + local search)"))

    return out


def en_iyi_aday(adaylar_: Sequence[Aday]) -> Aday:
    """En az kolon; esitlikte en az SATIR. Kupon satirla doldurulur, kolonla
    odenir — ikisi ayni sey degildir."""
    if not adaylar_:
        raise RuntimeError("Hiçbir motor sonuç üretemedi.")
    en_az = min(len(a.cols) for a in adaylar_)
    esitler = [a for a in adaylar_ if len(a.cols) == en_az]
    return min(esitler, key=lambda a: len(merge_rows(a.cols)))


def run_fix16(enc: Encoder, variant: int = 0) -> Dict[str, Any]:
    cols, aciklama = solve_fix16(enc, variant=variant)
    notlar = [aciklama]
    if variant:
        notlar.append(f"Varyant {variant}")
    return {"cols": cols, "baslik": f"Sabit 16 satır – {aciklama}", "notlar": notlar}


def run_auto(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    """Blok + (uygunsa) ILP + sezgiselden en ucuzu.

    ILP burada KISA butceyle kosar (`auto_ilp_limit`, varsayılan 3 sn):
    ölçüldü, 256 noktalık gerçekçi bir kuponda tam çözüm ~11 saniye sürüyor
    ve 3 saniyelik sınırla bulunan kaplama aynı bedelde çıkıyor — kaybedilen
    tek şey "optimallik kanıtlandı" bayrağı.
    """
    liste = adaylar(enc, eng, heuristic_ls_cap=10_000)
    en_iyi = en_iyi_aday(liste)
    notlar: List[str] = []
    if en_iyi.kanit:
        notlar.append("ILP optimalliği kanıtladı.")
    elif len(en_iyi.cols) == enc.lower_bound():
        notlar.append("Alt sınıra eşit → kanıtlanmış optimal.")
    if len(liste) > 1:
        notlar.append("Denenen motorlar: " + ", ".join(
            f"{a.baslik.split(' (')[0]}={len(a.cols)}" for a in liste))
    return {"cols": en_iyi.cols, "baslik": en_iyi.baslik, "notlar": notlar}


def run_heuristic(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    cols = solve_heuristic(enc, trials=eng["trials"], ls_iters=eng["ls_iters"],
                           seed=eng["seed"])
    return {"cols": cols, "baslik": "Sezgisel (açgözlü + local search)",
            "notlar": [f"trials={eng['trials']} · ls_iters={eng['ls_iters']} "
                       f"· seed={eng['seed']}"]}


def run_exact(enc: Encoder, eng: Dict[str, Any]) -> Dict[str, Any]:
    """Kesin cozucu (ILP). Kanit isteyen mod budur: uzay sinirini yok sayar
    ve tam `time_limit` butcesini kullanir."""
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


class ButceSigmazHatasi(ValueError):
    """Butce gecerli ama ona sigan bir plan yok.

    `butce_danismani` gecersiz girdi icin de ValueError firlatir
    ("Butce pozitif olmali"). Ikisi ayni tiple gelince cagiran ayirt
    edemiyordu: CLI `--budget 0`i "plan bulunamadi" diye yutup 0 ile
    cikiyordu, oysa bu bir KULLANIM hatasidir ve 1 ile cikmali.
    """


def run_maxcov(enc: Encoder, budget: int,
               time_limit: Optional[float] = None,
               seed: int = 42) -> Dict[str, Any]:
    """Sabit butceyle en genis kapsama. GARANTI VERMEZ — meta'da da oyle ilan
    edilir; saglik katmani bu iki ifadenin ayrismadigini denetler.

    `time_limit` ve `seed` disaridan verilebilir cunku CLI kendi
    `--time-limit`/`--seed` bayraklarini tasiyor. Once CLI bu govdenin
    kendi kopyasini calistiriyordu ve iki kopyanin varsayilanlari
    AYRISMISTI: burada 120 sn / seed 42, CLI'da 60 sn / kullanicinin
    seed'i. Ayni istekten iki farkli kaplama cikabilirdi.
    """
    cols, kapsanan, kanit = exact_max_coverage(
        enc.alphabet_sizes, budget,
        *( (time_limit,) if time_limit is not None else () ))
    if cols is None:
        g = greedy_full(list(enc.variable_space()), enc.alphabet_sizes,
                        random.Random(seed))
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
        raise ButceSigmazHatasi(
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
