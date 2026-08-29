"""Model Arena'nın denetimi.

Arena bir model değil bir **karşılaştırma zemini**dir, bu yüzden testlerin
çoğu "sayı doğru mu"dan çok *"tablo kıyaslanabilir mi"* sorusunu kovalıyor:

- kayıtta aile başına tek temsilci var mı (çoklu test problemi)
- daha dar kesit isteyen aile sessizce düşmüş mü, yoksa gerekçesiyle
  yazılmış mı
- eğitilemeyip bir tabana düşen aday tabloda **işaretli** mi

Sonuncusu arenanın en kolay sessiz hatasıdır: `+0,0000` yazan bir satır
"ölçtük, fark yok" gibi okunur, oysa söylediği şey "model hiç koşmadı".

Korpus üzerindeki gerçek koşum burada YOK: 31 bin maçta on aile eğitmek
dakikalar sürer ve bu bir test değil bir ölçüm koşumudur
(`python -m spor_toto.arena`). Buradaki uçtan uca denetim sentetik bir
kesitte koşar.
"""

import pytest

from spor_toto.arena import cokme, disarida, kesit, notlar, rapor, roster
from spor_toto.evaluate import karsilastir, sezon_anahtari
from spor_toto.history import MATCH_COUNT, SYMBOLS
from spor_toto.predict import REFERANS_AD, DuzgunTahminci, PiyasaTahminci, Tahminci

ESIT = dict.fromkeys(SYMBOLS, 1 / 3)


def _girdi(week: int, results: str, sezon: str, tarih: str, probs=None) -> dict:
    return {
        "week": week, "close_date": tarih, "sezon": sezon, "results": results,
        "probs": list(probs) if probs else [dict(ESIT)] * len(results),
        "missing": 0, "usable": True,
    }


def _kesit() -> list[dict]:
    """Üç sezon × iki hafta, piyasanın gerçekten bilgi taşıdığı bir kurgu."""
    egilimli = [{"1": 0.5, "0": 0.3, "2": 0.2}] * MATCH_COUNT
    out = []
    for i, (sezon, yil) in enumerate((("2122", "2021"), ("2223", "2022"),
                                      ("2324", "2023"))):
        for j in range(2):
            out.append(_girdi(10 * i + j, "102" * 5, sezon,
                              f"{yil}-0{j + 1}-15", egilimli))
    return out


# ─── kayıt ────────────────────────────────────────────────────────────────────

def test_kayit_referanslarin_ucunu_de_tasir():
    """Zemin, naif ve çizgi olmadan tablo okunamaz."""
    adlar = [f().ad for _, f in roster()]
    for ad in ("duzgun", "sezon_sabiti", REFERANS_AD):
        assert ad in adlar, f"kayitta {ad} yok — tablo referanssiz kalir"


def test_kayit_aile_basina_tek_temsilci():
    """Aynı aile iki satırla girerse tablo çoklu test problemine döner."""
    aileler = [aile for aile, _ in roster()]
    assert len(aileler) == len(set(aileler)), f"tekrar eden aile: {aileler}"


def test_kademe_temsilcisi_son_basamak_ve_en_iyi_basamak_degil():
    """Kural: kademe kümülatif, temsilci SON basamak.

    "En iyi basamağı seç" kuralı ölçüme bakarak seçmek olurdu ve tam da
    §8'in uyardığı çoklu test hatasıdır. Bu test o kuralı koda bağlar.
    """
    from spor_toto.recalibrate import KADEMELER

    adlar = [f().ad for _, f in roster()]
    assert f"kalibre_{KADEMELER[-1]}" in adlar
    # Ara basamaklarin hicbiri arenada olmamali.
    for k in KADEMELER[:-1]:
        assert f"kalibre_{k}" not in adlar, f"ara basamak arenaya girmis: {k}"


def test_lightgbm_yoksa_agac_uydurulmaz():
    """Paket yoksa aile atlanır ve `disarida` bunu **söyler**."""
    from spor_toto.agac import HAS_LIGHTGBM

    adlar = [f().ad for _, f in roster()]
    if HAS_LIGHTGBM:
        assert "agac" in adlar
        assert "agac" not in disarida()
    else:
        assert "agac" not in adlar
        assert "lightgbm" in disarida()["agac"]


# ─── dışarıda kalanlar ────────────────────────────────────────────────────────

def test_dar_kesitli_aileler_gerekcesiyle_disarida():
    """Sessizce düşen aday yok: üçü de adıyla ve sebebiyle yazılı."""
    d = disarida()
    for ad in ("acilis", "bahisci_*", "elo"):
        assert ad in d, f"{ad} disarida listesinde yok"
        assert len(d[ad]) > 20, f"{ad}: gerekce bos gibi"


def test_disarida_kalanlar_kayitta_yok():
    """Bir aile hem arenada hem 'dışarıda' olamaz."""
    adlar = {f().ad for _, f in roster()}
    for ad in disarida():
        if ad.endswith("*") or "(" in ad:
            continue
        assert ad not in adlar, f"{ad} hem kayitta hem disarida"


# ─── kesit künyesi ────────────────────────────────────────────────────────────

def test_kupon_kesiti_tek_sezon_uyarisini_tasir():
    """Kupon kesitinde sezon dışarıda bırakmalı ölçüm kurulamaz."""
    _, grup, kunye = kesit(kupon=True, last=3)
    assert grup is None
    assert kunye["grup_olcusu"] == "hafta"
    assert kunye["uyari"], "tek sezon uyarisi dusmus"


