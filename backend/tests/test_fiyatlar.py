"""Fiyat kaynakları katmanı — üç bahisçi × açılış/kapanış.

Bu testlerin çakıdığı şey **sayının kendisi değil, kaydın tamlığı**: her
fiyatın kitabı, dönemi ve kapsadığı tarih aralığı yazılı mı. Bir Brier
değerini çakmak, arşiv güncellendiğinde testi kırar ve kırılma bir hata
değil veri yenilenmesi olurdu.

Tek istisna omurga çapasıdır (`test_omurga_oynamadi`): fiyat katmanı
eklenirken yayımlanmış sayıların **bit birebir aynı** kalması gerekiyordu
ve bu, planın kabul ölçütüydü.
"""
from __future__ import annotations

import pytest

from spor_toto.backtest import backtest
from spor_toto.fiyatlar import (
    DONEMLER,
    KITAPLAR,
    mac_fiyatlari,
    sezon_fiyat_ozeti,
)
from spor_toto.odds import (
    FIYAT_VARSAYILAN,
    KAYNAK_SIRASI,
    donem_dagilimi,
    load_odds,
    provenance_notu,
    season_1x2_summary,
)


@pytest.fixture(scope="module")
def ozet():
    return sezon_fiyat_ozeti()


# ─── omurga çapası ────────────────────────────────────────────────────────────

def test_omurga_fiyat_sirasinin_basinda():
    """Omurga `KAYNAK_SIRASI`nın ilk elemanı olmalı.

    İkisi ayrı yerde tanımlı olsaydı biri değişip öteki kalabilirdi ve
    `market_odds` varsayılanı ile arşivin gerçekte kullandığı fiyat sessizce
    ayrışırdı.
    """
    assert KAYNAK_SIRASI[0] == FIYAT_VARSAYILAN


def test_omurga_oynamadi():
    """Fiyat katmanı eklendi, **yayımlanmış sayılar değişmedi**.

    Planın kabul ölçütü buydu: üç fiyatı ölçmek, ölçülen fiyatı
    değiştirmemeliydi. Bu değerler değişikliklerden ÖNCE alındı.
    """
    o = season_1x2_summary()
    assert o["books"] == ["Avg"]
    assert o["with_odds"] == 567
    assert o["brier_avg"] == pytest.approx(0.5787, abs=1e-4)
    assert o["avg_margin_pct"] == pytest.approx(7.26, abs=1e-2)

    g = backtest()
    assert g["meta"]["weeks_available"] == 41
    assert g["meta"]["weeks_used"] == 36


# ─── provenance ───────────────────────────────────────────────────────────────

def test_provenance_kitabi_ve_donemi_adlandirir():
    """Not **üretilir**; sabit yazılmaz.

    Eskiden "piyasa kapanış oranları — iddaa oranı değildir" diye sabitti
    ve hangi bahisçi olduğunu söylemiyordu; fiyat değişse okuyucu
    anlamazdı.
    """
    n = provenance_notu([{"book": "PS", "closing": True}] * 3)
    assert "Pinnacle" in n
    assert "kapanış" in n


def test_provenance_karisimi_ILAN_eder():
    """Kapanış+açılış karışımı sessiz kalmamalı — ölçek karışıyor demektir."""
    n = provenance_notu([{"book": "Avg", "closing": True},
                         {"book": "Avg", "closing": False}])
    assert "KARIŞIK" in n
    assert donem_dagilimi([{"book": "Avg", "closing": True},
                           {"book": "Avg", "closing": False}]) == {
        "kapanis": 1, "acilis": 1}


def test_sezon_ozeti_provenance_tasir():
    o = season_1x2_summary()
    assert o["periods"]["kapanis"] + o["periods"]["acilis"] == o["with_odds"]
    assert o["note"] and "iddaa oranı değildir" in o["note"]


# ─── fiyat katmanı ────────────────────────────────────────────────────────────

def test_mac_fiyatlari_her_blokta_kitap_ve_donem_yazar(ozet):
    satir = next(r for r in load_odds() if r.get("matched"))
    f = mac_fiyatlari(satir)
    assert f, "en az bir fiyat bulunmali"
    for anahtar, blok in f.items():
        assert blok["book"] in KITAPLAR
        assert isinstance(blok["closing"], bool)
        assert anahtar == f"{blok['book']}_{'kapanis' if blok['closing'] else 'acilis'}"
        assert set(blok["probs"]) == {"1", "0", "2"}
        assert blok["margin"] > 0


