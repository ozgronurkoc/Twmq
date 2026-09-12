"""Spor Toto tarihsel 1/0/2 istatistikleri.

Veri seti ``scripts/build_history.py`` ile kaynağından üretilir ve her hafta
kendi maç listesini (takım adları, tarih, skor) taşır. Tek doğruluk kaynağı
haftanın ``matches`` dizisidir; ``results`` ondan üretilir, ``n1/n0/n2`` de
ondan sayılır. Üçü arasındaki her tutarsızlık ``data_quality`` bloğunda
raporlanır — sessizce yutulmaz.
"""
from __future__ import annotations

import itertools
import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from .core import MAC_SAYISI, SEMBOLLER

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "st_history_2025_26.json"

#: §6G'nin urettigi sezon dosyalari. `DATA_FILE`dan AYRI durur ve ayri
#: kalmasi bilinclidir: ikisi farkli koken sinifidir (ucuncu parti payload
#: ile resmi bulten + fikstur birlestirmesi) ve 2025/26 icin ikisi de var.
SEZON_DIZIN = Path(__file__).resolve().parent.parent / "data" / "st_history"

#: Sembol duzeni ve kupon uzunlugu TEK kaynaktan (`core`). Bu iki ad
#: korunuyor cunku paketin yarisi onlari buradan import ediyor; degerin
#: kendisi artik burada tanimli DEGIL.
SYMBOLS: tuple[str, str, str] = SEMBOLLER
MATCH_COUNT = MAC_SAYISI
RECENT_WINDOW = 6

#: `sezon` bu degeri alirsa kesit tek sezon degil, SEZONLARIN BIRLESIMIDIR.
#:
#: Ayni dize `backtest.TUM_SEZONLAR` — oradan buraya tasindi ve orasi artik
#: burayi import ediyor. Iki ayri sabit tanimlamak, ayni sorgu dizesinin
#: (`?sezon=hepsi`) iki ucta iki farkli kesit anlatmasina acik kapi
#: birakirdi; tek tanim bunu yapisal olarak imkansiz kilar.
#:
#: **Iki ucun kesiti yine de AYNI DEGIL ve bu kasitli:** `/api/stats`
#: kuponun butun haftalarini sayar (122), geri test ise yalnizca oran
#: kapsamasi olanlari (`usable`, 114). Fark `evaluate.kupon_kesiti_tum`in
#: suzgecindedir, kesitin tanimlanmasinda degil.
TUM_SEZONLAR = "hepsi"

#: Varsayilan kaydin ACIK adi. Sorgu dizesinde sezon HIC verilmezse de
#: varsayilan okunur; bu ad "hicbir sey secilmedi" ile "varsayilani
#: SECTIM"i ayirir. Arayuzun secicisinde ikisi ayni tusa denk gelemez:
#: birlesik kesit artik ilk secenek ve varsayilan kayit kendi tusunda.
VARSAYILAN_KAYIT = "varsayilan"


def sezonlar() -> list[str]:
    """Secilebilir sezon anahtarlari — varsayilan (None) HARIC.

    Varsayilan liste disinda tutulur cunku o bir sezon SECIMI degil,
    "hicbir sey secilmedi" hali: `st_history_2025_26.json` 41 hafta tasir
    ve `data/st_history/2025_26.json` ayni sezonun 31 haftalik BASKA bir
    okumasidir (§6G.5). Ikisini tek listede sunmak hangisinin secildigini
    belirsizlestirirdi.
    """
    if not SEZON_DIZIN.is_dir():
        return []
    return sorted(p.stem for p in SEZON_DIZIN.glob("*.json")
                  if p.stem != "gecmis_rapor")


def birlesik_kesit() -> tuple[str | None, ...]:
    """`TUM_SEZONLAR` hangi kayitlardan kurulur — sirasi KRONOLOJIK DEGIL.

    Kaynak `evaluate.OLCUM_SEZONLARI` ve bu bilincli: o demet "hangi kupon
    sezonlari birlikte olculebilir" sorusunun **zaten verilmis** cevabidir
    ve gerekcesini kendi yaninda tasir — `2025_26` orada YOK, cunku o dosya
    varsayilan kaydin ayni sezonu ikinci kez okumasidir (§6G.5). Burada
    ikinci bir liste tutmak, o gerekcenin bir kopyasini bekcisiz birakirdi:
    biri degisir, oteki sessizce ayni sezonu iki kez sayar.

    Varsayilan kayit (None) 2025/26'yi TEMSIL EDER — 41 hafta, uc parti
    payload'i. Ayni sezonun bultenden okunan 31 haftalik kaydi birlesime
    girmez ama secilebilir olarak kalir (`?sezon=2025_26`).

    Ice aktarma TEMBEL: `evaluate` -> `backtest` -> `history` zinciri var,
    tepede aktarmak dongu kurardi (`backtest.kesit_girdileri` ayni deseni
    kullaniyor).
    """
    from .evaluate import OLCUM_SEZONLARI
    return (None, *OLCUM_SEZONLARI)


