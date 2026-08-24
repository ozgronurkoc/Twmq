"""Piyasanın yeniden kalibrasyonu — ilk gerçek tahminci adayı.

Mevcut veriyle dürüst tek aday sınıfı budur. Veride piyasa dışı hiçbir sinyal
yok (bkz. `docs/VERI_TOPLAMA_VE_ISLEME.md` §8.7): sakatlık, kadro, motivasyon
taşınmıyor. Dolayısıyla yapılabilecek tek şey **piyasanın kendi olasılığını
düzeltmeye çalışmaktır** — piyasanın sistematik olarak yanıldığı bir yer varsa.

Şüphelenilecek iki yer zaten ölçülmüştü:

    lig farkı    Süper Lig beraberlik %29,8 · Premier Lig %19,7
    favori bandı 1,75–2,00 aralığında isabet %50'ye düşüyor

Tek model yerine **kademe** kuruldu, çünkü asıl soru "bu model iyi mi" değil,
*"kaçıncı basamakta yardım bitip aşırı uyum başlıyor"*:

    sicaklik   z_s = β·log p_s                       1 parametre
    bias       + sınıf sabiti                        3 parametre
    lig        + lige göre beraberlik sapması        3 + lig sayısı
    bant       + favori bandına göre sapma           + bant sayısı
    form       + takım formu (2 parametre)
    hareket    + açılış→kapanış çizgi hareketi       + 1 parametre
    dagilim    + bahisçi anlaşmazlığı (sıcaklık)     + 1 parametre
    dinlenme   + dinlenme günü farkı                 + 1 parametre
    sikisiklik + fikstür sıkışıklığı farkı           + 1 parametre
    ic_dis     + iç saha / dış saha ayrı form        + 1 parametre
    sezon_sonu + sezon sonu "oynayacak şey" payı     + 1 parametre

Hepsi softmax ile olasılığa döner. Kapasite bilerek küçük tutuldu: 540 maçlık
bir eğitim setinde serbest parametre sayısı arttıkça ölçüm değil ezber olur.

**Düzenlileştirme katsayısı (L2) baştan sabitlendi ve ayarlanmadı.** Onu ölçüm
sonucuna bakarak seçmek, sınavın cevabını görerek çalışmak olurdu — projenin
hold-out'la ayırmaya çalıştığı şeyin tam olarak kendisi.

Sonucu okumak için: `python -m spor_toto.recalibrate` ya da `rapor()`.
"""
from __future__ import annotations

import itertools
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

import numpy as np

from .history import MATCH_COUNT, SYMBOLS
from .odds import AZ_ORNEK, FAVORI_BANTLARI, load_odds, match_1x2
from .predict import Girdi, Olasilik, Tahminci

#: Olasılık logaritması alınırken sıfıra düşmeyi engelleyen taban.
OLASILIK_TABANI = 1e-6

#: L2 düzenlileştirme katsayısı. **Ayarlanmadı ve ayarlanmayacak** — ölçüm
#: sonucuna bakarak seçilirse hold-out'un anlamı kalmaz. Küçük bir değer,
#: az örnekli lig/bant katsayılarının uçmasını engellemek için.
L2 = 1e-3

#: Newton yinelemesinin sınırları. Rastgelelik yok: başlangıç sıfır, durma
#: ölçütü sabit — aynı eğitim seti her zaman aynı katsayıyı verir.
#:
#: Newton seçildi çünkü **gradyan inişi yakınsamıyordu**: 15 parametreli
#: `bant` modeli 20 000 adımda hâlâ sürükleniyordu ve eksik uydurulmuş bir
#: model, aşırı uyumla aynı görüntüyü verir (dışarıda skor kötü). İkisini
#: ayırmadan "kapasite zarar veriyor" demek yanlış olurdu.
EN_COK_YINELEME = 100

#: `np.einsum(optimize=...)` esigi — maç sayısı. Altında yol arama işin
#: kendisinden pahalı (n=75'te 0,054 ms → 0,125 ms), üstünde iki kat kazanç
#: (n=8.000'de 25,7 ms → 12,4 ms). Dönüm noktası n≈300 ölçüldü; eşik oraya
#: kondu. Sonucu DEĞİŞTİRMEZ: yalnızca toplama sırası oynar, Newton adımı
#: makine epsilonu kadar (3e-16) farklı çıkar ve durma eşiği 1e-10'dur.
_BUZULME_ESIGI = 300
DURMA_ESIGI = 1e-10

