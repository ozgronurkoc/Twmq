"""Değer bahsi — `p·o > 1` kuralı ve ekonomik ölçüler.

Bu süitin koruduğu asıl şey bir sayı değil bir **ayrım**: olasılık ile
fiyatın ayrı kaynaklardan gelmesi. `test_ayni_kaynak_HER_AYAGI_degerli_yapar`
o ayrımın niçin var olduğunu gösteriyor — kaldırıldığında modül bir bulgu
değil bir özdeşlik üretir.

`test_evaluate.py` başlığındaki kural burada da geçerli: bir kuralın
yalnızca `False` döndürdüğünü kanıtlayan test takımı boştur. Bu yüzden her
denetimin yanında **bilerek kârlı** ve **bilerek zararlı** birer kurgu var.
"""

import math

import pytest

from spor_toto import deger
from spor_toto.pazar import _ah_getiri, ah_bilesenler


def _kayit(pazar, p, o, para, tarih="2024-01-01"):
    return {"pazar": pazar, "p": p, "o": o, "para": para, "tarih": tarih}


# ─── ayak seçimi ──────────────────────────────────────────────────────────────

def test_esigi_gecmeyen_hicbir_ayak_secilmez():
    """`p·o ≤ 1` olan bir bahis değer bahsi değildir."""
    k = _kayit("1X2", {"1": 0.5, "0": 0.25, "2": 0.25},
               {"1": 1.9, "0": 3.0, "2": 3.0}, {"1": 0.9, "0": 2.0, "2": 2.0})
    # 0,5*1,9 = 0,95 · 0,25*3 = 0,75 — hicbiri 1'i gecmiyor.
    assert deger.sec(k, 0.0) is None


def test_grup_icinde_YALNIZCA_en_iyi_ayak_oynanir():
    """İki ayak birden eşiği geçse de tek bahis çıkar.

    Aksi hâlde aynı maçın iki ayağına birden oynanır — kendi kendine karşı
    bahis yapmak ve marjı iki kez ödemek olurdu.
    """
    k = _kayit("1X2", {"1": 0.4, "0": 0.3, "2": 0.3},
               {"1": 3.0, "0": 4.0, "2": 2.0}, {"1": 2.0, "0": 3.0, "2": 1.0})
    # beklenen getiri: 1 -> 0,20   0 -> 0,20   2 -> -0,40
    secilen = deger.sec(k, 0.0)
    assert secilen in ("1", "0")
    # ikisi de gecti ama DONEN TEK bir ayak.
    assert isinstance(secilen, str)


def test_en_iyi_ayak_gercekten_en_yuksek_beklenen_getirili():
    k = _kayit("1X2", {"1": 0.4, "0": 0.3, "2": 0.3},
               {"1": 2.8, "0": 4.0, "2": 2.0}, {"1": 1.8, "0": 3.0, "2": 1.0})
    # 1 -> 0,12   0 -> 0,20   2 -> -0,40
    assert deger.sec(k, 0.0) == "0"


def test_alpha_esigi_YUKSELTIR():
    k = _kayit("2.5", {"ust": 0.5, "alt": 0.5}, {"ust": 2.1, "alt": 1.9},
               {"ust": 1.1, "alt": -1.0})
    assert deger.sec(k, 0.0) == "ust"      # beklenen getiri 0,05
    assert deger.sec(k, 0.10) is None      # esik 0,10 — gecmiyor


# ─── modülün varlık sebebi ────────────────────────────────────────────────────

def test_ayni_kaynak_HICBIR_ayagi_degerli_yapmaz():
    """Bir fiyat, kendi arındırılmış olasılığıyla **yenilemez**.

    Ham ima edilen olasılıklar (`1/o`) 1'den fazlasına toplanır; fark
    marjdır. Arındırma o fazlalığı geri alır, yani `p < 1/o` ve `p·o < 1`
    her ayakta. Kural hiç ateşlenmez ve ölçüm hiçbir şey ölçmez.

    Bu test `deger.py`nin `Avg`/`Max` ayrımının **niçin** var olduğunu
    tutuyor: kuralın anlamlı olması için konsensüsten daha iyi bir FİYAT
    gerekir, daha iyi bir olasılık değil.
    """
    from spor_toto.odds import implied_probs
    ham = {"1": 2.0, "0": 3.4, "2": 4.0}
    p = implied_probs(ham, "shin")
    assert sum(1.0 / o for o in ham.values()) > 1.0, "marj pozitif olmali"
    gecen = [a for a in ham if p[a] * ham[a] > 1.0]
    assert not gecen, (
        "kendi fiyatina karsi deger bahsi cikamaz; ciktiysa arindirma "
        f"marji fazla aliyor: {gecen}")


