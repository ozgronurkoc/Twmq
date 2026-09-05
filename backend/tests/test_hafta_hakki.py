"""`hafta_hakki` bekçileri — bütçe kalkınca ne bozuluyor, ne kalıyor.

Modülün bütün sonucu iki yapısal olguya ve bir ölçüme dayanıyor:

1. `P(hedef)` harcamada azalmayan bir fonksiyondur — yani bütçesiz
   enbüyüklemesi dejenere (her hafta "en büyüğü al").
2. Kural λ'da monotondur — yani λ gerçekten bir bütçe yerine geçiyor,
   keyfî bir sıralama üretmiyor.
3. Ve asıl kapanış: değişken bütçe sabitini yenmiyor
   (`docs/KAZANMA_PLANI.md` §3.60).

İlk ikisi ucuz ve her koşumda sınanır; üçüncüsü `slow` ve kesitin bir
diliminde koşar. Doktrin gereği ölçümün kendisi (fark, ROI) teste
dondurulmaz — yalnız **yönü** tutulur; sayılar `.claude/olcum_kutugu.json`da
komutuyla durur.
"""
from __future__ import annotations

import random
import sys
from itertools import pairwise
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto import hafta_hakki as hh
from spor_toto.secim import sistem_secimi


def _probs(tohum: int = 7) -> list[dict[str, float]]:
    """On beş maçlık sentetik hafta — favori gücü maçtan maça değişir."""
    rnd = random.Random(tohum)
    out = []
    for _ in range(15):
        a = rnd.uniform(0.35, 0.70)
        b = rnd.uniform(0.15, (1.0 - a) * 0.8)
        out.append({"1": a, "0": b, "2": 1.0 - a - b})
    return out


@pytest.fixture(scope="module")
def cephe14():
    return hh.cephe(_probs(), garanti=14)


# ─── 1. cephe, `sistem_secimi`in ta kendisi olmalı ────────────────────────

def test_cephe_sistem_secimiyle_BIREBIR_ayni_plani_verir(cephe14):
    """Yeni yol eski yolu yeniden üretmeli — yoksa kıyas kendi kendiyle olur.

    `sabit_secim(cephe(...), B)` ile `sistem_secimi(..., B)` aynı şekli ve
    aynı `P(hedef)`i vermek zorunda; cephe yeni bir arama değil, eskisinin
    bütün fiyat basamaklarında koşturulmuş hâlidir.
    """
    probs = _probs()
    for butce in (320.0, 500.0, 1000.0, 2000.0, 3500.0, 5000.0):
        bek = sistem_secimi(probs, butce, garanti=14)
        var = hh.sabit_secim(cephe14, butce)
        assert (bek is None) == (var is None), butce
        if bek is None:
            continue
        assert var.kolon == bek.bedel, butce
        assert var.p_hedef == pytest.approx(bek.p_hedef), butce
        assert (var.banko, var.cift, var.uclu) == (bek.banko, bek.cift, bek.uclu)


# ─── 2. birinci dejenerasyon: P(hedef) parayla azalmaz ────────────────────

def test_P_hedef_harcamada_AZALMAZ_yani_bütcesiz_enbuyukleme_dejenere(cephe14):
    """Modül başlığının birinci iddiası, cepheden okunuyor.

    Sembol eklemek kaçak olasılığını düşürür; dolayısıyla pahalı basamak
    ucuzunun `P`sinin altına inemez. Bu kırılırsa "bütçesiz `P` enbüyüklemesi
    dejeneredir" cümlesi de kırılır ve modül başlığı yeniden yazılmalıdır.
    """
    assert len(cephe14) > 5
    for onceki, sonraki in pairwise(cephe14):
        assert sonraki.tl > onceki.tl
        assert sonraki.kolon > onceki.kolon
        assert sonraki.p_hedef >= onceki.p_hedef - 1e-12, (
            f"{onceki.sekil} -> {sonraki.sekil} P dustu")


def test_tavan_kaldirilinca_cephe_P_biri_gorur():
    """Tavan kalkınca cephe `P = 1`'i görüyor: dejenerasyonun somut hâli.

    Eşik `k ≤ 2` olduğu için 13 üçlü kaçağı tanım gereği ikiye kilitler ve
    `P` tam olarak 1 olur — hafta ne olursa olsun. Bedeli bugünkü bütçenin
    yüzlerce katıdır ve modül başlığının birinci dejenerasyonu budur.
    """
    tam = hh.cephe(_probs(), garanti=14, en_cok_tl=None)
    assert tam[-1].p_hedef == pytest.approx(1.0)
    assert tam[-1].uclu >= 13
    assert tam[-1].tl > 100 * 2000.0, "en ust basamak beklenenden ucuz"


# ─── 3. kural λ'da monoton — λ gerçekten bütçe yerine geçiyor ─────────────

def test_marjinal_secim_lambda_buyudukce_KUCULMEZ(cephe14):
    """λ bir fiyat etiketi: büyürse alınan şekil büyür ya da aynı kalır."""
    onceki = 0
    for lam in (0.0, 1e3, 5e3, 1e4, 5e4, 1e5, 1e7):
        sec = hh.marjinal_secim(cephe14, lam)
        assert sec is not None
        assert sec.kolon >= onceki, f"lambda {lam} kucultmus"
        onceki = sec.kolon


