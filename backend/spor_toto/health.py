"""Sistem sağlık kontrolü — tüm katmanları tek vücut olarak doğrular.

Kullanım:
  python -m spor_toto.health
  python -m spor_toto.health --interval 60
  python -m spor_toto.health --json
  python -m spor_toto.health --only olasilik        # tek kategori
  python -m spor_toto.health --only fix16_garanti   # tek kontrol
  python -m spor_toto.health --list                 # kontrol envanteri
"""

from __future__ import annotations

import argparse
import math
import os
import platform
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import __version__
from .core import (
    HAS_SCIPY,
    Encoder,
    Fix16Hatasi,
    dogrula_kaplama,
    distance_layers,
    merge_rows,
    olasilik_raporu,
    parse_picks,
    row_cost,
    rows_to_points,
    solve_fix16,
    solve_by_blocks,
    solve_heuristic,
)
from .analysis import match_error_frequency, monte_carlo_report
from .bayes import posteriors_only
from .markov import markov_report
from .report import basliklar

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"

# Mod envanteri KUCUK bir kupon uzerinde kosar: 7 cifte -> 128 nokta, alt
# sinir 16 kolon. Sebep sure butcesi (§4.3): ayni denetim ORNEK uzerinde
# ILP'yi 11 saniyeye cikariyor, kanit degeri ise degismiyor — "ilan edilen
# her mod calisiyor ve garanti bayragini tutuyor mu" sorusu uzayin
# buyuklugunden bagimsizdir.
MOD_ORNEK = "1,1,1,1,1,1,1,10,10,10,10,10,10,10,1"
MOD_BUTCE = 24   # fix16 bedeli 16 kolon; plan bu butceye sigmak zorunda
MOD_MAXCOV_BUTCE = 8   # alt sinirin (16) ALTINDA: tam kaplama matematiksel
                       # olarak imkansiz, yani "garanti yok" ilani sinanabilir

SEMBOLLER = ("1", "0", "2")


@dataclass(frozen=True)
class KuponSinifi:
    """Cekirdek kontrollerin kostugu bir kupon sinifi.

    Beklenen sayilar tabloda YAZILIDIR: kontrol yalnizca "kaplama gecerli"
    demez, "bu sinif icin bedel tam olarak bu" der. Sessiz bir gerileme
    (ornegin fix16'nin bir sinifta 32 yerine 48 kolon uretmeye baslamasi)
    ancak boyle gorunur.
    """

    etiket: str
    picks: str
    uzay: int
    alt_sinir: int
    fix16_bedel: int


# Tek kupon sinifi kapsami dardi: 8 ciftlik kupon, motorun gordugu bicimlerin
# yalnizca biri. Siniflar SABIT ve deterministiktir — rastgele kupon uretmek
# kapsami genisletirdi ama arada bir dusen bir kontrol, hic olmayandan
# kotudur (§4, madde 1).
KUPON_SINIFLARI: Tuple[KuponSinifi, ...] = (
    KuponSinifi("8 çift", ORNEK, 256, 29, 32),
    KuponSinifi("7 çift + 8 banko", "1,1,1,1,1,1,1,10,10,10,10,10,10,10,1",
                128, 16, 16),
    KuponSinifi("9 çift", "1,10,10,12,0,10,2,10,1,12,02,1,10,2,10", 512, 52, 64),
    KuponSinifi("üçlü içeren", "1,10,102,12,0,10,2,10,1,12,02,1,10,2,10",
                768, 70, 96),
)

# Surecin ayaga kalktigi an. Iki yerde kullanilir: ornek kimligi (§7.8) ve
# ISINMA ayrimi (§7.1) — ilk kosu her zaman yavastir ve sure esikleri onu
# gerileme sanmamalidir.
_SUREC_BASLANGIC = time.monotonic()
_SUREC_BASLANGIC_ISO = datetime.now(timezone.utc).isoformat()

# Kategoriler, motorun katmanlarını izler: bir kontrol düştüğünde hatanın
# hangi katmanda olduğu isimden değil buradan okunur.
KATEGORILER: Tuple[Tuple[str, str, str], ...] = (
    ("cekirdek", "Çekirdek", "Kodlama, 14-garanti ve mesafe muhasebesi."),
    ("motor", "Çözücüler", "Alternatif motorların ürettiği kaplamalar."),
    ("olasilik", "Olasılık", "Exact, Monte Carlo, Bayes ve Markov hattı."),
    ("analiz", "Analiz", "Hata dağılımı ve seçim dışı fire katmanı."),
    ("ucuca", "Uçtan uca", "API'nin döndürdüğü sonucun bütünlüğü."),
    ("ortam", "Ortam", "Çalışan sürümün bağımlılık envanteri."),
)
KATEGORI_ETIKET: Dict[str, str] = {k: e for k, e, _ in KATEGORILER}


@dataclass(frozen=True)
class CheckSpec:
    """Tek bir değişmezin tanımı.

    `aciklama` kontrolün NEYİ koruduğunu söyler; arayüz kriptik `name`
    yerine bunu gösterir. `critical=False` olan kontroller bilgi amaçlıdır:
    düşmeleri raporu UNHEALTHY yapmaz, yalnızca "degraded" işaretler.
    """

    name: str
    category: str
    aciklama: str
    fn: Callable[[], str]
    critical: bool = True
    # Beklenen ust sure (ms). Asilmasi kontrolu DUSURMEZ — yalnizca raporu
    # `degraded` isaretler ve sayfada sure cubugunu ambere cevirir. Bir
    # kontrolun 8 ms'den 400 ms'ye cikmasi hicbir degismezi kirmaz ama bir
    # seyin degistigini kesin olarak soyler; bugune dek bunu yalnizca goz
    # yakaliyordu. Bant, olculen isinmis surenin ~3 katidir: dar bir bant
    # gurultu uretir, gurultu de raporu gormezden gelmeyi ogretir (§4.1).
    butce_ms: Optional[float] = None


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    duration_ms: float = 0.0
    category: str = "cekirdek"
    aciklama: str = ""
    critical: bool = True
    butce_ms: Optional[float] = None
    # Sure butcesi asildi mi. `isinma` kosusunda HER ZAMAN False'tur.
    yavas: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "duration_ms": round(self.duration_ms, 1),
            "category": self.category,
            "category_label": KATEGORI_ETIKET.get(self.category, self.category),
            "aciklama": self.aciklama,
            "critical": self.critical,
            "butce_ms": self.butce_ms,
            "yavas": self.yavas,
        }


@dataclass
class HealthReport:
    version: str
    timestamp: str
    ok: bool
    checks: List[CheckResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    degraded: bool = False

    def kategoriler(self) -> List[dict]:
        """Kontrolleri kategoriye göre, tanım sırasını koruyarak toplar."""
        out: List[dict] = []
        for key, etiket, aciklama in KATEGORILER:
            uyan = [c for c in self.checks if c.category == key]
            if not uyan:
                continue
            out.append({
                "id": key,
                "label": etiket,
                "aciklama": aciklama,
                "passed": sum(1 for c in uyan if c.ok),
                "failed": sum(1 for c in uyan if not c.ok),
                "total": len(uyan),
                "duration_ms": round(sum(c.duration_ms for c in uyan), 1),
                "ok": all(c.ok or not c.critical for c in uyan),
            })
        return out

    def to_dict(self) -> dict:
        en_yavas = max(self.checks, key=lambda c: c.duration_ms, default=None)
        butce_asan = [c.name for c in self.checks if c.yavas]
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "ok": self.ok,
            "degraded": self.degraded,
            "passed": sum(1 for c in self.checks if c.ok),
            "failed": sum(1 for c in self.checks if not c.ok),
            "total": len(self.checks),
            "duration_ms": round(sum(c.duration_ms for c in self.checks), 1),
            "categories": self.kategoriler(),
            "checks": [c.to_dict() for c in self.checks],
            "summary": {
                **self.summary,
                "slowest": (
                    {"name": en_yavas.name, "duration_ms": round(en_yavas.duration_ms, 1)}
                    if en_yavas
                    else None
                ),
                "butce_asan": butce_asan,
            },
        }


