"""analysis.py: Monte Carlo ve hata frekansi testleri."""

from __future__ import annotations

import math

import pytest

from spor_toto.analysis import match_error_frequency, monte_carlo_report
from spor_toto.core import SEMBOLLER, Encoder, parse_picks
from spor_toto.duz import kolonlar as duz_kolonlar

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


from tests.conftest import enc_ve_kolonlar as _enc_cols  # tek kaynak
from tests.conftest import esit_olasiliklar as _uniform_probs  # tek kaynak


def test_monte_carlo_shape_and_bounds():
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=3_000, seed=1)
    assert mc["n_samples"] == 3_000
    for key in ("kume_ici", "p15", "p14", "p13", "p12"):
        block = mc[key]
        assert 0.0 <= block["p"] <= 1.0
        assert "pct" in block and "se" in block and "ci95" in block
        assert "count" in block


def test_monte_carlo_mac_sayisi_uyusmazligi():
    enc, cols = _enc_cols()
    with pytest.raises(ValueError):
        monte_carlo_report(enc, cols, _uniform_probs(3), n_samples=100)


def test_monte_carlo_deterministik():
    enc, cols = _enc_cols()
    a = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2_000, seed=99)
    b = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2_000, seed=99)
    assert a["p15"]["count"] == b["p15"]["count"]
    assert a["kume_ici"]["count"] == b["kume_ici"]["count"]


def test_monte_carlo_exact_ile_yaklasik():
    """Yuksek n ile exact p_kume_ici'ye yaklasmali (uniform secim ici)."""
    enc, cols = _enc_cols()
    # Secim kumesi uzerinde uniform: her mac icin seceneklere esit agirlik
    probs = []
    for sec in enc.selections:
        p = dict.fromkeys(SEMBOLLER, 0.0)
        for s in sec:
            p[s] = 1.0 / len(sec)
        probs.append(p)
    mc = monte_carlo_report(enc, cols, probs, n_samples=20_000, seed=42)
    # Secim ici normalize oldugu icin kume_ici ~ 1
    assert mc["kume_ici"]["p"] > 0.95


def test_monte_carlo_dusuk_n_calisir():
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=500, seed=0)
    assert mc["n_samples"] == 500


def test_error_freq_gecerli_kaplamada_n2_sifir():
    enc, cols = _enc_cols()
    ef = match_error_frequency(enc, cols)
    assert ef["n2"] == 0
    assert isinstance(ef["d1"], list)
    assert isinstance(ef["d2"], list)


def test_error_freq_bos_kolon():
    enc = Encoder(parse_picks(ORNEK))
    ef = match_error_frequency(enc, [])
    assert ef == {"d1": [], "d2": [], "n1": 0, "n2": 0}


# ─── max_d: parametre gercekten bagli mi ──────────────────────────────────
#
# `max_d` uzun sure imzada vardi ama govde katmanlari sabit yaziyordu ve
# ucu cagirandan ikisi `max_d=2` gectigi icin atillik hicbir yerde
# gorunmuyordu. Bu testler parametrenin ISLEDIGINI gosterir; olmasalardi
# atil hale geri donmesi yine sessiz olurdu.

def _kacakli_enc_cols():
    """d2 katmani DOLU bir kurulum — kaplama kasten eksik.

    `_enc_cols` tam kaplama verir ve orada `n2 == 0`'dir; d2 uzerine bir
    sey soyleyebilmek icin bosluklu bir kurulum gerekiyor.
    """
    enc = Encoder(parse_picks(ORNEK))
    cols = duz_kolonlar(enc)
    return enc, cols[:3]


def test_max_d_sifir_hicbir_katman_saymaz():
    """`max_d=0` → sayilacak hata yok: d=0 noktasinin hata pozisyonu yoktur."""
    enc, cols = _kacakli_enc_cols()
    ef = match_error_frequency(enc, cols, max_d=0)
    assert ef["n1"] == 0 and ef["n2"] == 0
    assert ef["d1"] == [] and ef["d2"] == []


def test_max_d_bir_yalnizca_d1():
    enc, cols = _kacakli_enc_cols()
    bir = match_error_frequency(enc, cols, max_d=1)
    iki = match_error_frequency(enc, cols, max_d=2)
    # d1 iki kipte de AYNI: max_d katman sayisini belirler, sayimi degil.
    assert bir["d1"] == iki["d1"] and bir["n1"] == iki["n1"]
    assert bir["n1"] > 0, "kurulum d1 uretmiyor — test bos olurdu"
    # d2 yalnizca istendiginde dolar.
    assert bir["n2"] == 0 and bir["d2"] == []
    assert iki["n2"] > 0, "kurulum d2 uretmiyor — test bos olurdu"


