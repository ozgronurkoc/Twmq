"""Geri test — strateji, kaplama ve skorlamanın denetimi.

Buradaki testlerin çoğu **sentetik** haftalar kullanır: gerçek veri setinde
küme içi kalan hafta neredeyse hiç yok (bulgunun kendisi bu), o yüzden
skorlamanın doğruluğu ancak sonucu bilinen kurgu haftalarla kanıtlanabilir.
"""

import itertools

import pytest

from spor_toto.backtest import (
    BANKO_IZGARA,
    UCLU_IZGARA,
    UZAY_SINIRI,
    VARSAYILAN_BUTCE_TL,
    _hafta_calistir,
    _wilson,
    backtest,
    butce_kolon,
    esik_secici,
    esik_taramasi,
    hafta_girdileri,
    hedef_secici,
    holdout,
    izgara_tablosu,
    secici_uret,
    secim_uret,
)
from spor_toto.history import MATCH_COUNT
from spor_toto.odds import load_odds

KUVVETLI = {"1": 0.90, "0": 0.05, "2": 0.05}
ORTA = {"1": 0.45, "0": 0.35, "2": 0.20}
BELIRSIZ = {"1": 0.35, "0": 0.34, "2": 0.31}


def _girdi(results: str, probs) -> dict:
    return {
        "week": 99, "close_date": "2026-01-01", "results": results,
        "probs": list(probs), "missing": 0, "usable": True,
    }


# ─── strateji ─────────────────────────────────────────────────────────────────

def test_secim_esige_gore_banko_cifte_uclu():
    assert secim_uret(KUVVETLI, 0.68, 0.38) == ["1"]
    assert secim_uret(ORTA, 0.68, 0.38) == ["1", "0"]
    assert secim_uret(BELIRSIZ, 0.68, 0.38) == ["1", "0", "2"]


def test_secim_kupon_duzeninde_siralanir():
    """Çifte '01' değil '10' yazılır — kupon düzeni alfabetik değildir."""
    assert secim_uret({"1": 0.45, "0": 0.40, "2": 0.15}, 0.68, 0.0) == ["1", "0"]
    assert secim_uret({"2": 0.45, "0": 0.40, "1": 0.15}, 0.68, 0.0) == ["0", "2"]


def test_anlamsiz_esik_ciftinde_bile_tanimli():
    """banko <= uclu verilse bile önce banko sorulur, çıktı tanımlı kalır."""
    assert secim_uret(KUVVETLI, 0.30, 0.80) == ["1"]
    assert secim_uret(ORTA, 0.99, 0.99) == ["1", "0", "2"]


# ─── skorlama ─────────────────────────────────────────────────────────────────

def test_kume_ici_hafta_15_tutturur():
    """13 doğru banko + sonucu içeren 2 çifte: 4 kolon, küme içi, 15 doğru.

    **Sayı 2'den 4'e çıktı ve sebebi ölçüm değil YAPI.** Kaplama döneminde
    iki çifteyi bir hata payıyla örtmek 2 kolona yetiyordu (`2² = 4` noktanın
    yarıçap-1 topları); düzde örtme diye bir şey yok, seçim kümesinin
    tamamı oynanır ve o da `2² = 4` kolondur. Testin geri kalanı aynen
    duruyor: küme içi, kaçak yok, en iyi kolon 15.
    """
    h = _hafta_calistir(_girdi("1" * 13 + "10", [KUVVETLI] * 13 + [ORTA, ORTA]),
                        esik_secici(0.68, 0.38))
    assert h["banko"] == 13 and h["double"] == 2 and h["triple"] == 0
    assert h["columns"] == 2 ** h["double"] * 3 ** h["triple"] == 4
    assert h["in_set"] is True
    assert h["misses"] == 0 and h["miss_at"] == []
    assert h["best"] == MATCH_COUNT
    assert h["guaranteed"] is True


