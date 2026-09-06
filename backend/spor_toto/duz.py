"""Düz (tam sistem) oynamanın kolon sayımı ve para hesabı.

`secim.py` **hangi işaretlerin** konulacağına karar verir; bu modül o
işaretlerin oynandığında **kaç kolonun kaç tuttuğunu** ve o kolonların ne
kazandığını sayar. İkisi ayrı sorular:

    secim.hedef_olasiligi   →  P(en iyi kolon ≥ 12)      — bir olasılık
    duz.kademe_sayimlari    →  her kademede KAÇ kolon    — bir sayım

Ayrımın parasal karşılığı büyük: tam sistem bir haftada 12'yi **bir kez
değil yüzlerce kez** tutturur, ve ikramiye kademe başına kolon başına ödenir.
Yalnızca en iyi kolonu saymak (kaplama döneminin alışkanlığı) getiriyi
sistematik olarak eksik gösterir.

─── Neden `scripts/` değil de paket ──────────────────────────────────────

Bu iki gövde `scripts/kademe_analizi.py` içinde yazılmıştı ve orada
kalsalardı kuponu **kuran** hesapla onu **değerlendiren** hesap iki ayrı
dosyada yaşayacaktı. Depo bu hatayı bir kez yaptı: aynı betik
`ortak.kacak_dagilimi`yi yeniden yazmıştı ve `ortak.py` bunun için açık bir
uyarı taşıyor — *"iki gövde ayrışsaydı kuponu kuran hesap ile onu
değerlendiren hesap farklı şeyler söylerdi."* Tekilleştirme o dersin
uygulanmasıdır; `kademe_analizi` artık buradan import eder.
"""
from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from .core import Encoder

#: Kupondaki maç sayısı.
MAC_SAYISI = 15

#: Ödeyen en düşük kademe. Altı ödemez, o yüzden sayılmaz.
EN_DUSUK_KADEME = 12

#: `/api/solve` ve CLI'nin **maddeleştireceği** en fazla kolon.
#:
#: Düzde "çözüm" diye bir arama yok — kolonlar seçim kümesinin kendisidir ve
#: `3¹⁵ = 14.348.907`'ye kadar çıkabilir. Sınır bir ürün kararı değil bellek
#: kararıdır: her kolon 15 elemanlı bir demet, ve `_build_result` hepsini
#: gezerek olasılık/Monte Carlo/fire analizi yapıyor. Ölçülen kupon
#: bedelleri 1–60.000 bandında; tavan onun belirgin üstünde tutuldu.
#:
#: Aşılırsa **sessizce kırpılmaz, hata atar**: eksik bir kolon kümesiyle
#: hesaplanan küme-içi olasılık yanlış olur ve yanlışlığı görünmez.
KOLON_SINIRI = 200_000


def kademe_sayimlari(s: Sequence[int],
                     kacak: Sequence[int]) -> dict[int, int]:
    """Tam sistemde her kademeyi tutturan **kolon sayısı**.

    `s` her maçta işaretlenen sembol sayısı (1/2/3), `kacak` gerçek sonucun
    işaretlerin dışında kaldığı maçların indeksleri.

    Kaçak sayısı `k` ise en iyi kolon `15−k` doğru yapar. Tam olarak
    `15−k−j` doğru yapan kolon sayısı::

        e_j({s_i − 1 : i kaçak değil})  ×  Π_{i ∈ kaçak} s_i

    `e_j` elemanter simetrik polinomdur: kaçak olmayan maçların `j`
    tanesinde yanılmanın kaç yolu olduğunu sayar. Kaçak maçlarda ise
    **her** işaret yanlıştır, o yüzden çarpan olarak girerler.
    """
    kacak_kume = set(kacak)
    e = [1, 0, 0, 0]
    for i in range(MAC_SAYISI):
        if i in kacak_kume:
            continue
        x = s[i] - 1
        e[3] += e[2] * x
        e[2] += e[1] * x
        e[1] += e[0] * x
    carpan = 1
    for i in kacak_kume:
        carpan *= s[i]
    return {MAC_SAYISI - len(kacak_kume) - j: e[j] * carpan for j in range(4)}


