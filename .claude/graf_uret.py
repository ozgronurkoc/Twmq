#!/usr/bin/env python3
"""Bilgi grafının UCUZ bölümlerini kaynaktan yeniden ölçer.

Ucuz bölüm: `moduller`, `kapilar`, `boru_hatlari`. Üçünün de kaynağı
dosyanın kendisidir (docstring, `.gitignore` yorumu), dolayısıyla yeniden
okumak "tahmin" değil **yeniden ölçüm**dür ve saniyenin altında sürer.

`sayilar` bölümüne DOKUNULMAZ. Bir sayıyı üretmek komut koşmayı gerektirir
(`pytest --collect-only`, eksiksiz kurulum) ve otomatik yeniden yazmak
skill'in kuralını çiğnerdi: bayat girdi silinir ya da yeniden ölçülür,
**düzeltilmiş sayılmaz**. Bu modül `sayilar` için yalnızca DENETLER ve
şüpheli girdiyi bildirir.
"""
from __future__ import annotations

import ast
import datetime
import json
import pathlib
import re
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent
GRAF = KOK / ".claude" / "bilgi_grafi.json"

#: OLCUM KUTUGU — `sayilar` ve `komutlar`. Grafin geri kalanindan AYRI bir
#: dosyada ve `.gitignore`da DEGIL; sebebi ikisinin farkli seyler olmasi:
#:
#:   `moduller`/`kapilar`/`boru_hatlari` TURETILMISTIR. Depoyu tarayarak
#:   0,3 saniyede yeniden uretiliyorlar, dolayisiyla surumlenmemeleri
#:   dogru — surumlenseydi bir baskasinin haftalik eski kesfi bugunun
#:   gercegi sanilirdi.
#:
#:   `sayilar`/`komutlar` TURETILMIS DEGILDIR. "Bu sayi su komuttan su
#:   tarihte cikti" bir KOSUM KAYDIDIR; depoyu tarayarak uretilemez, komut
#:   kosmayi gerektirir. Git disi tutuldugunda her taze klonda — yani her
#:   uzak oturumda — SIFIRDAN basliyordu ve deponun en pahali bilgisi her
#:   seferinde kayboluyordu.
#:
#: "Bayat sayi" korkusu bu dosya icin de gecerli ama BEKCISIZ degil:
#: `sayilar_denetle` her oturum acilisinda her kaydi anildigi yerle
#: karsilastirip "SUPHELI SAYI" diye bildiriyor. Yani kutuk, belgelerin
#: bekci kazanmadan onceki halinde degil.
KUTUK = KOK / ".claude" / "olcum_kutugu.json"


def kutuk_oku() -> dict:
    """Surumlenmis olcum kutugunu okur; yoksa bos iskelet."""
    if KUTUK.exists():
        return json.loads(KUTUK.read_text(encoding="utf-8"))
    return {"sayilar": [], "komutlar": []}


def kutuk_yaz(g: dict) -> None:
    """`sayilar` ve `komutlar`i kutuge yazar (graf dosyasina DEGIL)."""
    KUTUK.write_text(
        json.dumps({"sayilar": g.get("sayilar", []),
                    "komutlar": g.get("komutlar", [])},
                   ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
KAPI_DOSYA = "backend/tests/test_belgeler.py"
MODUL_DIZIN = "backend/spor_toto"


def _git(*arg: str) -> str:
    """Depo kökünde bir git komutu koşar ve çıktısını döndürür."""
    # S603 gerekcesi: cagrilar bu modulun kendi sabitleri
    # (`rev-parse`, `hash-object`), disaridan arguman gelmiyor.
    return subprocess.run(["git", *arg], cwd=KOK, capture_output=True,  # noqa: S603
                          text=True).stdout.strip()


def _hash(yol: str) -> str:
    """`git hash-object` çıktısı — bayatlığı görünür kılan tek alan."""
    return _git("hash-object", yol)


def _ilk_paragraf(ds: str | None) -> str | None:
    """Docstring'in ilk paragrafını tek satıra indirger."""
    return " ".join(ds.strip().split("\n\n")[0].split()) if ds else None


def moduller() -> list[dict]:
    """Modül envanterini docstring'lerden ölçer; docstring'siz modül YAZILMAZ."""
    out = []
    for p in sorted((KOK / MODUL_DIZIN).glob("*.py")):
        yol = str(p.relative_to(KOK))
        try:
            ds = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8",
                                                         errors="replace")))
        except SyntaxError:
            continue
        gorev = _ilk_paragraf(ds)
        if not gorev:
            continue
        out.append({"yol": yol, "gorev": gorev,
                    "kaynak": f"{yol}:1", "hash": _hash(yol)})
    return out


