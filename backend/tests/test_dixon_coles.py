"""Dixon-Coles modelinin denetimi.

İki bekçi ötekilerden önemli:

`test_dc_gelecegi_gormez` — model tur tur yeniden uyduruluyor ve bir turun
maçları kendi tahminlerini üretirken **geçmişe eklenmemiş** olmalı. Sızıntı
burada özellikle sinsidir: aynı haftanın 200 maçı birbirinin sonucunu
görürse güçler o haftaya uyar ve skor mucizevi çıkar.

`test_guclerden_gol_beklentisi_geri_uretilebiliyor` — uydurucunun gerçekten
öğrendiğinin kanıtı. Bilinen güçlerle sentetik bir lig üretilir ve model o
güçleri geri bulmak zorundadır. Bunu yapmıyorsa geri kalan bütün ölçümler
anlamsızdır (`test_recalibrate.test_sistematik_sapmayi_yakalar` ile aynı
mantık).
"""
from __future__ import annotations

import random

import pytest

from spor_toto.dixon_coles import (
    EN_AZ_KESIT,
    LAMBDA_TAVANI,
    MAKS_GOL,
    DixonColes,
    _poisson_vektoru,
    dc_tablosu,
    skor_dagilimindan_1x2,
)
from spor_toto.history import SYMBOLS

TAKIM = [f"T{i:02d}" for i in range(12)]


def _sentetik(n: int = 1200, tohum: int = 11,
              guc: dict[str, float] | None = None) -> list[dict]:
    """Bilinen güçlerle üretilmiş lig. Ev avantajı çarpımsal 1,3."""
    rnd = random.Random(tohum)
    guc = guc or {t: 0.8 + 0.05 * i for i, t in enumerate(TAKIM)}
    maclar: list[dict] = []
    for i in range(n):
        ev, dep = rnd.sample(TAKIM, 2)
        lam = guc[ev] * 1.3
        mu = guc[dep]
        hg = _poisson_ornek(rnd, lam)
        ag = _poisson_ornek(rnd, mu)
        kod = "1" if hg > ag else ("2" if ag > hg else "0")
        gun = 1 + i // 8
        maclar.append({
            "tarih": f"2023-{1 + gun // 28:02d}-{1 + gun % 28:02d}",
            "lig": "E0", "ev": ev, "dep": dep, "kod": kod,
            "ev_gol": hg, "dep_gol": ag, "sezon": "2324",
            "iso_yil": 2023, "iso_hafta": 1 + i // 40,
        })
    return maclar


def _poisson_ornek(rnd: random.Random, lam: float) -> int:
    """Knuth'un yöntemi — sentetik veri için yeterli, bağımlılık eklemez."""
    hedef = pow(2.718281828459045, -lam)
    k, p = 0, 1.0
    while True:
        p *= rnd.random()
        if p <= hedef:
            return k
        k += 1
        if k > 20:
            return k


# ─── Poisson yardımcıları ─────────────────────────────────────────────────

def test_poisson_vektoru_bire_yakin_toplar():
    """Izgara kesmesi gerçekçi `λ`da ihmal edilebilir olmalı.

    Bu testin ilk sürümü `MAKS_GOL = 10` iken düştü: `λ = 3`'te kayıp
    2,9·10⁻⁴ çıktı, oysa docstring "milyonda bir" diyordu. Izgara
    büyütüldü ve **iddia ölçüme çekildi**: `MAKS_GOL` artık 18 ve
    docstring'de kaybın ölçülmüş tablosu duruyor.
    """
    for lam in (0.3, 1.4, 3.0, 4.0):
        assert sum(_poisson_vektoru(lam)) == pytest.approx(1.0, abs=1e-6)
    # Tavanda bile kayip on binde birin altinda kalmali.
    assert sum(_poisson_vektoru(LAMBDA_TAVANI)) > 0.9999


def test_poisson_vektoru_bilinen_degerler():
    p = _poisson_vektoru(1.0)
    assert p[0] == pytest.approx(0.3678794412, abs=1e-9)
    assert p[1] == pytest.approx(0.3678794412, abs=1e-9)
    assert p[2] == pytest.approx(0.1839397206, abs=1e-9)
    assert len(p) == MAKS_GOL + 1


# ─── skor dağılımı → 1X2 ──────────────────────────────────────────────────

def test_1x2_bire_toplar_ve_sinirli():
    for lam, mu, rho in ((1.5, 1.2, 0.0), (2.4, 0.7, -0.05), (0.6, 0.6, 0.1)):
        p = skor_dagilimindan_1x2(lam, mu, rho)
        assert set(p) == set(SYMBOLS)
        assert sum(p.values()) == pytest.approx(1.0, abs=1e-12)
        assert all(0.0 <= v <= 1.0 for v in p.values())


def test_esit_lambda_da_ev_ve_deplasman_simetrik():
    p = skor_dagilimindan_1x2(1.4, 1.4, 0.0)
    assert p["1"] == pytest.approx(p["2"], abs=1e-12)


