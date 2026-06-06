from __future__ import annotations

import json
import urllib.request
from typing import Any

from .models import AppConfig


class OllamaClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def is_running(self) -> bool:
        try:
            urllib.request.urlopen(self.config.ollama_tags_url, timeout=2)
            return True
        except Exception:
            return False

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, timeout: int = 180) -> str:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        request = urllib.request.Request(
            self.config.ollama_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            return str(result["message"]["content"])
