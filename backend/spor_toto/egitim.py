"""Eğitim korpusu okuyucusu — tahmin katmanının maç evreni.

**Bu modül istatistik katmanının parçası değildir.** `/istatistik` sayfası ve
`/api/stats` Spor Toto kuponunun sezonunu anlatır; burada okunan korpus
yalnızca **tahminciyi eğitmek ve ölçmek** içindir. Ayrım kasıtlıdır ve
`tests/test_egitim.py::test_ayrim_*` ile bekçiye bağlanmıştır: istatistik
katmanı bu modülü import etmez, korpustan hiçbir sayı `/api/stats` gövdesine
girmez.

Korpus `scripts/build_egitim.py` tarafından üretilir (football-data.co.uk,
22 lig × 4 geçmiş sezon, ~31 bin maç). Kupon değerlendirme setinin 58 katı
büyüklüğünde ve **kupon bileşimi taşımaz** — bir tahminciyi ölçmek için
gereken üçlü `(maç, oran, sonuç)` olduğu için buna gerek de yoktur.

Gruplama: maçlar ISO takvim haftasına göre sözde-haftalara toplanır. Sebep
`evaluate`'in bootstrap kuralıyla aynı — aynı hafta sonu oynanan maçlar
bağımsız değildir, güven aralığı hafta üzerinden kurulmalıdır.

**Sezon alanı taşınır ve önemlidir.** Korpusun asıl işi sezon dışarıda
bırakmalı ölçüm: bir sezonda eğit, hiç görmediğin başka bir sezonda ölç.
Leave-one-week-out'un veremediği gerçek out-of-sample budur.
"""
from __future__ import annotations

import csv
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .odds import ARINDIRMA_VARSAYILAN, implied_probs

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_KORPUS = KOK / "data" / "egitim" / "egitim_korpus.csv"

#: **Fark ölçülerinin** arındırması — projenin varsayılanından bağımsızdır.
#:
#: `cizgi_hareketi` (açılış↔kapanış) ve `bahisci_ayrismasi` (B365↔Pinnacle)
#: iki fiyatın FARKINI ölçer. Orantısal arındırma oranın ölçeğinden
#: bağımsızdır — bütün ayaklar aynı çarpanla kısılırsa olasılık kımıldamaz —
#: ve fikir değişimini marj değişiminden ayıran özellik tam olarak budur.
#: Shin ve güç yöntemleri marjın kendisini bilgi sayar; bir fark ölçüsünde
#: bu, marj oynamasını sinyal diye okumak olurdu.
#:
#: SEVIYE ölçüleri (tek bir fiyat → olasılık) varsayılanı izler; yalnızca
#: fark ölçüleri buraya sabitlenir.
FARK_ARINDIRMASI = "orantili"

#: Logaritma alınırken sıfıra düşmeyi engelleyen taban
#: (`recalibrate.OLASILIK_TABANI` ile aynı gerekçe).
OLASILIK_TABANI = 1e-6

#: A2'nin taşıdığı kapanış kaynakları — `build_egitim.A2_KAYNAKLARI` ile aynı.
#: `b_B365`/`b_PS` tekil bahisçi, `b_Max`/`b_Avg` bütün bahisçilerin özeti.
BAHISCILER: Sequence[str] = ("b_B365", "b_PS", "b_Max", "b_Avg")

#: Bir sözde-haftanın karşılaştırmaya girmesi için gereken en az maç. Altında
#: hafta düzeyinde ortalama kendi gürültüsünü ölçer.
EN_AZ_MAC = 5