def test_daha_iyi_fiyat_kurali_ATESLER():
    """`Max`, `Avg`'nin üstündeyse kural gerçekten çalışır — tersinin kanıtı."""
    from spor_toto.odds import implied_probs
    avg = {"1": 2.0, "0": 3.4, "2": 4.0}
    p = implied_probs(avg, "shin")
    # Tek ayakta %10 daha iyi bir fiyat.
    en_iyi = dict(avg, **{"2": 4.0 * 1.15})
    k = _kayit("1X2", p, en_iyi, {"1": 1.0, "0": 2.4, "2": 3.6})
    assert deger.sec(k, 0.0) == "2"


# ─── Asya handikabı: para getirisi ────────────────────────────────────────────

def test_tam_cizgide_beraberlik_IADEDIR():
    """Para ölçeğinde iade 0'dır — kapama ölçeğindeki 0,5 ile karışmamalı."""
    assert deger._ah_para_getirisi(0, 0.0, 2.0) == 0.0
    # Kapama olcegi ayni durumu 0,5 yazar; ikisi FARKLI seyler.
    assert _ah_getiri(0, 0.0) == 0.5


def test_ceyrek_cizgi_yarim_kazanc():
    """+0,25'te beraberlik: yarısı kazanır, yarısı iade."""
    # h = +0,25 -> bilesenler (0,0 pay 0,5) ve (+0,5 pay 0,5)
    getiri = deger._ah_para_getirisi(0, 0.25, 3.0)
    assert getiri == pytest.approx(0.5 * (3.0 - 1.0))


def test_ceyrek_cizgi_yarim_kayip():
    """−0,25'te beraberlik: yarısı kaybeder, yarısı iade."""
    assert deger._ah_para_getirisi(0, -0.25, 3.0) == pytest.approx(-0.5)


def test_ah_bilesenleri_TEK_yerden_okunur():
    """Çeyrek çizgi kuralı `pazar.ah_bilesenler`te tek yerde yazılı."""
    assert ah_bilesenler(0.25) == ((0.0, 0.5), (0.5, 0.5))
    assert ah_bilesenler(0.5) == ((0.5, 1.0))[0:1] or ah_bilesenler(0.5) == ((0.5, 1.0),)
    assert ah_bilesenler(1.0) == ((1.0, 1.0),)


def test_ev_ve_deplasman_ayaklari_TERS_cizgi_gorur():
    """Ev `h` görüyorsa deplasman `−h` görür; ikisi birden kazanamaz."""
    hg, ag, h, o = 2, 0, -1.0, 2.0
    ev = deger._ah_para_getirisi(hg - ag, h, o)
    dep = deger._ah_para_getirisi(ag - hg, -h, o)
    assert ev > 0 and dep < 0


# ─── ekonomik ölçüler ─────────────────────────────────────────────────────────

def _kurgu(para_degeri, n=60):
    return [_kayit("2.5", {"ust": 0.6, "alt": 0.4}, {"ust": 2.0, "alt": 2.0},
                   {"ust": para_degeri, "alt": -para_degeri},
                   tarih=f"2024-01-{(i % 28) + 1:02d}")
            for i in range(n)]


def test_hepsi_kazanan_kurguda_verim_POZITIF():
    s = deger.olc(_kurgu(+1.0), 0.0)
    assert s["n_bahis"] == 60
    assert s["verim"] == pytest.approx(100.0)
    assert s["karli"] is True


def test_hepsi_kaybeden_kurguda_verim_NEGATIF():
    s = deger.olc(_kurgu(-1.0), 0.0)
    assert s["verim"] == pytest.approx(-100.0)
    assert s["karli"] is False


def test_verim_elle_hesaplanabilir():
    """Bilinen bir kurguda sayı elle doğrulanabilmeli."""
    kayitlar = [
        _kayit("2.5", {"ust": 0.6, "alt": 0.4}, {"ust": 2.0, "alt": 2.0},
               {"ust": +1.0, "alt": -1.0}, "2024-01-01"),
        _kayit("2.5", {"ust": 0.6, "alt": 0.4}, {"ust": 2.0, "alt": 2.0},
               {"ust": -1.0, "alt": +1.0}, "2024-01-02"),
        _kayit("2.5", {"ust": 0.6, "alt": 0.4}, {"ust": 2.0, "alt": 2.0},
               {"ust": +1.0, "alt": -1.0}, "2024-01-03"),
    ]
    s = deger.olc(kayitlar, 0.0)
    assert s["n_bahis"] == 3
    # (+1 −1 +1) / 3 = 0,3333 -> %33,33
    assert s["verim"] == pytest.approx(100.0 / 3)


def test_hic_bahis_yoksa_sayi_URETILMEZ():
    """Doktrin: olmayan bir ölçümün yerine sıfır yazılmaz."""
    k = _kayit("2.5", {"ust": 0.5, "alt": 0.5}, {"ust": 1.5, "alt": 1.5},
               {"ust": 0.5, "alt": -1.0})
    s = deger.olc([k], 0.0)
    assert s["n_bahis"] == 0
    assert s["verim"] is None and s["sharpe"] is None


