#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import base64
from pathlib import Path
b64 = Path("scripts/ui_part1.b64").read_text() + Path("scripts/ui_part2.b64").read_text()
Path("templates/index.html").write_bytes(base64.b64decode(b64.strip()))
t = Path("templates/index.html").read_text(encoding="utf-8")
need = ["runLogCard", "resetSubmitUI", "copyRunLog", "Gönderiliyor", ".log-box"]
missing = [k for k in need if k not in t]
assert not missing, missing
print("UI garantili yazildi OK")
for k in need:
    print(" ", k, "OK")
PY
