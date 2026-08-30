"""Tahmin ürünü (C2) — ürünün söyleyebileceği yalanların bekçisi.

Bu paketteki diğer tahmin testleri bir **ölçümün** doğruluğunu korur. Burası
farklı: ürün, sonucu bilinmeyen bir maça sayı veriyor ve o sayıyı gören
kişi ona göre para harcayacak. Dolayısıyla korunan şey doğruluk değil
**dürüstlük**.

Ürünün söyleyebileceği dört yalan var ve dördünün de bekçisi burada:

    1. Olasılığı ölçülmüş isabetinden ayırmak — "şu maç %70" deyip
       tahmincinin 540 maçta %55,6 tutturduğunu söylememek
    2. 14+ tutturabileceğini ima etmek — tek kolonla P(14+) ≈ 1/1.161
    3. İddaa kaynaklı olasılığı ölçülmüş gibi göstermek — kalibrasyonu
       ölçülmedi, marj iki katından fazla
    4. Başlamış maça "maç öncesi" olasılığı vermek

En kritiği birincisi: `test_olasilik_isabetsiz_cikamaz`.
"""

import csv
from datetime import datetime, timedelta

import pytest

from spor_toto.tahmin import (
    KAYNAK_OLCULEN,
    KAYNAK_OLCULMEMIS,
    _gelecekte,
    fixtures_maclari,
    iddaa_maclari,
    olculmus_isabet,
    rapor,
    tahmin_et,
    yaklasan_maclar,
)


def _fixtures_yaz(yol, satirlar):
    basliklar = ["lig", "tarih", "saat", "ev", "dep", "oran_1", "oran_0",
                 "oran_2", "oran_kaynak", "olculen_lig"]
    with open(yol, "w", encoding="utf-8", newline="") as fh:
        y = csv.DictWriter(fh, fieldnames=basliklar)
        y.writeheader()
        y.writerows(satirlar)


def _fixture_satiri(**kw):
    temel = {"lig": "E0", "tarih": "2099-01-01", "saat": "20:00", "ev": "A",
             "dep": "B", "oran_1": 2.0, "oran_0": 3.5, "oran_2": 4.0,
             "oran_kaynak": "Avg", "olculen_lig": "1"}
    temel.update(kw)
    return temel


def _iddaa_yaz(yol, satirlar):
    basliklar = ["alinma", "event_id", "kickoff", "home", "away", "lig",
                 "lig_kodu", "canli", "odd_1", "odd_0", "odd_2",
                 "wodd_1", "wodd_0", "wodd_2", "marj"]
    with open(yol, "w", encoding="utf-8", newline="") as fh:
        y = csv.DictWriter(fh, fieldnames=basliklar, extrasaction="ignore")
        y.writeheader()
        y.writerows(satirlar)


def _iddaa_satiri(**kw):
    ileri = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
    temel = {"alinma": "2099-01-01 08:00", "event_id": "1", "kickoff": ileri,
             "home": "C", "away": "D", "lig": "Bir Lig", "lig_kodu": "1",
             "canli": "0", "odd_1": 2.0, "odd_0": 3.4, "odd_2": 3.8,
             "wodd_1": 2.0, "wodd_0": 3.4, "wodd_2": 3.8, "marj": "0.17"}
    temel.update(kw)
    return temel


# ─── kırmızı çizgi: olasılık ölçülmüş isabetinden ayrılamaz ───────────────────

def test_olasilik_isabetsiz_cikamaz(tmp_path):
    """**Projenin tek kırmızı çizgisi.**

    Gövde bir olasılık taşıyorsa, o tahmincinin ölçülmüş isabetini de
    taşımak zorundadır. Ayrılırsa geriye "şu maç %70" kalır ve bu, projenin
    baştan beri karşı çıktığı şeyin ta kendisidir.
    """
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri()])
    g = rapor(fixtures_yolu=str(yol))

    assert g["tahminler"], "tahmin uretilmedi — test anlamsiz"
    assert "olculmus_isabet" in g
    i = g["olculmus_isabet"]
    assert i["olculdu"] is True
    for alan in ("n_mac", "mac_basina_isabet", "brier", "hafta_ortalamasi",
                 "hafta_14_arti"):
        assert alan in i["manset"], f"manset blogunda {alan} yok"
    # Gövde bir ALTERNATIF olasilik tasiyorsa, onun da isabeti gelmeli.
    if any(s.get("alternatif") for s in g["tahminler"]):
        a = i["alternatif"]
        assert a is not None, "alternatif olasilik var ama isabeti yok"
        for alan in ("brier", "mac_basina_isabet", "fark", "gecti"):
            assert alan in a, f"alternatif isabetinde {alan} yok"


