"""Gradyan artırmalı ağaçlar — kalan tek denenmemiş model sınıfı (Faz 2.2).

`DIS_INCELEME.md` §3'ün itirazı §3.26'da **daraltıldı** ama kapanmadı:

> *"Piyasayı geçen özellik yok demediniz — sizin **doğrusal kademeniz** o
> özelliği kullanamadı demiş oldunuz."*

§3.26 doğrusal modele **açık etkileşim terimleri** ekledi ve bir şey
çıkmadı (§3.29'da bedel anlamlı bile oldu). Ama açık etkileşim terimi ile
**keyfî doğrusal olmama** aynı şey değildir: bir ağaç topluluğu eşik
kurabilir, bölgesel davranabilir ve hiçbir çarpım terimiyle yazılmayan
şekilleri öğrenebilir. Bu modül o sınıfı bizim kesitimizde ölçer.

─── Kritik tasarım: ağaç **artığı** öğrenir, sıfırdan değil ─────────────

Naif kurulum ağaca bütün özellikleri verip 1X2'yi doğrudan tahmin
ettirmektir. O ölçüm işe yaramaz, çünkü ağacın piyasa fiyatını **yeniden
keşfetmesi** gerekir ve neredeyse kesin olarak daha kötü keşfeder — sonuç
"ağaçlar kötü" olur, oysa sorulan soru bu değildir.

Doğru kurulum LightGBM'in `init_score`udur: modelin başlangıç ham skoru
**piyasanın log-olasılığına** sabitlenir ve ağaçlar yalnızca oradan sapmayı
öğrenir. Bu, kademenin `sicaklik`/`bias` basamaklarının `β·log p`'den
başlamasıyla **aynı** çerçevedir — yani ağaç ile kademe artık aynı soruyu
cevaplıyor ve karşılaştırılabilir.

İki tahminci sunulur ve ikisi ayrı sorudur:

    agac        piyasadan başlar, artığı öğrenir      ← asıl ölçüm
    agac_ham    sıfırdan öğrenir, piyasayı görmez     ← DC gibi bağımsız görüş

─── Hiperparametreler: iç halkada, dış halka dokunulmadan ────────────────

`arama.SezonKatlayici` ile eğitim sezonlarının içinde seçilir. Dış halkanın
test sezonu aramaya **hiç girmez**. Aday listesi bilerek küçük ve basitten
karmaşığa sıralı: eşitlikte az kapasiteli model kazanır.

Bağımlılık: `lightgbm` (`pip install -e "./backend[model]"`). Yoksa modül
**içe aktarılabilir** ama tahminci kurulamaz — `HAS_LIGHTGBM` ile
denetlenir, `core.HAS_SCIPY` deseninin aynısı.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from .arama import SezonKatlayici, izgara_ara
from .history import SYMBOLS
from .predict import Girdi, Olasilik, Tahminci

try:  # pragma: no cover - ortama bagli
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:  # pragma: no cover - ortama bagli
    HAS_LIGHTGBM = False

#: Olasılık logaritması alınırken sıfıra düşmeyi engelleyen taban —
#: `recalibrate.OLASILIK_TABANI` ile aynı değer, aynı gerekçe.
OLASILIK_TABANI = 1e-6

#: Aday hiperparametreler — **basitten karmaşığa**. Eşitlikte ilki kazanır
#: (`arama.izgara_ara`), yani az kapasiteli model tercih edilir.
#:
#: Liste bilerek kısa. Geniş bir ızgara iç halkada daha iyi bir sayı bulur
#: ama arama gürültüsünü de büyütür; 31 bin maçta dört aday, kapasitenin
#: yardım edip etmediğini görmeye yeter.
ADAYLAR: tuple[dict[str, Any], ...] = (
    {"num_leaves": 4, "n_estimators": 100, "learning_rate": 0.05,
     "min_child_samples": 500},
    {"num_leaves": 8, "n_estimators": 200, "learning_rate": 0.05,
     "min_child_samples": 200},
    {"num_leaves": 16, "n_estimators": 300, "learning_rate": 0.05,
     "min_child_samples": 100},
    {"num_leaves": 31, "n_estimators": 500, "learning_rate": 0.05,
     "min_child_samples": 50},
)

#: Sabit ayarlar — kapasiteyle ilgisi yok, tekrarlanabilirlik için.
SABIT: dict[str, Any] = {
    "objective": "multiclass",
    "num_class": len(SYMBOLS),
    "random_state": 20260824,
    "deterministic": True,
    "force_row_wise": True,
    "verbose": -1,
    "n_jobs": 1,
}

#: Ağacın gördüğü sayısal özellikler. Kademenin yön sütunlarıyla **aynı
#: küme** — böylece "ağaç mı kademe mi" sorusu özellik farkıyla değil
#: yalnızca model sınıfıyla cevaplanır.
OZELLIK_ALANLARI: tuple[str, ...] = (
    "form_puan_farki", "form_isabet_farki",
    "dinlenme_farki", "sikisiklik_farki",
    "ic_dis_form_farki", "sezon_sonu_pay_farki",
    "elo_farki", "h2h_farki", "seri_farki",
    "ayrisma",
)


def _tasarim(ozellikler: Sequence[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    """`(X, ham_skor)` — özellik matrisi ve piyasanın log-olasılığı.

    `X` ayrıca piyasanın kendi olasılıklarını da taşır: `init_score` ham
    skoru sabitler ama ağacın *nerede* sapması gerektiğini bilmesi için
    fiyatı görmesi gerekir (ör. "favori güçlüyken form daha az önemli"
    ancak favori gücü sütunda varsa öğrenilebilir).
    """
    n = len(ozellikler)
    k = len(OZELLIK_ALANLARI) + len(SYMBOLS)
    X = np.zeros((n, k), dtype=float)
    ham = np.zeros((n, len(SYMBOLS)), dtype=float)
    for i, o in enumerate(ozellikler):
        for j, alan in enumerate(OZELLIK_ALANLARI):
            X[i, j] = float(o.get(alan) or 0.0)
        probs = o.get("probs") or {}
        for j, s in enumerate(SYMBOLS):
            p = max(float(probs.get(s, 1.0 / len(SYMBOLS))), OLASILIK_TABANI)
            X[i, len(OZELLIK_ALANLARI) + j] = p
            ham[i, j] = np.log(p)
    return X, ham


def _satirlar(haftalar: Sequence[Girdi]) -> tuple[list[dict[str, Any]], list[int],
                                                  list[Any]]:
    """Eğitim satırları, sınıf indeksleri ve sezon etiketleri."""
    from .recalibrate import _mac_ozellikleri

    ozellikler: list[dict[str, Any]] = []
    y: list[int] = []
    gruplar: list[Any] = []
    for hafta in haftalar:
        satir = _mac_ozellikleri(hafta)
        for i, kod in enumerate(hafta["results"]):
            if i < len(satir) and satir[i]["probs"] and kod in SYMBOLS:
                ozellikler.append(satir[i])
                y.append(SYMBOLS.index(kod))
                gruplar.append(hafta.get("sezon"))
    return ozellikler, y, gruplar


class AgacTahminci(Tahminci):
    """LightGBM çok sınıflı — piyasanın artığını öğrenir.

    `piyasadan_basla=False` ile ağaç fiyatı bir başlangıç noktası olarak
    **kullanmaz** ve sıfırdan öğrenir; o hâli Dixon-Coles gibi bağımsız bir
    görüştür ve ayrı bir soruyu cevaplar.

    Eğitilmeden `tahmin` çağrılırsa piyasayı olduğu gibi taşır — `predict`
    modülündeki kuralın aynısı: bilgisizken uydurma düzeltme üretme.
    """

    aciklama = "LightGBM cok sinifli; piyasanin artigini ogrenir"

    def __init__(self, piyasadan_basla: bool = True,
                 adaylar: Sequence[dict[str, Any]] = ADAYLAR) -> None:
        if not HAS_LIGHTGBM:  # pragma: no cover - ortama bagli
            raise RuntimeError(
                "lightgbm kurulu degil — pip install -e './backend[model]'")
        self.piyasadan_basla = piyasadan_basla
        self.adaylar = list(adaylar)
        self.ad = "agac" if piyasadan_basla else "agac_ham"
        self._model: Any = None
        self._arama: dict[str, Any] | None = None

    # -- egitim --------------------------------------------------------------

    def _kur(self, params: dict[str, Any]) -> Any:
        return lgb.LGBMClassifier(**SABIT, **params)

    def _uydur(self, X: np.ndarray, y: np.ndarray, ham: np.ndarray,
               params: dict[str, Any]) -> Any:
        model = self._kur(params)
        # LightGBM cok sinifli `init_score`u (n, num_class) bekler.
        model.fit(X, y, init_score=ham if self.piyasadan_basla else None)
        return model

    def _olasilik(self, model: Any, X: np.ndarray, ham: np.ndarray) -> np.ndarray:
        """Ham skorlari topla ve softmax'la — `init_score` ile tek dogru yol.

        `predict_proba` `init_score`u **eklemez**; ham skoru alip baslangic
        skoruyla toplamak ve softmax uygulamak gerekir. Bu unutulursa model
        piyasayi hic gormemis gibi tahmin eder ve olcum sessizce baska bir
        seyi olcer.
        """
        z = model.predict(X, raw_score=True)
        z = np.asarray(z, dtype=float).reshape(len(X), len(SYMBOLS))
        if self.piyasadan_basla:
            z = z + ham
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        ozellikler, y_list, gruplar = _satirlar(haftalar)
        if not ozellikler:
            self._model = None
            return
        X, ham = _tasarim(ozellikler)
        y = np.asarray(y_list, dtype=int)

        katlayici = SezonKatlayici(gruplar)

        def skorla(params: dict[str, Any], egitim: np.ndarray,
                   test: np.ndarray) -> float:
            model = self._uydur(X[egitim], y[egitim], ham[egitim], params)
            p = self._olasilik(model, X[test], ham[test])
            hedef = np.zeros_like(p)
            hedef[np.arange(len(test)), y[test]] = 1.0
            return float(((p - hedef) ** 2).sum(axis=1).mean())

        self._arama = izgara_ara(self.adaylar, katlayici, skorla,
                                 varsayilan=self.adaylar[0])
        self._model = self._uydur(X, y, ham, self._arama["parametreler"])

    # -- tahmin --------------------------------------------------------------

    def tahmin(self, hafta: Girdi) -> list[Olasilik]:
        from .recalibrate import _mac_ozellikleri

        satir = _mac_ozellikleri(hafta)
        n = len(hafta.get("results") or "") or len(satir)
        satir = satir[:n]
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        if self._model is None or not satir:
            return [dict(o.get("probs") or esit) for o in satir] or [
                dict(esit) for _ in range(n)]

        X, ham = _tasarim(satir)
        p = self._olasilik(self._model, X, ham)
        return [{s: float(p[i, j]) for j, s in enumerate(SYMBOLS)}
                for i in range(len(satir))]

    @property
    def arama(self) -> dict[str, Any] | None:
        """İç halkanın ne seçtiği — ölçüm raporlarında yazılır."""
        return self._arama


def fabrikalar() -> list[Any]:
    """İki tahmincinin fabrikaları — `evaluate.karsilastir` için."""
    return [AgacTahminci, lambda: AgacTahminci(piyasadan_basla=False)]


# ─── LOFO — bir özelliği çıkarınca ne oluyor (Faz 2.5) ────────────────────────

def lofo(haftalar: Sequence[Girdi],
         alanlar: Sequence[str] = OZELLIK_ALANLARI,
         params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Leave-One-Feature-Out önem — **sezon katlarıyla**.

    Tekil önem ölçüleri (ağaç bölünme sayısı, permütasyon) korelasyonlu
    özelliklerde yanıltır: `elo_farki`, `form_puan_farki` ve `h2h_farki`
    üçü de takım gücünü ölçüyor ve biri düştüğünde ötekiler açığı kapatıyor.
    LOFO tam bunu ölçer — *"bu özelliği tamamen çıkarsam skor ne kadar
    kötüleşir?"*

    Pozitif `zarar` = özellik çıkarılınca Brier **arttı**, yani özellik
    işe yarıyordu. Sıfır ya da negatif = özellik hiçbir şey taşımıyor
    (ya da gürültü ekliyor).

    Katlar `arama.SezonKatlayici`dan gelir. AlphaPy Pro'nun `select_features_lofo`u
    aynı işi rastgele katlarla yapıyor (`DIS_INCELEME_ALPHAPY.md` §4.1) ve
    zaman sıralı veride o katlar sızdırır.
    """
    ozellikler, y_list, gruplar = _satirlar(haftalar)
    if not ozellikler:
        return {"n": 0, "taban": None, "ozellikler": []}

    X, ham = _tasarim(ozellikler)
    y = np.asarray(y_list, dtype=int)
    katlayici = SezonKatlayici(gruplar)
    p = dict(params or ADAYLAR[0])

    def skorla(sutunlar: Sequence[int]) -> float:
        toplam = 0.0
        n = 0
        for egitim, test in katlayici.split():
            # Sutunu SILMEK yerine SIFIRLAMAK: matris sekli sabit kalir ve
            # `init_score` hizasi bozulmaz. Sifir sutun agac icin bilgisiz
            # bir sutundur — bolunme uretmez.
            Xk = X.copy()
            for j in sutunlar:
                Xk[:, j] = 0.0
            model = self_uydur(Xk[egitim], y[egitim], ham[egitim], p)
            q = self_olasilik(model, Xk[test], ham[test])
            hedef = np.zeros_like(q)
            hedef[np.arange(len(test)), y[test]] = 1.0
            toplam += float(((q - hedef) ** 2).sum(axis=1).sum())
            n += len(test)
        return toplam / n if n else float("nan")

    # Uydurma/olasilik gövdeleri tahmincinin kendisinden alinir ki iki kopya
    # olmasin; `piyasadan_basla=True` sabit, cunku LOFO'nun sorusu
    # "piyasanin USTUNE ne ekliyor" sorusudur.
    _ornek = AgacTahminci()
    self_uydur = _ornek._uydur
    self_olasilik = _ornek._olasilik

    if not katlayici.yeterli():
        return {"n": len(y), "taban": None, "ozellikler": [],
                "sebep": "ic halka icin en az iki sezon gerekiyor"}

    taban = skorla(())
    out: list[dict[str, Any]] = []
    for alan in alanlar:
        if alan not in OZELLIK_ALANLARI:
            continue
        i = OZELLIK_ALANLARI.index(alan)
        skor = skorla((i,))
        out.append({"alan": alan, "brier": skor, "zarar": skor - taban})
    out.sort(key=lambda r: -r["zarar"])
    return {"n": len(y), "taban": taban, "n_kat": katlayici.get_n_splits(),
            "parametreler": p, "ozellikler": out}


