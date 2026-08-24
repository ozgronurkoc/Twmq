"""Yığınlama — bağımsız görüşleri **kat dışı** olasılıklarla birleştir (Faz 2.4).

`DIS_INCELEME_ALPHAPY.md` §4 madde 4'te ölçülen hata buydu: klasik
AlphaPy'ın `predict_blend`i harman tasarım matrisini
`model.probas[(algo, Partition.train)]`den — yani **örneklem içi**
olasılıklardan — kuruyor. En çok aşırı uyan model kendi eğitim setinde en
iyi görünür, üst-öğrenici de ona en büyük ağırlığı verir. Pro bunu
düzeltmiş ama kat dışılığı **rastgele** katlarla sağlıyor; zaman sıralı
veride o da sızdırır.

Buradaki yığın iki şartı birden sağlıyor:

1. Üst-öğrenici **kat dışı** olasılıklarla eğitilir;
2. Katlar `arama.SezonKatlayici`dan gelir, yani **sezon** sınırlarıdır.

─── Üst-öğrenici: taban başına TEK katsayı ───────────────────────────────

Tasarım `recalibrate`'in `sicaklik` basamağıyla aynı: her tabanın her
sembole verdiği log-olasılık bir sütundur ve geriye taban başına **tek** bir
katsayı kalır::

    z_s = Σ_j  w_j · ln p_j(s)

`w_j` doğrudan okunabilir: *"yığın bu görüşe ne kadar ağırlık veriyor?"*
Sembol başına ayrı katsayı verilseydi bu okuma kaybolurdu — `hareket`
basamağındaki gerekçenin aynısı.

Uydurma `recalibrate._uydur`u yeniden kullanır: aynı Newton, aynı L2, aynı
determinizm. Yığın için ayrı bir uydurucu yazmak iki gövde demek olurdu.

─── Beklenti, koşumdan önce yazılıyor ────────────────────────────────────

Faz 1–3 aynı şeyi beş kez ölçtü: piyasadan bağımsız olan da dahil hiçbir
görüş kapanış fiyatının ötesine geçmedi ve `kalibre_dc`nin katsayısı
**negatif** çıktı (§3.28). Yığının bunu tersine çevirmesi için bir sebep
yok; beklenen sonuç `w_piyasa ≈ 1`, ötekiler ≈ 0.

Yine de koşuluyor, çünkü *"birleştirilseler bir şey çıkar mıydı"* sorusu
tek tek denemelerin cevaplayamadığı ayrı bir sorudur — ve cevaplanmadan
kapatılamaz.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from .arama import SezonKatlayici
from .history import SYMBOLS
from .predict import Girdi, Olasilik, Tahminci
from .recalibrate import OLASILIK_TABANI, _softmax, _uydur


#: Yığına giren tabanlar. Sıra kasıtlı: referans önce, bağımsız görüşler
#: sonra — katsayı tablosu böyle okunur.
def taban_fabrikalari() -> list[tuple[str, Callable[[], Tahminci]]]:
    """(ad, fabrika) çiftleri. Ağaç yalnızca `lightgbm` varsa girer."""
    from .dixon_coles import DcTahminci
    from .predict import PiyasaTahminci
    from .recalibrate import KalibreTahminci

    tabanlar: list[tuple[str, Callable[[], Tahminci]]] = [
        ("piyasa", PiyasaTahminci),
        ("kademe", lambda: KalibreTahminci("bant")),
        ("dixon_coles", DcTahminci),
    ]
    from .agac import HAS_LIGHTGBM

    if HAS_LIGHTGBM:
        from .agac import AgacTahminci

        tabanlar.append(("agac", AgacTahminci))
    return tabanlar


def _log_olasilik(p: Olasilik) -> list[float]:
    return [float(np.log(max(p.get(s, 0.0), OLASILIK_TABANI))) for s in SYMBOLS]


class YiginTahminci(Tahminci):
    """Kat dışı olasılıklar üzerinde uydurulan multinom logit üst-öğrenici.

    `egit` iki geçiş yapar ve **sıra önemlidir**:

    1. **Kat dışı geçiş** — her sezon sırayla dışarıda bırakılır, tabanlar
       ötekilerde eğitilir ve dışarıdaki sezona tahmin üretir. Üst-öğrenici
       yalnızca bu tahminleri görür. Tabanlar burada kendi eğitim setlerini
       tahmin etselerdi yığın onların ezberini ölçerdi.
    2. **Tam geçiş** — tabanlar eğitim setinin tamamında yeniden eğitilir;
       `tahmin` bunları kullanır.

    Tek sezonluk eğitim setinde kat dışı geçiş kurulamaz; o durumda
    `_katsayilar` `None` kalır ve tahminci **referansa düşer** (ilk taban).
    Sessizce örneklem içi uydurmak, yığının bütün anlamını bozardı.
    """

    ad = "yigin"
    aciklama = "Kat disi olasiliklar uzerinde multinom logit ust-ogrenici"

    def __init__(self,
                 tabanlar: Sequence[tuple[str, Callable[[], Tahminci]]] | None = None
                 ) -> None:
        self.tabanlar = list(tabanlar) if tabanlar is not None else taban_fabrikalari()
        self._egitilmis: list[Tahminci] = []
        self._katsayilar: np.ndarray | None = None
        self._kat_disi_n = 0

    # -- egitim --------------------------------------------------------------

    def _tahminler(self, model: Tahminci, hafta: Girdi) -> list[Olasilik]:
        p = model.tahmin(hafta)
        n = len(hafta.get("results") or "")
        return p[:n] if n else p

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        gruplar = [h.get("sezon") for h in haftalar]
        katlayici = SezonKatlayici(gruplar)

        # --- 1) kat disi gecis ---
        satirlar: list[list[list[float]]] = []
        kodlar: list[str] = []
        if katlayici.yeterli():
            for egitim_i, test_i in katlayici.split():
                egitim = [haftalar[i] for i in egitim_i]
                test = [haftalar[i] for i in test_i]
                modeller = []
                for _, fabrika in self.tabanlar:
                    m = fabrika()
                    m.egit(egitim)
                    modeller.append(m)
                for hafta in test:
                    tahminler = [self._tahminler(m, hafta) for m in modeller]
                    for i, kod in enumerate(hafta["results"]):
                        if kod not in SYMBOLS:
                            continue
                        # (3 sembol x taban) blogu: sutun j = ln p_j(s)
                        blok = [[_log_olasilik(t[i])[j] for t in tahminler]
                                for j in range(len(SYMBOLS))]
                        satirlar.append(blok)
                        kodlar.append(kod)

        self._kat_disi_n = len(kodlar)
        if kodlar:
            X = np.asarray(satirlar, dtype=float)
            y = np.zeros((len(kodlar), len(SYMBOLS)))
            for i, kod in enumerate(kodlar):
                y[i, SYMBOLS.index(kod)] = 1.0
            self._katsayilar = _uydur(X, y)
        else:
            self._katsayilar = None

        # --- 2) tam gecis ---
        self._egitilmis = []
        for _, fabrika in self.tabanlar:
            m = fabrika()
            m.egit(haftalar)
            self._egitilmis.append(m)

    # -- tahmin --------------------------------------------------------------

    def tahmin(self, hafta: Girdi) -> list[Olasilik]:
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        if not self._egitilmis:
            n = len(hafta.get("results") or "") or len(hafta.get("probs") or [])
            return [dict(esit) for _ in range(n)]

        tahminler = [self._tahminler(m, hafta) for m in self._egitilmis]
        n = min(len(t) for t in tahminler)
        if self._katsayilar is None:
            # Ust-ogrenici kurulamadi — ILK tabana dus (referans). Uydurma
            # bir agirlik uretmektense bilinen bir gorusu tasimak dogru.
            return [dict(tahminler[0][i]) for i in range(n)]

        out: list[Olasilik] = []
        for i in range(n):
            blok = np.asarray(
                [[_log_olasilik(t[i])[j] for t in tahminler]
                 for j in range(len(SYMBOLS))], dtype=float)
            q = _softmax(blok @ self._katsayilar)
            out.append({s: float(q[j]) for j, s in enumerate(SYMBOLS)})
        return out

    # -- tanilama ------------------------------------------------------------

    @property
    def agirliklar(self) -> dict[str, float] | None:
        """Taban başına ağırlık — yığının **asıl çıktısı**.

        Sayı doğrudan okunur: `w_piyasa` 1'e yakın ve ötekiler 0'a yakınsa
        yığın *"fiyattan başka bir şeye ihtiyacım yok"* diyor demektir.
        """
        if self._katsayilar is None:
            return None
        return {ad: float(w) for (ad, _), w in zip(self.tabanlar, self._katsayilar)}

    @property
    def kat_disi_mac(self) -> int:
        return self._kat_disi_n


def rapor(sezonlar_: Sequence[str] | None = None) -> dict[str, Any]:
    """Yığını piyasaya karşı, sezon dışarıda bırakmalı koş."""
    from .egitim import korpus_haftalari
    from .evaluate import karsilastir, sezon_anahtari
    from .predict import PiyasaTahminci

    haftalar = korpus_haftalari(sezonlar_=sezonlar_)
    sonuc = karsilastir([PiyasaTahminci, YiginTahminci],
                        haftalar=haftalar, grup=sezon_anahtari)

    # Agirliklar tam egitim setinde uydurulmus haliyle raporlanir; olcum
    # kat disi kosumdan gelir. Ikisi ayri seydir ve ayri yazilir.
    ornek = YiginTahminci()
    ornek.egit(haftalar)
    sonuc["agirliklar"] = ornek.agirliklar
    sonuc["kat_disi_mac"] = ornek.kat_disi_mac
    sonuc["tabanlar"] = [ad for ad, _ in ornek.tabanlar]
    sonuc["soru"] = (
        "bagimsiz gorusler BIRLESTIRILDIGINDE piyasa fiyatinin otesine "
        "gecen bir sey cikiyor mu — tek tek denemelerin cevaplayamadigi soru")
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
    belki_kaydet("yigin", s, a)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1, default=str))
        return

    print(f"\nYIGIN — {s['n_mac']:,} mac · {s['n_hafta']} hafta "
          f"· kat disi {s['kat_disi_mac']:,} mac")
    print(f"{'tahminci':<14}{'brier':>10}{'fark':>11}{'%95 aralik':>26}  gecti")
    for t in s["tahminciler"]:
        f = t.get("fark") or {}
        aralik = ("—" if f.get("ham_alt") is None
                  else f"[{f['ham_alt']:+.6f}, {f['ham_ust']:+.6f}]")
        print(f"{t['ad']:<14}{t['brier']:>10.6f}"
              f"{(f.get('ham_fark') or 0):>+11.6f}{aralik:>26}  "
              f"{'EVET' if t.get('gecti') else 'hayir'}")
    print("\nTaban agirliklari (tam egitim setinde):")
    for ad, w in (s["agirliklar"] or {}).items():
        print(f"  {ad:<14}{w:>+9.4f}")
    print(f"\nSoru: {s['soru']}")


if __name__ == "__main__":  # pragma: no cover
    main()
