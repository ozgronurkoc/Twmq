"""1X2 dışı pazarlar — alt/üst 2,5 ve Asya handikabı (Faz 4.1).

`ISTATISTIK_YOL_HARITASI.md` §7 uzun süre şunu yazıyordu:

> *"Diğer pazarların arayüze çıkması — ürün kararı: 1X2 dışındakiler analiz
> içindir, arşivde kalır."*

Bu bir **ürün kararıydı**, bir ölçüm sonucu değil; kısıtlar kalkarken o da
kalktı. Arşiv iki fiyatı zaten taşıyor ve bu modül onları arayüze
çıkarılabilir hâle getiriyor — projenin değişmeyen tek kuralına uyarak:
**hiçbir sayı ölçülmüş isabeti olmadan görünmez.**

─── İki pazar, iki farklı ölçüm ──────────────────────────────────────────

**Alt/üst 2,5 temiz bir ikili olaydır.** 2,5 yarım çizgidir, iade yoktur,
sonuç ya üst ya alttır. Brier, kalibrasyon eğrisi ve Wilson aralığı
doğrudan uygulanır — 1X2 için ne yapılıyorsa aynısı.

**Asya handikabı değildir.** Arşivdeki çizgilerin **%53'ü çeyrektir**
(±0,25 / ±0,75) ve öyle bir bahis iki yarım bahse bölünür: sonuç
`{0, ¼, ½, ¾, 1}` kümesinden bir **getiri**dir, ikili bir olay değil. Tam
sayı çizgide ayrıca iade vardır.

Bu yüzden AH için Brier **hesaplanmaz**. Kesirli bir "sonuç"a karşı Brier
düzgün bir puanlama kuralı değildir ve hesaplansaydı sayı bir şeye
benzerdi ama hiçbir şey ölçmezdi. Onun yerine **beklenen getiri
kalibrasyonu** ölçülür: modelin dediği ortalama kapama olasılığı ile
gerçekleşen ortalama getiri, bant bant. Bu geçerli bir güvenilirlik
denetimidir ve bütün çizgileri kapsar.

Ayrımın yazılı olması şart: "AH'nin Brier'i yok" bir eksiklik değil, bir
**tanım**dır.
"""
from __future__ import annotations

from typing import Any

from .odds import (
    ARINDIRMA_VARSAYILAN,
    FIYAT_VARSAYILAN,
    implied_probs,
    load_odds,
    margin,
)
from .ortak import wilson

#: Alt/üst çizgisi. Arşiv yalnızca 2,5 taşıyor; sabit, seçim değil.
ALT_UST_CIZGI = 2.5

#: Kalibrasyon bantları — `ortak.OLASILIK_BANTLARI`dan farklı olarak kaba,
#: çünkü kesit bir sezon (615 maç) ve ince bant okunmaz. Kenarlar ölçüm
#: sonucuna BAKILMADAN seçildi.
BANTLAR: tuple[tuple[float, float], ...] = (
    (0.0, 0.35), (0.35, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 1.01),
)

#: Bir bandın yazılması için gereken en az maç. Altında yüzde okunmaz —
#: `kalibrasyon.EN_AZ_BANT` ile aynı gerekçe, kesit küçük olduğu için düşük.
EN_AZ_BANT = 30


def _cizgi(oranlar: dict[str, Any]) -> float | None:
    """Asya handikabı çizgisi — kapanış varsa o, yoksa açılış."""
    for ad in ("AHCh", "AHh"):
        v = oranlar.get(ad)
        if v is not None:
            return float(v)
    return None


def alt_ust(row: dict[str, Any], yontem: str = ARINDIRMA_VARSAYILAN,
            book: str = FIYAT_VARSAYILAN) -> dict[str, Any] | None:
    """Marj arındırılmış alt/üst 2,5 olasılığı + gerçekleşen sonuç.

    `None` döner ancak fiyat ya da gol eksikse — doktrin 2: eksik veri
    uydurulmaz, elenir.
    """
    o = row.get("odds") or {}
    ust = o.get(f"{book}C>{ALT_UST_CIZGI}", o.get(f"{book}>{ALT_UST_CIZGI}"))
    alt = o.get(f"{book}C<{ALT_UST_CIZGI}", o.get(f"{book}<{ALT_UST_CIZGI}"))
    if not ust or not alt or ust <= 1.0 or alt <= 1.0:
        return None

    p = implied_probs({"ust": float(ust), "alt": float(alt)}, yontem)
    if len(p) != 2:
        return None

    hg, ag = row.get("hg"), row.get("ag")
    toplam = None if hg is None or ag is None else int(hg) + int(ag)
    return {
        "week": row.get("week"), "no": row.get("no"),
        "home": row.get("home"), "away": row.get("away"),
        "cizgi": ALT_UST_CIZGI,
        "probs": p,
        "marj": margin({"ust": float(ust), "alt": float(alt)}),
        "toplam_gol": toplam,
        # 2,5 yarim cizgi: iade yok, sonuc kesin.
        "sonuc": None if toplam is None else ("ust" if toplam > ALT_UST_CIZGI
                                              else "alt"),
    }


