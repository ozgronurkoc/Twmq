"""Kapanış çizgisi verimliliği (A1) — ölçümün ve dayanağının denetimi.

A1 iki cümle söyleyecek ve ikisi de yol haritasına yazılacak: *"kapanış
açılışı geçiyor"* ve *"hareket kapanışın ötesinde bilgi taşımıyor"*. İkinci
cümle bir **yokluk iddiasıdır** ve yokluk iddiaları sessizce yanlış olabilir:
özellik hiç bağlanmamışsa da, ölçüm kesiti bozuksa da aynı sonucu verirler.

Bu dosyanın işi o iki yanlışı ayırt etmektir. Üç grup test var:

    kesit      açılış ve kapanış AYNI maçlarda mı ölçülüyor
    özellik    hareket sütunu gerçekten bir şey yapıyor mu
    bulgu      gerçek veride ham sinyal var mı, sonuç hâlâ aynı mı

En kritik olanı `test_hareket_sutunu_gercekten_calisiyor`: hareket kademesi,
hareketin sıfır olmadığı bir maçta bir alt basamaktan **farklı** tahmin
üretmek zorundadır. Üretmiyorsa "hareket yardım etmiyor" bulgusu ölçümden
değil, bağlanmamış bir sütundan gelir.
"""

import importlib.util
import math
from pathlib import Path

import pytest

from spor_toto.cizgi import (
    HAREKET_BANTLARI,
    AcilisTahminci,
    hareket_katsayisi,
    hareket_ozeti,
    kesit,
)
from spor_toto.egitim import cizgi_hareketi, korpus_haftalari, korpus_yukle
from spor_toto.history import SYMBOLS
from spor_toto.predict import PiyasaTahminci


KOK = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_egitim", KOK / "scripts" / "build_egitim.py")
uretici = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uretici)


@pytest.fixture(scope="module")
def a1():
    h = kesit()
    if not h:
        pytest.skip("egitim korpusu yok — once scripts/build_egitim.py")
    return h


# ─── üretici: çiftin kaynağı ──────────────────────────────────────────────────

def _ham(**alanlar) -> dict:
    """football-data satırının ilgili sütunları."""
    return {k: str(v) for k, v in alanlar.items()}


def test_cift_ayni_bahisci_ailesinden_gelir():
    """**Kaynak karışırsa ölçülen şey hareket değil, kaynak farkı olur.**

    `Avg` bütün bahisçilerin ortalaması, `B365` tek bahisçi. Açılışı `Avg`den,
    kapanışı `B365C`den alsaydık aradaki fark piyasanın fikir değiştirmesini
    değil, iki farklı fiyatlayıcıyı ölçerdi.
    """
    satir = _ham(AvgH=2.0, AvgD=3.0, AvgA=4.0,          # acilis: Avg tam
                 B365CH=1.8, B365CD=3.5, B365CA=4.5)    # kapanis: yalnizca B365C
    cift = uretici.cizgi_cifti(satir)
    # Avg ailesinin kapanis ucu yok → aile duser; B365 ailesinin acilis ucu
    # yok → o da duser. Karisik cift URETILMEZ.
    assert cift is None


def test_cift_tam_aile_bulunca_kurulur():
    satir = _ham(AvgH=2.0, AvgD=3.0, AvgA=4.0,
                 AvgCH=1.8, AvgCD=3.2, AvgCA=4.6)
    cift = uretici.cizgi_cifti(satir)
    assert cift["acilis_kaynak"] == "Avg" and cift["kapanis_kaynak"] == "AvgC"
    assert cift["acilis"]["1"] == 2.0 and cift["kapanis"]["1"] == 1.8


def test_askiya_alinmis_ayak_kaynagi_dusurur():
    """1.00 oran askıya alınmış ayaktır; uydurulmaz, kaynak atlanır."""
    satir = _ham(AvgH=1.0, AvgD=3.0, AvgA=4.0, AvgCH=1.8, AvgCD=3.2, AvgCA=4.6,
                 B365H=2.1, B365D=3.1, B365A=3.9,
                 B365CH=1.9, B365CD=3.3, B365CA=4.2)
    cift = uretici.cizgi_cifti(satir)
    assert cift["acilis_kaynak"] == "B365"


