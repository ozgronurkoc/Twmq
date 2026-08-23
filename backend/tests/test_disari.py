"""Piyasa dışı türetilebilir özellikler (A3) — Faz A'nın son ölçümü.

A3 dört özellik deniyor ve dördü de "geçmedi" diyor. Bu, Faz A'yı kapatan
cümlenin son parçası — dolayısıyla yanlış olmasının bedeli en yüksek olan
ölçüm. Üç ayrı yerden yanlış olabilir:

    sızıntı      özellik geleceği görürse skor iyileşir, bulgu ters döner
    ölü sütun    özellik bağlanmamışsa "katkısı yok" ölçüm değil, hata olur
    boş kapsama  özellik çoğu maçta tanımsızsa sıfır çıkması örneklemin olur

Üçü de burada bekçiye bağlı. Sızıntı testleri en kritiği: dinlenme,
sıkışıklık, iç/dış form ve lig sıralaması **hepsi** zaman içinde birikir ve
hepsi aynı hatayı yapabilir — maçın kendisini kendi geçmişine katmak.
"""

import pytest

from spor_toto.disari import (
    AVRUPA_LIGLERI,
    TURETILEMEYEN,
    artik_taramasi,
    kapsama,
    kesit,
    kor_nokta_taramasi,
)
from spor_toto.egitim import (
    DINLENME_TAVANI,
    SEZON_SONU_ORANI,
    _takvim_tablosu,
    korpus_haftalari,
)
from spor_toto.recalibrate import A3_ALANLARI


@pytest.fixture(scope="module")
def a3():
    h = kesit()
    if not h:
        pytest.skip("egitim korpusu yok — once scripts/build_egitim.py")
    return h


def _mac(tarih, ev, dep, kod, lig="XX", sezon="9999"):
    return {"sezon": sezon, "lig": lig, "tarih": tarih, "iso_yil": 2099,
            "iso_hafta": 1, "ev": ev, "dep": dep, "kod": kod,
            "oranlar": {"1": 2.0, "0": 3.0, "2": 4.0},
            "ev_isabet": 5, "dep_isabet": 5, "ev_sut": 5, "dep_sut": 5}


# ─── sızıntı bekçileri — A3'ün en kritik testleri ─────────────────────────────

def test_dinlenme_gelecegi_gormez():
    """Bir maçın dinlenme günü **kendi tarihinden önceki** maçtan hesaplanmalı.

    A takımı 1 ve 10 Ocak'ta oynuyor. 10 Ocak maçında dinlenme 9 gün olmalı;
    ilk maçta ise `dinlenme_var=False` — öncesi yok, uydurulmaz.
    """
    maclar = [_mac("2099-01-01", "A", "B", "1"),
              _mac("2099-01-10", "A", "C", "1")]
    t = _takvim_tablosu(maclar)
    assert t[0]["dinlenme_var"] is False
    assert t[0]["dinlenme_farki"] == 0.0
    # Ikinci macta A 9 gun dinlenmis, C hic oynamamis → cift tam degil
    assert t[1]["dinlenme_var"] is False


def test_dinlenme_farki_dogru_isaretli():
    """Ev takımı daha çok dinlenmişse fark **pozitif** (bütün A3 özellikleri
    "pozitif = ev lehine" okunur)."""
    maclar = [
        _mac("2099-01-01", "A", "X", "1"),      # A'nin onceki maci
        _mac("2099-01-08", "B", "Y", "1"),      # B'nin onceki maci (daha yakin)
        _mac("2099-01-10", "A", "B", "1"),      # A: 9 gun · B: 2 gun
    ]
    t = _takvim_tablosu(maclar)
    assert t[2]["dinlenme_var"] is True
    assert t[2]["dinlenme_farki"] == pytest.approx(7.0)


def test_dinlenme_tavani_uygulanir():
    """Sezon başı maçları (önceki maç aylar önce) modele devasa değer sokmamalı."""
    maclar = [_mac("2099-01-01", "A", "X", "1"), _mac("2099-01-02", "B", "Y", "1"),
              _mac("2099-06-01", "A", "B", "1")]
    t = _takvim_tablosu(maclar)
    assert abs(t[2]["dinlenme_farki"]) <= DINLENME_TAVANI


def test_sikisiklik_kendi_macini_saymaz():
    """**Sızıntı bekçisi**: maçın kendisi kendi 14 günlük penceresine girmemeli."""
    maclar = [_mac("2099-01-10", "A", "B", "1")]
    t = _takvim_tablosu(maclar)
    assert t[0]["sikisiklik_farki"] == 0.0


def test_sikisiklik_onceki_maclari_sayar():
    """Deplasmanın sıkışıklığı ev lehinedir → işaret pozitif."""
    maclar = [_mac("2099-01-02", "B", "P", "1"),
              _mac("2099-01-05", "B", "Q", "1"),
              _mac("2099-01-10", "A", "B", "1")]
    t = _takvim_tablosu(maclar)
    # B son 14 gunde 2 mac oynamis, A hic → dep daha sikisik → ev lehine
    assert t[2]["sikisiklik_farki"] == pytest.approx(2.0)


