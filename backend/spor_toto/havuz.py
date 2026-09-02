"""Havuz — resmî ikramiye tablosundan dağıtılan havuzu ve devri geri hesaplar.

`docs/VERI_TOPLAMA_VE_ISLEME.md` §6D resmî arşivi kurdu: 6 sezon, 225 hafta,
223'ünde kademe başına kazanan adedi ve kişi başı ikramiye. Ama §8 madde 10 ve
§10.1 şunu yazıyordu:

    Havuzun kendisi (haftalık hasılat) uçta yok; yalnızca kademe başına
    kazanan adedi ve kişi başı ikramiye var.

**Bu, olduğundan karamsardı.** Kademe havuzu `kazanan × kişi_başı`dır ve
kademeler arası oran sabit çıkıyor — yani tablonun kendisi havuzu taşıyor,
sadece açıkça yazmıyor.

─── Ölçülen bölüşüm: 35 / 20 / 20 / 25 ───────────────────────────────────

Havuzu hesaplanabilen **222 haftada**:

| Oran | Beklenen | Sonuç |
|---|---|---|
| 14 ÷ 13 | 1,00 | 218 haftanın **214'ünde birebir**; kalan 4'ü binde birin altında |
| 12 ÷ 13 | 1,25 | ortanca **tam 1,2500** |
| 15 ÷ 13 | 1,75 | 176 haftanın **135'inde tam**, hiçbirinde **altında değil** |

Bölüşüm sabit bir kuraldır ve `BOLUSUM` sabitinde durur.

─── Devir 15'e özgü DEĞİLDİR ─────────────────────────────────────────────

İlk yazım yalnızca 15'i devirli sayıyordu ve 10 haftayı "bölüşüm bozuk" diye
işaretliyordu. Veri aksini gösterdi: **kazanansız kalan HER kademe** payını
ileri taşır ve ertesi hafta **aynı kademe** fazlasıyla döner.

| Hafta | Kazanansız kademe | Ertesi hafta o kademe ÷ birim |
|---|---|---|
| 2021/22 hf 47 → 48 | 15 ve 14 | **1,58** |
| 2022/23 hf 28 → 29 | 15 ve 14 | **1,03** |
| 2025/26 hf 7 → 8   | 15 ve 14 | **1,67** |
| 2025/26 hf 45 → 46 | 15 ve 14 | **1,59** |

Model genelleştirilince açıklanamayan hafta **10'dan 2'ye** düştü: 222
haftanın **220'si** kurala birebir oturuyor.

─── Zincir kapanıyor — modelin en güçlü kanıtı ───────────────────────────

`devir_zinciri()` şunu ölçer: bir hafta devrettiyse, taşınan tutar ertesi
haftanın aldığı devre eşit mi?

    devreden hafta ardından devir alan hafta : 41
    gelen ÷ giden oranı: ortanca **1,000**
    birebir eşit (%2 içinde)                : **36 / 41**

Kalan 5'i ardışık devirdir (iki hafta üst üste kazanansız kapanır, üçüncüde
ikisi birden dağıtılır) ve oran 1'in üstüne çıkar — 1'in **altına** hiç
inmez, ki devrin ancak ekleyebileceğiyle tutarlıdır.

**Bağımsız doğrulama.** 2026/27 2. hafta için hesap **42.842.867,18 TL**
veriyor. Elle girilen kayıt (§6B — ayrı köken sınıfı, ekran görüntüsünden)
notunda şunu yazıyor:

    "15 kademesinin havuzu 1. haftadan devreden 30.149.380,57 TL'yi İÇERİR;
     haftanın kendi payı 42.842.867,72 TL'dir."

Fark **0,54 TL** — 42,8 milyonda, yani milyonda 0,013. Bu, 14-kademesinin
kendi kuruş yuvarlaması payının (±0,61 TL) içindedir; yani iki kaynak
ölçüm hassasiyeti sınırında aynı sayıya varıyor.

> **Bu satır bir kez fazla iddialı yazılmıştı.** Önce "kuruşuna kadar aynı"
> deniyordu ve o zamanki birim 13-kademesiydi: hata 33,12 TL'ydi, sıfır
> değil. `_birim` hassaslaştırılınca 0,54 TL'ye indi — ama "kuruşuna kadar"
> hâlâ yanlış olurdu. Ölçülen sayı ne ise o yazılır.

─── Neyi HÂLÂ vermiyor ───────────────────────────────────────────────────

**Brüt hasılat değil, DAĞITILAN havuz.** Aradaki fark Spor Toto'nun payıdır
ve oranı bu veriden çıkarılamaz. Bu yüzden modül her yerde `dagitilan` der;
"hasılat" demez.

**Kazananlar kolon sayısıdır, bilet değil** (§3.40). Bu modül o ayrımı
çözmez; çözülmesi gereken yerde (`faz_b`) uyarı olarak taşınır.

**Açıklanamayan 2 hafta düzeltilmez, işaretlenir** (doktrin 4): 2024/25 hf 43
ve 2025/26 hf 10, ikisinde de 12-kademesi beklenenin ALTINDA — devir ancak
şişirebileceği için bu bir devir değil, gerçek bir sapmadır.
"""
from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_DIZIN = KOK / "data" / "sportoto_arsiv"

