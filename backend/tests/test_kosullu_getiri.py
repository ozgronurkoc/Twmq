"""Koşullu getiri — havuz BİZ kazandığımızda bölünür.

Bu dosyanın bekçilik ettiği asıl şey `kalabalik_kademeleri` ile
`kosullu_kademe_dagilimi` arasındaki **farkın kaybolmamasıdır**: ilki
koşulsuzdur ve iki farklı plan için birebir aynı çıkar, ikincisi plana
bakar. Fark kaybolursa kalabalık ayarının kazancı tanım gereği ölçülemez
hâle gelir.
"""
from __future__ import annotations

import pytest

from spor_toto.getiri import (
    beklenen_tl,
    kalabalik_kademeleri,
    kosullu_kademe_dagilimi,
)


def _probs(n: int = 15) -> list[dict[str, float]]:
    out = []
    for i in range(n):
        p1 = 0.30 + 0.035 * i
        p0 = (1 - p1) * 0.42
        out.append({"1": p1, "0": p0, "2": 1 - p1 - p0})
    return out


def test_ortak_dagilim_olasilik_ve_toplami_bir():
    p = _probs()
    dp = kosullu_kademe_dagilimi(p, p, [["1", "0"]] * 15)
    assert dp.shape == (16, 16)
    assert dp.sum() == pytest.approx(1.0)
    assert (dp >= -1e-12).all()


def test_ucluye_isaretlenen_mac_ASLA_kacmaz():
    """Üç sembolün de işaretlendiği kuponda kaçak sıfırdır — sağlama."""
    p = _probs()
    dp = kosullu_kademe_dagilimi(p, p, [["1", "0", "2"]] * 15)
    assert dp[0, :].sum() == pytest.approx(1.0)
    assert dp[1:, :].sum() == pytest.approx(0.0, abs=1e-12)


def test_kosullu_dagilim_PLANA_bakar_kosulsuz_bakmaz():
    """Farkın kendisi bekçiye bağlandı — `getiri` docstring'inin iddiası."""
    p = _probs()
    a = [["1"]] * 15
    b = [["0"]] * 15
    # kosulsuz: iki plan icin BIREBIR ayni
    assert kalabalik_kademeleri(p, model="orneklem") == \
        kalabalik_kademeleri(p, model="orneklem")
    # kosullu: plana gore DEGISIR
    da = kosullu_kademe_dagilimi(p, p, a)
    db = kosullu_kademe_dagilimi(p, p, b)
    assert abs(float(da[0, :].sum()) - float(db[0, :].sum())) > 1e-6


def test_kalabalik_piyasayla_AYNIYSA_kosullu_uyum_yuksek():
    """`o = p` iken rakip bizimle aynı yerden çekiyor — uyum artar."""
    p = _probs()
    sec = [["1", "0"]] * 15
    ayni = kosullu_kademe_dagilimi(p, p, sec)
    # Kalabalik TERSINE oynasa uyum duser
    ters = [{"1": q["2"], "0": q["0"], "2": q["1"]} for q in p]
    zit = kosullu_kademe_dagilimi(p, ters, sec)
    assert float(ayni[0, 15]) > float(zit[0, 15])


def test_beklenen_tl_havuz_yoksa_sifir():
    p = _probs()
    assert beklenen_tl(p, p, [["1", "0"]] * 15, {}, {}, 13, 1000) == 0.0


def test_beklenen_tl_rakip_arttikca_DUSER():
    """`N·q` büyüdükçe pay söner — `getiri` modül başlığının tek cümlesi."""
    p = _probs()
    sec = [["1", "0"]] * 15
    havuz = {13: 1e7, 12: 1e6}
    az = beklenen_tl(p, p, sec, {}, havuz, 13, 1_000)
    cok = beklenen_tl(p, p, sec, {}, havuz, 13, 100_000_000)
    assert az > cok > 0


def test_kayip_orani_OLCULEN_sifir():
    """`0.05` bir harcama kararıydı; ölçüldü ve sıfır çıktı (Faz S)."""
    from spor_toto.secim import VARSAYILAN_KAYIP_ORANI

    assert VARSAYILAN_KAYIP_ORANI == 0.0


def test_monoton_kalabalikta_sapmak_KAZANDIRMAZ():
    """Faz S'nin çekirdek bulgusu: `o ∝ p^λ` iken taban plan zaten en iyi.

    Bekçi boş yeşil kalmasın diye alternatifin gerçekten kötü olduğu da
    sınanıyor — favoriyi bırakmak E[TL]'yi belirgin biçimde düşürmeli.
    """
    from spor_toto.kalabalik import OLCULEN, oynanma_paylari

    p = _probs()
    oy = oynanma_paylari(p, OLCULEN)
    havuz = {13: 1e7, 12: 1e6}
    taban = [["1", "0"]] * 15
    # ilk macta favoriyi birak
    kotu = [["0", "2"]] + [["1", "0"]] * 14
    a = beklenen_tl(p, oy, taban, {}, havuz, 13, 15_000_000)
    b = beklenen_tl(p, oy, kotu, {}, havuz, 13, 15_000_000)
    assert a > b, "monoton kalabalikta favoriyi birakmak kazandiramaz"
