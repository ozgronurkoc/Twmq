"""Sistem health — tek vücut entegrasyon doğrulaması."""

import os
import time

import pytest

from spor_toto.core import Encoder, parse_picks, solve_fix16
from spor_toto.health import (
    CHECKS,
    KATEGORILER,
    KUPON_SINIFLARI,
    ORNEK,
    CheckSpec,
    _run,
    check_envanteri,
    kupon_denetle,
    ornek_kimligi,
    print_report,
    run_health,
    secili_checkler,
)


def test_run_health_all_pass():
    report = run_health()
    failed = [c for c in report.checks if not c.ok]
    assert report.ok, f"Health FAIL: {[(c.name, c.detail) for c in failed]}"
    passed = sum(1 for c in report.checks if c.ok)
    assert passed == len(report.checks)
    assert len(report.checks) >= 10


def test_health_report_dict_shape():
    d = run_health().to_dict()
    assert "version" in d
    assert "timestamp" in d
    assert d["ok"] is True
    assert d["degraded"] is False
    assert d["passed"] == d["total"]
    assert d["duration_ms"] > 0
    assert isinstance(d["checks"], list)
    for c in d["checks"]:
        assert set(c.keys()) >= {
            "name", "ok", "detail", "duration_ms",
            "category", "category_label", "aciklama", "critical",
        }
        assert c["ok"] is True
        assert c["aciklama"], f"{c['name']} icin aciklama yok"


def test_health_includes_core_and_analysis():
    names = {c.name for c in run_health().checks}
    for required in (
        "encoder",
        "fix16_garanti",
        "distance_layers",
        "olasilik_exact",
        "monte_carlo",
        "error_freq",
        "pipeline_result_shape",
        "veri_seti",
        "oran_arsivi",
    ):
        assert required in names


def test_ilan_edilen_yuzey_kapsanir():
    """Meta sözleşmesi, ilan edilen modlar, preset'ler ve varyantlar.

    Bunların hepsi kullanıcıya doğrudan çarpan yüzeylerdir ve sağlık
    kapsamına sonradan alınmıştır; listeden düşerlerse kapsam boşluğu
    sessizce geri gelir.
    """
    names = {c.name for c in run_health().checks}
    for required in (
        "meta_sozlesmesi",
        "mod_envanteri",
        "bayes_presetleri",
        "fix16_varyantlari",
    ):
        assert required in names


def test_print_report_no_crash(capsys):
    print_report(run_health())
    out = capsys.readouterr().out
    assert "SYSTEM HEALTH" in out
    assert "HEALTHY" in out
    # Kategori başlıkları çıktıda görünmeli.
    assert "Çekirdek" in out


# ─── kategori / envanter ──────────────────────────────────────────────────────

def test_her_check_bilinen_kategoride():
    gecerli = {k for k, _, _ in KATEGORILER}
    for c in CHECKS:
        assert c.category in gecerli, f"{c.name}: bilinmeyen kategori {c.category}"


def test_check_adlari_tekil():
    adlar = [c.name for c in CHECKS]
    assert len(adlar) == len(set(adlar))


def test_kategori_ozeti_toplami_tutar():
    report = run_health()
    kats = report.kategoriler()
    assert sum(k["total"] for k in kats) == len(report.checks)
    assert sum(k["passed"] for k in kats) == sum(1 for c in report.checks if c.ok)


def test_envanter_calistirmadan_listeler():
    env = check_envanteri()
    assert len(env) == len(CHECKS)
    assert {e["name"] for e in env} == {c.name for c in CHECKS}
    assert all(e["aciklama"] for e in env)


# ─── kısmi çalıştırma (--only / ?only=) ───────────────────────────────────────

def test_only_tek_kontrol():
    report = run_health("encoder")
    assert [c.name for c in report.checks] == ["encoder"]
    assert report.summary["kismi"] is True
    assert report.summary["only"] == "encoder"
    assert report.ok


def test_only_kategori():
    report = run_health("olasilik")
    assert {c.category for c in report.checks} == {"olasilik"}
    assert len(report.checks) >= 4


def test_only_coklu_ve_sira_korunur():
    report = run_health("markov_chain,encoder")
    # Tanım sırası korunur; istek sırası değil.
    assert [c.name for c in report.checks] == ["encoder", "markov_chain"]