def _run(spec: CheckSpec, isinma: bool = False) -> CheckResult:
    """Tek kontrolu kosturur ve suresini butcesiyle karsilastirir.

    `isinma` True ise sure butcesi UYGULANMAZ: surecin ilk raporu numpy/scipy
    ilk import'unu, veri setinin ve oran arsivinin ilk okunmasini da ustlenir
    (olculdu: ~2,1 sn'ye karsi ~500 ms). Isinmayi gerileme saymak, her soguk
    baslangicta yanlis alarm uretirdi.
    """
    t0 = time.perf_counter()
    ortak = {
        "category": spec.category,
        "aciklama": spec.aciklama,
        "critical": spec.critical,
        "butce_ms": spec.butce_ms,
    }
    try:
        detail = spec.fn() or "ok"
        ok, sonuc_detay = True, detail
    except Exception as e:
        ok, sonuc_detay = False, f"{type(e).__name__}: {e}{_kirilma_yeri(e)}"

    sure = (time.perf_counter() - t0) * 1000
    yavas = bool(
        spec.butce_ms is not None and not isinma and sure > spec.butce_ms
    )
    if yavas and ok:
        # Sapma detaya da yazilir: rapora bakan kisi sayilari gormeden
        # "yavas" etiketine inanmak zorunda kalmasin.
        sonuc_detay = f"{sonuc_detay} | süre {sure:.0f} ms > bütçe {spec.butce_ms:.0f} ms"
    return CheckResult(spec.name, ok, sonuc_detay, sure, yavas=yavas, **ortak)


def _kirilma_yeri(e: BaseException) -> str:
    """Istisnanin KIRILDIGI son kare — "health.py:226" gibi.

    Yassiltilmis bir `AssertionError:` mesaji canlida hangi degismezin
    dustugunu soylemez; assert'ler cogunlukla mesajsizdir. Son kare birkac
    karakter yer kaplar ve hata ayiklamayi kaynak okumaktan kurtarir.
    """
    tb = traceback.extract_tb(e.__traceback__)
    if not tb:
        return ""
    son = tb[-1]
    return f" @ {os.path.basename(son.filename)}:{son.lineno}"


def _approx(a: float, b: float, rel: float = 1e-9) -> bool:
    return abs(a - b) <= rel * max(1.0, abs(b))


def _probs_on_selections(enc: Encoder) -> List[Dict[str, float]]:
    out: List[Dict[str, float]] = []
    for sel in enc.selections:
        p = {s: 0.0 for s in SEMBOLLER}
        u = 1.0 / len(sel) if sel else 1.0 / 3
        for s in sel:
            p[s] = u
        out.append(p)
    return out


def _check_encoder() -> str:
    """Kodlama katmani — DORT kupon sinifinda.

    Arama uzayi ve teorik alt sinir, sonraki her hesabin zeminidir; yanlis
    uzayda dogru hesap yapilamaz. Tek sinif yerine dort sinif kosar: bankosu
    cok olan, ciftesi cok olan ve UCLU iceren kuponlar farkli kod yollari
    kullanir (alfabe boyu 3'e cikar).
    """
    olcum: List[str] = []
    for s in KUPON_SINIFLARI:
        enc = Encoder(parse_picks(s.picks))
        assert enc.total_len == 15, f"{s.etiket}: {enc.total_len} maç"
        assert enc.space_size() == s.uzay, (
            f"{s.etiket}: uzay {enc.space_size()} ≠ {s.uzay}")
        assert enc.lower_bound() == s.alt_sinir == math.ceil(s.uzay / enc.ball_size())
        olcum.append(f"{s.etiket}={s.uzay}/{s.alt_sinir}")
    return f"sınıf={len(KUPON_SINIFLARI)} " + " ".join(olcum)


def _check_fix16_garanti() -> str:
    """Urunun ana vaadi — DORT kupon sinifinda.

    Beklenen bedel her sinif icin tabloda yazilidir (`KUPON_SINIFLARI`):
    kontrol "kaplama gecerli" demekle yetinmez, "bu sinifta bedel tam olarak
    bu" der. Sessiz bir gerileme ancak boyle gorunur.
    """
    olcum: List[str] = []
    for s in KUPON_SINIFLARI:
        enc = Encoder(parse_picks(s.picks))
        cols, _ = solve_fix16(enc)
        rows = merge_rows(cols)
        worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
        assert len(rows) == 16, f"{s.etiket}: {len(rows)} satır"
        assert worst <= 1 and acik == 0, f"{s.etiket}: worst={worst} acik={acik}"
        assert set(rows_to_points(rows)) == set(cols), f"{s.etiket}: satır↔kolon"
        assert sum(row_cost(r) for r in rows) == len(cols), f"{s.etiket}: bedel"
        assert len(cols) == s.fix16_bedel, (
            f"{s.etiket}: bedel {len(cols)} ≠ {s.fix16_bedel}")
        olcum.append(f"{s.etiket}={len(cols)}")
    return f"sınıf={len(KUPON_SINIFLARI)} rows=16 worst≤1 bedel: " + " ".join(olcum)


def _check_fix16_yetersiz_cifte() -> str:
    enc = Encoder(parse_picks("10,10,10,10,10,10,1,1,1,1,1,1,1,1,1"))
    try:
        solve_fix16(enc)
        raise AssertionError("Fix16Hatasi bekleniyordu")
    except Fix16Hatasi:
        return "6 cifte reddedildi"


def _check_distance_layers() -> str:
    """Mesafe muhasebesi — DORT kupon sinifinda.

    0 ve 1 hatali noktalarin toplami arama uzayinin TAMAMINI vermeli:
    tutmazsa kapsama raporundaki her yuzde yanlistir.
    """
    olcum: List[str] = []
    for s in KUPON_SINIFLARI:
        enc = Encoder(parse_picks(s.picks))
        cols, _ = solve_fix16(enc)
        dist = distance_layers(cols, enc.alphabet_sizes)
        assert sum(dist.values()) == enc.space_size() == s.uzay, (
            f"{s.etiket}: katman toplamı {sum(dist.values())} ≠ {s.uzay}")
        assert dist.get(0, 0) == len(set(cols)), f"{s.etiket}: d=0 katmanı"
        assert max(dist) <= 1, f"{s.etiket}: d={max(dist)} noktası açıkta"
        olcum.append(f"{s.etiket}={dist.get(0, 0)}+{dist.get(1, 0)}")
    return f"sınıf={len(KUPON_SINIFLARI)} d0+d1=uzay: " + " ".join(olcum)


def _check_fix16_varyantlari() -> str:
    """
    `--variant` ile uretilen alternatif 16'liklar.

    Varyantlar kod tabanini karistirarak baska bir kaplama uretir; ama
    16-satir/14-garanti sozlesmesi HEPSI icin gecerli olmak zorundadir.
    Kirilirsa "varyant sec" dugmesi sessizce garantisiz kupon dagitir.
    """
    enc = Encoder(parse_picks(ORNEK))
    kanonik, _ = solve_fix16(enc, variant=0)
    farkli = 0
    for v in (1, 2, 3):
        cols, _ = solve_fix16(enc, variant=v)
        rows = merge_rows(cols)
        worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
        assert len(rows) == 16, f"varyant {v}: {len(rows)} satır"
        assert worst <= 1 and acik == 0, f"varyant {v}: worst={worst} acik={acik}"
        assert sum(row_cost(r) for r in rows) == len(cols)
        if set(cols) != set(kanonik):
            farkli += 1
    # Varyantlar ayni kaplamayi tekrarlarsa secenek olmaktan cikar.
    assert farkli >= 1, "hicbir varyant kanonik kaplamadan farkli degil"
    return f"varyant=1..3 satir=16 worst<=1 farkli={farkli}/3"


def _check_blok_motor() -> str:
    enc = Encoder(parse_picks(ORNEK))
    r = solve_by_blocks(enc)
    assert r is not None
    cols, _ = r
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert worst <= 1 and acik == 0
    f16, _ = solve_fix16(enc)
    assert len(cols) <= len(f16)
    return f"blok_bedel={len(cols)} <= fix16={len(f16)}"


