"""Para karnesi — garanti tabanı, enflasyon uyarısı ve kıyas sınırı.

Bu dosyanın asıl bekçilik ettiği şey bir SAYI değil bir **sınır**: garanti
tabanı iki farklı garanti seviyesini karşılaştırmak için kullanılamaz. O
sınır kaybolursa modül sessizce yanlış bir cevap üretmeye başlar.
"""
from __future__ import annotations

import pytest

from spor_toto import karne
from spor_toto.sistem import VARSAYILAN_GARANTI


def _probs(n: int = 15) -> list[dict[str, float]]:
    out = []
    for i in range(n):
        p1 = 0.30 + 0.035 * i
        p0 = (1 - p1) * 0.42
        out.append({"1": p1, "0": p0, "2": 1 - p1 - p0})
    return out


def _tablo(prize: dict[int, float]) -> dict[int, dict[str, object]]:
    return {k: {"correct": k, "winners": 10, "prize": v}
            for k, v in prize.items()}


def test_garantiler_arasi_kiyas_YASAK():
    """Tabanın 15,1 katlık yanlılığı koda bağlı — sessizce kaybolmasın."""
    assert karne.gecerli_kiyas(13, 13) is True
    assert karne.gecerli_kiyas(14, 14) is True
    assert karne.gecerli_kiyas(13, 14) is False
    assert karne.gecerli_kiyas(12, 14) is False


def test_kademe_garantiden_ve_kacaktan_turer():
    """`kademe = G − k`. Kaçak arttıkça kademe düşer, 12'nin altı sıfır ödül."""
    tab = _tablo({15: 1e6, 14: 1e5, 13: 1e4, 12: 1e3})
    r = karne.hafta_karnesi(_probs(), ["1"] * 15, tab, 3000.0, garanti=14)
    assert r is not None
    assert r["kademe"] == 14 - r["kacak"]

    # Hic tutmayan bir sonuc: butun maclarda kacak -> kademe 12'nin altinda
    kotu = karne.hafta_karnesi(_probs(), ["0"] * 15, tab, 3000.0, garanti=14)
    assert kotu is not None
    assert kotu["odul"] == 0.0


def test_odul_12nin_altinda_sifir():
    """İkramiye 12'den başlar — 11 tutturmak para değildir."""
    tab = _tablo({15: 1e6, 14: 1e5, 13: 1e4, 12: 1e3})
    assert karne._odul(tab, 11) == 0.0
    assert karne._odul(tab, 12) == 1e3
    # Tabloda olmayan kademe de sifir, KeyError degil
    assert karne._odul(_tablo({12: 5.0}), 14) == 0.0


def test_butce_sigmazsa_hafta_dusmez_None_doner():
    """Şekil sığmıyorsa satır üretilmez — sıfır ödüllü sahte hafta yazılmaz."""
    tab = _tablo({12: 1.0})
    assert karne.hafta_karnesi(_probs(), ["1"] * 15, tab, 1.0,
                               garanti=VARSAYILAN_GARANTI) is None


def test_karne_bos_kesitte_sesli_duser():
    with pytest.raises(karne.KarneHatasi):
        karne.karne([])


def test_karne_uyarisi_enflasyonu_ve_tabani_ANIYOR():
    """Uyarı metni kaldırılırsa sayılar bağlamsız kalır — bekçi o yüzden var."""
    satir = [{"roi": 0.0, "odul": 0.0, "maliyet": 100.0, "kolon": 10,
              "sezon": "2025_26"}]
    k = karne.karne(satir)
    assert "enflasyon" in k["uyari"].lower()
    assert "GARANTI TABANI" in k["uyari"]
    assert k["sezonlar"][0]["sezon"] == "2025_26"


def test_kuyruk_sinavi_en_iyi_haftalari_atiyor():
    """§5.3(c): en iyi 5 hafta çıkarılınca ortalama düşmeli."""
    satir = [{"roi": 0.0, "odul": 0.0, "maliyet": 100.0, "kolon": 10,
              "sezon": "s"} for _ in range(20)]
    for i in range(5):
        satir[i] = {"roi": 10.0, "odul": 1000.0, "maliyet": 100.0,
                    "kolon": 10, "sezon": "s"}
    k = karne.karne(satir)
    assert k["ortalama_roi"] == pytest.approx(2.5)
    assert k["kuyruksuz_ortalama_roi"] == 0.0
    assert k["en_iyi_bes_hafta_payi"] == pytest.approx(1.0)


def test_bootstrap_sifir_farkta_sifir_aralik():
    lo, hi = karne.bootstrap_farki([0.0] * 50)
    assert lo == hi == 0.0
    lo2, hi2 = karne.bootstrap_farki([])
    assert (lo2, hi2) == (0.0, 0.0)


@pytest.mark.slow
def test_gercek_kesit_iki_arsivin_kesisimi():
    """Kesit gerçekten iki arşivin kesişimi ve boş değil."""
    kesit = karne.kupon_kesiti()
    assert len(kesit) > 100
    for h in kesit:
        assert len(h["probs"]) == 15
        assert len(h["gercek"]) == 15
        assert 15 in h["tablo"], "ikramiye tablosu olmayan hafta kesite girmis"


