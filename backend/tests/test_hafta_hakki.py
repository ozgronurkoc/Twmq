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
    return hh.cephe(_probs(), garanti=15)


# ─── 1. cephe, `sistem_secimi`in ta kendisi olmalı ────────────────────────

def test_cephe_sistem_secimiyle_BIREBIR_ayni_plani_verir(cephe14):
    """Yeni yol eski yolu yeniden üretmeli — yoksa kıyas kendi kendiyle olur.

    `sabit_secim(cephe(...), B)` ile `sistem_secimi(..., B)` aynı şekli ve
    aynı `P(hedef)`i vermek zorunda; cephe yeni bir arama değil, eskisinin
    bütün fiyat basamaklarında koşturulmuş hâlidir.
    """
    probs = _probs()
    for butce in (320.0, 500.0, 1000.0, 2000.0, 3500.0, 5000.0):
        bek = sistem_secimi(probs, butce, garanti=15)
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
    tam = hh.cephe(_probs(), garanti=15, en_cok_tl=None)
    assert tam[-1].p_hedef == pytest.approx(1.0)
    # Duzde esik k<=3 oldugu icin P=1'e 12 uclu ile ulasiliyor
    # (3 tek kalir ve ucu de kacsa k=3, yani hedef hala tutar).
    # Kaplamada esik k<=2 idi ve 13 uclu gerekiyordu.
    assert tam[-1].uclu >= 12
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
    # λ duz olceginde: bir birim P(hedef) sekiz kat pahali (LAMBDA_BANDI
    # kunyesi). Eski 2e4 duzde her hafta ayni sekli veriyordu ve bu kuralin
    # degil BANDIN bayatligiydi.
    kolonlar = {hh.marjinal_secim(hh.cephe(_probs(t), garanti=15), 8e4).kolon
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


def test_fiyat_karnesi_uc_olcuyu_de_lambdaya_oranlar():
    """§E6'nın 4. maddesinin sayıları buradan çıkıyor — üçü de λ'ya oranlı.

    Sahte cetvelde iki basamak var: 1.000 TL/`p`=0,2 → 2.000 TL/`p`=0,3.
    Uçtan uca fiyat `(2000−1000)/(0,3−0,2) = 10.000`; tek adım da aynı;
    referans 1.000 TL alınırsa "bir üst" de aynı olmalı.
    """
    c = _sahte_cetvel(4)
    f = hh.fiyat_karnesi(c, referans_tl=1000.0)
    assert f["lambda"] == pytest.approx(2500.0)   # 1000*(1+2+3+4)/4
    for ad in ("uctan_uca", "bir_ust", "en_ucuz_adim"):
        assert f[ad]["n"] == 4, ad
        assert f[ad]["medyan"] == pytest.approx(10_000.0), ad
        assert f[ad]["kat"] == pytest.approx(10_000.0 / 2500.0), ad


def test_fiyat_karnesi_bir_ust_referansin_USTUNDEKI_adimi_olcer():
    """`bir_ust`, referans basamağın üstü yoksa o haftayı saymamalı."""
    c = _sahte_cetvel(2)
    f = hh.fiyat_karnesi(c, referans_tl=5000.0)   # iki basamak da referansin altinda
    assert f["bir_ust"]["n"] == 0
    assert f["uctan_uca"]["n"] == 2


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


def test_isaret_sinavi_permutasyon_p_de_doner():
    """Aralık **ve** p birlikte dönmeli — Holm'a girecek olan p'dir."""
    c = []
    for i in range(40):
        c.append({"sezon": "s", "hafta": i, "basamak": 1, "basamaklar": [
            {"tl": 2000.0, "kolon": 200, "sekil": "x", "banko": 7, "cift": 3,
             "uclu": 5, "p_hedef": 0.1 + i / 100.0, "kacak": 0, "tuttu": True,
             "odul": 100.0 * i, "net": 0.0, "roi": 0.05 * i}]})
    s = hh.isaret_sinavi(c, n=2000)
    assert s["p"] < 0.01, "ekilmis isaret permutasyondan gecmeli"


def test_devir_isareti_arsivde_olmayan_haftayi_ATLAR():
    """Havuzu ilan edilmemiş (ya da arşivde olmayan) hafta sınava girmez.

    Sessiz atlama burada **istenen** davranıştır ama görünür olmalı: kesit
    114'ten 113'e bu yüzden düşüyor. Test iki kolu da tutar — var olmayan
    sezon hiç girmez, var olan hafta girer.
    """
    yok = _sahte_cetvel(3)
    for c in yok:
        c["sezon"] = "1999_00"
    assert hh.devir_isareti(yok) == []

    var = _sahte_cetvel(3)        # sezon 2025_26 — 1. ve 2. hafta arsivde var
    ciftler = hh.devir_isareti(var)
    assert ciftler, "gercek arsivden hicbir hafta eslesmedi"
    assert all(d >= 0.0 for d, _ in ciftler)


def test_kuyruk_payi_bilinen_dagilimda_dogru_sayiyor():
    """§E6'nın 5. maddesinin sayısı buradan çıkıyor — elle değil.

    Tek basamak, dört hafta, ödüller 100/1/1/1: en iyi **bir** hafta payın
    %97,1'ini taşır (100/103) ve en iyi 5 istenirse pay 1,0 olur.
    """
    c = []
    for i, odul in enumerate((100.0, 1.0, 1.0, 1.0)):
        c.append({"sezon": "s", "hafta": i, "basamak": 1, "basamaklar": [
            {"tl": 1000.0, "kolon": 100, "sekil": "x", "banko": 7, "cift": 3,
             "uclu": 5, "p_hedef": 0.2, "kacak": 0, "tuttu": True,
             "odul": odul, "net": 0.0, "roi": odul / 1000.0}]})
    k = hh.kuyruk_payi(c, en_iyi=1)
    assert k["basamak"] == 1
    assert k["satirlar"][0]["pay"] == pytest.approx(100 / 103)
    assert k["tek_hafta_en_cok"] == pytest.approx(100 / 103)
    assert hh.kuyruk_payi(c, en_iyi=5)["pay_en_az"] == pytest.approx(1.0)


def test_kuyruk_payi_odulsuz_basamagi_ATLAR():
    """Toplamı sıfır olan basamakta pay tanımsız — satır hiç çıkmamalı."""
    c = _sahte_cetvel(2)
    for w in c:
        for b in w["basamaklar"]:
            b["odul"] = 0.0
    assert hh.kuyruk_payi(c)["basamak"] == 0


def test_devir_ikili_tek_kol_bos_kalirsa_KESIYOR_der():
    """İki koldan biri boşsa fark kurulamaz; sessizce sayı uydurulmamalı."""
    yok = _sahte_cetvel(3)
    for w in yok:
        w["sezon"] = "1999_00"
    i = hh.devir_ikili(yok)
    assert i["devirli"] == i["devirsiz"] == 0
    assert i["kesiyor"] and i["fark"] == 0.0


def test_isaret_karnesi_HOLM_zincirini_dogru_uyguluyor(monkeypatch):
    """İki aday sınanınca eşik 0,05 değil 0,025'ten başlar — ve zincirlidir.

    Güçlü işaret düşük `p` alır ve 0,025'i geçer; gürültü işareti geçmez.
    Zincir kuralı da sınanır: sıradaki aday, önceki düştüyse geçemez.
    """
    rnd = random.Random(5)
    c = []
    for i in range(40):
        c.append({"sezon": "s", "hafta": i, "basamak": 1, "basamaklar": [
            {"tl": 2000.0, "kolon": 200, "sekil": "x", "banko": 7, "cift": 3,
             "uclu": 5, "p_hedef": 0.1 + i / 100.0, "kacak": 0, "tuttu": True,
             "odul": 0.0, "net": 0.0, "roi": 0.05 * i}]})

    def guclu(cet, referans_tl=2000.0):
        return [(b["basamaklar"][0]["p_hedef"], b["basamaklar"][0]["roi"])
                for b in cet]

    def gurultu(cet, referans_tl=2000.0):
        return [(rnd.random(), b["basamaklar"][0]["roi"]) for b in cet]

    monkeypatch.setattr(hh, "ISARETLER", {"guclu": guclu, "gurultu": gurultu})
    k = hh.isaret_karnesi(c, n=2000)
    assert k["aday"] == 2
    assert k["isaret"]["guclu"]["holm_esigi"] == pytest.approx(0.025)
    assert k["isaret"]["guclu"]["holm_gecti"]
    assert not k["isaret"]["gurultu"]["holm_gecti"]
    assert k["gecen"] == ["guclu"]


def test_isaret_karnesi_hicbiri_gecmezse_gecen_BOS():
    """Zincir ilk adayda kırılırsa ikincisi de düşer — `gecen` boş kalmalı."""
    rnd = random.Random(11)
    c = []
    for i in range(40):
        c.append({"sezon": "s", "hafta": i, "basamak": 1, "basamaklar": [
            {"tl": 2000.0, "kolon": 200, "sekil": "x", "banko": 7, "cift": 3,
             "uclu": 5, "p_hedef": rnd.random(), "kacak": 0, "tuttu": True,
             "odul": 0.0, "net": 0.0, "roi": rnd.random()}]})

    def gurultu(cet, referans_tl=2000.0):
        return [(rnd.random(), b["basamaklar"][0]["roi"]) for b in cet]

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(hh, "ISARETLER", {"a": gurultu, "b": gurultu})
    try:
        k = hh.isaret_karnesi(c, n=2000)
    finally:
        monkeypatch.undo()
    assert k["gecen"] == []
    assert all(not s["holm_gecti"] for s in k["isaret"].values())


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

def test_cetvel_gecersiz_garantide_HATA_verir():
    """Düzde garanti seviyesi seçilmez; sessizce yanlış ölçmez.

    Eski ad `test_cetvel_13_garantide_HATA_verir`'di ve gerekçesi *"13-
    garantinin kolon listesi satıcıdadır"*. Satıcı tablosu söküldü ama
    değişmez aynı kaldı: ölçülemeyen bir seviye istendiğinde sessizce
    yanlış sayı üretilmemeli.
    """
    with pytest.raises(ValueError, match="garanti seviyesi secilmez"):
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
    adimlar = hh.cephe(probs, garanti=15, en_cok_tl=5000.0)
    secili = adimlar[len(adimlar) // 2]
    _merdiven(probs, 15, secili.kolon, en_cok_tl=5000.0)
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
    assert k["temel"] == "sabit-16000"
    assert "lambda-LOO" in k["ozet"]
    # Duzde sabit butce her haftaya yetismiyor (odeyebilen en ucuz basamak
    # 10 TL ile 87.480 TL arasinda oynuyor). `kural_kiyasi` butun kurallari
    # ORTAK hafta kumesinde puanliyor; bekci esitlik degil ESLESME tutar.
    hafta_sayilari = {o["hafta"] for o in k["ozet"].values()}
    assert len(hafta_sayilari) == 1, f"kurallar farkli haftalarda: {k['ozet']}"
    assert hafta_sayilari.pop() > 0


@pytest.mark.slow
def test_E6_KAPANISI_hala_gecerli():
    """§E6'nın kapanışı: hiçbir kural sabit bütçeyi ayrıştırılabilir biçimde
    yenmiyor, ve merdivende yukarı çıkmak geri dönüş **oranını** açmıyor.

    Bekçi kasıtlı olarak dar: ölçümün değerlerini (fark, ROI, `rho`)
    dondurmaz — doktrin bunu yasaklıyor, sayılar `.claude/olcum_kutugu.json`da
    komutuyla durur. Tuttuğu tek şey **kapanışın kendisi**:

    1. **aynı parayı veren** eşleştirilmiş %95 aralıkların hepsi sıfırı keser;
    2. basamak geri dönüşünün kolon sayısıyla monoton bir eğilimi yoktur.

    Biri kırılırsa §E6 *"bütçe ekseni kapandı"* diyemez ve yeniden
    yazılmak zorundadır — tam olarak istenen davranış.

    ─── 1. madde neden "aynı parayı veren" diyor ─────────────────────────

    Bekçi eskiden bütün kuralları TEK sabit temele (bugün 16.000 TL) karşı
    ölçüyordu ve bu, kaplama ölçeğinde yeterliydi: ölçüm tavanı 5.000 TL idi
    ve bütün kuralları sabit bütçelerle aynı para bandına kelepçeliyordu.
    Düzde tavan 500.000 TL; λ bandının üstü haftada ~63.800 TL harcıyor, en
    pahalı sabit bütçenin (28.000) iki katından fazla. O yüzden tek temele
    karşı ölçüm artık iki soruyu karıştırıyor: *kural mı daha iyi seçiyor*
    ile *kural daha çok mu harcıyor*.

    Ölçüldü (11–12 haftalık dilim): `lambda-800000` tek temele karşı +0,543
    ROI [+0,107, +1,056] ile sıfırı kesmiyor; ama aynı parayı veren sabit
    kurala karşı +0,015 [+0,000, +0,045] ile kesiyor — aradaki farkın
    tamamı `sabit-65610` ile `sabit-16000` arasındaki **para** farkı. Yani
    açılan şey bütçe ekseni değil, kıyasın para eşleşmesiydi.

    Bekçi bu yüzden `fark_esit_para` sütununu tutar. Tek temele karşı bir
    açılma kalırsa hâlâ sınanır, ama yalnız **daha çok harcayarak** açılmış
    olmasına izin verilir: aynı ya da daha az parayla açan bir kural §E6'yı
    gerçekten kırar ve testi düşürür.

    Kesitin bir dilimidir (tam ölçüm ~20 dk); dilimde aralıklar daha geniş,
    yani bu bekçi kapanışı **kolay** doğrular ve ancak güçlü bir tersine
    dönüşte kırılır.
    """
    cet = hh.cetvel(hafta_siniri=12)
    assert len(cet) >= 10
    # Devir isareti gercek arsivden okunur ve kesitin TAMAMINI kapsamak
    # zorunda degil: sinyal yalniz devir bilgisi olan haftalarda var.
    # Kaplama olceginde cetvel daha kisaydi (olcum tavani 5.000 TL idi) ve
    # kapsama tesadufen tamdi. Bekcinin tuttugu sey sinyalin BOS OLMAMASI:
    # bos kalirsa ikinci aday sessizce dusar ve Holm boleni yalan olur.
    assert len(hh.devir_isareti(cet)) >= 3
    k = hh.kural_kiyasi(cet)
    ep = k["fark_esit_para"]
    assert len(ep) >= len(k["fark"]), "esit-para sutunu eksik kural birakti"
    acan = [ad for ad, f in ep.items() if not f["kesiyor"]]
    assert not acan, (
        f"butce ekseni ACILDI: {acan} AYNI PARAYLA sifiri kesmiyor — "
        "§E6 yeniden yazilmali")
    # Sabit kural kendi parasina karsi TAM SIFIR vermeli; vermezse esleme
    # kodu yanlistir ve yukaridaki kapanis bos yere gecmis olur.
    for ad, f in ep.items():
        if ad.startswith("sabit-"):
            assert f["ort_roi_farki"] == 0.0 and f["alt"] == f["ust"] == 0.0, \
                f"{ad} kendi butcesine karsi sifir vermedi: {f}"
    # Tek temele karsi bir acilma kaldiysa PARAYLA aciklanmak zorunda.
    temel_tl = k["ozet"][k["temel"]]["maliyet"]
    for ad, f in k["fark"].items():
        if f["kesiyor"]:
            continue
        assert k["ozet"][ad]["maliyet"] > temel_tl, (
            f"{ad} temeli AYNI ya da DAHA AZ parayla yeniyor "
            f"({k['ozet'][ad]['maliyet']:.0f} TL <= {temel_tl:.0f} TL) — "
            "§E6 gercekten kirildi, yeniden yazilmali")
    # Kuyruk: §E6'nin 5. maddesi "odul tek haftadan geliyor" diyor. Dilimde
    # bile en iyi 5 hafta basamaklarin cogunda yarıdan fazlasini tasimali.
    ky = hh.kuyruk_payi(cet)
    assert ky["basamak"] > 0
    assert ky["pay_en_cok"] > 0.5, (
        "odul dagilimi beklenenden DUZ — §E6'nin kuyruk gerekcesi yeniden "
        "olculmeli")
    kar = hh.basamak_karnesi(cet)
    rho = hh._spearman([x["kolon"] for x in kar], [x["roi"] for x in kar])
    assert abs(rho) < 0.7, (
        f"basamak ROI'si kolon sayisiyla egilim gosteriyor (rho={rho:+.3f}) — "
        "§E6'nin 'oran basamaktan bagimsiz' satiri yeniden olculmeli")
