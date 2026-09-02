#!/usr/bin/env python3
"""Fiyat kaynakları — hangi bahisçi, hangi dönem, ne kadar kapsıyor.

Bu betik tahmin üretmez ve hiçbir şey iddia etmez; arşivin taşıdığı bütün
fiyatları ölçer ve yan yana koyar. `scripts/acilis_kapanis.py` ile aynı
soruyu sorar (fiyat seçimi sonucu değiştiriyor mu) ama tek bir kitaba
bakmak yerine hepsine bakar.

Niçin gerekli: `odds_2025_26.csv` her bahisçinin her sütununu saklıyordu
ama ölçümlerin tamamı tek bir fiyattan (`odds.FIYAT_VARSAYILAN`) geçiyor
ve öteki fiyatlar **görünmez** duruyordu. Görünmeyen bir alternatif,
olmayan bir alternatiften daha kötüdür: seçimin bedeli ölçülemez.

    python scripts/fiyat_kaynaklari.py
    python scripts/fiyat_kaynaklari.py --json
    python scripts/fiyat_kaynaklari.py --yaz      # data/odds/fiyat_kaynaklari.json
    python scripts/fiyat_kaynaklari.py --kontrol  # yalnizca bayat mi diye bakar (CI)

**`--kontrol` neden var.** `data/odds/fiyat_kaynaklari.json` surumleniyor ve
`odds.py` ile `fiyatlar.py` docstring'lerinden ANILIYOR, ama uretildikten
sonra hicbir sey onu diskteki gercekle karsilastirmiyordu: arsiv buyudugunde
ya da arindirma varsayilani degistiginde dosya sessizce bayatlar ve kimse
gormezdi. `super_toto_frontend.py` ve `api_sozlesme.py` ayni korumayi kendi
uretilmis dosyalari icin zaten tasiyor; bu ucuncusuydu ve eksikti.

UYARI: farklı kapsamalı iki kitabın Brier'i **doğrudan kıyaslanamaz** —
Pinnacle yalnızca sezonun ilk yarısını kapsıyor ve o kesit daha kolay
olabilir. Doğru kıyas AYRIŞMA bölümündedir: orada her çift kendi ortak
kesitinde ölçülür.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.fiyatlar import sezon_fiyat_ozeti
from spor_toto.odds import FIYAT_VARSAYILAN

CIKTI = KOK / "data" / "odds" / "fiyat_kaynaklari.json"


def yazdir(o: dict) -> None:
    print("=" * 78)
    print(f"FİYAT KAYNAKLARI — {o['matches']} maç (2025/26 arşivi) · "
          f"arındırma: {o['arindirma']}")
    print("=" * 78)

    print("\n─── 1. KAPSAMA, MARJ, DÖNEM ─────────────────────────────────────────")
    print(f"{'kaynak':<15}{'n':>5}{'kapsama':>9}{'marj':>8}{'Brier':>9}  dönem")
    for s in o["sources"]:
        yildiz = " ←omurga" if (s["book"] == FIYAT_VARSAYILAN and s["closing"]) else ""
        brier = f"{s['brier']:.4f}" if s["brier"] is not None else "—"
        print(f"{s['key']:<15}{s['n']:>5}{s['coverage_pct']:>8.1f}%"
              f"{s['avg_margin_pct']:>8.2f}{brier:>9}  "
              f"{s['first_day']} → {s['last_day']}{yildiz}")
    print("\nDönem sütunu kapsama kadar önemli: bir kitabın eksiği rastgele değil")
    print("ZAMANA BAĞLI olabilir. Öyleyse %40 kapsama 'rastgele yarısı var'")
    print("demek DEĞİLDİR ve o kitabın Brier'i başka bir maç evrenine aittir.")

    print("\n─── 2. AYRIŞMA — her çift KENDİ ortak kesitinde ──────────────────────")
    print("Brier'ler burada kıyaslanabilir; yukarıdaki tabloda kıyaslanamaz.")
    for donem in ("kapanis", "acilis"):
        satir = [a for a in o["agreement"] if a["period"] == donem]
        if not satir:
            continue
        print(f"\n  [{donem}]")
        for a in satir:
            print(f"    {a['a']:<5}↔ {a['b']:<5} n={a['n']:>4}  "
                  f"ort {a['mean_gap_pct']:>5.2f} puan  en büyük {a['max_gap_pct']:>5.1f}  "
                  f"Brier {a['brier_a']:.4f} / {a['brier_b']:.4f}")

    print("\n─── 3. AÇILIŞ → KAPANIŞ (aynı ailenin iki ucu) ───────────────────────")
    print(f"{'kitap':<7}{'n':>6}{'ort hareket':>13}{'Brier açılış':>14}"
          f"{'Brier kapanış':>15}   sonuç")
    for m in o["movement"]:
        print(f"{m['book']:<7}{m['n']:>6}{m['mean_move_pct']:>12.2f}p"
              f"{m['brier_acilis']:>14.4f}{m['brier_kapanis']:>15.4f}   "
              f"{'kapanış önde' if m['kapanis_daha_iyi'] else 'AÇILIŞ önde'}")

    print("\n─── 4. BAYAT KAPANIŞ — fiyat değil, tazelenmemiş kayıt ───────────────")
    print("Kapanışı açılışıyla BİREBİR aynı olan satırlar. Bunlar ayrışma")
    print("ölçüsünde büyük görünür ve görüş farkı sanılır; değildir.")
    for b in o["stale_closing"]:
        print(f"  {b['book']:<6}{b['identical']:>4} / {b['pairs']:<5} çift  "
              f"(%{b['identical_pct']})")

    print(f"\n{o['note']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--yaz", action="store_true",
                    help=f"{CIKTI.relative_to(KOK)} dosyasına yaz")
    ap.add_argument("--kontrol", action="store_true",
                    help="dosya güncel mi — yazmaz, farklıysa 1 ile çıkar")
    a = ap.parse_args()
    o = sezon_fiyat_ozeti()
    govde = json.dumps(o, ensure_ascii=False, indent=1) + "\n"

    if a.kontrol:
        # Yazmaz. Kapının işi dosyayı tazelemek değil, BAYATLADIĞINI
        # söylemektir: sessizce yeniden yazsaydı, ölçümün değiştiğini
        # kimse görmeden commit'e girerdi.
        if not CIKTI.is_file():
            print(f"✗ {CIKTI.relative_to(KOK)} yok — "
                  "'python scripts/fiyat_kaynaklari.py --yaz' çalıştırın")
            raise SystemExit(1)
        if CIKTI.read_text(encoding="utf-8") != govde:
            print(f"✗ {CIKTI.relative_to(KOK)} BAYAT — "
                  "'python scripts/fiyat_kaynaklari.py --yaz' çalıştırın")
            raise SystemExit(1)
        print(f"{CIKTI.name} guncel")
        return

    if a.json:
        print(govde)
    else:
        yazdir(o)
    if a.yaz:
        CIKTI.parent.mkdir(parents=True, exist_ok=True)
        CIKTI.write_text(govde, encoding="utf-8")
        print(f"\nyazıldı: {CIKTI}")


if __name__ == "__main__":
    main()