#: Kendi katsayısını hak etmek için bir ligin/bandın eğitim setinde taşıması
#: gereken en az maç. Altındakiler "diger" havuzunda toplanır.
EN_AZ_ORNEK = AZ_ORNEK

#: Kademe — basitten karmaşığa. Sıra kasıtlı: her basamak bir öncekine
#: yalnızca bir özellik ekler, böylece fark o özelliğe atfedilebilir.
KADEMELER: tuple[str, ...] = ("sicaklik", "bias", "lig", "bant", "form",
                              "hareket", "dagilim",
                              "dinlenme", "sikisiklik", "ic_dis", "sezon_sonu",
                              "etkilesim", "etkilesim_favori")

#: **Etkileşim basamakları** — `DIS_INCELEME.md` §3'ün açık itirazına cevap.
#:
#: Dokuz denemenin hepsi tek bir model ailesiyle yapılmıştı: `ln p` üzerinde
#: **doğrusal**, Newton ile uydurulan softmax. İtiraz haklı bir yere basıyor:
#: *"piyasayı geçen özellik yok demediniz — sizin doğrusal kademeniz o
#: özelliği kullanamadı demiş oldunuz."* Bu iki basamak o itirazı **bizim
#: kesitimizde** ölçerek cevaplıyor.
#:
#: İki ayrı basamak, çünkü iki ayrı soru:
#:
#:     etkilesim          yön özellikleri BİRBİRİYLE etkileşiyor mu
#:                        (ör. yorgunluk formu bastırıyor mu)
#:     etkilesim_favori   yön özellikleri MAÇIN AÇIKLIĞIYLA etkileşiyor mu
#:                        (ör. form denk maçlarda daha mı önemli)
#:
#: İkincisi teorik olarak daha güçlü bir aday: Ö3 beraberlik sapmasının
#: favori gücüne bağlı olduğunu **ölçmüştü** (şekil gerçek, büyüklük yok).
#: Aynı bağımlılık yön özelliklerinde de olabilir.
ETKILESIM_KADEMELERI: tuple[str, ...] = ("etkilesim", "etkilesim_favori")

#: Etkileşime giren yön özellikleri ve **tanımsal** ölçekleri.
#:
#: Ölçek şart: `dinlenme_farki` ±14, `sezon_sonu_pay_farki` ±1 aralığında.
#: Çarpımları ölçeklenmeden aynı L2 cezasına sokmak, büyük ölçekli
#: özelliklerin katsayısını yapay olarak kısar ve karşılaştırmayı bozardı.
#:
#: Ölçekler **veriye bakılmadan**, her özelliğin kendi TANIMINDAN alındı
#: (`L2` ve `EN_AZ_KOVA` ile aynı gerekçe — ölçüm sonucuna bakarak seçilirse
#: hold-out'un anlamı kalmaz):
#:
#:     form_puan_farki       maç başına puan farkı, tanım gereği [-3, 3]
#:     form_isabet_farki     isabetli şut farkı; doğal tavanı yok, 10 alındı
#:     dinlenme_farki        `egitim.DINLENME_TAVANI` = 14
#:     sikisiklik_farki      14 günde oynanan maç farkı; pratikte [-5, 5]
#:     ic_dis_form_farki     yine maç başına puan farkı, [-3, 3]
#:     sezon_sonu_pay_farki  `2·|yüzdelik - 0.5|` farkı, tanım gereği [-1, 1]
YON_ALANLARI: tuple[tuple[str, float], ...] = (
    ("form_puan_farki", 3.0),
    ("form_isabet_farki", 10.0),
    ("dinlenme_farki", 14.0),
    ("sikisiklik_farki", 5.0),
    ("ic_dis_form_farki", 3.0),
    ("sezon_sonu_pay_farki", 1.0),
)

#: Favori gücünün merkezlendiği nokta. Üç sembolde favorinin alabileceği en
#: küçük değer 1/3'tür; merkezleme oradan yapılır ki "favori yok" durumu
#: sıfır versin. Uydurulmuş bir eşik DEĞİL, sembol sayısının aritmetiği.
FAVORI_MERKEZ = 1.0 / 3.0

