"""Bahisçi anlaşmazlığı (A2) — ölçümün ve kaynak seçiminin denetimi.

A2 iki cümle söylüyor ve ikisi de farklı türden:

    Pinnacle kolektifi geçiyor           — bir VARLIK iddiası
    Anlaşmazlık bilgi taşımıyor          — bir YOKLUK iddiası

Varlık iddiası küçük (−0,0004 Brier) ve dar bir aralıkla geçiyor; yanlışsa
sebebi ya kesitin kayması ya referansın yanlış doldurulmasıdır. Yokluk iddiası
ise sessizce yanlış olabilir: özellik bağlanmamışsa da, kesit bozuksa da aynı
sonucu verir.

Ama A2'nin en kırılgan yeri ikisi de değil, **kaynak seçimi**. İki karar
ölçümün kendisini belirliyor ve ikisi de burada bekçiye bağlı:

    `ayrisma` sabit bir kaynak çiftinden gelir     → sezonlar arası kaymamalı
    `en_iyi_prim` bahisçi sayısına duyarlıdır      → modele VERİLMEMELİ

İkincisi verilirse model anlaşmazlık değil **sezon kimliği** öğrenir ve sezon
dışarıda bırakmalı ölçüm sessizce çöker.
"""

import importlib.util
from pathlib import Path

import pytest

from spor_toto.bahisci import (
    AYRISMA_BANTLARI,
    TEKIL_BAHISCILER,
    BahisciTahminci,
    ayrisma_ozeti,
    dagilim_katsayisi,
    kesit,
)
from spor_toto.egitim import bahisci_ayrismasi, korpus_haftalari, korpus_yukle
from spor_toto.history import SYMBOLS
from spor_toto.predict import PiyasaTahminci

KOK = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_egitim_a2", KOK / "scripts" / "build_egitim.py")
uretici = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uretici)


@pytest.fixture(scope="module")
def a2():
    h = kesit()
    if not h:
        pytest.skip("egitim korpusu yok — once scripts/build_egitim.py")
    return h


def _dortlu(b365, ps, mx, avg):
    return {"b_B365": b365, "b_PS": ps, "b_Max": mx, "b_Avg": avg}


# ─── ayrışmanın tanımı ────────────────────────────────────────────────────────

def test_ayrisma_dortlu_yoksa_sifir():
    """Doktrin 2: eksik dörtlü uydurulmaz, nötr sıfıra düşer."""
    for eksik in (None, {}, _dortlu({"1": 2.0, "0": 3.0, "2": 4.0}, None, None, None)):
        assert bahisci_ayrismasi(eksik) == {"ayrisma": 0.0, "en_iyi_prim": 0.0}


def test_ayrisma_hemfikir_kaynaklarda_sifir():
    uclu = {"1": 2.0, "0": 3.6, "2": 4.5}
    d = bahisci_ayrismasi(_dortlu(dict(uclu), dict(uclu), dict(uclu), dict(uclu)))
    assert d["ayrisma"] == pytest.approx(0.0, abs=1e-12)
    assert d["en_iyi_prim"] == pytest.approx(0.0, abs=1e-12)


def test_ayrisma_saf_marj_farkini_gormez():
    """**Marj arındırmanın varlık sebebi.**

    İki bahisçi aynı fikirde olup farklı marj alıyorsa bu bir anlaşmazlık
    değildir. Ham oran üzerinden ölçseydik `ayrisma`, bahisçilerin görüşünü
    değil fiyatlama politikalarını ölçerdi — ve Pinnacle'ın düşük marjı tek
    başına onu "herkesle anlaşmaz" gösterirdi.
    """
    uclu = {"1": 2.0, "0": 3.6, "2": 4.5}
    dar = {s: v * 1.05 for s, v in uclu.items()}       # ayni fikir, dusuk marj
    d = bahisci_ayrismasi(_dortlu(dict(uclu), dar, dict(dar), dict(uclu)))
    assert d["ayrisma"] == pytest.approx(0.0, abs=1e-12)


