"""Favori ekseni — "haftada 7-8 favori tutuyor, o hâlde onları bulalım".

    python scripts/favori_analizi.py          # dört bölüm
    python scripts/favori_analizi.py --json

─── Soru ─────────────────────────────────────────────────────────────────

Yaygın ve sezgisel bir strateji önerisi şudur: her hafta favorilerin
ortalama 7-8'i tutuyor; bültende favorisi **net** maçlar ile favorisi
**güven vermeyen** maçlar var; tutacak olanları ayırabilirsek kuponun
yarısını çözmüş oluruz.

Bu betik o cümleyi dört parçaya ayırıp her parçayı 114 haftalık kupon
kesitinde (`evaluate.kupon_kesiti_tum`) ayrı ayrı ölçer. Hiçbir model
eğitilmez; kullanılan tek girdi piyasanın kendi `p₁/p₂/p₃`südür ve
"favori" her maçta **en yüksek olasılıklı işaret**tir.

A. Sayının kendisi — haftada kaç favori tutuyor, ve o sayının **şekli**
   15 bağımsız yazı-turadan ayırt edilebiliyor mu. Aşırı yayılım oranı
   1'e yakınsa hafta düzeyinde ("bu hafta favoriler tutuyor") tutamak
   yoktur; iş maç maç bir iştir.

B. "Bariz favori" ne kadar seyrek — bülten dengeli maçlardan mı kuruluyor.

C. Tutan favoriler hangi güç diliminden geliyor — haftalık toplam, net
   favorilerden mi yoksa yazı-turaların favori tarafına düşmesinden mi.

D. Öneriyi kuponun kendi parasına çevirir: en emin N favoriyi **banko**,
   kalan 15−N maça **üçlü**. `en iyi kolon = 15 − k` olduğu için kademe
   dağılımı doğrudan bankoların kaçağıdır.

─── Okuma uyarısı ────────────────────────────────────────────────────────

D bölümünün N=6 satırı README §1.1'in 114 haftalık kademe dağılımının
**aynısıdır**. Bu bir tesadüf değil: ürünün ₺210.000 tavanındaki şekli
zaten (6 banko, 0 çifte, 9 üçlü) ve o şekli `secim.en_iyi_secim` seçiyor.
Yani "en emin favorileri bul" burada bir öneri değil, **kurulu davranışın
tarifi**dir; tabloyu "yapılacak iş" diye değil, o davranışın çıplak
karnesi diye okuyun.

Dilim tablosundaki artı farklar (favori piyasanın dediğinden fazla
tutuyor) **yeni bulgu değildir**: aynı sapma ölçüm kütüğünde §3.60/§3.64
olarak kayıtlı ve incelenmiştir — korpus genelinde yoktur (+%0,5) ve
T1'de son sezonda sönmüştür (+%0,3). Kesit etkisidir, üstüne strateji
kurulmaz.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics as st
from collections import Counter

from spor_toto.evaluate import kupon_kesiti_tum

ISARET = ("1", "0", "2")
KOLON_BEDELI = 10.0


def _haftalar() -> list[list[tuple[float, bool]]]:
    """Her hafta için `(favori olasılığı, favori tuttu mu)` listesi."""
    haftalar = []
    for h in kupon_kesiti_tum():
        haftalar.append(
            [
                (max(p.values()), max(ISARET, key=lambda s: p[s]) == g)
                for p, g in zip(h["probs"], h["results"])
            ]
        )
    return haftalar


def sayinin_sekli(haftalar) -> dict:
    """A — haftalık tutan favori sayısı ve bağımsızlıktan sapması."""
    sayilar = [sum(t for _, t in w) for w in haftalar]
    beklenen = [sum(p for p, _ in w) for w in haftalar]
    # Kalibre ve bağımsız olsaydı varyans Poisson-binom varyansı olurdu.
    var_bagimsiz = st.mean([sum(p * (1 - p) for p, _ in w) for w in haftalar])
    tum = [x for w in haftalar for x in w]
    return {
        "hafta": len(haftalar),
        "ortalama": st.mean(sayilar),
        "medyan": st.median(sayilar),
        "sd": st.pstdev(sayilar),
        "min": min(sayilar),
        "max": max(sayilar),
        "dagilim": dict(sorted(Counter(sayilar).items())),
        "piyasa_beklentisi": st.mean(beklenen),
        "bagimsizlik_sd": math.sqrt(var_bagimsiz),
        "asiri_yayilim": st.pvariance(sayilar) / var_bagimsiz,
        "mac_isabeti": sum(t for _, t in tum) / len(tum),
        "mac": len(tum),
    }


def bariz_favori(haftalar) -> list[dict]:
    """B — eşik üstü favorinin hafta başına kaç maçta göründüğü."""
    tum = [p for w in haftalar for p, _ in w]
    n = len(haftalar)
    satir = []
    for esik in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85):
        k = sum(1 for p in tum if p >= esik)
        satir.append({"esik": esik, "mac": k, "hafta_basina": k / n, "pay": k / len(tum)})
    return satir


def dilim_karnesi(haftalar) -> list[dict]:
    """C — favori gücü dilimlerinde piyasa sözü, gerçekleşen ve haftalık katkı."""
    tum = [x for w in haftalar for x in w]
    kenar = (0.0, 0.45, 0.50, 0.55, 0.60, 0.70, 1.01)
    satir = []
    for a, b in itertools.pairwise(kenar):
        d = [(p, t) for p, t in tum if a <= p < b]
        if not d:
            continue
        satir.append(
            {
                "alt": a,
                "ust": b,
                "mac": len(d),
                "piyasa": sum(p for p, _ in d) / len(d),
                "gerceklesen": sum(t for _, t in d) / len(d),
                "hafta_basina_tutan": sum(t for _, t in d) / len(haftalar),
            }
        )
    return satir


def banko_merdiveni(haftalar, n_araligi=range(4, 11)) -> list[dict]:
    """D — en emin N favori banko + kalana üçlü: kademe dağılımı ve bedel."""
    satir = []
    for N in n_araligi:
        secimler = [sorted(w, key=lambda x: -x[0])[:N] for w in haftalar]
        kademeler = [15 - sum(1 for _, t in s if not t) for s in secimler]
        duz = [x for s in secimler for x in s]
        sayim = Counter(kademeler)
        n = len(kademeler)
        kolon = 3 ** (15 - N)
        satir.append(
            {
                "N": N,
                "kolon": kolon,
                "bedel": kolon * KOLON_BEDELI,
                "kademe": {k: sayim.get(k, 0) / n for k in (15, 14, 13, 12)},
                "on_ikinin_alti": sum(v for k, v in sayim.items() if k < 12) / n,
                "ortalama_kademe": st.mean(kademeler),
                "banko_piyasa": sum(p for p, _ in duz) / len(duz),
                "banko_isabeti": sum(t for _, t in duz) / len(duz),
                "hepsi_tuttu": sayim.get(15, 0) / n,
            }
        )
    return satir


def _yaz(rapor: dict) -> None:
    a = rapor["sayinin_sekli"]
    print(f"A) HAFTALIK TUTAN FAVORİ SAYISI — {a['hafta']:.0f} hafta × 15 maç")
    print(f"   gerçekleşen : ortalama {a['ortalama']:.2f} · medyan {a['medyan']:.0f} · "
          f"sd {a['sd']:.2f} · aralık {a['min']:.0f}–{a['max']:.0f}")
    print("   dağılım     : "
          + "  ".join(f"{k:.0f}:{v:.0f}" for k, v in a["dagilim"].items()))
    print(f"   piyasa      : beklenen {a['piyasa_beklentisi']:.2f} · "
          f"bağımsızlık sd'si {a['bagimsizlik_sd']:.2f}")
    print(f"   aşırı yayılım oranı {a['asiri_yayilim']:.2f}  "
          "(1,00 = 15 bağımsız yazı-turadan ayırt edilemez)")
    print(f"   maç düzeyinde favori isabeti %{100 * a['mac_isabeti']:.1f} "
          f"({a['mac']:.0f} maç)")

    print("\nB) 'BARİZ FAVORİ' NE KADAR SEYREK")
    for s in rapor["bariz_favori"]:
        print(f"   p_favori ≥ {s['esik']:.2f} : {s['mac']:4.0f} maç · "
              f"hafta başına {s['hafta_basina']:.2f} · kupon payı %{100 * s['pay']:.1f}")

    print("\nC) FAVORİ GÜCÜ DİLİMLERİ — piyasa ne dedi, ne oldu, haftaya ne kattı")
    print(f"   {'p_favori':<14} {'maç':>5} {'piyasa':>8} {'gerçekleşen':>12} "
          f"{'fark':>7} {'hafta başına':>14}")
    for s in rapor["dilim_karnesi"]:
        print(f"   [{s['alt']:.2f},{s['ust']:.2f}) {s['mac']:6.0f} "
              f"{100 * s['piyasa']:8.1f}% {100 * s['gerceklesen']:11.1f}% "
              f"{100 * (s['gerceklesen'] - s['piyasa']):+7.1f} "
              f"{s['hafta_basina_tutan']:14.2f}")

    print(f"\nD) EN EMİN N FAVORİ BANKO + KALANA ÜÇLÜ — kolon ₺{KOLON_BEDELI:.0f}")
    print(f"   {'N':>2} {'kolon':>10} {'bedel':>12} {'banko%':>8} {'15':>7} {'14':>7} "
          f"{'13':>7} {'12':>7} {'12−':>7} {'ort.':>8}")
    for s in rapor["banko_merdiveni"]:
        kolon = f"{s['kolon']:,}"
        bedel = f"₺{s['bedel']:,.0f}"
        print(f"   {s['N']:2.0f} {kolon:>10} {bedel:>12} "
              f"{100 * s['banko_isabeti']:7.1f}% {100 * s['kademe'][15]:6.1f}% "
              f"{100 * s['kademe'][14]:6.1f}% {100 * s['kademe'][13]:6.1f}% "
              f"{100 * s['kademe'][12]:6.1f}% {100 * s['on_ikinin_alti']:6.1f}% "
              f"{s['ortalama_kademe']:8.2f}")
    print("   N=6 satırı README §1.1'in kademe dağılımıdır — ürünün bugünkü şekli (6, 0, 9).")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="raporu JSON olarak bas")
    args = ap.parse_args(argv)

    haftalar = _haftalar()
    rapor = {
        "sayinin_sekli": sayinin_sekli(haftalar),
        "bariz_favori": bariz_favori(haftalar),
        "dilim_karnesi": dilim_karnesi(haftalar),
        "banko_merdiveni": banko_merdiveni(haftalar),
    }
    if args.json:
        print(json.dumps(rapor, ensure_ascii=False, indent=2, default=str))
    else:
        _yaz(rapor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
