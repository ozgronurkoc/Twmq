#!/usr/bin/env python3
"""Ö4 — iddaa ekseni: ölçtüğümüz piyasa, oynadığımız piyasa değil.

Projenin bütün kalibrasyonu **football-data** üzerinde: marj %7,26. Oysa
kupon **iddaa**'da oynanıyor: marj %18,86 (bayi) / %21,3 (web). Aradaki
oran **2,6 kat** ve marj, arındırma yönteminin ne kadar önemli olduğunu
doğrudan belirleyen sayı. A5'in bulgusu (`orantili` → `shin`, −0,00042
Brier) düşük marjlı bir piyasada ölçüldü; yüksek marjlı bir piyasada aynı
sorunun cevabı **aynı olmak zorunda değil**.

Bu betiğin işi ölçmek **değil** — bugün ölçülemez. İşi, ölçümün ne zaman
mümkün olacağını **şimdiden yazmak**, ki 5–10 hafta sonra erken karar
baskısı doğmasın:

    python scripts/iddaa_hazirlik.py            # elde ne var, ne eksik
    python scripts/iddaa_hazirlik.py --guc      # kac hafta gerekir
    python scripts/iddaa_hazirlik.py --bayi-web # odd vs wodd (bugun olculebilir)

─── Üç alt soru, üç ayrı veri ihtiyacı ───────────────────────────────────

**(a) iddaa'nın kendi kalibrasyonu.** (iddaa oranı + SONUÇ) çifti gerekir.
Bunu yalnızca kupon haftaları verir: haftada 15 maç, sonucu bilinen.
Bülten arşivi (`data/iddaa/*.csv`) oranı taşır ama **sonucu taşımaz**, o
yüzden tek başına kalibrasyon ölçemez.

**(b) eşiklerin iddaa ölçeğinde türetilmesi.** Aynı veri, aynı hacim.
Ö1'den sonra rolü değişti ama **bitmedi**: canlı kupon artık hedefe göre
kuruluyor, ama bütçe hâlâ eşik kuralının bedelinden geliyor
(`super_toto_hafta.kupon_kur`). Yani eşik, işaret seçmiyor ama **bütçe
belirliyor**.

**(c) bayi (`odd`) ↔ web (`wodd`) farkı.** Bu, ötekilerden farklı olarak
**bugün kısmen ölçülebilir**: iki fiyatın ayrışıp ayrışmadığı sonuç
gerektirmez, yalnızca bülten arşivi yeter. `--bayi-web` onu koşar. Sonucu
öngörüp öngörmediği ise yine sonuç gerektirir.

─── Durma kuralı ─────────────────────────────────────────────────────────

Aşağıdaki `guc_analizi` sd'yi **uydurmuyor, ölçüyor**: aynı maçlarda iki
arındırma yöntemi arasındaki hafta başına Brier farkının gerçek standart
sapması (football-data, 38 hafta, 15'lik hafta). Aranan etki ise ölçüme
BAKILMADAN, marj oranından türetiliyor (bkz. `ARANAN_ETKI`).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

VERI_KOK = KOK / "data"
ARSIV_KOK = VERI_KOK / "iddaa"
KUPON_KOK = VERI_KOK / "super_toto"
GERI_TEST_ORAN = VERI_KOK / "odds" / "odds_2025_26.csv"

#: Bir sezonun hafta sayısı — 2025/26'da 41 hafta kupon çıktı.
SEZON_HAFTA = 41

#: **Aranan etki, ölçüme bakılmadan seçildi.** Gerekçe: A5'te arındırma
#: yöntemi seçimi football-data'da (marj %7,26) hafta başına 0,00059 Brier
#: değiştirdi. Shin düzeltmesinin büyüklüğü marjla ölçeklenir; iddaa'nın
#: marjı 2,6 kat olduğuna göre aynı sorunun orada ~0,0015 getirmesi
#: beklenir. Bu sayı ÖNCEDEN yazılıyor ki sonuç görüldükten sonra
#: "aslında daha küçüğü de sayılır" denemesin.
ARANAN_ETKI = 0.0015

#: `guc_analizi` sd'yi ölçemezse kullanılacak değer (38 haftada ölçülen).
#: Ölçüm mümkünse **her zaman ölçülen kazanır**; bu yalnızca oran dosyası
#: yokken betiğin susmaması için.
VARSAYILAN_SD = 0.00358

#: İki fiyatın "ayrışmış" sayılması için gereken en küçük sembol farkı.
#: 1 puan, kupon kararını çevirebilecek en küçük büyüklük mertebesi.
AYRISMA_ESIGI = 0.01


def _oranli_mi(o: dict[str, Any]) -> bool:
    try:
        return len(o) == 3 and min(float(v) for v in o.values()) > 1.0
    except (TypeError, ValueError):
        return False


# ─── elde ne var ──────────────────────────────────────────────────────────

def elde_ne_var(sezon: str = "2026_27") -> dict[str, Any]:
    """Kaç maçta (iddaa oranı + sonuç) birlikte var — ölçümün asıl yakıtı."""
    from spor_toto.odds import margin

    haftalar: list[dict[str, Any]] = []
    dizin = KUPON_KOK / sezon
    for yol in sorted(dizin.glob("hafta_*.json")) if dizin.is_dir() else []:
        if yol.name.endswith("_kupon.json"):
            continue
        d = json.loads(yol.read_text(encoding="utf-8"))
        meta = d.get("meta") or {}
        kind = str(meta.get("odds_kind") or "")
        maclar = d.get("matches") or []
        oranli = [m for m in maclar if _oranli_mi(m.get("odds") or {})]
        cozulmus = [m for m in oranli if m.get("result")]
        marjlar = [margin({k: float(v) for k, v in m["odds"].items()})
                   for m in oranli]
        haftalar.append({
            "hafta": meta.get("week"),
            "oran_kaynagi": kind,
            "iddaa_mi": kind.startswith("iddaa"),
            "mac": len(maclar),
            "oranli": len(oranli),
            "cozulmus": len(cozulmus),
            "marj": statistics.mean(marjlar) if marjlar else None,
        })

    kullanilabilir = [h for h in haftalar if h["iddaa_mi"] and h["cozulmus"]]
    return {
        "sezon": sezon,
        "haftalar": haftalar,
        "kullanilabilir_hafta": len(kullanilabilir),
        "kullanilabilir_mac": sum(h["cozulmus"] for h in kullanilabilir),
        "arsiv_anlik": len(sorted(ARSIV_KOK.glob("iddaa_*.csv"))),
        "arsiv_not": ("bulten arsivi ORAN tasir, SONUC tasimaz; kalibrasyonu "
                      "tek basina olcemez"),
    }


# ─── güç analizi ──────────────────────────────────────────────────────────

def hafta_sd(yol: Path | None = None) -> tuple[float, int]:
    """Hafta başına Brier farkının **ölçülmüş** standart sapması.

    Aynı maçlarda iki arındırma yöntemi (`orantili` ↔ `shin`) koşulur;
    aradaki hafta başına farkın dağılımı, "bir arındırma sorusunu ayırt
    etmek ne kadar zor" sorusunun doğrudan cevabıdır. Uydurulmuş bir sd
    yerine bu kullanılıyor çünkü elde ölçecek veri var.
    """
    from spor_toto.history import SYMBOLS
    from spor_toto.odds import implied_probs

    # Brier BURADA IC FONKSIYON OLARAK YENIDEN YAZILMISTI. Govde kanonikle
    # birebir ayniydi — `history.SYMBOLS` zaten `core.SEMBOLLER`in kendisi
    # (`history.py:32`), yani iterasyon duzeni de ayniydi. Tek kaynak
    # `spor_toto.ortak.brier`.
    from spor_toto.ortak import brier

    yol = yol or GERI_TEST_ORAN
    if not yol.is_file():
        return VARSAYILAN_SD, 0

    gruplar: dict[str, list[tuple[dict[str, float], str]]] = {}
    with yol.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                o = {"1": float(r["AvgCH"]), "0": float(r["AvgCD"]),
                     "2": float(r["AvgCA"])}
            except (ValueError, KeyError):
                continue
            if min(o.values()) <= 1.0 or r.get("code") not in SYMBOLS:
                continue
            gruplar.setdefault(r["week"], []).append((o, r["code"]))

    farklar = []
    for ms in gruplar.values():
        if len(ms) < 10:
            continue
        a = sum(brier(implied_probs(o, "orantili"), k) for o, k in ms) / len(ms)
        b = sum(brier(implied_probs(o, "shin"), k) for o, k in ms) / len(ms)
        farklar.append(b - a)
    if len(farklar) < 2:
        return VARSAYILAN_SD, len(farklar)
    return statistics.pstdev(farklar), len(farklar)


def guc_analizi(n_hafta: int, etki: float = ARANAN_ETKI,
                sd: float | None = None) -> dict[str, Any]:
    """Bu soruyu cevaplamak için kaç kupon haftası gerekir.

    İki taraflı, %80 güç, %5 anlamlılık: `n ≈ ((z_a + z_b)·sd / etki)²`.
    Kesin sayı değil **büyüklük mertebesi** verir — ve bu soruda mertebe
    zaten cevabı belirliyor.
    """
    olculen_sd, sd_hafta = hafta_sd()
    kullanilan = sd if sd is not None else olculen_sd
    z_a, z_b = 1.959964, 0.841621
    gerekli = math.ceil(((z_a + z_b) * kullanilan / etki) ** 2)
    egri = {}
    for e in (0.005, 0.003, ARANAN_ETKI, 0.001, 0.0005):
        egri[f"{e:.4f}"] = math.ceil(((z_a + z_b) * kullanilan / e) ** 2)
    return {
        "eldeki_hafta": n_hafta,
        "aranan_etki": etki,
        "sd": kullanilan,
        "sd_olculdu_mu": sd is None and sd_hafta > 0,
        "sd_hafta": sd_hafta,
        "gerekli_hafta": gerekli,
        "gerekli_sezon": gerekli / SEZON_HAFTA,
        "egri": egri,
        "yeterli": n_hafta >= gerekli,
    }


# ─── bayi ↔ web ───────────────────────────────────────────────────────────

def bayi_web() -> dict[str, Any]:
    """`odd` (bayi) ile `wodd` (web) aynı görüşü mü taşıyor?

    **Bugün ölçülebilen tek Ö4 sorusu**: iki fiyatın ayrışıp ayrışmadığı
    sonuç gerektirmez. Ayrışmıyorlarsa "fark bilgi taşıyor mu" sorusunun
    ölçülecek bir tarafı zaten kalmaz.
    """
    from spor_toto.odds import implied_probs, margin

    marj_b: list[float] = []
    marj_w: list[float] = []
    farklar: list[float] = []
    for yol in sorted(ARSIV_KOK.glob("iddaa_*.csv")):
        with yol.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    b = {s: float(r[f"odd_{s}"]) for s in ("1", "0", "2")}
                    w = {s: float(r[f"wodd_{s}"]) for s in ("1", "0", "2")}
                except (ValueError, KeyError):
                    continue
                if not (_oranli_mi(b) and _oranli_mi(w)):
                    continue
                marj_b.append(margin(b))
                marj_w.append(margin(w))
                pb, pw = implied_probs(b), implied_probs(w)
                farklar.append(max(abs(pb[s] - pw[s]) for s in ("1", "0", "2")))

    n = len(farklar)
    ayrisan = sum(1 for x in farklar if x > AYRISMA_ESIGI)
    return {
        "n": n,
        "marj_bayi": statistics.mean(marj_b) if marj_b else None,
        "marj_web": statistics.mean(marj_w) if marj_w else None,
        "fark_ort": statistics.mean(farklar) if farklar else None,
        "fark_ortanca": statistics.median(farklar) if farklar else None,
        "ayrisan": ayrisan,
        "ayrisan_oran": ayrisan / n if n else None,
        "yorum": ("marj ayri, GORUS ayni: arindirmadan sonra iki fiyat "
                  "birbirine cok yakin duruyor" if n and ayrisan / n < 0.25
                  else "iki fiyat arindirmadan sonra da ayrisiyor"),
    }


# ─── rapor ────────────────────────────────────────────────────────────────

def rapor(sezon: str = "2026_27") -> dict[str, Any]:
    d = elde_ne_var(sezon)
    n = d["kullanilabilir_hafta"]
    g = guc_analizi(n)
    if n == 0:
        durum, gerekce = "olculemez", "iddaa orani + sonuc tasiyan hafta yok"
    elif not g["yeterli"]:
        durum, gerekce = "birikiyor", (
            f"{n} hafta var, ~{g['gerekli_hafta']} gerekiyor "
            f"(~{g['gerekli_sezon']:.1f} sezon)")
    else:
        durum, gerekce = "olculebilir", "guc yeterli, kalibrasyonu kos"
    return {
        **d,
        "guc": g,
        "bayi_web": bayi_web(),
        "durum": durum,
        "gerekce": gerekce,
        "soru": ("iddaa'nin kendi kalibrasyonu football-data'dan farkli mi; "
                 "esikler iddaa olceginde nereye duser"),
        "durma_kurali": (
            f"{g['gerekli_hafta']} kupon haftasi (iddaa orani + sonuc) "
            f"birikmeden kalibrasyon KOSULMAZ. Erken kosulup 'fark yok' "
            f"denmesi, gucun yetmedigi bir olcumu bulgu sanmaktir."),
        "sinir": ("bulten arsivi ileriye donuk buyur — gecmis iddaa orani "
                  "hicbir kaynakta yayinlanmiyor; kacan hafta geri gelmez"),
    }


def yaz(o: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print("=" * 78)
    print("Ö4 — İDDAA EKSENİ")
    print("=" * 78)
    print(f"Soru: {o['soru']}")
    print(f"\nDurum: {o['durum'].upper()} — {o['gerekce']}")

    print(f"\n{'hafta':>6}{'oran kaynağı':>18}{'maç':>6}{'oranlı':>8}"
          f"{'çözülmüş':>10}{'marj':>8}")
    for h in o["haftalar"]:
        marj = f"{100 * h['marj']:.2f}%" if h["marj"] is not None else "—"
        print(f"{h['hafta']!s:>6}{h['oran_kaynagi']:>18}{h['mac']:>6}"
              f"{h['oranli']:>8}{h['cozulmus']:>10}{marj:>8}")
    print(f"\n  Ölçüme giren: {o['kullanilabilir_hafta']} hafta · "
          f"{o['kullanilabilir_mac']} maç")
    print(f"  Bülten arşivi: {o['arsiv_anlik']} anlık görüntü — "
          f"{o['arsiv_not']}")

    g = o["guc"]
    print("\n─── GÜÇ ANALİZİ ─────────────────────────────────────────────────────────")
    kaynak = (f"ÖLÇÜLDÜ ({g['sd_hafta']} hafta)" if g["sd_olculdu_mu"]
              else "varsayılan")
    print(f"  sd = {g['sd']:.5f} [{kaynak}] · aranan etki {g['aranan_etki']}")
    print(f"  Gerekli hafta ≈ {g['gerekli_hafta']} "
          f"(≈ {g['gerekli_sezon']:.1f} sezon) · elde {g['eldeki_hafta']}")
    print(f"\n  {'etki (Brier)':>14}{'gerekli hafta':>16}{'sezon':>9}")
    for e, n in g["egri"].items():
        print(f"  {e:>14}{n:>16}{n / SEZON_HAFTA:>9.1f}")

    b = o["bayi_web"]
    print("\n─── BAYİ ↔ WEB (bugün ölçülebilen tek parça) ────────────────────────────")
    if b["n"]:
        print(f"  {b['n']} maç · marj bayi %{100 * b['marj_bayi']:.2f} ↔ "
              f"web %{100 * b['marj_web']:.2f}")
        print(f"  Arındırma SONRASI en büyük sembol farkı: "
              f"ort {100 * b['fark_ort']:.2f} puan · "
              f"ortanca {100 * b['fark_ortanca']:.2f} puan")
        print(f"  1 puandan çok ayrışan: {b['ayrisan']}/{b['n']} "
              f"(%{100 * b['ayrisan_oran']:.1f})")
        print(f"  → {b['yorum']}")
    else:
        print("  arşiv boş")

    print("\n─── DURMA KURALI ────────────────────────────────────────────────────────")
    print(f"  {o['durma_kurali']}")
    print("\n─── BİLİNEN SINIR ───────────────────────────────────────────────────────")
    print(f"  {o['sinir']}")


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description="O4: iddaa ekseni hazirlik")
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--guc", action="store_true", help="yalnizca guc analizi")
    ap.add_argument("--bayi-web", action="store_true",
                    help="yalnizca odd/wodd kiyasi")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    o = rapor(a.sezon)
    if a.json:
        print(json.dumps(o, ensure_ascii=False, indent=1, default=str))
    elif a.guc:
        print(json.dumps(o["guc"], ensure_ascii=False, indent=1))
    elif a.bayi_web:
        print(json.dumps(o["bayi_web"], ensure_ascii=False, indent=1))
    else:
        yaz(o)


if __name__ == "__main__":  # pragma: no cover
    main()
