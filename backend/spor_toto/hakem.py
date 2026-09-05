"""E4 — hakem: sütun arayışının son denemesi, **önceden yazılmış kuralla**.

─── Niçin bu ölçüm ────────────────────────────────────────────────────────

§3.24'ün teşhisi netti: *"sorun satır sayısı değil sütun."* On bir model
ailesi kapanış çizgisini geçemedi ve LOFO hiçbir özelliğin taşımadığını
ölçtü — ama bunların hepsi **aynı sütun kümesi** üzerinde koştu. Korpus
football-data'dan yalnızca şut ve korneri alıyor; alınmamış ve hukuken açık
sütunlar var: ilk yarı skoru, faul, kart ve **hakem**.

Hakem bunların içinde tek gerçekten yeni **aile**: ev sahibi yanlılığı ve
kart eğilimi takımdan bağımsız bir değişkendir, yani piyasanın fiyatladığı
takım gücüyle mekanik olarak örtüşmez. Ötekiler (faul, kart, ilk yarı) maçın
kendi sonucundan türer ve **maç öncesi bilinmez** — tahminde kullanılamaz.

─── Kesit: ölçülmüş bir coğrafi sınır ────────────────────────────────────

`build_hakem` ölçtü: football-data hakemi yalnızca **dokuz Britanya
liginde** yazıyor (%100), on üç kıta liginde **hiç yazmıyor** (%0). Korpusa
bağlandığında 31.103 satırın **13.334'ü** (%42,9) hakemli.

Bu yüzden ölçüm korpusun tamamında değil, **hakemi olan ligler** üzerinde
koşar ve piyasa kolu da aynı maçlarla sınırlanır — eşleştirme bozulmaz.
Kesitin daralması gücü düşürür ve bu bir kusur değil, sınırın kendisidir:
%100 kapsamanın olduğu yerde geçemiyorsa, seyreltilmiş bir yerde geçmesi
beklenmez.

─── Özellik: sızıntısız, ve küçültülmüş ──────────────────────────────────

Bir hakemin özelliği yalnızca **o maçtan ÖNCEKİ** maçlarından hesaplanır
(`_gecmis_artiklar`); aynı maçın kendisi hiçbir zaman kendi özelliğine
girmez. Ölçülen şey hakemin *piyasaya göre artığıdır*:

    artık_ev(h) = ortalama[ (ev kazandı mı) − piyasa P(ev) ]   h'nin geçmişi
    artık_ber(h) = ortalama[ (beraberlik mi) − piyasa P(0) ]

Yani "bu hakemin maçlarında ev sahibi piyasanın beklediğinden çok mu
kazanıyor". Ham ortalama az maçta gürültüdür, o yüzden §3.35'in ampirik
Bayes kalıbıyla küçültülür: `B = n / (n + K)`.

─── Durma kuralı — ÖNCEDEN yazıldı ───────────────────────────────────────

Aday, piyasanın üstüne eklendiğinde Brier'i düşürmeli **ve** sezon dışarıda
bırakmalı çapraz doğrulamada hafta düzeyi bootstrap %95 aralığı sıfırı
kesmemeli, **Holm düzeltmesinden sonra**. Geçmezse **sütun ekseni kapanır**
ve `ISTATISTIK_YOL_HARITASI §7`'ye *"denendi, geçmedi"* diye yazılır. Liste
uzatılmaz — birinci turun on bir ölçümüyle aynı disiplin.

    python -m spor_toto.hakem
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from .core import SEMBOLLER
from .odds import ARINDIRMA_VARSAYILAN, implied_probs

KOK = Path(__file__).resolve().parent.parent
HAKEM_DOSYA = KOK / "data" / "hakem" / "hakem.csv"
KORPUS = KOK / "data" / "egitim" / "egitim_korpus.csv"

#: Ampirik Bayes küçültme sabiti: `B = n / (n + K)`. §3.35'in takım
#: küçültmesiyle aynı kalıp ve aynı gerekçe — az maçlı hakem ortalamaya
#: çekilir. 30 maç ≈ bir hakemin bir sezonluk yükü.
KUCULTME_K = 30.0

#: Bootstrap yeniden örnekleme adedi — `evaluate`/`fiyatlar` ile aynı sınıf.
BOOTSTRAP = 20_000

#: Denenen adaylar. **Liste burada donar**: E4 tek denemedir ve geçmezse
#: uzatılmaz. Üçü de aynı geçmişten türer, farkları hangi artığı taşıdıkları.
ADAYLAR: tuple[str, ...] = ("hakem_ev", "hakem_beraberlik", "hakem_ikisi")


def _olasilik(satir: dict[str, str]) -> dict[str, float] | None:
    """Korpus satırının piyasa olasılığı — kapanış, `shin` arındırmalı."""
    try:
        oranlar = {s: float(satir[f"kapanis_{s}"]) for s in SEMBOLLER}
    except (KeyError, TypeError, ValueError):
        return None
    if any(v <= 1.0 for v in oranlar.values()):
        return None
    return implied_probs(oranlar, ARINDIRMA_VARSAYILAN)


def veri_seti() -> list[dict[str, Any]]:
    """Hakemi olan korpus satırları — tarihe göre sıralı (sızıntı için şart).

    Sıra kritiktir: özellik yalnızca **önceki** maçlardan hesaplanacak ve o
    ancak kronolojik bir geçişte doğru olur.
    """
    if not (HAKEM_DOSYA.exists() and KORPUS.exists()):
        return []
    with HAKEM_DOSYA.open(encoding="utf-8") as f:
        hakem = {(r["sezon"], r["lig"], r["tarih"], r["ev"], r["dep"]):
                 r["hakem"] for r in csv.DictReader(f)}
    out: list[dict[str, Any]] = []
    with KORPUS.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = (r["sezon"], r["lig"], r["tarih"], r["ev"], r["dep"])
            h = hakem.get(k)
            if not h or r.get("kod") not in SEMBOLLER:
                continue
            p = _olasilik(r)
            if p is None:
                continue
            out.append({
                "sezon": r["sezon"], "lig": r["lig"], "tarih": r["tarih"],
                "iso": (r["iso_yil"], r["iso_hafta"]),
                "hakem": h, "kod": r["kod"], "probs": p,
            })
    out.sort(key=lambda r: (r["tarih"], r["lig"], r["hakem"]))
    return out


def _gecmis_artiklar(satirlar: list[dict[str, Any]]) -> None:
    """Her satıra hakeminin **o ana kadarki** artıklarını yazar.

    Tek geçişte kronolojik: satır önce okunur (özellik yazılır), sonra
    hakemin birikimine katılır. Bu sıralama sızıntısızlığın kendisidir —
    ters çevrilirse maç kendi özelliğini besler.
    """
    top_ev: dict[str, float] = defaultdict(float)
    top_ber: dict[str, float] = defaultdict(float)
    adet: dict[str, int] = defaultdict(int)
    for r in satirlar:
        h = r["hakem"]
        n = adet[h]
        b = n / (n + KUCULTME_K)
        r["hakem_n"] = n
        r["hakem_ev"] = b * (top_ev[h] / n) if n else 0.0
        r["hakem_beraberlik"] = b * (top_ber[h] / n) if n else 0.0
        top_ev[h] += (1.0 if r["kod"] == "1" else 0.0) - r["probs"]["1"]
        top_ber[h] += (1.0 if r["kod"] == "0" else 0.0) - r["probs"]["0"]
        adet[h] = n + 1


def _brier(p: dict[str, float], kod: str) -> float:
    return sum((p[s] - (1.0 if s == kod else 0.0)) ** 2 for s in SEMBOLLER)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, x))))


def _egit(satirlar: list[dict[str, Any]], alanlar: tuple[str, ...],
          adim: float = 0.5, tur: int = 200) -> list[float]:
    """Piyasanın üstüne **tek katsayılı** düzeltme — `recalibrate` kalıbı.

    Model `logit(p_ev)`'i alır ve seçilen artıkları doğrusal olarak ekler;
    çok parametreli bir aile değildir, çünkü ölçülen soru *"bu sütun bir şey
    taşıyor mu"* — *"en iyi hakem modeli nedir"* değil. Az parametre, az
    aşırı uyum, ve §3.30'un kapasite bulgusuyla tutarlı.
    """
    w = [0.0] * len(alanlar)
    n = len(satirlar)
    if not n:
        return w
    for _ in range(tur):
        egim = [0.0] * len(alanlar)
        for r in satirlar:
            z = math.log(max(r["probs"]["1"], 1e-9)
                         / max(1.0 - r["probs"]["1"], 1e-9))
            for j, ad in enumerate(alanlar):
                z += w[j] * r[ad]
            hata = _sigmoid(z) - (1.0 if r["kod"] == "1" else 0.0)
            for j, ad in enumerate(alanlar):
                egim[j] += hata * r[ad]
        for j in range(len(alanlar)):
            w[j] -= adim * egim[j] / n
    return w


def _uygula(r: dict[str, Any], alanlar: tuple[str, ...],
            w: list[float]) -> dict[str, float]:
    """Düzeltmeyi uygular; ev olasılığı değişir, kalan kütle oranla dağılır."""
    p = r["probs"]
    z = math.log(max(p["1"], 1e-9) / max(1.0 - p["1"], 1e-9))
    for j, ad in enumerate(alanlar):
        z += w[j] * r[ad]
    yeni_ev = min(0.999, max(0.001, _sigmoid(z)))
    kalan = p["0"] + p["2"]
    if kalan <= 0.0:
        return {"1": yeni_ev, "0": (1 - yeni_ev) / 2, "2": (1 - yeni_ev) / 2}
    olcek = (1.0 - yeni_ev) / kalan
    return {"1": yeni_ev, "0": p["0"] * olcek, "2": p["2"] * olcek}


_ALAN: dict[str, tuple[str, ...]] = {
    "hakem_ev": ("hakem_ev",),
    "hakem_beraberlik": ("hakem_beraberlik",),
    "hakem_ikisi": ("hakem_ev", "hakem_beraberlik"),
}


def olc(adaylar: tuple[str, ...] = ADAYLAR,
        tekrar: int = BOOTSTRAP, tohum: int = 41) -> dict[str, Any]:
    """E4'ün ölçümü: sezon dışarıda bırakmalı, hafta bootstrap'i, Holm'lu."""
    from .evaluate import holm

    satirlar = veri_seti()
    if not satirlar:
        return {"mac": 0, "adaylar": [], "hata": "hakem tablosu ya da korpus yok"}
    _gecmis_artiklar(satirlar)
    sezonlar = sorted({r["sezon"] for r in satirlar})

    out: list[dict[str, Any]] = []
    p_degerleri: dict[str, float] = {}
    for ad in adaylar:
        alanlar = _ALAN[ad]
        # Sezon disarida birakmali: her sezon TUTULUR, kalanlarda egitilir.
        hafta: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
        katsayilar: dict[str, list[float]] = {}
        for tut in sezonlar:
            egitim = [r for r in satirlar if r["sezon"] != tut]
            sinav = [r for r in satirlar if r["sezon"] == tut]
            w = _egit(egitim, alanlar)
            katsayilar[tut] = w
            for r in sinav:
                hafta[r["iso"]].append(
                    (_brier(_uygula(r, alanlar, w), r["kod"]),
                     _brier(r["probs"], r["kod"])))
        gruplar = list(hafta.values())
        n = sum(len(g) for g in gruplar)
        if not n:
            continue
        aday_t = sum(x for g in gruplar for x, _ in g)
        ref_t = sum(y for g in gruplar for _, y in g)
        rnd = random.Random(tohum)
        dag = []
        for _ in range(tekrar):
            idx = [rnd.randrange(len(gruplar)) for _ in range(len(gruplar))]
            sn = sum(len(gruplar[i]) for i in idx)
            if not sn:
                continue
            dag.append((sum(x for i in idx for x, _ in gruplar[i])
                        - sum(y for i in idx for _, y in gruplar[i])) / sn)
        dag.sort()
        p = (sum(1 for x in dag if x >= 0.0) + 1) / (len(dag) + 1)
        p_degerleri[ad] = p
        alt = dag[int(0.025 * len(dag))]
        ust = dag[int(0.975 * len(dag))]
        out.append({
            "ad": ad, "n": n, "hafta": len(gruplar),
            "aday_brier": aday_t / n, "piyasa_brier": ref_t / n,
            "fark": (aday_t - ref_t) / n,
            "alt": alt, "ust": ust, "p": p, "gecti": bool(ust < 0.0),
            "katsayilar": {k: [round(x, 5) for x in v]
                           for k, v in katsayilar.items()},
        })
    karar = holm(p_degerleri)
    for satir in out:
        satir["gecti_holm"] = karar.get(satir["ad"])
    ligler = sorted({r["lig"] for r in satirlar})
    return {
        "mac": len(satirlar), "sezon": sezonlar, "lig": ligler,
        "hakem": len({r["hakem"] for r in satirlar}),
        "denenen_aday_sayisi": len(p_degerleri), "adaylar": out,
        "gecen_var_mi": any(s.get("gecti_holm") for s in out),
    }


