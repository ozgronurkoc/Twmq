"""Model kalıcılığı — **bayatlığın görünürlüğünün** denetimi.

**En kritik iki test `test_yuklenen_model_ayni_tahmini_veriyor` ile
`test_korpus_degisince_bayat.`** İkisi de aynı sessiz hatayı kovalıyor:
artefakt yerinde kalır, korpus değişir, servis çalışmaya devam eder ve
*eski* dünyanın sayısını üretir. Hiçbir sözleşme kırılmaz, hiçbir test
düşer — tahmin yalnızca başka bir şeyin tahmini olur.

Üçüncüsü `test_durum_sutun_duzenini_de_tasiyor`: `_theta` tek başına
taşınsaydı katsayılar geri gelir ama **başka sütunlara** binerdi.
"""
from __future__ import annotations

import json

import pytest

from spor_toto import __version__
from spor_toto.artefakt import (
    BICIM,
    bayat_mi,
    durum,
    korpus_parmak_izi,
    oku,
    uretim_tahmincisi,
    yaz,
    zarf_oku,
)
from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.recalibrate import KalibreTahminci

PIYASA = {"1": 0.50, "0": 0.28, "2": 0.22}


def _girdi(week: int, results: str) -> dict:
    return {"week": week, "close_date": "2026-01-01", "results": results,
            "probs": [dict(PIYASA)] * MATCH_COUNT, "missing": 0,
            "usable": True, "sezon": "2025-26",
            "ozellikler": [{"probs": dict(PIYASA)} for _ in range(MATCH_COUNT)]}


def _kesit(n: int = 6) -> list[dict]:
    import random

    rnd = random.Random(11)
    return [_girdi(w, "".join(rnd.choice(SYMBOLS) for _ in range(MATCH_COUNT)))
            for w in range(n)]


@pytest.fixture
def korpus(tmp_path):
    """Sahte bir korpus dosyası — parmak izi gerçek bir dosyadan alınır."""
    p = tmp_path / "korpus.csv"
    p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    return p


# ─── parmak izi ───────────────────────────────────────────────────────────

def test_parmak_izi_dosyadan_geliyor(korpus):
    p = korpus_parmak_izi(korpus)
    assert p["var"] is True
    assert len(p["sha256"]) == 64
    assert p["satir"] == 3
    assert p["bayt"] == korpus.stat().st_size


def test_parmak_izi_icerik_degisince_degisir(korpus):
    once = korpus_parmak_izi(korpus)["sha256"]
    korpus.write_text("a,b\n1,2\n3,5\n", encoding="utf-8")
    assert korpus_parmak_izi(korpus)["sha256"] != once


def test_parmak_izi_olmayan_dosyada_cokmez(tmp_path):
    """Korpussuz kurulum geçerli bir kurulumdur — istatistik katmanı ondan
    bağımsız çalışır."""
    p = korpus_parmak_izi(tmp_path / "yok.csv")
    assert p["var"] is False and "sha256" not in p


def test_parmak_izi_yolu_mutlak_degil(korpus):
    """Artefakt taşınabilir olmalı: mutlak yol yazılmaz."""
    for hedef in (korpus, korpus.parent / "yok.csv"):
        assert not korpus_parmak_izi(hedef)["yol"].startswith("/")


# ─── yaz / oku ────────────────────────────────────────────────────────────

def _egitilmis() -> KalibreTahminci:
    t = KalibreTahminci("bias")
    t.egit(_kesit())
    return t


def test_yaz_oku_turu(tmp_path, korpus):
    t = _egitilmis()
    p = yaz(t, tmp_path, korpus)
    assert p.exists() and p.name == "kalibre_bias.json"

    geri = KalibreTahminci("bias")
    yuklendi, sebep = oku(geri, tmp_path, korpus)
    assert yuklendi is True and sebep == ""


def test_yuklenen_model_ayni_tahmini_veriyor(tmp_path, korpus):
    """**Asıl bekçi.** Diskten dönen model, eğitilmiş modelle aynı olmalı."""
    t = _egitilmis()
    yaz(t, tmp_path, korpus)
    geri = KalibreTahminci("bias")
    assert oku(geri, tmp_path, korpus)[0] is True

    hafta = _girdi(99, "1" * MATCH_COUNT)
    assert geri.tahmin(hafta) == t.tahmin(hafta)