def test_ic_dis_form_yalnizca_kendi_sahasini_okur():
    """Ev takımının **iç saha**, deplasmanın **dış saha** formu.

    T5'in birleşik formundan farkı budur; karışırsa özellik zaten var olanın
    kopyası olur ve "yeni bir şey eklemiyor" bulgusu tautoloji haline gelir.
    """
    maclar = []
    for i in range(1, 4):                      # A ic sahada 3 galibiyet
        maclar.append(_mac(f"2099-01-0{i}", "A", f"R{i}", "1"))
    for i in range(4, 7):                      # A DIS sahada 3 maglubiyet
        maclar.append(_mac(f"2099-01-0{i}", f"S{i}", "A", "1"))
    for i in range(1, 4):                      # B dis sahada 3 maglubiyet
        maclar.append(_mac(f"2099-02-0{i}", f"T{i}", "B", "1"))
    maclar.append(_mac("2099-03-01", "A", "B", "1"))

    t = _takvim_tablosu(maclar)
    son = t[-1]
    assert son["ic_dis_form_var"] is True
    # A'nin IC formu 3,0 (3 galibiyet) · B'nin DIS formu 0,0 (3 maglubiyet)
    assert son["ic_dis_form_farki"] == pytest.approx(3.0)


def test_sezon_sonu_bayragi_son_dilimde_acilir():
    """Sezonun son %20'si işaretlenir; öncesi işaretlenmez."""
    maclar = [_mac(f"2099-01-{i:02d}", f"E{i}", f"D{i}", "1", lig="ZZ")
              for i in range(1, 11)]
    t = _takvim_tablosu(maclar)
    isaretli = [x["sezon_sonu"] for x in t]
    assert isaretli[0] is False
    assert isaretli[-1] is True
    assert sum(isaretli) == pytest.approx(len(maclar) * SEZON_SONU_ORANI, abs=1)


def test_sezon_sonu_payi_sezon_disinda_sifir():
    """Sezon sonu değilse pay taşınmaz — özellik yalnızca o pencerede konuşur."""
    maclar = [_mac(f"2099-01-{i:02d}", f"E{i}", f"D{i}", "1", lig="ZZ")
              for i in range(1, 11)]
    t = _takvim_tablosu(maclar)
    for x in t:
        if not x["sezon_sonu"]:
            assert x["sezon_sonu_pay_farki"] == 0.0


def test_takvim_deterministik():
    maclar = [_mac(f"2099-01-{i:02d}", "A", f"R{i}", "1") for i in range(1, 9)]
    assert _takvim_tablosu(maclar) == _takvim_tablosu(list(maclar))


# ─── kademe basamakları gerçekten bağlı mı ────────────────────────────────────

@pytest.mark.parametrize("kademe,alan", list(A3_ALANLARI))
def test_a3_basamagi_tek_sutun_ekler(kademe, alan):
    from spor_toto.recalibrate import KADEMELER, KalibreTahminci
    h = korpus_haftalari(sezonlar_=["2425"])
    onceki = KADEMELER[KADEMELER.index(kademe) - 1]
    alt = KalibreTahminci(onceki)
    alt.egit(h)
    ust = KalibreTahminci(kademe)
    ust.egit(h)
    assert len(ust.katsayilar) == len(alt.katsayilar) + 1


@pytest.mark.parametrize("kademe,alan", list(A3_ALANLARI))
def test_a3_sutunu_gercekten_calisiyor(kademe, alan):
    """**Yokluk iddiasının bekçisi** — dört özellik için ayrı ayrı.

    "Bu özellik bir şey eklemiyor" ancak sütun gerçekten bağlıysa bir
    ölçümdür. Katsayı elle değiştirilince tahmin değişmeli; değişmiyorsa
    sütun ölüdür ve Faz A'yı kapatan cümle bağlanmamış koddan gelir.
    """
    from spor_toto.recalibrate import KalibreTahminci, _mac_ozellikleri

    h = korpus_haftalari(sezonlar_=["2425"])
    hafta = next(x for x in h
                 if any(abs(o.get(alan) or 0.0) > 0.5 for o in x["ozellikler"]))

    t = KalibreTahminci(kademe)
    t.egit(h)
    once = t.tahmin(hafta)
    t._theta[-1] += 10.0
    sonra = t.tahmin(hafta)
    assert once != sonra, f"{alan} sutunu tahmini hic etkilemiyor — olu sutun"

    for i, satir in enumerate(_mac_ozellikleri(hafta)):
        if satir[alan] == 0.0:
            assert once[i] == pytest.approx(sonra[i])


def test_kupon_haftasinda_a3_notr():
    """Kupon haftaları A3 özelliği taşımaz; nötr 0 = "bilgi yok"."""
    from spor_toto.evaluate import olculebilir_haftalar
    from spor_toto.recalibrate import _mac_ozellikleri
    for o in _mac_ozellikleri(olculebilir_haftalar()[0]):
        for _, alan in A3_ALANLARI:
            assert o[alan] == 0.0


