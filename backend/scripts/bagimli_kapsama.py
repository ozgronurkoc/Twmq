"""Çoklu kuponun kazancı hafta içi **bağımlılık** altında da duruyor mu?

§3.67 aynı bütçede çoklu kuponun `P(15/15)`'i tek sistemin **1,45 katına**
çıkardığını ölçtü. İki sayı da maçları *bağımsız* sayıyor ve `coklu.py`nin
"Sınır" bölümü bunu şöyle bırakmıştı: *"bu her iki şekli de aynı yönde
etkiler, oran görece dayanıklıdır"*. O cümle bir **varsayımdı** — ölçülmedi.

Bu betik onu ölçer. §3.46 hafta içi bağımlılığı `ρ` olarak ölçtü ve tek
kolonun kuyruğuna çevirdi (`kuyruk.py`); burada aynı `a`, aynı tek faktörlü
model, ama **kupon kapsamasına** çevrilir (`kuyruk.kapsama`). Senaryo `ρ`ları
elle yazılmaz, ölçümden gelir (`kuyruk.rapor`).

    cd backend && python scripts/bagimli_kapsama.py
    cd backend && python scripts/bagimli_kapsama.py --butce 21000 --json

─── Durma kuralı — ÖLÇÜM GÖRÜLMEDEN yazıldı ─────────────────────────────

En kötü makul `a`da (kupon kesitinin bootstrap üst sınırı), 114 haftanın
ortalamasında:

* çoklu kuponun tek sisteme **oranı 1'in altına düşerse** ya da bağımsız
  hâldeki orandan **%10'dan fazla gerilerse** → şekil kararı bağımsızlık
  varsayımına bağımlıdır, eksen **yeniden açılır** ve `coklu.py`nin "Sınır"
  cümlesi yanlış sayılır;
* oran bu bandın içinde kalırsa → bağımlılık iki şekli aynı yönde etkiliyor
  demektir; kapsamanın **mutlak** değeri varsayıma bağlı kalır (ve bu zaten
  yazılı), **kararı** taşımaz.

Kural iki yöne de bakıyor: oran büyüyebilir de. Büyürse de kapanır — soru
"çoklu kupon bağımlılıkta bedel ödüyor mu", "kazancı nereden geliyor" değil.

─── Ne ölçülmüyor ────────────────────────────────────────────────────────

Plan her haftada **bağımsızlık altında** kurulur ve bağımlılık yalnızca onu
yeniden fiyatlar. Aramanın kendisini bağımlı hedefe göre koşmak
(`coklu.coklu_plan_serisi`in `p_eksen · p_alt` çarpanlaması tam olarak
bağımsızlıktan gelir) ayrı bir iştir; burada sorulan şey bugünkü planın
iddiasının ayakta kalıp kalmadığıdır. Buna karşılık tavanlar arası
**sıralama** bağımlı hedefte de okunur: bir tavan bağımlılıkta öne geçiyorsa
karar değişebilir demektir ve tablo bunu gösterir.
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
from spor_toto.coklu import coklu_plan_serisi
from spor_toto.kuyruk import KAPSAMA_MODELLERI, kapsama, rapor

#: Kıyaslanan kupon tavanları. 1 bugünkü tek sistemdir, 81 bugünkü
#: `coklu.VARSAYILAN_KUPON_TAVANI`, 729 §3.67'nin üst ucu.
TAVANLAR = (1, 81, 729)


def senaryolar() -> list[dict[str, Any]]:
    """`(ad, ρ, a)` — üçü de ölçümden, hiçbiri elle yazılmadan.

    `kuyruk.rapor` üç senaryoyu zaten kendisi seçiyor (nokta tahmini, korpus
    aralığının üst sınırı, en kötü makul üst sınır) ve `ρ → a` çevirisini
    çözmüş hâlde veriyor. Buradan ikinci bir seçim yapmak iki betiğin farklı
    `ρ`larla koşmasına yol açardı.
    """
    r = rapor()
    return [{"ad": ad, "rho": e["rho"], "a": e["latent_a"]}
            for ad, e in r["kuyruk"].items()]


def kos(butce: int, senaryo_listesi: list[dict[str, Any]] | None = None
        ) -> dict[str, Any]:
    sen = senaryo_listesi if senaryo_listesi is not None else senaryolar()
    haftalar = tam_haftalar(ikramiye_tablolari())
    n = len(haftalar)

    # (senaryo, model, tavan) -> toplam P; `a = 0`da iki model aynı modeldir
    # ve bir kez hesaplanır (`model = None`).
    top: dict[tuple[str, str | None, int], float] = {}
    geride: dict[tuple[str, str | None], int] = {}

    for _sezon, _w, lst in haftalar:
        probs, _gercek = hafta_probs(lst)
        seri = coklu_plan_serisi(probs, butce, TAVANLAR)
        for s in sen:
            modeller: tuple[str | None, ...] = (
                (None,) if s["a"] <= 0.0 else KAPSAMA_MODELLERI)
            for model in modeller:
                p: dict[int, float] = {}
                for t in TAVANLAR:
                    p[t] = kapsama(probs, seri[t].kuponlar, s["a"],
                                   model or "rutbe")
                    top[(s["ad"], model, t)] = (
                        top.get((s["ad"], model, t), 0.0) + p[t])
                anahtar = (s["ad"], model)
                geride[anahtar] = geride.get(anahtar, 0) + int(
                    p[TAVANLAR[-1]] <= p[TAVANLAR[0]])

    satirlar = []
    for s in sen:
        modeller = (None,) if s["a"] <= 0.0 else KAPSAMA_MODELLERI
        for model in modeller:
            ort = {t: top[(s["ad"], model, t)] / n for t in TAVANLAR}
            satirlar.append({
                "senaryo": s["ad"], "rho": s["rho"], "a": s["a"],
                "model": model, "p": {str(t): ort[t] for t in TAVANLAR},
                "oran": ort[TAVANLAR[-1]] / ort[TAVANLAR[0]],
                "en_iyi_tavan": max(TAVANLAR, key=lambda t: ort[t]),
                "hafta_geride": geride[(s["ad"], model)],
            })

    taban = next(r["oran"] for r in satirlar if r["a"] <= 0.0)
    return {"hafta": n, "butce": butce, "tavanlar": list(TAVANLAR),
            "taban_oran": taban, "satirlar": satirlar,
            "karar": _karar(satirlar, taban)}


def _karar(satirlar: list[dict[str, Any]], taban: float) -> dict[str, Any]:
    """Ön kayıtlı kuralı işletir — eşiği burada da yeniden yazmadan."""
    en_kotu = [r for r in satirlar if r["a"] == max(x["a"] for x in satirlar)]
    en_dusuk = min(r["oran"] for r in en_kotu)
    gerileme = 1.0 - en_dusuk / taban
    kapandi = en_dusuk > 1.0 and gerileme <= 0.10
    return {
        "kural": ("en kotu makul a'da oran 1'in altina duserse ya da bagimsiz "
                  "orandan %10'dan fazla gerilerse eksen YENIDEN ACILIR"),
        "en_kotu_oran": en_dusuk, "taban_oran": taban,
        "gerileme": gerileme,
        "karar": ("eksen kapandi" if kapandi
                  else "eksen acik — sekil karari bagimsizliga bagimli"),
    }


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon "
          f"({c['butce'] * 10:,} TL/hafta)\n")
    basliklar = "".join(f"{('tavan ' + str(t)):>13}" for t in c["tavanlar"])
    print(f"{'senaryo':<13} {'model':<8} {'ρ':>9} {'a':>7}{basliklar} "
          f"{'oran':>7} {'en iyi':>7} {'geride':>7}")
    for r in c["satirlar"]:
        hucreler = "".join(f"{r['p'][str(t)]:>12.3%} " for t in c["tavanlar"])
        oran = f"x{r['oran']:.2f}"
        print(f"{r['senaryo']:<13} {(r['model'] or '—'):<8} "
              f"{r['rho']:>+9.5f} {r['a']:>7.4f} {hucreler}"
              f"{oran:>7} {r['en_iyi_tavan']:>7,} "
              f"{r['hafta_geride']:>7}")
    d = c["karar"]
    print(f"\nkural : {d['kural']}")
    print(f"olcum : en kotu oran x{d['en_kotu_oran']:.2f} "
          f"(bagimsiz x{d['taban_oran']:.2f}, gerileme {d['gerileme']:+.1%})")
    print(f"karar : {d['karar'].upper()}")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    c = kos(a.butce)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
    else:
        bas(c)


if __name__ == "__main__":
    main()
