"""Çoklu planın **gerçek ikramiye tablolarına** karşı getirisi — sürdürülebilirlik.

`karne.py` bu işi **düz** (tek sistem) plan için yapar ve bütçe merdiveni
₺320–4.860 arasındadır. Görev bütçesi ise ₺210.000/hafta ve oynanan plan
çoklu kupon. Yani *"bu plan parasını çıkarıyor mu"* sorusu bugüne kadar
**görev ölçeğinde hiç ölçülmedi** — ve üç aylık kısıt gevşediği an o soru
kritik hâle geliyor: kâr ölçüt değil, ama **bütçe tükenirse hedef de tükenir.**

    cd backend && python scripts/coklu_karne.py --butce 21000
    cd backend && python scripts/coklu_karne.py --butce 21000 --tavan 729

─── Kademe sayımı bir tahmin değil, tam sayım ────────────────────────────

Bir kupon (kutu) `secimler` taşır: her maç için bir sembol kümesi. Gerçek
sonuç verildiğinde o kutudaki kolonların **kaç tanesinin tam `j` maçı
kaçırdığı** kesin olarak sayılır, üreteç fonksiyonuyla:

* maçta gerçek sembol kümedeyse → `1 + (|küme| − 1)·x`  (biri doğru, kalanı yanlış)
* değilse                        → `|küme|·x`            (hepsi yanlış)

On beş çarpanın çarpımında `x^j`'nin katsayısı, tam `j` kaçaklı kolon
sayısıdır; kademe `15 − j`. Kuponlar **ayrıktır** (ön ek ağacında ayrı
dallar), o yüzden kuponlar üzerinden toplamak çift saymaz — ve bekçi bunu
her hafta sınıyor: kademe sayımlarının toplamı planın kolon sayısına eşit.

─── İki getiri basılıyor ve ikincisi doğru olanı ─────────────────────────

**Ham**: kayıttaki kişi başı ikramiye × bizim o kademedeki kolonumuz. Bu
sayı **iyimserdir** çünkü biz oynamamışken hesaplanmış payı bize de
ödüyormuş gibi yapar.

**Seyrelmiş**: o kademenin havuzu (`kazanan × pay`) bizim kolonlarımız da
eklenerek yeniden bölünür. Müşterek bahsin tanımı budur ve 21.000 kolonluk
bir giriş, küçük kademelerde kazanan sayısını gerçekten oynatır.

Fark, planın ölçeğinin kendi payını ne kadar yediğinin ölçüsüdür.

─── KAZANANSIZ kademe: ilk sürümün hatası ve düzeltmesi ──────────────────

İlk sürüm `havuz = kazanan × pay` yazıyordu ve kazananı **sıfır** olan
kademede bu sıfır veriyordu — yani devir haftalarında (225 haftanın 47'si
15. kademede kazanansız) plan 15/15 tutturmuş olsa bile getirisi **sıfır**
sayılıyordu. Oysa tam tersi: orada tek kazanan biz olurduk.

Düzeltme deponun kendi havuz modelini kullanır (`havuz.hafta_havuzu`):
kazanansız kademenin o haftaki kendi payı `BOLUSUM[kademe] × birim`dir ve
tek kazanan bizsek tamamı bize gelir. Bu bir **ALT SINIR**dır — önceki
haftalardan birikmiş devir o haftanın tablosunda görünmez ve tahmin
edilmez (`havuz.py`nin `devir_giden_kesin: False` kuralı burada da geçerli).

─── Devir haftası bizim haftamız değil ───────────────────────────────────

Betik ayrıca bir çapraz tablo basar: **15. kademede kimsenin bilmediği
hafta** (havuz devrediyor, yani ikramiye en büyük) ile **bizim tutturduğumuz
hafta** aynı hafta mı? Ölçülen: değil, ve rastlantı değil. Bu, projenin
*"tuttuğunuz hafta herkesin tuttuğu haftadır"* bulgusunun
(`KADEME_OLASILIKLARI.md` §6, Spearman −0,843) kupon düzeyindeki karşılığı.

─── Bu bir kâr ölçümü DEĞİL, bir dayanıklılık ölçümü ─────────────────────

Sahibi kâr/zararı açıkça ölçüt saymadı ve bu betik o kararı değiştirmiyor.
Ölçtüğü şey başka: **hedefe kaç hafta dayanabiliriz.** Ufuk kısıtı
gevşediğinde hedefin olasılığı süreyle büyüyor (§3.78: 13 hafta %77,0 → 39
hafta %99,0) ama fatura da süreyle büyüyor. İkisinin oranı bu betikte.
"""
from __future__ import annotations

