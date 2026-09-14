"""Kupon arşivi — **bir kupon, bir kayıt**.

Arşivin birimi hafta değil **kupon**. Bir haftanın birden çok kuponu olur:
biri açılış oranlarıyla, öteki kapanışla; biri shin, öteki orantılı
arındırmayla. Bunlar birbirinin sürümü değil, ayrı denemelerdir ve yan yana
durmaları gerekir.

Bir kayıt dört şeyi birden taşır — çünkü kupon bu dördünün **zinciridir**:

    girdi   15 maç, elle yazılmış ad ve 1/0/2 oranı
    ayar    hangi çizgi, hangi arındırma, hangi örneklem, hangi kesme
    analiz  o ayarla çıkan karne — ÖLÇÜLDÜĞÜ ANIN damgasıyla
    kupon   o analizden çıkan işaretler

Zincirin bir halkası eksikse kayıt "neden bu işaretler" sorusunu
cevaplayamaz.

─── Neden diskte, neden tarayıcıda değil ────────────────────────────────

Gerekçe `.claude/olcum_kutugu.json`unkiyle **birebir aynı**: elle girilen
bir kayıt depodan yeniden üretilemez. Türetilmiş olan (envanter, kolonlar)
her zaman yeniden üretilebilir ve sürümlenmez; bir koşum ya da giriş kaydı
üretilemez ve sürümlenir. Tarayıcıda tutulan bir arşiv bu ayrımın dışında
kalırdı: başka makinede yoktur, tarayıcı verisi silinince gider ve
`git log` onu hiç görmez.

─── Analiz neden KAYDEDİLİYOR (önceki karar geri alındı) ────────────────

İlk sürümde karne bilerek yazılmıyordu: *"türetilmiş veridir ve korpus
büyüdükçe bayatlar."* Teşhis doğruydu, çare yanlıştı. Kupon **o analizden**
çıkıyor; analiz atılırsa kayıt, kendi kararının gerekçesini kaybeder ve
"neden bu işaretler" sorusu bir daha cevaplanamaz. Bayatlamanın çaresi
kaydı ATMAK değil **damgalamaktır** — ölçüm kütüğünün baştan beri yaptığı
şey: sayının yanında ne zaman ve neyin üstünde ölçüldüğü durur
(`analiz.olculdu`, `analiz.evren`). Arayüz o damgayı gösterir ve aynı
sorguyu bugünün korpusunda yeniden koşturmayı önerir; kayıt ise o günün
kaydı olarak kalır.

Yine de şu iki şey arşive GİRMEZ: lig kırılımı ve karnenin arkasındaki maç
listesi. İkisi de `/oran-analizi`de tek tıkla açılır ve kaydı on katına
çıkarırdı.

─── Neden `hafta_NN.json`un ÜSTÜNE yazmıyor ─────────────────────────────

`data/super_toto/<sezon>/hafta_NN.json` özenle kurulmuş bir künye taşıyor:
`odds_source`, `entered_at` ve dokuz maddelik `data_warnings` ("kapanış
etiketi fazla olabilir", "takım adı eşlemesi doğrulanmadı"). Arayüzden
gelen bir kayıt onun üstüne yazsaydı o kanıt zinciri **sessizce** silinirdi.
Bu yüzden bu aile ayrı, onun yanında durur.

    python -m spor_toto.kupon_arsivi --liste
    python -m spor_toto.kupon_arsivi --no 1
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import SEMBOLLER

KOK = Path(__file__).resolve().parent.parent
ARSIV = KOK / "data" / "kupon_arsivi"

#: Kayıt biçiminin sürümü. Alan eklenirse artmaz; **anlam** değişirse artar.
#:
#: 1 -> 2: birim HAFTA idi, KUPON oldu (`hafta_NN.json` -> `kupon_NNN.json`)
#: ve kayıt artık analiz ile kuponun kendisini de taşıyor. Göç kodu YOK ve
#: bu bilinçli: 1. sürümde hiç kayıt üretilmemişti (özellik aynı gün yazıldı),
#: yani göç edecek veri yok. Olmayan veri için göç yazmak, sınanamayan kod
#: yazmaktır.
SURUM = 2

#: Bir haftada kaç maç. `core.SEMBOLLER` gibi bu da tek kaynaktan gelmeli;
#: `meta.MATCH_COUNT` ile aynı sayıdır ve testi bunu tutar.
MAC_SAYISI = 15

#: Sezon anahtarının biçimi — `2026_27`. Katı, çünkü bu değer DOSYA YOLUNA
#: giriyor: serbest bir dize `../../` taşıyabilirdi.
SEZON_DESENI = re.compile(r"^\d{4}_\d{2}$")

VARSAYILAN_SEZON = "2026_27"

#: Hafta numarasının sınırı. Spor Toto sezonu ~40 hafta; üst sınır cömert
#: tutuldu ama sınırsız değil. Hafta ARTIK KİMLİK DEĞİL, yalnızca bir
#: etikettir (bir haftanın birden çok kuponu olur) ve boş bırakılabilir.
HAFTA_MIN, HAFTA_MAX = 1, 60

#: Kupon numarasının sınırı. Numara dosya adına girer, o yüzden sınırlı.
NO_MIN, NO_MAX = 1, 9999

#: Kupon adının en fazla uzunluğu. Ad SERBESTTİR ("1 numaralı kupon",
#: "açılışla kurulan") ve kimlik DEĞİLDİR: kimlik `no`dur, iki kupon aynı
#: adı taşıyabilir.
AD_SINIR = 80

#: Metin alanlarının en fazla uzunluğu (arayüzdeki `METIN_SINIR` ile aynı).
METIN_SINIR = 40
NOT_SINIR = 400


class ArsivHatasi(ValueError):
    """Girdi kabul edilemez. Çağıran bunu 400'e çevirir."""


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sezon_dogrula(ham: Any) -> str:
    """Sezon anahtarı — **varsayılana DÜŞMEZ**.

    Önceden boş bir değer sessizce `VARSAYILAN_SEZON`a düşüyordu ve bunu
    bekçi yakaladı: `yol("", 5)` reddedilmesi gereken bir çağrıyken geçerli
    bir yol üretiyordu. Varsayılan, bu fonksiyonun değil **çağıranın**
    kararıdır (uç `?sezon=` yokken varsayılanı kendisi koyar); burada
    uygulanırsa "sezon verilmedi" ile "sezon yanlış" ayrımı kaybolur.
    """
    sezon = str(ham).strip() if ham is not None else ""
    if not SEZON_DESENI.match(sezon):
        raise ArsivHatasi(f"sezon bicimi 'YYYY_YY' olmali: {sezon!r}")
    return sezon