def kapilar() -> list[dict]:
    """Belge bekçilerini ve tuttukları iddiayı kendi docstring'lerinden ölçer."""
    p = KOK / KAPI_DOSYA
    if not p.exists():
        return []
    h = _hash(KAPI_DOSYA)
    out = []
    for n in ast.parse(p.read_text(encoding="utf-8")).body:
        if not (isinstance(n, ast.FunctionDef) and n.name.startswith("test_")):
            continue
        iddia = _ilk_paragraf(ast.get_docstring(n))
        if not iddia:
            continue
        out.append({"yol": KAPI_DOSYA, "ad": n.name, "tuttugu_iddia": iddia,
                    "kaynak": f"{KAPI_DOSYA}:{n.lineno}", "hash": h})
    return out


_KOMUT = re.compile(r"Yeniden olusturmak icin:\s*(.+?)\s*$")
_GERI = re.compile(r"`((?:python )?[-\w./ ]*(?:scripts/[\w.]+\.py|spor_toto\.\w+[^`]*))`")


def _gitignore_bloklari() -> list[tuple[str, list[str], int]]:
    """`.gitignore`'u (yorum metni, desenler, ilk desen satırı) bloklarına ayırır."""
    satirlar = (KOK / ".gitignore").read_text(encoding="utf-8").splitlines()
    bloklar: list[tuple[str, list[str], int]] = []
    yorum: list[str] = []
    desen: list[str] = []
    ilk: int | None = None

    def kapat() -> None:
        nonlocal yorum, desen, ilk
        if desen:
            bloklar.append((" ".join(yorum), desen[:], ilk or 0))
        yorum, desen, ilk = [], [], None

    for i, ham in enumerate(satirlar, 1):
        s = ham.strip()
        if not s:
            kapat()
        elif s.startswith("#"):
            if desen:
                kapat()
            yorum.append(s.lstrip("#").strip())
        else:
            if ilk is None:
                ilk = i
            desen.append(s)
    kapat()
    return bloklar


def boru_hatlari() -> list[dict]:
    """Boru hatlarını `.gitignore` yorumlarından ölçer; komutu yazılmayan atlanır."""
    out = []
    for metin, desen, satir in _gitignore_bloklari():
        if not any(d.startswith("backend/data") for d in desen):
            continue
        m = _KOMUT.search(metin)
        if m:
            komut = re.split(r"\s{2,}|\. ", m.group(1).strip().rstrip("."))[0].strip()
        else:
            m2 = _GERI.search(metin)
            if not m2:
                continue                      # kaynak yok -> girdi de yok
            komut = m2.group(1).strip()
        yollar = re.findall(r"(?:python )?(scripts/[\w.]+\.py)", komut)
        yol = f"backend/{yollar[0]}" if yollar else "backend/spor_toto/artefakt.py"
        kayit = {"yol": yol, "uretir": desen, "git_disi": True,
                 "yeniden_uret": komut, "kaynak": f".gitignore:{satir}"}
        if (KOK / yol).exists():
            kayit["hash"] = _hash(yol)
        out.append(kayit)
    return out


def _desen(deger: str) -> re.Pattern:
    """Sayıyı, İÇİNE GÖMÜLDÜĞÜ başka sayılarla karışmayacak biçimde arar.

    Sınır şart: `1901` aranırken `0,1901` (bir Brier skoru) eşleşmemeli —
    bu tam olarak yaşandı ve denetimi kör etti. Noktalı biçim (`1.879`)
    de kabul edilir, çünkü belgeler binlik ayracı kullanıyor.
    """
    bicimler = [re.escape(deger)]
    if deger.isdigit() and len(deger) > 3:
        bicimler.append(re.escape(f"{int(deger):,}".replace(",", ".")))
    return re.compile(r"(?<![\d.,])(?:" + "|".join(bicimler) + r")(?!\d)")