# ─── kapsama — sıfır sonucu örneklemin değil ölçümün olmalı ───────────────────

def test_kapsama_yeterli(a3):
    """Özellik çoğu maçta tanımsız olsaydı, sıfır çıkması örneklemin olurdu."""
    k = kapsama(a3)
    assert k["dinlenme_var"] > 0.95
    assert k["ic_dis_form_var"] > 0.90
    # Sezon sonu tanimi geregi ~%20 olmali; sapiyorsa pencere hesabi bozuk.
    assert 0.15 < k["sezon_sonu"] < 0.25


# ─── türetilemeyenler ─────────────────────────────────────────────────────────

def test_turetilemeyenler_gerekceli_kayitli():
    """"Denenmedi" ile "denenemez" farklı şeyler; A4 bu ayrımı yazmak zorunda."""
    assert set(TURETILEMEYEN) == {"seyahat", "derbi"}
    for gerekce in TURETILEMEYEN.values():
        assert len(gerekce) > 30


def test_seyahat_gercekten_turetilemez():
    """Gerekçe iddia değil olgu: bir maçın iki takımı **her zaman aynı ligde**.

    Korpus lig başına ayrı dosyalardan kurulur ve `Div` tek değerdir; maç
    düzeyinde bir "lig/ülke değişimi" büyüklüğü yoktur.
    """
    from spor_toto.egitim import korpus_yukle
    satirlar = korpus_yukle()
    if not satirlar:
        pytest.skip("korpus yok")
    assert all("lig" in r for r in satirlar[:100])
    # Sehir/koordinat alani yok — derbi de bu yuzden turetilemiyor.
    assert not ({"sehir", "ev_sehir", "enlem", "boylam"} & set(satirlar[0]))


# ─── bulgu ────────────────────────────────────────────────────────────────────

def test_artik_taramasi_her_ozellik_icin_dilimlenebiliyor(a3):
    """Tarama cevapsız kalırsa "artık yok" diye okunamaz — eşikler buna göre.

    `sikisiklik_farki` eşiği tam bu yüzden 1,0'dan 0,5'e indirildi.
    """
    tarama = artik_taramasi(a3)
    for alan, blok in tarama.items():
        assert blok["dilimlenemedi"] is False, (
            f"{alan} taramasi dilimlenemedi — esik gozden gecirilmeli")


def test_ic_dis_form_ham_sinyali_guclu_artigi_kucuk(a3):
    """A3'ün en öğretici özelliği: **güçlü sinyal, sıfır katkı.**

    İç/dış form ham haliyle devasa bir fark taşıyor (ev galibiyeti oranında
    ~25 puan). Piyasa onu neredeyse tamamen fiyatlamış: artık, ham farkın
    onda birinden küçük. "Sinyal var" ile "fiyatlanmamış sinyal var"
    arasındaki farkı en açık gösteren ölçüm budur.
    """
    blok = artik_taramasi(a3)["ic_dis_form_farki"]
    assert blok["ham_fark"] > 0.15, "ic/dis form ham sinyali kaybolmus"
    assert blok["en_buyuk_artik"] < blok["ham_fark"] / 2


def test_kor_nokta_taramasi_katmanlari_ayirir(a3):
    """Kör nokta **iddia değil ölçüm** olarak kayıtlı.

    Denetlenen şey sayının kendisi değil — birkaç yüz maçlık tarama hücresi
    dar bir eşiğe bağlanamaz. Denetlenen şey taramanın **çalıştığı**: iki lig
    katmanı da dolu dönüyor ve karşılaştırılabilir.
    """
    kn = kor_nokta_taramasi(a3)
    for katman in ("avrupa_ligi", "diger_lig"):
        assert kn[katman]["dengeli"] is not None
        assert kn[katman]["dep_cok_dinlenmis"] is not None
    assert len(AVRUPA_LIGLERI) >= 8


def test_a3_ozelliklerinin_hicbiri_piyasayi_gecmiyor(a3):
    """**A3'ün bulgusu ve Faz A'yı kapatan cümlenin son parçası.**

    Dört özellik de kademeye eklendiğinde `kalibre_dagilim`ın üstüne kayda
    değer bir şey koymuyor. Bu test kırılırsa Faz A yeniden açılmış demektir
    ve yol haritasındaki A4(b) cümlesi geçersizdir.
    """
    from spor_toto.evaluate import bootstrap_farki, degerlendir, sezon_anahtari
    from spor_toto.recalibrate import KalibreTahminci

    taban = degerlendir(lambda: KalibreTahminci("dagilim"), a3, sezon_anahtari)
    tam = degerlendir(lambda: KalibreTahminci("sezon_sonu"), a3, sezon_anahtari)
    fark = bootstrap_farki(tam["_kayitlar"], taban["_kayitlar"])
    assert fark["ust"] >= 0, (
        f"A3 ozellikleri tabani gecti: {fark} — Faz A yeniden acilmis olabilir")
