from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
from types import ModuleType
from typing import Any

from .models import AppConfig, ModuleRule, Theme


DEFAULT_PROMPTS: dict[str, tuple[str, str]] = {
    "1": (
        "Next 2-hour focus block",
        "What should I do next for the next 2 hours? Give me the main tasks, backup tasks, and tiny task if tired, why, and evidence.",
    ),
    "2": (
        "List pending TODOs",
        "List pending TODOs from the provided notes. Group by source file and do not invent tasks.",
    ),
    "3": (
        "Plan today",
        "Plan today using realistic 2-hour focus blocks. Prioritize deadlines, required work, and high-leverage tasks.",
    ),
    "4": (
        "Tired mode",
        "I am tired. Pick the smallest useful thing I can do now, a 20-minute version, and a stop condition.",
    ),
    "5": (
        "What is urgent?",
        "What is most urgent or time-sensitive from the notes? Use explicit evidence only.",
    ),
    "6": (
        "Project/module summary",
        "Summarize this folder, active areas, pending tasks, and unclear items. Cite source files.",
    ),
    "7": (
        "Help me choose",
        "Compare the top 3 possible tasks from my notes, pick one, and explain why.",
    ),
}

DEFAULT_TASK_TYPE_TAGS = {
    "required": ["#required", "#core", "#mustdo", "#must-do"],
    "stretch": ["#stretch"],
    "optional": ["#optional"],
    "idea": ["#idea", "#ideas", "#backlog"],
    "blocked": ["#blocked", "#stuck"],
}

DEFAULT_HEADING_RULES = {
    "required": ["required", "core", "must do", "must-do", "quests"],
    "stretch": ["stretch", "stretch goals"],
    "optional": ["optional"],
    "idea": ["ideas", "idea backlog", "backlog"],
    "blocked": ["blocked", "stuck"],
}

DEFAULT_IGNORE_KEYWORDS = [
    ".git",
    ".obsidian",
    "node_modules",
    "__pycache__",
]

DEFAULT_TODO_SOURCE_KEYWORDS = [
    "TODO",
    "Todo",
    "Tasks",
    "Inbox",
    "Today",
    "Weeklies",
    "Weekly",
    "Dailies",
    "Daily",
    "Week ",
]

DEFAULT_ACTIVE_SOURCE_KEYWORDS = [
    "Today",
    "Inbox",
    "Master TODOs",
]

DEFAULT_ACTIVE_WEEK_SOURCE_PATTERNS = [
    r"week\s*{week}\b",
    r"w{week}(?:\b|d\d+)",
    r"#week/{week}",
]

DEFAULT_CANDIDATE_TASK_KINDS = [
    "required",
    "blocked",
    "stretch",
]

DEFAULT_LLM_IDENTITY = (
    "You are Obby, a local-first terminal command center for Obsidian notes. "
    "You help the user inspect real Markdown tasks, understand current work, "
    "and plan next actions from extracted note context."
)

DEFAULT_LLM_MISSION = (
    "Act as a grounded planning assistant, not a generic chatbot. Your job is to "
    "reason over scanned Obsidian tasks, cite sources, avoid invented work, and "
    "help the user choose practical next steps."
)

DEFAULT_LLM_STYLE_RULES = [
    "Use the name Obby when referring to yourself.",
    "Be concise, direct, and supportive.",
    "Prefer concrete task recommendations over generic productivity advice.",
    "Never invent tasks, deadlines, emails, meetings, or prep material.",
    "If evidence is missing, say that Obby does not see it in the notes.",
]

DEFAULT_MODULE_RULES: list[ModuleRule] = []


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Obby - local-first Obsidian command center"
    )
    parser.add_argument("command", nargs="?", default="run", help="Command to run: run (default) or init.")
    parser.add_argument("--folder", default=None, help="Notes folder to scan.")
    parser.add_argument("--model", default=None, help="Ollama model name.")
    parser.add_argument("--week", type=int, default=None, help="Current week override.")
    parser.add_argument(
        "--config",
        default=None,
        help="Optional path to a Python config file. Defaults to ./obby_config.py.",
    )
    return parser.parse_args(argv)


