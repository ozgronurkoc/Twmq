"""Müşterek bahis beklenen değeri — kapalı formun ve varsayımların denetimi.

**En kritik test `test_kapali_form_kaba_kuvvetle_ayni`.** `E[1/(1+W)]`
kapalı formu bir satırdır ve yanlış yazılırsa hiçbir yerde patlamaz:
beklenen getiri sessizce yanlış bir sayı verir ve o sayı "ölçtük" diye
okunur. Bekçi, formülü küçük `N` için tam binom toplamına karşı doğrular.

İkinci bekçi `test_uyari_ve_varsayimlar_govdede_duruyor`: bu modülün
ürettiği hiçbir sayı ölçülmüş değildir ve gövdesinden ayrılırsa
ölçülmüşlerle karışır.
"""
from __future__ import annotations

from math import comb
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent

from spor_toto.core import MAC_SAYISI
from spor_toto.getiri import (
    KADEMELER,
    KALABALIK_MODELLERI,
    VARSAYILAN_KOMISYON,
    VARSAYILAN_PAY,
    beklenen_getiri,
    duyarlilik,
    kademe_getirisi,
    kalabalik_kademeleri,
    kupon_kademeleri,
    pay_beklentisi,
)


def _kaba_kuvvet(n: int, q: float) -> float:
    """`E[1/(1+W)]`'yi binom toplamıyla doğrudan hesapla."""
    return sum(comb(n, w) * q ** w * (1.0 - q) ** (n - w) / (1 + w)
               for w in range(n + 1))


# ─── kapalı form — asıl bekçi ─────────────────────────────────────────────

@pytest.mark.parametrize("n", [0, 1, 2, 5, 17, 40])
@pytest.mark.parametrize("q", [1e-6, 0.01, 0.2, 0.5, 0.87, 0.999])
def test_kapali_form_kaba_kuvvetle_ayni(n: int, q: float):
    assert pay_beklentisi(n, q) == pytest.approx(_kaba_kuvvet(n, q), rel=1e-9)


def test_q_sifir_limitinde_pay_tam():
    """Kimse tutturmuyorsa pay bölünmez — 0/0 limiti 1'dir."""
    assert pay_beklentisi(1000, 0.0) == 1.0
    assert pay_beklentisi(1000, -0.0) == 1.0
    # Limite yaklasim da surekli olmali (kayan noktada patlamamali).
    assert pay_beklentisi(1000, 1e-12) == pytest.approx(1.0, abs=1e-6)


def test_q_bir_limitinde_herkes_tutturur():
    assert pay_beklentisi(9, 1.0) == pytest.approx(0.1)


def test_pay_q_arttikca_azalir():
    """`N·q` büyüdükçe pay söner — havuz ekseninin bütün gerekçesi."""
    paylar = [pay_beklentisi(500, q) for q in (0.001, 0.01, 0.1, 0.5)]
    assert paylar == sorted(paylar, reverse=True)


def test_pay_rakip_kolon_arttikca_azalir():
    paylar = [pay_beklentisi(n, 0.05) for n in (10, 100, 1000, 10_000)]
    assert paylar == sorted(paylar, reverse=True)


def test_buyuk_nq_de_pay_1_bolu_nq_gibi_soner():
    """Asimptotik davranış: `N·q ≫ 1` iken `E[1/(1+W)] ≈ 1/(N·q)`."""
    n, q = 200_000, 0.01
    assert pay_beklentisi(n, q) == pytest.approx(1.0 / (n * q), rel=1e-3)


def test_negatif_rakip_kolon_reddedilir():
    with pytest.raises(ValueError):
        pay_beklentisi(-1, 0.1)


# ─── kademe getirisi ──────────────────────────────────────────────────────

def test_komisyon_dagitilan_havuzu_kisar():
    tam = kademe_getirisi(1_000_000, 0.0, 0, 0.0, 1.0)
    yari = kademe_getirisi(1_000_000, 0.5, 0, 0.0, 1.0)
    assert tam == pytest.approx(1_000_000)
    assert yari == pytest.approx(500_000)


