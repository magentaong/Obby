from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from .models import AppConfig


def save_weekly_draft(config: AppConfig, week: int, content: str) -> Path:
    drafts_dir = Path(__file__).parents[1] / ".obby" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"week-{week}-draft-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    file_path = drafts_dir / filename
    
    file_path.write_text(content, encoding="utf-8")
    return file_path


def get_latest_draft_path(week: int) -> Path | None:
    drafts_dir = Path(__file__).parents[1] / ".obby" / "drafts"
    if not drafts_dir.exists():
        return None
    
    drafts = list(drafts_dir.glob(f"week-{week}-draft-*.md"))
    if not drafts:
        return None
    
    return max(drafts, key=os.path.getmtime)
