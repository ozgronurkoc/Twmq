"""`scripts/sembol_sirasi.py` bekçileri — 2.↔3. sembol sırası ölçümü.

**Neden var.** Bu ölçüm ölçüm kütüğünde vardı ama betiği yoktu: künyenin
`ureten` alanı bir *tarif* taşıyordu ("marj bandına bölünür") ve o tarif
**yanlıştı** — bant bahisçi marjı değil, iki sembol arasındaki beklenen
farktır. Yanlış tarifle sayı yeniden üretilemiyordu, yani kütükte "ölçülmüş"
diye duran bir kayıt pratikte doğrulanamazdı.

Doğru tarifle eski (22 ligli) korpusta kayıttaki üç bandın hem `n`'i hem
değeri birebir çıktı; betik o rekonstrüksiyondur. Buradaki testler onun
sözleşmesini tutar, ölçümü yeniden koşmaz.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.sembol_sirasi import BANTLAR, olc
from tests.conftest import korpus_yoksa_atla

KOK = Path(__file__).resolve().parent.parent
DEPO = KOK.parent


@pytest.fixture(scope="module")
def sonuc():
    return korpus_yoksa_atla(olc)


def test_bantlar_kesisMEZ_ve_hepsi_dolu(sonuc):
    """Üç bant da örnek taşımalı — biri boşsa bantlama kesiti kaçırıyordur."""
    assert set(sonuc) == set(BANTLAR), f"eksik bant: {set(BANTLAR) - set(sonuc)}"
    for ad, s in sonuc.items():
        assert s["n"] > 100, f"{ad} bandi cok ince: n={s['n']}"


def test_beklenen_fark_bandin_ICINDE(sonuc):
    """Bant beklenen fark üzerinden kurulur; ortalaması bandın dışına düşemez.

    Düşerse bantlama ölçünün kendisiyle tutarsızdır — tam olarak eski
    künyedeki "marj bandı" tarifinin yaptığı hata.
    """
    sinir = {"<2": (0.0, 2.0), "2-4": (2.0, 4.0), ">=4": (4.0, 100.0)}
    for ad, s in sonuc.items():
        alt, ust = sinir[ad]
        assert alt <= s["beklenen"] <= ust, (
            f"{ad} bandinin beklenen ortalamasi {s['beklenen']:.1f} bandin disinda")


def test_artik_fark_eksi_beklenen(sonuc):
    """`artik` türetilmiş bir alandır ve tanımıyla tutarlı kalmalı."""
    for ad, s in sonuc.items():
        assert s["artik"] == pytest.approx(s["fark"] - s["beklenen"], abs=1e-9), ad


def test_bant_olcusu_kutukle_ayni(sonuc):
    """`<2` bandının değeri ölçüm kütüğündeki künyeyle örtüşmeli.

    Kütükteki sayı bu betiğin çıktısıdır; ayrışırlarsa ya korpus değişmiştir
    (betiği koş, künyeyi güncelle) ya künye elle bozulmuştur. İkisi de elle
    karardır — eşik gevşetilerek geçiştirilmez.
    """
    kutuk = DEPO / ".claude" / "olcum_kutugu.json"
    if not kutuk.exists():
        pytest.skip("olcum_kutugu.json yok (git disi klon)")
    # Kutukte IKI kayit var: 22 ligli olcek DONMUS (hafta_05_kupon.json'da
    # yasiyor, guncellenmez) ve bugunku 17 ligli. Bekci bugunkuyle karsilastirir.
    kayit = [s for s in json.loads(kutuk.read_text(encoding="utf-8"))["sayilar"]
             if s["ne"].startswith("2.<->3. sembol sirasi")
             and "17 LIGLI" in s["ne"]]
    assert kayit, "kutukte 17 ligli 2.<->3. sembol sirasi kaydi yok"
    yazili = float(re.sub(r"[^\d,.-]", "", kayit[0]["deger"].replace("−", "-"))
                   .replace(",", "."))
    assert round(sonuc["<2"]["fark"], 1) == pytest.approx(yazili, abs=0.05), (
        f"kutuk {yazili} diyor, olcum {sonuc['<2']['fark']:.1f}")
