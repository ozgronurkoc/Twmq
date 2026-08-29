"""xG vekili — kalibrasyon okuma, sızıntı ve beyaz liste bekçileri.

**En kritik test `test_xg_gelecegi_gormez`.** Özellik bir maçın kendi şut
sayısından hesaplanıyor olsaydı model geleceği görürdü: şut sayısı ancak maç
bittiğinde bilinir. `xg_tablosu` bu yüzden `egitim._form_tablosu` ile aynı
"önce oku sonra işle" sırasını taşır ve burası o sıranın bekçisidir.

İkincisi `test_xg_tasarima_ulasiyor`: `recalibrate._mac_ozellikleri` bir
**beyaz listedir** ve yeni bir özelliği sessizce düşürür. `derbi` bir kez tam
bunu yaşadı — sütun her satırda sıfır kaldı, katsayı tam 0,000000 çıktı ve
ölçüm "derbi bir şey söylemiyor" diye okunacaktı. Aynı tuzak `xg_farki` için
de kuruludur.

Üçüncüsü `test_kalibrasyon_yoksa_notr`: katsayı dosyası yoksa modül
**uydurmaz**; her maç `xg_var=False` ve nötr 0 olur. `sehir.sehir_tablosu`
ile aynı sözleşme.
"""
from __future__ import annotations

import json

import pytest

from spor_toto.xg import (
    XG_PENCERE,
    kapsama,
    katsayilar,
    xg_tablosu,
    xg_vekili,
)

#: Testte kullanilan sahte katsayilar — gercek kalibrasyondan BAGIMSIZ.
#: Ölçülmüş degerlere baglanirsa `build_xg.py` yeniden kosuldugunda testler
#: veri degistigi icin kirilir; oysa test edilen sey ARITMETIK ve SIRA.
KAT = {"ev": {"isabet": 0.15, "isabetsiz": 0.05, "sabit": 0.10},
       "dep": {"isabet": 0.15, "isabetsiz": 0.05, "sabit": -0.20}}


def _mac(tarih: str, ev: str, dep: str, kod: str = "1",
         ev_sut: int = 10, ev_is: int = 5,
         dep_sut: int = 10, dep_is: int = 5) -> dict:
    return {"sezon": "9999", "lig": "XX", "tarih": tarih, "iso_yil": 2099,
            "iso_hafta": 1, "ev": ev, "dep": dep, "kod": kod,
            "oranlar": {"1": 2.0, "0": 3.0, "2": 4.0},
            "ev_sut": ev_sut, "ev_isabet": ev_is,
            "dep_sut": dep_sut, "dep_isabet": dep_is}


# ─── vekil aritmetigi ─────────────────────────────────────────────────────

def test_vekil_katsayilari_uygular():
    # 5 isabet · 5 isabetsiz -> 0,15*5 + 0,05*5 + 0,10 = 1,10
    assert xg_vekili(10, 5, True, KAT) == pytest.approx(1.10)


def test_vekil_ev_ve_deplasman_ayri():
    """İki taraf ayrı uydurulur; aynı sayım aynı sonucu vermez."""
    assert xg_vekili(10, 5, True, KAT) != xg_vekili(10, 5, False, KAT)


def test_vekil_negatife_dusmez():
    """Beklenen gol tanım gereği negatif olamaz.

    `dep` sabiti negatif ölçüldü; sıfır şutlu bir maçta doğrusal uydurma
    eksi beklenen gol verirdi ve o sayı bir sonraki basamağa aynen girerdi.
    """
    assert xg_vekili(0, 0, False, KAT) == 0.0


def test_vekil_isabet_sutu_asamaz():
    """`isabet > sut` bozuk bir satırdır; isabetsiz negatif sayılmaz."""
    assert xg_vekili(3, 5, True, KAT) == xg_vekili(5, 5, True, KAT)


def test_sayim_yoksa_none_doner():
    """`None` ile `0.0` ayrı şeyler — karıştırılırsa özellik sessizce seyrelir.

    Şut verisi olmayan bir maç `0.0` dönseydi "hiç şut çekilmedi" gibi
    görünür ve o maç geçmişe katılırdı.
    """
    assert xg_vekili(None, 5, True, KAT) is None
    assert xg_vekili(10, None, True, KAT) is None


def test_katsayi_yoksa_none_doner():
    assert xg_vekili(10, 5, True, {}) is None


# ─── sizinti ──────────────────────────────────────────────────────────────

def test_xg_gelecegi_gormez(monkeypatch):
    """**Sızıntı bekçisi** — modülün varlık sebebi.

    A takımı 5 maçta rakiplerinden çok daha fazla isabetli şut çekiyor, 6.
    maçta hiç çekmiyor. 6. maçtaki `xg_farki` o 5 maçı yansıtmalı
    (pozitif); kendi kötü maçını görmemeli. Sızıntı olsaydı değer düşerdi.
    """
    monkeypatch.setattr("spor_toto.xg.katsayilar", lambda yol=None: KAT)

    maclar = [_mac(f"2099-01-0{i}", "A", f"R{i}", ev_sut=15, ev_is=10,
                   dep_sut=5, dep_is=1) for i in range(1, 6)]
    # 6. mac: A hic isabetli sut cekmiyor
    maclar.append(_mac("2099-01-06", "A", "Z", ev_sut=1, ev_is=0,
                       dep_sut=15, dep_is=10))
    maclar += [_mac(f"2099-01-0{i}", "Z", f"Q{i}", ev_sut=5, ev_is=1,
                    dep_sut=5, dep_is=1) for i in range(1, 6)]

    tablo = xg_tablosu(maclar)
    alti = tablo[5]
    assert alti["xg_var"] is True
    assert alti["xg_farki"] > 0.5, (
        "6. macin xG vekili kendi sonucunu gormus olabilir")


