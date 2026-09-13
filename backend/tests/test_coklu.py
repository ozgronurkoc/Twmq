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

    Bu, tahsisin tanımının kendisi: kuponlar aynı cepheyi paylaşıyor ve
    yükseltmenin değeri `q_j · Δp`. O hâlde `q` azalırken seçilen bedel de
    azalmak zorunda — tersi, açgözlünün bozulduğu ya da `q`nun sırasının
    kaybolduğu anlamına gelir.

    Bekçi önce **planın üzerinden** koşuyordu: `plan.eksen`e bakıp `q`yu
    kupondan yeniden kuruyordu. §3.72 onu kırdı ve haklı olarak — değişken
    derinlikli planda kuponların ortak ekseni yok, yani o yoldan okunan `q`
    bütün kuponlarda **aynı** çıkıyor ve test kendi ölçtüğü şeyi kaybediyor.
    İddia zaten plana değil tahsisin kendisine aitti; bekçi oraya indi.
    """
    from spor_toto.coklu import _tahsis

    cephe = [(1, 0.10, None), (2, 0.18, None), (4, 0.30, None),
             (8, 0.44, None), (16, 0.56, None), (32, 0.63, None)]
    q = [0.30, 0.20, 0.12, 0.08, 0.05, 0.03, 0.01, 0.004]
    sonuc = _tahsis(q, cephe, 120)
    assert sonuc is not None
    kolonlar = [n[0] for n in sonuc[1]]
    assert all(y <= x for x, y in pairwise(kolonlar)), kolonlar
    assert sum(kolonlar) <= 120


def test_tahsis_KABUKLU_govdesi_ayni_kabukta_tahsisle_ayni():
    """`_tahsis_kabuklu` genelleştirme, davranış değişikliği değil.

    Değişken derinlikte her kuponun kabuğu ayrı (§3.72) ve tahsis o yüzden
    kabuk listesi alan bir gövdeye taşındı. Bütün kabuklar aynıyken sonuç
    eski gövdeyle birebir aynı olmalı — ayrışırsa §3.71'in bütün sayıları
    sessizce kayardı.
    """
    from spor_toto.coklu import _tahsis, _tahsis_kabuklu, _ust_kabuk

    cephe = [(1, 0.10, None), (3, 0.31, None), (9, 0.52, None),
             (27, 0.70, None), (81, 0.81, None)]
    q = [0.4, 0.25, 0.15, 0.1, 0.06, 0.04]
    kabuk = _ust_kabuk(cephe)
    a = _tahsis(q, cephe, 200)
    b = _tahsis_kabuklu(q, [kabuk] * len(q), 200)
    assert a is not None and b is not None
    assert a[0] == pytest.approx(b[0], rel=1e-15)
    assert [n[0] for n in a[1]] == [n[0] for n in b[1]]


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


# ─── değişken derinlikli eksen (§3.72) ───────────────────────────────────

def _oyuncak_katlar() -> list:
    """Elde kurulmuş kat listesi — ağaç mekaniğini cepheden bağımsız sınar.

    Gerçek katlar `secim_cephesi`den gelir ve onu kurmak 16 DP demek; ağacın
    kendi kuralları (antizincir, tavan, kök) cephenin şekline bakmıyor.

    Ama bir şeye bakıyor: **derin kat sığ kattan iyi olmalı**. `n` maçlık alt
    sistemde hepsi tek işaret `0,6ⁿ` verir ve bir maçı çifte çevirmek bedeli
    ikiye, olasılığı `0,85/0,6` katına çıkarır. İlk sürüm bütün derinliklere
    aynı kabuğu veriyordu ve ağaç **hiç bölünmüyordu** — haklı olarak:
    `w ↦ max_i(w·pᵢ − λ·cᵢ)` dışbükey ve `f(0) ≤ 0` olduğu için üstToplamsal,
    yani aynı kabukta bölmek tanım gereği kaybettirir. Bölmenin değeri
    tamamen "bir maç eksildi" farkından gelir.
    """
    from spor_toto.coklu import Nokta, _kat_kur

    katlar = []
    for k in range(MAC_SAYISI + 1):
        n = MAC_SAYISI - k
        noktalar: list[Nokta] = (
            [(1, 1.0, None)] if n == 0 else
            [(2 ** i, 0.6 ** (n - i) * 0.85 ** i, None) for i in range(n + 1)])
        katlar.append(_kat_kur(noktalar))
    return katlar


def _oyuncak_P() -> np.ndarray:
    """15 maçlık, favorisi belirgin ve maçtan maça değişen olasılık matrisi."""
    rng = np.random.default_rng(17)
    return np.array([rng.dirichlet([7.0, 3.0, 2.0]) for _ in range(MAC_SAYISI)])


def test_agac_yapraklari_ANTIZINCIR():
    """Hiçbir yaprak başka bir yaprağın ön eki olamaz.

    `p_onbes` kupon olasılıklarını **topluyor** ve bu ancak kuponlar ayrıksa
    doğrudur. Değişken derinlikte ayrıklığın tek kaynağı budur: yapraklar
    eminlik sırasının ön ek ağacında bir antizincirdir. Bölünen düğüm yaprak
    listesinde kalsaydı çocuklarının kolonları iki kez sayılırdı — ve
    `p_onbes` bunu **görmezdi**, çünkü o da aynı listeden toplar.
    """
    from spor_toto.coklu import _agac_buyut

    katlar = _oyuncak_katlar()
    P = _oyuncak_P()
    sonuc = _agac_buyut(P, list(range(MAC_SAYISI)), katlar, 81, 1e-5)
    assert sonuc is not None
    yapraklar = [bil for _q, _k, bil in sonuc[0]]
    assert len(yapraklar) > 1, "agac hic bolunmedi — sinav bos"
    for a in yapraklar:
        for b in yapraklar:
            if a is b:
                continue
            assert a[:len(b)] != b, f"{b} yapragi {a} yapraginin on eki"


def test_agac_TAVANI_asmiyor_ve_TEK_TAVANDA_kok():
    """Tavan bir operasyon kısıtı: aşılırsa oynanamayan plan üretilir.

    `tavan = 1` özellikle sınanıyor — o hâlde ağaç hiç bölünmemeli ve kök
    (derinlik 0, yani eksen yok) tek yaprak olarak kalmalı. Kök bölünseydi
    `coklu_plan(..., kupon_tavani=1)` tek sistem olmaktan çıkardı ve §3.67'nin
    bütün kıyas tabanı kayardı.
    """
    from spor_toto.coklu import _agac_buyut

    katlar = _oyuncak_katlar()
    P = _oyuncak_P()
    for tavan in (1, 2, 7, 27, 243):
        sonuc = _agac_buyut(P, list(range(MAC_SAYISI)), katlar, tavan, 1e-5)
        assert sonuc is not None
        assert len(sonuc[0]) <= tavan, f"tavan {tavan}: {len(sonuc[0])} yaprak"
    tek = _agac_buyut(P, list(range(MAC_SAYISI)), katlar, 1, 1e-5)
    assert tek is not None
    assert tek[0] == [(1.0, 0, ())]


def test_en_iyi_nokta_KABUGUN_ARGMAXI():
    """Fiyatlama `bisect` ile yapılıyor; kaba kuvvetle aynı noktayı vermeli.

    `w·p − λ·bedel`in enbüyükleyeni, kabukta oranlar azalan olduğu için bir
    **ön ek** sayısıyla bulunuyor (`bisect`). Kayma olsaydı ağaç sessizce
    yanlış şekli alırdı ve hiçbir bekçi bunu görmezdi: sonuç yine geçerli bir
    plan olurdu, yalnızca daha kötüsü.
    """
    from spor_toto.coklu import _en_iyi_nokta, _kat_kur

    kat = _kat_kur([(1, 0.10, None), (2, 0.18, None), (4, 0.30, None),
                    (8, 0.44, None), (16, 0.56, None), (64, 0.66, None)])
    assert kat is not None
    for w in (1.0, 0.4, 0.05, 0.004):
        for lam in (1e-5, 1e-3, 5e-3, 2e-2, 0.1):
            kaba = max(range(len(kat.bedel)),
                       key=lambda i: w * kat.p[i] - lam * kat.bedel[i])
            en_iyi = w * kat.p[kaba] - lam * kat.bedel[kaba]
            sonuc = _en_iyi_nokta(kat, w, lam)
            if en_iyi <= 0:
                assert sonuc is None, f"w={w} lam={lam}: deger {en_iyi}"
            else:
                assert sonuc is not None
                assert sonuc[1] == pytest.approx(en_iyi, rel=1e-12), (w, lam)


def test_agac_adayi_ARAMAYI_DARALTMIYOR():
    """Üçüncü aday eklendi; önceki iki aday **yerinde** kalmalı.

    Ağaç bir sezgiseldir (açgözlü, fiyat ızgarası üstünde) ve ölçülen kazancı
    binde birler mertebesinde (§3.72). O yüzden burada tutulan şey kazanç
    **değil**: üçüncü adayın eskileri gölgelemediği. Gölgeleseydi §3.71'in
    bütün sayıları sessizce gerilerdi ve bunun tek belirtisi bu bekçi olurdu.
    """
    tavanlar = (1, 27, 81)
    for tohum in range(5):
        probs = _probs(tohum)
        yeni = coklu_plan_serisi(probs, 21_000, tavanlar)
        eski = coklu_plan_serisi(probs, 21_000, tavanlar,
                                 degisken_derinlik=False)
        for t in tavanlar:
            assert yeni[t].p_onbes >= eski[t].p_onbes - 1e-12, (tohum, t)


def test_agac_KAZANDIGINDA_da_kupon_ayrik_ve_hedef_ayni():
    """Ağaç planı üretim yoluna girdiğinde de aynı iki değişmez geçerli.

    Üstteki iki genel bekçi (`test_kuponlar_AYRIK`,
    `test_p_onbes_plandan_ve_kupondan_AYNI`) **kazanan** aileyi sınıyor, yani
    ağaç hiç kazanmadığı bir tohum kümesinde onlara hiç değmez. Bu bekçi
    ağacın kazandığı bir hafta seçiyor ve iki değişmezi orada kovalıyor —
    değişken derinlikte kupon gövdeleri ayrı bir yoldan kuruluyor
    (`_kuponlari_kur` kupon başına, farklı eksenle).
    """
    probs = _probs(2)
    plan = coklu_plan_serisi(probs, 21_000, (9,))[9]
    duz = coklu_plan_serisi(probs, 21_000, (9,), degisken_derinlik=False)[9]
    assert plan.p_onbes > duz.p_onbes, "secilen hafta artik agacla kazanmiyor"

    assert plan.p_onbes == pytest.approx(p_onbes(probs, plan.kuponlar),
                                         rel=1e-12)
    assert plan.kolon == sum(k.kolon for k in plan.kuponlar) <= 21_000
    for a in range(len(plan.kuponlar)):
        for b in range(a + 1, len(plan.kuponlar)):
            ka, kb = plan.kuponlar[a], plan.kuponlar[b]
            assert any(set(x).isdisjoint(y)
                       for x, y in zip(ka.secimler, kb.secimler)), (a, b)