def _check_heuristic() -> str:
    picks = "10,10,10,10,10,10,1,1,1,1,1,1,1,1,1"
    enc = Encoder(parse_picks(picks))
    cols = solve_heuristic(enc, trials=2, ls_iters=3000, seed=42)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert worst <= 1 and acik == 0
    return f"heuristic_bedel={len(cols)}"


def _check_mod_envanteri() -> str:
    """
    Meta'da ILAN EDILEN her mod gercekten kosuyor mu ve `garanti` bayragi
    dogru mu?

    Saglik daha once yalnizca fix16/blok/sezgisel kosturuyordu; `auto`,
    `exact`, `butce` ve `maxcov` hic sinanmiyordu. Bozuk bir mod, meta'da
    ilan edildigi icin arayuzde secilebilir kalir ve dogrudan kullaniciya
    carpar.

    Baglanan degismez sudur: **garanti: True ilan eden bir mod acik nokta
    birakamaz; garanti: False ilan eden maxcov ise alt sinirin altindaki bir
    butceyle gercekten kaplayamaz.** Ikincisi kombinatoryal zorunluluktur:
    8 kolonun toplam topu 8*(1+ekseriyet) < 128'dir.
    """
    from .engines import (
        engine_params, run_auto, run_block, run_butce, run_exact, run_fix16,
        run_heuristic, run_maxcov,
    )
    from .meta import MODES

    enc = Encoder(parse_picks(MOD_ORNEK))
    # ILP'yi ve local search'u sure butcesine cek: burada olculen sey
    # kalite degil, modun ayakta olup olmadigi.
    eng = engine_params(trials=1, ls_iters=2_000, time_limit=10.0,
                        exact_limit=256, block_limit=256)

    kosucular: Dict[str, Callable[[], Dict[str, Any]]] = {
        "fix16": lambda: run_fix16(enc),
        "auto": lambda: run_auto(enc, eng),
        "exact": lambda: run_exact(enc, eng),
        "block": lambda: run_block(enc, eng),
        "heuristic": lambda: run_heuristic(enc, eng),
        "butce": lambda: run_butce(enc, MOD_BUTCE),
        "maxcov": lambda: run_maxcov(enc, MOD_MAXCOV_BUTCE),
    }
    eksik = [m["id"] for m in MODES if m["id"] not in kosucular]
    assert not eksik, f"meta'da ilan edilen ama koşulmayan mod: {eksik}"

    kosan: List[str] = []
    atlanan: List[str] = []
    for mod in MODES:
        mid = mod["id"]
        if mod["needs_scipy"] and not HAS_SCIPY:
            # Bilgi amacli scipy_flag zaten bunu ayrica raporluyor.
            atlanan.append(mid)
            continue
        r = kosucular[mid]()
        e = r.get("enc", enc)
        cols = r["cols"]
        assert cols, f"{mid}: bos kaplama"
        assert r.get("baslik"), f"{mid}: baslik yok"
        worst, acik = dogrula_kaplama(cols, e.alphabet_sizes)
        if mod["garanti"]:
            assert worst <= 1 and acik == 0, (
                f"{mid} meta'da garanti ilan ediyor ama worst={worst} acik={acik}"
            )
            assert len(merge_rows(cols)) >= 1
        else:
            assert acik > 0, (
                f"{mid} garanti VERMEDIGINI ilan ediyor ama tam kapladi — "
                f"ya bayrak ya kaplama yanlis"
            )
            assert len(cols) <= MOD_MAXCOV_BUTCE, f"{mid} bütçeyi aştı"
            assert r["kapsanan"] + acik == e.space_size(), "kapsama muhasebesi tutmuyor"
        if mod["needs_budget"]:
            # Butce modunun urettigi kupon, verilen butceyi asamaz.
            assert len(cols) <= (MOD_BUTCE if mid == "butce" else MOD_MAXCOV_BUTCE), \
                f"{mid} bütçeyi aştı: {len(cols)}"
        kosan.append(mid)

    atlama = f" atlanan={','.join(atlanan)}" if atlanan else ""
    return f"mod={len(kosan)}/{len(MODES)} uzay={enc.space_size()}{atlama}"


def _check_meta_sozlesmesi() -> str:
    """
    `/api/meta` sozlesmesi. Formul sayfasinin TAMAMI modlari, preset'leri,
    motor varsayilanlarini ve sinirlari buradan okur ve hicbirini sabit
    kodlamaz. Meta bozulursa ana sayfa coker; motor ise sapasaglam kalir,
    yani baska hicbir kontrol bunu yakalamaz.

    Denetlenen sey degerlerin "guzelligi" degil, ic tutarlilik: her sinirda
    min <= varsayilan <= max, preset listesinin motordaki tabloyla ortusmesi,
    scipy bayraginin gercekle ayni olmasi.
    """
    from . import __version__ as surum
    from .bayes import STRENGTH_PRESETS
    from .history import MATCH_COUNT as VERI_MAC_SAYISI
    from .meta import MODE_IDS, meta_payload

    m = meta_payload(surum)
    assert m["version"] == surum
    assert m["has_scipy"] is HAS_SCIPY, "meta scipy'yi motordan farklı biliyor"

    enc = Encoder(parse_picks(ORNEK))
    assert m["match_count"] == enc.total_len == VERI_MAC_SAYISI, (
        f"maç sayısı ayrışmış: meta={m['match_count']} motor={enc.total_len} "
        f"veri={VERI_MAC_SAYISI}"
    )
    assert tuple(m["symbols"]) == SEMBOLLER

    ids = [x["id"] for x in m["modes"]]
    assert len(ids) == len(set(ids)), "mod kimlikleri tekil değil"
    assert set(ids) == MODE_IDS
    for mod in m["modes"]:
        for alan in ("label", "aciklama"):
            assert mod.get(alan), f"{mod['id']}: {alan} boş"
        for bayrak in ("garanti", "needs_budget", "needs_scipy"):
            assert isinstance(mod.get(bayrak), bool), f"{mod['id']}: {bayrak}"
    assert {x["id"] for x in m["modes"] if x["needs_scipy"]} == {"exact"}
    assert {x["id"] for x in m["modes"] if x["needs_budget"]} == {"butce", "maxcov"}
    assert {x["id"] for x in m["modes"] if not x["garanti"]} == {"maxcov"}

    for ad, lim in m["limits"].items():
        assert lim["min"] <= lim["max"], f"{ad}: min > max"
        if "default" in lim:
            assert lim["min"] <= lim["default"] <= lim["max"], \
                f"{ad}: varsayılan bandın dışında"
    for ad, deger in m["engine_defaults"].items():
        lim = m["limits"].get(ad)
        if lim is not None:
            assert lim["min"] <= deger <= lim["max"], \
                f"engine_defaults[{ad}]={deger} sınırların dışında"

    presetler = {p["id"]: p for p in m["bayes_presets"]}
    assert set(presetler) == set(STRENGTH_PRESETS), "preset listesi motorla ayrışmış"
    for ad, p in presetler.items():
        kaynak = STRENGTH_PRESETS[ad]
        assert _approx(p["prior_strength"], kaynak["prior_strength"])
        assert _approx(p["evidence_strength"], kaynak["evidence_strength"])

    bt = m["backtest"]
    assert bt["banko_default"] in bt["banko_grid"], "banko varsayılanı ızgarada yok"
    assert bt["uclu_default"] in bt["uclu_grid"], "üçlü varsayılanı ızgarada yok"

    return (f"mod={len(ids)} preset={len(presetler)} limit={len(m['limits'])} "
            f"mac={m['match_count']}")


def _check_olasilik_exact() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_selections(enc)
    rap = olasilik_raporu(enc, cols, probs)
    assert 0 <= rap.p_15 <= 1
    assert 0 <= rap.p_kume_ici <= 1
    assert _approx(rap.p_15 + rap.p_14, rap.p_kume_ici)
    assert rap.p_kume_ici > 0.99
    return f"p_ici={rap.p_kume_ici:.4f} p15={rap.p_15:.4f} p14={rap.p_14:.4f}"


