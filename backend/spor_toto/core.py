"""
Spor Toto kapsama (covering code) cekirdegi.

Temel fikir
-----------
Kupon 15 mactan olusur. Her mac icin bir veya birden fazla sembol
secilebilir: '1' (ev sahibi), '0' (beraberlik), '2' (deplasman).
Tek sembollu maclar "banko", cok sembollu maclar "degisken"dir.

14-garanti: secilen ihtimal kumeleri icinde dogru sonuc varsa, oynanan
kolonlardan en az biri en fazla 1 mac hatali olacaktir. Bu, degisken
maclarin olusturdugu Hamming uzayinda yaricapi 1 olan bir KAPLAMA KODU
(covering code) problemidir.

Toplam hata butcesi 1 oldugu icin yalnizca TEK bir alt kume r=1 olabilir;
geri kalan tum maclar zorunlu olarak tam sistemdir (r=0). Iki r=1 blogu
birlestirilirse yaricap 2 olur ve garanti kirilir.
"""

from __future__ import annotations
import re

import heapq
import time as _time
import math
import random
from collections import Counter
from itertools import product
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "SEMBOLLER", "Point", "Sizes", "Row",
    "Encoder", "parse_picks", "parse_probs", "dogrula_secimler",
    "hamming", "ball", "distance_layers", "dogrula_kaplama",
    "hamming74_codewords", "solve_fix16", "solve_by_blocks",
    "solve_heuristic", "greedy_full", "ls_fixed_size",
    "exact_cover", "exact_max_coverage",
    "merge_rows", "row_cost", "sirala_semboller",
    "olasilik_raporu", "butce_danismani", "ButcePlani", "OlasilikRaporu",
    "HAS_SCIPY",
]

# Spor Toto kupon duzeni. Sembollerin ekrana yazilma sirasi budur;
# alfabetik siralama kullanilirsa 1/0 ciftesi "01" gorunur ki kupon
# duzenine aykiridir ve okurken hataya yol acar.
SEMBOLLER: Tuple[str, str, str] = ("1", "0", "2")
_SEMBOL_INDEX: Dict[str, int] = {s: i for i, s in enumerate(SEMBOLLER)}

MAC_SAYISI = 15
HAMMING_BLOK_BOYU = 7
HAMMING_KOLON = 16

Point = Tuple[int, ...]
Sizes = Tuple[int, ...]
Row = Tuple[FrozenSet[int], ...]

try:  # pragma: no cover - ortama bagli
    import numpy as _np
    from scipy.optimize import milp as _milp, LinearConstraint as _LC, Bounds as _Bounds
    from scipy.sparse import lil_matrix as _lil, hstack as _hstack, identity as _ident
    HAS_SCIPY = True
except ImportError:  # pragma: no cover
    HAS_SCIPY = False


# ============================================================
# GIRDI: ayristirma ve dogrulama
# ============================================================

def sirala_semboller(syms: Iterable[str]) -> List[str]:
    """
    Sembolleri kupon duzenine (1, 0, 2) gore siralar.
    Bilinmeyen sembolde KeyError degil, anlasilir bir ValueError firlatir.
    """
    syms = list(syms)
    for s in syms:
        if s not in _SEMBOL_INDEX:
            raise ValueError(
                f"gecersiz sembol {s!r}. Gecerli semboller: "
                f"{'/'.join(SEMBOLLER)}")
    return sorted(syms, key=lambda x: _SEMBOL_INDEX[x])


def dogrula_secimler(selections: Sequence[Sequence[str]], kati: bool = False) -> List[str]:
    """
    Secim listesini dogrular. Hatalarda ValueError firlatir; kritik olmayan
    durumlar uyari metni olarak dondurulur.
    """
    uyarilar: List[str] = []
    if not selections:
        raise ValueError("Secim listesi bos.")
    if len(selections) != MAC_SAYISI:
        msg = (f"Spor Toto {MAC_SAYISI} mactan olusur, "
               f"{len(selections)} mac girildi.")
        if kati:
            raise ValueError(msg)
        uyarilar.append(msg)

    for i, s in enumerate(selections, 1):
        if len(s) == 0:
            raise ValueError(f"{i}. mac icin hic secenek girilmemis.")
        if len(s) != len(set(s)):
            raise ValueError(
                f"{i}. macta tekrar eden sembol var: {''.join(s)}")
        if len(s) > len(SEMBOLLER):
            raise ValueError(
                f"{i}. macta {len(SEMBOLLER)}'ten fazla secenek var: {''.join(s)}")
        for sym in s:
            if sym not in _SEMBOL_INDEX:
                raise ValueError(
                    f"{i}. macta gecersiz sembol {sym!r}. "
                    f"Gecerli semboller: {'/'.join(SEMBOLLER)}")
    return uyarilar


def parse_picks(text: str) -> List[List[str]]:
    """
    '1,10,1,12,0,...' -> [['1'], ['1','0'], ['1'], ['1','2'], ['0'], ...]
    Ayirici olarak virgul, bosluk, noktali virgul veya '/' kabul edilir.
    Ortadaki bos slotlar (ornegin '1,,10') ValueError firlatir; bas/son
    fazla ayiricilar yok sayilir. '1, 10' gibi bosluklu yazim gecerlidir.
    """
    if not text or not text.strip():
        raise ValueError("--picks bos olamaz.")
    tmp = text
    for ch in (";", "/", "|", "\n", "\t"):
        tmp = tmp.replace(ch, ",")
    # Once virgul cevresindeki bosluklari temizle (1, 10 -> 1,10)
    tmp = re.sub(r"\s*,\s*", ",", tmp)
    # Kalan bosluklari ayirici say
    tmp = re.sub(r"\s+", ",", tmp)
    raw_parts = [p.strip() for p in tmp.split(",")]
    while raw_parts and not raw_parts[0]:
        raw_parts.pop(0)
    while raw_parts and not raw_parts[-1]:
        raw_parts.pop()
    if not raw_parts:
        raise ValueError(f"--picks ayristirilamadi: {text!r}")
    if any(not p for p in raw_parts):
        raise ValueError(
            "bos mac slotu: ardisik veya bos ayirici (orn. '1,,10'). "
            "Her mac icin en az bir sembol girin."
        )
    return [sirala_semboller(p) for p in raw_parts]





