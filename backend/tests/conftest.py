"""Testlerin paylaştığı zemin — fixture'lar ve yinelenmiş yardımcılar.

**Neden var.** Depoda `conftest.py` hiç yoktu ve bunun bedeli ölçüldü:
aynı yardımcı gövdesi dosyadan dosyaya kopyalanmıştı. `client` fixture'ı beş
dosyada (üçü birebir aynı), `_girdi` on dosyada, `_kesit` sekizde, `_mac`
altıda, `_hafta` dörtte; ayrıca `kaplama_gecerli`, `_uniform_probs`,
`_enc_cols`, `_dagilim`, `_ham` gibi gövdeler iki-üç yerde **byte byte**
aynıydı. Bir tanesi düzeltildiğinde ötekiler sessizce eskiyordu.

**Ne buraya girer, ne girmez.** Buraya yalnızca **birden fazla dosyanın
gerçekten paylaştığı** ve davranışı ayrışmaması gereken şeyler girer. Tek
dosyaya özgü bir kurgu yerinde kalır: ortak dosyayı şişirmek, okuyucuyu
testin kurulumunu başka bir dosyada aramaya zorlar.

Aynı adı taşıyıp **farklı** şey yapan yardımcılar da yerinde kalır ve bu
kasıtlıdır — örneğin `test_api_health.client` önbelleği temizler (sızıntı
testler arasında geçmesin diye) ve `test_tahmin.client` modül kapsamlıdır
(kurulumu pahalı). İkisi de aşağıdaki fixture'ı **bilinçli olarak ezer**;
pytest'te yerel fixture conftest'i geçersiz kılar.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

KOK = Path(__file__).resolve().parent.parent
# Paket kurulmadan da koşulabilsin. Önceden bu satır YALNIZCA
# `test_ortak.py`de duruyordu — 63 dosyanın birinde, gerekçesi yazılmadan.
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

#: README ve `scripts/check.sh` ile AYNI örnek kupon. İki test dosyasında
#: ayrı ayrı yazılıydı; ayrışsalardı iki testin "aynı kupon" dediği şey
#: farklı olurdu.
ORNEK_KUPON = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"


@pytest.fixture()
def client():
    """Flask test istemcisi — `TESTING` açık, ağ yok.

    `importorskip` gövdenin İÇİNDE: modül düzeyinde olsaydı flask kurulu
    olmayan bir ortamda bu conftest'i okuyan **bütün** testler toplanamazdı.
    """
    pytest.importorskip("flask")
    from web_app import app

    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def kume_tamami_oynaniyor(cols: Any, sizes: Any) -> bool:
    """Seçim kümesinin tamamı gerçekten oynanıyor mu?

    Bu yardımcı eskiden `kaplama_gecerli`ydi ve `core.dogrula_kaplama` ile
    *"en kötü hata ≤ 1 ve açıkta nokta yok"* diye soruyordu — kaplama
    kümenin bir dilimini oynadığı için anlamlı bir soruydu. Düzde dilim
    yok: doğru soru **hiçbir nokta eksik değil** ve bu ondan daha güçlü bir
    şarttır (açık nokta sayısı sıfır DEĞİL, kolon sayısı uzayın kendisi).
    """
    toplam = 1
    for k in sizes:
        toplam *= k
    return len(set(cols)) == toplam == len(cols)


def esit_olasiliklar(n: int = 15) -> list[dict[str, float]]:
    """Bilgi taşımayan tahminci: her maçta 1/3–1/3–1/3."""
    from spor_toto.core import SEMBOLLER

    return [dict.fromkeys(SEMBOLLER, 1.0 / 3.0) for _ in range(n)]


def dagilim(*p: float) -> dict[str, float]:
    """`(0.5, 0.3, 0.2)` -> `{"1": 0.5, "0": 0.3, "2": 0.2}` — düzen `SEMBOLLER`."""
    from spor_toto.core import SEMBOLLER

    return dict(zip(SEMBOLLER, p))


def enc_ve_kolonlar(kupon: str = ORNEK_KUPON):
    """Örnek kupon için `(Encoder, oynanan kolonlar)` — düz, tam sistem."""
    from spor_toto.core import Encoder, parse_picks
    from spor_toto.duz import kolonlar as duz_kolonlar

    enc = Encoder(parse_picks(kupon))
    return enc, duz_kolonlar(enc)


def ham_satir(**alanlar: Any) -> dict[str, str]:
    """CSV satırı taklidi: her değer metne çevrilir."""
    return {k: str(v) for k, v in alanlar.items()}


def hafta_girdisi(week: int, results: str, probs: Any = None,
                  varsayilan: dict[str, float] | None = None) -> dict[str, Any]:
    """Değerlendirme hattının beklediği tek haftalık girdi.

    `varsayilan` ZORUNLU olarak dışarıdan gelir: iki çağıran iki farklı
    taban olasılık kullanıyor (`evaluate` eşit dağılım, `recalibrate` piyasa)
    ve bunu gövdeye gömmek, birleştirmenin testlerden birini sessizce
    değiştirmesi demek olurdu.
    """
    from spor_toto.core import MAC_SAYISI, SEMBOLLER

    taban = varsayilan if varsayilan is not None else dict.fromkeys(SEMBOLLER, 1 / 3)
    return {
        "week": week, "close_date": "2026-01-01", "results": results,
        "probs": list(probs) if probs else [dict(taban)] * MAC_SAYISI,
        "missing": 0, "usable": True,
    }


def kahin_olasiliklari(hafta: dict[str, Any]) -> list[dict[str, float]]:
    """Sonucu BILEN sahte tahmin: gerçek işarete 0,90, ötekilere 0,05.

    Aynı gövde iki ayrı sahte tahminci sınıfında yazılıydı ve ikisi ayrı
    **rol** oynuyor: `test_evaluate.KahinTahminci` bir kuralın
    ateşlenebildiğini kanıtlıyor, `test_sizinti.SizdiranTahminci` sızıntı
    denetiminin onu yakaladığını. Roller ayrı kalmalı — ama mekanizma tek.
    """
    from spor_toto.core import SEMBOLLER

    out = []
    for kod in hafta["results"]:
        p = dict.fromkeys(SEMBOLLER, 0.05)
        p[kod] = 0.90
        out.append(p)
    return out


def esit_tahmin(hafta: dict[str, Any]) -> list[dict[str, float]]:
    """Bilgi taşımayan sahte tahmin: her maça 1/3–1/3–1/3.

    `test_arena.DuzgunKopyasi` ve `test_sizinti.SagirTahminci` aynı gövdeyi
    ayrı ayrı yazıyordu.
    """
    from spor_toto.core import SEMBOLLER

    return [dict.fromkeys(SEMBOLLER, 1 / 3)] * len(hafta["results"])


def korpus_yoksa_atla(yukleyici: Any) -> Any:
    """Eğitim korpusu yoksa testi ATLAR, kırmaz.

    Dört dosyada (`test_bahisci`, `test_cizgi`, `test_disari`, `test_egitim`)
    aynı üç satır ayrı ayrı yazılıydı; yalnızca çağrılan yükleyici
    farklıydı. Korpus `.gitignore`da olduğu için taze bir klonda bu yol
    gerçekten işletiliyor — yani kopyaların ayrışması teorik bir risk değildi.
    """
    h = yukleyici()
    if not h:
        pytest.skip("egitim korpusu yok — once scripts/build_egitim.py")
    return h
