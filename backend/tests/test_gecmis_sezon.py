"""Geçmiş sezon — bülten adlarını fikstüre bağlama ve 1/0/2 üretimi.

Bu boru hattının riski `build_odds.py`nınkinden **büyüktür** ve testler
oraya odaklanır: orada skor bir ayırt edici olarak kullanılabiliyordu,
burada skor aranan şeydir. Yani eşleştirme yalnızca ada ve tarihe dayanır.

Bu yüzden korunan asıl davranış **kabul değil, REDdir**: belirsiz bir aday
çifti karşısında maçın düşmesi, yanlış maçın sessizce seçilmesinden iyidir.
"""

import json

import pytest

gecmis = pytest.importorskip("scripts.build_gecmis_sezon")


def _aday(ev: str, dep: str, hg: int = 1, ag: int = 0, lig: str = "T1"):
    from datetime import date
    return {"lig": lig, "ev": ev, "dep": dep, "hg": hg, "ag": ag,
            "tarih": date(2023, 8, 12)}


# ─── sezon kodu ───────────────────────────────────────────────────────────────

def test_sezon_kodu():
    assert gecmis.sezon_kodu("2023_24") == "2324"
    assert gecmis.sezon_kodu("2025_26") == "2526"
    assert gecmis.sezon_kodu("2021_22") == "2122"


# ─── sonuç kodu ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hg,ag,beklenen", [(2, 1, "1"), (1, 1, "0"), (0, 3, "2")])
def test_kod(hg, ag, beklenen):
    assert gecmis.kod(hg, ag) == beklenen


# ─── eşleştirme ───────────────────────────────────────────────────────────────

def test_temiz_eslesme_kabul():
    adaylar = [_aday("Trabzonspor", "Antalyaspor"),
               _aday("Konyaspor", "Istanbulspor")]
    aday, gerekce = gecmis.eslestir("TRABZONSPOR A.Ş.", "ANTALYASPOR A.Ş.", adaylar)
    assert aday is not None
    assert (aday["ev"], aday["dep"]) == ("Trabzonspor", "Antalyaspor")
    assert gerekce == ""


def test_tek_taraf_tutarsa_kabul_ETMEZ():
    """Ev adı mükemmel, deplasman tamamen başka — kabul edilmemeli."""
    adaylar = [_aday("Trabzonspor", "Fenerbahce")]
    aday, gerekce = gecmis.eslestir("TRABZONSPOR A.Ş.", "ANTALYASPOR A.Ş.", adaylar)
    assert aday is None
    assert "esigi gecen aday yok" in gerekce


def test_aday_yoksa_duser():
    aday, gerekce = gecmis.eslestir("A", "B", [])
    assert aday is None
    assert gerekce


def test_ayirt_edilemeyen_iki_aday_MACI_DUSURUR():
    """En kritik bekçi: skor kilidi olmadığı için kura çekilmez.

    Aynı gün oynanan iki benzer adlı eşleşme varsa "en iyisini seç" demek
    sessizce yanlış maçı almaktır. Doktrin 2: belirsiz olan elenir.
    """
    adaylar = [_aday("Manchester United", "Arsenal"),
               _aday("Manchester United", "Arsenal", hg=3, ag=3)]
    aday, gerekce = gecmis.eslestir("MANCHESTER UNITED", "ARSENAL", adaylar)
    assert aday is None
    assert "ayirt edilemedi" in gerekce


def test_belirgin_fark_varsa_en_iyisi_secilir():
    """İkinci aday belirgin biçimde geride ise seçim güvenlidir."""
    adaylar = [_aday("Real Madrid", "Real Sociedad"),
               _aday("Real Betis", "Sevilla")]
    aday, _ = gecmis.eslestir("REAL MADRID", "REAL SOCIEDAD", adaylar)
    assert aday is not None
    assert aday["ev"] == "Real Madrid"


def test_sponsor_eki_eslesmeyi_bozmaz():
    """`build_odds.py`nin sponsor temizliği yeniden kullanılıyor."""
    adaylar = [_aday("Fatih Karagumruk", "Besiktas")]
    aday, _ = gecmis.eslestir("MISIRLI.COM.TR FATİH KARAGÜMRÜK",
                              "BEŞİKTAŞ A.Ş.", adaylar)
    assert aday is not None


