"""Kalabalık modeli — havuz ekseninin **ölçülmemiş** olan tek parçası.

`getiri.KALABALIK_MODELLERI` bugüne kadar üç modelden ibaretti ve **üçü de
varsayımdı**: `orneklem` (kalabalık piyasa olasılığından çekiyor), `favori`
(herkes favoriyi işaretliyor) ve `oynanma` (tek platformun kaydı, n = 4).
§3.34 ilk ikisi arasında **22 kat** getiri farkı ölçtü ve şunu yazdı:

    *"Bu eksende belirsizliğin kaynağı tahminci değil, kalabalık."*

O belirsizlik hiç ölçülmemişti — oysa ölçmeye yetecek veri arşivde duruyordu.

─── Neyin üzerine oturuyor: 448 gözlem ───────────────────────────────────

`data/sportoto_arsiv` her hafta için **kademe başına kazanan adedini**
taşıyor (223 hafta), `data/odds` + `data/st_history` kuponun 15 maçını ve
piyasa oranını (114 hafta). Kesişimde **112 hafta × 4 kademe** var ve bu,
kalabalığın ortak dağılımının **doğrudan gözlemidir**.

§6.3b *"≈71 ikramiyeli hafta gerekiyor, elde 1 var"* diyordu; o güç analizi
`kişi başı ikramiye ↔ crowd_ratio` regresyonu içindi. Kazanan adetleri çok
daha bilgili bir gözlemdir ve **geçmişte zaten duruyordu**.

─── Model: iki bükülme, bir güç ──────────────────────────────────────────

Bir halk kolonunun `i` maçında `s` sembolünü işaretleme payı::

    o_i(s)  ∝  p_i(s)^λ · (1 + δ·[s = "0"]) · (1 + h·[s = "1"])

`λ = 1` kalabalığın piyasa olasılığından çektiği anlamına gelir (`orneklem`);
`λ → ∞` herkesin favoriyi işaretlemesi (`favori`). Yani model bu ikisini
**içine alır** ve aralarındaki yeri ölçer.

─── Ölçek nasıl düşüyor: kademeler arası oran ────────────────────────────

Haftalık toplam kolon sayısı `N` bilinmiyor ve bilinmesi de gerekmiyor.
Gözlenen kazanan adetleri `N · P(k)` ile orantılıdır, dolayısıyla
**kademeler arası oranlar `N`'den bağımsızdır** ve modelin şeklini tek
başına tanımlar. Uyum bu yüzden `(14, 13, 12)` üçlüsü üzerinde çok terimli
olabilirlikle kurulur.

**15. kademe bilerek dışarıda.** `super_toto_degerlendir.havuz_karnesi`
notunun ölçtüğü ayrım: 14/13/12 **kolon** sayar, 15 ise **kupon** — bir
kuponun en fazla bir kolonu on beşi birden tutturabilir (iki kolon tanım
gereği en az bir maçta ayrışır). Aynı olabilirliğe karıştırılamazlar.

**Kazanan adedi ağırlık DEĞİLDİR.** Bir haftanın 40.000 kazananı 40.000
bağımsız gözlem değil, aynı 15 maçın 40.000 kez sayılmasıdır. Olabilirlik
bu yüzden hafta başına normalize edilir; ham sayıyla ağırlıklandırmak
kanıtı yüz binlerce kat şişirirdi.

─── Ölçülen: `favori` iki kez birden çürüdü ──────────────────────────────

`capraz_dogrula` (sezon dışarıda bırakmalı) ve `ima_edilen_kolon` (havuzla
bağımsız çapraz kontrol) aynı yere varıyor ve ayrıntısı
`docs/KAZANMA_PLANI.md`'de: `favori` modeli hafta başına ~4 kat kötü uyuyor
**ve** haftada 10¹⁷ kolonluk fiziksel olarak imkânsız bir havuz ima ediyor.

Bunun §3.34 için sonucu doğrudandır: 22 katlık belirsizlik aralığının
`favori` ucu **kapanır**. Kalabalık, piyasa olasılığının yakınındadır.

    python -m spor_toto.kalabalik            # kestirim + capraz dogrulama
    python -m spor_toto.kalabalik --havuz    # bagimsiz kolon-sayisi sinavi
"""
from __future__ import annotations

