"""Venn-Abers — geçerlilik garantili olasılık aralığı (Faz 2.3).

AlphaPy Pro'nun en dikkat çeken parçası buydu (`DIS_INCELEME_ALPHAPY.md`
§A.5): `VennAbersCalibrator(estimator=est, inductive=True, cal_size=0.2)`.
Venn-Abers, bir noktaya tek bir olasılık değil bir **aralık** verir ve
aralığın *değiştirilebilirlik* (exchangeability) altında geçerli olduğu
kanıtlanmıştır — yani "bu olasılık ne kadar güvenilir" sorusunun kendisi
ölçülür.

─── Üç sapma, üçü de gerekçeli ───────────────────────────────────────────

**1. Paket alınmadı, algoritma yazıldı.** `pip install venn-abers` bu
ortamda **derlenmiyor**. Ama zaten `recalibrate._pav` elimizde: Venn-Abers
iki PAV uydurmasıdır. `recalibrate._uydur`un "sessizce kaybolabilecek bir
isteğe bağlı bağımlılık, kendi çözücünü yazmaktan kötüdür" gerekçesi burada
teorik değil, ölçülmüş bir gerçek.

**2. Kalibrasyon bölmesi sezon bazlı, rastgele DEĞİL.** Pro'nun
`cal_size=0.2`si rastgele bir dilim alır. Zaman sıralı veride bu, aynı
sezonun maçlarını hem uydurmaya hem kalibrasyona koyar. Burada kalibrasyon
için **en son sezon** ayrılır — kronolojik olarak doğru olan tek bölme.

**3. Üç sınıf için bire-karşı-hepsi, ve bu bir ödünç.** Venn-Abers ikili
bir yöntemdir. Üç sembol için üç ayrı IVAP koşup sonucu normalize etmek
geçerlilik garantisini **korumaz** — garanti her sembol için ayrı ayrı
geçerlidir, normalize edilmiş üçlü için değil. Sayı yine kullanışlıdır ama
teorik iddiası küçülmüştür ve bu **yazılı olmak zorundadır.**

─── Beklenti, koşumdan önce ──────────────────────────────────────────────

§3.23 kalibrasyon ekseninin tavanını **0,00042** ölçtü. Venn-Abers'ın
kazanabileceği en fazla o kadardır ve izotonik zaten `shin` üzerinde
hiçbir şey eklemiyordu. Yani nokta tahmininde bir şey beklenmiyor.

**Beklenen asıl çıktı aralığın kendisi**: `p1 − p0` genişliği, "bu tahmin
ne kadar destekleniyor" sorusunun projede daha önce hiç ölçülmemiş
cevabıdır.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from .history import SYMBOLS
from .predict import Girdi, Olasilik, PiyasaTahminci, Tahminci
from .recalibrate import _pav

#: `p0`/`p1` ızgarasının nokta sayısı.
#:
#: Saf IVAP her test noktası için iki PAV uydurması ister; 31 bin maç × 3
#: sembol × 2 uydurma pratikte koşmaz. Izgara, kalibrasyon skorlarının
#: **quantile**'larına kurulur ve ara değerler doğrusal ara değerlenir.
#: Bu bir yaklaşıklıktır ve büyüklüğü ölçülebilir: ızgara sıklaştıkça
#: sonuç sabitlenir (`test_izgara_sikligi_sonucu_oynatmiyor`).
IZGARA = 128

#: Kalibrasyon kümesinin en az nokta sayısı. Altında aralık kendi
#: gürültüsünü ölçer — `recalibrate.EN_AZ_KOVA` ile aynı gerekçe.
EN_AZ_KALIBRASYON = 500


def _ivap_izgarasi(skorlar: np.ndarray, etiketler: np.ndarray,
                   izgara: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Izgaranın her noktası için `(p0, p1)`.

    `p0`: test noktası **0** etiketiyle kalibrasyon kümesine eklenirse
    izotonik uyumun o noktadaki değeri. `p1`: **1** etiketiyle.

    İkisinin arası, kalibrasyon kümesinin o skoru ne kadar kısıtladığını
    söyler — Venn-Abers'ın asıl kattığı şey budur.
    """
    sira = np.argsort(skorlar, kind="stable")
    s = skorlar[sira]
    y = etiketler[sira]
    p0 = np.empty(len(izgara))
    p1 = np.empty(len(izgara))

    for i, nokta in enumerate(izgara):
        yer = int(np.searchsorted(s, nokta, side="right"))
        for etiket, hedef in ((0.0, p0), (1.0, p1)):
            genis_y = np.concatenate([y[:yer], [etiket], y[yer:]])
            uyum = _pav(list(range(len(genis_y))), list(genis_y),
                        [1.0] * len(genis_y))
            hedef[i] = uyum[yer]
    return p0, p1


