"""`ortak` modülünün bekçileri — paylaşılan hesapların tek kaynağı.

Bu dosyanın en kritik testi `test_ayrisim_ozdesligi_tam_kapanir`. Murphy
ayrışımı dört terime bölünür ve o dört terim Brier'i **birebir** toplamak
zorundadır; toplamıyorsa ayrışım bir yaklaşıklıktır ve yaklaşıklığın
büyüklüğü bilinmez. Klasik üç terimli yazım tam da bu yüzden yanıltıcıdır:
bantlama bir artık bırakır ve o artık genelde yazılmaz.

İkinci bekçi `test_duzgun_tahminci_kapali_form`: bilgi taşımayan bir
tahminci için ayrışımın ne vermesi gerektiği **elle hesaplanabilir**
(REL = RES = 0, `Σ UNC = Σ ō_s(1−ō_s)`), yani test kendi beklentisini
koddan değil matematikten alır.
"""
from __future__ import annotations

import sys
from itertools import pairwise
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spor_toto.ortak import (
    BRIER_ESIT,
    OLASILIK_BANTLARI,
    SEMBOLLER,
    brier,
    brier_ayrisimi,
    karisiklik_matrisi,
    siralama_olculeri,
    wilson,
)

ALANLAR = ("brier", "guvenilirlik", "cozunurluk", "belirsizlik", "bant_ici")


def _kesit(tohum: int = 7, n: int = 900) -> tuple[list[dict[str, float]], list[str]]:
    """Sentetik ama gerçekçi bir kesit: olasılıklar dağılır, sonuçlar onlara uyar.

    Sonucu olasılıktan üretmek kasıtlı — kalibre bir tahminci üretir, yani
    `guvenilirlik` küçük ve `cozunurluk` belirgin çıkar. Ayrışımın *işareti*
    böylece bilinir; testler yalnızca özdeşliğe değil beklenen yöne de bakar.
    """
    import random

    rnd = random.Random(tohum)
    tahminler: list[dict[str, float]] = []
    kodlar: list[str] = []
    for _ in range(n):
        ham = [rnd.random() + 0.05 for _ in SEMBOLLER]
        toplam = sum(ham)
        p = {s: v / toplam for s, v in zip(SEMBOLLER, ham)}
        esik = rnd.random()
        birikim = 0.0
        secilen = SEMBOLLER[-1]
        for s in SEMBOLLER:
            birikim += p[s]
            if esik <= birikim:
                secilen = s
                break
        tahminler.append(p)
        kodlar.append(secilen)
    return tahminler, kodlar


# ─── Brier ayrışımı ───────────────────────────────────────────────────────

def test_ayrisim_ozdesligi_tam_kapanir():
    """BS = REL − RES + UNC + ICI, kayan noktaya kadar. **Asıl bekçi budur.**"""
    tahminler, kodlar = _kesit()
    a = brier_ayrisimi(tahminler, kodlar)
    for s in SEMBOLLER:
        blok = a["semboller"][s]
        beklenen = (blok["guvenilirlik"] - blok["cozunurluk"]
                    + blok["belirsizlik"] + blok["bant_ici"])
        assert blok["brier"] == pytest.approx(beklenen, abs=1e-12), (
            f"sembol {s}: ayrisim {beklenen} != brier {blok['brier']}")
        assert blok["artik"] == pytest.approx(0.0, abs=1e-12)
    assert a["toplam"]["artik"] == pytest.approx(0.0, abs=1e-12)


def test_ayrisim_toplami_brier_in_kendisi():
    """Üç sembolün toplamı `ortak.brier`in maç ortalamasıyla aynı olmalı.

    Ayrışım yeni bir ölçek uydurmaz; projenin kendi ölçeğinde kapanır.
    Bu bozulursa ayrışımın sayıları başka bir şeyin sayıları olur.
    """
    tahminler, kodlar = _kesit()
    a = brier_ayrisimi(tahminler, kodlar)
    dogrudan = sum(brier(p, k) for p, k in zip(tahminler, kodlar)) / len(kodlar)
    assert a["toplam"]["brier"] == pytest.approx(dogrudan, abs=1e-12)


