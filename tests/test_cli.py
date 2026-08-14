"""Olasilik raporu, butce danismani, CLI ve raporlama testleri."""

import math

import pytest

from spor_toto.cli import build_parser, main
from spor_toto.core import (HAS_SCIPY, Encoder, butce_danismani, merge_rows,
                            olasilik_raporu, parse_picks, parse_probs,
                            solve_fix16)

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


def test_olasilik_14_garanti_tutarli():
    """p_15 + p_14 = p_kume_ici olmali (kaplama gecerliyse)."""
    sel = parse_picks(ORNEK)
    enc = Encoder(sel)
    cols, _ = solve_fix16(enc)
    probs = parse_probs(esit_olasilik(ORNEK), sel)
    rap = olasilik_raporu(enc, cols, probs)
    assert rap.p_15 + rap.p_14 == pytest.approx(rap.p_kume_ici)
    assert 0.0 <= rap.p_15 <= rap.p_kume_ici <= 1.0


def test_olasilik_tek_kolon_kume_ici_ile_sinirli():
    """
    En olasi tek kolon, kume-ici olasiligi asamaz. Bilerek 'p_15 daha
    buyuktur' iddiasinda BULUNMUYORUZ: kaplama kodu 15 sansini degil
    kapsamayi maksimize eder.
    """
    sel = parse_picks(ORNEK)
    enc = Encoder(sel)
    cols, _ = solve_fix16(enc)
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
    cols, _ = solve_fix16(enc)
    with pytest.raises(ValueError):
        olasilik_raporu(enc, cols, [{"1": 1.0}])


# ------------------------------------------------------------
# Butce danismani
# ------------------------------------------------------------

def test_butce_danismani_butceye_uyar():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,10,102,2,1,0,1,1,2"))
    planlar = butce_danismani(enc, 32)
    assert planlar
    for pl in planlar:
        assert pl.bedel <= 32
        assert pl.satir == 16
        yeni = Encoder(pl.selections)
        assert len(yeni.double_pos()) >= 7
        cols, _ = solve_fix16(yeni)
        assert len(cols) == pl.bedel
        assert len(merge_rows(cols)) == 16


def test_butce_danismani_en_az_feda_edeni_once_verir():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,10,10,2,1,0,1,1,2"))
    planlar = butce_danismani(enc, 32)
    assert planlar
    say = [len(p.degisiklikler) for p in planlar]
    assert say == sorted(say)


def test_butce_yeterliyse_degisiklik_gerekmez():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,1,1,1,1,1,1,1,1"))
    planlar = butce_danismani(enc, 16)
    assert planlar[0].degisiklikler == []
    assert planlar[0].bedel == 16


def test_butce_cok_kucukse_plan_yok():
    enc = Encoder(parse_picks("10,10,10,10,10,10,10,10,1,1,1,1,1,1,1"))
    assert butce_danismani(enc, 4) == []


def test_butce_olasilikla_dusuk_ihtimali_atar():
    picks = "102,10,10,10,10,10,10,10,1,1,1,1,1,1,1"
    sel = parse_picks(picks)
    enc = Encoder(sel)
    # 1. macta '2' cok dusuk olasilikli -> once o atilmali
    probs = parse_probs("1:0.6,0:0.39,2:0.01;" + ";".join(["1:1,0:1"] * 14), sel)
    planlar = butce_danismani(enc, 16, probs)
    assert planlar
    ilk = planlar[0].degisiklikler[0]
    assert ilk.startswith("1. mac: 102 ->")
    # En dusuk olasilikli '2' once atilmali, '1' her zaman kalmali
    kalan = ilk.split("-> ")[1]
    assert "2" not in kalan
    assert kalan.startswith("1")


def test_butce_gecersiz_deger():
    enc = Encoder(parse_picks(ORNEK))
    with pytest.raises(ValueError):
        butce_danismani(enc, 0)


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def test_cli_varsayilan_calisir(capsys):
    assert main(["--picks", ORNEK, "--kisa", "--no-compare"]) == 0
    out = capsys.readouterr().out
    assert "16 satir" in out
    assert "14-GARANTI DOGRULANDI" in out
    assert " 01" not in out            # yanlis sembol sirasi olmamali


