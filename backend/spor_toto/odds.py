"""Oran arşivi okuyucu.

``scripts/build_odds.py`` ile üretilen arşivi okur.

**Arayüze yalnızca MAÇ SONUCU (1X2) çıkar.** Bu modül bir zamanlar hiçbir
API ucuna bağlı değildi ve baş yorumu hâlâ öyle diyordu; artık öyle değil:
``web_app`` ``week_1x2``i, ``payloads.stats_payload`` ``season_1x2_summary``i
ve ``backtest`` ``match_1x2``yi çağırıyor. Arşivdeki **diğer pazarlar**
(2,5 alt/üst, Asya handikap) ve maç istatistikleri API'ye hiç girmez;
onlar analiz için durur.

    from spor_toto.odds import load_odds, market_odds
    rows = load_odds()                       # maç başına tek satır
    p = market_odds(rows[0], "1X2", "Avg")   # {"1": 7.03, "0": 4.67, "2": 1.39}

Kaynak: football-data.co.uk piyasa oranları — **iddaa oranları değildir**
(gerekçe: docs/VERI_TOPLAMA_VE_ISLEME.md §3.2).
"""
from __future__ import annotations

import csv
import math
import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from .core import SEMBOLLER as _SEMBOLLER
from .ortak import BRIER_ESIT, brier

ODDS_FILE = Path(__file__).resolve().parent.parent / "data" / "odds" / "odds_2025_26.csv"

KIMLIK_ALANLARI = {
    "week", "no", "kickoff", "home", "away", "hg", "ag", "code",
    "kaynak_dosya", "kaynak_lig", "kaynak_ev", "kaynak_dep", "guven",
}

_SAYI = re.compile(r"^-?\d+(\.\d+)?$")


def _sayi(ham: str) -> float | None:
    ham = (ham or "").strip()
    return float(ham) if _SAYI.match(ham) else None