def test_uyarilar_kisaltilmaz(tmp_path):
    """Sınırlar gövdenin parçası; hiçbiri koşula bağlı olarak düşmez.

    İki uyarı **her zaman** vardır: tek kolonla 14+ tutturulamayacağı ve
    olasılıkların model değil piyasa fiyatı olduğu.
    """
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri()])
    adlar = {u["ad"] for u in rapor(fixtures_yolu=str(yol))["uyarilar"]}
    assert "tek_kolon_14_tutmaz" in adlar
    assert "model_yok" in adlar


def test_14_uyarisi_sayiyi_tasir(tmp_path):
    """Uyarı "zor" demiyor, **ölçülmüş sayıyı** söylüyor.

    "Zor" bir kanaat; "1/1.161 hafta" bir ölçüm. Projenin farkı bu.
    """
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri()])
    u = next(x for x in rapor(fixtures_yolu=str(yol))["uyarilar"]
             if x["ad"] == "tek_kolon_14_tutmaz")
    assert "1.161" in u["metin"] and "0,031" in u["metin"]


def test_olculmus_isabet_arsivden_kosuyor():
    """Sayılar elle yazılmadı — veri kayarsa sayı da kayar.

    Elle yazılmış bir isabet, arşiv değiştiğinde sessizce yalan söylemeye
    başlar. `test_health.py::_check_tahmin_referanslari` ile aynı gerekçe.
    """
    i = olculmus_isabet()
    if not i.get("olculdu"):
        pytest.skip("oran arsivi yok")
    m = i["manset"]
    assert m["n_mac"] == 540 and i["n_hafta"] == 36
    assert 0.50 < m["mac_basina_isabet"] < 0.62
    assert 0.55 < m["brier"] < 0.62
    # A4'un yazdigi sayi: tek kolonla 14+ hic gelmedi
    assert m["hafta_14_arti"] == 0


# ─── kaynak dürüstlüğü ────────────────────────────────────────────────────────

def test_iddaa_kaynagi_olculmemis_diye_isaretlenir(tmp_path):
    """İddaa marjı %17,2, ölçüm %7,26'lık kaynakta yapıldı — aynı şey değil."""
    yol = tmp_path / "iddaa_2099-01-01.csv"
    _iddaa_yaz(yol, [_iddaa_satiri()])
    g = rapor(fixtures_yolu=str(tmp_path / "yok.csv"), iddaa_yolu=str(yol))
    assert g["kaynaklar"] == [KAYNAK_OLCULMEMIS]
    assert g["olculen_kaynak"] is False
    adlar = {u["ad"] for u in g["uyarilar"]}
    assert "kalibrasyon_olculmemis" in adlar


def test_olculen_kaynak_tercih_edilir(tmp_path):
    """İkisi de varsa fikstür kazanır — ölçüm onun üzerinde yapıldı.

    Karıştırılsaydı gövdedeki tek isabet sayısı iki farklı fiyatlayıcıya
    aitmiş gibi okunurdu.
    """
    f = tmp_path / "f.csv"
    i = tmp_path / "iddaa_2099-01-01.csv"
    _fixtures_yaz(f, [_fixture_satiri()])
    _iddaa_yaz(i, [_iddaa_satiri()])
    maclar = yaklasan_maclar(str(f), str(i))
    assert {m["kaynak"] for m in maclar} == {KAYNAK_OLCULEN}


