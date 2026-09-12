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

from .backtest import (
    VARSAYILAN_BANKO,
    VARSAYILAN_BUTCE_TL,
    VARSAYILAN_UCLU,
    backtest,
)
from .history import (
    TUM_SEZONLAR,
    history_analytics,
    history_summary,
    history_weeks,
)
from .odds import season_1x2_summary
from .pazar import sezon_ozeti


def stats_payload(last: int | None = None,
                  sezon: str | None = None) -> dict[str, Any]:
    """Tarihsel 1/0/2 + analiz bloklari + oran ozeti.

    `last` verilirse ozet, bantlar VE analiz bloklarinin tamami ayni dilim
    uzerinden hesaplanir — iki gorsel asla farkli veriyi anlatmaz.

    `sezon` ayni sekilde HER IKI tarafa birden gecer. Bu sart: asagidaki
    `season_1x2_summary` cagrisi haftalari yalnizca NUMARAYLA suzuyor ve
    numara sezon tasimiyor — sezon gecirilmezse baska bir sezonun oran
    arsivinde ayni numaralar bulunur ve oran karti SESSIZCE baska bir
    sezonu anlatirdi.

    `sezon == TUM_SEZONLAR` (birlesik kesit) ayni tuzagin BUYUK halidir:
    orada numara listesi dort sezonun ayni numarali haftalarini birden
    gecirirdi. Bu yuzden birlesik kipte suzgec `(sezon, hafta)` ciftidir ve
    cift, hafta satirlarinin KENDI `sezon` alanindan kurulur — ikinci bir
    sezon listesi burada tutulmaz.
    """
    summary = history_summary(last, sezon)
    weeks = history_weeks(last, sezon)
    oran_kesiti: list[Any] = (
        [(w["sezon"], w["week"]) for w in weeks] if sezon == TUM_SEZONLAR
        else [w["week"] for w in weeks]
    )
    return {
        "meta": summary.get("meta", {}),
        "totals": summary.get("totals", {}),
        "weekly_avg": summary.get("weekly_avg", {}),
        "bands": summary.get("bands", {}),
        "data_quality": summary.get("data_quality", {}),
        "analytics": history_analytics(last, sezon),
        # Yalnizca MAC SONUCU (1X2). Diger pazarlar ARTIK cikiyor ama AYRI
        # bir uctan (`/api/pazar`, bkz. `pazar_payload`): olcumleri farkli
        # (alt/ust ikili ve Brier'li, handikap kesirli getirili ve Brier'siz)
        # ve ayni govdeye sikistirmak ikisini de yanlis okuturdu.
        # Arsiv yoksa None doner.
        "odds": season_1x2_summary(oran_kesiti, sezon),
        "weeks": weeks,
        "last": last,
        "sezon": sezon,
        "error": summary.get("error"),
    }


def backtest_payload(
    last: int | None = None,
    banko: float = VARSAYILAN_BANKO,
    uclu: float = VARSAYILAN_UCLU,
    sweep: bool = True,
    sezon: str | None = None,
    strateji: str = "hedef",
    butce_tl: float = VARSAYILAN_BUTCE_TL,
) -> dict[str, Any]:
    """Geri test govdesi: kesit ozeti + hafta hafta + o stratejinin taramasi.

    `strateji` varsayilan olarak **`hedef`**tir, yani urunun kendi kurali
    (`secim.en_iyi_secim`). Uzun sure burada tek secenek `esik` vardi ve
    arayuz urunun kullanmadigi bir kuralin sayilarini gosteriyordu.

    Taramanin sekli stratejiye baglidir ve bu bilincli:

    * `esik`  -> `sweep` + `sweep_best` + `holdout`. Ayarlanan bir parametre
      var, dolayisiyla asiri uyum OLCULEBILIR ve olculmelidir; esigin o
      haftayi GORMEDEN secildigi halde olculen sonuc, geriye uydurulmus
      sayinin yaninda her zaman birlikte okunur.
    * `hedef` -> `butce_sweep`, hold-out YOK. Optimizasyon sonucu gormez
      (ex-ante bir hedefi enbuyukler), yani hold-out'un korudugu risk
      yoktur; taranan sey bir parametre degil bir **harcama kararidir**.
    """
    return backtest(last=last, banko_esik=banko, uclu_esik=uclu, sweep=sweep,
                    sezon=sezon, strateji=strateji, butce_tl=butce_tl)


def takimlar_payload(lig: str | None = None,
                     sezon: str | None = None) -> dict[str, Any]:
    """Kucultulmus takim gucu tablosu — `/api/takimlar`in tek kaynagi.

    Govde her satirin yaninda `n` ve `kucultme`yi TASIMAK ZORUNDA: bu iki
    alan olmadan az macli bir takimin sayisi cok macli bir takiminkiyle
    ayni gorunur ve §7'nin "guvenilir gorunur ama gurultudur" itirazi
    aynen geri gelir.
    """
    from .takim_gucu import takim_tablosu

    return takim_tablosu(lig=lig, sezon=sezon)


def pazar_payload(yontem: str | None = None) -> dict[str, Any]:
    """1X2 disi pazarlarin olculmus ozeti — `/api/pazar`in tek kaynagi.

    `stats_payload`tan AYRI durmasi bilincli: alt/ust temiz bir ikili olay
    (Brier var), handikap kesirli getirili (Brier tanim geregi yok) ve
    bantlari farkli eksende (olasilik yerine cizgi). Tek govdede
    birlestirmek arayuzu ikisini ayni sanmaya iterdi.
    """
    from .odds import ARINDIRMA_VARSAYILAN

    return sezon_ozeti(yontem or ARINDIRMA_VARSAYILAN)
