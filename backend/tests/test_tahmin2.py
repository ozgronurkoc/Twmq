"""**2. Tahmin** — kalabalık ayarı, bağımsız görüş ve ikinci kayıt.

Buradaki testler bulguları değil **sözleşmeleri** korur. Üç tanesi
doğrudan bu iş sırasında yakalanan hatalara bağlı ve niçin var oldukları
kendi gövdelerinde yazıyor:

* `test_ayar_isaret_sayilarini_korur` — ayar bedeli değiştirirse "aynı
  kupon, başka sembol" cümlesi yalan olur.
* `test_kacak_dagilimi_secimden_okunur` — `kacak_olasiligi` en olası `k`
  sembolü varsayar; kalabalık ayarı o varsayımı bilerek bozuyor.
* `test_yan_kayit_hafta_sanilmaz` — `hafta_02_tahmin2.json` eklendiğinde
  sezon defteri 2. haftayı **iki kez** saydı ve arayüz beslemesi "3 hafta"
  yazdı. Kalıp kapatıldı; bekçisi burada.
"""

import importlib
import json
from pathlib import Path

import pytest

from spor_toto.core import SEMBOLLER
from spor_toto.getiri import kalabalik_kademeleri
from spor_toto.gorus import coz, sadelestir, takim_havuzu
from spor_toto.ortak import kacak_dagilimi
from spor_toto.secim import hedef_olasiligi, kalabalik_ayari

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data" / "super_toto" / "2026_27"

pytestmark = pytest.mark.skipif(
    not (VERI / "hafta_02.json").exists(),
    reason="super toto hafta verisi yok")


@pytest.fixture(scope="module")
def t2():
    return importlib.import_module("scripts.super_toto_tahmin2")


@pytest.fixture(scope="module")
def govde(t2):
    """2. haftanın gövdesi. Tarih SABIT — testin tek belirsiz alanı buydu."""
    return t2.uret("2026_27", 2, tarih="2026-08-24")


def _dagilim(*p: float) -> dict[str, float]:
    return dict(zip(SEMBOLLER, p))


# ─── kalabalık ayarı ──────────────────────────────────────────────────────

def test_ayar_isaret_sayilarini_korur():
    """Ayar HANGI sembolü sorar, KAÇ sembolü değil.

    Sayılar değişseydi bedel de değişirdi ve "aynı kolon, aynı satır, aynı
    motor" cümlesi doğru olmazdı — yani ayar bedava olmaktan çıkardı.
    """
    probs = [_dagilim(0.40, 0.30, 0.30) for _ in range(15)]
    oynanma = [_dagilim(0.70, 0.15, 0.15) for _ in range(15)]
    taban = [["1", "0"] for _ in range(15)]
    ayar = kalabalik_ayari(probs, oynanma, taban, 0.20)
    assert [len(s) for s in ayar.secimler] == [2] * 15


def test_ayar_kayip_butcesini_asmaz():
    probs = [_dagilim(0.50, 0.28, 0.22) for _ in range(15)]
    oynanma = [_dagilim(0.80, 0.10, 0.10) for _ in range(15)]
    taban = [["1", "0"] for _ in range(15)]
    for kayip in (0.0, 0.02, 0.10):
        ayar = kalabalik_ayari(probs, oynanma, taban, kayip)
        assert ayar.p_hedef >= (1 - kayip) * ayar.taban_p_hedef - 1e-12


def test_ayar_sifir_butcede_hedefi_dusurmez():
    """`kayip_orani=0` bir kapıdır: hedef bir puan bile harcanamaz."""
    probs = [_dagilim(0.50, 0.28, 0.22) for _ in range(15)]
    oynanma = [_dagilim(0.80, 0.10, 0.10) for _ in range(15)]
    taban = [["1", "0"] for _ in range(15)]
    ayar = kalabalik_ayari(probs, oynanma, taban, 0.0)
    assert ayar.p_hedef >= ayar.taban_p_hedef - 1e-12


def test_ayar_gercekten_kalabaliktan_kacar():
    """Olasılığı **denk**, kalabalığı ayrık iki küme: ayar az oynananı seçer.

    Kurgu bilerek uç: `0` ile `2` aynı olasılığı taşıyor, dolayısıyla
    hedeften hiçbir şey harcanmıyor; tek fark oynanma payı.
    """
    probs = [_dagilim(0.50, 0.25, 0.25) for _ in range(15)]
    oynanma = [_dagilim(0.50, 0.45, 0.05) for _ in range(15)]
    taban = [["1", "0"] for _ in range(15)]
    ayar = kalabalik_ayari(probs, oynanma, taban, 0.0)
    assert all(s == ["1", "2"] for s in ayar.secimler)
    assert ayar.oran > ayar.taban_oran
    assert len(ayar.degisimler) == 15


