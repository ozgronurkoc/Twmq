#!/usr/bin/env python3
"""**2. Tahmin** — aynı haftayı, bugünkü aletlerin tamamıyla yeniden okur.

2. haftanın kuponu 2026-08-18'de donduruldu ve o kayıt **yerinde durur**;
bu betik onu değiştirmez, yanına ikinci bir kayıt koyar. Sebebi basit: o
tarihten bu yana projede dört şey değişti ve dördü de aynı haftada başka
bir cevap üretiyor.

┌─ 1. Ölçek ── marj arındırma `orantili` → `shin` (A5, docs §3.18)
│  Orantısal yöntem marjı her sonuca eşit dağıtır; bahisçi onu sürprizlere
│  ağır yükler. Ölçüldü: Brier −0,00035 [−0,00049, −0,00021], sapan bant
│  10/15 → 4/15. **Aynı oran, başka olasılık.**
├─ 2. Kural ── `esik` → `hedef` (B0, docs §3.19)
│  Eşik kuralı her maça tek başına bakıp favoriyi iki sabit sayıya vurur.
│  Hedef kuralı verilen bütçede doğrudan `P(en iyi kolon ≥ 12)`'yi
│  enbüyükler. 36 haftanın 35'inde daha iyi, ortalama %26 daha ucuz.
├─ 3. Havuz ekseni ── kalabalıktan sapmak (Faz 4.2, docs §3.34)
│  Müşterek bahiste kazanç `p_piyasa − oynanma_payı`ndan doğar. Kupon
│  kuralı kalabalığı **hiç görmüyordu**; `secim.kalabalik_ayari` işaret
│  SAYILARINI koruyup hangi sembol sorusunu yeniden soruyor. Bedel aynı,
│  bölüşme farklı.
└─ 4. Bağımsız görüş ── Dixon-Coles + Elo (Faz 3.1/3.2, docs §3.27–3.28)
   2. haftanın ilk analizinde piyasadan başka bir görüş **yoktu**. Şimdi
   var ve oranlara hiç bakmıyor. **İşaret değiştirmez** — ikisi de kupon
   setinde piyasanın gerisinde ölçüldü — ama piyasanın nerede yalnız
   kaldığını gösterir.

─── Bu kayıt da sonuçlar görülmeden üretilir ─────────────────────────────

`meta.results_known` bu dosyada da `false`'tur ve hafta dosyasındaki
`results` alanı doluysa betik **yazmayı reddeder**. Sonucu bilinen bir
haftaya "ikinci tahmin" yazmak tahmin değil, geriye dönük kurgu olurdu —
projenin en değerli alışkanlığı tam olarak buna karşı.

    python scripts/super_toto_tahmin2.py --hafta 2
    python scripts/super_toto_tahmin2.py --hafta 2 --yaz
    python scripts/super_toto_tahmin2.py --hafta 2 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from scripts._ortak import metin
from scripts.super_toto_hafta import hafta_yukle, kupon_satirlari
from spor_toto import kosum
from spor_toto.backtest import (
    VARSAYILAN_BANKO,
    VARSAYILAN_UCLU,
    _kaplama,
    secim_uret,
)
from spor_toto.core import SEMBOLLER as SEM
from spor_toto.getiri import (
    KALABALIK_MODELLERI,
    VARSAYILAN_KOMISYON,
    beklenen_getiri,
    kalabalik_kademeleri,
)
from spor_toto.gorus import ayrisma, gorus_uret
from spor_toto.kaplama_arsiv import HAMMING_BLOK_BOYU
from spor_toto.odds import (
    ARINDIRMA_VARSAYILAN,
    implied_probs,
    margin,
)
from spor_toto.ortak import kacak_dagilimi
from spor_toto.secim import (
    VARSAYILAN_KAYIP_ORANI,
    bedel_hesapla,
    en_iyi_secim,
    hedef_olasiligi,
    kalabalik_ayari,
)

#: Dondurulmuş 1. kuponun ölçeği **kaydın kendisinden** okunur; bu sabit
#: yalnızca kayıt hiç söylemiyorsa devreye giren geri düşüştür.
#:
#: **Neden sabit olamaz.** Bu değer bir dönem `"orantili"` diye yazılıydı ve
#: 1.–2. haftada doğruydu: o kuponlar orantısal ölçekte donduruldu. 3. ve 4.
#: hafta `shin` + `hedef` ile donduruldu ve sabit o gün YALAN söylemeye
#: başladı — kayıt "ölçek orantılıdan shin'e değişti" ve "kural eşikten
#: hedefe çevrildi" diye yazacaktı, oysa ikisi de değişmemişti; üstelik
#: `_kiyas` "iki sayı doğrudan kıyaslanamaz" diyecekti, oysa tam olarak
#: kıyaslanabilirler. Deponun üçüncü kez gördüğü kalıp: **bugünkü durumu
#: kalıcı sanmak** (docs §3.38). Her dondurulmuş kayıt `strategy.arindirma`
#: ve `strategy.kural` taşır — bekçisi
#: `test_donmus_kupon_hangi_olcekte_donduruldugunu_yazar`.
ONCEKI_ARINDIRMA = "orantili"


def _onceki_olcek(donmus: dict[str, Any] | None) -> tuple[str, str]:
    """Dondurulmuş kaydın KENDİ ölçeği ve kuralı — sabit yazılmaz."""
    st = ((donmus or {}).get("meta") or {}).get("strategy") or {}
    return st.get("arindirma") or ONCEKI_ARINDIRMA, st.get("kural") or "esik"


def _yenilikler(onceki_arindirma: str, onceki_kural: str,
                arindirma: str, kural: str) -> list[str]:
    """1. Tahmin'den bu yana GERÇEKTEN ne değişti.

    Liste sabit yazılıydı ve dört maddesinin ikisi 3. haftadan beri yalandı:
    o hafta kupon zaten `shin` + `hedef` ile donduruldu, yani ölçek de kural
    da değişmemişti. Artık iki alan da dondurulmuş kayıttan okunur ve madde
    **yalnızca fark varsa** yazılır.

    Son iki madde koşulsuz: dondurulan kupon kalabalığı görmez (kaydın
    kendi `kalabalik_gerekcesi` alanı bunu söyler) ve bağımsız görüş hiçbir
    kupon kuralına girmez — ikisi de tanım gereği bu kaydın eklediği şey.
    Kalabalık ayarı dondurulmuş kuponun KENDİ kuralıysa o madde de düşer.
    """
    out = []
    if onceki_arindirma != arindirma:
        out.append(f"olcek: marj arindirma {onceki_arindirma} -> {arindirma} "
                   "(docs §3.18)")
    if onceki_kural != kural:
        out.append(f"kural: {onceki_kural} -> {kural}, "
                   "P(en iyi kolon >= 12) enbuyuklenir (docs §3.19)")
    if "kalabal" not in onceki_kural.lower():
        out.append("havuz: kalabalik ayari — isaret sayilari sabit, "
                   "sembol degisir (docs §3.34)")
    out.append("gorus: Dixon-Coles + Elo, piyasadan bagimsiz (docs §3.27–3.28)")
    if not out:  # pragma: no cover - son madde kosulsuz, buraya dusulmez
        out.append("1. Tahmin ile AYNI olcek ve kural; fark yalnizca kayit gunu")
    return out

#: Havuz ekseninin varsayımları. Hepsi **varsayım**, hiçbiri ölçüm — bu
#: yüzden gövdeye yazılırlar ve arayüzde para birimli hiçbir sayı
#: görünmez (`getiri` modül başlığı, docs §6.3b).
VARSAYILAN_HAVUZ = 50_000_000.0
VARSAYILAN_KOLON_BEDELI = 1.5


# ─── olasılık ─────────────────────────────────────────────────────────────

def _probs(mac: dict[str, Any], yontem: str) -> dict[str, float]:
    """Bir maçın olasılığı. Oranı yoksa 1/3 — tahmin değil, bilgi yokluğu."""
    if mac.get("odds_yok") or not mac.get("odds"):
        return dict.fromkeys(SEM, 1.0 / 3)
    return implied_probs(mac["odds"], yontem)


def _oynanma(mac: dict[str, Any]) -> dict[str, float]:
    return {s: float(mac["play"][s]) for s in SEM}


#: Marj (overround) TEK kaynaktan: `spor_toto.odds.margin`. Ayni govde
#: iki betikte birebir yaziliydi; kanonik govde ustelik daha korumali
#: (sifir/negatif orani eler, bu kopyalar ZeroDivisionError verirdi).
_marj = margin


def _marji_esitle(oranlar: dict[str, float], hedef_marj: float
                  ) -> dict[str, float]:
    """Oranları, ima ettikleri marj `hedef_marj` olacak şekilde ölçekler.

    Bir satırın marjı bültenin geri kalanından kopuksa iki ihtimal vardır:
    giriş hatası ya da gerçekten farklı fiyatlanmış bir satır. Ayırmanın
    yolu yok; **ama sonucun buna duyarlı olup olmadığı ölçülebilir.**
    Ölçekleme sonucun ŞEKLİNİ korur (oranların birbirine göre yerini),
    yalnızca toplam marjı taşır.
    """
    kat = (1.0 + _marj(oranlar)) / (1.0 + hedef_marj)
    return {s: v * kat for s, v in oranlar.items()}


# ─── kupon ────────────────────────────────────────────────────────────────

def _kupon_govdesi(probs: list[dict[str, float]],
                   oynanma: list[dict[str, float]],
                   secimler: list[list[str]]) -> dict[str, Any]:
    """Bir işaret planının bütün ölçüleri — tek yerde, tek biçimde."""
    kap = _kaplama(tuple(sorted(len(s) for s in secimler if len(s) > 1)))
    kume = 1.0
    kalabalik = 1.0
    for p, oy, sec in zip(probs, oynanma, secimler):
        kume *= sum(p[s] for s in sec)
        kalabalik *= sum(oy[s] for s in sec)
    # Kaçak olasılığı SEÇİMDEN okunur, `len(sec)`ten değil. `kacak_olasiligi`
    # en olası k sembolü varsayar; kalabalık ayarı bu varsayımı bilerek
    # bozuyor (aynı boyutta BAŞKA bir küme işaretleniyor) ve o durumda
    # seviyeden hesaplanan sayı gerçek plana ait olmazdı.
    dagilim = kacak_dagilimi([max(0.0, 1.0 - sum(p[s] for s in sec))
                              for p, sec in zip(probs, secimler)])
    return {
        "picks": ["".join(s) for s in secimler],
        "banko": [i + 1 for i, s in enumerate(secimler) if len(s) == 1],
        "cift": [i + 1 for i, s in enumerate(secimler) if len(s) == 2],
        "uclu": [i + 1 for i, s in enumerate(secimler) if len(s) == 3],
        "columns": kap["columns"] if kap else None,
        "rows": kap["rows"] if kap else None,
        "engine": kap["engine"] if kap else None,
        "guaranteed_14": kap["guaranteed"] if kap else None,
        "p_hedef": hedef_olasiligi(probs, secimler),
        "p14": dagilim[0] if len(dagilim) > 0 else 0.0,
        "p13": dagilim[1] if len(dagilim) > 1 else 0.0,
        "p12": dagilim[2] if len(dagilim) > 2 else 0.0,
        "in_set_p": kume,
        "crowd_in_set_p": kalabalik,
        "crowd_ratio": (kume / kalabalik) if kalabalik > 0 else None,
        "kosullu_rakip": _kosullu_rakip(probs, oynanma, secimler),
        "lines": kupon_satirlari(secimler),
    }


def _kosullu_rakip(probs: list[dict[str, float]],
                   oynanma: list[dict[str, float]],
                   secimler: list[list[str]]) -> dict[str, float]:
    """**Kazandığımız koşulunda** bir rakip kolonun bizimle aynı sonucu
    tutturma olasılığı.

    ─── Niçin `getiri`nin sayısı bu soruyu cevaplamıyor ──────────────────

    `getiri.kalabalik_kademeleri` rakibin isabetini **koşulsuz** hesaplar:
    rastgele bir sonuç, rastgele bir rakip kolon. O sayı bizim ne
    işaretlediğimize hiç bakmaz — dolayısıyla kalabalık ayarının kazancını
    **tanım gereği göremez** ve iki plan için birebir aynı çıkar.

    Oysa havuz, biz kazandığımızda bölünür. Doğru soru şudur: *sonuç bizim
    kümemize düştüyse*, rakip kolonun aynı sonucu tutturma olasılığı nedir?
    Koşullandırma maç maç ayrışır ve kapalı formda yazılır::

        q_koşullu = Π_i  ( Σ_{s∈sec_i} p_i(s)·o_i(s) ) / ( Σ_{s∈sec_i} p_i(s) )

    Pay: rakibin `o`dan çekip gerçek sonucun `p`den geldiği çapraz terim,
    kümeyle sınırlı. Payda: sonucun kümeye düşme olasılığı — koşul.

    `kat` bu sayının koşulsuz haline oranıdır: 1'in **üstü**, kazandığımız
    haftada rakiplerin bizimle birlikte kazanmaya normalden daha yatkın
    olduğunu söyler. Küçük olması iyidir.

    **Yalnızca aynı ŞEKİLDEKİ planlar arasında okunur.** Üçlü işaretlenen
    bir maçın çarpanı tam 1'dir, banko işaretlenenin çarpanı ise büyüktür
    (`o_fav / Σ p·o`); yani sayı "kalabalıktan kaçtım mı"nın yanı sıra
    "ne kadar daraldım"ı da taşır. Kalabalık ayarı işaret sayılarını sabit
    tuttuğu için taban ↔ ayarlı kıyası temizdir; farklı bütçedeki iki
    kuponu bu sayıyla karşılaştırmak iki ayrı şeyi tek rakama sıkıştırır.

    Sayı, oynanma paylarının kendi sınırını miras alır: paylar tek bir
    platformun kullanıcılarına aittir, havuzun tamamına değil.
    """
    kosullu = 1.0
    kosulsuz = 1.0
    for p, oy, sec in zip(probs, oynanma, secimler):
        icinde = sum(p[s] for s in sec)
        capraz = sum(p[s] * oy[s] for s in sec)
        kosullu *= (capraz / icinde) if icinde > 0 else 0.0
        kosulsuz *= sum(p[s] * oy[s] for s in SEM)
    # `kosulsuz == 0` SESSIZ `None` DEGIL, HATA. Once oyle degildi ve
    # koruma cokmeyi onlemiyor, iki katman asagi itiyordu:
    # `super_toto_frontend.py` govdeyi `round(...["kat"], 3)` ile okuyor
    # (TypeError) ve arayuz `kat_taban: number` deyip `.toFixed(1)`
    # cagiriyor. Uc katman da sayinin var oldugunu varsayiyordu; yalnizca
    # ureticinin kendisi aksini soyluyor ve kimseye soylemiyordu.
    #
    # Kosul ancak BIR macta uc sembolun de ya olasiligi ya oynanma payi
    # sifirsa saglanir — yani gercek veriyle degil, BOZUK veriyle. Boyle
    # bir girdide dogru cevap "sayi yok" degil "girdi bozuk"tur; deponun
    # `dixon_coles._gun` deki "bozuk tarih sessizce 0 olmaz, hata verir"
    # kurali burada da gecerli.
    if kosulsuz <= 0:
        raise ValueError(
            "kosulsuz rakip yogunlugu sifir: en az bir macta butun "
            "sembollerin olasiligi ya da oynanma payi sifir — girdi bozuk")
    return {
        "kosullu": kosullu,
        "kosulsuz": kosulsuz,
        "kat": kosullu / kosulsuz,
    }


def kupon_kur(probs: list[dict[str, float]],
              oynanma: list[dict[str, float]],
              kayip_orani: float = VARSAYILAN_KAYIP_ORANI
              ) -> dict[str, Any]:
    """Bütçe → hedef planı → kalabalık ayarı. Üç adım, üçü de görünür.

    **Bütçe eşik kuralından gelir** ve bu, `super_toto_hafta.kupon_kur` ile
    bilerek aynı: "hangi bütçe" sorusu veriden türetilemez, harcama
    kararıdır. Eşik kuralının ürettiği maliyeti tavan almak kuponu hiçbir
    hafta daha pahalı yapamaz (docs §3.19).
    """
    esik_secim = [secim_uret(p, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
                  for p in probs]
    esik_cift = sum(1 for s in esik_secim if len(s) == 2)
    esik_uclu = sum(1 for s in esik_secim if len(s) == 3)
    butce = (bedel_hesapla(esik_cift, esik_uclu)
             if esik_cift >= HAMMING_BLOK_BOYU else None)

    plan = en_iyi_secim(probs, butce) if butce else None
    if plan is None:
        # Eşik kuralı fix16 kuramıyorsa hedef kuralı çalıştırılamaz. Sessiz
        # düşüş yok: `kural` alanı gerçekte hangisinin kullanıldığını yazar.
        taban_secim = esik_secim
        kural = "esik"
    else:
        taban_secim = plan.secimler
        kural = "hedef"

    ayar = kalabalik_ayari(probs, oynanma, taban_secim, kayip_orani)
    return {
        "kural": kural,
        "butce": butce,
        "butce_kaynagi": ("esik kuralinin ayni haftada urettigi maliyet "
                          f"(banko {VARSAYILAN_BANKO}, uclu {VARSAYILAN_UCLU})"),
        "kayip_orani": kayip_orani,
        "esik": _kupon_govdesi(probs, oynanma, esik_secim),
        "taban": _kupon_govdesi(probs, oynanma, taban_secim),
        "ayarli": _kupon_govdesi(probs, oynanma, ayar.secimler),
        "ayar": {
            "degisimler": ayar.degisimler,
            "p_hedef_taban": ayar.taban_p_hedef,
            "p_hedef_ayarli": ayar.p_hedef,
            "oran_taban": ayar.taban_oran,
            "oran_ayarli": ayar.oran,
            "kirpildi": ayar.kirpildi,
            "not": ("Isaret SAYILARI degismez — bedel, satir ve motor "
                    "aynidir. Degisen yalnizca HANGI sembolun isaretlendigi."),
        },
    }


# ─── havuz ekseni ─────────────────────────────────────────────────────────

def havuz_bloku(kupon: dict[str, Any], probs: list[dict[str, float]],
                oynanma: list[dict[str, float]],
                havuz: float = VARSAYILAN_HAVUZ,
                kolon_bedeli: float = VARSAYILAN_KOLON_BEDELI
                ) -> dict[str, Any]:
    """Müşterek beklenen değer — **arayüze çıkmaz**, kayda geçer.

    `getiri` modülünün başlığı gerekçeyi yazıyor: bağıntıyı görmek için
    ≈71 ikramiyeli hafta gerekiyor ve elde 1 var. Buradaki sayılar
    varsayımların (havuz, komisyon, rakip kolon, kalabalık modeli)
    fonksiyonudur ve varsayımlarıyla birlikte okunmadıkları anda yalan
    söylerler. Bu yüzden gövde `varsayimlar` ve `uyari` taşır.
    """
    rakip = max(0, round(havuz / kolon_bedeli))
    q = {model: kalabalik_kademeleri(probs, model, oynanma)
         for model in KALABALIK_MODELLERI}
    out: dict[str, Any] = {
        "varsayim_kolon_bedeli": kolon_bedeli,
        "modeller": {},
        "model_notu": (
            "`orneklem` ve `favori` kalabaligi PIYASADAN turetir; kalabalik "
            "ayarinin kazancini tanim geregi goremezler. `oynanma` modeli "
            "olculmus oynanma paylarini kullanir ama o da KOSULSUZ hesaplar: "
            "rakibin isabeti bizim ne isaretledigimize bakmaz, dolayisiyla "
            "her plan icin ayni cikar. Ayarin kazancini goren sayi "
            "`kupon.<plan>.kosullu_rakip`tir ve yalnizca AYNI sekildeki "
            "planlar arasinda okunur (taban <-> ayarli). Oynanma paylari "
            "ayrica TEK bir platformun kullanicilarina aittir, Spor Toto "
            "havuzunun tamami degildir."),
    }
    for ad in ("taban", "ayarli"):
        g = kupon[ad]
        kademe = {14: g["p14"], 13: g["p13"], 12: g["p12"]}
        bedel = (g["columns"] or 0) * kolon_bedeli
        out["modeller"][ad] = {
            model: beklenen_getiri(kademe, bedel, havuz, rakip, q[model],
                                   VARSAYILAN_KOMISYON)
            for model in KALABALIK_MODELLERI
        }
    return out


# ─── duyarlılık ───────────────────────────────────────────────────────────

def marj_duyarliligi(d: dict[str, Any], yontem: str,
                     kayip_orani: float) -> dict[str, Any] | None:
    """Kuşkulu marjlı satır düzeltilseydi işaretler değişir miydi?

    2. haftanın 4. maçının (Fenerbahçe–Konyaspor) marjı %45,8; bültenin
    geri kalanı %17,5–17,9 bandında. Uyarı hafta dosyasında **insan
    tarafından** yazılmış ve kod da bağımsız olarak yakalamış durumda.
    Veriyi düzeltmiyoruz (doktrin: belirsiz veri uydurulmaz) ama sonucun
    ona **duyarlı olup olmadığını** ölçüyoruz.

    Kuşkulu satır yoksa `None` döner ve bu da bir cevaptır.
    """
    from scripts.super_toto_hafta import MARJ_SAPMA_ESIGI

    oranli = [(m, _marj(m["odds"])) for m in d["matches"] if not m["odds_yok"]]
    if len(oranli) < 3:
        return None
    ortanca = sorted(x[1] for x in oranli)[len(oranli) // 2]
    kuskulu = [(m, marj) for m, marj in oranli
               if 100 * abs(marj - ortanca) > MARJ_SAPMA_ESIGI]
    if not kuskulu:
        return None

    duzeltilmis: list[dict[str, float]] = []
    for m in d["matches"]:
        if m["odds_yok"]:
            duzeltilmis.append(dict.fromkeys(SEM, 1.0 / 3))
            continue
        oranlar = m["odds"]
        if any(m["no"] == k["no"] for k, _ in kuskulu):
            oranlar = _marji_esitle(oranlar, ortanca)
        duzeltilmis.append(implied_probs(oranlar, yontem))

    oynanma = [_oynanma(m) for m in d["matches"]]
    kupon = kupon_kur(duzeltilmis, oynanma, kayip_orani)
    return {
        "ortanca_marj": ortanca,
        "duzeltilen": [{"no": m["no"],
                        "mac": f"{m['home']} – {m['away']}",
                        "marj": marj,
                        "duzeltilmis_oran": _marji_esitle(m["odds"], ortanca),
                        "probs": duzeltilmis[m["no"] - 1]}
                       for m, marj in kuskulu],
        "picks": kupon["ayarli"]["picks"],
        "p_hedef": kupon["ayarli"]["p_hedef"],
        "columns": kupon["ayarli"]["columns"],
        "not": ("Veri DUZELTILMEDI; yalnizca sonucun kuskulu satira "
                "duyarliligi olculdu. Duzeltilmis oranlar kupona GIRMEZ."),
    }


# ─── kıyas ────────────────────────────────────────────────────────────────

def _kiyas(donmus: dict[str, Any] | None, probs: list[dict[str, float]],
           oynanma: list[dict[str, float]],
           kupon: dict[str, Any], arindirma: str) -> dict[str, Any] | None:
    """1. Tahmin ↔ 2. Tahmin — **aynı ölçekte**.

    Dondurulmuş kuponun kendi `p_hedef`i orantısal ölçekte hesaplanmıştı;
    yeni kuponunkiyle yan yana koymak iki farklı birimi karşılaştırmak
    olurdu. Bu yüzden eski işaretler **bugünkü olasılıklarla** yeniden
    ölçülür. Ölçülen şey işaretlerin kendisi, kaydın yeniden hesaplanması
    değil: `picks` olduğu gibi alınır, hiçbiri yeniden seçilmez.
    """
    if not donmus:
        return None
    eski = [list(p) for p in donmus["variants"][0]["picks"]]
    eski_govde = _kupon_govdesi(probs, oynanma, eski)
    yeni = kupon["ayarli"]
    eski_arindirma, eski_kural = _onceki_olcek(donmus)
    ayni_olcek = eski_arindirma == arindirma
    return {
        "eski_picks": ["".join(s) for s in eski],
        "eski_arindirma": eski_arindirma,
        "eski_kural": eski_kural,
        "eski_bugunku_olcekte": {
            "p_hedef": eski_govde["p_hedef"],
            "columns": eski_govde["columns"],
            "crowd_ratio": eski_govde["crowd_ratio"],
        },
        "yeni": {
            "p_hedef": yeni["p_hedef"],
            "columns": yeni["columns"],
            "crowd_ratio": yeni["crowd_ratio"],
        },
        "degisen_maclar": [i + 1 for i, (a, b)
                           in enumerate(zip(donmus["variants"][0]["picks"],
                                            yeni["picks"])) if a != b],
        # Uyari KOSULLU: iki kayit ayni olcekteyse "kiyaslanamaz" demek
        # yanlis olurdu — ve 3. haftadan beri cogunlukla ayni olcektedirler.
        "ayni_olcek": ayni_olcek,
        "not": ("Eski isaretler BUGUNKU olcekte yeniden olculdu; kayit "
                "yeniden hesaplanmadi. "
                + (f"Dondurulmus kupon da {eski_arindirma} olceginde "
                   "donduruldu, yani iki p_hedef DOGRUDAN kiyaslanabilir; "
                   "asagidaki yeniden olcum bir dogrulamadir."
                   if ayni_olcek else
                   f"Dondurulmus kuponun kendi p_hedef'i {eski_arindirma} "
                   "olceginde hesaplanmisti ve bu sayiyla dogrudan "
                   "kiyaslanamaz.")),
    }


# ─── gövde ────────────────────────────────────────────────────────────────

def uret(sezon: str, hafta: int,
         yontem: str = ARINDIRMA_VARSAYILAN,
         kayip_orani: float = VARSAYILAN_KAYIP_ORANI,
         havuz: float = VARSAYILAN_HAVUZ,
         tarih: str | None = None) -> dict[str, Any]:
    """Bir haftanın 2. Tahmin gövdesi.

    `tarih` kaydın dondurulduğu gündür (`YYYY-MM-DD`); verilmezse bugün.
    Testler sabitleyebilsin diye parametre — gövdedeki **tek** belirsiz
    alan budur, geri kalanı girdinin fonksiyonudur.
    """
    d = hafta_yukle(sezon, hafta)
    meta = d["meta"]
    maclar = d["matches"]

    # Dondurulmus kayit ONCE okunur: "onceki olcek" ondan turer, sabitten
    # degil. Once asagida okunuyordu ve `onceki` sabit bir yontemle
    # hesaplaniyordu — 3. haftadan beri yanlis olan tam olarak buydu.
    kupon_yolu = (KOK / "data" / "super_toto" / sezon
                  / f"hafta_{hafta:02d}_kupon.json")
    donmus = (json.loads(kupon_yolu.read_text(encoding="utf-8"))
              if kupon_yolu.exists() else None)
    onceki_arindirma, onceki_kural = _onceki_olcek(donmus)

    probs = [_probs(m, yontem) for m in maclar]
    onceki = [_probs(m, onceki_arindirma) for m in maclar]
    oynanma = [_oynanma(m) for m in maclar]

    # Görüşün zaman ağırlığı haftanın İLK maçından ölçülür — kaydın
    # dondurulduğu günden değil. İkisi karışırsa `tarih` parametresi
    # modelin gördüğü geçmişi de kaydırırdı.
    ilk_mac = min((m["date"] for m in maclar if m.get("date")), default=None)
    g = gorus_uret(maclar, ilk_mac)
    kupon = kupon_kur(probs, oynanma, kayip_orani)

    satirlar = []
    for i, m in enumerate(maclar):
        gr = g["rows"][i]
        satirlar.append({
            "no": m["no"], "lig": m["league"],
            "mac": f"{m['home']} – {m['away']}",
            "odds": m["odds"], "odds_yok": m["odds_yok"],
            "marj": m["margin"],
            "probs": probs[i],
            "probs_onceki": onceki[i],
            # Ölçek değişiminin bu maçtaki bedeli, puan cinsinden.
            "olcek_kaymasi": {s: probs[i][s] - onceki[i][s] for s in SEM},
            "play": oynanma[i],
            "dc": gr["dc"], "dc_var": gr["dc_var"],
            "elo_farki": gr["elo_farki"], "elo_beklenen": gr["elo_beklenen"],
            "taban": kupon["taban"]["picks"][i],
            "isaret": kupon["ayarli"]["picks"][i],
        })

    return {
        "meta": {
            "season": meta["season"], "week": meta["week"],
            "ad": "2. Tahmin",
            "frozen_at": tarih or date.today().isoformat(),
            "program": meta.get("program"),
            "results_known": bool(meta.get("results")),
            "arindirma": yontem,
            "onceki_arindirma": onceki_arindirma,
            "onceki_kural": onceki_kural,
            "kural": kupon["kural"],
            # Kaydın hangi OYNAMA SİSTEMİYLE kurulduğu. `arindirma` ve
            # `kural` gibi bir beyandır: kayıt kendi varsayımını yazmazsa
            # ileride yeniden üretilebilirliği ölçülemez, ve bayatlıkla
            # ölçek değişimi birbirine karışır.
            "sistem": "duz",
            "kayip_orani": kayip_orani,
            "note": ("SONUCLAR GORULMEDEN uretildi. 1. Tahmin'in kaydi "
                     "yerinde durur ve yeniden hesaplanmaz; bu ikinci bir "
                     "kayittir, bir duzeltme degil."),
            # YENILIK LISTESI TURETILIR. Once dort madde sabit yaziliydi ve
            # ilk ikisi 3. haftadan beri YALANDI: o kupon zaten shin+hedef
            # ile donduruldu, yani "orantili -> shin" ve "esik -> hedef"
            # diye bir degisiklik olmadi. Bir kayit, olmayan bir degisikligi
            # ilan edemez.
            "yenilikler": _yenilikler(onceki_arindirma, onceki_kural,
                                      yontem, kupon["kural"]),
            "veri_uyarilari": ((meta.get("data_warnings") or [])
                               + (meta.get("uretilen_uyarilar") or [])),
        },
        "matches": satirlar,
        "gorus": g,
        "ayrisma": ayrisma(g, probs),
        "kupon": kupon,
        "havuz": havuz_bloku(kupon, probs, oynanma, havuz),
        "duyarlilik": marj_duyarliligi(d, yontem, kayip_orani),
        "kiyas": _kiyas(donmus, probs, oynanma, kupon, yontem),
    }


# ─── yazım ────────────────────────────────────────────────────────────────

#: Uretilmis JSON metni TEK kaynaktan: `scripts._ortak.metin`. Ayni govde
#: uc betikte birebir yaziliydi ve `--kontrol` bayraklari tam da bu metnin
#: kararliligina dayaniyor.
_metin = metin


def yaz(govde: dict[str, Any], sezon: str, hafta: int,
        dizin: Path | None = None) -> Path:
    """Kaydı diske yazar. Sonucu bilinen haftada **yazmayı reddeder**."""
    if govde["meta"]["results_known"]:
        raise SystemExit(
            "Bu haftanin sonuclari biliniyor; 'sonuclar gorulmeden' diyen "
            "bir kayit yazilamaz. (meta.results dolu)")
    yol = ((dizin or (KOK / "data" / "super_toto" / sezon))
           / f"hafta_{hafta:02d}_tahmin2.json")
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(_metin(govde), encoding="utf-8")
    return yol


def yazdir(govde: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    meta = govde["meta"]
    k = govde["kupon"]
    print(f"\n{'='*78}\n{meta['season']} · {meta['week']}. HAFTA · "
          f"{meta['ad']} · {meta['frozen_at']}\n{'='*78}")
    for y in meta["yenilikler"]:
        print(f"  · {y}")

    _ony = meta["onceki_arindirma"]
    if _ony == meta["arindirma"]:
        print(f"\n─── 1. ÖLÇEK — 1. Tahmin ile AYNI ({_ony}); kayma yok ──────────────────")
    else:
        print("\n─── 1. ÖLÇEK — aynı oran, başka olasılık ────────────────────────────────")
    print(f"{'#':>2} {'Maç':<34} {meta['arindirma']+' 1/0/2':<16} "
          f"{_ony+' 1/0/2':<16} kayma (puan)")
    for r in govde["matches"]:
        yeni = "/".join(f"{100*r['probs'][s]:.0f}" for s in SEM)
        eski = "/".join(f"{100*r['probs_onceki'][s]:.0f}" for s in SEM)
        kay = "/".join(f"{100*r['olcek_kaymasi'][s]:+.0f}" for s in SEM)
        print(f"{r['no']:>2} {r['mac'][:34]:<34} {yeni:<16} {eski:<16} {kay}")

    g = govde["gorus"]
    print("\n─── 2. BAĞIMSIZ GÖRÜŞ — orana bakmadan ──────────────────────────────────")
    print(f"tarihçe {g['tarihce_mac']} maç (son {g['tarihce_son']}) · "
          f"kapsama %{100*g['kapsama']:.0f} · "
          f"{'kullanilabilir' if g['kullanilabilir'] else 'YETERSIZ'}")
    if g["eslesmeyen"]:
        print(f"korpusta karşılığı yok: {', '.join(g['eslesmeyen'])}")
    print(f"{'#':>2} {'Maç':<34} {'piyasa':<12} {'Dixon-Coles':<12} {'Elo farkı':<10} sapma")
    for r in govde["ayrisma"]:
        pi = "/".join(f"{100*r['piyasa'][s]:.0f}" for s in SEM)
        dc = "/".join(f"{100*r['dc'][s]:.0f}" for s in SEM)
        satir = next(x for x in govde["matches"] if x["no"] == r["no"])
        elo = (f"{satir['elo_farki']:+.0f}" if satir["elo_farki"] is not None
               else "—")
        isaret = " ← FAVORİ AYRIŞIYOR" if r["sembol_farkli"] else ""
        print(f"{r['no']:>2} {r['mac'][:34]:<34} {pi:<12} {dc:<12} {elo:<10} "
              f"{100*r['toplam_sapma']:.0f} puan{isaret}")
    print(f"\n{g['uyari']}")

    print("\n─── 3. KUPON ────────────────────────────────────────────────────────────")
    print(f"Bütçe {k['butce']:,} kolon ({k['butce_kaynagi']})")
    for ad, baslik in (("esik", "eşik kuralı (eski kural, yeni ölçek)"),
                       ("taban", "hedef kuralı (kalabalık görülmeden)"),
                       ("ayarli", "hedef + kalabalık ayarı  ← 2. TAHMİN")):
        v = k[ad]
        print(f"\n{baslik}")
        print(f"  {' '.join(v['picks'])}")
        print(f"  P(en iyi kolon ≥ 12) %{100*v['p_hedef']:.2f} · "
              f"{v['columns']:,} kolon · {v['rows']} satır · "
              f"küme-içi %{100*v['in_set_p']:.3f} · "
              f"kalabalık oranı {v['crowd_ratio']:.2f} · "
              f"kazanınca rakip yoğunluğu ×{v['kosullu_rakip']['kat']:.1f}")
    ayar = k["ayar"]
    print(f"\nKalabalık ayarı: hedef %{100*ayar['p_hedef_taban']:.2f} → "
          f"%{100*ayar['p_hedef_ayarli']:.2f} · "
          f"oran {ayar['oran_taban']:.2f} → {ayar['oran_ayarli']:.2f} · "
          f"rakip yoğunluğu ×{k['taban']['kosullu_rakip']['kat']:.1f} → "
          f"×{k['ayarli']['kosullu_rakip']['kat']:.1f}")
    for deg in ayar["degisimler"]:
        print(f"  {deg['no']:>2}. maç [{deg['taban']}] → [{deg['yeni']}]  "
              f"olasılık {100*deg['prob_taban']:.0f}→{100*deg['prob_yeni']:.0f} · "
              f"oynanma {100*deg['oynanma_taban']:.0f}→{100*deg['oynanma_yeni']:.0f}")

    kiyas = govde.get("kiyas")
    if kiyas:
        print("\n─── 4. 1. TAHMİN ↔ 2. TAHMİN (aynı ölçekte) ─────────────────────────────")
        print(f"1. Tahmin : {' '.join(kiyas['eski_picks'])}")
        print(f"2. Tahmin : {' '.join(govde['kupon']['ayarli']['picks'])}")
        e, y = kiyas["eski_bugunku_olcekte"], kiyas["yeni"]
        print(f"P(en iyi kolon ≥ 12): %{100*e['p_hedef']:.2f} → %{100*y['p_hedef']:.2f}")
        print(f"kolon               : {e['columns']:,} → {y['columns']:,}")
        print(f"kalabalık oranı     : {e['crowd_ratio']:.2f} → {y['crowd_ratio']:.2f}")
        print(f"işaret değişen maç  : {kiyas['degisen_maclar']}")

    duy = govde.get("duyarlilik")
    if duy:
        print("\n─── 5. DUYARLILIK — kuşkulu marj düzeltilseydi ──────────────────────────")
        for x in duy["duzeltilen"]:
            print(f"  {x['no']}. maç {x['mac']}: marj %{100*x['marj']:.1f} → "
                  f"%{100*duy['ortanca_marj']:.1f}")
        ayni = duy["picks"] == govde["kupon"]["ayarli"]["picks"]
        print(f"  işaretler: {' '.join(duy['picks'])}")
        print(f"  {'DEĞİŞMİYOR' if ayni else 'DEĞİŞİYOR'} · "
              f"P(en iyi kolon ≥ 12) %{100*duy['p_hedef']:.2f}")
        print(f"  {duy['not']}")

    print("\n─── 6. OYNANACAK SATIRLAR (16 satır, 14-garanti) ────────────────────────")
    for i, satir in enumerate(k["ayarli"]["lines"], 1):
        print(f"  {i:>2}  {satir}")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--hafta", type=int, default=2)
    ap.add_argument("--arindirma", default=ARINDIRMA_VARSAYILAN)
    ap.add_argument("--kayip-orani", type=float,
                    default=VARSAYILAN_KAYIP_ORANI,
                    help="P(en iyi kolon >= 12)'den kalabalik icin vazgecilecek en cok oran")
    ap.add_argument("--havuz", type=float, default=VARSAYILAN_HAVUZ)
    ap.add_argument("--tarih", default=None,
                    help="kaydin donduruldugu gun (YYYY-MM-DD); varsayilan bugun")
    ap.add_argument("--yaz", action="store_true",
                    help="kaydi hafta_NN_tahmin2.json'a yaz")
    ap.add_argument("--json", action="store_true")
    kosum.cli_ekle(ap)
    a = ap.parse_args(argv)

    govde = uret(a.sezon, a.hafta, a.arindirma, a.kayip_orani, a.havuz,
                 a.tarih)
    if a.json:
        print(_metin(govde), end="")
    else:
        yazdir(govde)
    if a.yaz:
        yol = yaz(govde, a.sezon, a.hafta)
        print(f"\nyazildi: {yol}")
    kosum.belki_kaydet("super_toto_tahmin2", govde, a)


if __name__ == "__main__":
    main()
