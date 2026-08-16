"""Iddaa bülten snapshot'ı — ayrıştırma ve yazma denetimi.

Testler **ağa çıkmaz**: gerçek bültenden alınmış küçük bir örnek payload
üzerinde çalışır. Ağ çağrısını test etmek bu paketin işi değil; ayrıştırmanın
doğruluğu ise arşivin tamamının dayandığı şey.
"""

import csv
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "snapshot_iddaa", KOK / "scripts" / "snapshot_iddaa.py"
)
snap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(snap)


def _etkinlik(i: int, hn: str, an: str, oranlar, *, sid=1, ci=1912, d=1786915800):
    """Bültendeki gerçek şekle birebir uyan bir etkinlik kaydı."""
    return {
        "i": i, "hn": hn, "an": an, "sid": sid, "ci": ci, "d": d, "il": True,
        "m": [
            # Alt/üst pazarı: 1X2 ile karışmamalı.
            {"t": 2, "st": 101, "sov": "2.5", "o": [
                {"no": 1, "odd": 1.67, "wodd": 1.61, "n": "Alt"},
                {"no": 2, "odd": 1.82, "wodd": 1.76, "n": "Üst"},
            ]},
            {"t": 1, "st": 1, "o": [
                {"no": i, "odd": o, "wodd": round(o * 0.96, 2), "n": s}
                for i, (s, o) in enumerate(zip(("1", "0", "2"), oranlar), 1)
            ]},
        ],
    }


ORNEK = {
    "isSuccess": True,
    "data": {
        "version": 1786892832819,
        "events": [
            _etkinlik(3056613, "FC Otelul Galati", "Un. Craiova", (3.76, 3.15, 1.67)),
            _etkinlik(3057367, "NK Radomlje", "NK Aluminij", (2.16, 3.10, 2.53), ci=1000),
            # Basketbol: futbol olmadigi icin elenmeli.
            _etkinlik(9, "A", "B", (1.5, 3.0, 5.0), sid=2),
            # 1X2 pazari olmayan etkinlik: elenmeli.
            {"i": 10, "hn": "C", "an": "D", "sid": 1, "ci": 1, "d": 1786915800,
             "m": [{"t": 2, "st": 101, "o": [{"n": "Alt", "odd": 1.5}]}]},
        ],
    },
}

LIGLER = {"isSuccess": True, "data": [
    {"i": 1912, "n": "Romanya 1. Lig"},
    {"i": 1000, "n": "Slovenya 1. SNL"},
]}


def test_govde_sarmali_acilir():
    assert snap._govde(ORNEK)["version"] == 1786892832819
    # Sarmalsiz govde de kabul edilir.
    assert snap._govde({"events": []}) == {"events": []}


def test_basarisiz_cevap_hata_verir():
    with pytest.raises(RuntimeError):
        snap._govde({"isSuccess": False, "data": None, "message": "bakim"})


def test_lig_adlari():
    assert snap.lig_adlari(LIGLER) == {1912: "Romanya 1. Lig", 1000: "Slovenya 1. SNL"}
    assert snap.lig_adlari({"isSuccess": True, "data": []}) == {}


def test_ms_orani_dogru_pazari_secer():
    """Bültende maça bağlı çok pazar var; yalnızca t=1/st=1 olan alınır."""
    blok = snap.ms_orani(ORNEK["data"]["events"][0])
    assert blok["odd"] == {"1": 3.76, "0": 3.15, "2": 1.67}
    assert set(blok["wodd"]) == {"1", "0", "2"}
    # Alt/ust pazari sizmamali.
    assert "Alt" not in blok["odd"] and "Üst" not in blok["odd"]


def test_eksik_ayakli_pazar_saklanmaz():
    """İki ayaklı bir '1X2' yanıltır; hiç yok sayılır."""
    e = {"sid": 1, "m": [{"t": 1, "st": 1, "o": [
        {"n": "1", "odd": 2.0}, {"n": "2", "odd": 3.0},
    ]}]}
    assert snap.ms_orani(e) is None


def test_askidaki_ayak_maci_eler():
    """1.00 fiyat değil, askıya alınmış ayağın yer tutucusudur.

    Gerçek bültende ölçüldü: 225 maçın 3'ünde 17.95 / 8.48 / 1.00 gibi
    anlamsız bir üçlü var. Fiyatmış gibi saklamak sonraki analizi zehirler.
    """
    e = _etkinlik(11, "AL Anwar", "Ahli Saudi", (17.95, 8.48, 1.0))
    assert snap.ms_orani(e) is None


def test_marj_pozitif_ve_hesabi_dogru():
    m = snap.marj({"1": 2.0, "0": 4.0, "2": 4.0})
    assert m == pytest.approx(0.0, abs=1e-9)  # 0.5+0.25+0.25 = 1.0
    assert snap.marj({"1": 1.9, "0": 3.8, "2": 3.8}) > 0
    assert snap.marj({"1": 2.0, "0": 4.0}) is None
    assert snap.marj({"1": 0.0, "0": 4.0, "2": 4.0}) is None