def hafta_dogrula(ham: Any) -> int | None:
    """Hafta ETİKETİ — boş bırakılabilir.

    Artık kimlik değil: bir haftanın birden çok kuponu olur ve bir kupon
    henüz bir haftaya bağlanmamış olabilir. Ama VERİLDİYSE okunabilir
    olmalı; sessizce `None`a düşen bir hafta, listede yanlış gruplanır.
    """
    if ham is None or (isinstance(ham, str) and not ham.strip()):
        return None
    try:
        hafta = int(ham)
    except (TypeError, ValueError):
        raise ArsivHatasi(f"hafta bir tamsayi olmali: {ham!r}") from None
    if not HAFTA_MIN <= hafta <= HAFTA_MAX:
        raise ArsivHatasi(f"hafta {HAFTA_MIN}-{HAFTA_MAX} arasinda olmali: {hafta}")
    return hafta


def no_dogrula(ham: Any) -> int:
    """Kupon numarası — kaydın KİMLİĞİ. Ad değil bu; ad serbesttir."""
    try:
        no = int(ham)
    except (TypeError, ValueError):
        raise ArsivHatasi(f"kupon no bir tamsayi olmali: {ham!r}") from None
    if not NO_MIN <= no <= NO_MAX:
        raise ArsivHatasi(f"kupon no {NO_MIN}-{NO_MAX} arasinda olmali: {no}")
    return no


def yol(sezon: str, no: int) -> Path:
    """Kaydın dosya yolu.

    İki doğrulamadan da geçmiş değerlerle çağrılır; yine de sonuç arşiv
    kökünün altında mı diye bakılır. Bu **savunma derinliği**: bir gün
    doğrulayıcılardan biri gevşerse yol kaçağı burada durur, sessizce
    depodaki başka bir dosyanın üstüne yazılmaz.
    """
    p = (ARSIV / sezon_dogrula(sezon) / f"kupon_{no_dogrula(no):03d}.json").resolve()
    if not str(p).startswith(str(ARSIV.resolve()) + os.sep):
        raise ArsivHatasi("yol arsiv kokunun disina cikiyor")
    return p


