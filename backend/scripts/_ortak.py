"""Betiklerin paylaştığı **saf standart kütüphane** yardımcıları.

**Neden ayrı bir modül.** `scripts/` altındaki betiklerde aynı on-yirmi
satır defalarca kopyalanmıştı ve kopyalar sessizce ayrışmıştı:

* `indir` sekiz yerde, üç varyantta;
* `tarih_coz` üç yerde — ve `build_odds`taki **`.strip()` yapmıyordu**, yani
  aynı football-data sütunundaki boşluklu bir tarih bir boru hattında satırı
  düşürüyor, ötekinde düşürmüyordu;
* `_metin` (JSON'u kararlı biçimde yazma) üç yerde birebir;
* `_modul` (kardeş betiği getirme) altı yerde — üçü **birebir gövde ve
  birebir docstring**, ki o docstring bir ÖNCEKI tekilleştirme turunu
  anlatıyor.

**Neden `spor_toto` değil.** Burası bilerek `spor_toto`'suz: `snapshot_iddaa`
ve `build_sportoto_arsiv` GitHub Actions'ta hiçbir bağımlılık kurulmadan
koşuyor ve bu modül onların da kullanabileceği tek ortak zemin. Buraya
üçüncü parti ya da `spor_toto` importu **girmez**; bekçisi
`tests/test_scripts_ortak.py::test_ortak_betik_katmani_stdlib_disina_cikmaz`.

Sayısal/olasılıksal hesaplar buraya DEĞİL `spor_toto.ortak`a gider — orası
paketin tek kaynağıdır ve arayüzün okuduğu gövdeyi üretir.
"""
from __future__ import annotations

import importlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

#: football-data ve kardeş kaynakların gün/ay/yıl biçimleri.
TARIH_BICIMLERI: tuple[str, ...] = ("%d/%m/%Y", "%d/%m/%y")

#: Kaynaklara kendimizi böyle tanıtıyoruz.
UA = "spor-toto-lab/1.0 (kisisel arsiv analizi)"


def tarih_coz(ham: str) -> datetime | None:
    """`GG/AA/YYYY` ya da `GG/AA/YY` — çözülemezse `None`.

    `.strip()` **gövdenin parçasıdır**: kopyalardan biri onu yapmıyordu ve
    aynı sütundaki boşluklu bir tarih iki boru hattında iki farklı sonuç
    veriyordu (biri satırı düşürüyor, öteki tarihi okuyordu).
    """
    ham = (ham or "").strip()
    for bicim in TARIH_BICIMLERI:
        try:
            return datetime.strptime(ham, bicim)
        except ValueError:
            continue
    return None


#: `urlopen`in kabul ettigi ama BIZIM asla kastetmedigimiz semalar.
#: `urllib.request.urlopen` `file:`, `ftp:` ve `data:` de acar; yani bir gun
#: bir URL sabitten degil de VERIDEN gelirse (yapilandirma, cekilen bir
#: dizin, bir yonlendirme) `file:///etc/passwd` sessizce OKUNUR ve indirilen
#: sey sanilir. Bugun butun cagrilar sabit `https://` ile geliyor; bu
#: denetim o dogrulugu bir VARSAYIM olmaktan cikarip KAPI yapiyor.
IZINLI_SEMALAR = ("http", "https")


def sema_dogrula(url: str) -> str:
    """URL semasini denetler; izinli degilse `ValueError`. Semayi dondurur.

    ACIK (private degil) cunku kendi `urlopen`ini kuran betikler de
    (`build_bulten.gorsel_indir` gibi, ayri hata politikasi tasidiklari
    icin ilkellere indirgenemeyenler) ayni denetimi kullanabilsin.
    Denetim TEK yerde yazili olmali; ikinci bir kopya ilk gun ayrisir.
    """
    sema = urllib.parse.urlparse(url).scheme.lower()
    if sema not in IZINLI_SEMALAR:
        raise ValueError(
            f"izin verilmeyen sema {sema!r}: {url} "
            f"(yalnizca {', '.join(IZINLI_SEMALAR)})")
    return sema


