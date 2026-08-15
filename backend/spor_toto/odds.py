"""Oran arşivi okuyucu — analiz katmanı için, arayüz için değil.

Bu modül hiçbir API ucuna, sayfaya ya da motor akışına bağlı DEĞİLDİR.
``scripts/build_odds.py`` ile üretilen arşivi ileride yapılacak analizin
kolayca okuyabilmesi için durur.

    from spor_toto.odds import load_odds, market_odds
    rows = load_odds()                       # maç başına tek satır
    p = market_odds(rows[0], "1X2", "Avg")   # {"1": 7.03, "0": 4.67, "2": 1.39}

Kaynak: football-data.co.uk piyasa oranları — **iddaa oranları değildir**
(gerekçe: docs/VERI_TOPLAMA_VE_ISLEME.md §12).
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

ODDS_FILE = Path(__file__).resolve().parent.parent / "data" / "odds" / "odds_2025_26.csv"

KIMLIK_ALANLARI = {
    "week", "no", "kickoff", "home", "away", "hg", "ag", "code",
    "kaynak_dosya", "kaynak_lig", "kaynak_ev", "kaynak_dep", "guven",
}

_SAYI = re.compile(r"^-?\d+(\.\d+)?$")


def _sayi(ham: str) -> Optional[float]:
    ham = (ham or "").strip()
    return float(ham) if _SAYI.match(ham) else None


@lru_cache(maxsize=1)
def load_odds(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Arşivi satır satır okur. Dosya yoksa boş liste döner (hata değil)."""
    yol = Path(path) if path else ODDS_FILE
    if not yol.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(yol, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            oranlar = {
                k: v for k, v in r.items()
                if k not in KIMLIK_ALANLARI and not k.startswith("stat_")
                and _sayi(v) is not None
            }
            out.append({
                "week": int(r["week"]),
                "no": int(r["no"]),
                "kickoff": r["kickoff"],
                "home": r["home"],
                "away": r["away"],
                "hg": int(r["hg"]) if r["hg"] else None,
                "ag": int(r["ag"]) if r["ag"] else None,
                "code": r["code"],
                "matched": bool(r["kaynak_dosya"]),
                "confidence": _sayi(r["guven"]) or 0.0,
                "source": {"file": r["kaynak_dosya"], "league": r["kaynak_lig"],
                           "home": r["kaynak_ev"], "away": r["kaynak_dep"]},
                "odds": {k: float(v) for k, v in oranlar.items()},
                "stats": {k[5:]: float(v) for k, v in r.items()
                          if k.startswith("stat_") and _sayi(v) is not None},
            })
    return out


def odds_for(week: int, no: int) -> Optional[Dict[str, Any]]:
    for r in load_odds():
        if r["week"] == week and r["no"] == no:
            return r
    return None


def market_odds(row: Dict[str, Any], market: str = "1X2", book: str = "Avg",
                closing: bool = True) -> Dict[str, float]:
    """Bir maçın tek pazarını sembol anahtarlı sözlüğe indirger.

    market: "1X2" | "2.5" | "AH"  ·  book: "Avg", "Max", "B365", "PS", …
    """
    ek = "C" if closing else ""
    if market == "1X2":
        harf = {"1": "H", "0": "D", "2": "A"}
        return {s: row["odds"][f"{book}{ek}{h}"]
                for s, h in harf.items() if f"{book}{ek}{h}" in row["odds"]}
    if market == "2.5":
        return {ad: row["odds"][f"{book}{ek}{sim}2.5"]
                for ad, sim in (("ust", ">"), ("alt", "<"))
                if f"{book}{ek}{sim}2.5" in row["odds"]}
    if market == "AH":
        return {s: row["odds"][f"{book}{ek}AH{h}"]
                for s, h in (("1", "H"), ("2", "A"))
                if f"{book}{ek}AH{h}" in row["odds"]}
    return {}


def implied_probs(oranlar: Dict[str, float]) -> Dict[str, float]:
    """Marjı (overround) atarak oranları 1'e normalize edilmiş olasılığa çevirir."""
    ters = {k: 1.0 / v for k, v in oranlar.items() if v and v > 0}
    toplam = sum(ters.values())
    if toplam <= 0:
        return {}
    return {k: v / toplam for k, v in ters.items()}


def coverage() -> Dict[str, Any]:
    rows = load_odds()
    eslesen = [r for r in rows if r["matched"]]
    return {
        "matches": len(rows),
        "matched": len(eslesen),
        "pct": round(100 * len(eslesen) / len(rows), 2) if rows else 0.0,
        "odds_values": sum(len(r["odds"]) for r in eslesen),
    }
