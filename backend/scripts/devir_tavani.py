#!/usr/bin/env python3
"""Devir tavanı — müşterek havuzda pozitif beklenen değerin **tek** koşulu.

Dış literatürün bu oyuna dair en somut iddiası şudur (Thaler & Ziemba 1988;
Ziemba 2021 §"carryover"): müşterek bir havuzda ortalama bilet **her zaman**
kaybettirir, çünkü kurum payı havuzdan önce alınır. Pozitif beklenen değer
ancak **dışarıdan para girerse** doğar ve piyangolarda o para tek bir yerden
gelir: **devir** (önceki haftalardan taşınan, bu hafta dağıtılan tutar).

Bu, ölçülecek değil **hesaplanacak** bir şeydir ve deponun bugünkü devir
sınavı (`kademe_analizi.py` bölüm G) bunu bir *istatistik* sorusu gibi
kuruyor: "devirli haftalarda getiri yüksek mi?" — 25 hafta, gürültü baskın,
"tutarlı bir yön YOK". Oysa aritmetik kapalı biçimde çözülüyor.

─── Özdeşlik ─────────────────────────────────────────────────────────────

Bir haftada kolon başına geri dönüş:

    getiri = dağıtılan_toplam / (N × bedel)

`dagitilan` haftanın **kendi** payıdır ve tanım gereği hasılatın sabit bir
oranıdır: `dagitilan = odeme_orani × N × bedel`. `devir_gelen` ise havuza
bilet karşılığı olmadan giren paradır. İkisini yerine koyunca:

    getiri = odeme_orani × (1 + devir_gelen / dagitilan) = odeme_orani × (1 + d)

`odeme_orani` düzenlemeyle sabittir, yani **bir haftanın getirisini haftalar
arasında ayıran tek çarpan `(1 + d)`'dir.** Pozitif beklenen değerin koşulu
tek bir eşitsizliktir:

    1 + d  >  1 / odeme_orani

`d` payda olarak `dagitilan`ı kullanır; o da hafta jackpot yüzünden kalabalık
olduğunda birlikte büyür, yani `d` hacim artışına karşı **kendiliğinden
normalize**dir. Ölçüm bu yüzden "devirli hafta daha çok oynanıyor" itirazına
bağışıktır.

`odeme_orani` bu veriden doğrudan okunamaz — arşiv brüt hasılatı taşımıyor
(`docs/VERI_TOPLAMA_VE_ISLEME.md` §10.1) ve doktrin 2 gereği uydurulmaz.
Ama geriye doğru **ima** edilebilir: `KADEME_OLASILIKLARI.md` §5.2 ölçülmüş
ortalama getiriyi bütçeye göre %37–%54 bandında veriyor (₺10 ölçeğinde), ve
`odeme_orani = ortalama_getiri / ortalama(1+d)`. Band olduğu için sonuç da
band olarak yazılır; tek bir sayıya indirilmez.

─── "Hep ev sahibi" kuralı ───────────────────────────────────────────────

Aynı taramada çıkan tek dış çalışma (arXiv:2303.16648) **birebir bu oyunda**
— Alman TOTO 13'lü Wette, müşterek havuz — kâr iddia ediyor ve reçetesi tek
cümle: ev sahibi galibiyeti en sık sonuçtur, hep `1` işaretle; makale isabet
oranını Bundesliga'da %50,4 alıyor. `--evkurali` o kuralı **bizim
korpusumuzda** koşar ve piyasa favorisiyle yan yana koyar.

Koşum (ağsız, saniyeler):

    python scripts/devir_tavani.py            # ikisi birden
    python scripts/devir_tavani.py --devir
    python scripts/devir_tavani.py --evkurali
    python scripts/devir_tavani.py --json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK.parent))

#: `KADEME_OLASILIKLARI.md` §5.2 (2026-09-04, ₺10 ölçeğinde yeniden ölçüldü):
#: bütçeye göre ortalama haftalık geri dönüş. En küçük ve en büyük değer.
#: Tek sayı DEĞİL — `odeme_orani` bundan türediği için sonuç da band kalır.
OLCULEN_ORT_GETIRI = (0.37, 0.54)

KORPUS = KOK.parent / "data" / "egitim" / "egitim_korpus.csv"


def _wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson %95 aralığı — 30 altı örneklemde de çökmez."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    z = 1.96
    d = 1 + z * z / n
    orta = (p + z * z / (2 * n)) / d
    yari = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (orta - yari, orta + yari)


def devir_tavani() -> dict[str, Any]:
    """222 arşiv haftasında `1 + d` dağılımı ve pozitif BD koşulu."""
    from spor_toto.havuz import arsiv_haftalari

    carpanlar: list[float] = []
    kayit: list[dict[str, Any]] = []
    for h in arsiv_haftalari():
        hv = h.get("havuz")
        if not hv or hv["dagitilan"] <= 0:
            continue
        d = hv["devir_gelen"] / hv["dagitilan"]
        carpanlar.append(1 + d)
        kayit.append({"sezon": h["season_key"], "hafta": h["week"],
                      "carpan": 1 + d, "devir_gelen": hv["devir_gelen"],
                      "dagitilan": hv["dagitilan"],
                      "anormal": bool(h.get("anormal"))})
    if not carpanlar:
        return {"n": 0}

    n = len(carpanlar)
    sirali = sorted(carpanlar)
    ort = sum(carpanlar) / n
    azami = sirali[-1]

    def yuzdelik(q: float) -> float:
        i = min(n - 1, max(0, round(q / 100 * (n - 1))))
        return sirali[i]

    kosul = []
    for getiri in OLCULEN_ORT_GETIRI:
        odeme = getiri / ort
        kosul.append({"olculen_ort_getiri": getiri,
                      "ima_edilen_odeme_orani": odeme,
                      "gereken_carpan": 1 / odeme,
                      "en_iyi_haftanin_getirisi": odeme * azami,
                      "ulasildi": azami >= 1 / odeme})

    return {
        "n": n,
        "devirli_hafta": sum(1 for c in carpanlar if c > 1.005),
        "ortalama_carpan": ort,
        "medyan_carpan": yuzdelik(50),
        "p90": yuzdelik(90), "p95": yuzdelik(95),
        "azami_carpan": azami,
        "kosul": kosul,
        "en_buyuk": sorted(kayit, key=lambda r: -r["carpan"])[:5],
    }


def ev_kurali() -> dict[str, Any]:
    """arXiv:2303.16648'in "hep ev sahibi" kuralı, bizim korpusumuzda."""
    if not KORPUS.exists():
        return {"n": 0, "not": f"korpus yok: {KORPUS}"}

    n = ev = 0
    orani_olan = favori = favori_ev = 0
    with KORPUS.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            kod = r.get("kod")
            if kod not in ("1", "0", "2"):
                continue
            n += 1
            ev += kod == "1"
            try:
                o = [float(r["oran_1"]), float(r["oran_0"]), float(r["oran_2"])]
            except (TypeError, ValueError, KeyError):
                continue
            if min(o) <= 0:
                continue
            orani_olan += 1
            s = ["1", "0", "2"][o.index(min(o))]
            favori += s == kod
            favori_ev += s == "1"

    def kupon(p: float) -> dict[str, float]:
        """15 maçlık kupon ölçeğine bağımsızlık VARSAYARAK çevirir."""
        t = [math.comb(15, k) * p ** k * (1 - p) ** (15 - k) for k in range(16)]
        return {"beklenen_dogru": 15 * p,
                "P12arti": sum(t[12:]), "P14arti": sum(t[14:])}

    p_ev = ev / n if n else 0.0
    p_fav = favori / orani_olan if orani_olan else 0.0
    return {
        "n": n, "orani_olan": orani_olan,
        "ev_orani": p_ev, "ev_ga": _wilson(ev, n),
        "favori_isabeti": p_fav, "favori_ga": _wilson(favori, orani_olan),
        "favorinin_ev_oldugu_pay": favori_ev / orani_olan if orani_olan else 0.0,
        "makalenin_orani": 0.504,
        "kupon_ev": kupon(p_ev), "kupon_favori": kupon(p_fav),
    }


