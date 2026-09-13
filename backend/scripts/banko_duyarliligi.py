"""Ölçülen banko sapması planın kararını değiştiriyor mu — 114 hafta.

§3.64 banko `p₁`'inin düşük yazıldığını ölçtü ve düzeltmeyi **uygulamadı**
(önceden yazılmış durma kuralı, `karne.T1_DUZELTME_ESIGI`). Bu betik o
kararı tartışmıyor; beklemenin **bedelini** ölçüyor. Ayrıntı ve gerekçe:
`spor_toto.duyarlilik` modül başlığı.

İki soru, iki ayrı kesit — ve ikisi bilerek ayrı tutuluyor, çünkü sapmalı
cetvelle ölçülen sapmalı bir plan kendini haklı çıkarır:

* **A · kalibrasyon** — plan SABIT (taban planı), cetvel değişir. Modelin
  iddiası gerçekleşen hafta sayısıyla bağdaşıyor mu; sapmayı kaldırmak onu
  yaklaştırıyor mu?
* **B · karar** — cetvel değişir, plan onunla kurulur, sonra **taban
  cetvelle** ve **gerçekleşenle** ölçülür. Seçilen şekil değişiyor mu,
  değişiyorsa 114 haftada daha çok 15/15 tutuyor mu?

    cd backend && python scripts/banko_duyarliligi.py
    cd backend && python scripts/banko_duyarliligi.py --butce 19683 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.coklu_kiyasi import hafta_probs, isabet
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from spor_toto.coklu import coklu_plan_serisi, p_onbes
from spor_toto.duyarlilik import BANKO_SAPMASI, TARANAN_SAYI, plan_kalibrasyonu, sapma_uygula

#: Kıyaslanan kupon tavanları. 1 bugün oynanan tek sistemdir; 729
#: `coklu.py` tablosunda serbest kümenin kazancının ~%88'ini alan satır.
TAVANLAR = (1, 27, 81, 729)

#: Gerçek bütçe — sahibinin haftalık 210.000 TL'si, ₺10 kolon.
VARSAYILAN_BUTCE = 21_000

#: A kesitinin senaryo boyu. A tek bir cetvel ister (plan sabit, cetvel
#: değişir) ve o cetvel gerçek bütçedeki banko sayısına, yani sapmanın
#: ÖLÇÜLDÜĞÜ kümeye karşılık gelir. Tarama B'nin işi.
A_SENARYO_SAYI = 6


def _bos() -> dict:
    return {t: {"p_senaryo": [], "p_taban": [], "isabet": [],
                "kupon": 0, "eksen": 0, "kolon": 0} for t in TAVANLAR}


def _sezon_kirilimi(sezonlar: Sequence[str], kesit: dict) -> list[dict]:
    """A kesitinin sezon sezon kalibrasyonu — sönüm sınavı.

    Hafta sayıları sezona göre eşitsizdir (17 · 31 · 30 · 36) ve bu bilerek
    düzeltilmiyor: `plan_kalibrasyonu` Poisson-binom kurduğu için her
    sezonun kendi `p`lerini kullanır, havuzlanmış bir oranla değil.
    """
    out = []
    for sz in sorted(set(sezonlar)):
        idx = [i for i, s in enumerate(sezonlar) if s == sz]
        out.append({"sezon": sz, **plan_kalibrasyonu(
            [kesit["p_taban"][i] for i in idx],
            [kesit["isabet"][i] for i in idx])})
        out[-1]["beklenen_sapmali"] = sum(kesit["p_senaryo"][i] for i in idx)
    return out


def kos(butce: int, sapma: float = BANKO_SAPMASI,
        sayilar: Sequence[int] = TARANAN_SAYI) -> dict:
    """Her senaryo × tavan için A ve B kesitlerini tek geçişte toplar."""
    haftalar = tam_haftalar(ikramiye_tablolari())
    n = len(haftalar)
    if not n:
        raise RuntimeError("Tam hafta bulunamadi — oran arsivi eksik.")

    # 0 taban demektir ve her zaman taranır: taban olmadan hiçbir senaryo
    # okunamaz.
    sayilar = sorted(set(sayilar) | {0})
    A = _bos()
    B = {s: _bos() for s in sayilar}
    sezonlar: list[str] = []

    for sezon, _w, lst in haftalar:
        sezonlar.append(sezon)
        probs, gercek = hafta_probs(lst)
        a_probs = sapma_uygula(probs, sapma, A_SENARYO_SAYI)

        for s in sayilar:
            s_probs = probs if s == 0 else sapma_uygula(probs, sapma, s)
            seri = coklu_plan_serisi(s_probs, butce, TAVANLAR)
            for t in TAVANLAR:
                plan = seri[t]
                b = B[s][t]
                b["p_senaryo"].append(plan.p_onbes)
                # ASIL sayı: sapmalı cetvelin seçtiği planın TABAN modelde
                # ne değdiği. Sapmalı cetvelle ölçmek kendini doğrulardı.
                b["p_taban"].append(p_onbes(probs, plan.kuponlar))
                b["isabet"].append(int(isabet(plan.kuponlar, gercek)))
                b["kupon"] += plan.kupon_sayisi
                b["eksen"] += len(plan.eksen)
                b["kolon"] += plan.kolon
                if s == 0:
                    # A kesiti: aynı taban planı, iki cetvel.
                    A[t]["p_taban"].append(plan.p_onbes)
                    A[t]["p_senaryo"].append(p_onbes(a_probs, plan.kuponlar))
                    A[t]["isabet"].append(int(isabet(plan.kuponlar, gercek)))

    return {
        "hafta": n, "butce": butce, "sapma": sapma,
        "a_senaryo_sayi": A_SENARYO_SAYI,
        "kalibrasyon": [{
            "tavan": t,
            "taban": plan_kalibrasyonu(A[t]["p_taban"], A[t]["isabet"]),
            "senaryo": plan_kalibrasyonu(A[t]["p_senaryo"], A[t]["isabet"]),
            # §3.64'ün kararını belirleyen şey sapmanın BÜYÜKLÜĞÜ değil
            # sezonlara göre SÖNMESİYDİ. O sınav burada da koşmalı, yoksa
            # aynı hata (işareti görüp sönümü kaçırmak) tekrar edilir.
            "sezon": _sezon_kirilimi(sezonlar, A[t]),
        } for t in TAVANLAR],
        "karar": [{
            "sayi": s,
            "satirlar": [{
                "tavan": t,
                "kupon_ort": B[s][t]["kupon"] / n,
                "eksen_ort": B[s][t]["eksen"] / n,
                "kolon_ort": B[s][t]["kolon"] / n,
                "p_senaryo": sum(B[s][t]["p_senaryo"]) / n,
                "p_taban": sum(B[s][t]["p_taban"]) / n,
                "isabet": int(sum(B[s][t]["isabet"])),
            } for t in TAVANLAR],
        } for s in sayilar],
    }


def bas(c: dict) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon "
          f"({c['butce'] * 10:,} TL)   sapma: +{c['sapma']:.1%}\n")

    print(f"A · KALIBRASYON — plan SABIT (taban), cetvel degisir "
          f"(sapma en emin {c['a_senaryo_sayi']} macta)")
    print(f"{'kupon':>7} {'cetvel':>9} {'beklenen':>9} {'gozlenen':>9} "
          f"{'oran':>7} {'iki yanli':>10}")
    for r in c["kalibrasyon"]:
        for ad, k in (("taban", r["taban"]), ("sapmali", r["senaryo"])):
            print(f"{r['tavan']:>7} {ad:>9} {k['beklenen']:>9.2f} "
                  f"{k['gozlenen']:>9} {k['oran']:>7.2f} "
                  f"{k['iki_yanli']:>10.4f}")

    print("\nA · SEZON — sapma SONUYOR mu (§3.64'un kararini belirleyen sinav)")
    print(f"{'kupon':>7} {'sezon':>9} {'hafta':>6} {'beklenen':>9} "
          f"{'sapmali':>8} {'gozlenen':>9} {'oran':>7} {'iki yanli':>10}")
    for r in c["kalibrasyon"]:
        for sz in r["sezon"]:
            print(f"{r['tavan']:>7} {sz['sezon']:>9} {sz['hafta']:>6} "
                  f"{sz['beklenen']:>9.2f} {sz['beklenen_sapmali']:>8.2f} "
                  f"{sz['gozlenen']:>9} {sz['oran']:>7.2f} "
                  f"{sz['iki_yanli']:>10.4f}")
        print()

    print("\nB · KARAR — plan sapmali cetvelle kurulur, TABAN cetvelle olculur")
    print(f"{'sayi':>5} {'kupon':>7} {'eksen':>6} {'kolon':>8} "
          f"{'P senaryo':>10} {'P taban':>9} {'gozlenen':>9}")
    for blok in c["karar"]:
        for r in blok["satirlar"]:
            not_ = "  <- bugun" if blok["sayi"] == 0 and r["tavan"] == 1 \
                else ""
            print(f"{blok['sayi']:>5} {r['kupon_ort']:>7,.0f} "
                  f"{r['eksen_ort']:>6.1f} {r['kolon_ort']:>8,.0f} "
                  f"{r['p_senaryo']:>10.3%} {r['p_taban']:>9.3%} "
                  f"{r['isabet']:>6}/{c['hafta']:<3}{not_}")
        print()


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 21.000 = 210.000 TL)")
    ap.add_argument("--sapma", type=float, default=BANKO_SAPMASI,
                    help=f"senaryo sapmasi (varsayilan {BANKO_SAPMASI})")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    c = kos(a.butce, a.sapma)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
    else:
        bas(c)


if __name__ == "__main__":
    main()