def _metin(ham: Any, sinir: int = METIN_SINIR) -> str:
    if not isinstance(ham, str):
        return ""
    return " ".join(ham.split())[:sinir]


def _oran(ham: Any) -> float | None:
    """Tek oran hücresi. Boş ve okunamayan `None`; 1,00 ve altı REDDEDİLİR.

    Boşa izin veriliyor çünkü kullanıcı tabloyu **doldururken** de kaydeder;
    yarım bir kayıt bir hata değildir. Ama okunabilen ama geçersiz bir
    değer (0, -3, 1.0) sessizce boşa çevrilmez: o, kullanıcının yazdığı bir
    şeyin kaybolması demek olurdu.
    """
    if ham is None or (isinstance(ham, str) and not ham.strip()):
        return None
    try:
        v = float(ham)
    except (TypeError, ValueError):
        raise ArsivHatasi(f"oran okunamadi: {ham!r}") from None
    if not (v > 1.0) or v != v or v in (float("inf"), float("-inf")):
        raise ArsivHatasi(f"oran 1.00'den buyuk olmali: {ham!r}")
    return v


def satirlari_dogrula(ham: Any) -> list[dict[str, Any]]:
    """15 satır, her satırda lig/ev/dep ve 1/0/2.

    Eksik satır **tamamlanır**, fazlası kırpılmaz: uzunluk tam 15 değilse
    reddedilir. Sebep, sessiz kaymanın bedeli — 14 satırlık bir kayıt geri
    okunurken 15. maç boş gelir ve kullanıcı bunu fark etmeyebilir.
    """
    if not isinstance(ham, list):
        raise ArsivHatasi("satirlar bir liste olmali")
    if len(ham) != MAC_SAYISI:
        raise ArsivHatasi(f"satirlar tam {MAC_SAYISI} olmali, {len(ham)} geldi")

    cikti: list[dict[str, Any]] = []
    for i, aday in enumerate(ham, start=1):
        if not isinstance(aday, dict):
            raise ArsivHatasi(f"{i}. satir bir nesne olmali")
        oran_ham = aday.get("oran") or {}
        if not isinstance(oran_ham, dict):
            raise ArsivHatasi(f"{i}. satirin orani bir nesne olmali")
        try:
            oran = {s: _oran(oran_ham.get(s)) for s in SEMBOLLER}
        except ArsivHatasi as e:
            raise ArsivHatasi(f"{i}. satir: {e}") from None
        cikti.append({
            "lig": _metin(aday.get("lig")),
            "ev": _metin(aday.get("ev")),
            "dep": _metin(aday.get("dep")),
            "oran": oran,
        })
    return cikti


def ayari_dogrula(ham: Any) -> dict[str, Any]:
    """Analiz ayarı — kaydın **yeniden üretilebilir** olmasının şartı.

    Ayarsız bir arşiv, "o hafta neye bakmıştık" sorusunu cevaplayamaz:
    aynı oranlar açılış evreninde ve kapanış evreninde farklı karne verir.
    Burada sunucunun kendi listeleri kullanılır (`odds.ARINDIRMA_YONTEMLERI`,
    `benzer.CIZGILER`), arayüzün gönderdiği dize değil.
    """
    from .benzer import CIZGILER
    from .odds import ARINDIRMA_YONTEMLERI

    ham = ham if isinstance(ham, dict) else {}
    cizgi = str(ham.get("cizgi") or "kapanis").strip()
    if cizgi not in CIZGILER:
        raise ArsivHatasi(f"cizgi: {', '.join(CIZGILER)}")
    arindirma = str(ham.get("arindirma") or "shin").strip()
    if arindirma not in ARINDIRMA_YONTEMLERI:
        raise ArsivHatasi(f"arindirma: {', '.join(ARINDIRMA_YONTEMLERI)}")
    try:
        en_az = int(ham.get("en_az", 200))
    except (TypeError, ValueError):
        raise ArsivHatasi("en_az bir tamsayi olmali") from None
    if not 1 <= en_az <= 5000:
        raise ArsivHatasi("en_az 1-5000 arasinda olmali")
    tarih = _metin(ham.get("tarih"), 10)
    if tarih:
        try:
            datetime.strptime(tarih, "%Y-%m-%d")
        except ValueError:
            raise ArsivHatasi("tarih YYYY-AA-GG olmali") from None
    return {"cizgi": cizgi, "arindirma": arindirma, "en_az": en_az, "tarih": tarih}


