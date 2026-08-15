from pathlib import Path
import re
p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")
if "fetch(form" in t or "fetch(form.getAttribute" in t:
    print("AJAX zaten var")
else:
    frag = Path("scripts/ajax_handler.jsfragment").read_text(encoding="utf-8")
    pat = r"document\.getElementById\('mainForm'\)\.addEventListener\('submit', function\(e\)\{.*?\n  \};"
    m = re.search(pat, t, re.S)
    if not m:
        raise SystemExit("submit handler bulunamadi")
    t = t[:m.start()] + frag + t[m.end():]
    t = t.replace("?.", ".")
    p.write_text(t, encoding="utf-8")
    print("AJAX eklendi")
print("fetch:", "fetch(" in p.read_text())
