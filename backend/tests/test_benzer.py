"""Benzer maç arama ve marj arındırma yöntemleri.

Bu dosyanın asıl işi bir tasarım kararını çivilemek: eşleme **olasılık
uzayında** yapılır, oran uzayında değil. Sebep ölçülmüş bir olgudur ve
`test_oran_uzayinda_arama_bos_doner` onu regresyona bağlar.
"""

import pytest

from spor_toto.benzer import (
    AZ_ORNEK,
    CIZGILER,
    EN_COK_LISTE,
    EN_COK_TOLERANS,
    _mesafe,
    _olasilik_tablosu,
    benzer_mac_listesi,
    benzer_maclar,
)
from spor_toto.egitim import korpus_yukle
from spor_toto.odds import ARINDIRMA_YONTEMLERI, SEMBOLLER, implied_probs, margin

KORPUS = korpus_yukle()
ORNEK = {"1": 1.82, "0": 3.04, "2": 2.44}

pytestmark = pytest.mark.skipif(
    not KORPUS, reason="egitim korpusu yok (scripts/build_egitim.py)")


# ─── marj arındırma ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("yontem", ARINDIRMA_YONTEMLERI)
def test_arindirma_bire_toplar(yontem):
    p = implied_probs(ORNEK, yontem)
    assert len(p) == 3
    assert sum(p.values()) == pytest.approx(1.0, abs=1e-12)
    assert all(0.0 < v < 1.0 for v in p.values())


@pytest.mark.parametrize("yontem", ARINDIRMA_YONTEMLERI)
def test_marjsiz_oranda_uc_yontem_ayni(yontem):
    """Marj sıfırsa arındırılacak bir şey yoktur; üçü de çakışmalı."""
    marjsiz = {"1": 2.0, "0": 4.0, "2": 4.0}
    assert margin(marjsiz) == pytest.approx(0.0, abs=1e-12)
    p = implied_probs(marjsiz, yontem)
    for s, beklenen in (("1", 0.5), ("0", 0.25), ("2", 0.25)):
        assert p[s] == pytest.approx(beklenen, abs=1e-9)


def test_yuksek_marjda_favori_orantilidan_buyuk():
    """Yanlılığın yönü: orantısal yöntem favoriyi eksik fiyatlar.

    Ölçüldü (23.085 maç): piyasanın %70–80 dediği maçlar gerçekte %79,2
    geliyor. Shin ve güç yöntemleri favoriye daha çok pay verir; bu testin
    kırılması, düzeltmenin yönünün ters çevrildiği anlamına gelir.
    """
    o = implied_probs(ORNEK, "orantili")
    for yontem in ("guc", "shin"):
        p = implied_probs(ORNEK, yontem)
        assert p["1"] > o["1"], yontem
    # Shin, güç yönteminden daha yumuşak düzeltir.
    assert implied_probs(ORNEK, "guc")["1"] > implied_probs(ORNEK, "shin")["1"]


def test_bilinmeyen_yontem_hata_verir():
    with pytest.raises(ValueError, match="bilinmeyen"):
        implied_probs(ORNEK, "kelly")


# ─── eşlemenin olasılık uzayında olması ───────────────────────────────────────

def test_oran_uzayinda_arama_bos_doner():
    """`benzer.py`'nin varlık sebebi: oran uzayında bu maç korpusta YOK.

    1.82/3.04/2.44 %28,8 marj taşır; korpus ~%7 marjlıdır. Aynı gerçek
    olasılık farklı marjda başka oran verir, o yüzden ±%10'luk oran
    komşuluğunda bile tek maç çıkmaz — oysa olasılık uzayında yüzlerce var.
    """
    yakin = [r for r in KORPUS
             if all(abs(r["oranlar"][s] - ORNEK[s]) <= 0.10 * ORNEK[s]
                    for s in SEMBOLLER)]
    assert yakin == []
    assert benzer_maclar(ORNEK, tolerans=0.02)["toplam"]["n"] > 100


def test_macin_kendisi_kendi_komsulugunda():
    """Bir korpus maçının kendi oranıyla arandığında kendisi bulunmalı."""
    hedef = KORPUS[0]["oranlar"]
    r = benzer_maclar(hedef, tolerans=0.0)
    assert r["toplam"]["n"] >= 1
    assert _mesafe(implied_probs(hedef), implied_probs(hedef)) == 0.0


# ─── uyarlanan yarıçap ────────────────────────────────────────────────────────

