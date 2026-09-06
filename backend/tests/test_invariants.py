"""
Rastgele uretilmis kuponlar uzerinde degismez (invariant) testleri.

Buradaki testler tek tek senaryolari degil, HER kupon icin gecerli olmasi
gereken kurallari dogrular. Amac, elle dusunulmemis girdi bicimlerinde de
hata cikmamasi.
"""

import math
import random
from itertools import product

import pytest

from spor_toto.core import (
    Encoder,
    olasilik_raporu,
    parse_picks,
    parse_probs,
    row_cost,
    rows_to_points,
)
from spor_toto.duz import kolonlar as duz_kolonlar
from spor_toto.duz import tek_satir
from spor_toto.report import (
    dagilim_satirlari,
    kolon_metni,
    olasilik_satirlari,
    satir_metni,
    yazdir_ve_kaydet,
)

SEMBOL_KUMELERI = [
    ["1"], ["0"], ["2"],
    ["1", "0"], ["1", "2"], ["0", "2"],
    ["1", "0", "2"],
]


def rastgele_kupon(rng: random.Random, en_az_cifte: int = 0) -> list:
    """15 maclik rastgele bir kupon uretir."""
    while True:
        kupon = [list(rng.choice(SEMBOL_KUMELERI)) for _ in range(15)]
        cifte = sum(1 for s in kupon if len(s) == 2)
        if cifte >= en_az_cifte:
            # Uzayin makul kalmasi icin ust sinir koy
            if math.prod(len(s) for s in kupon) <= 200_000:
                return kupon


from tests.conftest import kume_tamami_oynaniyor  # tek kaynak

# ------------------------------------------------------------
# Duz (tam sistem) degismezleri
#
# **Bu bolum eskiden kaplamayi olcuyordu** ve dokuz test tasiyordu: fix16'nin
# her zaman 16 satir vermesi, varyantlarin bedeli degistirmemesi, 7 cifteden
# azin reddedilmesi, blok motorunun fix16'dan pahali olmamasi, `distance_layers`
# katmanlarinin bosluksuzlugu, `dogrula_kaplama` ile mesafenin tutarliligi,
# `ball`in `hamming <= 1` ile ayni kumeyi vermesi, ve cozumun belirlenimciligi.
# Hepsi ARAMA ozellikleriydi; kaplama sokuldu (`docs/DUZ_SISTEME_GECIS.md`) ve
# arama diye bir sey kalmadi.
#
# Duzde korunacak degismez daha az ama daha KESIN: kolonlar secim kumesinin ta
# kendisi, bedel carpimin ta kendisi, satir tek. Ozelligi FORMULE degil
# sayarak sinariz — formulun kendisi test edilen sey.
# ------------------------------------------------------------

@pytest.mark.parametrize("tohum", range(40))
def test_duz_kolonlar_kumenin_TAMAMI(tohum):
    rng = random.Random(tohum)
    kupon = rastgele_kupon(rng)
    enc = Encoder(kupon)
    cols = duz_kolonlar(enc)
    sizes = enc.alphabet_sizes

    # 1) Kume eksiksiz ve fazlasiz oynaniyor (sayarak, formule guvenmeden)
    assert kume_tamami_oynaniyor(cols, sizes), kupon
    assert set(cols) == set(product(*[range(k) for k in sizes]))

    # 2) Bedel = 2^cifte * 3^uclu
    cifte = sum(1 for s in kupon if len(s) == 2)
    uclu = sum(1 for s in kupon if len(s) == 3)
    assert len(cols) == 2 ** cifte * 3 ** uclu == enc.space_size()

    # 3) Kolonlar tekil ve uzay icinde
    assert len(set(cols)) == len(cols)
    for c in cols:
        assert len(c) == len(sizes)
        assert all(0 <= v < k for v, k in zip(c, sizes))


@pytest.mark.parametrize("tohum", range(25))
def test_tek_satir_kayipsiz(tohum):
    """Kupon TEK satira siger ve o satirin acilimi kolonlarin ta kendisidir."""
    rng = random.Random(2000 + tohum)
    enc = Encoder(rastgele_kupon(rng))
    cols = duz_kolonlar(enc)
    satir = tek_satir(enc)
    assert row_cost(satir) == len(cols)
    assert set(rows_to_points([satir])) == set(cols)