#: Kademe bölüşümü — ÖLÇÜLDÜ, varsayılmadı (modül başlığındaki tablo).
#: 13 kademesi 1 birim kabul edilir; ötekiler ona oranlanır.
BOLUSUM: dict[int, float] = {15: 1.75, 14: 1.0, 13: 1.0, 12: 1.25}

#: Bölüşümün yüzde karşılığı. Toplam 5,0 birim: 1,75+1+1+1,25.
YUZDE: dict[int, float] = {k: v / sum(BOLUSUM.values()) for k, v in BOLUSUM.items()}

#: Kuruş yuvarlamasindan gelen sapma payı. Ölçülen en büyük sapma binde 2'ydi
#: (14÷13 için %95 dilimi 1,0002); eşik onun bir mertebe üstünde tutuldu ki
#: yuvarlama gürültüsü "bölüşüm bozuldu" diye raporlanmasın.
#: Hem yuvarlama gürültüsünün payı hem de **devir eşiği** — tek sayı.
#:
#: Devir eşiği MUTLAK DEĞİL GÖRELİDİR. İlk yazımda 1 TL mutlak eşik
#: kullanılmıştı ve **yanlıştı**: kişi başı ikramiye kuruşa yuvarlanıp on
#: binlerce kazananla çarpılınca yuvarlama hatası binlerce TL'ye çıkıyor,
#: dolayısıyla 176 haftanın 174'ü "devirli" görünüyordu. Ölçüm ayrımı
#: nettir ve iki küme arasında üç mertebe boşluk var: gürültünün en büyüğü
#: `birim`in **1,01e-3**'ü, gerçek devrin en küçüğü **4,82e-2**'si. 0,005
#: tam ortadaki boşluğa düşer ve 41 hafta verir.
#:
#: Burada ayrıca `DEVIR_PAYI = SAPMA_PAYI` diye bir **takma ad** duruyordu
#: ve hiçbir yerde okunmuyordu (kod her iki yerde de `SAPMA_PAYI`
#: kullanıyor). İki adı olan tek sayı, ayrışacak iki sayıya davetiyedir.
SAPMA_PAYI = 0.005


def _kademe_havuzlari(payout: dict[str, Any]) -> dict[int, float]:
    """Kademe -> o kademeye dağıtılan toplam (kazanan × kişi başı).

    Kazananı ya da ödülü olmayan kademe **atlanır**; sıfır sayılmaz.
    "Kimse bilemedi" ile "veri yok" ayrı şeylerdir ve ikisini karıştırmak
    bölüşüm oranını sessizce bozar.
    """
    out: dict[int, float] = {}
    for kat in payout.get("tiers") or []:
        kazanan, odul = kat.get("winners"), kat.get("prize")
        if kazanan is None or odul is None:
            continue
        out[int(kat["correct"])] = float(kazanan) * float(odul)
    return out


