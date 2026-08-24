"""Avrupa fikstürü — **kör noktanın kapanmasının** denetimi.

**En kritik test `test_dinlenme_uefa_gununu_goruyor`.** Faz 3.4'ün bütün
gerekçesi tek bir cümledir: takım Perşembe Avrupa'da oynadıysa Pazar günü
**üç gün** dinlenmiştir, on gün değil. Enjeksiyon unutulursa `dinlenme_farki`
eskisi gibi yanlış kalır, ölçüm çalışır görünür ve *"yorgunluk fiyatlanmış"*
diye okunur — oysa yorgunluk hiç ölçülmemiştir.

İkincisi `test_yil_donumu_dogru_sariyor`: `football.txt` yılı yalnızca
bölümün ilk tarihinde yazar. Aralık→Ocak geçişinde yıl artırılmazsa Şubat
maçları bir önceki yıla düşer ve "Avrupa'da oynadı mı" sorusu **365 gün**
yanlış cevaplanır.
"""
from __future__ import annotations

from datetime import date

import pytest

from spor_toto.avrupa import (
    _fikstur,
    avrupa_gunleri,
    kapsama,
    pencere_sayisi,
    son_avrupa,
)

METIN = """= UEFA Champions League 2024/25

# Teams 36

▪ League, Matchday 1
  Tue Dec 10 2024
    18:45  FC Bayern München (GER) v Real Madrid CF (ESP)     1-0 (1-0)
    21:00  Liverpool FC (ENG)      v AC Milan (ITA)           3-1 (2-0)
  Wed Jan 15
    21:00  Real Madrid CF (ESP)    v Liverpool FC (ENG)       2-2
"""


# ─── ayrıştırma ───────────────────────────────────────────────────────────

def _coz(metin: str = METIN):
    from scripts.build_avrupa import maclari_coz

    return maclari_coz(metin)


def test_maclar_ayristiriliyor():
    m = _coz()
    assert len(m) == 3
    assert m[0]["ev_ham"] == "FC Bayern München (GER)"
    assert m[0]["dep_ham"] == "Real Madrid CF (ESP)"


def test_yil_donumu_dogru_sariyor():
    """**Asıl bekçi.** Aralık→Ocak geçişinde yıl artmalı."""
    m = _coz()
    assert m[0]["tarih"] == "2024-12-10"
    assert m[1]["tarih"] == "2024-12-10"
    assert m[2]["tarih"] == "2025-01-15", "yil sarmadi — 365 gun yanlis"


def test_ayni_yil_icinde_yil_artmaz():
    from scripts.build_avrupa import maclari_coz

    m = maclari_coz("  Tue Sep 17 2024\n    18:45  A (ENG) v B (ENG)  0-0\n"
                    "  Wed Oct 2\n    21:00  C (ENG) v D (ENG)  1-1\n")
    assert [x["tarih"] for x in m] == ["2024-09-17", "2024-10-02"]


def test_tarihsiz_satir_mac_uretmez():
    from scripts.build_avrupa import maclari_coz

    assert maclari_coz("    18:45  A (ENG) v B (ENG)  0-0\n") == []


# ─── ad eşleme ────────────────────────────────────────────────────────────

def test_sadelestirme_ayirt_edici_kelimeyi_atmaz():
    """`real` atılsaydı "Real Madrid" ile "Real Sociedad" aynı ada düşerdi."""
    from scripts.build_avrupa import sadelestir

    assert sadelestir("Real Madrid CF") != sadelestir("Real Sociedad")
    assert sadelestir("FC Bayern München") == sadelestir("Bayern Munchen")
    assert sadelestir("Bologna FC 1909") == sadelestir("Bologna")


def test_ulke_kodu_bir_kisit(monkeypatch):
    """`(GER)` yalnızca Alman liglerinde aranır — yanlış eşleşme imkânsız."""
    from scripts.build_avrupa import eslestir

    lig_takim = {"D1": {"Bayern Munich"}, "E0": {"Bayern Munich"}}
    r, sebep = eslestir("FC Bayern München (GER)", lig_takim)
    assert r == ("D1", "Bayern Munich") and sebep == ""


def test_ust_lig_kazanir():
    """Aynı ad iki ligde varsa üst lig seçilir — Avrupa'da oynayan odur."""
    from scripts.build_avrupa import eslestir

    r, _ = eslestir("Villarreal CF (ESP)", {"SP1": {"Villarreal"},
                                            "SP2": {"Villarreal"}})
    assert r == ("SP1", "Villarreal")


def test_bulanik_esleme_yok():
    """Alt dize eşlemesi yok: "Rangers" ile "Cove Rangers" karışmaz."""
    from scripts.build_avrupa import eslestir

    r, sebep = eslestir("Rangers FC (SCO)", {"SC1": {"Cove Rangers"}})
    assert r is None and sebep


