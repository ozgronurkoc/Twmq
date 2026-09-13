"""Çoklu kupon — tek sistemin çarpım kısıtını kaldırır.

`secim.py` bir hafta için **tek** bir tam sistem kurar: her maça 1/2/3
sembol, kupon bunların Kartezyen çarpımı, bedel `2^a·3^b`. Bu modül aynı
bütçeyi **birden çok kupona** böler ve ölçülen kazanç büyüktür.

─── Neden çarpım bir kısıt ───────────────────────────────────────────────

`N` kolonluk en iyi küme, tanım gereği olasılığa göre en büyük `N` kolondur.
O küme genel olarak bir **kutu değildir**. Çarpım kümesi, kutunun köşelerini
(tüm belirsiz maçların aynı anda ters gitmesi) satın almak zorunda kalırken
kutunun dışında kalan daha olası kolonları (tek bir bankonun dönmesi)
alamaz. Ölçülen bedel, 114 tam haftada, `3⁹ = 19.683` kolonda:

    tek sistem (çarpım)        P(15/15) = %7,489    gerçekleşen 15/114
    serbest (en büyük N kolon) P(15/15) = %10,865   gerçekleşen 22/114

Aynı para, aynı olasılık modeli, **×1,45**. Fark yalnızca kümenin şekli.

─── Neden bu modül, serbest liste değil ──────────────────────────────────

Serbest kümeyi birebir oynamak ~4.300 ayrı kupon ister (ölçüldü: 20 haftada
medyan 4.290 kutu, birleştirme sonrası). Bedel aynıdır ama operasyon ağır.
Bu modül araya giren aileyi kurar ve kazancın çoğu birkaç düzine kuponda
zaten alınır:

    kupon    model P(15/15)    gerçekleşen    13 hafta
        1          %7,489         15/114        %63,7   ← tek sistem
       27          %9,353         20/114        %72,1
       81          %9,862         21/114        %74,1
      729         %10,461         22/114        %76,2
   19.683         %10,865         22/114        %77,6   ← serbest

729 kupon, serbest kümenin kazancının **~%88'ini** alır. Üretici:
`cd backend && python scripts/coklu_kiyasi.py`.

> **YENİDEN ÖLÇÜLDÜ (2026-09-13).** Tablo modülün ilk sürümüyle koşulmuştu;
> sonra kupon sayısı sabit ızgaradan alt sistemin bedeline bağlandı ve eksen
> bileşimleri yığınla üretilir oldu. Yeniden koşuldu ve **birebir aynı**
> çıktı — çünkü bu kıyas `3⁹ = 19.683` kolonda koşuyor ve o bütçede merdiven
> zaten yoktu (`bütçe // kupon_kolon`, ızgaranın verdiği sayıyla aynı).

─── Gerçek bütçede (21.000 kolon = 210.000 TL) ───────────────────────────

Merdivenin farkı yuvarlak olmayan bütçelerde ortaya çıkar. Tek sistem
`2^a·3^b`'ye sıkıştığı için 19.683 kolonda takılı kalır; çoklu kupon
bütçenin neredeyse tamamını kullanır:

    kupon    kolon     model P(15/15)   gerçekleşen   13 hafta
        1   19.683          %7,489        15/114        %63,7   ← tek sistem
       27   19.683          %9,353        20/114        %72,1
       79   19.709          %9,864        21/114        %74,1
      136   20.514         %10,264        21/114        %75,5
      329   20.786         %10,602        20/114        %76,7

**×1,42**, aynı parada. Üretici:
`cd backend && python scripts/coklu_kiyasi.py --butce 21000`.

Gözlenen sütun `n = 114` ile gürültülüdür (329 kuponda 20, 79 kuponda 21);
güvenilen sinyal **model** sütunudur ve o monotondur — bekçisi
`test_kupon_sayisi_buyudukce_P15_DUSMEZ`.

Yapı: `d` maç **eksen** seçilir — en emin olduklarımız — ve kuponlar arasında
tek tek sabitlenir; eksen üzerindeki `3^d` bileşimden en olası `M` tanesi
oynanır. Kalan `15−d` maç her kuponda **aynı alt sistemdir** ve onu
`secim.en_iyi_secim` kendi bütçesiyle (`bütçe // M`) çözer.

`M = 1` tam olarak bugünkü tek sistemdir. Yani bu modül mevcut davranışı
**içerir** ve arama onu bir aday olarak gezer; `M`i büyütmek genelleştirir.

─── Yan fayda: bütçe merdiveni kalkıyor ──────────────────────────────────

Tek sistemde bedel `2^a·3^b` olduğu için bütçe **basamaklıdır**: 19.683 ile
21.000 kolon *aynı* kuponu alır, aradaki 13.170 TL hiçbir şey satın almaz.
Çoklu kuponda bedel `M · 3^(15−d)`'dir ve `M` serbest tamsayıdır, yani her
bütçe kullanılabilir.

─── Sınır ────────────────────────────────────────────────────────────────

Buradaki olasılıklar maçlar arası **bağımsızlık** varsayar; `kuyruk.py`
hafta içi bağımlılığı ölçtü ve korpus üst sınırında kuyruk %5 şişiyor. Bu
her iki şekli de aynı yönde etkiler, oran görece dayanıklıdır — ama
`P(15/15)`'in mutlak değeri bu varsayıma bağlıdır ve öyle okunmalıdır.

─── Mutlak değer sınandı: OKUMA KURALI ───────────────────────────────────

Yukarıdaki tablonun iki sütunu (model ↔ gerçekleşen) ayrışıyor ve bu
ayrışma ölçüldü (`spor_toto.duyarlilik`, §3.68). Havuzlanmış 114 haftada
model **karamsar**: tek sistemde beklenen 8,54 hafta, gerçekleşen 15
(×1,76); 729 kuponda 12,09 ↔ 20 (×1,65). Açığın tamamını, bağımsız ölçülmüş
banko sapması (`p₁` 5,8 puan düşük yazılıyor) kapatıyor.

**Ama tablodaki sayılar yeniden ÖLÇEKLENMEDİ ve ölçeklenmeyecek.** Sezon
kırılımı açığın 2023/24'ten geldiğini ve 2025/26'da **kapandığını** gösterdi
(729 kuponda ×1,00); düzeltilmiş model o sezonda fazla iyimser olurdu.
Havuzlanmış oranla bütün sayıları büyütmek 2023/24'ü geçmişe uydurmak olurdu.

Okuma kuralı şu: bu sütun **havuzlanmış kesitte karamsar tarafta kalmış
olabilir**, ve kararı bu belirsizlik taşımıyor — aynı ölçüm sapmalı cetvelle
kurulan planın taban cetvelde hiç iyileşmediğini, `tavan = 1`'de ise
kuponun 114 haftanın 114'ünde **birebir aynı** kaldığını buldu.

─── Alt kademe: beklenti yalanlandı ──────────────────────────────────────

Bu modül **yalnızca 15/15'i** enbüyükler ve burada önce şu yazıyordu: *"alt
kademeler paranın çoğunu taşır ve çoklu kupon onları tek sistem kadar
tutturmaz."* Bir varsayımdı; ölçüldü ve **yanlış çıktı**. 114 haftada 12+
tutturan kolon toplamı:

    tek sistem   18.628
    729 kupon    26.274        **+%41**

Sebebi geriye dönük açık: olasılığa göre en büyük `N` kolon kümesi yalnızca
15'e değil 12–13'e de daha yakın durur; çarpımın satın almak zorunda kaldığı
köşeler hiçbir kademeye yaramıyordu. Yani burada bir ödünleşme yok — cümle
silinmedi, **düzeltildi** (kayıt yeniden yazılmaz, `.claude/olcum_kutugu.json`).
"""
from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from .core import SEMBOLLER, sirala_semboller