def test_duzgun_tahminci_kapali_form():
    """1/3 veren tahminci: REL = RES = 0, toplam Brier tam olarak 0,667.

    Tek bir olasılık değeri var, dolayısıyla tek bir dolu bant var:
    o bantta `ō_k = ō_s` (çözünürlük sıfır) ve `p̄_k = 1/3`. Beklenti
    koddan değil aritmetikten geliyor.
    """
    _, kodlar = _kesit()
    esit = {s: 1.0 / len(SEMBOLLER) for s in SEMBOLLER}
    a = brier_ayrisimi([dict(esit) for _ in kodlar], kodlar)

    for s in SEMBOLLER:
        blok = a["semboller"][s]
        assert blok["cozunurluk"] == pytest.approx(0.0, abs=1e-12)
        assert blok["bant_ici"] == pytest.approx(0.0, abs=1e-12)
        taban = blok["taban_oran"]
        assert blok["guvenilirlik"] == pytest.approx((1 / 3 - taban) ** 2, abs=1e-12)
        assert blok["belirsizlik"] == pytest.approx(taban * (1 - taban), abs=1e-12)

    assert a["toplam"]["brier"] == pytest.approx(BRIER_ESIT, abs=1e-3)


def test_belirsizlik_taban_oranlardan_gelir():
    """`Σ UNC_s` sınıf dengesizliğini taşımalı — havuzlanmış ölçekte taşımazdı.

    Havuzlanmış (üç sembol tek torbada) ayrışımda `ō` her zaman tam 1/3'tür,
    yani `UNC` sabit 2/3'e çakılır ve dağılım bilgisi düşer. Sembol başına
    ayrışımda düşmez; bu test o farkı kilitliyor.
    """
    _, kodlar = _kesit()
    esit = {s: 1.0 / len(SEMBOLLER) for s in SEMBOLLER}
    a = brier_ayrisimi([dict(esit) for _ in kodlar], kodlar)

    beklenen = 0.0
    for s in SEMBOLLER:
        taban = kodlar.count(s) / len(kodlar)
        beklenen += taban * (1 - taban)
    assert a["toplam"]["belirsizlik"] == pytest.approx(beklenen, abs=1e-12)
    # Dengesiz dağılımda havuzlanmış sabitin (2/3) ALTINDA kalmalı.
    assert a["toplam"]["belirsizlik"] < BRIER_ESIT


def test_taban_oranlar_bire_toplar():
    tahminler, kodlar = _kesit()
    a = brier_ayrisimi(tahminler, kodlar)
    toplam = sum(a["semboller"][s]["taban_oran"] for s in SEMBOLLER)
    assert toplam == pytest.approx(1.0, abs=1e-12)


def test_kalibre_tahmincide_cozunurluk_guvenilirligi_asar():
    """Sonucu kendi olasılığından üretilen kesitte yön bilinir.

    Kalibre bir tahminci için güvenilirlik borcu küçüktür ve çözünürlük
    belirgindir. Bu test ayrışımın *işaretini* tutar: terimler karışsaydı
    (REL ↔ RES) özdeşlik yine kapanırdı ama okuma tersine dönerdi.
    """
    tahminler, kodlar = _kesit()
    a = brier_ayrisimi(tahminler, kodlar)
    assert a["toplam"]["cozunurluk"] > a["toplam"]["guvenilirlik"]
    for s in SEMBOLLER:
        assert a["semboller"][s]["guvenilirlik"] >= 0.0
        assert a["semboller"][s]["cozunurluk"] >= 0.0
        assert a["semboller"][s]["belirsizlik"] >= 0.0


def test_ayrisim_bos_girdiyle_patlamaz():
    a = brier_ayrisimi([], [])
    assert a["n"] == 0
    assert a["toplam"]["brier"] == 0.0
    assert set(a["semboller"]) == set(SEMBOLLER)


def test_ayrisim_tek_bantla_da_kapanir():
    """Tek bant = en kaba bölme; özdeşlik yine tam kapanmalı.

    Bu, bant sayısının özdeşliği değil yalnızca `bant_ici`nin büyüklüğünü
    değiştirdiğini kanıtlar — ayrışımın doğruluğu bant seçimine bağlı değil.
    """
    tahminler, kodlar = _kesit()
    a = brier_ayrisimi(tahminler, kodlar, bantlar=((0.0, 1.01),))
    for s in SEMBOLLER:
        blok = a["semboller"][s]
        assert blok["artik"] == pytest.approx(0.0, abs=1e-12)
        # Tek bantta çözünürlük tanım gereği sıfırdır: kova ortalaması = taban.
        assert blok["cozunurluk"] == pytest.approx(0.0, abs=1e-12)


def test_bant_sayisi_artinca_bant_ici_kuculur():
    """İnce bantlama artığı küçültür — ayrışımın okunabilirliği buna bağlı."""
    tahminler, kodlar = _kesit()
    kaba = brier_ayrisimi(tahminler, kodlar, bantlar=((0.0, 1.01),))
    ince = brier_ayrisimi(tahminler, kodlar)
    assert abs(ince["toplam"]["bant_ici"]) < abs(kaba["toplam"]["bant_ici"])


