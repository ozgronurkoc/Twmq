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
        1          %7,489         15/114        %63,6   ← tek sistem
       27          %9,647         22/114        %73,3
       81         %10,121         21/114        %75,0
      729         %10,636         21/114        %76,8
   19.683         %10,865         22/114        %77,6   ← serbest

729 kupon, serbest kümenin kazancının **~%93'ünü** alır. Üretici:
`cd backend && python scripts/coklu_kiyasi.py`.

Gözlenen sütun `n = 114` ile gürültülüdür ve bunu bu tablonun kendisi
gösteriyor: 27 kuponda 22, 729 kuponda 21. Güvenilen sinyal **model**
sütunudur ve o monotondur — bekçisi `test_kupon_sayisi_buyudukce_P15_DUSMEZ`.

> **YENİDEN ÖLÇÜLDÜ (2026-09-13, ikinci kez).** Sayılar arama **tahsisli**
> hâle gelince değişti (§3.71): kupon başına ayrı alt sistem bütçesi, aynı
> parada 729 kuponu %10,461 → **%10,633**'e çıkardı ve serbest kümenin
> kazancından alınan pay %88 → %93 oldu. Tek sistem satırı **oynamadı** (tek
> kuponda bölünecek bütçe yok), yani kıyas tabanı yerinde.
>
> **ÜÇÜNCÜ KEZ (2026-09-13, değişken derinlik).** §3.72 aramaya bir aday daha
> koydu ve tablo dördüncü hanede oynadı (729: %10,633 → **%10,636**). Kazancın
> bu kadar küçük olması bulgunun kendisidir, ayrıntı aşağıda.

─── Gerçek bütçede (21.000 kolon = 210.000 TL) ───────────────────────────

Merdivenin farkı yuvarlak olmayan bütçelerde ortaya çıkar. Tek sistem
`2^a·3^b`'ye sıkıştığı için 19.683 kolonda takılı kalır; çoklu kupon
bütçenin neredeyse tamamını kullanır:

    kupon    kolon     model P(15/15)   gerçekleşen   13 hafta
        1   19.683          %7,489        15/114        %63,6   ← tek sistem
       27   20.970         %10,003        22/114        %74,6
       81   20.987         %10,489        21/114        %76,3
      243   20.998         %10,806        22/114        %77,4
      729   21.000         %11,034        21/114        %78,1

**×1,47**, aynı parada. Üretici:
`cd backend && python scripts/coklu_kiyasi.py --butce 21000`.

Serbest küme tavanı bu bütçede **%11,272**; 729 kuponluk plan onun
**%97,9**'una çıkıyor (§3.71).

> **NORMALLEŞTİRME DÜZELTİLDİ, iki tablo YENİDEN ÖLÇÜLDÜ (2026-09-13).**
> `p_alt` ham sözlükten okunuyordu (`p_eksen` ise normalleştirilmiş `P`den):
> arşiv satırları dört haneye yuvarlı ve 1,0001 toplayabildiği için
> `plan.p_onbes`, aynı kuponu yeniden ölçen `p_onbes`ten binde 0,3'e kadar
> büyük çıkıyordu — ve fazlalık adaylara **eşit binmediği** için (üçlü
> bırakılan maç sayısı kadar) aramanın sıralamasını da oynatabiliyordu.
> Düzeltildi; bekçisi `test_p_onbes_NORMALLESMEMIS_girdide_de_AYNI`. İki
> tablo yeniden koşuldu: **basılan hanelerde hiçbir sayı değişmedi** (en
> büyük oynama %7,4895 → %7,4890), gözlenen sütun ve kademe sayımları
> birebir aynı. Değişen tek şey `tavan = 3`ün kupon ortalaması (2,5 → 2,4),
> yani en az bir haftada seçilen yapılandırma gerçekten oynadı. Kusur
> **canlı haftalara değmedi**: `hafta_NN_coklu.json` kayıtları satırları tam
> 1 toplayan olasılıklarla kuruldu ve kaydın 1e-9'luk bekçisi hep yeşildi —
> kusurun bugüne kadar görünmemesinin sebebi de o.

Yapı: maçlar **eminliğe göre** sıralanır; bir kupon bu sıranın bir ön ekini
tekleştirir (**eksen**) ve kalan maçlarda bir **alt sistem** oynar — onu
`secim.secim_cephesi` çözer. Sabit derinlikte bütün kuponların ön eki aynı
boydadır (`d`) ve eksenin `3^d` bileşiminden en olası `M` tanesi oynanır;
değişken derinlikte (§3.72) ön ek boyu kupondan kupona değişebilir.

`M = 1` tam olarak bugünkü tek sistemdir. Yani bu modül mevcut davranışı
**içerir** ve arama onu bir aday olarak gezer; `M`i büyütmek genelleştirir.

─── Alt sistem bütçesi kupon başına AYRI (§3.71) ─────────────────────────

Burada önce *"kalan `15−d` maç her kuponda **aynı** alt sistemdir"* yazıyordu
ve o eşitlik ölçülmemiş bir kısıttı. Hedef şu:

    P(15/15) = Σ_j q_j · p_alt_j        q_j: j. kuponun eksen olasılığı

Bir kuponun alt sistemini genişletmenin değeri `q_j` ile çarpılıyor ve `q_j`
iki mertebe ayrışıyor (hepsi favori ↔ 81. bileşim). Eşit bölmek, o hâlde,
olası bileşime az olanaksız bileşime çok vermek demek. Arama artık
**ayrılabilir bir sırt çantası** çözüyor (`_tahsis`): cephenin üst konveks
kabuğunda, en yüksek `q_j · Δp / Δbedel` oranlı kupon yükseltilerek. Ölçülen
(114 hafta, gerçek bütçe): 729 kuponda %10,602 → **%11,031**, yani ×1,041 ve
serbest küme tavanının %94,1'inden %97,9'una.

