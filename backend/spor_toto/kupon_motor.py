"""Kupon kurucunun **motor** halkası — `/kupon` sayfasının düğmesi.

`/kupon` sayfası bugüne kadar tek bir kaynaktan kupon kuruyordu: **karne**
(`benzer` — "bu fiyatta geçmişte ne olmuş"). Bu modül ikinci kaynağı
bağlıyor: haftanın kuponunu fiilen kuran **motor** (`secim.odul_secim` ve
`secim.sekilli_secim`).

─── Niçin gerekti ───────────────────────────────────────────────────────

Sahibinin isteği, kendi cümlesiyle: *"hafta 5 için yaptığımız her şeyi,
hafta 6 verilerini girince tuşa basınca hafta 6 için yapmalı."* 5. haftanın
**oynanan** kuponu karneden değil motordan çıkmıştı
(`data/super_toto/2026_27/hafta_05_kupon.json`) ve o zincir yalnızca
komut satırında vardı (`scripts/hafta_kos.py --oncesi`). Sayfadaki düğme o
zinciri çağırabilsin diye gövde buraya alındı — Flask'tan bağımsız, yani
testi tarayıcı da sunucu da gerektirmiyor.

─── Girdi NEDEN yalnızca oran ───────────────────────────────────────────

Bu modül tahmin ÜRETMEZ. Olasılık, oranın marjı atılmış hâlidir
(`odds.implied_probs`, varsayılan `shin`) — takım kimliği, form, model
YOK. `scripts/super_toto_hafta.py` da baştan beri aynı şeyi yapıyor
("Bu script tahmin üretmez"). Sonucu şudur: sayfanın elle girilen 15
satırlık oran tablosu motoru beslemeye **yeter**; takım adı eşleştirmesi
gerekmiyor ve o eşleştirmenin bilinen kusuru buraya sızmıyor.

─── İki plan, iki ayrı soru ─────────────────────────────────────────────

``hak``
    Şekli **bütçe** seçer. `odul_secim` beklenen parayı enbüyükler ve
    kademeler kendi ağırlığıyla girer (15, 12'den 772 kat çok ödüyor).
    Vektör `karne.odul_vektoru_onceki` ile **nedenseldir**: bu sezonun ödül
    ölçeği kupon kurulurken henüz bilinmez.
``sabit``
    Şekli **kullanıcı** seçer (5 banko / 5 çifte / 5 üçlü) ve `sekilli_secim`
    o şeklin kanıtlanmış en iyisini verir.

─── Bekçi: 5. hafta BİREBİR yeniden üretiliyor ──────────────────────────

`tests/test_kupon_motor.py` bu modülü 5. haftanın iki fiyat çizgisiyle
koşar ve `hafta_05_kupon.json`un üç varyantının **on beş işaretini de**
karşılaştırır:

    kapanış · hak    6b/0ç/9ü  19.683 kolon  P(k≤3) = 0,951801  (variants[0])
    kapanış · sabit  5b/5ç/5ü   7.776 kolon  P(k≤3) = 0,799613  (variants[1])
    açılış  · hak    6b/0ç/9ü  19.683 kolon  P(k≤3) = 0,945670  (variants[2])

Bu üç sayı bu modülün ölçüsüdür: "motor hafta 5'i tekrar edebiliyor mu"
sorusu bir iddia değil, koşulan bir testtir.
"""
from __future__ import annotations

from typing import Any

from .backtest import VARSAYILAN_BUTCE_TL
from .core import SEMBOLLER
from .getiri import KOLON_BEDELI
from .karne import odul_vektoru_onceki
from .odds import ARINDIRMA_VARSAYILAN, ARINDIRMA_YONTEMLERI, implied_probs
from .secim import (
    DEGER_TAVANI,
    VARSAYILAN_KACAK_ESIGI,
    Secim,
    hedef_olasiligi,
    odul_secim,
    sekilli_secim,
)

#: Bir haftada kaç maç. `core.SEMBOLLER` gibi tek kaynaktan gelmeli.
MAC_SAYISI = 15

#: Sabit şeklin sayıları — sahibinin kararı, ölçüm değil.
#: 5 banko + 5 çifte + 5 üçlü = `2^5 · 3^5` = 7.776 kolon.
SABIT_CIFT, SABIT_UCLU = 5, 5

#: Nedensel ödül vektörünün okunduğu sezon. Vektör bu sezonun DEĞİL, bir
#: ÖNCEKİNİN tablosudur (`karne.odul_vektoru_onceki` künyesi).
VARSAYILAN_SEZON = "2026_27"


class MotorHatasi(ValueError):
    """Girdi kabul edilemez. Çağıran bunu 400'e çevirir."""


