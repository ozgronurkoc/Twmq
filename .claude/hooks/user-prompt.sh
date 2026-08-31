#!/bin/bash
#
# Kullanıcı mesajı bilgi grafıyla ilgiliyse ilgili graf girdilerini bağlama
# enjekte eder (`UserPromptSubmit`).
#
# Neden hook: `CLAUDE.md` yalnızca YÖNLENDİRİR ("keşiften önce grafa bak") ve
# model bunu atlayabilir. Bu hook yönlendirmez — cevabı karar anından ÖNCE
# bağlama koyar, yani kullanmamak diye bir seçenek kalmaz.
#
# Mesajı ASLA engellemez: python3 yoksa, graf yoksa, betik çökerse ya da
# mesaj hiçbir tetikleyiciye uymuyorsa sessizce çıkar (0 token enjekte edilir).
set -uo pipefail

KOK="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$KOK" 2>/dev/null || exit 0

command -v python3 >/dev/null 2>&1 || exit 0
[ -f .claude/graf_baglam.py ] || exit 0

python3 .claude/graf_baglam.py 2>/dev/null || exit 0