def _istek(url: str, headers: dict[str, str]) -> urllib.request.Request:
    """Semayi dogrulayip `Request` kurar — uc ilkelin ortak zemini."""
    sema_dogrula(url)
    # Asagidaki `noqa`nin gerekcesi: sema iki satir yukarida dogrulandi;
    # bu satir denetimin KENDISININ ciktisidir, denetimsiz cagri degil.
    return urllib.request.Request(url, headers=headers)  # noqa: S310


def indir(url: str, hedef: Path, zaman_asimi: float = 60.0) -> Path | None:
    """Kaynağı indirip `hedef`e yazar; **varsa yeniden indirmez**.

    Önbellek git dışıdır, bu yüzden var olan ve boş olmayan bir dosya
    yeterli sayılır. Ağ hatası sessizce yutulmaz: `stderr`e adıyla yazılır
    ve `None` döner — çağıran karar verir.
    """
    if hedef.exists() and hedef.stat().st_size > 0:
        return hedef
    istek = _istek(url, {"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as cevap:  # noqa: S310 - sema _istek'te dogrulandi
            ham = cevap.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        print(f"  {url} alinamadi ({e})", file=sys.stderr)
        return None
    if not ham:
        return None
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(ham)
    return hedef


def indir_bellek(url: str, zaman_asimi: float = 60.0) -> bytes | None:
    """Kaynağı **belleğe** indirir; diske yazmaz. Hata olursa `None`.

    `indir`den ayrı bir ilkel ve ayrı kalmalı: bazı kaynaklar tek seferlik ve
    çok büyük (`build_xg` 5,2 GB'lık bir arşivi diske yazmadan geçiriyor),
    bazıları ise önbelleklenmek zorunda. İkisini tek gövdeye sıkıştırmak
    çağıranı "yaz ama sakla ama silme" gibi bir bayrağa mahkûm ederdi.
    """
    istek = _istek(url, {"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as cevap:  # noqa: S310 - sema _istek'te dogrulandi
            return cevap.read()
    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, OSError) as e:
        print(f"  {url} alinamadi ({e})", file=sys.stderr)
        return None


def indir_json(url: str, zaman_asimi: float = 30.0,
               kabul: str = "application/json") -> Any:
    """JSON döndüren bir ucu çağırır. **Hata YUTULMAZ, yükselir.**

    Öteki iki ilkelden kasıtlı olarak farklı. Bunu kullanan iki betik
    (`snapshot_iddaa`, `build_sportoto_arsiv`) GitHub Actions'ta koşup depoya
    **commit atıyor**; orada yarım bir arşivi sessizce yazmak hiç
    yazmamaktan kötüdür. Ağ hatası işi düşürmeli ki cron kırmızı yansın.
    """
    istek = _istek(url, {"User-Agent": UA, "Accept": kabul})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as cevap:  # noqa: S310 - sema _istek'te dogrulandi
        return json.loads(cevap.read().decode("utf-8"))


def metin(veri: Any) -> str:
    """Üretilmiş JSON'un **kararlı** metni — tazelik denetimi buna dayanır.

    `sort_keys` ve sabit girinti şart: `--kontrol` bayrakları üretilen metni
    diskteki dosyayla karşılaştırıyor ve anahtar sırası oynarsa her koşumda
    yanlış yere "bayat" derdi.
    """
    return json.dumps(veri, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def modul(ad: str) -> Any:
    """Kardeş betiği getirir — sıradan bir import.

    Önce `spec_from_file_location` ile dosya yolundan yükleniyordu ve
    yüklerken `sys.argv`yi geçiciyle değiştiriyordu. İkisi de gereksizdi: bu
    dizin bir paket (`scripts/__init__.py`) ve hedef betiklerin hepsinde
    `if __name__ == "__main__"` guard'ı var, yani import etmek argparse'i
    tetiklemiyor.
    """
    return importlib.import_module(f"scripts.super_toto_{ad}")
