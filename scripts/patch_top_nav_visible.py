# -*- coding: utf-8 -*-
"""Formul sayfasinda navigasyonu basligin altinda net satir olarak goster."""
from pathlib import Path
import re

p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")

# Guclu, her zaman gorunur nav satiri
bar_css = '''
    .app-nav-bar {
      display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
      padding: 10px 24px 12px; background: #fff;
      border-bottom: 1px solid var(--border-light);
    }
    .app-nav-bar a {
      font-size: 0.88rem; font-weight: 600; text-decoration: none;
      color: var(--text-sec); padding: 8px 14px; border-radius: 10px;
      border: 1px solid var(--border);
      background: #fff;
    }
    .app-nav-bar a:hover { color: var(--text); background: var(--bg); }
    .app-nav-bar a.active {
      background: var(--blue); border-color: var(--blue); color: #fff;
    }
'''

if ".app-nav-bar" not in t:
    if "</style>" in t:
        t = t.replace("</style>", bar_css + "\n  </style>", 1)
        print("css eklendi")
    else:
        raise SystemExit("style yok")
else:
    print("css var")

bar_html = '''
<div class="app-nav-bar">
  <a href="/" class="active">Formül Üret</a>
  <a href="/stats">İstatistik</a>
  <a href="/health-ui">Sağlık</a>
</div>
'''

if 'class="app-nav-bar"' not in t:
    m = re.search(r"</header>\s*", t)
    if not m:
        raise SystemExit("header kapanisi yok")
    t = t[: m.end()] + bar_html + t[m.end() :]
    p.write_text(t, encoding="utf-8")
    print("nav bar eklendi")
else:
    print("nav bar zaten var")

print("DONE")