def test_durum_sutun_duzenini_de_tasiyor():
    """`_theta` tek başına yetmez: lig ve bant sütunları düzeni belirler."""
    t = KalibreTahminci("bant")
    d = t.durum()
    assert set(d) == {"kademe", "ligler", "bantlar", "theta"}


def test_durum_json_serilestirilebilir(tmp_path, korpus):
    """JSON seçildi ki artefakt `cat` ile okunabilsin — bekçisi bu."""
    p = yaz(_egitilmis(), tmp_path, korpus)
    zarf = json.loads(p.read_text(encoding="utf-8"))
    assert zarf["bicim"] == BICIM
    assert zarf["surum"] == __version__
    assert zarf["tahminci"] == "kalibre_bias"
    assert zarf["egitim_tarihi"].endswith("+00:00")


def test_egitilmemis_model_de_yazilip_okunabiliyor(tmp_path, korpus):
    """Eğitilmemiş model `theta=None` taşır; okunduğunda piyasayı geçirir."""
    t = KalibreTahminci("bias")
    yaz(t, tmp_path, korpus)
    geri = KalibreTahminci("bias")
    assert oku(geri, tmp_path, korpus)[0] is True
    assert geri.tahmin(_girdi(1, "1" * MATCH_COUNT))[0] == PIYASA


def test_yazma_atomik(tmp_path, korpus):
    """Yarım yazılmış artefakt 'bayat' değil 'bozuk'tur — ikisi ayrı şey."""
    yaz(_egitilmis(), tmp_path, korpus)
    assert not list(tmp_path.glob("*.tmp"))


# ─── bayatlık — kontrolün bütün sebebi ────────────────────────────────────

def test_korpus_degisince_bayat(tmp_path, korpus):
    """**Asıl bekçi.** Korpus değişip artefakt kalırsa okunmamalı."""
    yaz(_egitilmis(), tmp_path, korpus)
    korpus.write_text("a,b\n9,9\n", encoding="utf-8")

    zarf, sebep = zarf_oku("kalibre_bias", tmp_path)
    assert zarf is not None and sebep == ""     # zarf saglam
    assert "korpus degismis" in bayat_mi(zarf, korpus)

    geri = KalibreTahminci("bias")
    yuklendi, neden = oku(geri, tmp_path, korpus)
    assert yuklendi is False and "korpus degismis" in neden


def test_surum_degisince_bayat(tmp_path, korpus):
    """Uydurucu değişirse aynı korpustan başka katsayı çıkar."""
    p = yaz(_egitilmis(), tmp_path, korpus)
    zarf = json.loads(p.read_text(encoding="utf-8"))
    zarf["surum"] = "0.0.0-eski"
    p.write_text(json.dumps(zarf), encoding="utf-8")

    assert zarf_oku("kalibre_bias", tmp_path)[0] is None
    assert "surum degismis" in zarf_oku("kalibre_bias", tmp_path)[1]


def test_bicim_degisince_bayat(tmp_path, korpus):
    p = yaz(_egitilmis(), tmp_path, korpus)
    zarf = json.loads(p.read_text(encoding="utf-8"))
    zarf["bicim"] = BICIM + 1
    p.write_text(json.dumps(zarf), encoding="utf-8")
    assert "bicim eskimis" in zarf_oku("kalibre_bias", tmp_path)[1]


def test_eksik_alan_bayat(tmp_path, korpus):
    p = yaz(_egitilmis(), tmp_path, korpus)
    zarf = json.loads(p.read_text(encoding="utf-8"))
    del zarf["korpus"]
    p.write_text(json.dumps(zarf), encoding="utf-8")
    assert "eksik" in zarf_oku("kalibre_bias", tmp_path)[1]


def test_bozuk_json_cokmez(tmp_path):
    (tmp_path / "kalibre_bias.json").write_text("{bozuk", encoding="utf-8")
    zarf, sebep = zarf_oku("kalibre_bias", tmp_path)
    assert zarf is None and "okunamadi" in sebep


def test_olmayan_artefakt_cokmez(tmp_path):
    assert zarf_oku("yok_boyle", tmp_path) == (None, "artefakt yok")