def run_init_wizard() -> None:
    import questionary
    from rich.console import Console
    console = Console()

    console.print()
    console.print("[bold bright_magenta]OBBY CONFIGURATION WIZARD[/bold bright_magenta]")
    console.print("This will create a basic [cyan]obby_config.py[/cyan] in your current folder.")
    console.print()

    config_path = Path("obby_config.py")
    if config_path.exists():
        if not questionary.confirm("obby_config.py already exists. Overwrite?").ask():
            return

    target_folder = questionary.text(
        "Obsidian folder path to scan (relative or absolute):",
        default="~/Documents/ObsidianVault",
    ).ask()
    
    model = questionary.text(
        "Ollama model name (e.g., llama3.2, mistral):",
        default="llama3.2",
    ).ask()

    use_case = questionary.select(
        "Primary use case:",
        choices=[
            questionary.Choice(title="Study/School", value="study"),
            questionary.Choice(title="Work/Projects", value="work"),
            questionary.Choice(title="General Planning", value="personal"),
        ],
    ).ask()

    total_weeks = questionary.text(
        "Total weeks in your semester or project (if applicable):",
        default="14",
    ).ask()

    content = f'''from __future__ import annotations
from obby_core.models import ModuleRule

# --- OBBY CONFIGURATION ---

# The folder where your Obsidian notes live.
TARGET_FOLDER = "{target_folder}"

# The local Ollama model to use for planning and drafting.
MODEL = "{model}"

# Your primary use case (study, work, personal).
USE_CASE = "{use_case}"

# LLM identity and behavior. This tells local models what Obby is.
LLM_IDENTITY = "You are Obby, a local-first terminal command center for Obsidian notes."
LLM_MISSION = "Help the user inspect real Markdown tasks, understand current work, and plan next actions from extracted note context."
LLM_STYLE_RULES = [
    "Use the name Obby when referring to yourself.",
    "Cite source files for task recommendations.",
    "Do not invent tasks, deadlines, chores, or study material.",
    "Say when something is not visible in the notes.",
]

# Total weeks in your cycle.
TOTAL_WEEKS = {total_weeks}

# Optional: List your modules or major workstreams.
MODULES = [
    ModuleRule(
        key="general",
        name="General Tasks",
        tags=["#general"],
        outline_names=["Inbox"],
    ),
]

# Tags that define task priority/kind.
TASK_TYPE_TAGS = {{
    "required": ["#required", "#mustdo", "#core"],
    "stretch": ["#stretch", "#bonus"],
    "optional": ["#optional"],
    "idea": ["#idea", "#backlog"],
    "blocked": ["#blocked", "#stuck"],
}}

# Headings that imply task type if no tag is found.
HEADING_RULES = {{
    "required": ["required", "core", "must do"],
    "stretch": ["stretch", "bonus"],
    "idea": ["ideas", "backlog"],
}}

# Files or folders to ignore during scans.
IGNORE_KEYWORDS = [".git", ".obsidian", "node_modules", "__pycache__"]

# Source keywords for task extraction (files with these in their name).
TODO_SOURCE_KEYWORDS = ["TODO", "Tasks", "Today", "Weekly", "Daily"]
'''
    config_path.write_text(content, encoding="utf-8")
    console.print()
    console.print(f"[bright_green]SUCCESS:[/bright_green] Created [cyan]{config_path}[/cyan]")
    console.print("You can now run Obby with [bold]python obby.py[/bold]")
    console.print()


def load_config_module(config_path: str | None = None) -> ModuleType | None:
    path = Path(config_path).expanduser() if config_path else Path(__file__).parents[1] / "obby_config.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("obby_config", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cfg(module: ModuleType | None, attr: str, env_var: str | None, default: Any) -> Any:
    if module and hasattr(module, attr):
        return getattr(module, attr)
    if env_var:
        env_val = os.getenv(env_var)
        if env_val is not None:
            return env_val
    return default


def _as_module_rules(raw: Any) -> list[ModuleRule]:
    if not raw:
        return []
    rules: list[ModuleRule] = []
    for item in raw:
        if isinstance(item, ModuleRule):
            rules.append(item)
        elif isinstance(item, dict):
            rules.append(
                ModuleRule(
                    key=str(item.get("key", item.get("name", "module"))).lower(),
                    name=str(item.get("name", item.get("key", "Module"))),
                    tags=list(item.get("tags", [])),
                    outline_names=list(item.get("outline_names", item.get("outlines", []))),
                )
            )
    return rules