def test_only_tekrarli_ad_iki_kez_calismaz():
    report = run_health("encoder,encoder,cekirdek")
    adlar = [c.name for c in report.checks]
    assert len(adlar) == len(set(adlar))


def test_only_bilinmeyen_ad_hata_verir():
    with pytest.raises(ValueError, match="Bilinmeyen kontrol/kategori"):
        secili_checkler("boyle_bir_sey_yok")


def test_only_bos_hepsini_calistirir():
    assert len(secili_checkler(None)) == len(CHECKS)
    assert len(secili_checkler("  ")) == len(CHECKS)
    assert run_health().summary["kismi"] is False


# ─── ortam bilgisi ────────────────────────────────────────────────────────────

def test_env_bilgisi_raporda():
    env = run_health("encoder").summary["env"]
    assert env["python"]
    assert env["platform"]
    assert "numpy" in env and "scipy" in env


def test_dusen_kontrol_kirilma_yerini_yazar():
    """Yassıltılmış "AssertionError:" hangi satırda kırıldığını söylemez.

    Assert'ler çoğunlukla mesajsızdır; son kare olmadan canlıda düşen bir
    kontrolü ayıklamak kaynak okumaya dönüşür.
    """
    def kirik() -> str:
        assert False

    r = _run(CheckSpec("kirik_deneme", "cekirdek", "test", kirik))
    assert r.ok is False
    assert r.detail.startswith("AssertionError")
    assert "@ test_health.py:" in r.detail, r.detail


def test_gecen_kontrol_kirilma_yeri_yazmaz():
    r = _run(CheckSpec("gecen_deneme", "cekirdek", "test", lambda: "olctum=3"))
    assert r.ok is True
    assert r.detail == "olctum=3"
    assert "@" not in r.detail


# ─── süre bütçeleri (§7.1) ───────────────────────────────────────────────────

def test_her_kontrolun_butcesi_var():
    """Bütçesiz bir kontrol, süre gerilemesini görünmez kılar."""
    butcesiz = [c.name for c in CHECKS if c.butce_ms is None]
    assert not butcesiz, f"süre bütçesi olmayan kontrol: {butcesiz}"


def test_butce_asimi_dusurmez_yalnizca_isaretler():
    """Yavaşlamak bir gerilemedir ama DÜŞÜŞ değildir: değişmez hâlâ geçerli,
    yalnızca beklenenden pahalı."""
    def yavas() -> str:
        time.sleep(0.05)
        return "olctum=1"

    r = _run(CheckSpec("yavas_deneme", "cekirdek", "test", yavas, butce_ms=5))
    assert r.ok is True
    assert r.yavas is True
    assert "bütçe" in r.detail


def test_isinma_kosusunda_butce_uygulanmaz():
    """İlk koşu numpy/scipy import'unu ve veri setinin ilk okunmasını da
    üstlenir; ısınmayı gerileme saymak her soğuk başlangıçta yanlış alarm
    üretirdi."""
    def yavas() -> str:
        time.sleep(0.05)
        return "olctum=1"

    r = _run(CheckSpec("yavas_deneme", "cekirdek", "test", yavas, butce_ms=5),
             isinma=True)
    assert r.yavas is False


def test_butce_altindaki_kontrol_isaretlenmez():
    r = _run(CheckSpec("hizli", "cekirdek", "test", lambda: "ok", butce_ms=500))
    assert r.yavas is False
    assert "bütçe" not in r.detail


def test_rapor_butce_asanlari_ozetler():
    d = run_health().to_dict()
    assert "butce_asan" in d["summary"]
    assert isinstance(d["summary"]["butce_asan"], list)
    for c in d["checks"]:
        assert "butce_ms" in c and "yavas" in c


# ─── kupon sınıfları (§7.5) ──────────────────────────────────────────────────

def test_kupon_siniflari_tablosu_dogru():
    """Tablodaki beklenen sayılar motorla ölçülenle aynı olmalı; tablo
    yanlışsa kontrol yanlış şeyi doğrular."""
    for s in KUPON_SINIFLARI:
        enc = Encoder(parse_picks(s.picks))
        assert enc.total_len == 15, s.etiket
        assert enc.space_size() == s.uzay, s.etiket
        assert enc.lower_bound() == s.alt_sinir, s.etiket
        cols, _ = solve_fix16(enc)
        assert len(cols) == s.fix16_bedel, s.etiket