def sezon_anahtari(ham: Any) -> str | None:
    """Sorgu dizesindeki `?sezon=` degerini ic anahtara cevirir.

    Uc gecerli sekil var ve ucu de ACIK yazilir:

        ""  / None      -> None            (sezon verilmedi: varsayilan kayit)
        "varsayilan"    -> None            (varsayilan kayit, ACIKCA secildi)
        "hepsi"         -> TUM_SEZONLAR    (birlesik kesit)
        "2023_24"       -> "2023_24"       (tek sezon)

    Taninmayan deger icin `KeyError` yukselir — nobetci deger DONMEZ.
    Sessizce varsayilana dusmek bu depoda yasanmis bir hatadir: `/api/takimlar`
    taninmayan sezona 200 OK ve BOS govde donuyordu, sayfa hatasiz
    bosaliyordu. Kullanici bir sezon ISTEDI ve baska bir sezonun sayilarini
    gormek, hic sayi gormemekten kotudur.
    """
    if ham is None or str(ham).strip() == "":
        return None
    deger = str(ham).strip()
    if deger == VARSAYILAN_KAYIT:
        return None
    if deger == TUM_SEZONLAR:
        return TUM_SEZONLAR
    if deger not in sezonlar():
        raise KeyError(deger)
    return deger


def kayit_secenekleri() -> list[dict[str, Any]]:
    """Seçicinin göstereceği kayıtların TAMAMI — etiketi ve künyesiyle.

    Arayüz bu listeyi olduğu gibi basar; sezon adlarını, hangisinin
    birleşime girdiğini ya da iki kaydı birbirinden nasıl ayıracağını
    KENDİ bilmez. Gerekçe deponun kendi kuralı: arayüzde sabit liste
    tutulmaz, yoksa yeni bir sezon eklendiğinde orası bayatlar ve kimse
    görmez.

    Ayırt etme kuralı veriye bakar, sezon adına değil: aynı etikete iki
    kayıt düşerse (2025/26'nın iki okuması — §6G.5) ayıran şey **kökendir**
    ve etikete o yazılır ("2025/26 · bülten" ↔ "2025/26 · payload").
    Anahtarı (`2025_26`) buraya yazmak, aynı çakışma üçüncü bir sezonda
    çıktığında sessizce yanlış olurdu.
    """
    birlesim = set(birlesik_kesit())
    tekil: list[dict[str, Any]] = []
    for anahtar in (None, *sezonlar()):
        rows = _sezon_satirlari(anahtar)
        meta = load_history(anahtar).get("meta", {}) or {}
        koken = str(meta.get("origin") or "varsayilan kayit")
        tekil.append({
            "deger": anahtar or VARSAYILAN_KAYIT,
            "sezon": anahtar,
            "etiket": _sezon_etiketi(anahtar),
            "koken": koken,
            # Kisa koken adi etikette ayirt edici olarak kullaniliyor.
            "koken_kisa": "bülten" if koken.startswith("turetilmis") else "payload",
            "weeks": len(rows),
            "matches": sum(len(r["results"]) for r in rows),
            "date_from": rows[0]["close_date"] if rows else "",
            "date_to": rows[-1]["close_date"] if rows else "",
            # Kullanicinin ilk sordugu soru buydu: "birlesikte hangisi var?"
            "birlesimde": anahtar in birlesim,
        })
    sayim = Counter(k["etiket"] for k in tekil)
    for k in tekil:
        if sayim[k["etiket"]] > 1:
            k["etiket"] = f"{k['etiket']} · {k['koken_kisa']}"
    tekil.sort(key=lambda k: (str(k["date_from"]), k["deger"]))

    birlesik_hafta = sum(k["weeks"] for k in tekil if k["birlesimde"])
    birlesik_mac = sum(k["matches"] for k in tekil if k["birlesimde"])
    return [
        {
            "deger": TUM_SEZONLAR,
            "sezon": TUM_SEZONLAR,
            "etiket": "Tüm sezonlar",
            "koken": "birlesik kesit",
            "koken_kisa": "birleşik",
            "weeks": birlesik_hafta,
            "matches": birlesik_mac,
            "date_from": min((k["date_from"] for k in tekil if k["birlesimde"]),
                             default=""),
            "date_to": max((k["date_to"] for k in tekil if k["birlesimde"]),
                           default=""),
            "birlesimde": True,
        },
        *tekil,
    ]