@pytest.mark.slow
def test_anormal_haftalar_arsivin_tamamindan_hesaplanir():
    """Eşik alt kesitten değil arşivin tamamından — §8'in 32 haftası."""
    anom = karne.anormal_hafta_anahtarlari()
    assert 20 <= len(anom) <= 45, len(anom)


# ─── canlı hafta karnesi ──────────────────────────────────────────────────

def _canli_yaz(kok, sezon, hafta, *, sonuc=None, payout=None, play=True):
    import json as _json

    d = kok / sezon
    d.mkdir(parents=True, exist_ok=True)
    maclar = []
    for i in range(15):
        m = {"no": i + 1, "odds": {"1": 1.9, "0": 3.5, "2": 4.2}}
        if play:
            m["play_pct"] = {"1": 60.0, "0": 25.0, "2": 15.0}
        maclar.append(m)
    meta = {"season": sezon, "week": hafta, "program": "x", "odds_kind": "test",
            "entered_at": "2026-01-01"}
    if sonuc:
        meta["results"] = sonuc
    if payout:
        meta["payout"] = payout
    (d / f"hafta_{hafta:02d}.json").write_text(
        _json.dumps({"meta": meta, "matches": maclar}), encoding="utf-8")


def test_canli_hafta_eksik_yukte_None(tmp_path):
    """15 maçı olmayan ya da oranı eksik yük karneye girmez."""
    assert karne.canli_hafta("2099_00", 1, kok=tmp_path) is None


def test_canli_hafta_fiyat_kunyesini_TASIR(tmp_path):
    """Ölçek haftadan haftaya değişiyor; künye taşınmazsa haftalar
    karşılaştırılamaz hâle gelir ve bunu kimse fark etmez."""
    _canli_yaz(tmp_path, "2099_00", 1)
    h = karne.canli_hafta("2099_00", 1, kok=tmp_path)
    assert h is not None
    assert h["fiyat_kunyesi"] == "test"
    assert len(h["probs"]) == 15
    assert h["play"] is not None and len(h["play"]) == 15


def test_canli_hafta_oynanma_yoksa_None_dondurur(tmp_path):
    _canli_yaz(tmp_path, "2099_00", 2, play=False)
    h = karne.canli_hafta("2099_00", 2, kok=tmp_path)
    assert h is not None and h["play"] is None


def test_canli_karne_satiri_sonucsuz_haftada_odul_YAZMAZ(tmp_path):
    """Sonuç girilmemiş hafta plan taşır ama ödül taşımaz — uydurulmaz."""
    _canli_yaz(tmp_path, "2099_00", 3)
    r = karne.canli_karne_satiri("2099_00", 3, 2000.0, kok=tmp_path)
    assert r is not None
    assert "odul" not in r and "kacak" not in r
    assert r["banko"] + r["cift"] + r["uclu"] == 15
    assert r["oynanma_kaynagi"] == "kayit"


def test_canli_karne_satiri_kademe_GARANTI_TABANINDAN(tmp_path):
    """`kademe = garanti − kaçak` ve ödül o kademenin kişi başı ikramiyesi."""
    payout = {"tiers": [
        {"correct": 15, "winners": 1, "prize": 1e6},
        {"correct": 14, "winners": 5, "prize": 1e5},
        {"correct": 13, "winners": 50, "prize": 1e4},
        {"correct": 12, "winners": 500, "prize": 1e3},
    ]}
    _canli_yaz(tmp_path, "2099_00", 4, sonuc="1" * 15, payout=payout)
    r = karne.canli_karne_satiri("2099_00", 4, 2000.0, garanti=13,
                                 kok=tmp_path)
    assert r is not None
    assert r["kademe"] == 13 - r["kacak"]
    assert r["net"] == r["odul"] - r["maliyet"]


def test_oynanma_kaydi_yoksa_MODELE_duser(tmp_path):
    """Pay kaydı yoksa `kalabalik.OLCULEN` kullanılır ve satır bunu SÖYLER."""
    _canli_yaz(tmp_path, "2099_00", 5, play=False)
    r = karne.canli_karne_satiri("2099_00", 5, 2000.0, kok=tmp_path)
    assert r is not None
    assert r["oynanma_kaynagi"] == "model"


# ─── E1: tabanın gevşekliği ───────────────────────────────────────────────

