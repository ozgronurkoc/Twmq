"""Kalibrasyon — piyasa sözünü tutuyor mu, ve tutmuyorsa düzeltilebilir mi (A5).

İki iş yapar:

1. **Eğri.** Her sembolü kendi olasılık bandına koyar ve *piyasanın dediği* ile
   *gerçekleşen* oranı Wilson %95 aralığıyla yan yana yazar. `docs
   ISTATISTIK_YOL_HARITASI.md §3.18`'deki tablo bu fonksiyonun çıktısıdır —
   belgedeki sayı elle yazılmaz, buradan üretilir.

2. **Ölçüm.** `IzotonikTahminci`yi piyasaya karşı, **sezon dışarıda bırakmalı**
   koşar ve eşleştirilmiş bootstrap aralığını verir. Geçme ölçütü projenin
   geri kalanıyla aynıdır: aralığın **tamamı** sıfırın altında olmalı.

3. **Ayrışım.** Brier'i Murphy'nin dört terimine böler
   (`ortak.brier_ayrisimi`) ve *neden* böyle çıktığını söyler. Eğri
   "piyasa sözünü tutuyor mu" sorusuna bant bant cevap verir; ayrışım aynı
   cevabı **tek sayıya** indirger ve yanına ikinci bir sayı koyar:
   çözünürlük. İkisi ayrı sorudur ve tek bir Brier değeri onları ayırt
   ettirmez.

    python -m spor_toto.kalibrasyon
    python -m spor_toto.kalibrasyon --egri-only
    python -m spor_toto.kalibrasyon --ayrisim

UYARI: izotonik esnek bir düzelticidir. Aynı sezonda uydurulup aynı sezonda
ölçülürse **kesin** yanıltır — bu yüzden burada tek ölçüm yolu sezon dışarıda
bırakmadır ve seçenek olarak bile sunulmaz.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from .egitim import korpus_haftalari
from .history import SYMBOLS
from .odds import ARINDIRMA_VARSAYILAN, implied_probs
from .ortak import OLASILIK_BANTLARI
from .predict import PiyasaTahminci
from .recalibrate import EN_AZ_KOVA, IzotonikTahminci

#: Eğrinin bantları. Kenarlar ölçüm sonucuna bakılmadan, okunabilirlik için
#: seçildi: uçlarda seyrek olduğu için geniş, ortada yoğun olduğu için dar.
#:
#: Tanım artık `ortak`ta. Brier ayrışımı (`ortak.brier_ayrisimi`) aynı
#: kenarlara ihtiyaç duyuyor ve iki ayrı dizi olsaydı eğrinin söylediği ile
#: ayrışımın söylediği sessizce ayrışırdı. Ad burada korunuyor çünkü
#: `tests/test_kalibrasyon.py` onu buradan alıyor.
BANTLAR = OLASILIK_BANTLARI

#: Bir bandın yazılması için gereken en az nokta. Altında yüzde okunmaz.
EN_AZ_BANT = 100


def kalibrasyon_egrisi(yontem: str = ARINDIRMA_VARSAYILAN,
                       yol: str | None = None) -> dict[str, Any]:
    """Piyasa ↔ gerçek, olasılık bandı bandı.

    Üç sembol havuzlanır: soru "ev sahipleri ne kadar kazanır" değil,
    **"piyasa bir olasılık söylediğinde o olasılık tutuyor mu"**.
    """
    from .benzer import _wilson
    from .egitim import korpus_yukle

    noktalar: list[tuple] = []
    for r in korpus_yukle(yol):
        p = implied_probs(r["oranlar"], yontem)
        if len(p) != 3:
            continue
        for s in SYMBOLS:
            noktalar.append((p[s], r["kod"] == s))

    satirlar: list[dict[str, Any]] = []
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


def rapor(sezonlar_: Sequence[str] | None = None,
          yol: str | None = None,
          en_az_kova: int = EN_AZ_KOVA,
          yontem: str = ARINDIRMA_VARSAYILAN) -> dict[str, Any]:
    """İzotonik düzeltme piyasayı sezon dışarıda bırakmalı geçiyor mu?

    `yontem` marj arındırma yöntemidir ve **hem** korpus hazırlığına **hem**
    kalibrasyon eğrisine gider. Önce yalnızca `--egri-only` dalında
    onurlandırılıyordu; ana dal varsayılanla koşup bayrağı sessizce yutuyordu,
    yani `--arindirma guc` ile koşan biri `shin` sonucunu okuyordu.
    """
    from .evaluate import karsilastir, sezon_anahtari

    haftalar = korpus_haftalari(sezonlar_=sezonlar_, yol=yol, yontem=yontem)
    fabrikalar = [PiyasaTahminci, (lambda: IzotonikTahminci(en_az_kova))]
    sonuc = karsilastir(fabrikalar, haftalar=haftalar, grup=sezon_anahtari)
    sonuc["egri"] = kalibrasyon_egrisi(yontem, yol=yol)
    sonuc["en_az_kova"] = en_az_kova
    sonuc["arindirma"] = yontem
    sonuc["soru"] = (
        "piyasanin olculmus kalibrasyon sapmasi monoton bir duzeltmeyle "
        "kapatilabiliyor mu — `izotonik` `piyasa`yi sezon disarida birakmali "
        "gecmiyorsa hayir")
    return sonuc


def _yaz_egri(e: dict[str, Any]) -> None:
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


def _yaz_ayrisim(sonuc: dict[str, Any]) -> None:
    """Sembol başına dört terim + sapma payı.

    `sapma_payi` sütunu süs değil **okuma koşuludur**: `guvenilirlik` sonlu
    örneklemde yukarı yanlıdır ve payla aynı mertebedeyse o sayı çoğunlukla
    gürültüdür (bkz. `ortak.brier_ayrisimi`). Bu yüzden yan yana basılır,
    dipnota atılmaz.
    """
    print(f"\nBRIER AYRIŞIMI — {sonuc['n_mac']:,} maç · {sonuc['n_hafta']} hafta")
    for t_ in sonuc["tahminciler"]:
        a = t_.get("ayrisim")
        k = t_.get("karisiklik")
        if not a:
            continue
        top = a["toplam"]
        print(f"\n  {t_['ad']} — Brier {top['brier']:.4f}"
              f"  (= güvenilirlik − çözünürlük + belirsizlik + bant içi)")
        print(f"  {'sembol':<9}{'brier':>9}{'güvenilir':>11}{'çözünür':>10}"
              f"{'belirsiz':>10}{'bant içi':>10}{'sapma payı':>12}{'taban':>8}")
        for s in SYMBOLS:
            b = a["semboller"][s]
            print(f"  {s:<9}{b['brier']:>9.4f}{b['guvenilirlik']:>11.5f}"
                  f"{b['cozunurluk']:>10.5f}{b['belirsizlik']:>10.5f}"
                  f"{b['bant_ici']:>+10.5f}{b['sapma_payi']:>12.5f}"
                  f"{b['taban_oran']:>8.3f}")
        print(f"  {'TOPLAM':<9}{top['brier']:>9.4f}{top['guvenilirlik']:>11.5f}"
              f"{top['cozunurluk']:>10.5f}{top['belirsizlik']:>10.5f}"
              f"{top['bant_ici']:>+10.5f}{top['sapma_payi']:>12.5f}")
        print(f"  özdeşlik artığı: {top['artik']:+.2e}")
        if k:
            print(f"  isabet {k['isabet']:.3f} · dengeli isabet "
                  f"{k['dengeli_isabet']:.3f} · duyarlılık "
                  + " · ".join(f"{s}={k['duyarlilik'][s]:.3f}" for s in SYMBOLS))


def _yaz(sonuc: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
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
    _yaz_ayrisim(sonuc)
    print(f"\nSoru: {sonuc['soru']}")


def main(argv: Sequence[str] | None = None) -> None:
    from .kosum import belki_kaydet, cli_ekle

    ap = argparse.ArgumentParser()
    ap.add_argument("--egri-only", action="store_true",
                    help="yalnizca kalibrasyon egrisi (olcum kosulmaz)")
    ap.add_argument("--ayrisim", action="store_true",
                    help="yalnizca Brier ayrisimi (egri ve bootstrap basilmaz)")
    ap.add_argument("--arindirma", default=ARINDIRMA_VARSAYILAN)
    ap.add_argument("--kova", type=int, default=EN_AZ_KOVA)
    ap.add_argument("--json", action="store_true")
    cli_ekle(ap)
    a = ap.parse_args(argv)

    if a.egri_only:
        e = kalibrasyon_egrisi(a.arindirma)
        print(json.dumps(e, ensure_ascii=False, indent=1)) if a.json else _yaz_egri(e)
        return
    s = rapor(en_az_kova=a.kova, yontem=a.arindirma)
    belki_kaydet("kalibrasyon", {k: v for k, v in s.items()
                                 if not k.startswith("_")}, a)
    if a.ayrisim and not a.json:
        _yaz_ayrisim(s)
        return
    if a.json:
        print(json.dumps({k: v for k, v in s.items() if not k.startswith("_")},
                         ensure_ascii=False, indent=1, default=str))
    else:
        _yaz(s)


if __name__ == "__main__":
    main()
