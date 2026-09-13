"""Operasyonun denetimi — **oynanan** kuponu puanlamak.

Bu modülün iddiası bir plan değil bir **denetim**: insanın girdiği kupon
kümesi plandan sapabilir ve saptığında `coklu.p_onbes` yanlış cevap verir.
Buradaki bekçilerin çoğu tam olarak o yalanı kovalıyor.

`test_kopya_NAIF_toplami_SISIRIYOR` süs değil, bu modülün var olma
sebebidir: bir kupon iki kez girildiğinde ayrıklık bozulur, `Σ p_j` aynı
kolonu iki kez sayar ve sonuç **iyimser** yöne kayar. Yani denetim en çok
ihtiyaç duyulduğu anda sessizce güven verir.
"""

from itertools import pairwise

import numpy as np
import pytest

from spor_toto.coklu import MAC_SAYISI, Kupon, coklu_plan, p_onbes
from spor_toto.core import SEMBOLLER
from spor_toto.operasyon import (
    SLIP_TURLERI,
    ayrik_mi,
    birlesim_p_onbes,
    hedef_duyarliligi,
    kritik_hata_orani,
    kupon_olasiliklari,
    slip_ozeti,
    slipler,
    yogunlasma,
)

BUTCE = 19_683
TAVAN = 27


def _probs(tohum: int = 0) -> list[dict[str, float]]:
    rng = np.random.default_rng(tohum)
    out = []
    for _ in range(MAC_SAYISI):
        v = rng.dirichlet([6.0, 3.0, 2.5])
        out.append({s: float(v[j]) for j, s in enumerate(SEMBOLLER)})
    return out


def _plan(tohum: int = 0, tavan: int = TAVAN):
    probs = _probs(tohum)
    return probs, coklu_plan(probs, BUTCE, tavan)


# ─── Birleşim gövdesi: ayrıklık varsayılmıyor ────────────────────────────

def test_birlesim_AYRIKKEN_p_onbes_ile_ayni():
    """Plan ayrıktır; orada iki gövde aynı sayıyı vermek ZORUNDA."""
    for tohum in range(5):
        probs, plan = _plan(tohum)
        assert ayrik_mi(plan.kuponlar)
        assert birlesim_p_onbes(probs, plan.kuponlar) == pytest.approx(
            p_onbes(probs, plan.kuponlar), rel=1e-12)


def test_kopya_NAIF_toplami_SISIRIYOR():
    """Bir kupon iki kez girilince `Σ p_j` fazla sayar, birleşim saymaz.

    Bu modülün var olma sebebi. Naif toplam yalnızca yanlış değil, **tek
    yöne** yanlış: girilen kupon kümesini olduğundan iyi gösteriyor.
    """
    for tohum in range(5):
        probs, plan = _plan(tohum)
        bozuk = list(plan.kuponlar)
        bozuk[0] = bozuk[5]           # 0 girilmedi, 5 iki kez girildi
        assert not ayrik_mi(bozuk)
        gercek = birlesim_p_onbes(probs, bozuk)
        naif = p_onbes(probs, bozuk)
        assert naif > gercek
        # Ve gerçek kayıp tam olarak girilmeyen kupondur.
        assert gercek == pytest.approx(
            birlesim_p_onbes(probs, plan.kuponlar)
            - next(s.p_kayip for s in slipler(probs, plan.kuponlar)
                   if s.tur == "kopya" and s.kupon == 0), rel=1e-12)


def test_birlesim_KOPYA_EKLEMEK_degistirmez():
    """Var olan bir kuponu bir kez daha eklemek birleşimi büyütmez."""
    probs, plan = _plan(3)
    taban = birlesim_p_onbes(probs, plan.kuponlar)
    sisik = [*plan.kuponlar, plan.kuponlar[2], plan.kuponlar[7]]
    assert birlesim_p_onbes(probs, sisik) == pytest.approx(taban, rel=1e-12)
    assert p_onbes(probs, sisik) > taban        # naif gövde şişiyor


# ─── Kapalı form ↔ kesin sayım ───────────────────────────────────────────