def test_gecersiz_komisyon_reddedilir():
    for k in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError):
            kademe_getirisi(1000, k, 10, 0.1, 1.0)


def test_tek_kazanan_tum_kademeyi_alir():
    """Kalabalık yoksa (q=0) kademenin payının tamamı bizimdir."""
    assert kademe_getirisi(1000, 0.0, 100_000, 0.0, 0.55) == pytest.approx(550)


# ─── beklenen getiri gövdesi ──────────────────────────────────────────────

def _taban(**kw):
    varsayilan = {"kademe_olasiliklari": {14: 0.01, 13: 0.05, 12: 0.20},
                  "bedel": 1000.0, "havuz": 10_000_000.0,
                  "rakip_kolon": 100_000,
                  "q_kalabalik": {14: 0.01, 13: 0.05, 12: 0.20}}
    varsayilan.update(kw)
    return beklenen_getiri(**varsayilan)  # type: ignore[arg-type]


def test_uyari_ve_varsayimlar_govdede_duruyor():
    """**Asıl bekçi.** Sayı varsayımlarından ayrılırsa ölçülmüş sanılır."""
    r = _taban()
    assert "OLCULMEDI" in r["uyari"]
    assert "Arayuze cikmaz" in r["uyari"]
    v = r["varsayimlar"]
    assert set(v) == {"havuz", "komisyon", "rakip_kolon", "pay_dagilimi",
                      "pay_kaynagi"}
    assert v["pay_dagilimi"] == VARSAYILAN_PAY
    assert v["komisyon"] == VARSAYILAN_KOMISYON


def test_getiri_ozdeslikleri():
    r = _taban()
    assert r["beklenen_getiri"] == pytest.approx(r["beklenen_kazanc"] - r["bedel"])
    assert r["getiri_orani"] == pytest.approx(r["beklenen_kazanc"] / r["bedel"])
    assert sum(s["katki"] for s in r["kademeler"]) == pytest.approx(
        r["beklenen_kazanc"])


def test_katki_p_carpi_pay():
    for s in _taban()["kademeler"]:
        assert s["katki"] == pytest.approx(s["p"] * s["beklenen_pay"])


def test_sifir_olasilikli_kademe_satir_acmaz():
    r = _taban(kademe_olasiliklari={14: 0.0, 13: 0.0, 12: 0.3})
    assert [s["kademe"] for s in r["kademeler"]] == [12]


def test_kademeler_yuksekten_alcaga():
    assert [s["kademe"] for s in _taban()["kademeler"]] == list(KADEMELER)
    assert list(KADEMELER) == sorted(KADEMELER, reverse=True)


def test_bedelsiz_kuponda_oran_yok():
    """Sıfıra bölme yerine `None` — uydurma bir oran yazmaktan iyidir."""
    assert _taban(bedel=0.0)["getiri_orani"] is None


def test_pay_dagilimi_degistirilebiliyor():
    """Varsayım **parametredir**: çağıran onu değiştirebilmeli."""
    a = _taban(q_kalabalik={14: 0.001, 13: 0.05, 12: 0.30})
    b = _taban(q_kalabalik={14: 0.001, 13: 0.05, 12: 0.30},
               pay_dagilimi={14: 1.0, 13: 0.0, 12: 0.0})
    assert b["beklenen_kazanc"] != a["beklenen_kazanc"]
    assert b["varsayimlar"]["pay_dagilimi"] == {14: 1.0, 13: 0.0, 12: 0.0}


