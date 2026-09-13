#!/usr/bin/env python3
"""Bir haftanın **oynanacak** çoklu kuponlarını üretir.

`super_toto_hafta.py` haftayı okur, profilini çıkarır ve **tek** bir tam
sistem kurar (`secim.en_iyi_secim`). Bu script aynı olasılıkları alır ve
`coklu.coklu_plan` ile aynı bütçeyi birden çok kupona böler. 114 haftada
ölçülen fark, aynı parada `P(15/15)` için **×1,40** — ve bu çarpan hangi
satırdan geldiği yazılmadan okunmamalı: **729 kupon ↔ tek sistem, 19.683
kolonda** (%10,461 ↔ %7,489). Aynı bütçedeki üst sınır (serbest küme)
×1,45, gerçek bütçede (21.000 kolon) 329 kupon ×1,42. Üçü ayrı satırdır ve
üçü de `scripts/coklu_kiyasi.py`'den çıkar; ayrıntı `coklu.py` başlığında.

Olasılıklar `super_toto_hafta.hafta_yukle`den gelir — ayrı bir hesap
kurulmadı ve kurulmamalı: kuponu **kuran** olasılıkla onu **değerlendiren**
olasılık ayrışırsa aynı hafta iki farklı şey söyler. Depo bu hatayı bir kez
yaptı (`ortak.py` uyarısı).

    python scripts/coklu_kupon.py --hafta 5 --butce 21000
    python scripts/coklu_kupon.py --hafta 5 --butce 21000 --tavan 81
    python scripts/coklu_kupon.py --hafta 5 --butce 21000 --json > kupon.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from scripts.super_toto_hafta import hafta_yukle

#: Islenen sezon. `super_toto_hafta.py` bunu CLI varsayilaninda tutuyor;
#: burada tekrarlanmasi yerine tek yerden okunmasi gerekirdi ama o deger
#: bir sabit degil argparse varsayilani — kopyalamak yerine ayni dizgeyi
#: yaziyoruz ve ikisi ayrisirsa hafta dosyasi bulunamayip SESLI patlar.
VARSAYILAN_SEZON = "2026_27"

from spor_toto.coklu import (
    ARANAN_KUPON,
    coklu_plan,
    coklu_plan_serisi,
    p_onbes,
)
from spor_toto.getiri import KOLON_BEDELI
from spor_toto.secim import en_iyi_secim


def plan_uret(d: dict, butce: int, tavan: int | None) -> dict:
    """Haftanın çoklu kupon planı + tek sistemle kıyası."""
    maclar = d["matches"]
    probs = [m["probs"] for m in maclar]

    plan = coklu_plan(probs, butce, kupon_tavani=tavan)

    # kıyas: aynı bütçede tek sistem ne verirdi
    tek = en_iyi_secim(probs, butce, esik=0)
    if tek is None:
        # `coklu_plan` yukarıda ValueError atardı, yani buraya normalde
        # gelinmez; sessizce `None` taşımak yerine SESLİ patlıyor.
        raise ValueError(f"Butce tek sistemi de karsilamiyor: {butce}")
    p_tek = 1.0
    for m, sec in zip(maclar, tek.secimler):
        p_tek *= sum(m["probs"][s] for s in sec)

    return {
        "sezon": d["meta"].get("season"), "hafta": d["meta"].get("week"),
        "butce_kolon": butce,
        "butce_tl": butce * KOLON_BEDELI,
        "kupon_sayisi": plan.kupon_sayisi,
        "kolon": plan.kolon,
        "tl": plan.kolon * KOLON_BEDELI,
        "p_onbes": plan.p_onbes,
        # planın taşıdığı sayı ile kupondan yeniden ölçüm ayrışmamalı
        "p_onbes_dogrulama": p_onbes(probs, plan.kuponlar),
        "eksen": plan.eksen,
        "tek_sistem": {"kolon": tek.bedel, "p_onbes": p_tek,
                       "picks": ["".join(s) for s in tek.secimler]},
        "kazanc": plan.p_onbes / p_tek if p_tek else None,
        "kuponlar": [{"no": i + 1, "kolon": k.kolon, "picks": k.picks}
                     for i, k in enumerate(plan.kuponlar)],
        "maclar": [{"no": m.get("no", i + 1),
                    "mac": f"{m.get('home')} – {m.get('away')}",
                    "probs": m["probs"]}
                   for i, m in enumerate(maclar)],
    }


def yaz(c: dict, egri: list | None) -> None:
    print(f"\n{c['sezon']} · {c['hafta']}. hafta — çoklu kupon planı")
    print(f"bütçe   : {c['butce_kolon']:,} kolon  ({c['butce_tl']:,.0f} TL)")
    print(f"kullanım: {c['kupon_sayisi']:,} kupon × "
          f"{c['kuponlar'][0]['kolon']:,} kolon = {c['kolon']:,} kolon "
          f"({c['tl']:,.0f} TL)")
    print(f"\nP(15/15) : {c['p_onbes']:.3%}")
    print(f"tek sistem: {c['tek_sistem']['p_onbes']:.3%} "
          f"({c['tek_sistem']['kolon']:,} kolon)")
    if c["kazanc"]:
        print(f"kazanç    : ×{c['kazanc']:.2f}")

    fark = abs(c["p_onbes"] - c["p_onbes_dogrulama"])
    if fark > 1e-9:
        raise SystemExit(
            f"HEDEF AYRISTI: plan {c['p_onbes']} ↔ kupondan {c['p_onbes_dogrulama']}")

    print(f"\neksen maçları (kuponlar arasında değişen): "
          f"{', '.join(str(i + 1) for i in c['eksen'])}")

    if egri:
        print("\nkupon sayısı ↔ hedef:")
        for kupon, kolon, p in egri:
            print(f"  {kupon:>6,} kupon × {kolon:>7,} kolon   P(15/15) = {p:.3%}")

    print(f"\n{'#':>5}  " + "  ".join(f"{i + 1:>3}" for i in range(15)))
    for k in c["kuponlar"][:40]:
        print(f"{k['no']:>5}  " + "  ".join(f"{p:>3}" for p in k["picks"]))
    if len(c["kuponlar"]) > 40:
        print(f"  ... ve {len(c['kuponlar']) - 40:,} kupon daha (--json ile tamamı)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hafta", type=int, required=True)
    ap.add_argument("--sezon", default=VARSAYILAN_SEZON)
    ap.add_argument("--butce", type=int, required=True,
                    help="kolon butcesi (210.000 TL = 21.000 kolon)")
    ap.add_argument("--tavan", type=int, default=None,
                    help="en fazla kac kupon (varsayilan: sinirsiz)")
    ap.add_argument("--egri", action="store_true",
                    help="kupon sayisi <-> hedef odunlesmesini de bas")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    d = hafta_yukle(a.sezon, a.hafta)
    c = plan_uret(d, a.butce, a.tavan)

    egri = None
    if a.egri:
        probs = [m["probs"] for m in d["matches"]]
        seri = coklu_plan_serisi(probs, a.butce, ARANAN_KUPON)
        egri = [(seri[t].kupon_sayisi,
                 seri[t].kuponlar[0].kolon,
                 seri[t].p_onbes) for t in sorted(seri)]

    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
    else:
        yaz(c, egri)


if __name__ == "__main__":
    main()
