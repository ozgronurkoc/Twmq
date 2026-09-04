"""Para karnesi — garanti tabanı, enflasyon uyarısı ve kıyas sınırı.

Bu dosyanın asıl bekçilik ettiği şey bir SAYI değil bir **sınır**: garanti
tabanı iki farklı garanti seviyesini karşılaştırmak için kullanılamaz. O
sınır kaybolursa modül sessizce yanlış bir cevap üretmeye başlar.
"""
from __future__ import annotations

import pytest

from spor_toto import karne
from spor_toto.sistem import VARSAYILAN_GARANTI


def _probs(n: int = 15) -> list[dict[str, float]]:
    out = []
    for i in range(n):
        p1 = 0.30 + 0.035 * i
        p0 = (1 - p1) * 0.42
        out.append({"1": p1, "0": p0, "2": 1 - p1 - p0})
    return out


def _tablo(prize: dict[int, float]) -> dict[int, dict[str, object]]:
    return {k: {"correct": k, "winners": 10, "prize": v}
            for k, v in prize.items()}


def test_garantiler_arasi_kiyas_YASAK():
    """Tabanın 15,1 katlık yanlılığı koda bağlı — sessizce kaybolmasın."""
    assert karne.gecerli_kiyas(13, 13) is True
    assert karne.gecerli_kiyas(14, 14) is True
    assert karne.gecerli_kiyas(13, 14) is False
    assert karne.gecerli_kiyas(12, 14) is False


def test_kademe_garantiden_ve_kacaktan_turer():
    """`kademe = G − k`. Kaçak arttıkça kademe düşer, 12'nin altı sıfır ödül."""
    tab = _tablo({15: 1e6, 14: 1e5, 13: 1e4, 12: 1e3})
    r = karne.hafta_karnesi(_probs(), ["1"] * 15, tab, 3000.0, garanti=14)
    assert r is not None
    assert r["kademe"] == 14 - r["kacak"]

    # Hic tutmayan bir sonuc: butun maclarda kacak -> kademe 12'nin altinda
    kotu = karne.hafta_karnesi(_probs(), ["0"] * 15, tab, 3000.0, garanti=14)
    assert kotu is not None
    assert kotu["odul"] == 0.0


def test_odul_12nin_altinda_sifir():
    """İkramiye 12'den başlar — 11 tutturmak para değildir."""
    tab = _tablo({15: 1e6, 14: 1e5, 13: 1e4, 12: 1e3})
    assert karne._odul(tab, 11) == 0.0
    assert karne._odul(tab, 12) == 1e3
    # Tabloda olmayan kademe de sifir, KeyError degil
    assert karne._odul(_tablo({12: 5.0}), 14) == 0.0


def test_butce_sigmazsa_hafta_dusmez_None_doner():
    """Şekil sığmıyorsa satır üretilmez — sıfır ödüllü sahte hafta yazılmaz."""
    tab = _tablo({12: 1.0})
    assert karne.hafta_karnesi(_probs(), ["1"] * 15, tab, 1.0,
                               garanti=VARSAYILAN_GARANTI) is None


def test_karne_bos_kesitte_sesli_duser():
    with pytest.raises(karne.KarneHatasi):
        karne.karne([])


def test_karne_uyarisi_enflasyonu_ve_tabani_ANIYOR():
    """Uyarı metni kaldırılırsa sayılar bağlamsız kalır — bekçi o yüzden var."""
    satir = [{"roi": 0.0, "odul": 0.0, "maliyet": 100.0, "kolon": 10,
              "sezon": "2025_26"}]
    k = karne.karne(satir)
    assert "enflasyon" in k["uyari"].lower()
    assert "GARANTI TABANI" in k["uyari"]
    assert k["sezonlar"][0]["sezon"] == "2025_26"


def test_kuyruk_sinavi_en_iyi_haftalari_atiyor():
    """§5.3(c): en iyi 5 hafta çıkarılınca ortalama düşmeli."""
    satir = [{"roi": 0.0, "odul": 0.0, "maliyet": 100.0, "kolon": 10,
              "sezon": "s"} for _ in range(20)]
    for i in range(5):
        satir[i] = {"roi": 10.0, "odul": 1000.0, "maliyet": 100.0,
                    "kolon": 10, "sezon": "s"}
    k = karne.karne(satir)
    assert k["ortalama_roi"] == pytest.approx(2.5)
    assert k["kuyruksuz_ortalama_roi"] == 0.0
    assert k["en_iyi_bes_hafta_payi"] == pytest.approx(1.0)


def test_bootstrap_sifir_farkta_sifir_aralik():
    lo, hi = karne.bootstrap_farki([0.0] * 50)
    assert lo == hi == 0.0
    lo2, hi2 = karne.bootstrap_farki([])
    assert (lo2, hi2) == (0.0, 0.0)


@pytest.mark.slow
def test_gercek_kesit_iki_arsivin_kesisimi():
    """Kesit gerçekten iki arşivin kesişimi ve boş değil."""
    kesit = karne.kupon_kesiti()
    assert len(kesit) > 100
    for h in kesit:
        assert len(h["probs"]) == 15
        assert len(h["gercek"]) == 15
        assert 15 in h["tablo"], "ikramiye tablosu olmayan hafta kesite girmis"


@pytest.mark.slow
def test_anormal_haftalar_arsivin_tamamindan_hesaplanir():
    """Eşik alt kesitten değil arşivin tamamından — §8'in 32 haftası."""
    anom = karne.anormal_hafta_anahtarlari()
    assert 20 <= len(anom) <= 45, len(anom)
