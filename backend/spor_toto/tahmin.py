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
from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from .history import SYMBOLS
from .odds import implied_probs

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_FIXTURES = KOK / "data" / "fixtures" / "fixtures.csv"
IDDAA_DIZINI = KOK / "data" / "iddaa"

#: Kaynak etiketleri. Sıra tercih sırasıdır ve gerekçesi ölçümdür:
#: `football-data` ölçümün yapıldığı fiyatlayıcıdır, `iddaa` değildir.
KAYNAK_OLCULEN = "football-data"
KAYNAK_OLCULMEMIS = "iddaa"

#: Manşet tahminci — ürünün ana sayısı. Eğitimsiz; piyasa fiyatının kendisi.
MANSET_AD = "piyasa"

#: Alternatif tahminci: korpusta eğitilmiş yeniden kalibrasyon.
#:
#: **`bias` basamağı seçildi ve seçim kasıtlı.** Üç parametresi var (sıcaklık +
#: iki sınıf sabiti) ve yalnızca `probs` okur — lig, form, çizgi hareketi gibi
#: yaklaşan maçta **elimizde olmayan** hiçbir alana ihtiyaç duymaz. Üst
#: basamaklar o alanları nötr sıfır görüp `bias` ile aynı sayıyı üretirdi;
#: fazladan parametre, fazladan iddia demek olurdu.
#:
#: **Geçmedi ve öyle etiketlenir.** 31.103 maçta eğitilip 540 maçlık kupon
#: setinde ölçüldüğünde piyasadan iyi çıkıyor (0,5732'ye karşı 0,5740) ama
#: güven aralığı sıfırı içeriyor. Ürüne manşet olarak değil, **ölçülmüş
#: alternatif** olarak girer — farkı ve aralığıyla birlikte.
ALTERNATIF_AD = "kalibre_bias"
ALTERNATIF_KADEME = "bias"


def _simdi() -> datetime:
    """Şimdi — testler sabitleyebilsin diye tek noktada."""
    return datetime.now()


def _gelecekte(kickoff: str | None, simdi: datetime) -> bool:
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


def _sayi(ham: Any) -> float | None:
    try:
        v = float(str(ham).strip())
    except (TypeError, ValueError):
        return None
    return v if v > 1.0 else None


def fixtures_maclari(yol: str | None = None) -> list[dict[str, Any]]:
    """`build_fixtures.py`nin yazdığı yaklaşan maçlar (ölçülen kaynak).

    Dosya yoksa ya da boşsa **boş liste** döner ve bu bir hata değildir:
    fikstür yuvarlanan bir penceredir, hafta oynandığında boşalır.
    """
    p = Path(yol) if yol else VARSAYILAN_FIXTURES
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
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


def _son_iddaa_dosyasi() -> Path | None:
    if not IDDAA_DIZINI.exists():
        return None
    adaylar = sorted(IDDAA_DIZINI.glob("iddaa_*.csv"))
    return adaylar[-1] if adaylar else None


def iddaa_maclari(yol: str | None = None) -> list[dict[str, Any]]:
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
    out: list[dict[str, Any]] = []
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


@lru_cache(maxsize=1)
def _egitilmis_alternatif():
    """Korpusta eğitilmiş alternatif tahminci (korpus yoksa None).

    Eğitim **bir kez** yapılır ve sonucu önbelleklenir: korpus sürümlenmiş
    bir dosyadır, değişmez. `/api/tahmin` gövdesi önbelleklenmez ama bu
    uydurma öyle — ikisi farklı şeyler.
    """
    from .egitim import korpus_haftalari
    from .recalibrate import KalibreTahminci

    haftalar = korpus_haftalari()
    if not haftalar:
        return None
    t = KalibreTahminci(ALTERNATIF_KADEME)
    t.egit(haftalar)
    return t


