"""Kaplama ARŞİVİ — sökülmüş sistemin, hâlâ gereken tek parçası.

Depo düz (tam sistem) oynuyor; kaplama katmanı `docs/DUZ_SISTEME_GECIS.md`
gerekçesiyle söküldü. Bu modül o sökümün **istisnası** değil, kalıntısıdır ve
üretim yolunda hiçbir yerden çağrılmaz. İki iş için durur:

1. **2026/27'nin ilk dört haftası kaplamayla OYNANDI.** O kuponların en iyi
   kolonu `15 − kaçak` değildir — 16 satırın hangi noktaları örttüğüne
   bağlıdır. `scripts/super_toto_degerlendir.py` donmuş kayıtta
   `sistem: "kaplama"` görürse buradan geçer. Bu modül silinirse depo kendi
   oynadığı haftaları değerlendiremez hâle gelir.

2. **Söküm kararının kanıtı.** `scripts/sistem_kiyasi.py --dogrula` iki
   sistemin kolon başına beklentisini kaba kuvvetle karşılaştırır ve
   `.claude/olcum_kutugu.json`daki iki kaydın (`1,78× – 5,26×` ve
   `duz 7/5/3 ↔ kaplama 4/8/3`) üreteni odur. Kanıtı üretemeyen bir karar
   kaydı, deponun kendi doktrinine göre (ölçüm > kod > belge > graf) yarım
   kayıttır.

Kaplamanın geri kalanı — arama motorları (`exact_cover`, `solve_by_blocks`,
`solve_heuristic`, `greedy_full`, `ls_fixed_size`, `block_optimal`), mesafe
muhasebesi (`ball`, `distance_layers`, `dogrula_kaplama`), satır sıkıştırma
(`merge_rows`) ve bütçe danışmanı — **silindi**. Burada duran şey yalnızca
`solve_fix16`: donmuş bir kuponu yeniden kurmak için gereken en küçük küme.

**Yeni kod bu modülü çağırmaz.** Çağırıyorsa ya donmuş bir geçmiş kaydı
okuyordur ya da bir hata vardır.
"""

from __future__ import annotations

import math
import random
from itertools import product

from .core import Encoder, Point

#: Hamming(7,4) blogunun boyu ve verdigi satir sayisi.
HAMMING_BLOK_BOYU = 7
HAMMING_KOLON = 16


# ============================================================
# HAMMING(7,4) - MUKEMMEL KOD
# ============================================================

def hamming74_codewords() -> list[Point]:
    """
    Sistematik (7,4) Hamming kodunun 16 kod kelimesi.

    16 x 8 = 128 = 2^7 oldugundan MUKEMMEL (perfect) koddur: her nokta tam
    olarak bir topa dusar. 7 cifte icin 16'dan az kolonla 14-garanti
    matematiksel olarak imkansizdir.
    """
    out: list[Point] = []
    for d1, d2, d3, d4 in product((0, 1), repeat=4):
        out.append((d1, d2, d3, d4,
                    d1 ^ d2 ^ d3,
                    d2 ^ d3 ^ d4,
                    d1 ^ d2 ^ d4))
    return out


def hamming74_variant(variant: int = 0) -> list[Point]:
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


def solve_fix16(enc: Encoder, variant: int = 0) -> tuple[list[Point], str]:
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
            f"  - Yedek motorlar (--mode auto/block/heuristic) ARTIK YOK; "
            f"kaplama sokuldu, bkz. modul basligi.")

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

    cols: list[Point] = []
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
