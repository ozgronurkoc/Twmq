"""Bahisçi anlaşmazlığı (A2) — kolektifin içindeki dağılım bilgi mi?

A1 *"piyasa kolektif olarak doğru mu"* diye sordu ve cevap evetti: kapanış
açılışı geçiyor, hareketin ötesinde bir şey kalmıyor. Ama A1 baştan sona
**ortalama** üzerinden ölçtü (`Avg` = bütün bahisçilerin ortalaması).

Ortalamanın etrafındaki **dağılım** ayrı bir büyüklüktür ve ortalamanın kendi
değerinde görünmez. İki bağımsız soru doğuruyor:

**Soru 1 — kolektifin içinde daha iyi bir üye var mı?** Pinnacle'ın "keskin"
olduğu bahis literatürünün en bilinen iddiasıdır; düşük marjla çalışır ve
büyük bahisleri kabul eder. Doğruysa `PS` tek başına `Avg`'yi geçmeli.

**Soru 2 — anlaşmazlığın kendisi bilgi mi?** Bahisçiler ayrıştığında
kolektifin son sözü daha az güvenilir olabilir. Bu bir **yön** değil
**sıcaklık** sorusudur: "1 mi 2 mi" değil, "ne kadar emin olmalıyım".

İkisi bağımsız olarak yanlış çıkabilir — ve bu yüzden ayrı ayrı ölçülüyorlar.

**Kaynak seçimi ölçümü belirliyor ve gerekçesi taşınıyor.** football-data yedi
tekil bahisçi veriyor ama kapsamaları sezona göre değişiyor: `BW` 2425'te
%63'e, `WH` %76'ya düşüyor, `BF`/`1XB`/`BFE` yalnızca 2425'te var. Hepsini
isteyen bir filtre kesitin **sezon dengesini bozar** ve sezon dışarıda
bırakmalı ölçümde bu sessiz bir yanlılıktır. Taşınan dört kaynak
(`B365C`, `PSC`, `MaxC`, `AvgC`) dört sezonda da ~%100 — kesit 31.100 maç.

Aynı gerekçenin ikinci yüzü `egitim.bahisci_ayrismasi`'nde: `Max/Avg` açığı
daha geniş bir anlaşmazlık ölçüsüdür ama bahisçi sayısına duyarlıdır ve
sezonlara göre %20 sürükleniyor. Model yalnızca sabit `B365`↔`PS` çiftini
görür; sürüklenen özellik modele anlaşmazlık değil **sezon kimliği** öğretir.

Sonucu okumak için: `python -m spor_toto.bahisci`.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .egitim import korpus_haftalari
from .history import SYMBOLS
from .ortak import bant_adi, favori_dilimi
from .predict import Girdi, Olasilik, PiyasaTahminci, Tahminci

#: Kafa kafaya ölçülen tekil bahisçiler. `b_Max`/`b_Avg` burada **yok**:
#: `b_Avg` referansın kendisi, `b_Max` ise bir bahisçi değil her ayakta en iyi
#: fiyatı toplayan bir zarf — olasılık olarak okunamaz (toplamı 1'in altında
#: kalır, marj arındırma bunu yapay biçimde düzeltirdi).
TEKIL_BAHISCILER: Sequence[str] = ("b_B365", "b_PS")

#: Anlaşmazlık bantları — ½·Σ|Δp| üzerinden. Eşikler kaba ve **ölçüm
#: sonucuna bakılmadan** seçildi (`cizgi.HAREKET_BANTLARI` ile aynı gerekçe).
AYRISMA_BANTLARI: Sequence[float] = (0.01, 0.02, 0.04)

#: Çapraz tabloda bir hücrenin gösterilmesi için gereken en az maç. Altında
#: hücre ortalaması kendi gürültüsünü ölçer ve karışmayı açmak yerine
#: bulanıklaştırır.
AZ_HUCRE = 100


def kesit(sezonlar_: Sequence[str] | None = None,
          yol: str | None = None) -> list[Girdi]:
    """A2 kesiti: bahisçi dörtlüsü tam olan maçlar, `Avg` `probs` olarak.

    `cizgi.kesit` ile aynı iki garanti: **aynı maçlar** (dörtlüsü olmayan maç
    elenir, böylece tekil bahisçiler ve kolektif maç maç eşleşir) ve
    **`probs` = `Avg` kapanışı, açıkça.** İkincisi önemli: `oran_*` sütunu
    kapanışı *tercih eder* ve bugün pratikte `AvgC` çıkıyor, ama bir
    karşılaştırmanın referansı bir tercihin yan etkisi olmamalı.
    """
    haftalar = korpus_haftalari(sezonlar_=sezonlar_, yol=yol,
                                bahisci_gerekli=True)
    # Hafta kaydının ÜSTÜNE YAZILMAZ, kopyası alınır — gerekçe `cizgi.kesit`
    # ile aynı: `korpus_haftalari` önbellekli, kayıt paylaşılıyor.
    out: list[Girdi] = []
    for hafta in haftalar:
        probs: list[Olasilik] = []
        for ozellik in hafta["ozellikler"]:
            kolektif = (ozellik.get("bahisci_probs") or {}).get("b_Avg")
            if not kolektif:  # pragma: no cover - bahisci_gerekli bunu engeller
                raise ValueError("kesitte bahisci dortlusu olmayan mac var")
            probs.append(dict(kolektif))
        out.append({**hafta, "probs": probs})
    return out


class BahisciTahminci(Tahminci):
    """Tek bir bahisçinin marj arındırılmış kapanış oranı.

    `PiyasaTahminci`nin ikizi; tek farkı kolektifin ortalamasını değil **tek
    bir üyesini** okuması. A2 kesitinde ölçüldüğünde aradaki fark, o üyenin
    kolektiften daha iyi olup olmadığıdır.

    Referans listesine (`predict.referans_fabrikalar`) girmez: kupon haftaları
    bahisçi kırılımı taşımaz ve orada düzgün dağılıma düşerdi.
    """

    def __init__(self, kod: str = "b_PS") -> None:
        self.kod = kod
        self.ad = kod.replace("b_", "").lower()
        self.aciklama = f"Marj arındırılmış kapanış oranı ({kod})"

    def tahmin(self, hafta: Girdi) -> list[Olasilik]:
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        out: list[Olasilik] = []
        for ozellik in hafta.get("ozellikler") or []:
            blok = (ozellik.get("bahisci_probs") or {}).get(self.kod)
            out.append(dict(blok) if blok else dict(esit))
        if not out:  # kupon haftalari: bahisci kirilimi tasinmaz
            out = [dict(esit) for _ in hafta["probs"]]
        return out


def tekil_fabrikalar() -> list[Any]:
    """Her tekil bahisçi için bir fabrika."""
    return [(lambda k=k: BahisciTahminci(k)) for k in TEKIL_BAHISCILER]


# ─── betimleyici ölçüm ────────────────────────────────────────────────────────

def _bant_adi(ayrisma: float) -> str:
    """Ayrismanin bandi — genel bantlama `ortak.bant_adi`de."""
    return bant_adi(ayrisma, AYRISMA_BANTLARI)


#: `disari` ile birebir ayniydi (orada bir yorum bunu itiraf ediyordu);
#: tek kaynak artik `ortak`.
_favori_dilimi = favori_dilimi


def ayrisma_ozeti(haftalar: Sequence[Girdi] | None = None) -> dict[str, Any]:
    """Anlaşmazlık arttıkça kolektif gerçekten kötüleşiyor mu — betimleyici.

    **Sağlama, bulgu değil.** T5 ve A1'de aynı disiplin uygulanmıştı: bir
    yokluk iddiasını yorumlamadan önce ham sinyali doğrula.

    Burada iki tablo birden döner ve **ikincisi olmadan birincisi
    yanıltıcıdır.** Ham tablo anlaşmazlık arttıkça kolektifin Brier'inin
    *düştüğünü* gösterir — sanki anlaşmazlık doğruluk müjdeliyormuş gibi. Ama
    aynı satırda `ort_p_favori` de yükselir: bahisçiler, **favorinin belirgin
    olduğu maçlarda** daha çok ayrışıyor ve o maçların Brier'i zaten
    mekanik olarak düşüktür (0,85 olasılıklı bir favori tuttuğunda Brier ~0,05,
    üç yönlü bir maçta ~0,66).

    `favori_sabit` bu karışmayı açar: favori gücü dilim içinde sabitlendiğinde
    ilişki **kayboluyor mu?** Kayboluyorsa ham sinyal hiç yoktu ve kademenin
    sıfır çıkması bunun tekrarıdır, ayrı bir bulgu değil.

    Bu, T5 ve A1'in nullundan **farklı bir null**: orada ham sinyal gerçekti
    ve piyasa onu fiyatlamıştı; burada ham sinyalin kendisi bir yanılsama.

    `en_iyi_prim` yalnızca **sürüklenmesini göstermek için** raporlanır:
    sezona göre kayan bir özelliğin neden modele verilmediği sayıyla durur.
    """
    from .evaluate import brier

    if haftalar is None:
        haftalar = kesit()

    bantlar: dict[str, dict[str, float]] = {}
    capraz: dict[str, dict[str, dict[str, float]]] = {}
    sezon_prim: dict[str, list[float]] = {}
    sezon_ayrisma: dict[str, list[float]] = {}

    for hafta in haftalar:
        sezon = hafta.get("sezon") or "?"
        for i, kod in enumerate(hafta["results"]):
            ozellik = hafta["ozellikler"][i]
            probs = hafta["probs"][i]
            ayrisma = float(ozellik.get("ayrisma") or 0.0)
            b = brier(probs, kod)
            ad = _bant_adi(ayrisma)

            sezon_ayrisma.setdefault(sezon, []).append(ayrisma)
            sezon_prim.setdefault(sezon, []).append(
                float(ozellik.get("en_iyi_prim") or 0.0))

            bant = bantlar.setdefault(ad, {"n": 0.0, "brier": 0.0, "pfav": 0.0})
            bant["n"] += 1
            bant["brier"] += b
            bant["pfav"] += max(probs.values()) if probs else 0.0

            hucre = capraz.setdefault(_favori_dilimi(probs), {}).setdefault(
                ad, {"n": 0.0, "brier": 0.0})
            hucre["n"] += 1
            hucre["brier"] += b

    def _ort(degerler: Sequence[float]) -> float | None:
        return round(sum(degerler) / len(degerler), 4) if degerler else None

    return {
        "n_mac": sum(len(h["results"]) for h in haftalar),
        "bantlar": {
            ad: {"n": int(b["n"]),
                 "kolektif_brier": round(b["brier"] / b["n"], 4),
                 "ort_p_favori": round(b["pfav"] / b["n"], 4)}
            for ad, b in sorted(bantlar.items())
        },
        "favori_sabit": {
            dilim: {ad: {"n": int(h["n"]),
                         "kolektif_brier": round(h["brier"] / h["n"], 4)}
                    for ad, h in sorted(hucreler.items()) if h["n"] >= AZ_HUCRE}
            for dilim, hucreler in sorted(capraz.items())
        },
        "sezona_gore": {
            sezon: {"ayrisma": _ort(sezon_ayrisma[sezon]),
                    "en_iyi_prim": _ort(sezon_prim[sezon])}
            for sezon in sorted(sezon_ayrisma)
        },
        "not": ("ham `bantlar` tablosu KARISIK: ayrisma ile favori gucu "
                "birlikte artiyor. `favori_sabit` karismayi acar — iliski "
                "orada kayboluyorsa ham sinyal hic yoktu. "
                "`en_iyi_prim` surukleniyor (bahisci sayisina duyarli), "
                "modele yalnizca `ayrisma` verilir"),
    }


def dagilim_katsayisi(haftalar: Sequence[Girdi] | None = None) -> dict[str, Any]:
    """Model anlaşmazlığa göre güvenini ne kadar kısıyor — A2'nin okunaklı sayısı.

    `kalibre_dagilim`ın logiti `z_s = (β + δ·ayrisma)·ln p_s` biçimindedir.
    `δ·ayrisma`, β'nın yanında ne kadar yer kaplıyor? Ortalama anlaşmazlıkta
    **δ·ortalama_ayrisma / β**, kolektife duyulan güvenin yüzde kaç
    kısıldığıdır.

    Brier farkının veremediğini verir: fark sıfıra yakın çıkınca "model
    anlaşmazlığa bakmadı mı, yoksa baktı da söyleyecek bir şey mi bulamadı?"
    sorusu açık kalırdı.
    """
    from .recalibrate import KalibreTahminci

    if haftalar is None:
        haftalar = kesit()
    tahminci = KalibreTahminci("dagilim")
    tahminci.egit(haftalar)
    katsayilar = tahminci.katsayilar
    if not katsayilar:  # pragma: no cover - bos kesit
        return {"beta": None, "delta": None, "kisma": None}

    beta, delta = katsayilar[0], katsayilar[-1]
    ayrismalar = [float(o.get("ayrisma") or 0.0)
                  for h in haftalar for o in h["ozellikler"]]
    ortalama = sum(ayrismalar) / len(ayrismalar) if ayrismalar else 0.0
    return {
        "beta": round(beta, 5),
        "delta": round(delta, 5),
        "ortalama_ayrisma": round(ortalama, 5),
        "kisma": round(delta * ortalama / beta, 5) if beta else None,
        "not": ("kisma = δ·ortalama_ayrisma/β; ortalama anlasmazlikta "
                "kolektife duyulan guvenin kisilma orani. "
                "0 = anlasmazlik bir sey soylemiyor, − = guven azaltiliyor"),
    }


# ─── karar koşumu ─────────────────────────────────────────────────────────────

def rapor(sezonlar_: Sequence[str] | None = None,
          yol: str | None = None) -> dict[str, Any]:
    """A2'nin iki sorusunu tek koşumda ölç.

    Koşan tahminciler ve her birinin cevapladığı soru:

        piyasa           kolektif kapanış (`Avg`) — **referans**
        b365, ps         tekil bahisçiler — soru 1: biri kolektifi geçiyor mu?
        kalibre_hareket  anlaşmazlıksız üst basamak — soru 2'nin taban çizgisi
        kalibre_dagilim  hareket + anlaşmazlık      — soru 2: ekliyor mu?

    `kalibre_hareket` koşuma **bu yüzden** girer: `kalibre_dagilim` kademenin
    en üst basamağıdır ve altındaki her şeyi içerir. Aradaki farkı
    anlaşmazlığa atfedebilmek için bir alt basamağın aynı kesitte ölçülmesi
    gerekir (`cizgi.rapor`'da `kalibre_form` aynı rolü oynuyordu).

    Ölçüm **sezon dışarıda bırakmalıdır** (`evaluate.sezon_anahtari`).
    """
    from .evaluate import karsilastir, sezon_anahtari
    from .recalibrate import KalibreTahminci

    haftalar = kesit(sezonlar_=sezonlar_, yol=yol)
    fabrikalar = [PiyasaTahminci, *tekil_fabrikalar(), lambda: KalibreTahminci("hareket"), lambda: KalibreTahminci("dagilim")]
    sonuc = karsilastir(fabrikalar, haftalar=haftalar, grup=sezon_anahtari)
    sonuc["ayrisma"] = ayrisma_ozeti(haftalar)
    sonuc["katsayi"] = dagilim_katsayisi(haftalar)
    sonuc["soru"] = {
        "1_uye": ("tekil bahisci kolektifi geciyor mu — `b365`/`ps` satirinin "
                  "farki NEGATIF ve araligi tamamen sifirin altindaysa evet"),
        "2_anlasmazlik": ("anlasmazlik kolektifin otesinde bilgi tasiyor mu — "
                          "`kalibre_dagilim` `kalibre_hareket`i gecmiyorsa "
                          "hayir"),
    }
    return sonuc


def _yazdir(sonuc: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print(f"A2 kesiti: {sonuc['n_hafta']} hafta · {sonuc['n_mac']} maç "
          f"· referans: {sonuc['referans']} (kolektif kapanış)")
    print(f"{'tahminci':<20} {'brier':>8} {'log':>8} {'fark':>9} "
          f"{'%95 aralık':>18}  geçti")
    for s in sonuc["tahminciler"]:
        f = s["fark"]
        aralik = f"[{f['alt']:+.4f}, {f['ust']:+.4f}]" if f else ""
        fark = f"{f['fark']:+.4f}" if f else ""
        gecti = "" if s["gecti"] is None else ("EVET" if s["gecti"] else "hayir")
        print(f"{s['ad']:<20} {s['brier']:>8.4f} {s['log_kaybi']:>8.4f} "
              f"{fark:>9} {aralik:>18}  {gecti}")

    a = sonuc["ayrisma"]
    print("\nham tablo — KARIŞIK (ayrışma ile favori gücü birlikte artıyor):")
    print(f"{'bant':<10} {'n':>7} {'brier':>9} {'ort p_fav':>11}")
    for ad, b in a["bantlar"].items():
        print(f"{ad:<10} {b['n']:>7} {b['kolektif_brier']:>9.4f} "
              f"{b['ort_p_favori']:>11.4f}")

    print("\nfavori gücü sabitlenince — ilişki duruyor mu:")
    sutunlar = sorted({ad for h in a["favori_sabit"].values() for ad in h})
    print(f"{'p_favori':<10}" + "".join(f"{s:>18}" for s in sutunlar))
    for dilim, hucreler in a["favori_sabit"].items():
        hucre_metni = []
        for s in sutunlar:
            h = hucreler.get(s)
            hucre_metni.append(
                f"{h['kolektif_brier']:.4f} (n={h['n']})" if h else "—")
        print(f"{dilim:<10}" + "".join(f"{m:>18}" for m in hucre_metni))

    print(f"\n{'sezon':<8} {'ayrisma':>9} {'en_iyi_prim':>13}")
    for sezon, v in a["sezona_gore"].items():
        print(f"{sezon:<8} {v['ayrisma']:>9.4f} {v['en_iyi_prim']:>13.4f}")

    k = sonuc["katsayi"]
    print(f"\nkatsayı: β={k['beta']} δ={k['delta']} "
          f"(ortalama ayrışma {k['ortalama_ayrisma']}) → güven kısma "
          f"%{100 * (k['kisma'] or 0):.2f}")


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    _yazdir(rapor())
