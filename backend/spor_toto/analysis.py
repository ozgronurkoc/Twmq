"""Monte Carlo olasılık simülasyonu ve maç bazlı hata frekansı."""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Sequence

import numpy as _np

from .core import SEMBOLLER, Encoder, Point
from .ortak import GUVEN_Z, normalize_olasilik, wilson


def _dogrula_olasilik(p: dict[str, float], i: int) -> None:
    """Bir maçın olasılık sözlüğünü reddedilebilir hâle getirir.

    **Ne reddedilir ve niçin.** `NaN`, `inf` ve sayıya çevrilemeyen değer.
    Üçü de bugün sessizce yutuluyordu ve yutulma biçimleri birbirinden
    kötüydü:

    * `NaN` → `max(0.0, nan)` Python'da `0.0` döner (`nan > 0.0` yanlıştır),
      yani eksik veri **sıfır olasılık** oluyordu — üstelik hiçbir yerde
      görünmeden.
    * `inf` → `max`'tan geçer, toplam `inf` olur ve normalize sonucu bütün
      semboller için `nan` çıkar; rapor `p=nan` ile döner ve `nan`
      karşılaştırmaları hep yanlış olduğu için hiçbir eşik yakalamaz.

    Bir simülasyon girdisini sessizce başka bir girdiye çevirmek, ölçümü
    ölçtüğünü sandığı şeyden koparır. Erken ve adıyla kırılır.

    **Ne reddedilMEZ:** toplamı sıfır olan dağılım. `1/0/2 = 0/0/0`
    düzgün dağılıma çevrilir ve bu **bilinçli bir kural**: "bilgi yok"un
    tarafsız karşılığı düzgün dağılımdır. Kural tek yerde yazılı
    (`ortak.normalize_olasilik`) ve arayüzde birebir aynadadır
    (`frontend/lib/utils.ts` `normalize`) — yığının bir ucunda değiştirmek
    ikisini ayrıştırırdı. Negatif değer de aynı kuralla kırpılır.
    """
    for sym in SEMBOLLER:
        ham = p.get(sym, 0.0)
        try:
            deger = float(ham)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"{i + 1}. mac, '{sym}' olasiligi sayi degil: {ham!r}") from e
        if math.isnan(deger):
            raise ValueError(f"{i + 1}. mac, '{sym}' olasiligi NaN")
        if math.isinf(deger):
            raise ValueError(f"{i + 1}. mac, '{sym}' olasiligi sonsuz: {deger}")