def test_tolerans_buyudukce_orneklem_artar():
    n = [benzer_maclar(ORNEK, tolerans=t)["toplam"]["n"]
         for t in (0.01, 0.02, 0.03, 0.05)]
    assert n == sorted(n)
    assert n[0] < n[-1]


def test_uyarlanan_yaricap_hedefe_ulasir_ve_kendini_yazar():
    r = benzer_maclar(ORNEK, en_az=200)
    assert r["tolerans_uyarlandi"] is True
    assert r["toplam"]["n"] >= 200
    assert r["tolerans"] <= EN_COK_TOLERANS
    # Genişlemiş bir arama kendini gizlememeli.
    assert r["tolerans_genisledi"] is True


def test_ulasilamayan_orneklem_bayrak_birakir():
    """Tavana dayanıp hedefe ulaşamamak sessiz kalmamalı."""
    r = benzer_maclar(ORNEK, en_az=10 ** 6)
    assert r["tolerans"] == pytest.approx(EN_COK_TOLERANS)
    assert r["tolerans_tavana_dayandi"] is True
    assert any("tavana" in u for u in r["uyarilar"])


def test_verilen_tolerans_uyarlanmaz():
    r = benzer_maclar(ORNEK, tolerans=0.01, en_az=10 ** 6)
    assert r["tolerans"] == 0.01
    assert r["tolerans_uyarlandi"] is False


# ─── örneklem dürüstlüğü ──────────────────────────────────────────────────────

def test_her_yuzde_guven_araligiyla_gelir():
    r = benzer_maclar(ORNEK, tolerans=0.02)
    for s in SEMBOLLER:
        h = r["toplam"]["semboller"][s]
        assert h["ga_alt"] <= h["oran"] <= h["ga_ust"]
        assert 0.0 <= h["ga_alt"] and h["ga_ust"] <= 1.0
        assert h["piyasa_ga_icinde"] == (h["ga_alt"] <= h["piyasa"] <= h["ga_ust"])


def test_ince_dilim_sayi_vermez():
    """`AZ_ORNEK` altındaki dilim 'yeterli' bayrağını taşımamalı."""
    r = benzer_maclar(ORNEK, tolerans=0.02)
    dilimler = r["dilimler"]["lig"]
    assert dilimler, "en az bir lig dilimi bekleniyor"
    for d in dilimler:
        assert d["karne"]["yeterli"] == (d["karne"]["n"] >= AZ_ORNEK)
    assert any(not d["karne"]["yeterli"] for d in dilimler), (
        "22 ligde ince dilim olmaması beklenmez")


def test_dilimlerin_toplami_bulunani_verir():
    r = benzer_maclar(ORNEK, tolerans=0.02)
    for ad in ("lig", "sezon"):
        assert sum(d["karne"]["n"] for d in r["dilimler"][ad]) == r["toplam"]["n"]


def test_yuksek_marj_uyarisi_basilir():
    assert any("marj" in u for u in benzer_maclar(ORNEK, tolerans=0.02)["uyarilar"])


def test_filtre_evreni_daraltir():
    tum = benzer_maclar(ORNEK, tolerans=0.05)
    t1 = benzer_maclar(ORNEK, tolerans=0.05, lig="T1")
    assert t1["evren"] < tum["evren"]
    assert t1["toplam"]["n"] < tum["toplam"]["n"]
    assert all(d["deger"] == "T1" for d in t1["dilimler"]["lig"])


def test_gecersiz_oran_reddedilir():
    with pytest.raises(ValueError):
        benzer_maclar({"1": 1.0, "0": 3.0, "2": 3.0})


# ─── girdi doğrulama ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("bozuk", [float("inf"), float("nan"), float("-inf")])
def test_sonlu_olmayan_oran_adiyla_reddedilir(bozuk):
    """`inf` eskiden **kabul ediliyordu** — bu testin asıl sebebi o.

    `inf <= 1.0` yanlıştır, yani eski kapıdan geçerdi; `implied_probs` ona
    `0.0` olasılık verir ve üç anahtar döndüğü için `len(hedef) != 3`
    kontrolü de yakalamazdı. Sorgu koşar, bir sembolü olmayan hedef
    vektörle korpusu tarar ve çıkan sayı bir cevap gibi görünürdü.

    `nan` yakalanıyordu ama mesajı yanlış yeri gösteriyordu ("üç sembolün
    de oranı gerekli" — kullanıcı üçünü de vermişken).
    """
    with pytest.raises(ValueError, match="sonlu"):
        benzer_maclar({"1": bozuk, "0": 3.04, "2": 2.44})


