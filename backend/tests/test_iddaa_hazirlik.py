"""Ö4 hazırlık betiği (`scripts/iddaa_hazirlik.py`).

Bu betik bir **durma kuralı** taşıyor ve durma kuralının değeri, kimse
bakmıyorken bile doğru kalmasındadır. Korunan iki şey:

1. **Güç hesabı doğru yönde.** Aranan etki küçüldükçe gerekli hafta
   büyümeli; sd ölçülebiliyorsa uydurulmuş sabit KULLANILMAMALI.
2. **"Yeterli" bayrağı erken yeşile dönmemeli.** Ö4'ün bütün amacı,
   5–10 hafta sonra "bu kadar veri yeter herhalde" denmesini engellemek.
   O bayrak yanlışlıkla açılırsa kural sessizce kaybolur.
"""

import json

import pytest

from scripts.iddaa_hazirlik import (
    ARANAN_ETKI,
    AYRISMA_ESIGI,
    SEZON_HAFTA,
    VARSAYILAN_SD,
    _oranli_mi,
    bayi_web,
    elde_ne_var,
    guc_analizi,
    hafta_sd,
    rapor,
)

# ─── oran denetimi ────────────────────────────────────────────────────────

def test_gecerli_oran_kabul_edilir():
    assert _oranli_mi({"1": 1.82, "0": 3.04, "2": 2.44})


@pytest.mark.parametrize("bozuk", [
    {"1": 1.82, "0": 3.04},              # eksik sembol
    {"1": 1.0, "0": 3.04, "2": 2.44},    # 1,00 gerçek oran değil
    {"1": "x", "0": 3.04, "2": 2.44},    # sayıya dönmüyor
    {},
])
def test_bozuk_oran_reddedilir(bozuk):
    assert not _oranli_mi(bozuk)


# ─── güç analizi ──────────────────────────────────────────────────────────

def test_sd_uydurulmadi_olculdu():
    """Elde ölçecek veri varken varsayılan sabite düşmek gizli bir gerileme."""
    sd, n = hafta_sd()
    assert n >= 20, "hafta başına Brier farkı ölçülemedi"
    assert 0.0 < sd < 0.05


def test_kucuk_etki_daha_cok_hafta_ister():
    buyuk = guc_analizi(0, etki=0.005)["gerekli_hafta"]
    kucuk = guc_analizi(0, etki=0.0005)["gerekli_hafta"]
    assert kucuk > buyuk


def test_gerekli_hafta_etkinin_karesiyle_olcekler():
    """`n ∝ 1/etki²` — etki yarıya inince gerekli hafta dörde katlanmalı."""
    a = guc_analizi(0, etki=0.002, sd=0.004)["gerekli_hafta"]
    b = guc_analizi(0, etki=0.001, sd=0.004)["gerekli_hafta"]
    assert b == pytest.approx(4 * a, rel=0.02)


def test_buyuk_sd_daha_cok_hafta_ister():
    az = guc_analizi(0, etki=ARANAN_ETKI, sd=0.002)["gerekli_hafta"]
    cok = guc_analizi(0, etki=ARANAN_ETKI, sd=0.008)["gerekli_hafta"]
    assert cok > az


def test_verilen_sd_olculeni_ezer():
    g = guc_analizi(0, sd=0.01)
    assert g["sd"] == 0.01
    assert not g["sd_olculdu_mu"]


def test_gerekli_sezon_haftayla_tutarli():
    g = guc_analizi(0)
    assert g["gerekli_sezon"] == pytest.approx(g["gerekli_hafta"] / SEZON_HAFTA)


def test_aranan_etki_bir_sezonluk_mertebede():
    """Aranan etki ölçüme bakılmadan seçildi; mertebesi denetlenebilir.

    Çok büyük seçilirse kural anlamsızca erken yeşile döner, çok küçük
    seçilirse hiç ölçülemez. Bir–iki sezon arası, projenin gerçekten
    bekleyebileceği tek aralık.
    """
    g = guc_analizi(0)
    assert 0.5 <= g["gerekli_sezon"] <= 3.0


