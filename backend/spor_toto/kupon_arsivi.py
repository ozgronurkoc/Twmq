"""Kupon arşivi — **bir kupon, bir kayıt**.

Arşivin birimi hafta değil **kupon**. Bir haftanın birden çok kuponu olur:
biri açılış oranlarıyla, öteki kapanışla; biri shin, öteki orantılı
arındırmayla. Bunlar birbirinin sürümü değil, ayrı denemelerdir ve yan yana
durmaları gerekir.

Bir kayıt dört şeyi birden taşır — çünkü kupon bu dördünün **zinciridir**:

    girdi     15 maç, elle yazılmış ad ve HER ÇİZGİ İÇİN 1/0/2 oranı
    ayar      hangi arındırma, hangi örneklem, hangi kesme, hangi kapsam
    analizler açılışın ve kapanışın karnesi — ÖLÇÜLDÜĞÜ ANIN damgasıyla
    kupon     o analizlerden çıkan işaretler (ikili kupon + şekilli kuponlar)

Zincirin bir halkası eksikse kayıt "neden bu işaretler" sorusunu
cevaplayamaz.

─── Neden satırda İKİ fiyat var ─────────────────────────────────────────

Sahibinin isteği: *"açılış ve kapanış oranlarını verdiğimde ... açılış
kendi içinde 2 kupon, kapanış kendi içinde 2 kupon olacak."* Yani bir hafta
artık dört kupon üretiyor ve dördü **aynı 15 maçın** iki ayrı fiyatından
çıkıyor. Satır tek fiyat taşısaydı bu dört kupon iki ayrı kayda dağılır ve
"aynı maçlar mıydı" sorusunu hiçbir şey garanti etmezdi.

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
#: 2 -> 3: satırın oranı DÜZ bir `{1,0,2}` idi, ÇİZGİ BAŞINA bloğa dönüştü
#: (`{acilis: {...}, kapanis: {...}}`) ve tek `analiz` bloğu `analizler`
#: sözlüğü oldu. Anlam değişikliği: aynı alan artık başka bir şey tutuyor.
#: Göç kodu YAZILDI ve okumada çalışıyor (`_oranlari_coz`, `kaydi_kur`):
#: düz oran ve tek analiz, kaydın kendi `ayar.cizgi`sine oturur — o kayıtta
#: fiyatın hangi çizgiye ait olduğunu zaten o alan söylüyordu.
SURUM = 3

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

#: Aramanın evreni: bütün korpus mu, maçın kendi ligi mi. İkisi AYNI soruyu
#: sormaz, o yüzden kayıt hangisinin sorulduğunu taşır.
KAPSAMLAR = ("tum", "kendi")

#: Kuponun şekil anahtarının biçimi — arayüzün `SEKILLER` listesindeki
#: `anahtar`. Liste BURAYA KOPYALANMAZ: şekiller ürün kararıdır ve arayüzde
#: yaşar; kopyalansaydı ayrışabilen ikinci bir liste olurdu (`lib/types.ts`
#: lig sözlüğü için aynı kararı veriyor). Doğrulanan şey biçim: kısa, güvenli
#: bir anahtar — çünkü kayda yazılıyor ve listede gösteriliyor.
SEKIL_DESENI = re.compile(r"^[a-z0-9][a-z0-9_-]{0,23}$")

#: Bir kayıtta en çok kaç şekilli kupon durabilir. Bugün dört (iki çizgi x
#: iki şekil); sınır cömert ama sınırsız değil.
SEKIL_SINIRI = 8

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


def _bos_blok() -> dict[str, float | None]:
    """Hiç oran girilmemiş bir çizgi bloğu — üç hücre de `None`."""
    return dict.fromkeys(SEMBOLLER)


def _oranlari_coz(ham: Any, cizgi: str) -> dict[str, dict[str, float | None]]:
    """Satırın `oran` alanını **çizgi başına bloğa** çevirir — eskisini de.

    Yeni biçim `{acilis: {1,0,2}, kapanis: {1,0,2}}`. Eski biçim düz bir
    `{1,0,2}` sözlüğüydü ve hangi çizgiye ait olduğunu KENDİSİ söylemezdi;
    onu `ayar.cizgi` söylüyordu. Göç bu yüzden çizgiyi dışarıdan alıyor ve
    düz bloğu oraya oturtuyor. Öteki çizgi BOŞ kalır: iki çizgiye birden
    kopyalamak, girilmemiş bir fiyatı girilmiş gibi kaydetmek olurdu.
    """
    from .benzer import CIZGILER

    if not isinstance(ham, dict):
        raise ArsivHatasi("satirin orani bir nesne olmali")

    bloklar: dict[str, dict[str, float | None]] = {c: _bos_blok() for c in CIZGILER}
    yeni_bicim = False
    for c in CIZGILER:
        ic = ham.get(c)
        if ic is None:
            continue
        if not isinstance(ic, dict):
            raise ArsivHatasi(f"oran.{c} bir nesne olmali")
        yeni_bicim = True
        bloklar[c] = {s: _oran(ic.get(s)) for s in SEMBOLLER}

    if yeni_bicim:
        return bloklar

    # Eski (düz) biçim. Hiçbir hücresi yoksa satır zaten boştur.
    duz = {s: _oran(ham.get(s)) for s in SEMBOLLER}
    if any(v is not None for v in duz.values()):
        bloklar[cizgi] = duz
    return bloklar


def satirlari_dogrula(ham: Any, cizgi: str) -> list[dict[str, Any]]:
    """15 satır, her satırda lig/ev/dep ve **her çizgi için** 1/0/2.

    Eksik satır **tamamlanır**, fazlası kırpılmaz: uzunluk tam 15 değilse
    reddedilir. Sebep, sessiz kaymanın bedeli — 14 satırlık bir kayıt geri
    okunurken 15. maç boş gelir ve kullanıcı bunu fark etmeyebilir.

    `cizgi` yalnızca ESKİ biçimli gövdeler için kullanılır (bkz.
    `_oranlari_coz`); yeni biçimde hiçbir etkisi yoktur.
    """
    if not isinstance(ham, list):
        raise ArsivHatasi("satirlar bir liste olmali")
    if len(ham) != MAC_SAYISI:
        raise ArsivHatasi(f"satirlar tam {MAC_SAYISI} olmali, {len(ham)} geldi")

    cikti: list[dict[str, Any]] = []
    for i, aday in enumerate(ham, start=1):
        if not isinstance(aday, dict):
            raise ArsivHatasi(f"{i}. satir bir nesne olmali")
        try:
            oran = _oranlari_coz(aday.get("oran") or {}, cizgi)
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

    **`cizgi`nin anlamı 3. sürümde DARALDI.** Artık "bu kaydın tek çizgisi"
    değil; kayıt iki çizginin karnesini birden taşıyor (`analizler`). Kalan
    iki işi var: ekranda açılınca hangi çizginin gösterileceği, ve ikili
    `kupon` bloğunun hangi çizgiden çıktığı. ESKİ kayıtları okumadaki rolü
    ise kritik: düz yazılmış oran ve tek analiz bu alana göre yerleşir.
    """
    from .benzer import CIZGILER
    from .odds import ARINDIRMA_YONTEMLERI

    ham = ham if isinstance(ham, dict) else {}
    # Kapsam: `tum` butun korpus, `kendi` macin KENDI ligi. İkisi aynı
    # soruyu sormaz ve kayıt hangisinin sorulduğunu söylemek zorunda —
    # aynı oranlar, aynı çizgi, farklı kapsam farklı karne verir.
    kapsam = str(ham.get("kapsam") or "tum").strip()
    if kapsam not in KAPSAMLAR:
        raise ArsivHatasi(f"kapsam: {', '.join(KAPSAMLAR)}")
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
    return {"cizgi": cizgi, "arindirma": arindirma, "en_az": en_az,
            "tarih": tarih, "kapsam": kapsam}


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


