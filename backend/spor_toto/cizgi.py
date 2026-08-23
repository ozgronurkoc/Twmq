"""Kapanış çizgisi verimliliği (A1) — tahmin ekseninin en belirleyici deneyi.

Yol haritası (§6.2 A1) bu ölçümü "tek deneyde en çok bilgi veren" iş diye
işaretledi. Sebebi şu: piyasa maç öncesinde iki kez konuşur — bir **açılış**
çizgisi, bir de **kapanış** çizgisi. Aradaki fark, bahisler geldikçe piyasanın
fikrini değiştirmesidir. Bu farkı ölçmek iki ayrı soruyu birden cevaplar:

**Soru 1 — piyasa bilgiyi soğuruyor mu?** Kapanış açılışı sistematik olarak
yeniyorsa, aradan geçen sürede gelen bilgi (kadro, sakatlık, hava, para) fiyata
işleniyor demektir. Bu, piyasanın *çalıştığının* doğrudan kanıtıdır.

**Soru 2 — kapanışın kendisi verimli mi?** Hareketin yönü, kapanışın ötesinde
hâlâ bilgi taşıyor mu? İki olasılık var ve ikisi zıt:

    momentum   hareket devam ediyor → kapanış hareketi eksik fiyatlamış
    aşırı tepki hareket geri geliyor → kapanış hareketi fazla fiyatlamış

İkisi de yoksa kapanış **verimlidir**: söylenecek her şey fiyata girmiştir ve
aynı veriyle daha fazla aramak boşunadır. Bu, A4'ün (b) şıkkına giden en güçlü
tek kanıttır — ve "model bulamadık" demekten farklı bir şeydir: piyasanın kendi
hareketi bile kendini yenemiyorsa, sorun modelde değil veridedir.

**Ölçümün tek zor kısmı kesittir.** Açılış tahmincisiyle kapanış tahmincisi
*aynı maçlarda* ölçülmezse, aradaki fark hareketi değil örneklem farkını ölçer.
Bu yüzden `kesit()` yalnızca ikisi de tam olan maçları alır (31.099 / 31.103)
ve haftanın `probs` alanını **açıkça kapanışla** doldurur — `oran_*` sütununun
hangi ucu tercih ettiğine bağlı kalmaz.

Ayrıca hareket, ham oran üzerinden değil **marj arındırılmış olasılık**
üzerinden ölçülür (bkz. `egitim.cizgi_hareketi`): ham oranın hareketi,
piyasanın fikir değiştirmesiyle bahisçinin marjını değiştirmesini karıştırır.

Sonucu okumak için: `python -m spor_toto.cizgi`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .egitim import korpus_haftalari
from .history import SYMBOLS
from .predict import Girdi, Olasilik, PiyasaTahminci, Tahminci

#: Hareket büyüklüğü bantları — |ln p_kapanış − ln p_açılış| toplamı üzerinden.
#: Eşikler kaba ve **ölçüm sonucuna bakılmadan** seçildi: sonuca göre seçilseydi
#: "şu bantta sinyal var" bulgusu bandın kendisinden gelirdi.
HAREKET_BANTLARI: Sequence[float] = (0.05, 0.15, 0.30)


def kesit(sezonlar_: Optional[Sequence[str]] = None,
          yol: Optional[str] = None) -> List[Girdi]:
    """A1 kesiti: açılış+kapanış çifti tam olan maçlar, kapanış `probs` olarak.

    İki şey burada garanti altına alınır:

    1. **Aynı maçlar.** Çifti olmayan maç elenir; açılış ve kapanış tahmincileri
       böylece tek bir kesitte, maç maç eşleşerek ölçülür.
    2. **`probs` = kapanış, açıkça.** `korpus_haftalari` bu alanı `oran_*`
       sütunundan doldurur ve o sütun kapanışı *tercih eder* — bugün ikisi
       aynı çıkıyor, ama ölçüm bir tercihin yan etkisine yaslanmamalı.
    """
    haftalar = korpus_haftalari(sezonlar_=sezonlar_, yol=yol, cizgi_gerekli=True)
    # Hafta kaydının ÜSTÜNE YAZILMAZ, kopyası alınır. `korpus_haftalari`
    # önbellekli: aynı kayıt başka çağıranlara da gidiyor ve buradaki
    # `probs` (kapanış) onların gördüğü `probs`u (oran_* sütunu) sessizce
    # değiştirirdi. Sessiz olurdu çünkü ikisi bugün aynı çıkıyor — ta ki
    # bir gün çıkmayana kadar. Bekçi:
    # `test_egitim.py::test_korpus_haftalari_paylasilan_kaydi_korur`.
    out: List[Girdi] = []
    for hafta in haftalar:
        probs: List[Olasilik] = []
        for ozellik in hafta["ozellikler"]:
            kapanis = ozellik.get("kapanis_probs")
            if not kapanis:  # pragma: no cover - cizgi_gerekli bunu engeller
                raise ValueError("kesitte kapanis orani olmayan mac var")
            probs.append(dict(kapanis))
        out.append({**hafta, "probs": probs})
    return out


class AcilisTahminci(Tahminci):
    """Marj arındırılmış **açılış** oranı — piyasanın ilk sözü.

    `PiyasaTahminci`nin ikizi; tek farkı çizginin hangi ucunu okuduğu. Aynı
    kesitte ölçüldüğünde ikisi arasındaki fark, piyasanın maç öncesinde
    öğrendiği her şeydir.

    Referans listesine (`predict.referans_fabrikalar`) **girmez**: kupon
    haftaları açılış oranı taşımaz ve orada bu tahminci düzgün dağılıma
    düşerdi. A1 kesitinin dışında anlamı yoktur.
    """

    ad = "acilis"
    aciklama = "Marj arındırılmış açılış oranı (football-data)"

    def tahmin(self, hafta: Girdi) -> List[Olasilik]:
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        out: List[Olasilik] = []
        for ozellik in hafta.get("ozellikler") or []:
            acilis = ozellik.get("acilis_probs")
            out.append(dict(acilis) if acilis else dict(esit))
        if not out:  # kupon haftalari: acilis tasinmaz
            out = [dict(esit) for _ in hafta["probs"]]
        return out


# ─── betimleyici ölçüm ────────────────────────────────────────────────────────

def _bant_adi(buyukluk: float) -> str:
    """Hareket büyüklüğünün bandı."""
    for esik in HAREKET_BANTLARI:
        if buyukluk < esik:
            return f"<{esik:.2f}"
    return f">={HAREKET_BANTLARI[-1]:.2f}"


def hareket_ozeti(haftalar: Optional[Sequence[Girdi]] = None) -> Dict[str, Any]:
    """Çizgi ne kadar oynuyor ve oynadığı yön tutuyor mu — betimleyici.

    Bu bir tahminci değil, **olgu**: hareketin yönü ile sonucun ilişkisi.
    Karar buradan çıkmaz (karar `rapor()`un güven aralığındadır), ama bir
    kontrol sağlar: hareket hiç yoksa ya da yönü sonuçla hiç ilişkili değilse,
    A1'in "geçmedi" sonucu ölçümün bozukluğundan da gelebilirdi. İkisini
    ayırt etmek gerekir — T5'te aynı gerekçeyle ham form sinyali doğrulanmıştı.

    Dönen `yon` bloğu şunu sorar: hareketin en çok **lehine** olduğu sembol,
    gerçekleşen sonuç mu? Piyasa bilgiyi soğuruyorsa bu oran, o sembolün
    açılıştaki payından yüksek çıkmalıdır.
    """
    if haftalar is None:
        haftalar = kesit()

    bantlar: Dict[str, Dict[str, float]] = {}
    n_toplam = 0
    lehine_tuttu = 0
    aleyhine_tuttu = 0
    buyukluk_toplam = 0.0

    for hafta in haftalar:
        for i, kod in enumerate(hafta["results"]):
            ozellik = hafta["ozellikler"][i]
            hareket = {s: float(ozellik.get(f"hareket_{s}") or 0.0) for s in SYMBOLS}
            buyukluk = sum(abs(v) for v in hareket.values())
            n_toplam += 1
            buyukluk_toplam += buyukluk

            lehine = max(hareket, key=lambda s: hareket[s])
            aleyhine = min(hareket, key=lambda s: hareket[s])
            if kod == lehine:
                lehine_tuttu += 1
            if kod == aleyhine:
                aleyhine_tuttu += 1

            bant = bantlar.setdefault(_bant_adi(buyukluk),
                                      {"n": 0.0, "lehine": 0.0, "aleyhine": 0.0})
            bant["n"] += 1
            bant["lehine"] += 1.0 if kod == lehine else 0.0
            bant["aleyhine"] += 1.0 if kod == aleyhine else 0.0

    def _oran(pay: float, payda: float) -> Optional[float]:
        return round(pay / payda, 4) if payda else None

    return {
        "n_mac": n_toplam,
        "ortalama_buyukluk": round(buyukluk_toplam / n_toplam, 4) if n_toplam else None,
        "yon": {
            "lehine_tuttu": _oran(lehine_tuttu, n_toplam),
            "aleyhine_tuttu": _oran(aleyhine_tuttu, n_toplam),
            "not": ("hareketin en cok lehine oldugu sembol tuttu mu; "
                    "soguruma varsa lehine > aleyhine"),
        },
        "bantlar": {
            ad: {"n": int(b["n"]),
                 "lehine_tuttu": _oran(b["lehine"], b["n"]),
                 "aleyhine_tuttu": _oran(b["aleyhine"], b["n"])}
            for ad, b in sorted(bantlar.items())
        },
    }


def hareket_katsayisi(haftalar: Optional[Sequence[Girdi]] = None) -> Dict[str, Any]:
    """Modelin hareketi ne kadar uzatmak istediği — A1'in en okunaklı sayısı.

    `kalibre_hareket` iki katsayı taşır ve ikisi birlikte tek bir cümle söyler.
    Logit şöyle kurulur:

        z_s = β·ln p_kapanış,s  +  γ·(ln p_kapanış,s − ln p_açılış,s)  + …
            = (β+γ)·ln p_kapanış,s  −  γ·ln p_açılış,s  + …

    Yani **γ/β, kapanışın ötesine ne kadar uzatılacağıdır.** %0 = kapanış son
    sözdür. Pozitif = hareket eksik fiyatlanmış (momentum), negatif = fazla
    fiyatlanmış (aşırı tepki).

    Bu oran, Brier farkının veremediğini verir: fark sıfıra yakın çıkınca
    "model harekete bakmadı mı, yoksa baktı da söyleyecek bir şey mi bulamadı?"
    sorusu açık kalır. Katsayı ikisini ayırır.

    Katsayı **bütün kesitte** uydurulur; bu bir tahmin değil, bir tanılamadır.
    Karar `rapor()`un dışarıda bırakmalı ölçümündedir.
    """
    from .recalibrate import KalibreTahminci

    if haftalar is None:
        haftalar = kesit()
    tahminci = KalibreTahminci("hareket")
    tahminci.egit(haftalar)
    katsayilar = tahminci.katsayilar
    if not katsayilar:  # pragma: no cover - bos kesit
        return {"beta": None, "gama": None, "uzatma": None}
    beta, gama = katsayilar[0], katsayilar[-1]
    return {
        "beta": round(beta, 5),
        "gama": round(gama, 5),
        "uzatma": round(gama / beta, 5) if beta else None,
        "not": ("uzatma = γ/β; kapanisin otesine uzatilan oran. "
                "0 = kapanis son soz, + = momentum, − = asiri tepki"),
    }


# ─── karar koşumu ─────────────────────────────────────────────────────────────

def rapor(sezonlar_: Optional[Sequence[str]] = None,
          yol: Optional[str] = None) -> Dict[str, Any]:
    """A1'in iki sorusunu tek koşumda ölç.

    Koşan tahminciler ve her birinin cevapladığı soru:

        piyasa           kapanış çizgisi — **referans**
        acilis           açılış çizgisi  — soru 1: kapanış bunu geçiyor mu?
        kalibre_form     hareketsiz üst basamak — soru 2'nin taban çizgisi
        kalibre_hareket  form + hareket        — soru 2: hareket ekliyor mu?

    `kalibre_form` koşuma **bu yüzden** girer: `kalibre_hareket` kademenin en
    üst basamağıdır ve altındaki her şeyi içerir. Aradaki farkı harekete
    atfedebilmek için bir alt basamağın aynı kesitte ölçülmesi gerekir.

    Ölçüm **sezon dışarıda bırakmalıdır** (`evaluate.sezon_anahtari`): aynı
    sezonun başka haftaları da bilgi sızdırır, hafta dışarıda bırakmak yetmez.
    """
    from .evaluate import karsilastir, sezon_anahtari
    from .recalibrate import KalibreTahminci

    haftalar = kesit(sezonlar_=sezonlar_, yol=yol)
    fabrikalar = [
        PiyasaTahminci,
        AcilisTahminci,
        lambda: KalibreTahminci("form"),
        lambda: KalibreTahminci("hareket"),
    ]
    sonuc = karsilastir(fabrikalar, haftalar=haftalar, grup=sezon_anahtari)
    sonuc["hareket"] = hareket_ozeti(haftalar)
    sonuc["katsayi"] = hareket_katsayisi(haftalar)
    sonuc["soru"] = {
        "1_soguruma": ("kapanis acilisi geciyor mu — `acilis` satirinin farki "
                       "POZITIF ve araligi tamamen sifirin ustundeyse evet"),
        "2_verimlilik": ("hareket kapanisin otesinde bilgi tasiyor mu — "
                         "`kalibre_hareket` `kalibre_form`u gecmiyorsa hayir, "
                         "kapanis verimlidir"),
    }
    return sonuc


def _yazdir(sonuc: Dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print(f"A1 kesiti: {sonuc['n_hafta']} hafta · {sonuc['n_mac']} maç "
          f"· referans: {sonuc['referans']}")
    print(f"{'tahminci':<20} {'brier':>8} {'log':>8} {'fark':>9} "
          f"{'%95 aralık':>18}  geçti")
    for s in sonuc["tahminciler"]:
        f = s["fark"]
        aralik = f"[{f['alt']:+.4f}, {f['ust']:+.4f}]" if f else ""
        fark = f"{f['fark']:+.4f}" if f else ""
        gecti = "" if s["gecti"] is None else ("EVET" if s["gecti"] else "hayir")
        print(f"{s['ad']:<20} {s['brier']:>8.4f} {s['log_kaybi']:>8.4f} "
              f"{fark:>9} {aralik:>18}  {gecti}")

    h = sonuc["hareket"]
    print(f"\nhareket: ortalama büyüklük {h['ortalama_buyukluk']}"
          f" · lehine tuttu %{100 * (h['yon']['lehine_tuttu'] or 0):.1f}"
          f" · aleyhine tuttu %{100 * (h['yon']['aleyhine_tuttu'] or 0):.1f}")
    print(f"{'bant':<10} {'n':>7} {'lehine':>9} {'aleyhine':>9}")
    for ad, b in h["bantlar"].items():
        print(f"{ad:<10} {b['n']:>7} {b['lehine_tuttu']:>9.4f} "
              f"{b['aleyhine_tuttu']:>9.4f}")

    k = sonuc["katsayi"]
    print(f"\nkatsayı: β={k['beta']} γ={k['gama']} → kapanışın ötesine uzatma "
          f"%{100 * (k['uzatma'] or 0):.2f}")


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    _yazdir(rapor())