class VennAbersTahminci(Tahminci):
    """Bire-karşı-hepsi indüktif Venn-Abers, sezon bazlı kalibrasyonla.

    Taban tahminci varsayılan olarak `piyasa`dır: soru *"piyasanın
    olasılığı Venn-Abers ile düzeltilince bir şey kazanılıyor mu"*.

    Kalibrasyon için eğitim setinin **son sezonu** ayrılır ve taban ondan
    önceki sezonlarda eğitilir. Taban öğrenmiyorsa (piyasa) bölme yalnızca
    kalibrasyon kümesini belirler.

    Yeterli kalibrasyon noktası yoksa tahminci **tabanı aynen taşır** —
    uydurma bir düzeltme üretmez.
    """

    ad = "venn_abers"
    aciklama = "Bire-karsi-hepsi induktif Venn-Abers; sezon bazli kalibrasyon"

    def __init__(self, taban: Any = PiyasaTahminci, izgara: int = IZGARA) -> None:
        self._taban_fabrika = taban
        self._izgara_n = izgara
        self._taban: Tahminci = taban()
        self._model: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    # -- egitim --------------------------------------------------------------

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        sezonlar = list(dict.fromkeys(h.get("sezon") for h in haftalar))
        self._model = {}
        if len(sezonlar) >= 2:
            kal_sezon = sezonlar[-1]
            uydurma = [h for h in haftalar if h.get("sezon") != kal_sezon]
            kalibrasyon = [h for h in haftalar if h.get("sezon") == kal_sezon]
        else:
            # Tek sezon: bolme yapilamaz. Taban ogrenmiyorsa (piyasa) bu
            # sorun degil — kalibrasyon kumesi yine kurulabilir.
            uydurma, kalibrasyon = list(haftalar), list(haftalar)

        self._taban = self._taban_fabrika()
        self._taban.egit(uydurma)

        # Kalibrasyon kumesi: (skor, etiket) — sembol basina.
        havuz: dict[str, list[tuple[float, float]]] = {s: [] for s in SYMBOLS}
        for hafta in kalibrasyon:
            tahminler = self._taban.tahmin(hafta)
            for i, kod in enumerate(hafta["results"]):
                if i >= len(tahminler) or kod not in SYMBOLS:
                    continue
                for s in SYMBOLS:
                    havuz[s].append((float(tahminler[i].get(s, 0.0)),
                                     1.0 if kod == s else 0.0))

        for s, noktalar in havuz.items():
            if len(noktalar) < EN_AZ_KALIBRASYON:
                continue
            skorlar = np.array([p for p, _ in noktalar])
            etiketler = np.array([y for _, y in noktalar])
            izgara = np.unique(np.quantile(
                skorlar, np.linspace(0.0, 1.0, self._izgara_n)))
            p0, p1 = _ivap_izgarasi(skorlar, etiketler, izgara)
            self._model[s] = (izgara, p0, p1)

    # -- tahmin --------------------------------------------------------------

    def _tekil(self, s: str, skor: float) -> tuple[float, float]:
        """Bir sembolün `(p0, p1)` aralığı — ızgaradan ara değerlenir."""
        if s not in self._model:
            return skor, skor
        izgara, p0, p1 = self._model[s]
        return (float(np.interp(skor, izgara, p0)),
                float(np.interp(skor, izgara, p1)))

    def tahmin(self, hafta: Girdi) -> list[Olasilik]:
        taban = self._taban.tahmin(hafta)
        if not self._model:
            return taban

        out: list[Olasilik] = []
        for p in taban:
            ham: dict[str, float] = {}
            for s in SYMBOLS:
                p0, p1 = self._tekil(s, float(p.get(s, 0.0)))
                # Venn-Abers'in tekil olasilik ozeti: p1 / (1 - p0 + p1).
                payda = 1.0 - p0 + p1
                ham[s] = (p1 / payda) if payda > 0 else float(p.get(s, 0.0))
            toplam = sum(ham.values())
            out.append({s: (v / toplam if toplam > 0 else 1.0 / len(SYMBOLS))
                        for s, v in ham.items()})
        return out

    def aralik(self, hafta: Girdi) -> list[dict[str, tuple[float, float]]]:
        """Sembol başına `(p0, p1)` — **Venn-Abers'ın asıl kattığı şey**.

        Genişlik, kalibrasyon kümesinin o skoru ne kadar kısıtladığını
        söyler. Tek bir olasılık sayısının hiçbir zaman söylemediği şey
        budur ve projede daha önce hiç ölçülmedi.
        """
        return [{s: self._tekil(s, float(p.get(s, 0.0))) for s in SYMBOLS}
                for p in self._taban.tahmin(hafta)]


