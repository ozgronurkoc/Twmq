"""
Spor Toto kupon çekirdeği — işaretler, kodlama, olasılık.

Temel fikir
-----------
Kupon 15 mactan olusur. Her mac icin bir veya birden fazla sembol
secilebilir: '1' (ev sahibi), '0' (beraberlik), '2' (deplasman).
Tek sembollu maclar "banko", cok sembollu maclar "degisken"dir.

Oynanan kupon **seçim kümesinin tamamıdır** (düz / tam sistem): bedel
`2^çifte · 3^üçlü` kolon ve gerçek sonuç kümenin içindeyse bir kolon 15
tutturur. Küme dışında kalan her maç (bir "kaçak") en iyi kolonu tam bir
kademe düşürür — yani en iyi kolon `15 − k`'dır, bir alt sınır değil
**eşitlik**.

Bu modül eskiden bir KAPLAMA KODU (covering code) çekirdeğiydi
-------------------------------------------------------------
Yedi çifteyi Hamming(7,4) bloğuna koyup 16 satırda 14-garanti veriyordu:
bedelin 1/8'i, karşılığında en iyi kolon 15 değil 14. Kaplama söküldü
(`docs/DUZ_SISTEME_GECIS.md`): aynı kolon bütçesinde düz, ölçülen her
kademede öndeydi ve sebep sistem değil **şekil**di — "en az 7 çifte" şartı
kaplamayı yayvan şekillere hapsediyordu.

Sökülenler: arama motorları (`exact_cover`, `solve_by_blocks`,
`solve_heuristic`, `greedy_full`, `ls_fixed_size`, `block_optimal`), mesafe
muhasebesi (`hamming`, `ball`, `distance_layers`, `dogrula_kaplama`),
satır sıkıştırma (`merge_rows`), bütçe danışmanı ve `Encoder`'ın kaplama
teorisi metotları (`ball_size`, `lower_bound`). 1.076 satırdan geriye
kalan budur.

`solve_fix16` tek başına `spor_toto/kaplama_arsiv.py`ye taşındı ve orada
**neden durduğu** yazılıdır: 2026/27'nin ilk dört haftası kaplamayla
oynandı, o kuponlar `15 − k` ile değerlendirilemez.

Kolonların üretimi artık `spor_toto/duz.py`nin işidir.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from itertools import product

#: Modulun ilan edilen yuzeyi. Depoda `import *` yok, yani bu liste bir
#: sozlesme degil BELGE: "core'dan disari ne cikar" sorusunun cevabi.
#: `test_core.test_all_modulun_gercek_yuzeyini_sayar` bu listeyi modulun
#: kendisiyle karsilastirir; bir daha sessizce eskiyemez.
__all__ = [
    # Sabitler ve tipler
    "SEMBOLLER", "MAC_SAYISI", "ORNEK_KUPON",
    "Point", "Sizes", "Row", "HAS_SCIPY",
    # Girdi ayristirma ve kodlama
    "Encoder", "parse_picks", "parse_probs", "dogrula_secimler",
    "sirala_semboller",
    # Kupon satiri (cok-isaretli gosterim)
    "row_cost", "rows_to_points",
    # Rapor
    "olasilik_raporu", "OlasilikRaporu",
]

# Spor Toto kupon duzeni. Sembollerin ekrana yazilma sirasi budur;
# alfabetik siralama kullanilirsa 1/0 ciftesi "01" gorunur ki kupon
# duzenine aykiridir ve okurken hataya yol acar.
SEMBOLLER: tuple[str, str, str] = ("1", "0", "2")
_SEMBOL_INDEX: dict[str, int] = {s: i for i, s in enumerate(SEMBOLLER)}

MAC_SAYISI = 15

#: Belgelerdeki, CLI yardimindaki ve saglik kontrollerindeki ornek kupon.
#: `cli` ve `health` bu dizgiyi ayri ayri tasiyordu; biri degistiginde
#: otekinin haberi olmazdi ve "README'deki ornek" ile "olculen ornek"
#: sessizce ayrisirdi.
ORNEK_KUPON = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"

Point = tuple[int, ...]
Sizes = tuple[int, ...]
Row = tuple[frozenset[int], ...]

#: scipy kurulu mu — `/api/meta` ve saglik katmani bunu ilan eder.
#:
#: **Anlami degisti.** Once `exact_cover`in ILP cozucusunu (HiGHS) gecerdi:
#: "scipy yoksa kesin cozucu devre disi". Kaplamayla birlikte o cozucu
#: silindi, yani bayrak artik hicbir MOTORU gecmiyor. Yine de duruyor ve
#: dogru soyluyor: `spor_toto/kuyruk.py` scipy'yi KOSULSUZ import eder
#: (`scipy.special.ndtr/ndtri`), yani scipy yoksa kuyruk katmani hic
#: yuklenmez. Bayragin bekcisi `health._check_meta_sozlesmesi`.
try:  # pragma: no cover - ortama bagli
    import scipy  # noqa: F401
    HAS_SCIPY = True
except ImportError:  # pragma: no cover
    HAS_SCIPY = False


# ============================================================
# GIRDI: ayristirma ve dogrulama
# ============================================================

def sirala_semboller(syms: Iterable[str]) -> list[str]:
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


def dogrula_secimler(selections: Sequence[Sequence[str]], kati: bool = False) -> list[str]:
    """
    Secim listesini dogrular. Hatalarda ValueError firlatir; kritik olmayan
    durumlar uyari metni olarak dondurulur.
    """
    uyarilar: list[str] = []
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


def parse_picks(text: str) -> list[list[str]]:
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





def parse_probs(text: str, selections: Sequence[Sequence[str]]) -> list[dict[str, float]]:
    """
    Mac basina olasilik ayristirir. Bicim: mac basina '1:0.5,0:0.3,2:0.2'
    ve maclar ';' ile ayrilir. Eksik semboller 0 kabul edilir.
    Her mac icin toplam 1'e normalize edilir.
    """
    bloklar = [b.strip() for b in text.split(";") if b.strip()]
    if len(bloklar) != len(selections):
        raise ValueError(
            f"--probs {len(bloklar)} mac icerdi, {len(selections)} mac bekleniyordu.")
    out: list[dict[str, float]] = []
    for i, blok in enumerate(bloklar, 1):
        p: dict[str, float] = dict.fromkeys(SEMBOLLER, 0.0)
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
            except ValueError as e:
                raise ValueError(
                    f"{i}. macta sayiya cevrilemedi: {deger!r}.") from e
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
        self.selections: list[list[str]] = [sirala_semboller(s) for s in selections]
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

    # `ball_size` ve `lower_bound` burada durdu ve KAPLAMA TEORISIYDI:
    # yaricap-1 topunun buyuklugu ve kure-kaplama alt siniri. Duzde
    # oynanan kolon sayisi `space_size()`in ta kendisidir, alt sinir da
    # ustu de o; iki metot da bir soruya degil ARTIK OLMAYAN bir soruya
    # cevap veriyordu.

    def double_pos(self) -> list[int]:
        return [i for i, k in enumerate(self.alphabet_sizes) if k == 2]

    def triple_pos(self) -> list[int]:
        return [i for i, k in enumerate(self.alphabet_sizes) if k == 3]

    # -- donusumler ---------------------------------------------
    def variable_space(self):
        return product(*[range(k) for k in self.alphabet_sizes])

    def decode_full(self, var_point: Point) -> tuple[str, ...]:
        if len(var_point) != self.n:
            raise ValueError(
                f"Nokta {len(var_point)} boyutlu, {self.n} bekleniyordu.")
        full: list[str] = [""] * self.total_len
        for pos, sym in zip(self.banko_pos, self.banko_syms):
            full[pos] = sym
        for i, pos in enumerate(self.variable_pos):
            full[pos] = self.variable_syms[i][var_point[i]]
        return tuple(full)

    def decode_row(self, row: Row) -> tuple[str, ...]:
        """Cok-isaretli satiri kupon metnine cevirir ('10', '102' gibi)."""
        parts: list[str] = [""] * self.total_len
        for pos, sym in zip(self.banko_pos, self.banko_syms):
            parts[pos] = sym
        for i, pos in enumerate(self.variable_pos):
            parts[pos] = "".join(
                sirala_semboller(self.variable_syms[i][v] for v in row[i]))
        return tuple(parts)



# ============================================================
# SATIR SIKISTIRMA (cok-isaretli kupon satirlari)
# ============================================================

def row_cost(row: Row) -> int:
    return math.prod(len(s) for s in row) if row else 1


def rows_to_points(rows: Sequence[Row]) -> list[Point]:
    """Satirlari tekrar tek tek kolonlara acar (dogrulama icin)."""
    out: list[Point] = []
    for row in rows:
        for combo in product(*[sorted(s) for s in row]):
            out.append(tuple(combo))
    return out


# ============================================================
# OLASILIK RAPORU
# ============================================================

class OlasilikRaporu:
    __slots__ = ("mac_olasiliklari", "p_14", "p_15", "p_kume_ici", "p_tek_kolon_15")

    def __init__(self, p_kume_ici: float, p_15: float, p_14: float,
                 p_tek_kolon_15: float, mac_olasiliklari: Sequence[float]):
        self.p_kume_ici = p_kume_ici
        self.p_15 = p_15
        self.p_14 = p_14
        self.p_tek_kolon_15 = p_tek_kolon_15
        self.mac_olasiliklari = list(mac_olasiliklari)


def olasilik_raporu(enc: Encoder, cols: Sequence[Point],
                    probs: Sequence[dict[str, float]]) -> OlasilikRaporu:
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

    mac_p: list[float] = []
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


