"""Haftanın hakkı — bütçe bir **kısıt** olmaktan çıkınca geriye ne kalıyor.

Bugüne kadar haftanın planı tek bir çağrıyla kuruluyordu::

    sistem_secimi(probs, butce_tl=2000.0, garanti=14)

ve E2 bunun bedelini sayıya çevirdi (`docs/KAZANMA_PLANI.md` §3.57):

    *"Üç hedef de aynı şekli alıyor (3 çifte + 5 üçlü, 168 kolon), çünkü
    çifte/üçlü eklemek P(k ≤ eşik)'i hangi eşikte olursa olsun büyütür —
    yani şekli **bütçe** belirliyor, hedef değil."*

Yani haftanın planını haftanın kendisi değil, kenardan verilmiş bir sayı
seçiyordu. Bu modül o sayıyı kaldırır ve yerine ne konabileceğini sorar.

─── Kaldırınca iki ölçü birden bozuluyor, ve ikisi de ZITTIR ───────────────

**1. `P(hedef)` bütçesiz enbüyüklenemez.** Bir maça sembol eklemek kaçak
olasılığını düşürür, hiçbir zaman yükseltmez; dolayısıyla `P(k ≤ eşik)`
harcamada **azalmayan** bir fonksiyondur (`cephe` bunu her hafta üretir ve
`test_hafta_hakki` bekçisi tutar). Ve tavanı gerçekten görüyor: 14-garantide
cephe **`P = 1`**'e çıkıyor — 2 banko + 13 üçlü, **590.490 TL**, çünkü eşik
`k ≤ 2` iken 13 üçlü kaçağı tanım gereği ikiye kilitler. Yani "bütçe yok,
`P(hedef)`'i enbüyükle" sorusunun cevabı her hafta aynıdır ve haftaya hiç
bakmaz: *en büyük şekli al.* Kısıt kalkınca hedef fonksiyonu anlamını
yitiriyor.

**2. Para ölçüsü ise TERS yönde dejenere.** `beklenen_tl` de `hafta_karnesi`
de **garanti tabanını** kullanır — `k` kaçakta *bir* kolon `G−k`
kademesinde — ve o taban kolon sayısını hiç görmez: 32 kolonluk kupon da,
486 kolonluk kupon da tek kolon ödülü sayılır. Ölçüldü — 2026/27 **2.
hafta**, cephenin 15 basamağı (`--para 2026_27:2`, `beklenen_tl` ·
`RAKIP_KOLON`)::

        320 TL →  E[TL]  39      E/maliyet 0,121
      4.860 TL →  E[TL] 510      E/maliyet 0,105

Yani model ödülü maliyetle birlikte büyüyor ama **oranı her basamakta
1'in çok altında** kalıyor: 2. haftanın 15 basamağında 0,093–0,121, 3.
haftanın 14 basamağında 0,082–0,115 — E1'in `taban_roi`'siyle aynı
mertebe, ve E1 o tabanın 2,39 kat gevşek olduğunu ölçmüştü. Dolayısıyla
`E[TL] − maliyet` her adımda daha da negatifleşiyor ve "bütçe yok,
`E[TL] − maliyet`'i enbüyükle" sorusunun cevabı da her hafta aynıdır ve
haftaya hiç bakmaz: *en küçüğü al* — ya da hiç oynama.

İki dejenerasyon da haftanın değil **ölçünün** özelliğidir. Bu yüzden bu
modül ikisini de hedef fonksiyonu olarak kullanmaz; ikisini de tek bir
gerçekleşmiş sayıya karşı **sınar**.

─── O yüzden ölçü: haftanın CETVELİ ──────────────────────────────────────

E1 tabanın gevşekliğini ölçerken gereken makineyi kurmuştu
(`karne.gercek_kolon_dagilimi`): 14-garantide kolonları depo üretebiliyor,
kademe dağılımı sayılabiliyor ve **resmî ikramiye tablosuna** vurulabiliyor.
Cetvel budur — bir hafta için cephenin *her* basamağında:

    şekil · kolon · maliyet · P(hedef) · GERÇEKLEŞEN ödül

Cetvel bir kural değildir, kuralların **sınav kâğıdıdır**: sabit bütçe de,
λ kuralı da, "hep en büyük" de aynı tablodan puanlanır ve hiçbiri kendi
ürettiği sayıyla değerlendirilmez.

─── Kural: λ · P(hedef) − maliyet ────────────────────────────────────────

Bütçe yerine geçen tek serbestlik `λ`: **bir birim `P(hedef)`'in TL
karşılığı.** Kural, cephede `λ·p − tl`'yi enbüyükleyen basamağı seçer. İki
ucu da doğru davranır — `λ → 0` en ucuz şekli, `λ → ∞` en büyüğünü seçer —
ve arada haftaya göre **değişir**: aynı `λ` ile keskin hafta büyük, dağınık
hafta küçük kupon alır. Aranan şey buydu.

`λ`'nın uydurulmasına gerek yok: satın alınan olayın (12+ tutturma) parasal
karşılığıdır ve **ölçülebilir** (`lambda_kestir`). Aynı haftadan hem `λ`
kestirip hem o haftada sınamak iç örneklem olurdu; `kural_kiyasi` bu yüzden
`λ`'yı **haftayı dışarıda bırakarak** (LOO) da kestirir ve iki sayıyı yan
yana basar.

─── Kuralın taşıdığı varsayım, açıkça ────────────────────────────────────

`λ·p` ancak "tutturunca alınan para kuponun boyutundan bağımsız" olsaydı
beklenen ödül olurdu. Değil: büyük kuponun aynı kademede daha çok kolonu
olur (E1: 12. kademede `k=0` iken ~21 kolon). Yani kural büyük şekilleri
**eksik** değerler, yönü bellidir ve cetvel bunu düzeltmez — ölçer.

    python -m spor_toto.hafta_hakki --cephe          # tek haftanin cephesi
    python -m spor_toto.hafta_hakki --cetvel --hafta 20
    python -m spor_toto.hafta_hakki --kiyas          # YAVAS (~20 dk)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections.abc import Sequence
from typing import Any, NamedTuple

from .getiri import KOLON_BEDELI
from .karne import (
    BOOTSTRAP,
    _medyan,
    bootstrap_farki,
    gercek_kolon_dagilimi,
    gercek_odul,
    kupon_kesiti,
)
from .secim import sistem_secimi
from .sistem import HEDEF_KADEME, VARSAYILAN_GARANTI, kacak_esigi, sekiller

#: Cephenin ölçüm tavanı (TL) — **ürün kuralı değil, hesap sınırı.**
#:
#: Cetvelin her basamağı `engines.run_auto` ile gerçek kolon üretmeyi
#: gerektirir ve maliyeti kolon sayısıyla büyür (ölçüldü: 32 kolon 0,25 sn,
#: 486 kolon 1,3 sn, 1.728 kolon 7,3 sn). 5.000 TL = 500 kolon bandı 114
#: haftayı ~20 dakikada bitiriyor; üstü saatlere çıkar.
#:
#: Tavanın **bağlayıcı olup olmadığı ölçülür**: `kural_kiyasi` kaç haftada
#: en üst basamağın seçildiğini `tavan_dayanma` alanında sayar. Sıfırdan
#: büyükse sonuç kırpılmış demektir ve öyle okunmalıdır.
CEPHE_TAVANI = 5000.0

#: `lambda_kestir`in tarama bandı (TL / birim `P(hedef)`).
LAMBDA_BANDI: tuple[float, ...] = (
    1_000.0, 2_000.0, 5_000.0, 10_000.0, 20_000.0, 50_000.0, 100_000.0)


class Adim(NamedTuple):
    """Cephenin bir basamağı: bu parayı verirsen bu şekli ve bu `p`'yi alırsın."""

    tl: float
    kolon: int
    banko: int
    cift: int
    uclu: int
    p_hedef: float
    secimler: list[list[str]]

    @property
    def sekil(self) -> str:
        """`6b/1ç/8ü` biçiminde kısa ad."""
        return f"{self.banko}b/{self.cift}ç/{self.uclu}ü"