def test_olcum_evreni_disi_isaretlenir(tmp_path):
    """Korpusun taşımadığı bir lig için isabet o maça ait değildir."""
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri(lig="XX", olculen_lig="0")])
    adlar = {u["ad"] for u in rapor(fixtures_yolu=str(yol))["uyarilar"]}
    assert "olcum_evreni_disi" in adlar


# ─── başlamış maça tahmin verilmez ────────────────────────────────────────────

def test_baslamis_mac_elenir(tmp_path):
    """Snapshot dünden kalmış olabilir; oynanmış maça tahmin verilmez."""
    yol = tmp_path / "iddaa_2099-01-01.csv"
    gecmis = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
    _iddaa_yaz(yol, [_iddaa_satiri(kickoff=gecmis)])
    assert iddaa_maclari(str(yol)) == []


def test_canli_mac_elenir(tmp_path):
    yol = tmp_path / "iddaa_2099-01-01.csv"
    _iddaa_yaz(yol, [_iddaa_satiri(canli="1")])
    assert iddaa_maclari(str(yol)) == []


def test_cozulemeyen_saat_elenir():
    """Doktrin 2: belirsiz zaman uydurulmaz, maç elenir."""
    simdi = datetime(2099, 1, 1, 12, 0)
    assert _gelecekte("2099-01-02 20:00", simdi) is True
    assert _gelecekte("2098-01-02 20:00", simdi) is False
    assert _gelecekte("", simdi) is False
    assert _gelecekte("bilinmiyor", simdi) is False
    assert _gelecekte(None, simdi) is False


# ─── olasılığın kendisi ───────────────────────────────────────────────────────

def test_tahmin_marj_arindirilmis():
    """Olasılıklar 1'e toplanmalı — ham oran değil, olasılık gösteriliyor."""
    t = tahmin_et({"kaynak": KAYNAK_OLCULEN, "lig": "E0", "tarih": "2099-01-01",
                   "saat": "20:00", "ev": "A", "dep": "B", "oran_kaynak": "Avg",
                   "olculen_lig": True,
                   "oranlar": {"1": 2.0, "0": 3.5, "2": 4.0}})
    assert sum(t["olasilik"].values()) == pytest.approx(1.0, abs=1e-3)
    assert t["en_olasi"] == "1"
    assert t["guven"] == pytest.approx(t["olasilik"]["1"])


def test_eksik_oran_maci_eler(tmp_path):
    """Doktrin 2: eksik oran doldurulmaz, maç elenir."""
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri(oran_0="")])
    assert fixtures_maclari(str(yol)) == []


# ─── boş durum ────────────────────────────────────────────────────────────────

def test_bos_durum_sebebini_soyler(tmp_path):
    """Yaklaşan maç yok **bir hata değil**; fikstür yuvarlanan penceredir.

    Ama sessizce boş dönmek de olmaz — sebep gövdede yazılı olmalı.
    """
    g = rapor(fixtures_yolu=str(tmp_path / "yok.csv"),
              iddaa_yolu=str(tmp_path / "yok2.csv"))
    assert g["n_mac"] == 0
    assert g["tahminler"] == []
    assert g["bos_sebep"] and "yuvarlanan" in g["bos_sebep"]
    # Isabet ve uyarilar BOS DURUMDA DA gelir — govde hep tam.
    assert g["olculmus_isabet"]
    assert len(g["uyarilar"]) >= 2


def test_dolu_durumda_bos_sebep_yok(tmp_path):
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri()])
    assert rapor(fixtures_yolu=str(yol))["bos_sebep"] is None


def test_limit_yalnizca_listeyi_kirpar(tmp_path):
    """`?limit=` isabeti ve uyarıları kırpmaz — gövde hep tam."""
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri(ev=f"T{i}") for i in range(5)])
    g = rapor(fixtures_yolu=str(yol), limit=2)
    assert len(g["tahminler"]) == 2
    assert g["olculmus_isabet"]["olculdu"] is True
    assert len(g["uyarilar"]) >= 2


# ─── API sözleşmesi ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    import web_app
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


def test_api_tahmin_govdesi(client):
    r = client.get("/api/tahmin?limit=3")
    assert r.status_code == 200
    g = r.get_json()
    for alan in ("n_mac", "kaynaklar", "tahminler", "olculmus_isabet",
                 "uyarilar", "bos_sebep"):
        assert alan in g, f"govdede {alan} yok"
    assert len(g["tahminler"]) <= 3


