#!/usr/bin/env python3
"""Bulten listesini fiksture baglar ve gecmis sezonun 1/0/2 dizisini uretir.

    python scripts/build_gecmis_sezon.py --dry-run     # kapsama raporu
    python scripts/build_gecmis_sezon.py
    python scripts/build_gecmis_sezon.py --sezon 2023_24
    python scripts/build_gecmis_sezon.py --cache /tmp/fd   # CSV'leri sakla

NEDEN VAR
=========
`docs/VERI_TOPLAMA_VE_ISLEME.md` §10.3 gecmis kupon haftasini dort parcaya
ayirmisti:

    (a) hangi hafta, ne zaman kapandi   -> §6D resmi arsiv
    (b) ikramiye tablosu                -> §6D resmi arsiv
    (c) hangi 15 mac, kupon sirasiyla   -> §6F bulten OCR
    (d) skor ve 1/0/2                   -> BU BETIK

Bu betik son parcayi kapatir: bultendeki takim adlarini football-data
fiksturune baglar, skoru oradan alir ve kupon dizisini uretir.

ESLESTIRME BURADA `build_odds.py`DAN DAHA ZORDUR — ve bu bilincli
=================================================================
`build_odds.py` eslestirirken **skoru biliyor** ve onu ayirt edici olarak
kullaniyor: aday ancak skoru da tutuyorsa kabul ediliyor. Burada skor
ARANAN seydir, dolayisiyla o kilit yok.

Yerine konan uc kilit — ucu de "supheliyi ele" yonunde:

  1. **Iki taraf da esiği gecmeli.** Yalnizca ev adinin tutmasi yetmez;
     `EV_ESIK`/`ORTALAMA_ESIK` ikisini birden ister.
  2. **Aday TEK olmali.** Pencerede esigi gecen ikinci bir aday varsa mac
     DUSER. "En iyisini sec" demek, iki benzer adli takim arasinda sessizce
     kura cekmektir.
  3. **15/15 tamamlanmayan hafta DUSER.** Bir mac eksikse o haftanin 1/0/2
     dizisi zaten kurulamaz (doktrin 2).

`sadelestir` ve `benzerlik` **yeniden yazilmadi**, `build_odds.py`dan ice
aktarildi: sponsor eki temizligi, Turkce harf katlamasi ve takim adi
esleri orada zaten olculmus ve test edilmis durumda.

ZAMAN PENCERESI
===============
Bulten mac basina tarih tasimiyor; yalnizca hafta duzeyinde bir aralik var.
Resmi arsivin `close_date` alani ise §10.4'te olculdu: 41 haftanin 41'inde
haftanin **ILK macinin gunune** esit. Bu yuzden pencere `close_date - 1` ile
`close_date + PENCERE_GUN` arasidir; alt sinirdaki bir gun saat dilimi
payidir.

CIKTI
=====
    data/st_history/<sezon>.json        hafta -> 15 mac + 1/0/2 (surumlenir)
    data/st_history/gecmis_rapor.json   kapsama + elenen hafta gerekceleri

`st_history_2025_26.json` ile **karismaz**: o dosya yerinde durur, `/api/stats`
ve 27 degismez ona bakmaya devam eder. Bu dizin ayri bir koken sinifidir
(bulten OCR + fikstur birlestirme) ve meta'sinda bunu yazar.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

BULTEN_DIZIN = KOK / "data" / "bulten"
ARSIV_DIZIN = KOK / "data" / "sportoto_arsiv"
CIKTI_DIZIN = KOK / "data" / "st_history"

from scripts.build_odds import (
    ANA_LIGLER,
    EK_ULKELER,
    benzerlik,
    tarih_coz,
)

UA = "Mozilla/5.0 (compatible; spor-toto-lab/1.0)"
ANA_URL = "https://www.football-data.co.uk/mmz4281/{sezon}/{lig}.csv"
EK_URL = "https://www.football-data.co.uk/new/{ulke}.csv"

MAC_SAYISI = 15

#: Bir kupon haftasi kac gune yayilir. Olculdu: bultendeki aralik basliklari
#: 4-5 gun ("11 AGUSTOS - 15 AGUSTOS"); pencere payli tutuldu.
#:
#: **BU BIR AYAR DEGIL, BIR KORUMADIR — genisletilmemeli.** Olculdu: eslesmeyen
#: maclarin buyuk bolumu ERTELENMIS maclardir ve fiksturde haftalar/aylar sonra
#: duruyorlar:
#:
#:     bulten hf 33 (2024-03-15)  Atalanta - Fiorentina  -> gercekte 2024-06-02
#:     bulten hf 37 (2024-04-12)  Monaco - Lille         -> gercekte 2024-04-24
#:     bulten hf  3 (2023-08-25)  Ad. Demirspor - Besiktas -> gercekte 2023-09-27
#:     bulten hf  4 (2023-09-01)  Ath Madrid - Sevilla   -> gercekte 2023-12-23
#:
#: Ertelenen macin AYLAR SONRAKI sonucu, o haftanin kupon sonucu DEGILDIR.
#: Pencereyi genisletmek bu satirlari "eslesti" gosterir ve sessizce YANLIS
#: bir 1/0/2 dizisi uretir — §7.4'un v1 vakasinin tekrari. Bu yuzden pencere
#: disinda kalan mac DUSER ve onunla birlikte hafta duser.
PENCERE_GUN = 8

#: Tek bir tarafin en az benzerligi. `build_odds.py`nin esigi 0,55'ti ama
#: ORADA skor da tutuyordu; burada o kilit olmadigi icin esik yukseltildi.
TARAF_ESIK = 0.72

#: Iki tarafin ortalamasi. Bir taraf mukemmel, oteki zayifsa kabul etmemek
#: icin ikisi birden istenir.
ORTALAMA_ESIK = 0.82

#: Ikinci adayin en iyiye bu kadar yaklasmasi haftayi supheye dusurur.
#: Aralarindaki fark bunun altindaysa mac DUSER — "en iyisini sec" demek
#: iki benzer adli takim arasinda sessizce kura cekmektir.
AYIRT_EDICI_FARK = 0.08


#: Bultenin TURKCE kulup adlari -> football-data'nin kullandigi ad.
#:
#: `build_odds.py`nin `TAKIM_ESLERI`si kaynak tarafini duzeltir (football-data
#: kisaltmalari); bu tablo BULTEN tarafini duzeltir. Ayri tutulmalari bilincli:
#: biri ucuncu parti bir CSV'nin kisaltma aliskanligi, oteki Spor Toto'nun
#: Turkce yazim tercihi.
#:
#: **Her satir OLCULDU, tahmin edilmedi.** 156 haftalik bultende eslesmeyen
#: adlar sayildi ve yalnizca football-data'da karsiligi DOGRULANANLAR eklendi.
BULTEN_ESLERI = {
    "marsilya": "marseille",
    "bayern munih": "bayern munich",
    "b. munih": "bayern munich",
    "b. leverkusen": "leverkusen",
    "bayer leverkusen": "leverkusen",
    "b. dortmund": "dortmund",
    "borussia dortmund": "dortmund",
    "wolverhampton": "wolves",
    "leipzig": "rb leipzig",
    "m. gladbach": "m'gladbach",
    "monchengladbach": "m'gladbach",
    "sporting lizbon": "sp lisbon",
    "manchester utd": "man united",
    "milano": "milan",
}


def _bulten_adi(ad: str) -> str:
    """Bulten adini football-data'nin kullandigi ada cevirir.

    Ceviri yalnizca TABLODAKI adlar icin yapilir; tabloda olmayan ad
    OLDUGU GIBI birakilir ve bulanik eslestirmeye gider. Yani bu tablo bir
    "yakinsatma" degil, dogrulanmis bir sozluktur (doktrin 2).
    """
    s = (ad or "").lower()
    for a, b in (("\u0131", "i"), ("\u011f", "g"), ("\u015f", "s"),
                 ("\u00f6", "o"), ("\u00fc", "u"), ("\u00e7", "c")):
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    return BULTEN_ESLERI.get(s, ad)


def sezon_kodu(anahtar: str) -> str:
    """"2023_24" -> "2324" (football-data dosya adi)."""
    bas, _, son = anahtar.partition("_")
    return f"{bas[-2:]}{son}"


def indir(url: str, hedef: Path, zaman_asimi: float = 60.0) -> Path | None:
    if hedef.exists() and hedef.stat().st_size > 0:
        return hedef
    try:
        istek = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as cevap:
            ham = cevap.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    if not ham:
        return None
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(ham)
    return hedef


def fikstur(sezon_anahtar: str, cache: Path) -> dict[date, list[dict[str, Any]]]:
    """Gune gore indekslenmis fikstur — skorlariyla birlikte."""
    kod = sezon_kodu(sezon_anahtar)
    dosyalar: list[tuple[str, Path]] = []
    for lig in ANA_LIGLER:
        p = indir(ANA_URL.format(sezon=kod, lig=lig), cache / f"{kod}_{lig}.csv")
        if p:
            dosyalar.append((lig, p))
    for ulke in EK_ULKELER:
        p = indir(EK_URL.format(ulke=ulke), cache / f"new_{ulke}.csv")
        if p:
            dosyalar.append((f"new_{ulke}", p))

    indeks: dict[date, list[dict[str, Any]]] = {}
    for etiket, yol in dosyalar:
        with open(yol, encoding="latin-1", newline="") as fh:
            for ham in csv.DictReader(fh):
                satir = {(k or "").strip().lstrip("﻿").lstrip("ï»¿"): v
                         for k, v in ham.items()}
                dt = tarih_coz((satir.get("Date") or "").strip())
                if not dt:
                    continue
                ev = satir.get("HomeTeam") or satir.get("Home")
                dep = satir.get("AwayTeam") or satir.get("Away")
                eg = satir.get("FTHG") or satir.get("HG")
                dg = satir.get("FTAG") or satir.get("AG")
                if not ev or not dep:
                    continue
                try:
                    eg, dg = int(eg), int(dg)
                except (TypeError, ValueError):
                    continue
                indeks.setdefault(dt.date(), []).append({
                    "lig": satir.get("Div") or etiket,
                    "ev": ev, "dep": dep, "hg": eg, "ag": dg,
                    "tarih": dt.date(),
                })
    return indeks


def _pencere(indeks: dict[date, list[dict[str, Any]]],
             baslangic: date) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for kayma in range(-1, PENCERE_GUN + 1):
        out.extend(indeks.get(baslangic + timedelta(days=kayma), []))
    return out


def eslestir(ev: str, dep: str,
             adaylar: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    """Tek ve yeterince iyi bir aday dondurur; yoksa (None, gerekce)."""
    puanlar: list[tuple[float, dict[str, Any]]] = []
    for aday in adaylar:
        e = benzerlik(_bulten_adi(ev), aday["ev"])
        d = benzerlik(_bulten_adi(dep), aday["dep"])
        if e < TARAF_ESIK or d < TARAF_ESIK:
            continue
        ort = (e + d) / 2
        if ort >= ORTALAMA_ESIK:
            puanlar.append((ort, aday))
    if not puanlar:
        return None, "esigi gecen aday yok"
    puanlar.sort(key=lambda x: -x[0])
    if len(puanlar) > 1 and puanlar[0][0] - puanlar[1][0] < AYIRT_EDICI_FARK:
        # Doktrin 2: belirsizi secmek yerine elemek.
        return None, (f"iki aday ayirt edilemedi ({puanlar[0][0]:.2f} vs "
                      f"{puanlar[1][0]:.2f})")
    return puanlar[0][1], ""


def kod(hg: int, ag: int) -> str:
    return "1" if hg > ag else ("0" if hg == ag else "2")


def hafta_kur(bulten_hafta: dict[str, Any], kapanis: str | None,
              indeks: dict[date, list[dict[str, Any]]]) -> dict[str, Any]:
    kayit: dict[str, Any] = {"week": bulten_hafta["week"], "kabul": False,
                             "red_gerekcesi": None, "matches": [],
                             "data_warnings": []}
    if not kapanis:
        kayit["red_gerekcesi"] = "kapanis tarihi yok"
        return kayit
    try:
        baslangic = datetime.fromisoformat(kapanis).date()
    except ValueError:
        kayit["red_gerekcesi"] = f"kapanis tarihi okunamadi: {kapanis!r}"
        return kayit

    adaylar = _pencere(indeks, baslangic)
    if not adaylar:
        kayit["red_gerekcesi"] = "pencerede hic fikstur yok"
        return kayit

    maclar: list[dict[str, Any]] = []
    eksik: list[str] = []
    for m in bulten_hafta["matches"]:
        aday, gerekce = eslestir(m["home"], m["away"], adaylar)
        if not aday:
            eksik.append(f"{m['no']}. {m['home']} - {m['away']}: {gerekce}")
            continue
        maclar.append({
            "no": m["no"],
            "home": aday["ev"], "away": aday["dep"],
            # Bultendeki OCR adi da saklanir: eslestirme denetlenebilir olmali.
            "bulten_home": m["home"], "bulten_away": m["away"],
            "lig": aday["lig"],
            "kickoff": aday["tarih"].isoformat(),
            "hg": aday["hg"], "ag": aday["ag"],
            "code": kod(aday["hg"], aday["ag"]),
        })

    if len(maclar) != MAC_SAYISI:
        kayit["red_gerekcesi"] = f"{len(maclar)}/{MAC_SAYISI} mac eslesti"
        kayit["data_warnings"] = eksik[:6]
        return kayit

    kayit["matches"] = maclar
    kayit["results"] = "".join(m["code"] for m in maclar)
    kayit["n1"] = kayit["results"].count("1")
    kayit["n0"] = kayit["results"].count("0")
    kayit["n2"] = kayit["results"].count("2")
    kayit["close_date"] = kapanis[:10]
    kayit["kabul"] = True
    return kayit


def dogrula(sezonlar: dict[str, list[dict[str, Any]]]) -> None:
    """Doktrin 5 + doktrin 1: dizi listeden, sayimlar diziden turer."""
    for anahtar, haftalar in sezonlar.items():
        numaralar = [h["week"] for h in haftalar]
        assert len(numaralar) == len(set(numaralar)), f"{anahtar}: mukerrer hafta"
        for h in haftalar:
            assert len(h["matches"]) == MAC_SAYISI, (
                f"{anahtar} hafta {h['week']}: {len(h['matches'])} mac")
            assert [m["no"] for m in h["matches"]] == list(range(1, MAC_SAYISI + 1)), (
                f"{anahtar} hafta {h['week']}: kupon sirasi bozuk")
            turetilen = "".join(kod(m["hg"], m["ag"]) for m in h["matches"])
            assert h["results"] == turetilen, (
                f"{anahtar} hafta {h['week']}: results dizisi maclardan turemiyor")
            assert (h["n1"], h["n0"], h["n2"]) == (
                turetilen.count("1"), turetilen.count("0"), turetilen.count("2")), (
                f"{anahtar} hafta {h['week']}: sayimlar diziyle tutmuyor")


def capraz_dogrula(sezonlar: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Uretilen seti `st_history_2025_26.json` ile karsilastirir.

    **Bu, bu boru hattinin en guclu sinavidir ve BAGIMSIZDIR.** Iki set
    birbirini hic gormeden, tamamen ayri yollardan uretiliyor:

        eski: sportototahmin hafta payload'i (ucuncu parti Nuxt JSON)
        yeni: resmi bulten GORSELI -> OCR -> football-data fiksturu

    Ayni 1/0/2 dizisine variyorlarsa OCR, siralama ve eslestirme birlikte
    dogrulanmis olur. Varmiyorlarsa **hangisinin dogru oldugu bu fonksiyonun
    isi degildir** (doktrin 4): fark raporlanir, biri sessizce secilmez.
    """
    eski_yol = KOK / "data" / "st_history_2025_26.json"
    if not eski_yol.exists():
        return {"kosuldu": False, "gerekce": "st_history_2025_26.json yok"}
    eski = json.loads(eski_yol.read_text(encoding="utf-8"))
    eski_hafta = {w["week"]: w for w in eski["weeks"]}

    ayni, farkli = 0, []
    for anahtar, haftalar in sezonlar.items():
        if anahtar != "2025_26":
            continue
        for h in haftalar:
            karsilik = eski_hafta.get(h["week"])
            if not karsilik:
                continue
            if karsilik["results"] == h["results"]:
                ayni += 1
            else:
                farkli.append({
                    "week": h["week"],
                    "eski": karsilik["results"],
                    "yeni": h["results"],
                    "farkli_sembol": sum(
                        1 for a, b in zip(karsilik["results"], h["results"]) if a != b),
                    "ayni_mac_kumesi": _ayni_kume(karsilik, h),
                })
    return {"kosuldu": True, "ortak_hafta": ayni + len(farkli),
            "birebir_ayni": ayni, "ayrisan": farkli}


