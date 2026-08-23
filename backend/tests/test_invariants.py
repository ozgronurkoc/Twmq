"""
Rastgele uretilmis kuponlar uzerinde degismez (invariant) testleri.

Buradaki testler tek tek senaryolari degil, HER kupon icin gecerli olmasi
gereken kurallari dogrular. Amac, elle dusunulmemis girdi bicimlerinde de
hata cikmamasi.
"""

import math
import random
from itertools import product

import pytest

from spor_toto.core import (
    Encoder,
    Fix16Hatasi,
    ball,
    distance_layers,
    dogrula_kaplama,
    hamming,
    merge_rows,
    olasilik_raporu,
    parse_picks,
    parse_probs,
    row_cost,
    rows_to_points,
    solve_by_blocks,
    solve_fix16,
)
from spor_toto.report import (
    dagilim_satirlari,
    kolon_metni,
    olasilik_satirlari,
    satir_metni,
    yazdir_ve_kaydet,
)

SEMBOL_KUMELERI = [
    ["1"], ["0"], ["2"],
    ["1", "0"], ["1", "2"], ["0", "2"],
    ["1", "0", "2"],
]


def rastgele_kupon(rng: random.Random, en_az_cifte: int = 0) -> list:
    """15 maclik rastgele bir kupon uretir."""
    while True:
        kupon = [list(rng.choice(SEMBOL_KUMELERI)) for _ in range(15)]
        cifte = sum(1 for s in kupon if len(s) == 2)
        if cifte >= en_az_cifte:
            # Uzayin makul kalmasi icin ust sinir koy
            if math.prod(len(s) for s in kupon) <= 200_000:
                return kupon


def kaplama_gecerli(cols, sizes):
    worst, acik = dogrula_kaplama(cols, sizes)
    return worst <= 1 and acik == 0


# ------------------------------------------------------------
# fix16 degismezleri
# ------------------------------------------------------------

@pytest.mark.parametrize("tohum", range(40))
def test_fix16_degismezleri(tohum):
    rng = random.Random(tohum)
    kupon = rastgele_kupon(rng, en_az_cifte=7)
    enc = Encoder(kupon)
    cols, aciklama = solve_fix16(enc)
    sizes = enc.alphabet_sizes

    # 1) Her zaman 16 satir
    rows = merge_rows(cols)
    assert len(rows) == 16, (kupon, aciklama)

    # 2) 14-garanti bozulmamis
    assert kaplama_gecerli(cols, sizes), kupon

    # 3) Sikistirma kayipsiz ve bedeli degistirmiyor
    assert set(rows_to_points(rows)) == set(cols)
    assert sum(row_cost(r) for r in rows) == len(cols)

    # 4) Bedel = 16 x (blok disi seceneklerin carpimi)
    kalan = list(sizes)
    for _ in range(7):
        kalan.remove(2)
    assert len(cols) == 16 * math.prod(kalan)

    # 5) Kolonlar tekil ve uzay icinde
    assert len(set(cols)) == len(cols)
    for c in cols:
        assert len(c) == len(sizes)
        assert all(0 <= v < k for v, k in zip(c, sizes))

    # 6) Hicbir zaman tam sistemden pahali olamaz
    assert len(cols) <= enc.space_size()

    # 7) Alt sinirin altina inemez
    assert len(cols) >= enc.lower_bound()


@pytest.mark.parametrize("tohum", range(15))
def test_fix16_varyantlar_degismezleri(tohum):
    rng = random.Random(1000 + tohum)
    enc = Encoder(rastgele_kupon(rng, en_az_cifte=7))
    kanonik, _ = solve_fix16(enc, variant=0)
    for v in (1, 2, 3, 7):
        cols, _ = solve_fix16(enc, variant=v)
        assert len(cols) == len(kanonik)          # bedel degismez
        assert len(merge_rows(cols)) == 16        # satir degismez
        assert kaplama_gecerli(cols, enc.alphabet_sizes)


@pytest.mark.parametrize("tohum", range(20))
def test_7_cifteden_az_her_zaman_reddedilir(tohum):
    rng = random.Random(5000 + tohum)
    while True:
        kupon = [list(rng.choice(SEMBOL_KUMELERI)) for _ in range(15)]
        if sum(1 for s in kupon if len(s) == 2) < 7:
            break
    with pytest.raises(Fix16Hatasi):
        solve_fix16(Encoder(kupon))


# ------------------------------------------------------------
# Blok motoru degismezleri
# ------------------------------------------------------------