def _oran(ham: Any, nerede: str) -> float:
    """Tek oran hücresi — 1,00 ve altı REDDEDİLİR, boş da geçersizdir.

    `kupon_arsivi._oran`dan farkı bilerek: orada yarım bir tablo
    **kaydedilebilir** (insan doldururken de kaydeder), burada ise motor
    koşacak ve eksik bir oran o maçı körleştirirdi.
    """
    try:
        v = float(ham)
    except (TypeError, ValueError):
        raise MotorHatasi(f"{nerede}: oran okunamadi: {ham!r}") from None
    if not (v > 1.0) or v != v or v in (float("inf"), float("-inf")):
        raise MotorHatasi(f"{nerede}: oran 1.00'den buyuk olmali: {ham!r}")
    return v


def oranlari_dogrula(ham: Any, cizgi: str) -> list[dict[str, float]]:
    """15 satırlık `{1, 0, 2}` oran listesi. Eksik satır REDDEDİLİR."""
    if not isinstance(ham, list):
        raise MotorHatasi(f"{cizgi}: oranlar bir liste olmali")
    if len(ham) != MAC_SAYISI:
        raise MotorHatasi(
            f"{cizgi}: oranlar tam {MAC_SAYISI} olmali, {len(ham)} geldi")
    cikti: list[dict[str, float]] = []
    for i, satir in enumerate(ham, start=1):
        if not isinstance(satir, dict):
            raise MotorHatasi(f"{cizgi} {i}. satir bir nesne olmali")
        cikti.append({s: _oran(satir.get(s), f"{cizgi} {i}. satir {s}")
                      for s in SEMBOLLER})
    return cikti


def _plan_govdesi(anahtar: str, ad: str, plan: Secim,
                  probs: list[dict[str, float]],
                  kolon_bedeli: float,
                  tavana_dayandi: bool = False,
                  serbest_kolon: int | None = None) -> dict[str, Any]:
    """Bir planın arayüze giden hâli — sayılar HESAPLANIR, yazılmaz."""
    return {
        "anahtar": anahtar,
        "ad": ad,
        "isaretler": [list(s) for s in plan.secimler],
        "kolon": plan.bedel,
        "bedel_tl": plan.bedel * kolon_bedeli,
        "banko": plan.banko,
        "cift": plan.cift,
        "uclu": plan.uclu,
        "sekil": f"{plan.banko}b/{plan.cift}ç/{plan.uclu}ü",
        # `P(k <= 3)` = `P(en iyi kolon >= 12)`; duzde en iyi kolon 15 - k.
        "p_hedef": plan.p_hedef,
        # ODEYEN olay: 15. kademe. Hedef KAPSAMA olcusudur, bu degil.
        "p_kacaksiz": hedef_olasiligi(probs, plan.secimler, esik=0),
        # Plan butce yuzunden mi kisildi — sekli hafta degil TAVAN seciyorsa
        # bu gorunmeli, yoksa "motor bu sekli sectiu" yanlis okunur.
        "tavana_dayandi": tavana_dayandi,
        "serbest_kolon": serbest_kolon,
    }


def cizgi_planlari(oranlar: list[dict[str, float]],
                   odul_vektoru: dict[int, float],
                   butce_kolon: int,
                   arindirma: str = ARINDIRMA_VARSAYILAN,
                   kolon_bedeli: float = KOLON_BEDELI,
                   esik: int = VARSAYILAN_KACAK_ESIGI) -> dict[str, Any]:
    """Tek fiyat çizgisinin iki planı: bütçenin seçtiği şekil ve sabit şekil."""
    probs = [implied_probs(o, arindirma) for o in oranlar]

    # `hak`: once TAVANSIZ (guvenlik supabi `DEGER_TAVANI`) kosulur ki
    # "kural serbestken ne isterdi" gorunsun; asiyorsa butceye kisilir.
    serbest = odul_secim(probs, odul_vektoru, kolon_bedeli=kolon_bedeli,
                         kademe=15 - esik, tavan=DEGER_TAVANI)
    if serbest is None:
        raise MotorHatasi("bu girdide plan kurulamadi (odul_secim bos dondu)")
    tavana_dayandi = serbest.bedel > butce_kolon
    if tavana_dayandi:
        hak = odul_secim(probs, odul_vektoru, kolon_bedeli=kolon_bedeli,
                         kademe=15 - esik, tavan=butce_kolon)
        if hak is None:
            raise MotorHatasi("butce altinda plan kurulamadi")
    else:
        hak = serbest

    sabit = sekilli_secim(probs, cift=SABIT_CIFT, uclu=SABIT_UCLU, esik=esik)
    if sabit is None:
        raise MotorHatasi("sabit sekilli plan kurulamadi")

    return {
        "probs": [{s: p[s] for s in SEMBOLLER} for p in probs],
        "marjlar": [sum(1.0 / o[s] for s in SEMBOLLER) - 1.0 for o in oranlar],
        "planlar": [
            _plan_govdesi(
                "hak", "Bütçenin seçtiği şekil", hak, probs, kolon_bedeli,
                tavana_dayandi=tavana_dayandi,
                serbest_kolon=serbest.bedel if tavana_dayandi else None),
            _plan_govdesi(
                f"sabit{SABIT_CIFT}c{SABIT_UCLU}u",
                f"Sabit şekil — {MAC_SAYISI - SABIT_CIFT - SABIT_UCLU} banko"
                f" · {SABIT_CIFT} çift · {SABIT_UCLU} üçlü",
                sabit, probs, kolon_bedeli),
        ],
    }