import argparse
import json
import sys
from math import comb
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.coklu_kiyasi import VARSAYILAN_BUTCE, hafta_probs
from scripts.kademe_analizi import ikramiye_tablolari, tam_haftalar
from spor_toto.coklu import MAC_SAYISI, coklu_plan_serisi
from spor_toto.getiri import KOLON_BEDELI
from spor_toto.havuz import BOLUSUM, arsiv_haftalari, hafta_havuzu

#: Ödeyen kademeler. 11 ve altı ikramiye vermez.
KADEMELER = (15, 14, 13, 12)

#: Varsayılan kupon tavanı — bugün donan kayıt bu (§3.69).
VARSAYILAN_TAVAN = 81


def kademe_sayimi(secimler: Sequence[Sequence[str]],
                  gercek: Sequence[str]) -> dict[int, int]:
    """Bir kutudaki kolonların kademe dağılımı — **tam sayım**.

    Dönen sözlük `kademe -> kolon sayısı`; yalnız ödeyen kademeler değil,
    hepsi (çağıran süzer). Toplamı kutunun kolon sayısına eşittir ve bu,
    bekçinin sınadığı değişmezdir.
    """
    # kat[j] = tam j kaçaklı kolon sayısı
    kat = [1]
    for i, kume in enumerate(secimler):
        n = len(kume)
        dogru_var = gercek[i] in kume
        yeni = [0] * (len(kat) + 1)
        for j, c in enumerate(kat):
            if not c:
                continue
            if dogru_var:
                yeni[j] += c              # gerçek sembol seçildi
                if n > 1:
                    yeni[j + 1] += c * (n - 1)
            else:
                yeni[j + 1] += c * n      # hepsi yanlış
        kat = yeni
    return {MAC_SAYISI - j: c for j, c in enumerate(kat) if c}


def hafta_getirisi(kuponlar: Sequence[Any], gercek: Sequence[str],
                   tablo: dict[int, dict[str, Any]],
                   birim: float | None = None) -> dict[str, Any]:
    """Bir haftanın ham ve seyrelmiş getirisi, kademe kademe.

    `birim` verilirse kazanansız kademeler de fiyatlanır (o kademenin kendi
    payı `BOLUSUM × birim`, tek kazanan biz oluruz) — **alt sınır**.
    """
    bizim: dict[int, int] = {}
    toplam_kolon = 0
    for k in kuponlar:
        for kademe, adet in kademe_sayimi(k.secimler, gercek).items():
            bizim[kademe] = bizim.get(kademe, 0) + adet
            toplam_kolon += adet

    ham = seyrelmis = 0.0
    devirden = 0.0
    for kademe in KADEMELER:
        adet = bizim.get(kademe, 0)
        satir = tablo.get(kademe)
        if not adet or not satir:
            continue
        pay = float(satir["prize"])
        kazanan = int(satir["winners"])
        if kazanan > 0:
            ham += adet * pay
            havuz = kazanan * pay
            seyrelmis += adet * (havuz / (kazanan + adet))
        elif birim:
            # Kazanansız kademe: o haftanın kendi payı ileri devrediyordu;
            # biz oynasaydık tek kazanan biz olurduk. ALT SINIR.
            havuz = BOLUSUM[kademe] * birim
            ham += havuz
            seyrelmis += havuz
            devirden += havuz
    return {"kolon": toplam_kolon, "kademeler": bizim, "ham": ham,
            "seyrelmis": seyrelmis, "devirden": devirden}


