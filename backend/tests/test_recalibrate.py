"""Yeniden kalibrasyon adayının denetimi.

Ayrım burada önemli: testlerin çoğu **sözleşme** sınar (şekil, determinizm,
eğitimsizken ne yaptığı), bir tanesi ise bilinçli olarak **bulgu** sabitler.
Bulgu testi veri büyüdüğünde kırılabilir ve kırılması istenir — sessizce
değişmesindense haber vermesi yeğdir (`test_bulgu_*`).

Uydurucunun gerçekten öğrendiğini kanıtlamak için sentetik bir sinyal
kullanılır: piyasanın beraberliği sistematik olarak ucuz fiyatladığı bir
kurguda modelin beraberliğe doğru kayması gerekir. Bunu yapmıyorsa geri kalan
her ölçüm anlamsızdır.
"""

import numpy as np
import pytest

from spor_toto import recalibrate
from spor_toto.evaluate import brier, olculebilir_haftalar
from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.recalibrate import (
    KADEMELER,
    KalibreTahminci,
    _bant_adi,
    _softmax,
    kademe_fabrikalari,
    rapor,
)

PIYASA = {"1": 0.50, "0": 0.25, "2": 0.25}


def _girdi(week: int, results: str, probs=None) -> dict:
    return {
        "week": week, "close_date": "2026-01-01", "results": results,
        "probs": list(probs) if probs else [dict(PIYASA)] * MATCH_COUNT,
        "missing": 0, "usable": True,
    }


# ─── sözleşme ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kademe", KADEMELER)
def test_sozlesme_sekil_ve_toplam(kademe):
    t = KalibreTahminci(kademe)
    t.egit([_girdi(i, "102" * 5) for i in range(1, 8)])
    tahminler = t.tahmin(_girdi(9, "102" * 5))

    assert len(tahminler) == MATCH_COUNT
    for p in tahminler:
        assert set(p) == set(SYMBOLS)
        assert pytest.approx(sum(p.values()), abs=1e-9) == 1.0
        assert all(0.0 <= v <= 1.0 for v in p.values())


def test_bilinmeyen_kademe_reddedilir():
    with pytest.raises(ValueError, match="bilinmeyen kademe"):
        KalibreTahminci("olmayan")


@pytest.mark.parametrize("kademe", KADEMELER)
def test_egitilmeden_piyasayi_gecirir(kademe):
    """Uydurma düzeltme üretmez; bilgisizken piyasayı olduğu gibi taşır."""
    tahminler = KalibreTahminci(kademe).tahmin(_girdi(1, "1" * MATCH_COUNT))
    assert all(p == PIYASA for p in tahminler)


def test_bos_egitim_seti_cokmez():
    t = KalibreTahminci("bias")
    t.egit([])
    assert t.katsayilar is None
    assert t.tahmin(_girdi(1, "1" * MATCH_COUNT))[0] == PIYASA


@pytest.mark.parametrize("fabrika", kademe_fabrikalari())
def test_fabrikalar_taze_ornek_verir(fabrika):
    assert fabrika() is not fabrika()


def test_kademe_fabrikalari_tum_basamaklari_kapsar():
    assert [f().kademe for f in kademe_fabrikalari()] == list(KADEMELER)


# ─── determinizm ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kademe", KADEMELER)
def test_ayni_egitim_ayni_katsayi(kademe):
    """Rastgelelik yok — 'ölçtük' demenin önkoşulu."""
    haftalar = [_girdi(i, "102" * 5) for i in range(1, 8)]
    a, b = KalibreTahminci(kademe), KalibreTahminci(kademe)
    a.egit(haftalar)
    b.egit(haftalar)
    assert a.katsayilar == pytest.approx(b.katsayilar, abs=1e-12)


@pytest.mark.parametrize("kademe", KADEMELER)
def test_uydurucu_butcesinin_icinde_yakinsar(kademe, monkeypatch):
    """Gerileme testi: yineleme bütçesi gerçekten yetiyor mu.

    İlk sürüm gradyan inişi kullanıyordu ve 15 parametreli `bant` modeli
    20 000 adımda bile sürükleniyordu. **Eksik uydurulmuş bir model, aşırı
    uyumla aynı görüntüyü verir** (dışarıda skor kötü çıkar), yani bu hata
    bulguyu sessizce yanlış yorumlatırdı.

    Ölçüt: bütçenin onda biriyle uydurulan katsayı, tam bütçeyle
    uydurulandan ayırt edilemez olmalı.
    """
    haftalar = olculebilir_haftalar()

    monkeypatch.setattr(recalibrate, "EN_COK_YINELEME", 10)
    erken = KalibreTahminci(kademe)
    erken.egit(haftalar)

    monkeypatch.setattr(recalibrate, "EN_COK_YINELEME", 100)
    tam = KalibreTahminci(kademe)
    tam.egit(haftalar)

    assert erken.katsayilar == pytest.approx(tam.katsayilar, abs=1e-8)


# ─── uydurucu gerçekten öğreniyor mu ──────────────────────────────────────────

def test_sistematik_sapmayi_yakalar():
    """Piyasa beraberliği ucuz fiyatlıyorsa model beraberliğe kaymalı.

    Kurgu: piyasa her maça p(0)=0,25 diyor ama sonuçların yarısı beraberlik.
    Uydurucu çalışıyorsa eğitim sonrası p(0) belirgin biçimde yükselmeli.
    Yükselmiyorsa geri kalan bütün ölçümler anlamsızdır.
    """
    sonuc = ("0" * 8 + "1" * 4 + "2" * 3)
    haftalar = [_girdi(i, sonuc) for i in range(1, 13)]
    t = KalibreTahminci("bias")
    t.egit(haftalar)

    p = t.tahmin(_girdi(99, sonuc))[0]
    assert p["0"] > PIYASA["0"] + 0.10, "beraberlige kaymadi"
    assert p["0"] > p["1"], "cogunluk sembolu one gecmedi"


