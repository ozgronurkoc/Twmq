"""Tahminci sözleşmesi ve referans tahminciler.

Projenin amacı maç sonucu tahminine döndüğünde ilk gereken şey model değil,
**modelin karşılaştırılacağı çizgidir.** Bu modül o çizgiyi tanımlar: bir
tahmincinin ne olduğunu (tek imza) ve neyi geçmesi gerektiğini (üç referans).

Sözleşme tektir:

    tahminci.egit(egitim_haftalari)   # gerekiyorsa; varsayılan no-op
    tahminci.tahmin(hafta)  → haftanın her maçı için {"1","0","2"} olasılığı

Maç sayısı haftadan okunur (`mac_sayisi`), sabit değildir: kuponda 15, eğitim
korpusunun sözde-haftalarında değişken. Aynı tahminci böylece iki kaynakta da
çalışır.

`egit`/`tahmin` ayrımı süs değil, **sızıntıya karşı tek savunmadır.** Sezon
dağılımı gibi veriden türeyen bir tahminci, ölçüldüğü haftayı görerek eğitilirse
kendi sınavının cevabını okumuş olur; `evaluate.hafta_disarida_birak` bu ayrım
sayesinde eğitim setinden o haftayı çıkarabiliyor.

Üç referans tahminci — üçü de mevcut veriden, ek kaynak gerektirmez:

    duzgun          her sembole 1/3.  Brier 0,667. Mutlak zemin.
    sezon_sabiti    sezonun 1/0/2 dağılımı.  Naif taban.
    piyasa          marj arındırılmış kapanış oranı.  Brier 0,574.

**`piyasa` aşılması gereken çizgidir, referans değil.** Bir tahminci onu
out-of-sample geçmedikçe "iyileşme" sayılmaz — `evaluate.karsilastir` bu kuralı
kodda uygular, yorumu okura bırakmaz.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .history import SYMBOLS

#: Bir haftanın girdisi — `backtest.hafta_girdileri()` ya da
#: `egitim.korpus_haftalari()` üretir.
#: Alanlar: week, close_date, results, probs[], missing, usable
Girdi = Dict[str, Any]

#: Bir maçın tahmini: sembol → olasılık. Toplamı 1 olmalıdır.
Olasilik = Dict[str, float]


def mac_sayisi(hafta: Girdi) -> int:
    """Haftanın maç sayısı — kuponda 15, eğitim korpusunda değişken.

    Tahminciler bunu `MATCH_COUNT` yerine kullanır; aksi halde korpusun
    sözde-haftalarında (bkz. `egitim.korpus_haftalari`) yanlış uzunlukta
    çıktı verir ve koşum haklı olarak hata fırlatır.
    """
    sonuc = hafta.get("results") or ""
    if sonuc:
        return len(sonuc)
    return len(hafta.get("probs") or [])


class Tahminci:
    """Tahminci taban sınıfı.

    Alt sınıflar `tahmin`'i yazar; veriden öğrenen olanlar `egit`'i de.
    Öğrenmeyen bir tahminci için `egit` bilerek no-op'tur — böylece koşum
    her tahminciye aynı şekilde davranır ve "bu eğitilir mi?" sorusu
    değerlendirme tarafına sızmaz.
    """

    ad: str = "isimsiz"
    aciklama: str = ""

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        """Eğitim haftalarını gör. Öğrenmeyen tahminciler için no-op."""

    def tahmin(self, hafta: Girdi) -> List[Olasilik]:
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - tanılama kolayligi
        return f"<Tahminci {self.ad}>"


class DuzgunTahminci(Tahminci):
    """Her sembole 1/3 — bilgi taşımayan tahmin.

    Mutlak zemindir: Brier skoru 0,667 çıkar ve bunun altına inemeyen bir
    tahminci, hiçbir şey bilmiyor demektir.
    """

    ad = "duzgun"
    aciklama = "Her sembole 1/3; bilgi taşımayan zemin"

    def tahmin(self, hafta: Girdi) -> List[Olasilik]:
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        return [dict(esit) for _ in range(mac_sayisi(hafta))]


class SezonSabitiTahminci(Tahminci):
    """Eğitim haftalarının 1/0/2 dağılımını her maça aynen verir.

    Maçlar arasında hiçbir ayrım yapmaz; yalnızca "bu ligde 1 daha sık
    çıkar" bilgisini taşır. Piyasanın ne kadarının bu kadar ucuz bir
    bilgiden geldiğini gösterdiği için naif tabandır.

    **Eğitim şart.** Dağılım veriden gelir; `egit` çağrılmadan `tahmin`
    çağrılırsa düzgün dağılıma düşer — sessizce yanlış bir sayı üretmek
    yerine bilgisizliğini itiraf eder.
    """

    ad = "sezon_sabiti"
    aciklama = "Eğitim setinin 1/0/2 dağılımı, her maça aynı"

    def __init__(self) -> None:
        self._dagilim: Olasilik = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        sayim = {s: 0 for s in SYMBOLS}
        for hafta in haftalar:
            for kod in hafta["results"]:
                if kod in sayim:
                    sayim[kod] += 1
        toplam = sum(sayim.values())
        if toplam == 0:
            return
        self._dagilim = {s: sayim[s] / toplam for s in SYMBOLS}

    def tahmin(self, hafta: Girdi) -> List[Olasilik]:
        return [dict(self._dagilim) for _ in range(mac_sayisi(hafta))]


class PiyasaTahminci(Tahminci):
    """Marj arındırılmış kapanış oranı — aşılması gereken çizgi.

    Hiçbir şey öğrenmez; oranı olduğu gibi okur. Ölçülen Brier skoru 0,574
    (eşit dağıtım 0,667), yani piyasa bilgi taşıyor ama az. Yeni bir
    tahmincinin değeri, bu sayıyı out-of-sample geçip geçmediğidir.

    Sayı **arındırma yöntemine bağlıdır**: 0,574 bugünkü varsayılan (`shin`)
    ile; `orantili` ölçeğinde 0,5747'ydi (A5, `docs/ISTATISTIK_YOL_HARITASI.md`
    §3.18). Eski ölçümlerle kıyaslarken hangi ölçekte olduğuna bakılmalı.

    Oranı bulunamayan maç için düzgün dağılım döner. Bu durum yalnızca
    `usable=False` haftalarda olur ve koşum o haftaları zaten dışarıda
    bırakır (bkz. `evaluate.olculebilir_haftalar`).
    """

    ad = "piyasa"
    aciklama = "Marj arındırılmış kapanış oranı (football-data)"

    def tahmin(self, hafta: Girdi) -> List[Olasilik]:
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        out: List[Olasilik] = []
        for blok in hafta["probs"]:
            out.append(dict(blok) if blok else dict(esit))
        return out


#: Referans tahminciler — her koşumda bunlara karşı ölçülür.
#: Sıra kasıtlı: zeminden çizgiye doğru.
def referans_fabrikalar() -> List[type]:
    """Üç referansın **sınıfları** — her biri kendi fabrikasıdır.

    Örnek değil sınıf döner, çünkü `sezon_sabiti` eğitimle **durum tutar**:
    değerlendirme koşumu her kat için sıfırdan bir örnek kurmak zorundadır,
    yoksa bir katın eğitimi diğerine sızar.
    """
    return [DuzgunTahminci, SezonSabitiTahminci, PiyasaTahminci]


def referans_tahminciler() -> List[Tahminci]:
    """Üç referansın yeni birer örneği (tanılama ve elle kullanım için)."""
    return [f() for f in referans_fabrikalar()]


#: Karşılaştırmanın referansı. Bir aday "iyileşme" sayılmak için bunu
#: out-of-sample geçmek zorundadır.
REFERANS_AD = PiyasaTahminci.ad
