"""Süper Toto haftalık boru hattı — `scripts/super_toto_*.py`.

Bu scriptler canlı sezonun tek yolu ve **birleştirildiklerinde hiç testleri
yoktu**: 1.900 satır Python, CI'da hiç çalışmıyordu. Buradaki testler
bulguları değil **boru hattını** korur — bir hafta dosyası okunduğunda
olasılıklar doğru mu kuruluyor, kaçak dağılımı gerçekten bir dağılım mı,
en iyi kolon sayımı doğru mu.

`scripts/` artık bir pakettir, dolayısıyla üretim de test de sıradan
`importlib.import_module` kullanır — test, üretimin yüklediğinden başka
bir şeyi yüklememelidir.
"""

import importlib.util
import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data" / "super_toto" / "2026_27"

pytestmark = pytest.mark.skipif(
    not (VERI / "hafta_01.json").exists(),
    reason="super toto hafta verisi yok")


def _modul(ad: str):
    """Uretimin yukledigi neyse test de onu yuklemeli — artik siradan import."""
    return importlib.import_module(f"scripts.super_toto_{ad}")


def _haftalar() -> list[int]:
    """Girilmis hafta numaralari — DISKTEN, sabit yazilmadan.

    Once burada `[1, 2]` sabit yaziliydi ve 3. ile 4. hafta girildiginde
    testler onlara hic bakmadi. `scripts/check.sh` ayni hatayi yapmis, tesbit
    edilmis ve orada duzeltilmisti (hafta listesi diskten cikiyor); test
    tarafi ayni desenle geride kalmisti — kapinin sessizce kuculmesi, tam
    olarak yakalamasi gereken sey.
    """
    return sorted(int(f.stem.split("_")[1])
                  for f in VERI.glob("hafta_[0-9][0-9].json"))


@pytest.fixture(scope="module")
def hafta():
    return _modul("hafta")


@pytest.fixture(scope="module")
def deg():
    return _modul("degerlendir")


# ─── hafta_yukle ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("no", _haftalar())
def test_hafta_okunur_ve_olasiliklar_bire_toplanir(hafta, no):
    d = hafta.hafta_yukle("2026_27", no)
    assert len(d["matches"]) == 15
    for m in d["matches"]:
        assert sum(m["probs"].values()) == pytest.approx(1.0, abs=1e-9)
        assert sum(m["play"].values()) == pytest.approx(1.0, abs=1e-9)
        assert set(m["probs"]) == {"1", "0", "2"}


def test_orani_olmayan_mac_esit_dagitilir(hafta, tmp_path, monkeypatch):
    """Oranı ilan edilmemiş maç bir TAHMİN değil, bilgi yokluğu taşır.

    Boru hattı onu 1/3–1/3–1/3 yapar; kural da eşiğin altında kaldığı için
    otomatik üçlü açar. Değişmez, o maça uydurma bir olasılık atanmamasıdır.

    Test **sentetik veriyle** koşar, canlı hafta dosyasıyla değil: 2. haftanın
    9. maçının oranı 2026-08-22'de ilan edildi ve o dosyaya bağlı bir test
    mekanizmayı değil, o günkü veriyi ölçüyordu. Mekanizma kalıcıdır, veri
    değildir.
    """
    d = json.loads((VERI / "hafta_02.json").read_text(encoding="utf-8"))
    d["matches"][8]["odds"] = None
    kok = tmp_path / "2026_27"
    kok.mkdir()
    (kok / "hafta_08.json").write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(hafta, "VERI_KOK", tmp_path)

    y = hafta.hafta_yukle("2026_27", 8)
    m = next(x for x in y["matches"] if x["no"] == 9)
    assert m["odds_yok"] is True
    assert m["odds"] is None
    assert m["fav"] is None
    assert m["margin"] == 0.0
    for s in ("1", "0", "2"):
        assert m["probs"][s] == pytest.approx(1 / 3)

    # Marj ortalamasi oransiz maci saymaz — 0'lik marj ortalamayi sahte
    # bicimde asagi cekerdi.
    prof = hafta.hafta_profili(y, hafta.gecen_sezon_ref())
    oranli = [x for x in y["matches"] if not x["odds_yok"]]
    assert prof["avg_margin_pct"] == pytest.approx(
        100 * sum(x["margin"] for x in oranli) / len(oranli))