@pytest.mark.parametrize("tohum", range(25))
def test_blok_motoru_degismezleri(tohum):
    rng = random.Random(2000 + tohum)
    kupon = rastgele_kupon(rng)
    enc = Encoder(kupon)
    if enc.n == 0:
        assert solve_by_blocks(enc) is None
        return
    sonuc = solve_by_blocks(enc)
    assert sonuc is not None
    cols, _ = sonuc
    assert kaplama_gecerli(cols, enc.alphabet_sizes)
    assert enc.lower_bound() <= len(cols) <= enc.space_size()
    assert len(set(cols)) == len(cols)


@pytest.mark.parametrize("tohum", range(15))
def test_blok_fix16den_asla_pahali_degil(tohum):
    rng = random.Random(3000 + tohum)
    enc = Encoder(rastgele_kupon(rng, en_az_cifte=7))
    blok, _ = solve_by_blocks(enc)
    f16, _ = solve_fix16(enc)
    assert len(blok) <= len(f16)


# ------------------------------------------------------------
# Geometri ve sayim degismezleri
# ------------------------------------------------------------

@pytest.mark.parametrize("tohum", range(30))
def test_distance_layers_toplami_uzay_boyutu(tohum):
    rng = random.Random(4000 + tohum)
    sizes = tuple(rng.choice([2, 3]) for _ in range(rng.randint(1, 6)))
    space = list(product(*[range(k) for k in sizes]))
    cols = rng.sample(space, rng.randint(1, len(space)))
    dist = distance_layers(cols, sizes)
    assert sum(dist.values()) == len(space)
    assert dist[0] == len(set(cols))
    # katmanlar bosluksuz olmali: d varsa d-1 de var
    for d in dist:
        if d > 0:
            assert d - 1 in dist


@pytest.mark.parametrize("tohum", range(30))
def test_kaplama_ve_mesafe_tutarli(tohum):
    rng = random.Random(6000 + tohum)
    sizes = tuple(rng.choice([2, 3]) for _ in range(rng.randint(1, 5)))
    space = list(product(*[range(k) for k in sizes]))
    cols = rng.sample(space, rng.randint(1, len(space)))
    _worst, acik = dogrula_kaplama(cols, sizes)
    dist = distance_layers(cols, sizes)
    if acik == 0:
        assert max(dist) <= 1
    else:
        assert max(dist) >= 2
        assert sum(v for d, v in dist.items() if d >= 2) == acik


@pytest.mark.parametrize("tohum", range(20))
def test_ball_ve_hamming_tutarli(tohum):
    rng = random.Random(7000 + tohum)
    sizes = tuple(rng.choice([2, 3]) for _ in range(rng.randint(1, 6)))
    space = list(product(*[range(k) for k in sizes]))
    for p in rng.sample(space, min(30, len(space))):
        b = set(ball(p, sizes))
        assert b == {q for q in space if hamming(p, q) <= 1}


# ------------------------------------------------------------
# Belirlenimcilik
# ------------------------------------------------------------

@pytest.mark.parametrize("tohum", range(10))
def test_ayni_girdi_ayni_cikti(tohum):
    rng = random.Random(8000 + tohum)
    kupon = rastgele_kupon(rng, en_az_cifte=7)
    a, _ = solve_fix16(Encoder(kupon))
    b, _ = solve_fix16(Encoder(kupon))
    assert a == b
    assert merge_rows(a) == merge_rows(b)


# ------------------------------------------------------------
# Olasilik degismezleri
# ------------------------------------------------------------

@pytest.mark.parametrize("tohum", range(20))
def test_olasilik_degismezleri(tohum):
    rng = random.Random(9000 + tohum)
    kupon = rastgele_kupon(rng, en_az_cifte=7)
    enc = Encoder(kupon)
    cols, _ = solve_fix16(enc)
    probs = [{s: rng.random() + 0.01 for s in ("1", "0", "2")} for _ in range(15)]
    for p in probs:
        t = sum(p.values())
        for k in p:
            p[k] /= t
    rap = olasilik_raporu(enc, cols, probs)
    assert 0.0 <= rap.p_15 <= 1.0
    assert 0.0 <= rap.p_kume_ici <= 1.0
    assert 0.0 <= rap.p_14 <= 1.0
    # kaplama gecerli oldugundan 15 + 14 tam olarak kume-ici olasiligina esit
    assert rap.p_15 + rap.p_14 == pytest.approx(rap.p_kume_ici, rel=1e-9)
    # En olasi TEK kolon, tum kume-ici olasiliktan buyuk olamaz.
    # (p_15 >= p_tek_kolon_15 DOGRU DEGILDIR: kaplama kodu 15 sansini
    #  degil kapsamayi maksimize eder, en olasi nokta kolonlar arasinda
    #  olmayabilir.)
    assert rap.p_tek_kolon_15 <= rap.p_kume_ici + 1e-12