def kos(butce: int, tavan: int = VARSAYILAN_TAVAN) -> dict[str, Any]:
    """114 tam hafta: maliyet, ham getiri, seyrelmiş getiri, ROI."""
    haftalar = tam_haftalar(ikramiye_tablolari())
    tablolar = ikramiye_tablolari()
    #: (sezon, hafta) -> bölüşümün 1 birimi; kazanansız kademeyi fiyatlar.
    birimler: dict[tuple[str, int], float] = {}
    for h in arsiv_haftalari():
        hv = hafta_havuzu(h.get("payout"))
        if hv:
            birimler[(h["season_key"], h["week"])] = float(hv["birim"])
    satirlar: list[dict[str, Any]] = []

    for sezon, hafta, lst in haftalar:
        probs, gercek = hafta_probs(lst)
        plan = coklu_plan_serisi(probs, butce, (tavan,))[tavan]
        g = hafta_getirisi(plan.kuponlar, gercek, tablolar[(sezon, hafta)],
                           birimler.get((sezon, hafta)))
        assert g["kolon"] == plan.kolon, (
            f"{sezon}/{hafta}: kademe sayimi {g['kolon']} != plan "
            f"{plan.kolon} — kuponlar AYRIK degil")
        satirlar.append({
            "sezon": sezon, "hafta": hafta,
            "kolon": plan.kolon, "maliyet": plan.kolon * KOLON_BEDELI,
            "onbes": g["kademeler"].get(15, 0),
            "en_iyi_kacak": MAC_SAYISI - max(g["kademeler"]),
            "devir": int(tablolar[(sezon, hafta)][15]["winners"]) == 0,
            "ham": g["ham"], "seyrelmis": g["seyrelmis"],
            "devirden": g["devirden"],
        })

    # Çapraz tablo: devir haftası (kimse 15 bilmemiş) ↔ bizim isabetimiz.
    devir_h = [r for r in satirlar if r["devir"]]
    tutan = [r for r in satirlar if r["onbes"]]
    kesisim = sum(1 for r in devir_h if r["onbes"])
    n_h, n_d, n_t = len(satirlar), len(devir_h), len(tutan)
    # Bağımsızlık altında kesişimin bu kadar KÜÇÜK olma olasılığı
    # (hipergeometrik alt kuyruk) — ön kayıtlı bir sınav değil, betimleyici.
    p_alt = sum(comb(n_d, i) * comb(n_h - n_d, n_t - i) / comb(n_h, n_t)
                for i in range(kesisim + 1)
                if 0 <= n_t - i <= n_h - n_d)

    maliyet = sum(float(r["maliyet"]) for r in satirlar)
    ham = sum(float(r["ham"]) for r in satirlar)
    sey = sum(float(r["seyrelmis"]) for r in satirlar)
    n = len(satirlar)
    return {
        "hafta": n, "butce": butce, "tavan": tavan,
        "maliyet": maliyet, "ham": ham, "seyrelmis": sey,
        "roi_ham": ham / maliyet if maliyet else 0.0,
        "roi_seyrelmis": sey / maliyet if maliyet else 0.0,
        "hafta_basi_maliyet": maliyet / n if n else 0.0,
        "hafta_basi_net": (sey - maliyet) / n if n else 0.0,
        "devirden": sum(float(r["devirden"]) for r in satirlar),
        "devir_hafta": sum(1 for r in satirlar if r["devirden"] > 0),
        "devir_capraz": {
            "devir_hafta": n_d, "tutan_hafta": n_t, "kesisim": kesisim,
            "beklenen": (n_d * n_t / n_h) if n_h else 0.0, "p_alt": p_alt,
            "kacak_devir": (sum(int(r["en_iyi_kacak"]) for r in devir_h)
                            / n_d) if n_d else 0.0,
            "kacak_normal": (sum(int(r["en_iyi_kacak"]) for r in satirlar
                                 if not r["devir"]) / (n_h - n_d))
            if n_h - n_d else 0.0,
        },
        "onbes_hafta": sum(1 for r in satirlar if r["onbes"]),
        "odeyen_hafta": sum(1 for r in satirlar if r["seyrelmis"] > 0),
        "satirlar": satirlar,
    }