Tek tip aday aramada **kalıyor**, yani yeni arama eskisinin üst kümesi ve
hiçbir haftada ondan kötü olamaz (570 kıyasın 570'inde doğrulandı).

─── Eksen boyu SABİT olmak zorunda değil — ve olması da gerekmiyor (§3.72) ─

§3.71 bitince şu açık kalmıştı: eksen hâlâ **sabit boyda**, yani bütün
kuponlarda aynı `d` maç tekleştiriliyor. İki kısıt görünüyordu: granülerlik
tek tip (hepsi favori dalı ile 81. bileşim aynı inceliği alıyor, oysa `q` iki
mertebe ayrışıyor) ve **artan kütle düşüyor** (en olası `M` bileşimin dışı
hiç oynanmıyor — ölçüldü, eksen kütlesinin **%83'ü**). Beklenti, az kuponla
oynandığında masada değer olduğuydu.

Aile genelleştirildi: kuponlar artık eminlik sırasının ön ek ağacında bir
**antizincir** (`_degisken_derinlik`) ve sabit derinlik bunun özel hâli.
Ölçüldü (114 hafta, gerçek bütçe) ve **beklenti yanlandı**:

    tavan    sabit derinlik    + değişken    kazanç   kapanan açık
       27           %9,9999      %10,0025   ×1,00026          %0,2
       81          %10,4879      %10,4892   ×1,00013          %0,2
      729          %11,0312      %11,0337   ×1,00023          %1,0

570 kıyasın 570'inde geri gidiş yok (aile üst küme, o yüzden tanım gereği),
ama kazanç binde birler. **Sebebi de ölçüldü ve sezgisel içermiyor**: sabit
derinlikli planın yaprak kümesi bu ailenin bir üyesidir, o hâlde üstünde
ailenin hamleleri tek tek denenebilir. En düşük olasılıklı yaprağı atıp terk
edilmiş en olası düğümü koymak — kupon sayısı sabit, bütçe yeniden ve kesin
dağıtılmış — 114 haftada binde 0,3'ü geçmiyor. Yani sabit derinlikli
plan bu hamle kümesinde **yerel en iyi**; bulgu ailenin, aramanın değil.

Terk edilen %83'lük kütle ucuz durmuyor: onu kapatmak hem kolon hem kupon
yuvası harcıyor ve ikisinin marjinal getirisi derinleşmeninkiyle aynı yerde
buluşuyor. Üretici: `cd backend && python scripts/derinlik_kiyasi.py --butce
21000 --serbest` ve `--mekanizma 114`.

Aday aramada **kalıyor**: gerilemesi imkânsız (en iyisi seçiliyor), maliyeti
hafta başına onda birkaç saniye, ve kaldırılırsa yanlanan beklentinin kaydı
yeniden koşulamaz hâle gelir. `degisken_derinlik=False` onu kapatır ve
ölçümün kıyas tabanı odur.

─── Yan fayda: bütçe merdiveni kalkıyor ──────────────────────────────────

Tek sistemde bedel `2^a·3^b` olduğu için bütçe **basamaklıdır**: 19.683 ile
21.000 kolon *aynı* kuponu alır, aradaki 13.170 TL hiçbir şey satın almaz.
Çoklu kuponda bedel `M · c`'dir ve `M` serbest tamsayıdır, yani basamak
büyük ölçüde kalkar.

> **Ama burada önce "merdiven kalktı" yazıyordu ve bu fazla iddialıydı.**
> Bütün kuponlar aynı alt sistemi oynadığı sürece bedel `M · c` çarpımına
> sıkışır ve artan hâlâ harcanamaz: 21.000 kolonluk bütçede eski arama
> 19.683 kolon kullanıyordu. Kupon başına **ayrı** bütçe (§3.71) artanı da
> harcıyor — 21.000'in 21.000'i — ve ölçülen kazancın yarısı tam olarak
> buradan geliyor (yuvarlak bütçede ×1,016, gerçek bütçede ×1,041).

─── Sınır: bağımsızlık — ve artık ÖLÇÜLDÜ ────────────────────────────────

Buradaki olasılıklar maçlar arası **bağımsızlık** varsayar. Burada önce şu
yazıyordu: *"bu her iki şekli de aynı yönde etkiler, oran görece
dayanıklıdır — ama mutlak değer bu varsayıma bağlıdır"*. İkinci yarısı
ölçülmüştü (§3.46); **birinci yarısı bir varsayımdı** ve şekle göre farklı
çıkabilirdi. Ölçüldü (§3.70): `kuyruk.kapsama` §3.46'nın `a`sını üç sembole
taşıyor — favori göstergesinde eşik birebir aynı kaldığı için `ρ` yeniden
kalibre edilmiyor — ve 114 hafta bağımlı hâlde yeniden fiyatlanıyor.

    19.683 kolon      bağımsız   en kötü makul a (0,0166)   şişme
    tek sistem          %7,489                    %8,050    ×1,075
    729 kupon          %10,636                   %11,905    ×1,119
    oran                 ×1,42                     ×1,48

Oran **gerilemedi, büyüdü**; 114 haftanın hiçbirinde çoklu plan tek sistemin
gerisine düşmüyor ve en iyi tavan her senaryoda 729'da kalıyor. Yani cümlenin
birinci yarısı ayakta, ama artık "görece dayanıklı" değil **ölçülmüş** —
bağımlılık çoklu kupona biraz daha yarıyor. Mutlak değer ise %12'ye kadar
şişiyor ve öyle okunmalıdır. Üretici:
`cd backend && python scripts/bagimli_kapsama.py`.

─── Mutlak değer sınandı: OKUMA KURALI ───────────────────────────────────

Yukarıdaki tablonun iki sütunu (model ↔ gerçekleşen) ayrışıyor ve bu
ayrışma ölçüldü (`spor_toto.duyarlilik`, §3.68). Havuzlanmış 114 haftada
model **karamsar**: tek sistemde beklenen 8,54 hafta, gerçekleşen 15
(×1,76); 729 kuponda 12,58 ↔ 21 (×1,67). Açığın tamamını, bağımsız ölçülmüş
banko sapması (`p₁` 5,8 puan düşük yazılıyor) kapatıyor.

**Ama tablodaki sayılar yeniden ÖLÇEKLENMEDİ ve ölçeklenmeyecek.** Sezon
kırılımı açığın 2023/24'ten geldiğini ve 2025/26'da **kapandığını** gösterdi
(729 kuponda ×0,96); düzeltilmiş model o sezonda fazla iyimser olurdu.
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
    729 kupon    26.304        **+%41**

Sebebi geriye dönük açık: olasılığa göre en büyük `N` kolon kümesi yalnızca
15'e değil 12–13'e de daha yakın durur; çarpımın satın almak zorunda kaldığı
köşeler hiçbir kademeye yaramıyordu. Yani burada bir ödünleşme yok — cümle
silinmedi, **düzeltildi** (kayıt yeniden yazılmaz, `.claude/olcum_kutugu.json`).
"""
from __future__ import annotations

import bisect
import heapq
from typing import TYPE_CHECKING, NamedTuple, TypeAlias

import numpy as np

from .core import SEMBOLLER, sirala_semboller

if TYPE_CHECKING:  # `secim` çalışma zamanında TEMBEL çekiliyor (döngü),
    from .secim import Secim  # tip burada gerekiyor ve orada gerekmiyor.

#: Kupondaki maç sayısı.
MAC_SAYISI = 15

#: Cephe noktası: `(bedel, alt sistemin kaçmama olasılığı, planın kendisi)`.
#: Eksen 15 maçın tamamını kapladığında alt sistem **yoktur** ve nokta
#: `(1, 1.0, None)`'dır — kupon yalnızca eksen bileşiminin kendisidir.
Nokta: TypeAlias = "tuple[int, float, Secim | None]"

#: Sembol → `_matris` sütunu. İki yerde gerekiyordu ve iki yerde ayrı ayrı
#: kuruluyordu.
_INDEKS: dict[str, int] = {s: j for j, s in enumerate(SEMBOLLER)}

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
    """Olasılıkları satır toplamı 1 olan matrise çevirir — **sembol düzeninde**.

    Sıralama YOK: sütunlar `core.SEMBOLLER` (`1/0/2`) düzenindedir. Docstring
    burada "büyükten küçüğe sıralı" diyordu ve bu yanlıştı — `eksen_sec`in
    içindeki uyarı (*"`P[:, 0]` DEĞİL, ilk sütun ev sahibidir"*) tam bu
    yanlışa karşı yazılmış.
    """
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

    * **eksen** — eminlik sırasının bir ön eki, kupon içinde tek tek
      sabitlenir. Sabit derinlikte boyu (`d`) bütün kuponlarda aynıdır ve
      `3^d` bileşimden en olası `M` tanesi oynanır; değişken derinlikte
      (§3.72) kupondan kupona değişebilir.
    * **alt sistem** — eksen dışında kalan maçlar üzerinde bir tam sistem.
      Bütçesi kupon başına **ayrıdır** (§3.71, `_tahsis`) ve onu
      `secim.secim_cephesi` çözer.

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


def _eksen_olasiliklari(P: np.ndarray, eksen: list[int], M: int
                        ) -> tuple[list[tuple[int, ...]], list[float]]:
    """Eksenin en olası `M` bileşimi ve **her birinin ayrı olasılığı**.

    `_eksen_bilesimleri` toplamı döndürüyor; tahsis için tek tek gerekiyor,
    çünkü bir kupona ne kadar bütçe ayrılacağını belirleyen şey tam olarak o
    kuponun eksen olasılığıdır.
    """
    bilesimler, _ = _eksen_bilesimleri(P, eksen, M)
    q = [float(np.prod([P[i][s] for i, s in zip(eksen, b)]))
         for b in bilesimler]
    return bilesimler, q


def _p_alt(P: np.ndarray, kalanlar: list[int],
           secimler: list[list[str]]) -> float:
    """Alt sistemin kaçmama olasılığı — **normalleştirilmiş** `P`den."""
    return float(np.prod([P[i, [_INDEKS[s] for s in sec]].sum()
                          for i, sec in zip(kalanlar, secimler)]))


def _ust_kabuk(noktalar: list[Nokta]) -> list[Nokta]:
    """Cephenin **üst konveks kabuğu** — marjinal oranlar azalan kalsın.

    Açgözlü tahsis (aşağıda) ancak "bir kuponu bir basamak yükseltmenin
    kazanç/bedel oranı" o kupon için azalıyorsa doğru çalışır. Cephenin
    kendisi bunu garanti etmez: bedel ×2/×3 sıçradığı için aradaki bir nokta
    komşularının doğrusal birleşiminin altında kalabilir ve açgözlü o noktada
    durup daha iyisini kaçırabilir. Kabuktaki noktalar cephenin **gerçek**
    noktalarıdır, yani seçilen her plan oynanabilir; atılanlar yalnızca
    baskılanmışlardır.
    """
    kabuk: list[Nokta] = []
    for nokta in noktalar:
        c, p, _ = nokta
        while len(kabuk) >= 2:
            (c1, p1, _), (c2, p2, _) = kabuk[-2], kabuk[-1]
            # kabuk[-1] baskın değilse at: oran azalmıyor demektir
            if (p2 - p1) * (c - c2) <= (p - p2) * (c2 - c1):
                kabuk.pop()
            else:
                break
        kabuk.append(nokta)
    return kabuk


def _tahsis(q: list[float], noktalar: list[Nokta],
            butce: int) -> tuple[float, list[Nokta]] | None:
    """Kupon başına alt sistem — **eşit bölmek yerine olasılığa göre**.

    ─── Niçin eşit bölmek yanlış ─────────────────────────────────────────

    Eksen bileşimlerinin olasılıkları yüzler kat ayrışıyor: en olası bileşim
    (hepsi favori) ile 81.'si arasında iki mertebe fark var. Alt sistem
    bütçesini eşit bölmek, o iki kupona aynı parayı vermek demek — oysa bir
    kuponun alt sistemini genişletmenin değeri tam olarak o kuponun eksen
    olasılığıyla çarpılıyor (`P(15/15) = Σ_j q_j · p_alt_j`). Yani sabit
    bütçe altında doğru şey **ayrılabilir bir sırt çantası** çözmek.

    ─── Çözüm: açgözlü, ve niçin kesin ──────────────────────────────────

    Her kupon en ucuz noktadan başlar; sonra "bir basamak yükseltmenin
    `q_j · Δp / Δbedel` oranı" en büyük olan kupon yükseltilir, bütçe
    bitene kadar. Üst konveks kabukta oranlar her kupon için azalan
    olduğundan bu, kabuk üzerinde tanımlı problemin **kesin** çözümüdür;
    kalan pay yalnızca bütçenin son artığı kadardır (bölünemeyen basamak).

    Dönen değer `Σ q_j · p_alt_j` ve kupon başına seçilen noktalardır.
    `None` döner ancak en ucuz noktadan bile `len(q)` kupon alınamıyorsa.
    """
    kabuk = _ust_kabuk(noktalar)
    if not kabuk:
        return None
    return _tahsis_kabuklu(q, [kabuk] * len(q), butce)


def _tahsis_kabuklu(q: list[float], kabuklar: list[list[Nokta]],
                    butce: int) -> tuple[float, list[Nokta]] | None:
    """`_tahsis`in genel gövdesi: her kuponun **kendi** kabuğu olabilir.

    Sabit derinlikli eksende bütün kuponlar aynı `15−d` maçı alt sistem
    olarak oynar, yani cephe tektir ve `_tahsis` onu `M` kez kopyalar.
    Değişken derinlikte (§3.72) kuponların eksen boyu farklı, o hâlde alt
    sistem uzayları da farklı — ortak bir cephe yok. Açgözlü kural
    değişmiyor: en yüksek `q_j · Δp / Δbedel` oranlı basamak alınır.

    Kabuklar **hazır** gelir (`_ust_kabuk`ten geçmiş): bu gövde onları
    yeniden kabuklamaz, çünkü çağıranların ikisi de kabuğu zaten derinlik
    başına bir kez kuruyor.
    """
    M = len(q)
    if M == 0 or any(not k for k in kabuklar):
        return None
    taban = sum(k[0][0] for k in kabuklar)
    if taban > butce:
        return None

    seviye = [0] * M
    harcanan = taban
    # `-oran` ile en iyi yükseltme yığının tepesinde; eşitlikte küçük `j`.
    yigin: list[tuple[float, int]] = []

    def _it(j: int, k: int) -> None:
        kabuk = kabuklar[j]
        if k + 1 < len(kabuk):
            dc = kabuk[k + 1][0] - kabuk[k][0]
            dp = kabuk[k + 1][1] - kabuk[k][1]
            heapq.heappush(yigin, (-q[j] * dp / dc, j))

    for j in range(M):
        _it(j, 0)
    while yigin:
        _oran, j = heapq.heappop(yigin)
        k = seviye[j]
        kabuk = kabuklar[j]
        dc = kabuk[k + 1][0] - kabuk[k][0]
        # Bütçe yetmiyorsa bu kupon için DAHA UCUZ bir basamak da yok
        # (kabukta bedel artan), o yüzden kupon burada durur.
        if harcanan + dc <= butce:
            harcanan += dc
            seviye[j] = k + 1
            _it(j, k + 1)

    deger = sum(q[j] * kabuklar[j][seviye[j]][1] for j in range(M))
    return deger, [kabuklar[j][seviye[j]] for j in range(M)]


# ─── Değişken derinlikli eksen (§3.72) ───────────────────────────────────
#
# Sabit derinlikte **bütün** kuponlar aynı `d` maçı tekleştirir ve eksenin
# `3^d` bileşiminden en olası `M` tanesi oynanır. İki kısıt birden var:
#
# 1. **Granülerlik tek tip.** Hepsi favori dalı ile 81. bileşim aynı
#    inceliği alıyor, oysa `q` iki mertebe ayrışıyor.
# 2. **Artan kütle düşüyor.** En olası `M` bileşimin dışında kalan her şey
#    hiç oynanmıyor — `M = 27`, `d = 5` iken 243 bileşimin 216'sı boşta.
#
# Ağaç ikisini de kaldırır: kuponlar eminlik sırasının **ön eklerinde**
# duran bir antizincirdir. Olası dal derinlemesine bölünür, olanaksız dal
# sığ tek bir kupon olarak durur (yani düşmez). `M = 3^d` ile hepsi aynı
# derinlikte olan aile bu ailenin özel hâlidir.
#
# ─── Niçin fiyatlı (Lagrange) büyütme ────────────────────────────────────
#
# Bir düğümü bölmenin değeri, çocuklara **eşit olmayan** bütçe verebilmekten
# gelir; eşit bölmek tanım gereği hiçbir şey kazandırmaz (çocuklara `c`,
# ebeveyne `3c` vermek aynı şeydir — ebeveyn o maçı üçlü oynar). O hâlde
# bölmenin kazancı ancak para **fiyatlıyken** ölçülebilir: sabit bir `λ`
# altında her yaprak `q·p − λ·bedel`i enbüyükleyen kabuk noktasını seçer ve
# bölme kazancı çocukların toplamı eksi ebeveynin değeridir. `λ` bir
# **ızgarada** taranır ve gerçek hedefe göre en iyisi alınır; **harcamayı
# yine tahsis yapar** (`_tahsis_kabuklu`, kesin), yani `λ` ağacın yalnızca
# ŞEKLİNİ belirler. Gerekçesi `FIYAT_IZGARASI`nda.

#: Taranan `λ` ızgarası, `p/bütçe`nin katları olarak. Merkez orada çünkü
#: `λ` bir **fiyat**tır: bütçenin son kolonunun `P(15/15)` cinsinden değeri,
#: yani büyüklük mertebesi `p/bütçe`dir. Ölçülen en iyi `λ` bu merkezin
#: 0,25–0,5 katında çıktı; ızgara onu iki yana da bolca aşıyor.
#:
#: **Niçin ızgara, niçin ikili arama değil.** İlk sürüm `λ`yı bütçeyi tam
#: harcayacak şekilde ikili aramayla buluyordu ve bu YANLIŞ hedefti: bütçeyi
#: zaten `_tahsis_kabuklu` kesin harcıyor, `λ`nın tek işi ağacın şeklini
#: seçmek. Üstelik bedel `λ`da süreksiz (ağaç bir anda köke iniyor), yani
#: ikili arama dejenere tek yapraklı ağaçta duruyordu — ölçüldü, tek
#: sistemin kendisini veriyordu. Izgara doğrudan **gerçek hedefi** tarıyor.
FIYAT_IZGARASI = tuple(0.35 * 2.0 ** (k / 2) for k in range(-6, 7))


class _Kat(NamedTuple):
    """Bir eksen derinliğinin alt sistem kabuğu — fiyatlamaya hazır hâlde.

    `neg_oran[i]`, kabuğun `i → i+1` basamağının marjinal oranının
    **eksisi**dir. Kabukta oranlar azalan olduğu için bu dizi **artan**dır ve
    `bisect` ile "bu fiyatta kaç basamak alınır" sorusu `O(log n)` olur.
    """

    kabuk: list[Nokta]
    bedel: tuple[int, ...]
    p: tuple[float, ...]
    neg_oran: tuple[float, ...]


def _kat_kur(noktalar: list[Nokta]) -> _Kat | None:
    """Cepheyi kabukla ve fiyatlama dizilerini çıkar."""
    kabuk = _ust_kabuk(noktalar)
    if not kabuk:
        return None
    bedel = tuple(int(c) for c, _p, _s in kabuk)
    p = tuple(float(x) for _c, x, _s in kabuk)
    neg = tuple(-(p[i + 1] - p[i]) / (bedel[i + 1] - bedel[i])
                for i in range(len(kabuk) - 1))
    return _Kat(kabuk=kabuk, bedel=bedel, p=p, neg_oran=neg)


def _cepheler(probs_listesi: list[dict[str, float]], P: np.ndarray,
              butce: int, sira: list[int]
              ) -> tuple[list[list[Nokta] | None], list[_Kat | None]]:
    """Her eksen derinliği için alt sistem cephesi ve kabuğu — 16 DP, tek yer.

    `d` derinlikte eksen `sira`nın ilk `d` maçıdır ve alt sistem kalan
    `15−d` maçtır; cephe o maç kümesine ait, yani **yalnızca derinliğe**
    bağlı. Sabit derinlikli arama, ağaç araması ve mekanizma ölçümü
    (`scripts/derinlik_kiyasi.py`) aynı 16 cepheyi istiyor — üç kopya olsaydı
    biri sessizce eskirdi.

    Cephe **tam bütçeyle** çıkarılır, `bütçe // M` ile değil: tahsiste bir
    kupon ortalamanın çok üstüne çıkabilir ve o noktalar kırpılırsa tahsis
    eşit bölmeye geri düşer (prototipte tam bu oldu — kazanç sıfır göründü).
    """
    from .secim import secim_cephesi

    cepheler: list[list[Nokta] | None] = [None] * (MAC_SAYISI + 1)
    katlar: list[_Kat | None] = [None] * (MAC_SAYISI + 1)
    for d in range(MAC_SAYISI + 1):
        kalanlar = sorted(sira[d:])
        if kalanlar:
            cephe = secim_cephesi([probs_listesi[i] for i in kalanlar],
                                  butce, esik=0)
            if not cephe:
                continue
            noktalar: list[Nokta] = [
                (s.bedel, _p_alt(P, kalanlar, s.secimler), s) for s in cephe]
        else:
            noktalar = [(1, 1.0, None)]
        cepheler[d] = noktalar
        katlar[d] = _kat_kur(noktalar)
    return cepheler, katlar


def _en_iyi_nokta(kat: _Kat, w: float, lam: float) -> tuple[int, float] | None:
    """`w·p − λ·bedel`i enbüyükleyen kabuk noktası; değer `≤ 0` ise `None`.

    `None`, "bu dal bu fiyatta oynanmaz" demektir — sabit derinlikteki
    `sum(q[:sayi])` kırpmasının yerine geçen şey budur, ama kırpma artık
    **sıraya değil değere** bakıyor.
    """
    if w <= 0.0:
        return None
    # Kabukta `i → i+1` ancak `w·Δp > λ·Δc` iken alınır, yani `-oran < -λ/w`.
    # `neg_oran` artan olduğu için alınan basamaklar bir ön ektir.
    i = bisect.bisect_left(kat.neg_oran, -lam / w)
    deger = w * kat.p[i] - lam * kat.bedel[i]
    if deger <= 0.0:
        return None
    return i, deger


#: Ağacın bir yaprağı: `(q, derinlik, eksen bileşimi)`. Bileşim, eminlik
#: sırasının ilk `derinlik` maçına karşılık gelen **sembol indeksleri**dir.
Yaprak: TypeAlias = "tuple[float, int, tuple[int, ...]]"


def _agac_buyut(P: np.ndarray, sira: list[int], katlar: list[_Kat | None],
                tavan: int, lam: float) -> tuple[list[Yaprak], list[int], int] | None:
    """`λ` fiyatında açgözlü ağaç: `(yapraklar, kabuk indeksleri, bedel)`.

    Kök tek yapraktır (derinlik 0 — eksen yok, tek sistem). Her adımda
    "bölmenin kupon başına kazancı" en büyük yaprak bölünür; kazanç, çocuk
    değerlerinin toplamı eksi yaprağın kendi değeridir ve fiyat sabit
    olduğu için **yapraklar arası bağımsız**dır (bir yaprağın bölünmesi
    başkasının kazancını değiştirmez), yani yığın bayatlamaz.

    Bir çocuk bu fiyatta değer üretmiyorsa hiç alınmaz; o yüzden bölme bazen
    kupon sayısını ikiden az artırır ve bedava bölme (`delta = 0`) öne geçer.
    """
    kok = katlar[0]
    if kok is None:
        return None
    se = _en_iyi_nokta(kok, 1.0, lam)
    # Kök **düşemez**: bütçeyi harcayacak en az bir kupon olmak zorunda.
    # Değer negatifse en ucuz nokta alınır; bütçeyi zaten tahsis harcıyor.
    kok_i, kok_deger = se if se is not None else (0, kok.p[0] - lam * kok.bedel[0])

    dugum: TypeAlias = "tuple[int, tuple[int, ...]]"
    yaprak: dict[dugum, tuple[float, int]] = {(0, ()): (1.0, kok_i)}
    yigin: list[tuple[float, int, dugum,
                      list[tuple[dugum, float, int]]]] = []
    sayac = 0

    def _it(d: dugum, q: float, deger: float) -> None:
        """Bir yaprağın bölünme adayını yığına koyar (kazanç yoksa koymaz)."""
        nonlocal sayac
        k = d[0]
        if k >= MAC_SAYISI:
            return
        kat = katlar[k + 1]
        if kat is None:
            return
        mac = sira[k]
        cocuklar: list[tuple[dugum, float, int]] = []
        toplam = 0.0
        for s in range(len(SEMBOLLER)):
            qc = q * float(P[mac][s])
            c = _en_iyi_nokta(kat, qc, lam)
            if c is None:
                continue
            cocuklar.append(((k + 1, (*d[1], s)), qc, c[0]))
            toplam += c[1]
        if not cocuklar or toplam <= deger:
            return
        delta = len(cocuklar) - 1
        # Bedava bölme (`delta ≤ 0`) her zaman önce: kupon harcamıyor.
        anahtar = -float("inf") if delta <= 0 else -(toplam - deger) / delta
        heapq.heappush(yigin, (anahtar, sayac, d, cocuklar))
        sayac += 1

    _it((0, ()), 1.0, kok_deger)
    while yigin:
        _anahtar, _s, d, cocuklar = heapq.heappop(yigin)
        delta = len(cocuklar) - 1
        # Sığmayan bölme ATILIR, ertelenmez: kupon sayısı yalnızca artıyor,
        # yani bir daha sığmaz. Yığında kalan daha küçük `delta`lı adaylar
        # sığabilir ve döngü onlara devam eder.
        if len(yaprak) + delta > tavan:
            continue
        del yaprak[d]
        for cd, qc, idx in cocuklar:
            yaprak[cd] = (qc, idx)
            kat = katlar[cd[0]]
            assert kat is not None                       # `_it` onu gördü
            _it(cd, qc, qc * kat.p[idx] - lam * kat.bedel[idx])

    sirali = sorted(((q, k, bil, i) for (k, bil), (q, i) in yaprak.items()),
                    key=lambda x: (-x[0], x[1], x[2]))
    bedel = 0
    for _q, k, _bil, i in sirali:
        kat = katlar[k]
        assert kat is not None
        bedel += kat.bedel[i]
    return ([(q, k, bil) for q, k, bil, _i in sirali],
            [i for _q, _k, _b, i in sirali], bedel)


def _degisken_derinlik(P: np.ndarray, sira: list[int],
                       katlar: list[_Kat | None], butce: int, tavan: int,
                       taban_p: float
                       ) -> tuple[float, list[Yaprak], list[Nokta]] | None:
    """Değişken derinlikli eksen adayı: `(p_onbes, yapraklar, noktalar)`.

    `λ` yalnızca ağacın **şeklini** seçer; bütçeyi `_tahsis_kabuklu` kesin
    olarak harcar. Bu ayrım gereklidir: Lagrange gevşetmesi bütçeyi tam
    tutturamaz (basamaklar bölünemez) ve artan para boşa giderdi.

    `taban_p` sabit derinlikli aramanın o tavandaki hedefidir ve yalnızca
    `λ` ızgarasının merkezini ölçeklemeye yarar (`FIYAT_IZGARASI`); dönen
    değerin içine girmez.
    """
    if katlar[0] is None or taban_p <= 0.0:
        return None
    merkez = taban_p / butce
    en: tuple[float, list[Yaprak], list[Nokta]] | None = None
    for kat_sayi in FIYAT_IZGARASI:
        son = _agac_buyut(P, sira, katlar, tavan, kat_sayi * merkez)
        if son is None:
            continue
        yapraklar, _indeksler, _bedel = son
        kabuklar = [katlar[k].kabuk for _q, k, _b in yapraklar  # type: ignore[union-attr]
                    if katlar[k] is not None]
        if len(kabuklar) != len(yapraklar):
            continue
        sonuc = _tahsis_kabuklu([q for q, _k, _b in yapraklar], kabuklar, butce)
        if sonuc is None:
            continue
        if en is None or sonuc[0] > en[0]:
            en = (sonuc[0], yapraklar, sonuc[1])
    return en


def coklu_plan_serisi(probs_listesi: list[dict[str, float]],
                      butce: int,
                      tavanlar: tuple[int, ...] | None = None,
                      eksen_sirasi: list[int] | None = None,
                      degisken_derinlik: bool = True
                      ) -> dict[int, CokluPlan]:
    """Her kupon tavanı için en iyi plan — **tek aramada**.

    `coklu_plan`ı tavan tavan çağırmak aramayı her seferinde baştan yapardı;
    114 haftalık kıyasta bu yedi kat israftı. Arama zaten bütün eksen
    boylarını (`d`) geziyor, yani tek geçişte her tavanın cevabı toplanır.

    Dönen sözlüğün anahtarları verilen tavanlardır ve değerler **birikimli
    en iyi**dir, yani tavan büyüdükçe `p_onbes` düşemez.

    `eksen_sirasi` verilmezse eksen **en emin maçtan** başlayarak kurulur
    (`eksen_sec`in kuralı). Parametre olarak durmasının sebebi şu: o kural bir
    **iddiaydı** ve ölçülmeden duruyordu; sınanabilmesi için aramanın başka
    bir sırayla da koşması gerekiyordu (§3.71, `scripts/tahsis_kiyasi.py
    --eksen-sinavi`). Ölçüldü (20 hafta, tavan 81): ters sıra **×0,755**, tek
    takas araması ×1,0002 — yani kural doğru ve arama onu **varsayım olarak
    değil ölçülmüş olarak** kullanıyor.

    `degisken_derinlik` üçüncü aday ailesini kapatır. O da aynı sebeple
    parametre: ailenin kazancı **ölçülecekti** ve bir aramanın kazancı ancak
    onsuz koşulan bir arama varsa ölçülebilir (§3.72,
    `scripts/derinlik_kiyasi.py`). Ölçüldü — kazanç binde birler mertebesinde
    ve **hiçbir haftada geri gidiş yok**; aday, gerilemesi imkânsız olduğu
    için aramada kalıyor.

    ─── Arama üç aday ailesini birlikte geziyor ──────────────────────────

    Her `d` için kalan `15−d` maçın **bütün bütçelerdeki** en iyi alt
    sistemleri bir kez çıkarılır (`secim.secim_cephesi`, tek DP) ve üç aday
    değerlendirilir:

    * **tek tip** — bütün kuponlar aynı alt sistemi oynar. Bu, bu modülün
      ilk sürümünün yaptığı şeydir ve aramada **kalıyor**: cephenin her
      noktası için `M = min(tavan, bütçe // bedel, 3^d)` kupon alınır.
    * **tahsisli** — her kupon eksen olasılığına göre **ayrı** bir alt
      sistem bütçesi alır (`_tahsis`). Eksen bileşimlerinin olasılıkları
      yüzler kat ayrıştığı için eşit bölmek masada değer bırakıyordu;
      ölçüldü (§3.71).
    * **değişken derinlik** — kuponların eksen boyu **aynı olmak zorunda
      değil**: yapraklar eminlik sırasının ön ek ağacında bir antizincirdir
      (`_degisken_derinlik`). Sabit derinlik bu ailenin özel hâlidir.
      Ölçüldü (§3.72) ve kazancı binde birler çıktı — sebebi de ölçüldü:
      sabit derinliğin terk ettiği eksen kütlesinin marjinal getirisi, aynı
      parayı derinleşmeye harcamanınkiyle neredeyse **aynı**.

    Üçünün en iyisi seçilir, yani arama her genişlemede eskisinin **üst
    kümesi** olarak kalıyor ve hiçbir haftada ondan kötü olamaz. Bekçisi
    `test_tahsis_TEK_TIP_adayini_da_geziyor`,
    `test_tahsisli_plan_ESKI_aramadan_kotu_DEGIL` ve
    `test_agac_adayi_ARAMAYI_DARALTMIYOR`.
    """
    if butce is None or butce <= 0:
        raise ValueError("Butce pozitif bir kolon sayisi olmali.")
    if len(probs_listesi) != MAC_SAYISI:
        raise ValueError(f"{MAC_SAYISI} macin olasiligi gerekir.")

    istenen = sorted(tavanlar) if tavanlar else sorted(ARANAN_KUPON)
    tavan_ust = max(istenen)
    P = _matris(probs_listesi)
    if eksen_sirasi is None:
        emin_sira = np.argsort(-P.max(axis=1)).tolist()   # en eminden başla
    elif sorted(eksen_sirasi) != list(range(MAC_SAYISI)):
        raise ValueError(f"Eksen sirasi {MAC_SAYISI} macin permutasyonu olmali.")
    else:
        emin_sira = list(eksen_sirasi)

    #: tavan -> (p_onbes, kupon sayısı, gövde verisi). Gövde iki biçimden
    #: biri: sabit derinlik `("duz", eksen, kalanlar, bileşimler, noktalar)`,
    #: değişken derinlik `("agac", yapraklar, noktalar)`. Kupon GÖVDELERİ
    #: burada kurulmaz — yalnızca kazanan için kurulur.
    en_iyi: dict[int, tuple[float, int, tuple]] = {}

    # Ağaç araması da aynı 16 cepheyi istiyor; ikinci bir DP koşmuyor.
    cepheler, katlar = _cepheler(probs_listesi, P, butce, emin_sira)

    for d in range(MAC_SAYISI + 1):
        noktalar = cepheler[d]
        if noktalar is None:
            continue
        eksen = sorted(emin_sira[:d])
        kalanlar = sorted(emin_sira[d:])
        kat = katlar[d]
        bilesimler, q = _eksen_olasiliklari(P, eksen, min(tavan_ust, 3 ** d))

        for tavan in istenen:
            M = min(tavan, 3 ** d)
            #: (p, kupon sayısı, kupon başına nokta) — kupon GÖVDELERI
            #: burada kurulmaz, yalnızca kazanan için kurulur. Önce hepsi
            #: kuruluyordu ve 2.187 kupon × 16 eksen boyu × 8 tavan =
            #: haftada yüz binlerce gereksiz liste demekti.
            adaylar: list[tuple[float, int, list[Nokta]]] = []

            # ─── aday 1: tek tip (eski aramanın tamamı) ────────────────
            for nokta in noktalar:
                bedel, p_alt, _alt = nokta
                sayi = min(M, butce // bedel)
                if sayi < 1:
                    continue
                adaylar.append((sum(q[:sayi]) * p_alt, sayi, [nokta] * sayi))

            # ─── aday 2: tahsisli ─────────────────────────────────────
            sonuc = (None if kat is None
                     else _tahsis_kabuklu(q[:M], [kat.kabuk] * M, butce))
            if sonuc is not None:
                adaylar.append((sonuc[0], M, sonuc[1]))

            for p, sayi, secilen in adaylar:
                varsa = en_iyi.get(tavan)
                # eşitlikte AZ kupon kazanır: aynı hedefe daha az operasyonla
                if varsa is None or (p, -sayi) > (varsa[0], -varsa[1]):
                    en_iyi[tavan] = (p, sayi, ("duz", eksen, kalanlar,
                                               bilesimler[:sayi], secilen))

    # ─── aday 3: değişken derinlikli eksen (§3.72) ────────────────────────
    # Döngüden SONRA: bütün derinliklerin kabuğu gerekiyor ve arama `d` boyunca
    # değil kupon sayısı boyunca ilerliyor.
    for tavan in istenen if degisken_derinlik else ():
        varsa = en_iyi.get(tavan)
        agac = _degisken_derinlik(P, emin_sira, katlar, butce, tavan,
                                  varsa[0] if varsa else 0.0)
        if agac is None:
            continue
        p, yapraklar, secilen = agac
        if varsa is None or (p, -len(yapraklar)) > (varsa[0], -varsa[1]):
            en_iyi[tavan] = (p, len(yapraklar), ("agac", yapraklar, secilen))

    if not en_iyi:
        raise ValueError(f"Butce hicbir plani karsilamiyor: {butce}")

    seri: dict[int, CokluPlan] = {}
    for tavan, (p, _sayi, veri) in sorted(en_iyi.items()):
        if veri[0] == "duz":
            _tip, eksen, kalanlar, bilesimler, secilen = veri
            kuponlar = [
                _kuponlari_kur([bilesim], eksen, kalanlar, nokta[2], nokta[0])[0]
                for bilesim, nokta in zip(bilesimler, secilen)]
            ortak = eksen
        else:
            _tip, yapraklar, secilen = veri
            kuponlar = []
            for (_q, derinlik, bilesim), nokta in zip(yapraklar, secilen):
                y_eksen = emin_sira[:derinlik]
                y_kalan = sorted(emin_sira[derinlik:])
                kuponlar += _kuponlari_kur([bilesim], y_eksen, y_kalan,
                                           nokta[2], nokta[0])
            # Ortak eksen = HER kuponda tekleşen maçlar, yani en sığ yaprağın
            # ön eki. Sabit derinlikte bu tam olarak eski `eksen`dir.
            ortak = sorted(emin_sira[:min(k for _q, k, _b in yapraklar)])
        seri[tavan] = CokluPlan(kuponlar=kuponlar, eksen=ortak,
                                kolon=sum(k.kolon for k in kuponlar),
                                p_onbes=p)
    return seri


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
    toplam = 0.0
    for k in kuponlar:
        p = 1.0
        for i, sec in enumerate(k.secimler):
            p *= sum(P[i][_INDEKS[s]] for s in sec)
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