def test_tek_kacak_14e_duser_ve_yeri_raporlanir():
    girdi = _girdi("1" * 12 + "2" + "10", [KUVVETLI] * 13 + [ORTA, ORTA])
    h = _hafta_calistir(girdi, esik_secici(0.68, 0.38))
    assert h["in_set"] is False
    assert h["misses"] == 1 and h["miss_at"] == [13]
    assert h["best"] == MATCH_COUNT - 1


def test_iki_kacak_13e_duser():
    girdi = _girdi("1" * 11 + "22" + "10", [KUVVETLI] * 13 + [ORTA, ORTA])
    h = _hafta_calistir(girdi, esik_secici(0.68, 0.38))
    assert h["misses"] == 2 and h["miss_at"] == [12, 13]
    assert h["best"] == MATCH_COUNT - 2


def test_kacak_numaralari_1_tabanli_ve_sirali():
    girdi = _girdi("2" + "1" * 12 + "10", [KUVVETLI] * 13 + [ORTA, ORTA])
    h = _hafta_calistir(girdi, esik_secici(0.68, 0.38))
    assert h["miss_at"] == [1]


def test_uzay_siniri_asilirsa_hafta_atlanir():
    """15 üçlü = 14,3 M nokta. Doğrulanamayacak bedel raporlanmaz."""
    h = _hafta_calistir(_girdi("1" * 15, [BELIRSIZ] * 15),
                        esik_secici(0.99, 0.99))
    assert h["skipped"] is True
    assert str(UZAY_SINIRI) in h["reason"].replace(",", "")


def test_kume_ici_hafta_TAM_15_tutturur():
    """Düzde küme içi kalan hafta 15 tutturur — alt sınır değil eşitlik.

    Kaplama döneminde bu test `best >= 14` diyordu, çünkü orada en iyi kolon
    bir **alt sınırdı** ve motor küme içinde en fazla 1 hataya izin
    veriyordu. Düzde seçim kümesinin tamamı oynanıyor: küme içi bir haftada
    her maçı tutturan bir kolon **vardır**.
    """
    h = _hafta_calistir(_girdi("1" * 5 + "0" * 5 + "1" * 5,
                               [ORTA] * 15), esik_secici(0.68, 0.0))
    assert h["double"] == 15 and h["guaranteed"] is True
    assert h["in_set"] is True
    assert h["best"] == MATCH_COUNT


# ─── strateji secimi ──────────────────────────────────────────────────────────

def test_varsayilan_strateji_URUNUN_kurali():
    """Geri testin varsayılanı ürünün kullandığı kural olmalı.

    Uzun süre değildi: `backtest` yalnızca `secim_uret`i (iki eşikli mekanik
    seçim) koşuyordu ve README §1.1'in başlangıç çizgisi oradan yazılmıştı.
    Ürün ise `secim.en_iyi_secim` ile kupon kuruyor. Ölçülen kural ile
    oynanan kuralın ayrışması, bu depoda sessizce yanlışlanan sayıların en
    pahalı kaynağıydı.
    """
    secici = secici_uret()
    hedef = hedef_secici()
    girdi = _girdi("1" * 15, [ORTA] * 15)
    assert _hafta_calistir(girdi, secici) == _hafta_calistir(girdi, hedef)


def test_bilinmeyen_strateji_SESSIZCE_varsayilana_dusmez():
    with pytest.raises(ValueError, match="Bilinmeyen strateji"):
        secici_uret("yok")
    with pytest.raises(ValueError, match="Bilinmeyen strateji"):
        backtest(sweep=False, strateji="yok")


@pytest.mark.parametrize("butce", [None, 0, -100, 5.0])
def test_hedef_kurali_BUTCESIZ_kurulamaz(butce):
    """Tavansız aramanın cevabı dejeneredir: hepsi üçlü, 3^15 kolon.

    `secim.en_iyi_secim` bunu zaten reddediyor; geri test de reddetmeli,
    çünkü sessizce 14 milyon kolonluk bir tablo üretmek en kötü seçenek.
    Son durum (₺5) ayrı bir kapı: bütçe pozitif ama tek kolonu bile
    almıyor (kolon bedeli ₺10).
    """
    with pytest.raises(ValueError):
        hedef_secici(butce)