def analizleri_dogrula(ham: Any, eski: Any, cizgi: str) -> dict[str, Any]:
    """Kaydın **analiz halkası** — çizgi başına bir karne bloğu.

    Dönen sözlükte her çizgi vardır; koşulmamış olan `None` durur. Alan
    baştan tam olsun diye: sonradan eklenen bir anahtar, eski kayıtları
    "eksik" gösterir ve okuyanın her seferinde iki biçimi ayırt etmesini
    gerektirir (`sonuclari_dogrula` ile aynı gerekçe).

    `eski`, 2. sürümün tek `analiz` bloğudur ve varsa `cizgi`ye oturur —
    o kayıtta karnenin hangi çizgide ölçüldüğünü zaten o alan söylüyordu.
    """
    from .benzer import CIZGILER

    cikti: dict[str, Any] = dict.fromkeys(CIZGILER)
    if ham is None and eski is None:
        return cikti
    if ham is not None and not isinstance(ham, dict):
        raise ArsivHatasi("analizler ya null ya bir nesne olmali")

    verilen = ham if isinstance(ham, dict) else {}
    # Bilinmeyen bir çizgi SESSİZCE ATILMAZ: `analizler` sözlüğüne yanlış
    # anahtarla yazan bir istemci, karnesini kaybettiğini fark etmezdi.
    for anahtar in verilen:
        if anahtar not in CIZGILER:
            raise ArsivHatasi(f"analizler.{anahtar}: cizgi {', '.join(CIZGILER)} olmali")
    for c in CIZGILER:
        try:
            cikti[c] = analizi_dogrula(verilen.get(c))
        except ArsivHatasi as e:
            raise ArsivHatasi(f"analizler.{c}: {e}") from None

    if cikti[cizgi] is None and eski is not None:
        cikti[cizgi] = analizi_dogrula(eski)
    return cikti


