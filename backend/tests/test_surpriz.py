"""Sürpriz ekseninin denetimi.

Bu dosyada kilitlenen şeylerin ortak özelliği şu: **kırıldıklarında hiçbir
sayı hata vermez, sadece hepsi yanlış olur.**

`test_birlestirme_tarihle_denetleniyor` — iki arşivin hafta numaraları ayrı
kökenden gelir (resmî `GameRound` ↔ bülten/football-data). Kayarlarsa
haftanın ikramiyesi başka bir haftanın sonucuna yapışır. §5.6'daki v1 sıra
hatası tam olarak böyle aylarca görünmedi; orada da sezon toplamları
doğruydu.

`test_oran_eksik_hafta_kesite_girmez` — 13 maçın sürprizini 15 maçın
ikramiyesiyle karşılaştırmak, eksik iki maçı sessizce "sürpriz değil"
saymaktır. Milli maç haftaları (5, 10, 15) tam olarak bu tuzağı kurar.

`test_gercek_surpriz_surprizin_altkumesi` — iki tanım ters yazılabilir ve
ters yazıldığında sayılar hâlâ makul görünür.
"""
from __future__ import annotations

from itertools import pairwise

import pytest

from spor_toto.surpriz import (
    ASGARI_HAFTA,
    KUPON_MACI,
    SURPRIZ_BANTLARI,
    _gun_farki,
    bant_tablosu,
    dagilim,
    hafta_kayitlari,
    spearman,
    surpriz_ozeti,
)

# ─── birleştirme denetimi ────────────────────────────────────────────────

def test_gun_farki_bilinen_durumlar():
    assert _gun_farki("2023-08-11 20:55", "2023-08-11") == 0
    assert _gun_farki("2023-08-12", "2023-08-11 20:55") == 1
    assert _gun_farki("2023-09-11", "2023-08-11") == 31
    # Okunamayan tarih None doner — sessizce 0 DEGIL: 0 donseydi bozuk
    # tarihli bir hafta "tam eslesti" sayilirdi.
    assert _gun_farki(None, "2023-08-11") is None
    assert _gun_farki("bozuk", "2023-08-11") is None


def test_birlestirme_tarihle_denetleniyor():
    """Bugün sapan hafta YOK — ve sapsaydı elenip gövdede görünürdü."""
    _, denetim = hafta_kayitlari()
    tarih = [e for e in denetim["elenenler"] if e["sebep"] == "tarih tutmadı"]
    assert tarih == [], f"hafta numaraları kaymış olabilir: {tarih}"


def test_eleme_sessiz_degil():
    """Elenen her hafta sebebiyle birlikte gövdede durur."""
    kayitlar, denetim = hafta_kayitlari()
    assert denetim["kesit"] == len(kayitlar)
    assert len(denetim["elenenler"]) == denetim["elenen"]
    for e in denetim["elenenler"]:
        assert e["sebep"]
        assert e["sezon"] and e["hafta"] is not None


def test_oran_eksik_hafta_kesite_girmez():
    kayitlar, _ = hafta_kayitlari()
    assert kayitlar, "kesit boş — arşivlerden biri okunamıyor"
    for k in kayitlar:
        assert len(k["maclar"]) == KUPON_MACI


def test_kesitteki_her_hafta_dort_kademeyi_tasir():
    kayitlar, _ = hafta_kayitlari()
    for k in kayitlar:
        assert sorted(k["kazanan"]) == [12, 13, 14, 15]
        assert sorted(k["odul"]) == [12, 13, 14, 15]
        # 12 kademesi hacim vekili; kazanansiz kalirsa vekil coker.
        assert k["kazanan"][12] > 0


# ─── iki sürpriz tanımı ──────────────────────────────────────────────────

def test_gercek_surpriz_surprizin_altkumesi():
    """`ger_surpriz` beraberliği DIŞLAR, `surpriz` içerir — daima ≤."""
    kayitlar, _ = hafta_kayitlari()
    for k in kayitlar:
        assert 0 <= k["ger_surpriz"] <= k["surpriz"] <= KUPON_MACI


def test_surpriz_sayimi_favori_karsilastirmasiyla_tutarli():
    kayitlar, _ = hafta_kayitlari()
    for k in kayitlar:
        beklenen = sum(1 for m in k["maclar"] if m["favourite"] != m["code"])
        gercek = sum(1 for m in k["maclar"]
                     if m["favourite"] != m["code"] and m["code"] != "0")
        assert k["surpriz"] == beklenen
        assert k["ger_surpriz"] == gercek


