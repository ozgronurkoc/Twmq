#!/usr/bin/env python3
"""Yaklaşan maçlar ve oranları — tahmin ürününün girdisi.

**Neden ayrı bir kaynak.** `build_egitim.py` ve `build_odds.py` geriye dönük
çalışır: sonucu belli maçları toplar. Tahmin ürünü ise **henüz oynanmamış**
maça olasılık vermek zorunda ve oynanmamış maçın hiçbir arşivde oranı yok.

Kaynak football-data.co.uk'in `fixtures.csv` dosyasıdır ve seçim kasıtlıdır:
**ölçümü yaptığımız kaynağın ta kendisi.** Kupon setinde ölçülen isabet
(Brier 0,5740 · maç başına %55,6) aynı fiyatlayıcıya ait olduğu için ürüne
meşru biçimde taşınabilir. İddaa bülteninden üretilen olasılık da bir
tahmindir ama **kalibrasyonu ölçülmemiştir** (marj %17,2'ye karşı %7,26) ve
o yüzden burada ikinci sıradadır.

**Dosya yuvarlanan bir penceredir.** football-data yalnızca önümüzdeki birkaç
günün fikstürünü yayınlar; hafta oynandıkça satırlar düşer. Dolayısıyla
"yaklaşan maç yok" **normal bir durumdur, hata değildir** — ve script bunu
boş dosya yazarak değil, açıkça söyleyerek bildirir (doktrin 4: çelişki ve
eksik gizlenmez).

**Oranlar AÇILIŞ oranıdır** ve bunun bedeli ölçülmüştür: A1'de açılış çizgisi
31.099 maçta Brier 0,5964, kapanış 0,5940 — aradaki fark +0,0025. Yani maç
öncesi verilen bir tahmin, maç saatinde verilecek olandan **ölçülebilir
biçimde** biraz kötüdür. Bu sayı ürün gövdesinde taşınır.

Kullanım:

    python scripts/build_fixtures.py            # indir, dogrula, yaz
    python scripts/build_fixtures.py --dry-run  # yazmadan ozet
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_CIKTI = KOK / "data" / "fixtures"

UA = "Mozilla/5.0 (compatible; spor-toto-lab/1.0)"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"

#: Oran kaynagi tercihi. `Avg` once gelir cunku olcum onun uzerinde yapildi
#: (`egitim.py` korpusu `Avg`/`AvgC` ailesini tercih eder).
KAYNAK_SIRASI: Tuple[str, ...] = ("Avg", "B365", "PS", "Max")

#: Korpusun tasidigi ligler — olculen isabet bu evrene ait. Disindaki bir lig
#: icin tahmin uretilebilir ama olculmus isabet ONA AIT DEGILDIR, o yuzden
#: ayri isaretlenir.
OLCULEN_LIGLER: Tuple[str, ...] = (
    "E0", "E1", "E2", "E3", "EC",
    "SC0", "SC1", "SC2", "SC3",
    "D1", "D2", "I1", "I2", "SP1", "SP2",
    "F1", "F2", "N1", "B1", "P1", "T1", "G1",
)

BASLIKLAR = ["lig", "tarih", "saat", "ev", "dep",
             "oran_1", "oran_0", "oran_2", "oran_kaynak", "olculen_lig"]


def indir(url: str, timeout: float = 60.0) -> Optional[bytes]:
    istek = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=timeout) as r:
            return r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  {url} alinamadi ({e})", file=sys.stderr)
        return None


def _sayi(ham: Any) -> Optional[float]:
    try:
        v = float(str(ham).strip())
    except (TypeError, ValueError):
        return None
    return v if v > 1.0 else None


def oran_sec(satir: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tercih sirasindaki ilk tam uclu. Hicbiri tam degilse mac ELENIR."""
    for onek in KAYNAK_SIRASI:
        degerler = [_sayi(satir.get(f"{onek}{s}")) for s in ("H", "D", "A")]
        if all(v is not None for v in degerler):
            return {"1": degerler[0], "0": degerler[1], "2": degerler[2],
                    "kaynak": onek}
    return None


def tarih_coz(ham: str) -> Optional[date]:
    for bicim in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(ham.strip(), bicim).date()
        except ValueError:
            continue
    return None


