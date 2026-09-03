"""`scripts/_ortak.py` — betiklerin paylaştığı stdlib katmanının bekçileri.

Bu modül `scripts/` altındaki sekiz `indir`, üç `tarih_coz`, üç `_metin` ve
altı `_modul` kopyasını tek gövdeye indirdi. Buradaki testler iki şeyi tutar:
katmanın **stdlib dışına çıkmaması** ve kopyaların **geri gelmemesi**.
"""
from __future__ import annotations

import ast
import re
import sys
import tempfile
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


# ─── scripts/bagimliliklar.py — denetim yuzeyinin bekcisi ─────────────────
#
# Bu betigin HIC testi yoktu ve iki kusuru ayni anda tasiyordu; ikisi de
# ancak kapi GERCEKTEN kosturulunca gorundu (CI gunlugu, 2026-09-02):
#
#   1. `import tomllib` ciplakti. `tomllib` stdlib'e 3.11'de girdi, kapi
#      ise bilerek 3.10'a sabitli — betik kapinin kostugu yorumlayicida
#      HIC calismadi.
#   2. Ciktisi bos kalinca boru hatti (`... | pip-audit -r /dev/stdin`)
#      BOS bir listeyi denetleyip "No known vulnerabilities found" dedi.
#      Yani guvenlik kapisi hicligi onayliyordu.
#
# Ucuncu bir sessiz kucultme daha vardi: denetlenen ekstralar dort ad
# olarak ELLE yaziliydi ve `mcp` ekstrasi eklendiginde liste guncellenmedi.

def _toml_okuyucu():
    """`tomllib` (3.11+) ya da `tomli` — ikisi de yoksa ADIYLA atlar.

    `tomli` `[kalite]` ekstrasinda; CI'nin matris isi yalnizca `[test]`
    kuruyor, yani py3.10 bacaginda TOML okunamaz. Atlamak burada
    dogru: ayni testler ayni depoda py3.11+ matris bacaklarinda ve
    py3.10 kalite kapisinda TAM kosuyor.
    """
    try:
        import tomllib
        return tomllib
    except ModuleNotFoundError:
        return pytest.importorskip(
            "tomli", reason="py3.10'da TOML okuyucu yok — `pip install -e '.[kalite]'`")


def _bagimliliklar_modulu():
    """`scripts/bagimliliklar.py`yi getirir.

    `_ortak.modul` KULLANILMAZ: o yardimci adin basina `super_toto_`
    ekliyor ve yalnizca o aileye hizmet ediyor.
    """
    import importlib

    return importlib.import_module("scripts.bagimliliklar")


def test_bagimlilik_denetimi_ILAN_EDILEN_her_ekstrayi_kapsar():
    """Yeni bir ekstra eklenince denetim yuzeyi SESSIZCE kucululmemeli.

    Liste elle yazildiginda tam bu oldu: `mcp` eklendi, liste guncellenmedi
    ve o ekstranin paketleri aylarca hic denetlenmedi.
    """
    _toml = _toml_okuyucu()
    m = _bagimliliklar_modulu()
    kok = Path(m.__file__).resolve().parent.parent / "pyproject.toml"
    with kok.open("rb") as fh:
        proje = _toml.load(fh)["project"]

    cikti = "\n".join(m.bagimliliklar())
    eksik = []
    for ad, paketler in proje.get("optional-dependencies", {}).items():
        if ad in m.EKSTRALAR_DISI:
            continue
        for p in paketler:
            # Paket adi: ilk karsilastirma/nokta-virgul isaretine kadar.
            isim = re.split(r"[<>=!;\[ ]", p, maxsplit=1)[0]
            if isim and isim not in cikti:
                eksik.append(f"{ad}:{isim}")
    assert not eksik, (
        "pyproject'te ilan edilen ama pip-audit'e GITMEYEN paketler: "
        + ", ".join(eksik))

    for p in proje.get("dependencies", []):
        isim = re.split(r"[<>=!;\[ ]", p, maxsplit=1)[0]
        assert isim in cikti, f"cekirdek bagimlilik denetlenmiyor: {isim}"