def yayilim_sinavi(esikler: tuple[int, ...] = (30, 50)) -> list[dict[str, Any]]:
    """Hakemler arası yayılım **şanstan** büyük mü? — varyans ayrışımı.

    `olc()` "geçmedi" diyebilir ve bu iki farklı şeyden gelebilir: etki var
    ama düzeltme onu yakalayamıyor, ya da **etki yok**. İkisi çok farklı
    sonuçlardır ve Brier farkı ikisini ayırmaz.

    Ayrım burada yapılır. Bir hakemin ev-artığı ortalaması, hiçbir hakem
    etkisi olmasa bile sırf örnekleme gürültüsünden sapar; o gürültünün
    büyüklüğü **hesaplanabilir** (`sum p(1−p) / n²`). Gözlenen yayılım
    şanstan büyükse aradaki fark gerçek etkidir::

        Var(gerçek) = Var(gözlenen) − Var(şans)

    Sağ taraf negatif çıkarsa gözlenen yayılım şansın ürettiğinden bile
    küçüktür ve yakalanacak bir etki **yoktur** — düzeltmenin kusuru değil.
    """
    satirlar = veri_seti()
    if not satirlar:
        return []
    gruplar: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in satirlar:
        gruplar[r["hakem"]].append(r)
    out: list[dict[str, Any]] = []
    for esik in esikler:
        buyuk = {k: v for k, v in gruplar.items() if len(v) >= esik}
        if len(buyuk) < 2:
            continue
        ortalamalar = [
            sum((1.0 if r["kod"] == "1" else 0.0) - r["probs"]["1"]
                for r in v) / len(v) for v in buyuk.values()]
        m = sum(ortalamalar) / len(ortalamalar)
        gozlenen = math.sqrt(sum((x - m) ** 2 for x in ortalamalar)
                             / len(ortalamalar))
        sans = math.sqrt(sum(
            sum(r["probs"]["1"] * (1.0 - r["probs"]["1"]) for r in v)
            / len(v) ** 2 for v in buyuk.values()) / len(buyuk))
        artik = gozlenen ** 2 - sans ** 2
        out.append({
            "esik": esik, "hakem": len(buyuk),
            "gozlenen_sd": gozlenen, "sans_sd": sans,
            "oran": gozlenen / sans if sans else None,
            "gercek_etki_sd": math.sqrt(artik) if artik > 0.0 else None,
            "etki_var_mi": artik > 0.0,
        })
    return out