def test_tavani_asan_tolerans_reddedilir():
    """Otomatik yolun durduğu yerde elle yol da durmalı.

    `EN_COK_TOLERANS` uyarlanan aramanın tavanı ve gerekçesi sabitin kendi
    yorumunda yazılı: *"Ötesi 'benzer maç' olmaktan çıkar."* Elle verilen
    tolerans bu tavanı tanımıyordu; `tolerans=0.9` bütün korpusu "benzer"
    sayardı.
    """
    with pytest.raises(ValueError, match="en çok"):
        benzer_maclar(ORNEK, tolerans=0.50)


def test_tavanin_kendisi_kabul_edilir():
    """Sınır **dahil** — `test_tolerans_buyudukce_orneklem_artar` 0,05 kullanıyor."""
    r = benzer_maclar(ORNEK, tolerans=EN_COK_TOLERANS)
    assert r["tolerans"] == EN_COK_TOLERANS


@pytest.mark.parametrize("bozuk", [-0.01, float("nan")])
def test_gecersiz_tolerans_reddedilir(bozuk):
    with pytest.raises(ValueError):
        benzer_maclar(ORNEK, tolerans=bozuk)


@pytest.mark.parametrize("bozuk", [0, -5])
def test_gecersiz_en_az_reddedilir(bozuk):
    with pytest.raises(ValueError, match="en_az"):
        benzer_maclar(ORNEK, en_az=bozuk)


# ─── mesafe kalitesi ──────────────────────────────────────────────────────────

def test_mesafe_ozeti_yaricapin_icinde_ve_sirali():
    r = benzer_maclar(ORNEK, tolerans=0.02)
    m = r["mesafe"]
    assert m["en_yakin"] <= m["ortanca"] <= m["en_uzak"]
    assert m["en_yakin"] <= m["ortalama"] <= m["en_uzak"]
    assert 0.0 <= m["en_yakin"]
    assert m["en_uzak"] <= 0.02


def test_bos_sonucta_mesafe_yok():
    """Sayı yoksa mesafe de yok — boş kümede 0.0 basmak yanlış olurdu."""
    r = benzer_maclar({"1": 1.01, "0": 1000.0, "2": 1000.0}, tolerans=0.0)
    assert r["toplam"]["n"] == 0
    assert r["mesafe"] is None


def test_genisleyen_arama_ortancasini_tavana_dogru_iter():
    """Mesafe bloğunun varlık sebebi: `tolerans_genisledi` bir boolean.

    Genişlemiş bir arama "benzer maç buldum" der ama örneklemi sınırdan
    toplamış olabilir. Ortanca mesafe bunu gösteren tek sayıdır.
    """
    dar = benzer_maclar(ORNEK, tolerans=0.02)
    genis = benzer_maclar(ORNEK, tolerans=EN_COK_TOLERANS)
    assert genis["mesafe"]["ortanca"] > dar["mesafe"]["ortanca"]
    # En yakın maç değişmez — genişleyen şey kümenin ucu, çekirdeği değil.
    assert genis["mesafe"]["en_yakin"] == dar["mesafe"]["en_yakin"]


# ─── regresyon: ölçülen sayılar ───────────────────────────────────────────────

def test_olculen_sayilar_korunur():
    """Belgelere yazılan sayılar korpus değişmedikçe sabit kalmalı.

    Yöntem **açıkça** verilir: bu sayılar `orantili` ölçekte ölçüldü ve
    belgede o etiketle duruyor. Varsayılan değiştiğinde (2026-08'de `shin`
    oldu) sabitlenmiş sayı sessizce başka bir şeyi ölçmeye başlamamalı.
    """
    # 2026-09-12 korpus daraltmasi (22 -> 17 lig): 710 -> 426.
    # Onceki dagilim {"1": 293, "0": 184, "2": 233}.
    r = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    assert r["toplam"]["n"] == 426
    sayilar = {s: r["toplam"]["semboller"][s]["adet"] for s in SEMBOLLER}
    assert sayilar == {"1": 180, "0": 111, "2": 135}


def test_varsayilan_yontem_kendi_sayilarini_uretir():
    """Bugünün varsayılanı (`shin`) — aynı oran, farklı ölçek, farklı komşuluk.

    Aynı yarıçap Shin ölçeğinde daha az maç buluyor: yüksek marjlı hedef
    oran (%28,8) Shin'de favoriye daha çok pay verdiği için korpusun düşük
    marjlı maçlarından uzaklaşıyor.
    """
    r = benzer_maclar(ORNEK, tolerans=0.02)
    assert r["arindirma"] == "shin"
    assert r["toplam"]["n"] == 151      # korpus daraltmasi: 241 -> 151
    assert sum(r["toplam"]["semboller"][s]["adet"] for s in SEMBOLLER) == 151


