"""Benzer maç arama — "bu oranda geçmişte ne olmuş?"

Bir maçın oranını alır, 23.085 maçlık eğitim korpusunda **aynı fiyata sahip**
maçları bulur ve nasıl sonuçlandıklarını sayar:

    python -m spor_toto.benzer --oran 1.82,3.04,2.44

Bu modül tahmin üretmez. Ürettiği tek şey ampirik bir cevaptır: *piyasa bu
fiyatı verdiğinde geçmişte ne oldu.* Asıl sorduğu soru "yüzde kaçı ev sahibi
kazanmış" değil, **"piyasa sözünü tutmuş mu"** — bu yüzden her satırda
piyasanın kendi dediği yüzde de yazar.

─── Neden oran uzayında arama YAPILMAZ ────────────────────────────────────────

En önemli tasarım kararı bu. Aynı gerçek olasılık, farklı marjda tamamen
farklı oran verir: %18 marjlı bir iddaa bülteninde 1.82 ne diyorsa, %7 marjlı
football-data arşivinde başka bir sayı onu der. Ölçüldü (2026-09-12) —
1.82/3.04/2.44 (marj %28,8) korpusta, **her iki çizgide de aynı sonuç**:

                                      kapanış      açılış
    birebir aynı oran ..............    0 maç       0 maç
    oran ±%2 .......................    0 maç       0 maç
    oran ±%10 ......................    0 maç       0 maç
    olasılık ±2 puan ................ 426 maç     504 maç

Yani oran uzayında arama sessizce "sonuç yok" der. Eşleme **marj
arındırıldıktan sonra olasılık uzayında** yapılır; `tests/test_benzer.py`
bunu regresyon testine bağlar.

Sayılar 709/710 olarak yazılıydı ve 2026-09-12'de korpus 22 ligden 17'ye
inince bayatladı: o koşumda korpus boyutu satırı güncellendi, hemen
üstündeki bu blok güncellenmedi. İkisi de **yeniden ölçüldü**, eskisinden
türetilmedi; tekrarı `test_docstring_olcumu_GERCEK_kosumla_ayni` tutar.

─── Örneklem dürüstlüğü ──────────────────────────────────────────────────────

Bu araç yanlış kullanılmaya en müsait yer olduğu için üç koruma taşır:

1. Hiçbir yüzde **n ve güven aralığı olmadan** dönmez. "44 maçın 35'i ev
   sahibi" tek başına bir bilgi değildir; 44 maçta %80 ile %55 arasındaki
   fark gürültüdür.
2. `AZ_ORNEK` (30) altındaki dilim sayı vermez, "yetersiz" der.
3. Dilimleme (lig × sezon) çoklu karşılaştırma uyarısı bastırır: 22 lig ×
   4 sezon taranırsa rastgele bir yerde çarpıcı bir oran **kesinlikle**
   çıkar ve o bir bulgu değildir.
4. `tarih=T` verilirse evren **T'den öncesiyle** sınırlanır. Karşılaştırma
   katı küçüktür — aynı gün oynanan maçlar da düşer — ve bu, sorulan maçın
   kendi cevabına girmesini ayrı bir koda gerek kalmadan engeller. Gerekçe
   `_dogrula_tarih` yorumunda; sözleşme `tests/test_sizinti.py`te.

Korpusun birincil fiyatı 23.085 satırın **hepsinde kapanış** ortalamasıdır
(`oran_kaynak = AvgC`) ve varsayılan arama orada yapılır. `cizgi="acilis"`
aynı soruyu **açılış** çizgisinde sorar; o evren 23.083 satırdır (bkz.
`CIZGILER`). İki evren arasındaki fark **tam 2 satır** olduğu için iki
çizginin karneleri arasındaki fark evren farkından gelemez — fiyattan gelir;
bekçisi `test_acilis_ve_kapanis_EVRENI_tam_iki_satir_ayrisir`.
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from .egitim import korpus_yukle
from .odds import (
    ARINDIRMA_VARSAYILAN,
    AZ_ORNEK,
    LIG_ADLARI,
    SEMBOLLER,
    implied_probs,
    margin,
)
from .ortak import wilson

#: Aramanın başladığı yarıçap (olasılık puanı). Dar başlanır ki yakın maç
#: varken uzak maç sayılmasın.
BASLANGIC_TOLERANS = 0.01
#: Yarıçap her adımda bu kadar büyür.
TOLERANS_ADIMI = 0.005
#: Genişlemenin durduğu yer. Ötesi "benzer maç" olmaktan çıkar: %5 puan,
#: banko eşiğiyle çifte eşiği arasındaki mesafenin yarısıdır.
EN_COK_TOLERANS = 0.05
#: Uyarlanan aramanın hedeflediği en az örneklem. 200 maçta bir yüzdenin
#: Wilson aralığı ±%7 civarıdır — okunabilir ama hâlâ geniş.
HEDEF_ORNEKLEM = 200
#: Bu sayıdan çok dilim açılırsa çoklu karşılaştırma uyarısı basılır.
COK_DILIM = 8
#: Aramanın hangi fiyat çizgisinde yapılacağı. Varsayılan `kapanis`, çünkü
#: korpusun birincil fiyatı (`oran_*`) her satırda kapanış ortalamasıdır —
#: yani varsayılan yol bu eksen eklenmeden önceki davranışın ta kendisidir.
#:
#: **Neden eksen oldu.** Kupon kapanmadan önce oynanır; haftanın geç
#: maçlarında kapanış fiyatı kupon verilirken HENÜZ YOKTUR
#: (`scripts/acilis_kapanis.py` başlığı). Elinde açılış oranı olan biri
#: kapanış evreninde arama yaparsa elmayı armutla karşılaştırır: aynı maçın
#: iki fiyatı arasındaki fark bu deponun ayrıca ölçtüğü bir şeydir.
CIZGILER: tuple[str, ...] = ("kapanis", "acilis")


def _dogrula(oranlar: dict[str, float], tolerans: float | None,
             en_az: int, cizgi: str = "kapanis") -> None:
    """Girdiyi tek kapıda denetler — fonksiyon, CLI ve HTTP aynı kuralı görsün.

    Kural üç kapıda üç türlüydü: fonksiyonun hiç sınırı yoktu, CLI `float`
    neyi kabul ederse onu alıyordu, HTTP ise `_parse_esik` ile toleransı
    sessizce `[0, 1]`'e **kırpıyordu** — yani `?tolerans=0.9` hata vermeden
    başka bir sorguya dönüşüyordu.

    İki delik ölçüldü ve ikisi de burada kapanıyor:

    `inf` **kabul ediliyordu.** `inf <= 1.0` yanlıştır, yani eski kapıdan
    geçerdi; `implied_probs` ona `0.0` olasılık verir ve üç anahtar döndüğü
    için `len(hedef) != 3` kontrolü de yakalamazdı. Sorgu koşar ve bir
    sembolü olmayan bir hedef vektörle korpusu tarardı.

    `nan` yakalanıyordu ama **yanlış mesajla**: sembol arındırmadan sessizce
    düşer, `len(hedef) != 3` devreye girer ve "üç sembolün de oranı gerekli"
    denirdi. Kullanıcı üç oranı da vermiştir; mesaj yanlış yeri gösterirdi.

    Tolerans tavanı uydurma değil: `EN_COK_TOLERANS` uyarlanan aramanın
    zaten durduğu yer (bkz. sabitin kendi yorumu). Otomatik yolun "benzer
    olmaktan çıkar" dediği yarıçapta elle yolun serbest kalması bir özellik
    değil, tutarsızlıktı.
    """
    for s in SEMBOLLER:
        v = oranlar.get(s)
        if v is None:
            raise ValueError(f"'{s}' oranı eksik")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ValueError(f"'{s}' oranı sayı olmalı")
        if not math.isfinite(v):
            raise ValueError(f"'{s}' oranı sonlu bir sayı olmalı (verilen: {v})")
        if v <= 1.0:
            raise ValueError(f"'{s}' oranı 1.00'den büyük olmalı (verilen: {v})")

    if tolerans is not None:
        if not math.isfinite(tolerans):
            raise ValueError(f"tolerans sonlu olmalı (verilen: {tolerans})")
        if tolerans < 0:
            raise ValueError(f"tolerans negatif olamaz (verilen: {tolerans})")
        if tolerans > EN_COK_TOLERANS:
            raise ValueError(
                f"tolerans en çok {EN_COK_TOLERANS} olabilir (verilen: "
                f"{tolerans}). Ötesi 'benzer maç' olmaktan çıkar — uyarlanan "
                f"arama da orada duruyor.")

    if en_az < 1:
        raise ValueError(f"en_az en az 1 olmalı (verilen: {en_az})")

    # Bilinmeyen çizgi sessizce varsayılana DUSMEZ. Düşseydi `?cizgi=AvgC`
    # yazan biri kapanış cevabını alır ve açılış sorduğunu sanırdı — bu
    # fonksiyonun yukarıdaki iki deliğiyle (`inf`, kırpılan tolerans) aynı
    # türden bir arıza: istek reddedilmiyor, BASKA BIR SORGUYA çevriliyor.
    if cizgi not in CIZGILER:
        raise ValueError(
            f"cizgi {' | '.join(CIZGILER)} olmalı (verilen: {cizgi!r})")


def _dogrula_tarih(tarih: str | None) -> None:
    """`tarih` süzgecinin biçimi — `YYYY-MM-DD`, korpusun kendi biçimi.

    ─── Zaman kesme niçin var ─────────────────────────────────────────────

    Süzgeç eskiden yalnızca `lig` ve `sezon`du. `tarih` her satırda yüklüydü
    (`egitim.korpus_yukle`) ama hiç okunmuyordu. Sonuç: 2022 tarihli bir
    fiyat sorulduğunda 2024–2025 maçları da "geçmişte ne oldu" cevabına
    giriyordu.

    **Bu canlı tahmine sızıntı DEĞİL** — korpus güncel sezonu içermiyor ve
    bunu `test_egitim.test_varsayilan_korpus_guncel_sezonu_icermez`
    bekçiliyor. Kusur başka: bu modül o hâliyle **hiçbir kronolojik ölçümün
    içine konulamıyordu.** Depo bunun bedelini ölçtü — ileri yürüyüşte
    kronoloji zorlandığında piyasanın artığını öğrenen aileler 2–3 kat
    kötüleşti (`ISTATISTIK_YOL_HARITASI.md` §6.6). `benzer`in sayıları o
    sınavdan hiç geçmedi, çünkü sınava sokulamıyordu.

    Karşılaştırma **katı küçüktür** ve `datetime`sizdir: korpus tarihleri
    ISO dizgi (`2021-07-23`), ISO dizgilerde sözlük sırası takvim sırasıdır.
    Katılık aynı zamanda "kendini dışla"yı bedavaya çözer: aynı gün oynanan
    maçlar da düştüğü için sorulan maç kendi cevabına giremez.
    """
    if tarih is None:
        return
    if not isinstance(tarih, str):
        raise ValueError("tarih 'YYYY-MM-DD' biçiminde bir dizgi olmalı")
    p = tarih.split("-")
    if (len(p) != 3 or [len(x) for x in p] != [4, 2, 2]
            or not all(x.isdigit() for x in p)):
        raise ValueError(
            f"tarih 'YYYY-MM-DD' biçiminde olmalı (verilen: {tarih!r})")


def _mesafe(a: dict[str, float], b: dict[str, float]) -> float:
    """İki olasılık vektörü arasındaki en büyük tek sembol farkı (L∞).

    Öklid değil L∞: "hiçbir sembolde X puandan fazla ayrılmasın" kuralı,
    kullanıcının kafasındaki "aynı oranlar" fikrine karşılık gelen ölçüdür.
    Öklid, bir sembolde büyük sapmayı başka iki sembolde küçük sapmayla
    örtebilirdi.
    """
    return max(abs(a[s] - b[s]) for s in SEMBOLLER)


def _cizgi_orani(r: dict[str, Any], cizgi: str) -> dict[str, float] | None:
    """Satırın seçili çizgideki fiyatı — yoksa `None` (satır evrene girmez).

    `kapanis` için `r["oranlar"]` okunur, `r["kapanis"]` DEGIL. İkisi aynı
    fiyattır (korpusun `oran_kaynak`ı her satırda `AvgC`) ama `kapanis`
    alanı `acilis` ile birlikte düşer: `egitim._cizgi_uclusu` çifti "ya tam
    ya yok" diye taşır, yani açılışı eksik iki satırda `kapanis` de `None`
    olur. `oranlar`ı okumak bu eksenin varsayılan yolunu, eksen eklenmeden
    önceki davranışla **birebir** aynı tutar — regresyon sabitleri kımıldamaz.
    """
    return r["oranlar"] if cizgi == "kapanis" else r.get(cizgi)


@lru_cache(maxsize=16)
def _olasilik_tablosu(yontem: str, korpus: str | None, cizgi: str = "kapanis"
                      ) -> tuple[tuple[dict[str, float], dict[str, Any]], ...]:
    """Korpusun tamamının arındırılmış olasılıkları — yöntem başına bir kez.

    Bunsuz her sorgu 23 bin satırı yeniden arındırıyordu (~2 sn). Bir hafta
    sayfası 15 maç için 15 sorgu yapar; onbelleksiz yarım dakika sürerdi.
    Korpus sürümlenmiş bir dosyadır, aynı yöntem hep aynı tabloyu verir.

    `maxsize` çizgi ekseniyle birlikte 8'den 16'ya çıktı: anahtar artık
    (yöntem × korpus yolu × **çizgi**) ve üç arındırma × iki çizgi zaten
    altı gözü tek başına doldurur.

    Dönen yapı **okunmak içindir**; çağıran taraf satırları değiştirmemeli
    (onbellekteki nesnenin ta kendisidir).
    """
    out = []
    for r in korpus_yukle(korpus):
        ham = _cizgi_orani(r, cizgi)
        if ham is None:
            continue
        p = implied_probs(ham, yontem)
        if len(p) == 3:
            out.append((p, r))
    return tuple(out)


def _mesafe_ozeti(mesafeler: Sequence[float]) -> dict[str, float] | None:
    """Bulunan maçların ne kadar "benzer" olduğu — sıralı listeden bedavaya.

    Bu blok yeni bir soru sormuyor; **var olan bir bayrağı okunabilir
    kılıyor.** `tolerans_genisledi` bugün bir boolean: "yarıçap büyüdü".
    Büyüdüğünde okuyanın soracağı tek soru şudur — *gerçekten benzer maç mı
    bulundu, yoksa örneklem toplamak için uzağa mı uzanıldı?* Ortanca mesafe
    tavana dayanmışsa cevap ikincisidir ve bunu gösteren başka sayı yok.

    Payda `bulunan`dır: bütün mesafeler tanım gereği `[0, tolerans]`
    aralığındadır, yani tavana yakın bir ortanca doğrudan "sınırdan
    toplandı" demektir.
    """
    if not mesafeler:
        return None
    n = len(mesafeler)
    # Girdi `benzer_maclar`ta zaten sıralı; ortanca için yeniden sıralanmıyor.
    orta = (mesafeler[n // 2] if n % 2
            else (mesafeler[n // 2 - 1] + mesafeler[n // 2]) / 2)
    return {
        "en_yakin": mesafeler[0],
        "ortanca": orta,
        "ortalama": sum(mesafeler) / n,
        "en_uzak": mesafeler[-1],
    }


def _sayim(maclar: Sequence[dict[str, Any]],
           piyasa: dict[str, float]) -> dict[str, Any]:
    """Bir maç kümesinin 1/0/2 karnesi — her satırda n, GA ve piyasa payı."""
    n = len(maclar)
    satirlar = {}
    for s in SEMBOLLER:
        k = sum(1 for m in maclar if m["kod"] == s)
        if n:
            alt, ust = wilson(k, n)
        else:
            alt = ust = 0.0
        bekleniyor = piyasa[s]
        satirlar[s] = {
            "adet": k,
            "oran": (k / n) if n else None,
            "ga_alt": alt,
            "ga_ust": ust,
            # Piyasanın dediği bu aralığın DIŞINDAYSA, o fiyatta piyasa
            # sözünü tutmamış demektir. Asıl okunacak sütun budur.
            "piyasa": bekleniyor,
            "fark": ((k / n) - bekleniyor) if n else None,
            "piyasa_ga_icinde": (alt <= bekleniyor <= ust) if n else None,
        }
    return {"n": n, "yeterli": n >= AZ_ORNEK, "semboller": satirlar}


def _ara(hedef: dict[str, float], tolerans: float | None, en_az: int,
         lig: str | None, sezon: str | None, yontem: str,
         korpus: str | None, tarih: str | None, cizgi: str
         ) -> tuple[list[tuple[float, dict[str, Any]]], int, float, bool, int,
                    dict[str, int]]:
    """Evreni kurar, mesafeleri ölçer, yarıçapı uyarlar — **tek kopya**.

    `benzer_maclar` ve `benzer_mac_listesi` bu kümeyi aynı yerden almak
    zorunda. Ayrı ayrı kurulsalardı ikisi sessizce farklı bir yarıçapta
    durabilirdi ve kullanıcı, sayılan maçlardan BASKA maçların listesini
    görürdü — üstelik bunu gösteren hiçbir alan olmadan.

    Dönüş: `(yakinlar, evren_boyu, kullanilan_tolerans, genisledi, kesilen,
    taban)`; `yakinlar` = `[(mesafe, satir)]`, mesafeye göre artan sıralı,
    `taban` = evrenin tamamının 1/0/2 sayımı.

    **`taban` niçin var.** Tek başına bir yüzde okunamaz: "bu oranda %58 ev
    sahibi" çarpıcı görünür, ama korpusun genelinde ev sahibi zaten %43,5
    kazanıyor. Fiyatın taşıdığı bilgi ikisinin FARKIDIR. Sayı arayüzde elle
    yazılmaz, bu sorgunun kendi evreninden sayılır — lig/sezon/tarih
    süzgeçleri uygulandıktan sonra, yani kıyas hep aynı havuzla yapılır.
    """
    dilim = [(p, r) for p, r in _olasilik_tablosu(yontem, korpus, cizgi)
             if (lig is None or r["lig"] == lig)
             and (sezon is None or r["sezon"] == sezon)]
    # Kesme lig/sezon süzgecinden SONRA sayılır: `evren_kesilen` "bu sorgunun
    # evreninden kaç maç düştü" demek, "korpustan" değil.
    evren = ([(p, r) for p, r in dilim if r["tarih"] < tarih]
             if tarih is not None else dilim)
    kesilen = len(dilim) - len(evren)
    # Mesafe bir kez hesaplanır; hem uyarlanan arama hem dilimler bunu okur.
    olculu = sorted(((_mesafe(p, hedef), r) for p, r in evren),
                    key=lambda x: x[0])

    if tolerans is not None:
        kullanilan, genisledi = tolerans, False
    else:
        kullanilan, genisledi = BASLANGIC_TOLERANS, False
        while kullanilan < EN_COK_TOLERANS:
            if sum(1 for d, _ in olculu if d <= kullanilan) >= en_az:
                break
            kullanilan = round(kullanilan + TOLERANS_ADIMI, 6)
            genisledi = True

    # `olculu` sıralı: mesafeler de sırayla çıkıyor, ayrıca sıralanmıyor.
    yakinlar = [(d, r) for d, r in olculu if d <= kullanilan]
    taban = {s: sum(1 for _, r in olculu if r["kod"] == s) for s in SEMBOLLER}
    return yakinlar, len(olculu), kullanilan, genisledi, kesilen, taban


def benzer_maclar(oranlar: dict[str, float],
                  tolerans: float | None = None,
                  en_az: int = HEDEF_ORNEKLEM,
                  lig: str | None = None,
                  sezon: str | None = None,
                  yontem: str = ARINDIRMA_VARSAYILAN,
                  korpus: str | None = None,
                  tarih: str | None = None,
                  cizgi: str = "kapanis") -> dict[str, Any]:
    """Verilen orana benzeyen geçmiş maçları bulur ve karnelerini çıkarır.

    `tolerans=None` iken yarıçap **uyarlanır**: `BASLANGIC_TOLERANS`'tan
    başlar, `en_az` maça ulaşana kadar büyür, `EN_COK_TOLERANS`'ta durur.
    Fiilen kullanılan yarıçap raporda her zaman yazar — genişlemiş bir arama
    kendini gizlememeli.

    `tarih="YYYY-MM-DD"` verilirse evren **o günden öncesiyle** sınırlanır.
    Karşılaştırma katı küçüktür: aynı gün oynanan maçlar da dışarıda kalır,
    böylece sorulan maçın kendisi kendi cevabına giremez — ayrı bir "kendini
    dışla" koduna gerek yok. Gerekçe `_zaman_kesme` yorumunda.

    `tarih=None` (varsayılan) bugünkü davranışı birebir korur.

    `cizgi="acilis"` aramayı **açılış** fiyatlarının evreninde yapar;
    varsayılan `kapanis` korpusun birincil fiyatıdır (bkz. `CIZGILER`).
    Hangi çizgide arandığı raporda her zaman yazar.
    """
    _dogrula(oranlar, tolerans, en_az, cizgi)
    _dogrula_tarih(tarih)
    hedef = implied_probs(oranlar, yontem)
    if len(hedef) != 3:
        # `_dogrula`dan sonra bu artık gerçekten "arındırma üç sembol
        # üretemedi" demek: `nan`/`inf` bir üst kapıda adıyla düşüyor.
        raise ValueError("üç sembolün de oranı gerekli")

    yakinlar, evren_boyu, kullanilan, genisledi, kesilen, taban = _ara(
        hedef, tolerans, en_az, lig, sezon, yontem, korpus, tarih, cizgi)
    bulunan = [r for _, r in yakinlar]
    rapor: dict[str, Any] = {
        "oranlar": dict(oranlar),
        "marj": margin(oranlar),
        "arindirma": yontem,
        "hedef_olasilik": hedef,
        "tolerans": kullanilan,
        "tolerans_uyarlandi": tolerans is None,
        "tolerans_genisledi": genisledi,
        "tolerans_tavana_dayandi": (tolerans is None
                                    and kullanilan >= EN_COK_TOLERANS
                                    and len(bulunan) < en_az),
        "evren": evren_boyu,
        "cizgi": cizgi,
        "as_of": tarih,
        "evren_kesilen": kesilen,
        "filtre": {"lig": lig, "sezon": sezon},
        "mesafe": _mesafe_ozeti([d for d, _ in yakinlar]),
        "toplam": _sayim(bulunan, hedef),
        # Kiyas cizgisi: aynı evrenin TAMAMINDA 1/0/2 nasıl dagiliyor.
        # Bir yuzde ancak bunun yaninda okunur (gerekce `_ara` govdesinde).
        "taban": taban,
        "uyarilar": [],
    }

    if not bulunan:
        rapor["uyarilar"].append(
            "Bu yarıçapta hiç maç yok. Oran uzayında değil OLASILIK uzayında "
            "arandığı için bu ancak çok uç bir fiyatta olur.")
    elif len(bulunan) < AZ_ORNEK:
        rapor["uyarilar"].append(
            f"Örneklem {len(bulunan)} maç — {AZ_ORNEK} altında yüzde okunmaz.")
    if rapor["tolerans_tavana_dayandi"]:
        rapor["uyarilar"].append(
            f"Yarıçap tavana (±{100*EN_COK_TOLERANS:.0f} puan) dayandı ve "
            f"{en_az} maça ulaşılamadı; bulunanlar 'benzer' sayılamayacak "
            f"kadar uzak olabilir.")
    if rapor["marj"] > 0.12:
        rapor["uyarilar"].append(
            f"Girilen oranın marjı %{100*rapor['marj']:.1f}; korpus ~%7 "
            f"marjlı. Arındırma yöntemi ({yontem}) bu farkta sonucu "
            f"görünür biçimde değiştirir.")

    rapor["dilimler"] = {
        "lig": _dilimle(bulunan, hedef, "lig"),
        "sezon": _dilimle(bulunan, hedef, "sezon"),
    }
    acik = sum(1 for grup in rapor["dilimler"].values()
               for d in grup if d["karne"]["yeterli"])
    if acik > COK_DILIM:
        rapor["uyarilar"].append(
            f"{acik} dilim açıldı. Bu kadar dilimde en çarpıcı olanın "
            f"rastlantı olma ihtimali yüksektir — dilim tek başına bulgu "
            f"değildir.")
    return rapor


def lig_envanteri(cizgi: str = "kapanis") -> list[dict[str, Any]]:
    """Korpusta HANGİ ligler var ve her birinde kaç maç.

    **Neden gerekli.** `/kupon` sayfasında maçlar maçın kendi liginde
    aranabiliyor ve o sorgu `lig=` ile yapılıyor. Kullanıcının yazdığı lig
    kodu korpusta yoksa arama sessizce **boş** döner — yani kullanıcı
    "bu fiyatta hiç benzer maç yok" ile "yazdığım kodu tanımıyorum"u
    ayırt edemez. Bu liste o ayrımı mümkün kılar.

    **Neden `/api/meta`da değil.** Bu fonksiyon korpusu okur (23 bin satır);
    `meta` ise her sayfanın açılışta çağırdığı ucuz bir envanterdir ve
    `benzer` modülü tam bu yüzden modül düzeyinde import EDİLMİYOR. Liste
    kendi ucunda durur ve orada önbelleklenir.

    Çeviri burada yapılır (`odds.LIG_ADLARI`), arayüzde değil — `_etiket`in
    gerekçesiyle aynı: harita sunucuda zaten var, kopyalansaydı ayrışabilen
    ikinci bir sözlük olurdu.
    """
    if cizgi not in CIZGILER:
        raise ValueError(f"cizgi: {', '.join(CIZGILER)}")
    sayim: dict[str, int] = {}
    for r in korpus_yukle():
        # Evrenin tanımı `_cizgi_orani`dir — ARAMANIN kendi kullandığı
        # fonksiyon. Burada `r.get(cizgi)` yazmak ikinci bir tanım olurdu
        # ve YANLIŞ olurdu: korpusta kapanış fiyatı `oranlar` anahtarında
        # durur, `kapanis` diye bir alan yoktur. Liste ile aramanın aynı
        # evreni saydığını garanti eden tek şey bu ortak çağrıdır.
        if _cizgi_orani(r, cizgi) is None:
            continue
        kod = r.get("lig") or ""
        if kod:
            sayim[kod] = sayim.get(kod, 0) + 1
    return sorted(
        ({"lig": k, "etiket": LIG_ADLARI.get(k, k), "n": v} for k, v in sayim.items()),
        key=lambda d: (-d["n"], d["lig"]),
    )


def _dilimle(maclar: Sequence[dict[str, Any]], hedef: dict[str, float],
             alan: str) -> list[dict[str, Any]]:
    """Bulunan maçları bir alana göre böler; her dilim kendi n'i ve GA'sıyla.

    Lig diliminde ayrıca okunur bir `etiket` taşınır (`odds.LIG_ADLARI`).
    Çeviri **sunucuda** yapılır çünkü harita orada zaten var; arayüze
    kopyalansaydı iki yerde tutulan ve ayrışabilen bir sözlük daha olurdu.
    Eşleşmeyen kod olduğu gibi geçer — `odds.LIG_ADLARI` yorumundaki kural:
    uydurma ad üretilmez.
    """
    gruplar: dict[str, list[dict[str, Any]]] = {}
    for m in maclar:
        gruplar.setdefault(m[alan], []).append(m)
    out = [{"deger": k, "etiket": _etiket(k, alan), "karne": _sayim(v, hedef)}
           for k, v in gruplar.items()]
    out.sort(key=lambda d: -d["karne"]["n"])
    return out


def _etiket(deger: str, alan: str) -> str:
    """Dilim değerinin okunur karşılığı; yalnızca lig için çeviri var."""
    return LIG_ADLARI.get(deger, deger) if alan == "lig" else deger


#: Maç listesinin tek seferde döndürebileceği en çok satır. Tavan uydurma
#: değil: `HEDEF_ORNEKLEM`in (200) iki buçuk katı — uyarlanan aramanın
#: hedeflediği örneklemin tamamı tek sayfada, genişlemiş aramanın fazlası da
#: büyük ölçüde sığar.
EN_COK_LISTE = 500


def benzer_mac_listesi(oranlar: dict[str, float], *,
                       tolerans: float,
                       lig: str | None = None,
                       sezon: str | None = None,
                       yontem: str = ARINDIRMA_VARSAYILAN,
                       korpus: str | None = None,
                       tarih: str | None = None,
                       cizgi: str = "kapanis",
                       limit: int = HEDEF_ORNEKLEM,
                       atla: int = 0) -> dict[str, Any]:
    """Karnenin arkasındaki **maçların kendisi** — tarih, skor, sonuç, fiyat.

    `benzer_maclar` bir yüzde döndürür; bu fonksiyon o yüzdenin sayıldığı
    satırları döndürür. Yüzde bir iddiadır ve bu depo iddiayı `n` ve güven
    aralığı olmadan yazmaz; **maç listesi bir iddia değil kayıttır**, o
    yüzden `AZ_ORNEK` eşiği burada uygulanmaz. 12 maçlık bir ligin yüzdesi
    okunmaz ama o 12 maç görülebilir.

    ─── `tolerans` niçin ZORUNLU ──────────────────────────────────────────

    Tek gerçek tuzak bu. Uyarlanan yarıçap **evrene** bağlıdır: `en_az` maça
    ulaşana kadar büyür. `lig="T1"` ile çağrılan bir arama, bütün liglerde
    çalışan aramadan daha küçük bir evrende durur, yani **daha geniş** bir
    yarıçapta dinlenir. Liste kendi yarıçapını uyarlasaydı, kullanıcı lig
    satırında "n=34" okuyup tıkladığında 51 maç görebilirdi — ve iki sayının
    neden tutmadığını gösteren hiçbir alan olmazdı.

    Bu yüzden çağıran taraf (arayüz de, CLI de) ana cevaptaki **çözülmüş**
    `tolerans`ı aynen geri verir. Bekçisi
    `tests/test_benzer.py::test_mac_listesi_karneyle_AYNI_kumeyi_sayar`.
    """
    if tolerans is None:
        raise ValueError(
            "mac listesi tolerans ZORUNLU ister: karnenin cozdugu yaricapi "
            "aynen geri verin, yoksa liste sayilan kumeden baska bir kumeyi "
            "gosterir (bkz. fonksiyon govdesi).")
    # `en_az` burada anlamsız (yarıçap sabit), ama `_dogrula` tek kapıdır ve
    # tolerans tavanını orada kontrol ettiriyoruz.
    _dogrula(oranlar, tolerans, 1, cizgi)
    _dogrula_tarih(tarih)
    if limit < 1 or limit > EN_COK_LISTE:
        raise ValueError(
            f"limit 1..{EN_COK_LISTE} arasinda olmali (verilen: {limit})")
    if atla < 0:
        raise ValueError(f"atla negatif olamaz (verilen: {atla})")

    hedef = implied_probs(oranlar, yontem)
    if len(hedef) != 3:
        raise ValueError("üç sembolün de oranı gerekli")

    yakinlar, evren_boyu, kullanilan, _, kesilen, _taban = _ara(
        hedef, tolerans, 1, lig, sezon, yontem, korpus, tarih, cizgi)

    dilim = yakinlar[atla:atla + limit]
    return {
        "oranlar": dict(oranlar),
        "arindirma": yontem,
        "hedef_olasilik": hedef,
        "tolerans": kullanilan,
        "cizgi": cizgi,
        "evren": evren_boyu,
        "evren_kesilen": kesilen,
        "as_of": tarih,
        "filtre": {"lig": lig, "sezon": sezon},
        # `n` SAYFANIN degil KUMENIN buyuklugu — arayuz "34 maçin 20'si"
        # diyebilsin diye. Sayfanin boyu `len(maclar)`.
        "n": len(yakinlar),
        "limit": limit,
        "atla": atla,
        "maclar": [_mac_satiri(d, r, yontem, cizgi) for d, r in dilim],
    }


def _mac_satiri(mesafe: float, r: dict[str, Any], yontem: str,
                cizgi: str) -> dict[str, Any]:
    """Korpus satırının dışarı verilen yüzü.

    Gönderilen fiyat **arananla aynı çizgidendir**: kapanış evreninde
    arayıp açılış oranı göstermek, listedeki maçın neden bulunduğunu
    okunamaz kılardı. `mesafe` de aynı sebeple taşınır — kullanıcı satırın
    hedefe ne kadar yakın olduğunu görmeden "benzer" kelimesini denetleyemez.
    """
    ham = _cizgi_orani(r, cizgi) or {}
    return {
        "tarih": r["tarih"],
        "lig": r["lig"],
        "lig_etiket": LIG_ADLARI.get(r["lig"], r["lig"]),
        "sezon": r["sezon"],
        "ev": r["ev"],
        "dep": r["dep"],
        "ev_gol": r["ev_gol"],
        "dep_gol": r["dep_gol"],
        "kod": r["kod"],
        "oranlar": dict(ham),
        "olasilik": implied_probs(ham, yontem) if ham else {},
        "mesafe": mesafe,
    }


# ─── yazdırma ─────────────────────────────────────────────────────────────────

def _karne_satirlari(karne: dict[str, Any], girinti: str = "") -> None:
    n = karne["n"]
    if not karne["yeterli"]:
        print(f"{girinti}n={n} — örneklem yetersiz, yüzde yazılmadı.")
        return
    for s in SEMBOLLER:
        r = karne["semboller"][s]
        isaret = "" if r["piyasa_ga_icinde"] else "   ← piyasa GA DIŞINDA"
        print(f"{girinti}'{s}'  {r['adet']:>4}/{n:<5} gerçek %{100*r['oran']:>5.1f} "
              f"[%{100*r['ga_alt']:>4.1f} – %{100*r['ga_ust']:>4.1f}]   "
              f"piyasa %{100*r['piyasa']:>5.1f}  fark {100*r['fark']:>+5.1f}{isaret}")


def yaz(rapor: dict[str, Any]) -> None:
    o = rapor["oranlar"]
    print("=" * 78)
    print("GEÇMİŞTE BU ORANDA NE OLDU?")
    print("=" * 78)
    print(f"Oran        : {o['1']} / {o['0']} / {o['2']}   (marj %{100*rapor['marj']:.1f})")
    h = rapor["hedef_olasilik"]
    print(f"Piyasa der  : %{100*h['1']:.1f} / %{100*h['0']:.1f} / %{100*h['2']:.1f}"
          f"   (arındırma: {rapor['arindirma']})")
    f = rapor["filtre"]
    kapsam = ", ".join(x for x in (f["lig"], f["sezon"]) if x) or "tüm korpus"
    if rapor["as_of"]:
        kapsam += f" · {rapor['as_of']} öncesi ({rapor['evren_kesilen']:,} maç kesildi)"
    print(f"Çizgi       : {rapor['cizgi']}"
          f"{'  (korpusun birincil fiyatı)' if rapor['cizgi'] == 'kapanis' else ''}")
    print(f"Arama       : {kapsam} · {rapor['evren']:,} maç içinde, "
          f"olasılık uzayında ±{100*rapor['tolerans']:.1f} puan"
          f"{' (uyarlandı)' if rapor['tolerans_uyarlandi'] else ''}")
    print()
    print(f"─── BULUNAN {rapor['toplam']['n']} MAÇ " + "─" * 45)
    m = rapor["mesafe"]
    if m:
        # Yarıçap genişlediyse asıl okunacak satır bu: ortanca tavana
        # dayanmışsa örneklem sınırdan toplanmış demektir.
        print(f"  mesafe: en yakın %{100*m['en_yakin']:.2f} · ortanca "
              f"%{100*m['ortanca']:.2f} · ortalama %{100*m['ortalama']:.2f} · "
              f"en uzak %{100*m['en_uzak']:.2f} puan")
    _karne_satirlari(rapor["toplam"], "  ")

    for ad, baslik in (("lig", "LİG"), ("sezon", "SEZON")):
        dilimler = [d for d in rapor["dilimler"][ad] if d["karne"]["yeterli"]]
        atlanan = len(rapor["dilimler"][ad]) - len(dilimler)
        if not dilimler:
            continue
        print(f"\n─── {baslik} KIRILIMI " + "─" * 50)
        for d in dilimler:
            k = d["karne"]
            hucre = "  ".join(
                f"{s}:%{100*k['semboller'][s]['oran']:.0f}" for s in SEMBOLLER)
            print(f"  {d['etiket']:<28} n={k['n']:<5} {hucre}")
        if atlanan:
            print(f"  ({atlanan} dilim {AZ_ORNEK} maçın altında olduğu için yazılmadı)")

    if rapor["uyarilar"]:
        print("\n─── UYARILAR " + "─" * 58)
        for u in rapor["uyarilar"]:
            print(f"  • {u}")


def yaz_maclar(liste: dict[str, Any]) -> None:
    """Maç listesini konsola basar — karnenin arkasındaki kayıtlar."""
    n, gosterilen = liste["n"], len(liste["maclar"])
    f = liste["filtre"]
    kapsam = ", ".join(x for x in (f["lig"], f["sezon"]) if x) or "tüm korpus"
    print(f"\n─── MAÇLAR ({kapsam}) " + "─" * 45)
    print(f"  {n} maçın {gosterilen}'i · ±{100*liste['tolerans']:.1f} puan "
          f"· {liste['cizgi']} çizgisi")
    if not liste["maclar"]:
        print("  (yok)")
        return
    print(f"  {'tarih':<11} {'lig':<5} {'ev — dep':<44} {'skor':>5} "
          f"{'sonuç':>5}  {'oran (1/0/2)':<20} uzaklık")
    for m in liste["maclar"]:
        o = m["oranlar"]
        es = f"{m['ev']} — {m['dep']}"
        skor = (f"{m['ev_gol']}-{m['dep_gol']}"
                if m["ev_gol"] is not None else "?")
        oran = f"{o.get('1', 0):.2f}/{o.get('0', 0):.2f}/{o.get('2', 0):.2f}"
        print(f"  {m['tarih']:<11} {m['lig']:<5} {es[:44]:<44} {skor:>5} "
              f"{m['kod']:>5}  {oran:<20} %{100*m['mesafe']:.2f}")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Bir orana benzeyen geçmiş maçların nasıl sonuçlandığı.")
    ap.add_argument("--oran", required=True,
                    help="1,0,2 sırasıyla virgüllü: 1.82,3.04,2.44")
    ap.add_argument("--tolerans", type=float, default=None,
                    help="olasılık puanı cinsinden yarıçap (ör. 0.02); "
                         "verilmezse örnekleme göre uyarlanır")
    ap.add_argument("--en-az", type=int, default=HEDEF_ORNEKLEM,
                    help="uyarlanan aramanın hedeflediği en az maç")
    ap.add_argument("--lig", default=None)
    ap.add_argument("--sezon", default=None)
    ap.add_argument("--tarih", default=None,
                    help="YYYY-MM-DD; yalnızca bu günden ÖNCEKİ maçlar "
                         "aranır (kronolojik sorgu)")
    ap.add_argument("--arindirma", default=ARINDIRMA_VARSAYILAN,
                    choices=("orantili", "guc", "shin"))
    ap.add_argument("--cizgi", default="kapanis", choices=CIZGILER,
                    help="hangi fiyat çizgisinde aranacak "
                         "(varsayılan: korpusun birincil fiyatı = kapanış)")
    ap.add_argument("--maclar", type=int, default=0, metavar="N",
                    help="karnenin arkasındaki ilk N maçı da yaz "
                         "(karnenin ÇÖZDÜĞÜ yarıçapla, ayrı bir aramayla "
                         "değil)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        parcalar = [float(x) for x in a.oran.split(",")]
    except ValueError:
        # `from None`: bu bir KULLANIM hatasi, ic float() izlemesi
        # kullaniciya bir sey soylemez.
        raise SystemExit("--oran üç sayı olmalı: 1.82,3.04,2.44") from None
    if len(parcalar) != 3:
        raise SystemExit("--oran üç sayı olmalı: 1.82,3.04,2.44")

    try:
        rapor = benzer_maclar(
            {"1": parcalar[0], "0": parcalar[1], "2": parcalar[2]},
            tolerans=a.tolerans, en_az=a.en_az, lig=a.lig,
            sezon=a.sezon, yontem=a.arindirma, tarih=a.tarih,
            cizgi=a.cizgi)
        # Liste, karnenin COZDUGU yaricapi alir. Kendi yaricapini
        # uyarlasaydi lig suzgecli cagrida karneden BASKA bir kume sayardi
        # (gerekce `benzer_mac_listesi` govdesinde).
        liste = (benzer_mac_listesi(
            {"1": parcalar[0], "0": parcalar[1], "2": parcalar[2]},
            tolerans=rapor["tolerans"], lig=a.lig, sezon=a.sezon,
            yontem=a.arindirma, tarih=a.tarih, cizgi=a.cizgi,
            limit=a.maclar) if a.maclar else None)
    except ValueError as e:
        # CLI kendi kuralını YAZMAZ. Doğrulama tek yerde (`_dogrula`) ve
        # burası onun cümlesini olduğu gibi iletir; ikinci bir kopya iki
        # kapının zamanla ayrışması demekti.
        raise SystemExit(str(e)) from None
    if a.json:
        govde = dict(rapor)
        if liste is not None:
            govde["maclar"] = liste["maclar"]
        print(json.dumps(govde, ensure_ascii=False, indent=1))
    else:
        yaz(rapor)
        if liste is not None:
            yaz_maclar(liste)


if __name__ == "__main__":
    main()
