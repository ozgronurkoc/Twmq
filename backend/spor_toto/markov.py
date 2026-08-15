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

from typing import Dict, List, Optional, Sequence, Tuple

from .core import SEMBOLLER, Encoder, Point


def _norm(p: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(p.get(s, 0.0))) for s in SEMBOLLER)
    if total <= 0:
        return {s: 1.0 / 3.0 for s in SEMBOLLER}
    return {s: max(0.0, float(p.get(s, 0.0))) / total for s in SEMBOLLER}


def selection_survival_chain(
    enc: Encoder,
    probs: Sequence[Dict[str, float]],
) -> dict:
    """
    Durumlar: IN (tüm maçlar şimdiye kadar seçimde), OUT (emici).

    Dönüş:
      p_in_after[k]: k maç sonra hâlâ IN olasılığı (k=0..15)
      p_survive: tüm 15 maç IN = p_kume_ici
      transitions: maç bazlı P(IN→IN)
    """
    if len(probs) != enc.total_len:
        raise ValueError(
            f"{len(probs)} olasılık, {enc.total_len} maç bekleniyordu")

    p_in = 1.0
    p_in_after = [1.0]
    transitions = []
    for i, sel in enumerate(enc.selections):
        pr = _norm(probs[i])
        p_stay = sum(pr[s] for s in sel)
        transitions.append({
            "mac": i + 1,
            "p_stay": round(p_stay, 6),
            "p_exit": round(1.0 - p_stay, 6),
        })
        p_in *= p_stay
        p_in_after.append(round(p_in, 8))

    return {
        "states": ["IN", "OUT"],
        "p_in_after": p_in_after,
        "p_survive": round(p_in, 8),
        "transitions": transitions,
    }


def error_budget_chain(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[Dict[str, float]],
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
    probs: Sequence[Dict[str, float]],
) -> dict:
    """Değişken uzayı tarayarak min-mesafe dağılımı (küme-içi koşullu değil, tam)."""
    from itertools import product

    # Banko faktörü
    banko_p = 1.0
    banko_fail = False
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
            outcome_ok = True
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
        "method": "exact_space",
    }


def _error_budget_column_union(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[Dict[str, float]],
) -> dict:
    """Büyük uzay: kolon union alt sınırı (P(15) toplamı) + kabaca d=1."""
    banko_p = 1.0
    for pos, sym in zip(enc.banko_pos, enc.banko_syms):
        banko_p *= _norm(probs[pos]).get(sym, 0.0)

    p15 = 0.0
    for c in cols:
        pc = banko_p
        for i, pos in enumerate(enc.variable_pos):
            sym = enc.variable_syms[i][c[i]]
            pc *= _norm(probs[pos]).get(sym, 0.0)
        p15 += pc

    # kume ici
    p_kume = 1.0
    for i, sel in enumerate(enc.selections):
        pr = _norm(probs[i])
        p_kume *= sum(pr[s] for s in sel)

    p14_approx = max(0.0, p_kume - p15)
    return {
        "states": ["0", "1", "2+"],
        "p_final": {
            "0": round(p15, 8),
            "1": round(p14_approx, 8),
            "2+": round(max(0.0, 1.0 - p_kume), 8),
        },
        "p_garanti": round(p_kume, 8),
        "p_kume_ici": round(p_kume, 8),
        "p_in_and_garanti": round(p_kume, 8),
        "method": "column_union_approx",
    }


def markov_report(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[Dict[str, float]],
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