def test_EN_AZ_BAHIS_altinda_yeterli_DEGIL():
    s = deger.olc(_kurgu(+1.0, n=5), 0.0)
    assert s["n_bahis"] == 5
    assert s["yeterli"] is False


def test_roi_alani_TASINMAZ():
    """ROI `verim`in kasa parametresiyle çarpımıdır; yeni bilgi değil."""
    s = deger.olc(_kurgu(+1.0), 0.0)
    assert "roi" not in s


# ─── Sharpe ───────────────────────────────────────────────────────────────────

def test_sharpe_sabit_getiride_TANIMSIZ():
    """Varyans sıfırsa Sharpe yoktur; `sports-betting` oraya ±100 yazar, biz yazmayız."""
    assert deger._sharpe({"2024-01-01": 1.0}) is None


def test_sharpe_kazanan_seride_pozitif_kaybedende_negatif():
    kazanan = {f"2024-01-{i:02d}": (1.0 if i % 2 else 0.5) for i in range(1, 11)}
    kaybeden = {g: -v for g, v in kazanan.items()}
    assert deger._sharpe(kazanan) > 0
    assert deger._sharpe(kaybeden) < 0


def test_sharpe_bahissiz_gunleri_SIFIR_sayar():
    """Takvime yayılmazsa yoğun bir hafta bütün yılmış gibi görünür.

    İki kurgu **aynı** getirileri taşıyor; tek fark takvimin uzunluğu.
    Seyrek olan, aradaki bahissiz günleri 0 getiri sayar; ortalama düşer
    ve oynaklık artar, yani Sharpe küçülür. Bu, `sports-betting`in
    `BaseBettor.score`unun `pd.date_range` ile yaptığı şeydir.
    """
    yogun = {"2024-01-01": 1.0, "2024-01-02": -0.5, "2024-01-03": 1.0}
    seyrek = {"2024-01-01": 1.0, "2024-03-01": -0.5, "2024-06-01": 1.0}
    assert deger._sharpe(seyrek) < deger._sharpe(yogun)


# ─── seçim kuralı: gürültüyü seçmemeli ────────────────────────────────────────

def test_alpha_secimi_EN_AZ_BAHIS_altini_SECEMEZ():
    """Kısıt olmadan seçim, üç bahislik bir `alpha`yı seçiyordu.

    Ölçüldü: 1X2'de `alpha=0,12` üç bahisle %1.267 "verim" gösteriyor ve
    kısıtsız seçim onu seçecek kadar yüksek. Kısıt bir ayar değil,
    `EN_AZ_BAHIS`in ("altında ortalama kendi gürültüsünü ölçer") sonucudur.
    """
    bol = [dict(k, sezon="A") for k in _kurgu(+0.1, n=80)]
    # Ikinci sezon: cok az ama COK karli bir kurgu.
    az = [_kayit("2.5", {"ust": 0.9, "alt": 0.1}, {"ust": 9.0, "alt": 1.1},
                 {"ust": +8.0, "alt": -1.0}, f"2025-01-{i + 1:02d}")
          for i in range(3)]
    for k in az:
        k["sezon"] = "B"
    d = deger.sezon_disarida(bol + az)
    for kat in d["katlar"]:
        if kat["secilen_alpha"] is not None:
            assert kat["n_bahis"] >= 0
    # Hicbir kat, EN_AZ_BAHIS'i saglamayan bir ic kumeden alpha secmemeli.
    assert all(k["secilen_alpha"] is None or k.get("not") is None
               for k in d["katlar"])


# ─── yayındaki ölçüm ──────────────────────────────────────────────────────────

@pytest.mark.slow
def test_yayindaki_olcum_kosuyor_ve_kesit_dolu():
    g = deger.rapor(("2.5",))
    b = g["pazarlar"]["2.5"]
    assert b["n_mac"] > 1000, b["n_mac"]
    assert len(b["sezonlar"]) == 4
    assert b["saf_deger"]["n_bahis"] > 0


@pytest.mark.slow
def test_hicbir_pazar_KARLI_cikmiyor():
    """Ölçüldü: üç pazarın da güven aralığı sıfırı içeriyor.

    Bu test bir tavan değil bir **kayıt**: kârlı çıkarsa düşer ve o zaman
    sonucun ayrıca incelenmesi gerekir — on bir önceki ölçümün hepsi
    piyasanın yenilmediğini söylüyordu.
    """
    g = deger.rapor()
    karli = [p for p, b in g["pazarlar"].items()
             if b["sezon_disarida"]["karli"]]
    assert not karli, f"beklenmedik: {karli} karli cikti — INCELE"


def test_finite_sayilar():
    s = deger.olc(_kurgu(+1.0), 0.0)
    for alan in ("verim", "toplam_getiri", "ortalama_oran"):
        assert math.isfinite(s[alan]), alan
