"""Kalabalık modeli — havuz ekseninin ölçülen ilk parçası.

Bu dosyanın bekçilik ettiği asıl şey `λ`'nın **değeri** değil, modelin iki
uç varsayımı (`orneklem`, `favori`) gerçekten **içine aldığı** ve ölçeğin
(haftalık kolon sayısı) uyuma hiç girmediğidir. O iki özellik giderse sayı
sessizce başka bir şeyin ölçümü olur.
"""
from __future__ import annotations

import numpy as np
import pytest

from spor_toto import kalabalik as K


def _probs(n: int = 15) -> list[dict[str, float]]:
    out = []
    for i in range(n):
        p1 = 0.30 + 0.035 * i
        p0 = (1 - p1) * 0.42
        out.append({"1": p1, "0": p0, "2": 1 - p1 - p0})
    return out


def test_orneklem_piyasayi_AYNEN_kopyalar():
    """`λ = 1, δ = h = 0` piyasa olasılığının kendisidir — model onu içeriyor."""
    p = _probs()
    o = K.oynanma_paylari(p, K.ORNEKLEM)
    for ham, pay in zip(p, o):
        for s in ("1", "0", "2"):
            assert pay[s] == pytest.approx(ham[s], abs=1e-9)


def test_favori_butun_payi_en_olasiya_yigar():
    """`λ → ∞` ucunu da içeriyor: pay argmax sembolde toplanır."""
    o = K.oynanma_paylari([{"1": 0.5, "0": 0.3, "2": 0.2}], K.FAVORI)[0]
    assert o["1"] == pytest.approx(1.0, abs=1e-3)
    assert o["0"] + o["2"] < 1e-3


def test_lambda_buyudukce_favoriye_yigilma_ARTAR():
    """Parametrenin yönü tanımlı: monoton olmayan bir λ ölçümü anlamsız olurdu."""
    p = [{"1": 0.5, "0": 0.3, "2": 0.2}]
    onceki = 0.0
    for lam in (0.5, 1.0, 1.5, 2.0, 3.0):
        pay = K.oynanma_paylari(p, K.Kalabalik(lam, 0.0, 0.0))[0]["1"]
        assert pay > onceki
        onceki = pay


def test_paylar_toplami_bir():
    for model in (K.ORNEKLEM, K.OLCULEN, K.FAVORI):
        for pay in K.oynanma_paylari(_probs(), model):
            assert sum(pay.values()) == pytest.approx(1.0)


def test_kademe_dagilimi_poisson_binom_ve_toplami_bir():
    o = K.oynanma_paylari(_probs(), K.OLCULEN)
    dp = K.kademe_dagilimi(o, ["1"] * 15)
    assert len(dp) == 16
    assert dp.sum() == pytest.approx(1.0)
    # Hepsi kesin dogruysa dagilim 15'te tepe yapar
    kesin = [{"1": 1.0, "0": 0.0, "2": 0.0}] * 15
    assert K.kademe_dagilimi(kesin, ["1"] * 15)[15] == pytest.approx(1.0)


def test_uyum_OLCEKTEN_bagimsiz():
    """Haftalık kolon sayısı uyuma girmez — kademeler arası oran kullanılır.

    Kazanan adetlerini sabit bir çarpanla büyütmek NLL'i değiştirmemeli.
    Değiştirirse ölçek sızmış demektir ve `λ` artık şeklin değil
    büyüklüğün ölçümü olur.
    """
    satir = {"probs": _probs(), "gercek": ["1"] * 15,
             "kazanan": {14: 30, 13: 400, 12: 5000}}
    on_kat = {**satir, "kazanan": {k: v * 10 for k, v in satir["kazanan"].items()}}
    assert K.hafta_nll(satir, K.OLCULEN) == pytest.approx(
        K.hafta_nll(on_kat, K.OLCULEN))


def test_15_kademesi_uyuma_GIRMEZ():
    """14/13/12 kolon sayar, 15 KUPON sayar — aynı olabilirliğe karışamazlar."""
    assert 15 not in K.KADEMELER
    assert K.KADEMELER == (14, 13, 12)


def test_olculen_iki_ucun_ARASINDA():
    """Ölçülen model `orneklem` ile `favori` arasında olmalı — dışına düşerse
    ölçüm değil ekstrapolasyon yapıyoruz demektir."""
    assert 1.0 < K.OLCULEN.lam < K.FAVORI_USSU
    assert K.OLCULEN.delta == 0.0 and K.OLCULEN.h == 0.0, (
        "delta/h kazanmadi; modelde durmamali (OLCULEN kunyesi)")


def test_getiri_olculen_modelini_taniyor():
    """`getiri` dördüncü modeli gerçekten kullanıyor ve iki ucun arasında."""
    from spor_toto.getiri import KALABALIK_MODELLERI, kalabalik_kademeleri

    assert "olculen" in KALABALIK_MODELLERI
    p = _probs()
    orn = kalabalik_kademeleri(p, model="orneklem")
    olc = kalabalik_kademeleri(p, model="olculen")
    fav = kalabalik_kademeleri(p, model="favori")
    for k in orn:
        assert orn[k] < olc[k] < fav[k], k


def test_kestirim_sentetik_lambdayi_geri_bulur():
    """Bekçi boş yeşil kalmasın: bilinen λ ile üretilen veriden λ geri çıkmalı."""
    gercek_lam = 2.4
    rng = np.random.default_rng(7)
    satirlar = []
    for _ in range(40):
        p = []
        for _ in range(15):
            v = rng.dirichlet([4.0, 2.5, 3.0])
            p.append({"1": float(v[0]), "0": float(v[1]), "2": float(v[2])})
        gercek = ["1"] * 15
        dp = K.kademe_dagilimi(
            K.oynanma_paylari(p, K.Kalabalik(gercek_lam, 0.0, 0.0)), gercek)
        # Beklenen adetler (buyuk N) — gurultusuz kurgu
        satirlar.append({"probs": p, "gercek": gercek, "kazanan": {
            k: max(1.0, 1e7 * float(dp[k])) for k in K.KADEMELER}})
    assert K.kestir_lam(satirlar).lam == pytest.approx(gercek_lam, abs=0.15)


@pytest.mark.slow
def test_veri_seti_112_hafta_civari():
    veri = K.veri_seti()
    assert 100 <= len(veri) <= 120, len(veri)
    for r in veri:
        assert set(r["kazanan"]) == set(K.KADEMELER)
        assert all(v > 0 for v in r["kazanan"].values())


@pytest.mark.slow
def test_favori_havuz_sinavinda_IMKANSIZ_kolon_ima_ediyor():
    """`favori`nin çürütülmesi ikinci ve bağımsız yoldan da kayıtlı olsun."""
    veri = K.veri_seti()
    fav = K.havuz_sinavi(veri, K.FAVORI)
    olc = K.havuz_sinavi(veri, K.OLCULEN)
    assert fav["ortalama_r"] < 0 < olc["ortalama_r"]
    # Dunya nufusu ~8e9; favori bunun kat kat ustunu ima ediyor.
    assert min(s["medyan_N"] for s in fav["sezonlar"]) > 1e12
    assert all(s["medyan_N"] < 1e9 for s in olc["sezonlar"])