#: A3 basamaklarının okuduğu alanlar — hepsi **yön** özelliğidir ve hepsi
#: "pozitif = ev lehine" diye kurulmuştur (bkz. `egitim._takvim_tablosu`).
#: Sıra `KADEMELER`in son dördüyle birebir aynı olmalıdır; her basamak
#: listeye yalnızca bir sütun ekler.
A3_ALANLARI: tuple[tuple[str, str], ...] = (
    ("dinlenme", "dinlenme_farki"),
    ("sikisiklik", "sikisiklik_farki"),
    ("ic_dis", "ic_dis_form_farki"),
    ("sezon_sonu", "sezon_sonu_pay_farki"),
)


# ─── özellik kaynağı ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _ozellik_tablosu() -> dict[tuple[int, int], dict[str, Any]]:
    """(hafta, maç no) → lig etiketi ve favori oranı.

    `hafta_girdileri` yalnızca olasılık taşır; lig ve oran arşivde kalır.
    Buradan okunur, mevcut modüllerin sözleşmesi değiştirilmeden.
    """
    out: dict[tuple[int, int], dict[str, Any]] = {}
    for r in load_odds():
        blok = match_1x2(r)
        if not blok:
            continue
        favori = blok["favourite"]
        out[(r["week"], r["no"])] = {
            "lig": (r["source"].get("league") or "").strip() or "bilinmiyor",
            "favori": favori,
            "favori_oran": blok["odds"][favori],
        }
    return out


def _bant_adi(oran: float | None) -> str:
    """Favori oranının hangi banda düştüğü — `odds.FAVORI_BANTLARI` ile aynı."""
    if oran is None:
        return "bilinmiyor"
    for alt, ust in FAVORI_BANTLARI:
        if alt <= oran < ust:
            return f"{alt:.2f}-{ust:.2f}"
    return "bilinmiyor"


def _mac_ozellikleri(hafta: Girdi) -> list[dict[str, Any]]:
    """Bir haftanın maçları için özellik satırları — iki kaynak da desteklenir.

    Eğitim korpusu (`egitim.korpus_haftalari`) lig ve favori oranını haftanın
    içinde **taşır**; kupon haftaları taşımaz, oran arşivinden `(hafta, no)`
    ile aranır. Korpus olguyu taşır, bandı model türetir — bu ayrım sayesinde
    aynı tahminci iki kaynakta da değişmeden çalışır.
    """
    tasinan = hafta.get("ozellikler")
    probs_listesi = hafta.get("probs") or []

    if tasinan is not None:
        return [{
            "probs": probs_listesi[i] if i < len(probs_listesi) else None,
            "lig": o.get("lig", "bilinmiyor"),
            "favori": o.get("favori"),
            "bant": _bant_adi(o.get("favori_oran")),
            "form_puan_farki": float(o.get("form_puan_farki") or 0.0),
            "form_isabet_farki": float(o.get("form_isabet_farki") or 0.0),
            "hareket": {s: float(o.get(f"hareket_{s}") or 0.0) for s in SYMBOLS},
            "ayrisma": float(o.get("ayrisma") or 0.0),
            **{alan: float(o.get(alan) or 0.0) for _, alan in A3_ALANLARI},
        } for i, o in enumerate(tasinan)]

    tablo = _ozellik_tablosu()
    out: list[dict[str, Any]] = []
    for no in range(1, MATCH_COUNT + 1):
        ek = tablo.get((hafta["week"], no), {})
        probs = probs_listesi[no - 1] if no - 1 < len(probs_listesi) else None
        out.append({
            "probs": probs,
            "lig": ek.get("lig", "bilinmiyor"),
            "favori": ek.get("favori"),
            "bant": _bant_adi(ek.get("favori_oran")),
            # Kupon haftalari form da cizgi hareketi de tasimaz; notr 0 =
            # "bilgi yok". Sutun o macta hicbir sey yapmaz.
            "form_puan_farki": 0.0,
            "form_isabet_farki": 0.0,
            "hareket": dict.fromkeys(SYMBOLS, 0.0),
            "ayrisma": 0.0,
            **{alan: 0.0 for _, alan in A3_ALANLARI},
        })
    return out


# ─── tasarım matrisi ──────────────────────────────────────────────────────────