def _check_monte_carlo() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_selections(enc)
    mc = monte_carlo_report(enc, cols, probs, n_samples=5_000, seed=42)
    assert mc["n_samples"] == 5_000
    for key in ("kume_ici", "p15", "p14", "p13", "p12"):
        assert 0.0 <= mc[key]["p"] <= 1.0
        assert mc[key]["ci95"] >= 0.0
    assert mc["kume_ici"]["p"] > 0.9
    rap = olasilik_raporu(enc, cols, probs)
    assert abs(mc["kume_ici"]["p"] - rap.p_kume_ici) < 0.05
    return (
        f"n=5000 kume_ici={mc['kume_ici']['pct']}% "
        f"p15={mc['p15']['pct']}%±{mc['p15']['ci95']}"
    )


def _check_bayes() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    evidence = _probs_on_selections(enc)
    posts = posteriors_only(
        enc.selections, evidence, prior_strength=1.0, evidence_strength=10.0)
    assert len(posts) == 15
    assert all(abs(sum(p.values()) - 1.0) < 1e-9 for p in posts)
    rap = olasilik_raporu(enc, cols, posts)
    assert rap.p_kume_ici > 0.99
    return f"posteriors=15 p_ici={rap.p_kume_ici:.4f}"


def _check_bayes_presetleri() -> str:
    """
    Meta'da ILAN EDILEN Bayes preset'lerinin hepsi.

    `bayes_dirichlet` elle verilen guclerle kosuyor, preset'lerle degil;
    CLI duman testi de yalnizca `dengeli`yi kullaniyordu. Bozuk bir preset
    (ornegin `sadece_prior`, evidence_strength=0) hicbir yerde kosmadan
    kullaniciya gidiyordu.

    Iki degismez: (1) her preset'in posterior'lari 1'e toplanir,
    (2) posterior hangi preset ile uretilirse uretilsin KAPLAMAYI
    degistirmez — Bayes tahmini yumusatir, garantiyi degil.
    """
    from .bayes import STRENGTH_PRESETS, recommend_strengths

    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    evidence = _probs_on_selections(enc)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert worst <= 1 and acik == 0

    olculen: List[str] = []
    for ad in STRENGTH_PRESETS:
        v = recommend_strengths(ad)
        assert v == dict(STRENGTH_PRESETS[ad]), f"{ad}: preset çözümlemesi ayrıştı"
        posts = posteriors_only(
            enc.selections, evidence,
            prior_strength=v["prior_strength"],
            evidence_strength=v["evidence_strength"],
        )
        assert len(posts) == enc.total_len, f"{ad}: {len(posts)} posterior"
        for p in posts:
            assert abs(sum(p.values()) - 1.0) < 1e-9, f"{ad}: posterior 1'e toplanmıyor"
            assert all(x >= 0.0 for x in p.values()), f"{ad}: negatif olasılık"
        rap = olasilik_raporu(enc, cols, posts)
        assert rap.p_kume_ici > 0.99, f"{ad}: kaplama olasılığı düştü"
        assert _approx(rap.p_15 + rap.p_14, rap.p_kume_ici), f"{ad}: p15+p14 ayrıştı"
        olculen.append(f"{ad}={rap.p_kume_ici:.3f}")

    # Bilinmeyen bir preset sessizce patlamak yerine dengeliye duser.
    assert recommend_strengths("boyle_bir_preset_yok") == dict(STRENGTH_PRESETS["dengeli"])
    return f"preset={len(olculen)} " + " ".join(olculen)


def _check_markov() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    probs = _probs_on_selections(enc)
    rep = markov_report(enc, cols, probs)
    assert rep["summary"]["p_kume_ici"] > 0.99
    assert rep["summary"]["p_garanti_path"] > 0.99
    assert rep["error_budget"]["p_final"]["2+"] < 0.01
    return (
        f"p_ici={rep['summary']['p_kume_ici']:.4f} "
        f"p0={rep['summary']['p0']:.4f} p1={rep['summary']['p1']:.4f}"
    )


def _check_error_freq() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    ef = match_error_frequency(enc, cols, max_d=2)
    assert ef["n1"] >= 0 and ef["n2"] >= 0
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    assert acik == 0 and worst <= 1
    assert ef["n2"] == 0
    return f"n1={ef['n1']} n2={ef['n2']} d1_macs={len(ef['d1'])}"


def _check_fire_scenarios() -> str:
    """
    Secim DISI fire invariantlari.

    Bir mac isaret disindaysa hicbir kolon 15 tutturamaz; iki mac
    disindaysa 14 de imkansizdir. Bunlar kombinatoryal zorunluluktur,
    kupona bagli degildir - kirilirsa mesafe hesabi bozulmus demektir.
    """
    from .fire_scenarios import fire_maliyeti, fire_scenario_report
    enc = Encoder(parse_picks(ORNEK))
    cols, _ = solve_fix16(enc)
    r = fire_scenario_report(enc, cols, max_fires=2)
    assert r["fire1"]["scores"]["15"] == 0, "1 fire varken 15 mumkun gorunuyor"
    assert r["fire2"]["scores"]["15"] == 0
    assert r["fire2"]["scores"]["14"] == 0, "2 fire varken 14 mumkun gorunuyor"
    # Bankoda yanilmak ciftede yanilmaktan pahali olmali
    bt = r["fire1"]["by_type"]
    assert bt["double"]["pct"]["14"] > bt["banko"]["pct"]["14"]
    return (f"fire1>=14=%{r['fire1']['p_ge_14']} "
            f"fire2>=13=%{r['fire2']['p_ge_13']} "
            f"maliyet={fire_maliyeti(enc, cols)}")


def _check_stats_sozlesmesi() -> str:
    """
    `/api/stats` ve `/api/backtest` govdelerinin SEKLI.

    Veri katmani `veri_seti`, `oran_arsivi` ve `geri_test` ile
    dogrulaniyordu; ama arayuzun gercekten okudugu govde hicbir yerde
    sinanmiyordu. Bir alan adi degistiginde motor sapasaglam kalir, testler
    gecer, `/istatistik` sessizce bos doner.

    Denetlenen sey degerler degil, govdenin kendi icinde tutarliligi:
    hafta sayisi meta ile, analiz bloklari mac sayisi ile, sezon ozeti hafta
    hafta dokumle ortusmeli.
    """
    from .history import MATCH_COUNT
    from .payloads import backtest_payload, stats_payload

    s = stats_payload()
    for alan in ("meta", "totals", "weekly_avg", "bands", "data_quality",
                 "analytics", "odds", "weeks", "last", "error"):
        assert alan in s, f"/api/stats gövdesinde {alan} yok"

    haftalar = s["weeks"]
    if not haftalar:
        return "veri seti yok — istatistik gövdesi boş çalışır"

    assert s["meta"]["weeks"] == len(haftalar), "meta.weeks hafta listesiyle ayrışmış"
    assert s["meta"]["matches"] == len(haftalar) * MATCH_COUNT
    for w in haftalar:
        assert {"week", "results", "n1", "n0", "n2"} <= set(w), "hafta kaydı eksik"
    a = s["analytics"]
    assert len(a["positions"]) == MATCH_COUNT, "pozisyon bloğu 15 maç değil"
    assert a["transitions"]["n"] == len(haftalar) * (MATCH_COUNT - 1)
    assert s["data_quality"]["ok"] is True

    # Dilim: `?last=N` govdenin TAMAMINI daraltmali, yalnizca bir blogunu degil.
    n = min(5, len(haftalar))
    d = stats_payload(n)
    assert len(d["weeks"]) == n, "last dilimi hafta listesini daraltmadı"
    assert d["meta"]["weeks"] == n, "last dilimi meta'yı daraltmadı"
    assert d["analytics"]["transitions"]["n"] == n * (MATCH_COUNT - 1), \
        "last dilimi analiz bloğunu daraltmadı"
    assert d["last"] == n

    # Geri test: tarama KAPALI (sure butcesi); acik hali `pytest -m slow` isi.
    b = backtest_payload(sweep=False)
    # Arayuzun okudugu alanlarin TAMAMI (frontend/lib/types.ts:BacktestResponse).
    for alan in ("meta", "strategy", "season", "weeks", "sweep", "sweep_best",
                 "holdout", "grid", "warning"):
        assert alan in b, f"/api/backtest gövdesinde {alan} yok"
    assert b["grid"]["banko"] and b["grid"]["uclu"], "eşik ızgarası boş"
    assert b["strategy"]["banko"] in b["grid"]["banko"], "seçili eşik ızgarada yok"
    sezon, hafta_dokumu = b["season"], b["weeks"]
    kosan = [h for h in hafta_dokumu if not h["skipped"]]
    assert sezon["weeks"] == len(kosan), "sezon özeti hafta dökümüyle ayrışmış"
    assert sezon["hit14"] == sum(1 for h in kosan if h["best"] >= MATCH_COUNT - 1)
    assert sezon["hit15"] == sum(1 for h in kosan if h["best"] == MATCH_COUNT)

    return (f"stats: hafta={s['meta']['weeks']} dilim={n} | "
            f"backtest: hafta={sezon['weeks']} 14+={sezon['hit14']}")


