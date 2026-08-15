#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Premium sayfa bütünlük kontrolü (formula / stats / health).

Kullanım:
  python3 scripts/install_premium_pages.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

PAGES = {
    "app/page.tsx": ["Formül Üret", "onSolve", "matches"],
    "app/stats/page.tsx": ["Tarihsel", "getStats"],
    "app/health/page.tsx": ["Sağlık", "getHealth"],
    "app/layout.tsx": ["Spor Toto Lab", "sidebar"],
    "lib/api.ts": ["/api/solve", "/api/stats", "/api/health"],
}


def main() -> int:
    print("=== Premium sayfa doğrulama ===")
    ok = True
    for rel, needles in PAGES.items():
        path = FRONTEND / rel
        if not path.exists():
            print(f"✗ EKSİK  {rel}")
            ok = False
            continue
        text = path.read_text(encoding="utf-8")
        missing = [n for n in needles if n not in text]
        if missing:
            print(f"✗ ZAYIF  {rel}  (eksik: {', '.join(missing)})")
            ok = False
        else:
            print(f"✓ OK     {rel}")

    if ok:
        print("\nTüm premium sayfalar hazır.")
        return 0
    print("\nBazı dosyalar eksik/bozuk. git checkout origin/main -- frontend")
    return 1


if __name__ == "__main__":
    sys.exit(main())
