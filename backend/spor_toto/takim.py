"""H2H ve seriler — iki takım arasındaki geçmiş ve anlık gidişat (Faz 3.3).

İki özellik, iki ayrı gerekçe:

**H2H** (`DIS_INCELEME.md` §8) Elo'nun yanında *"denenebilir ama denenmedi"*
diye kayda geçirilmişti. Elo denendi ve geçmedi (§3.27); H2H açık kaldı.
Taşıdığı iddia şudur: *bazı eşleşmeler genel güç sıralamasının söylemediği
bir şey taşır* — "X takımı Y'ye yaramaz" folklorunun ölçülebilir hâli. Elo
ve Dixon-Coles bunu **tanım gereği göremez**: ikisi de her takıma tek bir
güç atar ve eşleşmeye özel bir terim taşımaz.

**Seriler** AlphaPy'ın `sport_flow.get_streak`'inin karşılığıdır
(`DIS_INCELEME_ALPHAPY.md` §7'de *"türetilebilir, denenmedi"* satırı).
Formdan farkı incedir ama gerçektir: `_form_tablosu` son 5 maçın **puan
ortalamasını** alır — 3 galibiyet + 2 mağlubiyet ile 5 beraberlik aynı
ortalamayı verebilir. Seri **ardışıklığı** ölçer ve momentum iddiasının
doğrudan karşılığıdır.

─── İkisi de aynı disipline tabi ─────────────────────────────────────────

`egitim._form_tablosu` ve `elo.elo_tablosu` ile birebir aynı sıra:
kronolojik gez, değeri **önce oku, sonra** maçı geçmişe ekle. Bekçiler:
`tests/test_takim.py::test_h2h_gelecegi_gormez` ve
`::test_seri_gelecegi_gormez`.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

#: H2H penceresi — son kaç karşılaşmaya bakılır. `DIS_INCELEME.md` §8
#: "son 5 karşılaşma" diye yazmıştı; sayı oradan geliyor, veriden değil.
H2H_PENCERE = 5

#: H2H'nin "gerçek" sayılması için gereken en az karşılaşma. Tek bir maçtan
#: eşleşmeye özel bir eğilim okumak gürültüyü bilgi sanmaktır.
H2H_EN_AZ = 3

#: Serinin üst sınırı. 10 maçlık bir galibiyet serisi ile 20 maçlık olan
#: arasındaki fark, modelin öğrenebileceğinden fazla gürültü taşır; tavan
#: `egitim.DINLENME_TAVANI` ile aynı gerekçeyle var.
SERI_TAVANI = 8

#: Maç sonucunun ev sahibi açısından **üstünlük** değeri.
#:
#: Bilerek 3/1/0 DEĞİL. İlk sürüm lig tablosu puanlamasını kullanıyordu ve
#: `test_h2h_hep_beraberlikte_sifir` onu düşürdü: 3/1/0 ölçeğinde bir
#: beraberlik [−1, 1] aralığına **−1/3** olarak düşüyor, yani "berabere
#: kaldılar" cümlesi "ev sahibi geride" diye okunuyordu.
#:
#: 3/1/0 bir *sıralama* geleneğidir ve galibiyeti beraberliğe göre kasten
#: fazla ödüllendirir. H2H'nin sorduğu şey sıralama değil **üstünlük**:
#: "geçmişte hangisi kazandı?" Beraberliğin doğru karşılığı sıfırdır.
_PUAN: dict[str, float] = {"1": 1.0, "0": 0.0, "2": -1.0}


def _cift(a: str, b: str) -> tuple[str, str]:
    """Eşleşme anahtarı — ev/deplasman ayrımından bağımsız."""
    return (a, b) if a <= b else (b, a)


def h2h_tablosu(satirlar: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Her maç için, **o maçtan önceki** karşılaşmalardan H2H farkı.

    `h2h_farki`, son `H2H_PENCERE` karşılaşmada **bu maçın ev sahibinin**
    maç başına üstünlüğüdür: galibiyet +1, beraberlik 0, mağlubiyet −1'in
    ortalaması. Aralık [−1, +1]; pozitif = ev sahibi geçmiş karşılaşmalarda
    üstün. Ölçek neden 3/1/0 değil: `_PUAN`.

    ─── Saha bilerek yok sayılıyor ───────────────────────────────────────

    Karşılaşmalar sahadan bağımsız toplanır ve puan **o maçın** ev sahibinin
    açısından yazılır. Alternatif — yalnızca aynı sahadaki karşılaşmalara
    bakmak — pencereyi yarıya indirirdi ve `H2H_EN_AZ` eşiğini çoğu
    eşleşmede hiç geçemezdi. Bu bir ödünç: saha etkisi H2H'den düşmüyor,
    ama zaten `EV_AVANTAJI` ve `γ` onu ayrıca taşıyor.

    Ölçek `_PUAN`da yazılı ve **3/1/0 DEĞİL**. Sebebi burada görünür:
    hep berabere kalmış bir eşleşme sıfır vermeli, "ev sahibi geride"
    değil. Dört maç, dördü de beraberlik::

        >>> maclar = [{"tarih": f"2024-01-0{i}", "lig": "T1",
        ...            "ev": "A", "dep": "B", "kod": "0"} for i in range(1, 5)]
        >>> tablo = h2h_tablosu(maclar)
        >>> tablo[-1]["h2h_farki"]
        0.0

    `H2H_EN_AZ` altındaki karşılaşma "gerçek" sayılmaz — tek bir maçtan
    eşleşmeye özel bir eğilim okumak gürültüyü bilgi sanmaktır::

        >>> tablo[0]["h2h_var"], tablo[-1]["h2h_var"]
        (False, True)

    Ev sahibi geçmişte üstünse işaret pozitiftir::

        >>> galip = [{"tarih": f"2024-01-0{i}", "lig": "T1",
        ...           "ev": "A", "dep": "B", "kod": "1"} for i in range(1, 5)]
        >>> h2h_tablosu(galip)[-1]["h2h_farki"]
        1.0
    """
    sirali = sorted(range(len(satirlar)),
                    key=lambda i: (satirlar[i]["tarih"], satirlar[i]["lig"],
                                   satirlar[i]["ev"]))
    gecmis: dict[tuple[str, str], list[tuple[str, float]]] = {}
    out: list[dict[str, Any]] = [
        {"h2h_var": False, "h2h_farki": 0.0} for _ in satirlar
    ]

    for i in sirali:
        r = satirlar[i]
        ev, dep = r["ev"], r["dep"]
        kayit = gecmis.get(_cift(ev, dep), [])

        # --- ONCE OKU ---
        if len(kayit) >= H2H_EN_AZ:
            son = kayit[-H2H_PENCERE:]
            n = float(len(son))
            # Kayitta ustunluk, o macin EV SAHIBI acisindan yazili. Bu macin
            # ev sahibi oradaki ev sahibi degilse isaret cevrilir.
            out[i] = {
                "h2h_var": True,
                "h2h_farki": sum(v if t == ev else -v for t, v in son) / n,
            }

        # --- SONRA ISLE ---
        puan = _PUAN.get(r["kod"])
        if puan is None:
            continue
        gecmis.setdefault(_cift(ev, dep), []).append((ev, puan))

    return out


