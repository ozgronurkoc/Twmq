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
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.core import SEMBOLLER

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
SEM = SEMBOLLER
CIKTI = KOK.parent / "frontend" / "lib" / "super-toto-veri.json"


def _modul(ad: str):
    """Kardes betigi getirir — artik sıradan bir import.

    Once `spec_from_file_location` ile dosya yolundan yukleniyordu ve
    yuklerken `sys.argv`yi geciciyle degistiriyordu. Ikisi de gereksizdi:
    bu dizin bir paket (`scripts/__init__.py`) ve hedef betiklerin hepsinde
    `if __name__ == "__main__"` guard'i var, yani import etmek argparse'i
    tetiklemiyor.
    """
    return importlib.import_module(f"scripts.super_toto_{ad}")


def _yuvarla(p: dict[str, float]) -> dict[str, float]:
    return {s: round(p[s], 4) for s in SEM}


def _donmus_blok(donmus: dict[str, Any] | None) -> dict[str, Any] | None:
    """Dondurulmuş kupon dosyasından arayüzün okuyacağı kayıt.

    Ana varyant (`variants[0]`) alınır; kupon dosyası birden çok bütçe
    sürümü taşıyabilir ama sayfada gösterilecek olan kuralın kendisidir.
    """
    if not donmus:
        return None
    v = donmus["variants"][0]
    st = donmus["meta"].get("strategy") or {}
    return {
        "picks": v["picks"],
        "label": v.get("label"),
        "columns": v.get("columns"), "rows": v.get("rows"),
        "in_set_p": v.get("in_set_p"),
        "banko_esik": st.get("banko_esik"),
        "uclu_esik": st.get("uclu_esik"),
        # Hangi olcekte donduruldugu — bu alan olmadan isaretler
        # yorumlanamaz (bkz. strategy.arindirma_notu).
        "arindirma": st.get("arindirma"),
        "marj_ort_pct": st.get("marj_ort_pct"),
        "frozen_at": donmus["meta"].get("frozen_at"),
        "results_known": donmus["meta"].get("results_known"),
    }


def uret(sezon: str = "2026_27") -> dict[str, Any]:
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU
    from spor_toto.odds import ARINDIRMA_VARSAYILAN

    hafta_mod = _modul("hafta")
    sezon_mod = _modul("sezon")

    haftalar: list[dict[str, Any]] = []
    for no in sezon_mod.haftalari_bul(sezon):
        d = hafta_mod.hafta_yukle(sezon, no)
        meta = d["meta"]
        # DONDURULMUS kupon KAYITTIR ve yeniden hesaplanmaz. Bu satirin
        # onemi buyuk: 2026-08'de marj arindirma varsayilani degisti ve ayni
        # esik baska isaretler uretiyor (1. haftada 12. mac uclu → cift,
        # 2. haftada 1. mac cift → banko). Yeniden hesaplanan bir kuponu
        # sayfada gostermek, sonuclar gorulmeden donduruldugunu soyleyen
        # kaydin ustune sonradan yazmak olurdu — projenin en degerli
        # aliskanligi tam olarak budur.
        kupon_yolu = (KOK / "data" / "super_toto" / sezon
                      / f"hafta_{no:02d}_kupon.json")
        donmus = (json.loads(kupon_yolu.read_text(encoding="utf-8"))
                  if kupon_yolu.exists() else None)
        # Bugunku kural ne uretirdi — AYRI alan, ayri etiket. Karsilastirma
        # bilgi tasir; kaydin yerine gecemez.
        bugun = hafta_mod.kupon_kur(d, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
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
            "coupon": _donmus_blok(donmus),
            # Revizyon kaydi: girdi degistigi icin (orn. sonradan ilan edilen
            # oran) kupon yeniden kuruldusa, ONCEKI surum de gorunur kalir.
            # Gorunmeyen bir revizyon, revizyon olmayan bir kayittan daha
            # kotudur — degistigi belli olmaz.
            "coupon_superseded": (
                {"reason": donmus["superseded"].get("reason"),
                 "revised_at": donmus["superseded"].get("revised_at"),
                 "arindirma": donmus["superseded"].get("arindirma"),
                 "picks": donmus["superseded"]["variants"][0]["picks"]}
                if donmus and donmus.get("superseded") else None),
            "coupon_today": {
                "picks": bugun["picks"],
                "banko": bugun["banko"], "cift": bugun["cift"],
                "uclu": bugun["uclu"],
                "columns": bugun["columns"], "rows": bugun["rows"],
                "in_set_p": round(bugun["in_set_p"], 6),
                "banko_esik": bugun["banko_esik"],
                "uclu_esik": bugun["uclu_esik"],
                "arindirma": ARINDIRMA_VARSAYILAN,
            },
            # Kural ayni, olcek farkli: hangi maclarda isaret degisti.
            "coupon_drift": (
                [i + 1 for i, (a, b) in enumerate(
                    zip(donmus["variants"][0]["picks"], bugun["picks"]))
                 if a != b]
                if donmus else None),
        })

    return {
        "season": "2026/2027",
        "season_key": sezon,
        "arindirma": ARINDIRMA_VARSAYILAN,
        "note": ("backend/data/super_toto altindan uretildi — elle "
                 "duzenlenmez; scripts/super_toto_frontend.py"),
        "weeks": haftalar,
    }


def _metin(govde: dict[str, Any]) -> str:
    return json.dumps(govde, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> None:
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