# ─── hafta kurma ──────────────────────────────────────────────────────────────

#: Adlar SIFIR DOLGULU: `EV1` `EV11`in alt dizesidir ve `benzerlik` alt
#: dizeye 0,94 verir — yani gercekci olmayan bir fixture, ayirt-edilemezlik
#: kilidini bosuna tetikler. `EV01`..`EV15` hicbiri otekinin alt dizesi
#: degildir.
def _bulten_hafta(n: int = 1):
    return {"week": n, "matches": [
        {"no": i, "home": f"EV{i:02d}", "away": f"DEP{i:02d}"}
        for i in range(1, 16)]}


def _indeks_tam():
    from datetime import date
    gun = date(2023, 8, 12)
    return {gun: [{"lig": "T1", "ev": f"EV{i:02d}", "dep": f"DEP{i:02d}",
                   "hg": i % 3, "ag": 0, "tarih": gun} for i in range(1, 16)]}


def test_tam_hafta_kurulur_ve_dizi_maclardan_turer():
    kayit = gecmis.hafta_kur(_bulten_hafta(), "2023-08-12", _indeks_tam())
    assert kayit["kabul"]
    assert len(kayit["matches"]) == 15
    assert kayit["results"] == "".join(
        gecmis.kod(m["hg"], m["ag"]) for m in kayit["matches"])
    assert kayit["n1"] + kayit["n0"] + kayit["n2"] == 15


def test_bulten_adi_da_saklanir():
    """Eşleştirme denetlenebilir olmalı: OCR adı da kayıtta durur."""
    kayit = gecmis.hafta_kur(_bulten_hafta(), "2023-08-12", _indeks_tam())
    m = kayit["matches"][0]
    assert m["bulten_home"] == "EV01"
    assert "home" in m


def test_eksik_mac_haftayi_DUSURUR():
    indeks = _indeks_tam()
    gun = next(iter(indeks))
    indeks[gun] = indeks[gun][:14]
    kayit = gecmis.hafta_kur(_bulten_hafta(), "2023-08-12", indeks)
    assert not kayit["kabul"]
    assert "14/15" in kayit["red_gerekcesi"]


def test_kapanis_tarihi_yoksa_duser():
    kayit = gecmis.hafta_kur(_bulten_hafta(), None, _indeks_tam())
    assert not kayit["kabul"]
    assert "kapanis tarihi yok" in kayit["red_gerekcesi"]


def test_pencere_disindaki_fikstur_kullanilmaz():
    """Pencere hafta kapanışına bağlıdır; bir ay sonrası sayılmaz."""
    kayit = gecmis.hafta_kur(_bulten_hafta(), "2023-10-12", _indeks_tam())
    assert not kayit["kabul"]


# ─── doğrulama kapısı ─────────────────────────────────────────────────────────

def _kabul_hafta(n: int = 1):
    maclar = [{"no": i, "home": f"E{i}", "away": f"D{i}",
               "bulten_home": f"E{i}", "bulten_away": f"D{i}",
               "lig": "T1", "kickoff": "2023-08-12", "hg": 1, "ag": 0,
               "code": "1"} for i in range(1, 16)]
    return {"week": n, "matches": maclar, "results": "1" * 15,
            "n1": 15, "n0": 0, "n2": 0, "season": "2023/2024", "kabul": True}


def test_dogrulama_saglam_seti_gecirir():
    """Sağlam bir set **yükseltmeden** geçmeli — asıl iddia budur.

    Bu testte bilerek `assert` yok: `dogrula()` bir kapı ve sözleşmesi
    "bozuksa yükselt"tir, yani sağlam girdide sessiz kalması TAM OLARAK
    beklenen davranıştır. Anlamını hemen altındaki negatif testlerden alır
    (`pytest.raises(AssertionError, ...)`): kapı no-op'a çevrilseydi bu test
    yeşil kalır ama o testler DÜŞERDİ. Çift birlikte tamdır.
    """
    gecmis.dogrula({"2023_24": [_kabul_hafta(1), _kabul_hafta(2)]})