def test_uretici_yarim_cifti_reddeder():
    """`dogrula` yazmadan önce yarım çifti yakalar — dosya hiç yazılmaz."""
    temel = {"kod": "1", "oran_1": 2.0, "oran_0": 3.0, "oran_2": 4.0,
             "ev": "A", "dep": "B", "sezon": "2425", "lig": "XX",
             "tarih": "2025-01-01",
             "acilis_1": 2.1, "acilis_0": 3.1, "acilis_2": 4.1,
             "kapanis_1": "", "kapanis_0": "", "kapanis_2": ""}
    hatalar = uretici.dogrula([temel])
    assert any("yarim" in h for h in hatalar)

    temel.update(kapanis_1=1.9, kapanis_0=3.2, kapanis_2=4.3)
    assert uretici.dogrula([temel]) == []


# ─── hareketin tanımı ─────────────────────────────────────────────────────────

def test_hareket_cift_yoksa_sifir():
    """Doktrin 2: eksik çift uydurulmaz, nötr sıfıra düşer."""
    for a, k in (({}, {}), ({"1": 2.0, "0": 3.0, "2": 4.0}, None), (None, None)):
        assert cizgi_hareketi(a, k) == {"1": 0.0, "0": 0.0, "2": 0.0}


def test_hareket_yonu_dogru():
    """Çizgi "1"e doğru oynarsa `hareket_1` pozitif, karşıtı negatif olmalı."""
    acilis = {"1": 3.00, "0": 3.40, "2": 2.50}
    kapanis = {"1": 2.00, "0": 3.40, "2": 4.00}   # "1" ucuzladi = olasiligi artti
    h = cizgi_hareketi(acilis, kapanis)
    assert h["1"] > 0
    assert h["2"] < 0


def test_hareket_saf_marj_degisimini_gormez():
    """**Marj arındırmanın varlık sebebi.**

    Bahisçi bütün ayakları aynı oranda kısarsa fikri değişmemiş, yalnızca
    marjı büyümüştür. Ham oran üzerinden ölçseydik bu bir "hareket" gibi
    görünür ve A1 kendi kaynağının fiyatlama politikasını ölçerdi.
    """
    acilis = {"1": 2.00, "0": 3.60, "2": 4.50}
    kapanis = {s: v * 0.90 for s, v in acilis.items()}   # marj buyudu, fikir ayni
    h = cizgi_hareketi(acilis, kapanis)
    for s in SYMBOLS:
        assert h[s] == pytest.approx(0.0, abs=1e-12)


def test_hareket_olcegi_simetrik():
    """Logaritma seçiminin sebebi: iki katına çıkmak her seviyede aynı sayı."""
    az = cizgi_hareketi({"1": 20.0, "0": 1.5, "2": 20.0},
                        {"1": 10.0, "0": 1.5, "2": 20.0})
    cok = cizgi_hareketi({"1": 4.0, "0": 4.0, "2": 2.0},
                         {"1": 2.0, "0": 4.0, "2": 2.0})
    # Ikisinde de "1"in ham orani yariya inmis; log olcegi ikisini de
    # ln 2'ye YAKIN gosterir (marj yeniden dagildigi icin tam esit degil).
    assert az["1"] > 0.5 * math.log(2)
    assert cok["1"] > 0.5 * math.log(2)


# ─── kesit ────────────────────────────────────────────────────────────────────

def test_kesit_yalnizca_ciftli_maclari_alir(a1):
    """Açılış ve kapanış **aynı maçlarda** ölçülmezse fark örneklem farkıdır."""
    for hafta in a1:
        for o in hafta["ozellikler"]:
            assert o["cizgi_var"] is True
            assert o["acilis_probs"] and o["kapanis_probs"]


def test_kesit_probs_alani_kapanis(a1):
    """`probs` açıkça kapanışla doldurulur — `oran_*` tercihine yaslanmaz."""
    for hafta in a1[:20]:
        for i, o in enumerate(hafta["ozellikler"]):
            assert hafta["probs"][i] == o["kapanis_probs"]


def test_kesit_korpusun_neredeyse_tamami(a1):
    """Kesit korpusun küçük bir alt kümesi olsaydı seçimin kendisi sinyal olurdu."""
    tum = korpus_haftalari()
    kesit_mac = sum(len(h["results"]) for h in a1)
    tum_mac = sum(len(h["results"]) for h in tum)
    assert kesit_mac / tum_mac > 0.99


def test_korpusta_yarim_cift_yok():
    """Üretici ile okuyucu birlikte bozulursa yarım çift korpusa sızabilir.

    Sızarsa hareket o maçta sıfır görünür, maç A1 kesitine girer ve ölçümü
    sessizce seyreltir — hiçbir şey kırmızı yanmadan.
    """
    satirlar = korpus_yukle()
    if not satirlar:
        pytest.skip("korpus yok")
    yarim = [r for r in satirlar if bool(r.get("acilis")) != bool(r.get("kapanis"))]
    assert not yarim, f"yarim cizgi cifti: {len(yarim)} mac"


