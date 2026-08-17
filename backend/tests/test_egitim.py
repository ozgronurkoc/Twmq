"""Eğitim korpusunun denetimi ve **istatistik katmanından ayrımı**.

Bu dosyanın en önemli testleri `test_ayrim_*` ile başlayanlardır. Korpus bir
ürün kararıyla istatistik katmanından ayrı tutuluyor: `/istatistik` Spor Toto
kuponunun sezonunu anlatır (41 hafta, 615 maç) ve korpustan hiçbir sayı oraya
girmez. Bu ayrım yorumla değil, testle korunur — aksi halde bir sonraki
"küçük ekleme" onu sessizce bozar.
"""

import pytest

from spor_toto import egitim
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
