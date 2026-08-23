"""Markov zincirleri — 14-garanti bağlamında sıralı risk.

İki zincir
----------
1) Küme-içi hayatta kalma (IN / OUT)
   Her maçta sonuç seçim kümesinde mi?
   OUT emici: 14-garanti bu senaryoda devreye girmez.

2) Hata bütçesi (0 / 1 / 2+)
   Seçim kümesi içinde kalındığı varsayımıyla, en yakın kolona
   göre birikmiş hata. 2+ emici (garanti dışı).
   Geçişler: maç maç, kullanıcı (veya posterior) olasılıklarıyla.

Not: Kaplama kodunun kendisi değişmez; zincir yalnızca sıralı
olasiliksal risk profili verir. 14-garantiyi bozmaz.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .core import Encoder, Point, ball
from .ortak import normalize_olasilik

#: `bayes` ile birebir ayni govdeydi; tek kaynak artik `ortak`.
_norm = normalize_olasilik


def selection_survival_chain(
    enc: Encoder,
    probs: Sequence[dict[str, float]],
) -> dict:
    """
    Durumlar: IN (tüm maçlar şimdiye kadar seçimde), OUT (emici).

    Dönüş:
      p_in_after[k]: k maç sonra hâlâ IN olasılığı (k=0..15)
      p_survive: tüm 15 maç IN = p_kume_ici

    Gövde eskiden bir de `transitions` (maç bazlı p_stay/p_exit) taşırdı.
    Kaldırıldı: onu gösteren panel bilerek silinmişti (gerekçe
    `panels-analiz.HataButcesiPanel` doc'unda — aynı sayılar girdi
    kartındaki kütle çubuğunda zaten canlı duruyor), yani her `/api/solve`
    cevabında hiç kimsenin okumadığı 15 kayıt gidiyordu.
    """
    if len(probs) != enc.total_len:
        raise ValueError(
            f"{len(probs)} olasılık, {enc.total_len} maç bekleniyordu")

    p_in = 1.0
    p_in_after = [1.0]
    for i, sel in enumerate(enc.selections):
        pr = _norm(probs[i])
        p_in *= sum(pr[s] for s in sel)
        p_in_after.append(round(p_in, 8))

    return {
        "states": ["IN", "OUT"],
        "p_in_after": p_in_after,
        "p_survive": round(p_in, 8),
    }


def error_budget_chain(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[dict[str, float]],
) -> dict:
    """
    Hata bütçesi Markov zinciri (0 → 1 → 2+).

    Her maç için:
      - Banko: doğru sembol → hata yok; aksi → +1 hata
        (yalnızca seçim içi mass normalize edilerek koşullu)
      - Değişken: en yakın kolona göre sembol eşleşmesi
        yaklaşık: seçim içi mass'te 'en olası kolon sembolü' ile uyum

    Daha doğru hesap: her kolon için ayrı mesafe birikimi, sonda min.
    Burada kolon başına yol olasılığı ile min-mesafe dağılımı (tam).
    """
    if len(probs) != enc.total_len:
        raise ValueError(
            f"{len(probs)} olasılık, {enc.total_len} maç bekleniyordu")
    if not cols:
        return {
            "states": ["0", "1", "2+"],
            "p_final": {"0": 0.0, "1": 0.0, "2+": 1.0},
            "p_garanti": 0.0,
            "p_in_and_garanti": 0.0,
        }

    # Kolon bazlı: her kolon için P(path) ve distance
    # distance = banko hataları + değişken Hamming
    # Min distance dağılımı: tüm outcome uzayını dolaşmak pahalı;
    # bunun yerine her kolonun tam eşleşme olasılığını ve
    # d=1 komşuluk mass'ini geometry ile birleştir.

    # Tam (ama değişken uzay üzerinden) — space küçükse exact
    space = enc.space_size()
    if space <= 4096 and enc.n > 0:
        return _error_budget_exact(enc, cols, probs)
    return _error_budget_column_union(enc, cols, probs)


def _error_budget_exact(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[dict[str, float]],
) -> dict:
    """Değişken uzayı tarayarak min-mesafe dağılımı (küme-içi koşullu değil, tam)."""
    from itertools import product

    # Banko faktörü
    banko_p = 1.0
    for pos, sym in zip(enc.banko_pos, enc.banko_syms):
        pr = _norm(probs[pos])
        banko_p *= pr.get(sym, 0.0)
    # banko yanlışsa sonuç seçim dışı → garanti devreye girmez
    # (min mesafe tanımı seçim içinde)

    # Değişken nokta olasılığı
    p_dist = {0: 0.0, 1: 0.0, 2: 0.0}
    p_kume = 0.0

    if enc.n == 0:
        p_kume = banko_p
        p_dist[0] = banko_p
    else:
        for var in product(*[range(k) for k in enc.alphabet_sizes]):
            # nokta olasılığı
            pc = banko_p
            for i, pos in enumerate(enc.variable_pos):
                sym = enc.variable_syms[i][var[i]]
                pr = _norm(probs[pos])
                pc *= pr.get(sym, 0.0)
            if pc <= 0:
                continue
            # seçim içinde mi? (değişken semboller zaten seçimden)
            p_kume += pc
            d = min(sum(a != b for a, b in zip(var, c)) for c in cols)
            if d <= 0:
                p_dist[0] += pc
            elif d == 1:
                p_dist[1] += pc
            else:
                p_dist[2] += pc

    # Yapisal kaplama durumu. Olasilik dagilimi tek basina bunu soylemez:
    # yukaridaki dongu pc<=0 olan noktalari atliyor, yani sifir olasilikli
    # bir acik nokta orada gorunmez. UI her iki dalda ayni alanlari
    # bekledigi icin burada da hesaplanir.
    kapsanan: set = set()
    for c in cols:
        kapsanan.update(ball(c, enc.alphabet_sizes))
    toplam_nokta = math.prod(enc.alphabet_sizes) if enc.alphabet_sizes else 1

    total_g = p_dist[0] + p_dist[1]
    return {
        "states": ["0", "1", "2+"],
        "p_final": {
            "0": round(p_dist[0], 8),
            "1": round(p_dist[1], 8),
            "2+": round(p_dist[2], 8),
        },
        "p_garanti": round(total_g, 8),
        "p_kume_ici": round(p_kume, 8),
        "p_in_and_garanti": round(total_g, 8),
        "acik_nokta": toplam_nokta - len(kapsanan),
        "tam_kaplama": len(kapsanan) >= toplam_nokta,
        "method": "exact_space",
    }


def _error_budget_column_union(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[dict[str, float]],
) -> dict:
    """
    Buyuk uzay: d<=1 kutlesi kolonlarin r=1 toplarinin BIRLESIMI uzerinden.

    DIKKAT - burada onceden sessiz bir hata vardi: p_garanti dogrudan
    p_kume_ici'ye esitleniyordu, yani "sonuc secim kumendeyse en fazla 1
    hata vardir" varsayiliyordu. Bu yalnizca kaplama TAMSA dogrudur.
    Kaplama eksikse (maxcov modu, ya da kesilmis acgozlu) acikta kalan
    noktalar d>=2'dedir ve garanti devreye girmez. Eski surum 8192
    noktalik uzayda tek kolonla 8178 nokta acikken p_garanti=1.0 ve
    p("2+")=0.0 raporluyordu - yani garantisi olmayan tek modda %100
    garanti gosteriyordu.

    Ikinci duzeltme: "2+" artik _error_budget_exact ile ayni anlamda,
    yani KUME ICI olup d>=2 olan kutle. Eski surum oraya kume DISI
    kutleyi (1 - p_kume) koyuyordu; iki dal farkli sey sayiyordu.
    """
    sizes = enc.alphabet_sizes
    # Normalize edilmis olasiliklari bir kez hesapla; asagidaki donguler
    # bunlari nokta basina yeniden hesaplamamali.
    norm_p = [_norm(p) for p in probs]

    banko_p = 1.0
    for pos, sym in zip(enc.banko_pos, enc.banko_syms):
        banko_p *= norm_p[pos].get(sym, 0.0)

    def _nokta_olasiligi(pt: Point) -> float:
        pc = banko_p
        for i, pos in enumerate(enc.variable_pos):
            pc *= norm_p[pos].get(enc.variable_syms[i][pt[i]], 0.0)
        return pc

    p15 = sum(_nokta_olasiligi(c) for c in cols)

    p_kume = 1.0
    for i, sel in enumerate(enc.selections):
        p_kume *= sum(norm_p[i][s] for s in sel)

    # Toplarin birlesimi: hem kaplama testini hem kapsanan kutleyi verir.
    # Maliyet O(kolon x top) - p15 dongusuyle ayni buyukluk sinifinda.
    kapsanan: set = set()
    for c in cols:
        kapsanan.update(ball(c, sizes))
    total = math.prod(sizes) if sizes else 1
    tam_kaplama = len(kapsanan) >= total

    if tam_kaplama:
        # Tum uzay kapsanmis: kume ici kutlenin tamami d<=1'de.
        # Uzayi taramaya gerek yok.
        p_kapsanan = p_kume
    else:
        p_kapsanan = sum(_nokta_olasiligi(pt) for pt in kapsanan)

    return {
        "states": ["0", "1", "2+"],
        "p_final": {
            "0": round(p15, 8),
            "1": round(max(0.0, p_kapsanan - p15), 8),
            "2+": round(max(0.0, p_kume - p_kapsanan), 8),
        },
        "p_garanti": round(p_kapsanan, 8),
        "p_kume_ici": round(p_kume, 8),
        "p_in_and_garanti": round(p_kapsanan, 8),
        "acik_nokta": total - len(kapsanan),
        "tam_kaplama": tam_kaplama,
        "method": "column_union" if tam_kaplama else "column_union_partial",
    }


def markov_report(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[dict[str, float]],
) -> dict:
    """Birleşik rapor: survival + hata bütçesi."""
    survival = selection_survival_chain(enc, probs)
    budget = error_budget_chain(enc, cols, probs)
    return {
        "survival": survival,
        "error_budget": budget,
        "summary": {
            "p_kume_ici": survival["p_survive"],
            "p_garanti_path": budget["p_garanti"],
            "p0": budget["p_final"]["0"],
            "p1": budget["p_final"]["1"],
            "p2plus": budget["p_final"]["2+"],
            "method": budget.get("method", ""),
        },
    }
