#!/usr/bin/env bash
# Yerel perfection kontrolü — CI ile aynı çekirdek adımlar
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> pytest (not slow)"
python -m pytest -m "not slow" -q

echo "==> system health (değişmezler)"
python -m spor_toto.health

ORNEK="1,10,1,12,0,10,2,10,1,12,02,1,10,2,10"
PROBS="1:0.5,0:0.3,2:0.2;1:0.4,0:0.4,2:0.2;1:0.6,0:0.2,2:0.2;1:0.5,0:0.25,2:0.25;1:0.3,0:0.4,2:0.3;1:0.45,0:0.35,2:0.2;1:0.5,0:0.3,2:0.2;1:0.4,0:0.3,2:0.3;1:0.55,0:0.25,2:0.2;1:0.5,0:0.3,2:0.2;1:0.4,0:0.3,2:0.3;1:0.5,0:0.3,2:0.2;1:0.45,0:0.35,2:0.2;1:0.5,0:0.25,2:0.25;1:0.4,0:0.4,2:0.2"

echo "==> CLI smoke (fix16)"
python -m spor_toto.cli --picks "$ORNEK" --kisa >/dev/null

echo "==> CLI smoke (bayes-preset dengeli)"
python -m spor_toto.cli --picks "$ORNEK" --probs "$PROBS" --bayes-preset dengeli --kisa >/dev/null

echo "OK — check.sh passed"
