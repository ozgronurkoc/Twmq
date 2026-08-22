"""Süper Toto haftalık boru hattı — `scripts/super_toto_*.py`.

Bu scriptler canlı sezonun tek yolu ve **birleştirildiklerinde hiç testleri
yoktu**: 1.900 satır Python, CI'da hiç çalışmıyordu. Buradaki testler
bulguları değil **boru hattını** korur — bir hafta dosyası okunduğunda
olasılıklar doğru mu kuruluyor, kaçak dağılımı gerçekten bir dağılım mı,
en iyi kolon sayımı doğru mu.

Scriptler paket değil; `super_toto_degerlendir._hafta_modulu`'nün kendi
kullandığı `spec_from_file_location` yolu burada da kullanılır — test,
üretimin yüklediğinden başka bir şeyi yüklememelidir.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data" / "super_toto" / "2026_27"

pytestmark = pytest.mark.skipif(
    not (VERI / "hafta_01.json").exists(),
    reason="super toto hafta verisi yok")


def _modul(ad: str):
    spec = importlib.util.spec_from_file_location(
        f"st_{ad}", str(KOK / "scripts" / f"super_toto_{ad}.py"))
    mod = importlib.util.module_from_spec(spec)
    eski = sys.argv
    sys.argv = ["x"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = eski
    return mod


@pytest.fixture(scope="module")
def hafta():
    return _modul("hafta")


@pytest.fixture(scope="module")
def deg():
    return _modul("degerlendir")


# ─── hafta_yukle ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("no", [1, 2])
def test_hafta_okunur_ve_olasiliklar_bire_toplanir(hafta, no):
    d = hafta.hafta_yukle("2026_27", no)
    assert len(d["matches"]) == 15
    for m in d["matches"]:
        assert sum(m["probs"].values()) == pytest.approx(1.0, abs=1e-9)
        assert sum(m["play"].values()) == pytest.approx(1.0, abs=1e-9)
        assert set(m["probs"]) == {"1", "0", "2"}


def test_orani_olmayan_mac_esit_dagitilir(hafta):
    """9. maçın oranı ilan edilmemişti. Bu bir TAHMİN değil, bilgi yokluğu.

    Boru hattı onu 1/3–1/3–1/3 taşır; kural da eşiğin altında kaldığı için
    otomatik üçlü yapar. Buradaki değişmez, o maça uydurma bir olasılık
    atanmamasıdır.
    """
    d = hafta.hafta_yukle("2026_27", 2)
    m = next(x for x in d["matches"] if x["no"] == 9)
    assert m["odds_yok"] is True
    assert m["odds"] is None
    assert m["fav"] is None
    assert m["margin"] == 0.0
    for s in ("1", "0", "2"):
        assert m["probs"][s] == pytest.approx(1 / 3)


def test_marj_ortalamasi_oransiz_maci_saymaz(hafta):
    """Oransız maçın marjı 0'dır; ortalamaya girseydi sahte biçimde düşerdi."""
    d = hafta.hafta_yukle("2026_27", 2)
    prof = hafta.hafta_profili(d, hafta.gecen_sezon_ref())
    oranli = [m for m in d["matches"] if not m["odds_yok"]]
    beklenen = 100 * sum(m["margin"] for m in oranli) / len(oranli)
    assert prof["avg_margin_pct"] == pytest.approx(beklenen)
    assert prof["avg_margin_pct"] > 10, "iddaa marji cift haneli olmali"


def test_eksik_mac_sayisi_reddedilir(hafta, tmp_path, monkeypatch):
    d = json.loads((VERI / "hafta_01.json").read_text(encoding="utf-8"))
    d["matches"] = d["matches"][:14]
    kok = tmp_path / "2026_27"
    kok.mkdir()
    (kok / "hafta_09.json").write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(hafta, "VERI_KOK", tmp_path)
    with pytest.raises(SystemExit, match="15 maç"):
        hafta.hafta_yukle("2026_27", 9)


def test_olmayan_hafta_sessizce_gecmez(hafta):
    with pytest.raises(SystemExit, match="Hafta dosyası yok"):
        hafta.hafta_yukle("2026_27", 41)