def _isaretleri_dogrula(ham: Any, ad: str) -> tuple[list[list[str]], int]:
    """15 maçın işaretleri ve kolon sayısı — `kupon` ve `sekilli` ortak."""
    if not isinstance(ham, list) or len(ham) != MAC_SAYISI:
        raise ArsivHatasi(f"{ad} tam {MAC_SAYISI} olmali")
    temiz: list[list[str]] = []
    kolon = 1
    for i, sec in enumerate(ham, start=1):
        if not isinstance(sec, list) or not sec:
            raise ArsivHatasi(f"{i}. macin isareti bos olamaz")
        bilinmeyen = [x for x in sec if x not in SEMBOLLER]
        if bilinmeyen:
            raise ArsivHatasi(f"{i}. macta bilinmeyen sembol: {bilinmeyen!r}")
        # Yinelenen sembol sessizce TEKILLESIR ama sira KUPON duzenine oturur.
        satir = [sem for sem in SEMBOLLER if sem in sec]
        temiz.append(satir)
        kolon *= len(satir)
    return temiz, kolon


def sekilli_dogrula(ham: Any) -> list[dict[str, Any]]:
    """**Şekilli kuponlar** — 6 banko/9 üçlü ve 5/5/5, çizgi başına.

    Kurulmamışsa boş liste. Her kayıt hangi çizgiden çıktığını ve hangi
    şekil anahtarıyla kurulduğunu söyler; `kolon` ile banko/çift/üçlü
    sayıları YAZILMAZ, **hesaplanır** — yazılsaydı kaydın içinde birbirini
    yalanlayabilecek iki sayı olurdu (`kuponu_dogrula` ile aynı karar).

    Aynı (çizgi, şekil) çifti iki kez GELEMEZ: ikisi de "açılışın 5/5/5'i"
    diyen iki satır, hangisinin oynandığını cevaplanamaz yapardı.
    """
    from .benzer import CIZGILER

    if ham is None:
        return []
    if not isinstance(ham, list):
        raise ArsivHatasi("sekilli ya null ya bir liste olmali")
    if len(ham) > SEKIL_SINIRI:
        raise ArsivHatasi(f"sekilli en cok {SEKIL_SINIRI} kupon tasiyabilir")

    cikti: list[dict[str, Any]] = []
    gorulen: set[tuple[str, str]] = set()
    for i, aday in enumerate(ham, start=1):
        if not isinstance(aday, dict):
            raise ArsivHatasi(f"sekilli[{i}] bir nesne olmali")
        cizgi = str(aday.get("cizgi") or "").strip()
        if cizgi not in CIZGILER:
            raise ArsivHatasi(f"sekilli[{i}].cizgi: {', '.join(CIZGILER)}")
        sekil = str(aday.get("sekil") or "").strip()
        if not SEKIL_DESENI.match(sekil):
            raise ArsivHatasi(f"sekilli[{i}].sekil bicimi kabul edilmedi: {sekil!r}")
        if (cizgi, sekil) in gorulen:
            raise ArsivHatasi(f"sekilli[{i}]: ayni cizgi/sekil iki kez geldi")
        gorulen.add((cizgi, sekil))
        try:
            isaretler, kolon = _isaretleri_dogrula(aday.get("isaretler"), "sekilli.isaretler")
        except ArsivHatasi as e:
            raise ArsivHatasi(f"sekilli[{i}]: {e}") from None
        cikti.append({
            "cizgi": cizgi,
            "sekil": sekil,
            "isaretler": isaretler,
            "kolon": kolon,
            "banko": sum(1 for x in isaretler if len(x) == 1),
            "cift": sum(1 for x in isaretler if len(x) == 2),
            "uclu": sum(1 for x in isaretler if len(x) == 3),
        })
    return cikti


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
    temiz, kolon = _isaretleri_dogrula(ham.get("isaretler"), "kupon.isaretler")

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
    # Ayar ONCE cozulur: satirlarin ve analizin ESKI bicimden gocu, kaydin
    # kendi cizgisini bilmeyi gerektiriyor (bkz. `_oranlari_coz`).
    ayar = ayari_dogrula(govde.get("ayar"))
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
        "ayar": ayar,
        "satirlar": satirlari_dogrula(govde.get("satirlar"), ayar["cizgi"]),
        "analizler": analizleri_dogrula(
            govde.get("analizler"), govde.get("analiz"), ayar["cizgi"],
        ),
        "kupon": kuponu_dogrula(govde.get("kupon")),
        "sekilli": sekilli_dogrula(govde.get("sekilli")),
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