@lru_cache(maxsize=8)
def load_history(sezon: str | None = None) -> dict[str, Any]:
    """Kupon hafta kaydi. `sezon` None ise BUGUNKU dosya okunur.

    Varsayilanin degismemesi bir urun karari: `/api/stats`, 27 degismez ve
    testlerin cipalari (41 hafta · 615 mac) o dosyaya bakiyor. Yeni sezonlar
    `?sezon=` ile EKLENIR, varsayilani degistirmez.

    Onbellek sezona anahtarli (`maxsize=8`); onceki surumde `maxsize=1` idi
    ve parametre eklenince ikinci sezon birincinin kaydini dusururdu.
    """
    yol = DATA_FILE if sezon is None else SEZON_DIZIN / f"{sezon}.json"
    if not yol.exists():
        return {
            "meta": {"weeks": 0, "matches": 0},
            "totals": {},
            "weekly_avg": {},
            "bands": {},
            "weeks": [],
            "error": f"Veri dosyasi yok: {yol}",
        }
    return json.loads(yol.read_text(encoding="utf-8"))


# ─── temel yardımcılar ────────────────────────────────────────────────────────

def _clean_results(raw: Any) -> str:
    """Sadece 1/0/2 karakterlerini bırakır."""
    return "".join(ch for ch in str(raw or "") if ch in SYMBOLS)


def _zero_counts() -> dict[str, int]:
    return dict.fromkeys(SYMBOLS, 0)


def _counts_of(results: str) -> dict[str, int]:
    return {s: results.count(s) for s in SYMBOLS}


def _runs(results: str) -> list[dict[str, Any]]:
    """Ardışık aynı sembol serilerini döndürür: [{symbol, start, length}]."""
    out: list[dict[str, Any]] = []
    for i, ch in enumerate(results):
        if out and out[-1]["symbol"] == ch:
            out[-1]["length"] += 1
        else:
            out.append({"symbol": ch, "start": i + 1, "length": 1})
    return out


def _max_run(results: str) -> dict[str, Any]:
    runs = _runs(results)
    if not runs:
        return {"symbol": "", "start": 0, "length": 0}
    return max(runs, key=lambda r: (r["length"], -r["start"]))


def _pct(part: float, total: float, digits: int = 4) -> float:
    return round(100.0 * part / total, digits) if total else 0.0


# ─── hafta normalizasyonu ─────────────────────────────────────────────────────

def _clean_matches(raw: Any) -> list[dict[str, Any]]:
    """Maç satırlarını normalize eder; kodu skordan yeniden türetir."""
    out: list[dict[str, Any]] = []
    for i, m in enumerate(raw or []):
        if not isinstance(m, dict):
            continue
        hg, ag = m.get("hg"), m.get("ag")
        code = ""
        if isinstance(hg, int) and isinstance(ag, int):
            code = "1" if hg > ag else "0" if hg == ag else "2"
        out.append({
            "no": int(m.get("no") or i + 1),
            "home": str(m.get("home") or ""),
            "away": str(m.get("away") or ""),
            "kickoff": str(m.get("kickoff") or ""),
            "hg": hg if isinstance(hg, int) else None,
            "ag": ag if isinstance(ag, int) else None,
            "code": code,
        })
    return out


def hafta_anahtari(sezon: str | None, week: int) -> str:
    """Bir haftanın kesitten bağımsız kimliği: ``"2023_24-12"``.

    Hafta NUMARASI tek başına kimlik değildir — dört sezonun dördünde de
    12. hafta var. Birleşik kesitte satırlar, oranın haftalık Brier'i ve
    arayüzün bağlantıları bu anahtar üzerinden buluşur; numara yalnızca
    **gösterim** için kalır.
    """
    return f"{sezon or VARSAYILAN_KAYIT}-{week}"


def _sezon_satirlari(sezon: str | None) -> list[dict[str, Any]]:
    """TEK sezonun normalize satırları, hafta numarasına göre sıralı.

    ``normalized_weeks``ün gövdesi buraya alındı: birleşik kesit aynı
    normalizasyonu sezon sezon çağırıp birleştiriyor. İkinci bir gövde
    yazmak iki normalizasyonun sessizce ayrışmasına açık kapı bırakırdı.
    """
    rows: list[dict[str, Any]] = []
    for w in load_history(sezon).get("weeks", []) or []:
        results = _clean_results(w.get("results"))
        derived = _counts_of(results)
        reported = {
            "1": int(w.get("n1") or 0),
            "0": int(w.get("n0") or 0),
            "2": int(w.get("n2") or 0),
        }
        matches = _clean_matches(w.get("matches"))
        mx = _max_run(results)
        hafta_no = int(w.get("week") or 0)
        rows.append({
            "week": hafta_no,
            # Satirin KENDI sezonu. Birlesik kesitte hafta numarasi kimlik
            # degil (dort sezonda da 12. hafta var); arayuzun baglantilari,
            # oranin haftalik Brier'i ve kopya dizi denetimi bu ikisiyle
            # eslesir. Tek sezon kesitinde de YAZILIR: govdenin sekli iki
            # kipte ayni kalsin, arayuz "hangi kipteyim" diye sormasin.
            "sezon": sezon,
            "anahtar": hafta_anahtari(sezon, hafta_no),
            "close_date": w.get("close_date") or "",
            "season": w.get("season") or "",
            "results": results,
            "n1": derived["1"],
            "n0": derived["0"],
            "n2": derived["2"],
            "counts": derived,
            "top": max(SYMBOLS, key=lambda s: (derived[s], -SYMBOLS.index(s))),
            "max_streak": mx,
            "complete": len(results) == MATCH_COUNT,
            "consistent": derived == reported,
            "reported_counts": None if derived == reported else reported,
            "matches": matches,
            # Maç listesi ile dizi birbirini tutuyor mu (sıra dahil).
            "matches_match_results": bool(matches) and "".join(
                m["code"] for m in matches
            ) == results,
        })
    rows.sort(key=lambda r: r["week"])
    return rows


