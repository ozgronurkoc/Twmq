# -*- coding: utf-8 -*-
"""index.html header'a top-nav ekler: Formül / İstatistik / Sağlık."""
from pathlib import Path
import re

p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")

if 'href="/stats"' in t.split("</header>")[0]:
    print("top-nav zaten var")
else:
    css = '''
    header .top-nav { display: flex; align-items: center; gap: 6px; margin-left: 18px; flex-wrap: wrap; }
    header .top-nav a {
      font-size: 0.82rem; font-weight: 500; color: var(--text-sec);
      text-decoration: none; padding: 6px 12px; border-radius: 8px;
    }
    header .top-nav a:hover { background: var(--bg); color: var(--text); }
    header .top-nav a.active { background: var(--blue); color: #fff; }
'''
    if "header .top-nav" not in t:
        t = t.replace("header .ver {", css + "\n    header .ver {", 1)

    nav = '''  <nav class="top-nav">
    <a href="/" class="active">Formül Üret</a>
    <a href="/stats">İstatistik</a>
    <a href="/health-ui">Sağlık</a>
  </nav>
'''
    m = re.search(r"<header>.*?</header>", t, re.S)
    if not m:
        raise SystemExit("header bulunamadi")
    h = m.group(0)
    h2 = h.replace("</header>", nav + "</header>")
    t = t.replace(h, h2, 1)
    p.write_text(t, encoding="utf-8")
    print("top-nav eklendi")

print("DONE")
