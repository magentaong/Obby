# Architecture

Obby is organized as a CLI entry point plus a modular `obby_core/` package.
The scanner and deterministic task model are the source of truth. Ollama is used
as a local reasoning assistant and not the primary parser.

## Runtime Flow

1. `obby.py` starts the app.
2. `obby_core.config` resolves CLI args, `obby_config.py`, stores environment variables, and defaults.
3. `obby_core.scanner` reads Markdown files from `TARGET_FOLDER` read-only.
4. `obby_core.classifier` classifies extracted tasks using tags and headings.
5. `obby_core.task_logic` applies reusable scope/current/behind/upcoming rules.
6. `obby_core.task_board` wraps the scanned context into reusable board queries and candidate selection.
7. `obby_core.progress` computes broader progress totals.
8. `obby_core.ui` renders the Rich terminal interface.
9. `obby_core.app` routes commands and calls Ollama when needed.
10. `obby_core.state` stores small local app state in `.obby/`.

## Modules

- `obby.py`: Entry point.
- `obby_core/app.py`: main command loop, command routing, and interactive workflows.
- `obby_core/config.py`: config loading, defaults, and precedence rules.
- `obby_core/commands.py`: command metadata, categories, aliases, and menu grouping.
- `obby_core/models.py`: dataclasses for config, tasks, context, and progress.
- `obby_core/scanner.py`: read-only Markdown scanning and context construction.
- `obby_core/classifier.py`: deterministic tag/heading classification.
- `obby_core/task_logic.py`: reusable task scoping, active-week, and sorting rules.
- `obby_core/task_board.py`: reusable query layer for current, behind, today, scoped, and candidate task views.
- `obby_core/progress.py`: progress rules and week inference.
- `obby_core/ollama_client.py`: local Ollama health checks and chat calls.
- `obby_core/prompts.py`: system prompts and grounded task packets.
- `obby_core/ui.py`: Rich/questionary/prompt-toolkit interface.
- `obby_core/state.py`: local `.obby/state.json` state such as remembered week.
- `.obby/state.json`: local state for remembered week, candidate edits, and the AI enable/disable switch.

## Data Model

The central object is `Task`.

Each task stores:

- task text
- source file and line number
- checked/unchecked state
- heading path
- tags
- inferred week
- inferred module
- classification kind
- classification reason

Task kinds are:

- `required`
- `stretch`
- `optional`
- `idea`
- `blocked`
- `unknown`

## Reliability Strategy

Obby avoids relying on the LLM for facts.

- Markdown scanning is deterministic.
- Tag and heading classification happens before any AI planning.
- Task scoping lives in pure functions that can be tested without the terminal UI.
- Candidate selection lives in `TaskBoard`, keyed by stable file/line/text hashes instead of transient scan IDs.
- Command metadata lives outside the UI/router so command groups can be reused in docs, tests, and future onboarding.
- `/today` and `/weekly` are local dashboards.
- `/focus`, `/today-plan`, and `/weekly-plan` use grounded candidate task packets.
- The model is instructed to recommend only tasks present in that packet.
- The TODO-list preset uses local task rendering instead of Ollama.
- `/ai off` disables all Ollama-backed routes while keeping local commands available.
- `/classify` only updates memory and never writes to Obsidian.

## Config Precedence

Settings resolve in this order:

1. CLI args
2. `obby_config.py`
3. environment variables
4. built-in defaults

This lets users keep the app generic while customizing their local vault,
modules, tags, headings, prompt presets, and ignore rules.

LLM behavior is also config-driven. `LLM_IDENTITY`, `LLM_MISSION`, and
`LLM_STYLE_RULES` are injected into the system prompt so local models know they
are acting as Obby instead of a generic chatbot.

Task scope is also config-driven. `TODO_SOURCE_KEYWORDS` decides which scanned
notes count as planning sources, `ACTIVE_SOURCE_KEYWORDS` marks always-relevant
sources, and `ACTIVE_WEEK_SOURCE_PATTERNS` defines how Obby recognizes the
current week from file or folder names.

## Safety Boundaries

Current version:

- Reads Markdown files.
- Writes small app state only to `.obby/`.
- Does not write to Markdown files.
- Does not edit tags.
- Does not check off TODOs.
- Does not move or delete files.

Future state should keep local state in `.obby/` before any Obsidian write-back
exists. Any write-back feature should require preview, confirmation, and dry-run support.