def normalized_weeks(last: int | None = None,
                     sezon: str | None = None) -> list[dict[str, Any]]:
    """Normalize hafta listesi — tek sezon ya da (``"hepsi"``) birleşim.

    ``last`` verilirse sadece son N hafta döner (istatistik dilimleme için).
    ``sezon`` bir anahtarsa o sezonun dosyası okunur, ``TUM_SEZONLAR`` ise
    ``birlesik_kesit()``in tamamı okunup **kronolojik** sıralanır,
    verilmezse varsayılan kayıt.

    ─── Birleştirme neden uzun süre YASAKTI, ve ne değişti ────────────────

    Bu fonksiyonun docstring'i *"sezonlar BİRLEŞTİRİLMEZ, seçilir"* diyordu
    ve gerekçesi gerçekti: ``week`` bu modülde küresel bir birincil anahtar
    gibi kullanılıyordu — sıralama, ``history_week_detail`` araması, oran
    arşivinin ``(week, no)`` haritası, arayüzün hafta bağlantıları ve
    ``duplicate_results``un çakışma denetimi. Dört sezonu tek listeye koymak
    beşini birden bozardı ("30. hafta" hangi sezonun?).

    Yasak kalkmadı, **koşulu karşılandı**: her satır artık kendi ``sezon``
    anahtarını ve ``anahtar``ını (``"2023_24-12"``) taşıyor. Beş kullanımın
    beşi de numaradan bu kimliğe geçti; numara yalnızca gösterimde kaldı.
    Karşılanmamış tek şey ``history_week_detail``dır ve o **bilerek** tek
    sezonda durur: "41 haftanın 7.si" gibi bir sıralama iki sezon
    karışmadan anlamlıdır (``/api/stats/<hafta>`` birleşik kesiti 400 ile
    reddeder, sessizce bir sezon SEÇMEZ).

    Birleşimde 2025/26 **bir kez** sayılır: ``birlesik_kesit()`` varsayılan
    kaydı alır, aynı sezonun bültenden okunan ikinci kaydını (§6G.5) almaz.
    """
    if sezon == TUM_SEZONLAR:
        # Tembel: `evaluate` bu modulu import ediyor (backtest uzerinden).
        from .evaluate import kronolojik_anahtar
        rows: list[dict[str, Any]] = []
        for anahtar in birlesik_kesit():
            rows.extend(_sezon_satirlari(anahtar))
        # Kronoloji SEZON SIRASINDAN gelmez: sezonlar zaman icinde
        # ust uste binmiyor ama bunu varsaymak bir kabul olurdu. Sira
        # `close_date`ten, esitlikte hafta numarasindan cikar —
        # `evaluate.kronolojik_anahtar` tam olarak bunu yapiyor ve
        # eksik/bozuk `week` degerinde cokmuyor.
        rows.sort(key=kronolojik_anahtar)
    else:
        rows = _sezon_satirlari(sezon)
    if last is not None and last > 0:
        rows = rows[-last:]
    return rows


def _band(values: Sequence[int]) -> dict[str, Any]:
    if not values:
        return {
            "avg": 0.0, "min": 0, "max": 0, "median": 0.0, "std": 0.0,
            "above_n": 0, "below_n": 0, "above_mean": 0.0, "below_mean": 0.0,
            "above_gap": 0.0, "below_gap": 0.0,
        }
    avg = statistics.fmean(values)
    above = [v for v in values if v > avg]
    below = [v for v in values if v <= avg]
    above_mean = statistics.fmean(above) if above else avg
    below_mean = statistics.fmean(below) if below else avg
    return {
        "avg": round(avg, 4),
        "min": min(values),
        "max": max(values),
        "median": round(statistics.median(values), 4),
        "std": round(statistics.pstdev(values), 4),
        "above_n": len(above),
        "below_n": len(below),
        "above_mean": round(above_mean, 4),
        "below_mean": round(below_mean, 4),
        "above_gap": round(above_mean - avg, 4),
        "below_gap": round(avg - below_mean, 4),
    }