# ─── elle koşum ───────────────────────────────────────────────────────────────

def rapor(sezonlar_: Sequence[str] | None = None) -> dict[str, Any]:
    """Ağaçları piyasaya karşı, **sezon dışarıda bırakmalı** koş.

    Geçme ölçütü projenin geri kalanıyla aynı: eşleştirilmiş bootstrap
    aralığının **tamamı** sıfırın altında olmalı.
    """
    from .egitim import korpus_haftalari
    from .evaluate import karsilastir, sezon_anahtari
    from .predict import PiyasaTahminci

    haftalar = korpus_haftalari(sezonlar_=sezonlar_)
    sonuc = karsilastir([PiyasaTahminci, *fabrikalar()],
                        haftalar=haftalar, grup=sezon_anahtari)
    sonuc["soru"] = (
        "keyfi dogrusal olmama (agac toplulugu) piyasa fiyatinin uzerine "
        "bir sey ekliyor mu — `agac` piyasadan baslayip artigi ogreniyor, "
        "`agac_ham` sifirdan")
    return sonuc


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--rapor", action="store_true", help="varsayilan kosum")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    s = rapor()
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=1, default=str))
        return

    print(f"\nAGAC OLCUMU — {s['n_mac']:,} mac · {s['n_hafta']} hafta "
          f"· referans {s['referans']}")
    print(f"{'tahminci':<12}{'brier':>10}{'fark':>11}{'%95 aralik':>26}  gecti")
    for t_ in s["tahminciler"]:
        f = t_.get("fark") or {}
        aralik = ("—" if f.get("ham_alt") is None
                  else f"[{f['ham_alt']:+.6f}, {f['ham_ust']:+.6f}]")
        print(f"{t_['ad']:<12}{t_['brier']:>10.6f}"
              f"{(f.get('ham_fark') or 0):>+11.6f}{aralik:>26}  "
              f"{'EVET' if t_.get('gecti') else 'hayir'}")
        a_ = t_["ayrisim"]["toplam"]
        print(f"{'':12}guvenilir {a_['guvenilirlik']:.5f} · "
              f"cozunur {a_['cozunurluk']:.5f} · "
              f"NDCG {t_['siralama']['ndcg']}")
    print(f"\nSoru: {s['soru']}")


if __name__ == "__main__":  # pragma: no cover
    main()