def monte_carlo_report(
    enc: Encoder,
    cols: Sequence[Point],
    probs: Sequence[dict[str, float]],
    n_samples: int = 100_000,
    seed: int = 42,
) -> dict:
    """
    Kullanıcı olasılıkları altında Monte Carlo simülasyonu.

    Dönen alanlar (her biri p, pct, se, ci95, ci_alt, ci_ust, count içerir):
      kume_ici, p15, p14, p13, p12

    `ci95` normal yaklaşımın **yarı genişliğidir** (yüzde puanı), aralığın
    kendisi değil; `ci_alt`/`ci_ust` gerçek %95 Wilson aralığıdır. İkisinin
    birlikte durmasının sebebi `rate()` gövdesinde yazılı.

    Sonuç bir **tahmindir**, kapalı form değil: aynı soruyu tam hesaplayan
    karşılığı `core.olasilik_raporu`dur ve ikisi `report.py` ile
    `health._check_monte_carlo`'da karşılaştırılır.

    n_samples < 1 → ValueError (sessiz sıfır rapor yok).
    1 ≤ n_samples < 100 → çalışır ama 'warning' alanı eklenir.
    100 ≤ n_samples < 1000 → yumuşak warning.
    Geçersiz olasılık (NaN / inf / sayı olmayan) → ValueError, bkz.
    `_dogrula_olasilik`.
    """
    if len(probs) != enc.total_len:
        raise ValueError(
            f"{len(probs)} maç için olasılık verildi, {enc.total_len} bekleniyordu."
        )
    try:
        n_samples = int(n_samples)
    except (TypeError, ValueError) as e:
        raise ValueError(f"n_samples sayi olmali, alindi: {n_samples!r}") from e
    if n_samples < 1:
        raise ValueError(
            f"Monte Carlo icin n_samples >= 1 gerekli (alindi: {n_samples}). "
            f"CLI'de --mc-samples 0 MC'yi kapatir; acmak icin pozitif deger ver."
        )
    warning: str | None = None
    if n_samples < 100:
        warning = (
            f"n_samples={n_samples} cok dusuk; %95 CI guvenilmez. "
            f"En az 1000 (tercihen 10000+) onerilir."
        )
    elif n_samples < 1000:
        warning = (
            f"n_samples={n_samples} dusuk; CI genis kalabilir. "
            f"Karar icin en az 1000, rapor icin 10000+ onerilir."
        )

    rng = random.Random(seed)

    cum: list[list[tuple[float, str]]] = []
    for i in range(enc.total_len):
        p = probs[i]
        _dogrula_olasilik(p, i)
        agirlik = normalize_olasilik(p)
        weights = [agirlik[sym] for sym in SEMBOLLER]
        running = 0.0
        entries: list[tuple[float, str]] = []
        for w, sym in zip(weights, SEMBOLLER):
            running += w
            entries.append((running, sym))
        if entries:
            entries[-1] = (1.0, entries[-1][1])
        cum.append(entries)

    sel_sets = [set(s) for s in enc.selections]

    n_ici = n_15 = n_14 = n_13 = n_12 = 0

    for _ in range(n_samples):
        outcome: list[str] = []
        for i in range(enc.total_len):
            r = rng.random()
            chosen = cum[i][-1][1]
            for threshold, sym in cum[i]:
                if r <= threshold:
                    chosen = sym
                    break
            outcome.append(chosen)

        if any(outcome[i] not in sel_sets[i] for i in range(enc.total_len)):
            continue
        n_ici += 1

        try:
            var = tuple(
                enc.variable_syms[j].index(outcome[pos])
                for j, pos in enumerate(enc.variable_pos)
            )
        except ValueError:
            continue

        if not cols:
            d = 99
        elif not enc.variable_pos:
            d = 0
        else:
            d = min(sum(a != b for a, b in zip(var, c)) for c in cols)

        # Kovalar HATA SAYISINDAN okunur. Once `15 - d` yazilmisti ve
        # `Encoder(kati=False)` 15'ten farkli uzunluga izin verdigi icin
        # kupon 14 macliksa butun etiketler bir kayardi. `d` tanim geregi
        # uzunluktan bagimsizdir: d=0 tamami dogru, d=1 bir hata...
        # Cikti anahtarlari (p15..p12) sozlesmedir, degismez.
        if d == 0:
            n_15 += 1
        elif d == 1:
            n_14 += 1
        elif d == 2:
            n_13 += 1
        elif d == 3:
            n_12 += 1

    def rate(k: int) -> dict:
        # `n_samples >= 1` yukarida (:40) garantilendi; eski `if n_samples
        # else` korumalari o yuzden olu koddu ve kaldirildi.
        p = k / n_samples
        se = math.sqrt(p * (1.0 - p) / n_samples)
        # `ci95` bir ARALIK DEGIL, normal yaklasimin YARI GENISLIGIDIR (yuzde
        # puani). Adi yaniltici ama sozlesmedir: `frontend/lib/types.ts` ve
        # `lib/api-sozlesme.json` onu bu adla okuyor. Yeniden adlandirmak
        # yerine yanina dogru adlandirilmis GERCEK aralik konuldu.
        #
        # Aralik Wilson: normal yaklasim kucuk orneklemde kenarlara yapisir
        # (0/5000'de alt sinir eksiye iner) ve tam da bu fonksiyonun
        # `n_samples < 100` uyarisi verdigi bolgede yanlistir. Kural depoda
        # tek yerde: `ortak.wilson`.
        alt, ust = wilson(k, n_samples)
        return {
            "p": p,
            "pct": round(100.0 * p, 3),
            "se": se,
            "ci95": round(GUVEN_Z * se * 100.0, 3),
            "ci_alt": round(100.0 * alt, 3),
            "ci_ust": round(100.0 * ust, 3),
            "count": k,
        }

    out = {
        "n_samples": n_samples,
        "kume_ici": rate(n_ici),
        "p15": rate(n_15),
        "p14": rate(n_14),
        "p13": rate(n_13),
        "p12": rate(n_12),
    }
    if warning:
        out["warning"] = warning
    return out


