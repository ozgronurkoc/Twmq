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
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from .core import (
    Encoder,
    dogrula_kaplama,
    merge_rows,
    solve_by_blocks,
    solve_fix16,
    solve_heuristic,
)
from .history import MATCH_COUNT, SYMBOLS, normalized_weeks
from .odds import (
    ARINDIRMA_VARSAYILAN,
    load_odds,
    match_1x2,
    provenance_notu,
)
from .ortak import wilson

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
BANKO_IZGARA: tuple[float, ...] = (0.50, 0.55, 0.60, 0.65, 0.68, 0.72, 0.78)
UCLU_IZGARA: tuple[float, ...] = (0.0, 0.34, 0.38, 0.42)


# ─── strateji ─────────────────────────────────────────────────────────────────

def secim_uret(probs: dict[str, float], banko_esik: float,
               uclu_esik: float) -> list[str]:
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

def _sentetik_encoder(sizes: tuple[int, ...]) -> Encoder:
    """Yalnız alfabe boyutlarından bir Encoder. Kaplamanın maliyeti hangi
    maçın çifte olduğuna değil, boyutların çokkümesine bağlıdır."""
    harf = {1: ["1"], 2: ["1", "0"], 3: ["1", "0", "2"]}
    return Encoder([harf[k] for k in sizes], kati=False)


@lru_cache(maxsize=256)
def _kaplama(sizes: tuple[int, ...]) -> dict[str, Any] | None:
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


def _en_iyi_skor(kap: dict[str, Any], nokta: Sequence[int]) -> int:
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

def hafta_girdileri(last: int | None = None,
                    yontem: str = ARINDIRMA_VARSAYILAN) -> list[dict[str, Any]]:
    """Geri teste girecek haftalar: sonuç + 15 maçın olasılığı.

    Oranı eksik olan hafta **elenir, tamamlanmaz** (veri doktrini 2). Kaç
    haftanın neden elendiği çağırana ayrıca döner.

    `yontem` marj arındırmasını seçer (A5). Varsayılan değişirse **eşikler de
    değişmek zorundadır**: `VARSAYILAN_BANKO=0,68` orantısal arındırmanın
    ölçeğinde türetildi ve başka bir ölçekte aynı sayı başka bir kupon üretir.
    """
    oran_satiri = {(r["week"], r["no"]): r for r in load_odds()}
    out: list[dict[str, Any]] = []
    for w in normalized_weeks(last):
        probs: list[dict[str, float] | None] = []
        #: Kullanilan her fiyatin kitabi/donemi. `girdiler` API'ye
        #: serilestirilmiyor (yanit `_hepsini_calistir` ciktisindan gelir),
        #: yani bu alan yanit boyutunu buyutmez.
        kaynaklar: list[dict[str, Any]] = []
        for no in range(1, MATCH_COUNT + 1):
            satir = oran_satiri.get((w["week"], no))
            blok = match_1x2(satir, yontem) if satir else None
            probs.append(blok["probs"] if blok else None)
            if blok:
                # Fiyatin KIMDEN ve HANGI DONEMDEN geldigi burada
                # atiliyordu: yalnizca `probs` alinip blok dusuruluyordu.
                # Sonuc olarak geri testin meta notu "piyasa kapanis
                # oranlari" diye SABIT yaziliydi ve fiyat karissa (kitap
                # ya da acilis/kapanis) bunu kimse goremezdi.
                kaynaklar.append({"book": blok["book"],
                                  "closing": blok["closing"]})
        eksik = sum(1 for p in probs if p is None)
        out.append({
            "week": w["week"],
            "close_date": w["close_date"],
            "results": w["results"],
            "probs": probs,
            "missing": eksik,
            "usable": eksik == 0 and len(w["results"]) == MATCH_COUNT,
            "price_sources": kaynaklar,
        })
    return out


# ─── tek hafta ────────────────────────────────────────────────────────────────

def _hafta_calistir(girdi: dict[str, Any], banko_esik: float,
                    uclu_esik: float) -> dict[str, Any]:
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
    nokta: list[int] = []
    kacak: list[int] = []
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

#: Wilson araligi artik `ortak`ta. Bu ad korunuyor cunku `benzer`,
#: `kalibrasyon` ve `scripts/super_toto_sezon` onu buradan cagiriyordu.
_wilson = wilson


def _ozet(hafta_sonuclari: Sequence[dict[str, Any]]) -> dict[str, Any]:
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


def _hepsini_calistir(girdiler: Sequence[dict[str, Any]], banko_esik: float,
                      uclu_esik: float) -> list[dict[str, Any]]:
    return [_hafta_calistir(g, banko_esik, uclu_esik)
            for g in girdiler if g["usable"]]


Tablo = dict[tuple[float, float], list[dict[str, Any]]]