def test_api_tahmin_isabeti_hep_tasir(client):
    """**Kırmızı çizginin API tarafı.** Limit ne olursa olsun isabet gelir."""
    for sorgu in ("", "?limit=1", "?limit=999999", "?limit=abc"):
        g = client.get(f"/api/tahmin{sorgu}").get_json()
        assert g["olculmus_isabet"], f"{sorgu}: isabet blogu dustu"
        adlar = {u["ad"] for u in g["uyarilar"]}
        assert "tek_kolon_14_tutmaz" in adlar, f"{sorgu}: 14+ uyarisi dustu"


def test_api_tahmin_bozuk_limit_cokmez(client):
    for ham in ("abc", "-5", "0", "1e9", ""):
        assert client.get(f"/api/tahmin?limit={ham}").status_code == 200


# ─── alternatif tahminci ──────────────────────────────────────────────────────

def test_alternatif_gecmedi_diye_etiketli():
    """**Alternatifin varlik sarti.**

    `kalibre_bias` ortalamada piyasadan iyi ama guven araligi sifiri
    iceriyor. Urun onu manset yapamaz; ama olculdugu icin de saklayamaz.
    Dogru davranis: yaninda dursun, `gecti=False` etiketiyle.

    Bu test kirilirsa — yani alternatif GECERSE — o zaman manset kararinin
    yeniden dusunulmesi gerekir ve bu bilincli bir istir, sessiz bir
    guncelleme degil.
    """
    i = olculmus_isabet()
    if not i.get("olculdu") or not i.get("alternatif"):
        pytest.skip("korpus ya da arsiv yok")
    a = i["alternatif"]
    assert a["gecti"] is False, (
        f"alternatif GECTI ({a['fark']}) — manset karari gozden gecirilmeli")
    # Ortalamada daha iyi olmali; degilse alternatifi tasimanin anlami yok.
    assert a["brier"] < i["manset"]["brier"]
    assert a["fark"]["alt"] < 0 < a["fark"]["ust"], "aralik sifiri icermeli"


def test_alternatif_manseti_degistirmez(tmp_path):
    """Manşet her zaman eğitimsiz `piyasa`dır.

    Alternatif ayrı bir alanda durur; manşet olasılığın yerine geçmez.
    Geçseydi sayfadaki ölçülmüş isabet kartı başka bir tahmincinin
    sayılarını gösteriyor olurdu.
    """
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri()])
    g = rapor(fixtures_yolu=str(yol))
    t = g["tahminler"][0]
    from spor_toto.odds import implied_probs
    ham = implied_probs({"1": 2.0, "0": 3.5, "2": 4.0})
    for s in ("1", "0", "2"):
        assert t["olasilik"][s] == pytest.approx(ham[s], abs=1e-4)


def test_alternatif_sozde_haftada_kupon_arsivine_bakmaz(tmp_path):
    """**Sessiz ve zehirli bir hatanin bekcisi.**

    `recalibrate._mac_ozellikleri`, `ozellikler` alani yoksa oran arsivine
    `(hafta, mac no)` ile bakar — kupon setine ozgu bir yol. Yaklasan macta
    o arama TAMAMEN BASKA bir macin ozelligini dondururdu.

    `_sozde_hafta` bu yuzden alani acikca doldurur. Burada dogrulanan sey:
    uretilen sozde haftanin her maci icin ozellik var ve hicbiri arsivden
    gelmiyor (form/hareket/ayrisma notr sifir).
    """
    from spor_toto.recalibrate import _mac_ozellikleri
    from spor_toto.tahmin import _sozde_hafta

    maclar = [{"lig": "E0", "oranlar": {"1": 2.0, "0": 3.5, "2": 4.0}},
              {"lig": "D1", "oranlar": {"1": 1.5, "0": 4.0, "2": 6.0}}]
    hafta = _sozde_hafta(maclar)
    assert hafta["ozellikler"] is not None
    satirlar = _mac_ozellikleri(hafta)
    assert len(satirlar) == len(maclar)
    for s in satirlar:
        assert s["form_puan_farki"] == 0.0
        assert s["ayrisma"] == 0.0
        assert all(v == 0.0 for v in s["hareket"].values())