def _cizgiler() -> tuple[str, ...]:
    """Sunucunun çizgi listesi. `benzer` içe aktarımı TEMBEL: bu modül
    korpusu açan bir modülü import zincirine sokmamalı."""
    from .benzer import CIZGILER

    return tuple(CIZGILER)


def _dolu_satir(satir: dict[str, Any], cizgi: str, kayit_cizgisi: str) -> bool:
    """Satırın **o çizgideki** üç oranı da girilmiş mi.

    Çizgi başına sayılır, çünkü iki blok bağımsız doldurulabiliyor: yalnızca
    kapanışı girilmiş bir tabloda "15/15 oran tam" demek, açılışın da hazır
    olduğunu söylemek olurdu.

    Listede 2. sürüm dosyaları da okunuyor ve orada oran DÜZ yazılmıştı;
    `kayit_cizgisi` o bloğun hangi çizgiye ait olduğunu söyler (aynı göç
    kuralı `_oranlari_coz`da). Doğrulama YOK — liste bozuk bir dosya
    yüzünden düşmemeli, `kayit_alanlari` orada sayılmaz.
    """
    oran = satir.get("oran") or {}
    blok = oran.get(cizgi)
    if not isinstance(blok, dict):
        # Düz (eski) biçim: yalnızca kaydın kendi çizgisinde sayılır.
        blok = oran if cizgi == kayit_cizgisi and not any(
            isinstance(oran.get(c), dict) for c in _cizgiler()
        ) else {}
    return all(blok.get(s) is not None for s in SEMBOLLER)


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
        # 2. sürüm kayıtlarında tek `analiz` vardı; listede ikisi de aynı
        # soruya cevap veriyor ("karne var mı"), o yüzden birleşik okunur.
        kayit_cizgisi = (k.get("ayar") or {}).get("cizgi") or "kapanis"
        analizler = k.get("analizler") or {}
        if not analizler and k.get("analiz"):
            analizler = {kayit_cizgisi: k["analiz"]}
        olculenler = [a.get("olculdu") for a in analizler.values() if a]
        cikti.append({
            "no": k.get("no"),
            "ad": k.get("ad") or "",
            "hafta": k.get("hafta"),
            "girildi": k.get("girildi"),
            "guncellendi": k.get("guncellendi"),
            "not": k.get("not", ""),
            "ayar": k.get("ayar"),
            # Çizgi başına sayı: hangi tarafın hazır olduğu listeden okunsun.
            "oranli_mac": {
                c: sum(1 for s in satirlar if _dolu_satir(s, c, kayit_cizgisi))
                for c in _cizgiler()
            },
            "adli_mac": sum(1 for s in satirlar if s.get("ev") and s.get("dep")),
            "analiz_var": bool(olculenler),
            # En YENİ damga: liste "bu kayıt ne zaman ölçüldü" sorusuna tek
            # sayı ile cevap verir, iki çizginin ikisini birden yazmaz.
            "analiz_olculdu": max(olculenler) if olculenler else None,
            "analiz_cizgileri": sorted(c for c, a in analizler.items() if a),
            "kupon_var": bool(kupon),
            "kolon": kupon.get("kolon"),
            "sekilli_sayisi": len(k.get("sekilli") or []),
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