def izgara_tablosu(girdiler: Sequence[dict[str, Any]],
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


def esik_taramasi(girdiler: Sequence[dict[str, Any]],
                  banko_izgara: Sequence[float] = BANKO_IZGARA,
                  uclu_izgara: Sequence[float] = UCLU_IZGARA,
                  tablo: Tablo | None = None) -> list[dict[str, Any]]:
    """Izgaradaki her eşik çifti için sezon özeti.

    Tabloyu "en iyi satır" diye okumak tam olarak aşırı uyumun kendisidir;
    `backtest()` bunun için ayrıca hold-out ölçer.
    """
    if tablo is None:
        tablo = izgara_tablosu(girdiler, banko_izgara, uclu_izgara)
    out: list[dict[str, Any]] = []
    for (banko, uclu), sonuclar in tablo.items():
        ozet = _ozet(sonuclar)
        if not ozet.get("weeks"):
            continue
        out.append({"banko": banko, "uclu": uclu, **ozet})
    out.sort(key=lambda r: (r["banko"], r["uclu"]))
    return out


def _en_iyi(satirlar: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    """Önce 14+ hafta sayısı, eşitlikte daha ucuz kupon."""
    if not satirlar:
        return None
    return max(satirlar, key=lambda r: (r["hit14"], -r["columns_total"]))


def holdout(girdiler: Sequence[dict[str, Any]],
            banko_izgara: Sequence[float] = BANKO_IZGARA,
            uclu_izgara: Sequence[float] = UCLU_IZGARA,
            tablo: Tablo | None = None) -> dict[str, Any]:
    """Bir hafta dışarıda bırak, eşiği kalan haftalarda seç, dışarıdakinde ölç.

    Eşik taramasının en iyi satırı geçmişin **en iyi açıklamasıdır**; bu
    fonksiyon aynı yöntemin görmediği bir hafta üzerinde ne yaptığını söyler.
    İki sayı arasındaki fark, aşırı uyumun büyüklüğüdür.

    ─── Paydalar ────────────────────────────────────────────────────────

    Burada **iki farklı payda** var ve ayrı durmaları zorunlu, çünkü döngü
    bazı katları ölçmeden geçebiliyor: dışarıda bırakılan hafta arama
    uzayı yüzünden `skipped` ise (`UZAY_SINIRI`) o kat ölçülmez.

    `weeks` (= `n`)   kesitin büyüklüğü: kullanılabilir hafta sayısı.
    `olculen`         gerçekten ölçülen kat sayısı.
    `atlanan`         `weeks - olculen`, ve niçin atlandığı aşağıda.

    Kolon ortalaması **ölçülen kata** bölünür. Önceden `kolon / n` idi ve
    bu gerçek bir pay/payda uyuşmazlığıydı: `kolon` yalnızca ölçülen
    katlarda birikiyor, `n` bütün kullanılabilir haftaları sayıyordu — yani
    bir hafta atlandığı anda ortalama kolon **olduğundan düşük** çıkardı.
    Bugünkü 36 haftalık kesitte hiçbir hafta atlanmıyor, yani yayımlanmış
    sayı (2.228,4) değişmiyor; düzeltilen şey sayı değil, sayının hangi
    koşulda yanlış olacağıydı.

    `hit14` paydası **bilerek `weeks`** olarak kalıyor: ölçülemeyen bir
    hafta ıska sayılır. Bu muhafazakâr okumadır ve kasıtlıdır — atlanan
    haftayı paydadan da düşmek, stratejinin çözemediği haftaları yok
    sayarak isabet oranını yukarı çekerdi (backtest'in en kolay kendini
    kandırma yolu). Ama artık **görünür**: `olculen` ve `atlanan` çıktıda
    yazıyor, yani okuyan hangi paydanın kullanıldığını sormak zorunda
    kalmıyor. Karşılaştırma noktası `_ozet`tir; o da `n`'i hayatta kalan
    listeden yeniden hesaplayıp `skipped`'ı yanına yazar.
    """
    kullanilir = [g for g in girdiler if g["usable"]]
    if len(kullanilir) < 3:
        return {"weeks": 0}
    if tablo is None:
        tablo = izgara_tablosu(girdiler, banko_izgara, uclu_izgara)

    n = len(kullanilir)
    tutan = 0
    kolon = 0
    olculen = 0
    secimler: dict[str, int] = {}
    for disarida in range(n):
        en_iyi_anahtar = None
        en_iyi_skor: tuple[int, int] = (-1, 0)
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
        olculen += 1

    lo, hi = _wilson(tutan, n)
    return {
        "weeks": n,
        "olculen": olculen,
        "atlanan": n - olculen,
        # Iki paydanin niceni ayri durdugu docstring'de yazili. `hit14`
        # kesite (`n`) bolunur, kolon ortalamasi OLCULEN kata.
        "payda": {
            "hit14": "weeks (olculemeyen hafta iska sayilir)",
            "columns_avg": "olculen (yalnizca gercekten olculen katlar)",
        },
        "hit14": tutan,
        "hit14_pct": round(100 * tutan / n, 1),
        "hit14_ci": [round(100 * lo, 1), round(100 * hi, 1)],
        "columns_total": kolon,
        "columns_avg": round(kolon / olculen, 1) if olculen else None,
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


def backtest(last: int | None = None,
             banko_esik: float = VARSAYILAN_BANKO,
             uclu_esik: float = VARSAYILAN_UCLU,
             sweep: bool = True,
             yontem: str = ARINDIRMA_VARSAYILAN) -> dict[str, Any]:
    """Bir stratejinin sezon boyu geri testi + eşik taraması + hold-out.

    `yontem` marj arındırmasını seçer (A5); `meta.arindirma` ile çıktıda yazar
    çünkü eşikler ölçeğe bağlıdır ve hangi ölçekte ölçüldüğü sonradan
    anlaşılamazsa tablo yorumlanamaz.
    """
    girdiler = hafta_girdileri(last, yontem)
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
            # SABIT yaziliydi ve hangi bahisci oldugunu soylemiyordu; fiyat
            # karissa okuyucu goremezdi. Artik KULLANILAN fiyatlardan
            # uretiliyor — yalnizca geri teste GIREN haftalardan, cunku
            # elenen haftanin fiyati sonuca girmiyor.
            "note": provenance_notu([
                k for g in girdiler if g["usable"] for k in g["price_sources"]
            ]),
            "arindirma": yontem,
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