#: `match_error_frequency`'nin kendi iş tavanı: uzay noktası × kolon.
#:
#: **Niçin modülün içinde.** Koruma tek bir çağıranda duruyordu
#: (`web_app.py`, `enc.space_size() <= 20000`); `health.py`'nin iki çağrısında
#: hiç yoktu. Orada bugün sabit kupon kullanıldığı için sorun çıkmıyor —
#: yani güvenlik yapıdan değil, tesadüften geliyordu. Yeni bir çağıran
#: eklendiğinde ilk bozulacak şey buydu.
#:
#: **Niçin uzay değil, iş.** Maliyet uzayla değil `uzay × kolon` ile büyüyor:
#: 10.368 noktalı bir uzay 1.296 kolonla 1,3e7 iş, 16 kolonla 1,7e5. Tek
#: başına uzaya bakan bir tavan ikisine aynı cevabı verirdi.
#:
#: **Değer ölçüldü, tahmin edilmedi ve sınırı bir kural belirledi:** motorun
#: üretebileceği EN BÜYÜK kupon, kanıtlanmış optimal kaplamasıyla birlikte
#: hâlâ koşabilmeli. O durum 15 üçlüdür (3^15 = 14.348.907 nokta) ve 16
#: kolonla kaplanır → 2,30e8 iş. Ölçüldü (bu makine, tek çekirdek):
#:
#:     3^15 x 16 kolon → 10,1 sn, tepe bellek 8,9 MB
#:     11.664 x 1.296  →  0,43 sn, tepe bellek 10,5 MB
#:     19.683 x 1.296  →  0,72 sn, tepe bellek 11,2 MB
#:
#: Hız ~2,3e7–3,5e7 iş/sn; tepe bellek uzayla BÜYÜMÜYOR (parça boyuna bağlı,
#: aynı ölçümdeki 215 MB'lık eski `meshgrid` yolunun karşılığı 8,9 MB).
#: Tavan bu yüzden 2,5e8: en büyük meşru işi geçirir, iki katını geçirmez.
#:
#: `web_app.py`'deki 20.000'lik uzay sınırı kaldırılmadı: o bir ÜRÜN kararı
#: (kullanıcı beklerken ne kadar), bu ise bir motor korkuluğu (hiçbir çağıran
#: belleği/işlemciyi süpüremesin). İkisi farklı sorulara cevap veriyor.
ISLEM_SINIRI = 250_000_000