def test_ortalama_kolonsak_pay_bolusumu_hicbir_sey_degistirmez():
    """Modülün en sert sonucu — ve tesadüf değil, aritmetik.

    `N·q ≫ 1` iken bir kademenin beklenen payı `havuz(1−c)·w_k/((N+1)q_k)`
    olur. Bizim tutturma olasılığımız kalabalığınkine eşitse (`p_k = q_k`)
    katkı `havuz(1−c)·w_k/(N+1)`'e iner ve `Σ w_k = 1` olduğu için **toplam
    `w`'den tamamen bağımsız** kalır: kalan tek değişken kolon sayısıdır.

    Okunuşu: *sıradan bir kolon kadar isabetliysek havuzun kademelere nasıl
    bölündüğü bizi hiç ilgilendirmez.* Kazanç ancak `p_k > q_k` olan — yani
    kalabalıktan saptığımız — kademeden gelir; §7'deki
    `edge = p_piyasa − oynanma_payı` satırının kapalı formdaki karşılığı
    budur.
    """
    q = {14: 0.01, 13: 0.05, 12: 0.20}
    a = _taban(kademe_olasiliklari=dict(q), q_kalabalik=q)
    b = _taban(kademe_olasiliklari=dict(q), q_kalabalik=q,
               pay_dagilimi={14: 1.0, 13: 0.0, 12: 0.0})
    c = _taban(kademe_olasiliklari=dict(q), q_kalabalik=q,
               pay_dagilimi={14: 0.2, 13: 0.3, 12: 0.5})
    assert a["beklenen_kazanc"] == pytest.approx(b["beklenen_kazanc"], rel=1e-9)
    assert a["beklenen_kazanc"] == pytest.approx(c["beklenen_kazanc"], rel=1e-9)
    # Ve deger tam olarak havuz(1-c)/(N+1)'dir.
    assert a["beklenen_kazanc"] == pytest.approx(
        10_000_000.0 * (1.0 - VARSAYILAN_KOMISYON) / 100_001, rel=1e-9)


def test_kalabaliktan_sapinca_kazanc_dogar():
    """`p_k > q_k` olan kademe **fazladan** getirir — asıl kenar budur."""
    q = {14: 0.01, 13: 0.05, 12: 0.20}
    esit = _taban(kademe_olasiliklari=dict(q), q_kalabalik=q)
    sapan = _taban(kademe_olasiliklari={14: 0.02, 13: 0.05, 12: 0.20},
                   q_kalabalik=q)
    assert sapan["beklenen_kazanc"] > esit["beklenen_kazanc"]


def test_bizim_p_ile_kalabalik_q_farkli_seyler():
    """İkisi karıştırılırsa pay tamamen yanlış çıkar — ayrı ayrı etkili."""
    az_kalabalik = _taban(q_kalabalik={14: 0.001, 13: 0.001, 12: 0.001})
    cok_kalabalik = _taban(q_kalabalik={14: 0.5, 13: 0.5, 12: 0.5})
    assert az_kalabalik["beklenen_kazanc"] > cok_kalabalik["beklenen_kazanc"]


# ─── duyarlılık ───────────────────────────────────────────────────────────

def test_duyarlilik_rakip_kolon_arttikca_getiri_duser():
    egri = duyarlilik(_taban(), (0.25, 0.5, 1.0, 2.0, 4.0))
    getiriler = [d["beklenen_getiri"] for d in egri]
    assert getiriler == sorted(getiriler, reverse=True)
    assert [d["rakip_kolon"] for d in egri] == [25_000, 50_000, 100_000,
                                           200_000, 400_000]


def test_duyarlilik_carpan_bir_tabanla_ayni():
    taban = _taban()
    bir = duyarlilik(taban, (1.0,))[0]
    assert bir["beklenen_getiri"] == pytest.approx(taban["beklenen_getiri"])


def test_duyarlilik_kolonu_negatife_dusurmez():
    assert duyarlilik(_taban(rakip_kolon=1), (0.0,))[0]["rakip_kolon"] == 0


# ─── gerçek kupondan kademe olasılıkları ──────────────────────────────────

def _probs(p1: float = 0.5):
    kalan = (1.0 - p1) / 2
    return [{"1": p1, "0": kalan, "2": kalan} for _ in range(15)]


