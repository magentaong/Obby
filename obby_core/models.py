from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TaskKind(str, Enum):
    REQUIRED = "required"
    URGENT = "urgent"
    STRETCH = "stretch"
    OPTIONAL = "optional"
    IDEA = "idea"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class ModuleRule:
    key: str
    name: str
    tags: list[str] = field(default_factory=list)
    outline_names: list[str] = field(default_factory=list)


@dataclass
class Theme:
    primary: str = "bright_magenta"
    secondary: str = "cyan"
    accent: str = "bright_green"
    warning: str = "yellow"
    danger: str = "bright_red"
    muted: str = "grey62"


@dataclass
class AppConfig:
    app_name: str
    subtitle: str
    tagline: str
    use_case: str
    vault: str | None
    target_folder: Path
    model: str
    ollama_url: str
    ollama_tags_url: str
    total_weeks: int
    current_week: int | None
    module_rules: list[ModuleRule]
    task_type_tags: dict[str, list[str]]
    heading_rules: dict[str, list[str]]
    ignore_keywords: list[str]
    max_lines_per_file: int
    max_total_context_chars: int
    prompt_presets: dict[str, tuple[str, str]]
    llm_identity: str = ""
    llm_mission: str = ""
    llm_style_rules: list[str] = field(default_factory=list)
    todo_source_keywords: list[str] = field(default_factory=list)
    active_source_keywords: list[str] = field(default_factory=list)
    active_week_source_patterns: list[str] = field(default_factory=list)
    candidate_task_kinds: list[str] = field(default_factory=list)
    candidate_max_tasks: int = 15
    startup_view: str = "compact"
    task_view: str = "table"
    theme: Theme = field(default_factory=Theme)
    xp_rules: dict[str, int] = field(default_factory=dict)
    today_tags: list[str] = field(default_factory=list)
    urgent_tags: list[str] = field(default_factory=list)
    required_tags: list[str] = field(default_factory=list)
    blocked_tags: list[str] = field(default_factory=list)
    optional_tags: list[str] = field(default_factory=list)
    stretch_tags: list[str] = field(default_factory=list)
    week_tag_pattern: str = ""
    due_date_pattern: str = ""


@dataclass
class Task:
    id: int
    text: str
    source_file: Path
    line_number: int
    checked: bool
    heading_path: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    week: int | None = None
    module: str | None = None
    kind: TaskKind = TaskKind.UNKNOWN
    all_kinds: list[TaskKind] = field(default_factory=list)
    classification_reason: str = "unclassified"
    llm_reason: str | None = None
    due_date: datetime.date | None = None

    def __post_init__(self) -> None:
        if not self.all_kinds:
            self.all_kinds = [self.kind]

    @property
    def source_label(self) -> str:
        return f"{self.source_file.name}:{self.line_number}"

    @property
    def heading_label(self) -> str:
        return " > ".join(self.heading_path)


@dataclass
class NoteContext:
    target_folder: Path
    tasks: list[Task] = field(default_factory=list)
    completed_tasks: list[Task] = field(default_factory=list)
    deadlines: list[str] = field(default_factory=list)
    weekly_items: list[str] = field(default_factory=list)
    module_outlines: list[str] = field(default_factory=list)
    general_context: list[str] = field(default_factory=list)
    files_used: list[Path] = field(default_factory=list)
    raw_chunks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all_tasks(self) -> list[Task]:
        return self.tasks + self.completed_tasks


@dataclass
class ProgressSummary:
    required_total: int = 0
    required_done: int = 0
    stretch_total: int = 0
    stretch_done: int = 0
    optional_total: int = 0
    idea_total: int = 0
    blocked_total: int = 0
    unknown_total: int = 0
    behind: list[Task] = field(default_factory=list)
    current: list[Task] = field(default_factory=list)
    upcoming: list[Task] = field(default_factory=list)

    @property
    def required_percent(self) -> float:
        if not self.required_total:
            return 0.0
        return self.required_done / self.required_total

    @property
    def stretch_percent(self) -> float:
        if not self.stretch_total:
            return 0.0
        return self.stretch_done / self.stretch_total