def _check_pipeline_result_shape() -> str:
    enc = Encoder(parse_picks(ORNEK))
    cols, baslik = solve_fix16(enc)
    rows = merge_rows(cols)
    total_cost = sum(row_cost(r) for r in rows)
    worst, acik = dogrula_kaplama(cols, enc.alphabet_sizes)
    dist = distance_layers(cols, enc.alphabet_sizes)
    probs = _probs_on_selections(enc)
    rap = olasilik_raporu(enc, cols, probs)
    mc = monte_carlo_report(enc, cols, probs, n_samples=3_000, seed=1)
    ef = match_error_frequency(enc, cols)

    result = {
        "baslik": baslik,
        "satir_sayisi": len(rows),
        "kolon_bedeli": total_cost,
        "guaranteed": worst <= 1,
        "probs": {"15": dist.get(0, 0), "14": dist.get(1, 0)},
        "advanced": {
            "exact": {"p_kume_ici": rap.p_kume_ici, "p_15": rap.p_15},
            "monte_carlo": mc,
        },
        "error_freq": ef,
        "stat_lines": basliklar(enc),
        "match_count": enc.total_len,
    }
    assert result["guaranteed"] is True
    assert result["satir_sayisi"] == 16
    assert result["match_count"] == 15
    assert result["advanced"]["monte_carlo"]["n_samples"] == 3_000
    assert result["error_freq"]["n2"] == 0
    assert len(result["stat_lines"]) >= 4
    assert rap.p_kume_ici > 0.99
    return f"satir=16 bedel={total_cost} p_ici={rap.p_kume_ici:.4f}"


def _check_veri_seti() -> str:
    """
    /istatistik sayfasinin dayandigi tarihsel veri seti.

    Dosya YOKSA bu bir hata degildir: motor veri setinden bagimsiz calisir,
    yalnizca istatistik sayfasi bos kalir. Dosya VARSA kendi ic tutarliligini
    saglamak zorundadir — hafta sayimi, 15'lik dizi ve mac listesi ortusmeli.
    """
    from .history import (
        MATCH_COUNT,
        history_analytics,
        history_summary,
        history_weeks,
    )

    s = history_summary()
    meta = s.get("meta") or {}
    if not meta.get("weeks"):
        return "veri seti yok — istatistik sayfası boş çalışır"

    dq = s["data_quality"]
    assert not dq["count_conflicts"], f"sayim catismasi: {dq['count_conflicts']}"
    assert not dq["match_conflicts"], f"mac/dizi catismasi: {dq['match_conflicts']}"
    assert not dq["incomplete_weeks"], f"eksik hafta: {dq['incomplete_weeks']}"
    assert dq["ok"] is True

    weeks = history_weeks()
    assert len(weeks) == meta["weeks"]
    for w in weeks:
        assert len(w["results"]) == MATCH_COUNT, f"hafta {w['week']} dizisi eksik"
        assert w["n1"] + w["n0"] + w["n2"] == MATCH_COUNT

    a = history_analytics()
    assert len(a["positions"]) == MATCH_COUNT
    for p in a["positions"]:
        assert sum(p["counts"].values()) == p["n"] == meta["weeks"]
    # Gecis matrisi hafta ici ardisik ciftleri sayar: hafta basina 14 gecis.
    assert a["transitions"]["n"] == meta["weeks"] * (MATCH_COUNT - 1)
    return f"hafta={meta['weeks']} mac={meta['matches']} catisma=0"


def _check_oran_arsivi() -> str:
    """
    Piyasa orani arsivi. Yoksa istatistik sayfasi oran bloklarini gizler;
    varsa marj arindirilmis olasiliklar 1'e toplanmak zorundadir.
    """
    from .odds import coverage, season_1x2_summary

    cov = coverage()
    if not cov["matches"]:
        return "oran arşivi yok — oran blokları gizlenir"

    assert 0 <= cov["pct"] <= 100
    o = season_1x2_summary()
    if o is None:
        return f"eşleşme=%{cov['pct']} — 1X2 özeti üretilemedi"

    assert o["favourite_hit"] + o["favourite_miss"] == o["with_odds"]
    assert sum(o["favourite_split"].values()) == o["with_odds"]
    for s in SEMBOLLER:
        assert (
            o["outcome_when_hit"][s] + o["outcome_when_miss"][s]
            == o["outcome_totals"][s]
        ), f"capraz tablo {s} icin tutmuyor"
    assert sum(b["n"] for b in o["favourite_bands"]) == o["with_odds"]
    assert o["avg_margin_pct"] > 0, "marj pozitif olmali"

    # Karar destek bloklari: her biri ayni mac kumesini bolusturur, bir mac
    # ne kaybolur ne iki kez sayilir.
    for anahtar in ("set_coverage", "draw_profile", "leagues", "weekly_brier"):
        assert sum(b["n"] for b in o[anahtar]) == o["with_odds"], \
            f"{anahtar} maclari bolusturmuyor"
    # Piyasa esit olasilik vermekten iyi olmali; olmuyorsa oran ya da
    # eslestirme bozulmustur.
    assert 0.0 < o["brier_avg"] < o["brier_uniform"], "piyasa esit dagilimdan kotu"
    assert sum(b["draw"] for b in o["draw_profile"]) == o["outcome_totals"]["0"]
    assert sum(l["draw"] for l in o["leagues"]) == o["outcome_totals"]["0"]
    assert sum(l["favourite_hit"] for l in o["leagues"]) == o["favourite_hit"]
    # Banko, ciftenin alt kumesidir: tek isaret ikisinden fazla tutamaz.
    for b in o["set_coverage"]:
        assert b["in_one"] <= b["in_two"] <= b["n"]

    return (
        f"eslesme=%{o['coverage_pct']} favori_isabet=%{o['favourite_hit_pct']} "
        f"marj=%{o['avg_margin_pct']} lig={len(o['leagues'])}"
    )


def _check_geri_test() -> str:
    """
    Geri test hatti. Iki degismez var ve ikisi de raporun durustlugunu
    korur: (1) her hafta 14-GARANTILI bir kaplamayla cozulur — acik nokta
    birakan bir cozum bedel tablosuna giremez; (2) kume ici kalan bir hafta
    tanimi geregi en az 14 tutturur, yani `in_set <= hit14`.

    Tarama KAPALI calisir: burada olculen sey stratejinin isabeti degil,
    boru hattinin kendi tutarliligi.
    """
    from .backtest import backtest
    from .history import MATCH_COUNT

    r = backtest(sweep=False)
    s = r["season"]
    if not s.get("weeks"):
        return "çalıştırılabilir hafta yok — oran arşivi eksik olabilir"

    for h in r["weeks"]:
        if h["skipped"]:
            continue
        assert h["guaranteed"], f"{h['week']}. hafta kaplaması açık nokta bıraktı"
        assert h["banko"] + h["double"] + h["triple"] == MATCH_COUNT
        assert h["in_set"] == (h["misses"] == 0)
        assert h["misses"] == len(h["miss_at"])
        assert 0 <= h["best"] <= MATCH_COUNT
        assert h["columns"] >= h["rows"], "kolon bedeli satır sayısının altına düşemez"
    assert s["in_set"] <= s["hit14"], "küme içi hafta en az 14 tutturmalı"
    assert s["hit15"] <= s["hit14"] <= s["hit13"] <= s["weeks"]
    lo, hi = s["hit14_ci"]
    assert lo <= s["hit14_pct"] <= hi, "güven aralığı ölçümü içermeli"
    return (
        f"hafta={s['weeks']} 14+={s['hit14']} kume_ici={s['in_set']} "
        f"kolon/hafta={s['columns_avg']}"
    )