def test_kupon_kademeleri_aritmetikle_uyumlu():
    """`P(en iyi = 15−k) = P(k)` — `secim` modül başlığındaki aritmetik.

    Kaplama döneminde bu `14−k` idi ve 15 kademesi hiç yoktu; düzde en iyi
    kolon `15−k`'dır ve bu bir **eşitliktir**, alt sınır değil.
    """
    from spor_toto.ortak import kacak_dagilimi
    from spor_toto.secim import en_iyi_secim, kacak_olasiligi

    probs = _probs(0.55)
    kademe_p, bedel = kupon_kademeleri(probs, 4096)
    plan = en_iyi_secim(probs, 4096)
    assert plan is not None
    assert bedel == plan.bedel
    d = kacak_dagilimi([kacak_olasiligi(p, len(s))
                        for p, s in zip(probs, plan.secimler)])
    for k in range(4):
        assert kademe_p[15 - k] == pytest.approx(d[k]), f"k={k}"


def test_kupon_kademeleri_butce_buyudukce_iyilesir():
    az, _ = kupon_kademeleri(_probs(0.55), 256)
    cok, _ = kupon_kademeleri(_probs(0.55), 16_384)
    assert sum(cok.values()) > sum(az.values())


def test_kupon_kademeleri_bedeli_butceyi_asmaz():
    for butce in (256, 1024, 4096, 16_384):
        _, bedel = kupon_kademeleri(_probs(0.5), butce)
        assert 0 < bedel <= butce


def test_kupon_kademeleri_bos_haftada_bos_doner():
    """Plan kurulamıyorsa uydurma sayı üretilmez.

    **Bu test eskiden 1 kolonluk bütçeyle sınıyordu** — kaplamada en ucuz
    plan 16 kolondu (yedi çifte + Hamming bloğu), o yüzden 1 kolon "hiçbir
    planı karşılamıyor" demekti. Düzde 1 kolon geçerli bir plandır (15 maç
    da tek). Boş dönen tek hâl artık maçsız haftadır.
    """
    kademe_p, bedel = kupon_kademeleri([], 1024)
    assert kademe_p == {} and bedel == 0


def test_kupon_kademeleri_motoru_besleyebiliyor():
    """Uçtan uca: iki fonksiyon **aynı birimde** konuşuyor mu?

    İlk sürümde konuşmuyordu — tek kolonun `P(14+)`'i 2.228 kolonluk bir
    bedelle toplanıyordu. Bekçi bedelin kupondan geldiğini doğruluyor.
    """
    kademe_p, kolon = kupon_kademeleri(_probs(0.55), 4096)
    r = beklenen_getiri(kademe_p, kolon * 1.5, 50_000_000.0, 400_000,
                        kademe_p)
    assert r["bedel"] == pytest.approx(kolon * 1.5)
    assert len(r["kademeler"]) == len(KADEMELER)


# ─── kalabalık modeli — motoru boş olmaktan kurtaran parça ────────────────

def test_kalabalik_favori_orneklemden_hep_yuksek():
    """`favori` üst sınırdır: herkes favoriyi işaretlerse isabet en yüksek."""
    a = kalabalik_kademeleri(_probs(0.55), "orneklem")
    b = kalabalik_kademeleri(_probs(0.55), "favori")
    for k in KADEMELER:
        assert b[k] > a[k]


def test_kalabalik_tek_kolon_kuponla_karistirilamaz():
    """**Asıl bekçi.** Tek kolon ile 3.888 kolonluk kaplama aynı şey değil.

    İlk sürüm `q`'yu bizim kademe olasılıklarımıza eşitliyordu; aradaki
    fark burada üç büyüklük mertebesidir ve karıştırılırsa beklenen pay
    binlerce kat yanlış çıkar.
    """
    probs = _probs(0.55)
    bizim, _ = kupon_kademeleri(probs, 4096)
    kalabalik = kalabalik_kademeleri(probs, "orneklem")
    for k in KADEMELER:
        assert bizim[k] > 100 * kalabalik[k]


