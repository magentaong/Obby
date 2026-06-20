from __future__ import annotations

from typing import TYPE_CHECKING

from . import task_logic
from .models import ProgressSummary, TaskKind

if TYPE_CHECKING:
    from .models import AppConfig, NoteContext, Task


def resolve_week(ctx: NoteContext, config: AppConfig) -> int:
    """Resolves the current focus week if not specified, follows patterns that people typically use."""
    if config.current_week is not None:
        return int(config.current_week)

    # Strategy 1: Check active file paths for week patterns
    for path in ctx.files_used:
        week = task_logic.infer_week_from_path(str(path), config)
        if week:
            return week

    # Strategy 2: Use the most recent completed week as context
    checked_weeks = [t.week for t in ctx.completed_tasks if t.week]
    if checked_weeks:
        return max(checked_weeks)

    # Strategy 3: Default to earliest open required/urgent week
    relevant_weeks = [
        t.week for t in ctx.tasks 
        if (TaskKind.REQUIRED in t.all_kinds or TaskKind.URGENT in t.all_kinds) and t.week
    ]
    if relevant_weeks:
        return min(relevant_weeks)

    return 1  # as deafult


def summarize_progress(ctx: NoteContext, current_week: int) -> ProgressSummary:
    summary = ProgressSummary()

    # Tally metrics across the entire context
    for task in ctx.all_tasks:
        _tally_task(task, summary)

    # Lane filtering for the active dashboard
    # Note: This summary lane logic should ideally be kept in sync with task_logic.py
    for task in ctx.tasks:
        # We only summarize tasks that have a required-level classification
        if not (TaskKind.REQUIRED in task.all_kinds or TaskKind.URGENT in task.all_kinds or TaskKind.IDEA in task.all_kinds):
            continue

        is_backlog = any("backlog" in tag.lower() for tag in task.tags)
        
        # Behind check
        if is_backlog or (task.week is not None and task.week < current_week):
            summary.behind.append(task)
        
        # Current check
        if (TaskKind.REQUIRED in task.all_kinds or TaskKind.URGENT in task.all_kinds) or (TaskKind.IDEA in task.all_kinds and task.week == current_week):
             # For summary, we only count it as 'current' if it's not strictly backlog or old
             if not is_backlog and (task.week is None or task.week == current_week):
                 summary.current.append(task)
        
        # Upcoming check
        if task.week is not None and task.week > current_week and not is_backlog:
            summary.upcoming.append(task)

    return summary


def _tally_task(task: Task, summary: ProgressSummary) -> None:
    # Use all_kinds to tally, prioritized by importance
    if TaskKind.URGENT in task.all_kinds or TaskKind.REQUIRED in task.all_kinds:
        summary.required_total += 1
        if task.checked:
            summary.required_done += 1
    elif TaskKind.STRETCH in task.all_kinds:
        summary.stretch_total += 1
        if task.checked:
            summary.stretch_done += 1
    elif TaskKind.OPTIONAL in task.all_kinds:
        summary.optional_total += 1
    elif TaskKind.IDEA in task.all_kinds:
        summary.idea_total += 1
    elif TaskKind.BLOCKED in task.all_kinds:
        summary.blocked_total += 1
    elif TaskKind.UNKNOWN in task.all_kinds and not task.checked:
        summary.unknown_total += 1
