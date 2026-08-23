#!/usr/bin/env python3
"""Sonuçlar geldikten sonra: kupon ne yaptı, neden, ve kural değişmeli mi.

Bu script `super_toto_hafta.py`nin ikinci yarısıdır. O, sonuç görülmeden
kuponu kurar; bu, sonuç görüldükten sonra **aynı sayıları** hesabın
neresinde yanıldığımızı göstermek için kullanır.

Üç soruya cevap verir:

  1. Kupon kaç tutturdu, hangi maçlar küme dışında kaldı?
  2. Bu, şanssızlık mıydı yoksa kuralın yapısal açığı mı? (kaçak
     dağılımı + geçen sezonun en-iyi-kolon dağılımı)
  3. Alternatif kurallar bu haftada ve geçen sezonun tamamında ne
     yapardı? (kolon başına maliyetiyle birlikte)

    python scripts/super_toto_degerlendir.py --hafta 1
    python scripts/super_toto_degerlendir.py --hafta 1 --kural-tara

`--kural-tara` geçen sezonun tamamını yeniden koşar (~1 dk).

UYARI: buradaki hiçbir sayı "şu kuralı kullan" demez. Alternatif kurallar
AYNI sezonda seçildiği için lehlerine görünmeleri beklenendir; karara esas
olan sayı kolon başına maliyettir, ham isabet değil.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.core import SEMBOLLER
from spor_toto.ortak import kacak_dagilimi as ortak_kacak_dagilimi

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
SEM = SEMBOLLER


def _hafta_modulu():
    """Hafta betigi — artik siradan bir import (bkz. scripts/__init__.py)."""
    return importlib.import_module("scripts.super_toto_hafta")


#: Tam sayım için üst sınır. 16 satırlık kaplama kurulamadığında seçim
#: uzayının tamamı gezilir; 200 bin kolon 15 maçta saniyenin altındadır.
TAM_SAYIM_SINIRI = 200_000


def en_iyi_kolon(secimler: Sequence[Sequence[str]], gercek: str) -> int:
    """Oynanan kuponun EN İYİ kolonunun kaç doğru tutturduğu.

    Kolonları tek tek gezer; 15 maç ve en fazla ~30 bin kolonda bu
    milisaniyelerdir ve motorun kendi skorlayıcısına bağımlılık
    yaratmaz — sonuç kümenin dışındayken de doğru cevap verir.

    **Yedek yol neden var.** `solve_fix16` en az 7 çifte maç ister; altında
    `Fix16Hatasi` atar. Kural az çifte üretebilir (çok banko çıkan hafta) ve
    bu, marj arındırma `shin`e çevrildikten sonra **daha olası** hâle geldi —
    Shin favoriye daha çok pay verir, daha çok banko çıkar. Böyle bir haftada
    sonuç değerlendirmesinin çökmesi, ölçümün en çok gerektiği anda
    kaybolması olurdu. Kaplama kurulamıyorsa seçim uzayının tamamı gezilir;
    o uzay zaten küçüktür (az çifte = az kolon).
    """
    from itertools import product

    from spor_toto.core import Encoder, Fix16Hatasi, solve_fix16
    listeler = [list(x) for x in secimler]
    try:
        enc = Encoder(listeler)
        cols, _ = solve_fix16(enc)
    except Fix16Hatasi:
        uzay = 1
        for s in listeler:
            uzay *= len(s)
        if uzay > TAM_SAYIM_SINIRI:  # pragma: no cover - kuralin uretemedigi hal
            raise
        # Tam sayim: her kolon secim kumesinin bir noktasidir.
        return max(sum(1 for a, b in zip(kolon, gercek) if a == b)
                   for kolon in product(*listeler))

    en_iyi = 0
    for c in cols:
        skor = 0
        j = 0
        for i, s in enumerate(secimler):
            if len(s) == 1:
                skor += 1 if s[0] == gercek[i] else 0
            else:
                skor += 1 if enc.variable_syms[j][c[j]] == gercek[i] else 0
                j += 1
        if skor > en_iyi:
            en_iyi = skor
    return en_iyi


#: Poisson-binom `spor_toto.ortak`a taşındı: `spor_toto.secim` kuponu
#: KURARKEN aynı hesabı istiyor, bu betik ise onu DEĞERLENDİRİYOR. İki
#: gövde ayrışsaydı kuponu kuran hesap ile onu ölçen hesap farklı şeyler
#: söylerdi — ve bu, fark edilmesi en zor hata türüdür.
kacak_dagilimi = ortak_kacak_dagilimi


def kupon_degerlendir(d: dict[str, Any], picks: Sequence[str]) -> dict[str, Any]:
    gercek = d["meta"]["results"]
    maclar = d["matches"]
    kacaklar = [i + 1 for i, (p, g) in enumerate(zip(picks, gercek)) if g not in p]
    p_kacak = [1 - sum(mm["probs"][x] for x in pk) for mm, pk in zip(maclar, picks)]
    dist = kacak_dagilimi(p_kacak)
    n = len(kacaklar)
    return {
        "picks": list(picks),
        "misses": kacaklar,
        "miss_count": n,
        "best": en_iyi_kolon([list(x) for x in picks], gercek),
        "expected_misses": sum(p_kacak),
        "p_in_set": dist[0],
        "p_at_least_actual": sum(dist[n:]),
        "dist": dist,
        "per_match": [
            {"no": mm["no"], "mac": f"{mm['home']} – {mm['away']}", "pick": pk,
             "gercek": g, "tuttu": g in pk, "p_kacak": pk_,
             "atilan": [x for x in SEM if x not in pk],
             "p_atilan": {x: mm["probs"][x] for x in SEM if x not in pk}}
            for mm, pk, g, pk_ in zip(maclar, picks, gercek, p_kacak)
        ],
    }


def kupon_kiyas(d, a_picks, b_picks) -> dict[str, Any]:
    """İki kuponu maç maç karşılaştırır ve birleşimlerini ölçer.

    Birleşim kolonu bilerek var: "iki kupon birlikte oynansaydı" sorusu,
    haftanın ulaşılabilir olup olmadığını gösteren en dürüst testtir.
    """
    import math
    gercek = d["meta"]["results"]
    birlesim = ["".join(sorted(set(x) | set(y), key=SEM.index))
                for x, y in zip(a_picks, b_picks)]
    bk = [i + 1 for i, (p_, g) in enumerate(zip(birlesim, gercek)) if g not in p_]
    return {
        "union_picks": birlesim,
        "union_space": math.prod(len(x) for x in birlesim),
        "union_misses": bk,
        "union_best": 15 - len(bk),
        "rows": [
            {"no": i + 1, "mac": f"{mm['home']} – {mm['away']}",
             "a": x, "b": y, "gercek": g,
             "a_tuttu": g in x, "b_tuttu": g in y}
            for i, (mm, x, y, g) in enumerate(zip(d["matches"], a_picks, b_picks, gercek))
        ],
    }


def banko_karnesi(d, picks) -> dict[str, Any]:
    """Bankolar ne yaptı — tek işaretli maçlar kuponun kırılma noktasıdır."""
    gercek = d["meta"]["results"]
    sat = [{"no": i + 1, "mac": f"{d['matches'][i]['home']} – {d['matches'][i]['away']}",
            "sembol": p, "gercek": gercek[i], "tuttu": p == gercek[i],
            "p": d["matches"][i]["probs"][p]}
           for i, p in enumerate(picks) if len(p) == 1]
    return {"rows": sat, "n": len(sat),
            "dogru": sum(1 for r in sat if r["tuttu"]),
            "beklenen": sum(r["p"] for r in sat)}


def kalabalik_karnesi(d: dict[str, Any]) -> dict[str, Any]:
    """Kalabalığın kuponu ne yaptı — ikramiyenin neden büyük olduğunun cevabı."""
    gercek = d["meta"]["results"]
    maclar = d["matches"]
    halk = "".join(max(SEM, key=lambda s: mm["play"][s]) for mm in maclar)
    piyasa = "".join(mm["fav"] for mm in maclar)
    return {
        "halk_kuponu": halk,
        "halk_dogru": sum(1 for a, b in zip(halk, gercek) if a == b),
        "piyasa_kuponu": piyasa,
        "piyasa_dogru": sum(1 for a, b in zip(piyasa, gercek) if a == b),
        # Bağımsızlık varsayımıyla rastgele bir halk kuponunun beklenen
        # doğru sayısı: her maçta gerçek sonuca oynayanların payı.
        "beklenen_halk_dogru": sum(mm["play"][g] for mm, g in zip(maclar, gercek)),
        "beklenen_piyasa_dogru": sum(mm["probs"][g] for mm, g in zip(maclar, gercek)),
    }


def ikramiye_ozeti(d: dict[str, Any]) -> dict[str, Any]:
    pay = d["meta"].get("payout")
    if not pay:
        return {}
    katlar = []
    for t in pay["tiers"]:
        if t.get("prize") is None:
            katlar.append({**t, "toplam": None})
        else:
            katlar.append({**t, "toplam": t["winners"] * t["prize"]})
    return {"tiers": katlar, "currency": pay.get("currency", "TRY")}


def yaz(d: dict[str, Any], kupon: dict[str, Any], sonuclar: list[dict[str, Any]],
        kal: dict[str, Any], ikr: dict[str, Any]) -> None:
    meta = d["meta"]
    gercek = meta["results"]
    sayim = {s: gercek.count(s) for s in SEM}
    print(f"\n{'='*78}\n{meta['season']} · {meta['week']}. HAFTA — SONUÇ DEĞERLENDİRMESİ\n{'='*78}")
    print(f"Gerçek dizi : {' '.join(gercek)}")
    print(f"Sayım 1/0/2 : {sayim['1']} / {sayim['0']} / {sayim['2']}")

    for ad, s in zip([v["label"] for v in kupon["variants"]], sonuclar):
        print(f"\n─── {ad}")
        print(f"  İşaret : {' '.join(s['picks'])}")
        print(f"  Kaçak  : {s['misses']} ({s['miss_count']} maç)")
        print(f"  EN İYİ KOLON: {s['best']}/15")
        print(f"  Beklenen kaçak {s['expected_misses']:.2f} · küme-içi %{100*s['p_in_set']:.2f} · "
              f"P(kaçak ≥ {s['miss_count']}) = %{100*s['p_at_least_actual']:.1f}")

    ana = sonuclar[0]
    print("\n─── MAÇ MAÇ (ana kupon) ───────────────────────────────────────────────")
    for r in ana["per_match"]:
        im = "✓" if r["tuttu"] else "✗"
        at = ", ".join(f"{x}=%{100*r['p_atilan'][x]:.0f}" for x in r["atilan"]) or "—"
        print(f"  {im} {r['no']:>2} {r['mac'][:34]:<34} işaret [{r['pick']:<3}] "
              f"gerçek {r['gercek']} · attığım: {at}")

    print("\n─── KALABALIK KARNESİ ─────────────────────────────────────────────────")
    print(f"  Halkın en çok oynadığı kupon : {kal['halk_kuponu']} → {kal['halk_dogru']}/15 doğru")
    print(f"  Piyasanın favori kuponu      : {kal['piyasa_kuponu']} → {kal['piyasa_dogru']}/15 doğru")
    print(f"  Rastgele bir halk kuponunun beklenen doğrusu : {kal['beklenen_halk_dogru']:.2f}")
    print(f"  Piyasa olasılıklarının beklediği doğru       : {kal['beklenen_piyasa_dogru']:.2f}")

    if ikr:
        print("\n─── İKRAMİYE ──────────────────────────────────────────────────────────")
        for t in ikr["tiers"]:
            if t["prize"] is None:
                print(f"  {t['correct']} bilen: çıkmadı · {t.get('rollover', 0):,.2f} TL devretti")
            else:
                print(f"  {t['correct']} bilen: {t['winners']:>5} kişi × {t['prize']:>12,.2f} TL "
                      f"= {t['toplam']:>15,.2f} TL")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--hafta", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    m = _hafta_modulu()
    d = m.hafta_yukle(a.sezon, a.hafta)
    if not d["meta"].get("results"):
        raise SystemExit("Bu haftanın sonucu henüz girilmemiş.")

    kupon_yolu = (KOK / "data" / "super_toto" / a.sezon /
                  f"hafta_{a.hafta:02d}_kupon.json")
    kupon = json.loads(kupon_yolu.read_text(encoding="utf-8"))
    sonuclar = [kupon_degerlendir(d, v["picks"]) for v in kupon["variants"]]
    kal = kalabalik_karnesi(d)
    ikr = ikramiye_ozeti(d)

    if a.json:
        print(json.dumps({"results": d["meta"]["results"], "coupons": sonuclar,
                          "crowd": kal, "payout": ikr}, ensure_ascii=False, indent=1))
    else:
        yaz(d, kupon, sonuclar, kal, ikr)


if __name__ == "__main__":
    main()