def test_dizi_maclardan_turemiyorsa_yazilmaz():
    """Doktrin 1: dizi listeden türer, bağımsız yazılmaz."""
    h = _kabul_hafta()
    h["results"] = "2" * 15
    with pytest.raises(AssertionError, match="turemiyor"):
        gecmis.dogrula({"2023_24": [h]})


def test_sayimlar_diziyle_tutmuyorsa_yazilmaz():
    h = _kabul_hafta()
    h["n1"] = 14
    with pytest.raises(AssertionError, match="sayimlar"):
        gecmis.dogrula({"2023_24": [h]})


def test_kupon_sirasi_bozuksa_yazilmaz():
    h = _kabul_hafta()
    h["matches"][2]["no"] = 9
    with pytest.raises(AssertionError, match="kupon sirasi"):
        gecmis.dogrula({"2023_24": [h]})


def test_mukerrer_hafta_yazilmaz():
    with pytest.raises(AssertionError, match="mukerrer"):
        gecmis.dogrula({"2023_24": [_kabul_hafta(1), _kabul_hafta(1)]})


# ─── yayındaki çıktı ──────────────────────────────────────────────────────────

def _sezon_dosyalari():
    return sorted(p for p in gecmis.CIKTI_DIZIN.glob("*.json")
                  if p.name != "gecmis_rapor.json")


def test_yayindaki_set_kendini_dogruluyor():
    dosyalar = _sezon_dosyalari()
    if not dosyalar:
        pytest.skip("geçmiş sezon henüz üretilmemiş")
    for yol in dosyalar:
        govde = json.loads(yol.read_text(encoding="utf-8"))
        assert govde["meta"]["weeks"] == len(govde["weeks"])
        gecmis.dogrula({yol.stem: govde["weeks"]})


def test_yayindaki_set_st_history_ile_KARISMAZ():
    """Ayrı köken sınıfı: `/api/stats` hâlâ eski dosyaya bakar."""
    eski = gecmis.KOK / "data" / "st_history_2025_26.json"
    assert eski.exists(), "st_history_2025_26.json yerinde durmalı"
    dosyalar = _sezon_dosyalari()
    if not dosyalar:
        pytest.skip("geçmiş sezon henüz üretilmemiş")
    for yol in dosyalar:
        meta = json.loads(yol.read_text(encoding="utf-8"))["meta"]
        assert meta["origin"].startswith("turetilmis")
        assert "KARISMAZ" in meta["note"]


# ─── çapraz doğrulama (boru hattının asıl sınavı) ─────────────────────────────

def test_capraz_dogrulama_st_history_ile_ortusuyor():
    """İki BAĞIMSIZ boru hattı aynı 1/0/2 dizisine varmalı.

    `st_history_2025_26.json` üçüncü parti bir Nuxt payload'ından geliyor;
    bu set resmî bülten görselinden OCR ile okunup football-data fikstürüne
    bağlanarak üretiliyor. İkisi birbirini hiç görmüyor.

    Ölçülen: **28/29 hafta birebir aynı.** Eşik oraya değil biraz altına
    konuldu; düşerse OCR ya da eşleştirme bozulmuş demektir.
    """
    yol = gecmis.CIKTI_DIZIN / "gecmis_rapor.json"
    if not yol.exists():
        pytest.skip("geçmiş sezon henüz üretilmemiş")
    c = json.loads(yol.read_text(encoding="utf-8")).get("capraz_dogrulama", {})
    if not c.get("kosuldu"):
        pytest.skip(c.get("gerekce", "çapraz doğrulama koşulmadı"))
    assert c["ortak_hafta"] >= 25
    oran = c["birebir_ayni"] / c["ortak_hafta"]
    assert oran >= 0.90, (
        f"iki boru hattı ayrıştı: {c['birebir_ayni']}/{c['ortak_hafta']}")


