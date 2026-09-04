"""Fiyat kaynakları — üç bahisçi × açılış/kapanış, arşivin üzerinde ölçülür.

3. haftada hafta dosyası ilk kez birden çok bahisçinin açılış ve kapanış
oranını taşıdı (`matches[].odds_books`) ve bu, projenin daha önce
ölçemediği üç şeyi ölçülebilir kıldı: **çizgi hareketi**, **bahisçi
ayrışması** ve **bayat kayıt** (bir bahisçinin kapanışının açılışıyla
birebir aynı olması). Arşiv aynı bilgiyi zaten taşıyordu —
`odds_2025_26.csv` her bahisçinin her sütununu saklıyor — ama hiçbir yerde
okunmuyordu: bütün ölçümler tek bir fiyattan (`FIYAT_VARSAYILAN`) geçiyor
ve öteki fiyatlar görünmez duruyordu.

Bu modül o boşluğu kapatır. **Omurgayı değiştirmez**: `match_1x2` ve geri
test `Avg` üzerinden koşmaya devam eder (gerekçesi `odds.FIYAT_VARSAYILAN`
üstünde). Buradaki iş, öteki fiyatları *paralel iz* olarak ölçmek ve
aralarındaki farkı sayıya dökmektir.

─── Niçin omurga değişmiyor — ölçüldü ────────────────────────────────────

    fiyat          kapsama   15 maçı tam hafta   marj      Brier*
    Avg              %92          36 / 41       %7,99     0,5515
    Pinnacle         %40          15 / 41       %3,73     0,5522
    Betfair Exc.     %94          32 / 41       %0,71     0,5508
    (*) yalnızca üçünün de bulunduğu 247 maç üzerinde

**football-data 2026-01'de Pinnacle yayımlamayı bıraktı** ve eksiklik
rastgele değil, zamana bağlıdır: Şubat–Mayıs 2026 tamamen boştur. Bu yüzden
her Pinnacle sayısının yanında **hangi döneme ait olduğu** yazar
(`SezonFiyat.donem`); sessizce "sezon" diye etiketlenmesi, olmayan bir
kapsamayı ima etmek olurdu.

    python -m spor_toto.fiyatlar        # ya da scripts/fiyat_kaynaklari.py
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .core import SEMBOLLER
from .odds import (
    ARINDIRMA_VARSAYILAN,
    KITAP_ADLARI,
    implied_probs,
    load_odds,
    market_odds,
)
from .ortak import brier as _brier

#: Paralel iz olarak ölçülen kitaplar. `Max` bilerek YOK: bahisçiler
#: üzerindeki en iyi orandır, tek bir bahisçinin fiyatı değildir ve marjı
#: mekanik olarak düşük çıkar — olmayan bir bahisçinin fiyatı gibi
#: okunmasın diye dışarıda bırakıldı.
KITAPLAR: tuple[str, ...] = ("Avg", "PS", "BFE", "B365")

#: Açılış/kapanış — `market_odds(closing=)` bayrağının okunur karşılığı.
DONEMLER: tuple[tuple[str, bool], ...] = (("acilis", False), ("kapanis", True))

#: Bir maçın "bayat" sayılması için kapanışın açılışa eşitliği. Oranlar iki
#: ondalıkla yayımlandığı için tam eşitlik aranır: yaklaşık bir eşik,
#: gerçekten oynamış ama az oynamış bir çizgiyi bayat sayardı.
def _ayni(a: dict[str, float], b: dict[str, float]) -> bool:
    return bool(a) and bool(b) and all(
        abs(a[s] - b[s]) < 1e-9 for s in SEMBOLLER if s in a and s in b
    ) and set(a) == set(b)


def mac_fiyatlari(row: dict[str, Any],
                  kitaplar: Sequence[str] = KITAPLAR,
                  yontem: str = ARINDIRMA_VARSAYILAN) -> dict[str, Any]:
    """Bir maçın bütün fiyatları — arşivin `odds_books` karşılığı.

    Her (kitap × dönem) için ham oran, marj ve **arındırılmış olasılık**
    döner. Karşılaştırma daima arındırılmış olasılık üzerinden yapılmalıdır:
    ham oranın hareketi, piyasanın fikir değiştirmesiyle bahisçinin marjını
    değiştirmesini karıştırır (bkz. `spor_toto.cizgi` modül başlığı).
    """
    out: dict[str, Any] = {}
    for kitap in kitaplar:
        for ad, kapanis in DONEMLER:
            o = market_odds(row, "1X2", kitap, closing=kapanis)
            if len(o) != 3 or any(v <= 1.0 for v in o.values()):
                continue
            out[f"{kitap}_{ad}"] = {
                "book": kitap,
                "closing": kapanis,
                "odds": {s: round(o[s], 2) for s in SEMBOLLER},
                "probs": {s: round(v, 4)
                          for s, v in implied_probs(o, yontem).items()},
                "margin": round(sum(1 / v for v in o.values()) - 1, 4),
            }
    return out


#: Brier BURADA YENIDEN YAZILMISTI ve `ortak.py`nin baslik cumlesini
#: ("tek kaynak artik `ortak`") yalanliyordu. Govde tam sozlukte birebir
#: ayni sonucu veriyordu (36 kiyas, fark 0 — olculdu), ama tek bir yerde
#: AYRISIYORDU: `p[s]` yazdigi icin eksik bir sembolde `KeyError` firlatiyor,
#: kanonik govde ise `.get(s, 0.0)` ile 0 sayip devam ediyor. Yani kopya
#: yalnizca gereksiz degil, daha kirilgandi.
def sezon_fiyat_ozeti(yontem: str = ARINDIRMA_VARSAYILAN) -> dict[str, Any]:
    """Kitap × dönem başına kapsama, marj, Brier, dönem ve hareket.

    Hiçbir şey iddia etmez; ölçer. Çıktısı `scripts/fiyat_kaynaklari.py`
    tarafından basılır ve `data/odds/fiyat_kaynaklari.json`e yazılır.
    """
    satirlar = [r for r in load_odds() if r.get("matched")]
    kaynak: dict[str, dict[str, Any]] = {}
    for r in satirlar:
        for anahtar, blok in mac_fiyatlari(r, yontem=yontem).items():
            k = kaynak.setdefault(anahtar, {
                "book": blok["book"], "closing": blok["closing"],
                "n": 0, "marj": 0.0, "brier": 0.0, "brier_n": 0,
                "ilk": None, "son": None,
            })
            k["n"] += 1
            k["marj"] += blok["margin"]
            gun = (r.get("kickoff") or "")[:10]
            if gun:
                k["ilk"] = gun if k["ilk"] is None else min(k["ilk"], gun)
                k["son"] = gun if k["son"] is None else max(k["son"], gun)
            if r.get("code"):
                k["brier"] += _brier(blok["probs"], r["code"])
                k["brier_n"] += 1

    toplam = len(satirlar)
    kaynaklar = []
    for anahtar in sorted(kaynak):
        k = kaynak[anahtar]
        kaynaklar.append({
            "key": anahtar,
            "book": k["book"],
            "book_label": KITAP_ADLARI.get(k["book"], k["book"]),
            "closing": k["closing"],
            "n": k["n"],
            "coverage_pct": round(100 * k["n"] / toplam, 2) if toplam else 0.0,
            "avg_margin_pct": round(100 * k["marj"] / k["n"], 2) if k["n"] else None,
            "brier": round(k["brier"] / k["brier_n"], 6) if k["brier_n"] else None,
            "brier_n": k["brier_n"],
            # Donem, kapsama kadar onemli: Pinnacle'in eksigi rastgele
            # degil ZAMANA BAGLI. Bu iki alan olmadan %40 kapsama
            # "rastgele yarisi var" gibi okunurdu.
            "first_day": k["ilk"],
            "last_day": k["son"],
        })
    return {
        "matches": toplam,
        "arindirma": yontem,
        "sources": kaynaklar,
        "agreement": _ayrisma(satirlar, yontem),
        "movement": _hareket(satirlar, yontem),
        "stale_closing": _bayat(satirlar),
        "note": ("Arındırılmış olasılıklar üzerinden ölçüldü. Omurga fiyatı "
                 "`odds.FIYAT_VARSAYILAN`dır ve bu tablo onu DEĞİŞTİRMEZ; "
                 "öteki fiyatlar paralel iz olarak ölçülür."),
    }


def _ayrisma(satirlar: Sequence[dict[str, Any]],
             yontem: str) -> list[dict[str, Any]]:
    """Kitap çiftleri arasındaki ortalama fark — aynı dönemde, ortak maçlarda.

    Ortak kesit şart: iki tahminci **aynı maçlarda** ölçülmezse aradaki fark
    görüşü değil örneklemi ölçer (`cizgi.kesit()` aynı gerekçeyi yazıyor).
    """
    out = []
    for _ad, kapanis in DONEMLER:
        for i, a in enumerate(KITAPLAR):
            for b in KITAPLAR[i + 1:]:
                farklar: list[float] = []
                ba = bb = 0.0
                n = 0
                for r in satirlar:
                    oa = market_odds(r, "1X2", a, closing=kapanis)
                    ob = market_odds(r, "1X2", b, closing=kapanis)
                    if len(oa) != 3 or len(ob) != 3:
                        continue
                    if any(v <= 1.0 for v in list(oa.values()) + list(ob.values())):
                        continue
                    pa, pb = implied_probs(oa, yontem), implied_probs(ob, yontem)
                    farklar.append(sum(abs(pa[s] - pb[s]) for s in SEMBOLLER) / 3)
                    if r.get("code"):
                        ba += _brier(pa, r["code"])
                        bb += _brier(pb, r["code"])
                        n += 1
                if not farklar:
                    continue
                out.append({
                    "period": "kapanis" if kapanis else "acilis",
                    "a": a, "b": b, "n": len(farklar),
                    "mean_gap_pct": round(100 * sum(farklar) / len(farklar), 3),
                    "max_gap_pct": round(100 * max(farklar), 2),
                    "brier_a": round(ba / n, 6) if n else None,
                    "brier_b": round(bb / n, 6) if n else None,
                })
    return out


def _hareket(satirlar: Sequence[dict[str, Any]],
             yontem: str) -> list[dict[str, Any]]:
    """Açılış→kapanış hareketi, kitap başına — AYNI ailenin iki ucu.

    Aile karıştırılmaz: bir maçın açılışı `Avg`, kapanışı `PSC` alınırsa
    aradaki fark hareket değil **kaynak farkı** olur.
    """
    out = []
    for kitap in KITAPLAR:
        buyukluk: list[float] = []
        ba = bk = 0.0
        n = 0
        for r in satirlar:
            oa = market_odds(r, "1X2", kitap, closing=False)
            ok = market_odds(r, "1X2", kitap, closing=True)
            if len(oa) != 3 or len(ok) != 3:
                continue
            if any(v <= 1.0 for v in list(oa.values()) + list(ok.values())):
                continue
            pa, pk = implied_probs(oa, yontem), implied_probs(ok, yontem)
            buyukluk.append(max(abs(pk[s] - pa[s]) for s in SEMBOLLER))
            if r.get("code"):
                ba += _brier(pa, r["code"])
                bk += _brier(pk, r["code"])
                n += 1
        if not buyukluk:
            continue
        out.append({
            "book": kitap, "n": len(buyukluk),
            "mean_move_pct": round(100 * sum(buyukluk) / len(buyukluk), 3),
            "brier_acilis": round(ba / n, 6) if n else None,
            "brier_kapanis": round(bk / n, 6) if n else None,
            # Kapanis acilisi yeniyor mu — 3. haftanin ana fiyat gerekcesi
            # tam olarak bu. Kitap basina ayri olculur.
            "kapanis_daha_iyi": (bk < ba) if n else None,
        })
    return out


def _bayat(satirlar: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kapanışı açılışıyla BİREBİR aynı olan satırlar — fiyat değil, kayıt.

    3. haftada Nesine'nin 10–15. maç kapanışı açılışıyla aynıydı ve bahisçi
    ayrışmasının en büyük üçü tam o satırlardan geliyordu: ayrışma görüş
    farkı değil kayıt farkıydı. Arşivde de aynı denetim koşar.
    """
    out = []
    for kitap in KITAPLAR:
        ayni = 0
        cift = 0
        for r in satirlar:
            oa = market_odds(r, "1X2", kitap, closing=False)
            ok = market_odds(r, "1X2", kitap, closing=True)
            if len(oa) != 3 or len(ok) != 3:
                continue
            cift += 1
            if _ayni(oa, ok):
                ayni += 1
        if cift:
            out.append({
                "book": kitap, "pairs": cift, "identical": ayni,
                "identical_pct": round(100 * ayni / cift, 2),
            })
    return out


