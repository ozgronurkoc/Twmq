"""Benzer maç arama ve marj arındırma yöntemleri.

Bu dosyanın asıl işi bir tasarım kararını çivilemek: eşleme **olasılık
uzayında** yapılır, oran uzayında değil. Sebep ölçülmüş bir olgudur ve
`test_oran_uzayinda_arama_bos_doner` onu regresyona bağlar.
"""

import pytest

from spor_toto.benzer import (
    AZ_ORNEK,
    EN_COK_TOLERANS,
    _mesafe,
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

    Ölçüldü (31.099 maç): piyasanın %70–80 dediği maçlar gerçekte %78,9
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
    r = benzer_maclar(ORNEK, tolerans=0.02, yontem="orantili")
    assert r["toplam"]["n"] == 710
    sayilar = {s: r["toplam"]["semboller"][s]["adet"] for s in SEMBOLLER}
    assert sayilar == {"1": 293, "0": 184, "2": 233}


def test_varsayilan_yontem_kendi_sayilarini_uretir():
    """Bugünün varsayılanı (`shin`) — aynı oran, farklı ölçek, farklı komşuluk.

    Aynı yarıçap Shin ölçeğinde daha az maç buluyor: yüksek marjlı hedef
    oran (%28,8) Shin'de favoriye daha çok pay verdiği için korpusun düşük
    marjlı maçlarından uzaklaşıyor.
    """
    r = benzer_maclar(ORNEK, tolerans=0.02)
    assert r["arindirma"] == "shin"
    assert r["toplam"]["n"] == 241
    assert sum(r["toplam"]["semboller"][s]["adet"] for s in SEMBOLLER) == 241


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
    assert g["toplam"]["n"] == 710
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