def test_butce_merdiveni_karneyi_KAPSAR():
    """Geri testin bütçe merdiveni para karnesinin bütün basamaklarını içermeli.

    Para ekseni (gerçek ikramiye ROI'si) `karne.BUTCELER` basamaklarında
    ölçülüyor. Merdiven onları içermezse kademe isabeti ile para karşılığı
    **aynı parayı anlatmayı bırakır** ve README §1.1'in "ikisi aynı
    koşumdan geliyor" cümlesi sessizce yanlışlanır.

    Eşitlik değil kapsama aranıyor: varsayılan tavan ₺210.000'e çıkınca
    merdivene ₺5.000 ile tavan arasını okunur kılan basamaklar eklendi.
    Sabit `karne`den içe aktarılmıyor — o 2.000 satırlık bir ölçüm modülü ve
    API'nin soğuk açılışında yalnız bir demet için yüklenmesi gereksiz;
    bedeli kopya değil, bu bekçi ödüyor.
    """
    from spor_toto.backtest import BUTCE_IZGARA
    from spor_toto.karne import BUTCELER

    assert set(BUTCELER) <= set(BUTCE_IZGARA), (
        f"karne basamakları merdivende yok: {sorted(set(BUTCELER) - set(BUTCE_IZGARA))}")
    assert VARSAYILAN_BUTCE_TL in BUTCE_IZGARA, (
        "varsayılan tavan merdivende yoksa taramanın tepesi ürünün "
        "çalıştığı noktayı göstermiyor demektir")
    assert list(BUTCE_IZGARA) == sorted(BUTCE_IZGARA), "merdiven artan olmalı"


def test_tavan_sekli_sabitler_ama_plani_SABITLEMEZ():
    """Varsayılan tavanda şekil her hafta aynı, plan her hafta farklı.

    ₺210.000 = 21.000 kolon; altındaki en geniş kapsama 9 üçlü + 6 banko
    (`3^9 = 19.683`), çünkü üçlünün kaçağı sıfırdır ve optimizasyon bütçe
    elverdiğince üçlü alır. Şekil bu yüzden sabittir.

    **Ama kural körleşmiyor** ve bunu söylemek önemli: hangi altı maçın
    banko olacağı oranlardan gelir. Şekil sabit, plan değil — bu test tam
    olarak o ayrımı çiviliyor, çünkü "tavan yükseldi, motor artık haftayı
    okumuyor" cümlesi kurulması kolay ve YANLIŞ bir cümledir.
    """
    r = backtest(sweep=False)
    kosan = [h for h in r["weeks"] if not h["skipped"]]
    assert len(kosan) > 10
    sekiller = {(h["banko"], h["double"], h["triple"]) for h in kosan}
    assert sekiller == {(6, 0, 9)}, f"beklenmeyen şekil: {sekiller}"
    planlar = {tuple(h["picks"]) for h in kosan}
    assert len(planlar) == len(kosan), "planlar haftaya göre değişmeli"


def test_butce_kolona_ASAGI_yuvarlanir():
    """Bütçenin üstüne çıkan bir plan oynanamaz."""
    assert butce_kolon(2000.0) == 200
    assert butce_kolon(2009.0) == 200
    assert butce_kolon(10.0) == 1


def test_hedef_kurali_butceyi_ASMAZ():
    """Üretilen kupon, verilen tavanın altında kalmalı — her hafta."""
    kolon = butce_kolon(2000.0)
    for g in hafta_girdileri():
        if not g["usable"]:
            continue
        h = _hafta_calistir(g, hedef_secici(2000.0))
        assert not h["skipped"]
        assert h["columns"] <= kolon, f"{h['week']}. hafta tavanı aştı"


# ─── Wilson ───────────────────────────────────────────────────────────────────

def test_wilson_sinirlari_araligi_asmaz():
    for basari, n in ((0, 36), (36, 36), (3, 36), (1, 2)):
        lo, hi = _wilson(basari, n)
        assert 0.0 <= lo <= hi <= 1.0
    assert _wilson(0, 0) == (0.0, 0.0)