def _kesir(ham: Any, ad: str) -> float:
    """0-1 arasi bir olasilik/oran. Sinir disi deger REDDEDILIR."""
    try:
        v = float(ham)
    except (TypeError, ValueError):
        raise ArsivHatasi(f"{ad} bir sayi olmali: {ham!r}") from None
    if not (0.0 <= v <= 1.0) or v != v:
        raise ArsivHatasi(f"{ad} 0-1 arasinda olmali: {ham!r}")
    return v


def _sembol_okumasi(ham: Any, ad: str) -> dict[str, Any]:
    """Bir sembolün karne hücresi — `benzer`in ürettiği alanların ALT KÜMESİ.

    Tamamı değil: `fark` gibi türetilebilen alanlar yazılmaz (iki sayıdan
    çıkar), lig kırılımı ve maç listesi ise hiç girmez (bkz. modül künyesi).
    Yazılanlar, arayüzün tabloyu **aynen** çizebilmesi için gerekli olan
    en küçük kümedir.
    """
    if not isinstance(ham, dict):
        raise ArsivHatasi(f"{ad} bir nesne olmali")
    adet = ham.get("adet")
    try:
        adet = int(adet)
    except (TypeError, ValueError):
        raise ArsivHatasi(f"{ad}.adet bir tamsayi olmali: {adet!r}") from None
    if adet < 0:
        raise ArsivHatasi(f"{ad}.adet negatif olamaz")
    oran = ham.get("oran")
    ga_icinde = ham.get("piyasa_ga_icinde")
    if ga_icinde is not None and not isinstance(ga_icinde, bool):
        raise ArsivHatasi(f"{ad}.piyasa_ga_icinde ya null ya boolean olmali")
    return {
        "adet": adet,
        # Ornek yoksa ampirik oran YOKTUR; 0 yazmak "hic olmadi" demek olurdu.
        "oran": None if oran is None else _kesir(oran, f"{ad}.oran"),
        "ga_alt": _kesir(ham.get("ga_alt", 0.0), f"{ad}.ga_alt"),
        "ga_ust": _kesir(ham.get("ga_ust", 0.0), f"{ad}.ga_ust"),
        "piyasa": _kesir(ham.get("piyasa", 0.0), f"{ad}.piyasa"),
        "piyasa_ga_icinde": ga_icinde,
    }


def analizi_dogrula(ham: Any) -> dict[str, Any] | None:
    """Kaydın **analiz halkası** — koşulmamışsa `None`.

    Damga (`olculdu`, `evren`) alan değil ZORUNLULUKTUR: bu blok türetilmiş
    bir sayıdır ve korpus büyüdükçe bayatlar. Damgasız yazılırsa iki ay
    sonra açan kişi onu bugünün cevabı sanır — modül künyesindeki kararın
    tamamı bu iki alana dayanıyor.
    """
    if ham is None:
        return None
    if not isinstance(ham, dict):
        raise ArsivHatasi("analiz ya null ya bir nesne olmali")
    satirlar = ham.get("satirlar")
    if not isinstance(satirlar, list) or len(satirlar) != MAC_SAYISI:
        raise ArsivHatasi(f"analiz.satirlar tam {MAC_SAYISI} olmali")

    try:
        evren = int(ham.get("evren", 0))
    except (TypeError, ValueError):
        raise ArsivHatasi("analiz.evren bir tamsayi olmali") from None
    if evren <= 0:
        raise ArsivHatasi("analiz.evren pozitif olmali — damgasiz analiz yazilmaz")

    cikti: list[dict[str, Any] | None] = []
    for i, satir in enumerate(satirlar, start=1):
        # Bir satirin sorgusu HATA almis olabilir; o satir `null` durur ve
        # bu bir kayip degil, kaydin kendisidir.
        if satir is None:
            cikti.append(None)
            continue
        if not isinstance(satir, dict):
            raise ArsivHatasi(f"analiz.satirlar[{i}] ya null ya nesne olmali")
        semboller_ham = satir.get("semboller")
        if not isinstance(semboller_ham, dict):
            raise ArsivHatasi(f"analiz.satirlar[{i}].semboller bir nesne olmali")
        try:
            n = int(satir.get("n", 0))
        except (TypeError, ValueError):
            raise ArsivHatasi(f"analiz.satirlar[{i}].n bir tamsayi olmali") from None
        cikti.append({
            "n": n,
            "yeterli": bool(satir.get("yeterli")),
            "tolerans": _kesir(satir.get("tolerans", 0.0), f"analiz.satirlar[{i}].tolerans"),
            "tolerans_genisledi": bool(satir.get("tolerans_genisledi")),
            "tolerans_tavana_dayandi": bool(satir.get("tolerans_tavana_dayandi")),
            "semboller": {
                sem: _sembol_okumasi(semboller_ham.get(sem),
                                     f"analiz.satirlar[{i}].semboller.{sem}")
                for sem in SEMBOLLER
            },
        })

    return {
        "olculdu": _metin(ham.get("olculdu"), 40) or _simdi(),
        "evren": evren,
        "satirlar": cikti,
    }