def bas(c: dict[str, Any]) -> None:
    print(f"tam hafta: {c['hafta']}   butce: {c['butce']:,} kolon   "
          f"kupon tavani: {c['tavan']}")
    print(f"15/15 tutturulan hafta: {c['onbes_hafta']}/{c['hafta']}   "
          f"herhangi bir odeme alan hafta: {c['odeyen_hafta']}/{c['hafta']}\n")
    print(f"{'':>18} {'toplam TL':>18} {'ROI':>8}")
    print(f"{'maliyet':>18} {c['maliyet']:>18,.0f} {'':>8}")
    print(f"{'ham getiri':>18} {c['ham']:>18,.0f} {c['roi_ham']:>8.3f}")
    print(f"{'seyrelmis getiri':>18} {c['seyrelmis']:>18,.0f} "
          f"{c['roi_seyrelmis']:>8.3f}   <- dogru olan")
    print(f"\n  ^ getirinin {c['devirden']:,.0f} TL'si KAZANANSIZ kademeden "
          f"({c['devir_hafta']} hafta) — ALT SINIR:")
    print("    onceki haftalardan birikmis devir tabloda gorunmez, tahmin")
    print("    edilmez (havuz.py: devir_giden_kesin = False).")
    print(f"\nhafta basi maliyet {c['hafta_basi_maliyet']:>14,.0f} TL")
    print(f"hafta basi NET     {c['hafta_basi_net']:>14,.0f} TL "
          f"(seyrelmis getiri - maliyet)")
    print("\nUFUK FATURASI (hafta basi net x hafta):")
    for h in (13, 26, 39, 52):
        print(f"  {h:>3} hafta  net {c['hafta_basi_net'] * h:>16,.0f} TL   "
              f"harcanan {c['hafta_basi_maliyet'] * h:>14,.0f} TL")
    d = c["devir_capraz"]
    print(f"\nDEVIR HAFTASI BIZIM HAFTAMIZ DEGIL")
    print(f"  15'i kimsenin bilmedigi hafta (havuz devrediyor): "
          f"{d['devir_hafta']}/{c['hafta']}")
    print(f"  onlarin kacinda biz tutturduk               : "
          f"{d['kesisim']}   (bagimsizlik altinda beklenen "
          f"{d['beklenen']:.2f}, p = {d['p_alt']:.4f})")
    print(f"  en iyi kolonun ortalama kacagi: devir haftasi "
          f"{d['kacak_devir']:.2f}  <->  normal {d['kacak_normal']:.2f}")
    print("  Yani ikramiyenin EN BUYUK oldugu haftalar, bizim de (ve")
    print("  herkesin) kacirdigi haftalar. Kupon duzeyinde 'tutturdugunuz")
    print("  hafta herkesin tutturdugu haftadir' (Spearman -0,843).")
    print("\n'ham' KAYITTAKI kisi basi ikramiyeyi bize de oderdi — iyimser.")
    print("'seyrelmis' o kademenin havuzunu BIZIM kolonlarimizla yeniden")
    print("boler; musterek bahsin tanimi budur ve dogru olan odur.")
    print("Bu bir KAR olcumu degil DAYANIKLILIK olcumu: kar olcut degil,")
    print("ama butce tukenirse hedef de tukenir.")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="kolon butcesi (varsayilan 3^9 = 19.683)")
    ap.add_argument("--tavan", type=int, default=VARSAYILAN_TAVAN,
                    help="kupon tavani (varsayilan 81)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    c = kos(a.butce, a.tavan)
    if a.json:
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return
    bas(c)


if __name__ == "__main__":  # pragma: no cover
    main()
