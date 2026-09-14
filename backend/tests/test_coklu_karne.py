"""`coklu_karne.py` — görev ölçeğinde para karnesinin bekçileri.

Bu dosyanın koruduğu iddia: **plan parasını çıkarmıyor ve bunun ölçüsü
doğru hesaplanıyor.** Hesap üç yerden bozulabilir ve üçü de burada tutulur:
kademe sayımı (üreteç fonksiyonu), kuponların ayrıklığı (çift sayma), ve
kazanansız kademenin fiyatlanması (ilk sürümün hatası — devir haftasında
getiriyi **sıfır** sayıyordu).
"""
from __future__ import annotations

import pytest

from scripts.coklu_karne import KADEMELER, hafta_getirisi, kademe_sayimi
from spor_toto.coklu import MAC_SAYISI, coklu_plan_serisi
from spor_toto.havuz import BOLUSUM


class _Kupon:
    """`coklu.Kupon`un bu ölçüm için gereken tek alanı."""

    def __init__(self, secimler):
        self.secimler = secimler


def _tek_kolon(sembol: str = "1") -> list[set[str]]:
    return [{sembol} for _ in range(MAC_SAYISI)]


def _gercek(kacak: int = 0) -> list[str]:
    return ["0" if i < kacak else "1" for i in range(MAC_SAYISI)]


def test_kademe_sayimi_tek_kolon():
    assert kademe_sayimi(_tek_kolon(), _gercek(0)) == {15: 1}
    assert kademe_sayimi(_tek_kolon(), _gercek(1)) == {14: 1}
    assert kademe_sayimi(_tek_kolon(), _gercek(4)) == {11: 1}


def test_kademe_sayimi_TOPLAMI_kutunun_kolon_sayisi():
    """Değişmez: sayım hiçbir kolonu düşürmez ve hiçbirini iki kez saymaz."""
    sec = [{"1", "0"}] * 3 + [{"1", "0", "2"}] * 2 + [{"1"}] * 10
    beklenen = 2 ** 3 * 3 ** 2
    for kacak in (0, 2, 5):
        say = kademe_sayimi(sec, _gercek(kacak))
        assert sum(say.values()) == beklenen, f"kacak={kacak}"


def test_kademe_sayimi_kacirilan_mac_TAVANI_dusurur():
    """Gerçek sembol kümede değilse o kutuda 15 mümkün olamaz."""
    sec = [{"0"}] + [{"1"}] * 14          # ilk maçta gerçek '1' kümede yok
    assert kademe_sayimi(sec, _gercek(0)) == {14: 1}
    sec2 = [{"0"}, {"0"}] + [{"1"}] * 13
    assert kademe_sayimi(sec2, _gercek(0)) == {13: 1}


def test_gercek_planin_kuponlari_AYRIK():
    """Kuponlar üzerinden toplamak çift saymamalı — betiğin dayandığı şart."""
    probs = [{"1": 0.5, "0": 0.25, "2": 0.25} for _ in range(MAC_SAYISI)]
    plan = coklu_plan_serisi(probs, 2_000, (27,))[27]
    toplam = 0
    for k in plan.kuponlar:
        toplam += sum(kademe_sayimi(k.secimler, _gercek(0)).values())
    assert toplam == plan.kolon


def test_seyrelme_ham_getiriden_BUYUK_OLAMAZ():
    """Havuzu bizim kolonlarımızla bölmek payı küçültür, büyütemez."""
    tablo = {k: {"correct": k, "winners": 10, "prize": 1_000.0}
             for k in KADEMELER}
    kuponlar = [_Kupon([{"1", "0"}] * 2 + [{"1"}] * 13)]
    g = hafta_getirisi(kuponlar, _gercek(0), tablo)
    assert 0 < g["seyrelmis"] <= g["ham"]


def test_KAZANANSIZ_kademe_sifir_sayilmaz():
    """İlk sürümün hatası: devir haftasında getiri sıfır çıkıyordu.

    Kazananı olmayan kademe, o haftanın payını ileri taşır; biz oynasaydık
    tek kazanan biz olurduk. Bekçi `birim` verildiğinde payın geldiğini,
    verilmediğinde **sessizce sıfır kalmadığını** değil, açıkça
    fiyatlanmadığını tutar.
    """
    tablo = {15: {"correct": 15, "winners": 0, "prize": 0.0}}
    kuponlar = [_Kupon(_tek_kolon())]
    birim = 1_000_000.0

    yok = hafta_getirisi(kuponlar, _gercek(0), tablo)
    assert yok["seyrelmis"] == 0.0 and yok["devirden"] == 0.0

    var = hafta_getirisi(kuponlar, _gercek(0), tablo, birim)
    assert var["seyrelmis"] == pytest.approx(BOLUSUM[15] * birim)
    assert var["devirden"] == pytest.approx(BOLUSUM[15] * birim)


def test_tutturmadigimiz_hafta_15ten_para_gelmez():
    tablo = {k: {"correct": k, "winners": 5, "prize": 100.0}
             for k in KADEMELER}
    kuponlar = [_Kupon(_tek_kolon())]
    g = hafta_getirisi(kuponlar, _gercek(3), tablo, 1_000.0)
    assert g["kademeler"] == {12: 1}
    assert g["seyrelmis"] == pytest.approx(5 * 100.0 / 6)