def test_yeterli_gecmis_yoksa_isaretlenir():
    """Doktrin 2: eksik geçmiş uydurulmaz, `xg_var=False` ile bildirilir."""
    tablo = xg_tablosu([_mac("2099-01-01", "A", "B")])
    assert tablo[0]["xg_var"] is False
    assert tablo[0]["xg_farki"] == 0.0


def test_pencere_form_penceresiyle_ayni():
    """`form_isabet_farki` ile yan yana ölçülebilmesi buna bağlı.

    Pencere ayrışsaydı iki özellik arasındaki fark kalibrasyonun mu yoksa
    pencerenin mi olduğunu söyleyemezdik.
    """
    from spor_toto.egitim import FORM_PENCERE

    assert XG_PENCERE == FORM_PENCERE


def test_istatistiksiz_mac_gecmise_katilmaz(monkeypatch):
    """Şut verisi olmayan maç vekili kirletmemeli (doktrin 2)."""
    monkeypatch.setattr("spor_toto.xg.katsayilar", lambda yol=None: KAT)

    maclar = [_mac(f"2099-01-0{i}", "A", f"R{i}") for i in range(1, 6)]
    for m in maclar:
        m["ev_sut"] = None
    maclar.append(_mac("2099-01-06", "A", "Z"))
    assert xg_tablosu(maclar)[5]["xg_var"] is False


# ─── kalibrasyon dosyasi ──────────────────────────────────────────────────

def test_kalibrasyon_yoksa_notr(tmp_path):
    """Dosya yoksa modül uydurmaz — `sehir` ile aynı sözleşme."""
    yok = str(tmp_path / "yok.json")
    assert katsayilar(yok) == {}
    tablo = xg_tablosu([_mac("2099-01-01", "A", "B")], yok)
    assert tablo[0] == {"xg_var": False, "xg_farki": 0.0}


def test_eksik_yan_tumunu_dusurur(tmp_path):
    """Yarım kalibrasyon yoktur: iki yan da olmalı, yoksa hiçbiri.

    Yalnız `ev` tarafı okunsaydı deplasman vekili sessizce ev katsayısıyla
    hesaplanır ya da sıfır kalırdı; ikisi de ölçülmemiş bir sayı üretirdi.
    """
    p = tmp_path / "yarim.json"
    p.write_text(json.dumps({"katsayilar": {"ev": KAT["ev"]}}),
                 encoding="utf-8")
    assert katsayilar(str(p)) == {}


def test_bozuk_dosya_bos_doner(tmp_path):
    p = tmp_path / "bozuk.json"
    p.write_text("{ bu json degil", encoding="utf-8")
    assert katsayilar(str(p)) == {}


def test_kapsama_kalibrasyonsuz_sifir(tmp_path):
    r = kapsama([_mac("2099-01-01", "A", "B")], str(tmp_path / "yok.json"))
    assert r["kalibrasyon_var"] is False
    assert r["oran"] == 0.0


# ─── beyaz liste ve korpus ────────────────────────────────────────────────

def test_xg_tasarima_ulasiyor():
    """**Sessiz hatanın bekçisi** — `_mac_ozellikleri` bir BEYAZ LİSTEdir.

    `derbi` bir kez tam bu tuzağa düştü: özellik korpusta vardı, tasarım
    matrisinde sütun vardı, ama arada duran sözlük alanı taşımıyordu. Sütun
    her satırda sıfır kaldı ve ölçüm "xG bir şey söylemiyor" diye
    okunacaktı — oysa cevap **ölçülmemiş**ti.
    """
    from spor_toto.egitim import korpus_haftalari
    from spor_toto.recalibrate import _mac_ozellikleri

    if not katsayilar():
        pytest.skip("xg kalibrasyonu yok")
    o = [x for w in korpus_haftalari() for x in _mac_ozellikleri(w)]
    assert sum(1 for x in o if x.get("xg_farki")) > 100, \
        "xg_farki tasarima ulasmiyor — beyaz liste dusurmus olabilir"


def test_korpusta_kapsama_yuksek():
    """Özellik korpusun ezici çoğunluğunda tanımlı olmalı.

    Seyrelmiş bir özelliğin katsayısı sıfıra yakın çıkar ve bu *"sinyal
    yok"* diye okunur — oysa sebep seyrelmedir.
    """
    from spor_toto.egitim import korpus_yukle

    if not katsayilar():
        pytest.skip("xg kalibrasyonu yok")
    satirlar = korpus_yukle()
    if not satirlar:
        pytest.skip("korpus yok")
    assert kapsama(satirlar)["oran"] > 0.85
