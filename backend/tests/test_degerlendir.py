"""Sonuç sonrası değerlendirme — **ölçünün kendisinin** bekçileri.

Bu dosyadaki testler bulguları değil, bulguyu üreten hesabı korur. Bir
hafta kapandıktan sonra tek savunma budur: kupon kaydı dondurulmuştur,
sonuç dizisi girilmiştir ve ikisi arasındaki her sayı bu gövdeden çıkar.
Gövde sessizce kayarsa, geçmiş haftaların karnesi de sessizce değişir.

İki tür test var ve ikisi de gerekli:

* **Sentetik** — hesap doğru mu (sıralama kaba kuvvetle aynı mı, defter
  doğru mu sayıyor, ayar karnesi kazancı kayıptan ayırıyor mu).
* **Canlı kayıt** — 1. ve 2. haftanın ölçülmüş sonucu YERİNDE Mİ. Bu
  sayılar bir kez ölçüldü ve kayda geçti; kod değişikliği onları
  oynatıyorsa test kırılmalıdır.
"""

import importlib
import json
import math
from itertools import product
from pathlib import Path

import pytest

from spor_toto.core import SEMBOLLER

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data" / "super_toto" / "2026_27"

pytestmark = pytest.mark.skipif(
    not (VERI / "hafta_02.json").exists(),
    reason="super toto hafta verisi yok")


@pytest.fixture(scope="module")
def deg():
    return importlib.import_module("scripts.super_toto_degerlendir")


def _dagilim(*p: float) -> dict[str, float]:
    return dict(zip(SEMBOLLER, p))


def _hafta(probs, sonuc, play=None):
    """Değerlendiricinin okuduğu en küçük hafta gövdesi."""
    play = play or probs
    return {
        "meta": {"season": "test", "week": 0, "results": sonuc},
        "matches": [
            {"no": i + 1, "home": f"E{i}", "away": f"D{i}",
             "probs": p, "play": q, "odds_yok": False,
             "odds": {s: 1 / p[s] for s in SEMBOLLER}}
            for i, (p, q) in enumerate(zip(probs, play))
        ],
    }


# ─── gerçeğin sırası ──────────────────────────────────────────────────────

def test_sira_kaba_kuvvetle_ayni(deg):
    """Bölüp-birleştiren sayım, bütün kolonları gezen sayımla aynı olmalı.

    Asıl gövde 3^15 kolonu gezmiyor; log toplamlarını ikiye bölüp ikili
    aramayla sayıyor. Bu testin işi o kısayolun kaba kuvvetle **birebir**
    aynı cevabı verdiğini göstermek — küçük bir uzayda ikisi de koşulabilir.
    """
    probs = [_dagilim(0.5, 0.3, 0.2), _dagilim(0.2, 0.5, 0.3),
             _dagilim(0.6, 0.1, 0.3), _dagilim(0.25, 0.35, 0.40),
             _dagilim(0.45, 0.30, 0.25), _dagilim(0.15, 0.55, 0.30)]
    for gercek in ("111111", "021203", "202020"[:6], "012012"):
        if any(c not in SEMBOLLER for c in gercek):
            continue
        p_gercek = math.prod(p[g] for p, g in zip(probs, gercek))
        kaba = 1 + sum(
            1 for kolon in product(*[SEMBOLLER] * len(probs))
            if math.prod(p[s] for p, s in zip(probs, kolon)) > p_gercek + 1e-12)
        assert deg._sira(probs, gercek) == kaba


def test_sira_en_olasi_kolonda_birdir(deg):
    """En olası kolonun sırası 1'dir — bütçe okuması bu ankraja dayanır."""
    probs = [_dagilim(0.5, 0.3, 0.2)] * 5
    assert deg._sira(probs, "11111") == 1


def test_sira_esit_olasilikta_oynamaz(deg):
    """Oranı ilan edilmemiş maç 1/3–1/3–1/3'tür ve üç dalı EŞİTTİR.

    Tolerans olmasa kayan nokta bu eşitliği rastgele bozar ve aynı hafta
    her koşumda başka bir sıra üretirdi.
    """
    probs = [_dagilim(1 / 3, 1 / 3, 1 / 3)] * 6
    assert all(deg._sira(probs, k * 6) == 1 for k in SEMBOLLER)