def test_varsayilan_bantlar_araligi_kapsar():
    """Bantlar [0, 1] aralığını boşluksuz örtmeli; boşluk sessiz kayıp olurdu."""
    assert OLASILIK_BANTLARI[0][0] == 0.0
    assert OLASILIK_BANTLARI[-1][1] > 1.0
    for (_, ust), (alt, _) in pairwise(OLASILIK_BANTLARI):
        assert ust == alt


def test_kalibrasyon_bantlari_ayni_kaynaktan():
    """`kalibrasyon.BANTLAR` ile ayrışımın bantları **aynı nesne** olmalı."""
    from spor_toto.kalibrasyon import BANTLAR

    assert BANTLAR is OLASILIK_BANTLARI


# ─── karışıklık matrisi ───────────────────────────────────────────────────

def test_karisiklik_satir_toplamlari_gercek_dagilim():
    tahminler, kodlar = _kesit()
    k = karisiklik_matrisi(tahminler, kodlar)
    for s in SEMBOLLER:
        assert sum(k["matris"][s].values()) == kodlar.count(s)
    toplam = sum(sum(satir.values()) for satir in k["matris"].values())
    assert toplam == len(kodlar)


def test_karisiklik_isabeti_kosegenden_gelir():
    tahminler, kodlar = _kesit()
    k = karisiklik_matrisi(tahminler, kodlar)
    kosegen = sum(k["matris"][s][s] for s in SEMBOLLER)
    assert k["isabet"] == pytest.approx(kosegen / len(kodlar))


def test_karisiklik_kusursuz_tahminci():
    """Gerçeğe 1 veren tahminci: her duyarlılık ve kesinlik 1."""
    _, kodlar = _kesit()
    tahminler = [{s: (1.0 if s == k else 0.0) for s in SEMBOLLER} for k in kodlar]
    k = karisiklik_matrisi(tahminler, kodlar)
    assert k["isabet"] == pytest.approx(1.0)
    assert k["dengeli_isabet"] == pytest.approx(1.0)
    for s in SEMBOLLER:
        assert k["duyarlilik"][s] == pytest.approx(1.0)
        assert k["kesinlik"][s] == pytest.approx(1.0)


def test_karisiklik_esitlikte_kupon_duzeni_kazanir():
    """Üç sembol eşitken seçim `SEMBOLLER` sırasının ilki olmalı — deterministik."""
    esit = dict.fromkeys(SEMBOLLER, 1 / 3)
    k = karisiklik_matrisi([dict(esit)], [SEMBOLLER[0]])
    assert k["matris"][SEMBOLLER[0]][SEMBOLLER[0]] == 1


def test_karisiklik_dengeli_isabet_cogunluga_sismez():
    """Hep favoriyi seçen tahminci: ham isabet yüksek, dengeli isabet 1/3.

    Sınıflar dengesiz olduğu için ham isabet çoğunluğu söylemekle şişer;
    dengeli isabet şişmez ve beraberliğin görülmediğini açık eder.
    """
    _, kodlar = _kesit()
    hep_bir = {SEMBOLLER[0]: 0.9, SEMBOLLER[1]: 0.05, SEMBOLLER[2]: 0.05}
    k = karisiklik_matrisi([dict(hep_bir) for _ in kodlar], kodlar)
    assert k["duyarlilik"][SEMBOLLER[0]] == pytest.approx(1.0)
    assert k["duyarlilik"][SEMBOLLER[1]] == pytest.approx(0.0)
    assert k["dengeli_isabet"] == pytest.approx(1 / 3, abs=1e-12)
    assert k["isabet"] > k["dengeli_isabet"]


def test_karisiklik_bos_girdiyle_patlamaz():
    k = karisiklik_matrisi([], [])
    assert k["n"] == 0
    assert k["isabet"] == 0.0


# ─── mevcut yüzeyin bekçileri ─────────────────────────────────────────────

def test_wilson_araligi_sinirlarda_kalir():
    for basari, n in ((0, 30), (30, 30), (1, 1), (0, 0)):
        alt, ust = wilson(basari, n)
        assert 0.0 <= alt <= ust <= 1.0


# ─── hafta içi sıralama ───────────────────────────────────────────────────

def test_siralama_kusursuz_tahmincide_ndcg_bir():
    """Her maçı bilen tahminci: bütün ilgililer listede zaten, NDCG = 1."""
    _, kodlar = _kesit(n=15)
    tahminler = [{s: (0.9 if s == k else 0.05) for s in SEMBOLLER} for k in kodlar]
    o = siralama_olculeri(tahminler, kodlar)
    assert o["ndcg"] == pytest.approx(1.0)
    assert o["taban_isabet"] == pytest.approx(1.0)
    for blok in o["isabet_k"].values():
        assert blok["dogru"] == blok["n"]


