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
from spor_toto.karne import VARSAYILAN_GARANTI
from spor_toto.secim import kacak_esigi

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


def _merdiven(probs: list[dict[str, float]], garanti: int,
              secili_kolon: int, en_cok_tl: float = 20_000.0) -> None:
    """Haftanın **merdiveni**: bütçenin ne satın aldığı görünür olsun.

    E2 şekli hedefin değil **bütçenin** belirlediğini ölçtü (§3.57); ama
    `--oncesi` bütçeyi tek satır olarak basıyordu, yani o kararın bedeli
    görünmüyordu. Merdiven seçilen basamağı `→` ile işaretler ve her adımın
    marjinal fiyatını (bir puan `P(hedef)` kaç TL) yanına yazar.

    Marjinal fiyat **seçili satıra göre** yazılır, bir öncekine göre değil:
    karar "bir üst basamağa çıkayım mı" sorusudur ve komşu satırlar arası
    fark o soruyu yanıtlamaz (merdivende neredeyse bedava tek adımlar var,
    ama onlara ancak pahalı bir adımdan sonra varılıyor).

    Bu bir öneri değil, bir **gösterge**: hangi basamağın oynanacağı hâlâ
    bütçe kararıdır ve E6 (`docs/KAZANMA_PLANI.md`) o kararı değiştirmek
    için gereken ölçümü yapar.
    """
    from spor_toto.hafta_hakki import cephe

    adimlar = cephe(probs, garanti=garanti, en_cok_tl=en_cok_tl)
    if not adimlar:
        return
    secili = next((x for x in adimlar if x.kolon == secili_kolon), None)
    print(f"\n  merdiven (tavan {en_cok_tl:,.0f} TL) — TL/puan SECILIYE gore:")
    print(f"    {'':2}{'TL':>9}{'kolon':>7}  {'sekil':<11}{'P(hedef)':>9}"
          f"{'TL/puan':>10}")
    for x in adimlar:
        marj = ""
        if secili is not None and x.p_hedef != secili.p_hedef:
            marj = f"{(x.tl - secili.tl) / (x.p_hedef - secili.p_hedef) / 100:,.0f}"
        im = "->" if x.kolon == secili_kolon else "  "
        print(f"    {im:2}{x.tl:>9,.0f}{x.kolon:>7}  {x.sekil:<11}"
              f"{x.p_hedef:>9.4f}{marj:>10}")


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
| garanti | **{garanti}** → kaçak eşiği `k ≤ {kacak_esigi()}`, hedef `P(en iyi kolon ≥ 12)` |
| bütçe | {butce:,.0f} TL ({butce / 10:,.0f} kolon) |
| bedel | ₺10/kolon — ölçülmüş (`getiri.KOLON_BEDELI`) |
| ödül | **garanti tabanı**: `k` kaçakta **bir** kolon `{garanti}−k` kademesinde. **Alt sınır** — gerçekleşen getiri bundan büyüktür |
| ödeyen olay | `k = 0` → {garanti}. kademe. `P(k≤{kacak_esigi()})` bunu `k = 1`'le **topluyor** ve o kademe maliyeti karşılamıyor — bkz. başabaş sütunu |
| rakip kolon | {RAKIP_KOLON:,} — varsayım (`karne.RAKIP_KOLON`); `E[TL]` buna `1/(N·q)` mertebesinde duyarlı |

## Haftalar

