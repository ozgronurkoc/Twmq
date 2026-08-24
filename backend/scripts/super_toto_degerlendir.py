#!/usr/bin/env python3
"""Sonuçlar geldikten sonra: kupon ne yaptı, neden, ve kural değişmeli mi.

Bu script `super_toto_hafta.py`nin ikinci yarısıdır. O, sonuç görülmeden
kuponu kurar; bu, sonuç görüldükten sonra **aynı sayıları** hesabın
neresinde yanıldığımızı göstermek için kullanır.

Altı soruya cevap verir:

  1. Kupon kaç tutturdu, hangi maçlar küme dışında kaldı?
  2. Bu, şanssızlık mıydı yoksa kuralın yapısal açığı mı? (kaçak
     dağılımı — beklenen kaçak ve P(kaçak ≥ gerçekleşen))
  3. Aynı haftanın İKİ kaydı (`1. Tahmin` / `2. Tahmin`) ne yaptı, ve
     ikisinin BİRLEŞİMİ kaç tutturdu?
  4. Kalabalık ayarı ne kazandırdı, ne kaybettirdi? (yalnızca sembolü
     değişen maçlar — bedel sabit olduğu için kıyas dürüsttür)
  5. O hafta hangi görüş haklıydı: piyasa mı, DC mi, kalabalık mı? Ve
     ölçek (marj arındırma) seçimi sonucu değiştirdi mi?
  6. Gerçek kolon, olasılığa göre sıralamada kaçıncıydı — yani bu haftayı
     tutturmak KAÇ kolonluk bir bütçe isterdi?

    python scripts/super_toto_degerlendir.py --hafta 1
    python scripts/super_toto_degerlendir.py --hafta 2 --json

Sezon boyu birikimli defter ayrı bir betiktedir
(`scripts/super_toto_sezon.py`); eşik/kural taraması `spor_toto.backtest`
içinde yaşar ve geçen sezonun tamamını koşar. Bu betik **tek haftaya**
bakar ve bilerek öyle kalır.

UYARI: buradaki hiçbir sayı "şu kuralı değiştir" demez. Bir hafta 15
maçtır; 15 maçlık bir örneklem, peşinde olunan büyüklükteki bir farkı
hiçbir zaman ayırt edemez (bkz. `super_toto_sezon.py` yeterlilik notu).
Buradaki sayılar kuralın NE YAPTIĞINI gösterir, ne yapması gerektiğini
değil.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.core import SEMBOLLER
from spor_toto.ortak import kacak_dagilimi as ortak_kacak_dagilimi

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
SEM = SEMBOLLER


def _hafta_modulu():
    """Hafta betigi — artik siradan bir import (bkz. scripts/__init__.py)."""
    return importlib.import_module("scripts.super_toto_hafta")


#: Tam sayım için üst sınır. 16 satırlık kaplama kurulamadığında seçim
#: uzayının tamamı gezilir; 200 bin kolon 15 maçta saniyenin altındadır.
TAM_SAYIM_SINIRI = 200_000


def en_iyi_kolon(secimler: Sequence[Sequence[str]], gercek: str) -> int:
    """Oynanan kuponun EN İYİ kolonunun kaç doğru tutturduğu.

    Kolonları tek tek gezer; 15 maç ve en fazla ~30 bin kolonda bu
    milisaniyelerdir ve motorun kendi skorlayıcısına bağımlılık
    yaratmaz — sonuç kümenin dışındayken de doğru cevap verir.

    **Yedek yol neden var.** `solve_fix16` en az 7 çifte maç ister; altında
    `Fix16Hatasi` atar. Kural az çifte üretebilir (çok banko çıkan hafta) ve
    bu, marj arındırma `shin`e çevrildikten sonra **daha olası** hâle geldi —
    Shin favoriye daha çok pay verir, daha çok banko çıkar. Böyle bir haftada
    sonuç değerlendirmesinin çökmesi, ölçümün en çok gerektiği anda
    kaybolması olurdu. Kaplama kurulamıyorsa seçim uzayının tamamı gezilir;
    o uzay zaten küçüktür (az çifte = az kolon).
    """
    from itertools import product

    from spor_toto.core import Encoder, Fix16Hatasi, solve_fix16
    listeler = [list(x) for x in secimler]
    try:
        enc = Encoder(listeler)
        cols, _ = solve_fix16(enc)
    except Fix16Hatasi:
        uzay = 1
        for s in listeler:
            uzay *= len(s)
        if uzay > TAM_SAYIM_SINIRI:  # pragma: no cover - kuralin uretemedigi hal
            raise
        # Tam sayim: her kolon secim kumesinin bir noktasidir.
        return max(sum(1 for a, b in zip(kolon, gercek) if a == b)
                   for kolon in product(*listeler))

    en_iyi = 0
    for c in cols:
        skor = 0
        j = 0
        for i, s in enumerate(secimler):
            if len(s) == 1:
                skor += 1 if s[0] == gercek[i] else 0
            else:
                skor += 1 if enc.variable_syms[j][c[j]] == gercek[i] else 0
                j += 1
        if skor > en_iyi:
            en_iyi = skor
    return en_iyi


#: Poisson-binom `spor_toto.ortak`a taşındı: `spor_toto.secim` kuponu
#: KURARKEN aynı hesabı istiyor, bu betik ise onu DEĞERLENDİRİYOR. İki
#: gövde ayrışsaydı kuponu kuran hesap ile onu ölçen hesap farklı şeyler
#: söylerdi — ve bu, fark edilmesi en zor hata türüdür.
kacak_dagilimi = ortak_kacak_dagilimi


def kupon_degerlendir(d: dict[str, Any], picks: Sequence[str]) -> dict[str, Any]:
    gercek = d["meta"]["results"]
    maclar = d["matches"]
    kacaklar = [i + 1 for i, (p, g) in enumerate(zip(picks, gercek)) if g not in p]
    p_kacak = [1 - sum(mm["probs"][x] for x in pk) for mm, pk in zip(maclar, picks)]
    dist = kacak_dagilimi(p_kacak)
    n = len(kacaklar)
    return {
        "picks": list(picks),
        "misses": kacaklar,
        "miss_count": n,
        "best": en_iyi_kolon([list(x) for x in picks], gercek),
        "expected_misses": sum(p_kacak),
        "p_in_set": dist[0],
        "p_at_least_actual": sum(dist[n:]),
        "dist": dist,
        "per_match": [
            {"no": mm["no"], "mac": f"{mm['home']} – {mm['away']}", "pick": pk,
             "gercek": g, "tuttu": g in pk, "p_kacak": pk_,
             "atilan": [x for x in SEM if x not in pk],
             "p_atilan": {x: mm["probs"][x] for x in SEM if x not in pk}}
            for mm, pk, g, pk_ in zip(maclar, picks, gercek, p_kacak)
        ],
    }


def kupon_kiyas(d, a_picks, b_picks) -> dict[str, Any]:
    """İki kuponu maç maç karşılaştırır ve birleşimlerini ölçer.

    Birleşim kolonu bilerek var: "iki kupon birlikte oynansaydı" sorusu,
    haftanın ulaşılabilir olup olmadığını gösteren en dürüst testtir.
    """
    import math
    gercek = d["meta"]["results"]
    birlesim = ["".join(sorted(set(x) | set(y), key=SEM.index))
                for x, y in zip(a_picks, b_picks)]
    bk = [i + 1 for i, (p_, g) in enumerate(zip(birlesim, gercek)) if g not in p_]
    return {
        "union_picks": birlesim,
        "union_space": math.prod(len(x) for x in birlesim),
        "union_misses": bk,
        "union_best": 15 - len(bk),
        "rows": [
            {"no": i + 1, "mac": f"{mm['home']} – {mm['away']}",
             "a": x, "b": y, "gercek": g,
             "a_tuttu": g in x, "b_tuttu": g in y}
            for i, (mm, x, y, g) in enumerate(zip(d["matches"], a_picks, b_picks, gercek))
        ],
    }


def banko_karnesi(d, picks) -> dict[str, Any]:
    """Bankolar ne yaptı — tek işaretli maçlar kuponun kırılma noktasıdır."""
    gercek = d["meta"]["results"]
    sat = [{"no": i + 1, "mac": f"{d['matches'][i]['home']} – {d['matches'][i]['away']}",
            "sembol": p, "gercek": gercek[i], "tuttu": p == gercek[i],
            "p": d["matches"][i]["probs"][p]}
           for i, p in enumerate(picks) if len(p) == 1]
    return {"rows": sat, "n": len(sat),
            "dogru": sum(1 for r in sat if r["tuttu"]),
            "beklenen": sum(r["p"] for r in sat)}


def kalabalik_karnesi(d: dict[str, Any]) -> dict[str, Any]:
    """Kalabalığın kuponu ne yaptı — ikramiyenin neden büyük olduğunun cevabı."""
    gercek = d["meta"]["results"]
    maclar = d["matches"]
    halk = "".join(max(SEM, key=lambda s: mm["play"][s]) for mm in maclar)
    piyasa = "".join(mm["fav"] for mm in maclar)
    return {
        "halk_kuponu": halk,
        "halk_dogru": sum(1 for a, b in zip(halk, gercek) if a == b),
        "piyasa_kuponu": piyasa,
        "piyasa_dogru": sum(1 for a, b in zip(piyasa, gercek) if a == b),
        # Bağımsızlık varsayımıyla rastgele bir halk kuponunun beklenen
        # doğru sayısı: her maçta gerçek sonuca oynayanların payı.
        "beklenen_halk_dogru": sum(mm["play"][g] for mm, g in zip(maclar, gercek)),
        "beklenen_piyasa_dogru": sum(mm["probs"][g] for mm, g in zip(maclar, gercek)),
    }


#: İkramiyenin başladığı kademe. 15 maçlık kuponda 12 doğru ilk ödüllü
#: satırdır (1. haftanın ikramiye ekranı: 12 → 2.859 kişi). Kuponun hedefi
#: bu yüzden 14 değil 12'dir — 1. haftanın 1. dersi (docs §3.19).
HEDEF_KADEME = 12

#: 2. Tahmin kaydındaki planların KAYIT SIRASI. `taban` kuralın kendi
#: çıktısı, `ayarli` kalabalık ayarı uygulanmış hâli, `esik` ise aynı
#: haftada eski kuralın ne üreteceği. Üçü de aynı dosyada durur.
TAHMIN2_PLANLARI = ("taban", "ayarli", "esik")

#: Sıralama karşılaştırmasında log toplamlarını eşit sayma toleransı.
#: Oranı ilan edilmemiş maç 1/3–1/3–1/3 taşır ve o maçın üç dalı BİREBİR
#: aynı olasılıktadır; tolerans olmadan kayan nokta bu eşitliği rastgele
#: bozar ve sıra her koşumda oynardı.
SIRA_EPS = 1e-9


def tahmin2_yukle(sezon: str, hafta: int) -> dict[str, Any] | None:
    """Haftanın ikinci kaydı — yoksa `None`, ve bu bir hata değildir.

    2. Tahmin her haftada olmak zorunda değil: yalnızca kupon
    dondurulduktan SONRA projede bir şey değiştiyse kurulur (docs §3.37).
    """
    yol = (KOK / "data" / "super_toto" / sezon /
           f"hafta_{hafta:02d}_tahmin2.json")
    if not yol.exists():
        return None
    return json.loads(yol.read_text(encoding="utf-8"))


def tahmin2_degerlendir(d: dict[str, Any],
                        kayit: dict[str, Any]) -> list[dict[str, Any]]:
    """İkinci kaydın üç planını da puanlar — 1. Tahmin'le AYNI gövdeyle.

    Ayrı bir puanlayıcı yazmak, iki kaydı farklı hesapla ölçmek olurdu;
    o hâlde aradaki fark kupondan mı yöntemden mi geldiği bilinemezdi.
    """
    out = []
    for ad in TAHMIN2_PLANLARI:
        plan = kayit["kupon"].get(ad)
        if not plan:
            continue
        s = kupon_degerlendir(d, plan["picks"])
        s.update({
            "plan": ad,
            "columns": plan.get("columns"),
            "crowd_ratio": plan.get("crowd_ratio"),
            # Kupon KURULURKEN hesaplanmış hedef olasılığı. Sonuç
            # görülmeden yazıldığı için burada yeniden hesaplanmaz.
            "p_hedef_onceden": plan.get("p_hedef"),
            "hedefe_ulasti": s["best"] >= HEDEF_KADEME,
        })
        out.append(s)
    return out


def ayar_karnesi(d: dict[str, Any], kayit: dict[str, Any]) -> dict[str, Any]:
    """Kalabalık ayarı ne kazandırdı, ne kaybettirdi.

    Ayar işaret SAYILARINI değiştirmez (docs §3.34), yani taban ile ayarlı
    aynı bedeldedir. Kıyasın dürüst olmasının sebebi budur: iki plan aynı
    parayı ödedi, tek fark hangi sembolün işaretlendiği.

    **Parasal karşılığı burada ölçülemez.** Ayarın amacı isabet değil
    bölüşmedir; karşılığı ancak o haftanın ikramiye ekranı girilirse
    görünür (`meta.payout`). Bu karne yalnızca isabet tarafını sayar.
    """
    gercek = d["meta"]["results"]
    ayar = kayit["kupon"].get("ayar") or {}
    sat = []
    for x in ayar.get("degisimler", []):
        g = gercek[x["no"] - 1]
        t_tuttu, y_tuttu = g in x["taban"], g in x["yeni"]
        sat.append({
            "no": x["no"],
            "mac": f"{d['matches'][x['no'] - 1]['home']} – "
                   f"{d['matches'][x['no'] - 1]['away']}",
            "taban": x["taban"], "yeni": x["yeni"], "gercek": g,
            "taban_tuttu": t_tuttu, "yeni_tuttu": y_tuttu,
            "net": int(y_tuttu) - int(t_tuttu),
            "prob_bedeli": x["prob_taban"] - x["prob_yeni"],
            "oynanma_kazanci": x["oynanma_taban"] - x["oynanma_yeni"],
        })
    taban = kayit["kupon"].get("taban")
    ayarli = kayit["kupon"].get("ayarli")
    return {
        "rows": sat,
        "degisen": len(sat),
        "kazanilan": sum(1 for r in sat if r["net"] > 0),
        "kaybedilen": sum(1 for r in sat if r["net"] < 0),
        "net": sum(r["net"] for r in sat),
        "taban_best": (en_iyi_kolon([list(x) for x in taban["picks"]], gercek)
                       if taban else None),
        "ayarli_best": (en_iyi_kolon([list(x) for x in ayarli["picks"]], gercek)
                        if ayarli else None),
        "oran_taban": ayar.get("oran_taban"),
        "oran_ayarli": ayar.get("oran_ayarli"),
        "not": ("İsabet tarafı bu karnede; bölüşme tarafı ikramiye "
                "ekranı girilmeden ölçülemez."),
    }


def atilan_defteri(d: dict[str, Any], picks: Sequence[str]) -> dict[str, Any]:
    """Attığım semboller ne yaptı — sembol sembol, gözlenen ↔ beklenen.

    1. haftanın 2. dersi buradan çıkmıştı: geçen sezonun 567 maçında
    çiftede atılan sembol beraberlikse %25,8 geliyordu, ev sahibiyse
    %16,0, deplasmansa %15,6. O ders ARŞİVDEN geldi; bu defter aynı
    ölçüyü CANLI sezonda tutar.

    Beklenen sütunu neden var: "attığım beraberliklerin %38'i geldi"
    tek başına bir şey söylemez — piyasa zaten %23 diyorduysa fark
    2 maçtır ve gürültüdür. Karar veren sayı ikisinin arasıdır.
    """
    gercek = d["meta"]["results"]
    kayit: dict[str, dict[str, float]] = {
        s: {"atildi": 0, "geldi": 0, "beklenen": 0.0} for s in SEM}
    for mm, pk, g in zip(d["matches"], picks, gercek):
        for s in SEM:
            if s in pk:
                continue
            kayit[s]["atildi"] += 1
            kayit[s]["beklenen"] += mm["probs"][s]
            if g == s:
                kayit[s]["geldi"] += 1
    return {
        "sembol": kayit,
        "atildi": sum(v["atildi"] for v in kayit.values()),
        "geldi": sum(v["geldi"] for v in kayit.values()),
        "beklenen": sum(v["beklenen"] for v in kayit.values()),
    }


def gorus_karnesi(d: dict[str, Any],
                  kayit: dict[str, Any] | None) -> dict[str, Any] | None:
    """O hafta hangi görüş haklıydı: piyasa mı, DC mi, kalabalık mı?

    Yalnızca DC'si olan maçlarda ölçülür — eksik maçı 1/3 sayıp ortalamaya
    katmak, modeli bilgi taşımadığı yerde ödüllendirmek olurdu.

    Harman satırı bir KURAL DEĞİL, bir ÖLÇÜDÜR. Yığınlama geçen sezonun
    tamamında ölçüldü ve geçmedi (docs §3.32); burada durmasının tek
    sebebi, tek haftalık farkın büyüklüğünü görünür kılmak.
    """
    if not kayit:
        return None
    from spor_toto.evaluate import brier, log_kaybi

    gercek = d["meta"]["results"]
    satir = [(r, mm, g) for r, mm, g in zip(kayit["matches"], d["matches"], gercek)
             if r.get("dc")]
    if not satir:
        return None

    def olc(f) -> dict[str, float]:
        n = len(satir)
        return {"brier": sum(brier(f(r, mm), g) for r, mm, g in satir) / n,
                "log": sum(log_kaybi(f(r, mm), g) for r, mm, g in satir) / n}

    return {
        "n": len(satir),
        "kaynaklar": [
            {"ad": "piyasa", **olc(lambda r, mm: mm["probs"])},
            {"ad": "Dixon-Coles", **olc(lambda r, mm: r["dc"])},
            {"ad": "kalabalık", **olc(lambda r, mm: mm["play"])},
            {"ad": "yarı yarıya harman",
             **olc(lambda r, mm: {s: 0.5 * mm["probs"][s] + 0.5 * r["dc"][s]
                                  for s in SEM})},
        ],
        "not": ("Harman bir ölçüdür, kural değil; yığınlama arşivde "
                "ölçüldü ve geçmedi (docs §3.32)."),
    }


def olcek_karnesi(d: dict[str, Any]) -> dict[str, Any]:
    """Marj arındırma seçimi o hafta sonucu değiştirdi mi.

    Aynı oranlar, üç ölçek. Kupon 1. haftada `orantili`, 2. haftada
    `shin` ölçeğinde donduruldu (docs §3.18); bu karne, aradaki farkın
    haftanın skorunda görünür olup olmadığını söyler. Görünmüyorsa
    haftanın iyi ya da kötü gitmesi ölçek değişimine YAZILAMAZ.
    """
    from spor_toto.evaluate import brier, log_kaybi
    from spor_toto.odds import ARINDIRMA_VARSAYILAN, ARINDIRMA_YONTEMLERI, implied_probs

    gercek = d["meta"]["results"]
    satir = [(mm, g) for mm, g in zip(d["matches"], gercek) if not mm["odds_yok"]]
    out = []
    for y in ARINDIRMA_YONTEMLERI:
        p = [(implied_probs(mm["odds"], y), g) for mm, g in satir]
        out.append({"yontem": y, "varsayilan": y == ARINDIRMA_VARSAYILAN,
                    "brier": sum(brier(x, g) for x, g in p) / len(p),
                    "log": sum(log_kaybi(x, g) for x, g in p) / len(p)})
    return {"n": len(satir), "yontemler": out}


def _sira(dagilimlar: Sequence[dict[str, float]], gercek: str) -> int:
    """Gerçek kolonun olasılık sıralamasındaki yeri (1 = en olası kolon).

    3^15 = 14.348.907 kolonu tek tek gezmek gerekmiyor: maçlar bağımsız
    kabul edildiği için kolonun log-olasılığı maç log'larının toplamıdır.
    İlk yedi maçın bütün toplamları (3^7) ile kalan sekizinkiler (3^8)
    ayrı ayrı çıkarılır, biri sıralanır ve ikili arama ile eşiği geçen
    çiftler sayılır — 8.748 terim, milisaniyeler.
    """
    import bisect
    import math

    log = [[math.log(max(p[s], 1e-12)) for s in SEM] for p in dagilimlar]
    hedef = sum(satir[SEM.index(g)] for satir, g in zip(log, gercek))

    def tum(satirlar):
        out = [0.0]
        for satir in satirlar:
            out = [a + b for a in out for b in satir]
        return out

    yari = len(log) // 2
    a = sorted(tum(log[:yari]))
    ustunde = sum(len(a) - bisect.bisect_right(a, hedef - b + SIRA_EPS)
                  for b in tum(log[yari:]))
    return ustunde + 1


def gercegin_sirasi(d: dict[str, Any]) -> dict[str, Any]:
    """Bu haftayı tutturmak KAÇ kolonluk bir bütçe isterdi.

    En dürüst "kaçırdık mı, yoksa ulaşılamaz mıydı" testi. Bütün kolonlar
    olasılığa göre sıralansa, gerçek kolon kaçıncı sırada olurdu? Cevap
    aynı zamanda bir bütçedir: o sıraya kadar olan HER kolonu oynamak
    gerekirdi. Sayı on binleri geçiyorsa hafta, kupon kuralının değil,
    bütçenin dışındaydı.
    """
    import math

    gercek = d["meta"]["results"]
    piyasa = [mm["probs"] for mm in d["matches"]]
    kalabalik = [mm["play"] for mm in d["matches"]]
    return {
        "uzay": 3 ** len(gercek),
        "piyasa": {
            "p": math.prod(p[g] for p, g in zip(piyasa, gercek)),
            "sira": _sira(piyasa, gercek),
            "en_olasi_p": math.prod(max(p.values()) for p in piyasa),
        },
        "kalabalik": {
            "p": math.prod(p[g] for p, g in zip(kalabalik, gercek)),
            "sira": _sira(kalabalik, gercek),
            "en_olasi_p": math.prod(max(p.values()) for p in kalabalik),
        },
    }


def ikramiye_ozeti(d: dict[str, Any]) -> dict[str, Any]:
    pay = d["meta"].get("payout")
    if not pay:
        return {}
    katlar = []
    for t in pay["tiers"]:
        if t.get("prize") is None:
            katlar.append({**t, "toplam": None})
        else:
            katlar.append({**t, "toplam": t["winners"] * t["prize"]})
    return {"tiers": katlar, "currency": pay.get("currency", "TRY")}


def rapor(sezon: str, hafta: int) -> dict[str, Any]:
    """Haftanın bütün değerlendirme gövdesi — tek yerde toplanır.

    Metin ve JSON çıktıları AYNI gövdeyi okur. Ayrı toplanan iki çıktı,
    biri güncellenip öteki unutulduğunda sessizce ayrışır; bu betiğin işi
    tam olarak böyle sessiz ayrışmaları yakalamak.
    """
    m = _hafta_modulu()
    d = m.hafta_yukle(sezon, hafta)
    if not d["meta"].get("results"):
        raise SystemExit("Bu haftanın sonucu henüz girilmemiş.")

    kupon_yolu = (KOK / "data" / "super_toto" / sezon /
                  f"hafta_{hafta:02d}_kupon.json")
    kupon = json.loads(kupon_yolu.read_text(encoding="utf-8"))
    sonuclar = [kupon_degerlendir(d, v["picks"]) for v in kupon["variants"]]
    for v, s in zip(kupon["variants"], sonuclar):
        s["label"] = v.get("label")
        s["columns"] = v.get("columns")
        s["hedefe_ulasti"] = s["best"] >= HEDEF_KADEME

    kayit = tahmin2_yukle(sezon, hafta)
    ikinci = tahmin2_degerlendir(d, kayit) if kayit else []
    # Kiyas ANA kupon ile AYARLI plan arasinda: ikisi de o kaydin "oynanacak"
    # plani. Taban ve esik ayni dosyada duruyor ama onlar ara olcumdur.
    ayarli = next((x for x in ikinci if x["plan"] == "ayarli"), None)
    return {
        "sezon": sezon, "hafta": hafta,
        "results": d["meta"]["results"],
        "results_source": d["meta"].get("results_source"),
        "coupons": sonuclar,
        "tahmin2": ikinci,
        "tahmin2_meta": ({"ad": kayit["meta"]["ad"],
                          "frozen_at": kayit["meta"]["frozen_at"],
                          "kural": kayit["meta"]["kural"],
                          "arindirma": kayit["meta"]["arindirma"]}
                         if kayit else None),
        "kiyas": (kupon_kiyas(d, sonuclar[0]["picks"], ayarli["picks"])
                  if ayarli else None),
        "ayar": ayar_karnesi(d, kayit) if kayit else None,
        "banko": {"birinci": banko_karnesi(d, sonuclar[0]["picks"]),
                  "ikinci": (banko_karnesi(d, ayarli["picks"])
                             if ayarli else None)},
        "atilan": {"birinci": atilan_defteri(d, sonuclar[0]["picks"]),
                   "ikinci": (atilan_defteri(d, ayarli["picks"])
                              if ayarli else None)},
        "gorus": gorus_karnesi(d, kayit),
        "olcek": olcek_karnesi(d),
        "sira": gercegin_sirasi(d),
        "crowd": kalabalik_karnesi(d),
        "payout": ikramiye_ozeti(d),
        "payout_note": d["meta"].get("payout_note"),
        "_d": d,
    }


def _basli(ad: str) -> None:
    print(f"\n─── {ad} " + "─" * max(0, 70 - len(ad)))


def _kupon_satiri(s: dict[str, Any], ad: str) -> None:
    kolon = f"{s['columns']:,} kolon · " if s.get("columns") else ""
    print(f"\n─── {ad}")
    print(f"  İşaret : {' '.join(s['picks'])}")
    print(f"  Kaçak  : {s['misses']} ({s['miss_count']} maç)")
    print(f"  EN İYİ KOLON: {s['best']}/15 · {kolon}"
          f"{'İKRAMİYE KADEMESİNDE' if s['hedefe_ulasti'] else 'kademe dışı'}")
    print(f"  Beklenen kaçak {s['expected_misses']:.2f} · küme-içi %{100*s['p_in_set']:.2f} · "
          f"P(kaçak ≥ {s['miss_count']}) = %{100*s['p_at_least_actual']:.1f}")


def yaz(o: dict[str, Any]) -> None:
    d = o["_d"]
    meta = d["meta"]
    gercek = o["results"]
    sayim = {s: gercek.count(s) for s in SEM}
    print(f"\n{'='*78}\n{meta['season']} · {meta['week']}. HAFTA — SONUÇ DEĞERLENDİRMESİ\n{'='*78}")
    print(f"Gerçek dizi : {' '.join(gercek)}")
    print(f"Sayım 1/0/2 : {sayim['1']} / {sayim['0']} / {sayim['2']}")
    print(f"İkramiye kademesi: {HEDEF_KADEME}+ doğru")

    print("\n█ 1. TAHMİN (dondurulmuş kupon)")
    for s in o["coupons"]:
        _kupon_satiri(s, s["label"] or "ana")

    if o["tahmin2"]:
        t = o["tahmin2_meta"]
        print(f"\n█ {t['ad']} — {t['frozen_at']} · kural {t['kural']} · "
              f"ölçek {t['arindirma']}")
        for s in o["tahmin2"]:
            _kupon_satiri(s, f"{s['plan']}")

    ana = o["coupons"][0]
    _basli("MAÇ MAÇ (1. Tahmin ana kupon)")
    for r in ana["per_match"]:
        im = "✓" if r["tuttu"] else "✗"
        at = ", ".join(f"{x}=%{100*r['p_atilan'][x]:.0f}" for x in r["atilan"]) or "—"
        print(f"  {im} {r['no']:>2} {r['mac'][:34]:<34} işaret [{r['pick']:<3}] "
              f"gerçek {r['gercek']} · attığım: {at}")

    if o["kiyas"]:
        k = o["kiyas"]
        _basli("İKİ KAYIT YAN YANA (1. Tahmin ana ↔ 2. Tahmin ayarlı)")
        for r in k["rows"]:
            a = "✓" if r["a_tuttu"] else "✗"
            b = "✓" if r["b_tuttu"] else "✗"
            fark = "  ← işaret farklı" if r["a"] != r["b"] else ""
            print(f"  {r['no']:>2} {r['mac'][:30]:<30} 1.T [{r['a']:<3}]{a}   "
                  f"2.T [{r['b']:<3}]{b}   gerçek {r['gercek']}{fark}")
        print(f"  BİRLEŞİM: {k['union_best']}/15 · kaçak {k['union_misses']} · "
              f"{k['union_space']:,} kolonluk uzay")
        print("  (Birleşim 'ikisini birden oynasaydık' sorusudur — haftanın "
              "ulaşılabilirliğini gösterir, oynanmış bir kupon değildir.)")

    if o["ayar"]:
        a = o["ayar"]
        _basli("KALABALIK AYARI KARNESİ")
        for r in a["rows"]:
            im = {1: "kazandı", 0: "değişmedi", -1: "kaybetti"}[r["net"]]
            print(f"  {r['no']:>2} {r['mac'][:30]:<30} [{r['taban']:<3}]→[{r['yeni']:<3}] "
                  f"gerçek {r['gercek']} · {im} "
                  f"(olasılıktan −{100*r['prob_bedeli']:.1f} puan, "
                  f"oynanmadan −{100*r['oynanma_kazanci']:.0f} puan)")
        print(f"  Net: {a['kazanilan']} kazanç / {a['kaybedilen']} kayıp "
              f"= {a['net']:+d} maç · taban {a['taban_best']}/15 ↔ "
              f"ayarlı {a['ayarli_best']}/15")
        print(f"  {a['not']}")

    _basli("BANKO KARNESİ")
    for ad, b in (("1. Tahmin", o["banko"]["birinci"]),
                  ("2. Tahmin", o["banko"]["ikinci"])):
        if b is None:
            continue
        if not b["n"]:
            print(f"  {ad}: banko yok")
            continue
        print(f"  {ad}: {b['dogru']}/{b['n']} tuttu · beklenen {b['beklenen']:.2f}")
        for r in b["rows"]:
            im = "✓" if r["tuttu"] else "✗"
            print(f"     {im} {r['no']:>2} {r['mac'][:32]:<32} [{r['sembol']}] "
                  f"gerçek {r['gercek']} · p=%{100*r['p']:.0f}")

    _basli("ATILAN SEMBOL DEFTERİ")
    for ad, t in (("1. Tahmin", o["atilan"]["birinci"]),
                  ("2. Tahmin", o["atilan"]["ikinci"])):
        if t is None:
            continue
        parca = " · ".join(
            f"{s}: {t['sembol'][s]['geldi']}/{t['sembol'][s]['atildi']} "
            f"(bekl. {t['sembol'][s]['beklenen']:.1f})" for s in SEM)
        print(f"  {ad}: {parca}")
    print("  Okuma: gözlenen ile beklenen ARASINDAKİ fark bilgi taşır; "
          "ham oran taşımaz.")

    if o["gorus"]:
        g = o["gorus"]
        _basli(f"GÖRÜŞ KARNESİ ({g['n']} maç — DC'si olanlar)")
        for k in g["kaynaklar"]:
            print(f"  {k['ad']:<20} Brier {k['brier']:.4f} · log {k['log']:.4f}")
        print(f"  {g['not']}")

    ol = o["olcek"]
    _basli(f"ÖLÇEK KARNESİ ({ol['n']} maç — marj arındırma)")
    for y in ol["yontemler"]:
        im = "  ← varsayılan" if y["varsayilan"] else ""
        print(f"  {y['yontem']:<10} Brier {y['brier']:.4f} · log {y['log']:.4f}{im}")

    sr = o["sira"]
    _basli("GERÇEĞİN SIRASI — bu haftayı tutturmak kaç kolon isterdi")
    for ad, x in (("piyasa", sr["piyasa"]), ("kalabalık", sr["kalabalik"])):
        print(f"  {ad:<10} gerçek kolonun olasılığı {x['p']:.3e} · sıra "
              f"{x['sira']:,} / {sr['uzay']:,}")
    print("  (Sıra = olasılığa göre dizilmiş kolonların kaçıncısı. Aynı "
          "zamanda bir bütçedir: o kadar kolon oynamak gerekirdi.)")

    kal = o["crowd"]
    _basli("KALABALIK KARNESİ")
    print(f"  Halkın en çok oynadığı kupon : {kal['halk_kuponu']} → {kal['halk_dogru']}/15 doğru")
    print(f"  Piyasanın favori kuponu      : {kal['piyasa_kuponu']} → {kal['piyasa_dogru']}/15 doğru")
    print(f"  Rastgele bir halk kuponunun beklenen doğrusu : {kal['beklenen_halk_dogru']:.2f}")
    print(f"  Piyasa olasılıklarının beklediği doğru       : {kal['beklenen_piyasa_dogru']:.2f}")

    if o["payout"]:
        _basli("İKRAMİYE")
        for t in o["payout"]["tiers"]:
            if t["prize"] is None:
                print(f"  {t['correct']} bilen: çıkmadı · {t.get('rollover', 0):,.2f} TL devretti")
            else:
                print(f"  {t['correct']} bilen: {t['winners']:>5} kişi × {t['prize']:>12,.2f} TL "
                      f"= {t['toplam']:>15,.2f} TL")
    elif o["payout_note"]:
        _basli("İKRAMİYE")
        print(f"  {o['payout_note']}")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--hafta", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    o = rapor(a.sezon, a.hafta)
    if a.json:
        # `_d` ham hafta gövdesidir ve JSON'a girmez: 15 maçın tamamını
        # ikinci kez yazmak, beslemeyi okuyan tarafta hangi kopyanın
        # doğru olduğu sorusunu doğururdu.
        print(json.dumps({k: v for k, v in o.items() if k != "_d"},
                         ensure_ascii=False, indent=1))
    else:
        yaz(o)


if __name__ == "__main__":
    main()
