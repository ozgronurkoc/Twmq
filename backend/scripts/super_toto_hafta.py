#!/usr/bin/env python3
"""İşlenen sezonun bir haftasını, GEÇEN SEZONUN kendi ölçümleriyle okur.

Bu script tahmin üretmez. Yaptığı tek şey, `data/super_toto/<sezon>/hafta_NN.json`
içindeki oranları ve oynanma yüzdelerini alıp **geçen sezonda ölçülmüş**
tablolara (favori bantları, çift kapsama, beraberlik profili, lig kırılımı)
oturtmak ve aynı stratejinin bu hafta ne işaretleyeceğini göstermektir.

Neden ayrı script: hafta verisi henüz üretim boru hattında değil (elle
girildi) ve `/api/stats` yolunun beslediği arşive KARIŞMAMALI. Geçen sezon
arşivi kapanmış bir kayıttır; bu dosya onu okur, ona yazmaz.

    python scripts/super_toto_hafta.py --hafta 1
    python scripts/super_toto_hafta.py --hafta 1 --json

UYARI: oranlar iddaa oranıdır, geçen sezon arşivi football-data piyasa
kapanışıdır. Marj farkı (§3.2) yüzünden marj arındırılmış olasılıklar
birebir aynı ölçekte DEĞİLDİR; script bu farkı ölçer ve yazar.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.backtest import (
    VARSAYILAN_BANKO,
    VARSAYILAN_UCLU,
    _kaplama,
    secim_uret,
)
from spor_toto.core import SEMBOLLER as _SEMBOLLER
from spor_toto.core import (
    Encoder,
    butce_danismani,
    merge_rows,
    solve_fix16,
)
from spor_toto.history import history_analytics, history_summary
from spor_toto.odds import (
    CIFT_BANTLARI,
    FARK_BANTLARI,
    FAVORI_BANTLARI,
    implied_probs,
    season_1x2_summary,
)

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
SEMBOLLER = _SEMBOLLER
VERI_KOK = KOK / "data" / "super_toto"


# ─── veri ─────────────────────────────────────────────────────────────────────

#: Bir satırın marjı bültenin ortancasından bu kadar puan saparsa KUŞKULU
#: damgası basılır. 2. haftada 4. maçın marjı %45,8'di (bültenin geri kalanı
#: %17,5–17,9) ve bunu **insan** yakaladı, kod değil. Elle girilen veride tek
#: gerçek savunma budur.
#:
#: 5 puan, ölçüm sonucuna bakılmadan seçildi: bültenler kendi içinde 1 puanın
#: altında oynuyor, gerçek giriş hataları ise on puanlarla sapıyor — arada
#: geniş bir boşluk var ve eşik oraya kondu.
MARJ_SAPMA_ESIGI = 5.0

#: Marjın kendi başına saçma sayıldığı sınırlar. Altı: oranlar arbitraj
#: verirdi (bülten böyle bir şey yayımlamaz, demek ki giriş hatası). Üstü:
#: hiçbir bülten bu marjla oynamaz.
MARJ_ALT, MARJ_UST = 0.0, 0.60


def dogrula(d: dict[str, Any]) -> list[str]:
    """Elle girilen hafta dosyasını denetler ve uyarı listesi döner.

    **Uyarı üretir, veri düzeltmez.** Şüpheli bir satırı sessizce onarmak
    veri doktrinine aykırı olurdu (belirsiz veri atılır ya da işaretlenir,
    uydurulmaz); burada yapılan işaretlemedir.

    `build_egitim.dogrula` ile aynı biçim: `assert` yerine liste döner çünkü
    bu dosya kullanıcının elinden çıkıyor ve koşumu durdurmak yerine
    şüpheyi görünür kılmak istiyoruz.
    """
    uyarilar: list[str] = []
    maclar = d.get("matches") or []

    marjlar = [(m["no"], sum(1.0 / v for v in m["odds"].values()) - 1.0)
               for m in maclar if m.get("odds")]
    if len(marjlar) >= 3:
        sirali = sorted(x[1] for x in marjlar)
        ortanca = sirali[len(sirali) // 2]
        for no, marj in marjlar:
            sapma = 100 * abs(marj - ortanca)
            if sapma > MARJ_SAPMA_ESIGI:
                uyarilar.append(
                    f"{no}. maç: marj %{100*marj:.1f}, bültenin ortancası "
                    f"%{100*ortanca:.1f} — {sapma:.1f} puan sapma, KUŞKULU")

    for no, marj in marjlar:
        if not (MARJ_ALT < marj < MARJ_UST):
            uyarilar.append(
                f"{no}. maç: marj %{100*marj:.1f} — hiçbir bültende olmayacak "
                f"bir değer, giriş hatası olmalı")

    for m in maclar:
        if m.get("odds") and any(v <= 1.0 for v in m["odds"].values()):
            uyarilar.append(f"{m['no']}. maç: 1.00'den küçük oran var")
        pay = m.get("play_pct") or {}
        if set(pay) != set(SEMBOLLER):
            uyarilar.append(f"{m['no']}. maç: oynanma yüzdesi eksik")
        elif not 90 <= sum(pay.values()) <= 110:
            uyarilar.append(
                f"{m['no']}. maç: oynanma yüzdeleri toplamı "
                f"%{sum(pay.values()):.0f} — 100'den uzak")

    ligler = [m.get("league") for m in maclar]
    if any(not x for x in ligler):
        uyarilar.append("lig etiketi olmayan maç var")

    sonuc = (d.get("meta") or {}).get("results")
    if sonuc is not None:
        if len(sonuc) != 15 or any(c not in SEMBOLLER for c in sonuc):
            uyarilar.append(f"sonuç dizisi bozuk: {sonuc!r}")
    return uyarilar


def hafta_yukle(sezon: str, hafta: int) -> dict[str, Any]:
    yol = VERI_KOK / sezon / f"hafta_{hafta:02d}.json"
    if not yol.exists():
        raise SystemExit(f"Hafta dosyası yok: {yol}")
    d = json.loads(yol.read_text(encoding="utf-8"))
    maclar = d["matches"]
    if len(maclar) != 15:
        raise SystemExit(f"15 maç bekleniyor, {len(maclar)} var")
    # Elle yazilan uyarilar KORUNUR; uretilenler onlarin ustune eklenir.
    # Kod insani duzeltmez, insan da kodu susturmaz — ikisi yan yana durur.
    d.setdefault("meta", {}).setdefault("data_warnings", [])
    d["meta"]["uretilen_uyarilar"] = dogrula(d)
    for m in maclar:
        # Oranı ilan edilmemiş maç: olasılık 1/3–1/3–1/3. Bu bir TAHMİN
        # DEĞİL, bilgi yokluğunun ilanıdır — arayüzün ESIT kuralıyla aynı
        # (bkz. app/istatistik/[week]/page.tsx). Böyle bir maç kuralın
        # üçlü eşiğinin (0,38) altında kalır ve otomatik olarak kapatılır.
        m["odds_yok"] = not m.get("odds")
        if m["odds_yok"]:
            m["odds"] = None
            m["probs"] = dict.fromkeys(SEMBOLLER, 1.0 / 3)
            m["margin"] = 0.0
            m["fav"] = None
        else:
            m["probs"] = implied_probs(m["odds"])
            m["margin"] = sum(1.0 / v for v in m["odds"].values()) - 1.0
            m["fav"] = min(m["odds"], key=lambda s: m["odds"][s])
        m["sirali"] = sorted(m["probs"].items(),
                             key=lambda kv: (-kv[1], SEMBOLLER.index(kv[0])))
        # Oynanma yüzdesi platformun kendi kullanıcı payıdır; 100'e
        # normalize edilir ki oranla aynı ölçekte kıyaslanabilsin.
        t = sum(m["play_pct"].values()) or 100
        m["play"] = {s: m["play_pct"][s] / t for s in SEMBOLLER}
    return d


# ─── geçen sezonun tabloları ──────────────────────────────────────────────────

def _bant_bul(bantlar, deger):
    for lo, hi in bantlar:
        if lo <= deger < hi:
            return lo, hi
    return None


def gecen_sezon_ref() -> dict[str, Any]:
    ozet = season_1x2_summary() or {}
    return {
        "odds": ozet,
        "hist": history_summary(),
        "analytics": history_analytics(),
        "fav_band": {(b["lo"], b["hi"] if b["hi"] else 99.0): b
                     for b in ozet.get("favourite_bands", [])},
        "cift_band": {(b["lo"], b["hi"] if b["hi"] else 1.01): b
                      for b in ozet.get("set_coverage", [])},
        "fark_band": {(b["lo"], b["hi"] if b["hi"] else 1.01): b
                      for b in ozet.get("draw_profile", [])},
        "lig": {b["league"]: b for b in ozet.get("leagues", [])},
    }


def hafta_profili(d: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    """Bu haftayı geçen sezonun bantlarına oturtur."""
    maclar = d["matches"]
    bekle = {s: sum(m["probs"][s] for m in maclar) for s in SEMBOLLER}
    fav_sayim = {s: sum(1 for m in maclar if m["fav"] == s) for s in SEMBOLLER}

    satirlar = []
    fav_bekleyen = 0.0
    fav_gecmis = 0.0
    cift_bekleyen = 0.0
    cift_gecmis = 0.0
    ber_gecmis = 0.0
    for m in maclar:
        fav_oran = m["odds"][m["fav"]] if not m["odds_yok"] else None
        fb = _bant_bul(FAVORI_BANTLARI, fav_oran) if fav_oran else None
        fb_ref = ref["fav_band"].get(fb) if fb else None
        ikili = m["sirali"][0][1] + m["sirali"][1][1]
        cb = _bant_bul(CIFT_BANTLARI, ikili)
        cb_ref = ref["cift_band"].get(cb) if cb else None
        fark = m["sirali"][0][1] - m["sirali"][1][1]
        kb = _bant_bul(FARK_BANTLARI, fark)
        kb_ref = ref["fark_band"].get(kb) if kb else None

        fav_bekleyen += m["probs"][m["fav"]] if m["fav"] else 0.0
        if fb_ref:
            fav_gecmis += fb_ref["hit_pct"] / 100
        cift_bekleyen += ikili
        if cb_ref:
            cift_gecmis += cb_ref["in_two_pct"] / 100
        if kb_ref:
            ber_gecmis += kb_ref["draw_pct"] / 100

        satirlar.append({
            "no": m["no"], "mac": f"{m['home']} – {m['away']}",
            "lig": m["league"], "odds": m["odds"], "probs": m["probs"],
            "fav": m["fav"], "fav_oran": fav_oran, "margin": m["margin"],
            "odds_yok": m["odds_yok"],
            "fav_band": fb_ref["label"] if fb_ref else None,
            "fav_band_hit": fb_ref["hit_pct"] if fb_ref else None,
            "fav_band_draw": fb_ref["draw_pct"] if fb_ref else None,
            "fav_band_n": fb_ref["n"] if fb_ref else None,
            "ikili": ikili,
            "cift_band": cb_ref["label"] if cb_ref else None,
            "cift_band_in_two": cb_ref["in_two_pct"] if cb_ref else None,
            "cift_band_n": cb_ref["n"] if cb_ref else None,
            "fark": fark,
            "fark_band": kb_ref["label"] if kb_ref else None,
            "fark_band_draw": kb_ref["draw_pct"] if kb_ref else None,
            "play": m["play"], "play_pct": m["play_pct"],
        })

    ligler: dict[str, int] = {}
    for m in maclar:
        ligler[m["league"]] = ligler.get(m["league"], 0) + 1

    return {
        "rows": satirlar,
        "expected": bekle,
        "fav_split": fav_sayim,
        "fav_expected_market": fav_bekleyen,
        "fav_expected_history": fav_gecmis,
        "double_expected_market": cift_bekleyen,
        "double_expected_history": cift_gecmis,
        "draw_expected_history": ber_gecmis,
        # Marj ortalaması YALNIZCA oranı olan maçlardan; oransız maçın
        # marjı 0'dır ve ortalamayı sahte biçimde aşağı çekerdi.
        "avg_margin_pct": (
            100 * sum(m["margin"] for m in maclar if not m["odds_yok"])
            / max(1, sum(1 for m in maclar if not m["odds_yok"]))),
        "leagues": ligler,
    }


# ─── kamuoyu (oynanma) — geçen sezonda karşılığı OLMAYAN boyut ────────────────

def kamuoyu(d: dict[str, Any]) -> dict[str, Any]:
    """Oynanma payı ile piyasa olasılığının farkı.

    Müşterek bahiste aynı olasılıktaki iki sonuçtan AZ oynananı işaretlemek,
    tutturma olasılığını değiştirmeden alınacak payı büyütür. Bu tablo o
    farkı ölçer — hangi sonucun daha olası olduğunu SÖYLEMEZ.
    """
    out = []
    for m in d["matches"]:
        satir = {"no": m["no"], "mac": f"{m['home']} – {m['away']}", "cells": {}}
        for s in SEMBOLLER:
            p, o = m["probs"][s], m["play"][s]
            satir["cells"][s] = {
                "prob": p, "play": o, "diff": o - p,
                "ratio": (o / p) if p > 0 else None,
            }
        fav = m["fav"]
        satir["fav"] = fav
        # Oranı olmayan maçın favorisi yoktur; sapma hesabına girmez.
        satir["fav_diff"] = (m["play"][fav] - m["probs"][fav]) if fav else 0.0
        satir["max_play"] = max(SEMBOLLER, key=lambda s: m["play"][s])
        satir["consensus"] = max(m["play"].values())
        out.append(satir)
    toplam_play = {s: sum(m["play"][s] for m in d["matches"]) for s in SEMBOLLER}
    toplam_prob = {s: sum(m["probs"][s] for m in d["matches"]) for s in SEMBOLLER}
    return {
        "rows": out,
        "totals": {"play": toplam_play, "market": toplam_prob},
        "avg_fav_diff": (sum(r["fav_diff"] for r in out if r["fav"])
                         / max(1, sum(1 for r in out if r["fav"]))),
        "consensus_70": sum(1 for r in out if r["consensus"] >= 0.70),
        "public_vs_market_disagree": [
            r["no"] for r in out if r["max_play"] != r["fav"]
        ],
    }


# ─── kupon ────────────────────────────────────────────────────────────────────

def kupon_kur(d: dict[str, Any], banko: float, uclu: float) -> dict[str, Any]:
    maclar = d["matches"]
    secimler = [secim_uret(m["probs"], banko, uclu) for m in maclar]
    boyutlar = tuple(len(s) for s in secimler if len(s) > 1)
    imza = tuple(sorted(boyutlar))
    kap = _kaplama(imza)

    kume_ici = 1.0
    kalabalik_ici = 1.0
    for m, sec in zip(maclar, secimler):
        kume_ici *= sum(m["probs"][s] for s in sec)
        kalabalik_ici *= sum(m["play"][s] for s in sec)

    # Her maç için: küme-içini kaç kat büyütür, bedeli kaç kat büyütür.
    oneriler = []
    for m, sec in zip(maclar, secimler):
        icinde = sum(m["probs"][s] for s in sec)
        k = len(sec)
        if k == 3:
            continue
        kalan = sorted(((s, m["probs"][s]) for s in SEMBOLLER if s not in sec),
                       key=lambda kv: -kv[1])
        ekle, p_ekle = kalan[0]
        oneriler.append({
            "no": m["no"], "mac": f"{m['home']} – {m['away']}",
            "ekle": ekle, "kume_carpani": (icinde + p_ekle) / icinde if icinde else None,
            "bedel_carpani": (k + 1) / k,
            "verim": ((icinde + p_ekle) / icinde) / ((k + 1) / k) if icinde else None,
        })
    oneriler.sort(key=lambda r: -(r["verim"] or 0))

    return {
        "banko_esik": banko, "uclu_esik": uclu,
        "picks": ["".join(s) for s in secimler],
        "banko": [i + 1 for i, s in enumerate(secimler) if len(s) == 1],
        "cift": [i + 1 for i, s in enumerate(secimler) if len(s) == 2],
        "uclu": [i + 1 for i, s in enumerate(secimler) if len(s) == 3],
        "space": math.prod(len(s) for s in secimler),
        "columns": kap["columns"] if kap else None,
        "rows": kap["rows"] if kap else None,
        "engine": kap["engine"] if kap else None,
        "guaranteed": kap["guaranteed"] if kap else None,
        "in_set_p": kume_ici,
        "in_set_1_in": (1 / kume_ici) if kume_ici > 0 else None,
        # Kalabalık-içi: rastgele bir halk kuponunun bu seçim kümesine
        # düşme payı (maçlar bağımsız varsayılır). Küme-içine oranı 1'in
        # ALTINDAYSA küme, olasılığına göre fazla oynanmış demektir —
        # tutarsa ikramiye daha çok bölünür.
        "crowd_in_set_p": kalabalik_ici,
        "crowd_ratio": (kume_ici / kalabalik_ici) if kalabalik_ici > 0 else None,
        "per_match_crowd": [
            {"no": m["no"], "sec": "".join(sec),
             "prob_in": sum(m["probs"][s] for s in sec),
             "play_in": sum(m["play"][s] for s in sec)}
            for m, sec in zip(maclar, secimler)
        ],
        "upgrades": oneriler[:6],
    }


def butce_merdiveni(d: dict[str, Any], secimler: list[list[str]],
                    butceler: list[int]) -> list[dict[str, Any]]:
    """Bütçe düşerse hangi maç kısılır — motorun kendi bütçe danışmanı.

    Kısma sırasını olasılık belirler (en düşük olasılıklı sembol önce
    düşer); bu script bir tercih üretmez, motorun planını okur.
    """
    enc = Encoder([list(s) for s in secimler])
    probs = [m["probs"] for m in d["matches"]]
    out = []
    for b in sorted(butceler):
        planlar = butce_danismani(enc, b, probs, en_fazla=1)
        if not planlar:
            out.append({"budget": b, "plan": None})
            continue
        pl = planlar[0]
        kalabalik = math.prod(
            sum(d["matches"][j]["play"][s] for s in pl.selections[j])
            for j in range(len(pl.selections)))
        out.append({
            "budget": b, "cost": pl.bedel, "rows": pl.satir,
            "picks": ["".join(x) for x in pl.selections],
            "changes": pl.degisiklikler,
            "in_set_p": pl.p_kume_ici,
            "crowd_in_set_p": kalabalik,
            "crowd_ratio": (pl.p_kume_ici / kalabalik) if kalabalik else None,
        })
    return out


def yaz(d: dict[str, Any], prof: dict[str, Any], kam: dict[str, Any],
        ref: dict[str, Any], kuponlar: list[dict[str, Any]],
        merdiven: list[dict[str, Any]]) -> None:
    meta = d["meta"]
    o = ref["odds"]
    h = ref["hist"]
    print(f"\n{'='*78}\n{meta['season']} · {meta['week']}. HAFTA · {meta['program']}\n{'='*78}")
    print(f"Oran kaynağı : {meta['odds_source']}")
    print(f"Oynanma      : {meta['play_source']}")
    print(f"Sonuç/ikramiye: {'YOK — bu analiz sonuçları görmeden yapıldı' if not meta.get('results') else 'var'}")

    elle = meta.get("data_warnings") or []
    uretilen = meta.get("uretilen_uyarilar") or []
    if elle or uretilen:
        print("\n─── VERİ UYARILARI ──────────────────────────────────────────────────────")
        for u in elle:
            print(f"  [elle]    {u}")
        for u in uretilen:
            print(f"  [kod]     {u}")

    print("\n─── 1. MARJ ─────────────────────────────────────────────────────────────")
    print(f"Bu hafta (iddaa)        : %{prof['avg_margin_pct']:.2f}")
    print(f"Geçen sezon (football-data): %{o['avg_margin_pct']:.2f}")
    print(f"Kat                     : {prof['avg_margin_pct'] / o['avg_margin_pct']:.2f}×")

    print("\n─── 2. MAÇ MAÇ ──────────────────────────────────────────────────────────")
    print(f"{'#':>2} {'Maç':<34} {'Lig':<4} {'oran 1/0/2':<20} {'olasılık':<20} "
          f"{'fav':<4} {'bant':<12} {'geç.sezon isabet'}")
    for r in prof["rows"]:
        oranstr = ("oran YOK" if r["odds_yok"]
                   else "/".join(f"{r['odds'][s]:.2f}" for s in SEMBOLLER))
        pstr = "/".join(f"{100*r['probs'][s]:.0f}" for s in SEMBOLLER)
        bant_not = ("—" if r["fav_band_hit"] is None
                    else f"%{r['fav_band_hit']} (n={r['fav_band_n']})")
        print(f"{r['no']:>2} {r['mac'][:34]:<34} {r['lig']:<4} {oranstr:<20} {pstr:<20} "
              f"{r['fav'] or '—'!s:<4} {r['fav_band'] or '—'!s:<12} {bant_not}")

    print("\n─── 3. BU HAFTA ↔ GEÇEN SEZON ───────────────────────────────────────────")
    wa = h["weekly_avg"]
    print(f"{'':<26}{'bu hafta (piyasa)':>20}{'geçen sezon ort.':>20}")
    for s in SEMBOLLER:
        print(f"beklenen '{s}' adedi{'':<9}{prof['expected'][s]:>20.2f}{wa[s]:>20.2f}")
    print(f"favori dağılımı 1/0/2     {prof['fav_split']['1']:>8} / {prof['fav_split']['0']} / {prof['fav_split']['2']}"
          f"{'':>8}%{100*o['favourite_split']['1']/o['with_odds']:.0f} / 0 / %{100*o['favourite_split']['2']/o['with_odds']:.0f}")
    print(f"favori tutar (piyasa)     {prof['fav_expected_market']:>20.2f}")
    print(f"favori tutar (geç.sezon bantları){prof['fav_expected_history']:>13.2f}"
          f"{15*o['favourite_hit_pct']/100:>20.2f}  ← sezon ort. %{o['favourite_hit_pct']}")
    print(f"çift kapsar (piyasa)      {prof['double_expected_market']:>20.2f}")
    print(f"çift kapsar (geç.sezon)   {prof['double_expected_history']:>20.2f}")
    print(f"beraberlik (geç.sezon prof.){prof['draw_expected_history']:>18.2f}{wa['0']:>20.2f}")

    print("\nLig kırılımı (bu hafta → geçen sezon haftalık ortalaması):")
    for lig, n in sorted(prof["leagues"].items(), key=lambda kv: -kv[1]):
        gec = ref["lig"].get(lig)
        if gec:
            print(f"  {lig:<4} {n:>2} maç   ← geçen sezon {gec['per_week']}/hafta, "
                  f"beraberlik %{gec['draw_pct']}, favori %{gec['favourite_hit_pct']}")
        else:
            print(f"  {lig:<4} {n:>2} maç   ← geçen sezon arşivinde YOK (karşılaştırılamaz)")

    print("\n─── 4. KAMUOYU (oynanma) — geçen sezonda karşılığı YOK ──────────────────")
    print(f"{'#':>2} {'Maç':<32} {'oynanma 1/0/2':<16} {'piyasa 1/0/2':<16} {'fark (puan)':<18} kalabalık")
    for r in kam["rows"]:
        oy = "/".join(f"{100*r['cells'][s]['play']:.0f}" for s in SEMBOLLER)
        pi = "/".join(f"{100*r['cells'][s]['prob']:.0f}" for s in SEMBOLLER)
        fk = "/".join(f"{100*r['cells'][s]['diff']:+.0f}" for s in SEMBOLLER)
        print(f"{r['no']:>2} {r['mac'][:32]:<32} {oy:<16} {pi:<16} {fk:<18} "
              f"%{100*r['consensus']:.0f} → {r['max_play']}")
    tp, tm = kam["totals"]["play"], kam["totals"]["market"]
    print("\nSembol başına TOPLAM pay (15 maç):")
    for s in SEMBOLLER:
        print(f"  '{s}' → kamuoyu {tp[s]:.2f} maç · piyasa {tm[s]:.2f} maç · "
              f"fark {tp[s]-tm[s]:+.2f}")
    print(f"\nFavoriye ortalama fazla oynanma: {100*kam['avg_fav_diff']:+.1f} puan")
    print(f"%70+ mutabakat olan maç: {kam['consensus_70']}")
    print(f"Kamuoyu ile piyasanın AYRIŞTIĞI maçlar: {kam['public_vs_market_disagree'] or 'yok'}")

    for k in kuponlar:
        print(f"\n─── 5. KUPON · eşik {k['banko_esik']:.2f}/{k['uclu_esik']:.2f} ──────────────────────────────")
        print(f"İşaretler : {' '.join(k['picks'])}")
        print(f"Banko {len(k['banko'])} (maç {k['banko']}) · çift {len(k['cift'])} · üçlü {len(k['uclu'])} (maç {k['uclu']})")
        print(f"Seçim uzayı {k['space']:,} → kolon {k['columns']:,} · satır {k['rows']} · {k['engine']}")
        print(f"14-garanti: {'VAR' if k['guaranteed'] else 'YOK'} (koşul: sonuç seçim kümesinde)")
        print(f"Küme-içi olasılık: %{100*k['in_set_p']:.3f}  (≈ 1/{k['in_set_1_in']:,.0f})")
        print(f"Kalabalık-içi    : %{100*k['crowd_in_set_p']:.3f}  → oran "
              f"{k['crowd_ratio']:.2f} "
              f"({'küme olasılığına göre AZ oynanmış' if k['crowd_ratio'] > 1 else 'küme olasılığına göre FAZLA oynanmış'})")
        kalabalik_sirali = sorted(k["per_match_crowd"],
                                  key=lambda r: -(r["play_in"] - r["prob_in"]))
        print("En kalabalık üç işaretim (tutarsa ikramiye çok bölünür):")
        for r in kalabalik_sirali[:3]:
            print(f"  {r['no']:>2}. maç [{r['sec']}] halk %{100*r['play_in']:.0f} · "
                  f"piyasa %{100*r['prob_in']:.0f} · fark {100*(r['play_in']-r['prob_in']):+.0f} puan")
        print("Bütçe artarsa en verimli genişletme sırası:")
        for u in k["upgrades"]:
            print(f"  {u['no']:>2} {u['mac'][:34]:<34} +{u['ekle']}  küme ×{u['kume_carpani']:.2f}  "
                  f"bedel ×{u['bedel_carpani']:.2f}  verim {u['verim']:.2f}")


def kupon_satirlari(secimler: list[list[str]]) -> list[str]:
    """Seçimleri OYNANACAK satırlara çevirir — 16 satır, 14-garantili.

    Motorun kendi `solve_fix16` + `merge_rows` yolu; burada yeniden
    hesaplanan hiçbir şey yok, yalnızca insan okuyacak biçime dökülüyor.
    `merge_rows` her değişken maç için bir frozenset döndürür (birleşmiş
    satırda o maçta birden çok sembol işaretlidir).
    """
    enc = Encoder([list(x) for x in secimler])
    cols, _ = solve_fix16(enc)
    out = []
    for row in merge_rows(cols, attempts=4):
        hucreler = []
        j = 0
        for sec in secimler:
            if len(sec) == 1:
                hucreler.append(sec[0])
                continue
            syms = enc.variable_syms[j]
            idx = row[j]
            secili = sorted(idx) if not isinstance(idx, int) else [idx]
            hucreler.append("".join(syms[i] for i in secili))
            j += 1
        out.append(hucreler)
    return [" ".join(f"{c:<3}" for c in r) for r in out]


def yaz_merdiven(merdiven: list[dict[str, Any]]) -> None:
    print("\n─── 6. BÜTÇE MERDİVENİ (motorun bütçe danışmanı) ────────────────────────")
    print("Kolon bedeli bilinmiyor; tablo KOLON cinsindendir. Kısma sırasını")
    print("olasılık belirler — en düşük olasılıklı sembol önce düşer.")
    print(f"{'bütçe':>8} {'kolon':>7} {'satır':>6} {'küme-içi':>10} {'kalabalık':>10} {'oran':>6}  kısılan")
    for m in merdiven:
        if not m.get("cost"):
            print(f"{m['budget']:>8} {'—':>7}  plan yok (fix16 en az 7 çifte ister)")
            continue
        print(f"{m['budget']:>8} {m['cost']:>7,} {m['rows']:>6} "
              f"%{100*m['in_set_p']:>9.3f} %{100*m['crowd_in_set_p']:>9.3f} "
              f"{m['crowd_ratio']:>6.2f}  {'; '.join(m['changes']) or 'değişiklik yok'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--hafta", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    d = hafta_yukle(a.sezon, a.hafta)
    ref = gecen_sezon_ref()
    prof = hafta_profili(d, ref)
    kam = kamuoyu(d)
    kuponlar = [
        kupon_kur(d, VARSAYILAN_BANKO, VARSAYILAN_UCLU),
        kupon_kur(d, 0.68, 0.42),
    ]
    ana_secim = [list(x) for x in kuponlar[0]["picks"]]
    merdiven = butce_merdiveni(d, ana_secim, [128, 256, 512, 1024, 2304])

    if a.json:
        print(json.dumps({"meta": d["meta"], "profile": prof, "public": kam,
                          "coupons": kuponlar, "budget_ladder": merdiven},
                         ensure_ascii=False, indent=1))
    else:
        yaz(d, prof, kam, ref, kuponlar, merdiven)
        yaz_merdiven(merdiven)


if __name__ == "__main__":
    main()
