"""Beraberliğe özel düzeltme — favori gücüne bağlı (Ö3).

─── Soru neden ayrıca soruluyor ──────────────────────────────────────────

Kalibrasyon eğrisi toplamda temiz (§3.18): üç sembol de aralık içinde. Ama
maçları **favorinin gücüne** göre bölünce beraberlikte düzenli bir şekil
çıkıyor — piyasa denk maçlarda beraberliği eksik, açık maçlarda fazla
fiyatlıyor gibi görünüyor:

    favori olasılığı      n       piyasa "0"   gerçek "0"    fark
    %30–40             6.350        %29,55       %30,25     +0,70
    %40–50            11.837        %27,95       %28,86     +0,91  ← aralık dışı
    %50–60             6.720        %25,22       %24,94     −0,28
    %60–70             3.446        %21,22       %20,63     −0,59
    %70+               2.750        %14,69       %14,22     −0,47

Sapma bantlar arasında **tek yönde ilerliyor** ve bu, gürültüden ayrılan
tarafı: rastgele beş sapma bu sırayla dizilmez. Ö3'ün hipotezi budur.

─── Neden karar kuralı değil, olasılık düzeltmesi ────────────────────────

Plan bunu "beraberliğe özel **karar kuralı**" diye yazmıştı. Ö1'den sonra o
biçim yanlış: eski eşik kuralı üç sembole simetrik davranıyor ve beraberliği
mekanik olarak atıyordu; `secim.en_iyi_secim` ise öyle bir kural taşımıyor,
**verilen olasılıklara göre** en iyi planı kuruyor. Yani seçim katmanına
"beraberliği koru" diye bir istisna eklemek, doğru olan optimizasyonu bozup
üstüne bir yama koymak olurdu.

Hipotez zaten olasılıkla ilgili: *piyasa beraberliği yanlış fiyatlıyor.*
Doğru yer o hâlde olasılığın kendisidir. Düzeltilmiş olasılık `en_iyi_secim`e
verilirse seçim katmanı **kendiliğinden** doğru şeyi yapar — beraberliği
gerektiği kadar korur, gerekmediği yerde atar.

─── Model: iki parametre, ve ikisi ayrı sorular ──────────────────────────

Piyasa olasılığı `p`, favorinin olasılığı `f = max(p)`:

    z₀ = log p₀ + a + b·(f − c)      z₁ = log p₁      z₂ = log p₂

`c` eğitim setinin ortalama `f`'idir (uydurulmuş bir eşik değil, merkezleme
sabiti). Softmax ile normalize edilir.

**İki parametre iki ayrı iddiadır ve ayrı ölçülür:**

    a   beraberliği topluca kaydırır — bant bilgisi taşımaz.
        Bu YENİ DEĞİL: `kalibre_bias` olarak zaten ölçüldü ve geçti (§3.11).
    b   sapmanın favori gücüyle değişmesi — Ö3'ün asıl iddiası.

Bu yüzden `beraberlik_sabit` (yalnız `a`) ve `beraberlik_bant` (`a`+`b`)
diye iki tahminci var. Ö3'ün sorusu "bant piyasayı geçiyor mu" değil,
**"bant, sabitin üstüne bir şey koyuyor mu"**. Birincisini sorup ikincisini
sormamak, zaten bilinen bir kazancı yeni bir bulgu sanmak olurdu.

Uydurma **log kaybı** üzerinden; sabit ofsetli iki parametreli çok terimli
lojistik regresyon, yani dışbükey — Newton tek çözüme gider, rastgelelik yok.
Düzenlileştirme `recalibrate.L2` ile aynı ve **ayarlanmadı**.

─── Ölçülen sonuç ────────────────────────────────────────────────────────

`python -m spor_toto.beraberlik` bu ölçümü koşar ve sonucu yazar; sayılar
`docs/ISTATISTIK_YOL_HARITASI.md` §3.21'e oradan geçer.
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Sequence
from typing import Any

from .history import SYMBOLS
from .predict import Girdi, Olasilik, Tahminci, mac_sayisi
from .recalibrate import L2, OLASILIK_TABANI

#: Newton yinelemesinin üst sınırı. Problem dışbükey ve iki boyutlu;
#: ölçümde en fazla 6 adımda durdu. Sınır güvenlik supabı.
EN_COK_YINELEME = 50

#: Newton'un durma ölçütü — adım normu bunun altına inince yakınsamıştır.
YAKINSAMA = 1e-10

#: Eğitim için gereken en az maç. Altında düzeltme yapılmaz; kötü uydurulmuş
#: bir düzeltme, düzeltme yapmamaktan kötüdür.
EN_AZ_MAC = 500


def _noktalar(haftalar: Sequence[Girdi]) -> list[tuple[dict[str, float], float, str]]:
    """(olasılık, favori olasılığı, gerçek sembol) üçlüleri."""
    out: list[tuple[dict[str, float], float, str]] = []
    for hafta in haftalar:
        kodlar = hafta.get("results") or ""
        for k, blok in enumerate(hafta["probs"]):
            if not blok or k >= len(kodlar) or kodlar[k] not in SYMBOLS:
                continue
            p = {s: max(float(blok.get(s, 0.0)), OLASILIK_TABANI) for s in SYMBOLS}
            out.append((p, max(p.values()), kodlar[k]))
    return out


def uygula(p: Olasilik, a: float, b: float, c: float) -> Olasilik:
    """Beraberliğe `a + b·(f − c)` kaydırması, sonra yeniden normalize.

    Yalnızca `"0"` kayar; `"1"` ve `"2"` kendi aralarındaki oranı **korur**.
    Bu bilinçli: hipotez beraberlik hakkında, taraf tercihi hakkında değil.
    """
    p0 = max(float(p.get("0", 0.0)), OLASILIK_TABANI)
    p1 = max(float(p.get("1", 0.0)), OLASILIK_TABANI)
    p2 = max(float(p.get("2", 0.0)), OLASILIK_TABANI)
    f = max(p0, p1, p2)
    agirlik = math.exp(a + b * (f - c))
    z0 = p0 * agirlik
    toplam = z0 + p1 + p2
    return {"1": p1 / toplam, "0": z0 / toplam, "2": p2 / toplam}


def _uydur(noktalar: Sequence[tuple[dict[str, float], float, str]],
           c: float, egimli: bool) -> tuple[float, float]:
    """Log kaybını enazlayan `(a, b)`. `egimli` değilse `b = 0` sabittir.

    Kayıp `(a, b)`'de dışbükeydir (sabit ofsetli çok terimli lojistik), yani
    Newton tek küresel çözüme gider ve başlangıç noktası sonucu değiştirmez.
    Gradyan ve Hessian kapalı formda:

        ∂L/∂u_i = q_i0 − 1{sonuç = 0}          ∂q_i0/∂u_i = q_i0(1 − q_i0)

    burada `u_i = a + b·(f_i − c)` ve `q_i0` düzeltilmiş beraberlik olasılığı.
    """
    a = b = 0.0
    for _ in range(EN_COK_YINELEME):
        g_a = g_b = h_aa = h_ab = h_bb = 0.0
        for p, f, kod in noktalar:
            x = f - c
            p0 = max(p["0"], OLASILIK_TABANI)
            p1 = max(p["1"], OLASILIK_TABANI)
            p2 = max(p["2"], OLASILIK_TABANI)
            z0 = p0 * math.exp(a + b * x)
            q0 = z0 / (z0 + p1 + p2)
            hedef = 1.0 if kod == "0" else 0.0
            fark = q0 - hedef
            w = q0 * (1.0 - q0)
            g_a += fark
            h_aa += w
            if egimli:
                g_b += fark * x
                h_ab += w * x
                h_bb += w * x * x
        g_a += L2 * a
        h_aa += L2
        if not egimli:
            if h_aa <= 0:
                break
            adim_a, adim_b = g_a / h_aa, 0.0
        else:
            g_b += L2 * b
            h_bb += L2
            det = h_aa * h_bb - h_ab * h_ab
            if abs(det) < 1e-18:
                break
            adim_a = (h_bb * g_a - h_ab * g_b) / det
            adim_b = (h_aa * g_b - h_ab * g_a) / det
        a -= adim_a
        b -= adim_b
        if abs(adim_a) + abs(adim_b) < YAKINSAMA:
            break
    return a, b


class BeraberlikTahminci(Tahminci):
    """Piyasanın beraberlik olasılığını düzelten aday (Ö3).

    Eğitilmeden çağrılırsa piyasayı **olduğu gibi** geçirir — bilgisizken
    bir şey uydurmaktansa hiçbir şey yapmamak.
    """

    def __init__(self, egimli: bool = True) -> None:
        self.egimli = egimli
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.egitildi = False

    @property
    def ad(self) -> str:  # type: ignore[override]
        return "beraberlik_bant" if self.egimli else "beraberlik_sabit"

    @property
    def aciklama(self) -> str:  # type: ignore[override]
        return ("Beraberlik düzeltmesi, favori gücüne bağlı (a + b·f)"
                if self.egimli
                else "Beraberlik düzeltmesi, topluca sabit (a)")

    def egit(self, haftalar: Sequence[Girdi]) -> None:
        noktalar = _noktalar(haftalar)
        if len(noktalar) < EN_AZ_MAC:
            self.egitildi = False
            return
        # Merkezleme sabiti EĞİTİM setinden gelir; ölçülen sezon görülmez.
        self.c = sum(f for _, f, _ in noktalar) / len(noktalar)
        self.a, self.b = _uydur(noktalar, self.c, self.egimli)
        self.egitildi = True

    def tahmin(self, hafta: Girdi) -> list[Olasilik]:
        out: list[Olasilik] = []
        for k in range(mac_sayisi(hafta)):
            blok = hafta["probs"][k] if k < len(hafta["probs"]) else None
            if not blok:
                out.append({s: 1.0 / len(SYMBOLS) for s in SYMBOLS})
                continue
            p = {s: float(blok.get(s, 0.0)) for s in SYMBOLS}
            out.append(dict(p) if not self.egitildi
                       else uygula(p, self.a, self.b, self.c))
        return out


def rapor(sezonlar_: Sequence[str] | None = None,
          yol: str | None = None) -> dict[str, Any]:
    """Ö3'ün tam ölçümü: her iki aday piyasaya karşı, ve bant sabite karşı.

    Üçüncü karşılaştırma asıl olandır — ilk ikisi `kalibre_bias`'ın zaten
    bilinen kazancını tekrar ölçebilir, bant terimi ancak **onun üstüne**
    bir şey koyuyorsa Ö3 bir bulgudur.
    """
    from .egitim import korpus_haftalari
    from .evaluate import bootstrap_farki, degerlendir, sezon_anahtari
    from .predict import PiyasaTahminci

    haftalar = korpus_haftalari(sezonlar_, yol)
    olcumler = {
        "piyasa": degerlendir(PiyasaTahminci, haftalar, sezon_anahtari),
        "sabit": degerlendir(lambda: BeraberlikTahminci(egimli=False),
                             haftalar, sezon_anahtari),
        "bant": degerlendir(lambda: BeraberlikTahminci(egimli=True),
                            haftalar, sezon_anahtari),
    }

    def kiyas(aday: str, referans: str) -> dict[str, Any]:
        f = bootstrap_farki(olcumler[aday]["_kayitlar"],
                            olcumler[referans]["_kayitlar"])
        f["gecti"] = bool(f.get("ham_ust") is not None and f["ham_ust"] < 0)
        return f

    # Sezon sezon uydurulan katsayılar — şeklin sezonlar arası tutarlılığı
    # sayının kendisi kadar önemli. Bir sezon `b`'yi ters işaretle
    # uyduruyorsa bulgu gürültüdür ve bu tabloda görünür.
    katsayilar = []
    for s in sorted({str(h["sezon"]) for h in haftalar if h.get("sezon")}):
        egitim = [h for h in haftalar if str(h.get("sezon")) != s]
        t = BeraberlikTahminci(egimli=True)
        t.egit(egitim)
        katsayilar.append({"tutulan": s, "a": t.a, "b": t.b, "c": t.c})

    return {
        "n_hafta": len(haftalar),
        "n_mac": sum(len(h["results"]) for h in haftalar),
        "brier": {k: v["brier"] for k, v in olcumler.items()},
        "katsayilar": katsayilar,
        "sabit_vs_piyasa": kiyas("sabit", "piyasa"),
        "bant_vs_piyasa": kiyas("bant", "piyasa"),
        "bant_vs_sabit": kiyas("bant", "sabit"),
        "yontem": ("sezon disarida birakmali; bootstrap hafta uzerinden ve "
                   "eslestirilmis; gecti = %95 araligin tamami sifirin altinda"),
        "uyari": ("ASIL SORU `bant_vs_sabit`. `bant_vs_piyasa`nin gecmesi tek "
                  "basina bulgu degildir: sabit terim (`kalibre_bias`) zaten "
                  "olculup gecmisti (§3.11)."),
    }


def _yaz(s: dict[str, Any]) -> None:  # pragma: no cover - elle kullanim
    print(f"kesit: {s['n_mac']} mac · {s['n_hafta']} hafta\n")
    print(f"{'tahminci':<18}{'Brier':>9}")
    for ad in ("piyasa", "sabit", "bant"):
        print(f"{ad:<18}{s['brier'][ad]:>9.4f}")
    print(f"\n{'tutulan':<10}{'a':>10}{'b':>10}{'c':>10}")
    for k in s["katsayilar"]:
        print(f"{k['tutulan']:<10}{k['a']:>10.4f}{k['b']:>10.4f}{k['c']:>10.4f}")
    print(f"\n{'kiyas':<20}{'fark':>11}{'%95 alt':>11}{'%95 ust':>11}{'karar':>9}")
    for ad, etiket in (("sabit_vs_piyasa", "sabit − piyasa"),
                       ("bant_vs_piyasa", "bant − piyasa"),
                       ("bant_vs_sabit", "bant − sabit")):
        f = s[ad]
        print(f"{etiket:<20}{f['ham_fark']:>+11.6f}{f['ham_alt']:>+11.6f}"
              f"{f['ham_ust']:>+11.6f}{('GECTI' if f['gecti'] else 'gecmedi'):>9}")
    print(f"\n{s['uyari']}")


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description="O3: beraberlik duzeltmesi")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--korpus", default=None)
    a = ap.parse_args(argv)
    s = rapor(None, a.korpus)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, indent=2, default=str))
    else:
        _yaz(s)


if __name__ == "__main__":  # pragma: no cover
    main()
