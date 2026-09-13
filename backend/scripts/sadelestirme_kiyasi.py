"""Planın SLİP sayısı: kupon ≠ slip, ve tahsisin operasyon bedeli (§3.75)

§3.74 operasyonun istatistiksel yarısını kapattı ve lojistik yarısını
*"bu depodan ölçülemez"* diye bıraktı: **bir insan 81 kuponu kupon
kapanmadan girebiliyor mu?** Kapanmayan yarı gerçekten bir insan
olgusudur, ama o cümle bir şeyi sormadan doğru kabul ediyordu: **81 kupon
81 slip demek.**

Demek değil. `spor_toto/sadelestirme.py` aynı kolon kümesini daha az
kutuyla yazıyor — kolonlar birebir aynı, kolon sayısı aynı, `P(15/15)`
aynı; değişen yalnızca kaç kez elle kutu doldurulacağı. Bu betik o farkı
114 tam haftada, tavan tavan ölçüyor ve iki soruya cevap veriyor:

1. **Gerçek yük nedir?** Kupon sayısı yerine slip ve karalanan kutucuk
   sayısı, tavan tavan.
2. **Tahsisin (§3.71) operasyon bedeli nedir?** §3.71 her kupona ayrı alt
   sistem bütçesi verdi ve `P`de ×1,041 kazandı. Ama iki kutu ancak bir
   tek konumda ayrışıyorsa birleşir; alt sistemleri ayrışan kuponlar
   **hiç** birleşmez. Yani o kazancın ölçülmemiş bir bedeli var ve bu
   betik onu tekdüze bütçeli aramaya karşı ölçüyor.

    cd backend && python scripts/sadelestirme_kiyasi.py
    cd backend && python scripts/sadelestirme_kiyasi.py --butce 21000 --json

─── Okuma kuralı — ölçüm görülmeden yazıldı ─────────────────────────────

1. **Slip sayısı kupon sayısından az çıkacak.** Bu kurulum, keşif değil:
   en olası `M` eksen bileşimi rütbe sırasında bir aşağı kümedir ve tek
   koordinatta komşu bileşimler kümeye birlikte girer. Ölçülecek olan
   düşüşün *oranı*.
2. **Tekdüze plan ALLOKELİ plandan daha çok birleşecek.** Tekdüze planda
   bütün kuponlar aynı alt sistemi oynar, yani ayrıştıkları tek yer
   eksendir. Tahsisli planda alt sistemler de ayrışır ve o ayrışma
   birleşmeyi **öldürür**. Beklenti: tahsis slip yükünü belirgin biçimde
   artırıyor.
3. **Bu, §3.71'i geri almaz — fiyatlar.** Kazanç `P`de ölçülmüştü, bedel
   slipte ölçülüyor. İkisi ancak §3.74'ün eşiğiyle aynı dile çevrilir:
   fazladan slipin hedefte kaç puan ettiği, kupon başına hata oranı `r`
   bilinmeden **sınır** olarak yazılabilir. Kararı değiştirmesi için o
   sınırın makul hata oranlarının altına inmesi gerekir.
4. **En büyük birleşmiş slip, tek sistem kuponundan KÜÇÜK çıkmalı.** Depo
   bir yıldır tek sistem kuponunu (19.683 kolon) tek bir giriş sayıyor.
   Birleşmiş bir slip ondan büyük çıkarsa bu betiğin "yük azaldı" iddiası
   kendi içinde tutarsızlaşır; küçük çıkarsa iddia deponun **kendi**
   varsayımına yaslanmış olur.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.coklu_kiyasi import VARSAYILAN_BUTCE, hafta_probs
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from spor_toto.coklu import (
    _INDEKS,
    ARANAN_KUPON,
    MAC_SAYISI,
    Kupon,
    _eksen_bilesimleri,
    _kuponlari_kur,
    _matris,
    coklu_plan_serisi,
    p_onbes,
)
from spor_toto.operasyon import (
    hedef_duyarliligi,
    kritik_hata_orani,
    slip_ozeti,
)
from spor_toto.sadelestirme import sadelestir
from spor_toto.secim import en_iyi_secim
from spor_toto.ufuk import UFUK_HAFTA, ufuk_ortalamasi

#: Ölçülen kupon tavanları — §3.74 ile aynı ızgara, kıyas edilebilsin.
TAVANLAR = (27, 81, 243, 729)

#: Kıyasların tabanı: bugün donan kaydın tavanı (§3.69).
TABAN_TAVAN = 81


def tek_tip_plan(probs: list[dict[str, float]], butce: int,
                 tavanlar: Sequence[int]
                 ) -> dict[int, tuple[list[Kupon], float]]:
    """Tahsissiz plan: bütün kuponlar **aynı** alt sistemi oynar.

    `scripts/tahsis_kiyasi.py::tek_tip_arama` aynı aramayı yapıyor ama
    yalnız `P`yi döndürüyor; burada kuponların kendisi gerekiyor, çünkü
    ölçülen şey onların birleşebilirliği. Gövde oradan **kopyalanmadı**,
    kupon kurma işi `coklu._kuponlari_kur`a bırakıldı — iki kopya olsaydı
    biri sessizce eskirdi.

    Bütün tavanlar **tek geçişte** dönüyor: `coklu_plan_serisi`nin
    sebebiyle aynı sebep, arama zaten bütün `(M, d)` çiftlerini geziyor.
    """
    P = _matris(probs)
    emin = np.argsort(-P.max(axis=1)).tolist()
    en: dict[int, tuple[list[Kupon], float]] = {t: ([], 0.0) for t in tavanlar}
    for M in ARANAN_KUPON:
        kupon_butce = butce // M
        if kupon_butce < 1:
            break
        for d in range(MAC_SAYISI + 1):
            eksen = sorted(emin[:d])
            kalanlar = [i for i in range(MAC_SAYISI) if i not in set(eksen)]
            alt = (en_iyi_secim([probs[i] for i in kalanlar], kupon_butce,
                                esik=0) if kalanlar else None)
            if kalanlar and alt is None:
                continue
            bedel = 1 if alt is None else alt.bedel
            p_alt = 1.0 if alt is None else float(np.prod(
                [P[i, [_INDEKS[s] for s in sec]].sum()
                 for i, sec in zip(kalanlar, alt.secimler)]))
            for tavan in tavanlar:
                sayi = min(butce // bedel, 3 ** d, tavan)
                if sayi < 1:
                    continue
                bilesimler, p_eksen = _eksen_bilesimleri(P, eksen, sayi)
                if p_eksen * p_alt <= en[tavan][1]:
                    continue
                en[tavan] = (_kuponlari_kur(bilesimler, eksen, kalanlar,
                                            alt, bedel), p_eksen * p_alt)
    return en


def _yuk(probs: list[dict[str, float]], kuponlar: Sequence[Kupon]
         ) -> dict[str, Any]:
    """Bir planın elle giriş yükü — birleştirmeden önce ve sonra."""
    s = sadelestir(kuponlar)
    return {
        "kupon": s.slip_once, "slip": s.slip_sonra,
        "isaret_once": s.isaret_once, "isaret": s.isaret_sonra,
        "en_buyuk_slip_kolon": s.en_buyuk_slip_kolon,
        "kolon": s.kolon,
        # Birleştirmenin `P`yi değiştirmediği burada, her hafta, yeniden
        # sınanıyor. Bekçi zaten var; ölçüm yine de kendi iddiasını
        # koşarken doğrular — belge sayısı ölçümle aynı koşumdan çıksın.
        "p_sapma": abs(p_onbes(probs, list(kuponlar))
                       - p_onbes(probs, s.kuponlar)),
        "kuponlar": s.kuponlar,
    }


def kos(butce: int, tavanlar: Sequence[int] = TAVANLAR,
        hafta_siniri: int | None = None) -> dict[str, Any]:
    """114 tam haftada, tavan tavan, slip ve kutucuk yükünü ölçer."""
    haftalar = tam_haftalar(ikramiye_tablolari())
    if hafta_siniri is not None:
        haftalar = haftalar[:hafta_siniri]
    probs_listeleri = [hafta_probs(lst)[0] for _, _, lst in haftalar]

    ham: dict[int, list[dict[str, Any]]] = {t: [] for t in tavanlar}
    tekduze: dict[int, list[dict[str, Any]]] = {t: [] for t in tavanlar}
    p_haftalik: dict[int, list[float]] = {t: [] for t in tavanlar}
    p_tekduze: dict[int, list[float]] = {t: [] for t in tavanlar}
    tek_sistem_kolon: list[int] = []
    slip_bedeli: dict[int, dict[str, list[float]]] = {
        t: {"takas": [], "atlama": []} for t in tavanlar}

    for probs in probs_listeleri:
        seri = coklu_plan_serisi(probs, butce, tuple(tavanlar))
        tek = coklu_plan_serisi(probs, butce, (1,))[1]
        tek_sistem_kolon.append(tek.kolon)
        duz = tek_tip_plan(probs, butce, tavanlar)
        for tavan in tavanlar:
            plan = seri[tavan]
            y = _yuk(probs, plan.kuponlar)
            ham[tavan].append(y)
            p_haftalik[tavan].append(plan.p_onbes)
            # Slip bedeli BİRLEŞMİŞ kümede ölçülüyor: fazladan girilen şey
            # artık birleşmiş sliptir, kupon değil. Bedeli de onun.
            for tur, o in slip_ozeti(probs, y["kuponlar"]).items():
                if tur in slip_bedeli[tavan]:
                    slip_bedeli[tavan][tur].append(o.ortalama)
            kupon, p = duz[tavan]
            tekduze[tavan].append(_yuk(probs, kupon))
            p_tekduze[tavan].append(p)

    def ort(xs: Sequence[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    satirlar: list[dict[str, Any]] = []
    for tavan in tavanlar:
        a, b = ham[tavan], tekduze[tavan]
        satirlar.append({
            "tavan": tavan,
            "kupon": ort([x["kupon"] for x in a]),
            "slip": ort([x["slip"] for x in a]),
            "slip_en_cok": max(x["slip"] for x in a),
            "isaret_once": ort([x["isaret_once"] for x in a]),
            "isaret": ort([x["isaret"] for x in a]),
            "en_buyuk_slip_kolon": max(x["en_buyuk_slip_kolon"] for x in a),
            "p_sapma": max(x["p_sapma"] for x in a),
            "tekduze_kupon": ort([x["kupon"] for x in b]),
            "tekduze_slip": ort([x["slip"] for x in b]),
            "tekduze_isaret": ort([x["isaret"] for x in b]),
            "p_haftalik": ort(p_haftalik[tavan]),
            "p_tekduze": ort(p_tekduze[tavan]),
            "hedef": ufuk_ortalamasi(p_haftalik[tavan], UFUK_HAFTA),
            "hedef_tekduze": ufuk_ortalamasi(p_tekduze[tavan], UFUK_HAFTA),
            "duyarlilik": ort([
                hedef_duyarliligi(p_haftalik[tavan][i:i + UFUK_HAFTA])
                for i in range(0, len(p_haftalik[tavan]) - UFUK_HAFTA + 1,
                               UFUK_HAFTA)]),
            "slip_bedeli": {t: ort(v) for t, v in slip_bedeli[tavan].items()},
        })

    # ─── Eşikler — §3.74'ün sorusu, ama KUPON yerine SLİP ile ───────────
    #
    # §3.74 "fazladan kupon ne zaman zarara döner" diye sordu ve bedeli
    # kupon sayısıyla ölçtü. Fazladan girilen şey artık slip; eşik de
    # onunla yazılmalı. İki eşik var ve ayrı şey soruyorlar:
    #
    #   tavan  — 81'den yukarı çıkmak ne zaman zarar (§3.74'ün eşiği)
    #   tahsis — §3.71'i açık tutmak ne zaman zarar (bu bölümün sorusu)
    taban = next(s for s in satirlar if s["tavan"] == TABAN_TAVAN)
    esikler: list[dict[str, Any]] = []
    for simdi in satirlar:
        if simdi["tavan"] <= taban["tavan"]:
            continue
        for tur in ("takas", "atlama"):
            esikler.append({
                "cins": "tavan", "ust": simdi["tavan"], "alt": taban["tavan"],
                "tur": tur,
                "fark_puan": simdi["hedef"] - taban["hedef"],
                "slip_farki": simdi["slip"] - taban["slip"],
                "kupon_farki": simdi["kupon"] - taban["kupon"],
                "slip_bedeli": simdi["slip_bedeli"][tur],
                "r": kritik_hata_orani(
                    simdi["hedef"] - taban["hedef"], simdi["duyarlilik"],
                    UFUK_HAFTA, simdi["slip"] - taban["slip"],
                    simdi["slip_bedeli"][tur]),
            })
    for s in satirlar:
        for tur in ("takas", "atlama"):
            esikler.append({
                "cins": "tahsis", "ust": s["tavan"], "alt": s["tavan"],
                "tur": tur,
                "fark_puan": s["hedef"] - s["hedef_tekduze"],
                "slip_farki": s["slip"] - s["tekduze_slip"],
                "kupon_farki": 0.0,
                "slip_bedeli": s["slip_bedeli"][tur],
                "r": kritik_hata_orani(
                    s["hedef"] - s["hedef_tekduze"], s["duyarlilik"],
                    UFUK_HAFTA, s["slip"] - s["tekduze_slip"],
                    s["slip_bedeli"][tur]),
            })

    return {
        "butce": butce, "hafta": len(haftalar), "satirlar": satirlar,
        "esikler": esikler,
        "tek_sistem_kolon": ort(tek_sistem_kolon),
        "taban_tavan": TABAN_TAVAN,
    }


def _oran(a: float, b: float) -> float:
    return a / b if b else float("nan")


def _yani(r: float) -> str:
    """`r*`ı "kaç slipte bir" diline çevirir; dejenere hâlleri ayırır.

    `operasyon_kiyasi._yani` ile aynı işi yapıyor ama birimi **slip**,
    kupon değil — §3.75'in tamamı bu ayrımın üstünde duruyor ve iki
    tabloyu aynı kelimeyle basmak onu silerdi.
    """
    if r == float("inf"):
        return "esik yok"
    if r <= 0.0:
        return "kazanc yok"
    return f"1 slipte {1 / r:,.0f}".replace(",", ".")


def bas(c: dict[str, Any]) -> None:
    """Ölçümü okunur bas."""
    print(f"\nPLANIN SLIP SAYISI (§3.75) — {c['hafta']} tam hafta, "
          f"butce {c['butce']:,} kolon".replace(",", "."))

    print("\n  ELLE GIRIS YUKU — ayni kolonlar, daha az kutu")
    print(f"  {'tavan':>6} {'kupon':>8} {'slip':>8} {'en cok':>7} {'x':>6} "
          f"{'kutucuk':>9} {'->':>9} {'x':>6} {'en buyuk slip':>14}")
    for s in c["satirlar"]:
        print(f"  {s['tavan']:>6} {s['kupon']:>8.1f} {s['slip']:>8.1f} "
              f"{s['slip_en_cok']:>7} "
              f"{_oran(s['kupon'], s['slip']):>6.2f} "
              f"{s['isaret_once']:>9.0f} {s['isaret']:>9.0f} "
              f"{_oran(s['isaret_once'], s['isaret']):>6.2f} "
              f"{s['en_buyuk_slip_kolon']:>14,}".replace(",", "."))
    print(f"  (tek sistem kuponu: {c['tek_sistem_kolon']:,.0f} kolon — "
          "depo onu BIR giris sayiyor)".replace(",", "."))

    # `tekduze kupon` sütunu SÜS DEĞİL: tekdüze arama tavana dayanmak
    # zorunda değil (bütçe // bedel onu erken kesebilir), yani slip farkı
    # iki ayrı şeyden gelebilir — daha az kupon, ya da daha çok birleşme.
    # Sütun olmadan ikisi ayrılamaz ve tahsisin bedeli şişik okunur.
    print("\n  TAHSISIN OPERASYON BEDELI — §3.71 acik, tekduze butce kapali")
    print(f"  {'tavan':>6} {'kupon':>6} {'slip':>7} | {'tekduze kupon':>14} "
          f"{'slip':>7} {'x':>6} | {'birlesme x':>11} {'tekduze x':>10} | "
          f"{'P kazanci':>10}")
    for s in c["satirlar"]:
        print(f"  {s['tavan']:>6} {s['kupon']:>6.0f} {s['slip']:>7.1f} | "
              f"{s['tekduze_kupon']:>14.1f} {s['tekduze_slip']:>7.1f} "
              f"{_oran(s['slip'], s['tekduze_slip']):>5.2f}x | "
              f"{_oran(s['kupon'], s['slip']):>10.2f}x "
              f"{_oran(s['tekduze_kupon'], s['tekduze_slip']):>9.2f}x | "
              f"{_oran(s['p_haftalik'], s['p_tekduze']):>9.4f}x")

    print("\n  HEDEF (13 hafta) ve dogrulama")
    print(f"  {'tavan':>6} {'hedef':>8} {'hedef tekduze':>14} "
          f"{'P sapmasi (birlestirme)':>25}")
    for s in c["satirlar"]:
        print(f"  {s['tavan']:>6} {s['hedef']:>8.4f} "
              f"{s['hedef_tekduze']:>14.4f} {s['p_sapma']:>25.2e}")

    print("\n  ESIK — slip basina hata orani `r` bu degeri ASARSA zarar")
    print(f"  {'kiyas':>16} {'slip':>6} {'hedef farki':>12} "
          f"{'fazla slip':>11} {'slip bedeli':>12} {'r*':>8} {'yani':>18}")
    for e in c["esikler"]:
        ad = (f"{e['alt']} -> {e['ust']}" if e["cins"] == "tavan"
              else f"tahsis @ {e['ust']}")
        print(f"  {ad:>16} {e['tur']:>6} {e['fark_puan']:>12.4f} "
              f"{e['slip_farki']:>11.1f} {e['slip_bedeli']:>12.6f} "
              f"{e['r']:>8.4f} {_yani(e['r']):>18}")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon cinsinden haftalik butce")
    ap.add_argument("--hafta", type=int, default=None,
                    help="ilk N hafta (deneme kosumu icin)")
    ap.add_argument("--json", action="store_true", help="ham cikti")
    a = ap.parse_args(argv)
    c = kos(a.butce, hafta_siniri=a.hafta)
    if a.json:
        # `kuponlar` JSON'a girmez: ham Kupon nesnesi ve ölçüm değil.
        print(json.dumps(c, ensure_ascii=False, indent=1, default=str))
    else:
        bas(c)


if __name__ == "__main__":  # pragma: no cover
    main()
