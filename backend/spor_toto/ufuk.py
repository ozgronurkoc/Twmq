"""Ufuk — haftalık `P(15/15)`'ten **hedefin kendisine**.

Bu deponun her ölçüsü haftalıktır: `coklu.coklu_plan_serisi` bir haftanın
`P(15/15)`'ini enbüyükler, geri test 114 haftayı tek tek puanlar. Ama
sahibinin verdiği hedef haftalık değil: **üç ay içinde 15/15**. İkisi aynı
şey değildir ve aradaki çeviri bu modüldedir.

    P(ufukta en az bir 15/15) = 1 − Π_w (1 − p_w)

─── Niçin ayrı bir modül ─────────────────────────────────────────────────

Çünkü çeviri iki yerde **sessizce yanlış** yapılabiliyordu ve biri
yapılıyordu da:

1. **Ortalamayla hesaplamak.** `coklu_kiyasi.py`nin "13 hafta" sütunu
   `1 − (1 − p̄)¹³` yazıyordu. `log(1 − p)` içbükey olduğu için bu sayı
   gerçek değerin **altında** kalır (Jensen) ve haftalar ne kadar
   ayrışırsa açık o kadar büyür — bu depoda haftalar on altı kat ayrışıyor.
   Ölçüldü (§3.73): 13 haftalık pencerelerde yaklaşıklık gerçek değeri
   **0,6–0,7 puan** düşük yazıyor. Küçük, ama **tek yöne** bakıyor ve
   yönü artık biliniyor — yaklaşıklık iyimser değil, karamsar.
2. **Tek sayı sanmak.** "Üç ayda 15/15 olasılığı" tek bir sayı değil, hangi
   13 haftaya denk gelindiğine bağlı bir **aralıktır**: 729 kuponluk planda
   ölçülen 8 pencerede %69,9 ile %86,7 arası (ortalama %78,8).

─── Haftalar bağımsız mı ─────────────────────────────────────────────────

Evet, ve bu varsayım bu depoda zaten yazılı: haftalar **ayrı maç
kümelerinden** kuruludur (`duyarlilik.py`, §3.70). Hafta *içi* bağımlılık
ölçüldü ve `p_w`nin kendisini şişiriyor (§3.70, %12'ye kadar) — ama o,
`p_w`nin sorunudur, çarpımınkinin değil. Çarpım yalnızca haftalar arası
bağımsızlığa dayanır ve aynı takımlar ancak sezon boyunca tekrar geldiği
için burada kalan bağ, model hatasının ortak bileşenidir: `p_w` sistematik
olarak yüksekse ufuk da sistematik olarak yüksektir. O yüzden aşağıdaki
sayılar **modelin** sayılarıdır ve yanlarında gerçekleşen sütunu olmadan
okunmamalıdır (§3.68'in okuma kuralı burada da geçerli).

─── Zamanlama ekseni: açıldı ve KAPANDI (§3.73) ──────────────────────────

Haftalar arası `P` **on altı kat** ayrışıyor (114 haftada, 729 kuponluk
planda, en zayıf hafta %2,3 ↔ en güçlü %37,2) ve güçlü haftanın **mutlak**
marjinal getirisi zayıfınkinin iki katı. Bu, "parayı iyi haftalara yığ"
fikrini akla getiriyor ve fikir ölçüldü.

`kahin_tahsisi` üst sınırı verir: bütün pencerenin eğrilerini **önceden
bilerek** en iyi dağıtım. Uygulanamaz (haftanın kuponu ancak o hafta
belli olur), o yüzden gerçek bir kural bunun ancak altında kalır. Ölçülen
kazanç 8 pencerede ortalama **×1,031**, en çok ×1,051 — ve kâhin bunun için
haftalık bütçeyi 0 ile 4 kat arasında oynatıyor, yani kural basit de değil.

Sebebi aritmetiktir ve tek cümledir: `1 − Π(1 − p)` **doyar**. 13 haftada
%11'lik atışlarla zaten %78,8'desiniz; kalan başlık %21,2 ve tam öngörülü
tahsis onun ancak yedide birini alıyor. Yığmanın işe yaraması için ya ufuk
çok daha kısa ya da `p` çok daha küçük olmalıydı.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from .coklu import Nokta, _tahsis_kabuklu, _ust_kabuk

#: Ufuk uzunluğu (hafta). 13 ≈ üç ay; sahibinin verdiği süre bu. Sabit
#: burada duruyor çünkü iki betik onu aynı anlamda kullanıyor.
UFUK_HAFTA = 13


def en_az_bir(p_listesi: Sequence[float]) -> float:
    """`P(en az bir hafta 15/15)` — haftalar bağımsız sayılarak.

    Kesin hesap: `1 − Π(1 − p_w)`. Ortalamayla yapılan yaklaşıklık için
    `ortalamayla`; ikisinin farkı ölçüldü — küçük (0,6–0,7 puan) ama **tek
    yöne** bakıyor, yani hata gürültü değil yanlılık (§3.73).

    >>> round(en_az_bir([0.1, 0.2, 0.3]), 6)
    0.496
    """
    kalan = 1.0
    for p in p_listesi:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"Olasilik 0..1 araliginda olmali: {p}")
        kalan *= 1.0 - p
    return 1.0 - kalan


def ortalamayla(p_ort: float, hafta: int) -> float:
    """`1 − (1 − p̄)ⁿ` — **yaklaşıklık**, gerçek değerin altında kalır.

    Gövde silinmiyor çünkü ölçülen bir sayıyı üretiyor: `coklu_kiyasi.py`nin
    "13 hafta" sütunu bu formülle yazıldı ve belgelerde öyle anılıyor.
    Yanlılığın **büyüklüğü** ancak iki gövde yan yana durursa ölçülebilir.

    >>> round(ortalamayla(0.2, 3), 6)
    0.488
    """
    if not 0.0 <= p_ort <= 1.0:
        raise ValueError(f"Olasilik 0..1 araliginda olmali: {p_ort}")
    if hafta < 0:
        raise ValueError("Hafta sayisi negatif olamaz.")
    return 1.0 - (1.0 - p_ort) ** hafta


def pencereler(n: int, boy: int) -> list[tuple[int, int]]:
    """Ardışık, **örtüşmeyen** pencereler; artan kuyruk atılır.

    Örtüşen pencere kullanmak sayıyı iyi gösterirdi (aynı iyi hafta birden
    çok pencerede sayılır) ama pencereler arası bağımsızlığı bozardı ve
    "kaç pencerede gerçekten tuttu" sütunu anlamını yitirirdi.

    İki betik bunu istiyor (`ufuk_kiyasi.py` ve `coklu_kiyasi.py`); iki
    kopya olsaydı biri sessizce eskirdi.

    >>> pencereler(114, 13)[:2], len(pencereler(114, 13))
    ([(0, 13), (13, 26)], 8)
    """
    if boy < 1:
        raise ValueError("Pencere boyu pozitif olmali.")
    return [(i, i + boy) for i in range(0, n - boy + 1, boy)]


def ufuk_ortalamasi(p_haftalik: Sequence[float], boy: int) -> float:
    """Ardışık pencerelerde `P(en az bir)`in **ortalaması**.

    "Üç ayda 15/15 olasılığı" tek bir sayı değil; bu gövde onu tek sayıya
    indirirken hangi indirgemeyi yaptığını açıkça yapar — ayrık pencereler,
    düz ortalama. Pencere sığmazsa (`boy > n`) bütün diziyi tek pencere
    sayar, çünkü alternatif sessizce 0 döndürmek olurdu.
    """
    araliklar = pencereler(len(p_haftalik), boy)
    if not araliklar:
        return en_az_bir(p_haftalik)
    return sum(en_az_bir(p_haftalik[a:b]) for a, b in araliklar) / len(araliklar)


def beklenen_sayi(p_listesi: Sequence[float]) -> float:
    """Ufukta beklenen 15/15 **hafta sayısı** — `Σ p_w`.

    `en_az_bir`den ayrı bir soru: biri "hiç olacak mı", öteki "kaç kez".
    Küçük `p`de ikisi birbirine yakındır ve ayrışmaları doymanın kendisidir.
    """
    return float(sum(p_listesi))


def kahin_tahsisi(egriler: Sequence[Sequence[tuple[int, float]]],
                  toplam: int) -> tuple[float, list[int]] | None:
    """Pencerenin **tam öngörüyle** en iyi bütçe dağıtımı — bir ÜST SINIR.

    `egriler[w]`, `w`. haftanın `(bedel, p)` noktalarıdır ve artan bedelli
    olmalıdır; ilk nokta bütçesiz hâli (genellikle `(0, 0.0)`) taşımalıdır,
    yoksa "bu haftayı hiç oynama" seçeneği aramaya girmez. `toplam`, pencere
    boyunca harcanabilecek toplam kolondur.

    ─── Niçin bu, doğrudan `coklu`nun tahsisi ──────────────────────────────

    Hedef `1 − Π(1 − p_w)`'yi enbüyüklemek, yani `Σ −log(1 − p_w)`'yi. Bu
    **ayrılabilir** bir sırt çantasıdır, tam olarak §3.71'in kupon başına
    bütçe problemi gibi — tek fark, orada ağırlık `q_j`, burada 1. O yüzden
    burada yeni bir çözücü yok: noktalar `−log(1 − p)` değerine çevrilip
    `coklu._ust_kabuk` + `coklu._tahsis_kabuklu`ya veriliyor. İki açgözlü
    kopyası olsaydı biri sessizce eskirdi.

    Dönen değer `(P(en az bir), hafta başına seçilen bedel)`. `None` döner
    ancak bir hafta için hiç nokta verilmemişse.

    ─── Bu sayı UYGULANAMAZ ve öyle okunmalıdır ───────────────────────────

    Bütün pencerenin eğrilerini önceden bilmek gerekir; gerçekte haftanın
    kuponu ancak o hafta belli olur. Yani bu, herhangi bir gerçek kuralın
    **geçemeyeceği** tavandır. Ölçüldü (§3.73): düz dağıtıma göre 8 pencerede
    ortalama ×1,031, en çok ×1,051 — yani zamanlama ekseninin tamamı o kadar.
    """
    kabuklar: list[list[Nokta]] = []
    for egri in egriler:
        if not egri:
            return None
        noktalar: list[Nokta] = [(c, -math.log(max(1e-15, 1.0 - p)), None)
                                 for c, p in egri]
        kabuklar.append(_ust_kabuk(noktalar))
    sonuc = _tahsis_kabuklu([1.0] * len(kabuklar), kabuklar, toplam)
    if sonuc is None:
        return None
    _deger, secilen = sonuc
    bedeller = [int(n[0]) for n in secilen]
    p = [dict(egri)[b] for egri, b in zip(egriler, bedeller)]
    return en_az_bir(p), bedeller
