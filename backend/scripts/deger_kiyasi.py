"""Değer kuralı ↔ bugünkü kural — GERÇEK ikramiye tablolarına karşı.

    python scripts/deger_kiyasi.py                 # tam kıyas
    python scripts/deger_kiyasi.py --odul 3000000  # tek ödül değeri
    python scripts/deger_kiyasi.py --json

─── Soru ─────────────────────────────────────────────────────────────────

Bugünkü kural (`secim.en_iyi_secim`) sabit bir bütçe altında `P(k ≤ 3)`'ü
enbüyüklüyor. O amaç üçlü sayısında **monoton** olduğu için bütçe
elverdiğince üçlü alıyor ve kupon şekli haftaya değil **bütçeye** göre
belirleniyor (README §1.1). İtiraz haklı: doğru olan, her sembolün
**bedelini ödemesi** — bir maçı çifteye çıkarmak kuponu iki katına çıkarır
ve bunu ancak kazandırdığı olasılık o parayı hak ediyorsa yapmalı.

`secim.deger_secim` bunu kuruyor:

    net = P(k ≤ esik) · odul_tl − bedel · KOLON_BEDELI

Bu betik `odul_tl`yi süpürüp her değerin **114 hafta** boyunca gerçekten ne
kazandırdığını ölçer. Ölçüm varsayımsızdır: kalabalık modeli, havuz
bölüşümü, `E[TL]` yok — yalnızca `karne.gercek_kolon_dagilimi` ile sayılan
kolonlar ve resmî ödül tablosundaki karşılıkları.

─── Okuma uyarısı — bu tablonun "en iyi satırı" YOKTUR ───────────────────

Getiri dağılımı **ağır kuyrukludur**: 114 haftanın büyük çoğunluğu para
kaybeder ve toplam birkaç haftadan gelir. Ödül taraması bu yüzden düzgün
bir eğri değil, gürültülü bir seridir; en yüksek ROI'li satırı "optimum"
diye okumak, hangi haftaların tuttuğuna uydurmaktır. Betik o yüzden her
satırın yanına **kaç haftada daha iyi olduğunu** basar ve kıyası
eşleştirilmiş bootstrap ile sınar. Projenin geçme kuralı aynı: aralığın
tamamı sıfırın bir yanında olmalı.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spor_toto.getiri import KOLON_BEDELI
from spor_toto.karne import (
    gercek_kolon_dagilimi,
    gercek_odul,
    kupon_kesiti,
)
from spor_toto.secim import (
    DEGER_TAVANI,
    VARSAYILAN_KACAK_ESIGI,
    deger_secim,
    sistem_secimi,
)

#: Taranan ödül değerleri (TL) — "hedefi tutturmak kaç lira eder".
ODUL_IZGARA: tuple[float, ...] = (
    20_000.0, 50_000.0, 100_000.0, 200_000.0, 500_000.0,
    1_000_000.0, 3_000_000.0,
)

#: Bugünkü kuralın kıyasa giren tavanları (TL).
TAVAN_IZGARA: tuple[float, ...] = (2_000.0, 210_000.0)

BOOTSTRAP = 20_000


def _haftalik(kesit: list[dict[str, Any]], planlar: list[Any]
              ) -> list[tuple[float, float, int, tuple[int, int, int]]]:
    """Hafta başına `(maliyet, gerçek ödül, kolon, şekil)`.

    Ödülü **olmayan** hafta atlanmaz: hafta oynandı, parası ödendi, ödülü
    sıfır. Atlamak sonuca göre eleme olur ve geri dönüşü sistematik olarak
    yukarı kaydırır (`karne.taban_gevsekligi` aynı gerekçeyi taşıyor).
    """
    out = []
    for h, p in zip(kesit, planlar, strict=True):
        if p is None:
            continue
        dagilim = gercek_kolon_dagilimi(p.secimler, h["gercek"]) or {}
        out.append((
            p.bedel * KOLON_BEDELI,
            gercek_odul(dagilim, h["tablo"]) or 0.0,
            p.bedel,
            (p.banko, p.cift, p.uclu),
        ))
    return out


def _roi(satirlar: list[tuple[float, float, int, tuple[int, int, int]]],
         idx: list[int] | None = None) -> float:
    dizi = range(len(satirlar)) if idx is None else idx
    maliyet = sum(satirlar[i][0] for i in dizi)
    return sum(satirlar[i][1] for i in dizi) / maliyet if maliyet else 0.0


def _ozet(satirlar: list[tuple[float, float, int, tuple[int, int, int]]]) -> dict[str, Any]:
    n = len(satirlar)
    sekiller: dict[tuple[int, int, int], int] = {}
    for _, _, _, s in satirlar:
        sekiller[s] = sekiller.get(s, 0) + 1
    return {
        "hafta": n,
        "maliyet": sum(x[0] for x in satirlar),
        "odul": sum(x[1] for x in satirlar),
        "roi": _roi(satirlar),
        "kolon_ort": sum(x[2] for x in satirlar) / n if n else 0.0,
        "sekil_sayisi": len(sekiller),
        "odullu_hafta": sum(1 for x in satirlar if x[1] > 0),
        "tavana_dayanan": sum(1 for x in satirlar if x[2] >= DEGER_TAVANI),
    }


def _bootstrap(a: list[Any], b: list[Any], tohum: int = 42) -> dict[str, Any]:
    """`b − a` ROI farkının eşleştirilmiş bootstrap aralığı.

    Eşleştirilmiş: aynı hafta indeksleri iki kurala da uygulanır, yani
    haftanın kolay/zor olması farktan düşer.
    """
    rnd = random.Random(tohum)
    n = len(a)
    farklar = []
    for _ in range(BOOTSTRAP):
        idx = [rnd.randrange(n) for _ in range(n)]
        farklar.append(_roi(b, idx) - _roi(a, idx))
    farklar.sort()
    lo = farklar[int(0.025 * BOOTSTRAP)]
    hi = farklar[int(0.975 * BOOTSTRAP)]
    return {
        "fark": _roi(b) - _roi(a),
        "alt": lo, "ust": hi,
        # Projenin gecme kurali: araligin TAMAMI sifirin bir yaninda.
        "gecti": lo > 0 or hi < 0,
        "daha_iyi_hafta": sum(1 for x, y in zip(a, b, strict=True)
                              if y[1] - y[0] > x[1] - x[0]),
        "esit_hafta": sum(1 for x, y in zip(a, b, strict=True)
                          if y[1] - y[0] == x[1] - x[0]),
    }


def kiyas(oduller: tuple[float, ...] = ODUL_IZGARA,
          tavanlar: tuple[float, ...] = TAVAN_IZGARA,
          esik: int = VARSAYILAN_KACAK_ESIGI) -> dict[str, Any]:
    """Bugünkü kural ↔ değer kuralı, gerçek ödül tablolarına karşı."""
    kesit = kupon_kesiti()
    bugun = {
        tl: _haftalik(kesit, [sistem_secimi(h["probs"], tl) for h in kesit])
        for tl in tavanlar
    }
    deger = {
        odul: _haftalik(kesit, [deger_secim(h["probs"], odul, esik=esik)
                                for h in kesit])
        for odul in oduller
    }
    # Kiyas ESLESIK BEDELE gore kurulur: her tavan icin, bedeli ona en yakin
    # odul satiri secilir. Farkli parayla kosan iki kurali yan yana koymak,
    # bu deponun README §1.1'de duzelttigi hatanin ta kendisiydi.
    kiyaslar = []
    for tl, a in bugun.items():
        hedef_kolon = _ozet(a)["kolon_ort"]
        en_yakin = min(deger, key=lambda o: abs(_ozet(deger[o])["kolon_ort"] - hedef_kolon))
        kiyaslar.append({
            "tavan_tl": tl, "odul_tl": en_yakin,
            "bugun": _ozet(a), "deger": _ozet(deger[en_yakin]),
            "sinav": _bootstrap(a, deger[en_yakin]),
        })
    return {
        "hafta": len(kesit),
        "kolon_bedeli": KOLON_BEDELI,
        "bugun": {tl: _ozet(v) for tl, v in bugun.items()},
        "deger": {o: _ozet(v) for o, v in deger.items()},
        "kiyas": kiyaslar,
        "uyari": (
            "Odul taramasinin EN IYI SATIRI YOKTUR: getiri agir kuyruklu, "
            "toplam birkac haftadan geliyor ve en yuksek ROI'li satiri "
            "optimum saymak hangi haftalarin tuttuguna uydurmaktir. "
            "Okunacak sey `sinav` blogudur."
        ),
    }


def _yaz(r: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print(f"\nDEGER KIYASI — {r['hafta']} hafta · gercek odul tablolari · "
          f"kolon TL{r['kolon_bedeli']:.0f}\n")
    print(f"{'kural':>24} {'maliyet TL':>14} {'odul TL':>14} {'ROI':>7} "
          f"{'kolon/hf':>9} {'sekil':>6} {'odullu':>7}")
    for tl, o in r["bugun"].items():
        ad = f"bugun tavan {int(tl):,}"
        print(f"{ad:>24} {o['maliyet']:>14,.0f} {o['odul']:>14,.0f} "
              f"{o['roi']:>7.3f} {o['kolon_ort']:>9,.0f} {o['sekil_sayisi']:>6} "
              f"{o['odullu_hafta']:>7}")
    for odul, o in r["deger"].items():
        ad = f"deger odul {int(odul):,}"
        tav = f" (tavana dayanan {o['tavana_dayanan']})" if o["tavana_dayanan"] else ""
        print(f"{ad:>24} {o['maliyet']:>14,.0f} {o['odul']:>14,.0f} "
              f"{o['roi']:>7.3f} {o['kolon_ort']:>9,.0f} {o['sekil_sayisi']:>6} "
              f"{o['odullu_hafta']:>7}{tav}")

    print("\nESLESIK BEDELDE SINAV (eslestirilmis bootstrap, %95):")
    for c in r["kiyas"]:
        s = c["sinav"]
        print(f"  tavan {int(c['tavan_tl']):,} TL  <->  odul {int(c['odul_tl']):,} TL")
        print(f"    ROI {c['bugun']['roi']:.3f} -> {c['deger']['roi']:.3f}  "
              f"fark {s['fark']:+.3f}  %95 [{s['alt']:+.3f}, {s['ust']:+.3f}]  "
              f"-> {'GECTI' if s['gecti'] else 'GECMEDI'}")
        print(f"    haftalik net karda deger {s['daha_iyi_hafta']} haftada daha iyi, "
              f"{s['esit_hafta']} esit, "
              f"{c['bugun']['hafta'] - s['daha_iyi_hafta'] - s['esit_hafta']} daha kotu")
    print(f"\n{r['uyari']}")


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--odul", type=float, action="append",
                    help="taranacak odul degeri (TL); birden cok kez verilebilir")
    ap.add_argument("--esik", type=int, default=VARSAYILAN_KACAK_ESIGI)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = kiyas(tuple(a.odul) if a.odul else ODUL_IZGARA, esik=a.esik)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
    else:
        _yaz(r)


if __name__ == "__main__":  # pragma: no cover
    main()
