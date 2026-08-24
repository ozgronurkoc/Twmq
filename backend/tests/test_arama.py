"""İç içe CV'nin denetimi — hiperparametre ayarının hold-out'u bozmaması.

**Asıl bekçi `test_ic_halka_dis_sezonu_gormez`.** Projenin hiperparametre
ayarını reddetmesinin gerekçesi tek halka olmasıydı; iki halka kurulunca
kısıt kalkar ama yalnızca iç halka gerçekten dış sezonu görmüyorsa. Bu
sızıntı sessizdir: model daha iyi bir sayı verir, kimse fark etmez ve
"ayarladık ama dürüst kaldık" cümlesi yalan olur.

`DIS_INCELEME_ALPHAPY.md` §4.1'de ölçülen şey tam bu boşluktu: AlphaPy
Pro'nun dış bölmesi kronolojik ama iç CV'si rastgele `StratifiedKFold`.
Bu dosya bizim tarafımızın öyle olmadığını kanıtlıyor.
"""
from __future__ import annotations

import numpy as np
import pytest

from spor_toto.arama import SezonKatlayici, izgara_ara


def _gruplar(n_sezon: int = 4, hafta: int = 5) -> list[str]:
    return [f"{20 + i}{21 + i}" for i in range(n_sezon) for _ in range(hafta)]


# ─── katlayıcı ────────────────────────────────────────────────────────────

def test_kat_sayisi_sezon_sayisi_kadar():
    k = SezonKatlayici(_gruplar(4))
    assert k.get_n_splits() == 4
    assert len(list(k.split())) == 4


def test_ic_halka_dis_sezonu_gormez():
    """**Asıl bekçi.** Test katındaki sezon eğitim katında HİÇ olmamalı."""
    gruplar = _gruplar(4)
    dizi = np.asarray(gruplar, dtype=object)
    for egitim, test in SezonKatlayici(gruplar).split():
        test_sezonlar = set(dizi[test])
        egitim_sezonlar = set(dizi[egitim])
        assert len(test_sezonlar) == 1
        assert not (test_sezonlar & egitim_sezonlar), (
            f"sizinti: {test_sezonlar} hem egitimde hem testte")


def test_katlar_butun_veriyi_ortuyor_ve_ortusmuyor():
    gruplar = _gruplar(4)
    goruldu: set[int] = set()
    for egitim, test in SezonKatlayici(gruplar).split():
        assert not (set(egitim.tolist()) & set(test.tolist()))
        assert len(egitim) + len(test) == len(gruplar)
        goruldu |= set(test.tolist())
    assert goruldu == set(range(len(gruplar)))


def test_tek_sezonda_yetersiz():
    """Tek sezonluk eğitim setinde sezon dışarıda bırakmalı ayar yapılamaz."""
    k = SezonKatlayici(["2324"] * 20)
    assert k.yeterli() is False


def test_iki_sezon_yeterli():
    assert SezonKatlayici(_gruplar(2)).yeterli() is True


def test_sira_gorulme_sirasi_alfabetik_degil():
    """Sezon etiketleri metin; alfabetik sıra kronolojik olmak zorunda değil.

    `dict.fromkeys` görülme sırasını korur. `sorted` kullanılsaydı
    "2021" < "2122" tesadüfen doğru olurdu ama etiket şeması değiştiğinde
    sessizce bozulurdu.
    """
    gruplar = ["b", "b", "a", "a", "c", "c"]
    k = SezonKatlayici(gruplar)
    dizi = np.asarray(gruplar, dtype=object)
    ilk_test = next(iter(k.split()))[1]
    assert set(dizi[ilk_test]) == {"b"}


def test_bos_grup_kati_uretmez():
    assert list(SezonKatlayici([]).split()) == []


# ─── ızgara araması ───────────────────────────────────────────────────────

def _skorla_fabrika(en_iyi: int):
    def skorla(params, egitim, test):
        return abs(params["k"] - en_iyi) + 0.0
    return skorla


