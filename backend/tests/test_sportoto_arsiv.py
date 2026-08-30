"""Spor Toto resmî arşivi — ayrıştırma, doğrulama ve yayındaki dosya denetimi.

Testler **ağa çıkmaz**: gerçek uçtan alınmış şekle birebir uyan küçük bir
payload üzerinde çalışır. Ağın kendisi test edilmez; ayrıştırmanın doğruluğu
ise arşivin tamamının dayandığı şeydir.

Bu veri setinin ne olduğu kadar **ne olmadığı** da burada bekçiye bağlanır:
resmî uç maç listesi vermez, dolayısıyla bu dosyalar hiçbir zaman 15 maçlık
1/0/2 dizisi taşımaz. Bir gün taşımaya başlarsa o, yeni bir köken sınıfıdır
ve sessizce olmamalıdır.
"""

import importlib
import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
arsiv = importlib.import_module("scripts.build_sportoto_arsiv")

ARSIV_DIZIN = KOK / "data" / "sportoto_arsiv"


def _hafta(kimlik=368, ad="1. Hafta", yil="2023/2024",
           kapanis="2023-08-11T20:55:00", ek="spor-toto-listesi-1-hafta-vx3sgbj1.jpg"):
    """Uçtan gelen `GameRound` kaydının birebir şekli."""
    return {
        "name": ad, "shortName": None,
        "startDate": "0001-01-01T00:00:00", "endDate": "0001-01-01T00:00:00",
        "year": yil, "roundCloseDate": kapanis,
        "gameRoundStatus": 0, "isPublished": True,
        "attachment": ({"attachmentName": ek, "attachmentType": 0,
                        "id": "4a1443f0-3f07-4258-b2c3-08dbad12e080"} if ek else None),
        "id": kimlik,
    }


ORNEK_SONUC = {
    "fifteenWinPrize": 1734435.88, "fifteenWinCount": 3,
    "fourteenWinPrize": 27278.15, "fourteenWinCount": 109,
    "thirteenWinPrize": 1387.45, "thirteenWinCount": 2143,
    "twelveWinPrize": 167.30, "twelveWinCount": 22215,
    "resultDescription": "Tebrikler", "isPublished": None,
    "gameRoundId": 0, "gameRoundName": None,
    "gameRoundCloseDate": "2023-08-11T20:55:00", "id": 0,
}


# ─── sarmal ───────────────────────────────────────────────────────────────────

def test_govde_sarmali_acilir():
    assert arsiv._govde({"object": [1, 2], "isSucceed": True, "isFailed": False}) == [1, 2]


def test_kayit_yok_hata_degildir():
    """`object: null` + `isSucceed: true` ucun 'kayit yok' cevabidir.

    Kapanmamis hafta boyle doner. Hata sayilirsa tum kosum duser.
    """
    cevap = {"object": None, "status": 2, "message": "Kayıt bulunamadı",
             "isSucceed": True, "isFailed": False}
    assert arsiv._govde(cevap) is None


def test_basarisiz_cevap_hata_verir():
    with pytest.raises(RuntimeError):
        arsiv._govde({"object": None, "isSucceed": False, "isFailed": True,
                      "message": "Kayıt bulunamadı"})


# ─── ayrıştırma ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ad,beklenen", [
    ("1. Hafta", 1), ("9. Hafta", 9), ("53. Hafta", 53), (" 12 . Hafta ", 12),
])
def test_hafta_no_okunur(ad, beklenen):
    assert arsiv.hafta_no(ad) == beklenen


@pytest.mark.parametrize("ad", ["Final Haftası", "", "Hafta", "1. Tur"])
def test_hafta_no_tahmin_edilmez(ad):
    """Doktrin 2: desene uymayan ad'dan numara UYDURULMAZ."""
    assert arsiv.hafta_no(ad) is None


def test_sezon_anahtari():
    assert arsiv.sezon_anahtari("2023/2024") == "2023_24"
    assert arsiv.sezon_anahtari("2026/2027") == "2026_27"


