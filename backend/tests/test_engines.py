"""Cozucu motorlari: bilinen optimal degerler ve garanti degismezleri."""

import math
import random
from itertools import product

import pytest

from spor_toto.core import (
    HAS_SCIPY,
    Encoder,
    Fix16Hatasi,
    _varsayilan_bloklar,
    ball,
    block_optimal,
    exact_cover,
    exact_max_coverage,
    greedy_full,
    hamming,
    hamming74_codewords,
    hamming74_variant,
    ls_fixed_size,
    merge_rows,
    parse_picks,
    row_cost,
    rows_to_points,
    solve_by_blocks,
    solve_fix16,
    solve_heuristic,
)

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
gerek_scipy = pytest.mark.skipif(not HAS_SCIPY, reason="scipy yok")


#: Kaplama gecerliligi TEK kaynaktan (`tests/conftest.py`). Ayni govde uc
#: dosyada birebir yaziliydi.
from tests.conftest import kaplama_gecerli

# ------------------------------------------------------------
# Hamming(7,4) - mukemmel kod
# ------------------------------------------------------------

def test_hamming74_mukemmel():
    cw = hamming74_codewords()
    assert len(cw) == 16
    assert len(set(cw)) == 16
    assert all(len(c) == 7 for c in cw)
    dmin = min(hamming(a, b) for i, a in enumerate(cw) for b in cw[i + 1:])
    assert dmin == 3
    assert kaplama_gecerli(cw, (2,) * 7)
    # mukemmel: 16 x 8 = 128, toplar cakismiyor
    toplam = sum(len(ball(c, (2,) * 7)) for c in cw)
    assert toplam == 128
    assert len({q for c in cw for q in ball(c, (2,) * 7)}) == 128


@pytest.mark.parametrize("variant", list(range(12)))
def test_hamming74_varyantlari_de_mukemmel(variant):
    cw = hamming74_variant(variant)
    assert len(set(cw)) == 16
    assert kaplama_gecerli(cw, (2,) * 7)


def test_varyantlar_gercekten_farkli():
    kumeler = {frozenset(hamming74_variant(v)) for v in range(15)}
    assert len(kumeler) > 1


def test_varyant_sifir_kanonik():
    assert hamming74_variant(0) == hamming74_codewords()


# ------------------------------------------------------------
# Onbellege konan cebirsel bloklar
# ------------------------------------------------------------

@pytest.mark.parametrize("sizes,cols", list(_varsayilan_bloklar().items()),
                         ids=lambda v: str(v) if isinstance(v, tuple) else "")
def test_tohum_bloklar_gecerli(sizes, cols):
    assert kaplama_gecerli(cols, sizes)


def test_tohum_bloklar_bilinen_optimal():
    b = _varsayilan_bloklar()
    assert len(b[(2,) * 7]) == 16      # K(7,1)
    assert len(b[(2,) * 8]) == 32      # K(8,1)
    assert len(b[(3,) * 4]) == 9       # K3(4,1)
    assert len(b[(3,) * 5]) == 27      # K3(5,1)
    assert len(b[(2, 2, 2)]) == 2      # K(3,1)
    # Cebirsel degil, ILP ispatli (bkz. core._ILP_3322_22). Sayinin kendisi
    # `test_donmus_ilp_blogu_hala_optimal` icinde ILP'ye yeniden sorulur.
    assert len(b[(3, 3, 2, 2, 2, 2)]) == 20


# ------------------------------------------------------------
# Kesin cozucu (ILP) - literaturdeki degerler
# ------------------------------------------------------------

BILINEN = [
    ((2,) * 1, 1), ((2,) * 2, 2), ((2,) * 3, 2), ((2,) * 4, 4),
    ((2,) * 5, 7), ((2,) * 6, 12), ((2,) * 7, 16),
    ((3,) * 1, 1), ((3,) * 2, 3), ((3,) * 3, 5), ((3,) * 4, 9),
]


@gerek_scipy
@pytest.mark.parametrize("sizes,beklenen", BILINEN)
def test_exact_cover_literatur(sizes, beklenen):
    cols, kanit = exact_cover(sizes, time_limit=60)
    assert cols is not None
    assert kanit is True
    assert len(cols) == beklenen
    assert kaplama_gecerli(cols, sizes)