def test_korpusta_cizgi_gercekten_oynuyor():
    """**A1'in en sinsi bozulma senaryosunun bekçisi.**

    Üretici bir gün iki ucu da aynı sütundan doldurursa (kaynak tercihi
    hatası) açılış == kapanış olur. O zaman hareket her maçta sıfır çıkar,
    A1 raporu sapasağlam görünür ve *"hareket bilgi taşımıyor"* sonucu
    ölçümden değil **hatadan** gelir. Aynı çizgi iki kez yazılmış bir
    korpusta bunu başka hiçbir test yakalamaz.

    Bu denetimin sağlık katmanında değil burada olması bir ürün kararıdır:
    korpus yalnızca tahmin katmanına aittir ve `/api/health` ondan hiçbir
    sayı okumaz (bkz. `test_egitim.py::test_ayrim_*`). Korpus çalışma anında
    kaymaz — git'e işlenmiş bir dosyadır — dolayısıyla bozulma ancak bir kod
    değişikliğiyle gelir ve orayı bekleyecek yer test paketidir.
    """
    satirlar = [r for r in korpus_yukle() if r.get("acilis") and r.get("kapanis")]
    if not satirlar:
        pytest.skip("korpus yok")
    oynayan = sum(1 for r in satirlar
                  if sum(abs(v) for v in
                         cizgi_hareketi(r["acilis"], r["kapanis"]).values()) > 1e-9)
    assert oynayan / len(satirlar) > 0.5, (
        "maclarin cogunda cizgi hic oynamamis — acilis ve kapanis ayni "
        "sutundan doldurulmus olabilir")


def test_yarim_cift_okunmaz(tmp_path):
    """Yarım çift sessiz bir yalandır: hareket sıfır görünür, kesite girer."""
    yol = tmp_path / "k.csv"
    yol.write_text(
        "sezon,lig,tarih,iso_yil,iso_hafta,ev,dep,kod,"
        "oran_1,oran_0,oran_2,acilis_1,acilis_0,acilis_2,"
        "kapanis_1,kapanis_0,kapanis_2\n"
        "2425,XX,2025-01-01,2025,1,A,B,1,2.0,3.0,4.0,2.1,3.1,4.1,,,\n",
        encoding="utf-8")
    satir = korpus_yukle(str(yol))[0]
    assert satir["acilis"] is None and satir["kapanis"] is None


# ─── açılış tahmincisi ────────────────────────────────────────────────────────

def test_acilis_tahmincisi_acilisi_okur(a1):
    """`piyasa`nın ikizi ama çizginin **öbür ucunu** okur."""
    hafta = a1[0]
    acilis = AcilisTahminci().tahmin(hafta)
    kapanis = PiyasaTahminci().tahmin(hafta)
    assert len(acilis) == len(hafta["results"])
    for i, o in enumerate(hafta["ozellikler"]):
        assert acilis[i] == o["acilis_probs"]
    assert acilis != kapanis, "acilis ve kapanis ayni cikti — cizgi hic oynamamis?"


def test_acilis_kupon_haftasinda_duzgune_duser():
    """Kupon haftaları açılış taşımaz; uydurma değer yerine bilgisizlik.

    Bu yüzden `AcilisTahminci` referans listesine girmez — A1 kesitinin
    dışında anlamı yoktur.
    """
    from spor_toto.evaluate import olculebilir_haftalar
    kupon = olculebilir_haftalar()[0]
    for blok in AcilisTahminci().tahmin(kupon):
        assert blok == pytest.approx({s: 1 / 3 for s in SYMBOLS})


# ─── hareket sütunu gerçekten bağlı mı ────────────────────────────────────────

def test_hareket_kademesi_form_ustune_tek_sutun_ekler():
    from spor_toto.recalibrate import KalibreTahminci
    h = korpus_haftalari(sezonlar_=["2425"], cizgi_gerekli=True)
    form = KalibreTahminci("form"); form.egit(h)
    hareket = KalibreTahminci("hareket"); hareket.egit(h)
    assert len(hareket.katsayilar) == len(form.katsayilar) + 1