def test_alternatif_farkli_secim_sayilir(tmp_path):
    """Alternatifin sıralamayı değiştirip değiştirmediği **ölçülür**.

    Sıfır çıkıyorsa tek kolon oynayan biri için iki tahminci aynıdır ve
    kullanıcının bunu tahmin etmesi değil görmesi gerekir.
    """
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri(ev=f"T{i}") for i in range(4)])
    g = rapor(fixtures_yolu=str(yol))
    assert "alternatif_farkli_secim" in g
    assert 0 <= g["alternatif_farkli_secim"] <= g["n_mac"]


def test_alternatif_uyarisi_var(tmp_path):
    yol = tmp_path / "f.csv"
    _fixtures_yaz(yol, [_fixture_satiri()])
    g = rapor(fixtures_yolu=str(yol))
    if not any(s.get("alternatif") for s in g["tahminler"]):
        pytest.skip("korpus yok — alternatif uretilmedi")
    adlar = {u["ad"] for u in g["uyarilar"]}
    assert "alternatif_gecmedi" in adlar


def test_gecti_karari_yuvarlanmamis_sinirdan_verilir(monkeypatch):
    """`gecti` YUVARLANMIS ust sinirdan karar vermemeli.

    `evaluate.bootstrap_farki` bu alani bilerek iki kez dondurur ve kendi
    yorumunda gerekcesini yazar: `round(-0.000031, 4)` `-0.0` verir ve
    `-0.0 < 0` Python'da `False`'tur. Yani guven araliginin TAMAMI sifirin
    altindayken aday "gecmedi" diye yazilirdi — hem de aralik daraldikca,
    yani tam kararin zorlastigi yerde.

    `evaluate.py` iki karar noktasinda da `ham_ust` okuyor; burasi urune
    `/api/tahmin` ile cikan ucuncu karar noktasidir ve ayni kurala uymali.
    """
    import spor_toto.evaluate as ev

    # Aralik tamamen sifirin altinda ama yuvarlaninca -0.0'a duser.
    dar = {"fark": -0.0, "alt": -0.0001, "ust": -0.0,
           "ham_fark": -0.000031, "ham_alt": -0.000052, "ham_ust": -0.000031,
           "tekrar": 2000}
    monkeypatch.setattr(ev, "bootstrap_farki", lambda a, m: dar)

    olculmus_isabet.cache_clear()
    try:
        i = olculmus_isabet()
    finally:
        olculmus_isabet.cache_clear()

    if not i.get("olculdu") or not i.get("alternatif"):
        pytest.skip("oran arsivi ya da egitilmis alternatif yok")

    assert i["alternatif"]["fark"]["ham_ust"] < 0
    assert i["alternatif"]["gecti"] is True, (
        "aralik tamamen sifirin altinda ama karar yuvarlanmis sinirdan "
        "verildigi icin 'gecmedi' dondu"
    )


# ─── geniş kesit: dört sezon, sezon dışarıda bırakmalı ───────────────────────

def test_genis_kesit_VARSAYILAN_govdede_yok():
    """`?genis` istenmediyse alan gövdede HİÇ olmamalı.

    `None` yazmak yanlış olurdu: "ölçülmedi" ile "ölçüldü, sonuç boş" ayrı
    şeylerdir ve arayüz ikincisini "veri yok" diye gösterirdi. Ayrıca bu
    testin asıl işi bedeli çıpalamak — alan gövdeye sızarsa `/api/tahmin`in
    soğuk maliyeti sessizce ~38 sn artar (korpus okuması).
    """
    from spor_toto.tahmin import rapor

    g = rapor()
    assert "genis_kesit" not in g, (
        "geniş kesit varsayılan gövdeye sızmış — soğuk bedel 38 sn artar")
    assert g["olculmus_isabet"], "dar ölçüm bloğu düşmüş"


