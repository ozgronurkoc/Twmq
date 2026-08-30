"""Model Arena — bütün tahminci aileleri **tek kesitte, tek tabloda**.

Bu modül yeni bir model getirmez. Getirdiği şey bir **karşılaştırma
zemini**dir ve eksikliği dıştan yapılan bir incelemede tespit edildi
(`docs/DIS_INCELEME_AZ_RAPORU.md` §3): depoda on bir ölçüm koşumu var,
her biri kendi modülünde kendi tablosunu yazıyor —

    cizgi.rapor()        kalibrasyon.rapor()   bahisci.rapor()
    disari.rapor()       recalibrate.rapor()   agac.rapor()
    yigin.rapor()        kalibre.rapor()       beraberlik.rapor()

— ve bu tabloların sayıları **doğrudan kıyaslanamaz.** Kesitleri farklı
(`cizgi` açılış+kapanış çifti ister, `bahisci` bahisçi dörtlüsü),
gruplamaları farklı, hatta bir kısmı farklı marj arındırma çevriminde
ölçüldü (§3.18'in ölçek uyarısı tam olarak bunun izidir). Yani "Elo geçmedi"
ile "Dixon-Coles geçmedi" cümleleri aynı cinsten iki cümle değildi.

Arena'nın tek işi bunu düzeltmek:

    Aynı haftalar · aynı gruplama · aynı bootstrap tohumu · aynı referans

─── Aile başına TEK temsilci — ve kural sonuca bakmadan yazıldı ──────────

Arena bir liste değil, bir **kayıttır**: her model ailesinden bir temsilci
girer. Kademenin on dokuz basamağını tabloya dökmek arenayı
`recalibrate.rapor()`un kopyası yapardı; daha kötüsü, on dokuz adayın en
iyisine bakıp "aile geçti" demek çoklu test problemidir (§8'in kendi
uyarısı).

Temsilci seçme kuralı **ölçüm görülmeden** yazıldı ve her aile için tek
cümledir:

    kademe        `KADEMELER[-1]` — kademe KÜMÜLATİF (her basamak bir
                  öncekine bir özellik ekler), yani son basamak ailenin
                  kendisidir. "En iyi basamak" DEĞİL.
    ağaç          `piyasadan_basla=True` — modülün varsayılanı.
    beraberlik    `egimli=True` — modülün varsayılanı (Ö3'ün asıl iddiası).
    ötekiler      tek temsilcileri zaten var.

Aynı ailenin ikinci temsilcisi (`agac_ham`, `beraberlik_sabit`, ara
kademeler) arenaya girmez ve `disarida()` bunu **adıyla ve gerekçesiyle**
yazar. Sessizce düşen bir aday, olmayan bir kapsama ima etmek olurdu.

─── Kesit kuralı — modülün asıl tasarım kısıtı ───────────────────────────

`evaluate.bootstrap_farki` **eşleştirilmiş** çalışır ve aday ile referans
aynı haftalarda ölçülmezse hata fırlatır. Bu bir uygulama ayrıntısı değil,
arenanın varlık sebebidir: kesit tahminci başına daralırsa tablo yine
kıyaslanamaz olur.

Bu yüzden daha dar bir kesit isteyen üç aile arenaya **giremez** ve
`disarida()` üçünü de gerekçesiyle listeler:

    acilis / kapanis   açılış+kapanış çifti gerekli (§3.14, `cizgi.py`)
    bahisci_*          bahisçi dörtlüsü gerekli (§3.15, `bahisci.py`)
    elo                1X2 vermez, beklenen skor verir (§3.27, `gorus.py`)

Üçü de kendi modülünde `predict.referans_fabrikalar`a girmediğini zaten
yazıyor; arena o kararı tekrar etmiyor, görünür kılıyor.

─── Ne YOK, ve niçin yok ─────────────────────────────────────────────────

Dış inceleme tabloda `ROI` ve `Max Drawdown` sütunları da istedi. Konmadı:
`getiri.py` o hesabı kapalı formda veriyor (§3.34) ama havuz ekseninde
elde 3 haftalık ikramiye kaydı var ve §6.3b ölçülmüş biçimde yazıyor —
orta büyüklükte bir etkiyi ayırt etmek ≈71 ikramiyeli hafta ister. Boş bir
`ROI` sütunu, ölçülmemiş bir sayıya tabloda yer ayırmak olurdu.

Bu gerekçe **havuz ekseni içindir ve orada aynen durur.** Sabit oranlı
yan pazarlarda geçerli değil — orada fiyat sabittir ve getiri doğrudan
hesaplanır. O ölçüm `deger.py`de yapıldı (§3.36) ve arenaya yine
girmiyor, ama artık *"ölçülmedi"* diye değil *"başka bir kesitte, başka
bir birimde ölçüldü"* diye: `deger.py`nin kesiti oran arşividir (1.737
maç), arenanınki kupon haftalarıdır (114 hafta) ve birimi Brier'dir.
İkisini aynı tabloya koymak arenanın kendi kesit kuralını bozardı.

    python -m spor_toto.arena              # sezon disarida birakmali
    python -m spor_toto.arena --ileri      # kronolojik (ileri yuruyus)
    python -m spor_toto.arena --kupon      # kupon setinde
    python -m spor_toto.arena --json --kosum
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from .evaluate import (
    Fabrika,
    Girdi,
    karsilastir,
    kupon_kesiti_tum,
    sezon_anahtari,
)
from .predict import REFERANS_AD, referans_fabrikalar

#: Kupon setinin egitim korpusuyla ORTAK mac sayisi — olculdu, varsayilmadi.
#:
#: §6G kupon setini dort sezona cikardi ve uc sezonu korpusla cakisiyor:
#: 2022/23 %100, 2023/24 %100, 2024/25 %97, 2025/26 %0 — toplam 1.680 macin
#: 1.200'u (%71) korpusta BIREBIR var. Bu yuzden korpusta egitilmis bir
#: tahminci bu haftalarda `grup=None` ile olculemez.
#:
#: Sayilar §6H'de buyudu (107 -> 112 hafta, eslestirmedeki Unicode kusuru
#: duzeltilince) ve burada ELLE guncellendi. Oran degismedi: %72 -> %71.
KUPON_KORPUS_KESISIMI = (
    "kupon maclarinin 1.200/1.680'i (%71) egitim korpusunda da var "
    "(2022/23, 2023/24, 2024/25). Korpusta egitilen bir tahminci bu "
    "kesitte grup=sezon_anahtari OLMADAN olculemez."
)
#: Arenanın kayıt satırı: (aile, fabrika).
#: `aile` tabloda okunmaz — `Tahminci.ad` okunur — ama kayıt hangi ailenin
#: hangi temsilciyle girdiğini taşımak zorundadır, yoksa "aile başına tek
#: temsilci" kuralı denetlenemez.
KayitSatiri = tuple[str, Fabrika]


def _kademe_temsilcisi() -> Fabrika:
    """Kademenin SON basamağı — kademe kümülatiftir, bkz. modül başlığı."""
    from .recalibrate import KADEMELER, KalibreTahminci

    son = KADEMELER[-1]
    return lambda: KalibreTahminci(son)


def roster() -> list[KayitSatiri]:
    """Arenaya giren aileler ve temsilcileri, **kesin sırayla**.

    Sıra zeminden çizgiye, çizgiden adaylara doğrudur ve tabloda korunmaz
    (tablo Brier'e göre sıralanır) — ama kaydın kendisi kararlıdır, çünkü
    `test_sizinti.py` bu liste üzerinde döner.

    `lightgbm` kurulu değilse ağaç ailesi **atlanır, uydurulmaz**:
    `agac.HAS_LIGHTGBM` deseninin (`core.HAS_SCIPY`) arena karşılığı. Üretim
    o paketi taşımaz (`scripts/run_prod.sh`), CI taşır.
    """
    from .beraberlik import BeraberlikTahminci
    from .dixon_coles import DcTahminci
    from .kalibre import VennAbersTahminci
    from .recalibrate import IzotonikTahminci
    from .yigin import YiginTahminci

    duzgun, sezon_sabiti, piyasa = referans_fabrikalar()
    kayit: list[KayitSatiri] = [
        ("zemin", duzgun),
        ("naif", sezon_sabiti),
        ("piyasa", piyasa),
        ("kademe", _kademe_temsilcisi()),
        ("izotonik", IzotonikTahminci),
        ("dixon_coles", DcTahminci),
        ("beraberlik", BeraberlikTahminci),
        ("venn_abers", VennAbersTahminci),
    ]

    from .agac import HAS_LIGHTGBM

    if HAS_LIGHTGBM:
        from .agac import AgacTahminci

        kayit.append(("agac", AgacTahminci))

    # Yigin EN SONA: ust-ogrenicidir, tabanlarini kendisi kurar ve
    # kosumun en pahali uyesidir.
    kayit.append(("yigin", YiginTahminci))
    return kayit


#: Arenaya **girmeyen** aileler: ad → gerekçe. Sessizce düşmesin diye
#: kodda; `rapor()` bunu çıktıya taşır.
def disarida() -> dict[str, str]:
    """Arenaya girmeyenler ve niçin girmedikleri."""
    disi = {
        "acilis": ("dar kesit — acilis+kapanis cifti olmayan mac elenir "
                   "(§3.14, cizgi.py); ayni haftalarda olculmedigi icin "
                   "eslestirilmis bootstrap kurulamaz"),
        "bahisci_*": ("dar kesit — bahisci dortlusu tam olmayan mac elenir "
                      "(§3.15, bahisci.py)"),
        "elo": ("1X2 vermez, beklenen skor verir (0..1) ve bu bir olasilik "
                "degildir; Elo farkini 1X2'ye ceviren bir esleme uydurmak "
                "olculmemis bir model eklemek olurdu (§3.27, gorus.py)"),
        "agac_ham": "ayni ailenin ikinci temsilcisi — aile basina tek temsilci",
        "beraberlik_sabit": "ayni ailenin ikinci temsilcisi",
        "kalibre_* (ara basamaklar)": (
            "kademe kumulatif; ailenin temsilcisi son basamak. Basamak "
            "basamak tablo: recalibrate.rapor()"),
    }
    from .agac import HAS_LIGHTGBM

    if not HAS_LIGHTGBM:
        disi["agac"] = "lightgbm kurulu degil — atlandi, uydurulmadi"
    return disi


def kesit(kupon: bool = False,
          last: int | None = None) -> tuple[list[Girdi],
                                            Callable[[Girdi], Any] | None,
                                            dict[str, Any]]:
    """Arenanın koşacağı haftalar, gruplama ve kesit künyesi.

    Varsayılan **korpustur** (22 lig × 4 sezon, ~31 bin maç).

    `kupon=True` ölçümü Spor Toto kupon haftalarına çeker. **Bu kesit artık
    çok sezonlu** (§6G: 2022/23–2024/25 eklendi) ve `hafta_girdileri` artık
    `sezon` alanı yazıyor, dolayısıyla burada da **sezon dışarıda bırakmalı**
    ölçüm kurulabiliyor. Önceki sürümde kupon seti tek sezondu, `sezon_anahtari`
    hepsine `None` derdi ve bu fonksiyon bunu bir `uyari` dizesiyle yazıyordu;
    o uyarı artık yalnızca gerçekten tek sezon kaldığında çıkar.

    **Sızıntı uyarısı ayrı bir konudur ve kalkmaz:** kupon sezonlarının üçü
    (2022/23, 2023/24, 2024/25) eğitim korpusunda da var — 1.680 maçın
    1.200'ü birebir. Korpusta eğitilmiş bir tahminci bu haftalarda
    ölçülecekse `grup=sezon_anahtari` **şart**; künye bunu `sizinti` alanında
    söyler.
    """
    if kupon:
        haftalar = kupon_kesiti_tum(last)
        sezon_sayisi = len({h.get("sezon") for h in haftalar})
        cok_sezon = sezon_sayisi > 1
        return haftalar, (sezon_anahtari if cok_sezon else None), {
            "kaynak": f"kupon ({sezon_sayisi} sezon Spor Toto haftalari)",
            "grup_olcusu": "sezon" if cok_sezon else "hafta",
            "sezonlar": sorted({str(h.get("sezon") or "") for h in haftalar}),
            "sizinti": KUPON_KORPUS_KESISIMI,
            "uyari": None if cok_sezon else (
                "tek sezon — sezon disarida birakmali olcum kurulamaz; "
                "ayni sezonun baska haftalari bilgi sizdirir"),
        }

    from .egitim import korpus_haftalari, sezonlar

    haftalar = korpus_haftalari()
    return list(haftalar), sezon_anahtari, {
        "kaynak": "egitim korpusu (22 lig x 4 sezon)",
        "grup_olcusu": "sezon",
        "sezonlar": sezonlar(),
        "uyari": None,
    }


# ─── çökme tespiti — "bu sayı ölçüm mü, yoksa geri düşüş mü?" ─────────────────
#
# Depodaki tahmincilerin çoğu, eğitilemediğinde **sessizce bir tabana
# düşer**: `yigin` üst-öğrenici kurulamazsa ilk tabanına (`piyasa`),
# `beraberlik` yeterli nokta yoksa piyasayı olduğu gibi geçirir,
# `dixon_coles` takım eşleşemezse düzgüne düşer. Her biri kendi yerinde
# **doğru** bir karar: uydurma bir katsayı üretmektense bilinen bir görüşü
# taşımak. Ama arenada bu kararın bedeli var — tabloda `+0,0000` yazar ve
# bu sayı "ölçtük, fark yok" gibi okunur, oysa söylediği şey "model hiç
# koşmadı".
#
# Kupon kesitinde ölçüldü: 36 haftada `izotonik`, `yigin` ve `beraberlik`
# piyasayla BİREBİR aynı çıkıyor, `dixon_coles` düzgünle. Dört sayı da
# ölçüm değil, geri düşüştür.
#
# Tespit haftalık skor vektörü üzerinden yapılır: bir aday, kesitteki
# **her** haftada referansla aynı Brier ve aynı log kaybını veriyorsa
# aday o referansın kendisidir. 138 haftanın hepsinde 4 basamak birden
# tesadüfen tutmaz; ayrı iki modelin tek bir haftada tutması olağandır,
# hepsinde tutması olağan değildir.

def _haftalik(s: dict[str, Any]) -> list[tuple[Any, Any, Any]]:
    return [(h["week"], h["brier"], h["log_kaybi"]) for h in s.get("haftalar", [])]


def cokme(tahminciler: Sequence[dict[str, Any]]) -> dict[str, str]:
    """Hangi aday hangi tabana düşmüş — ad → düştüğü tahmincinin adı.

    Yalnızca **zemin** tahmincilere karşı bakılır (`piyasa`, `duzgun`):
    ikisi de eğitim gerektirmez, yani onlarla özdeşleşmek "eğitilemedim"
    demenin ta kendisidir. İki aday adayın birbiriyle özdeşleşmesi başka
    bir şeydir ve burada aranmaz.
    """
    from .predict import DuzgunTahminci

    tabanlar = {}
    for s in tahminciler:
        if s["ad"] in (REFERANS_AD, DuzgunTahminci.ad):
            tabanlar[s["ad"]] = _haftalik(s)

    out: dict[str, str] = {}
    for s in tahminciler:
        if s["ad"] in tabanlar:
            continue
        benim = _haftalik(s)
        if not benim:
            continue
        for taban_ad, taban in tabanlar.items():
            if benim == taban:
                out[s["ad"]] = taban_ad
                break
    return out


def notlar(ileri: bool) -> list[str]:
    """Tabloyu okumadan önce bilinmesi gerekenler.

    Not listesi çıktının süsü değil, **okuma şartıdır**: aşağıdaki iki
    madde olmadan tablodaki bir sayı yanlış okunur.
    """
    out = [
        "Referans `piyasa`. Bir aday ancak esleştirilmis bootstrap araliginin "
        "TAMAMI sifirin altindaysa `gecti` sayilir; ortalamasi daha iyi cikan "
        "ama araligi sifiri iceren aday gecmedi sayilir.",
        "Tablodaki sayilar bu kesitin sayilaridir. Modul basina raporlardaki "
        "(§3.26-§3.35) sayilarla ayni olmak zorunda DEGILDIR: oradaki kesitler "
        "ve marj arindirma cevrimleri farkli (§3.18).",
    ]
    if ileri:
        out += [
            "Ileri yuruyuste ilk grup olculmez (egitim seti bos olurdu) ve "
            "kesit o kadar kucuktur; `atlanan_gruplar` adini yazar.",
            "Ileri yuruyus Brier'i disarida birakmali Brier'den SISTEMATIK "
            "olarak kotudur — son grup disinda hicbir olcum butun veriyi "
            "gormez. Iki kip dogrudan kiyaslanmaz; kiyaslanan sey her kipin "
            "KENDI icindeki aday-referans farkidir.",
            "`yigin` ust-ogrenicisi kat disi gecis icin en az iki sezon ister "
            "(`arama.SezonKatlayici.yeterli`). Ilk olculen grupta bu sart "
            "saglanmaz ve yigin ILK TABANINA (piyasa) duser — o gruptaki "
            "farki sifira yakin cikaran sey model degil, veri azligidir.",
        ]
    return out


def rapor(kupon: bool = False,
          last: int | None = None,
          ileri: bool = False) -> dict[str, Any]:
    """Arenayı koştur: tek kesit, tek tablo, tek referans.

    Gövde `evaluate.karsilastir`ın çıktısıdır — arena yeni bir skorlama ya
    da bootstrap yazmaz, kuralı olduğu yerde bırakır. Arenanın kendi
    katkısı kayıt, kesit künyesi, dışarıda kalanlar ve okuma notlarıdır.
    """
    haftalar, grup, kunye = kesit(kupon=kupon, last=last)
    kayit = roster()
    sonuc = karsilastir([f for _, f in kayit], haftalar=haftalar,
                        grup=grup, ileri=ileri)

    cokenler = cokme(sonuc["tahminciler"])
    for s in sonuc["tahminciler"]:
        # `None` degil bos: alan HER satirda bulunsun, okuyan "bu alan var
        # miydi" diye sormasin.
        s["cokme"] = cokenler.get(s["ad"], "")

    sonuc["kesit"] = kunye
    sonuc["kayit"] = [ad for ad, _ in kayit]
    sonuc["n_aile"] = len(kayit)
    sonuc["disarida"] = disarida()
    sonuc["cokme"] = cokenler
    sonuc["notlar"] = notlar(ileri) + ([
        "COKME: asagidaki aday(lar) egitilemedi ve bir tabana dustu; "
        "satirlarindaki sayi olcum DEGIL, geri dusustur — "
        + ", ".join(f"{a} -> {b}" for a, b in cokenler.items())
    ] if cokenler else [])
    sonuc["kip"] = "ileri_yuruyus" if ileri else "disarida_birakmali"
    sonuc["soru"] = (
        "ayni kesitte, ayni gruplamayla, ayni referansa karsi olculdugunde "
        "hangi model ailesi piyasayi geciyor — 'gecti' sutununda EVET yazan "
        "bir aile yoksa cevap hicbiri")
    return sonuc


# ─── elle koşum ───────────────────────────────────────────────────────────────

def _yazdir(sonuc: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    k = sonuc["kesit"]
    print(f"kesit: {k['kaynak']} · {sonuc['n_hafta']} hafta · "
          f"{sonuc['n_mac']} maç · {sonuc['n_aile']} aile")
    print(f"kip: {sonuc['kip']} · gruplama: {k['grup_olcusu']} · "
          f"referans: {sonuc['referans']}")
    if sonuc.get("atlanan_gruplar"):
        print(f"atlanan grup(lar): {', '.join(map(str, sonuc['atlanan_gruplar']))} "
              f"— girdi {sonuc['n_hafta_girdi']} hafta, ölçülen {sonuc['n_hafta']}")
    if k.get("uyari"):
        print(f"UYARI: {k['uyari']}")

    print(f"\n{'tahminci':<24} {'brier':>8} {'log':>8} {'ΔBrier':>9} "
          f"{'%95 aralık':>20}  geçti")
    for s in sonuc["tahminciler"]:
        f = s["fark"]
        aralik = f"[{f['alt']:+.4f}, {f['ust']:+.4f}]" if f else ""
        fark = f"{f['fark']:+.4f}" if f else ""
        gecti = "—" if s["gecti"] is None else ("EVET" if s["gecti"] else "hayir")
        brier = f"{s['brier']:.4f}" if s["brier"] is not None else "—"
        log = f"{s['log_kaybi']:.4f}" if s["log_kaybi"] is not None else "—"
        # Coken satir isaretlenir: sayisi olcum degil, geri dusustur.
        ad = s["ad"] + (f"  ↳{s['cokme']}" if s.get("cokme") else "")
        print(f"{ad:<24} {brier:>8} {log:>8} "
              f"{fark:>9} {aralik:>20}  {gecti}")

    print("\ndışarıda — arenaya girmeyen aileler ve gerekçeleri:")
    for ad, gerekce in sonuc["disarida"].items():
        print(f"  {ad}: {gerekce}")

    print("\nnotlar:")
    for n in sonuc["notlar"]:
        print(f"  · {n}")
    print(f"\nsoru: {sonuc['soru']}")


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse
    import json

    from .kosum import belki_kaydet, cli_ekle

    ap = argparse.ArgumentParser(description="Model Arena — tek kesit, tek tablo")
    ap.add_argument("--kupon", action="store_true",
                    help="kupon haftalarinda olc (varsayilan: egitim korpusu)")
    ap.add_argument("--ileri", action="store_true",
                    help="kronolojik olcum: egitim yalnizca gecmis gruplar")
    ap.add_argument("--last", type=int, default=None,
                    help="kupon kipinde son N hafta")
    ap.add_argument("--json", action="store_true")
    cli_ekle(ap)
    a = ap.parse_args(argv)

    s = rapor(kupon=a.kupon, last=a.last, ileri=a.ileri)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1, default=str))
    else:
        _yazdir(s)
    belki_kaydet("arena", s, a)


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    main()
