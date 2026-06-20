from __future__ import annotations

import os
import time
from pathlib import Path

import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.align import Align
from rich.box import HEAVY_EDGE, ROUNDED, SIMPLE
from rich.console import Console
from rich.console import Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from .models import AppConfig, NoteContext, ProgressSummary, Task, TaskKind

from .commands import (
    CATEGORY_ALIASES,
    CATEGORY_ORDER,
    COMMANDS,
    commands_by_category,
    resolve_category,
)


def select_menu_category() -> str | None:
    choices = [questionary.Choice(title=cat, value=cat) for cat in CATEGORY_ORDER]
    choices.append(questionary.Choice(title="[ show all ]", value="all"))
    choices.append(questionary.Choice(title="[ cancel ]", value="cancel"))
    return questionary.select("Command Center", choices=choices).ask()


def select_command(category: str | None = None) -> str | None:
    if category == "all" or category is None:
        cmds = list(COMMANDS)
        title = "All Commands"
    else:
        grouped = commands_by_category()
        cmds = grouped.get(category, [])
        title = f"{category} Commands"

    if not cmds:
        return None

    choices = [
        questionary.Choice(
            title=f"{cmd.command:18} // {cmd.description}", value=cmd.command
        )
        for cmd in cmds
    ]
    choices.append(questionary.Choice(title="[ back ]", value="back"))
    return questionary.select(title, choices=choices).ask()


console = Console()
_prompt_session = PromptSession(
    history=InMemoryHistory(),
    auto_suggest=AutoSuggestFromHistory(),
    style=Style.from_dict(
        {
            "prompt.user": "bold ansimagenta",
            "prompt.host": "ansibrightmagenta",
            "prompt.arrow": "ansibrightblack",
        }
    ),
)

KIND_STYLES = {
    TaskKind.REQUIRED: "bright_green",
    TaskKind.URGENT: "bright_red",
    TaskKind.STRETCH: "cyan",
    TaskKind.OPTIONAL: "yellow",
    TaskKind.IDEA: "bright_magenta",
    TaskKind.BLOCKED: "bright_red",
    TaskKind.UNKNOWN: "grey70",
}


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def banner(config: AppConfig) -> None:
    title = Text()
    title.append(config.app_name.upper(), style="bold bright_magenta")
    title.append(" // ", style="grey50")
    title.append(config.subtitle.upper(), style="bold cyan")
    logo = r"""
 ██████╗ ██████╗ ██████╗ ██╗   ██╗
██╔═══██╗██╔══██╗██╔══██╗╚██╗ ██╔╝
██║   ██║██████╔╝██████╔╝ ╚████╔╝
██║   ██║██╔══██╗██╔══██╗  ╚██╔╝
╚██████╔╝██████╔╝██████╔╝   ██║
 ╚═════╝ ╚═════╝ ╚═════╝    ╚═╝
"""
    content = Text(logo, style="bright_magenta")
    content.append("\n")
    content.append("LOCAL PLANNING INTERFACE", style="bold cyan")
    content.append("\n")
    content.append(config.tagline, style="grey70")
    console.print()
    console.print(
        Panel(
            Align.center(content),
            title=title,
            subtitle="[grey62]private notes in / local model out[/grey62]",
            border_style="bright_magenta",
            box=HEAVY_EDGE,
        )
    )
    console.print()


def boot(config: AppConfig, ctx: NoteContext, week: int) -> None:
    steps = [
        ("CORE", "System", "Online"),
        ("VAULT", str(config.target_folder), "Vault Linked"),
        ("MODEL", config.model, "Model Online"),
        ("SCAN", f"{len(ctx.files_used)} files / {len(ctx.tasks)} open tasks", "Read-only scan complete"),
        ("WEEK", f"{week}/{config.total_weeks}", "Quest board ready"),
    ]
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(justify="right", style="bold bright_magenta", no_wrap=True)
    table.add_column(style="grey82", ratio=1)
    table.add_column(justify="right", style="bright_green", no_wrap=True)
    for tag, detail, state in steps:
        table.add_row(f"[ {tag} ]", detail, state)
        if console.is_terminal:
            time.sleep(0.04)
    console.print()
    console.print(
        Panel(
            table,
            title="[cyan]DIAGNOSTICS[/cyan]",
            subtitle="[grey62]all Obsidian access remains read-only[/grey62]",
            border_style="cyan",
            box=ROUNDED,
        )
    )
    console.print()


