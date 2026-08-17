#!/usr/bin/env python3
"""Eğitim korpusu üretimi — tahminciyi eğitmek ve ölçmek için maç evreni.

**Bu dosya istatistik katmanının parçası DEĞİLDİR.** `/istatistik` sayfası
Spor Toto kuponunun sezonunu anlatır (41 hafta, 615 maç) ve öyle kalır. Burada
üretilen korpus yalnızca **tahmin katmanının eğitimi ve ölçümü** içindir; iki
veri seti bilerek ayrı tutulur ve ayrımı `tests/test_egitim.py` bekçiye bağlar.

Neden ayrı bir korpus:

Kupon değerlendirme seti 540 maç ve tek sezon. "Piyasayı geçen bir şey var mı"
sorusuna bu örneklemle verilen cevap zayıf kalıyor (bkz. Adım 2 ölçümü). Aynı
kaynak — football-data.co.uk — kupon dışındaki maçların da hem sonucunu hem
1X2 oranını taşıyor; bir tahminciyi ölçmek için gereken üçlü budur ve kuponun
hangi 15 maçtan oluştuğu bu iş için ilgisizdir.

**Varsayılan sezonlar geçmişle sınırlıdır ve bu kasıtlıdır.** Korpusa
2025/2026 katılırsa, kupon değerlendirme seti de o sezondan geldiği için
eğitim ve sınav aynı maçları paylaşır. Varsayılan dışında bir sezon istenirse
`--sezonlar` ile açıkça verilir ve rapor bunu yazar.

Kaynak: football-data.co.uk — **piyasa oranlarıdır, iddaa oranı değildir.**
`robots.txt` tüm erişime açıktır (`Disallow:` boş).

Kullanım:

    python scripts/build_egitim.py                    # varsayilan sezonlar
    python scripts/build_egitim.py --dry-run          # yazmadan ozet
    python scripts/build_egitim.py --sezonlar 2324 2425
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_CIKTI = KOK / "data" / "egitim"

UA = "Mozilla/5.0 (compatible; spor-toto-lab/1.0)"
ANA_URL = "https://www.football-data.co.uk/mmz4281/{sezon}/{lig}.csv"

#: Varsayilan sezonlar — **2526 bilerek yok** (kupon degerlendirme seti o
#: sezondan geliyor; korpusa katmak egitim/sinav ayrimini bozar).
VARSAYILAN_SEZONLAR: Tuple[str, ...] = ("2122", "2223", "2324", "2425")

#: build_odds.py ile ayni lig listesi — ayni kaynak, ayni etiketler.
ANA_LIGLER: Tuple[str, ...] = (
    "E0", "E1", "E2", "E3", "EC",
    "SC0", "SC1", "SC2", "SC3",
    "D1", "D2", "I1", "I2", "SP1", "SP2",
    "F1", "F2", "N1", "B1", "P1", "T1", "G1",
)

#: Oran kaynagi tercihi — once kapanis, sonra acilis. `odds.KAYNAK_SIRASI` ile
#: ayni mantik: kapanis orani acilistan daha bilgilidir.
KAYNAK_SIRASI: Tuple[Tuple[str, bool], ...] = (
    ("AvgC", True), ("B365C", True), ("PSC", True),
    ("Avg", False), ("B365", False), ("PS", False),
)

#: FTR -> kupon sembolu
SONUC_KODU = {"H": "1", "D": "0", "A": "2"}

#: Tasinan mac istatistikleri. Bunlar mac SONRASI veridir; dogrudan tahminci
#: girdisi OLAMAZLAR. Tek amaclari yuvarlanan takim formu uretmek: bir macin
#: oncesindeki maclardan hesaplanan sut/isabetli sut farki. Eksik olabilirler
#: ve eksikse UYDURULMAZ — form ureteci o maci gecmise katmaz (doktrin 2).
ISTATISTIK_SUTUNLARI: Tuple[Tuple[str, str], ...] = (
    ("HS", "ev_sut"), ("AS", "dep_sut"),
    ("HST", "ev_isabet"), ("AST", "dep_isabet"),
    ("HC", "ev_korner"), ("AC", "dep_korner"),
)


def indir(url: str, hedef: Path, timeout: float = 60.0) -> Optional[Path]:
    """Kaynak dosyayi indir; varsa yeniden indirme (onbellek git disi)."""
    if hedef.exists() and hedef.stat().st_size > 0:
        return hedef
    istek = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=timeout) as r:
            ham = r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  {url} alinamadi ({e})", file=sys.stderr)
        return None
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(ham)
    return hedef


def tarih_coz(ham: str) -> Optional[datetime]:
    for bicim in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(ham.strip(), bicim)
        except ValueError:
            continue
    return None


def _sayi(ham: Any) -> Optional[float]:
    try:
        v = float(str(ham).strip())
    except (TypeError, ValueError):
        return None
    return v if v > 1.0 else None


def oran_sec(satir: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Bir macin 1X2 orani — tercih sirasina gore ilk tam ucluyu dondurur.

    Ucunden biri eksikse ya da 1.00 ise (askiya alinmis ayak) o kaynak
    atlanir; hicbiri tam degilse mac **elenir, tamamlanmaz** (doktrin 2).
    """
    for onek, kapanis in KAYNAK_SIRASI:
        degerler = [_sayi(satir.get(f"{onek}{s}")) for s in ("H", "D", "A")]
        if all(v is not None for v in degerler):
            return {"1": degerler[0], "0": degerler[1], "2": degerler[2],
                    "kaynak": onek, "kapanis": kapanis}
    return None


