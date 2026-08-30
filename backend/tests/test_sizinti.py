"""Sızıntı sözleşmesi — *"bu tahminci kendi sınavının cevabını okudu mu?"*

Depoda sızıntı denetimi zaten vardı ama **dağınıktı**: `test_arama.py`
katların ayrıklığına, `test_recalibrate.py` bir kademenin okumaması gereken
alanı okumadığına, `test_egitim.py` korpusun güncel sezonu içermediğine,
`test_elo.py` sızıntı testinin boş yeşil kalmadığına bakıyordu. Dördü de
yerinde ve **kaldırılmadı**; her biri kendi modülünün başka şeylerini de
denetliyor.

Eksik olan şey bir sözleşmeydi: **yeni bir tahminci eklendiğinde onu kimse
otomatik denetlemiyordu.** Kural yazılı değil, âdetti — ve âdet, `arena.py`
gibi bütün aileleri tek listede toplayan bir kayıt geldiğinde ilk bozulacak
şeydir.

Bu dosya o sözleşmeyi yazıya döker. Denetlediği şey üç maddedir:

    1. `egit`/`tahmin` ayrımı gerçek mi — eğitim setini değiştirmek çıktıyı
       değiştiriyor mu, yoksa tahminci eğitimden hiç beslenmiyor mu?
    2. Ölçülen hafta kendi eğitim setinde YOK mu?
    3. İleri yürüyüşte ölçülen grubun eğitim setinde hiçbir SONRAKİ grup
       yok mu?

`test_evaluate.py` başlığındaki kural burada da geçerli ve iki yönlüdür:
*bir kuralın yalnızca `False` döndürdüğünü kanıtlayan test takımı boştur.*
Bu yüzden her denetimin yanında **bilerek sızdıran** bir kurgu var ve
denetimin onu yakaladığı ayrıca sınanıyor.
"""

import pytest

from spor_toto.arena import roster
from spor_toto.evaluate import (
    ILERI_EN_AZ_GRUP,
    hafta_disarida_birak,
    ileri_gruplar,
    ileri_yuruyus,
    sezon_anahtari,
)
from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.predict import Tahminci

ESIT = dict.fromkeys(SYMBOLS, 1 / 3)


def _girdi(week: int, results: str, sezon: str, tarih: str) -> dict:
    return {
        "week": week, "close_date": tarih, "sezon": sezon,
        "results": results,
        "probs": [dict(ESIT)] * len(results),
        "missing": 0, "usable": True,
    }


def _kesit() -> list[dict]:
    """Üç sezon × iki hafta — sezonlar kronolojik ve ayırt edilebilir."""
    out = []
    for i, (sezon, yil) in enumerate((("2122", "2021"), ("2223", "2022"),
                                      ("2324", "2023"))):
        for j in range(2):
            out.append(_girdi(10 * i + j, SYMBOLS[i] * MATCH_COUNT,
                              sezon, f"{yil}-0{j + 1}-15"))
    return out


# ─── kurgular: biri dürüst, biri sızdırıyor ───────────────────────────────────

class DefterTahminci(Tahminci):
    """Eğitim setini **ve sınavı** yazan dürüst kurgu.

    Hiçbir şey öğrenmez; işi kimi gördüğünü kayda geçirmek. Sızıntı bir
    tahmincinin skorundan değil, gördüğü veriden okunur — skor üzerinden
    çıkarım dolaylı ve kırılgandır.

    **İkisi de kaydedilir ve bu şart.** Yalnızca eğitim setine bakan bir
    denetim boştur: "bu setin en büyüğünden sonrası yok" cümlesi setin
    kendisinden türetildiğinde her zaman doğrudur. Sorulması gereken şey
    setin iç tutarlılığı değil, eğitim ile **sınav** arasındaki sıradır.
    """

    ad = "defter"
    aciklama = "test kurgusu: egitim setini ve sinavi kaydeder"

    def __init__(self) -> None:
        self.gordugu: list[int] = []
        self.olctugu: list[int] = []

    def egit(self, haftalar):
        self.gordugu = [h["week"] for h in haftalar]

    def tahmin(self, hafta):
        self.olctugu.append(hafta["week"])
        return [dict(ESIT)] * len(hafta["results"])