def compact_boot(config: AppConfig, ctx: NoteContext, week: int) -> None:
    info(f"App: [bold bright_magenta]{config.app_name}[/bold bright_magenta] | Week: [cyan]{week}/{config.total_weeks}[/cyan] | Model: [grey82]{config.model}[/grey82]")
    info(f"Vault: [grey82]{config.target_folder}[/grey82] | Files: [cyan]{len(ctx.files_used)}[/cyan] | Tasks: [cyan]{len(ctx.tasks)}[/cyan]")


def command_menu(config: AppConfig, category_filter: str | None = None) -> None:
    console.print()
    resolved_filter = resolve_category(category_filter)
    
    # If filter is 'all', we set it to None to show all
    if category_filter and category_filter.lower() == "all":
        resolved_filter = None
    elif not category_filter:
        # Default /menu behavior: show compact categories first
        console.print(
            Rule(
                f"[bright_magenta]{config.app_name.upper()} COMMAND CENTER[/bright_magenta]",
                style="bright_magenta",
            )
        )
        info("Available command categories. Use /menu <category> or /menu all.")
        cat_table = Table(box=SIMPLE, show_header=False)
        cat_table.add_column("Category", style="bold cyan")
        cat_table.add_column("Aliases", style="grey62")
        for cat in CATEGORY_ORDER:
            aliases = [k for k, v in CATEGORY_ALIASES.items() if v == cat and k != cat.lower()]
            cat_table.add_row(cat, ", ".join(aliases) or "-")
        console.print(cat_table)
        console.print()
        return

    console.print(
        Rule(
            f"[bright_magenta]{config.app_name.upper()} COMMAND CENTER[/bright_magenta]",
            style="bright_magenta",
        )
    )
    grouped = commands_by_category()
    for category in CATEGORY_ORDER:
        if resolved_filter and category != resolved_filter:
            continue
        commands = grouped.get(category, [])
        if not commands:
            continue
        table = Table(
            title=category,
            border_style="cyan" if category != "LLM" else "bright_magenta",
            show_lines=False,
            box=ROUNDED,
            header_style="bold bright_magenta",
        )
        table.add_column("Command", style="bold cyan", no_wrap=True)
        table.add_column("Mode", style="bright_green", no_wrap=True)
        table.add_column("Action", style="grey82")
        table.add_column("Aliases", style="grey62")
        for command in commands:
            table.add_row(
                command.command,
                command.mode,
                command.description,
                ", ".join(command.aliases) or "-",
            )
        console.print(table)
    console.print()


