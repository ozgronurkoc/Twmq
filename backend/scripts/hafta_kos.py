#!/usr/bin/env python3
"""Haftalık koşum — kupon öncesi plan, hafta sonrası karne.

Canlı hafta bugüne kadar dört betiğe dağılmıştı (`super_toto_hafta`,
`super_toto_tahmin2`, `super_toto_degerlendir`, `super_toto_sezon`) ve
hangisinin ne zaman koşacağı yalnızca akılda duruyordu. Bu betik o akışın
**iki uçlu** hâlidir:

    python scripts/hafta_kos.py --oncesi  2026_27 5   # kupon kurulur
    python scripts/hafta_kos.py --sonrasi             # karne yazilir

`--oncesi` maç öncesi girdilerden (oran + oynanma payı) bugünkü motorla
planı üretir ve **bütün varsayımlarıyla** basar. `--sonrasi` sonucu ve
resmî ikramiye tablosunu okuyup `docs/KAZANMA_KARNESI.md`'yi **baştan**
yazar — ekleme değil yeniden üretim, çünkü ekleme bir kez bozulunca
sessizce bozuk kalır.

─── Karne niçin "tahmin kaydı" demiyor ───────────────────────────────────

Plan, o haftanın kupon öncesi girdilerinden **bugünkü motorla** yeniden
türetiliyor. Sızıntı yok (girdiler `entered_at`te, sonuç
`results_entered_at`te kaydedildi ve kalabalık modeli 2026/27'yi hiç
görmeyen 112 tarihsel haftada kestirildi), ama motor o gün bugünkü hâlinde
de değildi. Karne bunu her satırda söyler; süslemek, ölçümü ürünün tarifi
olmaktan çıkarırdı.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.karne import (
    CANLI_KOK,
    RAKIP_KOLON,
    canli_hafta,
    canli_karne_satiri,
)
from spor_toto.sistem import VARSAYILAN_GARANTI, kacak_esigi

#: Karnenin yazıldığı yer.
KARNE = KOK.parent / "docs" / "KAZANMA_KARNESI.md"

#: Varsayılan haftalık bütçe (TL). Kullanıcı kararı, ölçüm değil.
VARSAYILAN_BUTCE = 2000.0


def sezon_haftalari(sezon: str) -> list[int]:
    """Yükü olan hafta numaraları, sıralı."""
    dizin = CANLI_KOK / sezon
    if not dizin.exists():
        return []
    out = []
    for p in sorted(dizin.glob("hafta_??.json")):
        try:
            out.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return out


def satirlar(sezon: str, butce: float, garanti: int) -> list[dict[str, Any]]:
    out = []
    for h in sezon_haftalari(sezon):
        r = canli_karne_satiri(sezon, h, butce, garanti)
        if r:
            out.append(r)
    return out


def _tl(v: float | None) -> str:
    return "—" if v is None else f"{v:,.0f}"


def karne_metni(sezon: str, butce: float, garanti: int) -> str:
    rows = satirlar(sezon, butce, garanti)
    bitmis = [r for r in rows if "odul" in r]
    maliyet = sum(r["maliyet"] for r in bitmis)
    odul = sum(r["odul"] for r in bitmis)

    p = [f"""# Kazanma Karnesi — {sezon.replace('_', '/')}

> **Bu bir tahmin kaydı DEĞİLDİR.** Plan, her haftanın kupon öncesi
> girdilerinden (oran + oynanma payı, `entered_at`) **bugünkü motorla**
> yeniden türetildi. Sızıntı yok — girdiler sonuç girilmeden kaydedildi ve
> kalabalık modeli 2026/27'yi hiç görmeyen 112 tarihsel haftada kestirildi.
> Ama sonuç görülmeden **dondurulmuş** bir kayıt da değil: motor o gün
> bugünkü hâlinde değildi.
>
> `python scripts/hafta_kos.py --sonrasi` ile yeniden üretilir.

## Kurulum

| | |
|---|---|
| garanti | **{garanti}** → kaçak eşiği `k ≤ {kacak_esigi(garanti)}`, hedef `P(en iyi kolon ≥ 12)` |
| bütçe | {butce:,.0f} TL ({butce / 10:,.0f} kolon) |
| bedel | ₺10/kolon — ölçülmüş (`getiri.KOLON_BEDELI`) |
| ödül | **garanti tabanı**: `k` kaçakta **bir** kolon `{garanti}−k` kademesinde. **Alt sınır** — gerçekleşen getiri bundan büyüktür |
| rakip kolon | {RAKIP_KOLON:,} — varsayım (`karne.RAKIP_KOLON`); `E[TL]` buna `1/(N·q)` mertebesinde duyarlı |

## Haftalar

| hf | şekil | kolon | maliyet | P(k≤{kacak_esigi(garanti)}) | E[TL] | kaçak | kademe | ödül | net | fiyat ölçeği |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"""]
    for r in rows:
        sekil = f"{r['banko']}b/{r['cift']}ç/{r['uclu']}ü"
        p.append(
            f"| {r['hafta']} | {sekil} | {r['kolon']} | {_tl(r['maliyet'])} | "
            f"{r['p_hedef']:.3f} | {_tl(r.get('beklenen_tl'))} | "
            f"{r.get('kacak', '—')} | {r.get('kademe', '—')} | "
            f"{_tl(r.get('odul'))} | {_tl(r.get('net'))} | "
            f"`{r['fiyat_kunyesi']}` |")

    p.append(f"""
## Toplam ({len(bitmis)} sonuçlanmış hafta)

