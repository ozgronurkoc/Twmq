"""Kupon kurucu arşivinin bekçileri (`spor_toto/kupon_arsivi.py`).

**Neden ayrıca bekçili.** Bu modül, API'nin **diske yazan ilk** üyesi.
Geri kalan her uç okuyucu: korpusu okur, türetir, döner — yanlış bir girdi
en fazla yanlış bir cevap verir. Burada yanlış bir girdi bir **dosyayı**
etkiler, ve o dosya elle girilmiş, yeniden üretilemeyen bir kayıttır.

Üç şey tutuluyor:

1. **Yol kaçağı yok.** Sezon ve hafta dosya yoluna giriyor; doğrulayıcı
   gevşerse arşiv kökünün dışına yazılabilirdi.
2. **Kayıp yok.** Yarım tablo kaydedilebilir (boş oran `None`), ama
   OKUNABILEN ama geçersiz bir oran sessizce boşa çevrilmez — kullanıcının
   yazdığı bir şeyin kaybolması, hata vermekten kötüdür.
3. **Künye korunur.** Bir haftayı düzeltmek onu yeniden girmek değildir:
   `girildi` üzerine yazmada korunur, `guncellendi` tazelenir.
"""
from __future__ import annotations

import json

import pytest

from spor_toto import kupon_arsivi as ka
from spor_toto.core import SEMBOLLER


@pytest.fixture(autouse=True)
def _gecici_arsiv(tmp_path, monkeypatch):
    """Testler GERÇEK arşive yazmaz.

    Bu fixture `autouse`: unutulabilecek bir şey değil. Bir test gerçek
    ağaca yazsaydı, depo `git status` altında kirlenirdi ve kapı kimsenin
    yazmadığı bir dosyayı gösterirdi.
    """
    monkeypatch.setattr(ka, "ARSIV", tmp_path / "kupon_arsivi")
    return tmp_path


def _satir(i: int = 0, **ek):
    return {"lig": "T1", "ev": f"ev{i}", "dep": f"dep{i}",
            "oran": {"1": "2.0", "0": "3.2", "2": "3.8"}, **ek}


def _govde(**ek):
    return {"sezon": "2026_27", "hafta": 5, "not": "iddaa kapanis",
            "ayar": {"cizgi": "kapanis", "arindirma": "shin", "en_az": 200, "tarih": ""},
            "satirlar": [_satir(i) for i in range(ka.MAC_SAYISI)], **ek}


def test_mac_sayisi_meta_ile_AYNI():
    """15 iki yerde yazılı olamaz.

    `meta.MATCH_COUNT` motorun sayısı; bu modülünki arşivin. Ayrışırlarsa
    14 satırlık bir kayıt sessizce kabul edilir ve geri okunurken 15. maç
    boş gelir.
    """
    from spor_toto.meta import MATCH_COUNT
    assert ka.MAC_SAYISI == MATCH_COUNT


def test_yol_arsiv_kokunun_DISINA_cikamaz():
    for sezon in ("../../etc", "2026_27/../..", "..", "", "26_7", "2026-27"):
        with pytest.raises(ka.ArsivHatasi):
            ka.yol(sezon, 5)
    for hafta in (0, -3, 61, 999, "bes", None):
        with pytest.raises(ka.ArsivHatasi):
            ka.yol("2026_27", hafta)
    # Gecerli deger arsiv kokunun ALTINDA kalmali.
    p = ka.yol("2026_27", 5)
    assert str(p).startswith(str(ka.ARSIV.resolve()))
    assert p.name == "hafta_05.json"


def test_yarim_tablo_kaydedilir_ama_BOZUK_oran_reddedilir():
    # Bos hucre: kullanici tabloyu doldururken de kaydeder.
    yarim = _govde(satirlar=[
        {"lig": "", "ev": "", "dep": "", "oran": {"1": "", "0": None, "2": ""}}
        for _ in range(ka.MAC_SAYISI)
    ])
    kayit = ka.kaydi_kur(yarim)
    assert all(kayit["satirlar"][0]["oran"][s] is None for s in SEMBOLLER)

    # Okunabilen ama gecersiz deger SESSIZCE bosa cevrilmez.
    for bozuk in ("0.5", "1.0", "-2", "0", "inf", "abc"):
        g = _govde()
        g["satirlar"][3] = _satir(3, oran={"1": bozuk, "0": "3.2", "2": "3.8"})
        with pytest.raises(ka.ArsivHatasi, match="4. satir"):
            ka.kaydi_kur(g)


def test_satir_sayisi_TAM_15_olmali():
    for n in (0, 1, 14, 16):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(satirlar=[_satir(i) for i in range(n)]))


def test_ayar_SUNUCUNUN_listesinden_dogrulanir():
    """Arayüzün gönderdiği dize değil, motorun kendi listesi geçerlidir."""
    from spor_toto.benzer import CIZGILER
    from spor_toto.odds import ARINDIRMA_YONTEMLERI

    for cizgi in CIZGILER:
        assert ka.kaydi_kur(_govde(ayar={"cizgi": cizgi}))["ayar"]["cizgi"] == cizgi
    for y in ARINDIRMA_YONTEMLERI:
        assert ka.kaydi_kur(_govde(ayar={"arindirma": y}))["ayar"]["arindirma"] == y

    for bozuk in ({"cizgi": "AvgC"}, {"arindirma": "yok"},
                  {"en_az": 0}, {"en_az": 99999}, {"tarih": "2026-02-30"},
                  {"tarih": "01.09.2026"}):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(ayar={**_govde()["ayar"], **bozuk}))


