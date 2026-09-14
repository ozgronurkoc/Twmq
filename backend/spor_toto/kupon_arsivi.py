"""Kupon kurucunun haftalık girdi arşivi — **elle girilen kayıt**.

Bu modül bir ölçüm yapmaz, bir tahmin üretmez. Tek işi, kullanıcının
`/kupon` ekranında elle doldurduğu 15 satırlık tabloyu hafta hafta diske
yazmak ve geri okumaktır.

─── Neden diskte, neden tarayıcıda değil ────────────────────────────────

Gerekçe `.claude/olcum_kutugu.json`unkiyle **birebir aynı**: elle girilen
bir kayıt depodan yeniden üretilemez. Türetilmiş olan (envanter, karne,
kolonlar) her zaman yeniden üretilebilir ve sürümlenmez; bir koşum ya da
giriş kaydı üretilemez ve sürümlenir. Tarayıcıda tutulan bir arşiv bu
ayrımın dışında kalırdı: başka makinede yoktur, tarayıcı verisi silinince
gider ve `git log` onu hiç görmez.

─── Neden `hafta_NN.json`un ÜSTÜNE yazmıyor ─────────────────────────────

`data/super_toto/<sezon>/hafta_NN.json` özenle kurulmuş bir künye taşıyor:
`odds_source`, `entered_at` ve dokuz maddelik `data_warnings` ("kapanış
etiketi fazla olabilir", "takım adı eşlemesi doğrulanmadı"). Arayüzden
gelen bir kayıt onun üstüne yazsaydı o kanıt zinciri **sessizce** silinirdi.
Bu yüzden yeni kayıt ayrı bir ailede, onun yanında durur; iki kaydı
birleştirmek istenirse bu bilinçli bir iş olur, bir yan etki değil.

─── Ne YAZILMIYOR ───────────────────────────────────────────────────────

Karne (sorgunun çıktısı) arşive girmez. Türetilmiş veridir ve korpus
büyüdükçe **bayatlar**: iki ay sonra açılan bir kayıt, o günkü korpusun
cevabını bugünün cevabı sanırdı. Kayıt girdiyi ve hangi ayarla bakıldığını
tutar; karne o ayarla yeniden üretilir.

    python -m spor_toto.kupon_arsivi --liste
    python -m spor_toto.kupon_arsivi --hafta 5
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
SURUM = 1

#: Bir haftada kaç maç. `core.SEMBOLLER` gibi bu da tek kaynaktan gelmeli;
#: `meta.MATCH_COUNT` ile aynı sayıdır ve testi bunu tutar.
MAC_SAYISI = 15

#: Sezon anahtarının biçimi — `2026_27`. Katı, çünkü bu değer DOSYA YOLUNA
#: giriyor: serbest bir dize `../../` taşıyabilirdi.
SEZON_DESENI = re.compile(r"^\d{4}_\d{2}$")

VARSAYILAN_SEZON = "2026_27"

#: Hafta numarasının sınırı. Spor Toto sezonu ~40 hafta; üst sınır cömert
#: tutuldu ama sınırsız değil — sınırsız bir tamsayı dosya adına girmez.
HAFTA_MIN, HAFTA_MAX = 1, 60

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


def hafta_dogrula(ham: Any) -> int:
    try:
        hafta = int(ham)
    except (TypeError, ValueError):
        raise ArsivHatasi(f"hafta bir tamsayi olmali: {ham!r}") from None
    if not HAFTA_MIN <= hafta <= HAFTA_MAX:
        raise ArsivHatasi(f"hafta {HAFTA_MIN}-{HAFTA_MAX} arasinda olmali: {hafta}")
    return hafta


def yol(sezon: str, hafta: int) -> Path:
    """Kaydın dosya yolu.

    İki doğrulamadan da geçmiş değerlerle çağrılır; yine de sonuç arşiv
    kökünün altında mı diye bakılır. Bu **savunma derinliği**: bir gün
    doğrulayıcılardan biri gevşerse yol kaçağı burada durur, sessizce
    depodaki başka bir dosyanın üstüne yazılmaz.
    """
    p = (ARSIV / sezon_dogrula(sezon) / f"hafta_{hafta_dogrula(hafta):02d}.json").resolve()
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


def kaydi_kur(govde: dict[str, Any], onceki: dict[str, Any] | None = None) -> dict[str, Any]:
    """Gelen gövdeden yazılacak kaydı kurar — saf, diske dokunmaz.

    `onceki` verilirse `girildi` KORUNUR: bir haftayı düzeltmek onu yeniden
    girmek değildir ve ilk giriş anı kaydın künyesidir.
    """
    sezon = sezon_dogrula(govde.get("sezon") or VARSAYILAN_SEZON)
    hafta = hafta_dogrula(govde.get("hafta"))
    simdi = _simdi()
    return {
        "surum": SURUM,
        "sezon": sezon,
        "hafta": hafta,
        "girildi": (onceki or {}).get("girildi") or simdi,
        "guncellendi": simdi,
        "not": _metin(govde.get("not"), NOT_SINIR),
        "ayar": ayari_dogrula(govde.get("ayar")),
        "satirlar": satirlari_dogrula(govde.get("satirlar")),
        "sonuclar": sonuclari_dogrula(govde.get("sonuclar")),
    }


def yaz(govde: dict[str, Any]) -> dict[str, Any]:
    """Kaydı diske yazar ve yazılanı döner.

    Yazma **atomik**: geçici dosyaya yazılıp `os.replace` ile yerine
    konur. Yarıda kesilen bir yazma (süreç ölümü, disk dolması) mevcut
    kaydı bozmaz — elle girilmiş bir haftayı yarım bir JSON'a çevirmek
    onu kaybetmekle aynı şeydir.
    """
    kayit = kaydi_kur(govde, onceki=_oku_sessiz(govde.get("sezon"), govde.get("hafta")))
    p = yol(kayit["sezon"], kayit["hafta"])
    p.parent.mkdir(parents=True, exist_ok=True)
    metin = json.dumps(kayit, ensure_ascii=False, indent=1) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=p.parent, prefix=".tmp-", delete=False,
    ) as f:
        f.write(metin)
        gecici = Path(f.name)
    os.replace(gecici, p)
    return kayit


def _oku_sessiz(sezon: Any, hafta: Any) -> dict[str, Any] | None:
    try:
        return oku(sezon, hafta)
    except (ArsivHatasi, FileNotFoundError, json.JSONDecodeError):
        return None


def oku(sezon: Any, hafta: Any) -> dict[str, Any]:
    """Kaydı okur. Yoksa `FileNotFoundError`."""
    p = yol(sezon_dogrula(sezon), hafta_dogrula(hafta))
    if not p.exists():
        raise FileNotFoundError(f"kayit yok: {p.name}")
    return json.loads(p.read_text(encoding="utf-8"))


def sil(sezon: Any, hafta: Any) -> bool:
    """Kaydı siler. Zaten yoksa `False` — bu bir hata DEĞİLDİR."""
    p = yol(sezon_dogrula(sezon), hafta_dogrula(hafta))
    if not p.exists():
        return False
    p.unlink()
    return True


def _dolu_satir(satir: dict[str, Any]) -> bool:
    return all(satir.get("oran", {}).get(s) is not None for s in SEMBOLLER)


def listele(sezon: Any = None) -> list[dict[str, Any]]:
    """Sezonun kayıtları — hafta sırasıyla, **özet** hâlinde.

    Liste 15 satırın tamamını taşımaz: hafta seçicinin ihtiyacı
    "hangi haftalar var, ne zaman girildi, kaç satırı tam". Tamamını
    taşısaydı 40 haftalık bir sezonun listesi 600 satır olurdu.
    """
    dizin = ARSIV / sezon_dogrula(sezon)
    if not dizin.is_dir():
        return []
    cikti: list[dict[str, Any]] = []
    for p in sorted(dizin.glob("hafta_*.json")):
        try:
            k = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Elle bozulmus bir dosya butun listeyi dusurmemeli.
            continue
        satirlar = k.get("satirlar") or []
        cikti.append({
            "hafta": k.get("hafta"),
            "girildi": k.get("girildi"),
            "guncellendi": k.get("guncellendi"),
            "not": k.get("not", ""),
            "ayar": k.get("ayar"),
            "oranli_mac": sum(1 for s in satirlar if _dolu_satir(s)),
            "adli_mac": sum(1 for s in satirlar if s.get("ev") and s.get("dep")),
            "sonuc_var": bool(k.get("sonuclar")),
        })
    cikti.sort(key=lambda d: d["hafta"] or 0)
    return cikti


def _cli() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Kupon kurucu haftalik arsivi")
    ap.add_argument("--sezon", default=VARSAYILAN_SEZON)
    ap.add_argument("--liste", action="store_true", help="sezonun kayitlarini yaz")
    ap.add_argument("--hafta", type=int, help="tek bir haftayi JSON olarak yaz")
    a = ap.parse_args()

    if a.hafta is not None:
        print(json.dumps(oku(a.sezon, a.hafta), ensure_ascii=False, indent=1))
        return 0

    kayitlar = listele(a.sezon)
    if not kayitlar:
        print(f"{a.sezon}: kayit yok ({ARSIV / a.sezon})")
        return 0
    print(f"{a.sezon} — {len(kayitlar)} kayit")
    for k in kayitlar:
        ayar = k.get("ayar") or {}
        print(f"  hafta {k['hafta']:>2}  {k['oranli_mac']:>2}/{MAC_SAYISI} oran"
              f"  {k['adli_mac']:>2}/{MAC_SAYISI} ad"
              f"  {ayar.get('cizgi', '?')}/{ayar.get('arindirma', '?')}"
              f"  {k.get('guncellendi', '')}"
              f"{'  [sonuclu]' if k['sonuc_var'] else ''}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