if TYPE_CHECKING:  # `secim` çalışma zamanında TEMBEL çekiliyor (döngü),
    from .secim import Secim  # tip burada gerekiyor ve orada gerekmiyor.

#: Kupondaki maç sayısı.
MAC_SAYISI = 15

#: Varsayılan kupon tavanı. Ölçülen eğride kazancın büyük kısmı ilk birkaç
#: düzine kuponda alınıyor; tavan bir **operasyon** kararıdır, matematiksel
#: bir sınır değil. `None` verilirse arama `ARANAN_KUPON`un tamamını gezer.
VARSAYILAN_KUPON_TAVANI = 81


class Kupon(NamedTuple):
    """Tek bir oynanabilir kupon: her maç için işaretlenen semboller."""

    secimler: list[list[str]]
    kolon: int

    @property
    def picks(self) -> list[str]:
        return ["".join(sirala_semboller(s)) for s in self.secimler]


class CokluPlan(NamedTuple):
    """Bir haftanın çoklu kupon planı ve ölçülmüş hedefi."""

    kuponlar: list[Kupon]
    eksen: list[int]
    kolon: int
    p_onbes: float

    @property
    def kupon_sayisi(self) -> int:
        return len(self.kuponlar)


def _matris(probs_listesi: list[dict[str, float]]) -> np.ndarray:
    """Olasılıkları satır başına büyükten küçüğe sıralı matrise çevirir."""
    p = np.array([[d.get(s, 0.0) for s in SEMBOLLER] for d in probs_listesi],
                 dtype=float)
    toplam = p.sum(axis=1, keepdims=True)
    if np.any(toplam <= 0):
        raise ValueError("Bir macin olasilik toplami sifir.")
    return p / toplam