def _check_tahmin_referanslari() -> str:
    """
    Tahmin katmaninin olcum kosumu hala ayni sayiyi veriyor mu.

    Denetlenen sey MODELIN KALITESI DEGIL, olcumun TEKRARLANABILIRLIGIdir.
    Bir tahmincinin iyi olup olmadigi istatistik katmaninin isidir (geri
    test, hold-out); burada sorulan soru daha temel: "referanslar hala
    bildigimiz degerleri veriyor mu, yoksa altlarindaki veri mi kaydi?"

    Uc sey sabittir ve veri ne kadar buyurse buyusun degismez:

      1. `duzgun` Brier'i tam olarak 0,667, log kaybi tam olarak ln(3).
         Bunlar matematiksel ozdesliktir; kayarsa bozulan olcut kodudur.
      2. Siralama piyasa < sezon_sabiti < duzgun. Piyasa bilgi tasiyor,
         sezon dagilimi ondan az, esit dagitim hic. Bu siralama bozulursa
         bozulan model degil ORAN ARSIVIdir.
      3. Hicbir referans piyasayi gecmez — cizgi kendisi referans oldugu
         icin gecmesi mantiken imkansiz.

    Piyasanin kendi degeri BILEREK dar bir esige baglanmadi: kupon seti
    ikinci sezonla buyursa deger mesru olarak kayar ve saglik bundan
    kirmizi olmamalidir. Bunun yerine genis bir akil saglami var (esit
    dagitimdan iyi, kusursuzdan uzak) ve tam deger mesajda raporlanir.
    """
    import math

    from .evaluate import karsilastir, olculebilir_haftalar
    from .odds import BRIER_ESIT

    kesit = olculebilir_haftalar()
    if not kesit:
        return "olculebilir hafta yok — oran arsivi eksik olabilir"

    r = karsilastir(haftalar=kesit)
    skor = {s["ad"]: s for s in r["tahminciler"]}
    for ad in ("duzgun", "sezon_sabiti", "piyasa"):
        assert ad in skor, f"referans tahminci kayip: {ad}"

    # 1) matematiksel ozdeslikler
    assert abs(skor["duzgun"]["brier"] - BRIER_ESIT) < 1e-3, (
        f"duzgun Brier {skor['duzgun']['brier']} — 0,667 olmaliydi")
    assert abs(skor["duzgun"]["log_kaybi"] - math.log(3)) < 1e-3, (
        f"duzgun log kaybi {skor['duzgun']['log_kaybi']} — ln(3) olmaliydi")

    # 2) siralama — bozulursa oran arsivi bozulmustur
    assert skor["piyasa"]["brier"] < skor["sezon_sabiti"]["brier"] < skor["duzgun"]["brier"], (
        "referans siralamasi bozuk: piyasa < sezon_sabiti < duzgun beklenir")

    # 3) genis akil saglami — dar esik BILEREK yok (bkz. docstring)
    p = skor["piyasa"]["brier"]
    assert 0.30 < p < BRIER_ESIT, f"piyasa Brier'i akil disi: {p}"

    # 4) cizgi kendisini gecemez
    for s in r["tahminciler"]:
        if s["ad"] != r["referans"]:
            assert s["gecti"] is False, f"{s['ad']} referansi gecti — beklenmez"

    return (
        f"hafta={r['n_hafta']} mac={r['n_mac']} | piyasa={p:.4f} "
        f"sezon={skor['sezon_sabiti']['brier']:.4f} duzgun={skor['duzgun']['brier']:.4f}"
    )


def _check_scipy_flag() -> str:
    return f"HAS_SCIPY={HAS_SCIPY}"


def ornek_kimligi() -> Dict[str, Any]:
    """Raporu HANGI surecin urettigi.

    Rapor, cagriyi karsilayan sureci anlatir. Cok ornekli bir dagitimda
    (autoscale, gunicorn'un birden fazla worker'i) "hangi ornek?" sorusu
    cevapsizdi: iki ardisik cagri farkli sureclere dusup farkli cevap
    verebilir ve fark okuyana rastgele gorunur.

    `INSTANCE_ID` (ya da Replit'in verdigi `REPL_ID`) tanimliysa etiket
    olarak gecer; yoksa pid + host yeterince ayirt eder.
    """
    return {
        "pid": os.getpid(),
        "host": platform.node() or None,
        "etiket": (os.environ.get("INSTANCE_ID")
                   or os.environ.get("REPL_ID") or None),
        "baslangic": _SUREC_BASLANGIC_ISO,
        "uptime_s": round(time.monotonic() - _SUREC_BASLANGIC, 1),
    }


def _env_info() -> Dict[str, Any]:
    """Calisan surumun bagimlilik envanteri — 'bende calisiyordu' icin."""
    from importlib.metadata import version as _paket_surum

    def _surum(paket: str) -> Optional[str]:
        # Surum bilgisi raporun kritik parcasi degil: bulunamazsa None gecer.
        try:
            return _paket_surum(paket)
        except Exception:
            return None

    return {
        "python": platform.python_version(),
        "platform": platform.platform(terse=True),
        "numpy": _surum("numpy"),
        "scipy": _surum("scipy"),
        "flask": _surum("flask"),
    }


