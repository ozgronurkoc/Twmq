"""Ufuk çevirisinin denetimi — haftalık `P(15/15)` → **hedefin kendisi**.

Bu modülün ölçtüğü şey bir plan değil bir **çeviri**: `1 − Π(1 − p_w)`. Küçük
bir gövde ama iki iddiası var ve ikisi de sayıya biniyor — yaklaşıklığın
yönü (Jensen) ve kâhin tahsisin bir **üst sınır** olduğu. İkisi de yanlış
yöne dönerse §3.73'ün hükmü sessizce tersine döner: zamanlama ekseni
"kapandı" diye yazılmışken aslında açık kalır.
"""

from itertools import product

import pytest

from spor_toto.ufuk import (
    beklenen_sayi,
    en_az_bir,
    kahin_tahsisi,
    ortalamayla,
)


def test_en_az_bir_CARPIMIN_kendisi():
    """Tanım: `1 − Π(1 − p)`. Sınır hâlleri de dahil."""
    assert en_az_bir([]) == 0.0
    assert en_az_bir([0.0, 0.0]) == 0.0
    assert en_az_bir([1.0, 0.3]) == 1.0
    assert en_az_bir([0.1, 0.2, 0.3]) == pytest.approx(0.496, rel=1e-12)


def test_en_az_bir_ARALIK_DISINDA_hata():
    """Sessizce kırpmaz: 1'i aşan bir `p` çarpımı işaretiyle bozardı."""
    for kotu in ([-0.01], [1.01], [0.5, 2.0]):
        with pytest.raises(ValueError, match=r"0\.\.1"):
            en_az_bir(kotu)


def test_en_az_bir_HAFTA_EKLEMEK_dusurmez():
    """Bir hafta daha oynamak hedefe ulaşma olasılığını azaltamaz."""
    p = [0.05, 0.12, 0.20, 0.08]
    for i in range(len(p)):
        assert en_az_bir(p[:i + 1]) >= en_az_bir(p[:i]) - 1e-15


def test_yaklasiklik_HEP_AYNI_YONE_yaniliyor():
    """`1 − (1 − p̄)ⁿ` gerçek değerin **altında** kalır — Jensen.

    §3.73'ün ölçtüğü yanlılık bu: `coklu_kiyasi.py`nin "13 hafta" sütunu bu
    formülle yazılmıştı. Yön tersine dönerse o sütun iyimser olurdu ve
    hedefin kendisi olduğundan **fazla** okunurdu. Eşitlik yalnızca bütün
    haftalar birbirinin aynıysa geçerli; test onu da kovalıyor.
    """
    kumeler = [
        [0.10] * 5,                                   # ayrışma yok → eşit
        [0.02, 0.35, 0.09, 0.11, 0.18],
        [0.001, 0.5, 0.001, 0.001],
        [0.08, 0.09, 0.10, 0.11, 0.12, 0.13],
    ]
    for p in kumeler:
        ort = sum(p) / len(p)
        kesin, yaklasik = en_az_bir(p), ortalamayla(ort, len(p))
        assert kesin >= yaklasik - 1e-15, (p, kesin, yaklasik)
        if len(set(p)) == 1:
            assert kesin == pytest.approx(yaklasik, rel=1e-12)
        else:
            assert kesin > yaklasik


def test_beklenen_sayi_EN_AZ_BIRDEN_buyuk():
    """`Σ p ≥ 1 − Π(1 − p)` — birlik sınırı; ayrışma **doymanın** kendisi."""
    for p in ([0.1, 0.2, 0.3], [0.5] * 4, [0.01] * 20):
        assert beklenen_sayi(p) >= en_az_bir(p) - 1e-15


def test_kahin_DUZ_dagitimdan_kotu_DEGIL():
    """Kâhin bir **üst sınır** olarak kullanılıyor; düzün altına düşemez.

    §3.73'ün bütün hükmü buna dayanıyor: "tam öngörülü tahsis bile ancak
    ×1,0x getiriyor, o hâlde uygulanabilir hiçbir kural daha fazlasını
    getiremez." Kâhin düzün altına düşebilseydi o cümle bir alt sınırla
    kurulmuş olurdu ve hükmü taşımazdı.
    """
    B = 1000
    egriler = [
        [(0, 0.0), (B // 2, 0.04), (B, 0.07), (2 * B, 0.11), (4 * B, 0.16)],
        [(0, 0.0), (B // 2, 0.20), (B, 0.31), (2 * B, 0.44), (4 * B, 0.57)],
        [(0, 0.0), (B // 2, 0.01), (B, 0.02), (2 * B, 0.035), (4 * B, 0.06)],
        [(0, 0.0), (B // 2, 0.07), (B, 0.12), (2 * B, 0.19), (4 * B, 0.28)],
    ]
    duz = en_az_bir([e[2][1] for e in egriler])
    sonuc = kahin_tahsisi(egriler, B * len(egriler))
    assert sonuc is not None
    kahin, bedeller = sonuc
    assert kahin >= duz - 1e-12, (kahin, duz)
    assert sum(bedeller) <= B * len(egriler)
    for egri, b in zip(egriler, bedeller):
        assert b in [c for c, _p in egri], "secilen bedel egride yok"


def test_kahin_KABA_KUVVETLE_ayni():
    """Açgözlü tahsis, küçük bir örnekte tüm kombinasyonlarla aynı cevabı verir.

    Kabuk üzerinde açgözlü **kesindir** ama ancak oranlar azalansa; bedel
    ızgarası düzgün ve değer içbükeyken kabuk bütün noktaları tutar, yani
    kaba kuvvet ile birebir örtüşmelidir. Örtüşmezse ya kabuk nokta
    düşürüyordur ya da açgözlü yanlış sırayla yükseltiyordur.
    """
    egriler = [
        [(0, 0.00), (1, 0.10), (2, 0.17), (3, 0.22)],
        [(0, 0.00), (1, 0.25), (2, 0.40), (3, 0.48)],
        [(0, 0.00), (1, 0.05), (2, 0.09), (3, 0.12)],
    ]
    toplam = 3
    en_iyi = max(
        (en_az_bir([e[i][1] for e, i in zip(egriler, secim)])
         for secim in product(range(4), repeat=3)
         if sum(egriler[j][secim[j]][0] for j in range(3)) <= toplam),
        default=0.0)
    sonuc = kahin_tahsisi(egriler, toplam)
    assert sonuc is not None
    assert sonuc[0] == pytest.approx(en_iyi, rel=1e-12), (sonuc, en_iyi)


def test_kahin_BOS_egride_None():
    """Bir haftanın hiç noktası yoksa cevap yok — sessizce o hafta atlanmaz."""
    assert kahin_tahsisi([[(0, 0.0), (10, 0.1)], []], 100) is None


def test_kahin_BUTCE_asilmaz():
    """Toplam bütçe bir kısıt; aşılırsa 'aynı para' kıyası yalan olur."""
    egriler = [[(0, 0.0), (10, 0.2), (20, 0.3), (40, 0.4)]] * 5
    for toplam in (0, 10, 37, 50, 200):
        sonuc = kahin_tahsisi(egriler, toplam)
        assert sonuc is not None
        assert sum(sonuc[1]) <= toplam