def eksen_sec(probs_listesi: list[dict[str, float]], d: int) -> list[int]:
    """Eksen maçları: en emin `d` maç (favori olasılığı en büyük).

    Eksen **kısıtlanan** taraftır — o maçlarda bütün bileşimleri değil
    yalnızca en olası `M` tanesini oynarız. Kısıtlamayı en emin olduğumuz
    yerde yapmak doğrudur: emin olmadığımız maç üçlü kalır ve hiç kaçmaz.
    """
    if not 0 <= d <= MAC_SAYISI:
        raise ValueError(f"Eksen sayisi 0..{MAC_SAYISI} araliginda olmali.")
    P = _matris(probs_listesi)
    # Favorinin olasılığı — `P[:, 0]` DEĞİL. `_matris` ham sembol düzeninde
    # (`1/0/2`) döner, yani ilk sütun ev sahibidir, favori değil.
    return sorted(np.argsort(-P.max(axis=1))[:d].tolist())


#: Aranan kupon sayıları. Her `M` için kupon başına bütçe `bütçe // M`
#: olur ve alt sistem o bütçeyle **ayrıca** çözülür. Izgara üçün kuvvetleri
#: etrafındadır çünkü eksen bileşim sayısı `3^d`'dir; aradaki değerler
#: kupon başına bütçeyi kırpmaktan başka bir şey yapmaz.
ARANAN_KUPON = (1, 3, 9, 27, 81, 243, 729, 2187)


def _eksen_bilesimleri(P: np.ndarray, eksen: list[int], M: int
                       ) -> tuple[list[tuple[int, ...]], float]:
    """Eksen üzerindeki en olası `M` bileşim: (sembol indeksleri, toplam).

    ─── Neden yığın, neden `3^d` dizi değil ──────────────────────────────

    İlk sürüm bütün bileşimleri kurup sıralıyordu (`np.multiply.outer`
    zinciri + `argpartition`). Doğruydu ama `d = 15`'te o dizi **14.348.907**
    eleman ve arama onu her `(M, d)` adayı için yeniden kuruyordu: tek
    haftanın planı 3,77 sn sürüyordu, 114 haftalık kıyas saatler.

    Oysa yalnızca en üstteki `M` bileşim gerekiyor. Her maçın sembolleri
    olasılığa göre sıralandığında bileşimler bir **kafes** kurar: bir
    bileşimden daha olasısına ancak bir koordinatın rütbesini *azaltarak*
    gidilir. O hâlde en olası bileşimden (hepsi favori) başlayıp komşuları
    bir yığında gezmek, `M` bileşimi sırayla ve tamamını kurmadan verir.
    Maliyet `O(M · d · log(M · d))`.
    """
    if not eksen:
        return [()], 1.0

    sirali = [np.argsort(-P[i]) for i in eksen]          # rütbe → sembol
    olas = [P[i][sirali[k]] for k, i in enumerate(eksen)]
    d = len(eksen)
    M = min(M, 3 ** d)

    baslangic = (0,) * d
    p0 = float(np.prod([olas[k][0] for k in range(d)]))
    # `-p` ile en büyük olasılık yığının tepesinde
    yigin = [(-p0, baslangic)]
    gorulen = {baslangic}
    cikti: list[tuple[int, ...]] = []
    toplam = 0.0

    while yigin and len(cikti) < M:
        eksi_p, rutbe = heapq.heappop(yigin)
        cikti.append(tuple(int(sirali[k][rutbe[k]]) for k in range(d)))
        toplam += -eksi_p
        for k in range(d):
            if rutbe[k] + 1 < 3:
                komsu = (*rutbe[:k], rutbe[k] + 1, *rutbe[k + 1:])
                if komsu in gorulen:
                    continue
                gorulen.add(komsu)
                p = float(np.prod([olas[j][komsu[j]] for j in range(d)]))
                heapq.heappush(yigin, (-p, komsu))

    return cikti, toplam


