"""Duyarlılık — ölçülen banko sapması planın **kararını** değiştiriyor mu.

§3.64 bir sapma ölçtü ve düzeltmeyi bilerek **uygulamadı**: etki dört sezon
boyunca gerçekti ama gözlenebilen son sezonda yoktu, ve önceden yazılmış
durma kuralı (`karne.T1_DUZELTME_ESIGI = 300`, bugün `n = 150`)
karşılanmadı. Bu modül o kararı tartışmıyor — `karne.BANKO_Q_DUZELTMESI`
sıfır kalıyor. Sorduğu soru başka ve bugüne kadar hiç sorulmadı:

    Durma kuralını beklemenin BEDELI ne?

Çünkü beklemek bedelsiz değilse bunu bilmek gerekir, bedelsizse de
bilmek gerekir — ikinci hâlde kural bir daha tartışılmaz.

─── Sapma neden doğrudan `P(15/15)`'in içinde ────────────────────────────

Gerçek bütçede (21.000 kolon) tek sistemin şekli **6 banko + 9 üçlü**dür.
Üçlü hiç kaçmaz (`q = 0`), yani plan hedefi tam olarak şudur:

    P(15/15) = Π p₁   (6 banko üzerinde)

Yani planın iddiası **yalnızca banko olasılıklarından** kuruludur. Banko
`p₁`'i `s` puan düşük yazılıyorsa iddia altıncı kuvvetten yanılır. Ölçüm,
gerçek bütçede, düz ölçekte, 114 haftada (`karne --kapsama --butce 210000`):

    banko rejimi   n = 684   model q %35,5   gerçekleşen %29,7
                   açık −%5,8   Wilson [%26,4, %33,2]   q DIŞINDA

`q = 1 − p₁` olduğuna göre aynı cümle: **`p₁` 5,8 puan düşük yazılıyor.**
(§3.64'ün −%5,6'sı aynı sapmanın *kaplama* ölçeğindeki, `n = 855`'lik
karşılığıydı; kaplama katmanı söküldü, bu onun düz ölçekteki ölçümüdür.)

─── İki ayrı soru, ve niçin ikisi de gerekli ─────────────────────────────

1. **Karar duyarlılığı.** Plan araması sapmalı `p`lerle koşulunca *seçilen
   şekil* değişiyor mu, ve seçilen şekil 114 haftada daha fazla 15/15
   tutuyor mu? Değişmiyorsa durma kuralı bedelsizdir.

2. **Plan düzeyi kalibrasyon.** `coklu.py` başlığındaki tablonun iki sütunu
   yan yana duruyor ve **ayrışıyorlar** — model %7,489 diyor, gerçekleşen
   15/114 = %13,2. Bu ayrışma bugüne kadar bir sınava sokulmadı. Sokulmalı,
   çünkü ikinci sütun birinciyi *bağımsız bir istatistikle* sınıyor: maç
   düzeyi kapsama değil, **hafta düzeyi 15/15 sayısı**.

İkisi birlikte sapmanın kendisini de sınar: sapma gerçekse, `p₁`'i 5,8 puan
kaldırmak plan düzeyi iddiayı gerçekleşene **yaklaştırmalıdır**. Yaklaşmıyor
ya da aşırı düzeltiyorsa açığın kaynağı marjinal olasılık değildir ve
kalan pay bağımlılığa (`kuyruk.py`, korpus üst sınırında kuyruk %5 şişer)
ya da sapmanın `p₁` boyunca düzgün olmayışına kalır.

─── ÖLÇÜLDÜ (2026-09-13) — üç cevap, üçü de "hayır" ──────────────────────

`cd backend && python scripts/banko_duyarliligi.py`, 114 hafta, 21.000
kolon. Ayrıntı ve tablolar: `docs/ISTATISTIK_YOL_HARITASI.md` §3.68.

**1. Kalibrasyon — açık gerçek.** Plan sabit tutulup yalnızca cetvel
değiştirildi:

    kupon   cetvel     beklenen   gözlenen    oran   iki yanlı
        1   taban          8,54         15   ×1,76      0,0444
        1   sapmalı       14,22         15   ×1,05      0,9097
      729   taban         12,58         21   ×1,67      0,0234
      729   sapmalı       18,46         21   ×1,14      0,5843

Havuzlanmış hâlde model **karamsar** ve ölçülen banko sapması açığı
kapatıyor. Kapanma bir uydurma değil: +%5,8 bu sınava ayarlanmadı, maç
düzeyi kapsamadan geldi ve olduğu gibi kondu.

**2. Ama açık GÜNCEL DEĞİL.** Sezon sınavı (§3.64'ün kararını belirleyen
sınav) aynı imzayı verdi — 729 kuponda ×2,15 · ×2,16 · ×1,85 · **×0,96**.
Havuzlanmış açık 2023/24'ten geliyor ve 2025/26'da model zaten tutuyor.
O sezonda **düzeltilmiş** model fazla iyimser olurdu: sapmalı cetvel 6,04
hafta bekliyor, gerçekleşen 4. Yani düzeltmeyi koymak bugünün verisinde
modeli bozardı.

**3. Ve karar hiç değişmiyor.** Sapmalı cetvelle kurulan plan taban cetvelle
ölçüldüğünde `tavan = 1`'de kupon **114/114** haftada birebir aynı
çıkıyor (eksen ortalaması 1,5 → 1,1 oynuyor, kupon oynamıyor: `M = 1`
hâlinde eksen/alt sistem ayrımı aynı kararın bölünmesidir). Çoklu
şekillerde plan kıpırdıyor ama hiçbir satırda iyileşmiyor (27 kuponda
%10,000 → %9,937, 729 kuponda %11,031 → %10,937). Sıralama korunuyor,
yani §3.67'nin kazancı senaryodan etkilenmiyor.

> **YENİDEN ÖLÇÜLDÜ (2026-09-13).** Yukarıdaki sayılar arama **tahsisli**
> hâle gelince (§3.71) yeniden koşuldu. Tek sistem satırı birebir aynı
> (o plan değişmedi); çoklu satırlar iyileşti ve `tavan = 1`'in **114/114**
> hükmü ile üç cevabın hiçbiri değişmedi.

Sebebi mekanik: sapma, planın zaten en emin olduğu maçlara uygulanan
neredeyse çarpımsal bir dönüşümdür ve adayları yeniden **sıralamaz**.
Kalibrasyon *sayıyı* değiştiriyor, *seçimi* değiştirmiyor.

─── Senaryo, düzeltme DEĞİL ──────────────────────────────────────────────

Buradaki dönüşüm depoya **konmaz**: üretim hattı `karne.BANKO_Q_DUZELTMESI`
(= 0,0) üzerinden geçer ve bu modül ona dokunmaz. Bekçisi
`test_duyarlilik.py::test_senaryo_URETIME_sizmiyor`.

Sapma "en emin `sayi` maç"a uygulanır çünkü ölçüldüğü yer optimizatörün
banko kümesidir ve gerçek bütçede o küme tam olarak **en emin 6 maç**tır
(`coklu.eksen_sec` ile aynı tanım — ikinci bir "en emin" tanımı yazılmadı).
Betik `sayi`yı tek bir değere sabitlemez, tarar: sonuç eşik seçimine
bağlıysa bu görünür olmalı.
"""
from __future__ import annotations

