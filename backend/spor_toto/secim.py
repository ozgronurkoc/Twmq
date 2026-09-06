"""Kuponun işaretlerini **hedefe göre** seçer — eşiğe göre değil.

Bugüne kadar seçim `backtest.secim_uret` ile yapılıyordu: her maça tek
başına bakılıp favorinin olasılığı iki sabit eşiğe vuruluyordu. O kural
haftanın şeklini görmez, bütçeyi bilmez, kaplama bedelini bilmez ve
**hiçbir yerde asıl önemsenen sayıyı optimize etmez.**

Asıl sayı `P(en iyi kolon ≥ 12)`'dir ve aritmetiği tam olarak şudur:

    k maç seçim kümesinin DIŞINDA kalırsa o k maç her kolonda yanlıştır.
    Kalan 15−k maç içeridedir ve **düz oynandığı için hepsi oynanır**, yani
    bir kolon onların hepsini tutturur:

        en iyi kolon = 15 − k

        k=0 → 15    k=1 → 14    k=2 → 13    k=3 → 12

    ⇒ P(en iyi kolon ≥ 12) = P(k ≤ 3)

Bu bir **eşitliktir**, alt sınır değil. Depo bir zamanlar kuponu kaplama
koduyla kuruyordu; orada en iyi kolon `≥ 14−k` idi, yani `P(k ≤ 2)`
*temkinli* bir hedefti ve gerçekleşen isabet onun üstünde çıkabiliyordu.
Kaplama söküldü (`docs/DUZ_SISTEME_GECIS.md`) ve o temkin payı da gitti:
buradaki sayı artık ne iyimser ne temkinli, **tam**.

─── Yapının sadeleştirdiği nokta ─────────────────────────────────────────

Bir maçın kaçak olasılığı yalnızca kaç sembol işaretlendiğine bağlıdır:

    banko (1 sembol)   q = 1 − p₁
    çifte (2 sembol)   q = p₃        (en düşük olasılıklı sembol)
    üçlü  (3 sembol)   q = 0         ← üçlü ASLA kaçmaz

Bedel ise yalnızca sayılara bağlıdır: `2^a · 3^b`, burada `a` çifte, `b`
üçlü sayısıdır — yani seçim kümesinin büyüklüğü. Bu iki olgu, aramayı küçük
ve **tam** çözülebilir bir probleme indirger.

─── Bütçe neden varsayılansız ────────────────────────────────────────────

Üçlünün kaçağı sıfırdır. Tavan yoksa `P(k ≤ 3)`'ü enbüyükleyen plan **her
maçı üçlü** yapmaktır: `3¹⁵ = 14.348.907` kolon, `P = 1,0`, ₺10 kolon
bedeliyle ₺143 milyon. Yani "bütçe yok" matematiksel olarak dejenere bir
cevaptır ve `en_iyi_secim` bunu sessizce üretmez: `butce` zorunludur.

─── Neden Pareto DP, neden açgözlü değil ─────────────────────────────────

Amaç bir Poisson-binom kuyruğudur ve maçlar arasında ayrışmaz; açgözlü bir
kural masada değer bırakır. Ama şu gözlem aramayı tamamlar: ileride yapılacak
her evrişim, kümülatif toplamların **pozitif doğrusal birleşimidir** —

    son_cum₂ = Σⱼ (gelecek pⱼ) · (şimdiki cum₂₋ⱼ)

Dolayısıyla `(cum₀, cum₁, cum₂)` üçlüsünde baskın olan bir durum, gelecekte
de baskın kalır. Pareto sınırını taşımak **kesin** çözüm verir; budama bir
yaklaşıklık değil, yalnızca baskılanmışları atmaktır.

    python -m spor_toto.secim            # gecen sezonun kiyasi
"""
from __future__ import annotations

import argparse
import json
import math
from typing import Any, NamedTuple

from .core import SEMBOLLER, sirala_semboller
from .ortak import kacak_dagilimi

#: Kaç kaçağa kadar hedefe ulaşılmış sayılır. 3, `P(en iyi kolon ≥ 12)`
#: demektir (yukarıdaki aritmetik: en iyi kolon = 15 − k). Ürün kararı:
#: ikramiye eşiği 12'dir, 15 bir yan üründür.
#:
#: **Kaplama döneminde bu sayı 2'ydi** ve aynı para hedefini gösteriyordu:
#: orada en iyi kolon 14 − k idi, yani ≥12 için k ≤ 2 gerekiyordu. Sayı
#: değişti çünkü aritmetik değişti; hedef (en az 12) değişmedi.
VARSAYILAN_KACAK_ESIGI = 3

#: Bir durumda tutulacak en fazla Pareto noktası. Sınır güvenlik supabı;
#: ölçümde sınıra dayanılmadı (en yoğun hafta 12 nokta gördü) ve dayanılsa
#: bile yalnızca baskılanmış adaylar düşer.
PARETO_SINIRI = 64


class Secim(NamedTuple):
    """Bir haftanın işaret planı ve onun ölçülmüş hedefi."""

    secimler: list[list[str]]
    bedel: int
    p_hedef: float
    banko: int
    cift: int
    uclu: int

    @property
    def picks(self) -> list[str]:
        """Kupon biçimi: her maç için işaretlerin bitişik yazımı."""
        return ["".join(s) for s in self.secimler]


