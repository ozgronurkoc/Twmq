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

#: Kapanis cizgisinin kaynak tercihi — piyasanin son sozu.
KAPANIS_SIRASI: Tuple[str, ...] = ("AvgC", "B365C", "PSC")

#: Acilis cizgisinin kaynak tercihi — piyasanin ilk sozu.
#:
#: **Ikisi ayri ayri tasinir, cunku A1 sorusu tam olarak ikisinin FARKIdir**
#: (bkz. `docs/ISTATISTIK_YOL_HARITASI.md` §6.2 A1). Onceki surum yalnizca
#: tercih sirasindaki ilk tam ucluyu yaziyordu; kapanis varsa acilis
#: kayboluyordu ve hareket olculemez haldeydi.
#:
#: Sira icinde kaynak karisimi kasitli olarak YASAK degil ama olculurken
#: onemlidir: `Avg` butun bahisci ortalamasi, `B365`/`PS` tek bahisci. Ayni
#: macin acilisi `Avg`, kapanisi `B365C` cikarsa aradaki fark hareket degil
#: kaynak farki olurdu. Bu yuzden `cizgi_cifti` yalnizca **ayni ailenin**
#: iki ucunu esler (`Avg`↔`AvgC`, `B365`↔`B365C`, `PS`↔`PSC`).
ACILIS_SIRASI: Tuple[str, ...] = ("Avg", "B365", "PS")

#: Acilis→kapanis eslesmesi: ayni bahisci ailesinin iki ucu.
CIZGI_AILELERI: Tuple[Tuple[str, str], ...] = (
    ("Avg", "AvgC"), ("B365", "B365C"), ("PS", "PSC"),
)

