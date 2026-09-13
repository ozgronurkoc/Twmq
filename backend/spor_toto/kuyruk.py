"""Hafta içi bağımlılık ve **kuyruk** etkisi — `P(k≥12)` iyimser mi? (§4.1)

Bu modülün cevapladığı soru depoda uzun süre **yazılı bir varsayım** olarak
durdu. `secim._carpim`ın docstring'i onu tek cümlede itiraf ediyor::

    \"\"\"Maçlar bağımsız varsayılarak seçim kümesine düşme olasılığı.\"\"\"

Aynı varsayım `ortak.kacak_dagilimi`nin Poisson-binomunda, `secim`in
`P(k≤2)`sinde ve geri testin `P(k≥12)`sinde tekrarlanıyor. Soru dışarıdan
gelen bir mimari makalesiyle yeniden gündeme geldi
(`GELECEK_MIMARISI_ESLEMESI.md` §4.1) ve durma kuralı **ölçüm görülmeden**
`ISTATISTIK_YOL_HARITASI.md` §6.2'ye yazıldı.

─── Neden tahminde değil, kuyrukta ──────────────────────────────────────

Bağımsızlık varsayımı tek tek `P(Y_i)`'leri **değiştirmez**; Brier de log
kaybı da maç maç hesaplanır ve bu ölçümlerin hiçbiri varsayımı kullanmaz.
Varsayımın girdiği tek yer, 15 maçın sonucunu **birlikte** sayan
büyüklüklerdir:

    P(k ≤ 2)     seçim kümesinin dışında en fazla iki maç  (`secim`)
    P(k ≥ 12)    ikramiye eşiği                            (geri test)

Korelasyonlu Bernoulli toplamının kuyruğu bağımsız olanınkinden **şişmandır**.
Yani pozitif bağımlılık varsa bugünkü hesap kendi riskini *iyimser*
gösteriyor demektir — ve hedefin `P(en iyi kolon ≥ 12)` olduğu ölçüldüğüne
göre (§5.2 bulgu 1) bu doğrudan hedef ölçüsünü ilgilendirir.

─── Zaten bir bekçi vardı, ve istatistiği YANLIŞTI ──────────────────────

`tests/test_invariants.py::test_bagimsizlik_varsayimi_hafta_duzeyinde_tutuyor`
bu varsayımı sınıyordu ve `ortak.kacak_dagilimi`nin docstring'i onun sayısını
(*"varyans oranı 0,91"*) varsayımın **kanıtı** diye anıyordu. Bekçi işe
yaramıyor değildi ama ölçtüğü şey sorulan şey değildi::

    eski:  Var_haftalar(K) / E[V]
    doğru: Var_haftalar(K − M) / E[V]

`K` haftanın gözlenen isabeti, `M = Σp_i` o haftanın **öngörülen** isabeti,
`V = Σp_i(1−p_i)` bağımsızlığın öngördüğü varyans. Kalibre bir tahmincide

    Var(K) = E[V] + Var(M)

olduğu için eski oran, hafta zorluğunun haftadan haftaya değişmesini
(`Var(M)`) bağımlılık sanıyordu. Sabit 15 maçlık kupon haftalarında bu
yalnızca **yukarı** yönlü bir yanlılıktır — yani bekçi kırılmadıysa sonuç
*a fortiori* ayakta kalır. Ama değişken boyutlu korpus haftalarında aynı
istatistik **36,09** veriyor (doğrusu 0,98): bekçi o kesitte hiç
kullanılamazdı, ve korpus tam da gücün olduğu yer.

─── Üç büyüklük, ve niçin AYRI ölçülüyorlar ─────────────────────────────

İlk koşum, ayrılmadıklarında ölçümün ne kadar yanıltıcı olduğunu gösterdi:
ham artıklarla kupon kesitinde `ρ = +0,0077` çıkıyor — pozitif bağımlılık
gibi görünen şey, tamamen **kalibrasyon yanlılığıdır**.

    yanlılık   b = ort(Y_i − p_i)          favori öngörülenden sık tutuyor
    dağılım    Var(K − M − b·n) / E[V]     bağımlılığın ölçüsü
    ρ          demeanlenmiş artıkların ortalama ikili korelasyonu

Yanlılık bir **kalibrasyon** kusurudur ve zaten ölçülmüştür (§3.18 A5:
piyasanın %70–80 dediği maçlar gerçekte %78,9). Bağımlılık ise haftaya özgü
ortak bir etkendir. Sabit bir `b`, `K`'nın haftalar arası varyansını
değiştirmez — kuyruğu şişiren şey `b` değil, hafta içi eş-harekettir. Bu
yüzden `ρ` **demeanlenmiş** artıklarla kurulur.

─── Bootstrap birimi HAFTA'dır, ve bu bir tercih değil zorunluluk ───────

Maç düzeyinde yeniden örneklemek, tam da ölçülmek istenen şeyi (hafta içi
bağımlılık) yok sayardı. Örnekleme birimi bu yüzden haftadır — deponun
geri kalanındaki kuralın aynısı (`evaluate.bootstrap_farki`), ama burada
gerekçe daha sıkı.

─── ρ → kuyruk: tek faktör, ve RNG YOK ──────────────────────────────────

Ölçülen `ρ`nun `P(k≥12)`ye ne yaptığını görmek için bir bağımlılık modeli
gerekir. Seçilen model standarttır ve **tek parametrelidir**::

    Z_i = √a · U + √(1−a) · ε_i        U, ε_i ~ N(0,1) bağımsız
    Y_i = 1{Z_i < Φ⁻¹(p_i)}

`U` haftanın ortak etkeni. Modelin tek işi `ρ`yu kuyruğa çevirmek; `a`
ölçülen `ρ`yu verecek biçimde ikiye bölmeyle çözülür.

Hesap **Monte Carlo değil**: `U = u` verildiğinde maçlar koşullu bağımsızdır,
yani `kacak_dagilimi`nin Poisson-binomu aynen kullanılabilir ve `u` üzerinden
Gauss-Hermite dördünlemesiyle integre edilir. Sonuç deterministiktir —
tohum tartışması yoktur, ve `kacak_dagilimi` ikinci kez yazılmaz.

Düğüm sayısı (`DUGUM = 64`) **ölçüm görülmeden** seçildi ve kararı
etkilemediği ayrıca sınandı (`tests/test_kuyruk.py`).

─── Sağlama: makine kendi kendini doğruluyor ────────────────────────────

`a = 0`da model bağımsızlığa iner ve `P(k≥14)` kupon kesitinde
**8,876·10⁻⁴** verir. §6.2'nin bağımsız olarak yayımladığı sayı
**8,6·10⁻⁴**tür. İki hesap birbirini tanımıyor; aynı sayıya varmaları
dördünlemenin ve kopulanın doğru kurulduğunun kanıtıdır.

─── Aynı bağımlılık, KUPON kapsamasında (§3.70) ─────────────────────────

Yukarıdaki her şey **tek kolonun** isabet sayısını sayar. Bir kupon
ailesinin `P(15/15)`'i başka bir büyüklüktür ve şekle göre farklı tepki
verebilir; `coklu.py` bunu yazılı bir varsayım olarak bırakmıştı. `kapsama`
aynı `a`yı üç sembole taşır (rütbe eşikleri — favori göstergesinde bu
modelin **birebir aynısı**, o yüzden `ρ` yeniden kalibre edilmez) ve 114
haftada ölçüldü: en kötü makul `a`da çoklu kuponun kazancı ×1,40'tan
×1,45'e **çıkıyor**, mutlak değerler %11'e kadar şişiyor. Ayrıntı §3.70,
üretici `scripts/bagimli_kapsama.py`.

Sonucu okumak için: `python -m spor_toto.kuyruk`.
"""
from __future__ import annotations