def test_ayrisan_hafta_SIRA_farkidir_sonuc_farki_degil():
    """Ayrışan hafta varsa nedeni belgelenmiş olmalı.

    Ölçüldü: 2025/26 hf 30'da iki kaynak **aynı 15 maçı** taşıyor ama
    KUPON SIRASI farklı (bültende Göztepe–Eyüpspor 6., payload'da 15.).
    Bu §7.4'ün v1 vakasıyla aynı sınıfta bir bulgudur ve doktrin 4 gereği
    düzeltilmez, raporlanır.

    Maç kümesi de farklı çıkarsa sorun sıralamada değil eşleştirmededir ve
    bu test onu ayırt eder.
    """
    yol = gecmis.CIKTI_DIZIN / "gecmis_rapor.json"
    if not yol.exists():
        pytest.skip("geçmiş sezon henüz üretilmemiş")
    c = json.loads(yol.read_text(encoding="utf-8")).get("capraz_dogrulama", {})
    if not c.get("kosuldu"):
        pytest.skip("çapraz doğrulama koşulmadı")
    for f in c["ayrisan"]:
        assert f["ayni_mac_kumesi"], (
            f"hf {f['week']}: maç kümesi de farklı — bu bir SIRA sorunu değil, "
            "eşleştirme sorunudur ve incelenmelidir")


# ─── ad çevirisi: sessizce ölü kalmış sözlük ──────────────────────────────────
#
# Aşağıdaki dört test tek bir kusurun bekçisidir ve kusur ÖLÇÜLEREK bulundu
# (`build_gecmis_sezon.py --teshis`). `BULTEN_ESLERI` bir "yakınsatma" değil
# doğrulanmış bir sözlüktür; ama satırlarının bir bölümü **hiçbir zaman
# çalışmadı** çünkü aramanın anahtarı, bültenin kendi yazımıyla eşleşmiyordu.

def test_noktali_I_sozlugu_OLU_BIRAKMAZ():
    """Türkçe `İ` (U+0130) sözlüğü sessizce devre dışı bırakıyordu.

    `"MARSİLYA".lower()` düz `marsilya` vermez: `i` + U+0307 (birleşen
    nokta) verir. Ekranda ikisi aynı görünür, sözlükte biri yoktur.

    Bülten **büyük harfli bir görselden** OCR ile okunuyor, yani `İ` orada
    kural dışı değil normal hâl — kusur tam da sözlüğe en çok ihtiyaç
    duyulan yerde vuruyordu.
    """
    assert gecmis._bulten_adi("MARSİLYA") == "marseille"
    assert gecmis._bulten_adi("SPORTING LİZBON") == "sp lisbon"
    assert gecmis._bulten_adi("MİLANO") == "milan"


def test_noktali_I_ile_noktasiz_I_AYNI_yere_gider():
    """Bülten iki yazımı da üretiyor; ikisi de aynı karşılığa varmalı."""
    for noktali, noktasiz in (("MARSİLYA", "MARSILYA"),
                              ("MİLANO", "MILANO")):
        assert gecmis._bulten_adi(noktali) == gecmis._bulten_adi(noktasiz)


def test_OCR_bolu_isareti_temizlenir():
    """`/` sütun ayracı OCR'da adın başına düşüyor; hiçbir kulüp `/` ile başlamaz."""
    assert gecmis._bulten_adi("/ MARSİLYA") == "marseille"
    assert gecmis._bulten_adi("/ MANCHESTER UTD") == "man united"


def test_ic_bolu_isaretine_DOKUNULMAZ():
    """Temizlik yalnızca kenarlardadır — ad içindeki `/` bilgi olabilir."""
    assert "/" in gecmis._bulten_adi("AAA / BBB")


def test_teshisle_eklenen_sozluk_satirlari_calisir():
    """`--teshis`in bulduğu ve football-data'da DOĞRULANAN karşılıklar."""
    beklenen = {
        "UNION SAINT GİLLOİSE": "st. gilloise",
        "LA GALAXY": "los angeles galaxy",
        "KUOPION": "kups",
        "VAASAN PS": "vps",
        "SEİNÖJOEN": "sjk",
        "H.KAMERATENE": "hamkam",
        "FCKTIP": "ktp",
    }
    for ham, karsilik in beklenen.items():
        assert gecmis._bulten_adi(ham) == karsilik, ham