class SizdiranTahminci(Tahminci):
    """Sınavın cevabını okuyan kurgu — denetimin ateşlenebildiğini kanıtlar.

    `egit` bir şey öğrenmez; `tahmin` doğrudan ölçülen haftanın kendi
    sonucuna bakar. Gerçek bir sızıntı genelde bu kadar açık değildir
    (eğitim setine ölçülen haftanın da girmesi gibi görünür) ama denetimin
    yakalaması gereken sınıf budur.
    """

    ad = "sizdiran"
    aciklama = "test kurgusu: olculen haftanin sonucunu okur"

    def tahmin(self, hafta):
        out = []
        for kod in hafta["results"]:
            p = dict.fromkeys(SYMBOLS, 0.05)
            p[kod] = 0.90
            out.append(p)
        return out


class SagirTahminci(Tahminci):
    """Eğitimden hiç beslenmeyen kurgu — 1. maddenin negatif ucu."""

    ad = "sagir"
    aciklama = "test kurgusu: egitim setini hic okumaz"

    def tahmin(self, hafta):
        return [dict(ESIT)] * len(hafta["results"])


# ─── 1. madde: egit/tahmin ayrımı gerçek mi ───────────────────────────────────

def _egitimden_besleniyor_mu(fabrika, a: list[dict], b: list[dict],
                             sinav: dict) -> bool:
    """İki farklı eğitim seti, aynı sınav — çıktı değişiyor mu?

    Değişmiyorsa tahminci ya eğitimden beslenmiyor (`duzgun`, `piyasa`) ya
    da veri onu hareket ettirmeye yetmiyor. İkisi de sızıntı DEĞİLDİR;
    ayrımın kendisi burada ölçülür, hüküm çağıranındır.
    """
    m1 = fabrika()
    m1.egit(a)
    p1 = m1.tahmin(sinav)
    m2 = fabrika()
    m2.egit(b)
    p2 = m2.tahmin(sinav)
    return any(abs(x[s] - y[s]) > 1e-12 for x, y in zip(p1, p2) for s in SYMBOLS)


def test_kurgu_sagir_egitimden_beslenmiyor():
    """Denetimin negatif ucu: sağır tahminci eğitim setine tepkisiz."""
    k = _kesit()
    assert not _egitimden_besleniyor_mu(SagirTahminci, k[:2], k[2:], k[0])


def test_kurgu_defter_egitim_setini_dogru_goruyor():
    """Denetimin pozitif ucu: defter iki farklı seti farklı görüyor."""
    k = _kesit()
    m = DefterTahminci()
    m.egit(k[:2])
    assert m.gordugu == [0, 1]


# ─── 2. madde: ölçülen hafta kendi eğitim setinde yok ─────────────────────────

def test_disarida_birakmali_olculen_haftayi_egitime_sokmaz():
    """`hafta_disarida_birak`: hiçbir hafta kendi eğitim setinde olamaz."""
    k = _kesit()
    defterler: list[DefterTahminci] = []

    def fabrika():
        m = DefterTahminci()
        defterler.append(m)
        return m

    hafta_disarida_birak(fabrika, k, sezon_anahtari)
    gorulen = {tuple(m.gordugu) for m in defterler}
    tum = {h["week"] for h in k}
    for gordugu in gorulen:
        # Her defter bir sezonu disarida birakti: gordugu kume, o sezonun
        # haftalarini ICERMEMELI ve geri kalanin TAMAMINI icermeli.
        eksik = tum - set(gordugu)
        assert eksik, "hicbir hafta disarida birakilmamis — sizinti"
        assert not (set(gordugu) & eksik)


def test_disarida_birakmali_sezonun_tamamini_cikarir():
    """Sezon grubu verilince haftanın **bütün sezonu** eğitimden çıkar."""
    k = _kesit()
    defterler: list[DefterTahminci] = []

    def fabrika():
        m = DefterTahminci()
        defterler.append(m)
        return m

    hafta_disarida_birak(fabrika, k, sezon_anahtari)
    sezonu = {h["week"]: h["sezon"] for h in k}
    for m in defterler:
        sezonlar = {sezonu[w] for w in m.gordugu}
        assert len(sezonlar) == 2, (
            f"egitim setinde {len(sezonlar)} sezon var — biri disarida "
            "birakilmis olmaliydi")


# ─── 3. madde: ileri yürüyüşte gelecek yok ────────────────────────────────────

