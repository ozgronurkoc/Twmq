"""Elo defterinin denetimi.

En kritik test `test_elo_gelecegi_gormez`. Elo bir **birikimdir** ve
biriken bir büyüklükte sızıntı sessizdir: bir maçın kendi sonucu kendi
puan farkına girerse model geleceği görür, skor mucizevi çıkar ve gerçek
maçta hiçbir işe yaramaz. `egitim._form_tablosu` için yazılan bekçinin
aynısı burada da gerekir — ve Elo'da daha kritiktir, çünkü form bir
pencereyken Elo bütün geçmişi taşır.

İkinci grup testler **parametrelerin dışarıdan geldiğini** sabitler.
Elo'nun bu projedeki avantajı, parametrelerini uydurmaya gerek olmaması:
K, ev avantajı ve gol çarpanı yayınlanmış futbol Elo değerleridir. Bir
gün biri onları "iyileştirmek" isterse testler ne yapıldığını söyler.
"""
from __future__ import annotations

from itertools import pairwise

import pytest

from spor_toto.elo import (
    BASLANGIC,
    EN_AZ_MAC,
    EV_AVANTAJI,
    OLCEK,
    SEZON_TASIMA,
    EloDefteri,
    K,
    beklenen,
    elo_tablosu,
    gol_carpani,
)


def _mac(tarih: str, ev: str, dep: str, kod: str,
         ev_gol: int = 1, dep_gol: int = 0, sezon: str = "2324") -> dict:
    return {"tarih": tarih, "lig": "E0", "ev": ev, "dep": dep, "kod": kod,
            "ev_gol": ev_gol, "dep_gol": dep_gol, "sezon": sezon}


#: Herkesin herkesle oynadigi kucuk bir turnuva. Tek maclik rakipler
#: kullanmak yetmez: `EN_AZ_MAC` kapisi IKI tarafa da bakar ve kapi hic
#: acilmazsa sizinti testi bos yere yesil kalir.
_TAKIMLAR = ("A", "B", "C", "D")


def _turnuva() -> list[dict]:
    """4 takim, cift devreli, 24 mac — herkes 12 mac oynar."""
    maclar: list[dict] = []
    gun = 1
    for _ in range(4):
        for i, ev in enumerate(_TAKIMLAR):
            for dep in _TAKIMLAR[i + 1:]:
                maclar.append(_mac(f"2024-{1 + gun // 28:02d}-{1 + gun % 28:02d}",
                                   ev, dep, "102"[len(maclar) % 3],
                                   ev_gol=2, dep_gol=len(maclar) % 3))
                gun += 1
    return maclar


# ─── beklenen skor ────────────────────────────────────────────────────────

def test_esit_puanda_beklenen_yarim():
    assert beklenen(0.0) == pytest.approx(0.5)


def test_olcek_kadar_farkta_bilinen_deger():
    """400 puan fark ≈ %90 — Elo'nun tanımının kendisi."""
    assert beklenen(OLCEK) == pytest.approx(10 / 11, abs=1e-9)
    assert beklenen(-OLCEK) == pytest.approx(1 / 11, abs=1e-9)


def test_beklenen_monoton_ve_sinirli():
    onceki = 0.0
    for fark in range(-800, 801, 50):
        v = beklenen(float(fark))
        assert 0.0 < v < 1.0
        assert v > onceki
        onceki = v


def test_beklenen_simetrik():
    for fark in (37.0, 120.0, 400.0):
        assert beklenen(fark) + beklenen(-fark) == pytest.approx(1.0, abs=1e-12)


# ─── gol çarpanı ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("fark,beklenen_deger", [
    (0, 1.0), (1, 1.0), (-1, 1.0), (2, 1.5), (-2, 1.5),
    (3, 1.75), (4, 1.875), (5, 2.0),
])
def test_gol_carpani_yayinlanmis_degerler(fark, beklenen_deger):
    """World Football Elo Ratings formülü — uydurulmuş değil, alıntı."""
    assert gol_carpani(fark) == pytest.approx(beklenen_deger)


def test_gol_carpani_artan_ama_doyan():
    """Fark büyüdükçe artmalı, ama artış hızı azalmalı.

    Doymasaydı tek bir 7-0 bütün puanı taşırdı.
    """
    degerler = [gol_carpani(m) for m in range(1, 9)]
    assert degerler == sorted(degerler)
    artislar = [b - a for a, b in pairwise(degerler)]
    assert artislar[0] > artislar[-1]


# ─── defter ───────────────────────────────────────────────────────────────