def bedel_hesapla(cift: int, uclu: int) -> int:
    """Düz (tam sistem) kolon bedeli — seçim kümesinin büyüklüğü.

    Her maçta işaretlenen sembollerin çarpımı: `2^a · 3^b`. Tek işaretli
    maçlar 1 ile çarpar, yani bedeli hiç büyütmez.

    **Eskiden bu formül `/2⁷ · 16` taşıyordu** çünkü kupon kaplama koduyla
    kuruluyordu ve Hamming(7,4) bloğu yedi çifteyi 16 satıra sığdırıyordu.
    O katman söküldü (`docs/DUZ_SISTEME_GECIS.md`): bedel artık sekiz kat
    pahalı ama en iyi kolon 14 değil **15** tutturuyor ve "en az yedi çifte"
    şartı ortadan kalktı — ölçümde kuponun asıl kazandığı şey o şartın
    kalkmasıydı.
    """
    return 2 ** cift * 3 ** uclu


def _sirali(probs: dict[str, float]) -> list[tuple[str, float]]:
    """Semboller olasılığa göre büyükten küçüğe; eşitlikte kupon düzeni."""
    return sorted(probs.items(),
                  key=lambda kv: (-kv[1], SEMBOLLER.index(kv[0])))


def kacak_olasiligi(probs: dict[str, float], seviye: int) -> float:
    """`seviye` sembol işaretlenirse maçın kaçma olasılığı."""
    s = _sirali(probs)
    return max(0.0, 1.0 - sum(v for _, v in s[:seviye]))


def hedef_olasiligi(probs_listesi: list[dict[str, float]],
                    secimler: list[list[str]],
                    esik: int = VARSAYILAN_KACAK_ESIGI) -> float:
    """Verilen işaretler için `P(k ≤ esik)` — kuponun ölçülmüş hedefi."""
    q = [max(0.0, 1.0 - sum(p.get(s, 0.0) for s in sec))
         for p, sec in zip(probs_listesi, secimler)]
    return sum(kacak_dagilimi(q)[:esik + 1])


def en_iyi_secim(probs_listesi: list[dict[str, float]],
                 butce: int,
                 esik: int = VARSAYILAN_KACAK_ESIGI) -> Secim | None:
    """Bütçe içinde `P(k ≤ esik)`'i **enbüyükleyen** işaret planı.

    `butce` kolon cinsindendir ve **zorunludur**; varsayılanı yoktur.
    Sebebi modül başlığında: üçlünün kaçağı sıfır olduğu için tavansız
    aramanın cevabı her zaman "hepsi üçlü"dür (`3¹⁵` kolon, `P = 1,0`).
    Dejenere bir cevabı sessizce üretmektense hata atmak doğrudur.

    `None` döner ancak bütçe **hiçbir** planı karşılamıyorsa; düzde en ucuz
    plan 15 maçın hepsi tek, yani 1 kolondur. Pratikte `butce ≥ 1` her zaman
    bir plan bulur — kaplama dönemindeki "yedi çifte kurulamıyor" hâli artık
    yok.

    Arama, kaçak eşiğine kadarki kümülatif olasılıkları taşır; `esik` büyürse
    taşınan vektör de büyür, karmaşıklık `esik` ile doğrusaldır.
    """
    if butce is None:
        raise ValueError(
            "Butce zorunludur — tavansiz aramanin cevabi dejeneredir "
            "(hepsi uclu, 3^15 = 14.348.907 kolon). Bkz. modul basligi.")
    if butce <= 0:
        raise ValueError("Butce pozitif olmali.")
    n = len(probs_listesi)
    if n == 0:
        return None

    sirali = [_sirali(p) for p in probs_listesi]
    # Her maç için seviye başına kaçak olasılığı. Üçlü her zaman 0'dır;
    # yine de formülden hesaplanıyor ki olasılıklar 1'e toplanmadığında
    # (bozuk girdi) sessizce sıfır varsayılmasın.
    q_seviye = [[max(0.0, 1.0 - sum(v for _, v in s[:k])) for k in (1, 2, 3)]
                for s in sirali]

    # Durum: (çifte, üçlü) -> Pareto kümesi [(kümülatifler, seviye izleği)]
    baslangic: tuple[float, ...] = tuple([1.0] * (esik + 1))
    durumlar: dict[tuple[int, int], list[tuple[tuple[float, ...], tuple[int, ...]]]] = {
        (0, 0): [(baslangic, ())],
    }

    for i in range(n):
        kalan_mac = n - i - 1
        yeni: dict[tuple[int, int], list[tuple[tuple[float, ...], tuple[int, ...]]]] = {}
        for (a, b), kume in durumlar.items():
            for seviye in (1, 2, 3):
                ya, yb = a + (seviye == 2), b + (seviye == 3)
                # Budama: kalan maçların hepsi tek olsa bile bedel bütçeyi
                # aşıyorsa bu dal ölüdür (tek, bedeli 1 ile çarpar).
                # Kaplama döneminde burada ikinci bir budama daha vardı —
                # "kalan maçlarla yedi çifteye ulaşılamıyorsa dal kapanır";
                # o şart Hamming bloğunundu ve katmanla birlikte kalktı.
                if bedel_hesapla(ya, yb) > butce:
                    continue
                qq = q_seviye[i][seviye - 1]
                for kumulatif, izlek in kume:
                    # cum_m' = cum_m·(1−q) + cum_{m−1}·q
                    guncel = [kumulatif[0] * (1.0 - qq)]
                    for m in range(1, esik + 1):
                        guncel.append(kumulatif[m] * (1.0 - qq)
                                      + kumulatif[m - 1] * qq)
                    yeni.setdefault((ya, yb), []).append(
                        (tuple(guncel), (*izlek, seviye)))
        durumlar = {k: _pareto(v) for k, v in yeni.items()}
        if not durumlar:
            return None

    en: tuple[float, int, tuple[int, ...]] | None = None
    for (a, b), kume in durumlar.items():
        c = bedel_hesapla(a, b)
        if c > butce:
            continue
        for kumulatif, izlek in kume:
            # Eşitlikte UCUZ olan kazanır: aynı hedefe daha az kolonla
            # ulaşmak her zaman tercih edilir.
            if en is None or (kumulatif[esik], -c) > (en[0], -en[1]):
                en = (kumulatif[esik], c, izlek)
    if en is None:
        return None

    p_hedef, maliyet, izlek = en
    secimler = [sirala_semboller([s for s, _ in sirali[i][:izlek[i]]])
                for i in range(n)]
    return Secim(
        secimler=secimler,
        bedel=maliyet,
        p_hedef=p_hedef,
        banko=sum(1 for s in secimler if len(s) == 1),
        cift=sum(1 for s in secimler if len(s) == 2),
        uclu=sum(1 for s in secimler if len(s) == 3),
    )


