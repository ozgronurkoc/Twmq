"""Şehir ve derbi — `TURETILEMEYEN` listesinden bir madde düştü (Faz 3.4).

`disari.TURETILEMEYEN` iki maddeyi kapalı tutuyordu:

    seyahat   sehir/koordinat yok
    derbi     sehir eslemesi ya da rekabet tablosu yok; elle liste yazmak
              turetme degil kuratorluk olurdu

İkinci cümle **doğruydu ve kapıyı kapatmıyordu**. Elle liste yazmak
kuratörlüktür; kamuya açık bir kaynaktan şehir okumak türetmedir.
`scripts/build_sehir.py` o tabloyu `openfootball/clubs`tan (CC0) üretiyor —
604 takımın 592'si, **%98,0**.

**`seyahat` hâlâ kapalı** ve gerekçesi değişti: artık "şehir yok" değil,
*"koordinat yok"*. İki şehrin arasındaki mesafe şehir adından çıkmaz.
Liste kısaldı, boşalmadı — ve bu ayrım `disari.py`de yazılı.

─── Derbi neden bir "yön" özelliği değil ────────────────────────────────

Projedeki bütün A3 özellikleri *"pozitif = ev lehine"* diye kurulur. Derbi
öyle değildir: aynı şehirde oynanan bir maç iki tarafa da aynı şeyi yapar.
İddia yön değil **şekil**dir: derbide beraberlik oranı ve sürpriz olasılığı
farklı olabilir. Bu yüzden `derbi` bir gösterge (0/1) olarak girer ve
`dagilim` basamağındaki `ayrisma` gibi bir **sıcaklık** değişkeni olarak
okunur:

    z_s = (β + δ·derbi)·ln p_s

    δ < 0   derbide piyasanın güvenini AZALT (sürpriz daha olası)
    δ ≈ 0   derbi bir şey söylemiyor
    δ > 0   derbide güveni artır (beklenmez; çıkarsa açıklama gerekir)

Yön sütunu (derbide kim avantajlı) **bilerek yok**: ev avantajı zaten
`bias`ta, takım gücü `elo`da. Derbinin ayrı bir iddiası varsa o iddia
belirsizlik hakkındadır.

─── Şehri bilinmeyen takım ──────────────────────────────────────────────

Kaynak bazı kulüplerin şehrini hiç yazmıyor (12 takım). O maçlarda
`derbi_bilinir` `False`, `derbi` `0.0` olur. **Bilinmeyeni "derbi değil"
saymak** kasıtlı ve tek yönlü bir hata: derbi olmayan maçların ezici
çoğunluğunda doğru, derbi olanların birkaçında eksik. Tersi — bilinmeyeni
derbi saymak — çok daha zararlı olurdu.
"""
from __future__ import annotations

import csv
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_TABLO = KOK / "data" / "sehir" / "sehir_tablosu.csv"


@lru_cache(maxsize=2)
def sehir_tablosu(yol: str | None = None) -> dict[str, str]:
    """`{takim: sehir}`. Dosya yoksa **boş** — çağıran karar verir.

    Anahtar takım adıdır, `(lig, takim)` değil: aynı takım iki sezonda iki
    ligde olabilir (küme düşme/çıkma) ve şehri değişmez. Ad çakışması
    ölçüldü: korpusta aynı ada sahip iki farklı kulüp yok.
    """
    p = Path(yol) if yol else VARSAYILAN_TABLO
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            takim = (r.get("takim") or "").strip()
            sehir = (r.get("sehir") or "").strip()
            if takim and sehir:
                out[takim] = sehir
    return out


def derbi_mi(ev: str, dep: str, tablo: dict[str, str] | None = None
             ) -> tuple[bool, bool]:
    """`(derbi, bilinir)` — aynı şehir mi, ve cevap **biliniyor** mu.

    İki değer birden döner çünkü *"derbi değil"* ile *"bilmiyorum"* farklı
    şeylerdir ve karıştırılırsa özellik sessizce seyrelir.
    """
    t = sehir_tablosu() if tablo is None else tablo
    a, b = t.get(ev), t.get(dep)
    if a is None or b is None:
        return False, False
    return a == b, True


def kapsama(satirlar: Sequence[dict[str, Any]],
            yol: str | None = None) -> dict[str, Any]:
    """Korpusun ne kadarında derbi sorusu **cevaplanabiliyor** ve kaçı derbi."""
    tablo = sehir_tablosu(yol)
    if not tablo:
        return {"takim": 0, "sehir": 0, "bilinen_mac": 0, "derbi": 0,
                "oran": 0.0, "derbi_orani": 0.0}
    bilinen = derbi = 0
    for r in satirlar:
        d, b = derbi_mi(r["ev"], r["dep"], tablo)
        bilinen += int(b)
        derbi += int(d)
    n = len(satirlar)
    return {"takim": len(tablo), "sehir": len(set(tablo.values())),
            "bilinen_mac": bilinen, "derbi": derbi,
            "oran": (bilinen / n) if n else 0.0,
            "derbi_orani": (derbi / bilinen) if bilinen else 0.0}


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    from .egitim import korpus_yukle

    k = kapsama(korpus_yukle())
    if a.json:
        print(json.dumps(k, ensure_ascii=False, indent=1))
        return
    print(f"\nSEHIR TABLOSU — {k['takim']} takim · {k['sehir']} sehir")
    print(f"Korpusun {k['bilinen_mac']:,} macinda ({k['oran']:.1%}) derbi "
          f"sorusu cevaplanabiliyor.")
    print(f"Bunlarin {k['derbi']:,}'i ({k['derbi_orani']:.2%}) ayni sehirde.")
    if not k["takim"]:
        print("\nTablo yok — `python scripts/build_sehir.py`")


if __name__ == "__main__":  # pragma: no cover
    main()
