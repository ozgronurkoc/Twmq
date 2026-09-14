"""`bilgi_esnekligi.py` ve serbest küme **tavanı** için bekçiler.

Bu dosyanın koruduğu iddia tek cümledir ve projenin en büyük iddiası:

> Kombinatorik eksenin bir TAVANI vardır ve bugünkü plan ona yakındır;
> geriye kalan pay **bilgide**dir.

Tavan cümlesi yanlışsa (ör. bir plan tavanı geçerse) o cümle çöker, yani
bekçi burada bir sayıyı değil bir **hükmü** tutuyor.
"""
from __future__ import annotations

import pytest

from scripts.bilgi_esnekligi import _ac, _brier, _karistir
from scripts.tahsis_kiyasi import kolon_p, serbest_kume
from spor_toto.coklu import MAC_SAYISI, coklu_plan_serisi
from spor_toto.core import SEMBOLLER


def _hafta(p_favori: float = 0.55) -> list[dict[str, float]]:
    """On beş maçlık sentetik hafta — favori `1`, kalan eşit bölünür."""
    kalan = (1.0 - p_favori) / 2
    return [{"1": p_favori, "0": kalan, "2": kalan}
            for _ in range(MAC_SAYISI)]


def _gercek(kacak: int = 0) -> list[str]:
    """Gerçek kolon: ilk `kacak` maçta favori dışına çıkar."""
    return ["0" if i < kacak else "1" for i in range(MAC_SAYISI)]


def test_serbest_kume_HICBIR_plan_tarafindan_gecilemez():
    """Tavan iddiası: aynı bütçede hiçbir kupon ailesi tavanı geçemez."""
    probs = _hafta()
    butce = 2_000
    tavan, _esik = serbest_kume(probs, butce)
    seri = coklu_plan_serisi(probs, butce, (1, 27, 81))
    for t, plan in seri.items():
        assert plan.p_onbes <= tavan + 1e-12, (
            f"tavan {t} kuponluk planla asildi: {plan.p_onbes} > {tavan}")


def test_serbest_kume_esigi_gercek_kolonun_uyeligini_dogru_soyler():
    """Eşik bir üyelik sınavıdır; en olası kolon her zaman içeride."""
    probs = _hafta()
    _toplam, esik = serbest_kume(probs, 100)
    # Hepsi favori: tanım gereği en olası kolon, 100 kolonluk kümede.
    assert kolon_p(probs, _gercek(0)) >= esik
    # Altı kaçak: bu hafta ailesinde 100 kolonun çok dışında.
    assert kolon_p(probs, _gercek(6)) < esik


def test_kolon_p_NORMALLESMEMIS_girdide_de_ayni():
    """§3.70'in dersi: ham sözlükten çarpmak binde birler kaydırır."""
    probs = _hafta()
    ham = [{s: v * 1.0001 for s, v in d.items()} for d in probs]
    assert kolon_p(ham, _gercek(0)) == pytest.approx(
        kolon_p(probs, _gercek(0)), rel=1e-12)


def test_serbest_kume_butce_buyudukce_DUSMEZ():
    probs = _hafta()
    onceki = 0.0
    for butce in (10, 100, 1_000, 10_000):
        simdi, _e = serbest_kume(probs, butce)
        assert simdi >= onceki - 1e-15
        onceki = simdi


def test_ac_k_buyudukce_tavan_DUSMEZ():
    """Daha çok kesin bilgi hedefi düşüremez — eğrinin monotonluğu."""
    probs, gercek = _hafta(), _gercek(2)
    onceki = 0.0
    for k in (0, 1, 2, 3):
        p, _e = serbest_kume(_ac(probs, gercek, k), 1_000)
        assert p >= onceki - 1e-15
        onceki = p


def test_ac_EN_BELIRSIZ_maci_secer():
    """Kâhin seçimi: açılan maç favori olasılığı en küçük olandır."""
    probs = _hafta()
    probs[7] = {"1": 0.34, "0": 0.33, "2": 0.33}  # en belirsiz
    gercek = _gercek(0)
    acik = _ac(probs, gercek, 1)
    assert acik[7] == {s: (1.0 if s == gercek[7] else 0.0) for s in SEMBOLLER}
    assert acik[0] == probs[0]


def test_karistir_uclari_dogru():
    probs, gercek = _hafta(), _gercek(3)
    assert _karistir(probs, gercek, 0.0) == probs
    tam = _karistir(probs, gercek, 1.0)
    assert all(d[gercek[i]] == pytest.approx(1.0) for i, d in enumerate(tam))


def test_karistir_Brieri_MONOTON_iyilestirir():
    """`λ` gerçek bilgidir; Brier'i kötüleştiremez."""
    probs, gercek = _hafta(), _gercek(4)
    onceki = _brier(probs, gercek)
    for lam in (0.01, 0.05, 0.10, 0.5):
        simdi = _brier(_karistir(probs, gercek, lam), gercek)
        assert simdi <= onceki + 1e-15
        onceki = simdi


def test_brier_esit_dagilimda_bilinen_degeri_verir():
    """Sağlama: üç sembole 1/3 vermek 2/3 eder."""
    esit = [{s: 1 / 3 for s in SEMBOLLER} for _ in range(MAC_SAYISI)]
    assert _brier(esit, _gercek(0)) == pytest.approx(2 / 3)


def test_zamanlama_izgarasi_TAM_YIGILMAYI_iceriyor():
    """Yığma ekseni ölçülerek kapandı; ızgara yeniden budanırsa açılır.

    §3.77: Mandel'in kuralının ikinci yarısı *"doğru çekilişe yığ"*dır ve
    ızgara 4 katta kesildiği sürece kâhin o seçeneği **göremez**. Ölçüm
    ancak pencerenin tamamı (13 kat) ızgaradaysa bir şey söyler; söylediği
    de şu oldu: kâhin yeni basamakları bir kez bile kullanmadı.

    Bu bekçi bir sayıyı değil, **sorunun sorulmuş olmasını** tutuyor.
    """
    from scripts.ufuk_kiyasi import ZAMANLAMA_IZGARASI
    from spor_toto.ufuk import UFUK_HAFTA

    assert max(ZAMANLAMA_IZGARASI) >= UFUK_HAFTA, (
        f"izgara {max(ZAMANLAMA_IZGARASI)} katta kesiliyor; pencerenin "
        f"tamamini ({UFUK_HAFTA}) tek haftaya yigmak secenek disi kaldi")
    assert 0.0 in ZAMANLAMA_IZGARASI, "'bu haftayi oynama' secenegi kayboldu"
