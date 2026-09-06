#!/usr/bin/env python3
"""Kaplama mı düz mü — aynı kolon bütçesinde iki sistemin en iyisi.

**Bu betik bir kararın kanıtıdır ve kaplama sökülmeden önce yazıldı.**
Depo düz (tam sistem) oynamaya geçiyor; geçişin gerekçesi burada ölçülür.
Kaplama katmanı depodan çıktıktan sonra bu kıyas bir daha koşulamaz, o yüzden
çıktısı `docs/DUZ_SISTEME_GECIS.md`e yazılıdır.

─── Ölçülen iki ayrı şey ─────────────────────────────────────────────────

``--dogrula``
    *Aynı* işaretler iki sistemde kolon başına aynı beklentiyi verir mi?
    Deponun bilinen bulgusu (`docs/ISTATISTIK_YOL_HARITASI.md` §3.40) bunu
    ₺46,88 ↔ ₺46,16 diye ölçmüştü. Betik onu bağımsız olarak yeniden üretir;
    tutmazsa aşağıdaki kıyas da güvenilmezdir.

kıyas (varsayılan)
    *Farklı* soru: aynı KOLON bütçesinde her sistemin **erişebildiği en iyi
    şekil** hangisi ve hangisi daha çok kazandırır? Kaplama `solve_fix16`
    yüzünden en az yedi çifte ister ve bu onu yayvan şekillere hapseder
    (8/7/0, 4/8/3); düz yoğunlaşabilir (11/4/0, 10/0/5). Fark buradan çıkar.

─── Sayıların sınırı — okunmadan kullanılmasın ───────────────────────────

Mutlak E[TL] değerleri **tek bir haftanın ikramiye tablosuna** dayanır ve o
tablo hafta hafta on kat oynar (2026/27 1. haftada 14 kademesi ₺2.153.527,
2. haftada ₺202.328). Bu yüzden manşet **oran**dır, mutlak sayı değil; oran
iki hafta ve yedi bütçe kademesinde tutarlı çıkıyor.

Ayrıca beklenen değer bir kâr göstergesi **değildir**: `docs/KADEME_OLASILIKLARI.md`
114 hafta üzerinde haftalık geri dönüş medyanını **%0** ve büyük bütçede
zarar olasılığını **%99–100** ölçtü. Bu betik "düz kaplamadan iyi" der,
"düz kârlıdır" demez.

    python scripts/sistem_kiyasi.py --dogrula
    python scripts/sistem_kiyasi.py --hafta 3 --odul-hafta 1
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from scripts.butce_kademeleri import hafta_olasiliklari
from spor_toto.core import (
    HAMMING_BLOK_BOYU,
    HAMMING_KOLON,
    Encoder,
    sirala_semboller,
    solve_fix16,
)
from spor_toto.ortak import kacak_dagilimi

#: Kıyasın koştuğu kolon bütçeleri. Değerler hem `2^a·3^b` (düz bedel) hem de
#: kaplamanın `2^a·3^b/8`i olarak anlamlı noktalara denk gelsin diye seçildi.
TAVANLAR: tuple[int, ...] = (16, 64, 256, 864, 3888, 10368, 59049)

#: Ödül kademeleri — `12` altı ödemiyor.
KADEMELER: tuple[int, ...] = (12, 13, 14, 15)


def odul_tablosu(sezon: str, hafta: int) -> dict[int, float]:
    """Resmî arşivden bir haftanın kademe başına **kişi başı** ödülü."""
    import json

    yol = KOK / "data" / "sportoto_arsiv" / f"{sezon}.json"
    ars = json.loads(yol.read_text(encoding="utf-8"))
    for w in ars["weeks"]:
        if w["week"] != hafta:
            continue
        p = w.get("payout")
        if not p:
            raise SystemExit(f"{sezon} {hafta}. hafta: ikramiye tablosu yok")
        return {int(t["correct"]): float(t["prize"]) for t in p["tiers"]}
    raise SystemExit(f"{sezon} {hafta}. hafta arşivde yok")


def _sirali(probs: list[dict[str, float]], i: int) -> list[float]:
    return sorted(probs[i].values(), reverse=True)


def E_tam(probs: list[dict[str, float]], seviyeler: list[int],
          odul: dict[int, float]) -> float:
    """Tam sistemde BÜTÜN kolonların toplam beklentisi — üreteç fonksiyonu.

    Her kolonun beklentisi yalnız kendi olasılık profiline bağlıdır, yani
    toplam beklenti kolonlar üzerinde toplanabilir (§3.40'ın doğrusallığı).
    `t` doğru yapan kolon sayısının beklentisi::

        [x^t]  Π_i ( Σ_{s ∈ S_i} (p_s·x + (1 − p_s)) )

    Kaba kuvvet sayımla (864 kolonu tek tek gezerek) birebir aynı sonucu
    verir; burada çarpım biçimi kullanılıyor çünkü şekil taraması yüzlerce
    kez çağırıyor.
    """
    poli = [1.0]
    for i, lv in enumerate(seviyeler):
        a = sum(_sirali(probs, i)[:lv])
        yeni = [0.0] * (len(poli) + 1)
        for j, v in enumerate(poli):
            yeni[j] += v * (lv - a)
            yeni[j + 1] += v * a
        poli = yeni
    return sum(poli[t] * odul.get(t, 0.0) for t in KADEMELER)


def P_en_az_12(probs: list[dict[str, float]], seviyeler: list[int],
               sistem: str) -> float:
    """`P(en iyi kolon ≥ 12)`.

    Düzde en iyi kolon **tam olarak** `15−k`, kaplamada **en az** `14−k`.
    Yani eşik düzde 3, kaplamada 2 — aynı para hedefinin (≥12) iki sistemdeki
    karşılığı. Kaplama tarafı bu yüzden temkinli: gerçekleşen daha iyi olabilir.
    """
    q = [max(0.0, 1.0 - sum(_sirali(probs, i)[:seviyeler[i]]))
         for i in range(len(seviyeler))]
    esik = 3 if sistem == "duz" else 2
    return sum(kacak_dagilimi(q)[:esik + 1])


def atama(probs: list[dict[str, float]], cift: int, uclu: int) -> list[int]:
    """`(çifte, üçlü)` sayıları verilince hangi maça ne düşer.

    Üçlü en yüksek `p₃`'lülere, tek en düşük `p₂`'lilere gider. Bu sıralama
    kesin değil ama ölçüldü: `en_iyi_secim`in kendi cevabıyla 2026/27'nin
    dört haftasının dördünde birebir, 400 rastgele haftanın %81–83'ünde
    örtüşüyor. Şekil taramasının amacı sistemler arası KIYAS olduğu için
    aynı sıralama iki tarafa da uygulanır; yanlılık varsa ikisinde de aynıdır.
    """
    n = len(probs)
    p2 = sorted(range(n), key=lambda i: _sirali(probs, i)[1])
    p3 = sorted(range(n), key=lambda i: -_sirali(probs, i)[2])
    uc = set(p3[:uclu])
    kalan = [i for i in p2 if i not in uc]
    tek = set(kalan[:n - uclu - cift])
    return [3 if i in uc else (1 if i in tek else 2) for i in range(n)]


def en_iyi_sekil(probs: list[dict[str, float]], tavan: int, sistem: str,
                 odul: dict[int, float]) -> dict[str, Any] | None:
    """`tavan` kolona sığan, o sistemin ERİŞEBİLDİĞİ en iyi şekil.

    Kaplamanın iki kısıtı burada devreye girer ve farkın tamamı odur:
    en az `HAMMING_BLOK_BOYU` çifte, ve bedel `2^a·3^b/2⁷·16`.
    """
    n = len(probs)
    en = None
    for uclu in range(n + 1):
        for cift in range(n - uclu + 1):
            uzay = (2 ** cift) * (3 ** uclu)
            if sistem == "duz":
                kolon = uzay
            else:
                if cift < HAMMING_BLOK_BOYU:
                    continue
                kolon = uzay // (2 ** HAMMING_BLOK_BOYU) * HAMMING_KOLON
            if kolon <= 0 or kolon > tavan:
                continue
            sev = atama(probs, cift, uclu)
            # Kaplamanin toplam beklentisi duzun 1/8'idir (asagida dogrulaniyor).
            # Bolme kaplama LEHINE temkinli: olcumde fix16 kolon basina %0,2
            # DAHA DUSUK cikti, yani gercek fark buradakinden biraz buyuk.
            tl = E_tam(probs, sev, odul)
            if sistem != "duz":
                tl /= 2 ** HAMMING_BLOK_BOYU / HAMMING_KOLON
            if en is None or tl > en["tl"]:
                en = {"tl": tl, "kolon": kolon, "sev": sev,
                      "sekil": (n - cift - uclu, cift, uclu),
                      "p12": P_en_az_12(probs, sev, sistem)}
    return en


def dogrula(probs: list[dict[str, float]], picks: list[str],
            odul: dict[int, float]) -> dict[str, float]:
    """AYNI işaretler iki sistemde: kolon başına beklenti eşit mi?

    Kaplama tarafı burada **kaba kuvvetle** sayılır (`solve_fix16`in ürettiği
    kolonlar tek tek gezilir), yani `en_iyi_sekil`in kullandığı 1/8 kısayolu
    bağımsız olarak sınanmış olur.
    """
    enc = Encoder([sirala_semboller(list(p)) for p in picks], kati=False)
    pts, _ = solve_fix16(enc)
    kf = [enc.decode_full(pt) for pt in pts]
    kd = list(itertools.product(*picks))

    def topla(kolonlar: list[Any]) -> float:
        toplam = 0.0
        for kol in kolonlar:
            dag = [1.0]
            for i in range(len(kol)):
                p = probs[i][kol[i]]
                yeni = [0.0] * (len(dag) + 1)
                for j, v in enumerate(dag):
                    yeni[j] += v * (1 - p)
                    yeni[j + 1] += v * p
                dag = yeni
            toplam += sum(dag[t] * odul.get(t, 0.0) for t in KADEMELER)
        return toplam

    tf, td = topla(kf), topla(kd)
    return {"fix16_kolon": len(kf), "fix16_tl": tf, "fix16_birim": tf / len(kf),
            "duz_kolon": len(kd), "duz_tl": td, "duz_birim": td / len(kd)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--hafta", type=int, default=None,
                    help="tek hafta; verilmezse ödül tablosu olan hepsi")
    ap.add_argument("--odul-hafta", type=int, default=1,
                    help="hangi haftanın ikramiye tablosu kullanılsın")
    ap.add_argument("--dogrula", action="store_true",
                    help="yalnızca §3.40 doğrusallığını yeniden üret")
    a = ap.parse_args()

    odul = odul_tablosu(a.sezon, a.odul_hafta)
    haftalar = [a.hafta] if a.hafta else [3, 4]

    print(f"\nödül tablosu: {a.sezon} {a.odul_hafta}. hafta · "
          + " · ".join(f"{k}={odul[k]:,.0f}TL" for k in sorted(odul, reverse=True)))
    print("UYARI: mutlak TL bu tabloya bağlıdır ve hafta hafta on kat oynar; "
          "manşet ORANDIR.")

    if a.dogrula:
        probs = hafta_olasiliklari(haftalar[0], a.sezon)
        picks = ["10", "10", "1", "102", "102", "10", "02", "12", "1", "1",
                 "02", "12", "12", "102", "2"]
        d = dogrula(probs, picks, odul)
        print(f"\n─── AYNI işaretler, iki sistem ({haftalar[0]}. hafta, 4/8/3) ───")
        print(f'  fix16       {d["fix16_kolon"]:>6,} kolon · '
              f'{d["fix16_tl"]:>14,.0f} TL · kolon başına {d["fix16_birim"]:>8,.1f} TL')
        print(f'  tam sistem  {d["duz_kolon"]:>6,} kolon · '
              f'{d["duz_tl"]:>14,.0f} TL · kolon başına {d["duz_birim"]:>8,.1f} TL')
        sapma = abs(d["fix16_birim"] - d["duz_birim"]) / d["duz_birim"]
        print(f"  sapma %{100*sapma:.2f} — §3.40'ın doğrusallığı "
              f"{'TUTUYOR' if sapma < 0.01 else 'TUTMUYOR'}")
        return

    for h in haftalar:
        probs = hafta_olasiliklari(h, a.sezon)
        print(f"\n{'='*100}\n{h}. HAFTA — aynı kolon bütçesinde her sistemin "
              f"erişebildiği en iyi şekil\n{'='*100}")
        print(f'{"tavan":>8} | {"DÜZ":^32} | {"KAPLAMA":^32} | oran')
        print(f'{"":>8} | {"şekil":>8}{"kolon":>8}{"E[TL]":>12}{"P≥12":>6} | '
              f'{"şekil":>8}{"kolon":>8}{"E[TL]":>12}{"P≥12":>6} |')
        for t in TAVANLAR:
            dz = en_iyi_sekil(probs, t, "duz", odul)
            fx = en_iyi_sekil(probs, t, "fix16", odul)
            if dz is None or fx is None:
                print(f"{t:>8,} | biri kurulamıyor")
                continue
            print(f'{t:>8,} | {"/".join(map(str, dz["sekil"])):>8}{dz["kolon"]:>8,}'
                  f'{dz["tl"]:>12,.0f}{dz["p12"]:>6.3f} | '
                  f'{"/".join(map(str, fx["sekil"])):>8}{fx["kolon"]:>8,}'
                  f'{fx["tl"]:>12,.0f}{fx["p12"]:>6.3f} | {dz["tl"]/fx["tl"]:>4.2f}×')


if __name__ == "__main__":
    main()