def test_sinyalsiz_veride_piyasadan_uzaklasmaz():
    """Sonuçlar piyasayla uyumluysa düzeltme küçük kalmalı."""
    sonuc = ("1" * 8 + "0" * 4 + "2" * 3)  # ~ p(1)=0,53 · p(0)=0,27 · p(2)=0,20
    t = KalibreTahminci("sicaklik")
    t.egit([_girdi(i, sonuc) for i in range(1, 13)])
    p = t.tahmin(_girdi(99, sonuc))[0]
    assert abs(p["1"] - PIYASA["1"]) < 0.15


# ─── yardımcılar ──────────────────────────────────────────────────────────────

def test_softmax_toplami_bir():
    q = _softmax(np.array([2.0, -1.0, 0.5]))
    assert pytest.approx(float(q.sum()), abs=1e-12) == 1.0


def test_softmax_buyuk_sayida_tasmaz():
    q = _softmax(np.array([1000.0, 999.0, 0.0]))
    assert np.all(np.isfinite(q))
    assert pytest.approx(float(q.sum()), abs=1e-12) == 1.0


@pytest.mark.parametrize("oran,beklenen", [
    (1.10, "1.00-1.20"),
    (1.20, "1.20-1.35"),   # alt sınır dahil
    (1.34, "1.20-1.35"),
    (2.50, "2.00-99.00"),
    (None, "bilinmiyor"),
    (150.0, "bilinmiyor"),  # üst bandın da dışında
])
def test_bant_sinirlari(oran, beklenen):
    assert _bant_adi(oran) == beklenen


# ─── gerçek veri: bulgu ───────────────────────────────────────────────────────

def test_bulgu_kademe_piyasayi_gecemiyor():
    """**Bulgu testi** — sözleşme değil.

    2026-08 ölçümü: kademenin hiçbir basamağı piyasayı geçmiyor. Veri
    büyüdüğünde (S1: ikinci sezon) bu değişebilir ve değişirse **haber
    vermesi istenir** — sessizce geçmiş sayılmasındansa test kırılsın.
    """
    r = rapor()
    adlar = {s["ad"] for s in r["tahminciler"]}
    assert adlar == {"piyasa"} | {f"kalibre_{k}" for k in KADEMELER}

    for s in r["tahminciler"]:
        if s["ad"] != "piyasa":
            assert s["gecti"] is False, f"{s['ad']} piyasayi gecti — bulguyu guncelle"


def test_bulgu_kapasite_arttikca_disarida_kotulesiyor():
    """**Bulgu testi** — aşırı uyumun imzası.

    Eğitim-içi skor kapasiteyle iyileşirken hafta-dışarıda skorun kötüleşmesi
    bu ölçümün ana sonucudur. Sıralamanın bozulması, ya verinin büyüdüğünü ya
    da uydurucunun değiştiğini gösterir; ikisi de bakılmayı hak eder.
    """
    r = rapor()
    skor = {s["ad"]: s["brier"] for s in r["tahminciler"]}
    assert skor["kalibre_bias"] < skor["kalibre_lig"] < skor["kalibre_bant"]
    assert skor["kalibre_bant"] > skor["piyasa"]


def test_gercek_veride_egitim_ici_kapasiteyle_iyilesiyor():
    """Aşırı uyumun öteki yarısı: eğitim setinde her basamak daha iyi."""
    haftalar = olculebilir_haftalar()

    def icsel(kademe: str) -> float:
        t = KalibreTahminci(kademe)
        t.egit(haftalar)
        top = n = 0.0
        for hafta in haftalar:
            tahminler = t.tahmin(hafta)
            for k, kod in enumerate(hafta["results"]):
                top += brier(tahminler[k], kod)
                n += 1
        return top / n

    skorlar = {k: icsel(k) for k in KADEMELER}
    sirali = [skorlar[k] for k in KADEMELER]
    # Azalan ama STRICT degil: `form` kupon kesitinde `bant` ile berabere
    # kalir, cunku kupon haftalari form tasimaz (asagidaki testin konusu).
    # Tolerans, esit ciftin kayan nokta gurultusu icin: ayni modelin iki
    # sifir sutunu fazlasi Newton cozumunde ~1e-13 fark uretiyor.
    assert all(a >= b - 1e-9 for a, b in zip(sirali, sirali[1:])), "egitim-ici artmis"
    assert skorlar["bant"] < skorlar["lig"] < skorlar["bias"] < skorlar["sicaklik"]


def test_form_kupon_kesitinde_bant_ile_ozdes():
    """Kupon haftaları form taşımaz — `form` orada `bant`'tan ayrışamaz.

    Bu bir eksiklik değil, ölçümün sınırı: form yalnızca eğitim korpusunda
    var. Kuponda form sütunları sabit 0 olduğu için model birebir aynı
    kalır. Sayı ayrışırsa nötr-form sözleşmesi bozulmuş demektir.
    """
    haftalar = olculebilir_haftalar()

    def katsayi(kademe: str):
        t = KalibreTahminci(kademe)
        t.egit(haftalar)
        return t.katsayilar

    bant, form = katsayi("bant"), katsayi("form")
    assert form[:len(bant)] == pytest.approx(bant, abs=1e-6)
    assert form[len(bant):] == pytest.approx([0.0, 0.0], abs=1e-6), (
        "kuponda form katsayisi sifirdan farkli — notr sozlesmesi bozuk")
