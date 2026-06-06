from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LocalState:
    path: Path

    @classmethod
    def default(cls) -> "LocalState":
        return cls(Path(__file__).parents[1] / ".obby" / "state.json")

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def get_current_week(self) -> int | None:
        value = self.load().get("current_week")
        return int(value) if isinstance(value, int) else None

    def set_current_week(self, week: int) -> None:
        data = self.load()
        data["current_week"] = week
        self.save(data)

    def is_llm_enabled(self) -> bool:
        # Keep 'ai_enabled' key for compatibility but use LLM in code
        value = self.load().get("ai_enabled", True)
        return bool(value) if isinstance(value, bool) else True

    def set_llm_enabled(self, enabled: bool) -> None:
        data = self.load()
        data["ai_enabled"] = enabled
        self.save(data)

    def is_debug_enabled(self) -> bool:
        value = self.load().get("debug_enabled", False)
        return bool(value) if isinstance(value, bool) else False

    def set_debug_enabled(self, enabled: bool) -> None:
        data = self.load()
        data["debug_enabled"] = enabled
        self.save(data)

    def get_startup_view(self, default: str = "compact") -> str:
        value = self.load().get("startup_view", default)
        return str(value)

    def set_startup_view(self, view: str) -> None:
        data = self.load()
        data["startup_view"] = view
        self.save(data)

    def get_task_view(self, default: str = "table") -> str:
        value = self.load().get("task_view", default)
        return str(value)

    def set_task_view(self, view: str) -> None:
        data = self.load()
        data["task_view"] = view
        self.save(data)

    def get_list(self, key: str) -> list[str]:
        value = self.load().get(key, [])
        return [str(item) for item in value] if isinstance(value, list) else []

    def add_to_list(self, key: str, value: str) -> None:
        data = self.load()
        values = [str(item) for item in data.get(key, []) if isinstance(item, str)]
        if value not in values:
            values.append(value)
        data[key] = values
        self.save(data)

    def remove_from_list(self, key: str, value: str) -> None:
        data = self.load()
        values = [str(item) for item in data.get(key, []) if isinstance(item, str)]
        data[key] = [item for item in values if item != value]
        self.save(data)

    def clear_list(self, key: str) -> None:
        data = self.load()
        data[key] = []
        self.save(data)
