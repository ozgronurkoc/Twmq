"""Spor Toto tarihsel 1/0/2 istatistikleri."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "st_history_2025_26.json"


@lru_cache(maxsize=1)
def load_history() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        return {
            "meta": {"weeks": 0, "matches": 0},
            "totals": {},
            "weekly_avg": {},
            "bands": {},
            "weeks": [],
            "error": f"Veri dosyasi yok: {DATA_FILE}",
        }
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def history_summary() -> Dict[str, Any]:
    data = load_history()
    return {
        "meta": data.get("meta", {}),
        "totals": data.get("totals", {}),
        "weekly_avg": data.get("weekly_avg", {}),
        "bands": data.get("bands", {}),
        "week_count": len(data.get("weeks", [])),
        "error": data.get("error"),
    }


def history_weeks() -> list:
    return load_history().get("weeks", [])


def history_week(week: int) -> Optional[Dict[str, Any]]:
    for w in history_weeks():
        if w.get("week") == week:
            return w
    return None
