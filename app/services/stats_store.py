from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

STATS_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "data", "stats.json")


def _ensure_parent_dir() -> None:
    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)


def _default_stats() -> Dict[str, Any]:
    return {"total_checks": 0, "total_fixes": 0, "updated_at": None}


def read_stats() -> Dict[str, Any]:
    _ensure_parent_dir()
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_stats()
        for k, v in _default_stats().items():
            data.setdefault(k, v)
        return data
    except FileNotFoundError:
        return _default_stats()
    except Exception:
        # 读取失败时不要影响主流程
        return _default_stats()


def write_stats(data: Dict[str, Any]) -> None:
    _ensure_parent_dir()
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def bump_counter(key: str, delta: int = 1) -> Dict[str, Any]:
    data = read_stats()
    data[key] = int(data.get(key, 0)) + int(delta)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        write_stats(data)
    except Exception:
        pass
    return data