def test_ayrisma_gercek_fikir_farkini_gorur():
    b365 = {"1": 2.00, "0": 3.60, "2": 4.50}
    ps = {"1": 3.00, "0": 3.60, "2": 2.60}            # "1" yerine "2" favori
    d = bahisci_ayrismasi(_dortlu(b365, ps, dict(b365), dict(b365)))
    assert d["ayrisma"] > 0.10


def test_en_iyi_prim_max_ile_avg_arasi():
    b = {"1": 2.0, "0": 3.6, "2": 4.5}
    d = bahisci_ayrismasi(_dortlu(dict(b), dict(b), {"1": 2.2, "0": 3.9, "2": 5.0}, dict(b)))
    assert d["en_iyi_prim"] > 0


# ─── kaynak seçimi — A2'nin en kırılgan yeri ──────────────────────────────────

def test_ayrisma_sezonlar_arasi_sabit(a2):
    """**Tasarım kararının bekçisi.**

    `ayrisma` sabit bir kaynak çiftinden (`B365`↔`PS`) gelir; ikisi de dört
    sezonda da ~%100 mevcut. Sezona göre kayarsa özellik anlaşmazlık değil
    sezon kimliği taşımaya başlar ve sezon dışarıda bırakmalı ölçüm çöker:
    model bir sezonu "yüksek anlaşmazlık sezonu" diye ezberler.
    """
    sezona_gore = ayrisma_ozeti(a2)["sezona_gore"]
    degerler = [v["ayrisma"] for v in sezona_gore.values()]
    assert len(degerler) >= 3
    assert max(degerler) - min(degerler) < 0.005, (
        f"ayrisma sezonlara gore kayiyor: {sezona_gore}")


def test_en_iyi_prim_surukleniyor_ve_bu_yuzden_modele_verilmiyor(a2):
    """`Max/Avg` neden **ikincil** kaldı — sürüklenme ölçülmüş bir olgudur.

    `Max` bütün bahisçilerin en iyisidir; football-data kaynak ekledikçe
    mekanik olarak kayar. Sürüklenme `ayrisma`nınkinden belirgin biçimde
    büyük olmalı — değilse bu testin koruduğu ayrım anlamını yitirmiştir ve
    tasarım kararı yeniden düşünülmelidir.
    """
    sezona_gore = ayrisma_ozeti(a2)["sezona_gore"]
    prim = [v["en_iyi_prim"] for v in sezona_gore.values()]
    ayrisma = [v["ayrisma"] for v in sezona_gore.values()]
    assert max(prim) - min(prim) > 3 * (max(ayrisma) - min(ayrisma))


def test_model_en_iyi_primi_gormez():
    """Sürüklenen özellik tasarım matrisine **girmemeli**.

    `dagilim` basamağı yalnızca `ayrisma` sütununu ekler. `en_iyi_prim`
    sızsaydı model sezon kimliğini anlaşmazlık sanardı — ve bu sızıntı
    sessizdir: skor iyileşir, sebep yanlıştır.
    """
    from spor_toto.recalibrate import _mac_ozellikleri

    h = korpus_haftalari(sezonlar_=["2425"], bahisci_gerekli=True)
    for satir in _mac_ozellikleri(h[0]):
        assert "ayrisma" in satir
        assert "en_iyi_prim" not in satir


# ─── üretici: dörtlünün bütünlüğü ─────────────────────────────────────────────

def _ham(**alanlar):
    return {k: str(v) for k, v in alanlar.items()}


