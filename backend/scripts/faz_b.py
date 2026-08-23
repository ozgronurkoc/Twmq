#!/usr/bin/env python3
"""Faz B — havuz ekseni: soru kuruldu, veri bekleniyor.

Faz B'nin sorusu (§6.3b):

    Aynı tutturma olasılığında **az oynanan** sembolü işaretlemek, kişi başı
    ikramiyeyi ölçülebilir biçimde büyütüyor mu?

Bu script iki iş yapar:

    python scripts/faz_b.py            # elde ne var, ne eksik
    python scripts/faz_b.py --guc      # kac hafta gerekir (guc analizi)

**Tahmin ekseninden farkı önemlidir.** Bu soru piyasayı geçmeyi
gerektirmiyor: piyasa fiyatı tamamen doğru olsa bile, aynı olasılıktaki iki
sonuçtan az oynananı seçmek tutturma olasılığını değiştirmeden **payı**
büyütür. A1–A3'ün kapattığı arayış bu ekseni kapatmaz.

**Bugünkü cevap: ölçülemez.** Elde bir haftalık ikramiye kaydı var. Bir
gözlemle bağıntı ölçülmez ve bu script bunu her koşumda yazar — durma
kuralının 1. şıkkı (§6.3b) tam olarak budur.
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

VERI_KOK = KOK / "data" / "super_toto"

#: Ayirt edilmek istenen etki: crowd_ratio'daki bir birimlik artisin kisi
#: basi ikramiyeyi kac kat degistirdigi (log olcekte). 0,5 "orta buyuklukte"
#: bir etkidir ve olcum sonucuna BAKILMADAN secildi.
ARANAN_ETKI = 0.5

#: Kisi basi ikramiyenin log'unun haftalar arasi standart sapmasi. Kazanan
#: sayisi 0 ile binler arasinda gezdigi icin buyuk; 1,5 muhafazakar bir
#: tahmindir ve gercek veri geldiginde YERINE OLCULEN konmalidir.
VARSAYILAN_SD = 1.5


def _modul(ad: str):
    """Kardes betigi getirir — artik sıradan bir import.

    Once `spec_from_file_location` ile dosya yolundan yukleniyordu ve
    yuklerken `sys.argv`yi geciciyle degistiriyordu. Ikisi de gereksizdi:
    bu dizin bir paket (`scripts/__init__.py`) ve hedef betiklerin hepsinde
    `if __name__ == "__main__"` guard'i var, yani import etmek argparse'i
    tetiklemiyor.
    """
    return importlib.import_module(f"scripts.super_toto_{ad}")


def elde_ne_var(sezon: str = "2026_27") -> Dict[str, Any]:
    """İkramiye kaydı olan haftalar ve o haftaların kalabalık ölçüleri."""
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU

    hafta_mod = _modul("hafta")
    sezon_mod = _modul("sezon")

    satirlar: List[Dict[str, Any]] = []
    for no in sezon_mod.haftalari_bul(sezon):
        d = hafta_mod.hafta_yukle(sezon, no)
        meta = d["meta"]
        k = hafta_mod.kupon_kur(d, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
        pay = meta.get("payout")
        kayit: Dict[str, Any] = {
            "hafta": no,
            "crowd_ratio": k["crowd_ratio"],
            "in_set_p": k["in_set_p"],
            "crowd_in_set_p": k["crowd_in_set_p"],
            "ikramiye_var": bool(pay),
        }
        if pay:
            # KAZANANI OLAN en ust kademe. En ust kademe korukorune
            # alinsaydi 15 bilen secilirdi ve o cogu hafta cikmaz
            # (1. hafta: 0 kisi, 30,1 milyon TL devretti) — havuz ekseninin
            # sorusu "kisi basi ne dustu" oldugu icin bos kademe cevap
            # vermez.
            odullu = [t for t in pay["tiers"] if t.get("prize")]
            ust = max(odullu, key=lambda t: t["correct"]) if odullu else None
            kayit["devreden"] = next(
                (t.get("rollover") for t in pay["tiers"] if t.get("rollover")),
                None)
            if ust:
                kayit.update({
                    "kademe": ust["correct"],
                    "kazanan": ust.get("winners"),
                    "kisi_basi": ust.get("prize"),
                })
            else:
                kayit["ikramiye_var"] = False
        satirlar.append(kayit)
    return {"sezon": sezon, "haftalar": satirlar,
            "ikramiyeli_hafta": sum(1 for r in satirlar if r["ikramiye_var"])}


def guc_analizi(n_hafta: int, sd: float = VARSAYILAN_SD,
                etki: float = ARANAN_ETKI) -> Dict[str, Any]:
    """Bu soruyu cevaplamak için kaç hafta gerekir.

    Basit iki taraflı güç hesabı (%80 güç, %5 anlamlılık): bir eğim
    katsayısını ayırt etmek için gereken n ≈ ((z_a + z_b)·sd / etki)².
    Kesin bir sayı değil, **büyüklük mertebesi** verir — ve bu soruda
    mertebe zaten cevabı belirliyor.
    """
    z_a, z_b = 1.959964, 0.841621
    gerekli = math.ceil(((z_a + z_b) * sd / etki) ** 2)
    # Kazanan cikmayan haftalar kisi basi ikramiye tasimaz ve olcume
    # giremez; gecen sezon 41 haftanin 36'si tam kupon uretti, 14 bilen
    # ise cok daha seyrek. Muhafazakar olarak haftalarin yarisi sayilir.
    kullanilabilir_oran = 0.5
    sezon_hafta = 41
    sezon = gerekli / (sezon_hafta * kullanilabilir_oran)
    return {
        "eldeki_hafta": n_hafta,
        "aranan_etki": etki,
        "varsayilan_sd": sd,
        "gerekli_hafta": gerekli,
        "gerekli_sezon": sezon,
        "yeterli": n_hafta >= gerekli,
    }


def rapor(sezon: str = "2026_27") -> Dict[str, Any]:
    d = elde_ne_var(sezon)
    n = d["ikramiyeli_hafta"]
    g = guc_analizi(n)
    if n == 0:
        durum, gerekce = "olculemez", "hic ikramiye kaydi yok"
    elif n < 3:
        durum, gerekce = "olculemez", f"{n} hafta — bagintiya bakilamaz"
    elif not g["yeterli"]:
        durum, gerekce = "acik ama olculmemis", (
            f"{n} hafta var, ~{g['gerekli_hafta']} gerekiyor")
    else:
        durum, gerekce = "olculebilir", "guc yeterli, bagintiyi kos"
    return {
        **d, "guc": g, "durum": durum, "gerekce": gerekce,
        "soru": ("ayni tutturma olasiliginda az oynanan sembolu isaretlemek "
                 "kisi basi ikramiyeyi buyutuyor mu"),
        "sinir": ("oynanma yuzdeleri TEK PLATFORMUN kullanicilaridir, Spor "
                  "Toto havuzunun tamami degildir; butun crowd_* olculeri bu "
                  "vekile dayanir ve vekilin havuzu ne kadar temsil ettigi "
                  "OLCULMEMISTIR"),
    }


def yaz(o: Dict[str, Any]) -> None:
    print("=" * 78)
    print("FAZ B — HAVUZ EKSENİ")
    print("=" * 78)
    print(f"Soru: {o['soru']}")
    print(f"\nDurum: {o['durum'].upper()} — {o['gerekce']}")

    print(f"\n{'hafta':>6}{'crowd_ratio':>13}{'küme-içi':>11}"
          f"{'kalabalık':>11}{'kademe':>8}{'kazanan':>9}{'kişi başı':>16}")
    for r in o["haftalar"]:
        cr = f"{r['crowd_ratio']:.3f}" if r["crowd_ratio"] else "—"
        kb = (f"{r['kisi_basi']:,.2f}" if r.get("kisi_basi") else "—")
        print(f"{r['hafta']:>6}{cr:>13}{100*r['in_set_p']:>10.2f}%"
              f"{100*r['crowd_in_set_p']:>10.2f}%"
              f"{str(r.get('kademe', '—')):>8}"
              f"{str(r.get('kazanan', '—')):>9}{kb:>16}")

    g = o["guc"]
    print(f"\n─── GÜÇ ANALİZİ ─────────────────────────────────────────────────────────")
    print(f"  Aranan etki {g['aranan_etki']} · varsayılan sd {g['varsayilan_sd']}")
    print(f"  Gerekli hafta ≈ {g['gerekli_hafta']} "
          f"(≈ {g['gerekli_sezon']:.1f} sezon) · elde {g['eldeki_hafta']}")
    print(f"\n  Bu, ekseni kapatmaz ama beklentiyi bugünden düzeltir: Faz B'nin")
    print(f"  cevabı bu sezon gelmeyecek. Gelecek olan şey, verinin")
    print(f"  BİRİKTİRİLMEYE BAŞLANMASIDIR — toplanmamış veri hiç ölçülemez.")

    print(f"\n─── BİLİNEN SINIR ───────────────────────────────────────────────────────")
    print(f"  {o['sinir']}")


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--guc", action="store_true",
                    help="yalnizca guc analizi")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    o = rapor(a.sezon)
    if a.json:
        print(json.dumps(o, ensure_ascii=False, indent=1))
    elif a.guc:
        print(json.dumps(o["guc"], ensure_ascii=False, indent=1))
    else:
        yaz(o)


if __name__ == "__main__":
    main()