def test_bos_cikti_HATA_verir_sessizce_gecmez(monkeypatch, capsys):
    """Bos cikti, bos bir listeyi denetleyen YESIL bir guvenlik kapisidir.

    `python scripts/bagimliliklar.py | pip-audit -r /dev/stdin` boru
    hattinda uretici cokerse pip-audit BOS bir listeyi denetler ve
    "No known vulnerabilities found" der. Kapinin bunu kirmizi gormesi
    icin uretici SIFIRDAN FARKLI donmeli.
    """
    _toml_okuyucu()          # okuyucu yoksa betik zaten ice aktarilamaz
    m = _bagimliliklar_modulu()

    bos = Path(tempfile.mkdtemp()) / "pyproject.toml"
    bos.write_text('[project]\nname = "x"\nversion = "0"\n', encoding="utf-8")
    assert m.bagimliliklar(bos) == []

    monkeypatch.setattr(m, "bagimliliklar", lambda: [])
    assert m.main() == 1, "bos ciktida cikis kodu 0 — kapi hicligi onaylar"
    assert "bagimlilik bulunamadi" in capsys.readouterr().err


def test_betikler_asgari_python_surumunde_ICE_AKTARILABILIR():
    """`requires-python` ne diyorsa betikler orada calismali.

    `tomllib` (3.11+) ciplak import edildiginde depo `>=3.10` ilan
    ediyordu ve kapi 3.10'da kosuyordu; betik her CI kosumunda
    `ModuleNotFoundError` verdi. Ne ruff (stdlib surumune bakmaz) ne mypy
    (`files` listesi `scripts/`i kapsamiyor) yakaladi — bu yuzden bekci
    burada.

    Tablo kucuk ve BILEREK oyle: yalnizca 3.10'dan SONRA stdlib'e giren,
    bu depoda gercekten kullanilabilecek modulleri sayar.
    """
    # TOML AYRISTIRICISI KULLANILMAZ ve sebebi bu testin kendi konusu:
    # `tomllib` 3.11+, `tomli` ise `[kalite]` ekstrasinda. Ikisine de
    # dayanan bir bekci tam olarak KORUMASI GEREKEN yerde — py3.10, yalnizca
    # `[test]` kuran CI matris isi — ya duser ya atlanir. Ilk yazilisi
    # boyleydi ve orada dustu; ders aninda geri geldi. Aranan tek bir satir
    # oldugu icin duz okuma yeterli ve her surumde calisir.
    esles = re.search(r'requires-python\s*=\s*"([^"]+)"',
                      (KOK / "pyproject.toml").read_text(encoding="utf-8"))
    assert esles, "pyproject.toml icinde requires-python bulunamadi"
    asgari = esles.group(1)
    assert asgari == ">=3.10", (
        f"asgari surum degismis ({asgari}) — asagidaki tablo gozden gecirilmeli")

    #: stdlib'e 3.10'DAN SONRA giren moduller.
    SONRADAN = {"tomllib": "3.11", "asyncio.taskgroups": "3.11"}

    kusurlu = []
    for yol in sorted((KOK / "scripts").glob("*.py")) + \
               sorted((KOK / "spor_toto").glob("*.py")):
        agac = ast.parse(yol.read_text(encoding="utf-8"))
        for dugum in ast.walk(agac):
            if not isinstance(dugum, (ast.Import, ast.ImportFrom)):
                continue
            adlar = ([a.name for a in dugum.names] if isinstance(dugum, ast.Import)
                     else [dugum.module or ""])
            for ad in adlar:
                if ad not in SONRADAN:
                    continue
                # `try/except ImportError` icindeyse korumali sayilir.
                korumali = any(
                    isinstance(u, ast.Try) and dugum in ast.walk(u)
                    for u in ast.walk(agac))
                if not korumali:
                    kusurlu.append(f"{yol.name}: {ad} (stdlib {SONRADAN[ad]}+)")
    assert not kusurlu, (
        "asgari surumde (3.10) BULUNMAYAN stdlib modulu korumasiz import "
        "ediliyor: " + "; ".join(kusurlu))
