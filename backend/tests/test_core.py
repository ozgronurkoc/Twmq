"""Girdi ayristirma, dogrulama, kodlayici ve geometri testleri."""

import math
import random
from itertools import product

import pytest

from spor_toto.core import (
    Encoder,
    ball,
    distance_layers,
    dogrula_kaplama,
    dogrula_secimler,
    hamming,
    parse_picks,
    parse_probs,
    sirala_semboller,
)

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


def test_sembol_sirasi_kupon_duzeninde():
    assert sirala_semboller(["0", "1"]) == ["1", "0"]
    assert sirala_semboller(["2", "0", "1"]) == ["1", "0", "2"]
    assert sirala_semboller(["2", "1"]) == ["1", "2"]
    assert sirala_semboller(["2", "0"]) == ["0", "2"]


def test_parse_picks_siralamayi_normalize_eder():
    assert parse_picks("01,21,201")[0] == ["1", "0"]
    assert parse_picks("01,21,201")[1] == ["1", "2"]
    assert parse_picks("01,21,201")[2] == ["1", "0", "2"]


def test_encoder_cikti_kupon_duzeninde():
    enc = Encoder(parse_picks(ORNEK))
    row = tuple(frozenset(range(k)) for k in enc.alphabet_sizes)
    metin = enc.decode_row(row)
    for pos, _i in zip(enc.variable_pos, range(enc.n)):
        assert metin[pos] in ("10", "12", "02", "102")
        assert metin[pos] != "01"


@pytest.mark.parametrize("metin,beklenen", [
    ("1,10,102", [["1"], ["1", "0"], ["1", "0", "2"]]),
    ("1 10 102", [["1"], ["1", "0"], ["1", "0", "2"]]),
    ("1;10;102", [["1"], ["1", "0"], ["1", "0", "2"]]),
    ("1, 10 , 102 ", [["1"], ["1", "0"], ["1", "0", "2"]]),
])
def test_parse_picks_ayiricilar(metin, beklenen):
    assert parse_picks(metin) == beklenen


@pytest.mark.parametrize("kotu", ["", "   ", ",,,"])
def test_parse_picks_bos_reddedilir(kotu):
    with pytest.raises(ValueError):
        parse_picks(kotu)


@pytest.mark.parametrize("kotu,parca", [
    ("1,5,1", "gecersiz sembol"),
    ("1,11,1", "tekrar eden"),
    ("1,1021,1", "tekrar eden"),
])
def test_gecersiz_secimler(kotu, parca):
    with pytest.raises(ValueError, match=parca):
        Encoder(parse_picks(kotu))


def test_bos_mac_reddedilir():
    with pytest.raises(ValueError, match="hic secenek"):
        Encoder([["1"], []])


def test_15_mac_disi_uyari_verir_hata_vermez():
    enc = Encoder(parse_picks("1,10,1"))
    assert enc.uyarilar
    assert "15" in enc.uyarilar[0]


def test_kati_modda_15_mac_disi_hata():
    with pytest.raises(ValueError):
        Encoder(parse_picks("1,10,1"), kati=True)


def test_dogrula_secimler_bos_liste():
    with pytest.raises(ValueError, match="bos"):
        dogrula_secimler([])


def test_parse_probs_normalize_eder():
    sel = parse_picks("1,10")
    p = parse_probs("1:2,0:1,2:1; 1:1,0:1", sel)
    assert p[0]["1"] == pytest.approx(0.5)
    assert p[0]["0"] == pytest.approx(0.25)
    assert sum(p[1].values()) == pytest.approx(1.0)


@pytest.mark.parametrize("kotu", [
    "1:0.5",
    "1:0.5;0:0.5;1:1",
    "1:abc;0:1",
    "9:0.5;0:1",
    "1:-1;0:1",
    "1:0,0:0;0:1",
    "1;0:1",
])
def test_parse_probs_hatalari(kotu):
    with pytest.raises(ValueError):
        parse_probs(kotu, parse_picks("1,10"))


def test_encoder_olculeri():
    enc = Encoder(parse_picks(ORNEK))
    assert len(enc.banko_pos) == 7
    assert enc.n == 8
    assert enc.alphabet_sizes == (2,) * 8
    assert enc.space_size() == 256
    assert enc.ball_size() == 9
    assert enc.lower_bound() == math.ceil(256 / 9)


def test_encoder_uclu_olculeri():
    enc = Encoder(parse_picks("102,102,102,102,1,1,1,1,1,1,1,1,1,1,1"))
    assert enc.alphabet_sizes == (3,) * 4
    assert enc.space_size() == 81
    assert enc.ball_size() == 9
    assert enc.lower_bound() == 9


def test_decode_full_gidip_gelme():
    enc = Encoder(parse_picks(ORNEK))
    for p in enc.variable_space():
        tam = enc.decode_full(p)
        assert len(tam) == 15
        for i, pos in enumerate(enc.variable_pos):
            assert tam[pos] == enc.variable_syms[i][p[i]]
        for pos, sym in zip(enc.banko_pos, enc.banko_syms):
            assert tam[pos] == sym


