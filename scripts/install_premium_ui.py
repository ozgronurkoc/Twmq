#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Premium Next.js UI kurulum / doğrulama.

Kullanım:
  python3 scripts/install_premium_ui.py

Yapar:
  - frontend/ varlığını kontrol eder
  - .env.local yoksa .env.example'dan kopyalar
  - package.json ve kritik sayfaları doğrular
  - npm install önerisi verir
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
REQUIRED = [
    "app/page.tsx",
    "app/layout.tsx",
    "app/stats/page.tsx",
    "app/health/page.tsx",
    "lib/api.ts",
    "package.json",
    "tailwind.config.ts",
    "globals.css",
]


def main() -> int:
    print("=== Premium Next.js UI kurulum ===")
    print(f"kök: {ROOT}")

    if not FRONTEND.is_dir():
        print("HATA: frontend/ dizini yok.")
        print("  git fetch origin && git checkout origin/main -- frontend")
        return 1

    missing = [p for p in REQUIRED if not (FRONTEND / p).exists()]
    if missing:
        print("EKSİK dosyalar:")
        for m in missing:
            print(f"  - frontend/{m}")
        print("  git checkout origin/main -- frontend")
        return 1

    print("✓ Kritik dosyalar mevcut")

    env_example = FRONTEND / ".env.example"
    env_local = FRONTEND / ".env.local"
    if env_example.exists() and not env_local.exists():
        shutil.copy(env_example, env_local)
        print("✓ .env.local oluşturuldu (.env.example'dan)")
    elif env_local.exists():
        print("✓ .env.local zaten var")
    else:
        print("! .env.example yok — NEXT_PUBLIC_API_URL=http://127.0.0.1:8080 elle ayarla")

    print()
    print("Sonraki adımlar:")
    print("  1) cd frontend && npm install")
    print("  2) Terminal A:  python web_app.py          # API :8080")
    print("  3) Terminal B:  cd frontend && npm run dev  # UI  :3000")
    print("  4) Tarayıcı:    http://localhost:3000")
    print()
    print("Veya tek komut:  bash scripts/run_next_dev.sh")
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
