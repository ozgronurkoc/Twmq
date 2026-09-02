#!/usr/bin/env python3
"""Arayüz ile backend arasındaki sözleşmeyi üretir ve denetler.

    python scripts/api_sozlesme.py            # yazar
    python scripts/api_sozlesme.py --kontrol  # yalnizca denetler (CI)

**Sorun.** `spor_toto/payloads.py` yalnızca `/api/stats` ve `/api/backtest`
gövdelerini tek kaynağa bağlıyor ve `health._check_stats_sozlesmesi` onları
denetliyordu. Kalan on bir uç korumasızdı. Arayüz tarafında ise 1000 satırlık
`lib/types.ts` **elle** bakılıyordu ve `frontend/scripts/check.mjs` backend'den
**elle ölçülmüş** sabitler taşıyordu (`p_kume_ici = 0.00014902`, `altSinir =
29`). Bir alan adı değiştiğinde motor sapasağlam kalır, bütün testler geçer ve
sayfa sessizce boş döner; backend matematiği değiştiğinde ise arayüzün
"doğrulanmış" sayıları sessizce yanlışlanır.

**Çözüm.** Bu script sözleşmeyi `frontend/lib/api-sozlesme.json` dosyasına
üretir; `--kontrol` üretilecek içerikle dosyadakini karşılaştırır ve
farklıysa sıfırdan farklı kodla çıkar. Desen yeni değil:
`super_toto_frontend.py` aynısını hafta beslemesi için yapıyor.

**Neden Flask test istemcisi, neden `payloads` fonksiyonları değil.**
Sözleşme, arayüzün gerçekten okuduğu şeydir — yani **HTTP cevabı**. Gövdeyi
yeniden kurmak, route'un `jsonify` öncesi eklediği alanları (`version`,
`onbellek`, `odds_hit`…) kaçırırdı. Test istemcisi ağ açmadan gerçek route'u
koşturur.

**Ne kaydedilir:** yalnızca **şekil** — anahtar adları ve tipleri. Değerler
girmez: `timestamp`, `duration_ms` ve sürüm numaraları her koşumda değişir ve
dosyayı her seferinde kirletirdi. Tek istisna `olculmus` bloğudur; oradaki
sayılar `check.mjs`'in elle taşıdığı sabitlerin yerine geçer.
"""
from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from scripts._ortak import metin

CIKTI = KOK.parent / "frontend" / "lib" / "api-sozlesme.json"


# ─── şekil çıkarımı ──────────────────────────────────────────────────────

def _sekil(deger: Any, yol: str = "") -> Any:
    """Bir JSON değerini tip ağacına çevirir.

    Liste elemanları **homojen** varsayılır ve bu doğrulanır: karışık bir
    liste sözleşmede tek bir elemanla temsil edilirse arayüz tarafı yanlış
    bir kesinlik kazanırdı.
    """
    if deger is None:
        return "null"
    if isinstance(deger, bool):
        return "bool"
    if isinstance(deger, int):
        return "int"
    if isinstance(deger, float):
        return "float"
    if isinstance(deger, str):
        return "str"
    if isinstance(deger, dict):
        return {k: _sekil(deger[k], f"{yol}.{k}") for k in sorted(deger)}
    if isinstance(deger, list):
        if not deger:
            # Bos liste eleman sekli TASIMAZ. Bunu "her sey olabilir" diye
            # gecistirmek yerine acikca isaretliyoruz ki denetim tarafi da
            # o alan icin bir sey iddia etmesin.
            return ["<bos>"]
        sekiller = [_sekil(e, f"{yol}[]") for e in deger]
        ilk = sekiller[0]
        for s in sekiller[1:]:
            if s != ilk:
                # Anahtar kumesi ayrisiyorsa BIRLESIMI bildir; sessizce
                # ilkini secmek yanlis bir kesinlik olurdu.
                if isinstance(s, dict) and isinstance(ilk, dict):
                    birlesik = dict(ilk)
                    for k, v in s.items():
                        birlesik.setdefault(k, v)
                    ilk = birlesik
                else:
                    return ["<karisik>"]
        return [ilk]
    raise TypeError(f"{yol}: JSON'da beklenmeyen tip {type(deger).__name__}")


# ─── uçlar ───────────────────────────────────────────────────────────────

#: `/api/tahmin` gövdesinin eleman şekli ancak listede maç VARKEN görünür.
#: Depodaki fikstür bugün boş (maçlar oynandı), o yüzden şekli yakalamak
#: için geçici ve **uzak gelecekte** bir fikstür yazılır. Deney değil:
#: amaç `TahminSatiri`nin alanlarını sözleşmeye sokmak.
_ORNEK_FIKSTUR = [
    ["E0", "", "20:00", "Örnek Ev", "Örnek Dep", "1.82", "3.40", "4.20",
     "sozlesme", "1"],
]