@pytest.mark.parametrize("tohum", range(20))
def test_bir_kacak_en_iyi_kolonu_TAM_BIR_kademe_dusurur(tohum):
    """Duzun kurucu esitligi: en iyi kolon `15 - k`.

    Kaplamada bu bir ALT SINIRDI (`>= 14 - k`) cunku kumenin bir dilimi
    oynaniyordu. Duzde esitliktir ve bu test onu kaba kuvvetle sinar:
    kolonlar tek tek gezilir, en iyisi sayilir.
    """
    rng = random.Random(3000 + tohum)
    kupon = rastgele_kupon(rng)
    enc = Encoder(kupon)
    cols = duz_kolonlar(enc)
    # Gercek sonucu kupondan uret, sonra k tanesini kume DISINA it.
    gercek = [rng.choice(s) for s in kupon]
    kacak_yerleri = [i for i, s in enumerate(kupon) if len(s) < 3]
    rng.shuffle(kacak_yerleri)
    k = min(rng.randint(0, 3), len(kacak_yerleri))
    for i in kacak_yerleri[:k]:
        gercek[i] = next(s for s in ("1", "0", "2") if s not in kupon[i])
    en_iyi = max(sum(1 for a, b in zip(enc.decode_full(c), gercek) if a == b)
                 for c in cols)
    assert en_iyi == 15 - k, (kupon, gercek, k)


@pytest.mark.parametrize("tohum", range(10))
def test_ayni_girdi_ayni_cikti(tohum):
    rng = random.Random(8000 + tohum)
    kupon = rastgele_kupon(rng)
    a = duz_kolonlar(Encoder(kupon))
    b = duz_kolonlar(Encoder(kupon))
    assert a == b
    assert tek_satir(Encoder(kupon)) == tek_satir(Encoder(kupon))


# ------------------------------------------------------------
# Olasilik degismezleri
# ------------------------------------------------------------

@pytest.mark.parametrize("tohum", range(20))
def test_olasilik_degismezleri(tohum):
    rng = random.Random(9000 + tohum)
    kupon = rastgele_kupon(rng, en_az_cifte=7)
    enc = Encoder(kupon)
    cols = duz_kolonlar(enc)
    probs = [{s: rng.random() + 0.01 for s in ("1", "0", "2")} for _ in range(15)]
    for p in probs:
        t = sum(p.values())
        for k in p:
            p[k] /= t
    rap = olasilik_raporu(enc, cols, probs)
    assert 0.0 <= rap.p_15 <= 1.0
    assert 0.0 <= rap.p_kume_ici <= 1.0
    assert 0.0 <= rap.p_14 <= 1.0
    # **Duzde bu esitlik guclendi.** Kaplamada `p_15 + p_14 == p_kume_ici`
    # idi cunku kumenin bir dilimi oynaniyor ve kalan olasilik 14'e dusuyordu.
    # Duzde kume ICINDE kalmak DOGRUDAN 15 demektir, yani `p_14` kume ici
    # payindan gelmez: `p_15` kume-ici olasiliginin kendisidir.
    assert rap.p_15 == pytest.approx(rap.p_kume_ici, rel=1e-9)
    # En olasi TEK kolon kume-ici olasiliktan buyuk olamaz. Duzde en olasi
    # nokta kolonlarin ICINDEDIR (hepsi oynaniyor), yani bu sinir gevsektir
    # ve bilerek oyle: tutmasi gereken sey siralamanin bozulmamasi.
    assert rap.p_tek_kolon_15 <= rap.p_kume_ici + 1e-12


# ------------------------------------------------------------
# Raporlama
# ------------------------------------------------------------

def test_yazdir_ve_kaydet_ozeti(tmp_path, capsys):
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols = duz_kolonlar(enc)
    hedef = tmp_path / "c.txt"
    ozet = yazdir_ve_kaydet(enc, cols, "test", str(hedef), ["not"], tam_liste=False)
    # Duzde kupon isaretlerin kendisi: tek satir, bedel = secim uzayi.
    # `en_kotu` ve `acik` kaplama olculeriydi ve tanim geregi sifir.
    assert ozet["satir"] == 1
    assert ozet["bedel"] == enc.space_size()
    assert ozet["en_kotu"] == 0
    assert ozet["acik"] == 0
    assert hedef.exists()
    capsys.readouterr()


def test_yazdir_ve_kaydet_BOZUK_satiri_yakalar(monkeypatch, capsys):
    """Basilan satir oynanan kolonlari tutmuyorsa rapor sessizce gecmemeli.

    Kaplamada bu bekci `merge_rows`un (bir ARAMA) kayipsizligini tutuyordu.
    Duzde satir kapali formda uretiliyor, yani sinanan sey arama degil
    **tutarlilik**: eksik ya da fazla basilmis bir kupon, sessizce yanlis
    kupondur ve ikisi de ayni derecede pahalidir.
    """
    import spor_toto.report as rp
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols = duz_kolonlar(enc)
    # Tek noktalik "satir": bedeli 1, oysa kolon sayisi cok daha buyuk.
    monkeypatch.setattr(rp, "tek_satir",
                        lambda e: tuple(frozenset([v]) for v in cols[0]))
    with pytest.raises(AssertionError):
        rp.yazdir_ve_kaydet(enc, cols, "test", None, tam_liste=False)
    capsys.readouterr()