def _main(argv: list[str] | None = None) -> int:  # pragma: no cover - elle
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    s = olc()
    if a.json:
        print(json.dumps(s, ensure_ascii=False))
        return 0
    if not s.get("adaylar"):
        print(s.get("hata", "olculemedi"))
        return 1
    print(f"\nE4 — hakem · {s['mac']:,} mac · {len(s['lig'])} lig "
          f"({', '.join(s['lig'])}) · {s['hakem']} hakem · "
          f"{len(s['sezon'])} sezon disarida birakmali")
    print(f"\n{'aday':>18}{'n':>8}{'piyasa':>10}{'aday':>10}{'fark':>11}"
          f"{'%95 aralik':>26}{'p':>8}{'Holm':>7}")
    for r in s["adaylar"]:
        print(f"{r['ad']:>18}{r['n']:>8,}{r['piyasa_brier']:>10.4f}"
              f"{r['aday_brier']:>10.4f}{r['fark']:>+11.6f}"
              f"   [{r['alt']:>+9.6f}, {r['ust']:>+9.6f}]{r['p']:>8.4f}"
              f"{'GECTI' if r['gecti_holm'] else 'hayir':>7}")
    print(f"\ndenenen aday: {s['denenen_aday_sayisi']} · "
          f"gecen: {'VAR' if s['gecen_var_mi'] else 'YOK'}")

    print("\nYAYILIM SINAVI — hakemler arasi fark SANSTAN buyuk mu?")
    print(f"{'esik':>6}{'hakem':>7}{'gozlenen sd':>13}{'sans sd':>10}"
          f"{'oran':>7}   sonuc")
    for y in yayilim_sinavi():
        sonuc = (f"gercek etki sd {y['gercek_etki_sd']:.4f}"
                 if y["etki_var_mi"] else
                 "gozlenen yayilim SANSTAN DA KUCUK — etki yok")
        print(f"{y['esik']:>6}{y['hakem']:>7}{y['gozlenen_sd']:>13.4f}"
              f"{y['sans_sd']:>10.4f}{y['oran']:>7.2f}   {sonuc}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
