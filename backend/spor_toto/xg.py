"""xG vekili — **korpusun kendi şut sayımı, ölçülmüş katsayılarla.**

`disari.TURETILEMEYEN` xG'yi kapalı tutuyordu ve gerekçesinin ilk yarısı
(Understat'ın `robots.txt`'i, fbref'in Cloudflare'i) artık geçersiz:
`hudl/open-data` olay düzeyi veriyi serbestçe yayımlıyor. **Gerekçenin ikinci
yarısı ise ayakta** — o depo Süper Lig'i ve korpusun çoğunluğunu oluşturan
alt İngiliz liglerini kapsamıyor, korpus penceresiyle kesişimi 92 maç ve
canlı akışı yok. Bu yüzden xG üretimde bir **girdi** olamaz.

Bu modül farklı bir şey yapar. Korpus zaten `ev_sut`/`ev_isabet` taşıyor;
onlardan bir "fakir adamın xG'si" kurulabilir ama katsayısı bugüne kadar
**keyfî** olurdu. `scripts/build_xg.py` o katsayıyı StatsBomb'un 2015/16 dört
lig kesitinde (1.517 maç) gerçek xG'ye karşı **ölçüyor**; burada okunan şey
o ölçümün sonucudur. StatsBomb böylece üretim girdisi değil **kalibrasyon
referansı** olur ve veri hiçbir zaman bu depoya girmez.

─── Neden `form_isabet_farki` ile aynı şekil ────────────────────────────

`egitim._form_tablosu` zaten isabetli şut farkının yuvarlanan ortalamasını
üretiyor (`form_isabet_farki`) ve penceresi 5. Buradaki özellik **birebir
aynı şekildedir**, tek farkla: ham sayım yerine kalibre edilmiş beklenen gol.
Aynı pencere, aynı sıralama, aynı "önce oku sonra işle" disiplini.

Bu bilerek böyle: iki özellik aynı kesitte yan yana ölçüldüğünde soru keskin
olur — **kalibrasyon ham sayımın üstüne bir şey koyuyor mu?** Pencereyi ya da
şekli değiştirseydik, aradaki fark kalibrasyonun mu yoksa şeklin mi olduğunu
söyleyemezdik.

─── Katsayı dosyası yoksa ───────────────────────────────────────────────

`katsayilar()` boş döner, `xg_tablosu` her maç için `xg_var=False` ve nötr 0
üretir. `sehir.sehir_tablosu` ile aynı sözleşme: dosya yoksa **çağıran karar
verir**, modül uydurmaz. `scripts/check.sh` ağsız koştuğu için testler
commit edilmiş katsayı dosyasını okur; üreticiyi koşmaz.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_KALIBRASYON = KOK / "data" / "xg" / "xg_kalibrasyon.json"

#: Yuvarlanan pencere — `egitim.FORM_PENCERE` ile **kasitla ayni** (bkz.
#: modul docstring'i: iki ozellik yan yana olculebilsin diye).
XG_PENCERE = 5


@lru_cache(maxsize=2)
def katsayilar(yol: str | None = None) -> dict[str, dict[str, float]]:
    """`{"ev": {...}, "dep": {...}}`. Dosya yoksa **boş** — çağıran karar verir.

    Yalnızca `katsayilar` bloğu döner; `lig_disarida` bölümü tanılamadır ve
    tahmin yolunda kullanılmaz (`scripts/build_xg.py` onu rapora yazar).
    """
    p = Path(yol) if yol else VARSAYILAN_KALIBRASYON
    if not p.exists():
        return {}
    try:
        ham = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    blok = ham.get("katsayilar") or {}
    out: dict[str, dict[str, float]] = {}
    for yan in ("ev", "dep"):
        k = blok.get(yan)
        if not k:
            continue
        try:
            out[yan] = {"isabet": float(k["isabet"]),
                        "isabetsiz": float(k["isabetsiz"]),
                        "sabit": float(k["sabit"])}
        except (KeyError, TypeError, ValueError):
            return {}
    return out if len(out) == 2 else {}


def xg_vekili(sut: int | None, isabet: int | None, ev_mi: bool,
              kat: dict[str, dict[str, float]] | None = None) -> float | None:
    """Kalibre edilmiş beklenen gol. Sayım ya da katsayı yoksa `None`.

    `None` ile `0.0` farklı şeylerdir ve karıştırılırsa özellik sessizce
    seyrelir: şut verisi olmayan bir maç "hiç şut çekilmedi" gibi görünürdü.
    Çağıran ayrımı korur (`xg_tablosu` o maçı geçmişe katmaz).

    Sonuç negatife düşemez: uydurma doğrusaldır ve `dep` tarafının sabiti
    negatif çıktı (ölçüldü), yani sıfır şutlu bir maç için model eksi beklenen
    gol verirdi. Beklenen gol tanım gereği negatif olamaz.
    """
    k = katsayilar() if kat is None else kat
    if not k or sut is None or isabet is None:
        return None
    c = k["ev" if ev_mi else "dep"]
    isabetsiz = max(0, sut - isabet)
    return max(0.0, c["isabet"] * isabet + c["isabetsiz"] * isabetsiz + c["sabit"])


def xg_tablosu(satirlar: Sequence[dict[str, Any]],
               yol: str | None = None) -> list[dict[str, Any]]:
    """Her maç için, **o maçtan önceki** maçlardan hesaplanmış xG vekili farkı.

    `elo.elo_tablosu` ve `egitim._form_tablosu` ile aynı sözleşme: kronolojik
    gez, **önce oku sonra işle**, dönen kayıtlar girdiyle aynı indekste.

    Takım başına tutulan büyüklük maç başına *net* vekildir (attığı beklenen
    gol eksi yediği). `xg_farki` ev takımının net ortalaması eksi deplasmanın:
    pozitif = ev lehine, projedeki bütün yön özellikleriyle aynı işaret
    sözleşmesi.

    `xg_var=False` olan maçta `xg_farki` nötr 0'dır — "bilinmiyor" ile "denk"
    aynı davranışa düşer (`form_var`, `elo_var` ile birebir aynı kural).
    """
    bos = {"xg_var": False, "xg_farki": 0.0}
    kat = katsayilar(yol)
    if not kat:
        return [dict(bos) for _ in satirlar]

    sirali = sorted(range(len(satirlar)),
                    key=lambda i: (satirlar[i]["tarih"], satirlar[i]["lig"],
                                   satirlar[i]["ev"]))
    gecmis: dict[str, list[float]] = {}
    out: list[dict[str, Any]] = [dict(bos) for _ in satirlar]

    def ortalama(takim: str) -> float | None:
        kayit = gecmis.get(takim, [])
        if len(kayit) < XG_PENCERE:
            return None
        son = kayit[-XG_PENCERE:]
        return sum(son) / len(son)

    for i in sirali:
        r = satirlar[i]
        # --- ONCE OKU ---
        ev_ort, dep_ort = ortalama(r["ev"]), ortalama(r["dep"])
        if ev_ort is not None and dep_ort is not None:
            out[i] = {"xg_var": True, "xg_farki": ev_ort - dep_ort}

        # --- SONRA ISLE ---
        ev_xg = xg_vekili(r.get("ev_sut"), r.get("ev_isabet"), True, kat)
        dep_xg = xg_vekili(r.get("dep_sut"), r.get("dep_isabet"), False, kat)
        if ev_xg is None or dep_xg is None:
            continue  # sut istatistigi olmayan mac gecmise katilmaz
        gecmis.setdefault(r["ev"], []).append(ev_xg - dep_xg)
        gecmis.setdefault(r["dep"], []).append(dep_xg - ev_xg)

    return out


def kapsama(satirlar: Sequence[dict[str, Any]],
            yol: str | None = None) -> dict[str, Any]:
    """Korpusun ne kadarında xG vekili **hesaplanabiliyor** — tanılama.

    `sehir.kapsama` ile aynı iş: bir özellik eklendiğinde ilk sorulacak şey
    "kaç maçta tanımlı" olmalıdır, yoksa katsayı sıfıra yakın çıkar ve bu
    "sinyal yok" diye okunur — oysa sebep seyrelmedir.
    """
    tablo = xg_tablosu(satirlar, yol)
    n = len(satirlar)
    var = sum(1 for t in tablo if t["xg_var"])
    return {
        "mac": n, "xg_var": var,
        "oran": (var / n) if n else 0.0,
        "kalibrasyon_var": bool(katsayilar(yol)),
    }
