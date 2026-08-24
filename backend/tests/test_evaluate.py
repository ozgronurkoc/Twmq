"""Değerlendirme koşumunun denetimi.

Koşumun işi bir tahmincinin piyasayı geçip geçmediğini söylemek. Bu yüzden
testlerin çoğu "sayı doğru mu"dan çok **kural doğru mu** sorusunu kovalıyor:

- sızıntı yok mu (`test_sezon_sabiti_sizdirmaz`)
- kural ateşleyebiliyor mu (`test_gercekten_iyi_aday_gecer`)
- kural yanlış ateşlemiyor mu (`test_esit_aday_gecmez`)

Bir kuralın yalnızca `False` döndüğünü kanıtlayan test takımı boştur; bu yüzden
hem geçen hem geçmeyen aday ayrıca sınanır.
"""

import math

import pytest

from spor_toto.evaluate import (
    AZ_HAFTA,
    BOOTSTRAP_TOHUM,
    EGRI_KESIRLERI,
    bootstrap_farki,
    brier,
    degerlendir,
    hafta_disarida_birak,
    karsilastir,
    log_kaybi,
    ogrenme_egrisi,
    olculebilir_haftalar,
)
from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.ortak import BRIER_ESIT
from spor_toto.predict import (
    DuzgunTahminci,
    PiyasaTahminci,
    SezonSabitiTahminci,
    Tahminci,
)

ESIT = dict.fromkeys(SYMBOLS, 1 / 3)


def _girdi(week: int, results: str, probs=None) -> dict:
    return {
        "week": week, "close_date": "2026-01-01", "results": results,
        "probs": list(probs) if probs else [dict(ESIT)] * MATCH_COUNT,
        "missing": 0, "usable": True,
    }


class KahinTahminci(Tahminci):
    """Sonucu bilen sahte tahminci — yalnızca kuralın ateşlenebildiğini kanıtlar."""

    ad = "kahin"
    aciklama = "test kurgusu: gerçek sonuca 0,9 verir"

    def tahmin(self, hafta):
        out = []
        for kod in hafta["results"]:
            p = dict.fromkeys(SYMBOLS, 0.05)
            p[kod] = 0.90
            out.append(p)
        return out


# ─── tek maç ölçütleri ────────────────────────────────────────────────────────

def test_brier_bilinen_degerler():
    assert brier({"1": 1.0, "0": 0.0, "2": 0.0}, "1") == pytest.approx(0.0)
    assert brier({"1": 0.0, "0": 0.0, "2": 1.0}, "1") == pytest.approx(2.0)
    assert brier(ESIT, "1") == pytest.approx(BRIER_ESIT, abs=1e-4)


def test_brier_esit_dagitim_sabiti_odds_ile_ayni():
    """Zemin iki modülde iki farklı sayı olmamalı."""
    assert brier(ESIT, "0") == pytest.approx(BRIER_ESIT, abs=1e-4)


def test_log_kaybi_bilinen_degerler():
    assert log_kaybi(ESIT, "1") == pytest.approx(math.log(3))
    assert log_kaybi({"1": 1.0, "0": 0.0, "2": 0.0}, "1") == pytest.approx(0.0)


def test_log_kaybi_sifir_olasilikta_sonlu_kalir():
    """'İmkânsız' deyip yanılmak ağır cezalanır ama ortalamayı yutmaz."""
    ceza = log_kaybi({"1": 0.0, "0": 0.5, "2": 0.5}, "1")
    assert math.isfinite(ceza)
    assert ceza > 30


# ─── hafta dışarıda bırakmalı koşum ───────────────────────────────────────────