| hf | şekil | kolon | maliyet | P(k≤{kacak_esigi()}) | **P(k=0)** | E[TL] | kaçak | kademe | **başabaş k** | ödül | net | fiyat ölçeği |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"""]
    for r in rows:
        sekil = f"{r['banko']}b/{r['cift']}ç/{r['uclu']}ü"
        bb = r.get("basabas_kacak")
        p.append(
            f"| {r['hafta']} | {sekil} | {r['kolon']} | {_tl(r['maliyet'])} | "
            f"{r['p_hedef']:.3f} | **{r['p_kacak_sifir']:.3f}** | "
            f"{_tl(r.get('beklenen_tl'))} | "
            f"{r.get('kacak', '—')} | {r.get('kademe', '—')} | "
            f"{bb if bb is not None else ('—' if 'kacak' not in r else 'hiçbiri')} | "
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
karşılaştırmayı engeller: ilk haftalarda ana fiyat ~%17 marjlı iddaa
oranıydı, sonra ~%3,4 marjlı Pinnacle'a geçildi. Sütun bunu her satırda
söylüyor — ama **ilan etmek karşılaştırmayı geçerli kılmıyor** (§3.63).

**Ve bu kayıt, kıyaslandığı geri testle de aynı ölçekte değil.** 114
haftalık geri test `Avg` kapanışla (marj %7,26) koşuyor, yani ortada
**üç** ölçek var. Düzeltilemez de: 2026/27'nin oran arşivi bugün boş,
canlı haftalar `Avg` ölçeğinde yeniden türetilemiyor. Geçersiz olan
karşılaştırmalar açıkça şunlar: canlı `P(k≤{kacak_esigi()})` ↔ geri
testin ortalaması, ve ölçeğin değiştiği yerde canlı haftaların
olasılıkları **birbiriyle**. Geçerli kalanlar sonuçtan gelenlerdir —
kaçak, kademe, ödül; onlar fiyattan bağımsızdır.

**Ödül sütunu alt sınırdır.** {r['kolon']} kolonluk bir {garanti}-garanti
sistemi, garantinin söylediği tek kolondan fazlasını da tutturur; karne
onları saymaz çünkü kolon listesi bizde değil (şekle biz karar veriyoruz,
kolonları satıcı üretiyor). Gerçekleşen getiri bu tablodan **büyüktür**.

**`P(k≤{kacak_esigi()})` bir kapsama ölçüsüdür, kâr ölçüsü değildir.**
Manşet olasılık iki farklı olayı topluyor ve biri para kaybettiriyor:
`k=0` {garanti}. kademeyi verir, `k=1` {garanti - 1}. kademeyi. Karnenin
kendi kaydı bunu iki kez yazdı — 2. ve 3. hafta 12 tutturdu ve ikisi de
zarar etti. Ödeyen olayın olasılığı `P(k=0)` sütununda ve manşetin
**dörtte biri ile beşte biri** arasında. **Başabaş k** sütunu her haftanın
KENDİ ikramiye tablosundan türetiliyor (medyan alınmıyor: nominal TL dört
sezonda 72 kat büyümüş), ve o sütun sabit değil — 1. haftada `k=1` bile
maliyeti karşılardı, 2. ve 3. haftada yalnızca `k=0`.

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
              f"{kacak_esigi()})")
        print(f"  sekil         : {r['banko']} banko · {r['cift']} cifte · "
              f"{r['uclu']} uclu")
        print(f"  bedel         : {r['kolon']} kolon = {r['maliyet']:,.0f} TL")
        print(f"  P(hedef)      : {r['p_hedef']:.4f}   "
              f"(k <= {kacak_esigi()}; KAPSAMA olcusu)")
        print(f"  P(kacak=0)    : {r['p_kacak_sifir']:.4f}   "
              f"(ODEYEN olay: {a.garanti}. kademe)")
        if r["beklenen_tl"] is not None:
            print(f"  E[TL]         : {r['beklenen_tl']:,.2f}  "
                  f"(rakip {RAKIP_KOLON:,} kolon VARSAYIMIYLA)")
        print("\n  kupon:")
        for i, x in enumerate(r["picks"], 1):
            print(f"    {i:>2}. {x}")

        h = canli_hafta(sezon, hafta)
        if h:
            _merdiven(h["probs"], a.garanti, r["kolon"])

        # Kalabalik ayari AYRI gosterilir, varsayilan DEGIL: olculdugunde
        # makul her kisitta kazanci sifir cikti (docs Faz B).
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