def test_en_dusuk_skorlu_aday_secilir():
    adaylar = [{"k": 1}, {"k": 5}, {"k": 9}]
    s = izgara_ara(adaylar, SezonKatlayici(_gruplar(3)), _skorla_fabrika(5))
    assert s["parametreler"] == {"k": 5}
    assert s["arandi"] is True
    assert s["n_kat"] == 3


def test_esitlikte_ilk_aday_kazanir():
    """Aday listesi basitten karmaşığaya sıralı; eşitlikte az kapasite kazanır."""
    adaylar = [{"k": 1}, {"k": 2}]
    s = izgara_ara(adaylar, SezonKatlayici(_gruplar(3)),
                   lambda p, e, t: 0.5)
    assert s["parametreler"] == {"k": 1}


def test_yetersiz_katta_arama_yapilmaz_ve_sebep_yazilir():
    """Sessizce tek katla aramak, ayarın yapıldığı yanılsamasını üretirdi."""
    s = izgara_ara([{"k": 1}, {"k": 2}], SezonKatlayici(["2324"] * 10),
                   _skorla_fabrika(2), varsayilan={"k": 7})
    assert s["arandi"] is False
    assert s["parametreler"] == {"k": 7}
    assert "ic halka" in s["sebep"]
    assert s["skorlar"] == []


def test_skorlar_her_aday_icin_kayitli():
    adaylar = [{"k": 1}, {"k": 5}]
    s = izgara_ara(adaylar, SezonKatlayici(_gruplar(3)), _skorla_fabrika(5))
    assert len(s["skorlar"]) == len(adaylar)
    for kayit in s["skorlar"]:
        assert kayit["n_kat"] == 3
        assert "skor" in kayit


def test_nan_skor_kati_elenir_kosum_devam_eder():
    """Bir kat NaN verirse o kat düşer, aday tamamen elenmez."""
    def skorla(params, egitim, test):
        return float("nan") if egitim[0] == 5 else 0.1
    s = izgara_ara([{"k": 1}], SezonKatlayici(_gruplar(3)), skorla)
    assert s["skorlar"][0]["skor"] == pytest.approx(0.1)
    assert s["skorlar"][0]["n_kat"] < 3


def test_bos_aday_listesi_reddedilir():
    with pytest.raises(ValueError, match="aday listesi bos"):
        izgara_ara([], SezonKatlayici(_gruplar(3)), _skorla_fabrika(1))


def test_arama_deterministik():
    adaylar = [{"k": 1}, {"k": 5}, {"k": 9}]
    katlayici = SezonKatlayici(_gruplar(3))
    a = izgara_ara(adaylar, katlayici, _skorla_fabrika(5))
    b = izgara_ara(adaylar, katlayici, _skorla_fabrika(5))
    assert a["parametreler"] == b["parametreler"]
    assert [s["skor"] for s in a["skorlar"]] == [s["skor"] for s in b["skorlar"]]


def test_sklearn_araclariyla_uyumlu():
    """`cv=` bekleyen sklearn araçlarına doğrudan verilebilmeli.

    `SezonKatlayici`nın var olma sebebi bu: `RFECV`, `GridSearchCV` ve
    `CalibratedClassifierCV` rastgele katlar yerine sezon katlarıyla
    çalışabilsin diye.
    """
    sklearn = pytest.importorskip("sklearn")
    from sklearn.model_selection import cross_val_score

    gruplar = _gruplar(3, hafta=30)
    rnd = np.random.default_rng(0)
    X = rnd.normal(size=(len(gruplar), 3))
    y = (X[:, 0] > 0).astype(int)

    from sklearn.linear_model import LogisticRegression
    skorlar = cross_val_score(LogisticRegression(), X, y,
                              cv=SezonKatlayici(gruplar))
    assert len(skorlar) == 3
    assert sklearn is not None