def test_dortlu_ya_tam_ya_hic():
    """Kısmi dörtlü, anlaşmazlığı değil o gün hangi kaynağın mevcut olduğunu ölçer."""
    tam = _ham(B365CH=2.0, B365CD=3.0, B365CA=4.0, PSCH=2.1, PSCD=3.1, PSCA=4.1,
               MaxCH=2.2, MaxCD=3.2, MaxCA=4.2, AvgCH=2.05, AvgCD=3.05, AvgCA=4.05)
    assert uretici.bahisci_dortlusu(tam) is not None

    eksik = dict(tam)
    for x in ("H", "D", "A"):
        eksik.pop(f"PSC{x}")
    assert uretici.bahisci_dortlusu(eksik) is None


def test_uretici_eksik_dortluyu_reddeder():
    temel = {"kod": "1", "oran_1": 2.0, "oran_0": 3.0, "oran_2": 4.0,
             "ev": "A", "dep": "B", "sezon": "2425", "lig": "XX",
             "tarih": "2025-01-01"}
    for _, ad in uretici.A2_KAYNAKLARI:
        for s, v in zip(("1", "0", "2"), (2.0, 3.0, 4.0)):
            temel[f"{ad}_{s}"] = v
    assert uretici.dogrula([temel]) == []

    temel["b_PS_0"] = ""
    assert any("bahisci dortlusu eksik" in h for h in uretici.dogrula([temel]))


def test_uretici_max_avgden_kucukse_reddeder():
    """`Max` en iyi fiyat, `Avg` ortalama — max < ort matematiksel olarak imkânsız.

    Çıkarsa kaynak sütunları karışmıştır ve `en_iyi_prim` ters işaretli olur.
    """
    temel = {"kod": "1", "oran_1": 2.0, "oran_0": 3.0, "oran_2": 4.0,
             "ev": "A", "dep": "B", "sezon": "2425", "lig": "XX",
             "tarih": "2025-01-01"}
    for _, ad in uretici.A2_KAYNAKLARI:
        for s, v in zip(("1", "0", "2"), (2.2, 3.2, 4.2)):
            temel[f"{ad}_{s}"] = v
    temel["b_Max_1"] = 2.0          # ortalamanin ALTINDA
    temel["b_Avg_1"] = 2.2
    assert any("b_Max_1 < b_Avg_1" in h for h in uretici.dogrula([temel]))


def test_korpusta_dortlu_butunlugu():
    """Gerçek korpusta yarım dörtlü yok ve `Max >= Avg` her maçta geçerli."""
    satirlar = korpus_yukle()
    if not satirlar:
        pytest.skip("korpus yok")
    dortlulu = [r for r in satirlar if r.get("bahisciler")]
    assert len(dortlulu) / len(satirlar) > 0.99
    for r in dortlulu:
        b = r["bahisciler"]
        for s in SYMBOLS:
            assert b["b_Max"][s] >= b["b_Avg"][s] - 1e-9


# ─── kesit ────────────────────────────────────────────────────────────────────

def test_kesit_probs_kolektif_kapanis(a2):
    """`probs` açıkça `b_Avg` ile doldurulur — `oran_*` tercihine yaslanmaz."""
    for hafta in a2[:20]:
        for i, o in enumerate(hafta["ozellikler"]):
            assert hafta["probs"][i] == o["bahisci_probs"]["b_Avg"]


def test_kesit_yalnizca_dortlulu_maclar(a2):
    for hafta in a2:
        for o in hafta["ozellikler"]:
            assert o["bahisci_var"] is True


def test_bahisci_tahmincisi_kendi_kaynagini_okur(a2):
    hafta = a2[0]
    ps = BahisciTahminci("b_PS").tahmin(hafta)
    kolektif = PiyasaTahminci().tahmin(hafta)
    for i, o in enumerate(hafta["ozellikler"]):
        assert ps[i] == o["bahisci_probs"]["b_PS"]
    assert ps != kolektif, "ps ve kolektif ayni cikti — kaynaklar karismis olabilir"


