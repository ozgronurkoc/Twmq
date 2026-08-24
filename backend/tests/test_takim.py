"""H2H ve seri özelliklerinin denetimi.

İki bekçi ötekilerden önemli ve ikisi de aynı şeyi kovalıyor: bir maçın
kendi sonucu kendi özelliğine giremez. `egitim._form_tablosu` için yazılan
disiplinin aynısı (`test_form_gelecegi_gormez`), burada iki kez.

Üçüncü grup testler **tanımın kendisini** sabitliyor: serinin beraberlikte
sıfırlanması ve H2H'nin sahaya göre işaret çevirmesi. İkisi de sessizce
ters yazılabilecek şeyler ve ters yazılırlarsa ölçüm hâlâ "çalışır", yalnızca
başka bir şeyi ölçer.
"""
from __future__ import annotations

import pytest

from spor_toto.takim import (
    H2H_EN_AZ,
    H2H_PENCERE,
    SERI_TAVANI,
    h2h_tablosu,
    seri_tablosu,
)


def _mac(gun: int, ev: str, dep: str, kod: str) -> dict:
    return {"tarih": f"2024-{1 + gun // 28:02d}-{1 + gun % 28:02d}",
            "lig": "E0", "ev": ev, "dep": dep, "kod": kod}


# ─── H2H ──────────────────────────────────────────────────────────────────

def test_h2h_en_az_esigine_kadar_kapali():
    maclar = [_mac(g, "A", "B", "1") for g in range(H2H_EN_AZ)]
    tablo = h2h_tablosu(maclar)
    for kayit in tablo:
        assert kayit["h2h_var"] is False
        assert kayit["h2h_farki"] == 0.0


def test_h2h_esikten_sonra_aciliyor():
    maclar = [_mac(g, "A", "B", "1") for g in range(H2H_EN_AZ + 2)]
    tablo = h2h_tablosu(maclar)
    assert tablo[H2H_EN_AZ]["h2h_var"] is True


def test_h2h_hep_kazanan_tarafta_bir():
    """A, B'yi hep yenmişse A ev sahibiyken H2H farkı +1 olmalı."""
    maclar = [_mac(g, "A", "B", "1") for g in range(6)]
    assert h2h_tablosu(maclar)[-1]["h2h_farki"] == pytest.approx(1.0)


def test_h2h_hep_kaybeden_tarafta_eksi_bir():
    maclar = [_mac(g, "A", "B", "2") for g in range(6)]
    assert h2h_tablosu(maclar)[-1]["h2h_farki"] == pytest.approx(-1.0)


def test_h2h_hep_beraberlikte_sifir():
    maclar = [_mac(g, "A", "B", "0") for g in range(6)]
    assert h2h_tablosu(maclar)[-1]["h2h_farki"] == pytest.approx(0.0)


def test_h2h_saha_degisince_isaret_donuyor():
    """**Tanımın bekçisi.** Geçmiş puan, o maçın ev sahibi açısından yazılı.

    A ev sahibiyken hep kazanmışsa, B ev sahibi olduğunda H2H farkı B'nin
    aleyhine (−1) olmalı. İşaret çevirme unutulursa özellik "geçmişte kim
    kazandı" yerine "geçmişte ev sahibi kazandı mı" ölçer — ki o zaten ev
    avantajıdır ve modelde ayrıca var.
    """
    maclar = [_mac(g, "A", "B", "1") for g in range(5)]
    maclar.append(_mac(9, "B", "A", "1"))
    tablo = h2h_tablosu(maclar)
    assert tablo[-1]["h2h_var"] is True
    assert tablo[-1]["h2h_farki"] == pytest.approx(-1.0)


def test_h2h_penceresi_eskiyi_disarida_birakir():
    """Pencere `H2H_PENCERE` ile sınırlı — daha eskisi sayılmamalı."""
    # Son macin GECMISINDE tam `H2H_PENCERE` galibiyet olmali; bu yuzden
    # yeni blok bir fazla mac tasiyor.
    eski = [_mac(g, "A", "B", "2") for g in range(H2H_PENCERE)]
    yeni = [_mac(H2H_PENCERE + g, "A", "B", "1") for g in range(H2H_PENCERE + 1)]
    tablo = h2h_tablosu(eski + yeni)
    assert tablo[-1]["h2h_farki"] == pytest.approx(1.0)


def test_h2h_gelecegi_gormez():
    """**Asıl bekçi.** Son maçın kendi sonucu kendi H2H farkına giremez.

    Kurgu: A önce dört kez kaybediyor, sonra kazanıyor. Son maçın farkı
    yalnızca ÖNCEKİ dört maçı görmeli, yani −1 olmalı.
    """
    maclar = [_mac(g, "A", "B", "2") for g in range(4)]
    maclar.append(_mac(9, "A", "B", "1"))
    tablo = h2h_tablosu(maclar)
    assert tablo[-1]["h2h_var"] is True
    assert tablo[-1]["h2h_farki"] == pytest.approx(-1.0)


def test_h2h_farkli_eslesmeler_karismaz():
    maclar = [_mac(g, "A", "B", "1") for g in range(5)]
    maclar += [_mac(10 + g, "A", "C", "2") for g in range(5)]
    tablo = h2h_tablosu(maclar)
    assert tablo[4]["h2h_farki"] > 0
    assert tablo[-1]["h2h_farki"] < 0


def test_h2h_gecersiz_kod_gecmise_girmez():
    maclar = [_mac(g, "A", "B", "X") for g in range(6)]
    assert all(k["h2h_var"] is False for k in h2h_tablosu(maclar))


