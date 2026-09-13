"""Operasyonun bedeli: elle giriş hatası hedefte kaç puan eder? (§3.74)

§3.73 operasyon sorusunun **yarısını** fiyatladı: 81 kuponda takılmanın
bedeli hedefte 1,8 puandır (77,0 → 78,8). Fiyatlanmayan yarısı sorunun
içindeki "güvenle" kelimesiydi. 81 kupon elle giriliyor; insan yanlış
girer ve yanlış girmenin de bir bedeli var.

Bu betik o bedeli ölçer ve iki soruya cevap verir:

1. **Tek bir slip ne eder?** Tür tür (atlama / kopya / eksik / fazla /
   takas), haftalık `P(15/15)`nin yüzdesi olarak, 114 tam haftada.
2. **Hangi hata oranında fazladan kupon ZARARA döner?** 729 kupon 81'e
   göre hedefte 1,8 puan kazandırır ama **dokuz kat** daha çok giriş
   demektir. Kupon başına hata oranı `r` büyüdükçe kazanç eriyor ve bir
   yerde işareti dönüyor. O eşik bu betiğin asıl çıktısıdır.

    cd backend && python scripts/operasyon_kiyasi.py
    cd backend && python scripts/operasyon_kiyasi.py --butce 21000 --json

─── Okuma kuralı — ölçüm görülmeden yazıldı ─────────────────────────────

1. **`fazla` satırının kaybı NEGATİF çıkacak** ve bu bir kusur değil:
   fazladan işaret kapsamayı genişletir, bedeli parada ödenir. O satırda
   okunacak sayı `P` değil `kolon` sütunudur. Plan bütçenin neredeyse
   tamamını kullandığı için aşım doğrudan cebe yazılır.
2. **`kopya` ile `atlama` aynı `P` kaybını verecek.** İkisinde de
   kaybedilen girilmeyen kupondur. Ayrışırlarsa gövde bozuktur
   (`test_kopya_kaybi_atlama_kaybiyla_AYNI`).
3. **Eşik sayısı bir TAHMİN değil bir SINIR.** `r*` "insanlar şu kadar
   hata yapar" demiyor; "şu kadardan çok hata yapılıyorsa kupon sayısını
   artırmak zarardır" diyor. Gerçek hata oranı bu depoda **ölçülmedi** ve
   ölçülemez — o bir insan olgusudur, kayıt gerektirir. Eşik, kararı o
   ölçüm olmadan da verilebilir kılıyorsa işini yapmıştır.
4. **Doğrusal yaklaşıklık.** Beklenen kayıp `M · r · δ̄` yazılıyor, yani
   sliplerin bağımsız ve tek tek küçük olduğu varsayılıyor. `r` büyüdükçe
   bozulur; betik bu yüzden `r*`ı basarken yaklaşıklığın orada hâlâ
   geçerli olup olmadığını da (`kayıp/P` oranıyla) basıyor.
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
from spor_toto.coklu import coklu_plan
from spor_toto.operasyon import (
    SLIP_TURLERI,
    hedef_duyarliligi,
    kritik_hata_orani,
    slip_ozeti,
    yogunlasma,
)
from spor_toto.ufuk import UFUK_HAFTA, ufuk_ortalamasi

#: Ölçülen kupon tavanları. 81 bugün donan kaydın tavanı, 729 §3.73'ün
#: ölçtüğü üst uç; aradakiler eşiğin tavanla nasıl oynadığını gösteriyor.
TAVANLAR = (27, 81, 243, 729)

#: Kıyasların TABANI: bugün donan kaydın tavanı (§3.69). Eşikler "bundan
#: yukarı çıkmak ne zaman zarar" diye sorulduğu için buradan ölçülüyor.
TABAN_TAVAN = 81


def kos(butce: int, tavanlar: Sequence[int] = TAVANLAR) -> dict[str, Any]:
    """114 tam haftada, tavan tavan, slip bedellerini ve eşiği ölçer."""
    haftalar = tam_haftalar(ikramiye_tablolari())
    probs_listeleri = [hafta_probs(lst)[0] for _, _, lst in haftalar]

    satirlar: list[dict[str, Any]] = []
    for tavan in tavanlar:
        p_haftalik: list[float] = []
        kolonlar: list[int] = []
        kuponlar: list[int] = []
        # Mutlak kayıp ve **o haftanın kendi `P`si içindeki pay** ayrı ayrı
        # birikiyor. Payı en sonda ortalama `P`ye bölerek hesaplamak yanlış
        # olurdu: en kötü slip zayıf bir haftadan gelir ve o haftanın `P`si
        # ortalamanın çok altındadır — oran o zaman iki ayrı haftanın
        # sayılarını böler.
        toplam: dict[str, list[float]] = {t: [] for t in SLIP_TURLERI}
        pay: dict[str, list[float]] = {t: [] for t in SLIP_TURLERI}
        en_kotu_pay: dict[str, float] = dict.fromkeys(SLIP_TURLERI, 0.0)
        en_kotu_kolon: dict[str, int] = dict.fromkeys(SLIP_TURLERI, 0)
        en_buyuk: list[float] = []
        yari: list[int] = []
        for probs in probs_listeleri:
            plan = coklu_plan(probs, butce, tavan)
            p_haftalik.append(plan.p_onbes)
            kolonlar.append(plan.kolon)
            kuponlar.append(plan.kupon_sayisi)
            y = yogunlasma(probs, plan.kuponlar)
            en_buyuk.append(y.en_buyuk_pay)
            yari.append(y.yarisini_tasiyan)
            for tur, o in slip_ozeti(probs, plan.kuponlar).items():
                toplam[tur].append(o.ortalama)
                pay[tur].append(o.ortalama / plan.p_onbes)
                en_kotu_pay[tur] = max(en_kotu_pay[tur],
                                       o.en_kotu / plan.p_onbes)
                en_kotu_kolon[tur] = max(en_kotu_kolon[tur], o.en_kotu_kolon)
        p_ort = sum(p_haftalik) / len(p_haftalik)
        satirlar.append({
            "tavan": tavan,
            # Fiilen girilen kupon sayısının ORTALAMASI. Arama tavana
            # dayanmak zorunda değil: bazı haftalarda daha az, daha büyük
            # kupon kazanıyor ve operasyon yükü o haftada gerçekten azdır.
            "kupon": sum(kuponlar) / len(kuponlar),
            "kupon_en_cok": max(kuponlar),
            "kolon_ort": sum(kolonlar) / len(kolonlar),
            "en_buyuk_pay": sum(en_buyuk) / len(en_buyuk),
            "yarisini_tasiyan": sum(yari) / len(yari),
            "yari_en_az": min(yari),
            "p_haftalik": p_ort,
            "hedef": ufuk_ortalamasi(p_haftalik, UFUK_HAFTA),
            # Duyarlılık pencere pencere ölçülüp ortalanıyor; tek pencereden
            # okumak onu o pencerenin `p`lerine bağlardı.
            "duyarlilik": sum(
                hedef_duyarliligi(p_haftalik[a:a + UFUK_HAFTA])
                for a in range(0, len(p_haftalik) - UFUK_HAFTA + 1, UFUK_HAFTA)
            ) / max(1, len(p_haftalik) // UFUK_HAFTA),
            "slip": {
                tur: {
                    "ortalama": sum(toplam[tur]) / len(toplam[tur]),
                    "ortalama_pay": sum(pay[tur]) / len(pay[tur]),
                    "en_kotu_pay": en_kotu_pay[tur],
                    "en_kotu_kolon": en_kotu_kolon[tur],
                }
                for tur in SLIP_TURLERI
            },
        })

    # Eşik: her tavanı **tabanla** (bugün donan kayıt, 81 kupon) kıyasla.
    # Kazanç hedef puanı farkı; bedel fazladan girişin slip yüküdür ve slip
    # bedeli olarak BÜYÜK tavanın ortalaması alınır — fazladan girişler
    # onun kuponlarıdır.
    taban = next((s for s in satirlar if s["tavan"] == TABAN_TAVAN),
                 satirlar[0])
    esikler: list[dict[str, Any]] = []
    for simdi in satirlar:
        if simdi["tavan"] <= taban["tavan"]:
            continue
        fark = simdi["hedef"] - taban["hedef"]
        kupon_farki = simdi["kupon"] - taban["kupon"]
        for tur in ("takas", "atlama"):
            bedel = simdi["slip"][tur]["ortalama"]
            esikler.append({
                "ust": simdi["tavan"], "alt": taban["tavan"], "tur": tur,
                "fark_puan": fark, "kupon_farki": kupon_farki,
                "slip_bedeli": bedel,
                "r": kritik_hata_orani(fark, simdi["duyarlilik"], UFUK_HAFTA,
                                       kupon_farki, bedel),
            })

    # İkinci okuma: tabanın KENDİ özensizliği. 729'a çıkmanın kazandıracağı
    # puanı, 81'i baştan savma girmek geri veriyor mu — ve hangi oranda?
    ust = max(satirlar, key=lambda s: s["tavan"])
    basibos = [{
        "tur": tur,
        "fark_puan": ust["hedef"] - taban["hedef"],
        "kupon": taban["kupon"],
        "slip_bedeli": taban["slip"][tur]["ortalama"],
        "r": kritik_hata_orani(ust["hedef"] - taban["hedef"],
                               taban["duyarlilik"], UFUK_HAFTA,
                               taban["kupon"], taban["slip"][tur]["ortalama"]),
    } for tur in ("takas", "atlama")]

    return {"butce": butce, "hafta": len(haftalar), "satirlar": satirlar,
            "esikler": esikler, "basibos": basibos,
            "taban_tavan": taban["tavan"], "ust_tavan": ust["tavan"]}


def _yani(r: float) -> str:
    """`r*`ı "kaç kuponda bir" diline çevirir; eşiksiz hâlleri ayırır.

    İki dejenere durum var ve ikisi ayrı şey söylüyor: `inf` "fazladan
    giriş yok ya da slip bedava" demek, `0` ise "kazanç zaten yok" —
    yani eşiği aramanın anlamı yok.
    """
    if r == float("inf"):
        return "esik yok"
    if r <= 0.0:
        return "kazanc yok"
    return f"1 kuponda {1 / r:,.0f}".replace(",", ".")


def bas(c: dict[str, Any]) -> None:
    """Ölçümü okunur bas — tablo tablo."""
    print(f"\nOPERASYONUN BEDELI (§3.74) — {c['hafta']} tam hafta, "
          f"butce {c['butce']:,} kolon".replace(",", "."))

    print("\n  Tek slipin O HAFTANIN P(15/15)'i icindeki payi "
          "(ortalama | en kotu hafta)")
    print(f"  {'tavan':>6} {'kupon':>7} {'P(15/15)':>10} {'hedef':>7} " +
          " ".join(f"{t:>17}" for t in SLIP_TURLERI))
    for s in c["satirlar"]:
        hucre = [
            f"{s['slip'][t]['ortalama_pay']:>+6.2%}|{s['slip'][t]['en_kotu_pay']:>+8.2%}"
            for t in SLIP_TURLERI
        ]
        print(f"  {s['tavan']:>6} {s['kupon']:>7.1f} {s['p_haftalik']:>10.4%} "
              f"{s['hedef']:>7.1%} " + " ".join(f"{h:>17}" for h in hucre))
    print("  (+ = kayip, - = slip P'yi YUKSELTTI; `fazla`nin bedeli parada)")

    print("\n  `fazla` isaretin PARA bedeli — tek fazladan isaret")
    for s in c["satirlar"]:
        asim = s["slip"]["fazla"]["en_kotu_kolon"]
        print(f"  {s['tavan']:>6} kupon: plan {s['kolon_ort']:>9,.0f} kolon, "
              f"en kotu +{asim:,} kolon = +{asim * 10:,} TL "
              f"(butcenin %{100 * asim / c['butce']:.0f}'i)".replace(",", "."))

    print("\n  YOGUNLASMA — hedef kac kupona yigilmis "
          "(114 haftanin ortalamasi)")
    print(f"  {'tavan':>6} {'en buyuk kupon':>15} {'duz olsaydi':>12} "
          f"{'yarisini tasiyan':>17} {'en az':>7}")
    for s in c["satirlar"]:
        print(f"  {s['tavan']:>6} {s['en_buyuk_pay']:>14.2%} "
              f"{1 / s['kupon']:>12.2%} {s['yarisini_tasiyan']:>13.0f} kupon "
              f"{s['yari_en_az']:>7}")
    print("  (denetim sirasi: kuponlari olasiliga gore azalan diz, "
          "ilk kume iki kez okunur)")

    print(f"\n  ESIK 1 — {c['taban_tavan']} kupondan YUKARI cikmak hangi "
          f"hata oraninda ZARARA doner")
    print(f"  {'kiyas':>13} {'slip':>7} {'hedef farki':>12} "
          f"{'fazla giris':>12} {'r*':>8}  {'yani':>20}")
    for e in c["esikler"]:
        print(f"  {e['alt']:>4} -> {e['ust']:>5} {e['tur']:>7} "
              f"{100 * e['fark_puan']:>+11.2f}p {e['kupon_farki']:>12,.0f} "
              f"{e['r']:>8.2%}  {_yani(e['r']):>20}".replace(",", "."))

    print(f"\n  ESIK 2 — {c['taban_tavan']} kuponu OZENSIZ girmek, "
          f"{c['ust_tavan']}'a cikmanin kazancini geri verir mi")
    for b in c["basibos"]:
        print(f"  {b['tur']:>7}: {100 * b['fark_puan']:>+.2f} puanlik kazanc, "
              f"{b['kupon']:.0f} giris -> r* = {b['r']:.2%}  "
              f"({_yani(b['r'])})".replace(",", "."))


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--tavan", type=int, nargs="+", default=list(TAVANLAR),
                    help="olculecek kupon tavanlari")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    c = kos(a.butce, a.tavan)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return
    bas(c)


if __name__ == "__main__":
    main()
