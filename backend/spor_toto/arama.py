"""İç içe CV — hiperparametre aramasını hold-out'u bozmadan serbest bırakır.

Proje bugüne kadar hiperparametre **ayarlamayı reddetti** ve gerekçesi
`recalibrate.L2`'nin yorumunda yazılı:

> *"Ayarlanmadı ve ayarlanmayacak — ölçüm sonucuna bakarak seçilirse
> hold-out'un anlamı kalmaz."*

Bu doğruydu, **çünkü tek halka vardı**. Aynı sezonlar hem ayar hem ölçüm
için kullanılırsa seçilen parametre o ölçüme uyar ve "dışarıda bıraktık"
cümlesi yalan olur.

İki halka kurulunca kısıt kalkar ve dürüstlük kalır:

    DIŞ halka   sezon dışarıda bırakmalı — `evaluate.hafta_disarida_birak`
                DOKUNULMAZ. Ayar bu halkanın test sezonunu hiç görmez.
    İÇ halka    eğitim sezonlarının kendi içinde, yine sezon bazlı.
                Parametre burada seçilir.

`Tahminci` sözleşmesi değişmez: ayar `egit`in **içinde** olur, dolayısıyla
`evaluate` bir tahmincinin ayarlanıp ayarlanmadığını bilmez ve bilmesi de
gerekmez.

─── AlphaPy burada yarım kaldı ───────────────────────────────────────────

`DIS_INCELEME_ALPHAPY.md` §4.1: AlphaPy Pro'nun **dış** bölmesi kronolojik
(`pl.col(ts_date) <= split_date`) ama **iç** CV'si hâlâ
`StratifiedKFold(shuffle=...)`. Yani `OptunaSearchCV`, `RFECV` ve
`CalibratedClassifierCV`'nin hepsi geleceği geçmişe karıştıran katlarla
karar veriyor. `SezonKatlayici` tam olarak o boşluğu kapatmak için var ve
sklearn'ün splitter arayüzünü uyguladığı için o araçların hepsine
doğrudan verilebilir.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import Any

import numpy as np


class SezonKatlayici:
    """Sezon bazlı `LeaveOneGroupOut` — sklearn splitter arayüzü.

    `cv=` bekleyen her sklearn aracına verilebilir (`GridSearchCV`,
    `RFECV`, `CalibratedClassifierCV`, `cross_val_score`, `OptunaSearchCV`).
    Fark şudur: kat sınırları **sezon** sınırlarıdır, rastgele değil.

    `en_az_kat` altında kalan gruplama reddedilir — tek sezonluk bir eğitim
    setinde "sezon dışarıda bırakmalı" ayar yapılamaz ve sessizce tek katla
    devam etmek, ayarın yapıldığı yanılsamasını üretirdi.
    """

    def __init__(self, gruplar: Sequence[Any], en_az_kat: int = 2) -> None:
        self.gruplar = list(gruplar)
        self.en_az_kat = en_az_kat
        # Sıra kasıtlı olarak GÖRÜLME sırası (sorted değil): sezon
        # etiketleri metin ve alfabetik sıra kronolojik olmak zorunda değil.
        self._benzersiz = list(dict.fromkeys(self.gruplar))

    def get_n_splits(self, X: Any = None, y: Any = None,
                     groups: Any = None) -> int:
        return len(self._benzersiz)

    def yeterli(self) -> bool:
        return len(self._benzersiz) >= self.en_az_kat

    def split(self, X: Any = None, y: Any = None,
              groups: Any = None) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        dizi = np.asarray(self.gruplar, dtype=object)
        for g in self._benzersiz:
            test = np.flatnonzero(dizi == g)
            egitim = np.flatnonzero(dizi != g)
            if len(egitim) == 0 or len(test) == 0:
                continue
            yield egitim, test


#: Aramanın sonucu: seçilen parametreler + her adayın kat ortalaması.
AramaSonucu = dict[str, Any]


def izgara_ara(adaylar: Sequence[dict[str, Any]],
               katlayici: SezonKatlayici,
               skorla: Callable[[dict[str, Any], np.ndarray, np.ndarray], float],
               varsayilan: dict[str, Any] | None = None) -> AramaSonucu:
    """Aday parametreleri iç halkada dener, en iyisini döndürür.

    `skorla(params, egitim_indeksleri, test_indeksleri)` **küçüğü iyi** bir
    sayı vermelidir (Brier, log kaybı). Aramanın kendisi modelden habersizdir
    — `agac.py` de, ileride başka bir modül de aynı gövdeyi kullanabilir.

    Katlayıcı yeterli sezon taşımıyorsa arama **yapılmaz** ve `varsayilan`
    döner. Sessizce tek katla aramak, ayarın yapıldığı yanılsamasını
    üretirdi; burada niçin yapılmadığı `sebep` alanında yazar.

    Beraberlikte **listedeki ilk aday** kazanır. Sıra bilinçlidir: aday
    listeleri basitten karmaşığa yazılır, yani eşitlikte daha az kapasiteli
    model seçilir (Occam, ve aşırı uyuma karşı ucuz bir savunma).
    """
    if not adaylar:
        raise ValueError("aday listesi bos")
    if not katlayici.yeterli():
        return {"parametreler": varsayilan or dict(adaylar[0]),
                "arandi": False, "n_kat": katlayici.get_n_splits(),
                "sebep": f"ic halka {katlayici.en_az_kat} sezon istiyor, "
                         f"{katlayici.get_n_splits()} var",
                "skorlar": []}

    katlar = list(katlayici.split())
    skorlar: list[dict[str, Any]] = []
    for params in adaylar:
        degerler = [skorla(params, egitim, test) for egitim, test in katlar]
        gecerli = [v for v in degerler if v == v]  # NaN elenir
        skorlar.append({
            "parametreler": params,
            "skor": sum(gecerli) / len(gecerli) if gecerli else float("inf"),
            "n_kat": len(gecerli),
        })

    en_iyi = min(skorlar, key=lambda s: s["skor"])
    return {"parametreler": en_iyi["parametreler"], "arandi": True,
            "n_kat": len(katlar), "sebep": "", "skorlar": skorlar}