def test_h2h_arali_sinirlarda():
    maclar = [_mac(g, "A", "B", "102"[g % 3]) for g in range(40)]
    for kayit in h2h_tablosu(maclar):
        assert -1.0 <= kayit["h2h_farki"] <= 1.0


def test_h2h_bos_girdiyle_patlamaz():
    assert h2h_tablosu([]) == []


# ─── seri ─────────────────────────────────────────────────────────────────

def test_seri_ilk_macta_sifir():
    tablo = seri_tablosu([_mac(0, "A", "B", "1")])
    assert tablo[0] == {"seri_ev": 0, "seri_dep": 0, "seri_farki": 0.0}


def test_seri_galibiyetle_buyur_maglubiyetle_kucultur():
    maclar = [_mac(g, "A", f"R{g}", "1") for g in range(4)]
    tablo = seri_tablosu(maclar)
    assert [k["seri_ev"] for k in tablo] == [0, 1, 2, 3]


def test_seri_deplasman_kaybedince_negatif():
    maclar = [_mac(g, f"R{g}", "A", "1") for g in range(4)]
    tablo = seri_tablosu(maclar)
    assert [k["seri_dep"] for k in tablo] == [0, -1, -2, -3]


def test_seri_beraberlikte_sifirlanir():
    """**Tanımın bekçisi.** Beraberlik seriyi sürdürmez, sıfırlar.

    "üç maçtır kaybetmiyor" ile "üç maçtır kazanıyor" farklı iddialardır ve
    ölçülen ikincisidir. Beraberlik seriyi sürdürseydi özellik `form`un
    gürültülü bir kopyası olurdu.
    """
    maclar = [_mac(0, "A", "X", "1"), _mac(1, "A", "Y", "1"),
              _mac(2, "A", "Z", "0"), _mac(3, "A", "W", "1")]
    tablo = seri_tablosu(maclar)
    assert [k["seri_ev"] for k in tablo] == [0, 1, 2, 0]


def test_seri_yon_degisince_bastan_baslar():
    maclar = [_mac(0, "A", "X", "1"), _mac(1, "A", "Y", "1"),
              _mac(2, "A", "Z", "2"), _mac(3, "A", "W", "1")]
    tablo = seri_tablosu(maclar)
    assert [k["seri_ev"] for k in tablo] == [0, 1, 2, -1]


def test_seri_tavanda_kirpilir():
    maclar = [_mac(g, "A", f"R{g}", "1") for g in range(SERI_TAVANI + 6)]
    tablo = seri_tablosu(maclar)
    assert max(k["seri_ev"] for k in tablo) == SERI_TAVANI


def test_seri_farki_olcekli_ve_sinirli():
    maclar = [_mac(g, "A", "B", "1") for g in range(SERI_TAVANI + 6)]
    for kayit in seri_tablosu(maclar):
        assert -1.0 <= kayit["seri_farki"] <= 1.0
    # A hep kazanip B hep kaybettiginde fark tavana dayanmali.
    assert seri_tablosu(maclar)[-1]["seri_farki"] == pytest.approx(1.0)


def test_seri_gelecegi_gormez():
    """**Asıl bekçi.** Son maçın kendi sonucu kendi serisine giremez."""
    maclar = [_mac(g, "A", f"R{g}", "2") for g in range(3)]
    maclar.append(_mac(9, "A", "R9", "1"))
    tablo = seri_tablosu(maclar)
    assert tablo[-1]["seri_ev"] == -3


def test_seri_gecersiz_kod_seriyi_bozmaz():
    maclar = [_mac(0, "A", "X", "1"), _mac(1, "A", "Y", "?"),
              _mac(2, "A", "Z", "1")]
    tablo = seri_tablosu(maclar)
    assert tablo[-1]["seri_ev"] == 1


def test_seri_bos_girdiyle_patlamaz():
    assert seri_tablosu([]) == []


def test_tablolar_girdiyle_ayni_uzunlukta():
    maclar = [_mac(g, "A", "B", "102"[g % 3]) for g in range(20)]
    assert len(h2h_tablosu(maclar)) == len(maclar)
    assert len(seri_tablosu(maclar)) == len(maclar)


def test_tablolar_deterministik():
    maclar = [_mac(g, f"T{g % 4}", f"T{(g + 1) % 4}", "102"[g % 3])
              for g in range(30)]
    assert h2h_tablosu(maclar) == h2h_tablosu(maclar)
    assert seri_tablosu(maclar) == seri_tablosu(maclar)


# ─── korpus üzerinde ──────────────────────────────────────────────────────

def test_korpusta_kapsama_ve_araliklar():
    """Gerçek veride kapsama ve aralıklar makul olmalı.

    H2H kapsaması **bilerek düşük**: dört sezonluk ve 22 ligli bir korpusta
    çoğu eşleşme `H2H_EN_AZ` karşılaşmayı bulamıyor. Sayı burada yazılı
    duruyor ki ölçümün gücü okunurken hatırlansın.
    """
    from spor_toto.egitim import korpus_haftalari

    ozellikler = [o for w in korpus_haftalari() for o in w["ozellikler"]]
    h2h = [o for o in ozellikler if o["h2h_var"]]
    assert 0.30 < len(h2h) / len(ozellikler) < 0.60

    for o in ozellikler:
        assert -1.0 <= o["h2h_farki"] <= 1.0
        assert -1.0 <= o["seri_farki"] <= 1.0
        assert abs(o["seri_ev"]) <= SERI_TAVANI
        assert abs(o["seri_dep"]) <= SERI_TAVANI

    # H2H simetrik bir olcudur: butun korpusta ortalamasi sifira yakin
    # olmali. Sapma varsa isaret cevirme bozuktur.
    ort = sum(o["h2h_farki"] for o in h2h) / len(h2h)
    assert abs(ort) < 0.05