def cephe(probs_listesi: list[dict[str, float]],
          garanti: int = VARSAYILAN_GARANTI,
          kademe: int | None = None,
          en_cok_tl: float | None = CEPHE_TAVANI,
          yol: str | None = None) -> list[Adim]:
    """Haftanın **bütün** satın alma basamakları — bütçe kısıtı olmadan.

    Satılan her fiyat basamağı için `sistem_secimi` bir kez koşturulur ve
    aynı şekli veren basamaklar teklenir. Dönen liste maliyete göre artan
    sıradadır ve `p_hedef` de artar (azalmaz) — bu, modül başlığındaki
    birinci dejenerasyonun kendisidir ve bekçisi `test_hafta_hakki`dedir.

    `en_cok_tl` **ölçüm** sınırıdır (`CEPHE_TAVANI`); `None` verilirse
    tablonun tamamı taranır — cephe hesabı ucuzdur (~0,2 sn/hafta), pahalı
    olan cetveldir.
    """
    n = len(probs_listesi)
    fiyatlar = sorted({s.tl for s in sekiller(garanti, yol=yol)
                       if s.tek + s.cift + s.kapali == n})
    out: list[Adim] = []
    for tl in fiyatlar:
        if en_cok_tl is not None and tl > en_cok_tl:
            break
        plan = sistem_secimi(probs_listesi, tl, garanti=garanti,
                             kademe=kademe, yol=yol)
        if plan is None or (out and plan.bedel == out[-1].kolon):
            continue
        out.append(Adim(tl=plan.bedel * KOLON_BEDELI, kolon=plan.bedel,
                        banko=plan.banko, cift=plan.cift, uclu=plan.uclu,
                        p_hedef=plan.p_hedef, secimler=plan.secimler))
    return out