def _pareto(adaylar: list[tuple[tuple[float, ...], tuple[int, ...]]],
            sinir: int = PARETO_SINIRI
            ) -> list[tuple[tuple[float, ...], tuple[int, ...]]]:
    """Baskılanmış adayları atar — kesin budama.

    Bir aday, başka bir adayın kümülatiflerinin **hepsinde** eşit ya da
    altında kalıyorsa (ve en az birinde kesin altındaysa) baskılanmıştır:
    gelecekteki her evrişim kümülatiflerin pozitif doğrusal birleşimi
    olduğu için o aday hiçbir sonda öne geçemez.
    """
    adaylar.sort(key=lambda t: tuple(-x for x in reversed(t[0])))
    tutulan: list[tuple[tuple[float, ...], tuple[int, ...]]] = []
    for kumulatif, izlek in adaylar:
        if any(all(o >= y for o, y in zip(onceki, kumulatif))
               for onceki, _ in tutulan):
            continue
        tutulan.append((kumulatif, izlek))
        if len(tutulan) >= sinir:
            break
    return tutulan


# ─── kalabalık ayarı — hedefi bırakmadan az oynanana kaymak ───────────────

#: `P(k ≤ 2)`'den vazgeçilecek EN ÇOK oran.
#:
#: **Artık bir harcama kararı değil, ÖLÇÜM SONUCU — ve sıfır.**
#:
#: Bu sabit uzun süre `0.05` yazıyordu ve başlığı dürüstçe *"bu bir ölçüm
#: değil, harcama kararıdır"* diyordu. Ölçüldü (`docs/KAZANMA_PLANI.md`
#: Faz S) ve optimal değer **sıfır** çıktı — üç bağımsız yoldan:
#:
#: 1. `kalabalik_ayari`, ölçülen kalabalık modeliyle (`kalabalik.OLCULEN`)
#:    kayıp bütçesi 0'dan **0,70**'e kadar taransa bile **tek bir maçın
#:    işaretini değiştirmiyor**.
#: 2. Doğrudan `E[TL]` üzerinde yerel arama: 25 haftanın 25'inde taban plan
#:    zaten en iyi; tek maçlık en iyi değişimin kazancı **tam 1,0000×**.
#:    (Arama dejenere değil: favoriyi bırakmak E[TL]'yi 0,39×'e düşürüyor.)
#: 3. Mekanizma analitik: ölçülen model `o(s) ∝ p(s)^λ` **monotondur**,
#:    yani sembol sıralamasını korur. Kalabalıktan sapmak ancak daha düşük
#:    olasılıklı sembole geçerek mümkün olur ve tutturma kaybı, pay
#:    kazancını her bantta eziyor.
#:
#: **Sıfır "ayar kapalı" demek değildir:** hedefi hiç düşürmeyen değişimler
#: hâlâ yapılır (iki sembol kümesi aynı olasılığı taşıyıp farklı kalabalık
#: çekebilir). Değişen şey, tutturma olasılığının **satılmamasıdır**.
#:
#: **Ve bu sonuç modelin monotonluğuna bağlıdır.** Kayıtlı oynanma payları
#: 60 maçın **21'inde** piyasadan farklı sıralama gösteriyor — monoton bir
#: model bunu üretemez. Kenar varsa oradadır ve bu sabit onu görmez.
VARSAYILAN_KAYIP_ORANI = 0.0

#: Bir durumda tutulacak en fazla Pareto noktası. `PARETO_SINIRI` ile aynı
#: gerekçe, farklı sayı: buradaki cephe bir boyut daha taşıyor (kalabalık
#: skoru) ve doğal olarak daha geniş. Sınıra dayanılırsa `kirpildi` açılır —
#: yani sessizce yaklaşık olunmaz.
KALABALIK_PARETO_SINIRI = 256

#: Logaritma alınmadan önce paylara uygulanan taban. Hiç oynanmamış bir
#: sembol kümesi sonsuz iyidir (`log 0 = −∞`); sonsuzla aritmetik yapmamak
#: için değer buraya kırpılır.
_PAY_TABANI = 1e-12


class KalabalikAyar(NamedTuple):
    """Kalabalık ayarının sonucu — taban planla birlikte okunur."""

    secimler: list[list[str]]
    p_hedef: float
    taban_p_hedef: float
    kume_ici: float
    kalabalik_ici: float
    #: `kume_ici / kalabalik_ici`. 1'in ÜSTÜ, küme olasılığına göre **az**
    #: oynanmış demektir — tutarsa ikramiye daha az bölünür.
    oran: float
    taban_oran: float
    degisimler: list[dict[str, Any]]
    kirpildi: bool


def _kume_olasiligi(dagilim: dict[str, float], sec: list[str]) -> float:
    return sum(max(0.0, float(dagilim.get(s, 0.0))) for s in sec)