CHECKS: Tuple[CheckSpec, ...] = (
    CheckSpec(
        "encoder", "cekirdek",
        "Kupon metnini arama uzayına çevirir: çift/üçlü sayısı, uzay büyüklüğü "
        "ve teorik alt sınır. Kırılırsa bütün hesap yanlış uzayda yapılır.",
        _check_encoder,
        butce_ms=25,
    ),
    CheckSpec(
        "fix16_garanti", "cekirdek",
        "16 satırlık sabit kaplama gerçekten 14-garanti veriyor mu: en kötü "
        "durumda hata ≤ 1 ve açıkta nokta yok. Ürünün ana vaadi budur.",
        _check_fix16_garanti,
        butce_ms=40,
    ),
    CheckSpec(
        "fix16_yetersiz_cifte", "cekirdek",
        "Yetersiz çift sayısıyla fix16 istendiğinde sessizce garantisiz sonuç "
        "dönmez, Fix16Hatası yükselir.",
        _check_fix16_yetersiz_cifte,
        butce_ms=25,
    ),
    CheckSpec(
        "distance_layers", "cekirdek",
        "Mesafe muhasebesi: 0 ve 1 hatalı noktaların toplamı arama uzayının "
        "tamamını vermeli. Tutmazsa kapsama raporu güvenilmezdir.",
        _check_distance_layers,
        butce_ms=30,
    ),
    CheckSpec(
        "fix16_varyantlari", "cekirdek",
        "Alternatif 16'lık kümeler (`variant`) de 16 satır ve 14-garanti "
        "veriyor mu. Kırılırsa varyant seçen kullanıcı sessizce garantisiz "
        "kupon alır.",
        _check_fix16_varyantlari,
        butce_ms=30,
    ),
    CheckSpec(
        "blok_motor", "motor",
        "Blok motoru da tam kaplama üretir ve fix16'dan pahalı olmaz.",
        _check_blok_motor,
        butce_ms=40,
    ),
    CheckSpec(
        "heuristic", "motor",
        "Sezgisel motor, fix16'nın reddettiği kuponda bile geçerli kaplama "
        "bulur — garanti motora değil, kaplamanın kendisine bağlıdır.",
        _check_heuristic,
        butce_ms=300,
    ),
    CheckSpec(
        "mod_envanteri", "motor",
        "Meta'da ilan edilen 7 modun hepsi koşuyor ve `garanti` bayrağı "
        "gerçeği söylüyor mu. Bozuk bir mod arayüzde seçilebilir kalır ve "
        "doğrudan kullanıcıya çarpar.",
        _check_mod_envanteri,
        butce_ms=400,
    ),
    CheckSpec(
        "olasilik_exact", "olasilik",
        "Kesin olasılık: p15 + p14 = küme içi olasılığı. Ayrışırsa olasılık "
        "raporu kendi içinde çelişiyor demektir.",
        _check_olasilik_exact,
        butce_ms=25,
    ),
    CheckSpec(
        "monte_carlo", "olasilik",
        "Simülasyon kesin hesapla aynı yeri gösteriyor mu (fark < 0,05) ve "
        "güven aralıkları makul mu.",
        _check_monte_carlo,
        butce_ms=400,
    ),
    CheckSpec(
        "bayes_dirichlet", "olasilik",
        "Dirichlet posterior'ları 15 maç için 1'e toplanır ve garantiyi "
        "bozmaz — Bayes tahmini yumuşatır, kaplamayı değiştirmez.",
        _check_bayes,
        butce_ms=25,
    ),
    CheckSpec(
        "bayes_presetleri", "olasilik",
        "Meta'nın ilan ettiği Bayes preset'lerinin hepsi çalışıyor, "
        "posterior'ları 1'e toplanıyor ve hiçbiri kaplamayı bozmuyor.",
        _check_bayes_presetleri,
        butce_ms=30,
    ),
    CheckSpec(
        "markov_chain", "olasilik",
        "Sıralı hata bütçesi: garanti yolunda kalma olasılığı ve 2+ hataya "
        "düşme olasılığı kombinatoryal sınırlarla tutarlı mı.",
        _check_markov,
        butce_ms=40,
    ),
    CheckSpec(
        "error_freq", "analiz",
        "Hangi maçlarda 1 hata oluşabildiği. Tam kaplamada 2 hatalı nokta "
        "sayısı sıfır olmak zorundadır.",
        _check_error_freq,
        butce_ms=25,
    ),
    CheckSpec(
        "fire_scenarios", "analiz",
        "Seçim DIŞI bölge: 1 fire varken 15, 2 fire varken 14 imkânsızdır; "
        "bankoda yanılmak çiftede yanılmaktan pahalıya patlar.",
        _check_fire_scenarios,
        butce_ms=120,
    ),
    CheckSpec(
        "veri_seti", "analiz",
        "İstatistik sayfasının dayandığı veri setinin iç tutarlılığı: hafta "
        "sayımı, 15'lik sonuç dizisi ve maç listesi birbirini doğruluyor mu.",
        _check_veri_seti,
        butce_ms=60,
    ),
    CheckSpec(
        "oran_arsivi", "analiz",
        "Piyasa oranı arşivi: kapsama, favori isabet muhasebesi ve çapraz "
        "tablonun toplamları tutuyor mu.",
        _check_oran_arsivi,
        butce_ms=250,
    ),
    CheckSpec(
        "geri_test", "analiz",
        "Geri test boru hattı: her hafta 14-garantili bir kaplamayla çözülüyor "
        "mu ve küme içi kalan hafta gerçekten en az 14 tutturuyor mu.",
        _check_geri_test,
        butce_ms=200,
    ),
    CheckSpec(
        "tahmin_referanslari", "analiz",
        "Tahmin katmanının ölçüm koşumu hâlâ aynı sayıyı veriyor mu: `duzgun` "
        "tam olarak 0,667, sıralama piyasa < sezon_sabiti < duzgun. Denetlenen "
        "şey modelin kalitesi değil ölçümün tekrarlanabilirliği — sıralama "
        "bozulursa bozulan model değil oran arşividir.",
        _check_tahmin_referanslari,
        butce_ms=350,
    ),
    CheckSpec(
        "meta_sozlesmesi", "ucuca",
        "`/api/meta` kendi içinde tutarlı mı: her sınırda min ≤ varsayılan ≤ "
        "max, preset ve mod listeleri motorla aynı. Meta bozulursa formül "
        "sayfası çöker ama motor sapasağlam kalır.",
        _check_meta_sozlesmesi,
        butce_ms=25,
    ),
    CheckSpec(
        "stats_sozlesmesi", "ucuca",
        "`/api/stats` ve `/api/backtest` gövdeleri kendi içinde tutarlı mı ve "
        "`?last=` dilimi gövdenin tamamını daraltıyor mu. Bir alan adı "
        "değiştiğinde motor sağlam kalır, /istatistik sessizce boşalır.",
        _check_stats_sozlesmesi,
        butce_ms=120,
    ),
    CheckSpec(
        "pipeline_result_shape", "ucuca",
        "API'nin döndürdüğü sonuç sözleşmesi: satır sayısı, bedel, garanti "
        "bayrağı ve analiz blokları eksiksiz mi.",
        _check_pipeline_result_shape,
        butce_ms=250,
    ),
    CheckSpec(
        "scipy_flag", "ortam",
        "scipy var mı — yoksa kesin çözücü (ILP) devre dışıdır. Bilgi "
        "amaçlıdır, raporu UNHEALTHY yapmaz.",
        _check_scipy_flag,
        butce_ms=25,
        critical=False,
    ),
)

CHECK_ADLARI: Tuple[str, ...] = tuple(c.name for c in CHECKS)


def secili_checkler(only: Optional[str] = None) -> List[CheckSpec]:
    """`only` ile kontrol/kategori suzer. Bos veya None ise hepsini dondurur.

    Virgulle birden fazla ad verilebilir ("olasilik,error_freq"). Taninmayan
    bir ad sessizce bos kume uretmez — ValueError yukselir.
    """
    if not only or not only.strip():
        return list(CHECKS)

    istenen = [p.strip().lower() for p in only.split(",") if p.strip()]
    secili: List[CheckSpec] = []
    for parca in istenen:
        uyan = [
            c for c in CHECKS
            if c.name == parca or c.category == parca
        ]
        if not uyan:
            gecerli = ", ".join(sorted({*CHECK_ADLARI, *KATEGORI_ETIKET}))
            raise ValueError(f"Bilinmeyen kontrol/kategori: {parca}. Geçerli: {gecerli}")
        for c in uyan:
            if c not in secili:
                secili.append(c)
    # Tanim sirasini koru — rapor her zaman ayni duzende okunur.
    return [c for c in CHECKS if c in secili]


# Bu surecte en az bir rapor kosuldu mu. Ilki ISINMA sayilir: numpy/scipy
# import'u, veri seti ve oran arsivinin ilk okunmasi onun sirtindadir.
_isindi = False


def run_health(only: Optional[str] = None) -> HealthReport:
    global _isindi
    isinma = not _isindi
    _isindi = True

    secili = secili_checkler(only)
    results = [_run(spec, isinma=isinma) for spec in secili]
    kritik_dusen = [c for c in results if not c.ok and c.critical]
    bilgi_dusen = [c for c in results if not c.ok and not c.critical]
    yavaslar = [c for c in results if c.yavas]
    return HealthReport(
        version=__version__,
        timestamp=datetime.now(timezone.utc).isoformat(),
        ok=not kritik_dusen,
        # Sure butcesini asmak da bir gerilemedir ama DUSUS degildir:
        # degismez hala gecerli, yalnizca beklenenden pahali. Bu yuzden
        # `ok` kalir, `degraded` isaretlenir (§6'daki ayrimla ayni mantik).
        degraded=bool(bilgi_dusen or yavaslar) and not kritik_dusen,
        checks=results,
        summary={
            "ornek_kupon": ORNEK,
            "kupon_siniflari": [
                {"etiket": s.etiket, "picks": s.picks, "uzay": s.uzay,
                 "alt_sinir": s.alt_sinir}
                for s in KUPON_SINIFLARI
            ],
            "has_scipy": HAS_SCIPY,
            "env": _env_info(),
            "ornek": ornek_kimligi(),
            "isinma": isinma,
            "only": only or None,
            "kismi": len(secili) < len(CHECKS),
            "kayitli_kontrol": len(CHECKS),
        },
    )