def _kimlik(w: dict[str, Any]) -> dict[str, Any]:
    """Bir haftayı kusur listelerinde ANAN kayıt: numara + sezon + anahtar.

    Bu listeler önce düz hafta numarasıydı. Tek sezonda doğruydu; birleşik
    kesitte "12. hafta tutarsız" cümlesi **dört sezonun dördünü birden**
    gösterebilirdi ve okuyanın hangisi olduğunu anlamasının yolu yoktu.
    Kusur raporu belirsiz olamaz (doktrin 4): kimlik satırın kendisiyle
    birlikte taşınır.
    """
    return {"week": w["week"], "sezon": w["sezon"], "anahtar": w["anahtar"]}


def _data_quality(weeks: Iterable[dict[str, Any]]) -> dict[str, Any]:
    weeks = list(weeks)
    conflicts = [
        {
            "week": w["week"],
            "sezon": w["sezon"],
            "anahtar": w["anahtar"],
            "close_date": w["close_date"],
            "reported": w["reported_counts"],
            "derived": w["counts"],
        }
        for w in weeks if not w["consistent"]
    ]
    incomplete = [_kimlik(w) for w in weeks if not w["complete"]]
    # Maç listesi taşımayan ya da listesi diziyle örtüşmeyen haftalar.
    without_matches = [_kimlik(w) for w in weeks if not w["matches"]]
    match_conflicts = [
        _kimlik(w) for w in weeks if w["matches"] and not w["matches_match_results"]
    ]
    # Anahtar (sezon, dizi): aynı 1/0/2 dizisinin İKİ FARKLI SEZONDA çıkması
    # bir kusur değildir — 15 maçlık bir dizinin 3^15 olasılığı var ama
    # sezonlar birbirinden bağımsız kuponlardır ve tekrar orada olağandır.
    # Kusur, AYNI sezonda aynı dizinin iki kez görünmesidir (§7.4'ün v1
    # vakası tam olarak buydu). Sezonsuz gruplama birleşik kesitte yanlış
    # çakışma raporlardı.
    by_results: dict[tuple[str | None, str], list[int]] = defaultdict(list)
    for w in weeks:
        if w["results"]:
            by_results[(w["sezon"], w["results"])].append(w["week"])
    duplicates = [
        {"results": r, "sezon": sz, "weeks": sorted(ws)}
        for (sz, r), ws in by_results.items() if len(ws) > 1
    ]
    duplicates.sort(key=lambda d: (str(d["sezon"] or ""), d["weeks"][0]))
    return {
        "source": "matches",
        "weeks_total": len(weeks),
        "weeks_with_matches": sum(1 for w in weeks if w["matches"]),
        "count_conflicts": conflicts,
        "match_conflicts": match_conflicts,
        "weeks_without_matches": without_matches,
        "incomplete_weeks": incomplete,
        "duplicate_results": duplicates,
        "ok": not conflicts and not incomplete and not duplicates
        and not match_conflicts and not without_matches,
    }


# ─── özet ─────────────────────────────────────────────────────────────────────

def _sezon_etiketi(sezon: str | None) -> str:
    """`"2023_24"` -> `"2023/24"`; varsayılan kayıt kendi sezon adını verir."""
    if sezon is None:
        ham = str(load_history(None).get("meta", {}).get("season") or "")
        # "2025/2026" -> "2025/26"; meta'da yoksa adı olduğu gibi bırak.
        parcalar = ham.split("/")
        if len(parcalar) == 2 and len(parcalar[1]) == 4:
            return f"{parcalar[0]}/{parcalar[1][2:]}"
        return ham or VARSAYILAN_KAYIT
    bas, _, son = sezon.partition("_")
    return f"{bas}/{son}" if son else sezon


def _birlesim_dokumu() -> list[dict[str, Any]]:
    """Birleşik kesitin hangi kayıttan kaç hafta aldığı — kesitin künyesi.

    Arayüz bunu satır satır basar. Toplam bir sayı ("122 hafta") nereden
    geldiğini söylemez; bu döküm söyler ve 2025/26'nın **bir kez**
    sayıldığı buradan görünür.
    """
    out: list[dict[str, Any]] = []
    for anahtar in birlesik_kesit():
        rows = _sezon_satirlari(anahtar)
        meta = load_history(anahtar).get("meta", {}) or {}
        out.append({
            "sezon": anahtar,
            "deger": anahtar or VARSAYILAN_KAYIT,
            "etiket": _sezon_etiketi(anahtar),
            "weeks": len(rows),
            "matches": sum(len(r["results"]) for r in rows),
            "date_from": rows[0]["close_date"] if rows else "",
            "date_to": rows[-1]["close_date"] if rows else "",
            "origin": meta.get("origin", "varsayilan kayit"),
        })
    # Sira KRONOLOJIK, `birlesik_kesit()`in sirasi degil: o demet
    # varsayilan kaydi (2025/26) basa koyuyor ve dokum "2025/26 → 2024/25"
    # diye okunurdu. Kesitin kendisi zaman siralidir, kunyesi de oyle olmali.
    out.sort(key=lambda d: str(d["date_from"]))
    return out


