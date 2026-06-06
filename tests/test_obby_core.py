from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from obby_core.app import ObbyApp
from obby_core.classifier import classify_context
from obby_core.commands import CATEGORY_ORDER, COMMANDS, commands_by_category, resolve_category
from obby_core.models import AppConfig, ModuleRule, Task, TaskKind, Theme
from obby_core.prompts import build_system_prompt, wrap_user_prompt
from obby_core.scanner import scan_notes
from obby_core.state import LocalState
from obby_core import task_logic
from obby_core import ui


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
        module_rules=[
            ModuleRule(
                key="app",
                name="Application",
                tags=["#module/app", "#app"],
                outline_names=["Outline"],
            )
        ],
        task_type_tags={
            "required": ["#required"],
            "stretch": ["#stretch"],
            "optional": ["#optional"],
            "idea": ["#idea"],
            "blocked": ["#blocked"],
        },
        heading_rules={
            "required": ["must do", "required"],
            "stretch": ["stretch"],
            "optional": ["optional"],
            "idea": ["ideas"],
            "blocked": ["blocked"],
        },
        ignore_keywords=[".obsidian"],
        max_lines_per_file=120,
        max_total_context_chars=24000,
        prompt_presets={
            "2": (
                "List pending TODOs",
                "List pending TODOs from the provided notes.",
            )
        },
        todo_source_keywords=["Tasks", "Sprint"],
        active_source_keywords=["Today", "Inbox"],
        active_week_source_patterns=[r"sprint\s*{week}\b", r"week\s*{week}\b"],
        candidate_task_kinds=["required", "blocked", "stretch"],
        candidate_max_tasks=10,
        theme=Theme(),
        xp_rules={},
    )


def make_task(path: str, text: str, kind: TaskKind, week: int | None = None) -> Task:
    return Task(
        id=1,
        text=text,
        source_file=Path(path),
        line_number=1,
        checked=False,
        week=week,
        kind=kind,
    )


class ScannerClassifierTests(unittest.TestCase):
    def test_scanner_and_classifier_use_configurable_headings_and_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = root / "Sprint 2 Tasks.md"
            note.write_text(
                "\n".join(
                    [
                        "# Sprint 2",
                        "## Must Do",
                        "- [ ] Ship demo #module/app",
                        "## Optional",
                        "- [ ] Polish dashboard",
                        "## Blocked",
                        "- [ ] Wait for API key #blocked",
                    ]
                ),
                encoding="utf-8",
            )
            ignored = root / ".obsidian" / "Ignored.md"
            ignored.parent.mkdir()
            ignored.write_text("- [ ] Hidden task #required", encoding="utf-8")

            config = make_config(root)
            ctx = scan_notes(config)
            classify_context(ctx, config)

            self.assertEqual(len(ctx.tasks), 3)
            self.assertEqual(ctx.tasks[0].kind, TaskKind.REQUIRED)
            self.assertEqual(ctx.tasks[0].module, "app")
            self.assertEqual(ctx.tasks[1].kind, TaskKind.OPTIONAL)
            self.assertEqual(ctx.tasks[2].kind, TaskKind.BLOCKED)


class TaskLogicTests(unittest.TestCase):
    def test_active_week_source_patterns_are_configurable(self) -> None:
        config = make_config(Path("/tmp/example"))
        sprint_task = make_task("notes/Sprint 2 Tasks.md", "Ship demo", TaskKind.REQUIRED)
        week_task = make_task("notes/Week 2.md", "Write notes", TaskKind.REQUIRED)
        old_task = make_task("notes/Sprint 1 Tasks.md", "Old task", TaskKind.REQUIRED)

        self.assertTrue(task_logic.is_active_task(sprint_task, config, 2))
        self.assertTrue(task_logic.is_active_task(week_task, config, 2))
        self.assertFalse(task_logic.is_active_task(old_task, config, 2))

    def test_current_behind_upcoming_do_not_need_one_note_style(self) -> None:
        config = make_config(Path("/tmp/example"))
        tasks = [
            make_task("notes/Sprint 2 Tasks.md", "Current by source", TaskKind.REQUIRED),
            make_task("notes/Any Tasks.md", "Current by tag", TaskKind.REQUIRED, week=2),
            make_task("notes/Any Tasks.md", "Behind", TaskKind.REQUIRED, week=1),
            make_task("notes/Any Tasks.md", "Upcoming", TaskKind.REQUIRED, week=3),
            make_task("notes/Sprint 2 Tasks.md", "Optional", TaskKind.OPTIONAL),
        ]

        self.assertEqual([task.text for task in task_logic.current_tasks(tasks, config, 2)], ["Current by tag", "Current by source"])
        self.assertEqual([task.text for task in task_logic.behind_tasks(tasks, config, 2)], ["Behind"])
        self.assertEqual([task.text for task in task_logic.upcoming_tasks(tasks, config, 2)], ["Upcoming"])


