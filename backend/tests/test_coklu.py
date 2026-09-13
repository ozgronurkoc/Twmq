"""Çoklu kuponun denetimi.

Bu modülün iddiası bir **sayı** değil bir **yapıdır**: aynı bütçe birden çok
kupona bölünürse `P(15/15)` artar. Testlerin çoğu o yapının bozulmadığını
kovalıyor — kuponlar ayrık mı, bütçe aşılıyor mu, iki ayrı hesap aynı hedefi
mi söylüyor.

`test_p_onbes_plandan_ve_kupondan_AYNI` süs değil: yazıldığında **gerçek bir
hatayı tuttu**. `coklu_plan` bileşim indeksini ham sembol düzeninde (`1/0/2`)
kuruyor ama çözerken sıralama düzenine çeviriyordu; plan `P = 0,0329` derken
kupondan yeniden ölçüm `0,0215` veriyordu. Aynı kupon iki yerde iki farklı
hedef gösteriyordu ve tek görünür belirti bu ayrışmaydı.
"""

from itertools import pairwise

import numpy as np
import pytest

from spor_toto.coklu import (
    MAC_SAYISI,
    VARSAYILAN_KUPON_TAVANI,
    coklu_plan,
    coklu_plan_serisi,
    eksen_sec,
    kademe_dagilimi,
    kupon_sayisi_egrisi,
    p_onbes,
)
from spor_toto.core import SEMBOLLER
from spor_toto.secim import en_iyi_secim


def _probs(tohum: int = 0) -> list[dict[str, float]]:
    rng = np.random.default_rng(tohum)
    out = []
    for _ in range(MAC_SAYISI):
        v = rng.dirichlet([6.0, 3.0, 2.5])
        out.append({s: float(v[j]) for j, s in enumerate(SEMBOLLER)})
    return out


def test_p_onbes_plandan_ve_kupondan_AYNI():
    """Planın taşıdığı hedef ile kupondan yeniden ölçülen hedef ayrışmaz."""
    for tohum in range(8):
        probs = _probs(tohum)
        plan = coklu_plan(probs, 19_683, VARSAYILAN_KUPON_TAVANI)
        assert plan.p_onbes == pytest.approx(p_onbes(probs, plan.kuponlar),
                                             rel=1e-12)


def test_p_onbes_NORMALLESMEMIS_girdide_de_AYNI():
    """Aynı ayrışma, satır toplamı 1 **olmayan** girdide de olmamalı.

    Üstteki bekçi bu kusuru göremiyordu: `_probs` Dirichlet'ten üretiyor ve
    satırları tam 1 topluyor. Arşiv öyle değil — olasılıklar dört haneye
    yuvarlı ve satır 1,0001 gelebiliyor. `coklu_plan` `p_eksen`i
    normalleştirilmiş matristen, `p_alt`ı ise ham sözlükten okuduğu için o
    fazlalık üçlü bırakılan her maçta bir kez daha çarpılıyordu: gerçek
    haftalarda `plan.p_onbes`, kupondan yeniden ölçülen `p_onbes`ten binde
    0,3 büyük çıkıyordu. Küçük bir sayı ama iki sonucu var — aynı kupon iki
    hedef gösteriyor, ve fazlalık adaylara eşit binmediği için aramanın
    sıralamasını oynatabiliyor.
    """
    for tohum in range(8):
        probs = _probs(tohum)
        # arşivin yuvarlaması: dört hane, satır toplamı 1'den sapıyor
        probs = [{s: round(v, 4) for s, v in d.items()} for d in probs]
        assert any(abs(sum(d.values()) - 1.0) > 1e-9 for d in probs)
        plan = coklu_plan(probs, 19_683, VARSAYILAN_KUPON_TAVANI)
        assert plan.p_onbes == pytest.approx(p_onbes(probs, plan.kuponlar),
                                             rel=1e-12)


def test_kuponlar_AYRIK():
    """İki kupon aynı kolonu içeremez — içerseydi toplama hakkımız olmazdı.

    `p_onbes` kupon olasılıklarını **topluyor**; bu ancak kuponlar ayrıksa
    doğrudur. Ayrıklık, her kupon çiftinin en az bir eksen maçında farklı
    tek sembol taşımasından gelir.
    """
    probs = _probs(3)
    plan = coklu_plan(probs, 19_683, kupon_tavani=27)
    for a in range(len(plan.kuponlar)):
        for b in range(a + 1, len(plan.kuponlar)):
            ka, kb = plan.kuponlar[a], plan.kuponlar[b]
            assert any(set(x).isdisjoint(y)
                       for x, y in zip(ka.secimler, kb.secimler)), (
                f"{a}. ve {b}. kupon kesisiyor")


