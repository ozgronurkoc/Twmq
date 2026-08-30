"""Birden fazla modülün paylaştığı küçük hesaplar — **tek kaynak**.

Bu modül var olmadan önce aynı formüller pakette dağınık duruyordu ve
ayrışmaya açıktı:

* olasılık normalizasyonu `bayes` ve `markov`'da **birebir aynı** iki
  private fonksiyondu (`_normalize` / `_norm`);
* Wilson aralığı `backtest`'te tanımlı, `benzer`'de yalnızca ileten bir
  kabuk, `kalibrasyon` ve `scripts/super_toto_sezon` ise o kabuğun içinden
  **private** bir sembolü iki sıçramayla import ediyordu;
* Brier `evaluate` ve `odds`'ta iki kez yazılmıştı (tek fark: biri sözlüğü
  doğrudan, öteki `blok["probs"]` üzerinden okuyordu);
* "bu değer hangi banda düşer" üç modülde aynı adla üç ayrı gövdeydi;
* favori dilimi `bahisci` ve `disari`'da aynıydı — `disari` bunu bir
  yorumda itiraf ediyordu ama kopya yine de duruyordu.

Buradaki her şey **saf**tır: dosya okumaz, önbellek tutmaz, paket içinden
yalnızca `core`'u (sembol düzeni için) çeker. Böylece hiçbir modül bu
modül yüzünden döngüye girmez.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from .core import SEMBOLLER

__all__ = [
    "BRIER_ESIT",
    "FAVORI_DILIMLERI",
    "GUVEN_Z",
    "OLASILIK_BANTLARI",
    "SEMBOLLER",
    "bant_adi",
    "brier",
    "brier_ayrisimi",
    "favori_dilimi",
    "kacak_dagilimi",
    "karisiklik_matrisi",
    "normalize_olasilik",
    "siralama_olculeri",
    "wilson",
]


# ─── olasılık ────────────────────────────────────────────────────────────

def normalize_olasilik(p: dict[str, float]) -> dict[str, float]:
    """1'e normalize edilmiş olasılık; negatif kırpılır, toplam 0 ise düzgün.

    Toplam sıfırken 1/3'e düşmek keyfi değil: "bilgi yok" durumunun tek
    tarafsız karşılığı düzgün dağılımdır. Arayüz de aynı kuralı uygular
    (`frontend/lib/utils.ts` `normalize`), yani yığının iki ucu aynı şeyi
    söyler.
    """
    toplam = sum(max(0.0, float(p.get(s, 0.0))) for s in SEMBOLLER)
    if toplam <= 0:
        return dict.fromkeys(SEMBOLLER, 1.0 / 3.0)
    return {s: max(0.0, float(p.get(s, 0.0))) / toplam for s in SEMBOLLER}


# ─── güven aralığı ───────────────────────────────────────────────────────

#: %95 iki yanlı normal kuantili.
GUVEN_Z = 1.959964


def wilson(basari: int, n: int) -> tuple[float, float]:
    """Oran için Wilson %95 güven aralığı.

    Normal yaklaşım küçük örneklemde kenarlara yapışır — 40/41'de üst sınır
    1'i aşar, 0/30'da alt sınır eksiye iner. Wilson bu yüzden tercih edilir
    ve aralık her zaman [0, 1] içinde kalır.

    Örnek — normal yaklaşımın taştığı iki uç, Wilson'da taşmıyor::

        >>> alt, ust = wilson(40, 41)
        >>> round(alt, 4), round(ust, 4)
        (0.874, 0.9957)
        >>> alt, ust = wilson(0, 30)
        >>> alt, round(ust, 4)
        (0.0, 0.1135)

    Örneklem yoksa aralık da yoktur — sıfır yazılmaz, `(0, 0)` bir aralık
    değil bir *"ölçülmedi"* işaretidir::

        >>> wilson(0, 0)
        (0.0, 0.0)
    """
    if n <= 0:
        return 0.0, 0.0
    p = basari / n
    payda = 1 + GUVEN_Z * GUVEN_Z / n
    merkez = (p + GUVEN_Z * GUVEN_Z / (2 * n)) / payda
    yari = GUVEN_Z * math.sqrt(
        p * (1 - p) / n + GUVEN_Z * GUVEN_Z / (4 * n * n)) / payda
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


# ─── puanlama ────────────────────────────────────────────────────────────

def brier(probs: dict[str, float], kod: str) -> float:
    """Tek maçın Brier skoru: Σ(p_s − 1{s=gerçek})².

    0 = kusursuz, 2 = tam ters. Olasılığın tamamını cezalandırır: 0,90
    verip tutturmakla 0,40 verip tutturmak aynı sayılmaz::

        >>> kesin = {"1": 1.0, "0": 0.0, "2": 0.0}
        >>> brier(kesin, "1")
        0.0
        >>> brier(kesin, "2")
        2.0

    "Tutturmak" tek başına yetmez — ne kadar emin olunduğu da sayılır::

        >>> round(brier({"1": 0.9, "0": 0.05, "2": 0.05}, "1"), 4)
        0.015
        >>> round(brier({"1": 0.4, "0": 0.3, "2": 0.3}, "1"), 4)
        0.54

    Eşit olasılık referans çizgisini verir::

        >>> round(brier({"1": 1/3, "0": 1/3, "2": 1/3}, "1"), 4) == BRIER_ESIT
        True
    """
    return sum((probs.get(s, 0.0) - (1.0 if s == kod else 0.0)) ** 2
               for s in SEMBOLLER)


#: Üç sembole eşit olasılık verildiğinde çıkan Brier — referans çizgi.
#: Bir tahminci bunun altına inemiyorsa hiç bilgi taşımıyor demektir.
BRIER_ESIT = round(2 * (1 / 3.0) ** 2 + (1 - 1 / 3.0) ** 2, 4)


# ─── bantlama ────────────────────────────────────────────────────────────

def bant_adi(deger: float, bantlar: Sequence[float]) -> str:
    """Bir değeri artan eşik dizisine göre okunabilir bant adına çevirir.

    Eşikler dahil değildir (üst sınır açık)::

        >>> bantlar = (0.40, 0.50, 0.65)
        >>> bant_adi(0.31, bantlar)
        '<0.40'
        >>> bant_adi(0.52, bantlar)
        '<0.65'
        >>> bant_adi(0.80, bantlar)
        '>=0.65'

    Eşiğin tam üstünde olan değer bir ÜST banda düşer — sınır açıktır::

        >>> bant_adi(0.40, bantlar)
        '<0.50'

    Bant yoksa bant adı da yoktur::

        >>> bant_adi(0.5, ())
        '—'
    """
    for esik in bantlar:
        if deger < esik:
            return f"<{esik:.2f}"
    return f">={bantlar[-1]:.2f}" if bantlar else "—"


#: Favori olasılığı dilimleri — karışmayı açmak için. Eşikler ölçüm
#: sonucuna BAKILMADAN, kaba biçimde seçildi; sonradan ayarlanırsa dilim
#: tanımı ölçümün kendisine bağlanmış olurdu.
FAVORI_DILIMLERI: Sequence[float] = (0.40, 0.50, 0.65)


def favori_dilimi(probs: dict[str, float] | None) -> str:
    """Bir maçın favori olasılığının hangi dilime düştüğü.

    Okunan şey en yüksek olasılıktır, `"1"`in olasılığı değil — deplasman
    favorisi de aynı dilime düşer::

        >>> favori_dilimi({"1": 0.25, "0": 0.25, "2": 0.50})
        '<0.65'
        >>> favori_dilimi({"1": 0.50, "0": 0.25, "2": 0.25})
        '<0.65'

    Denk bir maç en alt dilimdedir::

        >>> favori_dilimi({"1": 1/3, "0": 1/3, "2": 1/3})
        '<0.40'
        >>> favori_dilimi(None)
        '<0.40'
    """
    en_yuksek = max(probs.values()) if probs else 0.0
    return bant_adi(en_yuksek, FAVORI_DILIMLERI)


#: Olasılık bantları — kalibrasyon eğrisi ve Brier ayrışımı **aynı** kenarları
#: kullanır. Kenarlar ölçüm sonucuna BAKILMADAN, okunabilirlik için seçildi:
#: uçlarda seyrek olduğu için geniş, ortada yoğun olduğu için dar.
#:
#: Tanım uzun süre `kalibrasyon.BANTLAR`daydı; ayrışım da aynı kenarlara
#: ihtiyaç duyunca buraya taşındı. İki ayrı kenar dizisi olsaydı eğrinin
#: söylediği ile ayrışımın söylediği sessizce ayrışırdı — bu modülün var olma
#: sebebi tam olarak budur.
OLASILIK_BANTLARI: Sequence[tuple[float, float]] = (
    (0.0, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 0.20), (0.20, 0.25),
    (0.25, 0.30), (0.30, 0.35), (0.35, 0.40), (0.40, 0.45), (0.45, 0.50),
    (0.50, 0.55), (0.55, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 1.01),
)


def _bant_indeksi(p: float, bantlar: Sequence[tuple[float, float]]) -> int:
    """`p`'nin düştüğü bandın indeksi. Aralık `[lo, hi)`; dışarısı kenara kırpılır.

    Kırpma sessiz bir düzeltme değil, tanım gereği doğru olan şey: olasılık
    zaten `[0, 1]` içindedir ve son bandın üst kenarı `1.01`'dir, yani kırpma
    yalnızca kayan nokta artığı için devreye girer.
    """
    for i, (lo, hi) in enumerate(bantlar):
        if lo <= p < hi:
            return i
    return 0 if p < bantlar[0][0] else len(bantlar) - 1


def brier_ayrisimi(tahminler: Sequence[dict[str, float]],
                   kodlar: Sequence[str],
                   bantlar: Sequence[tuple[float, float]] | None = None
                   ) -> dict[str, Any]:
    """Brier skorunun Murphy ayrışımı — **sembol başına**, dört terim.

    Brier tek bir sayıdır ve iki farklı kusuru aynı torbaya koyar: olasılığın
    **yanlış ayarlı** olması (piyasa %30 diyor, gerçek %35) ve olasılığın
    **ayırt edemiyor** olması (her maça aynı sayıyı veriyor). Birincisi
    yeniden kalibrasyonla geri alınabilir, ikincisi alınamaz — yeni bilgi
    ister. Ayrışım bu ikisini ayırır::

        BS_s = REL_s − RES_s + UNC_s + ICI_s

        REL_s = Σ_k (n_k/N)(p̄_k − ō_k)²             güvenilirlik  ↓ iyi
        RES_s = Σ_k (n_k/N)(ō_k − ō_s)²             çözünürlük    ↑ iyi
        UNC_s = ō_s(1 − ō_s)                         belirsizlik   sabit
        ICI_s = Σ_k (n_k/N)[Var_k(p) − 2Cov_k(p,o)]  bant içi artık

    Bunun **ürüne dönük** karşılığı şudur: `REL`, *herhangi bir* yeniden
    kalibrasyon basamağının kazanabileceğinin üst sınırıdır. Küçükse
    kalibrasyon tarafında alınacak yol kalmamış demektir ve aranacak şey
    çözünürlüktür.

    ─── Üç tasarım kararı ────────────────────────────────────────────────

    **1. Sembol başına, havuzlanmış değil.** `kalibrasyon.kalibrasyon_egrisi`
    üç sembolü havuzlar ve eğri için bu doğrudur. Ama havuzlanmış ölçekte
    `ō` her zaman tam `1/3`'tür — her maçta üç sembolden tam biri gerçekleşir,
    yani `Σo = N` ve `ō = N/3N`. `UNC` böylece `2/9`'a çakılır ve **sınıf
    dengesizliği ölçüden tamamen düşer.** Sembol başına ayrışımda `UNC_s`
    gerçek taban oranını taşır ve beraberliğin satırı ayrı okunur.

    **2. Dördüncü terim gizlenmez.** Klasik üç terimli ayrışım yalnızca bir
    bandın içindeki tahminler birebir aynıysa tamdır; bantlama artık bırakır.
    Artığı ayrı sütun olarak yazmak özdeşliği **kayan noktaya kadar tam**
    yapar — ve `tests/test_ortak.py` bunu bekçiliyor. Gizlenseydi, ayrışım
    "yaklaşık" olurdu ve yaklaşıklığın büyüklüğü bilinmezdi.

    **3. Merkezlenmiş momentler.** `Var = E[p²] − E[p]²` kısayolu 1e-12'lik
    bir özdeşlik için yeterince kararlı değil; iki geçişli merkezlenmiş
    toplam kullanılır.

    ─── `sapma_payi` — sayıyı okumadan önce bakılacak alan ─────────────────

    `REL` ve `RES` sonlu örneklemde **yukarı yanlıdır**: bir bandın gözlenen
    oranı `ō_k` gürültü taşır ve `(p̄_k − ō_k)²` o gürültünün karesini de
    toplar. Yanlılığın büyüklüğü tahmin edilebilir::

        sapma ≈ Σ_k (n_k/N) · ō_k(1 − ō_k) / (n_k − 1)

    `sapma_payi` bu sayıdır ve **`REL`in yanına konmadan `REL` okunmaz**:
    540 maçlık kupon setinde bant başına ~36 nokta düşer ve pay `REL`in
    kendisiyle aynı mertebeye çıkar — yani orada `REL` çoğunlukla gürültüdür.
    31 bin maçlık korpusta pay iki mertebe küçülür ve sayı okunabilir hâle
    gelir. **Kesit büyüklüğü burada bir ayrıntı değil, ön koşuldur.**

    Yanlılık `RES`i de yaklaşık aynı miktarda şişirdiği için **farkta büyük
    ölçüde sadeleşir**; `RES − REL` tek tek terimlerden daha dayanıklıdır.

    Dönen gövde: `toplam` (üç sembolün toplamı — `brier`in maç ortalamasıyla
    birebir aynı ölçek) ve `semboller` (sembol başına aynı alanlar + taban
    oranı + sapma payı). `artik` alanı özdeşliğin kapanma hatasıdır ve sıfır
    olmalıdır; çıktıda durur ki bekçi yalnızca testte değil raporda da
    görünsün.
    """
    if bantlar is None:
        bantlar = OLASILIK_BANTLARI
    n = min(len(tahminler), len(kodlar))
    if n == 0 or not bantlar:
        bos = {"brier": 0.0, "guvenilirlik": 0.0, "cozunurluk": 0.0,
               "belirsizlik": 0.0, "bant_ici": 0.0, "sapma_payi": 0.0,
               "artik": 0.0}
        return {"n": 0, "bant_sayisi": len(bantlar),
                "toplam": dict(bos),
                "semboller": {s: {**bos, "taban_oran": 0.0} for s in SEMBOLLER}}

    semboller: dict[str, dict[str, float]] = {}
    for s in SEMBOLLER:
        # (p, o) noktaları — o ∈ {0, 1}
        kovalar: list[list[tuple[float, float]]] = [[] for _ in bantlar]
        toplam_o = 0.0
        brier_s = 0.0
        for i in range(n):
            p = float(tahminler[i].get(s, 0.0))
            o = 1.0 if kodlar[i] == s else 0.0
            toplam_o += o
            brier_s += (p - o) ** 2
            kovalar[_bant_indeksi(p, bantlar)].append((p, o))
        brier_s /= n
        taban = toplam_o / n

        rel = res = ici = sapma = 0.0
        for kova in kovalar:
            nk = len(kova)
            if nk == 0:
                continue
            agirlik = nk / n
            p_ort = sum(p for p, _ in kova) / nk
            o_ort = sum(o for _, o in kova) / nk
            # merkezlenmiş momentler — özdeşliğin tam kapanması için
            var_p = sum((p - p_ort) ** 2 for p, _ in kova) / nk
            kov = sum((p - p_ort) * (o - o_ort) for p, o in kova) / nk
            rel += agirlik * (p_ort - o_ort) ** 2
            res += agirlik * (o_ort - taban) ** 2
            ici += agirlik * (var_p - 2 * kov)
            if nk > 1:
                sapma += agirlik * o_ort * (1.0 - o_ort) / (nk - 1)
        unc = taban * (1.0 - taban)

        semboller[s] = {
            "brier": brier_s,
            "guvenilirlik": rel,
            "cozunurluk": res,
            "belirsizlik": unc,
            "bant_ici": ici,
            "taban_oran": taban,
            "sapma_payi": sapma,
            "artik": brier_s - (rel - res + unc + ici),
        }

    toplam = {
        alan: sum(semboller[s][alan] for s in SEMBOLLER)
        for alan in ("brier", "guvenilirlik", "cozunurluk", "belirsizlik",
                     "bant_ici", "sapma_payi", "artik")
    }
    return {"n": n, "bant_sayisi": len(bantlar),
            "toplam": toplam, "semboller": semboller}


def karisiklik_matrisi(tahminler: Sequence[dict[str, float]],
                       kodlar: Sequence[str]) -> dict[str, Any]:
    """3×3 karışıklık matrisi ve sınıf başına duyarlılık/kesinlik.

    Brier ve log kaybı **olasılığı** ölçer; bu panel tahmincinin *karar*
    verdiğinde ne yaptığını ölçer — en olası sembolü seçseydi hangi sonucu
    hangisiyle karıştırırdı.

    Ayrı ölçülmesinin sebebi beraberliktir. Dış bir çalışma bütün
    modellerinde beraberlikte ~sıfır duyarlılık ölçtü; bizde bunun ürün
    tarafındaki karşılığı ölçülü (çiftede atılan beraberlik %25,8 ile geliyor,
    ev sahibi %16,0) ama **tahmin tarafındaki karşılığı hiç ölçülmedi.**
    `duyarlilik["0"]` tam olarak o sayıdır.

    Eşitlik durumunda `SEMBOLLER` sırası (1, 0, 2) belirleyicidir — kupon
    düzeni ve deterministiklik için; rastgele bozma ölçümü tekrarlanamaz
    kılardı.

    `dengeli_isabet` sınıf başına duyarlılıkların ortalamasıdır: sınıflar
    dengesiz olduğu için (1: ~%44, 0: ~%24) ham isabet çoğunluğu tahmin
    etmekle şişer, dengeli isabet şişmez.
    """
    n = min(len(tahminler), len(kodlar))
    matris: dict[str, dict[str, int]] = {
        g: dict.fromkeys(SEMBOLLER, 0) for g in SEMBOLLER
    }
    dogru = 0
    for i in range(n):
        p = tahminler[i]
        secim = max(SEMBOLLER, key=lambda s: float(p.get(s, 0.0)))
        gercek = kodlar[i]
        if gercek not in matris:
            continue
        matris[gercek][secim] += 1
        if gercek == secim:
            dogru += 1

    duyarlilik: dict[str, float] = {}
    kesinlik: dict[str, float] = {}
    for s in SEMBOLLER:
        gercek_n = sum(matris[s].values())
        secim_n = sum(matris[g][s] for g in SEMBOLLER)
        duyarlilik[s] = matris[s][s] / gercek_n if gercek_n else 0.0
        kesinlik[s] = matris[s][s] / secim_n if secim_n else 0.0

    gecerli = [s for s in SEMBOLLER if sum(matris[s].values()) > 0]
    return {
        "n": n,
        # satır = gerçek sonuç, sütun = tahmincinin seçimi
        "matris": matris,
        "isabet": dogru / n if n else 0.0,
        "duyarlilik": duyarlilik,
        "kesinlik": kesinlik,
        "dengeli_isabet": (sum(duyarlilik[s] for s in gecerli) / len(gecerli)
                           if gecerli else 0.0),
    }


#: Hafta içi sıralamanın ölçüleceği kesme noktaları. 1 (tek banko), 3 ve 5
#: — kuponda gerçekten kurulan banko sayısı aralığı. Ölçüm sonucuna
#: BAKILMADAN seçildi.
SIRALAMA_K: Sequence[int] = (1, 3, 5)


def siralama_olculeri(tahminler: Sequence[dict[str, float]],
                      kodlar: Sequence[str],
                      k_listesi: Sequence[int] = SIRALAMA_K) -> dict[str, Any]:
    """Hafta **içinde** güven sıralaması — Brier'in göremediği yetenek.

    Brier ve log kaybı her maçı tek tek cezalandırır; ikisi de bir haftanın
    15 maçını **birbirine göre** sıralamayı ölçmez. Oysa kuponun sorduğu şey
    tam olarak budur: *"bu 15 maçın hangilerine banko koyayım?"*

    İki tahminci aynı Brier'i verip farklı sıralayabilir. Sıralaması iyi olan
    `secim.en_iyi_secim`e daha kullanışlı bir girdi verir — çünkü `secim`
    bütçeyi en güvenilir maçlara harcar ve o "en güvenilir" listesi doğru
    sıralanmamışsa bütçe yanlış yere gider.

    ─── Ölçüler ──────────────────────────────────────────────────────────

    Maçlar `max(p)` (favoriye verilen güven) azalan sırada dizilir. Bir maç
    **isabetli** sayılır: en olası sembol gerçekleşmişse.

    `ndcg`   Normalize edilmiş indirimli kazanç. İsabetli maçlar listenin
             başına ne kadar toplanmışsa 1'e o kadar yakın. Haftada hiç
             isabet yoksa tanımsızdır ve o hafta ortalamaya **girmez**
             (`ndcg_hafta` kaç haftanın girdiğini söyler).
    `isabet_k` En güvenilen `k` maçın isabet oranı. `k=1` "haftanın en emin
             maçı ne sıklıkta tutuyor" demektir — bankonun doğrudan karşılığı.

    `taban_isabet` bütün maçların isabet oranıdır ve `isabet_k`'nin yanında
    durması şart: `isabet_1` tabandan yüksek değilse tahminci **güvenini
    boşuna dağıtıyor** demektir — sıralama bilgi taşımıyordur.
    """
    n = min(len(tahminler), len(kodlar))
    if n == 0:
        return {"n": 0, "ndcg": None, "isabet_k": {}, "taban_isabet": 0.0}

    kayit: list[tuple[float, int]] = []
    for i in range(n):
        p = tahminler[i]
        secim = max(SEMBOLLER, key=lambda s: float(p.get(s, 0.0)))
        kayit.append((float(p.get(secim, 0.0)), 1 if kodlar[i] == secim else 0))
    kayit.sort(key=lambda x: -x[0])
    ilgi = [r for _, r in kayit]

    def _dcg(diz: Sequence[int]) -> float:
        return sum(r / math.log2(i + 2) for i, r in enumerate(diz))

    ideal = _dcg(sorted(ilgi, reverse=True))
    ndcg = (_dcg(ilgi) / ideal) if ideal > 0 else None

    isabet_k: dict[int, dict[str, int]] = {}
    for k in k_listesi:
        kk = min(k, n)
        isabet_k[k] = {"dogru": sum(ilgi[:kk]), "n": kk}

    return {
        "n": n,
        "ndcg": ndcg,
        "isabet_k": isabet_k,
        "taban_isabet": sum(ilgi) / n,
    }


def kacak_dagilimi(kacak_olasiliklari: Sequence[float]) -> list[float]:
    """Poisson-binom: bağımsız maçlarda **toplam kaçak sayısının** dağılımı.

    `d[m]` = tam olarak `m` maçın seçim kümesinin dışında kalma olasılığı.
    Maçlar bağımsız varsayılır; varsayım ölçüldü ve kırılmadı (haftalık
    favori isabetinin gözlenen varyansı / öngörülen = 0,91, bkz.
    `tests/test_invariants.py`).

    `scripts/super_toto_degerlendir.py` içinde tanımlıydı ve oradan
    kullanılıyordu; `secim` de aynı hesabı istediği için buraya taşındı —
    iki gövde ayrışsaydı kuponu kuran hesap ile onu değerlendiren hesap
    farklı şeyler söylerdi.
    """
    dagilim = [1.0]
    for q in kacak_olasiliklari:
        yeni = [0.0] * (len(dagilim) + 1)
        for i, v in enumerate(dagilim):
            yeni[i] += v * (1.0 - q)
            yeni[i + 1] += v * q
        dagilim = yeni
    return dagilim
