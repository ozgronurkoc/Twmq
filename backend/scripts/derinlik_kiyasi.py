"""Değişken derinlikli eksen ne getiriyor? (§3.72)

Sabit derinlikte **bütün** kuponlar aynı `d` maçı tekleştirir ve eksenin
`3^d` bileşiminden yalnızca en olası `M` tanesi oynanır. İki kısıt birden
var: granülerlik tek tip (hepsi favori dalı ile 81. bileşim aynı inceliği
alıyor, oysa `q` iki mertebe ayrışıyor) ve **artan kütle düşüyor** (en olası
`M` bileşimin dışı hiç oynanmıyor). Ağaç ikisini de kaldırır — kuponlar
eminlik sırasının ön eklerinde duran bir antizincirdir ve sabit derinlik
bunun özel hâlidir.

    cd backend && python scripts/derinlik_kiyasi.py
    cd backend && python scripts/derinlik_kiyasi.py --butce 21000 --serbest
    cd backend && python scripts/derinlik_kiyasi.py --mekanizma 20

─── Okuma kuralı — ölçüm görülmeden yazıldı ─────────────────────────────

`tahsis_kiyasi.py`nin okuma kuralının aynısı geçerli: yeni aile eskisini
**içeriyor** (sabit derinlik `M = 3^d` özel hâli), yani kazanç tanım gereği
`≥ 0` ve "kazanç var mı" diye sorulmuyor. Sorulan iki şey var:

1. **Büyüklük.** Kazanç, serbest kümeye kalan açığın ne kadarını kapatıyor?
   `--serbest` bunu ölçer. Kazanç küçük çıkarsa bu bir başarısızlık değil bir
   **bulgu**dur — ama ancak yanına *niçin* konursa.
2. **Niçin.** Ağaç bir **sezgiseldir** (açgözlü büyütme, fiyat ızgarası
   üstünde), yani kazanç küçük çıktığında iki okuma var: aile boş, ya da
   arama zayıf. `--mekanizma` tam bu ayrımı kapatır ve içinde sezgisel
   **yoktur**.

   Sabit derinlikli planın yaprak kümesi ağaç ailesinin bir üyesidir (aynı
   derinlikte `M` düğüm, bir antizincir). O hâlde üstünde ailenin hamleleri
   tek tek denenebilir ve bütçe her denemede `_tahsis_kabuklu` ile yeniden,
   **kesin** dağıtılır:

   * `takas` — en düşük olasılıklı yaprağı at, terk edilmiş en olası ön ek
     düğümünü koy. Kupon sayısı **değişmez**.
   * `ekleme` — düğümü ekle, hiçbirini atma. Bir yuva daha harcar; üst sınır.

   `takas` sıfırsa sabit derinlikli plan bu hamle kümesinde yerel en iyidir:
   bulgu ailenindir, aramanın değil.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.coklu_kiyasi import VARSAYILAN_BUTCE, hafta_probs
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from scripts.tahsis_kiyasi import serbest_kume_p
from spor_toto.coklu import (
    _cepheler,
    _eksen_olasiliklari,
    _matris,
    _tahsis_kabuklu,
    coklu_plan_serisi,
)

#: Kıyaslanan kupon tavanları. 1 bugünkü tek sistemdir.
TAVANLAR = (1, 27, 81, 243, 729)


def kos(butce: int, serbest: bool = False) -> dict[str, Any]:
    """114 tam haftada sabit derinlik ↔ sabit + değişken derinlik."""
    haftalar = tam_haftalar(ikramiye_tablolari())
    n = len(haftalar)
    top = {t: {"sabit": 0.0, "yeni": 0.0, "kazandi": 0, "geride": 0,
               "en_buyuk": 0.0, "kupon": 0, "kolon": 0} for t in TAVANLAR}
    serbest_top = 0.0

    for _sezon, _w, lst in haftalar:
        probs, _gercek = hafta_probs(lst)
        yeni = coklu_plan_serisi(probs, butce, TAVANLAR)
        sabit = coklu_plan_serisi(probs, butce, TAVANLAR,
                                  degisken_derinlik=False)
        for t in TAVANLAR:
            h = top[t]
            a, b = sabit[t].p_onbes, yeni[t].p_onbes
            h["sabit"] += a
            h["yeni"] += b
            h["kazandi"] += int(b > a * (1 + 1e-12))
            h["geride"] += int(b < a - 1e-12)
            h["en_buyuk"] = max(h["en_buyuk"], (b / a - 1.0) if a > 0 else 0.0)
            h["kupon"] += yeni[t].kupon_sayisi
            h["kolon"] += yeni[t].kolon
        if serbest:
            serbest_top += serbest_kume_p(probs, butce)

    return {"hafta": n, "butce": butce,
            "serbest": (serbest_top / n) if serbest else None,
            "satirlar": [{
                "tavan": t,
                "sabit": top[t]["sabit"] / n,
                "yeni": top[t]["yeni"] / n,
                "kazanc": top[t]["yeni"] / top[t]["sabit"],
                "kazandi": top[t]["kazandi"],
                "geride": top[t]["geride"],
                "en_buyuk": top[t]["en_buyuk"],
                "kupon_ort": top[t]["kupon"] / n,
                "kolon_ort": top[t]["kolon"] / n,
            } for t in TAVANLAR]}


def _yerel_sinav(probs: list[dict[str, float]], butce: int, tavan: int
                 ) -> tuple[float, float, float]:
    """`(terk, takas_kazanci, ekleme_kazanci)` — sabit derinlik yerel en iyi mi?

    `terk`, sabit derinlikli planın **oynamadığı** eksen kütlesidir: `d`
    derinlikte `3^d` bileşimin yalnızca en olası `M` tanesi oynanıyor ve
    kalanı hiç. Büyük çıkması tek başına "masada değer var" demez — o kütleyi
    kapatmak hem kolon hem **kupon yuvası** harcar.

    Onun için kütle doğrudan fiyatlanıyor. Sabit derinlikli planın yaprak
    kümesi ağaç ailesinin bir üyesidir (aynı derinlikte `M` düğüm, bir
    antizincir), yani üstünde ağaç ailesinin hamleleri denenebilir. Her
    `k ≤ d` derinliğinde **oynanmayan en olası ön ek düğümü** bulunur ve iki
    hamle ayrı ayrı ölçülür — ikisinde de bütçe `_tahsis_kabuklu` ile
    **yeniden ve kesin** dağıtılır, yani sezgisel yok:

    * `takas` — en düşük olasılıklı yaprağı atıp o düğümü koy. **Kupon sayısı
      değişmez**, yani bu, sabit derinliğin yerel en iyi olup olmadığının
      kesin sınavıdır.
    * `ekleme` — düğümü ekle, hiçbirini atma. Bir yuva daha harcar; üst sınır
      olarak durur.

    `takas` sıfırsa sabit derinlikli plan bu hamle kümesinde yerel en iyidir
    ve ağacın alacağı bir şey yoktur — kazancın niçin binde birlerde kaldığı
    buradan okunur.
    """
    P = _matris(probs)
    sira = np.argsort(-P.max(axis=1)).tolist()
    _cephe, katlar = _cepheler(probs, P, butce, sira)
    plan = coklu_plan_serisi(probs, butce, (tavan,),
                             degisken_derinlik=False)[tavan]
    d = len(plan.eksen)
    kat = katlar[d]
    M = plan.kupon_sayisi
    bilesimler, q = _eksen_olasiliklari(P, plan.eksen, M)
    terk = 1.0 - sum(q)
    if kat is None or M < 2:
        return terk, 0.0, 0.0

    taban = _tahsis_kabuklu(list(q), [kat.kabuk] * M, butce)
    if taban is None or taban[0] <= 0.0:
        return terk, 0.0, 0.0

    takas = ekleme = 0.0
    for k in range(d + 1):
        k_kat = katlar[k]
        if k_kat is None:
            continue
        k_eksen = sorted(sira[:k])
        # Oynanan her kuponun `k` derinliğindeki ön eki bu kümede; dışındaki
        # her düğümün ALTI tamamen terk edilmiştir.
        oynanan = {tuple(dict(zip(plan.eksen, b))[i] for i in k_eksen)
                   for b in bilesimler}
        aday, aday_q = _eksen_olasiliklari(
            P, k_eksen, min(len(oynanan) + 1, 3 ** k))
        bos = next((w for b, w in zip(aday, aday_q) if b not in oynanan), 0.0)
        if bos <= 0.0:
            continue
        # `q` azalan sırada — son yaprak en düşük olasılıklı olandır.
        a = _tahsis_kabuklu([*q[:-1], bos],
                            [kat.kabuk] * (M - 1) + [k_kat.kabuk], butce)
        b = _tahsis_kabuklu([*q, bos],
                            [kat.kabuk] * M + [k_kat.kabuk], butce)
        if a is not None:
            takas = max(takas, a[0] / taban[0] - 1.0)
        if b is not None:
            ekleme = max(ekleme, b[0] / taban[0] - 1.0)
    return terk, takas, ekleme


def mekanizma(butce: int, hafta_sayisi: int) -> dict[str, Any]:
    """Kazancın niçin küçük kaldığı: terk edilen kütle ve yerel en iyilik.

    Pahalıdır (tavan başına ayrı bir sabit derinlikli arama + her derinlikte
    iki yeniden tahsis), o yüzden hafta sayısı parametre — raporlanan `n`
    neyse o.
    """
    haftalar = tam_haftalar(ikramiye_tablolari())[:hafta_sayisi]
    n = len(haftalar)
    top = {t: [0.0, 0.0, 0.0, 0] for t in TAVANLAR}
    for _sezon, _w, lst in haftalar:
        probs, _gercek = hafta_probs(lst)
        for t in TAVANLAR:
            terk, takas, ekleme = _yerel_sinav(probs, butce, t)
            top[t][0] += terk
            top[t][1] += takas
            top[t][2] += ekleme
            top[t][3] += int(takas > 1e-12)
    return {"hafta": n, "butce": butce,
            "satirlar": [{"tavan": t,
                          "terk": top[t][0] / n,
                          "takas": top[t][1] / n,
                          "ekleme": top[t][2] / n,
                          "takas_kazandi": top[t][3]} for t in TAVANLAR]}


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon "
          f"({c['butce'] * 10:,} TL/hafta)\n")
    print(f"{'tavan':>6} {'sabit':>10} {'+degisken':>10} {'kazanc':>9} "
          f"{'kazandi':>8} {'en buyuk':>9} {'kupon':>7} {'kolon':>8} "
          f"{'geride':>7}" + ("  kapanan acik" if c["serbest"] else ""))
    for r in c["satirlar"]:
        pay = ""
        if c["serbest"]:
            acik = c["serbest"] - r["sabit"]
            pay = (f"{(r['yeni'] - r['sabit']) / acik:>13.2%}" if acik > 1e-12
                   else f"{'—':>13}")
        print(f"{r['tavan']:>6,} {r['sabit']:>10.4%} {r['yeni']:>10.4%} "
              f"x{r['kazanc']:>8.5f} {r['kazandi']:>4}/{c['hafta']:<3} "
              f"{r['en_buyuk']:>9.2%} {r['kupon_ort']:>7,.0f} "
              f"{r['kolon_ort']:>8,.0f} {r['geride']:>7}{pay}")
    if c["serbest"]:
        print(f"\nserbest kume (tavan, {c['butce']:,} kolon): {c['serbest']:.4%}")
    geride = sum(r["geride"] for r in c["satirlar"])
    print(f"geri giden hafta (tavan x hafta): {geride}  "
          f"{'— kusur YOK' if geride == 0 else '<<< KUSUR'}")


def bas_mekanizma(m: dict[str, Any]) -> None:
    print(f"\nmekanizma — {m['hafta']} hafta, butce {m['butce']:,}")
    print(f"{'tavan':>6} {'terk edilen eksen':>18} {'takas (ayni yuva)':>18} "
          f"{'kazandigi hafta':>16} {'ekleme (+1 yuva)':>17}")
    for r in m["satirlar"]:
        print(f"{r['tavan']:>6,} {r['terk']:>18.2%} {r['takas']:>18.4%} "
              f"{r['takas_kazandi']:>12}/{m['hafta']:<3} {r['ekleme']:>17.4%}")
    print("\nTerk edilen kutle buyuk, ama onu kapatmak hem kolon hem kupon")
    print("YUVASI harcar. 'takas' sutunu yuva sayisini SABIT tutar: sifirsa")
    print("sabit derinlikli plan bu hamle kumesinde yerel en iyidir, yani")
    print("agacin alacagi bir sey yoktur.")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--serbest", action="store_true",
                    help="serbest kume tavanini da olc (3^15 kolon, yavas)")
    ap.add_argument("--mekanizma", type=int, metavar="HAFTA", default=0,
                    help="terk edilen kutleyi ve marjinal oranlari olc")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.mekanizma:
        m = mekanizma(a.butce, a.mekanizma)
        if a.json:
            print(json.dumps(m, ensure_ascii=False, indent=1))
        else:
            bas_mekanizma(m)
        return

    c = kos(a.butce, a.serbest)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
    else:
        bas(c)


if __name__ == "__main__":
    main()
