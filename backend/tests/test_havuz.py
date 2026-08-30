"""Havuz — bölüşüm kuralı, devir geri hesabı ve zincir denetimi.

Testler iki katmanlı:

* **Sentetik** — kural elle kurulmuş tablolarda tek tek sınanır. Bunlar ağa
  ve yayındaki veriye bakmaz; kuralın kendisini korur.
* **Yayındaki arşiv** — 222 haftanın ölçülen sayıları çıpalanır. Bu sayılar
  değişirse ya arşiv büyümüştür (beklenen) ya da model bozulmuştur; ikisi
  de görünür olmalı, bu yüzden çıpa var.

`havuz.py`'nin başlığındaki her sayı burada bir teste bağlıdır. Belgeye
yazılan ama korunmayan sayı, bir sonraki değişiklikte sessizce yanlış olur.
"""

import json

import pytest

from spor_toto import havuz


def _payout(**kademe: tuple[int, float]) -> dict:
    """`_payout(k15=(3, 100.0), ...)` -> resmî uçtaki `payout` şekli."""
    sira = sorted((int(k[1:]) for k in kademe), reverse=True)
    return {"currency": "TRY", "tiers": [
        {"correct": k,
         "winners": kademe[f"k{k}"][0],
         "prize": kademe[f"k{k}"][1]}
        for k in sira
    ]}


def _duzgun(birim: float = 1_000_000.0) -> dict:
    """Devirsiz, kurala birebir uyan bir hafta: 1,75 / 1 / 1 / 1,25."""
    return _payout(
        k15=(1, havuz.BOLUSUM[15] * birim),
        k14=(1, havuz.BOLUSUM[14] * birim),
        k13=(1, havuz.BOLUSUM[13] * birim),
        k12=(1, havuz.BOLUSUM[12] * birim),
    )


# ─── bölüşüm sabiti ───────────────────────────────────────────────────────────

def test_bolusum_35_20_20_25():
    """Ölçülen bölüşüm; `havuz.py` başlığındaki tablonun çıpası."""
    assert havuz.BOLUSUM == {15: 1.75, 14: 1.0, 13: 1.0, 12: 1.25}
    yuzde = {k: round(100 * v) for k, v in havuz.YUZDE.items()}
    assert yuzde == {15: 35, 14: 20, 13: 20, 12: 25}
    assert sum(havuz.YUZDE.values()) == pytest.approx(1.0)


# ─── birim seçimi ─────────────────────────────────────────────────────────────

def test_birim_13_ve_14un_KUCUGU():
    """Devir ancak şişirir; iki eşit paydan küçüğü temiz olandır."""
    assert havuz._birim({13: 100.0, 14: 100.0}) == 100.0
    assert havuz._birim({13: 100.0, 14: 158.0}) == 100.0
    # 13 devir aldıysa küçük olan 14'tür ve birim odur.
    assert havuz._birim({13: 158.0, 14: 100.0}) == 100.0


def test_birim_kazanansiz_kademeyi_kullanmaz():
    """Havuzu 0 olan kademe birim adayı değildir — yoksa birim 0 çıkardı."""
    assert havuz._birim({13: 100.0, 14: 0.0}) == 100.0
    assert havuz._birim({13: 0.0, 14: 0.0}) is None


# ─── temel hesap ──────────────────────────────────────────────────────────────

def test_duzgun_haftada_devir_yok():
    v = havuz.hafta_havuzu(_duzgun())
    assert v is not None
    assert v["bolusum_tutuyor"]
    assert v["devir_gelen"] == 0
    assert v["devreden"] == []
    assert v["dagitilan"] == pytest.approx(5_000_000.0)  # 1,75+1+1+1,25 birim


def test_ikramiyesiz_hafta_none():
    assert havuz.hafta_havuzu(None) is None
    assert havuz.hafta_havuzu({"tiers": []}) is None


def test_kademe_alani_null_ise_atlanir():
    """"kimse bilemedi" (0) ile "veri yok" (None) ayrı şeylerdir."""
    p = _duzgun()
    p["tiers"][0]["winners"] = None
    v = havuz.hafta_havuzu(p)
    assert v is not None
    assert 15 not in v["kademeler"]      # veri yok → hiç girmez
    assert v["devreden"] == []           # devretmiş de sayılmaz


# ─── devir ────────────────────────────────────────────────────────────────────

def test_kazanansiz_kademe_devreder_sapma_degil():
    """15 kazanansızsa bu bir bölüşüm sapması DEĞİL, devretmedir.

    İlk yazım bunu sapma sayıyordu ve 46 haftayı yanlış işaretlemişti.
    """
    p = _duzgun()
    p["tiers"][0]["winners"] = 0
    v = havuz.hafta_havuzu(p)
    assert v is not None
    assert v["bolusum_tutuyor"], "kazanansız kademe sapma sayılmamalı"
    assert v["devreden"] == [15]
    assert v["devir_giden"] == pytest.approx(1_750_000.0)
    assert v["devir_giden_kesin"] is False


