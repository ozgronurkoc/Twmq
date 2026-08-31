"""Sürpriz ekseni — kupon haftasının sürprizi ve onun HAVUZDAKİ karşılığı.

Bu modül deponun on beş kez ölçtüğü şeyi bir kez daha ölçmüyor. §5.1'in
tablosu nettir ve tekrar edilmesi gerekmiyor:

    Handikap + alt/üst → türetilmiş 1X2   −0,000063 [−0,000287, +0,000155]
    Çizgi hareketi (açılış→kapanış)       kapanış verimli, artık YOK
    Bahisçi anlaşmazlığı                  ham sinyal yok, favori gücüyle karışık
    Elo · Dixon-Coles · H2H · form · ağaç hepsi geçmedi

Yani **hangi maçın sürpriz olacağı** kapanış fiyatından daha iyi bilinemiyor.
Bu modül o soruyu sormuyor. Sorduğu soru şu:

    Sürprizin kendisi, MÜŞTEREK havuzda ne kadar ediyor?

Ayrım `getiri.py`'nin docstring'inde zaten yazılı ve deponun en önemli tek
ayrımıdır::

    Sabit oranlı :  edge = p_model  − p_piyasa      ← 15 kez denendi, yok
    Müşterek     :  edge = p_piyasa − oynanma_payı  ← ölçülmemişti

İkincisinde piyasayı yenmek **gerekmiyor**. Piyasa olasılığını olduğu gibi
alıp yalnızca kalabalığın ondan saptığı yeri işaretlemek yetiyor. `getiri.py`
bunu biliyordu ama ölçemiyordu; kendi §6.3b notu *"elde 1 ikramiyeli hafta
var, ≈71 gerekiyor"* diyordu.

─── O engel kalktı ve kimse fark etmemişti ──────────────────────────────

Üç veri seti birbirinden bağımsız büyüdü ve kesişimleri hiç alınmamıştı:

    resmî arşiv       223 ikramiye tablosu   (`havuz.arsiv_haftalari`)
    oran arşivi       4 sezon · 2.283 maç    (`odds.load_odds`)
    kupon dizisi      oran arşivinin `code` sütunu

Üçünün kesişimi **119 hafta**. `getiri`nin beklediği 71 haftanın üstünde.

─── Birleştirme SESSİZCE bozulabilirdi — bu yüzden denetleniyor ─────────

İki arşivin hafta numaraları farklı kökenden gelir: resmî arşiv Spor Toto'nun
kendi `GameRound`'undan, oran arşivi bültenden/football-data'dan. Numaralar
kayarsa haftanın ikramiyesi **başka bir haftanın sonucuna** yapışır ve
hiçbir sayı hata vermez — sadece hepsi yanlış olur. §5.6'daki v1 sıra hatası
tam olarak böyle aylarca görünmedi.

Bu yüzden her birleştirme `close_date` ile denetlenir. Resmî `close_date`
**kupon kapanışıdır** ve ölçülmüştür (`build_sportoto_arsiv.py` notu):
2025/26'nın 41 haftasının 41'inde haftanın **ilk** maçının gününe eşit.
Denetim bunu kullanır: oran arşivindeki en erken `kickoff` ile resmî
`close_date` arasındaki fark 1 günü geçerse hafta **elenir** ve elenme
`denetim` bloğunda görünür.

Bugünkü ölçüm: 119 haftanın **119'u** geçiyor, sapan yok.

─── İki sürpriz tanımı, ve niçin ikisi de taşınıyor ─────────────────────

`surpriz`      favori kazanmadı (beraberlik DAHİL)   — ortalama 6,38/15
`ger_surpriz`  favorinin karşı tarafı kazandı        — ortalama 2,73/15

İkincisi `odds.py`'nin zaten kullandığı tanımdır (§5.4, "gerçek sürpriz").
Birincisi kuponun gördüğü şeydir: kolon açısından beraberlik de bir kayıptır.
Havuzla ilişkisi ölçüldüğünde **birincisi daha güçlü** çıkıyor (ρ = −0,74'e
karşı −0,48) ve sebebi mekaniktir — kalabalık beraberliği de eksik oynuyor.

─── Bantlar ölçüm sonucuna göre seçilMEDİ ───────────────────────────────

`SURPRIZ_BANTLARI` kaba ve okunabilirlik için, ölçülen ortalamanın (6,38)
etrafında yuvarlak sayılarla seçildi. Yine de bir bant tablosu her zaman
"bandı sonuca göre seçtin" itirazına açıktır; bu yüzden **manşet sayı bant
kullanmıyor**: `kalabalik.py`'nin τ'su sürekli log-olasılık üzerinden
uyduruluyor ve bu modülün bantlarını hiç görmüyor.

Sonucu okumak için: `python -m spor_toto.surpriz`.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from functools import lru_cache
from typing import Any

from .havuz import arsiv_haftalari
from .odds import ODDS_DIZIN, load_odds, match_1x2

#: Kupon maçı sayısı. Oranı eksik hafta (milli maç arası) ölçüme girmez:
#: 13 maçın sürprizini 15 maçın ikramiyesiyle karşılaştırmak, eksik iki maçı
#: sessizce "sürpriz değil" saymak demektir.
KUPON_MACI = 15

#: Birleştirme denetiminin toleransı, gün. `close_date` kupon kapanışıdır ve
#: haftanın ilk maçının gününe eşit ölçüldü; 1 gün payı saat dilimi ve
#: gece yarısını geçen maçlar içindir.
GUN_TOLERANSI = 1

#: Sürpriz sayısı bantları (alt dahil, üst hariç). Ölçülen ortalama 6,38 ve
#: kenarlar onun etrafında YUVARLAK sayılarla seçildi — sonuca bakılarak
#: değil. Manşet sayı (`kalabalik.tau`) bu bantları kullanmaz.
SURPRIZ_BANTLARI: Sequence[tuple[int, int]] = ((0, 5), (5, 7), (7, 9), (9, 16))

#: Bir bandın tabloya çıkması için gereken en az hafta. Altında ortanca kendi
#: gürültüsünü ölçer. `bahisci.py`'deki hücre eşiğiyle aynı gerekçe.
ASGARI_HAFTA = 3


def sezonlar() -> list[str]:
    """Oran arşivi olan sezonlar — sürpriz ekseninin kesiti bunlarla sınırlı.

    Kesiti belirleyen resmî arşiv değil oran arşividir: ikramiye tablosu 6
    sezon taşıyor ama favoriyi tanımlayan fiyat 4 sezonda var. Favorisi
    olmayan haftada "sürpriz" tanımsızdır.
    """
    return sorted(p.stem[len("odds_"):] for p in ODDS_DIZIN.glob("odds_*.csv"))


def _arsiv_haritasi() -> dict[tuple[str, int], dict[str, Any]]:
    return {(h["season_key"], h["week"]): h
            for h in arsiv_haftalari()
            if h.get("week") is not None and h.get("payout")}


def _gun_farki(a: str | None, b: str | None) -> int | None:
    """İki ISO tarihi arasındaki mutlak gün farkı; biri okunamazsa None.

    Okunamayan tarih `None` döner, **0 değil**: 0 dönseydi bozuk tarihli bir
    hafta "tam eşleşti" sayılır ve denetim tam olarak kaçırması gereken şeyi
    kaçırırdı.
    """
    if a is None or b is None:
        return None
    try:
        return abs((date.fromisoformat(a[:10])
                    - date.fromisoformat(b[:10])).days)
    except ValueError:
        return None


@lru_cache(maxsize=8)
def hafta_kayitlari(sezon: str | None = None) -> tuple[list[dict[str, Any]],
                                                       dict[str, Any]]:
    """Üç arşivin kesişimi: (kayıtlar, denetim).

    Önbellekli ve `load_odds` ile **aynı sözleşmede**: dönen yapı okunmak
    içindir, değiştirilmez. Aynı gövde bir istekte iki kez isteniyor
    (betimleyici özet + τ uyumu) ve birleştirme her seferinde baştan
    kurulsaydı uç iki kat yavaşlardı.

    Her kayıt bir kupon haftasıdır ve şunları taşır:

    ``maclar``      15 maçın ``(probs, code)`` çifti — kalabalık modelinin girdisi
    ``surpriz``     favori kazanmadı (beraberlik dahil)
    ``ger_surpriz`` favorinin karşı tarafı kazandı
    ``logp``        Σ ln p_piyasa(gerçek sonuç) — haftanın "sürprizliği", sürekli
    ``kazanan``     kademe → kazanan kolon adedi (resmî)
    ``odul``        kademe → kişi başı ikramiye, TL (resmî)

    `denetim` elenen her haftayı ve sebebini taşır. Sessiz eleme yok: bir
    hafta ölçümden düştüyse **niçin** düştüğü gövdede yazar.
    """
    ars = _arsiv_haritasi()
    kayitlar: list[dict[str, Any]] = []
    elenen: list[dict[str, Any]] = []

    for s in ([sezon] if sezon else sezonlar()):
        haftalar: dict[int, list[dict[str, Any]]] = {}
        for r in load_odds(sezon=s):
            haftalar.setdefault(r["week"], []).append(r)

        for w, satirlar in sorted(haftalar.items()):
            bloklar = [(b, r) for b, r in
                       ((match_1x2(r), r) for r in satirlar) if b]
            if len(bloklar) < KUPON_MACI:
                elenen.append({"sezon": s, "hafta": w, "sebep": "oran eksik",
                               "ayrinti": f"{len(bloklar)}/{KUPON_MACI} maç"})
                continue

            resmi = ars.get((s, w))
            if resmi is None:
                elenen.append({"sezon": s, "hafta": w,
                               "sebep": "resmî ikramiye tablosu yok",
                               "ayrinti": ""})
                continue

            ilk = min(r["kickoff"] for _, r in bloklar if r.get("kickoff"))
            fark = _gun_farki(ilk, resmi.get("close_date"))
            if fark is None or fark > GUN_TOLERANSI:
                elenen.append({
                    "sezon": s, "hafta": w, "sebep": "tarih tutmadı",
                    "ayrinti": f"ilk maç {ilk[:10]} ↔ kupon kapanışı "
                               f"{(resmi.get('close_date') or '?')[:10]}"})
                continue

            kademeler = {t["correct"]: t for t in resmi["payout"]["tiers"]}
            if not all(k in kademeler for k in (15, 14, 13, 12)):
                elenen.append({"sezon": s, "hafta": w,
                               "sebep": "ikramiye tablosu eksik kademeli",
                               "ayrinti": str(sorted(kademeler))})
                continue

            surpriz = ger_surpriz = 0
            logp = 0.0
            maclar = []
            for b, r in bloklar:
                kod = r["code"]
                if b["favourite"] != kod:
                    surpriz += 1
                    if kod != "0":
                        ger_surpriz += 1
                logp += math.log(max(b["probs"][kod], 1e-6))
                maclar.append({"probs": b["probs"], "code": kod,
                               "favourite": b["favourite"]})

            kayitlar.append({
                "sezon": s,
                "hafta": w,
                "maclar": maclar,
                "surpriz": surpriz,
                "ger_surpriz": ger_surpriz,
                "logp": logp,
                "ort_logp": logp / len(maclar),
                "kazanan": {k: kademeler[k]["winners"] for k in (15, 14, 13, 12)},
                "odul": {k: kademeler[k]["prize"] for k in (15, 14, 13, 12)},
                # 12 kademesi hiç kazanansız kalmıyor ve devir almıyor; kademe
                # havuzu bu yüzden haftanın SATIŞ hacminin en temiz vekili.
                "hacim": kademeler[12]["winners"] * kademeler[12]["prize"],
            })

    denetim = {
        "kesit": len(kayitlar),
        "elenen": len(elenen),
        "elenenler": elenen,
        "tarih_toleransi_gun": GUN_TOLERANSI,
        "not": ("Hafta numaraları iki AYRI kökenden gelir (resmî GameRound ↔ "
                "bülten/football-data). Kayarlarsa ikramiye başka bir haftanın "
                "sonucuna yapışır ve hiçbir sayı hata vermez. Denetim bu "
                "yüzden tarih üzerinden yapılır, numaraya güvenilmez."),
    }
    return kayitlar, denetim


# ─── betimleyici ölçüm ───────────────────────────────────────────────────

def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Sıra korelasyonu, bağlı sıralar ortalanarak. n < 3 ise None.

    Pearson değil Spearman: kazanan adedi kademeler arasında büyüklük olarak
    yüzlerce kat değişiyor ve doğrusal bir katsayı tek bir devasa haftayı
    ölçüyor olurdu.
    """
    n = len(xs)
    if n < 3 or n != len(ys):
        return None

    def sira(v: Sequence[float]) -> list[float]:
        duzen = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[duzen[j + 1]] == v[duzen[i]]:
                j += 1
            ortalama = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[duzen[k]] = ortalama
            i = j + 1
        return r

    rx, ry = sira(xs), sira(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    pay = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    payda = math.sqrt(sum((a - mx) ** 2 for a in rx)
                      * sum((b - my) ** 2 for b in ry))
    return round(pay / payda, 4) if payda else None


def _ortanca(v: Sequence[float]) -> float:
    s = sorted(v)
    n = len(s)
    if not n:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def bant_tablosu(kayitlar: Sequence[dict[str, Any]],
                 alan: str = "surpriz") -> list[dict[str, Any]]:
    """Sürpriz bandı → kazanan adedi ve kişi başı ikramiye (ortanca).

    **Ortalama değil ortanca**: 15 kademesinde kazanan adedi 0 ile 3.000
    arasında geziyor ve tek bir favorili hafta ortalamayı tek başına
    belirliyor. Ortanca bandın tipik haftasını anlatır.

    Kişi başı ikramiye **nominal TL**dir ve sezonlar arası enflasyon
    taşır — bant karşılaştırması bu yüzden `sezon` süzgeciyle birlikte
    okunmalıdır. Ölçekten bağımsız okunacak sütun `kazanan_15`tir.
    """
    out: list[dict[str, Any]] = []
    for lo, hi in SURPRIZ_BANTLARI:
        grup = [k for k in kayitlar if lo <= k[alan] < hi]
        if len(grup) < ASGARI_HAFTA:
            out.append({"lo": lo, "hi": hi, "n": len(grup), "yeterli": False})
            continue
        out.append({
            "lo": lo, "hi": hi, "n": len(grup), "yeterli": True,
            "kazanan_15": _ortanca([k["kazanan"][15] for k in grup]),
            "kazanan_12": _ortanca([k["kazanan"][12] for k in grup]),
            "odul_15": _ortanca([k["odul"][15] for k in grup]),
            "odul_12": _ortanca([k["odul"][12] for k in grup]),
            # Kademe havuzu = kazanan x kisi basi. Sürprize göre DEGISMEMELI;
            # degisiyorsa degisen sey havuz degil devirdir.
            "havuz_15": _ortanca([k["kazanan"][15] * k["odul"][15] for k in grup]),
            "kazanansiz_15": sum(1 for k in grup if k["kazanan"][15] == 0),
        })
    return out


def dagilim(kayitlar: Sequence[dict[str, Any]],
            alan: str = "surpriz") -> list[dict[str, Any]]:
    """Haftada kaç sürpriz çıkıyor — çıplak sayım.

    Bu tablo ekseni tek başına kuran şeydir: sürprizsiz hafta **yok**.
    "Sürpriz gelir mi" diye sormak anlamsız; haftada ortalama 6,4 tane
    geliyor ve bilinmeyen tek şey hangileri olduğu. Yani bu bir sinyal
    sorunu değil, bir **bütçe** sorunudur.
    """
    sayim: dict[int, int] = {}
    for k in kayitlar:
        sayim[k[alan]] = sayim.get(k[alan], 0) + 1
    return [{"adet": a, "hafta": sayim[a]} for a in sorted(sayim)]


def surpriz_ozeti(sezon: str | None = None) -> dict[str, Any]:
    """Sürpriz ekseninin ölçülmüş özeti — `/api/surpriz`ın betimleyici yarısı.

    Bu gövdede **tek bir tahmin yoktur**. Hepsi ya resmî ikramiye
    tablosundan ya kapanış fiyatından gelen sayımdır.
    """
    kayitlar, denetim = hafta_kayitlari(sezon)
    if not kayitlar:
        return {"kesit": 0, "denetim": denetim, "sezon": sezon,
                "sezonlar": sezonlar(), "error": "kesit boş"}

    ort = {alan: round(sum(k[alan] for k in kayitlar) / len(kayitlar), 2)
           for alan in ("surpriz", "ger_surpriz")}
    korelasyon = {
        alan: {f"kazanan_{k}": spearman([r[alan] for r in kayitlar],
                                        [r["kazanan"][k] for r in kayitlar])
               for k in (15, 14, 13, 12)}
        for alan in ("surpriz", "ger_surpriz", "ort_logp")
    }
    return {
        "kesit": len(kayitlar),
        "sezon": sezon,
        "sezonlar": sezonlar(),
        "hafta_basi": ort,
        "en_az_surprizli_hafta": min(k["surpriz"] for k in kayitlar),
        "dagilim": dagilim(kayitlar),
        "dagilim_gercek": dagilim(kayitlar, "ger_surpriz"),
        "bantlar": bant_tablosu(kayitlar),
        "korelasyon": korelasyon,
        "denetim": denetim,
        "tanim": {
            "surpriz": "favori kazanmadı (beraberlik dahil)",
            "ger_surpriz": "favorinin karşı tarafı kazandı",
            "ort_logp": "haftanın sonuç dizisinin piyasa altındaki "
                        "ortalama log-olasılığı; büyüdükçe hafta favorili",
        },
        "sinir": (
            "Bu blok betimleyicidir: sürprizin havuzda NE ETTİĞİNİ ölçer, "
            "hangi maçın sürpriz OLACAĞINI söylemez. İkincisi §5.1'de on beş "
            "kez denendi ve hiçbiri geçmedi. Kişi başı ikramiye nominal TL'dir "
            "ve sezonlar arası enflasyon taşır."),
    }


def _main() -> int:
    ozet = surpriz_ozeti()
    d = ozet["denetim"]
    print(f"Kesit: {ozet['kesit']} hafta  (elenen {d['elenen']})")
    for e in d["elenenler"][:10]:
        print(f"   elendi {e['sezon']} hf {e['hafta']}: {e['sebep']} {e['ayrinti']}")
    print(f"Hafta başı sürpriz: {ozet['hafta_basi']['surpriz']} "
          f"(gerçek {ozet['hafta_basi']['ger_surpriz']}) · "
          f"en temiz hafta {ozet['en_az_surprizli_hafta']} sürprizli\n")

    print(f"{'Sürpriz':<10}{'n':>4}{'15 bilen':>10}{'12 bilen':>10}"
          f"{'15 ödülü (TL)':>18}{'15 kazanansız':>15}")
    for b in ozet["bantlar"]:
        ad = f"{b['lo']}–{b['hi'] - 1}" if b["hi"] <= 15 else f"{b['lo']}+"
        if not b["yeterli"]:
            print(f"{ad:<10}{b['n']:>4}{'— (az)':>10}")
            continue
        # `.0f` DEGIL: bunlar ortanca ve cift sayida haftada `.5` ile
        # biter. `.0f` 18,5'i 18 yazardi, arayuz ayni sayiyi 18,5
        # gosterirdi — iki yuzey ayni olcume iki farkli sayi der.
        print(f"{ad:<10}{b['n']:>4}{b['kazanan_15']:>10,.1f}"
              f"{b['kazanan_12']:>10,.1f}{b['odul_15']:>18,.0f}"
              f"{b['kazanansiz_15']:>15}")

    print("\nSpearman ρ (sürprizlik ↔ kazanan adedi):")
    for alan, satir in ozet["korelasyon"].items():
        print(f"   {alan:<12}" + "  ".join(
            f"{k}={v:+.3f}" if v is not None else f"{k}=—"
            for k, v in satir.items()))
    print(f"\n{ozet['sinir']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