# ─── durma kuralı ─────────────────────────────────────────────────────────

def test_elde_olan_veri_yetmiyor():
    """Bilerek konmuş **tetik**: bu test kırıldığı gün veri gelmiş demektir.

    `test_super_toto.test_fazb_bugun_olculemez_der` ile aynı desen. Kırmızı
    olması bir gerileme DEĞİL, "artık ölçebilirsin" sinyalidir — o gün
    yapılacak şey testi silmek değil, `docs/ISTATISTIK_YOL_HARITASI.md`
    §3.22'deki ölçümü koşup testi ölçülen sonuca göre yeniden yazmaktır.
    """
    g = guc_analizi(elde_ne_var()["kullanilabilir_hafta"])
    assert not g["yeterli"]


def test_yeterli_bayragi_esikte_doner():
    n = guc_analizi(0)["gerekli_hafta"]
    assert not guc_analizi(n - 1)["yeterli"]
    assert guc_analizi(n)["yeterli"]


def test_rapor_durumu_ve_kurali_tasir():
    o = rapor()
    assert o["durum"] in ("olculemez", "birikiyor", "olculebilir")
    assert str(o["guc"]["gerekli_hafta"]) in o["durma_kurali"]
    assert o["sinir"]


def test_rapor_json_serilesebilir():
    json.dumps(rapor(), ensure_ascii=False, default=str)


# ─── elde ne var ──────────────────────────────────────────────────────────

def test_yalnizca_cozulmus_iddaa_haftalari_sayilir():
    """Sonucu bilinmeyen hafta oranı taşısa bile ölçüme giremez."""
    d = elde_ne_var()
    assert d["haftalar"], "kupon haftasi bulunamadi"
    sayilan = sum(1 for h in d["haftalar"] if h["iddaa_mi"] and h["cozulmus"])
    assert d["kullanilabilir_hafta"] == sayilan
    for h in d["haftalar"]:
        assert h["cozulmus"] <= h["oranli"] <= h["mac"]


def test_bilinmeyen_sezon_bos_doner():
    d = elde_ne_var("1900_01")
    assert d["haftalar"] == []
    assert d["kullanilabilir_hafta"] == 0


def test_iddaa_marji_football_datadan_buyuk():
    """Ö4'ün varlık sebebinin sayısı: ölçtüğümüz piyasa oynadığımız değil."""
    d = elde_ne_var()
    marjlar = [h["marj"] for h in d["haftalar"]
               if h["iddaa_mi"] and h["marj"] is not None]
    assert marjlar
    assert min(marjlar) > 0.12, "iddaa marji beklenenden kucuk"


# ─── bayi ↔ web ───────────────────────────────────────────────────────────

def test_bayi_web_arsivden_okunur():
    b = bayi_web()
    assert b["n"] > 0, "bulten arsivi bos"
    assert 0.0 < b["marj_bayi"] < 0.5
    assert 0.0 < b["marj_web"] < 0.5


def test_web_marji_bayiden_buyuk():
    """Ölçülmüş olgu: web platformu daha büyük pay alıyor."""
    b = bayi_web()
    assert b["marj_web"] > b["marj_bayi"]


def test_ayrisma_orani_paydayla_tutarli():
    b = bayi_web()
    assert 0.0 <= b["ayrisan_oran"] <= 1.0
    assert b["ayrisan_oran"] == pytest.approx(b["ayrisan"] / b["n"])
    assert b["fark_ort"] >= 0.0


def test_ayrisma_esigi_makul():
    assert 0.0 < AYRISMA_ESIGI < 0.05


def test_varsayilan_sd_olculenle_ayni_mertebede():
    """Sabit bir gün gerçekten kullanılırsa saçma bir sayı olmamalı."""
    olculen, _ = hafta_sd()
    assert 0.2 * olculen < VARSAYILAN_SD < 5 * olculen