def motoru_kos(govde: dict[str, Any]) -> dict[str, Any]:
    """Gövdeden planları kurar — saf, diske dokunmaz, ağ açmaz.

    Gövde: `{cizgiler: {acilis?: [...15], kapanis?: [...15]}, arindirma?,
    butce_tl?, sezon?}`. En az bir çizgi dolu olmalı; biri boşsa o çizgi
    **atlanır** (elinde tek bülten olan kullanıcı engellenmez).
    """
    from .benzer import CIZGILER

    if not isinstance(govde, dict):
        raise MotorHatasi("govde bir nesne olmali")

    arindirma = str(govde.get("arindirma") or ARINDIRMA_VARSAYILAN).strip()
    if arindirma not in ARINDIRMA_YONTEMLERI:
        raise MotorHatasi(f"arindirma: {', '.join(ARINDIRMA_YONTEMLERI)}")

    # `or` ile varsayilana dusmek YANLIS ve bekci bunu yakaladi: `0 or
    # VARSAYILAN` varsayilani verir, yani "butce sifir" diyen bir istek
    # sessizce ₺210.000'lik plan alirdi. "Verilmedi" ile "gecersiz verildi"
    # ayri seylerdir (`kupon_arsivi.sezon_dogrula` ayni dersi tasiyor).
    ham_butce = govde.get("butce_tl")
    if ham_butce is None or (isinstance(ham_butce, str) and not ham_butce.strip()):
        butce_tl = float(VARSAYILAN_BUTCE_TL)
    else:
        try:
            butce_tl = float(ham_butce)
        except (TypeError, ValueError):
            raise MotorHatasi(f"butce_tl bir sayi olmali: {ham_butce!r}") from None
    if not (butce_tl > 0) or butce_tl != butce_tl or butce_tl == float("inf"):
        raise MotorHatasi(f"butce_tl pozitif olmali: {ham_butce!r}")
    butce_kolon = int(butce_tl // KOLON_BEDELI)
    if butce_kolon < 1:
        raise MotorHatasi(
            f"butce en az bir kolonu almali (kolon bedeli {KOLON_BEDELI} TL)")

    sezon = str(govde.get("sezon") or VARSAYILAN_SEZON).strip()
    vektor = odul_vektoru_onceki(sezon)
    if not vektor:
        raise MotorHatasi(
            f"{sezon} icin ONCEKI sezonun odul tablosu yok; nedensel vektor "
            "olmadan 'hak' kurali kurulamaz")

    ham_cizgiler = govde.get("cizgiler")
    if not isinstance(ham_cizgiler, dict):
        raise MotorHatasi("cizgiler bir nesne olmali")
    bilinmeyen = [c for c in ham_cizgiler if c not in CIZGILER]
    if bilinmeyen:
        # Sessizce ATILMAZ: yanlis anahtarla gelen bir tablo, kullanicinin
        # kuponunu kaybettigini fark etmemesi demek olurdu.
        raise MotorHatasi(
            f"bilinmeyen cizgi: {bilinmeyen!r} — {', '.join(CIZGILER)}")

    cikti: dict[str, Any] = {}
    for c in CIZGILER:
        ham = ham_cizgiler.get(c)
        if ham is None:
            continue
        cikti[c] = cizgi_planlari(
            oranlari_dogrula(ham, c), vektor, butce_kolon,
            arindirma=arindirma)
    if not cikti:
        raise MotorHatasi("en az bir cizginin 15 orani girilmis olmali")

    return {
        "sezon": sezon,
        "arindirma": arindirma,
        "butce_tl": butce_tl,
        "butce_kolon": butce_kolon,
        "kolon_bedeli_tl": KOLON_BEDELI,
        # Vektor CEVAPLA gidiyor: plan onun uzerine kuruldu ve hangi sezonun
        # tablosuyla kuruldugu gorunmeden "beklenen para" okunamaz.
        "odul_vektoru": {str(k): v for k, v in sorted(vektor.items())},
        "kacak_esigi": VARSAYILAN_KACAK_ESIGI,
        "cizgiler": cikti,
    }
