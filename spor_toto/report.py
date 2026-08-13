"""Cikti bicimlendirme: konsol raporu ve dosyaya kayit."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .core import (Encoder, OlasilikRaporu, Point, Row, distance_layers,
                   dogrula_kaplama, merge_rows, olasilik_raporu, row_cost,
                   rows_to_points)

CIZGI = "=" * 68
INCE = "-" * 68


def satir_metni(enc: Encoder, row: Row, genislik: int = 3) -> str:
    return " ".join(f"{p:>{genislik}s}" for p in enc.decode_row(row))


def kolon_metni(enc: Encoder, col: Point) -> str:
    return " ".join(enc.decode_full(col))


def basliklar(enc: Encoder) -> List[str]:
    return [
        f"Banko mac       : {len(enc.banko_pos)}  {[p + 1 for p in enc.banko_pos]}",
        f"Cifte mac       : {sum(1 for k in enc.alphabet_sizes if k == 2)}",
        f"Uclu mac        : {sum(1 for k in enc.alphabet_sizes if k == 3)}",
        f"Degisken uzay   : {enc.space_size()} nokta "
        f"(tam sistem = {enc.space_size()} kolon)",
        f"Top boyutu      : {enc.ball_size()}",
        f"Alt sinir       : {enc.lower_bound()} kolon (kure-kaplama)",
    ]


def dagilim_satirlari(enc: Encoder, cols: Sequence[Point]) -> List[str]:
    dist = distance_layers(cols, enc.alphabet_sizes)
    total = enc.space_size()
    out = ["Kapsama dagilimi (degisken maclar uzerinden):"]
    for d in sorted(dist):
        etiket = f"{15 - d} dogru"
        out.append(f"  d={d} ({etiket:9s}) : {dist[d]:8d}  "
                   f"(%{100 * dist[d] / total:6.2f})")
    worst = max(dist) if dist else 99
    if worst <= 1:
        out.append("  -> EN KOTU DURUM 1 HATA: 14-GARANTI DOGRULANDI")
    else:
        out.append(f"  -> UYARI: en kotu durum {worst} hata. 14-GARANTI YOK.")
    return out


def olasilik_satirlari(rap: OlasilikRaporu) -> List[str]:
    return [
        "Olasilik raporu (senin tahminlerine gore):",
        f"  Tum sonuclar secim kumende : %{100 * rap.p_kume_ici:6.2f}"
        f"   <- 14-garanti ancak burada devreye girer",
        f"  15 tutturma                : %{100 * rap.p_15:6.2f}",
        f"  Tam 14 tutturma            : %{100 * rap.p_14:6.2f}",
        f"  En olasi TEK kolon icin 15 : %{100 * rap.p_tek_kolon_15:6.2f}",
        "  NOT: sistem 15 sansini degil KAPSAMAYI maksimize eder; en olasi tek",
        "       nokta kolonlar arasinda olmayabilir. Sistemin degeri 14-garantidir.",
        "  NOT: bu bir kar/beklenen-deger hesabi degildir; ikramiye havuzu",
        "       ve kolon bedeli hesaba katilmaz.",
    ]


def monte_carlo_satirlari(mc: dict) -> List[str]:
    lines = [
        f"Monte Carlo ({mc['n_samples']} deneme, %95 CI):",
        f"  Kume ici : %{mc['kume_ici']['pct']:6.3f}  ±{mc['kume_ici']['ci95']}",
        f"  P(15)    : %{mc['p15']['pct']:6.3f}  ±{mc['p15']['ci95']}",
        f"  P(14)    : %{mc['p14']['pct']:6.3f}  ±{mc['p14']['ci95']}",
        f"  P(13)    : %{mc['p13']['pct']:6.3f}  ±{mc['p13']['ci95']}",
        f"  P(12)    : %{mc['p12']['pct']:6.3f}  ±{mc['p12']['ci95']}",
    ]
    return lines


def yazdir_ve_kaydet(enc: Encoder, cols: List[Point], baslik: str,
                     output_path: Optional[str] = None,
                     ek_notlar: Sequence[str] = (),
                     probs: Optional[Sequence[Dict[str, float]]] = None,
                     tam_liste: bool = True,
                     mc_samples: int = 0,
                     mc_seed: int = 42) -> Dict[str, object]:
    """Sonucu ekrana basar, istenirse dosyaya yazar. Ozet sozluk dondurur."""
    rows = merge_rows(cols)
    toplam_bedel = sum(row_cost(r) for r in rows)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)

    if set(rows_to_points(rows)) != set(cols):
        raise AssertionError(
            "Satir sikistirma kolon kumesini degistirdi - bu bir hatadir.")
    if toplam_bedel != len(cols):
        raise AssertionError(
            f"Satir bedeli {toplam_bedel}, kolon sayisi {len(cols)} - uyusmuyor.")

    print("\n" + CIZGI)
    print("SONUC")
    print(CIZGI)
    print(f"Yontem                : {baslik}")
    print(f"Kupon satiri          : {len(rows)}")
    print(f"Kolon bedeli          : {len(cols)}")
    print(f"Kure-kaplama alt sinir: {enc.lower_bound()}")
    for note in ek_notlar:
        print(f"                        {note}")
    print(INCE)
    for line in dagilim_satirlari(enc, cols):
        print(line)

    rap = None
    mc = None
    if probs:
        rap = olasilik_raporu(enc, cols, probs)
        print(INCE)
        for line in olasilik_satirlari(rap):
            print(line)
        if mc_samples and mc_samples > 0:
            from .analysis import monte_carlo_report
            mc = monte_carlo_report(
                enc, cols, probs, n_samples=mc_samples, seed=mc_seed)
            print(INCE)
            for line in monte_carlo_satirlari(mc):
                print(line)
    print(INCE)

    print(f"\nKUPONA YAZILACAK: {len(rows)} satir "
          f"(bedel {len(cols)} kolon)\n")
    for i, r in enumerate(rows, 1):
        c = row_cost(r)
        print(f"{i:4d} | {satir_metni(enc, r)}" + (f"   [{c} kolon]" if c > 1 else ""))

    if tam_liste:
        print(f"\nAcik hali ({len(cols)} kolon):\n")
        for i, col in enumerate(cols, 1):
            print(f"{i:4d} | {kolon_metni(enc, col)}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"{baslik}\n")
            f.write(f"Kupon satiri : {len(rows)}\n")
            f.write(f"Kolon bedeli : {len(cols)}\n")
            for note in ek_notlar:
                f.write(f"{note}\n")
            f.write(f"En kotu durum: {worst} hata "
                    f"({'14-garanti VAR' if worst <= 1 else '14-garanti YOK'})\n")
            if rap:
                f.write("\n")
                for line in olasilik_satirlari(rap):
                    f.write(line + "\n")
            if mc:
                f.write("\n")
                for line in monte_carlo_satirlari(mc):
                    f.write(line + "\n")
            f.write(f"\n--- KUPONA YAZILACAK ({len(rows)} satir) ---\n")
            for i, r in enumerate(rows, 1):
                c = row_cost(r)
                f.write(f"{i:4d} | {satir_metni(enc, r)}"
                        + (f"   [{c} kolon]\n" if c > 1 else "\n"))
            f.write(f"\n--- ACIK HALI ({len(cols)} kolon) ---\n")
            for i, col in enumerate(cols, 1):
                f.write(f"{i:4d} | {kolon_metni(enc, col)}\n")
        print(f"\n-> '{output_path}' dosyasina kaydedildi.")

    return {"satir": len(rows), "bedel": len(cols), "en_kotu": worst,
            "acik": acik, "olasilik": rap, "monte_carlo": mc}