def test_sezon_sabiti_sizdirmaz():
    """Sızıntı testi — koşumun varlık sebebi.

    İki hafta: biri tamamen '1', diğeri tamamen '0'. Hafta dışarıda
    bırakıldığında tahminci yalnızca ötekini görür, yani '1' haftasına
    p(1)=0 der ve Brier 2,0 (tam ters) çıkar. Sızıntı olsaydı kendi
    sonucunu da görür, 0,5/0,5 der ve skor belirgin biçimde düşerdi.
    """
    haftalar = [_girdi(1, "1" * MATCH_COUNT), _girdi(2, "0" * MATCH_COUNT)]
    kayitlar = hafta_disarida_birak(SezonSabitiTahminci, haftalar)
    assert [k["brier"] for k in kayitlar] == [pytest.approx(2.0), pytest.approx(2.0)]


def test_duzgun_tam_olarak_zemini_verir():
    haftalar = [_girdi(i, "102" * 5) for i in range(1, 6)]
    sonuc = degerlendir(DuzgunTahminci, haftalar)
    assert sonuc["brier"] == pytest.approx(BRIER_ESIT, abs=1e-4)
    assert sonuc["log_kaybi"] == pytest.approx(math.log(3), abs=1e-4)
    assert sonuc["n_hafta"] == 5
    assert sonuc["n_mac"] == 5 * MATCH_COUNT


def test_koşum_eksik_tahmini_yakalar():
    class Eksik(Tahminci):
        ad = "eksik"

        def tahmin(self, hafta):
            return [dict(ESIT)]

    with pytest.raises(ValueError, match="tahmin geldi"):
        hafta_disarida_birak(Eksik, [_girdi(1, "1" * MATCH_COUNT)])


def test_hafta_kayitlari_sira_korur():
    haftalar = [_girdi(i, "102" * 5) for i in (7, 3, 9)]
    kayitlar = hafta_disarida_birak(DuzgunTahminci, haftalar)
    assert [k["week"] for k in kayitlar] == [7, 3, 9]


# ─── bootstrap ────────────────────────────────────────────────────────────────

def _kayit(week: int, brier_ort: float, n: int = MATCH_COUNT) -> dict:
    return {"week": week, "n": n, "brier_toplam": brier_ort * n,
            "log_toplam": 0.0, "brier": brier_ort, "log_kaybi": 0.0}


def test_bootstrap_ayni_tohumla_ayni_sonuc():
    a = [_kayit(i, 0.50) for i in range(20)]
    b = [_kayit(i, 0.55) for i in range(20)]
    assert bootstrap_farki(a, b) == bootstrap_farki(a, b)


def test_bootstrap_tohumu_gercekten_kullanir():
    """Tohum gerçekten yeniden örneklemeyi sürüyor mu.

    Determinizmi `test_bootstrap_ayni_tohumla_ayni_sonuc` kanıtlıyor; buradaki
    soru tersi: aralık tohumdan bağımsız çıkıyorsa yeniden örnekleme hiç
    olmuyor demektir. Haftalar bilerek birbirinden çok farklı, çünkü tekdüze
    bir kesitte her yeniden örnekleme aynı ortalamaya yakınsar ve test
    kodu değil kurguyu ölçer.
    """
    a_deger = [0.30, 0.95, 0.42, 0.88, 0.35, 1.10, 0.28, 0.72,
               0.51, 0.99, 0.33, 0.81, 0.44, 1.05, 0.39, 0.66]
    b_deger = [0.62, 0.58, 0.71, 0.55, 0.90, 0.48, 0.83, 0.60,
               0.75, 0.52, 0.68, 0.57, 0.79, 0.61, 0.86, 0.54]
    a = [_kayit(i, v) for i, v in enumerate(a_deger)]
    b = [_kayit(i, v) for i, v in enumerate(b_deger)]

    ilk = bootstrap_farki(a, b, tohum=BOOTSTRAP_TOHUM)
    ikinci = bootstrap_farki(a, b, tohum=BOOTSTRAP_TOHUM + 1)
    assert ilk["fark"] == ikinci["fark"], "nokta tahmini tohumdan bagimsiz olmali"
    assert (ilk["alt"], ilk["ust"]) != (ikinci["alt"], ikinci["ust"])