@gerek_scipy
@pytest.mark.slow
def test_exact_cover_8_cifte_32():
    """K(8,1)=32: 8 ciftenin 16 kolona sigmadiginin ILP ispati."""
    cols, kanit = exact_cover((2,) * 8, time_limit=180)
    assert kanit is True
    assert len(cols) == 32
    assert kaplama_gecerli(cols, (2,) * 8)


@gerek_scipy
@pytest.mark.slow
def test_donmus_ilp_blogu_hala_optimal():
    """**Donmus ILP cikitisinin bekcisi.**

    `core._ILP_3322_22` kaynakta duran 20 kolonluk bir kaplamadir; cebirsel
    degil, ILP'nin bulup optimalligini ispatladigi bir sonuctur. Oraya
    konmasinin tek sebebi bedeliydi (~17,6 sn, her kosuda yeniden).

    Donmus bir sayinin sessizce eskimesi buradaki asil risk: ILP kodlamasi
    bir gun iyilesir ve 20'nin altina inerse, tablo onu gormeden eski
    cevabi vermeye devam ederdi. Bu test ILP'yi yeniden kosarak tam olarak
    onu denetler — bu yuzden yavas isaretli, hizli kapiya girmez.
    """
    from spor_toto.core import _ILP_3322_22

    sizes = (3, 3, 2, 2, 2, 2)
    assert kaplama_gecerli(_ILP_3322_22, sizes), "donmus blok gecerli kaplama degil"

    cols, kanit = exact_cover(sizes, time_limit=180)
    assert kanit is True, "ILP optimalligi ispatlayamadi — donmus sayi dogrulanamiyor"
    assert len(cols) == len(_ILP_3322_22) == 20, (
        f"ILP artik {len(cols)} kolon buluyor, kaynakta {len(_ILP_3322_22)} var "
        f"— core._ILP_3322_22 guncellenmeli")


@gerek_scipy
def test_exact_cover_bos_sizes():
    assert exact_cover(()) == (None, False)


@gerek_scipy
def test_max_coverage_kure_tavanina_ulasir():
    """16 kolon x 9 nokta = 144; 8 ciftede bu tavan gercekten ulasilabiliyor."""
    cols, kapsanan, kanit = exact_max_coverage((2,) * 8, 16, time_limit=120)
    assert cols is not None
    assert len(cols) <= 16
    assert kapsanan == 144
    assert kanit is True
    assert kapsanan < 256  # 14-garanti imkansiz


@gerek_scipy
def test_max_coverage_gecersiz_butce():
    assert exact_max_coverage((2, 2), 0)[0] is None


# ------------------------------------------------------------
# Sabit 16 satir modu
# ------------------------------------------------------------

FIX16_KUPONLARI = [
    "10,10,10,10,10,10,10,0,1,2,1,0,1,1,2",              # 7 cifte
    "10,10,10,10,10,10,10,10,1,2,1,0,1,1,2",             # 8 cifte
    "10,10,10,10,10,10,10,10,10,2,1,0,1,1,2",            # 9 cifte
    "10,10,10,10,10,10,10,10,10,10,1,0,1,1,2",           # 10 cifte
    "10,10,10,10,10,10,10,102,1,2,1,0,1,1,2",            # 7 cifte + 1 uclu
    "10,10,10,10,10,10,10,102,102,2,1,0,1,1,2",          # 7 cifte + 2 uclu
    "10,10,10,10,10,10,10,10,102,2,1,0,1,1,2",           # 8 cifte + 1 uclu
    "12,02,10,12,02,10,12,1,1,2,1,0,1,1,2",              # karisik cifte turleri
]


@pytest.mark.parametrize("picks", FIX16_KUPONLARI)
def test_fix16_her_zaman_16_satir(picks):
    enc = Encoder(parse_picks(picks))
    cols, aciklama = solve_fix16(enc)
    rows = merge_rows(cols)
    assert len(rows) == 16, aciklama
    assert kaplama_gecerli(cols, enc.alphabet_sizes)