#: A2 (bahisci anlasmazligi) icin tasinan KAPANIS kaynaklari.
#:
#: Kaynak secimi olcumun kendisini belirledigi icin gerekcesi burada durur.
#: football-data 7 tekil bahisci disa aktariyor ama **kapsamalari sezona
#: gore degisiyor** (olculdu, 31.132 mac uzerinde):
#:
#:     B365C  %100 %100 %100 %100      PSC   %100 %100 %100 %100
#:     BWC    %99  %100 %97  %63       WHC   %99  %91  %94  %76
#:     BFC    %0   %0   %0   %100      1XBC  %0   %0   %0   %100
#:
#: BW/WH/BF/1XB/BFE eklenirse kesit **sezona gore dengesizlesir**: dortlunun
#: tamamini isteyen bir filtre 2425'in %40'ini atar. Sezon disarida birakmali
#: olcumde bu sessiz bir yanliliktir — model bir sezonu digerlerinden farkli
#: bir mac evreninde ogrenir. Bu yuzden yalnizca dort sezonda da ~%100 olan
#: kaynaklar tasinir.
#:
#: `MaxC` ve `AvgC` tekil bahisci degil, football-data'nin BUTUN bahisciler
#: uzerinden hesapladigi ozetlerdir; ikisinin arasindaki acik en genis
#: anlasmazlik olcusudur. Bedeli: `Max`, bahisci sayisi degistikce mekanik
#: olarak kayar (olculdu: ln(Max/Avg) sezonlara gore 0,0712→0,0577). Bu
#: yuzden A2'nin BIRINCIL ozelligi sabit `B365`↔`PS` cifti, `Max/Avg` ise
#: ikincil ve betimleyici kalir (bkz. `egitim.bahisci_ayrismasi`).
A2_KAYNAKLARI: Tuple[Tuple[str, str], ...] = (
    ("B365C", "b_B365"), ("PSC", "b_PS"), ("MaxC", "b_Max"), ("AvgC", "b_Avg"),
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


def _ucluyu_oku(satir: Dict[str, Any], onek: str) -> Optional[Dict[str, float]]:
    """Tek kaynagin 1X2 ucluSU. Biri eksik/askidaysa (<=1.00) kaynak dusEr."""
    degerler = [_sayi(satir.get(f"{onek}{s}")) for s in ("H", "D", "A")]
    if any(v is None for v in degerler):
        return None
    return {"1": degerler[0], "0": degerler[1], "2": degerler[2]}


def cizgi_sec(satir: Dict[str, Any], sira: Tuple[str, ...]) -> Optional[Dict[str, Any]]:
    """Verilen tercih sirasindaki ilk tam ucluyu dondur (yoksa None).

    Ucunden biri eksikse ya da 1.00 ise (askiya alinmis ayak) o kaynak
    atlanir; hicbiri tam degilse **uydurulmaz** (doktrin 2), None doner.
    """
    for onek in sira:
        uclu = _ucluyu_oku(satir, onek)
        if uclu is not None:
            return {**uclu, "kaynak": onek}
    return None


def cizgi_cifti(satir: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Ayni bahisci ailesinden acilis+kapanis cifti (yoksa None).

    A1'in olctugu hareket ancak **ayni kaynagin** iki ucu arasinda anlamlidir;
    `Avg` acilis ile `B365C` kapanis arasindaki fark hareketi degil kaynak
    farkini olcerdi. Bir aile ancak iki ucu da tamsa kabul edilir.
    """
    for acilis_onek, kapanis_onek in CIZGI_AILELERI:
        acilis = _ucluyu_oku(satir, acilis_onek)
        kapanis = _ucluyu_oku(satir, kapanis_onek)
        if acilis is not None and kapanis is not None:
            return {"acilis": acilis, "acilis_kaynak": acilis_onek,
                    "kapanis": kapanis, "kapanis_kaynak": kapanis_onek}
    return None


def bahisci_dortlusu(satir: Dict[str, Any]) -> Optional[Dict[str, Dict[str, float]]]:
    """A2 kaynaklarinin dordu birden (yoksa None).

    **Ya dordu ya hicbiri.** Anlasmazlik, eksik bir kaynak kumesinden
    hesaplaninca maclar arasinda KARSILASTIRILAMAZ hale gelir: uc kaynagin
    yayilimi ile dort kaynagin yayilimi ayni sayi degildir. Kismi dortlu
    kabul etseydik "anlasmazlik" sutunu, anlasmazligi degil hangi kaynaklarin
    o gun mevcut oldugunu olcerdi.
    """
    out: Dict[str, Dict[str, float]] = {}
    for onek, ad in A2_KAYNAKLARI:
        uclu = _ucluyu_oku(satir, onek)
        if uclu is None:
            return None
        out[ad] = uclu
    return out


def oran_sec(satir: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Macin **birincil** orani — once kapanis, sonra acilis.

    `oran_*` sutunlari bunu tasir ve `piyasa` tahmincisinin okudugu sey budur:
    kapanis orani acilistan daha bilgilidir, varsa o kullanilir. Acilis ve
    kapanis ayrica **kendi sutunlarinda** tasinir (bkz. `cizgi_cifti`); bu
    fonksiyon onlarin yerine gecmez, sadece tek bir oran isteyen cagirana
    hangisinin secildigini soyler.
    """
    kapanis = cizgi_sec(satir, KAPANIS_SIRASI)
    if kapanis is not None:
        return {**kapanis, "kapanis": True}
    acilis = cizgi_sec(satir, ACILIS_SIRASI)
    if acilis is not None:
        return {**acilis, "kapanis": False}
    return None


def satirlari_coz(sezon: str, lig: str, yol: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Bir lig-sezon dosyasindan gecerli mac satirlari."""
    sayac = {"toplam": 0, "tarih_yok": 0, "sonuc_yok": 0, "oran_yok": 0,
             "cizgi_cifti_yok": 0, "bahisci_dortlusu_yok": 0}
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

            # Cift yoksa mac ELENMEZ: `oran_*` tamdir, mac tahminci olcumune
            # girer; yalnizca A1 kesitine giremez. Eleseydik korpus kuculur ve
            # onceki olcumlerle karsilastirilamaz hale gelirdi.
            cift = cizgi_cifti(satir)
            if cift is None:
                sayac["cizgi_cifti_yok"] += 1
            cizgi = {
                "acilis_1": "", "acilis_0": "", "acilis_2": "", "acilis_kaynak": "",
                "kapanis_1": "", "kapanis_0": "", "kapanis_2": "", "kapanis_kaynak": "",
            }
            if cift is not None:
                for s in ("1", "0", "2"):
                    cizgi[f"acilis_{s}"] = cift["acilis"][s]
                    cizgi[f"kapanis_{s}"] = cift["kapanis"][s]
                cizgi["acilis_kaynak"] = cift["acilis_kaynak"]
                cizgi["kapanis_kaynak"] = cift["kapanis_kaynak"]

            # Bahisci dortlusu de eksikse mac elenmez; yalnizca A2 kesitine
            # giremez (cizgi cifti ile ayni gerekce).
            dortlu = bahisci_dortlusu(satir)
            if dortlu is None:
                sayac["bahisci_dortlusu_yok"] += 1
            bahisci: Dict[str, Any] = {
                f"{ad}_{s}": "" for _, ad in A2_KAYNAKLARI for s in ("1", "0", "2")}
            if dortlu is not None:
                for ad, uclu in dortlu.items():
                    for s in ("1", "0", "2"):
                        bahisci[f"{ad}_{s}"] = uclu[s]

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
                "oran_kapanis": "1" if oran["kapanis"] else "0",
                **cizgi,
                **bahisci,
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
        # Cizgi cifti YA TAMDIR YA YOKTUR — yarim cift sessiz bir yalan olur:
        # `acilis` dolu, `kapanis` bos bir satir A1 kesitine yanlislikla girip
        # hareketi sifir gosterirdi.
        dolu = [bool(str(r.get(f"{uc}_{s}") or "").strip())
                for uc in ("acilis", "kapanis") for s in ("1", "0", "2")]
        if any(dolu) and not all(dolu):
            hatalar.append(f"satir {i}: cizgi cifti yarim")

        # Bahisci dortlusu de ya tamdir ya yoktur (ayni gerekce).
        b_dolu = [bool(str(r.get(f"{ad}_{s}") or "").strip())
                  for _, ad in A2_KAYNAKLARI for s in ("1", "0", "2")]
        if any(b_dolu) and not all(b_dolu):
            hatalar.append(f"satir {i}: bahisci dortlusu eksik")
        elif all(b_dolu):
            # `Max` butun bahiscilerin EN IYISI, `Avg` ORTALAMASI: max < ort
            # matematiksel olarak imkansizdir. Cikarsa kaynak sutunlari
            # karismistir ve anlasmazlik olcusu ters isaretli olur.
            for s in ("1", "0", "2"):
                if float(r[f"b_Max_{s}"]) < float(r[f"b_Avg_{s}"]) - 1e-9:
                    hatalar.append(f"satir {i}: b_Max_{s} < b_Avg_{s}")
                    break
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
    sayaclar: Dict[str, int] = {"toplam": 0, "tarih_yok": 0, "sonuc_yok": 0,
                                "oran_yok": 0, "cizgi_cifti_yok": 0,
                                "bahisci_dortlusu_yok": 0}
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
    kapanis_orani = sum(1 for r in satirlar if r["oran_kapanis"] == "1") / len(satirlar)
    istatistikli = sum(1 for r in satirlar if r.get("ev_isabet"))
    ciftli = sum(1 for r in satirlar if r.get("acilis_1"))
    dortlulu = sum(1 for r in satirlar if r.get("b_B365_1"))

    print(f"\nkorpus: {len(satirlar)} mac · {len(sezon_dagilim)} sezon "
          f"· {len({r['lig'] for r in satirlar})} lig")
    print(f"  sezon dagilimi : {sezon_dagilim}")
    print(f"  sonuc dagilimi : {kod_dagilim}")
    print(f"  kapanis orani  : %{100 * kapanis_orani:.1f}")
    print(f"  cizgi cifti    : {ciftli} (%{100 * ciftli / len(satirlar):.1f}) "
          f"— A1 kesiti")
    print(f"  bahisci dortlu : {dortlulu} (%{100 * dortlulu / len(satirlar):.1f}) "
          f"— A2 kesiti")
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
                 "oran_kaynak", "oran_kapanis",
                 "acilis_1", "acilis_0", "acilis_2", "acilis_kaynak",
                 "kapanis_1", "kapanis_0", "kapanis_2", "kapanis_kaynak",
                 ] + [f"{ad}_{s}" for _, ad in A2_KAYNAKLARI for s in ("1", "0", "2")
                      ] + [h for _, h in ISTATISTIK_SUTUNLARI]
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
        "with_line_pair": ciftli,
        "line_pair_pct": round(100 * ciftli / len(satirlar), 2),
        "line_pair_note": ("acilis+kapanis ayni bahisci ailesinden esitlenmis "
                           "cift; A1 (kapanis cizgisi verimliligi) kesiti "
                           "budur. Cifti olmayan mac ELENMEZ — `oran_*` tamdir "
                           "ve tahminci olcumune girer"),
        "with_bookmaker_quartet": dortlulu,
        "bookmaker_quartet_pct": round(100 * dortlulu / len(satirlar), 2),
        "bookmaker_sources": [onek for onek, _ in A2_KAYNAKLARI],
        "bookmaker_note": ("A2 (bahisci anlasmazligi) kesiti. Yalnizca dort "
                           "sezonda da ~%100 olan kaynaklar tasinir; BW/WH/BF/"
                           "1XB eklenirse kesit sezona gore dengesizlesir ve "
                           "sezon disarida birakmali olcum yanlilanir"),
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