def dashboard(config: AppConfig, ctx: NoteContext, summary: ProgressSummary, week: int) -> None:
    header = Table.grid(expand=True)
    header.add_column(ratio=2)
    header.add_column(ratio=1)
    identity = (
        f"[bold bright_magenta]{config.app_name}[/bold bright_magenta]\n"
        f"[cyan]{config.subtitle}[/cyan]\n"
        f"[grey70]{config.use_case} mode | Week {week}/{config.total_weeks} | {len(ctx.files_used)} files[/grey70]"
    )
    signal = (
        "[bright_green]SYSTEM STATUS[/bright_green]\n"
        "[grey82]Obsidian read-only[/grey82]\n"
        "[grey70]LLM constrained to extracted notes[/grey70]"
    )
    header.add_row(identity, signal)
    console.print()
    console.print(
        Panel(
            header,
            title="[bright_magenta]OPS OVERVIEW[/bright_magenta]",
            subtitle="[grey62]deterministic scanner controls the mission board[/grey62]",
            border_style="bright_magenta",
            box=HEAVY_EDGE,
        )
    )
    console.print()

    tiles = Table.grid(expand=True)
    tiles.add_column(ratio=1)
    tiles.add_column(ratio=1)
    tiles.add_column(ratio=1)
    tiles.add_column(ratio=1)
    tiles.add_row(
        metric_tile("CORE", f"{summary.required_done}/{summary.required_total}", "bright_green"),
        metric_tile("BEHIND", str(len(summary.behind)), "bright_red"),
        metric_tile("CURRENT", str(len(summary.current)), "cyan"),
        metric_tile("UNKNOWN", str(summary.unknown_total), "grey82"),
    )
    console.print(tiles)
    console.print()

    bars = Table.grid(padding=(0, 2), expand=True)
    bars.add_column(style="bold")
    bars.add_column(ratio=1)
    bars.add_column(justify="right", style="grey82")
    bars.add_row(
        "[bright_green]Core[/bright_green]",
        ProgressBar(total=max(summary.required_total, 1), completed=summary.required_done, pulse=False),
        f"{summary.required_done}/{summary.required_total}",
    )
    bars.add_row(
        "[cyan]Bonus[/cyan]",
        ProgressBar(total=max(summary.stretch_total, 1), completed=summary.stretch_done, pulse=False),
        f"{summary.stretch_done}/{summary.stretch_total}",
    )
    console.print(
        Panel(
            bars,
            title="[bright_magenta]PROGRESS[/bright_magenta]",
            border_style="bright_green",
            box=ROUNDED,
        )
    )
    console.print()

    telemetry = Table(
        title="Quest Telemetry",
        border_style="cyan",
        box=ROUNDED,
        show_header=True,
        header_style="bold bright_magenta",
    )
    telemetry.add_column("Lane", style="grey70")
    telemetry.add_column("Signal", style="bold")
    telemetry.add_column("Meaning", style="grey82")
    telemetry.add_row("Required", f"[bright_green]{summary.required_done}/{summary.required_total}[/bright_green]", "core progress")
    telemetry.add_row("Stretch", f"[cyan]{summary.stretch_done}/{summary.stretch_total}[/cyan]", "bonus progress")
    telemetry.add_row("Blocked", f"[bright_red]{summary.blocked_total}[/bright_red]", "tracked separately")
    telemetry.add_row("Upcoming", f"[cyan]{len(summary.upcoming)}[/cyan]", "future required work")
    console.print(telemetry)
    console.print()


def compact_dashboard(
    config: AppConfig,
    week: int,
    current: list[Task],
    behind: list[Task],
    blocked: list[Task],
    unknown: list[Task],
) -> None:
    console.print()
    summary = Text()
    summary.append(f"{config.app_name.upper()}", style="bold bright_magenta")
    summary.append(f" | Week {week}", style="cyan")
    summary.append(f" | {config.model}", style="grey62")
    console.print(Panel(summary, border_style="bright_magenta", box=SIMPLE))

    metrics = Table.grid(expand=True)
    metrics.add_column(ratio=1)
    metrics.add_column(ratio=1)
    metrics.add_column(ratio=1)
    metrics.add_column(ratio=1)
    metrics.add_row(
        f"[bright_green]Current:[/bright_green] {len(current)}",
        f"[bright_red]Behind:[/bright_red] {len(behind)}",
        f"[yellow]Blocked:[/yellow] {len(blocked)}",
        f"[grey70]Unknown:[/grey70] {len(unknown)}",
    )
    console.print(metrics)
    console.print()

    if current:
        task_table("Next Suggested Tasks", current, limit=3, view_mode="table")
    elif behind:
        task_table("Next Suggested Tasks (Behind)", behind, limit=3, view_mode="table")
    else:
        info("No immediate tasks suggested. Try /quests or /refresh.")


