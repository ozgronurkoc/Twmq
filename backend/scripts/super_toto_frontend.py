#!/usr/bin/env python3
"""Arayüzün okuduğu sezon beslemesini üretir.

Sorun: `frontend/lib/super-toto.ts` sezonun 41 haftasını **elle** tutuyordu ve
hepsi boştu. Backend'de 1. ve 2. haftanın verisi dururken sayfa "verisi henüz
girilmedi" diyordu — iki taraf birbirinden habersizdi.

Bu script tek yönlü bağı kurar: backend verisi kaynaktır, arayüz onu okur.

    python scripts/super_toto_frontend.py            # yazar
    python scripts/super_toto_frontend.py --kontrol  # yalnizca denetler (CI)

`--kontrol` üretilecek içerikle dosyadakini karşılaştırır ve farklıysa sıfırdan
farklı kodla çıkar. Böylece hafta verisi girilip besleme yenilenmediğinde CI
kırılır — sessizce eskimiş bir arayüz, boş bir arayüzden daha kötüdür çünkü
yanlış olduğu belli olmaz.

**Neden statik dosya, neden API değil.** Geçmiş hafta kapanmış bir kayıttır:
sonuç değişmez, oran değişmez. Değişmeyen bir şey için istek başına hesap
yapmanın karşılığı yok. Yaklaşan haftanın canlı verisi (henüz oynanmamış maçın
oranı) bir gün gerekirse, o zaman ayrı bir uç nokta açılır — bu dosya
kapanmış haftaların kaydıdır.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

SEM = ("1", "0", "2")
CIKTI = KOK.parent / "frontend" / "lib" / "super-toto-veri.json"


def _modul(ad: str):
    spec = importlib.util.spec_from_file_location(
        f"st_{ad}", str(KOK / "scripts" / f"super_toto_{ad}.py"))
    mod = importlib.util.module_from_spec(spec)
    eski = sys.argv
    sys.argv = ["x"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = eski
    return mod


def _yuvarla(p: Dict[str, float]) -> Dict[str, float]:
    return {s: round(p[s], 4) for s in SEM}


def uret(sezon: str = "2026_27") -> Dict[str, Any]:
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU
    from spor_toto.odds import ARINDIRMA_VARSAYILAN

    hafta_mod = _modul("hafta")
    sezon_mod = _modul("sezon")

    haftalar: List[Dict[str, Any]] = []
    for no in sezon_mod.haftalari_bul(sezon):
        d = hafta_mod.hafta_yukle(sezon, no)
        meta = d["meta"]
        kupon = hafta_mod.kupon_kur(d, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
        haftalar.append({
            "week": no,
            "program": meta.get("program"),
            "close_date": min((m["date"] for m in d["matches"] if m.get("date")),
                              default=None),
            "results": meta.get("results"),
            "odds_source": meta.get("odds_source"),
            "odds_kind": meta.get("odds_kind"),
            "play_source": meta.get("play_source"),
            # Iki uyari listesi AYRI tasinir: biri insanin notu, digeri
            # kapinin urettigi. Arayuz de ikisini ayri gostermeli.
            "warnings_manual": meta.get("data_warnings") or [],
            "warnings_generated": meta.get("uretilen_uyarilar") or [],
            "matches": [{
                "no": m["no"], "date": m.get("date"), "kickoff": m.get("kickoff"),
                "league": m["league"], "home": m["home"], "away": m["away"],
                "odds": m["odds"], "odds_missing": m["odds_yok"],
                "probs": _yuvarla(m["probs"]), "fav": m["fav"],
                "margin": round(m["margin"], 4),
                "play": _yuvarla(m["play"]),
                "result": (meta["results"][m["no"] - 1]
                           if meta.get("results") else None),
            } for m in d["matches"]],
            "coupon": {
                "picks": kupon["picks"],
                "banko": kupon["banko"], "cift": kupon["cift"],
                "uclu": kupon["uclu"],
                "columns": kupon["columns"], "rows": kupon["rows"],
                "in_set_p": round(kupon["in_set_p"], 6),
                "banko_esik": kupon["banko_esik"],
                "uclu_esik": kupon["uclu_esik"],
            },
        })

    return {
        "season": "2026/2027",
        "season_key": sezon,
        "arindirma": ARINDIRMA_VARSAYILAN,
        "note": ("backend/data/super_toto altindan uretildi — elle "
                 "duzenlenmez; scripts/super_toto_frontend.py"),
        "weeks": haftalar,
    }


def _metin(govde: Dict[str, Any]) -> str:
    return json.dumps(govde, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--kontrol", action="store_true",
                    help="yazma, yalnizca dosyanin guncel olup olmadigina bak")
    ap.add_argument("--cikti", default=None)
    a = ap.parse_args(argv)

    yol = Path(a.cikti) if a.cikti else CIKTI
    metin = _metin(uret(a.sezon))

    if a.kontrol:
        mevcut = yol.read_text(encoding="utf-8") if yol.exists() else ""
        if mevcut != metin:
            raise SystemExit(
                f"{yol} guncel degil. Cozum:\n"
                f"  python scripts/super_toto_frontend.py")
        print(f"{yol.name} guncel")
        return

    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(metin, encoding="utf-8")
    print(f"{yol} yazildi ({len(json.loads(metin)['weeks'])} hafta)")


if __name__ == "__main__":
    main()
