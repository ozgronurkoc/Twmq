"""Avrupa kupası maçları — korpusun **ölçülmüş** kör noktasını kapatır (Faz 3.4).

`egitim._takvim_tablosu`ın kendi belgesi bu boşluğu yıllardır yazıyordu:

> *"Korpus 22 lig taşıyor; kupa ve Avrupa maçları içinde yok. Dolayısıyla
> dinlenme günü olduğundan **uzun**, fikstür sıkışıklığı olduğundan
> **düşük** ölçülür — ve hata rastgele değil, Avrupa oynayan (yani güçlü)
> takımlarda yoğunlaşır."*

§3.16 (A3) o eksik ölçümle bir şey buldu ve açıklayamadı: deplasman
"dinlenmiş" göründüğünde ev sahibi piyasayı **+0,0655** aşıyordu ve etki
Avrupa liglerinde dört kat güçlüydü. Yani bulgu bir *sinyal* değil, bir
*ölçüm hatası* olabilirdi — ve ikisini ayırt etmenin tek yolu eksik maçları
korpusa katmaktı.

`scripts/build_avrupa.py` onları getirir (openfootball, kamu malı, ad
eşleşmesi **%100**); bu modül onları takvime **enjekte eder**.

─── Yeni bir özellik değil, mevcut özelliğin düzeltilmesi ───────────────

Tasarımın can alıcı yeri burası. Avrupa maçları ayrı bir sütun olarak
eklenseydi, `dinlenme_farki` **yanlış kalmaya devam ederdi** ve model iki
çelişkili girdiyi uzlaştırmak zorunda kalırdı. Bunun yerine `dinlenme` ve
`sikisiklik` hesapları Avrupa günlerini de görür: sayı artık *doğru*dur.

Ayrıca ölçülebilir olsun diye **ayrı** bir sütun da eklenir
(`avrupa_farki`): pencere içinde deplasmanın kaç Avrupa maçı oynadığı eksi
ev sahibininki. İşaret projenin geri kalanıyla aynı yönde — pozitif = ev
lehine.

─── Sızıntı yok, ve sebebi ──────────────────────────────────────────────

Avrupa fikstürü bir **takvim** bilgisidir: kimin ne zaman oynayacağı maçtan
önce bellidir (`lig_toplam` ile aynı gerekçe). Yine de bu modül yalnızca
**kesinlikle geçmişte** kalan tarihleri sayar (`< bugun`); sonuç, gol,
skor hiç okunmaz — dosyada zaten yoktur. Bekçi:
`test_avrupa.py::test_gelecegi_gormez`.
"""
from __future__ import annotations

import bisect
import csv
from collections.abc import Sequence
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_FIKSTUR = KOK / "data" / "avrupa" / "avrupa_fikstur.csv"

#: Sıkışıklık penceresi — `egitim.SIKISIKLIK_PENCERE_GUN` ile **aynı** olmak
#: zorunda. Ayrışsalardı iki sayı aynı adı taşıyıp farklı şeyi ölçerdi;
#: bekçisi `test_avrupa.py::test_pencere_egitimle_ayni`.
def _pencere() -> int:
    from .egitim import SIKISIKLIK_PENCERE_GUN

    return SIKISIKLIK_PENCERE_GUN


def _gun(ham: str) -> date:
    y, a, g = (int(p) for p in ham.split("-"))
    return date(y, a, g)


@lru_cache(maxsize=2)
def _fikstur(yol: str | None = None) -> tuple[tuple[str, str], ...]:
    """`(takim, tarih)` çiftleri. Dosya yoksa **boş** — çağıran karar verir.

    Boş dönmek sessiz bir bozulma değil: `avrupa_var` alanı `False` kalır ve
    ölçüm raporunda kapsama sıfır görünür.
    """
    p = Path(yol) if yol else VARSAYILAN_FIKSTUR
    if not p.exists():
        return ()
    out: list[tuple[str, str]] = []
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            tarih = (r.get("tarih") or "").strip()
            if not tarih:
                continue
            for alan in ("ev", "dep"):
                takim = (r.get(alan) or "").strip()
                if takim:
                    out.append((takim, tarih))
    return tuple(out)


def avrupa_gunleri(yol: str | None = None) -> dict[str, list[date]]:
    """`{takim: [tarih, ...]}` — her takımın Avrupa maç günleri, **sıralı**.

    Sıralı olması şart: `_son_avrupa` ikili arama yapıyor ve sıralı olmayan
    bir liste sessizce yanlış cevap verir.
    """
    out: dict[str, list[date]] = {}
    for takim, tarih in _fikstur(yol):
        out.setdefault(takim, []).append(_gun(tarih))
    for v in out.values():
        v.sort()
    return out


def son_avrupa(gunler: Sequence[date], bugun: date) -> date | None:
    """`bugun`den **kesinlikle önceki** en yakın Avrupa maçı."""
    i = bisect.bisect_left(gunler, bugun)
    return gunler[i - 1] if i > 0 else None


def pencere_sayisi(gunler: Sequence[date], bugun: date,
                   pencere: int | None = None) -> int:
    """Son `pencere` gün içinde oynanan Avrupa maçı sayısı (bugün hariç)."""
    p = _pencere() if pencere is None else pencere
    sag = bisect.bisect_left(gunler, bugun)
    sol = bisect.bisect_right(gunler, date.fromordinal(bugun.toordinal() - p))
    return max(0, sag - sol)


def kapsama(satirlar: Sequence[dict[str, Any]],
            yol: str | None = None) -> dict[str, Any]:
    """Korpusun ne kadarı Avrupa fikstürüne dokunuyor — rapor için.

    *"Özellik gerçekten çalışıyor mu"* sorusunun ilk cevabı budur: kapsama
    sıfırsa ölçüm bir şeyi değil **hiçbir şeyi** ölçer.
    """
    gunler = avrupa_gunleri(yol)
    if not gunler:
        return {"takim": 0, "mac": 0, "dokunan_mac": 0, "oran": 0.0}
    dokunan = 0
    for r in satirlar:
        bugun = _gun(r["tarih"])
        if any(pencere_sayisi(gunler.get(t, []), bugun) > 0
               for t in (r["ev"], r["dep"])):
            dokunan += 1
    n = len(satirlar)
    return {"takim": len(gunler),
            "mac": len(_fikstur(yol)) // 2,
            "dokunan_mac": dokunan,
            "oran": (dokunan / n) if n else 0.0}


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    from .egitim import korpus_yukle

    k = kapsama(korpus_yukle())
    if a.json:
        print(json.dumps(k, ensure_ascii=False, indent=1))
        return
    print(f"\nAVRUPA FIKSTURU — {k['mac']:,} mac · {k['takim']} takim")
    print(f"Korpusun {k['dokunan_mac']:,} maci ({k['oran']:.1%}) "
          f"pencere icinde bir Avrupa maci tasiyor.")
    if not k["mac"]:
        print("\nFikstur dosyasi yok — `python scripts/build_avrupa.py`")


if __name__ == "__main__":  # pragma: no cover
    main()
