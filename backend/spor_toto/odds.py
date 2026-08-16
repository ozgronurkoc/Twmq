"""Oran arşivi okuyucu — analiz katmanı için, arayüz için değil.

Bu modül hiçbir API ucuna, sayfaya ya da motor akışına bağlı DEĞİLDİR.
``scripts/build_odds.py`` ile üretilen arşivi ileride yapılacak analizin
kolayca okuyabilmesi için durur.

    from spor_toto.odds import load_odds, market_odds
    rows = load_odds()                       # maç başına tek satır
    p = market_odds(rows[0], "1X2", "Avg")   # {"1": 7.03, "0": 4.67, "2": 1.39}

Kaynak: football-data.co.uk piyasa oranları — **iddaa oranları değildir**
(gerekçe: docs/VERI_TOPLAMA_VE_ISLEME.md §3.2).
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


# ─── maç sonucu (1X2) — arayüze giden tek pazar ───────────────────────────────

SEMBOLLER = ("1", "0", "2")
#: Tercih sırası: piyasa ortalaması, sonra tek tek bahisçiler.
KAYNAK_SIRASI = ("Avg", "B365", "PS", "BFE", "Max")


def match_1x2(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Bir maçın maç sonucu oranı: önce kapanış, yoksa açılış.

    Hangi kaynaktan ve hangi dönemden geldiği çıktıda yazar — sayının
    nereden geldiği belirsiz kalmamalı.
    """
    if not row.get("matched"):
        return None
    for kapanis in (True, False):
        for kaynak in KAYNAK_SIRASI:
            oranlar = market_odds(row, "1X2", kaynak, closing=kapanis)
            if len(oranlar) != 3 or any(v <= 1.0 for v in oranlar.values()):
                continue
            olasilik = implied_probs(oranlar)
            favori = min(oranlar, key=lambda s: oranlar[s])
            return {
                "odds": {s: round(oranlar[s], 2) for s in SEMBOLLER},
                "probs": {s: round(olasilik[s], 4) for s in SEMBOLLER},
                "favourite": favori,
                "hit": favori == row["code"],
                "margin": round(sum(1 / v for v in oranlar.values()) - 1, 4),
                "book": kaynak,
                "closing": kapanis,
            }
    return None


def week_1x2(week: int) -> Dict[int, Dict[str, Any]]:
    """Bir haftanın maç numarasına göre 1X2 blokları (oranı olmayanlar yok)."""
    out: Dict[int, Dict[str, Any]] = {}
    for r in load_odds():
        if r["week"] != week:
            continue
        blok = match_1x2(r)
        if blok:
            out[r["no"]] = blok
    return out


#: Banko kararı için favori oranı bantları (alt dahil, üst hariç).
FAVORI_BANTLARI = ((1.0, 1.20), (1.20, 1.35), (1.35, 1.50),
                   (1.50, 1.75), (1.75, 2.00), (2.00, 99.0))


def _favori_bantlari(oranli: List[Any]) -> List[Dict[str, Any]]:
    """Favorinin oranına göre: kaç maçta tuttu, kaçında tutmadı.

    ``tutmadı`` iki parçaya ayrılır — beraberlik ve karşı tarafın kazanması —
    çünkü banko kararında bunlar farklı riskler: beraberlik her maçta masada,
    karşı tarafın kazanması ise favorinin gerçekten yanılmasıdır.
    """
    out: List[Dict[str, Any]] = []
    for lo, hi in FAVORI_BANTLARI:
        grup = [(r, b) for r, b in oranli if lo <= min(b["odds"].values()) < hi]
        n = len(grup)
        if not n:
            continue
        tuttu = sum(1 for r, b in grup if b["hit"])
        beraberlik = sum(1 for r, _ in grup if r["code"] == "0")
        tutmadi = n - tuttu
        out.append({
            "lo": lo,
            "hi": hi if hi < 99 else None,
            "label": f"{lo:.2f}–{hi:.2f}" if hi < 99 else f"{lo:.2f} ve üstü",
            "n": n,
            "hit": tuttu,
            "miss": tutmadi,
            "draw": beraberlik,
            "upset": tutmadi - beraberlik,
            "hit_pct": round(100 * tuttu / n, 1),
            "miss_pct": round(100 * tutmadi / n, 1),
            "draw_pct": round(100 * beraberlik / n, 1),
            "upset_pct": round(100 * (tutmadi - beraberlik) / n, 1),
        })
    return out