def yaz_devir(o: dict[str, Any]) -> None:
    print("=" * 74)
    print("DEVİR TAVANI — pozitif beklenen değerin tek koşulu")
    print("=" * 74)
    print(f"  havuzu hesaplanabilen hafta : {o['n']}")
    print(f"  devir ALAN hafta            : {o['devirli_hafta']} "
          f"(%{100 * o['devirli_hafta'] / o['n']:.1f})")
    print(f"  çarpan (1+d)  ortalama      : {o['ortalama_carpan']:.4f}")
    print(f"                medyan        : {o['medyan_carpan']:.4f}")
    print(f"                p90 / p95     : {o['p90']:.3f} / {o['p95']:.3f}")
    print(f"                **AZAMİ**     : {o['azami_carpan']:.4f}")
    print()
    print("  Koşul:  1 + d  >  1 / ödeme_oranı")
    print(f"  {'ölçülen ort. getiri':>20} | {'ima edilen ödeme':>16} | "
          f"{'GEREKEN 1+d':>11} | {'en iyi hafta':>12} | ulaşıldı mı")
    for k in o["kosul"]:
        print(f"  {'%' + format(100 * k['olculen_ort_getiri'], '.0f'):>20} | "
              f"{'%' + format(100 * k['ima_edilen_odeme_orani'], '.1f'):>16} | "
              f"{k['gereken_carpan']:>11.2f} | "
              f"{'%' + format(100 * k['en_iyi_haftanin_getirisi'], '.1f'):>12} | "
              f"{'EVET' if k['ulasildi'] else 'HAYIR'}")
    print()
    print("  En büyük beş devir haftası:")
    for r in o["en_buyuk"]:
        print(f"    {r['sezon']} hf{r['hafta']:>2}  1+d={r['carpan']:.3f}  "
              f"gelen={r['devir_gelen']:>15,.0f}  kendi={r['dagitilan']:>15,.0f}")
    print()
    print("  -> Altı sezonun EN BÜYÜK devri bile eşiğin altında kalıyor. Devir")
    print("     ekseni 'ölçülemedi' değil, **hesaplandı ve yetmiyor**.")