def test_daha_yuksek_ev_lambdasi_ev_olasiligini_artirir():
    az = skor_dagilimindan_1x2(1.0, 1.2, 0.0)
    cok = skor_dagilimindan_1x2(2.0, 1.2, 0.0)
    assert cok["1"] > az["1"]
    assert cok["2"] < az["2"]


def test_negatif_rho_beraberligi_yukari_iter():
    """Bu parametrizasyonda `ρ < 0`, 0-0 ve 1-1'i yukarı iter.

    Bağımsız Poisson'un bilinen kusuru beraberliği eksik tahmin etmesidir;
    düzeltmenin işe yaraması tam olarak bu yönde olmalıdır. İşaret ters
    yazılırsa model beraberliği daha da azaltır ve kusuru büyütür.
    """
    duz = skor_dagilimindan_1x2(1.3, 1.1, 0.0)
    duzeltilmis = skor_dagilimindan_1x2(1.3, 1.1, -0.05)
    assert duzeltilmis["0"] > duz["0"]


def test_pozitif_rho_beraberligi_asagi_iter():
    duz = skor_dagilimindan_1x2(1.3, 1.1, 0.0)
    duzeltilmis = skor_dagilimindan_1x2(1.3, 1.1, 0.05)
    assert duzeltilmis["0"] < duz["0"]


def test_dusuk_lambdada_beraberlik_yuksek():
    """0-0 olasılığı büyüdükçe beraberlik payı artmalı."""
    dusuk = skor_dagilimindan_1x2(0.6, 0.6, 0.0)
    yuksek = skor_dagilimindan_1x2(2.5, 2.5, 0.0)
    assert dusuk["0"] > yuksek["0"]


# ─── uydurma ──────────────────────────────────────────────────────────────

def test_kucuk_kesitte_uydurmayi_reddeder():
    m = DixonColes()
    assert m.uydur(["A"] * 10, ["B"] * 10, [1] * 10, [0] * 10, [0.0] * 10) is False
    assert m.biliyor("A", "B") is False


def test_uydurulmadan_duzgun_dagilim_doner():
    m = DixonColes()
    p = m.tahmin("A", "B")
    assert all(v == pytest.approx(1 / 3) for v in p.values())


def _uydur(maclar: list[dict]) -> DixonColes:
    m = DixonColes(xi=0.0)  # sonum kapali: sentetik ligde guc sabit
    ok = m.uydur([r["ev"] for r in maclar], [r["dep"] for r in maclar],
                 [r["ev_gol"] for r in maclar], [r["dep_gol"] for r in maclar],
                 [0.0] * len(maclar))
    assert ok
    return m


def test_guclerden_gol_beklentisi_geri_uretilebiliyor():
    """**Uydurucunun kanıtı.** Bilinen güçlerle üretilen ligde güçler geri bulunmalı.

    En güçlü ve en zayıf takımın beklenen gol oranı, üretimde kullanılan
    oranı yakalamalı. Yakalamıyorsa model öğrenmiyordur ve geri kalan
    ölçümler anlamsızdır.
    """
    maclar = _sentetik(n=2400)
    m = _uydur(maclar)
    guclu_lam, _ = m.beklenen_goller(TAKIM[-1], TAKIM[0])
    zayif_lam, _ = m.beklenen_goller(TAKIM[0], TAKIM[-1])
    assert guclu_lam > zayif_lam
    # Uretimde en guclunun hucumu en zayifin ~1,7 katiydi (1.35/0.80).
    assert 1.3 < guclu_lam / zayif_lam < 2.4


def test_ev_avantaji_geri_bulunuyor():
    """Üretimde γ = 1,3; model onu makul bir bantta bulmalı."""
    m = _uydur(_sentetik(n=2400))
    assert 1.1 < m.gamma < 1.6


def test_uydurma_deterministik():
    maclar = _sentetik(n=1200)
    a, b = _uydur(maclar), _uydur(maclar)
    assert a.gamma == pytest.approx(b.gamma, abs=1e-12)
    assert a.rho == pytest.approx(b.rho, abs=1e-9)
    assert a.tahmin(TAKIM[3], TAKIM[7]) == pytest.approx(b.tahmin(TAKIM[3], TAKIM[7]))


def test_bilinmeyen_takimda_duzgun_dagilim():
    m = _uydur(_sentetik())
    assert m.biliyor("YOK", TAKIM[0]) is False
    assert all(v == pytest.approx(1 / 3) for v in m.tahmin("YOK", TAKIM[0]).values())


def test_zaman_sonumu_son_maclara_agirlik_verir():
    """Aynı takım önce kötü sonra iyi oynarsa sönümlü model iyiyi görmeli."""
    rnd = random.Random(3)
    maclar = []
    for i in range(1200):
        ev, dep = rnd.sample(TAKIM, 2)
        # "T00" ilk yarida hic gol atmiyor, ikinci yarida cok atiyor.
        lam = (0.1 if i < 600 else 3.0) if ev == TAKIM[0] else 1.2
        maclar.append((ev, dep, _poisson_ornek(rnd, lam),
                       _poisson_ornek(rnd, 1.2), float(1200 - i)))

    def kur(xi: float) -> float:
        m = DixonColes(xi=xi)
        assert m.uydur([r[0] for r in maclar], [r[1] for r in maclar],
                       [r[2] for r in maclar], [r[3] for r in maclar],
                       [r[4] for r in maclar])
        return m.beklenen_goller(TAKIM[0], TAKIM[1])[0]

    assert kur(0.02) > kur(0.0)


