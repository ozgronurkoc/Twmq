"""Beraberlik düzeltmesi (Ö3, `spor_toto.beraberlik`).

Bulgu **null**: bant terimi sabitin üstüne ölçülebilir bir şey koymuyor.
`test_skor.py` ile aynı gerekçe: testler bulguyu değil **matematiği**
korur. Bozuk bir uydurmanın ürettiği null "bilgi yok" değil "kod yanlış"
demektir; ikisi ayırt edilemezse bulgu da değersizdir.

En kritik test `test_uydurma_bilinen_carpitmayi_geri_bulur`: uydurma
mekanizmasına **bilinen** bir çarpıtma verilip geri bulunup bulunmadığına
bakılır. O test geçmiyorsa null sonucun hiçbir anlamı yoktur.
"""

import math
import random

import pytest

from spor_toto.beraberlik import (
    EN_AZ_MAC,
    BeraberlikTahminci,
    _uydur,
    uygula,
)

SEM = ("1", "0", "2")


def _p(p1: float, p0: float) -> dict[str, float]:
    return {"1": p1, "0": p0, "2": 1.0 - p1 - p0}


# ─── uygula ───────────────────────────────────────────────────────────────

def test_bire_toplar():
    for a, b in ((0.0, 0.0), (0.3, -0.5), (-0.2, 0.4)):
        q = uygula(_p(0.45, 0.27), a, b, 0.5)
        assert sum(q.values()) == pytest.approx(1.0)
        assert all(0.0 < v < 1.0 for v in q.values())


def test_notr_parametreler_degistirmez():
    p = _p(0.45, 0.27)
    q = uygula(p, 0.0, 0.0, 0.5)
    for s in SEM:
        assert q[s] == pytest.approx(p[s])


def test_a_beraberligi_buyutur():
    p = _p(0.45, 0.27)
    assert uygula(p, 0.30, 0.0, 0.5)["0"] > p["0"]
    assert uygula(p, -0.30, 0.0, 0.5)["0"] < p["0"]


def test_taraflarin_kendi_arasindaki_oran_korunur():
    """Hipotez beraberlik hakkında; `1`/`2` tercihine dokunulmamalı."""
    p = _p(0.45, 0.27)
    q = uygula(p, 0.4, -0.3, 0.5)
    assert q["1"] / q["2"] == pytest.approx(p["1"] / p["2"])


def test_egim_favori_gucune_gore_ayrisir():
    """`b < 0`: denk maçta beraberlik artar, açık maçta azalır.

    Ölçülen `b` her dört katlamada da negatif çıktı; testin koruduğu şey
    o işaretin ne anlama geldiği.
    """
    denk = _p(0.40, 0.30)          # f = 0.40, merkezin altında
    acik = _p(0.70, 0.18)          # f = 0.70, merkezin üstünde
    b = -0.25
    assert uygula(denk, 0.0, b, 0.50)["0"] > denk["0"]
    assert uygula(acik, 0.0, b, 0.50)["0"] < acik["0"]


def test_merkezde_egim_etkisizdir():
    p = _p(0.50, 0.27)             # f = 0.50 = c
    q = uygula(p, 0.0, -0.9, 0.50)
    assert q["0"] == pytest.approx(p["0"])


# ─── uydurma ──────────────────────────────────────────────────────────────

def _sentetik(a_ger: float, b_ger: float, c: float, tohum: int,
              n: int = 20000) -> list[tuple[dict[str, float], float, str]]:
    """Piyasa olasılıkları üret, sonuçları ÇARPITILMIŞ gerçekten çek."""
    rng = random.Random(tohum)
    out = []
    for _ in range(n):
        p1 = rng.uniform(0.15, 0.75)
        p0 = rng.uniform(0.18, 0.32)
        if p1 + p0 >= 0.98:
            continue
        p = _p(p1, p0)
        gercek = uygula(p, a_ger, b_ger, c)
        u = rng.random()
        toplam = 0.0
        for s in SEM:
            toplam += gercek[s]
            if u <= toplam:
                out.append((p, max(p.values()), s))
                break
    return out


def _egim(noktalar, a: float, b: float, c: float) -> tuple[float, float]:
    """Log kaybının `(a, b)`'deki gradyanı — düzenlileştirme dahil."""
    from spor_toto.recalibrate import L2

    g_a = g_b = 0.0
    for p, f, kod in noktalar:
        z0 = p["0"] * math.exp(a + b * (f - c))
        q0 = z0 / (z0 + p["1"] + p["2"])
        fark = q0 - (1.0 if kod == "0" else 0.0)
        g_a += fark
        g_b += fark * (f - c)
    return g_a + L2 * a, g_b + L2 * b


def test_uydurma_gercekten_en_az_noktasini_bulur():
    """Gürültüsüz ve kesin kontrol: çözümde gradyan sıfır olmalı.

    Geri bulma testi (aşağıda) örnekleme gürültüsü taşır; bu taşımaz.
    Newton'un doğru fonksiyonu enazladığını **tam olarak** doğrular.
    """
    c = 0.50
    veri = _sentetik(0.25, -0.60, c, tohum=4242)
    a, b = _uydur(veri, c, egimli=True)
    g_a, g_b = _egim(veri, a, b, c)
    assert abs(g_a) < 1e-6
    assert abs(g_b) < 1e-6


