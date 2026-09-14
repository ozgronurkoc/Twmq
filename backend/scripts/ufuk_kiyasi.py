"""Hedefin kendisi: **üç ay içinde 15/15** olasılığı (§3.73).

Bu deponun bütün ölçüleri haftalıktır ama sahibinin hedefi haftalık değil:
*"3 ay içinde Spor Toto'da 15/15."* Bu betik o çeviriyi yapar ve üç şeyi
ayrı ayrı ölçer:

1. **Hedefe ulaşma olasılığı**, `spor_toto.ufuk.en_az_bir` ile **kesin**
   (`1 − Π(1 − p_w)`), pencere pencere — tek bir sayı değil bir aralık.
2. **Yaklaşıklığın yanlılığı.** `coklu_kiyasi.py`nin "13 hafta" sütunu
   `1 − (1 − p̄)¹³` yazıyor. Jensen gereği bu gerçek değerin altında kalır;
   bu betik ne kadar altında kaldığını sayıya çevirir.
3. **Zamanlama ekseni** (`--zamanlama`). Haftalar arası `P` dört kat
   ayrışıyor, yani "parayı iyi haftalara yığ" akla geliyor. `ufuk.kahin_tahsisi`
   bunun **tam öngörülü** — yani uygulanamaz — üst sınırını verir. Gerçek
   bir kural ancak onun altında kalabilir, dolayısıyla üst sınır küçükse
   eksen ölçülmeden kapanır.

    cd backend && python scripts/ufuk_kiyasi.py --butce 21000
    cd backend && python scripts/ufuk_kiyasi.py --butce 21000 --zamanlama

─── Okuma kuralı — ölçüm görülmeden yazıldı ─────────────────────────────

`model` sütunu **modelin** sayısıdır ve §3.68'in okuma kuralı burada da
geçerli: havuzlanmış 114 haftada model karamsar çıkmıştı (tek sistemde
beklenen 8,54 ↔ gerçekleşen 15) ama açık 2023/24'ten geliyordu ve 2025/26'da
kapanmıştı. O yüzden `gerçekleşen` sütunu yanında basılıyor ve ikisi
**ayrışırsa** hüküm ikisinin arasındadır, modelin değil.

`gerçekleşen` sütununun kendi sınırı da yazılı: pencere sayısı `114 // H`,
yani 13 haftalık pencerede **8**. Sekiz gözlemle bir olasılık ölçülmez;
o sütun modelin makul olup olmadığına bakar, onu değiştirmez.
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

from scripts.coklu_kiyasi import VARSAYILAN_BUTCE, hafta_probs, isabet
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from scripts.tahsis_kiyasi import kolon_p, serbest_kume
from spor_toto.coklu import coklu_plan_serisi
from spor_toto.ufuk import (
    UFUK_HAFTA,
    en_az_bir,
    kahin_tahsisi,
    ortalamayla,
    pencereler,
)

#: Kıyaslanan kupon tavanları. 1 bugünkü tek sistemdir.
TAVANLAR = (1, 27, 81, 243, 729)

#: Tavan satırının anahtarı. Bir kupon sayısı DEĞİL — bu yüzden `int` değil:
#: tabloda kupon sütununa bir sayı yazmak, oynanabilir bir plan olduğunu
#: ima ederdi. Serbest küme ~4.300 ayrı kutu ister (`coklu.py` başlığı).
SERBEST = "serbest"

#: Ufuk uzunluğu (hafta). 13 ≈ üç ay; sahibinin verdiği süre bu.
VARSAYILAN_PENCERE = UFUK_HAFTA

#: Zamanlama sınavının bütçe ızgarası, haftalık bütçenin katları olarak.
#: `0` bilerek var — "bu haftayı hiç oynama" bir seçenektir ve kâhin onu
#: gerçekten kullanıyor. Üst uç 4 katta kesiliyor: haftada 840.000 TL zaten
#: operasyonun çok ötesinde ve eğri orada düzleşiyor.
ZAMANLAMA_IZGARASI = (0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0)


def kos(butce: int, pencere: int = VARSAYILAN_PENCERE,
        serbest: bool = False) -> dict[str, Any]:
    """Pencere pencere hedefe ulaşma olasılığı — model ve gerçekleşen.

    `serbest=True` tabloya **tavan satırını** ekler: aynı bütçeyle en olası
    `bütçe` kolonu doğrudan oynamak. O satır bir plan değil bir **sınırdır**
    — hiçbir kupon ailesi, hiçbir arama, hiçbir donanım onu geçemez (15/15
    olayları ayrık olduğu için `P = Σ p` ve en büyük `n` toplamı en büyüktür).
    Hedef kademesinde basıldığında, bütün kombinatorik eksenin geriye kalan
    payı **tek bakışta** okunur. Bedeli hafta başına ~1 sn.
    """
    haftalar = tam_haftalar(ikramiye_tablolari())
    n = len(haftalar)
    #: tavan -> hafta başına (p, isabet). `SERBEST` anahtarı sahte bir tavan
    #: değil, ailenin dışıdır — basımda ayrı yazılır.
    anahtarlar: list[int | str] = [*TAVANLAR] + ([SERBEST] if serbest else [])
    haftalik: dict[int | str, list[tuple[float, bool]]] = {
        t: [] for t in anahtarlar}

    for _sezon, _w, lst in haftalar:
        probs, gercek = hafta_probs(lst)
        seri = coklu_plan_serisi(probs, butce, TAVANLAR)
        for t in TAVANLAR:
            plan = seri[t]
            haftalik[t].append((plan.p_onbes, isabet(plan.kuponlar, gercek)))
        if serbest:
            toplam, esik = serbest_kume(probs, butce)
            haftalik[SERBEST].append((toplam, kolon_p(probs, gercek) >= esik))

    aralik = pencereler(n, pencere)
    satirlar = []
    for t in anahtarlar:
        kesin, tutan = [], 0
        for bas, son in aralik:
            dilim = haftalik[t][bas:son]
            kesin.append(en_az_bir([p for p, _i in dilim]))
            tutan += int(any(i for _p, i in dilim))
        p_ort = sum(p for p, _i in haftalik[t]) / n
        yaklasik = ortalamayla(p_ort, pencere)
        haftalik_p = [q for q, _i in haftalik[t]]
        satirlar.append({
            "tavan": t,
            "p_hafta": p_ort,
            "p_en_dusuk": min(haftalik_p),
            "p_en_yuksek": max(haftalik_p),
            "kesin": sum(kesin) / len(kesin),
            "en_dusuk": min(kesin),
            "en_yuksek": max(kesin),
            "yaklasik": yaklasik,
            "yanlilik": sum(kesin) / len(kesin) - yaklasik,
            "tutan_pencere": tutan,
            "isabet_hafta": sum(1 for _p, i in haftalik[t] if i),
        })
    return {"hafta": n, "butce": butce, "pencere": pencere,
            "pencere_sayisi": len(aralik), "satirlar": satirlar}


def zamanlama(butce: int, pencere: int = VARSAYILAN_PENCERE,
              tavan: int = 729) -> dict[str, Any]:
    """Zamanlama ekseninin **üst sınırı**: tam öngörülü tahsis ne getirir?

    Pahalıdır — hafta başına `len(ZAMANLAMA_IZGARASI) − 1` ayrı arama.
    """
    haftalar = tam_haftalar(ikramiye_tablolari())
    egriler: list[list[tuple[int, float]]] = []
    for _sezon, _w, lst in haftalar:
        probs, _gercek = hafta_probs(lst)
        egri: list[tuple[int, float]] = []
        for kat in ZAMANLAMA_IZGARASI:
            c = round(butce * kat)
            egri.append((c, 0.0) if c < 1 else
                        (c, coklu_plan_serisi(probs, c, (tavan,))[tavan].p_onbes))
        egriler.append(egri)

    bir = ZAMANLAMA_IZGARASI.index(1.0)
    satirlar: list[dict[str, Any]] = []
    for bas, son in pencereler(len(egriler), pencere):
        dilim = egriler[bas:son]
        duz = en_az_bir([e[bir][1] for e in dilim])
        sonuc = kahin_tahsisi(dilim, butce * pencere)
        if sonuc is None:
            continue
        kahin, bedeller = sonuc
        satirlar.append({
            "duz": duz, "kahin": kahin, "kazanc": kahin / duz if duz else 0.0,
            "dagilim": [round(b / butce, 2) for b in bedeller],
            "oynanmayan": sum(1 for b in bedeller if b < 1),
        })
    kazanclar = [float(r["kazanc"]) for r in satirlar]
    return {"butce": butce, "pencere": pencere, "tavan": tavan,
            "izgara": list(ZAMANLAMA_IZGARASI), "satirlar": satirlar,
            "kazanc_ort": (sum(kazanclar) / len(kazanclar)
                           if kazanclar else 0.0),
            "kazanc_en_buyuk": max(kazanclar, default=0.0)}


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon "
          f"({c['butce'] * 10:,} TL/hafta)")
    print(f"ufuk: {c['pencere']} hafta  ->  {c['pencere_sayisi']} ayrik "
          f"pencere\n")
    print(f"{'tavan':>7} {'P(15) hafta':>12} {'hafta araligi':>17} "
          f"{'HEDEF (kesin)':>14} {'pencere araligi':>17} {'yaklasik':>9} "
          f"{'yanlilik':>9} {'gozlenen':>10}")
    for r in c["satirlar"]:
        not_ = ("  <- bugun" if r["tavan"] == 1 else
                "  <- TAVAN (plan degil)" if r["tavan"] == SERBEST else "")
        ad = SERBEST if r["tavan"] == SERBEST else f"{r['tavan']:,}"
        print(f"{ad:>7} {r['p_hafta']:>12.3%} "
              f"{r['p_en_dusuk']:>7.1%}-{r['p_en_yuksek']:<9.1%} "
              f"{r['kesin']:>14.1%} "
              f"{r['en_dusuk']:>7.1%}-{r['en_yuksek']:<9.1%} "
              f"{r['yaklasik']:>9.1%} {r['yanlilik']:>+9.1%} "
              f"{r['tutan_pencere']:>4}/{c['pencere_sayisi']:<5}{not_}")
    if any(r["tavan"] == SERBEST for r in c["satirlar"]):
        print("\n'serbest' = ayni butceyle EN OLASI `butce` kolon. Oynanabilir")
        print("bir plan DEGIL (~4.300 ayri kutu); KOMBINATORIK EKSENIN TAVANI.")
        print("Bir planla bu satir arasindaki fark, gelecekteki her arama,")
        print("her algoritma ve her donanim icin kalan TOPLAM paydir.")
    print("\n'HEDEF (kesin)' = 1 - PI(1-p_w), pencere ortalamasi. 'yaklasik' =")
    print("1-(1-p_ort)^n, yani `coklu_kiyasi.py`nin '13 hafta' sutunu; farki")
    print("Jensen'dir ve HEP ayni yone bakar. 'gozlenen' kac pencerede gercekten")
    print(f"15/15 tuttugumuzdur — n = {c['pencere_sayisi']}, yani makullugu")
    print("sinar, olasiligi olcmez.")


def bas_zamanlama(z: dict[str, Any]) -> None:
    print(f"\nzamanlama sinavi — {z['pencere']} haftalik pencere, tavan "
          f"{z['tavan']}, butce {z['butce']:,}")
    print(f"izgara (haftalik butcenin kati): {z['izgara']}\n")
    print(f"{'pencere':>8} {'duz':>9} {'kahin':>9} {'kazanc':>9} "
          f"{'oynanmayan':>11}  dagilim")
    for i, r in enumerate(z["satirlar"], 1):
        print(f"{i:>8} {r['duz']:>9.1%} {r['kahin']:>9.1%} "
              f"x{r['kazanc']:>8.4f} {r['oynanmayan']:>11}  {r['dagilim']}")
    print(f"\nkahin kazanci: ortalama x{z['kazanc_ort']:.4f}, "
          f"en buyuk x{z['kazanc_en_buyuk']:.4f}")
    print("KAHIN UYGULANAMAZ: butun pencerenin egrilerini ONCEDEN bilir.")
    print("Gercek bir kural ancak bunun ALTINDA kalir, yani bu sayi")
    print("zamanlama ekseninin TAMAMIDIR.")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--pencere", type=int, default=VARSAYILAN_PENCERE,
                    help="ufuk uzunlugu, hafta (varsayilan 13 ~ uc ay)")
    ap.add_argument("--serbest", action="store_true",
                    help="tabloya kombinatorik TAVAN satirini ekle "
                         "(~1 sn/hafta, ~115 MB)")
    ap.add_argument("--zamanlama", action="store_true",
                    help="tam ongorulu tahsisin ust sinirini da olc (yavas)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    c = kos(a.butce, a.pencere, a.serbest)
    z = zamanlama(a.butce, a.pencere) if a.zamanlama else None
    if a.json:
        print(json.dumps({"hedef": c, "zamanlama": z}, ensure_ascii=False,
                         indent=1))
        return
    bas(c)
    if z is not None:
        bas_zamanlama(z)


if __name__ == "__main__":
    main()