def satirlari_coz(sezon: str, lig: str, yol: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Bir lig-sezon dosyasindan gecerli mac satirlari."""
    sayac = {"toplam": 0, "tarih_yok": 0, "sonuc_yok": 0, "oran_yok": 0}
    out: List[Dict[str, Any]] = []
    with open(yol, encoding="latin-1", newline="") as fh:
        for ham in csv.DictReader(fh):
            # BOM latin-1 okumada ilk sutun adina yapisir (build_odds vakasi)
            satir = {(k or "").lstrip("﻿\xef\xbb\xbf"): v for k, v in ham.items()}
            if not (satir.get("HomeTeam") or "").strip():
                continue
            sayac["toplam"] += 1

            tarih = tarih_coz(satir.get("Date") or "")
            if tarih is None:
                sayac["tarih_yok"] += 1
                continue
            kod = SONUC_KODU.get((satir.get("FTR") or "").strip().upper())
            if kod is None:
                sayac["sonuc_yok"] += 1
                continue
            oran = oran_sec(satir)
            if oran is None:
                sayac["oran_yok"] += 1
                continue

            yil, iso_hafta, _ = tarih.isocalendar()
            istatistik = {}
            for kaynak_ad, hedef_ad in ISTATISTIK_SUTUNLARI:
                ham_deger = (satir.get(kaynak_ad) or "").strip()
                istatistik[hedef_ad] = ham_deger if ham_deger.isdigit() else ""
            out.append({
                "sezon": sezon,
                "lig": (satir.get("Div") or lig).strip() or lig,
                "tarih": tarih.date().isoformat(),
                "iso_yil": yil,
                "iso_hafta": iso_hafta,
                "ev": (satir.get("HomeTeam") or "").strip(),
                "dep": (satir.get("AwayTeam") or "").strip(),
                "hg": (satir.get("FTHG") or "").strip(),
                "ag": (satir.get("FTAG") or "").strip(),
                "kod": kod,
                "oran_1": oran["1"], "oran_0": oran["0"], "oran_2": oran["2"],
                "oran_kaynak": oran["kaynak"],
                "kapanis": "1" if oran["kapanis"] else "0",
                **istatistik,
            })
    return out, sayac


def dogrula(satirlar: List[Dict[str, Any]]) -> List[str]:
    """Yazmadan once ic tutarlilik (doktrin 5). Bos liste = temiz."""
    hatalar: List[str] = []
    if not satirlar:
        return ["korpus bos"]
    for i, r in enumerate(satirlar):
        if r["kod"] not in ("1", "0", "2"):
            hatalar.append(f"satir {i}: gecersiz kod {r['kod']!r}")
        for s in ("1", "0", "2"):
            if not r[f"oran_{s}"] > 1.0:
                hatalar.append(f"satir {i}: oran_{s} <= 1.0")
        if not r["ev"] or not r["dep"]:
            hatalar.append(f"satir {i}: takim adi bos")
        if len(hatalar) > 20:
            hatalar.append("... (kirpildi)")
            break

    anahtar = {(r["sezon"], r["lig"], r["tarih"], r["ev"], r["dep"]) for r in satirlar}
    if len(anahtar) != len(satirlar):
        hatalar.append(f"mukerrer mac: {len(satirlar) - len(anahtar)} adet")
    return hatalar


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sezonlar", nargs="+", default=list(VARSAYILAN_SEZONLAR),
                    help="football-data sezon kodlari (orn. 2324 2425)")
    ap.add_argument("--ligler", nargs="+", default=list(ANA_LIGLER))
    ap.add_argument("--out-dir", type=Path, default=VARSAYILAN_CIKTI)
    ap.add_argument("--cache", type=Path, default=None,
                    help="ham dosya onbellegi (varsayilan: <out-dir>/_kaynak)")
    ap.add_argument("--dry-run", action="store_true", help="yazmadan ozet")
    args = ap.parse_args()

    cache = args.cache or (args.out_dir / "_kaynak")
    satirlar: List[Dict[str, Any]] = []
    sayaclar: Dict[str, int] = {"toplam": 0, "tarih_yok": 0, "sonuc_yok": 0, "oran_yok": 0}
    alinamayan: List[str] = []

    for sezon in args.sezonlar:
        for lig in args.ligler:
            yol = indir(ANA_URL.format(sezon=sezon, lig=lig),
                        cache / sezon / f"{lig}.csv")
            if yol is None:
                alinamayan.append(f"{sezon}/{lig}")
                continue
            yeni, sayac = satirlari_coz(sezon, lig, yol)
            satirlar.extend(yeni)
            for k, v in sayac.items():
                sayaclar[k] += v
        print(f"  {sezon}: {len(satirlar)} satir (kumulatif)")

    hatalar = dogrula(satirlar)
    if hatalar:
        print("\nDOGRULAMA BASARISIZ — dosya yazilmadi:", file=sys.stderr)
        for h in hatalar:
            print(f"  - {h}", file=sys.stderr)
        return 1

    satirlar.sort(key=lambda r: (r["tarih"], r["lig"], r["ev"]))
    sezon_dagilim = {s: sum(1 for r in satirlar if r["sezon"] == s)
                     for s in args.sezonlar}
    kod_dagilim = {k: sum(1 for r in satirlar if r["kod"] == k) for k in ("1", "0", "2")}
    kapanis_orani = sum(1 for r in satirlar if r["kapanis"] == "1") / len(satirlar)
    istatistikli = sum(1 for r in satirlar if r.get("ev_isabet"))


    print(f"\nkorpus: {len(satirlar)} mac · {len(sezon_dagilim)} sezon "
          f"· {len({r['lig'] for r in satirlar})} lig")
    print(f"  sezon dagilimi : {sezon_dagilim}")
    print(f"  sonuc dagilimi : {kod_dagilim}")
    print(f"  kapanis orani  : %{100 * kapanis_orani:.1f}")
    print(f"  istatistikli   : {istatistikli} (%{100 * istatistikli / len(satirlar):.1f})")
    if sayaclar["oran_yok"]:
        print(f"  orani olmadigi icin elenen: {sayaclar['oran_yok']}")
    if alinamayan:
        print(f"  alinamayan dosya: {len(alinamayan)} ({', '.join(alinamayan[:5])}...)")

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    basliklar = ["sezon", "lig", "tarih", "iso_yil", "iso_hafta", "ev", "dep",
                 "hg", "ag", "kod", "oran_1", "oran_0", "oran_2",
                 "oran_kaynak", "kapanis"] + [h for _, h in ISTATISTIK_SUTUNLARI]
    csv_yol = args.out_dir / "egitim_korpus.csv"
    with open(csv_yol, "w", encoding="utf-8", newline="") as fh:
        yazici = csv.DictWriter(fh, fieldnames=basliklar, extrasaction="ignore")
        yazici.writeheader()
        yazici.writerows(satirlar)
    print(f"\nyazildi: {csv_yol}")

    rapor = {
        "generated_at": datetime.now().date().isoformat(),
        "source": "football-data.co.uk (mmz4281) — piyasa oranlari, IDDAA DEGIL",
        "purpose": ("tahmin katmaninin egitimi ve olcumu; istatistik sayfasinin "
                    "verisi DEGILDIR"),
        "seasons": list(args.sezonlar),
        "season_note": ("varsayilan sezonlar 2025/2026'yi disarida birakir: kupon "
                        "degerlendirme seti o sezondan gelir, korpusa katmak "
                        "egitim/sinav ayrimini bozar"),
        "matches": len(satirlar),
        "by_season": sezon_dagilim,
        "leagues": sorted({r["lig"] for r in satirlar}),
        "result_distribution": kod_dagilim,
        "closing_odds_pct": round(100 * kapanis_orani, 2),
        "with_match_stats": istatistikli,
        "match_stats_pct": round(100 * istatistikli / len(satirlar), 2),
        "match_stats_note": ("mac SONRASI veridir; dogrudan tahminci girdisi degil, "
                             "yalnizca yuvarlanan takim formu icin"),
        "dropped": sayaclar,
        "unavailable_files": alinamayan,
    }
    rapor_yol = args.out_dir / "egitim_rapor.json"
    rapor_yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(f"yazildi: {rapor_yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
