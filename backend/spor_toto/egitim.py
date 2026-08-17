"""Eğitim korpusu okuyucusu — tahmin katmanının maç evreni.

**Bu modül istatistik katmanının parçası değildir.** `/istatistik` sayfası ve
`/api/stats` Spor Toto kuponunun sezonunu anlatır; burada okunan korpus
yalnızca **tahminciyi eğitmek ve ölçmek** içindir. Ayrım kasıtlıdır ve
`tests/test_egitim.py::test_ayrim_*` ile bekçiye bağlanmıştır: istatistik
katmanı bu modülü import etmez, korpustan hiçbir sayı `/api/stats` gövdesine
girmez.

Korpus `scripts/build_egitim.py` tarafından üretilir (football-data.co.uk,
22 lig × 4 geçmiş sezon, ~31 bin maç). Kupon değerlendirme setinin 58 katı
büyüklüğünde ve **kupon bileşimi taşımaz** — bir tahminciyi ölçmek için
gereken üçlü `(maç, oran, sonuç)` olduğu için buna gerek de yoktur.

Gruplama: maçlar ISO takvim haftasına göre sözde-haftalara toplanır. Sebep
`evaluate`'in bootstrap kuralıyla aynı — aynı hafta sonu oynanan maçlar
bağımsız değildir, güven aralığı hafta üzerinden kurulmalıdır.

**Sezon alanı taşınır ve önemlidir.** Korpusun asıl işi sezon dışarıda
bırakmalı ölçüm: bir sezonda eğit, hiç görmediğin başka bir sezonda ölç.
Leave-one-week-out'un veremediği gerçek out-of-sample budur.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .odds import implied_probs

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_KORPUS = KOK / "data" / "egitim" / "egitim_korpus.csv"

#: Bir sözde-haftanın karşılaştırmaya girmesi için gereken en az maç. Altında
#: hafta düzeyinde ortalama kendi gürültüsünü ölçer.
EN_AZ_MAC = 5


@lru_cache(maxsize=2)
def korpus_yukle(yol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Korpus satırlarını oku. Dosya yoksa boş liste (çağıran karar verir)."""
    p = Path(yol) if yol else VARSAYILAN_KORPUS
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                oranlar = {s: float(r[f"oran_{s}"]) for s in ("1", "0", "2")}
            except (KeyError, TypeError, ValueError):
                continue
            if any(v <= 1.0 for v in oranlar.values()):
                continue
            out.append({
                "sezon": r["sezon"],
                "lig": r["lig"],
                "tarih": r["tarih"],
                "iso_yil": int(r["iso_yil"]),
                "iso_hafta": int(r["iso_hafta"]),
                "ev": r["ev"],
                "dep": r["dep"],
                "kod": r["kod"],
                "oranlar": oranlar,
            })
    return out


def sezonlar() -> List[str]:
    """Korpustaki sezonlar, kronolojik."""
    return sorted({r["sezon"] for r in korpus_yukle()})


def korpus_haftalari(sezonlar_: Optional[Sequence[str]] = None,
                     ligler: Optional[Sequence[str]] = None,
                     en_az_mac: int = EN_AZ_MAC,
                     yol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Korpusu `evaluate` koşumunun beklediği hafta girdilerine çevir.

    Dönen her kayıt `backtest.hafta_girdileri()` ile aynı sözleşmeyi taşır
    (`results`, `probs`, `usable`, …) artı iki alan:

        sezon        sezon dışarıda bırakmalı ölçüm için grup anahtarı
        ozellikler   maç başına lig / favori / favori oranı

    `ozellikler` modelin özellik üretmesi içindir; korpus **olguyu** taşır,
    özelliği model türetir (`recalibrate._mac_ozellikleri`). Bu ayrım
    sayesinde aynı tahminci hem kupon haftalarında hem korpusta çalışır.
    """
    satirlar = korpus_yukle(yol)
    if sezonlar_ is not None:
        izin = set(sezonlar_)
        satirlar = [r for r in satirlar if r["sezon"] in izin]
    if ligler is not None:
        izin_lig = set(ligler)
        satirlar = [r for r in satirlar if r["lig"] in izin_lig]

    gruplar: Dict[Any, List[Dict[str, Any]]] = {}
    for r in satirlar:
        gruplar.setdefault((r["sezon"], r["iso_yil"], r["iso_hafta"]), []).append(r)

    out: List[Dict[str, Any]] = []
    for (sezon, yil, hafta), grup in sorted(gruplar.items()):
        if len(grup) < en_az_mac:
            continue
        grup.sort(key=lambda r: (r["tarih"], r["lig"], r["ev"]))
        probs: List[Dict[str, float]] = []
        ozellikler: List[Dict[str, Any]] = []
        for r in grup:
            olasilik = implied_probs(r["oranlar"])
            probs.append(olasilik)
            favori = min(r["oranlar"], key=lambda s: r["oranlar"][s])
            ozellikler.append({
                "lig": r["lig"],
                "favori": favori,
                "favori_oran": r["oranlar"][favori],
            })
        out.append({
            "week": yil * 100 + hafta,
            "close_date": grup[-1]["tarih"],
            "sezon": sezon,
            "results": "".join(r["kod"] for r in grup),
            "probs": probs,
            "ozellikler": ozellikler,
            "missing": 0,
            "usable": True,
        })
    return out


def ozet(yol: Optional[str] = None) -> Dict[str, Any]:
    """Korpusun tanılama özeti — rapor ve test için."""
    satirlar = korpus_yukle(yol)
    haftalar = korpus_haftalari(yol=yol)
    return {
        "mac": len(satirlar),
        "sezon": sorted({r["sezon"] for r in satirlar}),
        "lig": len({r["lig"] for r in satirlar}),
        "hafta": len(haftalar),
        "kod_dagilimi": {k: sum(1 for r in satirlar if r["kod"] == k)
                         for k in ("1", "0", "2")},
    }