# ─── /api/benzer ──────────────────────────────────────────────────────────────

@pytest.fixture()
def istemci():
    flask = pytest.importorskip("flask")  # noqa: F841
    from web_app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_api_govdesi_n_ve_ga_tasir(istemci):
    """Uçtan çıkan hiçbir yüzde n ve güven aralığı olmadan gitmemeli."""
    g = istemci.get(
        "/api/benzer?oran=1.82,3.04,2.44&tolerans=0.02&arindirma=orantili"
    ).get_json()
    assert g["toplam"]["n"] == 426      # korpus daraltmasi: 710 -> 426
    for s in SEMBOLLER:
        h = g["toplam"]["semboller"][s]
        assert {"adet", "oran", "ga_alt", "ga_ust", "piyasa",
                "piyasa_ga_icinde"} <= set(h)
        assert h["ga_alt"] <= h["oran"] <= h["ga_ust"]


@pytest.mark.parametrize("sorgu", [
    "", "?oran=abc", "?oran=1.82,3.04", "?oran=1.0,3.0,3.0",
    "?oran=1.82,3.04,2.44&arindirma=kelly",
    # Okunan ama sinir disi degerler. Bunlar eskiden **kirpiliyordu**:
    # `tolerans=0.9` sessizce 1.0 olup butun korpusu "benzer" sayiyor,
    # `en_az=0` sessizce 1 oluyordu. Istek reddedilmiyor, baska bir
    # sorguya cevriliyordu.
    "?oran=1.82,3.04,2.44&tolerans=0.9",
    "?oran=1.82,3.04,2.44&tolerans=-0.1",
    "?oran=1.82,3.04,2.44&en_az=0",
])
def test_api_bozuk_girdi_400_verir(istemci, sorgu):
    assert istemci.get("/api/benzer" + sorgu).status_code == 400


@pytest.mark.parametrize("sorgu", [
    "&arindirma=shin", "&lig=T1", "&sezon=2425", "&en_az=abc", "&tolerans=bozuk",
])
def test_api_gecerli_ve_bozuk_ek_parametreler_cokmez(istemci, sorgu):
    r = istemci.get("/api/benzer?oran=1.82,3.04,2.44" + sorgu)
    assert r.status_code == 200
    assert r.get_json()["toplam"]["n"] >= 0


# ─── çizgi ekseni (açılış ↔ kapanış) ──────────────────────────────────────────

def test_kapanis_varsayilani_BUGUNKU_cevabi_DEGISTIRMEZ():
    """Çizgi ekseni eklendi diye varsayılan yol kımıldamamalı.

    `cizgi="kapanis"` satırın `oranlar` alanını okur, `kapanis` alanını
    DEĞİL. İkisi aynı fiyattır (`oran_kaynak` her satırda `AvgC`) ama
    `kapanis`, `acilis` ile birlikte düşer — `egitim._cizgi_uclusu` çifti
    "ya tam ya yok" diye taşır. `kapanis` okunsaydı varsayılan evren iki
    satır daralır ve eksen, kimse istemeden eski sayıları oynatırdı.

    Sabitler `test_olculen_sayilar_korunur`unkilerle aynı; burada
    **çizgi açıkça verilerek** bir kez daha sınanıyor.
    """
    varsayilan = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    acikca = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili",
                           cizgi="kapanis")
    assert varsayilan["toplam"]["n"] == acikca["toplam"]["n"] == 426
    assert varsayilan["evren"] == acikca["evren"] == len(KORPUS)
    assert varsayilan["cizgi"] == "kapanis"


def test_acilis_ve_kapanis_EVRENI_tam_iki_satir_ayrisir():
    """**Bir sayının değil, bir YORUMUN bekçisi.**

    Arayüz ve belge şunu söylüyor: açılış ile kapanış karneleri arasındaki
    fark *fiyattan* gelir. Bu cümle ancak iki evren neredeyse aynıysa
    doğrudur — evrenler ciddi biçimde ayrışsaydı fark, fiyat farkı mı
    örneklem farkı mı, ayırt edilemezdi ve o cümle sessizce yanlış olurdu.

    Ölçülen: kapanış 23.085, açılış 23.083 — tam 2 satır. Kesin sayı
    buraya YAZILMAZ (korpus boyutunun künyesi kütükte, bekçisi
    `test_egitim.py::test_korpus_boyutu_RAPORLA_ve_KUTUKLE_ayni`); burada
    tutulan şey **farkın kendisi**.
    """
    kapanis = len(_olasilik_tablosu("orantili", None, "kapanis"))
    acilis = len(_olasilik_tablosu("orantili", None, "acilis"))
    assert kapanis - acilis == 2, (
        f"evren farki {kapanis - acilis} satir. Iki cizginin karne farki "
        f"artik fiyata atfedilemez — belgedeki cumle duzeltilmeli."
    )