class AppRoutingTests(unittest.TestCase):
    def test_prompt_2_lists_tasks_locally_without_ollama(self) -> None:
        app = ObbyApp(["--config", "/tmp/no-such-obby-config.py"])
        calls: list[str] = []

        app.ask_ollama = lambda prompt: calls.append("ollama")  # type: ignore[method-assign]
        app.print_pending_todos = lambda: calls.append("local")  # type: ignore[method-assign]

        app.run_prompt_key("2")

        self.assertEqual(calls, ["local"])

    def test_prompt_command_is_removed(self) -> None:
        app = ObbyApp(["--config", "/tmp/no-such-obby-config.py"])
        calls: list[str] = []
        original_error = ui.error
        ui.error = lambda message: calls.append(message)  # type: ignore[assignment]
        try:
            self.assertTrue(app.handle_command("/prompt 2"))
        finally:
            ui.error = original_error

        self.assertTrue(any("Unknown command" in message for message in calls))

    def test_noisy_aliases_are_removed(self) -> None:
        app = ObbyApp(["--config", "/tmp/no-such-obby-config.py"])
        calls: list[str] = []
        original_error = ui.error
        ui.error = lambda message: calls.append(message)  # type: ignore[assignment]
        try:
            for command in ["/daily", "/today-dashboard", "/board", "/ops", "/plan-today", "/p"]:
                self.assertTrue(app.handle_command(command))
        finally:
            ui.error = original_error

        self.assertEqual(len(calls), 6)
        self.assertTrue(all("Unknown command" in message for message in calls))

    def test_llm_switch_blocks_ollama_backed_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = ObbyApp(["--config", "/tmp/no-such-obby-config.py"])
            app.state = LocalState(Path(tmp) / "state.json")
            app.state.set_llm_enabled(False)
            calls: list[str] = []

            app.client.is_running = lambda: True  # type: ignore[method-assign]
            app.client.chat = lambda messages: calls.append("ollama") or "reply"  # type: ignore[method-assign]

            app.ask_ollama("hello")
            app.ask_grounded("Plan today")

            self.assertEqual(calls, [])

    def test_llm_switch_commands_persist_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = ObbyApp(["--config", "/tmp/no-such-obby-config.py"])
            app.state = LocalState(Path(tmp) / "state.json")

            app.handle_command("/llm off")
            self.assertFalse(app.llm_enabled())

            app.handle_command("/llm on")
            self.assertTrue(app.llm_enabled())

    def test_free_text_ollama_call_wraps_obby_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = ObbyApp(["--config", "/tmp/no-such-obby-config.py"])
            app.config = make_config(Path(tmp))
            app.state = LocalState(Path(tmp) / "state.json")
            app.context_str = "=== UNCHECKED TASKS ==="
            app.messages = []
            captured: list[list[dict[str, str]]] = []

            app.client.is_running = lambda: True  # type: ignore[method-assign]
            app.client.chat = lambda messages: captured.append(messages) or "I am Obby."  # type: ignore[method-assign]

            app.ask_ollama("who are you")

            self.assertIn("You are answering as Obby.", captured[0][-2]["content"])
            self.assertIn("User request:\nwho are you", captured[0][-2]["content"])


class CommandRegistryTests(unittest.TestCase):
    def test_commands_are_grouped_by_category(self) -> None:
        grouped = commands_by_category()

        for category in CATEGORY_ORDER:
            self.assertIn(category, grouped)

        self.assertIn("/dashboard", [command.command for command in grouped["Daily"]])
        self.assertIn("/quests", [command.command for command in grouped["Tasks"]])
        self.assertIn("/focus", [command.command for command in grouped["LLM"]])
        self.assertIn("/llm off", [command.command for command in grouped["Session"]])

    def test_command_registry_has_no_duplicate_primary_commands(self) -> None:
        primary = [command.command for command in COMMANDS]

        self.assertEqual(len(primary), len(set(primary)))
        self.assertNotIn("/prompt N", primary)

    def test_category_filter_resolves_exact_aliases(self) -> None:
        self.assertEqual(resolve_category("llm"), "LLM")
        self.assertNotEqual(resolve_category("llm"), "Daily")
        self.assertEqual(resolve_category("all"), "Broad Views")


class PromptTests(unittest.TestCase):
    def test_system_prompt_uses_configured_obby_identity(self) -> None:
        config = make_config(Path("/tmp/example"))
        config.llm_identity = "You are Obby, a configurable local notes assistant."
        config.llm_mission = "Help with real tasks only."
        config.llm_style_rules = ["Say you are Obby.", "Do not invent tasks."]

        prompt = build_system_prompt(config, "=== UNCHECKED TASKS ===", 2)

        self.assertIn("You are Obby, a configurable local notes assistant.", prompt)
        self.assertIn("Help with real tasks only.", prompt)
        self.assertIn("Say you are Obby.", prompt)

    def test_user_prompt_wrapper_reinforces_identity(self) -> None:
        config = make_config(Path("/tmp/example"))
        wrapped = wrap_user_prompt(config, 2, "are you obby?")

        self.assertIn("You are answering as Obby.", wrapped)
        self.assertIn("Do not claim to be a generic chatbot.", wrapped)
        self.assertIn("User request:\nare you obby?", wrapped)


if __name__ == "__main__":
    unittest.main()