import math
import random
from collections.abc import Sequence
from operator import itemgetter
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.special import ndtr, ndtri

from .core import SEMBOLLER
from .ortak import kacak_dagilimi

if TYPE_CHECKING:  # yalnızca tip: `coklu` çalışma zamanında ÇEKİLMEZ, çünkü
    from .coklu import Kupon  # bu modülün kupon üretmeye ihtiyacı yok.

#: Gauss-Hermite düğüm sayısı. Ölçüm görülmeden seçildi; duyarlılığı
#: `tests/test_kuyruk.py::test_dugum_sayisi_karari_degistirmiyor` tutuyor.
DUGUM = 64

#: Kuyruk eşikleri. 12 ikramiyenin başladığı yer (§5.2 bulgu 1), 14 ise
#: kaplama motorunun garanti ettiği sayı — ikisi de üründen gelir, ölçümden
#: değil.
ESIKLER: tuple[int, ...] = (12, 14)


def _dugumler(dugum: int = DUGUM) -> tuple[np.ndarray, np.ndarray]:
    """Olasılıkçı Gauss-Hermite düğümleri, ağırlıkları 1'e normalize."""
    u, w = np.polynomial.hermite_e.hermegauss(dugum)
    return u, w / w.sum()


# ─── kesit ────────────────────────────────────────────────────────────────────

