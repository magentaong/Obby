import unittest
from pathlib import Path
from obby_core.models import Task, TaskKind, AppConfig, NoteContext
from obby_core.classifier import classify_task
from obby_core.progress import resolve_week, summarize_progress
from obby_core import task_logic

class TestLogic(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig(
            app_name="Obby", subtitle="", tagline="", use_case="test",
            vault=None, target_folder=Path("."), model="", ollama_url="",
            ollama_tags_url="", total_weeks=10, current_week=None,
            module_rules=[], 
            task_type_tags={"required": ["#must"], "blocked": ["#stuck"]},
            heading_rules={"stretch": ["Bonus"]},
            ignore_keywords=[], max_lines_per_file=100, max_total_context_chars=1000,
            prompt_presets={},
            active_source_keywords=["Daily"],
            active_week_source_patterns=[r"week-(\d+)"]
        )

    def test_classification_precedence(self):
        """Tags should take precedence over headings."""
        task = Task(id=1, text="Test #must", source_file=Path("x.md"), line_number=1, checked=False, 
                    heading_path=["Bonus"], tags=["#must"])
        classify_task(task, self.config)
        self.assertEqual(task.kind, TaskKind.REQUIRED)

    def test_post_init_all_kinds_default(self):
        """Verifies default behavior of all_kinds on Task."""
        task = Task(id=1, text="Test", source_file=Path("x.md"), line_number=1, checked=False)
        self.assertEqual(task.all_kinds, [TaskKind.UNKNOWN])
        
        task2 = Task(id=2, text="Test", source_file=Path("x.md"), line_number=1, checked=False, kind=TaskKind.STRETCH)
        self.assertEqual(task2.all_kinds, [TaskKind.STRETCH])

    def test_multiple_kinds_classification(self):
        """Verifies that multiple kinds are matched and prioritized correctly."""
        self.config.task_type_tags = {
            "required": ["#must"],
            "stretch": ["#bonus"],
        }
        task = Task(id=1, text="Test #must #bonus", source_file=Path("x.md"), line_number=1, checked=False,
                    tags=["#must", "#bonus"])
        classify_task(task, self.config)
        self.assertEqual(task.kind, TaskKind.REQUIRED)
        self.assertEqual(task.all_kinds, [TaskKind.REQUIRED, TaskKind.STRETCH])


    def test_week_resolution_from_path(self):
        """Verifies week inference from file paths."""
        ctx = NoteContext(target_folder=Path("."))
        ctx.files_used = [Path("Daily/week-7.md")]
        week = resolve_week(ctx, self.config)
        self.assertEqual(week, 7)

    def test_progress_summarization(self):
        """Verifies correct calculation of totals and completion counts."""
        ctx = NoteContext(target_folder=Path("."))
        tasks = [
            Task(id=1, text="T1", source_file=Path("a.md"), line_number=1, checked=True, kind=TaskKind.REQUIRED),
            Task(id=2, text="T2", source_file=Path("a.md"), line_number=2, checked=False, kind=TaskKind.REQUIRED, week=1),
            Task(id=3, text="T3", source_file=Path("a.md"), line_number=3, checked=False, kind=TaskKind.STRETCH),
        ]
        ctx.tasks = [t for t in tasks if not t.checked]
        ctx.completed_tasks = [t for t in tasks if t.checked]
        
        summary = summarize_progress(ctx, current_week=2)
        self.assertEqual(summary.required_total, 2)
        self.assertEqual(summary.required_done, 1)
        self.assertEqual(len(summary.behind), 1)

    def test_task_sorting(self):
        """Verifies that relevance sorting puts current week first."""
        tasks = [
            Task(id=1, text="Future", source_file=Path("a.md"), line_number=1, checked=False, week=5),
            Task(id=2, text="Current", source_file=Path("a.md"), line_number=2, checked=False, week=2),
            Task(id=3, text="Past", source_file=Path("a.md"), line_number=3, checked=False, week=1),
        ]
        sorted_tasks = task_logic.sort_tasks(tasks, self.config, week=2)
        self.assertEqual(sorted_tasks[0].text, "Current")
        self.assertEqual(sorted_tasks[1].text, "Future")
        self.assertEqual(sorted_tasks[2].text, "Past")

if __name__ == "__main__":
    unittest.main()
