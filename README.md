# Obby

Obby is a terminal helper for people who keep their plans in Obsidian.

I built it because my notes had a lot of useful planning information and info dumps, but then every single time I open my notes, I end up having to manually check the TODOs and scroll past my notes to decide which tasks were needed. So instead of figuring that out, I went on a side quest rabbit hole and decided to turn that painpoint into a project.

Obby scans Markdown notes, pulls out tasks, groups them into useful buckets, and can ask a local LLM model to help plan from those tasks. It is local-first and read-only by default, the LLM is a feature you can turn off, and Obby still works without it.

**Comment:**
For now, the reason for implementing the LLM within this system is so that it can help with the reasoning for task prioritisation, as well as planning for those who suffer with task analysis paralysis, and for those who just prefer using LLM to reason.

The terminal UI uses rich because that makes it more fun to use :\)

## Quick Start (30 Seconds)

The fastest way to install and configure Obby:

1. **Install via pip**:
   ```zsh
   pip install git+https://github.com/magentaong/Obby.git
   ```
2. **Initialize**:
   ```zsh
   obby init
   ```
3. **Launch**:
   ```zsh
   obby
   ```

---

## What It Does

- Reads Markdown files from an Obsidian folder.
- Extracts checkbox tasks like `- [ ]` and `- [x]`.
- Classifies tasks as required, stretch, optional, idea, blocked, or unknown. (You can customise it to your liking)
- Tracks core progress separately from bonus/stretch work.
- Shows behind/current/upcoming tasks based on week tags and active weekly notes.
- Uses local Ollama (LLM) for planning and drafting from extracted tasks.
- Keeps LLM grounded in tasks that were actually found in your notes.
- Has grouped commands through `/menu`, with filtered views like `/menu tasks` and `/menu llm`.
- Supports `/llm off` so the local deterministic parts can run without Ollama.
- Can draft weekly planning notes with `/draft-weekly`.
- Stores local app state in `.obby/state.json` and draft files in `.obby/drafts/`.

Obby works really well with Obsidian cause Obsidian uses markdown, and as of now Obby only supports markdown.

**Comment:** Perhaps in the future I'd like to implement it such that it also allows word docs and to be integrated well with other productivity systems.

## Who It Is For

Obby can work for:

- students managing weekly study plans
- developers tracking project TODOs
- people using Obsidian as a personal command center
- job hunters tracking applications and interview prep :O (me rn)
- anyone with Markdown tasks who wants a local planning assistant

I think the only prerequisite of this is to have to have a somewhat consistent markdown note taking habit, and also be comfortable to use terminal for this.

## Note Format

The minimum useful format is:

```md
- [ ] Unfinished task
- [x] Finished task
```

