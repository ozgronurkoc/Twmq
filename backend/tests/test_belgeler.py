"""Belgelerin gerçekle örtüşmesini tutan bekçiler.

**Neden var.** Bu depoda belgeler koddan hızlı eskiyordu ve eskidikleri
hiçbir yerde görünmüyordu. Denetimde bulunanlar:

* test sayısı **dört belgede dört farklı** değerdi (700 / 911 / 664 / 664);
* `README.md` §1.1 hold-out isabetini **1**, §14 aynı sayıyı **0** diyordu —
  tek dosyanın kendi içinde çelişkisi;
* `docs/ARCHITECTURE_NEXT.md` "kesin karar" başlıklı API tablosunda **dört uç
  eksikti** ve iki belge daha o tabloyu kaynak gösteriyordu;
* `backend/README.md` "hiçbir API ucu oran arşivinden okumaz" diyordu, oysa
  `/api/stats` bir `odds` bloğu döndürüyor.

Bunların hepsi elle düzeltildi. Buradaki testler **tekrar eskimesini**
engeller: liste dosya sistemiyle karşılaştırılır, sayı ölçümle.

Kasıtlı olarak DAR: her cümleyi değil, sessizce yanlışlanabilen **sayılabilir**
iddiaları tutar.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
DEPO = KOK.parent


def _oku(göreli: str) -> str:
    p = DEPO / göreli
    if not p.exists():
        pytest.skip(f"{göreli} yok")
    return p.read_text(encoding="utf-8")


def test_mimari_belgesi_butun_uclari_sayar():
    """`ARCHITECTURE_NEXT.md` API tablosu `web_app`teki uçların TAMAMINI saymalı.

    Bu tablo iki belge tarafından daha *kaynak* gösteriliyor, yani bir eksik
    satır üç yere birden yayılıyor.
    """
    metin = _oku("docs/ARCHITECTURE_NEXT.md")
    kaynak = (KOK / "web_app.py").read_text(encoding="utf-8")

    yollar = set(re.findall(r'@app\.route\("([^"]+)"', kaynak))
    # `<int:week>` tabloda `<week>` diye yazılır.
    yollar = {y.replace("<int:week>", "<week>") for y in yollar}

    # YALNIZCA tablo satırları sayılır. Önce "belgede geçiyor mu" diye
    # bakılıyordu ve bekçi işe yaramıyordu: aynı belgenin NESRİ de uçları
    # anıyor, dolayısıyla tablodan bir satır silinse bile test geçiyordu.
    # (Ölçüldü: `/api/benzer` satırı tablodan çıkarıldı, test yeşil kaldı.)
    tablo_uclari: set[str] = set()
    for satir in metin.splitlines():
        if not satir.startswith("| "):
            continue
        hucreler = [h.strip() for h in satir.strip("|").split("|")]
        if len(hucreler) < 2:
            continue
        m = re.match(r"`([^`]+)`", hucreler[1])
        if m:
            # `?last=N` gibi örnek sorgular yoldan ayrılır.
            tablo_uclari.add(m.group(1).split("?")[0])

    eksik = sorted(y for y in yollar if y not in tablo_uclari)
    assert not eksik, (
        f"ARCHITECTURE_NEXT.md API TABLOSUNDA eksik uç: {eksik}. "
        f"web_app.py {len(yollar)} uç tanımlıyor, tablo {len(tablo_uclari)} sayıyor."
    )


def test_saglik_kontrol_sayisi_belgeyle_ayni():
    """"Kayıtlı kontrol: N" diyen her belge `health.CHECKS` ile örtüşmeli.

    **Bu bekçinin kör noktası tam olarak nereye baktığıydı.** Yalnızca
    `docs/SAGLIK_GELISTIRME_RAPORU.md`yi okuyordu — yani `DONMUS_BELGELER`
    listesindeki, tanımı gereği geçmişi anlatan tek belgeyi. Canlı olan
    `docs/SAGLIK_VIZYONU.md` §11 aynı satırı taşıyor ve taranmıyordu:
    rapor 23, vizyon 27 diyordu, gerçek 23'tü ve kapı yeşil kaldı.
    Bekçinin ölçtüğü sayı doğruydu, **baktığı yer yanlıştı**.

    Kaynak artık `_belge_listesi()`: donmuş kayıtlar hariç depodaki bütün
    belgeler. Aynı desen `test_betik_sayisi_belgeyle_ayni` ve
    `test_test_dosya_sayisi_belgelerle_ayni` ile aynıdır — varsayılan
    korumalıdır, muafiyet açıkça yazılır.

    **İkinci kör nokta: aynı sayının ikinci adı.** Yalnızca *"kayıtlı
    kontrol"* aranıyordu, oysa depo aynı sayıyı çoğu yerde **"N değişmez"**
    diye yazıyor. Ölçüldüğünde altı belgede toplam dokuz yerde `27` vardı
    (`README.md` §1 dahil — ki aynı dosya §6.3'te `23 kontrol` diyordu,
    yani dosya KENDİ İÇİNDE çelişiyordu). Bir sayının iki adı varsa bekçi
    ikisini de tanımalıdır, yoksa tanımadığı ad bekçisiz kalır.

    **Alt küme iddiaları sayılmaz.** `SAGLIK_VIZYONU.md` §11 şunu yazıyor:
    *"2 değişmez (`kume_tamami_oynaniyor`, `olasilik_tutarliligi`)"* — bu
    `/api/health/kupon`un koşturduğu alt kümedir, katmanın toplamı değil ve
    **doğrudur**. Kural şudur: sayı hemen ardından hangi kontrolleri kastettiğini
    parantez içinde `backtick`le sayıyorsa, o bir alt küme iddiasıdır ve
    atlanır. Doğru bir cümleyi kırmızı yakan bekçi, hiç bekçi olmamasından
    kötüdür (bu dosyanın kurucu kuralı).
    """
    from spor_toto.health import CHECKS

    desen = re.compile(
        r"(?:[Kk]ayıtlı kontrol[^\d\n]{0,12}(\d+)"
        r"|(\d+)\s*(?:sağlık\s*)?değişmez)")
    #: "2 değişmez (`a`, `b`)" — ardından kontrolleri adıyla sayan iddia.
    alt_kume = re.compile(r"\s*\(\s*`")
    yanlis: dict[str, list[int]] = {}
    tarandi = 0
    for d in _belge_listesi():
        p = DEPO / d
        if not p.exists():
            continue
        metin = p.read_text(encoding="utf-8")
        sayilar: set[int] = set()
        for m in desen.finditer(metin):
            if alt_kume.match(metin, m.end()):
                continue
            sayilar.add(int(m.group(1) or m.group(2)))
        if not sayilar:
            continue
        tarandi += 1
        if sayilar != {len(CHECKS)}:
            yanlis[d] = sorted(sayilar)
    if not tarandi:
        pytest.skip("hiçbir belgede kayıtlı kontrol sayısı geçmiyor")
    assert not yanlis, (
        f"kayıtlı kontrol sayısı GERÇEKLE ayrışmış (gerçek: {len(CHECKS)}): "
        + "; ".join(f"{d}={v}" for d, v in yanlis.items())
    )


#: Sayı taşımasına **izin verilen** donmuş kayıtlar. Bu liste bir opt-OUT'tur:
#: taranan küme depodaki bütün `*.md` dosyalarıdır, buradakiler hariç.
#:
#: **Neden ters çevrildi.** Önce burada `SAYI_TASIYAN_BELGELER` adlı bir
#: opt-IN demeti vardı — beş belge elle sayılıydı ve yeni bir belge
#: varsayılan olarak **korumasız** kalıyordu. `backend/README.md` tam olarak
#: böyle kaçtı: içinde `tests/ (31 dosya → 1.030 test)` yazıyordu, gerçek
#: 63 dosya / 1.901 testti (o günün sayısı), ve bekçi yeşil kaldı. Yani bekçinin kör noktası
#: sayının kendisi değil, **listenin kendisiydi**. Artık varsayılan
#: korumalıdır ve muafiyet açıkça, gerekçesiyle yazılır.
#:
#: Buradaki her satır belgenin KENDİSİNDE yazılı bir damgaya dayanır — bir
#: ölçüm kaydı sonradan yeniden yazılmaz, ve bekçinin **doğru bir cümleyi
#: yanlış** diye işaretlemesi hiç bekçi olmamasından kötüdür (aynı gerekçeyle
#: bu dosyadan bir hold-out bekçisi de kaldırılmıştı — aşağıdaki nota bakınız).
DONMUS_BELGELER = {
    # "Bugünkü sayılar (2026-08-23). Yukarısı bu turun kaydıdır ve öyle kalır."
    "docs/SAGLIK_GELISTIRME_RAPORU.md",
    # "Bu belgenin tarihi: 2026-08-29 · taban `d607360`"
    "docs/GELISTIRME_PLANI_ESLEMESI.md",
    # Aynı türden künye damgası taşır ("48 modüllük bir paket").
    "docs/BENZER_PLANI_ESLEMESI.md",
    # Ölçüm kütüğünün kendisi: her girdi tarihli bir turun kaydı ve
    # içindeki sayılar bilerek geçmişi anlatır (ör. "62 dosya → 1.879 test"
    # düzeltilmiş bir kör noktanın ANLATIMIDIR, bugünkü iddia değil).
    "docs/token_olcum_kutugu.md",
}

#: `.claude/` taranmaz: ajan kurulumudur, ürünün iddiası değil — ve
#: `skills/token-optimizer/` upstream'den olduğu gibi alınmıştır
#: (`VENDORED.md`), oradaki sayılar bu deponun ölçümü değildir.
TARANMAYAN_KOK = ".claude/"


def _belge_listesi() -> list[str]:
    """Depodaki taranacak `*.md` dosyaları — donmuş kayıtlar hariç.

    Kaynak `git ls-files`: elle tutulan bir liste tam olarak yukarıda
    anlatılan şekilde eskiyordu. Git yoksa bekçi kör kalmaktansa atlar.
    """
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=DEPO,
                         capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        pytest.skip("git ls-files okunamadı — belge listesi çıkarılamıyor")
    return [y for y in out.stdout.split()
            if not y.startswith(TARANMAYAN_KOK) and y not in DONMUS_BELGELER]


def _belgelerdeki_test_sayilari() -> dict[str, set[int]]:
    """Belgelerde geçen "N test" ifadelerini dosya dosya toplar."""
    bulunan: dict[str, set[int]] = {}
    for d in _belge_listesi():
        p = DEPO / d
        if not p.exists():
            continue
        sayilar = {
            int(x.replace(".", ""))
            for x in re.findall(r"([\d.]+)\s*test\b", p.read_text(encoding="utf-8"))
            if x.replace(".", "").isdigit() and int(x.replace(".", "")) > 300
        }
        if sayilar:
            bulunan[d] = sayilar
    return bulunan


def _gercek_test_sayisi() -> int:
    """Süiti AYRI bir süreçte toplayıp gerçek test sayısını döndürür.

    Ayrı süreç şart: `addopts` `-n auto` taşıyor ve xdist altında bir işçi
    yalnızca kendi payını görür, yani `request.session`den okumak paralel
    koşuda yanlış (ve işçi sayısına göre değişken) cevap verirdi. Alt
    süreçte `addopts` boşaltılır — hem xdist'i, hem de özyinelemeyi keser.

    **Sayı ortama bağlıdır ve bu bir kusur değil, tanımdır.** `test_agac.py`
    modül düzeyinde `pytest.importorskip("lightgbm")` yapıyor; paket yoksa
    modül hiç TOPLANMAZ, yalnızca "atlandı" da denmez — 22 test ortadan
    kalkar. Yani "süitte kaç test var" sorusunun tek bir cevabı yok:
    `lightgbm`siz kurulumda eksiksiz süitten 22 test eksiktir.

    **Bu sayı burada İKİ KEZ eskidi ve ikisinde de kimse görmedi.** Önce
    docstring `1.622` / `1.600` yazıyordu; o değerler README §9 tablosunun
    15. satırına kadarki ara toplamıydı, yani tablo bakımsız kaldığı
    dönemden kalmaydı. Düzeltilirken *"mutlak sayı yerine artık fark
    yazılı"* denildi ama **mutlak sayı satırda bırakıldı** (`1.929`) ve
    kaplama sökülüp ~130 test düşünce ikinci kez bayatladı. Bekçinin kendi
    dosyası, bekçilediği hatayı iki kez taşıdı — ve `.py` olduğu için
    hiçbir belge taraması ona bakmıyor.

    Bu yüzden mutlak sayı artık **gerçekten** yazılı değil: yalnızca fark
    (22) duruyor, çünkü fark koda bağlı ve `test_agac.py` durdukça doğru;
    süitin toplamı ise her eklemede değişir. Toplamın tek yazılı olduğu
    yer belgelerdir ve onu bu dosyadaki bekçi gerçek koleksiyona karşı
    denetler — yani toplamın burada ikinci bir kopyası olmamalı.

    Depo bu ikiliği zaten taşıyor ve bilerek taşıyor: üretim `lightgbm`
    kurmuyor (`scripts/run_prod.sh`), kalite kapısı kuruyor
    (`.[test,kalite,model,mcp,ocr]`), CI'nın sürüm matrisi kurmuyor (`.[test]`).
    Belgelerdeki sayı **eksiksiz süitin** sayısıdır, çünkü belgelerin
    anlattığı depo odur.

    Bu yüzden eksik kurulumda bekçi kırılmaz, **atlar**. Kırılsaydı
    söylediği şey "belgeler bayat" değil, "bu ortamda lightgbm yok" olurdu
    ve yanlış bir cümleyi kırmızı yakmak, bekçiyi zamanla görmezden
    gelinen bir gürültüye çevirir. Atladığında da sessiz kalmaz: sebebi
    yazar, ve kapı işini yapmaya devam eder — eksiksiz kurulumun bulunduğu
    tek koşum (kalite kapısı) sayıyı TAM olarak denetler.
    """
    import importlib.util

    eksik = [ad for ad in ("lightgbm",) if importlib.util.find_spec(ad) is None]
    if eksik:
        pytest.skip(
            f"eksik istege bagli paket: {', '.join(eksik)} — bu kurulumda "
            "sureden bazi modüller hic toplanmiyor, yani sayilan sey "
            "eksiksiz suit degil. Tam denetim kalite kapisinda "
            "(`pip install -e '.[test,kalite,model,mcp,ocr]'`).")

    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-o", "addopts=", "-p", "no:cacheprovider"],
        cwd=KOK, capture_output=True, text=True, timeout=300,
    )
    m = re.search(r"(\d+) tests? collected", out.stdout)
    if not m:
        pytest.skip(f"toplama sayısı okunamadı (çıkış {out.returncode})")
    return int(m.group(1))


def test_test_sayisi_belgelerde_tek_ve_dogru():
    """Belgelerdeki test sayısı hem birbiriyle hem GERÇEKLE aynı olmalı.

    **Bu bekçi bir kez zaten yetersiz kaldı.** Önceden yalnızca belgelerin
    *birbiriyle* uyumuna bakıyordu, oysa asıl bayatlama şöyle oluyor: sayı
    altı belgeye birden kopyalanıyor, süite test ekleniyor ve altısı da
    **birbiriyle tutarlı biçimde yanlış** kalıyor. Tam olarak bu yaşandı —
    1.022 altı belgede aynı anda eskidi ve bekçi yeşil kaldı.

    Bu yüzden karşılaştırma artık gerçek koleksiyona karşıdır ve **tamdır**.
    Tolerans bilerek yok: tolerans, sapmanın sessizce birikeceği yerdir.
    Süite test eklemek belgeleri bozarsa doğru davranış budur — sayı bir
    yerde tek satırdır ve `git grep` ile bulunur.
    """
    bulunan = _belgelerdeki_test_sayilari()
    assert bulunan, "hiçbir belgede test sayısı geçmiyor — bekçi kör kalmış"

    gercek = _gercek_test_sayisi()
    yanlis = {d: sorted(v) for d, v in bulunan.items() if v != {gercek}}
    assert not yanlis, (
        f"belgelerdeki test sayısı GERÇEKLE ayrışmış (gerçek: {gercek}). "
        + "; ".join(f"{d}={v}" for d, v in yanlis.items())
        + f" — düzeltmek için: git grep -n '{sorted(set().union(*bulunan.values()))[0]}'"
    )


def test_readme_belge_dizini_eksiksiz():
    """`docs/` altındaki her belge README §13'te sayılmalı.

    Belge dizini bir **giriş kapısıdır**: orada olmayan belge pratikte yok
    demektir. `docs/DIS_INCELEME.md` tam olarak böyle, listede hiç yer
    almadan durdu — dosya vardı, ona götüren bir yol yoktu.
    """
    metin = _oku("README.md")
    diskte = {p.name for p in (DEPO / "docs").glob("*.md")}
    eksik = sorted(ad for ad in diskte if f"docs/{ad}" not in metin)
    assert not eksik, (
        f"README §13 belge dizininde eksik: {eksik}. "
        "Dosya varsa dizinde de olmalı, yoksa kimse bulamaz."
    )


def test_readme_modul_listesi_eksiksiz():
    """README §7 modül ağacı `spor_toto/`teki her modülü saymalı.

    `replit.md` bu ağacı **"tam liste"** diye gösteriyor ve `backend/README.md`
    artık kendi seçkisinden buraya yönlendiriyor — yani bu tek listedir ve
    eksik bir satır üç belgeye birden yayılır. Ölçüldüğünde 51 modülün
    **13'ü** ağaçta yoktu (`fiyatlar.py` README'de hiç geçmiyordu), ve hiçbir
    bekçi bunu tutmuyordu.

    **Sayı değil liste karşılaştırılır.** Belgelerde `48/46/26/50` gibi
    modül sayıları geçiyor; bir kısmı meşru alt küme, bir kısmı donmuş künye.
    Sayısal bir bekçi doğru cümleleri kırmızı yakardı — bu dosyanın kuralı
    tam tersi. `test_readme_belge_dizini_eksiksiz` ile aynı desen: kaynak
    dosya sistemi, karşılaştırma isim isim.
    """
    metin = _oku("README.md")
    diskte = sorted(p.name for p in (KOK / "spor_toto").glob("*.py")
                    if p.name != "__init__.py")
    # Ağaç satırı `    <ad>.py   <açıklama>` biçiminde; nesirdeki `odds.py`
    # gibi anmalar sayılmasın diye satır başı girinti aranır.
    listede = set(re.findall(r"^\s+([a-z_0-9]+\.py)\s", metin, re.MULTILINE))
    eksik = [ad for ad in diskte if ad not in listede]
    assert not eksik, (
        f"README §7 modül ağacında eksik: {eksik}. "
        f"spor_toto/ {len(diskte)} modül taşıyor, ağaç bunların "
        f"{len(diskte) - len(eksik)}'ini sayıyor. "
        "Liste tek kaynaktır — replit.md ve backend/README.md buraya yönlendirir."
    )


def test_test_dosya_sayisi_belgelerle_ayni():
    """"N test dosyası" diyen belgeler dosya sistemiyle örtüşmeli.

    Ayrı bir test: dosya sayısı diskten okunur, alt süreç gerekmez — yani
    yukarıdaki toplama düşse bile bu bekçi ayakta kalır.

    **Bu bekçinin bir kör noktası vardı ve kapatıldı.** Yalnızca "N test
    dosyası" ifadesini arıyordu, oysa `README.md` §9 aynı sayıyı başka
    biçimde yazıyor: "(62 dosya → 1.879 test)". O 62 yanlıştı (gerçek 63),
    bekçi göremedi ve sayı sessizce bayat kaldı — tam olarak bu bekçinin
    engellemek için var olduğu şey. İkinci desen o biçimi de tarar.

    Ok biçimi (`N dosya →`) bilerek dar tutuldu: yalın "N dosya" taransaydı
    football-data arşivinin "38 dosya"sı yanlış yere kırmızı yanardı ve
    doğru bir cümleyi yanlış diye işaretleyen bekçi, hiç bekçi olmamasından
    kötüdür.
    """
    gercek = len(list((KOK / "tests").glob("test_*.py")))
    yanlis: dict[str, list[int]] = {}
    for d in _belge_listesi():
        p = DEPO / d
        if not p.exists():
            continue
        metin = p.read_text(encoding="utf-8")
        sayilar = {
            int(x) for x in
            re.findall(r"(\d+)\s*test dosyası", metin)
            + re.findall(r"(\d+)\s*dosya\s*(?:→|->)", metin)
        }
        if sayilar and sayilar != {gercek}:
            yanlis[d] = sorted(sayilar)
    assert not yanlis, f"test dosyası sayısı yanlış (gerçek: {gercek}): {yanlis}"


def test_betik_sayisi_belgeyle_ayni():
    """"N betik" diyen belge `scripts/` ile örtüşmeli.

    **Bu bekçi bir bayatlamadan SONRA yazıldı ve sebebi tam olarak budur.**
    `backend/README.md` "24 betik" diyordu, gerçek 27'ydi: üçü birden
    sessizce eskimişti, çünkü test dosyası ve modül listesinin bekçisi
    varken betik sayısının **yoktu**. Aynı depoda aynı kusurun bekçisiz
    kalan üçüncü kopyasıydı.

    `__init__.py` sayılmaz — belge onu ayrıca ("+ `__init__.py`") yazıyor
    ve pakete ait olduğunu söylüyor; sayılan şey **betiklerdir**.
    """
    gercek = len([y for y in (KOK / "scripts").glob("*.py")
                  if y.name != "__init__.py"])
    yanlis: dict[str, list[int]] = {}
    for d in _belge_listesi():
        p = DEPO / d
        if not p.exists():
            continue
        sayilar = {int(x) for x in
                   re.findall(r"(\d+)\s*betik", p.read_text(encoding="utf-8"))}
        if sayilar and sayilar != {gercek}:
            yanlis[d] = sorted(sayilar)
    assert not yanlis, f"betik sayısı yanlış (gerçek: {gercek}): {yanlis}"


def test_kalite_kapisi_ve_setup_AYNI_ekstralari_kurar():
    """CI'nın kalite kapısı ile `setup.sh --kalite` aynı kümeyi kurmalı.

    İkisi ayrışırsa yerelde geçen kapı CI'da **başka bir şey** koşar —
    `scripts/check.sh`in var olma sebebinin tam tersi (CI onu çağırıyor ki
    ayrışamasınlar; kurulum listesi ayrışırsa aynı betik farklı bir yüzeyi
    ölçer).

    **Ölçülmüş zarar.** Uzun süre iki ekstra (`mcp`, `ocr`) hiçbir CI
    işinde kurulmadı. Bir ekstra kurulmadığında ona bağlı testler
    **atlanır** ve kapı yine yeşil kalır: iki test bir kez bile CI'da
    koşmadı ve hiçbir yerde görünmedi. Sessiz atlama, kırmızı bir kapıdan
    kötüdür — çünkü korunuyor sanırsın.
    """
    import re as _re

    ci = (DEPO / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    m = _re.search(r'pip install -e "\./backend\[([^\]]+)\]"', ci)
    assert m, "CI kalite kapısında `pip install -e ./backend[...]` bulunamadı"
    ci_kume = {x.strip() for x in m.group(1).split(",")}

    kur = (DEPO / "scripts" / "setup.sh").read_text(encoding="utf-8")
    kalite_satirlari = _re.findall(r'^\s*EKSTRALAR="([^"]+)"', kur, _re.MULTILINE)
    assert len(kalite_satirlari) == 2, (
        f"`setup.sh` iki `EKSTRALAR` ataması bekliyordu, {len(kalite_satirlari)} var")
    setup_kume = {x.strip() for x in kalite_satirlari[-1].split(",")}

    assert ci_kume == setup_kume, (
        f"CI kalite kapısı {sorted(ci_kume)} kuruyor, "
        f"`setup.sh --kalite` {sorted(setup_kume)} — ayrışmışlar")

    # İlan edilen HER ekstra bu kümede olmalı; yenisi eklenince sessizce
    # denetimsiz kalmasın. (`pyproject.toml`ın kendisi tek kaynak.)
    #
    # TOML AYRIŞTIRICISI KULLANILMIYOR ve sebebi bu deponun kendi dersi:
    # `tomllib` 3.11+, `tomli` ise `[kalite]` ekstrasında. Bu test CI'nın
    # matris işinde py3.10 + yalnızca `[test]` ile de koşuyor; ayrıştırıcıya
    # dayanan bir bekçi tam orada ya düşer ya atlanır.
    proje_metni = (KOK / "pyproject.toml").read_text(encoding="utf-8")
    bolum = proje_metni.split("[project.optional-dependencies]", 1)
    assert len(bolum) == 2, "`[project.optional-dependencies]` bölümü yok"
    govde = bolum[1].split("\n[", 1)[0]
    ilan = set(_re.findall(r"^([a-z][a-z0-9_-]*)\s*=\s*\[", govde, _re.MULTILINE))
    assert ilan, "hiçbir ekstra adı okunamadı — bekçi kör kalmış"
    eksik = ilan - ci_kume
    assert not eksik, (
        f"ilan edilen ama kalite kapısında KURULMAYAN ekstra: {sorted(eksik)} "
        "— testleri sessizce atlanır")


def test_workflowlarda_pytest_gercekten_kosabilir():
    """`pytest` çağıran her workflow adımı GERÇEKTEN koşabilmeli.

    **Bu bekçi ölçülmüş bir sessiz ölümden geldi.** `pyproject.toml`
    `addopts` içinde `-n auto` taşıyor; o `pytest-xdist`in bayrağıdır. İki
    veri toplama workflow'u (`snapshot-iddaa.yml`, `snapshot-sportoto.yml`)
    bilerek yalnızca `pytest` kuruyordu ve xdist yokken pytest **tek test
    gövdesine girmeden** `unrecognized arguments: -n` ile çıkış 4 veriyordu.
    Yani haftalık cron ile depoya commit atan iki boru hattının tek biçim
    denetimi aylarca ölüydü ve hiçbir yerde görünmüyordu.

    Ders `scripts/setup.sh` içinde bir paragrafla zaten yazılıydı ("xdist
    yoksa pytest hic acilmadan 'unrecognized arguments' verir") — orada
    öğrenilmiş, workflow'lara uygulanmamıştı. Bekçi o boşluğu kapatır.

    Kabul edilen üç çare: xdist'i kurmak, `-o addopts=` ile ini'yi geçersiz
    kılmak, ya da `-p no:cacheprovider` gibi değil ama `-n` veren bir eklenti
    getirmek. Test bunlardan **en az birini** arar.
    """
    wf_dizin = DEPO / ".github" / "workflows"
    if not wf_dizin.is_dir():
        pytest.skip(".github/workflows yok")

    pyproject = (KOK / "pyproject.toml").read_text(encoding="utf-8")
    # `addopts` gerçekten `-n` taşıyor mu? Taşımıyorsa bu bekçinin konusu
    # kalmaz ve sessizce geçmesi doğrudur.
    if "-n auto" not in pyproject:
        pytest.skip("pyproject.toml artık `-n auto` taşımıyor")

    # Xdist DOLAYLI da gelebilir: `test` ekstrası onu taşıyorsa
    # `pip install -e ".[test]"` diyen bir workflow'da "xdist" kelimesi hiç
    # geçmez ama paket kurulur. İlk yazımda bu gözden kaçtı ve bekçi
    # `tests.yml`i haksız yere kırmızıya boyadı — bir bekçinin doğru
    # cümleyi yanlış diye işaretlemesi, hiç bekçi olmamasından kötüdür.
    test_ekstrasi = re.search(r"^test\s*=\s*\[[^\]]*\]", pyproject, re.MULTILINE)
    ekstra_xdist_veriyor = bool(test_ekstrasi and "xdist" in test_ekstrasi.group(0))

    kusurlu: list[str] = []
    for yol in sorted(wf_dizin.glob("*.yml")):
        satirlar = yol.read_text(encoding="utf-8").splitlines()
        # **Yorumlar konuşur, kurmaz.** Kanıt yalnızca KOŞAN satırlarda
        # aranır. İlk yazımda tüm dosyada aranıyordu ve bekçi kendi
        # açıklama yorumundaki "xdist" kelimesini kanıt sayıp kör kaldı —
        # onarımı geri alıp sınadığımda yakalandı.
        kod = "\n".join(s for s in satirlar if not s.strip().startswith("#"))
        # `pip install -e ".[test,...]"` biçimindeki her kurulum.
        ekstra_kuruluyor = bool(re.search(r"pip install[^\n]*\[[^\]]*\btest\b", kod))
        xdist_var = ("xdist" in kod
                     or (ekstra_xdist_veriyor and ekstra_kuruluyor))
        for satir in satirlar:
            s = satir.strip()
            # Yorum satırları konuşur, koşmaz.
            if s.startswith("#") or "pytest" not in s:
                continue
            # `pip install ... pytest` bir çağrı değil, kurulum.
            if "pip install" in s:
                continue
            if not re.search(r"(^|\s|&&\s*)pytest\s", s):
                continue
            if not (xdist_var or "-o addopts=" in s):
                kusurlu.append(f"{yol.name}: {s}")

    assert not kusurlu, (
        "bu pytest çağrıları `-n auto` yüzünden HİÇ KOŞMAZ "
        "(xdist kurulmuyor ve `-o addopts=` ile ini geçersiz kılınmıyor): "
        + "; ".join(kusurlu)
    )


# NOT: burada bir de "README hold-out sayisini kendi icinde celismiyor mu"
# testi vardi ve KALDIRILDI. Nesir uzerinde regex kirilgan cikti: README
# §5.4 bilerek TARIHSEL bir karsilastirma yapiyor ("orantisal olcekte ayni
# tablo hold-out'ta 0 haftaydi") ve o cumle dogru. Bir bekcinin dogru
# cumleyi yanlis diye isaretlemesi, hic bekci olmamasindan kotudur.
#
# Asil celiski (§14'un §1.1 ile catismasi) elle duzeltildi; onu tutan sey
# artik `api_sozlesme.py`nin urettigi olculmus degerler, nesir taramasi degil.


def test_readme_test_tablosu_GERCEK_koleksiyonu_sayar():
    """README §9 katman tablosu hem eksiksiz hem doğru toplamalı.

    **Bu tablo "bekçisi var" diye yazıyordu ve YOKTU.** Tablonun hemen
    üstündeki cümle *"dosyalar adıyla sayılıdır ki bu tablo elle bakımı
    gerektirmesin — `tests/test_belgeler.py` onu gerçek koleksiyona karşı
    denetler"* diyordu; hiçbir test o tabloyu okumuyordu. Ölçüldüğünde
    tablo **1.684** topluyordu ama manşeti **1.902** diyordu (Δ 218) ve
    63 dosyanın yalnızca **55'ini** sayıyordu — sekiz dosya (`bulten`,
    `deger`, `fiyatlar`, `gecmis_sezon`, `havuz`, `kuyruk`, `mcp`,
    `sportoto_arsiv`) eklendikten sonra tabloya hiç girmemişti.

    Test iki şeyi birden tutar: **kapsama** (her test dosyası tabloda
    anılmalı) ve **toplam** (satırların toplamı manşetle aynı olmalı).
    Dosya başına sayıyı doğrulamak için gerçek koleksiyon gerekir; o
    `test_test_sayisi_belgelerde_tek_ve_dogru`un işi.
    """
    metin = _oku("README.md")
    bas = metin.find("| Katman | Dosyalar | Test |")
    assert bas > 0, "README §9 katman tablosu bulunamadı"
    son = metin.find("\n\n", bas)
    tablo = metin[bas:son]

    anilan = set(re.findall(r"`([a-z_0-9]+)`", tablo))
    diskte = {p.stem[len("test_"):] for p in (KOK / "tests").glob("test_*.py")}
    eksik = sorted(diskte - anilan)
    assert not eksik, (
        f"README §9 tablosunda ANILMAYAN test dosyası: {eksik}. "
        f"Tablo {len(anilan & diskte)} dosya sayıyor, diskte {len(diskte)} var."
    )

    toplam = sum(int(x) for x in re.findall(r"\|\s*(\d+)\s*\|", tablo))
    manset = re.search(r"\*\*(\d+) test dosyası, parametrizasyonla\s*\n?([\d.]+) test",
                       metin)
    assert manset, "README §9 manşeti (N test dosyası / M test) bulunamadı"
    beklenen = int(manset.group(2).replace(".", ""))
    assert toplam == beklenen, (
        f"README §9 tablosu {toplam} topluyor ama manşeti {beklenen} diyor "
        f"(Δ {beklenen - toplam}). Tablo satır satır elle tutuluyor; "
        "süite test eklendiğinde ilgili satır da güncellenmeli."
    )


def test_check_sh_adimlari_belgeyle_ayni():
    """README'nin saydığı `check.sh` adım sayısı betikle örtüşmeli.

    Liste bir kez eskidi ve fark edilmedi: **interrogate, pip-audit ve
    doctest** betikte vardı, README'de yoktu — üstelik README aşağıda
    "`check.sh`in adımları bu bölümün başında sayılıdır" diyerek o eksik
    listeyi yetkili gösteriyordu.
    """
    betik = (DEPO / "scripts" / "check.sh").read_text(encoding="utf-8")
    gercek = len(re.findall(r"^baslik ", betik, re.MULTILINE))
    metin = _oku("README.md")
    m = re.search(r"`scripts/check\.sh` sırasıyla \*\*([a-zçğıöşü ]+?) adım\*\*", metin)
    assert m, "README `check.sh` adım sayısını yazmıyor"
    yazili = {"on": 10, "on bir": 11, "on iki": 12, "on üç": 13, "on dört": 14}
    beklenen = yazili.get(m.group(1).strip())
    assert beklenen is not None, f"tanınmayan sayı: {m.group(1)!r}"
    assert beklenen == gercek, (
        f"README `check.sh`i {beklenen} adım diyor, betikte {gercek} `baslik` var"
    )


def test_workflow_envanteri_belgeyle_ayni():
    """`.github/workflows/` altındaki her workflow bir belgede anılmalı.

    `snapshot-sportoto.yml` **hiçbir `.md` dosyasında geçmiyordu**: README
    "İkinci workflow" deyip yalnızca iddaa'yı anlatıyordu, oysa depoya
    haftalık commit atan iki iş var. Belgesiz bir yazma yetkisi, en kötü
    türden sessizliktir.
    """
    wf = DEPO / ".github" / "workflows"
    if not wf.is_dir():
        pytest.skip(".github/workflows yok")
    belgeler = "\n".join(
        (DEPO / d).read_text(encoding="utf-8")
        for d in _belge_listesi() if (DEPO / d).exists()
    )
    eksik = [y.name for y in sorted(wf.glob("*.yml")) if y.name not in belgeler]
    assert not eksik, (
        f"hicbir belgede anilmayan workflow: {eksik}. "
        "Depoya commit atan bir isin belgesiz kalmasi kabul edilemez."
    )


#: Dinamik rota parçası. Dosya sisteminde `[week]`, README §6.1'de
#: `<hafta>`, README §7 ağacında ve `replit.md`de `[week]` yazılıyor —
#: karşılaştırmadan önce üçü de tek biçime indirgenir. (Aynı sorun
#: `test_mimari_belgesi_butun_uclari_sayar`da `<int:week>` → `<week>` diye
#: çözülmüştü; burada üç biçim olduğu için normalleştirme genel tutuldu.)
_DINAMIK_PARCA = re.compile(r"\[[^\]/]+\]|<[^>/]+>")

#: "N sayfa" iddiasının DAR iki biçimi: sayı + parantez içi rota listesi
#: (README §7 ağacı), ve sayı + tabloya havale (`ARCHITECTURE_NEXT.md`).
#: Yalın `\d+ sayfa` taransaydı `super_toto_sayfa.py`nin bastığı HTML
#: sayfalarından söz eden bir cümle yanlış yere kırmızı yanardı —
#: `test_test_dosya_sayisi_belgelerle_ayni` "N dosya →" biçimini tam olarak
#: bu gerekçeyle dar tutuyor.
_SAYFA_SAYISI_LISTELI = re.compile(r"(\d+) sayfa \((/[^)]*)\)", re.DOTALL)
_SAYFA_SAYISI_TABLOYA = re.compile(r"(\d+) sayfa — aşağıdaki tablo")


def _rota_normal(yol: str) -> str:
    """Rotayı biçimden bağımsız hale getirir: dinamik parça tek ada iner."""
    return _DINAMIK_PARCA.sub(":dinamik", yol.strip().rstrip("/")) or "/"


def _arayuz_rotalari() -> set[str]:
    """`frontend/app/` altındaki her `page.tsx`in rotası — TEK kaynak."""
    kok = DEPO / "frontend" / "app"
    if not kok.is_dir():
        pytest.skip("frontend/app yok")
    rotalar = set()
    for p in kok.rglob("page.tsx"):
        # Next.js'te `(ad)` bir düzen grubudur, rotaya girmez.
        parcalar = [x for x in p.parent.relative_to(kok).parts
                    if not x.startswith("(")]
        rotalar.add(_rota_normal("/" + "/".join(parcalar)))
    return rotalar


def _sayfa_bolumu(metin: str) -> str:
    """"Sayfalar" başlıklı bölümün gövdesi — bir sonraki başlığa kadar.

    Bölüme daraltmak şarttır: aynı belgelerde `/api/...` uçlarını listeleyen
    BAŞKA tablolar var ve belgenin tamamı taransaydı onlar da rota sayılırdı.
    `test_mimari_belgesi_butun_uclari_sayar`ın "yalnızca tablo satırları"
    dersinin bir adım ilerisi: yalnızca DOĞRU tablonun satırları.
    """
    satirlar = metin.splitlines()
    for i, s in enumerate(satirlar):
        if s.startswith("#") and "Sayfalar" in s:
            j = i + 1
            while j < len(satirlar) and not satirlar[j].startswith("#"):
                j += 1
            return "\n".join(satirlar[i + 1:j])
    return ""


def _tablodaki_rotalar(bolum: str) -> set[str]:
    """Tablo satırının İLK hücresindeki backtick'li yolu toplar."""
    return {_rota_normal(m.group(1)) for m in
            re.finditer(r"^\|\s*`(/[^`]*)`\s*\|", bolum, re.MULTILINE)}