def test_bahisci_kupon_haftasinda_duzgune_duser():
    """Kupon haftaları bahisçi kırılımı taşımaz; uydurma değer yerine bilgisizlik."""
    from spor_toto.evaluate import olculebilir_haftalar
    kupon = olculebilir_haftalar()[0]
    for blok in BahisciTahminci("b_PS").tahmin(kupon):
        assert blok == pytest.approx({s: 1 / 3 for s in SYMBOLS})


def test_max_tekil_tahminci_degil():
    """`b_Max` bir bahisçi değil zarf; kafa kafaya ölçüme **girmemeli**.

    Her ayakta en iyi fiyatı toplar, dolayısıyla ters olasılıkları 1'in
    altında toplanır. Marj arındırma bunu yapay olarak düzeltir ve ortaya
    hiçbir bahisçinin gerçekten sunmadığı bir "tahmin" çıkar.
    """
    assert "b_Max" not in TEKIL_BAHISCILER
    assert "b_Avg" not in TEKIL_BAHISCILER


# ─── dağılım basamağı gerçekten bağlı mı ──────────────────────────────────────

def test_dagilim_kademesi_hareket_ustune_tek_sutun_ekler():
    from spor_toto.recalibrate import KalibreTahminci
    h = korpus_haftalari(sezonlar_=["2425"], bahisci_gerekli=True)
    hareket = KalibreTahminci("hareket"); hareket.egit(h)
    dagilim = KalibreTahminci("dagilim"); dagilim.egit(h)
    assert len(dagilim.katsayilar) == len(hareket.katsayilar) + 1


def test_dagilim_sutunu_gercekten_calisiyor():
    """**Yokluk iddiasının bekçisi.**

    "Anlaşmazlık bir şey eklemiyor" ancak sütun gerçekten bağlıysa bir
    ölçümdür. Katsayı elle değiştirildiğinde tahmin değişmeli; değişmiyorsa
    sütun ölüdür ve bulgu ölçümden değil bağlanmamış koddan gelir.
    """
    from spor_toto.recalibrate import KalibreTahminci, _mac_ozellikleri

    h = korpus_haftalari(sezonlar_=["2425"], bahisci_gerekli=True)
    hafta = next(x for x in h
                 if any(o["ayrisma"] > 0.02 for o in x["ozellikler"]))

    t = KalibreTahminci("dagilim"); t.egit(h)
    once = t.tahmin(hafta)
    t._theta[-1] += 20.0
    sonra = t.tahmin(hafta)
    assert once != sonra, "ayrisma sutunu tahmini hic etkilemiyor — olu sutun"

    # Ayrismasi sifir olan mac degismemeli.
    for i, satir in enumerate(_mac_ozellikleri(hafta)):
        if satir["ayrisma"] == 0.0:
            assert once[i] == pytest.approx(sonra[i])


def test_kupon_haftasinda_ayrisma_notr():
    from spor_toto.evaluate import olculebilir_haftalar
    from spor_toto.recalibrate import _mac_ozellikleri
    for o in _mac_ozellikleri(olculebilir_haftalar()[0]):
        assert o["ayrisma"] == 0.0


# ─── bulgular ─────────────────────────────────────────────────────────────────

def test_pinnacle_kolektifi_geciyor(a2):
    """**A2'nin birinci bulgusu** — projede referansı geçen ilk tahminci.

    Pinnacle'ın "keskin" olduğu bahis literatürünün en bilinen iddiasıdır.
    Burada ölçülüyor: aynı kesitte, aynı maçlarda, tek başına `PS` kapanışı
    kolektif ortalamayı geçmeli.

    Bu bir model başarısı **değildir** — bir kaynak seçimi bulgusudur ve asıl
    söylediği şey referans çizgimizin biraz yumuşak olduğudur.
    """
    from spor_toto.evaluate import bootstrap_farki, degerlendir

    ps = degerlendir(lambda: BahisciTahminci("b_PS"), a2)
    kolektif = degerlendir(PiyasaTahminci, a2)
    assert ps["brier"] < kolektif["brier"]
    assert ps["log_kaybi"] < kolektif["log_kaybi"]

    fark = bootstrap_farki(ps["_kayitlar"], kolektif["_kayitlar"])
    assert fark["ust"] < 0, f"ps kolektifi gecmedi: {fark}"