Would recommend using [this](obsidian://show-plugin?id=obsidian-tasks-plugin) Obsidian community plug-in

Obby works better if you use tags:

```md
- [ ] Finish API README #required #week/2 #module/backend
- [ ] Try dashboard polish #stretch
- [ ] Waiting on AWS access #blocked
```

Or headings:

```md
## Required

- [ ] Submit assignment

## Stretch Goals

- [ ] Add extra visual polish

## Ideas

- [ ] Build a future automation flow
```

These labels are configurable. If your notes use `## Must Ship` instead of `## Required`, you can configure Obby in `obby_config.py` to use `## Must Ship`.

## Safety

Current version is read-only toward Obsidian. It doesn't touch your files at all. No touchy touchy.

Future write features should be opt-in, previewed first, and probably stored in `.obby/` before touching real notes, that or it is also highly recommended to either have Obsidian Sync or use github to store your notes' version history before it gets modified.

## Install

```zsh
cd /path/to/Obby
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(This part is completely optional, if you'd like to not use LLM at all, you can skip this part)

Install Ollama separately, then pull a local model:

```zsh
ollama pull llama3.2
ollama serve
```

## Configure

### Option 1: Guided Setup (Recommended)

Run the initialization wizard to create a basic configuration:

```zsh
python obby.py init
```

The wizard will guide you through setting up your Obsidian path, preferred LLM model, and planning cycle.

### Option 2: Manual Config

Copy the example config:

```zsh
cp obby_config.example.py obby_config.py
```

### Option 3: Install as CLI

Install Obby as a local command:

```zsh
pip install -e .
```

Now you can just run `obby` from anywhere in your terminal!

Then edit:

- `TARGET_FOLDER`: the Obsidian folder to scan.
- `MODEL`: your local Ollama model.
- `TOTAL_WEEKS` and `CURRENT_WEEK`: if you use week-based planning.
- `TASK_TYPE_TAGS`: tags that mean required/stretch/optional/idea/blocked.
- `HEADING_RULES`: headings that imply task type.
- `MODULES`: modules, projects, or workstreams.
- `IGNORE_KEYWORDS`: folders/files to skip.
- `TODO_SOURCE_KEYWORDS`, `ACTIVE_SOURCE_KEYWORDS`, and `ACTIVE_WEEK_SOURCE_PATTERNS`: which notes count as active planning sources.
- `LLM_IDENTITY`, `LLM_MISSION`, and `LLM_STYLE_RULES`: how Ollama should understand Obby and respond.
- `STARTUP_VIEW` and `TASK_VIEW`: compact/full startup and table/card task rendering.

Config priority:

1. CLI args
2. `obby_config.py`
3. environment variables
4. built-in defaults

You can also try Obby on the included sample vault:

```zsh
python obby.py --folder examples/sample-vault/Study --week 2
```

Useful overrides:

```zsh
python obby.py --folder "/path/to/vault/folder"
python obby.py --model llama3.2
python obby.py --week 3
```

## Run

If you installed as a CLI (Option 3):

```zsh
obby
obby --week 4
obby --folder "/path/to/notes"
```

Otherwise, run using the script:

```zsh
python obby.py
```

The prompt supports in-session command history, use Up/Down arrows to move through previous and next commands.

e.g: if you typed /menu and you'd wanna do it again, just press the up button.

If you use week-based planning, run `/week N` once inside Obby. It saves the current week to `.obby/state.json`, so launching plain `obby` later can remember that temporal context without needing `obby --week N` every time.

## Commands

Commands are grouped in the app. Use `/menu` for interactive arrow-key navigation, or filter it to see a table:

```text
/menu daily
/menu tasks
/menu llm
/menu tuning
```

Daily:

- `/dashboard`, `/today` - today's immediate focus (compact by default)
- `/weekly` - current week high-level quest board
- `/draft-weekly` - generate an Obsidian weekly planning draft
- `/overview` - broader project progress overview
- `/candidates` - manual candidate/focus list management

Tasks:

- `/current`, `/behind`, `/upcoming`
- `/quests`, `/stretch`, `/optional`, `/ideas`, `/blocked`, `/unknown`

Broad views:

- `/all-quests`, `/all-stretch`, `/all-optional`, `/all-ideas`, `/all-blocked`, `/all-unknown`

Tuning:

- `/classify` - manually fix a task's kind/week/module
- `/search <keyword>` - search extracted context
- `/debug on/off` - toggle grounded candidate table display
- `/files`, `/context`, `/deadlines`

LLM and presets:

- `/focus`, `/today-plan`, `/weekly-plan`
- `/pick` - choose a local or LLM preset from an up/down menu

`/prompt N` has been removed. Use `/pick` instead so the preset list is visible and less confusing.

Session:

- `/llm status`, `/llm off`, `/llm on` - toggle Ollama features
- `/week N`, `/state`, `/summary`, `/refresh`, `/clear`, `/exit`

Compatibility aliases are intentionally kept small: `/today`, `/todos`, `/ai`, `/help`, and `/quit`.

Long task lists are paged in an interactive terminal. Use Left/Right arrows to move between pages and Enter/Esc to close the browser.

## Screenshots / GIFs

README files can show images and GIFs directly:

```md
![Obby dashboard](docs/assets/obby-dashboard.gif)
```

For videos, the usual GitHub-friendly approach is to use a screenshot or GIF as a thumbnail and link it to the video.

## Task Scope And Candidates

Obby still scans the target folder for context, but dashboards and focus candidates now use `TODO_SOURCE_KEYWORDS` from `obby_config.py`. This keeps old module notes, project ideas, and random historical checklists from flooding the daily view.

Active/current views are configurable too. Obby does not require everyone to name notes the same way.

`ACTIVE_SOURCE_KEYWORDS` marks files/folders that are always relevant, while `ACTIVE_WEEK_SOURCE_PATTERNS` tells Obby how to recognize the current week from a path.
Use `{week}` where the current week number should go.

Run `/candidates` to see which rules are active and what Obby currently thinks the candidate task list is. In an interactive terminal, `/candidates` also lets you browse candidates with paging, pin a task into the candidate list, remove a candidate locally, restore removed candidates, or clear candidate edits.

Candidate edits are stored in `.obby/state.json`. They do not edit Obsidian as of now..

## Daily vs. Weekly Focus

Obby distinguishes between your immediate tasks and your weekly goals:

- **Daily View**: Shows tasks specifically for today (from "Today.md", "Daily.md", or tagged `#today`).
- **Dashboard / Compact View**: Shows a quieter snapshot of current, behind, blocked, and unknown tasks.
- **Weekly View**: Shows the broader rundown of required tasks for your current cycle, plus behind/upcoming/blocked/stretch lanes.

## Weekly Drafting

Use `/draft-weekly` to generate a fresh weekly note draft. Obby will ask you to
paste a progress update, then use your extracted context to suggest a strategy,
list carried-over work, and build a daily flow.

Drafts can be:

- Previewed in the terminal.
- Regenerated with new instructions.
- Saved locally to `.obby/drafts/` for you to copy into Obsidian.

## How The LLM Is Used

Obby is deterministic first, meaning most of things are actually just based on patterns and classifying the patterns through code.

The scanner finds tasks, tags, headings, source files, and line numbers, the classifier applies your configured rules, then progress is computed from those classified tasks.

The LLM identity is also configurable in `obby_config.py`, because otherwise local models can start acting like a generic assistant instead of knowing that it is Obby.

```python
LLM_IDENTITY = "You are Obby, a local-first terminal command center for Obsidian notes."
LLM_MISSION = "Help the user inspect real Markdown tasks and plan next actions from extracted note context."
LLM_STYLE_RULES = [
    "Use the name Obby when referring to yourself.",
    "Cite source files for task recommendations.",
    "Do not invent tasks, deadlines, chores, or study material.",
]
```

The LLM is used for softer work:

- choosing between extracted tasks
- generating a weekly planning draft
- wording a daily or weekly plan
- answering questions about the scanned context

For `/focus`, `/today-plan`, and `/weekly-plan`, Obby sends the model a short list of real candidate tasks. The model is told to choose only from that list. To ensure a better answer, the model now includes a **"Thinking"** section where it explains its strategy before giving recommendations. This keeps the assistant useful without letting it invent work or hallucinate.

You can toggle candidate tables for grounded commands using `/debug on`.

You can disable all Ollama-backed behavior inside Obby:

```text
/llm off
```

When LLM features are off, local commands like `/dashboard`, `/current`, `/quests`,
the local "List pending TODOs" preset in `/pick`, `/search`, and `/classify` still work. Free-text chat, `/focus`, `/today-plan`, `/weekly-plan`, and LLM-backed presets are blocked until you run `/llm on`. The setting is remembered in `.obby/state.json`.

If I'm being honest, I have not actually tested out the LLM, I just know that it runs but I have not used it enough to determine if it's good enough. I welcome pull requests if there's anything that can enhance this portion, but for now its still in a very rough stage.

## Testing

Run the test script:

```bash
sh scripts/test.sh
```

It runs:

```bash
python -m compileall obby.py obby_core
python -m unittest discover -s tests
```

## Docs

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Note Conventions](docs/note-conventions.md) (Good to follow)

## Current Limitations

- Obby expects Markdown files and checkbox tasks.
- Setup is still manual through `obby_config.py`.
- Manual classification is memory-only for now.
- Obsidian write-back is not implemented yet.