def kupon_denetle(
    picks: str,
    mode: str = "fix16",
    variant: int = 0,
    budget: Optional[int] = None,
) -> Dict[str, Any]:
    """KULLANICININ kendi kuponunu ayni degismezlerden gecirir.

    Saglik raporunun en kolay yanlis anlasilan sinirini kapatir (§3.2): sabit
    ornek kuponla kosan bir HEALTHY, kullanicinin az once urettigi kuponun
    dogrulandigi anlamina GELMEZ. Bu fonksiyon o kuponu alir ve ayni
    kombinatoryal zorunluluklari onun uzerinde sinar.

    Donen sozluk, rapor govdesiyle ayni sekildedir (`ok`, `checks[]`), ama
    KAYITLI kontrol listesinden ayridir: burada olculen sey motorun genel
    sagligi degil, TEK bir kuponun sonucudur. Ikisi ayni tabloda gorunmemeli.
    """
    from .engines import (
        engine_params, run_auto, run_block, run_butce, run_exact, run_fix16,
        run_heuristic, run_maxcov,
    )
    from .meta import MODES

    mod = next((m for m in MODES if m["id"] == mode), None)
    if mod is None:
        raise ValueError(
            f"Bilinmeyen mod {mode!r}. Geçerli olanlar: "
            f"{', '.join(m['id'] for m in MODES)}")
    if mod["needs_budget"] and not budget:
        raise ValueError(f"{mode} modu için budget gerekli")
    if mod["needs_scipy"] and not HAS_SCIPY:
        raise ValueError(f"{mode} modu scipy gerektirir; bu kurulumda scipy yok")

    t0 = time.perf_counter()
    enc = Encoder(parse_picks(picks))
    eng = engine_params()
    kosucular = {
        "fix16": lambda: run_fix16(enc, variant=variant),
        "auto": lambda: run_auto(enc, eng),
        "exact": lambda: run_exact(enc, eng),
        "block": lambda: run_block(enc, eng),
        "heuristic": lambda: run_heuristic(enc, eng),
        "butce": lambda: run_butce(enc, int(budget or 0), variant=variant),
        "maxcov": lambda: run_maxcov(enc, int(budget or 0)),
    }
    r = kosucular[mode]()
    # Butce modu kuponu DARALTIR; sonraki her hesap daraltilmis kupon
    # uzerinde yapilmali, yoksa olculen sey kullanicinin aldigi sey olmaz.
    kupon_enc = r.get("enc", enc)
    cols = r["cols"]

    rows = merge_rows(cols)
    worst, acik = dogrula_kaplama(cols, kupon_enc.alphabet_sizes)
    dist = distance_layers(cols, kupon_enc.alphabet_sizes)
    probs = _probs_on_selections(kupon_enc)
    rap = olasilik_raporu(kupon_enc, cols, probs)
    garanti_bekleniyor = bool(mod["garanti"])

    def _kontrol(ad: str, gecti: bool, aciklama: str, detail: str) -> Dict[str, Any]:
        return {"name": ad, "ok": bool(gecti), "aciklama": aciklama,
                "detail": detail}

    checks = [
        _kontrol(
            "kaplama_garantisi",
            (worst <= 1 and acik == 0) if garanti_bekleniyor else acik > 0,
            "Bu kuponun kaplaması, modun ilan ettiği garanti sözünü tutuyor mu.",
            f"mod={mode} garanti={garanti_bekleniyor} worst={worst} açık={acik}",
        ),
        _kontrol(
            "mesafe_muhasebesi",
            sum(dist.values()) == kupon_enc.space_size(),
            "0/1/2… hatalı nokta sayılarının toplamı arama uzayının tamamını "
            "vermeli; tutmazsa bu kuponun yüzdeleri yanlıştır.",
            f"katman={dict(sorted(dist.items()))} uzay={kupon_enc.space_size()}",
        ),
        _kontrol(
            "satir_kolon_muhasebesi",
            (set(rows_to_points(rows)) == set(cols)
             and sum(row_cost(r_) for r_ in rows) == len(cols)),
            "Kupona yazılacak satırlar ile ödenecek kolon bedeli birbirini "
            "tutmalı: satır çözülüp tekrar kolona döndüğünde aynı küme çıkmalı.",
            f"satır={len(rows)} bedel={len(cols)}",
        ),
        _kontrol(
            "alt_sinir",
            len(cols) >= kupon_enc.lower_bound() or not garanti_bekleniyor,
            "Bedel, sayma argümanının verdiği teorik alt sınırın altına "
            "düşemez; düşüyorsa hesap yanlıştır.",
            f"bedel={len(cols)} alt_sınır={kupon_enc.lower_bound()}",
        ),
        _kontrol(
            "olasilik_tutarliligi",
            _approx(rap.p_15 + rap.p_14, rap.p_kume_ici),
            "p15 + p14 = küme içi olasılığı. Ayrışırsa bu kuponun olasılık "
            "raporu kendi içinde çelişiyor demektir.",
            f"p_içi={rap.p_kume_ici:.4f} p15={rap.p_15:.4f} p14={rap.p_14:.4f}",
        ),
    ]

    dusen = [c for c in checks if not c["ok"]]
    return {
        "ok": not dusen,
        "mode": mode,
        "picks": picks,
        "baslik": r.get("baslik", ""),
        "notlar": list(r.get("notlar", [])),
        "satir": len(rows),
        "bedel": len(cols),
        "alt_sinir": kupon_enc.lower_bound(),
        "uzay": kupon_enc.space_size(),
        "guaranteed": worst <= 1 and acik == 0,
        "worst": worst,
        "acik": acik,
        "checks": checks,
        "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "ornek": ornek_kimligi(),
        "uyari": (
            "Bu blok TEK bir kuponu doğrular; kayıtlı değişmez raporunun "
            "yerine geçmez. İkisi farklı katmandır."
        ),
    }


def check_envanteri() -> List[dict]:
    """Kontrolleri CALISTIRMADAN listeler — arayuzun filtre menusu icin."""
    return [
        {
            "name": c.name,
            "category": c.category,
            "category_label": KATEGORI_ETIKET.get(c.category, c.category),
            "aciklama": c.aciklama,
            "critical": c.critical,
            "butce_ms": c.butce_ms,
        }
        for c in CHECKS
    ]


def print_report(report: HealthReport) -> None:
    status = "HEALTHY" if report.ok else "UNHEALTHY"
    if report.ok and report.degraded:
        status = "DEGRADED"
    print(f"\n=== SYSTEM HEALTH [{status}] v{report.version} ===")
    print(f"time: {report.timestamp}")
    passed = sum(1 for c in report.checks if c.ok)
    toplam_ms = sum(c.duration_ms for c in report.checks)
    kismi = " (kısmi çalıştırma)" if report.summary.get("kismi") else ""
    print(f"checks: {passed}/{len(report.checks)} passed  "
          f"{toplam_ms:.0f} ms{kismi}")

    for kat in report.kategoriler():
        print(f"\n  {kat['label']}  [{kat['passed']}/{kat['total']}]")
        for c in report.checks:
            if c.category != kat["id"]:
                continue
            mark = "OK " if c.ok else ("FAIL" if c.critical else "warn")
            if c.ok and c.yavas:
                mark = "slow"
            print(f"    [{mark}] {c.name:22s} {c.duration_ms:7.1f} ms  {c.detail}")

    dusen = [c for c in report.checks if not c.ok]
    if dusen:
        print("\n  DÜŞEN KONTROLLER")
        for c in dusen:
            print(f"    · {c.name}: {c.aciklama}")
    print()


def print_envanter() -> None:
    for kat_id, etiket, aciklama in KATEGORILER:
        uyan = [c for c in CHECKS if c.category == kat_id]
        if not uyan:
            continue
        print(f"\n{etiket} ({kat_id}) — {aciklama}")
        for c in uyan:
            isaret = "" if c.critical else "  [bilgi]"
            print(f"  {c.name}{isaret}\n    {c.aciklama}")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Spor Toto system health checks")
    p.add_argument("--interval", type=float, default=0,
                   help="Saniye cinsinden tekrar aralığı (0 = bir kez)")
    p.add_argument("--json", action="store_true", help="JSON çıktı")
    p.add_argument("--only", default=None,
                   help="Yalnızca bu kontrol/kategori (virgülle çoklu)")
    p.add_argument("--list", action="store_true", dest="listele",
                   help="Kontrol envanterini yaz ve çık")
    args = p.parse_args(argv)

    if args.listele:
        print_envanter()
        return 0

    while True:
        try:
            report = run_health(args.only)
        except ValueError as e:
            print(f"hata: {e}", file=sys.stderr)
            return 2
        if args.json:
            import json
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            print_report(report)
        if args.interval <= 0:
            return 0 if report.ok else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
