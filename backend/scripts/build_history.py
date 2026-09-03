#!/usr/bin/env python3
"""Tarihsel 1/0/2 veri setini kaynagindan yeniden uretir.

    python scripts/build_history.py                  # cek, dogrula, yaz
    python scripts/build_history.py --dry-run        # yazmadan farki goster
    python scripts/build_history.py --cache /tmp/p   # payload'lari sakla/kullan

Kaynak: sportototahmin.com hafta payload'lari (Nuxt dehidrasyon dizisi).

Iki kural bu dosyanin varlik sebebi:

1. **Sira, haftanin kendi `matches` dizisinden gelir.** Payload icinde maca
   benzeyen baska bloklar da var (`featuredMatches`); diziyi duz tarayip
   birlestirmek kupon sirasini bozar. Onceki veri setinde 41 haftanin 15'inde
   sira, 6'sinda da sayim bu yuzden hataliydi.
2. **Skor, macin kendi referans zincirinden gelir** (`match.score.homeRegular`),
   "15 isim + 15 skor listesini sirayla yapistir" ile degil.

Kesinlik esigi: yalnizca tam 15 gecerli sonucu olan haftalar yazilir.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
# `scripts` paketini ice aktarabilmek icin — oteki betiklerin
# deseninin aynisi. Sema denetimi (`sema_dogrula`) TEK yerde yazili
# olsun diye gerekli; ikinci bir kopya ilk gun ayrisir.
sys.path.insert(0, str(KOK))

from scripts._ortak import sema_dogrula

VARSAYILAN_CIKTI = KOK / "data" / "st_history_2025_26.json"
URL = "https://sportototahmin.com/spor-toto/{week}-hafta-tahminleri/_payload.json"
UA = "spor-toto-lab/1.0 (veri yeniden uretimi; tek seferlik arsiv cekimi)"

SEMBOLLER = ("1", "0", "2")
MAC_SAYISI = 15
MAKUL_GOL = range(0, 21)


# ─── payload cozumleme ────────────────────────────────────────────────────────

def indir(week: int, cache: Path | None, timeout: float = 45.0) -> list | None:
    if cache:
        p = cache / f"w{week}.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
    hedef_url = URL.format(week=week)
    sema_dogrula(hedef_url)          # denetim `_ortak`ta, kopyalanmiyor
    istek = urllib.request.Request(hedef_url, headers={  # noqa: S310
        "User-Agent": UA, "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(istek, timeout=timeout) as r:  # noqa: S310
            ham = r.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  hafta {week}: indirilemedi ({e})", file=sys.stderr)
        return None
    try:
        veri = json.loads(ham)
    except json.JSONDecodeError:
        print(f"  hafta {week}: payload JSON degil", file=sys.stderr)
        return None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"w{week}.json").write_text(ham, encoding="utf-8")
    return veri


def coz(dizi: list, idx: Any, derinlik: int = 0) -> Any:
    """Nuxt referansini (["Reactive", i] vb.) duz degere indirger."""
    if derinlik > 12:
        return None
    v = dizi[idx] if isinstance(idx, int) and 0 <= idx < len(dizi) else idx
    if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
        return coz(dizi, v[1], derinlik + 1)
    return v


def hafta_katalogu(dizi: list, week: int) -> dict[str, Any]:
    """Kapanis tarihi ve sezon.

    Haftanin kendi nesnesi bu alanlari `roundCloseDate` / `year` diye tasir;
    `nearbyWeekSummaries` icindeki komsu hafta ozetleri ise `closeDate` /
    `season` der. Ikisine de bakariz, once haftanin kendi kaydina.
    """
    yedek = {"close_date": "", "season": ""}
    for v in dizi:
        if not isinstance(v, dict) or "weekNumber" not in v:
            continue
        if coz(dizi, v["weekNumber"]) != week:
            continue
        kapanis = coz(dizi, v.get("roundCloseDate")) or coz(dizi, v.get("closeDate"))
        sezon = coz(dizi, v.get("year")) or coz(dizi, v.get("season")) or ""
        kayit = {"close_date": str(kapanis or "")[:10], "season": str(sezon)}
        if "matches" in v and kayit["close_date"]:
            return kayit
        if kayit["close_date"] and not yedek["close_date"]:
            yedek = kayit
    return yedek


def hafta_maclari(dizi: list, week: int) -> list[dict[str, Any]]:
    """Haftanin KENDI `matches` dizisini sirasiyla cozer."""
    hedef = None
    for v in dizi:
        if isinstance(v, dict) and "matches" in v and "weekNumber" in v:
            if coz(dizi, v["weekNumber"]) != week:
                continue
            liste = coz(dizi, v["matches"])
            if isinstance(liste, list) and liste:
                hedef = liste
                break
    if hedef is None:
        return []

    out: list[dict[str, Any]] = []
    for ham in hedef:
        kayit = coz(dizi, ham)
        if not isinstance(kayit, dict):
            continue
        ev = coz(dizi, kayit.get("homeTeamName"))
        dep = coz(dizi, kayit.get("awayTeamName"))
        mac = coz(dizi, kayit.get("match"))
        if not isinstance(mac, dict):
            continue
        skor = coz(dizi, mac.get("score"))
        tarih = coz(dizi, mac.get("date")) or coz(dizi, kayit.get("date"))
        if not isinstance(skor, dict):
            continue
        eg = coz(dizi, skor.get("homeRegular"))
        dg = coz(dizi, skor.get("awayRegular"))
        if not (isinstance(eg, int) and isinstance(dg, int)):
            continue
        if eg not in MAKUL_GOL or dg not in MAKUL_GOL:
            continue
        out.append({
            "no": len(out) + 1,
            "home": str(ev or "").strip(),
            "away": str(dep or "").strip(),
            "kickoff": str(tarih or "")[:16].replace("T", " "),
            "hg": eg,
            "ag": dg,
            "code": "1" if eg > dg else "0" if eg == dg else "2",
        })
    return out


# ─── ozet ─────────────────────────────────────────────────────────────────────

def bant(degerler: list[int]) -> dict[str, Any]:
    ort = statistics.fmean(degerler)
    ust = [v for v in degerler if v > ort]
    alt = [v for v in degerler if v <= ort]
    ust_ort = statistics.fmean(ust) if ust else ort
    alt_ort = statistics.fmean(alt) if alt else ort
    return {
        "avg": round(ort, 4),
        "min": min(degerler),
        "max": max(degerler),
        "median": round(statistics.median(degerler), 4),
        "std": round(statistics.pstdev(degerler), 4),
        "above_n": len(ust),
        "below_n": len(alt),
        "above_mean": round(ust_ort, 4),
        "below_mean": round(alt_ort, 4),
        "above_gap": round(ust_ort - ort, 4),
        "below_gap": round(ort - alt_ort, 4),
    }


def veri_seti(haftalar: list[dict[str, Any]], kaynak: str) -> dict[str, Any]:
    n = len(haftalar)
    mac = sum(len(w["matches"]) for w in haftalar)
    toplam: dict[str, Any] = {
        s: sum(w["results"].count(s) for w in haftalar) for s in SEMBOLLER
    }
    for s in SEMBOLLER:
        toplam[f"pct_{s}"] = round(100 * toplam[s] / mac, 4) if mac else 0.0
    return {
        "meta": {
            "season": haftalar[0]["season"] if haftalar else "",
            "date_from": min((w["close_date"] for w in haftalar), default=""),
            "date_to": max((w["close_date"] for w in haftalar), default=""),
            "weeks": n,
            "matches": mac,
            "source": kaynak,
            "rule": "only weeks with exactly 15 results; match order from the week's own matches array",
            "generated_at": date.today().isoformat(),
        },
        "totals": toplam,
        "weekly_avg": {
            s: round(toplam[s] / n, 4) if n else 0.0 for s in SEMBOLLER
        },
        "bands": {
            s: bant([w["results"].count(s) for w in haftalar]) for s in SEMBOLLER
        },
        "weeks": haftalar,
    }


# ─── ana akis ─────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="ilk", type=int, default=1)
    ap.add_argument("--to", dest="son", type=int, default=53)
    ap.add_argument("--out", type=Path, default=VARSAYILAN_CIKTI)
    ap.add_argument("--cache", type=Path, default=None,
                    help="payload'lari bu dizinde sakla/oradan oku")
    ap.add_argument("--dry-run", action="store_true", help="dosyaya yazma")
    args = ap.parse_args()

    kabul: list[dict[str, Any]] = []
    elenen: list[str] = []

    for week in range(args.ilk, args.son + 1):
        dizi = indir(week, args.cache)
        if not isinstance(dizi, list):
            elenen.append(f"{week}: payload yok")
            continue
        maclar = hafta_maclari(dizi, week)
        if len(maclar) != MAC_SAYISI:
            elenen.append(f"{week}: {len(maclar)} gecerli mac")
            continue
        meta = hafta_katalogu(dizi, week)
        results = "".join(m["code"] for m in maclar)
        kabul.append({
            "week": week,
            "close_date": meta["close_date"],
            "season": meta["season"],
            "n1": results.count("1"),
            "n0": results.count("0"),
            "n2": results.count("2"),
            "results": results,
            "matches": maclar,
        })
        print(f"  hafta {week:>2}: {results}  ({maclar[0]['home']} … {maclar[-1]['away']})")

    if not kabul:
        print("Hicbir hafta kabul edilmedi.", file=sys.stderr)
        return 1

    kabul.sort(key=lambda w: w["week"])
    cikti = veri_seti(
        kabul,
        "sportototahmin week payloads (week.matches order, match-linked scores); "
        "incomplete weeks excluded",
    )

    print(f"\nkabul: {len(kabul)} hafta / {cikti['meta']['matches']} mac")
    print(f"elenen: {len(elenen)} hafta")
    for e in elenen:
        print(f"  - {e}")
    t = cikti["totals"]
    print(f"toplam 1/0/2: {t['1']}/{t['0']}/{t['2']}  "
          f"(%{t['pct_1']:.2f} / %{t['pct_0']:.2f} / %{t['pct_2']:.2f})")

    # Ic tutarlilik: dizi ile sayimlar ve mac listesi birbirini tutmali.
    for w in kabul:
        assert len(w["results"]) == MAC_SAYISI == len(w["matches"])
        assert (w["n1"], w["n0"], w["n2"]) == tuple(
            w["results"].count(s) for s in SEMBOLLER
        )
        assert w["results"] == "".join(m["code"] for m in w["matches"])

    if args.dry_run:
        print("\n--dry-run: dosya yazilmadi")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(cikti, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nyazildi: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