def test_korpus_disi_ulke_sebebiyle_atlanir():
    from scripts.build_avrupa import eslestir

    r, sebep = eslestir("FK Crvena Zvezda (SRB)", {"T1": {"Fenerbahce"}})
    assert r is None and "SRB" in sebep


def test_ulke_kodu_olmayan_ad_reddedilir():
    from scripts.build_avrupa import eslestir

    r, sebep = eslestir("Bir Takim", {"T1": {"Fenerbahce"}})
    assert r is None and "ulke kodu" in sebep


def test_elle_tablosu_korpusla_tutarli():
    """`ELLE`'deki her hedef ad korpusta **gerçekten** bulunmalı.

    Yanlış yazılmış tek bir satır sessizce kapsama düşürür; bu bekçi onu
    ada göre yakalar.
    """
    from scripts.build_avrupa import ELLE, _korpus_takimlari

    lig_takim = _korpus_takimlari()
    if not lig_takim:
        pytest.skip("egitim korpusu yok")
    hepsi = set().union(*lig_takim.values())
    eksik = sorted({v for v in ELLE.values() if v not in hepsi})
    assert not eksik, f"ELLE tablosunda korpusta olmayan ad: {eksik}"


# ─── takvim aritmetiği ────────────────────────────────────────────────────

GUNLER = [date(2024, 9, 17), date(2024, 10, 2), date(2024, 10, 23)]


def test_son_avrupa_kesinlikle_gecmise_bakar():
    """**Sızıntı bekçisi.** Maçın kendi günü sayılmaz, sonrası hiç sayılmaz."""
    assert son_avrupa(GUNLER, date(2024, 10, 3)) == date(2024, 10, 2)
    assert son_avrupa(GUNLER, date(2024, 10, 2)) == date(2024, 9, 17)
    assert son_avrupa(GUNLER, date(2024, 9, 17)) is None
    assert son_avrupa(GUNLER, date(2024, 9, 1)) is None


def test_pencere_sayisi_gecmisi_sayar():
    assert pencere_sayisi(GUNLER, date(2024, 10, 6), 10) == 1
    assert pencere_sayisi(GUNLER, date(2024, 10, 3), 30) == 2
    assert pencere_sayisi(GUNLER, date(2024, 9, 17), 30) == 0


def test_pencere_bugunu_saymaz():
    """Maçın kendisi 'son N günde oynanan' değildir."""
    assert pencere_sayisi([date(2024, 10, 2)], date(2024, 10, 2), 10) == 0


def test_pencere_egitimle_ayni():
    """İki sabit ayrışırsa aynı adı taşıyıp farklı şeyi ölçerler."""
    from spor_toto.avrupa import _pencere
    from spor_toto.egitim import SIKISIKLIK_PENCERE_GUN

    assert _pencere() == SIKISIKLIK_PENCERE_GUN


def test_bos_gunlerde_cokmez():
    assert son_avrupa([], date(2024, 1, 1)) is None
    assert pencere_sayisi([], date(2024, 1, 1), 10) == 0


# ─── enjeksiyon — Faz 3.4'ün bütün gerekçesi ──────────────────────────────

def test_dinlenme_uefa_gununu_goruyor(monkeypatch):
    """**Asıl bekçi.** Perşembe Avrupa + Pazar lig = 3 gün, 10 değil."""
    import spor_toto.avrupa as A
    from spor_toto.egitim import _takvim_tablosu

    satirlar = [
        {"sezon": "2425", "lig": "T1", "tarih": "2025-01-05",
         "ev": "A", "dep": "B", "kod": "1"},
        {"sezon": "2425", "lig": "T1", "tarih": "2025-01-15",
         "ev": "A", "dep": "B", "kod": "1"},
    ]

    monkeypatch.setattr(A, "avrupa_gunleri", lambda yol=None: {})
    yok = _takvim_tablosu(satirlar)[1]

    monkeypatch.setattr(A, "avrupa_gunleri",
                        lambda yol=None: {"A": [date(2025, 1, 12)]})
    var = _takvim_tablosu(satirlar)[1]

    # UEFA yokken iki takim da 10 gun dinlenmis: fark 0.
    assert yok["dinlenme_farki"] == 0.0
    # A 12 Ocak'ta oynadi: 3 gun dinlendi, B 10 gun. Fark NEGATIF (dep lehine).
    assert var["dinlenme_farki"] == pytest.approx(3.0 - 10.0)


