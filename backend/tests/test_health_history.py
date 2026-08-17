"""Sunucu tarafı sağlık geçmişi ve durum değişimi bildirimi.

Bu katmanın cevapladığı soru "ne zamandan beri kırmızı?"dır; oturum içi
geçmiş sekme kapanınca gittiği için hiçbir yerde cevaplanamıyordu.
"""

import pytest

from spor_toto import health_history as hh


def rapor(ok=True, degraded=False, kismi=False, dusen=(), yavas=(), zaman="t"):
    checks = [{"name": "gecen", "ok": True, "yavas": False}]
    checks += [{"name": ad, "ok": False, "yavas": False} for ad in dusen]
    checks += [{"name": ad, "ok": True, "yavas": True} for ad in yavas]
    return {
        "timestamp": zaman, "ok": ok, "degraded": degraded,
        "passed": sum(1 for c in checks if c["ok"]), "total": len(checks),
        "duration_ms": 12.5, "version": "4.0.0", "checks": checks,
        "summary": {"kismi": kismi},
    }


@pytest.fixture(autouse=True)
def temiz_tampon(monkeypatch):
    hh.temizle()
    gonderilen = []
    monkeypatch.setattr(hh, "_bildir",
                        lambda onceki, kayit: gonderilen.append((onceki, kayit["durum"])))
    yield gonderilen
    hh.temizle()


def test_kayit_ozeti_tutulur():
    hh.kaydet(rapor(dusen=("encoder",), ok=False))
    kayitlar = hh.gecmis()
    assert len(kayitlar) == 1
    k = kayitlar[0]
    assert k["durum"] == "UNHEALTHY"
    assert k["dusenler"] == ["encoder"]
    assert k["duration_ms"] == 12.5


def test_gecmis_en_yeniden_eskiye():
    for i in range(3):
        hh.kaydet(rapor(zaman=f"t{i}"))
    assert [k["timestamp"] for k in hh.gecmis()] == ["t2", "t1", "t0"]


def test_kismi_kosu_seriye_girmez():
    """"5/5 geçti" ile "21/21 geçti" aynı seride yan yana durursa seri yalan
    söyler: kısmi koşu daha az şey doğrular ama aynı yeşili gösterir."""
    sonuc = hh.kaydet(rapor(kismi=True))
    assert sonuc["kaydedildi"] is False
    assert hh.gecmis() == []


def test_ozet_ne_zamandan_beri_bu_durumda(temiz_tampon):
    hh.kaydet(rapor(zaman="t0"))
    hh.kaydet(rapor(ok=False, zaman="t1"))
    hh.kaydet(rapor(ok=False, zaman="t2"))
    o = hh.ozet()
    assert o["durum"] == "UNHEALTHY"
    assert o["bu_durumda_kosu"] == 2
    assert o["degisim_zamani"] == "t1", "kırmızıya dönüşün zamanı"
    assert o["son_saglikli"] == "t0"


def test_bildirim_yalnizca_degisimde(temiz_tampon):
    """Her kırmızı koşuda bildirim göndermek bildirimleri okunmaz yapar;
    okunmayan alarm, alarmsızlıktan kötüdür — korunduğunu sanırsın."""
    for r in (rapor(), rapor(), rapor(ok=False), rapor(ok=False), rapor()):
        hh.kaydet(r)
    assert temiz_tampon == [("HEALTHY", "UNHEALTHY"), ("UNHEALTHY", "HEALTHY")]


def test_degraded_ayri_bir_durumdur(temiz_tampon):
    hh.kaydet(rapor())
    hh.kaydet(rapor(degraded=True, yavas=("monte_carlo",)))
    assert temiz_tampon == [("HEALTHY", "DEGRADED")]
    assert hh.gecmis()[0]["yavaslar"] == ["monte_carlo"]


def test_ilk_kayit_bildirim_uretmez(temiz_tampon):
    """Süreç kırmızı başlamış olabilir; "değişti" demek için önce bir şey
    olması gerekir."""
    hh.kaydet(rapor(ok=False))
    assert temiz_tampon == []


def test_tampon_sinirlidir():
    sinir = hh._kayitlar.maxlen
    for i in range(sinir + 10):
        hh.kaydet(rapor(zaman=f"t{i}"))
    assert len(hh.gecmis(sinir + 50)) == sinir
    assert hh.gecmis()[0]["timestamp"] == f"t{sinir + 9}"