def _uzay_blogu(sizes: Sequence[int], basamak: Sequence[int],
                bas: int, son: int) -> _np.ndarray:
    """`[bas, son)` indeks aralığındaki uzay noktaları, `(son-bas, n)`.

    Sıra `itertools.product(*map(range, sizes))` sırasıdır — son eksen en
    hızlı değişir — ve bu **korunmak zorundadır**: eşit mesafede `argmin`
    ilk kolonu seçer, yani sıra değişirse eşitlik durumlarında başka bir
    kolon kazanır ve `d1`/`d2` dağılımı sessizce kayar.

    Eskiden bütün uzay `meshgrid` + `ravel` ile tek seferde üretiliyordu ve
    o da aynı sırayı veriyordu; değişen şey sıra değil **ne zaman** üretildiği.
    Karışık tabanda (mixed-radix) çözme, indeksten doğrudan basamağa gider:

        nokta[j] = (t // basamak[j]) % sizes[j]

    yani herhangi bir aralık, ondan öncekini üretmeden hesaplanabilir.
    """
    t = _np.arange(bas, son, dtype=_np.int64)
    blok = _np.empty((t.size, len(sizes)), dtype=_np.int8)
    for j, (adim, k) in enumerate(zip(basamak, sizes)):
        blok[:, j] = (t // adim) % k
    return blok


def match_error_frequency(
    enc: Encoder,
    cols: Sequence[Point],
    max_d: int = 2,
) -> dict:
    """
    Uniform varsayım altında, `d = 1..max_d` katmanlarında hangi maçların
    hata ürettiğini sayar.

    ─── `max_d` ─────────────────────────────────────────────────────────

    Parametre **artık gerçekten kullanılıyor.** İmzada vardı ama gövde
    katmanları `((1, err_d1), (2, err_d2))` diye sabit yazıyordu; üç
    çağıranın ikisi `max_d=2` geçtiği, biri varsayılanı kullandığı için
    atıllık hiçbir yerde görünmüyordu. Atıl bir parametre, olmayan bir
    yeteneği ilan eder.

    Anlamı: **tally edilecek en büyük hata mesafesi.**

        max_d = 0  → hiçbir katman (bkz. aşağıdaki not)
        max_d = 1  → d1
        max_d = 2  → d1, d2   ← varsayılan, eski davranışın birebir aynısı
        max_d = 3  → d1, d2, d3

    `max_d = 0`'ın "yalnızca tam eşleşme" demek olmamasının sebebi, bu
    fonksiyonun **hata pozisyonu** sayması: `d = 0` noktasının hatası yoktur,
    yani `d0` katmanı tanım gereği boştur. Sayılacak bir şey olmadığı için
    üretilmez.

    `max_d`, maç sayısına **tavanlanır** — mesafe pozisyon sayısını aşamaz,
    daha büyük bir değer boş katmanlar üretmekten başka bir şey yapmazdı.

    Çıktıda `d1`/`d2`/`n1`/`n2` **her zaman** bulunur (istenmediyse boş):
    ikisi de arayüz sözleşmesidir (`frontend/lib/api-sozlesme.json`).
    `max_d >= 3` istendiğinde `d3`/`n3`... eklenir; bugün hiçbir çağıran
    istemiyor, yani canlı sözleşme değişmiyor.

    ─── Yüzde paydası ───────────────────────────────────────────────────

    `pct`, o katmanın **hata yuvalarına** göredir: `n_d × d`. Önceden payda
    `n_d` (nokta sayısı) idi ve iki sütun farklı ölçekte normalize
    ediliyordu — `d1` %100'e toplanıyordu (her nokta 1 hata katar) ama `d2`
    **%200'e** (her nokta 2 hata katar). Aynı biçimde sunulan iki sayı aynı
    şeyi söylemiyordu.

    ─── Bellek ve iş ────────────────────────────────────────────────────

    Uzay **parça parça üretilir** (`_uzay_blogu`); tepe bellek uzayın
    tamamına değil parça boyuna bağlıdır. Önceden bütün uzay tek seferde
    `meshgrid` + `stack` ile kuruluyordu: 15 üçlüde `(14.348.907, 15)` int8
    ≈ 215 MB, üstelik `stack` öncesi aynı büyüklükte 15 ara dizi daha ayakta.
    Yalnızca mesafe hesabı parçalıydı, üretim değil.

    Toplam iş `ISLEM_SINIRI`yi aşarsa `ValueError` — sessiz bir OOM ya da
    dakikalarca dönen bir istek yerine adıyla kırılır.

    Uygulama notu: saf Python'da bu O(uzay × kolon × n) idi ve gerçekçi bir
    kuponda (uzay=10368, kolon=1296) ölçülen süre 10.9 saniyeydi — üstelik
    senkron istek yolunda. Hesap numpy'a taşındı: her parça için tüm
    kolonlara mesafe tek seferde hesaplanır ve en yakın kolon `argmin` ile
    bulunur. Davranış birebir korunur: `argmin` de, eski `if d < best_d`
    döngüsü de minimumu veren İLK kolonu seçer.
    """
    try:
        max_d = int(max_d)
    except (TypeError, ValueError) as e:
        raise ValueError(f"max_d sayi olmali, alindi: {max_d!r}") from e
    if max_d < 0:
        raise ValueError(f"max_d negatif olamaz (alindi: {max_d})")

    sizes = enc.alphabet_sizes
    n = len(sizes)
    # Katman sayisi mesafenin ust siniriyla tavanlanir; `d1`/`d2` yine de
    # daima uretilir (sozlesme), gerekiyorsa bos.
    katman_sayisi = min(max_d, n)
    anahtarlar = range(1, max(katman_sayisi, 2) + 1)

    if not cols or not sizes:
        return {**{f"d{k}": [] for k in anahtarlar},
                **{f"n{k}": 0 for k in anahtarlar}}

    kolonlar = _np.asarray(cols, dtype=_np.int8)          # (m, n)

    toplam = math.prod(sizes)
    is_yuku = toplam * len(kolonlar)
    if is_yuku > ISLEM_SINIRI:
        raise ValueError(
            f"hata frekansi icin is yuku cok buyuk: {toplam:,} nokta x "
            f"{len(kolonlar):,} kolon = {is_yuku:,} > {ISLEM_SINIRI:,}")

    # basamak[j] = prod(sizes[j+1:]) — karisik tabanda j. basamagin agirligi.
    basamak = [1] * n
    for j in range(n - 2, -1, -1):
        basamak[j] = basamak[j + 1] * sizes[j + 1]

    sayaclar = {k: _np.zeros(n, dtype=_np.int64) for k in range(1, katman_sayisi + 1)}
    adetler = dict.fromkeys(sayaclar, 0)

    # Parça boyu: (parca x kolon x n) bool geçici dizisini birkaç MB'ta tut.
    parca = max(1, min(toplam, 4_000_000 // max(1, len(kolonlar) * n)))

    for bas in range(0, toplam, parca):
        blok = _uzay_blogu(sizes, basamak, bas, min(bas + parca, toplam))
        d = (blok[:, None, :] != kolonlar[None, :, :]).sum(axis=2)  # (b, m)
        en_yakin = d.argmin(axis=1)
        en_kucuk = d[_np.arange(len(blok)), en_yakin]

        for hedef_d, sayac in sayaclar.items():
            secim = en_kucuk == hedef_d
            adet = int(secim.sum())
            if not adet:
                continue
            fark = blok[secim] != kolonlar[en_yakin[secim]]          # (k, n)
            sayac += fark.sum(axis=0)
            adetler[hedef_d] += adet

    def _counter(vec) -> Counter:
        c: Counter = Counter()
        for i, adet in enumerate(vec):
            if adet:
                c[enc.variable_pos[i] + 1] = int(adet)
        return c

    def to_list(counter: Counter, yuva: int) -> list[dict]:
        items = []
        for mac in sorted(counter.keys()):
            cnt = counter[mac]
            items.append({
                "mac": mac,
                "count": cnt,
                # Payda HATA YUVASI: `d` mesafesindeki her nokta tam olarak
                # `d` hata katar, yani sutun %100'e toplanir.
                "pct": round(100.0 * cnt / yuva, 2) if yuva else 0.0,
            })
        return items

    out: dict = {}
    for k in anahtarlar:
        adet = adetler.get(k, 0)
        sayac = sayaclar.get(k)
        out[f"d{k}"] = to_list(_counter(sayac), adet * k) if adet and sayac is not None else []
        out[f"n{k}"] = adet
    return out
