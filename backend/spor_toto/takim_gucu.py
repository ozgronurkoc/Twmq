"""Takım bazlı istatistik — **küçültmeyle** (Faz 4.3).

`ISTATISTIK_YOL_HARITASI.md` §7 uzun süre şunu yazıyordu:

> *"Takım bazlı istatistik | 216 takım, Süper Lig takımları bile 32 maç.
> Çıkacak sayı güvenilir görünür ama gürültüdür"*

Teşhis doğruydu, **çare yanlıştı**. Az örnekli bir ortalamanın gürültülü
olması onu yasaklamayı değil, *ne kadarının gürültü olduğunu göstermeyi*
gerektirir. Ampirik Bayes küçültmesi (James–Stein) tam bunu yapar::

    x̂_t = μ_L + B_t · (x_t − μ_L),      B_t = τ² / (τ² + σ²/n_t)

`B_t` sayının **ne kadarının takımın kendi verisi** olduğudur: 5 maçlık bir
takımda 0'a yakındır ve tahmin lig ortalamasına çöker; 200 maçlık bir
takımda 1'e yakındır ve takımın kendi sayısı kalır. Yasak yerine bir katsayı
— ve o katsayı arayüzde **görünür**.

─── Neden lig içinde ────────────────────────────────────────────────────

Küçültme lig ortalamasına doğru yapılır, korpus ortalamasına doğru değil.
22 lig aynı havuza konsaydı Süper Lig'in bir takımı Belçika ikinci liginin
ortalamasına çekilirdi; ligler arası gerçek güç farkı gürültü sayılıp
silinirdi. `τ²` de lig içinde kestirilir: takımlar arası yayılım liglere
göre değişir ve tek bir `τ` hepsini yanlış temsil eder.

─── Sayının yanında ne durur ────────────────────────────────────────────

Ürünün değişmeyen kuralı: *hiçbir sayı ölçülmüş isabeti olmadan arayüze
çıkmaz.* Burada karşılığı üç alan ve **üçü de zorunludur**:

``n``       kaç maçtan geldiği
``kucultme``  `B_t` — ne kadarı takımın kendi verisi
``alt``/``ust``  %95 aralık, `√(B_t·σ²/n_t)` üzerinden

Aralık kasıtlı olarak **ham** ortalamanın değil, küçültülmüş tahminin
aralığıdır; ham ortalamanın aralığı 5 maçlık bir takımda o kadar geniştir
ki hiçbir şey söylemez.

**Bir sınır kayda geçiyor.** `τ²` momentler yöntemiyle kestiriliyor ve
kendi belirsizliği aralığa **dahil edilmiyor**; az takımlı liglerde gerçek
aralık buradakinden geniştir. Tam Bayesçi bir hiyerarşi bunu kapatırdı ama
bir MCMC bağımlılığı getirirdi ve kazanç, gösterilen sayının okunuşunu
değiştirmezdi.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

#: %95 aralık için normal katsayı — `ortak.wilson` ile aynı z.
Z95 = 1.959963984540054

#: Bir takımın tabloya girmesi için gereken en az maç. **Küçültme az
#: örnekli takımı zaten lig ortalamasına çekiyor**, yani bu eşik doğruluk
#: için değil okunabilirlik için: 1 maçlık bir satır tabloyu şişirir ve
#: hiçbir şey söylemez.
EN_AZ_MAC = 5

#: Lig içinde `τ²` kestirebilmek için gereken en az takım. Altında
#: takımlar arası yayılım ölçülemez ve küçültme yapılmaz — o durumda
#: `kucultme` alanı 1,0 döner ve **sebebi yazılır**.
EN_AZ_TAKIM = 4

#: Lig tablosu puanlaması. H2H'de (`takim._PUAN`) bilerek ±1/0 kullanıldı
#: çünkü orada soru "üstünlük"tü. Burada soru **başarı**dır ve okurun
#: beklediği ölçek lig tablosununkidir.
PUAN: dict[str, float] = {"1": 3.0, "0": 1.0, "2": 0.0}

#: Tabloya çıkan ölçüler: (alan, açıklama).
OLCULER: tuple[tuple[str, str], ...] = (
    ("puan", "maç başına puan (3/1/0)"),
    ("gol_at", "maç başına atılan gol"),
    ("gol_ye", "maç başına yenilen gol"),
)


def _varyans(degerler: Sequence[float], ortalama: float) -> float:
    n = len(degerler)
    if n < 2:
        return 0.0
    return sum((v - ortalama) ** 2 for v in degerler) / (n - 1)


def kucult(gozlemler: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    """Ampirik Bayes küçültmesi — `{takim: {...}}`.

    `gozlemler` takım başına **maç başına** ham değerlerin listesi.
    Dönen her satır: `ham`, `n`, `kucultulmus`, `kucultme` (B), `alt`, `ust`.

    ─── τ² nasıl kestiriliyor ────────────────────────────────────────────

    Momentler yöntemi: takım ortalamalarının gözlenen yayılımı iki şeyin
    toplamıdır — gerçek takım farkı (`τ²`) ve örnekleme gürültüsü
    (`σ²/n_t`). İkincisi hesaplanabilir, dolayısıyla::

        τ̂² = max(0, Var(x_t) − ortalama(σ²/n_t))

    `max(0, ...)` şart: gözlenen yayılım gürültünün altına düşerse *"gerçek
    takım farkı yok"* demektir ve o zaman **her takım lig ortalamasıdır**.
    Negatif bir `τ²` ile devam etmek küçültmeyi tersine çevirirdi.
    """
    ortalamalar: dict[str, float] = {}
    sayilar: dict[str, int] = {}
    for takim, v in gozlemler.items():
        if v:
            ortalamalar[takim] = sum(v) / len(v)
            sayilar[takim] = len(v)
    if not ortalamalar:
        return {}

    # Havuzlanmis mac ici varyans: tek bir macin degerinin sacilimi.
    hepsi = [x for v in gozlemler.values() for x in v]
    genel = sum(hepsi) / len(hepsi)
    sigma2 = _varyans(hepsi, genel)

    mu = sum(ortalamalar[t] * sayilar[t] for t in ortalamalar) / sum(sayilar.values())
    if len(ortalamalar) < EN_AZ_TAKIM:
        # Yayilim olculemez: kucultme YAPILMAZ ve bu gorunur (B = 1).
        return {t: {"ham": x, "n": sayilar[t], "kucultulmus": x,
                    "kucultme": 1.0, "alt": x, "ust": x, "lig_ortalamasi": mu}
                for t, x in ortalamalar.items()}

    gozlenen = _varyans(list(ortalamalar.values()),
                        sum(ortalamalar.values()) / len(ortalamalar))
    gurultu = sum(sigma2 / sayilar[t] for t in ortalamalar) / len(ortalamalar)
    tau2 = max(0.0, gozlenen - gurultu)

    out: dict[str, dict[str, float]] = {}
    for t, x in ortalamalar.items():
        n = sayilar[t]
        ornek_var = sigma2 / n if n else float("inf")
        b = tau2 / (tau2 + ornek_var) if (tau2 + ornek_var) > 0 else 0.0
        tahmin = mu + b * (x - mu)
        # Sonsal standart hata: B * sigma^2/n  (tau'nun kendi belirsizligi
        # DAHIL DEGIL — modul basligindaki sinir).
        se = math.sqrt(b * ornek_var) if b > 0 else 0.0
        out[t] = {"ham": x, "n": n, "kucultulmus": tahmin, "kucultme": b,
                  "alt": tahmin - Z95 * se, "ust": tahmin + Z95 * se,
                  "lig_ortalamasi": mu}
    return out


# ─── tablo ────────────────────────────────────────────────────────────────

def _gozlemler(satirlar: Sequence[dict[str, Any]]
               ) -> dict[str, dict[str, dict[str, list[float]]]]:
    """`{lig: {olcu: {takim: [deger, ...]}}}` — maç başına ham değerler.

    Her maç **iki satır** üretir (ev ve deplasman). Gol atma/yeme
    simetriktir; puan `PUAN`dan okunur ve deplasman için ters çevrilir.
    """
    out: dict[str, dict[str, dict[str, list[float]]]] = {}
    for r in satirlar:
        lig = r.get("lig")
        ev, dep = r.get("ev"), r.get("dep")
        kod = r.get("kod")
        hg, ag = r.get("ev_gol"), r.get("dep_gol")
        if not (lig and ev and dep) or kod not in PUAN:
            continue
        if hg is None or ag is None:
            continue
        kova = out.setdefault(lig, {ad: {} for ad, _ in OLCULER})
        ters = {"1": "2", "0": "0", "2": "1"}[kod]
        for takim, puan, atilan, yenilen in (
                (ev, PUAN[kod], float(hg), float(ag)),
                (dep, PUAN[ters], float(ag), float(hg))):
            kova["puan"].setdefault(takim, []).append(puan)
            kova["gol_at"].setdefault(takim, []).append(atilan)
            kova["gol_ye"].setdefault(takim, []).append(yenilen)
    return out


def takim_tablosu(satirlar: Sequence[dict[str, Any]] | None = None,
                  lig: str | None = None,
                  sezon: str | None = None) -> dict[str, Any]:
    """Küçültülmüş takım gücü tablosu — `/api/takimlar`ın tek kaynağı.

    `lig` **çıktıyı** süzer, hesabı değiştirmez: küçültme her zaman lig
    içinde yapılır ve süzme sonucu değiştirmez (bekçi:
    `test_lig_suzgeci_sayilari_degistirmez`). `sezon` ise **girdiyi** süzer
    ve sayıları değiştirir — çünkü o zaman ortalama da, yayılım da o
    sezonun içinden hesaplanır.

    ─── Sezonlar havuzlanıyor, ve bu bilinçli ───────────────────────────

    Varsayılan bütün korpustur. Yani gösterilen sayı *"bu kulüp korpus
    dönemi boyunca ne yaptı"*dır, **bugünkü formu değil**. Bu bir eksiklik
    değil bir iş bölümü: anlık gidişat zaten `elo` (rakip gücüne göre
    düzeltilmiş) ve `takim.seri_tablosu` tarafından taşınıyor ve ikisi de
    ölçüldü (§3.27, §3.29). Burada sorulan soru başka: *"az maçlı bir
    takımın sayısına ne kadar güvenilir?"*

    Havuzlamanın bedeli kayda geçiyor: küme değiştiren bir takım (küçülen
    ya da büyüyen kadro) tek bir ortalamayla temsil edilir. `sezon`
    parametresi bunu isteyen için var — ama `n` düşeceği için `kucultme`
    de düşer, yani sayı otomatik olarak daha temkinli olur. Bu tam olarak
    istenen davranıştır.

    Satırlar `puan.kucultulmus`a göre azalan sıralıdır — okurun beklediği
    düzen lig tablosununkidir.
    """
    from .egitim import korpus_yukle

    ham = list(satirlar) if satirlar is not None else korpus_yukle()
    # Secilebilir sezonlar SUZMEDEN ONCE cikarilir. Sonra cikarilsaydi liste
    # secilen sezona duserdi ve arayuzdeki secici ilk secimden sonra tek
    # secenekli kalirdi — yani kullanici geri donemezdi.
    tum_sezonlar = sorted({r["sezon"] for r in ham if r.get("sezon")})
    if sezon is not None:
        ham = [r for r in ham if r.get("sezon") == sezon]
    tablo = _gozlemler(ham)
    ligler: list[dict[str, Any]] = []
    for lig_adi in sorted(tablo):
        if lig is not None and lig_adi != lig:
            continue
        olculer = {ad: kucult(tablo[lig_adi][ad]) for ad, _ in OLCULER}
        takimlar: list[dict[str, Any]] = []
        for takim in sorted(olculer["puan"]):
            n = int(olculer["puan"][takim]["n"])
            if n < EN_AZ_MAC:
                continue
            satir: dict[str, Any] = {"takim": takim, "n": n}
            for ad, _ in OLCULER:
                satir[ad] = olculer[ad].get(takim)
            takimlar.append(satir)
        if not takimlar:
            continue
        takimlar.sort(key=lambda t: -t["puan"]["kucultulmus"])
        ligler.append({
            "lig": lig_adi,
            "takim_sayisi": len(takimlar),
            "kucultme_yapildi": len(olculer["puan"]) >= EN_AZ_TAKIM,
            "takimlar": takimlar,
        })
    return {
        "sezon": sezon,
        # Secilebilir sezonlar GOVDEDE tasiniyor, `/api/meta`da DEGIL.
        # Gerekce maliyet: bu liste korpustan cikiyor ve korpus zaten burada
        # acik; `/api/meta`ya konsaydi her sayfa acilisinda 31 bin satir
        # okunurdu. Arayuz sezon secicisini bu alandan kuruyor — serbest
        # metin kutusu, ilan edilmeyen bir anahtar bicimi yuzunden sessizce
        # bos tablo gosteriyordu.
        "sezonlar": tum_sezonlar,
        "ligler": ligler,
        "olculer": [{"alan": ad, "aciklama": acik} for ad, acik in OLCULER],
        "en_az_mac": EN_AZ_MAC,
        "en_az_takim": EN_AZ_TAKIM,
        "kural": (
            "Sayilar KUCULTULMUS: her tahmin lig ortalamasina dogru "
            "n'e bagli olarak cekilir. `kucultme` alani sayinin ne kadarinin "
            "takimin KENDI verisi oldugunu soyler (1 = tamamen kendi, "
            "0 = tamamen lig ortalamasi). Aralik kucultulmus tahminindir; "
            "tau'nun kendi belirsizligi DAHIL DEGIL."),
    }


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    import argparse
    import json

    from .kosum import belki_kaydet, cli_ekle


    ap = argparse.ArgumentParser()
    ap.add_argument("--lig", default=None)
    ap.add_argument("--sezon", default=None)
    ap.add_argument("--json", action="store_true")
    cli_ekle(ap)
    a = ap.parse_args(argv)

    t = takim_tablosu(lig=a.lig, sezon=a.sezon)
    belki_kaydet("takim_gucu", t, a)
    if a.json:
        print(json.dumps(t, ensure_ascii=False, indent=1))
        return
    if not t["ligler"]:
        print("korpus yok ya da lig bulunamadi")
        return
    for grup in t["ligler"]:
        print(f"\n{grup['lig']} — {grup['takim_sayisi']} takim"
              f"{'' if grup['kucultme_yapildi'] else '  (KUCULTME YOK)'}")
        print(f"{'takim':<22}{'n':>5}{'puan':>8}{'ham':>8}{'kucultme':>10}"
              f"{'%95 aralik':>20}")
        for x in grup["takimlar"]:
            p = x["puan"]
            print(f"{x['takim']:<22}{x['n']:>5}{p['kucultulmus']:>8.3f}"
                  f"{p['ham']:>8.3f}{p['kucultme']:>10.2f}"
                  f"   [{p['alt']:.3f}, {p['ust']:.3f}]")
    print(f"\n{t['kural']}")


if __name__ == "__main__":  # pragma: no cover
    main()
