"""
Spor Toto kapsama (covering code) cekirdegi.

Temel fikir
-----------
Kupon 15 mactan olusur. Her mac icin bir veya birden fazla sembol
secilebilir: '1' (ev sahibi), '0' (beraberlik), '2' (deplasman).
Tek sembollu maclar "banko", cok sembollu maclar "degisken"dir.

14-garanti: secilen ihtimal kumeleri icinde dogru sonuc varsa, oynanan
kolonlardan en az biri en fazla 1 mac hatali olacaktir. Bu, degisken
maclarin olusturdugu Hamming uzayinda yaricapi 1 olan bir KAPLAMA KODU
(covering code) problemidir.

Toplam hata butcesi 1 oldugu icin yalnizca TEK bir alt kume r=1 olabilir;
geri kalan tum maclar zorunlu olarak tam sistemdir (r=0). Iki r=1 blogu
birlestirilirse yaricap 2 olur ve garanti kirilir.
"""

from __future__ import annotations

import heapq
import time as _time
import math
import random
from collections import Counter
from itertools import product
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "SEMBOLLER", "Point", "Sizes", "Row",
    "Encoder", "parse_picks", "parse_probs", "dogrula_secimler",
    "hamming", "ball", "distance_layers", "dogrula_kaplama",
    "hamming74_codewords", "solve_fix16", "solve_by_blocks",
    "solve_heuristic", "greedy_full", "ls_fixed_size",
    "exact_cover", "exact_max_coverage",
    "merge_rows", "row_cost", "sirala_semboller",
    "olasilik_raporu", "butce_danismani", "ButcePlani", "OlasilikRaporu",
    "HAS_SCIPY",
]

SEMBOLLER: Tuple[str, str, str] = ("1", "0", "2")
_SEMBOL_INDEX: Dict[str, int] = {s: i for i, s in enumerate(SEMBOLLER)}

MAC_SAYISI = 15
HAMMING_BLOK_BOYU = 7
HAMMING_KOLON = 16

Point = Tuple[int, ...]
Sizes = Tuple[int, ...]
Row = Tuple[FrozenSet[int], ...]

try:
    import numpy as _np
    from scipy.optimize import milp as _milp, LinearConstraint as _LC, Bounds as _Bounds
    from scipy.sparse import lil_matrix as _lil, hstack as _hstack, identity as _ident
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def sirala_semboller(syms: Iterable[str]) -> List[str]:
    syms = list(syms)
    for s in syms:
        if s not in _SEMBOL_INDEX:
            raise ValueError(
                f"gecersiz sembol {s!r}. Gecerli semboller: "
                f"{'/'.join(SEMBOLLER)}")
    return sorted(syms, key=lambda x: _SEMBOL_INDEX[x])


def dogrula_secimler(selections: Sequence[Sequence[str]], kati: bool = False) -> List[str]:
    uyarilar: List[str] = []
    if not selections:
        raise ValueError("Secim listesi bos.")
    if len(selections) != MAC_SAYISI:
        msg = (f"Spor Toto {MAC_SAYISI} mactan olusur, "
               f"{len(selections)} mac girildi.")
        if kati:
            raise ValueError(msg)
        uyarilar.append(msg)

    for i, s in enumerate(selections, 1):
        if len(s) == 0:
            raise ValueError(f"{i}. mac icin hic secenek girilmemis.")
        if len(s) != len(set(s)):
            raise ValueError(
                f"{i}. macta tekrar eden sembol var: {''.join(s)}")
        if len(s) > len(SEMBOLLER):
            raise ValueError(
                f"{i}. macta {len(SEMBOLLER)}'ten fazla secenek var: {''.join(s)}")
        for sym in s:
            if sym not in _SEMBOL_INDEX:
                raise ValueError(
                    f"{i}. macta gecersiz sembol {sym!r}. "
                    f"Gecerli semboller: {'/'.join(SEMBOLLER)}")
    return uyarilar


def parse_picks(text: str) -> List[List[str]]:
    """
    '1,10,1,12,0,...' -> [['1'], ['1','0'], ['1'], ['1','2'], ['0'], ...]
    Ayirici olarak virgul, bosluk, noktali virgul veya '/' kabul edilir.

    Bos slot (ornegin '1,,10' veya '1, ,2') ValueError firlatir; sessizce
    atlanmaz. Boylece mac sayisi kaymasi engellenir.
    """
    if not text or not text.strip():
        raise ValueError("--picks bos olamaz.")
    tmp = text.strip()
    for ch in (";", "/", "|", "\n", "\t"):
        tmp = tmp.replace(ch, ",")
    if "," not in tmp:
        parts = [p for p in tmp.split() if p]
        if not parts:
            raise ValueError(f"--picks ayristirilamadi: {text!r}")
        return [sirala_semboller(p) for p in parts]

    raw_parts = tmp.split(",")
    parts: List[str] = []
    for idx, p in enumerate(raw_parts):
        s = p.strip()
        if not s:
            if idx == 0 or idx == len(raw_parts) - 1:
                continue
            raise ValueError(
                f"--picks icinde bos mac slotu var (konum {idx + 1}). "
                f"Ornek hatali girdi: '1,,10' — her mac en az bir sembol "
                f"icermelidir (1/0/2)."
            )
        parts.append(s)
    if not parts:
        raise ValueError(f"--picks ayristirilamadi: {text!r}")
    return [sirala_semboller(p) for p in parts]


def parse_probs(text: str, selections: Sequence[Sequence[str]]) -> List[Dict[str, float]]:
    bloklar = [b.strip() for b in text.split(";") if b.strip()]
    if len(bloklar) != len(selections):
        raise ValueError(
            f"--probs {len(bloklar)} mac icerdi, {len(selections)} mac bekleniyordu.")
    out: List[Dict[str, float]] = []
    for i, blok in enumerate(bloklar, 1):
        p: Dict[str, float] = {s: 0.0 for s in SEMBOLLER}
        for parca in blok.split(","):
            parca = parca.strip()
            if not parca:
                continue
            if ":" not in parca:
                raise ValueError(
                    f"{i}. macta gecersiz olasilik parcasi {parca!r}; "
                    f"beklenen bicim '1:0.5'.")
            sym, deger = parca.split(":", 1)
            sym = sym.strip()
            if sym not in _SEMBOL_INDEX:
                raise ValueError(f"{i}. macta gecersiz sembol {sym!r}.")
            try:
                val = float(deger)
            except ValueError:
                raise ValueError(f"{i}. macta sayiya cevrilemedi: {deger!r}.")
            if val < 0:
                raise ValueError(f"{i}. macta negatif olasilik: {val}.")
            p[sym] = val
        toplam = sum(p.values())
        if toplam <= 0:
            raise ValueError(f"{i}. macta tum olasiliklar sifir.")
        out.append({s: v / toplam for s, v in p.items()})
    return out
