from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .models import ProgressSummary, TaskKind

if TYPE_CHECKING:
    from .models import AppConfig, NoteContext, Task


def resolve_week(ctx: NoteContext, config: AppConfig) -> int:
    """Resolves the current focus week if not specified, follows patterns that people typically use."""
    if config.current_week is not None:
        return int(config.current_week)

    # Strategy 1: Check active file paths for week patterns
    for path in ctx.files_used:
        path_text = str(path)
        for pattern in config.active_week_source_patterns:
            if "{week}" not in pattern:
                match = re.search(pattern, path_text, re.IGNORECASE)
                if match and match.groups():
                    week = int(match.group(1))
                    if 1 <= week <= config.total_weeks:
                        return week
                continue

            for week in range(1, config.total_weeks + 1):
                try:
                    rendered = pattern.format(week=week)
                except (IndexError, KeyError):
                    rendered = pattern.replace("{week}", str(week))
                if re.search(rendered, path_text, re.IGNORECASE):
                    return week

    # Strategy 2: Use the most recent completed week as context
    checked_weeks = [t.week for t in ctx.completed_tasks if t.week]
    if checked_weeks:
        return max(checked_weeks)

    # Strategy 3: Default to earliest open required week
    required_weeks = [t.week for t in ctx.tasks if t.kind == TaskKind.REQUIRED and t.week]
    if required_weeks:
        return min(required_weeks)

    return 1  # as deafult


def summarize_progress(ctx: NoteContext, current_week: int) -> ProgressSummary:
    summary = ProgressSummary()

    # Tally metrics across the entire context
    for task in ctx.all_tasks:
        _tally_task(task, summary)

    # Lane filtering for the active dashboard
    for task in ctx.tasks:
        if task.kind == TaskKind.REQUIRED and task.week:
            if task.week < current_week:
                summary.behind.append(task)
            elif task.week == current_week:
                summary.current.append(task)
            else:
                summary.upcoming.append(task)

    return summary


def _tally_task(task: Task, summary: ProgressSummary) -> None:
    if task.kind == TaskKind.REQUIRED:
        summary.required_total += 1
        if task.checked:
            summary.required_done += 1
    elif task.kind == TaskKind.STRETCH:
        summary.stretch_total += 1
        if task.checked:
            summary.stretch_done += 1
    elif task.kind == TaskKind.OPTIONAL:
        summary.optional_total += 1
    elif task.kind == TaskKind.IDEA:
        summary.idea_total += 1
    elif task.kind == TaskKind.BLOCKED:
        summary.blocked_total += 1
    elif task.kind == TaskKind.UNKNOWN and not task.checked:
        summary.unknown_total += 1
