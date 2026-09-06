#!/usr/bin/env python3
"""Bütçe kademeleri — "daha küçük bütçeyle oynasaydık ne olurdu?"

Bir haftanın işaretleri bütçeye **koşulludur**: `secim.en_iyi_secim` tavanın
altına sığan bütün tek/çift/üçlü dağılımlarını tarayıp `P(k ≤ 2)`'yi
enbüyükler, tavan değişince cevap da değişir. Kupon kayıtlarındaki
"864 kolon → %X · 1.296 kolon → %Y" satırları bu betiğin çıktısıdır.

**Neden ayrı bir betik.** 4. haftanın kaydında iki kademe varyantı
*"motorun kendi planı"* diye etiketliydi ve değildi: ana plandan işaret
düşürülerek üretilmişlerdi ve motorun aynı tavandaki gerçek cevabından
1,31 ve 1,43 puan **geride**ydiler. Kısma ile yeniden en iyileme aynı şey
değildir; elle kısılan bir plan motorun planı diye kaydedilirse "bütçeyi
düşürsek ne kaybederiz" sorusu olduğundan kötü cevaplanır. Bu betik o
sayının elle üretilmesini gereksiz kılar.

Sonuç kullanılmaz: yalnızca oran dosyası okunur.

    python scripts/butce_kademeleri.py --hafta 4
    python scripts/butce_kademeleri.py --hafta 4 --tavan 1024
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.odds import ARINDIRMA_VARSAYILAN, implied_probs
from spor_toto.secim import VARSAYILAN_KACAK_ESIGI, en_iyi_secim

#: Varsayılan kademe ızgarası. Değerler `bedel_hesapla`nın gerçekten
#: ürettiği bedellerdir (2^a·3^b/2⁷·16), yani her biri satın alınabilir bir
#: nokta; ızgara düz bir aralık olsaydı çoğu tavan aynı plana çıkardı.
KADEMELER: tuple[int, ...] = (256, 512, 864, 1296, 2304, 3888, 6144, 10368)

SEZON = "2026_27"


def hafta_olasiliklari(hafta: int, sezon: str = SEZON,
                       yontem: str = ARINDIRMA_VARSAYILAN
                       ) -> list[dict[str, float]]:
    """Haftanın ana fiyatından marj arındırılmış olasılıklar."""
    yol = KOK / "data" / "super_toto" / sezon / f"hafta_{hafta:02d}.json"
    d = json.loads(yol.read_text(encoding="utf-8"))
    return [implied_probs(m["odds"], yontem) for m in d["matches"]]


def dondurulmus_plan(hafta: int, sezon: str = SEZON) -> list[str] | None:
    """Kupon kaydındaki ana varyantın işaretleri — kıyas için, yoksa `None`."""
    yol = KOK / "data" / "super_toto" / sezon / f"hafta_{hafta:02d}_kupon.json"
    if not yol.exists():
        return None
    d = json.loads(yol.read_text(encoding="utf-8"))
    return list(d["variants"][0]["picks"])


def kademe(probs: list[dict[str, float]], tavan: int,
           esik: int = VARSAYILAN_KACAK_ESIGI) -> dict[str, Any] | None:
    """Bir tavandaki plan — motorun kendi cevabı, kısma değil."""
    a = en_iyi_secim(probs, tavan, esik)
    if a is None:
        return None
    return {"tavan": tavan, "picks": a.picks, "bedel": a.bedel,
            "hedef": a.p_hedef, "sekil": (a.banko, a.cift, a.uclu)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hafta", type=int, required=True)
    ap.add_argument("--sezon", default=SEZON)
    ap.add_argument("--tavan", type=int, default=None,
                    help="tek bir tavan; verilmezse bütün kademeler")
    ap.add_argument("--esik", type=int, default=VARSAYILAN_KACAK_ESIGI,
                    help="kaçak eşiği (14-garanti=2, 13=1, 12=0)")
    a = ap.parse_args()

    probs = hafta_olasiliklari(a.hafta, a.sezon)
    ana = dondurulmus_plan(a.hafta, a.sezon)
    tavanlar = (a.tavan,) if a.tavan else KADEMELER

    print(f"\n{a.sezon} · {a.hafta}. hafta · kaçak eşiği k≤{a.esik}"
          + ("  (kıyas: dondurulmuş ana varyant)" if ana else ""))
    print(f'{"tavan":>8}{"şekil":>9}{"bedel":>8}{"P(k≤" + str(a.esik) + ")":>10}'
          + ("  ana plandan farklı maç" if ana else ""))
    for t in tavanlar:
        k = kademe(probs, t, a.esik)
        if k is None:
            print(f"{t:>8,}  kurulamıyor")
            continue
        sekil = "/".join(str(x) for x in k["sekil"])
        satir = f'{t:>8,}{sekil:>9}{k["bedel"]:>8,}{k["hedef"]:>10.4f}'
        if ana:
            fark = [i + 1 for i in range(len(ana)) if k["picks"][i] != ana[i]]
            satir += f'  {len(fark)} {fark if fark else ""}'
        print(satir)
        if a.tavan:
            print("  işaretler:", " ".join(k["picks"]))


if __name__ == "__main__":
    main()
