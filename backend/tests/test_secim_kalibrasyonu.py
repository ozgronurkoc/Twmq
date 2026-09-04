"""Seçim koşullu kalibrasyon — **mekanizma** bekçileri.

`test_kalibrasyon.py` ile aynı ilke: buradaki testler *bulguyu* değil
mekanizmayı korur. Ölçümün cevabı (ters seçim var mı, ne kadar) koşumun
işidir ve buraya sabitlenmez — sabitlenirse test, ölçümün sonucunu önceden
bilmiş olurdu ve ölçüm anlamını yitirirdi.

Korunan şeyler: seçilen küme her zaman alt kümedir · eşik yükseldikçe daralır ·
seyrek bant yazılmaz ve sayılır · işaretler tek yöne bakar · **koşullama
sonucu görmez**.
"""

import random

import pytest

from spor_toto.secim_kalibrasyonu import (
    BANTLAR,
    DEGER_PAZARLARI,
    EN_AZ_BANT,
    ESIK_IZGARASI,
    Nokta,
    bonferroni,
    egri,
    eslestir,
    noktalar_deger,
    noktalar_model,
    sezon_kirilimi,
    wilson_z,
)


def _sentetik(n: int, p: float, isabet_orani: float, tohum: int = 7,
              sezon: str = "2023/2024") -> list[Nokta]:
    """Verilen olasılıkta `n` nokta; isabet oranı bilerek `p`'den ayrı tutulabilir."""
    rng = random.Random(tohum)
    return [(p, rng.random() < isabet_orani, sezon) for _ in range(n)]


# ─── egri / eslestir mekanigi ────────────────────────────────────────────────

def test_az_noktali_bant_yazilmaz_ve_sayilir() -> None:
    """`EN_AZ_BANT` altındaki bant tabloya girmez ama sessizce kaybolmaz."""
    az = _sentetik(EN_AZ_BANT - 1, 0.52, 0.5)
    sonuc = egri(az)
    assert sonuc["bantlar"] == []
    assert sonuc["dusen_bant"] == 1, "düşen bant sayılmalı"

    yeter = _sentetik(EN_AZ_BANT, 0.52, 0.5)
    assert len(egri(yeter)["bantlar"]) == 1
    assert egri(yeter)["dusen_bant"] == 0


def test_bos_kume_cokmez() -> None:
    """Hiç nokta yoksa tablo boş döner; sıfır bir aralık değil, ölçülmemişliktir."""
    sonuc = egri([])
    assert sonuc["n"] == 0 and sonuc["bantlar"] == []
    ozet = eslestir([], [])["ozet_secilen"]
    assert ozet["n"] == 0 and ozet["asiri_guven"] is None


def test_asiri_guven_ile_fark_ters_isaretli_ve_tutarli() -> None:
    """Bant satırı iki büyüklüğü de taşır ve biri ötekinin tam tersidir.

    İkisi de taşınıyor çünkü `fark` `kalibrasyon.py` ile aynı işarette
    (gerçek − söylenen), `asiri_guven` ise özetle aynı yöne bakıyor.
    """
    # söylenen 0,80 · gerçekleşen ~0,50 → model aşırı güvenli
    satir = egri(_sentetik(400, 0.80, 0.50))["bantlar"][0]
    assert satir["asiri_guven"] == pytest.approx(-satir["fark"])
    assert satir["asiri_guven"] > 0, "söylenen gerçekten büyükse aşırı güven pozitif"


def test_eslestirme_yarim_bandi_tabloya_koymaz() -> None:
    """Yalnız bir tarafta yazılabilen bant karşılaştırmaya girmez, sayılır."""
    hepsi = _sentetik(400, 0.52, 0.5) + _sentetik(400, 0.72, 0.7, tohum=9)
    secilen = _sentetik(400, 0.52, 0.5)          # ikinci bant seçilen tarafta yok
    sonuc = eslestir(hepsi, secilen)
    assert len(sonuc["bantlar"]) == 1
    assert sonuc["eslesmeyen_bant"] == 1


def test_secim_orani_paydayi_hepsiden_alir() -> None:
    """`secim_orani` seçilen/hepsi; payda daralan taraf değil."""
    hepsi = _sentetik(400, 0.52, 0.5)
    sonuc = eslestir(hepsi, hepsi[:100])
    assert sonuc["secim_orani"] == pytest.approx(0.25)


# ─── kural sozlesmesi ────────────────────────────────────────────────────────

