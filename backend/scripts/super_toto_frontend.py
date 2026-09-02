#!/usr/bin/env python3
"""Arayüzün okuduğu sezon beslemesini üretir.

Sorun: `frontend/lib/super-toto.ts` sezonun 41 haftasını **elle** tutuyordu ve
hepsi boştu. Backend'de 1. ve 2. haftanın verisi dururken sayfa "verisi henüz
girilmedi" diyordu — iki taraf birbirinden habersizdi.

Bu script tek yönlü bağı kurar: backend verisi kaynaktır, arayüz onu okur.

    python scripts/super_toto_frontend.py            # yazar
    python scripts/super_toto_frontend.py --kontrol  # yalnizca denetler (CI)

`--kontrol` üretilecek içerikle dosyadakini karşılaştırır ve farklıysa sıfırdan
farklı kodla çıkar. Böylece hafta verisi girilip besleme yenilenmediğinde CI
kırılır — sessizce eskimiş bir arayüz, boş bir arayüzden daha kötüdür çünkü
yanlış olduğu belli olmaz.

**Neden statik dosya, neden API değil.** Geçmiş hafta kapanmış bir kayıttır:
sonuç değişmez, oran değişmez. Değişmeyen bir şey için istek başına hesap
yapmanın karşılığı yok. Yaklaşan haftanın canlı verisi (henüz oynanmamış maçın
oranı) bir gün gerekirse, o zaman ayrı bir uç nokta açılır — bu dosya
kapanmış haftaların kaydıdır.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from scripts._ortak import metin, modul
from spor_toto.core import SEMBOLLER
from spor_toto.odds import implied_probs

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
SEM = SEMBOLLER
CIKTI = KOK.parent / "frontend" / "lib" / "super-toto-veri.json"


#: Kardes betigi getirme TEK kaynaktan: `scripts._ortak.modul`. Ayni govde
#: VE ayni docstring uc betikte birebir duruyordu — o docstring bir ONCEKI
#: tekillestirme turunu anlatiyor.
_modul = modul


def _yuvarla(p: dict[str, float]) -> dict[str, float]:
    return {s: round(p[s], 4) for s in SEM}


def _donmus_blok(donmus: dict[str, Any] | None) -> dict[str, Any] | None:
    """Dondurulmuş kupon dosyasından arayüzün okuyacağı kayıt.

    Ana varyant (`variants[0]`) alınır; kupon dosyası birden çok bütçe
    sürümü taşıyabilir ama sayfada gösterilecek olan kuralın kendisidir.
    """
    if not donmus:
        return None
    v = donmus["variants"][0]
    st = donmus["meta"].get("strategy") or {}
    return {
        "picks": v["picks"],
        "label": v.get("label"),
        "columns": v.get("columns"), "rows": v.get("rows"),
        "in_set_p": v.get("in_set_p"),
        "banko_esik": st.get("banko_esik"),
        "uclu_esik": st.get("uclu_esik"),
        # Hangi KURALLA donduruldugu. Ilk iki hafta `esik`ti ve arayuz
        # kuralin adini hic tasimiyordu — kartta "esik <banko>/<uclu>"
        # SABIT yaziliydi. 3. hafta `hedef + kalabalik ayari` ile
        # dondurulunca esikler bos kaldi ve kart "esik / " diye YANLIS bir
        # kural bildirdi. Ad artik kayittan gelir.
        "kural": st.get("kural"),
        # Hangi olcekte donduruldugu — bu alan olmadan isaretler
        # yorumlanamaz (bkz. strategy.arindirma_notu).
        "arindirma": st.get("arindirma"),
        "marj_ort_pct": st.get("marj_ort_pct"),
        "frozen_at": donmus["meta"].get("frozen_at"),
        "results_known": donmus["meta"].get("results_known"),
        # Oynanacak 16 satir. Kartta yalnizca isaretler vardi; kuponu
        # gercekten DOLDURACAK kisi satirlari gormek zorunda.
        "lines": v.get("lines"),
        # Kuralin verdigi ALTERNATIFLER ve her birinin olculmus bedeli.
        # Kupon "nicin bu" sorusunu ancak yaninda reddettikleriyle
        # cevaplayabilir; rapor sayfasi bunu gosteriyordu, arayuz
        # gostermiyordu.
        "variants": [{
            "label": x.get("label"),
            "picks": x["picks"],
            "columns": x.get("columns"),
            "hedef": x.get("hedef"),
            "in_set_p": x.get("in_set_p"),
            "crowd_in_set_p": x.get("crowd_in_set_p"),
            "crowd_ratio": x.get("crowd_ratio"),
        } for x in donmus.get("variants", [])],
        "kalabalik_gerekcesi": donmus["meta"].get("kalabalik_gerekcesi"),
        # Fiyat duyarliligi: kupon aninda KESINLIKLE elde olan fiyatla
        # (acilis) kurulan surum. Kapanisin o an elde olup olmadigi
        # dogrulanamiyorsa, bedelinin olculmus olmasi gerekir.
        "duyarlilik": ({
            "not": donmus["duyarlilik"].get("not"),
            "fark": donmus["duyarlilik"].get("fark"),
            "picks": donmus["duyarlilik"].get("picks"),
            "hedef": donmus["duyarlilik"].get("hedef"),
        } if donmus.get("duyarlilik") else None),
    }


def _fiyat_blok(d: dict[str, Any]) -> dict[str, Any] | None:
    """Bir haftanın FİYAT KAYNAKLARI — üç bahisçi × açılış/kapanış.

    3. haftadan itibaren hafta dosyası `matches[].odds_books` taşıyor.
    Rapor sayfası (`super_toto_sayfa.py`) bunu çiziyordu, arayüz
    göremiyordu; ikisi aynı haftayı anlatıp farklı şey söylüyordu.

    **Her sayı marj arındırılmış olasılıktır, ham oran değil.** Ham oranın
    hareketi, piyasanın fikir değiştirmesiyle bahisçinin marjını
    değiştirmesini karıştırır (bkz. `spor_toto.cizgi` modül başlığı).

    Alan yoksa `None` döner ve arayüz bölümü hiç çizmez — 1. ve 2.
    haftanın kaydı tek bir bültenin tek anını taşıyor.
    """
    maclar = d["matches"]
    kitaplar = sorted(maclar[0].get("odds_books") or {})
    if len(kitaplar) < 2:
        return None

    ana = (d["meta"].get("odds_kind") or "").replace("-", "_")
    ac = ana.replace("_kapanis", "_acilis")
    an = ana.rsplit("_", 1)[-1]
    esanlı = sorted((k for k in kitaplar if k.endswith(an)),
                    key=lambda k: (k != ana, k))

    def p(m, anahtar):
        o = (m.get("odds_books") or {}).get(anahtar)
        return implied_probs(o) if o else None

    marj = {}
    for k in kitaplar:
        ms = [sum(1 / v for v in m["odds_books"][k].values()) - 1 for m in maclar]
        marj[k] = round(100 * sum(ms) / len(ms), 2)

    # Bir bahiscinin kapanisi acilisiyla BIREBIR ayniysa o satir bir fiyat
    # degil, tazelenmemis bir kayittir. Ayrisma sutununda buyuk gorunur ve
    # gorus farki sanilir; isaretlenmezse okuyucu yaniltilir.
    bayat = {}
    for k in kitaplar:
        if not k.endswith("_kapanis"):
            continue
        esi = k.replace("_kapanis", "_acilis")
        if esi in kitaplar:
            ayni = [m["no"] for m in maclar
                    if m["odds_books"][k] == m["odds_books"][esi]]
            if ayni:
                bayat[k] = ayni

    satirlar = []
    for m in maclar:
        pk, pa = p(m, ana), p(m, ac)
        kitap = {k: _yuvarla_dagilim(p(m, k)) for k in esanlı}
        deger = [x for x in (p(m, k) for k in esanlı) if x]
        ayrisma = max((abs(x[s] - y[s]) for x in deger for y in deger
                       for s in SEM), default=0.0)
        sembol = (max(SEM, key=lambda s: abs(pk[s] - pa[s]))
                  if pk and pa else None)
        satirlar.append({
            "no": m["no"],
            "books": kitap,
            "movement_symbol": sembol,
            "movement": round(pk[sembol] - pa[sembol], 4) if sembol else None,
            "disagreement": round(ayrisma, 4),
        })
    return {"books": esanlı, "main_book": ana, "margins": marj,
            "stale_closing": bayat, "rows": satirlar}


def _yuvarla_dagilim(p: dict[str, float] | None) -> dict[str, float] | None:
    return None if p is None else {s: round(float(p[s]), 4) for s in SEM}


def _kayit_karnesi(d: dict[str, Any], ad: str, picks: list[str] | None,
                   deg_mod: Any) -> dict[str, Any] | None:
    """Bir dondurulmuş kaydın sonuç karnesi. Kaydın KENDİSİNE dokunmaz."""
    if not picks:
        return None
    k = deg_mod.kupon_degerlendir(d, picks)
    return {
        "ad": ad,
        "picks": k["picks"],
        "best": k["best"],
        "misses": k["misses"],
        "miss_count": k["miss_count"],
        "expected_misses": round(k["expected_misses"], 4),
        "p_in_set": round(k["p_in_set"], 6),
        # Hafta beklenenden iyi mi kotu mu gectiyse bu sayi soyler:
        # gerceklesen kacak sayisi kadar VEYA daha cok kacagin olasiligi.
        "p_at_least_actual": round(k["p_at_least_actual"], 6),
        "per_match": [{"no": m["no"], "pick": m["pick"], "gercek": m["gercek"],
                       "tuttu": m["tuttu"]} for m in k["per_match"]],
    }


def _sonuc_blok(d: dict[str, Any], donmus: dict[str, Any] | None,
                tahmin2: dict[str, Any] | None) -> dict[str, Any] | None:
    """Haftanın SONUÇ karnesi — tahmin kayıtlarından AYRI bir alan.

    **Niçin ayrı.** Sonuç geldiğinde tahmin panelleri sonuçla doluyordu:
    maç tablosuna bir "SONUÇ" sütunu giriyor, kupon kartına "9/15 küme
    içinde" ekleniyordu. Yani dondurulmuş bir kaydın üzerine sonradan
    bilinen bir şey yazılıyordu ve kayıt artık "o an ne biliniyordu"
    sorusunu temiz cevaplayamıyordu.

    Bu blok o bilgiyi kendi alanına alır. 1. ve 2. Tahmin panelleri
    sonuçları GÖRMEZ; sonuç kendi sekmesinde durur ve her iki kaydı da
    **aynı** ölçüyle karneler.

    Sonuç girilmemişse `None` döner ve arayüz sekmeyi hiç göstermez.
    """
    sonuc = (d.get("meta") or {}).get("results")
    if not sonuc:
        return None
    deg = _modul("degerlendir")

    kayitlar = []
    t1 = (donmus or {}).get("variants", [{}])[0].get("picks") if donmus else None
    k1 = _kayit_karnesi(d, "1. Tahmin", t1, deg)
    if k1:
        kayitlar.append(k1)
    t2 = ((tahmin2 or {}).get("kupon") or {}).get("ayarli", {}).get("picks")
    k2 = _kayit_karnesi(d, "2. Tahmin", t2, deg)
    if k2:
        kayitlar.append(k2)

    meta = d["meta"]
    return {
        "results": sonuc,
        "results_source": meta.get("results_source"),
        "results_entered_at": meta.get("results_entered_at"),
        "kayitlar": kayitlar,
        # Kalabaligin ve piyasanin kendi kuponu — ikramiyenin nicin buyuk
        # ya da kucuk oldugunun cevabi burada.
        "kalabalik": deg.kalabalik_karnesi(d),
        # Ikramiye ekrani girilmisse kademeler. Para birimli sayilar
        # arayuze cikar cunku bunlar OLCUM, tahmin degil.
        "payout": (meta.get("payout") or {}).get("tiers"),
        "payout_source": (meta.get("payout") or {}).get("source"),
        "note": ("Bu sekmedeki her sayı sonuçlar görüldükten SONRA "
                 "hesaplandı. Tahmin sekmeleri onu görmez ve değişmez."),
    }


def _tahmin2_blok(kayit: dict[str, Any] | None) -> dict[str, Any] | None:
    """**2. Tahmin** kaydından arayüzün okuyacağı kısım.

    Kayıt (`hafta_NN_tahmin2.json`) tam gövdedir ve havuz beklenen değeri
    gibi **arayüze çıkmayacak** bloklar taşır (`getiri` modül başlığı,
    docs §6.3b). Burada seçilerek alınır: para birimli hiçbir sayı geçmez.

    1. Tahmin'in kaydı bu bloktan **etkilenmez**. İkisi ayrı alanlarda
    durur ve arayüz aralarında geçiş yapar; biri ötekinin yerine geçmez.
    """
    if not kayit:
        return None
    meta = kayit["meta"]
    k = kayit["kupon"]
    ayarli, taban, esik = k["ayarli"], k["taban"], k["esik"]
    duy = kayit.get("duyarlilik")
    g = kayit["gorus"]
    return {
        "ad": meta["ad"],
        "frozen_at": meta["frozen_at"],
        "results_known": meta["results_known"],
        "arindirma": meta["arindirma"],
        "onceki_arindirma": meta["onceki_arindirma"],
        "kural": meta["kural"],
        "kayip_orani": meta["kayip_orani"],
        "note": meta["note"],
        "yenilikler": meta["yenilikler"],
        "picks": ayarli["picks"],
        "taban_picks": taban["picks"],
        "esik_picks": esik["picks"],
        "columns": ayarli["columns"], "rows": ayarli["rows"],
        "engine": ayarli["engine"],
        "guaranteed_14": ayarli["guaranteed_14"],
        "banko": ayarli["banko"], "cift": ayarli["cift"],
        "uclu": ayarli["uclu"],
        "p_hedef": round(ayarli["p_hedef"], 6),
        "in_set_p": round(ayarli["in_set_p"], 6),
        "crowd_in_set_p": round(ayarli["crowd_in_set_p"], 6),
        "crowd_ratio": round(ayarli["crowd_ratio"], 4),
        "butce": k["butce"], "butce_kaynagi": k["butce_kaynagi"],
        "lines": ayarli["lines"],
        "ayar": {
            "not": k["ayar"]["not"],
            "p_hedef_taban": round(k["ayar"]["p_hedef_taban"], 6),
            "p_hedef_ayarli": round(k["ayar"]["p_hedef_ayarli"], 6),
            "oran_taban": round(k["ayar"]["oran_taban"], 4),
            "oran_ayarli": round(k["ayar"]["oran_ayarli"], 4),
            # Rakip yogunlugu YALNIZCA ayni sekildeki planlar arasinda
            # okunur; taban ile ayarli tam olarak o cifttir.
            "kat_taban": round(taban["kosullu_rakip"]["kat"], 3),
            "kat_ayarli": round(ayarli["kosullu_rakip"]["kat"], 3),
            "degisimler": [{
                "no": x["no"], "taban": x["taban"], "yeni": x["yeni"],
                "prob_taban": round(x["prob_taban"], 4),
                "prob_yeni": round(x["prob_yeni"], 4),
                "oynanma_taban": round(x["oynanma_taban"], 4),
                "oynanma_yeni": round(x["oynanma_yeni"], 4),
            } for x in k["ayar"]["degisimler"]],
        },
        "kiyas": (None if not kayit.get("kiyas") else {
            "eski_picks": kayit["kiyas"]["eski_picks"],
            "eski_arindirma": kayit["kiyas"]["eski_arindirma"],
            "eski_kural": kayit["kiyas"]["eski_kural"],
            "eski_p_hedef": round(
                kayit["kiyas"]["eski_bugunku_olcekte"]["p_hedef"], 6),
            "eski_columns": kayit["kiyas"]["eski_bugunku_olcekte"]["columns"],
            "eski_crowd_ratio": round(
                kayit["kiyas"]["eski_bugunku_olcekte"]["crowd_ratio"], 4),
            "degisen_maclar": kayit["kiyas"]["degisen_maclar"],
            "not": kayit["kiyas"]["not"],
        }),
        "gorus": {
            "kapsama": round(g["kapsama"], 4),
            "dc_olan": g["dc_olan"], "n": g["n"],
            "kullanilabilir": g["kullanilabilir"],
            "tarihce_mac": g["tarihce_mac"], "tarihce_son": g["tarihce_son"],
            "eslesmeyen": g["eslesmeyen"],
            "uyari": g["uyari"],
        },
        "ayrisma": [{
            "no": r["no"], "mac": r["mac"],
            "piyasa": _yuvarla_dagilim(r["piyasa"]),
            "dc": _yuvarla_dagilim(r["dc"]),
            "piyasa_fav": r["piyasa_fav"], "dc_fav": r["dc_fav"],
            "sembol_farkli": r["sembol_farkli"],
            "toplam_sapma": round(r["toplam_sapma"], 4),
        } for r in kayit["ayrisma"]],
        "duyarlilik": (None if not duy else {
            "ortanca_marj": round(duy["ortanca_marj"], 4),
            "duzeltilen": [{"no": x["no"], "mac": x["mac"],
                            "marj": round(x["marj"], 4)}
                           for x in duy["duzeltilen"]],
            "picks": duy["picks"],
            "p_hedef": round(duy["p_hedef"], 6),
            # Asil cevap: isaretler DEGISIYOR mu. Arayuz bunu tek basina
            # okuyabilsin diye burada hesaplanir.
            "degisti": duy["picks"] != ayarli["picks"],
            "not": duy["not"],
        }),
        "matches": [{
            "no": r["no"],
            "probs": _yuvarla_dagilim(r["probs"]),
            "probs_onceki": _yuvarla_dagilim(r["probs_onceki"]),
            "dc": _yuvarla_dagilim(r["dc"]), "dc_var": r["dc_var"],
            "elo_farki": (None if r["elo_farki"] is None
                          else round(r["elo_farki"], 1)),
            "elo_beklenen": (None if r["elo_beklenen"] is None
                             else round(r["elo_beklenen"], 4)),
            "taban": r["taban"], "isaret": r["isaret"],
        } for r in kayit["matches"]],
    }


def _planlanan_hafta() -> int:
    """Sezonun planlanan hafta sayisi — gecen sezonun GERCEKLESMIS sayisi.

    Yeni sezonun takvimi bastan belli degil; en iyi tahmin bir onceki
    sezonun kac hafta urettigidir ve o sayi korpustan okunur. Korpus yoksa
    41'e duser (2025/26'nin olculmus degeri) — ama o zaman bile sayi BURADA
    turer, arayuzde elle yazili durmaz.
    """
    from spor_toto.history import normalized_weeks

    try:
        return len(normalized_weeks()) or 41
    except Exception:
        return 41


def uret(sezon: str = "2026_27") -> dict[str, Any]:
    from spor_toto.backtest import VARSAYILAN_BANKO, VARSAYILAN_UCLU
    from spor_toto.odds import (
        ARINDIRMA_VARSAYILAN,
        SAGLAYICI_ADLARI,
        saglayici_adi,
    )

    hafta_mod = _modul("hafta")
    sezon_mod = _modul("sezon")

    haftalar: list[dict[str, Any]] = []
    for no in sezon_mod.haftalari_bul(sezon):
        d = hafta_mod.hafta_yukle(sezon, no)
        meta = d["meta"]
        # DONDURULMUS kupon KAYITTIR ve yeniden hesaplanmaz. Bu satirin
        # onemi buyuk: 2026-08'de marj arindirma varsayilani degisti ve ayni
        # esik baska isaretler uretiyor (1. haftada 12. mac uclu → cift,
        # 2. haftada 1. mac cift → banko). Yeniden hesaplanan bir kuponu
        # sayfada gostermek, sonuclar gorulmeden donduruldugunu soyleyen
        # kaydin ustune sonradan yazmak olurdu — projenin en degerli
        # aliskanligi tam olarak budur.
        kupon_yolu = (KOK / "data" / "super_toto" / sezon
                      / f"hafta_{no:02d}_kupon.json")
        donmus = (json.loads(kupon_yolu.read_text(encoding="utf-8"))
                  if kupon_yolu.exists() else None)
        tahmin2_yolu = (KOK / "data" / "super_toto" / sezon
                        / f"hafta_{no:02d}_tahmin2.json")
        tahmin2 = (json.loads(tahmin2_yolu.read_text(encoding="utf-8"))
                   if tahmin2_yolu.exists() else None)
        # Bugunku kural ne uretirdi — AYRI alan, ayri etiket. Karsilastirma
        # bilgi tasir; kaydin yerine gecemez.
        bugun = hafta_mod.kupon_kur(d, VARSAYILAN_BANKO, VARSAYILAN_UCLU)
        haftalar.append({
            "week": no,
            "program": meta.get("program"),
            "close_date": min((m["date"] for m in d["matches"] if m.get("date")),
                              default=None),
            "results": meta.get("results"),
            "odds_source": meta.get("odds_source"),
            "odds_kind": meta.get("odds_kind"),
            "play_source": meta.get("play_source"),
            # Iki uyari listesi AYRI tasinir: biri insanin notu, digeri
            # kapinin urettigi. Arayuz de ikisini ayri gostermeli.
            "warnings_manual": meta.get("data_warnings") or [],
            "warnings_generated": meta.get("uretilen_uyarilar") or [],
            "matches": [{
                "no": m["no"], "date": m.get("date"), "kickoff": m.get("kickoff"),
                "league": m["league"], "home": m["home"], "away": m["away"],
                "odds": m["odds"], "odds_missing": m["odds_yok"],
                "probs": _yuvarla(m["probs"]), "fav": m["fav"],
                "margin": round(m["margin"], 4),
                "play": _yuvarla(m["play"]),
                "result": (meta["results"][m["no"] - 1]
                           if meta.get("results") else None),
            } for m in d["matches"]],
            "coupon": _donmus_blok(donmus),
            # Fiyat kaynaklari — yalnizca hafta dosyasi birden cok bahisci
            # tasiyorsa dolu. Ilk iki haftada null'dur ve arayuz bolumu
            # hic cizmez.
            "prices": _fiyat_blok(d),
            # IKINCI kayit — 1. Tahmin'in yerine GECMEZ, yanina durur.
            # Uretici: `scripts/super_toto_tahmin2.py --yaz`. Dosya yoksa
            # alan null'dir ve arayuz "2. Tahmin" dugmesini gostermez.
            "tahmin2": _tahmin2_blok(tahmin2),
            # SONUC — tahmin kayitlarindan AYRI. Sonuc girilmemisse null'dur
            # ve arayuz sekmeyi hic gostermez.
            "sonuc": _sonuc_blok(d, donmus, tahmin2),
            # Revizyon kaydi: girdi degistigi icin (orn. sonradan ilan edilen
            # oran) kupon yeniden kuruldusa, ONCEKI surum de gorunur kalir.
            # Gorunmeyen bir revizyon, revizyon olmayan bir kayittan daha
            # kotudur — degistigi belli olmaz.
            "coupon_superseded": (
                {"reason": donmus["superseded"].get("reason"),
                 "revised_at": donmus["superseded"].get("revised_at"),
                 "arindirma": donmus["superseded"].get("arindirma"),
                 "picks": donmus["superseded"]["variants"][0]["picks"]}
                if donmus and donmus.get("superseded") else None),
            "coupon_today": {
                "picks": bugun["picks"],
                "banko": bugun["banko"], "cift": bugun["cift"],
                "uclu": bugun["uclu"],
                "columns": bugun["columns"], "rows": bugun["rows"],
                "in_set_p": round(bugun["in_set_p"], 6),
                "banko_esik": bugun["banko_esik"],
                "uclu_esik": bugun["uclu_esik"],
                "arindirma": ARINDIRMA_VARSAYILAN,
                # Bugunku kuralin adi. Dondurulmus kuponlar `esik` ile
                # kuruldu; varsayilan 2026-08'de `hedef`e cevrildi (B0,
                # docs §3.19). Hangi kuralin urettigi yazmazsa iki kupon
                # arasindaki fark yorumlanamaz.
                "kural": bugun["kural"],
                "butce": bugun["butce"],
                "p_hedef": round(bugun["p_hedef"], 6),
                "p_hedef_esik": round(bugun["p_hedef_esik"], 6),
            },
            # Isaret farki: hem OLCEK (arindirma) hem KURAL degisti.
            "coupon_drift": (
                [i + 1 for i, (a, b) in enumerate(
                    zip(donmus["variants"][0]["picks"], bugun["picks"]))
                 if a != b]
                if donmus else None),
        })

    return {
        "season": "2026/2027",
        "season_key": sezon,
        # Sezonun PLANLANAN hafta sayisi — arayuzde ELLE yaziliydi (41) ve
        # o sayi GECEN sezonun sayisiydi; besleme ise 2026/27 diyor. Bu
        # modulun basligi tam da bu elle-tutmayi bitirmek icin yazilmisti:
        # hafta LISTESI uretilir olmus, hafta SAYISI elde kalmisti.
        #
        # Kaynak: gecen sezonun gerceklesmis hafta sayisi
        # (`spor_toto.history` korpusu). Yeni sezonun takvimi belli
        # olmadigi surece en iyi tahmin odur ve nereden geldigi burada
        # yazili — arayuzde bir sabit olarak degil.
        "planlanan_hafta": _planlanan_hafta(),
        "arindirma": ARINDIRMA_VARSAYILAN,
        # Fiyat saglayici etiketleri BESLEMEDE tasiniyor.
        #
        # Ayni dort cift uc yerde birden yaziliydi: `super_toto_sayfa.py`de
        # IKI KEZ (259 satir arayla) ve `fiyatlar.tsx`te. Ustelik
        # bicimleyiciler AYRISMISTI — Python soneksiz bir anahtarda
        # ("pinnacle") `else` dalina dusup "kapanış" uyduruyordu,
        # TypeScript yalnizca "Pinnacle" diyordu. Besleme zaten CI-kapili
        # (`--kontrol`), yani harita buradan gectiginde elle tutulan kopya
        # kalmiyor.
        "saglayici_adlari": dict(SAGLAYICI_ADLARI),
        # Bicimleyicinin ORNEK CIKTILARI. Harita tek kaynak olsa bile iki
        # dilde iki govde var (`odds.saglayici_adi` ve `saglayiciAdi`) ve
        # ayrisabilirler — nitekim ayrismislardi: soneksiz bir anahtarda
        # Python "kapanış" uyduruyor, TypeScript uydurmuyordu. Bu tablo
        # Python'un GERCEK ciktisidir; `check.mjs` arayuzun onu birebir
        # yeniden urettigini dogrular. Sinir durumlar bilerek listede.
        "saglayici_ornekleri": {
            k: saglayici_adi(k) for k in (
                "pinnacle_kapanis", "pinnacle_acilis", "pinnacle",
                "iddaa", "iddaa_acilis", "bet365nl_kapanis",
                "nesine", "bilinmeyen_kaynak",
            )
        },
        "note": ("backend/data/super_toto altindan uretildi — elle "
                 "duzenlenmez; scripts/super_toto_frontend.py"),
        "weeks": haftalar,
    }


#: Uretilmis JSON metni TEK kaynaktan: `scripts._ortak.metin`. Ayni govde
#: uc betikte birebir yaziliydi ve `--kontrol` bayraklari tam da bu metnin
#: kararliligina dayaniyor.
_metin = metin


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--kontrol", action="store_true",
                    help="yazma, yalnizca dosyanin guncel olup olmadigina bak")
    ap.add_argument("--cikti", default=None)
    a = ap.parse_args(argv)

    yol = Path(a.cikti) if a.cikti else CIKTI
    metin = _metin(uret(a.sezon))

    if a.kontrol:
        mevcut = yol.read_text(encoding="utf-8") if yol.exists() else ""
        if mevcut != metin:
            raise SystemExit(
                f"{yol} guncel degil. Cozum:\n"
                f"  python scripts/super_toto_frontend.py")
        print(f"{yol.name} guncel")
        return

    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(metin, encoding="utf-8")
    print(f"{yol} yazildi ({len(json.loads(metin)['weeks'])} hafta)")


if __name__ == "__main__":
    main()