def test_bootstrap_esit_uzunluk_ister():
    with pytest.raises(ValueError, match="ayni haftalarda"):
        bootstrap_farki([_kayit(1, 0.5)], [_kayit(1, 0.5), _kayit(2, 0.5)])


def test_bootstrap_bos_kesitte_cokmez():
    assert bootstrap_farki([], [])["fark"] is None


def test_bootstrap_ayni_skorda_aralik_sifiri_icerir():
    a = [_kayit(i, 0.50) for i in range(20)]
    fark = bootstrap_farki(a, list(a))
    assert fark["alt"] <= 0 <= fark["ust"]


# ─── karşılaştırma kuralı ─────────────────────────────────────────────────────

def _kesit(n: int = 12):
    """Piyasanın hafifçe bilgili olduğu sentetik kesit."""
    probs = [{"1": 0.5, "0": 0.3, "2": 0.2}] * MATCH_COUNT
    return [_girdi(i, ("1" * 8 + "0" * 4 + "2" * 3), probs) for i in range(1, n + 1)]


def test_gercekten_iyi_aday_gecer():
    """Kural ateşleyebiliyor mu — yalnızca `False` üreten kural işe yaramaz."""
    r = karsilastir([KahinTahminci, PiyasaTahminci], haftalar=_kesit())
    kahin = next(s for s in r["tahminciler"] if s["ad"] == "kahin")
    assert kahin["gecti"] is True
    assert kahin["fark"]["ust"] < 0


def test_esit_aday_gecmez():
    """Piyasanın kopyası piyasayı geçmez; aralık sıfırı içerir."""
    class Kopya(PiyasaTahminci):
        ad = "kopya"

    r = karsilastir([Kopya, PiyasaTahminci], haftalar=_kesit())
    kopya = next(s for s in r["tahminciler"] if s["ad"] == "kopya")
    assert kopya["gecti"] is False
    assert kopya["fark"]["alt"] <= 0 <= kopya["fark"]["ust"]


@pytest.mark.parametrize("sira", [
    [KahinTahminci, PiyasaTahminci],
    [PiyasaTahminci, KahinTahminci],
])
def test_sonuc_fabrika_sirasindan_bagimsiz(sira):
    """Gerileme testi: referans listenin başındayken de karşılaştırılabilmeli.

    İlk sürüm kayıtları tek geçişte siliyordu; referans başta olduğunda kendi
    kayıtlarını sonraki adaylar okumadan siliyor ve `KeyError` veriyordu.
    Sıra bir sözleşme değil, o yüzden ikisi de sınanır.
    """
    r = karsilastir(sira, haftalar=_kesit())
    kahin = next(s for s in r["tahminciler"] if s["ad"] == "kahin")
    assert kahin["gecti"] is True


def test_referans_kendisiyle_karsilastirilmaz():
    r = karsilastir([PiyasaTahminci], haftalar=_kesit())
    piyasa = next(s for s in r["tahminciler"] if s["ad"] == "piyasa")
    assert piyasa["fark"] is None


def test_az_ornek_bayragi():
    assert karsilastir(haftalar=_kesit(AZ_HAFTA - 1))["az_ornek"] is True
    assert karsilastir(haftalar=_kesit(AZ_HAFTA))["az_ornek"] is False


def test_sonuc_brier_sirasinda():
    r = karsilastir(haftalar=_kesit())
    brierler = [s["brier"] for s in r["tahminciler"]]
    assert brierler == sorted(brierler)


def test_ic_kayitlar_disari_sizmaz():
    """`_kayitlar` koşum içi ayrıntıdır; sözleşmeye dahil değildir."""
    r = karsilastir(haftalar=_kesit())
    assert all("_kayitlar" not in s for s in r["tahminciler"])


# ─── gerçek veri ──────────────────────────────────────────────────────────────