def test_ayar_kalabalik_ayrismiyorsa_tabanda_kalir():
    probs = [_dagilim(0.50, 0.30, 0.20) for _ in range(15)]
    # Oynanma piyasayla birebir: sapacak yer yok.
    ayar = kalabalik_ayari(probs, list(probs), [["1", "0"] for _ in range(15)],
                           0.10)
    assert ayar.degisimler == []
    assert ayar.p_hedef == pytest.approx(ayar.taban_p_hedef)


def test_ayar_bozuk_kayip_oranini_reddeder():
    probs = [_dagilim(0.5, 0.3, 0.2) for _ in range(15)]
    with pytest.raises(ValueError):
        kalabalik_ayari(probs, probs, [["1"] for _ in range(15)], 1.0)


# ─── kaçak dağılımı ───────────────────────────────────────────────────────

def test_kacak_dagilimi_secimden_okunur(t2):
    """Kaçak, işaretlenen KÜMEDEN hesaplanır; `len(sec)`ten değil.

    `secim.kacak_olasiligi` en olası `k` sembolü varsayar. Kalabalık ayarı
    aynı boyutta BAŞKA bir küme işaretleyebilir; seviyeden hesaplanan sayı
    o planda gerçek olmaz. İlk sürüm tam bu hatayı yapıyordu.
    """
    probs = [_dagilim(0.60, 0.25, 0.15) for _ in range(15)]
    oynanma = [_dagilim(0.10, 0.10, 0.80) for _ in range(15)]
    # `10` yerine `12` isaretleniyor: ayni boyut, daha dusuk olasilik.
    secimler = [["1", "2"] for _ in range(15)]
    govde = t2._kupon_govdesi(probs, oynanma, secimler)
    beklenen = kacak_dagilimi([1 - 0.75] * 15)
    assert govde["p14"] == pytest.approx(beklenen[0])
    assert govde["p13"] == pytest.approx(beklenen[1])
    assert govde["p12"] == pytest.approx(beklenen[2])
    assert govde["p_hedef"] == pytest.approx(hedef_olasiligi(probs, secimler))


def test_kosullu_rakip_uclude_notrdur(t2):
    """Üçlü işaretlenen maç koşullandırmaya hiçbir şey katmaz.

    Sonuç zaten kesin kümenin içinde; "kazandık" bilgisi o maç hakkında
    bir şey söylemez ve çarpanı tam 1 olmalıdır.
    """
    probs = [_dagilim(0.5, 0.3, 0.2)]
    oynanma = [_dagilim(0.8, 0.1, 0.1)]
    k = t2._kosullu_rakip(probs, oynanma, [["1", "0", "2"]])
    assert k["kat"] == pytest.approx(1.0)


def test_kosullu_rakip_kalabalik_bankoda_buyur(t2):
    """Kalabalığın yığıldığı sembole banko koymak rakip yoğunluğunu artırır."""
    probs = [_dagilim(0.5, 0.3, 0.2)]
    oynanma = [_dagilim(0.9, 0.05, 0.05)]
    kalabalik = t2._kosullu_rakip(probs, oynanma, [["1"]])
    tenha = t2._kosullu_rakip(probs, oynanma, [["0"]])
    assert kalabalik["kat"] > tenha["kat"]


# ─── kalabalık modeli (getiri) ────────────────────────────────────────────

def test_oynanma_modeli_piyasayla_ayniysa_ornekleme_duser():
    """`orneklem`, `oynanma` modelinin `o = p` özel hâlidir.

    İkisi ayrışırsa yeni model eski varsayımın genellemesi olmaz, ayrı bir
    şey olur — ve o zaman kıyas edilemezdi.
    """
    probs = [_dagilim(0.5, 0.3, 0.2) for _ in range(15)]
    a = kalabalik_kademeleri(probs, "orneklem")
    b = kalabalik_kademeleri(probs, "oynanma", probs)
    assert a == pytest.approx(b)


def test_oynanma_modeli_pay_olmadan_calismaz():
    probs = [_dagilim(0.5, 0.3, 0.2) for _ in range(15)]
    with pytest.raises(ValueError):
        kalabalik_kademeleri(probs, "oynanma")


# ─── ad eşleme ────────────────────────────────────────────────────────────

