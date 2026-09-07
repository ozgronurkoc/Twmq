"""Geri test — "bu strateji geçen sezon ne yapardı?"

Sezonun her haftası için oranlardan bir kupon üretir, seçim kümesini
kolonlara açar ve **gerçekleşen sonucun** o kupona ne yaptığını ölçer: küme
içinde mi kaldı, en iyi kolon kaç tutturdu, kaç kolona mal oldu.

Zincir tektir ve her adımı başka bir modülden gelir:

    odds.match_1x2   → maç başına marj arındırılmış olasılık
    strateji         → maç başına banko / çifte / üçlü
    core.Encoder     → seçimlerin tamsayı uzayı
    duz.kolonlar     → seçim kümesinin TAMAMI (2^çifte · 3^üçlü)
    history          → gerçekleşen sonuç

Üçüncü satır eskiden `core.solve_fix16 → 14-garantili kaplama (ya da
blok/heuristik yedeği)` idi ve bir **aramaydı**. Kaplama söküldü
(`docs/DUZ_SISTEME_GECIS.md`); arama da doğrulama da gereksiz, çünkü
kolonlar seçim kümesinin kendisi.

─── İkinci satır da değişti: strateji artık takılabilir ─────────────────

Uzun süre burada tek bir kural vardı — `secim_uret`, favorinin olasılığına
iki eşik uygulayan mekanik seçim (0,68 / 0,38). O kural **ürünün kullandığı
kural değildi**: kupon `secim.en_iyi_secim` ile, bütçe tavanı altında
`P(k ≤ 3)` enbüyüklenerek kuruluyor. Geri test ürünün ölçmediği bir şeyi
ölçüyordu ve README §1.1'in başlangıç çizgisi oradan yazılmıştı.

Bugün iki strateji var ve varsayılan **ürünün kendi kuralıdır**:

    "hedef"  (varsayılan)  secim.en_iyi_secim — bütçe altında P(k ≤ 3)
    "esik"   (taban çizgisi) secim_uret — iki eşikli mekanik kural

`esik` silinmedi çünkü kıyas için gereken tek karşı örnek odur: ayarlanan
bir parametresi olduğu için **aşırı uyum ölçülebilir** (eşik taraması +
hold-out). `hedef`te ayarlanan parametre yoktur — optimizasyon sonucu
görmez, piyasanın kendi olasılığına göre ex-ante bir hedefi enbüyükler —
dolayısıyla hold-out'un koruduğu risk de yoktur; onun yerine **bütçe
taraması** raporlanır.

─── Manşet 14 değil 12 ──────────────────────────────────────────────────

İkramiye 12. kademede başlar (`secim.HEDEF_KADEME`), 15 bir yan üründür.
Özet bu yüzden `hit12`yi manşet, `hit13`/`hit14`ü kuyruk olarak verir.
Eskiden manşet `hit14`tü ve bu, ortalaması 12 civarında olan bir dağılımın
üst kuyruğunu başarı ölçütü sanmak demekti.

**Bu bir kâr vaadi değildir.** Kesit küçüktür; eşik taraması yapıldığında en
iyi görünen eşiğin gelecek sezon aynısını yapmayacağı matematiksel bir
beklentidir, uyarı değil.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from .core import (
    Encoder,
)
from .duz import kolonlar as duz_kolonlar
from .getiri import KOLON_BEDELI
from .history import MATCH_COUNT, SYMBOLS, normalized_weeks
from .odds import (
    ARINDIRMA_VARSAYILAN,
    load_odds,
    match_1x2,
    provenance_notu,
)
from .ortak import wilson
from .secim import HEDEF_KADEME, en_iyi_secim, kacak_esigi

try:  # pragma: no cover - ortama bagli
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None

#: Seçim uzayı bundan büyükse hafta çözülmez. Düzde kolonlar seçim kümesinin
#: kendisidir, yani bu sınır bir arama sınırı değil **bellek** sınırıdır:
#: skorlama kolonları tek tek (numpy varsa tek matriste) gezer.
UZAY_SINIRI = 200_000

#: Taban çizgisi stratejinin eşikleri. Ölçülmüş banko bandından geliyor:
#: favori oranı 1.35 altına inince isabet %64'ün üstüne çıkıyor, marj
#: arındırılmış karşılığı ~0,68. Üçlü eşiği ise favorinin 0,38'in altında
#: kaldığı, yani piyasanın da karar veremediği maçları kapatır.
VARSAYILAN_BANKO = 0.68
VARSAYILAN_UCLU = 0.38

#: Eşik taraması ızgarası. `uclu = 0.0` "hiç üçlü yok" demektir.
BANKO_IZGARA: tuple[float, ...] = (0.50, 0.55, 0.60, 0.65, 0.68, 0.72, 0.78)
UCLU_IZGARA: tuple[float, ...] = (0.0, 0.34, 0.38, 0.42)

#: Tanınan stratejiler. `hedef` ürünün kendi kuralı, `esik` taban çizgisi.
STRATEJILER: tuple[str, ...] = ("hedef", "esik")

#: `hedef` stratejisinin varsayılan haftalık bütçesi (TL).
#:
#: **Bu bir HARCAMA KARARIDIR, veriden çıkarılmaz** — ve 2026-09-07'de
#: ₺2.000'den ₺210.000'e çıkarıldı. Gerekçe kıyasın geçerliliği: taban
#: çizgisi eşik kuralı tavansız koştuğu için düz ölçekte ₺187.217/hafta
#: harcıyordu, yani ürün kuralı onunla yan yana konamıyordu. ₺210.000 o
#: rakamın üstündedir; iki kural artık **en az aynı parayla** yarışıyor.
#:
#: Bedelin ölçülmüş karşılığı (114 hafta, düz): 12+ %93,0, ortalama en iyi
#: kolon 13,22, gerçek kolon ödülünün geri dönüşü %46,5. Başabaş 1,0 hâlâ
#: uzak — daha çok para, daha az kötü kaybetmek demek.
#:
#: **Tavanın şekli sabitlediği yer burasıdır.** 21.000 kolonun altında en
#: geniş kapsama 9 üçlü + 6 banko (`3^9 = 19.683`); üçlünün kaçağı sıfır
#: olduğu için optimizasyon bütçe elverdiğince üçlü alır. Şekil bu yüzden
#: 114 haftanın hepsinde aynıdır — ama **plan aynı değildir**: hangi altı
#: maçın banko olacağı oranlardan gelir ve 114 haftanın 114'ünde farklı
#: çıkar. Kural körleşmiyor, karar uzayı daralıyor.
VARSAYILAN_BUTCE_TL = 210000.0

#: `hedef` stratejisinin bütçe taraması (TL). Eşik taramasının yerini tutar:
#: orada taranan şey ayarlanan bir parametre (aşırı uyum riski), burada
#: taranan şey bir **harcama kararı**.
#:
#: Merdiven `karne.BUTCELER`in bütün basamaklarını **içermek zorunda**: para
#: ekseni (gerçek ikramiye ROI'si) orada ölçülüyor ve iki hat aynı parayı
#: konuşmazsa kademe isabeti ile para karşılığı yan yana okunamaz. Üstüne üç
#: basamak eklenir, çünkü varsayılan tavan artık ₺210.000 ve ₺5.000 ile onun
#: arasındaki eğri okunmadan "bir basamak yukarı çıkmak neye değiyor"
#: sorusu cevaplanamaz. `karne` içe aktarılmıyor (2.000 satırlık ölçüm
#: modülü, API'nin soğuk açılışına girmemeli); kapsamayı
#: `tests/test_backtest.py::test_butce_merdiveni_karneyi_KAPSAR` tutuyor.
BUTCE_IZGARA: tuple[float, ...] = (
    500.0, 1000.0, 1500.0, 2000.0, 3000.0, 5000.0,   # karne.BUTCELER
    20000.0, 60000.0, 210000.0,                       # düz tavana giden basamaklar
)


def butce_kolon(butce_tl: float) -> int:
    """TL bütçeyi kolon adedine çevirir — `getiri.KOLON_BEDELI` ile.

    Aşağı yuvarlanır: bütçenin üstüne çıkan bir plan oynanamaz.

    >>> butce_kolon(2000.0)
    200
    """
    return int(butce_tl // KOLON_BEDELI)


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


#: Bir haftanın olasılıklarından işaret planı üreten şey. `None` döndürmek
#: "bu hafta bu stratejiyle kurulamadı" demektir ve hafta atlanır.
Secici = Any


def esik_secici(banko_esik: float, uclu_esik: float) -> Secici:
    """Taban çizgisi: maç maç bağımsız iki eşik.

    Haftanın şeklini görmez, bütçeyi bilmez, hiçbir yerde ürünün önemsediği
    sayıyı optimize etmez. Kıyas için duruyor — ayarlanan bir parametresi
    olduğu için aşırı uyumu **ölçülebilen** tek strateji odur.
    """
    def sec(probs_listesi: Sequence[dict[str, float] | None]) -> list[list[str]] | None:
        return [secim_uret(p or {}, banko_esik, uclu_esik) for p in probs_listesi]
    return sec


def hedef_secici(butce_tl: float = VARSAYILAN_BUTCE_TL,
                 kademe: int = HEDEF_KADEME) -> Secici:
    """Ürünün kendi kuralı: bütçe altında `P(k ≤ 15 − kademe)`'yi enbüyükler.

    `secim.en_iyi_secim`in kesin Pareto DP'sini çağırır — geri test ile ürün
    **aynı** kodu koşsun diye; ikinci bir kopya, iki hattın sessizce
    ayrışacağı yer olurdu.

    Bütçe TL cinsindendir ve `butce_kolon` ile kolona çevrilir. Tavansız
    çağrı `secim.en_iyi_secim` tarafından reddedilir (dejenere cevap: hepsi
    üçlü); burada da varsayılan bir tavan **vardır**, çünkü geri testin
    tavansız hâli anlamsızdır ve sessizce anlamsız bir tablo üretmek en kötü
    seçenektir.
    """
    if butce_tl is None:
        raise ValueError(
            "Butce zorunludur — tavansiz aramanin cevabi dejeneredir "
            "(hepsi uclu, 3^15 = 14.348.907 kolon). Bkz. secim.en_iyi_secim.")
    if butce_tl <= 0:
        raise ValueError("Butce pozitif olmali.")
    kolon = butce_kolon(butce_tl)
    if kolon < 1:
        raise ValueError(
            f"Butce {butce_tl} TL tek kolonu bile almiyor "
            f"(kolon bedeli {KOLON_BEDELI} TL).")
    esik = kacak_esigi(kademe)

    def sec(probs_listesi: Sequence[dict[str, float] | None]) -> list[list[str]] | None:
        if any(p is None for p in probs_listesi):
            return None
        plan = en_iyi_secim([dict(p) for p in probs_listesi if p is not None],
                            kolon, esik)
        return None if plan is None else plan.secimler
    return sec


def secici_uret(strateji: str = "hedef",
                banko_esik: float = VARSAYILAN_BANKO,
                uclu_esik: float = VARSAYILAN_UCLU,
                butce_tl: float = VARSAYILAN_BUTCE_TL,
                kademe: int = HEDEF_KADEME) -> Secici:
    """Ada göre strateji. Tanınmayan ad **sessizce varsayılana düşmez**."""
    if strateji == "hedef":
        return hedef_secici(butce_tl, kademe)
    if strateji == "esik":
        return esik_secici(banko_esik, uclu_esik)
    raise ValueError(
        f"Bilinmeyen strateji {strateji!r}; tanınanlar: {', '.join(STRATEJILER)}")


# ─── kolon kümesi (hafta bağımsız, imzaya göre önbellekli) ────────────────────

def _sentetik_encoder(sizes: tuple[int, ...]) -> Encoder:
    """Yalnız alfabe boyutlarından bir Encoder. Kolon kümesinin büyüklüğü hangi
    maçın çifte olduğuna değil, boyutların çokkümesine bağlıdır."""
    harf = {1: ["1"], 2: ["1", "0"], 3: ["1", "0", "2"]}
    return Encoder([harf[k] for k in sizes], kati=False)


@lru_cache(maxsize=256)
def _kolon_kumesi(sizes: tuple[int, ...]) -> dict[str, Any] | None:
    """Sıralanmış boyut imzası için kolon kümesi. Uzay sınırı aşılırsa None.

    Önbellek anahtarı **sıralanmış** imzadır: 8 çifte + 2 üçlü, hangi maçlarda
    olursa olsun aynı bedeli verir. Tarama yüzlerce hafta × onlarca ayar
    gezdiği için bu önbellek işin bitme süresini belirliyor.

    **Bu fonksiyon eskiden bir ARAMAYDI** ve adı `_kaplama`ydı. Yedi çifte
    varsa `solve_fix16`, yoksa blok ayrıştırma, o da olmazsa sezgisel motor
    koşuyordu; sonra üretilen kaplamanın gerçekten örttüğü `dogrula_kaplama`
    ile sınanıyordu. Kaplama söküldü (`docs/DUZ_SISTEME_GECIS.md`): kolonlar
    seçim kümesinin kendisi, yani arama da doğrulama da gereksiz. Ad da o
    yüzden değişti — `_kaplama` diye duran bir fonksiyon, sökülmüş bir
    katmanın adını taşıyordu.
    """
    if not sizes:
        return {"columns": 1, "rows": 1, "cols": [()], "engine": "tam banko",
                "guaranteed": True, "worst": 0, "open": 0, "matrix": None}

    uzay = math.prod(sizes)
    if uzay > UZAY_SINIRI:
        return None

    enc = _sentetik_encoder(sizes)
    cols = duz_kolonlar(enc, en_cok=UZAY_SINIRI)
    return {
        "columns": len(cols),
        # Duzde kupon isaretlerin kendisidir: tek satir.
        "rows": 1,
        "cols": cols,
        "engine": "düz (tam sistem)",
        # Kume ICI acik nokta olamaz: her kombinasyon oynaniyor.
        "guaranteed": True,
        "worst": 0,
        "open": 0,
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
                    yontem: str = ARINDIRMA_VARSAYILAN,
                    sezon: str | None = None) -> list[dict[str, Any]]:
    """Geri teste girecek haftalar: sonuç + 15 maçın olasılığı.

    Oranı eksik olan hafta **elenir, tamamlanmaz** (veri doktrini 2). Kaç
    haftanın neden elendiği çağırana ayrıca döner.

    `yontem` marj arındırmasını seçer (A5). Varsayılan değişirse **eşikler de
    değişmek zorundadır**: `VARSAYILAN_BANKO=0,68` orantısal arındırmanın
    ölçeğinde türetildi ve başka bir ölçekte aynı sayı başka bir kupon üretir.

    `sezon` hem hafta kaydını hem oran arşivini seçer; **ikisi birlikte
    seçilmek zorundadır**, çünkü oran anahtarı `(week, no)` ve sezon
    bileşeni yok — karışık verilirse başka bir sezonun oranları sessizce
    bu haftalara yapışır.
    """
    oran_satiri = {(r["week"], r["no"]): r for r in load_odds(sezon=sezon)}
    out: list[dict[str, Any]] = []
    for w in normalized_weeks(last, sezon):
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
            # `sezon` OLMADAN `evaluate.sezon_anahtari` her haftaya None der
            # ve sezon disarida birakmali olcum tek gruba coker — yani hic
            # kurulamaz. `arena.kesit(kupon=True)` bunu bir uyari dizesiyle
            # yaziyordu; alan geldigi icin o uyari artik kalkabilir.
            "sezon": w.get("season") or "",
            "results": w["results"],
            "probs": probs,
            "missing": eksik,
            "usable": eksik == 0 and len(w["results"]) == MATCH_COUNT,
            "price_sources": kaynaklar,
        })
    return out


# ─── tek hafta ────────────────────────────────────────────────────────────────

def _hafta_calistir(girdi: dict[str, Any], secici: Secici) -> dict[str, Any]:
    """Bir haftayı verilen stratejiyle koş ve gerçekleşen sonuca karşı ölç."""
    secimler = secici(girdi["probs"])
    if secimler is None:
        return {
            "week": girdi["week"],
            "sezon": girdi.get("sezon", ""),
            "skipped": True,
            "reason": "strateji bu hafta için plan kuramadı (bütçe ya da eksik oran)",
        }
    gercek = girdi["results"]

    banko_pos = [i for i, s in enumerate(secimler) if len(s) == 1]
    var_pos = [i for i, s in enumerate(secimler) if len(s) > 1]
    sizes = tuple(len(secimler[i]) for i in var_pos)

    # İmzayı sırala; kolonları da o sıraya göre okuyacağız.
    duzen = sorted(range(len(sizes)), key=lambda j: (sizes[j], j))
    imza = tuple(sizes[j] for j in duzen)
    kap = _kolon_kumesi(imza)
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
    esik12 = sum(1 for h in calisan if h["best"] >= 12)
    lo12, hi12 = _wilson(esik12, n)
    # KADEME DAGILIMI: birikimli degil, TAM kademe. `hit12` "12 ve ustu"
    # demek ve icinde 15'ler de var; ikramiye tablosunda ise 15 ile 12
    # arasinda binlerce kat fark oluyor. Birikimli sayi o farki gizler,
    # dagilim gizlemez.
    tam = {str(k): sum(1 for h in calisan if h["best"] == k)
           for k in range(HEDEF_KADEME, MATCH_COUNT + 1)}
    tam["alt"] = sum(1 for h in calisan if h["best"] < HEDEF_KADEME)
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
        # MANSET. Ikramiye 12. kademede baslar (`secim.HEDEF_KADEME`), yani
        # urunun olctugu sayi budur. `hit14` kuyruktur ve tek basina
        # okunursa yaniltir: ortalamasi 12 civarinda olan bir dagilimin
        # ust ucudur, bir yetenek gostergesi degil.
        "hit12": esik12,
        "hit12_pct": round(100 * esik12 / n, 1),
        "hit12_ci": [round(100 * lo12, 1), round(100 * hi12, 1)],
        # Manset `hit12` KALIR; bu onun kirilimidir. Toplami `weeks` eder.
        "kademe_dagilimi": tam,
        "kademe_dagilimi_pct": {k: round(100 * v / n, 1) for k, v in tam.items()},
        # Duzde en iyi kolon = 15 - kacak, yani bu ortalama dogrudan
        # "haftanin tipik sonucu" demek.
        "best_avg": round(sum(h["best"] for h in calisan) / n, 2),
        "hit14_pct": round(100 * esik14 / n, 1),
        "hit14_ci": [round(100 * lo, 1), round(100 * hi, 1)],
        "columns_total": kolon,
        "columns_avg": round(kolon / n, 1),
        "columns_max": max(h["columns"] for h in calisan),
        # Kolon adedi tek basina okunamaz: bedeli TL'ye ceviren sey
        # `getiri.KOLON_BEDELI` ve o sayi olculmustur (dis kunye, §3.48).
        "tl_avg": round(KOLON_BEDELI * kolon / n, 2),
        "tl_total": round(KOLON_BEDELI * kolon, 2),
        "columns_per_hit12": round(kolon / esik12, 1) if esik12 else None,
        "columns_per_hit14": round(kolon / esik14, 1) if esik14 else None,
        "rows_avg": round(sum(h["rows"] for h in calisan) / n, 1),
        "banko_avg": round(sum(h["banko"] for h in calisan) / n, 1),
        "double_avg": round(sum(h["double"] for h in calisan) / n, 1),
        "triple_avg": round(sum(h["triple"] for h in calisan) / n, 1),
        "misses_total": sum(h["misses"] for h in calisan),
        "all_guaranteed": all(h["guaranteed"] for h in calisan),
    }


def _hepsini_calistir(girdiler: Sequence[dict[str, Any]],
                      secici: Secici) -> list[dict[str, Any]]:
    return [_hafta_calistir(g, secici) for g in girdiler if g["usable"]]


Tablo = dict[tuple[float, float], list[dict[str, Any]]]


def izgara_tablosu(girdiler: Sequence[dict[str, Any]],
                   banko_izgara: Sequence[float] = BANKO_IZGARA,
                   uclu_izgara: Sequence[float] = UCLU_IZGARA) -> Tablo:
    """(banko, üçlü) → hafta hafta sonuç. **Yalnız `esik` ailesine aittir.**

    Hem eşik taraması hem hold-out aynı hesabı ister; iki kez yapmamak için
    tablo bir kez üretilip ikisine de verilir.

    `hedef` stratejisinin karşılığı `butce_taramasi`dir ve orada hold-out
    yoktur — çünkü ayarlanan bir parametre yoktur (bkz. modül başlığı).
    """
    kullanilir = [g for g in girdiler if g["usable"]]
    return {
        (banko, uclu): [_hafta_calistir(g, esik_secici(banko, uclu))
                        for g in kullanilir]
        for banko in banko_izgara
        for uclu in uclu_izgara
    }


def butce_taramasi(girdiler: Sequence[dict[str, Any]],
                   butceler: Sequence[float] = BUTCE_IZGARA,
                   kademe: int = HEDEF_KADEME) -> list[dict[str, Any]]:
    """`hedef` stratejisi için bütçe basamağı başına sezon özeti.

    Eşik taramasının **yerini tutar ama aynı şey değildir** ve fark önemli:
    eşik taraması sonuçlara bakıp bir parametre seçtiği için hold-out
    gerektiriyordu. Burada seçilen bir parametre yok — bütçe bir **harcama
    kararıdır**, veriden çıkarılmaz. O yüzden bu tablonun "en iyi satırı"
    diye okunacak bir satırı da yoktur: pahalı basamak her zaman daha çok
    tutturur, sorulacak soru tutturmanın bedele değip değmediğidir.
    """
    kullanilir = [g for g in girdiler if g["usable"]]
    out: list[dict[str, Any]] = []
    for tl in butceler:
        ozet = _ozet([_hafta_calistir(g, hedef_secici(tl, kademe))
                      for g in kullanilir])
        if not ozet.get("weeks"):
            continue
        out.append({"butce_tl": tl, "butce_kolon": butce_kolon(tl), **ozet})
    return out


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


#: Tarama ve hold-out'un enbüyüklediği ölçü. Varsayılan **`hit12`**: ikramiye
#: 12'de başlar, yani ürünün hedefi odur. Eskiden `hit14`tü ve o seçim
#: taramayı 36 haftada 2-3 kez görülen bir kuyruk olayına göre ayarlıyordu —
#: gürültüye uydurma tanımının kendisi.
VARSAYILAN_OLCUT = "hit12"


def _en_iyi(satirlar: Sequence[dict[str, Any]],
            olcut: str = VARSAYILAN_OLCUT) -> dict[str, Any] | None:
    """Önce `olcut` (varsayılan 12+ hafta sayısı), eşitlikte daha ucuz kupon."""
    if not satirlar:
        return None
    return max(satirlar, key=lambda r: (r[olcut], -r["columns_total"]))


def holdout(girdiler: Sequence[dict[str, Any]],
            banko_izgara: Sequence[float] = BANKO_IZGARA,
            uclu_izgara: Sequence[float] = UCLU_IZGARA,
            tablo: Tablo | None = None,
            olcut: str = VARSAYILAN_OLCUT) -> dict[str, Any]:
    """Bir hafta dışarıda bırak, eşiği kalan haftalarda seç, dışarıdakinde ölç.

    **Yalnız `esik` ailesine aittir.** `hedef` stratejisinde ayarlanan bir
    parametre yoktur (optimizasyon sonucu görmez, ex-ante bir hedefi
    enbüyükler), dolayısıyla bu fonksiyonun koruduğu risk de yoktur —
    `backtest()` orada bunun yerine `butce_taramasi` döndürür.

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
    Düzde bu artık kuramsal bir uç durum değil: kaplama sökülünce kolon
    sayısı sekiz kat büyüdü ve `UZAY_SINIRI`'na dayanan haftalar çıktı,
    yani `atlanan` gerçekten sıfırdan büyük olabiliyor.

    İsabet paydası **bilerek `weeks`** olarak kalıyor: ölçülemeyen bir
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

    # "hit12" -> 12. Olcut adiyla esik ayni yerden gelsin ki ikisi ayrisamasin.
    kademe = int(olcut.removeprefix("hit"))
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
            skor = (sum(1 for h in ic if h["best"] >= kademe),
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
        tutan += 1 if test["best"] >= kademe else 0
        kolon += test["columns"]
        olculen += 1

    lo, hi = _wilson(tutan, n)
    return {
        "weeks": n,
        "olculen": olculen,
        "atlanan": n - olculen,
        # Iki paydanin niceni ayri durdugu docstring'de yazili. Isabet
        # kesite (`n`) bolunur, kolon ortalamasi OLCULEN kata.
        "olcut": olcut,
        "payda": {
            olcut: "weeks (olculemeyen hafta iska sayilir)",
            "columns_avg": "olculen (yalnizca gercekten olculen katlar)",
        },
        olcut: tutan,
        f"{olcut}_pct": round(100 * tutan / n, 1),
        f"{olcut}_ci": [round(100 * lo, 1), round(100 * hi, 1)],
        "columns_total": kolon,
        "columns_avg": round(kolon / olculen, 1) if olculen else None,
        "tl_avg": round(KOLON_BEDELI * kolon / olculen, 2) if olculen else None,
        "chosen": sorted(
            ({"threshold": k, "weeks": v} for k, v in secimler.items()),
            key=lambda d: -d["weeks"],
        ),
    }


#: `esik` ailesinin uyarısı: taranan bir parametre var, yani en iyi satır
#: tanımı gereği bu kesite uyar.
UYARI_ESIK = (
    "Bu tablo geçmişin en iyi açıklamasıdır, geleceğin garantisi değildir. "
    "Kesit küçüktür ve eşik taraması yapıldığı için en iyi satır tanımı "
    "gereği bu sezona uyar. Karara esas alınacak sayı, eşiğin o haftayı "
    "görmeden seçildiği hold-out satırıdır. Bu strateji ürünün kullandığı "
    "kural DEĞİLDİR; taban çizgisi olarak durur."
)

#: `hedef` ailesinin uyarısı: taranan parametre yok, ama okunacak sayı da
#: isabet değil bedeldir.
UYARI_HEDEF = (
    "Bu, ürünün kendi kuralıdır ve optimizasyon SONUCU GÖRMEZ: piyasanın "
    "kendi olasılığına göre ex-ante bir hedefi enbüyükler, yani eşik "
    "taramasının aşırı uyum riskini taşımaz. Manşet 12'dir — ikramiye orada "
    "başlar. 14+ sayıları tek olaydır ve sonuç olarak okunmamalıdır; sağlam "
    "olan sayılar hedef ve bedeldir. Kupon bütçesi bir harcama kararıdır, "
    "veriden çıkarılmaz."
)

#: Geriye uyum: bu ad dışarıdan çağrılıyordu.
UYARI = UYARI_ESIK


#: `sezon` bu değeri alırsa kesit tek sezon değil, ölçüm kesitinin tamamıdır
#: (varsayılan sezon + `evaluate.OLCUM_SEZONLARI` = 114 hafta / 1.710 maç).
TUM_SEZONLAR = "hepsi"


def kesit_girdileri(last: int | None = None,
                    yontem: str = ARINDIRMA_VARSAYILAN,
                    sezon: str | None = None) -> list[dict[str, Any]]:
    """Geri testin kesiti — tek sezon ya da ölçüm kesitinin tamamı.

    `sezon == "hepsi"` ise `evaluate.kupon_kesiti_tum()` çağrılır. O
    fonksiyon zaten bu iş için var ve sezonları **ayrı ayrı** okuyup
    `week`i sezonla ön-ekleyerek birleştiriyor — yani `hafta_girdileri`nin
    docstring'inde uyarılan "başka sezonun oranları sessizce yapışır"
    hatası açılmıyor. İkinci bir birleştirme yazmak o hatanın ikinci bir
    kopyasını üretmek olurdu.

    İçe aktarma **tembeldir**: `evaluate` bu modülü çağırıyor, tepede
    aktarmak döngü kurardı (`secim` ve `getiri` de aynı deseni kullanıyor).
    """
    if sezon == TUM_SEZONLAR:
        if yontem != ARINDIRMA_VARSAYILAN:
            raise ValueError(
                f"{TUM_SEZONLAR!r} kesiti yalnizca varsayilan arindirmayla "
                f"({ARINDIRMA_VARSAYILAN}) kurulur; kupon_kesiti_tum yontem almiyor.")
        from .evaluate import kupon_kesiti_tum
        return list(kupon_kesiti_tum(last))
    return hafta_girdileri(last, yontem, sezon)


def backtest(last: int | None = None,
             banko_esik: float = VARSAYILAN_BANKO,
             uclu_esik: float = VARSAYILAN_UCLU,
             sweep: bool = True,
             yontem: str = ARINDIRMA_VARSAYILAN,
             sezon: str | None = None,
             strateji: str = "hedef",
             butce_tl: float = VARSAYILAN_BUTCE_TL,
             kademe: int = HEDEF_KADEME) -> dict[str, Any]:
    """Bir stratejinin kesit boyu geri testi + o stratejiye ait tarama.

    `strateji` varsayılan olarak **`hedef`**tir, yani ürünün kendi kuralı
    (`secim.en_iyi_secim`, bütçe altında `P(k ≤ 15 − kademe)`). `esik` taban
    çizgisini koşar. Ayrım çıktının şeklini de değiştirir:

    * `hedef` → `butce_sweep` (harcama kararı taraması), hold-out **yok**
    * `esik`  → `sweep` + `sweep_best` + `holdout` (ayarlanan parametre var)

    `yontem` marj arındırmasını seçer (A5); `meta.arindirma` ile çıktıda yazar
    çünkü eşikler ölçeğe bağlıdır ve hangi ölçekte ölçüldüğü sonradan
    anlaşılamazsa tablo yorumlanamaz.

    `sezon` hafta kaydını ve oran arşivini birlikte seçer; `"hepsi"` ölçüm
    kesitinin tamamını verir. `meta.sezon` ile çıktıda yazar. **Sezonu
    çıktıya yazmak şart:** tarama hangi sezonda koşulduğu bilinmeden
    okunamaz, ve arayüzde sezon sekmeler arasında taşınmazsa iki sayfa aynı
    anda iki farklı sezonu anlatır.
    """
    if strateji not in STRATEJILER:
        raise ValueError(
            f"Bilinmeyen strateji {strateji!r}; tanınanlar: {', '.join(STRATEJILER)}")
    girdiler = kesit_girdileri(last, yontem, sezon)
    elenen = [
        {"week": g["week"], "missing": g["missing"]}
        for g in girdiler if not g["usable"]
    ]
    secici = secici_uret(strateji, banko_esik, uclu_esik, butce_tl, kademe)
    haftalar = _hepsini_calistir(girdiler, secici)

    esik_ailesi = strateji == "esik"
    # Tarama ile hold-out aynı tabloyu okur; iki kez hesaplanmaz.
    tablo = izgara_tablosu(girdiler) if (sweep and esik_ailesi) else None
    tarama = esik_taramasi(girdiler, tablo=tablo) if (sweep and esik_ailesi) else []
    butce_sweep = (butce_taramasi(girdiler, kademe=kademe)
                   if (sweep and not esik_ailesi) else [])

    if esik_ailesi:
        aciklama = (f"favori olasılığı ≥ %{100 * banko_esik:.0f} ise banko, "
                    f"< %{100 * uclu_esik:.0f} ise üçlü, arası çifte")
        strateji_blok: dict[str, Any] = {
            "ad": "esik", "rol": "taban çizgisi (ürünün kuralı DEĞİL)",
            "banko": banko_esik, "uclu": uclu_esik, "explain": aciklama,
        }
    else:
        strateji_blok = {
            "ad": "hedef", "rol": "ürünün kendi kuralı",
            "butce_tl": butce_tl, "butce_kolon": butce_kolon(butce_tl),
            "kademe": kademe, "kacak_esigi": kacak_esigi(kademe),
            "explain": (f"₺{butce_tl:,.0f} tavanı altında "
                        f"P(kaçak ≤ {kacak_esigi(kademe)}) enbüyüklenir, "
                        f"yani P(en iyi kolon ≥ {kademe})"),
        }

    return {
        "meta": {
            # Hangi sezonda kosuldugu ciktida DURMALI: tarama sezon
            # bilinmeden okunamaz.
            "sezon": sezon,
            "olcek": "duz",
            "kademe": kademe,
            "kolon_bedeli_tl": KOLON_BEDELI,
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
        "strategy": strateji_blok,
        "season": _ozet(haftalar),
        "weeks": haftalar,
        "sweep": tarama,
        "sweep_best": _en_iyi(tarama),
        "butce_sweep": butce_sweep,
        "holdout": (holdout(girdiler, tablo=tablo)
                    if (sweep and esik_ailesi) else {"weeks": 0}),
        "grid": {"banko": list(BANKO_IZGARA), "uclu": list(UCLU_IZGARA),
                 "butce_tl": list(BUTCE_IZGARA)},
        "warning": UYARI_ESIK if esik_ailesi else UYARI_HEDEF,
    }