from typing import Any

from .coklu import eksen_sec
from .core import SEMBOLLER
from .ortak import kacak_dagilimi

#: Gerçek bütçede (21.000 kolon = 210.000 TL), düz ölçekte, 114 haftada
#: ölçülen banko `p₁` açığı — **senaryo girdisi**, uygulanan düzeltme değil.
#: Üreten: `cd backend && python -m spor_toto.karne --kapsama --butce 210000`
#: (banko rejimi: `n = 684`, model q %35,5 ↔ gerçekleşen %29,7).
BANKO_SAPMASI = 0.058

#: Taranan senaryo boyları: kaç maçın favorisi kaldırılıyor. 0 taban
#: (bugünkü davranış), 6 gerçek bütçedeki banko sayısı, 15 üst sınır
#: (korpus ölçümü genel futbolda sapma bulmadığı için 15 sapmayı **abartır**
#: ve bilerek öyle okunur).
TARANAN_SAYI = (0, 4, 6, 8, 15)


def sapma_uygula(probs_listesi: list[dict[str, float]],
                 sapma: float = BANKO_SAPMASI,
                 sayi: int = 6) -> list[dict[str, float]]:
    """En emin `sayi` maçın favorisini `sapma` kadar kaldırır.

    Kalan iki sembol, toplam 1 kalsın diye **oranlarını koruyarak** küçülür:
    ölçüm yalnızca favorinin ne kadar düşük yazıldığını söyledi, kaçağın
    hangi sembole gittiğini söylemedi, o yüzden orada bir şey uydurulmuyor.

    Girdi **değiştirilmez**; yeni liste döner.

    `sayi = 0` (taban) için erken dönüş YOK ve bunun bir sebebi var: erken
    dönüş ham sözlüğü kopyalıyordu, gövde ise normalleştiriyor — yani taban
    ile senaryo aynı olasılıkları iki ayrı biçimde veriyordu. Aşağıda
    `coklu._matris` ikisini de normalleştirdiği için sonuç değişmiyordu,
    ama sözleşme ayrışıktı. Bekçisi `test_sapma_SIFIR_taban_ile_ayni`
    (yazıldığında bu ayrışmayı tuttu).
    """
    if not -1.0 < sapma < 1.0:
        raise ValueError(f"Sapma (-1, 1) araliginda olmali: {sapma}")

    hedef = set(eksen_sec(probs_listesi, sayi)) if sayi > 0 else set()
    cikti: list[dict[str, float]] = []
    for i, d in enumerate(probs_listesi):
        yeni = {s: float(d.get(s, 0.0)) for s in SEMBOLLER}
        toplam = sum(yeni.values())
        if toplam <= 0:
            raise ValueError("Bir macin olasilik toplami sifir.")
        yeni = {s: v / toplam for s, v in yeni.items()}
        if i not in hedef:
            cikti.append(yeni)
            continue
        fav = max(yeni, key=lambda s: yeni[s])
        p1 = yeni[fav]
        # `min(...)` bir kırpma değil gerçek bir sınır: `p₁ + sapma > 1`
        # olduğunda kalan iki sembol negatife düşerdi.
        p1_yeni = min(max(p1 + sapma, 0.0), 1.0)
        kalan_eski = 1.0 - p1
        olcek = 0.0 if kalan_eski <= 0 else (1.0 - p1_yeni) / kalan_eski
        yeni = {s: (p1_yeni if s == fav else v * olcek)
                for s, v in yeni.items()}
        cikti.append(yeni)
    return cikti


