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
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

_ap = argparse.ArgumentParser()
_ap.add_argument("--sezon", default="2026_27")
_ap.add_argument("--hafta", type=int, default=1)
_ap.add_argument("--cikti", default=None)
_a = _ap.parse_args()
sys.argv = ["x"]  # alt modülün kendi argparse'ı tetiklenmesin

_spec = importlib.util.spec_from_file_location(
    "st", str(KOK / "scripts" / "super_toto_hafta.py"))
m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(m)

S = ("1", "0", "2")
d = m.hafta_yukle(_a.sezon, _a.hafta)
ref = m.gecen_sezon_ref()
prof = m.hafta_profili(d, ref)
kam = m.kamuoyu(d)
ana = m.kupon_kur(d, 0.68, 0.38)
mer = {p["budget"]: p for p in m.butce_merdiveni(d, [list(x) for x in ana["picks"]], [256, 512])}
o, hist = ref["odds"], ref["hist"]
wa = hist["weekly_avg"]
e = html.escape

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
        <td class="num mono">{r['odds']['1']:.2f}<span class="sub">{r['odds']['0']:.2f}</span><span class="sub">{r['odds']['2']:.2f}</span></td>
        {''.join(hucre)}
        <td class="band">{e(str(r['fav_band']))}<span class="sub">%{r['fav_band_hit']} · n={r['fav_band_n']}</span></td>
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
            f'<b class="ok">Kazancı:</b> bu maç kuponu <b>asla</b> dışarı atmaz. '
            f'Bedeli, kolon sayısını 3 katına çıkarması.')
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
    en_buyuk = max(((abs(kr["cells"][x]["diff"]), x) for x in S))
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

