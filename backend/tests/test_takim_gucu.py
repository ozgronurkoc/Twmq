"""Takım bazlı istatistik — **küçültmenin** denetimi.

**En kritik test `test_az_macli_takim_lig_ortalamasina_cekilir`.** §7'nin
yasağının sebebi buydu: *"216 takım, Süper Lig takımları bile 32 maç.
Çıkacak sayı güvenilir görünür ama gürültüdür."* Yasağı kaldıran şey
küçültmenin kendisi — az maçlı takımın sayısı **otomatik olarak** lig
ortalamasına çöker ve `kucultme` alanı bunu söyler.

İkincisi `test_kucultme_hicbir_zaman_asiri_duzeltmez`: küçültme faktörü
[0, 1] dışına çıkarsa tahmin ham ortalamanın **ötesine** geçer ve
"düzeltme" bir bozmaya döner.
"""
from __future__ import annotations

import pytest

from spor_toto.payloads import takimlar_payload
from spor_toto.takim_gucu import (
    EN_AZ_MAC,
    EN_AZ_TAKIM,
    OLCULER,
    PUAN,
    kucult,
    takim_tablosu,
)


def _mac(lig: str, ev: str, dep: str, hg: int, ag: int,
         sezon: str = "2425") -> dict:
    kod = "1" if hg > ag else ("2" if ag > hg else "0")
    return {"lig": lig, "ev": ev, "dep": dep, "ev_gol": hg, "dep_gol": ag,
            "kod": kod, "sezon": sezon}


def _lig(n_takim: int = 8, tur: int = 6, lig: str = "L1",
         sezon: str = "2425") -> list[dict]:
    """Kurgu lig: takım gücü indeksle artar, sonuç güçten türetilir."""
    import random

    rnd = random.Random(3)
    takimlar = [f"T{i}" for i in range(n_takim)]
    out = []
    for _ in range(tur):
        for i, ev in enumerate(takimlar):
            for j, dep in enumerate(takimlar):
                if i == j:
                    continue
                hg = rnd.randint(0, 1) + (i > j)
                ag = rnd.randint(0, 1) + (j > i)
                out.append(_mac(lig, ev, dep, hg, ag, sezon))
    return out


# ─── küçültmenin kendisi ──────────────────────────────────────────────────

def test_az_macli_takim_lig_ortalamasina_cekilir():
    """**Asıl bekçi.** §7'nin yasağını kaldıran şey tam olarak budur."""
    cok = [3.0] * 200
    az = [3.0] * 3
    r = kucult({"cok": cok, "az": az,
                "orta1": [1.0] * 50, "orta2": [0.0] * 50, "orta3": [1.0] * 50})
    mu = r["az"]["lig_ortalamasi"]
    # Ikisi de HAM olarak 3.0; kucultulmus hallerinde az macli olan
    # ortalamaya cok daha yakin olmali.
    assert r["az"]["ham"] == r["cok"]["ham"] == 3.0
    assert abs(r["az"]["kucultulmus"] - mu) < abs(r["cok"]["kucultulmus"] - mu)
    assert r["az"]["kucultme"] < r["cok"]["kucultme"]


def test_kucultme_hicbir_zaman_asiri_duzeltmez():
    """`B ∈ [0, 1]`: tahmin ham ile ortalama **arasında** kalmalı."""
    r = kucult({f"t{i}": [float(i % 4)] * (2 + 7 * i) for i in range(10)})
    for x in r.values():
        assert 0.0 <= x["kucultme"] <= 1.0
        alt, ust = sorted((x["ham"], x["lig_ortalamasi"]))
        assert alt - 1e-9 <= x["kucultulmus"] <= ust + 1e-9


def test_mac_sayisi_arttikca_kucultme_artar():
    r = kucult({f"t{i}": [float(i % 3)] * n
                for i, n in enumerate((5, 20, 80, 320, 1280))})
    b = [r[f"t{i}"]["kucultme"] for i in range(5)]
    assert b == sorted(b)