def plan_kalibrasyonu(p_haftalar: list[float],
                      isabetler: list[int]) -> dict[str, Any]:
    """Planın `P(15/15)` iddiası hafta sayımıyla tutuyor mu.

    Her hafta kendi `p`siyle bir Bernoulli denemesidir ve haftalar ayrı maç
    kümelerinden kuruludur, yani **haftalar arası** bağımsızlık hafta *içi*
    bağımsızlıktan çok daha güvenli bir varsayımdır. O hâlde 15/15 tutan
    hafta sayısının dağılımı Poisson-binomdur ve depoda o hesap zaten var
    (`ortak.kacak_dagilimi` — adı maç kaçağından geliyor, gövdesi geneldir).

    Dönen `kuyruk` tek yanlıdır (`P(X ≥ gözlenen)`); `iki_yanli` onun
    standart iki katıdır, 1'de kırpılı. Ölçüt deponun geri kalanıyla aynı
    değil çünkü burada bir aralık değil bir **uyum sınavı** var: küçük
    `iki_yanli` modelin iddiasının gerçekleşenle bağdaşmadığını söyler.
    """
    if len(p_haftalar) != len(isabetler):
        raise ValueError("Hafta sayilari ayrisiyor.")
    if not p_haftalar:
        raise ValueError("Bos kesit kalibre edilemez.")

    dagilim = kacak_dagilimi(p_haftalar)
    gozlenen = int(sum(isabetler))
    beklenen = float(sum(p_haftalar))
    ust = float(sum(dagilim[gozlenen:]))
    alt = float(sum(dagilim[:gozlenen + 1]))
    return {
        "hafta": len(p_haftalar),
        "beklenen": beklenen,
        "gozlenen": gozlenen,
        "oran": None if beklenen <= 0 else gozlenen / beklenen,
        "kuyruk": ust,
        "iki_yanli": min(1.0, 2.0 * min(ust, alt)),
    }