def coklu_plan(probs_listesi: list[dict[str, float]],
               butce: int,
               kupon_tavani: int | None = None) -> CokluPlan:
    """Bütçe içinde `P(15/15)`'i enbüyükleyen çoklu kupon planı.

    `butce` kolon cinsindendir ve zorunludur — `secim.en_iyi_secim` ile aynı
    sebeple: tavansız aramanın cevabı dejenere (`3¹⁵` kolon, `P = 1`).

    Plan iki parçadır:

    * **eksen** — `d` maç, kuponlar arasında tek tek sabitlenir. Eksen
      üzerindeki `3^d` bileşimden en olası `M` tanesi oynanır, her biri bir
      kupon.
    * **alt sistem** — kalan `15−d` maç, her kuponda **aynı**, ve bütçesi
      `bütçe // M` olan bir tam sistem. Onu `secim.en_iyi_secim` çözer.

    Maçlar bağımsız sayıldığı için ikisi çarpılır:

        P(15/15) = P(eksen bileşimi oynananlar içinde) · P(alt sistem kaçmaz)

    ─── Alt sistemi neden `en_iyi_secim` çözüyor ────────────────────────

    İlk sürüm eksen dışını **üçlüye zorluyordu** ve bu ölçülebilir değer
    bırakıyordu: `test_tek_kupon_TEK_SISTEMIN_kendisi` tek kupon hâlinde iki
    planı karşılaştırdı ve `en_iyi_secim` daha iyisini buldu — `P = 0,1240`'a
    karşı `0,1142`, üstelik 17.496 kolona karşı 19.683. Sebebi: üçüncü
    sembolü çok küçük olan bir maçta **çifte**, üçlünün kapsamasının
    neredeyse tamamını üçte iki değil yarı bedele alır. Zorlama kalktı.
    """
    seri = coklu_plan_serisi(probs_listesi, butce, (kupon_tavani,)
                             if kupon_tavani is not None else None)
    return seri[max(seri)]


