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
    from .havuz import anormal_haftalar

    return anormal_haftalar(dizin)


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
        hafta += 1
    if not hafta or taban_odul <= 0.0:
        return {"hafta": hafta, "maliyet": maliyet, "taban_odul": taban_odul,
                "gercek_odul": gercek_toplam, "kat": None, "kat_ham": None,
                "kacak_kolon": {}}
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
    }


def _main(argv: list[str] | None = None) -> int:  # pragma: no cover - elle
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--garanti", type=int, default=VARSAYILAN_GARANTI)
    ap.add_argument("--butce", type=float, default=None)
    ap.add_argument("--taban", action="store_true",
                    help="tabanin gevsekligini olc (yalniz 14-garanti)")
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

    oynanma = h["play"] or oynanma_paylari(h["probs"], OLCULEN)
    havuzlar = kademe_havuzlari(h["payout"])
    satir: dict[str, Any] = {
        "sezon": sezon, "hafta": hafta, "program": h["program"],
        "fiyat_kunyesi": h["fiyat_kunyesi"], "girildi": h["girildi"],
        "garanti": garanti, "butce_tl": butce_tl,
        "kolon": plan.bedel, "maliyet": plan.bedel * KOLON_BEDELI,
        "banko": plan.banko, "cift": plan.cift, "uclu": plan.uclu,
        "p_hedef": plan.p_hedef,
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
