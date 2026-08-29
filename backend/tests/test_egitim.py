"""Eğitim korpusunun denetimi ve **istatistik katmanından ayrımı**.

Bu dosyanın en önemli testleri `test_ayrim_*` ile başlayanlardır. Korpus bir
ürün kararıyla istatistik katmanından ayrı tutuluyor: `/istatistik` Spor Toto
kuponunun sezonunu anlatır (41 hafta, 615 maç) ve korpustan hiçbir sayı oraya
girmez. Bu ayrım yorumla değil, testle korunur — aksi halde bir sonraki
"küçük ekleme" onu sessizce bozar.
"""

import pytest

from spor_toto.egitim import EN_AZ_MAC, korpus_haftalari, korpus_yukle, ozet
from spor_toto.evaluate import (
    capraz_olc,
    olculebilir_haftalar,
    sezon_anahtari,
)
from spor_toto.history import SYMBOLS
from spor_toto.predict import (
    DuzgunTahminci,
    PiyasaTahminci,
    SezonSabitiTahminci,
    mac_sayisi,
)
from spor_toto.recalibrate import KalibreTahminci


@pytest.fixture(scope="module")
def haftalar():
    h = korpus_haftalari()
    if not h:
        pytest.skip("egitim korpusu yok — once scripts/build_egitim.py")
    return h


# ─── ayrım bekçisi ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("modul", [
    "spor_toto.history", "spor_toto.odds", "spor_toto.payloads",
    "spor_toto.backtest", "spor_toto.core", "spor_toto.health",
    # `fiyatlar` de istatistik katmanidir: arsivin fiyat sutunlarini okur,
    # korpusu tanimaz. Listeye eklendi cunku eklenmeseydi bekci onu
    # korumazdi ve ilk yazildiginda gercekten korpusa atif yapiyordu.
    "spor_toto.fiyatlar",
])
def test_ayrim_istatistik_katmani_korpusu_import_etmez(modul):
    """İstatistik/motor katmanı eğitim korpusunu tanımaz.

    Ürün kararı: korpus **yalnızca tahmin katmanına** aittir. Bir gün biri
    `history.py` içinde korpustan bir sayı okumak isterse bu test kırılır ve
    kararın bilinçli olduğunu hatırlatır.
    """
    import importlib
    m = importlib.import_module(modul)
    kaynak = getattr(m, "__file__", "")
    with open(kaynak, encoding="utf-8") as fh:
        metin = fh.read()
    assert "egitim" not in metin.replace("egitim_", ""), (
        f"{modul} egitim korpusuna atif yapiyor — ayrim bozuluyor")


def test_ayrim_stats_govdesi_korpustan_etkilenmez():
    """`/api/stats` gövdesi korpusa dair hiçbir alan taşımaz."""
    from spor_toto.payloads import stats_payload
    govde = stats_payload(None)
    import json
    metin = json.dumps(govde, ensure_ascii=False).lower()
    for yasak in ("korpus", "egitim_korpus", "football-data.co.uk/mmz4281/2122"):
        assert yasak not in metin, f"stats govdesinde korpus izi: {yasak}"


def test_ayrim_korpus_kupon_bilesimi_tasimaz():
    """Korpus kupon maçı bilgisi taşımaz — kaplama katmanına karışmaz."""
    satirlar = korpus_yukle()
    if not satirlar:
        pytest.skip("korpus yok")
    for alan in ("no", "week", "kupon"):
        assert alan not in satirlar[0], f"korpus kupon alani tasiyor: {alan}"


# ─── korpus sözleşmesi ────────────────────────────────────────────────────────

def test_korpus_ozeti_tutarli(haftalar):
    o = ozet()
    assert o["mac"] > 10_000, "korpus beklenenden kucuk"
    assert o["lig"] >= 20
    assert sum(o["kod_dagilimi"].values()) == o["mac"]