def test_uzerine_yazma_GIRILDIYI_korur_guncellendiyi_tazeler():
    ilk = ka.yaz(_govde())
    ikinci = ka.yaz(_govde(**{"not": "duzeltildi"}))
    assert ikinci["girildi"] == ilk["girildi"], "ilk giris ani kaydin kunyesidir"
    assert ikinci["not"] == "duzeltildi"
    assert ikinci["guncellendi"] >= ilk["guncellendi"]


def test_yazma_ATOMIK_gecici_dosya_birakmaz():
    ka.yaz(_govde())
    dizin = ka.ARSIV / "2026_27"
    artik = [p.name for p in dizin.iterdir() if p.name.startswith(".tmp-")]
    assert not artik, f"gecici dosya kaldi: {artik}"
    assert [p.name for p in dizin.iterdir()] == ["hafta_05.json"]


def test_gidis_donus_ORANI_korur():
    ka.yaz(_govde(satirlar=[
        _satir(i, oran={"1": "1.26", "0": "6.48", "2": "13.54"})
        for i in range(ka.MAC_SAYISI)
    ]))
    geri = ka.oku("2026_27", 5)
    assert geri["satirlar"][0]["oran"] == {"1": 1.26, "0": 6.48, "2": 13.54}


def test_sonuclar_ya_null_ya_15_sembol():
    assert ka.kaydi_kur(_govde())["sonuclar"] is None
    tam = ka.kaydi_kur(_govde(sonuclar=["1"] * 15))["sonuclar"]
    assert tam == ["1"] * 15
    # Yarim sonuc girisi serbest: hafta oynanirken doldurulur.
    assert ka.kaydi_kur(_govde(sonuclar=["1", None] + [""] * 13))["sonuclar"][1] is None
    for bozuk in (["x"] * 15, ["1"] * 14, [1] * 15, "1"):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(sonuclar=bozuk))


def test_listele_OZET_doner_satirlari_tasimaz():
    ka.yaz(_govde(hafta=5))
    ka.yaz(_govde(hafta=3, satirlar=[
        _satir(i, oran={"1": "", "0": "", "2": ""}) for i in range(ka.MAC_SAYISI)
    ]))
    kayitlar = ka.listele("2026_27")
    assert [k["hafta"] for k in kayitlar] == [3, 5], "hafta sirasiyla"
    assert all("satirlar" not in k for k in kayitlar), "ozet 15 satiri tasimaz"
    assert kayitlar[0]["oranli_mac"] == 0 and kayitlar[1]["oranli_mac"] == 15
    assert ka.listele("2019_20") == [], "kayitsiz sezon bos liste, hata degil"


def test_bozuk_dosya_BUTUN_listeyi_dusurmez():
    ka.yaz(_govde(hafta=5))
    bozuk = ka.ARSIV / "2026_27" / "hafta_07.json"
    bozuk.write_text("{ yarim", encoding="utf-8")
    kayitlar = ka.listele("2026_27")
    assert [k["hafta"] for k in kayitlar] == [5]


def test_sil_yoksa_hata_DEGIL():
    assert ka.sil("2026_27", 5) is False
    ka.yaz(_govde())
    assert ka.sil("2026_27", 5) is True
    assert ka.sil("2026_27", 5) is False
    with pytest.raises(FileNotFoundError):
        ka.oku("2026_27", 5)


# ─── Uçlar ───────────────────────────────────────────────────────────────

@pytest.fixture()
def istemci():
    import web_app
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


def test_uc_yazar_okur_siler(istemci):
    r = istemci.post("/api/kupon/arsiv", json=_govde())
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["hafta"] == 5

    assert istemci.get("/api/kupon/arsiv/5").get_json()["not"] == "iddaa kapanis"
    assert len(istemci.get("/api/kupon/arsiv").get_json()["kayitlar"]) == 1
    assert istemci.delete("/api/kupon/arsiv/5").get_json()["silindi"] is True
    # Ikinci silme de BASARILI: istemci ayni istegi iki kez gonderebilir.
    assert istemci.delete("/api/kupon/arsiv/5").get_json()["silindi"] is False


def test_uc_olmayan_haftaya_404_bozuk_govdeye_400(istemci):
    assert istemci.get("/api/kupon/arsiv/9").status_code == 404
    for bozuk in ({}, _govde(hafta=0), _govde(sezon="../gizli"),
                  _govde(satirlar=[]), _govde(ayar={"cizgi": "AvgC"})):
        r = istemci.post("/api/kupon/arsiv", json=bozuk)
        assert r.status_code == 400, (bozuk, r.get_json())
        assert "error" in r.get_json()


def test_uc_govdeyi_ARAYUZE_birakmaz(istemci, tmp_path):
    """Doğrulama sunucuda. Arayüz bir istemcidir, kapı değil.

    Uç, arayüzün hiç göndermediği bir gövdeyi de reddetmeli: `curl` ile
    atılan bir istek arayüzün doğrulamasından geçmez.
    """
    r = istemci.post("/api/kupon/arsiv", json={"sezon": "2026_27", "hafta": 5,
                                               "satirlar": [{"oran": {"1": "yok"}}] * 15})
    assert r.status_code == 400
    assert not (ka.ARSIV / "2026_27").exists(), "reddedilen govde dosya YARATMAMALI"


def test_kayit_KARNE_tasimaz(istemci):
    """Türetilmiş veri arşive girmez — korpus büyüdükçe bayatlardı."""
    kayit = istemci.post("/api/kupon/arsiv", json=_govde()).get_json()
    assert set(kayit) == {"surum", "sezon", "hafta", "girildi", "guncellendi",
                          "not", "ayar", "satirlar", "sonuclar"}
    metin = json.dumps(kayit, ensure_ascii=False)
    for turetilmis in ("karne", "toplam", "tolerans", "piyasa"):
        assert turetilmis not in metin
