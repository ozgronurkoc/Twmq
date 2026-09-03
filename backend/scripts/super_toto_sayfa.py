#!/usr/bin/env python3
"""Bir haftanın analizini tek sayfalık HTML rapora döker.

Sayfadaki HER sayı `super_toto_hafta.py` boru hattından gelir; bu dosyada
elle yazılmış tek bir ölçüm yoktur — biçim burada, gerçek orada durur.
Gerekçe metinleri de şablon değildir: her cümle o maçın kendi
olasılığından, geçen sezonun kendi bandından ve oynanma verisinden
üretilir.

    python scripts/super_toto_sayfa.py --hafta 1
    python scripts/super_toto_sayfa.py --hafta 1 --cikti /tmp/h1.html

Tema: arayüzün kendi token düzeni (globals.css) — üç durumlu açık/koyu.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

_ap = argparse.ArgumentParser()
_ap.add_argument("--sezon", default="2026_27")
_ap.add_argument("--hafta", type=int, default=1)
_ap.add_argument("--cikti", default=None)
# Bayraklar YALNIZCA dogrudan calistirilirken okunur. Once kosulsuz
# `parse_args()` vardi: bu dosyayi import eden herkes (test toplayicisi
# dahil) kendi argv'siyle bu ayristiriciya carpiyordu.
_a = _ap.parse_args(None if __name__ == "__main__" else [])

m = importlib.import_module("scripts.super_toto_hafta")

from spor_toto.core import SEMBOLLER
from spor_toto.odds import margin, saglayici_adi

#: Sembol duzeni TEK kaynaktan (`spor_toto.core`). Bu dosyada ayri bir
#: demet olarak yaziliyordu; depoda ayni deger on bir kez tanimliydi.
S = SEMBOLLER
d = m.hafta_yukle(_a.sezon, _a.hafta)
ref = m.gecen_sezon_ref()
prof = m.hafta_profili(d, ref)
kam = m.kamuoyu(d)
ana = m.kupon_kur(d, 0.68, 0.38)

# Sonuç girilmişse değerlendirme katmanı da yüklenir. Girilmemişse sayfa
# eskisi gibi "sonuç yok" halinde üretilir — tek şablon, iki durum.
_deg = importlib.import_module("scripts.super_toto_degerlendir")
BITTI = bool(d["meta"].get("results"))
KUPON_JSON = json.loads((KOK / "data" / "super_toto" / _a.sezon /
                         f"hafta_{_a.hafta:02d}_kupon.json").read_text(encoding="utf-8"))
KULLANICI = KUPON_JSON.get("user")

#: Fiyat kaynağının ADI sayfada üç yerde geçiyordu ve üçünde de "iddaa"
#: diye SABİT yazılıydı. 3. haftada ana fiyat Pinnacle kapanışa geçince o
#: etiketler yalan söylemeye başladı: sayfa hangi fiyatı gösterdiğini
#: kendi verisinden okumak zorunda, yoksa rapor kendi kaynağını yanlış
#: bildirir. Ad `odds_kind`ten türetilir; bilinmeyen bir değer gelirse
#: uydurmak yerine ham değerin kendisi yazılır.
#: Harita ve bicimleyici TEK kaynaktan: `spor_toto.odds.saglayici_adi`.
#: Ayni dort cift bu dosyada IKI KEZ (asagida `_KITAP_ADI` olarak) ve
#: arayuzde bir kez daha yaziliydi.
_KIND = (d["meta"].get("odds_kind") or "").lower()
#: Soneksiz saglayici adi ("Pinnacle") — donem bilgisinin istenmedigi
#: yerlerde kullaniliyor.
_saglayici = saglayici_adi(_KIND.partition("_")[0])
FIYAT_ADI = f"{saglayici_adi(_KIND)} oranı"
#: "Program" alanı boş olabilir (3. haftada tarihler girilmedi ve
#: uydurulmadı). Şablon `html.escape`e doğrudan veriyordu ve None'da
#: çöküyordu; eksik veri sayfayı düşürmemeli, eksik olduğunu SÖYLEMELİ.
PROGRAM = d["meta"].get("program") or "program tarihleri girilmedi"

#: Aşağıdaki üç "sınır" maddesi 1. haftanın sayılarıyla ELLE yazılıydı
#: (belirli maç numaraları, sabit yüzdeler, tek yönlü bir marj yorumu).
#: Bu dosyanın kendi başlığı "elle yazılmış tek bir ölçüm yoktur" diyor;
#: 3. haftada ana fiyat Pinnacle'a geçince o satırlar hem başlığı hem
#: gerçeği yalanlar hâle geldi. Üçü de artık haftanın kendi verisinden
#: türetiliyor.
#:
#: Marj yönü İKİ TARAFLI: bu haftanın marjı arşivinkinden büyükse
#: arındırma favoriden fazla kesip olasılığı küçük gösterir, küçükse
#: tersi olur. Eski metin yalnızca "küçük" halini biliyordu.
_MARJ_FARKI = prof["avg_margin_pct"] - ref["odds"]["avg_margin_pct"]
if abs(_MARJ_FARKI) < 0.5:
    MARJ_YONU = ("iki ölçek pratikte aynı, bu haftaya özel bir ölçek "
                 "düzeltmesi gerekmiyor.")
elif _MARJ_FARKI > 0:
    MARJ_YONU = ("bu hafta <b>daha yüksek</b>. Arındırma favoriden daha çok "
                 "kestiği için favori olasılıkları bir miktar <b>küçük</b> "
                 "çıkıyor — gerçek banko sayısı buradakinden fazla olabilirdi.")
else:
    MARJ_YONU = ("bu hafta <b>daha düşük</b>. Eşikler daha marjlı bir fiyatta "
                 "kalibre edildiği için favori olasılıkları bu hafta bir miktar "
                 "<b>büyük</b> çıkıyor — eşik kuralı olduğundan cömert "
                 "davranabilir. (Hedef kuralı eşiğe bakmadığı için bu "
                 "sapmadan etkilenmez.)")

_kal_sirali = sorted(ana["per_match_crowd"],
                     key=lambda r: -(r["play_in"] - r["prob_in"]))[:3]
KALABALIK_UC = ", ".join(
    f"{r['no']}. maç [{r['sec']}] halkın %{100*r['play_in']:.0f}&#39;i"
    for r in _kal_sirali) or "yok"

#: Uyarılar hafta dosyasının kendisinden gelir (elle girilenler + `dogrula`
#: üretenler), böylece sayfa hangi boşlukla yaşadığını saklamaz.
_uyarilar = list(d["meta"].get("data_warnings") or [])
_uyarilar += list(d["meta"].get("uretilen_uyarilar") or [])
UYARI_OZETI = (f"Bu haftanın kaydında {len(_uyarilar)} veri uyarısı var "
               "(tamamı yukarıdaki “veri uyarıları” bölümünde)."
               if _uyarilar else "Bu haftanın kaydında veri uyarısı yok.")

# ─── FİYAT KAYNAKLARI ────────────────────────────────────────────────────
# 3. haftada hafta dosyası ilk kez birden çok bahisçinin AÇILIŞ ve KAPANIŞ
# fiyatını taşıyor (`matches[].odds_books`). Bu bölüm yalnızca o alan varsa
# çizilir; 1. ve 2. haftanın sayfaları değişmeden üretilmeye devam eder.
#
# Ölçüm arındırılmış olasılık üzerinden yapılır, ham oran üzerinden DEĞİL:
# ham oranın hareketi, piyasanın fikir değiştirmesiyle bahisçinin marjını
# değiştirmesini karıştırır (bkz. `spor_toto.cizgi` modül başlığı).
_ilk_kitap = (d["matches"][0].get("odds_books") or {})
KITAPLAR = sorted(_ilk_kitap)
FIYAT_VAR = len(KITAPLAR) > 1


def _oku(mac, anahtar):
    from spor_toto.odds import implied_probs
    o = (mac.get("odds_books") or {}).get(anahtar)
    return (implied_probs(o), o) if o else (None, None)


#: Marj (overround) TEK kaynaktan: `spor_toto.odds.margin`. Ayni govde
#: iki betikte birebir yaziliydi; kanonik govde ustelik daha korumali
#: (sifir/negatif orani eler, bu kopyalar ZeroDivisionError verirdi).
_marj = margin


FIYAT_SATIR: list[dict] = []
KITAP_MARJ: dict[str, float] = {}
BAYAT: list[str] = []
if FIYAT_VAR:
    for anahtar in KITAPLAR:
        ms = [_marj(mm["odds_books"][anahtar]) for mm in d["matches"]]
        KITAP_MARJ[anahtar] = 100 * sum(ms) / len(ms)
    # Bir bahisçinin kapanışı açılışıyla BİREBİR aynıysa o satır bir fiyat
    # değil, bayat bir kayıttır — ayrışma sayılırsa görüş farkı sanılır.
    for anahtar in KITAPLAR:
        if not anahtar.endswith("_kapanis"):
            continue
        ac = anahtar.replace("_kapanis", "_acilis")
        if ac not in KITAPLAR:
            continue
        ayni = [mm["no"] for mm in d["matches"]
                if mm["odds_books"][anahtar] == mm["odds_books"][ac]]
        if ayni:
            BAYAT.append(f"{anahtar.split('_')[0]}: "
                         + ", ".join(map(str, ayni)) + ". maç")

    _ana_kitap = (d["meta"].get("odds_kind") or "").replace("-", "_")
    _ac_kitap = _ana_kitap.replace("_kapanis", "_acilis")
    for mm in d["matches"]:
        p_ka, _ = _oku(mm, _ana_kitap)
        p_ac, _ = _oku(mm, _ac_kitap)
        # Ayrışma: aynı anı gösteren bahisçiler arasındaki en büyük fark.
        # Ana fiyat once gelir: tablonun ilk sutunu kuponu besleyen fiyat
        # olmazsa okuyucu ikincil bir bahisciyi ana fiyat sanir.
        esanlı = sorted((k for k in KITAPLAR
                         if k.endswith(_ana_kitap.split("_")[-1])),
                        key=lambda k: (k != _ana_kitap, k))
        pler = [_oku(mm, k)[0] for k in esanlı]
        pler = [x for x in pler if x]
        ayrisma = max((abs(a[s] - b[s]) for a in pler for b in pler for s in S),
                      default=0.0)
        hareket = None
        if p_ka and p_ac:
            hareket = max(S, key=lambda s: abs(p_ka[s] - p_ac[s]))
        FIYAT_SATIR.append({
            "no": mm["no"], "ad": f"{mm['home']} – {mm['away']}",
            "acilis": p_ac, "kapanis": p_ka,
            "hareket_sembol": hareket,
            "hareket": (p_ka[hareket] - p_ac[hareket]) if hareket else 0.0,
            "ayrisma": ayrisma,
            "kitaplar": {k: _oku(mm, k)[0] for k in esanlı},
            "esanlı": esanlı,
        })
    _EN_HAREKET = max(FIYAT_SATIR, key=lambda r: abs(r["hareket"]))
    _EN_AYRISMA = max(FIYAT_SATIR, key=lambda r: r["ayrisma"])

# ─── DONDURULAN KUPON ────────────────────────────────────────────────────
# Sayfanın kendi kurduğu kupon (`ana`) varsayılan kuralın çıktısıdır.
# Kayıtta ondan farklı bir varyant DONDURULDUYSA gösterilecek olan odur —
# oynanan kupon kayıttır, sayfanın o an yeniden hesapladığı şey değil.
DONMUS = next((v for v in KUPON_JSON.get("variants", [])
               if "DONDURULAN" in v.get("label", "")), None)
DUYARLILIK = KUPON_JSON.get("duyarlilik")

#: SONUÇ bölümünün puanladığı kupon — **kayıttaki**, yani gerçekten
#: dondurulmuş olan.
#:
#: Burası önceden `ana`yı, yani sayfanın O AN yeniden kurduğu kuponu
#: puanlıyordu; oysa `ana` bugünkü varsayılan kuralın (eşik 0,68/0,38,
#: bugünkü arındırma) çıktısıdır ve haftanın dondurulduğu andaki kuralla
#: aynı olmak zorunda değildir. 3. hafta girildiğinde ayrışma görünür oldu:
#: 1. haftanın sayfası **11/15** yazıyordu, kayıttaki oynanan kupon ise
#: **9**/15 yapmıştı (2.304 kolon ↔ 1.296) — yani sayfa hiç oynanmamış bir
#: kuponun karnesini haftanın sonucu diye ilan ediyordu. 2. haftada skor
#: rastlantıyla tutuyordu (12 ↔ 12) ama işaretler ve bedel tutmuyordu.
#:
#: `DONDURULAN` etiketi yalnızca 3. haftadan itibaren yazılıyor; o yüzden
#: geri düşüş kaydın İLK varyantıdır (kayıtların kendi ana planı), sayfanın
#: yeniden hesabı değil. Yeniden hesap ancak kayıt hiç yoksa kullanılır.
_KAYIT_ANA = DONMUS or next(iter(KUPON_JSON.get("variants") or []), None)
OYNANAN = list(_KAYIT_ANA["picks"]) if _KAYIT_ANA else list(ana["picks"])
OYNANAN_AD = (_KAYIT_ANA.get("label") if _KAYIT_ANA else "sayfanın yeniden kurduğu kupon")
OYNANAN_KOLON = (_KAYIT_ANA.get("columns") if _KAYIT_ANA else ana["columns"])

if BITTI:
    gercek = d["meta"]["results"]
    degerlendirme = _deg.kupon_degerlendir(d, OYNANAN)
    kal_karne = _deg.kalabalik_karnesi(d)
    ikramiye = _deg.ikramiye_ozeti(d)
    sayim_g = {x: gercek.count(x) for x in S}
    if KULLANICI:
        import math as _math
        kul_p = KULLANICI["picks"]
        kul_deg = _deg.kupon_degerlendir(d, kul_p)
        kul_banko = _deg.banko_karnesi(d, kul_p)
        ben_banko = _deg.banko_karnesi(d, OYNANAN)
        kiyas = _deg.kupon_kiyas(d, kul_p, OYNANAN)
        kul_kal = _math.prod(
            sum(mm["play"][x] for x in pk) for mm, pk in zip(d["matches"], kul_p))
        kul_uzay = _math.prod(len(x) for x in kul_p)
mer = {p["budget"]: p for p in m.butce_merdiveni(d, [list(x) for x in ana["picks"]], [256, 512])}
o, hist = ref["odds"], ref["hist"]
wa = hist["weekly_avg"]
e = html.escape

def para(n):
    """Türkçe para biçimi: 2.153.527,18"""
    return f"{n:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def tr(n):
    """Binlik ayracı Türkçe: 2.304."""
    return f"{n:,}".replace(",", ".")


def chip(sym, on=True):
    return f'<span class="chip s{sym}{"" if on else " off"}">{sym}</span>'

def marks(pick):
    return "".join(chip(s, s in pick) for s in S)

# ─── maç tablosu
mac_satir = []
for r, kr in zip(prof["rows"], kam["rows"]):
    if r["odds_yok"]:
        oran_hucre = '<td class="num mono yok">oran<span class="sub">yok</span></td>'
    else:
        oran_hucre = (f'<td class="num mono">{r["odds"]["1"]:.2f}'
                      f'<span class="sub">{r["odds"]["0"]:.2f}</span>'
                      f'<span class="sub">{r["odds"]["2"]:.2f}</span></td>')
    hucre = []
    for s in S:
        c = kr["cells"][s]
        fark = 100 * c["diff"]
        sinif = "up" if fark >= 6 else ("down" if fark <= -6 else "")
        hucre.append(
            f'<td class="num {sinif}"><b>{100*c["play"]:.0f}</b>'
            f'<span class="sub">{100*c["prob"]:.0f}</span>'
            f'<span class="delta">{fark:+.0f}</span></td>')
    mac_satir.append(f"""
      <tr>
        <td class="no">{r['no']}</td>
        <td class="mac">{e(r['mac'])}<span class="lig">{r['lig']}</span></td>
        {oran_hucre}
        {''.join(hucre)}
        <td class="band">{e(str(r['fav_band'] or '—'))}<span class="sub">{'—' if r['fav_band_hit'] is None else f"%{r['fav_band_hit']} · n={r['fav_band_n']}"}</span></td>
        <td class="pick">{marks(ana['picks'][r['no']-1])}</td>
      </tr>""")

# ─── kupon ızgarası
grid_rows = []
for i, satir in enumerate(m.kupon_satirlari([list(x) for x in ana["picks"]]), 1):
    hucreler = satir.split()
    tds = "".join(f'<td>{"".join(chip(c) for c in h)}</td>' for h in hucreler)
    grid_rows.append(f'<tr><th scope="row">{i}</th>{tds}</tr>')

# ─── lig kırılımı
lig_satir = []
for lig, n in sorted(prof["leagues"].items(), key=lambda kv: -kv[1]):
    g = ref["lig"].get(lig)
    if g:
        lig_satir.append(f'<tr><td>{lig}</td><td class="num">{n}</td>'
                         f'<td class="num">{g["per_week"]}</td><td class="num">%{g["draw_pct"]}</td>'
                         f'<td class="num">%{g["favourite_hit_pct"]}</td></tr>')
    else:
        lig_satir.append(f'<tr class="yok"><td>{lig}</td><td class="num">{n}</td>'
                         f'<td colspan="3">geçen sezon arşivinde yok — karşılaştırılamaz</td></tr>')

# ─── kalabalık ayrışması (en büyük 6)
ayrisma = []
for kr in kam["rows"]:
    for s in S:
        c = kr["cells"][s]
        ayrisma.append((c["diff"], kr["no"], kr["mac"], s, c["play"], c["prob"]))
ayrisma.sort(key=lambda t: -abs(t[0]))
ayr_html = []
for diff, no, mac, s, play, prob in ayrisma[:6]:
    w = min(100, abs(diff) * 300)
    yon = "up" if diff > 0 else "down"
    ayr_html.append(f"""
      <li class="{yon}">
        <span class="ay-mac">{no}. {e(mac)}</span>
        {chip(s)}
        <span class="ay-bar"><i style="width:{w:.0f}%"></i></span>
        <span class="ay-num">halk %{100*play:.0f} · piyasa %{100*prob:.0f}
          <b>{100*diff:+.0f} puan</b></span>
      </li>""")

#: Fiyat tablosunun satırları. Her hücre arındırılmış olasılıktır; ham oran
#: gösterilseydi marj değişimi fikir değişimi gibi okunurdu.
#: Ayni harita 259 satir yukarida `_SAGLAYICI` olarak DA duruyordu ve
#: buradaki bicimleyici soneksiz bir anahtarda ("pinnacle") `else` dalina
#: dusup "kapanış" UYDURUYORDU. Tek kaynak `odds.saglayici_adi`.
_kitap_adi = saglayici_adi


fiyat_satir = []
for r in FIYAT_SATIR:
    huc = []
    for k in r["esanlı"]:
        p = r["kitaplar"].get(k)
        huc.append(f'<td class="num mono">{100*p["1"]:.0f}/{100*p["0"]:.0f}/'
                   f'{100*p["2"]:.0f}</td>' if p else '<td class="num">—</td>')
    hs, hv = r["hareket_sembol"], r["hareket"]
    hlaf = (f'<b style="color:var(--{"ok" if hv > 0 else "danger"})">{hs} '
            f'{100*hv:+.1f}</b>' if hs and abs(hv) >= 0.005 else
            '<span style="color:var(--dim)">—</span>')
    fiyat_satir.append(
        f'<tr><td class="num mono">{r["no"]}</td><td>{e(r["ad"])}</td>'
        + "".join(huc)
        + f'<td class="num mono">{hlaf}</td>'
        + f'<td class="num mono">{100*r["ayrisma"]:.1f}</td></tr>')

#: Dondurulan kuponun kıyas tablosu ve 16 satırlık ızgarası. Şablonun
#: içinde f-string olarak kurulamıyor (iç içe tırnak), burada kuruluyor.
donmus_satir = []
donmus_grid = []
if DONMUS:
    for v in KUPON_JSON["variants"]:
        vur = (' style="background:var(--accent)"'
               if "DONDURULAN" in v["label"] else "")
        donmus_satir.append(
            f'<tr{vur}><td>{e(v["label"])}</td>'
            f'<td class="num mono">%{100*v["hedef"]:.2f}</td>'
            f'<td class="num mono">{tr(v["columns"])}</td>'
            f'<td class="num mono">%{100*v["in_set_p"]:.3f}</td>'
            f'<td class="num mono">%{100*v["crowd_in_set_p"]:.3f}</td>'
            f'<td class="num mono">{v["crowd_ratio"]:.2f}</td></tr>')
    for i, kupon_satiri in enumerate(KUPON_JSON.get("rows") or []):
        # Ad `hucre` DEGIL: modul duzeyinde 99 satir yukarida `hucre` bir
        # LISTE olarak baglaniyor (satir 266) ve bu betik butun govdesini
        # modul kapsaminda kosuyor, yani ayni ad iki farkli tipi tasiyordu.
        donmus_hucre = "".join(f"<td>{c}</td>" for c in kupon_satiri.split())
        donmus_grid.append(f'<tr><td class="rn">{i+1}</td>{donmus_hucre}</tr>')

fiyat_baslik = "".join(f'<th class="num">{e(_kitap_adi(k))}</th>'
                       for k in (FIYAT_SATIR[0]["esanlı"] if FIYAT_SATIR else []))
marj_rozet = " · ".join(
    f'{e(_kitap_adi(k))} <b style="color:var(--ink)">%{v:.2f}</b>'
    for k, v in KITAP_MARJ.items())


def varyant(v, etiket, vurgu=False):
    deg = "; ".join(v.get("changes", [])) or "kural birebir — kısılan yok"
    return f"""
    <article class="var{' vurgu' if vurgu else ''}">
      <header><h3>{etiket}</h3><span class="kolon">{tr(v['cost'] if 'cost' in v else v['columns'])} kolon</span></header>
      <div class="var-picks">{''.join(f'<span class="vp">{i+1}<em>{p}</em></span>' for i, p in enumerate(v['picks']))}</div>
      <dl>
        <div><dt>Küme-içi</dt><dd>%{100*v['in_set_p']:.3f}</dd></div>
        <div><dt>Kalabalık-içi</dt><dd>%{100*v['crowd_in_set_p']:.3f}</dd></div>
        <div><dt>Oran</dt><dd class="{'iyi' if v['crowd_ratio']>1 else 'kotu'}">{v['crowd_ratio']:.2f}</dd></div>
        <div><dt>Satır</dt><dd>16</dd></div>
      </dl>
      <p class="deg">{e(deg)}</p>
    </article>"""


# ─── neden bu işaret? (maç maç gerekçe)
SEM_AD = {"1": "ev sahibi", "0": "beraberlik", "2": "deplasman"}
from spor_toto.core import Encoder as _Encoder

enc_ana = _Encoder(
    [list(x) for x in ana["picks"]])
blok_maclar = [enc_ana.variable_pos[j] + 1 for j in enc_ana.double_pos()[:7]]
ekstra_maclar = [pz + 1 for i, pz in enumerate(enc_ana.variable_pos)
                 if i not in set(enc_ana.double_pos()[:7])]
ekstra_boy = [len(ana["picks"][x - 1]) for x in ekstra_maclar]
ekstra_carpim = "×".join(str(x) for x in ekstra_boy)
ekstra_toplam = 1
for x in ekstra_boy:
    ekstra_toplam *= x

def gerekce(r, kr, pick):
    mm = d["matches"][r["no"] - 1]
    sirali = mm["sirali"]
    p_fav = sirali[0][1]
    icinde = sum(mm["probs"][x] for x in pick)
    disarida = 1 - icinde
    parcalar = []

    if len(pick) == 1:
        karar, sinif = "BANKO", "banko"
        parcalar.append(
            f'Favori olasılığı <b>%{100*p_fav:.1f}</b>, banko eşiğinin (%68) üstünde — '
            f'kural tek işaret diyor.')
        parcalar.append(
            f'Geçen sezon <b>{r["fav_band"]}</b> oran bandındaki {r["fav_band_n"]} maçın '
            f'%{r["fav_band_hit"]}\'i favoriye gitti; bandın kaçırdıklarının '
            f'%{r["fav_band_draw"]}\'i beraberlikti.')
        parcalar.append(
            f'<b class="risk">Bedeli:</b> %{100*disarida:.1f} ihtimalle bu maç kuponu '
            f'tamamen dışarı atar. Banko yanlışsa 14-garanti geçersizdir — '
            f'kuponun en kırılgan yeri burasıdır.')
    elif len(pick) == 3:
        karar, sinif = "ÜÇLÜ", "uclu"
        parcalar.append(
            f'Favori olasılığı <b>%{100*p_fav:.1f}</b>, üçlü eşiğinin (%38) altında — '
            f'yani piyasanın kendisi de karar veremiyor. Üç sembol de işaretlenir.')
        parcalar.append(
            f'Olasılıklar birbirine yakın: {" · ".join(f"{x}=%{100*v:.0f}" for x, v in sirali)}. '
            f'Böyle bir maçta çifte yapmak kapsamayı '
            f'%{100*(sirali[0][1]+sirali[1][1]):.0f}\'e düşürür ve üçüncü sembolün '
            f'%{100*sirali[2][1]:.0f}\'lik kütlesini tamamen dışarıda bırakırdı — '
            f'piyasanın ayırt edemediği bir maçta bu, bilgi olmadan risk almaktır.')
        parcalar.append(
            '<b class="ok">Kazancı:</b> bu maç kuponu <b>asla</b> dışarı atmaz. '
            'Bedeli, kolon sayısını 3 katına çıkarması.')
    else:
        karar, sinif = "ÇİFTE", "cifte"
        ikinci = sirali[1]
        ucuncu = sirali[2]
        fark = ikinci[1] - ucuncu[1]
        parcalar.append(
            f'Favori olasılığı <b>%{100*p_fav:.1f}</b> — banko için (%68) düşük, üçlü için '
            f'(%38) yüksek. Aradaki her maç çifte olur.')
        if fark < 0.001:
            parcalar.append(
                f'İkinci işaret <b>{ikinci[0]}</b> ({SEM_AD[ikinci[0]]}) ile dışarıda kalan '
                f'<b>{ucuncu[0]}</b> <b class="risk">tam olarak eşit</b>: ikisi de '
                f'%{100*ikinci[1]:.1f}. Oranlar birebir aynı ({mm["odds"][ikinci[0]]:.2f} / '
                f'{mm["odds"][ucuncu[0]]:.2f}), yani piyasa bu iki sonucu ayırt etmiyor. '
                f'Seçim olasılıkla değil, <b>kupon düzeniyle</b> (1–0–2 sırası) çözüldü — '
                f'burada gerçek bir tercih yok, yazı tura var.')
        else:
            parcalar.append(
                f'İkinci işaret <b>{ikinci[0]}</b> ({SEM_AD[ikinci[0]]}, %{100*ikinci[1]:.1f}), '
                f'çünkü dışarıda bıraktığımız <b>{ucuncu[0]}</b> ondan '
                f'{100*fark:.1f} puan düşük (%{100*ucuncu[1]:.1f}).'
                + (' <b class="risk">Bu fark kıl payı</b> — sıralama neredeyse rastgele; '
                   'sonuç buradan gelirse suç olasılıkta değil, farkın küçüklüğünde.'
                   if fark < 0.03 else ''))
        if r["cift_band"]:
            parcalar.append(
                f'Geçen sezon ilk iki sembolün toplamı <b>{r["cift_band"]}</b> bandında olan '
                f'{r["cift_band_n"]} maçın <b>%{r["cift_band_in_two"]}</b>\'i gerçekten o iki '
                f'sembolden birine gitti. Bu haftaki toplam %{100*icinde:.0f}.')
        parcalar.append(
            f'<b class="risk">Bedeli:</b> %{100*disarida:.1f} ihtimalle bu maç kuponu dışarı atar.')

    # kalabalık notu
    en_buyuk = max((abs(kr["cells"][x]["diff"]), x) for x in S)
    if en_buyuk[0] >= 0.08:
        x = en_buyuk[1]
        c = kr["cells"][x]
        yon = "fazla" if c["diff"] > 0 else "az"
        icinde_mi = x in pick
        if c["diff"] > 0 and icinde_mi:
            sonuc = "işaretimin <b>içinde</b> — bu sonuç gelirse ikramiyeyi kalabalık bir grupla bölüşürüz"
        elif c["diff"] > 0 and not icinde_mi:
            sonuc = "işaretimin <b>dışında</b> — kalabalığın yığıldığı yeri kural zaten elemiş"
        elif c["diff"] < 0 and icinde_mi:
            sonuc = ("işaretimin <b>içinde</b> ve halk buraya piyasadan az oynamış — "
                     "kuponun bu maçtaki en değerli tarafı bu")
        else:
            sonuc = "işaretimin <b>dışında</b>"
        parcalar.append(
            f'<b class="kal">Kalabalık:</b> halk <b>{x}</b>\'e piyasadan '
            f'{100*abs(c["diff"]):.0f} puan {yon} oynamış (%{100*c["play"]:.0f} ↔ '
            f'%{100*c["prob"]:.0f}). Bu sembol {sonuc}.')

    return f"""
      <article class="ger {sinif}">
        <header>
          <span class="ger-no">{r['no']}</span>
          <h3>{e(r['mac'])}</h3>
          <span class="ger-karar">{karar}</span>
          <span class="ger-pick">{marks(pick)}</span>
        </header>
        <ul>{''.join(f'<li>{x}</li>' for x in parcalar)}</ul>
      </article>"""

ger_html = "".join(gerekce(r, kr, ana["picks"][r["no"] - 1])
                   for r, kr in zip(prof["rows"], kam["rows"]))

# risk sıralaması
risk = sorted(
    ({"no": mm["no"], "mac": f"{mm['home']} – {mm['away']}", "pick": pk,
      "ic": sum(mm["probs"][x] for x in pk)}
     for mm, pk in zip(d["matches"], ana["picks"])),
    key=lambda z: z["ic"])
risk_html = "".join(
    f'<tr><td class="no">{z["no"]}</td><td class="mac">{e(z["mac"])}</td>'
    f'<td>{marks(z["pick"])}</td><td class="num mono">%{100*z["ic"]:.1f}</td>'
    f'<td class="num mono risk-n">%{100*(1-z["ic"]):.1f}</td></tr>'
    for z in risk)

sayilar = {"banko": len(ana["banko"]), "cift": len(ana["cift"]), "uclu": len(ana["uclu"])}


# ─── sonuç blokları
if BITTI:
    # maç maç karne
    karne = []
    for r in degerlendirme["per_match"]:
        at = " · ".join(f'{x} %{100*r["p_atilan"][x]:.0f}' for x in r["atilan"]) or "—"
        karne.append(f"""
      <tr class="{'tuttu' if r['tuttu'] else 'kacti'}">
        <td class="no">{r['no']}</td>
        <td class="mac">{e(r['mac'])}</td>
        <td>{marks(r['pick'])}</td>
        <td class="sonuc-h">{chip(r['gercek'])}</td>
        <td class="band">{at}</td>
        <td class="im">{'✓' if r['tuttu'] else '✗'}</td>
      </tr>""")
    karne_html = "".join(karne)

    # kaçak dağılımı çubukları
    dist = degerlendirme["dist"]
    enb = max(dist)
    dag = []
    for i, v in enumerate(dist[:9]):
        bu = i == degerlendirme["miss_count"]
        bek = abs(i - round(degerlendirme["expected_misses"])) < 0.5
        dag.append(f"""
        <li class="{'bu' if bu else ('bek' if bek else '')}">
          <span class="d-k">{i}</span>
          <span class="d-bar"><i style="width:{100*v/enb:.1f}%"></i></span>
          <span class="d-p">%{100*v:.1f}</span>
          <span class="d-not">{'← gerçekleşen' if bu else ('← en olası' if bek else '')}</span>
        </li>""")
    dag_html = "".join(dag)

    ikr_satir = []
    for t in ikramiye.get("tiers", []):
        if t["prize"] is None:
            kisi = "—"
            tutar = "çıkmadı"
            not_ = f'{para(t.get("rollover", 0))} TL devretti'
        else:
            kisi = tr(t["winners"])
            tutar = f'{para(t["prize"])} TL'
            not_ = f'toplam {para(t["toplam"])} TL'
        ikr_satir.append(
            f'<tr><td><b>{t["correct"]} bilen</b></td>'
            f'<td class="num mono">{kisi}</td>'
            f'<td class="num mono">{tutar}</td>'
            f'<td class="band">{not_}</td></tr>')
    ikr_html = "".join(ikr_satir)
    ikr_var = bool(ikramiye.get("tiers"))
    # Tablo YOKSA sayfa bos bir tablo basmaz: eksikligi yazar. Bos
    # tablo "ikramiye dagilmadi" gibi okunur; oysa olan sey, verinin
    # girilmemis olmasi (2. hafta tam olarak bu durumda).
    ikr_bolum = (
        '<div class="scroll"><table><thead><tr><th>Kademe</th>'
        '<th class="num">Kişi</th><th class="num">Kişi başı</th>'
        '<th>Not</th></tr></thead><tbody>' + ikr_html + '</tbody></table></div>'
        if ikr_var else
        '<p style="font-size:13.5px;color:var(--dim);max-width:70ch">Bu haftanın '
        '<b style="color:var(--ink)">ikramiye ekranı girilmedi</b>. Kişi başı ödül ve '
        'kazanan adedi olmadan havuz tarafı — kalabalık ayarının karşılığı, kolon '
        'başına getiri — ölçülemez.</p>')
else:
    karne_html = dag_html = ikr_html = ikr_bolum = ""


if BITTI:
    dg = degerlendirme
    kayip = [r for r in dg["per_match"] if not r["tuttu"]]
    ber_kacak = [r for r in kayip if r["gercek"] == "0"]
    # Nesirdeki her nitelemenin kaynagi. Bu blok sayfanin kendi sozunun
    # ("bu dosyada elle yazilmis tek bir olcum yoktur") bekcisidir: burada
    # once 1. haftaya OZGU cumleler sabit yaziliydi — ikramiye kademesine
    # ulasilamadigi, kalabalik kuponunun piyasayla birebir ayni oldugu ve
    # 14 bilenin kisi basi odulu. 2. hafta girildiginde ucu de yanlis oldu.
    HEDEF = _deg.HEDEF_KADEME
    hedefe_ulasti = dg["best"] >= HEDEF
    # Rozet 1. haftanin 9'una sabitlenmisti ("ikramiye yok"); 3. haftada
    # kupon 14 yapinca rozet ile govde birbirini yalanladi.
    ROZET_KADEME = (f"{HEDEF}+ kademesinde" if hedefe_ulasti else "ikramiye yok")
    # Kuyruk YONU sonuca gore secilir. `p_at_least_actual` kotu haftanin
    # olcusudur (P(kacak >= gerceklesen)); iyi bir haftada o sayi 1'e yakin
    # cikar ve sansli hafta siradan gorunurdu — 3. haftada tam bu oldu:
    # 1 kacak %97'lik "kuyruk" diye yazildi, oysa P(kacak <= 1) %15,2'ydi.
    _p_alt = sum(dg["dist"][: dg["miss_count"] + 1])
    _iyi = dg["miss_count"] <= dg["expected_misses"]
    KUYRUK_YON = "beklenenden iyi" if _iyi else "beklenenden kötü"
    KUYRUK_AD = "iyi" if _iyi else "kötü"
    KUYRUK_P = _p_alt if _iyi else dg["p_at_least_actual"]
    enb_kacak = max(range(len(dg["dist"])), key=lambda i: dg["dist"][i])
    ber_ort = ref["hist"]["bands"]["0"]["avg"]
    halk_ayni = kal_karne["halk_kuponu"] == kal_karne["piyasa_kuponu"]
    ber_notu = ("" if not ber_kacak else
                f", bunların <b>{len(ber_kacak)}'ü beraberlikti</b> — çifte "
                "yaparken üçüncü sembol olarak attığım beraberlikler")
    serit = "".join(
        f'<span class="sh">{chip(x)}<small>{i+1}</small></span>'
        for i, x in enumerate(gercek))
    sonuc_bolumu = f"""
  <section>
    <header>
      <span class="eyebrow">Sonuç · kupon donduruldu, hafta oynandı</span>
      <h2>Kupon {dg['best']}/15 ile bitti</h2>
      <p>İkramiye kademesi {HEDEF}'ydi; kupon oraya <b>{'ulaştı' if hedefe_ulasti else 'ulaşamadı'}</b>.
      On beş maçın <b>{dg['miss_count']}'sında</b> gerçek sonuç işaretlerimin dışında kaldı{ber_notu}.
      Haftanın sembol dağılımı {sayim_g['1']} / {sayim_g['0']} / {sayim_g['2']}: {sayim_g['0']} beraberlik
      çıktı, geçen sezonun hafta ortalaması {ber_ort:.2f}'ti.</p>
      <p style="font-size:12.5px;color:var(--dim);max-width:74ch">Bu bölümün puanladığı kupon
      <b style="color:var(--ink)">kayıttakidir</b> — “{e(str(OYNANAN_AD))}”, {tr(OYNANAN_KOLON)} kolon.
      Sayfanın yukarıdaki bölümlerde <i>bugünkü</i> kuralla yeniden kurduğu kupon
      {'aynısıdır' if list(ana['picks']) == list(OYNANAN) else 'bundan FARKLIDIR ve oynanmamıştır'}.</p>
    </header>
    <div class="sonuc-serit">{serit}</div>
    <div class="scroll">
      <table>
        <thead><tr><th>#</th><th>Maç</th><th>İşaretim</th><th>Sonuç</th><th>Attığım sembol(ler)</th><th></th></tr></thead>
        <tbody>{karne_html}</tbody>
      </table>
    </div>

    <h3 style="margin:34px 0 6px">Şanssızlık mıydı, hata mıydı?</h3>
    <p style="font-size:13.5px;color:var(--dim);max-width:68ch;margin-bottom:16px">
      Kuponun kendi olasılıklarına göre <b style="color:var(--ink)">beklenen kaçak sayısı {dg['expected_misses']:.2f}</b>,
      en olası senaryo {enb_kacak} kaçaktı. {dg['miss_count']} kaçak geldi — hafta
      <b style="color:var(--ink)">{KUYRUK_YON}</b> geçti ve bu kadar {KUYRUK_AD} bir haftanın
      olasılığı %{100*KUYRUK_P:.0f} idi.
      Asıl mesele bu değil: {dg['miss_count']} kaçak
      <b style="color:var(--ink)">{"14'e zaten yetmiyordu" if dg['miss_count'] > 1 else "14'ü hâlâ mümkün bırakıyordu"}.</b>
      Kupon daha atılmadan beklentisi {15-dg['expected_misses']:.1f} doğruydu; 14 hedefi için gereken
      "sıfır kaçak" ihtimali %{100*dg['p_in_set']:.2f} idi.</p>
    <ul class="dag">{dag_html}</ul>

    <h3 style="margin:34px 0 14px">İkramiye nasıl dağıldı</h3>
    {ikr_bolum}
    <p style="margin-top:14px;font-size:13px;color:var(--dim);max-width:70ch">
      Halkın en çok oynadığı kupon <span class="mono">{kal_karne['halk_kuponu']}</span> —
      <b style="color:var(--ink)">{kal_karne['halk_dogru']}/15</b> tutturdu. Piyasanın favori kuponu
      <b style="color:var(--ink)">{'bunun birebir aynısı' if halk_ayni else 'ondan farklı'}</b>
      ve o {kal_karne['piyasa_dogru']}/15 yaptı. Rastgele bir halk kuponunun beklenen doğrusu
      {kal_karne['beklenen_halk_dogru']:.2f}'ydi. <b style="color:var(--ink)">İkramiyeyi büyüten şey,
      kalabalığın da tutturamamasıdır</b> — kupon tuttuğunda bölüşülecek kişi sayısı buradan okunur.</p>
  </section>"""
else:
    sonuc_bolumu = ""


if BITTI:
    dersler_bolumu = f"""
  <section>
    <header>
      <span class="eyebrow">Dersler · her biri ölçüme bağlı</span>
      <h2>Bir dahakine ne değişecek</h2>
      <p>Aşağıdaki her ders, bu haftanın hikâyesinden değil, geçen sezonun 567 maçında ya da 36 haftasında
      yeniden koşulmuş bir ölçümden çıkıyor. Tek maça bakıp kural değiştirmek, bu projenin baştan beri
      uyardığı hatanın ta kendisi olurdu.</p>
    </header>

    <div class="ders">
      <span class="olcum">Ölçüm · 36 hafta yeniden koşuldu</span>
      <h3>1. Hedefi yanlış koydum. 14 değil, 12–13.</h3>
      <p>Aynı kuralın geçen sezonki en iyi kolon dağılımı şöyleydi:
      <b>14 → 3 hafta, 13 → 6, 12 → 12, 11 → 9, 10 → 3, 9 → 3.</b>
      Yani kupon haftaların {'%'}58'inde ödeme eşiği olan 12'ye ulaşıyor, {'%'}8'inde 14'e.
      Bu hafta kuponun kendi matematiği de aynı şeyi söylüyordu: beklenen en iyi kolon
      <b>11,7</b>. Ben ise kuponu 14 hedefiyle kurdum ve "14-garanti" etiketiyle sundum.</p>
      <p>Etiket teknik olarak doğruydu — ama <b>koşullu</b> bir garantiyi hedef sanmak yanlıştı.
      Bu haftanın ödeme tablosu farkı gösteriyor: 12 bilen {para(7532.44)} TL, 13 bilen
      {para(82039.13)} TL, 14 bilen {para(2153527.18)} TL.</p>
      <p class="karar"><b>Karar:</b> kuponu bundan sonra "sıfır kaçak" olasılığına göre değil,
      <b>12–13'e ulaşma olasılığına</b> göre kuracağım. Bu, işaret sayısını değil hedef fonksiyonunu
      değiştirir ve raporun en üstünde artık bu sayı duracak.</p>
    </div>

    <div class="ders">
      <span class="olcum">Ölçüm · 567 maç, kimliğe göre kalibrasyon</span>
      <h3>2. Beraberliği atmak, kenar takımı atmaktan 1,6 kat pahalı</h3>
      <p>"Çifte" kuralı en olası iki sembolü işaretler, üçüncüyü atar. Ama atılan sembolün
      <b>kim olduğu</b> çok şey değiştiriyor. Geçen sezonun 567 maçında ölçtüm:</p>
      <p>Atılan sembol <b>beraberlik</b> ise {'%'}<b>25,8</b> ihtimalle geliyor (piyasa {'%'}26,9 demişti — yani
      piyasa beraberliği neredeyse tam fiyatlıyor). Atılan sembol <b>ev sahibi</b> ise {'%'}16,0
      (piyasa {'%'}20,0 demişti), <b>deplasman</b> ise {'%'}15,6 (piyasa {'%'}18,7). Kenar takımlar
      fiyatlarının 3–4 puan altında geliyor; beraberlik gelmiyor.</p>
      <p>Bu hafta 4 maçta beraberliği attım — 3'ü beraberlikle bitti. Üstelik bunların ikisini
      (<b>9. ve 13. maç</b>) raporda "kıl payı" diye <b>kendim işaretlemiştim</b> ve yine de attım.
      İşaretleyip bir şey yapmamak, karar değil not almaktır.</p>
      <p class="karar"><b>Karar:</b> "çifte" artık tek tip sayılmayacak. Beraberlik atan çifte ile
      kenar atan çifte ayrı raporlanacak, ve kuponun beklenen kaçağı bu ayrımla hesaplanacak.</p>
    </div>

    <div class="ders">
      <span class="olcum">Ölçüm · 7 alternatif kural, 36 hafta</span>
      <h3>3. Ama beraberliği korumak çözüm değil — denedim</h3>
      <p>2. dersin akla getirdiği çözüm şu: beraberlik canlıysa üçlü yap. Bunu geçen sezonun tamamında
      koşturdum. Kolon başına maliyet (bir 14 için kaç kolon):</p>
      <p><b>Kullandığım kural (0.68/0.38): 32.235 kolon/14.</b> Beraberlik koruması p₀≥0,28: 50.933.
      Üçlü eşiği 0,42: 61.208. Beraberlik koruması p₀≥0,25: 80.520. Banko yok: 84.480.</p>
      <p>Koruma isabeti artırıyor (3 → 4 hafta) ama bedeli 2,5 katına çıkarıyor. Yani 2. dersin cevabı
      "daha çok üçlü" değil.</p>
      <p class="karar"><b>Karar:</b> kural değişmiyor. Doğru yön, işaret genişletmek değil —
      1. derste yazdığı gibi <b>hedefi düşürmek</b>, ya da aynı parayı daha az haftaya yığmak.</p>
    </div>

    <div class="ders">
      <span class="olcum">Ölçüm · karşı-olgusal koşu</span>
      <h3>4. Bankonun suçu yoktu</h3>
      <p>Galatasaray 1.22 oranla berabere kaldı ve kuponu tek başına bitirdi. En kolay ders
      "banko yapma" olurdu — ama yanlış olurdu. "Beraberlik olasılığı {'%'}20'nin üstündeyse banko yapma"
      kuralını geçen sezonda koşturdum: <b>aynı 3 isabet, neredeyse aynı maliyet</b> (2.743 kolon).
      Bu haftada da hiçbir şey değişmiyordu — yine 6 kaçak, yine 9 doğru.</p>
      <p class="karar"><b>Karar:</b> banko kuralı duruyor. Tek maçın acısıyla kural değiştirmek,
      bu projenin geçen sezon hold-out'unda ({'%'}0 isabet) zaten ölçtüğü aşırı uyum hatasıdır.</p>
    </div>

    <div class="ders">
      <span class="olcum">Ölçüm · bu haftanın oynanma verisi</span>
      <h3>5. Kalabalık verisi yön için değil, büyüklük için işe yarıyor</h3>
      <p>Halkın en çok oynadığı işaretlerden kurulu kupon: <span class="mono">{kal_karne['halk_kuponu']}</span>.
      Piyasanın favori kuponu: <span class="mono">{kal_karne['piyasa_kuponu']}</span>.
      <b>On beş hanenin on beşi de aynı.</b> İkisi de 6/15 tutturdu.</p>
      <p>Yani "kalabalığın tersine oyna" diye ayrı bir sinyal yok — kalabalık, yönü piyasadan alıyor.
      Verinin taşıdığı bilgi <b>yönde değil, şiddette</b>: Celta'ya {'%'}77 (piyasa {'%'}47),
      Beşiktaş'a {'%'}89 (piyasa {'%'}73). Bu farklar hangi işareti seçeceğimi değil,
      tutturursam kaç kişiyle bölüşeceğimi anlatıyor.</p>
      <p class="karar"><b>Karar:</b> oynanma yüzdesini işaret seçimine sokmaya çalışmayacağım.
      Yeri, kuponun beklenen <b>payı</b> hesabı — ve o hesap ancak ikramiye verisi birikince kurulur.</p>
    </div>

    <div class="ders">
      <span class="olcum">Ölçüm · 36 hafta + ilk ikramiye gözlemi</span>
      <h3>6. İkramiye ile isabet ters çalışıyor — asıl ders bu</h3>
      <p>14 bileni yalnızca 8 kişi buldu ve kişi başı {para(2153527.18)} TL aldı. Ödülün bu kadar büyük
      olmasının sebebi haftanın zorluğu — yani <b>bizi bitiren şeyin ta kendisi</b>.</p>
      <p>Bunun tesadüf olmadığını geçen sezonda ölçtüm: kuralın en iyi kolonu <b>13+</b> yaptığı haftalarda
      ortalama <b>9,00</b> favori tutmuştu; <b>11 ve altı</b> yaptığı haftalarda <b>7,47</b>.
      Yani strateji, favorilerin tuttuğu "kolay" haftalarda başarılı oluyor — tam da kalabalığın da
      tutturduğu ve ikramiyenin bölündüğü haftalarda.</p>
      <p>Bu hafta 6/15 favori tuttu; geçen sezonun 36 haftasında bundan kötü yalnızca 4 hafta vardı.
      Tek deplasman galibiyeti ise 36 haftada 2 kez görülmüş bir uçtu.</p>
      <p class="karar"><b>Karar:</b> isabet olasılığını büyütmek, kazancı büyütmeyebilir. Bunu kanıtlamak
      ya da çürütmek için haftalık ikramiye verisi gerekiyor — <b>bu hafta 1. gözlem</b>. Her hafta
      kazanan sayısı + tutar kaydedilecek; 8–10 hafta sonra "isabet mi, pay mı" sorusu ilk kez
      ölçülebilir hale gelir.</p>
    </div>
  </section>"""
else:
    dersler_bolumu = ""


if BITTI and KULLANICI:
    kiyas_satir = []
    for r in kiyas["rows"]:
        ikisi = (not r["a_tuttu"]) and (not r["b_tuttu"])
        kiyas_satir.append(f"""
      <tr class="{'ikisi-de' if ikisi else ''}">
        <td class="no">{r['no']}</td>
        <td class="mac">{e(r['mac'])}</td>
        <td class="iki-a">{marks(r['a'])} {'✓' if r['a_tuttu'] else '✗'}</td>
        <td class="iki-b">{marks(r['b'])} {'✓' if r['b_tuttu'] else '✗'}</td>
        <td>{chip(r['gercek'])}</td>
      </tr>""")
    kiyas_html = "".join(kiyas_satir)

    kul_banko_satir = "".join(
        f'<tr class="{"tuttu" if r["tuttu"] else "kacti"}"><td class="no">{r["no"]}</td>'
        f'<td class="mac">{e(r["mac"])}</td><td>{chip(r["sembol"])}</td>'
        f'<td>{chip(r["gercek"])}</td><td class="num mono">%{100*r["p"]:.0f}</td>'
        f'<td class="im">{"✓" if r["tuttu"] else "✗"}</td></tr>'
        for r in kul_banko["rows"])

    dis_banko = [r for r in kul_banko["rows"] if r["sembol"] == "2"]
    dis_tutan = sum(1 for r in dis_banko if r["tuttu"])

    iki_kupon_bolumu = f"""
  <section>
    <header>
      <span class="eyebrow">Karşılaştırma · iki farklı yol, aynı sonuç</span>
      <h2>Senin kuponun da 9/15</h2>
      <p>İki kupon birbirinden çok farklı kuruldu — seninki 7 banko ile dar ve ucuz, benimki 11 çifte ile
      geniş ve pahalı. İkisi de aynı yerde bitti. Bu tesadüf değil: haftayı bitiren maçlar
      <b>ikimizin de kaçırdığı</b> maçlardı.</p>
    </header>

    <div class="ik">
      <div class="sen">
        <h4>Senin kuponun</h4>
        <div class="skor">9<span>/15</span></div>
        <dl>
          <div><dt>Yapı</dt><dd style="font-size:13px">{kul_banko['n']} banko · {sum(1 for x in kul_p if len(x)==2)} çifte · {sum(1 for x in kul_p if len(x)==3)} üçlü</dd></div>
          <div><dt>Kolon</dt><dd>{tr(kul_uzay)}</dd></div>
          <div><dt>Küme-içi</dt><dd>%{100*kul_deg['p_in_set']:.3f}</dd></div>
          <div><dt>Beklenen kaçak</dt><dd>{kul_deg['expected_misses']:.2f}</dd></div>
        </dl>
      </div>
      <div class="kur">
        <h4>Kural kuponu (benim)</h4>
        <div class="skor">9<span>/15</span></div>
        <dl>
          <div><dt>Yapı</dt><dd style="font-size:13px">{ben_banko['n']} banko · {len(ana['cift'])} çifte · {len(ana['uclu'])} üçlü</dd></div>
          <div><dt>Kolon</dt><dd>{tr(ana['columns'])}</dd></div>
          <div><dt>Küme-içi</dt><dd>%{100*degerlendirme['p_in_set']:.3f}</dd></div>
          <div><dt>Beklenen kaçak</dt><dd>{degerlendirme['expected_misses']:.2f}</dd></div>
        </dl>
      </div>
    </div>

    <p style="font-size:13.5px;color:var(--dim);max-width:70ch;margin-bottom:18px">
      Benim kuponumun tutma ihtimali seninkinin <b style="color:var(--ink)">11 katıydı</b>
      (%{100*degerlendirme['p_in_set']:.2f}'e karşı %{100*kul_deg['p_in_set']:.2f}) ve
      <b style="color:var(--ink)">6 kat</b> daha fazla kolona mal oluyordu. Bu hafta o fark hiçbir şey satın almadı:
      fazladan ödenen her kolon, zaten kaybedilmiş bir kuponu genişletti.</p>

    <div class="scroll">
      <table>
        <thead><tr><th>#</th><th>Maç</th><th>Senin</th><th>Kural</th><th>Sonuç</th></tr></thead>
        <tbody>{kiyas_html}</tbody>
      </table>
    </div>
    <p style="margin-top:12px;font-size:12.5px;color:var(--dim)">
      Kırmızı satırlar <b style="color:var(--ink)">ikimizin de kaçırdığı</b> maçlar.</p>

    <h3 style="margin:34px 0 6px">Haftayı bitiren dört maç</h3>
    <p style="font-size:13.5px;color:var(--dim);max-width:70ch;margin-bottom:14px">
      1, 5, 11 ve 13. maçlar iki kuponu da dışarı attı. Piyasa bu dört sonuca sırasıyla
      %17,6 · %18,0 · %20,2 · %24,9 vermişti; dördünün aynı hafta gerçekleşme olasılığı
      <b style="color:var(--ink)">1/627</b>. İki kupon <b style="color:var(--ink)">birleştirilse</b> bile
      ({tr(kiyas['union_space'])} kolon) sonuç {kiyas['union_best']}/15 olurdu — yine ödeme eşiğinin altında.
      Bu hafta seçimle ulaşılabilir değildi.</p>

    <h3 style="margin:30px 0 14px">Senin bankoların</h3>
    <div class="scroll">
      <table>
        <thead><tr><th>#</th><th>Maç</th><th>Banko</th><th>Sonuç</th><th class="num">Piyasa</th><th></th></tr></thead>
        <tbody>{kul_banko_satir}</tbody>
      </table>
    </div>
    <p style="margin-top:14px;font-size:13.5px;color:var(--dim);max-width:70ch">
      <b style="color:var(--ink)">{kul_banko['dogru']}/{kul_banko['n']} tuttu; beklenen {kul_banko['beklenen']:.2f}</b>'ydi.
      Asıl kırılma noktası şu: bankolarının {len(dis_banko)}'ü <b style="color:var(--ink)">deplasman</b> işaretiydi
      (Trabzonspor, Fenerbahçe, PSG, Villarreal) ve <b style="color:var(--ink)">{dis_tutan}'i tuttu</b>.
      Haftada toplam <b style="color:var(--ink)">tek bir</b> deplasman galibiyeti vardı — o da
      Konyaspor–Rizespor'daki Rizespor'du: haftanın tek deplasman galibiyeti, senin deplasman
      işaretlemediğin maçlardan birinde geldi.
      Dört bankonun dördü de %48–58 aralığındaydı; kural kuponunun banko eşiği %68'dir ve
      bu maçların hiçbirini banko yapmazdı.</p>
  </section>"""
else:
    iki_kupon_bolumu = ""

ana_v = dict(ana)
ana_v["cost"] = ana["columns"]
#: Belge kabugu. Sayfa uzun sure dogrudan `<title>` ile basliyordu: ne
#: doctype, ne `<head>`, ne de **`<meta charset>`**. Baytlar UTF-8'di ama
#: bildirim olmadan tarayici dosyayi kendi varsayilaniyla (cogu zaman
#: latin-1) okuyor ve Turkce harfler bozuluyordu. Arayuzun icinde sorun
#: gorunmuyordu cunku orada kabugu Next.js kuruyor; tek basina acilan
#: dosyada gorunuyordu.
HTML = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Süper Toto {_a.hafta}. Hafta</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@1,6..96,400;1,6..96,600;0,6..96,600&display=swap">
<style>
:root {{
  --bg: hsl(0 0% 100%); --ink: hsl(258 30% 10%); --card: hsl(0 0% 100%);
  --elev: hsl(260 40% 99%); --muted: hsl(260 20% 96%); --dim: hsl(258 12% 44%);
  --line: hsl(260 16% 90%); --line2: hsl(260 16% 82%);
  --primary: hsl(262 83% 58%); --accent: hsl(262 83% 96%);
  --s1: hsl(262 83% 58%); --s0: hsl(199 89% 44%); --s2: hsl(330 76% 52%);
  --warn: hsl(32 92% 45%); --warn-soft: hsl(38 95% 94%);
  --ok: hsl(152 58% 38%); --ok-soft: hsl(152 60% 95%);
  --danger: hsl(0 72% 48%); --danger-soft: hsl(0 85% 96%);
  --shadow: 0 4px 20px -2px hsl(262 83% 58% / .10);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: hsl(258 28% 7%); --ink: hsl(260 20% 96%); --card: hsl(258 26% 10%);
    --elev: hsl(258 24% 13%); --muted: hsl(258 20% 15%); --dim: hsl(258 12% 64%);
    --line: hsl(258 18% 19%); --line2: hsl(258 18% 28%);
    --primary: hsl(262 83% 70%); --accent: hsl(262 40% 18%);
    --s1: hsl(262 83% 68%); --s0: hsl(199 89% 54%); --s2: hsl(330 76% 62%);
    --warn: hsl(38 95% 62%); --warn-soft: hsl(32 60% 16%);
    --ok: hsl(152 50% 55%); --ok-soft: hsl(152 40% 14%);
    --danger: hsl(0 75% 65%); --danger-soft: hsl(0 45% 15%);
    --shadow: 0 4px 24px -4px hsl(0 0% 0% / .5);
  }}
}}
:root[data-theme="dark"] {{
  --bg: hsl(258 28% 7%); --ink: hsl(260 20% 96%); --card: hsl(258 26% 10%);
  --elev: hsl(258 24% 13%); --muted: hsl(258 20% 15%); --dim: hsl(258 12% 64%);
  --line: hsl(258 18% 19%); --line2: hsl(258 18% 28%);
  --primary: hsl(262 83% 70%); --accent: hsl(262 40% 18%);
  --s1: hsl(262 83% 68%); --s0: hsl(199 89% 54%); --s2: hsl(330 76% 62%);
  --warn: hsl(38 95% 62%); --warn-soft: hsl(32 60% 16%);
  --ok: hsl(152 50% 55%); --ok-soft: hsl(152 40% 14%);
  --danger: hsl(0 75% 65%); --danger-soft: hsl(0 45% 15%);
  --shadow: 0 4px 24px -4px hsl(0 0% 0% / .5);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.6 "Helvetica Neue", Helvetica, "Segoe UI", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}}
.wrap {{ max-width: 1120px; margin: 0 auto; padding: 40px 20px 80px; }}
h1, h2, h3 {{ font-family: "Bodoni Moda", Didot, "Bodoni MT", Georgia, serif; font-style: italic; font-weight: 600; text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(32px, 6vw, 46px); line-height: 1.05; letter-spacing: -.01em; }}
h2 {{ font-size: 24px; line-height: 1.2; }}
h3 {{ font-size: 17px; }}
p {{ margin: 0; }}
.eyebrow {{ font: 600 10.5px/1 ui-sans-serif, sans-serif; letter-spacing: .16em; text-transform: uppercase; color: var(--dim); }}
section {{ margin-top: 56px; }}
section > header {{ display: flex; flex-direction: column; gap: 6px; padding-bottom: 14px; border-bottom: 1px solid var(--line2); margin-bottom: 22px; }}
section > header p {{ color: var(--dim); font-size: 13.5px; max-width: 68ch; }}
.mono, .num, table {{ font-variant-numeric: tabular-nums; }}

/* başlık */
.hero {{ display: flex; flex-direction: column; gap: 14px; }}
.hero .prog {{ color: var(--dim); font-size: 14px; }}
.rozetler {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.rozet {{ font-size: 11.5px; font-weight: 500; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line2); color: var(--dim); background: var(--muted); }}
.rozet.mor {{ background: var(--accent); border-color: var(--primary); color: var(--primary); }}
.rozet.uyari {{ background: var(--warn-soft); border-color: var(--warn); color: var(--warn); }}

/* stat */
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 26px; }}
.stat {{ background: var(--elev); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; }}
.stat .k {{ font: 600 10.5px/1 sans-serif; letter-spacing: .1em; text-transform: uppercase; color: var(--dim); }}
.stat .v {{ font-size: 27px; font-weight: 600; line-height: 1.15; margin-top: 7px; font-variant-numeric: tabular-nums; }}
.stat .a {{ font-size: 12px; color: var(--dim); margin-top: 3px; }}

/* tablo */
.scroll {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 14px; background: var(--card); box-shadow: var(--shadow); }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ padding: 9px 10px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: middle; white-space: nowrap; }}
thead th {{ font: 600 10.5px/1.3 sans-serif; letter-spacing: .08em; text-transform: uppercase; color: var(--dim); background: var(--muted); position: sticky; top: 0; }}
tbody tr:last-child td {{ border-bottom: 0; }}
td.num, th.num {{ text-align: right; }}
td.no {{ color: var(--dim); width: 28px; }}
td.mac {{ white-space: normal; min-width: 190px; font-weight: 500; }}
td.mac .lig {{ display: inline-block; margin-left: 7px; font-size: 10px; letter-spacing: .08em; color: var(--dim); border: 1px solid var(--line2); border-radius: 4px; padding: 1px 5px; vertical-align: 1px; }}
.sub {{ display: block; font-size: 11px; color: var(--dim); }}
.delta {{ display: block; font-size: 10.5px; font-weight: 600; }}
td.up .delta {{ color: var(--warn); }}
td.down .delta {{ color: var(--s0); }}
td.up {{ background: var(--warn-soft); }}
td.band {{ font-size: 12px; color: var(--dim); }}
tr.yok td {{ color: var(--dim); font-style: italic; }}

/* sembol çipi */
.chip {{ display: inline-grid; place-items: center; width: 21px; height: 21px; border-radius: 6px; font: 700 12px/1 ui-monospace, "SF Mono", Menlo, monospace; color: #fff; margin-right: 3px; }}
.chip.s1 {{ background: var(--s1); }} .chip.s0 {{ background: var(--s0); }} .chip.s2 {{ background: var(--s2); }}
.chip.off {{ background: transparent; color: var(--line2); border: 1px dashed var(--line2); }}

/* kalabalık */
.ayr {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }}
.ayr li {{ display: grid; grid-template-columns: minmax(150px, 1.4fr) auto minmax(70px, 1fr) auto; align-items: center; gap: 12px; padding: 10px 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); font-size: 13px; }}
.ay-mac {{ font-weight: 500; }}
.ay-bar {{ height: 7px; border-radius: 999px; background: var(--muted); overflow: hidden; }}
.ay-bar i {{ display: block; height: 100%; border-radius: 999px; }}
.ayr li.up .ay-bar i {{ background: var(--warn); }}
.ayr li.down .ay-bar i {{ background: var(--s0); }}
.ay-num {{ font-size: 11.5px; color: var(--dim); text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.ay-num b {{ color: var(--ink); }}

/* kupon */
.grid-kupon th, .grid-kupon td {{ padding: 5px 6px; text-align: center; }}
.grid-kupon th[scope="row"] {{ color: var(--dim); font-weight: 500; font-size: 11px; background: var(--muted); position: sticky; left: 0; }}
.grid-kupon .chip {{ margin: 0 1px; }}
.varyantlar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 18px; }}
.var {{ border: 1px solid var(--line); border-radius: 14px; padding: 16px; background: var(--card); }}
.var.vurgu {{ border-color: var(--primary); box-shadow: var(--shadow); }}
.var header {{ display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 12px; }}
.var .kolon {{ font: 600 12px ui-monospace, Menlo, monospace; color: var(--primary); }}
.var-picks {{ display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }}
.vp {{ font-size: 9.5px; color: var(--dim); border: 1px solid var(--line); border-radius: 6px; padding: 2px 4px; text-align: center; line-height: 1.25; }}
.vp em {{ display: block; font-style: normal; font: 700 12px ui-monospace, Menlo, monospace; color: var(--ink); }}
.var dl {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0 0 10px; }}
.var dt {{ font: 600 9.5px/1 sans-serif; letter-spacing: .09em; text-transform: uppercase; color: var(--dim); }}
.var dd {{ margin: 3px 0 0; font-size: 16px; font-weight: 600; font-variant-numeric: tabular-nums; }}
.var dd.kotu {{ color: var(--warn); }} .var dd.iyi {{ color: var(--ok); }}
.var .deg {{ font-size: 11.5px; color: var(--dim); border-top: 1px solid var(--line); padding-top: 9px; }}

/* sonuç */
.sonuc-serit {{ display: flex; flex-wrap: wrap; gap: 5px; margin: 4px 0 18px; }}
.sonuc-serit .sh {{ display: grid; place-items: center; gap: 2px; }}
.sonuc-serit .sh small {{ font-size: 9.5px; color: var(--dim); }}
tr.tuttu td.im {{ color: var(--ok); font-weight: 700; }}
tr.kacti td.im {{ color: var(--danger); font-weight: 700; }}
tr.kacti {{ background: var(--danger-soft); }}
td.sonuc-h {{ width: 44px; }}
.dag {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 5px; }}
.dag li {{ display: grid; grid-template-columns: 22px minmax(80px, 1fr) 52px minmax(90px, auto); align-items: center; gap: 10px; font-size: 12.5px; color: var(--dim); }}
.dag .d-k {{ font: 600 12px ui-monospace, Menlo, monospace; color: var(--ink); text-align: right; }}
.dag .d-bar {{ height: 12px; border-radius: 4px; background: var(--muted); overflow: hidden; }}
.dag .d-bar i {{ display: block; height: 100%; background: var(--line2); }}
.dag li.bek .d-bar i {{ background: var(--primary); }}
.dag li.bu .d-bar i {{ background: var(--danger); }}
.dag .d-p {{ font-variant-numeric: tabular-nums; text-align: right; }}
.dag .d-not {{ font-size: 11px; font-weight: 600; }}
.dag li.bu .d-not {{ color: var(--danger); }}
.dag li.bek .d-not {{ color: var(--primary); }}
.ders {{ border: 1px solid var(--line); border-radius: 14px; background: var(--card); padding: 18px 20px; }}
.ders + .ders {{ margin-top: 12px; }}
.ders h3 {{ font-size: 17px; margin-bottom: 8px; }}
.ders .olcum {{ display: inline-block; font: 600 10.5px/1 sans-serif; letter-spacing: .1em; text-transform: uppercase; color: var(--primary); background: var(--accent); border-radius: 6px; padding: 4px 8px; margin-bottom: 9px; }}
.ders p {{ font-size: 13.5px; line-height: 1.65; color: var(--dim); }}
.ders p + p {{ margin-top: 9px; }}
.ders b {{ color: var(--ink); }}
.ders .karar {{ margin-top: 11px; padding-top: 10px; border-top: 1px solid var(--line); font-size: 13px; }}
.ders .karar b {{ color: var(--primary); }}

td.yok {{ color: var(--warn); font-style: italic; }}

/* iki kupon */
.ik {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 14px; margin-bottom: 22px; }}
.ik > div {{ border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; background: var(--card); border-top: 3px solid var(--line2); }}
.ik .sen {{ border-top-color: var(--s2); }}
.ik .kur {{ border-top-color: var(--s1); }}
.ik h4 {{ margin: 0 0 3px; font: 600 14px sans-serif; }}
.ik .skor {{ font-size: 32px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.1; }}
.ik .skor span {{ font-size: 14px; color: var(--dim); font-weight: 400; }}
.ik dl {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin: 13px 0 0; }}
.ik dt {{ font: 600 9.5px/1 sans-serif; letter-spacing: .09em; text-transform: uppercase; color: var(--dim); }}
.ik dd {{ margin: 3px 0 0; font-size: 15px; font-weight: 600; font-variant-numeric: tabular-nums; }}
td.iki-a, td.iki-b {{ width: 96px; }}
tr.ikisi-de td {{ background: var(--danger-soft); }}
.rozet-k {{ display: inline-block; font: 600 9.5px/1 sans-serif; letter-spacing: .08em; padding: 3px 6px; border-radius: 5px; background: var(--muted); color: var(--dim); }}

/* gerekçe */
.kural {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin-bottom: 30px; }}
.kural > div {{ border: 1px solid var(--line); border-radius: 14px; padding: 15px 16px; background: var(--card); border-top: 3px solid var(--line2); }}
.kural .kb {{ border-top-color: var(--s1); }}
.kural .kc {{ border-top-color: var(--s0); }}
.kural .ku {{ border-top-color: var(--s2); }}
.kural h4 {{ margin: 0 0 4px; font: 600 13px sans-serif; }}
.kural .adet {{ font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.1; }}
.kural .adet span {{ font-size: 12px; font-weight: 400; color: var(--dim); }}
.kural p {{ font-size: 12.5px; color: var(--dim); margin-top: 7px; }}
.kural code {{ font-size: 11.5px; background: var(--muted); padding: 1px 5px; border-radius: 4px; }}

.gerekceler {{ display: grid; gap: 12px; }}
.ger {{ border: 1px solid var(--line); border-left: 3px solid var(--line2); border-radius: 0 14px 14px 0; padding: 15px 18px; background: var(--card); }}
.ger.banko {{ border-left-color: var(--s1); }}
.ger.cifte {{ border-left-color: var(--s0); }}
.ger.uclu {{ border-left-color: var(--s2); }}
.ger > header {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 9px; padding: 0; border: 0; }}
.ger-no {{ display: inline-grid; place-items: center; width: 24px; height: 24px; border-radius: 7px; background: var(--muted); color: var(--dim); font: 600 12px ui-monospace, Menlo, monospace; }}
.ger h3 {{ font-size: 16px; flex: 1 1 auto; min-width: 150px; }}
.ger-karar {{ font: 600 9.5px/1 sans-serif; letter-spacing: .12em; padding: 4px 8px; border-radius: 6px; background: var(--muted); color: var(--dim); }}
.ger.banko .ger-karar {{ background: var(--accent); color: var(--primary); }}
.ger ul {{ margin: 0; padding-left: 17px; display: flex; flex-direction: column; gap: 6px; }}
.ger li {{ font-size: 13px; line-height: 1.55; color: var(--dim); }}
.ger li b {{ color: var(--ink); }}
.ger li b.risk {{ color: var(--warn); }}
.ger li b.ok {{ color: var(--ok); }}
.ger li b.kal {{ color: var(--s2); }}
td.risk-n {{ color: var(--warn); font-weight: 600; }}
.anatomi {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }}
.anatomi div {{ border: 1px solid var(--line); border-radius: 14px; padding: 15px 16px; background: var(--elev); font-size: 13px; color: var(--dim); }}
.anatomi h4 {{ margin: 0 0 6px; font: 600 13px sans-serif; color: var(--ink); }}
.anatomi b {{ color: var(--ink); }}

/* not */
.not {{ border-left: 3px solid var(--warn); background: var(--warn-soft); padding: 14px 18px; border-radius: 0 12px 12px 0; font-size: 13.5px; }}
.not h3 {{ font-size: 15px; margin-bottom: 5px; }}
.notlar {{ display: flex; flex-direction: column; gap: 12px; }}
.notlar li {{ font-size: 13.5px; color: var(--dim); }}
.notlar b {{ color: var(--ink); }}
footer {{ margin-top: 64px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--dim); font-size: 12px; }}
@media (max-width: 640px) {{
  .ayr li {{ grid-template-columns: 1fr auto; }}
  .ay-bar {{ grid-column: 1 / -1; }}
  .ay-num {{ grid-column: 1 / -1; text-align: left; }}
}}
</style>
</head>
<body>

<div class="wrap">
  <header class="hero">
    <span class="eyebrow">Süper Toto 2026/2027 · işlenen sezon</span>
    <h1>{_a.hafta}. Hafta</h1>
    <p class="prog">{e(PROGRAM)} · 15 maç · {e(FIYAT_ADI)} ve tek platform oynanma yüzdeleriyle</p>
    <div class="rozetler">
      <span class="rozet mor">2026/2027</span>
      <span class="rozet">{e(FIYAT_ADI)}</span>
      <span class="rozet">oynanma yüzdesi</span>
      {'<span class="rozet uyari">SONUÇ: en iyi kolon ' + str(degerlendirme["best"]) + '/15 — ' + ROZET_KADEME + '</span>' if BITTI else '<span class="rozet uyari">sonuçlar YOK — bu rapor sonuçlar görülmeden yazıldı</span>'}
      {'<span class="rozet">kupon sonuçlar görülmeden donduruldu</span>' if BITTI else ''}
    </div>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">Bahisçi marjı</div><div class="v">%{prof['avg_margin_pct']:.1f}</div><div class="a">geçen sezon arşivi %{o['avg_margin_pct']:.2f} — {prof['avg_margin_pct']/o['avg_margin_pct']:.2f}× {'daha yüksek' if prof['avg_margin_pct'] > o['avg_margin_pct'] else 'daha düşük'}</div></div>
    <div class="stat"><div class="k">Beklenen 1 / 0 / 2</div><div class="v">{prof['expected']['1']:.1f} · {prof['expected']['0']:.1f} · {prof['expected']['2']:.1f}</div><div class="a">geçen sezon ort. {wa['1']:.1f} · {wa['0']:.1f} · {wa['2']:.1f}</div></div>
    <div class="stat"><div class="k">Favori tutar</div><div class="v">{prof['fav_expected_market']:.1f}–{prof['fav_expected_history']:.1f}</div><div class="a">piyasa – geçen sezon bantları · sezon ort. {15*o['favourite_hit_pct']/100:.1f}</div></div>
    <div class="stat"><div class="k">Küme-içi</div><div class="v">%{100*ana['in_set_p']:.2f}</div><div class="a">≈ 1/{ana['in_set_1_in']:.0f} — 14-garantinin geçerlilik koşulu</div></div>
    <div class="stat"><div class="k">Kalabalık oranı</div><div class="v">{ana['crowd_ratio']:.2f}</div><div class="a">1'in altı: seçim kümem olasılığına göre fazla oynanmış</div></div>
  </div>

  {sonuc_bolumu}

  <section>
    <header>
      <span class="eyebrow">Ölçüm · geçen sezonun kendi tabloları</span>
      <h2>Maç maç</h2>
      <p>Her satırda üç sayı üst üste: kalın olan <b>oynanma yüzdesi</b>, altındaki <b>marj arındırılmış piyasa olasılığı</b>, en altta ikisinin farkı. Sarı hücre, halkın piyasadan en az 6 puan fazla oynadığı seçenektir. Sağdaki bant, favorinin oranının geçen sezon 567 maçta ölçülen isabetidir.</p>
    </header>
    <div class="scroll">
      <table>
        <thead><tr>
          <th>#</th><th>Maç</th><th class="num">Oran<br>1/0/2</th>
          <th class="num">1<br><span class="sub">halk/piyasa</span></th>
          <th class="num">0<br><span class="sub">halk/piyasa</span></th>
          <th class="num">2<br><span class="sub">halk/piyasa</span></th>
          <th>Favori bandı<br><span class="sub">geçen sezon isabeti</span></th>
          <th>İşaretim</th>
        </tr></thead>
        <tbody>{''.join(mac_satir)}</tbody>
      </table>
    </div>
  </section>

  <section>
    <header>
      <span class="eyebrow">Karşılaştırma · 41 hafta, 615 maç</span>
      <h2>Bu hafta ↔ geçen sezon</h2>
      <p>Soldaki sütun bu haftanın oranlarından, sağdaki 2025/2026 sezonunun gerçekleşmiş kaydından gelir. Hiçbiri tahmin değildir: ikisi de ölçülmüş sayılardır ve aralarındaki fark, bu haftanın sıradışı olup olmadığını söyler.</p>
    </header>
    <div class="scroll">
      <table>
        <thead><tr><th>Ölçü</th><th class="num">Bu hafta</th><th class="num">Geçen sezon</th><th>Not</th></tr></thead>
        <tbody>
          <tr><td>Beklenen "1"</td><td class="num mono">{prof['expected']['1']:.2f}</td><td class="num mono">{wa['1']:.2f}</td><td class="band">haftalık ortalama</td></tr>
          <tr><td>Beklenen "0"</td><td class="num mono">{prof['expected']['0']:.2f}</td><td class="num mono">{wa['0']:.2f}</td><td class="band">beraberlik bütçesi</td></tr>
          <tr><td>Beklenen "2"</td><td class="num mono">{prof['expected']['2']:.2f}</td><td class="num mono">{wa['2']:.2f}</td><td class="band">deplasman</td></tr>
          <tr><td>Favori dağılımı (1/0/2)</td><td class="num mono">{prof['fav_split']['1']} / 0 / {prof['fav_split']['2']}</td><td class="num mono">%{100*o['favourite_split']['1']/o['with_odds']:.0f} / 0 / %{100*o['favourite_split']['2']/o['with_odds']:.0f}</td><td class="band">beraberlik hiçbir maçta favori olmaz</td></tr>
          <tr><td>Favori kaç maçta tutar</td><td class="num mono">{prof['fav_expected_market']:.2f} – {prof['fav_expected_history']:.2f}</td><td class="num mono">{15*o['favourite_hit_pct']/100:.2f}</td><td class="band">piyasa – geçen sezon bantları</td></tr>
          <tr><td>İlk iki sembol kapsar</td><td class="num mono">{prof['double_expected_market']:.2f} – {prof['double_expected_history']:.2f}</td><td class="num mono">—</td><td class="band">çift işaretin karşılığı</td></tr>
          <tr><td>Beraberlik (profil tablosu)</td><td class="num mono">{prof['draw_expected_history']:.2f}</td><td class="num mono">{wa['0']:.2f}</td><td class="band">favori–ikinci farkına göre</td></tr>
          <tr><td>Bahisçi marjı</td><td class="num mono">%{prof['avg_margin_pct']:.2f}</td><td class="num mono">%{o['avg_margin_pct']:.2f}</td><td class="band">{e(_saglayici)} ↔ football-data kapanış</td></tr>
        </tbody>
      </table>
    </div>

    <h3 style="margin-top:28px;margin-bottom:12px">Lig kırılımı</h3>
    <div class="scroll">
      <table>
        <thead><tr><th>Lig</th><th class="num">Bu hafta</th><th class="num">Geçen sezon /hafta</th><th class="num">Beraberlik</th><th class="num">Favori isabeti</th></tr></thead>
        <tbody>{''.join(lig_satir)}</tbody>
      </table>
    </div>
  </section>

  {f'''
  <section>
    <header>
      <span class="eyebrow">Yeni boyut · ilk kez üç bahisçi, iki an</span>
      <h2>Fiyat kimin fiyatı?</h2>
      <p>Önceki iki hafta tek bir bültenin tek bir anını taşıyordu. Bu hafta üç bahisçinin hem açılış hem kapanış çizgisi kayıtta. Aşağıdaki her hücre <b>marj arındırılmış olasılıktır</b>, ham oran değil: ham oranın hareketi, piyasanın fikir değiştirmesiyle bahisçinin marjını değiştirmesini karıştırırdı. Ortalama marj — {marj_rozet}.</p>
    </header>
    <div class="scroll">
      <table>
        <thead><tr><th class="num">#</th><th>Maç</th>{fiyat_baslik}<th class="num">Hareket</th><th class="num">Ayrışma</th></tr></thead>
        <tbody>{''.join(fiyat_satir)}</tbody>
      </table>
    </div>
    <ul class="notlar" style="list-style:disc;padding-left:20px;gap:8px;margin-top:16px">
      <li><b>Ana fiyat neden {e(FIYAT_ADI)}?</b> Seçim iddia değil ölçüm: <code>scripts/acilis_kapanis.py</code> geçen sezon arşivinde kapanışı açılışın önünde ölçtü (Brier %0,27 daha iyi; yedi hareket bandının beşinde gerçekleşme kapanışı takip etti; kural kapanışla beslenince 36 haftanın 36'sında ≥12 ve hafta başına 2.051 kolon, açılışta 2.664). Bahisçi tarafında ise en düşük marj seçildi.</li>
      <li><b>En büyük hareket:</b> {_EN_HAREKET["no"]}. maç ({e(_EN_HAREKET["ad"])}) — <b>{_EN_HAREKET["hareket_sembol"]}</b> sembolü {100*_EN_HAREKET["hareket"]:+.1f} puan. Para bu maça geldi ve arşiv, bu büyüklükteki hareketlerde <b>kapanışın haklı çıktığını</b> ölçüyor.</li>
      {'<li><b>Bayat kapanış.</b> Şu satırlarda kapanış oranı açılışla BİREBİR aynı — ' + '; '.join(BAYAT) + '. Bunlar fiyat değil, tazelenmemiş kayıttır: o maçlarda o bahisçinin kapanışı bilgi taşımıyor ve ayrışma sütununda görünen fark görüş farkı değil, kayıt farkıdır.</li>' if BAYAT else ''}
      <li><b>Ayrışma nerede yoğunlaşıyor?</b> En büyüğü {_EN_AYRISMA["no"]}. maçta ({e(_EN_AYRISMA["ad"])}) {100*_EN_AYRISMA["ayrisma"]:.1f} puan. Ayrışmanın büyük olduğu satırlarda önce yukarıdaki bayatlık listesine bakılmalı: iki bahisçi farklı düşünüyor olabilir, ya da biri saatler önce durmuş olabilir.</li>
    </ul>
  </section>''' if FIYAT_VAR else ''}

  <section>
    <header>
      <span class="eyebrow">Yeni boyut · geçen sezonda karşılığı yok</span>
      <h2>Kalabalık nerede toplanmış</h2>
      <p>Spor Toto müşterek bahistir: ikramiye kazananlara bölünür. Yani aynı olasılıktaki iki sonuçtan <b>az oynananı</b> işaretlemek, tutturma olasılığını değiştirmeden alınacak payı büyütür. Bu, piyasayı tahminde yenmeyi gerektirmeyen tek kaldıraçtır — ve geçen sezon verisinde ölçülemiyordu. Aşağıdakiler halkın piyasadan en çok ayrıştığı altı seçenek.</p>
    </header>
    <ul class="ayr">{''.join(ayr_html)}</ul>
    <p style="margin-top:16px;font-size:13px;color:var(--dim)">
      Toplamda halk favorilere piyasanın verdiğinden ortalama <b style="color:var(--ink)">{100*kam['avg_fav_diff']:+.1f} puan</b> fazla oynamış;
      {kam['consensus_70']} maçta %70'in üzerinde mutabakat var. Sembol başına toplam pay:
      "1" halk {kam['totals']['play']['1']:.2f} ↔ piyasa {kam['totals']['market']['1']:.2f} ·
      "0" halk {kam['totals']['play']['0']:.2f} ↔ piyasa {kam['totals']['market']['0']:.2f} ·
      "2" halk {kam['totals']['play']['2']:.2f} ↔ piyasa {kam['totals']['market']['2']:.2f}.
      Beraberlik <b style="color:var(--ink)">aggregate olarak az oynanmamış</b> — sapma tek tek favorilerde toplanıyor.
    </p>
  </section>

  <section>
    <header>
      <span class="eyebrow">Çıktı · sonuçlar görülmeden donduruldu</span>
      <h2>Kupon</h2>
      <p>{'İşaret seçimi verilen bütçede doğrudan <b>P(en iyi kolon ≥ 12)</b>&#39;yi enbüyükler; eşiğe bakmaz. ' + ('Bu haftanın oynanma yüzdeleri işaret <b>sayılarını</b> değiştirmeden hangi sembol sorusunu yeniden sordu — dondurulan kupon aşağıda, bu ızgaranın altında.' if DONMUS else 'Bu haftanın oynanma yüzdeleri işaret seçimine <b>girmemiştir</b>; yukarıdaki kalabalık ölçüsü yalnızca sonucu okumak için hesaplandı.') if KUPON_JSON.get('meta', {}).get('strategy', {}).get('kural', '').startswith('hedef') else 'İşaret seçimi <b>yalnızca</b> 2025/2026 geri testinin varsayılan eşiğinden gelir: favori olasılığı ≥%68 ise banko, &lt;%38 ise üçlü, arası çifte. Bu haftanın oynanma yüzdeleri işaret seçimine <b>girmemiştir</b> — yukarıdaki kalabalık ölçüsü yalnızca sonucu okumak için hesaplandı.'} 16 satır, 14 doğru garantili; garanti koşulludur: ancak gerçek sonuç seçim kümesinin içindeyse geçerlidir.</p>
    </header>
    <div class="scroll">
      <table class="grid-kupon">
        <thead><tr><th></th>{''.join(f'<th>{i}</th>' for i in range(1, 16))}</tr></thead>
        <tbody>{''.join(grid_rows)}</tbody>
      </table>
    </div>
    <div class="varyantlar">
      {varyant(ana_v, "Ana — kural birebir", True)}
      {varyant(mer[512], "Bütçeli")}
      {varyant(mer[256], "Kısıtlı")}
    </div>
    <p style="margin-top:14px;font-size:12.5px;color:var(--dim)">Yukarıdaki 16 satırlık ızgara <b style="color:var(--ink)">ana</b> sürümündür. Bütçeli ve kısıtlı sürümlerin satırları da aynı motorla üretildi ve repoda <code>hafta_{_a.hafta:02d}_kupon.json</code> içinde duruyor.</p>
  </section>

  {f'''
  <section>
    <header>
      <span class="eyebrow">Oynanan kayıt · {e(KUPON_JSON["meta"].get("frozen_at", ""))} tarihinde donduruldu</span>
      <h2>Dondurulan kupon</h2>
      <p>Yukarıdaki ızgara kuralın kalabalığı <b>görmeden</b> verdiği cevaptır. Oynanan kupon ondan farklı: müşterek bahiste kazanç isabetten değil, <b>isabeti kaç kişiyle paylaştığından</b> doğar. Kalabalık ayarı işaret <b>sayılarını</b> aynen korur (yani bedel değişmez) ve yalnızca hangi sembol sorusunu yeniden sorar.</p>
    </header>
    <div class="var-picks" style="margin-bottom:18px">{''.join(f'<span class="vp">{i+1}<em>{p}</em></span>' for i, p in enumerate(DONMUS["picks"]))}</div>
    <div class="scroll">
      <table>
        <thead><tr><th>Kupon</th><th class="num">P(≥12)</th><th class="num">Kolon</th><th class="num">Küme-içi</th><th class="num">Aynı seti oynayan halk</th><th class="num">Oran</th></tr></thead>
        <tbody>{''.join(donmus_satir)}</tbody>
      </table>
    </div>
    <p style="margin-top:16px;font-size:13.5px;color:var(--dim);max-width:74ch">{e(KUPON_JSON["meta"].get("kalabalik_gerekcesi", ""))}</p>
    {'<p style="margin-top:14px;font-size:13px;color:var(--dim);max-width:74ch"><b style="color:var(--ink)">Fiyat duyarlılığı.</b> ' + e(DUYARLILIK["not"]) + " " + e(DUYARLILIK["fark"]) + '</p>' if DUYARLILIK else ''}
    <div class="scroll" style="margin-top:20px">
      <table class="grid-kupon">
        <thead><tr><th></th>{''.join(f'<th>{i}</th>' for i in range(1, 16))}</tr></thead>
        <tbody>{''.join(donmus_grid)}</tbody>
      </table>
    </div>
    <p style="margin-top:12px;font-size:12.5px;color:var(--dim)">Oynanacak 16 satır — dondurulan kupona ait. Motor aynı (<code>solve_fix16</code> + <code>merge_rows</code>), 14-garanti aynı koşulla duruyor.</p>
  </section>''' if DONMUS else ''}

  <section>
    <header>
      <span class="eyebrow">Gerekçe · her işaretin sebebi</span>
      <h2>Neden bu işaretler?</h2>
      <p>Kupondaki hiçbir işaret sezgiyle konmadı. Tek bir kural var ve her maça aynı uygulanıyor: <b>maçın favori olasılığı</b> hangi aralığa düşüyorsa işaret sayısı odur. Eşikler bu haftadan değil, geçen sezonun 36 haftalık geri testinden gelir.</p>
    </header>

    <div class="kural">
      <div class="kb">
        <h4>Banko — tek işaret</h4>
        <div class="adet">{sayilar['banko']} <span>maç</span></div>
        <p>Favori olasılığı <code>≥ %68</code>. Bu sayı ölçümden geldi: geçen sezon favori oranı 1.35'in altına inince isabet %64'ün üstüne çıkıyordu, marj arındırılmış karşılığı ~0,68. <b>Yanlışsa kupon tamamen ölür.</b></p>
      </div>
      <div class="kc">
        <h4>Çifte — iki işaret</h4>
        <div class="adet">{sayilar['cift']} <span>maç</span></div>
        <p>Arada kalan her maç. En olası iki sembol işaretlenir; üçüncüsü feda edilir. Geçen sezon ilk iki sembol, maçların <b>%77–87</b>'sini gerçekten kapsadı (bant başına değişir).</p>
      </div>
      <div class="ku">
        <h4>Üçlü — üç işaret</h4>
        <div class="adet">{sayilar['uclu']} <span>maç</span></div>
        <p>Favori olasılığı <code>&lt; %38</code>. Piyasanın kendisinin karar veremediği maç. Kapatmak kolonu 3'e katlar ama o maçtan <b>asla</b> hata gelmez.</p>
      </div>
    </div>

    <div class="gerekceler">{ger_html}</div>

    <h3 style="margin:36px 0 6px">Risk nerede toplanıyor</h3>
    <p style="font-size:13.5px;color:var(--dim);max-width:68ch;margin-bottom:14px">Kuponun ayakta kalması, <b style="color:var(--ink)">15 maçın hepsinde</b> sonucun işaretlerimin içinde olmasına bağlı. Aşağıdaki tablo en kırılgan maçtan başlar — bir maçın "dışarıda" sütunu, tek başına kuponu bitirme olasılığıdır. Çarpımları küme-içi olasılığını verir: <b style="color:var(--ink)">%{100*ana['in_set_p']:.2f}</b>.</p>
    <div class="scroll">
      <table>
        <thead><tr><th>#</th><th>Maç</th><th>İşaret</th><th class="num">İçinde</th><th class="num">Dışarıda</th></tr></thead>
        <tbody>{risk_html}</tbody>
      </table>
    </div>

    <h3 style="margin:36px 0 14px">16 satır nereden çıkıyor</h3>
    <div class="anatomi">
      <div>
        <h4>Hata bütçesi — {len(blok_maclar)} maç</h4>
        <p>Maç <b>{', '.join(str(x) for x in blok_maclar)}</b>. Bu yedi çiftin 128 ihtimali, Hamming(7,4) koduyla <b>16 satıra</b> sığdırılır. Kod, bu yedi maçta <b>en fazla 1 hatayı</b> affeder — 14-garanti tam olarak buradan gelir. Kanıtlanmış optimaldir: 16'dan az satırla olmaz.</p>
      </div>
      <div>
        <h4>Tam oynanan — {len(ekstra_maclar)} maç</h4>
        <p>Maç <b>{', '.join(str(x) for x in ekstra_maclar)}</b>. Bunların bütün ihtimalleri her satırda oynanır, yani buradan <b>hata gelmez</b>. Bedeli çarpan olarak öderiz — maç sırasına göre {ekstra_carpim} = {ekstra_toplam}.</p>
      </div>
      <div>
        <h4>Toplam bedel</h4>
        <p><b>16 satır × {ekstra_toplam} = {tr(ana['columns'])} kolon.</b> Seçim uzayının tamamı {tr(ana['space'])} kolondu; Hamming bloğu bunu <b>8 kat</b> ucuzlatıyor ve 14-garantiyi koruyor. Bankolar bedele girmez — ama karşılığında hata payı da tanımazlar.</p>
      </div>
    </div>

    <h3 style="margin:36px 0 6px">Kalabalık verisini neden kullanmadım</h3>
    <p style="font-size:13.5px;color:var(--dim);max-width:68ch">Oynanma yüzdeleri elimde ve yukarıda ölçtüm — ama <b style="color:var(--ink)">işaret seçimine sokmadım</b>. Sebep, bu kuponun ne olduğuyla ilgili: bu, geçen sezon verisinden çıkan kuralın kör bir sınavı. Kalabalığa göre işaret oynatsaydım, sonuç geldiğinde "kural mı tuttu, sezgim mi tuttu" ayırt edilemezdi.<br><br>Kalabalık verisinin asıl işi zaten farklı: <b style="color:var(--ink)">tutturma olasılığını değil, tutturunca alınacak payı</b> değiştirir. Onu ölçmek için ikramiye/havuz verisi gerekiyor. {'O veri artık elimizde — ve aşağıdaki 5. ve 6. ders tam olarak ne söylediğini yazıyor: kalabalık yönü piyasadan alıyor, dolayısıyla kural için bir sinyal taşımıyor; taşıdığı şey payın büyüklüğü.' if BITTI else 'O veri ilk kez bu hafta gelecek. Payı hesaplayabildiğimiz an, seçim kuralına ikinci bir terim eklemek meşru olur — daha önce değil.'}</p>
  </section>

  {iki_kupon_bolumu}

  {dersler_bolumu}

  <section>
    <header>
      <span class="eyebrow">Sınırlar</span>
      <h2>{'Baştan yazılmış olan sınırlar' if BITTI else 'Bu kupon neyi vaat etmiyor'}</h2>
    </header>
    <div class="notlar">
      <div class="not">
        <h3>Geçen sezonun hold-out sonucu: 36 haftada 0 isabet</h3>
        <p>Aynı strateji 2025/2026'da eşik taramasıyla 36 haftanın 3'ünde 14 tutturdu (%8,3). Ama eşik o haftayı <b>görmeden</b> seçildiğinde isabet <b>0/36</b> (%0, güven aralığı %0–9,6). Karara esas alınacak sayı budur. Bu araç maç sonucu tahmin etmez; tahmini garantiye alır.</p>
      </div>
      <ul class="notlar" style="list-style:disc;padding-left:20px;gap:8px">
        <li><b>Marj farkı ölçek bozar.</b> Eşikler football-data kapanış oranlarıyla (%{o['avg_margin_pct']:.2f} marj) kalibre edildi; bu haftanın {e(_saglayici)} oranlarında marj %{prof['avg_margin_pct']:.1f} — {MARJ_YONU}</li>
        <li><b>{'Kupon kalabalıkla aynı yöne bakıyor' if ana['crowd_ratio'] < 1 else 'Kupon kalabalıktan sapıyor'}.</b> Seçim kümesinin kalabalık oranı {ana['crowd_ratio']:.2f} ({'1&#39;in altı: tutarsa ikramiye çok bölünür' if ana['crowd_ratio'] < 1 else '1&#39;in üstü: tutarsa ikramiye az bölünür'}). En kalabalık işaretlerim: {KALABALIK_UC}.</li>
        <li><b>Veri boşlukları.</b> {UYARI_OZETI} {'İkramiye kaydı bu hafta için girildi.' if BITTI else 'Ve bu haftanın ikramiye/havuz verisi henüz yok — geldiğinde kalabalık ölçüsü vekil olmaktan çıkıp gerçek paya dönüşecek.'}</li>
      </ul>
    </div>
  </section>

  <footer>
    Veri elle girildi ({e(d['meta']['entered_at'])}), kaynağı dosyasında yazılı. Analiz projenin kendi modülleriyle üretildi
    (<code>odds</code>, <code>backtest</code>, <code>core</code>) — geçen sezon arşivi yalnızca <b>okundu</b>, değiştirilmedi.
    Kupon sonuçlar görülmeden donduruldu ve commit'lendi.
  </footer>
</div>
</body>
</html>
"""
# Dosya yazma YALNIZCA dogrudan calistirilirken. Once modul duzeyindeydi:
# bu dosyayi import etmek diske HTML yaziyordu. Dizindeki her script'in
# guard'i vardi, bunun yoktu.
if __name__ == "__main__":
    cikti = Path(_a.cikti) if _a.cikti else (
        KOK / "data" / "super_toto" / _a.sezon / f"hafta_{_a.hafta:02d}.html")
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(HTML, encoding="utf-8")
    print(f"yazıldı: {cikti} ({len(HTML):,} bayt)")
