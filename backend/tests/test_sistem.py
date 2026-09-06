"""ST EXTRA sistem fiyat tablosu — bedel formülden değil kayıttan.

Bu dosyanın bekçilik ettiği şey tek cümledir: **oynanan ürünün bedeli
`secim.bedel_hesapla`nın hesapladığı sayı değildir.** Tablo 84 şekli ve üç
garanti seviyesini taşır; formül yalnızca `solve_fix16`ın bedelini ve
yalnızca 14-garantiyi bilir.
"""
from __future__ import annotations

import pytest

from spor_toto import sistem
from spor_toto.secim import bedel_hesapla, sistem_secimi


def test_tablo_84_sekil_ve_15_mac():
    """Her satır 15 maça toplanır ve tablo eksiksizdir."""
    ham = sistem._tablo(None)
    assert len(ham["satirlar"]) == 84
    for s in ham["satirlar"]:
        assert s["tek"] + s["cift"] + s["kapali"] == sistem.MAC_SAYISI


def test_her_fiyat_kolon_bedelinin_kati():
    """250 fiyatın 250'si de ₺10'un katı — bedelin ÜÇÜNCÜ bağımsız teyidi.

    `dogrula` bunu okuma anında zaten koşuyor; burada niçin önemli olduğu
    yazılı kalsın diye ayrıca sınanıyor. Bir fiyat 10'un katı değilse kolon
    sayısı tamsayı çıkmaz ve o an tablo kolon bedeliyle çelişiyor demektir.
    """
    ham = sistem._tablo(None)
    kb = ham["meta"]["kolon_bedeli"]
    assert kb == 10.0
    for s in ham["satirlar"]:
        for g in sistem.GARANTILER:
            v = s["fiyat"][str(g)]
            assert v is None or v % kb == 0, (s, g, v)


def test_bozuk_tablo_okuma_aninda_duser():
    """Bekçi boş yeşil kalmasın: bilerek bozulmuş tablo `dogrula`yı düşürür."""
    iyi = {"meta": {"kolon_bedeli": 10.0},
           "satirlar": [{"tek": 7, "cift": 8, "kapali": 0,
                         "fiyat": {"12": 40, "13": 120, "14": 320}}]}
    sistem.dogrula(iyi)  # sağlam tablo geçer

    for bozuk, parca in (
        ({"tek": 7, "cift": 7, "kapali": 0}, "topluyor"),      # 14 maç
        ({"fiyat": {"12": 45, "13": 120, "14": 320}}, "kati degil"),
        ({"fiyat": {"12": 400, "13": 120, "14": 320}}, "ucuzlayamaz"),
    ):
        d = {"meta": {"kolon_bedeli": 10.0},
             "satirlar": [{**iyi["satirlar"][0], **bozuk}]}
        with pytest.raises(ValueError, match=parca):
            sistem.dogrula(d)


def test_kacak_esigi_garantiden_turer():
    """14→2, 13→1, 12→0. `secim`in sabit 2'si artık üç değerden biri."""
    assert [sistem.kacak_esigi(g) for g in (14, 13, 12)] == [2, 1, 0]
    with pytest.raises(ValueError):
        sistem.kacak_esigi(11)


def test_satilmayan_sekil_none_doner():
    """Tabloda `-` yazan hücre satılmayan şekildir, bedeli sıfır değil YOK."""
    assert sistem.bedel(6, 9, 0, garanti=12) is None
    assert sistem.bedel(6, 9, 0, garanti=13) is not None


def test_supheli_satirlar_isaretli_ve_duzeltilmemis():
    """İki tekdüzelik ihlali adıyla duruyor ve değerleri DEĞİŞTİRİLMEDİ."""
    sup = sistem.supheli_satirlar()
    assert len(sup) == 2
    for x in sup:
        s = sistem.bedel(x["tek"], x["cift"], x["kapali"], x["garanti"])
        assert s is not None
        assert s.supheli is True
        assert s.tl == x["fiyat"], "supheli satir sessizce duzeltilmis"


def _probs(n: int = 15) -> list[dict[str, float]]:
    out = []
    for i in range(n):
        p1 = 0.30 + 0.035 * i
        p0 = (1 - p1) * 0.42
        out.append({"1": p1, "0": p0, "2": 1 - p1 - p0})
    return out


def test_daha_cok_butce_hedefi_dusurmez():
    """Bütçe büyürken `P(k ≤ eşik)` monoton artmalı — arama kesin olduğu için.

    **Bu dosyanın üç testi silindi** ve sebebi bu testin ayakta kalmasıyla
    aynı: onlar `sistem_secimi` ile satıcının indirgenmiş sistem fiyat
    tablosu arasındaki BAĞI sınıyordu (formül ↔ tablo ayrışması, dönen
    şeklin tabloda satılıyor olması, yedi çifte şartının tabloda olmaması).
    Kaplama sökülünce o bağ kalmadı: `sistem_secimi` artık yalnızca TL'yi
    kolona çeviriyor. Buradaki iddia ise bağdan bağımsız — aramanın kesin
    olmasından geliyor ve düzde de geçerli.
    """
    onceki = -1.0
    for tl in (500.0, 1000.0, 2000.0, 3000.0, 5000.0):
        s = sistem_secimi(_probs(), tl)
        if s is None:
            continue
        assert s.p_hedef >= onceki - 1e-12, tl
        onceki = s.p_hedef
