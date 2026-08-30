"""Bülten OCR — ayrıştırma, sıra kilidi ve doğrulama kapısı.

**Testlerin çoğu OCR'a hiç dokunmaz.** Ayrıştırma saf bir metin işidir ve
asıl korunması gereken de odur: tesseract'ın ne okuduğu değil, okunanın
nasıl kabul/ret edildiği. Bu yüzden bu dosya `tesseract` ve `pillow`
olmadan da koşar ve yalnızca uçtan uca testler atlanır.

Korunan asıl şey **sıra**dır. §7.4'ün vakası (v1'de sıra hatası 41 haftanın
15'ini bozdu ve fark edilmedi) bu boru hattının en büyük riskidir: OCR
satırları düşürebilir ve düşen satır sessizce sırayı kaydırır.
"""

import importlib.util
import json

import pytest

bulten = pytest.importorskip("scripts.build_bulten")

OCR_VAR = importlib.util.find_spec("PIL") is not None


def _metin(*satirlar: str, hafta: int = 1) -> str:
    """Başlık + verilen satırlar — gerçek OCR çıktısının şeklinde."""
    return "\n".join([
        "Liste 1 haftalıktır.",
        f"11 AĞUSTOS- 15 AĞUSTOS 2023 ({hafta}. HAFTA)",
        *satirlar,
    ])


def _tam(numarali: bool = True) -> str:
    satirlar = [
        f"{i}. | EV{i} A.Ş. - DEP{i} A.Ş." if numarali else f"EV{i} A.Ş. - DEP{i} A.Ş."
        for i in range(1, 16)
    ]
    return _metin(*satirlar)


# ─── temel ayrıştırma ─────────────────────────────────────────────────────────

def test_tam_hafta_okunur():
    maclar, uyarilar = bulten.satirlari_ayristir(_tam())
    assert len(maclar) == 15
    assert maclar[1] == ("EV1 A.Ş.", "DEP1 A.Ş.")
    assert maclar[15] == ("EV15 A.Ş.", "DEP15 A.Ş.")
    assert uyarilar == []


def test_hafta_no_basliktan_okunur():
    assert bulten.hafta_no_oku(_metin(hafta=37)) == 37
    assert bulten.hafta_no_oku("başlıksız metin") is None


def test_basliktan_ONCEKI_satirlar_sayilmaz():
    """Logo bölgesindeki çöp `X - Y` üretebilir; başlıktan önce hiçbir şey."""
    metin = "ÇÖP - ARTIK\n" + _tam()
    maclar, _ = bulten.satirlari_ayristir(metin)
    assert len(maclar) == 15
    assert maclar[1] == ("EV1 A.Ş.", "DEP1 A.Ş.")


# ─── sıra kilidi (asıl bekçi) ─────────────────────────────────────────────────

def test_numarasiz_satirlar_konumdan_siralanir():
    """Ölçüldü: numara sütunu düşebiliyor ama satırlar sırasını koruyor."""
    maclar, uyarilar = bulten.satirlari_ayristir(_tam(numarali=False))
    assert len(maclar) == 15
    assert maclar[7] == ("EV7 A.Ş.", "DEP7 A.Ş.")
    assert any("numarasi okunamadi" in u for u in uyarilar)


def test_eksik_satir_haftayi_ELER():
    """14 satır: hangisinin kaydığı bilinemez, hafta elenir."""
    satirlar = [f"{i}. | EV{i} - DEP{i}" for i in range(1, 15)]
    maclar, uyarilar = bulten.satirlari_ayristir(_metin(*satirlar))
    assert maclar == {}
    assert any("14 mac satiri" in u for u in uyarilar)


def test_numarasiz_FAZLA_satir_haftayi_ELER():
    """16 aday: hangisinin fazla olduğu bilinemez, hafta elenir.

    Numaralı bir "16." satır zaten süzülür (1–15 dışı) ve bu doğrudur;
    asıl risk numarası okunmamış fazladan bir satırdır.
    """
    satirlar = [f"{i}. | EV{i} - DEP{i}" for i in range(1, 16)]
    satirlar.append("FAZLA TAKIM - BAŞKA TAKIM")
    maclar, uyarilar = bulten.satirlari_ayristir(_metin(*satirlar))
    assert maclar == {}
    assert any("16 mac satiri" in u for u in uyarilar)


def test_okunan_numara_konumla_celisirse_hafta_ELENIR():
    """En kritik bekçi: sıra kaydıysa veri yazılmaz.

    Burada 15 satır var ama 5. sıradaki satır "9." diye okunuyor — yani
    ya OCR yanlış okudu ya bir satır kaydı. İkisi de sessizce kabul
    edilemez.
    """
    satirlar = [f"{i}. | EV{i} - DEP{i}" for i in range(1, 16)]
    satirlar[4] = "9. | EV5 - DEP5"
    maclar, uyarilar = bulten.satirlari_ayristir(_metin(*satirlar))
    assert maclar == {}
    assert any("sira tutmuyor" in u for u in uyarilar)


def test_kismi_numara_tutuyorsa_kabul():
    """Numaraların bir kısmı okunmuş ve hepsi konumla uyuşuyorsa kabul."""
    satirlar = [f"EV{i} - DEP{i}" for i in range(1, 16)]
    satirlar[0] = "1. | EV1 - DEP1"
    satirlar[14] = "15. | EV15 - DEP15"
    maclar, _ = bulten.satirlari_ayristir(_metin(*satirlar))
    assert len(maclar) == 15


