"""Kupon motorunun bekçileri (`spor_toto/kupon_motor.py`).

**Bu dosyanın tek işi bir cümleyi koşulabilir kılmak:** *"motor 5. haftayı
tekrar edebiliyor."* O cümle bir iddia olarak söylendi (sahibine: "hafta 6
verisini girince tuşa basınca hafta 5'in aynısını yapar"), ve iddia
edilen şey tam olarak şudur — aynı oranlar girildiğinde motorun
**oynanan kuponun on beş işaretini de** yeniden üretmesi.

Karşılaştırılan kayıt `data/super_toto/2026_27/hafta_05_kupon.json`'dur ve
o dosya sonuçlar GÖRÜLMEDEN donduruldu (`frozen_at: 2026-09-10`,
`results_known: false`). Yani bu test bir geri uydurma değil: kupon o gün
neyse, bugün de o çıkmalı.

Üç varyant da tutuluyor, çünkü üçü ayrı bir şey söylüyor:

    variants[0]  kapanış · bütçenin seçtiği şekil   6b/0ç/9ü  P = 0,951801
    variants[1]  kapanış · sabit şekil              5b/5ç/5ü  P = 0,799613
    variants[2]  açılış  · bütçenin seçtiği şekil   6b/0ç/9ü  P = 0,945670

`variants[1]`in ayrıca bağımsız bir kanıtı var ve kayıt onu yazıyor:
`C(15,5) · C(10,5) = 756.756` atamanın TAMAMI gezildiğinde aynı plan çıktı.
Yani `sekilli_secim` bir yaklaşıklık değil, o şeklin en iyisidir.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from spor_toto import kupon_motor as km
from spor_toto.core import SEMBOLLER
from spor_toto.secim import bedel_hesapla, hedef_olasiligi, sekilli_secim

KOK = Path(__file__).resolve().parent.parent
HAFTA5 = KOK / "data" / "super_toto" / "2026_27" / "hafta_05.json"
KUPON5 = KOK / "data" / "super_toto" / "2026_27" / "hafta_05_kupon.json"


def _hafta5() -> dict:
    if not HAFTA5.exists() or not KUPON5.exists():
        pytest.skip("5. haftanin kaydi yok")
    return {
        "hafta": json.loads(HAFTA5.read_text(encoding="utf-8")),
        "kupon": json.loads(KUPON5.read_text(encoding="utf-8")),
    }


def _oranlar(hafta: dict, anahtar: str) -> list[dict[str, float]]:
    return [m["odds_books"][anahtar] for m in hafta["matches"]]


def test_mac_sayisi_TEK_kaynaktan():
    """15 iki yerde yazılı olamaz."""
    from spor_toto.meta import MATCH_COUNT
    assert km.MAC_SAYISI == MATCH_COUNT


def test_5_HAFTANIN_OYNANAN_kuponu_BIREBIR_yeniden_uretiliyor():
    """Bu testin düşmesi "motor hafta 5'i tekrar edemiyor" demektir.

    Karşılaştırma **tam**: on beş işaretin on beşi ve `P(k ≤ 3)`. Tolerans
    bilerek yok — planın bir maçta kayması, kuponun o maçını değiştirmek
    demektir ve "yaklaşık aynı kupon" diye bir şey yoktur.
    """
    v = _hafta5()
    govde = {"cizgiler": {c: _oranlar(v["hafta"], f"pinnacle_{c}")
                          for c in ("acilis", "kapanis")}}
    cevap = km.motoru_kos(govde)

    kayit = v["kupon"]["variants"]
    bekleniyor = [
        ("kapanis", "hak", kayit[0]),
        ("kapanis", f"sabit{km.SABIT_CIFT}c{km.SABIT_UCLU}u", kayit[1]),
        ("acilis", "hak", kayit[2]),
    ]
    for cizgi, anahtar, beklenen in bekleniyor:
        planlar = {p["anahtar"]: p for p in cevap["cizgiler"][cizgi]["planlar"]}
        plan = planlar[anahtar]
        assert ["".join(x) for x in plan["isaretler"]] == beklenen["picks"], (
            f"{cizgi}/{anahtar}: isaretler kayitla ayrisiyor")
        assert plan["kolon"] == beklenen["columns"]
        assert plan["sekil"] == beklenen["sekil"]
        assert round(plan["p_hedef"], 6) == round(beklenen["hedef"], 6)


def test_odenen_olay_ile_kapsama_olcusu_KARISTIRILMIYOR():
    """`p_kacaksiz` (15. kademe) ile `p_hedef` (k ≤ 3) ayrı sayılardır."""
    v = _hafta5()
    cevap = km.motoru_kos({"cizgiler": {"kapanis": _oranlar(v["hafta"], "pinnacle_kapanis")}})
    plan = cevap["cizgiler"]["kapanis"]["planlar"][0]
    kayit = v["kupon"]["variants"][0]
    assert round(plan["p_kacaksiz"], 6) == round(kayit["p_kacaksiz"], 6)
    assert plan["p_kacaksiz"] < plan["p_hedef"], "15 tutturmak >=12'den zordur"


def test_TAVANA_DAYANMA_gorunur_kalir():
    """Şekli hafta değil TAVAN seçtiyse bu gizlenmemeli.

    5. haftada kural serbestken 59.049 kolon istiyordu; tavan onu 19.683'e
    kıstı. Bunu yazmayan bir çıktı, "motor bu şekli seçti" diye okunurdu.
    """
    v = _hafta5()
    cevap = km.motoru_kos({"cizgiler": {"kapanis": _oranlar(v["hafta"], "pinnacle_kapanis")}})
    hak = cevap["cizgiler"]["kapanis"]["planlar"][0]
    assert hak["tavana_dayandi"] is True
    assert hak["serbest_kolon"] == 59049, "kayittaki gerekce bu sayiyi yaziyor"
    # Sabit sekil tavana DAYANMAZ: bedelini sekil belirler, butce degil.
    sabit = cevap["cizgiler"]["kapanis"]["planlar"][1]
    assert sabit["tavana_dayandi"] is False and sabit["serbest_kolon"] is None
    assert sabit["kolon"] == bedel_hesapla(km.SABIT_CIFT, km.SABIT_UCLU) == 7776


def test_sabit_sekil_KABA_KUVVETLE_ayni_cikiyor():
    """`sekilli_secim` bir yaklaşıklık değil, o şeklin EN İYİSİ.

    Kaba kuvvet burada 15 maçla koşulamaz (756.756 atama x DP); onun yerine
    küçük ve TAM çözülebilir bir vaka kuruluyor: 6 maç, (çifte=2, üçlü=2).
    Bütün atamalar gezilip en iyi `P(k ≤ 1)` bulunuyor ve DP'ninkiyle
    karşılaştırılıyor. Pareto budamasının değer kaçırmadığı iddiası budur.
    """
    import itertools

    probs = [
        {"1": 0.70, "0": 0.20, "2": 0.10},
        {"1": 0.45, "0": 0.30, "2": 0.25},
        {"1": 0.34, "0": 0.33, "2": 0.33},
        {"1": 0.55, "0": 0.28, "2": 0.17},
        {"1": 0.40, "0": 0.35, "2": 0.25},
        {"1": 0.62, "0": 0.23, "2": 0.15},
    ]
    esik, cift, uclu = 1, 2, 2
    sirali = [sorted(p, key=lambda s: (-p[s], SEMBOLLER.index(s))) for p in probs]

    en_iyi = -1.0
    for yerler in itertools.permutations(range(len(probs))):
        seviyeler = [1] * len(probs)
        for i in yerler[:cift]:
            seviyeler[i] = 2
        for i in yerler[cift:cift + uclu]:
            seviyeler[i] = 3
        secimler = [sirali[i][:seviyeler[i]] for i in range(len(probs))]
        en_iyi = max(en_iyi, hedef_olasiligi(probs, secimler, esik=esik))

    plan = sekilli_secim(probs, cift=cift, uclu=uclu, esik=esik)
    assert plan is not None
    assert plan.cift == cift and plan.uclu == uclu
    assert round(plan.p_hedef, 12) == round(en_iyi, 12), (
        "DP kaba kuvvetin bulduğu en iyiyi kaçırdı — Pareto budaması güvenli değil")


def test_sekilli_secim_sinirlari():
    probs = [{"1": 0.5, "0": 0.3, "2": 0.2}] * 5
    with pytest.raises(ValueError):
        sekilli_secim(probs, cift=-1, uclu=0)
    with pytest.raises(ValueError):
        sekilli_secim(probs, cift=4, uclu=4)  # 8 > 5 mac
    # Hepsi banko: sekil gecerli ve bedeli 1 kolon.
    hepsi_banko = sekilli_secim(probs, cift=0, uclu=0)
    assert hepsi_banko is not None and hepsi_banko.bedel == 1
    assert hepsi_banko.banko == 5


def test_tek_cizgi_yeter_oteki_ATLANIR():
    """Elinde yalnızca kapanış bülteni olan kullanıcı engellenmez."""
    v = _hafta5()
    cevap = km.motoru_kos({"cizgiler": {"kapanis": _oranlar(v["hafta"], "pinnacle_kapanis")}})
    assert set(cevap["cizgiler"]) == {"kapanis"}
    with pytest.raises(km.MotorHatasi):
        km.motoru_kos({"cizgiler": {}})


def test_bozuk_govde_REDDEDILIR():
    v = _hafta5()
    tam = _oranlar(v["hafta"], "pinnacle_kapanis")

    # Bilinmeyen cizgi SESSIZCE ATILMAZ.
    with pytest.raises(km.MotorHatasi, match="bilinmeyen cizgi"):
        km.motoru_kos({"cizgiler": {"AvgC": tam}})
    # Eksik satir: motor kosacak, yarim tablo o maci korlestirirdi.
    with pytest.raises(km.MotorHatasi, match="tam 15"):
        km.motoru_kos({"cizgiler": {"kapanis": tam[:14]}})
    # 1.00 ve alti oran degildir; bos hucre de burada gecersizdir.
    for bozuk in (1.0, 0.5, 0, -2, None, "", "abc", float("inf")):
        kirik = [dict(x) for x in tam]
        kirik[3] = {**kirik[3], "0": bozuk}
        with pytest.raises(km.MotorHatasi, match="4. satir"):
            km.motoru_kos({"cizgiler": {"kapanis": kirik}})
    for bozuk in ({"arindirma": "yok"}, {"butce_tl": 0}, {"butce_tl": -5},
                  {"butce_tl": "cok"}, {"sezon": "1900_01"}):
        with pytest.raises(km.MotorHatasi):
            km.motoru_kos({"cizgiler": {"kapanis": tam}, **bozuk})


def test_ARINDIRMA_sonucu_degistirir_ve_kayitta_durur():
    """Yöntem seçimi sonucu değiştirir; cevap hangisiyle koşulduğunu söyler."""
    v = _hafta5()
    tam = _oranlar(v["hafta"], "pinnacle_kapanis")
    shin = km.motoru_kos({"cizgiler": {"kapanis": tam}, "arindirma": "shin"})
    oran = km.motoru_kos({"cizgiler": {"kapanis": tam}, "arindirma": "orantili"})
    assert shin["arindirma"] == "shin" and oran["arindirma"] == "orantili"
    assert (shin["cizgiler"]["kapanis"]["planlar"][0]["p_hedef"]
            != oran["cizgiler"]["kapanis"]["planlar"][0]["p_hedef"])


def test_odul_vektoru_NEDENSEL_ve_cevapla_gidiyor():
    """Vektör bu sezonun değil, bir ÖNCEKİNİN tablosudur."""
    from spor_toto.karne import odul_vektoru_onceki

    v = _hafta5()
    cevap = km.motoru_kos({"cizgiler": {"kapanis": _oranlar(v["hafta"], "pinnacle_kapanis")}})
    beklenen = odul_vektoru_onceki(km.VARSAYILAN_SEZON)
    assert cevap["odul_vektoru"] == {str(k): v2 for k, v2 in sorted(beklenen.items())}
    assert cevap["butce_kolon"] == 21000, "₺210.000 / ₺10 = 21.000 kolon"