def _birlesik_meta(weeks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """`?sezon=hepsi` için künye — tek dosya olmadığı için elde kurulur."""
    dokum = _birlesim_dokumu()
    etiketler = [d["etiket"] for d in dokum]
    return {
        "season": f"{etiketler[0]} → {etiketler[-1]}" if etiketler else "",
        "sezon_sayisi": len(dokum),
        "birlesim": dokum,
        # Bu iki metin ARAYUZDE gorunur (kartin ipucu ve "Veri kalitesi"
        # basligi), o yuzden duzgun Turkce yaziliyor — kaynak dosyalarin
        # kendi ASCII `source`/`rule` alanlarindan farkli olmasinin sebebi bu.
        "source": ("birleşik kesit: varsayılan kayıt (üçüncü parti payload) + "
                   "bültenden fikstüre bağlanan sezonlar (§6F, §6G)"),
        "rule": ("her kayıt bir kez sayılır; 2025/26'nın bültenden okunan "
                 "ikinci kaydı (§6G.5) birleşime GİRMEZ, ayrı seçilir"),
        "generated_at": "",
    }


def history_summary(last: int | None = None,
                    sezon: str | None = None) -> dict[str, Any]:
    birlesik = sezon == TUM_SEZONLAR
    data = {} if birlesik else load_history(sezon)
    weeks = normalized_weeks(last, sezon)
    n_weeks = len(weeks)
    matches = sum(len(w["results"]) for w in weeks)

    totals: dict[str, Any] = {s: sum(w["counts"][s] for w in weeks) for s in SYMBOLS}
    for s in SYMBOLS:
        totals[f"pct_{s}"] = _pct(totals[s], matches)

    weekly_avg = {
        s: round(totals[s] / n_weeks, 4) if n_weeks else 0.0
        for s in SYMBOLS
    }
    bands = {s: _band([w["counts"][s] for w in weeks]) for s in SYMBOLS}

    meta = dict(_birlesik_meta(weeks) if birlesik else (data.get("meta", {}) or {}))
    meta.update({
        "weeks": n_weeks,
        "matches": matches,
        # Birlesik kesitte hafta NUMARASI aralik anlatmaz: dort sezonun
        # numaralari ic ice gecer ve "2-51. haftalar" yanlis okunurdu.
        # `None` bosluk degil bir cevaptir — arayuz o rozeti hic basmaz ve
        # yerine sezon dokumunu gosterir.
        "week_from": None if birlesik else (weeks[0]["week"] if weeks else None),
        "week_to": None if birlesik else (weeks[-1]["week"] if weeks else None),
        "sliced": bool(last and last > 0 and last < len(normalized_weeks(sezon=sezon))),
        # Hangi kaydin okundugu payload'da GORUNMELI: 2025/26 icin iki ayri
        # koken var (§6G.5) ve ikisi farkli hafta sayisi tasiyor.
        "sezon_secimi": sezon,
        "origin": ("birlesik kesit" if birlesik
                   else data.get("meta", {}).get("origin", "varsayilan kayit")),
    })
    if weeks:
        meta["date_from"] = weeks[0]["close_date"] or meta.get("date_from")
        meta["date_to"] = weeks[-1]["close_date"] or meta.get("date_to")

    return {
        "meta": meta,
        "totals": totals,
        "weekly_avg": weekly_avg,
        "bands": bands,
        "week_count": n_weeks,
        "data_quality": _data_quality(weeks),
        "error": data.get("error"),
    }


def history_weeks(last: int | None = None,
                  sezon: str | None = None) -> list[dict[str, Any]]:
    return normalized_weeks(last, sezon)


# ─── analitik bloklar ─────────────────────────────────────────────────────────

def position_stats(weeks: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Maç sırasına (1..15) göre 1/0/2 dağılımı."""
    out: list[dict[str, Any]] = []
    for pos in range(MATCH_COUNT):
        counts = _zero_counts()
        for w in weeks:
            if pos < len(w["results"]):
                counts[w["results"][pos]] += 1
        n = sum(counts.values())
        out.append({
            "pos": pos + 1,
            "counts": counts,
            "pct": {s: _pct(counts[s], n, 2) for s in SYMBOLS},
            "n": n,
            "top": max(SYMBOLS, key=lambda s: (counts[s], -SYMBOLS.index(s))) if n else "",
        })
    return out


def transition_stats(weeks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Hafta içinde ardışık maçlarda sembol geçiş matrisi (3x3)."""
    counts: dict[str, dict[str, int]] = {s: _zero_counts() for s in SYMBOLS}
    for w in weeks:
        r = w["results"]
        for a, b in itertools.pairwise(r):
            counts[a][b] += 1
    total = sum(sum(row.values()) for row in counts.values())
    pct = {
        a: {b: _pct(counts[a][b], sum(counts[a].values()), 2) for b in SYMBOLS}
        for a in SYMBOLS
    }
    repeat = sum(counts[s][s] for s in SYMBOLS)
    return {
        "counts": counts,
        "pct": pct,
        "row_totals": {a: sum(counts[a].values()) for a in SYMBOLS},
        "n": total,
        "repeat_pct": _pct(repeat, total, 2),
    }


def count_distribution(weeks: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Her sembol için 'kaç haftada k adet çıktı' histogramı."""
    n = len(weeks)
    out: dict[str, list[dict[str, Any]]] = {}
    hi = 0
    per: dict[str, Counter] = {}
    for s in SYMBOLS:
        c = Counter(w["counts"][s] for w in weeks)
        per[s] = c
        hi = max([hi, *list(c)])
    for s in SYMBOLS:
        out[s] = [
            {"count": k, "weeks": per[s].get(k, 0), "pct": _pct(per[s].get(k, 0), n, 2)}
            for k in range(0, hi + 1)
        ]
    return out


def streak_stats(weeks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Hafta içi en uzun aynı-sembol serileri."""
    best: dict[str, dict[str, Any]] = {
        s: {"length": 0, "week": None, "start": 0, "sezon": None, "anahtar": ""}
        for s in SYMBOLS
    }
    all_runs: list[dict[str, Any]] = []
    for w in weeks:
        for run in _runs(w["results"]):
            item = {
                "week": w["week"], "symbol": run["symbol"],
                "start": run["start"], "length": run["length"],
                # Sezon kimligi: arayuz bu satirdan bir BAGLANTI kuruyor
                # ve birlesik kesitte numara tek basina yanlis haftaya
                # goturur.
                "sezon": w["sezon"], "anahtar": w["anahtar"],
                "close_date": w["close_date"],
            }
            all_runs.append(item)
            s = run["symbol"]
            if run["length"] > best[s]["length"]:
                best[s] = {"length": run["length"], "week": w["week"],
                           "start": run["start"], "sezon": w["sezon"],
                           "anahtar": w["anahtar"]}
    # Siralama KRONOLOJIK: esit uzunluktaki seriler arasinda once erken
    # hafta. `week` tek basina birlesik kesitte dort sezonu karistirirdi;
    # `anahtar` ise metin sirasi verir ("...-12" < "...-7") ve tek sezonda
    # bugunku siralamayi degistirirdi. Tarih ikisini de cozer.
    all_runs.sort(key=lambda r: (-r["length"], r["close_date"], r["week"], r["start"]))
    avg_max = (
        round(statistics.fmean([w["max_streak"]["length"] for w in weeks]), 2)
        if weeks else 0.0
    )
    return {"by_symbol": best, "top": all_runs[:8], "avg_week_max": avg_max}


def extreme_weeks(weeks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Her sembol için en yüksek/en düşük haftalar."""
    out: dict[str, Any] = {}
    for s in SYMBOLS:
        if not weeks:
            out[s] = {"max": None, "min": None}
            continue
        # Esitlikte kronoloji karar verir (`max` en gec, `min` en erken
        # haftayi secer). Tek sezonda bu, eski `week` kirilimiyla ayni
        # sonucu verir — tarih hafta numarasiyla birlikte artiyor.
        hi = max(weeks, key=lambda w: (w["counts"][s], w["close_date"], w["week"]))
        lo = min(weeks, key=lambda w: (w["counts"][s], w["close_date"], w["week"]))
        # `sezon`/`anahtar` bagli: arayuz bu uctan hafta detayina gidiyor.
        out[s] = {
            "max": {"week": hi["week"], "value": hi["counts"][s],
                    "results": hi["results"], "sezon": hi["sezon"],
                    "anahtar": hi["anahtar"]},
            "min": {"week": lo["week"], "value": lo["counts"][s],
                    "results": lo["results"], "sezon": lo["sezon"],
                    "anahtar": lo["anahtar"]},
        }
    return out


def recent_form(weeks: Sequence[dict[str, Any]], window: int = RECENT_WINDOW) -> dict[str, Any]:
    """Son N haftanın ortalaması ve sezon ortalamasına göre sapması."""
    if not weeks:
        return {"window": 0, "weeks": [], "avg": _zero_counts(), "delta": _zero_counts()}
    tail = list(weeks[-window:])
    season_avg = {s: statistics.fmean([w["counts"][s] for w in weeks]) for s in SYMBOLS}
    tail_avg = {s: statistics.fmean([w["counts"][s] for w in tail]) for s in SYMBOLS}
    return {
        "window": len(tail),
        "weeks": [w["week"] for w in tail],
        # Numaralar birlesik kesitte tek basina hangi sezon oldugunu
        # soylemiyor; anahtar soyluyor. Ikisi birden yaziliyor ki
        # gosterim (numara) ile kimlik (anahtar) karismasin.
        "anahtarlar": [w["anahtar"] for w in tail],
        "avg": {s: round(tail_avg[s], 2) for s in SYMBOLS},
        "delta": {s: round(tail_avg[s] - season_avg[s], 2) for s in SYMBOLS},
    }


def history_analytics(last: int | None = None,
                      sezon: str | None = None) -> dict[str, Any]:
    weeks = normalized_weeks(last, sezon)
    return {
        "positions": position_stats(weeks),
        "transitions": transition_stats(weeks),
        "distribution": count_distribution(weeks),
        "streaks": streak_stats(weeks),
        "extremes": extreme_weeks(weeks),
        "recent": recent_form(weeks),
    }


# ─── tek hafta ────────────────────────────────────────────────────────────────

def _hafta_indeksi(weeks: Sequence[dict[str, Any]], week: int) -> int | None:
    """Hafta numarasının listedeki yeri — bulunamazsa `None`.

    Arama TEK yerde. `history_week` satırı, `history_week_detail` ise
    **indeksi** istiyor (komşu haftalar `weeks[i±1]`den geliyor), yani biri
    ötekini çağıramaz; ama ikisi de aynı aramayı yapıyordu ve iki ayrı
    gövdeydi. Ortak olan arama, ayrışan ise ondan ne istendiği.

    Varsayılanlı `next()` bilinçli: varsayılansız hâli eşleşme yoksa
    `StopIteration` yükseltir ve o, çağıran uçta HTTP 500 olarak görünürdü.
    """
    return next((i for i, w in enumerate(weeks) if w["week"] == week), None)


def _tek_sezon_sart(sezon: str | None) -> None:
    """Birleşik kesitte tek hafta sorgusu ANLAMSIZDIR — sessizce seçmeyiz.

    "12. hafta" birleşik kesitte dört sezonun dördünde de var. Bir tanesini
    seçmek doktrin 4'ün yasakladığı şeydir (belirsiz veri uydurulmaz);
    çağıran uç bunu 400 ile bildirir, `?sezon=` ile bir sezon istenir.
    """
    if sezon == TUM_SEZONLAR:
        raise ValueError(
            f"tek hafta sorgusu {TUM_SEZONLAR!r} kesitinde yapilamaz: "
            "hafta numarasi sezonlar arasinda benzersiz degil")


def history_week(week: int, sezon: str | None = None) -> dict[str, Any] | None:
    """Tek haftanın normalize edilmiş satırı; yoksa `None`."""
    _tek_sezon_sart(sezon)
    weeks = normalized_weeks(sezon=sezon)
    idx = _hafta_indeksi(weeks, week)
    return weeks[idx] if idx is not None else None


def history_week_detail(week: int,
                        sezon: str | None = None) -> dict[str, Any] | None:
    """Tek hafta + komşular + sezon ortalamasına göre konum.

    ``rank`` ve ``season_avg`` **seçilen sezonun içinde** hesaplanır; sezonlar
    birleştirilmediği için "41 haftanın 7.si" gibi bir sayı iki sezon
    karışmadan kalır.
    """
    _tek_sezon_sart(sezon)
    weeks = normalized_weeks(sezon=sezon)
    idx = _hafta_indeksi(weeks, week)
    if idx is None:
        return None
    w = dict(weeks[idx])
    n = len(weeks)
    season_avg = {
        s: round(statistics.fmean([x["counts"][s] for x in weeks]), 4) for s in SYMBOLS
    } if n else _zero_counts()

    ranks: dict[str, Any] = {}
    for s in SYMBOLS:
        ordered = sorted(weeks, key=lambda x: (-x["counts"][s], x["week"]))
        # Konum haritasi: varsayilansiz `next()` sira icinde tarardi ve
        # eslesme bulunmazsa StopIteration -> HTTP 500 verirdi. `week`in
        # listede oldugu yukarida (`idx`) cozuldu ve `ordered` ayni
        # listenin permutasyonu, yani arama tanim geregi basarili.
        konum = {x["week"]: i for i, x in enumerate(ordered)}
        ranks[s] = {"rank": konum[week] + 1, "of": n}

    w.update({
        "prev_week": weeks[idx - 1]["week"] if idx > 0 else None,
        "next_week": weeks[idx + 1]["week"] if idx < n - 1 else None,
        "cells": [
            {"pos": i + 1, "symbol": ch} for i, ch in enumerate(w["results"])
        ],
        "runs": _runs(w["results"]),
        "season_avg": season_avg,
        "delta_vs_avg": {
            s: round(w["counts"][s] - season_avg[s], 2) for s in SYMBOLS
        },
        "rank": ranks,
        "position_stats": position_stats(weeks),
    })
    return w
