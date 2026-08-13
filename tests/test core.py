"""Girdi ayristirma, dogrulama, kodlayici ve geometri testleri."""

import math
import random
from itertools import product

import pytest

from spor_toto.core import (SEMBOLLER, Encoder, ball, distance_layers,
                            dogrula_kaplama, dogrula_secimler, hamming,
                            parse_picks, parse_probs, sirala_semboller)

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


# ------------------------------------------------------------
# Sembol siralamasi
# ------------------------------------------------------------

def test_sembol_sirasi_kupon_duzeninde():
    # Alfabetik siralama '01' verirdi; kupon duzeni 1/0/2'dir.
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
    for pos, i in zip(enc.variable_pos, range(enc.n)):
        assert metin[pos] in ("10", "12", "02", "102")
        assert metin[pos] != "01"


# ------------------------------------------------------------
# Ayristirma
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Olasilik ayristirma
# ------------------------------------------------------------

def test_parse_probs_normalize_eder():
    sel = parse_picks("1,10")
    p = parse_probs("1:2,0:1,2:1; 1:1,0:1", sel)
    assert p[0]["1"] == pytest.approx(0.5)
    assert p[0]["0"] == pytest.approx(0.25)
    assert sum(p[1].values()) == pytest.approx(1.0)


@pytest.mark.parametrize("kotu", [
    "1:0.5",                 # eksik mac
    "1:0.5;0:0.5;1:1",       # fazla mac
    "1:abc;0:1",             # sayi degil
    "9:0.5;0:1",             # gecersiz sembol
    "1:-1;0:1",              # negatif
    "1:0,0:0;0:1",           # toplam sifir
    "1;0:1",                 # bicim hatasi
])
def test_parse_probs_hatalari(kotu):
    with pytest.raises(ValueError):
        parse_probs(kotu, parse_picks("1,10"))


# ------------------------------------------------------------
# Kodlayici
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Geometri
# ------------------------------------------------------------

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
        assert len(set(b)) == beklenen          # tekrar yok
        assert set(b) <= space                  # uzay disina cikmiyor
        assert all(hamming(p, q) <= 1 for q in b)
        # r=1 topu, mesafesi <=1 olan TUM noktalari icermeli
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