def satirlari_coz(ham: bytes, bugun: date) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Yalnizca BUGUN VE SONRASI maclar. Gecmis satirlar sessizce atilmaz, sayilir."""
    sayac = {"toplam": 0, "gecmis": 0, "tarih_yok": 0, "oran_yok": 0}
    out: List[Dict[str, Any]] = []
    metin = ham.decode("utf-8-sig", errors="replace").splitlines()
    for r in csv.DictReader(metin):
        satir = {(k or "").lstrip("﻿"): v for k, v in r.items()}
        if not (satir.get("HomeTeam") or "").strip():
            continue
        sayac["toplam"] += 1

        tarih = tarih_coz(satir.get("Date") or "")
        if tarih is None:
            sayac["tarih_yok"] += 1
            continue
        if tarih < bugun:
            sayac["gecmis"] += 1
            continue
        oran = oran_sec(satir)
        if oran is None:
            sayac["oran_yok"] += 1
            continue

        lig = (satir.get("Div") or "").strip()
        out.append({
            "lig": lig,
            "tarih": tarih.isoformat(),
            "saat": (satir.get("Time") or "").strip(),
            "ev": (satir.get("HomeTeam") or "").strip(),
            "dep": (satir.get("AwayTeam") or "").strip(),
            "oran_1": oran["1"], "oran_0": oran["0"], "oran_2": oran["2"],
            "oran_kaynak": oran["kaynak"],
            "olculen_lig": "1" if lig in OLCULEN_LIGLER else "0",
        })
    return out, sayac


def dogrula(satirlar: List[Dict[str, Any]]) -> List[str]:
    """Yazmadan once ic tutarlilik (doktrin 5).

    **Bos liste bir HATA DEGILDIR.** Fikstur yuvarlanan bir penceredir; hafta
    oynandiginda yaklasan mac kalmaz ve bu normaldir. Bos dosya yazmak,
    "yaklasan mac yok" olgusunu dogru bicimde kaydetmektir.
    """
    hatalar: List[str] = []
    for i, r in enumerate(satirlar):
        for s in ("1", "0", "2"):
            if not r[f"oran_{s}"] > 1.0:
                hatalar.append(f"satir {i}: oran_{s} <= 1.0")
        if not r["ev"] or not r["dep"]:
            hatalar.append(f"satir {i}: takim adi bos")
        if len(hatalar) > 20:
            hatalar.append("... (kirpildi)")
            break
    anahtar = {(r["lig"], r["tarih"], r["ev"], r["dep"]) for r in satirlar}
    if len(anahtar) != len(satirlar):
        hatalar.append(f"mukerrer mac: {len(satirlar) - len(anahtar)} adet")
    return hatalar


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=VARSAYILAN_CIKTI)
    ap.add_argument("--dry-run", action="store_true", help="yazmadan ozet")
    args = ap.parse_args()

    ham = indir(FIXTURES_URL)
    if ham is None:
        print("fikstur alinamadi — dosya YAZILMADI (eski dosya korunur)",
              file=sys.stderr)
        return 1

    bugun = date.today()
    satirlar, sayac = satirlari_coz(ham, bugun)
    hatalar = dogrula(satirlar)
    if hatalar:
        print("\nDOGRULAMA BASARISIZ — dosya yazilmadi:", file=sys.stderr)
        for h in hatalar:
            print(f"  - {h}", file=sys.stderr)
        return 1

    satirlar.sort(key=lambda r: (r["tarih"], r["saat"], r["lig"], r["ev"]))
    olculen = sum(1 for r in satirlar if r["olculen_lig"] == "1")
    ligler = sorted({r["lig"] for r in satirlar})

    print(f"yaklasan mac: {len(satirlar)} ({bugun} ve sonrasi)")
    print(f"  olculen lig evreninde : {olculen}")
    print(f"  lig                   : {len(ligler)} {ligler[:8]}")
    if satirlar:
        print(f"  tarih araligi         : {satirlar[0]['tarih']} → {satirlar[-1]['tarih']}")
    else:
        print("  NOT: yaklasan mac yok — fikstur yuvarlanan bir penceredir,")
        print("       hafta oynandiginda bosalir. Bu bir hata degildir.")
    print(f"  elenen: gecmis={sayac['gecmis']} oran_yok={sayac['oran_yok']}")

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_yol = args.out_dir / "fixtures.csv"
    with open(csv_yol, "w", encoding="utf-8", newline="") as fh:
        yazici = csv.DictWriter(fh, fieldnames=BASLIKLAR, extrasaction="ignore")
        yazici.writeheader()
        yazici.writerows(satirlar)
    print(f"\nyazildi: {csv_yol}")

    rapor = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "football-data.co.uk/fixtures.csv — piyasa oranlari, IDDAA DEGIL",
        "odds_period": ("ACILIS orani; kapanis henuz yok. A1 olcumu: acilis "
                        "Brier 0,5964 · kapanis 0,5940 — fark +0,0025"),
        "as_of": bugun.isoformat(),
        "matches": len(satirlar),
        "in_measured_leagues": olculen,
        "leagues": ligler,
        "rolling_window_note": ("fikstur yuvarlanan penceredir; bos olmasi "
                                "normaldir, hata degildir"),
        "dropped": sayac,
    }
    rapor_yol = args.out_dir / "fixtures_rapor.json"
    rapor_yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(f"yazildi: {rapor_yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