def test_varsayilan_korpus_guncel_sezonu_icermez():
    """Sızıntı bekçisi: kupon değerlendirme seti 2025/26'dan gelir.

    Korpusa o sezon katılırsa eğitim ve sınav aynı maçları paylaşır.
    `build_egitim.py` varsayılanı bilerek geçmiş sezonlarla sınırlar.
    """
    o = ozet()
    if not o["sezon"]:
        pytest.skip("korpus yok")
    assert "2526" not in o["sezon"], "korpus guncel sezonu iceriyor — sizinti riski"


def test_hafta_sozlesmesi(haftalar):
    """Korpus haftaları `evaluate` koşumunun beklediği şekli taşır."""
    for h in haftalar[:20]:
        assert h["usable"] is True
        assert h["missing"] == 0
        assert len(h["results"]) == len(h["probs"]) == len(h["ozellikler"])
        assert len(h["results"]) >= EN_AZ_MAC
        assert set(h["results"]) <= set(SYMBOLS)
        assert h["sezon"]
        for p in h["probs"]:
            assert pytest.approx(sum(p.values()), abs=1e-9) == 1.0


def test_ozellikler_lig_ve_favori_tasir(haftalar):
    o = haftalar[0]["ozellikler"][0]
    assert o["lig"]
    assert o["favori"] in SYMBOLS
    assert o["favori_oran"] > 1.0


def test_sezona_gore_suzme(haftalar):
    tek = korpus_haftalari(sezonlar_=["2425"])
    assert tek, "2425 sezonu bulunamadi"
    assert {h["sezon"] for h in tek} == {"2425"}
    assert len(tek) < len(haftalar)


def test_en_az_mac_esigi_uygulanir():
    genis = korpus_haftalari(en_az_mac=1)
    dar = korpus_haftalari(en_az_mac=50)
    if not genis:
        pytest.skip("korpus yok")
    assert len(dar) <= len(genis)
    assert all(len(h["results"]) >= 50 for h in dar)


def test_korpus_haftalari_paylasilan_kaydi_korur():
    """**Önbelleğin bekçisi.** `korpus_haftalari` aynı listeyi geri verir.

    Çağrı 31.103 satırı gezip 217.701 kez marj arındırdığı için önbelleklendi
    (tek geçiş ~12 sn, suite'te onlarca çağrı). Bunun bedeli şu: dönen kayıt
    artık **paylaşılıyor**. Bir çağıran bir haftanın alanını değiştirirse
    öteki çağıranların gördüğü veri sessizce bozulur — ve sessiz olur, çünkü
    bugün `probs` ile `kapanis_probs` aynı çıkıyor.

    Kayda yazması gereken (`cizgi.kesit`, `bahisci.kesit`) kopyasını alır.
    Bu test o kuralı korur.
    """
    from spor_toto import bahisci, cizgi

    a = korpus_haftalari(sezonlar_=["2425"])
    b = korpus_haftalari(sezonlar_=["2425"])
    if not a:
        pytest.skip("egitim korpusu yok")
    assert a is b, "onbellek calismiyor — cagri basina yeniden hesaplaniyor"

    for kesit_fn, bayrak in ((cizgi.kesit, "cizgi_gerekli"),
                             (bahisci.kesit, "bahisci_gerekli")):
        paylasilan = korpus_haftalari(sezonlar_=["2425"], **{bayrak: True})
        if not paylasilan:
            continue
        once = [[dict(p) for p in h["probs"]] for h in paylasilan]
        kendi = kesit_fn(sezonlar_=["2425"])
        sonra = [[dict(p) for p in h["probs"]]
                 for h in korpus_haftalari(sezonlar_=["2425"], **{bayrak: True})]
        assert once == sonra, (
            f"{kesit_fn.__module__}.kesit paylasilan kaydin uzerine yazdi")
        assert kendi is not paylasilan


def test_korpus_yoksa_bos_doner(tmp_path):
    yok = tmp_path / "olmayan.csv"
    assert korpus_yukle(str(yok)) == []
    assert korpus_haftalari(yol=str(yok)) == []


# ─── değişken uzunluk ─────────────────────────────────────────────────────────

def test_mac_sayisi_haftadan_okunur(haftalar):
    h = haftalar[0]
    assert mac_sayisi(h) == len(h["results"]) > 15