def test_siniflar_gercekten_farkli_bicimleri_kapsar():
    uzaylar = {s.uzay for s in KUPON_SINIFLARI}
    assert len(uzaylar) == len(KUPON_SINIFLARI), "iki sınıf aynı uzayı kapsıyor"
    # En az bir sınıf ÜÇLÜ içermeli: alfabe boyu 3 farklı kod yolu kullanır.
    uclu_var = any(3 in Encoder(parse_picks(s.picks)).alphabet_sizes
                   for s in KUPON_SINIFLARI)
    assert uclu_var, "hiçbir sınıf üçlü içermiyor"


def test_rapor_kupon_siniflarini_bildirir():
    siniflar = run_health("encoder").summary["kupon_siniflari"]
    assert len(siniflar) == len(KUPON_SINIFLARI)
    assert all(s["etiket"] and s["picks"] for s in siniflar)


# ─── örnek kimliği (§7.8) ────────────────────────────────────────────────────

def test_ornek_kimligi_raporda():
    """Çok örnekli bir dağıtımda "hangi örnek?" sorusu cevapsızdı: iki
    ardışık çağrı farklı süreçlere düşüp farklı cevap verebilir."""
    o = run_health("encoder").summary["ornek"]
    assert o["pid"] == os.getpid()
    assert o["host"]
    assert o["baslangic"]
    assert o["uptime_s"] >= 0


def test_ornek_etiketi_ortamdan_okunur(monkeypatch):
    monkeypatch.setenv("INSTANCE_ID", "kirmizi-3")
    assert ornek_kimligi()["etiket"] == "kirmizi-3"


# ─── kullanıcı kuponu (§7.4) ─────────────────────────────────────────────────

def test_kupon_denetle_gecerli_kupon():
    r = kupon_denetle(ORNEK)
    assert r["ok"] is True
    assert r["satir"] == 16
    assert r["bedel"] == 32
    assert r["guaranteed"] is True
    assert {c["name"] for c in r["checks"]} >= {
        "kaplama_garantisi", "mesafe_muhasebesi", "satir_kolon_muhasebesi",
        "alt_sinir", "olasilik_tutarliligi",
    }
    for c in r["checks"]:
        assert c["aciklama"] and c["detail"]


def test_kupon_denetle_kayitli_rapordan_ayridir():
    """Tek bir kuponun doğrulanması, motorun genel sağlığı değildir; ikisi
    aynı tabloda görünürse HEALTHY yanlış okunur."""
    r = kupon_denetle(ORNEK)
    assert "uyari" in r and r["uyari"]
    assert {c["name"] for c in r["checks"]}.isdisjoint(
        {c.name for c in CHECKS}), "kupon kontrolleri kayıtlı adlarla karışıyor"


def test_kupon_denetle_garanti_vermeyen_mod():
    """maxcov garanti VERMEDİĞİNİ ilan eder; bütçe alt sınırın altındayken
    kaplamanın açık bırakması doğru davranıştır, düşüş değil."""
    r = kupon_denetle(ORNEK, mode="maxcov", budget=8)
    assert r["ok"] is True
    assert r["guaranteed"] is False
    assert r["acik"] > 0


def test_kupon_denetle_butce_modu_kuponu_daraltir():
    r = kupon_denetle(ORNEK, mode="butce", budget=24)
    assert r["ok"] is True
    assert r["bedel"] <= 24


def test_kupon_denetle_bilinmeyen_mod():
    with pytest.raises(ValueError, match="Bilinmeyen mod"):
        kupon_denetle(ORNEK, mode="boyle_bir_mod_yok")


def test_kupon_denetle_butce_zorunlulugu():
    with pytest.raises(ValueError, match="budget"):
        kupon_denetle(ORNEK, mode="maxcov")


def test_kupon_denetle_yetersiz_cifte():
    with pytest.raises(Exception):
        kupon_denetle("1,1,1,1,1,1,1,1,1,1,1,1,1,1,1")


def test_slowest_en_uzun_kontrolu_gosterir():
    d = run_health().to_dict()
    slowest = d["summary"]["slowest"]
    assert slowest["duration_ms"] == max(c["duration_ms"] for c in d["checks"])