def test_sikisiklik_uefa_macini_sayiyor(monkeypatch):
    import spor_toto.avrupa as A
    from spor_toto.egitim import _takvim_tablosu

    satirlar = [
        {"sezon": "2425", "lig": "T1", "tarih": "2025-01-05",
         "ev": "A", "dep": "B", "kod": "1"},
        {"sezon": "2425", "lig": "T1", "tarih": "2025-01-12",
         "ev": "A", "dep": "B", "kod": "0"},
    ]
    monkeypatch.setattr(A, "avrupa_gunleri", lambda yol=None: {})
    yok = _takvim_tablosu(satirlar)[1]
    monkeypatch.setattr(A, "avrupa_gunleri",
                        lambda yol=None: {"B": [date(2025, 1, 9)]})
    var = _takvim_tablosu(satirlar)[1]

    assert yok["sikisiklik_farki"] == 0.0
    # Deplasmanin fazladan bir maci EV lehinedir: pozitif.
    assert var["sikisiklik_farki"] == pytest.approx(1.0)


def test_avrupa_farki_isaret_duzeni(monkeypatch):
    """Bütün A3 özellikleriyle aynı: pozitif = ev lehine."""
    import spor_toto.avrupa as A
    from spor_toto.egitim import _takvim_tablosu

    satirlar = [{"sezon": "2425", "lig": "T1", "tarih": "2025-01-12",
                 "ev": "A", "dep": "B", "kod": "1"}]
    monkeypatch.setattr(A, "avrupa_gunleri",
                        lambda yol=None: {"B": [date(2025, 1, 9)]})
    assert _takvim_tablosu(satirlar)[0]["avrupa_farki"] == pytest.approx(1.0)

    monkeypatch.setattr(A, "avrupa_gunleri",
                        lambda yol=None: {"A": [date(2025, 1, 9)]})
    assert _takvim_tablosu(satirlar)[0]["avrupa_farki"] == pytest.approx(-1.0)


def test_gelecegi_gormez(monkeypatch):
    """Maçtan **sonraki** bir UEFA maçı hiçbir sayıyı değiştirmemeli."""
    import spor_toto.avrupa as A
    from spor_toto.egitim import _takvim_tablosu

    satirlar = [{"sezon": "2425", "lig": "T1", "tarih": "2025-01-12",
                 "ev": "A", "dep": "B", "kod": "1"}]
    monkeypatch.setattr(A, "avrupa_gunleri", lambda yol=None: {})
    temiz = _takvim_tablosu(satirlar)[0]
    monkeypatch.setattr(A, "avrupa_gunleri",
                        lambda yol=None: {"A": [date(2025, 1, 20)],
                                          "B": [date(2025, 2, 1)]})
    gelecek = _takvim_tablosu(satirlar)[0]
    assert gelecek["dinlenme_farki"] == temiz["dinlenme_farki"]
    assert gelecek["sikisiklik_farki"] == temiz["sikisiklik_farki"]
    assert gelecek["avrupa_farki"] == 0.0


def test_fikstur_yoksa_ozellik_notr(monkeypatch):
    """Dosya yoksa sistem çalışmayı sürdürür; sayı **sıfır**, uydurma değil."""
    import spor_toto.avrupa as A
    from spor_toto.egitim import _takvim_tablosu

    monkeypatch.setattr(A, "VARSAYILAN_FIKSTUR",
                        A.KOK / "data" / "yok_boyle.csv")
    A._fikstur.cache_clear()
    try:
        assert avrupa_gunleri() == {}
        satirlar = [{"sezon": "2425", "lig": "T1", "tarih": "2025-01-12",
                     "ev": "A", "dep": "B", "kod": "1"}]
        r = _takvim_tablosu(satirlar)[0]
        assert r["avrupa_farki"] == 0.0 and r["avrupa_var"] is False
    finally:
        A._fikstur.cache_clear()


# ─── gerçek dosya ─────────────────────────────────────────────────────────

def test_gercek_fikstur_okunuyor():
    g = avrupa_gunleri()
    if not g:
        pytest.skip("avrupa fiksturu yok — scripts/build_avrupa.py")
    assert len(g) > 50
    for gunler in g.values():
        assert gunler == sorted(gunler), "siralanmamis liste ikili aramayi bozar"


def test_gercek_fikstur_korpusa_dokunuyor():
    """Kapsama sıfırsa ölçüm bir şeyi değil **hiçbir şeyi** ölçer."""
    from spor_toto.egitim import korpus_yukle

    satirlar = korpus_yukle()
    if not satirlar or not _fikstur():
        pytest.skip("korpus ya da fikstur yok")
    k = kapsama(satirlar)
    assert k["mac"] > 500 and k["takim"] > 50
    assert 0.01 < k["oran"] < 0.30, k