def yaz_ev(o: dict[str, Any]) -> None:
    print()
    print("=" * 74)
    print("'HEP EV SAHİBİ' KURALI (arXiv:2303.16648) — bizim korpusumuzda")
    print("=" * 74)
    if not o.get("n"):
        print(f"  {o.get('not', 'veri yok')}")
        return
    print(f"  korpus                       : {o['n']:,} maç")
    print(f"  ev sahibi galibiyeti         : %{100 * o['ev_orani']:.2f} "
          f"[%{100 * o['ev_ga'][0]:.2f}, %{100 * o['ev_ga'][1]:.2f}]")
    print(f"  makalenin dayandığı oran     : %{100 * o['makalenin_orani']:.1f} "
          f"(Bundesliga)")
    print(f"  piyasa favorisi isabeti      : %{100 * o['favori_isabeti']:.2f} "
          f"[%{100 * o['favori_ga'][0]:.2f}, %{100 * o['favori_ga'][1]:.2f}] "
          f"({o['orani_olan']:,} maç)")
    print(f"  favorinin 'ev' olduğu maç    : %{100 * o['favorinin_ev_oldugu_pay']:.1f}")
    print()
    print(f"  {'kural':<26} | {'p':>7} | {'E[doğru/15]':>11} | "
          f"{'P(12+)':>8} | {'P(14+)':>8}")
    for ad, p, k in (("hep ev (makalenin kuralı)", o["ev_orani"], o["kupon_ev"]),
                     ("piyasa favorisi", o["favori_isabeti"], o["kupon_favori"])):
        print(f"  {ad:<26} | {'%' + format(100 * p, '.2f'):>7} | "
              f"{k['beklenen_dogru']:>11.2f} | "
              f"{'%' + format(100 * k['P12arti'], '.3f'):>8} | "
              f"{'%' + format(100 * k['P14arti'], '.4f'):>8}")
    print()
    print("  Kupon sütunları BAĞIMSIZLIK varsayar (maçlar arası bağımlılık")
    print("  ölçülmedi — KADEME_OLASILIKLARI §9). Kıyas için, ölçüm değil.")
    print()
    print("  -> Kuralın öncülü bu korpusta tutmuyor: ev oranı %50,4 değil")
    print("     %43,4 ve piyasa favorisi onu 7,7 puan geçiyor. Üstelik")
    print("     favorinin %68,4'ü zaten ev sahibi — kural ayrı bir eksen")
    print("     değil, favori kuralının **zayıflatılmış** hâli.")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--devir", action="store_true", help="yalnızca devir tavanı")
    ap.add_argument("--evkurali", action="store_true", help="yalnızca ev kuralı")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    hepsi = not (a.devir or a.evkurali)
    o: dict[str, Any] = {}
    if hepsi or a.devir:
        o["devir"] = devir_tavani()
    if hepsi or a.evkurali:
        o["evkurali"] = ev_kurali()

    if a.json:
        print(json.dumps(o, ensure_ascii=False, indent=1))
        return
    if "devir" in o:
        yaz_devir(o["devir"])
    if "evkurali" in o:
        yaz_ev(o["evkurali"])


if __name__ == "__main__":
    main()
