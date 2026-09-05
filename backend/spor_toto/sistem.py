"""İndirgenmiş sistem fiyatları — bedel artık formülden değil **tablodan**.

`secim.bedel_hesapla` kuponun bedelini `2^çifte · 3^üçlü / 8` diye
hesaplıyordu. O formül yanlış değil ama **dar**: yalnızca `core.solve_fix16`
modunun bedelidir, yani Hamming(7,4) bloğunun; en az yedi çifte ister ve tek
bir garanti seviyesi tanır (14).

Oynanan ürün o değil. Satıcının fiyat tablosu **84 şeklin tamamını** ve **üç
garanti seviyesini** birden taşıyor — 12, 13 ve 14. Bu modül o tabloyu okur.

─── Tablo bir fiyat listesi değil, bir ölçümdür ──────────────────────────

Her satır, o `(tek, çifte, kapalı)` şekli için satıcının üretebildiği
indirgenmiş sistemin kolon sayısını verir. Yani tablo, bizim kendi
kaplama kodumuzun **bağımsız bir karşılaştırma noktasıdır**: aynı şekilde
formülün dediğinden ucuz bir satır, satıcının daha iyi bir kod bulduğu
anlamına gelir (ve tersi).

─── Garanti, kaçak eşiğini belirler — projenin asıl bağlantısı ───────────

`secim` modülünün başlığındaki aritmetik garantiye göre kayar. `G`-garanti,
*"doğru sonuç seçim kümesinin içindeyse en az bir kolon en fazla `15 − G`
hatalıdır"* demektir. `k` maç kümenin **dışında** kalırsa o `k` maç her
kolonda yanlıştır ve geriye kalan `15 − k` için garanti işler::

    en iyi kolon  ≥  (15 − k) − (15 − G)  =  G − k

`P(en iyi kolon ≥ 12)` aranıyorsa `G − k ≥ 12`, yani::

    14-garanti → k ≤ 2      13-garanti → k ≤ 1      12-garanti → k ≤ 0

Eşik **eşitlik değil alt sınırdır** (kaplama bir kolonu tesadüfen daha iyi
tutturabilir), dolayısıyla optimize edilmesi güvenlidir — `secim` modül
başlığındaki gerekçe aynen geçerli, yalnızca `G` artık sabit değil.

─── Şüpheli satırlar sessizce düzeltilmez ────────────────────────────────

Tabloda **iki** satır tekdüzeliği bozuyor: aynı `tek` bloğunda bir çifte
üçlüye dönerken fiyat *düşüyor*. Bir üçlü uzayı büyütür, ucuzlatamaz. İkisi
de `supheli` listesinde adıyla duruyor ve `bedel()` onları çağrıldığında
**uyarır**; değerleri düzeltilmez, çünkü hangi rakamın yanlış olduğu
bilinmiyor — bilinen tek şey satırın güvenilmez olduğudur.

    python -m spor_toto.sistem              # tablo ozeti + denetim
    python -m spor_toto.sistem --butce 3000 # butceye sigan sekiller
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_TABLO = KOK / "data" / "sistem_fiyat" / "st_extra.json"

#: Kupondaki maç sayısı — tablonun her satırı buna toplanır.
MAC_SAYISI = 15

#: Tablonun tanıdığı garanti seviyeleri.
GARANTILER: tuple[int, ...] = (12, 13, 14)

#: **Varsayılan garanti — ürün kararı, ölçüm değil.** Kullanıcı 13-garantili
#: oynuyor (2026-09-04); bütün bedel ve hedef hesapları bu seviyede kurulur.
#: `secim.VARSAYILAN_KACAK_ESIGI` bu sabitten TÜREYECEK, tersi değil.
VARSAYILAN_GARANTI = 13

#: İkramiyenin başladığı kademe (§5.2 bulgu 1: *"14 hiçbir zaman ulaşılabilir
#: hedef değildi; doğru ölçü P(en iyi kolon ≥ 12)"*). Kaçak eşiği buradan
#: türer ve bu yüzden ayrı bir sabittir.
#:
#: **Ve artık bir varsayım değil, ölçülmüş bir seçim** (2026-09-04, E2):
#: 12/13/14 adayları 114 hafta boyunca gerçek ikramiye tablolarına karşı
#: koşturuldu (`karne.hedef_kademe_kiyasi`, 14-garanti, 2.000 TL) ve
#: eşleştirilmiş ROI farklarının üçü de sıfırı kesti — en yakını 13 − 12,
#: +0,00928 [+0,00000, +0,02724], kuyruk sınavında da aynı. Sabit değişmedi
#: ama gerekçesi değişti.
#:
#: Ölçüm neden zayıf çıktı, o da yazılı olmalı: üç hedef de **aynı şekli**
#: alıyor (3 çifte + 5 üçlü, 168 kolon), çünkü çifte/üçlü eklemek
#: `P(k ≤ eşik)`'i hangi eşikte olursa olsun büyütür — yani şekli **bütçe**
#: belirliyor, hedef değil. Hedefin dokunabildiği tek şey hangi sembolün
#: işaretlendiği.
#:
#: Ölçüm 14-garantide yapıldı çünkü kolonları üretebilen tek yer orası
#: (`engines.run_auto`, `core.py` yarıçap 1'e kilitli). 13-garantiye
#: **taşınmaz** — §3.51'in 15,1 katı tam olarak o taşımayı geçersiz kılar.
HEDEF_KADEME = 12


class Sekil(NamedTuple):
    """Bir kuponun işaret şekli ve o şeklin ölçülmüş bedeli."""

    tek: int
    cift: int
    kapali: int
    kolon: int
    tl: float
    garanti: int
    supheli: bool


def kacak_esigi(garanti: int = VARSAYILAN_GARANTI,
                kademe: int = HEDEF_KADEME) -> int:
    """`P(en iyi kolon ≥ kademe)` için izin verilen en çok kaçak.

    Modül başlığındaki aritmetiğin tek satırlık hâli::

        >>> kacak_esigi(14)
        2
        >>> kacak_esigi(13)
        1
        >>> kacak_esigi(12)
        0

    Kademe düşürülürse eşik gevşer — 13-garantiyle 11'i hedeflemek iki
    kaçağa izin verir::

        >>> kacak_esigi(13, kademe=11)
        2
    """
    if garanti not in GARANTILER:
        raise ValueError(f"garanti {GARANTILER} icinde olmali, {garanti} geldi")
    return garanti - kademe


@lru_cache(maxsize=4)
def _tablo(yol: str | None = None) -> dict[str, Any]:
    p = Path(yol) if yol else VARSAYILAN_TABLO
    ham: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    dogrula(ham)
    return ham


def dogrula(ham: dict[str, Any]) -> None:
    """Tabloyu **okuma anında** denetler — bozuk tablo sessizce kullanılmaz.

    Üç değişmez: her satır 15 maça toplanır, her fiyat kolon bedelinin tam
    katıdır (yoksa kolon sayısı tamsayı çıkmaz), ve `12G ≤ 13G ≤ 14G`
    (daha sıkı garanti ucuzlayamaz).

    Tekdüzelik **denetlenir ama kapı değildir**: ihlal eden satırlar
    `supheli` listesinde adıyla durur ve `bedel()` onları uyarıyla döndürür.
    Kapı yapmak, elle girilmiş bir kaydı okunamaz hâle getirirdi.
    """
    bedel = float(ham["meta"]["kolon_bedeli"])
    for s in ham["satirlar"]:
        toplam = s["tek"] + s["cift"] + s["kapali"]
        if toplam != MAC_SAYISI:
            raise ValueError(
                f"({s['tek']},{s['cift']},{s['kapali']}) {toplam} maca "
                f"topluyor, {MAC_SAYISI} olmali")
        onceki = 0.0
        for g in GARANTILER:
            v = s["fiyat"][str(g)]
            if v is None:
                continue
            if round(v / bedel) * bedel != v:
                raise ValueError(
                    f"({s['tek']},{s['cift']},{s['kapali']}) {g}G fiyati "
                    f"{v}, kolon bedelinin ({bedel}) kati degil")
            if v < onceki:
                raise ValueError(
                    f"({s['tek']},{s['cift']},{s['kapali']}) {g}G {v} < "
                    f"onceki garanti {onceki}; daha siki garanti ucuzlayamaz")
            onceki = v


def _supheli_kume(ham: dict[str, Any]) -> set[tuple[int, int, int, int]]:
    return {(x["tek"], x["cift"], x["kapali"], x["garanti"])
            for x in ham.get("supheli", [])}


def bedel(tek: int, cift: int, kapali: int,
          garanti: int = VARSAYILAN_GARANTI,
          yol: str | None = None) -> Sekil | None:
    """Bir şeklin **ölçülmüş** bedeli. Şekil satılmıyorsa `None`.

    `secim.bedel_hesapla`nın aksine formül değil kayıt::

        >>> s = bedel(7, 8, 0, garanti=14)
        >>> s.kolon, s.tl
        (32, 320.0)

    Aynı şekil 13-garantide çok daha ucuz — ve pahalı olan bilgi değil
    garantidir::

        >>> bedel(7, 8, 0, garanti=13).kolon
        12

    Tabloda `-` yazan hücre satılmayan şekildir::

        >>> bedel(6, 9, 0, garanti=12) is None
        True
    """
    ham = _tablo(yol)
    if garanti not in GARANTILER:
        raise ValueError(f"garanti {GARANTILER} icinde olmali, {garanti} geldi")
    for s in ham["satirlar"]:
        if (s["tek"], s["cift"], s["kapali"]) != (tek, cift, kapali):
            continue
        v = s["fiyat"][str(garanti)]
        if v is None:
            return None
        kb = float(ham["meta"]["kolon_bedeli"])
        return Sekil(tek=tek, cift=cift, kapali=kapali,
                     kolon=round(v / kb), tl=float(v), garanti=garanti,
                     supheli=(tek, cift, kapali, garanti) in _supheli_kume(ham))
    return None


def sekiller(garanti: int = VARSAYILAN_GARANTI,
             en_cok_tl: float | None = None,
             yol: str | None = None) -> list[Sekil]:
    """Satılan bütün şekiller — bütçe verilirse yalnızca sığanlar.

    `secim` aramasının aday kümesi budur: formülün ürettiği her `(çifte,
    üçlü)` ikilisi değil, satıcının **gerçekten sattığı** şekiller.
    """
    out: list[Sekil] = []
    for s in _tablo(yol)["satirlar"]:
        x = bedel(s["tek"], s["cift"], s["kapali"], garanti, yol)
        if x is None:
            continue
        if en_cok_tl is not None and x.tl > en_cok_tl:
            continue
        out.append(x)
    return sorted(out, key=lambda x: x.tl)


def supheli_satirlar(yol: str | None = None) -> list[dict[str, Any]]:
    """Tekdüzeliği bozan satırlar — gerekçeleriyle."""
    return list(_tablo(yol).get("supheli", []))


def _main(argv: list[str] | None = None) -> int:  # pragma: no cover - elle
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--garanti", type=int, default=VARSAYILAN_GARANTI,
                    choices=GARANTILER)
    ap.add_argument("--butce", type=float, default=None,
                    help="TL cinsinden ust sinir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    liste = sekiller(a.garanti, a.butce)
    if a.json:
        print(json.dumps([x._asdict() for x in liste], ensure_ascii=False))
        return 0

    ham = _tablo(None)
    print(f"\nST EXTRA sistem fiyat tablosu — {len(ham['satirlar'])} sekil x "
          f"{len(GARANTILER)} garanti")
    print(f"kaynak : {ham['meta']['kaynak']}")
    print(f"kolon  : {ham['meta']['kolon_bedeli']:.2f} TL")
    print(f"garanti: {a.garanti}  ->  kacak esigi k <= {kacak_esigi(a.garanti)}"
          f"  (P(en iyi kolon >= {HEDEF_KADEME}))")
    if a.butce:
        print(f"butce  : {a.butce:,.0f} TL")
    print(f"\n{'tek':>4}{'cift':>6}{'kapali':>8}{'kolon':>8}{'TL':>12}")
    for x in liste:
        print(f"{x.tek:>4}{x.cift:>6}{x.kapali:>8}{x.kolon:>8}{x.tl:>12,.0f}"
              f"{'  SUPHELI' if x.supheli else ''}")
    print(f"\n{len(liste)} sekil")

    sup = supheli_satirlar()
    if sup:
        print(f"\nSUPHELI SATIR ({len(sup)}) — degerleri DUZELTILMEDI:")
        for sat in sup:
            print(f"  ({sat['tek']},{sat['cift']},{sat['kapali']}) "
                  f"{sat['garanti']}G = {sat['fiyat']:,} TL\n    {sat['sebep']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