def rapor(sezonlar_: Sequence[str] | None = None) -> dict[str, Any]:
    """Venn-Abers'ı piyasaya karşı, sezon dışarıda bırakmalı koş."""
    from .egitim import korpus_haftalari
    from .evaluate import karsilastir, sezon_anahtari

    haftalar = korpus_haftalari(sezonlar_=sezonlar_)
    sonuc = karsilastir([PiyasaTahminci, VennAbersTahminci],
                        haftalar=haftalar, grup=sezon_anahtari)

    # Aralik genisligi ayri raporlanir: nokta tahmininden BAGIMSIZ bir
    # bilgidir ve Venn-Abers'in asil ciktisidir.
    ornek = VennAbersTahminci()
    ornek.egit(haftalar)
    genislikler: list[float] = []
    for hafta in haftalar:
        for blok in ornek.aralik(hafta):
            genislikler.extend(p1 - p0 for p0, p1 in blok.values())
    sonuc["aralik"] = {
        "n": len(genislikler),
        "ortalama_genislik": (sum(genislikler) / len(genislikler)
                              if genislikler else None),
        "en_genis": max(genislikler) if genislikler else None,
    }
    sonuc["sinir"] = (
        "Uc sinif icin bire-karsi-hepsi kosuluyor ve sonuc normalize "
        "ediliyor; gecerlilik garantisi her sembol icin AYRI AYRI gecerli, "
        "normalize edilmis uclu icin degil")
    sonuc["soru"] = (
        "piyasanin olasiligi Venn-Abers ile duzeltilince bir sey "
        "kazaniliyor mu — §3.23 tavani 0,00042 olarak olctu")
    return sonuc


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse
    import json

    from .kosum import belki_kaydet, cli_ekle


    ap = argparse.ArgumentParser()
    ap.add_argument("--rapor", action="store_true")
    ap.add_argument("--json", action="store_true")
    cli_ekle(ap)
    a = ap.parse_args(argv)

    s = rapor()
    belki_kaydet("kalibre", s, a)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1, default=str))
        return

    print(f"\nVENN-ABERS — {s['n_mac']:,} mac · {s['n_hafta']} hafta")
    print(f"{'tahminci':<14}{'brier':>10}{'fark':>11}{'%95 aralik':>26}  gecti")
    for t in s["tahminciler"]:
        f = t.get("fark") or {}
        aralik = ("—" if f.get("ham_alt") is None
                  else f"[{f['ham_alt']:+.6f}, {f['ham_ust']:+.6f}]")
        print(f"{t['ad']:<14}{t['brier']:>10.6f}"
              f"{(f.get('ham_fark') or 0):>+11.6f}{aralik:>26}  "
              f"{'EVET' if t.get('gecti') else 'hayir'}")
    ar = s["aralik"]
    print(f"\nAralik genisligi — ort {ar['ortalama_genislik']:.5f} · "
          f"en genis {ar['en_genis']:.5f} · n {ar['n']:,}")
    print(f"\nSinir: {s['sinir']}")
    print(f"Soru: {s['soru']}")


if __name__ == "__main__":  # pragma: no cover
    main()