def test_sozlukte_olmayan_ad_OLDUGU_GIBI_kalir():
    """Sözlük bir yakınsatma değil; tanımadığı adı bulanık eşleştirmeye bırakır."""
    assert gecmis._bulten_adi("GALATASARAY A.Ş") == "GALATASARAY A.Ş"


# ─── teşhis kipi ──────────────────────────────────────────────────────────────

def test_teshis_ayirt_edilemezligi_ayri_sinifa_koyar():
    """`teshis_sinifi`, `eslestir`in tek gerekçesini ÜÇE ayırır.

    Ayrım olmadan *"eşleştirmeyi iyileştirelim"* ölçüsüz bir cümledir:
    strateji değişikliği yalnızca `ayirt_edilemedi` sınıfına dokunabilir,
    `aday_yok_uzak` ertelenmiş maçtır ve hiçbir strateji onu kurtarmaz.
    """
    iki_benzer = [_aday("Kayserispor", "Konyaspor"),
                  _aday("Kayserispor", "Konyaspor", hg=2, ag=2)]
    sinif, _ = gecmis.teshis_sinifi("KAYSERİSPOR", "KONYASPOR", iki_benzer)
    assert sinif == "ayirt_edilemedi"


def test_teshis_uzak_ile_esik_altini_AYIRIR():
    uzak = [_aday("Zzzzzzzz", "Wwwwwwww")]
    sinif, _ = gecmis.teshis_sinifi("TRABZONSPOR", "ANTALYASPOR", uzak)
    assert sinif == "aday_yok_uzak"

    yakin = [_aday("Trabzonspor", "Wwwwwwww")]
    sinif, _ = gecmis.teshis_sinifi("TRABZONSPOR", "ANTALYASPOR", yakin)
    assert sinif == "aday_yok_esik_alti"


def test_teshis_temiz_eslesmeyi_eslesti_sayar():
    sinif, skor = gecmis.teshis_sinifi(
        "TRABZONSPOR A.Ş.", "ANTALYASPOR A.Ş.",
        [_aday("Trabzonspor", "Antalyaspor"), _aday("Konyaspor", "Sivasspor")])
    assert sinif == "eslesti"
    assert skor >= gecmis.ORTALAMA_ESIK


def test_teshis_sinif_adlari_belgelenmis_kumeyle_ayni():
    """Yeni bir sınıf eklenirse `TESHIS_SINIFLARI` de büyümeli."""
    uretilen = set()
    for adaylar in ([], [_aday("Zzzz", "Wwww")], [_aday("Trabzonspor", "Wwww")],
                    [_aday("Trabzonspor", "Antalyaspor")]):
        uretilen.add(gecmis.teshis_sinifi("TRABZONSPOR", "ANTALYASPOR", adaylar)[0])
    assert uretilen.issubset(set(gecmis.TESHIS_SINIFLARI))


# ─── kesit geriye gitmemeli ───────────────────────────────────────────────────

def test_kabul_edilen_hafta_sayisi_DUSEMEZ():
    """Ölçüldü: 107 → 112 (Unicode kusuru + `/` artığı + 7 sözlük satırı).

    Eşik ölçülen değerin biraz altına konuldu. Düşerse eşleştirme ya da OCR
    bozulmuş demektir; **yükselmesi serbesttir**.
    """
    yol = gecmis.CIKTI_DIZIN / "gecmis_rapor.json"
    if not yol.exists():
        pytest.skip("geçmiş sezon henüz üretilmemiş")
    rapor = json.loads(yol.read_text(encoding="utf-8"))
    assert rapor["kabul_edilen"] >= 110, rapor["kabul_edilen"]


def test_canli_sezon_gecmis_sete_SIZMAZ():
    """2026/27 bülteni okunuyor ama kabul edilen haftası olmamalı.

    `evaluate.KUPON_SEZONLARI` aynı sezonu iki kez saymamak için özenle
    kuruldu; canlı sezonun bu tarihsel sete sızması o özeni boşa çıkarırdı.
    """
    yol = gecmis.CIKTI_DIZIN / "gecmis_rapor.json"
    if not yol.exists():
        pytest.skip("geçmiş sezon henüz üretilmemiş")
    seasons = json.loads(yol.read_text(encoding="utf-8"))["seasons"]
    assert "2026_27" not in seasons, seasons