def seri_tablosu(satirlar: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Her takımın **o maçtan önceki** ardışık galibiyet/mağlubiyet serisi.

    `seri_ev` / `seri_dep` işaretli tam sayıdır: `+3` üç maçlık galibiyet
    serisi, `−2` iki maçlık mağlubiyet serisi, `0` seri yok (son maç
    beraberlik ya da hiç maç yok). `SERI_TAVANI` ile kırpılır.

    `seri_farki` ikisinin farkının **ölçekli** hâlidir ve `[-1, 1]`
    aralığındadır — `recalibrate` yön sütunları bu aralığı bekliyor.

    Beraberlik seriyi **sıfırlar**, sürdürmez. Alternatif (beraberliği
    galibiyet serisinin parçası saymak) momentum iddiasını bulanıklaştırırdı:
    "üç maçtır kaybetmiyor" ile "üç maçtır kazanıyor" farklı iddialardır ve
    ölçülen ikincisidir.
    """
    sirali = sorted(range(len(satirlar)),
                    key=lambda i: (satirlar[i]["tarih"], satirlar[i]["lig"],
                                   satirlar[i]["ev"]))
    seri: dict[str, int] = {}
    out: list[dict[str, Any]] = [
        {"seri_ev": 0, "seri_dep": 0, "seri_farki": 0.0} for _ in satirlar
    ]

    for i in sirali:
        r = satirlar[i]
        ev, dep = r["ev"], r["dep"]

        # --- ONCE OKU ---
        s_ev = max(-SERI_TAVANI, min(SERI_TAVANI, seri.get(ev, 0)))
        s_dep = max(-SERI_TAVANI, min(SERI_TAVANI, seri.get(dep, 0)))
        out[i] = {
            "seri_ev": s_ev,
            "seri_dep": s_dep,
            "seri_farki": (s_ev - s_dep) / (2.0 * SERI_TAVANI),
        }

        # --- SONRA ISLE ---
        kod = r["kod"]
        if kod not in _PUAN:
            continue
        ev_sonuc = 1 if kod == "1" else (-1 if kod == "2" else 0)
        for takim, sonuc in ((ev, ev_sonuc), (dep, -ev_sonuc)):
            onceki = seri.get(takim, 0)
            if sonuc == 0:
                seri[takim] = 0
            elif onceki * sonuc > 0:
                seri[takim] = onceki + sonuc
            else:
                seri[takim] = sonuc

    return out
