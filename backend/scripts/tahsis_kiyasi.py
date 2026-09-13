"""Tahsis kazancı: kupon başına **ayrı** alt sistem bütçesi ne getiriyor? (§3.71)

`coklu.py`nin ilk araması bütün kuponlara **aynı** alt sistemi veriyordu.
Oysa eksen bileşimlerinin olasılıkları yüzler kat ayrışıyor (hepsi favori ↔
81. bileşim) ve bir kuponun alt sistemini genişletmenin değeri tam olarak o
kuponun eksen olasılığıyla çarpılıyor: `P(15/15) = Σ_j q_j · p_alt_j`. Sabit
bütçeyi eşit bölmek, o hâlde, masada değer bırakır.

    cd backend && python scripts/tahsis_kiyasi.py
    cd backend && python scripts/tahsis_kiyasi.py --butce 21000 --serbest
    cd backend && python scripts/tahsis_kiyasi.py --eksen-sinavi 20

─── Okuma kuralı — ölçüm görülmeden yazıldı ─────────────────────────────

Yeni arama eski aramayı **içeriyor** (tek tip aday aramada duruyor), yani
kazanç tanım gereği `≥ 0`. Burada sınanan şey "kazanç var mı" **değil**:

1. **Büyüklük.** Kazanç, serbest kümeye (olasılığa göre en büyük `N` kolon —
   hiçbir kupon ailesinin geçemeyeceği tavan) kalan açığın ne kadarını
   kapatıyor? Mutlak yüzde değil, **kalan başlık içindeki pay** okunur;
   `--serbest` bunu ölçer.
2. **Haftalık geri gidiş.** Tek bir haftada bile eski aramanın gerisine
   düşmek bir **kusurdur**, kazancın küçük çıkması değil. Betik onu ayrıca
   sayar ve bekçisi `test_tahsisli_plan_ESKI_aramadan_kotu_DEGIL`.

Eksen kuralı (`eksen = en emin d maç`) da bu betikte sınanıyor
(`--eksen-sinavi`): ters sıra ve tek takas araması. Kural bir **iddiaydı** ve
`coklu.eksen_sec`in docstring'i onu gerekçesiyle savunuyordu ama ölçmemişti.
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
from spor_toto.coklu import (
    _INDEKS,
    ARANAN_KUPON,
    MAC_SAYISI,
    _eksen_bilesimleri,
    _matris,
    coklu_plan_serisi,
)
from spor_toto.secim import en_iyi_secim

#: Kıyaslanan kupon tavanları. 1 bugünkü tek sistemdir.
TAVANLAR = (1, 27, 81, 243, 729)


def tek_tip_arama(probs: list[dict[str, float]], butce: int, tavan: int) -> float:
    """Bu modülün **İLK** araması: tek tip alt sistem, ızgara `M`.

    Referans olarak burada duruyor ve `coklu.py`den **bağımsız** yazıldı:
    yeni aramanın eskisini içerdiği iddiası, eskisi ayrı bir gövdede
    durmadan sınanamaz. `tests/test_coklu.py` de bu gövdeyi çağırıyor —
    iki kopya olsaydı biri sessizce eskirdi.
    """
    P = _matris(probs)
    emin = np.argsort(-P.max(axis=1)).tolist()
    en = 0.0
    for M in ARANAN_KUPON:
        kupon_butce = butce // M
        if kupon_butce < 1:
            break
        for d in range(MAC_SAYISI + 1):
            eksen = sorted(emin[:d])
            kalanlar = [i for i in range(MAC_SAYISI) if i not in set(eksen)]
            alt = en_iyi_secim([probs[i] for i in kalanlar], kupon_butce,
                               esik=0) if kalanlar else None
            if kalanlar and alt is None:
                continue
            bedel = 1 if alt is None else alt.bedel
            sayi = min(butce // bedel, 3 ** d, tavan)
            if sayi < 1:
                continue
            p_alt = 1.0 if alt is None else float(np.prod(
                [P[i, [_INDEKS[s] for s in sec]].sum()
                 for i, sec in zip(kalanlar, alt.secimler)]))
            _, p_eksen = _eksen_bilesimleri(P, eksen, sayi)
            en = max(en, p_eksen * p_alt)
    return en


def serbest_kume_p(probs: list[dict[str, float]], n: int) -> float:
    """Olasılığa göre en büyük `n` kolonun toplam olasılığı — **tavan**.

    Hiçbir kupon ailesi bunu geçemez: `n` kolonluk herhangi bir küme, en
    olası `n` kolondan fazlasını taşıyamaz. `3¹⁵ = 14.348.907` kolonun
    tamamı kurulur (~115 MB, ~1 sn); bu yüzden isteğe bağlı.
    """
    P = _matris(probs)
    kolonlar = P[0]
    for i in range(1, MAC_SAYISI):
        kolonlar = np.multiply.outer(kolonlar, P[i]).ravel()
    if n >= kolonlar.size:
        return float(kolonlar.sum())
    return float(np.partition(kolonlar, -n)[-n:].sum())


def kos(butce: int, serbest: bool = False) -> dict[str, Any]:
    haftalar = tam_haftalar(ikramiye_tablolari())
    n = len(haftalar)
    top = {t: {"eski": 0.0, "yeni": 0.0, "geride": 0, "kupon": 0, "kolon": 0,
               "boy": 0} for t in TAVANLAR}
    serbest_top = 0.0

    for _sezon, _w, lst in haftalar:
        probs, _gercek = hafta_probs(lst)
        seri = coklu_plan_serisi(probs, butce, TAVANLAR)
        for t in TAVANLAR:
            plan = seri[t]
            eski = tek_tip_arama(probs, butce, t)
            h = top[t]
            h["eski"] += eski
            h["yeni"] += plan.p_onbes
            h["geride"] += int(plan.p_onbes < eski - 1e-12)
            h["kupon"] += plan.kupon_sayisi
            h["kolon"] += plan.kolon
            h["boy"] += len({k.kolon for k in plan.kuponlar})
        if serbest:
            serbest_top += serbest_kume_p(probs, butce)

    return {"hafta": n, "butce": butce,
            "serbest": (serbest_top / n) if serbest else None,
            "satirlar": [{
                "tavan": t,
                "eski": top[t]["eski"] / n,
                "yeni": top[t]["yeni"] / n,
                "kazanc": top[t]["yeni"] / top[t]["eski"],
                "geride": top[t]["geride"],
                "kupon_ort": top[t]["kupon"] / n,
                "kolon_ort": top[t]["kolon"] / n,
                "boy_ort": top[t]["boy"] / n,
            } for t in TAVANLAR]}


def eksen_sinavi(butce: int, hafta_sayisi: int, tavan: int = 81) -> dict[str, Any]:
    """Eksen kuralı sınavı: en emin ↔ ters ↔ tek takas araması.

    Takas araması pahalıdır (her takas bir arama), o yüzden hafta sayısı
    parametre — raporlanan `n` neyse o.
    """
    haftalar = tam_haftalar(ikramiye_tablolari())[:hafta_sayisi]
    top = {"emin": 0.0, "ters": 0.0, "takas": 0.0}
    takas_sayisi = 0

    for _sezon, _w, lst in haftalar:
        probs, _gercek = hafta_probs(lst)
        P = _matris(probs)
        sira = np.argsort(-P.max(axis=1)).tolist()
        emin = coklu_plan_serisi(probs, butce, (tavan,), sira)[tavan]
        ters = coklu_plan_serisi(probs, butce, (tavan,), sira[::-1])[tavan]
        top["emin"] += emin.p_onbes
        top["ters"] += ters.p_onbes

        # tek takas: eksenin bir maçını eksen dışı bir maçla değiştir
        en_p, en_eksen = emin.p_onbes, list(emin.eksen)
        gelisti = True
        while gelisti:
            gelisti = False
            disari = [x for x in range(MAC_SAYISI) if x not in set(en_eksen)]
            for i in list(en_eksen):
                for j in disari:
                    aday = [x for x in en_eksen if x != i] + [j]
                    yeni_sira = aday + [x for x in range(MAC_SAYISI)
                                        if x not in set(aday)]
                    p = coklu_plan_serisi(probs, butce, (tavan,),
                                          yeni_sira)[tavan].p_onbes
                    if p > en_p * (1 + 1e-9):
                        en_p, en_eksen, gelisti = p, aday, True
                        takas_sayisi += 1
                        break
                if gelisti:
                    break
        top["takas"] += en_p

    return {"hafta": len(haftalar), "tavan": tavan, "butce": butce,
            "emin": top["emin"] / len(haftalar),
            "ters": top["ters"] / len(haftalar),
            "takas": top["takas"] / len(haftalar),
            "ters_orani": top["ters"] / top["emin"],
            "takas_orani": top["takas"] / top["emin"],
            "takas_sayisi": takas_sayisi}


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon "
          f"({c['butce'] * 10:,} TL/hafta)\n")
    print(f"{'tavan':>6} {'tek tip':>10} {'tahsisli':>10} {'kazanc':>8} "
          f"{'kupon':>7} {'kolon':>8} {'boy':>5} {'geride':>7}"
          + ("  kapanan acik" if c["serbest"] else ""))
    for r in c["satirlar"]:
        pay = ""
        if c["serbest"]:
            acik = c["serbest"] - r["eski"]
            pay = (f"{(r['yeni'] - r['eski']) / acik:>13.1%}" if acik > 1e-12
                   else f"{'—':>13}")
        print(f"{r['tavan']:>6,} {r['eski']:>10.3%} {r['yeni']:>10.3%} "
              f"x{r['kazanc']:>7.3f} {r['kupon_ort']:>7,.0f} "
              f"{r['kolon_ort']:>8,.0f} {r['boy_ort']:>5.1f} "
              f"{r['geride']:>7}{pay}")
    if c["serbest"]:
        print(f"\nserbest kume (tavan, {c['butce']:,} kolon): {c['serbest']:.3%}")
    geride = sum(r["geride"] for r in c["satirlar"])
    print(f"geri giden hafta (tavan x hafta): {geride}  "
          f"{'— kusur YOK' if geride == 0 else '<<< KUSUR'}")


def bas_eksen(e: dict[str, Any]) -> None:
    print(f"\neksen sinavi — {e['hafta']} hafta, tavan {e['tavan']}, "
          f"butce {e['butce']:,}")
    print(f"  en emin d mac (bugunku kural) : {e['emin']:.4%}")
    print(f"  ters sira (en EMIN OLMAYAN)   : {e['ters']:.4%}  "
          f"x{e['ters_orani']:.3f}")
    print(f"  tek takas aramasi             : {e['takas']:.4%}  "
          f"x{e['takas_orani']:.4f}  ({e['takas_sayisi']} takas)")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--serbest", action="store_true",
                    help="serbest kume tavanini da olc (3^15 kolon, yavas)")
    ap.add_argument("--eksen-sinavi", type=int, metavar="HAFTA", default=0,
                    help="eksen kuralini ilk N haftada sina")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.eksen_sinavi:
        e = eksen_sinavi(a.butce, a.eksen_sinavi)
        if a.json:
            print(json.dumps(e, ensure_ascii=False, indent=1))
        else:
            bas_eksen(e)
        return

    c = kos(a.butce, a.serbest)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
    else:
        bas(c)


if __name__ == "__main__":
    main()
