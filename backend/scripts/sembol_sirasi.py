#!/usr/bin/env python3
"""2.↔3. sembol sırası bilgi taşıyor mu — beraberlik en düşük olasılıkken.

Kupon kurulurken sorulan somut soru şudur: bir maçta beraberlik **üçüncü**
sıradaysa, ikinci sembolü üçüncüye tercih etmek bir bilgi mi, yoksa piyasanın
zaten söylediğini tekrar etmek mi? Ölçü basit: ikinci sıradaki sembolün gerçek
isabet oranı eksi üçüncününki (puan). Piyasa bu farkın ne kadar olacağını
zaten söylüyor (`beklenen`); **artık** ikisinin farkıdır ve asıl bakılan odur.

Kesit `acilis_*` sütunlarıdır — kapanış değil. Soru sıralamanın **maç
öncesinde** bilgi taşıyıp taşımadığı; kapanış piyasanın son sözüdür ve
sıralamayı zaten düzeltmiş olur.

Bantlama **beklenen fark** üzerindendir (2. olasılık eksi 3., puan), bahisçi
marjı üzerinden DEĞİL. Ayrım önemli: soru "piyasa iki sembolü ne kadar
ayırıyor" olduğunda bant o ayrımın kendisi olmalı, fiyatın şişkinliği değil.

Kullanım:

    python scripts/sembol_sirasi.py                      # varsayilan korpus
    python scripts/sembol_sirasi.py <korpus.csv>         # baska bir kesit
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.odds import implied_probs

VARSAYILAN_KORPUS = KOK / "data" / "egitim" / "egitim_korpus.csv"

#: Beklenen farkın (2. − 3., puan) bantları.
BANTLAR: tuple[str, ...] = ("<2", "2-4", ">=4")


def _bant(fark_puan: float) -> str:
    if fark_puan < 2:
        return "<2"
    return "2-4" if fark_puan < 4 else ">=4"


def olc(yol: Path | str | None = None) -> dict[str, dict[str, float]]:
    """Bant bant: n, 2./3. isabet, gerçek fark, beklenen fark, artık."""
    p = Path(yol) if yol else VARSAYILAN_KORPUS
    kova: dict[str, list[tuple[bool, bool, float, float]]] = {b: [] for b in BANTLAR}
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                o = {s: float(r[f"acilis_{s}"]) for s in ("1", "0", "2")}
            except (KeyError, TypeError, ValueError):
                continue
            if any(v <= 1.0 for v in o.values()):
                continue
            olasilik = implied_probs(o, "shin")
            sira = sorted(olasilik, key=lambda s: -olasilik[s])
            if sira[2] != "0":      # beraberlik 3. sirada DEGILSE bu soru sorulmaz
                continue
            ikinci, ucuncu = olasilik[sira[1]], olasilik[sira[2]]
            kova[_bant((ikinci - ucuncu) * 100)].append(
                (r["kod"] == sira[1], r["kod"] == sira[2], ikinci, ucuncu))

    out: dict[str, dict[str, float]] = {}
    for ad, v in kova.items():
        if not v:
            continue
        n = len(v)
        h2 = 100 * sum(a for a, _, _, _ in v) / n
        h3 = 100 * sum(b for _, b, _, _ in v) / n
        bek = 100 * sum(x - y for _, _, x, y in v) / n
        out[ad] = {"n": n, "isabet_2": h2, "isabet_3": h3,
                   "fark": h2 - h3, "beklenen": bek, "artik": (h2 - h3) - bek}
    return out


def _main() -> int:
    sonuc = olc(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"{'bant':>5} {'n':>7} {'2.isabet':>9} {'3.isabet':>9} "
          f"{'FARK':>7} {'beklenen':>9} {'artik':>7}")
    for ad in BANTLAR:
        s = sonuc.get(ad)
        if not s:
            continue
        print(f"{ad:>5} {int(s['n']):7,} {s['isabet_2']:8.1f}% {s['isabet_3']:8.1f}% "
              f"{s['fark']:+7.1f} {s['beklenen']:+9.1f} {s['artik']:+7.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
