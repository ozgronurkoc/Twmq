"""Tahmin ürünü — henüz oynanmamış maça olasılık vermek.

**Bu modül projenin amacının kendisidir** (README §1: *maç sonucu tahmini
yapmak*) ve Faz A'nın ölçümleri onu iptal etmez. A4'ün kapattığı soru
*"piyasayı geçen bir özellik var mı"* idi; cevabı hayır çıktı. Elimizde
kalibre ve ölçülmüş bir tahminci kalıyor — o da piyasanın kendisi. Çalışan
bir aracı, sırf daha iyisini bulamadık diye rafa kaldırmak olmaz.

Diğer tahmin modüllerinden farkı yönüdür: `evaluate`, `cizgi`, `bahisci` ve
`disari` **geçmişi** ölçer, sonucu bilinen maçlarda. Burası **geleceğe**
bakar ve sonucu bilinmeyen maça sayı verir.

**Tek kural: hiçbir olasılık ölçülmüş isabeti olmadan dışarı çıkmaz.** Bu
yüzden gövde iki bloğu ayrılmaz biçimde taşır — `tahminler` ve
`olculmus_isabet`. Süslenmiş bir olasılık, süslenmemiş bir yalandır.

Üç sınır gövdede açıkça yazılıdır ve hiçbiri gizlenmez:

1. **Oranlar açılış oranıdır.** Bedeli ölçülmüştür (A1): 31.099 maçta açılış
   Brier 0,5964, kapanış 0,5940 — fark +0,0025. Maç öncesi verilen tahmin,
   maç saatinde verilecek olandan ölçülebilir biçimde biraz kötüdür.
2. **Ölçülen isabet kupon setine aittir** (540 maç, 2025/26, football-data
   kapanış oranı). Aynı fiyatlayıcı olduğu için taşınabilir; ölçüm evreninin
   dışındaki bir lig için `olculen_lig=False` ile işaretlenir.
3. **İddaa kaynaklı tahminin kalibrasyonu ÖLÇÜLMEMİŞTİR.** Marj %17,2'ye
   karşı %7,26; yapı tutar, seviye tutmaz. Bu maçlar ayrı işaretlenir.

Ve bir dördüncüsü, ürünün en kolay söyleyeceği yalanı engelleyen:

4. **Bu tahminci tek kolonla 14+ tutturamaz** ve bu modelin kusuru değil
   aritmetiktir. Piyasanın kendi olasılıklarından P(14+) ≈ 8,6·10⁻⁴, yani
   ~1/1.161 hafta; 36 haftada beklenen 0,031, gözlenen 0. 14+'a **kaplama
   motoru** taşır, tahminci değil.
"""
from __future__ import annotations

import csv
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .history import SYMBOLS
from .odds import implied_probs

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_FIXTURES = KOK / "data" / "fixtures" / "fixtures.csv"
IDDAA_DIZINI = KOK / "data" / "iddaa"

#: Kaynak etiketleri. Sıra tercih sırasıdır ve gerekçesi ölçümdür:
#: `football-data` ölçümün yapıldığı fiyatlayıcıdır, `iddaa` değildir.
KAYNAK_OLCULEN = "football-data"
KAYNAK_OLCULMEMIS = "iddaa"


def _simdi() -> datetime:
    """Şimdi — testler sabitleyebilsin diye tek noktada."""
    return datetime.now()


def _gelecekte(kickoff: Optional[str], simdi: datetime) -> bool:
    """Başlama saati geçmiş mi. Saat çözülemezse maç **elenir** (doktrin 2).

    Belirsiz bir zamana maç öncesi olasılığı vermek, olasılığın maç öncesi
    olduğu iddiasını doğrulanamaz hale getirir.
    """
    ham = (kickoff or "").strip()
    for bicim in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(ham, bicim) > simdi
        except ValueError:
            continue
    return False


def _sayi(ham: Any) -> Optional[float]:
    try:
        v = float(str(ham).strip())
    except (TypeError, ValueError):
        return None
    return v if v > 1.0 else None


