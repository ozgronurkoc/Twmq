"""Asya handikabı + alt/üst 2.5 → skor dağılımı → 1X2 (A6).

Proje bugüne kadar **yalnızca 1X2** pazarını kullandı. Oysa football-data'nın
`build_egitim.py`'nin zaten indirdiği ana lig dosyaları iki fiyat daha
taşıyor ve ikisi de korpusun 22 liginin dördü sezonunda **%99,9** kapsamda:

    alt/üst 2.5    beklenen TOPLAM golü çiviler
    Asya handikabı beklenen GOL FARKINI (supremacy) çiviler

İkisi birlikte bir skor dağılımı ima eder ve oradan bir 1X2 türetilebilir.
**Bu, A1–A3'te denenip başarısız olan dokuz özellikten farklı bir şeydir:**
onlar 1X2 fiyatının ÜSTÜNE eklenen özelliklerdi, bu ise aynı maça verilmiş
bağımsız ikinci ve üçüncü fiyat.

─── Türetme ──────────────────────────────────────────────────────────────

1. Her iki pazar da iki sonuçludur; marj arındırılır (A5'in kuralı gereği
   bunlar **seviye** ölçüsüdür, `orantili` değil varsayılan yöntem kullanılır).
2. Alt/üst → `P(toplam ≥ 3)`; `Poisson(μ)` altında μ tek çözümdür (kuyruk
   μ'de kesin artan), ikiye bölmeyle bulunur.
3. Handikap → supremacy δ. Ev takımı `D + h > 0` ise kapar; `D` iki bağımsız
   Poisson'un farkıdır (λ_ev = (μ+δ)/2, λ_dep = (μ−δ)/2). Kapama olasılığı
   δ'da artan olduğu için yine ikiye bölme.
4. `D`'nin dağılımından 1X2: `P(D>0)`, `P(D=0)`, `P(D<0)`.

**Çeyrek çizgiler ihmal edilemez** — arşivdeki çizgilerin **%53'ü** çeyrek
(−0,25 / +0,25 / −0,75 …). Böyle bir bahis iki yarım bahse bölünür ve tam
sayı çizgide iade (push) vardır; `ah_kapama` bunların hepsini taşır.

─── Ölçülen sonuç: GEÇMEDİ ───────────────────────────────────────────────

Ham türetme piyasadan **kötü** çıktı (+0,00104 Brier). Teşhis, bağımsız
Poisson'un bilinen kusuruydu: **beraberliği eksik tahmin ediyor** — model
%24,23, gerçek %26,09. Bir beraberlik şişirme (ρ) ve bir sıcaklık (β)
parametresi eklenip **sezon dışarıda bırakmalı** uyduruldu (dört fold,
parametreler yalnızca eğitim sezonlarından):

    tutulan  ρ      β      piyasa   türet+d   fark
    2122     0,166  1,15   0,5943   0,5941    −0,00021
    2223     0,179  1,15   0,5929   0,5928    −0,00014
    2324     0,156  1,15   0,5921   0,5920    −0,00015
    2425     0,168  1,16   0,5954   0,5956    +0,00025

    TOPLAM (31.101 maç · 183 hafta)
      türet+düzeltme  −0,000063   %95 [−0,000287, +0,000155]  geçmedi
      50/50 karışım   −0,000107   %95 [−0,000223, +0,0000038] geçmedi

**Yöntem notu — bir kez yanlış okundu.** İlk koşumda karışımın üst sınırı
sıfırın hemen altında göründü ve "geçti" sanıldı. İki hata vardı: bootstrap
**maç** düzeyindeydi (proje kuralı **hafta**) ve verdict tek bir bootstrap
kuantiline dayanıyordu. Hafta düzeyine geçilip on ayrı tohumla koşulunca
**onunda da geçmedi**. Sınırdaki bir aralığı tek tohumla okumak, aralığın
kendisini görmezden gelmektir.

─── Ne öğrenildi ─────────────────────────────────────────────────────────

Handikap ve alt/üst fiyatları, 1X2 fiyatının **ötesinde** ölçülebilir bilgi
taşımıyor — üç pazar aynı görüşün üç yüzü. A4'ün "mevcut veriden türetilebilir
bir özellik piyasayı geçemiyor" hükmü, elde olup bakılmamış **son** veri
kaynağıyla da sınandı ve ayakta kaldı.

    python -m spor_toto.skor            # turetmeyi tek mac icin dene
"""
from __future__ import annotations