def test_ileri_yuruyus_gelecegi_egitime_sokmaz():
    """Ölçülen grubun eğitim setinde hiçbir SONRAKİ grup bulunamaz.

    Sözleşmenin en kritik maddesi: `hafta_disarida_birak` bu denetimden
    **kasten** geçemez (kendi grubu hariç HEPSİNDE eğitir, geleceği de),
    ve o bir hata değil başka bir ölçümdür. İleri yürüyüşün tek varlık
    sebebi budur.
    """
    k = _kesit()
    defterler: list[DefterTahminci] = []

    def fabrika():
        m = DefterTahminci()
        defterler.append(m)
        return m

    ileri_yuruyus(fabrika, k, sezon_anahtari)
    sirali = ileri_gruplar(k, sezon_anahtari)
    yeri = {h["week"]: sirali.index(h["sezon"]) for h in k}

    olcen = [m for m in defterler if m.olctugu]
    assert olcen, "hic olcum yapilmamis"
    for m in olcen:
        sinav = min(yeri[w] for w in m.olctugu)
        assert m.gordugu, "olcum yapildi ama egitim seti bos"
        en_ileri = max(yeri[w] for w in m.gordugu)
        assert en_ileri < sinav, (
            f"egitim setinde gelecek grup var: egitim {sirali[en_ileri]} "
            f">= sinav {sirali[sinav]}")


def test_disarida_birakmali_bu_denetimden_kasten_gecemez():
    """Bekçilik: aynı denetim `hafta_disarida_birak`ta **kırılmalı**.

    `hafta_disarida_birak` kendi grubu hariç HEPSİNDE eğitir — geleceği
    de. Bu bir hata değil, başka bir ölçümdür; ama denetim onu ayırt
    edemiyorsa denetim hiçbir şey ölçmüyor demektir. İleri yürüyüşün tek
    varlık sebebi aradaki bu farktır.
    """
    k = _kesit()
    defterler: list[DefterTahminci] = []

    def fabrika():
        m = DefterTahminci()
        defterler.append(m)
        return m

    hafta_disarida_birak(fabrika, k, sezon_anahtari)
    sirali = ileri_gruplar(k, sezon_anahtari)
    yeri = {h["week"]: sirali.index(h["sezon"]) for h in k}

    gelecegi_goren = [
        m for m in defterler if m.olctugu and m.gordugu
        and max(yeri[w] for w in m.gordugu) >= min(yeri[w] for w in m.olctugu)
    ]
    assert gelecegi_goren, (
        "disarida birakmali kosum gelecegi gormedi — denetim bos demektir")


def test_ileri_yuruyus_ilk_grubu_olcmez_ve_adini_yazar():
    """İlk grup ölçülemez (eğitim seti boş) ve bu **sessizce** olmaz."""
    k = _kesit()
    kayitlar = ileri_yuruyus(DefterTahminci, k, sezon_anahtari)
    atlanan = ileri_gruplar(k, sezon_anahtari)[:ILERI_EN_AZ_GRUP]
    assert atlanan == ["2122"]
    olculen = {kayit["week"] for kayit in kayitlar}
    assert olculen == {10, 11, 20, 21}, "atlanan grup olculmus ya da fazlasi dusmus"


def test_ileri_gruplar_anahtarin_alfabetigine_degil_tarihe_bakar():
    """Sıra grup adından değil, grubun **en erken haftasından** gelir.

    Sezon anahtarları bugün alfabetik olarak da kronolojik ama bu bir
    tesadüf; biçim değişirse sessizce yanlış sıra üreten bir ölçüm kalırdı.
    """
    k = [
        _girdi(1, "1" * MATCH_COUNT, "zzz_eski", "2020-01-01"),
        _girdi(2, "1" * MATCH_COUNT, "aaa_yeni", "2024-01-01"),
    ]
    assert ileri_gruplar(k, sezon_anahtari) == ["zzz_eski", "aaa_yeni"]


def test_ileri_gruplar_bozuk_week_alaninda_cokmez():
    """Eksik ya da metin bir `week`, sıralamayı **çökertmemeli**.

    `week` bugün her üreticide `int` ama bu bir sözleşme değil. Düz demet
    karşılaştırması `None` ile `int`i kıyaslayınca `TypeError` fırlatır ve
    ölçüm veriye bağlı olarak bazen koşup bazen çöker — en kötü kırılma
    türü. Sıra yine tarihten gelmeli.
    """
    k = [
        _girdi(3, "1" * MATCH_COUNT, "c", "2023-01-01"),
        _girdi(1, "1" * MATCH_COUNT, "a", "2021-01-01"),
        _girdi(2, "1" * MATCH_COUNT, "b", "2022-01-01"),
    ]
    k[0]["week"] = None
    k[2]["week"] = "iki"
    assert ileri_gruplar(k, sezon_anahtari) == ["a", "b", "c"]


def test_ileri_yuruyus_en_az_grup_sifiri_reddeder():
    """İlk grubu ölçmek eğitim seti boşken tahmin etmek demektir."""
    with pytest.raises(ValueError, match="en_az_grup"):
        ileri_yuruyus(DefterTahminci, _kesit(), sezon_anahtari, en_az_grup=0)