def test_marjinal_secim_uclari_dogru(cephe14):
    """λ→0 en ucuzu, λ→∞ en büyüğü almalı."""
    assert hh.marjinal_secim(cephe14, 0.0).kolon == cephe14[0].kolon
    assert hh.marjinal_secim(cephe14, 1e12).kolon == cephe14[-1].kolon
    assert hh.marjinal_secim([], 1.0) is None


def test_ayni_lambda_farkli_haftada_FARKLI_sekil_secebilir():
    """Aranan davranış: kural haftaya göre değişiyor mu — evet.

    Sabit bütçe tanım gereği her hafta aynı parayı harcar; λ kuralının tek
    varlık sebebi bunu bırakmasıdır. Bir hafta bile değişmiyorsa kural
    sabit bütçenin yeniden adlandırılmış hâlidir.
    """
    kolonlar = {hh.marjinal_secim(hh.cephe(_probs(t), garanti=14), 2e4).kolon
                for t in range(8)}
    assert len(kolonlar) > 1, "lambda kurali her hafta ayni sekli aliyor"


# ─── 4. λ kestirimi ve LOO ────────────────────────────────────────────────

def _sahte_cetvel(n: int = 6, odul: float = 1000.0):
    return [{"sezon": "2025_26", "hafta": i, "basamak": 2, "basamaklar": [
        {"tl": 1000.0, "kolon": 100, "sekil": "x", "banko": 7, "cift": 3,
         "uclu": 5, "p_hedef": 0.2, "kacak": 0, "tuttu": True,
         "odul": odul * (i + 1), "net": 0.0, "roi": odul * (i + 1) / 1000.0},
        {"tl": 2000.0, "kolon": 200, "sekil": "y", "banko": 6, "cift": 3,
         "uclu": 6, "p_hedef": 0.3, "kacak": 0, "tuttu": True,
         "odul": odul * (i + 1), "net": 0.0, "roi": odul * (i + 1) / 2000.0},
    ]} for i in range(n)]


def test_basamak_karnesi_her_basamagi_ayri_sayar():
    """Kuralsız tablo: her kolon sayısı kendi haftalarıyla toplanmalı."""
    c = _sahte_cetvel(3)
    k = hh.basamak_karnesi(c)
    assert [x["kolon"] for x in k] == [100, 200]
    assert k[0]["hafta"] == k[1]["hafta"] == 3
    assert k[0]["tutan"] == 3
    assert k[0]["ort_odul"] == pytest.approx(1000 * (1 + 2 + 3) / 3)
    assert k[0]["roi"] == pytest.approx(k[0]["ort_odul"] / 1000.0)
    assert k[1]["roi"] == pytest.approx(k[0]["roi"] / 2), \
        "ayni odul iki kat maliyette yari ROI vermeli"


def test_lambda_kestirimi_tutturan_haftalarin_ortalamasi():
    c = _sahte_cetvel(4)
    assert hh.lambda_kestir(c) == pytest.approx(1000 * (1 + 2 + 3 + 4) / 4)


def test_lambda_LOO_haftayi_GERCEKTEN_disarida_birakir():
    """LOO kolu iç örneklemi kapatıyor mu — bırakılan hafta sayıyı değiştirmeli."""
    c = _sahte_cetvel(4)
    tam = hh.lambda_kestir(c)
    eksik = hh.lambda_kestir(c, disarida=("2025_26", 3))
    assert eksik != tam
    assert eksik == pytest.approx(1000 * (1 + 2 + 3) / 3)


def test_tutturmayan_hafta_lambdaya_girmez():
    c = _sahte_cetvel(2)
    for b in c[0]["basamaklar"]:
        b["tuttu"] = False
    assert hh.lambda_kestir(c) == pytest.approx(2000.0)


# ─── 5. işaret sınavı kendi kendini kandırmıyor ───────────────────────────

def test_isaret_sinavi_ekilmis_isareti_BULUR():
    """Sınav çalışıyor mu: `p` ile ROI aynı sırayla artarsa `rho` pozitif."""
    c = []
    for i in range(40):
        c.append({"sezon": "s", "hafta": i, "basamak": 1, "basamaklar": [
            {"tl": 2000.0, "kolon": 200, "sekil": "x", "banko": 7, "cift": 3,
             "uclu": 5, "p_hedef": 0.1 + i / 100.0, "kacak": 0, "tuttu": True,
             "odul": 100.0 * i, "net": 0.0, "roi": 0.05 * i}]})
    s = hh.isaret_sinavi(c, n=2000)
    assert s["rho"] > 0.9
    assert not s["kesiyor"], "ekilmis isaret sifiri kesmemeli"