def test_kupon_sayisi_buyudukce_P15_DUSMEZ():
    """Eğri monoton: daha çok kupon her zaman en az o kadar kapsama verir."""
    for tohum in range(5):
        probs = _probs(tohum)
        egri = kupon_sayisi_egrisi(probs, 19_683)
        ps = [p for _, _, p in egri]
        assert ps == sorted(ps), f"egri monoton degil: {ps}"


def test_tek_kupon_TEK_SISTEMIN_kendisi():
    """Tavan 1 iken plan, `en_iyi_secim`in kurduğu tek sistemin aynısıdır.

    Bu modül mevcut davranışı **içerir**: genelleme onu bir aday olarak gezer
    ve tavan onu tek adaya indirdiğinde birebir aynısını üretmelidir. İlk
    sürüm bunu geçemiyordu — eksen dışını üçlüye zorladığı için `en_iyi_secim`
    daha iyisini buluyordu (`P = 0,1240` ↔ `0,1142`, 17.496 ↔ 19.683 kolon).
    """
    for tohum in range(5):
        probs = _probs(tohum)
        plan = coklu_plan(probs, 19_683, kupon_tavani=1)
        assert plan.kupon_sayisi == 1
        tek = en_iyi_secim(probs, 19_683, esik=0)
        a = [sorted(s) for s in plan.kuponlar[0].secimler]
        b = [sorted(s) for s in tek.secimler]
        assert a == b
        assert plan.p_onbes == pytest.approx(
            p_onbes(probs, plan.kuponlar), rel=1e-12)


def test_coklu_TEK_SISTEMI_gecer():
    """Asıl iddia: aynı bütçede çoklu kupon tek sistemden kötü olamaz.

    Arama tek sistemi zaten bir aday olarak geziyor, o yüzden bu bir
    **eşitsizliktir**, bir umut değil. Eşitlik nadir haftalarda olabilir;
    testin tuttuğu şey gerilemedir.
    """
    for tohum in range(8):
        probs = _probs(tohum)
        tek = coklu_plan(probs, 19_683, kupon_tavani=1)
        cok = coklu_plan(probs, 19_683, kupon_tavani=81)
        assert cok.p_onbes >= tek.p_onbes - 1e-12


def test_seri_TEK_TEK_cagirmakla_ayni():
    """Tek geçişli seri, tavan tavan çağırmakla aynı planı vermeli.

    Seri bir hızlandırmadır (114 haftalık kıyasta yedi kat), davranış
    değişikliği değil. Ayrışırsa hızlandırma sessizce yanlış plan üretir.
    """
    tavanlar = (1, 9, 81)
    for tohum in range(4):
        probs = _probs(tohum)
        seri = coklu_plan_serisi(probs, 19_683, tavanlar)
        for t in tavanlar:
            tek = coklu_plan(probs, 19_683, kupon_tavani=t)
            assert seri[t].p_onbes == pytest.approx(tek.p_onbes, rel=1e-12)
            assert seri[t].kupon_sayisi == tek.kupon_sayisi


def test_seri_tavanla_BIRIKIMLI():
    """Tavan büyüdükçe hedef düşemez — arama uzayı yalnızca genişler."""
    probs = _probs(5)
    seri = coklu_plan_serisi(probs, 19_683)
    ps = [seri[t].p_onbes for t in sorted(seri)]
    assert ps == sorted(ps)


def test_butce_asilmaz():
    for butce in (243, 729, 5_000, 19_683, 21_000):
        probs = _probs(1)
        plan = coklu_plan(probs, butce, VARSAYILAN_KUPON_TAVANI)
        assert plan.kolon <= butce
        assert plan.kolon == sum(k.kolon for k in plan.kuponlar)


def test_butce_BOSA_gitmez():
    """Tavan kısıtlamıyorsa bütçenin neredeyse tamamı kullanılmalı.

    Kupon sayısı bir ızgaradan (`ARANAN_KUPON`) alınıyordu ve bütçe boşa
    gidiyordu: 21.000 kolonda plan 81 × 243 = 19.683 kuruyor, 1.317 kolon
    (13.170 TL) hiçbir şey satın almıyordu. Kupon sayısı artık alt sistemin
    bedelinden türüyor; artan, bir kupon boyundan küçük olmalı.
    """
    for butce in (21_000, 19_683, 12_345):
        probs = _probs(6)
        plan = coklu_plan(probs, butce)
        kupon_kolon = plan.kuponlar[0].kolon
        assert plan.kolon <= butce
        assert butce - plan.kolon < kupon_kolon, (
            f"butce {butce}: {butce - plan.kolon} kolon bosa gitti "
            f"(kupon {kupon_kolon} kolon)")