def parse_probs(text: str, selections: Sequence[Sequence[str]]) -> List[Dict[str, float]]:
    """
    Mac basina olasilik ayristirir. Bicim: mac basina '1:0.5,0:0.3,2:0.2'
    ve maclar ';' ile ayrilir. Eksik semboller 0 kabul edilir.
    Her mac icin toplam 1'e normalize edilir.
    """
    bloklar = [b.strip() for b in text.split(";") if b.strip()]
    if len(bloklar) != len(selections):
        raise ValueError(
            f"--probs {len(bloklar)} mac icerdi, {len(selections)} mac bekleniyordu.")
    out: List[Dict[str, float]] = []
    for i, blok in enumerate(bloklar, 1):
        p: Dict[str, float] = {s: 0.0 for s in SEMBOLLER}
        for parca in blok.split(","):
            parca = parca.strip()
            if not parca:
                continue
            if ":" not in parca:
                raise ValueError(
                    f"{i}. macta gecersiz olasilik parcasi {parca!r}; "
                    f"beklenen bicim '1:0.5'.")
            sym, deger = parca.split(":", 1)
            sym = sym.strip()
            if sym not in _SEMBOL_INDEX:
                raise ValueError(f"{i}. macta gecersiz sembol {sym!r}.")
            try:
                val = float(deger)
            except ValueError:
                raise ValueError(f"{i}. macta sayiya cevrilemedi: {deger!r}.")
            if val < 0:
                raise ValueError(f"{i}. macta negatif olasilik: {val}.")
            p[sym] = val
        toplam = sum(p.values())
        if toplam <= 0:
            raise ValueError(f"{i}. macta tum olasiliklar sifir.")
        out.append({s: v / toplam for s, v in p.items()})
    return out