def fixtures_maclari(yol: Optional[str] = None) -> List[Dict[str, Any]]:
    """`build_fixtures.py`nin yazdığı yaklaşan maçlar (ölçülen kaynak).

    Dosya yoksa ya da boşsa **boş liste** döner ve bu bir hata değildir:
    fikstür yuvarlanan bir penceredir, hafta oynandığında boşalır.
    """
    p = Path(yol) if yol else VARSAYILAN_FIXTURES
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            oranlar = {s: _sayi(r.get(f"oran_{s}")) for s in SYMBOLS}
            if any(v is None for v in oranlar.values()):
                continue
            out.append({
                "kaynak": KAYNAK_OLCULEN,
                "lig": r.get("lig", ""),
                "tarih": r.get("tarih", ""),
                "saat": r.get("saat", ""),
                "ev": r.get("ev", ""),
                "dep": r.get("dep", ""),
                "oranlar": oranlar,
                "oran_kaynak": r.get("oran_kaynak", ""),
                "olculen_lig": r.get("olculen_lig") == "1",
            })
    return out


def _son_iddaa_dosyasi() -> Optional[Path]:
    if not IDDAA_DIZINI.exists():
        return None
    adaylar = sorted(IDDAA_DIZINI.glob("iddaa_*.csv"))
    return adaylar[-1] if adaylar else None


def iddaa_maclari(yol: Optional[str] = None) -> List[Dict[str, Any]]:
    """En son iddaa bülten snapshot'ından yaklaşan maçlar.

    **Kalibrasyonu ölçülmemiş bir kaynaktır** ve gövdede öyle işaretlenir.
    Yine de taşınır: ölçülen kaynak (fikstür) boş olduğunda ürünün elinde
    başka bir şey kalmaz ve "veri yok" demek, olmayan bir şeyi uydurmaktan
    iyidir ama olan bir şeyi saklamaktan kötüdür.

    **İki eleme var ve ikisi de aynı sebeple:** başlamış bir maça maç öncesi
    olasılığı vermek yanlıştır. Canlı işaretli (`canli=1`) maçlar elenir, ve
    başlama saati geçmiş maçlar da elenir — snapshot dünden kalmış olabilir
    ve o dosyadaki maçların bir kısmı çoktan oynanmıştır.
    """
    p = Path(yol) if yol else _son_iddaa_dosyasi()
    if p is None or not Path(p).exists():
        return []
    simdi = _simdi()
    out: List[Dict[str, Any]] = []
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("canli") or "").strip() == "1":
                continue
            if not _gelecekte(r.get("kickoff"), simdi):
                continue
            oranlar = {s: _sayi(r.get(f"odd_{s}")) for s in SYMBOLS}
            if any(v is None for v in oranlar.values()):
                continue
            kickoff = (r.get("kickoff") or "").strip()
            out.append({
                "kaynak": KAYNAK_OLCULMEMIS,
                "lig": r.get("lig", ""),
                "tarih": kickoff[:10],
                "saat": kickoff[11:16],
                "ev": r.get("home", ""),
                "dep": r.get("away", ""),
                "oranlar": oranlar,
                "oran_kaynak": "iddaa",
                "olculen_lig": False,
            })
    return out


def yaklasan_maclar(fixtures_yolu: Optional[str] = None,
                    iddaa_yolu: Optional[str] = None) -> List[Dict[str, Any]]:
    """Tahmin edilebilecek maçlar — **ölçülen kaynak önce.**

    İkisi birleştirilmez, **sıralanır**: fikstürde maç varsa ürün onu
    gösterir; yoksa iddaa'ya düşer. Karıştırmak, gövdedeki tek bir isabet
    sayısının iki farklı fiyatlayıcıya aitmiş gibi okunmasına yol açardı.
    """
    olculen = fixtures_maclari(fixtures_yolu)
    if olculen:
        return olculen
    return iddaa_maclari(iddaa_yolu)


