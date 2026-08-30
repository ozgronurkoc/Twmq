"""Benzer maç arama — "bu oranda geçmişte ne olmuş?"

Bir maçın oranını alır, 31 bin maçlık eğitim korpusunda **aynı fiyata sahip**
maçları bulur ve nasıl sonuçlandıklarını sayar:

    python -m spor_toto.benzer --oran 1.82,3.04,2.44

Bu modül tahmin üretmez. Ürettiği tek şey ampirik bir cevaptır: *piyasa bu
fiyatı verdiğinde geçmişte ne oldu.* Asıl sorduğu soru "yüzde kaçı ev sahibi
kazanmış" değil, **"piyasa sözünü tutmuş mu"** — bu yüzden her satırda
piyasanın kendi dediği yüzde de yazar.

─── Neden oran uzayında arama YAPILMAZ ────────────────────────────────────────

En önemli tasarım kararı bu. Aynı gerçek olasılık, farklı marjda tamamen
farklı oran verir: %18 marjlı bir iddaa bülteninde 1.82 ne diyorsa, %7 marjlı
football-data arşivinde başka bir sayı onu der. Ölçüldü — 1.82/3.04/2.44
(marj %28,8) korpusta:

    birebir aynı oran ..............   0 maç
    oran ±%2 .......................   0 maç
    oran ±%10 ......................   0 maç
    olasılık ±2 puan ................ 709 maç

Yani oran uzayında arama sessizce "sonuç yok" der. Eşleme **marj
arındırıldıktan sonra olasılık uzayında** yapılır; `tests/test_benzer.py`
bunu regresyon testine bağlar.

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

Korpusun birincil fiyatı 31.103 satırın **hepsinde kapanış** ortalamasıdır
(`oran_kaynak = AvgC`). Yani bu modül bugün "kapanış çizgisinde bu fiyatı
gören maçlar" sorusuna cevap veriyor; açılış çizgisi korpusta ayrıca duruyor
ama burada kullanılmıyor.
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from .egitim import korpus_yukle
from .odds import ARINDIRMA_VARSAYILAN, AZ_ORNEK, SEMBOLLER, implied_probs, margin
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


def _dogrula(oranlar: dict[str, float], tolerans: float | None,
             en_az: int) -> None:
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


@lru_cache(maxsize=8)
def _olasilik_tablosu(yontem: str, korpus: str | None
                      ) -> tuple[tuple[dict[str, float], dict[str, Any]], ...]:
    """Korpusun tamamının arındırılmış olasılıkları — yöntem başına bir kez.

    Bunsuz her sorgu 31 bin satırı yeniden arındırıyordu (~2 sn). Bir hafta
    sayfası 15 maç için 15 sorgu yapar; onbelleksiz yarım dakika sürerdi.
    Korpus sürümlenmiş bir dosyadır, aynı yöntem hep aynı tabloyu verir.

    Dönen yapı **okunmak içindir**; çağıran taraf satırları değiştirmemeli
    (onbellekteki nesnenin ta kendisidir).
    """
    return tuple((p, r) for p, r in
                 ((implied_probs(r["oranlar"], yontem), r)
                  for r in korpus_yukle(korpus))
                 if len(p) == 3)


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


def benzer_maclar(oranlar: dict[str, float],
                  tolerans: float | None = None,
                  en_az: int = HEDEF_ORNEKLEM,
                  lig: str | None = None,
                  sezon: str | None = None,
                  yontem: str = ARINDIRMA_VARSAYILAN,
                  korpus: str | None = None,
                  tarih: str | None = None) -> dict[str, Any]:
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
    """
    _dogrula(oranlar, tolerans, en_az)
    _dogrula_tarih(tarih)
    hedef = implied_probs(oranlar, yontem)
    if len(hedef) != 3:
        # `_dogrula`dan sonra bu artık gerçekten "arındırma üç sembol
        # üretemedi" demek: `nan`/`inf` bir üst kapıda adıyla düşüyor.
        raise ValueError("üç sembolün de oranı gerekli")

    dilim = [(p, r) for p, r in _olasilik_tablosu(yontem, korpus)
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
        "evren": len(olculu),
        "as_of": tarih,
        "evren_kesilen": kesilen,
        "filtre": {"lig": lig, "sezon": sezon},
        "mesafe": _mesafe_ozeti([d for d, _ in yakinlar]),
        "toplam": _sayim(bulunan, hedef),
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


def _dilimle(maclar: Sequence[dict[str, Any]], hedef: dict[str, float],
             alan: str) -> list[dict[str, Any]]:
    """Bulunan maçları bir alana göre böler; her dilim kendi n'i ve GA'sıyla."""
    gruplar: dict[str, list[dict[str, Any]]] = {}
    for m in maclar:
        gruplar.setdefault(m[alan], []).append(m)
    out = [{"deger": k, "karne": _sayim(v, hedef)}
           for k, v in gruplar.items()]
    out.sort(key=lambda d: -d["karne"]["n"])
    return out


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
            print(f"  {d['deger']:<8} n={k['n']:<5} {hucre}")
        if atlanan:
            print(f"  ({atlanan} dilim {AZ_ORNEK} maçın altında olduğu için yazılmadı)")

    if rapor["uyarilar"]:
        print("\n─── UYARILAR " + "─" * 58)
        for u in rapor["uyarilar"]:
            print(f"  • {u}")


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
            sezon=a.sezon, yontem=a.arindirma, tarih=a.tarih)
    except ValueError as e:
        # CLI kendi kuralını YAZMAZ. Doğrulama tek yerde (`_dogrula`) ve
        # burası onun cümlesini olduğu gibi iletir; ikinci bir kopya iki
        # kapının zamanla ayrışması demekti.
        raise SystemExit(str(e)) from None
    if a.json:
        print(json.dumps(rapor, ensure_ascii=False, indent=1))
    else:
        yaz(rapor)


if __name__ == "__main__":
    main()
