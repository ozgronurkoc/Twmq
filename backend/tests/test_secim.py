"""Hedefe göre işaret seçimi (`spor_toto.secim`).

Buradaki testler iki şeyi korur: **aritmetiği** (kaçak olasılığı, bedel,
hedef) ve **optimizasyonun gerçekten optimal olduğunu**. İkincisi kritik:
Pareto budaması "yaklaşık" olsaydı sessizce daha kötü kupon kurardı ve
hiçbir şey patlamazdı — o yüzden küçük vakalarda kaba kuvvetle
karşılaştırılıyor.
"""

from itertools import product

import pytest

from spor_toto.ortak import kacak_dagilimi
from spor_toto.secim import (
    VARSAYILAN_KACAK_ESIGI,
    bedel_hesapla,
    en_iyi_secim,
    hedef_olasiligi,
    kacak_olasiligi,
)

SEM = ("1", "0", "2")


def p(bir: float, sifir: float, iki: float) -> dict[str, float]:
    t = bir + sifir + iki
    return {"1": bir / t, "0": sifir / t, "2": iki / t}


def hafta(n: int = 15) -> list[dict[str, float]]:
    """Çeşitli şekilli 15 maç — hepsi aynı olsaydı seçim de sıkıcı olurdu."""
    sekiller = [
        (0.80, 0.12, 0.08), (0.45, 0.30, 0.25), (0.34, 0.33, 0.33),
        (0.55, 0.25, 0.20), (0.40, 0.35, 0.25), (0.70, 0.18, 0.12),
        (0.38, 0.32, 0.30), (0.60, 0.22, 0.18), (0.50, 0.28, 0.22),
        (0.33, 0.34, 0.33), (0.65, 0.20, 0.15), (0.42, 0.31, 0.27),
        (0.48, 0.29, 0.23), (0.75, 0.15, 0.10), (0.36, 0.33, 0.31),
    ]
    return [p(*sekiller[i % len(sekiller)]) for i in range(n)]


# ─── aritmetik ────────────────────────────────────────────────────────────

def test_uclu_asla_kacmaz():
    """Yapının tamamı bu olguya dayanıyor; kırılırsa optimizasyon çöker."""
    for m in hafta():
        assert kacak_olasiligi(m, 3) == pytest.approx(0.0, abs=1e-12)


def test_kacak_olasiligi_seviyeyle_azalir():
    for m in hafta():
        assert kacak_olasiligi(m, 1) >= kacak_olasiligi(m, 2)
        assert kacak_olasiligi(m, 2) >= kacak_olasiligi(m, 3)


def test_cifte_kacagi_en_dusuk_sembolun_olasiligidir():
    m = p(0.50, 0.30, 0.20)
    assert kacak_olasiligi(m, 2) == pytest.approx(0.20)


def test_bedel_SECIM_UZAYININ_kendisidir():
    """Düzde bedel = oynanacak kolon sayısı = işaret sayılarının çarpımı.

    Formüle değil **sayıma** karşı sınanıyor: kolonlar `itertools.product`
    ile tek tek üretilip sayılıyor. Formül ile sayım ayrışırsa bütçe kısıtı
    yalan söyler ve optimizasyon karşılayamayacağı planlar seçer.

    **Bu test eskiden `solve_fix16`ın ürettiği kolon sayısını sınıyordu**
    (`2^a·3^b/2⁷·16`); kaplama söküldü, bedel sekiz kat büyüdü ve "en az
    yedi çifte" varsayımı da testten kalktı — aşağıdaki şekillerin çoğu
    fix16'da hiç kurulamazdı.
    """
    for cift, uclu in ((0, 0), (1, 0), (0, 1), (3, 2), (7, 0), (0, 8)):
        banko = 15 - cift - uclu
        secimler = ([["1"]] * banko + [["1", "0"]] * cift
                    + [["1", "0", "2"]] * uclu)
        sayim = sum(1 for _ in product(*secimler))
        assert sayim == bedel_hesapla(cift, uclu), (cift, uclu)


def test_hedef_olasiligi_kacak_dagilimiyla_tutarli():
    maclar = hafta()
    secimler = [["1", "0"]] * 15
    q = [1 - sum(m[s] for s in sec) for m, sec in zip(maclar, secimler)]
    assert hedef_olasiligi(maclar, secimler) == pytest.approx(
        sum(kacak_dagilimi(q)[:VARSAYILAN_KACAK_ESIGI + 1]))