def tahmin_et(mac: Dict[str, Any]) -> Dict[str, Any]:
    """Tek maçın tahmini: marj arındırılmış 1/0/2 olasılığı.

    Model yok — ve bu bir eksiklik değil **ölçüm sonucu**: dokuz özellik
    denendi, hiçbiri piyasayı geçemedi (§6.2 A4). Piyasanın kendi fiyatı,
    elimizdeki en iyi tahmindir.
    """
    olasilik = implied_probs(mac["oranlar"])
    en_olasi = max(olasilik, key=lambda s: olasilik[s]) if olasilik else None
    return {
        **{k: mac[k] for k in ("kaynak", "lig", "tarih", "saat", "ev", "dep",
                               "oran_kaynak", "olculen_lig")},
        "oranlar": mac["oranlar"],
        "olasilik": {s: round(olasilik.get(s, 0.0), 4) for s in SYMBOLS},
        "en_olasi": en_olasi,
        "guven": round(olasilik.get(en_olasi, 0.0), 4) if en_olasi else None,
    }


@lru_cache(maxsize=1)
def olculmus_isabet() -> Dict[str, Any]:
    """Bu tahmincinin **ölçülmüş** isabeti — gövdeden ayrılamaz blok.

    Kupon setinde (2025/26, 36 tam hafta, 540 maç) hesaplanır. Hiçbiri
    elle yazılmadı; hepsi arşivden koşulur, çünkü elle yazılan bir sayı
    veri kaydığında sessizce yalan söylemeye başlar.
    """
    from .backtest import hafta_girdileri
    from .evaluate import brier, log_kaybi
    from .predict import PiyasaTahminci

    haftalar = [h for h in hafta_girdileri() if h["usable"]]
    if not haftalar:
        return {"olculdu": False,
                "not": "oran arsivi eksik — isabet olculemedi"}

    tahminci = PiyasaTahminci()
    n_mac = dogru = 0
    b_top = l_top = 0.0
    hafta_dogru: List[int] = []
    for hafta in haftalar:
        tahminler = tahminci.tahmin(hafta)
        d = 0
        for i, kod in enumerate(hafta["results"]):
            blok = tahminler[i]
            n_mac += 1
            b_top += brier(blok, kod)
            l_top += log_kaybi(blok, kod)
            if max(blok, key=lambda s: blok[s]) == kod:
                d += 1
        dogru += d
        hafta_dogru.append(d)

    return {
        "olculdu": True,
        "kesit": "2025/26 Spor Toto kuponu — football-data kapanış oranı",
        "n_hafta": len(haftalar),
        "n_mac": n_mac,
        "mac_basina_isabet": round(dogru / n_mac, 4),
        "brier": round(b_top / n_mac, 4),
        "log_kaybi": round(l_top / n_mac, 4),
        "hafta_ortalamasi": round(sum(hafta_dogru) / len(hafta_dogru), 2),
        "en_iyi_hafta": max(hafta_dogru),
        "hafta_14_arti": sum(1 for d in hafta_dogru if d >= 14),
        "hafta_13_arti": sum(1 for d in hafta_dogru if d >= 13),
    }