import argparse
import json
import random
from typing import Any, NamedTuple

import numpy as np

from .core import SEMBOLLER
from .karne import ikramiye_tablolari, kupon_kesiti

#: Uyumun kurulduğu kademeler — **kolon** sayanlar. 15 dışarıda (kupon sayar).
KADEMELER: tuple[int, ...] = (14, 13, 12)

#: Olasılık tabanı: sıfır paya `log 0` uygulanmasın diye.
TABAN = 1e-9

#: `favori` modelinin sayısal karşılığı. Sonsuz yerine büyük bir üs: argmax
#: sembolün payı 1'e, ötekiler sıfıra gider ve aritmetik taşmaz.
FAVORI_USSU = 25.0


class Kalabalik(NamedTuple):
    """Kalabalık modelinin üç parametresi.

    ``lam``
        Favoriye yığılma keskinliği. 1 = piyasa olasılığı (`orneklem`),
        büyüdükçe kalabalık favoriye piyasadan **daha çok** yığılır.
    ``delta``
        Beraberlik iştahı — güç yasasının üstüne binen çarpan.
    ``h``
        Ev sahibi yanlılığı, aynı biçimde.
    """

    lam: float
    delta: float
    h: float


#: `getiri.KALABALIK_MODELLERI`'nin iki varsayımının bu modeldeki karşılığı.
ORNEKLEM = Kalabalik(1.0, 0.0, 0.0)

#: Kestirimin başlangıç noktası — modül düzeyinde tekil (B008).
BASLANGIC = Kalabalik(1.5, 0.0, 0.0)
FAVORI = Kalabalik(FAVORI_USSU, 0.0, 0.0)

#: **Ölçülen** model — ve bilerek **tek parametreli**.
#:
#: `λ = 1,7608`, hafta düzeyinde bootstrap %95 aralığı **[1,669, 1,865]**.
#: Aralık 1'i içermiyor: kalabalık favoriye piyasadan **daha keskin**
#: yığılıyor ve bu artık bir varsayım değil ölçüm.
#:
#: **δ ve h neden sıfır.** Üç parametreli uyum denendi ve iki şey ölçüldü:
#: (1) sezon sezon kestirildiğinde `δ` −0,19 ↔ +0,61, `h` −0,26 ↔ +0,50
#: arasında **işaret değiştiriyor** — yani gürültü; (2) sezon dışarıda
#: bırakmalı karşılaştırmada tek parametreli model üç parametreliden
#: ayırt edilemiyor (fark −0,00012, %95 [−0,00047, +0,00012], sıfırı
#: kesiyor). Kazanmayan parametre modelde durmaz.
#:
#: `python -m spor_toto.kalabalik` ile yeniden üretilir; künyesi
#: `docs/KAZANMA_PLANI.md` Faz K'dadır.
OLCULEN = Kalabalik(1.7608, 0.0, 0.0)


def oynanma_paylari(probs_listesi: list[dict[str, float]],
                    model: Kalabalik) -> list[dict[str, float]]:
    """Her maç için kalabalığın sembol payları — normalize edilmiş.

    `orneklem` modeli piyasayı olduğu gibi kopyalar::

        >>> p = [{"1": 0.5, "0": 0.3, "2": 0.2}]
        >>> o = oynanma_paylari(p, ORNEKLEM)[0]
        >>> round(o["1"], 6), round(o["0"], 6), round(o["2"], 6)
        (0.5, 0.3, 0.2)

    `favori` modeli bütün payı en olası sembole yığar::

        >>> round(oynanma_paylari(p, FAVORI)[0]["1"], 4)
        1.0
    """
    out: list[dict[str, float]] = []
    for p in probs_listesi:
        ham = {s: max(float(p.get(s, 0.0)), TABAN) ** model.lam
               for s in SEMBOLLER}
        ham["0"] *= 1.0 + model.delta
        ham["1"] *= 1.0 + model.h
        toplam = sum(ham.values())
        out.append({s: ham[s] / toplam for s in SEMBOLLER})
    return out