def test_devir_15e_OZGU_degil():
    """Kazanansız kalan HER kademe devreder — 14 de dahil."""
    p = _duzgun()
    p["tiers"][0]["winners"] = 0   # 15
    p["tiers"][1]["winners"] = 0   # 14
    v = havuz.hafta_havuzu(p)
    assert v is not None
    assert v["devreden"] == [15, 14]
    assert v["bolusum_tutuyor"]


def test_sisen_kademe_devir_olarak_okunur():
    p = _duzgun()
    p["tiers"][0]["prize"] = havuz.BOLUSUM[15] * 1_000_000.0 + 500_000.0
    v = havuz.hafta_havuzu(p)
    assert v is not None
    assert v["devir_gelen"] == pytest.approx(500_000.0)
    # Devir haftanın kendi payı DEĞİLDİR ve dağıtılandan düşülür.
    assert v["dagitilan"] == pytest.approx(5_000_000.0)
    assert v["toplam"] == pytest.approx(5_500_000.0)


def test_beklenenin_ALTI_devir_degil_sapmadir():
    """Devir ancak ekleyebilir; eksik bir kademe gerçek sapmadır."""
    p = _duzgun()
    p["tiers"][3]["prize"] = havuz.BOLUSUM[12] * 1_000_000.0 * 0.75
    v = havuz.hafta_havuzu(p)
    assert v is not None
    assert not v["bolusum_tutuyor"]
    assert 12 in v["sapmalar"]


def test_kurus_yuvarlamasi_devir_sayilmaz():
    """Binde birin altındaki fazlalık yuvarlamadır; 41 haftayı 174 yapan hata."""
    p = _duzgun()
    p["tiers"][0]["prize"] = havuz.BOLUSUM[15] * 1_000_000.0 + 900.0  # 9e-4
    v = havuz.hafta_havuzu(p)
    assert v is not None
    assert v["devir_gelen"] == 0
    assert v["bolusum_tutuyor"]


# ─── yayındaki arşiv ──────────────────────────────────────────────────────────

def _arsiv_var() -> bool:
    return any(p.name != "arsiv_rapor.json"
               for p in havuz.VARSAYILAN_DIZIN.glob("*.json"))


def test_yayindaki_arsiv_kurala_oturuyor():
    """222 haftanın 220'si modele uyuyor; uymayan 2'si BİLİNİYOR.

    Bu çıpa gevşetilmemeli: sayı büyürse model bozulmuş demektir.
    """
    if not _arsiv_var():
        pytest.skip("arşiv henüz üretilmemiş")
    ozet = havuz.havuz_ozeti()
    assert ozet["havuz_hesaplanan"] >= 220
    assert ozet["bolusum_bozuk_hafta"] <= 2, (
        f"model açıklayamayan hafta arttı: {ozet['bolusum_bozuk_hafta']}")


def test_devir_zinciri_kapaniyor():
    """Modelin BAĞIMSIZ kanıtı: giden devir ertesi hafta gelen devre eşit."""
    if not _arsiv_var():
        pytest.skip("arşiv henüz üretilmemiş")
    z = havuz.devir_zinciri()
    assert z["eslesen"] >= 40
    assert z["birebir"] / z["eslesen"] >= 0.85
    assert z["oran_ortanca"] == pytest.approx(1.0, abs=0.01)


def test_devir_orani_BIRIN_ALTINA_dusmez():
    """Devir ancak ekleyebilir. Altına düşen bir hafta modeli çürütür."""
    if not _arsiv_var():
        pytest.skip("arşiv henüz üretilmemiş")
    assert havuz.devir_zinciri()["birin_altina_dusen"] == 0


def test_elle_girilen_kayitla_kurusuna_kadar_ayni():
    """Bağımsız çapraz doğrulama: §6B elle girilen not ile hesap aynı sayı.

    Elle girilen kayıt bir ekran görüntüsünden yazıldı, hesap resmî uçtan
    türetildi. İkisi birbirini görmüyor.
    """
    yol = havuz.VARSAYILAN_DIZIN / "2026_27.json"
    elle = havuz.KOK / "data" / "super_toto" / "2026_27" / "hafta_02.json"
    if not yol.exists() or not elle.exists():
        pytest.skip("veri yok")

    hafta = next(w for w in json.loads(yol.read_text(encoding="utf-8"))["weeks"]
                 if w["week"] == 2)
    v = havuz.hafta_havuzu(hafta["payout"])
    assert v is not None

    # Elle girilen not: haftanın kendi payı 42.842.867,72 TL.
    kendi_payi_15 = havuz.BOLUSUM[15] * v["birim"]
    assert kendi_payi_15 == pytest.approx(42_842_867.72, abs=1.0)

    not_metni = json.loads(elle.read_text(encoding="utf-8"))["meta"]["payout"]["note"]
    assert "42.842.867,72" in not_metni, "elle girilen not değişmiş — çıpa gözden geçirilmeli"


def test_ozet_sinirini_yaziyor():
    """Doktrin 7: brüt hasılat DEĞİL dağıtılan havuz — her çıktıda yazar."""
    if not _arsiv_var():
        pytest.skip("arşiv henüz üretilmemiş")
    sinir = havuz.havuz_ozeti()["sinir"]
    assert "brut hasilat DEGILDIR" in sinir
    assert "KOLON" in sinir