def test_acilis_cizgisi_FARKLI_karne_uretir():
    """`cizgi` gerçekten bağlanmış mı — aynı sayı dönüyorsa bağlanmamıştır.

    Evrenler yalnızca 2 satır ayrıştığı için (üstteki bekçi) bu fark
    fiyattan gelir: açılış çizgisi kapanıştan başka bir yere bakıyor.
    """
    k = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    a = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili",
                      cizgi="acilis")
    assert a["cizgi"] == "acilis"
    assert a["toplam"]["n"] != k["toplam"]["n"]


@pytest.mark.parametrize("bozuk", ["AvgC", "kapanış", "", "KAPANIS", None, 1])
def test_gecersiz_cizgi_SESSIZCE_dusmez(bozuk):
    """Bilinmeyen çizgi varsayılana düşmemeli — `inf` ve kırpılan
    toleransla aynı türden arıza: istek reddedilmiyor, BAŞKA BİR SORGUYA
    çevriliyor. `?cizgi=AvgC` yazan biri kapanış cevabını alıp açılış
    sorduğunu sanırdı."""
    with pytest.raises(ValueError, match="cizgi"):
        benzer_maclar(ORNEK, tolerans=0.02, cizgi=bozuk)


def test_api_cizgi_govdede_YAZAR_ve_bozugu_400(istemci):
    r = istemci.get("/api/benzer?oran=1.82,3.04,2.44&cizgi=acilis")
    assert r.status_code == 200
    assert r.get_json()["cizgi"] == "acilis"
    assert istemci.get(
        "/api/benzer?oran=1.82,3.04,2.44&cizgi=AvgC").status_code == 400


def test_cizgi_onbellegi_ayri_goz_kullanir():
    """İki çizgi aynı önbellek gözünü paylaşırsa biri diğerinin cevabını
    döndürür. `_olasilik_tablosu` anahtarı `cizgi`yi de içermeli."""
    assert _olasilik_tablosu("orantili", None, "kapanis") is not \
        _olasilik_tablosu("orantili", None, "acilis")
    assert len(CIZGILER) == 2


# ─── lig etiketi ──────────────────────────────────────────────────────────────

def test_lig_dilimi_OKUNUR_etiket_tasir():
    """Kod (`T1`) değil ad (`Türkiye · Süper Lig`) gösterilebilsin diye.

    Çeviri sunucuda yapılır: harita (`odds.LIG_ADLARI`) orada zaten var,
    arayüze kopyalansaydı ayrışabilen ikinci bir sözlük olurdu.
    """
    r = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    ligler = {d["deger"]: d["etiket"] for d in r["dilimler"]["lig"]}
    assert ligler.get("T1") == "Türkiye · Süper Lig"
    assert all(d["etiket"] for d in r["dilimler"]["lig"])
    # Sezon diliminde cevrilecek bir sey yok; etiket degeri aynen tasir.
    assert all(d["etiket"] == d["deger"] for d in r["dilimler"]["sezon"])


# ─── maç listesi ──────────────────────────────────────────────────────────────

def test_mac_listesi_karneyle_AYNI_kumeyi_sayar():
    """**Bu dosyanın asıl yeni bekçisi.**

    Uyarlanan yarıçap EVRENE bağlıdır: `lig="T1"` ile yapılan arama, bütün
    liglerdeki aramadan daha küçük bir evrende durduğu için daha GENİŞ bir
    yarıçapta dinlenir. Liste kendi yarıçapını uyarlasaydı, lig satırında
    "n=41" okuyup tıklayan kullanıcı başka sayıda maç görürdü — ve iki
    sayının neden tutmadığını gösteren hiçbir alan olmazdı.

    Sözleşme bu yüzden şu: çağıran taraf karnenin **çözdüğü** yarıçapı
    aynen geri verir. Test onu her lig dilimi için doğrular.
    """
    r = benzer_maclar(ORNEK, tolerans=None, yontem="orantili")
    tol = r["tolerans"]
    assert r["dilimler"]["lig"], "lig dilimi yok — test bir sey olcmuyor"
    for d in r["dilimler"]["lig"]:
        liste = benzer_mac_listesi(ORNEK, tolerans=tol, lig=d["deger"],
                                   yontem="orantili", limit=EN_COK_LISTE)
        assert liste["n"] == d["karne"]["n"], (
            f"{d['deger']}: karne {d['karne']['n']} mac sayiyor, liste "
            f"{liste['n']} dondurdu — yaricap ayristi."
        )