def kademe_dagilimi(paylar: list[dict[str, float]],
                    gercek: list[str]) -> np.ndarray:
    """Rastgele bir halk kolonunun `k` tutturma olasılığı — Poisson-binom.

    `dp[k]` = tam `k` maç doğru. Maçlar bağımsız işaretlendiği varsayılır;
    bu varsayım `docs/KADEME_OLASILIKLARI.md` §9'da zaten yazılı bir sınırdır.
    """
    dp = np.array([1.0])
    for pay, dogru in zip(paylar, gercek):
        q = pay.get(dogru, 0.0)
        yeni = np.zeros(len(dp) + 1)
        yeni[:-1] += dp * (1.0 - q)
        yeni[1:] += dp * q
        dp = yeni
    return dp


def veri_seti() -> list[dict[str, Any]]:
    """Uyumun kesiti: 15 maçında oran olan **ve** kademe adetleri bilinen hafta."""
    ars = ikramiye_tablolari()
    out: list[dict[str, Any]] = []
    for h in kupon_kesiti():
        tablo = ars[(h["sezon"], h["hafta"])]
        kaz = {k: tablo[k].get("winners") for k in KADEMELER if k in tablo}
        if len(kaz) < len(KADEMELER) or any(not v for v in kaz.values()):
            continue
        out.append({"sezon": h["sezon"], "hafta": h["hafta"],
                    "probs": h["probs"], "gercek": h["gercek"], "kazanan": kaz})
    return out


def hafta_nll(satir: dict[str, Any], model: Kalabalik) -> float:
    """Bir haftanın negatif log-olabilirliği — **hafta başına normalize.**

    Ağırlık kazanan adedi değil, adetlerin *payı*: aynı haftanın kazananları
    bağımsız gözlem değildir (modül başlığı).
    """
    paylar = oynanma_paylari(satir["probs"], model)
    dp = kademe_dagilimi(paylar, satir["gercek"])
    p = np.array([dp[k] for k in KADEMELER])
    if p.sum() <= 0:
        return float("inf")
    p = p / p.sum()
    obs = np.array([float(satir["kazanan"][k]) for k in KADEMELER])
    return -float((obs / obs.sum() * np.log(np.maximum(p, 1e-300))).sum())


def nll(satirlar: list[dict[str, Any]], model: Kalabalik) -> float:
    """Kesitin toplam negatif log-olabilirliği."""
    return sum(hafta_nll(s, model) for s in satirlar)


def kestir_lam(satirlar: list[dict[str, Any]]) -> Kalabalik:
    """**Birincil kestirim**: yalnızca `λ`, `δ = h = 0`.

    Sadelik bir zevk değil ölçüm sonucudur — `OLCULEN` künyesindeki iki
    gerekçe. Tek boyut olduğu için arama da kesin: `minimize_scalar`
    sınırlı aralıkta.
    """
    from scipy.optimize import minimize_scalar

    r = minimize_scalar(lambda L: nll(satirlar, Kalabalik(float(L), 0.0, 0.0)),
                        bounds=(0.2, 8.0), method="bounded")
    return Kalabalik(float(r.x), 0.0, 0.0)


def kestir(satirlar: list[dict[str, Any]],
           baslangic: Kalabalik = BASLANGIC) -> Kalabalik:
    """Üç parametreli kestirim — **karşılaştırma için**, varsayılan değil.

    `kestir_lam`e üstünlüğü ölçüldü ve **bulunamadı**; burada duruyor ki
    "denendi mi" sorusunun cevabı kodda olsun.
    """
    from scipy.optimize import minimize

    def hedef(v: np.ndarray) -> float:
        if v[0] <= 0 or v[1] <= -0.99 or v[2] <= -0.99:
            return 1e9
        return nll(satirlar, Kalabalik(float(v[0]), float(v[1]), float(v[2])))

    r = minimize(hedef, np.array(baslangic), method="Nelder-Mead",
                 options={"xatol": 1e-4, "fatol": 1e-6, "maxiter": 3000})
    return Kalabalik(float(r.x[0]), float(r.x[1]), float(r.x[2]))