def test_gercek_dagilim_kacak_yokken_GARANTI_KADEMESINE_ulasir():
    """Kaçak yoksa en iyi kolon 14'e ulaşır — ama 15 GARANTİ DEĞİLDİR.

    Şekil bilerek küçük: 15 üçlü `3^15 = 14M` nokta demek ve kaplama
    çözücüsü orada çöker. Sınanan şey uzayın büyüklüğü değil **kaçağın
    sıfırlığında garantinin tuttuğu**, o da üç üçlüyle görülür.

    Beklenen 15 değil 14: yarıçap-1 kaplama kodu tam isabetli noktayı
    kolonları arasında bulundurmak zorunda değildir — `core.py:943`
    bunu açıkça yazıyor (*"en olasi tek nokta formulun kolonlari
    arasinda olmayabilir. Sistemin degeri 14-garantidir"*). Bu şekilde
    gerçekten de öyle oluyor: dağılımın tepesi 14.
    """
    sec = [["1"]] * 12 + [["1", "0", "2"]] * 3
    d = karne.gercek_kolon_dagilimi(sec, ["1"] * 15)
    assert d is not None
    assert max(d) >= 14
    assert sum(v for k, v in d.items() if k >= 14) >= 1


def test_gercek_dagilim_bankolu_kuponda_toplam_KOLON_sayisi():
    """Dağılımın toplamı kolon sayısına eşit; ölçek verilirse ona indirgenir."""
    sec = [["1"]] * 8 + [["1", "0"]] * 7
    d = karne.gercek_kolon_dagilimi(sec, ["1"] * 15)
    assert d is not None
    toplam = sum(d.values())
    olcekli = karne.gercek_kolon_dagilimi(sec, ["1"] * 15, hedef_kolon=16)
    assert olcekli is not None
    assert sum(olcekli.values()) == pytest.approx(16.0)
    assert toplam >= 16


def test_gercek_odul_12nin_altini_saymaz():
    tablo = {14: {"prize": 100.0}, 13: {"prize": 10.0}, 12: {"prize": 1.0},
             11: {"prize": 0.5}}
    d = {14: 1.0, 13: 2.0, 12: 3.0, 11: 100.0}
    assert karne.gercek_odul(d, tablo) == pytest.approx(100 + 20 + 3)
    assert karne.gercek_odul(None, tablo) is None


@pytest.mark.slow
def test_taban_gercekten_GEVSEK_ve_yonu_belli():
    """E1'in çekirdek bulgusu: taban alt sınır, ve iyi haftaları eksik sayıyor.

    Garanti kademesinde çokluk ≈1 (kaplama orada sıkı) ama para 12'de ve
    orada `k` küçüldükçe kolon sayısı hızla artıyor — yani taban en çok
    **iyi giden** haftaları eksik sayar.
    """
    from spor_toto.secim import sistem_secimi

    kesit = karne.kupon_kesiti()
    oranlar = []
    for h in kesit[:25]:
        p = sistem_secimi(h["probs"], 2000.0, garanti=14)
        if p is None:
            continue
        kacak = sum(1 for s, c in zip(p.secimler, h["gercek"]) if c not in s)
        if kacak > 1:
            continue
        d = karne.gercek_kolon_dagilimi(p.secimler, h["gercek"],
                                        hedef_kolon=p.bedel)
        if not d:
            continue
        # Taban: 1 kolon @ (14-kacak). Gercek: o kademede ve ALTINDA da kolon.
        assert sum(v for k, v in d.items() if k >= 12) >= 1.0
        oranlar.append(sum(v for k, v in d.items() if k >= 12))
    assert oranlar, "olculebilir hafta cikmadi"
    # Iyi haftalarda 12+ kademesinde birden COK kolon olmali.
    assert max(oranlar) > 5.0


@pytest.mark.slow
def test_taban_gevsekligi_ULASILABILIR_ve_yon_YUKARI():
    """`--taban` ölçümü koşuyor ve tabanın alt sınır olduğunu doğruluyor.

    Yalnız yön sınanır, kat değeri değil: kat bir **ölçümdür** ve testte
    dondurulursa ölçüm değişince test onu geriye dönük yeniden yazmaya
    zorlar — depo doktrini bunu yasaklıyor. Sayının kendisi
    `.claude/olcum_kutugu.json`'da, komutuyla birlikte durur.
    """
    t = karne.taban_gevsekligi(2000.0, garanti=14, hafta_siniri=12)
    assert t["hafta"] > 0
    assert t["kat"] is not None and t["kat"] >= 1.0, \
        "gercek odul tabanin ALTINA dusemez — taban tanim geregi alt sinir"
    assert t["kat_ham"] >= t["kat"], \
        "indirgeme kolon sayisini kucultur, yani kat_ham buyuk olmali"


@pytest.mark.slow
def test_motorun_kaplamasi_TABLODAN_gevsek_ve_bu_yazili():
    """Motor aynı şekle satıcıdan daha çok kolon üretiyor — ölçülen fark.

    Bu, `taban_gevsekligi`nin indirgeme varsayımının **sebebidir**: iki
    ürün aynı değil, o yüzden hangi kolon sayısına indirgendiği docstring'de
    yazılı olmak zorunda.
    """
    t = karne.taban_gevsekligi(2000.0, garanti=14, hafta_siniri=8)
    assert t["motor_kolon"] >= t["tablo_kolon"] > 0
    assert t["kaplama_farki"] >= 1.0
