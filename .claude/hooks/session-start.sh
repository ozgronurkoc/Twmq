#!/bin/bash
#
# Bilgi grafını oturum başında tazeler.
#
# Yalnızca UCUZ bölümler (`moduller`, `kapilar`, `boru_hatlari`) yeniden
# ölçülür — üçünün de kaynağı dosyanın kendisidir ve toplam süre saniyenin
# altındadır. `sayilar` bölümüne DOKUNULMAZ: bir sayıyı üretmek komut
# koşmayı gerektirir (`pytest --collect-only`, eksiksiz kurulum) ve
# otomatik yeniden yazmak skill'in kuralını çiğnerdi — bayat girdi silinir
# ya da yeniden ölçülür, DÜZELTİLMİŞ SAYILMAZ. Şüpheli sayı yalnızca
# bildirilir.
#
# `--sessiz`: değişiklik ve şüphe yoksa hiçbir şey yazmaz. Bu çıktı her
# oturumda bağlama girdiği için sessizlik varsayılandır.
#
# Senkron koşar (async değil): tazeleme ~0,3 sn, async'in getireceği yarış
# koşulu bu kazanç için anlamsız olurdu.
#
# `$CLAUDE_CODE_REMOTE` kapısı BILEREK yok: graf `.gitignore`'da, yerel bir
# defterdir ve yerel oturumda da tazelenmesi gerekir.
set -uo pipefail

KOK="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$KOK" || exit 0

# Depo değilse ya da python3 yoksa oturumu ENGELLEME — sessizce çık.
command -v python3 >/dev/null 2>&1 || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
[ -f .claude/graf_uret.py ] || exit 0

python3 .claude/graf_uret.py --sessiz 2>&1 || {
  echo "bilgi grafi tazelenemedi (oturum etkilenmedi): .claude/graf_uret.py"
  exit 0
}
