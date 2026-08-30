"""`kuyruk.py` bekçileri — bağımlılık ölçümü ve kuyruk çevirisi.

Ölçümün kendisi yavaştır (korpus ~30 sn + bootstrap); buradaki testler
**mekanizmayı** tutar: bilinen bir cevabı olan girdilerde doğru sayıyı
veriyor mu, ve karar düğüm sayısına bağlı mı.
"""

from __future__ import annotations

import math
import random

import pytest

from spor_toto.kuyruk import (
    DUGUM,
    bootstrap,
    hafta_kayitlari,
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