# ------------------------------------------------------------
# Raporlama
# ------------------------------------------------------------

def test_yazdir_ve_kaydet_ozeti(tmp_path, capsys):
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols, _ = solve_fix16(enc)
    hedef = tmp_path / "c.txt"
    ozet = yazdir_ve_kaydet(enc, cols, "test", str(hedef), ["not"], tam_liste=False)
    assert ozet["satir"] == 16
    assert ozet["bedel"] == 32
    assert ozet["en_kotu"] == 1
    assert ozet["acik"] == 0
    assert hedef.exists()
    capsys.readouterr()


def test_yazdir_ve_kaydet_bozuk_sikistirmayi_yakalar(monkeypatch, capsys):
    """Sikistirma kayipli hale gelirse rapor sessizce gecmemeli."""
    import spor_toto.report as rp
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols, _ = solve_fix16(enc)
    monkeypatch.setattr(rp, "merge_rows", lambda c, **kw: rp.merge_rows.__wrapped__(c)
                        if False else [tuple(frozenset([v]) for v in cols[0])])
    with pytest.raises(AssertionError):
        rp.yazdir_ve_kaydet(enc, cols, "test", None, tam_liste=False)
    capsys.readouterr()


def test_rapor_metin_yardimcilari():
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols, _ = solve_fix16(enc)
    rows = merge_rows(cols)
    m = satir_metni(enc, rows[0])
    assert len(m.split()) == 15
    assert "01" not in m.replace(" ", ",")      # kupon duzeni korunmali
    k = kolon_metni(enc, cols[0])
    assert len(k.split()) == 15
    satirlar = dagilim_satirlari(enc, cols)
    assert any("14-GARANTI DOGRULANDI" in s for s in satirlar)


def test_dagilim_satirlari_acik_varsa_uyarir():
    enc = Encoder(parse_picks("10,10,10,10,10,1,1,1,1,1,1,1,1,1,1"))
    satirlar = dagilim_satirlari(enc, [(0, 0, 0, 0, 0)])
    assert any("14-GARANTI YOK" in s for s in satirlar)


def test_olasilik_satirlari_bicimi():
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols, _ = solve_fix16(enc)
    probs = parse_probs(";".join(["1:1,0:1,2:1"] * 15), enc.selections)
    satirlar = olasilik_satirlari(olasilik_raporu(enc, cols, probs))
    assert any("kar/beklenen-deger hesabi degildir" in s for s in satirlar)


# ─── bağımsızlık varsayımı ────────────────────────────────────────────────────

def test_bagimsizlik_varsayimi_hafta_duzeyinde_tutuyor():
    """`P(≥12)`, `p_kume_ici`, Poisson-binom — hepsi 15 maçın bağımsızlığına
    dayanıyor ve bu varsayım hiç sınanmamıştı.

    Sınama: haftalık favori isabetinin **gözlenen** varyansı, bağımsızlığın
    öngördüğü `Σp(1−p)` ile aynı büyüklükte mi. Maçlar birlikte hareket
    etseydi (favori haftası / sürpriz haftası) gözlenen varyans belirgin
    biçimde büyük çıkardı.

    Sınırlar geniş (0,5–1,6) ve bilerek: 36 haftada varyans oranının kendi
    örneklem dağılımı geniştir. Test "varsayım tam doğru" demiyor,
    **"kırılmadı"** diyor — dar bir sınır burada kendi gürültüsünü ölçerdi.
    """
    import statistics

    from spor_toto.backtest import hafta_girdileri

    haftalar = [g for g in hafta_girdileri(None) if g["usable"]]
    if len(haftalar) < 20:
        pytest.skip("bagimsizlik sinamasi icin en az 20 tam hafta gerekli")

    gozlenen, ongorulen = [], []
    for w in haftalar:
        favs = [max(p, key=p.get) for p in w["probs"]]
        pf = [p[f] for p, f in zip(w["probs"], favs)]
        gozlenen.append(sum(1 for f, k in zip(favs, w["results"]) if f == k))
        ongorulen.append(sum(x * (1 - x) for x in pf))

    oran = statistics.variance(gozlenen) / statistics.mean(ongorulen)
    assert 0.5 < oran < 1.6, (
        f"haftalik favori isabetinin varyans orani {oran:.2f} — bagimsizlik "
        f"varsayimi kirilmis olabilir; P(>=12) ve p_kume_ici bu varsayima "
        f"dayaniyor (gozlenen var {statistics.variance(gozlenen):.2f}, "
        f"ongorulen {statistics.mean(ongorulen):.2f})")