def test_mac_listesi_UYARLANAN_yaricapla_cagrilirsa_ayrisirdi():
    """Üstteki bekçinin **niçin** var olduğunu gösteren ölçüm.

    Aynı sorgu lig süzgeciyle kendi yarıçapını uyarlarsa, süzgeçsiz aramanın
    çözdüğü yarıçaptan farklı bir yere düşer. Bu test o farkın gerçek
    olduğunu kanıtlar; kaybolursa `tolerans`ı zorunlu tutmanın gerekçesi de
    kaybolmuş demektir ve sözleşme yeniden düşünülmeli.
    """
    genel = benzer_maclar(ORNEK, tolerans=None, yontem="orantili")
    tekil = benzer_maclar(ORNEK, tolerans=None, yontem="orantili", lig="T1")
    assert tekil["tolerans"] > genel["tolerans"]


def test_mac_listesi_tolerans_ZORUNLU():
    with pytest.raises(ValueError, match="tolerans"):
        benzer_mac_listesi(ORNEK, tolerans=None)


def test_mac_listesi_satiri_ARANAN_cizginin_fiyatini_tasir():
    """Kapanış evreninde arayıp açılış oranı göstermek, satırın neden
    bulunduğunu okunamaz kılardı."""
    for cizgi in CIZGILER:
        liste = benzer_mac_listesi(ORNEK, tolerans=0.02, lig="T1",
                                   yontem="orantili", cizgi=cizgi, limit=5)
        assert liste["cizgi"] == cizgi
        for m in liste["maclar"]:
            assert set(m["oranlar"]) == set(SEMBOLLER)
            assert m["mesafe"] <= 0.02
            assert m["kod"] in SEMBOLLER
            assert m["lig_etiket"]
        # Mesafeye gore artan: en benzer mac ustte.
        uzakliklar = [m["mesafe"] for m in liste["maclar"]]
        assert uzakliklar == sorted(uzakliklar)


def test_mac_listesi_sayfalama_kumeyi_bolmez():
    """`n` KÜMENİN, `maclar` SAYFANIN boyudur; arayüz 'N maçın M'si'
    diyebilsin diye ikisi ayrı alan."""
    tam = benzer_mac_listesi(ORNEK, tolerans=0.02, lig="T1",
                             yontem="orantili", limit=EN_COK_LISTE)
    ilk = benzer_mac_listesi(ORNEK, tolerans=0.02, lig="T1",
                             yontem="orantili", limit=10)
    sonra = benzer_mac_listesi(ORNEK, tolerans=0.02, lig="T1",
                               yontem="orantili", limit=10, atla=10)
    assert ilk["n"] == sonra["n"] == tam["n"]
    assert len(ilk["maclar"]) == 10
    assert ([m["tarih"] for m in ilk["maclar"] + sonra["maclar"]]
            == [m["tarih"] for m in tam["maclar"][:20]])


def test_az_ornek_dilim_YUZDE_vermez_ama_LISTELENEBILIR():
    """Onaylanan kural: yüzde bir iddiadır ve `AZ_ORNEK` altında okunmaz;
    maç listesi bir iddia değil KAYITTIR, o yüzden eşik ona uygulanmaz.

    12 maçlık bir ligin yüzdesi okunmaz ama o 12 maç görülebilir.
    """
    r = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    ince = [d for d in r["dilimler"]["lig"] if not d["karne"]["yeterli"]]
    if not ince:
        pytest.skip("bu sorguda AZ_ORNEK altinda dilim yok")
    d = ince[0]
    assert d["karne"]["n"] < AZ_ORNEK
    liste = benzer_mac_listesi(ORNEK, tolerans=0.02, lig=d["deger"],
                               yontem="orantili", limit=EN_COK_LISTE)
    assert liste["n"] == d["karne"]["n"] > 0
    assert len(liste["maclar"]) == liste["n"]


@pytest.mark.parametrize("bozuk", [{"limit": 0}, {"limit": EN_COK_LISTE + 1},
                                   {"atla": -1}, {"cizgi": "AvgC"}])