def test_gercek_fark_yoksa_hepsi_lig_ortalamasi():
    """Gözlenen yayılım gürültünün altındaysa `τ² = 0` ve herkes ortalamadır.

    `max(0, ...)` olmasaydı negatif bir `τ²` küçültmeyi **tersine**
    çevirirdi: tahmin ortalamanın öbür yanına geçerdi.
    """
    # Butun takimlar ayni dagilimdan: takimlar arasi gercek fark YOK.
    import random

    rnd = random.Random(7)
    r = kucult({f"t{i}": [rnd.choice([0.0, 1.0, 3.0]) for _ in range(30)]
                for i in range(12)})
    mu = next(iter(r.values()))["lig_ortalamasi"]
    for x in r.values():
        assert x["kucultme"] < 0.5
        assert abs(x["kucultulmus"] - mu) < abs(x["ham"] - mu) + 1e-12


def test_aralik_kucultulmus_tahmini_sariyor():
    r = kucult({f"t{i}": [float(i)] * (10 + i) for i in range(6)})
    for x in r.values():
        assert x["alt"] <= x["kucultulmus"] <= x["ust"]


def test_az_takimli_ligde_kucultme_yapilmaz_ve_gorunur():
    """Yayılım ölçülemiyorsa uydurma bir küçültme yapılmaz — `B = 1`."""
    r = kucult({"a": [1.0] * 10, "b": [2.0] * 10})
    assert len(r) < EN_AZ_TAKIM
    for x in r.values():
        assert x["kucultme"] == 1.0
        assert x["kucultulmus"] == x["ham"]


def test_bos_girdi_cokmez():
    assert kucult({}) == {}
    assert kucult({"a": []}) == {}


# ─── tablo ────────────────────────────────────────────────────────────────

def test_tablo_uc_olcuyu_de_tasiyor():
    t = takim_tablosu(_lig())
    satir = t["ligler"][0]["takimlar"][0]
    for ad, _ in OLCULER:
        assert set(satir[ad]) >= {"ham", "n", "kucultulmus", "kucultme",
                                  "alt", "ust", "lig_ortalamasi"}


def test_her_mac_iki_satir_uretir():
    """Ev ve deplasman ayrı ayrı sayılmalı; biri düşerse tablo yarım kalır."""
    maclar = _lig(n_takim=4, tur=2)
    t = takim_tablosu(maclar)
    toplam = sum(x["n"] for x in t["ligler"][0]["takimlar"])
    assert toplam == 2 * len(maclar)


def test_puan_olcegi_lig_tablosu():
    """Burada ölçek 3/1/0 — `takim._PUAN`ın ±1/0'ından **bilerek** farklı."""
    assert PUAN == {"1": 3.0, "0": 1.0, "2": 0.0}
    t = takim_tablosu([_mac("L", "a", "b", 2, 0)] * 10
                      + [_mac("L", "c", "d", 0, 2)] * 10
                      + [_mac("L", "e", "f", 1, 1)] * 10
                      + [_mac("L", "g", "h", 1, 1)] * 10)
    satirlar = {x["takim"]: x for x in t["ligler"][0]["takimlar"]}
    assert satirlar["a"]["puan"]["ham"] == 3.0
    assert satirlar["b"]["puan"]["ham"] == 0.0
    assert satirlar["e"]["puan"]["ham"] == 1.0


def test_goller_simetrik():
    t = takim_tablosu([_mac("L", "a", "b", 3, 1)] * 8
                      + [_mac("L", "c", "d", 1, 1)] * 8
                      + [_mac("L", "e", "f", 0, 2)] * 8
                      + [_mac("L", "g", "h", 2, 2)] * 8)
    s = {x["takim"]: x for x in t["ligler"][0]["takimlar"]}
    assert s["a"]["gol_at"]["ham"] == 3.0 and s["a"]["gol_ye"]["ham"] == 1.0
    assert s["b"]["gol_at"]["ham"] == 1.0 and s["b"]["gol_ye"]["ham"] == 3.0


def test_lig_suzgeci_sayilari_degistirmez():
    """`lig` **çıktıyı** süzer, hesabı değil — küçültme zaten lig içinde."""
    maclar = _lig(lig="L1") + _lig(lig="L2", n_takim=6, tur=4)
    hepsi = takim_tablosu(maclar)
    suzulmus = takim_tablosu(maclar, lig="L1")
    l1 = next(x for x in hepsi["ligler"] if x["lig"] == "L1")
    assert [x["lig"] for x in suzulmus["ligler"]] == ["L1"]
    assert suzulmus["ligler"][0]["takimlar"] == l1["takimlar"]


