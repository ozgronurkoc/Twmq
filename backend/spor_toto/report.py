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
        etiket = f"{enc.total_len - d} dogru"
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
    if mc.get("warning"):
        lines.append(f"  UYARI    : {mc['warning']}")
    return lines


def fire_satirlari(fire: dict) -> List[str]:
    """
    Secim DISI fire raporu.

    Diger tum bloklar kume ICI mesafeyi anlatir; bu blok 14-garantinin
    GECERLI OLMADIGI bolgeyi anlatir. Karistirilmamasi icin basligi acik.
    """
    lines = ["Secim DISI fire analizi (14-garantinin disi):"]
    for anahtar, etiket in (("fire1", "1 mac isaret disinda"),
                            ("fire2", "2 mac isaret disinda")):
        blok = fire.get(anahtar)
        if not blok or not blok.get("n"):
            continue
        lines.append(f"  {etiket} ({blok['n']} senaryo):")
        for skor in ("15", "14", "13", "12"):
            if skor in blok["scores"]:
                lines.append(
                    f"    {skor} dogru : {blok['scores'][skor]:9d}  "
                    f"(%{blok['pct'][skor]:6.2f})")
        lines.append(f"    >=14      : %{blok['p_ge_14']:6.2f}   "
                     f">=13: %{blok['p_ge_13']:6.2f}")
        turler = blok.get("by_type") or {}
        if turler:
            parcalar = []
            for tur, v in turler.items():
                p14 = v["pct"].get("14", 0.0)
                p13 = v["pct"].get("13", 0.0)
                parcalar.append(f"{tur} 14:%{p14:.1f}/13:%{p13:.1f}")
            lines.append("    tur bazinda: " + "  ".join(parcalar))
    lines.append("  NOT: bu bolum kume DISI senaryolardir; uniform 1/2 hata")
    lines.append("       katmanlari kume ICI mesafedir, ikisi farklidir.")
    return lines


def yazdir_ve_kaydet(enc: Encoder, cols: List[Point], baslik: str,
                     output_path: Optional[str] = None,
                     ek_notlar: Sequence[str] = (),
                     probs: Optional[Sequence[Dict[str, float]]] = None,
                     tam_liste: bool = True,
                     mc_samples: int = 0,
                     mc_seed: int = 42,
                     fire_max: int = 0) -> Dict[str, object]:
    """Sonucu ekrana basar, istenirse dosyaya yazar. Ozet sozluk dondurur."""
    rows = merge_rows(cols)
    toplam_bedel = sum(row_cost(r) for r in rows)

    # Sikistirma KAYIPSIZ olmali. merge_rows satir sayisini dusurur ama
    # bedeli ve kapsanan nokta kumesini asla degistirmez (bkz. merge_rows
    # docstring'indeki ispat). Bu kontrol olmadan bozuk bir sikistirma
    # sessizce gecer ve kullaniciya garantiyi tutmayan bir kupon basilir.
    # Ayni invariant health.py'de de var; rapor yolu da korunmali.
    if toplam_bedel != len(cols):
        raise AssertionError(
            f"Sikistirma bedeli bozdu: satirlarin toplam bedeli {toplam_bedel}, "
            f"kolon sayisi {len(cols)}. Kupon basilmadi.")
    if set(rows_to_points(rows)) != set(cols):
        raise AssertionError(
            "Sikistirma kolon kumesini degistirdi: satirlarin acilimi "
            "orijinal kolonlarla ayni degil. Kupon basilmadi.")

    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)

    print()
    print(CIZGI)
    print("SONUC")
    print(CIZGI)
    print(f"Yontem                : {baslik}")
    print(f"Kupon satiri          : {len(rows)}")
    print(f"Kolon bedeli          : {len(cols)}")
    print(f"Kure-kaplama alt sinir: {enc.lower_bound()}")
    print("NOT                   : Satir != bedel. Cifte/kapama satiri "
          "birden fazla kolon uretir; odenecek tutar kolon bedelidir.")
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
            def _pct(x: float) -> float:
                return 100.0 * float(x)
            gaps = [
                ("kume_ici", _pct(rap.p_kume_ici), float(mc["kume_ici"]["pct"])),
                ("P15", _pct(rap.p_15), float(mc["p15"]["pct"])),
                ("P14", _pct(rap.p_14), float(mc["p14"]["pct"])),
            ]
            print(INCE)
            print("Exact vs Monte Carlo sapma (puan, yuzde puan):")
            for name, ex, mc_p in gaps:
                d = mc_p - ex
                print(f"  {name:8s}: exact %{ex:6.2f}  MC %{mc_p:6.2f}  "
                      f"delta {d:+.2f}")
    fire = None
    if fire_max and fire_max > 0:
        from .fire_scenarios import fire_scenario_report
        fire = fire_scenario_report(enc, cols, max_fires=fire_max)
        print(INCE)
        for line in fire_satirlari(fire):
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
            if fire:
                f.write("\n")
                for line in fire_satirlari(fire):
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
            "acik": acik, "olasilik": rap, "monte_carlo": mc, "fire": fire}
