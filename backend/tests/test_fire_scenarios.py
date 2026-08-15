"""fire_scenarios.py: secim DISI fire analizi testleri.

En onemlisi test_eski_yeni_birebir_ayni: modul numpy'a tasinirken ve
kume-disi sembol enumerasyonu carpana cevrilirken CIKTININ degismedigini
garanti eder. Referans olarak eski saf-Python uygulamasi burada tutulur.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations, product

import pytest

from spor_toto.core import Encoder, SEMBOLLER, parse_picks, solve_fix16
from spor_toto.fire_scenarios import fire_maliyeti, fire_scenario_report

ORNEK = "1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
# 10 banko + 4 cifte + 1 uclu -> uzay 2^4 * 3 = 48, kucuk ve uclu iceriyor
UCLULU = "1,1,1,1,1,1,1,1,1,1,10,10,10,10,102"


def _enc_cols(picks: str = ORNEK):
    enc = Encoder(parse_picks(picks))
    cols, _ = solve_fix16(enc)
    return enc, cols


def _enc_tam_sistem(picks: str):
    """
    fix16 en az 7 cifte ister; UCLULU kuponunda 4 cifte var. Esitlik testi
    icin kolonlarin optimal olmasi gerekmiyor, yalnizca deterministik ve
    gecerli olmalari yeterli — tam sistem ikisini de saglar.
    """
    enc = Encoder(parse_picks(picks))
    return enc, list(enc.variable_space())


# ============================================================
# REFERANS: eski saf-Python uygulamasi (degistirilmedi)
# ============================================================

def _referans(enc, cols, max_fires: int = 2) -> dict:
    code_full = [enc.decode_full(c) for c in cols]
    n = enc.total_len
    ALL = tuple(SEMBOLLER)
    sel_sets = [set(s) for s in enc.selections]
    in_opts = [list(sel_sets[i]) for i in range(n)]
    out_opts = [[s for s in ALL if s not in sel_sets[i]] for i in range(n)]
    failable = [i for i in range(n) if out_opts[i]]

    def min_dist(x) -> int:
        best = n
        for c in code_full:
            d = sum(1 for i in range(n) if x[i] != c[i])
            if d < best:
                best = d
                if best == 0:
                    break
        return best

    def ftype(i: int) -> str:
        k = len(sel_sets[i])
        return "banko" if k == 1 else ("double" if k == 2 else "triple")

    def pack(score_counts, n_total, by_type, by_match) -> dict:
        scores, pct = {}, {}
        for s in range(n, n - 6, -1):
            cnt = int(score_counts.get(s, 0))
            scores[str(s)] = cnt
            pct[str(s)] = round(100.0 * cnt / n_total, 4) if n_total else 0.0
        for s, cnt in score_counts.items():
            if str(s) not in scores:
                scores[str(s)] = int(cnt)
                pct[str(s)] = round(100.0 * cnt / n_total, 4) if n_total else 0.0
        type_out = {}
        for tname, c in by_type.items():
            tot = sum(c.values())
            if tot == 0:
                continue
            type_out[tname] = {
                "n": tot,
                "scores": {str(k): int(v) for k, v in sorted(c.items(), reverse=True)},
                "pct": {str(k): round(100.0 * v / tot, 4)
                        for k, v in sorted(c.items(), reverse=True)},
            }
        match_out = []
        for i in range(n):
            c = by_match.get(i, Counter())
            tot = sum(c.values())
            if tot == 0:
                match_out.append({"mac": i + 1, "type": ftype(i), "n": 0,
                                  "can_fail": bool(out_opts[i]), "scores": {}, "pct": {}})
                continue
            match_out.append({
                "mac": i + 1, "type": ftype(i), "n": tot, "can_fail": True,
                "scores": {str(k): int(v) for k, v in sorted(c.items(), reverse=True)},
                "pct": {str(k): round(100.0 * v / tot, 4)
                        for k, v in sorted(c.items(), reverse=True)},
            })
        return {
            "n": n_total, "scores": scores, "pct": pct,
            "by_type": type_out, "by_match": match_out,
            "min_best": min(score_counts.keys()) if score_counts else None,
            "max_best": max(score_counts.keys()) if score_counts else None,
            "p_ge_14": round(100.0 * sum(v for k, v in score_counts.items() if k >= 14) / n_total, 4) if n_total else 0.0,
            "p_ge_13": round(100.0 * sum(v for k, v in score_counts.items() if k >= 13) / n_total, 4) if n_total else 0.0,
            "p_ge_12": round(100.0 * sum(v for k, v in score_counts.items() if k >= 12) / n_total, 4) if n_total else 0.0,
        }

    out = {"note": "Secim disi fire: mac isaret disi. Uniform 1hata/2hata kume ici mesafedir."}

    if max_fires >= 1:
        sc = Counter()
        by_type = {"banko": Counter(), "double": Counter(), "triple": Counter()}
        by_match = {i: Counter() for i in range(n)}
        n_total = 0
        for fail_i in failable:
            ranges = [out_opts[k] if k == fail_i else in_opts[k] for k in range(n)]
            ft = ftype(fail_i)
            for combo in product(*ranges):
                correct = n - min_dist(combo)
                sc[correct] += 1
                by_type[ft][correct] += 1
                by_match[fail_i][correct] += 1
                n_total += 1
        out["fire1"] = pack(sc, n_total, by_type, by_match)

    if max_fires >= 2:
        sc = Counter()
        by_type = {"banko+banko": Counter(), "banko+double": Counter(),
                   "double+double": Counter()}
        by_match = {i: Counter() for i in range(n)}
        n_total = 0
        for i, j in combinations(failable, 2):
            ranges = [out_opts[k] if k in (i, j) else in_opts[k] for k in range(n)]
            tkey = "+".join(sorted([ftype(i), ftype(j)]))
            if tkey not in by_type:
                by_type[tkey] = Counter()
            for combo in product(*ranges):
                correct = n - min_dist(combo)
                sc[correct] += 1
                by_type[tkey][correct] += 1
                by_match[i][correct] += 1
                by_match[j][correct] += 1
                n_total += 1
        out["fire2"] = pack(sc, n_total, by_type, by_match)

    return out


# ============================================================
# ESITLIK
# ============================================================

def test_eski_yeni_birebir_ayni_standart():
    enc, cols = _enc_cols()
    assert fire_scenario_report(enc, cols) == _referans(enc, cols)


def test_eski_yeni_birebir_ayni_uclu_iceren():
    """Uclu maclar fire uretemez; karisik kuponda da esitlik korunmali."""
    enc, cols = _enc_tam_sistem(UCLULU)
    assert fire_scenario_report(enc, cols) == _referans(enc, cols)


def test_eski_yeni_birebir_ayni_bozuk_kaplama():
    """Kaplama eksikken de (maxcov benzeri) ayni sonuc."""
    enc, cols = _enc_cols()
    kismi = cols[:5]
    assert fire_scenario_report(enc, kismi) == _referans(enc, kismi)


# ============================================================
# HIZLANDIRMANIN DAYANDIGI OZDESLIK
# ============================================================

def test_kume_disi_sembol_secimi_skoru_degistirmez():
    """
    Fire olan pozisyonda her kolon kume ICI sembol tasir; senaryo kume DISI
    sembol tasir. Uyusmazlik garanti oldugu icin HANGI disi sembolun geldigi
    mesafeyi degistirmez. Carpan optimizasyonu buna dayanir.
    """
    enc, cols = _enc_cols()
    code = [enc.decode_full(c) for c in cols]
    n = enc.total_len
    sel = [set(s) for s in enc.selections]

    def mind(x):
        return min(sum(1 for i in range(n) if x[i] != c[i]) for c in code)

    kontrol = 0
    for i in range(n):
        disi = [s for s in SEMBOLLER if s not in sel[i]]
        if len(disi) < 2:
            continue
        ic = [sorted(sel[k]) for k in range(n)]
        for combo in product(*[ic[k] if k != i else ["?"] for k in range(n)]):
            x = list(combo)
            skorlar = set()
            for d in disi:
                x[i] = d
                skorlar.add(mind(tuple(x)))
            assert len(skorlar) == 1, f"{i}. macta disi sembol skoru degistirdi"
            kontrol += 1
    assert kontrol > 0


# ============================================================
# ANLAMSAL INVARIANTLAR
# ============================================================

def test_fire1_de_15_imkansiz():
    """Bir mac isaret disindaysa hicbir kolon 15 tutturamaz."""
    enc, cols = _enc_cols()
    r = fire_scenario_report(enc, cols, max_fires=1)
    assert r["fire1"]["scores"]["15"] == 0


def test_fire2_de_14_imkansiz():
    """Iki mac isaret disindaysa en iyi kolon en fazla 13 tutturur."""
    enc, cols = _enc_cols()
    r = fire_scenario_report(enc, cols)
    assert r["fire2"]["scores"]["15"] == 0
    assert r["fire2"]["scores"]["14"] == 0
    assert r["fire2"]["p_ge_14"] == 0.0


def test_banko_fire_ciftе_fireindan_pahali():
    """
    Bankoda yanilmak ciftede yanilmaktan daha kotu sonuc verir: banko her
    kolonda sabittir, cifte ise Hamming blogunun icindedir.
    """
    enc, cols = _enc_cols()
    bt = fire_scenario_report(enc, cols, max_fires=1)["fire1"]["by_type"]
    banko_14 = bt["banko"]["pct"].get("14", 0.0)
    cifte_14 = bt["double"]["pct"].get("14", 0.0)
    assert cifte_14 > banko_14


def test_uclu_mac_fire_uretemez():
    enc, cols = _enc_tam_sistem(UCLULU)
    r = fire_scenario_report(enc, cols, max_fires=1)
    ucluler = [m for m in r["fire1"]["by_match"] if m["type"] == "triple"]
    assert ucluler
    for m in ucluler:
        assert m["can_fail"] is False
        assert m["n"] == 0


def test_yuzdeler_toplami_yaklasik_yuz():
    enc, cols = _enc_cols()
    r = fire_scenario_report(enc, cols)
    for blok in ("fire1", "fire2"):
        toplam = sum(r[blok]["pct"].values())
        assert abs(toplam - 100.0) < 0.01


def test_fire2_by_match_iki_kat_sayar():
    """Her senaryo iki maca birden yazilir; bu kasitli bir kosullu dagilimdir."""
    enc, cols = _enc_cols()
    f2 = fire_scenario_report(enc, cols)["fire2"]
    toplam = sum(m["n"] for m in f2["by_match"])
    assert toplam == 2 * f2["n"]


# ============================================================
# KENAR DURUMLARI
# ============================================================

def test_max_fires_sifir_hic_calismaz():
    enc, cols = _enc_cols()
    r = fire_scenario_report(enc, cols, max_fires=0)
    assert "fire1" not in r and "fire2" not in r
    assert "note" in r


def test_bos_kolon_listesi():
    enc = Encoder(parse_picks(ORNEK))
    r = fire_scenario_report(enc, [], max_fires=1)
    assert r["fire1"]["n"] == 0
    assert r["fire1"]["min_best"] is None


# ============================================================
# MALIYET TAHMINI
# ============================================================

def test_fire_maliyeti_gercek_senaryo_sayisiyla_uyumlu():
    """Kapali formul, gercekten uretilen ayrik senaryo sayisini vermeli."""
    enc, cols = _enc_cols()
    # fire1 ayrik senaryo sayisi = sum(uzay / k_i) failable uzerinden
    k = [len(s) for s in enc.selections]
    uzay = 1
    for x in k:
        uzay *= x
    beklenen = sum(uzay // k[i] for i in range(len(k)) if k[i] < 3) * len(cols)
    assert fire_maliyeti(enc, cols, max_fires=1) == beklenen


def test_fire_maliyeti_artan():
    enc, cols = _enc_cols()
    m0 = fire_maliyeti(enc, cols, max_fires=0)
    m1 = fire_maliyeti(enc, cols, max_fires=1)
    m2 = fire_maliyeti(enc, cols, max_fires=2)
    assert m0 == 0
    assert m1 > 0
    assert m2 > m1


@pytest.mark.slow
def test_buyuk_kupon_maliyeti_esigin_ustunde():
    """Uclu iceren gercekci kupon senkron istek yolunda calistirilamaz."""
    enc = Encoder(parse_picks(",".join(["1"] * 4 + ["10"] * 7 + ["102"] * 4)))
    cols, _ = solve_fix16(enc)
    assert fire_maliyeti(enc, cols, max_fires=2) > 100_000_000
