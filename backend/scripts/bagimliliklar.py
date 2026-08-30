#!/usr/bin/env python3
"""`pyproject.toml`in BEYAN ETTIGI bagimliliklari requirements bicimine yazar.

Nicin var: `pip-audit`i ciplak calistirmak **butun ortami** denetler ve bu
kapida yanlis alarm uretir. Olculdu — bu kapsayicida `setuptools`,
`urllib3`, `wheel` ve `pyjwt` icin bulgu cikiyor; dordu de taban imajdan
geliyor, hicbiri `pyproject.toml`de yazili degil ve projenin surumlerini
secme yetkisi yok. Boyle bir kapi ya surekli kirmizi durur ya da
susturulur; ikisi de kapiyi islevsiz kilar.

Denetlenen sey bu yuzden **bizim sozlestigimiz** bagimliliklardir.
`sports-betting`in `noxfile.py`i de ayni ayrimi yapiyor (`pip-audit -r`
ile, kilit dosyasindan uretilmis bir requirements uzerinde).

    python scripts/bagimliliklar.py | pip-audit -r /dev/stdin
"""
from __future__ import annotations

import sys
from pathlib import Path

import tomllib

#: Denetlenen ekstralar. `ocr` ve `model` de girer: uretim onlari
#: kurmuyor ama CI ve olcum kosumlari kuruyor, yani bir acik oradan da
#: gelir.
EKSTRALAR = ("test", "kalite", "model", "ocr")


def bagimliliklar(yol: Path | None = None) -> list[str]:
    """Beyan edilen tum bagimliliklar — cekirdek + `EKSTRALAR`."""
    kok = yol or Path(__file__).resolve().parent.parent / "pyproject.toml"
    with kok.open("rb") as fh:
        proje = tomllib.load(fh)["project"]
    out = list(proje.get("dependencies", []))
    ekstralar = proje.get("optional-dependencies", {})
    for ad in EKSTRALAR:
        out.extend(ekstralar.get(ad, []))
    return out


def main() -> int:
    """Bagimliliklari satir satir yazar."""
    print("\n".join(bagimliliklar()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
