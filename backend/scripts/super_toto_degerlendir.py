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
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.core import SEMBOLLER
from spor_toto.getiri import KOLON_BEDELI, KOLON_BEDELI_KAYNAGI
from spor_toto.ortak import kacak_dagilimi as ortak_kacak_dagilimi

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
SEM = SEMBOLLER

#: Kisa ad — bu dosyada carpim cok geciyor.
math_prod = math.prod


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


#: Bir kuponun OYNANMA biçimi — puanlama bundan değişir.
#:
#: `fix16`: 16 satırlık kaplama. Seçim uzayının tamamı değil, 14 garantisi
#: veren bir alt kümesi oynanır; küme içindeyken en iyi kolon 14'tür, 15
#: ancak şans eseri gelir.
#:
#: `tam`: seçim uzayının tamamı (uzay kadar kolon). Her kaçak birebir bir
#: puan götürür ve küme içindeyken sonuç 15'tir.
#:
#: Ayrım kozmetik değil: **aynı işaretler iki biçimde farklı puan alır.**
#: 2. haftanın 15 bilen kuponu tam sistemdi; aynı işaretler 16 satırda
#: 14 verirdi (ve 8 kat ucuza gelirdi).
SISTEMLER = ("fix16", "tam")


def kupon_degerlendir(d: dict[str, Any], picks: Sequence[str],
                      sistem: str = "fix16") -> dict[str, Any]:
    if sistem not in SISTEMLER:
        raise SystemExit(f"bilinmeyen sistem: {sistem} ({', '.join(SISTEMLER)})")
    gercek = d["meta"]["results"]
    maclar = d["matches"]
    kacaklar = [i + 1 for i, (p, g) in enumerate(zip(picks, gercek)) if g not in p]
    p_kacak = [1 - sum(mm["probs"][x] for x in pk) for mm, pk in zip(maclar, picks)]
    dist = kacak_dagilimi(p_kacak)
    n = len(kacaklar)
    return {
        "picks": list(picks),
        "sistem": sistem,
        "misses": kacaklar,
        "miss_count": n,
        "best": (len(gercek) - n if sistem == "tam"
                 else en_iyi_kolon([list(x) for x in picks], gercek)),
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
        #
        # `math.fsum`, `sum` DEĞİL — ve fark bu depoda ÖLÇÜLDÜ. CPython
        # 3.12 gömülü `sum()`ı float'lar için Neumaier telafili toplamaya
        # çevirdi; aynı girdi 3.10/3.11'de `5.890000000000001`, 3.12/3.13'te
        # `5.89` veriyor. İkisi de "doğru" ama bu değer SÜRÜMLENMİŞ bir
        # üretilmiş dosyaya (`frontend/lib/super-toto-veri.json`) yazılıyor
        # ve o dosyanın tazeliğini bayt eşitliğiyle denetleyen iki bekçi var
        # (`super_toto_frontend.py --kontrol` ve
        # `test_besleme_dosyasi_guncel`). Sonuç: dosyayı hangi yorumlayıcının
        # ürettiği bayt düzeyinde görünür oluyordu ve CI'nın py3.12 ile
        # py3.13 bacakları AYLARDIR bu yüzden kırmızıydı — kod değişmeden.
        #
        # `math.fsum` DOĞRU YUVARLANMIŞ sonucu verir, yani her CPython
        # sürümünde aynıdır. Üretilmiş dosya böylece yorumlayıcıdan
        # bağımsızlaşır; n=15'te maliyeti ölçülemez.
        "beklenen_halk_dogru": math.fsum(mm["play"][g] for mm, g in zip(maclar, gercek)),
        "beklenen_piyasa_dogru": math.fsum(mm["probs"][g] for mm, g in zip(maclar, gercek)),
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


def oynanan_kolonlar(d: dict[str, Any], picks: Sequence[str],
                     sistem: str = "fix16") -> dict[str, Any]:
    """OYNANAN kolonların toplam olasılığı — yani **P(15)**.

    Küme-içi olasılıkla karıştırılmamalı: küme-içi, gerçeğin seçim
    kümesinde kalma olasılığıdır. 16 satırlık kaplamada küme içinde
    kalmak 15 demek DEĞİLDİR, çünkü kümenin yalnızca bir dilimi oynanır.
    Bu fonksiyon o dilimin gerçek olasılığını, kolonları tek tek gezerek
    toplar.

    Tam sistemde dilim kümenin kendisidir ve sayı küme-içiye eşit çıkar;
    fonksiyon yine de aynı yoldan hesaplar, çünkü iki sayının eşitliği
    **sonuç**tur, varsayım değil.
    """
    from spor_toto.core import Encoder, Fix16Hatasi, solve_fix16

    listeler = [list(x) for x in picks]
    maclar = d["matches"]
    if sistem == "tam":
        from itertools import product
        toplam = sum(
            math_prod(mm["probs"][s] for mm, s in zip(maclar, kolon))
            for kolon in product(*listeler))
        return {"p15": toplam, "kolon": math_prod(len(x) for x in listeler)}

    enc = Encoder(listeler)
    try:
        cols, _ = solve_fix16(enc)
    except Fix16Hatasi:  # pragma: no cover - kuralin uretemedigi hal
        return {"p15": None, "kolon": None}
    toplam = 0.0
    for c in cols:
        p, j = 1.0, 0
        for i, sec in enumerate(listeler):
            sembol = sec[0] if len(sec) == 1 else enc.variable_syms[j][c[j]]
            if len(sec) > 1:
                j += 1
            p *= maclar[i]["probs"][sembol]
        toplam += p
    return {"p15": toplam, "kolon": len(cols)}


def plan_karnesi(d: dict[str, Any], picks: Sequence[str],
                 sistem: str = "fix16", ad: str = "") -> dict[str, Any]:
    """Bir kuponun tek satırlık karnesi — **iki sistemi kıyaslanabilir kılar.**

    Kademe olasılıkları sistemden okunur: 16 satırlık kaplamada küme içi
    kalmak 14 verir (`P(≥14) = P(k=0)`), tam sistemde 15 verir
    (`P(≥14) = P(k ≤ 1)`). Aynı dağılımı iki sistemde aynı sütuna yazmak,
    8 kat pahalı bir kuponu ucuz olanla eşit göstermek olurdu.
    """
    s = kupon_degerlendir(d, picks, sistem)
    dist = s["dist"]
    kaydir = 1 if sistem == "tam" else 0
    kume = math_prod(sum(mm["probs"][x] for x in pk)
                     for mm, pk in zip(d["matches"], picks))
    kalabalik = math_prod(sum(mm["play"][x] for x in pk)
                          for mm, pk in zip(d["matches"], picks))
    oynanan = oynanan_kolonlar(d, picks, sistem)
    return {
        "ad": ad, "sistem": sistem, "picks": list(picks),
        "banko": sum(1 for x in picks if len(x) == 1),
        "cift": sum(1 for x in picks if len(x) == 2),
        "uclu": sum(1 for x in picks if len(x) == 3),
        "uzay": math_prod(len(x) for x in picks),
        "kolon": oynanan["kolon"],
        "p15": oynanan["p15"],
        "p14": sum(dist[:1 + kaydir]),
        "p13": sum(dist[:2 + kaydir]),
        "p12": sum(dist[:3 + kaydir]),
        "kume_ici": kume,
        "kalabalik_ici": kalabalik,
        "oran": (kume / kalabalik) if kalabalik else None,
        "best": s["best"], "misses": s["misses"],
        "getiri": getiri_karnesi(d, picks, sistem),
    }


def sapma_defteri(d: dict[str, Any], picks: Sequence[str]) -> dict[str, Any]:
    """**Azami kapsamadan** sapmalar: nerede, ne pahasına, ödedi mi.

    Mekanik referans, her maçta en olası `k` sembolü işaretlemektir; kural
    da bunu yapar. Bir kupon o seçimden saptığında bir *görüş* beyan
    etmiştir: kapsamadan puan verip başka bir sembol tutmuştur.

    Defter üç şeyi ayırır ve üçü de gerekli:

    * **kazanç** — attığı yerine tuttuğu sembol geldi (sapma kurtardı),
    * **kayıp** — tuttuğu yerine attığı sembol geldi (sapma batırdı),
    * **beklenen** — piyasanın aynı sapmalara verdiği olasılık.

    Karar sayısı `p_net`: piyasanın kendi olasılıklarıyla, bu kadar iyi
    ya da daha iyi bir netin ortaya çıkma olasılığı. Küçükse ya görüş
    vardır ya da o hafta şanslıdır — **tek hafta ikisini ayıramaz**, ve
    defter bu yüzden hafta hafta birikmek üzere yazılmıştır.
    """
    gercek = d["meta"]["results"]
    satir = []
    for mm, pk, g in zip(d["matches"], picks, gercek):
        k = len(pk)
        sirali = sorted(SEM, key=lambda x: -mm["probs"][x])
        azami = set(sirali[:k])
        if set(pk) == azami:
            continue
        fazla = [x for x in pk if x not in azami]
        eksik = [x for x in azami if x not in pk]
        satir.append({
            "no": mm["no"], "mac": f"{mm['home']} – {mm['away']}",
            "pick": pk, "azami": "".join(sorted(azami, key=SEM.index)),
            "gercek": g,
            "tuttugu": fazla, "attigi": eksik,
            "p_tuttugu": sum(mm["probs"][x] for x in fazla),
            "p_attigi": sum(mm["probs"][x] for x in eksik),
            "kapsama_bedeli": (sum(mm["probs"][x] for x in azami)
                               - sum(mm["probs"][x] for x in pk)),
            "kazandi": g in fazla,
            "kaybetti": g in eksik,
        })

    # (kazanç, kayıp) ortak dağılımı — maçlar bağımsız kabul edilir, aynı
    # varsayım kaçak dağılımında da geçerli (`spor_toto.ortak`).
    dag: dict[tuple[int, int], float] = {(0, 0): 1.0}
    for r in satir:
        yeni: dict[tuple[int, int], float] = {}
        for (a, b), pr in dag.items():
            yeni[(a + 1, b)] = yeni.get((a + 1, b), 0.0) + pr * r["p_tuttugu"]
            yeni[(a, b + 1)] = yeni.get((a, b + 1), 0.0) + pr * r["p_attigi"]
            kalan = 1 - r["p_tuttugu"] - r["p_attigi"]
            yeni[(a, b)] = yeni.get((a, b), 0.0) + pr * kalan
        dag = yeni
    kazanc = sum(1 for r in satir if r["kazandi"])
    kayip = sum(1 for r in satir if r["kaybetti"])
    net = kazanc - kayip
    return {
        "rows": satir,
        "sapma": len(satir),
        "kazanc": kazanc, "kayip": kayip, "net": net,
        "beklenen_kazanc": sum(r["p_tuttugu"] for r in satir),
        "beklenen_kayip": sum(r["p_attigi"] for r in satir),
        "beklenen_net": sum(r["p_tuttugu"] - r["p_attigi"] for r in satir),
        "kapsama_bedeli": sum(r["kapsama_bedeli"] for r in satir),
        "p_net": sum(pr for (a, b), pr in dag.items() if a - b >= net),
    }


def oynanan_kolon_listesi(d: dict[str, Any], picks: Sequence[str],
                          sistem: str = "fix16") -> list[tuple[str, ...]]:
    """Gerçekten oynanan kolonların kendisi — sembol sembol.

    `oynanan_kolonlar` bu listenin olasılık toplamını verir; getiri hesabı
    ise kolonların **tek tek** kaç tutturduğunu ister, çünkü müşterek havuz
    kolon başına bölünür. Tek bir sistem kuponu aynı hafta hem 15 hem 14
    hem 13 kazanabilir ve bu, kupon bedelinin karşılığının tamamıdır.
    """
    from itertools import product

    from spor_toto.core import Encoder, Fix16Hatasi, solve_fix16

    listeler = [list(x) for x in picks]
    if sistem == "tam":
        return list(product(*listeler))
    enc = Encoder(listeler)
    try:
        cols, _ = solve_fix16(enc)
    except Fix16Hatasi:  # pragma: no cover - kuralin uretemedigi hal
        return []
    out = []
    for c in cols:
        kolon, j = [], 0
        for sec in listeler:
            if len(sec) == 1:
                kolon.append(sec[0])
            else:
                kolon.append(enc.variable_syms[j][c[j]])
                j += 1
        out.append(tuple(kolon))
    return out


def getiri_karnesi(d: dict[str, Any], picks: Sequence[str],
                   sistem: str = "fix16") -> dict[str, Any] | None:
    """Kuponun **gerçekleşen** ve **beklenen** getirisi — ikramiye tablosundan.

    Projede ilk kez para birimli bir sayı ölçümden geliyor: ikramiye ekranı
    girilmişse kademe ödülleri bilinir ve kuponun her kolonu tek tek
    puanlanabilir. İki sayı birden yazılır ve ikisi farklı soruya cevap
    verir:

    * **gerçekleşen** — bu hafta ne kazandı. Tek hafta, tek örneklem.
    * **beklenen** — AYNI ödül vektörüyle, sonuç görülmeden önceki
      beklenti. `E[k tutturan kolon sayısı] × ödül(k)` toplamı. Kuponları
      kıyaslamanın dürüst yolu budur; gerçekleşen sayı haftanın kendi
      gürültüsünü taşır.

    **Başabaş kolon bedeli** ikisinin de yanında durur: kolon fiyatı
    hiçbir ekranda yayınlanmadığı için getiri mutlak olarak değil, "kolon
    başına şu fiyatın altındaysa kâr" biçiminde okunur.

    Getiri **kolon başına doğrusaldır** — bu, sistem seçiminin (kaplama mı
    tam sistem mi) beklenen getiriyi DEĞİŞTİRMEDİĞİ anlamına gelir; yalnız
    dağılımını değiştirir. Ölçüm bunu doğruluyor (docs §3.40).
    """
    pay = d["meta"].get("payout")
    if not pay:
        return None
    odul = {t["correct"]: t["prize"] for t in pay["tiers"]
            if t.get("prize") is not None}
    if not odul:
        return None
    gercek = d["meta"]["results"]
    maclar = d["matches"]
    kolonlar = oynanan_kolon_listesi(d, picks, sistem)
    if not kolonlar:
        return None

    dagilim: dict[int, int] = {}
    beklenen = [0.0] * (len(gercek) + 1)
    for kolon in kolonlar:
        k = sum(1 for a, b in zip(kolon, gercek) if a == b)
        dagilim[k] = dagilim.get(k, 0) + 1
        # Bu kolonun kac tutturacaginin dagilimi (Poisson-binom).
        dp = [1.0]
        for mm, s in zip(maclar, kolon):
            q = mm["probs"][s]
            yeni = [0.0] * (len(dp) + 1)
            for i, v in enumerate(dp):
                yeni[i] += v * (1 - q)
                yeni[i + 1] += v * q
            dp = yeni
        for i, v in enumerate(dp):
            beklenen[i] += v

    n = len(kolonlar)
    ger = sum(adet * odul[k] for k, adet in dagilim.items() if k in odul)
    bek = sum(beklenen[k] * odul[k] for k in odul)
    # Kolon bedeli 3. haftada olculdu (`getiri.KOLON_BEDELI`, DIS KAYIT):
    # basabas fiyatin yaninda artik kar/zarar da yazilabiliyor. Basabas
    # satiri KALDIRILMADI — bedelin kaynagi disaridir ve dogrulanirsa da
    # degisebilir; iki sayi yan yana durur.
    mal = n * KOLON_BEDELI
    return {
        "sistem": sistem, "kolon": n,
        "kazanan_kolon": {k: dagilim[k] for k in sorted(dagilim, reverse=True)
                          if k in odul},
        "gerceklesen": ger, "gerceklesen_kolon_basi": ger / n,
        "beklenen": bek, "beklenen_kolon_basi": bek / n,
        "beklenen_kazanan": {k: beklenen[k] for k in sorted(odul, reverse=True)},
        "kolon_bedeli": KOLON_BEDELI, "maliyet": mal,
        "net": ger - mal, "roi": ger / mal,
        "beklenen_net": bek - mal, "beklenen_roi": bek / mal,
        "bedel_kaynagi": KOLON_BEDELI_KAYNAGI,
        "not": ("Ödül vektörü bu haftanınkidir ve SABİT alınmıştır; gerçekte "
                "haftadan haftaya değişir. Kolon bedeli yayınlanmadığı için "
                "getiri başabaş fiyat olarak okunur."),
    }


def havuz_karnesi(d: dict[str, Any]) -> dict[str, Any] | None:
    """İkramiye tablosu, kalabalık modelini **sınayan** ilk ölçüm.

    `VERI_TOPLAMA_VE_ISLEME.md` §B2 testi tam olarak şuydu: *oynanma payı +
    gerçekleşen sonuç, kazanan adetlerini önceden söyleyebilmelidir.*
    Artık söyleyip söylemediğine bakılabilir.

    Her kademe için bağımsız-kolon modeliyle `P(k doğru)` hesaplanır ve
    gözlenen kazanan sayısı ona bölünür: sonuç, o kademenin ima ettiği
    **havuzdaki kolon sayısı**. Model doğruysa dört kademe aynı sayıyı
    vermeli — kademeler arası tutarlılık, modelin ŞEKLİNİ sınar.

    İki model yan yana koşar (kalabalık ve piyasa) çünkü hangisinin
    kazanan adetlerini daha iyi ürettiği, havuz ekseninin tamamının
    dayandığı sorudur.

    **Kademe havuzu** ayrıca yazılır: kazanan kolon × ödül. İki haftada da
    14'e oranı 1,75 : 1 : 1 : 1,25 çıktı ve bu artık `getiri.OLCULEN_PAY`.
    """
    pay = d["meta"].get("payout")
    if not pay:
        return None
    gercek = d["meta"]["results"]

    def dagilim(kaynak: str) -> list[float]:
        dp = [1.0]
        for mm, x in zip(d["matches"], gercek):
            q = mm[kaynak][x]
            yeni = [0.0] * (len(dp) + 1)
            for i, v in enumerate(dp):
                yeni[i] += v * (1 - q)
                yeni[i + 1] += v * q
            dp = yeni
        return dp

    kalabalik, piyasa = dagilim("play"), dagilim("probs")
    satir = []
    for t in pay["tiers"]:
        k, kazanan = t["correct"], t["winners"]
        if not kazanan:
            continue
        havuz = kazanan * t["prize"] if t.get("prize") is not None else None
        satir.append({
            "kademe": k, "kazanan": kazanan, "odul": t.get("prize"),
            "kademe_havuzu": havuz,
            "p_kalabalik": kalabalik[k], "p_piyasa": piyasa[k],
            "n_kalabalik": kazanan / kalabalik[k] if kalabalik[k] else None,
            "n_piyasa": kazanan / piyasa[k] if piyasa[k] else None,
        })
    return {"rows": satir, "not": (
        "14-13-12 kademelerinde kazanan sayıları KİŞİ değil KOLONdur: tek "
        "bir sistem kuponu aynı hafta onlarca kolonla kazanabilir. "
        "Bağımsız-kolon modeli bu ilişkiyi göremez ve seviye tahmini bu "
        "yüzden şişer. 15 kademesi İSTİSNADIR: bir kuponun en fazla BİR "
        "kolonu on beşi birden tutturabilir (iki kolon tanım gereği en az "
        "bir maçta ayrışır), dolayısıyla 15 bilen adedi doğrudan KUPON "
        "sayar. 3. haftanın dört 15 bileni bunu gösteriyor — 400 ve 3.975 "
        "kolonluk kuponlar da dahil, dördü de tam 1 (docs §3.48).")}


def kayitli_karne(d: dict[str, Any], r: dict[str, Any]) -> dict[str, Any]:
    """Kolon LİSTESİ elimizde olmayan dış kuponun karnesi.

    3. haftanın dört 15 bileni indirgenmiş sistemlerdir: hangi kolonların
    oynandığı ekranda yok, ama **kaç kolon oynandığı** ve **her kademede
    kaç kolon kazandığı** yazıyor. Bu, modellemekten iyidir — kademe
    dağılımı burada varsayım değil **kayıt**tır.

    O yüzden bu karne `plan_karnesi`den ayrı durur: oradaki `p14/p13/p12`
    ve `kazanan_kolon` bir kaplama modelinden türer ve indirgenmiş bir
    sisteme uymaz; 8 kat pahalı bir kuponu ucuz göstermenin aynası, burada
    kolonları YANLIŞ SAYMAK olurdu.

    Modelden gelen tek sayı `beklenen_kolon_basi`dir ve **seçim uzayının
    tamamı** üzerinden hesaplanır: indirgeme yansız olduğu sürece bir alt
    kümenin kolon başı beklentisi uzayın ortalamasına eşittir. Bu bir
    varsayımdır ve çıktıda öyle işaretlenir.
    """
    gercek = d["meta"]["results"]
    picks = r["picks"]
    kacaklar = [i + 1 for i, (p, g) in enumerate(zip(picks, gercek)) if g not in p]
    kademeler = {int(k): v for k, v in (r.get("kademeler") or {}).items()}
    odul = {t["correct"]: t["prize"]
            for t in (d["meta"].get("payout") or {}).get("tiers", [])
            if t.get("prize") is not None}
    ger = sum(adet * odul[k] for k, adet in kademeler.items() if k in odul)
    kolon = r.get("columns")
    bedel = r.get("bedel")
    mal = bedel if bedel is not None else (kolon * KOLON_BEDELI if kolon else None)
    # Uzayin tamami uzerinden kolon basi beklenti — indirgemenin yansiz
    # oldugu VARSAYIMIYLA. Kayitli kolon sayisiyla carpilmaz; oran olarak
    # okunur.
    tam = plan_karnesi(d, picks, "tam", r.get("label", "referans"))
    return {
        "ad": r.get("label"), "sistem": "kayitli", "picks": list(picks),
        "source": r.get("source"), "note": r.get("note"),
        "banko": sum(1 for x in picks if len(x) == 1),
        "cift": sum(1 for x in picks if len(x) == 2),
        "uclu": sum(1 for x in picks if len(x) == 3),
        "uzay": math_prod(len(x) for x in picks),
        "kolon": kolon,
        "indirgeme": (kolon / math_prod(len(x) for x in picks)) if kolon else None,
        "misses": kacaklar,
        "best": (max(kademeler) if kademeler else None),
        "kume_ici": tam["kume_ici"], "kalabalik_ici": tam["kalabalik_ici"],
        "oran": tam["oran"],
        "kademeler": kademeler,
        "gerceklesen": ger, "maliyet": mal,
        "net": (ger - mal) if mal is not None else None,
        "roi": (ger / mal) if mal else None,
        "beklenen_kolon_basi_uzay": (tam["getiri"]["beklenen_kolon_basi"]
                                     if tam["getiri"] else None),
        "sapma": sapma_defteri(d, picks),
        "not": ("Kademe dağılımı KAYITTAN gelir, modelden değil. Kolon başı "
                "beklenti seçim uzayının tamamı üzerinden hesaplandı "
                "(indirgemenin yansız olduğu varsayımıyla)."),
    }


def referans_kuponlar(d: dict[str, Any],
                      kupon: dict[str, Any]) -> list[dict[str, Any]]:
    """Kupon dosyasına kaydedilmiş DIŞ kuponlar (kullanıcının kendi kuponu,
    o haftanın 15 bileni gibi) — kendi karneleri ve sapma defterleriyle.

    Bunlar bizim kuralımızın ürünü değildir ve öyle sunulmaz: ayrı bir
    başlıkta, kaynağıyla birlikte durur. Kıyasın anlamlı olması için
    oynanma biçimi (`sistem`) mutlaka kayıtta yazılıdır — yazılmazsa
    16 satır varsayılır ve 8 kat pahalı bir kupon ucuz gibi okunur.
    """
    out = []
    for r in kupon.get("referans") or []:
        if r.get("sistem") == "kayitli":
            out.append(kayitli_karne(d, r))
            continue
        kart = plan_karnesi(d, r["picks"], r.get("sistem", "fix16"),
                            r.get("label", "referans"))
        # Iki karsi-olgusal, ikisi de ayni gövdeyle ölçülür:
        #
        # `oteki_sistem` — AYNI isaretler oteki oynanma biciminde. "15'i
        # satin alan sey isaretler mi, tam kapsama mi" sorusunun cevabi.
        #
        # `azami` — AYNI SEKIL (ayni sayida banko/cift/uclu) ama mekanik
        # semboller. Bu satir kuponun kendi gorusunu yalitir: sekil ayni,
        # bedel ayni, degisen yalnizca hangi sembolun tutuldugu.
        oteki = "fix16" if r.get("sistem", "fix16") == "tam" else "tam"
        azami_picks = []
        for mm, pk in zip(d["matches"], r["picks"]):
            sirali = sorted(SEM, key=lambda x: -mm["probs"][x])
            azami_picks.append("".join(sorted(sirali[:len(pk)], key=SEM.index)))
        kart.update({
            "source": r.get("source"), "note": r.get("note"),
            "system_note": r.get("system_note"),
            "kayitli_kolon": r.get("columns"),
            "sapma": sapma_defteri(d, r["picks"]),
            "oteki_sistem": plan_karnesi(d, r["picks"], oteki,
                                         f"{r.get('label', 'referans')} · {oteki}"),
            "azami": plan_karnesi(d, azami_picks, r.get("sistem", "fix16"),
                                  "aynı şekil · azami kapsama"),
        })
        out.append(kart)
    return out


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
        # Dis kuponlar ve bizim planlarimiz AYNI karne gövdesiyle ölçülür;
        # aksi hâlde 8 kat pahalı bir kupon ucuz olanla eşit görünürdü.
        "referans": referans_kuponlar(d, kupon),
        "referans_notu": kupon.get("referans_notu"),
        "havuz": havuz_karnesi(d),
        "kartlar": ([plan_karnesi(d, sonuclar[0]["picks"], "fix16",
                                  sonuclar[0].get("label") or "1. Tahmin ana")]
                    + ([plan_karnesi(d, ayarli["picks"], "fix16",
                                     "2. Tahmin ayarlı")] if ayarli else [])),
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

    kayitli = [k for k in o["referans"] if k["sistem"] == "kayitli"]
    modelli = [k for k in o["referans"] if k["sistem"] != "kayitli"]
    if kayitli:
        _basli("KAYITLI DIŞ KUPONLAR — kademe dağılımı MODELDEN DEĞİL EKRANDAN")
        print(f"  {'kupon':<34}{'kolon':>7}{'maliyet':>11}{'getiri':>15}"
              f"{'NET':>15}{'ROI':>9}{'küme-içi':>9}{'E[TL/kolon]':>12}")
        for k in kayitli + [dict(kart, kolon=kart["kolon"],
                                 maliyet=kart["getiri"]["maliyet"],
                                 gerceklesen=kart["getiri"]["gerceklesen"],
                                 net=kart["getiri"]["net"], roi=kart["getiri"]["roi"],
                                 beklenen_kolon_basi_uzay=None)
                           for kart in o["kartlar"] if kart.get("getiri")]:
            e = k.get("beklenen_kolon_basi_uzay")
            print(f"  {k['ad'][:34]:<34}{k['kolon']:>7,}"
                  f"{'₺' + format(k['maliyet'], ',.0f'):>11}"
                  f"{'₺' + format(k['gerceklesen'], ',.2f'):>15}"
                  f"{'₺' + format(k['net'], ',.2f'):>15}"
                  f"{format(k['roi'], '.1f') + 'x':>9}"
                  f"{format(100*k['kume_ici'], '.2f') + '%':>9}"
                  f"{('₺' + format(e, '.2f')) if e else '—':>12}")
        print(f"  Kolon bedeli ₺{KOLON_BEDELI:.0f} — {KOLON_BEDELI_KAYNAGI}")
        print("  E[TL/kolon] seçim uzayının TAMAMI üzerinden; indirgemenin "
              "yansız olduğu varsayımıyla.")
        for k in kayitli:
            sp = k["sapma"]
            print(f"\n  ─ {k['ad']}")
            print(f"    işaret: {' '.join(k['picks'])}")
            print(f"    {k['banko']} banko · {k['cift']} çift · {k['uclu']} üçlü · "
                  f"uzay {k['uzay']:,} · oynanan {k['kolon']:,} kolon "
                  f"(uzayın %{100*k['indirgeme']:.1f}'i) · kaçak "
                  f"{k['misses'] or 'YOK — 15 kapsandı'}")
            print("    kademeler: " + " · ".join(
                f"{kk}: {vv}" for kk, vv in sorted(k["kademeler"].items(), reverse=True)))
            if not sp["sapma"]:
                print("    Azami kapsamadan sapma YOK — mekanik seçimin aynısı.")
            else:
                print(f"    Azami kapsamadan {sp['sapma']} sapma · net {sp['net']:+d} "
                      f"(piyasanın beklediği {sp['beklenen_net']:+.2f}) · "
                      f"P(net ≥ {sp['net']}) = %{100*sp['p_net']:.1f}")
                for r in sp["rows"]:
                    im = ("kazandı" if r["kazandi"]
                          else ("kaybetti" if r["kaybetti"] else "fark etmedi"))
                    print(f"      {r['no']:>2} {r['mac'][:30]:<30} [{r['pick']:<3}] "
                          f"azami [{r['azami']:<3}] gerçek {r['gercek']} · {im}")
        print(f"\n  {o['referans_notu']}" if o.get("referans_notu") else "")

    if modelli:
        _basli("REFERANS KUPONLAR (bize ait değil) ve AYNI ÖLÇEKTE BİZ")
        print(f"  {'kupon':<26}{'sistem':>7}{'kolon':>8}{'P15':>8}{'≥14':>8}"
              f"{'≥13':>8}{'≥12':>8}{'oran':>6}{'gerçek':>8}")
        for k in modelli + o["kartlar"]:
            p15 = "—" if k["p15"] is None else f"%{100*k['p15']:.3f}"
            print(f"  {k['ad'][:26]:<26}{k['sistem']:>7}{k['kolon']:>8,}{p15:>8}"
                  f"{'%' + format(100*k['p14'], '.2f'):>8}"
                  f"{'%' + format(100*k['p13'], '.2f'):>8}"
                  f"{'%' + format(100*k['p12'], '.2f'):>8}"
                  f"{k['oran']:>6.2f}{str(k['best']) + '/15':>8}")
        print("  P15 = OYNANAN kolonların toplam olasılığı. 16 satırlık kaplamada "
              "küme-içi kalmak 14 verir, 15 değil;")
        print("  tam sistemde küme-içi kalmak 15 verir. İki sütun bu yüzden "
              "sistemden okunur.")
        for k in modelli:
            sp = k["sapma"]
            print(f"\n  ─ {k['ad']} · {k.get('source') or '—'}")
            print(f"    işaret: {' '.join(k['picks'])}")
            print(f"    {k['banko']} banko · {k['cift']} çift · {k['uclu']} üçlü · "
                  f"uzay {k['uzay']:,} · oynanan {k['kolon']:,} kolon "
                  f"· en iyi kolon {k['best']}/15 · kaçak {k['misses']}")
            if not sp["sapma"]:
                print("    Azami kapsamadan sapma yok — mekanik seçimin aynısı.")
                continue
            print(f"    AZAMİ KAPSAMADAN {sp['sapma']} SAPMA "
                  f"({100*sp['kapsama_bedeli']:.1f} puan kapsama bedeli):")
            for r in sp["rows"]:
                im = ("kazandı" if r["kazandi"]
                      else ("kaybetti" if r["kaybetti"] else "fark etmedi"))
                print(f"      {r['no']:>2} {r['mac'][:30]:<30} [{r['pick']:<3}] "
                      f"azami [{r['azami']:<3}] gerçek {r['gercek']} · {im} "
                      f"(tuttuğu %{100*r['p_tuttugu']:.0f} ↔ attığı %{100*r['p_attigi']:.0f})")
            print(f"    Net {sp['net']:+d} (kazanç {sp['kazanc']} / kayıp {sp['kayip']}) · "
                  f"piyasanın beklediği net {sp['beklenen_net']:+.2f} · "
                  f"P(net ≥ {sp['net']}) = %{100*sp['p_net']:.1f}")
            az, ot = k["azami"], k["oteki_sistem"]
            print(f"    AYNI ŞEKİL, azami kapsama işaretleri ({az['kolon']:,} kolon): "
                  f"{az['best']}/15 · kaçak {az['misses']}")
            print(f"    AYNI İŞARET, {ot['sistem']} sisteminde ({ot['kolon']:,} kolon): "
                  f"{ot['best']}/15")
            print("    Sapmanın piyasa altındaki beklenen neti, tanım gereği "
                  "eksi kapsama bedelidir: sapmak")
            print("    ancak piyasadan BAŞKA bir görüş varsa mantıklıdır. "
                  "Tek hafta görüşü şanstan ayıramaz.")

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

    if o["havuz"]:
        _basli("HAVUZ KARNESİ — kazanan adetleri modelden çıkıyor mu")
        print(f"  {'kademe':<8}{'kazanan':>9}{'kademe havuzu':>18}"
              f"{'N (kalabalık)':>16}{'N (piyasa)':>14}")
        for r in o["havuz"]["rows"]:
            hav = ("—" if r["kademe_havuzu"] is None
                   else f"{r['kademe_havuzu']:,.2f}")
            nk = "—" if r["n_kalabalik"] is None else f"{r['n_kalabalik']:,.0f}"
            npi = "—" if r["n_piyasa"] is None else f"{r['n_piyasa']:,.0f}"
            print(f"  {str(r['kademe']) + ' bilen':<8}{r['kazanan']:>9,}{hav:>18}"
                  f"{nk:>16}{npi:>14}")
        print("  N = o kademenin ima ettiği havuz kolonu (kazanan ÷ modelin "
              "verdiği olasılık).")
        print("  Model doğruysa dört satır AYNI N'i verir; kademeler arası "
              "tutarlılık modelin şeklini sınar.")
        print(f"  {o['havuz']['not']}")

    if any(k.get("getiri") for k in o["kartlar"] + o["referans"]):
        _basli("GETİRİ — gerçekleşen ve (aynı ödül vektörüyle) beklenen")
        print(f"  {'kupon':<26}{'kolon':>7}  {'kazanan kolon':<24}"
              f"{'gerçekleşen TL':>16}{'başabaş':>10}{'bekl.TL/kolon':>14}")
        # Referansin OTEKI sistemdeki hali de listeye girer: "ayni isaretler,
        # sekizde bir bedel" cumlesinin parasal karsiligi tam olarak burada
        # gorunur.
        kartlar = []
        for k in o["referans"]:
            kartlar.append(k)
            if k.get("oteki_sistem"):
                kartlar.append(k["oteki_sistem"])
        for k in kartlar + o["kartlar"]:
            g = k.get("getiri")
            if not g:
                continue
            kaz = " ".join(f"{x}:{n}" for x, n in g["kazanan_kolon"].items()) or "—"
            print(f"  {k['ad'][:26]:<26}{g['kolon']:>7,}  {kaz:<24}"
                  f"{g['gerceklesen']:>16,.2f}{g['gerceklesen_kolon_basi']:>10,.2f}"
                  f"{g['beklenen_kolon_basi']:>14,.2f}")
        print("  'başabaş' = kolon bedeli bunun altındaysa hafta kâra geçti "
              "(kolon fiyatı yayınlanmıyor).")
        print("  Beklenen sütunu kuponları kıyaslar; gerçekleşen sütunu "
              "haftanın kendi gürültüsünü taşır.")

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
