from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from obby_core.models import AppConfig, NoteContext, Task, TaskKind, Theme
from obby_core.state import LocalState
from obby_core.task_board import TaskBoard, task_state_key


def make_config(folder: Path) -> AppConfig:
    return AppConfig(
        app_name="Obby",
        subtitle="Test",
        tagline="local-first",
        use_case="project",
        vault=None,
        target_folder=folder,
        model="test-model",
        ollama_url="http://localhost:11434/api/chat",
        ollama_tags_url="http://localhost:11434/api/tags",
        total_weeks=8,
        current_week=2,
        module_rules=[],
        task_type_tags={},
        heading_rules={},
        ignore_keywords=[],
        max_lines_per_file=120,
        max_total_context_chars=24000,
        prompt_presets={},
        todo_source_keywords=["Tasks", "Today"],
        active_source_keywords=["Today"],
        active_week_source_patterns=[r"week\s*{week}\b"],
        candidate_task_kinds=["required", "blocked", "stretch"],
        candidate_max_tasks=10,
        theme=Theme(),
        xp_rules={},
    )


def make_task(
    path: str,
    text: str,
    kind: TaskKind,
    week: int | None = None,
    task_id: int = 1,
    line: int = 1,
) -> Task:
    return Task(
        id=task_id,
        text=text,
        source_file=Path(path),
        line_number=line,
        checked=False,
        week=week,
        kind=kind,
    )


class TaskBoardTests(unittest.TestCase):
    def test_candidate_tasks_deduplicate_by_stable_key_not_scan_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = make_config(Path(tmp))
            state = LocalState(Path(tmp) / "state.json")
            ctx = NoteContext(
                target_folder=Path(tmp),
                tasks=[
                    make_task("Today.md", "Do current task", TaskKind.REQUIRED, week=2, task_id=1, line=3),
                    make_task("Week 2 Tasks.md", "Do second task", TaskKind.REQUIRED, week=2, task_id=1, line=4),
                ],
            )

            board = TaskBoard(ctx, config, week=2, state=state)

            self.assertEqual([task.text for task in board.candidate_tasks()], ["Do current task", "Do second task"])

    def test_candidate_exclusions_remove_tasks_without_touching_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = make_config(Path(tmp))
            state = LocalState(Path(tmp) / "state.json")
            remove_me = make_task("Today.md", "Remove locally", TaskKind.REQUIRED, week=2, line=3)
            keep_me = make_task("Today.md", "Keep visible", TaskKind.REQUIRED, week=2, line=4)
            ctx = NoteContext(target_folder=Path(tmp), tasks=[remove_me, keep_me])
            state.add_to_list("candidate_exclusions", task_state_key(remove_me))

            board = TaskBoard(ctx, config, week=2, state=state)

            self.assertEqual([task.text for task in board.candidate_tasks()], ["Keep visible"])

    def test_pinned_candidate_can_promote_allowed_backlog_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = make_config(Path(tmp))
            state = LocalState(Path(tmp) / "state.json")
            current = make_task("Today.md", "Current", TaskKind.REQUIRED, week=2, line=3)
            backlog = make_task("Archive Tasks.md", "Pinned backlog", TaskKind.STRETCH, week=None, line=8)
            ctx = NoteContext(target_folder=Path(tmp), tasks=[current, backlog])
            state.add_to_list("candidate_pins", task_state_key(backlog))

            board = TaskBoard(ctx, config, week=2, state=state)

            self.assertEqual([task.text for task in board.candidate_tasks()], ["Pinned backlog", "Current"])

    def test_task_state_key_uses_sha256_sized_digest(self) -> None:
        task = make_task("Today.md", "Stable", TaskKind.REQUIRED, week=2)

        digest = task_state_key(task).split(":")[-1]

        self.assertEqual(len(digest), 12)
        self.assertEqual(digest, task_state_key(task).split(":")[-1])


if __name__ == "__main__":
    unittest.main()