def test_wilson_kenarda_bile_daralir():
    """40/41'de normal yaklaşım 1'i aşardı; Wilson aşmaz."""
    lo, hi = _wilson(40, 41)
    assert hi <= 1.0 and lo > 0.8


# ─── sezon (gerçek veri) ──────────────────────────────────────────────────────

pytestmark_veri = pytest.mark.skipif(
    not load_odds(), reason="oran arşivi yok (scripts/build_odds.py)"
)


@pytestmark_veri
def test_girdiler_oransiz_haftayi_eler():
    girdiler = hafta_girdileri()
    assert girdiler
    for g in girdiler:
        assert len(g["probs"]) == MATCH_COUNT
        # Doktrin 2: eksik oranlı hafta tamamlanmaz, elenir.
        assert g["usable"] == (g["missing"] == 0 and len(g["results"]) == MATCH_COUNT)
    assert any(not g["usable"] for g in girdiler), "milli maç haftaları elenmeliydi"


@pytestmark_veri
def test_sezon_ozeti_tutarli():
    r = backtest(sweep=False)
    s = r["season"]
    assert s["weeks"] == r["meta"]["weeks_used"] - s["skipped"]
    assert s["hit15"] <= s["hit14"] <= s["hit13"] <= s["hit12"] <= s["weeks"]
    # Duzde `en iyi kolon = 15 - kacak`, yani kume ici hafta TAM 15 tutturur.
    # Kaplama doneminde bu satir `<= hit14` idi ve orada dogruydu: en iyi
    # kolon bir alt sinirdi. Sinir esitlige donunce degismez de siklasti.
    assert s["in_set"] <= s["hit15"], "düzde küme içi hafta 15 tutturmalı"
    assert s["columns_total"] == sum(h["columns"] for h in r["weeks"] if not h["skipped"])
    lo, hi = s["hit14_ci"]
    assert lo <= s["hit14_pct"] <= hi
    lo12, hi12 = s["hit12_ci"]
    assert lo12 <= s["hit12_pct"] <= hi12
    # Bedel TL olarak da yazilmali: kolon adedi tek basina okunamaz.
    assert s["tl_avg"] == round(r["meta"]["kolon_bedeli_tl"] * s["columns_avg"], 2)
    assert r["warning"]


@pytestmark_veri
def test_kademe_dagilimi_birikimliyle_TUTARLI():
    """Tam kademe kırılımı, birikimli sayılarla ve hafta sayısıyla örtüşmeli.

    `hit12` "12 ve üstü" demektir ve içinde 15'ler de vardır. İkramiye
    tablosunda 15 ile 12 arasında binlerce kat fark olduğu için birikimli
    sayı tek başına yanıltır: %93 "12+" ile %13 "15" aynı cümlede
    okunmalıdır. Kırılım o yüzden gövdede duruyor — ama birikimliyle
    ayrışırsa ikisinden biri yalan söylüyor demektir.
    """
    s = backtest(sweep=False)["season"]
    d = s["kademe_dagilimi"]
    assert sum(d.values()) == s["weeks"], "kırılım hafta sayısını toplamalı"
    assert d["15"] == s["hit15"]
    assert d["15"] + d["14"] == s["hit14"]
    assert d["15"] + d["14"] + d["13"] == s["hit13"]
    assert d["15"] + d["14"] + d["13"] + d["12"] == s["hit12"]
    assert d["alt"] == s["weeks"] - s["hit12"]
    yuzde = s["kademe_dagilimi_pct"]
    assert set(yuzde) == set(d)
    assert abs(sum(yuzde.values()) - 100.0) < 0.5