def test_yeni_takim_baslangic_puaninda():
    d = EloDefteri()
    assert d.puan("X") == BASLANGIC
    assert d.mac_sayisi("X") == 0


def test_ev_avantaji_farka_giriyor():
    d = EloDefteri()
    assert d.fark("A", "B") == pytest.approx(EV_AVANTAJI)


def test_puan_sifir_toplamli():
    """Bir takımın kazandığı puan diğerinin kaybettiğidir.

    Bozulursa toplam puan sürüklenir ve farklar zamanla anlamını yitirir.
    """
    d = EloDefteri()
    d.guncelle("A", "B", "1", 2)
    assert d.puan("A") + d.puan("B") == pytest.approx(2 * BASLANGIC)


def test_galibiyet_puan_kazandirir_maglubiyet_kaybettirir():
    d = EloDefteri()
    d.guncelle("A", "B", "1", 1)
    assert d.puan("A") > BASLANGIC
    assert d.puan("B") < BASLANGIC


def test_beraberlikte_ev_sahibi_puan_KAYBEDER():
    """Ev avantajı yüzünden beraberlik ev sahibi için kötü sonuçtur.

    Beklenen skor 0,5'in üstündedir (ev avantajı var), gerçekleşen 0,5 —
    yani ev sahibi beklentisinin altında kalmıştır. Bu Elo'nun doğru
    davranışıdır ve şaşırtıcı göründüğü için yazılı duruyor.
    """
    d = EloDefteri()
    d.guncelle("A", "B", "0", 0)
    assert d.puan("A") < BASLANGIC
    assert d.puan("B") > BASLANGIC


def test_surpriz_galibiyet_daha_cok_puan_tasir():
    zayif = EloDefteri()
    zayif._puan = {"A": 1300.0, "B": 1700.0}
    guclu = EloDefteri()
    guclu._puan = {"A": 1700.0, "B": 1300.0}
    zayif.guncelle("A", "B", "1", 1)
    guclu.guncelle("A", "B", "1", 1)
    assert zayif.puan("A") - 1300.0 > guclu.puan("A") - 1700.0


def test_gol_farki_puani_buyutur():
    dar = EloDefteri()
    genis = EloDefteri()
    dar.guncelle("A", "B", "1", 1)
    genis.guncelle("A", "B", "1", 4)
    assert genis.puan("A") > dar.puan("A")


def test_k_degisimin_ust_sinirini_belirler():
    """Tek maçta puan değişimi `K · çarpan`ı aşamaz."""
    d = EloDefteri()
    d._puan = {"A": 1000.0, "B": 2000.0}
    d.guncelle("A", "B", "1", 5)
    assert d.puan("A") - 1000.0 <= K * gol_carpani(5) + 1e-9


def test_gecersiz_kod_yok_sayilir():
    d = EloDefteri()
    d.guncelle("A", "B", "X", 1)
    assert d.puan("A") == BASLANGIC
    assert d.mac_sayisi("A") == 0


# ─── sezon taşıma ─────────────────────────────────────────────────────────

def test_sezon_basi_ortalamaya_ceker():
    d = EloDefteri()
    d._sezon = "2223"
    d._puan = {"A": 1700.0, "B": 1300.0}
    d.sezon_basi("2324")
    assert d.puan("A") == pytest.approx(1500.0 + SEZON_TASIMA * 200.0)
    assert d.puan("B") == pytest.approx(1500.0 - SEZON_TASIMA * 200.0)


def test_ayni_sezonda_tekrar_cagrilinca_bir_sey_yapmaz():
    d = EloDefteri()
    d.sezon_basi("2324")
    d._puan = {"A": 1700.0, "B": 1300.0}
    d.sezon_basi("2324")
    assert d.puan("A") == 1700.0


def test_sezon_tasima_siralamayi_korur():
    d = EloDefteri()
    d._sezon = "2223"
    d._puan = {"A": 1800.0, "B": 1500.0, "C": 1200.0}
    d.sezon_basi("2324")
    assert d.puan("A") > d.puan("B") > d.puan("C")


# ─── tablo: sızıntı disiplini ─────────────────────────────────────────────