def sayilar_denetle(g: dict) -> list[tuple[str, str, str]]:
    """Kayıtlı `anildigi_yerler` hâlâ o değeri içeriyor mu — YALNIZCA denetler.

    Sayı bölümünün hash'i yoktur (bir sayı tek bir dosyaya bağlı değildir),
    onun denetimi budur. Arama dosyanın tamamında değil KAYITLI SATIRIN
    çevresinde yapılır; satır kaymasına karşı pencere bırakılır. Bulgu
    **yazılmaz**, bildirilir: yeniden ölçmek komut koşmayı gerektirir ve
    bu, insanın kararıdır.
    """
    PENCERE = 5
    #: (deger, yer, sebep) — cagiran ucunu de ac(iyor).
    supheli: list[tuple[str, str, str]] = []
    for s in g.get("sayilar", []):
        desen = _desen(s["deger"])
        for yer in s.get("anildigi_yerler", []):
            dosya = yer.split(":")[0].split(" ")[0]
            p = KOK / dosya
            if not p.exists():
                supheli.append((s["deger"], dosya, "dosya yok"))
                continue
            satirlar = p.read_text(encoding="utf-8", errors="replace").splitlines()
            parca = yer.split(":")
            no = int(parca[1]) if len(parca) > 1 and parca[1].isdigit() else None
            if no is None:
                if not any(desen.search(x) for x in satirlar):
                    supheli.append((s["deger"], dosya, "yok"))
                continue
            bas, son = max(0, no - 1 - PENCERE), min(len(satirlar), no + PENCERE)
            if any(desen.search(x) for x in satirlar[bas:son]):
                continue
            nerede = "dosyanin baska yerinde var" if any(
                desen.search(x) for x in satirlar) else "dosyada hic yok"
            supheli.append((s["deger"], yer, nerede))
    return supheli


def tazele(sessiz: bool = False) -> int:
    """Ucuz bölümleri yeniden ölçüp yazar, `sayilar`ı denetleyip bildirir."""
    if GRAF.exists():
        g = json.loads(GRAF.read_text(encoding="utf-8"))
    else:
        g = {"surum": 1, "git": {}, "moduller": [], "komutlar": [],
             "kapilar": [], "sayilar": [], "boru_hatlari": []}

    # Olcum kutugu SURUMLENMIS dosyadan gelir; graf dosyasindaki kopya
    # yalnizca sorgunun tek yerden okumasi icin var. Taze klonda graf yok
    # ama kutuk VAR — bolumlerin bos gelmemesinin tek sebebi bu.
    kutuk = kutuk_oku()
    if kutuk.get("sayilar") or kutuk.get("komutlar"):
        g["sayilar"] = kutuk.get("sayilar", [])
        g["komutlar"] = kutuk.get("komutlar", [])
    elif g.get("sayilar") or g.get("komutlar"):
        # GECIS: kutuk henuz yok ama graf dosyasinda elle birikmis kayit
        # var — kaybolmadan kutuge tasinsin.
        kutuk_yaz(g)

    onceki = {b: len(g.get(b, [])) for b in ("moduller", "kapilar", "boru_hatlari")}
    g["moduller"], g["kapilar"], g["boru_hatlari"] = moduller(), kapilar(), boru_hatlari()
    g["git"] = {"head": _git("rev-parse", "HEAD"),
                "dal": _git("rev-parse", "--abbrev-ref", "HEAD")}
    g["yazildi"] = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    GRAF.parent.mkdir(exist_ok=True)
    GRAF.write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    kutuk_yaz(g)

    degisim = [f"{b} {onceki[b]}->{len(g[b])}"
               for b in onceki if onceki[b] != len(g[b])]
    supheli = sayilar_denetle(g)

    if not sessiz or degisim or supheli:
        n = sum(len(g[b]) for b in ("moduller", "komutlar", "kapilar",
                                    "sayilar", "boru_hatlari"))
        print(f"bilgi grafi tazelendi: {n} girdi"
              + (f" · {', '.join(degisim)}" if degisim else ""))
    if supheli:
        # Sayi basina TEK satir: bu cikti her oturumda baglama giriyor.
        gruplu: dict[str, list[str]] = {}
        for deger, yer, _sebep in supheli:
            gruplu.setdefault(deger, []).append(yer)
        print("SUPHELI SAYI (elle yeniden olculmeli, otomatik yazilmaz):")
        for deger, yerler in gruplu.items():
            print(f"  {deger}: kayitli {len(yerler)} yerin hicbirinde yok"
                  f" -> {yerler[0]} ...")
        print("  ayrinti: .claude/graf_sorgu.py sayi <deger>")
    # Graf `.gitignore`'da: taze klonda EL EMEGIYLE yazilan bolumler gelmez ve
    # tazeleyici onlari uretemez (kaynaklari komut kosmak / belge okumak).
    # Sessizce kaybolmasinlar diye bildirilir.
    bos = [b for b in ("komutlar", "sayilar") if not g[b]]
    if bos:
        print(f"NOT: {' ve '.join(bos)} bolumu bos — otomatik uretilmez, elle birikir")
        print("     (graf git disidir; taze klonda envanter gelir, bu ikisi gelmez)")
    return 0


if __name__ == "__main__":
    sys.exit(tazele(sessiz="--sessiz" in sys.argv))