def test_marj_ortalamasi_iddaa_bandinda(hafta):
    """İddaa marjı çift haneli olmalı — arşivin (~%7) iki katından fazla."""
    d = hafta.hafta_yukle("2026_27", 2)
    prof = hafta.hafta_profili(d, hafta.gecen_sezon_ref())
    assert prof["avg_margin_pct"] > 10


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

@pytest.mark.parametrize("no", _haftalar())
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


def test_oransiz_mac_otomatik_uclu_olur(hafta, tmp_path, monkeypatch):
    """1/3 üçlü eşiğinin (0,38) altındadır; kural maçı kendiliğinden açar."""
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU
    d = json.loads((VERI / "hafta_02.json").read_text(encoding="utf-8"))
    d["matches"][8]["odds"] = None
    kok = tmp_path / "2026_27"
    kok.mkdir()
    (kok / "hafta_08.json").write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(hafta, "VERI_KOK", tmp_path)

    y = hafta.hafta_yukle("2026_27", 8)
    k = hafta.kupon_kur(y, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
    assert 9 in k["uclu"], "orani olmayan mac uclu yapilmali"


def test_9_mac_orani_geldiginde_ucluden_ciftye_doner(hafta):
    """Girdi değişti, kural değişmedi — kayıt bunu ayırt edebilmeli.

    2. haftanın 9. maçının oranı sonradan ilan edildi (1.97-3.05-2.92) ve
    maç 1/3 varsayımından gerçek fiyata geçti. Kupon v2 kuruldu, v1
    `superseded` altında gerekçesiyle saklandı.
    """
    d = hafta.hafta_yukle("2026_27", 2)
    m = next(x for x in d["matches"] if x["no"] == 9)
    assert m["odds_yok"] is False
    assert m["fav"] is not None

    kupon = json.loads(
        (VERI / "hafta_02_kupon.json").read_text(encoding="utf-8"))
    assert "superseded" in kupon, "v1 kayitta durmali"
    v1 = kupon["superseded"]["variants"][0]["picks"]
    v2 = kupon["variants"][0]["picks"]
    assert v1[8] == "102" and v2[8] == "12", (v1[8], v2[8])
    # Revizyon SONUC gorulmeden yapildi — kaydin en onemli alani.
    assert kupon["meta"]["results_known"] is False
    assert kupon["superseded"]["reason"]


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
    return {"meta": {}, "matches": [mac, *digerleri]}


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


def test_kapi_delikli_bahisciyi_isaretler(hafta):
    """Bir bahiscinin kaydi BAZI maclarda yoksa bu soylenmeli.

    4. haftada Pinnacle 2. maci hic fiyatlamadi ve 13. macin kapanisini
    vermedi; o satirlarda ana fiyat baska bir kayittan gelmek zorunda kaldi.
    Kapi once yalnizca 1. MACIN kitaplarina bakiyordu, yani 1. macta olmayip
    baska macta olan bir bahisci hic denetlenmezdi.
    """
    d = _sahte()
    d["matches"][0]["odds_books"] = {
        "pinnacle_acilis": {"1": 2.0, "0": 3.4, "2": 3.6},
        "pinnacle_kapanis": {"1": 2.0, "0": 3.4, "2": 3.6},
    }
    for m in d["matches"][1:]:
        m["odds_books"] = {"nesine_acilis": {"1": 2.0, "0": 3.4, "2": 3.6}}
    uyarilar = hafta.dogrula(d)
    assert any("pinnacle_acilis" in u and "kayıt YOK" in u for u in uyarilar), uyarilar
    # 1. macta olmayan bir kitap da denetlenmeli — birlesim, ilk mac degil.
    assert any("nesine_acilis" in u and "kayıt YOK" in u for u in uyarilar), uyarilar


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
    # Liste sabit yazilmaz: her yeni hafta girildiginde bu test kirilirdi ve
    # kirilma bir HATA degil, isin ilerlemesi olurdu. Cakilan sey defterin
    # ISI: dosyadan bulunan haftalar, artan sirada, bosluksuz.
    bulunan = sezon.haftalari_bul("2026_27")
    assert bulunan, "girilmis hafta bulunamadi"
    assert bulunan == sorted(bulunan)
    assert bulunan == list(range(1, len(bulunan) + 1)), (
        f"hafta numaralarinda bosluk var: {bulunan}")


def test_defter_kupon_dosyasini_hafta_sanmaz(sezon):
    """`hafta_01_kupon.json` bir hafta dosyası değildir; listeye girmemeli."""
    assert all(isinstance(x, int) for x in sezon.haftalari_bul("2026_27"))


def test_defter_yalnizca_sonucu_olan_haftayi_olcer(sezon):
    """Ölçüm sonuca bağlıdır — sonucu olmayan hafta hiçbir ortalamaya girmez.

    Test hafta NUMARASINA bağlanmaz: 2. hafta bir zamanlar sonuçsuzdu, sonuç
    girildi ve testin ilk sürümü bu yüzden kırıldı. Bağlanacak şey haftanın
    kendisi değil, kuraldır: `sonuc_var` ne diyorsa ölçüm de onu demeli.
    """
    o = sezon.topla("2026_27")
    assert o["hafta_girilmis"] == len(sezon.haftalari_bul("2026_27"))
    olculen = [h for h in o["haftalar"] if h["sonuc_var"]]
    assert o["hafta_olculen"] == len(olculen)
    assert o["mac"] == 15 * len(olculen)
    for h in o["haftalar"]:
        assert ("brier" in h) is h["sonuc_var"]


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


def test_besleme_sonucu_uydurmaz_ve_kaydirmaz(besleme):
    """Maç sonucu ya YOKTUR ya da dizideki KENDİ yerinden gelir.

    İki hata da sessizdir ve ikisi de aynı bekçiyle kapanır: sonucu
    girilmemiş haftada uydurulmuş bir sonuç, ve girilmiş haftada bir
    kaydırma (15. maça 14. maçın sonucu). İkincisi ancak maç maç
    denetlenirse görülür.
    """
    for w in besleme.uret("2026_27")["weeks"]:
        if w["results"] is None:
            assert all(m["result"] is None for m in w["matches"])
            continue
        assert len(w["results"]) == 15
        for m in w["matches"]:
            assert m["result"] == w["results"][m["no"] - 1]


def test_besleme_eksik_bahisci_satirinda_cokmez(besleme, hafta):
    """Bir bahisci bazi maclarda yoksa besleme URETILEBILMELI.

    Bu bir kuram degil: 4. hafta girildiginde `_fiyat_blok` `KeyError:
    'pinnacle_acilis'` ile dustu, cunku kitap listesi 1. MACTAN aliniyor ve
    butun maclarda o anahtarla indeksleniyordu. Ortalama marj artik yalnizca
    o kitabi TASIYAN maclardan gelir ve kac macdan geldigi `margin_n`de
    yazili — 13 maclik bir ortalama 15 maclik sanilmasin.
    """
    for w in besleme.uret("2026_27")["weeks"]:
        f = w["prices"]
        if not f:
            continue
        assert f["match_count"] == len(w["matches"])
        for k, n in f["margin_n"].items():
            assert 0 < n <= f["match_count"]
            assert k in f["margins"]
        # Eksik satiri olan bir kitap icin sayi mac sayisindan KUCUK olmali;
        # tam olan icin esit. Ikisi de kaydin kendisinden dogrulanir.
        d = hafta.hafta_yukle("2026_27", w["week"])
        for k, n in f["margin_n"].items():
            var = sum(1 for m in d["matches"]
                      if (m.get("odds_books") or {}).get(k))
            assert n == var, (w["week"], k, n, var)


def test_besleme_arindirmayi_yazar(besleme):
    from spor_toto.odds import ARINDIRMA_VARSAYILAN
    assert besleme.uret("2026_27")["arindirma"] == ARINDIRMA_VARSAYILAN


# ─── Faz B ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fazb():
    return importlib.import_module("scripts.faz_b")


def test_fazb_gucu_yetmeden_olculebilir_demez(fazb):
    """Durma kuralı: güç yetmedikçe eksen "ölçülebilir" ilan edilmez.

    Test iki kez kırıldı ve ikisinde de kırılan şey testin SABİTİYDİ,
    kural değil. Önce hafta sayısı sabitti (1 → 2). Sonra durum etiketi
    sabitlendi (`== "olculemez"`); 3. haftanın ikramiye tablosu girilince
    ikramiyeli hafta 3'e çıktı ve `faz_b` doğru davranarak
    "acik ama olculmemis" demeye başladı — yani **doğru davranış testi
    kırdı**. Bu, 2. haftanın "bugünkü durumu kalıcı sanmak" kalıbının
    üçüncü örneğiydi (docs §3.38).

    Korunan kural: `guc.yeterli` false olduğu sürece durum
    "olculebilir" OLAMAZ. Etiketin hangi ara kademede olduğu (hiç kayıt
    yok / bağıntıya bakılamaz / açık ama ölçülmemiş) haftaların sayısıyla
    değişir ve testin işi değildir.
    """
    o = fazb.rapor("2026_27")
    ikramiyeli = sum(1 for h in fazb.elde_ne_var("2026_27")["haftalar"]
                     if h["ikramiye_var"])
    assert o["ikramiyeli_hafta"] == ikramiyeli
    assert o["guc"]["yeterli"] is False
    assert o["durum"] != "olculebilir"


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
    """İkramiye tablosu olmayan hafta ölçüme girmez, olan girer.

    Test hafta numarasına değil ALANIN KENDİSİNE bağlı: `ikramiye_var`
    ne diyorsa `kisi_basi` de onu demeli. (Önce "2. haftada ikramiye
    yok" yazıyordu; tablo girilince doğru davranış testi kırdı.)
    """
    for h in fazb.elde_ne_var("2026_27")["haftalar"]:
        assert ("kisi_basi" in h) is h["ikramiye_var"]


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


# ─── dondurulmuş kupon yeniden hesaplanmaz ────────────────────────────────────

def test_donmus_kupon_yeniden_hesaplanmaz(besleme, hafta):
    """Projenin en değerli alışkanlığı: kayıt, sonradan üzerine yazılmaz.

    Marj arındırma varsayılanı 2026-08'de değişti ve **aynı eşik başka
    işaretler üretiyor**. Beslemenin `coupon` alanı dondurulmuş dosyadan
    gelmeli; yeniden hesaplanan sürüm ayrı alanda (`coupon_today`) durmalı.
    """
    g = besleme.uret("2026_27")
    for w in g["weeks"]:
        yol = (KOK / "data" / "super_toto" / "2026_27"
               / f"hafta_{w['week']:02d}_kupon.json")
        donmus = json.loads(yol.read_text(encoding="utf-8"))
        assert w["coupon"]["picks"] == donmus["variants"][0]["picks"], (
            f"{w['week']}. hafta: besleme dondurulmus kaydi tasimiyor")


def test_donmus_kupon_hangi_olcekte_donduruldugunu_yazar(besleme):
    """Ölçek yazmıyorsa işaretler yorumlanamaz.

    Test uzun sure `arindirma == "orantili"` ve `marj_ort_pct > 10` diye
    cakiliydi. Ikisi de o gunku IKI haftanin tesadufuydu, kuralin kendisi
    degil: 1. ve 2. hafta olcek degismeden once dondurulmustu ve ana fiyat
    ~%18 marjli iddaa bulteniydi. 3. haftada kupon `shin` ile donduruldu ve
    ana fiyat %4,6 marjli Pinnacle kapanisi oldu — test o hafta kirildi ama
    kayitta yanlis olan hicbir sey yoktu.

    Cakilan sey bu yuzden degerin kendisi degil, kaydin TAM olmasidir:
    hangi arindirma, hangi marj, hangi tarih. Bu ucu yazan bir kayit
    yorumlanabilir; yazmayan yorumlanamaz.
    """
    from spor_toto.odds import ARINDIRMA_YONTEMLERI
    for w in besleme.uret("2026_27")["weeks"]:
        k = w["coupon"]
        assert k["arindirma"] in ARINDIRMA_YONTEMLERI, (
            f"{w['week']}. hafta: taninmayan arindirma {k['arindirma']!r}")
        assert isinstance(k["marj_ort_pct"], (int, float)) and k["marj_ort_pct"] > 0, (
            f"{w['week']}. hafta: kupon hangi marjda donduruldugunu yazmiyor")
        assert k["frozen_at"]


def test_olcek_kaymasi_gorunur_kilinir(besleme):
    """Ölçek değişimi işaret değiştirdiyse bu SÖYLENMELİ, gizlenmemeli."""
    from spor_toto.odds import ARINDIRMA_VARSAYILAN
    g = besleme.uret("2026_27")
    for w in g["weeks"]:
        assert w["coupon_today"]["arindirma"] == ARINDIRMA_VARSAYILAN
        kayan = w["coupon_drift"]
        assert kayan is not None
        beklenen = [i + 1 for i, (a, b) in enumerate(
            zip(w["coupon"]["picks"], w["coupon_today"]["picks"])) if a != b]
        assert kayan == beklenen
    # Iki haftada da olcek en az bir isareti degistirdi; test bunu civiler
    # ki "fark yok" diye sessizce gecilmesin.
    assert any(w["coupon_drift"] for w in g["weeks"])


def test_degerlendirme_donmus_kuponu_kullanir(deg, hafta):
    """Sonuç değerlendirmesi de kaydı okumalı, yeniden hesaplamamalı."""
    d = hafta.hafta_yukle("2026_27", 1)
    donmus = json.loads(
        (VERI / "hafta_01_kupon.json").read_text(encoding="utf-8"))
    s = deg.kupon_degerlendir(d, donmus["variants"][0]["picks"])
    assert s["picks"] == donmus["variants"][0]["picks"]
    assert s["best"] == 9, "1. haftanin kayitli sonucu: en iyi kolon 9/15"


def test_besleme_revizyonu_gorunur_tutar(besleme):
    """Görünmeyen bir revizyon, revizyon olmayan bir kayıttan daha kötüdür.

    2. haftanın kuponu 9. maçın oranı ilan edilince yenilendi; önceki sürüm
    gerekçesiyle birlikte beslemede durmalı.
    """
    g = besleme.uret("2026_27")
    w2 = next(w for w in g["weeks"] if w["week"] == 2)
    esk = w2["coupon_superseded"]
    assert esk is not None
    assert esk["picks"][8] == "102", "onceki surumde 9. mac ucluydu"
    assert w2["coupon"]["picks"][8] == "12", "yeni surumde cifte"
    assert esk["reason"] and esk["revised_at"]
    assert esk["arindirma"] == "orantili"
    w1 = next(w for w in g["weeks"] if w["week"] == 1)
    assert w1["coupon_superseded"] is None, "1. hafta yenilenmedi"
