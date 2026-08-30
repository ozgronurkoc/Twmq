"""Değer bahsi getirisi — sabit oranlı yan pazarlarda kâr var mı? (Faz 4.3)

`georgedouzas/sports-betting` incelemesinden alınan tek **ölçü**. Depo bize
model olarak hiçbir şey katmadı (`docs/DIS_INCELEME_SPORTS_BETTING.md`) ama
bir eksiği görünür kıldı: `pazar.py` alt/üst 2,5 ve Asya handikabını
**kalibrasyon** olarak ölçüyor, **getiri** olarak ölçmüyordu.

Fark önemsiz değil. İyi kalibre bir fiyat, üstüne bahis oynanınca marj
kadar kaybettirir; kalibrasyon "piyasa dürüst mü" der, getiri "bu masadan
para kalkar mı" der. İkincisi hiç sorulmamıştı.

─── Modelin nereden geldiği — projenin en kolay yanılacağı yer ───────────

`p·o > 1` kuralı bir **model olasılığı** ile bir **fiyat** ister. Naif
uygulama ikisini de aynı sütundan alır ve o anda kural **hiç ateşlenmez**::

    p = marj arındırılmış Avg    ve    o = Avg
    → p·o = 1/(1+marj) < 1  HER AYAKTA

Ham ima edilen olasılıklar (`1/o`) 1'den fazlasına toplanır — aradaki
fark marjdır. Arındırma o fazlalığı geri alır, yani `p` her ayakta
`1/o`nun **altına** iner ve `p·o` hiçbir zaman 1'i geçmez.

Bu ilk bakışta iyi haber gibi görünür ("yanlış pozitif yok") ama değildir:
ölçüm **hiçbir şey ölçmez**. Bir fiyatı, kendi arındırılmış olasılığıyla
yenmek tanım gereği imkânsızdır. Kuralın anlamlı olması için elde
konsensüsten **daha iyi bir fiyat** olmalıdır.

Bu yüzden ikisi **ayrı kaynaktan** gelir ve ayrım arşivde zaten var:

    p  ←  `Avg`  bütün bahisçilerin ortalaması, marj arındırılmış
                 → kolektifin olasılık tahmini
    o  ←  `Max`  her ayakta en iyi fiyat (bir zarf, bir bahisçi değil)
                 → gerçekten oynanabilecek fiyat

`bahisci.py` `b_Max`in **olasılık olarak okunamayacağını** yazar: toplamı
1'in altında kalır. Doğrudur ve burada engel değil, dayanaktır — `Max` bir
olasılık değil bir **fiyattır**. Yöntem literatürde *"Beating the bookies
with their own numbers"* (Kaunitz ve ark., 2017) diye geçer ve
`sports-betting`in `OddsComparisonBettor`ının yaptığı da tam budur.

─── `alpha`: ölçüm görülmeden yazılmış tek ayar ──────────────────────────

Konsensüs olasılığından çıkarılan sabit. `sports-betting`in varsayılanı
0,05; buraya **o değer olduğu gibi** alındı ve `ALPHA_VARSAYILAN` odur.
Ayrıca `alpha = 0` (saf değer kuralı) her koşumda ayrıca raporlanır.

Tarama YAPILIR ama taramanın en iyisi manşet **değildir**: `backtest.py`
ile aynı üç parçalı yapı kullanılır — tek strateji · eşik taraması ·
**sezon dışarıda bırakmalı** sağlama. Üçüncüsü, eşiği o sezonu görmeden
seçtiğinde ne olduğunu ölçer ve okunacak sayı odur.

─── Neden `evaluate.ileri_yuruyus` kullanılmıyor ─────────────────────────

Plan onu öngörüyordu; kullanılmadı ve gerekçe teknik: `ileri_yuruyus` bir
`Tahminci`yi **eğitir**. Buradaki bahisçinin eğitimi yoktur — tek
parametresi `alpha` ve o da veriden öğrenilmiyor. Kat yapısı yalnızca
`alpha` seçilirken gerekli ve o iş `sezon_disarida()` ile yapılıyor;
sabit `alpha` için kat kurmak, olmayan bir eğitimi taklit etmek olurdu.

─── Kupona UYGULANMAZ ────────────────────────────────────────────────────

`getiri.py` müşterek havuzun neden başka bir hesap olduğunu yazıyor:
ödeme kaç kolonun tutturduğuna bağlıdır, `edge = p_piyasa − oynanma_payı`.
Kelly ve değer bahsi çerçevesi sabit bir fiyata karşı tanımlıdır. Bu modül
**yalnızca sabit oranlı yan pazarlar** içindir ve kupon motoruna hiçbir
şey söylemez.

    python -m spor_toto.deger
    python -m spor_toto.deger --json
    python -m spor_toto.deger --pazar 2.5 --pazar AH --kaydet
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Sequence
from typing import Any

from .evaluate import BOOTSTRAP_TEKRAR, BOOTSTRAP_TOHUM, GUVEN
from .odds import (
    ARINDIRMA_VARSAYILAN,
    implied_probs,
    load_odds,
    market_odds,
)
from .pazar import ah_bilesenler

#: Ölçülen pazarlar. 1X2 **dahil**: `pazar.py` yalnızca yan pazarlara
#: bakıyordu ama değer sorusu 1X2'de de sorulmamıştı ve orada kesit en
#: geniş. Üçü de sabit oranlı; müşterek kupon burada YOK.
PAZARLAR: tuple[str, ...] = ("1X2", "2.5", "AH")

#: Karşılıklı dışlayan ayak grupları — grup içinde **tek** bahis oynanır.
#: `sports-betting`in `derive_complementary_events`ının karşılığı; orada
#: türetiliyor, burada yazılı çünkü üç pazarımız da sabit.
GRUPLAR: dict[str, tuple[str, ...]] = {
    "1X2": ("1", "0", "2"),
    "2.5": ("ust", "alt"),
    "AH": ("1", "2"),
}

#: Konsensüs olasılığından çıkarılan pay. `sports-betting`in varsayılanı;
#: ölçüm görülmeden alındı ve değiştirilmedi.
ALPHA_VARSAYILAN = 0.05

#: Tarama ızgarası. Kenarları kaba ve **ölçüm sonucuna bakılmadan** seçildi
#: (`pazar.BANTLAR` ile aynı gerekçe).
ALPHA_IZGARASI: tuple[float, ...] = (0.0, 0.02, 0.05, 0.08, 0.12)

#: Olasılık kaynağı ve fiyat kaynağı. İkisinin AYRI olması modülün varlık
#: sebebidir (başlık); sabit tutuluyor ki koşumlar kıyaslanabilsin.
OLASILIK_KAYNAGI = "Avg"
FIYAT_KAYNAGI = "Max"

#: Bir sayının yazılması için gereken en az bahis. Altında ortalama kendi
#: gürültüsünü ölçer.
EN_AZ_BAHIS = 30

#: Sharpe'ın yıllıklandırma çarpanı. Takvim günü, işlem günü değil —
#: futbol takvimi hafta sonuna yığılır ve "işlem günü" diye bir şey yok.
YIL_GUN = 365


def _cizgi(oranlar: dict[str, Any]) -> float | None:
    """Asya handikabı çizgisi — `pazar._cizgi` ile aynı, kapanış öncelikli."""
    for ad in ("AHCh", "AHh"):
        v = oranlar.get(ad)
        if v is not None:
            return float(v)
    return None


def _ah_para_getirisi(gol_farki: int, h: float, oran: float) -> float:
    """Asya handikabında **birim bahis başına para** getirisi.

    `pazar._ah_getiri`den ayrı olmak zorunda: orada iade 0,5 sayılır
    (kapama oranı ölçeği), burada iade **0**'dır — yatırılan geri gelir,
    kâr yoktur. Bölünme kuralı ikisinde de `pazar.ah_bilesenler`ten okunur,
    yani çeyrek çizgi tanımı tek yerde durur.
    """
    para = 0.0
    for cizgi, pay in ah_bilesenler(h):
        d = gol_farki + cizgi
        if d > 0:
            para += pay * (oran - 1.0)
        elif d < 0:
            para -= pay
        # d == 0: iade — ne kâr ne zarar.
    return para


def _mac_kaydi(row: dict[str, Any], pazar: str,
               yontem: str) -> dict[str, Any] | None:
    """Bir maçın bir pazarını `(olasılık, fiyat, sonuç)` üçlüsüne indirger.

    `None` döner ancak fiyatın bir ayağı ya da skor eksikse — doktrin 2:
    eksik veri uydurulmaz, elenir.
    """
    ayaklar = GRUPLAR[pazar]
    p_ham = market_odds(row, pazar, OLASILIK_KAYNAGI, closing=True)
    fiyat = market_odds(row, pazar, FIYAT_KAYNAGI, closing=True)
    if len(p_ham) != len(ayaklar) or len(fiyat) != len(ayaklar):
        return None
    if any(float(p_ham[a]) <= 1.0 or float(fiyat[a]) <= 1.0 for a in ayaklar):
        return None

    p = implied_probs({a: float(p_ham[a]) for a in ayaklar}, yontem)
    if len(p) != len(ayaklar):
        return None

    hg, ag = row.get("hg"), row.get("ag")
    if hg is None or ag is None:
        return None
    hg, ag = int(hg), int(ag)

    kayit: dict[str, Any] = {
        "pazar": pazar, "week": row.get("week"), "no": row.get("no"),
        "tarih": row.get("kickoff") or row.get("tarih"),
        "p": p, "o": {a: float(fiyat[a]) for a in ayaklar},
    }
    if pazar == "1X2":
        kod = "1" if hg > ag else ("0" if hg == ag else "2")
        kayit["para"] = {a: (kayit["o"][a] - 1.0 if a == kod else -1.0)
                         for a in ayaklar}
    elif pazar == "2.5":
        ust = (hg + ag) > 2.5
        kayit["para"] = {"ust": kayit["o"]["ust"] - 1.0 if ust else -1.0,
                         "alt": -1.0 if ust else kayit["o"]["alt"] - 1.0}
    else:
        h = _cizgi(row.get("odds") or {})
        if h is None:
            return None
        kayit["cizgi"] = h
        kayit["para"] = {
            "1": _ah_para_getirisi(hg - ag, h, kayit["o"]["1"]),
            # Deplasman ayagi ters isaretli cizgiyle ve ters gol farkiyla.
            "2": _ah_para_getirisi(ag - hg, -h, kayit["o"]["2"]),
        }
    return kayit


def sec(kayit: dict[str, Any], alpha: float) -> str | None:
    """Grup içinde oynanacak **tek** ayak, ya da `None`.

    İki kural birlikte çalışır ve ikincisi `sports-betting`den alındı:

    1. Beklenen getiri eşiği geçmeli: `p·o − 1 > alpha`.
    2. Geçen birden fazla ayak varsa **yalnızca en iyisi** oynanır.

    İkincisi olmadan 1X2'de aynı maçın iki ayağına birden oynanabilir ve
    bu, kendi kendine karşı bahis yapmaktır — marjı iki kez öder::

        >>> k = {"pazar": "1X2",
        ...      "p": {"1": 0.40, "0": 0.30, "2": 0.30},
        ...      "o": {"1": 3.00, "0": 4.00, "2": 2.00}}
        >>> # beklenen getiri:  1 -> +0,20   0 -> +0,20   2 -> -0,40
        >>> sec(k, 0.0) in ("1", "0")
        True

    Eşiği geçen ayak yoksa bahis de yok — `None` bir "oynama" işaretidir::

        >>> zayif = {"pazar": "1X2",
        ...          "p": {"1": 0.50, "0": 0.25, "2": 0.25},
        ...          "o": {"1": 1.90, "0": 3.00, "2": 3.00}}
        >>> sec(zayif, 0.0) is None
        True

    Eşit beklenen getiride **grup sırasındaki ilk** ayak seçilir; kural
    deterministiktir ve `GRUPLAR`ın sırasından okunur. (`sports-betting`
    burada ayaklara `eps` ekleyerek eşitliği bozar; sonuç aynı biçimde
    keyfîdir ama bizde en azından okunabilir.)::

        >>> sec(k, 0.10)
        '1'

    `alpha` eşiği yükseltir, yönü değiştirmez::

        >>> ayrik = {"pazar": "1X2",
        ...          "p": {"1": 0.40, "0": 0.30, "2": 0.30},
        ...          "o": {"1": 2.80, "0": 4.00, "2": 2.00}}
        >>> sec(ayrik, 0.0)
        '0'
        >>> sec(ayrik, 0.50) is None
        True
    """
    en_iyi, en_iyi_ed = None, alpha
    for ayak in GRUPLAR[kayit["pazar"]]:
        ed = kayit["p"][ayak] * kayit["o"][ayak] - 1.0
        if ed > en_iyi_ed:
            en_iyi, en_iyi_ed = ayak, ed
    return en_iyi


def _bootstrap_ortalama(degerler: Sequence[float],
                        tekrar: int = BOOTSTRAP_TEKRAR,
                        tohum: int = BOOTSTRAP_TOHUM) -> dict[str, Any]:
    """Ortalamanın bootstrap güven aralığı — tek örneklem, eşleştirilmemiş.

    `evaluate.bootstrap_farki` **eşleştirilmiş** çalışır (aday ↔ referans);
    burada karşılaştırılacak bir referans yok, ölçülen şey ortalamanın
    kendisidir. Tekrar sayısı ve tohum oradan alınır ki koşumlar aynı
    rastgelelik bütçesini kullansın.
    """
    n = len(degerler)
    if n == 0:
        return {"ortalama": None, "alt": None, "ust": None, "n": 0}
    rng = random.Random(tohum)
    ortalamalar = sorted(
        sum(degerler[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(tekrar))
    dis = (1.0 - GUVEN) / 2.0
    alt = ortalamalar[min(int(dis * tekrar), tekrar - 1)]
    ust = ortalamalar[min(int((1.0 - dis) * tekrar), tekrar - 1)]
    nokta = sum(degerler) / n
    return {"ortalama": nokta, "alt": alt, "ust": ust, "n": n,
            "tekrar": tekrar}


def _sharpe(gunluk: dict[str, float]) -> float | None:
    """Yıllıklandırılmış Sharpe — `sports-betting`in `BaseBettor.score`u.

    Günlük getiriler **takvime yayılır**: bahis oynanmayan gün 0 getiri
    sayılır. Yayılmazsa oynak bir haftada yoğunlaşan getiri, bütün yıl öyle
    kazanılmış gibi görünür.
    """
    if len(gunluk) < 2:
        return None
    gunler = sorted(gunluk)
    ilk = _gun_sayisi(gunler[0])
    son = _gun_sayisi(gunler[-1])
    if son is None or ilk is None or son < ilk:
        return None
    seri = [0.0] * (son - ilk + 1)
    for g, v in gunluk.items():
        i = _gun_sayisi(g)
        if i is not None:
            seri[i - ilk] += v
    n = len(seri)
    mu = sum(seri) / n
    var = sum((x - mu) ** 2 for x in seri) / (n - 1) if n > 1 else 0.0
    if var <= 0.0:
        return None
    return (YIL_GUN ** 0.5) * mu / (var ** 0.5)


def _gun_sayisi(tarih: str) -> int | None:
    """`YYYY-MM-DD` → gün numarası; okunamayan tarih `None`."""
    from datetime import date
    try:
        y, a, g = (int(x) for x in str(tarih)[:10].split("-"))
        return date(y, a, g).toordinal()
    except (ValueError, TypeError):
        return None


def olc(kayitlar: Sequence[dict[str, Any]], alpha: float) -> dict[str, Any]:
    """Bir bahis kümesinin ekonomik özeti.

    Döndürülen sayılar `sports-betting`in `_fit_bet`indekilerle **aynı
    tanımdadır** ki karşılaştırılabilsinler: bahis sayısı, bahis başına
    getiri (yield), ROI ve son kasa. Sharpe `BaseBettor.score`tan.
    """
    getiriler: list[float] = []
    oranlar: list[float] = []
    gunluk: dict[str, float] = {}
    for k in kayitlar:
        ayak = sec(k, alpha)
        if ayak is None:
            continue
        para = k["para"][ayak]
        getiriler.append(para)
        oranlar.append(k["o"][ayak])
        gun = str(k.get("tarih") or "")[:10]
        if gun:
            gunluk[gun] = gunluk.get(gun, 0.0) + para

    n = len(getiriler)
    if n == 0:
        return {"alpha": alpha, "n_bahis": 0, "n_mac": len(kayitlar),
                "verim": None, "roi": None, "sharpe": None, "yeterli": False}

    toplam = sum(getiriler)
    ci = _bootstrap_ortalama(getiriler)
    return {
        "alpha": alpha,
        "n_mac": len(kayitlar),
        "n_bahis": n,
        "bahis_orani": n / len(kayitlar) if kayitlar else 0.0,
        # Bahis basina getiri — birim bahiste, yuzde.
        "verim": 100.0 * toplam / n,
        "verim_ga": [100.0 * ci["alt"], 100.0 * ci["ust"]],
        # ROI BILEREK YOK. `sports-betting` onu `stake * toplam / init_cash`
        # diye yazar; bu, `verim`in `n * stake / init_cash` ile carpimidir,
        # yani yeni bir bilgi degil bir KASA PARAMETRESIDIR. Kasa buyuklugu
        # secilerek ROI istenen sayiya getirilebilir. Tasinmadi.
        "toplam_getiri": toplam,
        # Secilen bahislerin fiyat profili — sayiyi OKUNUR kilar.
        #
        # `Max/Avg` acigi uzun atislarda en genistir (bahisci
        # anlasmazligi orada buyur), dolayisiyla bu kural dogal olarak
        # uzun atisa yigilir. Yigiliyorsa varyans yuksek olur ve genis
        # guven araligi bir kusur degil, stratejinin kendi ozelligidir.
        "ortalama_oran": sum(oranlar) / n,
        "medyan_oran": sorted(oranlar)[n // 2],
        "sharpe": _sharpe(gunluk),
        "n_gun": len(gunluk),
        "yeterli": n >= EN_AZ_BAHIS,
        # Karar bu alandan verilir: aralik TAMAMEN sifirin ustunde mi?
        "karli": ci["alt"] > 0.0,
    }


def _sezon_anahtari(kayit: dict[str, Any]) -> str:
    """Kayıt hangi sezon dosyasından geldi — `sezon` alanı koşum sırasında konur."""
    return str(kayit.get("sezon") or "?")


def kayitlar(pazar: str, yontem: str = ARINDIRMA_VARSAYILAN) -> list[dict[str, Any]]:
    """Bütün sezon arşivlerini tek listede topla, sezon etiketiyle."""
    import glob
    from pathlib import Path

    kok = Path(__file__).resolve().parent.parent / "data" / "odds"
    out: list[dict[str, Any]] = []
    for yol in sorted(glob.glob(str(kok / "odds_*.csv"))):
        sezon = Path(yol).stem.replace("odds_", "")
        for row in load_odds(yol):
            k = _mac_kaydi(row, pazar, yontem)
            if k is not None:
                k["sezon"] = sezon
                out.append(k)
    return out


def sezon_disarida(kayit_listesi: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """`alpha`yı o sezonu GÖRMEDEN seç, sonra o sezonda uygula.

    Okunacak sayı budur. Tarama tablosunun en iyisi bir **seçim
    sonrasıdır** ve `backtest.py`nin eşik taraması için yazdığı uyarı
    burada da geçerli: en iyi görünen eşiğin gelecek sezon aynısını
    yapmayacağı matematiksel bir beklentidir.
    """
    sezonlar = sorted({_sezon_anahtari(k) for k in kayit_listesi})
    katlar: list[dict[str, Any]] = []
    tum: list[float] = []
    for sezon in sezonlar:
        disarida = [k for k in kayit_listesi if _sezon_anahtari(k) == sezon]
        icerde = [k for k in kayit_listesi if _sezon_anahtari(k) != sezon]
        if not icerde or not disarida:
            continue
        # Secim YALNIZCA icerideki sezonlarda — ve YALNIZCA yeterli
        # bahis ureten alpha'lar arasindan.
        #
        # Bu kisit bir ayar degil, modulun kendi kuralinin sonucu:
        # `EN_AZ_BAHIS` "altinda ortalama kendi gurultusunu olcer" diyor.
        # Kisit olmadan secim tam da o gurultuyu maksimize ediyordu —
        # olculdu: alpha=0,12 uc bahisle %1.267 "verim" gosteriyor ve
        # secim onu sececek kadar yuksek. Yeterli alpha yoksa kat DUSER;
        # varsayilana geri donmek, secimi sessizce yapmak olurdu.
        adaylar = [a for a in ALPHA_IZGARASI
                   if (olc(icerde, a)["n_bahis"] or 0) >= EN_AZ_BAHIS]
        if not adaylar:
            katlar.append({"sezon": sezon, "secilen_alpha": None,
                           "n_bahis": 0, "verim": None, "sharpe": None,
                           "not": f"hicbir alpha {EN_AZ_BAHIS} bahis uretmedi"})
            continue
        en_iyi = max(adaylar, key=lambda a: (olc(icerde, a)["verim"] or -1e9))
        dis = olc(disarida, en_iyi)
        katlar.append({"sezon": sezon, "secilen_alpha": en_iyi,
                       "n_bahis": dis["n_bahis"], "verim": dis["verim"],
                       "sharpe": dis["sharpe"]})
        for k in disarida:
            ayak = sec(k, en_iyi)
            if ayak is not None:
                tum.append(k["para"][ayak])
    ci = _bootstrap_ortalama(tum) if tum else {"ortalama": None, "alt": None,
                                               "ust": None, "n": 0}
    nokta, alt, ust = ci["ortalama"], ci["alt"], ci["ust"]
    return {
        "katlar": katlar,
        "n_bahis": len(tum),
        "verim": None if nokta is None else 100.0 * float(nokta),
        "verim_ga": (None if alt is None or ust is None
                     else [100.0 * float(alt), 100.0 * float(ust)]),
        "karli": bool(alt is not None and float(alt) > 0.0),
    }


def rapor(pazarlar: Sequence[str] | None = None,
          yontem: str = ARINDIRMA_VARSAYILAN) -> dict[str, Any]:
    """Üç parçalı çıktı: tek strateji · tarama · sezon dışarıda bırakmalı."""
    secilen = tuple(pazarlar or PAZARLAR)
    out: dict[str, Any] = {
        "arindirma": yontem,
        "olasilik_kaynagi": OLASILIK_KAYNAGI,
        "fiyat_kaynagi": FIYAT_KAYNAGI,
        "pazarlar": {},
        "sinir": (
            "Kesit kupon oran arsividir (4 sezon), 31 binlik egitim korpusu "
            "DEGIL: korpus alt/ust ve AH fiyatlarini tasimiyor. Kupona "
            "uygulanmaz — muserek havuzda odeme kac kolonun tutturduguna "
            "baglidir (`getiri.py`)."),
    }
    for pazar in secilen:
        ks = kayitlar(pazar, yontem)
        out["pazarlar"][pazar] = {
            "n_mac": len(ks),
            "sezonlar": sorted({_sezon_anahtari(k) for k in ks}),
            "varsayilan": olc(ks, ALPHA_VARSAYILAN),
            "saf_deger": olc(ks, 0.0),
            "tarama": [olc(ks, a) for a in ALPHA_IZGARASI],
            "sezon_disarida": sezon_disarida(ks),
        }
    return out


def _yaz(govde: dict[str, Any]) -> None:
    print(f"deger bahsi — olasilik={govde['olasilik_kaynagi']} "
          f"fiyat={govde['fiyat_kaynagi']} arindirma={govde['arindirma']}\n")
    for pazar, b in govde["pazarlar"].items():
        print(f"── {pazar} ── {b['n_mac']} mac, sezon {', '.join(b['sezonlar'])}")
        for ad, s in (("saf deger (alpha=0)", b["saf_deger"]),
                      (f"alpha={ALPHA_VARSAYILAN}", b["varsayilan"])):
            if not s["n_bahis"]:
                print(f"  {ad:<22} hic bahis yok")
                continue
            ga = s["verim_ga"]
            sh = "—" if s["sharpe"] is None else f"{s['sharpe']:+.2f}"
            print(f"  {ad:<22} {s['n_bahis']:>5} bahis  "
                  f"verim {s['verim']:+.2f}%  "
                  f"[{ga[0]:+.2f}, {ga[1]:+.2f}]  sharpe {sh}  "
                  f"medyan oran {s['medyan_oran']:.2f}")
        print("  tarama:")
        for s in b["tarama"]:
            if not s["n_bahis"]:
                print(f"    alpha={s['alpha']:<5} hic bahis yok")
                continue
            print(f"    alpha={s['alpha']:<5} {s['n_bahis']:>5} bahis  "
                  f"verim {s['verim']:+.2f}%")
        d = b["sezon_disarida"]
        print("  SEZON DISARIDA BIRAKMALI (okunacak sayi):")
        if d["verim"] is None:
            print("    olculemedi")
        else:
            ga = d["verim_ga"]
            print(f"    {d['n_bahis']:>5} bahis  verim {d['verim']:+.2f}%  "
                  f"[{ga[0]:+.2f}, {ga[1]:+.2f}]  "
                  f"{'KARLI' if d['karli'] else 'karli DEGIL'}")
            for k in d["katlar"]:
                v = "—" if k["verim"] is None else f"{k['verim']:+.2f}%"
                print(f"      {k['sezon']}  alpha={k['secilen_alpha']:<5} "
                      f"{k['n_bahis']:>4} bahis  {v}")
        print()
    print(govde["sinir"])


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Sabit oranli yan pazarlarda deger bahsi getirisi")
    ap.add_argument("--pazar", action="append", choices=list(PAZARLAR))
    ap.add_argument("--arindirma", default=ARINDIRMA_VARSAYILAN)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--kaydet", action="store_true",
                    help="olcum kosum defterine yaz")
    args = ap.parse_args(argv)

    govde = rapor(args.pazar, args.arindirma)
    if args.json:
        print(json.dumps(govde, ensure_ascii=False, indent=1, default=str))
    else:
        _yaz(govde)
    if args.kaydet:
        from .kosum import kaydet
        kaydet("deger", govde)
    return 0


if __name__ == "__main__":
    sys.exit(main())