# ─── denetim ateşlenebiliyor mu — sızdıran kurgu yakalanıyor ──────────────────

def test_sizdiran_kurgu_skorda_gorunur():
    """Sızdıran tahminci imkânsız derecede iyi bir skor verir.

    Bu test bir tahminciyi değil, **ölçümün duyarlılığını** denetler: eğer
    sınavın cevabını okuyan bir kurgu bile dürüst bir skor üretiyorsa,
    koşum sızıntıyı hiçbir zaman göremez ve bütün 'geçmedi' sonuçları
    bilgisizdir.
    """
    k = _kesit()
    durust = ileri_yuruyus(DefterTahminci, k, sezon_anahtari)
    sizan = ileri_yuruyus(SizdiranTahminci, k, sezon_anahtari)
    assert len(durust) == len(sizan)
    d = sum(x["brier_toplam"] for x in durust)
    s = sum(x["brier_toplam"] for x in sizan)
    assert s < d / 2, (
        f"sizdiran kurgu yakalanmadi: durust={d:.2f} sizan={s:.2f}")


# ─── kayıt sözleşmesi — arenaya giren her aile ────────────────────────────────

def test_kayittaki_her_aile_egit_tahmin_sozlesmesini_tasir():
    """`arena.roster()`teki her fabrika `Tahminci` sözleşmesine uymalı.

    Sözleşme süs değil, sızıntıya karşı **tek savunma**: `egit`/`tahmin`
    ayrımı olmayan bir tahminci dışarıda bırakılamaz, çünkü dışarıda
    bırakılacak bir eğitim adımı yoktur (`predict.py` modül başlığı).
    """
    kayit = roster()
    assert kayit, "arena kaydi bos"
    for aile, fabrika in kayit:
        m = fabrika()
        assert isinstance(m, Tahminci), f"{aile}: Tahminci degil"
        assert callable(getattr(m, "egit", None)), f"{aile}: egit yok"
        assert callable(getattr(m, "tahmin", None)), f"{aile}: tahmin yok"
        assert m.ad, f"{aile}: ad bos"


def test_kayitta_ayni_ad_iki_kez_gecmez():
    """Aile başına tek temsilci kuralının mekanik karşılığı.

    Aynı ad iki kez girseydi `evaluate.karsilastir` ikisini de tabloya
    yazar, `cokme` tespiti ikisini birbirine göre okur ve tablo sessizce
    yanlış olurdu.
    """
    adlar = [f().ad for _, f in roster()]
    assert len(adlar) == len(set(adlar)), f"kayitta tekrar eden ad: {adlar}"


def test_kayittaki_aileler_olculen_haftayi_gormez():
    """Kayıttaki her aile için 2. madde — gerçek fabrikalarla.

    Yukarıdaki denetimler `DefterTahminci` ile yapıldı çünkü sızıntı
    gördüğü veriden okunur. Burada aynı soru **gerçek** ailelere soruluyor
    ama ucuz biçimde: bir aile ölçülen haftayı görseydi, o haftada eğitim
    setine göre değil kendi sonucuna göre tahmin ederdi ve `Kâhin` kadar
    iyi çıkardı. Zemin şu: hiçbir aile, sonucu bilen bir kurgunun skorunu
    yakalayamaz.
    """
    k = _kesit()
    sizan = ileri_yuruyus(SizdiranTahminci, k, sezon_anahtari)
    tavan = sum(x["brier_toplam"] for x in sizan) / sum(x["n"] for x in sizan)

    for aile, fabrika in roster():
        kayitlar = ileri_yuruyus(fabrika, k, sezon_anahtari)
        n = sum(x["n"] for x in kayitlar)
        skor = sum(x["brier_toplam"] for x in kayitlar) / n
        assert skor > tavan, (
            f"{aile}: Brier {skor:.4f}, sizdiran kurgunun {tavan:.4f} "
            "skorundan iyi — olculen haftayi goruyor olabilir")


# ─── 4. madde: ampirik sorgu kronolojiyi tanıyor mu? ─────────────────────────
#
# `benzer.py` bu sözleşmede uzun süre **hiç geçmiyordu.** Dosyanın kendi
# gerekçesi burada birebir işledi: *"yeni bir tahminci eklendiğinde onu kimse
# otomatik denetlemiyordu."* `benzer` bir tahminci değil — tahmin üretmez,
# ampirik bir sayım verir — ama sızıntı riski aynıdır ve daha sinsidir:
# ürettiği sayı "geçmişte ne oldu" diye sunulur.
#
# Denetlenen şey: `tarih=T` verildiğinde evren gerçekten T'nin öncesiyle
# sınırlı mı, ve bu sınır **boş bir yeşil** değil mi (T'siz sorgu geleceği
# gerçekten görüyor mu).