def test_uydurma_bilinen_carpitmayi_geri_bulur():
    """Ölçümün tamamı buna dayanır: uydurma çalışmıyorsa null anlamsızdır.

    **`b`'nin toleransı `a`'nınkinden kat kat geniş ve bu tesadüf değil.**
    `b`, `f`'nin yayılımını kaldıraç olarak kullanır; `f` dar bir aralıkta
    (std ≈ 0,10) durduğu için `b`'nin standart hatası `a`'nınkinin ~15
    katıdır. Ö3'ün null çıkmasının bir sebebi de budur: bant terimi, veri
    ona kısa bir kaldıraç verdiği için zaten zor ölçülür.

    Tek tohum yerine **ortalama** alınıyor: tek çekiliş 1–2 standart hata
    sapabilir ve test o sapmayı kod hatası sanardı.
    """
    c, a_ger, b_ger = 0.50, 0.25, -0.60
    ler = [_uydur(_sentetik(a_ger, b_ger, c, tohum=t), c, egimli=True)
           for t in (11, 22, 33, 44, 55, 66)]
    a_ort = sum(x for x, _ in ler) / len(ler)
    b_ort = sum(y for _, y in ler) / len(ler)
    assert a_ort == pytest.approx(a_ger, abs=0.04)
    assert b_ort == pytest.approx(b_ger, abs=0.20)


def test_carpitma_yoksa_sifir_bulunur():
    c = 0.50
    ler = [_uydur(_sentetik(0.0, 0.0, c, tohum=t), c, egimli=True)
           for t in (11, 22, 33, 44, 55, 66)]
    a_ort = sum(x for x, _ in ler) / len(ler)
    b_ort = sum(y for _, y in ler) / len(ler)
    assert a_ort == pytest.approx(0.0, abs=0.04)
    assert b_ort == pytest.approx(0.0, abs=0.20)


def test_egimsiz_kip_b_yi_sifirda_tutar():
    c = 0.50
    a, b = _uydur(_sentetik(0.25, -0.60, c, tohum=4242), c, egimli=False)
    assert b == 0.0
    assert a != 0.0


def test_uydurma_baslangictan_bagimsizdir():
    """Kayıp dışbükey — Newton tek çözüme gitmeli, iki koşum aynı çıkmalı."""
    c = 0.50
    veri = _sentetik(0.25, -0.60, c, tohum=4242)
    u = _uydur(veri, c, egimli=True)
    # Bos donen bir govde de "deterministik" olurdu; asagidaki satir
    # sonucun BOS OLMADIGINI da tutar — determinizm tek basina
    # calistigini kanitlamaz.
    assert u is not None, "uydurma bos dondu"
    assert u == _uydur(veri, c, egimli=True)


# ─── tahminci sözleşmesi ──────────────────────────────────────────────────

def _hafta(n: int = 3) -> dict:
    return {
        "week": 1,
        "results": "10" + "2" * (n - 2),
        "probs": [_p(0.45, 0.27) for _ in range(n)],
    }


def test_egitilmeden_piyasayi_aynen_gecirir():
    """Bilgisizken bir şey uydurmaktansa hiçbir şey yapmamak."""
    t = BeraberlikTahminci()
    h = _hafta()
    for tahmin, p in zip(t.tahmin(h), h["probs"]):
        for s in SEM:
            assert tahmin[s] == pytest.approx(p[s])


def test_az_veriyle_egitim_duzeltme_yapmaz():
    t = BeraberlikTahminci()
    t.egit([_hafta(3)])
    assert not t.egitildi


def test_yeterli_veriyle_egitilir():
    t = BeraberlikTahminci()
    t.egit([_hafta(15) for _ in range(EN_AZ_MAC // 15 + 5)])
    assert t.egitildi
    assert 0.0 < t.c < 1.0


def test_adlar_ayrisir():
    assert BeraberlikTahminci(egimli=True).ad == "beraberlik_bant"
    assert BeraberlikTahminci(egimli=False).ad == "beraberlik_sabit"


def test_eksik_blok_duzgun_dagilima_duser():
    t = BeraberlikTahminci()
    h = {"week": 1, "results": "10", "probs": [None, _p(0.45, 0.27)]}
    out = t.tahmin(h)
    assert out[0]["1"] == pytest.approx(1 / 3)


def test_merkezleme_sabiti_egitimden_gelir():
    """`c` ölçülen haftayı görmemeli — sızıntıya karşı tek savunma."""
    t = BeraberlikTahminci()
    haftalar = [{"week": i, "results": "1" * 15,
                 "probs": [_p(0.60, 0.22) for _ in range(15)]}
                for i in range(40)]
    t.egit(haftalar)
    assert t.c == pytest.approx(0.60, abs=1e-9)


def test_uygulanan_duzeltme_gecerli_olasilik_verir():
    t = BeraberlikTahminci()
    t.egit([_hafta(15) for _ in range(60)])
    for tahmin in t.tahmin(_hafta(15)):
        assert sum(tahmin.values()) == pytest.approx(1.0)
        assert all(v > 0 for v in tahmin.values())


def test_asiri_egim_bile_tasmaz():
    """`math.exp` taşması olasılığa sızmamalı."""
    q = uygula(_p(0.45, 0.27), 50.0, 50.0, 0.0)
    assert sum(q.values()) == pytest.approx(1.0)
    assert not any(math.isnan(v) for v in q.values())
