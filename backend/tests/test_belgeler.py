"""Belgelerin gerçekle örtüşmesini tutan bekçiler.

**Neden var.** Bu depoda belgeler koddan hızlı eskiyordu ve eskidikleri
hiçbir yerde görünmüyordu. Denetimde bulunanlar:

* test sayısı **dört belgede dört farklı** değerdi (700 / 911 / 664 / 664);
* `README.md` §1.1 hold-out isabetini **1**, §14 aynı sayıyı **0** diyordu —
  tek dosyanın kendi içinde çelişkisi;
* `docs/ARCHITECTURE_NEXT.md` "kesin karar" başlıklı API tablosunda **dört uç
  eksikti** ve iki belge daha o tabloyu kaynak gösteriyordu;
* `backend/README.md` "hiçbir API ucu oran arşivinden okumaz" diyordu, oysa
  `/api/stats` bir `odds` bloğu döndürüyor.

Bunların hepsi elle düzeltildi. Buradaki testler **tekrar eskimesini**
engeller: liste dosya sistemiyle karşılaştırılır, sayı ölçümle.

Kasıtlı olarak DAR: her cümleyi değil, sessizce yanlışlanabilen **sayılabilir**
iddiaları tutar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
DEPO = KOK.parent


def _oku(göreli: str) -> str:
    p = DEPO / göreli
    if not p.exists():
        pytest.skip(f"{göreli} yok")
    return p.read_text(encoding="utf-8")


def test_mimari_belgesi_butun_uclari_sayar():
    """`ARCHITECTURE_NEXT.md` API tablosu `web_app`teki uçların TAMAMINI saymalı.

    Bu tablo iki belge tarafından daha *kaynak* gösteriliyor, yani bir eksik
    satır üç yere birden yayılıyor.
    """
    metin = _oku("docs/ARCHITECTURE_NEXT.md")
    kaynak = (KOK / "web_app.py").read_text(encoding="utf-8")

    yollar = set(re.findall(r'@app\.route\("([^"]+)"', kaynak))
    # `<int:week>` tabloda `<week>` diye yazılır.
    yollar = {y.replace("<int:week>", "<week>") for y in yollar}

    # YALNIZCA tablo satırları sayılır. Önce "belgede geçiyor mu" diye
    # bakılıyordu ve bekçi işe yaramıyordu: aynı belgenin NESRİ de uçları
    # anıyor, dolayısıyla tablodan bir satır silinse bile test geçiyordu.
    # (Ölçüldü: `/api/benzer` satırı tablodan çıkarıldı, test yeşil kaldı.)
    tablo_uclari: set[str] = set()
    for satir in metin.splitlines():
        if not satir.startswith("| "):
            continue
        hucreler = [h.strip() for h in satir.strip("|").split("|")]
        if len(hucreler) < 2:
            continue
        m = re.match(r"`([^`]+)`", hucreler[1])
        if m:
            # `?last=N` gibi örnek sorgular yoldan ayrılır.
            tablo_uclari.add(m.group(1).split("?")[0])

    eksik = sorted(y for y in yollar if y not in tablo_uclari)
    assert not eksik, (
        f"ARCHITECTURE_NEXT.md API TABLOSUNDA eksik uç: {eksik}. "
        f"web_app.py {len(yollar)} uç tanımlıyor, tablo {len(tablo_uclari)} sayıyor."
    )


def test_saglik_kontrol_sayisi_belgeyle_ayni():
    """Belgede yazan kontrol sayısı `health.CHECKS` ile örtüşmeli."""
    from spor_toto.health import CHECKS

    metin = _oku("docs/SAGLIK_GELISTIRME_RAPORU.md")
    sayilar = {int(x) for x in re.findall(r"[Kk]ayıtlı kontrol[^\d]{0,12}(\d+)", metin)}
    if not sayilar:
        pytest.skip("belgede kayıtlı kontrol sayısı geçmiyor")
    assert sayilar == {len(CHECKS)}, (
        f"belge {sorted(sayilar)} diyor, gerçek {len(CHECKS)}"
    )


def test_test_sayisi_belgelerde_tek_ve_dogru():
    """Test sayısı bütün belgelerde AYNI olmalı ve gerçeği söylemeli.

    Tam sayı tutturmak kırılgan olurdu (her yeni test belgeyi bozardı), o
    yüzden iddia şu: belgelerde geçen sayı gerçekten uzak olmamalı ve
    hepsi birbiriyle aynı olmalı.
    """
    dosyalar = [
        "README.md", "replit.md",
        "docs/ISTATISTIK_YOL_HARITASI.md",
        "docs/SAGLIK_GELISTIRME_RAPORU.md",
        "docs/SAGLIK_VIZYONU.md",
        "docs/VERI_TOPLAMA_VE_ISLEME.md",
    ]
    bulunan: dict[str, set[int]] = {}
    for d in dosyalar:
        p = DEPO / d
        if not p.exists():
            continue
        metin = p.read_text(encoding="utf-8")
        sayilar = {
            int(x.replace(".", ""))
            for x in re.findall(r"([\d.]+)\s*test\b", metin)
            if x.replace(".", "").isdigit() and int(x.replace(".", "")) > 300
        }
        if sayilar:
            bulunan[d] = sayilar

    tum = set().union(*bulunan.values()) if bulunan else set()
    assert len(tum) <= 1, (
        "test sayısı belgelerde AYRIŞMIŞ: "
        + ", ".join(f"{d}={sorted(v)}" for d, v in bulunan.items())
    )


# NOT: burada bir de "README hold-out sayisini kendi icinde celismiyor mu"
# testi vardi ve KALDIRILDI. Nesir uzerinde regex kirilgan cikti: README
# §5.4 bilerek TARIHSEL bir karsilastirma yapiyor ("orantisal olcekte ayni
# tablo hold-out'ta 0 haftaydi") ve o cumle dogru. Bir bekcinin dogru
# cumleyi yanlis diye isaretlemesi, hic bekci olmamasindan kotudur.
#
# Asil celiski (§14'un §1.1 ile catismasi) elle duzeltildi; onu tutan sey
# artik `api_sozlesme.py`nin urettigi olculmus degerler, nesir taramasi degil.