def _carpim(dagilimlar: list[dict[str, float]],
            secimler: list[list[str]]) -> float:
    """Maçlar bağımsız varsayılarak seçim kümesine düşme olasılığı."""
    toplam = 1.0
    for dagilim, sec in zip(dagilimlar, secimler):
        toplam *= _kume_olasiligi(dagilim, sec)
    return toplam


def _adaylar(probs: dict[str, float], oynanma: dict[str, float],
             taban: list[str]) -> list[list[str]]:
    """Bir maçta denenmeye değer sembol kümeleri — taban her zaman ilk.

    İki eleme, ikisi de **kayıpsız**:

    1. **Ne amacı ne kısıtı ilerleten aday atılır.** Amaç
       `küme-içi / kalabalık-içi` çarpımını enbüyüklemek, kısıt ise
       `p_in`den geliyor; ikisinde de tabanı geçemeyen bir küme hiçbir işe
       yaramaz. Pratikte taban o boyuttaki **en olası** kümedir
       (`en_iyi_secim` öyle kurar) ve `p_in` koşulu hiç tutmaz — ama koşul
       yazılı, çünkü fonksiyon keyfî bir planla da çağrılabilir ve o zaman
       elemenin kayıpsızlığı ona bağlı. Kalabalık piyasayla aynıysa bütün
       oranlar eşit çıkar ve ayar hiçbir şey yapmaz — doğru davranış.
    2. **Baskılanmış aday atılır.** `p_in`i de oranı da başka bir adaydan
       düşükse o aday hiçbir sonda öne geçemez.
    """
    k = len(taban)
    if k >= len(SEMBOLLER):
        return [list(taban)]
    from itertools import combinations

    def olcu(sec: list[str]) -> tuple[float, float]:
        p = _kume_olasiligi(probs, sec)
        c = _kume_olasiligi(oynanma, sec)
        return p, (p / c) if c > 0 else float("inf")

    taban_p, taban_oran = olcu(list(taban))
    ham: list[tuple[list[str], float, float]] = []
    for aday in combinations(SEMBOLLER, k):
        sec = sirala_semboller(aday)
        if sec == sirala_semboller(taban):
            continue
        p, oran = olcu(sec)
        if oran <= taban_oran and p <= taban_p:
            continue
        ham.append((sec, p, oran))

    out = [list(taban)]
    for sec, p, oran in ham:
        if any(op >= p and oo >= oran and (op, oo) != (p, oran)
               for _, op, oo in ham):
            continue
        out.append(sec)
    return out


