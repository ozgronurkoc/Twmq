"""Olasilik raporu, CLI ve raporlama testleri."""


import pytest

from spor_toto.cli import build_parser, main
from spor_toto.core import (
    HAS_SCIPY,
    Encoder,
    olasilik_raporu,
    parse_picks,
    parse_probs,
)
from spor_toto.duz import kolonlar as duz_kolonlar

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
gerek_scipy = pytest.mark.skipif(not HAS_SCIPY, reason="scipy yok")


def esit_olasilik(picks: str) -> str:
    n = len(parse_picks(picks))
    return ";".join(["1:1,0:1,2:1"] * n)


# ------------------------------------------------------------
# Olasilik raporu
# ------------------------------------------------------------

def test_olasilik_kesin_tahminde_kesin_sonuc():
    """Her mac %100 belli ve secim kumesinde ise 15 olasiligi 1 olmali."""
    picks = "1,10,1,1,1,1,1,1,1,1,1,1,1,1,1"
    sel = parse_picks(picks)
    enc = Encoder(sel)
    probs = parse_probs(";".join(
        ["1:1,0:0,2:0"] * 15), sel)
    cols = [(0,)]  # tek kolon: 2. mac '1'
    rap = olasilik_raporu(enc, cols, probs)
    assert rap.p_kume_ici == pytest.approx(1.0)
    assert rap.p_15 == pytest.approx(1.0)
    assert rap.p_14 == pytest.approx(0.0)


def test_olasilik_kume_disi_sifirlar():
    """Gercek sonuc secim kumesi disindaysa kume-ici olasilik 0."""
    picks = "1,10,1,1,1,1,1,1,1,1,1,1,1,1,1"
    sel = parse_picks(picks)
    enc = Encoder(sel)
    probs = parse_probs(";".join(["2:1"] * 15), sel)
    cols = [(0,)]
    rap = olasilik_raporu(enc, cols, probs)
    assert rap.p_kume_ici == pytest.approx(0.0)
    assert rap.p_15 == pytest.approx(0.0)


def test_olasilik_kume_ici_DOGRUDAN_15_demek():
    """Duzde `p_15 == p_kume_ici`; kaplamada `p_15 + p_14 == p_kume_ici` idi.

    Fark yapisal: kaplama kumenin bir dilimini oynadigi icin kume icinde
    kalmak 15 degil "en fazla 1 hata" demekti ve kalan kutle 14'e dusuyordu.
    Duzde her nokta oynaniyor, yani kume icinde kalmak DOGRUDAN 15'tir ve
    `p_14` artik kume ici payindan gelmez.
    """
    sel = parse_picks(ORNEK)
    enc = Encoder(sel)
    cols = duz_kolonlar(enc)
    probs = parse_probs(esit_olasilik(ORNEK), sel)
    rap = olasilik_raporu(enc, cols, probs)
    assert rap.p_15 == pytest.approx(rap.p_kume_ici)
    assert 0.0 <= rap.p_15 <= rap.p_kume_ici <= 1.0


def test_olasilik_tek_kolon_kume_ici_ile_sinirli():
    """
    En olasi tek kolon, kume-ici olasiligi asamaz. Sinir duzde gevsektir
    (en olasi nokta zaten kolonlarin icinde) ve bilerek oyle birakiliyor:
    tutulmasi gereken sey siralamanin bozulmamasi.
    """
    sel = parse_picks(ORNEK)
    enc = Encoder(sel)
    cols = duz_kolonlar(enc)
    probs = parse_probs(esit_olasilik(ORNEK), sel)
    rap = olasilik_raporu(enc, cols, probs)
    assert rap.p_tek_kolon_15 <= rap.p_kume_ici


def test_olasilik_tek_kolon_secim_kumesiyle_sinirli():
    """Secim kumende olmayan yuksek olasilikli sonuc sayilmamali."""
    sel = parse_picks("1,1,1,1,1,1,1,1,1,1,1,1,1,1,1")
    enc = Encoder(sel)
    probs = parse_probs(";".join(["1:0.1,0:0.1,2:0.8"] * 15), sel)
    rap = olasilik_raporu(enc, [()], probs)
    assert rap.p_tek_kolon_15 == pytest.approx(0.1 ** 15)


