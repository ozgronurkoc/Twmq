"""Koşum defteri — *"bu sayı hangi koşumdan geldi?"*

**En kritik test `test_ortam_korpusu_ve_kirliligi_tasiyor`.** Kayıt
edilen şey çıktı değil **ortam**dır: çıktı zaten belgeye kopyalanıyor,
yeniden üretilebilirliği taşıyan şey korpus parmak izi, commit ve
tohumlardır. `kirli` alanı olmadan commit kimliği yanıltır — kirli bir
ağaçta koşulan ölçüm o commit'ten üretilemez.
"""
from __future__ import annotations

import argparse
import json

import pytest

from spor_toto.kosum import (
    ZAMAN_BICIMI,
    belki_kaydet,
    cli_ekle,
    kaydet,
    kosumlar,
    ortam,
    son,
)


def test_kaydet_iki_dosya_yazar(tmp_path):
    yol = kaydet("deneme", {"a": 1}, tmp_path)
    assert (yol / "cikti.json").exists()
    assert (yol / "ortam.json").exists()
    assert json.loads((yol / "cikti.json").read_text(encoding="utf-8")) == {"a": 1}


def test_kimlik_siralanabilir(tmp_path):
    """`sorted(glob)` kronolojik sıra vermeli — ayrı tarih ayrıştırma yok."""
    import time

    a = kaydet("x", {}, tmp_path)
    time.sleep(1.1)
    b = kaydet("x", {}, tmp_path)
    assert sorted([b.name, a.name]) == [a.name, b.name]


def test_kimlik_zaman_ve_ad_tasiyor(tmp_path):
    from datetime import datetime

    yol = kaydet("agac", {}, tmp_path)
    zaman, _, ad = yol.name.partition("-")
    assert ad == "agac"
    datetime.strptime(zaman, ZAMAN_BICIMI)  # bicim bozuksa patlar


def test_serilestirilemeyen_govde_kaydi_dusurmez(tmp_path):
    """Bir kaydın **yazılamaması**, eksik yazılmasından daha kötüdür."""
    from datetime import date

    yol = kaydet("x", {"tarih": date(2026, 1, 1)}, tmp_path)
    assert "2026-01-01" in (yol / "cikti.json").read_text(encoding="utf-8")


# ─── ortam — asıl bekçi ───────────────────────────────────────────────────

def test_ortam_korpusu_ve_kirliligi_tasiyor():
    """**Asıl bekçi.** Yeniden üretilebilirlik bu alanlarda durur."""
    o = ortam()
    assert set(o) >= {"zaman", "surum", "git", "python", "paketler",
                      "korpus", "tohumlar"}
    assert set(o["git"]) == {"commit", "kirli"}
    assert {"bootstrap", "bootstrap_tekrar", "ogrenme_egrisi"} <= set(o["tohumlar"])


def test_ortam_tohumlari_evaluate_ile_ayni():
    """Tohum iki yerde yazılsaydı kayıt yanlış sayıyı taşırdı."""
    from spor_toto.evaluate import BOOTSTRAP_TEKRAR, BOOTSTRAP_TOHUM, EGRI_TOHUM

    t = ortam()["tohumlar"]
    assert t["bootstrap"] == BOOTSTRAP_TOHUM
    assert t["bootstrap_tekrar"] == BOOTSTRAP_TEKRAR
    assert t["ogrenme_egrisi"] == EGRI_TOHUM


def test_ortam_korpus_parmak_izi_artefaktla_ayni():
    from spor_toto.artefakt import korpus_parmak_izi

    assert ortam()["korpus"] == korpus_parmak_izi()


# ─── defter ───────────────────────────────────────────────────────────────

def test_bos_defter_cokmez(tmp_path):
    assert kosumlar(tmp_path) == []
    assert son("agac", tmp_path) is None


def test_defter_eskiden_yeniye(tmp_path):
    import time

    kaydet("a", {}, tmp_path)
    time.sleep(1.1)
    kaydet("b", {}, tmp_path)
    adlar = [k["ad"] for k in kosumlar(tmp_path)]
    assert adlar == ["a", "b"]


def test_son_kosum_ada_gore(tmp_path):
    import time

    kaydet("agac", {"v": 1}, tmp_path)
    time.sleep(1.1)
    kaydet("yigin", {"v": 2}, tmp_path)
    time.sleep(1.1)
    kaydet("agac", {"v": 3}, tmp_path)
    k = son("agac", tmp_path)
    assert k is not None and k["ad"] == "agac"
    from pathlib import Path
    assert json.loads((Path(k["yol"]) / "cikti.json").read_text())["v"] == 3


def test_bozuk_kayit_defteri_dusurmez(tmp_path):
    kaydet("saglam", {}, tmp_path)
    bozuk = tmp_path / "20260101T000000Z-bozuk"
    bozuk.mkdir()
    (bozuk / "ortam.json").write_text("{bozuk", encoding="utf-8")
    yarim = tmp_path / "20260101T000001Z-yarim"
    yarim.mkdir()  # ortam.json hic yok
    adlar = [k["ad"] for k in kosumlar(tmp_path)]
    assert adlar == ["saglam"]


# ─── CLI bağlantısı ───────────────────────────────────────────────────────

def test_cli_bayragi_tek_yerde_tanimli():
    ap = argparse.ArgumentParser()
    cli_ekle(ap)
    assert ap.parse_args([]).kaydet is False
    assert ap.parse_args(["--kaydet"]).kaydet is True


def test_belki_kaydet_bayraksiz_yazmaz(tmp_path, monkeypatch):
    import spor_toto.kosum as K

    monkeypatch.setattr(K, "KOSUM_DIZINI", tmp_path)
    assert K.belki_kaydet("x", {}, argparse.Namespace(kaydet=False)) is None
    assert list(tmp_path.iterdir()) == []


def test_belki_kaydet_bayrakla_yazar(tmp_path, monkeypatch):
    import spor_toto.kosum as K

    monkeypatch.setattr(K, "KOSUM_DIZINI", tmp_path)
    yol = K.belki_kaydet("x", {"a": 1}, argparse.Namespace(kaydet=True))
    assert yol is not None and yol.parent == tmp_path


def test_belki_kaydet_bayragi_olmayan_namespace_ile_calisir():
    """`--kaydet` eklenmemiş bir CLI'dan çağrılırsa **sessizce** atlar."""
    assert belki_kaydet("x", {}, argparse.Namespace()) is None


@pytest.mark.parametrize("modul", [
    "agac", "yigin", "kalibre", "takim_gucu", "evaluate", "kalibrasyon",
    "disari",
])
def test_olcum_clileri_kaydet_bayragini_tasiyor(modul):
    """Belgeye sayı yazan her ölçüm CLI'sı koşumunu kaydedebilmeli.

    Biri unutulursa o ölçümün sayısı yine belgeye girer ama **izsiz**
    girer; Faz 0.4'ün bütün amacı o izin var olması.
    """
    import importlib
    import inspect

    kaynak = inspect.getsource(importlib.import_module(f"spor_toto.{modul}"))
    assert "cli_ekle(ap)" in kaynak, f"{modul}: --kaydet bayragi yok"
    assert "belki_kaydet(" in kaynak, f"{modul}: kosum kaydedilmiyor"