def test_hepsi_uclu_ise_hedef_kesindir():
    maclar = hafta()
    assert hedef_olasiligi(maclar, [list(SEM)] * 15) == pytest.approx(1.0)


# ─── optimizasyon ─────────────────────────────────────────────────────────

def _kaba_kuvvet(maclar, butce, esik=VARSAYILAN_KACAK_ESIGI):
    """Küçük vakada TÜM atamaları gezip en iyisini bulur — referans."""
    n = len(maclar)
    sirali = [sorted(m.items(), key=lambda kv: (-kv[1], SEM.index(kv[0])))
              for m in maclar]
    en = None
    for seviyeler in product((1, 2, 3), repeat=n):
        cift = sum(1 for s in seviyeler if s == 2)
        uclu = sum(1 for s in seviyeler if s == 3)
        c = bedel_hesapla(cift, uclu)
        if c > butce:
            continue
        secimler = [[s for s, _ in sirali[i][:seviyeler[i]]] for i in range(n)]
        deger = hedef_olasiligi(maclar, secimler, esik)
        if en is None or (deger, -c) > (en[0], -en[1]):
            en = (deger, c)
    return en


@pytest.mark.parametrize("butce", [2048, 4096, 8192, 16384])
def test_optimizasyon_gercekten_optimal(butce):
    """Pareto budaması KESİN olmalı — kaba kuvvetle birebir aynı değer.

    Budama yaklaşık olsaydı sessizce daha kötü kupon kurardı ve hiçbir yer
    patlamazdı; bu testin varlık sebebi tam olarak o sessizlik.
    """
    maclar = hafta(9)          # 3^9 = 19.683 atama — kaba kuvvet mümkün
    beklenen = _kaba_kuvvet(maclar, butce)
    bulunan = en_iyi_secim(maclar, butce)
    if beklenen is None:
        assert bulunan is None
        return
    assert bulunan is not None
    assert bulunan.p_hedef == pytest.approx(beklenen[0], rel=1e-12)
    assert bulunan.bedel == beklenen[1]


def test_optimizasyon_esik_kuralini_geciyor():
    """Asıl iddia: aynı bütçede eşik kuralından daha iyi hedef."""
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU, secim_uret

    maclar = hafta()
    eski = [secim_uret(m, VARSAYILAN_BANKO, VARSAYILAN_UCLU) for m in maclar]
    cift = sum(1 for s in eski if len(s) == 2)
    uclu = sum(1 for s in eski if len(s) == 3)
    butce = bedel_hesapla(cift, uclu)
    yeni = en_iyi_secim(maclar, butce)
    assert yeni is not None
    assert yeni.bedel <= butce
    assert yeni.p_hedef >= hedef_olasiligi(maclar, eski)


def test_butce_kisiti_asilmaz():
    maclar = hafta()
    for butce in (16, 64, 256, 1024, 4096):
        s = en_iyi_secim(maclar, butce)
        if s is None:
            continue
        assert s.bedel <= butce
        assert bedel_hesapla(s.cift, s.uclu) == s.bedel


def test_yedi_cifte_kisiti_ARTIK_YOK():
    """Kısıtın kalktığı **gösterilmeli**, yokluğu sessizce varsayılmamalı.

    Kaplama döneminde bu testin adı `test_yedi_cifte_kisiti_korunur`'du ve
    tersini sınıyordu: her planın en az yedi çifte taşıdığını. Kısıt
    Hamming(7,4) bloğunundu ve katmanla birlikte kalktı — ölçümde kuponun
    asıl kazandığı şey de buydu (`docs/DUZ_SISTEME_GECIS.md` §3).

    Küçük bütçelerde motor yedi çifteden az taşıyan planlar seçebilmeli;
    seçemiyorsa kısıt bir yerde hâlâ duruyor demektir.
    """
    maclar = hafta()
    az_ciftesi_olan = [en_iyi_secim(maclar, b) for b in (1, 4, 16, 64)]
    assert any(s is not None and s.cift < 7 for s in az_ciftesi_olan), (
        "hicbir kucuk butcede yedi ciftenin altina inilmedi — kisit duruyor mu?")
    # En uc hal: butun maclar tek. Kaplamada bu plan HIC kurulamazdi.
    hepsi_tek = en_iyi_secim(maclar, 1)
    assert hepsi_tek is not None
    assert (hepsi_tek.banko, hepsi_tek.cift, hepsi_tek.uclu) == (15, 0, 0)
    assert hepsi_tek.bedel == 1


