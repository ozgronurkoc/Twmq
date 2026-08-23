"""Benzer maç arama — "bu oranda geçmişte ne olmuş?"

Bir maçın oranını alır, 31 bin maçlık eğitim korpusunda **aynı fiyata sahip**
maçları bulur ve nasıl sonuçlandıklarını sayar:

    python -m spor_toto.benzer --oran 1.82,3.04,2.44

Bu modül tahmin üretmez. Ürettiği tek şey ampirik bir cevaptır: *piyasa bu
fiyatı verdiğinde geçmişte ne oldu.* Asıl sorduğu soru "yüzde kaçı ev sahibi
kazanmış" değil, **"piyasa sözünü tutmuş mu"** — bu yüzden her satırda
piyasanın kendi dediği yüzde de yazar.

─── Neden oran uzayında arama YAPILMAZ ────────────────────────────────────────

En önemli tasarım kararı bu. Aynı gerçek olasılık, farklı marjda tamamen
farklı oran verir: %18 marjlı bir iddaa bülteninde 1.82 ne diyorsa, %7 marjlı
football-data arşivinde başka bir sayı onu der. Ölçüldü — 1.82/3.04/2.44
(marj %28,8) korpusta:

    birebir aynı oran ..............   0 maç
    oran ±%2 .......................   0 maç
    oran ±%10 ......................   0 maç
    olasılık ±2 puan ................ 709 maç

Yani oran uzayında arama sessizce "sonuç yok" der. Eşleme **marj
arındırıldıktan sonra olasılık uzayında** yapılır; `tests/test_benzer.py`
bunu regresyon testine bağlar.

─── Örneklem dürüstlüğü ──────────────────────────────────────────────────────

Bu araç yanlış kullanılmaya en müsait yer olduğu için üç koruma taşır:

1. Hiçbir yüzde **n ve güven aralığı olmadan** dönmez. "44 maçın 35'i ev
   sahibi" tek başına bir bilgi değildir; 44 maçta %80 ile %55 arasındaki
   fark gürültüdür.
2. `AZ_ORNEK` (30) altındaki dilim sayı vermez, "yetersiz" der.
3. Dilimleme (lig × sezon) çoklu karşılaştırma uyarısı bastırır: 22 lig ×
   4 sezon taranırsa rastgele bir yerde çarpıcı bir oran **kesinlikle**
   çıkar ve o bir bulgu değildir.
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .egitim import korpus_yukle
from .odds import (ARINDIRMA_VARSAYILAN, AZ_ORNEK, SEMBOLLER, implied_probs,
                   margin)

#: Aramanın başladığı yarıçap (olasılık puanı). Dar başlanır ki yakın maç
#: varken uzak maç sayılmasın.
BASLANGIC_TOLERANS = 0.01
#: Yarıçap her adımda bu kadar büyür.
TOLERANS_ADIMI = 0.005
#: Genişlemenin durduğu yer. Ötesi "benzer maç" olmaktan çıkar: %5 puan,
#: banko eşiğiyle çifte eşiği arasındaki mesafenin yarısıdır.
EN_COK_TOLERANS = 0.05
#: Uyarlanan aramanın hedeflediği en az örneklem. 200 maçta bir yüzdenin
#: Wilson aralığı ±%7 civarıdır — okunabilir ama hâlâ geniş.
HEDEF_ORNEKLEM = 200
#: Bu sayıdan çok dilim açılırsa çoklu karşılaştırma uyarısı basılır.
COK_DILIM = 8


def _wilson(basari: int, n: int) -> Tuple[float, float]:
    """Oran için Wilson %95 güven aralığı.

    `backtest._wilson` ile aynı formül ve aynı gerekçe: normal yaklaşım
    küçük örneklemde kenarlara yapışır (0/30'da alt sınır eksiye iner).
    Buraya kopyalanmadı, oradan çağrılıyor.
    """
    from .backtest import _wilson as _w
    return _w(basari, n)


def _mesafe(a: Dict[str, float], b: Dict[str, float]) -> float:
    """İki olasılık vektörü arasındaki en büyük tek sembol farkı (L∞).

    Öklid değil L∞: "hiçbir sembolde X puandan fazla ayrılmasın" kuralı,
    kullanıcının kafasındaki "aynı oranlar" fikrine karşılık gelen ölçüdür.
    Öklid, bir sembolde büyük sapmayı başka iki sembolde küçük sapmayla
    örtebilirdi.
    """
    return max(abs(a[s] - b[s]) for s in SEMBOLLER)


@lru_cache(maxsize=8)
def _olasilik_tablosu(yontem: str, korpus: Optional[str]
                      ) -> Tuple[Tuple[Dict[str, float], Dict[str, Any]], ...]:
    """Korpusun tamamının arındırılmış olasılıkları — yöntem başına bir kez.

    Bunsuz her sorgu 31 bin satırı yeniden arındırıyordu (~2 sn). Bir hafta
    sayfası 15 maç için 15 sorgu yapar; onbelleksiz yarım dakika sürerdi.
    Korpus sürümlenmiş bir dosyadır, aynı yöntem hep aynı tabloyu verir.

    Dönen yapı **okunmak içindir**; çağıran taraf satırları değiştirmemeli
    (onbellekteki nesnenin ta kendisidir).
    """
    return tuple((p, r) for p, r in
                 ((implied_probs(r["oranlar"], yontem), r)
                  for r in korpus_yukle(korpus))
                 if len(p) == 3)


def _sayim(maclar: Sequence[Dict[str, Any]],
           piyasa: Dict[str, float]) -> Dict[str, Any]:
    """Bir maç kümesinin 1/0/2 karnesi — her satırda n, GA ve piyasa payı."""
    n = len(maclar)
    satirlar = {}
    for s in SEMBOLLER:
        k = sum(1 for m in maclar if m["kod"] == s)
        if n:
            alt, ust = _wilson(k, n)
        else:
            alt = ust = 0.0
        bekleniyor = piyasa[s]
        satirlar[s] = {
            "adet": k,
            "oran": (k / n) if n else None,
            "ga_alt": alt,
            "ga_ust": ust,
            # Piyasanın dediği bu aralığın DIŞINDAYSA, o fiyatta piyasa
            # sözünü tutmamış demektir. Asıl okunacak sütun budur.
            "piyasa": bekleniyor,
            "fark": ((k / n) - bekleniyor) if n else None,
            "piyasa_ga_icinde": (alt <= bekleniyor <= ust) if n else None,
        }
    return {"n": n, "yeterli": n >= AZ_ORNEK, "semboller": satirlar}


def benzer_maclar(oranlar: Dict[str, float],
                  tolerans: Optional[float] = None,
                  en_az: int = HEDEF_ORNEKLEM,
                  lig: Optional[str] = None,
                  sezon: Optional[str] = None,
                  yontem: str = ARINDIRMA_VARSAYILAN,
                  korpus: Optional[str] = None) -> Dict[str, Any]:
    """Verilen orana benzeyen geçmiş maçları bulur ve karnelerini çıkarır.

    `tolerans=None` iken yarıçap **uyarlanır**: `BASLANGIC_TOLERANS`'tan
    başlar, `en_az` maça ulaşana kadar büyür, `EN_COK_TOLERANS`'ta durur.
    Fiilen kullanılan yarıçap raporda her zaman yazar — genişlemiş bir arama
    kendini gizlememeli.
    """
    if any(v is None or v <= 1.0 for v in oranlar.values()):
        raise ValueError("her oran 1.00'den büyük olmalı")
    hedef = implied_probs(oranlar, yontem)
    if len(hedef) != 3:
        raise ValueError("üç sembolün de oranı gerekli")

    evren = [(p, r) for p, r in _olasilik_tablosu(yontem, korpus)
             if (lig is None or r["lig"] == lig)
             and (sezon is None or r["sezon"] == sezon)]
    # Mesafe bir kez hesaplanır; hem uyarlanan arama hem dilimler bunu okur.
    olculu = sorted(((_mesafe(p, hedef), r) for p, r in evren),
                    key=lambda x: x[0])

    if tolerans is not None:
        kullanilan, genisledi = tolerans, False
    else:
        kullanilan, genisledi = BASLANGIC_TOLERANS, False
        while kullanilan < EN_COK_TOLERANS:
            if sum(1 for d, _ in olculu if d <= kullanilan) >= en_az:
                break
            kullanilan = round(kullanilan + TOLERANS_ADIMI, 6)
            genisledi = True

    bulunan = [r for d, r in olculu if d <= kullanilan]
    rapor: Dict[str, Any] = {
        "oranlar": dict(oranlar),
        "marj": margin(oranlar),
        "arindirma": yontem,
        "hedef_olasilik": hedef,
        "tolerans": kullanilan,
        "tolerans_uyarlandi": tolerans is None,
        "tolerans_genisledi": genisledi,
        "tolerans_tavana_dayandi": (tolerans is None
                                    and kullanilan >= EN_COK_TOLERANS
                                    and len(bulunan) < en_az),
        "evren": len(olculu),
        "filtre": {"lig": lig, "sezon": sezon},
        "toplam": _sayim(bulunan, hedef),
        "uyarilar": [],
    }

    if not bulunan:
        rapor["uyarilar"].append(
            "Bu yarıçapta hiç maç yok. Oran uzayında değil OLASILIK uzayında "
            "arandığı için bu ancak çok uç bir fiyatta olur.")
    elif len(bulunan) < AZ_ORNEK:
        rapor["uyarilar"].append(
            f"Örneklem {len(bulunan)} maç — {AZ_ORNEK} altında yüzde okunmaz.")
    if rapor["tolerans_tavana_dayandi"]:
        rapor["uyarilar"].append(
            f"Yarıçap tavana (±{100*EN_COK_TOLERANS:.0f} puan) dayandı ve "
            f"{en_az} maça ulaşılamadı; bulunanlar 'benzer' sayılamayacak "
            f"kadar uzak olabilir.")
    if rapor["marj"] > 0.12:
        rapor["uyarilar"].append(
            f"Girilen oranın marjı %{100*rapor['marj']:.1f}; korpus ~%7 "
            f"marjlı. Arındırma yöntemi ({yontem}) bu farkta sonucu "
            f"görünür biçimde değiştirir.")

    rapor["dilimler"] = {
        "lig": _dilimle(bulunan, hedef, "lig"),
        "sezon": _dilimle(bulunan, hedef, "sezon"),
    }
    acik = sum(1 for grup in rapor["dilimler"].values()
               for d in grup if d["karne"]["yeterli"])
    if acik > COK_DILIM:
        rapor["uyarilar"].append(
            f"{acik} dilim açıldı. Bu kadar dilimde en çarpıcı olanın "
            f"rastlantı olma ihtimali yüksektir — dilim tek başına bulgu "
            f"değildir.")
    return rapor


def _dilimle(maclar: Sequence[Dict[str, Any]], hedef: Dict[str, float],
             alan: str) -> List[Dict[str, Any]]:
    """Bulunan maçları bir alana göre böler; her dilim kendi n'i ve GA'sıyla."""
    gruplar: Dict[str, List[Dict[str, Any]]] = {}
    for m in maclar:
        gruplar.setdefault(m[alan], []).append(m)
    out = [{"deger": k, "karne": _sayim(v, hedef)}
           for k, v in gruplar.items()]
    out.sort(key=lambda d: -d["karne"]["n"])
    return out


# ─── yazdırma ─────────────────────────────────────────────────────────────────

def _karne_satirlari(karne: Dict[str, Any], girinti: str = "") -> None:
    n = karne["n"]
    if not karne["yeterli"]:
        print(f"{girinti}n={n} — örneklem yetersiz, yüzde yazılmadı.")
        return
    for s in SEMBOLLER:
        r = karne["semboller"][s]
        isaret = "" if r["piyasa_ga_icinde"] else "   ← piyasa GA DIŞINDA"
        print(f"{girinti}'{s}'  {r['adet']:>4}/{n:<5} gerçek %{100*r['oran']:>5.1f} "
              f"[%{100*r['ga_alt']:>4.1f} – %{100*r['ga_ust']:>4.1f}]   "
              f"piyasa %{100*r['piyasa']:>5.1f}  fark {100*r['fark']:>+5.1f}{isaret}")


def yaz(rapor: Dict[str, Any]) -> None:
    o = rapor["oranlar"]
    print("=" * 78)
    print("GEÇMİŞTE BU ORANDA NE OLDU?")
    print("=" * 78)
    print(f"Oran        : {o['1']} / {o['0']} / {o['2']}   (marj %{100*rapor['marj']:.1f})")
    h = rapor["hedef_olasilik"]
    print(f"Piyasa der  : %{100*h['1']:.1f} / %{100*h['0']:.1f} / %{100*h['2']:.1f}"
          f"   (arındırma: {rapor['arindirma']})")
    f = rapor["filtre"]
    kapsam = ", ".join(x for x in (f["lig"], f["sezon"]) if x) or "tüm korpus"
    print(f"Arama       : {kapsam} · {rapor['evren']:,} maç içinde, "
          f"olasılık uzayında ±{100*rapor['tolerans']:.1f} puan"
          f"{' (uyarlandı)' if rapor['tolerans_uyarlandi'] else ''}")
    print()
    print(f"─── BULUNAN {rapor['toplam']['n']} MAÇ " + "─" * 45)
    _karne_satirlari(rapor["toplam"], "  ")

    for ad, baslik in (("lig", "LİG"), ("sezon", "SEZON")):
        dilimler = [d for d in rapor["dilimler"][ad] if d["karne"]["yeterli"]]
        atlanan = len(rapor["dilimler"][ad]) - len(dilimler)
        if not dilimler:
            continue
        print(f"\n─── {baslik} KIRILIMI " + "─" * 50)
        for d in dilimler:
            k = d["karne"]
            hucre = "  ".join(
                f"{s}:%{100*k['semboller'][s]['oran']:.0f}" for s in SEMBOLLER)
            print(f"  {d['deger']:<8} n={k['n']:<5} {hucre}")
        if atlanan:
            print(f"  ({atlanan} dilim {AZ_ORNEK} maçın altında olduğu için yazılmadı)")

    if rapor["uyarilar"]:
        print("\n─── UYARILAR " + "─" * 58)
        for u in rapor["uyarilar"]:
            print(f"  • {u}")


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser(
        description="Bir orana benzeyen geçmiş maçların nasıl sonuçlandığı.")
    ap.add_argument("--oran", required=True,
                    help="1,0,2 sırasıyla virgüllü: 1.82,3.04,2.44")
    ap.add_argument("--tolerans", type=float, default=None,
                    help="olasılık puanı cinsinden yarıçap (ör. 0.02); "
                         "verilmezse örnekleme göre uyarlanır")
    ap.add_argument("--en-az", type=int, default=HEDEF_ORNEKLEM,
                    help="uyarlanan aramanın hedeflediği en az maç")
    ap.add_argument("--lig", default=None)
    ap.add_argument("--sezon", default=None)
    ap.add_argument("--arindirma", default=ARINDIRMA_VARSAYILAN,
                    choices=("orantili", "guc", "shin"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        parcalar = [float(x) for x in a.oran.split(",")]
    except ValueError:
        raise SystemExit("--oran üç sayı olmalı: 1.82,3.04,2.44")
    if len(parcalar) != 3:
        raise SystemExit("--oran üç sayı olmalı: 1.82,3.04,2.44")

    rapor = benzer_maclar({"1": parcalar[0], "0": parcalar[1], "2": parcalar[2]},
                          tolerans=a.tolerans, en_az=a.en_az, lig=a.lig,
                          sezon=a.sezon, yontem=a.arindirma)
    if a.json:
        print(json.dumps(rapor, ensure_ascii=False, indent=1))
    else:
        yaz(rapor)


if __name__ == "__main__":
    main()
