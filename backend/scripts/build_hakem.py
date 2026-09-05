"""Hakem sütununu football-data'dan çeker — **korpusa dokunmadan**.

─── Niçin ayrı bir dosya, niçin korpusa katılmıyor ────────────────────────

E4 tek bir soru soruyor: §3.24'ün *"sorun satır sayısı değil sütun"*
teşhisinden sonra **alınmamış** bir sütun ailesi kaldı mı? Hakem o ailenin
en umut verici üyesi: ev sahibi yanlılığı ve kart eğilimi takımdan bağımsız
bir değişken.

Ama sütun korpusa **katılamaz** ve sebebi ölçüldü (aşağıda `KAPSAMA`):
football-data hakemi yalnızca dokuz Britanya liginde yazıyor, kıta
Avrupası'nın on üç liginde **hiç yazmıyor**. Korpusa katmak `build_egitim`in
`A2_KAYNAKLARI` gerekçesiyle aynı kusuru üretirdi — kesit sessizce
dengesizleşir, model bir lig kümesini ötekinden farklı bir maç evreninde
öğrenir. Fark şu ki oradaki dengesizlik sezona göreydi, buradaki **coğrafi**
ve bu daha da beter: sezon dışarıda bırakmalı çapraz doğrulama onu
yakalayamaz.

İkinci bir sebep daha var ve o teknik: `egitim_korpus.csv` değişirse
`artefakt.py`nin taşıdığı sha256 bayatlar ve `health` kırmızı yanar; ayrıca
`ISTATISTIK_YOL_HARITASI.md`de "31.103" 53 yerde geçiyor ve çoğu bir
**ölçümün kaydı**. Bir sütun eklemek satır sayısını değiştirmez ama bu
dosyaların hiçbirine dokunmadan ölçüm yapmak zaten mümkün — bu betik onu
yapıyor.

Çıktı `data/hakem/hakem.csv`: korpusun satırlarına **anahtarla** bağlanan
ince bir tablo (sezon, lig, tarih, ev, dep, hakem). Ölçümü `spor_toto.hakem`
koşar.

    python scripts/build_hakem.py             # indir + yaz
    python scripts/build_hakem.py --kontrol   # diskteki bayat mı
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from scripts._ortak import indir_bellek, tarih_coz

ANA_URL = "https://www.football-data.co.uk/mmz4281/{sezon}/{lig}.csv"
CIKTI = KOK / "data" / "hakem" / "hakem.csv"
KORPUS = KOK / "data" / "egitim" / "egitim_korpus.csv"
BASLIK: tuple[str, ...] = ("sezon", "lig", "tarih", "ev", "dep", "hakem")

#: `build_egitim.VARSAYILAN_SEZONLAR` ile **aynı** olmak zorunda: tablo o
#: korpusun satırlarına bağlanıyor.
SEZONLAR: tuple[str, ...] = ("2122", "2223", "2324", "2425")

#: `build_egitim.ANA_LIGLER` ile aynı liste. Hakemi olmayanlar da taranır,
#: çünkü **kapsamanın kendisi ölçümdür** (`KAPSAMA`).
LIGLER: tuple[str, ...] = (
    "E0", "E1", "E2", "E3", "EC",
    "SC0", "SC1", "SC2", "SC3",
    "D1", "D2", "I1", "I2", "SP1", "SP2",
    "F1", "F2", "N1", "B1", "P1", "T1", "G1",
)

#: Ölçüldü (2026-09-04, 31.132 football-data satırı): hakem sütunu dokuz
#: Britanya liginde **%100**, on üç kıta liginde **%0**. Korpusa bağlandığında
#: 31.103 satırın 13.334'ü (%42,9) hakemli — ve bunların tamamı şu ligler.
KAPSAMA: tuple[str, ...] = ("E0", "E1", "E2", "E3", "EC",
                            "SC0", "SC1", "SC2", "SC3")


def _korpus_anahtarlari() -> set[tuple[str, str, str, str, str]]:
    """Korpusun satır anahtarları — tablo yalnızca bunlara bağlanır."""
    if not KORPUS.exists():
        return set()
    with KORPUS.open(encoding="utf-8") as f:
        return {(r["sezon"], r["lig"], r["tarih"], r["ev"], r["dep"])
                for r in csv.DictReader(f)}


def topla(sezonlar: tuple[str, ...] = SEZONLAR,
          ligler: tuple[str, ...] = LIGLER) -> list[dict[str, Any]]:
    """football-data'yı tarayıp korpusa bağlanan hakem satırlarını üretir."""
    anahtarlar = _korpus_anahtarlari()
    out: list[dict[str, Any]] = []
    for sezon in sezonlar:
        for lig in ligler:
            ham = indir_bellek(ANA_URL.format(sezon=sezon, lig=lig))
            if not ham:
                continue
            metin = ham.decode("utf-8-sig", errors="replace")
            for r in csv.DictReader(io.StringIO(metin)):
                hakem = (r.get("Referee") or "").strip()
                ev = (r.get("HomeTeam") or "").strip()
                dep = (r.get("AwayTeam") or "").strip()
                t = tarih_coz(r.get("Date") or "")
                if not (hakem and ev and dep and t):
                    continue
                k = (sezon, lig, t.date().isoformat(), ev, dep)
                if anahtarlar and k not in anahtarlar:
                    continue
                out.append(dict(zip(BASLIK, (*k, hakem))))
    out.sort(key=lambda r: (r["sezon"], r["lig"], r["tarih"], r["ev"]))
    return out


def metin(satirlar: list[dict[str, Any]]) -> str:
    """Tablonun **kararlı** metni — `--kontrol` buna dayanır."""
    tampon = io.StringIO()
    yaz = csv.DictWriter(tampon, fieldnames=list(BASLIK), lineterminator="\n")
    yaz.writeheader()
    yaz.writerows(satirlar)
    return tampon.getvalue()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kontrol", action="store_true",
                    help="yazma, diskteki tablo bayat mi soyle")
    a = ap.parse_args(argv)

    satirlar = topla()
    if not satirlar:
        print("hicbir hakem satiri toplanamadi (ag?)", file=sys.stderr)
        return 1
    yeni = metin(satirlar)
    if a.kontrol:
        eski = CIKTI.read_text(encoding="utf-8") if CIKTI.exists() else ""
        if eski == yeni:
            print(f"guncel: {len(satirlar)} satir")
            return 0
        print(f"BAYAT: diskte {eski.count(chr(10)) - 1} satir, "
              f"uretilen {len(satirlar)}", file=sys.stderr)
        return 1
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(yeni, encoding="utf-8")
    ligler = sorted({r["lig"] for r in satirlar})
    print(f"{CIKTI.relative_to(KOK)}: {len(satirlar)} satir · "
          f"{len(ligler)} lig · {len({r['hakem'] for r in satirlar})} hakem")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
