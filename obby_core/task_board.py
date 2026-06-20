from __future__ import annotations

import hashlib

from . import task_logic
from .models import AppConfig, NoteContext, Task, TaskKind
from .state import LocalState


def task_state_key(task: Task) -> str:
    """Returns alocal-state key for a task across refreshes."""
    raw = f"{task.source_file}|{task.line_number}|{task.text}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{task.source_file.name}:{task.line_number}:{digest}"


class TaskBoard:
    """Query layer for scoped, active, and candidate task views."""

    def __init__(self, ctx: NoteContext, config: AppConfig, week: int, state: LocalState) -> None:
        self.ctx = ctx
        self.config = config
        self.week = week
        self.state = state

    def todo_scope_context(self) -> NoteContext:
        return NoteContext(
            target_folder=self.ctx.target_folder,
            tasks=self.todo_scope_tasks(),
            completed_tasks=[
                task for task in self.ctx.completed_tasks if self.is_todo_source(task)
            ],
            deadlines=self.ctx.deadlines,
            weekly_items=self.ctx.weekly_items,
            module_outlines=self.ctx.module_outlines,
            general_context=self.ctx.general_context,
            files_used=self.ctx.files_used,
            raw_chunks=self.ctx.raw_chunks,
            errors=self.ctx.errors,
        )

    def todo_scope_tasks(self) -> list[Task]:
        return task_logic.scoped_tasks(self.ctx.tasks, self.config)

    def filter_scoped(self, kind: TaskKind) -> list[Task]:
        return task_logic.filter_kind(self.todo_scope_tasks(), kind)

    def active_kind_tasks(self, kind: TaskKind) -> list[Task]:
        return task_logic.active_kind_tasks(self.todo_scope_tasks(), self.config, self.week, kind)

    def today_tasks(self) -> list[Task]:
        return task_logic.today_tasks(self.todo_scope_tasks(), self.config, self.week)

    def current_tasks(self) -> list[Task]:
        return task_logic.current_tasks(self.todo_scope_tasks(), self.config, self.week)

    def behind_tasks(self) -> list[Task]:
        return task_logic.behind_tasks(self.todo_scope_tasks(), self.config, self.week)

    def upcoming_tasks(self) -> list[Task]:
        return task_logic.upcoming_tasks(self.todo_scope_tasks(), self.config, self.week)

    def sorted_tasks(self, tasks: list[Task]) -> list[Task]:
        return task_logic.sort_tasks(tasks, self.config, self.week)

    def task_relevance_key(self, task: Task) -> tuple[int, int, str, int]:
        return task_logic.task_relevance_key(task, self.config, self.week)

    def is_active_task(self, task: Task) -> bool:
        return task_logic.is_active_task(task, self.config, self.week)

    def is_active_source(self, path_text: str) -> bool:
        return task_logic.is_active_source(path_text, self.config, self.week)

    def is_todo_source(self, task: Task) -> bool:
        return task_logic.is_todo_source(task, self.config)

    def pending_todos(self) -> list[Task]:
        allowed = {kind.lower() for kind in self.config.candidate_task_kinds}
        allowed.add(TaskKind.UNKNOWN.value)
        allowed.add(TaskKind.URGENT.value)
        return self.sorted_tasks([
            task
            for task in self.todo_scope_tasks()
            if self.is_active_task(task) and any(k.value in allowed for k in task.all_kinds)
        ])

    def candidate_tasks(self) -> list[Task]:
        scoped = self.todo_scope_tasks()
        scoped_by_key = {task_state_key(task): task for task in scoped}
        pinned_keys = self.state.get_list("candidate_pins")
        excluded_keys = set(self.state.get_list("candidate_exclusions"))
        allowed_kinds = {kind.lower() for kind in self.config.candidate_task_kinds}
        allowed_kinds.add(TaskKind.URGENT.value)

        active_no_week = [
            task
            for task in scoped
            if task.week is None
            and any(k.value in allowed_kinds for k in task.all_kinds)
            and self.is_active_source(str(task.source_file))
        ]
        pinned = [
            scoped_by_key[key]
            for key in pinned_keys
            if key in scoped_by_key and key not in excluded_keys
        ]
        
        # Collect tasks from relevant lanes
        ordered = self.sorted_tasks([
            *self.current_tasks(),
            *active_no_week,
            *[task for task in scoped if TaskKind.BLOCKED in task.all_kinds],
            *self.behind_tasks(),
            *[task for task in scoped if TaskKind.STRETCH in task.all_kinds],
        ])

        candidates: list[Task] = []
        seen_keys: set[str] = set()
        pinned_task_keys = {task_state_key(task) for task in pinned}
        for task in [*pinned, *ordered]:
            key = task_state_key(task)
            if (
                key in seen_keys
                or task.checked
                or key in excluded_keys
                or (key not in pinned_task_keys and not any(k.value in allowed_kinds for k in task.all_kinds))
            ):
                continue
            seen_keys.add(key)
            candidates.append(task)
        return candidates[: self.config.candidate_max_tasks]