def test_mac_listesi_sinir_disi_deger_SESSIZCE_kirpilmaz(bozuk):
    with pytest.raises(ValueError):
        benzer_mac_listesi(ORNEK, tolerans=0.02, yontem="orantili", **bozuk)


# ─── /api/benzer/maclar ───────────────────────────────────────────────────────

def test_api_maclar_govdesi_karneyle_ayni_n_verir(istemci):
    r = istemci.get("/api/benzer?oran=1.82,3.04,2.44&arindirma=orantili"
                    ).get_json()
    tol = r["tolerans"]
    d = r["dilimler"]["lig"][0]
    g = istemci.get(
        f"/api/benzer/maclar?oran=1.82,3.04,2.44&arindirma=orantili"
        f"&tolerans={tol}&lig={d['deger']}&limit={EN_COK_LISTE}").get_json()
    assert g["n"] == d["karne"]["n"]
    assert g["cizgi"] == "kapanis"
    for m in g["maclar"]:
        assert {"tarih", "lig", "lig_etiket", "ev", "dep", "ev_gol",
                "dep_gol", "kod", "oranlar", "mesafe"} <= set(m)


@pytest.mark.parametrize("sorgu", [
    # `tolerans` YOK — varsayilana dusmemeli, 400 vermeli.
    "?oran=1.82,3.04,2.44",
    "?oran=1.82,3.04,2.44&tolerans=abc",
    "?oran=1.82,3.04,2.44&tolerans=0.9",
    "?oran=1.82,3.04,2.44&tolerans=0.02&cizgi=AvgC",
    "?oran=1.82,3.04,2.44&tolerans=0.02&limit=99999",
    "?oran=1.82,3.04,2.44&tolerans=0.02&arindirma=kelly",
    "?oran=abc&tolerans=0.02",
])
def test_api_maclar_bozuk_girdi_400_verir(istemci, sorgu):
    assert istemci.get("/api/benzer/maclar" + sorgu).status_code == 400


# ─── docstring'in ölçümü ──────────────────────────────────────────────────────

def test_docstring_olcumu_GERCEK_kosumla_ayni():
    """Modül başındaki ölçüm bloğu bugünkü koşumla eşit olmalı.

    **Niçin var.** 2026-09-12'de korpus 22 ligden 17'ye inince o bloğun
    korpus boyutu satırı güncellendi, hemen üstündeki sayılar (709/710)
    güncellenmedi ve bayat kaldı — gerçek 426'ydı. Aynı arıza aynı gün
    başka bir ölçümde on bir yere yayılmıştı
    (`test_capraz_dogrulama_sayilari_RAPORLA_ayni`), ve iki kez yakalanmadı
    çünkü metni tutan bir bekçi yoktu. Bu, o bekçinin bu modüldeki eşi:
    **veriyi değil METNİ** tutar.
    """
    import re

    import spor_toto.benzer as modul

    satirlar = dict(re.findall(r"olasılık ±2 puan \.+\s+(\d+) maç\s+(\d+) maç",
                               modul.__doc__ or ""))
    assert satirlar, "docstring'deki olcum blogu okunamadi — bicim degisti mi?"
    kapanis_yazili, acilis_yazili = next(iter(satirlar.items()))
    for cizgi, yazili in (("kapanis", kapanis_yazili),
                          ("acilis", acilis_yazili)):
        r = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili",
                          cizgi=cizgi)
        assert r["toplam"]["n"] == int(yazili), (
            f"docstring {cizgi} icin {yazili} yaziyor, kosum "
            f"{r['toplam']['n']} veriyor — blok bayat."
        )


# ─── taban (kıyas çizgisi) ────────────────────────────────────────────────────

def test_taban_EVRENIN_tamamini_sayar():
    """Bir yüzde tek başına okunamaz; kıyas çizgisi gövdede gelmeli.

    "Bu oranda %58 ev sahibi" çarpıcı görünür ama korpusun genelinde ev
    sahibi zaten %43,5 kazanıyor — fiyatın taşıdığı bilgi ikisinin FARKI.
    Sayı arayüzde elle yazılmaz; burada evrenin kendisinden sayılır.
    """
    r = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    assert set(r["taban"]) == set(SEMBOLLER)
    assert sum(r["taban"].values()) == r["evren"] == len(KORPUS)
    # Ev sahibi ustunlugu korpusun bilinen ozelligi; yon tersine donerse
    # okunan sey artik ayni korpus degildir.
    assert r["taban"]["1"] > r["taban"]["2"] > r["taban"]["0"]