def test_kalabalik_kesin_hafta_bire_gider():
    """Her maç kesinse tek kolon da tavanı tutturur.

    Oynanma payları da veriliyor: `oynanma` modeli onları **ister** ve
    verilmezse hata atar (ölçüm olmadan ölçüm modeli çalıştırılamaz).
    Kesin haftada kalabalık da kesin olduğu için üç model de aynı yere
    varmalı.
    """
    kesin = [{"1": 1.0, "0": 0.0, "2": 0.0}] * MAC_SAYISI
    for model in KALABALIK_MODELLERI:
        q = kalabalik_kademeleri(kesin, model, kesin)
        assert q[KADEMELER[0]] == pytest.approx(1.0)
        assert q[13] == pytest.approx(0.0, abs=1e-12)


def test_kalabalik_kademeleri_azalan():
    """Daha zor kademe daha seyrek — sıralama bozulursa hesap ters döner."""
    q = kalabalik_kademeleri(_probs(0.5), "orneklem")
    assert q[14] < q[13] < q[12]


def test_kalabalik_olasiliklari_gecerli():
    q = kalabalik_kademeleri(_probs(0.5), "orneklem")
    assert all(0.0 <= v <= 1.0 for v in q.values())
    assert sum(q.values()) <= 1.0


def test_kalabalik_bilinmeyen_model_reddedilir():
    with pytest.raises(ValueError):
        kalabalik_kademeleri(_probs(), "kahin")


def test_kalabalik_normalize_edilmemis_fiyati_toparlar():
    """Marj arındırılmamış fiyat gelirse toplam 1'e çekilir."""
    ham = [{"1": 1.0, "0": 0.6, "2": 0.4}] * MAC_SAYISI
    q = kalabalik_kademeleri(ham, "orneklem")
    assert all(0.0 <= v <= 1.0 for v in q.values())


# ─── ölçekli duyarlılık ───────────────────────────────────────────────────

def test_havuz_da_olceklenince_egri_duzlesir():
    """Müşterek bahsin en önemli sezgisi — ve tam bir özdeşlik.

    `N·q ≫ 1` iken pay `havuz(1−c)·w/(N·q)`'ya iner; havuz ve `N` aynı
    çarpanla ölçeklenirse ikisi **birbirini götürür**. Yani havuzun
    büyüklüğü getiriyi belirlemez, `p_k/q_k` oranı belirler.
    """
    taban = _taban(rakip_kolon=1_000_000,
                   q_kalabalik={14: 0.01, 13: 0.05, 12: 0.20})
    egri = duyarlilik(taban, (0.25, 1.0, 4.0), havuzu_olcekle=True)
    oranlar = [d["getiri_orani"] for d in egri]
    for o in oranlar:
        # Kalan sapma `N` ile `N+1` arasindaki farktir; 16 kat olceklemede
        # bile onbinde birin altinda kaliyor.
        assert o == pytest.approx(oranlar[0], rel=1e-4)
    assert [d["havuz"] for d in egri] == [2_500_000.0, 10_000_000.0,
                                          40_000_000.0]


def test_havuz_sabitken_egri_duzlesmiyor():
    """Karşıt bekçi: iki eğri **farklı** sorular sorar, karıştırılamaz."""
    taban = _taban(rakip_kolon=1_000_000,
                   q_kalabalik={14: 0.01, 13: 0.05, 12: 0.20})
    sabit = [d["getiri_orani"] for d in duyarlilik(taban, (0.25, 1.0, 4.0))]
    assert sabit == sorted(sabit, reverse=True)
    assert sabit[0] > 3 * sabit[-1]


def test_rapor_pay_kunyesini_TASIR():
    """Havuz payı oranının künyesi rapor gövdesinde bulunmalı.

    `PAY_KAYNAGI` tanımlıydı ama **hiçbir yerden okunmuyordu**: "bu oran
    ölçüm mü varsayım mı" bilgisi yalnızca kaynak dosyada duruyor, raporu
    okuyana ulaşmıyordu. `KOLON_BEDELI_KAYNAGI` ile aynı desen — o zaten
    gövdede taşınıyor ve testi var.
    """
    from spor_toto.getiri import PAY_KAYNAGI

    kunye = _taban()["varsayimlar"]["pay_kaynagi"]
    assert kunye == PAY_KAYNAGI
    # Kunye ise yarar: hangi haftalardan olculdugunu SOYLEMELI.
    assert "hafta" in kunye.lower()