def test_satirlar_filtreler_ve_siralar():
    satirlar = snap.satirlar_uret(
        snap._govde(ORNEK), snap.lig_adlari(LIGLER), "2026-08-16 15:08"
    )
    # Futbol olmayan ve 1X2'si olmayan elendi.
    assert len(satirlar) == 2
    assert [r["event_id"] for r in satirlar] == [3056613, 3057367]
    r = satirlar[0]
    assert r["lig"] == "Romanya 1. Lig"
    # `d` unix saniye -> UTC; oran arsiviyle ayni eksende.
    assert r["kickoff"] == "2026-08-16 21:30"
    assert r["marj"] > 0


def test_csv_ve_sqlite_yazimi(tmp_path):
    satirlar = snap.satirlar_uret(
        snap._govde(ORNEK), snap.lig_adlari(LIGLER), "2026-08-16 15:08"
    )
    csv_yol = tmp_path / "iddaa_2026-08-16.csv"
    snap.csv_yaz(csv_yol, satirlar)
    okunan = list(csv.DictReader(csv_yol.open(encoding="utf-8")))
    assert len(okunan) == 2
    assert okunan[0]["odd_1"] == "3.76" and okunan[0]["odd_2"] == "1.67"
    assert okunan[0]["lig"] == "Romanya 1. Lig"

    db_yol = tmp_path / "iddaa.sqlite3"
    snap.sqlite_yaz(db_yol, satirlar)
    with sqlite3.connect(db_yol) as db:
        assert db.execute("SELECT COUNT(*) FROM mac").fetchone()[0] == 2
        # 2 mac x 3 sembol x 2 fiyat listesi (kupon + web)
        assert db.execute("SELECT COUNT(*) FROM oran").fetchone()[0] == 12
        # Uzun bicim: oran arsiviyle ayni sorgu diliyle okunuyor mu.
        deger = db.execute(
            "SELECT deger FROM oran WHERE event_id=? AND pazar='1X2' "
            "AND secim='2' AND donem='kupon'", (3056613,)
        ).fetchone()[0]
        assert deger == 1.67


def test_ayni_snapshot_tekrar_yazilabilir(tmp_path):
    """Aynı gün iki kez çalışmak satırı çoğaltmaz, üstüne yazar."""
    satirlar = snap.satirlar_uret(
        snap._govde(ORNEK), snap.lig_adlari(LIGLER), "2026-08-16 15:08"
    )
    db_yol = tmp_path / "iddaa.sqlite3"
    snap.sqlite_yaz(db_yol, satirlar)
    snap.sqlite_yaz(db_yol, satirlar)
    with sqlite3.connect(db_yol) as db:
        assert db.execute("SELECT COUNT(*) FROM mac").fetchone()[0] == 2


def test_farkli_snapshot_birikir(tmp_path):
    """Farklı zamanda alınan aynı maç AYRI satırdır — arşivin amacı bu."""
    govde, ligler = snap._govde(ORNEK), snap.lig_adlari(LIGLER)
    db_yol = tmp_path / "iddaa.sqlite3"
    snap.sqlite_yaz(db_yol, snap.satirlar_uret(govde, ligler, "2026-08-09 12:00"))
    snap.sqlite_yaz(db_yol, snap.satirlar_uret(govde, ligler, "2026-08-16 12:00"))
    with sqlite3.connect(db_yol) as db:
        assert db.execute("SELECT COUNT(*) FROM mac").fetchone()[0] == 4
        assert db.execute(
            "SELECT COUNT(DISTINCT alinma) FROM oran"
        ).fetchone()[0] == 2


def test_yayindaki_snapshot_okunabilir():
    """Depoda snapshot varsa biçimi bozulmamış olmalı."""
    dizin = KOK / "data" / "iddaa"
    dosyalar = sorted(dizin.glob("iddaa_*.csv")) if dizin.exists() else []
    if not dosyalar:
        pytest.skip("henüz snapshot alınmamış (scripts/snapshot_iddaa.py)")
    for yol in dosyalar:
        satirlar = list(csv.DictReader(yol.open(encoding="utf-8")))
        assert satirlar, f"{yol.name} boş"
        for r in satirlar:
            assert list(r) == snap.CSV_BASLIK
            for s in ("1", "0", "2"):
                assert float(r[f"odd_{s}"]) > 1.0
            assert float(r["marj"]) > 0, "bahisçi payı pozitif olmalı"


def test_rapor_yayindaysa_tutarli():
    yol = KOK / "data" / "iddaa" / "iddaa_rapor.json"
    if not yol.exists():
        pytest.skip("henüz snapshot alınmamış")
    r = json.loads(yol.read_text(encoding="utf-8"))
    assert r["with_1x2"] <= r["football_events"]
    assert r["snapshots"]
    # Iddaa marji piyasa marjindan (%7,26) belirgin yuksek — kaynak
    # durustlugu notunun olculmus dayanagi.
    assert r["avg_margin_pct"] is None or r["avg_margin_pct"] > 7.26