@pytest.mark.parametrize("fabrika", [DuzgunTahminci, SezonSabitiTahminci,
                                     PiyasaTahminci,
                                     lambda: KalibreTahminci("bias")])
def test_tahminciler_korpus_haftasinda_dogru_uzunluk(fabrika, haftalar):
    """Sabit 15 varsayımı kalmamalı — korpus haftaları ~170 maç taşır."""
    t = fabrika()
    t.egit(haftalar[:8])
    tahminler = t.tahmin(haftalar[0])
    assert len(tahminler) == len(haftalar[0]["results"])


# ─── sezon dışarıda bırakmalı ─────────────────────────────────────────────────

def test_sezon_anahtari_grubu_dogru_kurar(haftalar):
    anahtarlar = {sezon_anahtari(h) for h in haftalar}
    assert anahtarlar == set(ozet()["sezon"])


def test_sezon_grubu_tum_sezonu_egitimden_cikarir(haftalar):
    """Grup dışarıda bırakma, aynı sezonun **bütün** haftalarını çıkarmalı.

    Yalnızca ölçülen haftayı çıkarmak yetmez: aynı sezonun başka haftaları da
    bilgi sızdırır. Sızıntı testi olarak `sezon_sabiti` kullanılır — dışarıda
    bırakılan sezonun dağılımını görmemiş olmalı.
    """
    from spor_toto.evaluate import hafta_disarida_birak

    hedef = haftalar[0]["sezon"]
    kayitlar = hafta_disarida_birak(SezonSabitiTahminci, haftalar, sezon_anahtari)
    assert len(kayitlar) == len(haftalar)

    # Elle: hedef sezon disinda egitilen model, hedef sezonun dagilimini bilmez
    disari = [h for h in haftalar if h["sezon"] != hedef]
    t = SezonSabitiTahminci()
    t.egit(disari)
    beklenen = t.tahmin(haftalar[0])[0]

    hepsi = SezonSabitiTahminci()
    hepsi.egit(haftalar)
    assert beklenen != hepsi.tahmin(haftalar[0])[0], "sezon ayrimi fark yaratmadi"


# ─── çapraz ölçüm ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def capraz(haftalar):
    return capraz_olc([PiyasaTahminci, lambda: KalibreTahminci("bias")],
                      haftalar, olculebilir_haftalar())


def test_capraz_egitim_ve_test_ayri(capraz):
    assert capraz["n_egitim_mac"] > 10_000
    assert capraz["n_mac"] == 540
    assert capraz["n_hafta"] == 36


def test_capraz_referans_kendisiyle_karsilastirilmaz(capraz):
    piyasa = next(s for s in capraz["tahminciler"] if s["ad"] == "piyasa")
    assert piyasa["fark"] is None
    assert piyasa["brier"] == pytest.approx(0.5747, abs=0.002)


def test_capraz_ic_kayitlar_sizmaz(capraz):
    assert all("_kayitlar" not in s for s in capraz["tahminciler"])


def test_capraz_referanssiz_liste_cokmez(haftalar):
    r = capraz_olc([DuzgunTahminci], haftalar[:5], olculebilir_haftalar()[:5])
    assert r["tahminciler"][0]["gecti"] is False
    assert r["tahminciler"][0]["fark"] is None


# ─── takım formu (T5) ─────────────────────────────────────────────────────────

def _mac(tarih: str, ev: str, dep: str, kod: str, ev_is: int = 5,
         dep_is: int = 5) -> dict:
    return {"sezon": "9999", "lig": "XX", "tarih": tarih, "iso_yil": 2099,
            "iso_hafta": 1, "ev": ev, "dep": dep, "kod": kod,
            "oranlar": {"1": 2.0, "0": 3.0, "2": 4.0},
            "ev_isabet": ev_is, "dep_isabet": dep_is,
            "ev_sut": ev_is, "dep_sut": dep_is}