def kalabalik_ayari(probs_listesi: list[dict[str, float]],
                    oynanma_listesi: list[dict[str, float]],
                    secimler: list[list[str]],
                    kayip_orani: float = VARSAYILAN_KAYIP_ORANI,
                    esik: int = VARSAYILAN_KACAK_ESIGI) -> KalabalikAyar:
    """İşaret **sayılarını** koruyup **hangi sembol** sorusunu yeniden sorar.

    `en_iyi_secim` her maçta en olası `k` sembolü işaretler ve kalabalığı
    hiç görmez. Oysa müşterek bahiste kazanç `p_piyasa − oynanma_payı`
    farkından doğar (`DIS_INCELEME.md` §7, kapalı formu `getiri`de): aynı
    olasılığı taşıyan iki küme, ikramiyenin kaç kolona bölüneceği
    bakımından aynı DEĞİLDİR.

    ─── Neden yalnızca sembol değişiyor, sayı değil ──────────────────────

    İşaret sayıları kuponun **bedelini** belirler (`bedel_hesapla`). Sayıları
    da oynatmak bütçeyi değiştirir ve iki farklı kararı (ne kadar harcarım /
    kalabalıktan nasıl saparım) tek adımda karıştırırdı. Sayılar sabit
    tutulunca ayar **bedava**dır: aynı kolon sayısı, aynı satır, aynı motor.

    ─── Kısıt ölçüde, amaç oranda ───────────────────────────────────────

    Kısıt: `P(k ≤ esik) ≥ (1 − kayip_orani) · taban`. Bu sayı kuponun asıl
    ölçüsüdür (`secim` modül başlığı) ve ayar onu **açıkça beyan edilen**
    bir oranın ötesinde harcayamaz.

    Amaç: `küme-içi / kalabalık-içi` **oranını** enbüyüklemek. Amacın oran
    olması esastır ve ilk sürüm burada yanlıştı: yalnızca kalabalık-içini
    küçültmek, kalabalık piyasayla birebir aynı olduğunda bile daralmayı
    ödüllendiriyordu — hiçbir şey kazandırmayan bir kayıp. Oran, tam olarak
    sayfada raporlanan sayıdır; enbüyüklenen ile gösterilen aynı şey olmalı.

    ─── Arama neden kesin ────────────────────────────────────────────────

    Amaç maçlar üzerinde toplanabilir (`Σ log(p_i/c_i)`), kısıt ise kaçak
    sayısının Poisson-binom kuyruğudur. `en_iyi_secim`in Pareto tekniği
    aynen geçerlidir, bir boyut fazlasıyla: bir durum, kümülatiflerinin
    **hepsinde** ve kalabalık skorunda başka bir durumdan geride kalıyorsa
    baskılanmıştır — ileride yapılacak her evrişim kümülatiflerin pozitif
    doğrusal birleşimi, skor ise toplamsaldır.

    Kaba kuvvet denendi ve yetmedi: maç başına üç aday, on beş maçta 14
    milyon bileşim demek. Budama ile aynı sonuç birkaç yüz durumda çıkıyor.
    """
    if not 0.0 <= kayip_orani < 1.0:
        raise ValueError("kayip_orani [0, 1) araliginda olmali")
    n = len(secimler)
    if not (len(probs_listesi) == len(oynanma_listesi) == n):
        raise ValueError("probs, oynanma ve secim listeleri ayni uzunlukta olmali")

    taban_p = hedef_olasiligi(probs_listesi, secimler, esik)
    alt_sinir = (1.0 - kayip_orani) * taban_p
    adaylar = [_adaylar(probs_listesi[i], oynanma_listesi[i], secimler[i])
               for i in range(n)]

    # Durum: (kumulatifler, skor, izlek). Skor = Σ log(p_in / kalabalik_in).
    baslangic: tuple[float, ...] = tuple([1.0] * (esik + 1))
    durumlar: list[tuple[tuple[float, ...], float, tuple[int, ...]]] = [
        (baslangic, 0.0, ()),
    ]
    kirpildi = False

    for i in range(n):
        yeni: list[tuple[tuple[float, ...], float, tuple[int, ...]]] = []
        for j, sec in enumerate(adaylar[i]):
            p_in = _kume_olasiligi(probs_listesi[i], sec)
            c_in = _kume_olasiligi(oynanma_listesi[i], sec)
            q = max(0.0, 1.0 - p_in)
            adim = (math.log(max(p_in, _PAY_TABANI))
                    - math.log(max(c_in, _PAY_TABANI)))
            for kumulatif, skor, izlek in durumlar:
                guncel = [kumulatif[0] * (1.0 - q)]
                for m in range(1, esik + 1):
                    guncel.append(kumulatif[m] * (1.0 - q)
                                  + kumulatif[m - 1] * q)
                yeni.append((tuple(guncel), skor + adim, (*izlek, j)))
        durumlar = _pareto_kalabalik(yeni)
        if len(durumlar) >= KALABALIK_PARETO_SINIRI:
            kirpildi = True
            # Kirpma cepheyi skora gore kesiyor ve TABAN yolu (hep 0.
            # aday) skorca en zayif olandir — yani ilk dusen o olur.
            # Oysa kisiti saglayan tek yol o olabilir. Baskilanma
            # feragati kaldirmaz (baskilayan durumun kumulatifleri de
            # tabandan buyuktur), ama kirpma kaldirir; bu yuzden taban
            # yolu kirpma sonrasinda geri konur.
            taban_izlek = (0,) * (i + 1)
            if all(izlek != taban_izlek for _, _, izlek in durumlar):
                durumlar.append(next(d for d in yeni if d[2] == taban_izlek))

    en: tuple[float, float, tuple[int, ...]] | None = None
    for kumulatif, skor, izlek in durumlar:
        if kumulatif[esik] < alt_sinir:
            continue
        if en is None or (skor, kumulatif[esik]) > (en[0], en[1]):
            en = (skor, kumulatif[esik], izlek)

    # Taban yolu cephede HER ZAMAN durur (yukaridaki geri koyma) ve kisiti
    # tanim geregi saglar, dolayisiyla `en` None olamaz. Yine de savunmaci
    # davranilir: ayar hicbir kosulda bir sey BOZAMAZ.
    plan = ([list(s) for s in secimler] if en is None
            else [list(adaylar[i][en[2][i]]) for i in range(n)])
    # `p_hedef` DP'nin taşıdığı kümülatiften DEĞİL, plandan yeniden
    # hesaplanır. İki yol matematiksel olarak aynı sayıyı verir ama
    # kayan noktada son hanelerde ayrışır; raporlanan sayı ile
    # `hedef_olasiligi`in söylediği sayı ayrışırsa aynı kupon iki yerde
    # iki değer gösterirdi.
    p_hedef = hedef_olasiligi(probs_listesi, plan, esik)

    kume_ici = _carpim(probs_listesi, plan)
    kalabalik_ici = _carpim(oynanma_listesi, plan)
    taban_kume = _carpim(probs_listesi, secimler)
    taban_kalabalik = _carpim(oynanma_listesi, secimler)

    degisimler = [
        {"no": i + 1,
         "taban": "".join(secimler[i]), "yeni": "".join(plan[i]),
         "prob_taban": _kume_olasiligi(probs_listesi[i], secimler[i]),
         "prob_yeni": _kume_olasiligi(probs_listesi[i], plan[i]),
         "oynanma_taban": _kume_olasiligi(oynanma_listesi[i], secimler[i]),
         "oynanma_yeni": _kume_olasiligi(oynanma_listesi[i], plan[i])}
        for i in range(n) if plan[i] != list(secimler[i])
    ]

    return KalabalikAyar(
        secimler=plan,
        p_hedef=p_hedef,
        taban_p_hedef=taban_p,
        kume_ici=kume_ici,
        kalabalik_ici=kalabalik_ici,
        oran=(kume_ici / kalabalik_ici) if kalabalik_ici > 0 else 0.0,
        taban_oran=((taban_kume / taban_kalabalik)
                    if taban_kalabalik > 0 else 0.0),
        degisimler=degisimler,
        kirpildi=kirpildi,
    )


def _pareto_kalabalik(
    adaylar: list[tuple[tuple[float, ...], float, tuple[int, ...]]],
    sinir: int = KALABALIK_PARETO_SINIRI,
) -> list[tuple[tuple[float, ...], float, tuple[int, ...]]]:
    """`_pareto`nun bir boyut fazlası: kümülatifler **ve** kalabalık skoru.

    Sıralama skoru en öne alır; böylece sınıra dayanıldığında düşenler
    amaç bakımından en zayıf olanlardır.
    """
    adaylar.sort(key=lambda t: (-t[1], tuple(-x for x in reversed(t[0]))))
    tutulan: list[tuple[tuple[float, ...], float, tuple[int, ...]]] = []
    for kumulatif, skor, izlek in adaylar:
        if any(o_skor >= skor and all(o >= y for o, y in zip(onceki, kumulatif))
               for onceki, o_skor, _ in tutulan):
            continue
        tutulan.append((kumulatif, skor, izlek))
        if len(tutulan) >= sinir:
            break
    return tutulan