def _ah_getiri(gol_farki: int, h: float) -> float:
    """Ev sahibine `h` çizgisiyle oynanan bahsin getirisi — `[0, 1]`.

    `skor.ah_kapama` **olasılık** dağılımı üzerinde çalışır; bu fonksiyon
    **gerçekleşmiş** bir skor üzerinde çalışır ve aynı kuralı uygular:
    çeyrek çizgi iki yarım bahse bölünür, tam sayı çizgide eşitlik iadedir
    (yarım getiri).
    """
    dortte_bir = round(h * 4)
    bilesenler: tuple[tuple[float, float], ...]
    if dortte_bir % 2 != 0:
        bilesenler = ((h - 0.25, 0.5), (h + 0.25, 0.5))
    else:
        bilesenler = ((h, 1.0),)

    getiri = 0.0
    for cizgi, pay in bilesenler:
        d = gol_farki + cizgi
        getiri += pay * (1.0 if d > 0 else (0.5 if d == 0 else 0.0))
    return getiri


def handikap(row: dict[str, Any], yontem: str = ARINDIRMA_VARSAYILAN,
             book: str = FIYAT_VARSAYILAN) -> dict[str, Any] | None:
    """Marj arındırılmış Asya handikabı + gerçekleşen **getiri**.

    Sonuç alanı `getiri`dir, `sonuc` değil — ve bu bilinçli: çeyrek
    çizgide bahis bölünür ve sonuç ikili değildir (modül başlığı).
    """
    o = row.get("odds") or {}
    ev = o.get(f"{book}CAHH", o.get(f"{book}AHH"))
    dep = o.get(f"{book}CAHA", o.get(f"{book}AHA"))
    h = _cizgi(o)
    if not ev or not dep or h is None or ev <= 1.0 or dep <= 1.0:
        return None

    p = implied_probs({"1": float(ev), "2": float(dep)}, yontem)
    if len(p) != 2:
        return None

    hg, ag = row.get("hg"), row.get("ag")
    fark = None if hg is None or ag is None else int(hg) - int(ag)
    return {
        "week": row.get("week"), "no": row.get("no"),
        "home": row.get("home"), "away": row.get("away"),
        "cizgi": h,
        "cizgi_tipi": ("ceyrek" if round(h * 4) % 2 else
                       ("tam" if float(h).is_integer() else "yarim")),
        "probs": p,
        "marj": margin({"1": float(ev), "2": float(dep)}),
        "gol_farki": fark,
        "getiri": None if fark is None else _ah_getiri(fark, h),
    }


def _alt_ust_ozeti(kayitlar: list[dict[str, Any]]) -> dict[str, Any]:
    """Brier + kalibrasyon — temiz ikili olay olduğu için tam ölçüm."""
    olculur = [k for k in kayitlar if k["sonuc"]]
    n = len(olculur)
    if not n:
        return {"n": 0, "brier": None, "bantlar": [], "marj": None,
                "ust_orani": None}

    # Iki sonuclu Brier: `ortak.brier` uc sembol bekliyor, o yuzden burada
    # ikili hali dogrudan yazilir. Olcek [0, 2] — 1X2'yle AYNI olcek, yani
    # sayilar dogrudan kiyaslanabilir.
    b = sum((k["probs"]["ust"] - (1.0 if k["sonuc"] == "ust" else 0.0)) ** 2
            + (k["probs"]["alt"] - (1.0 if k["sonuc"] == "alt" else 0.0)) ** 2
            for k in olculur) / n

    satirlar: list[dict[str, Any]] = []
    for lo, hi in BANTLAR:
        grup = [k for k in olculur if lo <= k["probs"]["ust"] < hi]
        if len(grup) < EN_AZ_BANT:
            continue
        ust = sum(1 for k in grup if k["sonuc"] == "ust")
        bekleniyor = sum(k["probs"]["ust"] for k in grup) / len(grup)
        alt_ga, ust_ga = wilson(ust, len(grup))
        satirlar.append({
            "lo": lo, "hi": hi, "n": len(grup),
            "piyasa": bekleniyor, "gercek": ust / len(grup),
            "fark": ust / len(grup) - bekleniyor,
            "ga_alt": alt_ga, "ga_ust": ust_ga,
            "piyasa_ga_icinde": alt_ga <= bekleniyor <= ust_ga,
        })

    return {
        "n": n,
        "brier": b,
        "ust_orani": sum(1 for k in olculur if k["sonuc"] == "ust") / n,
        "marj": sum(k["marj"] for k in olculur) / n,
        # Arayuz bantlarin NEYE gore dilimlendigini bilmek zorunda: alt/ust
        # olasiliga, handikap cizgiye gore (bkz. `CIZGI_DILIMLERI`).
        "bant_ekseni": "olasilik",
        "bantlar": satirlar,
        "sapan_bant": sum(1 for s in satirlar if not s["piyasa_ga_icinde"]),
    }


