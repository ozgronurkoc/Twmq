"""Şehir / derbi — `TURETILEMEYEN` listesinden bir maddenin düşmesi.

**En kritik test `test_bilinmeyen_derbi_degil_diye_sayilir`.** Şehri
bilinmeyen bir takımın maçı "derbi değil" sayılır ve bu **tek yönlü,
kasıtlı** bir hatadır. Ters yönlü hata — bilinmeyeni derbi saymak — 667
maçlık bir kümeyi 916 bilinmeyenle sulandırır ve özelliği anlamsız kılardı.

İkincisi `test_bilinmiyor_ile_derbi_degil_ayri_seyler`: `derbi_mi` iki
değer birden döndürmek zorunda; tek değer dönseydi ölçüm "cevap yok"u
"cevap hayır" diye okurdu.
"""
from __future__ import annotations

import pytest

from spor_toto.sehir import derbi_mi, kapsama, sehir_tablosu

TABLO = {"A": "Istanbul", "B": "Istanbul", "C": "Ankara"}


def test_ayni_sehir_derbi():
    assert derbi_mi("A", "B", TABLO) == (True, True)


def test_farkli_sehir_derbi_degil():
    assert derbi_mi("A", "C", TABLO) == (False, True)


def test_bilinmeyen_derbi_degil_diye_sayilir():
    """**Asıl bekçi.** Bilinmeyen "derbi değil"dir — tek yönlü hata."""
    assert derbi_mi("A", "YOK", TABLO) == (False, False)
    assert derbi_mi("YOK", "A", TABLO) == (False, False)
    assert derbi_mi("YOK", "HIC", TABLO) == (False, False)


def test_bilinmiyor_ile_derbi_degil_ayri_seyler():
    """İki durum da `derbi=False` verir; **ikinci** değer onları ayırır."""
    _, bilinen = derbi_mi("A", "C", TABLO)
    _, bilinmeyen = derbi_mi("A", "YOK", TABLO)
    assert bilinen is True and bilinmeyen is False


def test_bos_tabloda_hicbir_sey_bilinmez():
    assert derbi_mi("A", "B", {}) == (False, False)


# ─── ayrıştırma ───────────────────────────────────────────────────────────

def test_sehir_coz_alan_sirasini_tolere_ediyor():
    """Yıl ve stadyum **olmayabilir**; şehir her zaman son alandır."""
    from scripts.build_sehir import sehir_coz

    assert sehir_coz("Arsenal FC, 1886, @ Emirates Stadium, London (Highbury)") \
        == ("Arsenal FC", "London")
    assert sehir_coz("Kasımpaşa İstanbul,   İstanbul (Beyoğlu)") \
        == ("Kasımpaşa İstanbul", "İstanbul")
    assert sehir_coz("Dorking Wanderers FC,      Dorking › Surrey") \
        == ("Dorking Wanderers FC", "Dorking")
    assert sehir_coz("Bayern München, 1900, @ Allianz Arena, München") \
        == ("Bayern München", "München")


def test_sehirsiz_kayit_none_doner():
    """Kaynak bazı kulüplerin şehrini hiç yazmıyor — uydurulmaz."""
    from scripts.build_sehir import sehir_coz

    assert sehir_coz("CD Leganés") == ("CD Leganés", None)


def test_yorum_atiliyor():
    from scripts.build_sehir import sehir_coz

    assert sehir_coz("Atlético Madrid,    Madrid    ## use Atlético de Madrid") \
        == ("Atlético Madrid", "Madrid")


def test_sadelestirme_ayirt_edici_kalir():
    from scripts.build_sehir import sadelestir

    assert sadelestir("Real Madrid CF") != sadelestir("Real Sociedad")
    assert sadelestir("Newport County AFC") == sadelestir("Newport County")


def test_elle_tablosu_kaynakla_tutarli():
    """`ELLE`'deki her hedef ad kaynakta **gerçekten** bulunmalı.

    Bu tablo ad eşler, şehir değil — yanlış bir satır uydurma şehir
    üretmez, kapsamayı düşürür. Bekçi onu adla yakalar.
    """
    import pathlib

    from scripts.build_sehir import ELLE, kulup_sehirleri, sadelestir

    kaynak = pathlib.Path("/tmp/openfootball-clubs")
    if not (kaynak / "europe").exists():
        pytest.skip("openfootball/clubs yerel kopyasi yok")
    tablo = kulup_sehirleri(kaynak)
    adlar = {ad for _, ad in tablo}
    eksik = sorted({v for v in ELLE.values() if sadelestir(v) not in adlar})
    assert not eksik, f"ELLE'de kaynakta olmayan ad: {eksik}"


# ─── gerçek tablo ─────────────────────────────────────────────────────────

def test_gercek_tablo_okunuyor():
    t = sehir_tablosu()
    if not t:
        pytest.skip("sehir tablosu yok — scripts/build_sehir.py")
    assert len(t) > 400
    assert all(isinstance(v, str) and v for v in t.values())