def _tasarim_satiri(ozellik: dict[str, Any], kademe: str,
                    ligler: Sequence[str], bantlar: Sequence[str]) -> np.ndarray:
    """Tek maçın (3 sembol × k özellik) tasarım bloğu.

    Sütunlar kademeye göre büyür; her sembol satırı o sembolün logitine
    hangi özelliklerin girdiğini söyler.
    """
    probs = ozellik["probs"] or {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
    sutunlar: list[list[float]] = []

    # 1) sıcaklık: log piyasa olasılığı
    sutunlar.append([np.log(max(probs.get(s, 0.0), OLASILIK_TABANI))
                     for s in SYMBOLS])
    if kademe == "sicaklik":
        return np.array(sutunlar, dtype=float).T

    # 2) sınıf sabiti — "1" referans alınır (tanımlanabilirlik için)
    for hedef in SYMBOLS[1:]:
        sutunlar.append([1.0 if s == hedef else 0.0 for s in SYMBOLS])
    if kademe == "bias":
        return np.array(sutunlar, dtype=float).T

    # 3) lige göre beraberlik sapması
    lig = ozellik["lig"] if ozellik["lig"] in ligler else "diger"
    for ad in ligler:
        sutunlar.append([1.0 if (s == "0" and lig == ad) else 0.0
                         for s in SYMBOLS])
    if kademe == "lig":
        return np.array(sutunlar, dtype=float).T

    # 4) favori bandına göre favori sembolün sapması
    bant = ozellik["bant"] if ozellik["bant"] in bantlar else "diger"
    favori = ozellik["favori"]
    for ad in bantlar:
        sutunlar.append([1.0 if (favori is not None and s == favori and bant == ad)
                         else 0.0 for s in SYMBOLS])
    if kademe == "bant":
        return np.array(sutunlar, dtype=float).T

    # 5) takim formu — simetrik kaydirma: ev lehine fark "1"i yukari,
    #    "2"yi asagi iter, beraberlige dokunmaz. Form bilinmiyorsa deger
    #    0'dir ve sutun hicbir sey yapmaz; "notr" ile "bilinmiyor" ayni
    #    davranisa duser, cunku ikisinde de soylenecek bir sey yoktur.
    for alan in ("form_puan_farki", "form_isabet_farki"):
        v = float(ozellik.get(alan) or 0.0)
        sutunlar.append([v if s == "1" else (-v if s == "2" else 0.0)
                         for s in SYMBOLS])
    if kademe == "form":
        return np.array(sutunlar, dtype=float).T

    # 6) cizgi hareketi — **tek paylasilan katsayi**, ve bu kasitli.
    #    Sutun her sembolun logitine o sembolun hareketini ekler; geriye tek
    #    bir β kalir ve ISARETI dogrudan soruyu cevaplar:
    #
    #        β > 0  momentum   — kapanis hareketi EKSIK fiyatlamis
    #        β ≈ 0  verimli    — hareketin soyledigi zaten kapanista
    #        β < 0  asiri tepki — kapanis hareketi FAZLA fiyatlamis
    #
    #    Sembol basina ayri katsayi verilseydi ucu de karisir ve isaret
    #    okunamazdi; kapasiteyi buyutmek burada cevabi bulaniklastirirdi.
    hareket = ozellik.get("hareket") or {}
    sutunlar.append([float(hareket.get(s) or 0.0) for s in SYMBOLS])
    if kademe == "hareket":
        return np.array(sutunlar, dtype=float).T

    # 7) bahisci anlasmazligi — bir SICAKLIK degiskeni, yon degiskeni degil.
    #    Anlasmazligin yonu yoktur; buyuklugu vardir. Hipotez: bahisciler
    #    ayrisinca kolektifin son sozu daha az guvenilirdir, yani model
    #    duzgun dagilima dogru cekilmelidir. Bu, logitte sicakligin
    #    MODULASYONUdur:
    #
    #        z_s = (β + δ·ayrisma)·ln p_s
    #
    #    Sutun `ayrisma · ln p_s`; geriye tek bir δ kalir ve isareti dogrudan
    #    soruyu cevaplar:
    #
    #        δ < 0  ayrisinca guven azalt — anlasmazlik BILGI tasiyor
    #        δ ≈ 0  anlasmazlik bir sey soylemiyor
    #        δ > 0  ayrisinca guven artir (beklenmez; cikarsa aciklama gerekir)
    #
    #    Yon sutunu (hangi bahisci hakli) BILEREK yok: o ayri bir soru ve
    #    `bahisci.py` onu tekil tahminci olarak, kafa kafaya olcuyor.
    ayrisma = float(ozellik.get("ayrisma") or 0.0)
    probs_log = [np.log(max(probs.get(s, 0.0), OLASILIK_TABANI)) for s in SYMBOLS]
    sutunlar.append([ayrisma * v for v in probs_log])
    if kademe == "dagilim":
        return np.array(sutunlar, dtype=float).T

    # 8-11) A3 — piyasa disi ama turetilebilir ozellikler. Dordu de `form` ile
    #       ayni bicimde girer: simetrik kaydirma, ev lehine fark "1"i yukari
    #       "2"yi asagi iter, beraberlige dokunmaz. Her basamak SIRAYLA bir
    #       sutun ekler, boylece fark o ozellige atfedilebilir.
    for ad, alan in A3_ALANLARI:
        v = float(ozellik.get(alan) or 0.0)
        sutunlar.append([v if s == "1" else (-v if s == "2" else 0.0)
                         for s in SYMBOLS])
        if kademe == ad:
            break
    if kademe not in ETKILESIM_KADEMELERI:
        return np.array(sutunlar, dtype=float).T

    # 12) etkilesim — yon ozelliklerinin IKILI carpimlari.
    #     Olcekli okunur (bkz. `YON_ALANLARI`), ve `form` ile ayni simetrik
    #     kaydirmayla girer: pozitif carpim "1"i yukari, "2"yi asagi iter.
    #     Beraberlige dokunmaz, cunku bir YON buyuklugudur — beraberlik
    #     sorusu ayridir ve `beraberlik.py`de kendi modeline sahiptir.
    olcekli = [float(ozellik.get(alan) or 0.0) / olcek
               for alan, olcek in YON_ALANLARI]
    for i in range(len(olcekli)):
        for j in range(i + 1, len(olcekli)):
            v = olcekli[i] * olcekli[j]
            sutunlar.append([v if s == "1" else (-v if s == "2" else 0.0)
                             for s in SYMBOLS])
    if kademe == "etkilesim":
        return np.array(sutunlar, dtype=float).T

    # 13) etkilesim_favori — her yon ozelligi x macin ACIKLIGI.
    #     Aciklik = favorinin olasiligi, 1/3'ten merkezlenmis. Denk macta
    #     ~0, ezici favoride ~0,6. Katsayinin ISARETI dogrudan soruyu
    #     cevaplar: pozitifse ozellik acik maclarda daha cok is goruyor,
    #     negatifse denk maclarda.
    aciklik = (max(probs.values()) - FAVORI_MERKEZ) if probs else 0.0
    for v0 in olcekli:
        v = v0 * aciklik
        sutunlar.append([v if s == "1" else (-v if s == "2" else 0.0)
                         for s in SYMBOLS])
    return np.array(sutunlar, dtype=float).T


def _tasarim(ozellikler: Sequence[dict[str, Any]], kademe: str,
             ligler: Sequence[str], bantlar: Sequence[str]) -> np.ndarray:
    """(n, 3, k) tasarım tensörü."""
    if not ozellikler:
        return np.zeros((0, len(SYMBOLS), 1))
    return np.stack([_tasarim_satiri(o, kademe, ligler, bantlar)
                     for o in ozellikler])


# ─── uydurma ──────────────────────────────────────────────────────────────────

def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def _uydur(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Çok sınıflı lojistik katsayıları — Newton yinelemesi.

    Amaç fonksiyonu L2 cezalı çok sınıflı çapraz entropidir; Hessian'ı
    kapalı biçimde yazılabilir:

        g = Σ_i X_iᵀ (q_i − y_i) / n + λθ
        H = Σ_i X_iᵀ (diag(q_i) − q_i q_iᵀ) X_i / n + λI

    H yarı-tanımlı pozitif, λI ile tam tanımlı olur; `solve` güvenlidir.
    Parametre sayısı en çok ~20 olduğu için k×k çözüm bedava sayılır ve
    yineleme karesel yakınsar — gradyan inişinin binlerce adımda
    ulaşamadığı yere onlarca adımda varır.

    scipy kullanılmadı: isteğe bağlı bir bağımlılık (`HAS_SCIPY`) ve kurulu
    olmadığı ortamda tahmincinin sessizce kaybolmasındansa kendi
    optimizasyonumuzu yazmak yeğdir.
    """
    n, _, k = X.shape
    theta = np.zeros(k)
    if n == 0:
        return theta

    # `optimize` numpy'a buzulmeyi ikili adimlara bolup BLAS'a devretmesini
    # soyler. Ucuz degil: her cagrida ~0,1 ms'lik bir yol arama yapiyor, o
    # yuzden kosula bagli. Korpus olculerinde (n≈24.000, k=41) yineleme
    # 74 ms'den 34 ms'ye iniyor; kucuk uydurmalarda ise yol arama isin
    # kendisinden pahali ve saf dongu daha hizli. Esik olculdu (bkz. asagi).
    optimize = n >= _BUZULME_ESIGI

    goz = np.eye(k)
    for _ in range(EN_COK_YINELEME):
        q = _softmax(X @ theta)
        grad = np.einsum("isk,is->k", X, q - y, optimize=optimize) / n + L2 * theta
        # H_i = X_iᵀ (diag(q_i) − q_i q_iᵀ) X_i
        agirlikli = (np.einsum("is,isk->isk", q, X, optimize=optimize)
                     - np.einsum("is,it,itk->isk", q, q, X, optimize=optimize))
        hess = (np.einsum("isk,isj->kj", X, agirlikli, optimize=optimize) / n
                + L2 * goz)
        try:
            adim = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:  # pragma: no cover - L2 bunu engeller
            adim = np.linalg.lstsq(hess, grad, rcond=None)[0]
        theta = theta - adim
        if float(np.abs(adim).max()) < DURMA_ESIGI:
            break
    return theta


# ─── tahminci ─────────────────────────────────────────────────────────────────

class KalibreTahminci(Tahminci):
    """Piyasa olasılığını lojistik olarak yeniden kalibre eden aday.

    `kademe` hangi özelliklerin girdiğini belirler (bkz. `KADEMELER`).
    Eğitilmeden çağrılırsa piyasayı olduğu gibi geçirir — uydurma bir
    düzeltme üretmez.
    """

    def __init__(self, kademe: str = "bias") -> None:
        if kademe not in KADEMELER:
            raise ValueError(f"bilinmeyen kademe: {kademe}")
        self.kademe = kademe
        self.ad = f"kalibre_{kademe}"
        self.aciklama = f"Piyasanın lojistik yeniden kalibrasyonu ({kademe})"
        self._theta: np.ndarray | None = None
        self._ligler: list[str] = []
        self._bantlar: list[str] = []

    # -- eğitim --------------------------------------------------------------

    def _gruplari_belirle(self, ozellikler: Sequence[dict[str, Any]]) -> None:
        """Kendi katsayısını hak eden lig ve bantlar — **eğitim setinden**.

        Grup kümesi de veriden gelen bir seçimdir; ölçülen haftayı görerek
        belirlenirse sızıntı olur. Bu yüzden her katta yeniden hesaplanır.
        """
        def yeterli(alan: str) -> list[str]:
            sayim: dict[str, int] = {}
            for o in ozellikler:
                sayim[o[alan]] = sayim.get(o[alan], 0) + 1
            return [*sorted([k for k, v in sayim.items() if v >= EN_AZ_ORNEK and k != "bilinmiyor"]), "diger"]

        # Lig ve bant sutunlari, kendi basamaklarindan ITIBAREN butun ust
        # kademelerde bulunur. Bu daha once elle yazilmis bir liste olarak
        # duruyordu ve `KADEMELER`e yeni bir basamak eklendiginde SESSIZCE
        # bozuluyordu: yeni basamak listede olmadigi icin lig/bant sutunlari
        # tamamen dusuyor, kademe bias seviyesine geriliyordu. Tam da bu
        # yasandi (etkilesim basamaklari eklenirken) ve
        # `test_gercek_veride_egitim_ici_kapasiteyle_iyilesiyor` yakaladi.
        # Sira artik `KADEMELER`in kendisinden okunuyor — tek kaynak.
        sira = KADEMELER.index(self.kademe) if self.kademe in KADEMELER else -1
        self._ligler = yeterli("lig") if sira >= KADEMELER.index("lig") else []
        self._bantlar = yeterli("bant") if sira >= KADEMELER.index("bant") else []

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        ozellikler: list[dict[str, Any]] = []
        kodlar: list[str] = []
        for hafta in haftalar:
            satirlar = _mac_ozellikleri(hafta)
            for k, kod in enumerate(hafta["results"]):
                if k < len(satirlar) and satirlar[k]["probs"]:
                    ozellikler.append(satirlar[k])
                    kodlar.append(kod)
        if not ozellikler:
            self._theta = None
            return

        self._gruplari_belirle(ozellikler)
        X = _tasarim(ozellikler, self.kademe, self._ligler, self._bantlar)
        y = np.zeros((len(kodlar), len(SYMBOLS)))
        for i, kod in enumerate(kodlar):
            if kod in SYMBOLS:
                y[i, SYMBOLS.index(kod)] = 1.0
        self._theta = _uydur(X, y)

    # -- tahmin --------------------------------------------------------------

    def tahmin(self, hafta: Girdi) -> list[Olasilik]:
        satirlar = _mac_ozellikleri(hafta)
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        out: list[Olasilik] = []
        for satir in satirlar:
            piyasa = satir["probs"]
            if self._theta is None or piyasa is None:
                out.append(dict(piyasa) if piyasa else dict(esit))
                continue
            X = _tasarim_satiri(satir, self.kademe, self._ligler, self._bantlar)
            q = _softmax(X @ self._theta)
            out.append({s: float(q[i]) for i, s in enumerate(SYMBOLS)})
        return out

    @property
    def katsayilar(self) -> list[float] | None:
        """Uydurulmuş katsayılar — tanılama ve test için."""
        return None if self._theta is None else [float(v) for v in self._theta]


#: İzotonik kalibrasyonun bir kovaya koyduğu en az nokta. Ham PAV, 93 bin
#: noktada tek maçlık bloklar üretebilir ve o blok gürültünün kendisidir;
#: önce eşit sayıda noktalı kovalara bölünüp kova ortalamaları üzerinde
#: çalışılır. 1000 nokta ≈ 93 kova — eğri okumaya yetecek kadar ince,
#: sezon dışarıda bırakmalı ölçümde ezberlemeyecek kadar kalın.
#:
#: **Ölçüm sonucuna bakılarak seçilmedi** (L2 ile aynı gerekçe, bkz. `L2`).
EN_AZ_KOVA = 1000


def _pav(x: Sequence[float], y: Sequence[float],
         w: Sequence[float]) -> list[float]:
    """Ağırlıklı PAV (pool-adjacent-violators) — monoton artan en iyi uyum.

    Komşu iki blok sırayı bozuyorsa birleştirilir ve ağırlıklı ortalamaları
    alınır; işlem yukarı doğru yayılır. Sonuç, ağırlıklı kareler toplamını
    monotonluk kısıtı altında **kesin** olarak enküçülten dizidir — yaklaşık
    bir çözüm değil.
    """
    # Her blok: [toplam agirlikli y, toplam agirlik, kac kovayi yuttu].
    # Kova adedi agirliktan geri hesaplanmaz, acikca tasinir — agirliklar
    # kesirli oldugunda geri hesap kayardi.
    bloklar: list[list[float]] = []
    for yi, wi in zip(y, w):
        bloklar.append([yi * wi, wi, 1])
        while len(bloklar) > 1:
            onceki, son = bloklar[-2], bloklar[-1]
            if onceki[0] / onceki[1] <= son[0] / son[1]:
                break
            bloklar[-2] = [onceki[0] + son[0], onceki[1] + son[1],
                           onceki[2] + son[2]]
            bloklar.pop()
    out: list[float] = []
    for toplam, agirlik, adet in bloklar:
        out.extend([toplam / agirlik] * int(adet))
    return out


class IzotonikTahminci(Tahminci):
    """Piyasa olasılığını **monoton** bir eğriyle düzelten aday (A5).

    `KalibreTahminci`den farkı model sınıfı: orada düzeltme parametrik bir
    softmax (sıcaklık + sabitler), burada parametresiz monoton bir eşleme.
    Sebep ölçülmüş: sapma düzenli ama **düz değil** — sürprizler abartılıyor,
    favoriler küçümseniyor ve iki uçta eğim farklı. Sıcaklık ölçeklemesi tek
    bir eğim taşıyabildiği için bu şekli tam yakalayamaz.

    Üç sembol **havuzlanır**: eğri "piyasa p dediğinde gerçekte ne oluyor"
    sorusuna sembolden bağımsız cevap verir. Ayrı ayrı eğri uydurmak üç kat
    parametre demek olurdu ve ölçülen sapma zaten sembole göre ayrışmıyor.

    Eşlemeden sonra olasılıklar 1'e **yeniden normalize edilir**; monoton
    düzeltme toplamı korumaz.

    Eğitilmeden çağrılırsa piyasayı olduğu gibi geçirir.
    """

    ad = "izotonik"
    aciklama = "Piyasanın monoton (izotonik) yeniden kalibrasyonu"

    def __init__(self, en_az_kova: int = EN_AZ_KOVA) -> None:
        self.en_az_kova = en_az_kova
        self._x: list[float] = []
        self._y: list[float] = []

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        noktalar: list[tuple[float, float]] = []
        for hafta in haftalar:
            kodlar = hafta.get("results") or ""
            for k, blok in enumerate(hafta["probs"]):
                if not blok or k >= len(kodlar):
                    continue
                for s in SYMBOLS:
                    noktalar.append((blok[s], 1.0 if kodlar[k] == s else 0.0))
        if len(noktalar) < 2 * self.en_az_kova:
            # Eğri kurulamayacak kadar az veri: düzeltme yapmamak, kötü bir
            # düzeltme yapmaktan iyidir.
            self._x, self._y = [], []
            return

        noktalar.sort(key=lambda t: t[0])
        # Kova sayısı önce belirlenir, sonra noktalar eşit paylaştırılır.
        # `range(0, n, en_az_kova)` yazılsaydı sondaki artık kova tek başına
        # kalır ve en az veriye sahip uçta en oynak değeri üretirdi.
        kova_sayisi = max(1, len(noktalar) // self.en_az_kova)
        sinirlar = [round(i * len(noktalar) / kova_sayisi)
                    for i in range(kova_sayisi + 1)]
        x: list[float] = []
        y: list[float] = []
        w: list[float] = []
        for bas, son in itertools.pairwise(sinirlar):
            kova = noktalar[bas:son]
            if not kova:
                continue
            n = len(kova)
            x.append(sum(t[0] for t in kova) / n)
            y.append(sum(t[1] for t in kova) / n)
            w.append(float(n))
        self._x, self._y = x, _pav(x, y, w)

    def _duzelt(self, p: float) -> float:
        """Eğriyi kova merkezleri arasında doğrusal ara-değerleyerek uygula.

        Veri aralığının dışında eğri **düzleşir** (uçtaki kova değeri).
        Uçları eğimle uzatmak, en az veriye sahip bölgede en cesur tahmini
        yapmak olurdu.
        """
        if not self._x:
            return p
        if p <= self._x[0]:
            return self._y[0]
        if p >= self._x[-1]:
            return self._y[-1]
        # Kova sayısı ~93; doğrusal tarama okunaklı ve yeterince hızlı.
        for i in range(1, len(self._x)):
            if p <= self._x[i]:
                x0, x1 = self._x[i - 1], self._x[i]
                y0, y1 = self._y[i - 1], self._y[i]
                if x1 <= x0:
                    return y1
                return y0 + (y1 - y0) * (p - x0) / (x1 - x0)
        return self._y[-1]

    def tahmin(self, hafta: Girdi) -> list[Olasilik]:
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        out: list[Olasilik] = []
        for blok in hafta["probs"]:
            if not blok or not self._x:
                out.append(dict(blok) if blok else dict(esit))
                continue
            ham = {s: max(OLASILIK_TABANI, self._duzelt(blok[s]))
                   for s in SYMBOLS}
            toplam = sum(ham.values())
            out.append({s: ham[s] / toplam for s in SYMBOLS} if toplam > 0
                       else dict(esit))
        return out

    @property
    def egri(self) -> list[tuple[float, float]]:
        """Uydurulmuş eğri — tanılama ve test için (piyasa p, düzeltilmiş p)."""
        return list(zip(self._x, self._y))


def kademe_fabrikalari() -> list[Any]:
    """Kademenin her basamağı için bir fabrika."""
    return [(lambda k=k: KalibreTahminci(k)) for k in KADEMELER]


# ─── rapor ────────────────────────────────────────────────────────────────────

def rapor(last: int | None = None) -> dict[str, Any]:
    """Kademeyi piyasaya karşı koştur ve sonucu döndür.

    Bu fonksiyon bir öneri üretmez; yalnızca `evaluate.karsilastir`'ın
    verdiği tabloyu taşır. Hangi basamağın "geçtiği" kararı orada, güven
    aralığı kuralıyla verilir.
    """
    from .evaluate import karsilastir
    from .predict import PiyasaTahminci

    fabrikalar = [PiyasaTahminci, *kademe_fabrikalari()]
    return karsilastir(fabrikalar, last=last)


def _yazdir(sonuc: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print(f"kesit: {sonuc['n_hafta']} hafta · {sonuc['n_mac']} maç "
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


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    _yazdir(rapor())
