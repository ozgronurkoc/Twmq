"""
Seçim dışı fire senaryoları (1-fire / 2-fire, banko-çifte).

`en iyi kolon = 15 - k` KOSULLUDUR: kumenin disina dusen sonuc icin hicbir
sey soylemez. Deponun geri kalani (`olasilik_raporu`,
`match_error_frequency`, `markov`) hep kume ICINI olcer. Bu modul kume
DISINI olcer:

    "Tam k mac isaretlerimin disina cikarsa en iyi kolonum kac tutturur?"

Duzde cevap kapali formda bilinir (`15 - k`) ve bu modul onu SAYARAK
dogrular. Kaplamada oyle degildi: 16 satirin hangi noktalari orttugune
bagliydi ve fire turu (banko mu cifte mi) sonucu degistiriyordu — o fark
olculdu ve duzde kayboldu (bkz. `tests/test_fire_scenarios.py::
test_fire_TURU_artik_fark_etmiyor`).

Iki hesap uretilir:
  fire1 : tam 1 mac secim disinda, digerleri secim icinde
  fire2 : tam 2 mac secim disinda

Sonuclar skor dagilimi, fire TURU (banko/cifte/uclu) ve mac bazinda
ayristirilir. Tur ayrimi pratikte en degerli ciktidir: bankoda yanilmak
ciftede yanilmaktan belirgin sekilde pahalidir.
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from itertools import combinations

import numpy as _np

from .core import SEMBOLLER, Encoder, Point

_SEMBOL_KOD: dict[str, int] = {s: i for i, s in enumerate(SEMBOLLER)}


# ============================================================
# MALIYET
# ============================================================

def fire_maliyeti(enc: Encoder, cols: Sequence[Point], max_fires: int = 2) -> int:
    """
    Hesabi CALISTIRMADAN maliyet tahmini: ayrik senaryo sayisi x kolon sayisi.

    Cagiran taraf sinirlamayi bununla kurar. Kapali formul oldugu icin
    bedelsizdir; boylece "once hesapla, uzun surerse iptal et" gibi bir
    sey gerekmez.
    """
    k = [len(s) for s in enc.selections]
    if not k:
        return 0
    space = math.prod(k)
    failable = [i for i, x in enumerate(k) if x < len(SEMBOLLER)]

    senaryo = 0
    if max_fires >= 1:
        senaryo += sum(space // k[i] for i in failable)
    if max_fires >= 2:
        senaryo += sum(space // (k[i] * k[j]) for i, j in combinations(failable, 2))
    return senaryo * max(1, len(cols))


# ============================================================
# GEOMETRI (numpy)
# ============================================================

def _senaryo_dizisi(
    izinli: list[list[int]],
) -> _np.ndarray:
    """
    Pozisyon basina izinli sembol kodlarinin kartezyen carpimi -> (S, n) int8.

    meshgrid('ij') + C-order ravel, itertools.product ile AYNI sirayi verir;
    esit mesafede ilk kolonun secilmesi acisindan sira onemlidir.
    """
    eksenler = _np.meshgrid(
        *[_np.asarray(v, dtype=_np.int8) for v in izinli], indexing="ij"
    )
    return _np.stack([e.ravel() for e in eksenler], axis=1)


def _min_mesafeler(senaryolar: _np.ndarray, kolonlar: _np.ndarray) -> _np.ndarray:
    """
    Her senaryo icin en yakin kolona Hamming mesafesi.

    analysis.match_error_frequency ile ayni parcali desen: (parca, m, n)
    boolean gecici diziyi birkac MB'ta tutar. Saf Python'da bu dongu
    gercekci bir kuponda dakikalar aliyordu.
    """
    m, n = kolonlar.shape
    S = len(senaryolar)
    out = _np.empty(S, dtype=_np.int16)
    parca = max(1, min(S, 4_000_000 // max(1, m * n)))
    for bas in range(0, S, parca):
        blok = senaryolar[bas:bas + parca]
        d = (blok[:, None, :] != kolonlar[None, :, :]).sum(axis=2)
        out[bas:bas + parca] = d.min(axis=1)
    return out


# ============================================================
# RAPOR
# ============================================================

def fire_scenario_report(
    enc: Encoder,
    cols: Sequence[Point],
    max_fires: int = 2,
) -> dict:
    """
    Seçim dışı fire analizi (küme dışı).

    Tam k maç seçim dışında, diğerleri seçim içinde iken en iyi kolon
    skor dağılımı. Banko / çifte ayrımı ve maç bazlı özet.

    Not: Uniform '1 hata / 2 hata' küme *içi* mesafedir (d=1, d=2).
    Bu rapor seçim *dışı* fire içindir; ikisi farklıdır.

    HIZLANDIRMA (ciktiyi degistirmez)
    ---------------------------------
    Fire olan pozisyonda her kolon kume ICI bir sembol tasir, senaryo ise
    kume DISI bir sembol. Uyusmazlik garantidir; dolayisiyla HANGI kume-disi
    sembolun geldigi hicbir kolonun mesafesini degistirmez. Bu yuzden o
    secim enumere edilmez, sayilabilir bir CARPAN olarak islenir:
    fire kumesi F icin agirlik = prod(len(out_opts[i]) for i in F).
    Agirliklandirma, eski surumun kume-disi sonuclar uzerindeki uniform
    dagilimini birebir korur.
    """
    n = enc.total_len
    sel_sets = [set(s) for s in enc.selections]
    in_opts = [[_SEMBOL_KOD[s] for s in enc.selections[i]] for i in range(n)]
    out_opts = [[_SEMBOL_KOD[s] for s in SEMBOLLER if s not in sel_sets[i]]
                for i in range(n)]
    failable = [i for i in range(n) if out_opts[i]]

    def ftype(i: int) -> str:
        k = len(sel_sets[i])
        if k == 1:
            return "banko"
        if k == 2:
            return "double"
        return "triple"

    out: dict = {
        "note": "Secim disi fire: mac isaret disi. Uniform 1hata/2hata kume ici mesafedir."
    }

    kolonlar = _np.asarray(
        [[_SEMBOL_KOD[s] for s in enc.decode_full(c)] for c in cols],
        dtype=_np.int8,
    ) if cols else _np.empty((0, n), dtype=_np.int8)

    def pack(score_counts: Counter, n_total: int, by_type: dict, by_match: dict) -> dict:
        scores = {}
        pct = {}
        for s in range(n, n - 6, -1):
            cnt = int(score_counts.get(s, 0))
            scores[str(s)] = cnt
            pct[str(s)] = round(100.0 * cnt / n_total, 4) if n_total else 0.0
        for s, cnt in score_counts.items():
            if str(s) not in scores:
                scores[str(s)] = int(cnt)
                pct[str(s)] = round(100.0 * cnt / n_total, 4) if n_total else 0.0

        type_out = {}
        for tname, c in by_type.items():
            tot = sum(c.values())
            if tot == 0:
                continue
            type_out[tname] = {
                "n": tot,
                "scores": {str(k): int(v) for k, v in sorted(c.items(), reverse=True)},
                "pct": {
                    str(k): round(100.0 * v / tot, 4)
                    for k, v in sorted(c.items(), reverse=True)
                },
            }

        match_out = []
        for i in range(n):
            c = by_match.get(i, Counter())
            tot = sum(c.values())
            if tot == 0:
                match_out.append({
                    "mac": i + 1,
                    "type": ftype(i),
                    "n": 0,
                    "can_fail": bool(out_opts[i]),
                    "scores": {},
                    "pct": {},
                })
                continue
            match_out.append({
                "mac": i + 1,
                "type": ftype(i),
                "n": tot,
                "can_fail": True,
                "scores": {str(k): int(v) for k, v in sorted(c.items(), reverse=True)},
                "pct": {
                    str(k): round(100.0 * v / tot, 4)
                    for k, v in sorted(c.items(), reverse=True)
                },
            })

        return {
            "n": n_total,
            "scores": scores,
            "pct": pct,
            "by_type": type_out,
            "by_match": match_out,
            "min_best": min(score_counts.keys()) if score_counts else None,
            "max_best": max(score_counts.keys()) if score_counts else None,
            "p_ge_14": round(100.0 * sum(v for k, v in score_counts.items() if k >= 14) / n_total, 4) if n_total else 0.0,
            "p_ge_13": round(100.0 * sum(v for k, v in score_counts.items() if k >= 13) / n_total, 4) if n_total else 0.0,
            "p_ge_12": round(100.0 * sum(v for k, v in score_counts.items() if k >= 12) / n_total, 4) if n_total else 0.0,
        }

    def skorla(fired: Sequence[int]) -> _np.ndarray | None:
        """Verilen fire kumesi icin skor (dogru sayisi) dizisi."""
        if len(kolonlar) == 0:
            return None
        izinli = [
            [out_opts[k][0]] if k in fired else in_opts[k]
            for k in range(n)
        ]
        senaryolar = _senaryo_dizisi(izinli)
        return (n - _min_mesafeler(senaryolar, kolonlar)).astype(_np.int64)

    if max_fires >= 1:
        sc: Counter = Counter()
        by_type: dict[str, Counter] = {
            "banko": Counter(), "double": Counter(), "triple": Counter()
        }
        by_match: dict[int, Counter] = {i: Counter() for i in range(n)}
        n_total = 0
        for fail_i in failable:
            skorlar = skorla((fail_i,))
            if skorlar is None:
                continue
            agirlik = len(out_opts[fail_i])
            ft = ftype(fail_i)
            sayim = _np.bincount(skorlar, minlength=n + 1)
            for skor, adet in enumerate(sayim):
                if not adet:
                    continue
                pay = int(adet) * agirlik
                sc[skor] += pay
                by_type[ft][skor] += pay
                by_match[fail_i][skor] += pay
                n_total += pay
        out["fire1"] = pack(sc, n_total, by_type, by_match)

    if max_fires >= 2:
        sc = Counter()
        by_type = {
            "banko+banko": Counter(),
            "banko+double": Counter(),
            "double+double": Counter(),
        }
        by_match = {i: Counter() for i in range(n)}
        n_total = 0
        for i, j in combinations(failable, 2):
            skorlar = skorla((i, j))
            if skorlar is None:
                continue
            agirlik = len(out_opts[i]) * len(out_opts[j])
            tkey = "+".join(sorted([ftype(i), ftype(j)]))
            if tkey not in by_type:
                by_type[tkey] = Counter()
            sayim = _np.bincount(skorlar, minlength=n + 1)
            for skor, adet in enumerate(sayim):
                if not adet:
                    continue
                pay = int(adet) * agirlik
                sc[skor] += pay
                by_type[tkey][skor] += pay
                # Her senaryo iki maca birden yazilir: bu, "bu mac fire
                # olanlardan biriyken" kosullu dagilimidir. Dolayisiyla
                # by_match toplamlari n_total'in IKI KATIDIR.
                by_match[i][skor] += pay
                by_match[j][skor] += pay
                n_total += pay
        out["fire2"] = pack(sc, n_total, by_type, by_match)

    return out
