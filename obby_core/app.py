from __future__ import annotations

import questionary

from .classifier import classify_context, unknown_tasks
from .config import parse_args, resolve_config
from .models import NoteContext, Task, TaskKind
from .ollama_client import OllamaClient
from .progress import resolve_week, summarize_progress
from .prompts import (
    make_grounded_action_prompt,
    make_grounded_today_plan_prompt,
    make_weekly_draft_prompt,
    reset_messages,
    wrap_user_prompt,
)
from .scanner import build_context_string, scan_notes
from .state import LocalState
from .task_board import TaskBoard, task_state_key
from . import ui
from . import drafts


class ObbyApp:
    def __init__(self, argv: list[str] | None = None) -> None:
        self.args = parse_args(argv)
        self.config = resolve_config(self.args)
        self.state = LocalState.default()
        self.client = OllamaClient(self.config)
        self.ctx: NoteContext = NoteContext(target_folder=self.config.target_folder)
        self.week = 1
        self.board = TaskBoard(self.ctx, self.config, self.week, self.state)
        self.context_str = ""
        self.messages: list[dict[str, str]] = []

    def refresh(self) -> None:
        self.ctx = scan_notes(self.config)
        classify_context(self.ctx, self.config)
        if self.config.current_week is None:
            self.config.current_week = self.state.get_current_week()
        self.week = resolve_week(self.ctx, self.config)
        self.board = TaskBoard(self.ctx, self.config, self.week, self.state)
        self.context_str = build_context_string(self.ctx, self.config, self.week)
        self.messages = reset_messages(self.config, self.context_str, self.week)

    def run(self) -> None:
        ui.banner(self.config)
        self.refresh()
        if self.ctx.errors:
            ui.error("\n".join(self.ctx.errors))
            return
            
        startup_view = self.state.get_startup_view(self.config.startup_view)
        if startup_view == "compact":
            ui.compact_boot(self.config, self.ctx, self.week)
        elif startup_view != "silent":
            ui.boot(self.config, self.ctx, self.week)
            
        self.print_dashboard()
        ui.info("Command interface started. Type /menu for commands. Type /exit to quit.")

    def run_loop(self) -> None:
        while True:
            try:
                user_input = ui.prompt_text().strip()
            except (KeyboardInterrupt, EOFError):
                ui.info("Byebye, come back again.")
                break
            if not user_input:
                continue
            if self.handle_command(user_input):
                continue
            if not self.llm_enabled():
                self.llm_disabled_notice()
                continue
            self.ask_ollama(user_input)

    def handle_command(self, user_input: str) -> bool:
        
        tokens = user_input.split()
        if not tokens:
            return False

        cmd_name = tokens[0].lower()
        args = tokens[1:]

        # Exit early
        if cmd_name in {"/exit", "/quit", "exit", "quit", "bye"}:
            ui.info("Byebye, come back again.")
            raise SystemExit(0)

        # Basic command routing table
        dispatch = {
            "/menu": lambda: self.interactive_menu() if not args else ui.command_menu(self.config, args[0]),
            "/help": lambda: self.interactive_menu() if not args else ui.command_menu(self.config, args[0]),
            "/dashboard": self.print_today_dashboard,
            "/today": self.print_today_dashboard,
            "/overview": self.print_overview_dashboard,
            "/weekly": self.print_weekly_dashboard,
            "/state": self.show_state,
            "/llm": lambda: self.handle_llm_toggle(args[0] if args else None),
            "/ai": lambda: self.handle_llm_toggle(args[0] if args else None),
            "/debug": lambda: self.handle_debug_toggle(args[0] if args else None),
            "/candidates": self.manage_candidates,
            "/refresh": self.refresh_with_notice,
            "/clear": self.clear_chat,
            "/classify": self.manual_classify,
            "/search": lambda: self.search(" ".join(args)),
            "/draft-weekly": self.run_weekly_draft_workflow,
            "/weekly-plan": lambda: self.ask_grounded("Build a weekly pacing plan.", title="Weekly Plan"),
            "/today-plan": self.ask_grounded_today_plan,
            "/focus": lambda: self.ask_grounded("Pick a 2-hour focus block.", title="Focus Recommendation"),
            "/pick": self.run_picked_prompt,
        }

        # Task list views
        task_views = {
            "/current": (self.current_tasks, "Current Week Required Tasks"),
            "/behind": (self.behind_tasks, "Behind Required Tasks"),
            "/upcoming": (self.upcoming_tasks, "Upcoming Required Tasks"),
            "/quests": (lambda: self.active_kind_tasks(TaskKind.REQUIRED), "Active Required Quests"),
            "/todos": (lambda: self.active_kind_tasks(TaskKind.REQUIRED), "Active Required Quests"),
            "/stretch": (lambda: self.active_kind_tasks(TaskKind.STRETCH), "Active Stretch Goals"),
            "/optional": (lambda: self.active_kind_tasks(TaskKind.OPTIONAL), "Active Optional Tasks"),
            "/ideas": (lambda: self.active_kind_tasks(TaskKind.IDEA), "Active Idea Backlog"),
            "/blocked": (lambda: self.active_kind_tasks(TaskKind.BLOCKED), "Active Blocked Tasks"),
            "/unknown": (lambda: self.active_kind_tasks(TaskKind.UNKNOWN), "Active Unknown Tasks"),
            "/all-quests": (lambda: self.filter_scoped(TaskKind.REQUIRED), "All Scoped Required Quests"),
            "/all-stretch": (lambda: self.filter_scoped(TaskKind.STRETCH), "All Scoped Stretch Goals"),
            "/all-optional": (lambda: self.filter_scoped(TaskKind.OPTIONAL), "All Scoped Optional Tasks"),
            "/all-ideas": (lambda: self.filter_scoped(TaskKind.IDEA), "All Scoped Idea Backlog"),
            "/all-blocked": (lambda: self.filter_scoped(TaskKind.BLOCKED), "All Scoped Blocked Tasks"),
            "/all-unknown": (lambda: self.filter_scoped(TaskKind.UNKNOWN), "All Scoped Unknown Tasks"),
        }

        if cmd_name in dispatch:
            dispatch[cmd_name]()
            return True

        if cmd_name in task_views:
            func, title = task_views[cmd_name]
            ui.task_browser(title, self.sorted_tasks(func()), view_mode=self.task_view())
            return True

        if cmd_name == "/week":
            return self.set_week(user_input)

        if cmd_name == "/deadlines":
            ui.console.print("\n".join(self.ctx.deadlines) or "[grey70]No deadlines found.[/grey70]")
            return True

        if cmd_name == "/files":
            ui.files_table(self.ctx.files_used)
            return True

        if cmd_name == "/summary":
            self.print_dashboard()
            return True

        if cmd_name == "/context":
            ui.context_preview(self.context_str)
            return True

        if cmd_name.startswith("/"):
            ui.error(f"Unknown command: {cmd_name}\n")
            if ui.console.is_terminal:
                self.interactive_menu()
            else:
                ui.info("Type /menu to see available commands.")
            return True

        return False

    def show_state(self) -> None:
        llm_state = "enabled" if self.llm_enabled() else "disabled"
        debug_state = "ON" if self.state.is_debug_enabled() else "OFF"
        ui.info(f"Week: {self.week} | LLM: {llm_state} | Debug: {debug_state} | View: {self.task_view()}")

    def handle_llm_toggle(self, sub_cmd: str | None = None) -> None:
        if sub_cmd in {"off", "disable", "disabled"}:
            self.state.set_llm_enabled(False)
            ui.info("LLM features disabled.")
        elif sub_cmd in {"on", "enable", "enabled"}:
            self.state.set_llm_enabled(True)
            ui.info("LLM features enabled.")
        else:
            state = "enabled" if self.llm_enabled() else "disabled"
            ui.info(f"LLM features are currently {state}.")

    def handle_debug_toggle(self, sub_cmd: str | None = None) -> None:
        if sub_cmd == "on":
            self.state.set_debug_enabled(True)
            ui.info("Debug ON: Grounded tasks will be displayed.")
        elif sub_cmd == "off":
            self.state.set_debug_enabled(False)
            ui.info("Debug OFF: Silent grounding.")
        else:
            state = "ON" if self.state.is_debug_enabled() else "OFF"
            ui.info(f"Debug mode is {state}.")

    def refresh_with_notice(self) -> None:
        self.refresh()
        ui.info(f"Refreshed: {len(self.ctx.files_used)} files, {len(self.ctx.tasks)} open tasks.")

    def clear_chat(self) -> None:
        self.messages = reset_messages(self.config, self.context_str, self.week)
        ui.info("Chat history cleared. Note context remains.")

    def interactive_menu(self) -> None:
        while True:
            category = ui.select_menu_category()
            if not category or category == "cancel":
                return

            cmd = ui.select_command(category)
            if not cmd or cmd == "back":
                continue

            if "<" in cmd:
                ui.info(f"Command requires arguments: {cmd}")
                return

            self.handle_command(cmd)
            return

    def print_dashboard(self) -> None:
        startup_view = self.state.get_startup_view(self.config.startup_view)
        if startup_view == "compact":
            ui.compact_dashboard(
                self.config,
                self.week,
                self.current_tasks(),
                self.behind_tasks(),
                self.active_kind_tasks(TaskKind.BLOCKED),
                self.active_kind_tasks(TaskKind.UNKNOWN),
            )
        else:
            self.print_today_dashboard()

    def print_overview_dashboard(self) -> None:
        scoped = self.todo_scope_context()
        summary = summarize_progress(scoped, self.week)
        summary.current = self.current_tasks()
        summary.behind = self.behind_tasks()
        summary.upcoming = self.upcoming_tasks()
        ui.dashboard(self.config, scoped, summary, self.week)

    def print_today_dashboard(self) -> None:
        ui.today_dashboard(
            self.config,
            self.week,
            self.today_tasks(),
            self.sorted_tasks(self.filter_scoped(TaskKind.BLOCKED)),
            self.behind_tasks(),
            self.active_kind_tasks(TaskKind.UNKNOWN),
            view_mode=self.task_view(),
        )

    def print_weekly_dashboard(self) -> None:
        ui.weekly_dashboard(
            self.config,
            self.week,
            self.current_tasks(),
            self.behind_tasks(),
            self.upcoming_tasks(),
            self.active_kind_tasks(TaskKind.BLOCKED),
            self.active_kind_tasks(TaskKind.STRETCH),
            view_mode=self.task_view(),
        )

    def set_week(self, command: str) -> bool:
        raw = command.replace("/week ", "").strip()
        if not raw.isdigit() or not (1 <= int(raw) <= self.config.total_weeks):
            ui.error(f"Please enter a week between 1 and {self.config.total_weeks}.")
            return True
        self.week = int(raw)
        self.config.current_week = self.week
        self.state.set_current_week(self.week)
        self.board = TaskBoard(self.ctx, self.config, self.week, self.state)
        self.context_str = build_context_string(self.ctx, self.config, self.week)
        self.messages = reset_messages(self.config, self.context_str, self.week)
        ui.info(f"Quest board updated for Week {self.week}. Conversation buffer reset.")
        return True

    def search(self, keyword: str) -> bool:
        if not keyword:
            ui.error("Usage: /search <keyword>")
            return True
        hits = [chunk for chunk in self.ctx.raw_chunks if keyword.lower() in chunk.lower()]
        ui.console.print("\n".join(hits[:30]) or "[grey70]No matches found.[/grey70]")
        return True

    def run_picked_prompt(self) -> None:
        key = ui.pick_prompt(self.config)
        if key:
            self.run_prompt_key(key)

    def run_prompt_key(self, key: str) -> None:
        preset = self.config.prompt_presets.get(key)
        if not preset:
            ui.error("Unknown prompt. Type /menu to see options.")
            self.interactive_menu()
            return
        name, prompt = preset
        ui.info(f"Using: {name}")
        if key == "2":
            self.print_pending_todos()
            return
        if key in {"1", "3", "4", "5", "7"}:
            self.ask_grounded(prompt)
        else:
            self.ask_ollama(prompt)

    def print_pending_todos(self) -> None:
        ui.task_browser("Pending TODOs From Active Sources", self.board.pending_todos(), view_mode=self.task_view())

    def candidate_tasks(self) -> list:
        return self.board.candidate_tasks()

    def today_tasks(self) -> list[Task]:
        return self.board.today_tasks()

    def current_tasks(self) -> list[Task]:
        return self.board.current_tasks()

    def behind_tasks(self) -> list[Task]:
        return self.board.behind_tasks()

    def upcoming_tasks(self) -> list[Task]:
        return self.board.upcoming_tasks()

    def manage_candidates(self) -> None:
        while True:
            candidates = self.candidate_tasks()
            ui.candidate_rules(self.config, self.todo_scope_tasks())
            ui.task_browser("Current Candidate Tasks", candidates, page_size=12, view_mode=self.task_view())
            
            if not ui.console.is_terminal:
                return

            action = ui.select_candidate_action()
            if action in {None, "done"}:
                break
            
            self._handle_candidate_action(action, candidates)

    def _handle_candidate_action(self, action: str, candidates: list[Task]) -> None:
        if action == "pin":
            self.pin_candidate()
        elif action == "remove":
            self.remove_candidate(candidates)
        elif action == "restore":
            self.restore_candidate()
        elif action == "clear":
            if ui.confirm("Clear all pinned/removed candidate edits?"):
                self.state.clear_list("candidate_pins")
                self.state.clear_list("candidate_exclusions")
                ui.info("Candidate edits cleared.")

    def pin_candidate(self) -> None:
        task = ui.select_task("Pin which task as a candidate?", self.sorted_tasks(self.todo_scope_tasks()))
        if not task:
            ui.info("Candidate pin cancelled.")
            return
        key = task_state_key(task)
        self.state.add_to_list("candidate_pins", key)
        self.state.remove_from_list("candidate_exclusions", key)
        ui.info(f"Pinned candidate: {task.source_label}")

    def remove_candidate(self, candidates: list[Task]) -> None:
        task = ui.select_task("Remove which candidate?", candidates)
        if not task:
            ui.info("Candidate removal cancelled.")
            return
        key = task_state_key(task)
        self.state.add_to_list("candidate_exclusions", key)
        self.state.remove_from_list("candidate_pins", key)
        ui.info(f"Removed candidate: {task.source_label}")

    def restore_candidate(self) -> None:
        scoped_by_key = {task_state_key(task): task for task in self.todo_scope_tasks()}
        removed = [
            (key, scoped_by_key.get(key))
            for key in self.state.get_list("candidate_exclusions")
        ]
        key = ui.select_removed_candidate(removed)
        if not key:
            ui.info("Candidate not restored.")
            return
        self.state.remove_from_list("candidate_exclusions", key)
        ui.info("Candidate restored.")

    def task_state_key(self, task: Task) -> str:
        return task_state_key(task)

    def todo_scope_context(self) -> NoteContext:
        return self.board.todo_scope_context()

    def todo_scope_tasks(self) -> list[Task]:
        return self.board.todo_scope_tasks()

    def filter_scoped(self, kind: TaskKind) -> list[Task]:
        return self.board.filter_scoped(kind)

    def active_kind_tasks(self, kind: TaskKind) -> list[Task]:
        return self.board.active_kind_tasks(kind)

    def is_active_task(self, task: Task) -> bool:
        return self.board.is_active_task(task)

    def sorted_tasks(self, tasks: list[Task]) -> list[Task]:
        return self.board.sorted_tasks(tasks)

    def task_relevance_key(self, task: Task) -> tuple[int, int, str, int]:
        return self.board.task_relevance_key(task)

    def is_active_source(self, path_text: str) -> bool:
        return self.board.is_active_source(path_text)

    def is_todo_source(self, task: Task) -> bool:
        return self.board.is_todo_source(task)

    def task_view(self) -> str:
        return self.state.get_task_view(self.config.task_view)

    def ask_grounded(self, intent: str, title: str = "Recommendation") -> None:
        if not self.llm_enabled():
            self.llm_disabled_notice()
            return
        candidates = self.candidate_tasks()
        if not candidates:
            ui.error("No grounded candidate tasks found. Try /quests, /unknown, or /refresh.")
            return
        prompt = make_grounded_action_prompt(self.config, self.week, intent, candidates)
        if self.state.is_debug_enabled():
            ui.task_table("Grounded Candidate Tasks (DEBUG)", candidates, limit=8, view_mode=self.task_view())
        self.ask_ollama(prompt, title=title)

    def ask_grounded_today_plan(self) -> None:
        if not self.llm_enabled():
            self.llm_disabled_notice()
            return
        candidates = self.candidate_tasks()
        if not candidates:
            ui.error("No grounded candidate tasks found. Try /quests, /unknown, or /refresh.")
            return
        prompt = make_grounded_today_plan_prompt(self.config, self.week, candidates)
        if self.state.is_debug_enabled():
            ui.task_table("Grounded Candidate Tasks (DEBUG)", candidates, limit=8, view_mode=self.task_view())
        self.ask_ollama(prompt, title="Daily Plan")

    def manual_classify(self) -> None:
        scope = ui.select_classify_scope()
        if not scope:
            ui.info("Classification cancelled.")
            return

        if scope == "unknown":
            tasks = [task for task in unknown_tasks(self.ctx) if self.is_todo_source(task)]
        elif scope == "all":
            tasks = self.todo_scope_tasks()
        else:
            tasks = [
                task for task in self.todo_scope_tasks()
                if task.week == self.week or self.is_active_source(str(task.source_file))
            ]

        if not tasks:
            ui.error("No matching unchecked tasks found.")
            return

        task = ui.select_task("Select task to classify", tasks)
        if not task:
            ui.info("Classification cancelled.")
            return

        kind = ui.select_task_kind()
        if not kind:
            ui.info("Classification cancelled.")
            return

        week = ui.ask_week(task.week or self.week)
        module = ui.select_module(self.config, task.module)

        task.kind = kind
        task.week = week
        task.module = module
        task.classification_reason = "manual classification"
        task.llm_reason = None

        self.context_str = build_context_string(self.ctx, self.config, self.week)
        self.messages = reset_messages(self.config, self.context_str, self.week)
        ui.task_table("Classified Task (memory only)", [task], view_mode=self.task_view())

    def run_weekly_draft_workflow(self) -> None:
        if not self.llm_enabled():
            self.llm_disabled_notice()
            return
            
        update = questionary.text("Paste your progress update (mention if you are planning for a specific week):").ask()
        if update is None:
            return
            
        while True:
            current = self.current_tasks()
            behind = self.behind_tasks()
            blocked = self.active_kind_tasks(TaskKind.BLOCKED)
            stretch = self.active_kind_tasks(TaskKind.STRETCH)
            completed = [task for task in self.ctx.completed_tasks if self.is_todo_source(task)]
            
            prompt = make_weekly_draft_prompt(
                self.config, self.week, update, current, behind, blocked, stretch, completed
            )
            
            draft_content = self.call_ollama_direct(prompt, "Thinking and Generating Weekly Draft...")
            if not draft_content:
                return
                
            ui.assistant_reply(draft_content, title="Weekly Draft Preview")
            
            choices = [
                questionary.Choice(title="Accept", value="accept"),
                questionary.Choice(title="Regenerate", value="regen"),
                questionary.Choice(title="Edit progress update and regenerate", value="edit"),
                questionary.Choice(title="Save draft to .obby/drafts/", value="save"),
                questionary.Choice(title="Cancel", value="cancel"),
            ]
            action = questionary.select("Draft Actions", choices=choices).ask()
            
            if action == "accept":
                ui.info("Draft accepted. You can copy it from the terminal.")
                return
            elif action == "regen":
                continue
            elif action == "edit":
                new_update = questionary.text("Edit your progress update:", default=update).ask()
                if new_update is not None:
                    update = new_update
                continue
            elif action == "save":
                path = drafts.save_weekly_draft(self.config, self.week, draft_content)
                ui.info(f"Draft saved to: {path}")
                return
            else:
                ui.info("Draft cancelled.")
                return

    def call_ollama_direct(self, prompt: str, status_msg: str) -> str | None:
        if not self.client.is_running():
            ui.error("Ollama does not seem to be running.")
            return None
        try:
            with ui.console.status(f"[bright_magenta]{status_msg}[/bright_magenta]", spinner="dots"):
                messages = reset_messages(self.config, self.context_str, self.week)
                messages.append({"role": "user", "content": wrap_user_prompt(self.config, self.week, prompt)})
                return self.client.chat(messages)
        except Exception as exc:
            ui.error(f"Error talking to Ollama:\n{exc}")
            return None

    def ask_ollama(self, prompt: str, title: str = "Recommendation") -> None:
        if not self.llm_enabled():
            self.llm_disabled_notice()
            return
        if not self.client.is_running():
            ui.error("Ollama does not seem to be running.")
            return
            
        if not self.context_str.strip():
            ui.info("Warning: No context was extracted from Obsidian. LLM results may be generic or hallucinated.")

        wrapped_prompt = wrap_user_prompt(self.config, self.week, prompt)
        self.messages.append({"role": "user", "content": wrapped_prompt})
        try:
            with ui.console.status("[bright_magenta]Reading notes and planning...[/bright_magenta]", spinner="dots"):
                reply = self.client.chat(self.messages)
            self.messages.append({"role": "assistant", "content": reply})
            ui.assistant_reply(reply, title=title)
        except Exception as exc:
            ui.error(f"Error talking to Ollama:\n{exc}")

    def llm_enabled(self) -> bool:
        return self.state.is_llm_enabled()

    def llm_disabled_notice(self) -> None:
        ui.error("LLM features are disabled. Use `/llm on` to re-enable Ollama-backed commands.")

def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "init":
        from .config import run_init_wizard
        run_init_wizard()
        return

    app = ObbyApp(argv)
    app.run()
    app.run_loop()
