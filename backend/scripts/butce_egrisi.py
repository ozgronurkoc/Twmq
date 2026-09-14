"""Haftalık bütçe ne kadar olmalı — bekleme süresi ↔ beklenen harcama cephesi.

Sahibi iki kısıtı da kaldırdı (2026-09-14): **süre tavanı yok, toplam bütçe
tavanı yok.** O anda hedefin kendisi soru olmaktan çıkıyor — haftalık
`P(15/15) > 0` olduğu sürece yeterince oynayan **kesin** tutturur. Geriye iki
soru kalıyor ve ikisi de haftalık bütçenin fonksiyonu:

    ne kadar bekleriz?          E[hafta] = 1 / E[p]
    o zamana kadar ne harcarız?  E[harcama] = haftalık maliyet / E[p]

Bu betik o cepheyi çizer. Karar sahibinin; betiğin işi karara **fiyat
koymak**.

─── Neden TAVAN `p` kullanılıyor ─────────────────────────────────────────

Her basamakta `p`, o bütçeyle **en olası `N` kolonun** toplam olasılığıdır
(§3.76'nın kombinatorik tavanı), oynanabilir bir planınki değil. Sebep:
cephe bir **alt sınır** olsun isteniyor — gerçek bir plan bu `p`nin altında
kalır, yani gerçek bekleme ve gerçek harcama tablodakinden **büyüktür**.
Bugünkü planın tavana uzaklığı ölçülü ve küçük (21.000 kolonda %77,0 ↔
%79,6 hedef kademesinde), o yüzden cephe pratikte yakındır.

─── Bekleme neden `1 / E[p]` ─────────────────────────────────────────────

Haftalar arası `p` on altı kat ayrışıyor (%2,1–35,5). Gelecek haftaların bu
dağılımdan **bağımsız çekildiği** varsayılırsa bir haftada tutturmama
olasılığı `E[1−p] = 1 − E[p]`'dir ve ilk isabete kadar geçen süre geometrik
olur — yani `E[hafta] = 1 / E[p]` ve `P(H haftada) = 1 − (1 − E[p])^H`
**tam**, yaklaşık değil. (§3.73'ün Jensen uyarısı *sabit ardışık* pencere
içindir; burada pencere sabit değil, çekiliş bağımsız.)

Varsayımın sınırı yazılı: haftalar gerçekten bağımsız değilse (sezon etkisi,
lig karışımı) bu sayı iyimser olur. §3.46 hafta **içi** bağımlılığı ölçtü ve
kapattı; haftalar **arası** bağımlılık ölçülmedi.

    cd backend && python scripts/butce_egrisi.py
    cd backend && python scripts/butce_egrisi.py --basamak 21000 42000 105000
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from math import log
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.coklu_kiyasi import hafta_probs
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from spor_toto.coklu import MAC_SAYISI, _matris
from spor_toto.getiri import KOLON_BEDELI

#: Bütçe basamakları (kolon). Uçlar bilerek uçta: 1 kolon "tek kolon
#: oynasak" sorusudur, `3¹⁵` ise **kesin kazancın** fiyatı (Mandel, §3.77).
VARSAYILAN_BASAMAK = (1, 100, 1_000, 10_000, 21_000, 100_000, 1_000_000,
                      3 ** MAC_SAYISI)

#: Cephede gösterilen güven düzeyleri.
DUZEYLER = (0.50, 0.90, 0.99)


def _hafta_egrisi(probs: list[dict[str, float]],
                  basamaklar: Sequence[int]) -> list[float]:
    """Bir haftada her basamak için en olası `N` kolonun toplam olasılığı.

    `3¹⁵` kolonun tamamı bir kez kurulur, bir kez sıralanır ve birikimli
    toplam okunur — basamak başına ayrı `partition` çağırmaktan ucuz.
    """
    P = _matris(probs)
    kolonlar = P[0]
    for i in range(1, MAC_SAYISI):
        kolonlar = np.multiply.outer(kolonlar, P[i]).ravel()
    kolonlar.sort()
    birikim = np.cumsum(kolonlar[::-1])
    son = birikim.size
    return [float(birikim[min(n, son) - 1]) for n in basamaklar]


def kos(basamaklar: Sequence[int] = VARSAYILAN_BASAMAK) -> dict[str, Any]:
    """114 tam hafta üzerinde bütçe cephesi."""
    haftalar = tam_haftalar(ikramiye_tablolari())
    toplam = [0.0] * len(basamaklar)
    n = 0
    for _sezon, _hafta, lst in haftalar:
        probs, _gercek = hafta_probs(lst)
        for i, p in enumerate(_hafta_egrisi(probs, basamaklar)):
            toplam[i] += p
        n += 1

    satirlar = []
    for i, kolon in enumerate(basamaklar):
        p = toplam[i] / n
        maliyet = kolon * KOLON_BEDELI
        bekleme = (1.0 / p) if p > 0 else float("inf")
        satirlar.append({
            "kolon": kolon,
            "haftalik_tl": maliyet,
            "p": p,
            "bekleme_hafta": bekleme,
            "beklenen_harcama": maliyet * bekleme,
            "hafta": {
                f"{d:.0%}": (log(1 - d) / log(1 - p)) if 0 < p < 1 else
                (1.0 if p >= 1 else float("inf"))
                for d in DUZEYLER
            },
        })
    return {"hafta": n, "basamaklar": list(basamaklar), "satirlar": satirlar}


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   (TAVAN p — gercek plan bunun ALTINDA)\n")
    print(f"{'kolon':>12} {'haftalik TL':>14} {'P(15) hafta':>12} "
            f"{'E[hafta]':>10} {'E[harcama] TL':>17}   "
            f"{'%50':>7} {'%90':>8} {'%99':>8}")
    for r in c["satirlar"]:
        h = r["hafta"]
        print(f"{r['kolon']:>12,} {r['haftalik_tl']:>14,.0f} "
              f"{r['p']:>12.4%} {r['bekleme_hafta']:>10,.1f} "
              f"{r['beklenen_harcama']:>17,.0f}   "
              f"{h['50%']:>7,.1f} {h['90%']:>8,.1f} {h['99%']:>8,.1f}")
    print("\n'E[harcama]' = ilk isabete kadar beklenen BRUT harcama")
    print("(haftalik maliyet / P). Geri donen ikramiye dusulmemistir;")
    print("gorev olceginde olculen geri donus orani 0,449 (§3.79).")
    print("'%50/%90/%99' = o olasiliga ulasmak icin gereken hafta sayisi.")
    print("\nCephe MONOTON DEGIL iki yonlu okunur: butce buyudukce bekleme")
    print("kisalir ama beklenen harcama BUYUR — cunku p, butceyle")
    print("orantili degil, ALTINDA buyur. Karar bu odunlesmededir.")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--basamak", type=int, nargs="+",
                    default=list(VARSAYILAN_BASAMAK),
                    help="kolon basamaklari")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    c = kos(sorted(set(a.basamak)))
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return
    bas(c)


if __name__ == "__main__":  # pragma: no cover
    main()
