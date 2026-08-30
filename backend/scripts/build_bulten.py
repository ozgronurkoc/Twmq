#!/usr/bin/env python3
"""Bulten gorselinden haftanin 15 macini okur (OCR) ve DOGRULAR.

    python scripts/build_bulten.py --dry-run          # kapsama raporu, yazmadan
    python scripts/build_bulten.py                    # tum sezonlari oku ve yaz
    python scripts/build_bulten.py --sezon 2023_24
    python scripts/build_bulten.py --hafta 2023_24:1  # tek hafta, ham OCR ile

NEDEN VAR
=========
`docs/VERI_TOPLAMA_VE_ISLEME.md` §10.3: resmi arsiv (§6D) haftalarin
kendisini ve ikramiye tablosunu veriyor, ama MAC LISTESI vermiyor — o
yalnizca bir bulten GORSELI olarak yayimlaniyor. Gecmis sezon kupon
verisinin onundeki tek engel bu.

Gorseller **makine uretimi**dir: sabit sablon, yuksek kontrast, numarali
satirlar, `EV - DEPLASMAN` bicimi. Yani OCR burada bir umut degil, uygun
bir arac.

DOKTRIN 2 BURADA GEVSEMEZ, SIKISIR
==================================
**OCR ciktisi bir VERI DEGIL, bir ARAMA ANAHTARIDIR.**

Bu betik yalnizca okur ve dogrular; okudugunu "duzeltmez", eksigi
tamamlamaz, benzer isme yuvarlamaz. Bir hafta 15/15 cikmiyorsa **elenir**
ve gerekcesi rapora yazilir. Okunan adin gercek bir takima karsilik gelip
gelmedigi bu betigin isi degildir — o `build_gecmis_sezon.py`de,
football-data fiksturune karsi yapilir ve orada da eslesmeyen mac duser.

Gerekce §7.4'un vakasidir: v1'de sira hatasi 41 haftanin 15'ini bozdu ve
fark edilmedi. Sessizce yanlis bir kupon dizisi uretmek, hic veri
olmamasindan kotudur.

BAGIMLILIK — ve bunun neden ayri tutuldugu
==========================================
Bu betik deponun **stdlib disina cikan tek** uretim betigidir: `tesseract`
(sistem paketi) ve `pillow`. Bu yuzden:

  * `pyproject.toml`da `ocr` EKSTRASIDIR, varsayilan kuruluma girmez
  * `scripts/check.sh` ve CI onu kurmaz; testler bagimlilik yoksa ATLAR
  * urettigi cikti surumlenir, yani tekrar uretmek icin kimsenin
    tesseract kurmasi gerekmez

Kurulum:  apt-get install tesseract-ocr tesseract-ocr-tur
          pip install -e "./backend[ocr]"

OLCULEN AYARLAR
===============
Ayarlar denenerek secildi, varsayilmadi:

  --psm 4    Sutunlu metin. psm 6 (tek blok) ayni gorselde 15 satirin
             9'unu okuyabildi ve adlari bozdu ("BAŞAKŞEMİM FK"); psm 11
             ve 12 tabloyu hic goremedi.
  x3 olcek   Kucuk gorseller (595x756) x1'de 9/15, x2'de 14/15, x3'te
             15/15 verdi. Buyuk gorseller x2'de zaten tamdi; x3 ikisini
             de tamamladi, o yuzden tek ayar.
  -l tur     Turkce harfler (İ, Ş, Ğ, Ç, Ö, Ü) sart.

CIKTI
=====
    data/bulten/<sezon>.json       hafta -> 15 mac (surumlenir)
    data/bulten/bulten_rapor.json  kapsama + elenen hafta gerekceleri
    data/bulten/_kaynak/*.jpg      indirilen gorsel (git disi)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
ARSIV_DIZIN = KOK / "data" / "sportoto_arsiv"
CIKTI_DIZIN = KOK / "data" / "bulten"
UA = "spor-toto-lab/1.0 (kisisel arsiv analizi)"

MAC_SAYISI = 15

#: Olculdu (modul basligi). Degistirmeden once yeniden olc.
OLCEK = 3
PSM = "4"
DIL = "tur"

#: "1. | TRABZONSPOR A.Ş. - ANTALYASPOR A.Ş."
#: Ayirici sutun cizgisi OCR'da `|`, `!`, `I` ya da hic cikmayabilir;
#: hepsi ayni sey oldugu icin desende istege bagli.
SATIR_DESENI = re.compile(r"^\s*(\d{1,2})\s*[.)]\s*(.+?)\s*$")

#: "11 AĞUSTOS- 15 AĞUSTOS 2023 (1. HAFTA)"
BASLIK_DESENI = re.compile(r"\((\d{1,2})\s*\.?\s*HAFTA\)", re.IGNORECASE)

#: Ev ve deplasmani ayiran tire — IKI KADEMELI.
#:
#: Takim adlarinin ICINDE de tire olabilir ("SAINT-ETIENNE"), bu yuzden once
#: BOSLUKLA CEVRILI tire denenir. Ama OCR bir boslugu yutabiliyor: olculdu,
#: 2023/24 6. haftada 7. satir `KONYASPOR -RİZESPOR` cikti ve tek parca
#: sayilip hafta elendi. Bu yuzden sikisi tutmazsa **en az bir tarafinda**
#: bosluk olan tire denenir. Iki tarafi da bosluksuz tire ASLA ayirici
#: sayilmaz — o takim adinin kendi tiresidir.
AYIRICI = re.compile(r"\s+[-–—]\s+")
AYIRICI_GEVSEK = re.compile(r"\s+[-–—]|[-–—]\s+")


def _ikiye_ayir(govde: str) -> list[str]:
    """Once siki, tutmazsa gevsek ayirici. Ikisi de tutmazsa bos liste."""
    for desen in (AYIRICI, AYIRICI_GEVSEK):
        parcalar = desen.split(govde)
        if len(parcalar) == 2:
            return parcalar
    return []


#: OCR'in sutun cizgisinden urettigi tek karakterlik artiklar. Gorselde
#: dikey bir cizgi var ve tesseract onu `|`, `!`, `I`, `İ`, `l` ya da `]`
#: olarak okuyabiliyor ("12.İ VALENCİA" gibi). Takim adi tek harfle
#: baslamadigi icin bastaki tek karakterlik boyle bir belirtec atilir.
ARTIK_BAS = re.compile(r"^[|!I\u0130l\]\}i1]\s+")


def gorsel_indir(url: str, hedef: Path, zaman_asimi: float = 60.0) -> bytes:
    if hedef.exists():
        return hedef.read_bytes()
    istek = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as cevap:
        ham = cevap.read()
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(ham)
    return ham


def ocr_metni(gorsel: Path, olcek: int = OLCEK) -> str:
    """Gorseli olcekleyip griye cevirir ve tesseract'a verir.

    Olcekleme sart: kucuk gorsellerde harf yuksekligi tesseract'in
    isabetli calistigi araligin altinda kaliyor ve satirlar dusuyor.
    """
    from PIL import Image  # ocr ekstrasi

    with Image.open(gorsel) as im:
        buyuk = im.resize((im.width * olcek, im.height * olcek),
                          Image.LANCZOS).convert("L")
        gecici = gorsel.with_suffix(f".x{olcek}.png")
        buyuk.save(gecici)
    try:
        sonuc = subprocess.run(
            ["tesseract", str(gecici), "-", "-l", DIL, "--psm", PSM, "--dpi", "300"],
            capture_output=True, text=True, timeout=180, check=True,
        )
    finally:
        gecici.unlink(missing_ok=True)
    return sonuc.stdout


def _temizle(ad: str) -> str:
    """Yalnizca BICIMSEL temizlik — icerige dokunmaz.

    Fazla bosluk, satir sonu artigi ve OCR'in sutun cizgisinden urettigi
    kuyruk karakterleri atilir. Harf DUZELTILMEZ: "BAŞAKŞEMİM"i
    "BAŞAKŞEHİR"e cevirmek tam olarak doktrin 2'nin yasakladigi seydir —
    o is football-data fiksturune karsi eslestirmede yapilir ve orada
    tutmayan mac DUSER.
    """
    ad = ARTIK_BAS.sub("", ad.strip())
    ad = re.sub(r"[|!\[\]{}©®“”\"']+", " ", ad)
    # NOKTA ATILMAZ: Turk kulup adlarinin cogu "A.Ş." / "F.K." ile biter ve
    # sondaki noktayi kirpmak ADI DEGISTIRIR — bicimsel temizlik degil,
    # icerige mudahale olur. Yalnizca virgul, tire ve bosluk kirpilir.
    ad = re.sub(r"[,\-–—\s]+$", "", ad)
    return re.sub(r"\s+", " ", ad).strip()


def satirlari_ayristir(metin: str) -> tuple[dict[int, tuple[str, str]], list[str]]:
    """OCR metninden numara -> (ev, dep). Ikinci deger uyari listesidir.

    **Numara konumdan kurtarilir, ama uydurulmaz.** Olculdu: sol sutundaki
    kucuk rakam gorsele gore dusebiliyor — 2023/24 5. haftada 15 mac adinin
    tamami dogru okundu, numaralarin yalnizca 3'u cikti. Numarayi "eksik"
    sayip haftayi elemek, elde tam ve dogru bir liste varken veri atmaktir.

    Sira **gorselin kendi sirasidir** (doktrin 3): bulten satirlari yukaridan
    asagiya kupon sirasindadir ve OCR o sirayi korur. Bu yuzden basliktan
    sonra gelen ve `EV - DEPLASMAN` bicimine uyan satirlar sirayla 1..15
    sayilir.

    **Uydurma olmamasini saglayan iki kilit var:**

    1. Tam olarak 15 satir bulunmali. 14 ya da 16 satirda hafta ELENIR —
       hangisinin kaydigi bilinemez.
    2. Numarasi OKUNABILEN her satir, konumundan gelen numarayla AYNI
       olmali. Bir tanesi bile tutmuyorsa hafta ELENIR. Bu, §7.4'un v1 sira
       hatasinin (41 haftanin 15'i bozuk) tekrarina karsi bekcidir.
    """
    satirlar = metin.splitlines()
    basi = 0
    for i, ham in enumerate(satirlar):
        if BASLIK_DESENI.search(ham):
            basi = i + 1
            break

    adaylar: list[tuple[int | None, str, str]] = []
    uyarilar: list[str] = []
    for ham in satirlar[basi:]:
        m = SATIR_DESENI.match(ham)
        if m:
            acik_no: int | None = int(m.group(1))
            govde = m.group(2)
            if acik_no is not None and not 1 <= acik_no <= MAC_SAYISI:
                continue
        else:
            acik_no, govde = None, ham

        parcalar = _ikiye_ayir(_temizle(govde))
        if len(parcalar) != 2:
            continue
        ev, dep = (_temizle(x) for x in parcalar)
        if not ev or not dep:
            continue
        adaylar.append((acik_no, ev, dep))

    if len(adaylar) != MAC_SAYISI:
        uyarilar.append(
            f"{len(adaylar)} mac satiri bulundu, {MAC_SAYISI} bekleniyordu")
        return {}, uyarilar

    maclar: dict[int, tuple[str, str]] = {}
    for konum, (acik_no, ev, dep) in enumerate(adaylar, 1):
        if acik_no is not None and acik_no != konum:
            # Sira kaydi: hangi satirin kaydigi bilinemez, hafta elenir.
            uyarilar.append(
                f"{konum}. sirada okunan numara {acik_no} — sira tutmuyor")
            return {}, uyarilar
        maclar[konum] = (ev, dep)
    okunan = sum(1 for a, _, _ in adaylar if a is not None)
    if okunan < MAC_SAYISI:
        uyarilar.append(
            f"{MAC_SAYISI - okunan} satirin numarasi okunamadi, sira konumdan "
            f"alindi (okunan {okunan} numaranin hepsi tuttu)")
    return maclar, uyarilar


def hafta_no_oku(metin: str) -> int | None:
    """Basliktaki "(N. HAFTA)" — arsivdeki hafta numarasinin CAPRAZ kontrolu."""
    m = BASLIK_DESENI.search(metin)
    return int(m.group(1)) if m else None


def hafta_oku(hafta: dict[str, Any], kaynak_dizin: Path) -> dict[str, Any]:
    """Bir haftanin bultenini okur. Cikti her zaman doner; `kabul` bayragi karar."""
    gorsel = hafta.get("bulletin_image")
    kayit: dict[str, Any] = {
        "week": hafta.get("week"),
        "season": hafta.get("season"),
        "game_round_id": hafta.get("game_round_id"),
        "kabul": False,
        "red_gerekcesi": None,
        "matches": [],
        "data_warnings": [],
    }
    if not gorsel:
        kayit["red_gerekcesi"] = "bulten gorseli yok"
        return kayit

    ad = gorsel["name"]
    try:
        gorsel_indir(gorsel["url"], kaynak_dizin / ad)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        kayit["red_gerekcesi"] = f"gorsel indirilemedi: {e}"
        return kayit

    try:
        metin = ocr_metni(kaynak_dizin / ad)
    except (subprocess.SubprocessError, OSError) as e:
        kayit["red_gerekcesi"] = f"OCR calistirilamadi: {e}"
        return kayit

    maclar, uyarilar = satirlari_ayristir(metin)
    kayit["data_warnings"] = uyarilar
    kayit["okunan_satir"] = len(maclar)

    basliktaki = hafta_no_oku(metin)
    if basliktaki is not None and hafta.get("week") is not None:
        if basliktaki != hafta["week"]:
            # Doktrin 4: celiski gizlenmez. Ve bu celiski agirdir —
            # yanlis haftanin gorseli okunuyor olabilir.
            kayit["red_gerekcesi"] = (
                f"basliktaki hafta ({basliktaki}) arsivdekiyle ({hafta['week']}) "
                "uyusmuyor")
            return kayit
    kayit["basliktaki_hafta"] = basliktaki

    eksik = [n for n in range(1, MAC_SAYISI + 1) if n not in maclar]
    if eksik:
        kayit["red_gerekcesi"] = f"{MAC_SAYISI - len(eksik)}/{MAC_SAYISI} satir okundu"
        return kayit

    kayit["matches"] = [
        {"no": n, "home": maclar[n][0], "away": maclar[n][1]}
        for n in range(1, MAC_SAYISI + 1)
    ]
    kayit["kabul"] = True
    return kayit


def dogrula(sezonlar: dict[str, list[dict[str, Any]]]) -> None:
    """Doktrin 5: dogrulanmadan yazilmaz."""
    for anahtar, haftalar in sezonlar.items():
        for h in haftalar:
            assert h["kabul"], f"{anahtar}: kabul edilmemis hafta yazilamaz"
            assert len(h["matches"]) == MAC_SAYISI, (
                f"{anahtar} hafta {h['week']}: {len(h['matches'])} mac")
            numaralar = [m["no"] for m in h["matches"]]
            assert numaralar == list(range(1, MAC_SAYISI + 1)), (
                f"{anahtar} hafta {h['week']}: sira bozuk — kupon sirasi kaynagin "
                "kendi sirasidir (doktrin 3)")
            for m in h["matches"]:
                assert m["home"] and m["away"], (
                    f"{anahtar} hafta {h['week']}: bos takim adi")
        haftalar_no = [h["week"] for h in haftalar]
        assert len(haftalar_no) == len(set(haftalar_no)), f"{anahtar}: mukerrer hafta"


def arsiv_haftalari(sezonlar: list[str] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for yol in sorted(ARSIV_DIZIN.glob("*.json")):
        if yol.name == "arsiv_rapor.json":
            continue
        if sezonlar and yol.stem not in sezonlar:
            continue
        govde = json.loads(yol.read_text(encoding="utf-8"))
        for hafta in govde["weeks"]:
            kayit = dict(hafta)
            kayit["season_key"] = govde["meta"]["season_key"]
            out.append(kayit)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulten gorselinden 15 maci oku")
    ap.add_argument("--dry-run", action="store_true", help="yazmadan kapsama raporu")
    ap.add_argument("--sezon", action="append", help="yalnizca bu sezon, or. 2023_24")
    ap.add_argument("--hafta", help="tek hafta: <sezon>:<no>, ham OCR de basilir")
    ap.add_argument("--limit", type=int, help="ilk N haftayi dene (deneme kosumu)")
    ap.add_argument("--out-dir", type=Path, default=CIKTI_DIZIN)
    args = ap.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("pillow kurulu degil: pip install -e './backend[ocr]'", file=sys.stderr)
        return 1
    try:
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.SubprocessError):
        print("tesseract bulunamadi: apt-get install tesseract-ocr tesseract-ocr-tur",
              file=sys.stderr)
        return 1

    kaynak = args.out_dir / "_kaynak"
    kaynak.mkdir(parents=True, exist_ok=True)

    if args.hafta:
        sezon, _, no = args.hafta.partition(":")
        adaylar = [h for h in arsiv_haftalari([sezon]) if str(h.get("week")) == no]
        if not adaylar:
            print(f"hafta bulunamadi: {args.hafta}", file=sys.stderr)
            return 1
        hafta = adaylar[0]
        print(ocr_metni(kaynak / hafta["bulletin_image"]["name"])
              if (kaynak / hafta["bulletin_image"]["name"]).exists()
              else "(gorsel indiriliyor...)")
        kayit = hafta_oku(hafta, kaynak)
        print(json.dumps(kayit, ensure_ascii=False, indent=1))
        return 0 if kayit["kabul"] else 1

    haftalar = [h for h in arsiv_haftalari(args.sezon) if h.get("bulletin_image")]
    if args.limit:
        haftalar = haftalar[:args.limit]
    print(f"bulten gorseli olan hafta: {len(haftalar)}")

    kabul: dict[str, list[dict[str, Any]]] = {}
    red: list[dict[str, Any]] = []
    for i, hafta in enumerate(haftalar, 1):
        kayit = hafta_oku(hafta, kaynak)
        if kayit["kabul"]:
            kabul.setdefault(hafta["season_key"], []).append(kayit)
        else:
            red.append({"season_key": hafta["season_key"], "week": hafta.get("week"),
                        "gerekce": kayit["red_gerekcesi"],
                        "okunan_satir": kayit.get("okunan_satir")})
        if i % 20 == 0:
            print(f"  ... {i}/{len(haftalar)}")

    toplam_kabul = sum(len(v) for v in kabul.values())
    print(f"\nkabul edilen hafta: {toplam_kabul}/{len(haftalar)} "
          f"(%{100 * toplam_kabul / len(haftalar):.1f})" if haftalar else "")
    for anahtar in sorted(kabul):
        print(f"  {anahtar}  {len(kabul[anahtar])} hafta")
    if red:
        print(f"\nelenen hafta: {len(red)}")
        from collections import Counter
        for gerekce, adet in Counter(
                (r["gerekce"] or "")[:48] for r in red).most_common(8):
            print(f"  {adet:>3} x {gerekce}")

    try:
        dogrula(kabul)
    except AssertionError as e:
        print(f"\nDOGRULAMA BASARISIZ, dosya yazilmadi: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cekildi = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    for anahtar in sorted(kabul):
        haftalar_k = sorted(kabul[anahtar], key=lambda h: h["week"] or 0)
        govde = {
            "meta": {
                "season": haftalar_k[0]["season"],
                "season_key": anahtar,
                "weeks": len(haftalar_k),
                "source": ("sportoto.gov.tr resmi bulten GORSELI, OCR ile okundu "
                           "(tesseract --psm 4 -l tur, x3 olcek)"),
                "generated_at": cekildi,
                "contains": "15 mac, KUPON SIRASIYLA — takim ADLARI",
                "does_not_contain": (
                    "skor, sonuc (1/0/2) ve oran YOK. Takim adlari OCR ciktisidir "
                    "ve DOGRULANMAMISTIR — gercek fiksture eslestirme "
                    "build_gecmis_sezon.py'nin isidir; eslesmeyen mac orada duser."
                ),
                "rule": f"yalnizca {MAC_SAYISI}/{MAC_SAYISI} okunan hafta yazilir",
            },
            "weeks": [{k: v for k, v in h.items()
                       if k not in ("kabul", "red_gerekcesi")} for h in haftalar_k],
        }
        yol = args.out_dir / f"{anahtar}.json"
        yol.write_text(json.dumps(govde, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        print(f"yazildi: {yol}")

    rapor = {
        "generated_at": cekildi,
        "source": "sportoto.gov.tr bulten gorseli (OCR)",
        "settings": {"psm": PSM, "lang": DIL, "scale": OLCEK},
        "denenen_hafta": len(haftalar),
        "kabul_edilen": toplam_kabul,
        "elenen": len(red),
        "seasons": {a: len(v) for a, v in sorted(kabul.items())},
        "elenenler": red,
        "limits": [
            "Takim adlari OCR ciktisidir; DOGRULANMAMIS metindir.",
            "Skor, sonuc ve oran bu sette YOK.",
            f"{MAC_SAYISI}/{MAC_SAYISI} okunmayan hafta ELENIR, doldurulmaz.",
            "Bulten gorselleri 2023/2024'ten itibaren erisilebiliyor.",
        ],
    }
    (args.out_dir / "bulten_rapor.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazildi: {args.out_dir / 'bulten_rapor.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