def _bootstrap(fark: list[float], tohum: int = 17,
               n: int = 20_000) -> tuple[float, float]:
    if not fark:
        return (0.0, 0.0)
    rnd = random.Random(tohum)
    m = len(fark)
    dag = sorted(sum(fark[rnd.randrange(m)] for _ in range(m)) / m
                 for _ in range(n))
    return dag[int(0.025 * n)], dag[int(0.975 * n)]


def capraz_dogrula(satirlar: list[dict[str, Any]]) -> dict[str, Any]:
    """K4 — sezon dışarıda bırakmalı çapraz doğrulama, **önceden yazılmış kural.**

    Geçti sayılması için üçü birden: tutulan sezonun NLL'inde `orneklem` ve
    `favori` geçilmeli, hafta düzeyinde bootstrap %95 aralığı sıfırı
    kesmemeli, ve dört sezonun dördünde de aynı yön çıkmalı.
    """
    sezonlar = sorted({s["sezon"] for s in satirlar})
    kat: list[dict[str, Any]] = []
    f_orn: list[float] = []
    f_fav: list[float] = []
    for s in sezonlar:
        egit = [r for r in satirlar if r["sezon"] != s]
        test = [r for r in satirlar if r["sezon"] == s]
        if not egit or not test:
            continue
        par = kestir_lam(egit)
        a = [hafta_nll(r, par) for r in test]
        b = [hafta_nll(r, ORNEKLEM) for r in test]
        c = [hafta_nll(r, FAVORI) for r in test]
        f_orn += [x - y for x, y in zip(a, b)]
        f_fav += [x - y for x, y in zip(a, c)]
        kat.append({"sezon": s, "hafta": len(test), "parametre": par._asdict(),
                    "olculen": float(np.mean(a)), "orneklem": float(np.mean(b)),
                    "favori": float(np.mean(c)),
                    "onde": bool(np.mean(a) < np.mean(b))})
    lo_o, hi_o = _bootstrap(f_orn)
    lo_f, hi_f = _bootstrap(f_fav)
    gecti = (all(k["onde"] for k in kat) and hi_o < 0 and hi_f < 0 and bool(kat))
    return {
        "katlar": kat,
        "orneklem_farki": {"ortalama": float(np.mean(f_orn)) if f_orn else 0.0,
                           "alt": lo_o, "ust": hi_o},
        "favori_farki": {"ortalama": float(np.mean(f_fav)) if f_fav else 0.0,
                         "alt": lo_f, "ust": hi_f},
        "ayni_yon": sum(1 for k in kat if k["onde"]),
        "kat_sayisi": len(kat),
        "gecti": gecti,
    }


def ima_edilen_kolon(satirlar: list[dict[str, Any]],
                     model: Kalabalik) -> list[dict[str, Any]]:
    """K5 — modelin ima ettiği haftalık kolon sayısı `N = kazanan₁₂ / P(12)`.

    **Bağımsız sınav.** Uyum kademeler arası orana bakar ve `N`'yi hiç
    görmez; buradan çıkan `N` ise dağıtılan havuzla karşılaştırılabilir.
    Model doğruysa ikisi **sezon içinde** birlikte hareket etmelidir.

    Karşılaştırma sezon içinde yapılır çünkü havuz nominal TL'dir ve dört
    sezonda 72 kat büyümüştür (`karne` modül başlığı); havuzlanmış korelasyon
    o eğilimi sinyal sanar ve ölçüldüğünde **işaret bile değiştirir**.
    """
    from .havuz import arsiv_haftalari

    havuz = {(h["season_key"], h["week"]): (h.get("havuz") or {})
             for h in arsiv_haftalari()}
    out: list[dict[str, Any]] = []
    for r in satirlar:
        hv = havuz.get((r["sezon"], r["hafta"])) or {}
        dagitilan = hv.get("dagitilan")
        if not dagitilan:
            continue
        dp = kademe_dagilimi(oynanma_paylari(r["probs"], model), r["gercek"])
        if dp[12] <= 0:
            continue
        out.append({"sezon": r["sezon"], "hafta": r["hafta"],
                    "N": float(r["kazanan"][12]) / float(dp[12]),
                    "dagitilan": float(dagitilan)})
    return out