def test_cli_varyant(capsys):
    assert main(["--picks", ORNEK, "--kisa", "--no-compare", "--variant", "3"]) == 0
    a = capsys.readouterr().out
    assert main(["--picks", ORNEK, "--kisa", "--no-compare", "--variant", "0"]) == 0
    b = capsys.readouterr().out
    assert a != b


def test_cli_yetersiz_cifte_hata_kodu(capsys):
    kod = main(["--picks", "102,102,10,10,1,1,0,2,1,1,0,1,2,1,0", "--kisa"])
    assert kod == 1
    assert "EN AZ 7 CIFTE" in capsys.readouterr().err


def test_cli_gecersiz_sembol_hata_kodu(capsys):
    assert main(["--picks", "1,5,1,1,1,1,1,1,1,1,1,1,1,1,1"]) == 1
    assert "gecersiz sembol" in capsys.readouterr().err


def test_cli_kati_mod(capsys):
    assert main(["--picks", "1,10,1", "--kati"]) == 1


def test_cli_olasilik_ciktisi(capsys):
    assert main(["--picks", ORNEK, "--kisa", "--no-compare",
                 "--probs", esit_olasilik(ORNEK)]) == 0
    out = capsys.readouterr().out
    assert "Olasilik raporu" in out
    assert "15 tutturma" in out


def test_cli_butce_modu(capsys):
    assert main(["--picks", "10,10,10,10,10,10,10,10,10,2,1,0,1,1,2",
                 "--mode", "butce", "--budget", "32", "--kisa",
                 "--no-compare"]) == 0
    out = capsys.readouterr().out
    assert "BUTCE DANISMANI" in out
    assert "Plan 1" in out


def test_cli_butce_eksik_parametre(capsys):
    assert main(["--picks", ORNEK, "--mode", "butce"]) == 1
    assert "--budget" in capsys.readouterr().err


def test_cli_maxcov_eksik_parametre(capsys):
    assert main(["--picks", ORNEK, "--mode", "maxcov"]) == 1


@gerek_scipy
@pytest.mark.slow
def test_cli_maxcov_modu(capsys):
    assert main(["--picks", ORNEK, "--mode", "maxcov", "--budget", "16",
                 "--kisa", "--time-limit", "60"]) == 0
    out = capsys.readouterr().out
    assert "GARANTI DEGIL" in out
    assert "144/256" in out


def test_cli_auto_modu(capsys):
    assert main(["--picks", "10,10,10,10,10,1,1,1,1,1,1,1,1,1,1",
                 "--mode", "auto", "--kisa"]) == 0
    assert "SONUC" in capsys.readouterr().out


def test_cli_heuristic_modu(capsys):
    assert main(["--picks", "10,10,10,10,10,1,1,1,1,1,1,1,1,1,1",
                 "--mode", "heuristic", "--kisa", "--ls-iters", "2000"]) == 0
    assert "Heuristik" in capsys.readouterr().out


def test_cli_dosyaya_yazar(tmp_path, capsys):
    hedef = tmp_path / "formul.txt"
    assert main(["--picks", ORNEK, "--kisa", "--no-compare",
                 "--output", str(hedef)]) == 0
    icerik = hedef.read_text(encoding="utf-8")
    assert "KUPONA YAZILACAK" in icerik
    assert "ACIK HALI" in icerik
    assert icerik.count("|") >= 16 + 32


def test_cli_15_mac_uyarisi(capsys):
    assert main(["--picks", "10,10,10,10,10,10,10,1", "--kisa",
                 "--no-compare"]) == 0
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
        "--kisa", "--no-compare",
    ]) == 0
    out = capsys.readouterr().out
    assert "Bayes" in out
    assert "preset=dengeli" in out
    assert "Prior" in out
    assert "14-GARANTI DOGRULANDI" in out


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
        "--kisa", "--no-compare",
    ]) == 0
    out = capsys.readouterr().out
    assert "Prior" in out
    assert "Evidence" in out


@pytest.mark.parametrize("mode", ["fix16", "auto", "block", "heuristic"])
def test_cli_tum_modlar_kucuk_kuponda(mode, capsys):
    picks = "10,10,10,10,10,10,10,1,1,1,1,1,1,1,1"
    assert main(["--picks", picks, "--mode", mode, "--kisa",
                 "--ls-iters", "2000", "--no-compare"]) == 0
    out = capsys.readouterr().out
    assert "14-GARANTI DOGRULANDI" in out
