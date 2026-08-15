"""Monte Carlo olasılık simülasyonu ve maç bazlı hata frekansı."""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as _np

from .core import Encoder, Point, SEMBOLLER


def monte_carlo_report(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[Dict[str, float]],
    n_samples: int = 100_000,
    seed: int = 42,
) -> dict:
    """
    Kullanıcı olasılıkları altında Monte Carlo simülasyonu.

    Dönen alanlar (her biri p, pct, se, ci95, count içerir):
      kume_ici, p15, p14, p13, p12

    n_samples < 1 → ValueError (sessiz sıfır rapor yok).
    1 ≤ n_samples < 100 → çalışır ama 'warning' alanı eklenir.
    100 ≤ n_samples < 1000 → yumuşak warning.
    """
    if len(probs) != enc.total_len:
        raise ValueError(
            f"{len(probs)} maç için olasılık verildi, {enc.total_len} bekleniyordu."
        )
    try:
        n_samples = int(n_samples)
    except (TypeError, ValueError) as e:
        raise ValueError(f"n_samples sayi olmali, alindi: {n_samples!r}") from e
    if n_samples < 1:
        raise ValueError(
            f"Monte Carlo icin n_samples >= 1 gerekli (alindi: {n_samples}). "
            f"CLI'de --mc-samples 0 MC'yi kapatir; acmak icin pozitif deger ver."
        )
    warning: Optional[str] = None
    if n_samples < 100:
        warning = (
            f"n_samples={n_samples} cok dusuk; %95 CI guvenilmez. "
            f"En az 1000 (tercihen 10000+) onerilir."
        )
    elif n_samples < 1000:
        warning = (
            f"n_samples={n_samples} dusuk; CI genis kalabilir. "
            f"Karar icin en az 1000, rapor icin 10000+ onerilir."
        )

    rng = random.Random(seed)

    cum: List[List[Tuple[float, str]]] = []
    for i in range(enc.total_len):
        p = probs[i]
        weights = [max(0.0, float(p.get(sym, 0.0))) for sym in SEMBOLLER]
        total = sum(weights)
        if total <= 0:
            weights = [1.0 / 3.0] * 3
        else:
            weights = [w / total for w in weights]
        running = 0.0
        entries: List[Tuple[float, str]] = []
        for w, sym in zip(weights, SEMBOLLER):
            running += w
            entries.append((running, sym))
        if entries:
            entries[-1] = (1.0, entries[-1][1])
        cum.append(entries)

    sel_sets = [set(s) for s in enc.selections]

    n_ici = n_15 = n_14 = n_13 = n_12 = 0

    for _ in range(n_samples):
        outcome: List[str] = []
        for i in range(enc.total_len):
            r = rng.random()
            chosen = cum[i][-1][1]
            for threshold, sym in cum[i]:
                if r <= threshold:
                    chosen = sym
                    break
            outcome.append(chosen)

        if any(outcome[i] not in sel_sets[i] for i in range(enc.total_len)):
            continue
        n_ici += 1

        try:
            var = tuple(
                enc.variable_syms[j].index(outcome[pos])
                for j, pos in enumerate(enc.variable_pos)
            )
        except ValueError:
            continue

        if not cols:
            d = 99
        elif not enc.variable_pos:
            d = 0
        else:
            d = min(sum(a != b for a, b in zip(var, c)) for c in cols)

        dogru = 15 - d
        if dogru >= 15:
            n_15 += 1
        elif dogru == 14:
            n_14 += 1
        elif dogru == 13:
            n_13 += 1
        elif dogru == 12:
            n_12 += 1

    def rate(k: int) -> dict:
        p = k / n_samples if n_samples else 0.0
        se = math.sqrt(p * (1.0 - p) / n_samples) if n_samples else 0.0
        return {
            "p": p,
            "pct": round(100.0 * p, 3),
            "se": se,
            "ci95": round(1.96 * se * 100.0, 3),
            "count": k,
        }

    out = {
        "n_samples": n_samples,
        "kume_ici": rate(n_ici),
        "p15": rate(n_15),
        "p14": rate(n_14),
        "p13": rate(n_13),
        "p12": rate(n_12),
    }
    if warning:
        out["warning"] = warning
    return out


def match_error_frequency(
    enc: Encoder,
    cols: Sequence[Point],
    max_d: int = 2,
) -> dict:
    """
    Uniform varsayım altında, d=1 ve d=2 katmanlarında
    hangi maçların hata ürettiğini sayar.

    Uygulama notu: saf Python'da bu O(uzay x kolon x n) idi ve gerçekçi bir
    kuponda (uzay=10368, kolon=1296) ölçülen süre 10.9 saniyeydi — üstelik
    senkron istek yolunda. Hesap numpy'a taşındı: uzay parçalara bölünür,
    her parça için tüm kolonlara mesafe tek seferde hesaplanır ve en yakın
    kolon `argmin` ile bulunur.

    Davranış birebir korunur: `argmin` de, eski `if d < best_d` döngüsü de
    minimumu veren İLK kolonu seçer.
    """
    if not cols or not enc.alphabet_sizes:
        return {"d1": [], "d2": [], "n1": 0, "n2": 0}

    sizes = enc.alphabet_sizes
    n = len(sizes)
    kolonlar = _np.asarray(cols, dtype=_np.int8)          # (m, n)

    # Uzayı itertools.product ile aynı sırada üret (meshgrid 'ij' + C-order
    # ravel bu sırayı verir). Sıra, eşit mesafede ilk kolonun seçilmesi
    # açısından önemlidir.
    eksenler = _np.meshgrid(*[_np.arange(k, dtype=_np.int8) for k in sizes],
                            indexing="ij")
    uzay = _np.stack([e.ravel() for e in eksenler], axis=1)  # (S, n)

    err_d1 = _np.zeros(n, dtype=_np.int64)
    err_d2 = _np.zeros(n, dtype=_np.int64)
    n1 = n2 = 0

    # Parça boyu: (parca x kolon x n) bool geçici dizisini birkaç MB'ta tut.
    parca = max(1, min(len(uzay), 4_000_000 // max(1, len(kolonlar) * n)))

    for bas in range(0, len(uzay), parca):
        blok = uzay[bas:bas + parca]                                # (b, n)
        d = (blok[:, None, :] != kolonlar[None, :, :]).sum(axis=2)  # (b, m)
        en_yakin = d.argmin(axis=1)
        en_kucuk = d[_np.arange(len(blok)), en_yakin]

        for hedef_d, sayac in ((1, err_d1), (2, err_d2)):
            secim = en_kucuk == hedef_d
            adet = int(secim.sum())
            if not adet:
                continue
            fark = blok[secim] != kolonlar[en_yakin[secim]]          # (k, n)
            sayac += fark.sum(axis=0)
            if hedef_d == 1:
                n1 += adet
            else:
                n2 += adet

    def _counter(vec) -> Counter:
        c: Counter = Counter()
        for i, adet in enumerate(vec):
            if adet:
                c[enc.variable_pos[i] + 1] = int(adet)
        return c

    err_d1, err_d2 = _counter(err_d1), _counter(err_d2)

    def to_list(counter: Counter, total: int) -> List[dict]:
        items = []
        for mac in sorted(counter.keys()):
            cnt = counter[mac]
            items.append({
                "mac": mac,
                "count": cnt,
                "pct": round(100.0 * cnt / total, 2) if total else 0.0,
            })
        return items

    return {
        "d1": to_list(err_d1, max(n1, 1)),
        "d2": to_list(err_d2, max(n2, 1)),
        "n1": n1,
        "n2": n2,
    }