def test_olasilik_mac_sayisi_uyusmazligi():
    sel = parse_picks(ORNEK)
    enc = Encoder(sel)
    cols = duz_kolonlar(enc)
    with pytest.raises(ValueError):
        olasilik_raporu(enc, cols, [{"1": 1.0}])


# ------------------------------------------------------------
# Butce danismani — SOKULDU
#
# Alti test buradaydi ve hepsi `core.butce_danismani`yi olcuyordu: kupon
# kaplama butcesine sigmiyorsa hangi isaretlerden feda edilecegini secen,
# "en az degisiklik yapani once ver" diye siralayan bir yardimci. Duzde o
# is bir DANISMAN degil, secim motorunun kendisi: `secim.en_iyi_secim`
# tavani ZORUNLU parametre olarak alir ve tavan altindaki en iyi sekli
# kesin (Pareto DP) olarak bulur — feda sirasi diye bir sezgiye gerek
# birakmaz. Bekcileri `tests/test_secim.py`de.
# ------------------------------------------------------------


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def test_cli_varsayilan_calisir(capsys):
    assert main(["--picks", ORNEK, "--kisa"]) == 0
    out = capsys.readouterr().out
    # Duzde kupon isaretlerin kendisidir: TEK satir.
    assert "1 satir" in out
    assert "KUMENIN TAMAMI OYNANIYOR" in out
    assert " 01" not in out            # yanlis sembol sirasi olmamali


def test_cli_gecersiz_sembol_hata_kodu(capsys):
    assert main(["--picks", "1,5,1,1,1,1,1,1,1,1,1,1,1,1,1"]) == 1
    assert "gecersiz sembol" in capsys.readouterr().err


def test_cli_kati_mod(capsys):
    assert main(["--picks", "1,10,1", "--kati"]) == 1


def test_cli_olasilik_ciktisi(capsys):
    assert main(["--picks", ORNEK, "--kisa",
                 "--probs", esit_olasilik(ORNEK)]) == 0
    out = capsys.readouterr().out
    assert "Olasilik raporu" in out
    assert "15 tutturma" in out


def test_cli_dosyaya_yazar(tmp_path, capsys):
    hedef = tmp_path / "formul.txt"
    assert main(["--picks", ORNEK, "--kisa",
                 "--output", str(hedef)]) == 0
    icerik = hedef.read_text(encoding="utf-8")
    assert "KUPONA YAZILACAK" in icerik
    assert "ACIK HALI" in icerik
    assert icerik.count("|") >= 16 + 32


def test_cli_15_mac_uyarisi(capsys):
    assert main(["--picks", "10,10,10,10,10,10,10,1", "--kisa",]) == 0
    assert "UYARI" in capsys.readouterr().out


def test_parser_yardim_metni():
    p = build_parser()
    yardim = p.format_help()
    assert "--picks" in yardim
    assert "fix16" in yardim
    assert "--bayes-preset" in yardim
    assert "dengeli" in yardim


def test_cli_bayes_preset_dengeli(capsys):
    assert main([
        "--picks", ORNEK,
        "--probs", esit_olasilik(ORNEK),
        "--bayes-preset", "dengeli",
        "--kisa",
    ]) == 0
    out = capsys.readouterr().out
    assert "Bayes" in out
    assert "preset=dengeli" in out
    assert "Prior" in out
    assert "KUMENIN TAMAMI OYNANIYOR" in out


def test_cli_bayes_requires_probs(capsys):
    code = main(["--picks", ORNEK, "--bayes-preset", "dengeli", "--kisa"])
    assert code == 1
    err = capsys.readouterr().err
    assert "probs" in err.lower()


def test_cli_bayes_manual_strengths(capsys):
    assert main([
        "--picks", ORNEK,
        "--probs", esit_olasilik(ORNEK),
        "--bayes",
        "--prior-strength", "2",
        "--evidence-strength", "5",
        "--kisa",
    ]) == 0
    out = capsys.readouterr().out
    assert "Prior" in out
    assert "Evidence" in out