def havuz_sinavi(satirlar: list[dict[str, Any]],
                 model: Kalabalik) -> dict[str, Any]:
    """`ima_edilen_kolon`u sezon içi korelasyona çevirir."""
    rows = ima_edilen_kolon(satirlar, model)
    kat = []
    for s in sorted({r["sezon"] for r in rows}):
        alt = [r for r in rows if r["sezon"] == s]
        if len(alt) < 3:
            continue
        n = np.log([r["N"] for r in alt])
        p = np.log([r["dagitilan"] for r in alt])
        kat.append({"sezon": s, "hafta": len(alt),
                    "r": float(np.corrcoef(n, p)[0, 1]),
                    "medyan_N": float(np.median([r["N"] for r in alt]))})
    return {"sezonlar": kat,
            "ortalama_r": float(np.mean([k["r"] for k in kat])) if kat else 0.0}


def _main(argv: list[str] | None = None) -> int:  # pragma: no cover - elle
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--havuz", action="store_true",
                    help="bagimsiz kolon-sayisi sinavi")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    veri = veri_seti()
    if a.havuz:
        cikti = {ad: havuz_sinavi(veri, m) for ad, m in
                 (("olculen", OLCULEN), ("orneklem", ORNEKLEM),
                  ("favori", FAVORI))}
        if a.json:
            print(json.dumps(cikti, ensure_ascii=False))
            return 0
        print("\nBAGIMSIZ SINAV — ima edilen kolon <-> dagitilan havuz")
        print("(sezon ICINDE; havuz nominal TL ve dort sezonda 72 kat buyudu)\n")
        for ad, s in cikti.items():
            print(f"  {ad:>9}: ort r = {s['ortalama_r']:+.3f}   "
                  f"medyan N = " + " · ".join(
                      f"{k['sezon']} {k['medyan_N']:,.0f}"
                      for k in s["sezonlar"]))
        return 0

    par = kestir_lam(veri)
    cv = capraz_dogrula(veri)
    if a.json:
        print(json.dumps({"parametre": par._asdict(), "capraz": cv},
                         ensure_ascii=False))
        return 0
    print(f"\nKalabalik modeli — {len(veri)} hafta x {len(KADEMELER)} kademe")
    print(f"  tam kesit : lambda {par.lam:.4f}  (delta ve h SIFIR — "
          f"kazanmadilar, OLCULEN kunyesi)")
    print(f"\n{'tutulan sezon':>14}{'hafta':>7}{'olculen':>10}{'orneklem':>10}"
          f"{'favori':>10}")
    for k in cv["katlar"]:
        print(f"{k['sezon']:>14}{k['hafta']:>7}{k['olculen']:>10.4f}"
              f"{k['orneklem']:>10.4f}{k['favori']:>10.4f}")
    for ad, x in (("orneklem", cv["orneklem_farki"]),
                  ("favori", cv["favori_farki"])):
        print(f"\n  olculen - {ad:<9}: ort {x['ortalama']:+.5f}  "
              f"%95 [{x['alt']:+.5f}, {x['ust']:+.5f}]  "
              f"{'SIFIRI KESMIYOR' if x['ust'] < 0 else 'sifiri kesiyor'}")
    print(f"\n  ayni yon: {cv['ayni_yon']}/{cv['kat_sayisi']}   "
          f"GECTI: {cv['gecti']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