def _birim(kademeler: dict[int, float],
           kazananlar: dict[int, int] | None = None) -> float | None:
    """Bölüşümün 1 birimi — 13 ve 14 kademelerinden hangisi TEMİZ ve HASSAS ise.

    13 ve 14 aynı payı (%20) alır, dolayısıyla ikisi de birim adayıdır. Seçim
    iki kurala göre yapılır ve ikisi de ölçümden geldi:

    **1. Devir ancak ŞİŞİRİR.** Kazanansız kalan kademe payını ileri taşır ve
    ertesi hafta fazlasıyla döner. İki aday belirgin biçimde ayrışıyorsa
    büyük olan devir almıştır; **küçüğü** temiz olandır.

    **2. Kuruş yuvarlaması KAZANAN SAYISIYLA büyür.** Kademe havuzu
    `kazanan × kişi_başı`dır ve kişi başı kuruşa yuvarlanmıştır; hata
    ±0,005 × kazanan kadardır. İki aday uyuşuyorsa **kazananı az olan**
    daha hassas ölçüdür.

    Somut örnek — 2026/27 2. hafta:

        13. kademe: 2077 × 11.787,01 = 24.481.619,77   (yuvarlama ±10,39 TL)
        14. kademe:  121 × 202.327,59 = 24.481.638,39  (yuvarlama  ±0,61 TL)

    İkisi 18,62 TL ayrışıyor — yani ikisi de "doğru", ama 14 çok daha
    keskin. 1,75 × 14-birim haftanın kendi payını **0,54 TL** hatayla verir;
    13-birim ile hata 33,12 TL olurdu.
    """
    adaylar = {k: kademeler[k] for k in (13, 14) if kademeler.get(k, 0) > 0}
    if not adaylar:
        return None
    if len(adaylar) == 1:
        return next(iter(adaylar.values()))

    kucuk, buyuk = sorted(adaylar.values())
    if buyuk - kucuk > SAPMA_PAYI * kucuk:
        return kucuk  # biri devir almış — temiz olan küçüğü

    if not kazananlar:
        return kucuk
    # Uyuşuyorlar: kazananı az olan daha az yuvarlama hatası taşır.
    return adaylar[min(adaylar, key=lambda k: kazananlar.get(k, 0))]


def _kazananlar(payout: dict[str, Any]) -> dict[int, int]:
    """Kademe -> kazanan adedi. `_birim`in hassasiyet kuralı buna dayanır."""
    return {int(k["correct"]): int(k["winners"]) for k in payout.get("tiers") or []
            if k.get("winners") is not None}


def hafta_havuzu(payout: dict[str, Any] | None) -> dict[str, Any] | None:
    """Bir haftanın ikramiye tablosundan havuz ve devir. Hesaplanamazsa None.

    Çıkan sözlük:

        birim         bölüşümün 1 birimi (bkz. `_birim`)
        dagitilan     haftanın kendi payı — GELEN devir hariç
        devir_gelen   önceki haftalardan gelip bu hafta dağıtılan tutar
        devreden      bu hafta kazanansız kalıp İLERİ taşınan kademeler
        devir_giden   onların toplamı (ALT sınır, bkz. aşağıda)
        toplam        kademelerin toplamı (ekrandaki dağıtım)
        kademeler     kademe -> dağıtılan
        bolusum_tutuyor / sapmalar

    **Devir 15'e özgü değildir.** İlk yazım yalnızca 15'i devirli sayıyordu;
    veri aksini gösterdi. Ölçülen desen şudur: bir kademe kazanansız
    kapandığında (havuzu 0) payı ileri gider ve **ertesi hafta AYNI kademe**
    fazlasıyla döner. Dört örnek çifti:

    | Hafta | Kazanansız | Ertesi hafta o kademe |
    |---|---|---|
    | 2021/22 hf 47 → 48 | 15 ve 14 | 14 ÷ birim = **1,58** |
    | 2022/23 hf 28 → 29 | 15 ve 14 | 14 ÷ birim = **1,03** |
    | 2025/26 hf 7 → 8   | 15 ve 14 | 14 ÷ birim = **1,67** |
    | 2025/26 hf 45 → 46 | 15 ve 14 | 14 ÷ birim = **1,59** |

    **`devir_giden` bir ALT sınırdır, kesin tutar değildir.** İleri taşınan
    şey o haftanın kendi payı *artı* önceden birikmiş olandır; ikincisi bu
    haftanın tablosunda görünmez. Doktrin 2 gereği tahmin edilmez —
    `devir_giden_kesin: False` alanı bunu her kayıtta yazar.
    """
    if not payout:
        return None
    kademeler = _kademe_havuzlari(payout)
    birim = _birim(kademeler, _kazananlar(payout))
    if not birim or birim <= 0:
        return None

    tolerans = SAPMA_PAYI * birim
    sapmalar: dict[int, tuple[float, float]] = {}
    devir_gelen = 0.0
    devreden: list[int] = []
    devir_giden = 0.0

    for kademe, pay in BOLUSUM.items():
        havuz = kademeler.get(kademe)
        if havuz is None:
            continue  # tabloda hiç yok — sapma değil, veri yok
        beklenen = pay * birim
        if havuz <= 0:
            # Kazanan yok: bu kademenin payı DAGITILMADI, ileri devretti.
            devreden.append(kademe)
            devir_giden += beklenen
        elif havuz - beklenen > tolerans:
            devir_gelen += havuz - beklenen
        elif beklenen - havuz > tolerans:
            # Beklenenin ALTI: devir ancak şişirir, düşüremez. Bu yüzden
            # burası bir devir değil, gerçek bir sapmadır ve yutulmaz.
            sapmalar[kademe] = (round(havuz / birim, 4), pay)

    toplam = sum(kademeler.values())
    return {
        "birim": birim,
        "dagitilan": toplam - devir_gelen,
        "devir_gelen": devir_gelen,
        "devreden": sorted(devreden, reverse=True),
        "devir_giden": devir_giden,
        "devir_giden_kesin": False,
        "toplam": toplam,
        "kademeler": kademeler,
        "bolusum_tutuyor": not sapmalar,
        "sapmalar": sapmalar,
    }