def test_genis_kesit_dar_olcumu_DEGISTIRMEZ():
    """Geniş ölçüm eklenince dar kesitin sayıları oynamamalı.

    İkisi ayrı katlar: dar kesit (2025/26) korpusla tek maç paylaşmıyor ve
    geniş şemanın **dördüncü katıdır**. Biri diğerini değiştirirse ya kat
    kurgusu ya önbellek bozulmuştur.
    """
    from spor_toto.tahmin import olculmus_isabet, rapor

    dar = olculmus_isabet()
    g = rapor(genis=True)
    assert g["olculmus_isabet"]["manset"] == dar["manset"]
    assert g["olculmus_isabet"]["n_hafta"] == dar["n_hafta"]


@pytest.mark.slow
def test_genis_kesit_katlari_sizintisiz_ve_TAM():
    """Her kupon sezonu için korpustan o sezon gerçekten çıkarılmış olmalı.

    Bu testin sınadığı şey bir sayı değil bir **sözleşme**: geniş kesitte
    kupon maçlarının 1.155/1.605'i korpusta da var, dolayısıyla katın
    eğitim seti test sezonunu içeriyorsa ölçüm sızıntılıdır ve raporlanan
    "piyasayı geçti" sonucu anlamsız olur.

    2025/26 katı bilerek istisna: korpus 2425'te bitiyor, o sezon korpusta
    zaten YOK, bu yüzden çıkarılan hafta sayısı sıfırdır ve olması gereken
    de budur.
    """
    from spor_toto.tahmin import genis_kesit_isabeti

    g = genis_kesit_isabeti()
    if not g.get("olculdu"):
        pytest.skip(g.get("not", "geniş kesit kurulamadı"))
    alt = g.get("alternatif")
    if alt is None:
        pytest.skip("korpus yok — alternatif ölçülemedi")

    katlar = {k["sezon"]: k for k in alt["katlar"]}
    assert len(katlar) >= 2, "tek kat — sezon dışarıda bırakmalı ölçüm kurulmamış"

    for sezon, k in katlar.items():
        assert k["test_hafta"] > 0
        assert k["egitim_hafta"] > 0, f"{sezon}: eğitim seti boş kalmış"
        if sezon == "2025/2026":
            assert k["korpustan_cikarilan_hafta"] == 0, (
                "2025/26 korpusta yok; bir şey çıkarıldıysa eşleme yanlış")
        else:
            assert k["korpustan_cikarilan_hafta"] > 0, (
                f"{sezon}: korpustan hiçbir hafta çıkarılmamış — SIZINTI")

    assert alt["n_mac"] == sum(k["n_mac"] for k in alt["katlar"])


def test_yazdir_yaklasan_mac_VARKEN_patlamaz():
    """`_yazdir` yaklaşan maç varken çökmemeli — ve ölçümü basmalı.

    **Bu bir kez gerçekten çöküyordu ve hiçbir test görmüyordu.** İç
    döngüdeki `g = "EVET"/"hayir"` ataması fonksiyonun `g` parametresini
    eziyordu; hemen ardından gelen `g["uyarilar"]` bir dizgede indeksleme
    olup `TypeError` veriyordu. Yaklaşan maç YOKKEN erken `return` araya
    girdiği için hata görünmüyordu — yani tam olarak elle kullanımda,
    fikstür doluyken patlıyordu. `# pragma: no cover` etiketi de kapsamı
    susturuyordu.

    Test bu yüzden iki hâli birden koşar: dolu fikstür (asıl kusur) ve boş
    fikstür (ölçüm blokları yine de basılmalı).
    """
    from spor_toto.tahmin import _yazdir

    skor = {"ad": "piyasa", "brier": 0.5, "mac_basina_isabet": 0.5,
            "hafta_ortalamasi": 8.0, "fark": None, "gecti": None}
    govde = {
        "n_mac": 1,
        "kaynaklar": ["test"],
        "alternatif_farkli_secim": 0,
        "tahminler": [{
            "tarih": "2026-01-01", "saat": "20:00", "lig": "T1",
            "ev": "A", "dep": "B", "olasilik": {"1": 0.4, "0": 0.3, "2": 0.3},
            "en_olasi": "1", "guven": 0.4, "alternatif": None,
        }],
        "uyarilar": [{"ad": "u", "metin": "m"}],
        "bos_sebep": None,
        "olculmus_isabet": {"olculdu": True, "kesit": "k", "n_hafta": 1,
                            "manset": skor},
    }
    _yazdir(govde)                       # dolu fikstür — eski kusur burada

    bos = dict(govde, n_mac=0, tahminler=[], bos_sebep="mac yok")
    _yazdir(bos)                         # boş fikstür — ölçüm yine basılmalı


