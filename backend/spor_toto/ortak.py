"""Birden fazla modülün paylaştığı küçük hesaplar — **tek kaynak**.

Bu modül var olmadan önce aynı formüller pakette dağınık duruyordu ve
ayrışmaya açıktı:

* olasılık normalizasyonu `bayes` ve `markov`'da **birebir aynı** iki
  private fonksiyondu (`_normalize` / `_norm`);
* Wilson aralığı `backtest`'te tanımlı, `benzer`'de yalnızca ileten bir
  kabuk, `kalibrasyon` ve `scripts/super_toto_sezon` ise o kabuğun içinden
  **private** bir sembolü iki sıçramayla import ediyordu;
* Brier `evaluate` ve `odds`'ta iki kez yazılmıştı (tek fark: biri sözlüğü
  doğrudan, öteki `blok["probs"]` üzerinden okuyordu);
* "bu değer hangi banda düşer" üç modülde aynı adla üç ayrı gövdeydi;
* favori dilimi `bahisci` ve `disari`'da aynıydı — `disari` bunu bir
  yorumda itiraf ediyordu ama kopya yine de duruyordu.

Buradaki her şey **saf**tır: dosya okumaz, önbellek tutmaz, paket içinden
yalnızca `core`'u (sembol düzeni için) çeker. Böylece hiçbir modül bu
modül yüzünden döngüye girmez.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Sequence, Tuple

from .core import SEMBOLLER

__all__ = [
    "SEMBOLLER",
    "normalize_olasilik",
    "wilson",
    "GUVEN_Z",
    "brier",
    "BRIER_ESIT",
    "bant_adi",
    "FAVORI_DILIMLERI",
    "favori_dilimi",
]


# ─── olasılık ────────────────────────────────────────────────────────────

def normalize_olasilik(p: Dict[str, float]) -> Dict[str, float]:
    """1'e normalize edilmiş olasılık; negatif kırpılır, toplam 0 ise düzgün.

    Toplam sıfırken 1/3'e düşmek keyfi değil: "bilgi yok" durumunun tek
    tarafsız karşılığı düzgün dağılımdır. Arayüz de aynı kuralı uygular
    (`frontend/lib/utils.ts` `normalize`), yani yığının iki ucu aynı şeyi
    söyler.
    """
    toplam = sum(max(0.0, float(p.get(s, 0.0))) for s in SEMBOLLER)
    if toplam <= 0:
        return {s: 1.0 / 3.0 for s in SEMBOLLER}
    return {s: max(0.0, float(p.get(s, 0.0))) / toplam for s in SEMBOLLER}


# ─── güven aralığı ───────────────────────────────────────────────────────

#: %95 iki yanlı normal kuantili.
GUVEN_Z = 1.959964


def wilson(basari: int, n: int) -> Tuple[float, float]:
    """Oran için Wilson %95 güven aralığı.

    Normal yaklaşım küçük örneklemde kenarlara yapışır — 40/41'de üst sınır
    1'i aşar, 0/30'da alt sınır eksiye iner. Wilson bu yüzden tercih edilir
    ve aralık her zaman [0, 1] içinde kalır.
    """
    if n <= 0:
        return 0.0, 0.0
    p = basari / n
    payda = 1 + GUVEN_Z * GUVEN_Z / n
    merkez = (p + GUVEN_Z * GUVEN_Z / (2 * n)) / payda
    yari = GUVEN_Z * math.sqrt(
        p * (1 - p) / n + GUVEN_Z * GUVEN_Z / (4 * n * n)) / payda
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


# ─── puanlama ────────────────────────────────────────────────────────────

def brier(probs: Dict[str, float], kod: str) -> float:
    """Tek maçın Brier skoru: Σ(p_s − 1{s=gerçek})².

    0 = kusursuz, 2 = tam ters. Olasılığın tamamını cezalandırır: 0,90
    verip tutturmakla 0,40 verip tutturmak aynı sayılmaz.
    """
    return sum((probs.get(s, 0.0) - (1.0 if s == kod else 0.0)) ** 2
               for s in SEMBOLLER)


#: Üç sembole eşit olasılık verildiğinde çıkan Brier — referans çizgi.
#: Bir tahminci bunun altına inemiyorsa hiç bilgi taşımıyor demektir.
BRIER_ESIT = round(2 * (1 / 3.0) ** 2 + (1 - 1 / 3.0) ** 2, 4)


# ─── bantlama ────────────────────────────────────────────────────────────

def bant_adi(deger: float, bantlar: Sequence[float]) -> str:
    """Bir değeri artan eşik dizisine göre okunabilir bant adına çevirir.

    `bantlar = (0.40, 0.50, 0.65)` için: 0,31 → `<0.40`, 0,52 → `<0.65`,
    0,80 → `>=0.65`. Eşikler dahil değildir (üst sınır açık).
    """
    for esik in bantlar:
        if deger < esik:
            return f"<{esik:.2f}"
    return f">={bantlar[-1]:.2f}" if bantlar else "—"


#: Favori olasılığı dilimleri — karışmayı açmak için. Eşikler ölçüm
#: sonucuna BAKILMADAN, kaba biçimde seçildi; sonradan ayarlanırsa dilim
#: tanımı ölçümün kendisine bağlanmış olurdu.
FAVORI_DILIMLERI: Sequence[float] = (0.40, 0.50, 0.65)


def favori_dilimi(probs: Optional[Dict[str, float]]) -> str:
    """Bir maçın favori olasılığının hangi dilime düştüğü."""
    en_yuksek = max(probs.values()) if probs else 0.0
    return bant_adi(en_yuksek, FAVORI_DILIMLERI)
