# Roadmap

This roadmap is aimed at turning Obby from a personal local tool into a reusable
local-first Obsidian command center.

## V0.1 - Modular Local Command Center

Status: mostly implemented.

- Modular `obby_core/` package.
- Rich terminal UI.
- Markdown task scanning.
- Deterministic task classification.
- Progress dashboard.
- Local Ollama chat.
- Manual memory-only classification.
- Local-first `/today` and `/weekly` dashboards.
- Grounded `/focus`, `/today-plan`, and `/weekly-plan` planning.
- Read-only Obsidian safety model.

## V0.2 - Public Usability

Goal: make Obby easy for other people to adopt.

- Add `obby init` onboarding.
- Generate `obby_config.py` interactively.
- Add built-in profiles:
  - `study`
  - `project`
  - `work`
  - `personal`
  - `creator`
- Add `/doctor` to diagnose:
  - whether the folder exists
  - how many Markdown files were found
  - how many tasks were found
  - how many tasks were classified
  - which tags/headings were recognized
  - which files were ignored
- Add example note templates.
- Move personal Missing Term config into an example profile.
- Make default config generic.

## V0.3 - Obsidian Write-Back

Goal: support automation carefully.

This should remain opt-in.

- Dry-run previews for all write actions.
- Explicit confirmation before every write batch.
- Write only tags or metadata requested by the user.
- Never auto-check tasks without confirmation.
- Keep backups or reversible patches where possible.

Possible commands:

- `/tag-preview`
- `/tag-apply`
- `/mark-done-preview`
- `/mark-done-apply`

## Long-Term Ideas

- Textual/TUI mode with panes and keyboard shortcuts.
- SQLite-backed local index.
- Better query language.
- Plugin/profile system.
- Export weekly plan to Markdown.
- Optional desktop launcher.
- Multi-vault support.
- Multi-obby support.
- More customisation.
- Rewrite it in Go for easier distribution and installation.