@pytestmark_veri
def test_butce_taramasi_MONOTON_ve_hold_out_yok():
    """Bütçe arttıkça isabet düşemez; ve burada hold-out'un işi yoktur.

    İki ayrı iddia, ikisi de yapısal:

    1. Daha büyük tavan, daha küçük tavanın bulduğu her planı da
       kapsıyor — yani `P(k ≤ 3)` düşemez. Gerçekleşen isabet de bu
       kesitte düşmemeli; düşerse aramada bir kusur var demektir.
    2. `hedef` kuralında ayarlanan bir parametre yok (optimizasyon sonucu
       GÖRMEZ), dolayısıyla hold-out'un koruduğu aşırı uyum riski de yok.
       Bütçe veriden çıkarılmaz, bir **harcama kararıdır**.
    """
    r = backtest(sweep=True)
    assert r["holdout"]["weeks"] == 0, "hedef kuralında hold-out anlamsız"
    assert not r["sweep"], "hedef kuralında eşik taraması anlamsız"
    tarama = r["butce_sweep"]
    assert len(tarama) >= 2
    for onceki, sonraki in itertools.pairwise(tarama):
        assert sonraki["butce_tl"] > onceki["butce_tl"]
        assert sonraki["hit12"] >= onceki["hit12"]
        assert sonraki["columns_avg"] >= onceki["columns_avg"]


@pytestmark_veri
def test_tum_kesit_tek_sezondan_GENIS():
    """`sezon="hepsi"` ölçüm kesitinin tamamını verir, tek sezonu değil."""
    dar = backtest(sweep=False)["season"]["weeks"]
    genis = backtest(sweep=False, sezon="hepsi")["season"]["weeks"]
    assert genis > dar, "geniş kesit dar olanı içine almalı"


@pytestmark_veri
def test_dilim_daha_az_hafta_calistirir():
    tam = backtest(sweep=False)["meta"]["weeks_available"]
    dilim = backtest(last=6, sweep=False)["meta"]["weeks_available"]
    assert dilim == 6 < tam


@pytestmark_veri
def test_tarama_izgarayi_kapsar_ve_tablo_paylasilir():
    girdiler = hafta_girdileri()
    tablo = izgara_tablosu(girdiler)
    tarama = esik_taramasi(girdiler, tablo=tablo)
    assert len(tarama) == len(BANKO_IZGARA) * len(UCLU_IZGARA)
    for satir in tarama:
        assert satir["banko"] in BANKO_IZGARA and satir["uclu"] in UCLU_IZGARA
        assert satir["hit14"] <= satir["weeks"]
        assert satir["weeks"] + satir["skipped"] == len(tablo[(satir["banko"], satir["uclu"])])


@pytestmark_veri
def test_holdout_taramadan_iyi_olamaz():
    """Aşırı uyumun ölçüsü: hold-out, taramanın en iyisini geçemez."""
    girdiler = hafta_girdileri()
    tablo = izgara_tablosu(girdiler)
    tarama = esik_taramasi(girdiler, tablo=tablo)
    ho = holdout(girdiler, tablo=tablo)
    assert ho["olcut"] == "hit12", "manşet ölçüt ikramiye kademesi olmalı"
    en_iyi = max(s["hit12"] for s in tarama)
    assert ho["hit12"] <= en_iyi
    assert ho["chosen"], "hangi eşiğin seçildiği raporlanmalı"


# ─── hold-out paydaları ───────────────────────────────────────────────────────
#
# `holdout` iki farklı paydaya dayanıyor ve ikisi de görünmek zorunda:
# kesit (`weeks`) ile gerçekten ölçülen kat (`olculen`). Döngü, dışarıda
# bırakılan hafta arama uzayı yüzünden `skipped` ise o katı ölçmeden geçer.

@pytestmark_veri
def test_holdout_paydalari_tutarli():
    girdiler = hafta_girdileri()
    ho = holdout(girdiler)
    assert ho["olculen"] + ho["atlanan"] == ho["weeks"]
    assert ho["olculen"] == sum(c["weeks"] for c in ho["chosen"]), (
        "olculen kat sayisi, secilen esiklerin toplamiyla ayni olmali")
    # Hangi metrigin hangi paydaya dayandigi cikitida YAZILI olmali.
    assert set(ho["payda"]) == {"hit12", "columns_avg"}