def test_siralama_isabetsiz_haftada_ndcg_tanimsiz():
    """Hiç isabet yoksa ideal kazanç sıfırdır ve oran tanımsız — None döner.

    Sıfır dönmek yanlış olurdu: "en kötü sıralama" ile "sıralanacak bir şey
    yok" aynı şey değildir ve ortalamaya sıfır olarak girerse ortalama
    aşağı çekilir.
    """
    kodlar = ["1"] * 10
    tahminler = [{"1": 0.1, "0": 0.6, "2": 0.3} for _ in kodlar]
    o = siralama_olculeri(tahminler, kodlar)
    assert o["ndcg"] is None
    assert o["taban_isabet"] == 0.0


def test_siralama_guveni_dogru_yerde_odullendirir():
    """İsabetli maça YÜKSEK güven veren, düşük güven verenden iyi olmalı.

    İki tahminci aynı isabeti verir (aynı argmax'lar) ama biri isabetlilere
    yüksek güven yazar. Brier ikisini ayırt edebilir ya da edemez; NDCG'nin
    ayırt etmesi ZORUNLUDUR — ölçtüğü şey tam olarak budur.
    """
    # AYNI olasiliklar; dordunde de argmax "1", guven azalan sirada.
    tahminler = [
        {"1": 0.80, "0": 0.10, "2": 0.10},
        {"1": 0.70, "0": 0.20, "2": 0.10},
        {"1": 0.40, "0": 0.35, "2": 0.25},
        {"1": 0.38, "0": 0.37, "2": 0.25},
    ]
    # Yalnizca SONUCLAR farkli: iyi'de emin oldugu maclar tutuyor,
    # kotu'de tam tersi. Taban isabet ikisinde de 2/4.
    iyi = ["1", "1", "0", "0"]
    kotu = ["0", "0", "1", "1"]

    a = siralama_olculeri(tahminler, iyi)
    b = siralama_olculeri(tahminler, kotu)
    assert a["taban_isabet"] == pytest.approx(b["taban_isabet"])
    assert a["ndcg"] == pytest.approx(1.0)
    assert a["ndcg"] > b["ndcg"]
    # Ve en emin macin isabeti dogrudan ayrisiyor.
    assert a["isabet_k"][1]["dogru"] == 1
    assert b["isabet_k"][1]["dogru"] == 0


def test_siralama_en_emin_mac_ilk_sirada():
    """`isabet_k[1]` en yüksek güvenli maçın isabetini okumalı, ilk maçınkini değil."""
    kodlar = ["2", "1"]
    tahminler = [
        {"1": 0.50, "0": 0.30, "2": 0.20},   # argmax "1", yanlis, guven 0.50
        {"1": 0.90, "0": 0.05, "2": 0.05},   # argmax "1", DOGRU, guven 0.90
    ]
    o = siralama_olculeri(tahminler, kodlar)
    assert o["isabet_k"][1] == {"dogru": 1, "n": 1}


def test_siralama_k_mac_sayisini_asamaz():
    _, kodlar = _kesit(n=3)
    tahminler = [dict.fromkeys(SEMBOLLER, 1 / 3) for _ in kodlar]
    o = siralama_olculeri(tahminler, kodlar, k_listesi=(1, 5, 50))
    for k, blok in o["isabet_k"].items():
        assert blok["n"] == min(k, 3)


def test_siralama_bos_girdiyle_patlamaz():
    o = siralama_olculeri([], [])
    assert o["n"] == 0 and o["ndcg"] is None and o["isabet_k"] == {}


def test_siralama_bilgisiz_tahmincide_taban_uzerinde_degil():
    """Her maça aynı olasılığı veren tahmincinin sıralaması bilgi taşımaz.

    `max(p)` sabit olduğu için sıra girdinin kendi sırasıdır; `isabet_1`
    tabandan sistematik olarak yüksek çıkmamalıdır. Çıkarsa ölçü sıralamayı
    değil girdi sırasını ödüllendiriyordur.
    """
    _, kodlar = _kesit(n=600)
    esit = [dict.fromkeys(SEMBOLLER, 1 / 3) for _ in kodlar]
    o = siralama_olculeri(esit, kodlar, k_listesi=(200,))
    blok = o["isabet_k"][200]
    oran = blok["dogru"] / blok["n"]
    assert abs(oran - o["taban_isabet"]) < 0.08