def test_slip_kaybi_KESIN_sayimla_ayni():
    """Kapalı form, örtüşme dâhil, kolon sayımıyla birebir aynı olmalı.

    İki gövde ayrışırsa kapalı formdaki içerme–dışarma terimi yanlıştır ve
    bütün §3.74 tablosu onun üstünde duruyor.
    """
    rng = np.random.default_rng(4)
    for tohum in range(3):
        probs, plan = _plan(tohum)
        kuponlar = list(plan.kuponlar)
        taban = birlesim_p_onbes(probs, kuponlar)
        konumlu = [s for s in slipler(probs, kuponlar) if s.konum is not None]
        for idx in rng.choice(len(konumlu), size=12, replace=False):
            s = konumlu[int(idx)]
            sec = [list(x) for x in kuponlar[s.kupon].secimler]
            sec[s.konum] = sorted(s.yeni)
            bozuk = list(kuponlar)
            bozuk[s.kupon] = Kupon(sec, 1)
            assert taban - birlesim_p_onbes(probs, bozuk) == pytest.approx(
                s.p_kayip, abs=1e-15, rel=1e-9)


def test_atlama_kaybi_KUPONUN_KENDISI():
    """Girilmeyen kuponun bedeli tam olarak kendi olasılığıdır."""
    probs, plan = _plan(1)
    kuponlar = list(plan.kuponlar)
    taban = birlesim_p_onbes(probs, kuponlar)
    for s in (x for x in slipler(probs, kuponlar) if x.tur == "atlama"):
        kalan = [k for j, k in enumerate(kuponlar) if j != s.kupon]
        assert taban - birlesim_p_onbes(probs, kalan) == pytest.approx(
            s.p_kayip, rel=1e-12)


def test_kopya_kaybi_atlama_kaybiyla_AYNI():
    """Okuma kuralı 2: kopyanın `P` kaybı atlamanınkiyle aynı olmalı.

    Kopyada kaybedilen de girilmeyen kupondur; ikinci kez girilen kutu
    kümede zaten vardır. Ayrışırlarsa gövdede hata vardır.
    """
    probs, plan = _plan(2)
    sl = slipler(probs, plan.kuponlar)
    atlama = {s.kupon: s.p_kayip for s in sl if s.tur == "atlama"}
    kopya = {s.kupon: s.p_kayip for s in sl if s.tur == "kopya"}
    assert atlama.keys() == kopya.keys()
    for j in atlama:
        assert atlama[j] == pytest.approx(kopya[j], rel=1e-15)


# ─── Modların yönü ───────────────────────────────────────────────────────

def test_fazla_isaret_P_YUKSELTIR_ama_BUTCE_asar():
    """Okuma kuralı 1: fazla işaret kapsamayı büyütür, bedeli PARADA.

    Kayıp negatif (yani `P` artmış) ve kolon farkı pozitif olmalı. İşaret
    ters dönerse ya kutu mantığı ya da örtüşme terimi bozulmuştur.
    """
    probs, plan = _plan(0)
    fazla = [s for s in slipler(probs, plan.kuponlar) if s.tur == "fazla"]
    assert fazla
    assert all(s.p_kayip <= 1e-15 for s in fazla)
    assert all(s.kolon_fark > 0 for s in fazla)


def test_eksik_isaret_P_DUSURUR_ve_UCUZLAR():
    """Unutulan işaret kapsamayı daraltır; kutu küçüldüğü için örtüşme yok."""
    probs, plan = _plan(0)
    eksik = [s for s in slipler(probs, plan.kuponlar) if s.tur == "eksik"]
    assert eksik
    assert all(s.p_kayip > 0 for s in eksik)
    assert all(s.kolon_fark < 0 for s in eksik)


def test_takas_BEDELI_degistirmez():
    """Yanlış kutu işaretlemek kolon sayısını oynatmaz — yalnızca yeri."""
    probs, plan = _plan(0)
    takas = [s for s in slipler(probs, plan.kuponlar) if s.tur == "takas"]
    assert takas
    assert all(s.kolon_fark == 0 for s in takas)
    assert all(len(s.eski) == len(s.yeni) for s in takas)


def test_slip_ailesi_TEK_DARBE():
    """Her slip seçim kümesini en çok bir sembol oynatır.

    "Tek hata" sayımı bunun üstünde duruyor: iki sembolü birden oynatan bir
    bozulma ailede olsaydı `r` (kupon başına hata oranı) başka bir şeyi
    sayardı ve §3.74'ün eşiği anlamını yitirirdi.
    """
    probs, plan = _plan(0)
    for s in (x for x in slipler(probs, plan.kuponlar) if x.konum is not None):
        assert len(set(s.eski) ^ set(s.yeni)) <= 2
        assert s.tur in SLIP_TURLERI


def test_slip_ozeti_BUTUN_turleri_kapsiyor():
    """Özet, ailedeki her türü sayıyor — biri sessizce düşerse ortalama yalan."""
    probs, plan = _plan(0)
    ozet = slip_ozeti(probs, plan.kuponlar)
    assert set(ozet) == set(SLIP_TURLERI)
    assert all(o.sayi > 0 for o in ozet.values())
    assert ozet["atlama"].sayi == plan.kupon_sayisi