def test_butce_buyudukce_hedef_kotulesmez():
    maclar = hafta()
    onceki = -1.0
    for butce in (16, 128, 1024, 8192, 65536):
        s = en_iyi_secim(maclar, butce)
        if s is None:
            continue
        assert s.p_hedef >= onceki - 1e-12
        onceki = s.p_hedef


def test_en_ucuz_plan_BIR_kolondur():
    """Düzde her bütçe bir plan bulur; en ucuzu 15 tek = 1 kolon.

    **Bu test eskiden tersini söylüyordu**: *"yedi çiftenin bedeli 16
    kolondur; altında kurulacak plan yok"* ve 8 kolonluk bütçede `None`
    bekliyordu. Düzde öyle bir taban yok.
    """
    for butce in (1, 2, 8, 15):
        s = en_iyi_secim(hafta(), butce)
        assert s is not None, f"butce {butce}: plan bulunmali"
        assert s.bedel <= butce


def test_gecersiz_butce_reddedilir():
    with pytest.raises(ValueError, match="pozitif"):
        en_iyi_secim(hafta(), 0)


def test_butce_ZORUNLU_dejenerelige_dusulmez():
    """Tavansız aramanın cevabı "hepsi üçlü"dür; motor onu sessizce vermez.

    Bütçe bir **harcama kararıdır** ve veriden türetilemez. `None` geçmek
    dejenere planı (3^15 = 14.348.907 kolon) sipariş etmekle aynı şeydir.
    """
    with pytest.raises(ValueError, match="zorunlu"):
        en_iyi_secim(hafta(), None)


def test_bos_hafta_none_doner():
    assert en_iyi_secim([], 1024) is None


def test_esik_buyurse_hedef_kotulesmez():
    """`P(k ≤ 3)` her zaman `P(k ≤ 2)`'den büyük ya da eşittir."""
    maclar = hafta()
    dar = en_iyi_secim(maclar, 4096, esik=2)
    genis = en_iyi_secim(maclar, 4096, esik=3)
    assert dar is not None and genis is not None
    assert genis.p_hedef >= dar.p_hedef


def test_secimler_en_olasi_sembollerden_kurulur():
    """Bir maçta `L` sembol işaretleniyorsa, o `L` en olasılıklı olanlardır.

    Aksi bir seçim aynı bedele daha düşük hedef alırdı; testin işi bunun
    kodda da böyle olduğunu çivilemek.
    """
    maclar = hafta()
    s = en_iyi_secim(maclar, 8192)
    assert s is not None
    for m, sec in zip(maclar, s.secimler):
        sirali = sorted(m, key=lambda k: (-m[k], SEM.index(k)))
        assert set(sec) == set(sirali[:len(sec)])


def test_bilinen_haftada_uclu_pahali_olduğunda_secilmez():
    """Bütçe darsa üçlü (×3) yerine çifte (×2) tercih edilmeli.

    16 kolona düzde dört çifte sığar (`2⁴ = 16`); beşincisi 32 eder. Üçlü
    ×3 çarptığı için aynı bütçede daha az maç açar ve bu maçlarda `p₃`
    (0,20) `p₂`'den (0,30) küçük olduğu için değmiyor.
    """
    maclar = [p(0.50, 0.30, 0.20)] * 15
    dar = en_iyi_secim(maclar, 16)
    assert dar is not None
    assert dar.uclu == 0
    assert dar.cift == 4
    assert dar.bedel == 16


def test_her_plan_OYNANABILIR():
    """Üretilen her plan bedeli kadar kolon eder — sayımla doğrulanır.

    **Bu test eskiden `solve_fix16`ın planı çözebildiğini sınıyordu**
    (`test_fix16_kurulamayan_plan_uretilmez`): kaplamada plan "kurulamaz"
    olabiliyordu ve bu gerçek bir risk kaynağıydı. Düzde öyle bir hâl yok —
    her şekil oynanabilir; geriye kalan tek iddia bedelin doğruluğudur ve
    o da formülle değil **sayımla** sınanır.
    """
    for butce in (1, 16, 48, 512, 6144, 49152):
        s = en_iyi_secim(hafta(), butce)
        assert s is not None, f"butce {butce}"
        sayim = sum(1 for _ in product(*[list(x) for x in s.secimler]))
        assert sayim == s.bedel <= butce, f"butce {butce}"


