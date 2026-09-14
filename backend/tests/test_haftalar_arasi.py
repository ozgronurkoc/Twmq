"""`haftalar_arasi.py` — komşuluk tanımının ve kapsam sınırının bekçileri.

Bu sınavın hükmü (*"haftalar arası artık bağımlılık yok"*) iki şeye
dayanıyor ve ikisi de sessizce bozulabilir:

1. **Komşuluk tanımı.** Liste sırası kullanılırsa arşivdeki boşluklar
   (eksik hafta) ve sezon sınırları komşu sayılır; sınav o zaman var
   olmayan bir bitişikliği ölçer.
2. **Ölçülemeyen pencere sessizce düşmemeli.** 13 ve 26 haftalık pencere
   arşivde kesintisiz bulunmuyor; satır tablodan düşerse okuyan "geçti"
   sanır. Kapsam sınırı çıktının kendisinde durmalı.
"""
from __future__ import annotations

from scripts.haftalar_arasi import (
    PENCERELER,
    _komsu_indeksler,
    _pencere_indeksleri,
    kos,
)


def _s(*satir):
    """(sezon, hafta) çiftlerinden seri kurar; `p` ve isabet önemsiz."""
    return [(sz, hf, 0.1, False) for sz, hf in satir]


def test_komsuluk_SEZON_sinirini_gecmez():
    s = _s(("2022_23", 42), ("2022_23", 43), ("2023_24", 1), ("2023_24", 2))
    assert _komsu_indeksler(s) == [(0, 1), (2, 3)]


def test_komsuluk_EKSIK_haftayi_komsu_saymaz():
    """2025/26'da 5. hafta yok — 4 ile 6 komşu değildir."""
    s = _s(("2025_26", 4), ("2025_26", 6), ("2025_26", 7))
    assert _komsu_indeksler(s) == [(1, 2)]


def test_pencere_KESINTISIZ_olmak_zorunda():
    s = _s(("2025_26", 2), ("2025_26", 3), ("2025_26", 4),
           ("2025_26", 6), ("2025_26", 7), ("2025_26", 8))
    assert _pencere_indeksleri(s, 3) == [[0, 1, 2], [3, 4, 5]]
    assert _pencere_indeksleri(s, 4) == []


def test_pencere_sezon_sinirini_gecmez():
    s = _s(("2022_23", 42), ("2022_23", 43), ("2023_24", 1), ("2023_24", 2))
    assert _pencere_indeksleri(s, 3) == []
    assert _pencere_indeksleri(s, 2) == [[0, 1], [2, 3]]


def test_OLCULEMEYEN_pencere_tablodan_DUSMEZ():
    """Kapsam sınırı görünür kalmalı — 'geçti' ile 'ölçülemedi' ayrı şey."""
    c = kos(2_000, tavan=27, perm=50)
    boylar = [w["boy"] for w in c["obeklenme"]]
    assert boylar == list(PENCERELER), (
        "olculemeyen pencere satiri dusmus; okuyan gectigini sanir")
    for w in c["obeklenme"]:
        if w["pencere"] == 0:
            assert w["olculemedi"] is True


def test_holm_olculemeyen_pencereyi_hesaba_KATMAZ():
    """Ölçülemeyen satırın `p = 1,0`'ı en küçük p'yi kirletmemeli."""
    c = kos(2_000, tavan=27, perm=50)
    olculen = [w["p_deger"] for w in c["obeklenme"] if not w["olculemedi"]]
    assert olculen, "hicbir pencere olculememis — sinav bos kosmus"
    assert min(olculen) <= 1.0
    assert set(c["holm"]) == {"gecikme1", "obeklenme"}