def test_sadelestirme_turkce_yazimi_birlestirir():
    assert sadelestir("Kasımpaşa A.Ş.") == sadelestir("Kasimpasa")
    assert sadelestir("Göztepe A.Ş.") == "goztepe"


def test_lig_bir_kisittir():
    """Aynı ad başka ligde aranmaz — ligler arası eşleşme imkânsız."""
    havuz = takim_havuzu([
        {"lig": "T1", "ev": "Galatasaray", "dep": "Fenerbahce"},
        {"lig": "D1", "ev": "Dortmund", "dep": "Bayern Munich"},
    ])
    assert coz("Galatasaray A.Ş.", "T1", havuz) == "Galatasaray"
    assert coz("Galatasaray A.Ş.", "D1", havuz) is None


def test_bulanik_esleme_yok():
    """Alt dize eşlemesi ölçüldü ve %68'de kaldı; kapı kapalı kalmalı."""
    havuz = takim_havuzu([{"lig": "SC0", "ev": "Cove Rangers", "dep": "Celtic"}])
    assert coz("Rangers", "SC0", havuz) is None


def test_elle_tablosu_koprusu_kurar():
    havuz = takim_havuzu([{"lig": "D1", "ev": "Dortmund",
                           "dep": "Bayern Munich"}])
    assert coz("B. Dortmund", "D1", havuz) == "Dortmund"
    assert coz("Bayern Münih", "D1", havuz) == "Bayern Munich"


def test_karsiligi_olmayan_takim_uydurulmaz():
    havuz = takim_havuzu([{"lig": "T1", "ev": "Galatasaray",
                           "dep": "Fenerbahce"}])
    assert coz("Çorum FK", "T1", havuz) is None


# ─── marj duyarlılığı ─────────────────────────────────────────────────────

def test_marj_esitleme_hedef_marji_tutturur(t2):
    oranlar = {"1": 1.18, "0": 5.64, "2": 2.31}
    yeni = t2._marji_esitle(oranlar, 0.177)
    assert t2._marj(yeni) == pytest.approx(0.177)


def test_marj_esitleme_oranlarin_sirasini_bozmaz(t2):
    oranlar = {"1": 1.18, "0": 5.64, "2": 2.31}
    yeni = t2._marji_esitle(oranlar, 0.177)
    assert sorted(yeni, key=lambda s: yeni[s]) == sorted(
        oranlar, key=lambda s: oranlar[s])


# ─── gövde ────────────────────────────────────────────────────────────────

def test_kayit_sonuclari_gormeden_uretildi():
    """DİSKTEKİ kayıt sonuçlar görülmeden üretilmiş olmalı.

    Ölçünün öznesi bilerek diskteki dosya: `uret()` bugün çağrılırsa
    haftanın sonucu artık GİRİLMİŞTİR ve gövde `results_known: true`
    döner — bu doğru davranıştır, `yaz()` de o gövdeyi yazmayı reddeder
    (`test_sonuclari_bilinen_haftaya_ikinci_tahmin_yazilmaz`). Kaydın
    değeri, sonuç girilmeden önce donmuş olmasındadır ve bunu ancak
    dosyanın kendisi kanıtlar.
    """
    kayit = json.loads((VERI / "hafta_02_tahmin2.json").read_text(encoding="utf-8"))
    assert kayit["meta"]["results_known"] is False
    assert kayit["meta"]["frozen_at"] == "2026-08-24"


def test_govde_sonuc_girilince_bunu_ilan_eder(govde):
    """Sonuç girilmiş haftada gövde bunu SAKLAMAZ — yazım kapısı buna bakar."""
    assert govde["meta"]["results_known"] is True
    assert govde["meta"]["frozen_at"] == "2026-08-24"


def test_govde_on_bes_mac_tasir(govde):
    assert len(govde["matches"]) == 15
    for ad in ("esik", "taban", "ayarli"):
        assert len(govde["kupon"][ad]["picks"]) == 15


def test_ayarli_plan_tabanla_ayni_bedeldedir(govde):
    """Ayar bedava olmalı — kolon, satır ve motor değişmemeli."""
    taban, ayarli = govde["kupon"]["taban"], govde["kupon"]["ayarli"]
    assert taban["columns"] == ayarli["columns"]
    assert taban["rows"] == ayarli["rows"]
    assert taban["engine"] == ayarli["engine"]


def test_hedef_kurali_esik_kuralini_gecer(govde):
    """Aynı bütçede hedef kuralı eşiği geçmeli — geçmezse B0 bozulmuş demek."""
    k = govde["kupon"]
    assert k["taban"]["p_hedef"] >= k["esik"]["p_hedef"]
    assert k["taban"]["columns"] <= k["butce"]


