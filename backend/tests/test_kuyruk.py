"""`kuyruk.py` bekçileri — bağımlılık ölçümü ve kuyruk çevirisi.

Ölçümün kendisi yavaştır (korpus ~30 sn + bootstrap); buradaki testler
**mekanizmayı** tutar: bilinen bir cevabı olan girdilerde doğru sayıyı
veriyor mu, ve karar düğüm sayısına bağlı mı.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pytest

from spor_toto.core import SEMBOLLER
from spor_toto.kuyruk import (
    DUGUM,
    KAPSAMA_MODELLERI,
    _kosullu,
    _kosullu_sembol,
    bootstrap,
    hafta_kayitlari,
    kapsama,
    kuyruk,
    kuyruk_etkisi,
    latent_coz,
    olc,
    uretilen_rho,
)
from spor_toto.ortak import kacak_dagilimi


def _hafta(p_favori: list[float], isabet: list[bool]) -> dict:
    """Favorisi `1` olan sentetik hafta."""
    probs, sonuc = [], []
    for p, tuttu in zip(p_favori, isabet):
        kalan = (1.0 - p) / 2.0
        probs.append({"1": p, "0": kalan, "2": kalan})
        sonuc.append("1" if tuttu else "2")
    return {"probs": probs, "results": sonuc}


# ─── ölçüm ────────────────────────────────────────────────────────────────────

def test_bagimsiz_uretilmis_veride_rho_sifira_yakin():
    """Gerçekten bağımsız Bernoulli'lerde `ρ ≈ 0` ve `dagilim ≈ 1`.

    Bu testin tek işi ölçüm makinesinin **kendi tabanını** bulmasıdır: veri
    tanım gereği bağımsızken sıfırdan sapan bir `ρ` çıkarsa, sahadaki
    ölçümün negatif nokta tahmini de anlamsız olurdu.
    """
    rng = random.Random(20260830)
    p = [0.35, 0.45, 0.5, 0.55, 0.6, 0.65, 0.4, 0.5, 0.7, 0.45,
         0.55, 0.6, 0.5, 0.42, 0.58]
    haftalar = [_hafta(p, [rng.random() < x for x in p]) for _ in range(4000)]
    s = olc(hafta_kayitlari(haftalar))

    assert abs(s["rho"]) < 0.01, f"bagimsiz veride rho={s['rho']:+.5f}"
    assert 0.9 < s["dagilim"] < 1.1, f"bagimsiz veride dagilim={s['dagilim']:.3f}"
    assert abs(s["yanlilik"]) < 0.02


def test_ortak_etken_enjekte_edilince_rho_pozitif_cikiyor():
    """Haftaya ortak bir etken konursa ölçüm onu **görmeli**.

    Yokluk iddiasının anlamlı olması için ölçümün varlığı görebildiğini
    göstermek gerekir — `T5` ve `A2`de uygulanan disiplinin aynısı: bir
    null'u yazmadan önce ham sinyalin ölçülebildiği gösterilir.
    """
    rng = random.Random(20260830)
    taban = [0.5] * 15
    haftalar = []
    for _ in range(4000):
        kayma = 0.15 if rng.random() < 0.5 else -0.15   # haftanin ortak etkeni
        haftalar.append(_hafta(taban, [rng.random() < 0.5 + kayma
                                       for _ in taban]))
    s = olc(hafta_kayitlari(haftalar))
    assert s["rho"] > 0.05, f"ortak etken gorulmedi: rho={s['rho']:+.5f}"
    assert s["dagilim"] > 1.5, f"fazla dagilim gorulmedi: {s['dagilim']:.3f}"


def test_yanlilik_rho_ile_karistirilmiyor():
    """Sabit kalibrasyon yanlılığı `ρ`ya sızmamalı.

    İlk koşumda tam bu olmuştu: ham artıklarla kupon kesitinde `ρ = +0,0077`
    çıkıyordu ve tamamı yanlılıktı. Burada veri bağımsız üretiliyor ama
    tahminci sistematik olarak düşük söylüyor; `ρ` yine de sıfırda kalmalı.
    """
    rng = random.Random(20260830)
    gercek, soylenen = 0.60, 0.50
    haftalar = []
    for _ in range(4000):
        h = _hafta([soylenen] * 15, [rng.random() < gercek for _ in range(15)])
        haftalar.append(h)
    s = olc(hafta_kayitlari(haftalar))
    assert s["yanlilik"] == pytest.approx(gercek - soylenen, abs=0.02)
    assert abs(s["rho"]) < 0.01, f"yanlilik rho'ya sizdi: {s['rho']:+.5f}"


def test_bootstrap_araligi_nokta_tahmini_iceriyor():
    rng = random.Random(20260830)
    p = [0.4, 0.5, 0.6] * 5
    kayitlar = hafta_kayitlari(
        [_hafta(p, [rng.random() < x for x in p]) for _ in range(200)])
    s = olc(kayitlar)
    a = bootstrap(kayitlar, tekrar=200, tohum=1)
    assert a["rho"]["alt"] <= s["rho"] <= a["rho"]["ust"]
    assert a["dagilim"]["alt"] <= s["dagilim"] <= a["dagilim"]["ust"]


# ─── kuyruk çevirisi ──────────────────────────────────────────────────────────

def test_a_sifirda_poisson_binomla_birebir_ayni():
    """`a = 0` kuyruk hesabı, `ortak.kacak_dagilimi`nin ta kendisi olmalı.

    Ayrışırlarsa kuponu kuran hesap ile onu değerlendiren hesap farklı şeyler
    söylerdi — `kacak_dagilimi`nin kendi docstring'indeki gerekçe.
    """
    p = [0.35, 0.45, 0.5, 0.55, 0.6, 0.65, 0.4, 0.5, 0.7, 0.45,
         0.55, 0.6, 0.5, 0.42, 0.58]
    d = kacak_dagilimi([1.0 - x for x in p])
    for esik in (10, 12, 14, 15):
        beklenen = sum(d[m] for m in range(0, len(p) - esik + 1))
        assert kuyruk(p, 0.0, esik) == pytest.approx(beklenen, rel=1e-9)


def test_pozitif_bagimlilik_kuyrugu_sismanlatiyor():
    """Modelin yönü: `a` büyüdükçe `P(K≥14)` **artmalı**."""
    p = [0.55] * 15
    onceki = kuyruk(p, 0.0, 14)
    for a in (0.02, 0.05, 0.10, 0.20):
        simdi = kuyruk(p, a, 14)
        assert simdi > onceki, f"a={a} kuyrugu buyutmedi"
        onceki = simdi


def test_latent_coz_hedef_rhoyu_tutturuyor():
    kesit = [[0.4, 0.5, 0.6, 0.55, 0.45] * 3 for _ in range(5)]
    for hedef in (0.005, 0.02, 0.05):
        a = latent_coz(kesit, hedef)
        assert uretilen_rho(kesit, a) == pytest.approx(hedef, rel=0.02)


def test_negatif_rho_kuyrugu_buyutmuyor():
    """Nokta tahmini negatifken model `a = 0`a düşer — oran tam 1 olmalı."""
    kesit = [[0.5] * 15]
    e = kuyruk_etkisi(kesit, -0.02)
    assert e["latent_a"] == 0.0
    for blok in e["esikler"].values():
        assert blok["oran"] == pytest.approx(1.0, rel=1e-12)


def test_dugum_sayisi_karari_degistirmiyor():
    """`DUGUM = 64` ölçüm görülmeden seçildi; kararı taşımadığı burada tutulur.

    32 ile 128 arasında `P(K≥14)` binde birden az oynuyorsa, raporlanan
    oranlar dördünlemenin çözünürlüğüne değil ölçülen `ρ`ya bağlıdır.
    """
    p = [0.35, 0.45, 0.5, 0.55, 0.6, 0.65, 0.4, 0.5, 0.7, 0.45,
         0.55, 0.6, 0.5, 0.42, 0.58]
    taban = kuyruk(p, 0.05, 14, dugum=DUGUM)
    for dugum in (32, 96, 128):
        assert kuyruk(p, 0.05, 14, dugum=dugum) == pytest.approx(taban, rel=1e-3)


def test_esik_mac_sayisini_asarsa_sifir():
    assert kuyruk([0.5] * 3, 0.0, 4) == 0.0


def test_bos_kesit_none_donuyor():
    s = olc([])
    assert s["rho"] is None and s["dagilim"] is None
    assert bootstrap([]) == {}


# ─── sağlama: yayımlanmış sayı ────────────────────────────────────────────────

@pytest.mark.slow
def test_bagimsiz_kuyruk_yayimlanmis_sayiyi_uretiyor():
    """`a = 0`da `P(K≥14)` ≈ 8,6·10⁻⁴ — §6.2'nin bağımsız hesabı.

    İki hesap birbirini tanımıyor: §6.2'nin sayısı tahmincinin kendi
    olasılıklarından elle çıkarılmıştı, buradaki dördünlemeden geliyor.
    Aynı yere düşmeleri makinenin doğru kurulduğunun kanıtıdır.
    """
    from spor_toto.evaluate import kupon_kesiti_tum

    kesit = [k["p"] for k in hafta_kayitlari(kupon_kesiti_tum())]
    t14 = sum(kuyruk(p, 0.0, 14) for p in kesit) / len(kesit)
    assert 7e-4 < t14 < 1.1e-3, f"P(K>=14)={t14:.4e}"
    assert math.isclose(t14, 8.9e-4, rel_tol=0.10)


# ─── kupon kapsaması: aynı bağımlılık, üç sembol ──────────────────────────────

def _kupon(*picks: str):
    """Sembol dizgelerinden kupon: `_kupon("1", "10", "102")`."""
    from spor_toto.coklu import Kupon

    return Kupon(secimler=[list(p) for p in picks],
                 kolon=int(np.prod([len(p) for p in picks])))


def _probs(satirlar: list[tuple[float, float, float]]) -> list[dict[str, float]]:
    return [dict(zip(SEMBOLLER, satir)) for satir in satirlar]


#: Sentetik bir hafta — satır toplamları TAM 1, yani `a = 0` sağlaması
#: normalleştirmeye değil modele bakar.
ONBES_MAC = _probs([
    (0.55, 0.25, 0.20), (0.40, 0.30, 0.30), (0.70, 0.20, 0.10),
    (0.34, 0.33, 0.33), (0.25, 0.30, 0.45), (0.60, 0.25, 0.15),
    (0.45, 0.30, 0.25), (0.50, 0.20, 0.30), (0.38, 0.32, 0.30),
    (0.65, 0.20, 0.15), (0.30, 0.25, 0.45), (0.48, 0.27, 0.25),
    (0.20, 0.30, 0.50), (0.42, 0.28, 0.30), (0.58, 0.22, 0.20),
])


def test_kapsama_marjinalleri_GIRDIYI_veriyor():
    """Model bağımlılığı ekler, **tahmini değiştirmez**.

    `u` üzerinden integre edildiğinde her maçın üç sembol olasılığı girdinin
    ta kendisi olmalı. Olmazsa model sessizce başka bir tahminci kurmuş olur
    ve kapsama sayıları kendi tahmin katmanıyla çelişirdi.
    """
    ham = np.array([[d[s] for s in SEMBOLLER] for d in ONBES_MAC])
    for model in KAPSAMA_MODELLERI:
        for a in (0.0, 0.0011, 0.0166, 0.20):
            w, q = _kosullu_sembol(ONBES_MAC, a, model)
            marj = np.einsum("q,qis->is", w, q)
            assert np.abs(marj - ham).max() < 1e-9, f"{model} a={a}"
            assert np.abs(q.sum(axis=2) - 1.0).max() < 1e-12


def test_kapsama_FAVORI_gostergesi_IKILI_modelin_AYNISI():
    """Üçlü model, favori göstergesinde `_kosullu`nun **birebir aynısı**.

    `ρ → a` çevirisi (`latent_coz`) favori göstergesinden ölçülmüş `ρ` ile
    kalibre edilir (§3.46). Üçlü modelin o göstergede ikili modelle aynı
    eşiği kullanması, ölçülen `a`nın kapsama hesabına **yeniden kalibre
    edilmeden** taşınmasının tek gerekçesidir. Ayrışırlarsa kapsama sayıları
    ölçülmemiş bir `a` ile hesaplanmış olurdu.
    """
    p_fav = [max(d.values()) for d in ONBES_MAC]
    fav_i = [max(range(3), key=lambda j: d[SEMBOLLER[j]]) for d in ONBES_MAC]
    for a in (0.0, 0.0011, 0.0166, 0.20):
        _, ikili = _kosullu(p_fav, a)
        for model in KAPSAMA_MODELLERI:
            _, q = _kosullu_sembol(ONBES_MAC, a, model)
            uclu = np.array([q[:, i, j] for i, j in enumerate(fav_i)]).T
            assert np.abs(uclu - ikili).max() < 1e-12, f"{model} a={a}"


def test_kapsama_a_SIFIRDA_coklu_p_onbes():
    """`a = 0` tam olarak bağımsız hesaptır — iki gövde, tek sayı.

    `coklu.p_onbes` bağımsızlık altında aynı kuponu fiyatlar; ayrışırlarsa
    "bağımlılığın etkisi" diye okunan oranın bir kısmı iki hesabın
    farkından gelirdi.
    """
    from spor_toto.coklu import coklu_plan, p_onbes

    plan = coklu_plan(ONBES_MAC, 3 ** 9, kupon_tavani=81)
    assert kapsama(ONBES_MAC, plan.kuponlar, 0.0) == pytest.approx(
        p_onbes(ONBES_MAC, plan.kuponlar), rel=1e-12)
    assert kapsama(ONBES_MAC, plan.kuponlar, 0.0) == pytest.approx(
        plan.p_onbes, rel=1e-12)


def test_kapsama_BUTUN_kolonlar_oynanirsa_bir():
    """Bütün kolonlar ayrı ayrı oynanırsa toplam olasılık 1 — her `a`da.

    Bu testin tuttuğu şey modelin **tutarlılığıdır**, ve kapsamayı
    kupon başına ikili eşikle hesaplayan (reddedilen) yol tam burada
    düşer: iç içe eşikler eksen maçında üç sembolün toplamını 1 vermez.
    """
    from itertools import product

    probs = _probs([(0.5, 0.3, 0.2), (0.34, 0.33, 0.33), (0.7, 0.2, 0.1)])
    hepsi = [_kupon(*k) for k in product(*[SEMBOLLER] * 3)]
    assert len(hepsi) == 27
    for model in KAPSAMA_MODELLERI:
        for a in (0.0, 0.0166, 0.30):
            assert kapsama(probs, hepsi, a, model) == pytest.approx(1.0,
                                                                   abs=1e-12)


def test_kapsama_AYRIK_kuponlarda_toplaniyor():
    """Ayrık kuponların kapsaması toplanır — `a > 0`da da.

    `coklu.p_onbes`in gerekçesi bağımlılıkta da geçerli olmalı: koşullu
    bağımsızlık altında toplam `u` içinde toplanır, dördünleme dışta durur.
    """
    probs = _probs([(0.5, 0.3, 0.2), (0.4, 0.35, 0.25), (0.6, 0.25, 0.15)])
    bir, iki = _kupon("1", "10", "12"), _kupon("0", "10", "12")
    for model in KAPSAMA_MODELLERI:
        for a in (0.0, 0.0166, 0.30):
            assert (kapsama(probs, [bir, iki], a, model)
                    == pytest.approx(kapsama(probs, [bir], a, model)
                                     + kapsama(probs, [iki], a, model),
                                     rel=1e-12))


def test_kapsama_pozitif_bagimlilik_FAVORI_kolonunu_sismanlatiyor():
    """Yön: tek favori kolonu `a` büyüdükçe **daha olası** olmalı.

    `kuyruk`un `P(K≥14)` yönünün kapsama tarafındaki karşılığı; ters çıkarsa
    ölçülen oranlar da ters işaretli okunurdu.
    """
    favori = _kupon(*[max(d, key=lambda s: d[s]) for d in ONBES_MAC])
    for model in KAPSAMA_MODELLERI:
        onceki = kapsama(ONBES_MAC, [favori], 0.0, model)
        for a in (0.01, 0.05, 0.20):
            simdi = kapsama(ONBES_MAC, [favori], a, model)
            assert simdi > onceki, f"{model} a={a} kapsamayi buyutmedi"
            onceki = simdi


def test_kapsama_IKI_model_a_sifirda_ayni_buyudukce_ayrisiyor():
    """`ρ` 2.↔3. sembol paylaşımını belirlemez; iki uç ayrı ayrı ölçülür.

    `a = 0`da ikisi aynı sayıyı vermeli (fark modelden değil `a`dan gelir),
    `a > 0`da ayrışmalı — ayrışmasalar iki modeli ayrı ayrı raporlamak
    gereksiz olurdu ve bunu ölçüm söyler.
    """
    from spor_toto.coklu import coklu_plan

    plan = coklu_plan(ONBES_MAC, 3 ** 9, kupon_tavani=81)
    r0 = kapsama(ONBES_MAC, plan.kuponlar, 0.0, "rutbe")
    o0 = kapsama(ONBES_MAC, plan.kuponlar, 0.0, "oransal")
    assert r0 == pytest.approx(o0, rel=1e-12)
    r1 = kapsama(ONBES_MAC, plan.kuponlar, 0.05, "rutbe")
    o1 = kapsama(ONBES_MAC, plan.kuponlar, 0.05, "oransal")
    assert r1 != pytest.approx(o1, rel=1e-6)


def test_kapsama_dugum_sayisi_karari_degistirmiyor():
    """`DUGUM = 64` kapsama tarafında da kararı taşımıyor."""
    from spor_toto.coklu import coklu_plan

    plan = coklu_plan(ONBES_MAC, 3 ** 9, kupon_tavani=81)
    taban = kapsama(ONBES_MAC, plan.kuponlar, 0.0166, dugum=DUGUM)
    for dugum in (32, 96, 128):
        assert kapsama(ONBES_MAC, plan.kuponlar, 0.0166,
                       dugum=dugum) == pytest.approx(taban, rel=1e-6)


def test_kapsama_bilinmeyen_model_hata_veriyor():
    with pytest.raises(ValueError, match="kapsama modeli"):
        kapsama(ONBES_MAC, [_kupon(*["1"] * 15)], 0.01, model="yok")


def test_kapsama_eksik_mac_sayisi_hata_veriyor():
    """Kupon ile olasılık listesi ayrışırsa sessizce yanlış sayı çıkmaz."""
    with pytest.raises(ValueError, match="macin secimini"):
        kapsama(ONBES_MAC, [_kupon("1", "0")], 0.01)