def test_isaret_sinavi_gurultude_SIFIRI_keser():
    """Ve kandırmıyor: `p` ile ROI ilişkisiz olduğunda aralık sıfırı kesmeli."""
    rnd = random.Random(3)
    c = []
    for i in range(40):
        c.append({"sezon": "s", "hafta": i, "basamak": 1, "basamaklar": [
            {"tl": 2000.0, "kolon": 200, "sekil": "x", "banko": 7, "cift": 3,
             "uclu": 5, "p_hedef": rnd.random(), "kacak": 0, "tuttu": True,
             "odul": 0.0, "net": 0.0, "roi": rnd.random()}]})
    assert hh.isaret_sinavi(c, n=2000)["kesiyor"]


# ─── 6. cetvel yalnız 14-garantide koşar ve bunu söyler ───────────────────

def test_cetvel_13_garantide_HATA_verir():
    """13-garantinin kolon listesi satıcıdadır; sessizce yanlış ölçmez."""
    with pytest.raises(ValueError, match="14-garantide"):
        hh.hafta_cetveli({"sezon": "s", "hafta": 1, "probs": _probs(),
                          "gercek": ["1"] * 15, "tablo": {}}, garanti=13)


# ─── 7. haftalık koşumun merdiveni ────────────────────────────────────────

def test_merdiven_secili_satiri_isaretler_ve_secilie_gore_olcer(capsys):
    """`--oncesi` bütçenin ne satın aldığını göstermeli.

    İki şey sınanır: seçilen basamak `->` ile işaretli, ve marjinal fiyat
    **seçiliye göre** — yani seçili satırın kendi TL/puan hücresi boş.
    """
    from scripts.hafta_kos import _merdiven

    probs = _probs()
    adimlar = hh.cephe(probs, garanti=14, en_cok_tl=5000.0)
    secili = adimlar[len(adimlar) // 2]
    _merdiven(probs, 14, secili.kolon, en_cok_tl=5000.0)
    satirlar = capsys.readouterr().out.splitlines()
    isaretli = [s for s in satirlar if s.strip().startswith("->")]
    assert len(isaretli) == 1
    assert f"{secili.kolon}" in isaretli[0]
    assert isaretli[0].rstrip().endswith(f"{secili.p_hedef:.4f}"), \
        "secili satirin TL/puan hucresi bos olmali"


# ─── 8. gerçek kesitte: cetvel kuruluyor ve kural onu okuyabiliyor ────────

@pytest.mark.slow
def test_gercek_kesitte_cetvel_ve_kural_ucdan_uca(request):
    """Uçtan uca: gerçek hafta → cetvel → kural → karne satırı.

    Dar bir dilimde koşar (ölçüm değil, boru hattı sınavı). Ölçümün kendisi
    `python -m spor_toto.hafta_hakki --kiyas` ile üretilir ve sayıları
    `.claude/olcum_kutugu.json`dadır.
    """
    cet = hh.cetvel(hafta_siniri=3)
    assert cet, "kesitten cetvel cikmadi"
    for c in cet:
        assert c["basamak"] >= 5
        for b in c["basamaklar"]:
            assert b["odul"] >= 0.0
            assert b["roi"] == pytest.approx(b["odul"] / b["tl"])
    k = hh.kural_kiyasi(cet)
    assert k["temel"] == "sabit-2000"
    assert "lambda-LOO" in k["ozet"]
    for ad, o in k["ozet"].items():
        assert o["hafta"] == len(cet), ad


@pytest.mark.slow
def test_E6_KAPANISI_hala_gecerli():
    """§E6'nın kapanışı: hiçbir kural sabit bütçeyi ayrıştırılabilir biçimde
    yenmiyor, ve merdivende yukarı çıkmak geri dönüş **oranını** açmıyor.

    Bekçi kasıtlı olarak dar: ölçümün değerlerini (fark, ROI, `rho`)
    dondurmaz — doktrin bunu yasaklıyor, sayılar `.claude/olcum_kutugu.json`da
    komutuyla durur. Tuttuğu tek şey **kapanışın kendisi**:

    1. eşleştirilmiş %95 aralıkların hepsi sıfırı keser;
    2. basamak geri dönüşünün kolon sayısıyla monoton bir eğilimi yoktur.

    Biri kırılırsa §E6 *"bütçe ekseni kapandı"* diyemez ve yeniden
    yazılmak zorundadır — tam olarak istenen davranış.

    Kesitin bir dilimidir (tam ölçüm ~20 dk); dilimde aralıklar daha geniş,
    yani bu bekçi kapanışı **kolay** doğrular ve ancak güçlü bir tersine
    dönüşte kırılır.
    """
    cet = hh.cetvel(hafta_siniri=12)
    assert len(cet) >= 10
    k = hh.kural_kiyasi(cet)
    acan = [ad for ad, f in k["fark"].items() if not f["kesiyor"]]
    assert not acan, (
        f"butce ekseni ACILDI: {acan} sifiri kesmiyor — §E6 yeniden yazilmali")
    kar = hh.basamak_karnesi(cet)
    rho = hh._spearman([x["kolon"] for x in kar], [x["roi"] for x in kar])
    assert abs(rho) < 0.7, (
        f"basamak ROI'si kolon sayisiyla egilim gosteriyor (rho={rho:+.3f}) — "
        "§E6'nin 'oran basamaktan bagimsiz' satiri yeniden olculmeli")
