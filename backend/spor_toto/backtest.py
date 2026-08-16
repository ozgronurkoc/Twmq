"""Geri test — "bu strateji geçen sezon ne yapardı?"

Sezonun her haftası için oranlardan bir kupon üretir, kaplama motorunu
çalıştırır ve **gerçekleşen sonucun** o kupona ne yaptığını ölçer: küme içinde
mi kaldı, en iyi kolon kaç tutturdu, kaç kolona mal oldu.

Zincir tektir ve her adımı başka bir modülden gelir:

    odds.match_1x2   → maç başına marj arındırılmış olasılık
    strateji eşiği   → maç başına banko / çifte / üçlü
    core.Encoder     → seçimlerin tamsayı uzayı
    core.solve_fix16 → 14-garantili kaplama (ya da blok/heuristik yedeği)
    history          → gerçekleşen sonuç

**Bu bir kâr vaadi değildir.** 41 hafta küçük bir örneklemdir; eşik taraması
yapıldığında en iyi görünen eşiğin gelecek sezon aynısını yapmayacağı
matematiksel bir beklentidir, uyarı değil. Bu yüzden modül üç şey döndürür:
tek stratejinin sonucu, eşik taraması ve **çıkarımlı (hold-out) sağlama** —
sonuncusu, eşiği o haftayı görmeden seçtiğinde ne olacağını ölçer.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .core import (
    Encoder,
    dogrula_kaplama,
    merge_rows,
    solve_by_blocks,
    solve_fix16,
    solve_heuristic,
)
from .history import MATCH_COUNT, SYMBOLS, normalized_weeks
from .odds import match_1x2, load_odds

try:  # pragma: no cover - ortama bagli
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None

#: Seçim uzayı bundan büyükse hafta çözülmez. Kaplamayı doğrulamak uzayın
#: tamamını gezmeyi gerektirir; doğrulayamadığımız bir bedeli rapor etmek
#: "garanti" kelimesini boşa harcamak olurdu.
UZAY_SINIRI = 200_000

#: Varsayılan strateji. Ölçülmüş banko bandından geliyor: favori oranı 1.35
#: altına inince isabet %64'ün üstüne çıkıyor, marj arındırılmış karşılığı
#: ~0,68. Üçlü eşiği ise favorinin 0,38'in altında kaldığı, yani piyasanın da
#: karar veremediği maçları kapatır.
VARSAYILAN_BANKO = 0.68
VARSAYILAN_UCLU = 0.38

#: Eşik taraması ızgarası. `uclu = 0.0` "hiç üçlü yok" demektir.
BANKO_IZGARA: Tuple[float, ...] = (0.50, 0.55, 0.60, 0.65, 0.68, 0.72, 0.78)
UCLU_IZGARA: Tuple[float, ...] = (0.0, 0.34, 0.38, 0.42)


# ─── strateji ─────────────────────────────────────────────────────────────────

def secim_uret(probs: Dict[str, float], banko_esik: float,
               uclu_esik: float) -> List[str]:
    """Bir maçın olasılığından işaretlenecek sembolleri seçer.

    Sıra kritik: önce banko sorulur. Böylece ``banko_esik <= uclu_esik`` gibi
    anlamsız bir çift verildiğinde bile çıktı tanımlı kalır.
    """
    sirali = sorted(SYMBOLS, key=lambda s: (-probs.get(s, 0.0), SYMBOLS.index(s)))
    p_fav = probs.get(sirali[0], 0.0)
    if p_fav >= banko_esik:
        return [sirali[0]]
    if p_fav < uclu_esik:
        return list(SYMBOLS)
    return sorted(sirali[:2], key=SYMBOLS.index)


# ─── kaplama (hafta bağımsız, imzaya göre önbellekli) ─────────────────────────

def _sentetik_encoder(sizes: Tuple[int, ...]) -> Encoder:
    """Yalnız alfabe boyutlarından bir Encoder. Kaplamanın maliyeti hangi
    maçın çifte olduğuna değil, boyutların çokkümesine bağlıdır."""
    harf = {1: ["1"], 2: ["1", "0"], 3: ["1", "0", "2"]}
    return Encoder([harf[k] for k in sizes], kati=False)


@lru_cache(maxsize=256)
def _kaplama(sizes: Tuple[int, ...]) -> Optional[Dict[str, Any]]:
    """Sıralanmış boyut imzası için kaplama. Uzay sınırı aşılırsa None.

    Önbellek anahtarı **sıralanmış** imzadır: 8 çifte + 2 üçlü, hangi maçlarda
    olursa olsun aynı bedeli verir. 41 hafta × 28 eşik çifti bu sayede birkaç
    düzine gerçek çözüme iner — eşik taramasının 5 saniyede bitmesinin sebebi
    budur.

    Kesin çözücü (ILP) burada **bilerek yok**: blok ayrıştırma zaten blok
    başına kanıtlanmış optimali kullanıyor ve ölçümde ILP tek imza için ~3 sn
    harcıyordu (tarama 95 sn'ye çıkıyordu). Tek kupon çözerken ILP değerlidir,
    yüzlerce imzayı tararken değil.
    """
    if not sizes:
        return {"columns": 1, "rows": 1, "cols": [()], "engine": "tam banko",
                "guaranteed": True, "worst": 0, "open": 0, "matrix": None}

    uzay = math.prod(sizes)
    if uzay > UZAY_SINIRI:
        return None

    enc = _sentetik_encoder(sizes)
    cift = sum(1 for k in sizes if k == 2)

    if cift >= 7:
        cols, _ = solve_fix16(enc)
        motor = "sabit 16 satır (Hamming 7,4)"
    else:
        blok = solve_by_blocks(enc, max_block_space=128, time_limit=5.0)
        if blok:
            cols, motor = blok[0], "blok ayrıştırma"
        else:
            cols = solve_heuristic(enc, trials=3, ls_iters=4_000, seed=42)
            motor = "sezgisel"

    worst, acik = dogrula_kaplama(cols, sizes)
    # `attempts=1`: birleştirme doğal koordinat sırasıyla yapılır. Formül
    # sayfasındaki motor 4 farklı sıra deneyip bazen 1–2 satır daha azını
    # bulur; burada satır sayısı ikincil bir ölçü ve 4 deneme taramayı
    # ~6 sn yavaşlatıyordu. Bedel (kolon) bundan etkilenmez.
    return {
        "columns": len(cols),
        "rows": len(merge_rows(cols, attempts=1)),
        "cols": cols,
        "engine": motor,
        "guaranteed": acik == 0,
        "worst": worst,
        "open": acik,
        # Skorlama kolon kolon dolaşmayı gerektirir; numpy varsa tek matris
        # karşılaştırmasına iner (20 bin kolonda saniyeler yerine milisaniye).
        "matrix": _np.array(cols, dtype=_np.int8) if _np is not None else None,
    }


def _en_iyi_skor(kap: Dict[str, Any], nokta: Sequence[int]) -> int:
    """Kolonlar içinde gerçekleşen sonuca en çok uyanın doğru sayısı.

    ``nokta`` içinde −1, o maçın seçim kümesi dışında kaldığını gösterir;
    kolon değerleri hiçbir zaman negatif olmadığı için eşleşmez.
    """
    if not nokta:
        return 0
    mat = kap.get("matrix")
    if mat is not None:
        return int((mat == _np.array(nokta, dtype=_np.int8)).sum(axis=1).max())
    return max(
        (sum(1 for a, b in zip(c, nokta) if a == b) for c in kap["cols"]),
        default=0,
    )


# ─── hafta girdisi ────────────────────────────────────────────────────────────

def hafta_girdileri(last: Optional[int] = None) -> List[Dict[str, Any]]:
    """Geri teste girecek haftalar: sonuç + 15 maçın olasılığı.

    Oranı eksik olan hafta **elenir, tamamlanmaz** (veri doktrini 2). Kaç
    haftanın neden elendiği çağırana ayrıca döner.
    """
    oran_satiri = {(r["week"], r["no"]): r for r in load_odds()}
    out: List[Dict[str, Any]] = []
    for w in normalized_weeks(last):
        probs: List[Optional[Dict[str, float]]] = []
        for no in range(1, MATCH_COUNT + 1):
            satir = oran_satiri.get((w["week"], no))
            blok = match_1x2(satir) if satir else None
            probs.append(blok["probs"] if blok else None)
        eksik = sum(1 for p in probs if p is None)
        out.append({
            "week": w["week"],
            "close_date": w["close_date"],
            "results": w["results"],
            "probs": probs,
            "missing": eksik,
            "usable": eksik == 0 and len(w["results"]) == MATCH_COUNT,
        })
    return out


# ─── tek hafta ────────────────────────────────────────────────────────────────

def _hafta_calistir(girdi: Dict[str, Any], banko_esik: float,
                    uclu_esik: float) -> Dict[str, Any]:
    secimler = [
        secim_uret(p or {}, banko_esik, uclu_esik) for p in girdi["probs"]
    ]
    gercek = girdi["results"]

    banko_pos = [i for i, s in enumerate(secimler) if len(s) == 1]
    var_pos = [i for i, s in enumerate(secimler) if len(s) > 1]
    sizes = tuple(len(secimler[i]) for i in var_pos)

    # İmzayı sırala; kolonları da o sıraya göre okuyacağız.
    duzen = sorted(range(len(sizes)), key=lambda j: (sizes[j], j))
    imza = tuple(sizes[j] for j in duzen)
    kap = _kaplama(imza)
    if kap is None:
        return {
            "week": girdi["week"],
            "skipped": True,
            "reason": f"seçim uzayı {math.prod(sizes):,} > {UZAY_SINIRI:,}",
        }

    # Gerçekleşen sonucun seçim uzayındaki koordinatı; küme dışıysa -1.
    banko_dogru = sum(1 for i in banko_pos if secimler[i][0] == gercek[i])
    nokta: List[int] = []
    kacak: List[int] = []
    for j in duzen:
        i = var_pos[j]
        sym = gercek[i]
        nokta.append(secimler[i].index(sym) if sym in secimler[i] else -1)
        if sym not in secimler[i]:
            kacak.append(i + 1)
    kacak += [i + 1 for i in banko_pos if secimler[i][0] != gercek[i]]
    kacak.sort()

    kume_ici = not kacak
    en_iyi = banko_dogru + _en_iyi_skor(kap, nokta)

    return {
        "week": girdi["week"],
        "close_date": girdi["close_date"],
        "skipped": False,
        "picks": ["".join(s) for s in secimler],
        "banko": len(banko_pos),
        "double": sum(1 for k in sizes if k == 2),
        "triple": sum(1 for k in sizes if k == 3),
        "columns": kap["columns"],
        "rows": kap["rows"],
        "engine": kap["engine"],
        "guaranteed": kap["guaranteed"],
        "in_set": kume_ici,
        "misses": len(kacak),
        "miss_at": kacak,
        "best": en_iyi,
        "results": gercek,
    }


# ─── sezon ────────────────────────────────────────────────────────────────────

def _wilson(basari: int, n: int) -> Tuple[float, float]:
    """Oran için Wilson %95 güven aralığı.

    Normal yaklaşım 41 haftada kenarlara yapışır (ör. 40/41'de üst sınır 1'i
    aşar); Wilson küçük örneklemde bu yüzden tercih edilir.
    """
    if n <= 0:
        return 0.0, 0.0
    z = 1.959964
    p = basari / n
    payda = 1 + z * z / n
    merkez = (p + z * z / (2 * n)) / payda
    yari = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / payda
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


def _ozet(hafta_sonuclari: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    calisan = [h for h in hafta_sonuclari if not h["skipped"]]
    n = len(calisan)
    if not n:
        return {"weeks": 0, "skipped": len(hafta_sonuclari)}
    kume_ici = sum(1 for h in calisan if h["in_set"])
    kolon = sum(h["columns"] for h in calisan)
    esik14 = sum(1 for h in calisan if h["best"] >= 14)
    esik13 = sum(1 for h in calisan if h["best"] >= 13)
    lo, hi = _wilson(esik14, n)
    return {
        "weeks": n,
        # Uzay sınırını aşıp çözülemeyen haftalar. Satırlar farklı hafta
        # sayıları üzerinden hesaplandığında karşılaştırma yanıltıcı olur;
        # bu yüzden sayı tabloda görünür.
        "skipped": len(hafta_sonuclari) - n,
        "in_set": kume_ici,
        "in_set_pct": round(100 * kume_ici / n, 1),
        "hit15": sum(1 for h in calisan if h["best"] >= 15),
        "hit14": esik14,
        "hit13": esik13,
        "hit14_pct": round(100 * esik14 / n, 1),
        "hit14_ci": [round(100 * lo, 1), round(100 * hi, 1)],
        "columns_total": kolon,
        "columns_avg": round(kolon / n, 1),
        "columns_max": max(h["columns"] for h in calisan),
        "columns_per_hit14": round(kolon / esik14, 1) if esik14 else None,
        "rows_avg": round(sum(h["rows"] for h in calisan) / n, 1),
        "banko_avg": round(sum(h["banko"] for h in calisan) / n, 1),
        "double_avg": round(sum(h["double"] for h in calisan) / n, 1),
        "triple_avg": round(sum(h["triple"] for h in calisan) / n, 1),
        "misses_total": sum(h["misses"] for h in calisan),
        "all_guaranteed": all(h["guaranteed"] for h in calisan),
    }


def _hepsini_calistir(girdiler: Sequence[Dict[str, Any]], banko_esik: float,
                      uclu_esik: float) -> List[Dict[str, Any]]:
    return [_hafta_calistir(g, banko_esik, uclu_esik)
            for g in girdiler if g["usable"]]


Tablo = Dict[Tuple[float, float], List[Dict[str, Any]]]


def izgara_tablosu(girdiler: Sequence[Dict[str, Any]],
                   banko_izgara: Sequence[float] = BANKO_IZGARA,
                   uclu_izgara: Sequence[float] = UCLU_IZGARA) -> Tablo:
    """(banko, üçlü) → hafta hafta sonuç.

    Hem eşik taraması hem hold-out aynı hesabı ister; iki kez yapmamak için
    tablo bir kez üretilip ikisine de verilir.
    """
    kullanilir = [g for g in girdiler if g["usable"]]
    return {
        (banko, uclu): [_hafta_calistir(g, banko, uclu) for g in kullanilir]
        for banko in banko_izgara
        for uclu in uclu_izgara
    }


def esik_taramasi(girdiler: Sequence[Dict[str, Any]],
                  banko_izgara: Sequence[float] = BANKO_IZGARA,
                  uclu_izgara: Sequence[float] = UCLU_IZGARA,
                  tablo: Optional[Tablo] = None) -> List[Dict[str, Any]]:
    """Izgaradaki her eşik çifti için sezon özeti.

    Tabloyu "en iyi satır" diye okumak tam olarak aşırı uyumun kendisidir;
    `backtest()` bunun için ayrıca hold-out ölçer.
    """
    if tablo is None:
        tablo = izgara_tablosu(girdiler, banko_izgara, uclu_izgara)
    out: List[Dict[str, Any]] = []
    for (banko, uclu), sonuclar in tablo.items():
        ozet = _ozet(sonuclar)
        if not ozet.get("weeks"):
            continue
        out.append({"banko": banko, "uclu": uclu, **ozet})
    out.sort(key=lambda r: (r["banko"], r["uclu"]))
    return out


def _en_iyi(satirlar: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Önce 14+ hafta sayısı, eşitlikte daha ucuz kupon."""
    if not satirlar:
        return None
    return max(satirlar, key=lambda r: (r["hit14"], -r["columns_total"]))


def holdout(girdiler: Sequence[Dict[str, Any]],
            banko_izgara: Sequence[float] = BANKO_IZGARA,
            uclu_izgara: Sequence[float] = UCLU_IZGARA,
            tablo: Optional[Tablo] = None) -> Dict[str, Any]:
    """Bir hafta dışarıda bırak, eşiği kalan haftalarda seç, dışarıdakinde ölç.

    Eşik taramasının en iyi satırı geçmişin **en iyi açıklamasıdır**; bu
    fonksiyon aynı yöntemin görmediği bir hafta üzerinde ne yaptığını söyler.
    İki sayı arasındaki fark, aşırı uyumun büyüklüğüdür.
    """
    kullanilir = [g for g in girdiler if g["usable"]]
    if len(kullanilir) < 3:
        return {"weeks": 0}
    if tablo is None:
        tablo = izgara_tablosu(girdiler, banko_izgara, uclu_izgara)

    n = len(kullanilir)
    tutan = 0
    kolon = 0
    secimler: Dict[str, int] = {}
    for disarida in range(n):
        en_iyi_anahtar = None
        en_iyi_skor: Tuple[int, int] = (-1, 0)
        for anahtar, sonuclar in tablo.items():
            ic = [h for i, h in enumerate(sonuclar)
                  if i != disarida and not h["skipped"]]
            if not ic:
                continue
            skor = (sum(1 for h in ic if h["best"] >= 14),
                    -sum(h["columns"] for h in ic))
            if skor > en_iyi_skor:
                en_iyi_skor, en_iyi_anahtar = skor, anahtar
        if en_iyi_anahtar is None:
            continue
        test = tablo[en_iyi_anahtar][disarida]
        if test["skipped"]:
            continue
        etiket = f"{en_iyi_anahtar[0]:.2f}/{en_iyi_anahtar[1]:.2f}"
        secimler[etiket] = secimler.get(etiket, 0) + 1
        tutan += 1 if test["best"] >= 14 else 0
        kolon += test["columns"]

    lo, hi = _wilson(tutan, n)
    return {
        "weeks": n,
        "hit14": tutan,
        "hit14_pct": round(100 * tutan / n, 1),
        "hit14_ci": [round(100 * lo, 1), round(100 * hi, 1)],
        "columns_total": kolon,
        "columns_avg": round(kolon / n, 1),
        "chosen": sorted(
            ({"threshold": k, "weeks": v} for k, v in secimler.items()),
            key=lambda d: -d["weeks"],
        ),
    }


UYARI = (
    "Bu tablo geçmişin en iyi açıklamasıdır, geleceğin garantisi değildir. "
    "41 hafta küçük bir örneklemdir ve eşik taraması yapıldığı için en iyi "
    "satır tanımı gereği bu sezona uyar. Karara esas alınacak sayı, eşiğin o "
    "haftayı görmeden seçildiği hold-out satırıdır."
)


def backtest(last: Optional[int] = None,
             banko_esik: float = VARSAYILAN_BANKO,
             uclu_esik: float = VARSAYILAN_UCLU,
             sweep: bool = True) -> Dict[str, Any]:
    """Bir stratejinin sezon boyu geri testi + eşik taraması + hold-out."""
    girdiler = hafta_girdileri(last)
    elenen = [
        {"week": g["week"], "missing": g["missing"]}
        for g in girdiler if not g["usable"]
    ]
    haftalar = _hepsini_calistir(girdiler, banko_esik, uclu_esik)
    # Tarama ile hold-out aynı tabloyu okur; iki kez hesaplanmaz.
    tablo = izgara_tablosu(girdiler) if sweep else None
    tarama = esik_taramasi(girdiler, tablo=tablo) if sweep else []

    return {
        "meta": {
            "weeks_available": len(girdiler),
            "weeks_used": len([g for g in girdiler if g["usable"]]),
            "weeks_dropped": elenen,
            "match_count": MATCH_COUNT,
            "space_limit": UZAY_SINIRI,
            "note": "piyasa kapanış oranları — iddaa oranı değildir",
        },
        "strategy": {
            "banko": banko_esik,
            "uclu": uclu_esik,
            "explain": (
                f"favori olasılığı ≥ %{100 * banko_esik:.0f} ise banko, "
                f"< %{100 * uclu_esik:.0f} ise üçlü, arası çifte"
            ),
        },
        "season": _ozet(haftalar),
        "weeks": haftalar,
        "sweep": tarama,
        "sweep_best": _en_iyi(tarama),
        "holdout": holdout(girdiler, tablo=tablo) if sweep else {"weeks": 0},
        "grid": {"banko": list(BANKO_IZGARA), "uclu": list(UCLU_IZGARA)},
        "warning": UYARI,
    }