def _ayni_kume(eski_hafta: dict[str, Any], yeni_hafta: dict[str, Any]) -> bool:
    """Iki kayit AYNI 15 maci mi tasiyor (sira dikkate alinmadan)?

    Bu ayrimi yapmak sart: ayni maclar farkli SIRADA ise sorun sonucta degil
    KUPON SIRASINDADIR ve bu, §7.4'un v1 vakasiyla ayni sinifta bir bulgudur.
    """
    # Adlar iki kaynakta farkli yazildigi icin (sponsor ekleri, Turkce
    # exonimler) skor kumesi daha guvenilir bir kimliktir.
    return ({(m["hg"], m["ag"]) for m in eski_hafta["matches"]}
            == {(m["hg"], m["ag"]) for m in yeni_hafta["matches"]})


def _kapanis_tablosu(anahtar: str) -> dict[int, str]:
    yol = ARSIV_DIZIN / f"{anahtar}.json"
    if not yol.exists():
        return {}
    govde = json.loads(yol.read_text(encoding="utf-8"))
    return {w["week"]: w["close_date"] for w in govde["weeks"]
            if w.get("week") is not None and w.get("close_date")}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Bulten listesini fiksture baglayip 1/0/2 uretir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sezon", action="append")
    ap.add_argument("--cache", type=Path, default=CIKTI_DIZIN / "_kaynak")
    ap.add_argument("--out-dir", type=Path, default=CIKTI_DIZIN)
    args = ap.parse_args()

    dosyalar = sorted(p for p in BULTEN_DIZIN.glob("*.json")
                      if p.name != "bulten_rapor.json")
    if args.sezon:
        dosyalar = [p for p in dosyalar if p.stem in set(args.sezon)]
    if not dosyalar:
        print("bulten verisi yok — once scripts/build_bulten.py", file=sys.stderr)
        return 1

    kabul: dict[str, list[dict[str, Any]]] = {}
    red: list[dict[str, Any]] = []
    for yol in dosyalar:
        anahtar = yol.stem
        govde = json.loads(yol.read_text(encoding="utf-8"))
        kapanislar = _kapanis_tablosu(anahtar)
        print(f"\n{anahtar}: {len(govde['weeks'])} hafta, fikstur indiriliyor...")
        indeks = fikstur(anahtar, args.cache)
        print(f"  fikstur: {sum(len(v) for v in indeks.values())} mac, "
              f"{len(indeks)} gun")
        for hafta in govde["weeks"]:
            kayit = hafta_kur(hafta, kapanislar.get(hafta["week"]), indeks)
            kayit["season"] = govde["meta"]["season"]
            if kayit["kabul"]:
                kabul.setdefault(anahtar, []).append(kayit)
            else:
                red.append({"season_key": anahtar, "week": hafta["week"],
                            "gerekce": kayit["red_gerekcesi"],
                            "ornek": kayit.get("data_warnings", [])[:3]})
        n = len(kabul.get(anahtar, []))
        print(f"  kabul: {n}/{len(govde['weeks'])}")

    toplam = sum(len(v) for v in kabul.values())
    denenen = toplam + len(red)
    print(f"\nkabul edilen hafta: {toplam}/{denenen}")
    if red:
        print(f"elenen: {len(red)}")
        for g, adet in Counter(
                (r["gerekce"] or "")[:44] for r in red).most_common(6):
            print(f"  {adet:>3} x {g}")

    for haftalar in kabul.values():
        haftalar.sort(key=lambda h: h["week"] or 0)

    try:
        dogrula(kabul)
    except AssertionError as e:
        print(f"\nDOGRULAMA BASARISIZ, dosya yazilmadi: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0
    if not kabul:
        print("yazilacak hafta yok", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    uretildi = datetime.now().strftime("%Y-%m-%d")
    for anahtar, haftalar in sorted(kabul.items()):
        toplamlar = Counter(c for h in haftalar for c in h["results"])
        govde = {
            "meta": {
                "season": haftalar[0]["season"],
                "season_key": anahtar,
                "weeks": len(haftalar),
                "matches": len(haftalar) * MAC_SAYISI,
                "source": ("bulten GORSELI (OCR, §6F) + football-data.co.uk "
                           "fiksturu — takim adlari eslestirilerek baglandi"),
                "rule": (f"yalnizca {MAC_SAYISI}/{MAC_SAYISI} eslesen hafta; "
                         "iki aday ayirt edilemezse mac DUSER"),
                "generated_at": uretildi,
                "origin": "turetilmis (OCR + fikstur birlestirme)",
                "note": ("`st_history_2025_26.json` ile KARISMAZ: o dosya ucuncu "
                         "parti hafta payload'indan gelir ve /api/stats ona bakar. "
                         "Bu dizin ayri bir koken sinifidir."),
            },
            "totals": {s: toplamlar.get(s, 0) for s in ("1", "0", "2")},
            "weeks": [{k: v for k, v in h.items()
                       if k not in ("kabul", "red_gerekcesi")} for h in haftalar],
        }
        yol = args.out_dir / f"{anahtar}.json"
        yol.write_text(json.dumps(govde, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        print(f"yazildi: {yol}")

    capraz = capraz_dogrula(kabul)
    if capraz.get("kosuldu"):
        print(f"\ncapraz dogrulama (st_history_2025_26 ile ortak hafta): "
              f"{capraz['birebir_ayni']}/{capraz['ortak_hafta']} BIREBIR AYNI")
        for f in capraz["ayrisan"]:
            print(f"  hf {f['week']}: {f['farkli_sembol']} sembol farkli, "
                  f"ayni mac kumesi: {f['ayni_mac_kumesi']}")

    rapor = {
        "generated_at": uretildi,
        "capraz_dogrulama": capraz,
        "denenen_hafta": denenen,
        "kabul_edilen": toplam,
        "elenen": len(red),
        "seasons": {a: len(v) for a, v in sorted(kabul.items())},
        "esikler": {"taraf": TARAF_ESIK, "ortalama": ORTALAMA_ESIK,
                    "ayirt_edici_fark": AYIRT_EDICI_FARK,
                    "pencere_gun": PENCERE_GUN},
        "elenenler": red,
        "limits": [
            "Eslestirme SKORSUZ yapilir; build_odds.py'nin skor kilidi burada yok.",
            "Iki aday ayirt edilemezse mac DUSER, en iyisi secilmez.",
            "Takim adlari OCR ciktisindan gelir (§6F).",
            "Oran ve mac istatistigi bu sette YOK.",
        ],
    }
    (args.out_dir / "gecmis_rapor.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazildi: {args.out_dir / 'gecmis_rapor.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