def test_butce_pozitif_olmali():
    """Sessizce kırpmaz: eksik plan yanlış hedefi görünmez kılardı."""
    with pytest.raises(ValueError, match="pozitif"):
        coklu_plan(_probs(0), 0)


def test_eksen_FAVORI_olasiligina_gore_secilir():
    """Eksen, ev sahibi olasılığına göre değil favoriye göre seçilir.

    İlk sürüm `P[:, 0]`'a bakıyordu; `_matris` ham düzende (`1/0/2`) döndüğü
    için o sütun **ev sahibi**dir, favori değil. Deplasman favorili maçlar
    yanlış tarafa düşüyordu.
    """
    probs = [{"1": 0.10, "0": 0.20, "2": 0.70}] + \
            [{"1": 0.40, "0": 0.30, "2": 0.30}] * (MAC_SAYISI - 1)
    assert 0 in eksen_sec(probs, 1)


def test_butce_MERDIVEN_degil():
    """Daha büyük bütçe daha kötü plan veremez.

    Tek sistemde bedel `2^a·3^b` olduğu için bütçe basamaklıydı: 19.683 ile
    21.000 kolon **aynı** kuponu alıyordu. Çoklu kuponda bedel `M · kupon`
    ve `M` serbest tamsayı, yani aradaki para da bir şey satın alabilir.
    """
    probs = _probs(2)
    a = coklu_plan(probs, 19_683, kupon_tavani=243)
    b = coklu_plan(probs, 21_000, kupon_tavani=243)
    assert b.p_onbes >= a.p_onbes - 1e-12
    assert b.kolon >= a.kolon


def test_kademe_dagilimi_kupon_kupon_TOPLANIR():
    """Kademe sayımı her kupondan toplanır; tek sistemin sayımı değil."""
    probs = _probs(4)
    plan = coklu_plan(probs, 19_683, kupon_tavani=81)
    gercek = [max(p, key=p.get) for p in probs]      # her maçta favori
    dag = kademe_dagilimi(probs, plan.kuponlar, gercek)
    assert dag[15] == 1, "favori sonucunda tam olarak bir kolon 15 yapar"
    assert sum(dag.values()) <= plan.kolon


def test_p_onbes_GERCEK_float_donuyor():
    """İmza `-> float` diyor; numpy skaleri dönmek bir tip yalanıdır.

    `_matris` numpy döndüğü için gövdedeki toplam `np.float64` çıkıyordu ve
    bu sessiz kalmadı: çoklu kupon kaydının değerlendirmesinde bu değerden
    türeyen bir karşılaştırma `np.bool_` verdi ve `json.dumps` `TypeError`
    attı. `coklu_plan`ın taşıdığı `p_onbes` zaten `float`tu — yani aynı
    sayı iki yoldan iki ayrı TİPTE geliyordu.
    """
    probs = _probs(11)
    plan = coklu_plan(probs, 2187, kupon_tavani=9)
    yeniden = p_onbes(probs, plan.kuponlar)
    assert type(yeniden) is float
    assert type(plan.p_onbes) is float
    import json
    json.dumps({"p": yeniden, "esit": yeniden == plan.p_onbes})


# ─── tahsis: kupon başına ayrı alt sistem bütçesi (§3.71) ─────────────────

def _eski_arama(probs: list[dict[str, float]], butce: int, tavan: int) -> float:
    """Bu modülün İLK aramasının kendisi — betikten çağrılır, kopyalanmaz.

    Referans gövde `scripts/tahsis_kiyasi.py::tek_tip_arama`da duruyor ve
    orada durmasının sebebi var: 114 haftalık kıyası koşan şey o betik, yani
    gövde zaten orada gerekiyor. Buraya kopyalansaydı iki referans olurdu ve
    biri sessizce eskirdi — bu deponun tam olarak kaçındığı desen.
    """
    from scripts.tahsis_kiyasi import tek_tip_arama

    return tek_tip_arama(probs, butce, tavan)


def test_tahsisli_plan_ESKI_aramadan_kotu_DEGIL():
    """Yeni arama eski aramayı **içeriyor**: hiçbir haftada geride kalamaz.

    Tahsis bir sezgisel değil bir genişletme: tek tip aday (eski aramanın
    tamamı) aramada duruyor ve ikisinin en iyisi seçiliyor. Bu bekçi düşerse
    genişletme sırasında bir aday **kaybolmuş** demektir — ölçülen kazanç da
    o hâlde bir kazanç değil bir kıyas hatası olurdu.
    """
    for tohum in range(6):
        probs = _probs(tohum)
        for tavan in (1, 27, 81, 729):
            yeni = coklu_plan(probs, 19_683, kupon_tavani=tavan)
            eski = _eski_arama(probs, 19_683, tavan)
            assert yeni.p_onbes >= eski - 1e-12, (
                f"tohum={tohum} tavan={tavan}: yeni {yeni.p_onbes:.6f} < "
                f"eski {eski:.6f}")