def test_taban_SUZGECLE_birlikte_daralir():
    """Kıyas hep **aynı havuzla** yapılmalı: lig süzgeci varsa taban da o
    ligin tabanıdır, korpusun tamamının değil. Aksi halde Süper Lig'in
    beraberlik oranı, 17 ligin ortalamasıyla kıyaslanırdı."""
    genel = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    tekil = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili", lig="T1")
    assert sum(tekil["taban"].values()) == tekil["evren"] < genel["evren"]


# ─── Lig envanteri (`/api/benzer/ligler`) ────────────────────────────────

def test_lig_envanteri_ARAMAYLA_ayni_evreni_sayar():
    """Listedeki toplam, aramanın gördüğü evrenle **birebir** aynı olmalı.

    Bu bir tercih değil, bir değişmez. Envanter ayrı bir filtre yazsaydı
    (ve ilk sürümde tam bunu yaptı: `r.get("kapanis")` — korpusta öyle bir
    alan yok, kapanış fiyatı `oranlar`da durur) liste "şu ligde 241 maç"
    der, arama aynı ligde başka bir sayı bulurdu. Kullanıcı da hangisinin
    doğru olduğunu anlayamazdı.

    İki çizgi AYRI ayrı tutuluyor: açılış evreni kapanıştan küçüktür
    (23.083 ↔ 23.085) ve bu fark ölçülmüş bir şeydir.
    """
    from spor_toto.benzer import benzer_maclar, lig_envanteri

    for cizgi in ("kapanis", "acilis"):
        envanter = lig_envanteri(cizgi)
        toplam = sum(x["n"] for x in envanter)
        arama = benzer_maclar({"1": 1.82, "0": 3.04, "2": 2.44},
                              tolerans=0.02, yontem="shin", cizgi=cizgi)
        assert toplam == arama["evren"], (
            f"{cizgi}: envanter {toplam}, arama {arama['evren']}")


def test_lig_envanteri_ETIKETI_SUNUCUDA_cevirir():
    """Çeviri `odds.LIG_ADLARI`den gelir; arayüz kendi sözlüğünü tutmaz."""
    from spor_toto.benzer import lig_envanteri
    from spor_toto.odds import LIG_ADLARI

    envanter = lig_envanteri("kapanis")
    assert envanter, "korpus ligsiz olamaz"
    for x in envanter:
        assert x["etiket"] == LIG_ADLARI.get(x["lig"], x["lig"])
        assert x["n"] > 0, "sifir macli lig listede durmaz"
    # Siralama buyukten kucuge: secici en cok macli ligi basta gostersin.
    assert [x["n"] for x in envanter] == sorted((x["n"] for x in envanter), reverse=True)
    # Bilinmeyen cizgi sessizce varsayilana DUSMEZ.
    with pytest.raises(ValueError):
        lig_envanteri("AvgC")


def test_lig_suzgeci_EVRENI_daraltir_ve_bunu_yazar():
    """`lig=` verilen arama, o ligin evreninde koşar.

    Sayfanın "maçı kendi liginde değerlendir" seçeneği tam buna dayanıyor;
    daralmanın ölçüsü de görünür olmalı — daralan evrende yarıçap büyür ve
    örneklem küçülür.
    """
    from spor_toto.benzer import benzer_maclar, lig_envanteri

    envanter = {x["lig"]: x["n"] for x in lig_envanteri("kapanis")}
    hepsi = benzer_maclar({"1": 1.82, "0": 3.04, "2": 2.44},
                          tolerans=0.02, yontem="shin")
    tek = benzer_maclar({"1": 1.82, "0": 3.04, "2": 2.44},
                        tolerans=0.02, yontem="shin", lig="T1")
    assert tek["evren"] == envanter["T1"]
    assert tek["evren"] < hepsi["evren"]
    assert tek["filtre"]["lig"] == "T1", "hangi suzgecle arandigi cevapta yazar"
    assert tek["toplam"]["n"] <= hepsi["toplam"]["n"]


def test_api_ligler_ucu_cizgiyi_okur_bozuga_400():
    import web_app
    c = web_app.app.test_client()

    govde = c.get("/api/benzer/ligler").get_json()
    assert govde["cizgi"] == "kapanis"
    assert govde["evren"] == sum(x["n"] for x in govde["ligler"])
    assert {"lig", "etiket", "n"} == set(govde["ligler"][0])

    acilis = c.get("/api/benzer/ligler?cizgi=acilis").get_json()
    assert acilis["evren"] < govde["evren"], "acilis evreni kapanistan kucuk"
    assert c.get("/api/benzer/ligler?cizgi=AvgC").status_code == 400