def kuponu_dogrula(ham: Any) -> dict[str, Any] | None:
    """Kaydın **kupon halkası** — 15 maçın işaretleri. Kurulmamışsa `None`.

    Bir maçın işareti boş OLAMAZ: boş maç motorda `ValueError` üretir
    (`core.Encoder`) ve arayüz de en az bir seçimi garanti eder. Sıra
    `SEMBOLLER` sırasıdır (1, 0, 2) — alfabetik değil, kupon düzeni.

    `kolon` yazılmaz, HESAPLANIR: işaretlerin çarpımı. Yazılsaydı kaydın
    içinde birbirini yalanlayabilecek iki sayı olurdu.
    """
    if ham is None:
        return None
    if not isinstance(ham, dict):
        raise ArsivHatasi("kupon ya null ya bir nesne olmali")
    isaretler = ham.get("isaretler")
    if not isinstance(isaretler, list) or len(isaretler) != MAC_SAYISI:
        raise ArsivHatasi(f"kupon.isaretler tam {MAC_SAYISI} olmali")

    temiz: list[list[str]] = []
    kolon = 1
    for i, sec in enumerate(isaretler, start=1):
        if not isinstance(sec, list) or not sec:
            raise ArsivHatasi(f"{i}. macin isareti bos olamaz")
        bilinmeyen = [x for x in sec if x not in SEMBOLLER]
        if bilinmeyen:
            raise ArsivHatasi(f"{i}. macta bilinmeyen sembol: {bilinmeyen!r}")
        # Yinelenen sembol sessizce TEKILLESIR ama sira KUPON duzenine oturur.
        satir = [sem for sem in SEMBOLLER if sem in sec]
        temiz.append(satir)
        kolon *= len(satir)

    return {
        "isaretler": temiz,
        "kolon": kolon,
        "not": _metin(ham.get("not"), NOT_SINIR),
    }


def sonuclari_dogrula(ham: Any) -> list[str | None] | None:
    """Hafta oynandıktan sonra girilen 1/0/2. Girilmemişse `None`.

    Kayıt bunu **taşımak zorunda değil** ama alanı baştan var: sonradan
    eklenen bir alan, eski kayıtları "eksik" gösterir ve okuyanın her
    seferinde iki biçimi ayırt etmesini gerektirir.
    """
    if ham is None:
        return None
    if not isinstance(ham, list) or len(ham) != MAC_SAYISI:
        raise ArsivHatasi(f"sonuclar ya null ya da {MAC_SAYISI} elemanli olmali")
    cikti: list[str | None] = []
    for i, s in enumerate(ham, start=1):
        if s is None or (isinstance(s, str) and not s.strip()):
            cikti.append(None)
            continue
        # `1` (sayi) ile `"1"` (sembol) ayni sey DEGILDIR ve bekci bunu
        # yakaladi: `str(1)` "1" verdigi icin sayi sessizce kabul
        # ediliyordu. Bir KAYIT tipinde gevsek olmamali.
        if not isinstance(s, str):
            raise ArsivHatasi(f"{i}. sonuc metin olmali: {s!r}")
        deger = s.strip()
        if deger not in SEMBOLLER:
            raise ArsivHatasi(f"{i}. sonuc {'/'.join(SEMBOLLER)} olmali: {deger!r}")
        cikti.append(deger)
    return cikti