def hafta_kayitlari(haftalar: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hafta başına favori olasılıkları ve isabet göstergesi.

    **Favori göstergesi** kullanılır, üç sembolün tamamı değil. İki sebep:
    tek kolonun isabet sayısı tam olarak budur (yani ölçülen şey hedefin
    kendisidir), ve eski bekçi de aynı göstergeyi kullanıyordu — sayılar
    böylece karşılaştırılabilir kalıyor.
    """
    out: list[dict[str, Any]] = []
    for w in haftalar:
        probs, sonuc = w["probs"], w["results"]
        favs = [max(pr.items(), key=itemgetter(1))[0] for pr in probs]
        p = [pr[f] for pr, f in zip(probs, favs)]
        y = [1.0 if f == k else 0.0 for f, k in zip(favs, sonuc)]
        out.append({"n": len(p), "p": p, "y": y,
                    "K": sum(y), "M": sum(p),
                    "V": sum(x * (1.0 - x) for x in p)})
    return out


# ─── ölçüm ────────────────────────────────────────────────────────────────────

def olc(kayitlar: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Yanlılık, dağılım ve ortalama ikili korelasyon — üçü ayrı.

    Dönen `dagilim` bağımsızlıkta **1**'dir; `rho` bağımsızlıkta **0**.
    """
    if not kayitlar:
        return {"yanlilik": None, "dagilim": None, "rho": None,
                "n_hafta": 0, "n_mac": 0}

    n_mac = sum(k["n"] for k in kayitlar)
    b = sum(k["K"] - k["M"] for k in kayitlar) / n_mac

    sapma = [(k["K"] - k["M"]) - b * k["n"] for k in kayitlar]
    payda = sum(k["V"] for k in kayitlar)
    dagilim = sum(x * x for x in sapma) / payda if payda > 0 else None

    pay = alt = 0.0
    for k in kayitlar:
        r = [y - p - b for y, p in zip(k["y"], k["p"])]
        s = [math.sqrt(max(0.0, p * (1.0 - p))) for p in k["p"]]
        pay += (sum(r) ** 2 - sum(x * x for x in r)) / 2.0
        alt += (sum(s) ** 2 - sum(x * x for x in s)) / 2.0
    return {"yanlilik": b, "dagilim": dagilim,
            "rho": (pay / alt) if alt > 0 else None,
            "n_hafta": len(kayitlar), "n_mac": n_mac}


def bootstrap(kayitlar: Sequence[dict[str, Any]],
              tekrar: int | None = None,
              tohum: int | None = None) -> dict[str, Any]:
    """`dagilim` ve `rho` için hafta üzerinden bootstrap güven aralığı.

    Örnekleme birimi **hafta**dır; maç düzeyinde örneklemek ölçülmek istenen
    bağımlılığı tanım gereği yok ederdi.
    """
    from .evaluate import BOOTSTRAP_TEKRAR, BOOTSTRAP_TOHUM, GUVEN

    tekrar = BOOTSTRAP_TEKRAR if tekrar is None else tekrar
    tohum = BOOTSTRAP_TOHUM if tohum is None else tohum
    n = len(kayitlar)
    if n == 0:
        return {}

    rng = random.Random(tohum)
    dagilimlar: list[float] = []
    rholar: list[float] = []
    for _ in range(tekrar):
        ornek = [kayitlar[rng.randrange(n)] for _ in range(n)]
        s = olc(ornek)
        if s["dagilim"] is not None:
            dagilimlar.append(s["dagilim"])
        if s["rho"] is not None:
            rholar.append(s["rho"])

    def _aralik(diz: list[float]) -> dict[str, float | None]:
        if not diz:
            return {"alt": None, "ust": None}
        diz.sort()
        dis = (1.0 - GUVEN) / 2.0
        m = len(diz)
        return {"alt": diz[min(int(dis * m), m - 1)],
                "ust": diz[min(int((1.0 - dis) * m), m - 1)]}

    return {"dagilim": _aralik(dagilimlar), "rho": _aralik(rholar),
            "tekrar": tekrar}


# ─── ρ → kuyruk ───────────────────────────────────────────────────────────────

def _kosullu(p: Sequence[float], a: float,
             dugum: int = DUGUM) -> tuple[np.ndarray, np.ndarray]:
    """`U = u` verildiğinde koşullu olasılıklar, düğüm ağırlıklarıyla."""
    u, w = _dugumler(dugum)
    dizi = np.asarray(p, dtype=float)
    if a <= 0.0:
        return w, np.tile(dizi, (len(u), 1))
    z = ndtri(np.clip(dizi, 1e-12, 1 - 1e-12))
    m = (z[None, :] - math.sqrt(a) * u[:, None]) / math.sqrt(1.0 - a)
    return w, ndtr(m)


def uretilen_rho(kesit: Sequence[Sequence[float]], a: float,
                 dugum: int = DUGUM) -> float:
    """Latent `a`nın ürettiği ortalama ikili Bernoulli korelasyonu.

    Çift toplamı açıkça kurulmaz: `Σ_{i<j} x_i x_j = ((Σx)² − Σx²)/2` özdeşliği
    hem `n²` bellekten hem de `bahisci`nin düştüğü türden bir yavaşlıktan
    kurtarır.
    """
    pay = alt = 0.0
    for p in kesit:
        w, pu = _kosullu(p, a, dugum)
        dizi = np.asarray(p, dtype=float)
        capraz = float((w * ((pu.sum(axis=1) ** 2) - (pu ** 2).sum(axis=1))).sum()) / 2.0
        bagimsiz = ((dizi.sum() ** 2) - (dizi ** 2).sum()) / 2.0
        s = np.sqrt(np.clip(dizi * (1.0 - dizi), 0.0, None))
        pay += capraz - bagimsiz
        alt += ((s.sum() ** 2) - (s ** 2).sum()) / 2.0
    return pay / alt if alt > 0 else 0.0


def latent_coz(kesit: Sequence[Sequence[float]], hedef: float,
               dugum: int = DUGUM, adim: int = 40) -> float:
    """Hedef `ρ`yu veren latent `a` — ikiye bölme.

    `hedef ≤ 0` ise `a = 0` döner: tek faktör modeli **negatif** ortak etken
    üretemez. Bu bir sınırlamadır ve saklanmıyor — ölçülen nokta tahmini
    negatif çıktığında modelin söyleyeceği tek şey *"kuyruk şişmiyor"*dur,
    ve kararın ihtiyacı olan da budur.
    """
    if hedef <= 0.0:
        return 0.0
    lo, hi = 0.0, 0.9
    for _ in range(adim):
        orta = (lo + hi) / 2.0
        if uretilen_rho(kesit, orta, dugum) < hedef:
            lo = orta
        else:
            hi = orta
    return (lo + hi) / 2.0


def kuyruk(p: Sequence[float], a: float, esik: int,
           dugum: int = DUGUM) -> float:
    """`P(K ≥ esik)` — koşullu bağımsızlık + Poisson-binom + dördünleme."""
    w, pu = _kosullu(p, a, dugum)
    n = len(p)
    if esik > n:
        return 0.0
    toplam = 0.0
    for q in range(pu.shape[0]):
        d = kacak_dagilimi([1.0 - float(x) for x in pu[q]])
        toplam += float(w[q]) * sum(d[m] for m in range(0, n - esik + 1))
    return toplam


def kuyruk_etkisi(kesit: Sequence[Sequence[float]], rho: float,
                  esikler: Sequence[int] = ESIKLER,
                  dugum: int = DUGUM) -> dict[str, Any]:
    """Verilen `ρ`da kuyruk olasılıkları ve bağımsızlığa göre oranı."""
    a = latent_coz(kesit, rho, dugum)
    out: dict[str, Any] = {"rho": rho, "latent_a": a, "esikler": {}}
    for esik in esikler:
        bagimsiz = sum(kuyruk(p, 0.0, esik, dugum) for p in kesit) / len(kesit)
        bagimli = sum(kuyruk(p, a, esik, dugum) for p in kesit) / len(kesit)
        out["esikler"][str(esik)] = {
            "bagimsiz": bagimsiz,
            "bagimli": bagimli,
            "oran": (bagimli / bagimsiz) if bagimsiz > 0 else None,
        }
    return out


# ─── kupon kapsaması: aynı bağımlılık, üç sembol ──────────────────────────────
#
# Yukarıdaki hesap **tek kolonun** isabet sayısını sayar. Çoklu kupon sorusu
# başkadır: bir kupon ailesinin `P(15/15)`'i, yani gerçek kolonun oynanan
# kümeye düşme olasılığı. `coklu.p_onbes` onu maçlar **bağımsız** sayarak
# hesaplar ve `coklu.py`nin "Sınır" bölümü bunu yazılı bir varsayım olarak
# bırakmıştı.
#
# ─── Neden `kuyruk()` bu soruya cevap VERMEZ ─────────────────────────────
#
# Akla gelen ilk yol yanlıştır: her kupon için maç başına "kapsandı"
# göstergesi kurup (`q_i = Σ_{s∈seçim} p_is`) yukarıdaki ikili modeli
# çalıştırmak. O model göstergeleri `{Z_i < Φ⁻¹(q_i)}` biçiminde **iç içe**
# eşikler yapar; oysa iki kuponun eksen maçındaki seçimleri **ayrıktır**
# (biri "1", öteki "0"). İç içe eşiklerle kurulan olasılıklar toplandığında
# aynı sonucu iki kez sayar ve eksen maçında üç sembolün toplamı 1 vermez.
#
# ─── Seçilen model, ve `ρ`nun onu neden KALİBRE ETTİĞİ ───────────────────
#
# Bu yüzden model üç sembolün **tamamı** üzerine kurulur ve `Z_i` maçın
# sembollerini **rütbeye göre** keser::
#
#     sembol = favori    ⟺  Z_i < Φ⁻¹(p₁)
#            = ikinci    ⟺  Φ⁻¹(p₁) ≤ Z_i < Φ⁻¹(p₁+p₂)
#            = üçüncü    ⟺  aksi
#
# Bu, yukarıdaki ikili modelin **genellemesidir, başka bir model değil**:
# favori göstergesinin eşiği birebir aynı (`Φ⁻¹(p₁)`), yani `ρ → a`
# çevirisi (`latent_coz`) olduğu gibi geçerlidir ve ölçülen `ρ` yeniden
# kalibre edilmez. Rütbe sırası bir tercih değil **zorunluluk**: `ρ` favori
# göstergesinden ölçüldü (§3.46) ve modeli o göstergede ölçümle aynı yapan
# tek kesim sırası budur. Sembolleri sonuç ekseninde (`1/0/2`) sıralayan
# model de kurulabilir ama onun ortak etkeni başka bir mekanizmadır ("ev
# sahibi günü") ve ölçülen `ρ` onu kalibre etmez.
#
# Modelin `ρ` tarafından **belirlenmeyen** tek parçası, kötü haftada kalan
# kütlenin 2. ile 3. sembol arasında nasıl paylaşıldığıdır. İki uç ayrı ayrı
# hesaplanır (`KAPSAMA_MODELLERI`) ve ikisi de aynı `a`ya oturur; aradaki
# fark varsayımın bedelidir ve ölçülür — uydurulmaz.
#
# Kuponlar ayrık kolon kümeleri olduğu için `U = u` verildiğinde toplam,
# kupon olasılıklarının **toplamıdır** (`coklu.p_onbes`in gerekçesinin
# aynısı); dördünleme yalnızca dışta durur.

#: Kapsama modelinde favori DIŞI kütlenin ortak etkene tepkisi. `rutbe`:
#: kötü hafta 3. sembole de kayar (rütbe eşikleri). `oransal`: kaçan kütle
#: 2. ile 3. sembol arasında haftanın **kendi** oranını korur, yani ortak
#: etken yalnızca favori ↔ favori-dışı ayrımını oynatır. İkisi de `a = 0`da
#: bağımsızlığa iner ve ikisi de favori göstergesinde aynı modeldir.
KAPSAMA_MODELLERI: tuple[str, ...] = ("rutbe", "oransal")


def _kosullu_sembol(probs_listesi: Sequence[dict[str, float]], a: float,
                    model: str = "rutbe", dugum: int = DUGUM
                    ) -> tuple[np.ndarray, np.ndarray]:
    """`U = u` verildiğinde ÜÇ sembolün koşullu olasılıkları + ağırlıklar.

    Dönen dizi `(düğüm, maç, 3)` boyutundadır ve son eksen
    `core.SEMBOLLER` düzenindedir — rütbe düzeninde değil. Rütbe hesabın
    içinde kalır; dışarıya sembol verilir, çünkü kupon seçimleri semboldür
    ve ikisini karıştırmak `coklu._kuponlari_kur`un ilk hatasıydı.

    Dördünleme ağırlıklarıyla integre edildiğinde satırlar **girdi
    olasılıklarının kendisini** verir (bekçisi
    `test_kapsama_marjinalleri_GIRDIYI_veriyor`): model bağımlılığı ekler,
    tahmini değiştirmez.
    """
    if model not in KAPSAMA_MODELLERI:
        raise ValueError(f"Bilinmeyen kapsama modeli: {model!r} "
                         f"(gecerli: {'/'.join(KAPSAMA_MODELLERI)})")
    p = np.array([[float(d.get(s, 0.0)) for s in SEMBOLLER]
                  for d in probs_listesi], dtype=float)
    if p.ndim != 2 or p.shape[0] == 0:
        raise ValueError("Bos olasilik listesi.")
    toplam = p.sum(axis=1, keepdims=True)
    if np.any(toplam <= 0):
        raise ValueError("Bir macin olasilik toplami sifir.")
    p = p / toplam

    u, w = _dugumler(dugum)
    rutbe = np.argsort(-p, axis=1)                       # 0: favori, 2: üçüncü
    sirali = np.take_along_axis(p, rutbe, axis=1)

    if a <= 0.0:
        q_sirali = np.tile(sirali, (len(u), 1, 1))
    else:
        z = ndtri(np.clip(np.cumsum(sirali[:, :2], axis=1), 1e-12, 1 - 1e-12))
        F = ndtr((z[None, :, :] - math.sqrt(a) * u[:, None, None])
                 / math.sqrt(1.0 - a))                   # (düğüm, maç, 2)
        q_sirali = np.empty((len(u), p.shape[0], 3))
        q_sirali[:, :, 0] = F[:, :, 0]
        if model == "rutbe":
            q_sirali[:, :, 1] = F[:, :, 1] - F[:, :, 0]
        else:
            kalan = sirali[:, 1] + sirali[:, 2]
            oran = np.divide(sirali[:, 1], kalan,
                             out=np.zeros_like(kalan), where=kalan > 0)
            q_sirali[:, :, 1] = (1.0 - F[:, :, 0]) * oran[None, :]
        # Üçüncü sembol **çıkarmayla**: satır toplamı tam 1 kalsın.
        q_sirali[:, :, 2] = np.clip(
            1.0 - q_sirali[:, :, 0] - q_sirali[:, :, 1], 0.0, None)

    q = np.empty_like(q_sirali)
    np.put_along_axis(q, np.broadcast_to(rutbe[None], q.shape), q_sirali,
                      axis=2)
    return w, q


def kapsama(probs_listesi: Sequence[dict[str, float]],
            kuponlar: Sequence[Kupon], a: float,
            model: str = "rutbe", dugum: int = DUGUM) -> float:
    """Kupon ailesinin `P(15/15)`'i — hafta içi bağımlılık altında.

    `a = 0`da dönen sayı `coklu.p_onbes`in **ta kendisidir** (bekçisi
    `test_kapsama_a_SIFIRDA_coklu_p_onbes`); `a > 0` aynı kuponu bağımlı
    haftada yeniden fiyatlar. Kuponların ayrık olduğu varsayılır —
    `coklu.coklu_plan` öyle üretir.
    """
    w, q = _kosullu_sembol(probs_listesi, a, model, dugum)
    n = q.shape[1]
    indeks = {s: j for j, s in enumerate(SEMBOLLER)}
    maske = np.zeros((len(kuponlar), n, 3))
    for k, kupon in enumerate(kuponlar):
        if len(kupon.secimler) != n:
            raise ValueError(f"Kupon {n} macin secimini tasimali: "
                             f"{len(kupon.secimler)}")
        for i, sec in enumerate(kupon.secimler):
            for s in sec:
                maske[k, i, indeks[s]] = 1.0
    if not len(maske):
        return 0.0
    # `einsum` süs değil: 729 kuponu tek tek dolaşmak 114 haftalık kıyasta
    # ölçülür bir yavaşlıktı (kupon başına küçük numpy çağrısı).
    kapsanan = np.einsum("qis,kis->kqi", q, maske)        # (kupon, düğüm, maç)
    return float((w * kapsanan.prod(axis=2).sum(axis=0)).sum())


# ─── rapor ────────────────────────────────────────────────────────────────────

def _kesit_olc(ad: str, haftalar: Sequence[dict[str, Any]],
               tekrar: int | None = None) -> dict[str, Any]:
    kayitlar = hafta_kayitlari(haftalar)
    sonuc = olc(kayitlar)
    sonuc["ad"] = ad
    sonuc["aralik"] = bootstrap(kayitlar, tekrar=tekrar)
    return sonuc


def rapor(tekrar: int | None = None) -> dict[str, Any]:
    """Üç kesitte bağımlılık, ve kupon kesitinde kuyruk çevirisi.

    Kesitler bilerek üç tanedir ve **güçleri farklıdır**: korpus 183 hafta ile
    tek gerçek güç kaynağıdır, kupon kesitleri ise sorunun sorulduğu yerdir.
    İkisi ayrı raporlanır çünkü biri ötekinin yerine geçmez — korpus haftası
    22 ligden ~170 maç toplar, kupon haftası 15 maçtır.

    Durma kuralı (§6.2, **ölçüm görülmeden yazıldı**): bootstrap %95 aralığı
    sıfırı kesiyorsa eksen kapanır ve bugünkü geri test *savunulmuş* olur.
    """
    from .egitim import korpus_haftalari
    from .evaluate import kupon_kesiti_tum, olculebilir_haftalar

    kesitler = [
        _kesit_olc("kupon_varsayilan", olculebilir_haftalar(), tekrar),
        _kesit_olc("kupon_genis", kupon_kesiti_tum(), tekrar),
        _kesit_olc("korpus", korpus_haftalari(), tekrar),
    ]

    kupon = [k["p"] for k in hafta_kayitlari(kupon_kesiti_tum())]
    korpus = next(k for k in kesitler if k["ad"] == "korpus")
    genis = next(k for k in kesitler if k["ad"] == "kupon_genis")

    # Kuyruk çevirisi **en kötü makul** ρ'da okunur: iki kesitin üst
    # sınırlarının büyüğü. Nokta tahmini negatifken kuyruk zaten şişmiyor;
    # kararı belirleyen şey aralığın nereye kadar izin verdiğidir.
    ustler = [k["aralik"]["rho"]["ust"] for k in (korpus, genis)
              if k["aralik"].get("rho", {}).get("ust") is not None]
    en_kotu = max(ustler) if ustler else 0.0

    etki = {
        "nokta": kuyruk_etkisi(kupon, max(0.0, genis["rho"] or 0.0)),
        "korpus_ust": kuyruk_etkisi(kupon, korpus["aralik"]["rho"]["ust"]),
        "en_kotu_ust": kuyruk_etkisi(kupon, en_kotu),
    }

    keser = all(
        (k["aralik"]["rho"]["alt"] or 0) <= 0 <= (k["aralik"]["rho"]["ust"] or 0)
        for k in kesitler)
    return {
        "kesitler": kesitler,
        "kuyruk": etki,
        "durma_kurali": {
            "kural": ("bootstrap %95 araligi sifiri KESIYORSA eksen kapanir "
                      "ve bugunku geri test savunulmus olur (§6.2)"),
            "aralik_sifiri_kesiyor": keser,
            "karar": "eksen kapandi" if keser else "eksen acik — kuyruk duzeltilmeli",
        },
    }


def _yazdir(sonuc: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print(f"{'kesit':<20} {'hafta':>6} {'maç':>7} {'yanlılık':>9} "
          f"{'dağılım':>8} {'ρ':>10} {'%95 aralık (ρ)':>22}")
    for k in sonuc["kesitler"]:
        a = k["aralik"]["rho"]
        print(f"{k['ad']:<20} {k['n_hafta']:>6} {k['n_mac']:>7} "
              f"{k['yanlilik']:>+9.4f} {k['dagilim']:>8.4f} {k['rho']:>+10.5f} "
              f"  [{a['alt']:+.5f}, {a['ust']:+.5f}]")

    print("\nkuyruk çevirisi (kupon kesiti, tek kolon):")
    print(f"{'senaryo':<16} {'ρ':>9} {'a':>7} "
          f"{'P(K≥12)':>11} {'oran':>7} {'P(K≥14)':>11} {'oran':>7}")
    for ad, e in sonuc["kuyruk"].items():
        b12, b14 = e["esikler"]["12"], e["esikler"]["14"]
        print(f"{ad:<16} {e['rho']:>+9.5f} {e['latent_a']:>7.4f} "
              f"{b12['bagimli']:>11.4e} {b12['oran']:>7.2f} "
              f"{b14['bagimli']:>11.4e} {b14['oran']:>7.2f}")

    d = sonuc["durma_kurali"]
    print(f"\nkural : {d['kural']}")
    print(f"karar : {d['karar'].upper()}")


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    _yazdir(rapor())