# ─── Hedef çevirisi ──────────────────────────────────────────────────────

def test_hedef_duyarliligi_ARALIKTA():
    """Türev `Π(1−p)` ile 1 arasındadır; dışına çıkarsa çeviri bozuk."""
    for p in ([0.1] * 13, [0.02, 0.37] * 6, [0.0] * 5):
        d = hedef_duyarliligi(p)
        assert 0.0 <= d <= 1.0
    assert hedef_duyarliligi([]) == 0.0
    assert hedef_duyarliligi([0.0] * 4) == pytest.approx(1.0)


def test_kritik_oran_PAYDA_SIFIRSA_esik_yok():
    """Fazladan giriş ya da slip bedeli yoksa eşik sonsuzdur, 0 değil."""
    assert kritik_hata_orani(0.018, 0.237, 13, 0, 0.001) == float("inf")
    assert kritik_hata_orani(0.018, 0.237, 13, 648, 0.0) == float("inf")


def test_kritik_oran_SLIP_PAHALILASINCA_dusuyor():
    """Slip ne kadar pahalıysa tahammül edilen hata oranı o kadar küçük."""
    onceki = float("inf")
    for bedel in (1e-4, 5e-4, 1e-3, 5e-3):
        r = kritik_hata_orani(0.018, 0.237, 13, 648, bedel)
        assert r < onceki
        onceki = r


@pytest.mark.slow
def test_GERCEK_haftada_kapali_form_KESIN():
    """Gerçek bir haftada, gerçek bütçede, kapalı form ↔ kesin sayım.

    Sentetik olasılıklar kutuları iyi huylu yapabilir; asıl sınav arşivdeki
    hafta, çünkü §3.74'ün sayıları oradan çıkıyor.
    """
    from scripts.coklu_kiyasi import hafta_probs
    from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar

    haftalar = tam_haftalar(ikramiye_tablolari())
    _, _, lst = haftalar[0]
    probs, _ = hafta_probs(lst)
    plan = coklu_plan(probs, 21_000, 81)
    kuponlar = list(plan.kuponlar)
    assert ayrik_mi(kuponlar)
    taban = birlesim_p_onbes(probs, kuponlar)
    assert taban == pytest.approx(p_onbes(probs, kuponlar), rel=1e-12)
    rng = np.random.default_rng(9)
    konumlu = [s for s in slipler(probs, kuponlar) if s.konum is not None]
    for idx in rng.choice(len(konumlu), size=10, replace=False):
        s = konumlu[int(idx)]
        sec = [list(x) for x in kuponlar[s.kupon].secimler]
        sec[s.konum] = sorted(s.yeni)
        bozuk = list(kuponlar)
        bozuk[s.kupon] = Kupon(sec, 1)
        assert taban - birlesim_p_onbes(probs, bozuk) == pytest.approx(
            s.p_kayip, abs=1e-15, rel=1e-9)


# ─── Yoğunlaşma: hangi kupon yanlış girilirse pahalı ─────────────────────

def test_yogunlasma_PAYLAR_tutarli():
    """En büyük pay düz payın altına düşemez ve yarıyı taşıyan küme `M`yi aşamaz."""
    for tohum in range(5):
        probs, plan = _plan(tohum)
        y = yogunlasma(probs, plan.kuponlar)
        assert y.kupon == plan.kupon_sayisi
        assert y.duz_pay == pytest.approx(1.0 / y.kupon)
        assert y.en_buyuk_pay >= y.duz_pay - 1e-15
        assert 1 <= y.yarisini_tasiyan <= y.kupon


def test_yogunlasma_EN_BUYUK_atlama_kaybiyla_ayni():
    """En büyük pay, en pahalı `atlama` slipinin ta kendisidir.

    İki gövde aynı şeyi iki yoldan söylüyor; ayrışırlarsa denetim sırası
    yanlış kuponları işaret eder.
    """
    probs, plan = _plan(1)
    y = yogunlasma(probs, plan.kuponlar)
    en_kotu = max(s.p_kayip for s in slipler(probs, plan.kuponlar)
                  if s.tur == "atlama")
    taban = birlesim_p_onbes(probs, plan.kuponlar)
    assert y.en_buyuk_pay == pytest.approx(en_kotu / taban, rel=1e-12)


def test_yogunlasma_BOS_kupon_kumesi():
    """Kupon yoksa sessizce bölme hatası değil, sıfırlı kayıt döner."""
    probs = _probs(0)
    y = yogunlasma(probs, [])
    assert y == (0, 0.0, 0, 0.0)


