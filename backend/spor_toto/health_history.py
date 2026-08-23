"""Sunucu tarafi saglik gecmisi ve durum degisimi bildirimi.

Iki soru bu modulun varlik sebebi:

1. **"Ne zamandan beri kirmizi?"** Sayfadaki gecmis seridi oturum icidir;
   sekme kapaninca gider ve zaten yalnizca o sekmenin gordugu kosulari
   bilir. Sunucudaki halka tampon, sureci ayakta oldugu surece hatirlar.
2. **"Kirmiziya dondugunde kimse haberdar oluyor mu?"** Bugune kadar
   cevap hayirdi: birinin sayfaya bakiyor olmasi gerekiyordu.

Kasitli sinirlar:

- **Bellekte tutulur, diske yazilmaz.** Kalici depolama bir bagimlilik ve
  bir bakim yuku getirir; bu katmanin sordugu soru "son N kosuda ne oldu",
  "gecen ay ne oldu" degil. Surec yeniden basladiginda gecmis sifirlanir ve
  rapor bunu `ornek.baslangic` ile zaten soyler.
- **Yalniz DEGISIM bildirilir.** Her kirmizi kosuda bildirim gondermek,
  bildirimleri okunmaz hale getirir; okunmayan alarm, alarmsizliktan
  kotudur cunku korunuyor sanirsin.
- **Varsayilan KAPALI.** Bildirim yalnizca `HEALTH_ALARM_URL` tanimliysa
  gonderilir. Tanimli degilse durum degisimleri yine kaydedilir, disari
  hicbir sey cikmaz.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Son N kosunun OZETI (rapor gövdeleri degil): 200 kayit birkac on KB tutar
# ve saatlerce gecmis demektir.
GECMIS_SINIRI = int(os.environ.get("HEALTH_HISTORY_LIMIT", "200"))

ALARM_URL = os.environ.get("HEALTH_ALARM_URL", "").strip()
ALARM_TIMEOUT_S = float(os.environ.get("HEALTH_ALARM_TIMEOUT_S", "5"))

_kayitlar: deque[dict[str, Any]] = deque(maxlen=max(1, GECMIS_SINIRI))
_kilit = threading.Lock()


def _durum(rapor: dict[str, Any]) -> str:
    if not rapor.get("ok"):
        return "UNHEALTHY"
    return "DEGRADED" if rapor.get("degraded") else "HEALTHY"


def kaydet(rapor: dict[str, Any]) -> dict[str, Any]:
    """Rapor ozetini tampona yazar; durum DEGISTIYSE bildirimi tetikler.

    Kismi kosular (`?only=`) tampona GIRMEZ: zaman serisi ancak ayni sey
    olculdugunde karsilastirilabilir, yoksa "5/5 gecti" satiri "21/21
    gecti" satirinin yaninda ayni sey gibi gorunur.
    """
    if rapor.get("summary", {}).get("kismi"):
        return {"kaydedildi": False, "sebep": "kısmi koşu"}

    kayit = {
        "timestamp": rapor.get("timestamp"),
        "durum": _durum(rapor),
        "ok": bool(rapor.get("ok")),
        "degraded": bool(rapor.get("degraded")),
        "passed": rapor.get("passed"),
        "total": rapor.get("total"),
        "duration_ms": rapor.get("duration_ms"),
        "dusenler": [c["name"] for c in rapor.get("checks", []) if not c["ok"]],
        "yavaslar": [c["name"] for c in rapor.get("checks", []) if c.get("yavas")],
        "version": rapor.get("version"),
    }

    with _kilit:
        onceki = _kayitlar[-1]["durum"] if _kayitlar else None
        _kayitlar.append(kayit)
    degisti = onceki is not None and onceki != kayit["durum"]

    if degisti:
        _bildir(onceki, kayit)
    return {"kaydedildi": True, "degisim": degisti,
            "onceki": onceki, "durum": kayit["durum"]}


def gecmis(limit: int = 50) -> list[dict[str, Any]]:
    """En yeniden en eskiye. Tampon kopyalanir; cagiran taraf mutasyon yapamaz."""
    with _kilit:
        kayitlar = list(_kayitlar)
    return list(reversed(kayitlar))[:max(1, limit)]


def ozet() -> dict[str, Any]:
    """"Ne zamandan beri bu durumdayiz?" — tek cevaplanmasi gereken soru."""
    with _kilit:
        kayitlar = list(_kayitlar)
    if not kayitlar:
        return {"kayit": 0, "durum": None, "bu_durumda_kosu": 0,
                "degisim_zamani": None, "son_saglikli": None}

    son = kayitlar[-1]
    ayni = 0
    for k in reversed(kayitlar):
        if k["durum"] != son["durum"]:
            break
        ayni += 1
    # Durumun BASLADIGI kosunun zamani: "14:02'den beri kirmizi".
    degisim = kayitlar[len(kayitlar) - ayni]["timestamp"]
    son_saglikli = next(
        (k["timestamp"] for k in reversed(kayitlar) if k["durum"] == "HEALTHY"),
        None,
    )
    return {
        "kayit": len(kayitlar),
        "durum": son["durum"],
        "bu_durumda_kosu": ayni,
        "degisim_zamani": degisim,
        "son_saglikli": son_saglikli,
        "sinir": _kayitlar.maxlen,
        "alarm": bool(ALARM_URL),
    }


def temizle() -> None:
    """Yalnizca testler icin: tampon sureç omurludur."""
    with _kilit:
        _kayitlar.clear()


def _bildir(onceki: str | None, kayit: dict[str, Any]) -> None:
    """Durum degisimini disari haber verir (varsayilan: kapali).

    Gonderim ARKA PLANDA yapilir ve her hatasi yutulur: bildirim
    gonderilemedigi icin saglik ucunun 500 dondurmesi, cozmeye calistigi
    sorundan buyuk bir sorun olurdu.
    """
    govde = {
        "kaynak": "spor-toto-health",
        "onceki_durum": onceki,
        "durum": kayit["durum"],
        "zaman": kayit["timestamp"] or datetime.now(timezone.utc).isoformat(),
        "passed": kayit["passed"],
        "total": kayit["total"],
        "dusenler": kayit["dusenler"],
        "yavaslar": kayit["yavaslar"],
        "version": kayit["version"],
    }
    logger.warning("Sağlık durumu değişti: %s -> %s (düşen: %s)",
                   onceki, kayit["durum"], ", ".join(kayit["dusenler"]) or "-")
    if not ALARM_URL:
        return

    def _gonder() -> None:
        try:
            istek = urllib.request.Request(
                ALARM_URL,
                data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(istek, timeout=ALARM_TIMEOUT_S).close()
        except (urllib.error.URLError, OSError, ValueError) as e:
            logger.warning("Sağlık alarmı gönderilemedi: %s", e)

    threading.Thread(target=_gonder, name="saglik-alarm", daemon=True).start()
