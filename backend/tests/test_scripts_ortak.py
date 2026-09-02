"""`scripts/_ortak.py` — betiklerin paylaştığı stdlib katmanının bekçileri.

Bu modül `scripts/` altındaki sekiz `indir`, üç `tarih_coz`, üç `_metin` ve
altı `_modul` kopyasını tek gövdeye indirdi. Buradaki testler iki şeyi tutar:
katmanın **stdlib dışına çıkmaması** ve kopyaların **geri gelmemesi**.
"""
from __future__ import annotations

import ast
import sys
from datetime import datetime
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from scripts._ortak import metin, modul, tarih_coz

#: Bu betikler GitHub Actions'ta **hiçbir bağımlılık kurulmadan** koşuyor
#: (`snapshot-iddaa.yml`, `snapshot-sportoto.yml`). `_ortak` onların da
#: kullanabileceği tek ortak zemin olmak zorunda.
_BAGIMLILIKSIZ = ("snapshot_iddaa.py", "build_sportoto_arsiv.py")


def test_ortak_betik_katmani_stdlib_disina_cikmaz():
    """`scripts/_ortak.py` üçüncü parti ya da `spor_toto` import ETMEZ.

    Katmanın varlık sebebi bu: `snapshot_iddaa` ve `build_sportoto_arsiv`
    Actions'ta bağımlılıksız koşuyor. Buraya bir `numpy` ya da `spor_toto`
    importu girerse o iki iş, hatayı ancak haftalık cron ateşlendiğinde
    gösterir — yani en geç ve en pahalı yerde.
    """
    agac = ast.parse((KOK / "scripts" / "_ortak.py").read_text(encoding="utf-8"))
    kokler: set[str] = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Import):
            kokler |= {a.name.split(".")[0] for a in d.names}
        elif isinstance(d, ast.ImportFrom) and d.level == 0 and d.module:
            kokler.add(d.module.split(".")[0])

    disarida = sorted(k for k in kokler if k not in sys.stdlib_module_names)
    assert not disarida, (
        f"`scripts/_ortak.py` stdlib disina cikmis: {disarida}. "
        "Bu katman bagimliliksiz kosan betikler icin var."
    )


@pytest.mark.parametrize("dosya", _BAGIMLILIKSIZ)
def test_bagimliliksiz_betikler_spor_toto_import_etmez(dosya):
    """Actions'ta çıplak koşan betikler `spor_toto`'ya bağlanmamalı.

    `scripts/__init__.py` bunu bir kural olarak yazıyordu ama **bekçisi
    yoktu** — ve kural ölçüldüğünde beşlinin dördü için zaten yanlıştı
    (`build_avrupa`, `build_sehir`, `build_egitim`, `build_fixtures`
    `spor_toto` import ediyor). Kuralın gerçekten geçerli olduğu iki betik
    bunlar ve korunması gereken de tam olarak bu ikisi.
    """
    agac = ast.parse((KOK / "scripts" / dosya).read_text(encoding="utf-8"))
    for d in ast.walk(agac):
        adlar = []
        if isinstance(d, ast.Import):
            adlar = [a.name for a in d.names]
        elif isinstance(d, ast.ImportFrom) and d.module:
            adlar = [d.module]
        assert not any(a.split(".")[0] == "spor_toto" for a in adlar), (
            f"{dosya} `spor_toto` import ediyor; bu betik Actions'ta "
            "bagimliliksiz kosuyor ve orada `spor_toto` YOK."
        )


def test_tarih_coz_bosluga_takilmaz():
    """Boşluklu tarih, boşluksuzla **aynı** günü vermeli.

    Ölçülmüş ayrışmadan geldi: `build_odds`taki kopya `.strip()` yapmıyordu
    ve aynı football-data sütunundaki boşluklu bir tarih o boru hattında
    satırı düşürüyor, `build_egitim`de düşürmüyordu.
    """
    beklenen = datetime(2021, 9, 15)
    for ham in ("15/09/2021", " 15/09/2021", "15/09/2021 ", "\t15/09/2021\n"):
        assert tarih_coz(ham) == beklenen, ham
    assert tarih_coz("15/09/21") == beklenen
    for bos in ("", "   ", "abc", "32/13/2021"):
        assert tarih_coz(bos) is None, bos


def test_metin_kararli_ve_sirali():
    """Üretilmiş JSON metni anahtar sırasından bağımsız olmalı.

    `--kontrol` bayrakları üretilen metni diskteki dosyayla karşılaştırıyor;
    sıra oynarsa her koşumda yanlış yere "bayat" derdi.
    """
    a = metin({"b": 1, "a": {"z": 1, "y": 2}})
    b = metin({"a": {"y": 2, "z": 1}, "b": 1})
    assert a == b
    assert a.endswith("\n")
    assert '"a"' in a.split("\n")[1]      # sort_keys: a once


def test_modul_kardes_betigi_getirir():
    """`modul("hafta")` gerçekten `scripts.super_toto_hafta`yı verir."""
    m = modul("hafta")
    assert m.__name__ == "scripts.super_toto_hafta"


def test_paylasilan_yardimcilar_geri_kopyalanmamis():
    """`_ortak`taki gövdelerden hiçbiri `scripts/` altında yeniden yazılmamalı.

    `test_ortak.py`nin `spor_toto.ortak` icin yaptigini bu katman icin yapar:
    gövde imzası ada bağımsız çıkarılır, yani kopya başka adlarla yazılsa da
    yakalanır.
    """
    # `tests/` bir paket (`__init__.py` var); imza cikarici orada tanimli
    # ve BURAYA KOPYALANMIYOR — bu dosyanin konusu tam olarak o.
    from tests.test_ortak import _govde_imzasi

    ortak_agac = ast.parse((KOK / "scripts" / "_ortak.py").read_text(encoding="utf-8"))
    kanonik = {}
    for d in ortak_agac.body:
        if isinstance(d, ast.FunctionDef):
            imza = _govde_imzasi(d)
            if len(imza) >= 200:
                kanonik[imza] = d.name
    assert kanonik, "`_ortak` icinden hicbir govde imzalanamadi — bekci kor"

    ihlal = []
    for yol in sorted((KOK / "scripts").glob("*.py")):
        if yol.name == "_ortak.py":
            continue
        for d in ast.walk(ast.parse(yol.read_text(encoding="utf-8"))):
            if isinstance(d, ast.FunctionDef):
                ad = kanonik.get(_govde_imzasi(d))
                if ad:
                    ihlal.append(f"{yol.name}:{d.lineno} {d.name}() = _ortak.{ad}()")
    assert not ihlal, "`_ortak`taki govde yeniden yazilmis: " + "; ".join(ihlal)