import math
from collections import defaultdict

from .odds import implied_probs

#: Skellam dağılımı için gol üst sınırı. 12, Poisson kuyruğunun ihmal
#: edilebilir hale geldiği yer (λ≈3'te P(X>12) ≈ 1e-5) ve dağılım zaten
#: 1'e normalize ediliyor.
MAKS_GOL = 12

#: μ aramasının sınırları. Alt sınır sıfırdan uzak tutuluyor: `p_ust` çok
#: küçükken μ→0 giderken sayısal olarak kararsızlaşır.
MU_ALT, MU_UST = 0.05, 12.0

#: İkiye bölme adım sayısı. Sabit — aynı girdi her makinede aynı çıktıyı
#: versin (`evaluate`in sabit tohumuyla aynı gerekçe).
BOLME_ADIMI = 60


def poisson_pmf(lam: float, k: int) -> float:
    """`P(X = k)`, `X ~ Poisson(lam)`. Logaritma üzerinden — taşma olmaz."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def mu_coz(p_ust: float) -> float:
    """`P(toplam ≥ 3) = p_ust` olacak şekilde Poisson ortalaması.

    Kuyruk μ'de kesin artandır, yani kök tektir ve ikiye bölme güvenlidir.
    """
    def ust(mu: float) -> float:
        return 1.0 - sum(poisson_pmf(mu, k) for k in (0, 1, 2))

    alt, ustsinir = MU_ALT, MU_UST
    for _ in range(BOLME_ADIMI + 20):
        orta = (alt + ustsinir) / 2
        if ust(orta) < p_ust:
            alt = orta
        else:
            ustsinir = orta
    return (alt + ustsinir) / 2


def fark_dagilimi(lam_ev: float, lam_dep: float) -> dict[int, float]:
    """`P(D = d)`, `D = ev golü − deplasman golü` (iki Poisson'un farkı)."""
    p_ev = [poisson_pmf(lam_ev, k) for k in range(MAKS_GOL + 1)]
    p_dep = [poisson_pmf(lam_dep, k) for k in range(MAKS_GOL + 1)]
    dag: dict[int, float] = defaultdict(float)
    for i, x in enumerate(p_ev):
        for j, y in enumerate(p_dep):
            dag[i - j] += x * y
    return dict(dag)


def ah_kapama(dag: dict[int, float], h: float) -> tuple[float, float]:
    """Çizgi `h` için (kazanma, kaybetme) — pay ağırlıklı.

    football-data'da `AHh` **ev takımına** uygulanır; ev `D + h > 0` ise
    kapar, `D + h = 0` ise iade (push), altındaysa kaybeder.

    Çeyrek çizgi (±0,25 / ±0,75) iki yarım bahse bölünür: `h ∓ 0,25`.
    Arşivdeki çizgilerin **%53'ü** böyle, yani bu dal istisna değil ana yol.
    """
    dortte_bir = round(h * 4)
    bilesenler: tuple[tuple[float, float], ...]
    if dortte_bir % 2 != 0:
        bilesenler = ((h - 0.25, 0.5), (h + 0.25, 0.5))
    else:
        bilesenler = ((h, 1.0),)

    kazanc = kayip = 0.0
    for cizgi, pay in bilesenler:
        # Tam sayı çizgide `D + cizgi == 0` iadedir ve iki toplama da
        # girmez — oran zaten iadeyi hariç tutan bir olasılık ifade eder.
        kazanc += pay * sum(v for d, v in dag.items() if d + cizgi > 0)
        kayip += pay * sum(v for d, v in dag.items() if d + cizgi < 0)
    return kazanc, kayip


def delta_coz(mu: float, p_ev_ah: float, h: float) -> float:
    """`P_ah(ev kapar) = p_ev_ah` olacak şekilde supremacy (δ).

    Kapama olasılığı δ'da artandır; ikiye bölme yine güvenli. Sınırlar μ'nün
    biraz içinde tutuluyor çünkü |δ| = μ'de deplasman λ'sı sıfıra iner ve
    dağılım dejenere olur.
    """
    def kapama_orani(delta: float) -> float | None:
        lam_ev, lam_dep = (mu + delta) / 2, (mu - delta) / 2
        if lam_ev <= 1e-9 or lam_dep <= 1e-9:
            return None
        kazanc, kayip = ah_kapama(fark_dagilimi(lam_ev, lam_dep), h)
        toplam = kazanc + kayip
        return kazanc / toplam if toplam > 0 else None

    alt, ust = -mu * 0.98, mu * 0.98
    for _ in range(BOLME_ADIMI):
        orta = (alt + ust) / 2
        deger = kapama_orani(orta)
        if deger is None:
            break
        if deger < p_ev_ah:
            alt = orta
        else:
            ust = orta
    return (alt + ust) / 2


def turetilmis_1x2(p_ust: float, p_ev_ah: float, h: float
                   ) -> dict[str, float] | None:
    """Alt/üst ve handikap olasılıklarından 1X2. Çözülemezse `None`."""
    mu = mu_coz(p_ust)
    delta = delta_coz(mu, p_ev_ah, h)
    lam_ev, lam_dep = (mu + delta) / 2, (mu - delta) / 2
    if lam_ev <= 0 or lam_dep <= 0:
        return None
    dag = fark_dagilimi(lam_ev, lam_dep)
    ev = sum(v for d, v in dag.items() if d > 0)
    beraberlik = dag.get(0, 0.0)
    dep = sum(v for d, v in dag.items() if d < 0)
    toplam = ev + beraberlik + dep
    if toplam <= 0:
        return None
    return {"1": ev / toplam, "0": beraberlik / toplam, "2": dep / toplam}


def oranlardan_1x2(ust: float, alt: float, ah_ev: float, ah_dep: float,
                   h: float) -> dict[str, float] | None:
    """Ham oranlardan doğrudan türetilmiş 1X2 — marj arındırma dahil."""
    if min(ust, alt, ah_ev, ah_dep) <= 1.0:
        return None
    p_ust = implied_probs({"u": ust, "a": alt})["u"]
    p_ah = implied_probs({"h": ah_ev, "d": ah_dep})["h"]
    return turetilmis_1x2(p_ust, p_ah, h)


def beraberlik_duzelt(p: dict[str, float], rho: float, beta: float
                      ) -> dict[str, float]:
    """Bağımsız Poisson'un beraberlik açığını kapatan iki parametreli düzeltme.

    `rho` beraberliği şişirir, `beta` dağılımı keskinleştirir/yumuşatır.
    **Uydurulmuş parametrelerdir** ve sezon dışarıda bırakmalı ölçülmeleri
    şarttır; modül içinde varsayılan değer yoktur, çağıran vermek zorundadır.
    """
    q0 = p["0"] * (1.0 + rho)
    toplam = q0 + p["1"] + p["2"]
    q = {"1": p["1"] / toplam, "0": q0 / toplam, "2": p["2"] / toplam}
    z = {s: max(q[s], 1e-12) ** beta for s in ("1", "0", "2")}
    t = sum(z.values())
    return {s: v / t for s, v in z.items()}


if __name__ == "__main__":  # pragma: no cover - elle kullanim
    ornek = oranlardan_1x2(ust=1.95, alt=1.85, ah_ev=1.90, ah_dep=1.90, h=-0.25)
    print("ornek turetme (ust 1.95 / alt 1.85, AH -0.25 @ 1.90-1.90):")
    print("  ", {k: round(v, 4) for k, v in (ornek or {}).items()})
    print(__doc__.split("─── Ölçülen sonuç")[1].split("─── Ne öğrenildi")[0])