def test_form_gelecegi_gormez():
    """**Sızıntı bekçisi** — modülün varlık sebebi.

    A takımı 5 maç kazanıyor, 6. maçı kaybediyor. 6. maçtaki formu o 5
    galibiyeti yansıtmalı (pozitif); kendi yenilgisini görmemeli. Sızıntı
    olsaydı 6. maçın formu düşerdi.

    Bu sızıntı sessizdir: model geleceği görür, skor mucizevi çıkar, gerçek
    maçta hiçbir işe yaramaz.
    """
    from spor_toto.egitim import _form_tablosu

    maclar = [_mac(f"2099-01-0{i}", "A", f"R{i}", "1") for i in range(1, 6)]
    maclar.append(_mac("2099-01-06", "A", "Z", "2"))          # A kaybediyor
    maclar += [_mac(f"2099-01-0{i}", "Z", f"Q{i}", "0") for i in range(1, 6)]

    form = _form_tablosu(maclar)
    alti = form[5]
    assert alti["form_var"] is True
    # A: 5 galibiyet = 3,0 puan/mac · Z: 5 beraberlik = 1,0 → fark +2,0
    assert alti["form_puan_farki"] == pytest.approx(2.0), (
        "6. macin formu kendi sonucunu gormus olabilir")


def test_form_yeterli_gecmis_yoksa_isaretlenir():
    """Doktrin 2: eksik geçmiş uydurulmaz, `form_var=False` ile bildirilir."""
    from spor_toto.egitim import _form_tablosu

    form = _form_tablosu([_mac("2099-01-01", "A", "B", "1")])
    assert form[0]["form_var"] is False
    assert form[0]["form_puan_farki"] == 0.0


def test_form_istatistiksiz_mac_gecmise_katilmaz():
    """Şut verisi olmayan maç formu kirletmemeli (doktrin 2)."""
    from spor_toto.egitim import _form_tablosu

    maclar = [_mac(f"2099-01-0{i}", "A", f"R{i}", "1") for i in range(1, 6)]
    for m in maclar:
        m["ev_isabet"] = None                      # istatistik yok
    maclar.append(_mac("2099-01-06", "A", "Z", "1"))
    form = _form_tablosu(maclar)
    assert form[5]["form_var"] is False, "istatistiksiz maclar gecmise katilmis"


def test_form_deterministik():
    from spor_toto.egitim import _form_tablosu
    maclar = [_mac(f"2099-01-{i:02d}", "A", f"R{i}", "1") for i in range(1, 9)]
    assert _form_tablosu(maclar) == _form_tablosu(list(maclar))


def test_form_gercek_veride_ham_sinyal_tasiyor(haftalar):
    """Özellik bozuk değil mi — ham sinyal yoksa ölçüm anlamsız olurdu.

    Bu bir *bulgu* testi değil, bir *sağlama*: form ile sonuç arasında ham
    bir ilişki olmalı. Olmasaydı "form yardım etmiyor" sonucu, özelliğin
    bozuk olmasından da kaynaklanabilirdi.
    """
    ciftler = [(o, hf["results"][i]) for hf in haftalar
               for i, o in enumerate(hf["ozellikler"]) if o["form_var"]]
    assert len(ciftler) > 10_000

    iyi = [k for o, k in ciftler if o["form_puan_farki"] > 1.0]
    kotu = [k for o, k in ciftler if o["form_puan_farki"] < -1.0]
    def ev_orani(g):
        return sum(1 for k in g if k == "1") / len(g)

    assert ev_orani(iyi) > ev_orani(kotu) + 0.15, "form ham sinyal tasimiyor"


def test_kupon_haftasinda_form_notr():
    """Kupon haftaları form taşımaz; nötr 0 döner, uydurma değer değil."""
    from spor_toto.recalibrate import _mac_ozellikleri
    kupon = olculebilir_haftalar()[0]
    for o in _mac_ozellikleri(kupon):
        assert o["form_puan_farki"] == 0.0
        assert o["form_isabet_farki"] == 0.0


def test_form_kademesi_bant_ustune_iki_sutun_ekler():
    from spor_toto.recalibrate import KalibreTahminci
    h = korpus_haftalari(sezonlar_=["2425"])
    bant = KalibreTahminci("bant")
    bant.egit(h)
    form = KalibreTahminci("form")
    form.egit(h)
    assert len(form.katsayilar) == len(bant.katsayilar) + 2
