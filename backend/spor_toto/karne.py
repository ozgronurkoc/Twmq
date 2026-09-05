"""Para karnesi — kuponun **gerçek ikramiye tablolarına** karşı getirisi.

`secim` bir kuponu `P(k ≤ eşik)`'e göre kurar ve o sayı bir **olasılıktır**.
Bu modül bir adım ötesini sorar: *o kupon geçmiş haftalarda kaç lira
döndürürdü?* Ölçüm `data/sportoto_arsiv`'in resmî kademe tablolarına karşı
koşar — varsayılan ikramiye değil, **kayıt**.

─── Ne ölçülüyor: GARANTİ TABANI, gerçekleşen değil ──────────────────────

Elde kuponun kolon listesi **yoktur**: şekle biz karar veriyoruz, kolonları
satıcı üretiyor (`sistem` modül başlığı). Kolon listesi olmadan hangi
kolonun kaç tutturduğu bilinemez. Bilinen tek şey **garantinin kendisidir**:

    `k` maç seçim kümesinin dışında kalırsa en az bir kolon `G − k` tutturur

Bu modül tam olarak onu sayar: **bir** kolon, `G − k` kademesinde. Yani
üretilen sayı bir **alt sınırdır** — gerçekleşen getiri bundan küçük olamaz,
ama rahatlıkla büyük olabilir (aynı sistemin başka kolonları da alt
kademelerde kazanır ve bu hesap onları hiç saymaz).

─── Alt sınırın YANLILIĞI ölçüldü ve yönü bellidir ───────────────────────

**Bu taban iki farklı garanti seviyesini karşılaştırmak için kullanılamaz.**
Sebebi ölçüldü: arşivdeki 223 haftada `14 bilen ödülü / 13 bilen ödülü`
oranının medyanı **15,1**. Hiç kaçak olmayan bir haftada taban 14-garantiye
14. kademeyi, 13-garantiye 13. kademeyi yazar ve aradaki on beş kat farkın
**tamamı sınırın eseridir**: 288 kolonluk bir 13-garanti sistemi o hafta 14'ü
de büyük olasılıkla tutar, ama garanti bunu *söylemediği* için taban saymaz.

Dolayısıyla:

* **Aynı garanti içinde** karşılaştırma geçerlidir — yanlılık iki kolda da
  aynıdır ve eşleştirilmiş farkta büyük ölçüde götürür. Ama *tam* götürmez:
  yanlılığın büyüklüğü kaçağa bağlıdır ve aşağıdaki ölçüm onu gösteriyor.
* **Garantiler arasında** geçerli DEĞİLDİR. O karşılaştırma ancak gerçek
  kolon listeleriyle yapılır ve bu modül onu yapmaz; `gecerli_kiyas()`
  çağrıldığında bunu açıkça söyler.

─── Sınırın BÜYÜKLÜĞÜ de ölçüldü: 2,39 kat (`taban_gevsekligi`) ──────────

14-garantide kolonlar depoda üretilebiliyor (`engines.run_auto`), yani
tabanın ne kadar alt olduğu fişe gerek kalmadan sayılabildi. 114 hafta,
2.000 TL: taban 19.354 TL (geri dönüş %10,1), gerçek kolon dağılımı
46.301 TL (%24,2) — **2,39 kat**.

Ve yanlılık düzgün değil, **eğik**: 12+ tutturan ortalama kolon sayısı
kaçak 0'da 26,8, kaçak 1'de 10,2, kaçak 2'de 1,3, taban her durumda 1.
Yani sınır en çok **iyi giden** haftaları eksik sayar — eşleştirilmiş
karşılaştırmalarda muhafazakâr değil taraflıdır.

Bunun kapatmadığı şey de ölçüldü: %24,2 hâlâ 1'in altında. Taban
düzeltilince bile kupon para kaybediyor, yani geri dönüş açığı bir ölçüm
kusuru değildir.

    python -m spor_toto.karne --taban --garanti 14 --butce 2000

─── Enflasyon: sezonlar toplanamaz ───────────────────────────────────────

Kademe ödülleri nominal TL'dir ve dört sezonda **72 kat** büyümüştür
(12 bilen medyanı: 2022/23 ₺62 → 2026/27 ₺4.486). Maliyet ise **bugünün**
fiyatından hesaplanır. İkisini bölmek sezonlar arasında anlamlı değildir:
ölçüldüğünde 2022/23 sezonu haftaların %15'i olduğu hâlde toplam ödülün
**%1'ini** taşıyor — yani havuzlanmış bir ortalama, eski haftaları sessizce
sıfıra yakın ağırlıkla sayar.

Bu yüzden `karne()` her zaman **sezon kırılımı** döndürür ve havuzlanmış
ortalamayı `uyari` alanıyla birlikte verir. Eşleştirilmiş farklarda sorun
yoktur: aynı haftanın aynı TL'si iki kolda da kullanılır, enflasyon götürür.

    python -m spor_toto.karne                    # 13G, butce egrisi
    python -m spor_toto.karne --garanti 14 --butce 2000
    python -m spor_toto.karne --taban --garanti 14 --butce 2000   # E1
    python -m spor_toto.karne --hedef --garanti 14 --butce 2000   # E2
    python -m spor_toto.karne --omurga BFE --garanti 14 --butce 2000  # E3
    python -m spor_toto.karne --egri --garanti 14                     # butce egrisi
"""
from __future__ import annotations

import argparse
import json
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .core import SEMBOLLER
from .getiri import KOLON_BEDELI
from .havuz import arsiv_haftalari
from .ortak import wilson
from .secim import sistem_secimi
from .sistem import HEDEF_KADEME, VARSAYILAN_GARANTI

#: Ölçülen bütçe basamakları (TL). `kademe_analizi.BUTCELER` kolon
#: cinsindendir ve bu modül TL konuşur (`sistem` tablosu TL taşıyor).
BUTCELER: tuple[float, ...] = (500.0, 1000.0, 1500.0, 2000.0, 3000.0, 5000.0)

#: Bootstrap yeniden örnekleme adedi — `evaluate` ile aynı büyüklük sınıfı.
BOOTSTRAP = 20_000

#: §3.64'ün lig kırılımında bir ligin kendi satırını hak etmesi için gereken
#: en az maç. Wilson aralığı bunun altında okunacak kadar dar olmuyor.
EN_AZ_LIG_MAC = 100

#: §3.64'ün **önceden yazılmış durma kuralı** — banko `q`'suna T1 düzeltmesi
#: konmadan önce gereken banko-rejimi maç sayısı.
#:
#: Etki dört sezon boyunca gerçekti ve iki bağımsız örneklem doğruladı
#: (korpus T1: +%5,7 · +%8,1 · +%7,0 · +%6,6; kupon T1: +%9,0 · +%10,5 ·
#: +%5,4). Ama gözlenebilen **son** sezonda yok: 2025/26'da +%0,3, `n=150`
#: ve Wilson aralığı söylenen `p`'yi içeriyor. İki okuma bugünkü veriyle
#: ayrılamıyor — piyasa keskinleşti, ya da bir sezon gürültü.
#:
#: Kural: düzeltme ancak **2025/26 + 2026/27 birlikte** banko rejiminde bu
#: eşiğe ulaşıp havuzlanmış sapmanın Wilson %95 aralığı `p`'yi **tamamıyla**
#: dışarıda bıraktığında uygulanır. 2022–2024 üzerinde kalibre edilmiş bir
#: düzeltme, ölçülebilen son sezonda etkisi olmayan bir şeyi geçmişe
#: uydurmak olurdu (`esik_taramasi`nın bir kez yaptığı hata).
#:
#: Bekçisi `test_karne.py::test_banko_duzeltmesi_UYGULANMIYOR_kurali_yazili`:
#: düzeltmeyi koymak isteyen önce o testi değiştirmek, yani kararı görünür
#: kılmak zorunda.
T1_DUZELTME_ESIGI = 300

#: Bugün banko `q`'suna uygulanan düzeltme. §3.64'ün durma kuralı
#: karşılanmadı, o yüzden **yok** ve sıfır olmasının gerekçesi yukarıdadır.
BANKO_Q_DUZELTMESI = 0.0

#: Kuyruk sınavı: en çok kazandıran kaç hafta çıkarılınca hâlâ ayakta mı
#: (`docs/KADEME_OLASILIKLARI.md` §5.3(c) kuralı).
KUYRUK_HAFTA = 5


class KarneHatasi(RuntimeError):
    """Ölçüm kurulamadı — kesit boş ya da kaynak eksik."""


def _odul(tablo: dict[int, dict[str, Any]], kademe: int) -> float:
    """`kademe`de **bir** kolonun kazandığı TL; kademe yoksa sıfır."""
    if kademe < HEDEF_KADEME:
        return 0.0
    satir = tablo.get(kademe)
    if not satir or satir.get("prize") is None:
        return 0.0
    return float(satir["prize"])


def hafta_karnesi(probs_listesi: list[dict[str, float]],
                  gercek: Sequence[str],
                  tablo: dict[int, dict[str, Any]],
                  butce_tl: float,
                  garanti: int = VARSAYILAN_GARANTI) -> dict[str, Any] | None:
    """Tek haftanın karnesi. Bütçeye şekil sığmıyorsa `None`.

    `kademe` alanı **garantinin verdiği taban**dır, gerçekleşen en iyi kolon
    değil — modül başlığındaki gerekçe.
    """
    plan = sistem_secimi(probs_listesi, butce_tl, garanti=garanti)
    if plan is None:
        return None
    kacak = sum(1 for sec, c in zip(plan.secimler, gercek) if c not in sec)
    kademe = garanti - kacak
    maliyet = plan.bedel * KOLON_BEDELI
    odul = _odul(tablo, kademe)
    return {
        "kacak": kacak, "kademe": kademe, "kolon": plan.bedel,
        "maliyet": maliyet, "odul": odul, "net": odul - maliyet,
        "roi": odul / maliyet if maliyet else 0.0,
        "p_hedef": plan.p_hedef,
        "banko": plan.banko, "cift": plan.cift, "uclu": plan.uclu,
    }


def _medyan(v: Sequence[float]) -> float:
    s = sorted(v)
    n = len(s)
    if not n:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _ortalama(v: Sequence[float]) -> float:
    return sum(v) / len(v) if v else 0.0


def bootstrap_farki(fark: Sequence[float], tohum: int = 13,
                    n: int = BOOTSTRAP) -> tuple[float, float]:
    """Hafta düzeyinde eşleştirilmiş bootstrap %95 aralığı.

    Hafta düzeyinde örneklenir çünkü aynı haftanın maçları bağımsız değildir
    — `evaluate`in kuralıyla aynı gerekçe.
    """
    if not fark:
        return (0.0, 0.0)
    dag = _bootstrap_dagilimi(fark, tohum, n)
    return dag[int(0.025 * n)], dag[int(0.975 * n)]


def _bootstrap_dagilimi(fark: Sequence[float], tohum: int,
                        n: int) -> list[float]:
    """Eşleştirilmiş bootstrap ortalamalarının **sıralı** dağılımı.

    `bootstrap_farki` ile `bootstrap_p_degeri` aynı çekilişi okumak
    zorundadır; ayrı ayrı örneklenirse aralık ile p-değeri birbirini
    tutmayabilir ve hangisinin doğru olduğu belli olmaz.
    """
    rnd = random.Random(tohum)
    m = len(fark)
    return sorted(sum(fark[rnd.randrange(m)] for _ in range(m)) / m
                  for _ in range(n))


def bootstrap_p_degeri(fark: Sequence[float], tohum: int = 13,
                       n: int = BOOTSTRAP, buyuk_iyi: bool = True) -> float:
    """Tek yönlü bootstrap p-değeri — `evaluate.bootstrap_farki` ile aynı kalıp.

    `buyuk_iyi=True` ise aday, farkın **pozitif** olmasıyla kazanır ve
    p-değeri dağılımın sıfırın yanlış tarafında kalan payıdır. `+1 / (n+1)`
    düzeltmesi sıfır p-değerini engeller (`evaluate.py:670` ile aynı).

    Bu değer **yalnız** çoklu karşılaştırma düzeltmesi (`evaluate.holm`)
    için vardır; tekil karar hâlâ güven aralığından verilir.
    """
    if not fark:
        return 1.0
    dag = _bootstrap_dagilimi(fark, tohum, n)
    yanlis = (sum(1 for f in dag if f <= 0.0) if buyuk_iyi
              else sum(1 for f in dag if f >= 0.0))
    return (yanlis + 1) / (n + 1)