def resolve_config(args: argparse.Namespace) -> AppConfig:
    module = load_config_module(args.config)
    if module is None and args.command == "run":
        from rich.console import Console
        console = Console()
        console.print("[yellow]WARNING:[/yellow] No [cyan]obby_config.py[/cyan] found. Using built-in defaults.")
        console.print("Run [bold]python obby.py init[/bold] to create your configuration.")
        console.print()

    vault = _cfg(module, "VAULT", "OBBY_VAULT", None)
    raw_folder = args.folder or _cfg(module, "TARGET_FOLDER", "OBBY_FOLDER", "Missing Folder")
    target_folder = Path(str(raw_folder)).expanduser().resolve()

    module_rules = _as_module_rules(_cfg(module, "MODULES", None, None))
    legacy_outline_names = _cfg(module, "MODULE_OUTLINE_NAMES", None, None)
    if legacy_outline_names:
        for index, outline in enumerate(legacy_outline_names):
            if index < len(module_rules) and outline not in module_rules[index].outline_names:
                module_rules[index].outline_names.append(outline)

    theme_raw = _cfg(module, "THEME", None, {})
    theme = Theme(**theme_raw) if isinstance(theme_raw, dict) else Theme()

    return AppConfig(
        app_name=str(_cfg(module, "APP_NAME", "OBBY_APP_NAME", "Obby")),
        subtitle=str(
            _cfg(
                module,
                "APP_SUBTITLE",
                "OBBY_APP_SUBTITLE",
                "Local Obsidian Quest Engine",
            )
        ),
        tagline=str(
            _cfg(
                module,
                "APP_TAGLINE",
                "OBBY_APP_TAGLINE",
                "local-first command center - obsidian x ollama",
            )
        ),
        use_case=str(_cfg(module, "USE_CASE", "OBBY_USE_CASE", "study")),
        vault=str(vault) if vault else None,
        target_folder=target_folder,
        model=str(args.model or _cfg(module, "MODEL", "OBBY_MODEL", "llama3.2")),
        ollama_url=str(
            _cfg(module, "OLLAMA_URL", "OBBY_OLLAMA_URL", "http://localhost:11434/api/chat")
        ),
        ollama_tags_url=str(
            _cfg(
                module,
                "OLLAMA_TAGS_URL",
                "OBBY_OLLAMA_TAGS_URL",
                "http://localhost:11434/api/tags",
            )
        ),
        total_weeks=int(_cfg(module, "TOTAL_WEEKS", "OBBY_TOTAL_WEEKS", 14)),
        current_week=args.week
        if args.week is not None
        else _cfg(module, "CURRENT_WEEK", "OBBY_CURRENT_WEEK", None),
        module_rules=module_rules,
        task_type_tags=dict(
            _cfg(module, "TASK_TYPE_TAGS", None, DEFAULT_TASK_TYPE_TAGS)
        ),
        heading_rules=dict(_cfg(module, "HEADING_RULES", None, DEFAULT_HEADING_RULES)),
        ignore_keywords=list(
            _cfg(module, "IGNORE_KEYWORDS", None, DEFAULT_IGNORE_KEYWORDS)
        ),
        max_lines_per_file=int(_cfg(module, "MAX_LINES_PER_FILE", None, 120)),
        max_total_context_chars=int(
            _cfg(module, "MAX_TOTAL_CONTEXT_CHARS", None, 24000)
        ),
        prompt_presets=dict(_cfg(module, "PROMPT_PRESETS", None, DEFAULT_PROMPTS)),
        llm_identity=str(_cfg(module, "LLM_IDENTITY", None, DEFAULT_LLM_IDENTITY)),
        llm_mission=str(_cfg(module, "LLM_MISSION", None, DEFAULT_LLM_MISSION)),
        llm_style_rules=list(_cfg(module, "LLM_STYLE_RULES", None, DEFAULT_LLM_STYLE_RULES)),
        todo_source_keywords=list(
            _cfg(module, "TODO_SOURCE_KEYWORDS", None, DEFAULT_TODO_SOURCE_KEYWORDS)
        ),
        active_source_keywords=list(
            _cfg(module, "ACTIVE_SOURCE_KEYWORDS", None, DEFAULT_ACTIVE_SOURCE_KEYWORDS)
        ),
        active_week_source_patterns=list(
            _cfg(
                module,
                "ACTIVE_WEEK_SOURCE_PATTERNS",
                None,
                DEFAULT_ACTIVE_WEEK_SOURCE_PATTERNS,
            )
        ),
        candidate_task_kinds=list(
            _cfg(module, "CANDIDATE_TASK_KINDS", None, DEFAULT_CANDIDATE_TASK_KINDS)
        ),
        candidate_max_tasks=int(_cfg(module, "CANDIDATE_MAX_TASKS", None, 15)),
        startup_view=str(_cfg(module, "STARTUP_VIEW", "OBBY_STARTUP_VIEW", "compact")),
        task_view=str(_cfg(module, "TASK_VIEW", "OBBY_TASK_VIEW", "table")),
        theme=theme,
        xp_rules=dict(
            _cfg(
                module,
                "XP_RULES",
                None,
                {"required_done": 100, "stretch_done": 50, "blocked_seen": 10},
            )
        ),
    )