def test_elo_gelecegi_gormez():
    """**Asıl bekçi.** Bir maçın kendi sonucu kendi Elo farkına giremez.

    Kurgu: A her maçı kazanıyor. Son maçtaki fark, o maçtan ÖNCEKİ
    duruma ait olmalı — yani `guncelle`nin son çağrısını içermemeli.
    """
    maclar = _turnuva()
    tablo = elo_tablosu(maclar)
    assert tablo[-1]["elo_var"] is True, "kurgu yetersiz — kapi hic acilmamis"

    # Ayni maclar, SON MAC HARIC elle islenir; defterin o andaki farki
    # tablonun son macta yazdigi farkin ta kendisi olmali.
    d = EloDefteri()
    d.sezon_basi("2324")
    for m in maclar[:-1]:
        d.guncelle(m["ev"], m["dep"], m["kod"],
                   m["ev_gol"] - m["dep_gol"])
    son = maclar[-1]
    assert tablo[-1]["elo_farki"] == pytest.approx(d.fark(son["ev"], son["dep"]))


def test_ilk_maclarda_elo_var_kapali():
    """`EN_AZ_MAC` altındaki takım için fark gürültüdür; bayrak kapalı olmalı."""
    maclar = [_mac(f"2024-01-{g:02d}", "A", f"R{g}", "1") for g in range(1, 4)]
    for kayit in elo_tablosu(maclar):
        assert kayit["elo_var"] is False
        assert kayit["elo_farki"] == 0.0


def test_yeterli_mactan_sonra_elo_var_aciliyor():
    maclar = []
    for g in range(1, 16):
        ev, dep = ("A", "B") if g % 2 else ("B", "A")
        maclar.append(_mac(f"2024-01-{g:02d}", ev, dep, "1"))
    tablo = elo_tablosu(maclar)
    assert tablo[0]["elo_var"] is False
    assert tablo[-1]["elo_var"] is True
    assert EN_AZ_MAC < len(maclar)


def test_tablo_girdiyle_ayni_uzunlukta_ve_sirada():
    """Kayıtlar girdiyle AYNI indekste dönmeli — `zip` ile eşleştiriliyor."""
    maclar = [_mac("2024-03-02", "A", "B", "1"),
              _mac("2024-01-01", "C", "D", "2"),
              _mac("2024-02-01", "E", "F", "0")]
    tablo = elo_tablosu(maclar)
    assert len(tablo) == len(maclar)
    assert all(set(k) == {"elo_var", "elo_farki"} for k in tablo)


def test_tablo_deterministik():
    maclar = [_mac(f"2024-01-{g:02d}", "A", "B", "102"[g % 3]) for g in range(1, 20)]
    t = elo_tablosu(maclar)
    # Bos donen bir govde de "deterministik" olurdu; asagidaki satir
    # sonucun BOS OLMADIGINI da tutar — determinizm tek basina
    # calistigini kanitlamaz.
    assert len(t) == len(maclar), "tablo eksik — determinizm yeterli degil"
    assert t == elo_tablosu(maclar)


def test_tablo_kronolojik_isliyor_girdi_sirasi_onemsiz():
    """Girdi sırası karışık gelse de sonuç tarihe göre hesaplanmalı."""
    maclar = [_mac(f"2024-01-{g:02d}", "A", f"R{g}", "1") for g in range(1, 13)]
    karisik = list(reversed(maclar))
    duz = {(m["tarih"], m["ev"]): k["elo_farki"]
           for m, k in zip(maclar, elo_tablosu(maclar))}
    ters = {(m["tarih"], m["ev"]): k["elo_farki"]
            for m, k in zip(karisik, elo_tablosu(karisik))}
    assert duz == pytest.approx(ters)


def test_gol_alani_eksikse_cokmez():
    """Gol bilgisi yoksa çarpan 1 kabul edilir; satır atlanmaz."""
    maclar = [{k: v for k, v in m.items() if k not in ("ev_gol", "dep_gol")}
              for m in _turnuva()]
    tablo = elo_tablosu(maclar)
    assert tablo[-1]["elo_var"] is True


# ─── korpus üzerinde ──────────────────────────────────────────────────────

def test_korpusta_elo_makul_araliktа():
    """Gerçek veride farklar patlamamalı — patlarsa K ya da taşıma bozuktur."""
    from spor_toto.egitim import korpus_haftalari

    farklar = [o["elo_farki"] for w in korpus_haftalari()
               for o in w["ozellikler"] if o["elo_var"]]
    assert len(farklar) > 20_000
    assert min(farklar) > -800.0
    assert max(farklar) < 800.0
    # Ortalama, ev avantajının kendisi olmalı: puanlar sıfır toplamlı,
    # geriye yalnızca `EV_AVANTAJI` kalır. Sapma varsa taşıma bozuktur.
    ortalama = sum(farklar) / len(farklar)
    assert abs(ortalama - EV_AVANTAJI) < 25.0