@lru_cache(maxsize=2)
def korpus_yukle(yol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Korpus satırlarını oku. Dosya yoksa boş liste (çağıran karar verir)."""
    p = Path(yol) if yol else VARSAYILAN_KORPUS
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                oranlar = {s: float(r[f"oran_{s}"]) for s in ("1", "0", "2")}
            except (KeyError, TypeError, ValueError):
                continue
            if any(v <= 1.0 for v in oranlar.values()):
                continue
            def _tam(ad: str) -> Optional[int]:
                ham = (r.get(ad) or "").strip()
                return int(ham) if ham.isdigit() else None

            def _cizgi(onek: str) -> Optional[Dict[str, float]]:
                """Acilis/kapanis ucluSU — **ya tamdir ya yoktur.**

                Yarim bir cift sessiz bir yalan olurdu: hareket sifir gorunur,
                mac A1 kesitine girer ve olcumu seyreltirdi. Uretici zaten
                yarim cift yazmiyor (`build_egitim.dogrula`); burada okurken de
                gevsetilmez.
                """
                try:
                    uclu = {s: float(r[f"{onek}_{s}"]) for s in ("1", "0", "2")}
                except (KeyError, TypeError, ValueError):
                    return None
                return uclu if all(v > 1.0 for v in uclu.values()) else None

            acilis, kapanis = _cizgi("acilis"), _cizgi("kapanis")
            dortlu = {ad: _cizgi(ad) for ad in BAHISCILER}
            out.append({
                "sezon": r["sezon"],
                "lig": r["lig"],
                "tarih": r["tarih"],
                "iso_yil": int(r["iso_yil"]),
                "iso_hafta": int(r["iso_hafta"]),
                "ev": r["ev"],
                "dep": r["dep"],
                "kod": r["kod"],
                "oranlar": oranlar,
                # Cift ancak ikisi de tamsa tasinir; biri eksikse ikisi de
                # None olur ve mac A1 kesitine giremez (bkz. `_cizgi`).
                "acilis": acilis if (acilis and kapanis) else None,
                "kapanis": kapanis if (acilis and kapanis) else None,
                # Dortlu de ya tamdir ya yoktur: eksik bir kaynak kumesinden
                # hesaplanan ayrisma maclar arasinda karsilastirilamaz.
                "bahisciler": dortlu if all(dortlu.values()) else None,
                "ev_isabet": _tam("ev_isabet"),
                "dep_isabet": _tam("dep_isabet"),
                "ev_sut": _tam("ev_sut"),
                "dep_sut": _tam("dep_sut"),
            })
    return out


#: Yuvarlanan form penceresi — bir takımın son kaç maçına bakılır.
FORM_PENCERE = 5

#: Puan karşılıkları (galibiyet/beraberlik/mağlubiyet).
_PUAN = {"G": 3.0, "B": 1.0, "M": 0.0}

#: İç/dış saha formu için ayrı pencere. Birleşik formdan **küçük** tutuldu:
#: bir takımın son 5 iç saha maçı takvimde çok daha geriye gider (yaklaşık iki
#: katı), yani aynı sayı daha eski bilgi demektir. 3, tazelikle örneklem
#: arasındaki makul orta nokta — ve ölçüm sonucuna bakılmadan seçildi.
IC_DIS_PENCERE = 3

#: Fikstür sıkışıklığı penceresi (gün). 14 gün, iki maç haftası demektir.
SIKISIKLIK_PENCERE_GUN = 14

#: Dinlenme günü tavanı. Bunun ötesi "uzun ara"dır ve ayrım taşımaz; ara
#: vermiş bir takımla sezon başındaki bir takım aynı kategoriye düşer.
#: Tavansız bırakılsaydı sezon başı maçları (önceki maç 3 ay önce) modele
#: devasa değerler sokardı.
DINLENME_TAVANI = 14.0

#: Sezonun son yüzde kaçı "sezon sonu" sayılır.
SEZON_SONU_ORANI = 0.20

#: Bir takımın lig sıralamasının anlamlı olması için gereken en az maç.
#: Altında sıralama kendi gürültüsüdür (2 maçta lider olmak bir şey demez).
EN_AZ_LIG_MACI = 5


def _form_tablosu(satirlar: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Her maç için, **o maçtan önceki** maçlardan hesaplanmış takım formu.

    Zamansal sızıntıya karşı tek savunma buradaki sıradır: maçlar kronolojik
    gezilir, form **önce okunur, sonra** o maç geçmişe eklenir. Bir maçın
    kendi sonucu asla kendi formuna girmez.

    Sızıntının bu türü sessizdir ve ölçümü tamamen bozar — model geleceği
    görür, skor mucizevi çıkar, gerçek maçta hiçbir işe yaramaz. Bu yüzden
    `test_egitim.py::test_form_gelecegi_gormez` bekçidir.

    Eksik istatistik **uydurulmaz** (doktrin 2): şut verisi olmayan maç
    geçmişe katılmaz ve yeterli geçmişi olmayan maç `form_var=False` ile
    işaretlenir. Model o maçta formu değil, işareti görür.
    """
    sirali = sorted(range(len(satirlar)),
                    key=lambda i: (satirlar[i]["tarih"], satirlar[i]["lig"],
                                   satirlar[i]["ev"]))
    gecmis: Dict[str, List[Dict[str, float]]] = {}
    out: List[Optional[Dict[str, Any]]] = [None] * len(satirlar)

    def ozet(takim: str) -> Optional[Dict[str, float]]:
        kayit = gecmis.get(takim, [])
        if len(kayit) < FORM_PENCERE:
            return None
        son = kayit[-FORM_PENCERE:]
        n = float(len(son))
        return {
            "puan": sum(k["puan"] for k in son) / n,
            "isabet_farki": sum(k["isabet_farki"] for k in son) / n,
        }

    for i in sirali:
        r = satirlar[i]
        ev_ozet, dep_ozet = ozet(r["ev"]), ozet(r["dep"])
        if ev_ozet and dep_ozet:
            out[i] = {
                "form_var": True,
                "form_puan_farki": ev_ozet["puan"] - dep_ozet["puan"],
                "form_isabet_farki": (ev_ozet["isabet_farki"]
                                      - dep_ozet["isabet_farki"]),
            }
        else:
            out[i] = {"form_var": False, "form_puan_farki": 0.0,
                      "form_isabet_farki": 0.0}

        # --- form OKUNDUKTAN SONRA bu mac gecmise eklenir ---
        ev_isabet, dep_isabet = r.get("ev_isabet"), r.get("dep_isabet")
        if ev_isabet is None or dep_isabet is None:
            continue  # istatistigi olmayan mac gecmise katilmaz
        ev_sonuc = {"1": "G", "0": "B", "2": "M"}[r["kod"]]
        dep_sonuc = {"1": "M", "0": "B", "2": "G"}[r["kod"]]
        gecmis.setdefault(r["ev"], []).append({
            "puan": _PUAN[ev_sonuc], "isabet_farki": float(ev_isabet - dep_isabet)})
        gecmis.setdefault(r["dep"], []).append({
            "puan": _PUAN[dep_sonuc], "isabet_farki": float(dep_isabet - ev_isabet)})

    return [o for o in out if o is not None]


def _takvim_tablosu(satirlar: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """A3 özellikleri: dinlenme, sıkışıklık, iç/dış form, sezon sonu payı.

    Hepsi **yalnızca o maçtan önceki** maçlardan hesaplanır; `_form_tablosu`
    ile aynı sıra disiplini geçerlidir (önce oku, sonra geçmişe ekle). Bu
    modüldeki bütün zamansal özelliklerin tek savunması budur.

    **Korpusun göremediği bir kör nokta var ve ölçümü etkiler.** Korpus 22 lig
    taşıyor; kupa ve Avrupa maçları içinde yok. Dolayısıyla dinlenme günü
    olduğundan **uzun**, fikstür sıkışıklığı olduğundan **düşük** ölçülür — ve
    hata rastgele değil, Avrupa oynayan (yani güçlü) takımlarda yoğunlaşır.

    Bu, A3'ün cevabını okurken taşınması gereken sınırdır: "yorgunluk yardım
    etmiyor" sonucu, yorgunluğun **eksik ölçülmüş** olmasından da gelebilir.
    Sonuç bu yüzden "yorgunluk fiyatlanmış" değil, *"korpustan türetilebilen
    yorgunluk vekili fiyatlanmış"* diye yazılır.

    Sezon sonu payı kaba bir vekildir: ligin son %20'sinde, sıralamanın uçlarına
    yakın takımların oynayacak bir şeyi olduğu varsayılır (şampiyonluk/küme
    düşme), orta sıranın olmadığı. Şampiyonluğunu garantilemiş bir takımı
    ayırt edemez — bunun için puan farkı ve kalan maç hesabı gerekir ve o,
    vekilin taşıyabileceğinden fazla ayrıntıdır.
    """
    from datetime import date

    def _gun(ham: str) -> date:
        y, a, g = (int(p) for p in ham.split("-"))
        return date(y, a, g)

    sirali = sorted(range(len(satirlar)),
                    key=lambda i: (satirlar[i]["tarih"], satirlar[i]["lig"],
                                   satirlar[i]["ev"]))

    # Lig-sezon basina toplam mac sayisi: fikstur BASTAN bellidir (sonuc
    # degil takvim bilgisi), bu yuzden "sezonun neresindeyiz" sorusunda
    # kullanilmasi sizinti degildir.
    lig_toplam: Dict[Any, int] = {}
    for r in satirlar:
        anahtar = (r["sezon"], r["lig"])
        lig_toplam[anahtar] = lig_toplam.get(anahtar, 0) + 1

    son_mac: Dict[str, date] = {}
    mac_gunleri: Dict[str, List[date]] = {}
    ic_form: Dict[str, List[float]] = {}
    dis_form: Dict[str, List[float]] = {}
    puan: Dict[Any, Dict[str, List[float]]] = {}
    oynanan: Dict[Any, int] = {}

    out: List[Optional[Dict[str, Any]]] = [None] * len(satirlar)

    def dinlenme(takim: str, bugun: date) -> Optional[float]:
        onceki = son_mac.get(takim)
        return None if onceki is None else min((bugun - onceki).days,
                                               DINLENME_TAVANI)

    def sikisiklik(takim: str, bugun: date) -> int:
        gunler = mac_gunleri.get(takim, [])
        return sum(1 for g in gunler
                   if 0 < (bugun - g).days <= SIKISIKLIK_PENCERE_GUN)

    def yuvarlanan(kayit: List[float], pencere: int) -> Optional[float]:
        if len(kayit) < pencere:
            return None
        son = kayit[-pencere:]
        return sum(son) / len(son)

    def sira_payi(anahtar: Any, takim: str) -> Optional[float]:
        """Takımın ligindeki sıra yüzdeliğinden türeyen "oynayacak şey" payı.

        Uçlar (şampiyonluk / küme düşme) 1'e, orta sıra 0'a yakın. Sıralama
        maç başına puanla kurulur — takımlar farklı sayıda maç oynamış olabilir.
        """
        tablo = puan.get(anahtar, {})
        kendi = tablo.get(takim)
        if not kendi or len(kendi) < EN_AZ_LIG_MACI:
            return None
        yeterli = {t: sum(p) / len(p) for t, p in tablo.items()
                   if len(p) >= EN_AZ_LIG_MACI}
        if len(yeterli) < 4:
            return None
        benim = sum(kendi) / len(kendi)
        altinda = sum(1 for v in yeterli.values() if v < benim)
        yuzdelik = altinda / (len(yeterli) - 1)
        return 2.0 * abs(yuzdelik - 0.5)

    for i in sirali:
        r = satirlar[i]
        bugun = _gun(r["tarih"])
        anahtar = (r["sezon"], r["lig"])
        ev, dep = r["ev"], r["dep"]

        ev_dinlenme, dep_dinlenme = dinlenme(ev, bugun), dinlenme(dep, bugun)
        ev_ic, dep_dis = (yuvarlanan(ic_form.get(ev, []), IC_DIS_PENCERE),
                          yuvarlanan(dis_form.get(dep, []), IC_DIS_PENCERE))

        ilerleme = oynanan.get(anahtar, 0) / max(lig_toplam.get(anahtar, 1), 1)
        sezon_sonu = ilerleme >= 1.0 - SEZON_SONU_ORANI
        ev_pay, dep_pay = sira_payi(anahtar, ev), sira_payi(anahtar, dep)

        out[i] = {
            "dinlenme_var": ev_dinlenme is not None and dep_dinlenme is not None,
            "dinlenme_farki": (float(ev_dinlenme - dep_dinlenme)
                               if ev_dinlenme is not None
                               and dep_dinlenme is not None else 0.0),
            # Deplasmanin sikisikligi EV lehinedir; isaret bu yonde secildi ki
            # butun A3 ozellikleri "pozitif = ev lehine" okunsun.
            "sikisiklik_farki": float(sikisiklik(dep, bugun)
                                      - sikisiklik(ev, bugun)),
            "ic_dis_form_var": ev_ic is not None and dep_dis is not None,
            "ic_dis_form_farki": (float(ev_ic - dep_dis)
                                  if ev_ic is not None and dep_dis is not None
                                  else 0.0),
            "sezon_sonu": sezon_sonu,
            "sezon_sonu_pay_farki": (float(ev_pay - dep_pay)
                                     if sezon_sonu and ev_pay is not None
                                     and dep_pay is not None else 0.0),
        }

        # --- ozellikler OKUNDUKTAN SONRA bu mac gecmise eklenir ---
        son_mac[ev] = son_mac[dep] = bugun
        mac_gunleri.setdefault(ev, []).append(bugun)
        mac_gunleri.setdefault(dep, []).append(bugun)
        ev_sonuc = {"1": "G", "0": "B", "2": "M"}[r["kod"]]
        dep_sonuc = {"1": "M", "0": "B", "2": "G"}[r["kod"]]
        ic_form.setdefault(ev, []).append(_PUAN[ev_sonuc])
        dis_form.setdefault(dep, []).append(_PUAN[dep_sonuc])
        puan.setdefault(anahtar, {}).setdefault(ev, []).append(_PUAN[ev_sonuc])
        puan.setdefault(anahtar, {}).setdefault(dep, []).append(_PUAN[dep_sonuc])
        oynanan[anahtar] = oynanan.get(anahtar, 0) + 1

    return [o for o in out if o is not None]


def sezonlar() -> List[str]:
    """Korpustaki sezonlar, kronolojik."""
    return sorted({r["sezon"] for r in korpus_yukle()})


def cizgi_hareketi(acilis: Optional[Dict[str, float]],
                   kapanis: Optional[Dict[str, float]]
                   ) -> Dict[str, float]:
    """Açılış→kapanış hareketi, sembol başına: `ln p_kapanış − ln p_açılış`.

    Marj arındırılmış **olasılık** üzerinden ölçülür, ham oran üzerinden
    değil. Ham oran hareketi iki şeyi karıştırır: piyasanın fikir değiştirmesi
    ve bahisçinin marjını değiştirmesi. Marj arındırıldıktan sonra üç olasılık
    da 1'e toplandığı için geriye yalnızca **fikrin yeniden dağılımı** kalır.

    Logaritma alınır çünkü ölçek simetrik olsun isteriz: 0,10 → 0,20 ile
    0,40 → 0,80 aynı büyüklükte bir fikir değişikliğidir; farkları alsaydık
    ikincisi dört kat büyük görünürdü.

    Çift yoksa üç sıfır döner — "hareket bilinmiyor" ile "hareket yok" aynı
    davranışa düşer, çünkü ikisinde de söylenecek bir şey yoktur (`form` ile
    aynı gerekçe).

    **Arındırma burada `orantili`ya sabitlenmiştir ve projenin varsayılanını
    izlemez.** Sebep, bir FARK ölçüyor olmamız: orantısal yöntem oranın
    ölçeğinden bağımsızdır (bütün ayaklar aynı çarpanla kısılırsa olasılık
    kımıldamaz), Shin ve güç yöntemleri değildir — onlar marjın kendisini
    bilgi sayar. Varsayılanı izleseydi, bahisçinin yalnızca marjını büyütmesi
    "hareket" olarak okunur ve A1 fikir değişimi yerine bahisçinin fiyatlama
    politikasını ölçerdi. `test_hareket_saf_marj_degisimini_gormez` bekçisi
    bunu 2026-08'deki varsayılan çevriminde yakaladı.
    """
    if not acilis or not kapanis:
        return {s: 0.0 for s in ("1", "0", "2")}
    a = implied_probs(acilis, FARK_ARINDIRMASI)
    k = implied_probs(kapanis, FARK_ARINDIRMASI)
    return {s: math.log(max(k.get(s, 0.0), OLASILIK_TABANI)
                        / max(a.get(s, 0.0), OLASILIK_TABANI))
            for s in ("1", "0", "2")}


def bahisci_ayrismasi(bahisciler: Optional[Dict[str, Optional[Dict[str, float]]]]
                      ) -> Dict[str, float]:
    """Bahisçiler ne kadar ayrışıyor — **iki ayrı ölçü, ikisi de gerekli.**

    `ayrisma` — `B365` ile `Pinnacle`ın marj arındırılmış olasılıkları
    arasındaki toplam değişim uzaklığı, ½·Σ|Δp|. 0 = tam hemfikir, 1 = tam zıt.
    **A2'nin birincil özelliği budur** çünkü kaynak kümesi sabittir: iki
    bahisçi de dört sezonda da ~%100 mevcut ve ölçünün büyüklüğü kaç bahisçi
    olduğuna bağlı değil. Ölçülen sezon ortalamaları 0,0142 / 0,0122 / 0,0125
    / 0,0124 — sabit.

    `en_iyi_prim` — `ln(Max/Avg)`ın semboller ortalaması: en iyi fiyat,
    ortalamanın ne kadar üstünde. **Daha geniş** bir ölçüdür (bütün bahisçi
    evrenini görür) ama **bahisçi sayısına duyarlıdır**: football-data yeni
    kaynak ekledikçe `Max` mekanik olarak kayar. Ölçülen sezon ortalamaları
    0,0712 / 0,0641 / 0,0629 / 0,0577 — %20'lik bir sürüklenme.

    **Bu yüzden ikisi ayrı tutuluyor ve model yalnızca `ayrisma`yı görüyor.**
    Sezon dışarıda bırakmalı ölçümde sezona göre kayan bir özellik, sinyal
    değil sezon kimliği öğretir; model "hangi sezondayım" bilgisini
    anlaşmazlık sanır. `en_iyi_prim` betimleyici kalır ve sürüklenmesi
    raporlanır.

    Dörtlü yoksa iki sıfır döner — "bilinmiyor" ile "hemfikir" aynı davranışa
    düşer, çünkü ikisinde de söylenecek bir şey yoktur (`form`, `hareket` ile
    aynı gerekçe).
    """
    bos = {"ayrisma": 0.0, "en_iyi_prim": 0.0}
    if not bahisciler or not all(bahisciler.get(ad) for ad in BAHISCILER):
        return bos

    # Ayrisma da bir FARK olcusudur ve `cizgi_hareketi` ile ayni gerekceyle
    # `orantili`ya sabitlenmistir: B365 ile Pinnacle'in marjlari farklidir ve
    # olcek duyarli bir arindirmada o marj farki "anlasmazlik" gibi gorunurdu.
    p_b365 = implied_probs(bahisciler["b_B365"], FARK_ARINDIRMASI)
    p_ps = implied_probs(bahisciler["b_PS"], FARK_ARINDIRMASI)
    ayrisma = 0.5 * sum(abs(p_b365[s] - p_ps[s]) for s in ("1", "0", "2"))

    en_iyi, ortalama = bahisciler["b_Max"], bahisciler["b_Avg"]
    prim = sum(math.log(max(en_iyi[s], OLASILIK_TABANI)
                        / max(ortalama[s], OLASILIK_TABANI))
               for s in ("1", "0", "2")) / 3.0
    return {"ayrisma": ayrisma, "en_iyi_prim": prim}


def korpus_haftalari(sezonlar_: Optional[Sequence[str]] = None,
                     ligler: Optional[Sequence[str]] = None,
                     en_az_mac: int = EN_AZ_MAC,
                     yol: Optional[str] = None,
                     cizgi_gerekli: bool = False,
                     bahisci_gerekli: bool = False,
                     yontem: str = ARINDIRMA_VARSAYILAN) -> List[Dict[str, Any]]:
    """Korpusu `evaluate` koşumunun beklediği hafta girdilerine çevir.

    Dönen her kayıt `backtest.hafta_girdileri()` ile aynı sözleşmeyi taşır
    (`results`, `probs`, `usable`, …) artı iki alan:

        sezon        sezon dışarıda bırakmalı ölçüm için grup anahtarı
        ozellikler   maç başına lig / favori / form / çizgi hareketi

    `ozellikler` modelin özellik üretmesi içindir; korpus **olguyu** taşır,
    özelliği model türetir (`recalibrate._mac_ozellikleri`). Bu ayrım
    sayesinde aynı tahminci hem kupon haftalarında hem korpusta çalışır.

    `cizgi_gerekli=True` verilirse açılış+kapanış çifti olmayan maçlar elenir.
    A1 ölçümünün kesiti budur ve **eleme şart**: açılış tahmincisi ile kapanış
    tahmincisi aynı maçlarda ölçülmezse aradaki fark hareketi değil,
    örneklem farkını ölçer.

    `bahisci_gerekli=True` aynı şeyi A2 için yapar: bahisçi dörtlüsü tam
    olmayan maçlar elenir.

    `yontem` marj arındırmasını seçer (A5, `odds.implied_probs`). Varsayılan
    `orantili`dır ve **değiştirilmemelidir**: A1–A3'ün yayımlanmış bütün
    sayıları onunla ölçüldü. Parametre, "aynı ölçüm başka arındırmayla ne
    verir" sorusunu sormak için var — cevabı görmek isteyen açıkça ister.
    """
    ham = korpus_yukle(yol)
    # Form tum korpus uzerinde, kronolojik hesaplanir; suzme SONRA gelir.
    # Once suzseydik, secilen sezonun ilk maclari gecmissiz kalirdi.
    formlar = _form_tablosu(ham)
    takvimler = _takvim_tablosu(ham)
    # KOPYA uzerinde calisilir. `korpus_yukle` lru_cache'lidir ve
    # `benzer._olasilik_tablosu` ayni satir nesnelerini disariya dagitip
    # docstring'inde "degistirmeyin" der; `_form`/`_takvim` alanlarini
    # yerinde yazmak onbellegi ve o sozu birlikte bozuyordu.
    tumu = [dict(r) for r in ham]
    for r, f, t in zip(tumu, formlar, takvimler):
        r["_form"] = f
        r["_takvim"] = t

    satirlar = tumu
    if cizgi_gerekli:
        satirlar = [r for r in satirlar if r.get("acilis") and r.get("kapanis")]
    if bahisci_gerekli:
        satirlar = [r for r in satirlar if r.get("bahisciler")]
    if sezonlar_ is not None:
        izin = set(sezonlar_)
        satirlar = [r for r in satirlar if r["sezon"] in izin]
    if ligler is not None:
        izin_lig = set(ligler)
        satirlar = [r for r in satirlar if r["lig"] in izin_lig]

    gruplar: Dict[Any, List[Dict[str, Any]]] = {}
    for r in satirlar:
        gruplar.setdefault((r["sezon"], r["iso_yil"], r["iso_hafta"]), []).append(r)

    out: List[Dict[str, Any]] = []
    for (sezon, yil, hafta), grup in sorted(gruplar.items()):
        if len(grup) < en_az_mac:
            continue
        grup.sort(key=lambda r: (r["tarih"], r["lig"], r["ev"]))
        probs: List[Dict[str, float]] = []
        ozellikler: List[Dict[str, Any]] = []
        for r in grup:
            olasilik = implied_probs(r["oranlar"], yontem)
            probs.append(olasilik)
            favori = min(r["oranlar"], key=lambda s: r["oranlar"][s])
            form = r.get("_form") or {"form_var": False, "form_puan_farki": 0.0,
                                      "form_isabet_farki": 0.0}
            hareket = cizgi_hareketi(r.get("acilis"), r.get("kapanis"))
            takvim = r.get("_takvim") or {}
            ozellikler.append({
                "lig": r["lig"],
                "favori": favori,
                "favori_oran": r["oranlar"][favori],
                **form,
                **takvim,
                "cizgi_var": bool(r.get("acilis") and r.get("kapanis")),
                "acilis_probs": (implied_probs(r["acilis"], yontem)
                                 if r.get("acilis") else None),
                "kapanis_probs": (implied_probs(r["kapanis"], yontem)
                                  if r.get("kapanis") else None),
                **{f"hareket_{s}": v for s, v in hareket.items()},
                "bahisci_var": bool(r.get("bahisciler")),
                "bahisci_probs": ({ad: implied_probs(uclu, yontem)
                                   for ad, uclu in r["bahisciler"].items()}
                                  if r.get("bahisciler") else None),
                **bahisci_ayrismasi(r.get("bahisciler")),
            })
        out.append({
            "week": yil * 100 + hafta,
            "close_date": grup[-1]["tarih"],
            "sezon": sezon,
            "results": "".join(r["kod"] for r in grup),
            "probs": probs,
            "ozellikler": ozellikler,
            "missing": 0,
            "usable": True,
        })
    return out


def ozet(yol: Optional[str] = None) -> Dict[str, Any]:
    """Korpusun tanılama özeti — rapor ve test için."""
    satirlar = korpus_yukle(yol)
    haftalar = korpus_haftalari(yol=yol)
    return {
        "mac": len(satirlar),
        "sezon": sorted({r["sezon"] for r in satirlar}),
        "lig": len({r["lig"] for r in satirlar}),
        "hafta": len(haftalar),
        "kod_dagilimi": {k: sum(1 for r in satirlar if r["kod"] == k)
                         for k in ("1", "0", "2")},
        "cizgi_cifti": sum(1 for r in satirlar
                           if r.get("acilis") and r.get("kapanis")),
        "bahisci_dortlusu": sum(1 for r in satirlar if r.get("bahisciler")),
    }