def test_ozet_her_kaynagin_DONEMINI_yazar(ozet):
    """Kapsama tek başına yanıltıcı: eksiklik zamana bağlı olabilir.

    Pinnacle arşivin ~%40'ını kapsıyor ama eksik olan yarı rastgele değil —
    football-data 2026-01'de Pinnacle yayımlamayı bıraktı. Tarih aralığı
    yazılmazsa o %40 "rastgele yarısı var" gibi okunur ve Brier'i sezonun
    tamamına aitmiş sanılır.
    """
    for s in ozet["sources"]:
        assert s["first_day"] and s["last_day"], s["key"]
        assert s["first_day"] <= s["last_day"]
        assert 0 < s["coverage_pct"] <= 100
        assert s["book_label"], "kitabin okunur adi yazilmali"


def test_pinnacle_bosluğu_KAYITLI(ozet):
    """Pinnacle'ın zaman boşluğu beklenen ve kayıtlı bir olgudur.

    Bu test bir kusuru değil, **bilinen bir veri sınırını** çakar: gün
    gelip football-data Pinnacle'ı geri yayımlarsa test kırılır ve bu iyi
    bir kırılmadır — omurga kararı (`odds.FIYAT_VARSAYILAN` gerekçesi)
    yeniden ölçülmelidir.
    """
    ps = [s for s in ozet["sources"] if s["book"] == "PS"]
    assert ps, "arsivde Pinnacle sutunlari olmali"
    avg = next(s for s in ozet["sources"]
               if s["book"] == FIYAT_VARSAYILAN and s["closing"])
    for s in ps:
        assert s["coverage_pct"] < avg["coverage_pct"], (
            "Pinnacle omurgadan daha genis kapsiyorsa omurga karari "
            "yeniden olculmeli")
        assert s["last_day"] < avg["last_day"], (
            "Pinnacle'in zaman boslugu kapandiysa omurga karari "
            "yeniden olculmeli")


def test_ayrisma_ORTAK_kesitte_olculur(ozet):
    """İki fiyat aynı maçlarda ölçülmezse fark görüşü değil örneklemi ölçer."""
    for a in ozet["agreement"]:
        assert a["a"] != a["b"]
        assert a["n"] > 0
        assert a["period"] in ("acilis", "kapanis")
        # Ortak kesit, iki kaynagin tek tek kapsamasindan buyuk olamaz.
        for kitap in (a["a"], a["b"]):
            kaynak = next(s for s in ozet["sources"]
                          if s["book"] == kitap
                          and s["closing"] == (a["period"] == "kapanis"))
            assert a["n"] <= kaynak["n"]


def test_hareket_ayni_ailenin_iki_ucunu_esler(ozet):
    """Açılışı bir kitaptan, kapanışı başkasından almak hareket ölçmez."""
    assert ozet["movement"], "en az bir kitapta acilis+kapanis cifti olmali"
    for m in ozet["movement"]:
        assert m["book"] in KITAPLAR
        assert m["n"] > 0
        assert m["mean_move_pct"] >= 0


def test_bayat_kapanis_arsivde_de_var(ozet):
    """3. haftanın bulgusu bir bülten tuhaflığı değil, tekrarlayan bir olgu.

    Nesine'nin 10–15. maç kapanışı açılışıyla birebir aynıydı. Arşivde de
    aynı denetim koşar; toplayıcı sütunlarda (Avg) hiç görülmez çünkü
    onlar her zaman oynar, tekil bahisçide görülür.
    """
    bayat = {b["book"]: b for b in ozet["stale_closing"]}
    assert bayat, "bayat denetimi cikti uretmeli"
    for b in bayat.values():
        assert 0 <= b["identical"] <= b["pairs"]
    if FIYAT_VARSAYILAN in bayat:
        assert bayat[FIYAT_VARSAYILAN]["identical"] == 0, (
            "toplayici sutun bayat cikiyorsa arsiv uretiminde sorun var")


def test_donemler_market_odds_bayragiyla_ayni():
    """`DONEMLER` `market_odds(closing=)` ile aynı anlamı taşımalı."""
    assert dict(DONEMLER) == {"acilis": False, "kapanis": True}