def test_olculebilir_haftalar_tam_kupon():
    haftalar = olculebilir_haftalar()
    assert haftalar, "olculebilir hafta bulunamadi"
    for h in haftalar:
        assert h["usable"] is True
        assert h["missing"] == 0
        assert len(h["results"]) == MATCH_COUNT
        assert all(p is not None for p in h["probs"])


def test_gercek_kesit_36_hafta_540_mac():
    """Kesit belgede yazan sayıya bağlı: 41 haftanın 36'sı tam oranlı."""
    r = karsilastir()
    assert r["n_hafta"] == 36
    assert r["n_mac"] == 540


def test_piyasa_baslangic_cizgisi():
    """Piyasanın çizgisi 0,5747 — belgedeki 0,579 ile farkı bilinçlidir.

    0,579, 2 kısmi haftayı da içeren 38 haftanın (567 maç) ortalamasıdır.
    Koşum yalnızca 15 maçının tamamı oranlı haftaları alır, çünkü bütün
    tahminciler **aynı** haftalarda ölçülmezse karşılaştırma anlamsızdır.
    """
    r = karsilastir()
    piyasa = next(s for s in r["tahminciler"] if s["ad"] == "piyasa")
    assert piyasa["brier"] == pytest.approx(0.5747, abs=0.002)


def test_gercek_veride_referans_siralamasi():
    """piyasa < sezon_sabiti < duzgun. Bozulursa aday değil, veri bozulmuştur."""
    r = karsilastir()
    skor = {s["ad"]: s["brier"] for s in r["tahminciler"]}
    assert skor["piyasa"] < skor["sezon_sabiti"] < skor["duzgun"]
    assert skor["duzgun"] == pytest.approx(BRIER_ESIT, abs=1e-3)


def test_hicbir_referans_piyasayi_gecmez():
    """Referanslar çizgiyi geçmemeli; geçseydi çizgi yanlış seçilmiş olurdu."""
    r = karsilastir()
    for s in r["tahminciler"]:
        if s["ad"] != "piyasa":
            assert s["gecti"] is False


# ─── karar yuvarlanmamış sayıdan verilir ──────────────────────────────────────

def _kayit(brier_toplam: float, n: int = 15):
    return {"n": n, "brier_toplam": brier_toplam, "log_toplam": 0.0}


def test_bootstrap_ham_degerleri_tasir():
    from spor_toto.evaluate import bootstrap_farki
    aday = [_kayit(8.9) for _ in range(20)]
    ref = [_kayit(9.0) for _ in range(20)]
    f = bootstrap_farki(aday, ref)
    assert {"ham_fark", "ham_alt", "ham_ust"} <= set(f)
    assert f["ham_ust"] == pytest.approx(f["ust"], abs=5e-5)


def test_cok_dar_aralik_gecmis_sayilir():
    """Yuvarlanmış üst sınırla karar vermek sessiz bir hataydı.

    `round(-0.000031, 4)` `-0.0` verir ve `-0.0 < 0` `False`'tur; yani güven
    aralığının tamamı sıfırın altındayken aday "geçmedi" yazılırdı. Hata tam
    da aralığın daraldığı — kararın zorlaştığı — yerde ortaya çıkıyordu.
    """
    from spor_toto.evaluate import bootstrap_farki
    # Her hafta aday referanstan azıcık ama İSTİSNASIZ iyi: hangi haftalar
    # örneklenirse örneklensin fark negatif kalır, yani aralık tamamen
    # sıfırın altındadır.
    aday = [_kayit(9.0 - 0.0005) for _ in range(30)]
    ref = [_kayit(9.0) for _ in range(30)]
    f = bootstrap_farki(aday, ref)
    assert f["ust"] == 0.0, "yuvarlanmis ust sinir sifira dusmeli (senaryonun sarti)"
    assert f["ham_ust"] < 0, "ham ust sinir sifirin altinda olmali"
    assert bool(f["ham_ust"] < 0) is True
    # Eski kural bu adayı "geçmedi" sayardı:
    assert bool(f["ust"] < 0) is False