def sonraki_no(sezon: str) -> int:
    """Sezonun bir sonraki kupon numarası.

    **Numara yeniden KULLANILMAZ.** 1 ve 2 varken 2 silinirse sıradaki
    numara 3'tür, 2 değil: "2 numaralı kupon" dediğin şeyin iki farklı
    kayda işaret etmesi, arşivi bir kayıt olmaktan çıkarır.

    Bu yüzden sayım değil, EN BÜYÜK + 1 okunur — ve dosya adından, çünkü
    dosyanın içi bozulmuş olsa bile adı numarayı taşır.
    """
    dizin = ARSIV / sezon_dogrula(sezon)
    if not dizin.is_dir():
        return NO_MIN
    enbuyuk = 0
    for p in dizin.glob("kupon_*.json"):
        m = re.match(r"kupon_(\d+)\.json$", p.name)
        if m:
            enbuyuk = max(enbuyuk, int(m.group(1)))
    return max(NO_MIN, enbuyuk + 1)


def kaydi_kur(govde: dict[str, Any], no: int,
              onceki: dict[str, Any] | None = None) -> dict[str, Any]:
    """Gelen gövdeden yazılacak kaydı kurar — saf, diske dokunmaz.

    `onceki` verilirse `girildi` KORUNUR: bir kuponu düzeltmek onu yeniden
    kurmak değildir ve ilk giriş anı kaydın künyesidir.
    """
    simdi = _simdi()
    ad = _metin(govde.get("ad"), AD_SINIR)
    return {
        "surum": SURUM,
        "sezon": sezon_dogrula(govde.get("sezon") or VARSAYILAN_SEZON),
        "no": no_dogrula(no),
        # Adsiz kayit olmaz: liste okunamaz hale gelirdi. Ad verilmediyse
        # numaradan turetilir ve kullanici sonra degistirebilir.
        "ad": ad or f"{no_dogrula(no)}. kupon",
        "hafta": hafta_dogrula(govde.get("hafta")),
        "girildi": (onceki or {}).get("girildi") or simdi,
        "guncellendi": simdi,
        "not": _metin(govde.get("not"), NOT_SINIR),
        "ayar": ayari_dogrula(govde.get("ayar")),
        "satirlar": satirlari_dogrula(govde.get("satirlar")),
        "analiz": analizi_dogrula(govde.get("analiz")),
        "kupon": kuponu_dogrula(govde.get("kupon")),
        "sonuclar": sonuclari_dogrula(govde.get("sonuclar")),
    }


def yaz(govde: dict[str, Any]) -> dict[str, Any]:
    """Kaydı diske yazar ve yazılanı döner.

    `no` verilmişse o kaydın ÜSTÜNE yazar, verilmemişse YENİ kupon açar.
    Ayrım gövdenin kendisinden okunur: arayüz "kaydet" ile "yeni kupon
    olarak kaydet"i ayırabilsin diye.

    Yazma **atomik**: geçici dosyaya yazılıp `os.replace` ile yerine konur.
    Yarıda kesilen bir yazma (süreç ölümü, disk dolması) mevcut kaydı
    bozmaz — elle girilmiş bir kuponu yarım bir JSON'a çevirmek onu
    kaybetmekle aynı şeydir.
    """
    sezon = sezon_dogrula(govde.get("sezon") or VARSAYILAN_SEZON)
    ham_no = govde.get("no")
    if ham_no is None or (isinstance(ham_no, str) and not ham_no.strip()):
        no = sonraki_no(sezon)
        onceki = None
    else:
        no = no_dogrula(ham_no)
        onceki = _oku_sessiz(sezon, no)

    kayit = kaydi_kur(govde, no, onceki=onceki)
    p = yol(kayit["sezon"], kayit["no"])
    p.parent.mkdir(parents=True, exist_ok=True)
    metin = json.dumps(kayit, ensure_ascii=False, indent=1) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=p.parent, prefix=".tmp-", delete=False,
    ) as f:
        f.write(metin)
        gecici = Path(f.name)
    os.replace(gecici, p)
    return kayit


def _oku_sessiz(sezon: Any, no: Any) -> dict[str, Any] | None:
    try:
        return oku(sezon, no)
    except (ArsivHatasi, FileNotFoundError, json.JSONDecodeError):
        return None


