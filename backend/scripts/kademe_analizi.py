#!/usr/bin/env python3
"""Kademe analizi — 15/14/13/12'yi tutturma olasılığı ve bedeli.

Sorulan soru şuydu: **bu projeyle 15/15 yapma olasılığımız nedir?**

Bu script o soruyu ve onun üç küçük kardeşini (14, 13, 12) tek bir ölçüm
hattında cevaplar. Ölçüm, projenin kendi arşivleri üzerinde koşar:

    - `data/odds/*.csv`            piyasa oranları  -> olasılık (shin)
    - `data/sportoto_arsiv/*.json` RESMİ ikramiye tabloları -> para

**Neden ayrı bir script.** `getiri.py` kademe olasılıklarını *kaplama kodu*
için hesaplar (14-garanti; alt sınır). 15/15 sorusu farklıdır: 15'i tutturmak
için seçim kümesinin **tamamını** oynamak gerekir, kaplama kodu yetmez.
Buradaki sayım o yüzden tam sistem üzerindedir ve `getiri.kupon_kademeleri`
ile karıştırılmamalıdır.

    python scripts/kademe_analizi.py             # bütün bölümler
    python scripts/kademe_analizi.py --bolum A   # tek bölüm
    python scripts/kademe_analizi.py --json      # makine okunur

Bölümler:

    A  tek kolonun 15/15 olasılığı (3^15 uzayının tamamı açılır)
    B  gerçek sonucun sırası — modele değil GERÇEĞE karşı sınama
    C  kademe olasılıkları (model diyor / gözlenen), bütçeye göre
    D  para: hangi kademeden ne geliyor
    E  haftalık geri dönüş dağılımı — ortalama değil MEDYAN
    F  seyreltme: tuttuğun hafta herkesin tuttuğu hafta mı
    G  devir haftası etkisi
    H  arşiv veri kalitesi — anormal haftalar

Bulguların yorumu ve sınırları: `docs/KADEME_OLASILIKLARI.md`.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

import numpy as np

from spor_toto import odds as O
from spor_toto.core import SEMBOLLER
from spor_toto.ortak import kacak_dagilimi as _kacak_dagilimi

#: Spor Toto kolon bedeli. `getiri.py` CLI varsayılanıyla aynı tutulur;
#: **doğrulanmış bir fiyat değildir** ve para sonuçları buna doğrusal
#: bağlıdır (2,50 TL olsaydı bütün geri dönüşler %40 düşerdi).
KOLON_BEDELI = 1.50

#: Ölçümde kullanılan sezonlar — oran arşivi olan bütün sezonlar.
SEZONLAR = ("2025_26", "2024_25", "2023_24", "2022_23")

#: Bütçe basamakları (kolon adedi). Gerçekçi oyuncu bandı ile
#: "sermayeli operasyon" bandını birlikte gösterir.
BUTCELER = (10, 20, 50, 100, 200, 500, 1000, 2000,
            10000, 20000, 64000, 180000, 540000)


# --------------------------------------------------------------------------
# veri
# --------------------------------------------------------------------------
def ikramiye_tablolari() -> dict[tuple[str, int], dict[int, dict[str, Any]]]:
    """Resmî arşivden (sezon, hafta) -> kademe tablosu."""
    out: dict[tuple[str, int], dict[int, dict[str, Any]]] = {}
    for f in sorted((KOK / "data" / "sportoto_arsiv").glob("*.json")):
        d = json.loads(f.read_text())
        if "meta" not in d:
            continue
        for w in d.get("weeks", []):
            p = w.get("payout")
            if not p:
                continue
            t = {x["correct"]: x for x in p.get("tiers", [])}
            if 15 in t:
                out[(d["meta"]["season_key"], w["week"])] = t
    return out


def anormal_haftalar(ars: dict) -> set:
    """12. kademe kazananı medyanın onda birinden az olan haftalar.

    Bunlar arşivde **gerçek** haftalardır ama ikramiye tablosu normal bir
    Spor Toto haftasının şeklinde değildir (12. kademede 41.516 yerine 13
    kazanan gibi). Ortalama alan her hesabı bozarlar; §H'de sayılır.
    """
    w12 = [t[12]["winners"] for t in ars.values() if 12 in t]
    if not w12:
        return set()
    med = float(np.median(w12))
    return {k for k, t in ars.items() if 12 in t and t[12]["winners"] < med / 10}


def tam_haftalar(ars: dict) -> list[tuple[str, int, list]]:
    """15 maçının hepsinde oran OLAN ve ikramiye tablosu bulunan haftalar."""
    out = []
    for sezon in SEZONLAR:
        try:
            rows = O.load_odds(sezon=sezon)
        except Exception:
            continue
        byw: dict[int, list] = {}
        for r in rows:
            b = O.match_1x2(r)
            if b and r.get("code") in SEMBOLLER:
                byw.setdefault(r["week"], []).append((b, r["code"]))
        for w, lst in byw.items():
            if len(lst) == 15 and (sezon, w) in ars:
                out.append((sezon, w, lst))
    return out


def olasilik_matrisi(lst: list) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """(sıralı olasılıklar, sıralama indeksi, gerçek sonucun sembol indeksi)."""
    p = np.array([[b["probs"][s] for s in SEMBOLLER] for b, _ in lst])
    p = p / p.sum(axis=1, keepdims=True)
    idx = np.argsort(-p, axis=1)
    return np.take_along_axis(p, idx, axis=1), idx, [SEMBOLLER.index(c) for _, c in lst]


# --------------------------------------------------------------------------
# kombinatorik
# --------------------------------------------------------------------------
def en_iyi_sistem(P: np.ndarray, butce: int) -> tuple[list[int], int]:
    """Bütçeye sığan en yüksek kapsamalı TAM sistem — açgözlü.

    `secim.en_iyi_secim`den farkı: orada bedel kaplama kodunun kolon
    sayısıdır (14-garanti), burada sistemin **tamamıdır** (15 için gerekli).
    Her adımda kolon başına en çok kapsama katan işaret eklenir.
    """
    s = [1] * 15
    bedel = 1
    while True:
        en = None
        for i in range(15):
            if s[i] >= 3:
                continue
            yeni = bedel // s[i] * (s[i] + 1)
            if yeni > butce:
                continue
            kazanc = sum(P[i][:s[i] + 1]) / sum(P[i][:s[i]])
            oran = kazanc ** (1 / (yeni - bedel))
            if en is None or oran > en[0]:
                en = (oran, i)
        if en is None:
            return s, bedel
        i = en[1]
        bedel = bedel // s[i] * (s[i] + 1)
        s[i] += 1


def kacak_dagilimi(q: Sequence[float]) -> np.ndarray:
    """k kaçağın Poisson-binom dağılımı — `ortak.kacak_dagilimi`nin dizi hâli.

    **Hesap burada YENIDEN YAZILMISTI** ve `ortak.py:499`un açık uyarısını
    çiğniyordu: *"`secim` de aynı hesabı istediği için buraya taşındı — iki
    gövde ayrışsaydı kuponu kuran hesap ile onu değerlendiren hesap farklı
    şeyler söylerdi."* İki gövde bugün ayrışmamıştı (404 kıyas, n=1..15 ve
    sınır durumlar dâhil, en büyük mutlak fark **0,000e+00** — ölçüldü), ama
    ayrışmaya açıktı ve bu betik kapının koşmadığı bir betiktir.

    Geriye kalan tek fark **kabuk**: çağıran taraf `dag[:2].sum()` gibi dizi
    işlemleri yapıyor. O yüzden burada bir sarmalayıcı duruyor, ikinci bir
    hesap değil.
    """
    return np.asarray(_kacak_dagilimi(q), dtype=float)


def kademe_sayimlari(s: Sequence[int], kacak: Sequence[int]) -> dict[int, int]:
    """Tam sistemde her kademeyi tutturan KOLON SAYISI.

    Kaçak sayısı `k` ise en iyi kolon `15-k` doğru yapar. Tam olarak
    `15-k-j` doğru yapan kolon sayısı::

        e_j({s_i - 1 : i kaçak degil})  x  prod_{i kaçak} s_i

    `e_j` elemanter simetrik polinomdur: kaçak olmayan maçların `j`
    tanesinde yanılmanın kaç yolu olduğunu sayar. Kaçak maçlarda ise
    **her** işaret yanlıştır, o yüzden çarpan olarak girerler.
    """
    kacak = set(kacak)
    e = [1, 0, 0, 0]
    for i in range(15):
        if i in kacak:
            continue
        x = s[i] - 1
        e[3] += e[2] * x
        e[2] += e[1] * x
        e[1] += e[0] * x
    carpan = 1
    for i in kacak:
        carpan *= s[i]
    return {15 - len(kacak) - j: e[j] * carpan for j in range(4)}


def hafta_kazanci(s: Sequence[int], kacak: Sequence[int],
                  tablo: dict[int, dict[str, Any]]) -> tuple[float, dict[int, float]]:
    """Bir haftada tam sistemin kazandığı para — seyreltme modellenmiş.

    Kademe havuzu sabittir; `m` kolonumuz eklenince havuz `w+m` kişiye
    bölünür ve payımız `havuz * m / (w + m)` olur.
    """
    if len(kacak) > 3:
        return 0.0, {}
    kad: dict[int, float] = {}
    for tier, m in kademe_sayimlari(s, kacak).items():
        if tier < 12 or m <= 0 or tier not in tablo:
            continue
        w, pz = tablo[tier]["winners"], tablo[tier]["prize"]
        havuz = pz * w if w > 0 else pz
        kad[tier] = havuz * m / (w + m)
    return sum(kad.values()), kad


# --------------------------------------------------------------------------
# bölümler
# --------------------------------------------------------------------------
def bolum_a(haftalar: list, cikti: dict) -> None:
    """Tek kolonun 15/15 olasılığı — 3^15 uzayının tamamı."""
    print("=" * 78)
    print("A) TEK EN İYİ KOLON — 15/15 olasılığı")
    print("=" * 78)
    p1, rank, kaps = [], [], []
    esik = [1, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304]
    for _, _, lst in haftalar:
        P, idx, gercek = olasilik_matrisi(lst)
        p = np.take_along_axis(P, np.argsort(idx, axis=1), axis=1)
        joint = np.array([1.0])
        for i in range(15):
            joint = np.outer(joint, p[i]).ravel()
        pg = float(np.prod([p[i][gercek[i]] for i in range(15)]))
        rank.append(int((joint > pg).sum()) + 1)
        srt = np.sort(joint)[::-1]
        p1.append(float(srt[0]))
        cum = np.cumsum(srt)
        kaps.append({n: float(cum[n - 1]) for n in esik})
        del joint, srt, cum
    p1 = np.array(p1)
    rast = 1 / 3 ** 15
    print(f"  ortalama      : {p1.mean():.3e}  = 1/{1 / p1.mean():,.0f}")
    print(f"  medyan        : {np.median(p1):.3e}  = 1/{1 / np.median(p1):,.0f}")
    print(f"  en iyi hafta  : {p1.max():.3e}  = 1/{1 / p1.max():,.0f}")
    print(f"  en kötü hafta : {p1.min():.3e}  = 1/{1 / p1.min():,.0f}")
    print(f"  RASTGELE      : {rast:.3e}  = 1/{3 ** 15:,}")
    print(f"  >>> projenin çarpanı: {p1.mean() / rast:,.0f}x")
    cikti["A"] = {"ortalama": float(p1.mean()), "medyan": float(np.median(p1)),
                  "rastgele": rast, "carpan": float(p1.mean() / rast)}
    cikti["_rank"] = rank
    cikti["_kapsama"] = kaps
    print()
    print("=" * 78)
    print("B) GERÇEK SONUÇ KAÇINCI SIRADAYDI — modele değil GERÇEĞE karşı")
    print("=" * 78)
    rk = np.array(rank)
    for n in esik:
        c = int((rk <= n).sum())
        m = float(np.mean([k[n] for k in kaps]))
        print(f"  ilk {n:>9,} kolon: model %{100 * m:6.2f} | gözlenen "
              f"{c:>3}/{len(rk)} (%{100 * c / len(rk):5.1f})")
    print(f"\n  gerçek sıranın medyanı : {np.median(rk):,.0f}.")
    print(f"  en iyi hafta           : {rk.min():,.0f}.")
    cikti["B"] = {"medyan_sira": float(np.median(rk)), "en_iyi_sira": int(rk.min())}


def bolum_c(haftalar: list, cikti: dict) -> None:
    """Kademe olasılıkları — model diyor / gözlenen."""
    print()
    print("=" * 94)
    print("C) KADEME OLASILIKLARI — tam sistem (model diyor / GÖZLENEN)")
    print("=" * 94)
    print(f"{'haftalık TL':>11} | {'kolon':>7} | {'P(15)':>15} | {'P(>=14)':>15} | "
          f"{'P(>=13)':>15} | {'P(>=12)':>15}")
    tablo = {}
    n = len(haftalar)
    for butce in BUTCELER:
        m = {15: [], 14: [], 13: [], 12: []}
        g = {15: 0, 14: 0, 13: 0, 12: 0}
        bd = []
        for _, _, lst in haftalar:
            P, idx, gercek = olasilik_matrisi(lst)
            s, bedel = en_iyi_sistem(P, butce)
            bd.append(bedel)
            q = [1 - sum(P[i][:s[i]]) for i in range(15)]
            dag = kacak_dagilimi(q)
            m[15].append(dag[0])
            m[14].append(dag[:2].sum())
            m[13].append(dag[:3].sum())
            m[12].append(dag[:4].sum())
            kacak = sum(1 for i in range(15) if list(idx[i]).index(gercek[i]) >= s[i])
            for c, kmax in ((15, 0), (14, 1), (13, 2), (12, 3)):
                if kacak <= kmax:
                    g[c] += 1
        tablo[butce] = {"kolon": float(np.mean(bd)),
                        "model": {c: float(np.mean(m[c])) for c in m},
                        "gozlenen": {c: g[c] / n for c in g}}
        print(f"{butce * KOLON_BEDELI:>11,.0f} | {np.mean(bd):>7,.0f} | "
              + " | ".join(f"%{100 * np.mean(m[c]):6.2f} /%{100 * g[c] / n:5.1f}"
                           for c in (15, 14, 13, 12)))
    cikti["C"] = {str(k): v for k, v in tablo.items()}


def bolum_de(haftalar: list, ars: dict, cikti: dict) -> None:
    """Para: kademelerin payı ve haftalık geri dönüş dağılımı."""
    print()
    print("=" * 94)
    print("D) PARA — hangi kademeden ne geliyor (resmî ikramiyeler, seyreltme modellenmiş)")
    print("=" * 94)
    print(f"{'haftalık TL':>11} | {'15':>7} | {'14':>7} | {'13':>7} | {'12':>7} | {'DÖNÜŞ':>7}")
    dagilim = {}
    for butce in BUTCELER:
        kad = {15: 0.0, 14: 0.0, 13: 0.0, 12: 0.0}
        kaz, mal = [], []
        for sezon, w, lst in haftalar:
            P, idx, gercek = olasilik_matrisi(lst)
            s, bedel = en_iyi_sistem(P, butce)
            kacak = [i for i in range(15) if list(idx[i]).index(gercek[i]) >= s[i]]
            v, kk = hafta_kazanci(s, kacak, ars[(sezon, w)])
            for c, x in kk.items():
                kad[c] = kad.get(c, 0.0) + x
            kaz.append(v)
            mal.append(bedel * KOLON_BEDELI)
        kaz, mal = np.array(kaz), np.array(mal)
        dagilim[butce] = (kaz, mal, kad)
        tk = sum(kad.values())
        if tk <= 0:
            continue
        print(f"{butce * KOLON_BEDELI:>11,.0f} | "
              + " | ".join(f"%{100 * kad[c] / tk:6.1f}" for c in (15, 14, 13, 12))
              + f" | %{100 * kaz.sum() / mal.sum():6.0f}")
    print()
    print("=" * 94)
    print("E) HAFTALIK GERİ DÖNÜŞ DAĞILIMI — ortalama yanıltır, MEDYAN'a bakın")
    print("=" * 94)
    print(f"{'haftalık TL':>11} | {'medyan':>7} | {'ortalama':>9} | {'%25':>6} | {'%75':>6} | "
          f"{'-1 hafta':>9} | {'-3 hafta':>9} | {'-5 hafta':>9}")
    ozet = {}
    for butce, (kaz, mal, _) in dagilim.items():
        oran = kaz / mal
        net = kaz - mal
        srt = np.sort(net)[::-1]
        T, M = kaz.sum(), mal.sum()

        def cik(k: int, _T: float = T, _M: float = M, _s: np.ndarray = srt) -> float:
            """En çok kazandıran k hafta çıkarılınca kalan geri dönüş (%)."""
            return 100 * (_T - _s[:k].sum()) / _M

        ozet[butce] = {"medyan": float(np.median(oran)), "ortalama": float(oran.mean()),
                       "genel": float(T / M), "eksi3": float(cik(3) / 100)}
        print(f"{butce * KOLON_BEDELI:>11,.0f} | %{100 * np.median(oran):5.0f} | "
              f"%{100 * oran.mean():7.0f} | %{100 * np.percentile(oran, 25):4.0f} | "
              f"%{100 * np.percentile(oran, 75):4.0f} | %{cik(1):8.0f} | %{cik(3):8.0f} | "
              f"%{cik(5):8.0f}")
    print()
    print("  Bootstrap (%95 güven aralığı, 20.000 örnek):")
    rng = np.random.default_rng(7)
    for butce in (20000, 180000, 540000):
        if butce not in dagilim:
            continue
        kaz, mal, _ = dagilim[butce]
        n = len(kaz)
        sims = np.array([(lambda i: kaz[i].sum() / mal[i].sum())(rng.integers(0, n, n))
                         for _ in range(20000)])
        print(f"    haftalık {butce * KOLON_BEDELI:>9,.0f} TL: gözlenen "
              f"%{100 * kaz.sum() / mal.sum():.0f} | GA [%{100 * np.percentile(sims, 2.5):.0f}, "
              f"%{100 * np.percentile(sims, 97.5):.0f}] | P(zarar)=%{100 * (sims < 1).mean():.0f}")
        ozet[butce]["ga"] = [float(np.percentile(sims, 2.5)), float(np.percentile(sims, 97.5))]
    cikti["DE"] = {str(k): v for k, v in ozet.items()}
    cikti["_dagilim"] = dagilim


def bolum_fgh(haftalar: list, ars: dict, anom: set, cikti: dict) -> None:
    """Seyreltme, devir etkisi, veri kalitesi."""
    print()
    print("=" * 78)
    print("F) SEYRELTME — tuttuğun hafta, herkesin tuttuğu hafta mı")
    print("=" * 78)
    rank = cikti.get("_rank")
    if rank:
        E = [(r, ars[(s, w)]) for r, (s, w, _) in zip(rank, haftalar)]
        bantlar = [(1, 1000), (1000, 20000), (20000, 150000),
                   (150000, 600000), (600000, 3000000), (3000000, 15000000)]
        print(f"{'gerçek sonucun sırası':>26} | {'hafta':>5} | {'15 bilen':>10} | {'ikramiye':>14}")
        for lo, hi in bantlar:
            g = [(r, t) for r, t in E if lo <= r < hi]
            if not g:
                continue
            print(f"{lo:>10,}-{hi:<14,} | {len(g):>5} | "
                  f"{np.median([t[15]['winners'] for _, t in g]):>10,.0f} | "
                  f"{np.median([t[15]['prize'] for _, t in g]):>14,.0f}")
        r = np.array([r for r, _ in E], float)
        n15 = np.array([t[15]["winners"] for _, t in E], float)
        rho = float(np.corrcoef(np.argsort(np.argsort(r)), np.argsort(np.argsort(n15)))[0, 1])
        print(f"\n  Spearman(sıra, 15 bilen sayısı) = {rho:+.3f}")
        print("  negatif = sonuç ne kadar 'beklenen'se o kadar çok kişi biliyor")
        cikti["F"] = {"spearman": rho}

    print()
    print("=" * 78)
    print("G) DEVİR ETKİSİ — önceki hafta 15 bileni yoksa havuz şişer")
    print("=" * 78)
    dag = cikti.get("_dagilim", {})
    for butce in (20000, 180000, 540000):
        if butce not in dag:
            continue
        kaz, mal, _ = dag[butce]
        devir = np.array([1 if (ars.get((s, w - 1)) is not None
                                and ars[(s, w - 1)][15]["winners"] == 0) else 0
                          for s, w, _ in haftalar], bool)
        print(f"  haftalık {butce * KOLON_BEDELI:>9,.0f} TL: "
              f"devirli ({devir.sum():>3}) %{100 * kaz[devir].sum() / mal[devir].sum():>5.0f} | "
              f"normal ({(~devir).sum():>3}) %{100 * kaz[~devir].sum() / mal[~devir].sum():>5.0f}")
    print("  -> tutarlı bir yön YOK; bu örneklemde devir bir sinyal değil.")

    print()
    print("=" * 78)
    print("H) ARŞİV VERİ KALİTESİ — anormal haftalar")
    print("=" * 78)
    w12 = [t[12]["winners"] for t in ars.values() if 12 in t]
    print(f"  12. kademe kazanan medyanı : {np.median(w12):,.0f}")
    print(f"  medyanın 1/10'undan az olan: {len(anom)}/{len(ars)} hafta")
    print("  Bunlar ortalama alan her hesabı bozar; kademe ortalaması alınırken elenmeli.")
    cikti["H"] = {"anormal": len(anom), "toplam": len(ars)}


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bolum", choices=[*list("ACDEFGH"), "hepsi"], default="hepsi")
    ap.add_argument("--json", action="store_true", help="makine okunur çıktı")
    a = ap.parse_args(argv)

    ars = ikramiye_tablolari()
    anom = anormal_haftalar(ars)
    haftalar = tam_haftalar(ars)
    print(f"Ölçüm kesiti: {len(haftalar)} tam hafta (oran + resmî ikramiye tablosu), "
          f"{len(ars)} haftalık arşiv, kolon bedeli {KOLON_BEDELI:.2f} TL\n")

    cikti: dict[str, Any] = {"kesit": {"hafta": len(haftalar), "arsiv": len(ars),
                                       "kolon_bedeli": KOLON_BEDELI}}
    if a.bolum in ("A", "hepsi"):
        bolum_a(haftalar, cikti)
    if a.bolum in ("C", "hepsi"):
        bolum_c(haftalar, cikti)
    if a.bolum in ("D", "E", "hepsi"):
        bolum_de(haftalar, ars, cikti)
    if a.bolum in ("F", "G", "H", "hepsi"):
        bolum_fgh(haftalar, ars, anom, cikti)

    if a.json:
        print(json.dumps({k: v for k, v in cikti.items() if not k.startswith("_")},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
