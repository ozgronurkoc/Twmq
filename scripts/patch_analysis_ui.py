"""Analiz bolumlerini ayri kartlara ayir: Exact, MC, Bayes, Dirichlet, Markov."""
from pathlib import Path

p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")
css = Path("scripts/analysis_sections.css").read_text(encoding="utf-8")
frag = Path("scripts/analysis_sections_fragment.html").read_text(encoding="utf-8")

if 'id="sec-exact"' in t and 'id="sec-markov"' in t:
    print("analiz kartlari zaten var")
else:
    if ".analysis-card" not in t:
        t = t.replace("  </style>", css + "\n  </style>", 1)
    start = t.find("{% if result.advanced %}")
    end = t.find("{% if result.notlar %}")
    if start > 0 and end > start and 'id="sec-exact"' not in t[start:end]:
        t = t[:start] + "\n        " + t[end:]
    if 'id="sec-exact"' not in t:
        ins = t.find("{% if result.error_freq %}")
        if ins < 0:
            ins = t.find("Kapsama Dağılımı")
            if ins > 0:
                ins = t.rfind("<div class=\"card\"", 0, ins)
        if ins < 0:
            raise SystemExit("insert noktasi yok")
        t = t[:ins] + frag + t[ins:]
    t = t.replace(
        '<div class="card-title" style="margin:0">Uniform Dağılım</div>',
        '<div class="card-title" style="margin:0" id="sec-uniform">Uniform Dağılım <span class="analysis-badge badge-uniform">KOMBİNATORİK</span></div>',
        1,
    )
    t = t.replace("Bayes güncelle (Dirichlet)", "Bayes + Dirichlet prior", 1)
    p.write_text(t, encoding="utf-8")
    print("analiz kartlari eklendi")

for k in ["sec-exact", "sec-mc", "sec-bayes", "sec-dirichlet", "sec-markov", "analysis-badge"]:
    print(k, p.read_text().count(k))
