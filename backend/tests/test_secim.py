"""Hedefe göre işaret seçimi (`spor_toto.secim`).

Buradaki testler iki şeyi korur: **aritmetiği** (kaçak olasılığı, bedel,
hedef) ve **optimizasyonun gerçekten optimal olduğunu**. İkincisi kritik:
Pareto budaması "yaklaşık" olsaydı sessizce daha kötü kupon kurardı ve
hiçbir şey patlamazdı — o yüzden küçük vakalarda kaba kuvvetle
karşılaştırılıyor.
"""

from itertools import product

import pytest

from spor_toto.core import HAMMING_BLOK_BOYU, Fix16Hatasi, solve_fix16
from spor_toto.ortak import kacak_dagilimi
from spor_toto.secim import (
    VARSAYILAN_KACAK_ESIGI,
    bedel_hesapla,
    en_iyi_secim,
    hedef_olasiligi,
    kacak_olasiligi,
)

SEM = ("1", "0", "2")


def p(bir: float, sifir: float, iki: float) -> dict[str, float]:
    t = bir + sifir + iki
    return {"1": bir / t, "0": sifir / t, "2": iki / t}


def hafta(n: int = 15) -> list[dict[str, float]]:
    """Çeşitli şekilli 15 maç — hepsi aynı olsaydı seçim de sıkıcı olurdu."""
    sekiller = [
        (0.80, 0.12, 0.08), (0.45, 0.30, 0.25), (0.34, 0.33, 0.33),
        (0.55, 0.25, 0.20), (0.40, 0.35, 0.25), (0.70, 0.18, 0.12),
        (0.38, 0.32, 0.30), (0.60, 0.22, 0.18), (0.50, 0.28, 0.22),
        (0.33, 0.34, 0.33), (0.65, 0.20, 0.15), (0.42, 0.31, 0.27),
        (0.48, 0.29, 0.23), (0.75, 0.15, 0.10), (0.36, 0.33, 0.31),
    ]
    return [p(*sekiller[i % len(sekiller)]) for i in range(n)]


# ─── aritmetik ────────────────────────────────────────────────────────────

def test_uclu_asla_kacmaz():
    """Yapının tamamı bu olguya dayanıyor; kırılırsa optimizasyon çöker."""
    for m in hafta():
        assert kacak_olasiligi(m, 3) == pytest.approx(0.0, abs=1e-12)


def test_kacak_olasiligi_seviyeyle_azalir():
    for m in hafta():
        assert kacak_olasiligi(m, 1) >= kacak_olasiligi(m, 2)
        assert kacak_olasiligi(m, 2) >= kacak_olasiligi(m, 3)


def test_cifte_kacagi_en_dusuk_sembolun_olasiligidir():
    m = p(0.50, 0.30, 0.20)
    assert kacak_olasiligi(m, 2) == pytest.approx(0.20)


def test_bedel_formulu_fix16_ile_uyusuyor():
    """Bedel formülü motorun gerçekten ürettiği kolon sayısını vermeli.

    Formül `2^a·3^b/2⁷·16`; motor `solve_fix16`. İkisi ayrışırsa bütçe
    kısıtı yalan söyler ve optimizasyon karşılayamayacağı planlar seçer.
    """
    from spor_toto.core import Encoder

    for cift, uclu in ((7, 0), (8, 0), (7, 1), (9, 2), (10, 0)):
        banko = 15 - cift - uclu
        secimler = ([["1"]] * banko + [["1", "0"]] * cift
                    + [["1", "0", "2"]] * uclu)
        enc = Encoder([list(s) for s in secimler])
        cols, _ = solve_fix16(enc)
        assert len(cols) == bedel_hesapla(cift, uclu), (cift, uclu)


def test_hedef_olasiligi_kacak_dagilimiyla_tutarli():
    maclar = hafta()
    secimler = [["1", "0"]] * 15
    q = [1 - sum(m[s] for s in sec) for m, sec in zip(maclar, secimler)]
    assert hedef_olasiligi(maclar, secimler) == pytest.approx(
        sum(kacak_dagilimi(q)[:3]))


def test_hepsi_uclu_ise_hedef_kesindir():
    maclar = hafta()
    assert hedef_olasiligi(maclar, [list(SEM)] * 15) == pytest.approx(1.0)


# ─── optimizasyon ─────────────────────────────────────────────────────────

def _kaba_kuvvet(maclar, butce, esik=VARSAYILAN_KACAK_ESIGI):
    """Küçük vakada TÜM atamaları gezip en iyisini bulur — referans."""
    n = len(maclar)
    sirali = [sorted(m.items(), key=lambda kv: (-kv[1], SEM.index(kv[0])))
              for m in maclar]
    en = None
    for seviyeler in product((1, 2, 3), repeat=n):
        cift = sum(1 for s in seviyeler if s == 2)
        uclu = sum(1 for s in seviyeler if s == 3)
        if cift < HAMMING_BLOK_BOYU:
            continue
        c = bedel_hesapla(cift, uclu)
        if c > butce:
            continue
        secimler = [[s for s, _ in sirali[i][:seviyeler[i]]] for i in range(n)]
        deger = hedef_olasiligi(maclar, secimler, esik)
        if en is None or (deger, -c) > (en[0], -en[1]):
            en = (deger, c)
    return en