def test_sayfa_tablolari_eksiksiz():
    """"Sayfalar" tablosu taşıyan her belge `frontend/app/`in TAMAMINI saymalı.

    **Ölçülen boşluk buydu.** Bu dosya modülleri, testleri, uçları,
    betikleri, workflow'ları ve kapı adımlarını sayan bekçiler içeriyordu —
    ama sayfa sayan bir bekçi içermiyordu, ve sayının kaydığı yer bekçinin
    olmadığı yerle birebir örtüştü. Dosya sisteminde **10** `page.tsx`
    varken README §6.1 tablosu **8** rota (eksik: `/tahmin`, `/super-toto`),
    README §7 ağacı **7** rota, `docs/ARCHITECTURE_NEXT.md` tablosu **9**
    rota (eksik: `/pazarlar`) sayıyordu. `replit.md` tek doğru listeydi.

    Kaynak dosya sistemi, karşılaştırma isim isim —
    `test_readme_modul_listesi_eksiksiz` ile aynı desen. Belge listesi
    `git ls-files`ten geldiği için ileride "Sayfalar" tablosu kazanan bir
    belge kendiliğinden kapsama girer.

    **Fazlalık da tutulur.** Silinmiş bir sayfanın tabloda kalması, eksik
    satırla aynı türden bir yalandır ve arayan kişiyi var olmayan bir yola
    gönderir.
    """
    gercek = _arayuz_rotalari()
    kusurlu: dict[str, tuple[list[str], list[str]]] = {}
    for d in _belge_listesi():
        p = DEPO / d
        if not p.exists():
            continue
        tablo = _tablodaki_rotalar(_sayfa_bolumu(p.read_text(encoding="utf-8")))
        if not tablo:
            continue
        eksik, fazla = sorted(gercek - tablo), sorted(tablo - gercek)
        if eksik or fazla:
            kusurlu[d] = (eksik, fazla)
    assert not kusurlu, (
        "Sayfa tablosu gerçekle örtüşmüyor: "
        + "; ".join(f"{d} eksik={e or '-'} fazla={f or '-'}"
                    for d, (e, f) in sorted(kusurlu.items()))
        + f". frontend/app/ {len(gercek)} sayfa taşıyor: {sorted(gercek)}"
    )


