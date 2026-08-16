#!/usr/bin/env python3
"""Iddaa acik bulteninin tarih damgali anlik goruntusunu alir.

    python scripts/snapshot_iddaa.py              # cek ve yaz
    python scripts/snapshot_iddaa.py --dry-run    # yazmadan ozet
    python scripts/snapshot_iddaa.py --no-sqlite  # yalnizca CSV
    python scripts/snapshot_iddaa.py --kaynak d.json   # kaydedilmis ham dosyadan

NEDEN VAR
=========
Gecmis iddaa orani hicbir yerde yayinlanmiyor: iddaa ve bayileri yalnizca
ACIK bulteni servis eder, kapanan macin orani API'den duser (olcumde 8
gunluk pencere). Bu yuzden `build_odds.py` geriye donuk analizde piyasa
oranini (football-data.co.uk) vekil olarak kullaniyor — seviye tutmuyor,
yapi tutuyor.

Bu script o boslugu ILERIYE DONUK kapatir: haftada bir calisip bultenin o
anki halini saklarsa bir sezon sonunda **kendi iddaa arsivimiz** olur.
Bugun baslamanin maliyeti bir cron job; baslamamanin maliyeti bir sezon.

Tek basina bir snapshot ise yaramaz — deger zamanla birikir. Bu yuzden
dosyalar tarih damgali ve surumlenir; ayni gun yeniden calistirmak ayni
dosyanin uzerine yazar, farkli gun yeni dosya acar.

NE TOPLANIR
===========
Yalnizca futbol (sid=1) ve yalnizca **mac sonucu (1X2)** pazari — olculdu:
`t=1, st=1` ve secenek adlari "1"/"0"/"2". Bultendeki diger pazarlar
(alt/ust, karsilikli gol, handikap...) bilincli olarak DISARIDA: onlari
anlamli bir sozluge oturtmak ayri bir istir ve F1'in ihtiyaci 1X2.

Iki oran alani var ve ikisi de saklanir:
  odd   — bayi/kupon orani
  wodd  — web orani (olcumde sistematik olarak biraz dusuk)

CIKTI
=====
    data/iddaa/iddaa_YYYY-MM-DD.csv   surumlenen anlik goruntu (mac basina 1 satir)
    data/iddaa/iddaa_rapor.json       en son calismanin ozeti
    data/iddaa/iddaa.sqlite3          UZUN BICIM kopya (git disi, uretilir)
    data/iddaa/_kaynak/*.json         indirilen ham payload (git disi)

SQLite semasi bilerek `odds.sqlite3` ile ayni uzun bicimdedir
(`pazar`/`secim`/`deger`), boylece iki kaynak yan yana sorgulanabilir.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

KOK = Path(__file__).resolve().parent.parent
CIKTI_DIZIN = KOK / "data" / "iddaa"
UA = "spor-toto-lab/1.0 (kisisel arsiv analizi)"

EVENTS_URL = "https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=0&version=0"
COMP_URL = "https://sportsbookv2.iddaa.com/sportsbook/competitions?st=1"

#: Futbol. Bultende baska spor dallari da var, onlar kupona girmez.
FUTBOL_SID = 1

#: Mac sonucu pazarinin bultendeki kimligi. Olculdu: 226 etkinligin
#: 225'inde bu pazar var ve secenek adlari tam olarak "1"/"0"/"2".
MS_TIP, MS_ALT_TIP = 1, 1

SEMBOLLER = ("1", "0", "2")


def indir(url: str, zaman_asimi: float = 30.0) -> Any:
    istek = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as cevap:
        return json.loads(cevap.read().decode("utf-8"))


def _govde(payload: Any) -> Dict[str, Any]:
    """`{isSuccess, data, message}` sarmalini acar; sarmalsizi da kabul eder."""
    if isinstance(payload, dict) and "data" in payload:
        if payload.get("isSuccess") is False:
            raise RuntimeError(f"API basarisiz: {payload.get('message')}")
        return payload["data"] or {}
    return payload or {}


def lig_adlari(payload: Any) -> Dict[int, str]:
    """Yaris (competition) kimligi -> okunur ad. Alinamazsa bos sozluk."""
    veri = _govde(payload)
    kayitlar = veri if isinstance(veri, list) else veri.get("competitions", [])
    out: Dict[int, str] = {}
    for c in kayitlar or []:
        if isinstance(c, dict) and isinstance(c.get("i"), int):
            ad = (c.get("n") or c.get("sn") or "").strip()
            if ad:
                out[c["i"]] = ad
    return out


def ms_orani(etkinlik: Dict[str, Any]) -> Optional[Dict[str, Dict[str, float]]]:
    """Etkinligin 1X2 pazari: {"odd": {...}, "wodd": {...}} ya da None.

    1.00 ve altindaki oran FIYAT DEGILDIR — bultende askiya alinmis ayagin
    yer tutucusu. Olculdu: 225 macin 3'unde bir ayak 1.00 ve digerleri
    17.95/8.48 gibi anlamsiz; bunlari fiyatmis gibi saklamak sonraki her
    analizi zehirler. `spor_toto.odds.match_1x2` ayni kurali uyguluyor,
    burada da ayni: boyle bir mac hic kaydedilmez.
    """
    for m in etkinlik.get("m") or []:
        if m.get("t") != MS_TIP or m.get("st") != MS_ALT_TIP:
            continue
        kupon: Dict[str, float] = {}
        web: Dict[str, float] = {}
        for o in m.get("o") or []:
            ad = str(o.get("n") or "").strip()
            if ad not in SEMBOLLER:
                continue
            try:
                kupon[ad] = float(o["odd"])
            except (KeyError, TypeError, ValueError):
                continue
            try:
                web[ad] = float(o["wodd"])
            except (KeyError, TypeError, ValueError):
                pass
        # Eksik ayakli pazar saklanmaz: iki ayakli bir "1X2" yaniltir.
        if len(kupon) != len(SEMBOLLER):
            return None
        if any(v <= 1.0 for v in kupon.values()):
            return None
        return {"odd": kupon, "wodd": web}
    return None


def marj(oranlar: Dict[str, float]) -> Optional[float]:
    """Bahisci payi: ham olasilik toplaminin 1'i asan kismi."""
    if len(oranlar) != len(SEMBOLLER) or any(v <= 0 for v in oranlar.values()):
        return None
    return round(sum(1.0 / v for v in oranlar.values()) - 1.0, 4)