def marjinal_secim(adimlar: Sequence[Adim], lam: float) -> Adim | None:
    """`λ·p − tl`'yi enbüyükleyen basamak; eşitlikte **ucuz** olan kazanır.

    `λ` bir birim `P(hedef)`'in TL karşılığıdır. Kuralın haftaya duyarlılığı
    buradan gelir: aynı `λ` altında `p` ucuz olan hafta büyük, pahalı olan
    hafta küçük kupon alır.

        >>> a = [Adim(320.0, 32, 7, 8, 0, 0.09, []),
        ...      Adim(1680.0, 168, 7, 3, 5, 0.29, [])]
        >>> marjinal_secim(a, 1_000.0).kolon    # ucuz lambda: kucuk sekil
        32
        >>> marjinal_secim(a, 20_000.0).kolon   # pahali lambda: buyuk sekil
        168
    """
    if not adimlar:
        return None
    return max(adimlar, key=lambda a: (lam * a.p_hedef - a.tl, -a.tl))


def sabit_secim(adimlar: Sequence[Adim], butce_tl: float) -> Adim | None:
    """Bugünkü ürünün kuralı: bütçeye sığan **en büyük** basamak."""
    uygun = [a for a in adimlar if a.tl <= butce_tl]
    return uygun[-1] if uygun else None


def hafta_cetveli(h: dict[str, Any],
                  garanti: int = VARSAYILAN_GARANTI,
                  kademe: int | None = None,
                  en_cok_tl: float | None = CEPHE_TAVANI) -> dict[str, Any]:
    """Bir haftanın cetveli: her basamakta **gerçekleşen** ödül.

    Ödül `karne.gercek_kolon_dagilimi` + `gercek_odul` ikilisinden gelir,
    yani garanti tabanı değil **motorun ürettiği kolonların** o haftanın
    resmî ikramiye tablosundaki karşılığı; kolon sayısı satıcının şekline
    indirgenir. E1'in varsayımı aynen devralınır ve orada yazılıdır:
    satıcının daha az kolonu motorunkiyle aynı biçimde dağılıyor sayılır.

    Kaplama üretilemeyen basamak **atlanır** (`None` dönmez) — cetvelin
    eksik basamağı olabilir ve `basamak` alanı kaç tane ölçüldüğünü söyler.
    """
    if garanti != 14:
        raise ValueError(
            "cetvel yalniz 14-garantide kosar: gercek kolonlari uretebilen "
            "tek yer orasi (karne.gercek_kolon_dagilimi, core.py yaricap 1)")
    kad = HEDEF_KADEME if kademe is None else kademe
    esik = kacak_esigi(garanti, kad)
    adimlar = cephe(h["probs"], garanti=garanti, kademe=kademe,
                    en_cok_tl=en_cok_tl)
    basamaklar: list[dict[str, Any]] = []
    for a in adimlar:
        dagilim = gercek_kolon_dagilimi(a.secimler, h["gercek"],
                                        hedef_kolon=a.kolon)
        odul = gercek_odul(dagilim, h["tablo"], hedef_kademe=kad)
        if odul is None:
            continue
        kacak = sum(1 for s, c in zip(a.secimler, h["gercek"]) if c not in s)
        basamaklar.append({
            "tl": a.tl, "kolon": a.kolon, "sekil": a.sekil,
            "banko": a.banko, "cift": a.cift, "uclu": a.uclu,
            "p_hedef": a.p_hedef, "kacak": kacak,
            "tuttu": kacak <= esik,
            "odul": odul, "net": odul - a.tl,
            "roi": odul / a.tl if a.tl else 0.0,
        })
    return {"sezon": h["sezon"], "hafta": h["hafta"],
            "basamak": len(basamaklar), "basamaklar": basamaklar}