@pytest.mark.parametrize("butce", [2048, 4096, 8192, 16384])
def test_optimizasyon_gercekten_optimal(butce):
    """Pareto budaması KESİN olmalı — kaba kuvvetle birebir aynı değer.

    Budama yaklaşık olsaydı sessizce daha kötü kupon kurardı ve hiçbir yer
    patlamazdı; bu testin varlık sebebi tam olarak o sessizlik.
    """
    maclar = hafta(9)          # 3^9 = 19.683 atama — kaba kuvvet mümkün
    beklenen = _kaba_kuvvet(maclar, butce)
    bulunan = en_iyi_secim(maclar, butce)
    if beklenen is None:
        assert bulunan is None
        return
    assert bulunan is not None
    assert bulunan.p_hedef == pytest.approx(beklenen[0], rel=1e-12)
    assert bulunan.bedel == beklenen[1]


def test_optimizasyon_esik_kuralini_geciyor():
    """Asıl iddia: aynı bütçede eşik kuralından daha iyi hedef."""
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU, secim_uret

    maclar = hafta()
    eski = [secim_uret(m, VARSAYILAN_BANKO, VARSAYILAN_UCLU) for m in maclar]
    cift = sum(1 for s in eski if len(s) == 2)
    uclu = sum(1 for s in eski if len(s) == 3)
    if cift < HAMMING_BLOK_BOYU:
        pytest.skip("bu sentetik haftada esik kurali fix16 kuramiyor")
    butce = bedel_hesapla(cift, uclu)
    yeni = en_iyi_secim(maclar, butce)
    assert yeni is not None
    assert yeni.bedel <= butce
    assert yeni.p_hedef >= hedef_olasiligi(maclar, eski)


def test_butce_kisiti_asilmaz():
    maclar = hafta()
    for butce in (16, 64, 256, 1024, 4096):
        s = en_iyi_secim(maclar, butce)
        if s is None:
            continue
        assert s.bedel <= butce
        assert bedel_hesapla(s.cift, s.uclu) == s.bedel


def test_yedi_cifte_kisiti_korunur():
    """`solve_fix16` yedi çifteden azını kabul etmez; plan bunu taşımalı."""
    from spor_toto.core import Encoder

    maclar = hafta()
    for butce in (16, 128, 2048, 32768):
        s = en_iyi_secim(maclar, butce)
        if s is None:
            continue
        assert s.cift >= HAMMING_BLOK_BOYU
        # Motor gerçekten kurabilmeli — kısıt kâğıt üzerinde kalmasın.
        solve_fix16(Encoder([list(x) for x in s.secimler]))


def test_butce_buyudukce_hedef_kotulesmez():
    maclar = hafta()
    onceki = -1.0
    for butce in (16, 128, 1024, 8192, 65536):
        s = en_iyi_secim(maclar, butce)
        if s is None:
            continue
        assert s.p_hedef >= onceki - 1e-12
        onceki = s.p_hedef


def test_cok_kucuk_butce_none_doner():
    """Yedi çiftenin bedeli 16 kolondur; altında kurulacak plan yok."""
    assert en_iyi_secim(hafta(), 8) is None


def test_gecersiz_butce_reddedilir():
    with pytest.raises(ValueError, match="pozitif"):
        en_iyi_secim(hafta(), 0)


def test_bos_hafta_none_doner():
    assert en_iyi_secim([], 1024) is None


def test_esik_buyurse_hedef_kotulesmez():
    """`P(k ≤ 3)` her zaman `P(k ≤ 2)`'den büyük ya da eşittir."""
    maclar = hafta()
    dar = en_iyi_secim(maclar, 4096, esik=2)
    genis = en_iyi_secim(maclar, 4096, esik=3)
    assert dar is not None and genis is not None
    assert genis.p_hedef >= dar.p_hedef


def test_secimler_en_olasi_sembollerden_kurulur():
    """Bir maçta `L` sembol işaretleniyorsa, o `L` en olasılıklı olanlardır.

    Aksi bir seçim aynı bedele daha düşük hedef alırdı; testin işi bunun
    kodda da böyle olduğunu çivilemek.
    """
    maclar = hafta()
    s = en_iyi_secim(maclar, 8192)
    assert s is not None
    for m, sec in zip(maclar, s.secimler):
        sirali = sorted(m, key=lambda k: (-m[k], SEM.index(k)))
        assert set(sec) == set(sirali[:len(sec)])


def test_bilinen_haftada_uclu_pahali_olduğunda_secilmez():
    """Bütçe darsa üçlü (×3) yerine çifte (×2) tercih edilmeli."""
    maclar = [p(0.50, 0.30, 0.20)] * 15
    dar = en_iyi_secim(maclar, 16)         # yalnizca 7 cifte + 8 banko sigar
    assert dar is not None
    assert dar.uclu == 0
    assert dar.cift == HAMMING_BLOK_BOYU


def test_fix16_kurulamayan_plan_uretilmez():
    """Üretilen her plan motorda gerçekten çözülebilmeli."""
    from spor_toto.core import Encoder

    for butce in (16, 48, 512, 6144, 49152):
        s = en_iyi_secim(hafta(), butce)
        if s is None:
            continue
        try:
            cols, _ = solve_fix16(Encoder([list(x) for x in s.secimler]))
        except Fix16Hatasi as e:  # pragma: no cover - kirilirsa test patlar
            pytest.fail(f"butce {butce}: plan cozulemedi — {e}")
        assert len(cols) == s.bedel