def _gecici_fikstur(dizin: Path) -> Path:
    yol = dizin / "fixtures.csv"
    tarih = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d")
    with yol.open("w", newline="", encoding="utf-8") as f:
        y = csv.writer(f)
        y.writerow(["lig", "tarih", "saat", "ev", "dep", "oran_1", "oran_0",
                    "oran_2", "oran_kaynak", "olculen_lig"])
        for satir in _ORNEK_FIKSTUR:
            y.writerow([satir[0], tarih, *satir[2:]])
    return yol


#: `/api/solve` icin ornek govde — kupon `core.ORNEK_KUPON`, olasiliklar
#: `check.sh`in ornegi. Ikisi de depoda zaten var, yani uydurma degil.
_SOLVE_PROBS = [
    {"1": 0.5, "0": 0.3, "2": 0.2}, {"1": 0.4, "0": 0.4, "2": 0.2},
    {"1": 0.6, "0": 0.2, "2": 0.2}, {"1": 0.5, "0": 0.25, "2": 0.25},
    {"1": 0.3, "0": 0.4, "2": 0.3}, {"1": 0.45, "0": 0.35, "2": 0.2},
    {"1": 0.5, "0": 0.3, "2": 0.2}, {"1": 0.4, "0": 0.3, "2": 0.3},
    {"1": 0.55, "0": 0.25, "2": 0.2}, {"1": 0.5, "0": 0.3, "2": 0.2},
    {"1": 0.4, "0": 0.3, "2": 0.3}, {"1": 0.5, "0": 0.3, "2": 0.2},
    {"1": 0.45, "0": 0.35, "2": 0.2}, {"1": 0.5, "0": 0.25, "2": 0.25},
    {"1": 0.4, "0": 0.4, "2": 0.2},
]


def _uclar(istemci, ornek_kupon: str) -> dict[str, Any]:
    """Her ucu gercekten cagirip sekli cikarir."""
    from spor_toto.tahmin import genis_kesit_isabeti, olculmus_isabet

    cagrilar: list[dict[str, Any]] = [
        {"ad": "GET /", "yol": "/"},
        {"ad": "GET /health", "yol": "/health"},
        {"ad": "GET /api/meta", "yol": "/api/meta"},
        {"ad": "GET /api/health", "yol": "/api/health"},
        {"ad": "GET /api/health/checks", "yol": "/api/health/checks"},
        {"ad": "GET /api/health/history", "yol": "/api/health/history?limit=5"},
        {"ad": "POST /api/health/kupon", "yol": "/api/health/kupon",
         "govde": {"picks": ornek_kupon, "mode": "fix16"}},
        {"ad": "GET /api/stats", "yol": "/api/stats"},
        {"ad": "GET /api/stats/<week>", "yol": "/api/stats/<cozulecek>"},
        # Tarama KAPALI: acik hali dakikalar surer ve sekli degistirmez.
        {"ad": "GET /api/backtest", "yol": "/api/backtest?sweep=0"},
        {"ad": "GET /api/pazar", "yol": "/api/pazar"},
        {"ad": "GET /api/takimlar", "yol": "/api/takimlar"},
        {"ad": "GET /api/tahmin", "yol": "/api/tahmin"},
        {"ad": "GET /api/benzer", "yol": "/api/benzer?oran=1.82,3.04,2.44"},
        {"ad": "POST /api/solve", "yol": "/api/solve",
         "govde": {"picks": ornek_kupon, "mode": "fix16",
                   "probs": _SOLVE_PROBS, "fire_max": 1}},
    ]

    # Hafta numarasi VERIDEN cozulur. `/api/stats/1` yazmak cazipti ama
    # sezon 2. haftadan basliyor ve sabit bir numara veri degistiginde
    # sessizce 404'e duserdi.
    ilk_hafta = (istemci.get("/api/stats").get_json()["weeks"] or [{}])[0].get("week")
    if ilk_hafta is None:
        raise SystemExit("hafta verisi yok — sozlesme uretilemez")
    for c in cagrilar:
        if c["ad"] == "GET /api/stats/<week>":
            c["yol"] = f"/api/stats/{ilk_hafta}"

    out: dict[str, Any] = {}
    for c in cagrilar:
        if "govde" in c:
            cevap = istemci.post(c["yol"], json=c["govde"])
        else:
            cevap = istemci.get(c["yol"])
        # /api/health SAGLIKSIZ durumda 503 doner ve bu bir hata degil,
        # raporun kendisidir (bkz. lib/api.getHealth).
        if cevap.status_code not in (200, 503):
            raise SystemExit(
                f"{c['ad']} beklenmedik durum kodu {cevap.status_code}: "
                f"{cevap.get_data(as_text=True)[:300]}")
        out[c["ad"]] = _sekil(cevap.get_json(), c["ad"])
    # `olculmus_isabet` lru_cache'li; gecici fikstur silinmeden once temizle.
    # `genis_kesit_isabeti` de ayni desende ve AYRI bir onbellek: bugun bu
    # betik `?genis=1` cagirmiyor, ama cagirdigi gun temizlenmezse gecici
    # fikstur verisi surecin geri kalanina yapisirdi. Bir satirlik bedel.
    olculmus_isabet.cache_clear()
    genis_kesit_isabeti.cache_clear()
    return out


