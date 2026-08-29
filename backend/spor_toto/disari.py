"""Piyasa dışı ama türetilebilir özellikler (A3) — Faz A'nın son işi.

Yol haritası §6.2 A3 altı özellik listeledi. **İlk iş listeyi denetlemekti** ve
ikisi elendi — korpusta türetilecek şey yok:

    seyahat   Şehir/koordinat yok. Ayrıca bir maçın iki takımı **her zaman
              aynı ligde** (`Div` sütunu tek); "deplasman takımının lig/ülke
              değişimi" maç düzeyinde bir büyüklük değil.
    derbi     Şehir eşlemesi ya da rekabet tablosu yok. Elle bir derbi listesi
              yazmak *türetme* değil **küratörlük** olurdu ve keyfî olurdu.

İkisi de yeni bir **veri kaynağı** ister; dolayısıyla A4(b)'nin "tekrar
açılması için yeni bir veri kaynağı gerekir" şartına aittirler, A3'e değil.
Bunu yazmak, denemiş gibi yapıp sessizce atlamaktan iyidir.

Kalan dördü gerçekten türetilebilir ve `egitim._takvim_tablosu` üretir:

    dinlenme     önceki maçtan geçen gün (ev − dep)
    sikisiklik   son 14 günde oynanan maç (dep − ev; ev lehine pozitif)
    ic_dis       ev takımının İÇ saha formu − dep takımının DIŞ saha formu
    sezon_sonu   sezonun son %20'sinde, sıralamanın uçlarına yakınlık payı

**Korpusun bir kör noktası var ve A3'ün cevabını sınırlıyor.** Korpus 22 lig
taşıyor; kupa ve Avrupa maçları içinde yok. Dinlenme olduğundan uzun,
sıkışıklık olduğundan düşük ölçülür — ve hata rastgele değil, **Avrupa oynayan
takımlarda** yoğunlaşır. Bu yüzden sonuç *"yorgunluk fiyatlanmış"* diye değil,
*"korpustan türetilebilen yorgunluk vekili fiyatlanmış"* diye yazılır.

**A2'nin dersi buraya taşındı.** A2'de ham bir tablo, favori gücüyle karışıp
gerçek sinyal taklidi yapmıştı. A3'ün dört özelliği de aynı riski taşıyor:
dinlenme ve sıkışıklık takım gücüyle karışık (Avrupa oynayan takımlar hem
yorgun hem güçlü), iç/dış form doğrudan güç ölçüsü. Bu yüzden betimleyici
tablo ham farkı değil **artığı** raporlar: gerçekleşen oran eksi *piyasanın
kendi beklediği* oran. Piyasa özelliği zaten fiyatlamışsa artık sıfıra düşer.

Sonucu okumak için: `python -m spor_toto.disari`.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .egitim import korpus_haftalari
from .ortak import FAVORI_DILIMLERI, favori_dilimi
from .predict import Girdi, PiyasaTahminci
from .recalibrate import A3_ALANLARI

#: Listeden elenen özellikler ve gerekçeleri. Kodda durur çünkü "denenmedi"
#: ile "denenemez" farklı şeylerdir ve A4 bu ayrımı yazmak zorunda.
TURETILEMEYEN: dict[str, str] = {
    # Liste Faz 3.4'te KISALDI: `derbi` cikti, `seyahat` kaldi ve
    # gerekcesi degisti — artik "sehir yok" degil, "KOORDINAT yok".
    "seyahat": ("sehir var (`sehir.py`, %98,0) ama KOORDINAT yok; iki "
                "sehrin arasindaki mesafe sehir adindan cikmaz"),
    # Gerekce DEGISTI ve girdi yerinde kaldi. Onceki gerekce erisim
    # hakkindaydi: "Understat robots.txt'i `Disallow: /` diyor, fbref
    # Cloudflare arkasinda". O yari artik gecersiz — `hudl/open-data`
    # (eski adiyla `statsbomb/open-data`) olay duzeyi veriyi serbestce
    # yayimliyor ve her sutta `shot.statsbomb_xg` var.
    #
    # Ama ikinci yari AYAKTA ve tek basina yetiyor. Depo lig-sezon
    # lig-sezon sayildi: Super Lig YOK, alt Ingiliz ligleri (E1/E2/E3/EC)
    # YOK. Korpus penceresiyle (2122-2425) kesisim 31.103 macta topu topu
    # 92 mac ve o 92'nin hepsi tek takima yanli (PSG'nin Ligue 1 maclari,
    # Leverkusen'in Bundesliga maclari). Ustelik canli akis yok: veri
    # maclardan yillar sonra yayimlaniyor, yani `/tahmin` onu ilkesel
    # olarak da goremezdi.
    #
    # Girdinin kalmasi onemli: kaynagin acilmasi SORUNUN cozulmesi
    # demek degildi ve bu ayrimi yazmak, "artik var" deyip kapsamayi
    # sessizce gormezden gelmekten iyidir. Acilan sey ayri bir
    # anahtarla asagida: `xg_vekili`.
    "xg": ("kaynak ARTIK ACIK (`hudl/open-data`, her sutta "
           "`shot.statsbomb_xg`) ama kapsamiyor: Super Lig ve alt Ingiliz "
           "ligleri depoda yok, korpus penceresiyle kesisim 92 mac ve hepsi "
           "tek takima yanli. Canli akis da yok — veri maclardan yillar "
           "sonra yayimlaniyor, yani ileriye donuk kullanilamaz"),
    "kadro_sakatlik": (
        "kaynak teknik olarak acik (transfermarkt `Allow: /`) ama ozellik "
        "ILERIYE DONUK KULLANILAMAZ: gercek kadro ancak ilk vurusta bellidir. "
        "Korpusta kullanip `/tahmin`de kullanamamak egitim/servis ayrismasidir "
        "ve olcumu anlamsiz kilar. Gereken sey MAC ONCESI haber akisinin "
        "tarihsel anlik goruntuleridir; arsivde yok ve geriye donuk "
        "kurulamaz"),
}

#: Faz 3.4'te turetilebilir hale gelenler — liste bir kez kisaldi ve
#: nedeni kayda gecti. Yeni bir model degil, YENI VERI acti.
TURETILEBILIR_OLDU: dict[str, str] = {
    "derbi": ("`openfootball/clubs` (CC0) kulup-sehir tablosu veriyor; elle "
              "liste yazmak kuratorluk olurdu ama KAYNAKTAN sehir okumak "
              "turetmedir — `scripts/build_sehir.py`, 592/604 takim"),
    "avrupa": ("`openfootball/champions-league` (kamu mali) UEFA fiksturu "
               "veriyor; `dinlenme` ve `sikisiklik` artik o gunleri de "
               "goruyor — `scripts/build_avrupa.py`, ad eslemesi %100"),
    # xG'nin KENDISI degil, korpusun kendi sut sayiminin KALIBRASYONU.
    # Ayrim onemli: `xg` yukarida kapali kaldi cunku StatsBomb korpusun
    # liglerini kapsamiyor. Kapsamadigi icin bir GIRDI olamaz — ama
    # kapsadigi 1.517 macta gercek xG ile korpusun `sut`/`isabet`
    # sayimlarini YAN YANA gordugu icin bir REFERANS olabilir. Vekil o
    # kesitte uydurulur, korpusun tamamina uygulanir ve StatsBomb verisi
    # depoya hic girmez (lisans md. 1.2.1).
    "xg_vekili": ("`hudl/open-data`in 2015/16 dort lig kesiti (PL, La Liga, "
                  "Serie A, Ligue 1; 1.517 mac) gercek xG'yi football-data "
                  "sut sayimiyla ayni macta veriyor; `ev_sut`/`ev_isabet` "
                  "artik KEYFI degil OLCULMUS katsayilarla beklenen gole "
                  "ceviriliyor — `scripts/build_xg.py`, `spor_toto/xg.py`"),
}

#: Ham sinyal taramasında bir özelliğin "yüksek"/"düşük" sayıldığı eşik.
#: Her özelliğin kendi ölçeğine göre, **ölçüm sonucuna bakılmadan** seçildi.
#:
#: `sikisiklik_farki` tam sayıdır (maç adedi farkı) ve eşiği 0,5 — yani "en az
#: bir maç fark". 1,0 denenmişti; kuyruklarda 300 maç kalıyor ve favori
#: dilimlerine bölününce hücreler 30–130'a düşüp taramayı okunamaz hale
#: getiriyordu. Eşik gevşetildi çünkü **hücre boş kalırsa tarama sessizce
#: cevapsız kalır** — ve cevapsızlığın "artık yok" diye okunması A3'ün en
#: kolay yapılacak hatası olurdu.
TARAMA_ESIKLERI: dict[str, float] = {
    "dinlenme_farki": 2.0,
    "sikisiklik_farki": 0.5,
    # `avrupa_farki` de tam sayidir (pencere icindeki UEFA maci farki) ve
    # esigi ayni gerekcelerle 0,5: "en az bir mac fark". Faz 3.4.
    "avrupa_farki": 0.5,
    "ic_dis_form_farki": 1.0,
    "sezon_sonu_pay_farki": 0.3,
}

#: Bir hücrenin raporlanması için gereken en az maç.
AZ_HUCRE = 150


def kesit(sezonlar_: Sequence[str] | None = None,
          yol: str | None = None) -> list[Girdi]:
    """A3 kesiti — korpusun tamamı.

    A1 ve A2'den farklı olarak burada **eleme yok**: dört özellik de her maç
    için tanımlı (yeterli geçmişi olmayan maçta nötr 0'a düşer ve bir bayrakla
    işaretlenir). Eleseydik kesit, "yeterli geçmişi olan maçlar" diye sessizce
    sezon başlarını atardı ve kesitin kendisi bir seçim taşırdı.
    """
    return korpus_haftalari(sezonlar_=sezonlar_, yol=yol)


#: `bahisci` ile birebir ayniydi; tek kaynak artik `ortak`.
_favori_dilimi = favori_dilimi


def artik_taramasi(haftalar: Sequence[Girdi] | None = None) -> dict[str, Any]:
    """Her özellik için: piyasanın **fiyatlamadığı** bir şey kalıyor mu?

    Ham fark yerine **artık** raporlanır ve fark budur:

        ham fark  = gerçekleşen ev oranı(yüksek) − gerçekleşen ev oranı(düşük)
        piyasa    = piyasanın beklediği ev oranı(yüksek) − ...(düşük)
        **artık** = ham fark − piyasa

    Ham fark, özelliğin bilgi taşıyıp taşımadığını söyler; artık, o bilginin
    **fiyata girmemiş** kısmını. A3'ün sorusu ikincisidir. `ic_dis_form_farki`
    bunu en açık gösterir: ham farkı devasa (+0,247) ama artığı sıfıra yakın —
    özellik güçlü, katkısı yok.

    Karışmaya karşı favori gücü dilimlenir (A2'nin dersi): bir özellik
    yalnızca "güçlü takım" demenin başka bir yolu olabilir ve o zaman ham
    fark özelliğin değil gücün olur.

    Bu bir **tarama**, karar değil. Karar `rapor()`un güven aralığındadır;
    buradaki hücreler 150–800 maçlık ve tek başlarına gürültülü.
    """
    if haftalar is None:
        haftalar = kesit()

    veri = [(hf["ozellikler"][i], hf["probs"][i], kod)
            for hf in haftalar for i, kod in enumerate(hf["results"])]

    out: dict[str, Any] = {}
    for _, alan in A3_ALANLARI:
        esik = TARAMA_ESIKLERI[alan]
        dusuk = [g for g in veri if g[0].get(alan, 0.0) < -esik]
        yuksek = [g for g in veri if g[0].get(alan, 0.0) > esik]

        def _ev(grup: Sequence[Any]) -> float | None:
            return sum(1 for _, _, k in grup if k == "1") / len(grup) if grup else None

        def _piyasa(grup: Sequence[Any]) -> float | None:
            return sum(p["1"] for _, p, _ in grup) / len(grup) if grup else None

        dilimler: dict[str, dict[str, Any]] = {}
        for dilim in [f"<{e:.2f}" for e in FAVORI_DILIMLERI] + \
                     [f">={FAVORI_DILIMLERI[-1]:.2f}"]:
            d = [g for g in dusuk if _favori_dilimi(g[1]) == dilim]
            y = [g for g in yuksek if _favori_dilimi(g[1]) == dilim]
            if len(d) < AZ_HUCRE or len(y) < AZ_HUCRE:
                continue
            gercek = _ev(y) - _ev(d)
            beklenen = _piyasa(y) - _piyasa(d)
            dilimler[dilim] = {
                "n_dusuk": len(d), "n_yuksek": len(y),
                "gercek_fark": round(gercek, 4),
                "piyasa_farki": round(beklenen, 4),
                "artik": round(gercek - beklenen, 4),
            }

        ham = (round(_ev(yuksek) - _ev(dusuk), 4)
               if dusuk and yuksek else None)
        out[alan] = {
            "esik": esik,
            "n_dusuk": len(dusuk), "n_yuksek": len(yuksek),
            "ham_fark": ham,
            "dilimler": dilimler,
            # Hicbir dilim esigi gecmediyse tarama CEVAPSIZ kalmistir; bunu
            # "artik yok" diye okumak A3'un en kolay yapilacak hatasi olurdu.
            # Bayrak acikca tasinir ve `_yazdir` onu yazar.
            "dilimlenemedi": not dilimler,
            "en_buyuk_artik": (max((abs(d["artik"]) for d in dilimler.values()),
                                   default=None)),
        }
    return out


#: Avrupa kupalarına takım veren ligler. Kör nokta taramasının ayırıcısı:
#: kupa/Avrupa maçları korpusta **görünmez**, dolayısıyla eksik ölçüm bu
#: liglerde yoğunlaşmalıdır. Liste kabadır ve sonuca bakılmadan yazıldı.
AVRUPA_LIGLERI: Sequence[str] = ("E0", "SP1", "D1", "I1", "F1", "N1", "P1",
                                 "T1", "B1", "G1", "SC0")


def kor_nokta_taramasi(haftalar: Sequence[Girdi] | None = None
                       ) -> dict[str, Any]:
    """Dinlenme özelliğinin kör noktası ölçülebiliyor mu — **iddia değil test.**

    Modül başlığı korpusun kupa ve Avrupa maçlarını görmediğini söylüyor.
    Bunu yazıp geçmek kolay olurdu; burada sınanıyor.

    Hipotez: korpusta "uzun dinlenme" görünen bir takım, aslında sık sık
    **görünmeyen bir maç** oynamıştır — yani dinlenmiş değil yorgundur.
    Doğruysa etki, Avrupa'ya takım veren liglerde belirgin biçimde daha güçlü
    olmalıdır; o ligler görünmeyen maçların gerçekten oynandığı yerlerdir.

    Ölçülen artık = gerçekleşen ev galibiyeti oranı − piyasanın beklediği.

    **Sonucun nasıl okunacağı önemli.** Bu bir tarama hücresidir: örneklem
    birkaç yüz maç, birden çok hücre arasından okunuyor ve dışarıda bırakmalı
    ölçümde katkısı sıfır. Yani bir *bulgu* değil, A4(b)'nin yeniden açılma
    koşulunu **somutlaştıran** bir işaret: eksik olan model değil, fikstür
    verisidir.
    """
    if haftalar is None:
        haftalar = kesit()
    avrupa = set(AVRUPA_LIGLERI)
    veri = [(hf["ozellikler"][i], hf["probs"][i], kod)
            for hf in haftalar for i, kod in enumerate(hf["results"])]

    def _artik(grup: Sequence[Any]) -> dict[str, Any] | None:
        if len(grup) < AZ_HUCRE:
            return None
        gercek = sum(1 for _, _, k in grup if k == "1") / len(grup)
        beklenen = sum(p["1"] for _, p, _ in grup) / len(grup)
        return {"n": len(grup), "artik": round(gercek - beklenen, 4)}

    kesimler = (
        ("ev_cok_dinlenmis", lambda o: o["dinlenme_farki"] > 2),
        ("dengeli", lambda o: abs(o["dinlenme_farki"]) <= 1),
        ("dep_cok_dinlenmis", lambda o: o["dinlenme_farki"] < -2),
    )
    out: dict[str, Any] = {}
    for katman, icinde in (("avrupa_ligi", True), ("diger_lig", False)):
        secim = [g for g in veri if (g[0]["lig"] in avrupa) is icinde]
        out[katman] = {ad: _artik([g for g in secim if kosul(g[0])])
                       for ad, kosul in kesimler}
    out["not"] = ("hipotez: korpusta 'uzun dinlenme', gorunmeyen bir kupa/"
                  "Avrupa maci demek olabilir. Dogruysa etki Avrupa liglerinde "
                  "daha guclu cikar. TARAMA hucresidir — disarida birakmali "
                  "olcumde katkisi sifir; A4(b)'nin yeniden acilma kosulunu "
                  "somutlastirir, bulgu degildir")
    return out


def kapsama(haftalar: Sequence[Girdi] | None = None) -> dict[str, Any]:
    """Özelliklerin kaç maçta gerçekten tanımlı olduğu.

    Yeterli geçmişi olmayan maçta özellik nötr 0'a düşer (doktrin 2: uydurma
    yok, "bilgi yok" işareti). Kapsama düşükse basamağın sıfır çıkması
    özelliğin değil **örneklemin** sonucu olabilir; bu sayı olmadan bulgu
    okunamaz.
    """
    if haftalar is None:
        haftalar = kesit()
    ozellikler = [o for hf in haftalar for o in hf["ozellikler"]]
    n = len(ozellikler)
    return {
        "n_mac": n,
        "dinlenme_var": round(sum(1 for o in ozellikler
                                  if o.get("dinlenme_var")) / n, 4),
        "ic_dis_form_var": round(sum(1 for o in ozellikler
                                     if o.get("ic_dis_form_var")) / n, 4),
        "sezon_sonu": round(sum(1 for o in ozellikler
                                if o.get("sezon_sonu")) / n, 4),
        "not": ("`sikisiklik_farki` her macta tanimli (gecmisi olmayan takim "
                "icin 0 = 'son 14 gunde mac yok', uydurma degil olgu)"),
    }


def rapor(sezonlar_: Sequence[str] | None = None,
          yol: str | None = None) -> dict[str, Any]:
    """A3'ün dört özelliğini kademe üzerinde, sırayla ölç.

    Kademe **kümülatiftir**: her basamak bir öncekine yalnızca bir sütun
    ekler. Bir özelliğin katkısı ardışık iki basamağın farkıdır ve toplam
    katkı `kalibre_sezon_sonu` ile `kalibre_dagilim` arasındaki farktır —
    A3'ün asıl cevabı budur.

    `kalibre_dagilim` taban çizgisi olarak koşuma **bu yüzden** girer: A1 ve
    A2'nin bıraktığı en üst basamak odur ve A3 onun üstüne ne eklediğiyle
    ölçülür.

    Ölçüm **sezon dışarıda bırakmalıdır** (`evaluate.sezon_anahtari`).
    """
    from .evaluate import karsilastir, sezon_anahtari
    from .recalibrate import KalibreTahminci

    haftalar = kesit(sezonlar_=sezonlar_, yol=yol)
    basamaklar = ["dagilim"] + [ad for ad, _ in A3_ALANLARI]
    fabrikalar = [PiyasaTahminci] + [
        (lambda k=k: KalibreTahminci(k)) for k in basamaklar]

    sonuc = karsilastir(fabrikalar, haftalar=haftalar, grup=sezon_anahtari)
    sonuc["kapsama"] = kapsama(haftalar)
    sonuc["artik"] = artik_taramasi(haftalar)
    sonuc["kor_nokta"] = kor_nokta_taramasi(haftalar)
    sonuc["turetilemeyen"] = TURETILEMEYEN
    sonuc["turetilebilir_oldu"] = TURETILEBILIR_OLDU
    sonuc["soru"] = (
        "piyasa disi turetilebilir bir ozellik piyasayi geciyor mu — "
        "`kalibre_sezon_sonu` (dordu birden) `kalibre_dagilim`i gecmiyorsa "
        "hayir, ve Faz A'nin son sorusu da kapanir")
    return sonuc


def _yazdir(sonuc: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    k = sonuc["kapsama"]
    print(f"A3 kesiti: {sonuc['n_hafta']} hafta · {sonuc['n_mac']} maç "
          f"· referans: {sonuc['referans']}")
    print(f"kapsama: dinlenme %{100 * k['dinlenme_var']:.1f} · "
          f"iç/dış form %{100 * k['ic_dis_form_var']:.1f} · "
          f"sezon sonu %{100 * k['sezon_sonu']:.1f}")

    print(f"\n{'tahminci':<22} {'brier':>8} {'log':>8} {'fark':>9} "
          f"{'%95 aralık':>18}  geçti")
    for s in sonuc["tahminciler"]:
        f = s["fark"]
        aralik = f"[{f['alt']:+.4f}, {f['ust']:+.4f}]" if f else ""
        fark = f"{f['fark']:+.4f}" if f else ""
        gecti = "" if s["gecti"] is None else ("EVET" if s["gecti"] else "hayir")
        print(f"{s['ad']:<22} {s['brier']:>8.4f} {s['log_kaybi']:>8.4f} "
              f"{fark:>9} {aralik:>18}  {gecti}")

    print("\nartık taraması — ham fark, piyasanın beklediği, aradaki artık:")
    for alan, blok in sonuc["artik"].items():
        print(f"\n  {alan} (eşik ±{blok['esik']}, ham fark {blok['ham_fark']:+.3f})")
        if blok["dilimlenemedi"]:
            print("  hiçbir dilim eşiği geçmedi — tarama CEVAPSIZ, "
                  "'artık yok' diye okunamaz")
            continue
        print(f"  {'p_favori':<10} {'gerçek':>9} {'piyasa':>9} {'ARTIK':>9}"
              f" {'n':>12}")
        for dilim, d in blok["dilimler"].items():
            sayilar = f"{d['n_dusuk']}/{d['n_yuksek']}"
            print(f"  {dilim:<10} {d['gercek_fark']:>+9.3f} "
                  f"{d['piyasa_farki']:>+9.3f} {d['artik']:>+9.3f} "
                  f"{sayilar:>12}")

    kn = sonuc["kor_nokta"]
    print("\nkör nokta taraması — korpus kupa/Avrupa maçlarını görmüyor:")
    print(f"  {'katman':<14} {'ev dinlenmiş':>18} {'dengeli':>18} "
          f"{'dep dinlenmiş':>18}")
    for katman in ("avrupa_ligi", "diger_lig"):
        hucreler = []
        for ad in ("ev_cok_dinlenmis", "dengeli", "dep_cok_dinlenmis"):
            h = kn[katman][ad]
            hucreler.append(f"{h['artik']:+.4f} (n={h['n']})" if h else "—")
        print(f"  {katman:<14}" + "".join(f"{m:>18}" for m in hucreler))

    print("\ntüretilebilir OLDU (Faz 3.4 — yeni veri geldi):")
    for ad, gerekce in sonuc.get("turetilebilir_oldu", {}).items():
        print(f"  {ad}: {gerekce}")

    print("\ntüretilemeyen (yeni veri kaynağı ister):")
    for ad, gerekce in sonuc["turetilemeyen"].items():
        print(f"  {ad}: {gerekce}")


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse
    import json

    from .kosum import belki_kaydet, cli_ekle

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    cli_ekle(ap)
    a = ap.parse_args(argv)

    s = rapor()
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1, default=str))
    else:
        _yazdir(s)
    belki_kaydet("disari", s, a)


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    main()