# ─── F2: kitap karşılaştırması — denenmemiş tek FİYAT ────────────────────

#: Karşılaştırmanın referansı — omurganın kendi fiyatı.
KIYAS_REFERANSI = "Avg_kapanis"

#: Arenaya hiç girmemiş adaylar. `A2` yalnızca B365 ve Pinnacle'ı denedi;
#: Betfair Exchange **bir model değil bir fiyattır** ve marjı bir büyüklük
#: mertebesi düşüktür (bkz. `kitap_kiyasi`).
KIYAS_ADAYLARI: tuple[str, ...] = (
    "BFE_kapanis", "PS_kapanis", "B365_kapanis", "Avg_acilis", "BFE_acilis")


def kitap_kiyasi(adaylar: Sequence[str] = KIYAS_ADAYLARI,
                 referans: str = KIYAS_REFERANSI,
                 tekrar: int = 20_000,
                 tohum: int = 29) -> dict[str, Any]:
    """Kupon kesitinde **fiyat** karşılaştırması — eşleştirilmiş, Holm'lu.

    ─── Niçin bu ölçüm: A2'nin görmediği aday ───────────────────────────

    §3.15 (A2) bahisçi ayrışmasını ölçtü ama yalnızca **B365 ve Pinnacle**
    ile; `build_egitim.A2_KAYNAKLARI` Betfair'i bilerek dışarıda bırakıyor
    ve gerekçesi kesit dengesi. Oysa kupon kesitinde ölçülen tablo
    (`sezon_fiyat_ozeti`) Betfair Exchange'i en düşük marjlı fiyat olarak
    gösteriyordu ve o fiyat **hiçbir zaman arenaya girmedi**.

    Aday bir model değil bir **fiyattır**: geçmesi *"piyasayı geçen bir
    modelimiz var"* demek değil, *"daha iyi bir piyasa var"* demektir.

    ─── Karşılaştırma yalnızca ORTAK maçlarda ───────────────────────────

    Her aday, referansla **birlikte bulunduğu** maçlarda ölçülür; kapsama
    ayrı bir sütundur ve karıştırılmaz. Bootstrap **hafta düzeyinde**
    (aynı haftanın maçları bağımsız değil) ve karar `evaluate.holm` ile
    aile bazlı düzeltilir — beş aday tekil aralığa bakılarak
    değerlendirilemez.
    """
    import random as _random

    from .evaluate import holm

    haftalar: dict[tuple[str, int], list[tuple[dict[str, Any], str]]] = {}
    for sezon in _SEZONLAR_KIYAS:
        try:
            satirlar = load_odds(sezon=sezon)
        except OSError:
            continue
        for r in satirlar:
            if r.get("code") not in SEMBOLLER:
                continue
            haftalar.setdefault((sezon, r["week"]), []).append(
                (mac_fiyatlari(r), r["code"]))
    toplam = sum(len(v) for v in haftalar.values())
    out: list[dict[str, Any]] = []
    p_degerleri: dict[str, float] = {}
    for ad in adaylar:
        hf: list[tuple[float, float, int]] = []
        marjlar: list[float] = []
        for lst in haftalar.values():
            a = b = 0.0
            n = 0
            for f, kod in lst:
                x, y = f.get(ad), f.get(referans)
                if x and y:
                    a += _brier(x["probs"], kod)
                    b += _brier(y["probs"], kod)
                    n += 1
                    marjlar.append(float(x["margin"]))
            if n:
                hf.append((a, b, n))
        na = sum(x[2] for x in hf)
        if not na:
            out.append({"ad": ad, "n": 0, "kapsama": 0.0, "gecti": None})
            continue
        rnd = _random.Random(tohum)
        dag = []
        for _ in range(tekrar):
            idx = [rnd.randrange(len(hf)) for _ in range(len(hf))]
            sn = sum(hf[i][2] for i in idx)
            dag.append((sum(hf[i][0] for i in idx)
                        - sum(hf[i][1] for i in idx)) / sn if sn else 0.0)
        dag.sort()
        alt = dag[int(0.025 * tekrar)]
        ust = dag[int(0.975 * tekrar)]
        p = (sum(1 for x in dag if x >= 0.0) + 1) / (tekrar + 1)
        p_degerleri[ad] = p
        out.append({
            "ad": ad, "n": int(na), "kapsama": na / toplam if toplam else 0.0,
            "marj": sum(marjlar) / len(marjlar) if marjlar else None,
            "aday_brier": sum(x[0] for x in hf) / na,
            "referans_brier": sum(x[1] for x in hf) / na,
            "fark": (sum(x[0] for x in hf) - sum(x[1] for x in hf)) / na,
            "alt": alt, "ust": ust, "p": p, "gecti": bool(ust < 0),
        })
    karar = holm(p_degerleri)
    for satir in out:
        satir["gecti_holm"] = karar.get(satir["ad"])
    return {"referans": referans, "hafta": len(haftalar), "mac": toplam,
            "denenen_aday_sayisi": len(p_degerleri), "adaylar": out}


#: Karşılaştırmanın koştuğu sezonlar — oran arşivi olan bütün sezonlar.
_SEZONLAR_KIYAS: tuple[str, ...] = (
    "2022_23", "2023_24", "2024_25", "2025_26")
