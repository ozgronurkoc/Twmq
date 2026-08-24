"""Eğitilmiş modelin diske yazılması ve **bayatlığının görülmesi** (Faz 0.3).

Bugün üretimdeki tahminci ilk istekte eğitiliyor ve `lru_cache(maxsize=1)`
ile süreç ömrü boyunca tutuluyor (`tahmin._egitilmis_alternatif`). Bu iki
şeyi birden bozuyor:

1. **İlk isteğin bedeli.** 31.103 maçlık korpus okunuyor ve model
   uyduruluyor; o isteği yapan kullanıcı bekliyor.
2. **Hangi korpusla eğitildiği kayıtsız.** Süreç yeniden başlarsa model
   sessizce *yeni* korpusla yeniden eğitilir. Değişen bir şey olduğu hiçbir
   yerde görünmez — ne loglarda, ne sağlık raporunda.

Bu modül ikisini de kapatır: model bir dosyaya yazılır, dosya **hangi
korpustan** geldiğini taşır ve `health.py` korpus değiştiğinde bunu
**kırmızı** gösterir.

─── Neden turşu (pickle) değil, JSON ─────────────────────────────────────

Plan `joblib` diyordu. Alınmadı, üç sebeple:

1. **Yeni üretim bağımlılığı gerekmiyor.** `joblib`in asıl faydası büyük
   `numpy` dizilerini bellek eşlemeli yazmaktır; bizim durumumuz bir avuç
   katsayı (`KalibreTahminci._theta` tipik olarak 10–60 sayı).
2. **Turşu kod çalıştırır.** `pickle.load` dosyadaki talimatları yürütür;
   bozuk ya da değiştirilmiş bir artefakt sessiz bir yürütme yüzeyidir.
   JSON'da böyle bir yüzey yok.
3. **Turşu okunamaz, JSON okunur.** Artefakt bir *ölçüm kaydıdır*: hangi
   korpustan, ne zaman, hangi sürümle. `cat` ile bakılabilmesi bu belgenin
   işine yarar.

Bedeli: her tahminci durumunu **açıkça** yazmak zorunda (`durum`/`yukle`).
Bu bir maliyet gibi görünür ama aslında bir kazanç: turşu, sınıfın *bütün*
iç durumunu — geçici alanlar, önbellekler, kaza eseri kalmış her şey —
sessizce taşır. Açık durum, taşınanı **seçmeye** zorlar.

─── Bayatlık: yazılan tek şey model değil ────────────────────────────────

Zarf (`_ZARF_ALANLARI`) modelin yanında üç şey taşır:

``korpus``
    Korpus dosyasının sha256'sı, boyu ve satır sayısı. Model bundan geldi.
``egitim_tarihi``
    UTC ISO. *"Bu sayı ne zamanın sayısı?"*
``surum``
    Paket sürümü. Uydurucu değişirse aynı korpustan başka katsayı çıkar.

`oku()` uyuşmazlıkta **çökmez, `None` döner** ve sebebi `son_sebep`e yazar.
Çağıran o zaman yeniden eğitir. Bayatlık bir hata değil, bir olaydır — ama
**görünmez** olmamalıdır; `health.artefakt` onu raporlar.

    python -m spor_toto.artefakt --yaz     # egit ve diske yaz
    python -m spor_toto.artefakt           # durumu goster
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from . import __version__

KOK = Path(__file__).resolve().parent.parent

#: Artefakt dizini. **Sürümlenmez** (`.gitignore`): türetilmiş çıktıdır ve
#: projenin başka her boru hattında olduğu gibi kaynağından üretilir.
ARTEFAKT_DIZINI = KOK / "data" / "artefakt"

#: Zarf biçim sürümü. Biçim değişirse burası artar ve eski artefaktlar
#: sessizce okunmak yerine bayat sayılır.
BICIM = 1

_ZARF_ALANLARI = ("bicim", "tahminci", "surum", "korpus", "egitim_tarihi",
                  "durum")


@runtime_checkable
class Kalici(Protocol):
    """Diske yazılabilen tahminci: durumunu **açıkça** verir ve geri alır."""

    ad: str

    def durum(self) -> dict[str, Any]:
        """Uydurulmuş her şey, JSON'a çevrilebilir hâlde."""
        ...

    def yukle(self, durum: dict[str, Any]) -> None:
        """`durum`u geri koy. Eğitim yapılmaz."""
        ...