# ─── Denetim sırası: kaydın KENDİSİ okunabilir olmalı ────────────────────

def _sahte_hafta(tohum: int = 0) -> dict:
    probs = _probs(tohum)
    return {
        "meta": {"season": "2026/2027", "week": 9},
        "matches": [{"no": i + 1, "home": f"E{i}", "away": f"D{i}",
                     "probs": p} for i, p in enumerate(probs)],
    }


def test_kayit_kuponlari_OLASILIGA_GORE_azalan():
    """Donan kayıt en pahalı kupondan başlar — denetim sırası budur.

    Aramanın kendi çıktısı bu sırada DEĞİL (gerçek haftaların bir kısmında
    kuponlar karışık geliyor), yani sıralama kayıt kurulurken yapılıyor ve
    bu bekçi onun düşmediğini tutuyor. Düşerse §3.74'ün operasyon kuralı
    ("ilk kümeyi iki kez oku") yanlış kuponları işaret eder.
    """
    from scripts.coklu_kupon import plan_uret
    from spor_toto.coklu import Kupon

    for tohum in range(4):
        d = _sahte_hafta(tohum)
        c = plan_uret(d, BUTCE, TAVAN)
        assert len(c["kuponlar"]) == c["kupon_sayisi"]
        kuponlar = [Kupon([list(s) for s in k["picks"]], k["kolon"])
                    for k in c["kuponlar"]]
        p = kupon_olasiliklari([m["probs"] for m in d["matches"]], kuponlar)
        assert all(a >= b - 1e-15 for a, b in pairwise(p))


def test_kayit_DENETIM_kunyesi_dogru():
    """Kaydın `denetim` bloğu ölçümle aynı şeyi söylüyor."""
    from scripts.coklu_kupon import plan_uret
    from spor_toto.coklu import Kupon

    d = _sahte_hafta(0)
    c = plan_uret(d, BUTCE, TAVAN)
    probs = [m["probs"] for m in d["matches"]]
    kuponlar = [Kupon([list(s) for s in k["picks"]], k["kolon"])
                for k in c["kuponlar"]]
    y = yogunlasma(probs, kuponlar)
    assert c["denetim"]["sirali"] == "p_azalan"
    assert c["denetim"]["en_buyuk_pay"] == pytest.approx(y.en_buyuk_pay,
                                                         rel=1e-12)
    assert c["denetim"]["yarisini_tasiyan"] == y.yarisini_tasiyan
    # Yoğunlaşma DÜZ olamaz: eksen bileşimlerinin olasılıkları ayrışıyor.
    assert y.en_buyuk_pay > y.duz_pay


def test_DONMUS_kayitlar_azalan_sirada():
    """Depodaki donmuş `hafta_NN_coklu.json` kayıtları denetim sırasında.

    Bekçi kodu değil **artefaktı** sınıyor: girişi yapan kişi elinde o
    dosyayla oturuyor ve sıra orada bozuksa ölçüm kâğıt üstünde kalır.
    """
    import json
    from pathlib import Path

    from spor_toto.coklu import Kupon

    kok = Path(__file__).resolve().parent.parent / "data" / "super_toto"
    kayitlar = sorted(kok.glob("*/hafta_*_coklu.json"))
    assert kayitlar, "donmus coklu kupon kaydi bulunamadi"
    for yol in kayitlar:
        plan = json.loads(yol.read_text(encoding="utf-8"))["plan"]
        probs = [m["probs"] for m in plan["maclar"]]
        kuponlar = [Kupon([list(s) for s in k["picks"]], k["kolon"])
                    for k in plan["kuponlar"]]
        p = kupon_olasiliklari(probs, kuponlar)
        assert all(a >= b - 1e-15 for a, b in pairwise(p)), yol.name


def test_kopya_PARA_bedeli_atlamadan_farkli():
    """`kopya` ile `atlama` `P`de aynı, **parada** değil.

    Atlanan kuponun parası cepte kalır (`kolon_fark < 0`); kopyada para
    harcanır ve kupon bedelleri ayrıştığı için (§3.71) fark sıfır da
    değildir. Bu ayrım kaybolursa iki mod ayırt edilemez hâle gelir.
    """
    probs, plan = _plan(2)
    sl = slipler(probs, plan.kuponlar)
    atlama = {s.kupon: s.kolon_fark for s in sl if s.tur == "atlama"}
    kopya = {s.kupon: s.kolon_fark for s in sl if s.tur == "kopya"}
    assert all(v < 0 for v in atlama.values())
    assert all(v >= 0 for v in kopya.values())
    assert any(v > 0 for v in kopya.values())