def test_korpus_kesiti_sezon_gruplu():
    _, grup, kunye = kesit()
    assert grup is sezon_anahtari
    assert kunye["grup_olcusu"] == "sezon"
    assert len(kunye["sezonlar"]) >= 2


# ─── çökme tespiti — arenanın en kolay sessiz hatası ──────────────────────────

class PiyasaKopyasi(Tahminci):
    """Eğitilemeyip piyasaya düşmüş bir adayın taklidi."""

    ad = "kopya"
    aciklama = "test kurgusu: piyasayi oldugu gibi gecirir"

    def tahmin(self, hafta):
        return [dict(b) if b else dict(ESIT) for b in hafta["probs"]]


class GercekAday(Tahminci):
    """Piyasadan gerçekten ayrışan aday — tespitin yanlış ateşlememesi için."""

    ad = "gercek"
    aciklama = "test kurgusu: piyasayi hafifce kaydirir"

    def tahmin(self, hafta):
        out = []
        for b in hafta["probs"]:
            p = dict(b) if b else dict(ESIT)
            p = {"1": p["1"] + 0.05, "0": p["0"] - 0.03, "2": p["2"] - 0.02}
            out.append(p)
        return out


def test_cokme_piyasaya_dusen_adayi_yakalar():
    s = karsilastir([PiyasaTahminci, DuzgunTahminci, PiyasaKopyasi],
                    haftalar=_kesit(), grup=sezon_anahtari)
    assert cokme(s["tahminciler"]) == {"kopya": REFERANS_AD}


def test_cokme_duzgune_duseni_de_yakalar():
    class DuzgunKopyasi(Tahminci):
        ad = "duzgun_kopya"
        aciklama = "test kurgusu"

        def tahmin(self, hafta):
            return [dict(ESIT)] * len(hafta["results"])

    s = karsilastir([PiyasaTahminci, DuzgunTahminci, DuzgunKopyasi],
                    haftalar=_kesit(), grup=sezon_anahtari)
    assert cokme(s["tahminciler"]) == {"duzgun_kopya": "duzgun"}


def test_cokme_gercek_adayda_yanlis_atesle_mez():
    """Kuralın diğer ucu: ayrışan aday çökmüş sayılmaz."""
    s = karsilastir([PiyasaTahminci, DuzgunTahminci, GercekAday],
                    haftalar=_kesit(), grup=sezon_anahtari)
    assert cokme(s["tahminciler"]) == {}


def test_cokme_tabanlarin_kendisini_isaretlemez():
    """`piyasa` ve `duzgun` tanım gereği kendileridir, çökmüş değil."""
    s = karsilastir([PiyasaTahminci, DuzgunTahminci],
                    haftalar=_kesit(), grup=sezon_anahtari)
    assert cokme(s["tahminciler"]) == {}


# ─── notlar ───────────────────────────────────────────────────────────────────

def test_ileri_kipte_okuma_sartlari_eklenir():
    """İleri yürüyüş notları olmadan tablo yanlış okunur."""
    az = notlar(ileri=False)
    cok = notlar(ileri=True)
    assert len(cok) > len(az)
    metin = " ".join(cok)
    assert "atlanan_gruplar" in metin
    assert "yigin" in metin, "yiginin ilk grupta tabana dustugu uyarisi yok"


# ─── uçtan uca — sentetik kesitte ─────────────────────────────────────────────

@pytest.fixture()
def sentetik_arena(monkeypatch):
    """Arena'yı sentetik kesitte koştur — korpus dokunulmaz."""
    monkeypatch.setattr(
        "spor_toto.arena.kesit",
        lambda kupon=False, last=None: (
            _kesit(), sezon_anahtari,
            {"kaynak": "test", "grup_olcusu": "sezon", "uyari": None}))
    monkeypatch.setattr(
        "spor_toto.arena.roster",
        lambda: [("piyasa", PiyasaTahminci), ("zemin", DuzgunTahminci),
                 ("kopya", PiyasaKopyasi)])
    return rapor


def test_rapor_govdesi_kesit_kayit_disarida_ve_notlari_tasir(sentetik_arena):
    s = sentetik_arena()
    for alan in ("kesit", "kayit", "disarida", "notlar", "cokme", "kip",
                 "soru", "tahminciler", "referans"):
        assert alan in s, f"govdede {alan} yok"
    assert s["referans"] == REFERANS_AD
    assert s["kip"] == "disarida_birakmali"


def test_rapor_her_satira_cokme_alani_koyar(sentetik_arena):
    """Alan HER satırda bulunmalı — okuyan 'bu alan var mıydı' diye sormasın."""
    s = sentetik_arena()
    for t in s["tahminciler"]:
        assert "cokme" in t
    coken = {t["ad"]: t["cokme"] for t in s["tahminciler"] if t["cokme"]}
    assert coken == {"kopya": REFERANS_AD}


def test_rapor_cokme_varsa_notlara_uyari_ekler(sentetik_arena):
    """Çökme sessiz olmaz: tabloda işaret, notlarda cümle."""
    s = sentetik_arena()
    assert any("COKME" in n for n in s["notlar"])


def test_ileri_kip_atlanan_grubu_bildirir(sentetik_arena):
    s = sentetik_arena(ileri=True)
    assert s["kip"] == "ileri_yuruyus"
    assert s["atlanan_gruplar"] == ["2122"]
    # Kesit sayilari OLCULEN haftadan okunur, girdiden degil.
    assert s["n_hafta"] == 4
    assert s["n_hafta_girdi"] == 6