def oku(sezon: Any, no: Any) -> dict[str, Any]:
    """Kaydı okur. Yoksa `FileNotFoundError`."""
    p = yol(sezon_dogrula(sezon), no_dogrula(no))
    if not p.exists():
        raise FileNotFoundError(f"kayit yok: {p.name}")
    return json.loads(p.read_text(encoding="utf-8"))


def sil(sezon: Any, no: Any) -> bool:
    """Kaydı siler. Zaten yoksa `False` — bu bir hata DEĞİLDİR."""
    p = yol(sezon_dogrula(sezon), no_dogrula(no))
    if not p.exists():
        return False
    p.unlink()
    return True


def _dolu_satir(satir: dict[str, Any]) -> bool:
    return all(satir.get("oran", {}).get(s) is not None for s in SEMBOLLER)


def listele(sezon: Any = None) -> list[dict[str, Any]]:
    """Sezonun kayıtları — numara sırasıyla, **özet** hâlinde.

    Liste kaydın gövdesini taşımaz: seçicinin ihtiyacı "hangi kuponlar var,
    adları ne, zinciri tam mı". Tamamını taşısaydı on kuponluk bir sezonun
    listesi yüzlerce satır, analizlerle birlikte yüz kilobayt olurdu.

    Zincirin durumu (`analiz_var` · `kupon_var`) özet alanıdır ve **liste
    ekranında okunacak asıl şey**: yarım kalmış bir kupon, kaydı açmadan
    görünmeli.
    """
    dizin = ARSIV / sezon_dogrula(sezon)
    if not dizin.is_dir():
        return []
    cikti: list[dict[str, Any]] = []
    for p in sorted(dizin.glob("kupon_*.json")):
        try:
            k = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Elle bozulmus bir dosya butun listeyi dusurmemeli.
            continue
        satirlar = k.get("satirlar") or []
        kupon = k.get("kupon") or {}
        analiz = k.get("analiz") or {}
        cikti.append({
            "no": k.get("no"),
            "ad": k.get("ad") or "",
            "hafta": k.get("hafta"),
            "girildi": k.get("girildi"),
            "guncellendi": k.get("guncellendi"),
            "not": k.get("not", ""),
            "ayar": k.get("ayar"),
            "oranli_mac": sum(1 for s in satirlar if _dolu_satir(s)),
            "adli_mac": sum(1 for s in satirlar if s.get("ev") and s.get("dep")),
            "analiz_var": bool(analiz),
            "analiz_olculdu": analiz.get("olculdu"),
            "kupon_var": bool(kupon),
            "kolon": kupon.get("kolon"),
            "sonuc_var": bool(k.get("sonuclar")),
        })
    cikti.sort(key=lambda d: d["no"] or 0)
    return cikti


def _cli() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Kupon kurucu haftalik arsivi")
    ap.add_argument("--sezon", default=VARSAYILAN_SEZON)
    ap.add_argument("--liste", action="store_true", help="sezonun kayitlarini yaz")
    ap.add_argument("--no", type=int, help="tek bir kuponu JSON olarak yaz")
    a = ap.parse_args()

    if a.no is not None:
        print(json.dumps(oku(a.sezon, a.no), ensure_ascii=False, indent=1))
        return 0

    kayitlar = listele(a.sezon)
    if not kayitlar:
        print(f"{a.sezon}: kayit yok ({ARSIV / a.sezon})")
        return 0
    print(f"{a.sezon} — {len(kayitlar)} kupon")
    for k in kayitlar:
        ayar = k.get("ayar") or {}
        hafta = f"h{k['hafta']:02d}" if k.get("hafta") else "  - "
        zincir = "".join((
            "G" if k["oranli_mac"] == MAC_SAYISI else "-",
            "A" if k["analiz_var"] else "-",
            "K" if k["kupon_var"] else "-",
            "S" if k["sonuc_var"] else "-",
        ))
        print(f"  #{k['no']:<3} {hafta}  {zincir}  {k['ad'][:28]:<28}"
              f"  {ayar.get('cizgi', '?')}/{ayar.get('arindirma', '?')}"
              f"  {(k.get('kolon') or '-')!s:>7} kolon"
              f"  {k.get('guncellendi', '')[:10]}")
    print("\n  zincir: G girdi · A analiz · K kupon · S sonuc")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
