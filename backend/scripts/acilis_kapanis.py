#!/usr/bin/env python3
"""Açılış oranı mı kapanış oranı mı? — arşivde ölçer, iddia etmez.

football-data arşivi her maç için iki fiyat taşır: `AvgH/D/A` açılış,
`AvgCH/CD/CA` kapanış. Bu script ikisini karşılaştırır:

  1. Brier ve favori isabeti — hangisi daha doğru?
  2. Hareket bilgi taşıyor mu? Fiyat açılıştan kapanışa kayınca,
     gerçekleşme oranı açılışı mı kapanışı mı takip ediyor?
  3. Kuralın kendisi hangi fiyatla beslenirse ne oluyor?

NEDEN ÖNEMLİ: Spor Toto kuponu ilk maçtan önce kapanır, ama her maçın
oranı kendi başlama saatine kadar oynar. Yani haftanın son maçları için
KAPANIŞ oranı kupon verildiğinde HENÜZ YOKTUR. Bu script, elde olmayan
fiyatın ne kadar değerli olduğunu ölçer.

    python scripts/acilis_kapanis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.backtest import _en_iyi_skor, _kaplama, secim_uret  # noqa: E402
from spor_toto.history import normalized_weeks  # noqa: E402
from spor_toto.odds import implied_probs, load_odds, market_odds  # noqa: E402

SEM = ("1", "0", "2")
#: Kapanış - açılış farkının (puan) bantları. Orta bant "hareket yok".
HAREKET_BANTLARI = ((-99, -4), (-4, -2), (-2, -0.5), (-0.5, 0.5),
                    (0.5, 2), (2, 4), (4, 99))


def ciftler():
    """Hem açılış hem kapanış fiyatı olan maçlar."""
    out = []
    for r in load_odds():
        if not r.get("matched"):
            continue
        ac = market_odds(r, "1X2", "Avg", closing=False)
        ka = market_odds(r, "1X2", "Avg", closing=True)
        if len(ac) != 3 or len(ka) != 3:
            continue
        if any(v <= 1 for v in list(ac.values()) + list(ka.values())):
            continue
        out.append((r, implied_probs(ac), implied_probs(ka), ac, ka))
    return out


def brier(p, kod):
    return sum((p[s] - (1.0 if s == kod else 0.0)) ** 2 for s in SEM)


def dogruluk(rows):
    n = len(rows)
    ba = sum(brier(pa, r["code"]) for r, pa, _, _, _ in rows) / n
    bk = sum(brier(pk, r["code"]) for r, _, pk, _, _ in rows) / n
    fa = sum(1 for r, _, _, oa, _ in rows if min(oa, key=oa.get) == r["code"])
    fk = sum(1 for r, _, _, _, ok in rows if min(ok, key=ok.get) == r["code"])
    degisen = [x for x in rows
               if min(x[3], key=x[3].get) != min(x[4], key=x[4].get)]
    return {"n": n, "brier_acilis": ba, "brier_kapanis": bk,
            "fav_acilis": fa, "fav_kapanis": fk,
            "degisen": len(degisen),
            "degisen_ac_hakli": sum(1 for r, _, _, oa, _ in degisen
                                    if min(oa, key=oa.get) == r["code"]),
            "degisen_ka_hakli": sum(1 for r, _, _, _, ok in degisen
                                    if min(ok, key=ok.get) == r["code"])}


def hareket(rows):
    """Fiyat kayınca gerçekleşme hangi fiyatı takip ediyor."""
    out = []
    for lo, hi in HAREKET_BANTLARI:
        g = []
        for r, pa, pk, _, _ in rows:
            for s in SEM:
                d = 100 * (pk[s] - pa[s])
                if lo <= d < hi:
                    g.append((r["code"] == s, pa[s], pk[s]))
        if len(g) < 20:
            continue
        n = len(g)
        out.append({"lo": lo, "hi": hi, "n": n,
                    "acilis": 100 * sum(x[1] for x in g) / n,
                    "kapanis": 100 * sum(x[2] for x in g) / n,
                    "gercek": 100 * sum(1 for x in g if x[0]) / n})
    return out


def kural_kosusu(closing: bool):
    """Aynı strateji, farklı fiyatla beslenirse."""
    P = {}
    for r in load_odds():
        if not r.get("matched"):
            continue
        o = market_odds(r, "1X2", "Avg", closing=closing)
        if len(o) != 3 or any(v <= 1 for v in o.values()):
            continue
        P.setdefault(r["week"], {})[r["no"]] = implied_probs(o)

    n = h14 = h13 = h12 = kolon = 0
    for w in normalized_weeks(None):
        blok = P.get(w["week"], {})
        if len(blok) != 15:
            continue
        gercek = w["results"]
        sec = [secim_uret(blok[i + 1], 0.68, 0.38) for i in range(15)]
        var = [i for i, s in enumerate(sec) if len(s) > 1]
        sizes = tuple(len(sec[i]) for i in var)
        duzen = sorted(range(len(sizes)), key=lambda j: (sizes[j], j))
        kap = _kaplama(tuple(sizes[j] for j in duzen))
        if kap is None:
            continue
        n += 1
        bd = sum(1 for i, s in enumerate(sec) if len(s) == 1 and s[0] == gercek[i])
        nokta = [sec[var[j]].index(gercek[var[j]])
                 if gercek[var[j]] in sec[var[j]] else -1 for j in duzen]
        en_iyi = bd + _en_iyi_skor(kap, nokta)
        h14 += en_iyi >= 14
        h13 += en_iyi >= 13
        h12 += en_iyi >= 12
        kolon += kap["columns"]
    return {"hafta": n, "h14": h14, "h13": h13, "h12": h12,
            "kolon_ort": kolon / n if n else 0}


def main() -> None:
    rows = ciftler()
    d = dogruluk(rows)
    print(f"\n{'='*74}\nAÇILIŞ ↔ KAPANIŞ — {d['n']} maç (2025/26 arşivi)\n{'='*74}")
    print(f"Brier   açılış {d['brier_acilis']:.4f} · kapanış {d['brier_kapanis']:.4f}"
          f"  → kapanış %{100*(d['brier_acilis']-d['brier_kapanis'])/d['brier_acilis']:.2f} daha iyi")
    print(f"Favori  açılış {d['fav_acilis']}/{d['n']} (%{100*d['fav_acilis']/d['n']:.1f}) · "
          f"kapanış {d['fav_kapanis']}/{d['n']} (%{100*d['fav_kapanis']/d['n']:.1f})")
    print(f"Favori değişen maç: {d['degisen']} — açılış {d['degisen_ac_hakli']}, "
          f"kapanış {d['degisen_ka_hakli']} kez haklı")

    print(f"\n─── HAREKET BİLGİ TAŞIYOR MU ────────────────────────────────────────")
    print(f'{"hareket (puan)":<18}{"gözlem":>8}{"açılış":>10}{"kapanış":>10}{"gerçek":>10}  kim haklı')
    for h in hareket(rows):
        fark_ac = abs(h["gercek"] - h["acilis"])
        fark_ka = abs(h["gercek"] - h["kapanis"])
        kim = "kapanış" if fark_ka < fark_ac - 0.3 else ("açılış" if fark_ac < fark_ka - 0.3 else "berabere")
        etiket = f'{h["lo"]:+.1f} … {h["hi"]:+.1f}'
        print(f'{etiket:<18}{h["n"]:>8}{h["acilis"]:>9.1f}%{h["kapanis"]:>9.1f}%'
              f'{h["gercek"]:>9.1f}%  {kim}')

    print(f"\n─── KURAL HANGİ FİYATLA BESLENİRSE ──────────────────────────────────")
    print(f'{"fiyat":<12}{"hafta":>6}{"14":>4}{"13":>4}{"12":>4}{"kolon/hafta":>13}')
    for ad, c in (("AÇILIŞ", False), ("KAPANIŞ", True)):
        r = kural_kosusu(c)
        print(f'{ad:<12}{r["hafta"]:>6}{r["h14"]:>4}{r["h13"]:>4}{r["h12"]:>4}'
              f'{r["kolon_ort"]:>13,.0f}')


if __name__ == "__main__":
    main()