# ─── ölçülmüş referans değerler ──────────────────────────────────────────

def _olculmus(ornek_kupon: str) -> dict[str, Any]:
    """`check.mjs`in elle tasidigi sayilarin KAYNAGI.

    O dosyada `p_kume_ici = 0.00014902`, `altSinir = 29` gibi degerler duz
    yaziliydi ve yanlarinda "(olculdu)" notu vardi. Backend matematigi
    degistiginde bu sayilar sessizce yanlislanirdi: test yesil kalir ama
    artik yanlis bir seyi dogrulardi. Artik ayni kaynaktan uretiliyorlar.
    """
    from spor_toto.core import Encoder, olasilik_raporu, parse_picks, solve_fix16

    sec = parse_picks(ornek_kupon)
    enc = Encoder(sec)
    cols, _ = solve_fix16(enc)
    rap = olasilik_raporu(enc, cols, _SOLVE_PROBS)

    # Kume-ici olasiliga en cok zarar veren uc mac (1 tabanli sira).
    kutleler = [
        (i + 1, sum(_SOLVE_PROBS[i][s] for s in sec[i]))
        for i in range(len(sec))
    ]
    en_zayif = sorted(sorted(kutleler, key=lambda kv: kv[1])[:3])

    return {
        "ornek_kupon": ornek_kupon,
        "p_kume_ici": round(rap.p_kume_ici, 10),
        "alt_sinir": enc.lower_bound(),
        "uzay": enc.space_size(),
        "top_boyutu": enc.ball_size(),
        "en_zayif_uc_mac": [i for i, _ in en_zayif],
        "fix16_kolon": len(cols),
    }


# ─── sinirlar ────────────────────────────────────────────────────────────

def _sinirlar(istemci) -> dict[str, Any]:
    """`/api/meta`nin ilan ettigi sayisal sinirlar.

    Arayuz bunlarin bir kismini SABIT kodluyordu (`lib/kurulum.ts`,
    `app/page.tsx`) ve iki taraf ayrismisti: kurulum kodlamasi mc_samples'i
    1.000.000'a kirpiyordu, sunucu 200.000'e. Sozlesmeye girince ayrisma
    denetlenebilir hale gelir.
    """
    return istemci.get("/api/meta").get_json()["limits"]


def uret() -> dict[str, Any]:
    import spor_toto.tahmin as tahmin_mod
    from spor_toto import __version__
    from spor_toto.core import ORNEK_KUPON
    from web_app import app

    app.config.update(TESTING=True)
    istemci = app.test_client()

    with tempfile.TemporaryDirectory() as gecici:
        eski_fikstur = tahmin_mod.VARSAYILAN_FIXTURES
        tahmin_mod.VARSAYILAN_FIXTURES = _gecici_fikstur(Path(gecici))
        tahmin_mod.olculmus_isabet.cache_clear()
        try:
            uclar = _uclar(istemci, ORNEK_KUPON)
        finally:
            tahmin_mod.VARSAYILAN_FIXTURES = eski_fikstur
            tahmin_mod.olculmus_isabet.cache_clear()

    return {
        "_aciklama": (
            "URETILMIS DOSYA — elle duzenlemeyin. "
            "Kaynak: backend/scripts/api_sozlesme.py. "
            "Yenilemek icin: python scripts/api_sozlesme.py"
        ),
        "surum": __version__,
        "uclar": uclar,
        "sinirlar": _sinirlar(istemci),
        "olculmus": _olculmus(ORNEK_KUPON),
    }


#: Uretilmis JSON metni TEK kaynaktan: `scripts._ortak.metin`. Ayni govde
#: uc betikte birebir yaziliydi ve `--kontrol` bayraklari tam da bu metnin
#: kararliligina dayaniyor.
_metin = metin


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kontrol", action="store_true",
                    help="yazma, yalnizca dosyanin guncel olup olmadigina bak")
    ap.add_argument("--cikti", default=None)
    a = ap.parse_args(argv)

    yol = Path(a.cikti) if a.cikti else CIKTI
    metin = _metin(uret())

    if a.kontrol:
        mevcut = yol.read_text(encoding="utf-8") if yol.exists() else ""
        if mevcut != metin:
            print(f"✗ {yol.name} BAYAT — API govdesi degismis ama sozlesme "
                  f"yenilenmemis.\n  Duzeltmek icin: python scripts/api_sozlesme.py",
                  file=sys.stderr)
            return 1
        print(f"{yol.name} guncel")
        return 0

    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(metin, encoding="utf-8")
    print(f"yazildi: {yol} ({len(metin):,} bayt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