class Encoder:
    """Sembol listelerini tamsayi koordinatlarina cevirir."""

    def __init__(self, selections: Sequence[Sequence[str]], kati: bool = False):
        self.uyarilar = dogrula_secimler(selections, kati=kati)
        self.selections: List[List[str]] = [sirala_semboller(s) for s in selections]
        self.total_len = len(self.selections)
        self.banko_pos = [i for i, s in enumerate(self.selections) if len(s) == 1]
        self.variable_pos = [i for i, s in enumerate(self.selections) if len(s) > 1]
        self.variable_syms = [self.selections[i] for i in self.variable_pos]
        self.banko_syms = [self.selections[i][0] for i in self.banko_pos]
        self.alphabet_sizes: Sizes = tuple(len(s) for s in self.variable_syms)
        self.n = len(self.variable_pos)

    # -- olculer ------------------------------------------------
    def space_size(self) -> int:
        return math.prod(self.alphabet_sizes) if self.n else 1

    def ball_size(self) -> int:
        return 1 + sum(k - 1 for k in self.alphabet_sizes)

    def lower_bound(self) -> int:
        """Kure-kaplama (sphere covering) alt siniri."""
        if self.n == 0:
            return 1
        return -(-self.space_size() // self.ball_size())

    def double_pos(self) -> List[int]:
        return [i for i, k in enumerate(self.alphabet_sizes) if k == 2]

    def triple_pos(self) -> List[int]:
        return [i for i, k in enumerate(self.alphabet_sizes) if k == 3]

    # -- donusumler ---------------------------------------------
    def variable_space(self):
        return product(*[range(k) for k in self.alphabet_sizes])

    def decode_full(self, var_point: Point) -> Tuple[str, ...]:
        if len(var_point) != self.n:
            raise ValueError(
                f"Nokta {len(var_point)} boyutlu, {self.n} bekleniyordu.")
        full: List[str] = [""] * self.total_len
        for pos, sym in zip(self.banko_pos, self.banko_syms):
            full[pos] = sym
        for i, pos in enumerate(self.variable_pos):
            full[pos] = self.variable_syms[i][var_point[i]]
        return tuple(full)

    def decode_row(self, row: Row) -> Tuple[str, ...]:
        """Cok-isaretli satiri kupon metnine cevirir ('10', '102' gibi)."""
        parts: List[str] = [""] * self.total_len
        for pos, sym in zip(self.banko_pos, self.banko_syms):
            parts[pos] = sym
        for i, pos in enumerate(self.variable_pos):
            parts[pos] = "".join(
                sirala_semboller(self.variable_syms[i][v] for v in row[i]))
        return tuple(parts)


# ============================================================
# GEOMETRI
# ============================================================

def hamming(a: Point, b: Point) -> int:
    return sum(x != y for x, y in zip(a, b))


def ball(point: Point, sizes: Sizes) -> List[Point]:
    """
    r=1 topu. Degisken uzay tam bir kartezyen carpim oldugundan tek bir
    koordinati degistirmek her zaman uzay icinde kalir; uyelik kontrolu
    gerekmez.
    """
    pts = [point]
    for i, k in enumerate(sizes):
        orig = point[i]
        for s in range(k):
            if s != orig:
                pts.append(point[:i] + (s,) + point[i + 1:])
    return pts


def distance_layers(cols: Sequence[Point], sizes: Sizes) -> Counter:
    """
    Her noktanin en yakin kolona uzakligini BFS ile katman katman sayar.

    Naif yontem her nokta icin tum kolonlara mesafe hesaplar: O(|S| x m x n).
    Bu surum toplarla genisler: O(|S| x top). 7 cifte + 4 uclu kuponunda
    olculen fark 8.92 sn -> 0.01 sn idi.
    """
    total = math.prod(sizes) if sizes else 1
    dist: Counter = Counter()
    if not cols:
        return dist
    seen = set(cols)
    dist[0] = len(seen)
    frontier = seen
    d = 0
    while len(seen) < total:
        d += 1
        nxt = set()
        for p in frontier:
            for q in ball(p, sizes):
                if q not in seen:
                    nxt.add(q)
        if not nxt:
            break
        seen |= nxt
        dist[d] = len(nxt)
        frontier = nxt
    return dist


def dogrula_kaplama(cols: Sequence[Point], sizes: Sizes) -> Tuple[int, int]:
    """(en_kotu_mesafe, acik_nokta_sayisi). Bagimsiz dogrulama icin."""
    total = math.prod(sizes) if sizes else 1
    if not cols:
        return (0 if total == 0 else 99), total
    covered = set()
    for c in cols:
        covered.update(ball(c, sizes))
    acik = total - len(covered)
    if acik:
        return 2, acik
    return (1 if len(cols) < total else 0), 0


# ============================================================
# HAMMING(7,4) - MUKEMMEL KOD
# ============================================================

def hamming74_codewords() -> List[Point]:
    """
    Sistematik (7,4) Hamming kodunun 16 kod kelimesi.

    16 x 8 = 128 = 2^7 oldugundan MUKEMMEL (perfect) koddur: her nokta tam
    olarak bir topa dusar. 7 cifte icin 16'dan az kolonla 14-garanti
    matematiksel olarak imkansizdir.
    """
    out: List[Point] = []
    for d1, d2, d3, d4 in product((0, 1), repeat=4):
        out.append((d1, d2, d3, d4,
                    d1 ^ d2 ^ d3,
                    d2 ^ d3 ^ d4,
                    d1 ^ d2 ^ d4))
    return out


def hamming74_variant(variant: int = 0) -> List[Point]:
    """
    Ayni garantiyi veren FARKLI bir 16 kelimelik mukemmel kod uretir.

    Iki donusum de kaplama yaricapini korur:
      - koset kaydirma: her kelimeye sabit bir vektor XOR'lanir
      - koordinat permutasyonu: 7 pozisyon yer degistirir
    variant=0 kanonik kodu dondurur.
    """
    base = hamming74_codewords()
    if variant == 0:
        return base
    rng = random.Random(variant)
    perm = list(range(HAMMING_BLOK_BOYU))
    rng.shuffle(perm)
    coset = tuple(rng.randrange(2) for _ in range(HAMMING_BLOK_BOYU))
    return [tuple(cw[perm[j]] ^ coset[j] for j in range(HAMMING_BLOK_BOYU))
            for cw in base]


# ============================================================
# MOTOR: SABIT 16 SATIR
# ============================================================

class Fix16Hatasi(ValueError):
    """7 cifteden az mac varken sabit 16 satir modu calisamaz."""


def solve_fix16(enc: Encoder, variant: int = 0) -> Tuple[List[Point], str]:
    """
    SABIT 16 SATIR modu.

    7 cifte maci Hamming(7,4) blogunda kapatir (16 kolon, kanitlanmis
    optimal). Bu 7'nin disinda kalan her sey - fazladan cifteler ve tum
    ucluler - "ekstra" sayilir, tam sistem olarak ayni 16 satirin icine
    cifte/kapama isareti seklinde girer.

    Sonuc HER ZAMAN 16 satirdir.
    Bedel = 16 x (ekstralarin secenek sayilari carpimi) kolon.

    14-garanti korunur: ekstra maclarda tum ihtimaller oynandigi icin hata
    payi sifirdir; tum hata butcesi Hamming blogunda kalir, orada da en
    fazla 1 hata olur.
    """
    sizes = enc.alphabet_sizes
    doubles = enc.double_pos()

    if len(doubles) < HAMMING_BLOK_BOYU:
        raise Fix16Hatasi(
            f"Sabit 16 satir modu EN AZ {HAMMING_BLOK_BOYU} CIFTE mac "
            f"gerektirir; su an {len(doubles)} cifte var.\n"
            f"  - Bir maci daha cifte yaparsan bu mod calisir.\n"
            f"  - Ya da --mode auto kullan: eldeki en iyi blogu kendi secer "
            f"(satir sayisi 16 olmayabilir).")

    if variant == 0:
        block_idx = doubles[:HAMMING_BLOK_BOYU]
    else:
        rng = random.Random(variant * 104729)
        block_idx = sorted(rng.sample(doubles, HAMMING_BLOK_BOYU))

    codewords = hamming74_variant(variant)
    block_set = set(block_idx)
    extra_idx = [i for i in range(len(sizes)) if i not in block_set]
    extra_sizes = [sizes[i] for i in extra_idx]
    carpim = math.prod(extra_sizes) if extra_sizes else 1

    cols: List[Point] = []
    extra_combos = list(product(*[range(k) for k in extra_sizes])) or [()]
    for cw in codewords:
        for ec in extra_combos:
            pt = [0] * len(sizes)
            for slot, i in enumerate(block_idx):
                pt[i] = cw[slot]
            for slot, i in enumerate(extra_idx):
                pt[i] = ec[slot]
            cols.append(tuple(pt))

    hb = [enc.variable_pos[i] + 1 for i in block_idx]
    ex = [enc.variable_pos[i] + 1 for i in extra_idx]
    aciklama = f"Hamming blogu = maclar {hb} ({HAMMING_KOLON} satir)"
    if ex:
        aciklama += f" + ekstra tam sistem = maclar {ex} (carpan {carpim})"
    return cols, aciklama


# ============================================================
# MOTOR: KESIN COZUCU (ILP / HiGHS)
# ============================================================

def _kaplama_matrisi(space: List[Point], sizes: Sizes):
    idx = {p: i for i, p in enumerate(space)}
    n = len(space)
    M = _lil((n, n))
    for j, p in enumerate(space):
        for q in ball(p, sizes):
            M[idx[q], j] = 1
    return M.tocsc()


def exact_cover(sizes: Sizes, time_limit: float = 60.0
                ) -> Tuple[Optional[List[Point]], bool]:
    """
    Minimum kaplama kodunu ILP ile bulur.
    Donen: (kolonlar, optimallik_kanitlandi_mi). Cozulemezse (None, False).
    """
    if not HAS_SCIPY or not sizes:
        return None, False
    space = list(product(*[range(k) for k in sizes]))
    M = _kaplama_matrisi(space, sizes)
    res = _milp(c=_np.ones(len(space)),
                constraints=_LC(M, lb=1, ub=_np.inf),
                integrality=_np.ones(len(space)),
                bounds=_Bounds(0, 1),
                options={"time_limit": time_limit, "mip_rel_gap": 0})
    if res.x is None:
        return None, False
    cols = [space[j] for j in range(len(space)) if res.x[j] > 0.5]
    return cols, bool(res.status == 0)


def exact_max_coverage(sizes: Sizes, budget: int, time_limit: float = 120.0
                       ) -> Tuple[Optional[List[Point]], int, bool]:
    """Sabit kolon butcesiyle kapsanan nokta sayisini maksimize eder."""
    if not HAS_SCIPY or not sizes or budget <= 0:
        return None, 0, False
    space = list(product(*[range(k) for k in sizes]))
    n = len(space)
    M = _kaplama_matrisi(space, sizes)
    A = _hstack([M, -_ident(n, format="csc")], format="csc")
    c = _np.concatenate([_np.zeros(n), -_np.ones(n)])
    butce_satiri = _np.concatenate([_np.ones(n), _np.zeros(n)]).reshape(1, -1)
    res = _milp(c=c,
                constraints=[_LC(A, lb=0, ub=_np.inf),
                             _LC(butce_satiri, lb=0, ub=budget)],
                integrality=_np.ones(2 * n),
                bounds=_Bounds(0, 1),
                options={"time_limit": time_limit, "mip_rel_gap": 0})
    if res.x is None:
        return None, 0, False
    cols = [space[j] for j in range(n) if res.x[j] > 0.5]
    return cols, int(round(-res.fun)), bool(res.status == 0)


# ============================================================
# MOTOR: BLOK AYRISTIRMA
# ============================================================

def ternary_hamming4() -> List[Point]:
    """
    Mukemmel uclu (ternary) Hamming kodu [4,2,3]_3: 9 kod kelimesi.
    9 x 9 = 81 = 3^4, yani her nokta tam olarak bir topa duser.
    4 uclu mac icin 9'dan az kolonla 14-garanti imkansizdir.
    Dogrulandi: 9 kelime, min mesafe 3, kaplama yaricapi 1.
    """
    H = ((0, 1, 1, 1), (1, 0, 1, 2))
    return [x for x in product(range(3), repeat=4)
            if all(sum(h[i] * x[i] for i in range(4)) % 3 == 0 for h in H)]


def _carpim_kodu(a: List[Point], b_sizes: Sizes) -> List[Point]:
    """r=1 blogunu tam sistemle carpar (bedel carpilir, garanti korunur)."""
    combos = list(product(*[range(k) for k in b_sizes])) or [()]
    return [tuple(x) + tuple(c) for x in a for c in combos]


#: ILP'nin ISPATLADIGI, cebirsel karsiligi olmayan optimal blok.
#:
#: Asagidaki tablonun oteki girdileri cebirsel yapilardir (Hamming vb.) ve
#: formulden turetilirler. Bu degil: 20 kolonu HiGHS buldu ve optimalligini
#: ispatladi (`exact_cover(...)[1] is True`; kure alt siniri 16, yani sayi
#: formulden okunamiyor). Kaynaga donmesinin tek sebebi bedeli: tek basina
#: ~17,6 sn, ve testler onu her kosuda yeniden cozuyordu — (2,)*8 icin ayni
#: karar zaten verilmisti.
#:
#: Iki bekci var: `block_optimal` onbellekteki her blogu ilk kullanimda
#: dogrular (gecerli kaplama mi), ve `test_engines.py` icindeki yavas
#: isaretli test ILP'yi yeniden kosarak sayinin hala optimal oldugunu
#: denetler. Yani donmus bir yanlis ne sessizce gecerli sayilir, ne de
#: ILP kodlamasi iyilesirse fark edilmeden eskir.
#:
#: Kolonlar siralidir; sira ILP kosumdan kosuma degisebilir, kaynak degismez.
_ILP_3322_22: List[Point] = [
    (0, 0, 0, 1, 0, 1), (0, 0, 1, 1, 1, 0), (0, 1, 0, 0, 1, 0),
    (0, 1, 1, 0, 1, 1), (0, 2, 0, 1, 0, 1), (0, 2, 1, 0, 0, 0),
    (1, 0, 0, 0, 1, 1), (1, 0, 1, 1, 1, 0), (1, 1, 0, 1, 0, 0),
    (1, 1, 1, 1, 0, 1), (1, 2, 0, 0, 1, 1), (1, 2, 1, 0, 0, 0),
    (2, 0, 0, 0, 0, 0), (2, 0, 1, 0, 0, 1), (2, 1, 0, 0, 0, 1),
    (2, 1, 0, 1, 1, 1), (2, 1, 1, 0, 1, 0), (2, 1, 1, 1, 0, 0),
    (2, 2, 0, 1, 1, 0), (2, 2, 1, 1, 1, 1),
]


def _varsayilan_bloklar() -> Dict[Sizes, List[Point]]:
    """
    Onceden bilinen optimal bloklar. ILP'yi beklemeye gerek birakmaz:
    (2,)*8 icin ILP tek basina ~12 sn, (3,3,2,2,2,2) icin ~17,6 sn suruyordu.

    Bir tanesi disinda hepsi cebirseldir (bkz. `_ILP_3322_22`).
    """
    h7 = hamming74_codewords()
    t4 = ternary_hamming4()
    return {
        (2,): [(0,)],
        (2, 2): [(0, 0), (1, 1)],
        (2, 2, 2): [(0, 0, 0), (1, 1, 1)],          # tekrar kodu, mukemmel
        (2,) * 7: h7,                                # Hamming(7,4), mukemmel
        (2,) * 8: _carpim_kodu(h7, (2,)),            # 16 x 2 = 32 = K(8,1)
        (3,): [(0,)],
        (3, 3): [(0, 0), (1, 1), (2, 2)],
        (3, 3, 3, 3): t4,                            # ucluk Hamming, mukemmel
        (3, 3, 3, 3, 3): _carpim_kodu(t4, (3,)),     # 9 x 3 = 27 = K3(5,1)
        (3, 2): [(0, 0), (1, 1)],
        (3, 3, 2, 2, 2, 2): _ILP_3322_22,            # ILP ispatli, K=20
    }


_BLOCK_CACHE: Dict[Sizes, List[Point]] = _varsayilan_bloklar()
_DOGRULANMIS: set = set()


def block_optimal(sizes: Sizes, time_limit: float = 30.0) -> Optional[List[Point]]:
    """
    Verilen blok icin optimal kaplamayi dondurur (onbellekli).

    DIKKAT: donen kolonlarin koordinat sirasi verilen `sizes` sirasiyla
    birebir aynidir. Gelistirme sirasinda burada bir hata vardi: onbellek
    anahtari siralaniyor, donen kolonlar sirasiz eslesiyordu; 3 degerli
    sembol 2 secenekli maca atanip IndexError uretiyordu. Cagiran taraf
    block_sizes'i her zaman ucluler-once sirali kurmalidir.
    """
    if sizes in _BLOCK_CACHE:
        cols = _BLOCK_CACHE[sizes]
        # Onbellege konan cebirsel yapilar ilk kullanimda dogrulanir.
        # (Gelistirme sirasinda hatali bir (3,3,2) yapisi bu kontrolle
        # yakalandi; sessizce garanti kiran bir formul uretecekti.)
        if sizes not in _DOGRULANMIS:
            worst, acik = dogrula_kaplama(cols, sizes)
            if acik or worst > 1:
                raise AssertionError(
                    f"Onbellekteki blok {sizes} gecersiz: {acik} nokta acik.")
            _DOGRULANMIS.add(sizes)
        return cols
    cols, _ = exact_cover(sizes, time_limit=time_limit)
    if cols is None:
        return None
    _BLOCK_CACHE[sizes] = cols
    return cols


def solve_by_blocks(enc: Encoder, max_block_space: int = 256,
                    time_limit: float = 30.0,
                    total_time_limit: Optional[float] = None
                    ) -> Optional[Tuple[List[Point], str]]:
    """
    En ucuz (r=1 blogu + tam sistem) ayristirmasini bulur.

    Blogun hangi maclardan olustugu degil, yalnizca alfabe boyutlarinin
    cokkumesi onemli oldugundan (cifte_sayisi, uclu_sayisi) ciftlerini
    taramak yeterlidir.
    """
    sizes = enc.alphabet_sizes
    if not sizes:
        return None
    double_pos = enc.double_pos()
    triple_pos = enc.triple_pos()

    # Buyuk bloklar genelde daha cok kazandirir; once onlari dene ki zaman
    # butcesi dolsa bile elde iyi bir cozum olsun. Onbellekteki cebirsel
    # yapilar (Hamming vb.) hicbir zaman butceden harcamaz.
    adaylar = []
    for nd in range(len(double_pos) + 1):
        for nt in range(len(triple_pos) + 1):
            if nd + nt == 0:
                continue
            # Sira kritik: block_sizes ile block_idx birebir hizali olmali.
            bs: Sizes = tuple([3] * nt + [2] * nd)
            if math.prod(bs) > max_block_space:
                continue
            adaylar.append((math.prod(bs), bs, triple_pos[:nt] + double_pos[:nd]))
    adaylar.sort(key=lambda a: -a[0])

    baslangic = _time.monotonic()
    bulunanlar: List[Tuple[int, List[int], List[Point]]] = []
    for _, block_sizes, block_idx in adaylar:
        if block_sizes not in _BLOCK_CACHE:
            if total_time_limit is not None and bulunanlar \
                    and _time.monotonic() - baslangic > total_time_limit:
                continue
        cols = block_optimal(block_sizes, time_limit=time_limit)
        if cols is None:
            continue
        rest = [i for i in range(len(sizes)) if i not in set(block_idx)]
        total = len(cols) * (math.prod([sizes[i] for i in rest]) if rest else 1)
        bulunanlar.append((total, block_idx, cols))

    if not bulunanlar:
        return None

    # Ayni bedelde birden fazla blok olabilir; ILP'nin dondurdugu yapisiz
    # cozum kotu sikisirken cebirsel (Hamming vb.) blok cok daha az satir
    # verir. Bedel esitse kupon satiri az olani sec.
    en_az = min(b[0] for b in bulunanlar)
    _, block_idx, block_cols = min(
        (b for b in bulunanlar if b[0] == en_az),
        key=lambda b: len(merge_rows(b[2])))
    block_set = set(block_idx)
    rest_idx = [i for i in range(len(sizes)) if i not in block_set]
    rest_combos = list(product(*[range(sizes[i]) for i in rest_idx])) or [()]

    out: List[Point] = []
    for bc in block_cols:
        for rc in rest_combos:
            pt = [0] * len(sizes)
            for slot, i in enumerate(block_idx):
                pt[i] = bc[slot]
            for slot, i in enumerate(rest_idx):
                pt[i] = rc[slot]
            out.append(tuple(pt))

    aciklama = (f"blok = degisken maclar "
                f"{[enc.variable_pos[i] + 1 for i in block_idx]} "
                f"({len(block_cols)} kolon, kanitlanmis optimal)")
    if rest_idx:
        aciklama += (f" x tam sistem "
                     f"{[enc.variable_pos[i] + 1 for i in rest_idx]} "
                     f"({math.prod([sizes[i] for i in rest_idx])} kombinasyon)")
    return out, aciklama


# ============================================================
# MOTOR: HEURISTIK
# ============================================================

def greedy_full(space: List[Point], sizes: Sizes, rng: random.Random) -> List[Point]:
    """
    Tembel (lazy) max-heap ile klasik acgozlu kume kaplama.
    Aday havuzu tum uzaydir; ornekleme yapilmaz.
    """
    if not space:
        return []
    uncovered = set(space)
    balls = {p: ball(p, sizes) for p in space}
    heap = [(-len(balls[p]), rng.random(), p) for p in space]
    heapq.heapify(heap)
    cols: List[Point] = []
    while uncovered:
        secilen: Optional[Point] = None
        while heap:
            neg_g, tie, p = heapq.heappop(heap)
            g = sum(1 for q in balls[p] if q in uncovered)
            if not heap or g >= -heap[0][0]:
                secilen = p
                break
            heapq.heappush(heap, (-g, tie, p))
        if secilen is None:
            secilen = next(iter(uncovered))
        cols.append(secilen)
        uncovered.difference_update(balls[secilen])
    return cols


def ls_fixed_size(space: List[Point], sizes: Sizes, m: int, iters: int,
                  rng: random.Random, start: Optional[List[Point]] = None
                  ) -> Optional[List[Point]]:
    """
    Sabit m kolonla tam kaplama arar. Amac fonksiyonu: acik nokta sayisi.

    Onceki surumde kabul kosulu "en az 1 boslugu kapat" idi; bu, 8 boslugun
    1'ini kapatan hamleyi kabul edip kapsamayi kiriyordu ve sonrasindaki
    yama adimi kolon ekleyerek telafi ediyordu - yani local search net
    zarardaydi (olcum: 43 -> 56 kolon). Burada hamle yalnizca acik sayisini
    ARTIRMIYORSA kabul edilir; kucuk bir olasilikla kotu hamleye de izin
    verilir ki yerel minimumdan cikilabilsin.
    """
    if m <= 0 or not space:
        return None
    balls = {p: ball(p, sizes) for p in space}
    if start and len(start) >= m:
        cols = list(rng.sample(start, m))
    else:
        cols = [rng.choice(space) for _ in range(m)]

    cnt: Counter = Counter()
    for c in cols:
        cnt.update(balls[c])
    open_pts = {p for p in space if cnt[p] == 0}

    for _ in range(iters):
        if not open_pts:
            return cols
        i = rng.randrange(m)
        old = cols[i]
        for p in balls[old]:
            cnt[p] -= 1
            if cnt[p] == 0:
                open_pts.add(p)
        before = len(open_pts)

        if open_pts and rng.random() < 0.85:
            hedef = rng.choice(tuple(open_pts))
            new = rng.choice(balls[hedef])
        else:
            new = tuple(rng.randrange(k) for k in sizes)

        for p in balls[new]:
            if cnt[p] == 0:
                open_pts.discard(p)
            cnt[p] += 1

        if len(open_pts) <= before or rng.random() < 0.02:
            cols[i] = new
        else:
            for p in balls[new]:
                cnt[p] -= 1
                if cnt[p] == 0:
                    open_pts.add(p)
            for p in balls[old]:
                if cnt[p] == 0:
                    open_pts.discard(p)
                cnt[p] += 1

    return cols if not open_pts else None


def solve_heuristic(enc: Encoder, trials: int = 5, ls_iters: int = 30000,
                    seed: int = 42, restarts: int = 3,
                    log=None) -> List[Point]:
    sizes = enc.alphabet_sizes
    space = list(enc.variable_space())
    lb = enc.lower_bound()

    best: Optional[List[Point]] = None
    for t in range(max(1, trials)):
        cols = greedy_full(space, sizes, random.Random(seed + t))
        if best is None or len(cols) < len(best):
            best = cols
    assert best is not None
    if log:
        log(f"Acgozlu (tum uzay, {trials} tohum): {len(best)} kolon")

    m = len(best) - 1
    while m >= lb:
        bulunan = None
        for r in range(restarts):
            bulunan = ls_fixed_size(space, sizes, m, ls_iters,
                                    random.Random(seed * 7919 + m * 31 + r),
                                    start=best)
            if bulunan is not None:
                break
        if bulunan is None:
            if log:
                log(f"Local search: {m} kolon bulunamadi, {len(best)}'te durdu")
            break
        best = bulunan
        if log:
            log(f"Local search: {m} kolona indirildi")
        m -= 1
    return best


# ============================================================
# SATIR SIKISTIRMA (cok-isaretli kupon satirlari)
# ============================================================

def row_cost(row: Row) -> int:
    return math.prod(len(s) for s in row) if row else 1


def _collapse(rows: List[Row], d: int) -> List[Row]:
    """
    d. koordinat boyunca birlestirir: diger tum koordinatlarda ayni olan
    satirlarin d. kumeleri birlestirilir.

    Bu, ikili (pairwise) birlestirmeyi kapsar ve o koordinat icin
    maksimaldir. Salt ikili birlestirme, olusan gruplar kup olmadiginda
    tikanabiliyordu: 7 ciftelik tam sistem (128 satir) tek satira inmesi
    gerekirken 2 satirda kaliyordu.
    """
    gruplar: Dict[Tuple, FrozenSet[int]] = {}
    sira: List[Tuple] = []
    for r in rows:
        anahtar = r[:d] + r[d + 1:]
        if anahtar in gruplar:
            gruplar[anahtar] = gruplar[anahtar] | r[d]
        else:
            gruplar[anahtar] = r[d]
            sira.append(anahtar)
    return [k[:d] + (gruplar[k],) + k[d:] for k in sira]


def merge_rows(cols: Sequence[Point], attempts: int = 4, seed: int = 0) -> List[Row]:
    """
    Kolonlari cok-isaretli KUPON SATIRLARINA sikistirir (Quine-McCluskey
    mantigi): tek bir koordinatta farkli olan iki satir, o maca cifte veya
    kapama isaretlenerek tek satirda birlesir.

    ONEMLI: bu islem BEDELI DEGISTIRMEZ. Bir satirin maliyeti isaretlerinin
    carpimidir; 16 satir + 1 cifte = 32 kolon bedelidir. Yalnizca elle
    doldurulacak satir sayisi azalir.

    Cok-isaretin bedeli neden dusuremedigi (ispat): mac i'ye a_i isaret
    konursa maliyet prod(a_i), kapsanan nokta prod(a_i) * (1 + sum((k_i -
    a_i)/a_i)). Birim bedel basina verim 1 + sum((k_i - a_i)/a_i) olup
    (k_i - a_i)/a_i <= k_i - 1 esitsizligi geregi tum a_i = 1 iken
    maksimumdur. Yani cifte/kapama koymak kolon basina kapsamayi ancak
    DUSURUR; hicbir zaman artirmaz.

    Birlestirme acgozludur ve sira duyarlidir, bu yuzden birkac farkli
    sirayla denenip en az satirli sonuc secilir.
    """
    if not cols:
        return []
    boyut = len(cols[0])
    taban: List[Row] = [tuple(frozenset([v]) for v in c) for c in cols]
    en_iyi: Optional[List[Row]] = None
    rng = random.Random(seed)

    for deneme in range(max(1, attempts)):
        koordinatlar = list(range(boyut))
        if deneme > 0:
            rng.shuffle(koordinatlar)
        rows = list(taban)
        degisti = True
        while degisti:
            degisti = False
            for d in koordinatlar:
                yeni = _collapse(rows, d)
                if len(yeni) < len(rows):
                    rows = yeni
                    degisti = True
        if en_iyi is None or len(rows) < len(en_iyi):
            en_iyi = rows
        if len(en_iyi) == 1:
            break
    assert en_iyi is not None
    return en_iyi


def rows_to_points(rows: Sequence[Row]) -> List[Point]:
    """Satirlari tekrar tek tek kolonlara acar (dogrulama icin)."""
    out: List[Point] = []
    for row in rows:
        for combo in product(*[sorted(s) for s in row]):
            out.append(tuple(combo))
    return out


# ============================================================
# OLASILIK RAPORU
# ============================================================

class OlasilikRaporu:
    __slots__ = ("p_kume_ici", "p_15", "p_14", "p_tek_kolon_15", "mac_olasiliklari")

    def __init__(self, p_kume_ici: float, p_15: float, p_14: float,
                 p_tek_kolon_15: float, mac_olasiliklari: Sequence[float]):
        self.p_kume_ici = p_kume_ici
        self.p_15 = p_15
        self.p_14 = p_14
        self.p_tek_kolon_15 = p_tek_kolon_15
        self.mac_olasiliklari = list(mac_olasiliklari)


def olasilik_raporu(enc: Encoder, cols: Sequence[Point],
                    probs: Sequence[Dict[str, float]]) -> OlasilikRaporu:
    """
    Kullanicinin kendi olasilik tahminlerine gore formulun basari sansi.

    Hesaplananlar:
      p_kume_ici : tum maclarin gercek sonucunun secim kumende olma olasiligi.
                   14-garanti ancak bu durumda devreye girer.
      p_15       : oynanan kolonlardan birinin 15 tutturma olasiligi.
      p_14       : tam 14 tutturma olasiligi (p_kume_ici - p_15).
      p_tek_kolon_15 : sistem oynamayip, secim kumen icinden her mactan en
                   olasi sonucu alarak TEK kolon oynasaydin 15 tutturma
                   olasiligin (karsilastirma icin).

    DIKKAT: p_15 > p_tek_kolon_15 GARANTI DEGILDIR. Kaplama kodu 15
    olasiligini degil, KAPSAMAYI maksimize eder; en olasi tek nokta
    formulun kolonlari arasinda olmayabilir. Sistemin degeri 14-garantidir,
    15 sansini artirmak degil.

    NOT: bu bir beklenen-deger/kar hesabi DEGILDIR. Ikramiye havuzu, kolon
    bedeli ve kac kisinin tutturdugu hesaba katilmaz.
    """
    if len(probs) != enc.total_len:
        raise ValueError(
            f"{len(probs)} mac icin olasilik verildi, "
            f"{enc.total_len} bekleniyordu.")

    mac_p: List[float] = []
    for i, sec in enumerate(enc.selections):
        mac_p.append(sum(probs[i].get(s, 0.0) for s in sec))
    p_kume_ici = math.prod(mac_p)

    banko_carpani = math.prod(
        probs[pos].get(sym, 0.0) for pos, sym in zip(enc.banko_pos, enc.banko_syms)
    ) if enc.banko_pos else 1.0

    p_15 = 0.0
    for c in cols:
        pc = banko_carpani
        for i, pos in enumerate(enc.variable_pos):
            pc *= probs[pos].get(enc.variable_syms[i][c[i]], 0.0)
        p_15 += pc

    # Secim kumen icindeki en olasi tek kolon
    p_tek = math.prod(
        max((probs[i].get(s, 0.0) for s in sec), default=0.0)
        for i, sec in enumerate(enc.selections))
    return OlasilikRaporu(p_kume_ici, p_15, max(0.0, p_kume_ici - p_15),
                          p_tek, mac_p)


# ============================================================
# BUTCE DANISMANI
# ============================================================

class ButcePlani:
    __slots__ = ("bedel", "satir", "selections", "degisiklikler", "p_kume_ici")

    def __init__(self, bedel: int, satir: int, selections: List[List[str]],
                 degisiklikler: List[str], p_kume_ici: Optional[float]):
        self.bedel = bedel
        self.satir = satir
        self.selections = selections
        self.degisiklikler = degisiklikler
        self.p_kume_ici = p_kume_ici

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ButcePlani bedel={self.bedel} satir={self.satir}>"


def butce_danismani(enc: Encoder, budget: int,
                    probs: Optional[Sequence[Dict[str, float]]] = None,
                    en_fazla: int = 5) -> List[ButcePlani]:
    """
    "Elimde N kolon var, hangi macimi kismaliyim?" sorusunu yanitlar.

    Her degisken mac icin secenek sayisini kucultmeyi (uclu -> cifte ->
    banko) dener; sabit 16 satir modunun calisabilmesi icin en az 7 cifte
    kalmasi gerektigini gozetir. Sabit 16 satir modunda bedel formulu:

        bedel = 16 x prod(blok disi secenekler) = prod(tum secenekler) / 8

    Siralama: once en az secenek feda eden, olasilik verilmisse kume-ici
    kalma olasiligi en yuksek olan plan.
    """
    if budget <= 0:
        raise ValueError("Butce pozitif olmali.")
    sizes = list(enc.alphabet_sizes)
    if not sizes:
        return []

    # Her degisken mac icin: (yeni_boyut, feda_edilen_semboller)
    secenekler: List[List[Tuple[int, Tuple[str, ...]]]] = []
    for i, pos in enumerate(enc.variable_pos):
        syms = enc.variable_syms[i]
        p = probs[pos] if probs else None
        # Dusuk olasilikli sembolleri once at; olasilik yoksa sondan at.
        sirali = sorted(syms, key=lambda s: (-(p[s] if p else 0.0),
                                             _SEMBOL_INDEX[s]))
        mac_secenek = []
        for yeni in range(1, len(syms) + 1):
            kalan = sirali[:yeni]
            atilan = tuple(s for s in syms if s not in kalan)
            mac_secenek.append((yeni, atilan))
        secenekler.append(mac_secenek)

    planlar: List[ButcePlani] = []
    gorulen: set = set()

    for kombo in product(*secenekler):
        yeni_sizes = [k for k, _ in kombo]
        if sum(1 for k in yeni_sizes if k == 2) < HAMMING_BLOK_BOYU:
            continue
        carpim = math.prod(yeni_sizes)
        bedel = carpim // (2 ** HAMMING_BLOK_BOYU) * HAMMING_KOLON
        if bedel > budget:
            continue

        yeni_sel = [list(s) for s in enc.selections]
        degisiklikler: List[str] = []
        for i, (yeni, atilan) in enumerate(kombo):
            if not atilan:
                continue
            pos = enc.variable_pos[i]
            kalan = [s for s in enc.variable_syms[i] if s not in atilan]
            yeni_sel[pos] = sirala_semboller(kalan)
            degisiklikler.append(
                f"{pos + 1}. mac: {''.join(enc.variable_syms[i])} -> "
                f"{''.join(yeni_sel[pos])}")

        anahtar = tuple(tuple(s) for s in yeni_sel)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)

        p_ici = None
        if probs:
            p_ici = math.prod(
                sum(probs[j].get(s, 0.0) for s in yeni_sel[j])
                for j in range(len(yeni_sel)))

        planlar.append(ButcePlani(bedel, HAMMING_KOLON, yeni_sel,
                                  degisiklikler, p_ici))

    planlar.sort(key=lambda pl: (len(pl.degisiklikler),
                                 -(pl.p_kume_ici or 0.0),
                                 -pl.bedel))
    return planlar[:en_fazla]
