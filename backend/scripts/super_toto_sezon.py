#!/usr/bin/env python3
"""İşlenen sezonun birikimli karnesi — hafta hafta değil, **sezon boyu**.

`super_toto_hafta.py` bir haftayı kurar, `super_toto_degerlendir.py` o haftayı
sonuçlandırır. İkisi de tek haftaya bakar. Bu script girilmiş bütün haftaları
üst üste koyar ve tek soruyu sorar:

    *Piyasa bu sezon sözünü tutuyor mu, ve kupon kuralı ne yapıyor?*

    python scripts/super_toto_sezon.py
    python scripts/super_toto_sezon.py --sezon 2026_27 --json

─── Neden birikimli bir defter ────────────────────────────────────────────────

Hafta hafta bakmak, 5-10 hafta sonra kaçınılmaz olarak "kuralı değiştirelim mi"
baskısı üretir. Oysa peşinde olunan üstünlük **0,0005 Brier** büyüklüğünde ve
bir sezon 41×15 = 615 maçtır: o örneklem bu farkı **hiçbir zaman** anlamlı
kılamaz. Defter bunu her koşumda kendi güven aralığıyla birlikte yazar —
"bu sezon karar veremez" cümlesi çıktının kendisinden okunmalı, dipnottan değil.

Bu yüzden defterde bir **karar** satırı yoktur; yalnızca ölçü ve belirsizlik
vardır.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.core import SEMBOLLER  # noqa: E402

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
SEM = SEMBOLLER
VERI_KOK = KOK / "data" / "super_toto"

#: Bir kalibrasyon kovasının yazılması için gereken en az maç.
EN_AZ_KOVA = 20

#: Kovalar. Canlı sezon küçük olduğu için arşivdekinden (15 bant) çok daha
#: kaba: 615 maçlık bir sezonda 15 bant, her birinde 40 maç demektir ve o
#: genişlikte bir güven aralığı hiçbir şey söylemez.
KOVALAR = ((0.0, 0.20), (0.20, 0.30), (0.30, 0.40),
           (0.40, 0.55), (0.55, 0.70), (0.70, 1.01))


def _modul(ad: str):
    spec = importlib.util.spec_from_file_location(
        f"st_{ad}", str(KOK / "scripts" / f"super_toto_{ad}.py"))
    mod = importlib.util.module_from_spec(spec)
    eski = sys.argv
    sys.argv = ["x"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = eski
    return mod


def haftalari_bul(sezon: str) -> List[int]:
    kok = VERI_KOK / sezon
    if not kok.exists():
        raise SystemExit(f"Sezon dizini yok: {kok}")
    out = []
    for yol in sorted(kok.glob("hafta_*.json")):
        ad = yol.stem
        if ad.endswith("_kupon"):
            continue
        try:
            out.append(int(ad.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return out


def topla(sezon: str) -> Dict[str, Any]:
    """Girilmiş bütün haftaları tek tabloya indirger."""
    from spor_toto.benzer import _wilson
    from spor_toto.evaluate import brier, log_kaybi
    from spor_toto.odds import ARINDIRMA_VARSAYILAN

    hafta_mod = _modul("hafta")
    deg_mod = _modul("degerlendir")

    haftalar: List[Dict[str, Any]] = []
    noktalar: List[tuple] = []          # (piyasa p, gerceklesti mi)
    for no in haftalari_bul(sezon):
        d = hafta_mod.hafta_yukle(sezon, no)
        meta = d["meta"]
        sonuc = meta.get("results")
        kayit: Dict[str, Any] = {
            "hafta": no,
            "program": meta.get("program"),
            "sonuc_var": bool(sonuc),
            "uyari": len(meta.get("data_warnings") or [])
                     + len(meta.get("uretilen_uyarilar") or []),
            "oransiz_mac": sum(1 for m in d["matches"] if m["odds_yok"]),
        }
        if sonuc:
            b = sum(brier(m["probs"], k) for m, k in zip(d["matches"], sonuc)) / 15
            l = sum(log_kaybi(m["probs"], k) for m, k in zip(d["matches"], sonuc)) / 15
            fav_dogru = sum(1 for m, k in zip(d["matches"], sonuc)
                            if m["fav"] == k)
            fav_beklenen = sum(m["probs"][m["fav"]] for m in d["matches"] if m["fav"])
            kayit.update({"brier": b, "log": l,
                          "favori_dogru": fav_dogru,
                          "favori_beklenen": fav_beklenen})
            for m, k in zip(d["matches"], sonuc):
                if m["odds_yok"]:
                    continue          # 1/3 bir tahmin degil, kalibrasyona girmez
                for s in SEM:
                    noktalar.append((m["probs"][s], k == s))

        kupon_yolu = VERI_KOK / sezon / f"hafta_{no:02d}_kupon.json"
        if kupon_yolu.exists() and sonuc:
            kupon = json.loads(kupon_yolu.read_text(encoding="utf-8"))
            s0 = deg_mod.kupon_degerlendir(d, kupon["variants"][0]["picks"])
            kayit.update({"en_iyi_kolon": s0["best"],
                          "kacak": s0["miss_count"],
                          "beklenen_kacak": s0["expected_misses"],
                          "kume_ici_p": s0["p_in_set"]})
        haftalar.append(kayit)

    olculen = [h for h in haftalar if h["sonuc_var"]]
    kovalar = []
    for lo, hi in KOVALAR:
        g = [t for t in noktalar if lo <= t[0] < hi]
        if len(g) < EN_AZ_KOVA:
            continue
        n = len(g)
        k = sum(1 for t in g if t[1])
        alt, ust = _wilson(k, n)
        bekleniyor = sum(t[0] for t in g) / n
        kovalar.append({"lo": lo, "hi": hi, "n": n, "piyasa": bekleniyor,
                        "gercek": k / n, "ga_alt": alt, "ga_ust": ust,
                        "piyasa_ga_icinde": alt <= bekleniyor <= ust})

    n_mac = 15 * len(olculen)
    ozet: Dict[str, Any] = {
        "sezon": sezon,
        "arindirma": ARINDIRMA_VARSAYILAN,
        "hafta_girilmis": len(haftalar),
        "hafta_olculen": len(olculen),
        "mac": n_mac,
        "kovalar": kovalar,
    }
    if olculen:
        ozet["brier"] = sum(h["brier"] for h in olculen) / len(olculen)
        ozet["log"] = sum(h["log"] for h in olculen) / len(olculen)
        gozlenen = sum(h["favori_dogru"] for h in olculen)
        beklenen = sum(h["favori_beklenen"] for h in olculen)
        # Bagimsizlik varsayimiyla toplam favori isabetinin sapmasi.
        var = sum(h["favori_beklenen"] - h["favori_beklenen"] ** 2 / 15
                  for h in olculen)
        ozet.update({
            "favori_gozlenen": gozlenen,
            "favori_beklenen": beklenen,
            "favori_sapma_sd": ((gozlenen - beklenen) / math.sqrt(var)
                                if var > 0 else None),
        })
        kolonlu = [h for h in olculen if "en_iyi_kolon" in h]
        if kolonlu:
            ozet["en_iyi_kolon"] = [h["en_iyi_kolon"] for h in kolonlu]
            ozet["kacak_gozlenen"] = sum(h["kacak"] for h in kolonlu)
            ozet["kacak_beklenen"] = sum(h["beklenen_kacak"] for h in kolonlu)
    ozet["haftalar"] = haftalar
    ozet["yeterlilik"] = yeterlilik_notu(n_mac)
    return ozet


def yeterlilik_notu(n_mac: int) -> Dict[str, Any]:
    """Bu örneklem neyi ayırt edebilir, neyi edemez — **her koşumda yazılır.**

    Peşinde olunan üstünlük ~0,0005 Brier. Maç başına Brier'in standart
    sapması kabaca 0,4'tür; n maçta ortalamanın standart hatası 0,4/√n ve
    %95 aralığın yarı genişliği ≈ 1,96 × o. Ayırt edilebilmesi için yarı
    genişliğin 0,0005'in altına inmesi gerekir.
    """
    hedef = 0.0005
    sd = 0.4
    gerekli = math.ceil((1.96 * sd / hedef) ** 2)
    yari = 1.96 * sd / math.sqrt(n_mac) if n_mac else None
    return {
        "n_mac": n_mac,
        "aranan_fark": hedef,
        "yari_genislik": yari,
        "gerekli_mac": gerekli,
        "karar_verebilir": bool(yari is not None and yari < hedef),
        "not": (
            f"Aranan üstünlük {hedef} Brier. Bu örneklemde %95 aralığın yarı "
            f"genişliği ≈ {yari:.4f} — aranan farkın "
            f"{(yari / hedef):.0f} katı. Ayırt edebilmek için ~{gerekli:,} maç "
            f"gerekir; bir sezon 615 maçtır. **Bu defter kural değiştirmek "
            f"için değil, kuralın ne yaptığını görmek içindir.**"
            if yari else "Ölçülmüş hafta yok."),
    }


def yaz(o: Dict[str, Any]) -> None:
    print("=" * 78)
    print(f"{o['sezon']} · SEZON KARNESİ · arındırma: {o['arindirma']}")
    print("=" * 78)
    print(f"Girilmiş hafta: {o['hafta_girilmis']} · sonucu olan: "
          f"{o['hafta_olculen']} · maç: {o['mac']}")

    print(f"\n{'hafta':>6}{'sonuç':>7}{'Brier':>8}{'log':>7}{'fav':>6}"
          f"{'bekl':>7}{'kolon':>7}{'kaçak':>7}{'uyarı':>7}")
    for h in o["haftalar"]:
        if not h["sonuc_var"]:
            print(f"{h['hafta']:>6}{'—':>7}{'':>8}{'':>7}{'':>6}{'':>7}"
                  f"{'':>7}{'':>7}{h['uyari']:>7}")
            continue
        print(f"{h['hafta']:>6}{'var':>7}{h['brier']:>8.4f}{h['log']:>7.3f}"
              f"{h['favori_dogru']:>6}{h['favori_beklenen']:>7.2f}"
              f"{h.get('en_iyi_kolon', '—'):>7}{h.get('kacak', '—'):>7}"
              f"{h['uyari']:>7}")

    if o["hafta_olculen"]:
        print(f"\n─── BİRİKİMLİ ───────────────────────────────────────────────────────────")
        print(f"Brier {o['brier']:.4f} · log {o['log']:.3f}")
        sd = o.get("favori_sapma_sd")
        print(f"Favori isabeti: gözlenen {o['favori_gozlenen']} ↔ beklenen "
              f"{o['favori_beklenen']:.2f}"
              + (f" ({sd:+.2f} sd)" if sd is not None else ""))
        if "en_iyi_kolon" in o:
            k = o["en_iyi_kolon"]
            print(f"En iyi kolon: {k} · ortalama {sum(k)/len(k):.2f}")
            print(f"Kaçak: gözlenen {o['kacak_gozlenen']} ↔ beklenen "
                  f"{o['kacak_beklenen']:.2f}")

    if o["kovalar"]:
        print(f"\n─── KALİBRASYON (canlı sezon) ───────────────────────────────────────────")
        print(f"{'kova':<12}{'n':>6}{'piyasa':>9}{'gerçek':>9}{'%95 aralık':>20}")
        for r in o["kovalar"]:
            isaret = "" if r["piyasa_ga_icinde"] else "  ← DIŞINDA"
            print(f"%{100*r['lo']:>3.0f}–%{100*r['hi']:<6.0f}{r['n']:>6}"
                  f"{100*r['piyasa']:>8.1f}%{100*r['gercek']:>8.1f}%"
                  f"   [%{100*r['ga_alt']:>5.1f}, %{100*r['ga_ust']:>5.1f}]{isaret}")

    print(f"\n─── ÖRNEKLEM YETERLİLİĞİ ────────────────────────────────────────────────")
    print(f"  {o['yeterlilik']['not']}")


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    o = topla(a.sezon)
    print(json.dumps(o, ensure_ascii=False, indent=1)) if a.json else yaz(o)


if __name__ == "__main__":
    main()
