"""Kaydet: seçimler + üretilmiş formül. Yükle: ikisini de geri getir."""
from pathlib import Path

p = Path("templates/index.html")
t = p.read_text(encoding="utf-8")
frag = Path("scripts/save_formula_fragment.js").read_text(encoding="utf-8")
if "captureFormula" in t and "renderSavedFormula" in t:
    print("save+formula zaten var")
else:
    start = t.find("  function saveCoupon()")
    if start < 0:
        raise SystemExit("saveCoupon yok")
    cstart = t.find("  function captureFormula()")
    if cstart >= 0:
        start = cstart
    end_markers = ["  const HEALTH_TIPS", "  async function runHealth", "  updateLiveStats(); renderSavedList();"]
    end = None
    for em in end_markers:
        i = t.find(em, start)
        if i > start:
            end = i
            break
    if end is None:
        raise SystemExit("blok sonu bulunamadi")
    t = t[:start] + frag + "\n" + t[end:]
    p.write_text(t, encoding="utf-8")
    print("save+formula eklendi")
print("captureFormula:", "captureFormula" in p.read_text())
print("renderSavedFormula:", "renderSavedFormula" in p.read_text())