def _sozde_hafta(maclar: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Yaklaşan maçları kademe tahmincisinin beklediği hafta girdisine çevir.

    **`ozellikler` AÇIKÇA doldurulur ve bu şart.** `recalibrate` bu alan
    yoksa oran arşivine `(hafta, maç no)` ile bakar — kupon setine özgü bir
    yol. Yaklaşan maçta o arama anlamsız bir eşleşme üretir ve model,
    tamamen başka bir maçın özelliğini okur. Sessiz ve zehirli bir hata
    olurdu.

    Elimizde olmayan her alan **nötr sıfır**: form, çizgi hareketi, bahisçi
    ayrışması, A3 özellikleri. `bias` basamağı bunların hiçbirini okumaz
    zaten; nötr vermek, uydurmamanın kod hâlidir (doktrin 2).
    """
    from .recalibrate import A3_ALANLARI

    ozellikler: list[dict[str, Any]] = []
    probs: list[dict[str, float]] = []
    for m in maclar:
        olasilik = implied_probs(m["oranlar"])
        probs.append(olasilik)
        favori = min(m["oranlar"], key=lambda s: m["oranlar"][s])
        ozellikler.append({
            "lig": m.get("lig") or "bilinmiyor",
            "favori": favori,
            "favori_oran": m["oranlar"][favori],
            "form_var": False,
            "form_puan_farki": 0.0,
            "form_isabet_farki": 0.0,
            **{f"hareket_{s}": 0.0 for s in SYMBOLS},
            "ayrisma": 0.0,
            **{alan: 0.0 for _, alan in A3_ALANLARI},
        })
    return {"week": 0, "close_date": "", "results": "", "probs": probs,
            "ozellikler": ozellikler, "missing": 0, "usable": True}


def yaklasan_maclar(fixtures_yolu: str | None = None,
                    iddaa_yolu: str | None = None) -> list[dict[str, Any]]:
    """Tahmin edilebilecek maçlar — **ölçülen kaynak önce.**

    İkisi birleştirilmez, **sıralanır**: fikstürde maç varsa ürün onu
    gösterir; yoksa iddaa'ya düşer. Karıştırmak, gövdedeki tek bir isabet
    sayısının iki farklı fiyatlayıcıya aitmiş gibi okunmasına yol açardı.
    """
    olculen = fixtures_maclari(fixtures_yolu)
    if olculen:
        return olculen
    return iddaa_maclari(iddaa_yolu)


def _blok(olasilik: dict[str, float]) -> dict[str, Any]:
    """Olasılık sözlüğünü gövde bloğuna çevir: olasılık + en olası + güven."""
    en_olasi = max(olasilik, key=lambda s: olasilik[s]) if olasilik else None
    return {
        "olasilik": {s: round(olasilik.get(s, 0.0), 4) for s in SYMBOLS},
        "en_olasi": en_olasi,
        "guven": round(olasilik.get(en_olasi, 0.0), 4) if en_olasi else None,
    }


def tahmin_et(mac: dict[str, Any],
              alternatif: dict[str, float] | None = None) -> dict[str, Any]:
    """Tek maçın tahmini: marj arındırılmış 1/0/2 olasılığı.

    **Manşet sayı eğitimsizdir** ve bu bir eksiklik değil ölçüm sonucu:
    dokuz özellik denendi, hiçbiri piyasayı geçemedi (§6.2 A4).

    `alternatif` verilirse korpusta eğitilmiş yeniden kalibrasyonun aynı maça
    verdiği olasılık da taşınır. İkisi **yan yana** durur, biri diğerinin
    yerine geçmez: alternatif ölçüldü ve geçmedi, dolayısıyla manşet olamaz —
    ama ölçüldüğü için de saklanamaz.
    """
    return {
        **{k: mac[k] for k in ("kaynak", "lig", "tarih", "saat", "ev", "dep",
                               "oran_kaynak", "olculen_lig")},
        "oranlar": mac["oranlar"],
        **_blok(implied_probs(mac["oranlar"])),
        "alternatif": ({"ad": ALTERNATIF_AD, **_blok(alternatif)}
                       if alternatif else None),
    }


def _tahminci_skoru(tahminci, haftalar) -> dict[str, Any]:
    """Bir tahmincinin kupon setindeki isabeti — maç ve hafta düzeyinde."""
    from .evaluate import brier, log_kaybi

    n_mac = dogru = 0
    b_top = l_top = 0.0
    hafta_dogru: list[int] = []
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
        "n_mac": n_mac,
        "mac_basina_isabet": round(dogru / n_mac, 4),
        "brier": round(b_top / n_mac, 4),
        "log_kaybi": round(l_top / n_mac, 4),
        "hafta_ortalamasi": round(sum(hafta_dogru) / len(hafta_dogru), 2),
        "en_iyi_hafta": max(hafta_dogru),
        "hafta_14_arti": sum(1 for d in hafta_dogru if d >= 14),
        "hafta_13_arti": sum(1 for d in hafta_dogru if d >= 13),
    }


@lru_cache(maxsize=1)
def olculmus_isabet() -> dict[str, Any]:
    """İki tahmincinin de **ölçülmüş** isabeti — gövdeden ayrılamaz blok.

    Kupon setinde (2025/26, 36 tam hafta, 540 maç) hesaplanır. Hiçbiri elle
    yazılmadı; hepsi arşivden koşar, çünkü elle yazılan bir sayı veri
    kaydığında sessizce yalan söylemeye başlar.

    **Alternatif için ölçüm gerçekten çaprazdır:** 31.103 maçlık korpusta
    eğitilir, 540 maçlık kupon setinde ölçülür ve aralarında **tek bir ortak
    maç yoktur**. Fark, hafta üzerinden eşleştirilmiş bootstrap ile verilir;
    `gecti` yalnızca aralık tamamen sıfırın altındaysa `True` olur.

    Bugün `gecti=False` çıkıyor ve gövde bunu **saklamaz**: alternatif
    ortalamada daha iyi ama 540 maçta anlamlılık kurulamıyor. Kullanıcı iki
    sayıyı da, aradaki farkı da, farkın belirsizliğini de görür.
    """
    from .backtest import hafta_girdileri
    from .evaluate import bootstrap_farki
    from .predict import PiyasaTahminci

    haftalar = [h for h in hafta_girdileri() if h["usable"]]
    if not haftalar:
        return {"olculdu": False,
                "not": "oran arsivi eksik — isabet olculemedi"}

    manset = _tahminci_skoru(PiyasaTahminci(), haftalar)
    out: dict[str, Any] = {
        "olculdu": True,
        "kesit": "2025/26 Spor Toto kuponu — football-data kapanış oranı",
        "n_hafta": len(haftalar),
        "referans": MANSET_AD,
        "manset": {"ad": MANSET_AD,
                   "aciklama": "Marj arındırılmış piyasa fiyatı — eğitimsiz",
                   **manset},
        "alternatif": None,
    }

    alternatif = _egitilmis_alternatif()
    if alternatif is None:
        return out

    # Kat yok: alternatif KORPUSTA egitildi, burada yalnizca olculuyor.
    # Egitim ve sinav setleri ayrik oldugu icin sizinti mumkun degil.
    from .evaluate import _hafta_skoru

    skor = _tahminci_skoru(alternatif, haftalar)
    a_kayit = [_hafta_skoru(alternatif, h) for h in haftalar]
    m_kayit = [_hafta_skoru(PiyasaTahminci(), h) for h in haftalar]
    fark = bootstrap_farki(a_kayit, m_kayit)
    out["alternatif"] = {
        "ad": ALTERNATIF_AD,
        "aciklama": ("31.103 maçlık korpusta eğitilmiş yeniden kalibrasyon "
                     "(3 parametre); kupon setinde ölçüldü, ortak maç yok"),
        **skor,
        "fark": fark,
        # Karar HAM ustten verilir: `round(-0.000031, 4)` `-0.0` verir ve
        # `-0.0 < 0` False'tur — aralik tamamen sifirin altindayken aday
        # "gecmedi" diye yazilirdi (bkz. evaluate.bootstrap_farki yorumu).
        "gecti": bool(fark["ham_ust"] is not None and fark["ham_ust"] < 0),
    }
    return out


def _uyarilar(maclar: Sequence[dict[str, Any]]) -> list[dict[str, str]]:
    """Gövdenin taşımak zorunda olduğu sınırlar. **Kısaltılmaz.**"""
    out = [
        {"ad": "tek_kolon_14_tutmaz",
         "metin": ("Bu tahminci tek kolonla 14+ tutturamaz ve bu modelin kusuru "
                   "degil ARITMETIKTIR: piyasanin kendi olasiliklarindan "
                   "P(14+) ≈ 1/1.161 hafta. 36 haftada beklenen 0,031, "
                   "gozlenen 0. 14+'a kaplama motoru tasir, tahminci degil.")},
        {"ad": "model_yok",
         "metin": ("Manset olasiliklar piyasa fiyatidir. Dokuz ozellik "
                   "denendi, hicbiri piyasayi out-of-sample gecemedi "
                   "(§6.2 A4) — yani bu bir eksiklik degil olcum sonucudur.")},
        {"ad": "alternatif_gecmedi",
         "metin": ("Yanindaki `kalibre_bias`, 31.103 maclik korpusta "
                   "egitilmis 3 parametreli bir yeniden kalibrasyondur ve "
                   "540 maclik kupon setinde ORTALAMADA daha iyi cikiyor "
                   "(0,5732'ye karsi 0,5740). Ama guven araligi sifiri "
                   "iceriyor: 540 macta anlamlilik KURULAMIYOR. Bu yuzden "
                   "manset degil, olculmus alternatif olarak duruyor.")},
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


def rapor(fixtures_yolu: str | None = None,
          iddaa_yolu: str | None = None,
          limit: int | None = None) -> dict[str, Any]:
    """Tahmin gövdesi — olasılıklar ve ölçülmüş isabet, **birlikte.**

    İkisi ayrılamaz. Bir arayüz olasılıkları alıp isabeti atarsa, projenin
    baştan beri karşı çıktığı şeyi üretmiş olur.
    """
    maclar = yaklasan_maclar(fixtures_yolu, iddaa_yolu)

    # Alternatif TEK SEFERDE, toplu hesaplanir: kademe tahmincisi hafta
    # duzeyinde calisir ve mac basina cagirmak hem yavas hem gereksiz olurdu.
    alt_olasiliklar: list[dict[str, float] | None] = [None] * len(maclar)
    alternatif = _egitilmis_alternatif()
    if alternatif is not None and maclar:
        cikti = alternatif.tahmin(_sozde_hafta(maclar))
        alt_olasiliklar = list(cikti)[:len(maclar)]

    tahminler = [tahmin_et(m, alt_olasiliklar[i]) for i, m in enumerate(maclar)]
    tahminler.sort(key=lambda t: (t["tarih"], t["saat"], t["lig"], t["ev"]))
    if limit is not None:
        tahminler = tahminler[:limit]

    kaynaklar = sorted({t["kaynak"] for t in tahminler})
    # Alternatif KAC macta baska bir sembol seciyor.
    #
    # Bu sayi, alternatifin ne ise yarayip yaramadigini okumanin en dogrudan
    # yolu: sicaklik + sinif sabiti bir yeniden kalibrasyondur, siralamayi
    # neredeyse hic degistirmez — yalnizca GUVENI keskinlestirir. Sifir
    # cikiyorsa tek kolon oynayan biri icin iki tahminci AYNIDIR ve fark
    # ancak olasiliga dayali bir karar (kupon kurma) icin anlamlidir.
    # Kullanicinin bunu tahmin etmesi degil, gormesi gerekir.
    farkli = sum(1 for t in tahminler
                 if t.get("alternatif")
                 and t["alternatif"]["en_olasi"] != t["en_olasi"])
    return {
        "n_mac": len(tahminler),
        "kaynaklar": kaynaklar,
        "alternatif_farkli_secim": farkli,
        "olculen_kaynak": KAYNAK_OLCULEN in kaynaklar,
        "tahminler": tahminler,
        "olculmus_isabet": olculmus_isabet(),
        "uyarilar": _uyarilar(maclar),
        "bos_sebep": (None if tahminler else
                      "yaklasan mac yok — fikstur yuvarlanan penceredir ve "
                      "hafta oynandiginda bosalir; iddaa bulteni de bos ya da "
                      "alinmamis olabilir"),
    }


def _yazdir(g: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    i = g["olculmus_isabet"]
    print(f"YAKLASAN {g['n_mac']} MAC · kaynak: {', '.join(g['kaynaklar']) or '—'}")
    if g["n_mac"] and g.get("alternatif_farkli_secim") is not None:
        f = g["alternatif_farkli_secim"]
        print(f"alternatif {f}/{g['n_mac']} macta farkli sembol seciyor"
              + ("  — tek kolon icin ikisi AYNI" if not f else ""))
    if not g["n_mac"]:
        print(f"\n{g['bos_sebep']}")
        return
    print(f"\n{'tarih':<11} {'saat':<6} {'lig':<6} {'ev':<18} {'dep':<18} "
          f"{'1':>6} {'0':>6} {'2':>6}  {'sec':>3} {'guven':>6} {'alt':>7}")
    for t in g["tahminler"]:
        o = t["olasilik"]
        a = t.get("alternatif")
        # Alternatif ayni sembolu seciyorsa yalnizca guveni yazilir; FARKLI
        # sembol seciyorsa sembol de yazilir — asil bilgi orada.
        alt = ""
        if a and a["en_olasi"]:
            ayni = a["en_olasi"] == t["en_olasi"]
            alt = (f"{a['guven']*100:.1f}%" if ayni
                   else f"{a['en_olasi']} {a['guven']*100:.0f}%")
        print(f"{t['tarih']:<11} {t['saat']:<6} {t['lig'][:6]:<6} "
              f"{t['ev'][:18]:<18} {t['dep'][:18]:<18} "
              f"{o['1']:.3f}  {o['0']:.3f}  {o['2']:.3f}  {t['en_olasi']:>3} "
              f"{t['guven']*100:>5.1f}% {alt:>7}")
    if i.get("olculdu"):
        print(f"\nOLCULMUS ISABET ({i['kesit']}, {i['n_hafta']} hafta):")
        print(f"  {'tahminci':<16} {'brier':>8} {'isabet':>8} {'hafta':>8} "
              f"{'fark':>9} {'%95 aralik':>20}  gecti")
        for anahtar in ("manset", "alternatif"):
            b = i.get(anahtar)
            if not b:
                continue
            f = b.get("fark")
            ar = f"[{f['alt']:+.4f}, {f['ust']:+.4f}]" if f else ""
            fk = f"{f['fark']:+.4f}" if f else ""
            g = "" if b.get("gecti") is None else ("EVET" if b["gecti"] else "hayir")
            print(f"  {b['ad']:<16} {b['brier']:>8.4f} "
                  f"{100*b['mac_basina_isabet']:>7.1f}% "
                  f"{b['hafta_ortalamasi']:>7}  {fk:>9} {ar:>20}  {g}")
    print("\nSINIRLAR:")
    for u in g["uyarilar"]:
        print(f"  [{u['ad']}] {u['metin']}")


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    _yazdir(rapor(limit=20))