def test_rapor_metin_yardimcilari():
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols = duz_kolonlar(enc)
    m = satir_metni(enc, tek_satir(enc))
    assert len(m.split()) == 15
    assert "01" not in m.replace(" ", ",")      # kupon duzeni korunmali
    k = kolon_metni(enc, cols[0])
    assert len(k.split()) == 15
    satirlar = dagilim_satirlari(enc, cols)
    assert any("KUMENIN TAMAMI OYNANIYOR" in s for s in satirlar)


def test_dagilim_satirlari_eksik_kume_UYARIR():
    """Kolonlar kümenin tamamı değilse rapor bunu **söylemeli**.

    Kaplama döneminde bu test "14-GARANTI YOK" uyarısını arıyordu: tek bir
    kolon açık nokta bırakıyordu. Düzde kolonlar tanım gereği kümenin
    tamamıdır, yani bu durum bir HATA belirtisidir — ve raporun sessiz
    kalmaması, testin koruduğu şeyin ta kendisi.
    """
    enc = Encoder(parse_picks("10,10,10,10,10,1,1,1,1,1,1,1,1,1,1"))
    satirlar = dagilim_satirlari(enc, [(0, 0, 0, 0, 0)])
    assert any("kume eksik oynaniyor" in s for s in satirlar)


def test_olasilik_satirlari_bicimi():
    enc = Encoder(parse_picks("1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"))
    cols = duz_kolonlar(enc)
    probs = parse_probs(";".join(["1:1,0:1,2:1"] * 15), enc.selections)
    satirlar = olasilik_satirlari(olasilik_raporu(enc, cols, probs))
    assert any("kar/beklenen-deger hesabi degildir" in s for s in satirlar)


# ─── bağımsızlık varsayımı ────────────────────────────────────────────────────

def test_bagimsizlik_varsayimi_hafta_duzeyinde_tutuyor():
    """`P(≥12)`, `p_kume_ici`, Poisson-binom — hepsi 15 maçın bağımsızlığına
    dayanıyor. Bu bekçi o varsayımın **kırılmadığını** tutar.

    **İstatistiği bir kez yanlıştı ve düzeltildi.** Önce
    `Var_haftalar(K) / E[V]` hesaplanıyordu; kalibre bir tahmincide
    `Var(K) = E[V] + Var(M)` olduğu için o oran, hafta zorluğunun haftadan
    haftaya değişmesini bağımlılık sanıyordu. Sabit 15 maçlık kupon
    haftalarında bu yalnızca yukarı yönlü bir yanlılıktı (yani eski yeşil
    sonuç ayakta kalır), ama değişken boyutlu korpus haftalarında aynı
    istatistik **36,09** veriyordu — doğrusu 0,98. Formül artık
    `kuyruk.olc`ten geliyor; iki gövde ayrışamaz.

    **Tek yönlüdür, ve bu bilinçli.** Ürünü ilgilendiren yön yalnızca
    yukarıdır: fazla dağılım (`> 1`) hafta içi eş-hareket demektir ve
    `P(k≥12)`yi *iyimser* yapar. Az dağılım geri testi temkinli yapar, yani
    bir kusur değildir — ve 36 haftada dağılımın kendi örneklem aralığı
    zaten `[0,46, 1,00]`. İki yönlü bir sınır orada kendi gürültüsünü
    ölçerdi.

    Asıl ölçüm — güven aralığı, korpus kesiti ve `ρ`nun kuyruğa çevrilmesi —
    bu bekçide değil `spor_toto.kuyruk`tadır (§3.46).
    """
    from spor_toto.backtest import hafta_girdileri
    from spor_toto.kuyruk import hafta_kayitlari, olc

    haftalar = [g for g in hafta_girdileri(None) if g["usable"]]
    if len(haftalar) < 20:
        pytest.skip("bagimsizlik sinamasi icin en az 20 tam hafta gerekli")

    s = olc(hafta_kayitlari(haftalar))
    assert s["dagilim"] < 1.6, (
        f"haftalik favori isabetinin dagilimi {s['dagilim']:.2f} — bagimsizlik "
        f"varsayimi kirilmis olabilir; P(>=12) ve p_kume_ici bu varsayima "
        f"dayaniyor (rho={s['rho']:+.5f}, yanlilik={s['yanlilik']:+.4f}). "
        f"Olcum icin: python -m spor_toto.kuyruk")