def test_kademe_tutmayan_durum_reddedilir(tmp_path, korpus):
    """Sessizce başka bir kademeye yüklemek, modeli sessizce değiştirir."""
    yaz(_egitilmis(), tmp_path, korpus)
    zarf, _ = zarf_oku("kalibre_bias", tmp_path)
    assert zarf is not None
    with pytest.raises(ValueError):
        KalibreTahminci("lig").yukle(zarf["durum"])


# ─── durum raporu ─────────────────────────────────────────────────────────

def test_durum_bos_dizinde_cokmez(tmp_path):
    d = durum(tmp_path)
    assert d["artefaktlar"] == [] and d["bayat_sayisi"] == 0


def test_durum_bayati_sayiyor(tmp_path, korpus):
    yaz(_egitilmis(), tmp_path, korpus)
    assert durum(tmp_path, korpus)["bayat_sayisi"] == 0
    korpus.write_text("bambaska\n", encoding="utf-8")
    d = durum(tmp_path, korpus)
    assert d["bayat_sayisi"] == 1
    assert d["artefaktlar"][0]["gecerli"] is True   # zarf saglam, korpus eski


# ─── üretim yolu — tek kaynak ─────────────────────────────────────────────

def test_uretim_tahmincisi_tahmin_modulunun_kullandigi(tmp_path, korpus):
    """Artefakt ile servis **aynı** tahminciyi kurmalı.

    Ayrışsalardı artefakt bir modeli yazar, servis başkasını çalıştırırdı:
    sağlık yeşil, tahmin başka olurdu.
    """
    from spor_toto.tahmin import ALTERNATIF_KADEME

    t = uretim_tahmincisi()
    assert isinstance(t, KalibreTahminci)
    assert t.kademe == ALTERNATIF_KADEME


def test_servis_bayat_artefakti_kullanmaz(tmp_path, korpus, monkeypatch):
    """Servis bayat artefaktı okumaz — okusa eski dünyanın sayısını verir."""
    import spor_toto.artefakt as A

    monkeypatch.setattr(A, "ARTEFAKT_DIZINI", tmp_path)
    yaz(_egitilmis(), tmp_path, korpus)
    korpus.write_text("degisti\n", encoding="utf-8")
    geri = KalibreTahminci("bias")
    assert A.oku(geri, korpus_yolu=korpus)[0] is False


def test_saglik_kontrolu_yoklukta_dusmuyor(tmp_path, monkeypatch):
    """Artefaktın **yokluğu hata değildir**: servis o zaman istekte eğitir."""
    import spor_toto.artefakt as A
    from spor_toto.health import _check_artefakt_tazeligi

    monkeypatch.setattr(A, "ARTEFAKT_DIZINI", tmp_path)
    assert "artefakt yok" in _check_artefakt_tazeligi()


def test_saglik_kontrolu_bayatta_dusuyor(tmp_path, monkeypatch):
    """**Kontrolün bütün sebebi.** Bayat artefakt sağlığı kırmızı yapmalı."""
    import spor_toto.artefakt as A
    from spor_toto.health import _check_artefakt_tazeligi

    monkeypatch.setattr(A, "ARTEFAKT_DIZINI", tmp_path)
    p = yaz(_egitilmis(), tmp_path)
    zarf = json.loads(p.read_text(encoding="utf-8"))
    # Gercek korpus yerinde duruyor; artefakt BASKA bir korpustan gelmis.
    zarf["korpus"] = {"var": True, "yol": "data/egitim/egitim_korpus.csv",
                      "sha256": "0" * 64, "bayt": 1, "satir": 1}
    p.write_text(json.dumps(zarf), encoding="utf-8")

    with pytest.raises(AssertionError, match="bayat artefakt"):
        _check_artefakt_tazeligi()


def test_saglik_kontrolu_tazede_geciyor(tmp_path, monkeypatch):
    """Tazelik gercek korpusa gore olculur; korpussuz kurulumda atlanir."""
    import spor_toto.artefakt as A
    from spor_toto.health import _check_artefakt_tazeligi

    if not korpus_parmak_izi()["var"]:
        pytest.skip("egitim korpusu yok")
    monkeypatch.setattr(A, "ARTEFAKT_DIZINI", tmp_path)
    yaz(_egitilmis(), tmp_path)
    assert "taze" in _check_artefakt_tazeligi()