@lru_cache(maxsize=1)
def load_odds(path: str | None = None) -> list[dict[str, Any]]:
    """Arşivi satır satır okur. Dosya yoksa boş liste döner (hata değil)."""
    yol = Path(path) if path else ODDS_FILE
    if not yol.exists():
        return []
    out: list[dict[str, Any]] = []
    with open(yol, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            oranlar = {
                k: v for k, v in r.items()
                if k not in KIMLIK_ALANLARI and not k.startswith("stat_")
                and _sayi(v) is not None
            }
            out.append({
                "week": int(r["week"]),
                "no": int(r["no"]),
                "kickoff": r["kickoff"],
                "home": r["home"],
                "away": r["away"],
                "hg": int(r["hg"]) if r["hg"] else None,
                "ag": int(r["ag"]) if r["ag"] else None,
                "code": r["code"],
                "matched": bool(r["kaynak_dosya"]),
                "confidence": _sayi(r["guven"]) or 0.0,
                "source": {"file": r["kaynak_dosya"], "league": r["kaynak_lig"],
                           "home": r["kaynak_ev"], "away": r["kaynak_dep"]},
                "odds": {k: float(v) for k, v in oranlar.items()},
                "stats": {k[5:]: float(v) for k, v in r.items()
                          if k.startswith("stat_") and _sayi(v) is not None},
            })
    return out


def odds_for(week: int, no: int) -> dict[str, Any] | None:
    for r in load_odds():
        if r["week"] == week and r["no"] == no:
            return r
    return None


#: Arşivin **omurga fiyatı**. Bu string on ayrı yerde tekrarlanıyordu
#: (`market_odds` varsayılanı, `KAYNAK_SIRASI`, `pazar` ve birkaç betik) ve
#: hiçbirinde niçin o olduğu yazmıyordu; yani projenin en belirleyici
#: seçimi isimsizdi. Çağıranlar artık bu sabiti içe aktarır.
#:
#: **Niçin Avg, niçin Pinnacle değil.** 2026-08'de üç aday ölçüldü
#: (`scripts/fiyat_kaynaklari.py` bunu her koşumda yeniden üretir):
#:
#:     fiyat       kapsama   15 maçı tam hafta   marj      Brier*
#:     Avg           %92          36 / 41       %7,99     0,5515
#:     Pinnacle      %40          15 / 41       %3,73     0,5522
#:     Betfair Exc.  %94          32 / 41       %0,71     0,5508
#:     (*) yalnızca üçünün de bulunduğu 247 maç üzerinde
#:
#: İki sebep Avg'yi omurgada tutuyor:
#:
#: 1. **football-data, 2026-01'de Pinnacle yayımlamayı bıraktı.** Eksiklik
#:    rastgele değil, zamana bağlı: Şubat–Mayıs 2026 tamamen boş. Pinnacle'a
#:    geçmek örneklemi küçültmekle kalmaz, sezonun ikinci yarısını düşürür
#:    ve geri testi 36 haftadan 15'e indirir.
#: 2. **Marj arındırıldıktan sonra üçü ayırt edilemiyor** — ortalama fark
#:    0,70–0,86 puan ve Brier farkları gürültü içinde (Avg, Pinnacle'ın
#:    önünde bile çıkıyor). Yani geçiş, 21 haftayı ölçülebilir hiçbir
#:    doğruluk kazancı olmadan feda ederdi.
#:
#: Pinnacle ve Betfair **atılmadı**: var oldukları yerde paralel iz olarak
#: ölçülür (`spor_toto.fiyatlar`). Omurga olmamaları, görünmez olmaları
#: demek değildir.
FIYAT_VARSAYILAN = "Avg"


def market_odds(row: dict[str, Any], market: str = "1X2",
                book: str = FIYAT_VARSAYILAN,
                closing: bool = True) -> dict[str, float]:
    """Bir maçın tek pazarını sembol anahtarlı sözlüğe indirger.

    market: "1X2" | "2.5" | "AH"  ·  book: "Avg", "Max", "B365", "PS", …
    """
    ek = "C" if closing else ""
    if market == "1X2":
        harf = {"1": "H", "0": "D", "2": "A"}
        return {s: row["odds"][f"{book}{ek}{h}"]
                for s, h in harf.items() if f"{book}{ek}{h}" in row["odds"]}
    if market == "2.5":
        return {ad: row["odds"][f"{book}{ek}{sim}2.5"]
                for ad, sim in (("ust", ">"), ("alt", "<"))
                if f"{book}{ek}{sim}2.5" in row["odds"]}
    if market == "AH":
        return {s: row["odds"][f"{book}{ek}AH{h}"]
                for s, h in (("1", "H"), ("2", "A"))
                if f"{book}{ek}AH{h}" in row["odds"]}
    return {}


#: Marj arındırma yöntemleri ve projenin varsayılanı.
#:
#: Varsayılan **2026-08'de `orantili`dan `shin`e çevrildi** (A5, bkz.
#: `docs/ISTATISTIK_YOL_HARITASI.md` §3.18). Gerekçe ölçüm: orantısal
#: yöntem marjı her sonuca eşit dağıtır, oysa bahisçi onu sürprizlere ağır
#: yükler; sonuç favorinin sistematik olarak eksik fiyatlanmasıydı.
#:
#:     Brier            0,5940 → 0,5936 · −0,00035 [−0,00049, −0,00021]
#:     sapan bant       10/15 → 4/15
#:     geri test kolon  6.897/hafta → 2.228/hafta (hold-out)
#:
#: Çevrimden ÖNCE yayımlanmış sayılar orantısal ölçekte ölçülmüştür ve
#: yenileriyle doğrudan kıyaslanamaz; ikisi de belgede o etiketle durur.
ARINDIRMA_YONTEMLERI = ("orantili", "guc", "shin")
ARINDIRMA_VARSAYILAN = "shin"

#: Kök bulucu tarama sınırları ve adım sayısı. 60 ikiye bölme, çift
#: duyarlıkta ulaşılabilir hassasiyetin ötesindedir; sabit tutuldu ki
#: sonuç makineden makineye oynamasın.
_ARINDIRMA_ADIM = 60

#: Arındırma önbelleğinin boyu. Korpusta 126.274 eşsiz oran üçlüsü var
#: (217.701 çağrının %42'si tekrar); tavan onun üstünde tutuldu ki tek bir
#: korpus geçişi kendi kendini tahliye etmesin. Sınırsız DEĞİL: `implied_probs`
#: dışarıdan gelen oranla da çağrılır ve önbellek bir bellek sızıntısı olmamalı.
_ONBELLEK_BOYU = 1 << 18


def implied_probs(oranlar: dict[str, float],
                  yontem: str = ARINDIRMA_VARSAYILAN) -> dict[str, float]:
    """Marjı (overround) atarak oranları 1'e normalize edilmiş olasılığa çevirir.

    Üç yöntem var ve **hangisinin seçildiği sonucu değiştirir**:

    ``orantili``
        Eski varsayılan. ``p = (1/o) / Σ(1/o)``; marjı her sonuca eşit
        oranda dağıtır.
        Basit ve tersine çevrilebilir, ama bahisçi marjı sürprizlere daha
        çok yüklediği için favoriyi **sistematik olarak eksik fiyatlar**
        (favourite–longshot yanlılığı). Korpusta ölçüldü: piyasanın %70–80
        dediği maçlar gerçekte %78,9 geliyor (n=1.702).
    ``guc``
        ``p ∝ (1/o)^k``, ``k`` toplamı 1 yapacak şekilde çözülür. ``k>1``
        çıkar ve küçük olasılıkları büyüklerden daha çok kısar.
    ``shin``
        **Varsayılan.** Shin (1993): bahisçinin marjını, bilgili bahisçi
        payı ``z`` ile açıklar. Güç yöntemiyle aynı yönde ama daha yumuşak
        düzeltir; ikisi ölçümde ayırt edilemedi, kapalı formu olan seçildi.

    Marj sıfıra giderken üç yöntem de aynı sonuca yakınsar; ayrıştıkları yer
    yüksek marjdır — iddaa bülteni (~%18) tam olarak orası.

    Hesabın kendisi `_arindirilmis` içinde ve **önbelleklidir**; burada
    çağırana her seferinde taze bir sözlük verilir, çünkü önbellekteki kayıt
    paylaşılır ve bir çağıranın onu değiştirmesi ötekini bozardı.
    """
    return dict(_arindirilmis(tuple(oranlar.items()), yontem))


#: **Ölçülmüş sıcak nokta.** `shin` kök bulucusu 60 ikiye bölme adımı koşar
#: ve her adım üç karekök alır; korpus üzerinde profillendiğinde
#: `korpus_haftalari`nin süresinin **%92'si** buradaydı (217.685 çağrı,
#: 39,7 sn) ve korpusta aynı oran üçlüsü %42 oranında tekrar ediyordu.
#:
#: Önbellek sonucu **bit birebir** korur — aynı girdi, aynı kayan nokta
#: işlemleri. Adım sayısını düşürmek ya da `_dagilim`in içindeki sabitleri
#: dışarı almak da hızlandırırdı ama ikisi de son basamağı oynatabilirdi;
#: yayımlanmış ölçümlerin arkasındaki sayılar değişmemeli.
@lru_cache(maxsize=_ONBELLEK_BOYU)
def _arindirilmis(cift: tuple[tuple[str, float], ...],
                  yontem: str) -> tuple[tuple[str, float], ...]:
    """`implied_probs`in saf çekirdeği — yalnızca önbelleklenebilsin diye ayrı.

    Arındırma **saf**tır: aynı oran üçlüsü hep aynı olasılığı verir. Shin kök
    bulucusu çağrı başına 61 kez üç elemanlı bir vektör kuruyor (~61 µs,
    orantısal yöntemin 54 katı) ve korpusta aynı üçlü ortalama iki kez geçiyor
    — ikinci kez hesaplamanın hiçbir karşılığı yok.

    Anahtar `oranlar.items()` sırasını **korur**. Sıralasaydık dönen sözlüğün
    anahtar sırası değişir ve JSON gövdelerinin alan sırası sessizce oynardı;
    korpus üçlüleri zaten hep ("1", "0", "2") sırasında kurulduğu için sıra
    korunurken isabetten de bir şey kaybedilmiyor.

    Sözlük yerine ikili demeti döner: önbellekte duran nesne **değişmez**
    olmalı, yoksa çağıranlardan biri ötekinin sonucunu yazabilirdi.
    """
    oranlar = dict(cift)
    ters = {k: 1.0 / v for k, v in oranlar.items() if v and v > 0}
    toplam = sum(ters.values())
    if toplam <= 0:
        return ()
    if yontem == "orantili":
        return tuple((k, v / toplam) for k, v in ters.items())
    if yontem == "guc":
        ham = _arindir_guc(ters, toplam)
    elif yontem == "shin":
        ham = _arindir_shin(ters, toplam)
    else:
        raise ValueError(
            f"bilinmeyen arındırma yöntemi: {yontem!r} "
            f"(seçenekler: {', '.join(ARINDIRMA_YONTEMLERI)})")
    # Kök bulucunun bıraktığı son kırıntı da atılır: çağıran taraf
    # olasılıkların tam olarak 1'e toplandığına güvenebilmeli.
    kalan = sum(ham.values())
    if kalan <= 0:
        return ()
    return tuple((k, v / kalan) for k, v in ham.items())


def _arindir_guc(ters: dict[str, float], toplam: float) -> dict[str, float]:
    """``p ∝ (1/o)^k``; ``k`` ikiye bölmeyle çözülür.

    ``Σ(1/o)^k`` ``k``'ye göre kesin azalandır (her taban 1'den küçük), yani
    kök tektir ve ikiye bölme güvenlidir — Newton'un ıraksama riski yok.
    """
    if toplam <= 1.0:
        return dict(ters)
    q = list(ters.values())
    alt, ust = 1.0, 8.0
    for _ in range(_ARINDIRMA_ADIM):
        k = (alt + ust) / 2
        if sum(x ** k for x in q) > 1.0:
            alt = k
        else:
            ust = k
    k = (alt + ust) / 2
    return {s: v ** k for s, v in ters.items()}


def _arindir_shin(ters: dict[str, float], toplam: float) -> dict[str, float]:
    """Shin (1993) marj arındırması.

    ``p_i = (√(z² + 4(1−z)·q_i²/Σq) − z) / (2(1−z))``; ``z`` toplamı 1 yapan
    bilgili-bahisçi payıdır. ``z=0`` orantısal yöntemin kendisidir, yani
    marjsız oranda ikisi çakışır.
    """
    if toplam <= 1.0:
        return dict(ters)
    q = list(ters.values())

    def _dagilim(z: float) -> list[float]:
        return [(math.sqrt(z * z + 4 * (1 - z) * x * x / toplam) - z)
                / (2 * (1 - z)) for x in q]

    alt, ust = 0.0, 0.99
    for _ in range(_ARINDIRMA_ADIM):
        z = (alt + ust) / 2
        if sum(_dagilim(z)) > 1.0:
            alt = z
        else:
            ust = z
    return dict(zip(ters.keys(), _dagilim((alt + ust) / 2)))


def margin(oranlar: dict[str, float]) -> float:
    """Bültenin marjı (overround): ``Σ(1/o) − 1``. Arındırmadan bağımsızdır."""
    return sum(1.0 / v for v in oranlar.values() if v and v > 0) - 1.0


# ─── maç sonucu (1X2) — arayüze giden tek pazar ───────────────────────────────

#: Sembol duzeni TEK kaynaktan (`core`) — ad korunuyor, deger degil.
SEMBOLLER = _SEMBOLLER
#: Tercih sırası: piyasa ortalaması, sonra tek tek bahisçiler. İlk eleman
#: `FIYAT_VARSAYILAN`dır ve **öyle kalmalıdır** — gerekçesi orada yazılı.
#: Sıra bugün pratikte hiç kullanılmıyor (arşivde Avg 567/567 maçı kapıyor,
#: `season_1x2_summary().books == ["Avg"]`), ama kullanılırsa **kitap karışır**
#: ve karışım zamana bağlı olur; o yüzden `match_1x2` hangi kitaptan geldiğini
#: satır satır yazar ve özet onu ilan eder.
KAYNAK_SIRASI = (FIYAT_VARSAYILAN, "B365", "PS", "BFE", "Max")

#: `fiyatlar` modülünün paralel iz olarak ölçtüğü kitaplar ve okunur adları.
#: Burada durur çünkü sütun öneki bilgisi bu modülün işidir.
KITAP_ADLARI: dict[str, str] = {
    "Avg": "piyasa ortalaması", "PS": "Pinnacle",
    "BFE": "Betfair Exchange", "B365": "Bet365", "Max": "en iyi oran",
}


def donem_dagilimi(bloklar: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Kaç maç kapanış, kaç maç açılış fiyatından geldi."""
    kap = sum(1 for b in bloklar if b.get("closing"))
    return {"kapanis": kap, "acilis": len(bloklar) - kap}


def provenance_notu(bloklar: Sequence[dict[str, Any]]) -> str:
    """Sayıların hangi kitaptan ve hangi dönemden geldiğini **üretir**.

    Elle yazılan bir provenance, fiyat değiştiği anda yalan söyler ve
    yalan söylediği belli olmaz — bu depoda aynı hata `super_toto_sayfa`
    ve hafta panelinde de çıktı. Bu yüzden metin veriden türetilir.
    """
    if not bloklar:
        return "oran yok"
    kitaplar = sorted({b["book"] for b in bloklar})
    ad = ", ".join(KITAP_ADLARI.get(k, k) for k in kitaplar)
    d = donem_dagilimi(bloklar)
    if d["acilis"] == 0:
        donem = "kapanış oranları"
    elif d["kapanis"] == 0:
        donem = "açılış oranları"
    else:
        donem = (f"{d['kapanis']} maç kapanış, {d['acilis']} maç açılış "
                 "oranı — KARIŞIK")
    return (f"{ad} · {donem} (football-data.co.uk) — iddaa oranı değildir")


def match_1x2(row: dict[str, Any],
              yontem: str = ARINDIRMA_VARSAYILAN) -> dict[str, Any] | None:
    """Bir maçın maç sonucu oranı: önce kapanış, yoksa açılış.

    Hangi kaynaktan, hangi dönemden ve **hangi arındırmayla** geldiği çıktıda
    yazar — sayının nereden geldiği belirsiz kalmamalı.

    `yontem` varsayılanı `ARINDIRMA_VARSAYILAN`dır (bugün **`shin`**).
    Burada bir zamanlar "varsayılanı `orantili`dır" yazıyordu; A5 ölçümünden
    sonra varsayılan değişti ama bu satır kaldı. Arşivin **çevrimden önce**
    yayımlanmış sayıları orantısal ölçekte ölçülmüştür ve yenileriyle
    doğrudan kıyaslanamaz (bkz. `implied_probs` ve `ARINDIRMA_VARSAYILAN`
    üstündeki not).
    """
    if not row.get("matched"):
        return None
    for kapanis in (True, False):
        for kaynak in KAYNAK_SIRASI:
            oranlar = market_odds(row, "1X2", kaynak, closing=kapanis)
            if len(oranlar) != 3 or any(v <= 1.0 for v in oranlar.values()):
                continue
            olasilik = implied_probs(oranlar, yontem)
            favori = min(oranlar, key=lambda s: oranlar[s])
            return {
                "odds": {s: round(oranlar[s], 2) for s in SEMBOLLER},
                "probs": {s: round(olasilik[s], 4) for s in SEMBOLLER},
                "favourite": favori,
                "hit": favori == row["code"],
                "margin": round(sum(1 / v for v in oranlar.values()) - 1, 4),
                "book": kaynak,
                "closing": kapanis,
                "arindirma": yontem,
            }
    return None


def week_1x2(week: int) -> dict[int, dict[str, Any]]:
    """Bir haftanın maç numarasına göre 1X2 blokları (oranı olmayanlar yok)."""
    out: dict[int, dict[str, Any]] = {}
    for r in load_odds():
        if r["week"] != week:
            continue
        blok = match_1x2(r)
        if blok:
            out[r["no"]] = blok
    return out


#: Banko kararı için favori oranı bantları (alt dahil, üst hariç).
FAVORI_BANTLARI = ((1.0, 1.20), (1.20, 1.35), (1.35, 1.50),
                   (1.50, 1.75), (1.75, 2.00), (2.00, 99.0))


def _favori_bantlari(oranli: list[Any]) -> list[dict[str, Any]]:
    """Favorinin oranına göre: kaç maçta tuttu, kaçında tutmadı.

    ``tutmadı`` iki parçaya ayrılır — beraberlik ve karşı tarafın kazanması —
    çünkü banko kararında bunlar farklı riskler: beraberlik her maçta masada,
    karşı tarafın kazanması ise favorinin gerçekten yanılmasıdır.
    """
    out: list[dict[str, Any]] = []
    for lo, hi in FAVORI_BANTLARI:
        grup = [(r, b) for r, b in oranli if lo <= min(b["odds"].values()) < hi]
        n = len(grup)
        if not n:
            continue
        tuttu = sum(1 for r, b in grup if b["hit"])
        beraberlik = sum(1 for r, _ in grup if r["code"] == "0")
        tutmadi = n - tuttu
        out.append({
            "lo": lo,
            "hi": hi if hi < 99 else None,
            "label": f"{lo:.2f}–{hi:.2f}" if hi < 99 else f"{lo:.2f} ve üstü",
            "n": n,
            "hit": tuttu,
            "miss": tutmadi,
            "draw": beraberlik,
            "upset": tutmadi - beraberlik,
            "hit_pct": round(100 * tuttu / n, 1),
            "miss_pct": round(100 * tutmadi / n, 1),
            "draw_pct": round(100 * beraberlik / n, 1),
            "upset_pct": round(100 * (tutmadi - beraberlik) / n, 1),
        })
    return out


#: Bir satır bu sayının altında maça dayanıyorsa yüzdesi oynaktır ve
#: arayüzde işaretlenir. 30, "yüzde okumaya başlanabilir" sınırı.
AZ_ORNEK = 30

#: İlk iki sembolün olasılık toplamı bantları — çift mi banko mu kararı.
#: Alt sınır teorik olarak 2/3'tür (üç sembol de eşitse), o yüzden ilk bant
#: açık uçlu başlar.
CIFT_BANTLARI = ((0.0, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 1.01))

#: Favori ile ikincinin olasılık farkı bantları — beraberlik profili.
FARK_BANTLARI = ((0.0, 0.05), (0.05, 0.15), (0.15, 0.30),
                 (0.30, 0.50), (0.50, 1.01))


def _sirali_olasilik(blok: dict[str, Any]) -> list[tuple[str, float]]:
    """Sembolleri olasılığa göre büyükten küçüğe; eşitlikte kupon düzeni."""
    return sorted(blok["probs"].items(),
                  key=lambda kv: (-kv[1], SEMBOLLER.index(kv[0])))


def _kume_kapsama(oranli: list[Any]) -> list[dict[str, Any]]:
    """Çift (ilk iki sembol) işaretlemek sonucu ne sıklıkla kapsıyor.

    Her bant için üç sayı yan yana durur: piyasanın **söylediği** kapsama
    (ilk iki olasılığın toplamı), **gerçekleşen** kapsama ve aynı bantta
    banko yapılsaydı ne olacağı. Çift mi banko mu kararı bu üçlünün işidir.
    """
    out: list[dict[str, Any]] = []
    for lo, hi in CIFT_BANTLARI:
        grup = []
        for r, b in oranli:
            s = _sirali_olasilik(b)
            ikili = s[0][1] + s[1][1]
            if lo <= ikili < hi:
                grup.append((r, s, ikili))
        n = len(grup)
        if not n:
            continue
        ikide = sum(1 for r, s, _ in grup if r["code"] in (s[0][0], s[1][0]))
        birde = sum(1 for r, s, _ in grup if r["code"] == s[0][0])
        out.append({
            "lo": round(lo, 2),
            "hi": round(hi, 2) if hi <= 1.0 else None,
            "label": f"%{100 * lo:.0f}–%{100 * hi:.0f}" if hi <= 1.0 else f"%{100 * lo:.0f}+",
            "n": n,
            "model_pct": round(100 * sum(x[2] for x in grup) / n, 1),
            "in_two": ikide,
            "in_two_pct": round(100 * ikide / n, 1),
            "in_one": birde,
            "in_one_pct": round(100 * birde / n, 1),
            "low_sample": n < AZ_ORNEK,
        })
    return out


def _beraberlik_profili(oranli: list[Any]) -> list[dict[str, Any]]:
    """Favori ile ikincinin arası açıldıkça beraberlik ne yapıyor.

    Sinyal var ama zayıf: bu bir **gösterge**dir, tahminci değildir. Model
    sütunu bilerek yanında durur — piyasa zaten beraberliğe bir olasılık
    veriyor ve tabloda asıl soru, o olasılığın tutup tutmadığı.
    """
    out: list[dict[str, Any]] = []
    for lo, hi in FARK_BANTLARI:
        grup = []
        for r, b in oranli:
            s = _sirali_olasilik(b)
            fark = s[0][1] - s[1][1]
            if lo <= fark < hi:
                grup.append((r, b))
        n = len(grup)
        if not n:
            continue
        beraberlik = sum(1 for r, _ in grup if r["code"] == "0")
        tutan = sum(1 for _, b in grup if b["hit"])
        out.append({
            "lo": round(lo, 2),
            "hi": round(hi, 2) if hi <= 1.0 else None,
            "label": f"{lo:.2f}–{hi:.2f}" if hi <= 1.0 else f"{lo:.2f} ve üstü",
            "n": n,
            "draw": beraberlik,
            "draw_pct": round(100 * beraberlik / n, 1),
            "model_draw_pct": round(
                100 * sum(b["probs"]["0"] for _, b in grup) / n, 1),
            "favourite_hit_pct": round(100 * tutan / n, 1),
            "low_sample": n < AZ_ORNEK,
        })
    return out


#: football-data ana lig dosyaları ligi kodla verir (`T1`, `E0`…); ek ülke
#: dosyaları zaten "Sweden/Allsvenskan" gibi okunur bir ad taşır. Tabloda
#: kod görünmesin diye çeviri burada durur; eşleşmeyen değer olduğu gibi
#: geçer — uydurma ad üretilmez.
LIG_ADLARI: dict[str, str] = {
    "E0": "İngiltere · Premier Lig", "E1": "İngiltere · Championship",
    "E2": "İngiltere · League One", "E3": "İngiltere · League Two",
    "EC": "İngiltere · National League",
    "SC0": "İskoçya · Premiership", "SC1": "İskoçya · Championship",
    "SC2": "İskoçya · League One", "SC3": "İskoçya · League Two",
    "D1": "Almanya · Bundesliga", "D2": "Almanya · 2. Bundesliga",
    "I1": "İtalya · Serie A", "I2": "İtalya · Serie B",
    "SP1": "İspanya · La Liga", "SP2": "İspanya · La Liga 2",
    "F1": "Fransa · Ligue 1", "F2": "Fransa · Ligue 2",
    "N1": "Hollanda · Eredivisie", "B1": "Belçika · Pro Lig",
    "P1": "Portekiz · Primeira Liga", "T1": "Türkiye · Süper Lig",
    "G1": "Yunanistan · Süper Lig",
}


def _lig_kirilimi(oranli: list[Any], hafta_sayisi: int) -> list[dict[str, Any]]:
    """Lig lig beraberlik oranı ve favori isabeti.

    Lig etiketi oran arşivinden gelir (kupon payload'ı lig adı taşımaz).
    BOM hatası kapanana kadar bu alan 539 maçta boştu; etiketsiz satırlar
    gizlenmez, "bilinmiyor" olarak sayılır.
    """
    gruplar: dict[str, list[Any]] = {}
    for r, b in oranli:
        ad = (r["source"].get("league") or "").strip() or "bilinmiyor"
        gruplar.setdefault(ad, []).append((r, b))

    out: list[dict[str, Any]] = []
    for ad, grup in gruplar.items():
        n = len(grup)
        beraberlik = sum(1 for r, _ in grup if r["code"] == "0")
        tutan = sum(1 for _, b in grup if b["hit"])
        out.append({
            "league": ad,
            "label": LIG_ADLARI.get(ad, ad),
            "n": n,
            "share_pct": round(100 * n / len(oranli), 1),
            "per_week": round(n / hafta_sayisi, 1) if hafta_sayisi else 0.0,
            "draw": beraberlik,
            "draw_pct": round(100 * beraberlik / n, 1),
            "favourite_hit": tutan,
            "favourite_hit_pct": round(100 * tutan / n, 1),
            "low_sample": n < AZ_ORNEK,
        })
    out.sort(key=lambda d: (-d["n"], d["league"]))
    return out


def _brier(blok: dict[str, Any], code: str) -> float:
    """Bir oran blogunun Brier skoru — hesap `ortak.brier`de.

    `evaluate.brier` ile ayni formuldu; tek fark olasiligi `blok["probs"]`
    icinden okumasi. Formul artik tek yerde.
    """
    return brier(blok["probs"], code)


def _haftalik_brier(oranli: list[Any]) -> list[dict[str, Any]]:
    """Hafta hafta "piyasa ne kadar yanıldı".

    Favori isabeti tek başına yanıltıcıdır: 1,05 oranlı favorinin tutması
    ile 2,40 oranlının tutması aynı şey değil. Brier skoru olasılığın
    tamamını cezalandırır, bu yüzden sürpriz haftayı isabet sayısından
    daha dürüst gösterir.
    """
    gruplar: dict[int, list[Any]] = {}
    for r, b in oranli:
        gruplar.setdefault(r["week"], []).append((r, b))

    out: list[dict[str, Any]] = []
    for hafta, grup in sorted(gruplar.items()):
        n = len(grup)
        toplam = sum(_brier(b, r["code"]) for r, b in grup)
        tutan = sum(1 for _, b in grup if b["hit"])
        out.append({
            "week": hafta,
            "n": n,
            "brier": round(toplam / n, 4),
            "favourite_hit": tutan,
            "favourite_hit_pct": round(100 * tutan / n, 1),
            # Kupon eksik oranlıysa hafta karşılaştırmaya girmemeli.
            "partial": n < 15,
        })
    return out


def season_1x2_summary(weeks: list[int] | None = None) -> dict[str, Any] | None:
    """Dilim için oran özeti: kapsama, favori isabeti, marj ve kalibrasyon.

    ``weeks`` verilirse yalnızca o haftalar sayılır — arayüzdeki aralık
    filtresi böylece oran kartını da kapsar.
    """
    rows = load_odds()
    if not rows:
        return None
    izin = set(weeks) if weeks is not None else None
    ilgili = [r for r in rows if izin is None or r["week"] in izin]
    if not ilgili:
        return None

    bloklar = [(r, match_1x2(r)) for r in ilgili]
    oranli = [(r, b) for r, b in bloklar if b]
    if not oranli:
        return None

    tutan = sum(1 for _, b in oranli if b["hit"])
    fav_dagilim = {s: sum(1 for _, b in oranli if b["favourite"] == s) for s in SEMBOLLER}

    # Favori tuttuğunda / tutmadığında ne gerçekleşti.
    # "0" tuttu sütunu her zaman 0'dır: beraberlik hiçbir maçta favori olmaz,
    # bu yüzden HER beraberlik tanımı gereği "tutmadı" tarafına düşer.
    tuttu_sonuc = {
        s: sum(1 for r, b in oranli if b["hit"] and r["code"] == s) for s in SEMBOLLER
    }
    tutmadi_sonuc = {
        s: sum(1 for r, b in oranli if not b["hit"] and r["code"] == s) for s in SEMBOLLER
    }
    # Favori (satır) × gerçekleşen (sütun) çapraz tablosu.
    capraz = {
        f: {s: sum(1 for r, b in oranli if b["favourite"] == f and r["code"] == s)
            for s in SEMBOLLER}
        for f in SEMBOLLER
    }
    # Gerçek sürpriz: favorinin KARŞI tarafı kazandı (beraberlik değil).
    underdog = sum(
        capraz[f][s] for f in SEMBOLLER for s in SEMBOLLER
        if f != s and s != "0"
    )

    bantlar = _favori_bantlari(oranli)

    # Kalibrasyon: modelin verdiği olasılık ile gerçekleşme yan yana.
    kovalar: dict[int, dict[str, float]] = {}
    for r, b in oranli:
        for s in SEMBOLLER:
            p = b["probs"][s]
            k = min(int(p * 10), 9)
            hucre = kovalar.setdefault(k, {"n": 0, "model": 0.0, "gercek": 0})
            hucre["n"] += 1
            hucre["model"] += p
            hucre["gercek"] += 1 if s == r["code"] else 0
    kalibrasyon = [
        {
            "lo": k * 10,
            "hi": k * 10 + 10,
            "n": int(v["n"]),
            "model_pct": round(100 * v["model"] / v["n"], 1),
            "actual_pct": round(100 * v["gercek"] / v["n"], 1),
        }
        for k, v in sorted(kovalar.items()) if v["n"] >= 10
    ]

    return {
        "matches": len(ilgili),
        "with_odds": len(oranli),
        "coverage_pct": round(100 * len(oranli) / len(ilgili), 1),
        "favourite_hit": tutan,
        "favourite_miss": len(oranli) - tutan,
        "favourite_hit_pct": round(100 * tutan / len(oranli), 1),
        "favourite_split": fav_dagilim,
        "outcome_when_hit": tuttu_sonuc,
        "outcome_when_miss": tutmadi_sonuc,
        "cross": capraz,
        "underdog_wins": underdog,
        "favourite_bands": bantlar,
        # Karar destek blokları — üçü de aynı dilim üzerinden hesaplanır.
        "set_coverage": _kume_kapsama(oranli),
        "draw_profile": _beraberlik_profili(oranli),
        "leagues": _lig_kirilimi(oranli, len({r["week"] for r, _ in oranli})),
        "weekly_brier": _haftalik_brier(oranli),
        "brier_avg": round(
            sum(_brier(b, r["code"]) for r, b in oranli) / len(oranli), 4
        ),
        "brier_uniform": BRIER_ESIT,
        "low_sample_at": AZ_ORNEK,
        "outcome_totals": {
            s: tuttu_sonuc[s] + tutmadi_sonuc[s] for s in SEMBOLLER
        },
        "avg_margin_pct": round(
            100 * sum(b["margin"] for _, b in oranli) / len(oranli), 2
        ),
        "calibration": kalibrasyon,
        "books": sorted({b["book"] for _, b in oranli}),
        "periods": donem_dagilimi([b for _, b in oranli]),
        # Bu metin SABIT yaziliydi: "piyasa kapanis oranlari
        # (football-data.co.uk) — iddaa orani degildir". Iki seyi
        # soylemiyordu: hangi bahisci ve gercekten hepsi kapanis mi.
        # Arayuz onu oldugu gibi basiyor (istatistik/oranlar), yani fiyat
        # degisse okuyucu anlamazdi. Artik KULLANILAN kitap ve donem
        # karisimindan uretiliyor — `match_1x2` zaten satir satir yaziyordu,
        # yalnizca ozetlenmiyordu.
        "note": provenance_notu([b for _, b in oranli]),
    }


def coverage() -> dict[str, Any]:
    rows = load_odds()
    eslesen = [r for r in rows if r["matched"]]
    return {
        "matches": len(rows),
        "matched": len(eslesen),
        "pct": round(100 * len(eslesen) / len(rows), 2) if rows else 0.0,
        "odds_values": sum(len(r["odds"]) for r in eslesen),
    }
