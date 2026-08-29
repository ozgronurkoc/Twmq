"""Dixon-Coles — takım gücünü **gollerden** türeten model (Faz 3.1).

Projede bugüne kadar takım gücünü *sonuçlardan* türeten hiçbir şey yoktu.
`skor.py` (A6) gol parametrelerini **fiyattan** çıkarıyordu — alt/üst ve Asya
handikabından — ve tam bu yüzden geçmedi:

> *"Üç pazar aynı görüşün üç yüzü."*

Elo (§3.27) da bir sonuç modelidir ama **tek bir sayı** taşır: puan farkı.
Beraberliği ayrı bir sonuç olarak modellemez (yarım galibiyet sayar) ve gol
üretimini hiç bilmez. Dixon-Coles her takıma **iki** sayı verir — hücum ve
savunma — ve bir **skor dağılımı** üretir. 1X2 o dağılımdan çıkar.

Bunun projedeki değeri şudur: **piyasadan bağımsız ilk görüş.** Yığınlamanın
(Faz 2.4) anlamlı olabilmesi için en az iki bağımsız görüş gerekir ve bugüne
kadar hepsi aynı fiyatın türevleriydi.

─── Model ────────────────────────────────────────────────────────────────

Ev sahibi `h`, deplasman `a` için beklenen goller::

    λ_ev  = α_h · β_a · γ        γ = ev avantajı (çarpımsal)
    λ_dep = α_a · β_h

`α` hücum, `β` savunma gücü. Skor dağılımı iki bağımsız Poisson'dur — ama
bağımsız Poisson **düşük skorları yanlış verir**: 0-0, 1-0, 0-1 ve 1-1
gerçekte olduğundan seyrek çıkar. Dixon & Coles (1997) bunu tek bir `ρ`
parametresiyle düzeltir::

    τ(0,0) = 1 − λ_ev·λ_dep·ρ      τ(0,1) = 1 + λ_ev·ρ
    τ(1,0) = 1 + λ_dep·ρ           τ(1,1) = 1 − ρ
    τ(x,y) = 1                     diğer bütün skorlar

`ρ > 0` beraberliği (özellikle 0-0 ve 1-1) yukarı iter. Beraberliğin
projedeki önemi düşünülürse (§3.23: piyasanın beraberlik çözünürlüğü on kat
düşük) bu düzeltme süs değil.

─── Neden kendi çözücümüz ────────────────────────────────────────────────

`α`, `β`, `γ` için ağırlıklı Poisson olabilirlik **kapalı biçimde**
güncellenebilir (klasik IPF / koordinat yükselişi): her parametrenin en iyi
değeri ötekiler sabitken bir bölme işlemidir. Yakınsama hızlı ve
deterministiktir.

`scipy.optimize` kullanılmadı ve gerekçesi `recalibrate._uydur` ile aynı:
sessizce kaybolabilecek bir isteğe bağlı bağımlılık, kendi Newton'unu
yazmaktan kötüdür. Burada ayrıca gerek de yok — problem kapalı biçimli.

`ρ` tek skalerdir ve ızgara + ikiye bölme ile aranır.

─── Sızıntı disiplini ────────────────────────────────────────────────────

`elo.elo_tablosu` ile **birebir aynı**: model her turda (ISO hafta)
**yalnızca o turdan önceki** maçlarla yeniden uydurulur ve o turun maçlarına
tahmin üretir. Bir maçın kendi sonucu asla kendi tahminine giremez.
Bekçi: `tests/test_dixon_coles.py::test_dc_gelecegi_gormez`.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from .history import SYMBOLS
from .predict import Girdi, Tahminci

#: Zaman sönümü — bir maçın ağırlığı `exp(−XI · geçen_gün)`.
#: Dixon & Coles yarı ömrü ~1,5 yıl olan bir sönüm kullanır; futbol
#: uygulamalarında 0,002–0,01/gün yaygındır. 0,0045 ≈ **154 günlük yarı
#: ömür** — bir sezonun yarısı. **Veriye bakılarak seçilmedi**
#: (`recalibrate.L2` ile aynı gerekçe: hold-out'a bakarak ayarlanan bir
#: parametre hold-out'un anlamını bitirir).
XI = 0.0045

#: Skor ızgarasının üst sınırı ve `λ`nın üst kırpması.
#:
#: **Sayı ölçülerek seçildi, tahmin edilerek değil.** İlk sürüm 10'du ve
#: docstring "kesilen kuyruk milyonda bir" diyordu; ölçülen kayıp `λ = 3`
#: için **2,9·10⁻⁴** çıktı (on binde üç) ve testi düşürdü. Ölçülen tablo:
#:
#:     ızgara   λ=3        λ=4        λ=6
#:     10       2,9e-04    —          —
#:     15       1,2e-07    4,9e-06    5,1e-04
#:     18       5,6e-10    5,2e-08    1,8e-05     ← seçilen
#:
#: `LAMBDA_TAVANI` gerçekçi bir üst sınırdır: futbolda bir takımın beklenen
#: golü 4'ü nadiren aşar; tavan 6,0'da bile kayıp 10⁻⁵ mertebesinde kalıyor.
MAKS_GOL = 18
LAMBDA_TAVANI = 6.0

#: IPF yinelemesinin sınırları. Rastgelelik yok: başlangıç 1,0 ve durma
#: ölçütü sabit, yani aynı eğitim seti her zaman aynı gücü verir.
EN_COK_YINELEME = 200
DURMA_ESIGI = 1e-9

#: `ρ` aramasının ızgarası. Dixon-Coles'un kendi kesitinde ρ ≈ 0,13;
#: aralık onu rahatça kapsıyor. Kaba ızgara + ikiye bölme yeterli, çünkü
#: olabilirlik ρ'da tek tepelidir.
RHO_ALT, RHO_UST = -0.20, 0.40
RHO_IZGARA = 25
RHO_BOLME = 30

#: Bir takımın kendi gücünü hak etmesi için gereken en az (ağırlıklı) maç.
#: Altındaki takım havuz ortalamasına düşer — `elo.EN_AZ_MAC` ile aynı
#: mantık: bilgisizlik gizlenmez, ortalamaya çekilir.
EN_AZ_MAC = 4.0

#: Modelin uydurulması için gereken en az maç. Altında güçler gürültüdür.
EN_AZ_KESIT = 200


class DixonColes:
    """Ağırlıklı Poisson güçleri + düşük skor düzeltmesi.

    `uydur` çağrılmadan `tahmin` çağrılırsa düzgün dağılım döner — sessizce
    yanlış bir sayı üretmek yerine bilgisizliğini itiraf eder (`predict`
    modülündeki `SezonSabitiTahminci` ile aynı kural).
    """

    def __init__(self, xi: float = XI) -> None:
        self.xi = xi
        self._takimlar: dict[str, int] = {}
        self._atak: np.ndarray | None = None
        self._savunma: np.ndarray | None = None
        self._gamma = 1.0
        self._rho = 0.0
        self._agirlik: np.ndarray | None = None

    # -- uydurma -------------------------------------------------------------

    def uydur(self, ev: Sequence[str], dep: Sequence[str],
              ev_gol: Sequence[int], dep_gol: Sequence[int],
              gun_farki: Sequence[float]) -> bool:
        """Güçleri uydur. `gun_farki` her maçın **kaç gün önce** olduğudur.

        `False` döner ancak kesit `EN_AZ_KESIT`'in altındaysa; o durumda
        model kullanılamaz ve çağıran düzgün dağılıma düşer.
        """
        n = len(ev)
        if n < EN_AZ_KESIT:
            return False

        takimlar = sorted(set(ev) | set(dep))
        self._takimlar = {t: i for i, t in enumerate(takimlar)}
        T = len(takimlar)
        h = np.fromiter((self._takimlar[t] for t in ev), dtype=np.int64, count=n)
        a = np.fromiter((self._takimlar[t] for t in dep), dtype=np.int64, count=n)
        hg = np.asarray(ev_gol, dtype=float)
        ag = np.asarray(dep_gol, dtype=float)
        w = np.exp(-self.xi * np.asarray(gun_farki, dtype=float))

        # Takım başına ağırlıklı maç sayısı — az oynayan takım ortalamaya
        # çekilecek (bkz. `EN_AZ_MAC`).
        mac = np.bincount(h, weights=w, minlength=T) + np.bincount(a, weights=w, minlength=T)
        self._agirlik = mac

        atilan = (np.bincount(h, weights=w * hg, minlength=T)
                  + np.bincount(a, weights=w * ag, minlength=T))
        yenen = (np.bincount(h, weights=w * ag, minlength=T)
                 + np.bincount(a, weights=w * hg, minlength=T))

        # Tur acikca yazilir. `np.ones(T)` numpy 2.2 govdesinde SEKILLI bir tur
        # cikarsiyor (`ndarray[tuple[int], float64]`, yani "tam 1 boyutlu") ve
        # asagidaki `np.where` / carpim genel `ndarray` dondurdugu icin mypy her
        # yeniden atamayi reddediyordu. Kod dogru; daralan sey numpy'nin sekil
        # tiplemesiydi ve surumden surume degisiyor (numpy 2.4 govdesinde ayni
        # kod uyari uretmiyor). Acik anotasyon ikisinde de gecer, davranisi
        # degistirmez ve bir dahaki stub degisikliginde yeniden kirilmaz.
        atak: np.ndarray = np.ones(T)
        savunma: np.ndarray = np.ones(T)
        gamma = 1.3  # ev avantajı için makul başlangıç; sonuç ondan bağımsız

        for _ in range(EN_COK_YINELEME):
            onceki = np.concatenate([atak, savunma, [gamma]])

            # α_i = atılan_i / Σ (rakibin savunması · ev ise γ)
            payda = (np.bincount(h, weights=w * savunma[a] * gamma, minlength=T)
                     + np.bincount(a, weights=w * savunma[h], minlength=T))
            atak = np.where(payda > 0, atilan / np.maximum(payda, 1e-12), atak)

            # β_i = yenen_i / Σ (rakibin hücumu · deplasmandaysa γ)
            payda = (np.bincount(h, weights=w * atak[a], minlength=T)
                     + np.bincount(a, weights=w * atak[h] * gamma, minlength=T))
            savunma = np.where(payda > 0, yenen / np.maximum(payda, 1e-12), savunma)

            # γ = Σ ev golü / Σ (α_ev · β_dep)
            pay = float((w * hg).sum())
            payda_g = float((w * atak[h] * savunma[a]).sum())
            gamma = pay / payda_g if payda_g > 0 else gamma

            # Tanımlanabilirlik: α'nın ortalaması 1'e sabitlenir. Aksi halde
            # (α·c, β/c) aynı olabilirliği verir ve sayılar sürüklenir.
            olcek = float(atak.mean())
            if olcek > 0:
                atak = atak / olcek
                savunma = savunma * olcek

            if float(np.abs(np.concatenate([atak, savunma, [gamma]]) - onceki).max()) < DURMA_ESIGI:
                break

        # Az oynayan takımı havuz ortalamasına çek — gürültüyü güç sanmamak
        # için. Çekim oranı ağırlıklı maç sayısıyla artar.
        # Ad `pay` DEGIL: dongu icinde `pay` bir skalerdi (γ'nin payi) ve
        # ayni adi burada diziye baglamak mypy'nin hakli olarak yakaladigi
        # bir tur cakismasiydi.
        cekim = np.clip(mac / EN_AZ_MAC, 0.0, 1.0)
        atak = cekim * atak + (1.0 - cekim) * 1.0
        savunma = cekim * savunma + (1.0 - cekim) * float(savunma.mean())

        self._atak, self._savunma, self._gamma = atak, savunma, gamma
        self._rho = self._rho_uydur(h, a, hg.astype(int), ag.astype(int), w)
        return True

    def _rho_uydur(self, h: np.ndarray, a: np.ndarray,
                   hg: np.ndarray, ag: np.ndarray, w: np.ndarray) -> float:
        """`ρ`yu ağırlıklı log-olabilirliği enbüyükleyerek ara.

        Yalnızca dört düşük skor hücresi `ρ`ya bağlıdır; geri kalan bütün
        maçların katkısı sabittir ve aramaya girmez. Bu, aramayı hem hızlı
        hem sayısal olarak kararlı yapar.
        """
        lam, mu = self._lambda(h, a)
        dusuk = (hg <= 1) & (ag <= 1)
        if not dusuk.any():
            return 0.0
        lam_d, mu_d = lam[dusuk], mu[dusuk]
        hg_d, ag_d, w_d = hg[dusuk], ag[dusuk], w[dusuk]

        # Maskeler ve katsayilar aramanin DISINDA bir kez hesaplanir.
        # Icinde hesaplanmalari ~115 kez tekrar demekti ve tur basina
        # uydurmanin maliyetinin cogu oradaydi.
        m00 = (hg_d == 0) & (ag_d == 0)
        m01 = (hg_d == 0) & (ag_d == 1)
        m10 = (hg_d == 1) & (ag_d == 0)
        m11 = (hg_d == 1) & (ag_d == 1)
        # tau = 1 + kat·rho biciminde yazilir; `kat` rho'dan bagimsiz.
        kat = np.zeros_like(lam_d)
        kat[m00] = -lam_d[m00] * mu_d[m00]
        kat[m01] = lam_d[m01]
        kat[m10] = mu_d[m10]
        kat[m11] = -1.0

        def skor(rho: float) -> float:
            tau = 1.0 + kat * rho
            if (tau <= 0).any():
                return -np.inf
            return float((w_d * np.log(tau)).sum())

        izgara = np.linspace(RHO_ALT, RHO_UST, RHO_IZGARA)
        degerler = [skor(float(r)) for r in izgara]
        i = int(np.argmax(degerler))
        alt = float(izgara[max(0, i - 1)])
        ust = float(izgara[min(len(izgara) - 1, i + 1)])
        for _ in range(RHO_BOLME):
            m1 = alt + (ust - alt) / 3.0
            m2 = ust - (ust - alt) / 3.0
            if skor(m1) < skor(m2):
                alt = m1
            else:
                ust = m2
        return (alt + ust) / 2.0

    # -- tahmin --------------------------------------------------------------

    def _lambda(self, h: np.ndarray, a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        assert self._atak is not None and self._savunma is not None
        lam = self._atak[h] * self._savunma[a] * self._gamma
        mu = self._atak[a] * self._savunma[h]
        return (np.clip(lam, 1e-6, LAMBDA_TAVANI),
                np.clip(mu, 1e-6, LAMBDA_TAVANI))

    def biliyor(self, ev: str, dep: str) -> bool:
        return (self._atak is not None
                and ev in self._takimlar and dep in self._takimlar)

    def beklenen_goller(self, ev: str, dep: str) -> tuple[float, float]:
        h = np.array([self._takimlar[ev]])
        a = np.array([self._takimlar[dep]])
        lam, mu = self._lambda(h, a)
        return float(lam[0]), float(mu[0])

    def tahmin(self, ev: str, dep: str) -> dict[str, float]:
        """Bir maçın 1X2 olasılığı — skor ızgarasından toplanır."""
        if not self.biliyor(ev, dep):
            return dict.fromkeys(SYMBOLS, 1.0 / len(SYMBOLS))
        lam, mu = self.beklenen_goller(ev, dep)
        return skor_dagilimindan_1x2(lam, mu, self._rho)

    @property
    def rho(self) -> float:
        return self._rho

    @property
    def gamma(self) -> float:
        return self._gamma


def _poisson_vektoru(lam: float, n: int = MAKS_GOL) -> np.ndarray:
    """`P(X=k)`, k = 0..n. Yineleyerek hesaplanır: `p_k = p_{k−1}·λ/k`.

    `math.factorial` yerine yineleme, büyük `k`da taşmayı ve gereksiz
    hassasiyet kaybını önler.
    """
    p = np.empty(n + 1)
    p[0] = math.exp(-lam)
    for k in range(1, n + 1):
        p[k] = p[k - 1] * lam / k
    return p


def skor_dagilimindan_1x2(lam: float, mu: float, rho: float) -> dict[str, float]:
    """Dixon-Coles düzeltmeli skor ızgarasından 1X2.

    Izgara `MAKS_GOL`da kesildiği için toplam tam 1 değildir; normalize
    edilir. Kesilen kuyruk gerçekçi `λ` değerlerinde (≤4) 10⁻⁹, tavanda
    (6,0) 10⁻⁴'ün altındadır ve normalizasyon onu üç sembole **oranlı**
    dağıtır — yani kesme hiçbir sembolü kayırmaz.
    """
    pe = _poisson_vektoru(lam)
    pd = _poisson_vektoru(mu)
    m = np.outer(pe, pd)
    # düşük skor düzeltmesi — yalnızca dört hücre
    m[0, 0] *= 1.0 - lam * mu * rho
    m[0, 1] *= 1.0 + lam * rho
    m[1, 0] *= 1.0 + mu * rho
    m[1, 1] *= 1.0 - rho
    m = np.maximum(m, 0.0)

    ev = float(np.tril(m, -1).sum())      # ev golü > dep golü
    ber = float(np.trace(m))
    dep = float(np.triu(m, 1).sum())
    toplam = ev + ber + dep
    if toplam <= 0:
        return dict.fromkeys(SYMBOLS, 1.0 / len(SYMBOLS))
    return {"1": ev / toplam, "0": ber / toplam, "2": dep / toplam}


def _gun(ham: Any) -> float:
    """`YYYY-MM-DD` → sıra günü. Bozuk tarih sessizce 0 olmaz, hata verir."""
    from datetime import date

    y, a, g = str(ham)[:10].split("-")
    return float(date(int(y), int(a), int(g)).toordinal())


def dc_tablosu(satirlar: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Her maç için, **o maçtan önceki** maçlarla uydurulmuş DC tahmini.

    `elo.elo_tablosu` ile aynı sözleşme ve aynı disiplin, tek farkla: Elo
    maç maç güncellenirken DC **tur tur yeniden uydurulur**. Tur ölçüsü ISO
    haftadır (`iso_yil`, `iso_hafta`) — korpusun kendi gruplaması.

    Maç başına yeniden uydurmak doğru olurdu ama 31 bin uydurma anlamına
    gelirdi ve kazancı yok: aynı haftanın maçları arasında güçler ölçülebilir
    biçimde değişmez. Hafta başına uydurmak **muhafazakâr** taraftadır —
    bir haftanın maçları birbirinin sonucunu görmez.

    `dc_var=False` olan maçta üç olasılık da 1/3'tür ve bayrak kapalıdır.
    """
    n = len(satirlar)
    out: list[dict[str, Any]] = [
        {"dc_var": False, **{f"dc_{s}": 1.0 / len(SYMBOLS) for s in SYMBOLS}}
        for _ in range(n)
    ]
    if not satirlar:
        return out

    gunler = [_gun(r["tarih"]) for r in satirlar]
    # Turlar kronolojik sırada; her tur icin ONCEKI turlarin maclari.
    tur_anahtari = [(int(r.get("iso_yil") or 0), int(r.get("iso_hafta") or 0),
                     gunler[i]) for i, r in enumerate(satirlar)]
    sira = sorted(range(n), key=lambda i: (tur_anahtari[i][0], tur_anahtari[i][1],
                                           tur_anahtari[i][2], satirlar[i]["lig"],
                                           satirlar[i]["ev"]))

    turlar: list[list[int]] = []
    onceki: tuple[int, int] | None = None
    for i in sira:
        anahtar = (tur_anahtari[i][0], tur_anahtari[i][1])
        if anahtar != onceki:
            turlar.append([])
            onceki = anahtar
        turlar[-1].append(i)

    ev: list[str] = []
    dep: list[str] = []
    hg: list[int] = []
    ag: list[int] = []
    gun: list[float] = []

    for tur in turlar:
        simdi = max(gunler[i] for i in tur)
        if len(ev) >= EN_AZ_KESIT:
            model = DixonColes()
            if model.uydur(ev, dep, hg, ag, [simdi - g for g in gun]):
                for i in tur:
                    r = satirlar[i]
                    if model.biliyor(r["ev"], r["dep"]):
                        p = model.tahmin(r["ev"], r["dep"])
                        out[i] = {"dc_var": True, **{f"dc_{s}": p[s] for s in SYMBOLS}}

        # --- tahmin URETILDIKTEN SONRA bu turun maclari gecmise eklenir ---
        for i in tur:
            r = satirlar[i]
            eg, dg = r.get("ev_gol"), r.get("dep_gol")
            if eg is None or dg is None:
                continue  # golu olmayan mac modele girmez (doktrin 2)
            ev.append(r["ev"])
            dep.append(r["dep"])
            hg.append(int(eg))
            ag.append(int(dg))
            gun.append(gunler[i])

    return out