def today_dashboard(
    config: AppConfig,
    week: int,
    current: list[Task],
    blocked: list[Task],
    behind: list[Task],
    unknown: list[Task],
    view_mode: str = "table",
) -> None:
    # header = Table.grid(expand=True)
    # header.add_column(ratio=2)
    # header.add_column(ratio=1)
    # header.add_row(
    #     (
    #         f"[bold bright_magenta]Today[/bold bright_magenta]\n"
    #         f"[cyan]Week {week}/{config.total_weeks}[/cyan]\n"
    #         "[grey70]scoped to configured TODO sources[/grey70]"
    #     ),
    #     (
    #         "[bright_green]LOCAL STATUS[/bright_green]\n"
    #         f"[grey82]{len(current)} current / {len(behind)} behind[/grey82]\n"
    #         f"[grey70]{len(blocked)} blocked / {len(unknown)} unknown[/grey70]"
    #     ),
    # )
    # console.print()
    # console.print(
    #     Panel(
    #         header,
    #         title="[bright_magenta]TODAY DECK[/bright_magenta]",
    #         border_style="bright_magenta",
    #         box=HEAVY_EDGE,
    #     )
    # )
    # console.print()
    
    tiles = Table.grid(expand=True)
    tiles.add_column(ratio=1)
    tiles.add_column(ratio=1)
    tiles.add_column(ratio=1)
    tiles.add_column(ratio=1)
    tiles.add_row(
        metric_tile("CURRENT", str(len(current)), "bright_green"),
        metric_tile("BEHIND", str(len(behind)), "bright_red"),
        metric_tile("BLOCKED", str(len(blocked)), "yellow"),
        metric_tile("UNKNOWN", str(len(unknown)), "grey82"),
    )
    console.print(tiles)
    console.print()

    task_table("Current Week Required", current, limit=6, view_mode=view_mode)
    if blocked:
        task_table("Blocked", blocked, limit=4, view_mode=view_mode)
    if behind:
        task_table("Behind, But Not First", behind, limit=4, view_mode=view_mode)
    if unknown:
        task_table("Needs Classification", unknown, limit=4, view_mode=view_mode)


def weekly_dashboard(
    config: AppConfig,
    week: int,
    current: list[Task],
    behind: list[Task],
    upcoming: list[Task],
    blocked: list[Task],
    stretch: list[Task],
    view_mode: str = "table",
) -> None:
    # header = Table.grid(expand=True)
    # header.add_column(ratio=2)
    # header.add_column(ratio=1)
    # header.add_row(
    #     (
    #         f"[bold bright_magenta]Week {week}[/bold bright_magenta]\n"
    #         f"[cyan]{config.use_case} planning[/cyan]\n"
    #         "[grey70]scoped to configured TODO sources[/grey70]"
    #     ),
    #     (
    #         "[bright_green]WEEK LOCK[/bright_green]\n"
    #         f"[grey82]{len(current)} current / {len(behind)} behind[/grey82]\n"
    #         f"[grey70]{len(upcoming)} upcoming / {len(stretch)} stretch[/grey70]"
    #     ),
    # )
    # console.print()
    # console.print(
    #     Panel(
    #         header,
    #         title="[bright_magenta]WEEKLY DECK[/bright_magenta]",
    #         border_style="bright_magenta",
    #         box=HEAVY_EDGE,
    #     )
    # )
    # console.print()

    lanes = Table(
        title="Week Lanes",
        border_style="cyan",
        box=ROUNDED,
        show_header=True,
        header_style="bold bright_magenta",
    )
    lanes.add_column("Lane", style="grey70")
    lanes.add_column("Count", justify="right", style="bold")
    lanes.add_column("Use", style="grey82")
    lanes.add_row("Current", f"[bright_green]{len(current)}[/bright_green]", "main work for this week")
    lanes.add_row("Behind", f"[bright_red]{len(behind)}[/bright_red]", "older required tasks with explicit week tags")
    lanes.add_row("Upcoming", f"[cyan]{len(upcoming)}[/cyan]", "future required work")
    lanes.add_row("Blocked", f"[yellow]{len(blocked)}[/yellow]", "needs unblock or decision")
    lanes.add_row("Stretch", f"[bright_magenta]{len(stretch)}[/bright_magenta]", "bonus only")
    console.print(lanes)
    console.print()

    task_table("Current Week Required", current, limit=10, view_mode=view_mode)
    if behind:
        task_table("Behind", behind, limit=6, view_mode=view_mode)
    if upcoming:
        task_table("Upcoming", upcoming, limit=6, view_mode=view_mode)
    if blocked:
        task_table("Blocked", blocked, limit=6, view_mode=view_mode)
    if stretch:
        task_table("Stretch", stretch, limit=6, view_mode=view_mode)