def test_max_d_ikinin_uzeri_yeni_katman_acar():
    enc, cols = _kacakli_enc_cols()
    ef = match_error_frequency(enc, cols, max_d=3)
    # Sozlesme anahtarlari yerinde, ustune d3 eklendi.
    assert {"d1", "d2", "n1", "n2", "d3", "n3"} <= set(ef)
    assert match_error_frequency(enc, cols, max_d=2).keys() == {
        "d1", "d2", "n1", "n2"}, "istenmemis katman uretilmemeli"


def test_max_d_mac_sayisina_tavanlanir():
    """Mesafe pozisyon sayisini asamaz — buyuk `max_d` bos katman uretmez."""
    enc, cols = _kacakli_enc_cols()
    n = len(enc.alphabet_sizes)
    ef = match_error_frequency(enc, cols, max_d=n + 5)
    assert f"d{n}" in ef and f"d{n + 1}" not in ef


def test_max_d_gecersiz_deger_reddedilir():
    enc, cols = _enc_cols()
    with pytest.raises(ValueError):
        match_error_frequency(enc, cols, max_d=-1)
    with pytest.raises(ValueError):
        match_error_frequency(enc, cols, max_d="iki")


def test_max_d_varsayilani_eski_davranis():
    """Varsayilan cagri, `max_d=2` ile birebir ayni — sozlesme kirilmadi."""
    enc, cols = _kacakli_enc_cols()
    assert match_error_frequency(enc, cols) == match_error_frequency(
        enc, cols, max_d=2)


# ─── yuzde paydasi ────────────────────────────────────────────────────────

def test_yuzdeler_yuze_toplanir():
    """Her katman %100'e toplanir — payda HATA YUVASI, nokta degil.

    Onceden payda nokta sayisiydi ve `d2` **%200'e** topluyordu: d=2
    noktasinin iki hata pozisyonu var, yani pay iki kez sayiliyordu.
    Iki sutun ayni bicimde sunuluyor ama farkli olcekte normalize
    ediliyordu; ayni tabloda yan yana duran iki sayi ayni seyi
    soylemiyordu.
    """
    enc, cols = _kacakli_enc_cols()
    ef = match_error_frequency(enc, cols, max_d=3)
    for k in (1, 2, 3):
        if ef[f"n{k}"] == 0:
            continue
        assert abs(sum(i["pct"] for i in ef[f"d{k}"]) - 100.0) < 0.5, f"d{k}"
        # Ham sayimlarin toplami da tanim geregi `n_k * k` olmali.
        assert sum(i["count"] for i in ef[f"d{k}"]) == ef[f"n{k}"] * k


# ─── parcali uretim ───────────────────────────────────────────────────────

def test_uzay_parcali_uretim_itertools_sirasini_korur():
    """Sira `itertools.product` ile birebir — esitlikte ilk kolon secilir.

    `argmin` esit mesafede ILK kolonu secer; uzayin sirasi degisirse
    esitlik durumlarinda baska bir kolon kazanir ve `d1`/`d2` dagilimi
    **sessizce** kayar. Bu yuzden sira bir uygulama ayrintisi degil,
    davranisin kendisidir.
    """
    import itertools

    import numpy as np

    from spor_toto.analysis import _uzay_blogu

    for sizes in ([3, 2, 3], [2, 2, 2, 3], [3, 3, 2], [2], [4, 3]):
        n = len(sizes)
        basamak = [1] * n
        for j in range(n - 2, -1, -1):
            basamak[j] = basamak[j + 1] * sizes[j + 1]
        toplam = math.prod(sizes)
        ref = np.array(list(itertools.product(*[range(k) for k in sizes])),
                       dtype=np.int8)
        assert np.array_equal(_uzay_blogu(sizes, basamak, 0, toplam), ref)
        # Parca sinirlari sirayi bozmuyor: her parca kendi araligini verir.
        for p in (1, 2, 5, 7):
            yigin = np.concatenate([
                _uzay_blogu(sizes, basamak, b, min(b + p, toplam))
                for b in range(0, toplam, p)])
            assert np.array_equal(yigin, ref), (sizes, p)


def test_is_tavani_asilirsa_acik_hata():
    """Tavan asilinca sessiz OOM degil, adiyla `ValueError`."""
    from spor_toto.analysis import ISLEM_SINIRI

    enc = Encoder(["102"] * 15)                       # 3^15 = 14.348.907
    kolon = ISLEM_SINIRI // enc.space_size() + 2      # tavani bir tik asan
    cols = [tuple([0] * len(enc.alphabet_sizes))] * kolon
    with pytest.raises(ValueError, match="is yuku"):
        match_error_frequency(enc, cols)


# ─── olasilik dogrulamasi ─────────────────────────────────────────────────

@pytest.mark.parametrize("bozuk", [float("nan"), float("inf"),
                                   float("-inf"), "yarim"])
