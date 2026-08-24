"""Ölçüm koşumlarının kaydı — *"bu sayı hangi koşumdan geldi?"* (Faz 0.4).

Belgelerdeki her sayı bir koşumdan gelir ve bugüne kadar o bağ **elle**
kuruluyordu: bir insan CLI'yı çalıştırıyor, çıktıyı okuyup Markdown'a
yazıyordu. Bu ara adım iki şeyi kaybediyor — sayının hangi korpustan,
hangi kod sürümünden ve hangi tohumdan geldiğini.

Kaybın maliyeti soyut değil. `ISTATISTIK_YOL_HARITASI.md` §3.16'da
**+0,0655** yazıyordu; Faz 3.4'te aynı hücre kontrollü koşumda **+0,0613**
çıktı. İkisi de doğruydu — farklı korpus sürümleriydi — ama bunu anlamak
yeni bir koşum gerektirdi. Koşum kaydı olsaydı fark **bakılarak**
görülürdü.

─── Ne yazılır ──────────────────────────────────────────────────────────

`data/kosumlar/<zaman>-<ad>/` altında iki dosya:

``cikti.json``   ölçümün kendi gövdesi, olduğu gibi
``ortam.json``   korpus parmak izi, git commit'i, paket sürümleri, tohumlar

İkincisi asıl olandır. Çıktı zaten belgeye kopyalanıyor; **yeniden
üretilebilirliği** taşıyan şey ortamdır.

─── Sürümlenmez, ve bu bilinçli ────────────────────────────────────────

Koşum dizini `.gitignore`'dadır. Sürümlenseydi her ölçüm koşumu depoyu
büyütürdü ve depo bir veri ambarına dönüşürdü. Kayıt **yerel bir
defterdir**: bir sayıyı savunmak gerektiğinde bakılır, paylaşılmaz.
Belgeye giren şey sayının kendisi ve koşum kimliğidir.

    python -m spor_toto.kosum              # kayitli kosumlar
    python -m spor_toto.kosum --son disari # son `disari` kosumunun ortami
"""
from __future__ import annotations

import json
import platform
import subprocess
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__

KOK = Path(__file__).resolve().parent.parent

#: Koşum defteri. **Sürümlenmez** — türetilmiş, yerel kayıt.
KOSUM_DIZINI = KOK / "data" / "kosumlar"

#: Kimlik biçimi: sıralanabilir olsun diye zaman önce gelir.
ZAMAN_BICIMI = "%Y%m%dT%H%M%SZ"


