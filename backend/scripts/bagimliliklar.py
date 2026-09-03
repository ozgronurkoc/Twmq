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

# `tomllib` STANDART KUTUPHANEYE 3.11'DE GIRDI ve bu satir bir zamanlar
# ciplak `import tomllib`di. Depo `requires-python = ">=3.10"` ilan ediyor,
# `.replit` python-3.10 kosuyor ve CI'nin kalite kapisi da bilerek 3.10'a
# sabitlenmis ("kapi da urunun kostugu zeminde kossun"). Yani bu betik
# KAPININ KOSTUGU YORUMLAYICIDA HIC CALISMADI: her CI kosumunda
# `ModuleNotFoundError: No module named 'tomllib'` verdi.
#
# Ne ruff ne mypy yakaladi — ruff `target-version` ile stdlib surumune
# bakmaz, mypy'nin `files` listesi ise `["spor_toto", "web_app.py"]`, yani
# `scripts/` tip denetiminin TAMAMEN DISINDA.
try:
    import tomllib
except ModuleNotFoundError:            # pragma: no cover - yalnizca py3.10
    import tomli as tomllib  # type: ignore[no-redef]

#: Denetlenen ekstralar. `ocr` ve `model` de girer: uretim onlari
#: kurmuyor ama CI ve olcum kosumlari kuruyor, yani bir acik oradan da
#: gelir.
#:
#: Liste ELLE yazili DEGIL: `pyproject.toml`in ilan ettigi ekstralarin
#: TAMAMI alinir. Onceden dort ad sabit yaziliydi ve `mcp` ekstrasi
#: eklendiginde bu liste guncellenmedi — yani denetim yuzeyi kimse fark
#: etmeden kuculdu. Bu, deponun baska yerlerde (check.sh'in hafta listesi)
#: zaten ogrendigi ders: kapinin kapsami diskteki gercekten turemeli.
EKSTRALAR_DISI: tuple[str, ...] = ()


def bagimliliklar(yol: Path | None = None) -> list[str]:
    """Beyan edilen tum bagimliliklar — cekirdek + `EKSTRALAR`."""
    kok = yol or Path(__file__).resolve().parent.parent / "pyproject.toml"
    with kok.open("rb") as fh:
        proje = tomllib.load(fh)["project"]
    out = list(proje.get("dependencies", []))
    ekstralar = proje.get("optional-dependencies", {})
    for ad in sorted(ekstralar):
        if ad in EKSTRALAR_DISI:
            continue
        out.extend(ekstralar[ad])
    return out


def main() -> int:
    """Bagimliliklari satir satir yazar; BOS cikti hatadir."""
    satirlar = bagimliliklar()
    # Bos cikti SESSIZCE YESIL bir guvenlik kapisi demektir ve tam olarak
    # oyle oldu: `import tomllib` py3.10'da patlayinca bu betik hicbir sey
    # yazmadi, `pip-audit -r /dev/stdin` BOS bir listeyi denetledi ve
    # "No known vulnerabilities found" dedi. Kapiyi yalnizca check.sh'in
    # `pipefail`i kirmizi tuttu; onsuz denetim hicligi onaylardi.
    if not satirlar:
        print("bagimlilik bulunamadi — pyproject.toml okunamadi ya da bos",
              file=sys.stderr)
        return 1
    print("\n".join(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