def test_b365_kolektifi_gecmiyor(a2):
    """Her bahisçi keskin değil — bulgu `PS`'e özgü, "tekil kaynak" genellemesi değil."""
    from spor_toto.evaluate import bootstrap_farki, degerlendir

    b365 = degerlendir(lambda: BahisciTahminci("b_B365"), a2)
    kolektif = degerlendir(PiyasaTahminci, a2)
    fark = bootstrap_farki(b365["_kayitlar"], kolektif["_kayitlar"])
    assert fark["ust"] > 0, "b365 de kolektifi geciyor — bulgu PS'e ozgu degil"


def test_ham_ayrisma_iliskisi_karisik(a2):
    """**A2'nin ikinci bulgusunun yarısı**: ham tablo yanıltıcı.

    Anlaşmazlık arttıkça kolektifin Brier'i *düşüyor* — sanki anlaşmazlık
    doğruluk müjdeliyor. Ama aynı yönde favori gücü de artıyor ve güçlü
    favorili maçların Brier'i zaten mekanik olarak düşüktür.
    """
    ozet = ayrisma_ozeti(a2)
    bantlar = ozet["bantlar"]
    kucuk = bantlar[f"<{AYRISMA_BANTLARI[0]:.2f}"]
    buyuk = bantlar[f">={AYRISMA_BANTLARI[-1]:.2f}"]
    assert buyuk["kolektif_brier"] < kucuk["kolektif_brier"]
    assert buyuk["ort_p_favori"] > kucuk["ort_p_favori"], (
        "karisma yok — ham tablo dogrudan okunabilir demektir, bulgu degismis")


def test_favori_sabitlenince_iliski_kayboluyor(a2):
    """**A2'nin ikinci bulgusunun diğer yarısı** ve asıl sonucu.

    Favori gücü dilim içinde sabitlendiğinde anlaşmazlık ile Brier arasındaki
    ilişki kayboluyor. Yani ham sinyal bir yanılsamaydı.

    Bu, T5 ve A1'in nullundan **farklı bir null**: orada ham sinyal gerçekti
    ve piyasa onu fiyatlamıştı. Burada ham sinyalin kendisi yok.
    """
    capraz = ayrisma_ozeti(a2)["favori_sabit"]
    denetlenen = 0
    for dilim, hucreler in capraz.items():
        degerler = [h["kolektif_brier"] for h in hucreler.values()]
        if len(degerler) < 2:
            continue
        denetlenen += 1
        assert max(degerler) - min(degerler) < 0.02, (
            f"{dilim} diliminde ayrisma hala fark yaratiyor: {hucreler}")
    assert denetlenen >= 3, "capraz tablo cok seyrek — karisma acilamadi"


def test_anlasmazlik_guveni_kismiyor(a2):
    """**A2'nin ikinci bulgusu**, katsayı tarafından.

    Model anlaşmazlığa baktı (sütun bağlı, bkz.
    `test_dagilim_sutunu_gercekten_calisiyor`) ve ortalama anlaşmazlıkta
    kolektife duyduğu güveni kayda değer biçimde değiştirmedi.

    Eşik %2 — dar değil, çünkü denetlenen şey kesin bir sayı değil bir
    **büyüklük mertebesi**.
    """
    k = dagilim_katsayisi(a2)
    assert k["beta"] > 0.5, "sicaklik katsayisi anlamsiz — model bozuk"
    assert abs(k["kisma"]) < 0.02, (
        f"anlasmazlik guveni %{100 * k['kisma']:.2f} kisiyor — bulgu degismis")