def _git_commit() -> str | None:
    """Calisan kodun commit'i — yoksa None (git disi bir kurulum olabilir)."""
    try:
        r = subprocess.run(["git", "-C", str(KOK), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def _kirli_mi() -> bool | None:
    """Calisma agacinda commit edilmemis degisiklik var mi.

    **Bu alan olmadan commit kimligi yaniltir:** kirli bir agacta kosulan
    olcum, o commit'ten uretilemez.
    """
    try:
        r = subprocess.run(["git", "-C", str(KOK), "status", "--porcelain"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return bool(r.stdout.strip()) if r.returncode == 0 else None


def ortam() -> dict[str, Any]:
    """Koşumun **yeniden üretilebilirlik** zarfı."""
    from importlib.metadata import version as _surum

    from .artefakt import korpus_parmak_izi
    from .evaluate import BOOTSTRAP_TEKRAR, BOOTSTRAP_TOHUM, EGRI_TOHUM

    def _v(paket: str) -> str | None:
        try:
            return _surum(paket)
        except Exception:
            return None

    return {
        "zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "surum": __version__,
        "git": {"commit": _git_commit(), "kirli": _kirli_mi()},
        "python": platform.python_version(),
        "paketler": {a: _v(a) for a in ("numpy", "scipy", "scikit-learn",
                                        "lightgbm")},
        "korpus": korpus_parmak_izi(),
        "tohumlar": {
            "bootstrap": BOOTSTRAP_TOHUM,
            "bootstrap_tekrar": BOOTSTRAP_TEKRAR,
            "ogrenme_egrisi": EGRI_TOHUM,
        },
    }


def kaydet(ad: str, cikti: dict[str, Any],
           dizin: Path | str | None = None) -> Path:
    """Koşumu deftere yaz; dizinini döndür.

    `ad` ölçümün adıdır (`disari`, `agac`, `yigin`…). Kimlik
    `<zaman>-<ad>` olur ve **sıralanabilir**: `sorted(glob)` kronolojik
    sıra verir, ayrı bir tarih ayrıştırmaya gerek kalmaz.
    """
    zaman = datetime.now(timezone.utc).strftime(ZAMAN_BICIMI)
    hedef = Path(dizin or KOSUM_DIZINI) / f"{zaman}-{ad}"
    hedef.mkdir(parents=True, exist_ok=True)
    # `default=str`: govdede tarih/ndarray gibi seyler olabilir ve bir
    # kaydin YAZILAMAMASI, eksik yazilmasindan daha kotudur.
    (hedef / "cikti.json").write_text(
        json.dumps(cikti, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    (hedef / "ortam.json").write_text(
        json.dumps(ortam(), ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    return hedef


def kosumlar(dizin: Path | str | None = None) -> list[dict[str, Any]]:
    """Defterdeki koşumlar, **eskiden yeniye**."""
    d = Path(dizin or KOSUM_DIZINI)
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob("*-*")) if d.exists() else []:
        if not (p / "ortam.json").exists():
            continue
        try:
            o = json.loads((p / "ortam.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        zaman, _, ad = p.name.partition("-")
        out.append({
            "kimlik": p.name, "ad": ad, "zaman": zaman, "yol": str(p),
            "commit": (o.get("git") or {}).get("commit"),
            "kirli": (o.get("git") or {}).get("kirli"),
            "korpus": (o.get("korpus") or {}).get("sha256"),
        })
    return out


def son(ad: str, dizin: Path | str | None = None) -> dict[str, Any] | None:
    """`ad` ölçümünün en son koşumu (yoksa `None`)."""
    uyan = [k for k in kosumlar(dizin) if k["ad"] == ad]
    return uyan[-1] if uyan else None


# ─── ölçüm CLI'larına bağlanma ────────────────────────────────────────────

def cli_ekle(ap: Any) -> None:
    """Ölçüm CLI'sına `--kaydet` bayrağını ekler.

    Tek satırlık bir yardımcı olmasının sebebi **tutarlılık**: bayrak adı,
    yardım metni ve davranışı yedi CLI'da tek yerde tanımlı. Ayrı ayrı
    yazılsaydı biri `--kayit`, öteki `--save` olurdu.
    """
    ap.add_argument("--kaydet", action="store_true",
                    help="kosumu deftere yaz (data/kosumlar/, surumlenmez)")


def belki_kaydet(ad: str, cikti: dict[str, Any], args: Any) -> Path | None:
    """`--kaydet` verilmişse koşumu yaz ve kimliği bas.

    Kimliği **basmak** işin yarısıdır: belgeye sayıyı yazan kişi koşum
    kimliğini de kopyalayabilsin diye.
    """
    if not getattr(args, "kaydet", False):
        return None
    yol = kaydet(ad, cikti)
    print(f"\nkosum kaydedildi: {yol.name}")
    return yol


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--son", default=None, metavar="AD",
                    help="bu olcumun son kosumunun ortamini bas")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.son:
        k = son(a.son)
        if k is None:
            print(f"'{a.son}' icin kayitli kosum yok")
            return
        o = json.loads((Path(k["yol"]) / "ortam.json").read_text(encoding="utf-8"))
        print(json.dumps(o, ensure_ascii=False, indent=1))
        return

    kayit = kosumlar()
    if a.json:
        print(json.dumps(kayit, ensure_ascii=False, indent=1))
        return
    print(f"\nKOSUM DEFTERI — {KOSUM_DIZINI}")
    if not kayit:
        print("  (bos) — bir olcumu `--kaydet` ile kosun")
        return
    print(f"{'kimlik':<34}{'commit':<10}{'korpus':<10}  agac")
    for k in kayit:
        print(f"{k['kimlik']:<34}"
              f"{(k['commit'] or '—')[:8]:<10}"
              f"{(k['korpus'] or '—')[:8]:<10}  "
              f"{'KIRLI' if k['kirli'] else 'temiz'}")


if __name__ == "__main__":  # pragma: no cover
    main()