# ─── kupon ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("no", [1, 2])
def test_kupon_kume_ici_olasiligi_tutarli(hafta, no):
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU
    d = hafta.hafta_yukle("2026_27", no)
    k = hafta.kupon_kur(d, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
    assert len(k["picks"]) == 15
    assert 0.0 < k["in_set_p"] < 1.0
    # Kume-ici, tek tek maclarin secim-ici olasiliklarinin carpimi olmali.
    beklenen = 1.0
    for m, sec in zip(d["matches"], k["picks"]):
        beklenen *= sum(m["probs"][s] for s in sec)
    assert k["in_set_p"] == pytest.approx(beklenen)
    assert len(k["banko"]) + len(k["cift"]) + len(k["uclu"]) == 15


def test_oransiz_mac_otomatik_uclu_olur(hafta):
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU
    d = hafta.hafta_yukle("2026_27", 2)
    k = hafta.kupon_kur(d, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
    assert 9 in k["uclu"], "orani olmayan mac uclu yapilmali"


# ─── kaçak dağılımı (Poisson-binom) ───────────────────────────────────────────

def test_kacak_dagilimi_bir_dagilimdir(deg):
    d = deg.kacak_dagilimi([0.1, 0.5, 0.9, 0.25])
    assert len(d) == 5
    assert sum(d) == pytest.approx(1.0)
    assert all(v >= 0 for v in d)


def test_kacak_dagilimi_uc_durumlar(deg):
    assert deg.kacak_dagilimi([]) == [1.0]
    kesin = deg.kacak_dagilimi([1.0, 1.0])
    assert kesin[2] == pytest.approx(1.0)
    hic = deg.kacak_dagilimi([0.0, 0.0, 0.0])
    assert hic[0] == pytest.approx(1.0)


def test_kacak_beklentisi_olasilik_toplamina_esit(deg):
    """Poisson-binom'un ortalaması, bileşen olasılıklarının toplamıdır."""
    p = [0.1, 0.35, 0.6, 0.05, 0.9]
    d = deg.kacak_dagilimi(p)
    assert sum(i * v for i, v in enumerate(d)) == pytest.approx(sum(p))


# ─── en iyi kolon ─────────────────────────────────────────────────────────────

def test_en_iyi_kolon_tam_isabeti_bulur(deg):
    secim = ["1"] * 8 + ["12"] * 7
    assert deg.en_iyi_kolon(secim, "1" * 15) == 15


def test_en_iyi_kolon_kume_disinda_da_dogru_sayar(deg):
    """Gerçek sonuç seçim kümesinin dışındayken bile doğru cevap vermeli.

    Motorun kendi skorlayıcısına bağlanılmamasının sebebi bu: küme dışı
    sonuç onun tanımlı olmadığı yerdir.
    """
    secim = ["1"] * 8 + ["12"] * 7
    gercek = "0" + "1" * 14          # ilk mac banko ve kacti
    assert deg.en_iyi_kolon(secim, gercek) == 14


def test_en_iyi_kolon_hicbiri_tutmazsa_sifir(deg):
    secim = ["1"] * 8 + ["12"] * 7
    assert deg.en_iyi_kolon(secim, "0" * 15) == 0


# ─── kupon değerlendirme ve kıyas ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def hafta1(hafta):
    return hafta.hafta_yukle("2026_27", 1)


def test_degerlendirme_kacaklari_dogru_sayar(deg, hafta1):
    kupon = json.loads((VERI / "hafta_01_kupon.json").read_text(encoding="utf-8"))
    s = deg.kupon_degerlendir(hafta1, kupon["variants"][0]["picks"])
    gercek = hafta1["meta"]["results"]
    beklenen = [i + 1 for i, (p, g)
                in enumerate(zip(kupon["variants"][0]["picks"], gercek))
                if g not in p]
    assert s["misses"] == beklenen
    assert s["miss_count"] == len(beklenen)
    assert s["best"] == 15 - len(beklenen)
    assert sum(s["dist"]) == pytest.approx(1.0)
    assert 0.0 <= s["p_at_least_actual"] <= 1.0


def test_kiyas_birlesimi_iki_kupondan_genis(deg, hafta1):
    kupon = json.loads((VERI / "hafta_01_kupon.json").read_text(encoding="utf-8"))
    varyantlar = {v["label"]: v["picks"] for v in kupon["variants"]}
    etiketler = list(varyantlar)
    if len(etiketler) < 2:
        pytest.skip("kiyas icin iki varyant gerekli")
    a, b = varyantlar[etiketler[0]], varyantlar[etiketler[1]]
    k = deg.kupon_kiyas(hafta1, a, b)
    for birlesim, x, y in zip(k["union_picks"], a, b):
        assert set(birlesim) == set(x) | set(y)
    assert k["union_best"] == 15 - len(k["union_misses"])
    assert k["union_space"] >= 1


def test_en_iyi_kolon_az_cifteli_kuponda_cokmez(deg):
    """`solve_fix16` en az 7 çifte ister; kural daha azını üretebilir.

    Shin arındırmasına geçildikten sonra favori daha çok pay aldığı için
    banko sayısı arttı ve bu hâl daha olası oldu. Sonuç değerlendirmesinin
    o haftada çökmesi, ölçümün en çok gerektiği anda kaybolması olurdu.
    """
    secim = ["1"] * 12 + ["12"] * 3          # 3 cifte — fix16 kurulamaz
    assert deg.en_iyi_kolon(secim, "1" * 15) == 15
    # Son uc mac cifte ve "2"yi kapsiyor; ilk on iki banko kacti.
    assert deg.en_iyi_kolon(secim, "0" * 12 + "2" * 3) == 3
    assert deg.en_iyi_kolon(secim, "0" * 15) == 0
    assert deg.en_iyi_kolon(secim, "1" * 14 + "2") == 15


# ─── veri kalite kapısı ───────────────────────────────────────────────────────

def test_kapi_kuskulu_marji_yakalar(hafta):
    """2. haftanın 4. maçını **insan** yakalamıştı; artık kod da yakalıyor."""
    d = hafta.hafta_yukle("2026_27", 2)
    uyarilar = d["meta"]["uretilen_uyarilar"]
    assert any("4. maç" in u and "KUŞKULU" in u for u in uyarilar), uyarilar


def test_kapi_temiz_haftada_susar(hafta):
    d = hafta.hafta_yukle("2026_27", 1)
    assert d["meta"]["uretilen_uyarilar"] == []


def test_elle_yazilan_uyarilar_korunur(hafta):
    """Kod insanı düzeltmez, insan da kodu susturmaz — ikisi yan yana durur."""
    d = hafta.hafta_yukle("2026_27", 2)
    assert len(d["meta"]["data_warnings"]) >= 3
    assert "uretilen_uyarilar" in d["meta"]
    assert d["meta"]["data_warnings"] is not d["meta"]["uretilen_uyarilar"]


def _sahte(**degisiklik):
    mac = {"no": 1, "league": "T1", "home": "A", "away": "B",
           "odds": {"1": 2.0, "0": 3.4, "2": 3.6},
           "play_pct": {"1": 50, "0": 30, "2": 20}}
    mac.update(degisiklik)
    digerleri = [{"no": i, "league": "T1", "home": "C", "away": "D",
                  "odds": {"1": 2.0, "0": 3.4, "2": 3.6},
                  "play_pct": {"1": 50, "0": 30, "2": 20}}
                 for i in range(2, 16)]
    return {"meta": {}, "matches": [mac] + digerleri}


@pytest.mark.parametrize("degisiklik,beklenen", [
    ({"odds": {"1": 1.05, "0": 1.05, "2": 1.05}}, "marj"),
    ({"odds": {"1": 0.9, "0": 3.4, "2": 3.6}}, "1.00'den küçük"),
    ({"play_pct": {"1": 50, "0": 30}}, "eksik"),
    ({"play_pct": {"1": 10, "0": 10, "2": 10}}, "100'den uzak"),
    ({"league": ""}, "lig etiketi"),
])
def test_kapi_bozuk_satirlari_isaretler(hafta, degisiklik, beklenen):
    uyarilar = hafta.dogrula(_sahte(**degisiklik))
    assert any(beklenen in u for u in uyarilar), (degisiklik, uyarilar)


def test_kapi_bozuk_sonuc_dizisini_yakalar(hafta):
    d = _sahte()
    d["meta"]["results"] = "0121"
    assert any("sonuç dizisi bozuk" in u for u in hafta.dogrula(d))
    d["meta"]["results"] = "1" * 14 + "X"
    assert any("sonuç dizisi bozuk" in u for u in hafta.dogrula(d))


def test_kapi_veriyi_degistirmez(hafta):
    """Uyarı üretir, onarmaz — belirsiz veri uydurulmaz (veri doktrini 2)."""
    d = _sahte(odds={"1": 1.05, "0": 1.05, "2": 1.05})
    once = json.dumps(d["matches"], sort_keys=True)
    hafta.dogrula(d)
    assert json.dumps(d["matches"], sort_keys=True) == once


# ─── sezon defteri ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sezon():
    return _modul("sezon")


def test_defter_girilmis_haftalari_bulur(sezon):
    assert sezon.haftalari_bul("2026_27") == [1, 2]


def test_defter_kupon_dosyasini_hafta_sanmaz(sezon):
    """`hafta_01_kupon.json` bir hafta dosyası değildir; listeye girmemeli."""
    assert all(isinstance(x, int) for x in sezon.haftalari_bul("2026_27"))


def test_defter_sonucsuz_haftayi_olcume_katmaz(sezon):
    o = sezon.topla("2026_27")
    assert o["hafta_girilmis"] == 2
    assert o["hafta_olculen"] == 1
    assert o["mac"] == 15
    ikinci = next(h for h in o["haftalar"] if h["hafta"] == 2)
    assert ikinci["sonuc_var"] is False
    assert "brier" not in ikinci


def test_defter_uretilen_uyarilari_sayar(sezon):
    o = sezon.topla("2026_27")
    ikinci = next(h for h in o["haftalar"] if h["hafta"] == 2)
    assert ikinci["uyari"] >= 4, "elle + kod uyarilarinin toplami"


def test_defter_yeterlilik_notunu_her_zaman_yazar(sezon):
    """Bu satır kaldırılmamalı: 5-10 hafta sonra kural değiştirme baskısına
    karşı tek savunma, örneklemin ne diyemeyeceğinin yazılı olmasıdır."""
    y = sezon.topla("2026_27")["yeterlilik"]
    assert y["karar_verebilir"] is False
    assert y["yari_genislik"] > y["aranan_fark"]
    assert y["gerekli_mac"] > 615
    assert "kural değiştirmek için değil" in y["not"]


@pytest.mark.parametrize("n,karar", [(15, False), (615, False), (10 ** 7, True)])
def test_yeterlilik_orneklemle_birlikte_buyur(sezon, n, karar):
    assert sezon.yeterlilik_notu(n)["karar_verebilir"] is karar


def test_defter_oransiz_maci_kalibrasyona_sokmaz(sezon):
    """1/3–1/3–1/3 bir tahmin değil, bilgi yokluğudur; eğriyi kirletmemeli."""
    o = sezon.topla("2026_27")
    for r in o["kovalar"]:
        assert r["ga_alt"] <= r["gercek"] <= r["ga_ust"]
        assert r["n"] >= sezon.EN_AZ_KOVA


# ─── arayüz beslemesi ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def besleme():
    return _modul("frontend")


def test_besleme_dosyasi_guncel(besleme):
    """Besleme eskirse sayfa sessizce yanlış veri gösterir.

    CI'da da koşuyor (`--kontrol`); burada olması, testi çalıştıran kişinin
    veri girip beslemeyi yenilemeyi unuttuğunu hemen görmesi için.
    """
    if not besleme.CIKTI.exists():
        pytest.fail("frontend/lib/super-toto-veri.json yok — "
                    "python scripts/super_toto_frontend.py")
    beklenen = besleme._metin(besleme.uret("2026_27"))
    mevcut = besleme.CIKTI.read_text(encoding="utf-8")
    assert mevcut == beklenen, (
        "besleme guncel degil — python scripts/super_toto_frontend.py")


def test_besleme_backend_verisiyle_ayni_haftalari_tasir(besleme, sezon):
    g = besleme.uret("2026_27")
    assert [w["week"] for w in g["weeks"]] == sezon.haftalari_bul("2026_27")
    for w in g["weeks"]:
        assert len(w["matches"]) == 15


def test_besleme_olasiliklari_bire_toplanir(besleme):
    for w in besleme.uret("2026_27")["weeks"]:
        for m in w["matches"]:
            assert sum(m["probs"].values()) == pytest.approx(1.0, abs=2e-4)
            assert sum(m["play"].values()) == pytest.approx(1.0, abs=2e-4)


def test_besleme_iki_uyari_listesini_ayri_tasir(besleme):
    """Kod insanı düzeltmez, insan da kodu susturmaz — arayüz de ayrı gösterir."""
    w2 = next(w for w in besleme.uret("2026_27")["weeks"] if w["week"] == 2)
    assert w2["warnings_manual"]
    assert w2["warnings_generated"]
    assert w2["warnings_manual"] != w2["warnings_generated"]


def test_besleme_sonucsuz_haftada_sonuc_uydurmaz(besleme):
    w2 = next(w for w in besleme.uret("2026_27")["weeks"] if w["week"] == 2)
    assert w2["results"] is None
    assert all(m["result"] is None for m in w2["matches"])


def test_besleme_arindirmayi_yazar(besleme):
    from spor_toto.odds import ARINDIRMA_VARSAYILAN
    assert besleme.uret("2026_27")["arindirma"] == ARINDIRMA_VARSAYILAN


# ─── Faz B ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fazb():
    spec = importlib.util.spec_from_file_location(
        "st_fazb", str(KOK / "scripts" / "faz_b.py"))
    mod = importlib.util.module_from_spec(spec)
    eski = sys.argv
    sys.argv = ["x"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = eski
    return mod


def test_fazb_bugun_olculemez_der(fazb):
    """Durma kuralının 1. şıkkı: bir gözlemle bağıntı ölçülmez."""
    o = fazb.rapor("2026_27")
    assert o["ikramiyeli_hafta"] == 1
    assert o["durum"] == "olculemez"
    assert o["guc"]["yeterli"] is False


def test_fazb_bos_kademeyi_secmez(fazb):
    """15 bilen çıkmadıysa o kademe cevap vermez; kazananı olan en üst alınır.

    1. haftada 15 bilen 0 kişi (30,1 milyon TL devretti), 14 bilen 8 kişi.
    Körü körüne en üst kademe alınsaydı satır boş görünürdü.
    """
    h1 = next(h for h in fazb.elde_ne_var("2026_27")["haftalar"]
              if h["hafta"] == 1)
    assert h1["kademe"] == 14
    assert h1["kazanan"] == 8
    assert h1["kisi_basi"] == pytest.approx(2153527.18)
    assert h1["devreden"] == pytest.approx(30149380.57)


def test_fazb_ikramiyesiz_hafta_sayilmaz(fazb):
    h2 = next(h for h in fazb.elde_ne_var("2026_27")["haftalar"]
              if h["hafta"] == 2)
    assert h2["ikramiye_var"] is False
    assert "kisi_basi" not in h2


def test_fazb_guc_orneklemle_birlikte_karar_degistirir(fazb):
    az = fazb.guc_analizi(1)
    cok = fazb.guc_analizi(10 ** 4)
    assert az["yeterli"] is False
    assert cok["yeterli"] is True
    assert az["gerekli_hafta"] == cok["gerekli_hafta"]
    assert az["gerekli_hafta"] > 41 * 0.5, "bir sezondan uzun surmeli"


def test_fazb_sinir_notu_kaldirilmamis(fazb):
    """Oynanma yüzdeleri tek platformun; bu not her çıktıda durmalı."""
    o = fazb.rapor("2026_27")
    assert "TEK PLATFORM" in o["sinir"].upper()
    assert "OLCULMEMISTIR" in o["sinir"].upper()
