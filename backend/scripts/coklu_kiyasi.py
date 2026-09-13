"""Çoklu kupon ↔ tek sistem kıyası, 114 tam haftada.

Tek soru: **aynı bütçe birden çok kupona bölünürse `P(15/15)` ne oluyor?**

Kıyas ikisini de aynı olasılık modeliyle, aynı kolon bütçesiyle koşar; tek
değişen kuponun şeklidir. Alt kademeler de sayılır — çoklu kupon 15'i
enbüyükler ve bunun 12–13'te bir bedeli olup olmadığı ölçülmeden
bilinmemelidir.

    cd backend && python scripts/coklu_kiyasi.py
    cd backend && python scripts/coklu_kiyasi.py --butce 19683 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from spor_toto.coklu import coklu_plan_serisi, kademe_dagilimi
from spor_toto.core import SEMBOLLER

#: Kıyaslanan kupon tavanları. 1 bugünkü tek sistemdir.
TAVANLAR = (1, 3, 9, 27, 81, 243, 729)

#: Varsayılan bütçe (kolon). 19.683 = 3⁹, tek sistemin bu banttaki bedeli;
#: kıyasın adil olması için ikisi de aynı kolon sayısını harcar.
VARSAYILAN_BUTCE = 3 ** 9


def hafta_probs(lst: list) -> tuple[list[dict[str, float]], list[str]]:
    """Bir haftanın maç olasılıkları ve gerçekleşen sembolleri."""
    probs = [{s: float(b["probs"][s]) for s in SEMBOLLER} for b, _ in lst]
    gercek = [c for _, c in lst]
    return probs, gercek


def isabet(kuponlar, gercek: list[str]) -> bool:
    """Gerçek kolon oynananların içinde mi — 15/15 tuttu mu."""
    return any(all(gercek[i] in sec for i, sec in enumerate(k.secimler))
               for k in kuponlar)


def kos(butce: int) -> dict:
    ars = ikramiye_tablolari()
    haftalar = tam_haftalar(ars)
    n = len(haftalar)

    # Tip açıkça yazılıyor: `kademe` bir sözlük, ötekiler sayı — çıkarım
    # ortak üst tip olarak `object` buluyor ve aşağıdaki her toplama mypy'da
    # düşüyordu.
    top: dict[int, dict[str, Any]] = {
        t: {"p": 0.0, "isabet": 0, "kolon": 0, "kupon": 0,
            "kademe": {12: 0, 13: 0, 14: 0, 15: 0}} for t in TAVANLAR}

    for _sezon, _w, lst in haftalar:
        probs, gercek = hafta_probs(lst)
        # tek geçiş: `coklu_plan`ı tavan tavan çağırmak aramayı yedi kez
        # baştan yapardı (bkz. `coklu.coklu_plan_serisi`).
        seri = coklu_plan_serisi(probs, butce, TAVANLAR)
        for t in TAVANLAR:
            plan = seri[t]
            h = top[t]
            h["p"] += plan.p_onbes
            h["isabet"] += int(isabet(plan.kuponlar, gercek))
            h["kolon"] += plan.kolon
            h["kupon"] += plan.kupon_sayisi
            for kademe, adet in kademe_dagilimi(probs, plan.kuponlar,
                                                gercek).items():
                if kademe in h["kademe"]:
                    h["kademe"][kademe] += adet

    return {"hafta": n, "butce": butce,
            "satirlar": [{
                "tavan": t,
                "kupon_ort": top[t]["kupon"] / n,
                "kolon_ort": top[t]["kolon"] / n,
                "p_model": top[t]["p"] / n,
                "isabet": top[t]["isabet"],
                "p_13hafta": 1 - (1 - top[t]["p"] / n) ** 13,
                "kademe": top[t]["kademe"],
            } for t in TAVANLAR]}


def bas(c: dict) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon "
          f"({c['butce'] * 10:,} TL/hafta)\n")
    # `tavan` sütunu bilerek var: `kupon_ort` yuvarlanıyor ve küçük
    # bütçelerde iki farklı tavan aynı ortalamaya düşüyor (3.888 kolonda
    # tavan 1 ile 3 ikisi de "1 kupon" yazıyordu ve tablo aynı satırı iki
    # kez basmış gibi görünüyordu — oysa 12+ kolonları farklıydı).
    print(f"{'tavan':>6} {'kupon':>8} {'kolon':>9} {'model P(15)':>13} "
          f"{'gozlenen':>11} {'13 hafta':>10} {'12+ kolon':>11}")
    taban = None
    for r in c["satirlar"]:
        alt = sum(r["kademe"].values())
        if taban is None:
            taban = r["p_model"]
        not_ = "  <- bugun" if r["tavan"] == 1 else ""
        print(f"{r['tavan']:>6,} {r['kupon_ort']:>8,.0f} "
              f"{r['kolon_ort']:>9,.0f} "
              f"{r['p_model']:>12.3%} {r['isabet']:>6}/{c['hafta']:<4} "
              f"{r['p_13hafta']:>9.1%} {alt:>11,}{not_}")
    en = c["satirlar"][-1]
    print(f"\nkazanc (tavan {en['tavan']} / tek sistem): "
          f"model x{en['p_model'] / taban:.2f}   "
          f"gozlenen {en['isabet']} - {c['satirlar'][0]['isabet']}")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    c = kos(a.butce)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
    else:
        bas(c)


if __name__ == "__main__":
    main()