# ─── ayırıcı ──────────────────────────────────────────────────────────────────

def test_bosluklu_tire_ayirir():
    assert bulten._ikiye_ayir("A TAKIMI - B TAKIMI") == ["A TAKIMI", "B TAKIMI"]


def test_tek_yanli_bosluk_da_ayirir():
    """Ölçüldü: OCR bir boşluğu yutabiliyor (`KONYASPOR -RİZESPOR`)."""
    assert bulten._ikiye_ayir("KONYASPOR -RİZESPOR") == ["KONYASPOR", "RİZESPOR"]
    assert bulten._ikiye_ayir("KONYASPOR- RİZESPOR") == ["KONYASPOR", "RİZESPOR"]


def test_takim_adindaki_tire_ayirici_DEGIL():
    """İki yanı da boşluksuz tire takım adının kendi tiresidir."""
    assert bulten._ikiye_ayir("SAINT-ETIENNE") == []
    assert bulten._ikiye_ayir("SAINT-ETIENNE - LYON") == ["SAINT-ETIENNE", "LYON"]


# ─── biçimsel temizlik ────────────────────────────────────────────────────────

def test_sutun_artigi_atilir():
    """`12.İ VALENCİA` — dikey çizgi `İ` diye okunmuş."""
    assert bulten._temizle("İ VALENCİA") == "VALENCİA"
    assert bulten._temizle("| CHELSEA") == "CHELSEA"


def test_gercek_adin_ilk_harfi_yenmez():
    """Tek harflik artık atılır ama gerçek ad bozulmaz."""
    assert bulten._temizle("İSTANBULSPOR A.Ş.") == "İSTANBULSPOR A.Ş."
    assert bulten._temizle("INTER") == "INTER"


def test_harf_DUZELTILMEZ():
    """Doktrin 2: OCR çıktısı arama anahtarıdır, düzeltilmez."""
    assert bulten._temizle("BAŞAKŞEMİM FK") == "BAŞAKŞEMİM FK"


# ─── doğrulama kapısı ─────────────────────────────────────────────────────────

def _hafta_kaydi(week: int = 1) -> dict:
    return {"week": week, "season": "2023/2024", "kabul": True,
            "matches": [{"no": i, "home": f"EV{i}", "away": f"DEP{i}"}
                        for i in range(1, 16)]}


def test_dogrulama_saglam_seti_gecirir():
    bulten.dogrula({"2023_24": [_hafta_kaydi(1), _hafta_kaydi(2)]})


def test_sirasi_bozuk_hafta_yazilmaz():
    h = _hafta_kaydi()
    h["matches"][3]["no"] = 9
    with pytest.raises(AssertionError, match="sira bozuk"):
        bulten.dogrula({"2023_24": [h]})


def test_eksik_macli_hafta_yazilmaz():
    h = _hafta_kaydi()
    h["matches"].pop()
    with pytest.raises(AssertionError):
        bulten.dogrula({"2023_24": [h]})


def test_mukerrer_hafta_yazilmaz():
    with pytest.raises(AssertionError, match="mukerrer"):
        bulten.dogrula({"2023_24": [_hafta_kaydi(1), _hafta_kaydi(1)]})


# ─── yayındaki çıktı ──────────────────────────────────────────────────────────

def _sezon_dosyalari():
    return sorted(p for p in bulten.CIKTI_DIZIN.glob("*.json")
                  if p.name != "bulten_rapor.json")


def test_yayindaki_bulten_okunabilir():
    dosyalar = _sezon_dosyalari()
    if not dosyalar:
        pytest.skip("bülten henüz üretilmemiş (scripts/build_bulten.py)")
    for yol in dosyalar:
        govde = json.loads(yol.read_text(encoding="utf-8"))
        assert govde["meta"]["season_key"] == yol.stem
        assert govde["meta"]["weeks"] == len(govde["weeks"])
        for h in govde["weeks"]:
            assert [m["no"] for m in h["matches"]] == list(range(1, 16))


def test_yayindaki_bultende_SONUC_yok():
    """Bu setin sınırı: skor, sonuç ve oran taşımaz.

    Bir gün taşımaya başlarsa bu test kırılır ve kırılması DOĞRUDUR.
    """
    dosyalar = _sezon_dosyalari()
    if not dosyalar:
        pytest.skip("bülten henüz üretilmemiş")
    for yol in dosyalar:
        govde = json.loads(yol.read_text(encoding="utf-8"))
        assert "does_not_contain" in govde["meta"]
        for h in govde["weeks"]:
            assert "results" not in h
            for m in h["matches"]:
                assert set(m) == {"no", "home", "away"}


# ─── uçtan uca (OCR gerekir) ──────────────────────────────────────────────────

@pytest.mark.skipif(not OCR_VAR, reason="ocr ekstrasi kurulu degil")
def test_gercek_gorselden_okuma():
    """Yayındaki bir görselden 15 maç okunabiliyor mu — uçtan uca."""
    kaynak = bulten.CIKTI_DIZIN / "_kaynak"
    gorseller = sorted(kaynak.glob("*.jpg")) + sorted(kaynak.glob("*.jpeg"))
    if not gorseller:
        pytest.skip("indirilmiş görsel yok (_kaynak git dışı)")
    metin = bulten.ocr_metni(gorseller[0])
    maclar, _ = bulten.satirlari_ayristir(metin)
    assert len(maclar) == 15, f"{gorseller[0].name}: {len(maclar)} satır okundu"