def test_gercegin_sirasi_bir_butcedir(deg):
    """Sıra, uzayın içinde kalmalı ve gerçek kolonun olasılığını taşımalı."""
    probs = [_dagilim(0.5, 0.3, 0.2)] * 15
    d = _hafta(probs, "1" * 14 + "2")
    o = deg.gercegin_sirasi(d)
    assert o["uzay"] == 3 ** 15
    assert 1 < o["piyasa"]["sira"] <= o["uzay"]
    assert o["piyasa"]["p"] == pytest.approx(0.5 ** 14 * 0.2)


# ─── atılan sembol defteri ────────────────────────────────────────────────

def test_atilan_defteri_sayar_ve_bekler(deg):
    """Atılan sembol sayısı, gelen sayısı ve beklenen — üçü birden.

    Beklenen sütunu olmadan defter yanıltıcıdır: "attığım beraberliklerin
    yarısı geldi" cümlesi, piyasa zaten %50 diyorsa bir bulgu değildir.
    """
    probs = [_dagilim(0.5, 0.3, 0.2)] * 3
    d = _hafta(probs, "100")
    o = deg.atilan_defteri(d, ["1", "12", "12"])
    assert o["sembol"]["0"]["atildi"] == 3       # üç maçta da beraberlik atıldı
    assert o["sembol"]["0"]["geldi"] == 2        # 2. ve 3. maçta beraberlik geldi
    assert o["sembol"]["0"]["beklenen"] == pytest.approx(0.9)
    assert o["sembol"]["2"]["atildi"] == 1       # yalnızca banko maçta
    assert o["sembol"]["2"]["geldi"] == 0
    assert o["sembol"]["1"]["atildi"] == 0
    assert o["atildi"] == 4 and o["geldi"] == 2


def test_atilan_defteri_uclude_bos_kalir(deg):
    """Üçlü işaretlenmiş maç hiçbir sembol atmaz — deftere girmez."""
    d = _hafta([_dagilim(0.4, 0.3, 0.3)] * 2, "10")
    assert deg.atilan_defteri(d, ["102", "102"])["atildi"] == 0


# ─── kalabalık ayarı karnesi ──────────────────────────────────────────────

def test_ayar_karnesi_kazanci_kayiptan_ayirir(deg):
    """Ayar bir maçta kazanır, ötekinde kaybederse net SIFIRDIR.

    Karnenin işi ayarı savunmak değil; ne kazandırdığını ve ne
    kaybettirdiğini ayrı ayrı yazmak. İki sayı toplanıp tek "başarı"
    sayısına indirilseydi, ayarın gerçek etkisi (bölüşme) görünmezdi.
    """
    d = _hafta([_dagilim(0.4, 0.3, 0.3)] * 3, "100")
    kayit = {"kupon": {
        "ayar": {"degisimler": [
            {"no": 1, "taban": "02", "yeni": "12", "prob_taban": 0.6,
             "prob_yeni": 0.58, "oynanma_taban": 0.8, "oynanma_yeni": 0.7},
            {"no": 3, "taban": "10", "yeni": "12", "prob_taban": 0.7,
             "prob_yeni": 0.66, "oynanma_taban": 0.9, "oynanma_yeni": 0.8},
        ]},
        "taban": {"picks": ["02", "10", "10"]},
        "ayarli": {"picks": ["12", "10", "12"]},
    }}
    o = deg.ayar_karnesi(d, kayit)
    assert o["kazanilan"] == 1 and o["kaybedilen"] == 1 and o["net"] == 0
    assert o["rows"][0]["prob_bedeli"] == pytest.approx(0.02)
    # Net sıfır olduğu için en iyi kolon da aynı kalır: kazanılan maç
    # kaybedilenin yerine geçti, sayı değişmedi — değişen HANGİ maçların
    # tuttuğu. Ayarın ölçüsü zaten burada değil, bölüşmede.
    assert o["taban_best"] == 2 and o["ayarli_best"] == 2


# ─── canlı kayıt: ölçülmüş sonuçlar yerinde mi ────────────────────────────