def test_gecersiz_olasilik_reddedilir(bozuk):
    """NaN / inf / sayi olmayan sessizce yutulmaz.

    Ucu de eskiden gecerdi ve yutulma bicimleri birbirinden kotuydu:
    `max(0.0, nan)` Python'da `0.0` doner (eksik veri sifir olasiliga
    donusurdu), `inf` ise normalize sonucu butun sembolleri `nan` yapardi
    ve `nan` karsilastirmalari hep yanlis oldugu icin hicbir esik
    yakalamazdi.
    """
    enc, cols = _enc_cols()
    probs = _uniform_probs()
    probs[4] = {**probs[4], "0": bozuk}
    with pytest.raises(ValueError):
        monte_carlo_report(enc, cols, probs, n_samples=100)


def test_sifir_toplam_duzgun_dagilima_duser():
    """`0/0/0` HATA DEGIL — "bilgi yok"un tarafsiz karsiligi duzgun dagilim.

    Kural bilinclidir, tek yerde yazilidir (`ortak.normalize_olasilik`) ve
    arayuzde birebir aynadadir (`frontend/lib/utils.ts`). Yiginin bir
    ucunda hataya cevirmek ikisini ayristirirdi; bu test o karari
    sabitler.
    """
    enc, cols = _enc_cols()
    probs = _uniform_probs()
    probs[0] = dict.fromkeys(SEMBOLLER, 0.0)
    mc = monte_carlo_report(enc, cols, probs, n_samples=2_000, seed=3)
    assert mc["n_samples"] == 2_000


def test_negatif_olasilik_kirpilir():
    """Negatif deger reddedilmez, kirpilir — ayni paylasilan kural."""
    enc, cols = _enc_cols()
    probs = _uniform_probs()
    probs[0] = {"1": -0.5, "0": 0.5, "2": 0.5}
    mc = monte_carlo_report(enc, cols, probs, n_samples=1_000, seed=3)
    assert mc["n_samples"] == 1_000


# ─── guven araligi ────────────────────────────────────────────────────────

def test_wilson_araligi_orani_kapsar_ve_sinirlar_icinde():
    """`ci_alt`/`ci_ust` GERCEK aralik; `ci95` yari genislik olarak kaliyor.

    Normal yaklasim kucuk orneklemde kenarlara yapisir — 0 sayimda alt
    siniri eksiye iner. Wilson her zaman [0, 100] icinde kalir ve
    fonksiyonun `n_samples < 100` uyarisi verdigi bolge tam olarak bu
    yaklasimin yanildigi bolgedir.
    """
    from spor_toto.ortak import GUVEN_Z

    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=5_000, seed=7)
    for key in ("kume_ici", "p15", "p14", "p13", "p12"):
        b = mc[key]
        assert 0.0 <= b["ci_alt"] <= 100.0
        assert 0.0 <= b["ci_ust"] <= 100.0
        assert b["ci_alt"] <= b["pct"] + 1e-9
        assert b["pct"] <= b["ci_ust"] + 1e-9
        # `ci95` sozlesme geregi duruyor ve yari genislik olarak tanimli.
        assert abs(b["ci95"] - round(GUVEN_Z * b["se"] * 100.0, 3)) < 1e-9


def test_wilson_sifir_sayimda_negatife_inmez():
    """Normal yaklasimin yanildigi yer: 0 sayim.

    `p - 1.96*se = 0` degil, pratikte `-` tarafa gecen bir yari genislik
    uretir; Wilson alt siniri 0'da kalir, ust siniri pozitiftir.
    """
    from spor_toto.ortak import wilson

    alt, ust = wilson(0, 5_000)
    assert alt == 0.0 and 0.0 < ust < 0.01


def test_error_freq_se_ci_formulu():
    """rate blogundaki se formulu tutarli."""
    enc, cols = _enc_cols()
    n = 5_000
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=n, seed=7)
    p = mc["p15"]["p"]
    se = math.sqrt(p * (1.0 - p) / n)
    assert abs(mc["p15"]["se"] - se) < 1e-12


def test_mc_warning_cok_dusuk():
    """n < 100 → sert uyarı."""
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=50, seed=1)
    assert "warning" in mc
    assert "cok dusuk" in mc["warning"]


def test_mc_warning_dusuk():
    """100 ≤ n < 1000 → yumuşak uyarı."""
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=500, seed=1)
    assert "warning" in mc
    assert "dusuk" in mc["warning"]
    assert "cok dusuk" not in mc["warning"]


def test_mc_warning_yok_yeterli_n():
    enc, cols = _enc_cols()
    mc = monte_carlo_report(enc, cols, _uniform_probs(), n_samples=2000, seed=1)
    assert "warning" not in mc