def korpus_parmak_izi(yol: Path | str | None = None) -> dict[str, Any]:
    """Korpus dosyasının kimliği — model bundan geldi.

    Sha256 **dosyanın kendisinden** alınır, türetilmiş haftalardan değil:
    türetme kodu değişirse aynı dosyadan başka haftalar çıkar ve o fark
    `surum` alanında görünür. İki alanın iki ayrı şeyi ölçmesi kasıtlıdır.

    Dosya yoksa `{"var": False}` döner — çökmez. Korpussuz bir kurulum
    geçerli bir kurulumdur (istatistik katmanı korpustan bağımsızdır).
    """
    from .egitim import VARSAYILAN_KORPUS

    p = Path(yol) if yol else VARSAYILAN_KORPUS
    if not p.exists():
        return {"var": False, "yol": _goreli(p)}

    h = hashlib.sha256()
    satir = 0
    with p.open("rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
            satir += blok.count(b"\n")
    return {"var": True, "yol": _goreli(p), "sha256": h.hexdigest(),
            "bayt": p.stat().st_size, "satir": satir}


def _goreli(p: Path) -> str:
    """Depo köküne göre yol — artefakt **taşınabilir** olmalı.

    Mutlak yol yazılsaydı bir makinede üretilen artefakt başka makinede
    okunduğunda anlamsız bir dize taşırdı; ayrıca gereksiz yere çalışma
    dizinini ifşa ederdi.
    """
    try:
        return p.resolve().relative_to(KOK).as_posix()
    except ValueError:
        return p.name


def _yol(ad: str, dizin: Path | str | None = None) -> Path:
    return Path(dizin or ARTEFAKT_DIZINI) / f"{ad}.json"


def yaz(model: Kalici, dizin: Path | str | None = None,
        korpus_yolu: Path | str | None = None) -> Path:
    """Eğitilmiş modeli zarfıyla birlikte diske yaz; yolu döndür."""
    zarf = {
        "bicim": BICIM,
        "tahminci": model.ad,
        "surum": __version__,
        "korpus": korpus_parmak_izi(korpus_yolu),
        "egitim_tarihi": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "durum": model.durum(),
    }
    p = _yol(model.ad, dizin)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Once gecici dosyaya, sonra tek adimda yerine: yarim yazilmis bir
    # artefakt "bayat" degil "bozuk"tur ve ikisi ayri seylerdir.
    gecici = p.with_suffix(".json.tmp")
    gecici.write_text(json.dumps(zarf, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    gecici.replace(p)
    return p


def zarf_oku(ad: str, dizin: Path | str | None = None
             ) -> tuple[dict[str, Any] | None, str]:
    """Zarfı oku ve **doğrula**: `(zarf, sebep)`. Geçerliyse sebep boştur.

    Doğrulama sırası kasıtlı — en ucuz ve en kesin olan önce: dosya var mı,
    biçim doğru mu, alanlar tam mı, sürüm aynı mı, korpus aynı mı.
    """
    p = _yol(ad, dizin)
    if not p.exists():
        return None, "artefakt yok"
    try:
        zarf = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return None, f"okunamadi: {type(e).__name__}"
    if not isinstance(zarf, dict):
        return None, "zarf sozluk degil"
    eksik = [a for a in _ZARF_ALANLARI if a not in zarf]
    if eksik:
        return None, f"zarf alanlari eksik: {', '.join(eksik)}"
    if zarf["bicim"] != BICIM:
        return None, f"bicim eskimis: {zarf['bicim']} != {BICIM}"
    if zarf["tahminci"] != ad:
        return None, f"tahminci adi tutmuyor: {zarf['tahminci']} != {ad}"
    if zarf["surum"] != __version__:
        return None, f"surum degismis: {zarf['surum']} != {__version__}"
    return zarf, ""


def bayat_mi(zarf: dict[str, Any],
             korpus_yolu: Path | str | None = None) -> str:
    """Zarfın korpusu bugünküyle aynı mı — değilse sebebi döner.

    **Bu fonksiyon `health`in kırmızısıdır.** Korpus değişip model
    değişmediğinde sistem çalışmaya devam eder ve *eski* korpusun modeliyle
    tahmin üretir; hiçbir test bunu görmez.
    """
    simdi = korpus_parmak_izi(korpus_yolu)
    onceki = zarf.get("korpus") or {}
    if not simdi.get("var"):
        return "korpus dosyasi yok"
    if not onceki.get("var"):
        return "artefakt korpussuz egitilmis"
    if onceki.get("sha256") != simdi.get("sha256"):
        return (f"korpus degismis: {str(onceki.get('sha256'))[:12]} != "
                f"{str(simdi.get('sha256'))[:12]}")
    return ""


def oku(model: Kalici, dizin: Path | str | None = None,
        korpus_yolu: Path | str | None = None) -> tuple[bool, str]:
    """Artefaktı `model`e yükle. `(yuklendi, sebep)`.

    Yüklenmediğinde **istisna yükseltmez**: çağıran yeniden eğitir. Sessiz
    olan tek şey bu değil — sebep her zaman döner ve `health` onu okur.
    """
    zarf, sebep = zarf_oku(model.ad, dizin)
    if zarf is None:
        return False, sebep
    bayat = bayat_mi(zarf, korpus_yolu)
    if bayat:
        return False, bayat
    try:
        model.yukle(zarf["durum"])
    except (KeyError, TypeError, ValueError) as e:
        return False, f"durum yuklenemedi: {type(e).__name__}: {e}"
    return True, ""


def durum(dizin: Path | str | None = None,
          korpus_yolu: Path | str | None = None) -> dict[str, Any]:
    """Diskteki bütün artefaktların durumu — `health` ve CLI bunu okur."""
    d = Path(dizin or ARTEFAKT_DIZINI)
    kayitlar: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        ad = p.stem
        zarf, sebep = zarf_oku(ad, d)
        if zarf is None:
            kayitlar.append({"ad": ad, "gecerli": False, "bayat": True,
                             "sebep": sebep})
            continue
        bayat = bayat_mi(zarf, korpus_yolu)
        kayitlar.append({
            "ad": ad, "gecerli": True, "bayat": bool(bayat),
            "sebep": bayat, "surum": zarf["surum"],
            "egitim_tarihi": zarf["egitim_tarihi"],
            "korpus_satir": (zarf.get("korpus") or {}).get("satir"),
        })
    return {
        "dizin": str(d),
        "korpus": korpus_parmak_izi(korpus_yolu),
        "artefaktlar": kayitlar,
        "bayat_sayisi": sum(1 for k in kayitlar if k["bayat"]),
    }


def uretim_tahmincisi() -> Kalici:
    """Üretimde `/api/tahmin`in kullandığı tahminci — **tek kaynak**.

    `tahmin.py` ile burası ayrı ayrı tahminci kursaydı, artefakt bir modeli
    yazar, servis başkasını çalıştırırdı; sağlık yeşil, tahmin başka olurdu.
    """
    from .recalibrate import KalibreTahminci
    from .tahmin import ALTERNATIF_KADEME

    return KalibreTahminci(ALTERNATIF_KADEME)


def uret(dizin: Path | str | None = None) -> Path | None:
    """Üretim tahmincisini korpusta eğit ve diske yaz."""
    from .egitim import korpus_haftalari

    haftalar = korpus_haftalari()
    if not haftalar:
        return None
    model = uretim_tahmincisi()
    model.egit(haftalar)  # type: ignore[attr-defined]
    return yaz(model, dizin)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--yaz", action="store_true", help="egit ve diske yaz")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.yaz:
        p = uret()
        print("korpus yok — yazilmadi" if p is None else f"yazildi: {p}")

    d = durum()
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return

    k = d["korpus"]
    print(f"\nKorpus: {k.get('yol')}")
    if k.get("var"):
        print(f"  sha256 {k['sha256'][:16]} · {k['satir']:,} satir "
              f"· {k['bayt']:,} bayt")
    else:
        print("  YOK")
    print(f"\nArtefakt dizini: {d['dizin']}")
    if not d["artefaktlar"]:
        print("  (bos) — `python -m spor_toto.artefakt --yaz`")
    for x in d["artefaktlar"]:
        durumu = "BAYAT" if x["bayat"] else "taze"
        print(f"  {x['ad']:<20}{durumu:<8}{x.get('egitim_tarihi') or '—':<22}"
              f"{x.get('sebep') or ''}")


if __name__ == "__main__":  # pragma: no cover
    main()