def test_bozuk_sezon_reddedilir():
    with pytest.raises(ValueError):
        arsiv.sezon_anahtari("2023")


def test_bos_tarih_alani_none_olur():
    """Uc bos tarihi "0001-01-01T00:00:00" yaziyor; bu bir tarih degildir."""
    assert arsiv._tarih("0001-01-01T00:00:00") is None
    assert arsiv._tarih("") is None
    assert arsiv._tarih(None) is None
    assert arsiv._tarih("2023-08-11T20:55:00") == "2023-08-11 20:55"


def test_ikramiye_kademeleri_15ten_12ye_siralanir():
    odeme = arsiv.ikramiye_ayristir(ORNEK_SONUC)
    assert [k["correct"] for k in odeme["tiers"]] == [15, 14, 13, 12]
    assert odeme["tiers"][0] == {"correct": 15, "winners": 3, "prize": 1734435.88}
    assert odeme["currency"] == "TRY"
    assert odeme["close_date"] == "2023-08-11 20:55"


def test_eksik_kademe_sifir_sayilmaz():
    """"kimse bilemedi" ile "veri yok" ayri seylerdir."""
    ham = dict(ORNEK_SONUC, fifteenWinCount=None, fifteenWinPrize=None)
    odeme = arsiv.ikramiye_ayristir(ham)
    assert [k["correct"] for k in odeme["tiers"]] == [14, 13, 12]

    sifirli = dict(ORNEK_SONUC, fifteenWinCount=0, fifteenWinPrize=0)
    odeme_sifirli = arsiv.ikramiye_ayristir(sifirli)
    assert odeme_sifirli["tiers"][0] == {"correct": 15, "winners": 0, "prize": 0.0}


def test_ikramiyesiz_hafta_none_tasir():
    assert arsiv.ikramiye_ayristir(None) is None
    assert arsiv.ikramiye_ayristir({}) is None


def test_hafta_kaydi_gorseli_adresler_indirmez():
    kayit = arsiv.hafta_kaydi(_hafta(), arsiv.ikramiye_ayristir(ORNEK_SONUC))
    assert kayit["week"] == 1
    assert kayit["season"] == "2023/2024"
    assert kayit["game_round_id"] == 368
    assert kayit["bulletin_image"]["url"].startswith(
        "https://webapi.sportoto.gov.tr/image/")
    assert kayit["data_warnings"] == []


def test_celisen_kapanis_tarihi_raporlanir():
    """Doktrin 4: iki uc farkli tarih verirse biri sessizce secilmez."""
    kayit = arsiv.hafta_kaydi(
        _hafta(kapanis="2023-08-12T20:55:00"),
        arsiv.ikramiye_ayristir(ORNEK_SONUC),
    )
    assert len(kayit["data_warnings"]) == 1
    assert "kapanis tarihi" in kayit["data_warnings"][0]


def test_anlasilmayan_hafta_adi_elenmez_isaretlenir():
    kayit = arsiv.hafta_kaydi(_hafta(ad="Final Haftası"), None)
    assert kayit["week"] is None
    assert kayit["data_warnings"]
    assert kayit["name"] == "Final Haftası"


# ─── doğrulama kapısı ─────────────────────────────────────────────────────────

def test_dogrulama_saglam_seti_gecirir():
    haftalar = [arsiv.hafta_kaydi(_hafta(kimlik=368, ad="1. Hafta"),
                                  arsiv.ikramiye_ayristir(ORNEK_SONUC)),
                arsiv.hafta_kaydi(_hafta(kimlik=369, ad="2. Hafta"), None)]
    arsiv.dogrula({"2023_24": haftalar})


def test_mukerrer_hafta_yazilmaz():
    haftalar = [arsiv.hafta_kaydi(_hafta(kimlik=368, ad="1. Hafta"), None),
                arsiv.hafta_kaydi(_hafta(kimlik=369, ad="1. Hafta"), None)]
    with pytest.raises(AssertionError, match="mukerrer hafta"):
        arsiv.dogrula({"2023_24": haftalar})