def cetvel(hafta_siniri: int | None = None,
           garanti: int = 14,
           kademe: int | None = None,
           en_cok_tl: float | None = CEPHE_TAVANI,
           kesit: Sequence[dict[str, Any]] | None = None
           ) -> list[dict[str, Any]]:
    """Kesitin tamamı için cetvel — **yavaş** (114 hafta ≈ 20 dk).

    Yalnız 14-garantide koşar, çünkü kolonları üretebilen tek yer orası
    (`engines.run_auto`, `core.py` yarıçap 1'e kilitli) — E1'in sınırı
    aynen geçerli.
    """
    kes = list(kupon_kesiti()) if kesit is None else list(kesit)
    if hafta_siniri:
        kes = kes[:hafta_siniri]
    out = []
    for h in kes:
        c = hafta_cetveli(h, garanti=garanti, kademe=kademe,
                          en_cok_tl=en_cok_tl)
        if c["basamak"]:
            out.append(c)
    return out


def para_cephesi(sezon: str, hafta: int,
                 garanti: int = 14,
                 en_cok_tl: float | None = CEPHE_TAVANI) -> list[dict[str, Any]]:
    """Cephenin her basamağında modelin `E[TL]`'si — **ikinci dejenerasyonun
    ölçümü.**

    Modül başlığının 2. maddesi bir iddiadır ve bu fonksiyon onu üretir:
    `E[TL] / maliyet` cephe boyunca 1'in çok altında kalıyorsa
    `E[TL] − maliyet` en küçük basamakta enbüyüktür, yani bütçesiz para
    enbüyüklemesi haftayı hiç görmeden "en küçüğü al" der.

    Canlı hafta yükünden koşar (resmî ikramiye tablosu oradan gelir);
    ikramiye ilan edilmemişse boş liste döner.
    """
    from .getiri import beklenen_tl, kademe_havuzlari
    from .kalabalik import OLCULEN, oynanma_paylari
    from .karne import RAKIP_KOLON, canli_hafta

    h = canli_hafta(sezon, hafta)
    if h is None:
        return []
    havuzlar = kademe_havuzlari(h["payout"])
    if not havuzlar:
        return []
    oynanma = h["play"] or oynanma_paylari(h["probs"], OLCULEN)
    out = []
    for a in cephe(h["probs"], garanti=garanti, en_cok_tl=en_cok_tl):
        e = beklenen_tl(h["probs"], oynanma, a.secimler, {}, havuzlar,
                        garanti, RAKIP_KOLON)
        out.append({"tl": a.tl, "kolon": a.kolon, "sekil": a.sekil,
                    "p_hedef": a.p_hedef, "beklenen_tl": e,
                    "e_bolu_maliyet": e / a.tl if a.tl else 0.0,
                    "net": e - a.tl})
    return out


def lambda_kestir(cetveller: Sequence[dict[str, Any]],
                  disarida: tuple[str, int] | None = None,
                  referans_tl: float = 2000.0) -> float:
    """`λ`'yı **gerçekleşen paradan** kestirir: tutturan haftanın ortalama ödülü.

    `λ` "bir birim `P(hedef)` kaç TL eder" sorusunun cevabıdır; satın alınan
    olay `k ≤ eşik`, o olayın parası da tutturan haftalarda gerçekleşen
    ödüldür. Referans basamak sabit tutulur (bugünkü ürünün bütçesi), yoksa
    kestirim kuralın kendi seçimine bağlı olur ve döngü kapanır.

    `disarida` verilirse o hafta kestirimden çıkarılır — `kural_kiyasi`'nin
    LOO kolu budur.
    """
    oduller = []
    for c in cetveller:
        if disarida and (c["sezon"], c["hafta"]) == disarida:
            continue
        ref = [b for b in c["basamaklar"] if b["tl"] <= referans_tl]
        if not ref:
            continue
        b = ref[-1]
        if b["tuttu"]:
            oduller.append(b["odul"])
    if not oduller:
        return 0.0
    return sum(oduller) / len(oduller)


def basamak_karnesi(cetveller: Sequence[dict[str, Any]]
                    ) -> list[dict[str, Any]]:
    """Her basamağın kendi karnesi — **kuralsız**, merdivenin çıplak hâli.

    Kural kıyası "hangi seçim daha iyi" sorusunu sorar; bu tablo ondan
    önceki soruyu sorar: *bir basamak parasını çıkarıyor mu?* Her kolon
    sayısı için o basamağı ölçebilmiş bütün haftalar toplanır ve üç sayı
    verilir:

    * ``ort_odul`` — hafta başına gerçekleşen ödül (tutmayan hafta = 0)
    * ``roi`` — `ort_odul / maliyet`; 1'in altındaysa o basamak kaybediyor
    * ``odul_tuttu`` — **tutturunca** alınan ortalama para; λ'nın ta kendisi

    `odul_tuttu`nun kolon sayısıyla nasıl büyüdüğü ayrıca döner
    (`odul_tuttu_kolon`), çünkü `marjinal_secim`in taşıdığı varsayım tam
    olarak "büyümez"dir ve buradan **ölçülür**.
    """
    from collections import defaultdict

    hep: dict[int, list[float]] = defaultdict(list)
    tuttu: dict[int, list[float]] = defaultdict(list)
    for c in cetveller:
        for b in c["basamaklar"]:
            hep[b["kolon"]].append(b["odul"])
            if b["tuttu"]:
                tuttu[b["kolon"]].append(b["odul"])
    out = []
    for kolon in sorted(hep):
        tl = kolon * KOLON_BEDELI
        v = hep[kolon]
        t = tuttu.get(kolon, [])
        ort = sum(v) / len(v)
        ort_t = sum(t) / len(t) if t else 0.0
        out.append({
            "kolon": kolon, "tl": tl, "hafta": len(v), "tutan": len(t),
            "ort_odul": ort, "roi": ort / tl if tl else 0.0,
            "odul_tuttu": ort_t,
            "odul_tuttu_kolon": ort_t / kolon if kolon else 0.0,
        })
    return out