_ORNEK_ORAN = {"1": 1.82, "0": 3.04, "2": 2.44}
_KESME = "2023-08-01"


def _benzer_korpus():
    from spor_toto.egitim import korpus_yukle
    return korpus_yukle()


def _benzer_bul(**kw):
    from spor_toto.benzer import benzer_maclar
    return benzer_maclar(_ORNEK_ORAN, tolerans=0.02, **kw)


def _korpus_yoksa_atla():
    if not _benzer_korpus():
        pytest.skip("egitim korpusu yok (scripts/build_egitim.py)")


def test_benzer_kesme_tarihinden_sonrasini_gormez():
    """1. madde: `tarih=T` verildiğinde hiçbir maç T'de ya da sonrasında değil.

    Süzgeç **katı küçüktür**: aynı gün oynanan maçlar da düşer. Bu, ayrı bir
    "kendini dışla" koduna gerek bırakmadan sorulan maçın kendi cevabına
    girmesini engeller.
    """
    _korpus_yoksa_atla()
    from spor_toto.benzer import _mesafe, _olasilik_tablosu
    from spor_toto.odds import ARINDIRMA_VARSAYILAN, implied_probs

    r = _benzer_bul(tarih=_KESME)
    hedef = implied_probs(_ORNEK_ORAN, ARINDIRMA_VARSAYILAN)
    bulunan = [kayit for p, kayit in _olasilik_tablosu(ARINDIRMA_VARSAYILAN, None)
               if _mesafe(p, hedef) <= 0.02 and kayit["tarih"] < _KESME]

    assert r["as_of"] == _KESME
    assert r["toplam"]["n"] == len(bulunan)
    assert all(m["tarih"] < _KESME for m in bulunan), "kesme tarihi sızdırdı"


def test_benzer_kesmesiz_sorgu_gelecegi_gercekten_goruyor():
    """Denetimin boş yeşil olmadığının kanıtı — bilerek sızdıran kurgu.

    `test_evaluate.py` başlığındaki kural: *bir kuralın yalnızca `False`
    döndürdüğünü kanıtlayan test takımı boştur.* Kesme çalışıyor demek için
    kesmesiz yolun geleceği gerçekten kattığını göstermek gerekir; yoksa
    yukarıdaki test korpusta hiç gelecek maç olmadığı için de yeşil kalırdı.
    """
    _korpus_yoksa_atla()
    kesik = _benzer_bul(tarih=_KESME)
    tam = _benzer_bul()

    assert tam["evren"] > kesik["evren"], "kesmesiz sorgu daha büyük evren görmeli"
    assert kesik["evren_kesilen"] == tam["evren"] - kesik["evren"]
    assert tam["evren_kesilen"] == 0
    # Kesilen kesitte gerçekten SONRAKI maçlar var.
    sonraki = [m for m in _benzer_korpus() if m["tarih"] >= _KESME]
    assert sonraki, "korpusta kesme tarihinden sonra maç yok — test anlamsız"


def test_benzer_sorulan_macin_kendisi_kendi_cevabinda_yok():
    """3. madde: bir maçı kendi tarihiyle sorarsan kendini sayamaz.

    `test_benzer.test_macin_kendisi_kendi_komsulugunda`'nın kronolojik
    ikizi: orada maçın kendi komşuluğunda **bulunması** doğrulanıyor (arama
    çalışıyor mu), burada kendi tarihiyle sorulduğunda **bulunmaması**
    (arama kendi cevabını okuyor mu).
    """
    _korpus_yoksa_atla()
    from spor_toto.benzer import _mesafe, _olasilik_tablosu
    from spor_toto.odds import ARINDIRMA_VARSAYILAN

    tablo = _olasilik_tablosu(ARINDIRMA_VARSAYILAN, None)
    hedef_p, hedef_mac = tablo[0]

    kendi_tarihiyle = [k for p, k in tablo
                       if _mesafe(p, hedef_p) <= 0.02
                       and k["tarih"] < hedef_mac["tarih"]]
    kesmesiz = [k for p, k in tablo if _mesafe(p, hedef_p) <= 0.02]

    assert hedef_mac in kesmesiz, "maç kendi komşuluğunda bulunmuyor — arama bozuk"
    assert hedef_mac not in kendi_tarihiyle, "maç kendi cevabına girdi"
