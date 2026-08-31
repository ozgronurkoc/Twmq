"""Kalabalık modeli — havuzu kim, nereye oynuyor? (τ ölçümü)

`getiri.py` müşterek bahsin kenarını tek satırda yazıyor::

    edge = p_piyasa − oynanma_payı

Sağ taraf bugüne kadar bir **varsayımdı**. `getiri.VARSAYILAN_PAY` havuzun
kademelere bölünmesini resmî tablodan alıyordu ama kalabalığın *hangi
sembolü* oynadığını kimse ölçmemişti; §3.34 bunu açıkça yazıyor:

> Sonucu belirleyen tahminci değil **kalabalık varsayımı**: `orneklem`
> modelinde getiri oranı 0,156, `favori` modelinde 0,007 — arada **22 kat**.
> Bu eksenin ihtiyacı yeni model değil, **oynanma paylarının ölçümü**.

Bu modül o ölçümü yapıyor.

─── Kalabalık görünmez, ama izini bırakıyor ─────────────────────────────

Kimse bize kaç kişinin neyi oynadığını söylemiyor. Ama resmî ikramiye
tablosu her hafta bir sayı veriyor: **15'i kaç kolon bildi.** O sayı,
kalabalığın o haftanın gerçek dizisine ne kadar yığıldığının doğrudan
ölçüsüdür. 114 haftada 27.040 tane 15 bilen kolon var ve her biri bir
gözlem.

Model tek parametrelidir ve kasıtlı olarak öyle::

    c_i(sembol) ∝ p_i(sembol)^τ          (maç içinde normalize)
    E[15 bilen] = N_sezon · Π_i c_i(gerçek)

τ = 1  kalabalık tam piyasayı oynuyor          → sürprizde kenar YOK
τ > 1  kalabalık favoriye piyasadan FAZLA yükleniyor → sürpriz ucuz
τ < 1  kalabalık favoriden kaçıyor             → favori ucuz

Bir maçın 15 sembolü çarpım hâlinde girdiği için tek bir τ, hafta düzeyinde
büyük ve ölçülebilir bir fark yaratır: sürprizli hafta ile favorili hafta
arasında 15 bilen sayısı yüzlerce kat ayrışıyor ve τ o ayrışmanın eğimidir.

─── Poisson, sezon sabiti, hacim ofseti ─────────────────────────────────

`N` (o hafta oynanan kolon sayısı) uçta **yok**. İki katmanda soğuruluyor:

    sezon sabiti α_s   sezonun ortalama satış hacmi (kapalı formda çözülür)
    hafta ofseti       ln(12 kademesi havuzu) — haftanın kendi hacminin vekili

12 kademesi vekil olarak seçildi çünkü **hiç kazanansız kalmıyor**, yani
devir almıyor ve payı doğrudan o haftanın satışıyla ölçekleniyor. 15
kademesi bunu yapamazdı: kazanansız kapandığında havuzu ertesi haftaya
taşınır ve vekil, ölçmek istediğimiz şeyin kendisiyle kirlenirdi.

─── Aşırı yayılım gizlenmiyor ───────────────────────────────────────────

Ham Poisson bu veride **çok** dar aralık verir: φ ≈ 390, yani gözlenen
saçılım Poisson'un öngördüğünün yüzlerce katı. Sebep belli — bir oyuncu tek
başına on binlerce kolon oynayabilir, yani "kolon" bağımsız bir deneme
değil. Aralıklar bu yüzden profil olabilirlikte **φ ile ölçeklenir**
(`Δ(−2ℓ) ≤ 1,92·φ`). Ölçeklenmeseydi τ'nun aralığı ±0,01 çıkardı ve
sayı olduğundan kat kat kesin görünürdü.

─── Ölçülen ─────────────────────────────────────────────────────────────

    τ = 1,28   [%95, φ ölçekli: 1,03 – 1,56]     114 hafta · 4 sezon

Aralık 1'i geçmiyor: **kalabalık favoriye piyasadan daha çok yükleniyor.**

Ama sağlama manşeti yumuşatıyor ve yumuşatması gövdede duruyor: dokuz
uyumun dokuzunda da τ > 1 çıkıyor, buna karşılık **aralığı 1'i geçen
yalnızca dördü**, nokta tahmini sezondan sezona **1,04 ile 1,80** arasında
geziyor ve sezon dışarıda bırakmalı iki uyumun aralığı 1'in altına değiyor. Deponun diliyle: **yön sağlam, miktar
belirsiz.** Okunacak cümle "τ = 1,28" değil, "τ birden büyük"tür.

─── Ne ölçmüyor ─────────────────────────────────────────────────────────

**Mutlak beklenen değer ölçülmedi ve bu modül onu iddia etmiyor.** τ iki
kupon arasındaki *oranı* verir. Havuzun satışa oranı (RTP) resmî uçta yok —
dağıtılan havuzu geri hesaplayabiliyoruz, satış hacmini değil. Yani "sürpriz
kuponu para kazandırır" cümlesi bu ölçümden **çıkmaz**; çıkan cümle "sürpriz
kuponu favori kuponundan şu oranda daha iyi öder"dir.

Model ayrıca kalabalığın banko/sistem davranışını görmüyor: tek parametreli
bir güç yasası, gerçek bir oyuncu popülasyonunun kaba bir vekilidir. φ'nin
büyüklüğü bu kabalığın itirafıdır.

Sonucu okumak için: `python -m spor_toto.kalabalik`.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from .history import SYMBOLS
from .surpriz import hafta_kayitlari, sezonlar

#: τ'nun arandığı aralık. Kenarlar ölçüm sonucuna BAKILMADAN, fiziksel
#: anlamdan seçildi: 0,5 kalabalığın piyasanın yarısı kadar keskin olması,
#: 2,5 iki buçuk katı. Bulunan değer kenara dayanırsa gövdede `kenarda`
#: alanı `true` döner — sessizce kırpılmaz.
TAU_ALT, TAU_UST = 0.5, 2.5

#: İki kademeli tarama: önce kaba adım, sonra en iyinin etrafında ince adım.
#: Düz 0,001 adımlı tarama aynı sonucu verir ama ~20 kat yavaştır ve bu
#: fonksiyon bir API ucundan çağrılıyor.
KABA_ADIM, INCE_ADIM = 0.02, 0.001

#: Profil olabilirlik %95 eşiği: χ²₁'in 0,95 kuantilinin yarısı.
PROFIL_ESIK = 1.920729

#: Bir uyumun kurulabilmesi için gereken en az hafta. Altında sezon sabiti
#: kendi gürültüsünü ölçer ve τ okunamaz.
ASGARI_HAFTA = 10

#: `E[15 bilen]` yerine hangi kademenin sayıldığı. 15 tek ve tam eşleşmedir
#: — çarpım formu **tam olarak** onun için geçerlidir. 14 ve altı, bir maçın
#: kaçırıldığı kombinasyonların toplamıdır ve aynı kapalı formu taşımaz.
KADEME = 15


def kalabalik_agirliklari(probs: dict[str, float], tau: float,
                          beraberlik: float = 0.0,
                          deplasman: float = 0.0) -> dict[str, float]:
    """Bir maçta kalabalığın sembol dağılımı — maç içinde normalize.

    `beraberlik`/`deplasman` isteğe bağlı kaymalardır ve **varsayılanı
    sıfırdır**: manşet τ onlarsız ölçülür. Ayrı bir uyumda birlikte
    ölçülüyorlar (bkz. `tau_olcumu` → `genisletilmis`) ama manşete
    girmiyorlar — iki fazladan parametre, tek parametreli sayının
    yorumunu sessizce değiştirirdi.
    """
    ham = {}
    for s in SYMBOLS:
        p = max(probs.get(s, 0.0), 1e-6)
        kayma = beraberlik if s == "0" else (deplasman if s == "2" else 0.0)
        ham[s] = (p ** tau) * math.exp(kayma)
    toplam = sum(ham.values())
    return {s: v / toplam for s, v in ham.items()}


#: İç hesap için sıkıştırılmış hafta kaydı. `uydur` bunu **bir kez** kurar;
#: olabilirlik yüzlerce kez çağrıldığı için maç sözlüklerini her seferinde
#: dolaşmak ölçümün kendisinden pahalıya geliyordu (52 sn → 6 sn).
Kesit = list[tuple[str, float, float, tuple[tuple[float, float, float, int], ...]]]

#: Sembollerin sabit sırası — sıkıştırılmış kayıtta indeks bu sıradadır.
_SIRA = tuple(SYMBOLS)


def _kesit(kayitlar: Sequence[dict[str, Any]], ofset: bool) -> Kesit:
    """(sezon, kazanan, ofset, maçların log-olasılıkları) dörtlüleri."""
    out: Kesit = []
    for k in kayitlar:
        maclar: tuple[tuple[float, float, float, int], ...] = tuple(
            (math.log(max(m["probs"].get(_SIRA[0], 0.0), 1e-6)),
             math.log(max(m["probs"].get(_SIRA[1], 0.0), 1e-6)),
             math.log(max(m["probs"].get(_SIRA[2], 0.0), 1e-6)),
             _SIRA.index(m["code"]))
            for m in k["maclar"]
        )
        off = math.log(k["hacim"]) if (ofset and k["hacim"] > 0) else 0.0
        out.append((k["sezon"], float(k["kazanan"][KADEME]), off, maclar))
    return out


def _hafta_lineer(maclar: tuple[tuple[float, float, float, int], ...],
                  tau: float, beraberlik: float, deplasman: float) -> float:
    """Σ ln c_i(gerçek sonuç) — haftanın kalabalık altındaki log-olasılığı.

    Maç içi normalizasyon `logsumexp` yerine düz toplamla yapılıyor:
    üsler `tau·ln p` biçiminde ve `ln p ≤ 0`, `tau ≤ 2,5` olduğu için
    taşma imkânsız, alttan taşma da `p ≥ 1e-6` kırpmasıyla sınırlı.
    """
    toplam = 0.0
    for lp1, lp0, lp2, idx in maclar:
        a = math.exp(tau * lp1)
        b = math.exp(tau * lp0 + beraberlik)
        c = math.exp(tau * lp2 + deplasman)
        sec = (a, b, c)[idx]
        toplam += math.log(sec / (a + b + c))
    return toplam


def _olabilirlik(kesit: Kesit, tau: float, beraberlik: float = 0.0,
                 deplasman: float = 0.0) -> tuple[float, list[float]]:
    """Poisson log-olabilirliği ve uyum değerleri; α_s kapalı formda çözülür.

    Sezon sabiti serbest bırakıldığı için `Σ y = Σ μ` sezon içinde tam
    olarak sağlanır; α_s'nin kapalı formu budur ve sayısal bir arama
    gerektirmez.
    """
    lineer = [off + _hafta_lineer(maclar, tau, beraberlik, deplasman)
              for _, _, off, maclar in kesit]
    pay: dict[str, float] = {}
    payda: dict[str, float] = {}
    for (s, y, _, _), x in zip(kesit, lineer):
        pay[s] = pay.get(s, 0.0) + y
        payda[s] = payda.get(s, 0.0) + math.exp(x)

    ll = 0.0
    mu_hepsi: list[float] = []
    for (s, y, _, _), x in zip(kesit, lineer):
        alfa = math.log(pay[s] / payda[s]) if pay[s] > 0 and payda[s] > 0 else -50.0
        mu = math.exp(alfa + x)
        mu_hepsi.append(mu)
        ll += y * math.log(mu + 1e-300) - mu
    return ll, mu_hepsi


def _en_iyi_tau(kesit: Kesit) -> tuple[float, float]:
    """Kaba→ince iki kademeli tarama. Döner: (τ, log-olabilirlik)."""
    def tara(alt: float, ust: float, adim: float) -> tuple[float, float]:
        en_iyi = (alt, -math.inf)
        for i in range(round((ust - alt) / adim) + 1):
            t = alt + i * adim
            ll, _ = _olabilirlik(kesit, t)
            if ll > en_iyi[1]:
                en_iyi = (t, ll)
        return en_iyi

    kaba, _ = tara(TAU_ALT, TAU_UST, KABA_ADIM)
    return tara(max(TAU_ALT, kaba - KABA_ADIM),
                min(TAU_UST, kaba + KABA_ADIM), INCE_ADIM)


def _asiri_yayilim(kesit: Kesit, tau: float) -> float:
    """Pearson φ = χ²/sd. 1'e yakınsa Poisson tutuyor, büyükse tutmuyor.

    Alttan 1'e kırpılıyor: φ < 1 (eksik yayılım) aralığı **daraltırdı** ve
    bu veride öyle bir daraltmayı savunacak hiçbir gerekçe yok.
    """
    _, mu = _olabilirlik(kesit, tau)
    sd = len(kesit) - (1 + len({s for s, _, _, _ in kesit}))
    if sd <= 0:
        return 1.0
    khi = sum((y - m) ** 2 / max(m, 1e-9)
              for (_, y, _, _), m in zip(kesit, mu))
    return max(khi / sd, 1.0)


def _profil_araligi(kesit: Kesit, tau: float, ll_tepe: float,
                    phi: float) -> tuple[float, float]:
    """φ ölçekli profil aralığı; her yönde ikili arama.

    Tarama yerine ikili arama: olabilirlik τ'da tek tepeli olduğu için
    eşiği kesen nokta ikili aramayla ~40 çağrıda bulunur, düz taramayla
    2.000'de.
    """
    esik = ll_tepe - PROFIL_ESIK * phi

    def kes(disarda: float) -> float:
        icerde = tau
        if _olabilirlik(kesit, disarda)[0] >= esik:
            return round(disarda, 3)   # aralık arama penceresinin dışına taşıyor
        for _ in range(40):
            orta = (icerde + disarda) / 2.0
            if _olabilirlik(kesit, orta)[0] >= esik:
                icerde = orta
            else:
                disarda = orta
        return round(icerde, 3)

    return kes(TAU_ALT), kes(TAU_UST)


def uydur(kayitlar: Sequence[dict[str, Any]],
          ofset: bool = True) -> dict[str, Any] | None:
    """Tek bir kesitte τ uyumu. Kesit küçükse None."""
    if len(kayitlar) < ASGARI_HAFTA:
        return None
    kesit = _kesit(kayitlar, ofset)
    tau, ll = _en_iyi_tau(kesit)
    phi = _asiri_yayilim(kesit, tau)
    alt, ust = _profil_araligi(kesit, tau, ll, phi)
    return {
        "n": len(kayitlar),
        "tau": round(tau, 3),
        "ga_alt": alt,
        "ga_ust": ust,
        "phi": round(phi, 1),
        "birden_buyuk": alt > 1.0,
        "kenarda": tau <= TAU_ALT + INCE_ADIM or tau >= TAU_UST - INCE_ADIM,
        "kazanan_kolon": sum(k["kazanan"][KADEME] for k in kayitlar),
    }


def prim(p_hedef: float, p_favori: float, tau: float) -> float:
    """Bir sürprizi işaretlemenin ÖDEME primi — favoriye göre oran.

    Türetme kısa ve tamamen `c ∝ p^τ` modelinden çıkıyor. Müşterek havuzda
    bir işaretin beklenen getirisi `p / c` ile orantılıdır (`p` tutturma
    olasılığı, `1/c` payın büyüklüğü). İki işaretin oranı::

        (p_h / c_h) / (p_f / c_f) = (p_h / p_f)^(1−τ)

    Normalizasyon sabiti aynı maç içinde bölündüğü için düşer.

    **Bu oran isabet kaybını zaten içinde taşır**: pay `p`'dir, yani
    sürprizin daha az tutması hesaba girmiştir. τ > 1 iken oran 1'in
    üstündedir; τ = 1 iken tam olarak 1, yani kenar yoktur.

    Ölçmediği şey mutlak değerdir: RTP bilinmediği için `prim > 1` "kâr"
    demek değil, "favoriden iyi" demektir.
    """
    if p_hedef <= 0 or p_favori <= 0:
        return float("nan")
    return (p_hedef / p_favori) ** (1.0 - tau)


def _genisletilmis(kesit: Kesit, tau0: float, ll0: float,
                   phi: float) -> dict[str, Any]:
    """τ + beraberlik + deplasman kayması — manşetin YANINDA duran uyum.

    Sorduğu şey tek bir evet/hayırdır: *kalabalığın piyasadan sapması tek
    bir üsle açıklanıyor mu, yoksa sembole özgü bir kayma da mı var?*
    Nokta tahminleri manşete **girmiyor**; girerlerse tek parametreli
    sayının yorumu sessizce değişirdi.

    Arama kaba→ince iki kademeli ızgaradır. Nelder-Mead denenmedi çünkü
    burada aranan bir optimum değil bir **olabilirlik farkı**: ızgaranın
    en iyisi gerçek optimumun biraz altında kalsa bile oran aşağı
    yanlıdır, yani kararı gevşetmez sıkılaştırır.
    """
    def tara(t_ler, b_ler, d_ler, baslangic):
        en_iyi = baslangic
        for t in t_ler:
            for b in b_ler:
                for d in d_ler:
                    ll, _ = _olabilirlik(kesit, t, b, d)
                    if ll > en_iyi[3]:
                        en_iyi = (t, b, d, ll)
        return en_iyi

    kaba = tara([0.6 + 0.1 * i for i in range(20)],
                [-0.4 + 0.1 * i for i in range(9)],
                [-0.2 + 0.1 * i for i in range(5)],
                (tau0, 0.0, 0.0, ll0))
    t, b, d, ll = tara([kaba[0] - 0.1 + 0.02 * i for i in range(11)],
                       [kaba[1] - 0.1 + 0.02 * i for i in range(11)],
                       [kaba[2] - 0.1 + 0.02 * i for i in range(11)],
                       kaba)
    # Aşırı yayılım ölçekli olabilirlik oranı; χ²₂'nin %95 eşiği 5,99.
    ly = 2.0 * (ll - ll0) / phi
    return {
        "tau": round(t, 3),
        "beraberlik": round(b, 3),
        "deplasman": round(d, 3),
        "olabilirlik_orani": round(ly, 2),
        "esik_khi2_2": 5.99,
        "gecti": ly > 5.99,
        "not": ("İki fazladan parametre manşete GİRMEZ. Geçmesi, kalabalığın "
                "sapmasının tek bir üsle tam açıklanmadığını söyler; hangi "
                "YÖNDE saptığı ayrı ve henüz sağlaması yapılmamış bir "
                "iddiadır — bant tablosu gibi okunmamalı."),
    }


def tau_olcumu(sezon: str | None = None,
               ofset: bool = True) -> dict[str, Any]:
    """Kalabalık ölçümünün tamamı — `/api/surpriz`ın model yarısı.

    Üç kat birlikte döner ve **birlikte okunmalıdır**: tam kesit manşeti,
    sezon dışarıda bırakmalı uyumlar sağlamayı, tek sezon uyumları
    dalgalanmayı verir. Yalnızca ilkini okumak sayıyı olduğundan kesin
    gösterir.
    """
    kayitlar, denetim = hafta_kayitlari(sezon)
    if len(kayitlar) < ASGARI_HAFTA:
        return {"kesit": len(kayitlar), "denetim": denetim, "sezon": sezon,
                "error": f"kesit {ASGARI_HAFTA} haftanın altında"}

    tam = uydur(kayitlar, ofset)
    assert tam is not None
    kesit = _kesit(kayitlar, ofset)
    ll0, _ = _olabilirlik(kesit, tam["tau"])

    mevcut = sorted({k["sezon"] for k in kayitlar})
    disari = {}
    tekil = {}
    if len(mevcut) > 1:
        for s in mevcut:
            u = uydur([k for k in kayitlar if k["sezon"] != s], ofset)
            if u:
                disari[s] = u
            t = uydur([k for k in kayitlar if k["sezon"] == s], ofset)
            if t:
                tekil[s] = t

    uyumlar = [tam, *disari.values(), *tekil.values()]
    return {
        "kesit": len(kayitlar),
        "sezon": sezon,
        "sezonlar": sezonlar(),
        "ofset": ofset,
        "kademe": KADEME,
        "tam": tam,
        "sezon_disarida": disari,
        "tek_sezon": tekil,
        "genisletilmis": _genisletilmis(kesit, tam["tau"], ll0,
                                        tam["phi"]),
        "saglama": {
            "uyum": len(uyumlar),
            "tau_birden_buyuk": sum(1 for u in uyumlar if u["tau"] > 1.0),
            "aralik_biri_geciyor": sum(1 for u in uyumlar if u["birden_buyuk"]),
            "tau_alt": min(u["tau"] for u in uyumlar),
            "tau_ust": max(u["tau"] for u in uyumlar),
        },
        "prim": [
            {"p_favori": pf, "p_surpriz": ps,
             "prim": round(prim(ps, pf, tam["tau"]), 3),
             "prim_3": round(prim(ps, pf, tam["tau"]) ** 3, 3),
             # Prim τ ile ARTAR: alt uç τ'nun alt ucundan gelir.
             "prim_alt": round(prim(ps, pf, tam["ga_alt"]), 3),
             "prim_ust": round(prim(ps, pf, tam["ga_ust"]), 3)}
            for pf, ps in ((0.55, 0.25), (0.50, 0.28), (0.45, 0.30),
                           (0.40, 0.32))
        ],
        "denetim": denetim,
        "sinir": (
            "τ iki kupon arasındaki ORANI verir, mutlak beklenen değeri "
            "değil: havuzun satışa oranı (RTP) resmî uçta yok, dağıtılan "
            "havuz geri hesaplanabiliyor ama satış hacmi hesaplanamıyor. "
            "'Prim > 1' kâr demek değil, 'favoriden iyi' demektir. Model tek "
            "parametrelidir ve kalabalığın banko/sistem davranışını görmez — "
            f"φ = {tam['phi']} bu kabalığın itirafıdır."),
    }


def _aralik(uyum: dict[str, Any]) -> str:
    """`[alt, ust]` — tabloda tek sütun genişliğinde okunsun diye ayrı."""
    return f"[{uyum['ga_alt']:.3f}, {uyum['ga_ust']:.3f}]"


def _main() -> int:
    o = tau_olcumu()
    if o.get("error"):
        print(o["error"])
        return 1
    t = o["tam"]
    print(f"Kesit: {o['kesit']} hafta · {t['kazanan_kolon']:,} adet "
          f"{KADEME} bilen kolon")
    print(f"Aşırı yayılım φ = {t['phi']}  (Poisson ise 1) — "
          f"aralıklar φ ile ölçeklendi\n")

    print(f"{'Kesit':<24}{'n':>5}{'τ':>8}{'%95 aralık':>20}")
    print(f"{'TAM':<24}{t['n']:>5}{t['tau']:>8.3f}{_aralik(t):>20}")
    for ad, blok in (("sezon dışarıda", o["sezon_disarida"]),
                     ("tek sezon", o["tek_sezon"])):
        for s, u in blok.items():
            print(f"{ad + ' · ' + s:<24}{u['n']:>5}{u['tau']:>8.3f}"
                  f"{_aralik(u):>20}")

    s = o["saglama"]
    print(f"\nSağlama: {s['uyum']} uyumun {s['tau_birden_buyuk']}'inde τ > 1; "
          f"aralığı 1'i geçen {s['aralik_biri_geciyor']}. "
          f"τ aralığı {s['tau_alt']:.2f}–{s['tau_ust']:.2f}")

    g = o["genisletilmis"]
    print(f"Genişletilmiş uyum: τ={g['tau']:.3f} beraberlik={g['beraberlik']:+.3f} "
          f"deplasman={g['deplasman']:+.3f} · oran {g['olabilirlik_orani']:.2f} "
          f"(eşik {g['esik_khi2_2']}) → {'geçti' if g['gecti'] else 'geçmedi'}")

    print("\nSürpriz işaretinin ödeme primi (favoriye göre):")
    for p in o["prim"]:
        print(f"   p {p['p_favori']:.2f} → {p['p_surpriz']:.2f}: "
              f"×{p['prim']:.3f}  [{p['prim_alt']:.3f}, {p['prim_ust']:.3f}]"
              f"   üç maçta ×{p['prim_3']:.3f}")
    print(f"\n{o['sinir']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
