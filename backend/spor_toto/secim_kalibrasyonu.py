"""Seçim koşullu kalibrasyon — *"seçtiğimiz yerde olasılık tutuyor mu?"*

`kalibrasyon.py` şunu sorar: *piyasa bir olasılık söylediğinde o olasılık
tutuyor mu?* Cevabı **bütün maçlar** üzerinden verir. `beraberlik.py` aynı
soruyu favori gücü bandına koşullu sorar. İkisi de bir **ortak değişkene**
koşulludur.

Bu modül farklı bir şeye koşullar: **seçim kuralının kendisine**. Soru şu —
*bir kural bir noktayı seçtiğinde, o noktada söylenen olasılık hâlâ tutuyor
mu, yoksa kural tam da modelin yanıldığı yeri mi seçiyor?*

─── Neden ayrı bir soru ──────────────────────────────────────────────────

`deger.olc()` seçilen kümede yalnızca **ekonomik** sonucu ölçüyor: verim,
bootstrap aralığı, Sharpe. Yani seçilen bahislerin kâr etmediğini biliyoruz.
Bilmediğimiz şey **niçin**: kaybın ne kadarı marj, ne kadarı modelin kestirim
gürültüsü. Bu ayrımı yalnızca seçim koşullu kalibrasyon yapar.

Soru dışarıdan geldi ve üç bağımsız depoda ölçüldü (`docs/` altındaki dış
inceleme serisinin devamı):

* `mperi1208/value-bet-model` — *"küresel olarak iyi kalibre, ama seçtiği
  bahislerde sistematik aşırı güvenli; `p_model − p_piyasa > eşik`
  koşullaması modelin kestirim gürültüsünü seçiyor."*
* `thewongdirection/soccer-betting-strategy` — *"overconfident on its bet
  subset (model 0,45 vs realised 0,34) … being more selective makes it
  worse."*
* `jkrusina/SoccerPredictor` — aynı yapıyı ölçmedi ve %1069 kâr raporladı.

─── ÖLÇÜLDÜ: kupon bankosu bu soruyu SORAMAZ ────────────────────────────

İlk tasarım kupon bankosunu (`backtest.secim_uret`) koşullama kuralı
yapacaktı. Uygulamadan önce sınandı ve **dejenere** çıktı:

    esik = 0,68
    band (0,60–0,70)  p = 0,601 · 0,650 · 0,699  → banko? Hayır · Hayır · EVET
    band (0,70–0,80)  p = 0,701 · 0,750 · 0,799  → banko? EVET · EVET · EVET
    band (0,80–1,01)  p = 0,801 · 0,905 · 1,009  → banko? EVET · EVET · EVET

Sebep tek cümlede: **banda ayırdığın değişkenle eşikliyorsan, eşiğin tamamen
üstündeki bantta seçilen küme kümenin kendisidir.** Bant içi karşıtlık yalnızca
eşiği kesen tek bantta kalır, o da ölçüm değil artıktır.

Buradan modülün kuralı çıkıyor ve iki aracın seçimini o kural belirledi:

    Seçim koşullu kalibrasyon ancak kural, banda ayrılan olasılığın
    ÖTESİNDE bir bilgi kullanıyorsa anlamlıdır.

─── İki araç, ikisi de bu şartı sağlıyor ────────────────────────────────

``model``
    Banda ayıran: `p_model`. Seçen: `p_model − p_piyasa > eşik`.
    Fazladan bilgi **piyasa fiyatıdır**. Dış depoların ölçtüğü olgunun birebir
    karşılığı budur. Tahminler `evaluate.hafta_disarida_birak` ile **sezon
    dışarıda bırakmalı** üretilir; içeride uydurulmuş bir tahminci kendi
    kalibrasyonunu ölçemez.

``deger``
    Banda ayıran: `p` (`Avg` konsensüsü, marj arındırılmış).
    Seçen: `deger.sec` → `p·o − 1 > alpha`, fazladan bilgi **`Max` fiyatıdır**.
    Sorduğu şey biraz farklıdır ve öyle okunmalıdır: *en iyi fiyatın
    konsensüsü geçtiği ayaklarda konsensüs hâlâ dürüst mü?*

─── Bu modül bir eşik SEÇMEZ ────────────────────────────────────────────

`deger.py`nin üç parçalı yapısındaki tarama burada bir **duyarlılık
analizidir**, bir arama değil: eşik bir koşullama değişkenidir, optimize
edilen bir parametre değil. Manşet her zaman sabit varsayılan eşiktir;
`--tarama` yalnızca dış depoların öngörüsünü sınar (*"eşiği yükseltmek
durumu kötüleştirir"*). Izgaranın "en iyi" satırı manşet DEĞİLDİR.

    python -m spor_toto.secim_kalibrasyonu
    python -m spor_toto.secim_kalibrasyonu --esik 0.08 --sezon-kirilimi
    python -m spor_toto.secim_kalibrasyonu --kural deger --tarama
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from .history import SYMBOLS
from .odds import ARINDIRMA_VARSAYILAN
from .ortak import OLASILIK_BANTLARI, wilson

#: `kalibrasyon.BANTLAR` ile **aynı** dizi. Ayrı bir tanım, eğrinin
#: söylediğiyle bu modülün söylediğini sessizce ayrıştırırdı.
BANTLAR = OLASILIK_BANTLARI

#: Bir bandın yazılması için gereken en az nokta — `kalibrasyon.EN_AZ_BANT`
#: ile aynı gerekçe (altında yüzde okunmaz). Seçilen alt küme küçüldüğü için
#: burada daha sık devreye girer ve **kaç bandın düştüğü rapora yazılır**;
#: sessizce düşen bant, kesiti daraltıp bunu söylememek olurdu.
EN_AZ_BANT = 100

#: Model kuralının varsayılan eşiği. `deger.ALPHA_VARSAYILAN` ile aynı
#: gerekçeyle **ölçüm görülmeden** seçildi: modelin piyasadan sapması bu
#: kadarını geçtiğinde "seçildi" sayılır.
ESIK_VARSAYILAN = 0.02

#: Duyarlılık ızgarası. Kenarları kaba ve ölçüm sonucuna bakılmadan seçildi
#: (`deger.ALPHA_IZGARASI` ile aynı gerekçe).
ESIK_IZGARASI: tuple[float, ...] = (0.0, 0.01, 0.02, 0.04, 0.08)

#: Bir nokta: (söylenen olasılık, gerçekleşti mi, **sezon**).
#:
#: Sezon etiketi bu üçüncü alanla taşınıyor çünkü bu deponun bir sayıya
#: "bulgu" demeden önce sorduğu iki sorudan biri odur (`§3.21`/Ö3):
#: *"sezon sezon işaret tutuyor mu?"* Havuzlanmış bir sapma, sezonların
#: yarısının taşıdığı bir şey olabilir ve Ö3 tam bu sınavda "şekil
#: gerçek, büyüklük yok"a düştü. Etiket olmadan o sınav kurulamaz.
Nokta = tuple[float, bool, str]


def _bant_satiri(grup: Sequence[Nokta], lo: float, hi: float) -> dict[str, Any] | None:
    """Tek bandın Wilson satırı; nokta `EN_AZ_BANT`ın altındaysa `None`.

    Satır şeması `kalibrasyon.kalibrasyon_egrisi`inkiyle bilerek aynı:
    aynı soruyu soran iki tablo aynı sütunlarla okunmalı.
    """
    n = len(grup)
    if n < EN_AZ_BANT:
        return None
    k = sum(1 for t in grup if t[1])
    soylenen = sum(t[0] for t in grup) / n
    gercek = k / n
    alt, ust = wilson(k, n)
    return {
        "lo": lo, "hi": hi, "n": n,
        "soylenen": soylenen, "gercek": gercek,
        # `fark` bilerek `kalibrasyon.kalibrasyon_egrisi` ile AYNI
        # işarette (gerçek − söylenen); iki tablo yan yana okunacak.
        # `asiri_guven` onun tersidir (söylenen − gerçek) ve özetle aynı
        # yöne bakar — biri pozitifken öteki negatif olmasın diye ikisi
        # de taşınıyor, biri türetilip okurun kafasında çevrilmiyor.
        "fark": gercek - soylenen,
        "asiri_guven": soylenen - gercek,
        "ga_alt": alt, "ga_ust": ust,
        "icinde": alt <= soylenen <= ust,
    }


def egri(noktalar: Sequence[Nokta]) -> dict[str, Any]:
    """Nokta kümesini banda bölüp Wilson satırlarını üretir.

    `kalibrasyon.kalibrasyon_egrisi`in gövdesiyle aynı iş; farkı, korpusu
    kendi okumak yerine **verilen** noktaları alması — çünkü burada nokta
    kümesi bir seçim kuralıyla süzülüyor.
    """
    satirlar: list[dict[str, Any]] = []
    dusen = 0
    for lo, hi in BANTLAR:
        grup = [t for t in noktalar if lo <= t[0] < hi]
        if not grup:
            continue
        satir = _bant_satiri(grup, lo, hi)
        if satir is None:
            dusen += 1
            continue
        satirlar.append(satir)
    return {
        "n": len(noktalar),
        "bantlar": satirlar,
        "sapan_bant": sum(0 if r["icinde"] else 1 for r in satirlar),
        "toplam_bant": len(satirlar),
        "dusen_bant": dusen,
    }


def noktalar_model(fabrika: Any,
                   haftalar: Sequence[dict[str, Any]],
                   esik: float = ESIK_VARSAYILAN
                   ) -> tuple[list[Nokta], list[Nokta]]:
    """Model kuralı: banda ayıran `p_model`, seçen `p_model − p_piyasa > esik`.

    Tahminler **sezon dışarıda bırakmalı** üretilir (`evaluate.sezon_anahtari`):
    kendi eğitim setinde uydurulmuş bir tahminci kendi kalibrasyonunu ölçemez —
    `kalibrasyon.py`nin izotonik uyarısıyla aynı gerekçe.

    Dönen ikili: (bütün noktalar, kuralın seçtiği noktalar). İkincisi her
    zaman birincinin alt kümesidir ve bekçi bunu sınar.
    """
    from .evaluate import hafta_disarida_birak, sezon_anahtari

    kayitlar = hafta_disarida_birak(fabrika, haftalar, grup=sezon_anahtari)
    hepsi: list[Nokta] = []
    secilen: list[Nokta] = []
    for hafta, kayit in zip(haftalar, kayitlar):
        piyasa = hafta.get("probs") or []
        tahminler = kayit["_tahminler"]
        kodlar = kayit["_kodlar"]
        for i, kod in enumerate(kodlar):
            if i >= len(tahminler) or i >= len(piyasa) or not piyasa[i]:
                continue
            p_model = tahminler[i]
            p_piyasa = piyasa[i]
            for s in SYMBOLS:
                pm = float(p_model.get(s, 0.0))
                nokta: Nokta = (pm, kod == s, str(hafta.get("sezon") or ""))
                hepsi.append(nokta)
                if pm - float(p_piyasa.get(s, 0.0)) > esik:
                    secilen.append(nokta)
    return hepsi, secilen


#: `deger` kuralının ölçülebildiği pazarlar. `AH` **bilerek dışarıda**:
#: iade (push) yüzünden `para` sıfır ya da kesirli olabiliyor, yani "bu ayak
#: tuttu mu" ikili bir soru olmaktan çıkıyor. Kalibrasyon ikili sonuç ister;
#: yarım tutan bir ayağı "tuttu" ya da "tutmadı" saymak ölçümü sessizce
#: bozardı (`deger._ah_para_getirisi` iadeyi 0 sayar, `pazar._ah_getiri` 0,5).
DEGER_PAZARLARI: tuple[str, ...] = ("1X2", "2.5")


def noktalar_deger(pazar: str = "1X2",
                   alpha: float = 0.05,
                   yontem: str = ARINDIRMA_VARSAYILAN
                   ) -> tuple[list[Nokta], list[Nokta]]:
    """Değer kuralı: banda ayıran `p` (Avg), seçen `deger.sec` (`p·o − 1 > alpha`).

    Fazladan bilgi `Max` fiyatıdır, yani kural banda ayrılan olasılığın
    ötesinde bir şey görüyor — modülün başlığındaki şart sağlanıyor.
    """
    from .deger import GRUPLAR, kayitlar, sec

    if pazar not in DEGER_PAZARLARI:
        raise ValueError(
            f"{pazar!r} bu ölçüme girmiyor (iade ikili sonucu bozar); "
            f"seçenekler: {', '.join(DEGER_PAZARLARI)}")

    hepsi: list[Nokta] = []
    secilen: list[Nokta] = []
    for kayit in kayitlar(pazar, yontem):
        secili = sec(kayit, alpha)
        for ayak in GRUPLAR[pazar]:
            nokta: Nokta = (float(kayit["p"][ayak]),
                            kayit["para"][ayak] > 0,
                            str(kayit.get("sezon") or ""))
            hepsi.append(nokta)
            if ayak == secili:
                secilen.append(nokta)
    return hepsi, secilen


def _ozet(noktalar: Sequence[Nokta]) -> dict[str, Any]:
    """Nokta kümesinin tek satırlık özeti: söylenen ↔ gerçek ve aşırı güven.

    `asiri_guven` = söylenen − gerçek. **Pozitifi** aşırı güvendir: model
    olduğundan çok söylemiştir. Dış depoların bulduğu işaret budur.
    """
    n = len(noktalar)
    if not n:
        return {"n": 0, "soylenen": None, "gercek": None,
                "asiri_guven": None, "ga_alt": None, "ga_ust": None}
    k = sum(1 for t in noktalar if t[1])
    soylenen = sum(t[0] for t in noktalar) / n
    gercek = k / n
    alt, ust = wilson(k, n)
    return {
        "n": n, "soylenen": soylenen, "gercek": gercek,
        "asiri_guven": soylenen - gercek,
        "ga_alt": alt, "ga_ust": ust,
        # Söylenen olasılık gerçekleşenin Wilson aralığının DIŞINDAysa fark
        # gürültüyle açıklanamıyor demektir; okunacak bayrak budur.
        "icinde": alt <= soylenen <= ust,
    }


def eslestir(hepsi: Sequence[Nokta], secilen: Sequence[Nokta]) -> dict[str, Any]:
    """Aynı bantlarda `hepsi` ↔ `secilen` eşleştirilmiş tablo.

    Eşleştirme bandın kimliği üzerinden yapılır; bir bant yalnız bir tarafta
    yazılabiliyorsa (öteki tarafta `EN_AZ_BANT` altında kaldıysa) o bant
    **karşılaştırmaya girmez** ve `eslesmeyen_bant` sayar. Yarım eşleşmeyi
    tabloya koymak, iki farklı kesiti aynı satırda göstermek olurdu.
    """
    e_hepsi = egri(hepsi)
    e_secilen = egri(secilen)
    sag = {(r["lo"], r["hi"]): r for r in e_secilen["bantlar"]}
    satirlar: list[dict[str, Any]] = []
    eslesmeyen = 0
    for r in e_hepsi["bantlar"]:
        s = sag.get((r["lo"], r["hi"]))
        if s is None:
            eslesmeyen += 1
            continue
        satirlar.append({"lo": r["lo"], "hi": r["hi"], "hepsi": r, "secilen": s})
    return {
        "bantlar": satirlar,
        "eslesmeyen_bant": eslesmeyen,
        "dusen_bant_secilen": e_secilen["dusen_bant"],
        "sapan_bant_hepsi": e_hepsi["sapan_bant"],
        "sapan_bant_secilen": e_secilen["sapan_bant"],
        # Paydalar AYRI durmak zorunda: `sapan_bant_*` her eğrinin KENDİ
        # bant sayısına göre sayılır, eşleşen tabloya göre değil. Tek payda
        # kullanmak, seçilen taraf inceldiğinde "6/0" gibi okunamaz bir
        # oran üretiyordu.
        "toplam_bant_hepsi": e_hepsi["toplam_bant"],
        "toplam_bant_secilen": e_secilen["toplam_bant"],
        "ozet_hepsi": _ozet(hepsi),
        "ozet_secilen": _ozet(secilen),
        "secim_orani": len(secilen) / len(hepsi) if hepsi else 0.0,
    }


# ─── çok kıyas (Bonferroni) ──────────────────────────────────────────────────
#
# `§3.21` (Ö3) bu deponun standardını koyuyor: *"Beş bant bakıldı; birinin
# %95 aralığının dışına düşmesi tek başına bulgu değil."* Bu modül bir
# koşumda ONLARCA aralık okuyor (bant × eşik), yani düzeltme isteğe bağlı
# değil. Rapor kıyas sayısını ve düzeltilmiş aralığı KENDİ yazar; okurun
# hesaplaması gereken bir şey bırakmaz.


def _z(alfa: float) -> float:
    """İki yanlı `alfa` için standart normal kritik değer.

    `ortak.wilson` %95'e sabittir (`GUVEN_Z`); Bonferroni düzeltilmiş aralık
    başka bir `z` ister. Ters normal kapalı formda yoktur; `statistics`in
    `NormalDist.inv_cdf`ı standart kütüphanededir ve yeni bağımlılık getirmez.
    """
    from statistics import NormalDist
    return NormalDist().inv_cdf(1.0 - alfa / 2.0)


def wilson_z(basari: int, n: int, z: float) -> tuple[float, float]:
    """`ortak.wilson`ın `z` parametreli hâli — gövde birebir aynı.

    Ayrı durmasının tek sebebi `ortak.GUVEN_Z`in sabit olması. Formül
    kopyalanmadı, genelleştirildi: `z = ortak.GUVEN_Z` verilirse `ortak.wilson`
    ile **aynı** sayıyı döndürür ve bekçi bunu sınar.
    """
    if n <= 0:
        return 0.0, 0.0
    import math
    p = basari / n
    payda = 1 + z * z / n
    merkez = (p + z * z / (2 * n)) / payda
    yari = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / payda
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


def bonferroni(noktalar: Sequence[Nokta], kiyas: int) -> dict[str, Any]:
    """`kiyas` kadar aralık okunduğunda bu kümenin sapması hâlâ duruyor mu.

    Düzeltilmiş düzey `0,05 / kiyas`; `kiyas=1` verilirse sonuç `%95` ile,
    yani `_ozet`le aynıdır.
    """
    n = len(noktalar)
    if not n:
        return {"kiyas": kiyas, "alfa": None, "icinde": None,
                "ga_alt": None, "ga_ust": None}
    alfa = 0.05 / max(1, kiyas)
    k = sum(1 for t in noktalar if t[1])
    soylenen = sum(t[0] for t in noktalar) / n
    alt, ust = wilson_z(k, n, _z(alfa))
    return {"kiyas": kiyas, "alfa": alfa, "ga_alt": alt, "ga_ust": ust,
            "icinde": alt <= soylenen <= ust}


# ─── sezon kırılımı ──────────────────────────────────────────────────────────

def sezonlar(noktalar: Sequence[Nokta]) -> list[str]:
    """Nokta kümesindeki sezon etiketleri, sıralı ve tekilleştirilmiş."""
    return sorted({t[2] for t in noktalar if t[2]})


def sezon_kirilimi(secilen: Sequence[Nokta]) -> list[dict[str, Any]]:
    """Sezon sezon aşırı güven — `§3.21`in ikinci uyarısının aracı.

    Havuzlanmış bir sapmanın kaç sezonun taşıdığını söyler. İşaret sezonlar
    arasında dönüyorsa bulgu "şekil gerçek, büyüklük yok"tur; Ö3 tam olarak
    bu sınavda düştü ve bu modülün ölçümü de aynı sınava girmek zorunda.
    """
    out: list[dict[str, Any]] = []
    for sz in sezonlar(secilen):
        alt_kume = [t for t in secilen if t[2] == sz]
        out.append({"sezon": sz, **_ozet(alt_kume)})
    return out


def olc(kural: str = "model",
        esik: float = ESIK_VARSAYILAN,
        alpha: float = 0.05,
        pazar: str = "1X2",
        aday: str = "izotonik",
        last: int | None = None) -> dict[str, Any]:
    """Bir seçim kuralı için eşleştirilmiş kalibrasyon raporu.

    `kural="model"` dış depoların ölçtüğü olgunun birebir karşılığıdır;
    `kural="deger"` konsensüs ↔ en iyi fiyat sorusunu sorar (modül başlığı).
    """
    if kural == "model":
        from .evaluate import kupon_kesiti_tum
        from .recalibrate import IzotonikTahminci
        adaylar: dict[str, Any] = {"izotonik": IzotonikTahminci}
        if aday not in adaylar:
            raise ValueError(f"bilinmeyen aday {aday!r}; seçenekler: {', '.join(adaylar)}")
        haftalar = kupon_kesiti_tum(last)
        hepsi, secilen = noktalar_model(adaylar[aday], haftalar, esik)
        baglam: dict[str, Any] = {"aday": aday, "esik": esik, "n_hafta": len(haftalar)}
    elif kural == "deger":
        hepsi, secilen = noktalar_deger(pazar, alpha)
        baglam = {"pazar": pazar, "alpha": alpha}
    else:
        raise ValueError(f"bilinmeyen kural {kural!r}; seçenekler: model, deger")

    sonuc = {"kural": kural, **baglam, **eslestir(hepsi, secilen)}
    # Kıyas sayısı: seçilen tarafta okunan her bant aralığı + toplam
    # aralık. Rapor kendi düzeltmesini taşısın ki bir bandın yıldızı
    # "bulgu" diye okunmasın (`§3.21`in birinci uyarısı).
    kiyas = int(sonuc["toplam_bant_secilen"]) + 1
    sonuc["bonferroni"] = bonferroni(secilen, kiyas)
    sonuc["sezon_kirilimi"] = sezon_kirilimi(secilen)
    return sonuc


def tarama(kural: str = "model",
           izgara: Sequence[float] = ESIK_IZGARASI,
           **kw: Any) -> list[dict[str, Any]]:
    """Eşik boyunca duyarlılık — **arama değil**.

    Dış depoların öngörüsünü sınar: *"daha seçici olmak durumu kötüleştirir."*
    Doğruysa `asiri_guven` eşikle birlikte **büyümeli**. Izgaranın "en iyi"
    satırı manşet değildir ve rapor onu ayrıca işaretlemez (modül başlığı).
    """
    anahtar = "alpha" if kural == "deger" else "esik"
    out: list[dict[str, Any]] = []
    for e in izgara:
        # Dinamik `**{anahtar: e}` yerine açık dallanma: eşiğin hangi
        # kurala gittiği okunur kalsın ve tip denetimi kurabilsin.
        sonuc = (olc(kural, alpha=e, **kw) if kural == "deger"
                 else olc(kural, esik=e, **kw))
        kir = sonuc["sezon_kirilimi"]
        isaretler = {(r["asiri_guven"] or 0) > 0 for r in kir}
        out.append({
            anahtar: e,
            "n_secilen": sonuc["ozet_secilen"]["n"],
            "secim_orani": sonuc["secim_orani"],
            "asiri_guven": sonuc["ozet_secilen"]["asiri_guven"],
            "icinde": sonuc["ozet_secilen"]["icinde"],
            # Düzeltilmiş aralık ve işaret kararlılığı: taramanın "*"
            # işaretleri düzeltmesiz okunursa beş iç içe alt küme beş
            # bağımsız sınama sanılır.
            "bonferroni_icinde": sonuc["bonferroni"]["icinde"],
            "n_sezon": len(kir),
            "isaret_tutuyor": len(isaretler) == 1 if kir else None,
        })
    return out


def _yuzde(x: float | None) -> str:
    """Yüzde biçimi; ölçülmemiş değer sıfır yazılmaz, tire yazılır."""
    return "—" if x is None else f"{100 * x:5.1f}%"


def _yaz(sonuc: dict[str, Any],
         sezon_tablosu: bool = False) -> None:  # pragma: no cover - elle kullanım
    """Eşleştirilmiş tabloyu ve iki özeti okunur biçimde yazar.

    `sezon_tablosu` yalnızca **dökümü** açar. Sezon işareti verdikti (tutuyor /
    dönüyor) bayraktan bağımsız her zaman yazılır: `§3.21`in ikinci uyarısı
    isteğe bağlı bir ek değil, bir sayıya "bulgu" demenin şartıdır.
    """
    print(f"kural: {sonuc['kural']}  ·  " +
          "  ·  ".join(f"{k}={v}" for k, v in sonuc.items()
                       if k in ("aday", "esik", "pazar", "alpha", "n_hafta")))
    h, s = sonuc["ozet_hepsi"], sonuc["ozet_secilen"]
    print(f"nokta: hepsi {h['n']:,} · seçilen {s['n']:,} "
          f"(%{100 * sonuc['secim_orani']:.1f})")
    print()
    print(f"{'bant':>12} | {'n':>7} {'söyl.':>7} {'gerç.':>7} {'aş.güv':>7} | "
          f"{'n':>6} {'söyl.':>7} {'gerç.':>7} {'aş.güv':>7}  GA")
    print("-" * 92)
    for r in sonuc["bantlar"]:
        a, b = r["hepsi"], r["secilen"]
        bayrak = " " if b["icinde"] else "*"
        print(f"{r['lo']:.2f}–{r['hi']:.2f}".rjust(12) +
              f" | {a['n']:7,} {_yuzde(a['soylenen'])} {_yuzde(a['gercek'])} "
              f"{_yuzde(a['asiri_guven'])} | {b['n']:6,} {_yuzde(b['soylenen'])} "
              f"{_yuzde(b['gercek'])} {_yuzde(b['asiri_guven'])} {bayrak}")
    print("-" * 92)
    print(f"aşırı güven (söylenen − gerçek):  hepsi {_yuzde(h['asiri_guven'])}"
          f"   ·   seçilen {_yuzde(s['asiri_guven'])}")
    print(f"  seçilen küme Wilson içinde mi: "
          f"{'EVET — ters seçim işareti yok' if s['icinde'] else 'HAYIR — sapma gürültüyle açıklanmıyor'}")
    b = sonuc["bonferroni"]
    if b["alfa"] is not None:
        print(f"  çok kıyas: {b['kiyas']} aralık okundu → Bonferroni düzeyi "
              f"%{100 * b['alfa']:.3f}; düzeltilmiş aralıkta "
              f"{'İÇİNDE' if b['icinde'] else 'DIŞINDA'}")
    kir = sonuc.get("sezon_kirilimi") or []
    if kir:
        if sezon_tablosu:
            print("\nsezon sezon aşırı güven (§3.21'in ikinci uyarısı):")
            for r in kir:
                print(f"  {r['sezon']:>10}  n={r['n']:>6,}  {_yuzde(r['asiri_guven'])}"
                      f"  {'' if r['icinde'] else '*'}")
        isaretler = {(r["asiri_guven"] or 0) > 0 for r in kir}
        tutuyor = len(isaretler) == 1
        print(f"  sezon işareti ({len(kir)} sezon): " +
              ("TUTUYOR — hepsi aynı yönde" if tutuyor
               else "DÖNÜYOR — havuzlanmış sapma bütün sezonların değil") +
              ("" if sezon_tablosu else "  (döküm: --sezon-kirilimi)"))
    print(f"sapan bant: hepsi {sonuc['sapan_bant_hepsi']}/{sonuc['toplam_bant_hepsi']}"
          f" · seçilen {sonuc['sapan_bant_secilen']}/{sonuc['toplam_bant_secilen']}"
          f" · eşleşmeyen {sonuc['eslesmeyen_bant']}"
          f" · seçilen tarafta düşen {sonuc['dusen_bant_secilen']}")
    if not sonuc["bantlar"]:
        print(f"\n! Bant tablosu BOŞ: seçilen küme ({s['n']:,} nokta) "
              f"bant başına {EN_AZ_BANT} noktayı hiçbir bantta bulmuyor.\n"
              "  Okunacak sayı yalnızca yukarıdaki toplam aşırı güvendir; "
              "bant bant karşılaştırma bu kesitte kurulamaz.")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI girişi: tek ölçüm ya da eşik duyarlılığı."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kural", choices=("model", "deger"), default="model")
    ap.add_argument("--esik", type=float, default=ESIK_VARSAYILAN)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--pazar", default="1X2", choices=DEGER_PAZARLARI)
    ap.add_argument("--aday", default="izotonik")
    ap.add_argument("--last", type=int, default=None)
    ap.add_argument("--sezon-kirilimi", action="store_true",
                    dest="sezon_kirilimi",
                    help="sezon sezon aşırı güven (§3.21'in ikinci uyarısı)")
    ap.add_argument("--tarama", action="store_true",
                    help="eşik duyarlılığı (arama DEĞİL — manşet sabit eşiktir)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    kw: dict[str, Any] = ({"pazar": a.pazar} if a.kural == "deger"
                          else {"aday": a.aday, "last": a.last})
    if a.tarama:
        sonuc: Any = tarama(a.kural, **kw)
    else:
        sonuc = olc(a.kural, esik=a.esik, alpha=a.alpha, **kw)

    if a.json:
        print(json.dumps(sonuc, ensure_ascii=False, indent=2, default=float))
    elif a.tarama:
        anahtar = "alpha" if a.kural == "deger" else "esik"
        print(f"{anahtar:>6} {'n':>8} {'oran':>7} {'aşırı güven':>12}  GA  Bonf.  işaret")
        for r in sonuc:
            bayrak = " " if r["icinde"] else "*"
            bonf = "içinde" if r["bonferroni_icinde"] else "DIŞINDA"
            isaret = ("—" if r["isaret_tutuyor"] is None
                      else ("tutuyor" if r["isaret_tutuyor"] else "DÖNÜYOR"))
            print(f"{r[anahtar]:6.2f} {r['n_secilen']:8,} "
                  f"{100 * r['secim_orani']:6.1f}% {_yuzde(r['asiri_guven'])} {bayrak} "
                  f"{bonf:>7}  {isaret}")
    else:
        _yaz(sonuc, sezon_tablosu=a.sezon_kirilimi)
    return 0


if __name__ == "__main__":  # pragma: no cover - elle kullanım
    raise SystemExit(main())