def test_tek_dosyada_iki_sezon_yazilmaz():
    haftalar = [arsiv.hafta_kaydi(_hafta(kimlik=368, ad="1. Hafta"), None),
                arsiv.hafta_kaydi(_hafta(kimlik=500, ad="2. Hafta",
                                         yil="2024/2025"), None)]
    with pytest.raises(AssertionError, match="birden fazla sezon"):
        arsiv.dogrula({"2023_24": haftalar})


def test_bos_sezon_yazilmaz():
    with pytest.raises(AssertionError):
        arsiv.dogrula({"2023_24": []})


# ─── yayındaki dosyalar ───────────────────────────────────────────────────────

def _yayindaki_sezonlar():
    return sorted(p for p in ARSIV_DIZIN.glob("*.json") if p.name != "arsiv_rapor.json")


def test_yayindaki_arsiv_okunabilir():
    dosyalar = _yayindaki_sezonlar()
    if not dosyalar:
        pytest.skip("arşiv henüz üretilmemiş (scripts/build_sportoto_arsiv.py)")
    for yol in dosyalar:
        govde = json.loads(yol.read_text(encoding="utf-8"))
        assert govde["meta"]["season_key"] == yol.stem
        assert govde["meta"]["weeks"] == len(govde["weeks"])
        arsiv.dogrula({yol.stem: govde["weeks"]})


def test_yayindaki_arsivde_kupon_dizisi_YOK():
    """Bu setin sınırı: resmî uç maç listesi vermez.

    Bir gün verirse bu test kırılır ve kırılması DOĞRUDUR — o zaman köken
    sınıfı değişmiş demektir ve belgeyle birlikte bilinçli güncellenir.
    """
    dosyalar = _yayindaki_sezonlar()
    if not dosyalar:
        pytest.skip("arşiv henüz üretilmemiş")
    for yol in dosyalar:
        govde = json.loads(yol.read_text(encoding="utf-8"))
        for hafta in govde["weeks"]:
            assert "results" not in hafta
            assert "matches" not in hafta


def test_yayindaki_arsiv_st_history_ile_karismaz():
    """İki veri seti ayrı kalır: biri kupon sonucu, öteki ikramiye/havuz."""
    dosyalar = _yayindaki_sezonlar()
    if not dosyalar:
        pytest.skip("arşiv henüz üretilmemiş")
    assert not (ARSIV_DIZIN / "st_history_2025_26.json").exists()
    for yol in dosyalar:
        meta = json.loads(yol.read_text(encoding="utf-8"))["meta"]
        assert "does_not_contain" in meta, "sınır meta'da yazılı olmalı"
        assert "source" in meta and "sportoto.gov.tr" in meta["source"]


def test_rapor_yayindaysa_tutarli():
    rapor_yol = ARSIV_DIZIN / "arsiv_rapor.json"
    if not rapor_yol.exists():
        pytest.skip("arşiv henüz üretilmemiş")
    rapor = json.loads(rapor_yol.read_text(encoding="utf-8"))
    toplam = 0
    odemeli = 0
    for anahtar, ozet in rapor["seasons"].items():
        yol = ARSIV_DIZIN / f"{anahtar}.json"
        assert yol.exists(), f"raporda var, dosyası yok: {anahtar}"
        govde = json.loads(yol.read_text(encoding="utf-8"))
        assert ozet["weeks"] == len(govde["weeks"])
        assert ozet["with_payout"] == sum(1 for h in govde["weeks"] if h["payout"])
        toplam += ozet["weeks"]
        odemeli += ozet["with_payout"]
    assert rapor["totals"]["weeks"] == toplam
    assert rapor["totals"]["with_payout"] == odemeli
    assert rapor["limits"], "sınırlar raporda yazılı olmalı"
