#!/usr/bin/env python3
"""Önceden yazılmış durma kuralları — bugün hangisi karşılandı.

Depoda iki tane **ölçümden önce yazılmış** durma kuralı var ve ikisi de
aynı kusura karşı kondu: bir haftanın kötü sonucuna bakıp modele elle
düzeltme koymak. İkisi de bugüne kadar sözle kontrol edildi — yani her
hafta, o haftanın kötü maçlarını hatırlayan biri tarafından. 5. hafta
ikisini birden gündeme getirdi (üç kaçağın üçü banko, ikisi orta favori
bandında) ve kuralların **koşulabilir** olmadığı görüldü.

Bu betik onları koşar. Karar vermez, yalnızca eşiğin neresinde
olduğumuzu yazar:

  1. **§3.64 — T1 banko `q` düzeltmesi.** 2025/26 + 2026/27 birlikte banko
     rejiminde `n ≥ 300`'e ulaşmalı VE havuzlanmış sapmanın Wilson %95
     aralığı söylenen `p`'yi tamamıyla dışarıda bırakmalı.
  2. **§3.65 — orta favori bandı (%40–55) düzeltmesi.** Canlı sezon
     birikimi `n ≥ 150`'ye ulaşmalı, bandın Wilson %95 aralığı piyasanın
     `p`'sini tamamıyla dışarıda bırakmalı VE aynı sapma 2025/26 arşivinde
     de görülmeli.

      python scripts/durma_kurallari.py
      python scripts/durma_kurallari.py --json

Banko rejiminin sınırı **kupon kesitinden** gelir (`karne.banko_yanliligi`,
T1 süzgeciyle ortanca `p_favori`), canlı sezondan değil: eşik canlı
sezonun kendi ortancasından kesilseydi her hafta yer değiştirirdi ve
havuzlama iki farklı rejimi toplamış olurdu.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.karne import (
    T1_DUZELTME_ESIGI,
    banko_yanliligi,
    canli_hafta,
)
from spor_toto.ortak import wilson

#: §3.65'in orta favori bandı ve canlı sezon eşiği.
ORTA_FAVORI_BANDI = (0.40, 0.55)
ORTA_FAVORI_ESIGI = 150

#: Canlı sezonun dizini; hafta dosyaları burada.
CANLI_SEZON = "2026_27"


def canli_satirlar(sezon: str = CANLI_SEZON) -> list[dict[str, Any]]:
    """Sonucu girilmiş canlı haftaların `(p_favori, lig, tuttu)` satırları.

    Lig kodu hafta dosyasından okunur; `canli_hafta` onu taşımıyor ve
    §3.64'ün kuralı T1'e özgü olduğu için gerekli.
    """
    out: list[dict[str, Any]] = []
    for hafta in range(1, 60):
        d = canli_hafta(sezon, hafta)
        if not d or not d["gercek"]:
            continue
        yol = (KOK / "data" / "super_toto" / sezon / f"hafta_{hafta:02d}.json")
        ligler = [m.get("league") for m in
                  json.loads(yol.read_text(encoding="utf-8"))["matches"]]
        for pr, gercek, lig in zip(d["probs"], d["gercek"], ligler):
            fav = max(pr, key=lambda k: pr[k])
            out.append({"hafta": hafta, "lig": lig, "p": pr[fav],
                        "tuttu": 1 if gercek == fav else 0})
    return out


def _ozet(satirlar: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(satirlar)
    if not n:
        return {"n": 0}
    k = sum(x["tuttu"] for x in satirlar)
    p = sum(x["p"] for x in satirlar) / n
    lo, hi = wilson(k, n)
    return {"n": n, "soylenen": p, "gerceklesen": k / n, "acik": k / n - p,
            "wilson": [lo, hi], "p_disinda": not (lo <= p <= hi)}


def banko_kurali(satirlar: list[dict[str, Any]]) -> dict[str, Any]:
    """§3.64 — T1 banko `q` düzeltmesi bugün uygulanabilir mi."""
    b = banko_yanliligi(ligler=["T1"])
    ref = next(k for k in b["kollar"] if k["yontem"] == b["referans"])
    esik_p = ref["banko_rejimi"]["alt_sinir"]
    arsiv = [s for s in b["sezonlar"] if s["sezon"] == "2025_26"]
    if not arsiv:
        return {"kural": "§3.64", "olculemedi": "2025/26 kupon kesitinde yok"}
    a = arsiv[0]
    canli = [x for x in satirlar if x["lig"] == "T1" and x["p"] >= esik_p]
    c = _ozet(canli)

    n = a["mac"] + c["n"]
    # Havuzlama: iki orneklemin ham sayilari. `gerceklesen` bir orandir,
    # tekrar maca cevrilir (arsiv tarafinda ham sayi disari cikmiyor).
    k = round(a["gerceklesen"] * a["mac"]) + round(c["gerceklesen"] * c["n"])
    p = (a["p"] * a["mac"] + c["soylenen"] * c["n"]) / n
    lo, hi = wilson(k, n)
    disinda = not (lo <= p <= hi)
    return {
        "kural": "§3.64 — T1 banko q duzeltmesi",
        "rejim_esigi_p": esik_p,
        "2025_26": {"n": a["mac"], "soylenen": a["p"],
                    "gerceklesen": a["gerceklesen"], "acik": a["acik"]},
        "2026_27": c,
        "havuzlanmis": {"n": n, "soylenen": p, "gerceklesen": k / n,
                        "acik": k / n - p, "wilson": [lo, hi],
                        "p_disinda": disinda},
        "esik_n": T1_DUZELTME_ESIGI,
        "n_yeterli": n >= T1_DUZELTME_ESIGI,
        "gecti": n >= T1_DUZELTME_ESIGI and disinda,
    }


def orta_favori_kurali(satirlar: list[dict[str, Any]]) -> dict[str, Any]:
    """§3.65 — orta favori bandı (%40–55) düzeltmesi bugün uygulanabilir mi."""
    lo_b, hi_b = ORTA_FAVORI_BANDI
    canli = _ozet([x for x in satirlar if lo_b <= x["p"] < hi_b])
    # Ikinci sart: ayni sapma 2025/26 arsivinde de gorunuyor mu. Arsiv
    # tarafi kupon kesitinden, ayni bant sinirlariyla.
    b = banko_yanliligi()
    ref = b["referans"]
    from spor_toto.karne import _favori_satirlari
    arsiv = _ozet([{"p": x["p_favori"], "tuttu": int(x["tuttu"])}
                   for x in _favori_satirlari(ref, korpus=False)
                   if x["sezon"] == "2025_26" and lo_b <= x["p_favori"] < hi_b])
    ayni_yon = bool(arsiv.get("n")) and arsiv["acik"] < 0 and canli["acik"] < 0
    return {
        "kural": "§3.65 — orta favori bandi duzeltmesi",
        "bant": [lo_b, hi_b],
        "2026_27": canli,
        "2025_26_arsiv": arsiv,
        "esik_n": ORTA_FAVORI_ESIGI,
        "n_yeterli": canli["n"] >= ORTA_FAVORI_ESIGI,
        "arsivde_de_var": ayni_yon,
        "gecti": (canli["n"] >= ORTA_FAVORI_ESIGI
                  and canli.get("p_disinda", False) and ayni_yon),
    }


def rapor(sezon: str = CANLI_SEZON) -> dict[str, Any]:
    satirlar = canli_satirlar(sezon)
    return {
        "canli_sezon": sezon,
        "canli_mac": len(satirlar),
        "canli_hafta": len({x["hafta"] for x in satirlar}),
        "kurallar": [banko_kurali(satirlar), orta_favori_kurali(satirlar)],
    }


def _satir(ad: str, o: dict[str, Any]) -> str:
    if not o.get("n"):
        return f"  {ad:<22} —  (kesit bos)"
    return (f"  {ad:<22} n={o['n']:>4}  soylenen %{100*o['soylenen']:.1f}  "
            f"gercek %{100*o['gerceklesen']:.1f}  acik {100*o['acik']:+.1f} puan"
            + (f"  Wilson [%{100*o['wilson'][0]:.1f}, %{100*o['wilson'][1]:.1f}]"
               if "wilson" in o else ""))


def yaz(o: dict[str, Any]) -> None:
    print("=" * 78)
    print(f"ONCEDEN YAZILMIS DURMA KURALLARI — canli sezon {o['canli_sezon']}, "
          f"{o['canli_hafta']} hafta / {o['canli_mac']} mac")
    print("=" * 78)
    for k in o["kurallar"]:
        print(f"\n{k['kural']}")
        if k.get("olculemedi"):
            print(f"  OLCULEMEDI: {k['olculemedi']}")
            continue
        if "havuzlanmis" in k:
            print(f"  banko rejimi siniri: p_favori >= {k['rejim_esigi_p']:.4f}"
                  "  (kupon kesitinin T1 ortancasi)")
            print(_satir("2025/26 (kupon)", k["2025_26"]))
            print(_satir("2026/27 (canli)", k["2026_27"]))
            print(_satir("HAVUZLANMIS", k["havuzlanmis"]))
            print(f"  esik n >= {k['esik_n']}: "
                  f"{'ULASILDI' if k['n_yeterli'] else 'ULASILMADI'}")
        else:
            print(f"  bant: %{100*k['bant'][0]:.0f}-%{100*k['bant'][1]:.0f}")
            print(_satir("2026/27 (canli)", k["2026_27"]))
            print(_satir("2025/26 (arsiv)", k["2025_26_arsiv"]))
            print(f"  esik n >= {k['esik_n']}: "
                  f"{'ULASILDI' if k['n_yeterli'] else 'ULASILMADI'}"
                  f"  ·  arsivde de ayni yonde: "
                  f"{'EVET' if k['arsivde_de_var'] else 'HAYIR'}")
        print(f"  >>> {'GECTI — duzeltme tartisilabilir' if k['gecti'] else 'GECMEDI — duzeltme YOK'}")
    print("\nKural gecmediyse yapilacak sey yoktur. Bu betigin isi kararin "
          "hatirlanmasini degil\nOLCULMESINI saglamak; esik sozle kontrol "
          "edilirse kotu bir hafta onu her zaman esner.")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default=CANLI_SEZON)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    o = rapor(a.sezon)
    print(json.dumps(o, ensure_ascii=False, indent=1)) if a.json else yaz(o)


if __name__ == "__main__":
    main()