def candidate_rules(config: AppConfig, scoped_tasks: list[Task]) -> None:
    table = Table(
        title="Candidate Task Rules",
        border_style="cyan",
        box=ROUNDED,
        show_header=True,
        header_style="bold bright_magenta",
    )
    table.add_column("Setting", style="grey70")
    table.add_column("Value", style="grey93")
    table.add_row("TODO source keywords", ", ".join(config.todo_source_keywords))
    table.add_row("Always-active sources", ", ".join(config.active_source_keywords))
    table.add_row("Active week patterns", ", ".join(config.active_week_source_patterns))
    table.add_row("Allowed kinds", ", ".join(config.candidate_task_kinds))
    table.add_row("Max candidates", str(config.candidate_max_tasks))
    table.add_row("Scoped open tasks", str(len(scoped_tasks)))
    console.print()
    console.print(table)
    console.print()


def select_candidate_action() -> str | None:
    choices = [
        questionary.Choice(title="browse candidates", value="browse"),
        questionary.Choice(title="pin/add a task to candidates", value="pin"),
        questionary.Choice(title="remove a task from candidates", value="remove"),
        questionary.Choice(title="restore a removed task", value="restore"),
        questionary.Choice(title="clear all candidate edits", value="clear"),
        questionary.Choice(title="done", value="done"),
    ]
    return questionary.select("Candidate controls", choices=choices).ask()


def select_removed_candidate(removed: list[tuple[str, Task | None]]) -> str | None:
    if not removed:
        return None
    choices = []
    for key, task in removed:
        if task:
            title = f"{task.source_label} | {task.text[:100]}"
        else:
            title = key
        choices.append(questionary.Choice(title=title, value=key))
    return questionary.select("Restore which removed task?", choices=choices).ask()


def confirm(message: str) -> bool:
    return bool(questionary.confirm(message, default=False).ask())


def metric_tile(label: str, value: str, style: str) -> Panel:
    text = Text()
    text.append(value, style=f"bold {style}")
    text.append("\n")
    text.append(label, style="grey62")
    return Panel(Align.center(text), border_style=style, box=ROUNDED, padding=(0, 1))


def task_table(title: str, tasks: list[Task], limit: int | None = None, view_mode: str = "table") -> None:
    shown = tasks[:limit] if limit else tasks
    if not shown:
        console.print()
        console.print(Panel("[grey70]No tasks found.[/grey70]", title=title, border_style="grey50"))
        console.print()
        return

    if view_mode == "cards":
        _task_cards(title, shown, limit, len(tasks))
    else:
        _task_table(title, shown, limit, len(tasks))


def _task_table(title: str, shown: list[Task], limit: int | None, total: int) -> None:
    table = Table(
        title=title,
        border_style="cyan",
        box=ROUNDED,
        header_style="bold bright_magenta",
        expand=True,
    )
    table.add_column("ID", justify="right", style="grey50", no_wrap=True)
    table.add_column("Kind", style="bold", no_wrap=True)
    table.add_column("Task", style="grey93", ratio=1)
    table.add_column("Module", style="bright_magenta", no_wrap=True)
    table.add_column("Source", style="grey62", no_wrap=True)

    for index, task in enumerate(shown, start=1):
        style = KIND_STYLES.get(task.kind, "grey70")
        
        # Display all kinds if multiple exist
        if len(task.all_kinds) > 1:
            kind_labels = [k.value[:3].upper() for k in task.all_kinds]
            kind_text = " | ".join(kind_labels)
        else:
            kind_text = task.kind.value.upper()

        table.add_row(
            f"{index:02d}",
            Text(kind_text, style=style),
            task.text,
            task.module or "-",
            task.source_label,
        )
    console.print()
    console.print(table)
    if limit and total > limit:
        console.print(f"[grey70]Showing {limit} of {total} tasks.[/grey70]")
    console.print()


