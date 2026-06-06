import unittest
from pathlib import Path
import tempfile
from obby_core.scanner import _parse_file, scan_notes
from obby_core.models import NoteContext, AppConfig, TaskKind

class TestScanner(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig(
            app_name="Obby", subtitle="", tagline="", use_case="test",
            vault=None, target_folder=Path("."), model="", ollama_url="",
            ollama_tags_url="", total_weeks=10, current_week=None,
            module_rules=[], task_type_tags={}, heading_rules={},
            ignore_keywords=[], max_lines_per_file=100, max_total_context_chars=1000,
            prompt_presets={}
        )

    def test_code_block_exclusion(self):
        """Verifies that tasks inside code blocks are ignored."""
        content = """
- [ ] real task
```python
# - [ ] fake task
```
- [ ] another real task
"""
        ctx = NoteContext(target_folder=Path("."))
        _parse_file(content, Path("test.md"), ctx, self.config, 1)
        
        self.assertEqual(len(ctx.tasks), 2)
        self.assertEqual(ctx.tasks[0].text, "real task")
        self.assertEqual(ctx.tasks[1].text, "another real task")

    def test_nested_headings(self):
        """Verifies that heading paths are correctly tracked."""
        content = """
# Project A
## Phase 1
### Tasks
- [ ] nested task
"""
        ctx = NoteContext(target_folder=Path("."))
        _parse_file(content, Path("test.md"), ctx, self.config, 1)
        
        self.assertEqual(ctx.tasks[0].heading_path, ["Project A", "Phase 1", "Tasks"])

    def test_week_and_tag_extraction(self):
        """Verifies parsing of week tags and general hashtags."""
        content = "- [ ] Task for #week/5 with #urgent tag"
        ctx = NoteContext(target_folder=Path("."))
        _parse_file(content, Path("test.md"), ctx, self.config, 1)
        
        task = ctx.tasks[0]
        self.assertEqual(task.week, 5)
        self.assertIn("#urgent", task.tags)

    def test_deadline_detection(self):
        """Verifies detection of deadline keywords and emojis."""
        content = "This is a 📅 deadline for tomorrow."
        ctx = NoteContext(target_folder=Path("."))
        _parse_file(content, Path("test.md"), ctx, self.config, 1)
        
        self.assertTrue(any("📅" in line for line in ctx.deadlines))

    def test_file_read_error_handling(self):
        """Verifies that the scanner handles missing directories gracefully."""
        self.config.target_folder = Path("/non/existent/path")
        ctx = scan_notes(self.config)
        self.assertTrue(any("Folder not found" in err for err in ctx.errors))

if __name__ == "__main__":
    unittest.main()