def hafta_kazanci(s: Sequence[int], kacak: Sequence[int],
                  tablo: dict[int, dict[str, Any]]
                  ) -> tuple[float, dict[int, float]]:
    """Bir haftada tam sistemin kazandığı para — **seyreltme modellenmiş**.

    Kademe havuzu sabittir; `m` kolonumuz eklenince havuz `w+m` kişiye
    bölünür ve payımız `havuz · m / (w + m)` olur. Seyreltmeyi atlamak tam
    sistemi olduğundan iyi gösterirdi: çok kolon kazanmak, kendi kademeni
    kendi kolonlarınla sulandırmak demektir.

    `tablo` resmî ikramiye kaydıdır — `{kademe: {"winners": w, "prize": p}}`.
    """
    if len(kacak) > MAC_SAYISI - EN_DUSUK_KADEME:
        return 0.0, {}
    kad: dict[int, float] = {}
    for tier, m in kademe_sayimlari(s, kacak).items():
        if tier < EN_DUSUK_KADEME or m <= 0 or tier not in tablo:
            continue
        w, pz = tablo[tier]["winners"], tablo[tier]["prize"]
        havuz = pz * w if w > 0 else pz
        kad[tier] = havuz * m / (w + m)
    return sum(kad.values()), kad


def kolonlar(enc: Encoder,
             en_cok: int = KOLON_SINIRI) -> list[tuple[int, ...]]:
    """Oynanacak kolonların tamamı — düzde "çözüm" budur.

    Kaplama döneminde bu iş bir **arama**ydı: `engines.py` yedi ayrı motor
    taşıyordu (`fix16`, `auto`, `block`, `exact`, `heuristic`, `butce`,
    `maxcov`) ve hepsi aynı soruyu soruyordu — *seçim kümesini en az kaç
    kolonla örtebilirim?* Düzde o soru yok: kümenin tamamı oynanıyor.
    Geriye kalan tek şey çarpımı üretmek.

    Nokta biçimi `core.Encoder`ınkiyle aynı kalır — değişken maçların
    sembol indeksleri, banko maçlar dışarıda — ki `enc.decode_full` ve
    `_build_result` gibi çağıranlar değişmesin.
    """
    boyutlar = [len(s) for s in enc.variable_syms]
    toplam = 1
    for b in boyutlar:
        toplam *= b
    if toplam > en_cok:
        raise ValueError(
            f"secim kumesi {toplam:,} kolon — tavan {en_cok:,}. Duzde kolonlar "
            f"kirpilamaz: eksik kume ile hesaplanan kume-ici olasilik yanlis "
            f"olur ve yanlisligi gorunmez. Isaret sayisini azaltin.")
    return list(itertools.product(*[range(b) for b in boyutlar]))


def tek_satir(enc: Encoder) -> tuple[frozenset[int], ...]:
    """Kuponun **satır** gösterimi — düzde her zaman TEK satır.

    Kupon fişinde bir satır, her maç için işaretlenen sembol kümesidir
    (`core.Row`). Düzde oynanan şey seçim kümesinin kendisidir, yani o
    küme **tek bir satıra** sığar ve o satırın bedeli `2^çifte · 3^üçlü`
    kolondur.

    Bu iş kaplama döneminde `core.merge_rows`un işiydi ve bir **aramaydı**:
    kaplamanın ürettiği dağınık kolonlar tek tek geziliyor, bir koordinatta
    ayrışan çiftler tekrar tekrar birleştirilerek satır sayısı düşürülüyordu
    (kayıpsız olduğu ayrıca sınanıyordu). Düzde arayacak bir şey yok —
    cevap kapalı formda ve yanılma payı sıfır: her değişken maçta bütün
    semboller işaretli.
    """
    return tuple(frozenset(range(len(s))) for s in enc.variable_syms)
