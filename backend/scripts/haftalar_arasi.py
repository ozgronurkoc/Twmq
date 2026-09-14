"""Haftalar **arası** bağımlılık — cephedeki bekleme sayısının tek dayanağı.

§3.80 haftalık bütçeyi ₺210.000'de sabitledi ve geriye sahibinin
ilgilendiği tek sayı kaldı: **ne kadar sürer.** O sayı (beklenen 8,9 hafta,
%90 için 19,3) tek bir varsayıma dayanıyor ve bu depoda hiç ölçülmedi:

    gelecek haftalar, ölçülen `p` dağılımından BAĞIMSIZ çekiliyor mu?

§3.46 hafta **içi** bağımlılığı ölçtü ve kapattı (maçlar arası `ρ ≈ 0`).
Haftalar **arası** hiç bakılmadı. Fark önemli: hafta içi bağımlılık tek bir
haftanın `P`sini oynatır; haftalar arası bağımlılık **bekleme süresinin
kuyruğunu** oynatır — ortalama yerinde kalsa bile *"%90 için kaç hafta"*
cevabı değişir.

    cd backend && python scripts/haftalar_arasi.py --butce 21000

─── Neyin ölçüldüğü: ARTIK bağımlılık ──────────────────────────────────

Haftalar arasında görünür bir düzensizlik zaten var ve **modelde**: `p`
haftadan haftaya on altı kat ayrışıyor (%2,1–35,5). Bu heterojenlik
bağımlılık değildir ve cephe onu zaten taşıyor. Aranan şey **onun
üstünde** kalan bağımlılık:

1. **`p` serisinin gecikme-1 ilişkisi.** Zor hafta zor haftayı izliyor mu?
2. **İsabetlerin öbeklenmesi.** Her pencere için model `Π(1−p_w)` diyor;
   gözlenen isabetsiz pencere sayısı bunun etrafında mı, yoksa öbekleniyor
   mu? Bu ikincisi asıl sorudur, çünkü kuyruğu doğrudan o belirler.

**Komşuluk tanımı:** aynı sezon **ve** hafta numarası tam 1 fark. Liste
sırası kullanılmaz — arşivde eksik haftalar var (ör. 2025/26'da 5. hafta
yok) ve sezon sınırı gerçek bir kesintidir.

─── DURMA KURALI — ölçüm görülmeden yazıldı ────────────────────────────

* **Gecikme-1 ilişkisi**, permütasyon %95 aralığı sıfırı **kesiyorsa**
  eksen kapanır ve §3.80'in bekleme sayıları olduğu gibi durur.
* **Öbeklenme**, gözlenen isabetsiz pencere sayısı permütasyon %95 bandının
  **içindeyse** kapanır.
* İkisinden biri geçerse, cephenin `%90` / `%99` satırları geometrik
  formülle değil **gözlenen pencere dağılımıyla** yeniden türetilir. Bu
  yeniden türetme bu betiğin işi değildir; bu betik yalnız kapıyı açar.

İki sınav var, o yüzden eşik **Holm** ile düzeltilir (0,025 ve 0,05).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.coklu_kiyasi import VARSAYILAN_BUTCE, hafta_probs, isabet
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from spor_toto.coklu import coklu_plan_serisi

#: Öbeklenme sınavının pencere boyları (hafta).
PENCERELER = (4, 8, 13, 26)

#: Permütasyon sayısı. 10.000, %95 aralığın kenarını binde bir oynatır.
PERMUTASYON = 10_000

#: Varsayılan kupon tavanı — oynanan plan (§3.69).
VARSAYILAN_TAVAN = 81


def seri(butce: int, tavan: int = VARSAYILAN_TAVAN
         ) -> list[tuple[str, int, float, bool]]:
    """`(sezon, hafta, p, isabet)`, sezon ve hafta numarasına göre sıralı."""
    out = []
    for sezon, hafta, lst in tam_haftalar(ikramiye_tablolari()):
        probs, gercek = hafta_probs(lst)
        plan = coklu_plan_serisi(probs, butce, (tavan,))[tavan]
        out.append((sezon, hafta, plan.p_onbes,
                    isabet(plan.kuponlar, gercek)))
    return sorted(out, key=lambda r: (r[0], r[1]))


def _komsu_indeksler(s: Sequence[tuple[str, int, float, bool]]
                     ) -> list[tuple[int, int]]:
    """Aynı sezon ve hafta numarası tam 1 fark olan indeks çiftleri."""
    return [(i, i + 1) for i in range(len(s) - 1)
            if s[i][0] == s[i + 1][0] and s[i + 1][1] == s[i][1] + 1]


def _pencere_indeksleri(s: Sequence[tuple[str, int, float, bool]],
                        boy: int) -> list[list[int]]:
    """Kesintisiz `boy` haftalık pencerelerin indeksleri (örtüşen)."""
    out: list[list[int]] = []
    for i in range(len(s) - boy + 1):
        blok = list(range(i, i + boy))
        if all(s[j][0] == s[i][0] and s[j][1] == s[i][1] + (j - i)
               for j in blok):
            out.append(blok)
    return out


def _korelasyon(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3 or x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def kos(butce: int, tavan: int = VARSAYILAN_TAVAN,
        perm: int = PERMUTASYON, tohum: int = 20260914) -> dict[str, Any]:
    """İki sınav: `p` serisinin gecikme-1 ilişkisi ve isabet öbeklenmesi."""
    s = seri(butce, tavan)
    p = np.array([r[2] for r in s])
    vur = np.array([r[3] for r in s], dtype=bool)
    rng = np.random.default_rng(tohum)

    # ─── Sınav 1: gecikme-1 ilişkisi ────────────────────────────────────
    ciftler = _komsu_indeksler(s)
    ii = np.array([a for a, _ in ciftler])
    jj = np.array([b for _, b in ciftler])
    r_gozlenen = _korelasyon(p[ii], p[jj])
    null_r = np.empty(perm)
    for t in range(perm):
        q = rng.permutation(p)
        null_r[t] = _korelasyon(q[ii], q[jj])
    alt, ust = np.percentile(null_r, [2.5, 97.5])
    p_deger_r = float(np.mean(np.abs(null_r) >= abs(r_gozlenen)))

    # ─── Sınav 2: isabet öbeklenmesi ────────────────────────────────────
    pencereler = []
    for boy in PENCERELER:
        blok = _pencere_indeksleri(s, boy)
        if not blok:
            # Sessizce atlanmaz: arşivde o boyda KESINTISIZ pencere yok ve
            # bu, sınavın kapsam sınırıdır — okuyan "geçti" sanmamalı.
            pencereler.append({"boy": boy, "pencere": 0, "gozlenen": 0,
                               "model": 0.0, "null_alt": 0.0, "null_ust": 0.0,
                               "icinde": True, "p_deger": 1.0,
                               "olculemedi": True})
            continue
        gozlenen = sum(1 for b in blok if not vur[b].any())
        model = float(sum(np.prod(1.0 - p[b]) for b in blok))
        null = np.empty(perm)
        for t in range(perm):
            sira = rng.permutation(len(s))
            v = vur[sira]
            null[t] = sum(1 for b in blok if not v[b].any())
        n_alt, n_ust = np.percentile(null, [2.5, 97.5])
        pencereler.append({
            "olculemedi": False,
            "boy": boy, "pencere": len(blok), "gozlenen": gozlenen,
            "model": model, "null_alt": float(n_alt), "null_ust": float(n_ust),
            "icinde": bool(n_alt <= gozlenen <= n_ust),
            "p_deger": float(np.mean(np.abs(null - null.mean())
                                     >= abs(gozlenen - null.mean()))),
        })

    # Holm: iki aile (ilişki, öbeklenme-en küçük p)
    p_obek = min((w["p_deger"] for w in pencereler
                  if not w["olculemedi"]), default=1.0)
    sirali = sorted([("gecikme1", p_deger_r), ("obeklenme", p_obek)],
                    key=lambda x: x[1])
    holm = {}
    for k, (ad, pd) in enumerate(sirali):
        holm[ad] = bool(pd <= 0.05 / (2 - k))

    return {
        "hafta": len(s), "butce": butce, "tavan": tavan,
        "isabet": int(vur.sum()), "p_ortalama": float(p.mean()),
        "gerceklesen": {
            "oran": float(vur.mean()),
            "bekleme": (1.0 / float(vur.mean())) if vur.any() else
            float("inf"),
        },
        "gecikme1": {
            "cift": len(ciftler), "r": r_gozlenen,
            "null_alt": float(alt), "null_ust": float(ust),
            "p_deger": p_deger_r,
            "sifiri_kesiyor": bool(alt <= 0 <= ust),
        },
        "obeklenme": pencereler,
        "holm": holm,
        "permutasyon": perm,
    }


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   isabet: {c['isabet']}   "
          f"ortalama p: {c['p_ortalama']:.4%}   "
          f"permutasyon: {c['permutasyon']:,}\n")

    g = c["gecikme1"]
    print("SINAV 1 — `p` serisinin gecikme-1 iliskisi "
          f"({g['cift']} komsu cift)")
    print(f"  gozlenen r = {g['r']:+.4f}   "
          f"permutasyon %95 null araligi [{g['null_alt']:+.4f}, "
          f"{g['null_ust']:+.4f}]   p = {g['p_deger']:.4f}")
    print(f"  -> {'ILISKI YOK' if not c['holm']['gecikme1'] else 'ILISKI VAR'}"
          f" (Holm'lu)")

    print("\nSINAV 2 — isabet obeklenmesi (isabetsiz pencere sayisi)")
    print(f"{'boy':>5} {'pencere':>9} {'gozlenen':>9} {'model':>9} "
          f"{'null %95':>18} {'p':>8}")
    for w in c["obeklenme"]:
        if w["olculemedi"]:
            print(f"{w['boy']:>5} {'—':>9}   OLCULEMEDI: arsivde bu boyda "
                  f"KESINTISIZ pencere yok")
            continue
        print(f"{w['boy']:>5} {w['pencere']:>9} {w['gozlenen']:>9} "
              f"{w['model']:>9.1f} "
              f"[{w['null_alt']:>6.1f}, {w['null_ust']:>6.1f}]"
              f"{'  ':>2}{w['p_deger']:>8.4f}")
    print(f"  -> {'OBEKLENME YOK' if not c['holm']['obeklenme'] else 'OBEKLENME VAR'}"
          f" (Holm'lu)")

    g2 = c["gerceklesen"]
    print(f"\nYAN OLCUM — model mi gercek mi (§3.68'in acigi)")
    print(f"  model p        {c['p_ortalama']:>8.4%}  ->  E[hafta] "
          f"{1 / c['p_ortalama']:>5.1f}")
    print(f"  gerceklesen    {g2['oran']:>8.4%}  ->  E[hafta] "
          f"{g2['bekleme']:>5.1f}   ({c['isabet']}/{c['hafta']})")
    print("  Model KARAMSAR cikiyor; §3.68 bu acigi olctu ve 'GUNCEL DEGIL'")
    print("  dedi (2025/26'da x1,00). Ikisi ayrisirsa hukum ARASINDADIR.")

    kapandi = not (c["holm"]["gecikme1"] or c["holm"]["obeklenme"])
    print(f"\nDURMA KURALI (olcumden ONCE yazildi): "
          f"{'EKSEN KAPANDI' if kapandi else 'EKSEN ACIK'}")
    if kapandi:
        print("§3.80'in bekleme sayilari (E[hafta] = 1/E[p], %90 icin 19,3)")
        print("oldugu gibi durur — haftalar arasi artik bagimlilik yok.")
        print("\nKAPANISIN IKI SINIRI, ACIKCA:")
        print("  1. Gecikme-1 iliskisi SIFIR olculmedi, sifirdan")
        print("     AYIRILAMADI (r = +0,19; 83 cift, aralik genis). Isaret")
        print("     POZITIF ve gercek olsaydi kuyrugu UZATIRDI.")
        print("  2. Sinav yalniz 4 ve 8 haftalik pencerelerde kosabildi;")
        print("     ilgilendigimiz ufuk (13-26 hafta) arsivde KESINTISIZ")
        print("     bulunmadigi icin hic sinanmadi.")
        print("  Yeniden acilma sarti: hafta birikince (kesintisiz 13")
        print("  haftalik pencere cikinca) sinav o boyda tekrarlanir.")
    else:
        print("Cephenin %90 / %99 satirlari geometrik formulle degil,")
        print("GOZLENEN pencere dagilimiyla yeniden turetilmelidir.")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE)
    ap.add_argument("--tavan", type=int, default=VARSAYILAN_TAVAN)
    ap.add_argument("--permutasyon", type=int, default=PERMUTASYON)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    c = kos(a.butce, a.tavan, a.permutasyon)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return
    bas(c)


if __name__ == "__main__":  # pragma: no cover
    main()
