#!/usr/bin/env python3
"""İki amaç aynı kuponu mu veriyor? — "en az kaçak" ile `P(k ≤ eşik)`.

`spor_toto.secim` bir **kuyruk olasılığını** enbüyüklüyor: `P(k ≤ eşik)`,
yani kaçan maç sayısının eşiği aşmama olasılığı. Kuralı anlatırken bu
neredeyse her seferinde *"en az kaçağı seçiyor"* diye okunuyor ve o okuma
başka bir amaçtır: **beklenen** kaçak sayısını, `E[k] = Σqᵢ`, küçültmek.

İkisi aynı şey değildir ve fark yapısaldır: `E[k]` maçlara **ayrışır**
(her maç için "lira başına en çok q düşüşü" diye açgözlü çözülür), kuyruk
olasılığı ayrışmaz — bir maçın değeri öteki on dördünün ne kadar riskli
olduğuna bağlıdır (`spor_toto/secim.py` modül başlığı).

Ama "aynı değil" ile "farklı kupon üretir" de aynı şey değildir. Bu betik
ikincisini ölçer, iddia etmez:

  1. Bu sezonun dondurulmuş haftaları — iki amaç ayrışıyor mu?
  2. Rastgele haftalar (tohum sabit) — ne sıklıkla ayrışıyor, ayrışınca
     `P(k ≤ eşik)` cinsinden ne kaybediliyor?

ÖLÇEK UYARISI: kıyas BUGÜNÜN varsayılan marj arındırmasıyla (`shin`)
koşar. 1. ve 2. hafta `orantili` ile dondurulmuştu, o yüzden oradaki plan
dondurulmuş kuponla aynı olmak zorunda **değildir**; 3. ve 4. hafta aynı
ölçekte olduğu için kuponun kendisini birebir vermelidir. Kıyasın konusu
iki AMAÇ; ölçek ikisi için de aynı tutulduğundan sonucu bozmaz.

    python scripts/amac_kiyasi.py
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from spor_toto.core import SEMBOLLER, sirala_semboller
from spor_toto.kaplama_arsiv import HAMMING_BLOK_BOYU
from spor_toto.odds import implied_probs
from spor_toto.secim import (
    VARSAYILAN_KACAK_ESIGI,
    bedel_hesapla,
    en_iyi_secim,
    hedef_olasiligi,
    kacak_olasiligi,
)

#: Bu sezonun dondurulmuş haftaları ve her birinin kendi bütçe tavanı.
#: Tavan kupon dosyasından gelir: 3. ve 4. haftada `strategy.butce_kolon`
#: yazılıdır (eşik kuralının aynı haftada ürettiği bedel), 1. ve 2. haftada
#: öyle bir alan yoktur ve ana varyantın kolon sayısı tavan sayılır.
SEZON = "2026_27"


def _hafta_dosyalari(kok: Path) -> list[tuple[int, Path, Path]]:
    """(hafta no, maç dosyası, kupon dosyası) — numaraya göre sıralı."""
    dizin = kok / "data" / "super_toto" / SEZON
    out = []
    for mac in sorted(dizin.glob("hafta_[0-9][0-9].json")):
        kupon = mac.with_name(mac.stem + "_kupon.json")
        if kupon.exists():
            out.append((int(mac.stem.split("_")[1]), mac, kupon))
    return out


def enaz_kacak_plani(probs_listesi: list[dict[str, float]],
                     butce: int,
                     esik: int = VARSAYILAN_KACAK_ESIGI) -> list[list[str]] | None:
    """`E[k] = Σqᵢ`'yi enküçükleyen plan — `en_iyi_secim`in rakip amacı.

    Kısıtlar birebir aynı tutulur (bütçe tavanı, en az yedi çifte), yalnızca
    amaç değişir. `E[k]` ayrışabildiği için burada Pareto sınırı gerekmez:
    `(çifte, üçlü)` durumu başına **tek** bir en iyi toplam yeter.

    `esik` yalnızca imza uyumu için durur; toplam kaçak beklentisi eşiğe
    bakmaz — farkın kaynağı zaten budur.
    """
    n = len(probs_listesi)
    if n == 0:
        return None
    durum: dict[tuple[int, int], tuple[float, tuple[int, ...]]] = {(0, 0): (0.0, ())}
    for i, p in enumerate(probs_listesi):
        q = [kacak_olasiligi(p, k) for k in (1, 2, 3)]
        yeni: dict[tuple[int, int], tuple[float, tuple[int, ...]]] = {}
        for (a, b), (toplam, izlek) in durum.items():
            for seviye in (1, 2, 3):
                ya, yb = a + (seviye == 2), b + (seviye == 3)
                if bedel_hesapla(ya, yb) > butce:
                    continue
                if ya + (n - i - 1) < HAMMING_BLOK_BOYU:
                    continue
                aday = (toplam + q[seviye - 1], (*izlek, seviye))
                if (ya, yb) not in yeni or aday[0] < yeni[(ya, yb)][0]:
                    yeni[(ya, yb)] = aday
        durum = yeni
        if not durum:
            return None
    uygun = [v for (a, _b), v in durum.items() if a >= HAMMING_BLOK_BOYU]
    if not uygun:
        return None
    _, izlek = min(uygun, key=lambda t: t[0])
    sirali = [sorted(p.items(), key=lambda kv: (-kv[1], SEMBOLLER.index(kv[0])))
              for p in probs_listesi]
    return [sirala_semboller([s for s, _ in sirali[i][:izlek[i]]]) for i in range(n)]


def _kiyas(probs_listesi: list[dict[str, float]],
           butce: int,
           esik: int = VARSAYILAN_KACAK_ESIGI) -> dict[str, Any] | None:
    """Bir haftada iki amacı yan yana koyar; hiçbiri kurulamazsa `None`."""
    a = en_iyi_secim(probs_listesi, butce, esik)
    b = enaz_kacak_plani(probs_listesi, butce, esik)
    if a is None or b is None:
        return None

    def bekleneni(sec: list[list[str]]) -> float:
        """`E[k] = Σqᵢ` — rakip amacın kendi ölçüsü, ikisi için de yazılır."""
        return sum(kacak_olasiligi(p, len(s))
                   for p, s in zip(probs_listesi, sec))

    return {
        "hedef_picks": a.picks,
        "hedef_p": a.p_hedef,
        "hedef_e": bekleneni(a.secimler),
        "hedef_bedel": a.bedel,
        "hedef_sekil": (a.banko, a.cift, a.uclu),
        "enaz_picks": ["".join(s) for s in b],
        "enaz_p": hedef_olasiligi(probs_listesi, b, esik),
        "enaz_e": bekleneni(b),
        "enaz_bedel": bedel_hesapla(sum(1 for s in b if len(s) == 2),
                                    sum(1 for s in b if len(s) == 3)),
        "ayrisan": [i + 1 for i in range(len(probs_listesi))
                    if a.picks[i] != "".join(b[i])],
    }


def sezon_kiyasi(kok: Path = KOK) -> list[dict[str, Any]]:
    """Dondurulmuş haftaların her birinde iki amacın cevabı."""
    out = []
    for no, mac_yolu, kupon_yolu in _hafta_dosyalari(kok):
        mac = json.loads(mac_yolu.read_text(encoding="utf-8"))
        kupon = json.loads(kupon_yolu.read_text(encoding="utf-8"))
        strateji = kupon.get("meta", {}).get("strategy", {})
        butce = strateji.get("butce_kolon") or kupon["variants"][0]["columns"]
        probs = [implied_probs(m["odds"]) for m in mac["matches"]]
        k = _kiyas(probs, int(butce))
        if k is None:
            continue
        k.update(hafta=no, butce=int(butce), kural=strateji.get("kural", "?"))
        out.append(k)
    return out


def rastgele_kiyas(hafta_sayisi: int, tohum: int,
                   butceler: tuple[int, ...] = (512, 864, 1024, 1296, 2304, 3888)
                   ) -> dict[str, Any]:
    """Rastgele haftalarda ayrışma sıklığı ve `P(k ≤ eşik)` cinsinden bedeli.

    Olasılıklar `u²` ile üretilir (düz uniform değil): karesi almak dağılımı
    bir sembole doğru çeker, yani gerçek bültenlerdeki gibi net favorili ve
    çaresiz maçları birlikte üretir. Tohum sabittir; sayı yeniden koşulduğunda
    aynı çıkar.
    """
    rnd = random.Random(tohum)
    ayrisan, kayiplar, kurulan = 0, [], 0
    for _ in range(hafta_sayisi):
        probs = []
        for _ in range(15):
            ham = [rnd.random() ** 2 + 0.02 for _ in range(3)]
            t = sum(ham)
            probs.append({s: x / t for s, x in zip(SEMBOLLER, ham)})
        k = _kiyas(probs, rnd.choice(butceler))
        if k is None:
            continue
        kurulan += 1
        if k["ayrisan"]:
            ayrisan += 1
            kayiplar.append(k["hedef_p"] - k["enaz_p"])
    return {
        "hafta": kurulan,
        "ayrisan": ayrisan,
        "kayip_ort": sum(kayiplar) / len(kayiplar) if kayiplar else 0.0,
        "kayip_max": max(kayiplar) if kayiplar else 0.0,
        "kayip_min": min(kayiplar) if kayiplar else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hafta", type=int, default=400,
                    help="rastgele hafta sayısı")
    ap.add_argument("--tohum", type=int, default=7,
                    help="rastgele üretimin tohumu — sayı bununla tekrarlanır")
    a = ap.parse_args()

    print(f"\n{'='*74}\nİKİ AMAÇ: P(k≤{VARSAYILAN_KACAK_ESIGI}) enbüyükle  "
          f"↔  E[k] enküçükle\n{'='*74}")

    sezon = sezon_kiyasi()
    print(f'\n─── {SEZON} dondurulmuş haftalar ──────────────────────────────────')
    print(f'{"hafta":<7}{"kural":<8}{"bütçe":>7}{"şekil":>9}{"bedel":>7}'
          f'{"P(k≤" + str(VARSAYILAN_KACAK_ESIGI) + ")":>9}{"E[k]":>7}  ayrışan maç')
    for h in sezon:
        sekil = "/".join(str(x) for x in h["hedef_sekil"])
        ayr = ", ".join(str(x) for x in h["ayrisan"]) or "yok"
        print(f'{h["hafta"]:<7}{h["kural"]:<8}{h["butce"]:>7,}{sekil:>9}'
              f'{h["hedef_bedel"]:>7,}{h["hedef_p"]:>9.4f}{h["hedef_e"]:>7.4f}  {ayr}')
    # Iki sayi da BASILIYOR ve gerekcesi somut: tek sayi ("0/4") hangi
    # yonde okundugu belirsizdi ve bir kez TERS okundu — PR 48'in govdesi
    # "0/4 ayrisma", yani "dordunde de ayni kupon" diye yazmisti, oysa
    # cikti "0 haftada AYNI" diyordu, yani dordunde de ayrisiyordu.
    hic = sum(1 for h in sezon if not h["ayrisan"])
    ayrisan = len(sezon) - hic
    print(f'\n{ayrisan}/{len(sezon)} haftada iki amaç AYRIŞIYOR '
          f'({hic}/{len(sezon)} haftada aynı kuponu veriyor).')

    r = rastgele_kiyas(a.hafta, a.tohum)
    print(f'\n─── rastgele hafta (tohum {a.tohum}) ───────────────────────────────')
    print(f'kurulabilen hafta : {r["hafta"]}')
    print(f'ayrışan hafta     : {r["ayrisan"]}  '
          f'(%{100*r["ayrisan"]/r["hafta"]:.1f})')
    print(f'P(k≤{VARSAYILAN_KACAK_ESIGI}) kaybı      : ortalama {r["kayip_ort"]:.5f} · '
          f'en büyük {r["kayip_max"]:.5f} · en küçük {r["kayip_min"]:.5f}')
    if r["kayip_min"] < 0:
        print('UYARI: negatif kayıp = "en az kaçak" planı hedefi GEÇMİŞ. '
              'Bu imkânsızdır (`en_iyi_secim` kesin çözer); çıkarsa hata arayın.')
    else:
        print('Kayıp hiçbir haftada negatif değil: "en az kaçak" okuması '
              'hedefi hiç geçmiyor, ayrıştığı her haftada geride kalıyor.')


if __name__ == "__main__":
    main()