# ─── karşılaştırma ────────────────────────────────────────────────────────

def kiyas(last: int | None = None,
          esik: int = VARSAYILAN_KACAK_ESIGI) -> dict[str, Any]:
    """Eşik kuralı ↔ hedefe göre seçim, geçen sezonun tamamında.

    **Aşırı uyum yok ve bunu söylemek önemli.** Optimizasyon sonucu GÖRMEZ;
    piyasanın kendi olasılığına göre ex-ante bir hedefi enbüyükler. Yani
    burada eşik taramasının (`backtest.esik_taramasi`) taşıdığı risk yoktur.
    Yine de model-içi bir iyileşmenin gerçeğe yansıyıp yansımadığı ayrı bir
    sorudur; bu yüzden gerçekleşen en iyi kolon da ölçülür.
    """
    from .backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU, hafta_girdileri, secim_uret

    def en_iyi_kolon(secimler: list[list[str]], gercek: str) -> int:
        """Düzde en iyi kolon **sayılmaz, hesaplanır**: `15 − kaçak`.

        Seçim kümesinin tamamı oynandığı için, küme içinde kalan her maçı
        tutturan bir kolon her zaman vardır; kaçan maçlar ise her kolonda
        yanlıştır. Kaplama döneminde burada `solve_fix16` koşup 864 kolonu
        tek tek gezmek gerekiyordu, çünkü orada en iyi kolon bir **alt
        sınırdı** ve gerçek değeri ancak sayarak bulunuyordu.
        """
        return sum(1 for i, s in enumerate(secimler) if gercek[i] in s)

    haftalar = []
    for w in hafta_girdileri(last):
        if not w["usable"]:
            continue
        eski = [secim_uret(p or {}, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
                for p in w["probs"]]
        a = sum(1 for s in eski if len(s) == 2)
        b = sum(1 for s in eski if len(s) == 3)
        butce = bedel_hesapla(a, b)
        yeni = en_iyi_secim(list(w["probs"]), butce, esik)
        if yeni is None:
            continue
        haftalar.append({
            "week": w["week"],
            "esik": {
                "picks": ["".join(s) for s in eski],
                "bedel": butce,
                "p_hedef": hedef_olasiligi(list(w["probs"]), eski, esik),
                "en_iyi_kolon": en_iyi_kolon(eski, w["results"]),
            },
            "hedef": {
                "picks": yeni.picks,
                "bedel": yeni.bedel,
                "p_hedef": yeni.p_hedef,
                "en_iyi_kolon": en_iyi_kolon(yeni.secimler, w["results"]),
            },
        })

    def ozet(ad: str) -> dict[str, Any]:
        n = len(haftalar)
        kolonlar = [h[ad]["en_iyi_kolon"] for h in haftalar]
        return {
            "hafta": n,
            "bedel_ort": sum(h[ad]["bedel"] for h in haftalar) / n if n else None,
            "p_hedef_ort": sum(h[ad]["p_hedef"] for h in haftalar) / n if n else None,
            "en_iyi_kolon_ort": sum(kolonlar) / n if n else None,
            "hit14": sum(1 for k in kolonlar if k >= 14),
            "hit13": sum(1 for k in kolonlar if k >= 13),
            "hit12": sum(1 for k in kolonlar if k >= 12),
        }

    return {
        "esik_kacak": esik,
        "hedef": f"P(kacak <= {esik}) = P(en iyi kolon >= {14 - esik})",
        "haftalar": haftalar,
        "ozet": {"esik": ozet("esik"), "hedef": ozet("hedef")},
        "uyari": (
            "Optimizasyon SONUCU gormez; ex-ante bir hedefi enbuyukler, yani "
            "esik taramasinin asiri uyum riskini tasimaz. 14+ sayilari TEK "
            "OLAYDIR ve sonuc olarak okunmamalidir; saglam olan sayi bedeldir."
        ),
    }


def _yaz(s: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print(f"HEDEF: {s['hedef']}")
    o = s["ozet"]
    print(f"\n{'kural':<10}{'hafta':>7}{'kolon/hafta':>13}{'P(hedef)':>11}"
          f"{'en iyi kolon':>14}{'>=14':>6}{'>=13':>6}{'>=12':>6}")
    for ad, etiket in (("esik", "eşik"), ("hedef", "hedefe göre")):
        r = o[ad]
        print(f"{etiket:<10}{r['hafta']:>7}{r['bedel_ort']:>13.0f}"
              f"{100 * r['p_hedef_ort']:>10.2f}%{r['en_iyi_kolon_ort']:>14.2f}"
              f"{r['hit14']:>6}{r['hit13']:>6}{r['hit12']:>6}")
    e, h = o["esik"], o["hedef"]
    print(f"\nFark: P(hedef) {100 * (h['p_hedef_ort'] - e['p_hedef_ort']):+.2f} puan · "
          f"kolon {100 * (h['bedel_ort'] / e['bedel_ort'] - 1):+.0f}%")
    print(f"\n{s['uyari']}")


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--last", type=int, default=None)
    ap.add_argument("--esik", type=int, default=VARSAYILAN_KACAK_ESIGI,
                    help="kac kacaga kadar hedefe ulasilmis sayilir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    s = kiyas(a.last, a.esik)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    else:
        _yaz(s)


if __name__ == "__main__":  # pragma: no cover
    main()


# ─── TL cinsinden seçim ───────────────────────────────────────────────────

#: Düzde bir kademeyi tutturmak için gereken en çok kaçak: `en iyi kolon =
#: 15 − k` olduğuna göre `k ≤ 15 − kademe`. Ürünün hedef kademesi 12'dir.
HEDEF_KADEME = 12


def kacak_esigi(kademe: int = HEDEF_KADEME) -> int:
    """`kademe`yi tutturmak için izin verilen en çok kaçak — düzde `15 − kademe`.

    Kaplama döneminde bu hesap `sistem.kacak_esigi(garanti, kademe)`ydi ve
    üç garanti seviyesi tanıyordu (14-garantide `k ≤ 2`, 13'te `k ≤ 1`,
    12'de `k ≤ 0`). Düzde garanti seviyesi diye bir seçim yoktur: seçim
    kümesinin tamamı oynandığı için en iyi kolon her zaman `15 − k`'dir.
    """
    return 15 - kademe


def sistem_secimi(probs_listesi: list[dict[str, float]],
                  butce_tl: float,
                  garanti: int | None = None,
                  kademe: int | None = None,
                  yol: str | None = None) -> Secim | None:
    """`en_iyi_secim`in **TL** cinsinden hâli — oynanan ürünün kendisi.

    Tek işi birim çevirmek: düzde fiyat `kolon × getiri.KOLON_BEDELI`
    (ölçülen ₺10) olduğu için TL bütçesi doğrudan kolon tavanına dönüşür ve
    karar `en_iyi_secim`e devredilir.

    **Bu fonksiyon eskiden 120 satırdı** ve satıcının indirgenmiş sistem
    fiyat tablosunu (`sistem.py`, 84 şekil × üç garanti seviyesi) kendi
    Pareto DP'siyle tarıyordu. Kaplama söküldüğünde o tablo anlamını
    yitirdi: indirgenmiş sistem satın almıyoruz, seçim kümesinin tamamını
    oynuyoruz. Geriye kalan tek gerçek fark birimdi.

    ``garanti``
        Düzde garanti seviyesi diye bir seçim yok — en iyi kolon her zaman
        `15 − k`. Parametre yalnızca çağıranların imzası bozulmasın diye
        duruyor ve **14 dışında bir değer verilirse hata atar**; sessizce
        yok saymak, çağıranın 13-garanti istediğini sanmasına yol açardı.

    ``kademe``
        Hedef ikramiye kademesi (varsayılan 12). Eşiği `kacak_esigi` verir.

    ``yol``
        Fiyat tablosunun yolu. Tablo kalktı; **verilirse hata atar.**
    """
    from .getiri import KOLON_BEDELI

    if garanti is not None and garanti != 15:
        raise ValueError(
            f"Duz sistemde garanti seviyesi secilmez (en iyi kolon = 15 - k); "
            f"garanti={garanti} verildi. Hedef kademeyi `kademe` ile ver.")
    if yol is not None:
        raise ValueError(
            "Sistem fiyat tablosu sokuldu (docs/DUZ_SISTEME_GECIS.md); "
            "`yol` artik bir sey ifade etmiyor.")
    if butce_tl <= 0:
        raise ValueError("Butce pozitif olmali.")
    if not probs_listesi:
        return None

    esik = kacak_esigi(HEDEF_KADEME if kademe is None else kademe)
    if esik < 0:
        raise ValueError(f"{kademe}. kademe 15 macta tutturulamaz.")
    butce_kolon = int(butce_tl // KOLON_BEDELI)
    if butce_kolon < 1:
        return None
    return en_iyi_secim(probs_listesi, butce_kolon, esik)


# ─── kalabalığa göre E[TL] seçimi — kupon KAPANMADAN ─────────────────────

#: Yerel aramanın en çok kaç tur döneceği. Ölçümde üçüncü turda hiçbir
#: hafta değişmedi; sınır güvenlik supabı.
GETIRI_TUR_SINIRI = 3


#: `getiri_secim`in `P(k ≤ eşik)`'ten vazgeçebileceği EN ÇOK oran.
#:
#: **Bu kısıt bir kez kaldırıldı ve ölçüm onu geri getirdi.** Kısıtsız
#: `E[TL]` enbüyüklemesi 2026/27 2. haftada `E[TL]`'yi 3,01 kat büyütürken
#: `P(k≤1)`'i **0,2194 → 0,0073**'e (−%96,7) düşürdü; gerçekleşen sonuçta
#: kaçak 1'den 3'e çıktı ve **1.439 TL'lik ödül sıfıra indi**.
#:
#: Sebep yapısal: `pay_beklentisi` çok küçük `q`'da `1/(N·q)` gibi patlıyor,
#: dolayısıyla kısıtsız beklenen değer, neredeyse hiç gerçekleşmeyen ama
#: gerçekleşirse çok büyük olan bir dalı seçiyor. Ağır kuyruklu bir ödemede
#: beklenen değeri tek başına enbüyüklemek, iyi olmakla aynı şey değildir.
#:
#: Varsayılan temkinli: `P` tabanın **%95'inin altına inemez**. Bu bir
#: ölçüm değil **harcama kararıdır** ve öyle etiketlenir — optimalini
#: söyleyecek `n` yok (elde üç sonuçlanmış hafta var).
GETIRI_KAYIP_TAVANI = 0.05


def getiri_secim(probs_listesi: list[dict[str, float]],
                 oynanma_listesi: list[dict[str, float]],
                 butce_tl: float,
                 garanti: int | None = None,
                 rakip_kolon: int | None = None,
                 kademe_havuzu: dict[int, float] | None = None,
                 kayip_tavani: float = GETIRI_KAYIP_TAVANI,
                 yol: str | None = None) -> Secim | None:
    """`E[TL]`'yi enbüyükleyen işaret planı — **kayıtlı oynanma paylarıyla.**

    ─── Niçin `kalabalik_ayari` yetmiyor ────────────────────────────────

    `kalabalik_ayari` `küme-içi / kalabalık-içi` **oranını** enbüyüklüyor ve
    hedefi bir bütçeyle koruyor. O amaç, ölçülen monoton kalabalık modeliyle
    (`kalabalik.OLCULEN`) hiçbir maçı değiştirmiyor — kayıp bütçesi 0,70'e
    kadar tarandı, `VARSAYILAN_KAYIP_ORANI` künyesinde. Sebebi yapısal:
    `o ∝ p^λ` sembol sıralamasını koruyor.

    Kayıtlı oynanma payları **monoton değil**: 60 maçın 21'inde kalabalığın
    sıralaması piyasanınkinden farklı. Kenar oradadır ve onu görmek için
    amacın oran değil doğrudan `E[TL]` olması gerekir.

    ─── Şekil SABİT, yalnızca semboller değişir ─────────────────────────

    İşaret sayıları kuponun bedelini belirler; sabit tutulunca arama
    **bedava**dır: aynı kolon, aynı satır, aynı bütçe. `kalabalik_ayari`nın
    gerekçesi aynen geçerli — bütçeyi de oynatmak iki ayrı kararı tek adımda
    karıştırırdı.

    ─── Kademe havuzu KARAR ANINDA biliniyor ────────────────────────────

    `E[TL]`'nin argmax'ı havuzun **ölçeğine** değil kademeler arası
    **oranına** bağlıdır (bütün kademeleri aynı katsayıyla çarpmak `E[TL]`'yi
    aynı katsayıyla çarpar). O oran `havuz.BOLUSUM`'dur ve 222 haftada
    ölçülmüş bir kuraldır — yani kupon kapanmadan **bilinir**. Ölçüldü:
    gerçek ikramiye tablosuyla ve `BOLUSUM` oranlarıyla optimize edilen
    kupon üç haftanın üçünde de **birebir aynı** çıktı.

    `None` döner ancak bütçeye şekil sığmıyorsa.
    """
    from .getiri import beklenen_tl
    from .havuz import BOLUSUM

    # Duzde en iyi kolon her zaman 15 - k; "garanti seviyesi" secimi yok.
    g = 15 if garanti is None else garanti
    taban = sistem_secimi(probs_listesi, butce_tl, garanti=g, yol=yol)
    if taban is None:
        return None
    if len(oynanma_listesi) != len(probs_listesi):
        raise ValueError("oynanma ve olasilik listeleri ayni uzunlukta olmali")

    # Olcek keyfi: yalnizca ORAN onemli (docstring).
    havuz = kademe_havuzu or {k: BOLUSUM[k] * 1e7
                              for k in range(HEDEF_KADEME, g + 1)
                              if k in BOLUSUM}
    n_rakip = rakip_kolon if rakip_kolon is not None else _RAKIP_KOLON

    if not 0.0 <= kayip_tavani < 1.0:
        raise ValueError("kayip_tavani [0, 1) araliginda olmali")
    esik = kacak_esigi(HEDEF_KADEME)
    p_alt = hedef_olasiligi(probs_listesi, taban.secimler,
                            esik) * (1.0 - kayip_tavani)

    secimler = [list(x) for x in taban.secimler]
    en_iyi = beklenen_tl(probs_listesi, oynanma_listesi, secimler, {},
                         havuz, g, n_rakip)
    for _ in range(GETIRI_TUR_SINIRI):
        gelisti = False
        for i, mevcut in enumerate(secimler):
            k = len(mevcut)
            for aday in _kombinasyonlar(k):
                if set(aday) == set(mevcut):
                    continue
                yedek = secimler[i]
                secimler[i] = sirala_semboller(list(aday))
                # KISIT ONCE: hedefi tavanin otesinde harcayan hicbir
                # degisim, E[TL] ne kadar buyurse buyusun kabul edilmez.
                if hedef_olasiligi(probs_listesi, secimler, esik) < p_alt:
                    secimler[i] = yedek
                    continue
                v = beklenen_tl(probs_listesi, oynanma_listesi, secimler, {},
                                havuz, g, n_rakip)
                if v > en_iyi * (1.0 + 1e-9):
                    en_iyi = v
                    gelisti = True
                else:
                    secimler[i] = yedek
        if not gelisti:
            break

    return Secim(
        secimler=secimler,
        bedel=taban.bedel,
        p_hedef=hedef_olasiligi(probs_listesi, secimler, esik),
        banko=sum(1 for x in secimler if len(x) == 1),
        cift=sum(1 for x in secimler if len(x) == 2),
        uclu=sum(1 for x in secimler if len(x) == 3),
    )


def _kombinasyonlar(k: int) -> list[tuple[str, ...]]:
    """`k` boyutlu bütün sembol kümeleri — şekli bozmadan aday üretir."""
    from itertools import combinations

    return list(combinations(SEMBOLLER, k))


#: `getiri_secim`in varsayılan rakip kolon sayısı — `karne.RAKIP_KOLON` ile
#: aynı gerekçe ve aynı sayı; döngüsel import olmasın diye burada da yazılı
#: ve bekçisi `test_rakip_kolon_TEK_sayi`.
_RAKIP_KOLON = 15_000_000