def test_yazdir_bos_fiksturde_de_OLCUMU_basar(capsys):
    """Fikstür penceresi boşken ölçülmüş isabet GÖRÜNMELİ.

    Eskiden `if not g["n_mac"]: return` ölçüm bloklarını da yutuyordu.
    Oysa o sayı yaklaşan maçtan bağımsız — sürümlenmiş arşivden koşuyor.
    Projenin kırmızı çizgisi "olasılık ölçümsüz çıkmaz" der; tersi
    serbesttir ve hafta arası tam da bakılacak zamandır.
    """
    from spor_toto.tahmin import _yazdir

    _yazdir({
        "n_mac": 0, "kaynaklar": [], "alternatif_farkli_secim": None,
        "tahminler": [], "uyarilar": [], "bos_sebep": "mac yok",
        "olculmus_isabet": {
            "olculdu": True, "kesit": "kesit adi", "n_hafta": 36,
            "manset": {"ad": "piyasa", "brier": 0.574,
                       "mac_basina_isabet": 0.5556, "hafta_ortalamasi": 8.33,
                       "fark": None, "gecti": None}},
    })
    cikti = capsys.readouterr().out
    assert "OLCULMUS ISABET" in cikti, "boş fikstürde ölçüm bloğu yutuldu"
    assert "0.5740" in cikti


def test_api_genis_parametresi_UCTAN_calisir(client):
    """`?genis=` ayrıştırması uçtan sınanmalı, yalnızca fonksiyon düzeyinde değil.

    Ayrıştırma `web_app.api_tahmin` içinde yazılı bir küme
    (`{"1", "true", "evet", "yes"}`) ve fonksiyon testleri onu HİÇ
    görmüyordu: `rapor(genis=True)` çağrısı doğru sonucu veriyor olsa da
    uç parametreyi yanlış okusaydı kimse fark etmezdi.

    Açık/kapalı iki yön de sınanır. Kapalı yön daha önemli: alan gövdeye
    kazara sızarsa `/api/tahmin`in soğuk maliyeti sessizce ~38 sn artar.
    """
    kapali = client.get("/api/tahmin?limit=1").get_json()
    assert "genis_kesit" not in kapali, "istenmeden geniş kesit gövdeye girdi"

    for deger in ("1", "true", "evet", "yes", "TRUE", "Evet"):
        g = client.get(f"/api/tahmin?limit=1&genis={deger}").get_json()
        assert "genis_kesit" in g, f"?genis={deger} açmadı"

    for deger in ("0", "false", "hayir", "", "sacma"):
        g = client.get(f"/api/tahmin?limit=1&genis={deger}").get_json()
        assert "genis_kesit" not in g, f"?genis={deger} yanlışlıkla açtı"


def test_api_genis_govdesi_olculmus_isabeti_DUSURMEZ(client):
    """Geniş kesit istendiğinde dar ölçüm bloğu da gelmeli.

    Projenin kırmızı çizgisi `tahminler` ↔ `olculmus_isabet` ayrılmazlığı.
    Geniş blok o ikilinin YANINA gelir; birini ötekinin yerine koymak
    çizgiyi geniş kesit üzerinden delmek olurdu.
    """
    g = client.get("/api/tahmin?limit=1&genis=1").get_json()
    assert g["olculmus_isabet"]["olculdu"] is True
    assert "tahminler" in g and "uyarilar" in g
    gk = g["genis_kesit"]
    assert gk["olculdu"] is True
    assert gk["n_hafta"] > g["olculmus_isabet"]["n_hafta"], (
        "geniş kesit dar kesitten büyük olmalı")