class DcTahminci(Tahminci):
    """Dixon-Coles'u tek başına bir tahminci olarak sunar.

    Güçleri **yeniden uydurmaz**: `egitim._zenginlestirilmis_korpus` zaten
    tur tur uydurup `dc_*` alanlarını haftaya yazıyor ve o hesap sızıntıya
    karşı doğru sırada yapılıyor (`dc_tablosu`). Burada yeniden uydurmak
    hem pahalı olurdu hem de **daha kötü**: `egit` çağrısı sezon dışarıda
    bırakmalı koşumda gelecek sezonları da görür, oysa `dc_tablosu`
    yalnızca geçmişi görüyor.

    Bu yüzden `egit` bilerek no-op'tur ve bu bir eksiklik değil, ölçümün
    doğru tarafında durmaktır.

    Kupon haftalarında `dc_var` kapalıdır (korpus dışı takımlar için güç
    yok) ve düzgün dağılım döner.
    """

    ad = "dixon_coles"
    aciklama = "Gollerden hucum/savunma gucu; piyasadan bagimsiz gorus"

    def tahmin(self, hafta: Girdi) -> list[dict[str, float]]:
        esit = {s: 1.0 / len(SYMBOLS) for s in SYMBOLS}
        ozellikler = hafta.get("ozellikler") or []
        n = len(hafta.get("results") or "") or len(ozellikler)
        out: list[dict[str, float]] = []
        for i in range(n):
            o = ozellikler[i] if i < len(ozellikler) else {}
            if o.get("dc_var"):
                out.append({s: float(o[f"dc_{s}"]) for s in SYMBOLS})
            else:
                out.append(dict(esit))
        return out