def _task_cards(title: str, shown: list[Task], limit: int | None, total: int) -> None:
    cards = []
    for index, task in enumerate(shown, start=1):
        style = KIND_STYLES.get(task.kind, "grey70")
        meta = Text()
        meta.append(f"{index:02d} ", style="grey50")
        meta.append(task.kind.value.upper(), style=f"bold {style}")
        meta.append("  |  ", style="grey35")
        meta.append(f"week {task.week or '-'}", style="cyan")
        meta.append("  |  ", style="grey35")
        meta.append(task.module or "no module", style="bright_magenta")
        meta.append("  |  ", style="grey35")
        meta.append(task.source_label, style="grey62")

        body = Text(task.text, style="grey93")
        if task.heading_label:
            body.append("\n")
            body.append(task.heading_label, style="italic grey62")
        if task.classification_reason:
            body.append("\n")
            body.append(task.classification_reason, style="grey50")

        cards.append(
            Panel(
                body,
                title=meta,
                title_align="left",
                border_style=style,
                box=ROUNDED,
                padding=(0, 1),
            )
        )
        cards.append(Text(""))

    if cards:
        cards.pop()
    console.print()
    console.print(Panel(Group(*cards), title=title, border_style="cyan", padding=(0, 1), box=ROUNDED))
    if limit and total > limit:
        console.print(f"[grey70]Showing {limit} of {total} tasks.[/grey70]")
    console.print()