@pytest.mark.parametrize("picks", FIX16_KUPONLARI)
def test_fix16_bedel_formulu(picks):
    """Bedel = 16 x (blok disi seceneklerin carpimi)."""
    enc = Encoder(parse_picks(picks))
    cols, _ = solve_fix16(enc)
    kalan = list(enc.alphabet_sizes)
    for _ in range(7):
        kalan.remove(2)          # blok tam olarak 7 cifteden olusur
    assert len(cols) == 16 * math.prod(kalan)


@pytest.mark.parametrize("picks", FIX16_KUPONLARI[:5])
@pytest.mark.parametrize("variant", [0, 1, 2, 5, 9])
def test_fix16_varyantlar_garantiyi_korur(picks, variant):
    enc = Encoder(parse_picks(picks))
    cols, _ = solve_fix16(enc, variant=variant)
    assert len(merge_rows(cols)) == 16
    assert kaplama_gecerli(cols, enc.alphabet_sizes)


def test_fix16_varyantlar_farkli_kupon_uretir():
    enc = Encoder(parse_picks(ORNEK))
    kumeler = {frozenset(solve_fix16(enc, variant=v)[0]) for v in range(10)}
    assert len(kumeler) > 1


def test_fix16_ayni_varyant_ayni_sonuc():
    enc = Encoder(parse_picks(ORNEK))
    assert solve_fix16(enc, variant=7)[0] == solve_fix16(enc, variant=7)[0]


@pytest.mark.parametrize("picks", [
    "102,102,10,10,1,1,0,2,1,1,0,1,2,1,0",   # 2 cifte
    "1,1,1,1,1,1,1,1,1,1,1,1,1,1,1",         # hic cifte yok
    "10,10,10,10,10,10,1,1,1,1,1,1,1,1,1",   # 6 cifte - bir eksik
])
def test_fix16_yetersiz_cifte_reddedilir(picks):
    enc = Encoder(parse_picks(picks))
    with pytest.raises(Fix16Hatasi, match="EN AZ 7 CIFTE"):
        solve_fix16(enc)


def test_fix16_tam_7_cifte_sinirda_calisir():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,1,1,1,1,1,1,1,1"))
    cols, _ = solve_fix16(enc)
    assert len(cols) == 16
    assert len(merge_rows(cols)) == 16


# ------------------------------------------------------------
# Blok motoru
# ------------------------------------------------------------

BLOK_KUPONLARI = [*FIX16_KUPONLARI, "102,102,102,102,1,1,0,2,1,1,0,1,2,1,0", "102,102,10,10,1,1,0,2,1,1,0,1,2,1,0", "10,10,10,10,10,1,1,1,1,1,1,1,1,1,1"]


@pytest.mark.parametrize("picks", BLOK_KUPONLARI)
def test_blok_motoru_gecerli_kaplama(picks):
    enc = Encoder(parse_picks(picks))
    sonuc = solve_by_blocks(enc)
    assert sonuc is not None
    cols, _ = sonuc
    assert kaplama_gecerli(cols, enc.alphabet_sizes)
    assert len(cols) >= enc.lower_bound()
    assert len(cols) <= enc.space_size()


@pytest.mark.parametrize("picks", BLOK_KUPONLARI)
def test_blok_fix16den_ucuz_veya_esit(picks):
    """Blok motoru tum bloklari tarar; fix16 tek bir blogu zorlar."""
    enc = Encoder(parse_picks(picks))
    blok, _ = solve_by_blocks(enc)
    try:
        f16, _ = solve_fix16(enc)
    except Fix16Hatasi:
        return
    assert len(blok) <= len(f16)


def test_blok_4_uclu_9_kolon():
    enc = Encoder(parse_picks("102,102,102,102,1,1,1,1,1,1,1,1,1,1,1"))
    cols, _ = solve_by_blocks(enc)
    assert len(cols) == 9
    assert len(merge_rows(cols)) == 9


def test_blok_degisken_yoksa_none():
    enc = Encoder(parse_picks(",".join(["1"] * 15)))
    assert solve_by_blocks(enc) is None


def test_block_optimal_koordinat_sirasi_korunur():
    """
    Gerileme testi: onbellek anahtari siralanip donen kolonlar sirasiz
    eslesince 3 degerli sembol 2 secenekli maca atanip IndexError
    uretiyordu.
    """
    sizes = (3, 2, 2)
    cols = block_optimal(sizes, time_limit=30)
    assert cols is not None
    for c in cols:
        for v, k in zip(c, sizes):
            assert 0 <= v < k


