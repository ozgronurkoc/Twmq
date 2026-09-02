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


def indir(url: str, hedef: Path, zaman_asimi: float = 60.0) -> Path | None:
    """Kaynağı indirip `hedef`e yazar; **varsa yeniden indirmez**.

    Önbellek git dışıdır, bu yüzden var olan ve boş olmayan bir dosya
    yeterli sayılır. Ağ hatası sessizce yutulmaz: `stderr`e adıyla yazılır
    ve `None` döner — çağıran karar verir.
    """
    if hedef.exists() and hedef.stat().st_size > 0:
        return hedef
    istek = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as cevap:
            ham = cevap.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        print(f"  {url} alinamadi ({e})", file=sys.stderr)
        return None
    if not ham:
        return None
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(ham)
    return hedef


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
