"""Elo — rakip gücüne göre düzeltilmiş takım gücü (Faz 3.2).

`DIS_INCELEME.md` §8 bu özelliği *"denenebilir ama denenmedi"* diye kayda
geçirmişti ve gerekçesi bir tahsis kararıydı, bir imkânsızlık değil. Faz 1'in
iki ölçümü o kararı tersine çevirdi:

* **§3.23** kalibrasyon ekseninin tavanının **0,00042** olduğunu ölçtü —
  yeniden kalibrasyon tarafında alınacak yol kalmadı;
* **§3.24** öğrenme eğrisinin **piyasaya yetişmeden düzleştiğini** ölçtü —
  aynı türden daha çok satır bu farkı kapatmıyor.

İkisi birlikte tek bir şey söylüyor: eksik olan **sütun**. Elo, projenin
kendi belgelerinde en çok işaret edilen eksik sütundur ve gerekçesi kayıtlı:

> *"`kalibre_form` **ham** formdu, rakip gücüne göre düzeltilmemişti — Elo
> tam o eksiği kapatan standart sinyaldir. Yani 'form denendi' demek 'Elo
> denendi' demek değildir."*

─── Neden Elo, formun ölçemediği ne var ──────────────────────────────────

`_form_tablosu` son 5 maçın **puan ortalamasını** alır. O ortalama kiminle
oynandığını bilmez: küme düşme hattındaki üç takımı yenen 9 puan ile
şampiyonluk yarışındaki üçünü yenen 9 puan aynı görünür. Elo tam bu farkı
taşır — her galibiyet rakibin o anki gücüne göre değerlenir ve puan
kaybeden taraftan alınır.

Ayrıca form bir **pencere**dir (5 maç); Elo bir **birikimdir** ve sezon
başında geçen sezonun bilgisini taşır (bkz. `SEZON_TASIMA`).

─── Parametreler: hepsi dışarıdan, hiçbiri uydurulmadı ───────────────────

Bu modülün her sabiti **yayınlanmış standart değerlerden** alındı ve
ölçüm sonucuna **bakılmadan** sabitlendi. Gerekçe `recalibrate.L2` ile
aynıdır: bir parametre hold-out'a bakılarak seçilirse hold-out'un anlamı
kalmaz. Elo'nun bu projede bir avantajı var — parametrelerini uydurmaya
gerek yok, çünkü futbol için kırk yıldır yayınlanmış değerleri var.

─── Sızıntı disiplini ────────────────────────────────────────────────────

`egitim._form_tablosu` ile **birebir aynı**: maçlar kronolojik gezilir,
puan **önce okunur, sonra** maç işlenir. Bir maçın kendi sonucu asla kendi
Elo farkına giremez. Bekçi: `tests/test_elo.py::test_elo_gelecegi_gormez`.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

#: Başlangıç puanı. Ölçek keyfîdir ve yalnızca farklar anlamlıdır; 1500
#: satranç geleneğinden gelen alışıldık değerdir.
BASLANGIC = 1500.0

#: K katsayısı — bir maçın puanı ne kadar oynatabileceği. World Football Elo
#: Ratings lig maçları için 20 kullanır. Büyük K son maçlara aşırı tepki
#: verir, küçük K değişimi geç görür.
K = 20.0

#: Ev sahibi avantajı, puan cinsinden. Yayınlanmış futbol Elo
#: uygulamalarında 60–100 aralığında; ortasına yakın bir değer alındı.
#: **Veriden ölçülmedi** — ölçülseydi eğitim setine bakmış olurduk.
EV_AVANTAJI = 65.0

#: Beklenen skor lojistiğinin ölçeği. 400, Elo'nun tanımının parçasıdır:
#: 400 puan fark ≈ %90 kazanma beklentisi.
OLCEK = 400.0

#: Sezonlar arası taşıma. Takımlar sezon başında ortalamaya doğru çekilir
#: (kadro değişir, lig değişir). 0,75 futbol Elo uygulamalarında yaygın.
#: 1,0 olsaydı bir takımın on yıl önceki formu bugüne taşınırdı; 0,0
#: olsaydı Elo'nun formdan farkı kalmazdı.
SEZON_TASIMA = 0.75

#: Bir takımın farkının "gerçek" sayılması için gereken en az maç. Altında
#: puan hâlâ başlangıç değerinin gölgesindedir ve fark gürültüdür.
#: `form_var` ile aynı mantık: bilgisizlik gizlenmez, işaretlenir.
EN_AZ_MAC = 5


def beklenen(fark: float) -> float:
    """Ev sahibinin beklenen skoru — `fark` ev avantajı DAHİL puan farkı.

    Beklenen skor [0, 1] arasıdır ve galibiyet 1, beraberlik 0,5, mağlubiyet
    0 sayılır. Yani bu bir "kazanma olasılığı" **değildir**; beraberliği
    yarım galibiyet sayan bir beklentidir ve Elo'nun beraberliği ayrı bir
    sonuç olarak modellemediği yer burasıdır.
    """
    return 1.0 / (1.0 + 10.0 ** (-fark / OLCEK))


def gol_carpani(gol_farki: int) -> float:
    """Gol farkına göre K çarpanı — World Football Elo Ratings formülü.

    1 farkla kazanmak ile 5 farkla kazanmak aynı bilgi değildir; ama fark
    büyüdükçe getirisi azalmalıdır, yoksa tek bir 7-0 bütün puanı taşır.

        fark 0-1 → 1,00    fark 2 → 1,50    fark m≥3 → (11+m)/8

    Doğrusal değil, doygun: 3 farkta 1,75, 5 farkta 2,00.
    """
    m = abs(gol_farki)
    if m <= 1:
        return 1.0
    if m == 2:
        return 1.5
    return (11.0 + m) / 8.0


class EloDefteri:
    """Takım puanlarını tutan defter — **okuma ve güncelleme ayrı**.

    Ayrım süs değil, sızıntıya karşı tek savunma: çağıran önce `fark`ı
    okur, sonra `guncelle`i çağırır. `egitim._form_tablosu`nun sırasıyla
    birebir aynı desendir.
    """

    def __init__(self) -> None:
        self._puan: dict[str, float] = {}
        self._mac: dict[str, int] = {}
        self._sezon: str | None = None

    # -- okuma ---------------------------------------------------------------

    def puan(self, takim: str) -> float:
        return self._puan.get(takim, BASLANGIC)

    def mac_sayisi(self, takim: str) -> int:
        return self._mac.get(takim, 0)

    def fark(self, ev: str, dep: str) -> float:
        """Ev avantajı dâhil ham puan farkı. Pozitif = ev lehine."""
        return self.puan(ev) + EV_AVANTAJI - self.puan(dep)

    def yeterli(self, ev: str, dep: str) -> bool:
        """İki takımın da `EN_AZ_MAC` maçı var mı — yoksa fark gürültüdür."""
        return (self.mac_sayisi(ev) >= EN_AZ_MAC
                and self.mac_sayisi(dep) >= EN_AZ_MAC)

    # -- güncelleme ----------------------------------------------------------

    def sezon_basi(self, sezon: str) -> None:
        """Sezon değiştiyse puanları ortalamaya doğru çek.

        Çekim **ortalamaya** yapılır, `BASLANGIC`a değil: lig seviyeleri
        arasındaki gerçek fark korunur, takım içi dalgalanma söner.
        """
        if sezon == self._sezon:
            return
        self._sezon = sezon
        if not self._puan:
            return
        ortalama = sum(self._puan.values()) / len(self._puan)
        for takim, p in self._puan.items():
            self._puan[takim] = ortalama + SEZON_TASIMA * (p - ortalama)

    def guncelle(self, ev: str, dep: str, kod: str, gol_farki: int) -> None:
        """Maç sonucunu işle. **`fark` okunduktan sonra** çağrılmalı."""
        gercek = {"1": 1.0, "0": 0.5, "2": 0.0}.get(kod)
        if gercek is None:
            return
        bek = beklenen(self.fark(ev, dep))
        degisim = K * gol_carpani(gol_farki) * (gercek - bek)
        self._puan[ev] = self.puan(ev) + degisim
        self._puan[dep] = self.puan(dep) - degisim
        self._mac[ev] = self.mac_sayisi(ev) + 1
        self._mac[dep] = self.mac_sayisi(dep) + 1


def elo_tablosu(satirlar: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Her maç için, **o maçtan önceki** maçlardan hesaplanmış Elo farkı.

    `egitim._form_tablosu` ile aynı sıralama ve aynı sıra: oku, sonra işle.
    Dönen kayıtlar girdiyle **aynı indekste**dir.

    `elo_var=False` olan maçta `elo_farki` nötr 0'dır — "bilinmiyor" ile
    "denk" aynı davranışa düşer, çünkü ikisinde de söylenecek bir şey yok
    (`form_var` ile birebir aynı kural).
    """
    sirali = sorted(range(len(satirlar)),
                    key=lambda i: (satirlar[i]["tarih"], satirlar[i]["lig"],
                                   satirlar[i]["ev"]))
    defter = EloDefteri()
    out: list[dict[str, Any]] = [
        {"elo_var": False, "elo_farki": 0.0} for _ in satirlar
    ]

    for i in sirali:
        r = satirlar[i]
        sezon = r.get("sezon")
        if sezon:
            defter.sezon_basi(str(sezon))

        # --- ONCE OKU ---
        if defter.yeterli(r["ev"], r["dep"]):
            out[i] = {"elo_var": True, "elo_farki": defter.fark(r["ev"], r["dep"])}

        # --- SONRA ISLE ---
        ev_gol, dep_gol = r.get("ev_gol"), r.get("dep_gol")
        gol_farki = int(ev_gol - dep_gol) if (ev_gol is not None
                                              and dep_gol is not None) else 0
        defter.guncelle(r["ev"], r["dep"], r["kod"], gol_farki)

    return out