def test_iade_li_pazar_reddedilir() -> None:
    """`AH` ölçüme giremez: iade, "bu ayak tuttu mu" sorusunu ikili olmaktan çıkarır."""
    assert "AH" not in DEGER_PAZARLARI
    with pytest.raises(ValueError, match="iade"):
        noktalar_deger("AH")


def test_bilinmeyen_kural_ve_bant_dizisi() -> None:
    """Kural adı yanlışsa sessizce boş sonuç değil, hata döner."""
    from spor_toto.secim_kalibrasyonu import olc
    with pytest.raises(ValueError, match="bilinmeyen kural"):
        olc("yok")
    # Bantlar `kalibrasyon` ile aynı dizi olmak zorunda; ayrışırsa iki tablo
    # aynı soruyu farklı kenarlarla cevaplar.
    from spor_toto.kalibrasyon import BANTLAR as KALIBRASYON_BANTLARI
    assert BANTLAR is KALIBRASYON_BANTLARI


# ─── secim kuralinin invariantlari (gercek veriyle) ──────────────────────────

@pytest.fixture(scope="module")
def deger_noktalari() -> tuple[list[Nokta], list[Nokta]]:
    hepsi, secilen = noktalar_deger("1X2", 0.05)
    if not hepsi:
        pytest.skip("oran arşivi yok (data/odds)")
    return hepsi, secilen


def test_secilen_hepsinin_alt_kumesidir(
        deger_noktalari: tuple[list[Nokta], list[Nokta]]) -> None:
    """Seçim süzer, üretmez: her seçilen nokta `hepsi` içinde de olmalı."""
    hepsi, secilen = deger_noktalari
    assert len(secilen) <= len(hepsi)
    from collections import Counter
    h, s = Counter(hepsi), Counter(secilen)
    assert all(s[k] <= h[k] for k in s), "seçilen kümede hepside olmayan nokta var"


def test_esik_yukseldikce_secim_daralir(
        deger_noktalari: tuple[list[Nokta], list[Nokta]]) -> None:
    """`alpha` monoton bir eşiktir; yükseldikçe seçilen küme büyüyemez."""
    onceki = None
    for alpha in ESIK_IZGARASI:
        _, secilen = noktalar_deger("1X2", alpha)
        if onceki is not None:
            assert len(secilen) <= onceki, f"alpha={alpha} seçimi genişletti"
        onceki = len(secilen)


def test_kosullama_sonucu_gormez(
        deger_noktalari: tuple[list[Nokta], list[Nokta]]) -> None:
    """**Sızıntı bekçisi.** Seçim yalnız `p` ve `o`ya bakar, sonuca değil.

    `test_elo.py::test_elo_gelecegi_gormez` ile aynı fikir: sonuçları
    karıştırmak seçilen kümenin BÜYÜKLÜĞÜNÜ değiştiremez. Değiştirseydi,
    kural gerçekleşen sonucu okuyor olurdu ve ölçüm kendi cevabını
    seçiyor olurdu.
    """
    from spor_toto.deger import GRUPLAR, kayitlar, sec

    kayit_listesi = kayitlar("1X2")
    if not kayit_listesi:
        pytest.skip("oran arşivi yok")
    once = sum(1 for k in kayit_listesi if sec(k, 0.05) is not None)

    rng = random.Random(11)
    for k in kayit_listesi:
        paralar = [k["para"][a] for a in GRUPLAR["1X2"]]
        rng.shuffle(paralar)
        k["para"] = dict(zip(GRUPLAR["1X2"], paralar))
    sonra = sum(1 for k in kayit_listesi if sec(k, 0.05) is not None)
    assert once == sonra, "seçim sonucu okuyor — sızıntı"


def test_model_kurali_haftasiz_kesitte_bos_doner() -> None:
    """Hafta yoksa ölçüm çökmez; boş kesit boş nokta kümesidir."""
    hepsi, secilen = noktalar_model(lambda: None, [], 0.02)
    assert hepsi == [] and secilen == []


# ─── cok kiyas ve sezon kirilimi (§3.21 standardi) ───────────────────────────

def test_wilson_z_ortakla_ayni_sayiyi_verir() -> None:
    """`z = ortak.GUVEN_Z` verilirse genelleştirilmiş biçim `ortak.wilson`la aynıdır.

    Formül kopyalanmadı, genelleştirildi; bu bekçi ikisinin ayrışmasını tutar.
    """
    from spor_toto.ortak import GUVEN_Z, wilson
    for basari, n in ((40, 41), (0, 30), (119, 300), (0, 0)):
        assert wilson_z(basari, n, GUVEN_Z) == pytest.approx(wilson(basari, n))