def test_gorus_isaret_degistirmez(govde):
    """Bağımsız görüş kayda geçer, karar yoluna girmez.

    Bekçi doğrudan: işaretler yalnızca piyasa olasılığından kurulmuş
    plandan gelir; Dixon-Coles'un favorisi ayrıştığı maçlarda bile işaret
    piyasanın planına eşittir.
    """
    ayarli = govde["kupon"]["ayarli"]["picks"]
    for r in govde["matches"]:
        assert r["isaret"] == ayarli[r["no"] - 1]


def test_gorus_eslesmeyen_macta_susar(govde):
    for r in govde["matches"]:
        if not r["dc_var"]:
            assert r["dc"] is None
            assert r["elo_farki"] is None


def test_kiyas_eski_isaretleri_yeniden_secmez(govde):
    """Kıyas eski işaretleri **ölçer**, yeniden kurmaz."""
    kupon = json.loads(
        (VERI / "hafta_02_kupon.json").read_text(encoding="utf-8"))
    assert govde["kiyas"]["eski_picks"] == kupon["variants"][0]["picks"]


def test_sonuclari_bilinen_haftaya_ikinci_tahmin_yazilmaz(t2, tmp_path):
    govde = {"meta": {"results_known": True}}
    with pytest.raises(SystemExit):
        t2.yaz(govde, "2026_27", 2, tmp_path)


# ─── diskteki kayıt ───────────────────────────────────────────────────────

def test_diskteki_kayit_bayat_degil(t2, govde):
    """`hafta_02_tahmin2.json` bugünkü kodun ürettiğiyle aynı olmalı.

    Sessizce eskimiş bir kayıt, olmayan bir kayıttan kötüdür: arayüz onu
    "bugünkü aletlerle üretildi" diye gösterir. `frozen_at` dışarıda
    bırakılır — o, kaydın **donduğu** gündür ve kodla değişmez.
    """
    yol = VERI / "hafta_02_tahmin2.json"
    if not yol.exists():
        pytest.skip("2. tahmin kaydi yok")
    diskte = json.loads(yol.read_text(encoding="utf-8"))
    taze = json.loads(t2._metin(t2.uret("2026_27", 2,
                                        tarih=diskte["meta"]["frozen_at"])))
    # `results_known` dışarıda: kayıt sonuç girilmeden donduruldu, bugün
    # aynı haftanın sonucu BİLİNİYOR ve taze gövde bunu doğru şekilde
    # `true` yazıyor. Bu bir bayatlık değil, kaydın tanımı — flamanın
    # kendisi ayrı bir testte (`test_kayit_sonuclari_gormeden_uretildi`)
    # korunuyor. Geri kalan her alan birebir eşit olmak zorunda.
    for govde in (diskte, taze):
        govde["meta"].pop("results_known", None)

    # Havuz bloğu VARSAYIMA dayanır ve varsayım kaydın donduğu günden
    # sonra ÖLÇÜLDÜ: `getiri.VARSAYILAN_PAY` iki haftanın ikramiye
    # ekranından türetilen orana çevrildi (docs §3.40). Kayıt yeniden
    # hesaplanmaz; bunun yerine kaydın KENDİ varsayımını yazdığı
    # doğrulanır ve blok kıyastan çıkarılır. Kayıt varsayımını yazmıyorsa
    # bu bir bayatlık değil, izlenemezliktir — o zaman test kırılmalıdır.
    from spor_toto.getiri import VARSAYILAN_PAY
    kayitli = diskte["havuz"]["modeller"]["ayarli"]["favori"]["varsayimlar"]
    assert "pay_dagilimi" in kayitli, "kayıt hangi varsayımla konuştuğunu yazmalı"
    bugunku = {str(k): v for k, v in VARSAYILAN_PAY.items()}
    if kayitli["pay_dagilimi"] != bugunku:
        for govde in (diskte, taze):
            govde.pop("havuz", None)

    assert taze == diskte


def test_yan_kayit_hafta_sanilmaz():
    """`hafta_NN_tahmin2.json` bir hafta dosyası **değildir**.

    Sezon defteri önce yalnızca `_kupon` sonekini eliyordu; `_tahmin2`
    eklendiğinde 2. hafta iki kez sayıldı ve besleme "3 hafta" yazdı.
    """
    sezon = importlib.import_module("scripts.super_toto_sezon")
    haftalar = sezon.haftalari_bul("2026_27")
    assert haftalar == sorted(set(haftalar))
    assert 2 in haftalar