def coklu_plan_serisi(probs_listesi: list[dict[str, float]],
                      butce: int,
                      tavanlar: tuple[int, ...] | None = None
                      ) -> dict[int, CokluPlan]:
    """Her kupon tavanı için en iyi plan — **tek aramada**.

    `coklu_plan`ı tavan tavan çağırmak aramayı her seferinde baştan yapardı;
    114 haftalık kıyasta bu yedi kat israftı. Arama zaten `M` büyüdükçe
    ilerlediği için, bir tavanın cevabı o tavana kadarki adayların en
    iyisidir — yani tek geçişte hepsi toplanır.

    Dönen sözlüğün anahtarları verilen tavanlardır ve değerler **birikimli
    en iyi**dir, yani tavan büyüdükçe `p_onbes` düşemez.
    """
    if butce is None or butce <= 0:
        raise ValueError("Butce pozitif bir kolon sayisi olmali.")
    if len(probs_listesi) != MAC_SAYISI:
        raise ValueError(f"{MAC_SAYISI} macin olasiligi gerekir.")

    from .secim import en_iyi_secim

    istenen = sorted(tavanlar) if tavanlar else sorted(ARANAN_KUPON)
    P = _matris(probs_listesi)
    emin_sira = np.argsort(-P.max(axis=1)).tolist()   # en eminden başlayarak

    # ─── 1. yapılandırmalar ────────────────────────────────────────────
    # Bir yapılandırma = (eksen kümesi, ortak alt sistem). Kaç kupon
    # alınacağı buraya GİRMEZ; o tavana göre sonra kesilir. Önce kupon
    # sayısı burada sabitleniyordu ve seri bozuluyordu: `tavan_ust`e göre
    # kırpılan bir aday, daha küçük bir tavanın seçiminden tamamen
    # düşüyordu (`test_seri_TEK_TEK_cagirmakla_ayni` tuttu).
    #: (tam_kupon, p_alt, eksen, kalanlar, alt, kolon_kupon)
    yapilar: list[tuple[int, float, list[int], list[int],
                        Secim | None, int]] = []
    gorulen: set[tuple[int, int]] = set()

    for M in ARANAN_KUPON:
        kupon_butce = butce // M
        if kupon_butce < 1:
            break
        for d in range(MAC_SAYISI + 1):
            eksen = sorted(emin_sira[:d])
            kalanlar = [i for i in range(MAC_SAYISI) if i not in set(eksen)]
            alt = en_iyi_secim([probs_listesi[i] for i in kalanlar],
                               kupon_butce, esik=0) if kalanlar else None
            if kalanlar and alt is None:
                continue
            kolon_kupon = 1 if alt is None else alt.bedel

            # ─── kupon sayısı ızgaradan DEĞİL, bedelden türetilir ───────
            # Önce `M`in kendisi kullanılıyordu ve bütçe boşa gidiyordu:
            # 21.000 kolonluk bütçede `M = 81`, alt sistem 243 kolon çıkıyor
            # ve 81 × 243 = 19.683 — geriye 1.317 kolon (13.170 TL) hiçbir
            # şey satın almadan kalıyordu. Aynı boydaki kupondan bütçenin
            # aldığı KADAR alınır; fazladan her kupon bir eksen bileşimi
            # daha açar ve hedefi yalnızca büyütür.
            tam = min(butce // kolon_kupon, 3 ** d)
            if tam < 1 or (d, kolon_kupon) in gorulen:
                continue
            gorulen.add((d, kolon_kupon))

            p_alt = 1.0 if alt is None else float(np.prod(
                [sum(probs_listesi[i][s] for s in sec)
                 for i, sec in zip(kalanlar, alt.secimler)]))
            yapilar.append((tam, p_alt, eksen, kalanlar, alt, kolon_kupon))

    if not yapilar:                           # bütçe 1 kolona bile yetmiyor
        raise ValueError(f"Butce hicbir plani karsilamiyor: {butce}")

    # ─── 2. her tavan için en iyi yapılandırma ─────────────────────────
    seri: dict[int, CokluPlan] = {}
    for tavan in istenen:
        en: tuple[float, int, list[int], list[int],
                  Secim | None, int] | None = None
        for tam, p_alt, eksen, kalanlar, alt, kolon_kupon in yapilar:
            sayi = min(tam, tavan)
            if sayi < 1:
                continue
            _, p_eksen = _eksen_bilesimleri(P, eksen, sayi)
            p = p_eksen * p_alt
            # eşitlikte AZ kupon kazanır: aynı hedefe daha az operasyonla
            if en is None or (p, -sayi) > (en[0], -en[1]):
                en = (p, sayi, eksen, kalanlar, alt, kolon_kupon)
        if en is None:
            continue
        p, sayi, eksen, kalanlar, alt, kolon_kupon = en
        bilesimler, _ = _eksen_bilesimleri(P, eksen, sayi)
        seri[tavan] = _plan((p, _kuponlari_kur(bilesimler, eksen, kalanlar,
                                               alt, kolon_kupon), eksen))

    if not seri:
        raise ValueError(f"Butce hicbir plani karsilamiyor: {butce}")
    return seri


def _plan(en: tuple[float, list[Kupon], list[int]]) -> CokluPlan:
    p, kuponlar, eksen = en
    return CokluPlan(kuponlar=kuponlar, eksen=eksen,
                     kolon=sum(k.kolon for k in kuponlar), p_onbes=p)


def _kuponlari_kur(bilesimler: list[tuple[int, ...]], eksen: list[int],
                   kalanlar: list[int], alt: Secim | None,
                   kolon_kupon: int) -> list[Kupon]:
    """Eksen bileşimleri + ortak alt sistem → oynanabilir kuponlar.

    `bilesimler`in her elemanı, `eksen` sırasına karşılık gelen **sembol
    indeksleri**dir (rütbe değil — `_eksen_bilesimleri` çevirisini kendi
    içinde yapar). Rütbe ile sembolü karıştırmak bu modülün ilk hatasıydı
    ve `p_onbes` bekçisi onu tuttu.
    """
    alt_secim = {} if alt is None else dict(zip(kalanlar, alt.secimler))
    kuponlar = []
    for bilesim in bilesimler:
        yerlesim = dict(zip(eksen, bilesim))
        secimler = [[SEMBOLLER[yerlesim[i]]] if i in yerlesim
                    else list(alt_secim[i])
                    for i in range(MAC_SAYISI)]
        kuponlar.append(Kupon(secimler=secimler, kolon=kolon_kupon))
    return kuponlar


def p_onbes(probs_listesi: list[dict[str, float]],
            kuponlar: list[Kupon]) -> float:
    """Verilen kuponlar için `P(15/15)` — plandan bağımsız, yeniden ölçüm.

    `coklu_plan` bu sayıyı eksen vektöründen taşır; bu gövde onu **kuponun
    kendisinden** yeniden hesaplar. İkisi ayrışırsa aynı kupon iki yerde iki
    farklı hedef gösterir, ve bekçisi bunu tutar.

    Kuponlar ayrık olduğu için toplam, kupon olasılıklarının toplamıdır.
    """
    P = _matris(probs_listesi)
    indeks = {s: j for j, s in enumerate(SEMBOLLER)}
    toplam = 0.0
    for k in kuponlar:
        p = 1.0
        for i, sec in enumerate(k.secimler):
            p *= sum(P[i][indeks[s]] for s in sec)
        toplam += p
    # `float(...)` SÜS DEĞİL: `P` numpy olduğu için `toplam` `np.float64`
    # çıkıyordu ve imza `-> float` diyordu. Tip yalanı sessiz kalmadı —
    # `json.dumps`, bu değerden türeyen bir karşılaştırmanın `np.bool_`
    # sonucunda `TypeError` attı (çoklu kupon kaydının değerlendirmesi).
    # `coklu_plan`ın taşıdığı `p_onbes` zaten `float`tu, yani iki yol
    # aynı sayıyı iki ayrı TIPTE veriyordu.
    return float(toplam)


def kademe_dagilimi(probs_listesi: list[dict[str, float]],
                    kuponlar: list[Kupon],
                    gercek: list[str]) -> dict[int, int]:
    """Gerçek sonuç verildiğinde her kademeyi tutturan **kolon sayısı**.

    `duz.kademe_sayimlari` tek sistem içindir; çoklu kuponda her kupon kendi
    sayımını üretir ve kuponlar ayrık olduğu için sayımlar toplanır.
    """
    from .duz import kademe_sayimlari

    top: dict[int, int] = {}
    for k in kuponlar:
        kacak = [i for i, sec in enumerate(k.secimler) if gercek[i] not in sec]
        s = [len(sec) for sec in k.secimler]
        for kademe, adet in kademe_sayimlari(s, kacak).items():
            top[kademe] = top.get(kademe, 0) + adet
    return top


def kupon_sayisi_egrisi(probs_listesi: list[dict[str, float]],
                        butce: int,
                        tavanlar: tuple[int, ...] = ARANAN_KUPON
                        ) -> list[tuple[int, int, float]]:
    """`(kupon sayısı, kolon/kupon, P(15/15))` — tavana göre eğri.

    Bir haftada operasyon yükü ile hedef arasındaki ödünleşmeyi görmek için.
    Eğri **monotondur**: tavanı büyütmek aramanın uzayını genişletir, yani
    bulunan plan kötüleşemez.
    """
    out = []
    for tavan in tavanlar:
        try:
            plan = coklu_plan(probs_listesi, butce, kupon_tavani=tavan)
        except ValueError:
            continue
        kolon_kupon = plan.kuponlar[0].kolon if plan.kuponlar else 0
        out.append((plan.kupon_sayisi, kolon_kupon, plan.p_onbes))
    return out
