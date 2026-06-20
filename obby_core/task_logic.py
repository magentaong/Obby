from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TypeVar

from .models import AppConfig, Task, TaskKind

T = TypeVar("T", bound=Task)

def render_week_pattern(pattern: str, week: int) -> str:
    try:
        # Prefer .format() if placeholders exist
        return pattern.format(week=week)
    except (IndexError, KeyError):
        # Fallback to direct replacement for robustness
        return pattern.replace("{week}", str(week))


def infer_week_from_path(path_text: str, config: AppConfig) -> int | None:
    """Extracts a week number from a path string based on config patterns."""
    lowered = path_text.lower()
    for pattern in config.active_week_source_patterns:
        if "{week}" not in pattern:
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match and match.groups():
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass
            continue

        # Use regex to capture the digits where {week} would be
        regex_pattern = pattern.replace("{week}", r"(\d+)")
        match = re.search(regex_pattern, lowered, re.IGNORECASE)
        if match:
            try:
                val = int(match.group(1))
                if 1 <= val <= config.total_weeks:
                    return val
            except (ValueError, IndexError):
                pass
    return None


def is_todo_source(task: Task, config: AppConfig) -> bool:
    path_text = str(task.source_file).lower()
    return any(kw.lower() in path_text for kw in config.todo_source_keywords)


def is_active_source(path_text: str, config: AppConfig, week: int) -> bool:
    lowered = path_text.lower()
    
    # Check fixed active keywords
    if any(kw.lower() in lowered for kw in config.active_source_keywords):
        return True
        
    # Check dynamic week-based patterns
    for pattern in config.active_week_source_patterns:
        if "{week}" not in pattern:
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match and match.groups():
                return int(match.group(1)) == week
            continue

        if re.search(render_week_pattern(pattern, week), lowered, re.IGNORECASE):
            return True
    return False


def is_active_task(task: Task, config: AppConfig, week: int) -> bool:
    if task.week == week:
        return True
        
    return task.week is None and is_active_source(str(task.source_file), config, week)


def task_relevance_key(task: Task, config: AppConfig, week: int) -> tuple[int, int, str, int]:
    """Generates a sorting tuple to prioritize tasks by relevance."""
    if task.week == week:
        bucket = 0  # This week exactly
    elif task.week is None and is_active_source(str(task.source_file), config, week):
        bucket = 1  # Active file, untagged
    elif task.week and task.week > week:
        bucket = 2  # Future work
    elif task.week and task.week < week:
        bucket = 3  # Past work (overdue)
    else:
        bucket = 4  # Generic/backlog

    sort_week = task.week if task.week is not None else 999
    return (bucket, sort_week, task.source_file.name, task.line_number)


def sort_tasks(tasks: Iterable[T], config: AppConfig, week: int) -> list[T]:
    """Sorts tasks by relevance bucket, then by date/location."""
    return sorted(tasks, key=lambda t: task_relevance_key(t, config, week))


def filter_kind(tasks: Iterable[Task], kind: TaskKind) -> list[Task]:
    return [t for t in tasks if kind in t.all_kinds]


def active_kind_tasks(tasks: Iterable[Task], config: AppConfig, week: int, kind: TaskKind) -> list[Task]:
    filtered = [t for t in tasks if kind in t.all_kinds and is_active_task(t, config, week)]
    return sort_tasks(filtered, config, week)

# TODO: use config to set this instead of hardcoding, also figure out why #urgent does not work but #today does.
# ./dashboard and ./today does not display the dashboard for the day/week
# should figure out how to customise this so its not as frustrating
def is_today_task(task: Task, config: AppConfig, week: int) -> bool:
    # 1. Explicit #today or #daily or #urgent tags
    if any(t.lower().strip() in {"#today", "#daily", "#urgent"} for t in task.tags):
        return True
        
    # 2. Formally classified as URGENT
    if TaskKind.URGENT in task.all_kinds:
        return True

    # 3. Source file is a 'Today' note (e.g., Today.md, 2026-06-06.md)
    # We check if the source filename contains 'today' or 'daily'
    # or matches a date pattern (basic check)
    filename = task.source_file.name.lower()
    if "today" in filename or "daily" in filename:
        return True
        
    # 3. Handle specific active sources like 'Inbox' as today's tasks if they are active
    # but only if they don't have a future week tag.
    if "inbox" in filename and (task.week is None or task.week <= week):
        return True

    return False


def today_tasks(tasks: Iterable[Task], config: AppConfig, week: int) -> list[Task]:
    """Tasks specifically scoped for today's immediate focus."""
    filtered = [
        t for t in tasks 
        if (TaskKind.REQUIRED in t.all_kinds or TaskKind.URGENT in t.all_kinds) 
        and is_active_task(t, config, week) 
        and is_today_task(t, config, week)
    ]
    return sort_tasks(filtered, config, week)


def behind_tasks(tasks: Iterable[Task], config: AppConfig, week: int) -> list[Task]:
    """Helper for required/urgent TODOs and scheduled ideas from previous weeks, or tasks marked #backlog."""
    filtered = [
        t for t in tasks
        if (
            # Case 1: Overdue based on week
            ((TaskKind.REQUIRED in t.all_kinds or TaskKind.URGENT in t.all_kinds or TaskKind.IDEA in t.all_kinds) 
             and t.week is not None and t.week < week)
            # Case 2: Explicitly marked as #backlog
            or any("backlog" in tag.lower() for tag in t.tags)
        )
    ]
    return sort_tasks(filtered, config, week)


def current_tasks(tasks: Iterable[Task], config: AppConfig, week: int) -> list[Task]:
    """Helper for current week's required/urgent TODOs and scheduled ideas."""
    filtered = [
        t for t in tasks
        if (
            # REQUIRED or URGENT are always "current" if active
            (TaskKind.REQUIRED in t.all_kinds or TaskKind.URGENT in t.all_kinds)
            # IDEA is only current if explicitly scheduled for this week
            or (TaskKind.IDEA in t.all_kinds and t.week == week)
        )
        and is_active_task(t, config, week)
    ]
    return sort_tasks(filtered, config, week)


def upcoming_tasks(tasks: Iterable[Task], config: AppConfig, week: int) -> list[Task]:
    """Helper for required/urgent TODOs and scheduled ideas in future weeks."""
    filtered = [
        t for t in tasks
        if (TaskKind.REQUIRED in t.all_kinds or TaskKind.URGENT in t.all_kinds or TaskKind.IDEA in t.all_kinds)
        and t.week is not None and t.week > week
    ]
    return sort_tasks(filtered, config, week)

def scoped_tasks(tasks: Iterable[Task], config: AppConfig) -> list[Task]:
    return [t for t in tasks if is_todo_source(t, config)]