@pytest.mark.parametrize(("hafta", "en_iyi", "kacak"), [
    (1, 9, [1, 4, 5, 9, 11, 13]),
    (2, 12, [7, 8, 12]),
])
def test_dondurulmus_kupon_karnesi_yerinde(deg, hafta, en_iyi, kacak):
    """1. ve 2. haftanın ölçülmüş karnesi — kayıt, yeniden hesap değil.

    Bu iki satır bir kez ölçüldü ve belgeye girdi. Kod bunları oynatıyorsa
    kod yanlıştır; sayılar değil.
    """
    o = deg.rapor("2026_27", hafta)
    ana = o["coupons"][0]
    assert ana["best"] == en_iyi
    assert ana["misses"] == kacak


def test_ikinci_kayit_ayni_govdeyle_puanlanir(deg):
    """2. Tahmin'in üç planı da puanlanır ve üçü de ikramiye kademesinde.

    2. haftanın ölçülmüş sonucu: taban ve eşik 7-8-12'yi kaçırdı, ayarlı
    7'yi kurtarıp 14'ü verdi — üçü de 12/15. Kalabalık ayarının net
    etkisi bu haftada SIFIR maçtır ve karne bunu böyle yazmalıdır.
    """
    o = deg.rapor("2026_27", 2)
    planlar = {x["plan"]: x for x in o["tahmin2"]}
    assert set(planlar) == {"taban", "ayarli", "esik"}
    assert all(x["best"] == 12 and x["hedefe_ulasti"] for x in planlar.values())
    assert planlar["ayarli"]["misses"] == [8, 12, 14]
    assert planlar["taban"]["misses"] == [7, 8, 12]
    # Ayar bedavadır: aynı kolon sayısı, başka sembol (docs §3.34).
    assert planlar["ayarli"]["columns"] == planlar["taban"]["columns"]
    assert o["ayar"]["net"] == 0
    assert o["ayar"]["kazanilan"] == 1 and o["ayar"]["kaybedilen"] == 1


def test_iki_kaydin_birlesimi_haftanin_tavanini_gosterir(deg):
    """Birleşim 13/15 — iki kupon birlikte oynansaydı bile 14 yoktu.

    Haftanın ulaşılabilirliği kuralın değil, haftanın özelliğidir; bu
    satır o ayrımı ölçülebilir tutar.
    """
    o = deg.rapor("2026_27", 2)
    assert o["kiyas"]["union_best"] == 13
    assert o["kiyas"]["union_misses"] == [8, 12]


def test_hafta_bir_ikinci_kayit_tasimaz(deg):
    """1. haftada 2. Tahmin YOK — ve bu bir hata değil, kaydın kendisidir."""
    o = deg.rapor("2026_27", 1)
    assert o["tahmin2"] == [] and o["tahmin2_meta"] is None
    assert o["kiyas"] is None and o["ayar"] is None


def test_json_ciktisi_ham_hafta_govdesini_tasimaz(deg, capsys):
    """`--json` gövdesinde `_d` bulunmaz — 15 maçın ikinci kopyası olmaz."""
    deg.main(["--hafta", "2", "--json"])
    o = json.loads(capsys.readouterr().out)
    assert "_d" not in o
    assert len(o["results"]) == 15
    assert sum(o["coupons"][0]["dist"]) == pytest.approx(1.0)


def test_sonucu_olmayan_hafta_sessizce_gecmez(deg, tmp_path):
    """Sonuç girilmemişse rapor ÜRETİLMEZ; boş bir karne yanlış karnedir."""
    m = importlib.import_module("scripts.super_toto_hafta")
    gercek = m.hafta_yukle

    def sonucsuz(sezon, hafta):
        d = gercek(sezon, hafta)
        d["meta"] = {**d["meta"], "results": None}
        return d

    m.hafta_yukle = sonucsuz
    try:
        with pytest.raises(SystemExit):
            deg.rapor("2026_27", 2)
    finally:
        m.hafta_yukle = gercek


# ─── hafta raporu sayfası ─────────────────────────────────────────────────