def test_gercek_kapsama_makul():
    """Kapsama sıfırsa ölçüm bir şeyi değil **hiçbir şeyi** ölçer."""
    from spor_toto.egitim import korpus_yukle

    satirlar = korpus_yukle()
    if not satirlar or not sehir_tablosu():
        pytest.skip("korpus ya da tablo yok")
    k = kapsama(satirlar)
    assert k["oran"] > 0.90, k
    # Derbi NADIRDIR: ayni ligde ayni sehirden iki takim istisnadir.
    assert 0.005 < k["derbi_orani"] < 0.10, k


def test_derbi_ozelligi_korpusa_giriyor():
    """Özellik gerçekten çalışıyor mu — sıfır sütun sessizce ölçülür."""
    from spor_toto.egitim import korpus_haftalari

    o = [x for w in korpus_haftalari() for x in w["ozellikler"]]
    if not sehir_tablosu():
        pytest.skip("sehir tablosu yok")
    assert sum(1 for x in o if x.get("derbi")) > 100
    assert sum(1 for x in o if not x.get("derbi_bilinir")) > 0


def test_derbi_sicaklik_sutunu_gercekten_calisiyor():
    """`derbi` basamağı `seri`ye **bir sütun** eklemeli."""
    import numpy as np

    from spor_toto.recalibrate import _tasarim_satiri

    ozellik = {"probs": {"1": 0.5, "0": 0.3, "2": 0.2}, "derbi": 1.0,
               "lig": "diger", "favori": "1", "bant": "diger"}
    a = _tasarim_satiri(ozellik, "seri", [], [])
    b = _tasarim_satiri(ozellik, "derbi", [], [])
    assert b.shape[1] == a.shape[1] + 1
    # Derbi sutunu `ayrisma` gibi `ln p_s`in modulasyonu.
    assert b[0, -1] == pytest.approx(np.log(0.5))


def test_derbi_yokken_sutun_sifir():
    from spor_toto.recalibrate import _tasarim_satiri

    b = _tasarim_satiri({"probs": {"1": 0.5, "0": 0.3, "2": 0.2},
                         "lig": "diger", "favori": "1", "bant": "diger"},
                        "derbi", [], [])
    assert list(b[:, -1]) == [0.0, 0.0, 0.0]


def test_turetilemeyen_listesi_kisaldi():
    """Faz 3.4'ün kaydı: `derbi` listeden **çıktı**, `seyahat` kaldı."""
    from spor_toto.disari import TURETILEBILIR_OLDU, TURETILEMEYEN

    assert "derbi" not in TURETILEMEYEN
    assert "seyahat" in TURETILEMEYEN
    assert "KOORDINAT" in TURETILEMEYEN["seyahat"]
    assert {"derbi", "avrupa"} <= set(TURETILEBILIR_OLDU)
    # Faz 3.4 iki kaynagi ARADI ve kapali buldu — kayit duruyor.
    assert {"xg", "kadro_sakatlik"} <= set(TURETILEMEYEN)
    assert "robots.txt" in TURETILEMEYEN["xg"]


def test_derbi_korpustan_tasarima_ulasiyor():
    """**Sessiz hatanın bekçisi.** `_mac_ozellikleri` bir BEYAZ LİSTEdir.

    `derbi` bir kez tam bu tuzağa düştü: özellik korpusta vardı, tasarım
    matrisinde sütun vardı, ama arada duran sözlük alanı taşımıyordu.
    Sütun her satırda sıfır kaldı, katsayı **tam 0,000000** çıktı ve ölçüm
    *"derbi bir şey söylemiyor"* diye okunacaktı. Düzeltildikten sonra
    katsayı +0,0992 oldu — yani "hiçbir şey" değil, **ölçülmemiş** bir
    şeydi.
    """
    from spor_toto.egitim import korpus_haftalari
    from spor_toto.recalibrate import _mac_ozellikleri

    if not sehir_tablosu():
        pytest.skip("sehir tablosu yok")
    o = [x for w in korpus_haftalari() for x in _mac_ozellikleri(w)]
    assert sum(1 for x in o if x.get("derbi")) > 100, \
        "derbi tasarima ulasmiyor — beyaz liste dusurmus olabilir"


def test_avrupa_da_tasarima_ulasiyor():
    """Aynı tuzak `avrupa_farki` için de kurulu — `A3_ALANLARI` üzerinden."""
    from spor_toto.avrupa import avrupa_gunleri
    from spor_toto.egitim import korpus_haftalari
    from spor_toto.recalibrate import _mac_ozellikleri

    if not avrupa_gunleri():
        pytest.skip("avrupa fiksturu yok")
    o = [x for w in korpus_haftalari() for x in _mac_ozellikleri(w)]
    assert sum(1 for x in o if x.get("avrupa_farki")) > 100
