from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandSpec:
    command: str
    category: str
    mode: str
    description: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec("/dashboard", "Daily", "local", "today's scoped task dashboard", ("/today",)),
    CommandSpec("/weekly", "Daily", "local", "current week dashboard"),
    CommandSpec("/draft-weekly", "Daily", "LLM", "generate weekly planning draft"),
    CommandSpec("/overview", "Daily", "local", "broader progress overview"),
    CommandSpec("/candidates", "Daily", "local", "explicit candidate/focus list"),
    CommandSpec("/current", "Tasks", "local", "current week required tasks"),
    CommandSpec("/behind", "Tasks", "local", "behind required tasks"),
    CommandSpec("/upcoming", "Tasks", "local", "future required tasks"),
    CommandSpec("/quests", "Tasks", "local", "active required/core tasks", ("/todos",)),
    CommandSpec("/stretch", "Tasks", "local", "active stretch goals"),
    CommandSpec("/optional", "Tasks", "local", "active optional tasks"),
    CommandSpec("/ideas", "Tasks", "local", "active idea backlog"),
    CommandSpec("/blocked", "Tasks", "local", "active blocked tasks"),
    CommandSpec("/unknown", "Tasks", "local", "active unclassified tasks"),
    CommandSpec("/all-quests", "Broad Views", "local", "all scoped required tasks"),
    CommandSpec("/all-stretch", "Broad Views", "local", "all scoped stretch goals"),
    CommandSpec("/all-optional", "Broad Views", "local", "all scoped optional tasks"),
    CommandSpec("/all-ideas", "Broad Views", "local", "all scoped ideas"),
    CommandSpec("/all-blocked", "Broad Views", "local", "all scoped blocked tasks"),
    CommandSpec("/all-unknown", "Broad Views", "local", "all scoped unknown tasks"),
    CommandSpec("/classify", "Tuning", "local", "manually classify one task in memory"),
    CommandSpec("/search <kw>", "Tuning", "local", "search extracted context"),
    CommandSpec("/debug", "Tuning", "session", "toggle candidate task debug mode", ("/debug on", "/debug off", "/debug status")),
    CommandSpec("/files", "Tuning", "local", "show scanned Markdown files"),
    CommandSpec("/context", "Tuning", "local", "preview extracted context"),
    CommandSpec("/deadlines", "Tuning", "local", "show detected deadline lines"),
    CommandSpec("/focus", "LLM", "LLM", "next 2-hour focus block"),
    CommandSpec("/today-plan", "LLM", "LLM", "grounded daily plan"),
    CommandSpec("/weekly-plan", "LLM", "LLM", "grounded weekly pacing plan"),
    CommandSpec("/pick", "LLM", "mixed", "up/down preset picker"),
    CommandSpec("/llm status", "Session", "session", "show LLM feature switch", ("/llm", "/ai status", "/ai")),
    CommandSpec("/llm off", "Session", "session", "disable Ollama-backed commands", ("/llm disable", "/ai off", "/ai disable")),
    CommandSpec("/llm on", "Session", "session", "enable Ollama-backed commands", ("/llm enable", "/ai on", "/ai enable")),
    CommandSpec("/week N", "Session", "session", "set and remember current week"),
    CommandSpec("/state", "Session", "local", "show remembered local state"),
    CommandSpec("/summary", "Session", "local", "same as dashboard summary"),
    CommandSpec("/refresh", "Session", "local", "reload notes read-only"),
    CommandSpec("/clear", "Session", "session", "clear chat memory"),
    CommandSpec("/menu", "Session", "session", "show this command center", ("/help",)),
    CommandSpec("/exit", "Session", "session", "quit", ("/quit", "bye")),
)


CATEGORY_ORDER = ("Daily", "Tasks", "Broad Views", "Tuning", "LLM", "Session")
CATEGORY_ALIASES = {
    "daily": "Daily",
    "day": "Daily",
    "tasks": "Tasks",
    "task": "Tasks",
    "broad": "Broad Views",
    "all": "Broad Views",
    "tuning": "Tuning",
    "tune": "Tuning",
    "llm": "LLM",
    "ai": "LLM",
    "session": "Session",
    "system": "Session",
}


def commands_by_category() -> dict[str, list[CommandSpec]]:
    grouped: dict[str, list[CommandSpec]] = {category: [] for category in CATEGORY_ORDER}
    for command in COMMANDS:
        grouped.setdefault(command.category, []).append(command)
    return grouped


def resolve_category(raw: str | None) -> str | None:
    if not raw:
        return None
    normalized = raw.lower().strip()
    return CATEGORY_ALIASES.get(normalized)


def all_command_tokens() -> set[str]:
    tokens: set[str] = set()
    for command in COMMANDS:
        tokens.add(command.command.split()[0])
        tokens.update(alias.split()[0] for alias in command.aliases)
    return tokens
