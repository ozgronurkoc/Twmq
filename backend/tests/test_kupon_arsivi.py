"""Kupon arşivinin bekçileri (`spor_toto/kupon_arsivi.py`).

**Neden ayrıca bekçili.** Bu modül, API'nin **diske yazan tek** üyesi. Geri
kalan her uç okuyucu: korpusu okur, türetir, döner — yanlış bir girdi en
fazla yanlış bir cevap verir. Burada yanlış bir girdi bir **dosyayı**
etkiler, ve o dosya elle kurulmuş, yeniden üretilemeyen bir kayıttır.

Tutulan şeyler:

1. **Yol kaçağı yok.** Sezon ve numara dosya yoluna giriyor.
2. **Kimlik kararlı.** Numara yeniden kullanılmaz; silinen bir numaranın
   yerine yenisi geçerse "2 numaralı kupon" iki farklı kayda işaret eder.
3. **Kayıp yok.** Yarım tablo kaydedilebilir, ama okunabilen ama geçersiz
   bir oran sessizce boşa çevrilmez.
4. **Zincir bütün.** Kayıt girdi · ayar · analizler · kupon taşır; analiz
   DAMGASIZ yazılamaz (ne zaman, hangi evrende ölçüldü), kuponun bir maçı
   işaretsiz kalamaz.
5. **İki çizgi ayrı.** Satır açılışın ve kapanışın oranını birlikte taşır,
   karne çizgi başına saklanır ve 2. sürümün DÜZ biçimi okunmaya devam
   eder — göç kodu olmadan eski bir kayıt sessizce boşalırdı.
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


#: Iki cizgi BILEREK farkli sayilar tasiyor: bloklar birbirine karisirsa
#: (ya da biri otekinin uzerine yazarsa) esit sayilarla bu gorunmezdi.
ACILIS_ORANI = {"1": "2.1", "0": "3.3", "2": "3.6"}
KAPANIS_ORANI = {"1": "2.0", "0": "3.2", "2": "3.8"}


def _satir(i: int = 0, **ek):
    return {"lig": "T1", "ev": f"ev{i}", "dep": f"dep{i}",
            "oran": {"acilis": dict(ACILIS_ORANI), "kapanis": dict(KAPANIS_ORANI)},
            **ek}


def _sembol(icinde=True):
    return {"adet": 80, "oran": 0.42, "ga_alt": 0.31, "ga_ust": 0.53,
            "piyasa": 0.44, "piyasa_ga_icinde": icinde}


def _analiz_satiri():
    return {"n": 225, "yeterli": True, "tolerans": 0.015,
            "tolerans_genisledi": False, "tolerans_tavana_dayandi": False,
            "semboller": {s: _sembol() for s in SEMBOLLER}}


def _analiz(**ek):
    return {"olculdu": "2026-09-14T15:00:00+00:00", "evren": 23083,
            "satirlar": [_analiz_satiri() for _ in range(ka.MAC_SAYISI)], **ek}


def _analizler(**ek):
    """İki çizginin karnesi. Kayıt artık ikisini birden taşıyor."""
    return {"acilis": _analiz(), "kapanis": _analiz(), **ek}


#: 6 banko + 9 uclu -> 3^9 = 19.683 kolon. Bu sayi UYDURULMADI: 5. haftada
#: OYNANAN tek sistemin kolon sayisi (`docs`/devam notu §3.82) tam buydu ve
#: sahibinin istedigi ilk sekil odur.
def _sekilli(**ek):
    return {"cizgi": "acilis", "sekil": "b6u9",
            "isaretler": [["1"]] * 6 + [["1", "0", "2"]] * 9, **ek}


def _kupon(**ek):
    # 8 banko + 5 cifte + 2 uclu -> 2^5 * 3^2 = 288 kolon.
    return {"isaretler": [["1"]] * 8 + [["1", "0"]] * 5 + [["1", "0", "2"]] * 2,
            "not": "deneme", **ek}


def _govde(**ek):
    return {"sezon": "2026_27", "ad": "1 numaralı kupon", "hafta": 5,
            "not": "iddaa açılış",
            "ayar": {"cizgi": "acilis", "arindirma": "shin", "en_az": 200,
                     "tarih": "", "kapsam": "tum"},
            "satirlar": [_satir(i) for i in range(ka.MAC_SAYISI)],
            "analizler": _analizler(), "kupon": _kupon(),
            "sekilli": [_sekilli()], **ek}


def test_mac_sayisi_meta_ile_AYNI():
    """15 iki yerde yazılı olamaz.

    `meta.MATCH_COUNT` motorun sayısı; bu modülünki arşivin. Ayrışırlarsa
    14 satırlık bir kayıt sessizce kabul edilir ve geri okunurken 15. maç
    boş gelir.
    """
    from spor_toto.meta import MATCH_COUNT
    assert ka.MAC_SAYISI == MATCH_COUNT


def test_yol_arsiv_kokunun_DISINA_cikamaz():
    for sezon in ("../../etc", "2026_27/../..", "..", "", "26_7", "2026-27", None):
        with pytest.raises(ka.ArsivHatasi):
            ka.yol(sezon, 1)
    for no in (0, -3, 10000, "bir", None):
        with pytest.raises(ka.ArsivHatasi):
            ka.yol("2026_27", no)
    p = ka.yol("2026_27", 7)
    assert str(p).startswith(str(ka.ARSIV.resolve()))
    assert p.name == "kupon_007.json"


def test_numara_YENIDEN_KULLANILMAZ():
    """Silinen bir numara boşalmaz.

    Yeniden kullanılsaydı "2 numaralı kupon" iki farklı kayda işaret
    ederdi ve arşiv bir kayıt olmaktan çıkardı.
    """
    assert ka.yaz(_govde())["no"] == 1
    assert ka.yaz(_govde(ad="ikinci"))["no"] == 2
    assert ka.yaz(_govde(ad="ucuncu"))["no"] == 3
    assert ka.sil("2026_27", 2) is True
    assert ka.sonraki_no("2026_27") == 4, "bosalan 2 DEGIL, 4 gelmeli"
    assert ka.yaz(_govde(ad="dorduncu"))["no"] == 4


def test_no_VERILIRSE_ustune_yazar_verilmezse_YENI_acar():
    ilk = ka.yaz(_govde())
    ayni = ka.yaz(_govde(no=1, ad="adı değişti"))
    assert ayni["no"] == 1
    assert ayni["ad"] == "adı değişti"
    assert ayni["girildi"] == ilk["girildi"], "ilk kurulus ani kaydin kunyesidir"
    assert ayni["guncellendi"] >= ilk["guncellendi"]
    assert len(ka.listele("2026_27")) == 1

    yeni = ka.yaz(_govde(ad="ayrı deneme"))
    assert yeni["no"] == 2
    assert len(ka.listele("2026_27")) == 2


def test_ad_SERBEST_ama_bos_kalmaz():
    """Ad kimlik değildir (kimlik `no`), ama liste okunabilir kalmalı."""
    assert ka.yaz(_govde(ad="açılışla kurulan, shin"))["ad"] == "açılışla kurulan, shin"
    # Ayni adi iki kupon tasiyabilir — cakisma DEGIL.
    a = ka.yaz(_govde(ad="deneme"))
    b = ka.yaz(_govde(ad="deneme"))
    assert a["no"] != b["no"] and a["ad"] == b["ad"]
    # Adsiz kayit numaradan turetilir.
    assert ka.yaz(_govde(ad=""))["ad"].endswith(". kupon")
    assert ka.yaz(_govde(ad=None))["ad"].endswith(". kupon")


def test_hafta_ETIKET_kimlik_degil():
    """Bir haftanın birden çok kuponu olur; hafta boş da bırakılabilir."""
    a = ka.yaz(_govde(hafta=5, ad="açılışla"))
    b = ka.yaz(_govde(hafta=5, ad="kapanışla"))
    assert a["no"] != b["no"] and a["hafta"] == b["hafta"] == 5
    assert ka.yaz(_govde(hafta=None))["hafta"] is None
    assert ka.yaz(_govde(hafta=""))["hafta"] is None
    # VERILDIYSE okunabilir olmali; sessizce None'a dusmemeli.
    for bozuk in ("besinci", 0, 61):
        with pytest.raises(ka.ArsivHatasi):
            ka.yaz(_govde(hafta=bozuk))


def test_yarim_tablo_kaydedilir_ama_BOZUK_oran_reddedilir():
    yarim = _govde(satirlar=[
        {"lig": "", "ev": "", "dep": "", "oran": {"kapanis": {"1": "", "0": None, "2": ""}}}
        for _ in range(ka.MAC_SAYISI)
    ], analizler=None, kupon=None, sekilli=None)
    kayit = ka.kaydi_kur(yarim, no=1)
    for cizgi in ("acilis", "kapanis"):
        assert all(kayit["satirlar"][0]["oran"][cizgi][s] is None for s in SEMBOLLER)

    # Bozuk hucre HANGI blokta olursa olsun satiri reddeder.
    for cizgi in ("acilis", "kapanis"):
        for bozuk in ("0.5", "1.0", "-2", "0", "inf", "abc"):
            g = _govde()
            g["satirlar"][3] = _satir(3, oran={cizgi: {"1": bozuk, "0": "3.2", "2": "3.8"}})
            with pytest.raises(ka.ArsivHatasi, match="4. satir"):
                ka.kaydi_kur(g, no=1)


def test_satir_sayisi_TAM_15_olmali():
    for n in (0, 1, 14, 16):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(satirlar=[_satir(i) for i in range(n)]), no=1)


def test_ayar_SUNUCUNUN_listesinden_dogrulanir():
    """Arayüzün gönderdiği dize değil, motorun kendi listesi geçerlidir."""
    from spor_toto.benzer import CIZGILER
    from spor_toto.odds import ARINDIRMA_YONTEMLERI

    for cizgi in CIZGILER:
        assert ka.kaydi_kur(_govde(ayar={"cizgi": cizgi}), no=1)["ayar"]["cizgi"] == cizgi
    for y in ARINDIRMA_YONTEMLERI:
        assert ka.kaydi_kur(_govde(ayar={"arindirma": y}), no=1)["ayar"]["arindirma"] == y

    for kapsam in ka.KAPSAMLAR:
        k = ka.kaydi_kur(_govde(ayar={**_govde()["ayar"], "kapsam": kapsam}), no=1)
        assert k["ayar"]["kapsam"] == kapsam
    # Kapsam verilmezse `tum`a duser — eski kayitlar da okunabilsin.
    assert ka.kaydi_kur(_govde(ayar={"cizgi": "acilis"}), no=1)["ayar"]["kapsam"] == "tum"

    for bozuk in ({"cizgi": "AvgC"}, {"arindirma": "yok"}, {"en_az": 0},
                  {"en_az": 99999}, {"tarih": "2026-02-30"}, {"tarih": "01.09.2026"},
                  {"kapsam": "lig"}, {"kapsam": "hepsi"}):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(ayar={**_govde()["ayar"], **bozuk}), no=1)


# ─── Zincirin analiz halkası ─────────────────────────────────────────────

def test_analiz_DAMGASIZ_yazilamaz():
    """`olculdu` ve `evren` alan değil zorunluluktur.

    Bu blok türetilmiş bir sayıdır ve korpus büyüdükçe bayatlar. Damgasız
    yazılırsa iki ay sonra açan kişi onu bugünün cevabı sanır — modül
    künyesindeki "kaydı atma, DAMGALA" kararının tamamı bu iki alana
    dayanıyor.
    """
    with pytest.raises(ka.ArsivHatasi, match="evren"):
        ka.kaydi_kur(_govde(analizler=_analizler(acilis=_analiz(evren=0))), no=1)
    with pytest.raises(ka.ArsivHatasi, match="evren"):
        ka.kaydi_kur(
            _govde(analizler={"kapanis": {"satirlar": [_analiz_satiri()] * 15}}), no=1)
    # `olculdu` verilmezse SESSIZCE bos kalmaz, su an damgalanir.
    k = ka.kaydi_kur(_govde(analizler=_analizler(acilis=_analiz(olculdu=""))), no=1)
    assert k["analizler"]["acilis"]["olculdu"], "damga uydurulmaz ama BOS da birakilmaz"


def test_analiz_kosulmamissa_null_satir_hatasi_KAYDIN_kendisi():
    bos = ka.kaydi_kur(_govde(analizler=None), no=1)["analizler"]
    assert bos == {"acilis": None, "kapanis": None}
    # Tek cizgi kosulmus olabilir: oteki `null` durur, alan yine de VARDIR.
    tek = ka.kaydi_kur(_govde(analizler={"kapanis": _analiz()}), no=1)["analizler"]
    assert tek["acilis"] is None and tek["kapanis"]["evren"] == 23083
    # Bir satirin sorgusu hata almis olabilir: o satir `null` durur.
    yarim = _analiz()
    yarim["satirlar"][6] = None
    k = ka.kaydi_kur(_govde(analizler=_analizler(acilis=yarim)), no=1)
    assert k["analizler"]["acilis"]["satirlar"][6] is None
    assert k["analizler"]["acilis"]["satirlar"][0]["n"] == 225


def test_analizler_BILINMEYEN_cizgiyi_sessizce_atmaz():
    """Yanlış anahtarla gelen bir karne kaybolmamalı, reddedilmeli."""
    with pytest.raises(ka.ArsivHatasi, match="AvgC"):
        ka.kaydi_kur(_govde(analizler={"AvgC": _analiz()}), no=1)


def test_analiz_sinir_disi_olasilik_REDDEDILIR():
    def _kur(a):
        return ka.kaydi_kur(_govde(analizler=_analizler(acilis=a)), no=1)

    for alan, deger in (("oran", 1.4), ("ga_alt", -0.1), ("piyasa", 2.0)):
        a = _analiz()
        a["satirlar"][0]["semboller"]["1"] = {**_sembol(), alan: deger}
        with pytest.raises(ka.ArsivHatasi):
            _kur(a)
    # Ornek yoksa ampirik oran YOKTUR; `null` gecerlidir, 0 DEGIL ayni sey.
    a = _analiz()
    a["satirlar"][0]["semboller"]["1"] = {**_sembol(), "oran": None, "adet": 0}
    assert _kur(a)["analizler"]["acilis"]["satirlar"][0]["semboller"]["1"]["oran"] is None
    # `piyasa_ga_icinde` uc durumlu: True / False / null (karar verilemez).
    for deger in (True, False, None):
        a = _analiz()
        a["satirlar"][0]["semboller"]["1"] = _sembol(icinde=deger)
        k = _kur(a)
        assert k["analizler"]["acilis"]["satirlar"][0]["semboller"]["1"]["piyasa_ga_icinde"] is deger
    a = _analiz()
    a["satirlar"][0]["semboller"]["1"] = _sembol(icinde="evet")
    with pytest.raises(ka.ArsivHatasi):
        _kur(a)


def test_analiz_LIG_kirilimi_ve_mac_listesi_TASIMAZ():
    """İkisi de `/oran-analizi`de açılır ve kaydı on katına çıkarırdı."""
    k = ka.kaydi_kur(_govde(), no=1)
    metin = json.dumps(k, ensure_ascii=False)
    for buyuk in ("dilimler", "maclar", "lig_etiket", "ev_gol"):
        assert buyuk not in metin
    satir = k["analizler"]["acilis"]["satirlar"][0]
    assert set(satir) == {"n", "yeterli", "tolerans", "tolerans_genisledi",
                          "tolerans_tavana_dayandi", "semboller"}


# ─── 2. sürümden göç ─────────────────────────────────────────────────────

def test_ESKI_duz_oran_kaydin_kendi_cizgisine_oturur():
    """2. sürümde satır TEK fiyat taşıyordu ve çizgiyi `ayar` söylüyordu.

    Göç o bilgiyi kullanır: düz `{1,0,2}` bloğu kaydın `ayar.cizgi`sine
    yerleşir, öteki çizgi BOŞ kalır. İki çizgiye birden kopyalasaydık
    girilmemiş bir fiyatı girilmiş gibi kaydederdik — ve o fiyattan kupon
    kurulurdu.
    """
    for cizgi in ("acilis", "kapanis"):
        g = _govde(ayar={**_govde()["ayar"], "cizgi": cizgi}, satirlar=[
            {"lig": "T1", "ev": "a", "dep": "b",
             "oran": {"1": "1.26", "0": "6.48", "2": "13.54"}}
            for _ in range(ka.MAC_SAYISI)
        ])
        oran = ka.kaydi_kur(g, no=1)["satirlar"][0]["oran"]
        assert oran[cizgi] == {"1": 1.26, "0": 6.48, "2": 13.54}
        oteki = "kapanis" if cizgi == "acilis" else "acilis"
        assert all(v is None for v in oran[oteki].values()), "uydurulmus fiyat YOK"


def test_ESKI_tek_analiz_kaydin_kendi_cizgisine_oturur():
    g = _govde(ayar={**_govde()["ayar"], "cizgi": "kapanis"}, analizler=None,
               analiz=_analiz())
    a = ka.kaydi_kur(g, no=1)["analizler"]
    assert a["kapanis"]["evren"] == 23083
    assert a["acilis"] is None
    # Yeni biçim geldiyse eski alan GÖRMEZDEN gelinir; iki kaynak
    # çakışmasın diye sıra bellidir: `analizler` kazanır.
    g2 = _govde(analizler={"acilis": _analiz(evren=999)}, analiz=_analiz())
    a2 = ka.kaydi_kur(g2, no=1)["analizler"]
    assert a2["acilis"]["evren"] == 999 and a2["kapanis"] is None


def test_ESKI_kayit_listede_okunur():
    """2. sürüm dosyası diskte duruyorsa liste onu `analiz_var` saymalı."""
    ka.yaz(_govde())
    yol = ka.yol("2026_27", 1)
    eski = json.loads(yol.read_text(encoding="utf-8"))
    eski["surum"] = 2
    eski["analiz"] = eski.pop("analizler")["acilis"]
    eski["satirlar"] = [{**s, "oran": {"1": 2.0, "0": 3.2, "2": 3.8}}
                        for s in eski["satirlar"]]
    yol.write_text(json.dumps(eski, ensure_ascii=False), encoding="utf-8")

    (k,) = ka.listele("2026_27")
    assert k["analiz_var"] and k["analiz_cizgileri"] == ["acilis"]
    # Düz oran, kaydın kendi çizgisinde sayılır; öteki boş görünür.
    assert k["oranli_mac"] == {"acilis": 15, "kapanis": 0}


# ─── Zincirin şekilli kupon halkası ──────────────────────────────────────

def test_sekilli_kolon_ve_dagilim_HESAPLANIR():
    """Sahibinin iki şekli; kolon sayıları ölçülmüş değil ARİTMETİK."""
    g = _govde(sekilli=[
        _sekilli(cizgi="acilis", sekil="b6u9"),
        _sekilli(cizgi="acilis", sekil="b5c5u5",
                 isaretler=[["1"]] * 5 + [["1", "0"]] * 5 + [["1", "0", "2"]] * 5),
        _sekilli(cizgi="kapanis", sekil="b6u9"),
    ])
    sekilli = ka.kaydi_kur(g, no=1)["sekilli"]
    assert [x["kolon"] for x in sekilli] == [3 ** 9, 2 ** 5 * 3 ** 5, 3 ** 9]
    assert [x["kolon"] for x in sekilli] == [19683, 7776, 19683]
    assert sekilli[1]["banko"] == 5 and sekilli[1]["cift"] == 5 and sekilli[1]["uclu"] == 5
    # Gonderilen sayilar YOK SAYILIR, hesap kazanir.
    yalanci = ka.kaydi_kur(_govde(sekilli=[_sekilli(kolon=7, banko=99)]), no=1)
    assert yalanci["sekilli"][0]["kolon"] == 19683
    assert yalanci["sekilli"][0]["banko"] == 6


def test_sekilli_AYNI_cizgi_sekil_iki_kez_gelemez():
    """"Açılışın 5/5/5'i" diyen iki satır, hangisinin oynandığını siler."""
    with pytest.raises(ka.ArsivHatasi, match="iki kez"):
        ka.kaydi_kur(_govde(sekilli=[_sekilli(), _sekilli()]), no=1)
    # Ayni sekil BASKA cizgide serbest — zaten istenen sey bu.
    k = ka.kaydi_kur(_govde(sekilli=[_sekilli(), _sekilli(cizgi="kapanis")]), no=1)
    assert len(k["sekilli"]) == 2


def test_sekilli_bozuk_govdeyi_REDDEDER():
    assert ka.kaydi_kur(_govde(sekilli=None), no=1)["sekilli"] == []
    assert ka.kaydi_kur(_govde(sekilli=[]), no=1)["sekilli"] == []
    for bozuk in ([_sekilli(cizgi="AvgC")], [_sekilli(sekil="")],
                  [_sekilli(sekil="../kotu")], [_sekilli(sekil="A" * 40)],
                  [_sekilli(isaretler=[[]] * 15)], [_sekilli(isaretler=[["1"]] * 14)],
                  [_sekilli()] * (ka.SEKIL_SINIRI + 1), "liste degil", [3]):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(sekilli=bozuk), no=1)


# ─── Zincirin kupon halkası ──────────────────────────────────────────────

def test_kupon_kolonu_HESAPLANIR_yazilmaz():
    """Kayıtta birbirini yalanlayabilecek iki sayı olmamalı."""
    k = ka.kaydi_kur(_govde(), no=1)
    assert k["kupon"]["kolon"] == 2 ** 5 * 3 ** 2 == 288
    # Gonderilen `kolon` YOK SAYILIR, hesap kazanir.
    yalanci = ka.kaydi_kur(_govde(kupon=_kupon(kolon=7)), no=1)
    assert yalanci["kupon"]["kolon"] == 288


def test_kupon_bos_isaret_kabul_ETMEZ():
    """Boş maç motorda `ValueError` üretir (`core.Encoder`)."""
    with pytest.raises(ka.ArsivHatasi, match="1. macin isareti"):
        ka.kaydi_kur(_govde(kupon={"isaretler": [[]] * 15}), no=1)
    for bozuk in ([["1"]] * 14, [["1"]] * 16, "111", [["x"]] * 15, [["1", "9"]] * 15):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(kupon={"isaretler": bozuk}), no=1)


def test_kupon_isaret_sirasi_KUPON_duzeni():
    """Sıra 1, 0, 2 — alfabetik değil. Yinelenen sembol tekilleşir."""
    k = ka.kaydi_kur(_govde(kupon={"isaretler": [["2", "0", "1"]] * 15}), no=1)
    assert k["kupon"]["isaretler"][0] == ["1", "0", "2"]
    t = ka.kaydi_kur(_govde(kupon={"isaretler": [["1", "1", "0"]] * 15}), no=1)
    assert t["kupon"]["isaretler"][0] == ["1", "0"]
    assert t["kupon"]["kolon"] == 2 ** 15


def test_kupon_kurulmamissa_null():
    assert ka.kaydi_kur(_govde(kupon=None), no=1)["kupon"] is None


# ─── Kayıt bütünlüğü ─────────────────────────────────────────────────────

def test_yazma_ATOMIK_gecici_dosya_birakmaz():
    ka.yaz(_govde())
    dizin = ka.ARSIV / "2026_27"
    artik = [p.name for p in dizin.iterdir() if p.name.startswith(".tmp-")]
    assert not artik, f"gecici dosya kaldi: {artik}"
    assert [p.name for p in dizin.iterdir()] == ["kupon_001.json"]


def test_gidis_donus_ZINCIRIN_TAMAMINI_korur():
    """Kaydı açan kişi dördünü de görmeli: girdi · ayar · analiz · kupon."""
    # 5. haftanin 1. maci, iki cizgi (`data/super_toto/2026_27/hafta_05.json`).
    ka.yaz(_govde(satirlar=[
        _satir(i, oran={"acilis": {"1": "1.28", "0": "5.53", "2": "10.16"},
                        "kapanis": {"1": "1.26", "0": "6.48", "2": "13.54"}})
        for i in range(ka.MAC_SAYISI)
    ]))
    geri = ka.oku("2026_27", 1)
    assert geri["surum"] == 3
    assert geri["satirlar"][0]["oran"]["acilis"] == {"1": 1.28, "0": 5.53, "2": 10.16}
    assert geri["satirlar"][0]["oran"]["kapanis"] == {"1": 1.26, "0": 6.48, "2": 13.54}
    assert geri["ayar"]["cizgi"] == "acilis"
    assert geri["analizler"]["acilis"]["evren"] == 23083
    assert geri["analizler"]["kapanis"]["evren"] == 23083
    assert geri["analizler"]["acilis"]["satirlar"][0]["semboller"]["1"]["adet"] == 80
    assert geri["kupon"]["kolon"] == 288
    assert geri["sekilli"][0]["kolon"] == 3 ** 9 == 19683
    assert geri["ad"] == "1 numaralı kupon"


def test_sonuclar_ya_null_ya_15_sembol():
    assert ka.kaydi_kur(_govde(), no=1)["sonuclar"] is None
    assert ka.kaydi_kur(_govde(sonuclar=["1"] * 15), no=1)["sonuclar"] == ["1"] * 15
    assert ka.kaydi_kur(_govde(sonuclar=["1", None] + [""] * 13), no=1)["sonuclar"][1] is None
    for bozuk in (["x"] * 15, ["1"] * 14, [1] * 15, "1"):
        with pytest.raises(ka.ArsivHatasi):
            ka.kaydi_kur(_govde(sonuclar=bozuk), no=1)


def test_listele_OZET_doner_govdeyi_tasimaz():
    ka.yaz(_govde(ad="birinci"))
    ka.yaz(_govde(ad="ikinci", analizler=None, kupon=None, sekilli=None, satirlar=[
        _satir(i, oran={"acilis": {"1": "", "0": "", "2": ""}})
        for i in range(ka.MAC_SAYISI)
    ]))
    kayitlar = ka.listele("2026_27")
    assert [k["no"] for k in kayitlar] == [1, 2], "numara sirasiyla"
    for k in kayitlar:
        assert "satirlar" not in k and "analizler" not in k, "ozet govdeyi tasimaz"
    assert kayitlar[0]["analiz_var"] and kayitlar[0]["kupon_var"]
    assert kayitlar[0]["kolon"] == 288
    assert kayitlar[0]["sekilli_sayisi"] == 1
    assert kayitlar[0]["analiz_cizgileri"] == ["acilis", "kapanis"]
    # Oran sayimi CIZGI BASINA: tek tarafi dolu bir tablo "15/15" demez.
    assert kayitlar[0]["oranli_mac"] == {"acilis": 15, "kapanis": 15}
    assert not kayitlar[1]["analiz_var"] and not kayitlar[1]["kupon_var"]
    assert kayitlar[1]["oranli_mac"] == {"acilis": 0, "kapanis": 0}
    assert ka.listele("2019_20") == [], "kayitsiz sezon bos liste, hata degil"


def test_bozuk_dosya_BUTUN_listeyi_dusurmez():
    ka.yaz(_govde())
    (ka.ARSIV / "2026_27" / "kupon_007.json").write_text("{ yarim", encoding="utf-8")
    assert [k["no"] for k in ka.listele("2026_27")] == [1]
    # Bozuk dosya numarayi yine de TUTAR: adindan okunuyor.
    assert ka.sonraki_no("2026_27") == 8


def test_sil_yoksa_hata_DEGIL():
    assert ka.sil("2026_27", 1) is False
    ka.yaz(_govde())
    assert ka.sil("2026_27", 1) is True
    assert ka.sil("2026_27", 1) is False
    with pytest.raises(FileNotFoundError):
        ka.oku("2026_27", 1)


# ─── Uçlar ───────────────────────────────────────────────────────────────

@pytest.fixture()
def istemci():
    import web_app
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


def test_uc_yazar_okur_siler(istemci):
    r = istemci.post("/api/kupon/arsiv", json=_govde())
    assert r.status_code == 200, r.get_json()
    no = r.get_json()["no"]

    kayit = istemci.get(f"/api/kupon/arsiv/{no}").get_json()
    assert kayit["ad"] == "1 numaralı kupon"
    assert kayit["kupon"]["kolon"] == 288
    assert len(istemci.get("/api/kupon/arsiv").get_json()["kayitlar"]) == 1
    assert istemci.delete(f"/api/kupon/arsiv/{no}").get_json()["silindi"] is True
    assert istemci.delete(f"/api/kupon/arsiv/{no}").get_json()["silindi"] is False


def test_uc_olmayan_kayda_404_bozuk_govdeye_400(istemci):
    assert istemci.get("/api/kupon/arsiv/9").status_code == 404
    for bozuk in ({}, _govde(sezon="../gizli"), _govde(satirlar=[]),
                  _govde(ayar={"cizgi": "AvgC"}), _govde(kupon={"isaretler": [[]] * 15}),
                  _govde(analizler={"acilis": _analiz(evren=0)}),
                  _govde(sekilli=[_sekilli(sekil="../kotu")]),
                  _govde(sekilli=[_sekilli(), _sekilli()])):
        r = istemci.post("/api/kupon/arsiv", json=bozuk)
        assert r.status_code == 400, (bozuk.get("ad"), r.get_json())
        assert "error" in r.get_json()


def test_uc_govdeyi_ARAYUZE_birakmaz(istemci):
    """Doğrulama sunucuda. Arayüz bir istemcidir, kapı değil.

    `curl` ile atılan bir istek arayüzün doğrulamasından geçmez.
    """
    r = istemci.post("/api/kupon/arsiv", json={"satirlar": [{"oran": {"1": "yok"}}] * 15})
    assert r.status_code == 400
    assert not (ka.ARSIV / "2026_27").exists(), "reddedilen govde dosya YARATMAMALI"


def test_kayit_alanlari_SABIT():
    """Kaydın şekli sözleşmedir; sessizce alan eklenip çıkmaz."""
    assert set(ka.kaydi_kur(_govde(), no=1)) == {
        "surum", "sezon", "no", "ad", "hafta", "girildi", "guncellendi",
        "not", "ayar", "satirlar", "analizler", "kupon", "sekilli", "sonuclar",
    }