def task_browser(title: str, tasks: list[Task], page_size: int = 24, view_mode: str = "table") -> None:
    if not tasks:
        task_table(title, tasks, view_mode=view_mode)
        return
    if not console.is_terminal or len(tasks) <= page_size:
        task_table(title, tasks, limit=page_size if len(tasks) > page_size else None, view_mode=view_mode)
        return

    page = 0
    total_pages = max((len(tasks) - 1) // page_size + 1, 1)
    while True:
        clear_screen()
        start = page * page_size
        end = start + page_size
        task_table(f"{title} - Page {page + 1}/{total_pages}", tasks[start:end], view_mode=view_mode)
        action = page_nav_prompt(page, total_pages)
        if action == "next" and page < total_pages - 1:
            page += 1
        elif action == "prev" and page > 0:
            page -= 1
        elif action in {"quit", "enter"}:
            break


def page_nav_prompt(page: int, total_pages: int) -> str:
    bindings = KeyBindings()

    @bindings.add("right")
    def _next(event) -> None:
        event.app.exit(result="next")

    @bindings.add("left")
    def _prev(event) -> None:
        event.app.exit(result="prev")

    @bindings.add("enter")
    def _enter(event) -> None:
        event.app.exit(result="enter")

    @bindings.add("escape")
    def _quit(event) -> None:
        event.app.exit(result="quit")

    @bindings.add("q")
    def _quit_q(event) -> None:
        event.app.exit(result="quit")

    hint = f"Page {page + 1}/{total_pages}  |  Left/Right to page  |  Enter/Esc to close"
    action = PromptSession().prompt(HTML(f'<prompt.arrow>{hint}</prompt.arrow> '), key_bindings=bindings)
    return action if action in {"next", "prev", "enter", "quit"} else "quit"


def select_task(title: str, tasks: list[Task]) -> Task | None:
    if not tasks:
        return None
    choices = [
        questionary.Choice(
            title=f"{task.source_label} | week {task.week or '-'} | {task.kind.value} | {task.text[:100]}",
            value=task,
        )
        for task in tasks
    ]
    return questionary.select(title, choices=choices).ask()


def select_task_kind() -> TaskKind | None:
    choices = [
        questionary.Choice(title="required - core progress / must-do", value=TaskKind.REQUIRED),
        questionary.Choice(title="stretch - bonus work", value=TaskKind.STRETCH),
        questionary.Choice(title="optional - okay to skip", value=TaskKind.OPTIONAL),
        questionary.Choice(title="idea - backlog / future", value=TaskKind.IDEA),
        questionary.Choice(title="blocked - waiting / stuck", value=TaskKind.BLOCKED),
        questionary.Choice(title="unknown - leave unclassified", value=TaskKind.UNKNOWN),
    ]
    return questionary.select("What kind of task is this?", choices=choices).ask()


def select_classify_scope() -> str | None:
    choices = [
        questionary.Choice(title="active week/source tasks", value="active"),
        questionary.Choice(title="unknown tasks", value="unknown"),
        questionary.Choice(title="all unchecked tasks", value="all"),
    ]
    return questionary.select("Which tasks do you want to classify?", choices=choices).ask()


def ask_week(default_week: int | None) -> int | None:
    default = str(default_week) if default_week else ""
    raw = questionary.text("Week number (blank for none)", default=default).ask()
    if raw is None:
        return default_week
    raw = raw.strip()
    if not raw:
        return None
    return int(raw) if raw.isdigit() else default_week


def select_module(config: AppConfig, current_module: str | None) -> str | None:
    choices = [questionary.Choice(title="no module", value=None)]
    for module in config.module_rules:
        label = module.name
        if module.key == current_module:
            label += " (current)"
        choices.append(questionary.Choice(title=label, value=module.key))
    return questionary.select("Module/workstream", choices=choices).ask()


def files_table(files: list[Path]) -> None:
    table = Table(title="Scanned Files", border_style="cyan")
    table.add_column("#", justify="right", style="grey62")
    table.add_column("Path", style="grey82")
    for index, path in enumerate(files, start=1):
        table.add_row(str(index), str(path))
    console.print()
    console.print(table if files else Panel("[red]No files found.[/red]", border_style="red"))
    console.print()


def context_preview(context: str) -> None:
    preview = context[:3000]
    console.print()
    console.print(Panel(preview or "[grey70]No context extracted.[/grey70]", title="Context Preview", border_style="cyan"))
    if len(context) > 3000:
        console.print("[grey70]Preview truncated.[/grey70]")
    console.print()


def assistant_reply(reply: str, title: str = "LLM Recommendation") -> None:
    clean = reply.strip().replace("\\n", "\n")
    console.print()
    console.print(Rule(f"[bright_magenta]{title.upper()}[/bright_magenta]", style="bright_magenta"))
    console.print(
        Panel(
            Text(clean, style="grey93"),
            title=f"[cyan]{title}[/cyan]",
            border_style="bright_magenta",
            box=ROUNDED,
        )
    )
    console.print()


def pick_prompt(config: AppConfig) -> str | None:
    choices = [
        questionary.Choice(title=f"{key}. {name}", value=key)
        for key, (name, _) in config.prompt_presets.items()
    ]
    return questionary.select("Select prompt", choices=choices).ask()


def prompt_text() -> str:
    return _prompt_session.prompt(
        HTML(
            '<prompt.host>OBBY</prompt.host>'
            '<prompt.arrow>::</prompt.arrow>'
            '<prompt.user>cmd</prompt.user>'
            '<prompt.arrow> ❯ </prompt.arrow>'
        )
    )


def error(message: str) -> None:
    console.print()
    console.print(Panel(message, title="[red]FAULT DETECTED[/red]", border_style="red", box=ROUNDED))
    console.print()


def info(message: str) -> None:
    console.print(f"[cyan]//[/cyan] [grey70]{message}[/grey70]")
    console.print()