# ─── getiri_secim: kalabalığa göre E[TL] seçimi ───────────────────────────

def _oyn(n: int = 15):
    """Kalabalık favoriden SAPAN paylar — monoton olmayan kurgu."""
    out = []
    for i in range(n):
        if i % 3 == 0:
            out.append({"1": 0.20, "0": 0.30, "2": 0.50})
        else:
            out.append({"1": 0.60, "0": 0.25, "2": 0.15})
    return out


def _pr(n: int = 15):
    out = []
    for i in range(n):
        p1 = 0.30 + 0.035 * i
        p0 = (1 - p1) * 0.42
        out.append({"1": p1, "0": p0, "2": 1 - p1 - p0})
    return out


def test_getiri_secim_sekli_ve_bedeli_KORUR():
    """Şekil sabit: aynı kolon, aynı bütçe — ayar bedava olmalı."""
    from spor_toto.secim import getiri_secim, sistem_secimi

    a = sistem_secimi(_pr(), 2000.0, kademe=12)
    b = getiri_secim(_pr(), _oyn(), 2000.0, kademe=12)
    assert a is not None and b is not None
    assert (b.banko, b.cift, b.uclu) == (a.banko, a.cift, a.uclu)
    assert b.bedel == a.bedel


def test_kayip_tavani_hedefi_KORUYOR():
    """Kısıt bağlayıcı: `P` tabanın (1−tavan) katının altına inemez."""
    from spor_toto.secim import getiri_secim, hedef_olasiligi, sistem_secimi

    taban = sistem_secimi(_pr(), 2000.0, kademe=12)
    assert taban is not None
    p0 = hedef_olasiligi(_pr(), taban.secimler, 1)
    for tavan in (0.0, 0.05, 0.25):
        b = getiri_secim(_pr(), _oyn(), 2000.0, kademe=12,
                         kayip_tavani=tavan)
        assert b is not None
        assert b.p_hedef >= p0 * (1 - tavan) - 1e-12, tavan


def test_kayip_tavani_BUYUDUKCE_daha_cok_mac_degisir():
    """Tavan monoton: gevşedikçe arama daha çok maça dokunabilir."""
    from spor_toto.secim import getiri_secim, sistem_secimi

    taban = sistem_secimi(_pr(), 2000.0, kademe=12)
    assert taban is not None
    onceki = -1
    for tavan in (0.0, 0.25, 0.95):
        b = getiri_secim(_pr(), _oyn(), 2000.0, kademe=12,
                         kayip_tavani=tavan)
        assert b is not None
        dg = sum(1 for x, y in zip(taban.secimler, b.secimler)
                 if set(x) != set(y))
        assert dg >= onceki
        onceki = dg


def test_KISITSIZ_arama_hedefi_yok_edebilir():
    """Kısıtın niçin var olduğu — ölçülmüş tuzağın bekçisi.

    Kısıtsız `E[TL]` enbüyüklemesi, `pay_beklentisi`nin küçük `q`'da
    patlaması yüzünden neredeyse hiç gerçekleşmeyen bir dalı seçebilir.
    2026/27 2. haftada bu tam olarak yaşandı: `E[TL]` 3,01 kat büyürken
    `P` 0,2194'ten 0,0073'e düştü ve gerçekleşen 1.439 TL sıfıra indi.
    """
    from spor_toto.secim import GETIRI_KAYIP_TAVANI, getiri_secim

    assert 0.0 < GETIRI_KAYIP_TAVANI < 0.2, "varsayilan temkinli olmali"
    sikı = getiri_secim(_pr(), _oyn(), 2000.0, kademe=12, kayip_tavani=0.0)
    gevsek = getiri_secim(_pr(), _oyn(), 2000.0, kademe=12, kayip_tavani=0.95)
    assert sikı is not None and gevsek is not None
    assert gevsek.p_hedef <= sikı.p_hedef


def test_gecersiz_kayip_tavani_sesli_duser():
    from spor_toto.secim import getiri_secim

    for kotu in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError, match="kayip_tavani"):
            getiri_secim(_pr(), _oyn(), 2000.0, kayip_tavani=kotu)