def test_surprizsiz_hafta_yok():
    """Eksenin var olma sebebi: sürpriz bir olay değil, bir sabit.

    Bu bir ölçüm sonucudur ve değişebilir; değiştiğinde bekçi kırılsın
    isteniyor — çünkü değiştiği an eksenin gerekçesi de değişir.
    """
    kayitlar, _ = hafta_kayitlari()
    assert min(k["surpriz"] for k in kayitlar) > 0


# ─── Spearman ───────────────────────────────────────────────────────────

def test_spearman_bilinen_durumlar():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    # Dogrusal olmayan ama monoton: Pearson 1 vermezdi, Spearman verir.
    assert spearman([1, 2, 3, 4], [1, 4, 9, 16]) == pytest.approx(1.0)


def test_spearman_bagli_siralar_ortalanir():
    # Ikinci dizi tamamen sabit -> payda sifir -> tanimsiz, None doner.
    assert spearman([1, 2, 3], [5, 5, 5]) is None


def test_spearman_kucuk_ornek_sayi_vermez():
    assert spearman([1, 2], [1, 2]) is None
    assert spearman([1, 2, 3], [1, 2]) is None


# ─── bant tablosu ───────────────────────────────────────────────────────

def _sahte(surpriz: int, kazanan15: int = 5) -> dict:
    return {"sezon": "x", "hafta": 1, "maclar": [], "surpriz": surpriz,
            "ger_surpriz": 0, "logp": -1.0, "ort_logp": -1.0,
            "kazanan": {15: kazanan15, 14: 10, 13: 100, 12: 1000},
            "odul": {15: 100.0, 14: 10.0, 13: 1.0, 12: 0.5},
            "hacim": 500.0}


def test_az_haftali_bant_sayi_vermez():
    """`ASGARI_HAFTA` altında ortanca kendi gürültüsünü ölçer."""
    tablo = bant_tablosu([_sahte(0) for _ in range(ASGARI_HAFTA - 1)])
    ilk = tablo[0]
    assert ilk["yeterli"] is False
    assert "kazanan_15" not in ilk


def test_bant_tablosu_ortanca_kullanir_ortalama_degil():
    """Tek bir uç hafta bandı belirlememeli."""
    kayitlar = [_sahte(0, k) for k in (1, 1, 1, 10_000)]
    ilk = bant_tablosu(kayitlar)[0]
    assert ilk["kazanan_15"] == 1.0        # ortanca; ortalama 2.500 olurdu


def test_bantlar_kesisMEZ_ve_butun_araligi_kaplar():
    for onceki, sonraki in pairwise(SURPRIZ_BANTLARI):
        assert onceki[1] == sonraki[0]
    assert SURPRIZ_BANTLARI[0][0] == 0
    assert SURPRIZ_BANTLARI[-1][1] > KUPON_MACI


def test_dagilim_toplami_kesite_esit():
    kayitlar, _ = hafta_kayitlari()
    assert sum(d["hafta"] for d in dagilim(kayitlar)) == len(kayitlar)


# ─── gövde sözleşmesi ───────────────────────────────────────────────────

def test_ozet_govdesi_sinirini_tasir():
    o = surpriz_ozeti()
    assert o["kesit"] > 0
    for alan in ("dagilim", "bantlar", "korelasyon", "denetim", "tanim",
                 "sinir", "hafta_basi"):
        assert alan in o
    # "Hangi mac surpriz OLACAK" iddiasi asla girmemeli; sinir metni bunu
    # yazili tutar ve silinirse bekci kirilir.
    assert "hangi maçın sürpriz OLACAĞINI söylemez" in o["sinir"]


def test_korelasyon_isaretleri_yon_degistirmedi():
    """Sürpriz arttıkça kazanan azalır; favorililik arttıkça artar.

    İşaret sabitlenmiştir, büyüklük değil: ölçüm yeni sezonlarla oynayabilir
    ama YÖN değişirse eksenin bütün yorumu terse döner.
    """
    k = surpriz_ozeti()["korelasyon"]
    assert k["surpriz"]["kazanan_15"] < 0
    assert k["ger_surpriz"]["kazanan_15"] < 0
    assert k["ort_logp"]["kazanan_15"] > 0
