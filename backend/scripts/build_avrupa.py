#!/usr/bin/env python3
"""Avrupa kupası fikstürü — korpusun **ölçülmüş** kör noktasını kapatır.

`ISTATISTIK_YOL_HARITASI.md` §3.16 (A3) bir şey ölçtü ve açıklayamadı:
deplasman takımı **"dinlenmiş"** göründüğünde ev sahibi piyasayı
+0,0655 aşıyor, ve etki Avrupa liglerinde dört kat güçlü. `dinlenme_farki`
lig maçları arasındaki gün sayısıdır; bir takım Perşembe Avrupa'da oynayıp
Pazar lige çıktığında korpus onu **on gün dinlenmiş** sanır.

Yani sorun modelde değil **veride**ydi: korpus, oynanan maçların bir
kısmını hiç görmüyordu. Faz 3.4'ün en yüksek beklenen değerli maddesi
buydu ve kapattığı boşluk tam olarak budur.

─── Kaynak ───────────────────────────────────────────────────────────────

`openfootball/champions-league` (GitHub) — kamu malı (public domain),
`football.txt` biçiminde UEFA Şampiyonlar Ligi, Avrupa Ligi ve Konferans
Ligi fikstürleri. `raw.githubusercontent.com` **robots.txt yayınlamıyor**
(404), yani yayınlanmış bir kısıt yok; erişim tek seferlik ve önbelleklidir.

─── Ad eşleme — bu betiğin asıl işi ─────────────────────────────────────

openfootball tam adları yazar (`FC Bayern München (GER)`), football-data
kısaltır (`Bayern Munich`). Eşleme yapılmazsa dosya sessizce **boş**
çıkar: satırlar yazılır, hiçbiri korpusa bağlanmaz, özellik her yerde
sıfır olur ve "ölçtük, çıkmadı" denir. Bu yüzden:

1. **Ülke kodu bir kısıttır, ipucu değil.** `(GER)` yalnızca `D1`/`D2`
   içinde aranır; ligler arası yanlış eşleşme baştan imkânsızdır.
2. **Bulanık eşleme yok.** Ya sadeleştirilmiş ad birebir tutar, ya da
   `ELLE` tablosunda açıkça yazılıdır. "Rangers" ile "Cove Rangers"ı
   birbirine karıştıran bir alt dize eşlemesi ölçüldü ve **%68**'de kaldı.
3. **Kapsama bir kapıdır.** `--en-az-kapsama` altındaki bir koşum dosya
   **yazmaz**; eşleşmeyen adların tamamı raporda listelenir.

Ölçülen kapsama: **%100** (2.222 ad ifadesi, 4 sezon, üç turnuva).

Kullanım:

    python scripts/build_avrupa.py
    python scripts/build_avrupa.py --dry-run
    python scripts/build_avrupa.py --sezonlar 2324 2425
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_CIKTI = KOK / "data" / "avrupa"

UA = "Mozilla/5.0 (compatible; spor-toto-lab/1.0)"
ANA_URL = ("https://raw.githubusercontent.com/openfootball/champions-league/"
           "master/{yil}/{turnuva}.txt")

#: football-data sezon kodu -> openfootball dizin adi.
SEZON_DIZIN: dict[str, str] = {
    "2122": "2021-22", "2223": "2022-23",
    "2324": "2023-24", "2425": "2024-25", "2526": "2025-26",
}

#: `build_egitim.VARSAYILAN_SEZONLAR` ile ayni — ayni korpus.
VARSAYILAN_SEZONLAR: tuple[str, ...] = ("2122", "2223", "2324", "2425")

TURNUVALAR: tuple[str, ...] = ("cl", "el", "conf")

#: Ulke kodu -> korpustaki ligler, **ust ligden alta**. Sira onemlidir:
#: ayni sadelestirilmis ad iki ligde birden bulunursa ust lig kazanir
#: (Avrupa'da oynayan takim ust ligdedir).
ULKE_LIG: dict[str, tuple[str, ...]] = {
    "ENG": ("E0", "E1", "E2", "E3", "EC"),
    "SCO": ("SC0", "SC1", "SC2", "SC3"),
    "GER": ("D1", "D2"), "ITA": ("I1", "I2"), "ESP": ("SP1", "SP2"),
    "FRA": ("F1", "F2"), "NED": ("N1",), "BEL": ("B1",), "POR": ("P1",),
    "TUR": ("T1",), "GRE": ("G1",),
}

#: **Elle yazilmis, gozden gecirilmis** esleme tablosu: openfootball'un tam
#: adi -> football-data'nin kisaltmasi. Bulanik eslemeye ALTERNATIF olarak
#: var; her satir tek tek dogrulandi ve yanlis bir satir sessiz degil,
#: `--en-az-kapsama` kapisinda gorunur bir dususe yol acar.
ELLE: dict[str, str] = {
    "Manchester United": "Man United", "Manchester City": "Man City",
    "Club Atletico de Madrid": "Ath Madrid", "Atletico Madrid": "Ath Madrid",
    "Athletic Club": "Ath Bilbao", "Athletic Bilbao": "Ath Bilbao",
    "Real Sociedad": "Sociedad", "Real Sociedad de Futbol": "Sociedad",
    "Eintracht Frankfurt": "Ein Frankfurt",
    "FC Bayern Munchen": "Bayern Munich", "Bayern Munchen": "Bayern Munich",
    "Bayer 04 Leverkusen": "Leverkusen", "Bayer Leverkusen": "Leverkusen",
    "FC Internazionale Milano": "Inter", "Internazionale": "Inter",
    "Lazio Roma": "Lazio", "SS Lazio": "Lazio",
    "Paris Saint-Germain FC": "Paris SG", "Paris Saint-Germain": "Paris SG",
    "Sporting CP": "Sp Lisbon", "Sporting Clube de Portugal": "Sp Lisbon",
    "PAOK Saloniki": "PAOK", "PAOK Thessaloniki": "PAOK",
    "Union Saint-Gilloise": "St. Gilloise",
    "Royale Union Saint-Gilloise": "St. Gilloise",
    "Stade Rennais": "Rennes", "Stade Rennais FC": "Rennes",
    "Club Brugge KV": "Club Brugge", "Rangers FC": "Rangers",
    "Villarreal CF": "Villarreal", "Real Madrid CF": "Real Madrid",
    "Real Betis Balompie": "Betis", "Real Betis": "Betis",
    "Olympique de Marseille": "Marseille", "Olympique Lyonnais": "Lyon",
    "AS Monaco FC": "Monaco", "OGC Nice": "Nice", "LOSC Lille": "Lille",
    "Lille OSC": "Lille", "Stade Brestois 29": "Brest",
    "RC Lens": "Lens", "Racing Club de Lens": "Lens",
    "FC Nantes": "Nantes", "Toulouse FC": "Toulouse",
    "AS Saint-Etienne": "St Etienne", "Stade de Reims": "Reims",
    "Celtic FC": "Celtic", "Heart of Midlothian FC": "Hearts",
    "Hibernian FC": "Hibernian", "Aberdeen FC": "Aberdeen",
    "Sport Lisboa e Benfica": "Benfica", "SL Benfica": "Benfica",
    "FC Porto": "Porto", "SC Braga": "Sp Braga", "Sporting Braga": "Sp Braga",
    "Sporting Clube de Braga": "Sp Braga",
    "Vitoria SC": "Guimaraes", "Vitoria Guimaraes": "Guimaraes",
    "Fenerbahce SK": "Fenerbahce", "Galatasaray SK": "Galatasaray",
    "Besiktas JK": "Besiktas",
    "Istanbul Basaksehir FK": "Buyuksehyr", "Basaksehir": "Buyuksehyr",
    "AEK Athens": "AEK", "AEK Athen": "AEK",
    "Olympiacos Piraeus": "Olympiakos", "Olympiakos Piraeus": "Olympiakos",
    "Panathinaikos Athens": "Panathinaikos", "Aris Thessaloniki": "Aris",
    "AFC Ajax": "Ajax", "PSV": "PSV Eindhoven", "PSV Eindhoven": "PSV Eindhoven",
    "Feyenoord Rotterdam": "Feyenoord", "AZ Alkmaar": "AZ Alkmaar",
    "FC Twente": "Twente", "FC Utrecht": "Utrecht", "Vitesse Arnhem": "Vitesse",
    "RSC Anderlecht": "Anderlecht", "KAA Gent": "Gent", "KRC Genk": "Genk",
    "Royal Antwerp FC": "Antwerp", "Standard Liege": "Standard",
    "Cercle Brugge KSV": "Cercle Brugge",
    "West Ham United FC": "West Ham", "Tottenham Hotspur FC": "Tottenham",
    "Newcastle United FC": "Newcastle",
    "Nottingham Forest FC": "Nott'm Forest",
    "Brighton & Hove Albion FC": "Brighton",
    "Wolverhampton Wanderers FC": "Wolves",
    "Leicester City FC": "Leicester", "Crystal Palace FC": "Crystal Palace",
    "SSC Napoli": "Napoli", "Atalanta BC": "Atalanta", "AC Milan": "Milan",
    "Juventus FC": "Juventus", "AS Roma": "Roma", "ACF Fiorentina": "Fiorentina",
    "Bologna FC 1909": "Bologna", "Torino FC": "Torino",
    "Udinese Calcio": "Udinese", "US Sassuolo Calcio": "Sassuolo",
    "Hellas Verona FC": "Verona",
    "Borussia Dortmund": "Dortmund",
    "Borussia Monchengladbach": "M'gladbach",
    "RB Leipzig": "RB Leipzig", "VfB Stuttgart": "Stuttgart",
    "VfL Wolfsburg": "Wolfsburg", "1. FC Union Berlin": "Union Berlin",
    "SC Freiburg": "Freiburg", "TSG 1899 Hoffenheim": "Hoffenheim",
    "1. FSV Mainz 05": "Mainz", "FC Augsburg": "Augsburg",
    "1. FC Koln": "FC Koln", "Werder Bremen": "Werder Bremen",
    "SV Werder Bremen": "Werder Bremen",
    "FC Barcelona": "Barcelona", "Sevilla FC": "Sevilla",
    "Valencia CF": "Valencia", "Girona FC": "Girona",
    "RC Celta de Vigo": "Celta", "Celta de Vigo": "Celta",
    "Rayo Vallecano": "Vallecano", "CA Osasuna": "Osasuna",
    "Real Mallorca": "Mallorca", "RCD Mallorca": "Mallorca",
    "Getafe CF": "Getafe", "Elche CF": "Elche",
}

#: Sadelestirmede ATILAN kulup ekleri. Liste kisa ve kasitli: "real",
#: "borussia", "sporting" gibi AYIRT EDICI kelimeler burada YOKTUR —
#: atilsalardi "Real Madrid" ile "Real Sociedad" ayni ada duserdi.
_ATILAN = {
    "fc", "ac", "sc", "cf", "afc", "sk", "fk", "bk", "if", "kv", "cd", "rc",
    "ss", "ssc", "us", "club", "clube", "de", "du", "the", "calcio", "jk",
    "ksv", "krc", "kaa", "rsc", "losc", "ogc", "acf", "bsc", "gnk", "nk",
    "hnk", "sad", "cp", "1",
}

AYLAR = {a: i for i, a in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

_TARIH_RE = re.compile(
    r"^\s{2}(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})"
    r"(?:\s+(\d{4}))?\s*$")
_MAC_RE = re.compile(r"^\s{4,}(?:\d{2}:\d{2}\s+)?(.+?)\s+v\s+(.+?)(?:\s{2,}.*)?$")
_TAKIM_RE = re.compile(r"^(.*?)\s*\((\w{3})\)$")


def sadelestir(ad: str) -> str:
    """Aksan, noktalama ve kulup eki olmadan karsilastirilabilir ad."""
    a = unicodedata.normalize("NFKD", ad)
    a = "".join(c for c in a if not unicodedata.combining(c))
    for eski, yeni in (("ø", "o"), ("Ø", "O"), ("ß", "ss"), ("ð", "d"),
                       ("þ", "th"), ("đ", "d"), ("Đ", "D")):
        a = a.replace(eski, yeni)
    a = re.sub(r"[^a-z0-9]+", " ", a.lower())
    kel = [w for w in a.split()
           if w not in _ATILAN and not re.fullmatch(r"1[89]\d\d", w)]
    return " ".join(kel) if kel else a.strip()


def indir(url: str, hedef: Path, timeout: float = 60.0) -> Path | None:
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


def maclari_coz(metin: str) -> list[dict[str, Any]]:
    """`football.txt` metnini `(tarih, ev, dep)` satirlarina cevirir.

    ─── Yil satirdan satira TASINIR ve bu bir tuzaktir ──────────────────

    Biçim yılı yalnızca bölümün **ilk** tarihinde yazar; sonrakiler
    `Wed Sep 18` gibidir. Ay geriye sardığında (Aralık → Ocak) yıl da
    artmalıdır; artırılmazsa Şubat maçları bir önceki yıla düşer ve
    "Avrupa'da oynadı mı" sorusu **365 gün** yanlış cevaplanır. Bekçi:
    `test_avrupa.py::test_yil_donumu_dogru_sariyor`.
    """
    out: list[dict[str, Any]] = []
    gecerli: date | None = None
    for satir in metin.splitlines():
        t = _TARIH_RE.match(satir)
        if t:
            ay, gun, yil = AYLAR[t.group(1)], int(t.group(2)), t.group(3)
            if yil:
                gecerli = date(int(yil), ay, gun)
            elif gecerli is not None:
                # Ay geriye sardiysa yeni takvim yili basladi.
                y = gecerli.year + (1 if ay < gecerli.month else 0)
                gecerli = date(y, ay, gun)
            continue
        m = _MAC_RE.match(satir)
        if m and gecerli is not None:
            out.append({"tarih": gecerli.isoformat(),
                        "ev_ham": m.group(1).strip(),
                        "dep_ham": m.group(2).strip()})
    return out


def _korpus_takimlari(korpus_yolu: Path | None = None
                      ) -> dict[str, set[str]]:
    """Lig -> korpusta gecen takim adlari."""
    sys.path.insert(0, str(KOK))
    from spor_toto.egitim import korpus_yukle

    out: dict[str, set[str]] = collections.defaultdict(set)
    for r in korpus_yukle(str(korpus_yolu) if korpus_yolu else None):
        out[r["lig"]].add(r["ev"])
        out[r["lig"]].add(r["dep"])
    return dict(out)


def eslestir(ham: str, lig_takim: dict[str, set[str]]
             ) -> tuple[tuple[str, str] | None, str]:
    """`"FC Bayern München (GER)"` -> `(("D1", "Bayern Munich"), "")`.

    Ikinci deger sebeptir; eslesme varsa bostur. Bulanik esleme YOK:
    ya birebir, ya `ELLE`, ya da eslesmez.
    """
    m = _TAKIM_RE.match(ham)
    if not m:
        return None, "ulke kodu yok"
    ad, ulke = m.group(1).strip(), m.group(2)
    ligler = ULKE_LIG.get(ulke)
    if not ligler:
        return None, f"korpus disi ulke ({ulke})"

    n = sadelestir(ad)
    hedef = {sadelestir(k): v for k, v in ELLE.items()}.get(n)
    adaylar: list[tuple[str, str]] = []
    for lig in ligler:
        for t in lig_takim.get(lig, ()):
            if (t == hedef) if hedef is not None else (sadelestir(t) == n):
                adaylar.append((lig, t))
    if not adaylar:
        return None, (f"ELLE tablosunda '{hedef}' yazili ama korpusta yok"
                      if hedef else f"karsiligi yok ({n})")
    # Ust lig kazanir: `ULKE_LIG` ust->alt siralidir.
    adaylar.sort(key=lambda a: ligler.index(a[0]))
    return adaylar[0], ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sezonlar", nargs="+", default=list(VARSAYILAN_SEZONLAR))
    ap.add_argument("--out-dir", type=Path, default=VARSAYILAN_CIKTI)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--en-az-kapsama", type=float, default=0.98,
                    help="korpus ulkelerindeki ad ifadelerinin eslesme orani")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cache = args.cache or (args.out_dir / "_kaynak")
    lig_takim = _korpus_takimlari()
    if not lig_takim:
        print("egitim korpusu yok — once scripts/build_egitim.py",
              file=sys.stderr)
        return 1

    satirlar: list[dict[str, Any]] = []
    essiz: collections.Counter[str] = collections.Counter()
    sebepler: dict[str, str] = {}
    ilgili = tutan = 0
    alinamayan: list[str] = []

    for sezon in args.sezonlar:
        dizin = SEZON_DIZIN.get(sezon)
        if dizin is None:
            print(f"  {sezon}: openfootball dizini bilinmiyor — atlandi",
                  file=sys.stderr)
            continue
        for turnuva in TURNUVALAR:
            yol = indir(ANA_URL.format(yil=dizin, turnuva=turnuva),
                        cache / dizin / f"{turnuva}.txt")
            if yol is None:
                alinamayan.append(f"{dizin}/{turnuva}")
                continue
            for m in maclari_coz(yol.read_text(encoding="utf-8")):
                taraf: list[tuple[str, str] | None] = []
                for ham in (m["ev_ham"], m["dep_ham"]):
                    tm = _TAKIM_RE.match(ham)
                    ulke = tm.group(2) if tm else ""
                    r, sebep = eslestir(ham, lig_takim)
                    if ulke in ULKE_LIG:
                        ilgili += 1
                        if r:
                            tutan += 1
                        else:
                            essiz[ham] += 1
                            sebepler[ham] = sebep
                    taraf.append(r)
                ev, dep = taraf
                # Bir tarafi bile eslesmeyen mac YAZILMAZ: yarim satir,
                # "Avrupa'da oynamadi" diye okunur ve sessizce yanlistir.
                if ev and dep:
                    satirlar.append({
                        "sezon": sezon, "turnuva": turnuva,
                        "tarih": m["tarih"],
                        "ev_lig": ev[0], "ev": ev[1],
                        "dep_lig": dep[0], "dep": dep[1],
                    })
        print(f"  {sezon}: {len(satirlar)} satir (kumulatif)")

    kapsama = (tutan / ilgili) if ilgili else 0.0
    print(f"\nAd eslemesi: {tutan}/{ilgili} = {kapsama:.1%}")
    if essiz:
        print(f"Eslesmeyen {len(essiz)} ad:")
        for ad, c in essiz.most_common(30):
            print(f"  {c:>4}  {ad:<44} {sebepler[ad]}")

    if kapsama < args.en_az_kapsama:
        print(f"\nDOGRULAMA BASARISIZ — kapsama {kapsama:.1%} < "
              f"{args.en_az_kapsama:.1%}; dosya yazilmadi", file=sys.stderr)
        return 1
    if not satirlar:
        print("\nDOGRULAMA BASARISIZ — hic satir yok", file=sys.stderr)
        return 1

    satirlar.sort(key=lambda r: (r["tarih"], r["turnuva"], r["ev"]))
    print(f"\n{len(satirlar)} mac · {len({r['ev'] for r in satirlar} | {r['dep'] for r in satirlar})} takim")
    if alinamayan:
        print(f"Alinamayan kaynak: {', '.join(alinamayan)}")

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    hedef = args.out_dir / "avrupa_fikstur.csv"
    alanlar = ["sezon", "turnuva", "tarih", "ev_lig", "ev", "dep_lig", "dep"]
    with open(hedef, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=alanlar)
        w.writeheader()
        w.writerows(satirlar)
    rapor = args.out_dir / "avrupa_rapor.json"
    rapor.write_text(json.dumps({
        "uretildi": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kaynak": "openfootball/champions-league (public domain)",
        "sezonlar": args.sezonlar, "turnuvalar": list(TURNUVALAR),
        "mac": len(satirlar), "ad_kapsamasi": round(kapsama, 4),
        "eslesmeyen": dict(essiz.most_common()),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"yazildi: {hedef} · {rapor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
