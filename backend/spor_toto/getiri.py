"""Müşterek bahis beklenen değeri (Faz 4.2).

`README.md` §1.6 uzun süre şunu yazıyordu:

> *"İkramiye / beklenen değer hesabı yapmaz (veri ilk kez birikiyor, ölçüm
> yok — §10)"*

Bu bir **ürün kararıydı** ve kısıtlar kalkarken o da kalktı. Ama kalkan şey
*hesabın yapılmaması*ydı; kalkmayan şey **ölçülmemiş bir sayının arayüze
çıkmaması**. Bu modül hesabı yapar ve **arayüze çıkmaz** — sebebi §6.3b'de
ölçülü: bağıntıyı görmek için ≈71 ikramiyeli hafta gerekiyor, elde **1**
var.

─── Sabit oranlı bahisten farkı — projenin en önemli tek ayrımı ──────────

`DIS_INCELEME.md` §7 bunu şöyle yazıyor::

    Sabit oranlı :  edge = p_model  − p_piyasa
    Müşterek     :  edge = p_piyasa − oynanma_payı

Sabit oranlıda kazanmak için **piyasayı yenmek** gerekir ve Faz 1–3 bunun
olmadığını on bir kez ölçtü. Müşterek bahiste gerekmez: piyasa olasılığını
olduğu gibi kullanıp yalnızca **kalabalığın ondan saptığı yeri**
işaretlemek yeter. Kelly burada yanlış alettir — sabit bir fiyata karşı
optimaldir, oysa havuzda ödeme kaç kişinin tutturduğuna bağlıdır.

─── Payın kapalı formu ───────────────────────────────────────────────────

Müşterek havuz **oyuncu başına değil, kazanan kolon başına** bölünür ve
bu ayrım sayının büyüklüğünü tamamen belirler: tek bir oyuncu on binlerce
kolon oynayabilir. Bu yüzden modelin nüfusu `rakip_kolon`dur — bizim
dışımızda oynanan kolon sayısı — ve `q` **bir kolonun** o kademeyi
tutturma olasılığıdır, bir oyuncunun değil.

Bizimle birlikte kazanan rakip kolon sayısı `W ~ Binom(N, q)` ise, kazanan
kolon başına düşen pay `1/(1+W)`'dir ve beklentisi **kapalı formda**
yazılır::

    E[1/(1+W)] = (1 − (1−q)^(N+1)) / ((N+1)·q)

Monte Carlo'ya gerek yok; sayı kesin ve deterministik. `q → 0` limitinde
ifade `1`'e gider ve kod o limiti ayrıca ele alır (0/0).

Kapalı form **doğrudan yazılırsa küçük `q`'da sayısal olarak çöker:**
`(1−q)^(N+1)` bire çok yakındır, `1 − ...` çıkarması anlamlı basamakları
yer ve `q = 1e-12`'de sonuç üçüncü hanede yanlış çıkar. Kod bu yüzden
`expm1`/`log1p` ile yazılıyor::

    1 − (1−q)^n  =  −expm1(n · log1p(−q))

Bekçi `test_q_sifir_limitinde_pay_tam`.

Bu formülün pratikteki anlamı sert: `N·q` büyüdükçe pay `1/(N·q)` gibi
söner. Yani **tutturmak yetmez, az kişiyle tutturmak gerekir** — projenin
havuz ekseninin bütün gerekçesi bu tek satırdadır.

─── Sayıyı belirleyen şey tahminci değil ─────────────────────────────────

Ölçümün asıl sonucu §3.34'te: kalabalık `orneklem` modeliyle işaretlendiğinde
getiri oranı 0,156, `favori` modeliyle 0,007 — **arada 22 kat**. Yani bu
eksende sonucu belirleyen bizim tahmincimiz değil, kalabalığın nasıl
oynadığına dair varsayım. Eksik olan yeni bir model değil, **oynanma
paylarının ölçümü**dür (`super_toto_hafta.kamuoyu`).

`p_k = q_k` alınırsa hesap tamamen çöker — bkz. `kalabalik_kademeleri`.

Not (§3.37): o ölçüm artık **var**. 2026/27 hafta dosyaları oynanma payını
taşıyor ve `kalabalik_kademeleri`nin üçüncü modeli (`oynanma`) onu
kullanıyor. Kalan boşluk paylardan değil, ikramiyeli hafta sayısından
geliyor — ve o hâlâ 1.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

#: Spor Toto'da ikramiye **12 bilenden** başlar (§5.2 bulgu 1: "14 hiçbir
#: zaman ulaşılabilir hedef değildi; doğru ölçü P(en iyi kolon ≥ 12)").
#: Kademeler yüksekten alçağa yazılır — pay dağıtımı öyle okunur.
KADEMELER: tuple[int, ...] = (14, 13, 12)

#: Havuzun kademelere dağılımı — **artık varsayım değil, ÖLÇÜM.**
#:
#: Önce `{14: 0.55, 13: 0.25, 12: 0.20}` yazıyordu ve başlığında "varsayım,
#: ölçüm değil; elde henüz bir haftalık kayıt var" diyordu. Üç haftanın
#: ikramiye ekranı girilince oran **kuruşuna kadar** çıktı ve üç haftada
#: birebir aynı:
#:
#:     kademe havuzu = kazanan kolon × kolon başına ödül
#:
#:     hafta 1:  15: 30.149.380,57 (devretti) · 14: 17.228.217,44
#:               13: 17.228.217,30 · 12: 21.535.245,96
#:     hafta 2:  15: 42.842.867,72 (+ 30.149.380,57 devir) · 14: 24.481.638,39
#:               13: 24.481.619,77 · 12: 30.601.899,20
#:     hafta 3:  15: 38.356.803,63 (devir YOK) · 14: 21.918.171,76
#:               13: 21.918.168,00 · 12: 27.397.501,56
#:
#: 3. hafta, oranın **devir düzeltmesi yapılmadan** doğrulandığı ilk hafta:
#: 15 bileni çıktığı için devreden pay yok ve tablo ham hâliyle okunuyor.
#:
#: 14'e bölününce üç haftada da **1,75 : 1 : 1 : 1,25** çıkıyor, yani
#: dağıtılan havuzun %35 / %20 / %20 / %25'i. Ölçüm `OLCULEN_PAY`de tam
#: hâliyle durur; `VARSAYILAN_PAY` onun bu modülün kademelerine (14-13-12)
#: düşen, 1'e normalize edilmiş dilimidir.
#:
#: **Değişmeyen varsayım:** havuzun kendisi (`havuz`) ve komisyon. Onlar
#: satış cirosundan gelir ve ciro hiçbir ekranda yayınlanmıyor.
OLCULEN_PAY: dict[int, float] = {15: 0.35, 14: 0.20, 13: 0.20, 12: 0.25}

#: Ölçümün kaynağı — sayı kadar önemli, çünkü bu satır olmadan yukarıdaki
#: oran bir daha "varsayım mı ölçüm mü" diye sorulur.
PAY_KAYNAGI = ("2026/27 1., 2. ve 3. hafta resmî ikramiye ekranları; üç "
               "hafta da 1,75:1:1:1,25 veriyor — 3. hafta devirsiz "
               "(docs §3.40, §3.47)")

VARSAYILAN_PAY: dict[int, float] = {
    k: OLCULEN_PAY[k] / sum(OLCULEN_PAY[x] for x in KADEMELER)
    for k in KADEMELER}

#: Havuzdan kesilen pay (komisyon + vergi). Yine **varsayım**.
VARSAYILAN_KOMISYON = 0.50


def pay_beklentisi(rakip_kolon: int, q: float) -> float:
    """`E[1/(1+W)]`, `W ~ Binom(rakip_kolon, q)` — kapalı form.

    `q` **bir rakip kolonun** o kademeyi tutturma olasılığıdır — bir
    oyuncunun değil (havuz kolon başına bölünür). `q = 0` ise kimse
    tutturmuyor demektir ve pay tamdır (1,0); formülün 0/0 limiti de odur::

        >>> pay_beklentisi(1000, 0.0)
        1.0
        >>> pay_beklentisi(0, 0.5)
        1.0

    Küçük `q`'da doğrudan yazılan form **çöker**: `(1−q)**n` bire yapışır
    ve çıkarma anlamlı basamakları yer. Fark yürütülebilir::

        >>> import math
        >>> n, q = 1001, 1e-12
        >>> naif = (1 - (1 - q) ** n) / (n * q)
        >>> round(naif, 10)
        0.9999778783
        >>> round(pay_beklentisi(1000, 1e-12), 10)
        0.9999999995

    Naif form dördüncü hanede yanlış — ve yanlış **yukarı** doğru değil
    aşağı doğru, yani havuz payını olduğundan küçük gösterir.

    Modülün asıl cümlesi bu iki satırda okunur — **tutturmak yetmez, az
    kişiyle tutturmak gerekir.** `N·q` on kat büyüyünce pay altıda bire
    iner::

        >>> round(pay_beklentisi(1000, 0.001), 5)
        0.63204
        >>> round(pay_beklentisi(10000, 0.001), 5)
        0.09999

    Rakip sayısı sabitken `q`'yu on katlamak da aynı yere götürür — sayıyı
    belirleyen `N·q` çarpımıdır::

        >>> round(pay_beklentisi(1000, 0.01), 5)
        0.0999
    """
    if rakip_kolon < 0:
        raise ValueError("rakip kolon sayisi negatif olamaz")
    if q <= 0.0:
        return 1.0
    if q >= 1.0:
        return 1.0 / (rakip_kolon + 1)
    n = rakip_kolon + 1
    # `1 - (1-q)**n` degil: kucuk q'da anlamli basamak kaybi verir.
    return -math.expm1(n * math.log1p(-q)) / (n * q)


def kademe_getirisi(havuz: float, komisyon: float, rakip_kolon: int,
                    q_kalabalik: float, pay_orani: float) -> float:
    """Bir kademeyi tutturmanın **beklenen** kazancı (bedel hariç)."""
    if not 0.0 <= komisyon < 1.0:
        raise ValueError("komisyon [0, 1) araliginda olmali")
    dagitilan = havuz * (1.0 - komisyon) * pay_orani
    return dagitilan * pay_beklentisi(rakip_kolon, q_kalabalik)


def beklenen_getiri(kademe_olasiliklari: dict[int, float],
                    bedel: float,
                    havuz: float,
                    rakip_kolon: int,
                    q_kalabalik: dict[int, float],
                    komisyon: float = VARSAYILAN_KOMISYON,
                    pay_dagilimi: dict[int, float] | None = None
                    ) -> dict[str, Any]:
    """`E[getiri] = Σ_k P(k) · pay(k) − bedel`.

    `kademe_olasiliklari` bizim kuponumuzun her kademeyi tutturma
    olasılığı (`secim`/`ortak.kacak_dagilimi` üretir).
    `q_kalabalik` **bir rakip kolonun** aynı kademeyi tutturma olasılığı
    (`kalabalik_kademeleri` üretir). İkisi farklı şeydir ve karıştırılırsa
    pay tamamen yanlış çıkar: bizimki bir **kaplamanın en iyi kolonuna**
    aittir, ötekisi **tek** bir kolona.

    Dönen gövde `varsayimlar` bloğunu **taşımak zorunda**: bu sayının
    tamamı varsayıma dayanıyor ve varsayımları görünmeden okunmamalı.
    """
    dagilim = pay_dagilimi or VARSAYILAN_PAY
    satirlar: list[dict[str, Any]] = []
    toplam = 0.0
    for k in KADEMELER:
        p = float(kademe_olasiliklari.get(k, 0.0))
        if p <= 0.0:
            continue
        q = float(q_kalabalik.get(k, 0.0))
        kazanc = kademe_getirisi(havuz, komisyon, rakip_kolon, q, dagilim.get(k, 0.0))
        katki = p * kazanc
        toplam += katki
        satirlar.append({
            "kademe": k, "p": p, "q_kalabalik": q,
            "beklenen_pay": kazanc,
            "beklenen_kazanan": rakip_kolon * q,
            "katki": katki,
        })

    return {
        "beklenen_kazanc": toplam,
        "bedel": bedel,
        "beklenen_getiri": toplam - bedel,
        # Oran 1'in ustundeyse kupon POZITIF beklenen degerli demektir.
        "getiri_orani": (toplam / bedel) if bedel > 0 else None,
        "kademeler": satirlar,
        "varsayimlar": {
            "havuz": havuz, "komisyon": komisyon, "rakip_kolon": rakip_kolon,
            "pay_dagilimi": dict(dagilim),
        },
        "uyari": (
            "Bu sayi OLCULMEDI. Havuz payi, komisyon ve kalabalik "
            "olasiliklari VARSAYIMDIR; §6.3b bagintiyi gorebilmek icin "
            "~71 ikramiyeli hafta gerektigini olctu ve elde 1 var. "
            "Arayuze cikmaz."),
    }


def duyarlilik(taban: dict[str, Any],
               carpanlar: Sequence[float] = (0.5, 1.0, 2.0),
               havuzu_olcekle: bool = False) -> list[dict[str, Any]]:
    """Rakip kolon sayısı çarpanlarına göre beklenen getiri.

    Tek bir sayı yerine bir **eğri** vermek, varsayımın ne kadar
    belirleyici olduğunu gösterir: `N·q` büyüdükçe pay `1/(N·q)` gibi
    söner ve beklenen getiri hızla düşer. Okur bunu görmeden tek bir
    rakama güvenmemeli.

    İki ayrı soru, iki ayrı eğri — ve **karıştırılırsa yanlış okunur**:

    ``havuzu_olcekle=False`` (varsayılan)
        Havuz sabit, kolon sayısı değişiyor: *"aynı para daha az kolona
        bölünseydi"*. Kolon başına daha çok para demektir, getiri yükselir.
    ``havuzu_olcekle=True``
        Havuz da aynı çarpanla ölçekleniyor: *"oyun büyüseydi/küçülseydi"*.
        Havuzun büyümesi ile seyrelmenin artması birbirini götürür. `N·q ≫ 1`
        rejiminde pay `havuz(1−c)·w/(N·q)`'ya iner ve eğri **tam olarak
        düzdür**; ancak `N·q ~ 1` olduğunda (küçük havuz) kıvrılır.
        Müşterek bahsin en önemli sezgisi budur: getiriyi belirleyen
        havuzun büyüklüğü değil, `p_k/q_k` oranıdır.
    """
    v = taban["varsayimlar"]
    kademe_p = {s["kademe"]: s["p"] for s in taban["kademeler"]}
    q = {s["kademe"]: s["q_kalabalik"] for s in taban["kademeler"]}
    out: list[dict[str, Any]] = []
    for c in carpanlar:
        rakip_kolon = max(0, round(float(v["rakip_kolon"]) * c))
        havuz = float(v["havuz"]) * c if havuzu_olcekle else float(v["havuz"])
        r = beklenen_getiri(kademe_p, taban["bedel"], havuz, rakip_kolon, q,
                            v["komisyon"], v["pay_dagilimi"])
        out.append({"carpan": c, "rakip_kolon": rakip_kolon, "havuz": havuz,
                    "beklenen_getiri": r["beklenen_getiri"],
                    "getiri_orani": r["getiri_orani"]})
    return out


def kupon_kademeleri(probs_listesi: Sequence[dict[str, float]],
                     butce: int) -> tuple[dict[int, float], int]:
    """Gerçek bir kupondan kademe olasılıkları — `(olasiliklar, bedel)`.

    **Bu fonksiyon olmadan motor yanlış kullanılır.** İlk sürümde CLI
    varsayılanları tek kolonun `P(14+) ≈ 0,0009`'unu 2.228 kolonluk bir
    bedelle topluyordu; iki sayı farklı şeylerin sayısıydı ve beklenen
    getiri oranı yapay olarak yerlerde çıkıyordu.

    Doğrusu garantinin aritmetiğinden gelir (`secim` modül başlığı):
    seçim kümesinin dışında kalan maç sayısı `k` ise en iyi kolon
    `14 − k` doğru tutturur. Yani::

        P(en iyi kolon = 14) = P(k = 0)
        P(en iyi kolon = 13) = P(k = 1)
        P(en iyi kolon = 12) = P(k = 2)

    `k`'nın dağılımı Poisson-binomdur (`ortak.kacak_dagilimi`) ve
    kaçak olasılıkları seçilen plandan çıkar.

    Not: bu bir **alt sınırdır** — kaplama bir kolonu tesadüfen daha iyi
    tutturabilir (§3.19). Yani beklenen getiri de temkinlidir.
    """
    from .ortak import kacak_dagilimi
    from .secim import en_iyi_secim, kacak_olasiligi

    plan = en_iyi_secim(list(probs_listesi), butce)
    if plan is None:
        return {}, 0
    kacaklar = [kacak_olasiligi(p, len(s))
                for p, s in zip(probs_listesi, plan.secimler)]
    dagilim = kacak_dagilimi(kacaklar)
    return ({14: dagilim[0] if len(dagilim) > 0 else 0.0,
             13: dagilim[1] if len(dagilim) > 1 else 0.0,
             12: dagilim[2] if len(dagilim) > 2 else 0.0},
            plan.bedel)


#: Kalabalığın nasıl işaretlediğine dair modeller.
#:
#: İlk ikisi **varsayım**: kalabalığın piyasa fiyatından ya da favoriden
#: türetildiğini kabul ederler. Üçüncüsü (`oynanma`) varsayım değil
#: **ölçüm** kullanır — gerçekten kaydedilmiş oynanma paylarını. `getiri`
#: modül başlığı uzun süre şunu yazıyordu: *"Eksik olan yeni bir model
#: değil, oynanma paylarının ölçümüdür."* O ölçüm 2026/27 hafta
#: dosyalarında var (`super_toto_hafta.kamuoyu`) ve bu model onu kullanır.
#:
#: Ölçüm de kusursuz değil ve kusuru yazılmalı: paylar **tek bir
#: platformun** kendi kullanıcılarınındır, Spor Toto havuzunun tamamı
#: değildir. Yani `oynanma` modeli varsayımı daraltır, kaldırmaz.
KALABALIK_MODELLERI: tuple[str, ...] = ("orneklem", "favori", "oynanma")


def kalabalik_kademeleri(probs_listesi: Sequence[dict[str, float]],
                         model: str = "orneklem",
                         oynanma_listesi: Sequence[dict[str, float]] | None = None
                         ) -> dict[int, float]:
    """**Tek bir rakip kolonun** her kademeyi tutturma olasılığı.

    Bu fonksiyon olmadan motorun çıktısı boştur. İlk sürüm `q`'yu bizim
    kademe olasılıklarımıza eşitliyordu ve o özel durumda sonuç
    aritmetik olarak çöküyor::

        p_k = q_k  ve  N·q ≫ 1   ⇒   E[kazanç] = havuz·(1−c)/(N+1)

    yani havuzun kademelere nasıl bölündüğünden de, bizim ne oynadığımızdan
    da **bağımsız** bir sayı. Bekçisi
    `test_ortalama_oyuncuysak_pay_bolusumu_hicbir_sey_degistirmez`. Kazanç
    ancak `p_k > q_k` olan kademeden — kalabalıktan **saptığımız** yerden —
    doğar; `DIS_INCELEME.md` §7'nin `edge = p_piyasa − oynanma_payı`
    satırının kapalı formdaki karşılığı budur.

    İki model:

    ``orneklem``
        Rakip her maçı piyasa dağılımından **çekiyor**. Maç başına isabet
        `r = Σ_s p(s)²`. Kalabalığın çeşitliliğini korur.
    ``favori``
        Rakip her maçta favoriyi işaretliyor: `r = max_s p(s)`. Üst sınır —
        gerçek kalabalık bundan daha dağınıktır.
    ``oynanma``
        Rakip **ölçülmüş** oynanma paylarından çekiyor: `r = Σ_s o(s)·p(s)`.
        Kare DEĞİL çapraz terim, ve fark esastır: rakibin işareti `o`dan,
        gerçek sonuç `p`den gelir. `orneklem` bu ifadenin `o = p` özel
        hâlidir — yani kalabalığın piyasayla aynı oynadığı varsayımı.
        `oynanma_listesi` verilmezse bu model çağrılamaz.

    Gerçek kalabalık ilk ikisinin arasındadır ve hangisinin seçildiği
    sonucu büyük ölçüde belirler; bu yüzden model adı `varsayimlar`a
    yazılır. Üçüncüsü o aralığı tahmin etmez, **ölçer**.

    Üçünün de gördüğü şey aynı biçimde **koşulsuzdur**: rakibin isabeti
    bizim ne işaretlediğimize bakmaz, dolayısıyla bu sayı iki farklı plan
    için birebir aynı çıkar. Havuz ise biz kazandığımızda bölünür; o
    koşullu soruyu `scripts/super_toto_tahmin2._kosullu_rakip` cevaplar
    (docs §3.37).

    Kademeler `KADEMELER` ile aynı okunur: en üst kademe **en az** o kadar
    doğru (kaplamanın tavanı 14'tür), alttakiler **tam** o kadar.
    """
    if model not in KALABALIK_MODELLERI:
        raise ValueError(f"bilinmeyen kalabalik modeli: {model}")
    if model == "oynanma" and oynanma_listesi is None:
        raise ValueError("'oynanma' modeli oynanma_listesi ister")
    if (oynanma_listesi is not None
            and len(oynanma_listesi) != len(probs_listesi)):
        raise ValueError("oynanma ve olasilik listeleri ayni uzunlukta olmali")
    from .core import SEMBOLLER
    from .ortak import kacak_dagilimi

    def _normal(d: dict[str, float]) -> list[float]:
        v = [max(0.0, float(d.get(s, 0.0))) for s in SEMBOLLER]
        toplam = sum(v) or 1.0
        return [x / toplam for x in v]

    isabet = []
    for i, p in enumerate(probs_listesi):
        v = _normal(p)
        if model == "orneklem":
            isabet.append(sum(x * x for x in v))
        elif model == "favori":
            isabet.append(max(v))
        else:
            o = _normal(oynanma_listesi[i])  # type: ignore[index]
            isabet.append(sum(a * b for a, b in zip(o, v)))

    # `kacak_dagilimi` KACAK sayisinin dagilimini verir: d[m] = tam m yanlis.
    d = kacak_dagilimi([1.0 - r for r in isabet])
    tavan = KADEMELER[0]
    out: dict[int, float] = {}
    for i, k in enumerate(KADEMELER):
        # tavan kademesi: yanlis sayisi <= (mac - tavan) → "en az"
        if i == 0:
            esik = len(isabet) - tavan
            out[k] = sum(d[: esik + 1]) if esik >= 0 else 0.0
        else:
            m = len(isabet) - k
            out[k] = d[m] if 0 <= m < len(d) else 0.0
    return out


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    """Elle koşum — **ürüne çıkmaz**, varsayımları görünür kılar.

        python -m spor_toto.getiri --havuz 50000000 --butce 4096
    """
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--havuz", type=float, default=50_000_000.0)
    ap.add_argument("--butce", type=int, default=4096,
                    help="kolon butcesi (secim plani buna gore kurulur)")
    ap.add_argument("--kolon-bedeli", type=float, default=1.5)
    ap.add_argument("--komisyon", type=float, default=VARSAYILAN_KOMISYON)
    ap.add_argument("--kalabalik", choices=KALABALIK_MODELLERI,
                    default="orneklem")
    ap.add_argument("--rakip-kolon", type=int, default=None,
                    help="varsayilan: havuz / kolon bedeli (tutarli olsun diye)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    # Kademe olasiliklari GERCEK bir kupondan turetilir — elle girilen
    # sayilar iki farkli seyin sayisini karistirmaya cok musait.
    from .backtest import hafta_girdileri

    haftalar = [h for h in hafta_girdileri() if h["usable"]]
    if not haftalar:
        raise SystemExit("olculebilir hafta yok — oran arsivi eksik")
    hafta = haftalar[-1]
    kademe_p, kolon = kupon_kademeleri(hafta["probs"], a.butce)
    if not kademe_p:
        raise SystemExit("butce hicbir plani karsilamiyor")
    bedel = kolon * a.kolon_bedeli

    # Rakip kolon sayisi havuzdan TURETILIR. Elle verilirse iki sayi
    # birbirini tutmayabilir: 400.000 "oyuncu" ile 50 milyonluk havuz
    # kisi basi 125 TL demektir ve o varsayim gorunmeden kalir.
    rakip_kolon = (a.rakip_kolon if a.rakip_kolon is not None
                   else max(0, int(a.havuz / a.kolon_bedeli) - kolon))
    q = kalabalik_kademeleri(hafta["probs"], a.kalabalik)

    r = beklenen_getiri(kademe_p, bedel, a.havuz, rakip_kolon, q, a.komisyon)
    if a.json:
        print(json.dumps({**r, "kalabalik_modeli": a.kalabalik,
                          "duyarlilik": duyarlilik(r)},
                         ensure_ascii=False, indent=1))
        return

    print(f"\nKupon: {hafta['week']}. hafta · butce {a.butce:,} · "
          f"kurulan {kolon:,} kolon · bedel {bedel:,.0f}")
    print(f"BEKLENEN GETIRI — havuz {a.havuz:,.0f} · rakip kolon "
          f"{rakip_kolon:,} · komisyon %{100*a.komisyon:.0f} · "
          f"kalabalik '{a.kalabalik}'")
    print(f"{'kademe':>7}{'P(biz)':>10}{'q(kolon)':>12}"
          f"{'bekl. kazanan':>15}{'bekl. pay':>14}{'katki':>14}")
    for x in r["kademeler"]:
        print(f"{x['kademe']:>7}{x['p']:>10.5f}{x['q_kalabalik']:>12.2e}"
              f"{x['beklenen_kazanan']:>15,.0f}{x['beklenen_pay']:>14,.0f}"
              f"{x['katki']:>14,.0f}")
    print(f"\n  beklenen kazanc {r['beklenen_kazanc']:>14,.0f}")
    print(f"  bedel           {r['bedel']:>14,.0f}")
    print(f"  BEKLENEN GETIRI {r['beklenen_getiri']:>14,.0f}"
          f"   (oran {r['getiri_orani']:.3f})")

    for baslik, olcekle in (("havuz SABIT", False), ("havuz da olcekli", True)):
        print(f"\nRakip kolon sayisina duyarlilik ({baslik}):")
        for d in duyarlilik(r, (0.25, 0.5, 1.0, 2.0, 4.0), olcekle):
            print(f"  x{d['carpan']:<5} kolon {d['rakip_kolon']:>12,}"
                  f"   getiri {d['beklenen_getiri']:>14,.0f}"
                  f"   oran {d['getiri_orani']:.3f}")

    print(f"\n{r['uyari']}")


if __name__ == "__main__":  # pragma: no cover
    main()