def _sezon_kirilimi(satirlar: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for s in sorted({r["sezon"] for r in satirlar}):
        alt = [r for r in satirlar if r["sezon"] == s]
        roi = [r["roi"] for r in alt]
        out.append({
            "sezon": s, "hafta": len(alt),
            "medyan_roi": _medyan(roi), "ortalama_roi": _ortalama(roi),
            "toplam_odul": sum(r["odul"] for r in alt),
            "odul_alan_hafta": sum(1 for r in alt if r["odul"] > 0),
        })
    return out


def karne(satirlar: list[dict[str, Any]]) -> dict[str, Any]:
    """Hafta satırlarını tek bir karneye toplar — **sezon kırılımıyla**.

    Havuzlanmış ortalama da döner ama `uyari` alanı onu nasıl okumak
    gerektiğini söyler: nominal TL sezonlar arasında toplanamaz.
    """
    if not satirlar:
        raise KarneHatasi("kesit bos")
    roi = [r["roi"] for r in satirlar]
    sirali = sorted(satirlar, key=lambda r: -r["odul"])
    kalan = sirali[KUYRUK_HAFTA:]
    return {
        "hafta": len(satirlar),
        "medyan_roi": _medyan(roi),
        "ortalama_roi": _ortalama(roi),
        "odul_alan_hafta": sum(1 for r in satirlar if r["odul"] > 0),
        "toplam_odul": sum(r["odul"] for r in satirlar),
        "toplam_maliyet": sum(r["maliyet"] for r in satirlar),
        "ort_kolon": _ortalama([r["kolon"] for r in satirlar]),
        "en_iyi_bes_hafta_payi": (
            sum(r["odul"] for r in sirali[:KUYRUK_HAFTA])
            / sum(r["odul"] for r in satirlar)
            if sum(r["odul"] for r in satirlar) else 0.0),
        "kuyruksuz_ortalama_roi": _ortalama([r["roi"] for r in kalan]),
        "sezonlar": _sezon_kirilimi(satirlar),
        "uyari": (
            "ODUL nominal TL'dir ve sezonlar arasinda 72 kata varan enflasyon "
            "vardir; MALIYET bugunun fiyatindandir. Havuzlanmis ortalama bu "
            "yuzden eski haftalari sifira yakin agirlikla sayar — sezon "
            "kirilimina bakin. Ayrica butun oduller GARANTI TABANIDIR: bir "
            "kolon, G-k kademesinde. Gerceklesen getiri bundan buyuktur."),
    }


def gecerli_kiyas(garanti_a: int, garanti_b: int) -> bool:
    """İki garanti seviyesi bu tabanla karşılaştırılabilir mi — **hayır**.

    Aynı seviye kendisiyle karşılaştırılabilir (yanlılık iki kolda da
    aynıdır); farklı seviyeler karşılaştırılamaz, çünkü taban yüksek
    garantiyi 15,1 kat kayırır (modül başlığı)::

        >>> gecerli_kiyas(13, 13)
        True
        >>> gecerli_kiyas(13, 14)
        False
    """
    return garanti_a == garanti_b


def ikramiye_tablolari(dizin: Any = None
                       ) -> dict[tuple[str, int], dict[int, dict[str, Any]]]:
    """Resmî arşiv → `(sezon, hafta)` → kademe tablosu. **Tek kaynak.**

    `scripts/kademe_analizi.py` aynı gövdeyi kendi içinde taşıyordu; ölçüm
    hattı ikiye ayrılmasın diye buraya alındı ve o script buradan okuyor.
    """
    out: dict[tuple[str, int], dict[int, dict[str, Any]]] = {}
    for h in arsiv_haftalari(dizin):
        p = h.get("payout")
        if not p:
            continue
        t = {x["correct"]: x for x in p.get("tiers", [])}
        if 15 in t:
            out[(h["season_key"], h["week"])] = t
    return out


def anormal_hafta_anahtarlari(dizin: Any = None) -> set[tuple[str, int]]:
    """12. kademe kazananı medyanın onda birinden az olan haftalar.

    `docs/KADEME_OLASILIKLARI.md` §8: 223 haftanın 32'si. *"Elenmeden alınan
    kademe ortalaması tek kolonun beklenen değerini 4,99 TL gösteriyor"* —
    yani kademe ortalaması alan her hesap bunlarla kirlenir. `karne` CLI'sı
    bu yüzden iki kolonu da basar; eleme sessizce yapılmaz.
    """
    from .havuz import anormal_haftalar

    return anormal_haftalar(dizin)


def kupon_kesiti(dizin: Any = None,
                 kaynaklar: Sequence[str] | None = None,
                 yontem: str | None = None,
                 ) -> list[dict[str, Any]]:
    """Ölçümün kesiti: **on beş maçında da oran olan VE ikramiyesi ilan
    edilmiş** haftalar.

    İki arşivin kesişimidir ve projenin bugüne kadar birleştirmediği yer
    tam olarak burasıdır: `data/odds/*.csv` kuponun maçlarını ve piyasa
    oranını, `data/sportoto_arsiv/*.json` o haftanın **gerçek** kademe
    tablosunu taşıyor.

    `kaynaklar` verilirse kesit o fiyattan kurulur (`odds.match_1x2`);
    `yontem` marj arındırmasını seçer (varsayılan `odds.ARINDIRMA_VARSAYILAN`,
    bugün `shin`). İkincisi §3.64 için eklendi: aynı maçlar üç arındırmayla
    kurulup favori sembolün kalibrasyonu kıyaslanabilsin diye.
    **On beş maçın on beşinde de fiyat şartı korunur**, yani BFE gibi
    kısmi kapsamalı bir kaynakta kesit kendiliğinden daralır — daraldığı
    yer de bilgidir ve `omurga_kiyasi` onu sayar.
    """
    from .core import SEMBOLLER
    from .odds import ARINDIRMA_VARSAYILAN, KAYNAK_SIRASI, load_odds, match_1x2

    kay = KAYNAK_SIRASI if kaynaklar is None else tuple(kaynaklar)
    yon = ARINDIRMA_VARSAYILAN if yontem is None else yontem
    ars = ikramiye_tablolari(dizin)
    out: list[dict[str, Any]] = []
    for sezon in sorted({s for s, _ in ars}, reverse=True):
        try:
            satirlar = load_odds(sezon=sezon)
        except OSError:
            continue
        haftalik: dict[int, list[tuple[dict[str, Any], str, str]]] = {}
        for r in satirlar:
            b = match_1x2(r, yontem=yon, kaynaklar=kay)
            if b and r.get("code") in SEMBOLLER:
                lig = (r.get("source") or {}).get("league") or "bilinmiyor"
                haftalik.setdefault(r["week"], []).append((b, r["code"], lig))
        for w, lst in sorted(haftalik.items()):
            if len(lst) != 15 or (sezon, w) not in ars:
                continue
            out.append({
                "sezon": sezon, "hafta": w,
                "probs": [b["probs"] for b, _, _ in lst],
                "gercek": [c for _, c, _ in lst],
                # Lig, §3.64'un ayirici kesiti: kuponun yarisi Super Lig'den
                # gelir ve korpusun lig agirligi bambaska.
                "ligler": [g for _, _, g in lst],
                "tablo": ars[(sezon, w)],
            })
    return out


def taban_gevsekligi(butce_tl: float = 2000.0,
                     garanti: int = 14,
                     hafta_siniri: int | None = None) -> dict[str, Any]:
    """Tabanın gerçek kolon dağılımına göre ne kadar gevşek olduğunu ölçer.

    Modül başlığı tabanın bir **alt sınır** olduğunu söylüyor ama ne kadar
    alt olduğunu söylemiyordu — bu fonksiyon onu sayıya çevirir. Yalnızca
    14-garantide koşabilir, çünkü kolonları gerçekten üretebilen tek yer
    `engines.run_auto` ve `core.py` yarıçap 1'e kilitli. 13-garantinin
    kolon listesi satıcıdadır ve burada yoktur.

    **İki sayı döner, çünkü iki farklı ürün var ve ikisi aynı değil.**
    Motorun ürettiği kaplama, satıcının aynı şekle sattığı kaplamadan
    **daha gevşektir**: ölçüldü, 3 çifte + 5 üçlü şekli için motor
    **216** kolon üretiyor, tablo aynı şekli **168** kolonla satıyor
    (%28,6 fazla). İkisi de 14-garanti veriyor, yani satıcının kodu
    ölçülebilir biçimde daha sıkı.

    * ``kat_ham`` — motorun kendi kolonları, olduğu gibi. Motorun ürününü
      tarif eder, oynanan ürünü değil.
    * ``kat`` — kolon sayısı satıcının şekline (`plan.bedel`) indirgenmiş.
      **Varsayım:** satıcının daha az kolonu, motorunkiyle *aynı biçimde*
      dağılıyor. Bu varsayım ölçülmedi ve ölçülemez (kolon listesi elde
      yok). Yön muhtemelen ihtiyatlı: daha sıkı bir kod aynı bütçeyi daha
      iyi yayar, yani indirgenmiş sayı gerçeği **eksik** sayıyor olabilir.

    Yayımlanan sayı `kat`tır — ikisinden küçüğü ve oynanan ürüne yakın
    olanı. `kat_ham` yanında durur ki indirgemenin bedeli görünsün.
    """
    from .secim import sistem_secimi

    kesit = kupon_kesiti()
    if hafta_siniri:
        kesit = kesit[:hafta_siniri]
    maliyet = taban_odul = gercek_toplam = ham_toplam = 0.0
    hafta = 0
    motor_kolon = tablo_kolon = 0
    kacak_kolon: dict[int, list[float]] = {}
    haftalar: list[dict[str, Any]] = []
    sekiller: dict[tuple[int, int, int], int] = {}
    for h in kesit:
        plan = sistem_secimi(h["probs"], butce_tl, garanti=garanti)
        if plan is None:
            continue
        ham = gercek_kolon_dagilimi(plan.secimler, h["gercek"])
        if ham is None:
            continue
        motor_kolon += round(sum(ham.values()))
        tablo_kolon += plan.bedel
        olcek = plan.bedel / sum(ham.values())
        dagilim = {k: v * olcek for k, v in ham.items()}
        kacak = sum(1 for s, c in zip(plan.secimler, h["gercek"])
                    if c not in s)
        taban = 0.0
        satir = h["tablo"].get(garanti - kacak)
        if kacak <= garanti - HEDEF_KADEME and satir \
                and satir.get("prize") is not None:
            taban = float(satir["prize"])
        gercek = gercek_odul(dagilim, h["tablo"]) or 0.0
        maliyet += plan.bedel * KOLON_BEDELI
        taban_odul += taban
        gercek_toplam += gercek
        ham_toplam += gercek_odul(ham, h["tablo"]) or 0.0
        kacak_kolon.setdefault(kacak, []).append(
            sum(v for k, v in dagilim.items() if k >= HEDEF_KADEME))
        sekiller[(plan.banko, plan.cift, plan.uclu)] = \
            sekiller.get((plan.banko, plan.cift, plan.uclu), 0) + 1
        haftalar.append({
            "sezon": h["sezon"], "hafta_no": h["hafta"],
            "kacak": kacak, "kolon": plan.bedel,
            "maliyet": plan.bedel * KOLON_BEDELI,
            "gercek_odul": gercek, "taban_odul": taban,
            "p_hedef": plan.p_hedef,
            "sekil": (plan.banko, plan.cift, plan.uclu),
        })
        hafta += 1
    if not hafta or taban_odul <= 0.0:
        return {"hafta": hafta, "maliyet": maliyet, "taban_odul": taban_odul,
                "gercek_odul": gercek_toplam, "kat": None, "kat_ham": None,
                "kacak_kolon": {}, "kacak_hafta": {}, "haftalar": haftalar,
                "sekil": None, "ort_p_hedef": None}
    return {
        "hafta": hafta,
        "maliyet": maliyet,
        "taban_odul": taban_odul,
        "gercek_odul": gercek_toplam,
        "ham_odul": ham_toplam,
        "taban_roi": taban_odul / maliyet,
        "gercek_roi": gercek_toplam / maliyet,
        "kat": gercek_toplam / taban_odul,
        "kat_ham": ham_toplam / taban_odul,
        "motor_kolon": motor_kolon,
        "tablo_kolon": tablo_kolon,
        "kaplama_farki": motor_kolon / tablo_kolon if tablo_kolon else None,
        "kacak_kolon": {k: sum(v) / len(v)
                        for k, v in sorted(kacak_kolon.items())},
        # Kaçak SIKLIĞI — `kacak_kolon` yalnız ortalamayı tutuyordu ve
        # `len(v)` atılıyordu. Ödeyen tek olay `k = 0` olduğu için
        # (§3.57: kaçak 0'da medyan 1,34×, kaçak 1'de 0,28×) dağılımın
        # kendisi ortalamadan daha çok şey söylüyor.
        "kacak_hafta": {k: len(v) for k, v in sorted(kacak_kolon.items())},
        "sekil": max(sekiller.items(), key=lambda x: x[1])[0]
        if sekiller else None,
        "ort_p_hedef": sum(w["p_hedef"] for w in haftalar) / len(haftalar)
        if haftalar else None,
        "haftalar": haftalar,
    }


def butce_egrisi(garanti: int = 14,
                 butceler: Sequence[float] = BUTCELER,
                 referans: float = 2000.0,
                 hafta_siniri: int | None = None) -> dict[str, Any]:
    """Bütçe eğrisi — **gerçek kolon ödülüyle** ve ödeyen olayın sıklığıyla.

    ─── Niçin bu kol, ve niçin şimdiye kadar koşulmadı ───────────────────

    §3.57 kendi sonucunu genelleyip şunu yazdı: *"şekli **bütçe** belirliyor,
    hedef değil; şeklin kendisiyle oynayan kollar (bütçe eğrisi) hedef
    kademesiyle oynayan koldan **yapısal olarak daha güçlü**."* Buna rağmen
    E1–E4'ün dördü de tek bir sabit 2.000 TL'de koştu.

    Var olan bütçe eğrisi (`_main`in varsayılan yolu) **garanti tabanına**
    dayanıyor ve taban 2,39 kat gevşek **ve eğik**: 12+ tutturan kolon
    sayısı kaçak 0'da 26,8, kaçak 2'de 1,3 iken taban her durumda 1 sayıyor
    (§3.56). Yani mevcut eğri en çok *iyi giden* haftaları eksik sayıyor —
    bütçeleri kıyaslamak için tam olarak yanlış cetvel. Bu fonksiyon aynı
    eğriyi `taban_gevsekligi`nin **gerçek kolon** hattı üzerinde kurar.

    ─── Ölçünün kendisi: kaçaksız hafta, lira başına ─────────────────────

    Ödeyen tek olay `k = 0`'dır (§3.57: kaçak 0'da medyan geri dönüş
    **1,34×**, kaçak 1'de 0,28×, kaçak 2'de 0,12×). Bütçe sorusu bu yüzden
    *"daha çok kapsama alınır mı"* değil, **"aynı parayla daha çok kaçaksız
    hafta alınır mı"**dır:

        kacaksiz_bin_tl = 1.000 × (kaçaksız hafta) / (toplam maliyet)

    Aritmetik iki yönü de mümkün kılıyor ve ölçüm gerekmesinin sebebi bu:
    kaçak eklemek bedeli **çarpımsal** büyütür (2^çifte·3^üçlü) ama
    `P(k=0) = Π(1−qᵢ)` çarpanları 1'e yaklaştıkça kazanç yavaşlar. Yani
    lira başına tutturma bütçeyle **azalıyor** olabilir — öyleyse aynı
    yıllık parayı çok haftaya yaymak, az haftaya yığmaktan iyidir.

    ─── İki sayı, ve niçin ikisi de veriliyor ────────────────────────────

    ``kacaksiz_bin_tl``
        Toplulaştırılmış: `1.000 · n₀ / Σmaliyet`. Manşet sayı budur.
    ``kacaksiz_bin_tl_hafta_ort``
        Hafta düzeyinde ortalama (`1.000·[k=0]/maliyetₕ`'nin ortalaması).
        Şekil haftadan haftaya değişebildiği için ikisi birebir aynı
        değildir; **eşleştirilmiş bootstrap yalnız bunun üzerinde
        kurulabilir**, çünkü aralık hafta düzeyinde örneklemeyi ister.

    `fark` alanı her bütçenin `referans`a göre eşleştirilmiş farkıdır —
    yalnız **iki bütçede de ölçülebilen** haftalar üzerinde.

    ─── Durma kuralı (ölçümden ÖNCE yazıldı) ─────────────────────────────

    Varsayılan bütçe ancak bir basamağın `fark` aralığının **tamamı sıfırın
    üstünde** kalırsa değişir. Aralık sıfırı keserse eğri yayımlanır ve
    varsayılan 2.000 TL'de kalır.

    Yalnız 14-garantide koşar — `taban_gevsekligi` ile aynı gerekçe: kolon
    listesi 13-garantide satıcıdadır. Sonuç 13G'ye **taşınmaz** (§3.51'in
    15,1 katı).

        cd backend && python -m spor_toto.karne --egri --garanti 14
    """
    kollar: list[dict[str, Any]] = []
    hafta_kaydi: dict[float, dict[tuple[str, int], dict[str, Any]]] = {}
    for tl in butceler:
        t = taban_gevsekligi(tl, garanti, hafta_siniri)
        if not t["hafta"]:
            continue
        hs: list[dict[str, Any]] = t["haftalar"]
        hafta_kaydi[tl] = {(w["sezon"], w["hafta_no"]): w for w in hs}
        kacaksiz = sum(1 for w in hs if w["kacak"] == 0)
        kollar.append({
            "butce": tl,
            "hafta": t["hafta"],
            "sekil": t["sekil"],
            "ort_kolon": sum(w["kolon"] for w in hs) / len(hs),
            "maliyet": t["maliyet"],
            "kacaksiz_hafta": kacaksiz,
            "p_kacak_sifir": kacaksiz / len(hs),
            "ort_p_hedef": t["ort_p_hedef"],
            "kacak_hafta": t["kacak_hafta"],
            "gercek_odul": t["gercek_odul"],
            "gercek_roi": t.get("gercek_roi"),
            "taban_roi": t.get("taban_roi"),
            "kat": t.get("kat"),
            "kacaksiz_bin_tl": 1000.0 * kacaksiz / t["maliyet"]
            if t["maliyet"] else None,
            "kacaksiz_bin_tl_hafta_ort": sum(
                1000.0 * (w["kacak"] == 0) / w["maliyet"] for w in hs
            ) / len(hs),
        })

    ref = hafta_kaydi.get(referans)
    for kol in kollar:
        if ref is None or kol["butce"] == referans:
            kol["fark"] = None
            continue
        bu = hafta_kaydi[kol["butce"]]
        ortak = sorted(set(bu) & set(ref))
        if not ortak:
            kol["fark"] = None
            continue
        d_hit = [1000.0 * (bu[a]["kacak"] == 0) / bu[a]["maliyet"]
                 - 1000.0 * (ref[a]["kacak"] == 0) / ref[a]["maliyet"]
                 for a in ortak]
        d_roi = [(bu[a]["gercek_odul"] - bu[a]["maliyet"]) / bu[a]["maliyet"]
                 - (ref[a]["gercek_odul"] - ref[a]["maliyet"])
                 / ref[a]["maliyet"] for a in ortak]
        alt, ust = bootstrap_farki(d_hit)
        r_alt, r_ust = bootstrap_farki(d_roi)
        kol["fark"] = {
            "ortak_hafta": len(ortak),
            "kacaksiz_bin_tl": sum(d_hit) / len(d_hit),
            "kacaksiz_bin_tl_alt": alt, "kacaksiz_bin_tl_ust": ust,
            "gecti": alt > 0.0,
            "p": bootstrap_p_degeri(d_hit),
            "roi": sum(d_roi) / len(d_roi),
            "roi_alt": r_alt, "roi_ust": r_ust,
        }

    # Çoklu karşılaştırma: referans dışındaki HER basamak bir adaydır ve
    # beşinde tekil %95 aralığın aile bazlı hatası ~%23'e çıkar. Faz 0.3
    # bu düzeltmeyi zorunlu kıldı (§3.44) — `gecti` tekil aralığı okumaya
    # devam eder, `gecti_holm` yanına yazılır.
    from .evaluate import holm

    p_ler = {str(k["butce"]): k["fark"]["p"]
             for k in kollar if k["fark"]}
    kararlar = holm(p_ler) if p_ler else {}
    for kol in kollar:
        if kol["fark"]:
            kol["fark"]["gecti_holm"] = bool(
                kararlar.get(str(kol["butce"]), False)
                and kol["fark"]["gecti"])
    return {"garanti": garanti, "referans": referans, "kollar": kollar,
            "holm_aday": len(p_ler)}


def hedef_kademe_kiyasi(butce_tl: float = 2000.0,
                        garanti: int = 14,
                        kademeler: Sequence[int] = (12, 13, 14),
                        hafta_siniri: int | None = None) -> dict[str, Any]:
    """E2: hedef kademeyi **paradan** seç — tabandan değil gerçek kolondan.

    `sistem.kacak_esigi(garanti, kademe)` iki parametreli ama `kademe`
    sabit **12** yazılı, ve o 12 bir ölçümden değil bir varsayımdan
    geliyordu. Bu fonksiyon her aday kademeyi 114 hafta boyunca **gerçek
    ikramiye tablosuna** karşı koşturur ve eşleştirilmiş farkı verir.

    Puanlama `gercek_odul`dur, taban değil: E1 tabanın 2,39 kat gevşek ve
    **eğik** olduğunu ölçtü (kaçak küçüldükçe yanlılık büyüyor), yani taban
    tam bu karşılaştırmayı bastırırdı — hedefi sıkılaştırmanın kazancı
    kaçağın küçük olduğu yerdedir.

    Fark **ROI** üzerinde ve hafta hafta eşleştirilmiş: aynı haftanın aynı
    TL'si iki kolda da geçtiği için enflasyon götürür (modül başlığı).
    Kesitler arası medyan **alınmaz** — nominal TL dört sezonda 72 kat
    büyümüş, o yüzden kademe medyanlarını haftalara taşımak ölçümü kirletir.
    """
    kesit = kupon_kesiti()
    if hafta_siniri:
        kesit = kesit[:hafta_siniri]
    kollar: dict[int, dict[tuple[str, int], dict[str, Any]]] = {}
    for kad in kademeler:
        kol: dict[tuple[str, int], dict[str, Any]] = {}
        for h in kesit:
            plan = sistem_secimi(h["probs"], butce_tl, garanti=garanti,
                                 kademe=kad)
            if plan is None:
                continue
            ham = gercek_kolon_dagilimi(plan.secimler, h["gercek"])
            if not ham:
                continue
            olcek = plan.bedel / sum(ham.values())
            dagilim = {k: v * olcek for k, v in ham.items()}
            maliyet = plan.bedel * KOLON_BEDELI
            odul = gercek_odul(dagilim, h["tablo"]) or 0.0
            kol[(h["sezon"], h["hafta"])] = {
                "maliyet": maliyet, "odul": odul, "roi": odul / maliyet,
                "kolon": plan.bedel, "p_hedef": plan.p_hedef,
                "cift": plan.cift, "uclu": plan.uclu,
                "kacak": sum(1 for sc, c in zip(plan.secimler, h["gercek"])
                             if c not in sc),
            }
        kollar[kad] = kol
    ortak = sorted(set.intersection(*(set(k) for k in kollar.values()))
                   ) if kollar else []

    kollar_ozet = []
    for kad, kol in kollar.items():
        v = [kol[a] for a in ortak]
        kollar_ozet.append({
            "kademe": kad, "hafta": len(v),
            "roi": (sum(x["odul"] for x in v) / sum(x["maliyet"] for x in v)
                    if v else 0.0),
            "odul_alan_hafta": sum(1 for x in v if x["odul"] > 0),
            "ort_kolon": _ortalama([x["kolon"] for x in v]),
            "ort_p_hedef": _ortalama([x["p_hedef"] for x in v]),
            "sekiller": sorted({(x["cift"], x["uclu"]) for x in v}),
        })

    farklar = []
    for i, a in enumerate(kademeler):
        for b in kademeler[i + 1:]:
            f = [kollar[b][k]["roi"] - kollar[a][k]["roi"] for k in ortak]
            alt, ust = bootstrap_farki(f)
            # Kuyruk sınavı: en çok kazandıran KUYRUK_HAFTA hafta çıkınca.
            en_iyi = sorted(range(len(ortak)),
                            key=lambda j: -kollar[b][ortak[j]]["odul"]
                            )[:KUYRUK_HAFTA]
            ks = [x for j, x in enumerate(f) if j not in set(en_iyi)]
            kalt, kust = bootstrap_farki(ks)
            farklar.append({
                "kademe": f"{b}-{a}",
                "ust_kademe": b, "alt_kademe": a,
                "ort": _ortalama(f), "alt": alt, "ust": ust,
                "sifir_disinda": alt > 0.0 or ust < 0.0,
                "kuyruksuz_ort": _ortalama(ks),
                "kuyruksuz_alt": kalt, "kuyruksuz_ust": kust,
                "kuyruksuz_sifir_disinda": kalt > 0.0 or kust < 0.0,
            })

    varsayilan = kollar.get(HEDEF_KADEME, {})
    kacak_kirilim: dict[int, dict[str, Any]] = {}
    for anahtar in ortak:
        x = varsayilan.get(anahtar)
        if x is None:
            continue
        kacak_kirilim.setdefault(x["kacak"], {"roi": [], "odul_alan": 0})
        kacak_kirilim[x["kacak"]]["roi"].append(x["roi"])
        if x["odul"] > 0:
            kacak_kirilim[x["kacak"]]["odul_alan"] += 1
    basabas = {
        k: {"hafta": len(v["roi"]), "medyan_roi": _medyan(v["roi"]),
            "ortalama_roi": _ortalama(v["roi"]),
            "odul_alan_hafta": v["odul_alan"],
            "maliyeti_karsiliyor": _medyan(v["roi"]) >= 1.0}
        for k, v in sorted(kacak_kirilim.items())
    }
    return {"butce": butce_tl, "garanti": garanti, "hafta": len(ortak),
            "kollar": kollar_ozet, "farklar": farklar, "basabas": basabas}


def omurga_kiyasi(butce_tl: float = 2000.0,
                  garanti: int = 14,
                  aday: str = "BFE",
                  omurga: str | None = None) -> dict[str, Any]:
    """E3: omurga fiyatını **kupon düzeyinde** kıyasla — Brier'de değil TL'de.

    §3.52 Betfair Exchange'in Brier'de geçtiğini ölçtü (−0,00100, Holm'lu)
    ve marjının omurganınkinin onda biri olduğunu gösterdi. Ama omurgayı
    değiştirmenin ölçüsü Brier değildir: §3.19 karar katmanının +6,02
    puanı için tahmin tarafında ~0,10 Brier gerekirdiğini ölçtü, yani
    −0,001 kupon için görünmez. **Marj farkı ise Brier'de görünmeyen bir
    etkidir** — arındırma ne kadar az müdahale ederse olasılık o kadar az
    bozulur ve kupon şekli değişebilir.

    Bu yüzden ölçü üç kupon sayısıdır: kolon, `P(hedef)` ve **gerçek kolon
    ödülü**. Kesit ikisinde de aynı haftalardan kurulur (eşleştirme), yani
    BFE'nin kapsamadığı haftalar iki koldan da düşer.

    ─── İş 4: dördüncü ölçü — ISABET (2026-09-05) ────────────────────────

    E3 iki cetvelle karar verdi ve ikisi de sorunluydu: gerçek kolon
    **ROI** kuyruk ağırlıklıdır ve 64 haftada gürültülüdür; `P(hedef)` ise
    modelin kendi güvenidir ve farkın %81'i seçim hiç değişmeden geliyordu
    (`p_ayrisimi`). Sorulmamış olan üçüncüsü **isabetin kendisiydi**:
    gerçekleşen kaçak sayısı her hafta gözlenir ve ROI'den çok daha az
    oynaktır.

    `kacak` ve `kacaksiz` alanları bu yüzden eklendi. Ölçünün yönü ters:
    kaçak **küçük** iyidir, kaçaksız hafta **büyük** iyidir.

    **Kapsama sınırı şimdiden yazılı:** BFE kapsaması 2022/23–2023/24'te
    sıfır, 2024/25 %100, 2025/26 %87. `n` iki sezon, ve `sezonlar` alanı
    işaretin sezon sezon tutup tutmadığını ayrı gösterir.
    """
    from .odds import FIYAT_VARSAYILAN

    ana = FIYAT_VARSAYILAN if omurga is None else omurga
    kollar: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    kesit_boy: dict[str, int] = {}
    for ad in (ana, aday):
        kesit = kupon_kesiti(kaynaklar=(ad,))
        kesit_boy[ad] = len(kesit)
        kol: dict[tuple[str, int], dict[str, Any]] = {}
        for h in kesit:
            plan = sistem_secimi(h["probs"], butce_tl, garanti=garanti)
            if plan is None:
                continue
            ham = gercek_kolon_dagilimi(plan.secimler, h["gercek"])
            if not ham:
                continue
            olcek = plan.bedel / sum(ham.values())
            maliyet = plan.bedel * KOLON_BEDELI
            odul = gercek_odul({k: v * olcek for k, v in ham.items()},
                               h["tablo"]) or 0.0
            kol[(h["sezon"], h["hafta"])] = {
                "maliyet": maliyet, "odul": odul, "roi": odul / maliyet,
                "kolon": plan.bedel, "p_hedef": plan.p_hedef,
                "kacak": sum(1 for sc, c in zip(plan.secimler, h["gercek"])
                             if c not in sc),
            }
        kollar[ad] = kol
    ortak = sorted(set(kollar[ana]) & set(kollar[aday]))

    ozet = []
    for ad in (ana, aday):
        v = [kollar[ad][k] for k in ortak]
        ozet.append({
            "kaynak": ad, "kesit_hafta": kesit_boy[ad], "hafta": len(v),
            "roi": (sum(x["odul"] for x in v) / sum(x["maliyet"] for x in v)
                    if v else 0.0),
            "odul_alan_hafta": sum(1 for x in v if x["odul"] > 0),
            "ort_kolon": _ortalama([x["kolon"] for x in v]),
            "ort_p_hedef": _ortalama([x["p_hedef"] for x in v]),
            "ort_kacak": _ortalama([float(x["kacak"]) for x in v]),
            "kacaksiz_hafta": sum(1 for x in v if x["kacak"] == 0),
        })

    farklar = {}
    for alan in ("roi", "p_hedef", "kacak", "kacaksiz"):
        def _al(x: dict[str, Any], alan: str = alan) -> float:
            if alan != "kacaksiz":
                return float(x[alan])
            return 1.0 if x["kacak"] == 0 else 0.0
        f = [_al(kollar[aday][k]) - _al(kollar[ana][k]) for k in ortak]
        alt, ust = bootstrap_farki(f)
        en_iyi = sorted(range(len(ortak)),
                        key=lambda j: -kollar[aday][ortak[j]]["odul"]
                        )[:KUYRUK_HAFTA]
        ks = [x for j, x in enumerate(f) if j not in set(en_iyi)]
        kalt, kust = bootstrap_farki(ks)
        farklar[alan] = {
            "ort": _ortalama(f), "alt": alt, "ust": ust,
            "sifir_disinda": alt > 0.0 or ust < 0.0,
            "kuyruksuz_ort": _ortalama(ks),
            "kuyruksuz_alt": kalt, "kuyruksuz_ust": kust,
            "kuyruksuz_sifir_disinda": kalt > 0.0 or kust < 0.0,
        }
    ayni_kupon = sum(1 for k in ortak
                     if kollar[ana][k]["kolon"] == kollar[aday][k]["kolon"]
                     and kollar[ana][k]["kacak"] == kollar[aday][k]["kacak"])
    # Sezon işareti ayrı: BFE kapsaması 2022/23–2023/24'te SIFIR, yani
    # havuzlanmış sayı iki sezonu temsil ediyor. Ö3 tam bu sınavda düştü
    # (§3.21) ve aynı sınav burada da koşmalı.
    sezonlar: dict[str, dict[str, Any]] = {}
    for k in ortak:
        sz = k[0]
        d = sezonlar.setdefault(sz, {"hafta": 0, "kacak": [], "roi": []})
        d["hafta"] += 1
        d["kacak"].append(float(kollar[aday][k]["kacak"]
                                - kollar[ana][k]["kacak"]))
        d["roi"].append(kollar[aday][k]["roi"] - kollar[ana][k]["roi"])
    sezon_ozeti = [{"sezon": sz, "hafta": d["hafta"],
                    "d_kacak": _ortalama(d["kacak"]),
                    "d_roi": _ortalama(d["roi"])}
                   for sz, d in sorted(sezonlar.items())]
    return {"butce": butce_tl, "garanti": garanti, "omurga": ana,
            "aday": aday, "hafta": len(ortak), "kollar": ozet,
            "farklar": farklar, "ayni_sekil_ve_kacak": ayni_kupon,
            "sezonlar": sezon_ozeti,
            "p_ayrisimi": p_ayrisimi(butce_tl, garanti, aday, ana)}


def kapsama_acigi(butce_tl: float = 2000.0,
                  garanti: int = 14,
                  dilim: int = 3) -> dict[str, Any]:
    """`KADEME_OLASILIKLARI.md` §3'ün açıklanmamış tek yönlü sapmasını ayrıştırır.

    ─── Açık nedir ──────────────────────────────────────────────────────

    Gözlenen kapsama modelin dediğini **her bütçede** aşıyor: 162 kolonda
    model `P(≥12)` %28,85 derken gözlenen %39,5. Belge üç aday sayıyor —
    (a) bağımsızlık varsayımı fazla temkinli, (b) 114 haftalık şans,
    (c) kesit yanlılığı — ve *"ayrıştırılmadan §5'in lehte sayıları buna
    yaslanmamalıdır"* diyor.

    ─── (a) aradan geçen sürede büyük ölçüde elendi, ama TAM değil ───────

    §3.46 hafta içi bağımlılığı ölçtü: korpusta ortalama ikili artık
    korelasyonu −0,00009 [−0,00102, +0,00080] ve korpus **üst sınırında**
    kuyruk yalnız **%5** şişiyor. Ama o sonucu taşıyan korpustur; kupon
    kesiti tek başına ±%82'ye izin veriyordu. Yani (a) *korpus sınırının
    kupona taşındığı varsayımıyla* eleniyor. Bu fonksiyon açığın
    büyüklüğünü ölçer ki o varsayımın ne kadarını taşıması gerektiği
    görülsün.

    ─── Ne ölçülüyor ────────────────────────────────────────────────────

    Modelin ex-ante `P(k ≤ eşik)`i bir **hafta düzeyi tahmindir** ve
    gerçekleşen `[k ≤ eşik]` onun sonucudur. İkisinin farkı (gerçekleşen −
    model) bu tahminin kalibrasyonudur; eşleştirilmiş bootstrap aralığı
    sıfırı kesmiyorsa açık gürültü değildir.

    Üç kırılım verilir ve üçü de **karar için** anlamlıdır:

    ``sezon``
        Açık tek bir sezondan mı geliyor (kesit yanlılığı, aday c)?
    ``favori_gucu``
        Haftanın ortalama favori olasılığına göre dilim. A5'in
        favori–sürpriz yanlılığı bu eksende ölçülmüştü; açık favorinin
        güçlü olduğu haftalarda büyüyorsa **kalibrasyon** adayı güçlenir.
    ``model_p``
        Modelin kendi `P(k ≤ eşik)`ine göre dilim. Bu kırılım ayrıca
        **hafta seçimi** sorusunu cevaplar: ex-ante `P` haftalar arasında
        kalibreyse, yüksek `P` haftalarına yığmak aritmetik olarak çalışır.

        cd backend && python -m spor_toto.karne --kapsama --garanti 14
    """
    from .sistem import HEDEF_KADEME as _hk
    from .sistem import kacak_esigi

    esik = kacak_esigi(garanti, _hk)
    satirlar: list[dict[str, Any]] = []
    maclar: list[dict[str, Any]] = []
    for h in kupon_kesiti():
        plan = sistem_secimi(h["probs"], butce_tl, garanti=garanti)
        if plan is None:
            continue
        kacak = sum(1 for sc, c in zip(plan.secimler, h["gercek"])
                    if c not in sc)
        satirlar.append({
            "sezon": h["sezon"], "hafta": h["hafta"],
            "model_p": plan.p_hedef,
            "gerceklesen": 1.0 if kacak <= esik else 0.0,
            "kacak": kacak,
            "favori_gucu": _ortalama([max(p.values()) for p in h["probs"]]),
        })
        for sc, c, pr in zip(plan.secimler, h["gercek"], h["probs"]):
            q = max(0.0, 1.0 - sum(pr.get(x, 0.0) for x in sc))
            maclar.append({"q": q, "kacti": 0.0 if c in sc else 1.0,
                           "seviye": len(sc), "sezon": h["sezon"]})
    if not satirlar:
        raise KarneHatasi("kesit bos")

    def _ozet(alt: Sequence[dict[str, Any]]) -> dict[str, Any]:
        f = [x["gerceklesen"] - x["model_p"] for x in alt]
        lo, hi = bootstrap_farki(f)
        return {
            "hafta": len(alt),
            "model_p": _ortalama([x["model_p"] for x in alt]),
            "gerceklesen": _ortalama([x["gerceklesen"] for x in alt]),
            "acik": _ortalama(f), "alt": lo, "ust": hi,
            "sifir_disinda": lo > 0.0 or hi < 0.0,
        }

    def _dilimle(alan: str) -> list[dict[str, Any]]:
        sirali = sorted(satirlar, key=lambda x: x[alan])
        boy = len(sirali)
        out = []
        for i in range(dilim):
            parca = sirali[i * boy // dilim:(i + 1) * boy // dilim]
            if not parca:
                continue
            out.append({
                "dilim": i + 1,
                "alt_sinir": parca[0][alan], "ust_sinir": parca[-1][alan],
                **_ozet(parca),
            })
        return out

    return {
        "butce": butce_tl, "garanti": garanti, "esik": esik,
        "tumu": _ozet(satirlar),
        "sezon": [{"sezon": sz,
                   **_ozet([x for x in satirlar if x["sezon"] == sz])}
                  for sz in sorted({x["sezon"] for x in satirlar})],
        "favori_gucu": _dilimle("favori_gucu"),
        "model_p": _dilimle("model_p"),
        # Maç düzeyi: optimizatörün kullandığı `q` ile GERÇEKLEŞEN kaçma
        # oranı. Hafta düzeyi kırılımlar düz çıkarsa mekanizma buradadır —
        # `q` bir hafta özelliği değil, **sembol** özelliğidir.
        "q_dilim": _q_dilimleri(maclar, dilim),
        # Aynı soru, **sıralamadan bağımsız** kesitte: banko ↔ çifte.
        # `q_dilim` tam da sınadığı değişkene göre sıralıyor ve o sıralama
        # `q`nun gürültüsünü uçlara taşır (ortalamaya dönüş). Seviye ise
        # optimizatörün **ayrık kararıdır**; aynı sapma orada da görünüyorsa
        # bulgu sıralama eseri olamaz.
        "seviye": _seviye_kirilimi(maclar),
        "mac": len(maclar),
        # §3.46'nın korpus üst sınırı: bağımlılık kuyruğu en fazla bu kadar
        # şişirebilir. Açık bundan büyükse bağımsızlık adayı açığı TEK
        # BAŞINA açıklayamaz.
        "bagimlilik_tavani": 0.05,
    }


def _seviye_kirilimi(maclar: Sequence[dict[str, Any]]
                     ) -> list[dict[str, Any]]:
    """`q` ↔ gerçekleşen, **işaret sayısına** göre — sıralama eseri değil.

    `_q_dilimleri` sınadığı değişkenin kendisine göre sıralıyor ve bu,
    ortalamaya dönüş üretir: `q`nun kestirim gürültüsü pozitif olan maçlar
    üst dilime toplanır, gerçekleşen oran o dilimde `q`nun altında çıkar —
    sapma olmasa bile. Bu kırılım aynı soruyu optimizatörün **ayrık**
    kararıyla sorar (banko / çifte), yani bucket sınırları `q`nun
    gürültüsünden gelmez.
    """
    out: list[dict[str, Any]] = []
    for sev, ad in ((1, "banko"), (2, "cifte")):
        parca = [m for m in maclar if m["seviye"] == sev]
        if not parca:
            continue
        q_ort = _ortalama([m["q"] for m in parca])
        gercek = _ortalama([m["kacti"] for m in parca])
        lo, hi = wilson(sum(int(m["kacti"]) for m in parca), len(parca))
        out.append({
            "seviye": sev, "ad": ad, "mac": len(parca),
            "q": q_ort, "gerceklesen": gercek, "acik": gercek - q_ort,
            "wilson_alt": lo, "wilson_ust": hi,
            "sifir_disinda": not (lo <= q_ort <= hi),
        })
    return out


def _q_dilimleri(maclar: Sequence[dict[str, Any]],
                 dilim: int) -> list[dict[str, Any]]:
    """Kaçma olasılığı `q` ↔ **gerçekleşen** kaçma oranı, `q` dilimlerinde.

    Üçlüler dışarıda: `q = 0` tanım gereği ve asla kaçmazlar (`secim`
    modül başlığı), yani dilimlemede yalnız gürültü yaparlardı. Kalan
    banko ve çifteler kuponun **karar verilen** maçlarıdır.

    Bu, kapsama açığının mekanizma sınavıdır: hafta düzeyi kırılımlar düz
    çıkarken burada tek yönlü bir sapma varsa açık maç seçiminden değil
    **sembol olasılığından** geliyor demektir.
    """
    kararli = sorted((m for m in maclar if m["q"] > 0.0),
                     key=lambda m: m["q"])
    boy = len(kararli)
    out: list[dict[str, Any]] = []
    for i in range(dilim):
        parca = kararli[i * boy // dilim:(i + 1) * boy // dilim]
        if not parca:
            continue
        q_ort = _ortalama([m["q"] for m in parca])
        gercek = _ortalama([m["kacti"] for m in parca])
        lo, hi = wilson(sum(int(m["kacti"]) for m in parca), len(parca))
        out.append({
            "dilim": i + 1, "mac": len(parca),
            "alt_sinir": parca[0]["q"], "ust_sinir": parca[-1]["q"],
            "q": q_ort, "gerceklesen": gercek, "acik": gercek - q_ort,
            "wilson_alt": lo, "wilson_ust": hi,
            "sifir_disinda": not (lo <= q_ort <= hi),
        })
    return out


def banko_yanliligi(dilim: int = 3,
                    yontemler: Sequence[str] = ("orantili", "guc", "shin"),
                    korpus: bool = False,
                    ligler: Sequence[str] | None = None) -> dict[str, Any]:
    """§3.60'ın açık ucu: banko `q` sapması **arındırma eseri mi, yanlılık mı?**

    §3.60 ölçtü: optimizatörün banko maçlarına atadığı `q` gerçekleşenden
    **5,6 puan yüksek** (%37,3 ↔ %31,7). `q_banko = 1 − p₁` olduğuna göre
    aynı cümle şudur: **en olası sembolün olasılığı 5,6 puan düşük
    yazılıyor.** Sebep iki yerden gelebilir ve ikisi bambaşka işler
    gerektirir:

    ``arındırma eseri``
        Marj kaldırma yöntemi favoriye hak ettiğinden az pay veriyordur.
        Öyleyse çözüm `odds.ARINDIRMA_VARSAYILAN`ı değiştirmektir —
        ücretsiz, ve A5'in zaten bir kez yaptığı iş.
    ``piyasa yanlılığı``
        Fiyatın kendisi favoriyi ucuza satıyordur (favori–uzunatış
        yanlılığının bilinen yönü). Öyleyse hiçbir normalizasyon onu
        kapatmaz; düzeltme kalibrasyon katmanında ve **banda özgü** olmak
        zorundadır (§3.61 global bir düzeltmenin yetmediğini gösterdi).

    ─── Sınavı ayıran kurulum: ÖRNEKLEM SABİT ────────────────────────────

    Her yöntem kendi favorisini seçseydi karşılaştırma iki şeyi birden
    değiştirirdi. Bu yüzden favori sembol **tek bir referansla** (`shin`)
    bir kez belirlenir ve üç yöntem de **aynı maçın aynı sembolüne** ne
    olasılık verdiğiyle sınanır. Dilimler de referansa göre kesilir. Böylece
    değişen tek şey arındırmanın kendisidir.

    `korpus=True` aynı sınavı 31.103 maçlık eğitim korpusunda koşar — kupon
    kesitinin 1.710'una karşı 18 kat güç. Kupon kesiti **karar için**,
    korpus **güç için** okunur.

        cd backend && python -m spor_toto.karne --banko
        cd backend && python -m spor_toto.karne --banko --korpus
    """
    from .odds import ARINDIRMA_VARSAYILAN

    ref = ARINDIRMA_VARSAYILAN
    suzgec = set(ligler) if ligler else None
    kesitler = {y: [x for x in _favori_satirlari(y, korpus)
                    if suzgec is None or x["lig"] in suzgec]
                for y in yontemler}
    if ref not in kesitler:
        kesitler[ref] = [x for x in _favori_satirlari(ref, korpus)
                         if suzgec is None or x["lig"] in suzgec]
    n = min(len(v) for v in kesitler.values())
    if not n:
        raise KarneHatasi("kesit bos")
    for y, v in kesitler.items():
        if len(v) != n:
            raise KarneHatasi(
                f"{y} kesiti {len(v)} satir, {ref} {n} — eslesmiyor")

    # Favori sembol ve dilim sinirlari REFERANSTAN; yontemler yalnizca o
    # sembole verdikleri olasilikla yarisiyor.
    referans = kesitler[ref]
    sira = sorted(range(n), key=lambda i: referans[i]["p_favori"])
    kollar: list[dict[str, Any]] = []
    for y in yontemler:
        satir = kesitler[y]
        dilimler = []
        for d in range(dilim):
            idx = sira[d * n // dilim:(d + 1) * n // dilim]
            if not idx:
                continue
            dilimler.append(_kalibrasyon_ozeti(
                [satir[i]["p_favori"] for i in idx],
                [satir[i]["tuttu"] for i in idx],
                referans[idx[0]]["p_favori"], referans[idx[-1]]["p_favori"]))
        # Banko rejimi: referansin en yuksek p_favori'li ust yarisi.
        ust = sira[n // 2:]
        kollar.append({
            "yontem": y,
            "tumu": _kalibrasyon_ozeti(
                [x["p_favori"] for x in satir],
                [x["tuttu"] for x in satir], None, None),
            "banko_rejimi": _kalibrasyon_ozeti(
                [satir[i]["p_favori"] for i in ust],
                [satir[i]["tuttu"] for i in ust],
                referans[ust[0]]["p_favori"], referans[ust[-1]]["p_favori"]),
            "dilimler": dilimler,
        })
    # Lig kirilimi REFERANS yontemle: korpus ile kupon arasindaki fark
    # lig agirligindan mi geliyor? Kuponun yarisi Super Lig'den gelir
    # (932/1.785, %52,2) ve korpusun 22 liginin agirligi bambaska.
    lig_sayim: dict[str, list[int]] = {}
    for i, x in enumerate(referans):
        lig_sayim.setdefault(x["lig"], []).append(i)
    lig_ozeti = [
        {"lig": lg, **_kalibrasyon_ozeti(
            [referans[i]["p_favori"] for i in idx],
            [referans[i]["tuttu"] for i in idx], None, None)}
        for lg, idx in sorted(lig_sayim.items(), key=lambda kv: -len(kv[1]))
        if len(idx) >= EN_AZ_LIG_MAC
    ]
    # Sezon isareti: Ö3 tam bu sinavda dustu (§3.21). Havuzlanmis bir sapma,
    # bir iki sezonun tasidigi bir sey olabilir; kirilim onu gorunur kilar.
    # BANKO REJIMINDE olculur, cunku karari veren o rejim.
    ust_kume = set(sira[n // 2:])
    sezon_sayim: dict[str, list[int]] = {}
    for i in ust_kume:
        sezon_sayim.setdefault(referans[i]["sezon"], []).append(i)
    sezonlar = [
        {"sezon": sz, **_kalibrasyon_ozeti(
            [referans[i]["p_favori"] for i in idx],
            [referans[i]["tuttu"] for i in idx], None, None)}
        for sz, idx in sorted(sezon_sayim.items())
    ]
    return {"kesit": "korpus" if korpus else "kupon", "mac": n,
            "referans": ref, "kollar": kollar, "ligler": lig_ozeti,
            "sezonlar": sezonlar,
            "lig_suzgeci": sorted(suzgec) if suzgec else None}


def _favori_satirlari(yontem: str, korpus: bool) -> list[dict[str, Any]]:
    """`(p_favori, tuttu)` satırları — favori sembol **her yöntemde kendi**.

    Çağıran bunları referansın favorisiyle hizalar; burada hizalama
    yapılmaz çünkü sıra iki kaynakta da maç sırasıdır ve `banko_yanliligi`
    aynı indekse bakar.
    """
    out: list[dict[str, Any]] = []
    if korpus:
        from .egitim import korpus_haftalari
        for h in korpus_haftalari(yontem=yontem):
            for pr, kod, oz in zip(h["probs"], h["results"],
                                    h["ozellikler"]):
                if not pr:
                    continue
                fav = max(pr, key=lambda k: pr[k])
                out.append({"p_favori": pr[fav],
                            "lig": oz.get("lig") or "bilinmiyor",
                            "sezon": h["sezon"],
                            "tuttu": 1.0 if kod == fav else 0.0})
        return out
    for h in kupon_kesiti(yontem=yontem):
        for pr, kod, lig in zip(h["probs"], h["gercek"], h["ligler"]):
            fav = max(pr, key=lambda k: pr[k])
            out.append({"p_favori": pr[fav], "lig": lig, "sezon": h["sezon"],
                        "tuttu": 1.0 if kod == fav else 0.0})
    return out


def _kalibrasyon_ozeti(p: Sequence[float], tuttu: Sequence[float],
                       alt_sinir: float | None,
                       ust_sinir: float | None) -> dict[str, Any]:
    """Söylenen ↔ gerçekleşen, Wilson aralığıyla ve `p` içeride mi diye."""
    ort_p, gercek = _ortalama(list(p)), _ortalama(list(tuttu))
    lo, hi = wilson(sum(int(x) for x in tuttu), len(tuttu))
    return {
        "mac": len(p), "alt_sinir": alt_sinir, "ust_sinir": ust_sinir,
        "p": ort_p, "gerceklesen": gercek, "acik": gercek - ort_p,
        "wilson_alt": lo, "wilson_ust": hi,
        "sifir_disinda": not (lo <= ort_p <= hi),
    }


def kalibre_kesit(kesit: Sequence[dict[str, Any]],
                  kademe: str = "bias") -> list[dict[str, Any]]:
    """Kupon kesitinin olasılıklarını **sezon dışarıda bırakmalı** kalibre eder.

    Kesit aynı kalır (aynı haftalar, aynı sonuçlar, aynı ikramiye tablosu);
    değişen tek şey `probs`tur. Kalibrasyon her hafta için o haftanın
    **bütün sezonu** eğitimden çıkarılarak kestirilir — `arena`nın
    `KUPON_KORPUS_KESISIMI` uyarısının istediği budur: kupon maçlarının
    %71'i korpusta da var, hafta dışarıda bırakmak yetmez.

    `bias` basamağı yalnız `probs` okur (sıcaklık + iki sınıf sabiti), o
    yüzden özellik satırları nötr geçilir; üst basamaklar bu yoldan
    ölçülemez ve `KADEMELER` sırası bunu zorlar.
    """
    from .egitim import korpus_haftalari, sezon_anahtari
    from .recalibrate import KADEMELER, KalibreTahminci

    if KADEMELER.index(kademe) > KADEMELER.index("bias"):
        raise ValueError(
            f"{kademe} basamagi ozellik sutunu ister; bu yol yalniz "
            "probs okuyan basamaklar icindir (sicaklik, bias)")
    korpus = korpus_haftalari()
    onbellek: dict[Any, KalibreTahminci] = {}
    out: list[dict[str, Any]] = []
    for h in kesit:
        anahtar = sezon_anahtari(h["sezon"])
        tahminci = onbellek.get(anahtar)
        if tahminci is None:
            tahminci = KalibreTahminci(kademe)
            tahminci.egit([w for w in korpus
                           if sezon_anahtari(w["sezon"]) != anahtar])
            onbellek[anahtar] = tahminci
        yeni_probs = tahminci.tahmin({
            "probs": h["probs"],
            "ozellikler": [{} for _ in h["probs"]],
        })
        out.append({**h, "probs": yeni_probs})
    return out


def kalibrasyon_kiyasi(butce_tl: float = 2000.0,
                       garanti: int = 14,
                       kademe: str = "bias") -> dict[str, Any]:
    """İş 1: omurga olasılığını **karar cetveliyle** kıyasla — Brier'de değil.

    ─── Niçin bu ölçüm, ve niçin Brier onu veremiyor ─────────────────────

    `KADEME_OLASILIKLARI.md` §3'te açıklanmamış tek yönlü bir sapma duruyor:
    **gözlenen kapsama modelin dediğini her bütçede aşıyor** (162 kolonda
    model %28,85, gözlenen %39,5). Belge üç aday sayıyor — bağımsızlık,
    şans, kesit yanlılığı — ve *"§5'in lehte sayıları buna yaslanmamalıdır"*
    diye uyarıyor. Bağımsızlık §3.46'da büyük ölçüde elendi (korpus üst
    sınırında kuyruk yalnız %5 şişiyor). Belgenin **saymadığı** dördüncü
    aday ölçülmüş bir olgudur: A5'in favori–sürpriz yanlılığı — piyasanın
    %70–80 dediği maçlar gerçekte **%78,9**, sapma tek yönlü ve düzenli.

    Banko kararını tam olarak o bant verir. `q = 1 − p₁` sistematik olarak
    fazla yüksekse `sistem_secimi` **gereğinden fazla kapsama satın alır**:
    çiftenin yeteceği yere üçlü koyar. Aynı parayla daha az maç kapanır ve
    bu doğrudan tutturma olasılığıdır.

    Brier bunu göremez, ve bunu söyleyen sayı deponun kendisinde: §3.19
    dönüşümü **0,01 Brier ≈ +0,6 puan** ölçtü, yani `kalibre_bias`ın
    −0,0013'ü Brier ölçeğinde +0,08 puan eder. Karar cetveli farklı bir
    şey sorar: **şekil değişiyor mu, ve değişince gerçekleşen kaçak
    düşüyor mu?**

    ─── Ölçü: modelin kendi sayısı DEĞİL, gerçekleşen ────────────────────

    Üç sayı gerçekleşendir (`kacak`, `kacaksiz_hafta`, gerçek kolon
    `roi`), biri modelin kendisidir (`p_hedef`) ve **o tek başına kanıt
    sayılmaz** — E3 bunu ölçtü: BFE farkının %81'i seçim hiç değişmeden,
    yalnız keskinlikten geliyordu (§3.58). `p_ayrisimi` alanı aynı
    ayrıştırmayı burada da yapar.

    ─── Durma kuralı (ölçümden ÖNCE yazıldı) ─────────────────────────────

    `kalibre_bias` omurga olur ancak **kaçaksız hafta** farkının VE gerçek
    kolon ROI farkının eşleştirilmiş hafta-bootstrap %95 aralığı **tamamı
    sıfırın üstünde** kalırsa. Yalnız `P(hedef)` büyümesi geçmez. Aralık
    sıfırı keserse manşet `piyasa` kalır ve `tahmin.py`nin gerekçesi
    **güncel kesitle** yeniden yazılır.

        cd backend && python -m spor_toto.karne --kalibrasyon --garanti 14
    """
    from .sistem import HEDEF_KADEME as _hk
    from .sistem import kacak_esigi

    ham = kupon_kesiti()
    kesitler = {"piyasa": ham, f"kalibre_{kademe}": kalibre_kesit(ham, kademe)}
    kollar: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    for ad, kesit in kesitler.items():
        kol: dict[tuple[str, int], dict[str, Any]] = {}
        for h in kesit:
            plan = sistem_secimi(h["probs"], butce_tl, garanti=garanti)
            if plan is None:
                continue
            dag = gercek_kolon_dagilimi(plan.secimler, h["gercek"])
            if not dag:
                continue
            olcek = plan.bedel / sum(dag.values())
            maliyet = plan.bedel * KOLON_BEDELI
            odul = gercek_odul({k: v * olcek for k, v in dag.items()},
                               h["tablo"]) or 0.0
            kol[(h["sezon"], h["hafta"])] = {
                "maliyet": maliyet, "odul": odul, "roi": odul / maliyet,
                "kolon": plan.bedel, "p_hedef": plan.p_hedef,
                "secimler": plan.secimler,
                "kacak": sum(1 for sc, c in zip(plan.secimler, h["gercek"])
                             if c not in sc),
            }
        kollar[ad] = kol
    adlar = list(kesitler)
    ortak = sorted(set(kollar[adlar[0]]) & set(kollar[adlar[1]]))

    ozet = []
    for ad in adlar:
        v = [kollar[ad][k] for k in ortak]
        ozet.append({
            "kaynak": ad, "hafta": len(v),
            "roi": (sum(x["odul"] for x in v) / sum(x["maliyet"] for x in v)
                    if v else 0.0),
            "kacaksiz_hafta": sum(1 for x in v if x["kacak"] == 0),
            "ort_kacak": _ortalama([float(x["kacak"]) for x in v]),
            "ort_kolon": _ortalama([x["kolon"] for x in v]),
            "ort_p_hedef": _ortalama([x["p_hedef"] for x in v]),
            "odul_alan_hafta": sum(1 for x in v if x["odul"] > 0),
        })

    a, b = adlar
    farklar = {}
    for alan in ("roi", "kacak", "p_hedef", "kacaksiz"):
        def _al(x: dict[str, Any], alan: str = alan) -> float:
            return 1.0 if alan == "kacaksiz" and x["kacak"] == 0 else (
                0.0 if alan == "kacaksiz" else float(x[alan]))
        f = [_al(kollar[b][k]) - _al(kollar[a][k]) for k in ortak]
        alt, ust = bootstrap_farki(f)
        en_iyi = sorted(range(len(ortak)),
                        key=lambda j: -kollar[b][ortak[j]]["odul"]
                        )[:KUYRUK_HAFTA]
        ks = [x for j, x in enumerate(f) if j not in set(en_iyi)]
        kalt, kust = bootstrap_farki(ks)
        farklar[alan] = {
            "ort": _ortalama(f), "alt": alt, "ust": ust,
            "sifir_disinda": alt > 0.0 or ust < 0.0,
            "kuyruksuz_ort": _ortalama(ks),
            "kuyruksuz_alt": kalt, "kuyruksuz_ust": kust,
            "kuyruksuz_sifir_disinda": kalt > 0.0 or kust < 0.0,
        }

    # E3 tuzagina karsi: P(hedef) farkinin ne kadari secim DEGISMEDEN?
    esik = kacak_esigi(garanti, _hk)
    kes_a = {(h["sezon"], h["hafta"]): h for h in kesitler[a]}
    kes_b = {(h["sezon"], h["hafta"]): h for h in kesitler[b]}
    sabit, serbest = [], []
    for k in ortak:
        sec_a = kollar[a][k]["secimler"]
        sabit.append(_p_hedef(sec_a, kes_b[k]["probs"], esik)
                     - _p_hedef(sec_a, kes_a[k]["probs"], esik))
        serbest.append(kollar[b][k]["p_hedef"] - kollar[a][k]["p_hedef"])
    o_sabit, o_serbest = _ortalama(sabit), _ortalama(serbest)

    ayni = sum(1 for k in ortak
               if kollar[a][k]["kolon"] == kollar[b][k]["kolon"]
               and kollar[a][k]["kacak"] == kollar[b][k]["kacak"])
    degisen = sum(1 for k in ortak
                  if kollar[a][k]["secimler"] != kollar[b][k]["secimler"])
    return {
        "butce": butce_tl, "garanti": garanti, "kademe": kademe,
        "hafta": len(ortak), "kollar": ozet, "farklar": farklar,
        "ayni_sekil_ve_kacak": ayni, "isareti_degisen_hafta": degisen,
        "p_ayrisimi": {"hafta": len(sabit), "serbest": o_serbest,
                       "sekil_sabit": o_sabit,
                       "keskinlik_payi": (o_sabit / o_serbest)
                       if o_serbest else None},
        "gecti": (farklar["kacaksiz"]["alt"] > 0.0
                  and farklar["roi"]["alt"] > 0.0),
    }


def _p_hedef(secimler: Sequence[Sequence[str]],
             probs_listesi: Sequence[dict[str, float]], esik: int) -> float:
    """`P(k ≤ esik)` — verilen işaret planını verilen olasılıkla puanlar.

    `sistem_secimi` bunu DP'nin içinde hesaplıyor ve **kendi seçtiği**
    planla; burası aynı hesabı **dışarıdan verilen** bir planla yapar, ki
    aynı kupon iki farklı fiyatla puanlanabilsin.
    """
    q = [max(0.0, 1.0 - sum(p.get(sym, 0.0) for sym in sec))
         for sec, p in zip(secimler, probs_listesi)]
    kum = [1.0] + [0.0] * esik
    for qq in q:
        yeni = [kum[0] * (1.0 - qq)]
        for m in range(1, esik + 1):
            yeni.append(kum[m] * (1.0 - qq) + kum[m - 1] * qq)
        kum = yeni
    return sum(kum)


def p_ayrisimi(butce_tl: float = 2000.0, garanti: int = 14,
               aday: str = "BFE", omurga: str | None = None,
               ) -> dict[str, Any]:
    """`P(hedef)` farkının ne kadarı **seçim değişmeden** geliyor?

    Bu ayrışım olmadan `omurga_kiyasi`nin `p_hedef` satırı yanlış okunur.
    `P(hedef)` bir sonuç değil **modelin kendi güvenidir**: daha keskin bir
    olasılık, isabet hiç değişmese bile onu büyütür. Yani aday fiyatın
    `P(hedef)`i anlamlı biçimde yüksek çıkması tek başına *hiçbir şey*
    söylemez.

    Ayrışım şöyle kurulur: omurganın kurduğu kupon **sabit tutulur** ve iki
    fiyatla ayrı ayrı puanlanır. Kalan pay seçimin gerçekten değişmesinden
    gelir.
    """
    from .odds import FIYAT_VARSAYILAN
    from .sistem import HEDEF_KADEME as _hk
    from .sistem import kacak_esigi

    ana = FIYAT_VARSAYILAN if omurga is None else omurga
    esik = kacak_esigi(garanti, _hk)
    a_kesit = {(h["sezon"], h["hafta"]): h
               for h in kupon_kesiti(kaynaklar=(ana,))}
    b_kesit = {(h["sezon"], h["hafta"]): h
               for h in kupon_kesiti(kaynaklar=(aday,))}
    sabit, serbest = [], []
    for k in sorted(set(a_kesit) & set(b_kesit)):
        pa = sistem_secimi(a_kesit[k]["probs"], butce_tl, garanti=garanti)
        pb = sistem_secimi(b_kesit[k]["probs"], butce_tl, garanti=garanti)
        if pa is None or pb is None:
            continue
        sabit.append(_p_hedef(pa.secimler, b_kesit[k]["probs"], esik)
                     - _p_hedef(pa.secimler, a_kesit[k]["probs"], esik))
        serbest.append(pb.p_hedef - pa.p_hedef)
    o_sabit, o_serbest = _ortalama(sabit), _ortalama(serbest)
    return {
        "hafta": len(sabit),
        "serbest": o_serbest,
        "sekil_sabit": o_sabit,
        "keskinlik_payi": (o_sabit / o_serbest) if o_serbest else None,
    }


def _main(argv: list[str] | None = None) -> int:  # pragma: no cover - elle
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--garanti", type=int, default=VARSAYILAN_GARANTI)
    ap.add_argument("--butce", type=float, default=None)
    ap.add_argument("--taban", action="store_true",
                    help="tabanin gevsekligini olc (yalniz 14-garanti)")
    ap.add_argument("--hedef", action="store_true",
                    help="E2: hedef kademeyi paradan sec (yalniz 14-garanti)")
    ap.add_argument("--egri", action="store_true",
                    help="butce egrisi GERCEK kolon oduluyle (yalniz 14-garanti)")
    ap.add_argument("--hafta-siniri", type=int, default=None,
                    help="ilk N haftayla sinirla (deneme kosumu)")
    ap.add_argument("--omurga", metavar="ADAY", default=None,
                    help="E3: omurga fiyatini kupon duzeyinde kiyasla (or. BFE)")
    ap.add_argument("--kalibrasyon", metavar="KADEME", nargs="?",
                    const="bias", default=None,
                    help="omurga olasiligini karar cetveliyle kiyasla (bias)")
    ap.add_argument("--kapsama", action="store_true",
                    help="model P(k<=esik) ile gerceklesen arasindaki acik")
    ap.add_argument("--banko", action="store_true",
                    help="§3.64: banko q sapmasi arindirma eseri mi, yanlilik mi")
    ap.add_argument("--korpus", action="store_true",
                    help="--banko ile: kupon kesiti yerine 31.103 macliK korpus")
    ap.add_argument("--lig", nargs="+", metavar="LIG", default=None,
                    help="--banko ile: kesiti bu liglere kisitla (or. T1 E0)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.taban:
        t = taban_gevsekligi(a.butce or 2000.0, a.garanti)
        if a.json:
            print(json.dumps(t, ensure_ascii=False))
            return 0
        print(f"\nTabanin gevsekligi — {a.garanti}-garanti · "
              f"{a.butce or 2000.0:,.0f} TL · {t['hafta']} hafta")
        print(f"  maliyet              : {t['maliyet']:>12,.0f} TL")
        print(f"  GARANTI TABANI odul  : {t['taban_odul']:>12,.0f} TL "
              f"(geri donus {t.get('taban_roi', 0.0):.1%})")
        print(f"  GERCEK kolon odulu   : {t['gercek_odul']:>12,.0f} TL "
              f"(geri donus {t.get('gercek_roi', 0.0):.1%})")
        if t["kat"]:
            print(f"  taban ne kadar gevsek: {t['kat']:>12.2f} KAT "
                  f"(motorun HAM kolonlariyla {t['kat_ham']:.2f})")
            print(f"  motor {t['motor_kolon']:,} kolon uretti, tablo ayni "
                  f"sekli {t['tablo_kolon']:,} kolonla satiyor "
                  f"(+{t['kaplama_farki'] - 1:.1%})")
        print("\n  kacak -> 12+ tutturan ortalama kolon sayisi")
        for k, v in t["kacak_kolon"].items():
            print(f"  {k:>7} {v:>12.1f}")
        return 0

    if a.egri:
        e = butce_egrisi(a.garanti, hafta_siniri=a.hafta_siniri)
        if a.json:
            print(json.dumps(e, ensure_ascii=False, default=str))
            return 0
        print(f"\nButce egrisi — {e['garanti']}-garanti · GERCEK kolon odulu")
        print("  odeyen tek olay k=0 (§3.57: k=0 medyan 1,34x, k=1 0,28x)")
        print(f"\n{'butce':>8}{'sekil':>10}{'kolon':>7}{'hafta':>7}"
              f"{'k=0':>6}{'P(k=0)':>9}{'ort P(hedef)':>14}"
              f"{'gercek ROI':>12}{'k=0/1000TL':>12}")
        for k in e["kollar"]:
            sk = "/".join(str(x) for x in k["sekil"]) if k["sekil"] else "-"
            print(f"{k['butce']:>8,.0f}{sk:>10}{k['ort_kolon']:>7.0f}"
                  f"{k['hafta']:>7}{k['kacaksiz_hafta']:>6}"
                  f"{k['p_kacak_sifir']:>9.1%}{k['ort_p_hedef']:>14.4f}"
                  f"{k['gercek_roi']:>12.1%}{k['kacaksiz_bin_tl']:>12.4f}")
        print(f"\nESLESTIRILMIS FARK — referans {e['referans']:,.0f} TL "
              f"(hafta duzeyi bootstrap %95)")
        print(f"{'butce':>8}{'ortak':>7}{'d k=0/1000TL':>15}{'%95 aralik':>26}"
              f"{'tekil':>7}{'p':>9}{'HOLM':>7}{'d ROI':>10}")
        for k in e["kollar"]:
            f = k["fark"]
            if not f:
                continue
            aralik = f"[{f['kacaksiz_bin_tl_alt']:+.4f}, " \
                     f"{f['kacaksiz_bin_tl_ust']:+.4f}]"
            print(f"{k['butce']:>8,.0f}{f['ortak_hafta']:>7}"
                  f"{f['kacaksiz_bin_tl']:>+15.4f}{aralik:>26}"
                  f"{'EVET' if f['gecti'] else 'hayir':>7}{f['p']:>9.4f}"
                  f"{'EVET' if f['gecti_holm'] else 'hayir':>7}"
                  f"{f['roi']:>+10.1%}")
        print(f"  ({e['holm_aday']} aday, Holm–Bonferroni; tekil %95 bes "
              "adayda ~%23 aile hatasi verir)")
        print("\n  kacak histogrami (hafta sayisi)")
        for k in e["kollar"]:
            hist = " ".join(f"{a}:{b}" for a, b in k["kacak_hafta"].items())
            print(f"  {k['butce']:>7,.0f} TL  {hist}")
        print("\nDURMA KURALI (olcumden ONCE yazildi): varsayilan butce ancak "
              "bir\nbasamagin farki %95 araligin TAMAMIYLA sifirin ustunde "
              "kalirsa degisir\n(ve bes aday oldugu icin Holm'dan da "
              "gecmelidir).")
        print("Yalniz 14-garanti. Sonuc 13G'ye TASINMAZ (§3.51, 15,1 kat).")
        return 0

    if a.banko:
        b = banko_yanliligi(korpus=a.korpus, ligler=a.lig)
        if a.json:
            print(json.dumps(b, ensure_ascii=False, default=str))
            return 0
        print(f"\nBanko yanliligi — favori sembolun kalibrasyonu · "
              f"{b['kesit']} kesiti · {b['mac']:,} mac")
        print(f"  ORNEKLEM SABIT: favori sembol ve dilim sinirlari "
              f"'{b['referans']}'dan; yontemler yalniz o sembole verdikleri "
              f"olasilikla yarisiyor")
        for kol in b["kollar"]:
            print(f"\n  {kol['yontem'].upper()}")
            print(f"{'grup':>16}{'mac':>8}{'soylenen':>11}{'gercek':>9}"
                  f"{'acik':>9}{'Wilson %95':>22}{'p disinda':>11}")
            for ad, r in (("tumu", kol["tumu"]),
                          ("BANKO REJIMI", kol["banko_rejimi"]),
                          *[(f"dilim {i + 1}", d)
                            for i, d in enumerate(kol["dilimler"])]):
                etiket = ad
                if r["alt_sinir"] is not None and ad.startswith("dilim"):
                    etiket = f"{r['alt_sinir']:.3f}-{r['ust_sinir']:.3f}"
                aralik = f"[{r['wilson_alt']:.1%}, {r['wilson_ust']:.1%}]"
                print(f"{etiket:>16}{r['mac']:>8,}{r['p']:>11.1%}"
                      f"{r['gerceklesen']:>9.1%}{r['acik']:>+9.1%}{aralik:>22}"
                      f"{'EVET' if r['sifir_disinda'] else 'hayir':>11}")
        print(f"\n  LIG KIRILIMI ({b['referans']}; en az "
              f"{EN_AZ_LIG_MAC} mac)")
        print(f"{'lig':>16}{'mac':>8}{'soylenen':>11}{'gercek':>9}"
              f"{'acik':>9}{'Wilson %95':>22}{'p disinda':>11}")
        for r in b["ligler"]:
            aralik = f"[{r['wilson_alt']:.1%}, {r['wilson_ust']:.1%}]"
            print(f"{r['lig']:>16}{r['mac']:>8,}{r['p']:>11.1%}"
                  f"{r['gerceklesen']:>9.1%}{r['acik']:>+9.1%}{aralik:>22}"
                  f"{'EVET' if r['sifir_disinda'] else 'hayir':>11}")
        print(f"\n  SEZON ISARETI — BANKO REJIMI ({b['referans']}; Ö3 bu "
              f"sinavda dusmustu)")
        print(f"{'sezon':>16}{'mac':>8}{'soylenen':>11}{'gercek':>9}"
              f"{'acik':>9}{'Wilson %95':>22}{'p disinda':>11}")
        for r in b["sezonlar"]:
            aralik = f"[{r['wilson_alt']:.1%}, {r['wilson_ust']:.1%}]"
            print(f"{r['sezon']:>16}{r['mac']:>8,}{r['p']:>11.1%}"
                  f"{r['gerceklesen']:>9.1%}{r['acik']:>+9.1%}{aralik:>22}"
                  f"{'EVET' if r['sifir_disinda'] else 'hayir':>11}")
        print("\nOKUMA: sapma UC yontemde de duruyorsa arindirma eseri DEGIL,")
        print("piyasa yanliligidir ve normalizasyonla kapanmaz (§3.61: global")
        print("bir kalibrasyon duzeltmesi de yetmedi).")
        return 0

    if a.kapsama:
        g = kapsama_acigi(a.butce or 2000.0, a.garanti)
        if a.json:
            print(json.dumps(g, ensure_ascii=False, default=str))
            return 0
        t = g["tumu"]
        print(f"\nKapsama acigi — {g['garanti']}-garanti · "
              f"{g['butce']:,.0f} TL · hedef P(k <= {g['esik']}) · "
              f"{t['hafta']} hafta")
        print(f"  model diyor  : {t['model_p']:.1%}")
        print(f"  gerceklesen  : {t['gerceklesen']:.1%}")
        print(f"  ACIK         : {t['acik']:+.1%}  "
              f"[{t['alt']:+.1%}, {t['ust']:+.1%}]  "
              f"{'SIFIR DISINDA' if t['sifir_disinda'] else 'sifiri kesiyor'}")
        print(f"  §3.46 bagimlilik tavani: kuyrugu en fazla "
              f"%{g['bagimlilik_tavani'] * 100:.0f} sisirebilir")
        print(f"\nMAC DUZEYI — optimizatorun q'su ile GERCEKLESEN kacma "
              f"({g['mac']:,} mac; ucluler haric, q=0)")
        print(f"{'q araligi':>16}{'mac':>7}{'model q':>10}{'gercek':>9}"
              f"{'acik':>9}{'Wilson %95':>22}{'q disinda':>11}")
        for r in g["q_dilim"]:
            etiket = f"{r['alt_sinir']:.3f}-{r['ust_sinir']:.3f}"
            aralik = f"[{r['wilson_alt']:.1%}, {r['wilson_ust']:.1%}]"
            print(f"{etiket:>16}{r['mac']:>7}{r['q']:>10.1%}"
                  f"{r['gerceklesen']:>9.1%}{r['acik']:>+9.1%}{aralik:>22}"
                  f"{'EVET' if r['sifir_disinda'] else 'hayir':>11}")
        print("  UYARI: dilimler sinanan degiskene gore siralaniyor; "
              "ortalamaya donus\n  ayni imzayi uretebilir. Siralamadan "
              "bagimsiz kesit asagida.")
        print("\nISARET SAYISINA GORE (siralama eseri OLAMAZ — ayrik karar)")
        print(f"{'seviye':>16}{'mac':>7}{'model q':>10}{'gercek':>9}"
              f"{'acik':>9}{'Wilson %95':>22}{'q disinda':>11}")
        for r in g["seviye"]:
            aralik = f"[{r['wilson_alt']:.1%}, {r['wilson_ust']:.1%}]"
            print(f"{r['ad']:>16}{r['mac']:>7}{r['q']:>10.1%}"
                  f"{r['gerceklesen']:>9.1%}{r['acik']:>+9.1%}{aralik:>22}"
                  f"{'EVET' if r['sifir_disinda'] else 'hayir':>11}")
        for ad, baslik in (("sezon", "SEZON"), ("favori_gucu", "FAVORI GUCU"),
                           ("model_p", "MODEL P")):
            print(f"\n{baslik}")
            print(f"{'grup':>12}{'hafta':>7}{'model':>9}{'gercek':>9}"
                  f"{'acik':>9}{'%95 aralik':>22}{'sifir disi':>12}")
            for r in g[ad]:
                etiket = (str(r["sezon"]) if ad == "sezon"
                          else f"{r['alt_sinir']:.3f}-{r['ust_sinir']:.3f}")
                aralik = f"[{r['alt']:+.1%}, {r['ust']:+.1%}]"
                print(f"{etiket:>12}{r['hafta']:>7}{r['model_p']:>9.1%}"
                      f"{r['gerceklesen']:>9.1%}{r['acik']:>+9.1%}"
                      f"{aralik:>22}"
                      f"{'EVET' if r['sifir_disinda'] else 'hayir':>12}")
        return 0

    if a.kalibrasyon:
        c = kalibrasyon_kiyasi(a.butce or 2000.0, a.garanti,
                               kademe=a.kalibrasyon)
        if a.json:
            print(json.dumps(c, ensure_ascii=False, default=str))
            return 0
        print(f"\nKalibrasyon — piyasa ↔ kalibre_{c['kademe']} · "
              f"{c['garanti']}-garanti · {c['butce']:,.0f} TL · "
              f"{c['hafta']} hafta")
        print(f"\n{'kaynak':>16}{'hafta':>7}{'geri donus':>12}{'odul>0':>8}"
              f"{'kacaksiz':>10}{'ort kacak':>11}{'ort kolon':>11}"
              f"{'ort P':>9}")
        for k in c["kollar"]:
            print(f"{k['kaynak']:>16}{k['hafta']:>7}{k['roi']:>11.1%}"
                  f"{k['odul_alan_hafta']:>8}{k['kacaksiz_hafta']:>10}"
                  f"{k['ort_kacak']:>11.2f}{k['ort_kolon']:>11.0f}"
                  f"{k['ort_p_hedef']:>9.4f}")
        print(f"\nESLESTIRILMIS FARK (hafta duzeyi bootstrap %95; "
              f"kuyruksuz = en iyi {KUYRUK_HAFTA} hafta cikarilmis)")
        print(f"{'olcu':>12}{'ort':>11}{'%95 aralik':>26}{'sifir disi':>12}"
              f"{'kuyruksuz':>11}{'sifir disi':>12}")
        for ad, f in c["farklar"].items():
            aralik = f"[{f['alt']:+.5f}, {f['ust']:+.5f}]"
            print(f"{ad:>12}{f['ort']:>+11.5f}{aralik:>26}"
                  f"{'EVET' if f['sifir_disinda'] else 'hayir':>12}"
                  f"{f['kuyruksuz_ort']:>+11.5f}"
                  f"{'EVET' if f['kuyruksuz_sifir_disinda'] else 'hayir':>12}")
        pa = c["p_ayrisimi"]
        print("\nE3 TUZAGI — P(hedef) farkinin ne kadari secim DEGISMEDEN?")
        print(f"  serbest (secim degisebilir): {pa['serbest']:+.5f}")
        print(f"  sekil sabit (salt keskinlik): {pa['sekil_sabit']:+.5f}")
        if pa["keskinlik_payi"] is not None:
            print(f"  keskinlik payi             : {pa['keskinlik_payi']:.1%}")
        print(f"\nisareti degisen hafta: {c['isareti_degisen_hafta']}/"
              f"{c['hafta']} · ayni sekil VE ayni kacak: "
              f"{c['ayni_sekil_ve_kacak']}/{c['hafta']}")
        print("\nDURMA KURALI (olcumden ONCE yazildi): omurga ancak KACAKSIZ "
              "hafta VE\ngercek kolon ROI farklarinin ikisi de %95 araligin "
              "TAMAMIYLA sifirin\nustunde kalirsa degisir. Yalniz P(hedef) "
              "buyumesi GECMEZ.")
        print(f"\nVERDIKT: {'GECTI' if c['gecti'] else 'GECMEDI'}")
        return 0

    if a.omurga:
        o = omurga_kiyasi(a.butce or 2000.0, a.garanti, aday=a.omurga)
        if a.json:
            print(json.dumps(o, ensure_ascii=False, default=str))
            return 0
        print(f"\nOmurga fiyati — {o['omurga']} ↔ {o['aday']} · "
              f"{o['garanti']}-garanti · {o['butce']:,.0f} TL · "
              f"{o['hafta']} ORTAK hafta")
        print(f"\n{'kaynak':>8}{'kesit':>7}{'ortak':>7}{'geri donus':>12}"
              f"{'odul>0':>8}{'ort kolon':>11}{'ort P':>8}{'ort kacak':>11}")
        for k in o["kollar"]:
            print(f"{k['kaynak']:>8}{k['kesit_hafta']:>7}{k['hafta']:>7}"
                  f"{k['roi']:>11.1%}{k['odul_alan_hafta']:>8}"
                  f"{k['ort_kolon']:>11.0f}{k['ort_p_hedef']:>8.4f}"
                  f"{k['ort_kacak']:>11.2f}")
        print(f"\nSEZON ISARETI ({o['aday']} kapsamasi sezona gore degisir)")
        print(f"{'sezon':>10}{'hafta':>7}{'d kacak':>10}{'d ROI':>10}")
        for sz in o["sezonlar"]:
            print(f"{sz['sezon']:>10}{sz['hafta']:>7}{sz['d_kacak']:>+10.3f}"
                  f"{sz['d_roi']:>+10.1%}")
        print(f"\nayni sekil VE ayni kacak: {o['ayni_sekil_ve_kacak']}/"
              f"{o['hafta']} hafta")
        print(f"\nESLESTIRILMIS FARK ({o['aday']} − {o['omurga']}), "
              "hafta bootstrap %95")
        for alan, f in o["farklar"].items():
            print(f"  {alan:>8}: {f['ort']:>+9.5f} "
                  f"[{f['alt']:>+9.5f}, {f['ust']:>+9.5f}]  "
                  f"{'SIFIR DISINDA' if f['sifir_disinda'] else 'sifiri kesiyor'}"
                  f"  | kuyruksuz {f['kuyruksuz_ort']:>+9.5f} "
                  f"[{f['kuyruksuz_alt']:>+9.5f}, {f['kuyruksuz_ust']:>+9.5f}]")
        ay = o["p_ayrisimi"]
        print(f"\nP(hedef) AYRISIMI — {ay['hafta']} hafta")
        print(f"  serbest (her fiyat kendi kuponunu kurar): "
              f"{ay['serbest']:>+9.5f}")
        print(f"  sekil sabit ({o['omurga']} kuponu, {o['aday']} olasiligi): "
              f"{ay['sekil_sabit']:>+9.5f}")
        if ay["keskinlik_payi"] is not None:
            print(f"  -> farkin %{100 * ay['keskinlik_payi']:.0f}'i SECIM "
                  "DEGISMEDEN, yalnizca olasiligin keskinliginden geliyor")
        kk, kc = o["farklar"]["kacak"], o["farklar"]["kacaksiz"]
        print("\nDURMA KURALI (olcumden ONCE yazildi): omurga ancak "
              "GERCEKLESEN kacak\nfarki %95 araligin TAMAMIYLA sifirin "
              "ALTINDA kalirsa degisir. P(hedef) buyumesi GECMEZ.")
        print(f"VERDIKT: "
              f"{'GECTI' if kk['ust'] < 0.0 else 'GECMEDI'}"
              f"  (kacaksiz hafta farki {kc['ort']:+.5f} "
              f"[{kc['alt']:+.5f}, {kc['ust']:+.5f}])")
        return 0

    if a.hedef:
        h = hedef_kademe_kiyasi(a.butce or 2000.0, a.garanti)
        if a.json:
            print(json.dumps(h, ensure_ascii=False, default=str))
            return 0
        print(f"\nHedef kademe — {h['garanti']}-garanti · "
              f"{h['butce']:,.0f} TL · {h['hafta']} hafta · GERCEK kolon odulu")
        print(f"\n{'hedef':>7}{'geri donus':>12}{'odul>0':>8}"
              f"{'ort kolon':>11}{'ort P(hedef)':>14}{'sekil':>10}")
        for k in h["kollar"]:
            print(f"{k['kademe']:>7}{k['roi']:>11.1%}{k['odul_alan_hafta']:>8}"
                  f"{k['ort_kolon']:>11.0f}{k['ort_p_hedef']:>14.4f}"
                  f"{len(k['sekiller']):>10}")
        print("\nESLESTIRILMIS ROI FARKI (hafta duzeyi bootstrap %95)")
        for f in h["farklar"]:
            print(f"  {f['kademe']:>7}: {f['ort']:>+8.5f} "
                  f"[{f['alt']:>+8.5f}, {f['ust']:>+8.5f}]  "
                  f"{'SIFIR DISINDA' if f['sifir_disinda'] else 'sifiri kesiyor'}"
                  f"  | kuyruksuz {f['kuyruksuz_ort']:>+8.5f} "
                  f"[{f['kuyruksuz_alt']:>+8.5f}, {f['kuyruksuz_ust']:>+8.5f}]")
        print(f"\nBASABAS — hedef {HEDEF_KADEME}, kacaga gore (gerceklesen)")
        print(f"{'kacak':>7}{'hafta':>7}{'medyan':>9}{'ortalama':>10}"
              f"{'odul>0':>8}{'maliyeti karsiliyor':>21}")
        for k, v in h["basabas"].items():
            print(f"{k:>7}{v['hafta']:>7}{v['medyan_roi']:>8.2f}x"
                  f"{v['ortalama_roi']:>9.2f}x{v['odul_alan_hafta']:>8}"
                  f"{'EVET' if v['maliyeti_karsiliyor'] else 'hayir':>21}")
        return 0

    butceler = (a.butce,) if a.butce else BUTCELER
    kesit = kupon_kesiti()
    anom = anormal_hafta_anahtarlari()
    cikti: list[dict[str, Any]] = []
    for tl in butceler:
        satirlar = []
        for h in kesit:
            r = hafta_karnesi(h["probs"], h["gercek"], h["tablo"], tl,
                              a.garanti)
            if r is None:
                continue
            r["sezon"] = h["sezon"]
            r["hafta_no"] = h["hafta"]
            r["anormal"] = (h["sezon"], h["hafta"]) in anom
            satirlar.append(r)
        if not satirlar:
            continue
        k = karne(satirlar)
        temiz = karne([r for r in satirlar if not r["anormal"]])
        cikti.append({"butce": tl, "tum": k, "anormalsiz": temiz})

    if a.json:
        print(json.dumps(cikti, ensure_ascii=False))
        return 0

    print(f"\nPara karnesi — {a.garanti}-garanti · GARANTI TABANI (alt sinir)")
    ilk_tum: dict[str, Any] = cikti[0]["tum"]
    ilk_temiz: dict[str, Any] = cikti[0]["anormalsiz"]
    print(f"kesit: {ilk_tum['hafta']} hafta · anormal: "
          f"{ilk_tum['hafta'] - ilk_temiz['hafta']}")
    print(f"\n{'butce':>8}{'odul>0':>8}{'medyan':>9}{'ortalama':>10}"
          f"{'kuyruksuz':>11}{'en iyi 5 payi':>15}{'kolon':>8}")
    for c in cikti:
        ktum: dict[str, Any] = c["tum"]
        print(f"{c['butce']:>8,.0f}{ktum['odul_alan_hafta']:>8}"
              f"{ktum['medyan_roi']:>9.1%}{ktum['ortalama_roi']:>10.1%}"
              f"{ktum['kuyruksuz_ortalama_roi']:>11.1%}"
              f"{ktum['en_iyi_bes_hafta_payi']:>15.1%}{ktum['ort_kolon']:>8.0f}")

    print("\nSEZON KIRILIMI (enflasyon: sezonlar toplanamaz)")
    for c in cikti:
        print(f"\n  {c['butce']:,.0f} TL")
        print(f"  {'sezon':>9}{'hafta':>7}{'medyan':>9}{'ortalama':>10}"
              f"{'toplam odul':>15}")
        sezonlar: list[dict[str, Any]] = c["tum"]["sezonlar"]
        for s in sezonlar:
            print(f"  {s['sezon']:>9}{s['hafta']:>7}{s['medyan_roi']:>9.1%}"
                  f"{s['ortalama_roi']:>10.1%}{s['toplam_odul']:>15,.0f}")

    print(f"\n{ilk_tum['uyari']}")
    return 0


# ─── canlı hafta karnesi — öngörülen ↔ gerçekleşen ────────────────────────

#: Canlı hafta yüklerinin kökü.
CANLI_KOK = Path(__file__).resolve().parent.parent / "data" / "super_toto"


def canli_hafta(sezon: str, hafta: int,
                kok: Any = None) -> dict[str, Any] | None:
    """Elle girilen hafta yükünü karne için okunur hâle getirir.

    Yük `data/super_toto/<sezon>/hafta_NN.json`'dır ve **elle girilen kayıt**
    sınıfındandır. Karne için gereken beş şeyi çıkarır: olasılıklar (marj
    arındırılmış), oynanma payları (varsa), gerçek sonuç, resmî kademe
    tablosu ve **fiyatın künyesi**.

    Künye taşınmak zorunda çünkü **ölçek haftadan haftaya değişiyor**:
    1. ve 2. haftada ana fiyat ~%18 marjlı iddaa oranıydı, 3. haftada
    ~%4,6 marjlı Pinnacle. Haftalar arası olasılık karşılaştırması bu
    farkı hesaba katmadan yapılamaz ve karne bunu satırında söyler.
    """
    from .odds import implied_probs

    d = (Path(kok) if kok else CANLI_KOK) / sezon / f"hafta_{hafta:02d}.json"
    if not d.exists():
        return None
    govde = json.loads(d.read_text(encoding="utf-8"))
    meta = govde.get("meta") or {}
    maclar = govde.get("matches") or []
    if len(maclar) != 15:
        return None

    probs: list[dict[str, float]] = []
    play: list[dict[str, float]] = []
    for m in maclar:
        oran = m.get("odds") or {}
        try:
            probs.append(implied_probs({s: float(oran[s]) for s in SEMBOLLER}))
        except (KeyError, TypeError, ValueError):
            return None
        ham = m.get("play_pct") or {}
        if all(s in ham for s in SEMBOLLER):
            toplam = sum(float(ham[s]) for s in SEMBOLLER) or 1.0
            play.append({s: float(ham[s]) / toplam for s in SEMBOLLER})

    sonuc = (meta.get("results") or "").strip()
    tablo: dict[int, dict[str, Any]] = {}
    for x in ((meta.get("payout") or {}).get("tiers") or []):
        tablo[int(x["correct"])] = x
    return {
        "sezon": sezon, "hafta": hafta,
        "probs": probs,
        "play": play if len(play) == 15 else None,
        "gercek": list(sonuc) if len(sonuc) == 15 else None,
        "tablo": tablo,
        "payout": meta.get("payout"),
        "fiyat_kunyesi": meta.get("odds_kind") or meta.get("odds_source") or "?",
        "program": meta.get("program", ""),
        "girildi": meta.get("entered_at", ""),
    }


def _basabas_kacak(tablo: dict[int, dict[str, Any]], garanti: int,
                   maliyet: float) -> int | None:
    """Hangi kaçak seviyesine kadar garanti tabanı maliyeti karşılıyor.

    Taban `k` kaçakta **bir** kolonu `garanti − k` kademesinde sayar. Bu
    fonksiyon o kolonun ödülünün maliyeti karşıladığı **en büyük** `k`'yi
    döndürür; hiçbiri karşılamıyorsa `None`.

    Sayı elle yazılmaz: `maliyet` `getiri.KOLON_BEDELI`den, ödül haftanın
    **kendi** resmî tablosundan gelir. İkisinden biri değişirse bu sayı da
    değişir — bekçisi `test_karne.py::test_basabas_kacak_ELLE_YAZILMAZ`.

    Ölçülen alt sınırdır (`gercek_kolon_dagilimi` 2,39 kat gevşek olduğunu
    gösterdi, §3.56), yani gerçek başabaş seviyesi bundan **büyük** olabilir.
    """
    en_iyi: int | None = None
    for k in range(garanti - HEDEF_KADEME + 1):
        if _odul(tablo, garanti - k) >= maliyet > 0.0:
            en_iyi = k
    return en_iyi


def canli_karne_satiri(sezon: str, hafta: int, butce_tl: float,
                       garanti: int = VARSAYILAN_GARANTI,
                       kok: Any = None) -> dict[str, Any] | None:
    """Bir canlı haftanın karne satırı: **öngörülen ↔ gerçekleşen**.

    ─── Bu bir tahmin KAYDI değildir ve öyle etiketlenir ─────────────────

    Plan, o haftanın **kupon öncesi** girdilerinden (oran + oynanma payı,
    `entered_at`) **bugünkü motorla** yeniden türetilir. Sızıntı yoktur —
    girdiler sonuç girilmeden önce kaydedilmiştir (`entered_at` <
    `results_entered_at`) ve kalabalık modeli 2026/27'yi hiç görmeyen 112
    tarihsel hafta üzerinde kestirildi. Ama bu, sonuç görülmeden
    **dondurulmuş** bir kayıt da değildir: motor o gün bugünkü hâlinde
    değildi. Satır `tur` alanında bunu söyler.

    Gerçekleşen taraf `hafta_karnesi` ile aynı garanti tabanını kullanır:
    `k` kaçakta **bir** kolon `garanti − k` kademesinde. Alt sınırdır.
    """
    h = canli_hafta(sezon, hafta, kok)
    if h is None:
        return None
    plan = sistem_secimi(h["probs"], butce_tl, garanti=garanti)
    if plan is None:
        return None

    from .getiri import beklenen_tl, kademe_havuzlari
    from .kalabalik import OLCULEN, oynanma_paylari
    from .secim import hedef_olasiligi

    oynanma = h["play"] or oynanma_paylari(h["probs"], OLCULEN)
    havuzlar = kademe_havuzlari(h["payout"])
    satir: dict[str, Any] = {
        "sezon": sezon, "hafta": hafta, "program": h["program"],
        "fiyat_kunyesi": h["fiyat_kunyesi"], "girildi": h["girildi"],
        "garanti": garanti, "butce_tl": butce_tl,
        "kolon": plan.bedel, "maliyet": plan.bedel * KOLON_BEDELI,
        "banko": plan.banko, "cift": plan.cift, "uclu": plan.uclu,
        "p_hedef": plan.p_hedef,
        # `p_hedef` = `P(k ≤ eşik)` ve o olasılık **iki farklı olayı
        # topluyor**: 13-garantide `k=0` 13. kademeyi verir ve maliyeti
        # karşılar, `k=1` 12'yi verir ve karşılamaz (karnenin kendi kaydı:
        # 2. hafta 12 tutturdu −181 TL, 3. hafta 12 tutturdu −390 TL).
        # Ödeyen olayın olasılığı bu yüzden ayrı durur.
        "p_kacak_sifir": hedef_olasiligi(h["probs"], plan.secimler, 0),
        "oynanma_kaynagi": "kayit" if h["play"] else "model",
        "beklenen_tl": (beklenen_tl(h["probs"], oynanma, plan.secimler, {},
                                    havuzlar, garanti, RAKIP_KOLON)
                        if havuzlar else None),
        "tur": "yeniden turetildi (dondurulmus kayit DEGIL)",
        "picks": plan.picks,
    }
    if h["gercek"] and h["tablo"]:
        kacak = sum(1 for sec, c in zip(plan.secimler, h["gercek"])
                    if c not in sec)
        kademe = garanti - kacak
        satir.update({
            "kacak": kacak, "kademe": kademe,
            "odul": _odul(h["tablo"], kademe),
            "sonuc": "".join(h["gercek"]),
            # Başabaş kaçak seviyesi — o haftanın KENDİ ikramiye
            # tablosundan, medyan alınmadan. Sezonlar arası medyan almak
            # ölçümü kirletirdi (nominal TL dört sezonda 72 kat büyümüş,
            # modül başlığı). `None` = kaçaksız hafta bile maliyeti
            # karşılamıyor.
            "basabas_kacak": _basabas_kacak(
                h["tablo"], garanti, satir["maliyet"]),
        })
        satir["net"] = satir["odul"] - satir["maliyet"]
    return satir


#: Karnenin `beklenen_tl` hesabında kullandığı rakip kolon sayısı.
#:
#: `kalabalik.havuz_sinavi` 2025/26'da haftalık **10–19 milyon** kolon ima
#: ediyor (model ve sezona göre). Yuvarlak bir orta değer alınıyor ve
#: **varsayım olarak etiketleniyor**: `beklenen_tl` bu sayıya `1/(N·q)`
#: mertebesinde duyarlıdır, yani mutlak TL değil **karşılaştırma** için
#: okunmalıdır.
RAKIP_KOLON = 15_000_000


# ─── E1: tabanın gevşekliği — gerçek kolon dağılımı ──────────────────────

def gercek_kolon_dagilimi(secimler: Sequence[Sequence[str]],
                          gercek: Sequence[str],
                          hedef_kolon: int | None = None
                          ) -> dict[int, float] | None:
    """Kuponun **gerçek** kolonlarını üretip kademe dağılımını sayar.

    ─── Niçin bu, fişe gerek bırakmıyor ──────────────────────────────────

    `hafta_karnesi` **garanti tabanını** kullanır: `k` kaçakta *bir* kolon
    `G−k` kademesinde. Tabanın ne kadar gevşek olduğu bilinmiyordu ve
    kapatmanın tek yolu ST EXTRA fişi sanılıyordu.

    Değil: **14-garanti için motor kolonları kendisi üretebiliyor**
    (`engines.run_auto`). Üretilen kaplama gerçek oynanan sistemle birebir
    aynı olmayabilir — satıcının kodu daha ucuz (aynı şekilde 168 kolon,
    motorunki 216) — ama tabanın **mertebesini** verir ve soru zaten oydu.

    Dönen sözlük `{kademe: kolon}`; `hedef_kolon` verilirse sayılar o
    ölçeğe indirgenir (motorun 216'sından tablonun 168'ine).

    ─── Ölçülen: taban **2,39 kat** gevşek ───────────────────────────────

    114 hafta · 14-garanti · 2.000 TL bütçe::

        maliyet              191.520 TL
        garanti tabanı ödül   19.354 TL   geri dönüş %10,1
        GERÇEK kolon ödülü    46.252 TL   geri dönüş %24,2

    Ve gevşeklik kademeye göre çok farklı: garanti kademesinde çokluk
    **≈1** (kaplama kodu orada sıkı), ama para 12'de ve orada `k=0` iken
    ~21, `k=1` iken ~6, `k=2` iken ~1 kolon var. Yani taban en çok
    **iyi giden haftaları** eksik sayıyor.

    `None` döner: 14-garanti dışı bir şekil ya da motor kaplama üretemezse.
    """
    from .core import Encoder
    from .engines import engine_params, run_auto

    enc = Encoder(list(secimler))
    banko_dogru = sum(1 for i, sym in zip(enc.banko_pos, enc.banko_syms)
                      if gercek[i] == sym)
    try:
        kolonlar = run_auto(enc, engine_params())["cols"]
    except Exception:  # motor kaplama uretemezse olcum yok
        return None
    if not kolonlar:
        return None
    sayim: dict[int, float] = {}
    for kolon in kolonlar:
        dogru = banko_dogru
        for j, v in enumerate(kolon):
            if enc.variable_syms[j][v] == gercek[enc.variable_pos[j]]:
                dogru += 1
        sayim[dogru] = sayim.get(dogru, 0.0) + 1.0
    if hedef_kolon:
        olcek = hedef_kolon / len(kolonlar)
        sayim = {k: v * olcek for k, v in sayim.items()}
    return sayim


def gercek_odul(dagilim: dict[int, float] | None,
                tablo: dict[int, dict[str, Any]],
                hedef_kademe: int = HEDEF_KADEME) -> float | None:
    """Gerçek kolon dağılımının resmî ödül tablosundaki karşılığı."""
    if not dagilim:
        return None
    toplam = 0.0
    for kademe, kolon in dagilim.items():
        if kademe < hedef_kademe:
            continue
        satir = tablo.get(kademe)
        if satir and satir.get("prize") is not None:
            toplam += kolon * float(satir["prize"])
    return toplam


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