def test_sayfa_her_girilmis_haftada_uretilir(tmp_path):
    """`super_toto_sayfa.py` girilmiş HER hafta için koşabilmeli.

    Bu bekçi bir çökmeye bağlı: sayfa, sonucu olan haftada ikramiye
    tablosunun da olduğunu varsayıyordu (`ikramiye["tiers"]`). 2. haftanın
    sonucu girildi, ikramiye ekranı girilmedi ve sayfa `KeyError` ile
    düştü. Betik `scripts/check.sh` kapısında koşmadığı için de sessizce
    kırık kalabilirdi.
    """
    import subprocess
    import sys

    m = importlib.import_module("scripts.super_toto_hafta")
    sezon = importlib.import_module("scripts.super_toto_sezon")
    for hafta in sezon.haftalari_bul("2026_27"):
        cikti = tmp_path / f"h{hafta}.html"
        r = subprocess.run(
            [sys.executable, "scripts/super_toto_sayfa.py", "--hafta", str(hafta),
             "--cikti", str(cikti)],
            cwd=KOK, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stderr[-2000:]
        metin = cikti.read_text(encoding="utf-8")
        d = m.hafta_yukle("2026_27", hafta)
        if not d["meta"].get("results"):
            continue
        # Sayfanin sonuc cumleleri HESAPTAN gelmeli: kademeye ulasildi mi
        # ve ikramiye tablosu var mi, ikisi de haftanin kendi verisinden.
        deg = importlib.import_module("scripts.super_toto_degerlendir")
        o = deg.rapor("2026_27", hafta)
        beklenen = ("ulaştı" if o["coupons"][0]["best"] >= deg.HEDEF_KADEME
                    else "ulaşamadı")
        assert f"kupon oraya <b>{beklenen}</b>" in metin
        assert ("bilen</b>" in metin) is bool(d["meta"].get("payout"))


# ─── oynanma biçimi: 16 satır ↔ tam sistem ────────────────────────────────

def test_tam_sistem_ile_kaplama_ayni_isarette_farkli_puan_alir(deg):
    """Aynı işaretler, iki sistem, iki puan — ve fark kozmetik değil.

    16 satırlık kaplama seçim uzayının bir dilimini oynar: küme içinde
    kalmak 14 demektir. Tam sistem uzayın tamamını oynar: küme içinde
    kalmak 15 demektir. 2. haftanın 15 bilen kuponu tam sistemdi; aynı
    işaretler kaplamada 14 verirdi ve 8 kat ucuza gelirdi.
    """
    probs = [_dagilim(0.5, 0.3, 0.2)] * 15
    d = _hafta(probs, "1" * 15)
    picks = ["1", "1"] + ["10"] * 13          # 2 banko + 13 çift
    tam = deg.plan_karnesi(d, picks, "tam")
    kap = deg.plan_karnesi(d, picks, "fix16")
    # Kaplamanin GARANTISI 14'tur; 15 ancak gercek nokta oynanan
    # kolonlardan birine denk gelirse gelir (bu sentetik kupon icin
    # geliyor). Sozlesme bu yuzden ">= 14"tur, "== 14" degil — canli
    # ornekte gercek 14 zaten olculuyor
    # (`test_referans_kupon_kendi_sistemiyle_puanlanir`).
    assert tam["best"] == 15 and kap["best"] >= 14
    assert tam["kolon"] == 2 ** 13
    assert kap["kolon"] == 2 ** 13 // 2 ** 7 * 16
    # Tam sistemde oynanan kolonlar = kümenin kendisi.
    assert tam["p15"] == pytest.approx(tam["kume_ici"])
    # Kaplamada oynanan dilim kümeden KÜÇÜK olmalı.
    assert kap["p15"] < kap["kume_ici"]


def test_kademe_olasiliklari_sistemden_okunur(deg):
    """`P(≥14)` kaplamada `P(k=0)`, tam sistemde `P(k ≤ 1)`dir."""
    probs = [_dagilim(0.5, 0.3, 0.2)] * 15
    d = _hafta(probs, "1" * 15)
    picks = ["1", "1"] + ["10"] * 13
    tam = deg.plan_karnesi(d, picks, "tam")
    kap = deg.plan_karnesi(d, picks, "fix16")
    dist = deg.kupon_degerlendir(d, picks)["dist"]
    assert kap["p14"] == pytest.approx(dist[0])
    assert tam["p14"] == pytest.approx(dist[0] + dist[1])


def test_bilinmeyen_sistem_sessizce_gecmez(deg):
    d = _hafta([_dagilim(0.5, 0.3, 0.2)] * 2, "11")
    with pytest.raises(SystemExit):
        deg.kupon_degerlendir(d, ["1", "1"], "yarim")


# ─── azami kapsamadan sapmalar ────────────────────────────────────────────

def test_sapma_defteri_mekanik_secimde_bos(deg):
    """Kural her maçta en olası k sembolü işaretler — sapma üretmez."""
    d = _hafta([_dagilim(0.5, 0.3, 0.2)] * 3, "111")
    assert deg.sapma_defteri(d, ["1", "10", "102"])["sapma"] == 0


def test_sapmanin_beklenen_neti_eksi_kapsama_bedelidir(deg):
    """Bir özdeşlik, ve defterin okunma biçimi bundan çıkıyor.

    Sapmanın beklenen neti = P(tuttuğu) − P(attığı) = −(kapsama bedeli).
    Yani piyasanın olasılıklarına göre sapmak **her zaman** negatif
    beklenen değerlidir; sapmak ancak piyasadan başka bir görüş varsa
    mantıklıdır. Bu satır, defteri "kim daha çok kapsadı" yarışına
    çevirmeye karşı bekçidir.
    """
    d = _hafta([_dagilim(0.5, 0.3, 0.2), _dagilim(0.4, 0.35, 0.25)], "12")
    o = deg.sapma_defteri(d, ["12", "02"])
    assert o["sapma"] == 2
    assert o["beklenen_net"] == pytest.approx(-o["kapsama_bedeli"])


def test_sapma_defteri_kazanci_kaybi_ve_olasiligi_ayirir(deg):
    """Tuttuğu geldiyse kazanç, attığı geldiyse kayıp; ikisi ayrı sayılır."""
    d = _hafta([_dagilim(0.5, 0.3, 0.2)] * 2, "21")
    o = deg.sapma_defteri(d, ["12", "02"])   # azami ikisinde de "10"
    assert o["kazanc"] == 1 and o["kayip"] == 1 and o["net"] == 0
    assert 0 < o["p_net"] <= 1


# ─── canlı kayıt: 2. haftanın 15 bilen kuponu ─────────────────────────────

def test_referans_kupon_kendi_sistemiyle_puanlanir(deg):
    """15 bilen kupon 15/15; aynı işaretler kaplamada 14, sekizde bir bedelle.

    Kaydın değeri tam olarak bu iki satırın yan yana durmasıdır: 15'i
    satın alan şey işaret seçimi DEĞİL, tam kapsamadır.
    """
    o = deg.rapor("2026_27", 2)
    k = next(x for x in o["referans"] if x["ad"] == "15 bilen kupon")
    assert k["sistem"] == "tam" and k["kolon"] == 8192
    assert k["best"] == 15 and k["misses"] == []
    assert k["oteki_sistem"]["kolon"] == 1024
    assert k["oteki_sistem"]["best"] == 14


def test_referans_kuponun_gorusu_sekilden_yalitilir(deg):
    """Aynı şekil + mekanik semboller 12/15 — yani şekil değil, seçim kazandı.

    Kuponun 8.192 kolonu ve 13 çiftesi tek başına 12 veriyor; bizim
    planlarımızın aldığı sayının aynısı. Farkı yapan altı sapmadır.
    """
    o = deg.rapor("2026_27", 2)
    k = next(x for x in o["referans"] if x["ad"] == "15 bilen kupon")
    assert k["azami"]["best"] == 12
    assert k["azami"]["misses"] == [7, 8, 12]
    # Azami kapsama kümesi DAHA olası; buna rağmen gerçeği kaçırıyor.
    assert k["azami"]["kume_ici"] > k["kume_ici"]


def test_referans_kuponun_sapma_defteri(deg):
    """Altı sapma, üçü kazandı, hiçbiri kaybetmedi — ve bu %5,6'lık bir kuyruk."""
    o = deg.rapor("2026_27", 2)
    sp = next(x for x in o["referans"] if x["ad"] == "15 bilen kupon")["sapma"]
    assert sp["sapma"] == 6
    assert sp["kazanc"] == 3 and sp["kayip"] == 0 and sp["net"] == 3
    assert sp["beklenen_net"] == pytest.approx(-0.196, abs=5e-3)
    assert sp["p_net"] == pytest.approx(0.056, abs=5e-3)
    assert [r["no"] for r in sp["rows"] if r["kazandi"]] == [7, 8, 12]