# ─── tablo: sızıntı disiplini ─────────────────────────────────────────────

def test_dc_gelecegi_gormez():
    """**Asıl bekçi.** Bir turun maçları kendi tahminlerini üretirken geçmişte olmamalı.

    Kurgu: son turun maçları elle uydurulan bir modelle karşılaştırılır ve
    o model son turu **hiç görmemiştir**. Tablonun son tur için ürettiği
    olasılık birebir aynı olmalı.
    """
    maclar = _sentetik(n=1600)
    tablo = dc_tablosu(maclar)
    assert tablo[-1]["dc_var"] is True, "kurgu yetersiz — model hic uymamis"

    son_tur = maclar[-1]["iso_hafta"]
    onceki = [r for r in maclar if r["iso_hafta"] < son_tur]
    son = [r for r in maclar if r["iso_hafta"] == son_tur]
    from spor_toto.dixon_coles import _gun
    simdi = max(_gun(r["tarih"]) for r in son)
    m = DixonColes()
    assert m.uydur([r["ev"] for r in onceki], [r["dep"] for r in onceki],
                   [r["ev_gol"] for r in onceki], [r["dep_gol"] for r in onceki],
                   [simdi - _gun(r["tarih"]) for r in onceki])

    hedef = son[-1]
    beklenen = m.tahmin(hedef["ev"], hedef["dep"])
    kayit = tablo[maclar.index(hedef)]
    for s in SYMBOLS:
        assert kayit[f"dc_{s}"] == pytest.approx(beklenen[s], abs=1e-12)


def test_ilk_turlarda_dc_var_kapali():
    """`EN_AZ_KESIT` altındaki turlarda model uydurulmaz; bayrak kapalı."""
    maclar = _sentetik(n=120)
    for kayit in dc_tablosu(maclar):
        assert kayit["dc_var"] is False
        assert kayit["dc_1"] == pytest.approx(1 / 3)
    assert len(maclar) < EN_AZ_KESIT


def test_tablo_girdiyle_ayni_uzunlukta():
    maclar = _sentetik(n=800)
    tablo = dc_tablosu(maclar)
    assert len(tablo) == len(maclar)
    for kayit in tablo:
        assert set(kayit) == {"dc_var", "dc_1", "dc_0", "dc_2"}
        assert sum(kayit[f"dc_{s}"] for s in SYMBOLS) == pytest.approx(1.0, abs=1e-9)


def test_tablo_bos_girdiyle_patlamaz():
    assert dc_tablosu([]) == []


def test_tablo_deterministik():
    maclar = _sentetik(n=800)
    t = dc_tablosu(maclar)
    # Bos donen bir govde de "deterministik" olurdu; asagidaki satir
    # sonucun BOS OLMADIGINI da tutar — determinizm tek basina
    # calistigini kanitlamaz.
    assert t, "tablo bos — determinizm tek basina bir sey kanitlamaz"
    assert t == dc_tablosu(maclar)


def test_golu_olmayan_mac_modele_girmez():
    """Doktrin 2: eksik veri uydurulmaz, elenir.

    Golü olmayan maçlar geçmişe eklenmezse model onları hiç görmez ve
    tahminleri değişmez.
    """
    maclar = _sentetik(n=900)
    kirli = [dict(r) for r in maclar]
    for r in kirli[:50]:
        r["ev_gol"] = None
        r["dep_gol"] = None
    temiz = [r for r in maclar if r not in maclar[:50]]

    a = dc_tablosu(kirli)[-1]
    b = dc_tablosu(temiz)[-1]
    for s in SYMBOLS:
        assert a[f"dc_{s}"] == pytest.approx(b[f"dc_{s}"], abs=1e-9)


# ─── korpus üzerinde ──────────────────────────────────────────────────────

def test_korpusta_dc_makul():
    """Gerçek veride kapsama yüksek ve ortalama tahmin taban orana yakın olmalı."""
    from spor_toto.egitim import korpus_haftalari

    ozellikler = [o for w in korpus_haftalari() for o in w["ozellikler"]]
    var = [o for o in ozellikler if o["dc_var"]]
    assert len(var) / len(ozellikler) > 0.90

    ort = {s: sum(o[f"dc_{s}"] for o in var) / len(var) for s in SYMBOLS}
    assert sum(ort.values()) == pytest.approx(1.0, abs=1e-9)
    # Ev galibiyeti ~%43, beraberlik ~%26, deplasman ~%30 (§5).
    assert 0.38 < ort["1"] < 0.48
    assert 0.20 < ort["0"] < 0.31
    assert 0.26 < ort["2"] < 0.36
