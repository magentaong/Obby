# =============================================================================
# obby_config.example.py - Example configuration for Obby
#
# Copy this file to obby_config.py and edit it for your local setup.
#
# Priority order:
#   1. CLI arguments (--folder, --model, --week)
#   2. obby_config.py
#   3. Environment variables
#   4. Built-in defaults
# =============================================================================

APP_NAME = "Obby"
APP_SUBTITLE = "Local Obsidian Quest Engine"
APP_TAGLINE = "local-first command center - obsidian x ollama"
USE_CASE = "study"  # study, project, work, personal

LLM_IDENTITY = (
    "You are Obby, a local-first terminal command center for Obsidian notes."
)
LLM_MISSION = (
    "Help the user inspect real Markdown tasks, understand current work, and plan next actions from extracted note context."
)
LLM_STYLE_RULES = [
    "Use the name Obby when referring to yourself.",
    "Cite source files for task recommendations.",
    "Do not invent tasks, deadlines, chores, or study material.",
    "Say when something is not visible in the notes.",
]

# Vault/folder
VAULT = "yourOwnPath/Obby/examples"
TARGET_FOLDER = VAULT + "/sample-vault"

# Local Ollama
MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

# Schedule
TOTAL_WEEKS = 14
CURRENT_WEEK = None  # set to an int to skip auto-inference

# Modules are config-driven so Obby can support study, project, work, or personal flows.
MODULES = [
    {
        "key": "Backend Engineering",
        "name": "Backend Engineering + System Design",
        "tags": ["#module/go", "#go"],
        "outline_names": ["Module 1"],
    },
    {
        "key": "Frontend Engineering",
        "name": "Frontend Engineering",
        "tags": ["#module/frontend", "#frontend"],
        "outline_names": ["Module 2"],
    },
    {
        "key": "Project 1",
        "name": "Project 1",
        "tags": ["#module/Project", "#project", "#project1"],
        "outline_names": ["Module 3"],
    },
]


# Legacy outline support. Safe to remove if MODULES has outline_names.
MODULE_OUTLINE_NAMES = ["Module 1", "Module 2", "Module 3"]

TASK_TYPE_TAGS = {
    "required": ["#required", "#core", "#mustdo", "#must-do"],
    "stretch": ["#stretch"],
    "optional": ["#optional"],
    "idea": ["#idea", "#ideas", "#backlog"],
    "blocked": ["#blocked", "#stuck"],
}

HEADING_RULES = {
    "required": ["required", "core", "must do", "must-do", "quests"],
    "stretch": ["stretch", "stretch goals"],
    "optional": ["optional"],
    "idea": ["ideas", "idea backlog", "backlog"],
    "blocked": ["blocked", "stuck"],
}

IGNORE_KEYWORDS = [
    ".git",
    ".obsidian",
    "node_modules",
    "scripts",
    "__pycache__",
]

TODO_SOURCE_KEYWORDS = [
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

ACTIVE_SOURCE_KEYWORDS = [
    "Today",
    "Inbox",
    "Master TODOs",
]

ACTIVE_WEEK_SOURCE_PATTERNS = [
    r"week\s*{week}\b",
    r"w{week}(?:\b|d\d+)",
    r"#week/{week}",
]

CANDIDATE_TASK_KINDS = [
    "required",
    "blocked",
    "stretch",
]

CANDIDATE_MAX_TASKS = 15

STARTUP_VIEW = "compact"  # compact, full, silent
TASK_VIEW = "table"       # table or cards

MAX_LINES_PER_FILE = 120
MAX_TOTAL_CONTEXT_CHARS = 24000

THEME = {
    "primary": "bright_magenta",
    "secondary": "cyan",
    "accent": "bright_green",
    "warning": "yellow",
    "danger": "bright_red",
    "muted": "grey62",
}

XP_RULES = {
    "required_done": 100,
    "stretch_done": 50,
    "blocked_seen": 10,
}

PROMPT_PRESETS = {
    "1": (
        "Next 2-hour focus block",
        "What should I do next for the next 2 hours? Give me a main task, backup task, tiny task if tired, why, and evidence.",
    ),
    "2": (
        "List pending TODOs",
        "List pending TODOs from the provided notes. Group by source file and do not invent tasks.",
    ),
    "3": (
        "Plan today",
        "Plan today using realistic 2-hour focus blocks. Prioritize deadlines, required work, and high-leverage tasks.",
    ),
}
