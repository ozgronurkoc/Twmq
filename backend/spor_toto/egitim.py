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

from .odds import implied_probs

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_KORPUS = KOK / "data" / "egitim" / "egitim_korpus.csv"

#: Logaritma alınırken sıfıra düşmeyi engelleyen taban
#: (`recalibrate.OLASILIK_TABANI` ile aynı gerekçe).
OLASILIK_TABANI = 1e-6

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
    """
    if not acilis or not kapanis:
        return {s: 0.0 for s in ("1", "0", "2")}
    a, k = implied_probs(acilis), implied_probs(kapanis)
    return {s: math.log(max(k.get(s, 0.0), OLASILIK_TABANI)
                        / max(a.get(s, 0.0), OLASILIK_TABANI))
            for s in ("1", "0", "2")}


def korpus_haftalari(sezonlar_: Optional[Sequence[str]] = None,
                     ligler: Optional[Sequence[str]] = None,
                     en_az_mac: int = EN_AZ_MAC,
                     yol: Optional[str] = None,
                     cizgi_gerekli: bool = False) -> List[Dict[str, Any]]:
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
    """
    tumu = korpus_yukle(yol)
    # Form tum korpus uzerinde, kronolojik hesaplanir; suzme SONRA gelir.
    # Once suzseydik, secilen sezonun ilk maclari gecmissiz kalirdi.
    formlar = _form_tablosu(tumu)
    for r, f in zip(tumu, formlar):
        r["_form"] = f

    satirlar = tumu
    if cizgi_gerekli:
        satirlar = [r for r in satirlar if r.get("acilis") and r.get("kapanis")]
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
            olasilik = implied_probs(r["oranlar"])
            probs.append(olasilik)
            favori = min(r["oranlar"], key=lambda s: r["oranlar"][s])
            form = r.get("_form") or {"form_var": False, "form_puan_farki": 0.0,
                                      "form_isabet_farki": 0.0}
            hareket = cizgi_hareketi(r.get("acilis"), r.get("kapanis"))
            ozellikler.append({
                "lig": r["lig"],
                "favori": favori,
                "favori_oran": r["oranlar"][favori],
                **form,
                "cizgi_var": bool(r.get("acilis") and r.get("kapanis")),
                "acilis_probs": (implied_probs(r["acilis"])
                                 if r.get("acilis") else None),
                "kapanis_probs": (implied_probs(r["kapanis"])
                                  if r.get("kapanis") else None),
                **{f"hareket_{s}": v for s, v in hareket.items()},
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
    }