def test_tahsis_TEK_KUPONDA_eski_aramanin_AYNISI():
    """`tavan = 1`de tahsisin oynayacak bir şeyi yok — sayı birebir aynı.

    Tek kupon hâlinde eksen bileşimi tektir, yani bütçe bölünmüyor ve tahsis
    tek tip adaya iner. Ayrışırlarsa genişletme tek sistem satırını da
    oynatmış olurdu ve §3.67'nin kıyas tabanı kayardı.
    """
    for tohum in range(4):
        probs = _probs(tohum)
        plan = coklu_plan(probs, 19_683, kupon_tavani=1)
        assert plan.p_onbes == pytest.approx(_eski_arama(probs, 19_683, 1),
                                             rel=1e-12)


def test_tahsis_GERCEKTEN_farkli_boyda_kupon_uretiyor():
    """Mekanizma kâğıt üstünde değil, gerçekten ateşliyor mu.

    Tahsisin tek işi kuponlara **ayrı** bütçeler vermek. Kazanan plan hep
    tek tip çıkıyorsa ya cephe kırpılmıştır (prototipte tam bu oldu: cephe
    `bütçe // M` ile çıkarılınca kazanç sıfır göründü) ya da açgözlü
    yükseltme hiç çalışmıyordur. İkisi de sessiz kusurdur.
    """
    farkli = 0
    for tohum in range(6):
        plan = coklu_plan(_probs(tohum), 19_683, kupon_tavani=81)
        if len({k.kolon for k in plan.kuponlar}) > 1:
            farkli += 1
    assert farkli >= 4, f"6 haftanin yalnizca {farkli}'inde tahsis farkli bedel verdi"


def test_tahsis_DAHA_OLASI_kupona_daha_cok_kolon():
    """Eksen olasılığı büyük olan kupon daha az kolon alamaz.

    Bu, tahsisin tanımının kendisi: bütün kuponlar aynı cepheyi paylaşıyor ve
    yükseltmenin değeri `q_j · Δp`. O hâlde `q` azalırken seçilen bedel de
    azalmak zorunda — tersi, açgözlünün bozulduğu ya da `q`nun sırasının
    kaybolduğu anlamına gelir (`_eksen_bilesimleri` azalan sırada döner).
    """
    from spor_toto.coklu import _matris

    for tohum in range(4):
        probs = _probs(tohum)
        P = _matris(probs)
        plan = coklu_plan(probs, 19_683, kupon_tavani=81)
        q = [float(np.prod([P[i][SEMBOLLER.index(sec[0])]
                            for i, sec in enumerate(k.secimler)
                            if i in set(plan.eksen)]))
             for k in plan.kuponlar]
        kolonlar = [k.kolon for k in plan.kuponlar]
        ikili = sorted(zip(q, kolonlar), key=lambda x: -x[0])
        assert all(y[1] <= x[1] for x, y in pairwise(ikili)), ikili


def test_ust_kabuk_ORANLARI_azaltiyor_ve_cepheden_secmiyor_disindan():
    """Kabuk: marjinal oranlar azalan, ve her noktası cephenin **gerçek** noktası.

    İkisi de gerekli. Oranlar azalmazsa açgözlü tahsis yanlış sırayla
    yükseltir; kabuk cephe dışına çıkarsa seçilen "plan" oynanamaz bir
    noktadır.
    """
    from spor_toto.coklu import _ust_kabuk

    noktalar = [(1, 0.20, None), (2, 0.34, None), (3, 0.40, None),
                (4, 0.52, None), (6, 0.60, None), (9, 0.61, None),
                (12, 0.75, None), (27, 0.90, None)]
    kabuk = _ust_kabuk(noktalar)
    assert all(n in noktalar for n in kabuk)
    assert kabuk[0] == noktalar[0] and kabuk[-1] == noktalar[-1]
    oranlar = [(y[1] - x[1]) / (y[0] - x[0]) for x, y in pairwise(kabuk)]
    assert all(y <= x + 1e-15 for x, y in pairwise(oranlar)), oranlar
    # baskılanmış nokta (3, 0,40) kabukta olmamalı: (2,0,34)-(4,0,52) dogrusu
    # onu asiyor
    assert (3, 0.40, None) not in kabuk


def test_tahsis_butce_yetmezse_None():
    """`M` kupon en ucuz noktadan bile alınamıyorsa tahsis yok, hata da yok."""
    from spor_toto.coklu import _tahsis

    assert _tahsis([0.5] * 10, [(3, 0.4, None)], 20) is None
    assert _tahsis([0.5] * 10, [], 1000) is None