def satirlar_uret(veri: Dict[str, Any], ligler: Dict[int, str],
                  alinma: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in veri.get("events") or []:
        if e.get("sid") != FUTBOL_SID:
            continue
        blok = ms_orani(e)
        if not blok:
            continue
        ts = e.get("d")
        # Bultendeki `d` unix saniye. UTC saklaniyor — oran arsivindeki
        # `kickoff` da UTC, iki kaynak ayni eksende olsun diye.
        kickoff = (
            datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if isinstance(ts, (int, float)) else ""
        )
        kupon = blok["odd"]
        out.append({
            "alinma": alinma,
            "event_id": e.get("i"),
            "kickoff": kickoff,
            "home": (e.get("hn") or "").strip(),
            "away": (e.get("an") or "").strip(),
            "lig_kodu": e.get("ci"),
            "lig": ligler.get(e.get("ci"), ""),
            "canli": 1 if e.get("il") else 0,
            "odd": kupon,
            "wodd": blok["wodd"],
            "marj": marj(kupon),
        })
    out.sort(key=lambda r: (r["kickoff"], r["event_id"] or 0))
    return out


# ─── yazma ────────────────────────────────────────────────────────────────────

CSV_BASLIK = [
    "alinma", "event_id", "kickoff", "home", "away", "lig", "lig_kodu", "canli",
    "odd_1", "odd_0", "odd_2", "wodd_1", "wodd_0", "wodd_2", "marj",
]


def csv_yaz(yol: Path, satirlar: List[Dict[str, Any]]) -> None:
    with open(yol, "w", encoding="utf-8", newline="") as fh:
        yazici = csv.DictWriter(fh, fieldnames=CSV_BASLIK)
        yazici.writeheader()
        for r in satirlar:
            duz = {k: r[k] for k in ("alinma", "event_id", "kickoff", "home",
                                     "away", "lig", "lig_kodu", "canli")}
            for s in SEMBOLLER:
                duz[f"odd_{s}"] = r["odd"].get(s, "")
                duz[f"wodd_{s}"] = r["wodd"].get(s, "")
            duz["marj"] = "" if r["marj"] is None else r["marj"]
            yazici.writerow(duz)


def sqlite_yaz(yol: Path, satirlar: List[Dict[str, Any]]) -> None:
    """Uzun bicim — `odds.sqlite3` ile ayni sekil, ayni sorgu diliyle okunur.

    Anahtar (alinma, event_id): ayni mac farkli snapshot'larda tekrar
    gorunur ve ISTENEN de budur — acilis/kapanis farki ancak boyle cikar.
    """
    with sqlite3.connect(yol) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS mac (
                alinma TEXT, event_id INTEGER, kickoff TEXT,
                home TEXT, away TEXT, lig TEXT, lig_kodu INTEGER, canli INTEGER,
                PRIMARY KEY (alinma, event_id)
            );
            CREATE TABLE IF NOT EXISTS oran (
                alinma TEXT, event_id INTEGER,
                pazar TEXT, secim TEXT, donem TEXT, deger REAL,
                PRIMARY KEY (alinma, event_id, pazar, secim, donem)
            );
            CREATE INDEX IF NOT EXISTS oran_mac ON oran (event_id, pazar, secim);
        """)
        db.executemany(
            "INSERT OR REPLACE INTO mac VALUES (?,?,?,?,?,?,?,?)",
            [(r["alinma"], r["event_id"], r["kickoff"], r["home"], r["away"],
              r["lig"], r["lig_kodu"], r["canli"]) for r in satirlar],
        )
        # `donem`: oran arsivinde "acilis"/"kapanis" olan alan. Bultende
        # boyle bir ayrim yok; hangi fiyat listesi oldugunu yaziyoruz.
        kayitlar = []
        for r in satirlar:
            for s in SEMBOLLER:
                if s in r["odd"]:
                    kayitlar.append((r["alinma"], r["event_id"], "1X2", s,
                                     "kupon", r["odd"][s]))
                if s in r["wodd"]:
                    kayitlar.append((r["alinma"], r["event_id"], "1X2", s,
                                     "web", r["wodd"][s]))
        db.executemany("INSERT OR REPLACE INTO oran VALUES (?,?,?,?,?,?)", kayitlar)


# ─── giris ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Iddaa acik bulteninin anlik goruntusu")
    ap.add_argument("--dry-run", action="store_true", help="dosya yazma, yalnizca ozet bas")
    ap.add_argument("--no-sqlite", action="store_true", help="SQLite kopyasini uretme")
    ap.add_argument("--kaynak", type=Path, help="indirmek yerine bu ham JSON dosyasini oku")
    ap.add_argument("--out-dir", type=Path, default=CIKTI_DIZIN)
    args = ap.parse_args()

    simdi = datetime.now(timezone.utc)
    alinma = simdi.strftime("%Y-%m-%d %H:%M")
    gun = simdi.strftime("%Y-%m-%d")

    if args.kaynak:
        ham = json.loads(args.kaynak.read_text(encoding="utf-8"))
        ligler: Dict[int, str] = {}
    else:
        try:
            ham = indir(EVENTS_URL)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"bulten alinamadi: {e}", file=sys.stderr)
            return 1
        try:
            ligler = lig_adlari(indir(COMP_URL))
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as e:
            # Lig adi olmadan da snapshot degerlidir; kod zaten satirda duruyor.
            print(f"uyari: lig adlari alinamadi ({e}); lig sutunu bos kalacak")
            ligler = {}

    veri = _govde(ham)
    tum = [e for e in (veri.get("events") or []) if e.get("sid") == FUTBOL_SID]
    satirlar = satirlar_uret(veri, ligler, alinma)

    print(f"bulten surumu : {veri.get('version')}")
    print(f"futbol etkinlik: {len(tum)}")
    print(f"kaydedilen    : {len(satirlar)}")
    if tum and len(satirlar) < len(tum):
        print(f"elenen        : {len(tum) - len(satirlar)} "
              f"(1X2 pazari yok ya da bir ayagi 1.00 — askidaki fiyat)")
    marjlar = [r["marj"] for r in satirlar if r["marj"] is not None]
    if marjlar:
        print(f"ortalama marj : %{100 * sum(marjlar) / len(marjlar):.2f}")
    ligli = sum(1 for r in satirlar if r["lig"])
    print(f"lig etiketli  : {ligli}/{len(satirlar)}")

    if not satirlar:
        print("kaydedilecek mac yok", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        for r in satirlar[:5]:
            print(f"  {r['kickoff']}  {r['home']} - {r['away']}  "
                  f"{r['odd'].get('1')}/{r['odd'].get('0')}/{r['odd'].get('2')}")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "_kaynak").mkdir(exist_ok=True)

    if not args.kaynak:
        ham_yol = args.out_dir / "_kaynak" / f"events_{gun}.json"
        ham_yol.write_text(json.dumps(ham, ensure_ascii=False), encoding="utf-8")

    csv_yol = args.out_dir / f"iddaa_{gun}.csv"
    csv_yaz(csv_yol, satirlar)
    print(f"\nyazildi: {csv_yol}")

    rapor = {
        "taken_at": alinma,
        "source": "sportsbookv2.iddaa.com/sportsbook/events — ACIK bulten, gecmis yok",
        "bulletin_version": veri.get("version"),
        "football_events": len(tum),
        "with_1x2": len(satirlar),
        "dropped": len(tum) - len(satirlar),
        "with_league_label": ligli,
        "avg_margin_pct": round(100 * sum(marjlar) / len(marjlar), 2) if marjlar else None,
        "snapshots": sorted(p.name for p in args.out_dir.glob("iddaa_*.csv")),
        "note": (
            "Tek snapshot analize yetmez; deger haftalik birikimle olusur. "
            "Gecmis iddaa orani hicbir kaynakta yayinlanmadigi icin bu arsiv "
            "ancak ileriye donuk buyur."
        ),
    }
    rapor_yol = args.out_dir / "iddaa_rapor.json"
    rapor_yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(f"yazildi: {rapor_yol}")

    if not args.no_sqlite:
        db_yol = args.out_dir / "iddaa.sqlite3"
        sqlite_yaz(db_yol, satirlar)
        print(f"yazildi: {db_yol} ({len(rapor['snapshots'])} snapshot birikti)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