#: Handikap dilimleri **çizgiye** göre, olasılığa göre DEĞİL.
#:
#: Ölçüm sonucuna bakılarak yapılmış bir seçim değil, pazarın **tanımının**
#: sonucu: Asya handikabının bütün amacı iki tarafı eşitlemektir, yani
#: olasılık kasten %50'ye çivilenir. Olasılık bandına göre dilimlendiğinde
#: 539 maçın **531'i** tek banda düşüyor ve eğri hiçbir şey söylemiyor —
#: bu ölçüldü ve dilimleme o yüzden değişti.
#:
#: Çizgi ise gerçekten değişiyor (0'dan ±2,5'e) ve *"piyasa büyük
#: handikaplarda da haklı mı"* sorusu ancak öyle sorulabilir.
CIZGI_DILIMLERI: tuple[tuple[float, float], ...] = (
    (0.0, 0.30), (0.30, 0.60), (0.60, 1.10), (1.10, 9.99),
)


def _handikap_ozeti(kayitlar: list[dict[str, Any]]) -> dict[str, Any]:
    """Beklenen getiri kalibrasyonu — Brier **bilerek yok** (modül başlığı)."""
    olculur = [k for k in kayitlar if k["getiri"] is not None]
    n = len(olculur)
    if not n:
        return {"n": 0, "bantlar": [], "marj": None, "cizgi_tipleri": {}}

    satirlar: list[dict[str, Any]] = []
    for lo, hi in CIZGI_DILIMLERI:
        grup = [k for k in olculur if lo <= abs(k["cizgi"]) < hi]
        if len(grup) < EN_AZ_BANT:
            continue
        bekleniyor = sum(k["probs"]["1"] for k in grup) / len(grup)
        gercek = sum(k["getiri"] for k in grup) / len(grup)
        # Getiri kesirli oldugu icin Wilson dogrudan uygulanamaz; ortalamanin
        # standart hatasi kullanilir ve bu FARKLI bir aralik turudur —
        # etiketi de oyle yazilir.
        var = sum((k["getiri"] - gercek) ** 2 for k in grup) / max(len(grup) - 1, 1)
        se = (var / len(grup)) ** 0.5
        satirlar.append({
            "lo": lo, "hi": hi, "n": len(grup),
            "piyasa": bekleniyor, "gercek": gercek,
            "fark": gercek - bekleniyor,
            "se": se, "ga_alt": gercek - 1.96 * se, "ga_ust": gercek + 1.96 * se,
            "piyasa_ga_icinde": abs(gercek - bekleniyor) <= 1.96 * se,
        })

    tipler: dict[str, int] = {}
    for k in olculur:
        tipler[k["cizgi_tipi"]] = tipler.get(k["cizgi_tipi"], 0) + 1

    return {
        "n": n,
        # Brier YOK ve bu bir eksiklik degil bir tanim; alan acikca yaziliyor
        # ki arayuz "hesaplanamadi" diye gostermesin.
        "brier": None,
        "brier_yok_sebep": (
            "cizgilerin %53'u ceyrek; boyle bir bahis iki yarim bahse bolunur "
            "ve sonuc ikili degil kesirli bir getiridir. Kesirli bir sonuca "
            "karsi Brier duzgun bir puanlama kurali degildir"),
        "ortalama_getiri": sum(k["getiri"] for k in olculur) / n,
        "marj": sum(k["marj"] for k in olculur) / n,
        "cizgi_tipleri": tipler,
        # `lo`/`hi` burada CIZGI buyuklugu, olasilik degil.
        "bant_ekseni": "cizgi",
        "bantlar": satirlar,
        "sapan_bant": sum(1 for s in satirlar if not s["piyasa_ga_icinde"]),
    }


def sezon_ozeti(yontem: str = ARINDIRMA_VARSAYILAN,
                yol: str | None = None) -> dict[str, Any]:
    """İki pazarın sezon boyu ölçülmüş hâli — `/api/pazar`ın tek kaynağı."""
    satirlar = load_odds(yol)
    au = [k for k in (alt_ust(r, yontem) for r in satirlar) if k]
    ah = [k for k in (handikap(r, yontem) for r in satirlar) if k]
    return {
        "arindirma": yontem,
        "n_mac": len(satirlar),
        "alt_ust": {"kapsama": len(au) / len(satirlar) if satirlar else 0.0,
                    **_alt_ust_ozeti(au)},
        "handikap": {"kapsama": len(ah) / len(satirlar) if satirlar else 0.0,
                     **_handikap_ozeti(ah)},
        "sinir": (
            "Kesit BIR SEZON (kupon arsivi), 31 binlik egitim korpusu degil: "
            "korpus bu iki fiyati tasimiyor. Bantlar bu yuzden kaba ve "
            "sayilar 1X2 olcumlerinden daha genis araliklidir."),
    }
