"""`/api/stats` ve `/api/backtest` govdeleri — TEK kaynak.

Bu govdeler `web_app.py` icindeki route fonksiyonlarinda kuruluyordu ve
saglik katmani onlara erisemiyordu: veri katmani (history/odds/backtest)
dogrulaniyordu ama **arayuzun gercekten okudugu sekil** hicbir yerde
sinanmiyordu. Bir alan adi degistiginde motor sapasaglam kalir, testler
gecer, `/istatistik` bos doner.

`meta.meta_payload()` ile ayni desen: route yalnizca `jsonify` eder,
`health._check_stats_sozlesmesi` ayni fonksiyonu cagirip ic tutarliligini
denetler.
"""

from __future__ import annotations

from typing import Any

from .backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU, backtest
from .history import history_analytics, history_summary, history_weeks
from .odds import season_1x2_summary


def stats_payload(last: int | None = None) -> dict[str, Any]:
    """Tarihsel 1/0/2 + analiz bloklari + oran ozeti.

    `last` verilirse ozet, bantlar VE analiz bloklarinin tamami ayni dilim
    uzerinden hesaplanir — iki gorsel asla farkli veriyi anlatmaz.
    """
    summary = history_summary(last)
    weeks = history_weeks(last)
    return {
        "meta": summary.get("meta", {}),
        "totals": summary.get("totals", {}),
        "weekly_avg": summary.get("weekly_avg", {}),
        "bands": summary.get("bands", {}),
        "data_quality": summary.get("data_quality", {}),
        "analytics": history_analytics(last),
        # Yalnizca MAC SONUCU (1X2). Arsivdeki diger pazarlar (alt/ust, Asya
        # handikap) analiz icindir, API'den cikmaz. Arsiv yoksa None doner.
        "odds": season_1x2_summary([w["week"] for w in weeks]),
        "weeks": weeks,
        "last": last,
        "error": summary.get("error"),
    }


def backtest_payload(
    last: int | None = None,
    banko: float = VARSAYILAN_BANKO,
    uclu: float = VARSAYILAN_UCLU,
    sweep: bool = True,
) -> dict[str, Any]:
    """Geri test govdesi: sezon + hafta hafta + (istege bagli) esik taramasi.

    Tarama acikken hold-out bloku da gelir; esigin o haftayi GORMEDEN
    secildigi halde olculen sonuc odur ve geriye uydurulmus sayinin yaninda
    her zaman birlikte okunmalidir.
    """
    return backtest(last=last, banko_esik=banko, uclu_esik=uclu, sweep=sweep)
