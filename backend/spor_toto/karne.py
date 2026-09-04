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
  aynıdır ve eşleştirilmiş farkta büyük ölçüde götürür.
* **Garantiler arasında** geçerli DEĞİLDİR. O karşılaştırma ancak gerçek
  kolon listeleriyle yapılır ve bu modül onu yapmaz; `gecerli_kiyas()`
  çağrıldığında bunu açıkça söyler.

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
"""
from __future__ import annotations

import argparse
import json
import random
from collections.abc import Sequence
from typing import Any

from .havuz import arsiv_haftalari
from .secim import sistem_secimi
from .sistem import HEDEF_KADEME, VARSAYILAN_GARANTI

#: Ölçülen bütçe basamakları (TL). `kademe_analizi.BUTCELER` kolon
#: cinsindendir ve bu modül TL konuşur (`sistem` tablosu TL taşıyor).
BUTCELER: tuple[float, ...] = (500.0, 1000.0, 1500.0, 2000.0, 3000.0, 5000.0)

#: Bootstrap yeniden örnekleme adedi — `evaluate` ile aynı büyüklük sınıfı.
BOOTSTRAP = 20_000

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
    maliyet = plan.bedel * 10.0
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
    rnd = random.Random(tohum)
    m = len(fark)
    dag = sorted(sum(fark[rnd.randrange(m)] for _ in range(m)) / m
                 for _ in range(n))
    return dag[int(0.025 * n)], dag[int(0.975 * n)]


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
    ars = ikramiye_tablolari(dizin)
    w12 = [float(t[12]["winners"]) for t in ars.values()
           if 12 in t and t[12].get("winners") is not None]
    if not w12:
        return set()
    esik = _medyan(w12) / 10.0
    return {k for k, t in ars.items()
            if 12 in t and t[12].get("winners") is not None
            and t[12]["winners"] < esik}


def kupon_kesiti(dizin: Any = None) -> list[dict[str, Any]]:
    """Ölçümün kesiti: **on beş maçında da oran olan VE ikramiyesi ilan
    edilmiş** haftalar.

    İki arşivin kesişimidir ve projenin bugüne kadar birleştirmediği yer
    tam olarak burasıdır: `data/odds/*.csv` kuponun maçlarını ve piyasa
    oranını, `data/sportoto_arsiv/*.json` o haftanın **gerçek** kademe
    tablosunu taşıyor.
    """
    from .core import SEMBOLLER
    from .odds import load_odds, match_1x2

    ars = ikramiye_tablolari(dizin)
    out: list[dict[str, Any]] = []
    for sezon in sorted({s for s, _ in ars}, reverse=True):
        try:
            satirlar = load_odds(sezon=sezon)
        except OSError:
            continue
        haftalik: dict[int, list[tuple[dict[str, Any], str]]] = {}
        for r in satirlar:
            b = match_1x2(r)
            if b and r.get("code") in SEMBOLLER:
                haftalik.setdefault(r["week"], []).append((b, r["code"]))
        for w, lst in sorted(haftalik.items()):
            if len(lst) != 15 or (sezon, w) not in ars:
                continue
            out.append({
                "sezon": sezon, "hafta": w,
                "probs": [b["probs"] for b, _ in lst],
                "gercek": [c for _, c in lst],
                "tablo": ars[(sezon, w)],
            })
    return out


def _main(argv: list[str] | None = None) -> int:  # pragma: no cover - elle
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--garanti", type=int, default=VARSAYILAN_GARANTI)
    ap.add_argument("--butce", type=float, default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
