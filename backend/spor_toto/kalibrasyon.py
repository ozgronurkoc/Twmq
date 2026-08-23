"""Kalibrasyon — piyasa sözünü tutuyor mu, ve tutmuyorsa düzeltilebilir mi (A5).

İki iş yapar:

1. **Eğri.** Her sembolü kendi olasılık bandına koyar ve *piyasanın dediği* ile
   *gerçekleşen* oranı Wilson %95 aralığıyla yan yana yazar. `docs
   ISTATISTIK_YOL_HARITASI.md §3.18`'deki tablo bu fonksiyonun çıktısıdır —
   belgedeki sayı elle yazılmaz, buradan üretilir.

2. **Ölçüm.** `IzotonikTahminci`yi piyasaya karşı, **sezon dışarıda bırakmalı**
   koşar ve eşleştirilmiş bootstrap aralığını verir. Geçme ölçütü projenin
   geri kalanıyla aynıdır: aralığın **tamamı** sıfırın altında olmalı.

    python -m spor_toto.kalibrasyon
    python -m spor_toto.kalibrasyon --egri-only

UYARI: izotonik esnek bir düzelticidir. Aynı sezonda uydurulup aynı sezonda
ölçülürse **kesin** yanıltır — bu yüzden burada tek ölçüm yolu sezon dışarıda
bırakmadır ve seçenek olarak bile sunulmaz.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional, Sequence

from .egitim import korpus_haftalari
from .history import SYMBOLS
from .odds import ARINDIRMA_VARSAYILAN, implied_probs
from .predict import PiyasaTahminci
from .recalibrate import EN_AZ_KOVA, IzotonikTahminci

#: Eğrinin bantları. Kenarlar ölçüm sonucuna bakılmadan, okunabilirlik için
#: seçildi: uçlarda seyrek olduğu için geniş, ortada yoğun olduğu için dar.
BANTLAR = ((0.0, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 0.20), (0.20, 0.25),
           (0.25, 0.30), (0.30, 0.35), (0.35, 0.40), (0.40, 0.45), (0.45, 0.50),
           (0.50, 0.55), (0.55, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 1.01))

#: Bir bandın yazılması için gereken en az nokta. Altında yüzde okunmaz.
EN_AZ_BANT = 100


def kalibrasyon_egrisi(yontem: str = ARINDIRMA_VARSAYILAN,
                       yol: Optional[str] = None) -> Dict[str, Any]:
    """Piyasa ↔ gerçek, olasılık bandı bandı.

    Üç sembol havuzlanır: soru "ev sahipleri ne kadar kazanır" değil,
    **"piyasa bir olasılık söylediğinde o olasılık tutuyor mu"**.
    """
    from .benzer import _wilson
    from .egitim import korpus_yukle

    noktalar: List[tuple] = []
    for r in korpus_yukle(yol):
        p = implied_probs(r["oranlar"], yontem)
        if len(p) != 3:
            continue
        for s in SYMBOLS:
            noktalar.append((p[s], r["kod"] == s))

    satirlar: List[Dict[str, Any]] = []
    sapan = 0
    for lo, hi in BANTLAR:
        g = [t for t in noktalar if lo <= t[0] < hi]
        n = len(g)
        if n < EN_AZ_BANT:
            continue
        k = sum(1 for t in g if t[1])
        bekleniyor = sum(t[0] for t in g) / n
        gercek = k / n
        alt, ust = _wilson(k, n)
        icinde = alt <= bekleniyor <= ust
        sapan += 0 if icinde else 1
        satirlar.append({
            "lo": lo, "hi": hi, "n": n,
            "piyasa": bekleniyor, "gercek": gercek,
            "fark": gercek - bekleniyor,
            "ga_alt": alt, "ga_ust": ust,
            "piyasa_ga_icinde": icinde,
        })
    return {
        "arindirma": yontem,
        "n_nokta": len(noktalar),
        "n_mac": len(noktalar) // 3,
        "bantlar": satirlar,
        "sapan_bant": sapan,
        "toplam_bant": len(satirlar),
        # Yönün kendisi bulgunun ta kendisi: negatif uçta abartma, pozitif
        # uçta küçümseme varsa bu favourite–longshot yanlılığıdır.
        "dusuk_uc_fark": next((r["fark"] for r in satirlar if r["hi"] <= 0.25), None),
        "yuksek_uc_fark": next((r["fark"] for r in reversed(satirlar)
                                if r["lo"] >= 0.70), None),
    }


def rapor(sezonlar_: Optional[Sequence[str]] = None,
          yol: Optional[str] = None,
          en_az_kova: int = EN_AZ_KOVA) -> Dict[str, Any]:
    """İzotonik düzeltme piyasayı sezon dışarıda bırakmalı geçiyor mu?"""
    from .evaluate import karsilastir, sezon_anahtari

    haftalar = korpus_haftalari(sezonlar_=sezonlar_, yol=yol)
    fabrikalar = [PiyasaTahminci, (lambda: IzotonikTahminci(en_az_kova))]
    sonuc = karsilastir(fabrikalar, haftalar=haftalar, grup=sezon_anahtari)
    sonuc["egri"] = kalibrasyon_egrisi(yol=yol)
    sonuc["en_az_kova"] = en_az_kova
    sonuc["soru"] = (
        "piyasanin olculmus kalibrasyon sapmasi monoton bir duzeltmeyle "
        "kapatilabiliyor mu — `izotonik` `piyasa`yi sezon disarida birakmali "
        "gecmiyorsa hayir")
    return sonuc


def _yaz_egri(e: Dict[str, Any]) -> None:
    print(f"\nKALİBRASYON EĞRİSİ — {e['n_mac']:,} maç · {e['n_nokta']:,} nokta "
          f"· arındırma: {e['arindirma']}")
    print(f"{'band':<12}{'n':>7}{'piyasa':>9}{'gerçek':>9}{'fark':>8}"
          f"{'%95 aralık':>20}  sapma")
    for r in e["bantlar"]:
        isaret = "" if r["piyasa_ga_icinde"] else "  ← GA DIŞINDA"
        print(f"%{100*r['lo']:>3.0f}–%{100*r['hi']:<6.0f}{r['n']:>7}"
              f"{100*r['piyasa']:>8.1f}%{100*r['gercek']:>8.1f}%"
              f"{100*r['fark']:>+8.1f}"
              f"   [%{100*r['ga_alt']:>5.1f}, %{100*r['ga_ust']:>5.1f}]{isaret}")
    print(f"\nAnlamlı sapan bant: {e['sapan_bant']} / {e['toplam_bant']}")


def _yaz(sonuc: Dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    _yaz_egri(sonuc["egri"])
    print(f"\nÖLÇÜM — sezon dışarıda bırakmalı · {sonuc['n_hafta']} hafta "
          f"· {sonuc['n_mac']:,} maç · kova {sonuc['en_az_kova']}")
    print(f"{'tahminci':<22}{'brier':>9}{'log':>9}{'fark':>10}"
          f"{'%95 aralık':>20}  geçti")
    for t in sonuc["tahminciler"]:
        f = t.get("fark") or {}
        aralik = ("—" if f.get("alt") is None
                  else f"[{f['alt']:+.4f}, {f['ust']:+.4f}]")
        print(f"{t['ad']:<22}{t['brier']:>9.4f}{t['log_kaybi']:>9.4f}"
              f"{(f.get('fark') if f.get('fark') is not None else 0):>+10.4f}"
              f"{aralik:>20}  {'EVET' if t.get('gecti') else 'hayır'}")
    print(f"\nSoru: {sonuc['soru']}")


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--egri-only", action="store_true",
                    help="yalnizca kalibrasyon egrisi (olcum kosulmaz)")
    ap.add_argument("--arindirma", default=ARINDIRMA_VARSAYILAN)
    ap.add_argument("--kova", type=int, default=EN_AZ_KOVA)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.egri_only:
        e = kalibrasyon_egrisi(a.arindirma)
        print(json.dumps(e, ensure_ascii=False, indent=1)) if a.json else _yaz_egri(e)
        return
    s = rapor(en_az_kova=a.kova)
    if a.json:
        print(json.dumps({k: v for k, v in s.items() if not k.startswith("_")},
                         ensure_ascii=False, indent=1, default=str))
    else:
        _yaz(s)


if __name__ == "__main__":
    main()