def arsiv_haftalari(dizin: Path | None = None) -> list[dict[str, Any]]:
    """Resmî arşivin tüm sezonlarını tek listede döndürür, kronolojik.

    Her satır arşivdeki hafta kaydına `havuz` anahtarını ekler; ikramiyesi
    olmayan haftada `havuz` None'dır ve satır **elenmez** — hafta vardır,
    yalnızca ikramiyesi ilan edilmemiştir.
    """
    kok = dizin or VARSAYILAN_DIZIN
    out: list[dict[str, Any]] = []
    for yol in sorted(kok.glob("*.json")):
        if yol.name == "arsiv_rapor.json":
            continue
        govde = json.loads(yol.read_text(encoding="utf-8"))
        for hafta in govde["weeks"]:
            kayit = dict(hafta)
            kayit["season_key"] = govde["meta"]["season_key"]
            kayit["havuz"] = hafta_havuzu(hafta.get("payout"))
            out.append(kayit)
    out.sort(key=lambda h: (h["season_key"], h["week"] is None, h["week"] or 0))
    return out


def devir_zinciri(dizin: Path | None = None) -> dict[str, Any]:
    """Devreden hafta ile ertesi haftanın aldığı devri karşılaştırır.

    Modelin en güçlü kanıtı budur ve **bağımsızdır**: bölüşüm oranları tek
    bir haftanın içinden okunur, zincir ise ardışık iki haftayı birbirine
    bağlar. İkisi aynı sayıya varıyorsa model yalnızca bir eğri uydurması
    değildir.

    `oran > 1` ardışık devirdir (üst üste kazanansız kapanan haftalar);
    `oran < 1` görülürse model yanlıştır, çünkü devir ancak ekleyebilir.
    """
    haftalar = [h for h in arsiv_haftalari(dizin) if h["havuz"]]
    eslesme: list[dict[str, Any]] = []
    kacan: list[dict[str, Any]] = []
    for once, sonra in pairwise(haftalar):
        if once["season_key"] != sonra["season_key"]:
            continue
        giden = once["havuz"]["devir_giden"]
        if giden <= 0:
            continue
        gelen = sonra["havuz"]["devir_gelen"]
        kayit = {"season_key": once["season_key"], "week": once["week"],
                 "giden": giden, "gelen": gelen}
        # Ertesi hafta da devrettiyse devir görünmez; bu bir kaçak değil,
        # zincirin uzamasidir ve ayri sayilir.
        (eslesme if gelen > 0 else kacan).append(kayit)

    oranlar = sorted(k["gelen"] / k["giden"] for k in eslesme)
    birebir = sum(1 for o in oranlar if abs(o - 1.0) <= 0.02)
    return {
        "eslesen": len(eslesme),
        "ertesi_hafta_da_devretti": len(kacan),
        "birebir": birebir,
        "oran_min": round(oranlar[0], 4) if oranlar else None,
        "oran_ortanca": round(oranlar[len(oranlar) // 2], 4) if oranlar else None,
        "oran_maks": round(oranlar[-1], 4) if oranlar else None,
        "birin_altina_dusen": sum(1 for o in oranlar if o < 0.98),
    }


def havuz_ozeti(dizin: Path | None = None) -> dict[str, Any]:
    """Arşivin tamamı için havuz özeti — `/api` ve raporların tek kaynağı."""
    haftalar = arsiv_haftalari(dizin)
    havuzlu = [h for h in haftalar if h["havuz"]]
    devir_alan = [h for h in havuzlu if h["havuz"]["devir_gelen"] > 0]
    devreden = [h for h in havuzlu if h["havuz"]["devreden"]]
    bozuk = [h for h in havuzlu if not h["havuz"]["bolusum_tutuyor"]]

    dagitimlar = sorted(h["havuz"]["dagitilan"] for h in havuzlu)
    sezonlar: dict[str, dict[str, Any]] = {}
    for h in havuzlu:
        s = sezonlar.setdefault(h["season_key"], {"hafta": 0, "dagitilan": 0.0,
                                                  "devir": 0.0})
        s["hafta"] += 1
        s["dagitilan"] += h["havuz"]["dagitilan"]
        s["devir"] += h["havuz"]["devir_gelen"]

    return {
        "hafta": len(haftalar),
        "havuz_hesaplanan": len(havuzlu),
        "devir_alan_hafta": len(devir_alan),
        "devreden_hafta": len(devreden),
        "bolusum_bozuk_hafta": len(bozuk),
        "bolusum": dict(BOLUSUM),
        "bolusum_yuzde": {k: round(100 * v, 2) for k, v in YUZDE.items()},
        "dagitilan_ortanca": dagitimlar[len(dagitimlar) // 2] if dagitimlar else None,
        "sezonlar": {k: {"hafta": v["hafta"],
                         "dagitilan": round(v["dagitilan"], 2),
                         "devir": round(v["devir"], 2)}
                     for k, v in sorted(sezonlar.items())},
        "sinir": (
            "DAGITILAN havuzdur, brut hasilat DEGILDIR — Spor Toto'nun payi bu "
            "veriden cikarilamaz. Ayrica kazananlar KOLON sayisidir, bilet degil "
            "(docs/VERI_TOPLAMA_VE_ISLEME.md §3.40)."
        ),
    }


def _main() -> int:
    """`python -m spor_toto.havuz` — arşivin havuz özetini basar."""
    ozet = havuz_ozeti()
    print("=" * 78)
    print("HAVUZ — resmî ikramiye tablosundan geri hesap")
    print("=" * 78)
    print(f"hafta                 : {ozet['hafta']}")
    print(f"havuzu hesaplanan     : {ozet['havuz_hesaplanan']}")
    print(f"devir ALAN hafta      : {ozet['devir_alan_hafta']}")
    print(f"DEVREDEN hafta       : {ozet['devreden_hafta']}"
          "  (bir kademe kazanansız kapandı)")
    print(f"bölüşümü bozuk hafta  : {ozet['bolusum_bozuk_hafta']}")
    print("bölüşüm (15/14/13/12) : "
          + " · ".join(f"%{ozet['bolusum_yuzde'][k]:g}" for k in (15, 14, 13, 12)))
    if ozet["dagitilan_ortanca"]:
        print(f"dağıtılan (ortanca)   : {ozet['dagitilan_ortanca']:,.2f} TL")
    print("\n sezon      hafta        dağıtılan              devir")
    for anahtar, s in ozet["sezonlar"].items():
        print(f"  {anahtar:<9} {s['hafta']:>5}  {s['dagitilan']:>18,.2f} "
              f"{s['devir']:>18,.2f}")
    z = devir_zinciri()
    print(f"\ndevir zinciri: {z['birebir']}/{z['eslesen']} hafta birebir "
          f"(oran ortanca {z['oran_ortanca']}, maks {z['oran_maks']}); "
          f"1'in altina dusen {z['birin_altina_dusen']}")
    print(f"\nSINIR: {ozet['sinir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