# ─── öğrenme eğrisi ───────────────────────────────────────────────────────

def _egri_kesiti(n: int = 24):
    """Eğri için yeterli hafta — kesirlerin ayrışabilmesi lazım."""
    import random

    rnd = random.Random(4242)
    return [_girdi(i + 1, "".join(rnd.choice(SYMBOLS) for _ in range(MATCH_COUNT)))
            for i in range(n)]


def test_ogrenmeyen_tahmincide_egri_duz():
    """**Asıl bekçi.** `piyasa` hiçbir şey öğrenmez; eğrisi düz olmalı.

    Eğri düz çıkmıyorsa alt örnekleme *ölçüm* setine dokunuyor demektir —
    yani eğitim/test ayrımı sızdırıyordur. Bu test o sızıntıyı yakalar ve
    hiçbir sayı bilgisi gerektirmez: `piyasa` için eğitim büyüklüğünün
    sonuca etkisi tanım gereği sıfırdır.
    """
    e = ogrenme_egrisi(PiyasaTahminci, _egri_kesiti())
    brierler = {n["brier"] for n in e["noktalar"]}
    assert len(brierler) == 1, f"ogrenmeyen tahminci egrisi duz degil: {brierler}"
    assert e["toplam_inis"] == 0.0


def test_egri_her_kesir_icin_nokta_uretir():
    e = ogrenme_egrisi(PiyasaTahminci, _egri_kesiti())
    assert [n["kesir"] for n in e["noktalar"]] == list(EGRI_KESIRLERI)
    for n in e["noktalar"]:
        assert n["egitim_hafta"] >= 1
        assert n["n_mac"] > 0


def test_egri_egitim_buyuklugu_kesirle_artar():
    e = ogrenme_egrisi(PiyasaTahminci, _egri_kesiti())
    boyutlar = [n["egitim_hafta"] for n in e["noktalar"]]
    assert boyutlar == sorted(boyutlar)
    assert boyutlar[0] < boyutlar[-1]


def test_egri_tam_kesirde_butun_egitimi_kullanir():
    """`kesir=1.0` alt örneklememeli — tam eğitim setiyle aynı sonucu vermeli."""
    haftalar = _egri_kesiti()
    e = ogrenme_egrisi(SezonSabitiTahminci, haftalar)
    son = e["noktalar"][-1]
    tam = degerlendir(SezonSabitiTahminci, haftalar)
    assert son["brier"] == pytest.approx(tam["brier"], abs=5e-5)
    assert son["egitim_hafta"] == len(haftalar) - 1


def test_egri_deterministik():
    """Aynı tohum aynı eğriyi vermeli; yoksa 'ölçtük' demenin anlamı yok."""
    haftalar = _egri_kesiti()
    a = ogrenme_egrisi(SezonSabitiTahminci, haftalar)
    b = ogrenme_egrisi(SezonSabitiTahminci, haftalar)
    assert a["noktalar"] == b["noktalar"]


def test_egri_tohum_degisince_degisir():
    """Farklı tohum farklı alt küme seçmeli — aksi halde örnekleme ölüdür."""
    haftalar = _egri_kesiti()
    a = ogrenme_egrisi(SezonSabitiTahminci, haftalar)
    b = ogrenme_egrisi(SezonSabitiTahminci, haftalar, tohum=999)
    kucuk_a = [n["brier"] for n in a["noktalar"][:2]]
    kucuk_b = [n["brier"] for n in b["noktalar"][:2]]
    assert kucuk_a != kucuk_b


def test_egri_grup_olcusunu_bildirir():
    from spor_toto.evaluate import sezon_anahtari

    haftalar = _egri_kesiti()
    for h in haftalar:
        h["sezon"] = "2425" if h["week"] <= 12 else "2324"
    e = ogrenme_egrisi(SezonSabitiTahminci, haftalar, grup=sezon_anahtari)
    assert e["grup_olcusu"] == "sezon"
    assert e["n_grup"] == 2