| | |
|---|---:|
| maliyet | {maliyet:,.0f} TL |
| ödül (garanti tabanı) | {odul:,.0f} TL |
| **net** | **{odul - maliyet:,.0f} TL** |
| geri dönüş | **%{100 * odul / maliyet:.1f}** |

## Okuma

**Fiyat ölçeği haftalar arasında değişti** ve bu, olasılıkları doğrudan
karşılaştırmayı engeller: ilk haftalarda ana fiyat ~%18 marjlı iddaa
oranıydı, sonra ~%4,6 marjlı Pinnacle'a geçildi. Sütun bunu her satırda
söylüyor.

**Ödül sütunu alt sınırdır.** {r['kolon']} kolonluk bir {garanti}-garanti
sistemi, garantinin söylediği tek kolondan fazlasını da tutturur; karne
onları saymaz çünkü kolon listesi bizde değil (şekle biz karar veriyoruz,
kolonları satıcı üretiyor). Gerçekleşen getiri bu tablodan **büyüktür**.

**`n` küçük.** Bu tablo bir strateji karnesi değil, bir **kayıt
başlangıcı**. Anlamlı bir yargı için haftaların birikmesi gerekiyor ve
biriktirmekten başka yolu yok.
""")
    return "\n".join(p) + "\n"


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--oncesi", nargs=2, metavar=("SEZON", "HAFTA"),
                    help="kupon oncesi plan uret")
    ap.add_argument("--sonrasi", action="store_true",
                    help="karneyi yeniden yaz")
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--butce", type=float, default=VARSAYILAN_BUTCE)
    ap.add_argument("--garanti", type=int, default=VARSAYILAN_GARANTI)
    ap.add_argument("--yaz", action="store_true",
                    help="--sonrasi ile: dosyaya yaz (varsayilan: ekrana bas)")
    a = ap.parse_args(argv)

    if a.oncesi:
        sezon, hafta = a.oncesi[0], int(a.oncesi[1])
        r = canli_karne_satiri(sezon, hafta, a.butce, a.garanti)
        if r is None:
            print(f"{sezon} {hafta}. hafta: yuk yok ya da eksik", file=sys.stderr)
            return 1
        print(f"\n{sezon} · {hafta}. hafta · {r['program']}")
        print(f"  fiyat kunyesi : {r['fiyat_kunyesi']}")
        print(f"  oynanma payi  : {r['oynanma_kaynagi']}")
        print(f"  garanti       : {a.garanti} (kacak esigi k <= "
              f"{kacak_esigi(a.garanti)})")
        print(f"  sekil         : {r['banko']} banko · {r['cift']} cifte · "
              f"{r['uclu']} uclu")
        print(f"  bedel         : {r['kolon']} kolon = {r['maliyet']:,.0f} TL")
        print(f"  P(hedef)      : {r['p_hedef']:.4f}")
        if r["beklenen_tl"] is not None:
            print(f"  E[TL]         : {r['beklenen_tl']:,.2f}  "
                  f"(rakip {RAKIP_KOLON:,} kolon VARSAYIMIYLA)")
        print("\n  kupon:")
        for i, x in enumerate(r["picks"], 1):
            print(f"    {i:>2}. {x}")

        # Kalabalik ayari AYRI gosterilir, varsayilan DEGIL: olculdugunde
        # makul her kisitta kazanci sifir cikti (docs Faz B).
        h = canli_hafta(sezon, hafta)
        if h and h["play"]:
            from spor_toto.getiri import beklenen_tl
            from spor_toto.havuz import BOLUSUM
            from spor_toto.secim import (
                GETIRI_KAYIP_TAVANI,
                getiri_secim,
                sistem_secimi,
            )
            taban = sistem_secimi(h["probs"], a.butce, garanti=a.garanti)
            ayar = getiri_secim(h["probs"], h["play"], a.butce,
                                garanti=a.garanti)
            if taban is not None and ayar is not None:
                degisen = [i for i, (x, y) in enumerate(
                    zip(taban.secimler, ayar.secimler), 1) if set(x) != set(y)]
                hv = {k: BOLUSUM[k] * 1e7
                      for k in range(12, a.garanti + 1) if k in BOLUSUM}
                e0 = beklenen_tl(h["probs"], h["play"], taban.secimler, {},
                                 hv, a.garanti, RAKIP_KOLON)
                e1 = beklenen_tl(h["probs"], h["play"], ayar.secimler, {},
                                 hv, a.garanti, RAKIP_KOLON)
                print(f"\n  kalabalik ayari (kayip tavani "
                      f"{GETIRI_KAYIP_TAVANI:.0%}) — VARSAYILAN DEGIL:")
                print(f"    degisen mac : {len(degisen)}"
                      f"{' (' + ', '.join(map(str, degisen)) + '. mac)' if degisen else ''}")
                print(f"    P(hedef)    : {taban.p_hedef:.4f} -> "
                      f"{ayar.p_hedef:.4f}")
                print(f"    E[TL] kat   : {e1 / e0:.3f}x" if e0 else "")
                if degisen:
                    print("    ayarli kupon:")
                    for i in degisen:
                        print(f"      {i:>2}. {''.join(taban.secimler[i-1])}"
                              f"  ->  {''.join(ayar.secimler[i-1])}")
                print("    NOT: uc sonuclanmis haftada gerceklesen kazanc "
                      "SIFIR; kisitsiz arama para kaybettiriyor (docs Faz B).")
        return 0

    metin = karne_metni(a.sezon, a.butce, a.garanti)
    if a.yaz:
        KARNE.write_text(metin, encoding="utf-8")
        print(f"yazildi: {KARNE}")
    else:
        print(metin)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
