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
    for a, b in zip(kenar, kenar[1:]):
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
    print("A) HAFTALIK TUTAN FAVORİ SAYISI — %d hafta × 15 maç" % a["hafta"])
    print(
        "   gerçekleşen : ortalama %.2f · medyan %.0f · sd %.2f · aralık %d–%d"
        % (a["ortalama"], a["medyan"], a["sd"], a["min"], a["max"])
    )
    print("   dağılım     : " + "  ".join("%d:%d" % kv for kv in a["dagilim"].items()))
    print(
        "   piyasa      : beklenen %.2f · bağımsızlık sd'si %.2f"
        % (a["piyasa_beklentisi"], a["bagimsizlik_sd"])
    )
    print(
        "   aşırı yayılım oranı %.2f  (1,00 = 15 bağımsız yazı-turadan ayırt edilemez)"
        % a["asiri_yayilim"]
    )
    print("   maç düzeyinde favori isabeti %%%.1f (%d maç)" % (100 * a["mac_isabeti"], a["mac"]))

    print("\nB) 'BARİZ FAVORİ' NE KADAR SEYREK")
    for s in rapor["bariz_favori"]:
        print(
            "   p_favori ≥ %.2f : %4d maç · hafta başına %.2f · kupon payı %%%.1f"
            % (s["esik"], s["mac"], s["hafta_basina"], 100 * s["pay"])
        )

    print("\nC) FAVORİ GÜCÜ DİLİMLERİ — piyasa ne dedi, ne oldu, haftaya ne kattı")
    print("   %-14s %5s %8s %12s %7s %14s" % ("p_favori", "maç", "piyasa", "gerçekleşen", "fark", "hafta başına"))
    for s in rapor["dilim_karnesi"]:
        print(
            "   [%.2f,%.2f) %6d %8.1f%% %11.1f%% %+7.1f %14.2f"
            % (
                s["alt"],
                s["ust"],
                s["mac"],
                100 * s["piyasa"],
                100 * s["gerceklesen"],
                100 * (s["gerceklesen"] - s["piyasa"]),
                s["hafta_basina_tutan"],
            )
        )

    print("\nD) EN EMİN N FAVORİ BANKO + KALANA ÜÇLÜ — kolon ₺%d" % KOLON_BEDELI)
    print(
        "   %2s %10s %12s %8s %7s %7s %7s %7s %7s %8s"
        % ("N", "kolon", "bedel", "banko%", "15", "14", "13", "12", "12−", "ort.")
    )
    for s in rapor["banko_merdiveni"]:
        print(
            "   %2d %10s %12s %7.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%% %8.2f"
            % (
                s["N"],
                f"{s['kolon']:,}",
                f"₺{s['bedel']:,.0f}",
                100 * s["banko_isabeti"],
                100 * s["kademe"][15],
                100 * s["kademe"][14],
                100 * s["kademe"][13],
                100 * s["kademe"][12],
                100 * s["on_ikinin_alti"],
                s["ortalama_kademe"],
            )
        )
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
