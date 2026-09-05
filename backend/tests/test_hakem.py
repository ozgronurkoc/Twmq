"""E4 — hakem ailesinin bekçileri.

Ölçümün **sonucu** dondurulmaz (ölçüm değişince test onu geriye dönük
yeniden yazmaya zorlardı — depo doktrini bunu yasaklıyor); dondurulan şey
ölçümün **sızıntısızlığı** ve kesitinin sınırıdır.
"""
from __future__ import annotations

import pytest

from spor_toto import hakem


def test_ozellik_MACIN_KENDISINI_gormuyor():
    """Sızıntısızlığın kendisi: ilk maçta özellik sıfırdır.

    Bir hakemin ilk maçında geçmişi yoktur, dolayısıyla artığı da olamaz.
    Sıfırdan farklı çıkarsa geçiş sırası ters kurulmuş, yani maç kendi
    özelliğini besliyor demektir.
    """
    satirlar = [
        {"hakem": "A", "kod": "1", "probs": {"1": 0.5, "0": 0.3, "2": 0.2}},
        {"hakem": "A", "kod": "2", "probs": {"1": 0.5, "0": 0.3, "2": 0.2}},
        {"hakem": "B", "kod": "1", "probs": {"1": 0.4, "0": 0.3, "2": 0.3}},
    ]
    hakem._gecmis_artiklar(satirlar)
    assert satirlar[0]["hakem_n"] == 0
    assert satirlar[0]["hakem_ev"] == 0.0
    assert satirlar[0]["hakem_beraberlik"] == 0.0
    assert satirlar[2]["hakem_n"] == 0, "B'nin ilk maci — A'nin gecmisi ona akmaz"
    # A'nin IKINCI maci artik bir gecmis GORUR ve isareti dogru olmali:
    # ilk macta ev kazandi ve piyasa 0,5 diyordu -> artik POZITIF.
    assert satirlar[1]["hakem_n"] == 1
    assert satirlar[1]["hakem_ev"] > 0.0


def test_kucultme_az_macli_hakemi_SIFIRA_ceker():
    """`B = n / (n + K)` — bir maçlık hakem neredeyse hiç konuşamaz."""
    tek = [{"hakem": "A", "kod": "1", "probs": {"1": 0.2, "0": 0.4, "2": 0.4}},
           {"hakem": "A", "kod": "1", "probs": {"1": 0.2, "0": 0.4, "2": 0.4}}]
    hakem._gecmis_artiklar(tek)
    ham = 1.0 - 0.2
    assert 0.0 < tek[1]["hakem_ev"] < ham / 10.0, \
        "kucultme uygulanmamis — ham artik geciyor"
    assert tek[1]["hakem_ev"] == pytest.approx(
        (1 / (1 + hakem.KUCULTME_K)) * ham)


def test_aday_listesi_DONMUS():
    """E4 tek denemedir: geçmezse liste uzatılmaz.

    Bu bekçi bir disiplin kaydıdır — birinci turun on bir ölçümü de aynı
    kuralla koştu. Aday eklemek isteyen önce bu testi değiştirmek, yani
    kararı görünür kılmak zorunda.
    """
    assert hakem.ADAYLAR == ("hakem_ev", "hakem_beraberlik", "hakem_ikisi")
    assert set(hakem._ALAN) == set(hakem.ADAYLAR)


@pytest.mark.slow
def test_kesit_YALNIZCA_hakemi_olan_liglerde():
    """Coğrafi sınır ölçülmüş bir olgudur ve kesit onu itiraf etmeli.

    football-data hakemi yalnızca Britanya liglerinde yazıyor. Kesit kıta
    Avrupası liglerinden satır taşıyorsa eşleme bozulmuş demektir.
    """
    s = hakem.veri_seti()
    if not s:
        pytest.skip("hakem tablosu yok — scripts/build_hakem.py ile uretilir")
    ligler = {r["lig"] for r in s}
    assert ligler <= {"E0", "E1", "E2", "E3", "EC",
                      "SC0", "SC1", "SC2", "SC3"}
    assert len({r["sezon"] for r in s}) == 4, "sezon disarida birakmali icin"


@pytest.mark.slow
def test_yayilim_sinavi_ETKI_VAR_MI_sorusunu_ayirir():
    """"Geçmedi" iki şeyden gelebilir; yayılım sınavı ikisini ayırır.

    Etki var ama düzeltme yakalayamıyor **ile** etki yok aynı Brier farkını
    verir. Sınav şansın ürettiği yayılımı hesaplayıp gözlenenden çıkarır.
    """
    y = hakem.yayilim_sinavi()
    if not y:
        pytest.skip("hakem tablosu yok")
    for satir in y:
        assert satir["gozlenen_sd"] > 0.0 and satir["sans_sd"] > 0.0
        assert (satir["gercek_etki_sd"] is None) is not satir["etki_var_mi"]
