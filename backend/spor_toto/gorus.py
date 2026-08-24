"""Piyasadan **bağımsız** görüş — yaklaşan maça, orana bakmadan sayı.

`tahmin` modülünün manşet tahmincisi piyasanın kendisidir ve Faz 1–3
boyunca on bir ölçüm onu geçen bir şey bulamadı (§3.27–§3.36). Bu modül o
sonucu tersine çevirmeye çalışmaz; yaptığı şey daha küçük ve daha
dürüsttür: **oranlara hiç bakmadan** kurulmuş ikinci bir görüşü, yaklaşan
bir haftanın maçlarına uygular ve piyasayla nerede ayrıştığını yazar.

Neden bunun bir değeri var:

* Ayrışma bir **kalite işaretidir**, bir üstünlük iddiası değil. §3.25
  ölçtü: piyasa hangi maçta haklı olduğunu biliyor. Bağımsız görüşün
  piyasadan koptuğu maç, kuponun kırılgan olduğu maçtır — orayı
  genişletmek (çift/üçlü) modelin haklı olmasını gerektirmez.
* Görüş **hiçbir işareti değiştirmez.** İşaretleri kuran şey piyasa
  olasılığı ve `secim.en_iyi_secim`'dir; buradaki sayılar kayda geçer ve
  okunur. Ölçümde geçmemiş bir modeli karar yoluna sokmak, on bir ölçümü
  görmezden gelmek olurdu.

─── İki görüş, iki ayrı gerekçe ──────────────────────────────────────────

**Dixon-Coles** (`dixon_coles`) gollerden hücum/savunma gücü çıkarır ve
1X2 olasılığı verir. Piyasadan bağımsız olan ilk görüştür (§3.28).

**Elo** (`elo`) sonuçlardan güç sıralaması çıkarır. 1X2 vermez — **beklenen
skor** verir (0..1) ve bu bir olasılık DEĞİLDİR; beraberliği yarım sayar.
Buraya bir tanı olarak girer, tahmin olarak değil. Elo farkını 1X2'ye
çeviren bir eşleme uydurmak, ölçülmemiş bir model eklemek olurdu.

─── Ad eşleme — bu modülün asıl zorluğu ─────────────────────────────────

Hafta dosyası iddaa adlarını taşır (`Galatasaray A.Ş.`), korpus
football-data kısaltmalarını (`Galatasaray`). `build_avrupa` ile **birebir
aynı iki kural** geçerlidir ve gerekçesi orada ölçüldü:

1. **Lig bir kısıttır, ipucu değil.** `T1` adı yalnızca `T1` havuzunda
   aranır; ligler arası yanlış eşleşme baştan imkânsızdır.
2. **Bulanık eşleme yok.** Ya sadeleştirilmiş ad birebir tutar, ya `ELLE`
   tablosunda yazılıdır, ya da **eşleşmez**. Alt dize eşlemesi ölçüldü ve
   %68'de kaldı ("Rangers" ↔ "Cove Rangers").

Eşleşmeyen takım bir hata değildir: yeni yükselen bir takımın korpusta
karşılığı **yoktur** ve olmaması doğrudur. O maçta görüş `yok` kalır ve
uydurulmaz.

    python -m spor_toto.gorus --sezon 2026_27 --hafta 2
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from .core import SEMBOLLER
from .dixon_coles import DixonColes, _gun
from .egitim import korpus_yukle
from .elo import EloDefteri, beklenen
from .odds import load_odds

#: Sadeleştirmede atılan kulüp ekleri. Liste **kısa** tutuldu: her ek,
#: iki farklı takımı aynı ada indirme riski taşır. Buradakiler ligde tekil
#: ayırt edicilik taşımayan sonekler.
_ATILAN = frozenset({
    "fk", "fc", "sk", "as", "ac", "cf", "sc", "afc", "jk", "kv", "sv",
    "us", "ss", "a", "s", "kulubu", "club", "the",
})

#: **Elle yazılmış, gözden geçirilmiş** eşleme: iddaa adı (sadeleştirilmiş)
#: → football-data kısaltması. `build_avrupa.ELLE` ile aynı disiplin: her
#: satır tek tek doğrulandı ve yanlış bir satır sessiz kalmaz — kapsama
#: raporunda görünür.
#:
#: Anahtarlar `sadelestir`den geçmiş hâlleriyle yazılır; tablo okunurken
#: yeniden sadeleştirilir, yani buraya ham ad yazmak da çalışır.
ELLE: dict[str, str] = {
    # Türkiye — iddaa ünvanları taşır, football-data taşımaz.
    "caykur rizespor": "Rizespor",
    "gaziantep f k": "Gaziantep",
    "gaziantep": "Gaziantep",
    "basaksehir": "Buyuksehyr",
    "istanbul basaksehir": "Buyuksehyr",
    "goztepe": "Goztep",
    "adana demirspor": "Ad. Demirspor",
    "fatih karagumruk": "Karagumruk",
    "mke ankaragucu": "Ankaragucu",
    "yukatel kayserispor": "Kayserispor",
    # Almanya
    "b dortmund": "Dortmund",
    "borussia dortmund": "Dortmund",
    "bayern munih": "Bayern Munich",
    "bayern munchen": "Bayern Munich",
    "b monchengladbach": "M'gladbach",
    "bayer leverkusen": "Leverkusen",
    "eintracht frankfurt": "Ein Frankfurt",
    "rb leipzig": "RB Leipzig",
    # Fransa
    "marsilya": "Marseille",
    "olympique marsilya": "Marseille",
    "paris saint germain": "Paris SG",
    "olympique lyon": "Lyon",
    "saint etienne": "St Etienne",
    # İngiltere
    "newcastle united": "Newcastle",
    "manchester united": "Man United",
    "manchester city": "Man City",
    "nottingham forest": "Nott'm Forest",
    "tottenham hotspur": "Tottenham",
    "west ham united": "West Ham",
    "wolverhampton": "Wolves",
    "leeds united": "Leeds",
    # İspanya
    "real betis": "Betis",
    "real sociedad": "Sociedad",
    "atletico madrid": "Ath Madrid",
    "athletic bilbao": "Ath Bilbao",
    "rayo vallecano": "Vallecano",
    "espanyol": "Espanol",
    "celta vigo": "Celta",
    # İtalya
    "ac milan": "Milan",
    "inter milan": "Inter",
    "hellas verona": "Verona",
}

#: Görüşün "kullanılabilir" sayılması için gereken en az kapsama. Altında
#: kalan bir hafta için blok yine üretilir ama `kullanilabilir` kapalıdır:
#: dört maçta konuşup on birinde susan bir görüşü haftanın görüşü saymak,
#: seçmeli bir okuma davetidir.
EN_AZ_KAPSAMA = 0.60


def sadelestir(ad: str) -> str:
    """Aksan, noktalama ve kulüp eki olmadan karşılaştırılabilir ad.

    Türkçe harfler NFKD ile ayrışmayanlar dâhil elle indirgenir: `ı` ve `i`
    aynı sade harfe düşer, çünkü iki kaynak aynı takımı iki biçimde yazıyor
    (`Kasımpaşa` ↔ `Kasimpasa`) ve fark ayırt edici değil, tipografik.
    """
    a = unicodedata.normalize("NFKD", ad)
    a = "".join(c for c in a if not unicodedata.combining(c))
    for eski, yeni in (("ı", "i"), ("İ", "I"), ("ğ", "g"), ("Ğ", "G"),
                       ("ş", "s"), ("Ş", "S"), ("ø", "o"), ("ß", "ss"),
                       ("đ", "d"), ("Đ", "D")):
        a = a.replace(eski, yeni)
    a = re.sub(r"[^a-z0-9]+", " ", a.lower())
    kelimeler = [k for k in a.split() if k not in _ATILAN]
    return " ".join(kelimeler) if kelimeler else a.strip()


def _ham_tarihce() -> list[dict[str, Any]]:
    """Korpus + 2025/26 arşivi — gol taşıyan her maç, tek listede.

    İki kaynak **bilerek** birleştiriliyor: korpus 2021/22–2024/25'i tam
    kapsar ama orada durur; 2025/26 yalnızca kupon maçlarını taşır (615
    maç) ama **güncel** olan tek kayıt odur. Dixon-Coles zaman ağırlıklı
    çalıştığı için eski korpusun katkısı zaten sönüyor; eksik olan yakın
    geçmişi eklemek, sönmüş bir geçmişle yetinmekten iyidir.

    Kayıt eksikliği gizlenmez: 2025/26 seyrek bir kesittir ve bu, o
    sezondan gelen güçlerin daha gürültülü olduğu anlamına gelir.
    """
    satirlar: list[dict[str, Any]] = []
    for r in korpus_yukle():
        if r["ev_gol"] is None or r["dep_gol"] is None:
            continue
        satirlar.append({
            "sezon": str(r["sezon"]), "lig": r["lig"], "tarih": r["tarih"],
            "ev": r["ev"], "dep": r["dep"], "kod": r["kod"],
            "ev_gol": int(r["ev_gol"]), "dep_gol": int(r["dep_gol"]),
        })
    for r in load_odds():
        kaynak = r["source"]
        if not kaynak.get("league") or r["hg"] is None or r["ag"] is None:
            continue
        satirlar.append({
            "sezon": "2526", "lig": kaynak["league"],
            "tarih": str(r["kickoff"])[:10],
            "ev": kaynak["home"], "dep": kaynak["away"], "kod": r["code"],
            "ev_gol": int(r["hg"]), "dep_gol": int(r["ag"]),
        })
    satirlar.sort(key=lambda r: (r["tarih"], r["lig"], r["ev"]))
    return satirlar


def takim_havuzu(satirlar: Sequence[dict[str, Any]]
                 ) -> dict[str, dict[str, str]]:
    """Lig → {sadeleştirilmiş ad: gerçek ad}. Lig kısıtı burada doğar."""
    havuz: dict[str, dict[str, str]] = {}
    for r in satirlar:
        lig = havuz.setdefault(r["lig"], {})
        for ad in (r["ev"], r["dep"]):
            lig.setdefault(sadelestir(ad), ad)
    return havuz


def coz(ad: str, lig: str, havuz: dict[str, dict[str, str]]) -> str | None:
    """İddaa adını korpus adına çevirir — ya birebir, ya `ELLE`, ya da None.

    `None` bir hata değil bir **cevaptır**: o takımın korpusta karşılığı
    yok (yeni yükselen ya da hiç oynamamış). Bulanık bir eşleme uydurmak
    yerine sessiz kalmak, ölçümün doğru tarafında durmaktır.
    """
    lig_havuzu = havuz.get(lig)
    if not lig_havuzu:
        return None
    sade = sadelestir(ad)
    if sade in lig_havuzu:
        return lig_havuzu[sade]
    hedef = {sadelestir(k): v for k, v in ELLE.items()}.get(sade)
    if hedef and sadelestir(hedef) in lig_havuzu:
        return lig_havuzu[sadelestir(hedef)]
    return None


def gorus_uret(maclar: Sequence[dict[str, Any]],
               tarih: str | None = None) -> dict[str, Any]:
    """Verilen maçlar için Dixon-Coles + Elo görüşü.

    `maclar` her biri `no`, `league`, `home`, `away` taşıyan kayıtlar.
    `tarih` (`YYYY-MM-DD`) zaman ağırlığının ölçüldüğü **şimdi**; verilmezse
    tarihçenin son günü kullanılır — testler sabitleyebilsin diye tek nokta.

    Sızıntı yok ve olamaz: tarihçe yalnızca sonucu **bilinen** maçlardan
    kurulur, tahmin edilen hafta o listede yoktur.
    """
    tarihce = _ham_tarihce()
    havuz = takim_havuzu(tarihce)
    # Zaman ağırlığının ölçüldüğü gün. Tarihçenin son günü varsayılan:
    # o gün verilmezse "şimdi", elimizdeki en yeni maçtır.
    simdi = (_gun(tarih) if tarih
             else max((_gun(r["tarih"]) for r in tarihce), default=0.0))

    model = DixonColes()
    uyduruldu = model.uydur(
        [r["ev"] for r in tarihce], [r["dep"] for r in tarihce],
        [r["ev_gol"] for r in tarihce], [r["dep_gol"] for r in tarihce],
        [simdi - _gun(r["tarih"]) for r in tarihce])

    defter = EloDefteri()
    for r in tarihce:
        defter.sezon_basi(r["sezon"])
        defter.guncelle(r["ev"], r["dep"], r["kod"],
                        int(r["ev_gol"] - r["dep_gol"]))
    # Yeni sezon: puanlar ortalamaya çekilir. Bu adım atlanırsa geçen
    # sezonun uçları olduğu gibi taşınır ve fark sistematik olarak büyük
    # okunur (`EloDefteri.sezon_basi`in kendi gerekçesi).
    defter.sezon_basi("gelecek")

    satirlar: list[dict[str, Any]] = []
    for m in maclar:
        ev = coz(str(m["home"]), str(m["league"]), havuz)
        dep = coz(str(m["away"]), str(m["league"]), havuz)
        satir: dict[str, Any] = {
            "no": m["no"], "lig": m["league"],
            "ev_ad": m["home"], "dep_ad": m["away"],
            "ev": ev, "dep": dep,
            "eslesti": bool(ev and dep),
            "dc_var": False, "dc": None,
            "elo_var": False, "elo_farki": None, "elo_beklenen": None,
        }
        if ev and dep:
            if uyduruldu and model.biliyor(ev, dep):
                p = model.tahmin(ev, dep)
                satir["dc_var"] = True
                satir["dc"] = {s: float(p[s]) for s in SEMBOLLER}
            if defter.yeterli(ev, dep):
                fark = defter.fark(ev, dep)
                satir["elo_var"] = True
                satir["elo_farki"] = fark
                satir["elo_beklenen"] = beklenen(fark)
        satirlar.append(satir)

    eslesen = sum(1 for r in satirlar if r["eslesti"])
    dc_olan = sum(1 for r in satirlar if r["dc_var"])
    kapsama = dc_olan / len(satirlar) if satirlar else 0.0
    return {
        "rows": satirlar,
        "n": len(satirlar),
        "eslesen": eslesen,
        "dc_olan": dc_olan,
        "kapsama": kapsama,
        "kullanilabilir": kapsama >= EN_AZ_KAPSAMA,
        "tarihce_mac": len(tarihce),
        "tarihce_son": max((r["tarih"] for r in tarihce), default=None),
        "dc_gamma": model.gamma if uyduruldu else None,
        "dc_rho": model.rho if uyduruldu else None,
        "eslesmeyen": sorted({
            ad for r in satirlar if not r["eslesti"]
            for ad, coz_ in ((r["ev_ad"], r["ev"]), (r["dep_ad"], r["dep"]))
            if coz_ is None
        }),
        "uyari": (
            "Bu gorus ISARET DEGISTIRMEZ. Dixon-Coles kupon setinde "
            "piyasanin gerisinde olculdu (docs §3.28); Elo bir 1X2 "
            "olasiligi degil beklenen SKOR verir (docs §3.27). Ikisi de "
            "kayda gecer, karar yoluna girmez."),
    }


def ayrisma(gorus: dict[str, Any],
            piyasa: Sequence[dict[str, float]]) -> list[dict[str, Any]]:
    """Bağımsız görüşün piyasadan koptuğu maçlar.

    İki ölçü ayrı yazılır çünkü ayrı şey söylerler:

    ``sembol_farkli``
        En olası sembol değişiyor — görüş piyasanın favorisini reddediyor.
    ``toplam_sapma``
        Üç olasılığın mutlak farkının yarısı (toplam varyasyon uzaklığı,
        0..1). Sembol aynı kalsa bile güvenin ne kadar ayrıştığını verir.
    """
    out: list[dict[str, Any]] = []
    for satir, p in zip(gorus["rows"], piyasa):
        if not satir["dc_var"]:
            continue
        dc = satir["dc"]
        sapma = 0.5 * sum(abs(dc[s] - p.get(s, 0.0)) for s in SEMBOLLER)
        pf = max(SEMBOLLER, key=lambda s: p.get(s, 0.0))
        df = max(SEMBOLLER, key=lambda s: dc[s])
        out.append({
            "no": satir["no"], "lig": satir["lig"],
            "mac": f"{satir['ev_ad']} – {satir['dep_ad']}",
            "piyasa": {s: p.get(s, 0.0) for s in SEMBOLLER},
            "dc": dc,
            "piyasa_fav": pf, "dc_fav": df,
            "sembol_farkli": pf != df,
            "toplam_sapma": sapma,
        })
    out.sort(key=lambda r: -r["toplam_sapma"])
    return out


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover
    """Elle koşum — görüşü tek başına görmek için.

        python -m spor_toto.gorus --sezon 2026_27 --hafta 2
    """
    import argparse
    import json
    from pathlib import Path

    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", default="2026_27")
    ap.add_argument("--hafta", type=int, default=2)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    kok = Path(__file__).resolve().parent.parent
    yol = kok / "data" / "super_toto" / a.sezon / f"hafta_{a.hafta:02d}.json"
    d = json.loads(yol.read_text(encoding="utf-8"))
    g = gorus_uret(d["matches"],
                   min((m["date"] for m in d["matches"] if m.get("date")),
                       default=None))
    if a.json:
        print(json.dumps(g, ensure_ascii=False, indent=1))
        return
    print(f"tarihce {g['tarihce_mac']} mac (son {g['tarihce_son']}) · "
          f"kapsama {100*g['kapsama']:.0f}% · "
          f"{'KULLANILABILIR' if g['kullanilabilir'] else 'YETERSIZ'}")
    if g["eslesmeyen"]:
        print(f"eslesmeyen: {', '.join(g['eslesmeyen'])}")
    for r in g["rows"]:
        dc = ("/".join(f"{100*r['dc'][s]:.0f}" for s in SEMBOLLER)
              if r["dc_var"] else "gorus yok")
        elo = (f"{r['elo_farki']:+.0f} (bek. {r['elo_beklenen']:.2f})"
               if r["elo_var"] else "—")
        print(f"{r['no']:>2} {r['ev_ad'][:22]:<22} – {r['dep_ad'][:22]:<22} "
              f"DC {dc:<12} Elo {elo}")


if __name__ == "__main__":  # pragma: no cover
    main()