def test_belgelerdeki_sayfa_sayisi_gercekle_ayni():
    """"N sayfa" diyen belge hem sayıyı hem listeyi doğru vermeli.

    README §7 ağacı sayıyı ve listeyi YAN YANA yazıyor
    (`app/  N sayfa (/, /tahmin, ...)`), yani ikisi birden bayatlayabilir ve
    ölçüldüğünde ikisi birden bayattı: "7 sayfa" diyip yedi rota sayıyordu,
    gerçek on. `ARCHITECTURE_NEXT.md` ise sayıyı yazıp listeyi tabloya
    havale ediyor — orada yalnızca sayı denetlenir, tablonun kendisini
    yukarıdaki bekçi tutar.
    """
    gercek = _arayuz_rotalari()
    hata: list[str] = []
    for d in _belge_listesi():
        p = DEPO / d
        if not p.exists():
            continue
        metin = p.read_text(encoding="utf-8")
        for m in _SAYFA_SAYISI_LISTELI.finditer(metin):
            yazili = {_rota_normal(x) for x in m.group(2).split(",") if x.strip()}
            if int(m.group(1)) != len(gercek):
                hata.append(f"{d}: '{m.group(1)} sayfa' yazıyor, gerçek {len(gercek)}")
            if yazili != gercek:
                hata.append(
                    f"{d}: parantez içi liste eksik={sorted(gercek - yazili) or '-'} "
                    f"fazla={sorted(yazili - gercek) or '-'}"
                )
        for m in _SAYFA_SAYISI_TABLOYA.finditer(metin):
            if int(m.group(1)) != len(gercek):
                hata.append(f"{d}: '{m.group(1)} sayfa' yazıyor, gerçek {len(gercek)}")
    assert not hata, "Sayfa sayısı bayat: " + "; ".join(hata)