# ------------------------------------------------------------
# Heuristik motor
# ------------------------------------------------------------

@pytest.mark.parametrize("picks", [
    "10,10,10,10,10,1,1,1,1,1,1,1,1,1,1",
    "102,102,102,1,1,1,1,1,1,1,1,1,1,1,1",
    "10,10,102,10,1,1,1,1,1,1,1,1,1,1,1",
])
def test_greedy_full_tam_kaplar(picks):
    enc = Encoder(parse_picks(picks))
    space = list(enc.variable_space())
    cols = greedy_full(space, enc.alphabet_sizes, random.Random(0))
    assert kaplama_gecerli(cols, enc.alphabet_sizes)
    assert len(cols) >= enc.lower_bound()


def test_greedy_full_bos_uzay():
    assert greedy_full([], (), random.Random(0)) == []


def test_solve_heuristic_gecerli_ve_makul():
    enc = Encoder(parse_picks("10,10,10,10,10,10,1,1,1,1,1,1,1,1,1"))
    cols = solve_heuristic(enc, trials=3, ls_iters=8000, seed=1)
    assert kaplama_gecerli(cols, enc.alphabet_sizes)
    # 6 cifte icin optimal 12; heuristik cok uzaga dusmemeli
    assert len(cols) <= 20


def test_local_search_asla_kaplamayi_bozmaz():
    """
    Gerileme testi: onceki surumde LS 'en az 1 boslugu kapat' kosuluyla
    kabul yapiyor ve kapsamayi kiriyordu (43 -> 56 kolon). Donen sonuc
    ya None ya da GECERLI bir kaplama olmalidir, asla yarim kalmis
    bir kume degil.
    """
    enc = Encoder(parse_picks("10,10,10,10,10,1,1,1,1,1,1,1,1,1,1"))
    space = list(enc.variable_space())
    for m in range(3, 12):
        for seed in range(5):
            r = ls_fixed_size(space, enc.alphabet_sizes, m, 4000,
                              random.Random(seed))
            if r is not None:
                assert len(r) == m
                assert kaplama_gecerli(r, enc.alphabet_sizes)


def test_local_search_gecersiz_boyut():
    enc = Encoder(parse_picks("10,10,1,1,1,1,1,1,1,1,1,1,1,1,1"))
    space = list(enc.variable_space())
    assert ls_fixed_size(space, enc.alphabet_sizes, 0, 10, random.Random(0)) is None


# ------------------------------------------------------------
# Satir sikistirma
# ------------------------------------------------------------

@pytest.mark.parametrize("picks", FIX16_KUPONLARI)
def test_sikistirma_kayipsiz(picks):
    enc = Encoder(parse_picks(picks))
    cols, _ = solve_fix16(enc)
    rows = merge_rows(cols)
    assert set(rows_to_points(rows)) == set(cols)
    assert sum(row_cost(r) for r in rows) == len(cols)


def test_sikistirma_rastgele_kumelerde_kayipsiz():
    rng = random.Random(20240613)
    for _ in range(300):
        sizes = tuple(rng.choice([2, 3]) for _ in range(rng.randint(1, 5)))
        space = list(product(*[range(k) for k in sizes]))
        cols = rng.sample(space, rng.randint(1, len(space)))
        rows = merge_rows(cols)
        assert set(rows_to_points(rows)) == set(cols)
        assert sum(row_cost(r) for r in rows) == len(cols)
        assert len(rows) <= len(cols)


def test_sikistirma_tam_sistemi_tek_satira_indirir():
    sizes = (2,) * 7
    cols = list(product(*[range(k) for k in sizes]))
    rows = merge_rows(cols)
    assert len(rows) == 1
    assert row_cost(rows[0]) == 128


def test_sikistirma_bos():
    assert merge_rows([]) == []


def test_row_cost():
    assert row_cost((frozenset([0, 1]), frozenset([0]))) == 2
    assert row_cost((frozenset([0, 1, 2]), frozenset([0, 1]))) == 6
