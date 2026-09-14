"""Kaç maçlık **kesin bilgi** kaç puan eder — model ekseninin para birimi.

`ufuk_kiyasi.py --serbest` kombinatorik eksenin tavanını verdi: aynı bütçeyle
en olası `N` kolonu doğrudan oynamak. O tavan aşılamaz, yani bütün arama /
algoritma / donanım işinin kalan payı bellidir. Geriye tek bir eksen kalır:
**olasılıkların kendisi**.

O eksenin büyüklüğü bilinir ama para birimi yoktur: "Brier'i 0,001 iyileştir"
bir sayıdır, hedefte ne ettiği değil. Bu betik çeviriyi yapar ve ölçüyü
kimsenin yanlış anlayamayacağı bir birime koyar:

    bir haftada k maçın sonucunu KESİN bilseydik, üç aylık hedef ne olurdu?

`k = 0` bugünkü bilgi düzeyidir. `k = 15` hedefi %100 yapar. Aradaki eğri,
"daha iyi model" arayışının **en iyi ihtimalle** ne satın aldığını söyler.

─── Neden bu üst sınırdır, bir tahmin değil ──────────────────────────────

Üç yerden birden sınır:

1. **Kolon kümesi serbest.** Her `k` için tavan satırı kullanılır (en olası
   `N` kolon), yani kombinatorik kayıp sıfır sayılır.
2. **Bilgi kesindir.** Gerçek sembole olasılık 1 verilir. Hiçbir model bunu
   veremez; en iyi model bu sınıra yaklaşır.
3. **Maçları kâhin seçer.** Açılan `k` maç, o hafta **en belirsiz** olanlar
   (favori olasılığı en küçük). Belirsizliği en çok azaltan seçim budur.

Üçü birden şunu söyler: eğri **yukarıdan** sınırlıyor. Gerçek bir model
iyileştirmesi bu eğrinin altında kalır — o yüzden eğri düşükse eksen
ölçülmeden küçülür, yüksekse aramanın değeri sayıyla gösterilmiş olur.

─── Neden "bilinen maç sayısı" doğru birim ───────────────────────────────

Brier'in hedefte ne ettiği doğrusal değil: §3.23 piyasanın toplam
güvenilirlik borcunu 0,00042 ölçtü, denenen etkiler onun üstünde kaldı ve
hiçbiri geçmedi. Yani "Brier'i şu kadar iyileştir" cümlesi bugün **boş bir
çek**. "Haftada bir maçı kesin bil" cümlesi ise boş değil ve eğri onu
fiyatlar.

**Kapsam sınırı — bu eğri bir davet değildir.** `k` maçı "kesin bilmek"
burada bir ÜST SINIR kurgusudur, aranacak bir kaynak değil. Meşru bilgi
(sakatlık/kadro haberi, hava, saha, motivasyon) kupon kapandığında henüz
yoktur — kupon ilk maçtan önce kapanır, kadrolar ilk vuruşta belli olur
(§3.36'nın eğitim/servis ayrışması). Meşru olmayan bilgi (iç bilgi, şike)
suçtur ve bu proje onu aramaz; eğride yeri, aranacak bir yer olduğu için
değil, **aranmayacak olanın bedelini de ölçmek** gerektiği içindir.

    cd backend && python scripts/bilgi_esnekligi.py --butce 21000
    cd backend && python scripts/bilgi_esnekligi.py --butce 21000 --k 0 1 2

Ölçüm 114 tam hafta üzerinde koşar ve hafta başına `len(k) × ~1 sn` sürer.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.coklu_kiyasi import VARSAYILAN_BUTCE, hafta_probs
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from scripts.tahsis_kiyasi import serbest_kume
from spor_toto.core import SEMBOLLER
from spor_toto.ufuk import UFUK_HAFTA, en_az_bir, pencereler

#: Kaç maçın açılacağı. 0 bugündür; üst uç 4'te kesiliyor çünkü eğri orada
#: zaten hedefi doyuruyor ve daha fazlası "ne kadar imkânsız" sorusudur.
VARSAYILAN_K = (0, 1, 2, 3, 4)

#: Yayılmış bilgi ızgarası: her maça `λ` kadar gerçek karıştırılır. Üst uç
#: %10'da kesiliyor — ölçülen 11 model ailesinin tamamı `λ ≈ 0,00x`
#: mertebesinde kaldı, yani ızgaranın ilk basamağı bile iyimserdir.
VARSAYILAN_LAMBDA = (0.0, 0.01, 0.02, 0.05, 0.10)


def _ac(probs: list[dict[str, float]], gercek: list[str],
        k: int) -> list[dict[str, float]]:
    """En belirsiz `k` maçın sonucunu **kesin** yapar (kâhin seçimi).

    Belirsizlik ölçüsü favorinin olasılığıdır; en küçük olan en belirsizdir.
    Seçim kâhine bırakıldığı için dönen liste bir ÜST SINIR üretir.
    """
    if k < 1:
        return probs
    sira = sorted(range(len(probs)), key=lambda i: max(probs[i].values()))
    acilan = set(sira[:k])
    return [{s: (1.0 if s == gercek[i] else 0.0) for s in SEMBOLLER}
            if i in acilan else d
            for i, d in enumerate(probs)]


def _karistir(probs: list[dict[str, float]], gercek: list[str],
              lam: float) -> list[dict[str, float]]:
    """Her maça `lam` kadar gerçeği karıştırır — **yayılmış** bilgi.

    `_ac` bir maçı tamamen açar; bu, on beş maçın hepsini biraz açar. İkisi
    aynı ekseni iki uçtan ölçer ve ikincisi "daha iyi bir model" dediğimiz
    şeye daha yakındır: model bir maçı bilmez, hepsinde biraz haklı çıkar.
    """
    if lam <= 0:
        return probs
    return [{s: (1 - lam) * d.get(s, 0.0) + lam * (1.0 if s == gercek[i]
                                                   else 0.0)
             for s in SEMBOLLER}
            for i, d in enumerate(probs)]


def _brier(probs: list[dict[str, float]], gercek: list[str]) -> float:
    """Çok sınıflı Brier — üç sembol üzerinden toplam, maç başına."""
    top = 0.0
    for d, g in zip(probs, gercek):
        pay = sum(d.get(s, 0.0) for s in SEMBOLLER) or 1.0
        top += sum((d.get(s, 0.0) / pay - (1.0 if s == g else 0.0)) ** 2
                   for s in SEMBOLLER)
    return top / len(probs)


def yayilmis(butce: int, pencere: int = UFUK_HAFTA,
             lambdalar: Sequence[float] = VARSAYILAN_LAMBDA) -> dict[str, Any]:
    """`λ` kadar daha iyi bir model hedefte kaç puan eder — Brier'iyle.

    Çıktının asıl sütunu `Brier`dir: ölçülen 11 model ailesinin hiçbiri
    piyasayı 0,001'den fazla geçemedi, o yüzden bu tablo "ne kadar daha iyi
    model gerekir" sorusunu **denenmişin para biriminde** cevaplar.
    """
    haftalar = tam_haftalar(ikramiye_tablolari())
    n = len(haftalar)
    haftalik: dict[float, list[float]] = {a: [] for a in lambdalar}
    brier: dict[float, list[float]] = {a: [] for a in lambdalar}

    for _sezon, _w, lst in haftalar:
        probs, gercek = hafta_probs(lst)
        for a in lambdalar:
            q = _karistir(probs, gercek, a)
            haftalik[a].append(serbest_kume(q, butce)[0])
            brier[a].append(_brier(q, gercek))

    aralik = pencereler(n, pencere)
    satirlar = []
    for a in lambdalar:
        kesin = [en_az_bir(haftalik[a][bas:son]) for bas, son in aralik]
        satirlar.append({
            "lam": a,
            "brier": sum(brier[a]) / n,
            "p_hafta": sum(haftalik[a]) / n,
            "hedef": sum(kesin) / len(kesin),
        })
    taban = satirlar[0] if satirlar else {"hedef": 0.0, "brier": 0.0}
    for r in satirlar:
        r["kazanc_puan"] = r["hedef"] - taban["hedef"]
        r["brier_kazanc"] = taban["brier"] - r["brier"]
        r["puan_basina_mbrier"] = (
            (r["brier_kazanc"] * 1000) / (r["kazanc_puan"] * 100)
            if r["kazanc_puan"] > 0 else 0.0)
    return {"hafta": n, "butce": butce, "pencere": pencere,
            "pencere_sayisi": len(aralik), "satirlar": satirlar}


def bas_yayilmis(c: dict[str, Any]) -> None:
    print(f"\nyayilmis bilgi — her maca `lambda` kadar gercek karistirilir")
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon\n")
    print(f"{'lambda':>8} {'Brier':>9} {'Brier kaz.':>11} "
          f"{'P(15) hafta':>12} {'HEDEF':>8} {'kazanc':>8} "
          f"{'mBrier/puan':>12}")
    for r in c["satirlar"]:
        not_ = "  <- bugun" if r["lam"] == 0 else ""
        print(f"{r['lam']:>8.2f} {r['brier']:>9.4f} "
              f"{r['brier_kazanc']:>11.5f} {r['p_hafta']:>12.3%} "
              f"{r['hedef']:>8.1%} {r['kazanc_puan']:>+8.1%} "
              f"{r['puan_basina_mbrier']:>12.3f}{not_}")
    print("\n'mBrier/puan' = bir HEDEF puani icin gereken Brier iyilesmesi,")
    print("binde cinsinden. Olculen 11 model ailesinin tamami |dBrier| <")
    print("0,001'de kaldi; bu sutun o sayiyi hedef puanina cevirir.")


def kos(butce: int, pencere: int = UFUK_HAFTA,
        k_listesi: Sequence[int] = VARSAYILAN_K) -> dict[str, Any]:
    """Her `k` için haftalık `P(15/15)` tavanı ve hedef kademesi."""
    haftalar = tam_haftalar(ikramiye_tablolari())
    n = len(haftalar)
    haftalik: dict[int, list[float]] = {k: [] for k in k_listesi}

    for _sezon, _w, lst in haftalar:
        probs, gercek = hafta_probs(lst)
        for k in k_listesi:
            haftalik[k].append(serbest_kume(_ac(probs, gercek, k), butce)[0])

    aralik = pencereler(n, pencere)
    satirlar = []
    for k in k_listesi:
        kesin = [en_az_bir(haftalik[k][bas:son]) for bas, son in aralik]
        satirlar.append({
            "k": k,
            "p_hafta": sum(haftalik[k]) / n,
            "p_en_dusuk": min(haftalik[k]),
            "p_en_yuksek": max(haftalik[k]),
            "hedef": sum(kesin) / len(kesin),
            "en_dusuk": min(kesin),
            "en_yuksek": max(kesin),
        })
    taban = satirlar[0]["hedef"] if satirlar else 0.0
    for r in satirlar:
        r["kazanc_puan"] = r["hedef"] - taban
    return {"hafta": n, "butce": butce, "pencere": pencere,
            "pencere_sayisi": len(aralik), "satirlar": satirlar}


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon "
          f"({c['butce'] * 10:,} TL/hafta)")
    print(f"ufuk: {c['pencere']} hafta  ->  {c['pencere_sayisi']} ayrik "
          f"pencere\n")
    print(f"{'bilinen mac':>12} {'P(15) hafta':>12} {'hafta araligi':>17} "
          f"{'HEDEF':>8} {'pencere araligi':>17} {'kazanc':>8}")
    for r in c["satirlar"]:
        not_ = "  <- bugun" if r["k"] == 0 else ""
        print(f"{r['k']:>12} {r['p_hafta']:>12.3%} "
              f"{r['p_en_dusuk']:>7.1%}-{r['p_en_yuksek']:<9.1%} "
              f"{r['hedef']:>8.1%} "
              f"{r['en_dusuk']:>7.1%}-{r['en_yuksek']:<9.1%} "
              f"{r['kazanc_puan']:>+8.1%}{not_}")
    print("\nHER SATIR BIR UST SINIRDIR: kolon kumesi serbest (kombinatorik")
    print("kayip sifir), bilgi KESIN (olasilik 1), ve acilan maclari KAHIN")
    print("secer (en belirsiz olanlar). Gercek bir model iyilestirmesi bu")
    print("egrinin ALTINDA kalir.")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--pencere", type=int, default=UFUK_HAFTA,
                    help="ufuk uzunlugu, hafta (varsayilan 13 ~ uc ay)")
    ap.add_argument("--k", type=int, nargs="+", default=list(VARSAYILAN_K),
                    help="kac mac acilsin (birden cok deger verilebilir)")
    ap.add_argument("--yayilmis", action="store_true",
                    help="ayrica `lambda` kadar daha iyi bir modelin "
                         "hedefte ne ettigini Brier'iyle olc")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    c = kos(a.butce, a.pencere, sorted(set(a.k)))
    y = yayilmis(a.butce, a.pencere) if a.yayilmis else None
    if a.json:
        print(json.dumps({"acik_mac": c, "yayilmis": y}, ensure_ascii=False,
                         indent=1))
        return
    bas(c)
    if y is not None:
        bas_yayilmis(y)


if __name__ == "__main__":  # pragma: no cover
    main()