def _uyarilar(maclar: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Gövdenin taşımak zorunda olduğu sınırlar. **Kısaltılmaz.**"""
    out = [
        {"ad": "tek_kolon_14_tutmaz",
         "metin": ("Bu tahminci tek kolonla 14+ tutturamaz ve bu modelin kusuru "
                   "degil ARITMETIKTIR: piyasanin kendi olasiliklarindan "
                   "P(14+) ≈ 1/1.161 hafta. 36 haftada beklenen 0,031, "
                   "gozlenen 0. 14+'a kaplama motoru tasir, tahminci degil.")},
        {"ad": "model_yok",
         "metin": ("Olasiliklar piyasa fiyatidir. Dokuz ozellik denendi, "
                   "hicbiri piyasayi out-of-sample gecemedi (§6.2 A4) — "
                   "yani bu bir eksiklik degil olcum sonucudur.")},
    ]
    kaynaklar = {m["kaynak"] for m in maclar}
    if KAYNAK_OLCULEN in kaynaklar:
        out.append({"ad": "acilis_orani",
                    "metin": ("Oranlar ACILIS oranidir. A1 olcumu: 31.099 macta "
                              "acilis Brier 0,5964, kapanis 0,5940 — fark "
                              "+0,0025. Mac saatinde verilecek tahmin "
                              "olculebilir bicimde biraz daha iyidir.")})
    if KAYNAK_OLCULMEMIS in kaynaklar:
        out.append({"ad": "kalibrasyon_olculmemis",
                    "metin": ("Bu maclar IDDAA bulteninden geliyor ve iddaa "
                              "kaynakli olasiligin kalibrasyonu OLCULMEMISTIR "
                              "(marj %17,2'ye karsi %7,26). Yapisi tutar, "
                              "seviyesi tutmayabilir. Asagidaki olculmus "
                              "isabet bu maclara ait DEGILDIR.")})
    disarida = sum(1 for m in maclar if not m.get("olculen_lig"))
    if disarida:
        out.append({"ad": "olcum_evreni_disi",
                    "metin": (f"{disarida} mac, isabetin olculdugu lig "
                              "evreninin disinda. Tahmin uretilir ama olculmus "
                              "isabet o maclara ait degildir.")})
    return out


def rapor(fixtures_yolu: Optional[str] = None,
          iddaa_yolu: Optional[str] = None,
          limit: Optional[int] = None) -> Dict[str, Any]:
    """Tahmin gövdesi — olasılıklar ve ölçülmüş isabet, **birlikte.**

    İkisi ayrılamaz. Bir arayüz olasılıkları alıp isabeti atarsa, projenin
    baştan beri karşı çıktığı şeyi üretmiş olur.
    """
    maclar = yaklasan_maclar(fixtures_yolu, iddaa_yolu)
    tahminler = [tahmin_et(m) for m in maclar]
    tahminler.sort(key=lambda t: (t["tarih"], t["saat"], t["lig"], t["ev"]))
    if limit is not None:
        tahminler = tahminler[:limit]

    kaynaklar = sorted({t["kaynak"] for t in tahminler})
    return {
        "n_mac": len(tahminler),
        "kaynaklar": kaynaklar,
        "olculen_kaynak": KAYNAK_OLCULEN in kaynaklar,
        "tahminler": tahminler,
        "olculmus_isabet": olculmus_isabet(),
        "uyarilar": _uyarilar(maclar),
        "bos_sebep": (None if tahminler else
                      "yaklasan mac yok — fikstur yuvarlanan penceredir ve "
                      "hafta oynandiginda bosalir; iddaa bulteni de bos ya da "
                      "alinmamis olabilir"),
    }


def _yazdir(g: Dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    i = g["olculmus_isabet"]
    print(f"YAKLASAN {g['n_mac']} MAC · kaynak: {', '.join(g['kaynaklar']) or '—'}")
    if not g["n_mac"]:
        print(f"\n{g['bos_sebep']}")
        return
    print(f"\n{'tarih':<11} {'saat':<6} {'lig':<6} {'ev':<20} {'dep':<20} "
          f"{'1':>6} {'0':>6} {'2':>6}  {'sec':>3} {'guven':>6}")
    for t in g["tahminler"]:
        o = t["olasilik"]
        print(f"{t['tarih']:<11} {t['saat']:<6} {t['lig'][:6]:<6} "
              f"{t['ev'][:20]:<20} {t['dep'][:20]:<20} "
              f"{o['1']:.3f}  {o['0']:.3f}  {o['2']:.3f}  {t['en_olasi']:>3} "
              f"{t['guven']*100:>5.1f}%")
    if i.get("olculdu"):
        print(f"\nOLCULMUS ISABET ({i['kesit']}):")
        print(f"  {i['n_hafta']} hafta · {i['n_mac']} mac · mac basina "
              f"%{100*i['mac_basina_isabet']:.1f} · haftada ort "
              f"{i['hafta_ortalamasi']}/15 (en iyi {i['en_iyi_hafta']})")
        print(f"  Brier {i['brier']} · log {i['log_kaybi']} · "
              f"14+ tutan hafta {i['hafta_14_arti']}/{i['n_hafta']}")
    print("\nSINIRLAR:")
    for u in g["uyarilar"]:
        print(f"  [{u['ad']}] {u['metin']}")


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    _yazdir(rapor(limit=20))
