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

import itertools

import numpy as np
import pytest

from spor_toto import recalibrate
from spor_toto.egitim import korpus_haftalari
from spor_toto.evaluate import brier, olculebilir_haftalar
from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.recalibrate import (
    ETKILESIM_KADEMELERI,
    KADEMELER,
    YON_ALANLARI,
    KalibreTahminci,
    _bant_adi,
    _mac_ozellikleri,
    _softmax,
    _tasarim_satiri,
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
    assert all(a >= b - 1e-9 for a, b in itertools.pairwise(sirali)), "egitim-ici artmis"
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


# ─── etkileşim basamakları (Faz 2.1) ──────────────────────────────────────

def test_etkilesim_kademeleri_kademe_listesinde():
    for ad in ETKILESIM_KADEMELERI:
        assert ad in KADEMELER
    # Sıra kasıtlı: etkileşim EN SONDA, çünkü bir öncekinin üstüne biniyor.
    assert KADEMELER[-2:] == ETKILESIM_KADEMELERI


def test_etkilesim_sutun_sayisi_ikili_carpim_kadar():
    """`etkilesim` C(6,2)=15, `etkilesim_favori` +6 sütun eklemeli."""
    ozellik = {
        "probs": {"1": 0.5, "0": 0.3, "2": 0.2},
        "lig": "E0", "favori": "1", "bant": "<1.50",
        "hareket": {"1": 0.0, "0": 0.0, "2": 0.0}, "ayrisma": 0.0,
        **{alan: 1.0 for alan, _ in YON_ALANLARI},
    }
    ligler, bantlar = ["E0"], ["<1.50"]
    # Taban `elo`dur, `sezon_sonu` degil: `etkilesim` Elo sutununu da
    # tasir ve yanlis taban secilirse fark bir fazla cikar.
    taban = _tasarim_satiri(ozellik, "elo", ligler, bantlar).shape[1]
    e1 = _tasarim_satiri(ozellik, "etkilesim", ligler, bantlar).shape[1]
    e2 = _tasarim_satiri(ozellik, "etkilesim_favori", ligler, bantlar).shape[1]

    n = len(YON_ALANLARI)
    assert e1 - taban == n * (n - 1) // 2
    assert e2 - e1 == n
    assert not np.isnan(_tasarim_satiri(ozellik, "etkilesim_favori",
                                        ligler, bantlar)).any()


def test_etkilesim_sutunu_yon_ozelligi_gibi_davranir():
    """Çarpım simetrik kaymalı: "1" yukarı, "2" aşağı, beraberlik sabit.

    Yön büyüklüğü olduğu için beraberliğe dokunmamalı — beraberlik ayrı bir
    sorudur ve `beraberlik.py`de kendi modeli var.
    """
    ozellik = {
        "probs": {"1": 0.5, "0": 0.3, "2": 0.2},
        "lig": "E0", "favori": "1", "bant": "<1.50",
        "hareket": {"1": 0.0, "0": 0.0, "2": 0.0}, "ayrisma": 0.0,
        **{alan: 2.0 for alan, _ in YON_ALANLARI},
    }
    X = _tasarim_satiri(ozellik, "etkilesim", ["E0"], ["<1.50"])
    taban = _tasarim_satiri(ozellik, "elo", ["E0"], ["<1.50"]).shape[1]
    for sutun in range(taban, X.shape[1]):
        ev, ber, dep = X[0, sutun], X[1, sutun], X[2, sutun]
        assert ber == 0.0
        assert ev == pytest.approx(-dep)


def test_etkilesim_olcekleri_tanimsal_ve_pozitif():
    """Ölçekler veriden değil tanımdan gelir; sıfır ya da negatif olamaz."""
    # Sayi degil YAPI sabitlenir: yeni bir yon ozelligi eklemek serbest,
    # olceksiz eklemek degil.
    assert len(YON_ALANLARI) >= 6
    assert len({alan for alan, _ in YON_ALANLARI}) == len(YON_ALANLARI)
    for _, olcek in YON_ALANLARI:
        assert olcek > 0


def test_kupon_haftasinda_etkilesim_notr():
    """Kupon haftaları yön özelliği taşımaz — çarpımlar da sıfır olmalı.

    Kupon haftaları form ve A3 taşımaz (`_mac_ozellikleri` nötr 0 yazar);
    etkileşim sütunları orada hiçbir şey yapmamalı, yoksa kademenin kupon
    üzerindeki davranışı sessizce değişir.
    """
    kupon = _girdi(1, "1" * MATCH_COUNT)
    for satir in _mac_ozellikleri(kupon):
        for alan, _ in YON_ALANLARI:
            assert satir[alan] == 0.0

    ozellik = _mac_ozellikleri(kupon)[0]
    taban = _tasarim_satiri(ozellik, "elo", ["E0"], ["<1.50"])
    genis = _tasarim_satiri(ozellik, "etkilesim_favori", ["E0"], ["<1.50"])
    # Yeni sutunlarin TAMAMI sifir olmali.
    assert (genis[:, taban.shape[1]:] == 0.0).all()


@pytest.mark.parametrize("kademe", ["etkilesim", "etkilesim_favori"])
def test_etkilesim_sutunu_gercekten_calisiyor(kademe):
    """**Yokluk iddiasının bekçisi.**

    "Etkileşim bir şey eklemiyor" ancak sütunlar gerçekten bağlıysa bir
    ölçümdür. Katsayı elle değiştirilince tahmin değişmeli; değişmiyorsa
    sütun ölüdür ve §3.26'yı kapatan cümle bağlanmamış koddan gelir.
    """
    h = korpus_haftalari(sezonlar_=["2425"])
    # SON sutun her iki kademede de `sezon_sonu_pay_farki`yi tasiyor
    # (`etkilesim`de ic_dis ile carpim, `etkilesim_favori`de aciklikla).
    # Rastgele bir hafta secmek yetmez: sezon sonu payi sezonun son %20'si
    # disinda sifirdir ve o haftalarda sutun HAKLI OLARAK olu gorunur.
    hafta = next(
        x for x in h
        if any(abs(o.get("sezon_sonu_pay_farki") or 0.0) > 0.05
               and abs(o.get("ic_dis_form_farki") or 0.0) > 0.05
               for o in x["ozellikler"])
    )
    t = KalibreTahminci(kademe)
    t.egit(h)
    once = t.tahmin(hafta)
    t._theta[-1] += 50.0
    sonra = t.tahmin(hafta)
    assert once != sonra, f"{kademe} son sutunu tahmini hic etkilemiyor — olu sutun"


def test_kademe_tam_bir_sutun_ekler():
    """**Yapısal bekçi.** Her basamak bir öncekine TAM OLARAK bir sütun eklemeli.

    Kademenin bütün anlamı budur: fark tek bir özelliğe atfedilebilsin diye
    her basamak yalnızca bir sütun ekler. Bozulduğunda ölçüm sessizce
    yanlış olur — bir basamak komşusunun sütununu da taşırsa iki özelliğin
    katkısı birbirine karışır.

    Bu test gerçek bir hatadan doğdu: A3 döngüsündeki `break` fonksiyondan
    çıkmadığı için `elo` sütunu `dinlenme`den itibaren bütün alt
    basamaklara sızmıştı ve `kalibre_elo` ile `kalibre_sezon_sonu` birebir
    aynı sayıyı veriyordu.

    Etkileşim basamakları istisnadır ve **bilerek** birden çok sütun ekler
    (çarpım kümesi bir bütündür); onlar için yalnızca artışın pozitif
    olması denetlenir.
    """
    from spor_toto.recalibrate import YON_ALANLARI

    ozellik = {
        "probs": {"1": 0.5, "0": 0.3, "2": 0.2},
        "lig": "E0", "favori": "1", "bant": "<1.50",
        "hareket": {"1": 0.1, "0": 0.0, "2": -0.1}, "ayrisma": 0.2,
        **{alan: 1.0 for alan, _ in YON_ALANLARI},
    }
    ligler, bantlar = ["E0", "diger"], ["<1.50", "diger"]

    def genislik(kademe: str) -> int:
        return _tasarim_satiri(ozellik, kademe, ligler, bantlar).shape[1]

    n = len(YON_ALANLARI)
    beklenen_artis = {
        "bias": len(SYMBOLS) - 1,          # sinif sabitleri, "1" referans
        "lig": len(ligler),
        "bant": len(bantlar),
        "form": 2,                          # puan + isabet
        "etkilesim": n * (n - 1) // 2,
        "etkilesim_favori": n,
    }
    for onceki, simdiki in itertools.pairwise(KADEMELER):
        artis = genislik(simdiki) - genislik(onceki)
        assert artis == beklenen_artis.get(simdiki, 1), (
            f"{onceki} -> {simdiki}: {artis} sutun eklendi, "
            f"{beklenen_artis.get(simdiki, 1)} bekleniyordu")


def test_elo_sutunu_alt_basamaklara_sizmaz():
    """`elo`nun ALTINDAKI hiçbir basamak Elo farkını okumamalı.

    Gerileme testi: sızıntı olduğunda `sezon_sonu` ile `elo` birebir aynı
    tahmini verir ve "Elo bir şey eklemiyor" cümlesi bağlanmamış koddan
    gelir.
    """
    from spor_toto.recalibrate import ELO_KADEMELERI, YON_ALANLARI

    ligler, bantlar = ["E0", "diger"], ["<1.50", "diger"]
    taban = {
        "probs": {"1": 0.5, "0": 0.3, "2": 0.2},
        "lig": "E0", "favori": "1", "bant": "<1.50",
        "hareket": {"1": 0.0, "0": 0.0, "2": 0.0}, "ayrisma": 0.0,
        **{alan: 0.0 for alan, _ in YON_ALANLARI},
    }
    elolu = {**taban, "elo_farki": 300.0}

    for kademe in KADEMELER:
        a = _tasarim_satiri(taban, kademe, ligler, bantlar)
        b = _tasarim_satiri(elolu, kademe, ligler, bantlar)
        ayni = np.array_equal(a, b)
        if kademe in ELO_KADEMELERI:
            assert not ayni, f"{kademe} Elo'yu okumali ama okumuyor"
        else:
            assert ayni, f"{kademe} Elo'yu okumamali ama okuyor — sizinti"