def test_olculen_ve_varsayilan_kolon_bedeli_KARISTIRILMIYOR():
    """İki kolon bedeli var ve ayrı kalmak zorundalar.

    `KOLON_BEDELI` (₺10) **ölçüldü** ve künyesi var
    (`KOLON_BEDELI_KAYNAGI`); `VARSAYILAN_KOLON_BEDELI` (₺1,50) ise
    doğrulanmamış bir varsayımdır ve hesabın varsayılanıdır.

    **Ölçülmüş bir ayrışmadan geldi.** Varsayım üç yerde birden yazılıydı:
    `getiri` CLI'sının `--kolon-bedeli` bayrağında çıplak bir sabit olarak,
    `scripts/kademe_analizi.py`de ikinci kez, ve belge onu "`getiri.py` CLI
    varsayılanıdır" diye anarak üçüncü kez. Yani ölçülmüş ₺10 ile varsayılan
    ₺1,50 arasındaki ayrım hiçbir yerde ADLANDIRILMAMIŞTI — ikisi aynı
    kavramın iki değeri gibi görünüyordu.

    Bu test ayrımı tutar: değerler eşitlenirse ya bir ölçüm sessizce
    varsayıma dönmüş ya da varsayım ölçüm gibi kullanılmaya başlanmıştır.

    **2026-09-04: betiğin okuduğu sabit DEĞİŞTİ ve bu kasıtlı.** ₺10 üç
    bağımsız kökenden doğrulanınca (`KOLON_BEDELI` künyesi) hesabın
    varsayılanı ölçülen bedele geçti; `kademe_analizi` artık
    `getiri.KOLON_BEDELI` okuyor. Testin asıl işi değişmedi — **üçüncü
    kopyanın geri gelmemesi** — yalnızca hangi tek kaynağı okuduğu değişti.
    `VARSAYILAN_KOLON_BEDELI` silinmedi: ₺1,50 ile yayımlanmış sayılar
    hangi ölçekte olduklarını söyleyebilmeli.
    """
    from spor_toto.getiri import (
        KOLON_BEDELI,
        KOLON_BEDELI_KAYNAGI,
        VARSAYILAN_KOLON_BEDELI,
    )

    assert KOLON_BEDELI != VARSAYILAN_KOLON_BEDELI, (
        "olculen bedel ile varsayilan esitlenmis — hangisinin oldugu belirsizlesir")
    assert KOLON_BEDELI_KAYNAGI, "olculen bedelin kunyesi bos"

    # Betik tarafi da AYNI varsayimi okumali, kendi kopyasini degil.
    import sys
    sys.path.insert(0, str(KOK))
    from scripts.kademe_analizi import KOLON_BEDELI as betik_bedeli

    assert betik_bedeli == KOLON_BEDELI, (
        "kademe_analizi OLCULEN bedeli okumali; kendi kopyasini tasiyorsa "
        "ucuncu kopya geri gelmis demektir")


def test_kapisiz_olcum_betikleri_KOSUYOR():
    """`kademe_analizi` ve `acilis_kapanis` çalışabilir durumda olmalı.

    İkisi de dosya üretmiyor, **stdout'a** basıyor — yani bir "bayatlık
    kapısı" (`--kontrol`) onlara uymaz. Ama ikisinin de sayıları belgelere
    ve rapor sayfasına giriyor, dolayısıyla sessizce kırılmaları belgelerin
    kaynağını yok eder. En az koruma: gerçekten koşuyorlar mı.
    """
    import subprocess
    import sys

    for betik in ("kademe_analizi.py", "acilis_kapanis.py"):
        # S603 gerekcesi: `sys.executable` ve depo ici sabit betik adi.
        r = subprocess.run([sys.executable, str(KOK / "scripts" / betik)],  # noqa: S603
                           cwd=KOK, capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, f"{betik} dustu:\n{r.stderr[-800:]}"
        assert r.stdout.strip(), f"{betik} hicbir sey basmadi"