def season_1x2_summary(weeks: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
    """Dilim için oran özeti: kapsama, favori isabeti, marj ve kalibrasyon.

    ``weeks`` verilirse yalnızca o haftalar sayılır — arayüzdeki aralık
    filtresi böylece oran kartını da kapsar.
    """
    rows = load_odds()
    if not rows:
        return None
    izin = set(weeks) if weeks is not None else None
    ilgili = [r for r in rows if izin is None or r["week"] in izin]
    if not ilgili:
        return None

    bloklar = [(r, match_1x2(r)) for r in ilgili]
    oranli = [(r, b) for r, b in bloklar if b]
    if not oranli:
        return None

    tutan = sum(1 for _, b in oranli if b["hit"])
    fav_dagilim = {s: sum(1 for _, b in oranli if b["favourite"] == s) for s in SEMBOLLER}

    # Favori tuttuğunda / tutmadığında ne gerçekleşti.
    # "0" tuttu sütunu her zaman 0'dır: beraberlik hiçbir maçta favori olmaz,
    # bu yüzden HER beraberlik tanımı gereği "tutmadı" tarafına düşer.
    tuttu_sonuc = {
        s: sum(1 for r, b in oranli if b["hit"] and r["code"] == s) for s in SEMBOLLER
    }
    tutmadi_sonuc = {
        s: sum(1 for r, b in oranli if not b["hit"] and r["code"] == s) for s in SEMBOLLER
    }
    # Favori (satır) × gerçekleşen (sütun) çapraz tablosu.
    capraz = {
        f: {s: sum(1 for r, b in oranli if b["favourite"] == f and r["code"] == s)
            for s in SEMBOLLER}
        for f in SEMBOLLER
    }
    # Gerçek sürpriz: favorinin KARŞI tarafı kazandı (beraberlik değil).
    underdog = sum(
        capraz[f][s] for f in SEMBOLLER for s in SEMBOLLER
        if f != s and s != "0"
    )

    bantlar = _favori_bantlari(oranli)

    # Kalibrasyon: modelin verdiği olasılık ile gerçekleşme yan yana.
    kovalar: Dict[int, Dict[str, float]] = {}
    for r, b in oranli:
        for s in SEMBOLLER:
            p = b["probs"][s]
            k = min(int(p * 10), 9)
            hucre = kovalar.setdefault(k, {"n": 0, "model": 0.0, "gercek": 0})
            hucre["n"] += 1
            hucre["model"] += p
            hucre["gercek"] += 1 if s == r["code"] else 0
    kalibrasyon = [
        {
            "lo": k * 10,
            "hi": k * 10 + 10,
            "n": int(v["n"]),
            "model_pct": round(100 * v["model"] / v["n"], 1),
            "actual_pct": round(100 * v["gercek"] / v["n"], 1),
        }
        for k, v in sorted(kovalar.items()) if v["n"] >= 10
    ]

    return {
        "matches": len(ilgili),
        "with_odds": len(oranli),
        "coverage_pct": round(100 * len(oranli) / len(ilgili), 1),
        "favourite_hit": tutan,
        "favourite_miss": len(oranli) - tutan,
        "favourite_hit_pct": round(100 * tutan / len(oranli), 1),
        "favourite_split": fav_dagilim,
        "outcome_when_hit": tuttu_sonuc,
        "outcome_when_miss": tutmadi_sonuc,
        "cross": capraz,
        "underdog_wins": underdog,
        "favourite_bands": bantlar,
        "outcome_totals": {
            s: tuttu_sonuc[s] + tutmadi_sonuc[s] for s in SEMBOLLER
        },
        "avg_margin_pct": round(
            100 * sum(b["margin"] for _, b in oranli) / len(oranli), 2
        ),
        "calibration": kalibrasyon,
        "books": sorted({b["book"] for _, b in oranli}),
        "note": "piyasa kapanış oranları (football-data.co.uk) — iddaa oranı değildir",
    }


def coverage() -> Dict[str, Any]:
    rows = load_odds()
    eslesen = [r for r in rows if r["matched"]]
    return {
        "matches": len(rows),
        "matched": len(eslesen),
        "pct": round(100 * len(eslesen) / len(rows), 2) if rows else 0.0,
        "odds_values": sum(len(r["odds"]) for r in eslesen),
    }
