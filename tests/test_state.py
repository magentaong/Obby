import unittest
import json
from pathlib import Path
import tempfile
from obby_core.state import LocalState

class TestState(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.tmp_dir.name) / "state.json"
        self.state = LocalState(self.state_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_state_persistence(self):
        """Verifies saving and loading simple keys."""
        self.state.set_current_week(4)
        new_state = LocalState(self.state_path)
        self.assertEqual(new_state.get_current_week(), 4)

    def test_llm_toggle(self):
        """Verifies LLM enable/disable persistence."""
        self.state.set_llm_enabled(False)
        self.assertFalse(self.state.is_llm_enabled())
        self.state.set_llm_enabled(True)
        self.assertTrue(self.state.is_llm_enabled())

    def test_list_management(self):
        """Verifies add/remove operations on state lists (pins/exclusions)."""
        self.state.add_to_list("test_list", "item1")
        self.state.add_to_list("test_list", "item1")  # Duplicate
        self.state.add_to_list("test_list", "item2")
        
        items = self.state.get_list("test_list")
        self.assertEqual(len(items), 2)
        self.assertIn("item1", items)
        
        self.state.remove_from_list("test_list", "item1")
        self.assertEqual(len(self.state.get_list("test_list")), 1)

    def test_corrupted_json_handling(self):
        """Verifies that the state handles invalid JSON gracefully."""
        self.state_path.write_text("not valid json")
        # Should not crash, just return empty/defaults
        self.assertEqual(self.state.load(), {})
        self.assertIsNone(self.state.get_current_week())

if __name__ == "__main__":
    unittest.main()