def fiyat_karnesi(cetveller: Sequence[dict[str, Any]],
                  referans_tl: float = 2000.0) -> dict[str, Any]:
    """Merdivenin bir birim `P(hedef)`'i kaça sattığı — λ'nın karşı tarafı.

    `lambda_kestir` satın alınan şeyin **ettiğini** ölçer; bu fonksiyon
    **istenen fiyatı**. Üçü birden dönüyor çünkü üçü çok farklı:

    * ``uctan_uca`` — en ucuz basamaktan en pahalıya toplam maliyet farkının
      toplam `p` farkına oranı; merdivenin ortalama fiyatı.
    * ``bir_ust`` — referans basamaktan (bugünkü bütçe) bir üst basamağa
      geçmenin fiyatı. Karar tam olarak budur.
    * ``en_ucuz_adim`` — haftanın en ucuz tek adımı. Merdivende bedavaya
      yakın adımlar var, ama onlara ancak pahalı bir adımdan sonra
      varılıyor; bu sayı yalnız o yüzden ayrı duruyor.

    Medyan verilir, ortalama değil: dağılım sağa çok çarpık (tek bir hafta
    ortalamayı iki katına çıkarabiliyor).
    """
    uctan_uca: list[float] = []
    bir_ust: list[float] = []
    en_ucuz: list[float] = []
    for c in cetveller:
        b = c["basamaklar"]
        if len(b) < 2:
            continue
        adim = [(b[i + 1]["tl"] - b[i]["tl"])
                / (b[i + 1]["p_hedef"] - b[i]["p_hedef"])
                for i in range(len(b) - 1)
                if b[i + 1]["p_hedef"] > b[i]["p_hedef"]]
        if adim:
            en_ucuz.append(min(adim))
        if b[-1]["p_hedef"] > b[0]["p_hedef"]:
            uctan_uca.append((b[-1]["tl"] - b[0]["tl"])
                             / (b[-1]["p_hedef"] - b[0]["p_hedef"]))
        ref = [i for i, x in enumerate(b) if x["tl"] <= referans_tl]
        if ref and ref[-1] + 1 < len(b):
            i = ref[-1]
            if b[i + 1]["p_hedef"] > b[i]["p_hedef"]:
                bir_ust.append((b[i + 1]["tl"] - b[i]["tl"])
                               / (b[i + 1]["p_hedef"] - b[i]["p_hedef"]))
    lam = lambda_kestir(cetveller, referans_tl=referans_tl)
    out: dict[str, Any] = {"lambda": lam, "hafta": len(cetveller)}
    for ad, v in (("uctan_uca", uctan_uca), ("bir_ust", bir_ust),
                  ("en_ucuz_adim", en_ucuz)):
        med = _medyan(v)
        out[ad] = {"n": len(v), "medyan": med,
                   "kat": med / lam if lam else 0.0}
    return out


def _uygula(c: dict[str, Any], secici: Any) -> dict[str, Any] | None:
    """Bir kuralı bir haftanın cetveline uygular."""
    adimlar = [Adim(tl=b["tl"], kolon=b["kolon"], banko=b["banko"],
                    cift=b["cift"], uclu=b["uclu"], p_hedef=b["p_hedef"],
                    secimler=[])
               for b in c["basamaklar"]]
    sec = secici(adimlar)
    if sec is None:
        return None
    for b in c["basamaklar"]:
        if b["kolon"] == sec.kolon:
            return b
    return None


