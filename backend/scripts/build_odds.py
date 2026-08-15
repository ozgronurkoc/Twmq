#!/usr/bin/env python3
"""Tarihsel kupon maclari icin bahis oranlarini toplar.

    python scripts/build_odds.py                 # cek, eslestir, yaz
    python scripts/build_odds.py --dry-run       # yazmadan kapsama raporu
    python scripts/build_odds.py --no-sqlite     # yalnizca CSV + rapor

Kaynak: football-data.co.uk ucretsiz arsiv CSV'leri (kisisel kullanim icin
serbest). Iki tur dosya var:

- Ana ligler (`mmz4281/2526/T1.csv` gibi): 12 bahisciden 1X2 (acilis +
  kapanis), 2.5 alt/ust, Asya handikap ve mac istatistikleri — ~131 sutun.
- Ek ulkeler (`new/POL.csv` gibi): yalnizca kapanis 1X2, 4 kaynaktan.

NOT: Bunlar **iddaa oranlari degildir**. Iddaa kendi gecmis bultenini
yayinlamaz (resmi API yalnizca acik bulteni verir), bu yuzden geriye donuk
tek gercekci kaynak piyasa oranlaridir. Sıralama ve olasilik yapisi
iddaa ile buyuk olcude ortusur, seviye ortusmez (iddaa marji daha yuksek).

Eslestirme: tarih (±1 gun) + BIREBIR skor + bulanik takim adi. Skor sarti
yanlis eslesmeye karsi en guclu korumadir; takim adi benzerligi de esigi
gecmek zorundadir.

Cikti arayuze BAGLI DEGILDIR. Yalnizca ileride yapilacak analiz icin durur:

    data/odds/odds_2025_26.csv     surumlenen genis tablo (mac basina 1 satir)
    data/odds/odds_rapor.json      kapsama raporu
    data/odds/odds.sqlite3         sorgulanabilir kopya (git disi, uretilir)
    data/odds/_kaynak/*.csv        indirilen ham dosyalar (git disi)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KOK = Path(__file__).resolve().parent.parent
GECMIS = KOK / "data" / "st_history_2025_26.json"
CIKTI_DIZIN = KOK / "data" / "odds"
UA = "spor-toto-lab/1.0 (kisisel arsiv analizi)"

SEZON = "2526"
ANA_LIGLER = [
    "E0", "E1", "E2", "E3", "EC",            # Ingiltere
    "SC0", "SC1", "SC2", "SC3",              # Iskocya
    "D1", "D2", "I1", "I2", "SP1", "SP2",    # Almanya / Italya / Ispanya
    "F1", "F2", "N1", "B1", "P1", "T1", "G1",
]
EK_ULKELER = [
    "ARG", "AUT", "BRA", "CHN", "DNK", "FIN", "IRL", "JPN",
    "MEX", "NOR", "POL", "ROU", "RUS", "SWE", "SWZ", "USA",
]
ANA_URL = "https://www.football-data.co.uk/mmz4281/{sezon}/{lig}.csv"
EK_URL = "https://www.football-data.co.uk/new/{ulke}.csv"

# Kimlik ve istatistik sutunlari — geri kalan her sey oran sayilir.
KIMLIK = {
    "Div", "Country", "League", "Season", "Date", "Time",
    "HomeTeam", "AwayTeam", "Home", "Away",
    "FTHG", "FTAG", "FTR", "HG", "AG", "Res",
}
ISTATISTIK = {
    "HTHG", "HTAG", "HTR", "HS", "AS", "HST", "AST",
    "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
}

# Bahisci/agregat on ekleri — uzun olan once denenir.
KAYNAKLAR = [
    "B365", "BFD", "BMGM", "BFE", "BW", "BV", "CL", "LB", "PS", "SJ", "VC",
    "WH", "1XB", "GB", "IW", "SB", "SO", "SY", "Max", "Avg", "P",
]

TAKIM_ESLERI = {
    # kaynaktaki kisaltma -> bultendeki ada yakin bicim
    "buyuksehyr": "basaksehir",
    "ath madrid": "atletico madrid",
    "ath bilbao": "athletic bilbao",
    "sp lisbon": "sporting lisbon",
    "man united": "manchester united",
    "man city": "manchester city",
    "nott'm forest": "nottingham forest",
    "sheffield weds": "sheffield wednesday",
    "paris sg": "paris saint germain",
    "ein frankfurt": "eintracht frankfurt",
    "leverkusen": "bayer leverkusen",
    "m'gladbach": "borussia monchengladbach",
    "dortmund": "borussia dortmund",
}

# Yalnizca SPONSOR ekleri — takim adinin kendisi buraya asla girmez.
SPONSOR = [
    "hesap.com", "misirli.com.tr", "corendon", "zecorner", "tumosan", "caykur",
    "natura dunyasi", "rams", "ikas", "arabam.com",
]


# ─── isim normalizasyonu ──────────────────────────────────────────────────────

def sadelestir(ad: str) -> str:
    s = (ad or "").lower()
    for a, b in (("ı", "i"), ("ğ", "g"), ("ş", "s"), ("ö", "o"), ("ü", "u"), ("ç", "c")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = TAKIM_ESLERI.get(s.strip(), s)
    for j in SPONSOR:
        s = s.replace(j, " ")
    s = re.sub(r"\b(a\.?s\.?|fk|fc|sk|cf|ac|sc|kulubu|futbol|1907)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def benzerlik(a: str, b: str) -> float:
    x, y = sadelestir(a), sadelestir(b)
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0
    if x in y or y in x:
        return 0.94
    return SequenceMatcher(None, x, y).ratio()


# ─── sutun adi cozumleme ──────────────────────────────────────────────────────

def sutun_ayristir(sutun: str) -> Tuple[str, str, str, str]:
    """'AvgCH' -> (kaynak='Avg', pazar='1X2', secim='1', donem='kapanis')."""
    s = sutun.strip()
    kaynak = ""
    for k in sorted(KAYNAKLAR, key=len, reverse=True):
        if s.startswith(k):
            kaynak, s = k, s[len(k):]
            break
    donem = "acilis"
    if s.startswith("C") and s != "C":
        donem, s = "kapanis", s[1:]
    if ">2.5" in s:
        return kaynak, "2.5U", "ust", donem
    if "<2.5" in s:
        return kaynak, "2.5A", "alt", donem
    if s in ("AHh", "AHCh", "Ch", "h"):
        return kaynak or "piyasa", "AH", "cizgi", donem
    if s.startswith("AH"):
        son = s[2:]
        return kaynak, "AH", {"H": "1", "A": "2"}.get(son[-1:], son), donem
    if s in ("H", "D", "A"):
        return kaynak, "1X2", {"H": "1", "D": "0", "A": "2"}[s], donem
    return kaynak, "diger", s, donem


# ─── kaynak dosyalar ──────────────────────────────────────────────────────────

def indir(url: str, hedef: Path, timeout: float = 60.0) -> Optional[Path]:
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
            return datetime.strptime(ham, bicim)
        except ValueError:
            continue
    return None


def kaynak_satirlari(cache: Path) -> Dict[Any, List[Dict[str, Any]]]:
    """Gune gore indekslenmis kaynak satirlari."""
    indeks: Dict[Any, List[Dict[str, Any]]] = {}
    dosyalar: List[Tuple[str, Path]] = []

    for lig in ANA_LIGLER:
        p = indir(ANA_URL.format(sezon=SEZON, lig=lig), cache / f"{lig}.csv")
        if p:
            dosyalar.append((lig, p))
    for ulke in EK_ULKELER:
        p = indir(EK_URL.format(ulke=ulke), cache / f"new_{ulke}.csv")
        if p:
            dosyalar.append((f"new_{ulke}", p))

    for etiket, yol in dosyalar:
        with open(yol, encoding="latin-1", newline="") as fh:
            for satir in csv.DictReader(fh):
                satir = {(k or "").strip().lstrip("﻿"): v for k, v in satir.items()}
                dt = tarih_coz((satir.get("Date") or "").strip())
                if not dt:
                    continue
                ev = satir.get("HomeTeam") or satir.get("Home")
                dep = satir.get("AwayTeam") or satir.get("Away")
                eg = satir.get("FTHG") if satir.get("FTHG") not in (None, "") else satir.get("HG")
                dg = satir.get("FTAG") if satir.get("FTAG") not in (None, "") else satir.get("AG")
                try:
                    eg, dg = int(eg), int(dg)
                except (TypeError, ValueError):
                    continue
                if not ev or not dep:
                    continue
                indeks.setdefault(dt.date(), []).append({
                    "_dosya": etiket,
                    "_lig": satir.get("Div") or f'{satir.get("Country","")}/{satir.get("League","")}',
                    "_ev": ev, "_dep": dep, "_eg": eg, "_dg": dg,
                    "_tarih": dt.date().isoformat(),
                    "ham": satir,
                })
    return indeks


# ─── eslestirme ───────────────────────────────────────────────────────────────

def en_iyi_aday(mac: Dict[str, Any], indeks, esik: float = 0.55):
    gun = (mac.get("kickoff") or "")[:10]
    try:
        d = datetime.strptime(gun, "%Y-%m-%d").date()
    except ValueError:
        return None, 0.0
    en_iyi, en_iyi_skor = None, 0.0
    for kayma in (0, -1, 1):
        for aday in indeks.get(d + timedelta(days=kayma), []):
            if (aday["_eg"], aday["_dg"]) != (mac["hg"], mac["ag"]):
                continue
            skor = (benzerlik(mac["home"], aday["_ev"]) + benzerlik(mac["away"], aday["_dep"])) / 2
            if skor > en_iyi_skor:
                en_iyi, en_iyi_skor = aday, skor
    return (en_iyi, round(en_iyi_skor, 3)) if en_iyi_skor >= esik else (None, round(en_iyi_skor, 3))


# ─── cikti ────────────────────────────────────────────────────────────────────

def sayi(ham: Any) -> Optional[float]:
    if ham in (None, "", "-"):
        return None
    try:
        return float(str(ham).replace(",", "."))
    except ValueError:
        return None


def sqlite_yaz(yol: Path, satirlar: List[Dict[str, Any]]) -> None:
    if yol.exists():
        yol.unlink()
    db = sqlite3.connect(yol)
    db.executescript("""
        CREATE TABLE mac (
            week INTEGER, no INTEGER, kickoff TEXT, home TEXT, away TEXT,
            hg INTEGER, ag INTEGER, code TEXT,
            kaynak_dosya TEXT, kaynak_lig TEXT, kaynak_ev TEXT, kaynak_dep TEXT,
            guven REAL,
            PRIMARY KEY (week, no)
        );
        CREATE TABLE oran (
            week INTEGER, no INTEGER, sutun TEXT,
            kaynak TEXT, pazar TEXT, secim TEXT, donem TEXT, deger REAL,
            PRIMARY KEY (week, no, sutun)
        );
        CREATE TABLE istatistik (
            week INTEGER, no INTEGER, ad TEXT, deger REAL,
            PRIMARY KEY (week, no, ad)
        );
        CREATE INDEX oran_pazar ON oran (pazar, donem, kaynak);
    """)
    for r in satirlar:
        if not r["eslesti"]:
            continue
        db.execute(
            "INSERT INTO mac VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["week"], r["no"], r["kickoff"], r["home"], r["away"], r["hg"], r["ag"],
             r["code"], r["kaynak_dosya"], r["kaynak_lig"], r["kaynak_ev"],
             r["kaynak_dep"], r["guven"]),
        )
        for sutun, deger in r["oranlar"].items():
            kaynak, pazar, secim, donem = sutun_ayristir(sutun)
            db.execute("INSERT OR REPLACE INTO oran VALUES (?,?,?,?,?,?,?,?)",
                       (r["week"], r["no"], sutun, kaynak, pazar, secim, donem, deger))
        for ad, deger in r["istatistikler"].items():
            db.execute("INSERT OR REPLACE INTO istatistik VALUES (?,?,?,?)",
                       (r["week"], r["no"], ad, deger))
    db.commit()
    db.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gecmis", type=Path, default=GECMIS)
    ap.add_argument("--out-dir", type=Path, default=CIKTI_DIZIN)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--esik", type=float, default=0.55, help="takim adi benzerlik esigi")
    ap.add_argument("--no-sqlite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cache = args.cache or (args.out_dir / "_kaynak")
    if not args.gecmis.exists():
        print(f"Gecmis veri seti yok: {args.gecmis}", file=sys.stderr)
        return 1
    gecmis = json.loads(args.gecmis.read_text(encoding="utf-8"))
    haftalar = gecmis.get("weeks", [])

    print("kaynak dosyalar indiriliyor / okunuyor…")
    indeks = kaynak_satirlari(cache)
    print(f"  {sum(len(v) for v in indeks.values())} kaynak satiri, {len(indeks)} gun\n")

    satirlar: List[Dict[str, Any]] = []
    oran_sutunlari: set = set()
    stat_sutunlari: set = set()

    for w in haftalar:
        for mac in w.get("matches", []):
            aday, guven = en_iyi_aday(mac, indeks, args.esik)
            kayit: Dict[str, Any] = {
                "week": w["week"], "no": mac["no"], "kickoff": mac["kickoff"],
                "home": mac["home"], "away": mac["away"],
                "hg": mac["hg"], "ag": mac["ag"], "code": mac["code"],
                "eslesti": aday is not None, "guven": guven,
                "kaynak_dosya": aday["_dosya"] if aday else "",
                "kaynak_lig": aday["_lig"] if aday else "",
                "kaynak_ev": aday["_ev"] if aday else "",
                "kaynak_dep": aday["_dep"] if aday else "",
                "oranlar": {}, "istatistikler": {},
            }
            if aday:
                for sutun, ham in aday["ham"].items():
                    if not sutun or sutun in KIMLIK:
                        continue
                    deger = sayi(ham)
                    if deger is None:
                        continue
                    if sutun in ISTATISTIK:
                        kayit["istatistikler"][sutun] = deger
                        stat_sutunlari.add(sutun)
                    else:
                        kayit["oranlar"][sutun] = deger
                        oran_sutunlari.add(sutun)
            satirlar.append(kayit)

    eslesen = [r for r in satirlar if r["eslesti"]]
    toplam = len(satirlar)
    tam_hafta = sum(
        1 for w in haftalar
        if all(r["eslesti"] for r in satirlar if r["week"] == w["week"])
    )
    print(f"eslesme: {len(eslesen)}/{toplam} mac "
          f"(%{100 * len(eslesen) / toplam:.1f}) · {tam_hafta}/{len(haftalar)} hafta tam")
    print(f"oran sutunu: {len(oran_sutunlari)} · istatistik sutunu: {len(stat_sutunlari)}")

    # Pazar bazinda kac maca oran dustu
    pazar_sayaci: Dict[str, int] = {}
    for r in eslesen:
        for sutun in r["oranlar"]:
            _, pazar, _, donem = sutun_ayristir(sutun)
            pazar_sayaci[f"{pazar}/{donem}"] = pazar_sayaci.get(f"{pazar}/{donem}", 0) + 1
    print("pazar kapsamasi (sutun-deger adedi):")
    for k, v in sorted(pazar_sayaci.items(), key=lambda x: -x[1]):
        print(f"  {k:<16} {v}")

    eksik = [r for r in satirlar if not r["eslesti"]]
    if eksik:
        print(f"\neslesmeyen {len(eksik)} mac (ilk 10):")
        for r in eksik[:10]:
            print(f"  hf {r['week']:>2} #{r['no']:>2} {r['home']} – {r['away']} "
                  f"{r['kickoff'][:10]} {r['hg']}-{r['ag']} (en iyi benzerlik {r['guven']})")

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    oran_sirali = sorted(oran_sutunlari)
    stat_sirali = sorted(stat_sutunlari)
    csv_yol = args.out_dir / "odds_2025_26.csv"
    basliklar = [
        "week", "no", "kickoff", "home", "away", "hg", "ag", "code",
        "kaynak_dosya", "kaynak_lig", "kaynak_ev", "kaynak_dep", "guven",
    ] + oran_sirali + [f"stat_{s}" for s in stat_sirali]

    with open(csv_yol, "w", encoding="utf-8", newline="") as fh:
        yazici = csv.DictWriter(fh, fieldnames=basliklar, extrasaction="ignore")
        yazici.writeheader()
        for r in satirlar:
            satir = {k: r[k] for k in basliklar[:13] if k in r}
            satir.update({k: r["oranlar"].get(k, "") for k in oran_sirali})
            satir.update({f"stat_{k}": r["istatistikler"].get(k, "") for k in stat_sirali})
            yazici.writerow(satir)
    print(f"\nyazildi: {csv_yol}")

    rapor = {
        "generated_at": datetime.now().date().isoformat(),
        "source": "football-data.co.uk (mmz4281/2526 + new/) — piyasa oranlari, IDDAA DEGIL",
        "matches_total": toplam,
        "matches_matched": len(eslesen),
        "coverage_pct": round(100 * len(eslesen) / toplam, 2) if toplam else 0,
        "weeks_total": len(haftalar),
        "weeks_full": tam_hafta,
        "odds_columns": oran_sirali,
        "stat_columns": stat_sirali,
        "market_coverage": pazar_sayaci,
        "unmatched": [
            {"week": r["week"], "no": r["no"], "home": r["home"], "away": r["away"],
             "date": r["kickoff"][:10], "best_similarity": r["guven"]}
            for r in eksik
        ],
    }
    rapor_yol = args.out_dir / "odds_rapor.json"
    rapor_yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(f"yazildi: {rapor_yol}")

    if not args.no_sqlite:
        db_yol = args.out_dir / "odds.sqlite3"
        sqlite_yaz(db_yol, satirlar)
        print(f"yazildi: {db_yol}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
