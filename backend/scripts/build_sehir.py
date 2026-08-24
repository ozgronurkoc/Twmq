#!/usr/bin/env python3
"""Kulüp → şehir tablosu — **derbiyi türetilebilir kılar** (Faz 3.4).

`spor_toto/disari.py` iki şeyi *"türetilemeyen"* diye kayda geçirmişti:

> ``seyahat``  sehir/koordinat yok
> ``derbi``    sehir eslemesi ya da rekabet tablosu yok; elle liste yazmak
>              turetme degil kuratorluk olurdu

İkinci cümle doğruydu ve kapıyı kapatmıyordu: **elle liste** yazmak
kuratörlüktür, ama **kamuya açık bir kaynaktan şehir okumak** türetmedir.
`openfootball/clubs` (CC0, kamu malı) tam olarak onu veriyor — kulüp adı,
şehir ve alternatif adlar.

Bu betik o tabloyu korpusun takım adlarına bağlar. Sonuç: `derbi` artık
türetilebilir. **`seyahat` hâlâ türetilemez** — kaynakta koordinat yok ve
"iki şehrin arası kaç km" sorusu şehir adından çıkmaz. Yani
`TURETILEMEYEN` listesi kısaldı, boşalmadı.

─── Ad eşleme — `build_avrupa.py` ile aynı disiplin ─────────────────────

1. Ülke bir **kısıt**tır: `(TUR)` yalnızca `T1` içinde aranır.
2. **Bulanık eşleme yok.** Ya sadeleştirilmiş ad birebir tutar (kaynağın
   kendi `| takma ad` listeleri dahil), ya `ELLE` tablosunda yazılıdır,
   ya da eşleşmez.
3. `ELLE` tablosu **şehir değil ad** eşler. Fark önemli: şehir her zaman
   kaynaktan okunur, yani elle yazılan bir isim yanlış olsa bile *uydurma
   bir şehir* üretmez — kapsama düşer ve raporda görünür.

Kaynakta şehri **hiç yazmayan** kulüpler var (ör. `CD Leganés`). Onlar
tabloya girmez; `sehir.py` o takımlar için "bilinmiyor" der ve derbi
sorusunu **cevapsız** bırakır. Uydurmak yerine bilmemek.

Ölçülen kapsama: **%98,0** (604 takımın 592'si). Kalan 12'sinin şehri
kaynakta **hiç yazmıyor** (ör. `CD Leganés`); onlar "bilinmiyor" kalır.

Kullanım:

    python scripts/build_sehir.py
    python scripts/build_sehir.py --dry-run
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_CIKTI = KOK / "data" / "sehir"

DEPO = "https://github.com/openfootball/clubs"

#: Ulke -> (openfootball dizini, dosya oneki) listesi. Galler kuluplerinin
#: (Cardiff, Swansea, Wrexham, Newport) ligi INGILTERE'dir; bu yuzden ENG
#: iki dosya okur — kaynak onlari ulkelerine gore ayirir, biz LIGE gore.
ULKE_DOSYA: dict[str, tuple[tuple[str, str], ...]] = {
    "ENG": (("england", "eng"), ("wales", "wal")),
    "SCO": (("scotland", "sco"),), "GER": (("germany", "de"),),
    "ITA": (("italy", "it"),), "ESP": (("spain", "es"),),
    # Monaco ligi FRANSA'dir; kaynak onu ayri bir ulke dosyasinda tutar.
    "FRA": (("france", "fr"), ("monaco", "mc")),
    "NED": (("netherlands", "nl"),),
    "BEL": (("belgium", "be"),), "POR": (("portugal", "pt"),),
    "TUR": (("turkey", "tr"),), "GRE": (("greece", "gr"),),
}

#: `build_avrupa.ULKE_LIG` ile ayni — ayni korpus, ayni ulke tanimi.
ULKE_LIG: dict[str, tuple[str, ...]] = {
    "ENG": ("E0", "E1", "E2", "E3", "EC"),
    "SCO": ("SC0", "SC1", "SC2", "SC3"),
    "GER": ("D1", "D2"), "ITA": ("I1", "I2"), "ESP": ("SP1", "SP2"),
    "FRA": ("F1", "F2"), "NED": ("N1",), "BEL": ("B1",), "POR": ("P1",),
    "TUR": ("T1",), "GRE": ("G1",),
}

#: Korpus adi -> openfootball kulup adi. **Sehir DEGIL ad** eslenir.
ELLE: dict[str, str] = {
    "Ath Madrid": "Atlético Madrid",
    "Sp Lisbon": "Sporting CP",
    "Bayern Munich": "Bayern München",
    "Monaco": "AS Monaco",
    "St. Gilloise": "Saint-Gilloise",
    "Dorking": "Dorking Wanderers FC",
    "Athens Kallithea": "Kallithea FC",
    # Korpusun kendi kaydinda cift kodlanmis bir ad (mojibake). Kaynagi
    # duzeltmek bu betigin isi degil; esleme burada acikca yazilir.
    "Preu\u00c3\u009fen M\u00c3\u00bcnster": "Preu\u00dfen M\u00fcnster",
}

_ATILAN = {
    "fc", "ac", "sc", "cf", "afc", "sk", "fk", "bk", "if", "kv", "cd", "rc",
    "ss", "ssc", "us", "club", "clube", "de", "du", "the", "calcio", "jk",
    "ksv", "krc", "kaa", "rsc", "losc", "ogc", "acf", "bsc", "gnk", "nk",
    "hnk", "sad", "cp", "1", "spor", "kulubu", "as", "asd", "a",
    "utd", "united", "city", "county",
}


def sadelestir(ad: str) -> str:
    """`build_avrupa.sadelestir` ile ayni fikir, biraz daha genis atma listesi.

    Burada `utd`/`united`/`city`/`county` de atilir cunku kaynak tam adi
    ("Newport County AFC"), korpus kisaltmasini ("Newport County") yazar ve
    ikisi arasindaki fark bu kelimelerdedir.
    """
    a = unicodedata.normalize("NFKD", ad)
    a = "".join(c for c in a if not unicodedata.combining(c))
    for eski, yeni in (("ø", "o"), ("ß", "ss"), ("ð", "d"), ("þ", "th"),
                       ("đ", "d"), ("ı", "i"), ("İ", "I")):
        a = a.replace(eski, yeni)
    a = re.sub(r"[^a-z0-9]+", " ", a.lower())
    kel = [w for w in a.split()
           if w not in _ATILAN and not re.fullmatch(r"1[89]\d\d", w)]
    return " ".join(kel) if kel else a.strip()


def sehir_coz(satir: str) -> tuple[str, str | None]:
    """`"Arsenal FC, 1886, @ Emirates Stadium, London (Highbury)"` -> `("Arsenal FC", "London")`.

    Alanlar virgulle ayrilir ve **sirasi degisken**: yil ve stadyum
    olmayabilir. Sehir her zaman SON alandir; parantezli semt ve `##`
    yorumu atilir.
    """
    govde = satir.split("##")[0].split("#")[0].strip().rstrip(",")
    parcalar = [p.strip() for p in govde.split(",")]
    ad = parcalar[0]
    kalan = [p for p in parcalar[1:]
             if p and not re.fullmatch(r"\d{4}", p) and not p.startswith("@")]
    if not kalan:
        return ad, None
    sehir = re.sub(r"\(.*?\)", "", kalan[-1]).strip()
    # "Dorking › Surrey" gibi bolgeli yazimlarda ilk parca sehirdir.
    sehir = sehir.split("›")[0].strip()
    return ad, (sehir or None)


def kulup_sehirleri(kaynak: Path) -> dict[tuple[str, str], str]:
    """`(ulke, sadelestirilmis_ad) -> sehir`. Takma adlar da anahtar olur."""
    out: dict[tuple[str, str], str] = {}
    for ulke, dosyalar in ULKE_DOSYA.items():
        for dizin, kod in dosyalar:
            p = kaynak / "europe" / dizin / f"{kod}.clubs.txt"
            if not p.exists():
                print(f"  {p} yok — atlandi", file=sys.stderr)
                continue
            su_an: str | None = None
            for ham in p.read_text(encoding="utf-8").splitlines():
                if not ham.strip() or ham.lstrip().startswith(("#", "=")):
                    continue
                if ham[0].isspace():
                    # Takma ad satiri: `  | Arsenal | FC Arsenal`
                    if "|" in ham and su_an:
                        for al in ham.split("|"):
                            al = al.split("#")[0].strip()
                            if al:
                                out.setdefault((ulke, sadelestir(al)), su_an)
                    continue
                ad, sehir = sehir_coz(ham)
                su_an = sehir
                if sehir:
                    out[(ulke, sadelestir(ad))] = sehir
    return out


def _kaynagi_getir(kaynak: Path | None) -> Path:
    """Depoyu klonla (ya da verilen yerel kopyayi kullan)."""
    if kaynak is not None:
        return kaynak
    hedef = Path(tempfile.gettempdir()) / "openfootball-clubs"
    if (hedef / "europe").exists():
        return hedef
    print(f"  klonlaniyor: {DEPO}")
    subprocess.run(["git", "clone", "--depth", "1", DEPO, str(hedef)],
                   check=True, capture_output=True)
    return hedef


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kaynak", type=Path, default=None,
                    help="yerel openfootball/clubs kopyasi (yoksa klonlanir)")
    ap.add_argument("--out-dir", type=Path, default=VARSAYILAN_CIKTI)
    ap.add_argument("--en-az-kapsama", type=float, default=0.95)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, str(KOK))
    from spor_toto.egitim import korpus_yukle

    korpus = korpus_yukle()
    if not korpus:
        print("egitim korpusu yok — once scripts/build_egitim.py",
              file=sys.stderr)
        return 1

    tablo = kulup_sehirleri(_kaynagi_getir(args.kaynak))
    if not tablo:
        print("kaynak okunamadi", file=sys.stderr)
        return 1
    print(f"  kaynak: {len(tablo)} kulup/takma ad kaydi")

    lig_takim: dict[str, set[str]] = collections.defaultdict(set)
    for r in korpus:
        lig_takim[r["lig"]].add(r["ev"])
        lig_takim[r["lig"]].add(r["dep"])

    satirlar: list[dict[str, str]] = []
    essiz: list[tuple[str, str]] = []
    for ulke, ligler in ULKE_LIG.items():
        for lig in ligler:
            for takim in sorted(lig_takim.get(lig, ())):
                aranan = sadelestir(ELLE.get(takim, takim))
                sehir = tablo.get((ulke, aranan))
                if sehir:
                    satirlar.append({"lig": lig, "ulke": ulke,
                                     "takim": takim, "sehir": sehir})
                else:
                    essiz.append((lig, takim))

    toplam = len(satirlar) + len(essiz)
    kapsama = (len(satirlar) / toplam) if toplam else 0.0
    print(f"\nSehir kapsamasi: {len(satirlar)}/{toplam} = {kapsama:.1%}")
    if essiz:
        print(f"Sehri bilinmeyen {len(essiz)} takim "
              f"(kaynakta sehir yazmiyor — uydurulmaz):")
        for lig, takim in essiz[:30]:
            print(f"  {lig:<5}{takim}")

    if kapsama < args.en_az_kapsama:
        print(f"\nDOGRULAMA BASARISIZ — kapsama {kapsama:.1%} < "
              f"{args.en_az_kapsama:.1%}; dosya yazilmadi", file=sys.stderr)
        return 1

    sehirler = collections.Counter(r["sehir"] for r in satirlar)
    cok = [(s, n) for s, n in sehirler.most_common() if n > 1]
    print(f"{len(sehirler)} farkli sehir · {len(cok)} sehirde birden fazla takim")
    for s, n in cok[:10]:
        print(f"  {s:<20}{n}")

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    hedef = args.out_dir / "sehir_tablosu.csv"
    with open(hedef, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["lig", "ulke", "takim", "sehir"])
        w.writeheader()
        w.writerows(sorted(satirlar, key=lambda r: (r["lig"], r["takim"])))
    (args.out_dir / "sehir_rapor.json").write_text(json.dumps({
        "uretildi": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kaynak": "openfootball/clubs (CC0)",
        "takim": len(satirlar), "kapsama": round(kapsama, 4),
        "sehir": len(sehirler),
        "sehri_bilinmeyen": [f"{lig}:{t}" for lig, t in essiz],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"yazildi: {hedef}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