def _ozet(satirlar: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Bir kuralın karnesi — havuzlanmış ve hafta düzeyinde."""
    maliyet = sum(r["tl"] for r in satirlar)
    odul = sum(r["odul"] for r in satirlar)
    roi = [r["roi"] for r in satirlar]
    return {
        "hafta": len(satirlar),
        "maliyet": maliyet,
        "odul": odul,
        "roi": odul / maliyet if maliyet else 0.0,
        "ort_hafta_roi": sum(roi) / len(roi) if roi else 0.0,
        "ort_kolon": (sum(r["kolon"] for r in satirlar) / len(satirlar)
                      if satirlar else 0.0),
        "odul_alan_hafta": sum(1 for r in satirlar if r["odul"] > 0),
    }


def kural_kiyasi(cetveller: Sequence[dict[str, Any]],
                 butceler: Sequence[float] = (1000.0, 2000.0, 3500.0),
                 lambdalar: Sequence[float] = LAMBDA_BANDI,
                 tohum: int = 13) -> dict[str, Any]:
    """Kuralları **aynı cetvel** üzerinde puanlar ve eşleştirilmiş farkı verir.

    Her kural için havuzlanmış ROI ve hafta düzeyinde ortalama ROI döner;
    karşılaştırma `sabit(2000)` temeline karşı **eşleştirilmiş** yapılır
    (aynı hafta, iki kural) ve %95 aralık `karne.bootstrap_farki` ile
    hafta düzeyinde bootstrap'lanır.

    Fark istatistiği **ROI farkıdır**, TL farkı değil: nominal TL dört sezon
    boyunca 72 kata varan enflasyon taşır, oran taşımaz. Yine de haftalık ROI
    payı o haftanın nominal ödülünden gelir, yani havuzlanmış ortalama yeni
    haftalara daha ağır biner — `sezon` kırılımı bu yüzden ayrıca döner.
    """
    kurallar: dict[str, Any] = {}
    for b in butceler:
        kurallar[f"sabit-{int(b)}"] = lambda a, b=b: sabit_secim(a, b)
    for lam in lambdalar:
        kurallar[f"lambda-{int(lam)}"] = lambda a, lam=lam: marjinal_secim(a, lam)
    kurallar["en-buyuk"] = lambda a: (a[-1] if a else None)
    lam_ic = lambda_kestir(cetveller)
    kurallar[f"lambda-olculen-{int(lam_ic)}"] = \
        lambda a, lam=lam_ic: marjinal_secim(a, lam)

    # Secimler HAFTA ANAHTARIYLA tutulur: bir kural bir haftada secim
    # uretemezse listeler kayar ve esleştirilmiş fark sessizce yanlis
    # haftalari karsilastirmaya baslar.
    secimler: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    for ad, fn in kurallar.items():
        secimler[ad] = {(c["sezon"], c["hafta"]): r for c in cetveller
                        if (r := _uygula(c, fn)) is not None}

    # LOO: her haftanin lambda'si o hafta DISARIDA birakilarak kestirilir.
    loo: dict[tuple[str, int], dict[str, Any]] = {}
    for c in cetveller:
        anahtar = (c["sezon"], c["hafta"])
        lam = lambda_kestir(cetveller, disarida=anahtar)
        r = _uygula(c, lambda a, lam=lam: marjinal_secim(a, lam))
        if r is not None:
            loo[anahtar] = r
    secimler["lambda-LOO"] = loo

    # Ortak hafta kumesi: butun kurallar AYNI haftalarda puanlanir.
    ortak = set.intersection(*(set(s) for s in secimler.values()))
    secimler = {ad: {k: v for k, v in s.items() if k in ortak}
                for ad, s in secimler.items()}

    temel = "sabit-2000"
    ozet = {ad: _ozet(list(s.values())) for ad, s in secimler.items()}
    taban = secimler[temel]
    farklar: dict[str, Any] = {}
    for ad, satir in secimler.items():
        if ad == temel:
            continue
        fark = [satir[k]["roi"] - taban[k]["roi"] for k in sorted(ortak)]
        lo, hi = bootstrap_farki(fark, tohum=tohum, n=BOOTSTRAP)
        farklar[ad] = {
            "ort_roi_farki": sum(fark) / len(fark) if fark else 0.0,
            "alt": lo, "ust": hi, "kesiyor": lo <= 0.0 <= hi,
            "hafta": len(fark),
        }

    en_ust_kolon = {(c["sezon"], c["hafta"]): c["basamaklar"][-1]["kolon"]
                    for c in cetveller if c["basamaklar"]}
    en_ust = {ad: sum(1 for k, r in s.items()
                      if r["kolon"] == en_ust_kolon.get(k))
              for ad, s in secimler.items()}
    return {
        "hafta": len(ortak),
        "temel": temel,
        "lambda_olculen": lam_ic,
        "ozet": ozet,
        "fark": farklar,
        "tavan_dayanma": en_ust,
        "secim_dagilimi": {ad: sorted({r["kolon"] for r in s.values()})
                           for ad, s in secimler.items()},
    }


def _spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Sıra korelasyonu — bağlar ortalama sırayla."""
    def sira(v: Sequence[float]) -> list[float]:
        s = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                j += 1
            ort = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[s[k]] = ort
            i = j + 1
        return r

    n = len(x)
    if n < 3:
        return 0.0
    rx, ry = sira(x), sira(y)
    mx, my = sum(rx) / n, sum(ry) / n
    ust = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    alt = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return ust / alt if alt else 0.0


def isaret_sinavi(cetveller: Sequence[dict[str, Any]],
                  referans_tl: float = 2000.0,
                  tohum: int = 13,
                  n: int = BOOTSTRAP) -> dict[str, Any]:
    """**Değişken bütçenin ön şartı:** hafta öncesi bir işaret, o haftanın
    gerçekleşen ROI'sini bilebiliyor mu?

    Değişken bütçe ancak "iyi hafta"yı kupon kapanmadan tanıyabiliyorsak
    sabitini yener. Sınav bunu doğrudan sorar: referans basamağın **kupon
    öncesi** `P(hedef)`'i ile o haftanın **gerçekleşen** ROI'si arasındaki
    Spearman korelasyonu, hafta düzeyinde bootstrap aralığıyla.

    Aralık sıfırı kesiyorsa işaret yok demektir ve değişken bütçenin
    dayanacağı zemin de yok demektir — kuralların kıyası o durumda yalnızca
    *ne kadar* harcandığını ölçer, *hangi haftaya* harcandığını değil.
    """
    p: list[float] = []
    roi: list[float] = []
    for c in cetveller:
        ref = [b for b in c["basamaklar"] if b["tl"] <= referans_tl]
        if not ref:
            continue
        p.append(ref[-1]["p_hedef"])
        roi.append(ref[-1]["roi"])
    if len(p) < 3:
        return {"n": len(p), "rho": 0.0, "alt": 0.0, "ust": 0.0,
                "kesiyor": True}
    rho = _spearman(p, roi)
    rnd = random.Random(tohum)
    m = len(p)
    dag = []
    for _ in range(n):
        idx = [rnd.randrange(m) for _ in range(m)]
        dag.append(_spearman([p[i] for i in idx], [roi[i] for i in idx]))
    dag.sort()
    lo, hi = dag[int(0.025 * n)], dag[int(0.975 * n)]
    return {"n": m, "rho": rho, "alt": lo, "ust": hi,
            "kesiyor": lo <= 0.0 <= hi}


def _yaz_cephe(adimlar: Sequence[Adim]) -> None:  # pragma: no cover - elle
    """Cepheyi insan gözü için basar."""
    print(f"\n{'TL':>9}{'kolon':>7}  {'sekil':<10}{'P(hedef)':>10}"
          f"{'marj TL/puan':>14}")
    onceki: Adim | None = None
    for a in adimlar:
        marj = ""
        if onceki and a.p_hedef > onceki.p_hedef:
            marj = f"{(a.tl - onceki.tl) / (a.p_hedef - onceki.p_hedef) / 100:,.0f}"
        print(f"{a.tl:>9,.0f}{a.kolon:>7}  {a.sekil:<10}{a.p_hedef:>10.4f}"
              f"{marj:>14}")
        onceki = a


def _main(argv: list[str] | None = None) -> int:  # pragma: no cover - elle
    """CLI — cephe, tek hafta cetveli, kural kıyası."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cephe", action="store_true", help="tek haftanin cephesi")
    ap.add_argument("--cetvel", action="store_true", help="tek haftanin cetveli")
    ap.add_argument("--kiyas", action="store_true", help="kural kiyasi (YAVAS)")
    ap.add_argument("--para", metavar="SEZON:HAFTA", default=None,
                    help="canli haftada E[TL] cephesi, or. 2026_27:3")
    ap.add_argument("--hafta", type=int, default=None,
                    help="kesitteki hafta sayisi (varsayilan: hepsi)")
    ap.add_argument("--indis", type=int, default=0, help="tek hafta indisi")
    ap.add_argument("--garanti", type=int, default=VARSAYILAN_GARANTI,
                    help="cephe icin; cetvel/kiyas yalniz 14'te kosar")
    ap.add_argument("--tavan", type=float, default=CEPHE_TAVANI)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.para:
        sezon, _, hf = a.para.partition(":")
        satir = para_cephesi(sezon, int(hf), garanti=a.garanti,
                             en_cok_tl=a.tavan)
        if not satir:
            print("ikramiye tablosu olmayan hafta — E[TL] kurulamiyor")
            return 1
        if a.json:
            print(json.dumps(satir, ensure_ascii=False, indent=1))
            return 0
        print(f"\n{sezon} hafta {hf} · {a.garanti}-garanti")
        print(f"\n{'TL':>9}{'kolon':>7}{'P(hedef)':>10}{'E[TL]':>12}"
              f"{'E/maliyet':>11}{'E-maliyet':>12}")
        for s in satir:
            print(f"{s['tl']:>9,.0f}{s['kolon']:>7}{s['p_hedef']:>10.4f}"
                  f"{s['beklenen_tl']:>12,.0f}{s['e_bolu_maliyet']:>11.3f}"
                  f"{s['net']:>12,.0f}")
        return 0

    if a.cephe or a.cetvel:
        h = kupon_kesiti()[a.indis]
        print(f"{h['sezon']} hafta {h['hafta']} · {a.garanti}-garanti")
        if a.cephe:
            _yaz_cephe(cephe(h["probs"], garanti=a.garanti, en_cok_tl=a.tavan))
            return 0
        c = hafta_cetveli(h, garanti=a.garanti, en_cok_tl=a.tavan)
        if a.json:
            print(json.dumps(c, ensure_ascii=False, indent=1))
            return 0
        print(f"\n{'TL':>9}{'kolon':>7}{'P(hedef)':>10}{'kacak':>7}"
              f"{'odul':>12}{'ROI':>8}")
        for b in c["basamaklar"]:
            print(f"{b['tl']:>9,.0f}{b['kolon']:>7}{b['p_hedef']:>10.4f}"
                  f"{b['kacak']:>7}{b['odul']:>12,.0f}{b['roi']:>8.2f}")
        return 0

    cet = cetvel(hafta_siniri=a.hafta, en_cok_tl=a.tavan)
    k = kural_kiyasi(cet)
    isaret = isaret_sinavi(cet)
    if a.json:
        print(json.dumps({"kiyas": k, "isaret": isaret},
                         ensure_ascii=False, indent=1))
        return 0
    print(f"\nHAFTANIN HAKKI — {k['hafta']} hafta · 14-garanti · "
          f"tavan {a.tavan:,.0f} TL")
    print(f"olculen lambda: {k['lambda_olculen']:,.0f} TL / birim P(hedef)")
    print(f"\n{'kolon':>6}{'TL':>9}{'hafta':>7}{'tutan':>7}"
          f"{'ort odul':>11}{'ROI':>8}{'odul|tuttu':>12}{'/kolon':>9}")
    for s in basamak_karnesi(cet):
        print(f"{s['kolon']:>6}{s['tl']:>9,.0f}{s['hafta']:>7}{s['tutan']:>7}"
              f"{s['ort_odul']:>11,.0f}{s['roi']:>8.3f}"
              f"{s['odul_tuttu']:>12,.0f}{s['odul_tuttu_kolon']:>9.1f}")
    print(f"\n{'kural':<22}{'kolon/hafta':>12}{'maliyet':>12}{'odul':>12}"
          f"{'ROI':>8}{'hafta ROI':>11}")
    for ad, o in k["ozet"].items():
        print(f"{ad:<22}{o['ort_kolon']:>12,.0f}{o['maliyet']:>12,.0f}"
              f"{o['odul']:>12,.0f}{o['roi']:>8.3f}{o['ort_hafta_roi']:>11.3f}")
    print(f"\n{'kural':<22}{'ROI farki':>11}{'%95 alt':>11}{'%95 ust':>11}"
          f"{'sifiri kesiyor':>16}")
    for ad, f in k["fark"].items():
        print(f"{ad:<22}{f['ort_roi_farki']:>+11.3f}{f['alt']:>+11.3f}"
              f"{f['ust']:>+11.3f}{'EVET' if f['kesiyor'] else 'HAYIR':>16}")
    f = fiyat_karnesi(cet)
    print(f"\nFIYAT — bir birim P(hedef) {f['lambda']:,.0f} TL ediyor, "
          f"merdiven kaca satiyor:")
    print(f"{'':2}{'olcu':<22}{'n':>5}{'medyan TL/birim':>18}{'lambda kati':>13}")
    for ad, etiket in (("uctan_uca", "uctan uca ortalama"),
                       ("bir_ust", "oynananin bir ustu"),
                       ("en_ucuz_adim", "haftanin en ucuz adimi")):
        s = f[ad]
        print(f"{'':2}{etiket:<22}{s['n']:>5}{s['medyan']:>18,.0f}"
              f"{s['kat']:>12.1f}x")
    print(f"\nisaret sinavi: rho = {isaret['rho']:+.3f} "
          f"[{isaret['alt']:+.3f}, {isaret['ust']:+.3f}] "
          f"(n={isaret['n']}) — {'ISARET YOK' if isaret['kesiyor'] else 'ISARET VAR'}")
    print(f"tavan dayanma: {k['tavan_dayanma']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main())