def test_holdout_kolon_ortalamasi_olculen_kata_bolunur():
    """Atlanan kat varken `columns_avg`, kesite değil **ölçülene** bölünür.

    Düzeltilen kusur budur ve **gerçek veriyle bugün görünmez**: 36
    haftalık kesitte kazanan eşik çifti (0,68/0,38) hiçbir haftayı
    atlamıyor, yani `kolon / n` ile `kolon / olculen` aynı sayıyı veriyor.
    Kusur gizliydi — bir hafta arama uzayına takıldığı anda pay yalnızca
    ölçülen katlarda birikirken payda bütün kesiti saymaya devam ediyor ve
    ortalama kolon **olduğundan düşük** çıkıyordu.

    Gizli olması güvenli olduğu anlamına gelmiyor: eşitliği ucuz kolon
    lehine bozulan çiftlerden biri hafta atlıyorsa, veri bir tık kaydığı
    anda atlayan çift kazanır ve ortalama sessizce düşer.

    Kurgu tabloyla ölçülmesinin sebebi bu: eşik ızgarasında `uclu = 0,0`
    satırı olduğu için sentetik bir haftayı BÜTÜN çiftlerde atlatmak
    mümkün değil (çifte kalır, 2^15 = 32.768 < `UZAY_SINIRI`). Ölçülmek
    istenen şey eşik seçimi değil zaten, **payda**.

    `olcut` burada AÇIKÇA `hit14` veriliyor. Ölçülen şey payda olduğu için
    hangi kademeye bakıldığı önemsiz; açık vermek testi manşet ölçütün
    varsayılanından ayırıyor, yani varsayılan bir daha değişirse bu test
    sessizce başka bir şey ölçmeye başlamıyor.
    """
    girdiler = [{"usable": True} for _ in range(5)]
    anahtar = (0.68, 0.38)
    # Dordu olculebilir, biri arama uzayina takilmis.
    tablo = {anahtar: [
        {"skipped": False, "best": 13, "columns": 100},
        {"skipped": False, "best": 14, "columns": 200},
        {"skipped": False, "best": 12, "columns": 300},
        {"skipped": False, "best": 13, "columns": 400},
        {"skipped": True, "reason": f"seçim uzayı > {UZAY_SINIRI:,}"},
    ]}

    ho = holdout(girdiler, tablo=tablo, olcut="hit14")
    assert ho["weeks"] == 5 and ho["olculen"] == 4 and ho["atlanan"] == 1
    assert ho["columns_total"] == 1000
    # Eski davranis `1000 / 5 = 200,0` derdi; dogrusu `1000 / 4 = 250,0`.
    assert ho["columns_avg"] == 250.0
    # `hit14` paydasi BILEREK kesit: olculemeyen hafta iska sayilir, cunku
    # paydadan dusmek stratejinin cozemedigi haftalari yok saymak olurdu.
    assert ho["hit14"] == 1
    assert ho["hit14_pct"] == round(100 * 1 / 5, 1)


def test_holdout_atlanan_yoksa_iki_payda_ayni():
    """Atlanan kat yokken eski ve yeni payda aynı sayıyı verir.

    Düzeltmenin yayımlanmış sayıyı değiştirmediğinin kanıtı: fark yalnızca
    atlanan kat varken doğuyor.
    """
    girdiler = [{"usable": True} for _ in range(4)]
    tablo = {(0.68, 0.38): [
        {"skipped": False, "best": 13, "columns": 100} for _ in range(4)]}
    ho = holdout(girdiler, tablo=tablo)
    assert ho["atlanan"] == 0
    assert ho["columns_avg"] == round(ho["columns_total"] / ho["weeks"], 1)


@pytestmark_veri
def test_hicbir_hafta_garantisiz_kalmaz():
    r = backtest(sweep=False)
    for h in r["weeks"]:
        if h["skipped"]:
            continue
        assert h["guaranteed"], f"{h['week']}. hafta kaplaması açık nokta bıraktı"
        assert h["banko"] + h["double"] + h["triple"] == MATCH_COUNT
        assert len(h["picks"]) == MATCH_COUNT