def test_decode_full_yanlis_boyut():
    enc = Encoder(parse_picks(ORNEK))
    with pytest.raises(ValueError):
        enc.decode_full((0, 0))


def test_tum_banko_kupon():
    enc = Encoder(parse_picks(",".join(["1"] * 15)))
    assert enc.n == 0
    assert enc.space_size() == 1
    assert enc.lower_bound() == 1


def test_hamming_temel():
    assert hamming((0, 0, 0), (0, 0, 0)) == 0
    assert hamming((0, 1, 0), (0, 0, 0)) == 1
    assert hamming((1, 1, 1), (0, 0, 0)) == 3


@pytest.mark.parametrize("sizes", [(2,), (2, 3), (3, 3, 2), (2,) * 5])
def test_ball_boyutu_ve_uyeligi(sizes):
    space = set(product(*[range(k) for k in sizes]))
    beklenen = 1 + sum(k - 1 for k in sizes)
    for p in space:
        b = ball(p, sizes)
        assert len(b) == beklenen
        assert len(set(b)) == beklenen
        assert set(b) <= space
        assert all(hamming(p, q) <= 1 for q in b)
        assert set(b) == {q for q in space if hamming(p, q) <= 1}


def test_ball_simetrik():
    sizes = (2, 3, 2)
    space = list(product(*[range(k) for k in sizes]))
    for p in space:
        for q in ball(p, sizes):
            assert p in ball(q, sizes)


@pytest.mark.parametrize("sizes", [(2, 2, 2), (3, 3), (2, 3, 2)])
def test_distance_layers_naif_ile_ayni(sizes):
    space = list(product(*[range(k) for k in sizes]))
    rng = random.Random(0)
    for _ in range(20):
        cols = rng.sample(space, rng.randint(1, len(space)))
        hizli = distance_layers(cols, sizes)
        naif = {}
        for p in space:
            d = min(hamming(p, c) for c in cols)
            naif[d] = naif.get(d, 0) + 1
        assert dict(hizli) == naif


def test_distance_layers_bos_kolon():
    assert distance_layers([], (2, 2)) == {}


def test_dogrula_kaplama_acik_tespit_eder():
    sizes = (2, 2, 2)
    worst, acik = dogrula_kaplama([(0, 0, 0)], sizes)
    assert acik == 8 - 4
    assert worst == 2
    worst, acik = dogrula_kaplama([(0, 0, 0), (1, 1, 1)], sizes)
    assert acik == 0
    assert worst == 1


def test_all_modulun_gercek_yuzeyini_sayar():
    """`core.__all__` modulun kendisiyle ortusmeli.

    Depoda `import *` yok, yani bu liste calisma zamaninda hicbir sey
    yapmiyordu ve tam bu yuzden sessizce eskimisti: `Fix16Hatasi`,
    `rows_to_points`, `MAC_SAYISI`, `hamming74_variant`, `block_optimal` ve
    `ternary_hamming4` disarida kalmisti — ilk ikisini `cli`, `web_app`,
    `report` ve `health` zaten import ediyordu. Yani "core'dan ne cikar"
    sorusunun yazili cevabi ile gercek cevap ayrismisti.

    Bu test ikisini bagliyor: listeye eklemeden yeni public isim
    tanimlanamaz, listeden cikarmadan public isim silinemez.
    """
    import ast
    import pathlib

    import spor_toto.core as core

    kaynak = pathlib.Path(core.__file__).read_text(encoding="utf-8")
    tanimli: set[str] = set()

    def topla(govde):
        """Modul duzeyindeki tanimlar — try/if bloklarinin ICI dahil.

        `HAS_SCIPY` bir `try/except ImportError` icinde atanir; yalnizca
        `tree.body`ye bakmak onu kacirirdi.
        """
        for dugum in govde:
            if isinstance(dugum, (ast.FunctionDef, ast.ClassDef)):
                tanimli.add(dugum.name)
            elif isinstance(dugum, ast.Assign):
                tanimli.update(t.id for t in dugum.targets if isinstance(t, ast.Name))
            elif isinstance(dugum, ast.AnnAssign) and isinstance(dugum.target, ast.Name):
                tanimli.add(dugum.target.id)
            elif isinstance(dugum, ast.Try):
                topla(dugum.body)
                for h in dugum.handlers:
                    topla(h.body)
                topla(dugum.orelse)
                topla(dugum.finalbody)
            elif isinstance(dugum, ast.If):
                topla(dugum.body)
                topla(dugum.orelse)

    topla(ast.parse(kaynak).body)
    # Private isimler disarida.
    tanimli = {a for a in tanimli if not a.startswith("_")}

    ilan = set(core.__all__)
    assert ilan - tanimli == set(), \
        f"__all__ modulde tanimli olmayan isim sayiyor: {sorted(ilan - tanimli)}"
    assert tanimli - ilan == set(), \
        f"public tanim __all__'da yok: {sorted(tanimli - ilan)}"
    assert len(core.__all__) == len(ilan), "__all__ icinde tekrar var"