def test_hareket_sutunu_gercekten_calisiyor():
    """**Yokluk iddiasının bekçisi.**

    A1'in ikinci bulgusu "hareket bir şey eklemiyor". Bu cümle ancak sütun
    gerçekten bağlıysa bir ölçümdür. Burada katsayı elle sıfırdan farklı
    yapılır ve tahminin **değişmesi** beklenir; değişmiyorsa sütun ölü
    demektir ve bulgu ölçümden değil bağlanmamış bir koddan gelir.
    """
    from spor_toto.recalibrate import KalibreTahminci, _mac_ozellikleri

    h = korpus_haftalari(sezonlar_=["2425"], cizgi_gerekli=True)
    hafta = next(x for x in h
                 if any(abs(o["hareket_1"]) > 0.1 for o in x["ozellikler"]))

    t = KalibreTahminci("hareket"); t.egit(h)
    once = t.tahmin(hafta)
    t._theta[-1] += 5.0          # hareket katsayisi
    sonra = t.tahmin(hafta)
    assert once != sonra, "hareket sutunu tahmini hic etkilemiyor — olu sutun"

    # ...ve etkilenen sey dogru maclar: hareketi sifir olan mac degismemeli.
    satirlar = _mac_ozellikleri(hafta)
    for i, satir in enumerate(satirlar):
        if all(abs(v) < 1e-12 for v in satir["hareket"].values()):
            assert once[i] == pytest.approx(sonra[i])


def test_kupon_haftasinda_hareket_notr():
    """Kupon haftaları hareket taşımaz; nötr 0 = "bilgi yok"."""
    from spor_toto.evaluate import olculebilir_haftalar
    from spor_toto.recalibrate import _mac_ozellikleri
    for o in _mac_ozellikleri(olculebilir_haftalar()[0]):
        assert o["hareket"] == {s: 0.0 for s in SYMBOLS}


# ─── bulgular ─────────────────────────────────────────────────────────────────

def test_ham_sinyal_gercek_hareketin_yonu_tutuyor(a1):
    """**Sağlama, bulgu değil** — T5'teki ham form sağlamasıyla aynı gerekçe.

    "Hareket kapanışın ötesinde bilgi taşımıyor" sonucu, hareketin hiç bilgi
    taşımamasından da gelebilirdi. Gelmediğini burada gösteriyoruz: çizginin
    lehine oynadığı sembol, aleyhine oynadığından belirgin biçimde daha sık
    tutar — ve fark hareket büyüdükçe **büyür.**
    """
    ozet = hareket_ozeti(a1)
    yon = ozet["yon"]
    assert yon["lehine_tuttu"] > yon["aleyhine_tuttu"] + 0.04

    bantlar = ozet["bantlar"]
    kucuk = bantlar[f"<{HAREKET_BANTLARI[0]:.2f}"]
    buyuk = bantlar[f">={HAREKET_BANTLARI[-1]:.2f}"]
    assert kucuk["n"] > 500 and buyuk["n"] > 500
    # Kucuk harekette yon bilgi tasimaz, buyukte tasir.
    assert abs(kucuk["lehine_tuttu"] - kucuk["aleyhine_tuttu"]) < 0.05
    assert buyuk["lehine_tuttu"] > buyuk["aleyhine_tuttu"] + 0.10


def test_kapanis_acilisi_geciyor(a1):
    """**A1'in birinci bulgusu**: piyasa maç öncesinde bilgi soğuruyor.

    Aynı kesitte, aynı maçlarda, kapanış çizgisinin Brier'i açılışınkinden
    düşük olmalı. Bu, piyasanın *çalıştığının* doğrudan kanıtıdır ve bozulursa
    bozulan model değil oran arşividir.
    """
    from spor_toto.evaluate import degerlendir

    acilis = degerlendir(AcilisTahminci, a1)
    kapanis = degerlendir(PiyasaTahminci, a1)
    assert kapanis["brier"] < acilis["brier"]
    assert kapanis["log_kaybi"] < acilis["log_kaybi"]


def test_hareket_kapanisin_otesine_uzatilmiyor(a1):
    """**A1'in ikinci bulgusu**: kapanış son sözdür.

    Katsayı okuması Brier farkının veremediğini verir: model harekete baktı
    (sütun bağlı, bkz. `test_hareket_sutunu_gercekten_calisiyor`) ve kapanışın
    ötesine uzatmak için kayda değer bir sebep bulamadı.

    Eşik %10 — dar değil, çünkü denetlenen şey *kesin bir sayı* değil, bir
    **büyüklük mertebesi**: uzatma sıfır civarındaysa kapanış verimlidir.
    """
    k = hareket_katsayisi(a1)
    assert k["beta"] > 0.5, "sicaklik katsayisi anlamsiz — model bozuk"
    assert abs(k["uzatma"]) < 0.10, (
        f"hareket kapanisin otesine %{100 * k['uzatma']:.1f} uzatiliyor — "
        "A1 bulgusu degismis olabilir")