def test_ligler_birbirine_karismiyor():
    """Küçültme lig içinde: bir ligin ortalaması ötekini çekmemeli."""
    maclar = ([_mac("GUCLU", f"a{i}", f"b{i}", 4, 0) for i in range(6)] * 6
              + [_mac("ZAYIF", f"c{i}", f"d{i}", 0, 0) for i in range(6)] * 6)
    t = takim_tablosu(maclar)
    ort = {g["lig"]: g["takimlar"][0]["gol_at"]["lig_ortalamasi"]
           for g in t["ligler"]}
    assert ort["GUCLU"] > ort["ZAYIF"]


def test_sezon_suzgeci_sayilari_degistirir():
    """`sezon` **girdiyi** süzer: `n` düşer, küçültme artar — istenen budur."""
    maclar = _lig(sezon="2324") + _lig(sezon="2425")
    hepsi = takim_tablosu(maclar)["ligler"][0]["takimlar"][0]
    tek = takim_tablosu(maclar, sezon="2425")["ligler"][0]["takimlar"][0]
    assert tek["n"] < hepsi["n"]
    assert tek["puan"]["kucultme"] < hepsi["puan"]["kucultme"]


def test_en_az_mac_altindaki_takim_tabloya_girmez():
    maclar = _lig(n_takim=6, tur=4)
    maclar.append(_mac("L1", "YENI", "T0", 1, 0))
    t = takim_tablosu(maclar)
    adlar = {x["takim"] for x in t["ligler"][0]["takimlar"]}
    assert "YENI" not in adlar
    assert all(x["n"] >= EN_AZ_MAC for x in t["ligler"][0]["takimlar"])


def test_siralama_puana_gore_azalan():
    t = takim_tablosu(_lig())
    puanlar = [x["puan"]["kucultulmus"] for x in t["ligler"][0]["takimlar"]]
    assert puanlar == sorted(puanlar, reverse=True)


def test_eksik_gol_ya_da_kod_satiri_atlanir():
    """Yarım satır sessizce sıfır sayılmaz — hiç sayılmaz."""
    maclar = _lig(n_takim=6, tur=4)
    bozuk = dict(maclar[0])
    bozuk["ev_gol"] = None
    t_bozuk = takim_tablosu([*maclar, bozuk])
    t = takim_tablosu(maclar)
    assert t_bozuk["ligler"][0]["takimlar"] == t["ligler"][0]["takimlar"]


def test_bos_korpusta_cokmez():
    t = takim_tablosu([])
    assert t["ligler"] == [] and t["kural"]


# ─── gövde sözleşmesi ─────────────────────────────────────────────────────

def test_govde_n_ve_kucultmeyi_tasimak_zorunda():
    """**Ürün kuralı.** Bu iki alan olmadan §7'nin itirazı aynen geri gelir."""
    t = takimlar_payload()
    if not t["ligler"]:
        pytest.skip("korpus yok")
    for grup in t["ligler"]:
        for x in grup["takimlar"]:
            assert x["n"] >= EN_AZ_MAC
            for ad, _ in OLCULER:
                assert 0.0 <= x[ad]["kucultme"] <= 1.0


def test_govde_kurali_yaziyor():
    t = takimlar_payload()
    assert "KUCULTULMUS" in t["kural"]
    assert {o["alan"] for o in t["olculer"]} == {ad for ad, _ in OLCULER}


def test_gercek_korpusta_az_macli_takim_daha_temkinli():
    """Gerçek veride de küçültme yönü doğru: az maçlı = düşük `kucultme`."""
    t = takimlar_payload()
    satirlar = [x for g in t["ligler"] for x in g["takimlar"]]
    if len(satirlar) < 50:
        pytest.skip("korpus yok ya da cok kucuk")
    satirlar.sort(key=lambda x: x["n"])
    az = satirlar[:20]
    cok = satirlar[-20:]
    assert (sum(x["puan"]["kucultme"] for x in az) / len(az)
            < sum(x["puan"]["kucultme"] for x in cok) / len(cok))