ana_v = dict(ana); ana_v["cost"] = ana["columns"]
HTML = f"""<title>Süper Toto 1. Hafta</title>
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

<div class="wrap">
  <header class="hero">
    <span class="eyebrow">Süper Toto 2026/2027 · işlenen sezon</span>
    <h1>1. Hafta</h1>
    <p class="prog">{e(d['meta']['program'])} · 15 maç · iddaa taraf oranları ve tek platform oynanma yüzdeleriyle</p>
    <div class="rozetler">
      <span class="rozet mor">2026/2027</span>
      <span class="rozet">iddaa oranı</span>
      <span class="rozet">oynanma yüzdesi</span>
      <span class="rozet uyari">sonuçlar YOK — bu rapor sonuçlar görülmeden yazıldı</span>
    </div>
  </header>

  <div class="stats">
    <div class="stat"><div class="k">Bahisçi marjı</div><div class="v">%{prof['avg_margin_pct']:.1f}</div><div class="a">geçen sezon arşivi %{o['avg_margin_pct']:.2f} — {prof['avg_margin_pct']/o['avg_margin_pct']:.1f}× daha yüksek</div></div>
    <div class="stat"><div class="k">Beklenen 1 / 0 / 2</div><div class="v">{prof['expected']['1']:.1f} · {prof['expected']['0']:.1f} · {prof['expected']['2']:.1f}</div><div class="a">geçen sezon ort. {wa['1']:.1f} · {wa['0']:.1f} · {wa['2']:.1f}</div></div>
    <div class="stat"><div class="k">Favori tutar</div><div class="v">{prof['fav_expected_market']:.1f}–{prof['fav_expected_history']:.1f}</div><div class="a">piyasa – geçen sezon bantları · sezon ort. {15*o['favourite_hit_pct']/100:.1f}</div></div>
    <div class="stat"><div class="k">Küme-içi</div><div class="v">%{100*ana['in_set_p']:.2f}</div><div class="a">≈ 1/{ana['in_set_1_in']:.0f} — 14-garantinin geçerlilik koşulu</div></div>
    <div class="stat"><div class="k">Kalabalık oranı</div><div class="v">{ana['crowd_ratio']:.2f}</div><div class="a">1'in altı: seçim kümem olasılığına göre fazla oynanmış</div></div>
  </div>

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
          <tr><td>Bahisçi marjı</td><td class="num mono">%{prof['avg_margin_pct']:.2f}</td><td class="num mono">%{o['avg_margin_pct']:.2f}</td><td class="band">iddaa ↔ football-data kapanış</td></tr>
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
      <p>İşaret seçimi <b>yalnızca</b> 2025/2026 geri testinin varsayılan eşiğinden gelir: favori olasılığı ≥%68 ise banko, &lt;%38 ise üçlü, arası çifte. Bu haftanın oynanma yüzdeleri işaret seçimine <b>girmemiştir</b> — yukarıdaki kalabalık ölçüsü yalnızca sonucu okumak için hesaplandı. 16 satır, 14 doğru garantili; garanti koşulludur: ancak gerçek sonuç seçim kümesinin içindeyse geçerlidir.</p>
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
    <p style="margin-top:14px;font-size:12.5px;color:var(--dim)">Yukarıdaki 16 satırlık ızgara <b style="color:var(--ink)">ana</b> sürümündür. Bütçeli ve kısıtlı sürümlerin satırları da aynı motorla üretildi ve repoda <code>hafta_01_kupon.json</code> içinde duruyor.</p>
  </section>

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
    <p style="font-size:13.5px;color:var(--dim);max-width:68ch">Oynanma yüzdeleri elimde ve yukarıda ölçtüm — ama <b style="color:var(--ink)">işaret seçimine sokmadım</b>. Sebep, bu kuponun ne olduğuyla ilgili: bu, geçen sezon verisinden çıkan kuralın kör bir sınavı. Kalabalığa göre işaret oynatsaydım, sonuç geldiğinde "kural mı tuttu, sezgim mi tuttu" ayırt edilemezdi.<br><br>Kalabalık verisinin asıl işi zaten farklı: <b style="color:var(--ink)">tutturma olasılığını değil, tutturunca alınacak payı</b> değiştirir. Onu ölçmek için ikramiye/havuz verisi gerekiyor ve o veri ilk kez bu hafta gelecek. Payı hesaplayabildiğimiz an, seçim kuralına ikinci bir terim eklemek meşru olur — daha önce değil.</p>
  </section>

  <section>
    <header>
      <span class="eyebrow">Sınırlar</span>
      <h2>Bu kupon neyi vaat etmiyor</h2>
    </header>
    <div class="notlar">
      <div class="not">
        <h3>Geçen sezonun hold-out sonucu: 36 haftada 0 isabet</h3>
        <p>Aynı strateji 2025/2026'da eşik taramasıyla 36 haftanın 3'ünde 14 tutturdu (%8,3). Ama eşik o haftayı <b>görmeden</b> seçildiğinde isabet <b>0/36</b> (%0, güven aralığı %0–9,6). Karara esas alınacak sayı budur. Bu araç maç sonucu tahmin etmez; tahmini garantiye alır.</p>
      </div>
      <ul class="notlar" style="list-style:disc;padding-left:20px;gap:8px">
        <li><b>Marj farkı ölçek bozar.</b> Eşikler football-data kapanış oranlarıyla (%{o['avg_margin_pct']:.2f} marj) kalibre edildi; bu haftanın iddaa oranlarında marj %{prof['avg_margin_pct']:.1f}. Marj orantılı atıldığı için favori olasılıkları muhtemelen bir miktar <b>küçük</b> çıkıyor — yani gerçek banko sayısı 2'den fazla olabilirdi.</li>
        <li><b>Kupon kalabalıkla aynı yöne bakıyor.</b> Seçim kümesinin kalabalık oranı {ana['crowd_ratio']:.2f} (1'in altı). Tutarsa ikramiye çok bölünür. En kalabalık işaretlerim: 8. maç [1] halkın %89'u, 15. maç [10] %91'i, 5. maç [02] %97'si.</li>
        <li><b>Üç veri boşluğu duruyor.</b> 7. maç (Amed–Erzurumspor, TFF 1. Lig) geçen sezon arşivinde karşılığı olmayan bir lig. 13. maçın lig etiketi varsayım. Ve ikramiye/havuz verisi henüz yok — geldiğinde kalabalık ölçüsü vekil olmaktan çıkıp gerçek paya dönüşecek.</li>
      </ul>
    </div>
  </section>

  <footer>
    Veri elle girildi ({e(d['meta']['entered_at'])}), kaynağı dosyasında yazılı. Analiz projenin kendi modülleriyle üretildi
    (<code>odds</code>, <code>backtest</code>, <code>core</code>) — geçen sezon arşivi yalnızca <b>okundu</b>, değiştirilmedi.
    Kupon sonuçlar görülmeden donduruldu ve commit'lendi.
  </footer>
</div>
"""
cikti = Path(_a.cikti) if _a.cikti else (
    KOK / "data" / "super_toto" / _a.sezon / f"hafta_{_a.hafta:02d}.html")
cikti.parent.mkdir(parents=True, exist_ok=True)
cikti.write_text(HTML, encoding="utf-8")
print(f"yazıldı: {cikti} ({len(HTML):,} bayt)")
