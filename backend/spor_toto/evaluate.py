"""Tahminci değerlendirme koşumu — "bu tahminci piyasayı geçiyor mu?"

Bu modül tahmin **üretmez**, tahminciyi **ölçer**. Amaç tahmine döndüğünde ilk
yazılan şey bu olmalıydı, çünkü projenin kendi geçmişi ölçümsüz bir iyimserliğin
nasıl göründüğünü gösteriyor: eşik taraması 36 haftanın 4'ünde 14+ diyordu,
aynı yöntemin hold-out'u **0** çıktı. Aradaki fark kazanç değil, aşırı uyumdu.

Üç karar bu koşumu belirliyor:

**1. Hafta dışarıda bırakmalı ölçüm.** Her hafta için tahminci diğer haftalarda
eğitilir ve o haftada ölçülür. Eğitilmeyen tahminciler için sonuç değişmez;
eğitilenler için tek doğru ölçüm budur.

**2. Tahminci değil, tahminci *fabrikası* alınır.** Her kat için sıfırdan bir
örnek kurulur. Tek örnek paylaşılsaydı bir katın eğitimi diğerine sızar ve
"dışarıda bıraktık" cümlesi yalan olurdu.

**3. Güven aralığı hafta üzerinden bootstrap'lenir, maç üzerinden değil.** Aynı
haftanın 15 maçı bağımsız değildir: aynı kupon, aynı hafta sonu, aynı ligler.
Maç üzerinden yeniden örnekleme aralığı olduğundan dar gösterirdi.

Karşılaştırmanın kuralı koddadır: bir aday, `predict.REFERANS_AD` tahmincisini
**eşleştirilmiş bootstrap farkının güven aralığı sıfırın tamamen altında
kalarak** geçmedikçe `gecti` bayrağı `False` döner. "Ortalaması daha iyi çıktı"
yeterli değildir.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from typing import Any

from .backtest import hafta_girdileri
from .ortak import brier as _ortak_brier
from .predict import REFERANS_AD, Girdi, Olasilik, Tahminci, referans_fabrikalar

#: Log kaybında sıfır olasılığa sonsuz ceza vermemek için kırpma tabanı.
#: Tahminci "imkânsız" dediği bir sonuç gerçekleşirse ceza büyük olmalı ama
#: sonlu kalmalı; aksi halde tek bir maç bütün ortalamayı yutar.
LOG_KIRPMA = 1e-15

#: Bootstrap tekrar sayısı ve tohumu. Tohum sabittir: aynı veri aynı aralığı
#: vermezse "ölçtük" demenin anlamı kalmaz.
BOOTSTRAP_TEKRAR = 2000
BOOTSTRAP_TOHUM = 20260817

#: Güven aralığı genişliği.
GUVEN = 0.95

#: Karşılaştırmanın anlamlı olması için gereken en az hafta sayısı. Altında
#: bootstrap aralığı kendi gürültüsünü ölçer.
AZ_HAFTA = 10

#: Tahminci fabrikası: her kat için sıfırdan bir örnek üretir.
Fabrika = Callable[[], Tahminci]


# ─── tek maç ölçütleri ────────────────────────────────────────────────────────

#: Brier artik `ortak`ta; `odds._brier` de ayni govdeyi tasiyordu.
#: Ad burada korunuyor cunku disari/cizgi/bahisci/predict onu buradan alir.
brier = _ortak_brier


def log_kaybi(probs: Olasilik, code: str) -> float:
    """Tek maçın log kaybı: −ln(p_gerçek).

    Brier'den farkı: emin olup yanılmayı çok daha sert cezalandırır. İkisi
    birlikte raporlanır, çünkü bir tahminci Brier'i ortalama yakınında
    oynayarak iyileştirebilir; log kaybı bu oyunu bozar.
    """
    p = probs.get(code, 0.0)
    return -math.log(max(p, LOG_KIRPMA))


# ─── ölçülebilir kesit ────────────────────────────────────────────────────────

def olculebilir_haftalar(last: int | None = None) -> list[Girdi]:
    """Karşılaştırmaya girebilecek haftalar.

    `usable=False` olan hafta elenir — 15 maçın hepsinin oranı yoksa piyasa
    tahmincisi o hafta tahmin üretemez. Bütün tahminciler **aynı** haftalarda
    ölçülmezse karşılaştırma anlamsızdır; bu yüzden eleme tahminci başına
    değil, kesit başına yapılır (veri doktrini 2: eksik veri elenir,
    tamamlanmaz).
    """
    return [h for h in hafta_girdileri(last) if h["usable"]]


# ─── hafta dışarıda bırakmalı koşum ───────────────────────────────────────────

def sezon_anahtari(hafta: Girdi) -> Any:
    """Sezon dışarıda bırakmalı ölçüm için grup anahtarı.

    Eğitim korpusunda (`egitim.korpus_haftalari`) her haftanın `sezon` alanı
    vardır. Sezonu grup yapmak, "bir sezonda eğit, hiç görmediğin başka bir
    sezonda ölç" demeyi sağlar — leave-one-week-out'un veremediği gerçek
    out-of-sample budur ve S1'in asıl istediği şeydir.
    """
    return hafta.get("sezon")


def hafta_disarida_birak(fabrika: Fabrika,
                         haftalar: Sequence[Girdi],
                         grup: Callable[[Girdi], Any] | None = None
                         ) -> list[dict[str, Any]]:
    """Her hafta için: dışarıda bırakılan grupta değil, ötekilerde eğit.

    `grup` verilmezse her hafta kendi grubudur — klasik hafta dışarıda
    bırakmalı ölçüm. `grup=sezon_anahtari` verilirse haftanın **bütün
    sezonu** eğitimden çıkarılır; 31 bin maçlık korpusta doğru ölçüm budur,
    çünkü aynı sezonun başka haftaları da bilgi sızdırır.

    Dönen liste hafta başına bir kayıt taşır; toplamlar `degerlendir` içinde
    alınır. Kayıtlar hafta düzeyinde tutulur çünkü bootstrap hafta üzerinden
    yapılır (modül başlığı, karar 3) — grup ölçüsü ne olursa olsun.
    """
    anahtarlar = [grup(h) if grup else i for i, h in enumerate(haftalar)]
    # Aynı gruba düşen haftalar için model bir kez eğitilir; 4 sezonluk
    # korpusta bu, 180 uydurma yerine 4 uydurma demektir.
    onbellek: dict[Any, Any] = {}

    out: list[dict[str, Any]] = []
    for i, hafta in enumerate(haftalar):
        anahtar = anahtarlar[i]
        tahminci = onbellek.get(anahtar)
        if tahminci is None:
            egitim = [h for j, h in enumerate(haftalar) if anahtarlar[j] != anahtar]
            tahminci = fabrika()
            tahminci.egit(egitim)
            onbellek[anahtar] = tahminci
        out.append(_hafta_skoru(tahminci, hafta))
    return out


def _hafta_skoru(tahminci: Tahminci, hafta: Girdi) -> dict[str, Any]:
    """Tek haftanın skor kaydı — hem dışarıda bırakmalı hem çapraz ölçüm kullanır."""
    tahminler = tahminci.tahmin(hafta)
    kodlar = hafta["results"]
    if len(tahminler) < len(kodlar):
        raise ValueError(
            f"{tahminci.ad}: {hafta['week']}. hafta icin "
            f"{len(kodlar)} mac beklenirken {len(tahminler)} tahmin geldi"
        )
    b_top = sum(brier(tahminler[k], kod) for k, kod in enumerate(kodlar))
    l_top = sum(log_kaybi(tahminler[k], kod) for k, kod in enumerate(kodlar))
    n = len(kodlar)
    return {
        "week": hafta["week"],
        "n": n,
        "brier_toplam": b_top,
        "log_toplam": l_top,
        "brier": round(b_top / n, 4) if n else 0.0,
        "log_kaybi": round(l_top / n, 4) if n else 0.0,
    }


def capraz_olc(fabrikalar: Sequence[Fabrika],
               egitim_haftalari: Sequence[Girdi],
               test_haftalari: Sequence[Girdi]) -> dict[str, Any]:
    """Bir veri setinde eğit, **bambaşka** bir veri setinde ölç.

    Dışarıda bırakmalı ölçümün veremediği şeyi verir: eğitim ve sınav yalnızca
    farklı haftalar değil, farklı **sezonlar ve farklı maç evrenleri**. Eğitim
    korpusunda (22 lig, 4 geçmiş sezon) uydurulan bir model, 2025/26 Spor Toto
    kuponunda ölçülür — aralarında tek bir ortak maç yoktur.

    Kat yok, sızıntı yok: her tahminci bir kez eğitilir ve test setinin
    tamamında ölçülür. Karşılaştırma kuralı aynıdır — `gecti` yalnızca
    eşleştirilmiş bootstrap aralığı tamamen sıfırın altındaysa `True`.
    """
    sonuclar: list[dict[str, Any]] = []
    for fabrika in fabrikalar:
        tahminci = fabrika()
        tahminci.egit(egitim_haftalari)
        kayitlar = [_hafta_skoru(tahminci, h) for h in test_haftalari]
        n_mac = sum(k["n"] for k in kayitlar)
        b_top = sum(k["brier_toplam"] for k in kayitlar)
        l_top = sum(k["log_toplam"] for k in kayitlar)
        sonuclar.append({
            "ad": tahminci.ad,
            "aciklama": tahminci.aciklama,
            "n_hafta": len(kayitlar),
            "n_mac": n_mac,
            "brier": round(b_top / n_mac, 4) if n_mac else None,
            "log_kaybi": round(l_top / n_mac, 4) if n_mac else None,
            "_kayitlar": kayitlar,
        })

    referans = next((s for s in sonuclar if s["ad"] == REFERANS_AD), None)
    for s in sonuclar:
        if referans is None or s["ad"] == REFERANS_AD:
            s["fark"] = None
            s["gecti"] = False if referans is None else None
        else:
            fark = bootstrap_farki(s["_kayitlar"], referans["_kayitlar"])
            s["fark"] = fark
            # Karar YUVARLANMAMIS ust sinirdan (bkz. `bootstrap_farki`).
            s["gecti"] = bool(fark.get("ham_ust") is not None
                              and fark["ham_ust"] < 0)
    for s in sonuclar:
        s.pop("_kayitlar", None)

    return {
        "referans": REFERANS_AD,
        "n_egitim_hafta": len(egitim_haftalari),
        "n_egitim_mac": sum(len(h["results"]) for h in egitim_haftalari),
        "n_hafta": len(test_haftalari),
        "n_mac": sum(len(h["results"]) for h in test_haftalari),
        "az_ornek": len(test_haftalari) < AZ_HAFTA,
        "tahminciler": sorted(sonuclar,
                              key=lambda s: (s["brier"] is None, s["brier"])),
        "bootstrap": {"tekrar": BOOTSTRAP_TEKRAR, "tohum": BOOTSTRAP_TOHUM,
                      "guven": GUVEN},
        "yontem": ("capraz: egitim ve test farkli veri setleri; ortak mac yok; "
                   "gecti = guven araligi tamamen sifirin altinda"),
    }


def degerlendir(fabrika: Fabrika,
                haftalar: Sequence[Girdi],
                grup: Callable[[Girdi], Any] | None = None) -> dict[str, Any]:
    """Bir tahmincinin dışarıda bırakmalı toplam skoru (bkz. `grup`)."""
    kayitlar = hafta_disarida_birak(fabrika, haftalar, grup)
    n_mac = sum(k["n"] for k in kayitlar)
    b_top = sum(k["brier_toplam"] for k in kayitlar)
    l_top = sum(k["log_toplam"] for k in kayitlar)
    ornek = fabrika()
    return {
        "ad": ornek.ad,
        "aciklama": ornek.aciklama,
        "n_hafta": len(kayitlar),
        "n_mac": n_mac,
        "brier": round(b_top / n_mac, 4) if n_mac else None,
        "log_kaybi": round(l_top / n_mac, 4) if n_mac else None,
        "haftalar": [{k: v for k, v in kayit.items()
                      if k not in ("brier_toplam", "log_toplam")}
                     for kayit in kayitlar],
        "_kayitlar": kayitlar,
    }


# ─── eşleştirilmiş bootstrap ──────────────────────────────────────────────────

def _ortalama(kayitlar: Sequence[dict[str, Any]], indeksler: Sequence[int],
              alan: str) -> float:
    """Seçilen haftaların maç başına ortalaması."""
    top = sum(kayitlar[i][alan] for i in indeksler)
    n = sum(kayitlar[i]["n"] for i in indeksler)
    return top / n if n else 0.0


def bootstrap_farki(aday: Sequence[dict[str, Any]],
                    referans: Sequence[dict[str, Any]],
                    alan: str = "brier_toplam",
                    tekrar: int = BOOTSTRAP_TEKRAR,
                    tohum: int = BOOTSTRAP_TOHUM) -> dict[str, Any]:
    """Aday − referans farkının eşleştirilmiş bootstrap güven aralığı.

    **Eşleştirilmiş**: her yinelemede aynı hafta kümesi iki tahminci için de
    kullanılır. Haftalar bağımsız örneklenseydi, ikisinin de zor bulduğu bir
    haftanın ortak etkisi farka gürültü olarak binerdi.

    Brier'de küçük iyidir; bu yüzden aralığın **tamamı sıfırın altındaysa**
    aday referansı geçmiş demektir.
    """
    if len(aday) != len(referans):
        raise ValueError("aday ve referans ayni haftalarda olculmeli")
    n = len(aday)
    if n == 0:
        return {"fark": None, "alt": None, "ust": None, "tekrar": 0}

    rng = random.Random(tohum)
    farklar: list[float] = []
    for _ in range(tekrar):
        indeksler = [rng.randrange(n) for _ in range(n)]
        farklar.append(_ortalama(aday, indeksler, alan)
                       - _ortalama(referans, indeksler, alan))
    farklar.sort()

    dis = (1.0 - GUVEN) / 2.0
    alt = farklar[min(int(dis * tekrar), tekrar - 1)]
    ust = farklar[min(int((1.0 - dis) * tekrar), tekrar - 1)]
    tum = list(range(n))
    nokta = _ortalama(aday, tum, alan) - _ortalama(referans, tum, alan)
    return {
        # Gösterim için yuvarlanmış — belgelerde ve arayüzde okunacak sayılar.
        "fark": round(nokta, 4),
        "alt": round(alt, 4),
        "ust": round(ust, 4),
        # **Karar bu alandan verilir.** Yuvarlanmış üst sınırla karar vermek
        # sessiz bir hataydı: `round(-0.000031, 4)` `-0.0` verir ve
        # `-0.0 < 0` Python'da `False`'tur — yani güven aralığının tamamı
        # sıfırın altındayken aday "geçmedi" diye yazılırdı. Aralık ne kadar
        # dar olursa hata o kadar olasıydı, yani tam da kararın zorlaştığı
        # yerde. Ham değerler bu yüzden taşınır ve `gecti` bunları okur.
        "ham_fark": nokta,
        "ham_alt": alt,
        "ham_ust": ust,
        "tekrar": tekrar,
    }


# ─── karşılaştırma ────────────────────────────────────────────────────────────

def karsilastir(fabrikalar: Sequence[Fabrika] | None = None,
                last: int | None = None,
                haftalar: Sequence[Girdi] | None = None,
                grup: Callable[[Girdi], Any] | None = None) -> dict[str, Any]:
    """Tahmincileri aynı kesitte ölç ve referansla karşılaştır.

    `fabrikalar` verilmezse yalnızca üç referans koşar — koşumun kendisinin
    sağlaması budur: `piyasa` her zaman `duzgun`'u geçmeli, `duzgun` her zaman
    0,667 çıkmalı. Bunlar kaymışsa bozulan şey aday değil, veridir.

    `gecti` bayrağı **yalnızca** güven aralığının tamamı sıfırın altındaysa
    `True` olur. Ortalaması daha iyi çıkan ama aralığı sıfırı içeren bir aday
    "geçmedi" sayılır — 41 haftalık örneklemde bu ayrım her şeydir.
    """
    if haftalar is None:
        haftalar = olculebilir_haftalar(last)
    if fabrikalar is None:
        fabrikalar = referans_fabrikalar()

    sonuclar = [degerlendir(f, haftalar, grup) for f in fabrikalar]
    referans = next((s for s in sonuclar if s["ad"] == REFERANS_AD), None)

    # İki geçiş: karşılaştırmaların tamamı bitmeden hiçbir kayıt silinmez.
    # Tek geçişte referans listenin başındaysa kendi kayıtlarını, sonraki
    # adaylar onu okumadan önce siliyordu — sıraya bağlı sessiz bir hata.
    for s in sonuclar:
        if referans is None or s["ad"] == REFERANS_AD:
            s["fark"] = None
            s["gecti"] = False if referans is None else None
        else:
            fark = bootstrap_farki(s["_kayitlar"], referans["_kayitlar"])
            s["fark"] = fark
            # Karar YUVARLANMAMIS ust sinirdan (bkz. `bootstrap_farki`).
            s["gecti"] = bool(fark.get("ham_ust") is not None
                              and fark["ham_ust"] < 0)
    for s in sonuclar:
        s.pop("_kayitlar", None)

    n_hafta = len(haftalar)
    return {
        "referans": REFERANS_AD,
        "n_hafta": n_hafta,
        "n_mac": sum(len(h["results"]) for h in haftalar),
        "az_ornek": n_hafta < AZ_HAFTA,
        "tahminciler": sorted(sonuclar, key=lambda s: (s["brier"] is None, s["brier"])),
        "bootstrap": {"tekrar": BOOTSTRAP_TEKRAR, "tohum": BOOTSTRAP_TOHUM,
                      "guven": GUVEN},
        "yontem": (("sezon" if grup is not None else "hafta")
                   + " disarida birakmali; bootstrap hafta uzerinden ve "
                   "eslestirilmis; gecti = guven araligi tamamen sifirin altinda"),
    }