def test_bonferroni_kiyas_arttikca_araligi_genisletir() -> None:
    """Daha çok aralık okunduysa eşik yükselir; aralık daralamaz."""
    noktalar = _sentetik(300, 0.60, 0.50)
    dar = bonferroni(noktalar, 1)
    genis = bonferroni(noktalar, 20)
    assert genis["ga_alt"] <= dar["ga_alt"] and genis["ga_ust"] >= dar["ga_ust"]
    assert genis["alfa"] < dar["alfa"]


def test_bonferroni_tek_kiyasta_ozetle_ayni_karari_verir() -> None:
    """`kiyas=1` düzeltmesiz demektir — `_ozet`in kararıyla örtüşmeli."""
    from spor_toto.secim_kalibrasyonu import _ozet
    noktalar = _sentetik(400, 0.80, 0.50)
    assert bonferroni(noktalar, 1)["icinde"] == _ozet(noktalar)["icinde"]


def test_sezon_kirilimi_noktayi_kaybetmez() -> None:
    """Kırılımın `n` toplamı havuzlanmış `n`e eşit olmalı — süzgeç sızdırmasın."""
    noktalar = (_sentetik(150, 0.55, 0.5, sezon="2023/2024")
                + _sentetik(90, 0.55, 0.5, tohum=3, sezon="2024/2025"))
    kirilim = sezon_kirilimi(noktalar)
    assert [r["sezon"] for r in kirilim] == ["2023/2024", "2024/2025"]
    assert sum(r["n"] for r in kirilim) == len(noktalar)


def test_sezon_etiketi_olmayan_nokta_kirilima_girmez() -> None:
    """Etiketsiz nokta sessizce bir sezona yazılmaz; kırılım onu dışarıda bırakır."""
    noktalar = _sentetik(100, 0.55, 0.5, sezon="") + _sentetik(100, 0.55, 0.5)
    assert sum(r["n"] for r in sezon_kirilimi(noktalar)) == 100


# ─── F3: KUPON kuralının seçim koşullu kalibrasyonu ───────────────────────

@pytest.mark.slow
def test_kupon_kurali_kalibrasyonu_BOZMUYOR():
    """F3 kapandı: kupon kuralı modelin yanıldığı yeri **seçmiyor**.

    §3.49'un ölçtüğü ters seçim gerçektir ama `model` kuralına
    (`p_model − p_piyasa > eşik`) aittir; kupon o kuralı kullanmıyor.
    Kupon kuralı için soru **dejenere değildir** — `sistem_secimi` haftanın
    tamamına ve bütçeye bakıyor, yani bilgi `p`'nin ötesinde.
    """
    from spor_toto.secim_kalibrasyonu import kupon_kurali

    r = kupon_kurali()
    assert r["n_hafta"] > 100
    assert r["banko"]["n"] > 300 and r["banko_degil"]["n"] > 300
    # Fark sifiri kesiyor -> secim kalibrasyonu bozmuyor.
    assert r["alt"] <= 0.0 <= r["ust"], (r["alt"], r["ust"])
    assert r["secim_bozuyor"] is False
    assert abs(r["fark"]) < 0.02


@pytest.mark.slow
def test_kupon_kesitinde_iki_kol_da_EKSIK_guvenli():
    """Yan bulgu ve yeni değil: favori–sürpriz yanlılığının izdüşümü.

    §5.1 A5: *"piyasanın %70–80 dediği maçlar gerçekte %78,9"*. Burada da
    iki kol da negatif çıkıyor — yani sapma seçimin ürettiği bir şey değil.
    """
    from spor_toto.secim_kalibrasyonu import kupon_kurali

    r = kupon_kurali()
    assert r["banko"]["asiri_guven"] < 0
    assert r["banko_degil"]["asiri_guven"] < 0


def test_ters_secim_ESIK_yukseldikce_buyuyor():
    """§3.49'un kendisi: `model` kuralında ters seçim yüksek eşikte gerçek."""
    from spor_toto.secim_kalibrasyonu import tarama

    satir = {round(x["esik"], 3): x for x in tarama()}
    assert satir[0.0]["icinde"] is True, "dusuk esikte anlamli olmamali"
    assert satir[0.08]["icinde"] is False, "yuksek esikte anlamli olmali"
    assert satir[0.08]["asiri_guven"] > satir[0.0]["asiri_guven"]
    assert satir[0.08]["isaret_tutuyor"] is True
